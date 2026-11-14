"""Trusted QA/invocation harness. Runs inside the restricted container.

Reads /job/job.json, executes the generated tool's handle(input, context)
against contract probes and bundle-supplied tests, and prints one JSON
result object to stdout. Everything the tool prints is treated as data.
"""

import json
import sys
import traceback
import types

JOB_PATH = "/job/job.json"
MAX_OUTPUT = 60 * 1024
ALLOWED_OPS = {"create_followup_task", "add_activity", "update_lead_stage"}
TIMEOUT_SECONDS = 50

_failures: list[str] = []
_warnings: list[str] = []


def _fail(msg: str) -> None:
    _failures.append(msg[:500])


def _load_tool(source: str):
    module = types.ModuleType("generated_tool")
    module.__dict__["__name__"] = "generated_tool"
    try:
        exec(compile(source, "tool.py", "exec"), module.__dict__)
    except Exception:
        _fail("source failed to import: " + traceback.format_exc(limit=3)[-800:])
        return None
    handle = getattr(module, "handle", None)
    if not callable(handle):
        _fail("module does not define callable handle(input, context)")
        return None
    return module


def _validate_result(result) -> bool:
    ok = True
    if not isinstance(result, dict):
        _fail("handle() must return a dict")
        return False
    if not isinstance(result.get("display"), dict):
        _fail("result.display must be an object")
        ok = False
    ops = result.get("operations", [])
    if not isinstance(ops, list):
        _fail("result.operations must be a list")
        return False
    if len(ops) > 50:
        _fail("too many operations proposed")
        ok = False
    for i, op in enumerate(ops):
        if not isinstance(op, dict) or op.get("op") not in ALLOWED_OPS:
            _fail(f"operations[{i}] uses a disallowed op")
            ok = False
    return ok


def _call_handle(module, tool_input, context):
    try:
        return module.handle(tool_input, context), None
    except Exception:
        return None, traceback.format_exc(limit=5)[-1200:]


def main() -> int:
    sys.dont_write_bytecode = True
    try:
        with open(JOB_PATH, "r", encoding="utf-8") as fh:
            job = json.load(fh)
    except Exception as exc:
        print(json.dumps({"passed": False, "failures": [f"cannot read job: {exc}"]}))
        return 0

    mode = job.get("mode", "qa")
    source = job.get("source_code", "")
    context = {
        "snapshot": job.get("snapshot") or {},
        "run_id": job.get("run_id"),
        "workspace_id": job.get("workspace_id"),
    }

    module = _load_tool(source)
    last_result = None

    if module is not None:
        inputs = job.get("inputs") or [{}]
        results = []
        for i, tool_input in enumerate(inputs):
            result, err = _call_handle(module, tool_input if isinstance(tool_input, dict) else {}, context)
            if err:
                _fail(f"handle() raised on input {i}: {err}")
                continue
            if _validate_result(result):
                results.append(result)
                last_result = result
        if not results:
            _fail("no probe produced a valid result")

        # Bundle-supplied tests: each defines run(result, tool_module).
        for t in job.get("tests") or []:
            code = t.get("code", "") if isinstance(t, dict) else ""
            name = t.get("name", "test") if isinstance(t, dict) else "test"
            ns: dict = {}
            try:
                exec(compile(code, f"test_{name}.py", "exec"), ns)
                runner = ns.get("run")
                if not callable(runner):
                    _fail(f"test '{name}' does not define run(result, tool)")
                    continue
                runner(last_result, module)
            except Exception:
                _fail(f"test '{name}' failed: {traceback.format_exc(limit=3)[-800:]}")

    passed = not _failures
    out = {
        "passed": passed,
        "mode": mode,
        "failures": _failures[:20],
        "warnings": _warnings[:10],
    }
    if mode == "invoke" and last_result is not None:
        out["result"] = last_result
    elif last_result is not None:
        out["sample_result"] = last_result

    text = json.dumps(out)
    if len(text) > MAX_OUTPUT:
        text = json.dumps({"passed": False, "failures": ["result exceeded output cap"], "mode": mode})
    print(text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
