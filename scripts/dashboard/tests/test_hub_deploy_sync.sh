#!/bin/bash
# Regression test: sync_dashboard_from_origin must bring landed dashboard code into
# the SERVED tree, and must refuse to do damage while doing it.
#
# WHY (2026-08-28). The stale-source watchdog answers "is the running hub older than
# dashboard/ ON DISK" and was working correctly, yet four dashboard fixes published
# that day stayed invisible for hours: nothing ever updated dashboard/ on disk. The
# hub serves ${EPYC_ROOT} directly and that tree sat 35 commits behind origin/main.
# The watchdog closed "committed but not restarted"; this closes "committed but never
# arrived".
#
# SCOPE: the SYNC FUNCTION only, against a throwaway git repo. It never sources the
# supervisor's dispatch and never reaches restart_hub -- the sibling stale-source test
# carries the same restriction because on 2026-07-27 a supervisor test that believed
# itself isolated killed the live daemon.
set -euo pipefail   # MATCH PRODUCTION: running without -e is what hid two C42 bugs

cd "$(dirname "$0")/../../.." || exit 1
SUP=scripts/dashboard/hub_supervisor.sh
TMP=$(mktemp -d); trap 'rm -rf "$TMP"' EXIT

fail() { echo "FAIL: $*" >&2; exit 1; }
pass() { echo "  ok — $*"; }

# --- a throwaway repo shaped like the served tree ---------------------------- #
REPO="$TMP/epyc-root"
mkdir -p "$REPO/dashboard/static" "$REPO/logs"
# `-b main`: production is on main and the sync targets origin/main explicitly.
# A fixture defaulting to master would test a branch name that does not exist here.
git -C "$REPO" init -q -b main
git -C "$REPO" config user.email t@t; git -C "$REPO" config user.name t
echo "v1" > "$REPO/dashboard/server.py"
echo "v1" > "$REPO/dashboard/static/kernel.html"
echo "peer" > "$REPO/other.txt"
git -C "$REPO" add -A; git -C "$REPO" commit -qm base

# An "origin" with newer dashboard code plus a change OUTSIDE dashboard/.
UP="$TMP/upstream"; git clone -q "$REPO" "$UP"
git -C "$UP" config user.email t@t; git -C "$UP" config user.name t
echo "v2" > "$UP/dashboard/server.py"
echo "v2" > "$UP/dashboard/static/kernel.html"
echo "upstream-only" > "$UP/other.txt"
git -C "$UP" add -A; git -C "$UP" commit -qm newer
git -C "$REPO" remote add origin "$UP" 2>/dev/null || git -C "$REPO" remote set-url origin "$UP"
git -C "$REPO" fetch -q origin

# --- load ONLY the sync machinery ------------------------------------------- #
EPYC_ROOT="$REPO"
LOG_DIR="$REPO/logs"
DEPLOY_SYNC_ENABLED=1
DEPLOY_SYNC_INTERVAL_S=0
log() { :; }
eval "$(sed -n '/^DEPLOY_SYNC_STATE=/,/^}/p' "$SUP")"
eval "$(sed -n '/^deploy_sync_age_s()/,/^}/p' "$SUP")"
eval "$(sed -n '/^sync_dashboard_from_origin()/,/^}/p' "$SUP")"

# --- 1. it deploys landed dashboard code ------------------------------------- #
sync_dashboard_from_origin
[[ "$(cat "$REPO/dashboard/server.py")" == "v2" ]] || fail "server.py was not deployed"
[[ "$(cat "$REPO/dashboard/static/kernel.html")" == "v2" ]] || fail "kernel.html was not deployed"
pass "landed dashboard code reaches the served tree"

# --- 2. it stays out of everything that is not dashboard/ -------------------- #
[[ "$(cat "$REPO/other.txt")" == "peer" ]] || fail "sync touched a file outside dashboard/"
pass "files outside dashboard/ are untouched"

# --- 3. it never writes the shared INDEX ------------------------------------- #
staged="$(git -C "$REPO" diff --cached --name-only)"
[[ -z "$staged" ]] || fail "sync staged files (a peer's commit would sweep them): $staged"
pass "the git index is never written"

# --- 4. it never moves the branch or pushes ---------------------------------- #
[[ "$(git -C "$REPO" rev-parse HEAD)" == "$(git -C "$REPO" rev-parse main)" ]] \
  || fail "branch pointer moved"
pass "the branch pointer is not moved"

# --- 5. it refuses to clobber work in progress ------------------------------- #
echo "LOCAL WORK IN PROGRESS" > "$REPO/dashboard/server.py"
echo "v3" > "$UP/dashboard/server.py"
git -C "$UP" add -A; git -C "$UP" commit -qm v3; git -C "$REPO" fetch -q origin
rm -f "$DEPLOY_SYNC_STATE"
sync_dashboard_from_origin
[[ "$(cat "$REPO/dashboard/server.py")" == "LOCAL WORK IN PROGRESS" ]] \
  || fail "sync overwrote a locally-modified file — this is the no-reflog data loss case"
pass "a locally-modified file is never overwritten"

# --- 6. rate limiting actually limits ---------------------------------------- #
DEPLOY_SYNC_INTERVAL_S=99999
echo "v4" > "$UP/dashboard/static/kernel.html"
git -C "$UP" add -A; git -C "$UP" commit -qm v4; git -C "$REPO" fetch -q origin
sync_dashboard_from_origin
[[ "$(cat "$REPO/dashboard/static/kernel.html")" == "v2" ]] \
  || fail "sync ran despite the rate limit"
pass "the rate limit suppresses a too-soon sync"

# --- 7. it can be switched off ----------------------------------------------- #
DEPLOY_SYNC_ENABLED=0; DEPLOY_SYNC_INTERVAL_S=0; rm -f "$DEPLOY_SYNC_STATE"
sync_dashboard_from_origin
[[ "$(cat "$REPO/dashboard/static/kernel.html")" == "v2" ]] || fail "disabled sync still ran"
pass "DEPLOY_SYNC_ENABLED=0 disables it"

# --- 8. the loop actually calls it ------------------------------------------- #
# The whole outage was a function that existed and was never invoked on the code
# path in use: both of these ran in cmd_once and neither in cmd_loop.
loop_body="$(sed -n '/^cmd_loop()/,/^}/p' "$SUP")"
grep -q "sync_dashboard_from_origin" <<<"$loop_body" || fail "cmd_loop never calls the sync"
grep -q "check_hub_stale_source" <<<"$loop_body" || fail "cmd_loop never checks stale source"
pass "cmd_loop calls both the sync and the stale-source check"

echo "PASS: hub deploy-sync"
