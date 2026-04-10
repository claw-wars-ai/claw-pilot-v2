#!/usr/bin/env python3
"""Preflight, gate enforcement, and machine-readable status for Claw Pilot vNext."""

from __future__ import annotations

import argparse
import json
import os
import shutil
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from validate_state import validate_state_dir


ROOT = Path(__file__).resolve().parents[1]
PREFLIGHT_SCHEMA = "clawwars/vnext/preflight@1"
REVIEWER_URL = "https://api.x.ai/v1/chat/completions"
GATE_DEADLINES = {"G1": 3, "G2": 6, "G3": 7, "G4": 8}
GATE_CLASSIFICATIONS = {
    "G1": "problem_selection_failure",
    "G2": "deployment_failure",
    "G3": "harness_distribution_failure",
    "G4": "harness_distribution_failure",
}


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def load_json(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return data


def save_json(path: Path, data: dict[str, Any]) -> None:
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    records: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        record = json.loads(line)
        if not isinstance(record, dict):
            raise ValueError(f"{path} must contain JSON objects per line")
        records.append(record)
    return records


def request_ok(url: str, method: str = "GET", timeout: int = 10, data: bytes | None = None, headers: dict[str, str] | None = None) -> tuple[bool, str]:
    req = urllib.request.Request(url, data=data, method=method, headers=headers or {})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as response:
            return 200 <= response.status < 400, f"HTTP {response.status}"
    except urllib.error.HTTPError as exc:
        return False, f"HTTP {exc.code}"
    except Exception as exc:  # pragma: no cover - exercised by environment
        return False, str(exc)


def reviewer_roundtrip(api_key: str, reviewer_model: str) -> tuple[bool, str]:
    payload = json.dumps(
        {
            "model": reviewer_model,
            "max_tokens": 1,
            "messages": [
                {"role": "system", "content": "Reply with OK."},
                {"role": "user", "content": "OK?"},
            ],
        }
    ).encode("utf-8")
    ok, detail = request_ok(
        REVIEWER_URL,
        method="POST",
        timeout=15,
        data=payload,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        },
    )
    if ok:
        return True, "reviewer round-trip succeeded"
    return False, f"reviewer round-trip failed: {detail}"


def verification_read_path_status(read_path: str | None) -> tuple[bool, str]:
    if not read_path:
        return False, "verification read_path is not configured"
    if read_path.startswith(("http://", "https://")):
        ok, detail = request_ok(read_path, method="GET", timeout=10)
        return (True, f"verification export reachable: {detail}") if ok else (False, f"verification export unreachable: {detail}")
    path = Path(read_path)
    if path.exists():
        return True, f"verification read path exists: {path}"
    if path.parent.exists():
        return True, f"verification read path is bootstrappable under existing directory: {path.parent}"
    return False, f"verification read path parent does not exist: {path.parent}"


def url_verification(public_url: str | None) -> tuple[bool, str]:
    if not public_url:
        return False, "public_url is not configured"
    if not public_url.startswith(("http://", "https://")):
        return False, "public_url must start with http:// or https://"
    ok, detail = request_ok(public_url, method="GET", timeout=10)
    return (True, f"public URL reachable: {detail}") if ok else (False, f"public URL check failed: {detail}")


def ensure_run_metadata(state_dir: Path, heartbeat: int | None = None) -> dict[str, Any]:
    run_path = state_dir / "run.json"
    run_data = load_json(run_path)
    if heartbeat is not None:
        run_data["current_heartbeat"] = heartbeat
    run_data["updated_at"] = utc_now()
    save_json(run_path, run_data)
    return run_data


def run_preflight(state_dir: Path, workspace: Path, reviewer_model: str) -> int:
    deployment = load_json(state_dir / "deployment.json")
    verification = load_json(state_dir / "verification_config.json")
    product_lane = deployment.get("product_lane", {})
    verification_lane = verification.get("lane", {})

    api_key = os.environ.get("XAI_API_KEY", "")
    required_envs = ["XAI_API_KEY"]
    required_envs.extend(product_lane.get("required_env_vars", []))
    required_envs.extend(verification_lane.get("env_vars", []))
    required_envs = sorted(dict.fromkeys(required_envs))

    checks: list[dict[str, Any]] = []

    def add_check(name: str, passed: bool, detail: str) -> None:
        checks.append({"name": name, "passed": passed, "detail": detail})

    openclaw_path = shutil.which("openclaw")
    add_check("openclaw_in_path", bool(openclaw_path), openclaw_path or "openclaw not found in PATH")

    add_check("reviewer_auth_present", bool(api_key), "XAI_API_KEY is set" if api_key else "XAI_API_KEY is missing")

    if api_key:
        passed, detail = reviewer_roundtrip(api_key, reviewer_model)
        add_check("reviewer_roundtrip", passed, detail)
    else:
        add_check("reviewer_roundtrip", False, "skipped because XAI_API_KEY is missing")

    missing_envs = [env_name for env_name in required_envs if not os.environ.get(env_name)]
    add_check(
        "required_secrets_present",
        not missing_envs,
        "all required env vars are present" if not missing_envs else f"missing env vars: {', '.join(missing_envs)}",
    )

    deployment_ok = (
        deployment.get("status") == "configured"
        and product_lane.get("kind") == "github_pages"
        and isinstance(product_lane.get("required_env_vars"), list)
        and len(product_lane.get("required_env_vars", [])) > 0
    )
    add_check(
        "product_lane_configured",
        deployment_ok,
        "GitHub Pages lane configured" if deployment_ok else "deployment.json is missing a configured GitHub Pages lane",
    )

    verification_ok = (
        verification.get("status") == "configured"
        and verification_lane.get("kind") == "operator_managed_collector"
    )
    add_check(
        "verification_lane_configured",
        verification_ok,
        "verification lane configured" if verification_ok else "verification_config.json is missing the operator-managed collector lane",
    )

    read_path_ok, read_path_detail = verification_read_path_status(verification_lane.get("read_path"))
    add_check("verification_read_path", read_path_ok, read_path_detail)

    workspace_ok = workspace.exists() and workspace.is_dir()
    workspace_objective = workspace / "OBJECTIVE.md"
    workspace_objective_ok = workspace_objective.exists() and workspace_objective.is_file()
    add_check(
        "workspace_objective_seeded",
        workspace_objective_ok,
        f"workspace objective exists: {workspace_objective}" if workspace_objective_ok else f"missing workspace objective: {workspace_objective}",
    )
    state_ok = state_dir.exists() and state_dir.is_dir()
    state_errors = validate_state_dir(state_dir) if state_ok else ["state directory missing"]
    combined_ok = workspace_ok and workspace_objective_ok and state_ok and not state_errors
    if not workspace_ok:
        detail = f"workspace directory missing: {workspace}"
    elif not workspace_objective_ok:
        detail = f"workspace objective missing: {workspace_objective}"
    elif not state_ok:
        detail = f"state directory missing: {state_dir}"
    elif state_errors:
        detail = "; ".join(state_errors)
    else:
        detail = "workspace and state directories exist and canonical state validates"
    add_check("workspace_and_state_valid", combined_ok, detail)

    passed = all(check["passed"] for check in checks)
    payload = {
        "schema_version": PREFLIGHT_SCHEMA,
        "checked_at": utc_now(),
        "passed": passed,
        "checks": checks,
    }
    save_json(state_dir / "preflight.json", payload)
    ensure_run_metadata(state_dir)
    return 0 if passed else 1


def update_gates(state_dir: Path) -> int:
    gates_path = state_dir / "gates.json"
    deployment_path = state_dir / "deployment.json"
    analytics_path = state_dir / "analytics_summary.json"
    deployment = load_json(deployment_path)
    gates = load_json(gates_path)
    queue = load_json(state_dir / "outreach_queue.json")
    receipts = load_json(state_dir / "outreach_receipts.json")
    analytics = load_json(analytics_path)
    verification_events = load_jsonl(state_dir / "verification_events.jsonl")

    product_lane = deployment.get("product_lane", {})
    url_ok, url_detail = url_verification(product_lane.get("public_url"))
    product_lane["url_verified"] = url_ok
    product_lane["verified_at"] = utc_now() if url_ok else None
    deployment["product_lane"] = product_lane
    save_json(deployment_path, deployment)

    gate_data = gates.get("gates", {})
    g1 = gate_data.get("G1", {})
    if g1.get("status") == "pass":
        pass
    elif g1.get("evidence"):
        g1["status"] = "partial"
    gate_data["G1"] = g1

    gate_data["G2"] = {
        "status": "pass" if url_ok else "pending",
        "description": gate_data.get("G2", {}).get("description", "Public product deployed and URL verified."),
        "evidence": [url_detail] if url_detail else [],
    }

    receipt_ids = {receipt.get("item_id") for receipt in receipts.get("receipts", []) if receipt.get("validated")}
    posted_items = [item.get("id") for item in queue.get("items", []) if item.get("status") == "posted" and item.get("id") in receipt_ids]
    gate_data["G3"] = {
        "status": "pass" if posted_items else "pending",
        "description": gate_data.get("G3", {}).get("description", "At least one receipt-backed outreach item posted."),
        "evidence": posted_items,
    }

    verified_count = analytics.get("verified_user_count", 0)
    event_count = len([record for record in verification_events if record.get("event_type") == "core_action_completed"])
    evidence = [f"verified_user_count={verified_count}", f"event_count={event_count}"]
    gate_data["G4"] = {
        "status": "pass" if verified_count >= 1 and event_count >= 1 else "pending",
        "description": gate_data.get("G4", {}).get("description", "At least one verified external core action recorded."),
        "evidence": evidence,
    }

    gates["gates"] = gate_data
    save_json(gates_path, gates)
    ensure_run_metadata(state_dir)
    return 0


def status_payload(state_dir: Path, heartbeat: int, max_heartbeats: int, model: str, reviewer_model: str) -> dict[str, Any]:
    run = load_json(state_dir / "run.json")
    preflight = load_json(state_dir / "preflight.json")
    gates = load_json(state_dir / "gates.json")
    tool_grants = load_json(state_dir / "tool_grants.json")
    outreach = load_json(state_dir / "outreach_queue.json")
    analytics = load_json(state_dir / "analytics_summary.json")
    run["current_heartbeat"] = heartbeat
    run["max_heartbeats"] = max_heartbeats
    run["updated_at"] = utc_now()
    save_json(state_dir / "run.json", run)
    return {
        "heartbeat": heartbeat,
        "max_heartbeats": max_heartbeats,
        "model": model,
        "reviewer_model": reviewer_model,
        "run": run,
        "preflight": {
            "passed": preflight.get("passed"),
            "checked_at": preflight.get("checked_at"),
        },
        "gates": gates.get("gates", {}),
        "tool_requests": {
            "pending_review": len([grant for grant in tool_grants.get("grants", []) if grant.get("status") == "pending_review"]),
            "invalid": len([grant for grant in tool_grants.get("grants", []) if grant.get("status") == "invalid"]),
        },
        "outreach": {
            "approved_draft": len([item for item in outreach.get("items", []) if item.get("status") == "approved_draft"]),
            "posted": len([item for item in outreach.get("items", []) if item.get("status") == "posted"]),
        },
        "verification": analytics,
    }


def enforce_deadlines(state_dir: Path, next_heartbeat: int) -> int:
    gates = load_json(state_dir / "gates.json").get("gates", {})
    run_path = state_dir / "run.json"
    run = load_json(run_path)

    for gate_name, deadline in GATE_DEADLINES.items():
        if next_heartbeat <= deadline:
            continue
        gate = gates.get(gate_name, {})
        if gate.get("status") == "pass":
            continue
        run["status"] = "blocked"
        run["updated_at"] = utc_now()
        run["blocked_gate"] = gate_name
        run["blocked_after_heartbeat"] = deadline
        run["classification"] = GATE_CLASSIFICATIONS[gate_name]
        run["block_reason"] = f"{gate_name} missed at HB{deadline}"
        save_json(run_path, run)
        print(
            json.dumps(
                {
                    "allowed": False,
                    "next_heartbeat": next_heartbeat,
                    "blocked_gate": gate_name,
                    "deadline": deadline,
                    "gate_status": gate.get("status"),
                    "classification": GATE_CLASSIFICATIONS[gate_name],
                    "evidence": gate.get("evidence", []),
                },
                indent=2,
            )
        )
        return 1

    print(json.dumps({"allowed": True, "next_heartbeat": next_heartbeat}, indent=2))
    return 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--state-dir", default=str(ROOT / "state"))
    parser.add_argument("--workspace", default=str(ROOT / "pilot-workspace"))
    parser.add_argument("--reviewer-model", default="xai/grok-4-1-fast-non-reasoning")
    parser.add_argument("--heartbeat", type=int, default=0)
    parser.add_argument("--max-heartbeats", type=int, default=20)
    parser.add_argument("--model", default="xai/grok-4-1-fast-reasoning")
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("preflight")
    subparsers.add_parser("update-gates")
    subparsers.add_parser("status")
    deadline_parser = subparsers.add_parser("enforce-deadlines")
    deadline_parser.add_argument("--next-heartbeat", type=int, required=True)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    state_dir = Path(args.state_dir).resolve()
    workspace = Path(args.workspace).resolve()

    if args.command == "preflight":
        return run_preflight(state_dir=state_dir, workspace=workspace, reviewer_model=args.reviewer_model)
    if args.command == "update-gates":
        return update_gates(state_dir=state_dir)
    if args.command == "status":
        update_gates(state_dir)
        payload = status_payload(
            state_dir=state_dir,
            heartbeat=args.heartbeat,
            max_heartbeats=args.max_heartbeats,
            model=args.model,
            reviewer_model=args.reviewer_model,
        )
        print(json.dumps(payload, indent=2))
        return 0
    if args.command == "enforce-deadlines":
        return enforce_deadlines(state_dir=state_dir, next_heartbeat=args.next_heartbeat)
    raise ValueError(f"unsupported command: {args.command}")


if __name__ == "__main__":
    raise SystemExit(main())
