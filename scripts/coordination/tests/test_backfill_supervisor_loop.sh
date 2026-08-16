#!/bin/bash
# =============================================================================
# test_backfill_supervisor_loop.sh — backfill_supervisor.sh `loop` mode
# =============================================================================
#
# WHY THIS EXISTS (P0-4, 2026-08-14). `backfill_supervisor.sh loop` called
# `health_ok` twice. Nothing defined `health_ok` — not the file, not
# observer_guard.sh, not env.sh. The observation-contract rewrite (ed38041d)
# deleted the old two-state definition and migrated `start_runner`, `check_once`
# and `status` onto `observe_runner` + `heartbeat_fresh`, and left the `loop`
# case block's two call sites dangling.
#
# Under `set -e` a `command not found` inside an `if` CONDITION is not fatal — it
# is merely FALSE. So loop mode took the failure branch on every iteration
# against a perfectly healthy runner: relaunch, "restart failed", back off,
# doubling to the 300s cap, forever, in silence. `bash -n` cannot see it (the
# syntax is fine) and `shellcheck` cannot either (it does not resolve names
# across `source`).
#
# WHY THE EXISTING TESTS DID NOT CATCH IT, which is the point of this file.
# tests/test_observer_contract.py drives `observe` and `once`. That is A
# consumer. `loop` is THE consumer — it is what `nohup ... backfill_supervisor.sh`
# actually runs in production, and it was the only mode with the bug. This is
# the same lesson bus_supervisor.sh already paid for once (C42: the stale-source
# check was wired into check_once and never reached from the loop's healthy
# branch; "the tests passed because they exercised the predicate and check_once
# directly and never the loop").
#
# SCOPE / SAFETY. Everything is confined to a temp EPYC_ROOT: the queue dir, the
# heartbeat, the logs, the observer-alert breadcrumbs and the supervisor flock
# are all overridden per scenario. RUNNER_MARK is a per-run random token that
# exists nowhere on this host but in the stand-in this test spawns itself, so the
# supervisor's /proc walk cannot see, and its kill path cannot reach, any other
# session's process (INC-20260731-broad-process-pattern-kills). The only pids
# this test signals are ones it captured from its own `&`. The RUNNER it points
# the supervisor at is a stub that touches a marker file; hardware_backfill.py is
# never executed and no region lock is ever taken.
#
# MUTATION-TESTED. Run with BACKFILL_SUP=<path> to drive a mutated copy; the
# `--mutation` mode below builds the copies and asserts this suite goes RED on
# each. A test that passes with the bug present is worthless.
set -euo pipefail   # MATCH PRODUCTION. backfill_supervisor.sh runs under
                    # `set -euo pipefail`, and this repo has shipped tests that
                    # passed only because they ran without it.

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO="$(cd "$HERE/../../.." && pwd)"
SUP="${BACKFILL_SUP:-$REPO/scripts/coordination/backfill_supervisor.sh}"
GUARD="$REPO/scripts/coordination/observer_guard.sh"

pass=0; fail=0
chk()  { if [ "$2" = "$3" ]; then echo "  PASS  $1"; pass=$((pass+1));
         else echo "  FAIL  $1 (got [$2], want [$3])"; fail=$((fail+1)); fi; }
has()  { if printf '%s' "$2" | grep -qF -- "$3"; then echo "  PASS  $1"; pass=$((pass+1));
         else echo "  FAIL  $1 — output lacks [$3]"; fail=$((fail+1)); fi; }
hasnt(){ if printf '%s' "$2" | grep -qF -- "$3"; then echo "  FAIL  $1 — output CONTAINS [$3]"; fail=$((fail+1));
         else echo "  PASS  $1"; pass=$((pass+1)); fi; }

STANDIN_PIDS=()
TMPROOT="$(mktemp -d)"
# ISOLATION WITNESS. Sandboxing that silently writes to the production supervisor
# log is not sandboxing, and that is exactly what this file did before
# BACKFILL_LOG_DIR existed. Record the production log's size up front and prove at
# the end that this suite never touched it.
PROD_LOG="$REPO/logs/backfill_supervisor.log"
PROD_LOG_BEFORE="$( [[ -f "$PROD_LOG" ]] && stat -c %s "$PROD_LOG" || echo missing )"
cleanup() {
  # Only ever pids this script captured from its own `&`. Never a name pattern.
  local p
  for p in ${STANDIN_PIDS[@]+"${STANDIN_PIDS[@]}"}; do
    [[ -n "$p" ]] || continue
    kill "$p" 2>/dev/null || true
    wait "$p" 2>/dev/null || true
  done
  rm -rf "$TMPROOT"
}
trap cleanup EXIT

# =========================================================================== #
# MUTATION MODE:  test_backfill_supervisor_loop.sh --mutation
# =========================================================================== #
#
# A test that passes with the bug present is worthless, and this repo has shipped
# several. So the mutants are checked in next to the assertions rather than run
# once by hand and described in a commit message: each one re-breaks the
# supervisor in a specific way and this suite must go RED on it. If a future edit
# makes one of them pass, that assertion has stopped measuring anything.
#
#   M1  health_ok's DEFINITION renamed        — the P0-4 bug, verbatim.
#   M2  the first call site back to `if !`    — the third state collapsed at the
#                                               point of use (3 is falsy).
#   M3  health_ok always returns 0            — the FAIL-OPEN repair (C3/C6/C8):
#                                               passes scenario 1 by doing nothing.
#
# The mutant is written into a throwaway tree with `../lib/env.sh` symlinked, so
# the copy resolves env.sh exactly as the original does and NOTHING is written
# inside the repo.
if [[ "${1:-}" == "--mutation" ]]; then
  mut_pass=0; mut_fail=0
  run_mutant() {
    local name="$1" desc="$2" pyexpr="$3"
    local mdir="$TMPROOT/mutant_$name"
    mkdir -p "$mdir/coordination"
    ln -sfn "$REPO/scripts/lib" "$mdir/lib"
    python3 - "$SUP" "$mdir/coordination/backfill_supervisor.sh" "$pyexpr" <<'PY'
import sys
src, dst, mode = sys.argv[1], sys.argv[2], sys.argv[3]
s = open(src).read()
if mode == "M1":
    n = s.replace("\nhealth_ok() {", "\nhealth_ok_RENAMED() {", 1)
elif mode == "M2":
    # BOTH call sites — a faithful revert to the two-valued idiom. Mutating only
    # the first was MISSED on the first mutation run: check_once re-observes and
    # suppresses on its own, so the single-site damage was invisible until the
    # loop got its own "corrective branch NOT entered" line.
    n = s.replace("rc=0; health_ok || rc=$?", "rc=0; if ! health_ok; then rc=1; fi")
elif mode == "M3":
    n = s.replace("\nhealth_ok() {\n", "\nhealth_ok() {\n  return 0\n", 1)
else:
    raise SystemExit(f"unknown mutant {mode}")
assert n != s, f"mutation {mode} did not apply — the anchor text moved"
open(dst, "w").write(n)
PY
    chmod +x "$mdir/coordination/backfill_supervisor.sh"
    echo
    echo "  -- $name: $desc"
    local rc=0 out
    out="$(BACKFILL_SUP="$mdir/coordination/backfill_supervisor.sh" bash "${BASH_SOURCE[0]}" 2>&1)" || rc=$?
    # A mutant that cannot even START would turn every assertion red and be
    # counted as a detection it did not earn — the mutation must be VISIBLE, not
    # just followed by a red suite. Caught here on the first attempt: the mutant
    # tree resolved EPYC_ROOT to its own throwaway dir, so it died sourcing
    # observer_guard.sh and "detected" all three mutations without running once.
    if ! printf '%s' "$out" | grep -qF "PASS  loop actually ran"; then
      echo "     FAIL  $name never STARTED — this is not a detection, it is a broken mutant tree"
      mut_fail=$((mut_fail+1)); return 0
    fi
    if (( rc != 0 )); then
      echo "     PASS  suite went RED on $name (exit $rc). Failing assertions:"
      printf '%s\n' "$out" | grep '  FAIL' | sed 's/^/       /'
      mut_pass=$((mut_pass+1))
    else
      echo "     FAIL  suite still PASSED with $name applied — it is not measuring this"
      mut_fail=$((mut_fail+1))
    fi
  }
  echo "== MUTATION TEST: this suite must FAIL on each re-broken supervisor =="
  run_mutant M1 "health_ok's definition renamed away (the P0-4 bug, verbatim)" M1
  run_mutant M2 "both call sites back to \`if ! health_ok\` (third state collapsed)" M2
  run_mutant M3 "health_ok always returns 0 (fail-open)" M3
  echo
  echo "  ---- mutants detected: $mut_pass, mutants MISSED: $mut_fail"
  if [ "$mut_fail" -eq 0 ]; then exit 0; else exit 1; fi
fi

# --------------------------------------------------------------------------- #
# Scenario scaffolding
# --------------------------------------------------------------------------- #
#
# Each scenario gets its OWN tmp tree, flock, alert dir and blind-streak state:
# observer_guard's detector B is stateful across rounds, and a streak leaking
# from the previous scenario would force `unobservable` in the next one and hand
# this suite a pass (or a fail) it did not earn.
SC_DIR=""; SC_MARK=""; SC_MARKER=""; SC_LOG=""; SC_HB=""; SC_ALERTS=""

scenario() {
  SC_DIR="$TMPROOT/$1"
  # NOTE the log dir is deliberately NOT pre-created. The supervisor must make it
  # itself, and a fixture that makes it first DELETES THE SIGNAL: it hides an
  # ordering bug where LOG_DIR is reassigned by a late `source` after SUP_LOG has
  # been captured, in which case every `log` call dies on a `tee` to a
  # non-existent directory and takes the whole supervisor with it under
  # `set -euo pipefail`. That bug existed and this suite passed over it until the
  # `mkdir` came out.
  mkdir -p "$SC_DIR/queue" "$SC_DIR/alerts"
  # A token that exists nowhere on this host but in the stand-in below.
  SC_MARK="epyc_backfill_loop_standin_$$_${RANDOM}${RANDOM}"
  SC_MARKER="$SC_DIR/launched.marker"
  SC_LOG="$SC_DIR/root/logs/backfill_supervisor.log"
  SC_HB="$SC_DIR/queue/heartbeat.json"
  SC_ALERTS="$SC_DIR/alerts"
  # The stub the supervisor would launch. If the failure branch fires, this file
  # appears — which is the ASSERTION, in both directions.
  cat > "$SC_DIR/runner_stub.sh" <<EOF
#!/bin/bash
touch "$SC_MARKER"
EOF
  chmod +x "$SC_DIR/runner_stub.sh"
}

# A live process whose argv contains SC_MARK and nothing else on this host does.
# Publishes its pid in SC_STANDIN_PID rather than on stdout — see below.
SC_STANDIN_PID=""
spawn_standin() {
  local script="$SC_DIR/${SC_MARK}.sh"
  printf '#!/bin/bash\nsleep 120\n' > "$script"
  chmod +x "$script"
  # `>/dev/null 2>&1`, and NOT called inside `$(...)`, are both load-bearing.
  # A background child inherits the caller's stdout; when that stdout is a
  # command-substitution pipe, the substitution blocks until every holder of the
  # write end exits. Measured while writing this file: `$(spawn_standin)` waited
  # out the whole `sleep 120`, so by the time the supervisor ran the stand-in was
  # already GONE and scenario 1 reported a relaunch. The supervisor was right and
  # the test method was wrong — rule out the test method before calling it a bug.
  bash "$script" >/dev/null 2>&1 &
  SC_STANDIN_PID=$!
  STANDIN_PIDS+=("$SC_STANDIN_PID")
  # Confirm the mark really is visible in /proc before relying on it: a stand-in
  # the supervisor cannot see would make every assertion below meaningless.
  local waited=0
  while (( waited < 50 )); do
    if [[ -r "/proc/$SC_STANDIN_PID/cmdline" ]] \
       && tr '\0' ' ' < "/proc/$SC_STANDIN_PID/cmdline" | grep -qF "$SC_MARK"; then
      return 0
    fi
    sleep 0.1; waited=$((waited+1))
  done
  echo "  FATAL: stand-in $SC_STANDIN_PID never showed mark $SC_MARK in /proc" >&2
  return 1
}

# Run `loop` with a bounded iteration budget, in the scenario sandbox.
run_loop() {
  local iters="$1"
  # EPYC_ROOT stays the REAL repo: the supervisor sources observer_guard.sh
  # through it, so moving the root would only prove the script cannot start.
  # Isolation comes from overriding every path it WRITES instead.
  env \
    EPYC_ROOT="$REPO" \
    BACKFILL_LOG_DIR="$SC_DIR/root/logs" \
    QUEUE_DIR="$SC_DIR/queue" \
    HEARTBEAT="$SC_HB" \
    OG_STATE_DIR="$SC_ALERTS" \
    LOCK_FILE="$SC_DIR/sup.lock" \
    RUNNER="$SC_DIR/runner_stub.sh" \
    RUNNER_MARK="$SC_MARK" \
    PY=/bin/bash \
    POLL_INTERVAL=1 \
    STALE_AFTER=120 \
    STARTUP_TIMEOUT=2 \
    MAX_BACKOFF=300 \
    LOOP_MAX_ITERATIONS="$iters" \
    bash "$SUP" loop
}

# =========================================================================== #
echo "== 1. HEALTHY runner: loop must NOT take the failure branch =="
# THE REGRESSION. With `health_ok` undefined this scenario went: undefined ->
# false -> check_once -> relaunch -> "restart failed" -> back off 10s, every
# iteration, against a live runner with a fresh heartbeat.
# =========================================================================== #
scenario healthy
spawn_standin
printf '{"pid":%s,"state":"working","jobs_running":0}\n' "$SC_STANDIN_PID" > "$SC_HB"
rc=0; out="$(run_loop 3 2>&1)" || rc=$?
log1="$(cat "$SC_LOG" 2>/dev/null || true)"

chk   "loop exits 0 on the bounded budget" "$rc" 0
has   "loop actually ran" "$log1" "supervisor started"
has   "loop honoured the iteration budget (it is not hanging)" "$log1" "LOOP_MAX_ITERATIONS=3 reached"
hasnt "NO backoff against a healthy runner" "$log1" "backing off"
hasnt "NO relaunch against a healthy runner" "$log1" "launching hardware_backfill.py"
hasnt "no OBSERVER-BLIND alarm while the runner is plainly visible" "$out" "OBSERVER-BLIND"
chk   "the runner stub was NEVER launched" "$( [[ -e "$SC_MARKER" ]] && echo launched || echo no )" "no"
# ...and the loop is not silently doing nothing: a healthy poll must be a poll.
chk   "no observer-blind breadcrumb was written" \
      "$( ls "$SC_ALERTS"/*.json >/dev/null 2>&1 && echo some || echo none )" "none"
chk   "the stand-in was still alive for the whole scenario (the test method held)" \
      "$( [[ -d "/proc/$SC_STANDIN_PID" ]] && echo alive || echo GONE )" "alive"
kill "$SC_STANDIN_PID" 2>/dev/null || true; wait "$SC_STANDIN_PID" 2>/dev/null || true

# =========================================================================== #
echo
echo "== 2. ABSENT runner: loop must still ACT (the compliant path) =="
# The mirror assertion, and it is not optional. Scenario 1 alone is passed by a
# `health_ok` that returns 0 unconditionally — which is the FAIL-OPEN repair, the
# defect class this repo documents as C3/C6/C8. A guard must fire when it should
# and only when it should, so the suite has to test both polarities.
# =========================================================================== #
scenario absent
# No heartbeat file at all, and no process carrying SC_MARK: both identity
# channels can speak and both say absent. A real negative, not a blind spot.
rc=0; out="$(run_loop 1 2>&1)" || rc=$?
log2="$(cat "$SC_LOG" 2>/dev/null || true)"

chk "loop exits 0 on the bounded budget" "$rc" 0
has "loop recognised the real negative" "$log2" "runner is absent"
has "loop ACTED on it" "$log2" "launching hardware_backfill.py"
chk "the runner stub WAS launched" \
    "$( for _ in 1 2 3 4 5 6 7 8 9 10; do [[ -e "$SC_MARKER" ]] && break; sleep 0.2; done
        [[ -e "$SC_MARKER" ]] && echo launched || echo no )" "launched"
has "a failed relaunch IS scored as a failure (the backoff branch is reachable)" \
    "$log2" "backing off"

# =========================================================================== #
echo
echo "== 3. UNOBSERVABLE: loop must suppress action AND not back off =="
# The third state, which is the entire reason observer_guard.sh exists. A
# heartbeat that exists but carries no parsable pid makes the authoritative
# channel `unavailable` while the /proc walk says `absent` — partial blindness.
# Folding that into "unhealthy" restart-loops a possibly-healthy runner (the
# specimen); folding it into "healthy" leaves the runner unwatched while
# everything looks green. It must be its own branch, and `if health_ok` cannot
# express it because 3 is falsy.
# =========================================================================== #
scenario blind
printf '{"state":"working","jobs_running":0}\n' > "$SC_HB"   # no "pid" key
rc=0; out="$(run_loop 2 2>&1)" || rc=$?
log3="$(cat "$SC_LOG" 2>/dev/null || true)"

chk   "loop exits 0 on the bounded budget" "$rc" 0
has   "loop said it is blind, loudly" "$out" "OBSERVER-BLIND"
has   "the LOOP declined to enter the corrective branch at all" \
      "$log3" "corrective branch NOT entered"
has   "loop suppressed corrective action and logged why" "$log3" "suppressing all corrective action"
hasnt "blind is NOT treated as a failed restart (no backoff)" "$log3" "backing off"
hasnt "blind is NOT treated as absent (no relaunch)" "$log3" "launching hardware_backfill.py"
chk   "the runner stub was NEVER launched while blind" \
      "$( [[ -e "$SC_MARKER" ]] && echo launched || echo no )" "no"
chk   "a machine-readable breadcrumb was written" \
      "$( ls "$SC_ALERTS"/*.json >/dev/null 2>&1 && echo some || echo none )" "some"

# =========================================================================== #
echo
echo "== 4. WIRING: no dangling call site anywhere in the loop block =="
# The generalisation. Scenarios 1-3 cover the branches they reach; this covers
# the ones they do not, and it is the assertion that would have caught the
# original bug at the commit that introduced it. Every name used in COMMAND
# position inside the `loop` case block must resolve — to a function defined in
# the supervisor or in observer_guard.sh, or to a shell builtin/keyword/binary.
# `bash -n` accepts an undefined function; this does not.
# =========================================================================== #
loop_block="$(sed -n '/^  loop)/,/^    ;;$/p' "$SUP" | tail -n +2)"
chk "the loop block was actually extracted (guard against a vacuous scan)" \
    "$( [[ -n "$loop_block" ]] && echo yes || echo NO )" "yes"

# Strip comments, string literals and arithmetic contexts, split on command
# separators, drop leading shell keywords, keep the head of each command.
cands="$(printf '%s\n' "$loop_block" \
  | sed -e 's/#.*$//' -e 's/"[^"]*"/""/g' -e "s/'[^']*'/''/g" \
        -e 's/\$((\([^)]*\)))/1/g' -e 's/((\([^)]*\)))/:/g' \
  | awk '{ gsub(/[;&|(){}]/, "\n"); print }' \
  | awk '{ while (NF>0 && ($1=="if"||$1=="elif"||$1=="then"||$1=="else"||$1=="do" \
                          ||$1=="done"||$1=="fi"||$1=="while"||$1=="until"||$1=="!"||$1=="time")) {
             for (i=1;i<NF;i++) $i=$(i+1); NF--
           }
           if (NF>0 && $1 ~ /^[a-z_][a-z0-9_]*$/) print $1 }' \
  | sort -u)"
# EMPTY INPUT IS THE FIRST WAY A CHECK PASSES FOR THE WRONG REASON. Assert the
# scan found something, and specifically that it found the name that broke.
chk "the call-site scan is non-empty" "$( [[ -n "$cands" ]] && echo yes || echo NO )" "yes"
chk "the scan sees health_ok (it is the name that was dangling)" \
    "$( printf '%s\n' "$cands" | grep -qx 'health_ok' && echo yes || echo NO )" "yes"

dangling=""
while IFS= read -r n; do
  [[ -n "$n" ]] || continue
  grep -qE "^${n}\(\)" "$SUP" "$GUARD" && continue
  type -t "$n" >/dev/null 2>&1 && continue
  dangling="${dangling}${n} "
done <<< "$cands"
chk "every command the loop calls is defined" "${dangling:-none}" "none"

# =========================================================================== #
echo
echo '== 5. `if health_ok` must not come back =='
# health_ok is three-valued and 3 is falsy, so `if health_ok; then` silently
# re-collapses `unobservable` into "unhealthy, restart it" at the point of use.
# The call sites must capture the code.
# =========================================================================== #
if printf '%s\n' "$loop_block" | grep -qE '^\s*(if|elif)\s+health_ok\s*;'; then
  echo "  FAIL  the loop uses \`if health_ok\` — that collapses the third state at the call site"
  fail=$((fail+1))
else
  echo "  PASS  no bare \`if health_ok\` in the loop"; pass=$((pass+1))
fi
if printf '%s\n' "$loop_block" | grep -qF 'health_ok || rc=$?'; then
  echo "  PASS  the loop captures health_ok's exit code"; pass=$((pass+1))
else
  echo "  FAIL  the loop does not capture health_ok's exit code"; fail=$((fail+1))
fi

# =========================================================================== #
echo
echo "== 6. the test hook must be inert in production =="
# LOOP_MAX_ITERATIONS exists for this file. If it changed behaviour when unset,
# the thing under test would not be the thing that runs.
# =========================================================================== #
chk "LOOP_MAX_ITERATIONS defaults to 0 (loop forever)" \
    "$(grep -c '^LOOP_MAX_ITERATIONS="${LOOP_MAX_ITERATIONS:-0}"' "$SUP")" "1"
# With the budget at 0 the guard must be false, so sup_sleep is a plain sleep.
inert="$(bash -c '
  LOOP_MAX_ITERATIONS=0; _loop_iters=999
  _loop_budget_exhausted() { (( LOOP_MAX_ITERATIONS > 0 )) || return 1; (( _loop_iters >= LOOP_MAX_ITERATIONS )); }
  _loop_budget_exhausted && echo exhausted || echo forever')"
chk "budget 0 never reports exhausted, whatever the iteration count" "$inert" "forever"
# The sandbox knob must stay BACKFILL_LOG_DIR. `scripts/lib/env.sh` does an
# unconditional `export LOG_DIR=...`, so a bare `LOG_DIR="${LOG_DIR:-...}"` would
# isolate nothing while looking like isolation — and this whole suite would
# silently append to the production supervisor log again.
chk "the log dir knob is BACKFILL_LOG_DIR (env.sh clobbers a bare LOG_DIR)" \
    "$(grep -c '^LOG_DIR="${BACKFILL_LOG_DIR:-' "$SUP")" "1"
chk "env.sh really does clobber LOG_DIR (the premise above is checked, not assumed)" \
    "$(grep -c '^export LOG_DIR="${ORCHESTRATOR_PATHS_LOG_DIR}"' "$REPO/scripts/lib/env.sh")" "1"
# ...and the assignment must sit AFTER the last `source`, or observer_guard.sh's
# own `source env.sh` overwrites it while SUP_LOG keeps the sandbox path.
sup_log_line="$(grep -n '^SUP_LOG=' "$SUP" | cut -d: -f1)"
guard_src_line="$(grep -n '^source "${EPYC_ROOT}/scripts/coordination/observer_guard.sh"' "$SUP" | cut -d: -f1)"
chk "the log paths are assigned after observer_guard.sh is sourced" \
    "$( [[ -n "$sup_log_line" && -n "$guard_src_line" && "$sup_log_line" -gt "$guard_src_line" ]] \
        && echo after || echo BEFORE )" "after"
chk "this suite never wrote to the PRODUCTION supervisor log" \
    "$( [[ -f "$PROD_LOG" ]] && stat -c %s "$PROD_LOG" || echo missing )" "$PROD_LOG_BEFORE"

echo
echo "  ---- $pass passed, $fail failed"
[ "$fail" -eq 0 ]
