#!/bin/bash
set -euo pipefail
D=$(cd -- "$(dirname -- "$0")" && pwd -P)
IMG='vllm/vllm-openai-rocm@sha256:4fcd39b758b660c4e9c345c021e2ea8f0ccdb31e3c32507d676cc3005ae83fba'
HF=/mnt/raid0/llm/models/Qwen3-4B-Instruct-2507
SMHF=/mnt/raid0/llm/models/Qwen3-0.6B-PAW-smoke-c1899de
B=/mnt/raid0/llm/kernels/builds/gpu-20261030-729599d69-c6/bin
CPUS=${Q38P4_PREP_CPUS:-4-7}
docker run --rm --pull never --network none --cpus 2 --cpuset-cpus "$CPUS" -u "$(id -u):$(id -g)" \
  -e HOME=/tmp -e HF_HUB_OFFLINE=1 -e TOKENIZERS_PARALLELISM=false -e OMP_NUM_THREADS=2 \
  -v "$D:/pkt:ro" -v "$HF:/model:ro" -v "$SMHF:/smoke:ro" \
  --entrypoint python3 "$IMG" /pkt/render_tokens.py > "$D/tokens.json"
LD_LIBRARY_PATH="$B:/opt/rocm/lib" taskset -c "$CPUS" \
  /mnt/raid0/llm/epyc-inference-research/scripts/utils/verify_ggml_linkage.sh "$B/llama-server" "${B%/bin}" \
  > "$D/c6-ggml-linkage.txt" 2>&1
env LD_LIBRARY_PATH="$B:/opt/rocm/lib" taskset -c "$CPUS" "$B/llama-server" --version > "$D/c6-version.txt" 2>&1
taskset -c "$CPUS" nice -n 10 /usr/bin/python3 -B "$D/prepare.py"
