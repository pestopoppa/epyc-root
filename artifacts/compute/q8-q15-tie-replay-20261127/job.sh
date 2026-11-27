#!/bin/bash
set -euo pipefail
D=/mnt/raid0/llm/tmp/q8-q15-tie-replay-20261127
STORE=/mnt/raid0/llm/kernels/builds/cpu-20260921-ffc1bac82
MODEL=/mnt/raid0/llm/models/Qwen_Qwen3-0.6B-Q8_0.gguf
export LD_LIBRARY_PATH="$STORE/bin"
export HIP_VISIBLE_DEVICES=-1 ROCR_VISIBLE_DEVICES=-1 CUDA_VISIBLE_DEVICES=-1 GGML_IQK=1
export OMP_WAIT_POLICY=PASSIVE OMP_DYNAMIC=FALSE
unset OMP_PROC_BIND OMP_PLACES GOMP_CPU_AFFINITY
cd "$D"
mode=run
target="$D/out"
if [[ "${FILLER_SMOKE:-0}" == 1 ]]; then
    mode=smoke
    target="$D/out-smoke"
fi
export Q15_PHYSICAL_CPUS
Q15_PHYSICAL_CPUS=$(python3 -I -c '
import os
cpus = set()
for item in os.environ["FILLER_CPUS"].split(","):
    bounds = [int(i) for i in item.split("-")]
    cpus.update(range(bounds[0], bounds[-1] + 1))
cpus &= os.sched_getaffinity(0)
if os.getenv("FILLER_SMOKE") != "1":
    cpus = {cpu for cpu in cpus if cpu < 96}
    if len(cpus) != 24:
        raise SystemExit(f"expected 24 granted physical CPUs, got {sorted(cpus)}")
print(",".join(str(cpu) for cpu in sorted(cpus)))
')
if [[ "${Q15_JOB_PINNED:-0}" != 1 ]]; then
    exec taskset -c "$Q15_PHYSICAL_CPUS" env Q15_JOB_PINNED=1 /bin/bash "$0"
fi
mkdir -p "$target"
sha256sum --check --status SOURCE.sha256
(
    cd "$STORE"
    rg '^\S+  bin/(libggml(-cpu|-base)?\.so\.|libllama\.so\.)' SHA256SUMS |
        sha256sum --check
) > "$target/store-check.txt"
/workspace/repos/epyc-inference-research/scripts/utils/verify_ggml_linkage.sh "$D/replay" "$STORE" > "$target/linkage.txt"
printf '%s\n' "$Q15_PHYSICAL_CPUS" > "$target/physical-cpus.txt"
if taskset -c "$Q15_PHYSICAL_CPUS" "$D/replay" "$mode" "$MODEL" "$D/prompts.txt" "$target" > "$target/replay.log" 2>&1; then
    tail -n 7 "$target/replay.log"
else
    tail -n 60 "$target/replay.log" >&2
    exit 1
fi
if [[ "$mode" == smoke ]]; then
    [[ -s "$target/head-t1.f32" ]]
    [[ -s "$target/signed-pairs.csv" ]]
    printf '{"ok":true, "native_capture":true, "signed_pair_oracle":true}\n' > "$target/SMOKE.json"
else
    taskset -c "$Q15_PHYSICAL_CPUS" python3 -I "$D/analyze.py" "$target" --model "$MODEL"
fi
