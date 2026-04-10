#!/usr/bin/env bash
# ============================================================================
# heartbeat.sh — Claw Pilot Orchestrator
#
# Single agent, AI-reviewed outreach, 20 heartbeats, minimal operator involvement.
#
# Usage:
#   ./heartbeat.sh                # Run next heartbeat
#   ./heartbeat.sh --dry-run      # Preview
#   ./heartbeat.sh --status       # Current state
#   ./heartbeat.sh --reset        # Reset to HB0
#   ./heartbeat.sh --review-test  # Test the AI reviewer with sample content
#
# Env:
#   WORKSPACE       (default: ./pilot-workspace)
#   MODEL           (default: xai/grok-4-1-fast-reasoning)
#   REVIEWER_MODEL  (default: xai/grok-4-1-fast-non-reasoning)
#   RUNNER          (default: openclaw)  — openclaw | claude-code
#   XAI_API_KEY     (required for reviewer)
#
# Cron:
#   0 */2 * * * cd /path/to/project && ./heartbeat.sh >> heartbeat.log 2>&1
# ============================================================================

set -euo pipefail

WORKSPACE="${WORKSPACE:-./pilot-workspace}"
MODEL="${MODEL:-xai/grok-4-1-fast-reasoning}"
REVIEWER_MODEL="${REVIEWER_MODEL:-xai/grok-4-1-fast-non-reasoning}"
RUNNER="${RUNNER:-openclaw}"
XAI_API_KEY="${XAI_API_KEY:-}"
MAX_HEARTBEATS=20
DRY_RUN=false
ACTION="run"
TIMESTAMP="$(date -u +"%Y-%m-%dT%H:%M:%SZ")"

for arg in "$@"; do
    case "$arg" in
        --dry-run)      DRY_RUN=true ;;
        --status)       ACTION="status" ;;
        --reset)        ACTION="reset" ;;
        --review-test)  ACTION="review-test" ;;
    esac
done

log() { echo "[$(date -u +"%Y-%m-%dT%H:%M:%SZ")] $*"; }

get_hb_number() {
    local last
    last=$(ls "${WORKSPACE}"/HB*_PLAN.md 2>/dev/null \
        | sed 's/.*HB\([0-9]*\)_PLAN.md/\1/' \
        | sort -n | tail -1 2>/dev/null) || true
    echo "${last:-0}"
}

# ============================================================================
# AI REVIEWER
# ============================================================================
# Calls the reviewer model to evaluate proposed outreach content.
# Returns: APPROVE / DENY: reason / EDIT: changes
# ============================================================================

review_outreach() {
    local platform="$1"
    local target="$2"
    local content="$3"
    local context="$4"

    if [ -z "$XAI_API_KEY" ]; then
        log "WARNING: XAI_API_KEY not set — cannot run reviewer. Defaulting to DENY."
        echo "DENY: reviewer unavailable (no API key)"
        return
    fi

    local reviewer_prompt
    reviewer_prompt=$(cat "${WORKSPACE}/../REVIEWER_PROMPT.md" 2>/dev/null || \
                      cat "$(dirname "$0")/REVIEWER_PROMPT.md" 2>/dev/null || \
                      echo "You are a strict content reviewer. Evaluate for spam, transparency (must mention AI agent), relevance, and tone. Respond with APPROVE, DENY: reason, or EDIT: changes. Default to DENY if uncertain.")

    local user_msg="Platform: ${platform}
Target: ${target}
Proposed content: ${content}
Context: ${context}"

    local payload
    payload=$(jq -n \
        --arg model "$REVIEWER_MODEL" \
        --arg system "$reviewer_prompt" \
        --arg user "$user_msg" \
        '{
            model: $model,
            max_tokens: 500,
            messages: [
                { role: "system", content: $system },
                { role: "user", content: $user }
            ]
        }')

    local response
    response=$(curl -s "https://api.x.ai/v1/chat/completions" \
        -H "Content-Type: application/json" \
        -H "Authorization: Bearer ${XAI_API_KEY}" \
        -d "$payload" 2>/dev/null)

    local decision
    decision=$(echo "$response" | jq -r '.choices[0].message.content // "DENY: reviewer error"' 2>/dev/null)

    if [ -z "$decision" ] || [ "$decision" = "null" ]; then
        decision="DENY: reviewer returned empty response"
    fi

    echo "$decision"
}

# ============================================================================
# AUTO-APPROVE LOW RISK TOOL REQUESTS
# ============================================================================

process_tool_requests() {
    local tool_req="${WORKSPACE}/TOOL_REQUEST.md"
    if [ ! -f "$tool_req" ]; then
        return
    fi

    local risk
    risk=$(grep -i "Risk:" "$tool_req" | head -1 | tr '[:lower:]' '[:upper:]')

    if echo "$risk" | grep -q "LOW"; then
        log "AUTO-APPROVING low-risk tool request"
        local tool_name
        tool_name=$(grep -i "^##\|Tool:" "$tool_req" | head -1 | sed 's/.*: //')

        # Append to TOOL_GRANTS.md
        cat >> "${WORKSPACE}/TOOL_GRANTS.md" << GRANT

### GRANTED (auto) — HB${hb} — ${tool_name}
**Decision**: GRANTED (auto-approved, LOW risk)
**Timestamp**: ${TIMESTAMP}
GRANT

        # Archive the request
        mv "$tool_req" "${WORKSPACE}/logs/tool_request_hb${hb}.md" 2>/dev/null || true
    else
        log "⚠️  TOOL REQUEST requires operator review (MEDIUM/HIGH risk)"
        log "    Review: ${tool_req}"
    fi
}

# ============================================================================
# REVIEW OUTREACH FROM PLAN
# ============================================================================

process_outreach() {
    local plan_file="${WORKSPACE}/HB${hb}_PLAN.md"
    if [ ! -f "$plan_file" ]; then
        return
    fi

    if ! grep -qi "Proposed Outreach" "$plan_file"; then
        return
    fi

    log "Found outreach proposals — running AI reviewer..."

    # Extract outreach section (everything after "## Proposed Outreach")
    local outreach_section
    outreach_section=$(sed -n '/## Proposed Outreach/,/^## /p' "$plan_file" | head -50)

    # Simple review of full section (in production, parse individual posts)
    local decision
    decision=$(review_outreach \
        "extracted from plan" \
        "see content" \
        "$outreach_section" \
        "AI agent pilot experiment — agent building a self-serve web tool and seeking users")

    log "Reviewer decision: ${decision}"

    # Log to TOOL_GRANTS.md
    local short_decision
    short_decision=$(echo "$decision" | head -1 | cut -c1-80)
    cat >> "${WORKSPACE}/TOOL_GRANTS.md" << REVIEW

### Outreach Review — HB${hb}
**Decision**: ${short_decision}
**Full response**: ${decision}
**Timestamp**: ${TIMESTAMP}
REVIEW

    # Log to OPERATOR_LOG.md
    echo "| ${TIMESTAMP} | ${hb} | AI_REVIEW | Outreach reviewed: ${short_decision} | — |" \
        >> "${WORKSPACE}/OPERATOR_LOG.md"
}

# ============================================================================
# STATUS
# ============================================================================
if [ "$ACTION" = "status" ]; then
    hb_count="$(get_hb_number)"
    echo ""
    echo "  🦞 CLAW PILOT"
    echo "  Heartbeat: ${hb_count} / ${MAX_HEARTBEATS}"
    echo "  Model: ${MODEL}"
    echo "  Reviewer: ${REVIEWER_MODEL}"
    echo ""
    if [ -f "${WORKSPACE}/JOURNEY.md" ]; then
        grep -E "(Phase|Problem|Solution|Verified|users|Gate)" "${WORKSPACE}/JOURNEY.md" \
            | head -12
    fi
    echo ""
    [ -f "${WORKSPACE}/TOOL_REQUEST.md" ] && echo "  ⚠️  TOOL REQUEST pending"
    echo ""
    exit 0
fi

# ============================================================================
# RESET
# ============================================================================
if [ "$ACTION" = "reset" ]; then
    log "Resetting..."
    rm -f "${WORKSPACE}"/HB*_PLAN.md "${WORKSPACE}"/HB*_EXECUTION.md
    rm -f "${WORKSPACE}/TOOL_REQUEST.md"
    rm -rf "${WORKSPACE}/logs"
    log "Cleared heartbeat files. Manually reset JOURNEY.md and RESOURCES.md if needed."
    exit 0
fi

# ============================================================================
# REVIEW TEST
# ============================================================================
if [ "$ACTION" = "review-test" ]; then
    echo "Testing AI reviewer with sample content..."
    result=$(review_outreach \
        "reddit" \
        "r/webdev" \
        "Hey everyone! I built a cool tool that converts JSON to CSV instantly. Check it out at example.com! It's free and works in your browser." \
        "AI agent pilot — testing reviewer")
    echo "Reviewer says: ${result}"
    echo ""
    result2=$(review_outreach \
        "reddit" \
        "r/webdev" \
        "Hi r/webdev — I'm an AI agent running an experiment to build useful tools. I noticed a lot of posts here about JSON/CSV conversion pain. I built a browser-based converter at example.com (no login, no data sent to servers). Would love feedback on whether this actually solves the problem. Full transparency: this is part of an autonomous AI pilot documented at [link]." \
        "AI agent pilot — testing reviewer")
    echo "Reviewer says: ${result2}"
    exit 0
fi

# ============================================================================
# RUN HEARTBEAT
# ============================================================================

mkdir -p "${WORKSPACE}" "${WORKSPACE}/logs"

# Lock
LOCK="${WORKSPACE}/.heartbeat.lock"
if [ -f "$LOCK" ]; then
    lock_pid="$(cat "$LOCK" 2>/dev/null || echo "")"
    if [ -n "$lock_pid" ] && kill -0 "$lock_pid" 2>/dev/null; then
        log "ERROR: Already running (PID ${lock_pid})"
        exit 1
    fi
    rm -f "$LOCK"
fi
echo $$ > "$LOCK"
trap 'rm -f "$LOCK"' EXIT

# HB number
last_hb="$(get_hb_number)"
hb=$((last_hb + 1))
hb_prev=$((hb - 1))

if [ "$hb" -gt "$MAX_HEARTBEATS" ]; then
    log "Pilot complete — reached HB${MAX_HEARTBEATS}."
    log "Run --status to see final state."
    exit 0
fi

log "=== Heartbeat ${hb} / ${MAX_HEARTBEATS} ==="

if $DRY_RUN; then
    log "DRY RUN — would execute HB${hb}"
    exit 0
fi

# Assemble context
objective="$(sed \
    -e "s/{HB_NUMBER}/${hb}/g" \
    -e "s/{HB_NUMBER_PREV}/${hb_prev}/g" \
    "${WORKSPACE}/OBJECTIVE.md")"

journey="$(cat "${WORKSPACE}/JOURNEY.md" 2>/dev/null || echo "_No journey yet._")"
resources="$(cat "${WORKSPACE}/RESOURCES.md" 2>/dev/null || echo "_No resources yet._")"
tool_grants="$(cat "${WORKSPACE}/TOOL_GRANTS.md" 2>/dev/null || echo "_No tool grants._")"

prev_exec="_First heartbeat. No previous execution._"
[ -f "${WORKSPACE}/HB${hb_prev}_EXECUTION.md" ] && \
    prev_exec="$(cat "${WORKSPACE}/HB${hb_prev}_EXECUTION.md")"

prompt="You are an autonomous agent executing Heartbeat #${hb} of ${MAX_HEARTBEATS}.
Current time: ${TIMESTAMP}

=== OBJECTIVE ===
${objective}

=== JOURNEY ===
${journey}

=== RESOURCES ===
${resources}

=== TOOL GRANTS ===
${tool_grants}

=== PREVIOUS EXECUTION (HB${hb_prev}) ===
${prev_exec}

=== YOUR TASK ===
Follow the Heartbeat Protocol in OBJECTIVE.md exactly.
Phase 1 (Orient) is done — you just read all context above.

Now:
1. Write ${WORKSPACE}/HB${hb}_PLAN.md
2. Execute your plan
3. Write ${WORKSPACE}/HB${hb}_EXECUTION.md
4. Update ${WORKSPACE}/RESOURCES.md
5. Update ${WORKSPACE}/JOURNEY.md

If you need a new tool: write ${WORKSPACE}/TOOL_REQUEST.md
If you want to post publicly: put exact text under '## Proposed Outreach' in your PLAN.md — the AI reviewer will evaluate it.
If at a gate deadline: include a gate assessment in EXECUTION.md.

You have ${MAX_HEARTBEATS} heartbeats total. You are on #${hb}. Budget your time."

log_file="${WORKSPACE}/logs/hb${hb}_$(date +%s).log"

# Run agent
case "$RUNNER" in
    openclaw)
        openclaw agent \
            --model "$MODEL" \
            --workspace "$WORKSPACE" \
            --message "$prompt" \
            --thinking medium \
            2>&1 | tee "$log_file"
        ;;
    claude-code)
        claude --model "$MODEL" \
            --print \
            --dangerously-skip-permissions \
            "$prompt" \
            2>&1 | tee "$log_file"
        ;;
    *)
        log "ERROR: Unknown runner '${RUNNER}'"
        exit 1
        ;;
esac

# --- Post-heartbeat processing ---

log "--- Post-HB${hb} ---"

# Check expected files
missing=()
[ ! -f "${WORKSPACE}/HB${hb}_PLAN.md" ] && missing+=("PLAN")
[ ! -f "${WORKSPACE}/HB${hb}_EXECUTION.md" ] && missing+=("EXECUTION")

if [ ${#missing[@]} -gt 0 ]; then
    log "WARNING: Missing: ${missing[*]}"
    if [ ! -f "${WORKSPACE}/HB${hb}_EXECUTION.md" ]; then
        cat > "${WORKSPACE}/HB${hb}_EXECUTION.md" << STUB
# HB${hb} Execution Log
**Status**: INCOMPLETE
**Timestamp**: ${TIMESTAMP}
**Raw log**: logs/$(basename "$log_file")
STUB
    fi
else
    log "All files present."
fi

# Process tool requests (auto-approve LOW, flag MEDIUM/HIGH)
process_tool_requests

# Process outreach through AI reviewer
process_outreach

# Gate warnings
case $hb in
    3)  log "📍 GATE G1 — Problem selected?" ;;
    7)  log "📍 GATE G2 — Public URL live?" ;;
    10) log "📍 GATE G3 — First verified user?" ;;
    20) log "📍 GATE G4 — 10 verified users? PILOT COMPLETE." ;;
esac

# Context size check
if [ -f "${WORKSPACE}/JOURNEY.md" ]; then
    wc_count="$(wc -w < "${WORKSPACE}/JOURNEY.md")"
    [ "$wc_count" -gt 2000 ] && log "WARNING: JOURNEY.md at ${wc_count} words"
fi

log "HB${hb} complete. Next HB in ~2 hours."
