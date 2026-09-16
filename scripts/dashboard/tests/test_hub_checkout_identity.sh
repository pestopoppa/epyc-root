#!/bin/bash
# Regression test: hub_supervisor.sh must refuse to supervise from a LINKED git
# worktree, must NOT refuse from a primary checkout or a non-git fixture, and a
# failing stale-source restart must be reported, not abort the caller.
#
# WHY (2026-09-16). The :8100 hub was found serving from a lane worktree for the
# second time (2026-08-21, 2026-09-15): a supervisor launched with EPYC_ROOT set
# to the lane. The /proc-cwd guard tried on 2026-08-24 false-positived in this
# container and was reverted; this guard asks git (--git-dir vs --git-common-dir).
#
# SCOPE: extracted predicates only. It never sources the supervisor's dispatch and
# never reaches the real restart_hub/kill path -- on 2026-07-27 a supervisor test
# that believed itself isolated killed the live daemon.
set -euo pipefail   # MATCH PRODUCTION
cd "$(dirname "$0")/../../.." || exit 1
SUP=scripts/dashboard/hub_supervisor.sh
TMP=$(mktemp -d); trap 'rm -rf "$TMP"' EXIT

eval "$(sed -n '/^root_is_linked_worktree()/,/^}/p;/^refuse_linked_worktree()/,/^}/p;/^check_hub_stale_source()/,/^}/p' "$SUP")"
log() { :; }

pass=0; fail=0
chk() { if [ "$2" = "$3" ]; then echo "  PASS  $1"; pass=$((pass+1));
        else echo "  FAIL  $1 (got $2, want $3)"; fail=$((fail+1)); fi; }

PRIMARY="$TMP/primary"
git init -q -b main "$PRIMARY"
git -C "$PRIMARY" -c user.email=t@t -c user.name=t commit -q --allow-empty -m base
git -C "$PRIMARY" worktree add -q "$TMP/lane" -b lane >/dev/null 2>&1
mkdir -p "$TMP/plain"

EPYC_ROOT="$PRIMARY"; rc=0; root_is_linked_worktree || rc=$?
chk "primary checkout -> not linked" "$rc" 1
EPYC_ROOT="$TMP/lane"; rc=0; root_is_linked_worktree || rc=$?
chk "linked worktree -> linked" "$rc" 0
EPYC_ROOT="$TMP/plain"; rc=0; root_is_linked_worktree || rc=$?
chk "non-git fixture -> proceeds (not linked)" "$rc" 1
EPYC_ROOT="$TMP/missing"; rc=0; root_is_linked_worktree || rc=$?
chk "missing root -> proceeds (not linked)" "$rc" 1

# refuse_linked_worktree exits 3 on a lane (run in a subshell so exit is contained)
rc=0; ( EPYC_ROOT="$TMP/lane"; refuse_linked_worktree ) || rc=$?
chk "refuse on lane -> exit 3" "$rc" 3
rc=0; ( EPYC_ROOT="$TMP/lane"; HUB_ALLOW_LINKED_WORKTREE=1; refuse_linked_worktree ) || rc=$?
chk "override on lane -> allowed" "$rc" 0
rc=0; ( EPYC_ROOT="$PRIMARY"; refuse_linked_worktree ) || rc=$?
chk "primary -> allowed" "$rc" 0

# check_hub_stale_source: a FAILING restart must return 1 under set -e, not abort.
STALE_SRC_STATE="$TMP/stale_src"
hub_source_is_newer() { return 0; }
hub_newest_source_mtime() { echo 123; }
restart_hub() { return 1; }
rc=0; check_hub_stale_source || rc=$?
chk "failed stale restart -> returns 1 (reported)" "$rc" 1
rc=0; ( set -e; check_hub_stale_source || true; echo ok >"$TMP/after2" ) || rc=$?
chk "loop-style caller survives failed restart" "$( [ -f "$TMP/after2" ] && echo yes || echo no )" "yes"
restart_hub() { return 0; }
rm -f "$STALE_SRC_STATE"
rc=0; check_hub_stale_source || rc=$?
chk "successful stale restart -> 0" "$rc" 0

echo "  ---- $pass passed, $fail failed"
[ "$fail" -eq 0 ]
