# Canonical State

`state/` is the authoritative execution record for Claw Pilot vNext.

Rules:
- Structured files under `state/` are canonical.
- Markdown in the repo is human-facing only unless a prompt explicitly says otherwise.
- The orchestrator owns canonical state mutations.
- Operator actions are logged as inputs and receipts, not direct edits to canonical state.
- Fresh-run resets must go through the harness helper, not hand edits to the state files.

State layout:
- `run.json`: high-level pilot run metadata.
- `preflight.json`: latest hard-preflight result and per-check details.
- `distribution_policy.json`: enabled outreach surfaces and narrow extension policy.
- `gates.json`: machine-readable gate status.
- `deployment.json`: official public product deployment lane config and URL verification status.
- `verification_config.json`: official shared verification lane contract for verified-user pilots.
- `analytics_summary.json`: derived usage summary from canonical verification data.
- `tool_grants.json`: canonical tool grant record.
- `outreach_queue.json`: canonical outreach review and execution queue.
- `outreach_receipts.json`: validated posting receipts.
- `verification_events.jsonl`: append-only verification events.
- `operator_events.jsonl`: append-only operator and orchestrator audit log.
- `tool_requests/`: structured tool requests live here as one JSON file per request.
- `archive/`: archived runtime state snapshots from prior runs.

Validation and runtime helpers:
```bash
python tools/reset_pilot_run.py --pilot-class pilot_a
python tools/orchestrator_state.py preflight
python tools/orchestrator_state.py update-gates
python tools/orchestrator_state.py enforce-deadlines --next-heartbeat 1
python tools/validate_state.py
python tools/process_tool_requests.py
python tools/process_outreach_state.py render
python tools/verification_events.py init
python tools/verification_events.py append-synthetic --user-seed demo-user
```

Lane policy:
- Product deploy lane: GitHub Pages only.
- Verification lane: one shared operator-managed collector endpoint reused across pilots.
- GitHub Pages alone is not sufficient for verified-user measurement because it cannot host the event write collector.
- Additional distribution surface extension: `hackernews_show_hn` only.
