#!/usr/bin/env python3
"""Helpers for append-only verification events and derived user counts."""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


EVENT_SCHEMA_VERSION = "clawwars/vnext/verification_event@1"
SUMMARY_SCHEMA_VERSION = "clawwars/vnext/analytics_summary@1"
EVENT_TYPE = "core_action_completed"


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
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        record = json.loads(line)
        if not isinstance(record, dict):
            raise ValueError(f"{path}:{line_number} must be a JSON object")
        records.append(record)
    return records


def save_jsonl(path: Path, records: list[dict[str, Any]]) -> None:
    if not records:
        path.write_text("", encoding="utf-8")
        return
    path.write_text("".join(json.dumps(record) + "\n" for record in records), encoding="utf-8")


def anonymous_user_id(seed: str) -> str:
    digest = hashlib.sha256(seed.encode("utf-8")).hexdigest()
    return f"anon_{digest[:16]}"


def make_event(*, anonymous_id: str, source: str, occurred_at: str | None = None, metadata: dict[str, Any] | None = None) -> dict[str, Any]:
    timestamp = occurred_at or utc_now()
    seed = f"{anonymous_id}:{timestamp}:{source}:{EVENT_TYPE}"
    return {
        "schema_version": EVENT_SCHEMA_VERSION,
        "event_id": hashlib.sha256(seed.encode("utf-8")).hexdigest()[:24],
        "event_type": EVENT_TYPE,
        "anonymous_user_id": anonymous_id,
        "occurred_at": timestamp,
        "source": source,
        "metadata": metadata or {},
    }


def init_log(events_path: Path, summary_path: Path) -> int:
    events_path.parent.mkdir(parents=True, exist_ok=True)
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    if not events_path.exists():
        events_path.write_text("", encoding="utf-8")
    if not summary_path.exists():
        save_json(
            summary_path,
            {
                "schema_version": SUMMARY_SCHEMA_VERSION,
                "verified_user_count": 0,
                "event_count": 0,
                "last_event_at": None,
                "sources": {},
            },
        )
    return 0


def append_event(events_path: Path, summary_path: Path, event: dict[str, Any]) -> int:
    records = load_jsonl(events_path)
    records.append(event)
    save_jsonl(events_path, records)
    derive_summary(events_path, summary_path)
    return 0


def append_synthetic(events_path: Path, summary_path: Path, user_seed: str, source: str) -> int:
    event = make_event(anonymous_id=anonymous_user_id(user_seed), source=source, metadata={"synthetic": True})
    return append_event(events_path, summary_path, event)


def import_events(events_path: Path, summary_path: Path, input_path: Path) -> int:
    imported: list[dict[str, Any]]
    if input_path.suffix.lower() == ".json":
        payload = json.loads(input_path.read_text(encoding="utf-8"))
        if isinstance(payload, dict):
            imported = [payload]
        elif isinstance(payload, list):
            imported = [entry for entry in payload if isinstance(entry, dict)]
        else:
            raise ValueError(f"{input_path} must contain a JSON object or array")
    else:
        imported = load_jsonl(input_path)

    records = load_jsonl(events_path)
    records.extend(imported)
    save_jsonl(events_path, records)
    derive_summary(events_path, summary_path)
    return 0


def derive_summary(events_path: Path, summary_path: Path) -> int:
    records = load_jsonl(events_path)
    unique_users: set[str] = set()
    sources: dict[str, int] = {}
    last_event_at: str | None = None

    for record in records:
        if record.get("event_type") != EVENT_TYPE:
            continue
        user_id = record.get("anonymous_user_id")
        source = record.get("source", "unknown")
        occurred_at = record.get("occurred_at")
        if isinstance(user_id, str) and user_id:
            unique_users.add(user_id)
        if isinstance(source, str) and source:
            sources[source] = sources.get(source, 0) + 1
        if isinstance(occurred_at, str) and (last_event_at is None or occurred_at > last_event_at):
            last_event_at = occurred_at

    save_json(
        summary_path,
        {
            "schema_version": SUMMARY_SCHEMA_VERSION,
            "verified_user_count": len(unique_users),
            "event_count": len([record for record in records if record.get("event_type") == EVENT_TYPE]),
            "last_event_at": last_event_at,
            "sources": sources,
        },
    )
    return 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--events-path", default=str(Path(__file__).resolve().parents[1] / "state" / "verification_events.jsonl"))
    parser.add_argument("--summary-path", default=str(Path(__file__).resolve().parents[1] / "state" / "analytics_summary.json"))
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("init")

    append_parser = subparsers.add_parser("append-synthetic")
    append_parser.add_argument("--user-seed", required=True)
    append_parser.add_argument("--source", default="synthetic")

    import_parser = subparsers.add_parser("import")
    import_parser.add_argument("--input", required=True)

    subparsers.add_parser("derive-summary")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    events_path = Path(args.events_path).resolve()
    summary_path = Path(args.summary_path).resolve()

    if args.command == "init":
        return init_log(events_path, summary_path)
    if args.command == "append-synthetic":
        return append_synthetic(events_path, summary_path, user_seed=args.user_seed, source=args.source)
    if args.command == "import":
        return import_events(events_path, summary_path, Path(args.input).resolve())
    if args.command == "derive-summary":
        return derive_summary(events_path, summary_path)
    raise ValueError(f"unsupported command: {args.command}")


if __name__ == "__main__":
    raise SystemExit(main())
