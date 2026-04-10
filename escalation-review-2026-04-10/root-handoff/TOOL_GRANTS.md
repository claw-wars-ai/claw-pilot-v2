# TOOL GRANTS

Agent reads at start of each heartbeat.
**No raw secrets here.** Reference secret names only.

## Pre-Granted (HB0)

### GRANTED — Static Site Deployment (Surge.sh)
**Access**: `npx surge` available in workspace. Free tier, no auth needed.
**Limits**: One project. No custom domain unless requested.

### GRANTED — Analytics (privacy-respecting)
**Access**: Embed a no-cookie analytics snippet (Plausible script tag or self-hosted counter).
**Limits**: Page views and core action completions only. No PII. No cookies.

### GRANTED — GitHub Repo Creation
**Access**: GitHub token stored as OpenClaw secret `github_pat`.
**Limits**: Public repos only. One repo for this pilot.

## Auto-Approved (LOW risk tools — no operator needed)
_(orchestrator auto-approves LOW risk requests and logs them here)_

## Operator-Approved (MEDIUM/HIGH risk)
_(operator reviews and decides)_

## Denied
_(with reasons)_

## Outreach Decisions (from AI Reviewer)
| HB | Platform | Decision | Reason | Operator Override? |
|----|----------|----------|--------|--------------------|
| — | — | — | — | — |

---
### Format:
```
### [GRANTED/DENIED] — HB{n} — {Tool Name}
**Decision**: GRANTED / DENIED
**Reason**: ...
**Access**: [secret name or instructions — NOT the secret]
**Limits**: [restrictions]
```
