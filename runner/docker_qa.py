"""Docker-backed QA and isolated tool invocation.

Each job runs in a fresh container: no network, read-only root, non-root
user, dropped capabilities, no privilege escalation, bounded CPU/memory/
PIDs/scratch, and a hard timeout. The job directory is mounted read-only;
nothing from the host project or credentials is visible inside.
"""

import json
import subprocess
import tempfile
import time
import uuid
from datetime import date, timedelta
from pathlib import Path

from . import config


class QAError(Exception):
    pass


def _run_container(job: dict, timeout: int) -> dict:
    with tempfile.TemporaryDirectory(prefix="aos-qa-") as tmp:
        job_path = Path(tmp) / "job.json"
        job_path.write_text(json.dumps(job), encoding="utf-8")
        container_name = "aos-qa-" + uuid.uuid4().hex
        cmd = [
            "docker", "run", "--rm", "-i", "--name", container_name,
            "--network", "none",
            "--read-only",
            "--tmpfs", "/tmp:rw,size=32m",
            "--user", "65534:65534",
            "--cap-drop", "ALL",
            "--security-opt", "no-new-privileges:true",
            "--pids-limit", "64",
            "--memory", "256m",
            "--cpus", "1",
            "--stop-timeout", "2",
            "-v", f"{tmp}:/job:ro",
            config.QA_IMAGE,
        ]
        started = time.monotonic()
        try:
            proc = subprocess.run(
                cmd,
                input="",
                capture_output=True,
                text=True,
                timeout=timeout,
                encoding="utf-8",
                errors="replace",
            )
        except subprocess.TimeoutExpired:
            # Kill any leftover container from this job.
            subprocess.run(["docker", "rm", "-f", container_name],
                           capture_output=True, text=True)
            raise QAError("qa_timeout")
        elapsed = time.monotonic() - started

        out = (proc.stdout or "")[-config.MAX_DIAGNOSTIC_CHARS:]
        # The harness prints exactly one JSON line as its last output.
        line = out.strip().splitlines()[-1] if out.strip() else ""
        try:
            result = json.loads(line)
        except json.JSONDecodeError:
            raise QAError(
                f"harness produced no parseable result (exit={proc.returncode}): "
                f"{(proc.stderr or '')[-400:]}"
            )
        result["_elapsed_seconds"] = round(elapsed, 2)
        return result


def run_qa(bundle: dict, inputs: list[dict], run_id: str | None = None) -> dict:
    """QA a candidate bundle. Returns harness result dict."""
    job = {
        "mode": "qa",
        "source_code": bundle.get("source_code", ""),
        "tests": bundle.get("tests") or [],
        "inputs": inputs or [{}],
        "run_id": run_id,
        "snapshot": {"leads": [
            {"id": "11111111-1111-4111-8111-111111111111", "name": "QA Lead", "stage": "new",
             "last_contact_date": (date.today() - timedelta(days=14)).isoformat(), "value": 1000, "currency": "USD"},
            {"id": "22222222-2222-4222-8222-222222222222", "name": "QA Customer", "stage": "customer",
             "last_contact_date": (date.today() - timedelta(days=30)).isoformat(), "value": 500, "currency": "USD"}
        ], "tasks": [], "companies": []},
    }
    return _run_container(job, config.QA_TIMEOUT_SECONDS)


def run_invocation(tool: dict, tool_input: dict, run_id: str | None = None) -> dict:
    """Execute the pinned active tool version in the sandbox."""
    job = {
        "mode": "invoke",
        "source_code": tool.get("source_code", ""),
        "tests": [],
        "inputs": [tool_input if isinstance(tool_input, dict) else {}],
        "snapshot": tool.get("snapshot") or {},
        "run_id": run_id,
    }
    return _run_container(job, 30)
