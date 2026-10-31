#!/bin/bash
set -euo pipefail
D=/mnt/raid0/llm/tmp/codex-ni-yarn-agg1g-prep-20261031
OUT=$D/run
BUILD=/mnt/raid0/llm/kernels/builds/gpu-20260921-ffc1bac82/bin
VIEW=/mnt/raid0/llm/tmp/codex-ni-gpu-anchor-custody-20261030/private-v10-view/bin
MODEL=/mnt/raid0/llm/models/Qwen3.8-27B-Q8_0.gguf
TEMPLATE=/mnt/raid0/llm/models/chat-templates/epyc-qwen3x-v1-terse.jinja
: "${FILLER_DEADLINE:?live grant deadline required}"
: "${FILLER_STOPFILE:?live stop path required}"
: "${FILLER_PIDFILE:?captured child pid file required}"
: "${FILLER_LIB:?filler library required}"
SMOKE=0
if [[ ${1:-} == --smoke ]]; then SMOKE=1; shift; fi
[[ $# == 0 ]] || exit 64
if [[ $SMOKE == 1 ]]; then
  [[ ${FILLER_CPUS:-} == 184-185 ]] || { echo 'REFUSED: wrong GPU smoke CPU list' >&2; exit 6; }
else
  [[ ${FILLER_CPUS:-} == 184-191 ]] || { echo 'REFUSED: wrong GPU host CPU grant' >&2; exit 6; }
fi
[[ -f $OUT/plan/plan.json ]] || { echo 'REFUSED: no frozen plan' >&2; exit 6; }
if [[ $SMOKE == 1 ]]; then expected_affinity=184,185; else expected_affinity=184-191; fi
taskset -pc $$ | grep -q "$expected_affinity" || { echo 'REFUSED: host affinity differs' >&2; exit 6; }
sha256sum -c "$D/ARCHIVE.sha256" >/dev/null
export YARN_1G_IDENTITY=$D/RUN-IDENTITY.json
export EPYC_ROOT=$D/archive
LD_LIBRARY_PATH="$VIEW:/opt/rocm/lib:/usr/lib/llvm-20/lib:/opt/AMD/aocc-compiler-5.0.0/lib" \
  "$D/archive/scripts/utils/verify_ggml_linkage.sh" "$VIEW/llama-server" "$BUILD" >/dev/null
if [[ $SMOKE == 0 ]]; then
  "/mnt/raid0/llm/tmp/clbench-venv/bin/python" -B "$D/preflight.py"
fi
YG_ID=yarn-agg-1g-power
YG_PLAN=native-gate-power-1g
YG_OUT=$OUT
YG_PORT=18155
. "$D/archive/yarn_gate_lib.sh"
if [[ $SMOKE == 1 ]]; then
  YG_ID=yarn-agg-1g-power-smoke
  YG_PLAN=native-gate-power-1g-smoke
  YG_OUT=$D/smoke
  YG_PORT=18156
  YG_LOAD_S=20
  YG_MIN_ARM_S=20
fi
YG_RUNNER=$D/archive/scripts/benchmark/yarn_gate/arm_runner.py
YG_PY=/mnt/raid0/llm/tmp/clbench-venv/bin/python
YG_LINKAGE=$D/archive/scripts/utils/verify_ggml_linkage.sh
# The frozen v10 production alias is stale for the unversioned HIP library.
# Run the private copy of the same pinned v10 binary so its sibling backend scan
# sees the versioned HIP alias, while linkage resolution checks the canonical v10 target.
yg_lib_path() { echo "$VIEW:/opt/rocm/lib:/usr/lib/llvm-20/lib:/opt/AMD/aocc-compiler-5.0.0/lib"; }
if [[ $SMOKE == 1 ]]; then
  smoke_cleanup() {
    local pid=${YG_ACTIVE_SERVER_PID:-} born=${YG_ACTIVE_SERVER_BIRTH:-} current state i
    [[ $pid =~ ^[0-9]+$ && $born =~ ^[0-9]+$ ]] || return 0
    [[ -r /proc/$pid/stat ]] || return 0
    current=$(awk '{print $22}' "/proc/$pid/stat")
    [[ $current == "$born" ]] || return 0
    state=$(ps -p "$pid" -o stat= 2>/dev/null || :)
    [[ -n $state && $state != Z* ]] || return 0
    kill -TERM -- "-$pid" 2>/dev/null || :
    for i in {1..10}; do ps -p "$pid" -o stat= 2>/dev/null | grep -qv '^Z' || break; sleep 1; done
    state=$(ps -p "$pid" -o stat= 2>/dev/null || :)
    if [[ -n $state && $state != Z* ]]; then kill -KILL -- "-$pid" 2>/dev/null || :; fi
    for i in {1..10}; do ps -p "$pid" -o stat= 2>/dev/null | grep -qv '^Z' || break; sleep 1; done
    state=$(ps -p "$pid" -o stat= 2>/dev/null || :)
    [[ -z $state || $state == Z* ]] || echo "SMOKE_CLEANUP_FAILED pid=$pid" >&2
  }
  trap smoke_cleanup EXIT
  trap 'exit 143' TERM INT
  . "$FILLER_LIB"
  rd=$YG_OUT/windows/$(date -u +%Y%m%dT%H%M%SZ)
  mkdir -p "$rd"
  yg_resolve "$rd"
  yg_tenancy
  yg_identity "$rd"
  set +e
  yg_arm_once A1 "$((FILLER_DEADLINE-5))" "$rd" "$rd/A1.stopflag"
  smoke_rc=$?
  set -e
  [[ $smoke_rc == 0 ]] || exit "$smoke_rc"
  "$YG_PY" -I "$YG_RUNNER" decide --out "$YG_OUT" --identity-file "$rd/identity.json" > "$rd/decide.txt"
  "$YG_PY" -B "$D/smoke_evaluate.py" "$YG_OUT" "$rd"
  exit 0
fi
set +e
yg_main
rc=$?
set -e
if [[ -f $OUT/COMPLETE ]]; then
  "$YG_PY" -I "$D/evaluate.py" "$OUT" > "$OUT/POWER-RESULT.json"
  exit 0
fi
if [[ $rc == 0 || $rc == 4 || $rc == 7 ]]; then
  printf 'partial=true rc75 reason=window-or-resource remaining=%s\n' \
    "$("$YG_PY" -I "$YG_RUNNER" status --out "$OUT" --json | "$YG_PY" -c 'import json,sys;d=json.load(sys.stdin);print(sum(v["pending"] for v in d["arms"].values()))')"
  exit 75
fi
exit "$rc"
