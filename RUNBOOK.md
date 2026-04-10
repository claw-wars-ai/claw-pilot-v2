# Claw Pilot vNext Runbook

This file is the operator-facing quick reference for the official lanes introduced in Prompt 2.

## Canonical Sources
- Runtime state lives under [`state/`](C:\Users\jdste\Coding Projects\claw-wars\state\README.md).
- Markdown is explanatory only unless a prompt explicitly says otherwise.
- Structured tool requests live in [`state/tool_requests/`](C:\Users\jdste\Coding Projects\claw-wars\state\tool_requests\README.md), and canonical grant outcomes live in [`state/tool_grants.json`](C:\Users\jdste\Coding Projects\claw-wars\state\tool_grants.json).
- Canonical outreach state lives in [`state/outreach_queue.json`](C:\Users\jdste\Coding Projects\claw-wars\state\outreach_queue.json), [`state/outreach_receipts.json`](C:\Users\jdste\Coding Projects\claw-wars\state\outreach_receipts.json), and [`state/operator_events.jsonl`](C:\Users\jdste\Coding Projects\claw-wars\state\operator_events.jsonl).
- Canonical preflight and gate state live in [`state/preflight.json`](C:\Users\jdste\Coding Projects\claw-wars\state\preflight.json) and [`state/gates.json`](C:\Users\jdste\Coding Projects\claw-wars\state\gates.json).

## Preflight And Status
- Run `./heartbeat.sh --preflight` before any heartbeat execution.
- Preflight writes structured results to `state/preflight.json` and exits non-zero on failure.
- Run `./heartbeat.sh --status` for machine-readable JSON status.
- Run `./heartbeat.sh --render-summaries` after state-only changes to refresh rendered markdown.
- `./heartbeat.sh --run-once` refuses to proceed if preflight fails.

## Regression Suite
- Run `python -m unittest discover -s tests -p 'test_*.py'` for the local regression suite.
- The suite covers preflight failures, malformed structured tool requests, receipt-backed outreach transitions, public URL gate checks, and verification-event counting.

## Tool Request Processing
- Create one JSON file per request in `state/tool_requests/`.
- Process the queue with `./heartbeat.sh --review-queue` or `python tools/process_tool_requests.py`.
- LOW-risk requests become `auto_granted`.
- MEDIUM/HIGH-risk requests become `pending_review`.
- Malformed requests become `invalid` with an auditable reason in canonical state.

## Outreach Receipt Relay
- Reviewer approval creates an `approved_draft`; it does not mean the post has executed.
- After the operator executes the approved action, record the receipt with:
  `./heartbeat.sh --record-receipt <item-id> --receipt-type <type> --receipt-value <value>`
- Allowed receipt types are `public_url`, `post_id`, `screenshot_path`, and `operator_confirmation`.
- The orchestrator validates the receipt, transitions the item to `posted`, and records the audit events.
- Human-facing status is rendered into [`OUTBOX.md`](C:\Users\jdste\Coding Projects\claw-wars\OUTBOX.md) and [`OPERATOR_LOG.md`](C:\Users\jdste\Coding Projects\claw-wars\OPERATOR_LOG.md).

## Official Lanes
- Product deployment lane: GitHub Pages only.
- Verification lane: one shared operator-managed collector reused across pilots.

## Additional Distribution Surface
- The only optional extension enabled in vNext is `hackernews_show_hn`.
- Canonical policy lives in [`state/distribution_policy.json`](C:\Users\jdste\Coding Projects\claw-wars\state\distribution_policy.json).
- Use `Platform: hackernews_show_hn` and `Target: show-hn` for that surface.
- Unsupported surfaces should be rejected rather than improvised.

## Product Deployment Contract
Canonical config: [`state/deployment.json`](C:\Users\jdste\Coding Projects\claw-wars\state\deployment.json)

Required before a deploy-capable run can pass G2:
- `product_lane.kind = "github_pages"`
- `GITHUB_PAGES_OWNER`
- `GITHUB_PAGES_REPO`
- `GITHUB_PAGES_TOKEN`
- a resolved `public_url`
- a successful URL verification check recorded by the orchestrator

No alternate product deployment target is approved for the current pilot class.

## Verification Contract
Canonical config: [`state/verification_config.json`](C:\Users\jdste\Coding Projects\claw-wars\state\verification_config.json)

Verified-user pilots require:
- a client-write endpoint named by `CLAW_VERIFY_WRITE_ENDPOINT`
- a readable append-only export path named by `CLAW_VERIFY_READ_PATH`
- anonymous-only event payloads
- derived summaries written to [`state/analytics_summary.json`](C:\Users\jdste\Coding Projects\claw-wars\state\analytics_summary.json)
- local import and summary helpers via `python tools/verification_events.py import --input <export-path>` and `python tools/verification_events.py derive-summary`

GitHub Pages cannot satisfy this alone. If the collector lane is not provisioned, do not claim verified-user measurement for that run.

Client event contract for the public product:
- Emit `event_type: core_action_completed`
- Include `anonymous_user_id` as a stable anonymous hash or ID
- Include `occurred_at` as an ISO8601 UTC timestamp
- Keep `metadata` anonymous and minimal

## Pilot Readiness Rule
- Build-only runs may proceed without a live verification collector.
- Any run that claims verified external users must have the shared collector provisioned first.
- If that infrastructure does not exist yet, stop at the config and state contract and escalate rather than improvising a new service.
