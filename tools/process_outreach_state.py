#!/usr/bin/env python3
"""Manage canonical outreach state, receipt-backed posting, and rendered summaries."""

from __future__ import annotations

import argparse
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


QUEUE_SCHEMA = "clawwars/vnext/outreach_queue@1"
RECEIPT_SCHEMA = "clawwars/vnext/outreach_receipts@1"
POLICY_SCHEMA = "clawwars/vnext/distribution_policy@1"
VALID_RECEIPT_TYPES = {"public_url", "post_id", "screenshot_path", "operator_confirmation"}
TERMINAL_ITEM_STATUSES = {"posted", "failed_to_post"}


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def load_json(path: Path, default: dict[str, Any]) -> dict[str, Any]:
    if not path.exists():
        return default
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


def save_jsonl(path: Path, records: list[dict[str, Any]]) -> None:
    if not records:
        path.write_text("", encoding="utf-8")
        return
    path.write_text("".join(json.dumps(record) + "\n" for record in records), encoding="utf-8")


def append_event(events_path: Path, action: str, actor: str, details: dict[str, Any], occurred_at: str | None = None) -> None:
    records = load_jsonl(events_path)
    timestamp = occurred_at or utc_now()
    records.append(
        {
            "event_id": f"{action}:{len(records) + 1}",
            "action": action,
            "actor": actor,
            "occurred_at": timestamp,
            "details": details,
        }
    )
    save_jsonl(events_path, records)


def normalize_review_decision(review_response: str) -> tuple[str, str]:
    first_line = review_response.splitlines()[0].strip()
    upper = first_line.upper()
    if upper == "APPROVE" or upper.startswith("APPROVE"):
        return "APPROVE", "approved_draft"
    if upper.startswith("EDIT"):
        return "EDIT", "edit_required"
    if upper.startswith("DENY"):
        return "DENY", "denied"
    raise ValueError(f"unrecognized reviewer decision: {first_line}")


def extract_outreach_section(plan_path: Path) -> str | None:
    text = plan_path.read_text(encoding="utf-8")
    match = re.search(r"^## Proposed Outreach\s*$([\s\S]*?)(?=^## |\Z)", text, flags=re.MULTILINE)
    if not match:
        return None
    section = match.group(1).strip()
    return section or None


def extract_labeled_value(section: str, label: str) -> str | None:
    pattern = rf"(?im)^(?:[-*]\s*)?(?:\*\*)?{re.escape(label)}(?:\*\*)?\s*:\s*(.+)$"
    match = re.search(pattern, section)
    if not match:
        return None
    return match.group(1).strip()


def parse_outreach_item(heartbeat: int, section: str) -> dict[str, Any]:
    platform = extract_labeled_value(section, "Platform") or "unspecified"
    target = extract_labeled_value(section, "Target") or "unspecified"
    content = extract_labeled_value(section, "Content") or section
    rationale = extract_labeled_value(section, "Why") or extract_labeled_value(section, "Rationale")
    return {
        "id": f"hb{heartbeat}-outreach-1",
        "heartbeat": heartbeat,
        "status": "pending_review",
        "platform": platform,
        "target": target,
        "content": content,
        "rationale": rationale,
        "raw_section": section,
    }


def load_distribution_policy(state_dir: Path) -> dict[str, Any]:
    policy = load_json(
        state_dir / "distribution_policy.json",
        {
            "schema_version": POLICY_SCHEMA,
            "default_surface": "reddit_public_post",
            "additional_surface": "hackernews_show_hn",
            "surfaces": [
                {
                    "id": "reddit_public_post",
                    "platform": "reddit",
                    "target_rule": "non-empty public subreddit or thread target",
                    "status": "enabled",
                    "notes": "Baseline public Reddit posting surface.",
                },
                {
                    "id": "hackernews_show_hn",
                    "platform": "hackernews_show_hn",
                    "target_rule": "target must be exactly show-hn",
                    "status": "enabled",
                    "notes": "Narrow optional extension for a public Show HN submission.",
                },
            ],
        },
    )
    if policy.get("schema_version") != POLICY_SCHEMA:
        raise ValueError("distribution policy schema mismatch")
    return policy


def assign_surface(item: dict[str, Any], policy: dict[str, Any]) -> dict[str, Any]:
    surfaces = [surface for surface in policy.get("surfaces", []) if isinstance(surface, dict) and surface.get("status") == "enabled"]
    platform = item.get("platform")
    target = str(item.get("target", "")).strip().lower()

    if platform == "reddit":
        if not any(surface.get("id") == "reddit_public_post" for surface in surfaces):
            raise ValueError("reddit_public_post is not enabled in distribution_policy.json")
        item["surface"] = "reddit_public_post"
        return item

    if platform == "hackernews_show_hn":
        if not any(surface.get("id") == "hackernews_show_hn" for surface in surfaces):
            raise ValueError("hackernews_show_hn is not enabled in distribution_policy.json")
        if target != "show-hn":
            raise ValueError("hackernews_show_hn requires Target: show-hn")
        item["surface"] = "hackernews_show_hn"
        return item

    raise ValueError(f"unsupported outreach platform: {platform}")


def render_outbox(markdown_path: Path, items: list[dict[str, Any]], receipts: list[dict[str, Any]]) -> None:
    receipt_by_item = {receipt["item_id"]: receipt for receipt in receipts if isinstance(receipt, dict) and receipt.get("validated")}
    status_order = [
        ("pending_review", "Pending Review"),
        ("approved_draft", "Approved Draft"),
        ("edit_required", "Edit Required"),
        ("denied", "Denied"),
        ("posted", "Posted"),
        ("failed_to_post", "Failed To Post"),
    ]

    lines = [
        "# OUTBOX",
        "",
        "Rendered from `state/outreach_queue.json` and `state/outreach_receipts.json`. Canonical outreach execution state lives under `state/`.",
        "",
    ]

    for status, title in status_order:
        lines.append(f"## {title}")
        subset = [item for item in items if item.get("status") == status]
        if not subset:
            lines.append("_(none)_")
            lines.append("")
            continue
        for item in sorted(subset, key=lambda entry: (entry.get("heartbeat") or 0, entry.get("id", ""))):
            lines.append(f"### {item.get('id', '<no-id>')}")
            lines.append(f"**Heartbeat**: {item.get('heartbeat')}")
            if item.get("surface"):
                lines.append(f"**Surface**: {item.get('surface')}")
            lines.append(f"**Platform**: {item.get('platform')}")
            lines.append(f"**Target**: {item.get('target')}")
            lines.append(f"**Status**: {item.get('status')}")
            if item.get("review_decision"):
                lines.append(f"**Reviewer decision**: {item.get('review_decision')}")
            if item.get("reviewed_at"):
                lines.append(f"**Reviewed at**: {item.get('reviewed_at')}")
            if item.get("rationale"):
                lines.append(f"**Rationale**: {item.get('rationale')}")
            lines.append(f"**Content**: {item.get('content')}")
            receipt = receipt_by_item.get(item.get("id"))
            if receipt:
                lines.append(f"**Receipt**: {receipt.get('receipt_type')} -> {receipt.get('receipt_value')}")
            lines.append("")

    markdown_path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")


def render_operator_log(markdown_path: Path, records: list[dict[str, Any]]) -> None:
    lines = [
        "# OPERATOR LOG",
        "",
        "Rendered from `state/operator_events.jsonl`. Canonical operator and orchestrator audit events live under `state/`.",
        "",
        "| Timestamp | Actor | Action | Details |",
        "|-----------|-------|--------|---------|",
    ]
    if not records:
        lines.append("| - | - | - | No events recorded |")
    else:
        for record in records:
            details = record.get("details", {})
            if isinstance(details, dict):
                detail_text = "; ".join(f"{key}={value}" for key, value in details.items()) or "-"
            else:
                detail_text = str(details)
            lines.append(
                f"| {record.get('occurred_at', '-')} | {record.get('actor', '-')} | {record.get('action', '-')} | {detail_text} |"
            )
    lines.append("")
    markdown_path.write_text("\n".join(lines), encoding="utf-8")


def render_from_state(state_dir: Path, outbox_target: Path, operator_log_target: Path) -> None:
    queue = load_json(state_dir / "outreach_queue.json", {"schema_version": QUEUE_SCHEMA, "items": []})
    receipts = load_json(state_dir / "outreach_receipts.json", {"schema_version": RECEIPT_SCHEMA, "receipts": []})
    operator_events = load_jsonl(state_dir / "operator_events.jsonl")
    render_outbox(outbox_target, queue.get("items", []), receipts.get("receipts", []))
    render_operator_log(operator_log_target, operator_events)


def review_plan(state_dir: Path, heartbeat: int, plan_file: Path, review_response: str, outbox_target: Path, operator_log_target: Path) -> int:
    section = extract_outreach_section(plan_file)
    if section is None:
        render_from_state(state_dir, outbox_target, operator_log_target)
        return 0

    policy = load_distribution_policy(state_dir)
    queue_path = state_dir / "outreach_queue.json"
    queue = load_json(queue_path, {"schema_version": QUEUE_SCHEMA, "items": []})
    items = queue.setdefault("items", [])
    item = assign_surface(parse_outreach_item(heartbeat, section), policy)
    review_decision, status = normalize_review_decision(review_response)
    item["status"] = status
    item["review_decision"] = review_decision
    item["review_response"] = review_response
    item["reviewed_at"] = utc_now()

    existing = next((entry for entry in items if entry.get("id") == item["id"]), None)
    if existing is not None:
        preserved_status = existing.get("status")
        if preserved_status in TERMINAL_ITEM_STATUSES:
            item["status"] = preserved_status
            if existing.get("posted_at"):
                item["posted_at"] = existing["posted_at"]
        existing.update(item)
    else:
        items.append(item)

    save_json(queue_path, queue)
    append_event(
        state_dir / "operator_events.jsonl",
        action="outreach_reviewed",
        actor="orchestrator",
        details={
            "item_id": item["id"],
            "decision": review_decision,
            "status": item["status"],
        },
        occurred_at=item["reviewed_at"],
    )
    render_from_state(state_dir, outbox_target, operator_log_target)
    return 0


def validate_receipt_value(receipt_type: str, receipt_value: str) -> None:
    if receipt_type not in VALID_RECEIPT_TYPES:
        raise ValueError(f"receipt_type must be one of: {', '.join(sorted(VALID_RECEIPT_TYPES))}")
    if not receipt_value.strip():
        raise ValueError("receipt_value must be non-empty")
    if receipt_type == "public_url" and not re.match(r"^https?://", receipt_value):
        raise ValueError("public_url receipts must start with http:// or https://")
    if receipt_type == "screenshot_path" and not Path(receipt_value).exists():
        raise ValueError("screenshot_path receipt must point to an existing file")


def record_receipt(
    state_dir: Path,
    item_id: str,
    receipt_type: str,
    receipt_value: str,
    outbox_target: Path,
    operator_log_target: Path,
) -> int:
    queue_path = state_dir / "outreach_queue.json"
    receipts_path = state_dir / "outreach_receipts.json"
    queue = load_json(queue_path, {"schema_version": QUEUE_SCHEMA, "items": []})
    receipts = load_json(receipts_path, {"schema_version": RECEIPT_SCHEMA, "receipts": []})
    items = queue.setdefault("items", [])
    item = next((entry for entry in items if entry.get("id") == item_id), None)

    if item is None:
        append_event(
            state_dir / "operator_events.jsonl",
            action="receipt_rejected",
            actor="orchestrator",
            details={"item_id": item_id, "reason": "unknown_item"},
        )
        render_from_state(state_dir, outbox_target, operator_log_target)
        raise ValueError(f"unknown outreach item: {item_id}")

    if item.get("status") != "approved_draft":
        append_event(
            state_dir / "operator_events.jsonl",
            action="receipt_rejected",
            actor="orchestrator",
            details={"item_id": item_id, "reason": f"item status is {item.get('status')}"},
        )
        render_from_state(state_dir, outbox_target, operator_log_target)
        raise ValueError(f"item {item_id} must be approved_draft before recording a receipt")

    validate_receipt_value(receipt_type, receipt_value)
    recorded_at = utc_now()
    append_event(
        state_dir / "operator_events.jsonl",
        action="receipt_submitted",
        actor="operator",
        details={
            "item_id": item_id,
            "receipt_type": receipt_type,
            "receipt_value": receipt_value,
        },
        occurred_at=recorded_at,
    )

    receipt_record = {
        "receipt_id": f"{item_id}:{receipt_type}",
        "item_id": item_id,
        "receipt_type": receipt_type,
        "receipt_value": receipt_value,
        "recorded_at": recorded_at,
        "validated": True,
    }

    receipt_entries = receipts.setdefault("receipts", [])
    existing_receipt = next((entry for entry in receipt_entries if entry.get("item_id") == item_id), None)
    if existing_receipt is not None:
        existing_receipt.update(receipt_record)
    else:
        receipt_entries.append(receipt_record)

    item["status"] = "posted"
    item["posted_at"] = recorded_at
    item["receipt_type"] = receipt_type
    item["receipt_value"] = receipt_value

    save_json(queue_path, queue)
    save_json(receipts_path, receipts)
    append_event(
        state_dir / "operator_events.jsonl",
        action="outreach_posted",
        actor="orchestrator",
        details={
            "item_id": item_id,
            "receipt_type": receipt_type,
            "to_status": "posted",
        },
        occurred_at=recorded_at,
    )
    render_from_state(state_dir, outbox_target, operator_log_target)
    return 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--state-dir", default=str(Path(__file__).resolve().parents[1] / "state"))
    parser.add_argument("--outbox-target", default=str(Path(__file__).resolve().parents[1] / "OUTBOX.md"))
    parser.add_argument("--operator-log-target", default=str(Path(__file__).resolve().parents[1] / "OPERATOR_LOG.md"))
    subparsers = parser.add_subparsers(dest="command", required=True)

    review_parser = subparsers.add_parser("review-plan")
    review_parser.add_argument("--heartbeat", type=int, required=True)
    review_parser.add_argument("--plan-file", required=True)
    review_parser.add_argument("--review-response", required=True)

    receipt_parser = subparsers.add_parser("record-receipt")
    receipt_parser.add_argument("--item-id", required=True)
    receipt_parser.add_argument("--receipt-type", required=True)
    receipt_parser.add_argument("--receipt-value", required=True)

    subparsers.add_parser("render")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    state_dir = Path(args.state_dir).resolve()
    outbox_target = Path(args.outbox_target).resolve()
    operator_log_target = Path(args.operator_log_target).resolve()

    if args.command == "review-plan":
        return review_plan(
            state_dir=state_dir,
            heartbeat=args.heartbeat,
            plan_file=Path(args.plan_file).resolve(),
            review_response=args.review_response,
            outbox_target=outbox_target,
            operator_log_target=operator_log_target,
        )
    if args.command == "record-receipt":
        return record_receipt(
            state_dir=state_dir,
            item_id=args.item_id,
            receipt_type=args.receipt_type,
            receipt_value=args.receipt_value,
            outbox_target=outbox_target,
            operator_log_target=operator_log_target,
        )
    if args.command == "render":
        render_from_state(state_dir, outbox_target, operator_log_target)
        return 0
    raise ValueError(f"unsupported command: {args.command}")


if __name__ == "__main__":
    raise SystemExit(main())
