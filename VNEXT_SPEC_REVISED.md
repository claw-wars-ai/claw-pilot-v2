# Claw Pilot vNext Spec — Revised

## Executive summary

The critique is correct on the two main failure modes in the first draft:

1. receipt-backed external execution was treated as important in principle but not made mandatory in the implementation sequence,
2. usage verification was specified without a concrete hosting model.

This revised spec closes both gaps.

The next improvement cycle should be framed as:

- make external execution receipt-backed and mandatory,
- make usage verification receipt-backed and technically runnable,
- keep canonical state machine-readable,
- make the operator/orchestrator boundary explicit,
- use a pilot ladder so harder runs only happen after the harness proves the easier loop.

---

## What v1 actually proved

- The agent can identify a plausible problem.
- The agent can build and deploy a small self-serve tool.
- The harness cannot yet reliably convert approved outreach into public execution receipts.
- The harness cannot yet reliably verify real users through an agent-readable evidence channel.
- Canon docs, runtime assumptions, and operator behavior still drift.

---

## Non-negotiable vNext requirements

### 1. Structured state is canonical

Markdown remains human-facing only.

Recommended layout:

```text
state/
  run.json
  gates.json
  preflight.json
  deployment.json
  verification_config.json
  analytics_summary.json
  tool_grants.json
  outreach_queue.json
  outreach_receipts.json
  verification_events.jsonl
  operator_events.jsonl
  tool_requests/
    hb001_request.json
```

Rules:

- The agent may propose state changes by writing structured files that match schema.
- The orchestrator is the only actor allowed to mutate canonical execution state.
- Operator actions are inputs to the orchestrator, not direct edits to canonical state.
- Markdown summaries are rendered from state.

### 2. Receipt-backed posting is mandatory, not optional

The v2 harness is not complete until one approved outreach item can become one posted item with a receipt.

Allowed execution states:

- `pending_review`
- `approved_draft`
- `edit_required`
- `denied`
- `posted`
- `failed_to_post`

Allowed receipt types:

- public URL
- post ID
- screenshot path
- operator confirmation with timestamp

Rules:

- `approved_draft` is not execution.
- Nothing may transition to `posted` without a validated receipt.
- The orchestrator, not the operator, performs the transition after validating the receipt input.

### 3. Verification must have an official hosting lane

A static GitHub Pages site cannot itself host a write collector.
That means one of the following must be true before any run that measures verified users:

#### Option A — recommended for repeated pilots

Use two official lanes:

1. **Product deploy lane**: GitHub Pages for the public static product.
2. **Verification lane**: one pre-provisioned operator-managed collector endpoint reused across pilots.

The collector endpoint must:

- accept a minimal event payload from the public product,
- write append-only events,
- expose either a read-only JSON export or a file-sync path the orchestrator can read,
- avoid PII.

This is the recommended path because it keeps product deploy simple while making verification real.

#### Option B — for earlier infra-only pilots

If you refuse a second official service, then do **not** claim verified-user measurement for that run.
Downgrade the success metric to:

- deployed tool,
- receipt-backed outreach,
- optional qualitative feedback.

Rules:

- Any run whose success metric includes “verified users” must use Option A.
- The collector endpoint is part of harness infrastructure, not a per-run improvisation.

### 4. Hard preflight before HB1

No heartbeat may run until preflight passes.

Preflight must verify:

- `openclaw` exists in the real cron/service environment,
- reviewer auth exists and the reviewer round-trip works,
- required secrets exist by name,
- the official product deployment lane is configured,
- the official verification lane is configured,
- the verification read path is reachable or bootstrappable,
- workspace and state directories exist and validate,
- the configured sandbox/browser profile matches the docs.

Required command:

```bash
./heartbeat.sh --preflight
```

It must exit non-zero on failure and write `state/preflight.json`.

### 5. One boring product deploy lane

The official product deployment lane for the current pilot class is:

- **GitHub Pages only**

Other product deploy targets are denied by default unless a later pilot class explicitly changes policy.

### 6. One boring verification lane

The official verification lane for the current pilot class is:

- **one operator-managed collector endpoint reused across pilots**

The canon docs should name it as infrastructure, not as a vague future idea.

### 7. Clarify roles

#### Agent

- autonomous inside the sandboxed workspace,
- can search, build, instrument, deploy through the approved lane,
- can draft outreach and request tools,
- cannot claim external execution without a receipt,
- cannot mark state transitions reserved for the orchestrator.

#### Operator

- approves or denies sensitive actions,
- may execute an approved external action through the relay path,
- provides receipt inputs,
- does not edit canonical execution state directly,
- all actions logged.

#### Orchestrator

- validates state,
- runs preflight,
- runs reviews,
- validates receipts,
- mutates canonical state,
- renders markdown summaries,
- enforces gates.

---

## Gate rules

### G1 — problem identified

Pass only when the chosen problem is specific and supported by evidence.

### G2 — public product deployed

Pass only when the public URL is configured in `state/deployment.json` and a URL verification check succeeds.

### G3 — external execution loop closed

Pass only when:

- at least one outreach item is approved,
- at least one outreach item is `posted`,
- the posted item has a validated receipt.

### G4 — verified user loop closed

Pass only when:

- at least one external human completes the core action,
- the completion appears in the verification event stream,
- the derived verified user count is at least 1.

For a full 0→10 pilot, the same mechanism scales to 10 users.

---

## Recommended pilot ladder

### Pilot A — Harness smoke

Goal:
- preflight green,
- one dummy reviewed outreach item,
- one receipt-backed posted test item,
- one synthetic verification event readable.

### Pilot B — Build-only

Goal:
- blank workspace to deployed public tool,
- no user requirement.

### Pilot C — Distribution replay

Goal:
- existing live product,
- one real receipt-backed outreach execution,
- one verified external core-action event.

### Pilot D — Full 0→10

Goal:
- blank workspace to deployed tool plus 10 verified external users,
- only after A, B, and C succeed.

---

## Doc changes required

### README.md

Replace overclaimed framing with:

> Can a sandboxed AI agent go from workspace to deployed tool and verified users using operator-gated external actions, auditable receipts, and structured state?

Add sections:

- what is autonomous vs operator-gated,
- official product deploy lane,
- official verification lane,
- preflight,
- receipts,
- verification,
- operator relay,
- failure handling.

Remove or rewrite:

- “with no human in the loop”,
- “walk away”,
- any suggestion that approval equals posting,
- any stale alternate deploy lane.

### OBJECTIVE.md

Change:

- “If APPROVED: post it during this heartbeat”

to:

- “If APPROVED: it becomes an approved draft. Treat it as not executed until the orchestrator records a valid receipt.”

Add:

- if no executable posting path exists, escalate,
- verified-user claims come from the verification stream only,
- do not improvise new deployment or analytics lanes.

### REVIEWER_PROMPT.md

Return structured output.
Reject:

- fabricated first-hand experience,
- fabricated posting history,
- unverifiable social proof,
- generic self-promotional copy.

### TOOL_GRANTS.md and OPERATOR_LOG.md

Rendered summaries only.
Canonical state lives under `state/`.

### SESSION.md

Replace stale handoff notes with a proper `RUNBOOK.md`.

---

## Orchestrator requirements

Required commands:

```bash
./heartbeat.sh --preflight
./heartbeat.sh --status
./heartbeat.sh --run-once
./heartbeat.sh --review-queue
./heartbeat.sh --record-receipt <item-id> --receipt-type <type> --receipt-value <value>
./heartbeat.sh --render-summaries
./heartbeat.sh --reset
```

Behavior rules:

- fail fast with traps and clear errors,
- validate structured inputs before acting,
- update canonical state first,
- render markdown second,
- never mark outreach as executed without a receipt,
- never mark G2 passed without a verified public URL,
- never mark G3 passed without a receipt-backed post,
- never mark G4 passed without a verification event,
- emit machine-readable status for automation.

The operator relay should work like this:

1. agent creates an outreach item,
2. reviewer marks it `approved_draft`,
3. operator executes the action off-system or via dedicated safe path,
4. operator runs `--record-receipt ...`,
5. orchestrator validates the receipt and moves the item to `posted`,
6. rendered summaries update.

This preserves orchestrator ownership of canonical state.

---

## Revised implementation order

The original prompt order was wrong because preflight and enforcement were asked to validate infrastructure that had not yet been canonically defined.

Use this order instead:

1. repo scaffolding, `AGENTS.md`, `.codex/config.toml`, and canonical state layout,
2. define the official product deploy lane and official verification lane in state/config,
3. replace prose tool requests with structured canonical state,
4. implement receipt-backed outreach state and required operator relay,
5. implement verification log helpers and derived counts,
6. add preflight and gate enforcement,
7. refresh docs and runbook,
8. add regression tests,
9. optional later: direct posting executor or second distribution surface.

---

## Decision summary

The critique was right.

The harness should not be treated as ready for another full acquisition pilot until it can do these two things reliably:

1. one approved outreach item becomes one posted item with a receipt,
2. one external core-action completion appears in a readable verification stream.

Everything else is secondary until those loops are closed.
