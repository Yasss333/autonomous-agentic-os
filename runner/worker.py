"""Worker main loop: claim -> heartbeat -> execute -> submit result.

One job at a time. Heartbeats keep the 30s lease alive; the API clock is
authoritative. The sponsored OpenRouter key comes from this process's
environment; reviewer keys are fetched per job and dropped afterwards.
"""

import json
import sys
import threading
import time
import urllib.request

from . import config, graph


def _api(path: str, method: str = "GET", body: dict | None = None) -> dict:
    req = urllib.request.Request(
        f"{config.API_BASE_URL}{path}",
        method=method,
        headers={
            "Authorization": f"Bearer {config.RUNNER_TOKEN}",
            "X-Worker-Id": config.WORKER_ID,
            "Content-Type": "application/json",
        },
        data=json.dumps(body).encode() if body is not None else None,
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode())


def _fetch_reviewer_key(ref: str) -> str | None:
    try:
        data = _api(f"/worker/credentials/{ref}")
        return data.get("api_key")
    except Exception:
        return None


def _heartbeat_loop(stop: threading.Event, lease_token: str) -> None:
    while not stop.wait(config.HEARTBEAT_SECONDS):
        try:
            _api("/worker/heartbeat", "POST", {"lease_token": lease_token})
        except Exception:
            return  # lease lost; main flow will fail on next call


def _progress(lease_token: str, kind: str, payload: dict) -> None:
    try:
        _api("/worker/progress", "POST", {"lease_token": lease_token, "kind": kind, "payload": payload})
    except Exception:
        pass


def _resolve_key(job: dict) -> tuple[str, str]:
    """Return (api_key, payer). Raises RuntimeError('needs_key') if absent."""
    if config.RUNNER_FIXTURE:
        # Labeled test fixture: no provider call is made, so no key is needed.
        return "fixture-no-key", "sponsored"
    if job.get("credential_mode") == "byok":
        ref = job.get("credential_ref")
        if not ref:
            raise RuntimeError("needs_key")
        key = _fetch_reviewer_key(ref)
        if not key:
            raise RuntimeError("needs_key")
        return key, "reviewer_key"
    if config.OPENROUTER_API_KEY or config.VELONA_API_KEY:
        return config.OPENROUTER_API_KEY, "sponsored"
    raise RuntimeError("needs_key")


def execute_generate(job: dict, lease_token: str) -> dict:
    try:
        api_key, payer = _resolve_key(job)
    except RuntimeError as exc:
        return {"outcome": "needs_key", "error_code": str(exc)}

    _progress(lease_token, "generating", {"attempt": 0, "message": "Starting generation"})
    initial: graph.RunState = {
        "run_id": job["run_id"],
        "prompt": job.get("prompt") or "",
        "model_id": job.get("model_id"),
        "api_key": api_key,
        "payer": payer,
        "attempt": job.get("attempt_count", 0),
        "provider_requests": 0,
        "tokens_used": 0,
        "usage": [],
    }
    try:
        state = graph.run_workflow(initial, lambda kind, payload: _progress(lease_token, kind, payload))
    except Exception as exc:
        return {
            "outcome": "failed",
            "error_code": "worker_error",
            "error": f"{type(exc).__name__}: {exc}"[:500],
            "usage": initial.get("usage", []),
        }

    usage = state.get("usage", [])
    outcome = state.get("outcome", "failed")
    if outcome == "awaiting_activation":
        _progress(lease_token, "testing", {"message": "QA passed; awaiting activation"})
        return {
            "outcome": "awaiting_activation",
            "bundle": state.get("bundle"),
            "qa": state.get("qa_result"),
            "attempts": state.get("attempt", 0),
            "usage": usage,
        }
    return {
        "outcome": outcome if outcome in {"failed", "needs_key"} else "failed",
        "error_code": state.get("error_code") or "unknown",
        "attempts": state.get("attempt", 0),
        "diagnostics": (state.get("diagnostics") or "")[:2000],
        "bundle": state.get("bundle"),
        "qa": state.get("qa_result"),
        "usage": usage,
    }


def execute_invoke(job: dict, lease_token: str) -> dict:
    from . import docker_qa

    tool = job.get("tool") or {}
    tool_input = ((job.get("input") or {}).get("tool_input")) or {}
    _progress(lease_token, "testing", {"message": "Running tool in sandbox"})
    try:
        result = docker_qa.run_invocation(
            {**tool, "snapshot": (tool.get("snapshot") or {})},
            tool_input,
            run_id=job["run_id"],
        )
    except docker_qa.QAError as exc:
        return {"outcome": "failed", "error_code": "sandbox_error", "error": str(exc)[:500]}

    if result.get("passed") and result.get("result"):
        r = result["result"]
        return {
            "outcome": "succeeded",
            "display": r.get("display") or {},
            "operations": r.get("operations") or [],
        }
    return {
        "outcome": "failed",
        "error_code": "tool_failed",
        "error": json.dumps(result.get("failures", []))[:1000],
    }


def handle_job(job: dict) -> dict:
    lease_token = job["lease"]["token"]
    stop = threading.Event()
    hb = threading.Thread(target=_heartbeat_loop, args=(stop, lease_token), daemon=True)
    hb.start()
    try:
        if job["kind"] == "generate":
            result = execute_generate(job, lease_token)
        elif job["kind"] == "tool_invoke":
            result = execute_invoke(job, lease_token)
        else:
            result = {"outcome": "failed", "error_code": "unknown_kind"}
        # Map invoke-specific keys into the submit_result contract.
        if job["kind"] == "tool_invoke" and result.get("outcome") == "succeeded":
            result = {
                "outcome": "succeeded",
                "operations": result.get("operations") or [],
                "display": result.get("display") or {},
            }
        return result
    finally:
        stop.set()


def main() -> int:
    if not config.RUNNER_TOKEN:
        print("RUNNER_TOKEN is not set", file=sys.stderr)
        return 1
    print(f"worker {config.WORKER_ID} polling {config.API_BASE_URL}")
    idle = config.POLL_SECONDS
    while True:
        try:
            resp = _api("/worker/claim", "POST", {})
        except Exception as exc:
            print(f"claim failed: {exc}", file=sys.stderr)
            time.sleep(min(idle * 2, 30))
            idle = config.POLL_SECONDS
            continue
        job = resp.get("job")
        if not job:
            time.sleep(idle)
            idle = min(idle * 1.5, 15)
            continue
        idle = config.POLL_SECONDS
        print(f"claimed run {job['run_id']} kind={job['kind']}")
        try:
            result = handle_job(job)
            _api("/worker/result", "POST", {
                "lease_token": job["lease"]["token"],
                "result": result,
            })
            print(f"run {job['run_id']} -> {result.get('outcome')}")
        except Exception as exc:
            print(f"job {job['run_id']} failed in worker: {exc}", file=sys.stderr)
            try:
                _api("/worker/result", "POST", {
                    "lease_token": job["lease"]["token"],
                    "result": {"outcome": "failed", "error_code": "worker_error"},
                })
            except Exception:
                pass


if __name__ == "__main__":
    sys.exit(main())
