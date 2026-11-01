#!/bin/bash
set -euo pipefail
D=/mnt/raid0/llm/tmp/codex-ni-s18-qwenvl-cpu-r2-20261101
ID=codex-ni-s18-qwenvl-cpu-r2-20261101
cd "$D"
if [[ ${1:-} == --job ]]; then
    [[ $# == 1 ]]
    : "${FILLER_CPUS:?keeper CPU affinity missing}"
    export THREADS=48 OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1
    if [[ ${FILLER_DRYRUN:-0} == 1 ]]; then
        launcher_sha=$(sha256sum "$D/run_full.r2.v15.sh" | awk '{print $1}')
        mkdir -p "$D/attempts"
        attempt_dir=$(mktemp -d "$D/attempts/dryrun-${launcher_sha}.XXXXXXXX")
        output_dir="${attempt_dir#"$D"/}"
    else
        output_dir=attempts/production
    fi
    exec taskset -c "$FILLER_CPUS" python3 -B "$D/s18_job.py" --mode full --output-dir "$output_dir" --seconds "${WINDOW_SECONDS:-86400}" --max-tokens 512 --port 19930
fi
if [[ ${1:-} == --complete ]]; then
    exec python3 -B "$D/check_complete.py"
fi
if [[ ${1:-} == --smoke-normal || ${1:-} == --smoke-cutoff ]]; then
    mode=${1#--smoke-}
    export THREADS=2 OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1
    port=19933; [[ $mode == normal ]] || port=19934
    exec taskset -c 96-97 python3 -B "$D/launch_bridge.py" --id "$ID-$mode" --max-wall-s 300 -- python3 -B "$D/s18_job.py" --mode smoke --control "$mode" --output-dir "attempts/smoke-r2-$mode" --seconds 295 --port "$port"
fi
[[ $# == 0 ]] || exit 64
: "${WS58_REGIONS:?keeper regions missing}"
[[ $WS58_REGIONS == 0-47,96-143 ]] || { echo 'S18 source requires NUMA_HALF_A 48 cores + SMT'; exit 70; }
export RUS3_DIAGNOSTIC=1
export FILLER_FLAGS_DIR=/mnt/raid0/llm/tmp/compute-flags
export FILLER_GRANTS_DIR=/mnt/raid0/llm/tmp/compute-flags/grants
export FILLERS_MD=/mnt/raid0/llm/tmp/compute-flags/FILLERS.md
export FILLER_STATE_DIR="$D/state/$ID"
exec /mnt/raid0/llm/tmp/compute-flags/bin/rowflow/filler_run15.sh --id "$ID" --class cpu --role build --gpu-quiet none --claim-cpus "${WS58_REGIONS}" --min-window 1800 --stop "$D/STOP-$ID" --workdir "$D" --port 19930 --cmd "python3 -B $D/launch_bridge.py --id $ID --max-wall-s 172800 -- /bin/bash $D/run_full.r2.v15.sh --job" --complete-cmd "/bin/bash $D/run_full.r2.v15.sh --complete"
