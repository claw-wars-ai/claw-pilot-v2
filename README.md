# Claw Pilot vNext

**Question**: Can a sandboxed AI agent go from workspace to a deployed no-login tool and one verified external core action using operator-gated external actions, auditable receipts, and structured state?

## Operating Model
- Agent autonomy is limited to the sandboxed workspace.
- The agent can research, build, instrument, draft outreach, and propose structured state changes.
- The operator approves sensitive actions and can execute approved external actions through the relay path.
- The orchestrator validates state, runs preflight, records receipts, enforces gates, and renders human-facing markdown.
- Approval is not posting. Outreach only becomes executed when the orchestrator records a valid receipt.

## Current Pilot Scope
- Fresh pilot target: 1 verified external core-action event.
- Stretch goal: 3 verified external users.
- Hard gates: HB3 problem evidence, HB6 public URL, HB7 receipt-backed outreach execution, HB8 verified external core action, HB10 wrap and classify.
- Keep the same model, runtime, deploy lane, and verification lane for this run.
- Do not add more tools, more lanes, or more distribution surfaces before this pilot is measured.

## Official Lanes
- Product deployment lane: GitHub Pages only.
- Verification lane: one shared operator-managed collector reused across pilots.
- GitHub Pages alone is not enough for verified-user measurement because it cannot host the write collector.

## Optional Narrow Extension
- One additional distribution surface is enabled: `hackernews_show_hn`.
- Its canonical policy lives in [`state/distribution_policy.json`](C:\Users\jdste\Coding Projects\claw-wars\state\distribution_policy.json).
- Only use it when the product is clearly dev-tool-shaped.

## Canonical State
- Canonical execution state lives under [`state/`](C:\Users\jdste\Coding Projects\claw-wars\state\README.md).
- Rendered summaries include [`TOOL_GRANTS.md`](C:\Users\jdste\Coding Projects\claw-wars\TOOL_GRANTS.md), [`OUTBOX.md`](C:\Users\jdste\Coding Projects\claw-wars\OUTBOX.md), and [`OPERATOR_LOG.md`](C:\Users\jdste\Coding Projects\claw-wars\OPERATOR_LOG.md).
- Human-facing notes such as [`JOURNEY.md`](C:\Users\jdste\Coding Projects\claw-wars\JOURNEY.md) and [`RESOURCES.md`](C:\Users\jdste\Coding Projects\claw-wars\RESOURCES.md) are summaries, not canonical execution proof.

## Core Files
| File | Purpose |
|------|---------|
| [`RUNBOOK.md`](C:\Users\jdste\Coding Projects\claw-wars\RUNBOOK.md) | Operator-facing preflight, relay, reset, and lane guidance |
| [`OBJECTIVE.md`](C:\Users\jdste\Coding Projects\claw-wars\OBJECTIVE.md) | Agent mission and heartbeat protocol |
| [`REVIEWER_PROMPT.md`](C:\Users\jdste\Coding Projects\claw-wars\REVIEWER_PROMPT.md) | Outreach review rubric and response format |
| [`state/run.json`](C:\Users\jdste\Coding Projects\claw-wars\state\run.json) | Run metadata |
| [`state/preflight.json`](C:\Users\jdste\Coding Projects\claw-wars\state\preflight.json) | Hard preflight result |
| [`state/gates.json`](C:\Users\jdste\Coding Projects\claw-wars\state\gates.json) | Gate status derived from canonical state |
| [`state/deployment.json`](C:\Users\jdste\Coding Projects\claw-wars\state\deployment.json) | GitHub Pages deployment config and URL verification |
| [`state/verification_config.json`](C:\Users\jdste\Coding Projects\claw-wars\state\verification_config.json) | Verification lane contract |
| [`state/outreach_queue.json`](C:\Users\jdste\Coding Projects\claw-wars\state\outreach_queue.json) | Outreach review and execution queue |
| [`state/outreach_receipts.json`](C:\Users\jdste\Coding Projects\claw-wars\state\outreach_receipts.json) | Receipt-backed posting evidence |
| [`state/verification_events.jsonl`](C:\Users\jdste\Coding Projects\claw-wars\state\verification_events.jsonl) | Append-only verification events |
| [`tools/reset_pilot_run.py`](C:\Users\jdste\Coding Projects\claw-wars\tools\reset_pilot_run.py) | Archive runtime artifacts and reset into a fresh pilot |

## Core Commands
```bash
python tools/reset_pilot_run.py --pilot-class pilot_a
./heartbeat.sh --preflight
./heartbeat.sh --status
./heartbeat.sh --run-once
./heartbeat.sh --review-queue
./heartbeat.sh --record-receipt <item-id> --receipt-type <type> --receipt-value <value>
./heartbeat.sh --render-summaries
python -m unittest discover -s tests -p 'test_*.py'
python tools/validate_state.py
```

## Receipts And Verification
- Allowed receipt types are `public_url`, `post_id`, `screenshot_path`, and `operator_confirmation`.
- `approved_draft` is review state only.
- `posted` requires a validated receipt in canonical state.
- Verified-user claims come from [`state/verification_events.jsonl`](C:\Users\jdste\Coding Projects\claw-wars\state\verification_events.jsonl) and the derived summary in [`state/analytics_summary.json`](C:\Users\jdste\Coding Projects\claw-wars\state\analytics_summary.json).

## Preflight And Failure Handling
- Run `./heartbeat.sh --preflight` before any heartbeat execution.
- Preflight fails fast if required infrastructure, auth, config, workspace seed files, or canonical state is missing.
- `./heartbeat.sh --run-once` refuses to proceed when preflight fails.
- `./heartbeat.sh --run-once` also refuses to proceed once a hard gate deadline has already been missed.
- G2 only passes after a public URL verification check succeeds.
- G3 only passes after at least one posted outreach item has a validated receipt.
- G4 only passes after at least one `core_action_completed` event appears in the verification stream.
- If required external infrastructure is missing, define the config/state contract clearly and stop there.
