"""Tool bundle contract validation (developer-side filter).

The Docker sandbox is the real boundary; this static check rejects
malformed bundles and obvious escape attempts before wasting a QA slot.
"""

import ast
import re

from . import config

ALLOWED_OPS = {"create_followup_task", "add_activity", "update_lead_stage"}
ALLOWED_UI_TYPES = {"heading", "text", "number", "date", "select", "table", "badge"}
BUNDLE_SCHEMA_VERSION = 1

_NAME_RE = re.compile(r"^[a-z][a-z0-9_]{1,60}$")

_FORBIDDEN_IMPORTS = {
    "os", "subprocess", "socket", "sys", "shutil", "pathlib", "importlib",
    "ctypes", "multiprocessing", "threading", "http", "urllib", "requests",
    "sqlite3", "pickle", "marshal", "builtins", "runpy", "pty", "signal",
}


class BundleError(Exception):
    pass


def validate_bundle(bundle: dict) -> list[str]:
    """Return list of problems; empty means structurally valid."""
    problems: list[str] = []
    if not isinstance(bundle, dict):
        return ["bundle must be an object"]

    if bundle.get("schema_version") != BUNDLE_SCHEMA_VERSION:
        problems.append(f"schema_version must be {BUNDLE_SCHEMA_VERSION}")

    name = bundle.get("name")
    if not isinstance(name, str) or not _NAME_RE.match(name):
        problems.append("name must be a lowercase snake_case identifier")

    source = bundle.get("source_code")
    if not isinstance(source, str) or not source.strip():
        problems.append("source_code is required")
    elif len(source.encode()) > config.MAX_BUNDLE_SOURCE:
        problems.append("source_code exceeds size limit")
    else:
        problems.extend(_check_source(source))

    if bundle.get("entry_point", "handle") != "handle":
        problems.append("entry_point must be 'handle'")

    for key in ("input_schema", "output_schema", "ui_spec"):
        if not isinstance(bundle.get(key), dict):
            problems.append(f"{key} must be an object")

    ops = bundle.get("allowed_operations")
    if not isinstance(ops, list) or not ops:
        problems.append("allowed_operations must be a non-empty list")
    else:
        bad = set(ops) - ALLOWED_OPS
        if bad:
            problems.append(f"disallowed operations: {sorted(bad)}")

    ui = bundle.get("ui_spec") or {}
    components = ui.get("components") if isinstance(ui, dict) else None
    if components is not None:
        if not isinstance(components, list):
            problems.append("ui_spec.components must be a list")
        else:
            for i, comp in enumerate(components):
                if not isinstance(comp, dict) or comp.get("type") not in ALLOWED_UI_TYPES:
                    problems.append(f"ui_spec.components[{i}] has unsupported type")

    tests = bundle.get("tests")
    if tests is not None and not isinstance(tests, list):
        problems.append("tests must be a list")

    return problems


def _check_source(source: str) -> list[str]:
    problems = []
    try:
        tree = ast.parse(source)
    except SyntaxError as exc:
        return [f"source has a syntax error: {exc}"]

    has_handle = any(
        isinstance(node, ast.FunctionDef) and node.name == "handle"
        for node in ast.walk(tree)
    )
    if not has_handle:
        problems.append("source must define handle(input, context)")

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                root = alias.name.split(".")[0]
                if root in _FORBIDDEN_IMPORTS:
                    problems.append(f"forbidden import: {alias.name}")
        elif isinstance(node, ast.ImportFrom):
            root = (node.module or "").split(".")[0]
            if root in _FORBIDDEN_IMPORTS:
                problems.append(f"forbidden import: {node.module}")
        elif isinstance(node, ast.Call):
            # Block obvious dynamic escapes.
            func = node.func
            name = ""
            if isinstance(func, ast.Name):
                name = func.id
            elif isinstance(func, ast.Attribute):
                name = func.attr
            if name in {"eval", "exec", "compile", "__import__", "breakpoint", "input", "open"}:
                problems.append(f"forbidden call: {name}()")
    return problems
