#!/bin/bash
set -euo pipefail
BASE=/mnt/raid0/llm/tmp/codex-ni-20261027-kpf62-fixed-build
ID=kpf62-native-g1-pf-20261027
PY=/home/node/.local/bin/python3.12
ENGINE=/mnt/raid0/llm/tmp/fillers-3c4ca599/filler_run9.sh
FLAGS=/mnt/raid0/llm/tmp/compute-flags
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 BLIS_NUM_THREADS=1 NUMEXPR_NUM_THREADS=1
export PYTHONDONTWRITEBYTECODE=1 PYTHONNOUSERSITE=1 TZ=UTC
unset PYTHONPATH ORCHESTRATOR_TMP_DIR ORCHESTRATOR_PATHS_TMP_DIR
refuse() { printf 'REFUSED: %s\n' "$*" >&2; return 70; }
hold_guard() {
 local -a holds
 shopt -s nullglob globstar
 holds=(/mnt/raid0/llm/tmp/HOLD_* "$FLAGS"/HOLD_* "$FLAGS"/**/HOLD_*)
 ((${#holds[@]}==0)) || { refuse HOLD; return 70; }
 [[ ! -e $BASE/STOP && ! -L $BASE/STOP ]] || { refuse STOP; return 70; }
}
source_guard() {
 (cd "$BASE" && sha256sum --quiet -c SOURCE.SHA256SUMS) || return 70
 sha256sum --quiet -c "$BASE/NATIVE-SOURCES.sha256" || return 70
 [[ -s $BASE/MAIN-ACCEPTANCE.txt && ! -L $BASE/MAIN-ACCEPTANCE.txt ]] || refuse 'MAIN source review missing'
 grep -Fx 'source=MAIN-approved' "$BASE/MAIN-ACCEPTANCE.txt" >/dev/null || return 70
 grep -Fx "source-seal-sha256=$(sha256sum "$BASE/SOURCE.SHA256SUMS" | cut -d' ' -f1)" "$BASE/MAIN-ACCEPTANCE.txt" >/dev/null || return 70
}
