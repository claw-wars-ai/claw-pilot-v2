#!/usr/bin/env python3
"""Archive prior pilot runtime artifacts and reset canonical state for a fresh run."""

from __future__ import annotations

import argparse
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from process_outreach_state import render_from_state
from process_tool_requests import render_tool_grants


RUN_SCHEMA = "clawwars/vnext/run@1"
PREFLIGHT_SCHEMA = "clawwars/vnext/preflight@1"
GATES_SCHEMA = "clawwars/vnext/gates@1"
ANALYTICS_SCHEMA = "clawwars/vnext/analytics_summary@1"
QUEUE_SCHEMA = "clawwars/vnext/outreach_queue@1"
RECEIPTS_SCHEMA = "clawwars/vnext/outreach_receipts@1"


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def timestamp_slug() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def load_json(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return data


def save_json(path: Path, data: dict[str, Any]) -> None:
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


def archive_file(path: Path, destination_dir: Path) -> None:
    if path.exists():
        destination_dir.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, destination_dir / path.name)


def archive_runtime_state(state_dir: Path, archive_dir: Path) -> None:
    runtime_files = [
        "run.json",
        "preflight.json",
        "gates.json",
        "analytics_summary.json",
        "outreach_queue.json",
        "outreach_receipts.json",
        "verification_events.jsonl",
        "operator_events.jsonl",
        "tool_grants.json",
    ]
    for filename in runtime_files:
        archive_file(state_dir / filename, archive_dir)

    tool_requests_dir = state_dir / "tool_requests"
    if tool_requests_dir.exists():
        for path in sorted(tool_requests_dir.glob("*.json")):
            archive_file(path, archive_dir / "tool_requests")


def archive_workspace(workspace: Path, archive_dir: Path) -> None:
    if not workspace.exists():
        return
    for pattern in ("HB*_PLAN.md", "HB*_EXECUTION.md"):
        for path in workspace.glob(pattern):
            archive_file(path, archive_dir)

    logs_dir = workspace / "logs"
    if logs_dir.exists():
        archive_logs = archive_dir / "logs"
        archive_logs.mkdir(parents=True, exist_ok=True)
        for path in logs_dir.iterdir():
            if path.is_file():
                shutil.copy2(path, archive_logs / path.name)

    for filename in ("OBJECTIVE.md", "JOURNEY.md", "RESOURCES.md"):
        archive_file(workspace / filename, archive_dir)


def reset_run(state_dir: Path, run_id: str, pilot_class: str, max_heartbeats: int) -> None:
    save_json(
        state_dir / "run.json",
        {
            "schema_version": RUN_SCHEMA,
            "run_id": run_id,
            "pilot_class": pilot_class,
            "status": "not_started",
            "current_heartbeat": 0,
            "max_heartbeats": max_heartbeats,
            "updated_at": utc_now(),
            "objective": "Build and deploy a small self-serve web tool from scratch, then achieve 1 verified external core-action event.",
            "stretch_goal_verified_users": 3,
            "notes": "Fresh harness-qualification pilot. External claims require receipt-backed outreach and canonical verification events.",
        },
    )


def reset_preflight(state_dir: Path) -> None:
    save_json(
        state_dir / "preflight.json",
        {
            "schema_version": PREFLIGHT_SCHEMA,
            "checked_at": utc_now(),
            "passed": False,
            "checks": [
                {
                    "name": "not_run",
                    "passed": False,
                    "detail": "fresh run reset; preflight has not been executed yet",
                }
            ],
        },
    )


def reset_gates(state_dir: Path) -> None:
    save_json(
        state_dir / "gates.json",
        {
            "schema_version": GATES_SCHEMA,
            "gates": {
                "G1": {
                    "status": "pending",
                    "description": "Problem selected with external evidence.",
                    "evidence": [],
                },
                "G2": {
                    "status": "pending",
                    "description": "Public product deployed and URL verified.",
                    "evidence": ["public_url is not configured"],
                },
                "G3": {
                    "status": "pending",
                    "description": "At least one receipt-backed outreach item posted.",
                    "evidence": [],
                },
                "G4": {
                    "status": "pending",
                    "description": "At least one verified external core action recorded.",
                    "evidence": ["verified_user_count=0", "event_count=0"],
                },
            },
        },
    )


def reset_analytics(state_dir: Path) -> None:
    save_json(
        state_dir / "analytics_summary.json",
        {
            "schema_version": ANALYTICS_SCHEMA,
            "verified_user_count": 0,
            "event_count": 0,
            "last_event_at": None,
            "sources": {},
        },
    )


def reset_outreach_state(state_dir: Path) -> None:
    save_json(state_dir / "outreach_queue.json", {"schema_version": QUEUE_SCHEMA, "items": []})
    save_json(state_dir / "outreach_receipts.json", {"schema_version": RECEIPTS_SCHEMA, "receipts": []})
    (state_dir / "verification_events.jsonl").write_text("", encoding="utf-8")
    (state_dir / "operator_events.jsonl").write_text("", encoding="utf-8")


def reset_tool_requests(state_dir: Path) -> None:
    tool_requests_dir = state_dir / "tool_requests"
    tool_requests_dir.mkdir(parents=True, exist_ok=True)
    for path in tool_requests_dir.glob("*.json"):
        path.unlink()


def reset_tool_grants(state_dir: Path) -> None:
    grants = load_json(state_dir / "tool_grants.json")
    bootstrap = [
        grant
        for grant in grants.get("grants", [])
        if isinstance(grant, dict) and grant.get("source") == "bootstrap"
    ]
    save_json(state_dir / "tool_grants.json", {"schema_version": grants.get("schema_version"), "grants": bootstrap})


def reset_deployment_verification(state_dir: Path) -> None:
    deployment = load_json(state_dir / "deployment.json")
    lane = deployment.get("product_lane", {})
    lane["repository"] = None
    lane["owner"] = None
    lane["public_url"] = None
    lane["url_verified"] = False
    lane["verified_at"] = None
    deployment["product_lane"] = lane
    save_json(state_dir / "deployment.json", deployment)


def reset_workspace(workspace: Path, objective_template: Path) -> None:
    workspace.mkdir(parents=True, exist_ok=True)
    for pattern in ("HB*_PLAN.md", "HB*_EXECUTION.md"):
        for path in workspace.glob(pattern):
            path.unlink()

    lock_path = workspace / ".heartbeat.lock"
    if lock_path.exists():
        lock_path.unlink()

    logs_dir = workspace / "logs"
    if logs_dir.exists():
        shutil.rmtree(logs_dir)
    logs_dir.mkdir(parents=True, exist_ok=True)

    shutil.copy2(objective_template, workspace / "OBJECTIVE.md")
    (workspace / "JOURNEY.md").write_text("# JOURNEY\n\n_This fresh pilot has not started yet._\n", encoding="utf-8")
    (workspace / "RESOURCES.md").write_text("# RESOURCES\n\n_No validated resources yet._\n", encoding="utf-8")


def render_summaries(repo_root: Path, state_dir: Path) -> None:
    tool_grants = load_json(state_dir / "tool_grants.json")
    render_tool_grants(repo_root / "TOOL_GRANTS.md", tool_grants.get("grants", []))
    render_from_state(state_dir, repo_root / "OUTBOX.md", repo_root / "OPERATOR_LOG.md")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", default=str(Path(__file__).resolve().parents[1]))
    parser.add_argument("--state-dir")
    parser.add_argument("--workspace")
    parser.add_argument("--run-id")
    parser.add_argument("--pilot-class", default="pilot_a")
    parser.add_argument("--max-heartbeats", type=int, default=10)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    repo_root = Path(args.repo_root).resolve()
    state_dir = Path(args.state_dir).resolve() if args.state_dir else repo_root / "state"
    workspace = Path(args.workspace).resolve() if args.workspace else repo_root / "pilot-workspace"
    state_dir.mkdir(parents=True, exist_ok=True)
    workspace.mkdir(parents=True, exist_ok=True)

    previous_run_id = load_json(state_dir / "run.json").get("run_id", "unknown-run")
    archive_suffix = f"{timestamp_slug()}-{previous_run_id}"
    archive_runtime_state(state_dir, state_dir / "archive" / archive_suffix)
    archive_workspace(workspace, workspace / "archive" / archive_suffix)

    run_id = args.run_id or f"harness-pilot-{timestamp_slug().lower()}"
    reset_run(state_dir, run_id=run_id, pilot_class=args.pilot_class, max_heartbeats=args.max_heartbeats)
    reset_preflight(state_dir)
    reset_gates(state_dir)
    reset_analytics(state_dir)
    reset_outreach_state(state_dir)
    reset_tool_requests(state_dir)
    reset_tool_grants(state_dir)
    reset_deployment_verification(state_dir)
    reset_workspace(workspace, objective_template=repo_root / "OBJECTIVE.md")
    render_summaries(repo_root, state_dir)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
