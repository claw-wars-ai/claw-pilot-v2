# SESSION.md - Claw Pilot Setup Catchup
_Generated: 2026-04-09. For Claude Code / Codex context._

## What This Is
An autonomous AI agent experiment ("Claw Pilot") running on a Minisforum EliteMini Ubuntu PC.
- **Agent**: OpenClaw `pilot` agent, model `xai/grok-4-1-fast-reasoning`
- **Reviewer**: `grok-4-1-fast-non-reasoning` (gates all outbound posts)
- **Goal**: Build a self-serve web tool, get 10 verified external users in 20 heartbeats
- **Product**: Batch image resizer (no watermark, no limits, client-side JS)
- **Heartbeat cron**: every 30 min (`*/30 * * * *`)

## Machine
- **Host**: `jeremy@jeremy-EliteMini-Series` (Minisforum EliteMini, Ubuntu)
- **Pilot dir**: `~/claw-pilot/`
- **Workspace**: `~/claw-pilot/pilot-workspace/`
- **Logs**: `~/claw-pilot/heartbeat.log`, `~/claw-pilot/pilot-workspace/logs/`

## Key Files
| File | Location | Purpose |
|------|----------|---------|
| heartbeat.sh | `~/claw-pilot/` | Orchestrator - runs agent, reviewer, gates |
| OBJECTIVE.md | `~/claw-pilot/pilot-workspace/` | Mission, rules, protocol |
| JOURNEY.md | `~/claw-pilot/pilot-workspace/` | Running log + gate tracker |
| RESOURCES.md | `~/claw-pilot/pilot-workspace/` | Product state, user evidence |
| TOOL_GRANTS.md | `~/claw-pilot/pilot-workspace/` | Approvals, reviewer decisions |
| OPERATOR_LOG.md | `~/claw-pilot/pilot-workspace/` | Every intervention |
| REVIEWER_PROMPT.md | `~/claw-pilot/` | AI reviewer rubric |
| index.html | `~/claw-pilot/pilot-workspace/` | Built in HB4 - image resizer UI |

## Configuration Changes Made
- `heartbeat.sh` model names stripped of `xai/` prefix for reviewer API calls
- `heartbeat.sh` openclaw runner fixed: `openclaw agent --local --agent pilot --message "$prompt" --thinking medium`
- `~/.openclaw/openclaw.json` pilot agent model set to `xai/grok-4-1-fast`
- `~/.openclaw/openclaw.json` Brave Search API key updated to paid tier key
- `XAI_API_KEY` exported and persisted in `~/.bashrc`

## API Keys / Auth
- **xAI**: Configured in `~/.openclaw/openclaw.json` under `auth.xai:manual` + exported as `$XAI_API_KEY`
- **Brave Search**: Paid tier, stored in `~/.openclaw/openclaw.json` at `tools.web.search.apiKey`
- **GitHub PAT**: Available as openclaw secret `github_pat` (for repo creation, pre-granted)
- **Surge.sh**: `npm install -g surge` done, free tier, no auth needed

## Known Issues
- `Failed to discover Ollama models: TypeError: fetch failed` - cosmetic noise, no local GPU, can't disable, ignore
- `No reply from agent` in shell - normal, agent writes files but doesn't echo to chat channel
- Browser tool had port conflict (18792) - resolved by gateway restart

## Gate Status
| Gate | HB | Requirement | Status |
|------|----|-------------|--------|
| G1 | 3 | Problem selected w/ evidence | [PASS] |
| G2 | 7 | Public working URL | PENDING |
| G3 | 10 | First verified external user | PENDING |
| G4 | 20 | 10 verified external users | PENDING |

## Heartbeat Log
| HB | Status | Key output |
|----|--------|------------|
| 1 | [PASS] | 5 problem candidates (Reddit JSON fallback - search was rate limited) |
| 2 | [PASS] | Validated candidates, image resizer selected |
| 3 | [PASS] | G1 PASS, MVP spec written to RESOURCES.md |
| 4 | [PASS] | index.html scaffolded, UI + JS working locally |

## Useful Commands
```bash
# Check status
./heartbeat.sh --status

# Run next heartbeat manually
cd ~/claw-pilot && ./heartbeat.sh

# Read latest execution
latest=$(ls -1 ~/claw-pilot/pilot-workspace/HB*_EXECUTION.md | sort -V | tail -1)
cat "$latest"

# Watch live log
tail -f ~/claw-pilot/heartbeat.log

# Test reviewer
./heartbeat.sh --review-test

# Check cron
crontab -l | grep claw
```

## Next Actions (as of HB4)
- HB5-6: Complete image resizer (canvas resize, JSZip download, analytics snippet)
- HB6: Create GitHub repo, deploy to Surge.sh
- HB7: G2 - public URL must be live
- HB8+: Distribution - find communities, draft outreach through AI reviewer

## Tool Grants Pre-Approved
- Surge.sh static deployment
- GitHub repo creation (public, one repo)
- Privacy-respecting analytics (Plausible snippet, no PII)
