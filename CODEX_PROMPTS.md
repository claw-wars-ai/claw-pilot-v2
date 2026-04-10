# Codex prompts for Claw Pilot vNext

Use these in order. Each prompt is designed to be one focused Codex task. Run each one in its own branch or worktree.

---

## Prompt 1 — Create repo guidance for Codex itself

Goal:
Create a concise `AGENTS.md` and repo-local `.codex/config.toml` for this repository so future Codex tasks have stable context and consistent defaults.

Context:
- This repo is an orchestration harness for repeated autonomous pilot runs.
- The core files are `README.md`, `OBJECTIVE.md`, `REVIEWER_PROMPT.md`, `SESSION.md`, `TOOL_GRANTS.md`, `OPERATOR_LOG.md`, `RESOURCES.md`, `JOURNEY.md`, and `heartbeat.sh`.
- The repo needs durable guidance for state handling, testing expectations, safety limits, and how to verify work.

Constraints:
- Keep `AGENTS.md` short and practical.
- Include repo layout, how to run checks, conventions for structured state vs rendered markdown, and a definition of done.
- In `.codex/config.toml`, keep sandbox/approval defaults conservative.
- Do not introduce speculative tooling.

Done when:
- `AGENTS.md` exists and is under ~150 lines.
- `.codex/config.toml` exists with sane defaults and comments.
- The docs tell future Codex runs to prefer small PRs, add tests when behavior changes, and render markdown from state rather than treating markdown as canonical.
- Provide a short summary of the files added and why.

---

## Prompt 2 — Add a hard preflight gate to heartbeat.sh

Goal:
Refactor `heartbeat.sh` so the pilot cannot start unless environment, auth, deployment lane, and verification path pass a strict preflight.

Context:
- The previous pilot failed in part because cron/runtime env differed from the interactive shell, the reviewer key was missing, and deployment/verification paths were not actually executable.
- The current script has `--dry-run`, `--status`, `--reset`, and `--review-test`, but no true preflight.
- The current docs say to run `openclaw doctor`, but the orchestrator does not enforce any preflight state.

Constraints:
- Add `--preflight` and `--run-once` modes.
- `--preflight` must write `state/preflight.json` and exit non-zero on failure.
- Validate at minimum:
  - `openclaw` exists in PATH in the current shell
  - reviewer auth is present and a reviewer test call works
  - required secrets exist by name
  - official deployment lane configuration exists
  - verification log path exists and is readable or bootstrappable
  - workspace and state directories exist
- Keep the script POSIX-ish bash and defensive under `set -euo pipefail`.
- Add clear error output and traps.

Done when:
- `bash -n heartbeat.sh` passes.
- `./heartbeat.sh --preflight` writes a structured JSON report.
- `./heartbeat.sh --run-once` refuses to run if preflight fails.
- README instructions are updated to use preflight before any pilot run.
- Add at least one regression test or testable shell harness for preflight failure cases.

---

## Prompt 3 — Replace freeform tool/outreach parsing with structured state

Goal:
Move the orchestrator from markdown parsing to machine-readable state files for tool requests, tool grants, outreach queue items, and execution receipts.

Context:
- The existing system parses `TOOL_REQUEST.md` with grep-like logic and parses outreach from `## Proposed Outreach` in `HBn_PLAN.md`.
- This is too brittle and allows state drift.
- The repo should keep markdown summaries, but JSON should be canonical.

Constraints:
- Introduce a `state/` directory with at least:
  - `run.json`
  - `tool_requests/`
  - `tool_grants.json`
  - `outreach_queue.json`
  - `outreach_receipts.json`
  - `operator_events.jsonl`
- Add JSON schemas or validation helpers where practical.
- Keep backward compatibility light: it is acceptable to stop relying on `TOOL_REQUEST.md` as the canonical input.
- If you keep markdown files, render them from state.

Done when:
- The orchestrator reads structured tool requests instead of scraping prose.
- Outreach proposals live in `state/outreach_queue.json` with explicit statuses.
- Tool grants live in `state/tool_grants.json`.
- `TOOL_GRANTS.md` and `OPERATOR_LOG.md` become rendered summaries.
- Tests cover malformed requests and missing fields.

---

## Prompt 4 — Implement explicit draft/posted receipt handling

Goal:
Make it impossible for the system to confuse “approved draft” with “posted externally.”

Context:
- The current canon docs still imply that approved outreach gets posted in the same heartbeat.
- Runtime evidence showed that review often produced draft-only handoffs.
- The system needs explicit posting receipts.

Constraints:
- Add a first-class `OUTBOX.md` rendered from state plus canonical `state/outreach_queue.json` and `state/outreach_receipts.json`.
- Distinguish these states: `pending_review`, `approved_draft`, `edit_required`, `denied`, `posted`, `failed_to_post`.
- A queued item may only become `posted` if a receipt exists.
- Accepted receipt types: public URL, post ID, screenshot path, or operator confirmation record.
- Update `OBJECTIVE.md`, `README.md`, and `REVIEWER_PROMPT.md` to reflect this reality.

Done when:
- An approved item becomes `approved_draft`, not `posted`.
- There is an explicit path for an operator relay or future executor to attach a receipt.
- Rendered markdown tells humans not to claim posting without evidence.
- Tests cover the state transition from review to receipt-backed posting.

---

## Prompt 5 — Add a real verification channel for core-action users

Goal:
Create a minimal, auditable verification system for user acquisition so the agent can prove real core-action completions.

Context:
- The previous pilot had a live static site but no reliable proof channel for actual usage.
- The next runs need a single source of truth for “verified user” events.
- Keep this simple and privacy-preserving.

Constraints:
- Add an append-only `state/verification_events.jsonl` log format.
- Add helper code/scripts to:
  - initialize the log
  - append synthetic test events
  - compute a verified user count from the log
- If there is a site in the repo, add a documented way for the site to emit a `core_action_completed` event.
- No PII.
- Prefer anonymous stable IDs or hashes where needed.

Done when:
- There is a small verification spec in the repo.
- The orchestrator can read the event log and compute verified user counts.
- `RESOURCES.md` is rendered from this source instead of manual free text.
- A synthetic end-to-end test proves that one logged completion increments the derived count.

---

## Prompt 6 — Narrow the deploy lane and add gate enforcement

Goal:
Standardize on one official deploy lane and make gate claims verifiable.

Context:
- The previous run used Surge in docs but needed GitHub Pages remediation in reality.
- The orchestrator should not let G2 pass unless the deployment URL actually resolves successfully.

Constraints:
- Update docs and defaults to use one official deploy lane only.
- Add deployment metadata to `state/deployment.json`.
- Add `verify_public_url()` and use it to enforce G2.
- Do not mark G2 passed from agent prose alone.
- Keep the design simple and static-site friendly.

Done when:
- README, SESSION/RUNBOOK, and grants all name the same official deploy lane.
- The orchestrator verifies the URL before updating gate state.
- Tests cover both a passing and failing URL verification path.

---

## Prompt 7 — Refresh the docs to match the actual operating model

Goal:
Rewrite the human-facing docs so they no longer overclaim autonomy and no longer contradict the runtime model.

Context:
- The current README still says “with no human in the loop” and encourages the operator to “walk away.”
- The actual model is operator-gated external actions with an honest intervention log.
- SESSION.md also contains stale one-off setup notes that should not be treated as current truth.

Constraints:
- Update `README.md`, `OBJECTIVE.md`, `TOOL_GRANTS.md`, `OPERATOR_LOG.md`, `RESOURCES.md`, and `JOURNEY.md`.
- Replace claims of full autonomy with precise language about sandboxed autonomy plus operator-gated external actions.
- Add a “What counts as autonomy vs assistance” section.
- Standardize cadence and gate language.
- Prefer short, direct docs.

Done when:
- The docs no longer say or imply that approval equals execution.
- The docs no longer say “no human in the loop.”
- The docs explicitly define receipts, verification, and preflight.
- There is a clean `RUNBOOK.md` or equivalent for operators instead of a stale `SESSION.md` dump.

---

## Prompt 8 — Add regression tests for the failure modes from the first pilot

Goal:
Add a lightweight automated regression suite covering the concrete failure modes already observed.

Context:
- Known failures included missing reviewer auth, openclaw missing from cron PATH, deploy verification mismatches, brittle tool-request parsing, and approved-draft vs posted confusion.
- The point of vNext is to stop repeating known failures.

Constraints:
- Add tests for at least these cases:
  1. reviewer key missing
  2. `openclaw` missing from PATH
  3. malformed structured tool request
  4. approved outreach without receipt stays draft-only
  5. failed public URL check blocks G2
  6. one synthetic verification event increments user count
- Use the lightest-weight test harness that fits the repo.
- Make tests runnable locally by Codex.

Done when:
- There is a documented test command in `AGENTS.md` and/or README.
- The regression suite fails before the fixes and passes after them.
- Codex reports which cases are covered and how to run them.

---

## Prompt 9 — Optional: operator relay for posting execution

Goal:
Implement a minimal operator relay path so approved drafts can become receipt-backed posted actions without giving the agent broad direct posting powers.

Context:
- vNext needs a closed loop between draft approval and posting receipt.
- The safest version is operator relay first, not full agent-controlled social auth.

Constraints:
- Add a simple CLI or JSON-based workflow for an operator to mark a queued outreach item as posted and attach a receipt.
- Log this to `state/operator_events.jsonl`.
- Render the result in `OUTBOX.md` and `OPERATOR_LOG.md`.
- Do not implement direct DMs, broad auth, or multi-platform automation in this task.

Done when:
- An operator can execute one command to attach a receipt to an approved draft.
- The item moves from `approved_draft` to `posted`.
- The rendered summaries update correctly.
- The action is auditable.
