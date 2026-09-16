#!/bin/bash
# Regression test: the read-only hub VIEW (dashboard fix A, 2026-09-16).
#
# WHY. The hub serves whatever checkout the launch manifest names. A lane stops
# advancing when the lane does (the AutoKernel lane sat 141 commits behind
# origin/main), so pushed progress never appeared. The hub now serves a standalone
# clone marked `.epyc-view-readonly`, and refresh_hub_view.sh advances it.
#
# Checks:
#   A. refresh_hub_view.sh against a FAKE origin: refuses unmarked trees and linked
#      worktrees; advances to origin/main; discards local edits; regenerates the
#      untracked artifacts and reverts the generator's edit to a tracked file;
#      does not regenerate when nothing moved.
#   B. mtimes: a handoff-only refresh leaves dashboard/*.py mtimes alone (so the
#      stale-source check does NOT restart the hub); a dashboard commit moves them
#      (so it restarts exactly once).
#   C. supervisor wiring: refresh_hub_view runs only for a marked, non-linked hub
#      source, is rate-limited, never aborts under set -e; deploy-sync is skipped
#      for a view; once/loop both call it before the sync; `plan` reports it.
#
# SCOPE: extracted functions, the refresher against throwaway repos, and the
# read-only `plan` subcommand. Nothing reaches kill_wedged_hub or restart_hub (on
# 2026-07-27 a supervisor test that believed itself isolated killed the live daemon).
set -euo pipefail   # MATCH PRODUCTION
cd "$(dirname "$0")/../../.." || exit 1
REPO_DIR="$PWD"
SUP="$REPO_DIR/scripts/dashboard/hub_supervisor.sh"
REFRESH="$REPO_DIR/scripts/dashboard/refresh_hub_view.sh"
TMP=$(mktemp -d); trap 'rm -rf "$TMP"' EXIT
PY="$(command -v python3)"
export GIT_CONFIG_GLOBAL=/dev/null GIT_AUTHOR_NAME=t GIT_AUTHOR_EMAIL=t@t \
       GIT_COMMITTER_NAME=t GIT_COMMITTER_EMAIL=t@t

pass=0; fail=0
chk() { if [ "$2" = "$3" ]; then echo "  PASS  $1"; pass=$((pass+1));
        else echo "  FAIL  $1 (got $2, want $3)"; fail=$((fail+1)); fi; }

# --- fixture: a fake origin (bare) seeded from a work repo -------------------- #
WORK="$TMP/work"; ORIGIN="$TMP/origin.git"
git init -q -b main "$WORK"
mkdir -p "$WORK/dashboard" "$WORK/handoffs/active" "$WORK/scripts/handoffs" "$WORK/data"
echo "v1" > "$WORK/dashboard/server.py"
echo "# master" > "$WORK/handoffs/active/master-handoff-index.md"
echo "- [ ] task" > "$WORK/handoffs/active/h1.md"
printf 'handoffs/active/.index-state.json\nhandoffs/active/.index-graph.json\ndata/handoff_timeline.json\n' > "$WORK/.gitignore"
# Stub generators: write the artifacts, and (like the real index_state.py) edit
# the TRACKED master index, which the refresher must revert.
cat > "$WORK/scripts/handoffs/index_state.py" <<'PY'
import pathlib, datetime
a = pathlib.Path("handoffs/active")
(a / ".index-state.json").write_text('{"n": %d}\n' % len(list(a.glob("*.md"))))
(a / ".index-graph.json").write_text('{"generated_at": "%s"}\n' % datetime.datetime.now().isoformat())
m = a / "master-handoff-index.md"; m.write_text(m.read_text() + "GENERATED ROLLUP\n")
with open("regen.count", "a") as fh: fh.write("x")
PY
cat > "$WORK/scripts/handoffs/build_handoff_timeline.py" <<'PY'
import sys, pathlib
repo = pathlib.Path(sys.argv[sys.argv.index("--repo") + 1])
(repo / "data").mkdir(exist_ok=True)
(repo / "data" / "handoff_timeline.json").write_text('{"ok": true}\n')
PY
echo "regen.count" >> "$WORK/.gitignore"
git -C "$WORK" add -A; git -C "$WORK" commit -qm base
git clone -q --bare "$WORK" "$ORIGIN"
git -C "$WORK" remote add origin "$ORIGIN"

VIEW="$TMP/views/root-main"
git clone -q "$ORIGIN" "$VIEW"
push_change() {   # $1 = path, $2 = content
  echo "$2" > "$WORK/$1"; git -C "$WORK" add "$1"
  git -C "$WORK" commit -qm "change $1"; git -C "$WORK" push -q origin main
}
export HUB_VIEW_PYTHON="$PY"

# ---------------------------------------------------------------- A. refresher #
rc=0; "$REFRESH" "$VIEW" 2>/dev/null || rc=$?
chk "A1 unmarked tree -> refused (3)" "$rc" 3
chk "A1 unmarked tree -> still on branch main" "$(git -C "$VIEW" symbolic-ref -q --short HEAD || echo detached)" "main"

LANE="$TMP/lane"
git -C "$VIEW" worktree add -q "$LANE" -b lane >/dev/null 2>&1
touch "$LANE/.epyc-view-readonly"
rc=0; "$REFRESH" "$LANE" 2>/dev/null || rc=$?
chk "A2 marked LINKED worktree -> refused (3)" "$rc" 3
git -C "$VIEW" worktree remove --force "$LANE"

touch "$VIEW/.epyc-view-readonly"
echo ".epyc-view-readonly" >> "$VIEW/.git/info/exclude"
push_change handoffs/active/h1.md "- [x] task"
echo "local hand edit" > "$VIEW/handoffs/active/h1.md"
rc=0; out="$("$REFRESH" "$VIEW" 2>&1)" || rc=$?
chk "A3 refresh -> rc 0" "$rc" 0
chk "A3 view HEAD == origin/main" "$(git -C "$VIEW" rev-parse HEAD)" "$(git -C "$WORK" rev-parse HEAD)"
chk "A3 view is detached" "$(git -C "$VIEW" symbolic-ref -q HEAD >/dev/null && echo attached || echo detached)" "detached"
chk "A3 local edit discarded" "$(cat "$VIEW/handoffs/active/h1.md")" "- [x] task"
chk "A3 artifacts generated" "$(ls -A "$VIEW/handoffs/active/.index-state.json" "$VIEW/handoffs/active/.index-graph.json" "$VIEW/data/handoff_timeline.json" | wc -l)" 3
chk "A3 tracked master index reverted" "$(grep -c GENERATED "$VIEW/handoffs/active/master-handoff-index.md" || true)" 0
chk "A3 view clean (porcelain)" "$(git -C "$VIEW" status --porcelain | wc -l)" 0
chk "A3 log line says head moved + regen" "$(grep -c 'head=.*->.*(+1) regen=yes(head-moved) rc=0' <<<"$out")" 1

rc=0; out="$("$REFRESH" "$VIEW" 2>&1)" || rc=$?
chk "A4 nothing new -> rc 0, unchanged, no regen" "$rc:$(grep -c 'head=unchanged regen=no' <<<"$out")" "0:1"
chk "A4 generator ran exactly once so far" "$(cat "$VIEW/regen.count")" "x"

rm -f "$VIEW/data/handoff_timeline.json"
"$REFRESH" "$VIEW" 2>/dev/null
chk "A5 missing artifact -> regenerated" "$( [ -f "$VIEW/data/handoff_timeline.json" ] && echo yes || echo no)" "yes"
touch -d '-2 hours' "$VIEW/handoffs/active/.index-graph.json"
out="$(HUB_VIEW_REGEN_MAX_AGE_S=3600 "$REFRESH" "$VIEW" 2>&1)"
chk "A6 aged artifact -> regenerated" "$(grep -c 'regen=yes(aged:' <<<"$out")" 1

git -C "$VIEW" remote set-url origin "$TMP/nonexistent.git"
head_before="$(git -C "$VIEW" rev-parse HEAD)"
rc=0; "$REFRESH" "$VIEW" 2>/dev/null || rc=$?
chk "A7 fetch failure -> rc 1, view untouched" "$rc:$(git -C "$VIEW" rev-parse HEAD)" "1:$head_before"
git -C "$VIEW" remote set-url origin "$ORIGIN"

LOGF="$TMP/refresh.log"
HUB_VIEW_LOG="$LOGF" "$REFRESH" "$VIEW" 2>/dev/null
chk "A8 HUB_VIEW_LOG receives the result line" "$(grep -c '\[hub-view\] refresh view=' "$LOGF")" 1

# ----------------------------------------------------------------- B. mtimes #
SRV="$VIEW/dashboard/server.py"
touch -d '2020-01-01' "$SRV"; m0="$(stat -c %Y "$SRV")"
push_change handoffs/active/h1.md "- [x] task (again)"
"$REFRESH" "$VIEW" 2>/dev/null
chk "B1 handoff-only refresh leaves dashboard mtime" "$(stat -c %Y "$SRV")" "$m0"
push_change dashboard/server.py "v2"
"$REFRESH" "$VIEW" 2>/dev/null
m1="$(stat -c %Y "$SRV")"
chk "B2 dashboard commit moves dashboard mtime" "$(( m1 > m0 ))" 1
chk "B2 dashboard content is origin's" "$(cat "$SRV")" "v2"

# Stale-source predicate against the view, with a hub "started" now.
HUB_SRC="$VIEW"; STALE_SRC_SKEW_S=5
resolve_hub_spec() { :; }
eval "$(sed -n '/^hub_newest_source_mtime()/,/^}/p;/^hub_source_is_newer()/,/^}/p' "$SUP")"
sleep 1; ( exec sleep 30 ) & HUBPID=$!
hub_pids() { printf '%s ' "$HUBPID"; }
sleep 1
push_change handoffs/active/h1.md "- [ ] reopened"
"$REFRESH" "$VIEW" 2>/dev/null
rc=0; hub_source_is_newer || rc=$?
chk "B3 hub started after v2; handoff refresh -> current (no restart)" "$rc" 1
sleep 6
push_change dashboard/server.py "v3"
"$REFRESH" "$VIEW" 2>/dev/null
rc=0; hub_source_is_newer || rc=$?
chk "B4 dashboard change after hub start -> STALE (restart)" "$rc" 0
kill "$HUBPID" 2>/dev/null || true; wait "$HUBPID" 2>/dev/null || true

# ------------------------------------------------------ C. supervisor wiring #
CANON="$TMP/canon"; mkdir -p "$CANON/logs"
LOG_DIR="$CANON/logs"; SUP_LOG="$LOG_DIR/hub_supervisor.log"; HUB_PYTHON="$PY"
log() { echo "$*" >>"$TMP/suplog"; }
eval "$(sed -n '/^HUB_VIEW_REFRESH_ENABLED=/,/^HUB_VIEW_REFRESHER=/p' "$SUP")"
for fn in is_linked_worktree is_hub_view view_refresh_age_s refresh_hub_view; do
  eval "$(sed -n "/^${fn}()/,/^}/p" "$SUP")"
done
eval "$(sed -n '/^HUB_VIEW_REFRESH_STATE=/p' "$SUP")"
chk "C0 default interval 180s" "$HUB_VIEW_REFRESH_INTERVAL_S" 180

CALLS="$TMP/calls"; : >"$CALLS"
FAKE_REFRESHER="$TMP/fake_refresher.sh"
printf '#!/bin/bash\necho "$1 log=$HUB_VIEW_LOG" >>"%s"\nexit "${FAKE_RC:-0}"\n' "$CALLS" > "$FAKE_REFRESHER"
chmod +x "$FAKE_REFRESHER"
HUB_VIEW_REFRESHER="$FAKE_REFRESHER"

rc=0; is_hub_view "$VIEW" || rc=$?; chk "C1 marked clone is a view" "$rc" 0
rc=0; is_hub_view "$WORK" || rc=$?; chk "C1 unmarked repo is not a view" "$rc" 1
git -C "$VIEW" worktree add -q "$LANE" -b lane2 >/dev/null 2>&1
touch "$LANE/.epyc-view-readonly"
rc=0; is_hub_view "$LANE" || rc=$?; chk "C1 marked linked worktree is NOT a view" "$rc" 1

HUB_SRC="$LANE"; refresh_hub_view
chk "C2 lane hub source -> refresher not called" "$(wc -l <"$CALLS")" 0
HUB_SRC="$WORK"; refresh_hub_view
chk "C2 unmarked hub source -> refresher not called" "$(wc -l <"$CALLS")" 0
HUB_SRC="$VIEW"; refresh_hub_view
chk "C3 view hub source -> refresher called once with the view" "$(cat "$CALLS")" "$VIEW log=$SUP_LOG"
refresh_hub_view
chk "C4 rate-limited within the interval" "$(wc -l <"$CALLS")" 1
HUB_VIEW_REFRESH_INTERVAL_S=0
rc=0; ( set -e; FAKE_RC=1 refresh_hub_view; echo survived >"$TMP/after" ) || rc=$?
chk "C5 failing refresher -> supervisor survives set -e" "$(cat "$TMP/after" 2>/dev/null)" "survived"
chk "C5 failure logged" "$(grep -c 'refresher exited 1' "$TMP/suplog")" 1
HUB_VIEW_REFRESH_ENABLED=0; : >"$CALLS"; refresh_hub_view
chk "C6 disabled -> not called" "$(wc -l <"$CALLS")" 0
HUB_VIEW_REFRESH_ENABLED=1

# deploy-sync is skipped for a view (no fetch, no writes)
DEPLOY_SYNC_ENABLED=1; DEPLOY_SYNC_INTERVAL_S=0
eval "$(sed -n '/^DEPLOY_SYNC_STATE=/,/^}/p' "$SUP")"
eval "$(sed -n '/^sync_dashboard_from_origin()/,/^}/p' "$SUP")"
git() { if [[ " $* " == *" fetch "* ]]; then echo fetched >>"$TMP/fetches"; fi; command git "$@"; }
HUB_SRC="$VIEW"; sync_dashboard_from_origin
chk "C7 deploy-sync does not fetch/write a view" "$( [ -f "$TMP/fetches" ] && echo fetched || echo skipped)" "skipped"
unset -f git

# once/loop: both refresh the view, before the sync
for fn in cmd_once cmd_loop; do
  body="$(sed -n "/^${fn}()/,/^}/p" "$SUP")"
  chk "C8 $fn calls refresh_hub_view" "$(grep -c '^ *refresh_hub_view$' <<<"$body")" 1
  r="$(grep -n '^ *refresh_hub_view$' <<<"$body" | cut -d: -f1)"
  s="$(grep -n '^ *sync_dashboard_from_origin$' <<<"$body" | cut -d: -f1)"
  chk "C8 $fn refreshes before syncing" "$(( r < s ))" 1
done
chk "C9 stable marker still present" "$(grep -c 'HUB_SUPERVISOR_MANIFEST_LAUNCH_V1' "$SUP")" 1

# `plan` (read-only) names the view and the refresher, and skips deploy-sync
LLM="$TMP/llm"; mkdir -p "$LLM"
MANIFEST="$TMP/launch_manifest.yaml"
cat > "$MANIFEST" <<YAML
aux_services:
  - name: handoff_dashboard
    port: 18100
    argv: ["{python}", "-m", "dashboard.server", "--host", "0.0.0.0", "--port", "18100"]
    cwd: "$VIEW"
    pythonpath: ["$VIEW"]
    health_path: /health
    model_label: fixture hub
    log: handoff_dashboard.log
YAML
out="$(env EPYC_ROOT="$CANON" HUB_CANONICAL_ROOT="$CANON" HUB_LAUNCH_MANIFEST="$MANIFEST" \
        HUB_PYTHON="$PY" HUB_SPEC_RESOLVER=local HUB_PORT=18100 ORCHESTRATOR_PATHS_LLM_ROOT="$LLM" \
        bash "$SUP" plan 2>/dev/null)" || true
chk "C10 plan: hub source is the view" "$(grep -c "hub source  : $VIEW\$" <<<"$out")" 1
chk "C10 plan: deploy-sync skipped for view" "$(grep -c 'deploy-sync : SKIP (hub source is a read-only view' <<<"$out")" 1
chk "C10 plan: view-refresh enabled, sibling refresher" "$(grep -c "view-refresh: enabled=1 every 180s via $REPO_DIR/scripts/dashboard/refresh_hub_view.sh " <<<"$out")" 1
git -C "$VIEW" worktree remove --force "$LANE"

echo "  ---- $pass passed, $fail failed"
[ "$fail" -eq 0 ]
