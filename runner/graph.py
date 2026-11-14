"""LangGraph workflow: specify -> generate -> QA -> decide, with a capped
repair loop (1 initial generation + at most 2 repairs = 3 attempts).

Attempt and budget counters live in durable run state, not the prompt.
"""

import json
import re
from typing import Any, TypedDict

from langgraph.graph import END, StateGraph

from . import bundle as bundle_check
from . import config, docker_qa, provider


class RunState(TypedDict, total=False):
    run_id: str
    prompt: str
    model_id: str | None
    api_key: str
    payer: str
    attempt: int
    provider_requests: int
    tokens_used: int
    requirement: str
    domain: str
    bundle: dict | None
    diagnostics: str
    qa_result: dict | None
    usage: list[dict]
    outcome: str
    error_code: str | None
    retry: bool


SYSTEM_PROMPT = """You build small Python tools for a CRM demo.
Reply with ONE JSON object only (no markdown) matching this shape:
{
  "schema_version": 1,
  "name": "snake_case_tool_name",
  "description": "what it does",
  "source_code": "python source defining handle(input, context)",
  "entry_point": "handle",
  "input_schema": {"type": "object"},
  "output_schema": {"type": "object"},
  "ui_spec": {"components": [{"type": "heading", "text": "..."}]},
  "allowed_operations": ["create_followup_task"],
  "tests": [{"name": "...", "code": "def run(result, tool): ..."}]
}
Rules for source_code:
- Define handle(input, context). input is a dict; context has "snapshot"
  with keys leads/companies/tasks (lists of dicts with id,name,...).
- Return {"display": {...}, "operations": [...]}. operations may only use:
  create_followup_task {title, due_date, lead_id?},
  add_activity {lead_id, kind, body},
  update_lead_stage {lead_id, stage}.
- Only stdlib imports. No network, files, or environment access.
- Dates are ISO strings. Do not crash on missing fields.
"""


def _extract_json(text: str) -> dict | None:
    text = text.strip()
    # Strip markdown fences if the model adds them.
    text = re.sub(r"^```(?:json)?\s*|\s*```$", "", text, flags=re.MULTILINE).strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    start, end = text.find("{"), text.rfind("}")
    if start != -1 and end > start:
        try:
            return json.loads(text[start : end + 1])
        except json.JSONDecodeError:
            return None
    return None


def _record_usage(state: RunState, completion) -> None:
    state.setdefault("usage", []).append(
        {
            "model_id": completion.usage.model_id,
            "payer": completion.usage.payer,
            "input_tokens": completion.usage.input_tokens,
            "output_tokens": completion.usage.output_tokens,
            "cost_usd": completion.usage.cost_usd,
            "cost_known": completion.usage.cost_known,
        }
    )
    state["tokens_used"] = state.get("tokens_used", 0) + (
        (completion.usage.input_tokens or 0) + (completion.usage.output_tokens or 0)
    )
    state["provider_requests"] = state.get("provider_requests", 0) + 1


def _budget_left(state: RunState) -> bool:
    return (
        state.get("provider_requests", 0) < config.MAX_PROVIDER_REQUESTS
        and state.get("tokens_used", 0) < config.MAX_RUN_TOKENS
    )


def node_specify(state: RunState) -> RunState:
    if config.RUNNER_FIXTURE:
        state["requirement"] = "fixture: seven-day no-activity follow-up tool"
        state["domain"] = "crm"
        return state
    if not _budget_left(state):
        state["outcome"] = "failed"
        state["error_code"] = "budget_exhausted"
        return state
    try:
        completion = provider.complete(
            api_key=state["api_key"],
            payer=state["payer"],
            model_id=state.get("model_id"),
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": f"Requirement: {state['prompt']}\nRespond with the tool JSON only."},
            ],
            max_tokens=config.MAX_OUTPUT_TOKENS,
        )
    except provider.ProviderError as exc:
        state["outcome"] = "failed" if exc.code == "invalid_key" else "needs_key" if exc.code == "needs_key" else "failed"
        state["error_code"] = exc.code
        return state
    _record_usage(state, completion)
    parsed = _extract_json(completion.text) or {}
    state["requirement"] = str(parsed.get("requirement") or state["prompt"])[:500]
    state["domain"] = str(parsed.get("domain") or "crm")[:60]
    # The same response may already contain a bundle; stash it for generate.
    if "source_code" in parsed:
        state["bundle"] = parsed
    return state


def _fixture_bundle() -> dict:
    return {
        "schema_version": 1,
        "name": "stale_lead_followup",
        "description": "TEST FIXTURE: finds leads with no activity for 7+ days and proposes follow-up tasks",
        "entry_point": "handle",
        "source_code": '''
from datetime import date, datetime

def handle(tool_input, context):
    days = int(tool_input.get("days", 7))
    today = date.today()
    leads = (context.get("snapshot") or {}).get("leads", [])
    tasks = (context.get("snapshot") or {}).get("tasks", [])
    existing = {(t.get("lead_id"), t.get("title")) for t in tasks}
    operations = []
    rows = []
    for lead in leads:
        last = lead.get("last_contact_date")
        if not last:
            continue
        try:
            last_d = date.fromisoformat(str(last)[:10])
        except ValueError:
            continue
        if (today - last_d).days >= days:
            title = f"Follow up with {lead.get('name', 'lead')}"
            if (lead.get("id"), title) in existing:
                continue
            operations.append({
                "op": "create_followup_task",
                "op_key": f"followup-{lead.get('id')}",
                "title": title,
                "due_date": today.isoformat(),
                "lead_id": lead.get("id"),
            })
            rows.append({"lead": lead.get("name"), "days_since_contact": (today - last_d).days})
    return {
        "display": {"stale_leads": rows, "tasks_created": len(operations)},
        "operations": operations[:50],
    }
''',
        "input_schema": {"type": "object", "properties": {"days": {"type": "integer"}}},
        "output_schema": {"type": "object"},
        "ui_spec": {"components": [
            {"type": "heading", "text": "Stale leads needing follow-up"},
            {"type": "table", "columns": ["lead", "days_since_contact"]},
        ]},
        "allowed_operations": ["create_followup_task"],
        "tests": [{
            "name": "returns_display_and_operations",
            "code": "def run(result, tool):\n    assert isinstance(result, dict)\n    assert 'display' in result\n",
        }],
    }


def node_generate(state: RunState) -> RunState:
    state["attempt"] = state.get("attempt", 0) + 1
    if state["attempt"] > config.MAX_GENERATION_ATTEMPTS:
        state["outcome"] = "failed"
        state["error_code"] = "attempts_exhausted"
        return state
    if not _budget_left(state):
        state["outcome"] = "failed"
        state["error_code"] = "budget_exhausted"
        return state

    if config.RUNNER_FIXTURE:
        state["bundle"] = _fixture_bundle()
        return state

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": (
            f"Requirement: {state.get('requirement') or state['prompt']}\n"
            f"Tool name hint: snake_case.\n"
            + (f"Previous attempt failed QA. Diagnostics:\n{state.get('diagnostics','')[:2000]}\nFix the tool.\n"
               if state.get("diagnostics") else "")
            + "Respond with the tool JSON only."
        )},
    ]
    try:
        completion = provider.complete(
            api_key=state["api_key"],
            payer=state["payer"],
            model_id=state.get("model_id"),
            messages=messages,
            max_tokens=config.MAX_OUTPUT_TOKENS,
        )
    except provider.ProviderError as exc:
        state["outcome"] = "failed"
        state["error_code"] = exc.code
        if exc.retryable and state["attempt"] < config.MAX_GENERATION_ATTEMPTS and _budget_left(state):
            state["diagnostics"] = f"provider error: {exc}"
            return state  # decide will route back? No — generate consumed attempt; loop via decide.
        return state
    _record_usage(state, completion)
    parsed = _extract_json(completion.text)
    if not parsed:
        state["bundle"] = None
        state["diagnostics"] = "model did not return valid JSON"
        return state
    state["bundle"] = parsed
    return state


def node_qa(state: RunState) -> RunState:
    bundle = state.get("bundle")
    if not bundle:
        state["qa_result"] = {"passed": False, "failures": ["no bundle to test"]}
        return state
    problems = bundle_check.validate_bundle(bundle)
    if problems:
        state["qa_result"] = {"passed": False, "failures": problems}
        return state
    probes = bundle.get("qa_inputs") or [
        {},
        {"days": 7},
    ]
    try:
        result = docker_qa.run_qa(bundle, probes, run_id=state.get("run_id"))
    except docker_qa.QAError as exc:
        state["qa_result"] = {"passed": False, "failures": [str(exc)]}
        return state
    state["qa_result"] = result
    return state


def node_decide(state: RunState) -> RunState:
    if state.get("outcome") in {"failed", "needs_key"}:
        state["retry"] = False
        return state
    qa = state.get("qa_result") or {}
    if qa.get("passed"):
        state["outcome"] = "awaiting_activation"
        state["retry"] = False
        return state
    # Repair loop: bounded diagnostics back to generate.
    failures = qa.get("failures") or ["QA failed"]
    state["diagnostics"] = json.dumps(failures)[:4000]
    state["retry"] = (
        state.get("attempt", 0) < config.MAX_GENERATION_ATTEMPTS
        and _budget_left(state)
    )
    if not state["retry"]:
        state["outcome"] = "failed"
        state["error_code"] = "qa_failed"
    return state


def _decide_route(state: RunState) -> str:
    return "generate" if state.get("retry") else END


def build_graph():
    g = StateGraph(RunState)
    g.add_node("specify", node_specify)
    g.add_node("generate", node_generate)
    g.add_node("qa", node_qa)
    g.add_node("decide", node_decide)
    g.add_conditional_edges("specify", lambda s: END if s.get("outcome") else "generate")
    g.add_edge("generate", "qa")
    g.add_edge("qa", "decide")
    g.add_conditional_edges("decide", _decide_route, {"generate": "generate", END: END})
    g.set_entry_point("specify")
    return g.compile()


def run_workflow(initial: RunState) -> RunState:
    graph = build_graph()
    return graph.invoke(initial, config={"recursion_limit": 15})
