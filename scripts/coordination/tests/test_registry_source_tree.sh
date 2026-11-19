#!/bin/bash
# Regression + DORMANCY test for NIB2-89: the H-4 `source_tree` predicate generalised
# to registered daemons (bus_supervisor.sh `registry_source_tree_is_stale`, publisher
# daemon_source_tree.sh `dp_publish_source_tree`). Lands DORMANT: opt-in per registry
# row, and bus_supervisor stays DOWN by operator ruling. Starts NOTHING from the real
# tree; the one fake daemon is a `sleep` THIS TEST spawns and kills.
set -euo pipefail
cd "$(dirname "$0")/../../.." || exit 1
REPO="$PWD"
SUP=scripts/coordination/bus_supervisor.sh
PUB=scripts/coordination/daemon_source_tree.sh

TMP=$(mktemp -d)
cleanup() { [[ -n "${DPID:-}" ]] && kill -9 "$DPID" 2>/dev/null || true; rm -rf "$TMP"; }
trap cleanup EXIT

pass=0; fail=0
chk() { if [ "$2" = "$3" ]; then echo "  PASS  $1"; pass=$((pass+1));
        else echo "  FAIL  $1 (got $2, want $3)"; fail=$((fail+1)); fi; }

eval "$(sed -n '/^registry_restart_candidates()/,/^}/p;
                /^registry_daemon_identity()/,/^}/p;
                /^registry_source_tree_is_stale()/,/^}/p;
                /^registry_script_is_stale()/,/^}/p;
                /^stop_registry_daemon()/,/^}/p;
                /^start_registry_daemon()/,/^}/p;
                /^check_registry_restarts()/,/^}/p' "$SUP")"
log() { printf '%s %s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$*" >&2; }
# shellcheck source=/dev/null
source "$PUB"

# ---------------------------------------------------------------- git fixture
EPYC_ROOT="$TMP/root"; LOG_DIR="$TMP/logs"; STARTUP_TIMEOUT=3; RESTART_MIN_INTERVAL_S=60
mkdir -p "$EPYC_ROOT/scripts/system" "$LOG_DIR"
G() { git -C "$EPYC_ROOT" -c user.email=t@t -c user.name=t "$@"; }
G init -q
DAEMON_REL="scripts/system/fakedaemon.sh"
printf '#!/bin/bash\nwhile true; do sleep 1; done\n' > "$EPYC_ROOT/$DAEMON_REL"
G add -A; G commit -q -m v1
TREE1="$(G rev-parse HEAD:scripts/system)"

# a "daemon": a real process whose argv names fakedaemon.sh
cp "$EPYC_ROOT/$DAEMON_REL" "$TMP/fakedaemon.sh"
/bin/bash "$TMP/fakedaemon.sh" </dev/null >/dev/null 2>&1 & DPID=$!
PIDFILE="$TMP/d.pid"; echo "$DPID" > "$PIDFILE"; PROV="$TMP/d.prov.json"
sleep 0.2

# ---- publisher: flag off is a no-op ------------------------------------------
echo '{"pid": '"$DPID"', "inode": 1}' > "$PROV"
before="$(cat "$PROV")"
( unset DP_PUBLISH_SOURCE_TREE; dp_publish_source_tree "$EPYC_ROOT/$DAEMON_REL" "$PROV" )
chk "publisher: flag unset leaves the record byte-identical" "$(cat "$PROV")" "$before"
( DP_PUBLISH_SOURCE_TREE=0; dp_publish_source_tree "$EPYC_ROOT/$DAEMON_REL" "$PROV" )
chk "publisher: flag=0 leaves the record byte-identical" "$(cat "$PROV")" "$before"

# ---- publisher: flag on writes tree (as pid $$ of the caller) -----------------
( DP_PUBLISH_SOURCE_TREE=1; dp_publish_source_tree "$EPYC_ROOT/$DAEMON_REL" "$PROV" )
chk "publisher: flag=1 records the committed tree" \
    "$(python3 -c 'import json,sys;print(json.load(open(sys.argv[1]))["source_tree"])' "$PROV")" "$TREE1"
chk "publisher: preserves dp_attest's keys" \
    "$(python3 -c 'import json,sys;print(json.load(open(sys.argv[1]))["inode"])' "$PROV")" "1"

# The publisher stamps its own $$ (subshell pid); the predicate needs the LIVE pid.
rec() { echo '{"pid": '"${2:-$DPID}"', "source_tree": "'"$1"'"}' > "$PROV"; }

# ---- predicate ---------------------------------------------------------------
rc=0; rec "$TREE1"; registry_source_tree_is_stale "$DPID" "$PROV" scripts/system || rc=$?
chk "predicate: published == HEAD tree -> current (1)" "$rc" "1"

printf '#!/bin/bash\nwhile true; do sleep 1; done # v2\n' > "$EPYC_ROOT/$DAEMON_REL"; G add -A; G commit -q -m v2
rc=0; registry_source_tree_is_stale "$DPID" "$PROV" scripts/system || rc=$?
chk "predicate: HEAD moved past the published tree -> stale (0)" "$rc" "0"

rc=0; rec "$TREE1" 99999999; registry_source_tree_is_stale "$DPID" "$PROV" scripts/system || rc=$?
chk "predicate: record pid != live pid -> cannot tell (2)" "$rc" "2"

rc=0; echo '{"pid": '"$DPID"'}' > "$PROV"; registry_source_tree_is_stale "$DPID" "$PROV" scripts/system || rc=$?
chk "predicate: no published source_tree -> cannot tell (2)" "$rc" "2"

rc=0; rec "$TREE1"; registry_source_tree_is_stale "$DPID" "$PROV" scripts/nonexistent || rc=$?
chk "predicate: unresolvable tree path -> cannot tell (2)" "$rc" "2"

rc=0; registry_source_tree_is_stale "$DPID" "$TMP/missing.json" scripts/system || rc=$?
chk "predicate: missing provenance -> cannot tell (2)" "$rc" "2"

# ---- dispatch: default row (no stale_predicate) stays on the inode path --------
REGISTRY_PATH="$TMP/reg.json"
write_reg() {  # $1 = extra runtime json fragment (may be empty)
  cat > "$REGISTRY_PATH" <<JSON
{"observers":[{"id":"fd","script":"$DAEMON_REL","contract":"v1","runtime":{
 "pidfile":"$PIDFILE","expected_path":"$DAEMON_REL","provenance":"$PROV",
 "restart_on_stale":true,"start_argv":["/bin/true"],"log":""$1}}]}
JSON
}
write_reg ""
line="$(registry_restart_candidates)"
chk "candidates: default predicate is inode" "$(printf '%s' "$line" | cut -f6)" "inode"
chk "candidates: default tree path is dirname(expected_path)" "$(printf '%s' "$line" | cut -f7)" "scripts/system"
chk "candidates: log (last, empty) survives" "$(printf '%s' "$line" | awk -F'\t' '{print NF}')" "8"
write_reg ',"stale_predicate":"source_tree"'
chk "candidates: opt-in carried through" "$(registry_restart_candidates | cut -f6)" "source_tree"

# unknown predicate -> logged, nothing signalled
write_reg ',"stale_predicate":"bogus"'
check_registry_restarts 2>"$TMP/err" || true
chk "dispatch: unknown predicate fails closed" "$(grep -c "unknown stale_predicate 'bogus'" "$TMP/err")" "1"
chk "dispatch: the daemon was not signalled" "$([[ -d /proc/$DPID ]] && echo alive)" "alive"

# source_tree row, CURRENT -> untouched
rec "$(G rev-parse HEAD:scripts/system)"; write_reg ',"stale_predicate":"source_tree"'
check_registry_restarts 2>"$TMP/err" || true
chk "dispatch: source_tree current -> untouched" "$([[ -d /proc/$DPID ]] && echo alive)" "alive"

# source_tree row, STALE -> stop + relaunch via start_argv (/bin/true)
rec "$TREE1"
check_registry_restarts 2>"$TMP/err" || true
chk "dispatch: source_tree stale -> old pid stopped" "$([[ -d /proc/$DPID ]] && echo alive || echo gone)" "gone"
chk "dispatch: restart was logged" "$(grep -c 'STALE inode — restarting' "$TMP/err")" "1"
DPID=""

# ================================================================== DORMANCY ==
cd "$REPO"
# (1) the real registry: no row opts in, every candidate resolves to the inode default.
REGISTRY_PATH="$REPO/scripts/coordination/observer_registry.json"
optin="$(python3 -c '
import json,sys
reg=json.load(open(sys.argv[1]))
print(sum(1 for r in reg["observers"] if (r.get("runtime") or {}).get("stale_predicate") not in (None,"inode")))
' "$REGISTRY_PATH")"
chk "dormancy: zero real registry rows opt into source_tree" "$optin" "0"
chk "dormancy: every real restart candidate uses the inode predicate" \
    "$(registry_restart_candidates | cut -f6 | sort -u)" "inode"

# (2) nothing sources or executes the publisher outside this test.
refs="$(git ls-files -z -- scripts | xargs -0 grep -l 'daemon_source_tree\|dp_publish_source_tree' 2>/dev/null \
        | grep -v -e "^$PUB\$" -e '^scripts/coordination/tests/test_registry_source_tree.sh$' \
                  -e '^scripts/coordination/bus_supervisor.sh$' || true)"
chk "dormancy: no other script references the publisher" "$refs" ""

# (3) the untouched pinned/live-sourced files really are untouched by this change.
chk "dormancy: daemon_provenance.sh not modified" \
    "$(git diff --name-only origin/main -- scripts/coordination/daemon_provenance.sh scripts/coordination/observer_census.py | wc -l | tr -d ' ')" "0"

echo "---- $pass passed, $fail failed ----"
[ "$fail" -eq 0 ]
