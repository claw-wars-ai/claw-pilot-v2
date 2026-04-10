# Pilot Escalation Bundle

This bundle collates the local handoff docs and the runtime artifacts retrieved from the Minisforum host on 2026-04-10.

## Purpose

- Give an escalation reviewer one place to inspect source documents, runtime logs, and the final state.
- Preserve both the stale handoff copy and the authoritative runtime copy for comparison.
- Provide a single consolidated dossier for LLM review without losing raw evidence.

## Bundle Layout

- `root-handoff/`: the local handoff docs that were present before SSH retrieval.
- `runtime-artifacts/`: the authoritative docs copied from `~/claw-pilot/pilot-workspace/` and `~/claw-pilot/heartbeat.log` on the Minisforum host.
- `PILOT_DOSSIER.md`: concatenated review packet with the key docs and the full heartbeat chronology.
- `ESCALATION_PROMPT.md`: a ready-to-use prompt for another LLM.

## Final Run State

- Gates: `G1 PASS | G2 PASS | G3 FAIL | G4 FAIL`.
- Verified users: `0 / 10`.
- Live product URL: `https://jdsteel61.github.io/pilot-image-resizer-site/`.
- Build outcome: product shipped; distribution and verification failed.

## Key Runtime Risks To Review

- Repeated `openclaw: command not found` failures during early cron heartbeats.
- Surge deployment failed and required operator remediation to GitHub Pages.
- Reviewer auth failed at HB8 because `XAI_API_KEY` was not set.
- `heartbeat.sh` crashed at line 235 during HB14 and HB15 while parsing a tool request.
- Multiple later heartbeats produced approved drafts but no posting proof.

## Runtime Artifact Inventory

- `runtime-artifacts/HB1_EXECUTION.md` (2894 bytes)
- `runtime-artifacts/HB1_PLAN.md` (1592 bytes)
- `runtime-artifacts/HB10_EXECUTION.md` (686 bytes)
- `runtime-artifacts/HB10_PLAN.md` (1381 bytes)
- `runtime-artifacts/HB11_EXECUTION.md` (439 bytes)
- `runtime-artifacts/HB11_PLAN.md` (1102 bytes)
- `runtime-artifacts/HB12_EXECUTION.md` (430 bytes)
- `runtime-artifacts/HB12_PLAN.md` (1100 bytes)
- `runtime-artifacts/HB13_EXECUTION.md` (345 bytes)
- `runtime-artifacts/HB13_PLAN.md` (972 bytes)
- `runtime-artifacts/HB14_EXECUTION.md` (393 bytes)
- `runtime-artifacts/HB14_PLAN.md` (1015 bytes)
- `runtime-artifacts/HB15_EXECUTION.md` (274 bytes)
- `runtime-artifacts/HB15_PLAN.md` (842 bytes)
- `runtime-artifacts/HB16_EXECUTION.md` (366 bytes)
- `runtime-artifacts/HB16_PLAN.md` (714 bytes)
- `runtime-artifacts/HB17_EXECUTION.md` (336 bytes)
- `runtime-artifacts/HB17_PLAN.md` (344 bytes)
- `runtime-artifacts/HB18_EXECUTION.md` (438 bytes)
- `runtime-artifacts/HB18_PLAN.md` (696 bytes)
- `runtime-artifacts/HB19_EXECUTION.md` (338 bytes)
- `runtime-artifacts/HB19_PLAN.md` (362 bytes)
- `runtime-artifacts/HB2_EXECUTION.md` (2133 bytes)
- `runtime-artifacts/HB2_PLAN.md` (1612 bytes)
- `runtime-artifacts/HB20_EXECUTION.md` (781 bytes)
- `runtime-artifacts/HB20_PLAN.md` (332 bytes)
- `runtime-artifacts/HB3_EXECUTION.md` (1455 bytes)
- `runtime-artifacts/HB3_PLAN.md` (985 bytes)
- `runtime-artifacts/HB4_EXECUTION.md` (904 bytes)
- `runtime-artifacts/HB4_PLAN.md` (1015 bytes)
- `runtime-artifacts/HB5_EXECUTION.md` (817 bytes)
- `runtime-artifacts/HB5_PLAN.md` (743 bytes)
- `runtime-artifacts/HB6_EXECUTION.md` (804 bytes)
- `runtime-artifacts/HB6_PLAN.md` (747 bytes)
- `runtime-artifacts/HB7_EXECUTION.md` (1112 bytes)
- `runtime-artifacts/HB7_PLAN.md` (622 bytes)
- `runtime-artifacts/HB8_EXECUTION.md` (469 bytes)
- `runtime-artifacts/HB8_PLAN.md` (1508 bytes)
- `runtime-artifacts/HB9_EXECUTION.md` (468 bytes)
- `runtime-artifacts/HB9_PLAN.md` (1354 bytes)
- `runtime-artifacts/heartbeat.log` (7067 bytes)
- `runtime-artifacts/heartbeat.remote.sh` (19625 bytes)
- `runtime-artifacts/index.html` (11465 bytes)
- `runtime-artifacts/JOURNEY.md` (206 bytes)
- `runtime-artifacts/OPERATOR_LOG.md` (2793 bytes)
- `runtime-artifacts/OUTBOX.md` (444 bytes)
- `runtime-artifacts/RESOURCES.md` (215 bytes)
- `runtime-artifacts/TOOL_GRANTS.md` (5489 bytes)
