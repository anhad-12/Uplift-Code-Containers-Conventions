"""Load and validate reports. Keep this module free of Dash imports so it can be unit-tested."""
from __future__ import annotations

import json
from pathlib import Path

from jsonschema import Draft7Validator

HERE = Path(__file__).parent
REPORTS = HERE / "reports"
SCHEMA_PATH = HERE / "schema" / "report.schema.json"  # a committed COPY: Render deploys only the dashboard/ folder


def load_schema() -> dict:
    return json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))


def validate(report: dict) -> list[str]:
    """Return human-readable schema errors (empty list = valid)."""
    validator = Draft7Validator(load_schema())
    return [f"{'/'.join(map(str, e.absolute_path)) or 'report'}: {e.message}" for e in validator.iter_errors(report)]


def load_index() -> list[dict]:
    return json.loads((REPORTS / "index.json").read_text(encoding="utf-8"))


def load_report(file_name: str) -> dict:
    return json.loads((REPORTS / file_name).read_text(encoding="utf-8"))


def load_all() -> dict[str, dict]:
    """scenario id -> report; invalid reports are kept with an '_errors' key so the UI can show them."""
    out: dict[str, dict] = {}
    for entry in load_index():
        report = load_report(entry["file"])
        errors = validate(report)
        if errors:
            report = {**report, "_errors": errors}
        out[entry["id"]] = report
    return out
