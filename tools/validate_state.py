#!/usr/bin/env python3
"""Lightweight validator for Claw Pilot vNext canonical state."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
STATE_DIR = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else ROOT / "state"


def fail(errors: list[str]) -> int:
    for error in errors:
        print(f"ERROR: {error}", file=sys.stderr)
    return 1


def load_json(path: Path, errors: list[str]) -> dict[str, Any] | None:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        errors.append(f"missing file: {path}")
        return None
    except json.JSONDecodeError as exc:
        errors.append(f"invalid JSON in {path}: {exc}")
        return None
    if not isinstance(data, dict):
        errors.append(f"{path} must contain a JSON object")
        return None
    return data


def load_jsonl(path: Path, errors: list[str]) -> list[dict[str, Any]] | None:
    try:
        raw = path.read_text(encoding="utf-8")
    except FileNotFoundError:
        errors.append(f"missing file: {path}")
        return None

    records: list[dict[str, Any]] = []
    for index, line in enumerate(raw.splitlines(), start=1):
        if not line.strip():
            continue
        try:
            record = json.loads(line)
        except json.JSONDecodeError as exc:
            errors.append(f"invalid JSONL in {path}:{index}: {exc}")
            continue
        if not isinstance(record, dict):
            errors.append(f"{path}:{index} must be a JSON object")
            continue
        records.append(record)
    return records


def require_keys(obj: dict[str, Any], keys: list[str], label: str, errors: list[str]) -> None:
    missing = [key for key in keys if key not in obj]
    if missing:
        errors.append(f"{label} missing keys: {', '.join(missing)}")


def require_string(
    obj: dict[str, Any],
    key: str,
    label: str,
    errors: list[str],
    allowed: set[str] | None = None,
    nullable: bool = False,
) -> None:
    value = obj.get(key)
    if value is None and nullable:
        return
    if not isinstance(value, str) or not value:
        errors.append(f"{label}.{key} must be a non-empty string")
        return
    if allowed and value not in allowed:
        errors.append(f"{label}.{key} must be one of: {', '.join(sorted(allowed))}")


def require_int(obj: dict[str, Any], key: str, label: str, errors: list[str], minimum: int = 0) -> None:
    value = obj.get(key)
    if not isinstance(value, int) or value < minimum:
        errors.append(f"{label}.{key} must be an integer >= {minimum}")


def require_bool(obj: dict[str, Any], key: str, label: str, errors: list[str]) -> None:
    if not isinstance(obj.get(key), bool):
        errors.append(f"{label}.{key} must be a boolean")


def require_list(obj: dict[str, Any], key: str, label: str, errors: list[str]) -> list[Any]:
    value = obj.get(key)
    if not isinstance(value, list):
        errors.append(f"{label}.{key} must be a list")
        return []
    return value


def require_object(obj: dict[str, Any], key: str, label: str, errors: list[str]) -> dict[str, Any]:
    value = obj.get(key)
    if not isinstance(value, dict):
        errors.append(f"{label}.{key} must be an object")
        return {}
    return value


def validate_run(path: Path, errors: list[str]) -> None:
    data = load_json(path, errors)
    if data is None:
        return
    require_keys(
        data,
        ["schema_version", "run_id", "pilot_class", "status", "current_heartbeat", "max_heartbeats", "updated_at"],
        str(path),
        errors,
    )
    require_string(data, "schema_version", str(path), errors, {"clawwars/vnext/run@1"})
    require_string(data, "run_id", str(path), errors)
    require_string(data, "pilot_class", str(path), errors, {"pilot_a", "pilot_b", "pilot_c", "pilot_d", "unassigned"})
    require_string(data, "status", str(path), errors, {"not_started", "in_progress", "paused", "completed", "blocked"})
    require_int(data, "current_heartbeat", str(path), errors, minimum=0)
    require_int(data, "max_heartbeats", str(path), errors, minimum=1)
    require_string(data, "updated_at", str(path), errors)


def validate_preflight(path: Path, errors: list[str]) -> None:
    data = load_json(path, errors)
    if data is None:
        return
    require_keys(data, ["schema_version", "checked_at", "passed", "checks"], str(path), errors)
    require_string(data, "schema_version", str(path), errors, {"clawwars/vnext/preflight@1"})
    require_string(data, "checked_at", str(path), errors)
    require_bool(data, "passed", str(path), errors)
    checks = require_list(data, "checks", str(path), errors)
    for index, check in enumerate(checks, start=1):
        if not isinstance(check, dict):
            errors.append(f"{path}.checks[{index}] must be an object")
            continue
        require_keys(check, ["name", "passed", "detail"], f"{path}.checks[{index}]", errors)
        require_string(check, "name", f"{path}.checks[{index}]", errors)
        require_bool(check, "passed", f"{path}.checks[{index}]", errors)
        require_string(check, "detail", f"{path}.checks[{index}]", errors)


def validate_distribution_policy(path: Path, errors: list[str]) -> None:
    data = load_json(path, errors)
    if data is None:
        return
    require_keys(data, ["schema_version", "default_surface", "additional_surface", "surfaces"], str(path), errors)
    require_string(data, "schema_version", str(path), errors, {"clawwars/vnext/distribution_policy@1"})
    require_string(data, "default_surface", str(path), errors)
    require_string(data, "additional_surface", str(path), errors)
    surfaces = require_list(data, "surfaces", str(path), errors)
    surface_ids: set[str] = set()
    for index, surface in enumerate(surfaces, start=1):
        if not isinstance(surface, dict):
            errors.append(f"{path}.surfaces[{index}] must be an object")
            continue
        require_keys(surface, ["id", "platform", "target_rule", "status", "notes"], f"{path}.surfaces[{index}]", errors)
        require_string(surface, "id", f"{path}.surfaces[{index}]", errors)
        require_string(surface, "platform", f"{path}.surfaces[{index}]", errors)
        require_string(surface, "target_rule", f"{path}.surfaces[{index}]", errors)
        require_string(surface, "status", f"{path}.surfaces[{index}]", errors, {"enabled", "disabled"})
        require_string(surface, "notes", f"{path}.surfaces[{index}]", errors)
        surface_id = surface.get("id")
        if isinstance(surface_id, str):
            surface_ids.add(surface_id)
    if data.get("default_surface") not in surface_ids:
        errors.append(f"{path}.default_surface must match a declared surface id")
    if data.get("additional_surface") not in surface_ids:
        errors.append(f"{path}.additional_surface must match a declared surface id")
    if data.get("default_surface") == data.get("additional_surface"):
        errors.append(f"{path}.additional_surface must differ from default_surface")


def validate_gates(path: Path, errors: list[str]) -> None:
    data = load_json(path, errors)
    if data is None:
        return
    require_keys(data, ["schema_version", "gates"], str(path), errors)
    require_string(data, "schema_version", str(path), errors, {"clawwars/vnext/gates@1"})
    gates = require_object(data, "gates", str(path), errors)
    for gate_name in ("G1", "G2", "G3", "G4"):
        gate = gates.get(gate_name)
        if not isinstance(gate, dict):
            errors.append(f"{path}.gates.{gate_name} must be an object")
            continue
        require_keys(gate, ["status", "description", "evidence"], f"{path}.gates.{gate_name}", errors)
        require_string(gate, "status", f"{path}.gates.{gate_name}", errors, {"pending", "pass", "fail", "partial", "blocked"})
        require_string(gate, "description", f"{path}.gates.{gate_name}", errors)
        evidence = gate.get("evidence")
        if not isinstance(evidence, list):
            errors.append(f"{path}.gates.{gate_name}.evidence must be a list")


def validate_deployment(path: Path, errors: list[str]) -> None:
    data = load_json(path, errors)
    if data is None:
        return
    require_keys(data, ["schema_version", "status", "product_lane"], str(path), errors)
    require_string(data, "schema_version", str(path), errors, {"clawwars/vnext/deployment@1"})
    require_string(data, "status", str(path), errors, {"unconfigured", "configured"})
    lane = require_object(data, "product_lane", str(path), errors)
    require_keys(
        lane,
        ["kind", "mode", "repository", "owner", "branch", "site_path", "public_url", "url_verified", "required_env_vars", "verified_at"],
        f"{path}.product_lane",
        errors,
    )
    require_string(lane, "kind", f"{path}.product_lane", errors, {"unconfigured", "github_pages"})
    require_string(lane, "mode", f"{path}.product_lane", errors, {"branch", "github_actions"})
    for key in ("repository", "owner", "public_url", "verified_at"):
        if lane.get(key) is not None and not isinstance(lane.get(key), str):
            errors.append(f"{path}.product_lane.{key} must be null or a string")
    require_string(lane, "branch", f"{path}.product_lane", errors)
    require_string(lane, "site_path", f"{path}.product_lane", errors)
    require_bool(lane, "url_verified", f"{path}.product_lane", errors)
    env_vars = require_list(lane, "required_env_vars", f"{path}.product_lane", errors)
    for index, entry in enumerate(env_vars, start=1):
        if not isinstance(entry, str) or not entry:
            errors.append(f"{path}.product_lane.required_env_vars[{index}] must be a non-empty string")
    if data.get("status") == "configured" and lane.get("kind") != "github_pages":
        errors.append(f"{path}.product_lane.kind must be github_pages when deployment status is configured")
    if data.get("status") == "configured" and not env_vars:
        errors.append(f"{path}.product_lane.required_env_vars must not be empty when deployment status is configured")


def validate_verification_config(path: Path, errors: list[str]) -> None:
    data = load_json(path, errors)
    if data is None:
        return
    require_keys(data, ["schema_version", "status", "lane"], str(path), errors)
    require_string(data, "schema_version", str(path), errors, {"clawwars/vnext/verification_config@1"})
    require_string(data, "status", str(path), errors, {"unconfigured", "configured"})
    lane = require_object(data, "lane", str(path), errors)
    require_keys(
        lane,
        [
            "kind",
            "readiness",
            "write_endpoint",
            "read_path",
            "read_format",
            "summary_path",
            "client_event_contract",
            "sync_contract",
            "env_vars",
            "pii_policy",
            "verified_user_runs_require_lane",
        ],
        f"{path}.lane",
        errors,
    )
    require_string(lane, "kind", f"{path}.lane", errors, {"unconfigured", "operator_managed_collector"})
    require_string(lane, "readiness", f"{path}.lane", errors, {"pending_operator_provisioning", "ready"})
    for key in ("write_endpoint", "read_path"):
        if lane.get(key) is not None and not isinstance(lane.get(key), str):
            errors.append(f"{path}.lane.{key} must be null or a string")
    require_string(lane, "read_format", f"{path}.lane", errors, {"json", "jsonl"})
    require_string(lane, "summary_path", f"{path}.lane", errors)
    client_contract = require_object(lane, "client_event_contract", f"{path}.lane", errors)
    require_keys(
        client_contract,
        ["event_type", "anonymous_user_id_field", "timestamp_field", "metadata_rules"],
        f"{path}.lane.client_event_contract",
        errors,
    )
    require_string(client_contract, "event_type", f"{path}.lane.client_event_contract", errors, {"core_action_completed"})
    require_string(client_contract, "anonymous_user_id_field", f"{path}.lane.client_event_contract", errors)
    require_string(client_contract, "timestamp_field", f"{path}.lane.client_event_contract", errors)
    require_string(client_contract, "metadata_rules", f"{path}.lane.client_event_contract", errors)
    sync_contract = require_object(lane, "sync_contract", f"{path}.lane", errors)
    require_keys(sync_contract, ["import_format", "import_command", "derive_command"], f"{path}.lane.sync_contract", errors)
    require_string(sync_contract, "import_format", f"{path}.lane.sync_contract", errors, {"json", "jsonl"})
    require_string(sync_contract, "import_command", f"{path}.lane.sync_contract", errors)
    require_string(sync_contract, "derive_command", f"{path}.lane.sync_contract", errors)
    env_vars = require_list(lane, "env_vars", f"{path}.lane", errors)
    for index, entry in enumerate(env_vars, start=1):
        if not isinstance(entry, str) or not entry:
            errors.append(f"{path}.lane.env_vars[{index}] must be a non-empty string")
    require_string(lane, "pii_policy", f"{path}.lane", errors, {"anonymous_only"})
    require_bool(lane, "verified_user_runs_require_lane", f"{path}.lane", errors)
    if data.get("status") == "configured" and lane.get("kind") != "operator_managed_collector":
        errors.append(f"{path}.lane.kind must be operator_managed_collector when verification status is configured")
    if data.get("status") == "configured" and not env_vars:
        errors.append(f"{path}.lane.env_vars must not be empty when verification status is configured")


def validate_analytics_summary(path: Path, errors: list[str]) -> None:
    data = load_json(path, errors)
    if data is None:
        return
    require_keys(data, ["schema_version", "verified_user_count", "event_count", "last_event_at", "sources"], str(path), errors)
    require_string(data, "schema_version", str(path), errors, {"clawwars/vnext/analytics_summary@1"})
    require_int(data, "verified_user_count", str(path), errors, minimum=0)
    require_int(data, "event_count", str(path), errors, minimum=0)
    if data.get("last_event_at") is not None and not isinstance(data.get("last_event_at"), str):
        errors.append(f"{path}.last_event_at must be null or a string")
    sources = data.get("sources")
    if not isinstance(sources, dict):
        errors.append(f"{path}.sources must be an object")
    else:
        for key, value in sources.items():
            if not isinstance(key, str) or not key:
                errors.append(f"{path}.sources keys must be non-empty strings")
            if not isinstance(value, int) or value < 0:
                errors.append(f"{path}.sources[{key}] must be an integer >= 0")


def validate_tool_grants(path: Path, errors: list[str]) -> None:
    data = load_json(path, errors)
    if data is None:
        return
    require_keys(data, ["schema_version", "grants"], str(path), errors)
    require_string(data, "schema_version", str(path), errors, {"clawwars/vnext/tool_grants@1"})
    grants = require_list(data, "grants", str(path), errors)
    for index, grant in enumerate(grants, start=1):
        if not isinstance(grant, dict):
            errors.append(f"{path}.grants[{index}] must be an object")
            continue
        require_keys(grant, ["id", "tool", "status"], f"{path}.grants[{index}]", errors)
        require_string(grant, "id", f"{path}.grants[{index}]", errors)
        require_string(grant, "tool", f"{path}.grants[{index}]", errors)
        require_string(
            grant,
            "status",
            f"{path}.grants[{index}]",
            errors,
            {"pending_review", "auto_granted", "granted", "denied", "invalid"},
        )


def validate_outreach_queue(path: Path, errors: list[str]) -> None:
    data = load_json(path, errors)
    if data is None:
        return
    require_keys(data, ["schema_version", "items"], str(path), errors)
    require_string(data, "schema_version", str(path), errors, {"clawwars/vnext/outreach_queue@1"})
    items = require_list(data, "items", str(path), errors)
    for index, item in enumerate(items, start=1):
        if not isinstance(item, dict):
            errors.append(f"{path}.items[{index}] must be an object")
            continue
        require_keys(item, ["id", "heartbeat", "status", "platform", "target", "content"], f"{path}.items[{index}]", errors)
        require_string(item, "id", f"{path}.items[{index}]", errors)
        require_int(item, "heartbeat", f"{path}.items[{index}]", errors, minimum=1)
        require_string(
            item,
            "status",
            f"{path}.items[{index}]",
            errors,
            {"pending_review", "approved_draft", "edit_required", "denied", "posted", "failed_to_post"},
        )
        require_string(item, "platform", f"{path}.items[{index}]", errors)
        require_string(item, "target", f"{path}.items[{index}]", errors)
        require_string(item, "content", f"{path}.items[{index}]", errors)


def validate_outreach_receipts(path: Path, errors: list[str]) -> None:
    data = load_json(path, errors)
    if data is None:
        return
    require_keys(data, ["schema_version", "receipts"], str(path), errors)
    require_string(data, "schema_version", str(path), errors, {"clawwars/vnext/outreach_receipts@1"})
    receipts = require_list(data, "receipts", str(path), errors)
    for index, receipt in enumerate(receipts, start=1):
        if not isinstance(receipt, dict):
            errors.append(f"{path}.receipts[{index}] must be an object")
            continue
        require_keys(
            receipt,
            ["item_id", "receipt_type", "receipt_value", "recorded_at", "validated"],
            f"{path}.receipts[{index}]",
            errors,
        )
        require_string(receipt, "item_id", f"{path}.receipts[{index}]", errors)
        require_string(
            receipt,
            "receipt_type",
            f"{path}.receipts[{index}]",
            errors,
            {"public_url", "post_id", "screenshot_path", "operator_confirmation"},
        )
        require_string(receipt, "receipt_value", f"{path}.receipts[{index}]", errors)
        require_string(receipt, "recorded_at", f"{path}.receipts[{index}]", errors)
        require_bool(receipt, "validated", f"{path}.receipts[{index}]", errors)


def validate_verification_events(path: Path, errors: list[str]) -> None:
    records = load_jsonl(path, errors)
    if records is None:
        return
    for index, record in enumerate(records, start=1):
        label = f"{path}:{index}"
        require_keys(record, ["schema_version", "event_id", "event_type", "anonymous_user_id", "occurred_at", "source", "metadata"], label, errors)
        require_string(record, "schema_version", label, errors, {"clawwars/vnext/verification_event@1"})
        require_string(record, "event_id", label, errors)
        require_string(record, "event_type", label, errors, {"core_action_completed"})
        require_string(record, "anonymous_user_id", label, errors)
        require_string(record, "occurred_at", label, errors)
        require_string(record, "source", label, errors)
        if not isinstance(record.get("metadata"), dict):
            errors.append(f"{label}.metadata must be an object")


def validate_operator_events(path: Path, errors: list[str]) -> None:
    records = load_jsonl(path, errors)
    if records is None:
        return
    for index, record in enumerate(records, start=1):
        label = f"{path}:{index}"
        require_keys(record, ["event_id", "action", "actor", "occurred_at", "details"], label, errors)
        require_string(record, "event_id", label, errors)
        require_string(record, "action", label, errors)
        require_string(record, "actor", label, errors)
        require_string(record, "occurred_at", label, errors)
        if not isinstance(record.get("details"), dict):
            errors.append(f"{label}.details must be an object")


def validate_state_dir(state_dir: Path) -> list[str]:
    errors: list[str] = []
    if not state_dir.exists():
        return [f"missing directory: {state_dir}"]

    validate_run(state_dir / "run.json", errors)
    validate_preflight(state_dir / "preflight.json", errors)
    validate_distribution_policy(state_dir / "distribution_policy.json", errors)
    validate_gates(state_dir / "gates.json", errors)
    validate_deployment(state_dir / "deployment.json", errors)
    validate_verification_config(state_dir / "verification_config.json", errors)
    validate_analytics_summary(state_dir / "analytics_summary.json", errors)
    validate_tool_grants(state_dir / "tool_grants.json", errors)
    validate_outreach_queue(state_dir / "outreach_queue.json", errors)
    validate_outreach_receipts(state_dir / "outreach_receipts.json", errors)
    validate_verification_events(state_dir / "verification_events.jsonl", errors)
    validate_operator_events(state_dir / "operator_events.jsonl", errors)

    tool_requests_dir = state_dir / "tool_requests"
    if not tool_requests_dir.is_dir():
        errors.append(f"missing directory: {tool_requests_dir}")
    return errors


def main() -> int:
    errors = validate_state_dir(STATE_DIR)
    if errors:
        return fail(errors)

    print(f"State scaffold is valid: {STATE_DIR}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
