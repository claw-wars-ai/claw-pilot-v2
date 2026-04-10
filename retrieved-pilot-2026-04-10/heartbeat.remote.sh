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
#   0 * * * * cd /path/to/project && ./heartbeat.sh >> heartbeat.log 2>&1
# ============================================================================

set -Eeuo pipefail

WORKSPACE="${WORKSPACE:-./pilot-workspace}"
MODEL="${MODEL:-grok-4-1-fast-reasoning}"
REVIEWER_MODEL="${REVIEWER_MODEL:-grok-4-1-fast-non-reasoning}"
RUNNER="${RUNNER:-openclaw}"
XAI_API_KEY="${XAI_API_KEY:-}"
if [ -z "$XAI_API_KEY" ] && [ -f "$HOME/.openclaw/agents/pilot/agent/auth-profiles.json" ]; then
    XAI_API_KEY="$(python3 -c 'import json; from pathlib import Path; cfg = json.loads(Path.home().joinpath(".openclaw/agents/pilot/agent/auth-profiles.json").read_text(encoding="utf-8")); entry=((cfg.get("profiles") or {}).get("xai:manual") or {}); print(next((entry.get(k) for k in ("token", "apiKey", "api_key", "secret") if entry.get(k)), ""), end="")')"
fi
OPENCLAW_BIN="${OPENCLAW_BIN:-}"
if [ -z "$OPENCLAW_BIN" ]; then
    OPENCLAW_BIN="$(command -v openclaw 2>/dev/null || true)"
fi
if [ -z "$OPENCLAW_BIN" ] && [ -x "/home/jeremy/.npm-global/bin/openclaw" ]; then
    OPENCLAW_BIN="/home/jeremy/.npm-global/bin/openclaw"
fi
MAX_HEARTBEATS=20
DRY_RUN=false
ACTION="run"
TIMESTAMP="$(date -u +"%Y-%m-%dT%H:%M:%SZ")"
NOTIFIED_ERROR=false
TELEGRAM_BOT_TOKEN="${TELEGRAM_BOT_TOKEN:-}"
TELEGRAM_CHAT_ID="${TELEGRAM_CHAT_ID:-}"
if [ -f "$HOME/.openclaw/openclaw.json" ]; then
    [ -z "$TELEGRAM_BOT_TOKEN" ] && TELEGRAM_BOT_TOKEN="$(python3 -c 'import json; from pathlib import Path; cfg=json.loads(Path.home().joinpath(".openclaw/openclaw.json").read_text(encoding="utf-8")); chan=((cfg.get("channels") or {}).get("telegram") or {}); print((chan.get("botToken") if chan.get("enabled") else "") or "", end="")')"
    [ -z "$TELEGRAM_CHAT_ID" ] && TELEGRAM_CHAT_ID="$(python3 -c 'import json; from pathlib import Path; cfg=json.loads(Path.home().joinpath(".openclaw/openclaw.json").read_text(encoding="utf-8")); chan=((cfg.get("channels") or {}).get("telegram") or {}); allow=(chan.get("allowFrom") or []); print(str(allow[0]) if chan.get("enabled") and allow else "", end="")')"
fi

for arg in "$@"; do
    case "$arg" in
        --dry-run)      DRY_RUN=true ;;
        --status)       ACTION="status" ;;
        --reset)        ACTION="reset" ;;
        --review-test)  ACTION="review-test" ;;
        --notify-test)  ACTION="notify-test" ;;
    esac
done

log() { echo "[$(date -u +"%Y-%m-%dT%H:%M:%SZ")] $*"; }

notify_telegram() {
    local message="$1"
    [ -n "$TELEGRAM_BOT_TOKEN" ] || return 0
    [ -n "$TELEGRAM_CHAT_ID" ] || return 0
    curl -s -X POST "https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/sendMessage"         -d "chat_id=${TELEGRAM_CHAT_ID}"         --data-urlencode "text=${message}" >/dev/null 2>&1 || true
}

alert_error() {
    local message="$1"
    log "ERROR: ${message}"
    if [ "$ACTION" = "run" ] && [ "$NOTIFIED_ERROR" != "true" ]; then
        NOTIFIED_ERROR=true
        notify_telegram "claw-pilot error on $(hostname) at ${TIMESTAMP} (HB${hb:-?}): ${message}. Check ~/claw-pilot/heartbeat.log"
    fi
}

on_error() {
    local line="$1"
    local code="$2"
    alert_error "heartbeat.sh failed at line ${line} with exit ${code}"
    exit "$code"
}

trap 'on_error ${LINENO} $?' ERR

get_hb_number() {
    local last
    last=$(ls "${WORKSPACE}"/HB*_PLAN.md 2>/dev/null \
        | sed 's/.*HB\([0-9]*\)_PLAN.md/\1/' \
        | sort -n | tail -1 2>/dev/null) || true
    echo "${last:-0}"
}

verify_public_url() {
    local url="$1"
    local status
    status=$(curl -L -s -o /dev/null -w "%{http_code}" "$url" || true)
    if [[ "$status" =~ ^2[0-9][0-9]$ ]]; then
        echo "$status"
        return 0
    fi
    echo "${status:-000}"
    return 1
}

enforce_g2_verification() {
    local exec_file="${WORKSPACE}/HB${hb}_EXECUTION.md"
    local journey_file="${WORKSPACE}/JOURNEY.md"
    local resources_file="${WORKSPACE}/RESOURCES.md"
    local url
    local status

    [ "$hb" -ne 7 ] && return
    [ ! -f "$exec_file" ] && return

    url=$(grep -Eho 'https://[^ )]+' "$exec_file" "$journey_file" "$resources_file" 2>/dev/null | head -1 || true)
    if [ -z "$url" ]; then
        log "WARNING: G2 verification skipped - no public URL found in heartbeat artifacts."
        return
    fi

    if status=$(verify_public_url "$url"); then
        log "G2 verification succeeded: ${url} (HTTP ${status})"
        return
    fi

    alert_error "G2 verification failed for ${url} (HTTP ${status}); treating G2 as NOT PASSED"

    if ! grep -q 'G2 deployment verification failed' "$exec_file" 2>/dev/null; then
        cat >> "$exec_file" <<EOF

## Orchestrator Verification
G2 deployment verification failed at ${TIMESTAMP}. ${url} returned HTTP ${status}. Treat G2 as NOT PASSED.
EOF
    fi

    if [ -f "$journey_file" ] && ! grep -q 'G2 NOT PASSED' "$journey_file" 2>/dev/null; then
        cat >> "$journey_file" <<EOF

### Orchestrator Verification ? ${TIMESTAMP}
**Phase**: Build
**Gate**: G2 NOT PASSED
**Key**: Deployment verification failed
**Result**: ${url} returned HTTP ${status}
**Users**: 0/10
**Next**: Re-run deploy and verify HTTP 200 before outreach
EOF
    fi

    if [ -f "$resources_file" ] && ! grep -q 'Treat G2 as NOT PASSED' "$resources_file" 2>/dev/null; then
        cat >> "$resources_file" <<EOF

## Orchestrator Verification ? ${TIMESTAMP}
- Deployment verification failed for ${url} (HTTP ${status}).
- Treat G2 as NOT PASSED until the public URL returns HTTP 200.
EOF
    fi
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
                      echo "You are a strict content reviewer. Evaluate for honesty (no impersonation or fabricated first-hand claims), relevance, value, and tone. Respond with APPROVE, DENY: reason, or EDIT: changes. Default to DENY if uncertain.")

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
    risk=$(awk 'BEGIN{IGNORECASE=1} /^\*\*Risk\*\*:|^Risk:/ { print toupper($0); exit }' "$tool_req")

    if [ -z "$risk" ]; then
        log "TOOL REQUEST missing parsable risk field"
        log "    Review: ${tool_req}"
        return
    fi

    if echo "$risk" | grep -q "LOW"; then
        log "AUTO-APPROVING low-risk tool request"
        local tool_name
        tool_name=$(awk 'BEGIN{IGNORECASE=1} /^\*\*Tool\*\*:|^Tool:/ { sub(/^[^:]*:[[:space:]]*/, "", $0); print; exit }' "$tool_req")
        [ -z "$tool_name" ] && tool_name="Tool request"

        # Append to TOOL_GRANTS.md
        cat >> "${WORKSPACE}/TOOL_GRANTS.md" << GRANT

### GRANTED (auto) - HB${hb} - ${tool_name}
**Decision**: GRANTED (auto-approved, LOW risk)
**Timestamp**: ${TIMESTAMP}
GRANT

        # Archive the request
        mv "$tool_req" "${WORKSPACE}/logs/tool_request_hb${hb}.md" 2>/dev/null || true
    else
        log "TOOL REQUEST requires operator review (MEDIUM/HIGH risk)"
        log "    Review: ${tool_req}"
    fi
}

# ============================================================================
# REVIEW OUTREACH FROM PLAN
# ============================================================================

process_outreach() {
    local plan_file="${WORKSPACE}/HB${hb}_PLAN.md"
    local outbox_file="${WORKSPACE}/OUTBOX.md"
    rm -f "$outbox_file"

    if [ ! -f "$plan_file" ]; then
        return
    fi

    if ! grep -qi "Proposed Outreach" "$plan_file"; then
        return
    fi

    log "Found outreach proposals - running AI reviewer..."

    local outreach_section
    outreach_section=$(sed -n '/## Proposed Outreach/,/^## /p' "$plan_file" | head -80)

    local first_content_line
    first_content_line=$(printf '%s
' "$outreach_section" | sed '1d' | sed '/^[[:space:]]*$/d' | head -1 | tr -d '')
    if [ -z "$first_content_line" ] || printf '%s' "$first_content_line" | grep -qi '^none'; then
        log "No substantive outreach content to review."
        return
    fi

    local decision
    decision=$(review_outreach         "extracted from plan"         "see content"         "$outreach_section"         "AI agent pilot experiment - agent building a self-serve web tool and seeking users. Approval is draft approval only, not publication.")

    log "Reviewer decision: ${decision}"

    local outbox_status="DENIED"
    if echo "$decision" | grep -q '^APPROVE'; then
        outbox_status="APPROVED DRAFT ONLY"
    elif echo "$decision" | grep -q '^EDIT:'; then
        outbox_status="EDIT REQUIRED"
    fi

    cat > "$outbox_file" <<EOF
# OUTBOX - HB${hb}

**Status**: ${outbox_status}
**Generated**: ${TIMESTAMP}
**Source**: HB${hb}_PLAN.md

This file is a manual handoff only. Review does not mean posting happened.
Do not claim outreach was posted unless there is explicit evidence such as a public URL, post ID, screenshot, or operator confirmation.

## Reviewer Decision
${decision}

## Draft
${outreach_section}
EOF

    local short_decision
    short_decision=$(echo "$decision" | head -1 | cut -c1-80)
    cat >> "${WORKSPACE}/TOOL_GRANTS.md" << REVIEW

### Outreach Review - HB${hb}
**Decision**: ${short_decision}
**Posting status**: NOT POSTED BY ORCHESTRATOR
**Outbox**: OUTBOX.md updated
**Full response**: ${decision}
**Timestamp**: ${TIMESTAMP}
REVIEW

    echo "| ${TIMESTAMP} | ${hb} | AI_REVIEW | Outreach reviewed: ${short_decision} | draft only |"         >> "${WORKSPACE}/OPERATOR_LOG.md"

    log "OUTBOX updated: ${outbox_status}"
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
        grep -E '^\*\*(Phase|Gate|Users|Next)\*\*:' "${WORKSPACE}/JOURNEY.md" \
            | tail -4
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
if [ "$ACTION" = "notify-test" ]; then
    notify_telegram "claw-pilot test notification from $(hostname) at ${TIMESTAMP}"
    echo "Notification test sent."
    exit 0
fi

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
        alert_error "already running (PID ${lock_pid})"
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
If you want to post publicly: put exact text under '## Proposed Outreach' in your PLAN.md. The AI reviewer will evaluate it and write OUTBOX.md.
Approval is draft approval only. It is not evidence that anything was posted.
Use outreach states precisely: proposed, reviewed, approved draft only, posted, engaged.
Never claim posted unless you have explicit evidence such as a public URL, post ID, screenshot, or operator confirmation.
For this product, pageviews are awareness only, upload/process_start are engagement only, and download on the public deployment is the core action.
If at a gate deadline: include a gate assessment in EXECUTION.md.

You have ${MAX_HEARTBEATS} heartbeats total. You are on #${hb}. Budget your time."

log_file="${WORKSPACE}/logs/hb${hb}_$(date +%s).log"

# Run agent
case "$RUNNER" in
    openclaw)
        if [ -z "$OPENCLAW_BIN" ]; then
            alert_error "openclaw binary not found. Set OPENCLAW_BIN or install it on PATH."
            exit 1
        fi
        "$OPENCLAW_BIN" agent --local             --agent pilot             --message "$prompt"             --thinking medium             2>&1 | tee "$log_file"
        ;;
    claude-code)
        claude --model "$MODEL" \
            --print \
            --dangerously-skip-permissions \
            "$prompt" \
            2>&1 | tee "$log_file"
        ;;
    *)
        alert_error "unknown runner ${RUNNER}"
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
    alert_error "missing expected heartbeat artifacts: ${missing[*]}"
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

# Verify gate-critical public deployment before treating G2 as passed
enforce_g2_verification

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

log "HB${hb} complete. Next HB in ~1 hour."
