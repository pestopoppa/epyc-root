#!/bin/bash
# Regression test: bus_supervisor.sh's registry-restart tick (NIB2-81 remedy
# (b) — the H-4 generalisation to OTHER registered daemons, not just the
# coordinator-daemon this supervisor already watches).
#
# WHY THIS EXISTS. tmp/daemon-staleness-20260917/report.md found three shapes
# of a daemon executing an inode its own launch predates a later commit to:
# lane-pinned, orphaned-inode, orphaned-tree. Remedy (a) (daemon_provenance.sh)
# closes the door at LAUNCH time; H-4 (test_supervisor_stale_source.sh) already
# proves the restart mechanism works for the ONE daemon bus_supervisor.sh
# watches via its own heartbeat. This tests the GENERALISATION: registry rows
# carrying `runtime.restart_on_stale: true` get the same restart, keyed off
# THEIR OWN pidfile + cmdline identity, never a name pattern and never this
# supervisor's own DAEMON_MARKER (which only ever names the coordinator).
#
# SCOPE, and it is not optional. Extracts ONLY the six registry-restart
# functions (plus the one-line `log`) via sed, exactly as
# test_supervisor_stale_source.sh extracts the stale-source predicate — never
# sources the whole script (its case-block dispatch would run) and never
# touches the real /mnt/raid0/llm/epyc-root registry or pidfiles. Every
# "daemon" here is a real short-lived `sleep`-based bash script THIS TEST
# spawns and kills, confirmed dead before the test exits.
set -euo pipefail
cd "$(dirname "$0")/../../.." || exit 1
SUP=scripts/coordination/bus_supervisor.sh

TMP=$(mktemp -d)
trap 'rm -rf "$TMP"' EXIT

pass=0; fail=0
chk() { if [ "$2" = "$3" ]; then echo "  PASS  $1"; pass=$((pass+1));
        else echo "  FAIL  $1 (got $2, want $3)"; fail=$((fail+1)); fi; }
chk_true() { if [ "$2" = "1" ]; then echo "  PASS  $1"; pass=$((pass+1));
             else echo "  FAIL  $1"; fail=$((fail+1)); fi; }

# --------------------------------------------------------------------------- #
# Extract under test — six functions + the logger they all call.
# --------------------------------------------------------------------------- #
eval "$(sed -n '/^registry_restart_candidates()/,/^}/p;
                /^registry_daemon_identity()/,/^}/p;
                /^registry_script_is_stale()/,/^}/p;
                /^stop_registry_daemon()/,/^}/p;
                /^start_registry_daemon()/,/^}/p;
                /^check_registry_restarts()/,/^}/p' "$SUP")"
log() { printf '%s %s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$*" >&2; }

# The globals these functions read.
EPYC_ROOT="$TMP/root"
LOG_DIR="$TMP/logs"
mkdir -p "$LOG_DIR" "$EPYC_ROOT/scripts/system"
STARTUP_TIMEOUT=5
RESTART_MIN_INTERVAL_S=5   # short window so case (c) below can test the boundary quickly

# --------------------------------------------------------------------------- #
# Fixture: a fake daemon under EPYC_ROOT, launched and stopped like the
# opencode reaper is — `bash <canonical>/scripts/system/fakedaemon.sh loop`,
# holding its own script open on fd 255 (the real bash convention), writing
# its own pidfile as its FIRST act (mirrors dp_attest's own ordering: pidfile
# is a claim of identity, written only once the process exists to back it).
# --------------------------------------------------------------------------- #
DAEMON_REL="scripts/system/fakedaemon.sh"
DAEMON_SCRIPT="$EPYC_ROOT/$DAEMON_REL"
PIDFILE="$TMP/fakedaemon.pid"
DAEMON_LOG="$TMP/fakedaemon.log"

write_daemon_v1() {
  cat > "$DAEMON_SCRIPT" <<EOF
#!/bin/bash
echo \$\$ > "$PIDFILE"
echo "fakedaemon v1 up" >> "$DAEMON_LOG"
while true; do sleep 300; done
EOF
  chmod +x "$DAEMON_SCRIPT"
}

write_daemon_v2() {
  # A committed "fix" — write+rename, git's own mechanism, so a process still
  # holding the OLD file open ends up on an orphaned (deleted) inode.
  local tmp_sibling="$EPYC_ROOT/scripts/system/fakedaemon.sh.new"
  cat > "$tmp_sibling" <<EOF
#!/bin/bash
echo \$\$ > "$PIDFILE"
echo "fakedaemon v2 up" >> "$DAEMON_LOG"
while true; do sleep 300; done
EOF
  chmod +x "$tmp_sibling"
  mv "$tmp_sibling" "$DAEMON_SCRIPT"
}

start_via_argv() {
  # Exactly the argv the registry row's start_argv would produce.
  nohup /bin/bash "$DAEMON_SCRIPT" >>"$DAEMON_LOG" 2>&1 &
  disown
  for _ in $(seq 1 50); do
    [[ -s "$PIDFILE" ]] && break
    sleep 0.1
  done
}

wait_for_pidfile_pid_alive() {
  for _ in $(seq 1 50); do
    local p; p="$(cat "$PIDFILE" 2>/dev/null || true)"
    [[ -n "$p" && -d "/proc/$p" ]] && { printf '%s\n' "$p"; return 0; }
    sleep 0.1
  done
  return 1
}

kill_if_alive() {
  local p="${1:-}"
  [[ -n "$p" ]] || return 0
  kill -9 "$p" 2>/dev/null || true
}

# A registry with exactly ONE restart_on_stale row.
REGISTRY_PATH="$TMP/observer_registry.json"
write_registry() {
  cat > "$REGISTRY_PATH" <<EOF
{
  "observers": [
    {
      "id": "fakedaemon",
      "script": "$DAEMON_REL",
      "contract": "v1",
      "runtime": {
        "pidfile": "$PIDFILE",
        "expected_path": "$DAEMON_REL",
        "provenance": "$PIDFILE.provenance.json",
        "restart_on_stale": true,
        "start_argv": ["/bin/bash", "{canonical_root}/$DAEMON_REL"],
        "log": "$DAEMON_LOG"
      }
    }
  ]
}
EOF
}

# =============================================================================
# case a — CURRENT: fd inode matches the on-disk inode. No restart.
# =============================================================================
write_registry
write_daemon_v1
start_via_argv
old_pid="$(wait_for_pidfile_pid_alive)"
[[ -n "$old_pid" ]] || { echo "FIXTURE FAILED: fakedaemon never wrote its pidfile"; exit 1; }

check_registry_restarts
new_pid="$(cat "$PIDFILE" 2>/dev/null || true)"
chk "a: current daemon left untouched" "$new_pid" "$old_pid"
chk_true "a: current daemon still alive" "$([[ -d "/proc/$old_pid" ]] && echo 1 || echo 0)"

# =============================================================================
# case b — STALE: write+rename replaces the script under the running daemon.
# check_registry_restarts must kill the old pid and relaunch a new one.
# =============================================================================
write_daemon_v2
check_registry_restarts
new_pid="$(wait_for_pidfile_pid_alive || true)"
chk_true "b: old pid is gone" "$([[ ! -d "/proc/$old_pid" ]] && echo 1 || echo 0)"
chk_true "b: a NEW pid is now alive" "$([[ -n "$new_pid" && -d "/proc/$new_pid" ]] && echo 1 || echo 0)"
if [[ -n "$new_pid" && -n "$old_pid" ]]; then
  chk_true "b: new pid differs from old pid" "$([[ "$new_pid" != "$old_pid" ]] && echo 1 || echo 0)"
fi
chk_true "b: v2 actually came up (log shows it)" "$(grep -q 'fakedaemon v2 up' "$DAEMON_LOG" && echo 1 || echo 0)"
stale_pid="$new_pid"

# =============================================================================
# case c — RATE LIMIT: a second STALE verdict inside RESTART_MIN_INTERVAL_S
# must NOT restart again (the H-4 storm-bound, generalised).
# =============================================================================
write_daemon_v2   # already current for the pid from case b, so force staleness again
check_registry_restarts
after_rate_limited="$(cat "$PIDFILE" 2>/dev/null || true)"
chk "c: rate-limited — same pid as after case b" "$after_rate_limited" "$stale_pid"

# =============================================================================
# case d — NOT RUNNING: no restart is attempted from here (deliverable-3
# territory — report/alarm, not this tick's job).
# =============================================================================
kill_if_alive "$stale_pid"
for _ in $(seq 1 30); do [[ -d "/proc/$stale_pid" ]] || break; sleep 0.1; done
rm -f "$PIDFILE"
launches_before="$(grep -c 'v[12] up' "$DAEMON_LOG" || true)"
check_registry_restarts
launches_after="$(grep -c 'v[12] up' "$DAEMON_LOG" || true)"
chk "d: not_running triggers no relaunch here" "$launches_after" "$launches_before"

# =============================================================================
# case e — IDENTITY SAFETY: a pidfile pointing at a live STRANGER process
# (argv does not contain the daemon's basename) must never be signalled.
# =============================================================================
stranger_pid_file="$TMP/stranger.marker"
/bin/sleep 300 &
stranger=$!
echo "$stranger" > "$PIDFILE"
check_registry_restarts
chk_true "e: the stranger was never signalled" "$([[ -d "/proc/$stranger" ]] && echo 1 || echo 0)"
kill -9 "$stranger" 2>/dev/null || true
wait "$stranger" 2>/dev/null || true
rm -f "$PIDFILE" "$stranger_pid_file"

echo "---- $pass passed, $fail failed ----"
[ "$fail" -eq 0 ]
