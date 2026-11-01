#!/bin/bash
set -euo pipefail
D=/mnt/raid0/llm/tmp/codex-ni-v2-ch27-20261101
ID=codex-ni-ch27-c5-raw-recalibration-v2-20261101
FLAGS=/mnt/raid0/llm/tmp/compute-flags
ENGINE=/mnt/raid0/llm/tmp/compute-flags/bin/qual-v1/filler_run14.sh
QUALIFIER=/mnt/raid0/llm/tmp/compute-flags/bin/qual-v1/qualify_launcher.py
[[ -x "$ENGINE" && -f "$QUALIFIER" ]] || { echo 'REFUSED: canonical v14 bundle absent' >&2; exit 70; }
WS58_MANIFEST_PATH=${WS58_MANIFEST_PATH:-$FLAGS/ready/$ID.json}
WS58_QUALIFIER_PATH=${WS58_QUALIFIER_PATH:-$QUALIFIER}
if [[ "${WS58_FINGERPRINT_ONLY:-0}" == 1 && -z "${WS58_REGIONS:-}" ]]; then
  WS58_REGIONS=0-95
fi
[[ -n "${WS58_REGIONS:-}" ]] || { echo 'REFUSED: keeper did not set WS58_REGIONS' >&2; exit 70; }
if [[ "${WS58_FINGERPRINT_ONLY:-0}" != 1 && "${WS58_QUAL:-0}" != 1 ]]; then
  exec >> "$D/ws58-launcher.out" 2>&1
fi
if [[ "${WS58_QUAL:-0}" == 1 ]]; then
  # Keeper qualification is an R11 two-SMT placement of the exact 48-thread
  # recipe; the request itself and server thread count remain production-shaped.
  GPU_QUIET=none
  CLAIM_CPUS=${WS58_QUAL_CPUS:?keeper qualification CPU pair missing}
else
  GPU_QUIET=exclusive
  CLAIM_CPUS=$WS58_REGIONS
fi
env_args=(
  PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin
  HOME=/home/node LANG=C LC_ALL=C OMP_NUM_THREADS=1 PYTHONDONTWRITEBYTECODE=1
  FILLER_RL=/workspace/repos/epyc-orchestrator/scripts/region-lock
  EPYC_ROOT_REPO=/workspace EPYC_SOURCE_CLOSURE_MANIFEST=$D/RESEARCH-SOURCE-CLOSURE.json
  EPYC_SOURCE_IDENTITY=$D/research-source/SOURCE-COMMIT.json
  PYTHONPATH=$D/research-source:$D/research-source/scripts/kernel_rnd:/mnt/raid0/llm/epyc-orchestrator
  FILLER_FLAGS_DIR=$FLAGS FILLER_GRANTS_DIR=${FILLER_GRANTS_DIR:-$FLAGS/grants}
  FILLERS_MD=$FLAGS/FILLERS.md FILLER_POLL=45
  WS58_MANIFEST_PATH=$WS58_MANIFEST_PATH WS58_QUALIFIER_PATH=$WS58_QUALIFIER_PATH
)
# Preserve a keeper-provided nonce-bound state directory verbatim; never invent or redirect it.
if [[ -n "${FILLER_STATE_DIR:-}" ]]; then env_args+=("FILLER_STATE_DIR=$FILLER_STATE_DIR"); fi
while IFS= read -r key; do
  [[ "$key" == WS58_* ]] || continue
  [[ "$key" == WS58_MANIFEST_PATH || "$key" == WS58_QUALIFIER_PATH ]] && continue
  env_args+=("$key=${!key}")
done < <(compgen -e)
complete_cmd='if [[ "${WS58_QUAL:-0}" == 1 ]]; then test -s "${FILLER_RESULTS_DIR:?}/${FILLER_QUAL_PHASE:?}.json"; else test -s /mnt/raid0/llm/tmp/codex-ni-v2-ch27-20261101/COMPLETE.json; fi'
job_cmd='exec taskset -c "$FILLER_CPUS" /bin/bash /mnt/raid0/llm/tmp/codex-ni-v2-ch27-20261101/job.sh'
exec /usr/bin/env -i "${env_args[@]}" /bin/bash "$ENGINE" \
  --id "$ID" --class cpu --role bench --self-claim \
  --gpu-quiet "$GPU_QUIET" --claim-cpus "$CLAIM_CPUS" \
  --min-window 5400 --stop "$D/STOP" --workdir "$D" \
  --port 18651 --requires-tool /usr/bin/python3 --requires-tool /usr/bin/taskset \
  --requires-tool /usr/bin/numactl --requires-tool /usr/bin/curl --requires-tool /usr/bin/ss \
  --qual-interpreter /usr/bin/python3 --cmd "$job_cmd" \
  --complete-cmd "$complete_cmd"
