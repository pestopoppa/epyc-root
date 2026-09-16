#!/bin/bash
# Regression test: hub_supervisor.sh follows the orchestrator launch manifest for
# WHERE and HOW the hub runs, and keeps its own home in the canonical root.
#
# WHY (2026-09-16). An earlier version of this branch refused to run whenever
# EPYC_ROOT was a linked worktree, on the premise that "a hub serving a lane is a
# misconfiguration". That premise was wrong: orchestrator f5476148 (2026-09-09)
# deliberately points the manifest's `handoff_dashboard` cwd/pythonpath at a
# reviewed lane. The supervisor must now:
#   * launch the hub with the manifest's cwd, env and argv;
#   * never deploy-sync into a linked-worktree hub source;
#   * refuse only when its HOME (EPYC_ROOT) is not the canonical root;
#   * keep the two-probe restart and survive a failed stale-source restart.
#
# SCOPE: extracted functions plus the read-only `plan` subcommand. Nothing here
# reaches kill_wedged_hub or restart_hub. On 2026-07-27 a supervisor test that
# believed itself isolated killed the live daemon. The launched "hub" is a
# recorder module that writes its cwd/env/argv and exits, and it binds no port.
set -euo pipefail   # MATCH PRODUCTION
cd "$(dirname "$0")/../../.." || exit 1
REPO_DIR="$PWD"
SUP="$REPO_DIR/scripts/dashboard/hub_supervisor.sh"
TMP=$(mktemp -d); trap 'rm -rf "$TMP"' EXIT
PY="$(command -v python3)"
ORCH=/mnt/raid0/llm/epyc-orchestrator

pass=0; fail=0
chk() { if [ "$2" = "$3" ]; then echo "  PASS  $1"; pass=$((pass+1));
        else echo "  FAIL  $1 (got $2, want $3)"; fail=$((fail+1)); fi; }

# --- fixture: canonical home, a primary repo, and a LINKED lane worktree ------ #
LLM="$TMP/llm"
CANON="$LLM/epyc-root"; mkdir -p "$CANON/logs"
PRIMARY="$LLM/primary"
git init -q -b main "$PRIMARY"
mkdir -p "$PRIMARY/dashboard"
cat > "$PRIMARY/dashboard/server.py" <<'PY'
import json, os, sys
out = os.environ["HUB_RECORD"]
with open(out, "w") as fh:
    json.dump({"cwd": os.getcwd(), "file": __file__, "argv": sys.argv[1:],
               "store": os.environ.get("AUTOKERNEL_LOOP_STORE_ROOT"),
               "pythonpath": os.environ.get("PYTHONPATH", "")}, fh)
PY
touch "$PRIMARY/dashboard/__init__.py"
git -C "$PRIMARY" add -A
git -C "$PRIMARY" -c user.email=t@t -c user.name=t commit -qm base
mkdir -p "$LLM/worktrees/mains"
LANE="$LLM/worktrees/mains/lane-fixture"
git -C "$PRIMARY" worktree add -q "$LANE" -b lane >/dev/null 2>&1

MANIFEST="$TMP/orch/orchestration/launch_manifest.yaml"
mkdir -p "$(dirname "$MANIFEST")"
cat > "$MANIFEST" <<'YAML'
aux_services:
  - name: other
    port: 1
    argv: ["{python}", "-c", "pass"]
    cwd: /nonexistent
    log: other.log
    model_label: other
  - name: handoff_dashboard
    port: 18100
    argv: ["{python}", "-m", "dashboard.server", "--host", "0.0.0.0", "--port", "18100"]
    cwd: "{llm_root}/worktrees/mains/lane-fixture"
    pythonpath: ["{llm_root}/worktrees/mains/lane-fixture"]
    env:
      AUTOKERNEL_LOOP_STORE_ROOT: /fixture/loop-store
    health_path: /health
    health_timeout: 30
    model_label: fixture hub
    log: handoff_dashboard.log
YAML

# --- load the supervisor's functions (no dispatch) ----------------------------- #
HUB_CANONICAL_ROOT="$CANON"; EPYC_ROOT="$CANON"
HUB_LAUNCH_MANIFEST="$MANIFEST"; HUB_SERVICE_NAME=handoff_dashboard
HUB_SPEC_HELPER="$REPO_DIR/scripts/dashboard/hub_launch_spec.py"
HUB_PYTHON="$PY"; HUB_PORT=18100; STARTUP_TIMEOUT=1
LOG_DIR="$CANON/logs"; SUP_LOG="$LOG_DIR/hub_supervisor.log"; HUB_LOG="$LOG_DIR/handoff_dashboard.log"
export ORCHESTRATOR_PATHS_LLM_ROOT="$LLM"
log() { echo "$*" >>"$TMP/log"; }
eval "$(sed -n '/^HUB_SRC=""/,/^HUB_M_ENV=()/p' "$SUP")"
for fn in resolve_hub_spec is_linked_worktree start_hub refuse_noncanonical_home \
          check_hub_stale_source hub_down_confirmed; do
  eval "$(sed -n "/^${fn}()/,/^}/p" "$SUP")"
done

run_launch() {   # $1 = resolver mode: orchestrator|local
  rm -f "$TMP/record.json"
  HUB_SPEC_SOURCE=""; HUB_M_CWD=""
  if [[ "$1" == local ]]; then export HUB_SPEC_RESOLVER=local; unset HUB_ORCHESTRATOR_ROOT
  else unset HUB_SPEC_RESOLVER; export HUB_ORCHESTRATOR_ROOT="$ORCH"; fi
  export HUB_RECORD="$TMP/record.json"
  start_hub
  for _ in $(seq 1 50); do [[ -s "$TMP/record.json" ]] && break; sleep 0.1; done
}
field() { "$PY" -c "import json,sys; print(json.load(open('$TMP/record.json'))[sys.argv[1]])" "$1"; }

# 1. launched with the manifest cwd, env and argv (local resolver)
run_launch local
chk "local resolver used" "${HUB_M_RESOLVER}" "local"
chk "hub source = manifest cwd (lane)" "${HUB_SRC}" "$LANE"
chk "hub cwd = manifest cwd" "$(field cwd)" "$LANE"
chk "hub imported the LANE's dashboard.server" "$(field file)" "$LANE/dashboard/server.py"
chk "manifest env applied" "$(field store)" "/fixture/loop-store"
chk "manifest pythonpath first" "$(field pythonpath | cut -d: -f1)" "$LANE"
chk "manifest argv applied" "$(field argv)" "['--host', '0.0.0.0', '--port', '18100']"

# 1b. same result through the orchestrator's own resolver, when it is importable
if [[ -f "$ORCH/scripts/server/stack_manifest.py" && -x "$ORCH/.venv/bin/python" ]]; then
  HUB_PYTHON="$ORCH/.venv/bin/python"
  run_launch orchestrator
  chk "orchestrator resolver used" "${HUB_M_RESOLVER}" "orchestrator"
  chk "orchestrator resolver: hub cwd" "$(field cwd)" "$LANE"
  chk "orchestrator resolver: env" "$(field store)" "/fixture/loop-store"
  chk "{python} -> HUB_PYTHON" "${HUB_M_ARGV[0]}" "$ORCH/.venv/bin/python"
  HUB_PYTHON="$PY"
else
  echo "  SKIP  orchestrator resolver not present on this host"
fi
unset HUB_ORCHESTRATOR_ROOT HUB_SPEC_RESOLVER

# 2. no writes into the lane (launch + resolution leave it clean)
chk "lane working tree untouched" "$(git -C "$LANE" status --porcelain --ignored | grep -v __pycache__ | wc -l)" 0

# 3. unreadable manifest -> loud fallback to cwd=EPYC_ROOT
HUB_LAUNCH_MANIFEST="$TMP/missing.yaml"; HUB_SPEC_SOURCE=""; : >"$TMP/log"
resolve_hub_spec
chk "fallback when manifest unreadable" "${HUB_SPEC_SOURCE}" "fallback"
chk "fallback cwd = EPYC_ROOT" "${HUB_M_CWD}" "$CANON"
chk "fallback logged loudly" "$(grep -c 'UNREADABLE' "$TMP/log")" 1
HUB_LAUNCH_MANIFEST="$MANIFEST"; HUB_SPEC_SOURCE=""

# 4. home guard: canonical home runs, a lane home refuses, a lane HUB SOURCE does not
rc=0; ( refuse_noncanonical_home ) || rc=$?; chk "canonical home -> allowed" "$rc" 0
rc=0; ( EPYC_ROOT="$LANE"; refuse_noncanonical_home ) || rc=$?; chk "lane as HOME -> exit 3" "$rc" 3
rc=0; ( EPYC_ROOT="$TMP/missing"; refuse_noncanonical_home ) || rc=$?; chk "missing home -> exit 3" "$rc" 3
ln -s "$CANON" "$TMP/canon-link"
rc=0; ( EPYC_ROOT="$TMP/canon-link"; refuse_noncanonical_home ) || rc=$?; chk "same-inode alias of canonical -> allowed" "$rc" 0

# 4b. the real script, read-only `plan`: runs from canonical, reports lane + skip
plan_env=(env EPYC_ROOT="$CANON" HUB_CANONICAL_ROOT="$CANON" HUB_LAUNCH_MANIFEST="$MANIFEST"
          HUB_PYTHON="$PY" HUB_SPEC_RESOLVER=local HUB_PORT=18100 ORCHESTRATOR_PATHS_LLM_ROOT="$LLM")
rc=0; out="$("${plan_env[@]}" bash "$SUP" plan 2>/dev/null)" || rc=$?
chk "plan from canonical home -> exit 0" "$rc" 0
chk "plan names the lane as hub source" "$(grep -c "hub source  : $LANE\$" <<<"$out")" 1
chk "plan skips deploy-sync for the lane" "$(grep -c 'deploy-sync : SKIP' <<<"$out")" 1
rc=0; "${plan_env[@]}" EPYC_ROOT="$LANE" bash "$SUP" once >/dev/null 2>&1 || rc=$?
chk "once with a lane HOME -> refused (exit 3)" "$rc" 3
chk "refused lane HOME gets no logs/ dir" "$( [ -e "$LANE/logs" ] && echo created || echo absent )" "absent"
chk "lane still clean after refusal" "$(git -C "$LANE" status --porcelain --ignored | grep -v __pycache__ | wc -l)" 0
chk "stable marker present" "$(grep -c 'HUB_SUPERVISOR_MANIFEST_LAUNCH_V1' "$SUP")" 1

# 5. check_hub_stale_source: a FAILING restart returns 1 under set -e, never aborts
STALE_SRC_STATE="$TMP/stale_src"
resolve_hub_spec() { :; }
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

# 6. two-probe rule
HEALTH_CONFIRM_DELAY_S=0
probes=(1 1); health_ok() { local r=${probes[0]}; probes=("${probes[@]:1}"); return "$r"; }
rc=0; hub_down_confirmed || rc=$?; chk "two failed probes -> down" "$rc" 0
probes=(1 0); rc=0; hub_down_confirmed || rc=$?; chk "second probe healthy -> not down" "$rc" 1
probes=(0); rc=0; hub_down_confirmed || rc=$?; chk "first probe healthy -> not down" "$rc" 1

# 7. once/loop parity: both run sync then stale-source on the healthy path
for fn in cmd_once cmd_loop; do
  body="$(sed -n "/^${fn}()/,/^}/p" "$SUP")"
  chk "$fn syncs" "$(grep -c sync_dashboard_from_origin <<<"$body")" 1
  chk "$fn checks stale source" "$(grep -c check_hub_stale_source <<<"$body")" 1
  chk "$fn uses the home guard" "$(grep -c refuse_noncanonical_home <<<"$body")" 1
done

echo "  ---- $pass passed, $fail failed"
[ "$fail" -eq 0 ]
