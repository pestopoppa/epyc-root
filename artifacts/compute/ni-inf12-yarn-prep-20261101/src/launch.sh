#!/bin/bash
set -euo pipefail
D=/mnt/raid0/llm/tmp/codex-ni-inf12-yarne1-repair-20261101/yarn-packet-r2
ID=codex-ni-yarn-e1-mem-phase-r2-20261101
ENGINE=/mnt/raid0/llm/tmp/codex-ni-hard-qual-gate-20261101/src/scripts/coordination/filler_run14.sh

if [[ "${1:-}" != --job ]]; then
  MIN_WINDOW_S=$(/mnt/raid0/llm/epyc-orchestrator/.venv/bin/python -I \
    "$D/helper/validate_launch_window.py") || exit $?
fi

case ${1:-} in
  --job)
    if [[ "${WS58_QUAL:-0}" == 1 ]]; then
      MODE=job
    else
      MODE=full
    fi
    exec taskset -c "${FILLER_CPUS:?missing native CPUs}" /mnt/raid0/llm/epyc-orchestrator/.venv/bin/python -B "$D/run.py" "$MODE" --deadline "${FILLER_DEADLINE:?missing native deadline}"
    ;;
  '') ;;
  *) exit 64 ;;
esac

cd "$D"
exec /usr/bin/env -i \
  PATH=/usr/bin:/bin HOME=/home/node \
  LD_LIBRARY_PATH=/opt/rocm/lib:/usr/lib/llvm-20/lib:/opt/AMD/aocc-compiler-5.0.0/lib \
  WS58_QUAL="${WS58_QUAL:-0}" \
  WS58_QUAL_NONCE="${WS58_QUAL_NONCE:-}" \
  WS58_QUAL_CPUS="${WS58_QUAL_CPUS:-}" \
  WS58_QUAL_RESULTS="${WS58_QUAL_RESULTS:-}" \
  WS58_QUAL_FIXTURE="${WS58_QUAL_FIXTURE:-}" \
  WS58_QUAL_PROOF="${WS58_QUAL_PROOF:-}" \
  WS58_QUAL_GPU_HELD="${WS58_QUAL_GPU_HELD:-0}" \
  WS58_QUAL_PRODUCTION="${WS58_QUAL_PRODUCTION:-0}" \
  WS58_QUAL_WINDOW_S="${WS58_QUAL_WINDOW_S:-}" \
  WS58_QUAL_CUTOFF_EVENT="${WS58_QUAL_CUTOFF_EVENT:-}" \
  WS58_MANIFEST_PATH="${WS58_MANIFEST_PATH:-}" \
  WS58_QUALIFIER_PATH="${WS58_QUALIFIER_PATH:-}" \
  WS58_PRODUCTION_RECIPE_SHA256="${WS58_PRODUCTION_RECIPE_SHA256:-}" \
  WS58_REGIONS="${WS58_REGIONS:-}" \
  WS58_FINGERPRINT_ONLY="${WS58_FINGERPRINT_ONLY:-0}" \
  FILLER_FLAGS_DIR=/mnt/raid0/llm/tmp/compute-flags \
  FILLER_GRANTS_DIR="${FILLER_GRANTS_DIR:-/mnt/raid0/llm/tmp/compute-flags/grants}" \
  FILLERS_MD=/mnt/raid0/llm/tmp/compute-flags/FILLERS.md \
  FILLER_STATE_DIR="${FILLER_STATE_DIR:-$D/state}" \
  FILLER_GPU_LOCK="${FILLER_GPU_LOCK:-/mnt/raid0/llm/tmp/gpu_device.mi210_0.lock}" \
  /bin/bash "$ENGINE" \
    --id "$ID" --class gpu --gpu-threads 184-191 --no-fold-siblings \
    --role bench --gpu-quiet exclusive --min-window "$MIN_WINDOW_S" --stop "$D/STOP" \
    --workdir "$D" --port 18437 --requires-tool taskset --requires-tool ss \
    --qual-interpreter /mnt/raid0/llm/epyc-orchestrator/.venv/bin/python \
    --cmd "/bin/bash $D/launch.sh --job" \
    --complete-cmd "/mnt/raid0/llm/epyc-orchestrator/.venv/bin/python -I $D/helper/check_complete.py"
