# Claw Pilot vNext Agent Notes

This repo follows `CODEX_PROMPTS_REVISED.md` in order. Implement exactly one prompt at a time, starting from the latest integrated repo state.

## Core Rules
- Treat [`state/`](C:\Users\jdste\Coding Projects\claw-wars\state\README.md) as canonical execution state.
- Treat markdown files as human-facing summaries or operator docs unless a prompt explicitly says otherwise.
- Prefer structured inputs and outputs over prose parsing.
- Keep changes pragmatic, minimal, and testable.
- Add or update tests when behavior changes.
- Do not claim an execution loop is closed without receipt-backed or verification-backed evidence in canonical state.

## Role Boundaries
- Agent: works inside the workspace, drafts artifacts, and proposes state changes.
- Operator: approves sensitive actions and can supply receipt inputs.
- Orchestrator: validates inputs, mutates canonical state, renders markdown summaries, and enforces gates.
- Operator actions never directly edit canonical execution state.

## Prompt Discipline
- Prompt 1: scaffold canonical state, Codex guidance, and repo conventions.
- Prompt 2: define the official GitHub Pages deploy lane and shared verification lane.
- Prompt 3: move tool requests into structured canonical state.
- Prompt 4: add receipt-backed outreach state and operator relay.
- Prompt 5: add verification event handling and derived counts.
- Prompt 6: harden `heartbeat.sh` preflight and gate enforcement.
- Prompt 7: refresh human-facing docs and runbook.
- Prompt 8: add regressions for known failures and hard-loop invariants.
- Prompt 9: optional narrow executor or second distribution surface.

Do not pull later-prompt behavior forward unless it is required to complete the current prompt cleanly.

## Canonical State
Expected canonical files live under `state/`:
- `run.json`
- `gates.json`
- `deployment.json`
- `verification_config.json`
- `analytics_summary.json`
- `tool_grants.json`
- `outreach_queue.json`
- `outreach_receipts.json`
- `verification_events.jsonl`
- `operator_events.jsonl`
- `tool_requests/`

The scaffold and validator live in:
- [`state/README.md`](C:\Users\jdste\Coding Projects\claw-wars\state\README.md)
- [`tools/validate_state.py`](C:\Users\jdste\Coding Projects\claw-wars\tools\validate_state.py)

## Validation
Run the lightest checks that match the change:
- `python tools/orchestrator_state.py preflight`
- `python tools/orchestrator_state.py update-gates`
- `python tools/validate_state.py`
- `python tools/process_tool_requests.py`
- `python tools/process_outreach_state.py render`
- `python tools/verification_events.py derive-summary`
- `python -c "import tomllib, pathlib; tomllib.loads(pathlib.Path('.codex/config.toml').read_text())"`
- `bash -n heartbeat.sh` after shell edits

## Editing Guidance
- Preserve existing behavior unless the current prompt requires a change.
- Avoid inventing new lanes, services, or state transitions beyond the revised spec.
- Keep secrets out of markdown and out of committed state.
- If a prompt depends on external infrastructure that is still out of scope, define the config or state contract and stop there.

## Working Notes
- `README.md`, `OBJECTIVE.md`, and related markdown are still due for a larger prompt-7 refresh.
- Until those docs are refreshed, prefer `AGENTS.md` plus `state/` for repo conventions and canonical truth.
