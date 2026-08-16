#!/bin/bash
# =============================================================================
# alarm_drill.sh — Phase 0 acceptance gate for THE ALARM CHANNEL (P0-1)
# =============================================================================
#
# THE GATE IT PROVES. "The operator's push channel receives exactly ONE alarm."
# Not at-least-one — EXACTLY one. A channel that pages five times for one dead
# fleet gets muted, and a muted channel is indistinguishable from the
# advisory.jsonl void this whole task exists to escape.
#
# WHAT IT DOES *NOT* DO. It kills nothing. This is a shared host: no process
# management, no pkill, no daemon touching, no writes anywhere under
# coordination/session-bus/. The drill runs the alarm module against a TEMP
# state file, a TEMP config and a TEMP record file (all via the module's env
# overrides), so it is safe to run at any moment, including mid-campaign, and
# leaves the live alarm state byte-identical.
#
# WHAT IT PROVES, in order:
#   1  a fresh channel has zero active alarms          (the well-run-night state)
#   2  five raises of ONE key produce exactly ONE delivery
#   3  the suppressed raises are still COUNTED (evidence is not lost, only the
#      notification is suppressed)
#   4  clear() delivers the resolution exactly once
#   5  clearing an inactive key delivers NOTHING
#   6  re-raising after a clear delivers AGAIN — dedupe is a state machine, not
#      a permanent mute
#   7  an unreachable backend still records the alarm locally, records the
#      DELIVERY FAILURE as its own event, shouts on stderr, and exits 3
#   8  the shipped repo config is inert: the placeholder endpoint means no
#      network call ever happens until the operator edits the one `url:` line
#   9  --dry-run delivers nothing at all
#
# `set -e` is deliberately OFF: this harness asserts on non-zero exit codes
# (case 7 REQUIRES rc=3), and -e would abort the drill at the very assertion it
# exists to make. Every command's status is inspected explicitly instead.
#
# Usage: scripts/coordination/tests/alarm_drill.sh
# Exit:  0 = PASS (gate met), 1 = FAIL (gate not met)
# =============================================================================
set -uo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ALARM="${ALARM_CHANNEL_PY:-${HERE}/../alarm_channel.py}"
REPO_CONFIG="${HERE}/../../../coordination/session-bus/alarm_config.yaml"
PY="${PYTHON:-python3}"

if [[ ! -f "$ALARM" ]]; then
    printf 'FAIL: alarm module not found at %s\n' "$ALARM"
    exit 1
fi

TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

PASS=0
FAIL=0

ok()   { printf '  PASS  %s\n' "$1"; PASS=$((PASS + 1)); }
bad()  { printf '  FAIL  %s\n' "$1"; FAIL=$((FAIL + 1)); }
check(){ # check <condition-result> <description> ; 0 => pass
    if [[ "$1" -eq 0 ]]; then ok "$2"; else bad "$2"; fi
}

# Count records in the temp alarm file matching an event type (and optionally a key).
count_events() { # count_events <file> <event> [key]
    local f="$1" ev="$2" key="${3:-}"
    [[ -f "$f" ]] || { printf '0'; return; }
    "$PY" - "$f" "$ev" "$key" <<'PY'
import json, sys
path, ev, key = sys.argv[1], sys.argv[2], sys.argv[3]
n = 0
with open(path, encoding="utf-8") as fh:
    for line in fh:
        line = line.strip()
        if not line:
            continue
        r = json.loads(line)
        if r.get("event") == ev and (not key or r.get("key") == key):
            n += 1
print(n)
PY
}

# The live state file must be untouched. Fingerprint it before and after.
LIVE_STATE="${HERE}/../../../coordination/session-bus/alarm_state.json"
live_fingerprint() {
    if [[ -f "$LIVE_STATE" ]]; then sha256sum "$LIVE_STATE" | cut -d' ' -f1; else echo "ABSENT"; fi
}
LIVE_BEFORE="$(live_fingerprint)"

printf '=============================================================\n'
printf 'ALARM DRILL — Phase 0 acceptance gate (P0-1)\n'
printf 'module: %s\n' "$ALARM"
printf 'sandbox: %s   (nothing outside this directory is written)\n' "$TMP"
printf '=============================================================\n\n'

# ── the sandboxed channel: `file` backend, temp everything ────────────────────
STATE="$TMP/alarm_state.json"
REC="$TMP/alarms.jsonl"
CFG="$TMP/alarm_config.yaml"
cat > "$CFG" <<EOF
schema_version: alarm_channel.config.v1
enabled: true
backend: file
advisory_mirror: false
file:
  path: $REC
EOF
export ALARM_STATE_PATH="$STATE"
export ALARM_CONFIG_PATH="$CFG"

KEY="drill-fleet-absent"

printf -- '--- 1. a fresh channel is silent -------------------------------\n'
out="$("$PY" "$ALARM" status 2>&1)"; rc=$?
[[ $rc -eq 0 ]] && grep -q 'active alarms: none' <<<"$out"
check $? "fresh channel reports zero active alarms"

printf -- '\n--- 2. FIVE raises of one key => EXACTLY ONE delivery ----------\n'
for i in 1 2 3 4 5; do
    "$PY" "$ALARM" raise --severity critical --key "$KEY" \
        --message "the fleet is absent: 0 live roster mains" \
        --evidence "{\"tick\":$i,\"live_mains\":0}" >"$TMP/raise.$i.out" 2>"$TMP/raise.$i.err"
    rc=$?
    if [[ $rc -ne 0 ]]; then bad "raise #$i exited $rc (expected 0)"; fi
done
n="$(count_events "$REC" raised "$KEY")"
[[ "$n" == "1" ]]
check $? "exactly ONE delivery landed after 5 raises (got $n)"

grep -q 'suppressed' "$TMP/raise.5.out"
check $? "raise #5 reported itself as suppressed, not delivered"

n="$(count_events "$REC" delivery-result "$KEY")"
[[ "$n" == "1" ]]
check $? "exactly ONE delivery-result states the outcome positively (got $n)"

printf -- '\n--- 3. suppressed raises are COUNTED, not discarded ------------\n'
cnt="$("$PY" - "$STATE" "$KEY" <<'PY'
import json, sys
print(json.load(open(sys.argv[1]))["active"][sys.argv[2]]["count"])
PY
)"
[[ "$cnt" == "5" ]]
check $? "state records all 5 occurrences (count=$cnt) while notifying once"

ev="$("$PY" - "$STATE" "$KEY" <<'PY'
import json, sys
print(json.load(open(sys.argv[1]))["active"][sys.argv[2]]["evidence"].get("tick"))
PY
)"
[[ "$ev" == "5" ]]
check $? "the LATEST evidence is retained (tick=$ev), not frozen at first raise"

printf -- '\n--- 4. clear() delivers the resolution exactly once ------------\n'
"$PY" "$ALARM" clear --key "$KEY" --message "3 roster mains back up" >"$TMP/clear.out" 2>&1
rc=$?
n="$(count_events "$REC" cleared "$KEY")"
[[ $rc -eq 0 && "$n" == "1" ]]
check $? "clear delivered exactly ONE resolution (rc=$rc, cleared records=$n)"

printf -- '\n--- 5. clearing an inactive key delivers NOTHING ---------------\n'
"$PY" "$ALARM" clear --key "$KEY" >"$TMP/clear2.out" 2>&1
rc=$?
n="$(count_events "$REC" cleared "$KEY")"
[[ $rc -eq 0 && "$n" == "1" ]] && grep -q 'not-active' "$TMP/clear2.out"
check $? "second clear was a no-op (rc=$rc, cleared records still $n)"

printf -- '\n--- 6. re-raise after clear delivers AGAIN ---------------------\n'
"$PY" "$ALARM" raise --severity critical --key "$KEY" \
    --message "the fleet is absent again" >"$TMP/raise6.out" 2>&1
rc=$?
n="$(count_events "$REC" raised "$KEY")"
[[ $rc -eq 0 && "$n" == "2" ]]
check $? "a SECOND delivery landed after the clear (raised records=$n) — dedupe is a state machine, not a mute"

printf -- '\n--- 7. an unreachable backend records the failure LOUDLY -------\n'
FCFG="$TMP/fail_config.yaml"
FREC="$TMP/fail_alarms.jsonl"
FSTATE="$TMP/fail_state.json"
# 127.0.0.1:1 refuses instantly and involves no external network.
cat > "$FCFG" <<EOF
schema_version: alarm_channel.config.v1
enabled: true
backend: ntfy
ntfy:
  url: http://127.0.0.1:1/drill-unreachable
  timeout_s: 3
file:
  path: $FREC
EOF
ALARM_CONFIG_PATH="$FCFG" ALARM_STATE_PATH="$FSTATE" \
    "$PY" "$ALARM" raise --severity critical --key drill-unreachable \
    --message "backend is down" >"$TMP/fail.out" 2>"$TMP/fail.err"
rc=$?
[[ $rc -eq 3 ]]
check $? "raise exited 3 (recorded, NOT delivered) — never a silent 0 (rc=$rc)"

n="$(count_events "$FREC" raised drill-unreachable)"
[[ "$n" == "1" ]]
check $? "the alarm still landed in the durable local record (records=$n)"

n="$(count_events "$FREC" delivery-failed drill-unreachable)"
[[ "$n" == "1" ]]
check $? "the DELIVERY FAILURE was itself recorded as an event (records=$n)"

grep -q 'DELIVERY FAILED' "$TMP/fail.err" && grep -q 'NOBODY WAS PAGED' "$TMP/fail.err"
check $? "the failure shouted on stderr ('DELIVERY FAILED … NOBODY WAS PAGED')"

printf -- '\n--- 8. the shipped repo config is inert until the operator edits it\n'
if [[ -f "$REPO_CONFIG" ]]; then
    PSTATE="$TMP/placeholder_state.json"
    PREC="$TMP/placeholder_alarms.jsonl"
    ALARM_CONFIG_PATH="$REPO_CONFIG" ALARM_STATE_PATH="$PSTATE" ALARM_FILE_PATH="$PREC" \
        "$PY" "$ALARM" raise --severity warning --key drill-placeholder \
        --message "placeholder check" >"$TMP/ph.out" 2>"$TMP/ph.err"
    rc=$?
    # The OUTCOME lives in the `delivery-result` record, not in the `raised` one
    # (which can only honestly say `pending` — it is written before the attempt).
    d="$("$PY" - "$PREC" <<'PY'
import json, sys
for line in open(sys.argv[1], encoding="utf-8"):
    r = json.loads(line)
    if r.get("event") == "delivery-result":
        print(r["delivery"]); break
else:
    print("NO-DELIVERY-RESULT-RECORD")
PY
)"
    [[ $rc -eq 0 && "$d" == "skipped_not_live" ]]
    check $? "shipped config touches no network (delivery=$d) yet still records locally"
    grep -q 'PLACEHOLDER' "$TMP/ph.err"
    check $? "and says so loudly on stderr, with the one-line fix"
else
    bad "repo config missing at $REPO_CONFIG"
fi

printf -- '\n--- 9. --dry-run delivers nothing ------------------------------\n'
DSTATE="$TMP/dry_state.json"
DREC="$TMP/dry_alarms.jsonl"
ALARM_STATE_PATH="$DSTATE" ALARM_FILE_PATH="$DREC" \
    "$PY" "$ALARM" --dry-run raise --severity critical --key drill-dry \
    --message "should never be delivered" >"$TMP/dry.out" 2>&1
rc=$?
[[ $rc -eq 0 && ! -f "$DREC" && ! -f "$DSTATE" ]]
check $? "dry-run wrote no record and no state (rc=$rc)"
grep -q 'DRY RUN' "$TMP/dry.out"
check $? "dry-run printed what it WOULD deliver"

printf -- '\n--- 10. the live channel state was never touched ---------------\n'
[[ "$(live_fingerprint)" == "$LIVE_BEFORE" ]]
check $? "coordination/session-bus/alarm_state.json unchanged ($LIVE_BEFORE)"

printf '\n=============================================================\n'
printf 'ALARM DRILL SUMMARY: %d passed, %d failed\n' "$PASS" "$FAIL"
if [[ $FAIL -eq 0 ]]; then
    printf 'RESULT: PASS — the alarm channel emits exactly ONE alarm per state\n'
    printf '        change, records every delivery failure loudly, and is inert\n'
    printf '        until the operator edits the one `url:` line.\n'
    printf '=============================================================\n'
    exit 0
fi
printf 'RESULT: FAIL — the Phase 0 gate is NOT met. Do not rely on this channel.\n'
printf '=============================================================\n'
exit 1
