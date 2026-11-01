#!/bin/bash
set -euo pipefail
D=/mnt/raid0/llm/tmp/codex-ni-kpf18-cpu-repair-20261101/r11
ID=codex-ni-kpf18-r11-full-bridge-v2-20261101
ENGINE=/mnt/raid0/llm/tmp/compute-flags/bin/qual-v1/filler_run14.sh
QUALIFIER=/mnt/raid0/llm/tmp/compute-flags/bin/qual-v1/qualify_launcher.py
[[ -x $ENGINE && -f $QUALIFIER ]] || { echo 'REFUSED: canonical qualifier bundle absent' >&2; exit 70; }
if [[ ${WS58_FINGERPRINT_ONLY:-0} == 1 && -z ${WS58_REGIONS:-} ]]; then WS58_REGIONS=0-95; fi
[[ -n ${WS58_REGIONS:-} ]] || { echo 'REFUSED: keeper region absent' >&2; exit 70; }
if [[ ${WS58_QUAL:-0} != 1 && ${WS58_FINGERPRINT_ONLY:-0} != 1 ]]; then
  exec >> "$D/ws58-launcher.out" 2>&1
fi
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 BLIS_NUM_THREADS=1 NUMEXPR_NUM_THREADS=1
export PYTHONDONTWRITEBYTECODE=1 RUS3_DIAGNOSTIC=1
export WS58_MANIFEST_PATH=${WS58_MANIFEST_PATH:-$D/READY-DRAFT.json}
export WS58_QUALIFIER_PATH=${WS58_QUALIFIER_PATH:-$QUALIFIER}
export FILLER_RL=/workspace/repos/epyc-orchestrator/scripts/region-lock
complete_cmd='if [[ "${WS58_QUAL:-0}" == 1 ]]; then test -s "${FILLER_RESULTS_DIR:?}/normal.json"; else test -s /mnt/raid0/llm/tmp/codex-ni-kpf18-cpu-repair-20261101/r11/COMPLETE.json; fi'
job_cmd='exec taskset -c "$FILLER_CPUS" /usr/bin/python3 -B -I /mnt/raid0/llm/tmp/codex-ni-kpf18-cpu-repair-20261101/r11/job.py'
exec /bin/bash "$ENGINE" --id "$ID" --class cpu --role build \
  --claim-cpus "$WS58_REGIONS" --min-window 3300 \
  --stop "$D/STOP" --workdir "$D" --cmd "$job_cmd" --complete-cmd "$complete_cmd" \
  --requires-tool /usr/bin/python3 --requires-tool /usr/bin/taskset --qual-interpreter /usr/bin/python3
