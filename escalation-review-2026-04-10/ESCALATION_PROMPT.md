# Escalation Prompt

Use the bundle contents to perform an escalation review of the Claw Pilot run.

Required outputs:
- State the true final result in plain terms.
- Separate build success from growth/distribution failure.
- Identify the top 5 process or infra failures that most reduced the chance of success.
- Recommend concrete fixes, ordered by likely impact.
- Call out which fixes are product changes, orchestration changes, operator-policy changes, or measurement changes.
- Highlight any places where the documentation disagrees with the runtime evidence.

Constraints:
- Prefer authoritative runtime docs in `runtime-artifacts/` over the stale local handoff copy in `root-handoff/` when they conflict.
- Treat approved outreach drafts as drafts unless there is explicit posting evidence.
- Quote filenames and line numbers when making claims.

Suggested reading order:
1. `PILOT_DOSSIER.md`
2. `runtime-artifacts/RESOURCES.md`
3. `runtime-artifacts/HB20_EXECUTION.md`
4. `runtime-artifacts/heartbeat.log`
5. `runtime-artifacts/TOOL_GRANTS.md`
6. `runtime-artifacts/OPERATOR_LOG.md`
