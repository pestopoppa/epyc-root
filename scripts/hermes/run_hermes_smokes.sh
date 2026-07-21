#!/bin/bash
set -euo pipefail
# run_hermes_smokes.sh — Hermes agent-frontend smoke orchestrator.
#
# Runs a sequence of PASS/FAIL smoke checks against the EPYC Hermes outer shell.
# STATIC checks (config present, upstream pin audit, launch-config validity,
# single-slot/subagent wiring, reference-client dry-run) run every time and need
# no running server. The LIVE end-to-end legs (chat / tool-use / streaming /
# override / multi-turn / reference-client --send / parallel subagents against
# the single-slot llama-server) require a running Hermes backend and are GATED
# behind HERMES_SMOKE_LIVE=1 (or --live); they are SKIPPED by default because
# they run later in the operator's quiet-window loop.
#
# The script is non-mutating and safe to run repeatedly. It never fetches,
# checks out, installs, starts a server, or sends inference traffic unless the
# live gate is explicitly set.
#
# Owning handoff: handoffs/active/hermes-outer-shell.md
#   item G — "Validate subagent + single-slot llama-server interaction"
# Also covers: hermes-agent-index.md "Live Hermes end-to-end smoke checklist".
#
# Usage:
#   bash scripts/hermes/run_hermes_smokes.sh                 # static checks; live legs skipped
#   HERMES_SMOKE_LIVE=1 bash scripts/hermes/run_hermes_smokes.sh --chat --tooluse ...   # live
#
# Leg selectors (choose live legs; omit all to select every leg):
#   --chat --tooluse --streaming --override --multiturn --reference-client --subagent
#
# Options:
#   --live                      Force live legs (same as HERMES_SMOKE_LIVE=1).
#   --target-tag <tag>          Pin-audit target tag (default: env HERMES_SMOKE_TARGET_TAG or v2026.7.1).
#   --base-url <url>            Hermes backend /v1 base URL (default: from hermes-config.yaml).
#   -h, --help                  Show this help and exit.
#
# Environment:
#   HERMES_SMOKE_LIVE=1         Enable the live end-to-end legs.
#   HERMES_SMOKE_TARGET_TAG     Pin-audit target tag override.
#   HERMES_SMOKE_SUBAGENTS=N    Parallel subagents for the live subagent leg (default: 2).
#   HERMES_SMOKE_OUT=<path>     Append a JSONL summary row to this file (default: none).

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"

# --- Logging: graceful fallback stubs, then real agent_log.sh if available ----
agent_task_start() { echo "TASK: ${1:-}"; }
agent_task_end()   { :; }
agent_decision()   { :; }
agent_warn()       { echo "WARN: ${1:-}" >&2; }
if [[ -f "${ROOT}/scripts/utils/agent_log.sh" ]]; then
    # shellcheck source=../utils/agent_log.sh
    source "${ROOT}/scripts/utils/agent_log.sh" 2>/dev/null || true
fi

# --- Config defaults ----------------------------------------------------------
CONFIG_YAML="${SCRIPT_DIR}/hermes-config.yaml"
LAUNCH_SH="${SCRIPT_DIR}/launch_hermes_backend.sh"
SETUP_SH="${SCRIPT_DIR}/setup_hermes.sh"
CHAT_TEMPLATE="${SCRIPT_DIR}/chat-template-no-think.jinja"
PIN_AUDIT="${SCRIPT_DIR}/hermes_pin_audit.py"
REF_CLIENT="${SCRIPT_DIR}/reference_openai_client.py"
HERMES_MD="${SCRIPT_DIR}/HERMES.md"
PLUGINS_DIR="${SCRIPT_DIR}/plugins"

TARGET_TAG="${HERMES_SMOKE_TARGET_TAG:-v2026.7.1}"
BASE_URL_OVERRIDE=""
SUBAGENTS="${HERMES_SMOKE_SUBAGENTS:-2}"
LIVE="${HERMES_SMOKE_LIVE:-0}"

# Leg toggles (empty = auto: enable all legs if no explicit leg flag is given).
LEG_CHAT=0; LEG_TOOLUSE=0; LEG_STREAMING=0; LEG_OVERRIDE=0
LEG_MULTITURN=0; LEG_REFCLIENT=0; LEG_SUBAGENT=0
ANY_LEG=0

usage() { awk 'NR>2 && /^#/{sub(/^# ?/,"");print} NR>2 && !/^#/{exit}' "${BASH_SOURCE[0]}"; }

# --- Argument parsing (permissive: unknown flags warn, do not abort) ----------
while [[ $# -gt 0 ]]; do
    case "$1" in
        --chat)             LEG_CHAT=1; ANY_LEG=1 ;;
        --tooluse)          LEG_TOOLUSE=1; ANY_LEG=1 ;;
        --streaming)        LEG_STREAMING=1; ANY_LEG=1 ;;
        --override)         LEG_OVERRIDE=1; ANY_LEG=1 ;;
        --multiturn)        LEG_MULTITURN=1; ANY_LEG=1 ;;
        --reference-client) LEG_REFCLIENT=1; ANY_LEG=1 ;;
        --subagent)         LEG_SUBAGENT=1; ANY_LEG=1 ;;
        --live)             LIVE=1 ;;
        --target-tag)       TARGET_TAG="${2:?--target-tag needs a value}"; shift ;;
        --target-tag=*)     TARGET_TAG="${1#*=}" ;;
        --base-url)         BASE_URL_OVERRIDE="${2:?--base-url needs a value}"; shift ;;
        --base-url=*)       BASE_URL_OVERRIDE="${1#*=}" ;;
        -h|--help)          usage; exit 0 ;;
        *)                  echo "WARN: ignoring unknown flag: $1" >&2; agent_warn "ignoring unknown flag: $1" ;;
    esac
    shift
done

# No explicit leg selected -> run every live leg (matches a bare invocation).
if [[ "$ANY_LEG" -eq 0 ]]; then
    LEG_CHAT=1; LEG_TOOLUSE=1; LEG_STREAMING=1; LEG_OVERRIDE=1
    LEG_MULTITURN=1; LEG_REFCLIENT=1; LEG_SUBAGENT=1
fi

# --- Result accounting --------------------------------------------------------
PASS=0; FAIL=0; SKIP=0
DETAIL=""
declare -a SUMMARY_LINES=()

record() {  # record <status> <name> <detail>
    local status="$1" name="$2" detail="$3"
    case "$status" in
        PASS) PASS=$((PASS + 1)) ;;
        FAIL) FAIL=$((FAIL + 1)) ;;
        SKIP) SKIP=$((SKIP + 1)) ;;
    esac
    printf '[%-4s] %-24s %s\n' "$status" "$name" "$detail"
    SUMMARY_LINES+=("${status}:${name}")
}

# Run a static check function (name set global DETAIL, returns 0/1).
run_static() {  # run_static <name> <fn>
    local name="$1" fn="$2"
    DETAIL=""
    if "$fn"; then
        record PASS "$name" "$DETAIL"
    else
        record FAIL "$name" "$DETAIL"
    fi
}

# Read a top-level-ish scalar from a YAML/shell file.
yaml_scalar() {  # yaml_scalar <file> <key>
    grep -E "^[[:space:]]*$2:" "$1" 2>/dev/null | head -1 \
        | sed -E "s/^[[:space:]]*$2:[[:space:]]*//; s/[[:space:]]*(#.*)?$//; s/^[\"']//; s/[\"']$//"
}
sh_var() {  # sh_var <file> <VAR>
    grep -E "^$2=" "$1" 2>/dev/null | head -1 | sed -E "s/^$2=//; s/[[:space:]]*(#.*)?$//"
}

# =============================================================================
# STATIC CHECKS
# =============================================================================

check_config_present() {
    local missing=()
    local f
    for f in "$CONFIG_YAML" "$LAUNCH_SH" "$SETUP_SH" "$CHAT_TEMPLATE" \
             "$PIN_AUDIT" "$REF_CLIENT" "$HERMES_MD"; do
        [[ -f "$f" ]] || missing+=("$(basename "$f")")
    done
    [[ -d "$PLUGINS_DIR" ]] || missing+=("plugins/")
    if [[ ${#missing[@]} -gt 0 ]]; then
        DETAIL="missing: ${missing[*]}"
        return 1
    fi
    DETAIL="7 config artifacts + plugins/ present"
    return 0
}

check_pin_audit() {
    if ! command -v python3 >/dev/null 2>&1; then
        DETAIL="python3 not found"
        return 1
    fi
    local out
    if ! out="$(timeout 90 python3 "$PIN_AUDIT" --target-tag "$TARGET_TAG" --json 2>/tmp/hermes_pinaudit.$$.err)"; then
        DETAIL="pin audit exited nonzero: $(tr '\n' ' ' </tmp/hermes_pinaudit.$$.err | head -c 200)"
        rm -f /tmp/hermes_pinaudit.$$.err
        return 1
    fi
    rm -f /tmp/hermes_pinaudit.$$.err
    # Validate JSON + surface describe/dirty. Dirty is informational, not a fail:
    # the expected `?? HERMES.md` symlink is created by setup_hermes.sh.
    local describe dirty
    describe="$(printf '%s' "$out" | python3 -c 'import sys,json;print(json.load(sys.stdin)["current_describe"])' 2>/dev/null)" || {
        DETAIL="pin audit did not emit valid JSON"
        return 1
    }
    dirty="$(printf '%s' "$out" | python3 -c 'import sys,json;d=json.load(sys.stdin)["dirty_entries"];print(len(d))' 2>/dev/null)"
    DETAIL="checkout ${describe}; target ${TARGET_TAG}; dirty=${dirty} (informational)"
    return 0
}

check_launch_config() {
    # Shell syntax must be clean.
    if ! bash -n "$SETUP_SH" 2>/tmp/hermes_synerr.$$; then
        DETAIL="setup_hermes.sh syntax: $(head -c 160 /tmp/hermes_synerr.$$)"
        rm -f /tmp/hermes_synerr.$$; return 1
    fi
    if ! bash -n "$LAUNCH_SH" 2>/tmp/hermes_synerr.$$; then
        DETAIL="launch_hermes_backend.sh syntax: $(head -c 160 /tmp/hermes_synerr.$$)"
        rm -f /tmp/hermes_synerr.$$; return 1
    fi
    rm -f /tmp/hermes_synerr.$$
    # Config <-> launcher consistency.
    local cfg_ctx launch_ctx launch_port cfg_baseurl
    cfg_ctx="$(yaml_scalar "$CONFIG_YAML" context_length)"
    launch_ctx="$(sh_var "$LAUNCH_SH" CONTEXT)"
    launch_port="$(sh_var "$LAUNCH_SH" PORT)"
    cfg_baseurl="$(yaml_scalar "$CONFIG_YAML" base_url)"
    if [[ -z "$cfg_ctx" || -z "$launch_ctx" ]]; then
        DETAIL="could not read context_length (config=$cfg_ctx launch=$launch_ctx)"
        return 1
    fi
    if [[ "$cfg_ctx" != "$launch_ctx" ]]; then
        DETAIL="context_length mismatch: config=$cfg_ctx launcher=$launch_ctx"
        return 1
    fi
    if [[ -z "$cfg_baseurl" ]]; then
        DETAIL="model.base_url missing from hermes-config.yaml"
        return 1
    fi
    # base_url port should match the launcher port.
    if [[ -n "$launch_port" && "$cfg_baseurl" != *":${launch_port}/"* ]]; then
        DETAIL="base_url ($cfg_baseurl) does not point at launcher port $launch_port"
        return 1
    fi
    DETAIL="ctx=$cfg_ctx (config==launcher); base_url=$cfg_baseurl; port=$launch_port"
    return 0
}

# Static half of handoff item G: assert the single-slot / subagent wiring the
# live leg depends on (-np 1, ctx 32768, delegation configured). The live half
# (spawning real parallel subagents) runs only under the live gate.
check_single_slot_wiring() {
    local slots npflag deleg
    slots="$(sh_var "$LAUNCH_SH" SLOTS)"
    if [[ "$slots" != "1" ]]; then
        DETAIL="launcher SLOTS=$slots (expected 1 for single-slot Hermes backend)"
        return 1
    fi
    if ! grep -Eq -- '-np[[:space:]]+"?\$?\{?SLOTS' "$LAUNCH_SH"; then
        DETAIL="launcher does not pass -np \$SLOTS"
        return 1
    fi
    npflag="ok"
    # Delegation subagents must be configured to reuse the single endpoint.
    if ! grep -Eq '^delegation:' "$CONFIG_YAML"; then
        DETAIL="delegation block missing from hermes-config.yaml"
        return 1
    fi
    deleg="$(grep -E '^[[:space:]]*max_iterations:' "$CONFIG_YAML" | head -1 | sed -E 's/.*:[[:space:]]*//')"
    DETAIL="SLOTS=1 (-np $npflag); delegation configured (max_iterations=${deleg:-?}); subagents queue on the single slot"
    return 0
}

# Reference non-Hermes client renders its override recipe with no traffic.
check_reference_client_dryrun() {
    if ! command -v python3 >/dev/null 2>&1; then
        DETAIL="python3 not found"
        return 1
    fi
    if ! timeout 30 python3 "$REF_CLIENT" --print-only --x-show-routing >/tmp/hermes_ref.$$ 2>&1; then
        DETAIL="reference client --print-only failed: $(head -c 160 /tmp/hermes_ref.$$)"
        rm -f /tmp/hermes_ref.$$; return 1
    fi
    if ! grep -q 'x_orchestrator_role' /tmp/hermes_ref.$$; then
        DETAIL="reference client output missing x_orchestrator_role override"
        rm -f /tmp/hermes_ref.$$; return 1
    fi
    rm -f /tmp/hermes_ref.$$
    DETAIL="print-only recipe renders with x_* overrides (no traffic)"
    return 0
}

# =============================================================================
# LIVE LEGS (gated behind HERMES_SMOKE_LIVE=1 / --live)
# =============================================================================

# Resolve the Hermes backend /v1 base URL from config unless overridden.
resolve_base_url() {
    if [[ -n "$BASE_URL_OVERRIDE" ]]; then
        printf '%s' "$BASE_URL_OVERRIDE"; return
    fi
    local u
    u="$(yaml_scalar "$CONFIG_YAML" base_url)"
    printf '%s' "${u:-http://localhost:8099/v1}"
}

live_leg() {  # live_leg <enabled> <name> <fn>
    local enabled="$1" name="$2" fn="$3"
    [[ "$enabled" -eq 1 ]] || return 0
    if [[ "$LIVE" != "1" ]]; then
        record SKIP "live:${name}" "skipped (needs live server; set HERMES_SMOKE_LIVE=1)"
        return 0
    fi
    DETAIL=""
    if "$fn"; then
        record PASS "live:${name}" "$DETAIL"
    else
        record FAIL "live:${name}" "$DETAIL"
    fi
}

_curl_json() {  # _curl_json <url> <json-body> ; echoes body, returns curl rc
    curl -sf --max-time 120 -H 'Content-Type: application/json' \
        -H 'Authorization: Bearer sk-no-key' \
        -X POST "$1" -d "$2"
}

live_health() {
    local base health
    base="$(resolve_base_url)"
    health="${base%/v1}/health"
    if curl -sf --max-time 15 "$health" >/dev/null 2>&1; then
        DETAIL="backend healthy at $health"; return 0
    fi
    DETAIL="no healthy backend at $health (start launch_hermes_backend.sh)"; return 1
}

live_chat() {
    local base body
    base="$(resolve_base_url)"
    body='{"model":"","messages":[{"role":"user","content":"Reply with the single word OK."}],"max_tokens":16,"temperature":0,"seed":42}'
    if _curl_json "${base}/chat/completions" "$body" | grep -q '"choices"'; then
        DETAIL="chat completion returned choices"; return 0
    fi
    DETAIL="chat completion returned no choices"; return 1
}

live_streaming() {
    local base body tmp response
    base="$(resolve_base_url)"
    body='{"model":"","messages":[{"role":"user","content":"Count to three."}],"max_tokens":32,"stream":true,"temperature":0,"seed":42}'
    tmp="$(mktemp /tmp/hermes_streaming.XXXXXX)"
    if curl -sf --max-time 120 -N -H 'Content-Type: application/json' \
        -X POST "${base}/chat/completions" -d "$body" >"$tmp" 2>&1 \
        && grep -q '^data:' "$tmp"; then
        rm -f "$tmp"
        DETAIL="received streamed data: chunks"; return 0
    fi
    response="$(tr '\n' ' ' <"$tmp" | head -c 200)"
    rm -f "$tmp"
    DETAIL="no streamed data: chunks; response=${response}"
    return 1
}

live_tooluse() {
    local base body
    base="$(resolve_base_url)"
    body='{"model":"","messages":[{"role":"user","content":"What is 2+2? Use the calc tool."}],"max_tokens":64,"temperature":0,"seed":42,"tools":[{"type":"function","function":{"name":"calc","description":"evaluate an integer expression","parameters":{"type":"object","properties":{"expr":{"type":"string"}},"required":["expr"]}}}]}'
    if _curl_json "${base}/chat/completions" "$body" | grep -Eq '"tool_calls"|"choices"'; then
        DETAIL="tool schema accepted; response returned"; return 0
    fi
    DETAIL="tool-use request rejected or empty"; return 1
}

live_override() {
    # Exercises the x_orchestrator_role override passthrough on /v1.
    local base body
    base="$(resolve_base_url)"
    body='{"model":"","messages":[{"role":"user","content":"ping"}],"max_tokens":16,"temperature":0,"seed":42,"x_orchestrator_role":"frontdoor","x_show_routing":true}'
    if _curl_json "${base}/chat/completions" "$body" | grep -q '"choices"'; then
        DETAIL="x_orchestrator_role override accepted"; return 0
    fi
    DETAIL="override request rejected"; return 1
}

live_multiturn() {
    local base body tmp response
    base="$(resolve_base_url)"
    body='{"model":"","messages":[{"role":"user","content":"My name is Ada."},{"role":"assistant","content":"Hi Ada."},{"role":"user","content":"What is my name? One word."}],"max_tokens":16,"temperature":0,"seed":42}'
    tmp="$(mktemp /tmp/hermes_multiturn.XXXXXX)"
    if _curl_json "${base}/chat/completions" "$body" >"$tmp" 2>&1 && grep -qi 'ada' "$tmp"; then
        rm -f "$tmp"
        DETAIL="multi-turn context retained across turns"; return 0
    fi
    response="$(tr '\n' ' ' <"$tmp" | head -c 200)"
    rm -f "$tmp"
    DETAIL="multi-turn context not retained; response=${response}"
    return 1
}

live_refclient() {
    # Live --send validation of the reference non-Hermes client transport surface.
    # Defaults to the standalone Hermes backend; set HERMES_SMOKE_REFCLIENT_BASE_URL
    # or HERMES_SMOKE_ORCH_URL for the orchestrator override-semantics gate.
    local base ref_base ref_model
    ref_base="${HERMES_SMOKE_REFCLIENT_BASE_URL:-${HERMES_SMOKE_ORCH_URL:-}}"
    if [[ -z "$ref_base" ]]; then
        base="$(resolve_base_url)"
        ref_base="${base%/v1}"
    fi
    ref_model="${HERMES_SMOKE_REFCLIENT_MODEL-}"
    if timeout 120 python3 "$REF_CLIENT" --send --x-show-routing --stream \
        --base-url "$ref_base" --model "$ref_model" \
        --prompt "Reply with the single word OK." --max-tokens 16 --timeout 120 \
        >/tmp/hermes_refsend.$$ 2>&1; then
        DETAIL="reference client --send/stream ok against $ref_base"
        rm -f /tmp/hermes_refsend.$$; return 0
    fi
    DETAIL="reference client --send failed: $(head -c 160 /tmp/hermes_refsend.$$)"
    rm -f /tmp/hermes_refsend.$$; return 1
}

# Item G live half: spawn N parallel requests at the single-slot backend and
# confirm all complete (serialized on one slot, no wedge / cross-talk).
live_subagent() {
    local base i rc n="$SUBAGENTS"
    base="$(resolve_base_url)"
    [[ "$n" -ge 2 ]] || n=2
    local tmpdir; tmpdir="$(mktemp -d /tmp/hermes_subagent.XXXXXX)"
    for ((i = 1; i <= n; i++)); do
        (
            body="{\"model\":\"\",\"messages\":[{\"role\":\"user\",\"content\":\"Subagent ${i}: reply with the number ${i} only.\"}],\"max_tokens\":16,\"temperature\":0,\"seed\":42}"
            _curl_json "${base}/chat/completions" "$body" >"${tmpdir}/r${i}.json" 2>&1
            echo "$?" >"${tmpdir}/rc${i}"
        ) &
    done
    wait
    local ok=0 fails=0
    for ((i = 1; i <= n; i++)); do
        rc="$(cat "${tmpdir}/rc${i}" 2>/dev/null || echo 1)"
        if [[ "$rc" == "0" ]] && grep -q '"choices"' "${tmpdir}/r${i}.json" 2>/dev/null; then
            ok=$((ok + 1))
        else
            fails=$((fails + 1))
        fi
    done
    rm -rf "$tmpdir"
    if [[ "$fails" -eq 0 ]]; then
        DETAIL="${ok}/${n} parallel subagents completed on single slot (no wedge)"; return 0
    fi
    DETAIL="${fails}/${n} subagents failed against single-slot backend"; return 1
}

# =============================================================================
# RUN
# =============================================================================

agent_task_start "Hermes smoke orchestrator (live=${LIVE}, target=${TARGET_TAG})" \
    "Static Hermes outer-shell smokes; live legs gated behind HERMES_SMOKE_LIVE"

echo "=== Hermes smoke harness ==="
echo "root:        $ROOT"
echo "target tag:  $TARGET_TAG"
echo "live mode:   $([[ "$LIVE" == "1" ]] && echo "ON" || echo "off (static only)")"
echo "base url:    $(resolve_base_url)"
echo ""
echo "--- static checks (no server needed) ---"

run_static "config-present"        check_config_present
run_static "pin-audit"             check_pin_audit
run_static "launch-config"         check_launch_config
run_static "single-slot-wiring"    check_single_slot_wiring
run_static "reference-client-dry"  check_reference_client_dryrun

echo ""
echo "--- live end-to-end legs (HERMES_SMOKE_LIVE gate) ---"

if [[ "$LIVE" == "1" ]]; then
    # Health first; if the backend is down, the legs will fail with a clear reason.
    DETAIL=""
    if live_health; then record PASS "live:health" "$DETAIL"; else record FAIL "live:health" "$DETAIL"; fi
else
    record SKIP "live:health" "skipped (needs live server; set HERMES_SMOKE_LIVE=1)"
fi

live_leg "$LEG_CHAT"       chat            live_chat
live_leg "$LEG_TOOLUSE"    tooluse         live_tooluse
live_leg "$LEG_STREAMING"  streaming       live_streaming
live_leg "$LEG_OVERRIDE"   override        live_override
live_leg "$LEG_MULTITURN"  multiturn       live_multiturn
live_leg "$LEG_REFCLIENT"  reference-client live_refclient
live_leg "$LEG_SUBAGENT"   subagent        live_subagent

# --- Summary ------------------------------------------------------------------
echo ""
echo "=== summary: ${PASS} passed, ${FAIL} failed, ${SKIP} skipped ==="

if [[ -n "${HERMES_SMOKE_OUT:-}" ]]; then
    mkdir -p "$(dirname "$HERMES_SMOKE_OUT")"
    ts="$(date -Iseconds)"
    joined="$(IFS=,; echo "${SUMMARY_LINES[*]}")"
    printf '{"ts":"%s","target_tag":"%s","live":%s,"pass":%d,"fail":%d,"skip":%d,"checks":"%s"}\n' \
        "$ts" "$TARGET_TAG" "$([[ "$LIVE" == "1" ]] && echo true || echo false)" \
        "$PASS" "$FAIL" "$SKIP" "$joined" >>"$HERMES_SMOKE_OUT"
    echo "summary row appended to $HERMES_SMOKE_OUT"
fi

if [[ "$FAIL" -gt 0 ]]; then
    agent_task_end "Hermes smoke orchestrator" "failure"
    exit 1
fi
agent_task_end "Hermes smoke orchestrator" "success"
exit 0
