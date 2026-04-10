# 🦞 Claw Pilot

**Question**: Can a sandboxed AI agent go from blank workspace to deployed tool with 10 real users — with no human in the loop?

## Design
- 1 agent, 1 model (Grok 4.1 Fast reasoning), 20 heartbeats (40 hours)
- AI reviewer (Grok 4.1 Fast non-reasoning) gates all outbound comms
- LOW-risk tool requests auto-approved; MEDIUM/HIGH queued for operator
- Operator only intervenes for MEDIUM/HIGH tool grants and reviewer overrides
- Everything logged for honest post-mortem

## Files

| File | Owner | Purpose |
|------|-------|---------|
| OBJECTIVE.md | Static | Mission, rules, protocol |
| JOURNEY.md | Agent | Running log + gate tracker |
| RESOURCES.md | Agent | Product state, user evidence |
| TOOL_GRANTS.md | Orchestrator + Operator | Approvals, reviewer decisions |
| OPERATOR_LOG.md | Operator + Orchestrator | Every intervention |
| REVIEWER_PROMPT.md | Static | Rubric for AI reviewer |
| TOOL_REQUEST.md | Agent | Created when tools needed |
| HBn_PLAN.md | Agent | Per-heartbeat plan |
| HBn_EXECUTION.md | Agent | Per-heartbeat results |
| heartbeat.sh | Infra | Orchestration + reviewer |

## Gates

| Gate | HB | Requirement |
|------|----|-------------|
| G1 | 3 | Problem selected with evidence |
| G2 | 7 | Public working URL |
| G3 | 10 | First verified external user |
| G4 | 20 | 10 verified external users |

## Cost Estimate
~$0.05-0.15 per heartbeat (agent) + ~$0.001 per review call.
**20 heartbeats ≈ $1-3 total.** Plus ~$0.10-0.50 for web/X search calls.

## Ship Steps

### 1. Environment (30 min)
```bash
# Install OpenClaw
curl -fsSL https://openclaw.ai/install.sh | bash
openclaw onboard --install-daemon

# Add xAI key
openclaw models auth paste-token --provider xai

# Set model
openclaw config set agents.defaults.model.primary "xai/grok-4-1-fast-reasoning"

# Install deploy tool
npm install -g surge

# Install jq (needed for reviewer API calls)
# macOS: brew install jq
# Ubuntu: sudo apt install jq
```

### 2. Agent Setup (15 min)
```bash
# Create agent
openclaw agents add pilot --workspace ./pilot-workspace --non-interactive

# Copy all files into workspace
cp OBJECTIVE.md JOURNEY.md RESOURCES.md TOOL_GRANTS.md OPERATOR_LOG.md \
   ./pilot-workspace/

# Keep REVIEWER_PROMPT.md and heartbeat.sh in project root (not workspace)

# Enable sandbox in ~/.openclaw/openclaw.json:
# "sandbox": { "mode": "non-main", "scope": "session", "docker": { "network": "bridge" } }

# Export API key for reviewer
export XAI_API_KEY="your-key-here"
# (add to .bashrc/.zshrc for persistence)
```

### 3. Verify (10 min)
```bash
# Health check
openclaw doctor

# Test the script
chmod +x heartbeat.sh
./heartbeat.sh --dry-run

# Test the AI reviewer
./heartbeat.sh --review-test

# Check status
./heartbeat.sh --status

# (Optional) Pre-create a GitHub token as OpenClaw secret
openclaw secrets set github_pat "ghp_your_token"
```

### 4. Run HB1
```bash
./heartbeat.sh
```
Then read `pilot-workspace/HB1_PLAN.md` and `HB1_EXECUTION.md`.

### 5. Set Up Cron
```bash
crontab -e
# Add:
# 0 */2 * * * cd /full/path/to/project && ./heartbeat.sh >> heartbeat.log 2>&1
```

### 6. Walk Away
Check in once or twice a day:
- `./heartbeat.sh --status` for quick overview
- Scan `OPERATOR_LOG.md` for any MEDIUM/HIGH tool requests needing approval
- Read latest `HBn_EXECUTION.md` for content ideas
- At gates (HB3, 7, 10, 20): read the gate assessment

## Security Checklist
- [ ] Sandbox enabled in openclaw.json
- [ ] Gateway auth token set
- [ ] Workspace scoped (not ~/)
- [ ] No personal accounts connected
- [ ] `openclaw doctor` green
- [ ] XAI_API_KEY set as env var (not in any file)
- [ ] `--review-test` returns sensible reviewer decisions
