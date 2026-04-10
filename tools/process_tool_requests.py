#!/usr/bin/env python3
"""Process structured tool requests into canonical grant state and a rendered summary."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


SCHEMA_VERSION = "clawwars/vnext/tool_grants@1"
REQUIRED_FIELDS = ("id", "heartbeat", "tool", "why", "plan", "risk", "alternatives_considered")
VALID_RISKS = {"LOW", "MEDIUM", "HIGH"}
MANUAL_STATUSES = {"granted", "denied"}


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def ensure_tool_grants(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {"schema_version": SCHEMA_VERSION, "grants": []}
    data = load_json(path)
    if not isinstance(data, dict):
        raise ValueError(f"{path} must contain a JSON object")
    data.setdefault("schema_version", SCHEMA_VERSION)
    grants = data.setdefault("grants", [])
    if not isinstance(grants, list):
        raise ValueError(f"{path}.grants must be a list")
    return data


def validate_request(data: Any) -> tuple[dict[str, Any] | None, list[str]]:
    errors: list[str] = []
    if not isinstance(data, dict):
        return None, ["request must be a JSON object"]

    normalized: dict[str, Any] = dict(data)
    missing = [field for field in REQUIRED_FIELDS if field not in normalized]
    if missing:
        errors.append(f"missing required fields: {', '.join(missing)}")

    if "id" in normalized and (not isinstance(normalized["id"], str) or not normalized["id"].strip()):
        errors.append("id must be a non-empty string")
    if "heartbeat" in normalized and (not isinstance(normalized["heartbeat"], int) or normalized["heartbeat"] < 1):
        errors.append("heartbeat must be an integer >= 1")
    for field in ("tool", "why", "plan"):
        if field in normalized and (not isinstance(normalized[field], str) or not normalized[field].strip()):
            errors.append(f"{field} must be a non-empty string")

    if "risk" in normalized:
        if not isinstance(normalized["risk"], str) or not normalized["risk"].strip():
            errors.append("risk must be a non-empty string")
        else:
            normalized["risk"] = normalized["risk"].upper()
            if normalized["risk"] not in VALID_RISKS:
                errors.append(f"risk must be one of: {', '.join(sorted(VALID_RISKS))}")

    if "alternatives_considered" in normalized:
        alternatives = normalized["alternatives_considered"]
        if not isinstance(alternatives, list) or not alternatives:
            errors.append("alternatives_considered must be a non-empty list of strings")
        elif any(not isinstance(item, str) or not item.strip() for item in alternatives):
            errors.append("alternatives_considered must contain only non-empty strings")

    return (normalized if not errors else None), errors


def invalid_record(source_file: Path, reason: str, request: dict[str, Any] | None = None) -> dict[str, Any]:
    request_id = request.get("id") if isinstance(request, dict) else None
    tool_name = request.get("tool") if isinstance(request, dict) else None
    return {
        "id": f"invalid:{source_file.stem}",
        "request_id": request_id,
        "tool": tool_name or "<invalid>",
        "status": "invalid",
        "heartbeat": request.get("heartbeat") if isinstance(request, dict) else None,
        "risk": request.get("risk") if isinstance(request, dict) else None,
        "source": "request_file",
        "source_file": source_file.as_posix(),
        "requested_at": request.get("requested_at") if isinstance(request, dict) else None,
        "decided_at": utc_now(),
        "reason": reason,
    }


def decision_record(request: dict[str, Any], source_file: Path) -> dict[str, Any]:
    risk = request["risk"]
    status = "auto_granted" if risk == "LOW" else "pending_review"
    reason = "Auto-approved because the request is marked LOW risk." if risk == "LOW" else "Queued for operator review because the request is MEDIUM/HIGH risk."
    return {
        "id": request["id"],
        "request_id": request["id"],
        "tool": request["tool"],
        "status": status,
        "heartbeat": request["heartbeat"],
        "risk": risk,
        "source": "request_file",
        "source_file": source_file.as_posix(),
        "requested_at": request.get("requested_at"),
        "decided_at": utc_now(),
        "reason": reason,
        "why": request["why"],
        "plan": request["plan"],
        "alternatives_considered": request["alternatives_considered"],
    }


def render_tool_grants(markdown_path: Path, grants: list[dict[str, Any]]) -> None:
    sections = [
        ("granted", "Granted"),
        ("auto_granted", "Auto-Approved"),
        ("pending_review", "Pending Review"),
        ("denied", "Denied"),
        ("invalid", "Invalid"),
    ]

    lines = [
        "# TOOL GRANTS",
        "",
        "Rendered from `state/tool_grants.json`. Canonical tool-request and grant state lives under `state/`.",
        "",
        "**No raw secrets here.** Reference secret names only.",
        "",
    ]

    for status, title in sections:
        lines.append(f"## {title}")
        subset = [grant for grant in grants if grant.get("status") == status]
        if not subset:
            lines.append("_(none)_")
            lines.append("")
            continue
        for grant in sorted(subset, key=lambda item: (item.get("heartbeat") or 0, item.get("id", ""))):
            lines.append(f"### {grant.get('tool', '<unknown>')} ({grant.get('id', '<no-id>')})")
            lines.append(f"**Status**: {grant.get('status')}")
            if grant.get("heartbeat") is not None:
                lines.append(f"**Heartbeat**: {grant.get('heartbeat')}")
            if grant.get("risk"):
                lines.append(f"**Risk**: {grant.get('risk')}")
            if grant.get("reason"):
                lines.append(f"**Reason**: {grant.get('reason')}")
            if grant.get("access"):
                lines.append(f"**Access**: {grant.get('access')}")
            if grant.get("limits"):
                lines.append(f"**Limits**: {grant.get('limits')}")
            if grant.get("source_file"):
                lines.append(f"**Source file**: `{grant.get('source_file')}`")
            lines.append("")

    markdown_path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")


def process_requests(state_dir: Path, render_target: Path) -> tuple[list[dict[str, Any]], int]:
    tool_grants_path = state_dir / "tool_grants.json"
    requests_dir = state_dir / "tool_requests"
    requests_dir.mkdir(parents=True, exist_ok=True)

    existing = ensure_tool_grants(tool_grants_path)
    existing_grants = existing.get("grants", [])
    preserved_bootstrap = [grant for grant in existing_grants if grant.get("source") == "bootstrap"]
    preserved_manual = [grant for grant in existing_grants if grant.get("status") in MANUAL_STATUSES and grant.get("source") != "bootstrap"]
    manual_by_request_id = {
        grant.get("request_id"): grant
        for grant in preserved_manual
        if isinstance(grant, dict) and grant.get("request_id")
    }

    processed: list[dict[str, Any]] = []
    seen_request_ids: set[str] = set()
    exit_code = 0

    for path in sorted(requests_dir.glob("*.json")):
        relative_path = path.relative_to(state_dir.parent)
        try:
            raw = load_json(path)
        except json.JSONDecodeError as exc:
            processed.append(invalid_record(relative_path, f"invalid JSON: {exc.msg}"))
            exit_code = 1
            continue

        request, errors = validate_request(raw)
        if errors:
            processed.append(invalid_record(relative_path, "; ".join(errors), raw if isinstance(raw, dict) else None))
            exit_code = 1
            continue

        assert request is not None
        request_id = request["id"]
        if request_id in seen_request_ids:
            processed.append(invalid_record(relative_path, f"duplicate request id: {request_id}", request))
            exit_code = 1
            continue

        seen_request_ids.add(request_id)
        manual = manual_by_request_id.get(request_id)
        if manual:
            preserved = dict(manual)
            preserved["source_file"] = relative_path.as_posix()
            processed.append(preserved)
            continue

        processed.append(decision_record(request, relative_path))

    historical_manual = [grant for grant in preserved_manual if grant.get("request_id") not in seen_request_ids]
    final_grants = preserved_bootstrap + historical_manual + processed
    final_grants.sort(key=lambda item: (item.get("heartbeat") or 0, item.get("id", "")))

    payload = {"schema_version": SCHEMA_VERSION, "grants": final_grants}
    tool_grants_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    render_tool_grants(render_target, final_grants)
    return final_grants, exit_code


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--state-dir", default=str(Path(__file__).resolve().parents[1] / "state"))
    parser.add_argument("--render-target", default=str(Path(__file__).resolve().parents[1] / "TOOL_GRANTS.md"))
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    state_dir = Path(args.state_dir).resolve()
    render_target = Path(args.render_target).resolve()
    _, exit_code = process_requests(state_dir, render_target)
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
