#!/bin/bash
# run_probe.sh <arm: base|fix> — real-model V/VKQ-accumulator probe, CPU only, f16 KV.
# Run under: region-lock run --cpu-list 0-23 --role bench --tag cpu-fa-f16 -- taskset -c 0-23 ./run_probe.sh base
set -euo pipefail
P=/mnt/raid0/llm/tmp/cpu-fa-f16-20261004/probe
ARM=${1:-base}
case $ARM in
    base) LIB=/mnt/raid0/llm/kernels/builds/cpu-20260925-90c12df42/bin ;;
    fix)  LIB=/mnt/raid0/llm/tmp/cpu-fa-f16-20261004/build-cpu/bin ;;
    *) echo "arm?"; exit 2 ;;
esac
O=$P/out-$ARM; mkdir -p "$O"
ARCH=/mnt/raid0/llm/models/unsloth/Qwen3.8-Flash-Next-GGUF/UD-IQ4_XS/Qwen3.8-Flash-Next-UD-IQ4_XS-00001-of-00003.gguf
EMB=/mnt/raid0/llm/models/bge-large-en-v1.5-f16.gguf
DF=/mnt/raid0/llm/tmp/v11-fa-ab-20261004/df29/prompts
run() { env -u LD_LIBRARY_PATH LD_LIBRARY_PATH="$LIB" OMP_WAIT_POLICY=passive nice -n 19 "$P/fa_vkq_probe" "$@" || echo "probe rc=$?"; }
# embedder: one ubatch per input (non-causal); short (one_chunk, n_q<64) and 2k-char (tiled) inputs
run -m "$EMB" -p "$DF/probe_olymp00.txt:512" -p "$DF/probe_short.txt:64" --kv f16 --ngl 0 -t 24 --ctx 512 \
    --feat-layers none --acc-max-q 512 --kv-every 1 --out "$O" --tag emb
# architect_general model: bulk prefill R=512 (tiled), last 20 tokens as 5-row verify-shaped ubatches (one_chunk)
for pr in "$P/code8k.txt" "$P/doc8k.txt" "$DF/probe_long2k_a.txt" "$P/mixed16k.txt"; do
    t=$(basename "$pr" .txt)
    run -m "$ARCH" -p "$pr:512" --kv f16 --ngl 0 -t 24 --ctx 20480 --feat-layers none \
        --tail 20 --tail-R 5 --kv-every 1000 --time-cap 1800 --out "$O" --tag arch_$t
done
grep -h "^SUMMARY\|^FINAL" "$O"/*.summary.txt
