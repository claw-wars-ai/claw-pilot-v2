# Claw Pilot vNext Spec

## Executive summary

The next improvement cycle should not be framed as “make the agent smarter.”
It should be framed as:

1. close the execution gap between **approved** and **actually executed** external actions,
2. close the verification gap between **maybe someone used it** and **provable core-action usage**,
3. remove stale contradictions between the root docs and the runtime reality,
4. make the run state machine-readable so the orchestrator, operator, and agent share the same truth.

The design target is a repeatable pilot harness that can support increasingly difficult runs.

---

## What v1 actually proved

- The agent can identify a plausible problem.
- The agent can build and deploy a small self-serve tool.
- The system cannot yet reliably convert approved outreach into public execution receipts.
- The system cannot yet reliably verify users through an agent-readable measurement path.
- The current docs and orchestrator still contain state mismatches that make false progress too easy.

---

## Non-negotiable vNext changes

### 1. Replace prose state with structured state

Keep markdown for human-readable summaries, but the system of record must be structured files.

Recommended layout:

```text
state/
  run.json
  gates.json
  tool_requests/
    hb001_request.json
  tool_grants.json
  outreach_queue.json
  outreach_receipts.json
  verification_events.jsonl
  operator_events.jsonl
  deployment.json
  analytics.json
```

Rules:

- The agent may propose changes by writing JSON files that match schema.
- The orchestrator is the only actor allowed to mark external actions as executed.
- Human-readable markdown files should be rendered from state, not treated as the canonical source.

### 2. Add a hard preflight gate

No heartbeat may run until preflight passes.

Preflight must verify:

- `openclaw` is available in the real cron/service environment.
- reviewer auth is present and the reviewer round-trip works.
- the deployment lane is valid.
- the agent can read the verification path.
- the sandbox/browser profile is configured the way the docs claim.
- required secrets are present by name.
- state directory exists and validates.

Recommended command:

```bash
./heartbeat.sh --preflight
```

It should return non-zero on any failed check and write a machine-readable report to `state/preflight.json`.

### 3. Make outreach a queue, not a paragraph

Replace `## Proposed Outreach` parsing with explicit items.

Recommended schema:

```json
{
  "id": "hb010_reddit_macapps_01",
  "heartbeat": 10,
  "platform": "reddit",
  "target": "r/macapps",
  "kind": "post",
  "content": {
    "title": "...",
    "body": "..."
  },
  "rationale": "...",
  "review_status": "pending",
  "execution_status": "not_executed",
  "receipt": null
}
```

Execution states should be one of:

- `not_executed`
- `approved_draft`
- `edit_required`
- `denied`
- `posted`
- `failed_to_post`

A post only becomes `posted` if there is a receipt.

### 4. Add receipts for any external action

Every externally visible action must produce a receipt.

Allowed receipt types:

- public URL
- post ID
- screenshot path
- operator confirmation with timestamp

No receipt, no claim.

### 5. Replace “analytics access” with a concrete verification channel

The next runs should use one explicit event stream for the product’s core action.

Recommended model:

- client-side core action emits a POST to a tiny endpoint or collector
- collector writes append-only JSONL
- orchestrator copies/read exposes that file to the agent
- verification standard is computed from this log

Recommended event format:

```json
{
  "ts": "2026-04-10T12:34:56Z",
  "event": "core_action_completed",
  "product": "pilot-image-resizer-site",
  "anonymous_user_id": "sha256:...",
  "details": {
    "files_processed": 12,
    "format": "jpg"
  },
  "source": "public_site"
}
```

The run should count verified users from this event log plus optional feedback evidence.

### 6. Collapse to one official deployment lane

The canon docs should stop advertising multiple equal deploy options.
The pilot evidence says the actual viable lane was GitHub Pages, not Surge.

Recommended vNext policy:

- official pre-granted deployment: GitHub Pages only
- all other deploy targets: denied unless explicitly justified for a later run

### 7. Clarify the human role

The README currently overclaims autonomy.
The new phrasing should be:

- autonomous build/execution **inside the sandboxed workspace**
- operator-gated external actions
- operator-owned reputation and account surfaces
- all interventions logged

### 8. Standardize cadence

The docs disagree on timing.
Make cadence a single parameter, e.g.

```bash
HEARTBEAT_INTERVAL_MINUTES=60
MAX_HEARTBEATS=12
```

Gates should be expressed in heartbeat numbers, not in wall-clock language.

---

## Recommended doc changes

## README.md

Replace the framing question with:

> Can a sandboxed AI agent go from workspace to deployed tool and verified users with operator-gated external actions and auditable state?

Add sections:

- `What is autonomous vs operator-gated`
- `Preflight`
- `State files`
- `Receipts and verification`
- `Failure handling`

Remove / rewrite:

- “with no human in the loop”
- “walk away”
- pre-granted Surge deployment

## OBJECTIVE.md

Keep the mission but change the external communications workflow.

Instead of:
- “If APPROVED: post it during this heartbeat”

Use:
- “If APPROVED: enqueue it for execution. Treat it as a draft until a posting receipt exists.”

Add explicit rules:

- do not claim any external action was executed without a receipt
- verification comes from `state/verification_events.jsonl`, not intuition
- if G3 is missed, pivot is required and must be justified against evidence
- if no executable distribution path exists by HB8, file a blocking escalation

## REVIEWER_PROMPT.md

Strengthen the reviewer rubric to reject:

- fabricated first-hand experience
- unverifiable social proof
- generic “feedback?” self-promotion
- any claim that the agent has already posted elsewhere unless receipt exists

Return JSON instead of free text:

```json
{
  "decision": "approve",
  "reason": "...",
  "required_edits": [],
  "risk_flags": ["self_promo"],
  "suggested_targeting": "..."
}
```

## TOOL_GRANTS.md

Turn this into a rendered summary only.
Canonical grants should live in `state/tool_grants.json`.

## OPERATOR_LOG.md

Turn this into a rendered summary only.
Canonical operator actions should live in `state/operator_events.jsonl`.

## SESSION.md

Strip stale one-off setup history from the repo-facing version.
Split into:

- `RUNBOOK.md` for live operator instructions
- `SESSION.md` only if you truly need a temporary handoff note

---

## Orchestrator requirements

`heartbeat.sh` should become a strict state machine.

Recommended commands:

```bash
./heartbeat.sh --preflight
./heartbeat.sh --status
./heartbeat.sh --run-once
./heartbeat.sh --review-queue
./heartbeat.sh --render-summaries
./heartbeat.sh --reset
```

Recommended behaviors:

- fail fast with trap + clear error messages
- write a JSON preflight report
- validate any JSON written by the agent before acting on it
- update state first, render markdown second
- keep locks reliable
- never mark outreach as executed without a receipt
- never mark G2 passed until the public URL returns success
- never mark G3 passed until at least one verified event exists
- emit machine-readable run status for automation

---

## Tools for v2

### Add now

1. **Posting relay or managed execution path**
   - safest option: operator relay
   - higher-autonomy option: dedicated managed browser profile for one approved platform at a time

2. **Readable verification channel**
   - append-only event log for core-action completions
   - agent-readable and operator-auditable

### Keep disabled for now

- direct messages
- email sending
- payments
- user accounts/login
- broad social auth across multiple platforms
- remote code execution outside the canonical local workspace path

### Optional later

- Telegram or Slack error notifications
- one additional distribution surface once the first posting loop works

---

## Recommended pilot ladder

Do not jump from this pilot straight to more complicated runs.
Use a ladder.

### Pilot A — Infra smoke
Goal: prove the harness works.

Success:
- preflight green
- reviewer green
- one dummy outreach item reviewed and rendered
- one synthetic verification event readable
- deployment lane verified

### Pilot B — Build-only
Goal: blank workspace to deployed public tool.

Success:
- G1 pass
- G2 pass
- no requirement for user acquisition

### Pilot C — Distribution-loop replay
Goal: existing live product to 1 verified external user.

Success:
- one approved outreach item
- one posted receipt
- one verified core-action event

### Pilot D — Full 0→10
Goal: blank workspace to deployed tool + 10 verified users.

Success:
- same harness as C
- stricter gate discipline

### Pilot E — More complicated runs
Only after A-D are stable.

Possible complications:
- authenticated products
- more complex research loops
- multi-step workflows
- richer channels

---

## Merge-back items from runtime evidence

The runtime bundle already contained ideas that should be brought back into canon:

- `OUTBOX.md` manual handoff wording
- “approval is draft approval only, not publication”
- G2 URL verification before claiming pass
- safer tool request parsing
- optional error notifications

These should not remain trapped in the dossier; they should become repo truth.

---

## Minimal v2 success definition

A v2 run is successful if all of the following are true:

1. the harness passes preflight,
2. the agent can deploy through the official lane,
3. at least one approved outreach item is executed with a receipt,
4. at least one verified external core-action event is recorded,
5. docs, state, and receipts agree.

That is the smallest credible step toward more complicated autonomous runs.
