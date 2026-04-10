# Codex prompts — Revised

Run these in order.
Each new prompt should start from the latest integrated main branch or from a stacked branch/worktree that already includes the prior prompt's merged changes.
Do **not** start later prompts from the original repo snapshot.

The core principle of this revised pack:
- receipt-backed posting is required,
- verification hosting is explicit,
- operator input does not bypass orchestrator ownership of canonical state.

---

## Prompt 1 — Scaffold canonical state, Codex guidance, and repo conventions

Goal:
Create the repo scaffolding for canonical structured state, short Codex guidance, and conservative local Codex defaults.

Context:
- The repo currently relies too much on markdown as both workflow and state.
- Later prompts will depend on a shared `state/` layout and clear conventions.

Constraints:
- Add `AGENTS.md` under ~150 lines.
- Add `.codex/config.toml` with conservative defaults and comments.
- Add a `state/` directory scaffold and lightweight schemas or validation helpers for:
  - `run.json`
  - `gates.json`
  - `deployment.json`
  - `verification_config.json`
  - `tool_grants.json`
  - `outreach_queue.json`
  - `outreach_receipts.json`
  - `verification_events.jsonl`
  - `operator_events.jsonl`
- Make it clear that markdown files are rendered summaries, not canonical state.

Done when:
- `AGENTS.md` exists and is practical.
- `.codex/config.toml` exists with conservative defaults.
- The state scaffold exists.
- There is a small README or comments explaining canonical state vs rendered markdown.
- Provide a short summary of what was added.

---

## Prompt 2 — Define the official product deploy lane and official verification lane

Goal:
Make the hosting model explicit so later code can validate real infrastructure rather than placeholders.

Context:
- GitHub Pages is the official product deploy lane for the static site.
- Verified-user runs also require an official second lane for event collection because GitHub Pages cannot host a write collector.
- The verification lane should be treated as shared harness infrastructure, not a per-run improvisation.

Constraints:
- Standardize the product deploy lane as GitHub Pages only.
- Add canonical config/state for the verification lane, for example in `state/verification_config.json`.
- The verification lane should model:
  - a write endpoint for client-side event submission,
  - a readable export or sync path for append-only events,
  - a derived summary path.
- Do not implement a full remote service here if that is out of scope.
- Do make the required config, expected environment variables, and state contracts explicit.
- Update operator-facing docs or runbook text to explain that verified-user pilots require this second official service.

Done when:
- The repo has one official product deploy lane and one official verification lane defined in canonical config/state.
- Docs no longer imply GitHub Pages alone can satisfy verified-user measurement.
- There is no ambiguity about what must exist before a verified-user pilot can start.

---

## Prompt 3 — Replace prose tool requests with structured canonical state

Goal:
Eliminate brittle `TOOL_REQUEST.md` parsing and make tool-request handling part of canonical structured state.

Context:
- One of the observed failures in v1 was brittle parsing around tool requests.
- The revised state model already includes `state/tool_requests/` and `state/tool_grants.json`.
- Tool requests should follow the same rule as other execution-critical inputs: structured first, rendered markdown second.

Constraints:
- Canonical tool requests must live in `state/tool_requests/*.json`.
- Define and validate a minimal request schema including at least:
  - `id`
  - `heartbeat`
  - `tool`
  - `why`
  - `plan`
  - `risk`
  - `alternatives_considered`
- Supported outcomes should be explicit in canonical state, for example:
  - `pending_review`
  - `auto_granted`
  - `granted`
  - `denied`
  - `invalid`
- The orchestrator must read structured requests instead of scraping prose from `TOOL_REQUEST.md`.
- `state/tool_grants.json` must become the canonical grant record.
- `TOOL_GRANTS.md` may remain, but only as a rendered summary from state.
- Backward compatibility can be minimal. It is acceptable to stop treating `TOOL_REQUEST.md` as canonical.

Done when:
- A valid structured tool request can be created and processed end-to-end.
- A malformed tool request is rejected cleanly with an auditable reason.
- The orchestrator no longer depends on markdown parsing for canonical tool-request handling.
- Tests cover malformed requests and missing required fields.

---

## Prompt 4 — Implement receipt-backed outreach state and the required operator relay

Goal:
Make receipt-backed posting a mandatory core capability, not an optional add-on.

Context:
- The prior prompt pack made this optional, which was wrong.
- The system must be able to distinguish `approved_draft` from `posted` and move to `posted` only through a validated receipt path.
- The operator may supply a receipt, but the orchestrator must remain the only actor mutating canonical execution state.

Constraints:
- Add canonical outreach and receipt handling using structured state.
- Required statuses:
  - `pending_review`
  - `approved_draft`
  - `edit_required`
  - `denied`
  - `posted`
  - `failed_to_post`
- Add a command or subcommand such as:
  - `./heartbeat.sh --record-receipt <item-id> --receipt-type <type> --receipt-value <value>`
- The operator command must feed validated input into the orchestrator.
- The operator must not directly edit `state/outreach_queue.json`.
- Render `OUTBOX.md` and `OPERATOR_LOG.md` from state.
- Update any docs or prompts that still imply “approval means posting.”

Done when:
- An approved item remains `approved_draft` until a valid receipt is recorded.
- A receipt can be attached through the relay command.
- The orchestrator validates the receipt and performs the transition to `posted`.
- The action is auditable in `state/operator_events.jsonl`.
- Tests cover review-to-posted transitions.

---

## Prompt 5 — Implement the verification event log and derived user counts

Goal:
Create a minimal, auditable verification path for real core-action usage.

Context:
- Verified-user pilots need a real evidence channel.
- The official verification lane has already been defined in config/state.
- The repo needs local helpers and a clear contract even if the remote collector is operator-managed.

Constraints:
- Add append-only `state/verification_events.jsonl` handling.
- Add helper scripts or code to:
  - initialize the log,
  - append a synthetic event,
  - ingest a sync/export payload if that is part of the chosen architecture,
  - compute unique verified user counts from the log,
  - write a small summary to canonical state.
- No PII.
- Use anonymous stable IDs or hashes where needed.
- If the repo contains the public site, document how the site should emit a `core_action_completed` event to the official write endpoint.

Done when:
- One synthetic event can be logged and counted.
- The verified-user count is derived from canonical event data, not free text.
- The summary is readable by the orchestrator and renderable into human docs.

---

## Prompt 6 — Add hard preflight and gate enforcement to heartbeat.sh

Goal:
Refactor `heartbeat.sh` so runs fail fast unless real infrastructure, auth, and state are ready.

Context:
- Preflight depends on the canonical lanes and state introduced by earlier prompts.
- The orchestrator also needs gate enforcement so G2, G3, and G4 cannot pass from prose alone.

Constraints:
- Add or harden these modes:
  - `--preflight`
  - `--run-once`
  - `--status`
  - `--record-receipt ...`
  - `--render-summaries`
- `--preflight` must write `state/preflight.json` and exit non-zero on failure.
- Validate at minimum:
  - `openclaw` exists in the current PATH,
  - reviewer auth exists and a reviewer round-trip works,
  - required secrets exist by name,
  - product deploy lane config exists,
  - verification lane config exists,
  - verification read path is reachable or bootstrappable,
  - workspace and state directories exist and validate.
- Enforce:
  - G2 only passes if the public URL verifies,
  - G3 only passes if at least one outreach item is `posted` with a receipt,
  - G4 only passes if at least one verification event exists.
- Keep the script defensive under `set -euo pipefail`.

Done when:
- `bash -n heartbeat.sh` passes.
- `./heartbeat.sh --preflight` writes structured output and fails correctly.
- `./heartbeat.sh --run-once` refuses to proceed on failed preflight.
- Gate status comes from canonical state and checks, not markdown prose.

---

## Prompt 7 — Refresh README, OBJECTIVE, REVIEWER_PROMPT, and operator docs

Goal:
Bring the human-facing docs in line with the actual operating model.

Context:
- The old docs overclaimed autonomy and blurred approval versus execution.
- The revised model is sandboxed autonomy inside the workspace plus operator-gated external actions with receipts and a separate verification lane.

Constraints:
- Update `README.md`, `OBJECTIVE.md`, `REVIEWER_PROMPT.md`, `TOOL_GRANTS.md`, `OPERATOR_LOG.md`, `RESOURCES.md`, `JOURNEY.md`.
- Replace or retire stale `SESSION.md` with a real `RUNBOOK.md` if appropriate.
- Explicitly define:
  - autonomy vs assistance,
  - official product deploy lane,
  - official verification lane,
  - receipts,
  - operator relay,
  - preflight,
  - verified-user evidence rules.
- Do not say or imply that approval equals posting.
- Do not say or imply “no human in the loop.”

Done when:
- The docs match the runtime model.
- The docs no longer contain the known misleading claims.
- Operators have a short runbook for preflight, review, receipt recording, and status checks.

---

## Prompt 8 — Add regression tests for the known failure modes

Goal:
Add a lightweight automated regression suite covering the failures already observed and the new critical invariants.

Context:
- vNext is supposed to prevent the same class of failures from recurring.
- The highest-value tests are the ones tied to real prior failures and the two hard loops.

Constraints:
- Cover at least these cases:
  1. reviewer key missing,
  2. `openclaw` missing from PATH,
  3. malformed structured tool request,
  4. approved outreach without receipt stays draft-only,
  5. receipt recording transitions an approved draft to `posted`,
  6. failed public URL check blocks G2,
  7. one synthetic verification event increments the derived verified-user count.
- Use the lightest-weight test harness that fits the repo.
- Make tests runnable locally.

Done when:
- There is a documented test command.
- The regression suite covers both hard loops and the known infra failures.
- The summary explains what is covered.

---

## Prompt 9 — Optional later: direct executor or second distribution surface

Goal:
Only after the relay-based loop is proven, add one more execution surface if needed.

Context:
- This is intentionally not part of the core vNext sequence.
- Do not attempt this before the relay and verification loops are already proven.

Constraints:
- Pick exactly one extension:
  - a dedicated direct executor for one posting surface, or
  - one additional distribution surface.
- Keep it narrow and auditable.
- Do not add DMs, payments, or broad auth.

Done when:
- The extension is narrower than the original pilot scope.
- It does not weaken the receipt and verification guarantees.
