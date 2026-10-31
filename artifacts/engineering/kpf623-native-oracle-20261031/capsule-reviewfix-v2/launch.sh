#!/bin/bash
set -euo pipefail
D=/mnt/raid0/llm/tmp/codex-ni-next-ranked-cpu-ready-20261031
ID=codex-ni-kpf623-native-oracle-r1-20261031
cd "$D"
case "${1:-}" in
--smoke|--cutoff)
 [[ $# == 1 ]]
 export FILLER_CPUS=${FILLER_CPUS:-128,129} OMP_NUM_THREADS=1
 exec taskset -c "$FILLER_CPUS" /usr/bin/python3 -B "$D/runtime.py" --mode "${1#--}"
 ;;
--job)
 [[ $# == 1 ]]
 exec taskset -c "${FILLER_CPUS:?}" /usr/bin/python3 -B "$D/runtime.py" --mode full
 ;;
esac
[[ $# == 0 ]]
/usr/bin/python3 -B "$D/runtime.py" --check-enrolled
[[ ${WS58_REGIONS:-} =~ ^[0-9]+(-[0-9]+)?(,[0-9]+(-[0-9]+)?)*$ ]]
exec /usr/bin/env -i PATH=/usr/bin:/bin HOME=/nonexistent OMP_NUM_THREADS=1 RUS3_DIAGNOSTIC=1 WS58_REGIONS="$WS58_REGIONS" \
 FILLER_FLAGS_DIR=/mnt/raid0/llm/tmp/compute-flags FILLER_GRANTS_DIR=/mnt/raid0/llm/tmp/compute-flags/grants \
 FILLERS_MD=/mnt/raid0/llm/tmp/compute-flags/FILLERS.md FILLER_STATE_DIR="$D/state" \
 FILLER_RL=/workspace/repos/epyc-orchestrator/scripts/region-lock \
 /usr/bin/python3 -B "$D/launch_bridge.py" --id "$ID" --max-wall-s 12600 -- /bin/bash "$D/engine/filler_run13.sh" \
 --id "$ID" --class cpu --claim-cpus "$WS58_REGIONS" --role build --gpu-quiet none --min-window 600 \
 --stop "$D/STOP" --workdir "$D" --cmd "/bin/bash $D/launch.sh --job" --complete-cmd "/usr/bin/python3 -B $D/runtime.py --complete"
