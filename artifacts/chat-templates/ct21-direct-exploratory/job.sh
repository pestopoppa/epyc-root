#!/bin/bash
set -euo pipefail
D=/mnt/raid0/llm/tmp/codex-ni-20261027-ct21-cause-audit
OLD=/mnt/raid0/llm/tmp/refactor-01a16fc3/ct21-parse-outcome-unblock-20261027
BUILD=/mnt/raid0/llm/kernels/builds/gpu-20261020-dd3d9721c
ENGINE=/mnt/raid0/llm/tmp/refactor-01a16fc3/compute-coordination-20261026/launch-contract-85c442b3d/dryrun_check.py
MODEL=/mnt/raid0/llm/models/Qwen3.8-27B-Q8_0.gguf
TEMPLATE=/mnt/raid0/llm/models/chat-templates/epyc-qwen3x-v1-terse.jinja
: "${FILLER_DEADLINE:?}" "${FILLER_STOPFILE:?}" "${FILLER_CPUS:?}" "${FILLER_LIB:?}" "${CT21_ENROLLMENT_RECEIPT:?}"
source "$FILLER_LIB"
export LD_LIBRARY_PATH="$BUILD/bin" OMP_NUM_THREADS=1
sha256sum -c "$D/source-manifest.sha256"
sha256sum -c "$OLD/source-manifest.sha256" >/dev/null
python3 "$D/direct_diagnostic.py" --dry-run
bash /workspace/repos/epyc-inference-research/scripts/utils/verify_ggml_linkage.sh "$BUILD/bin/llama-server" "$BUILD"
# Same actual job entry reaches this boundary BEFORE server/model or HTTP.
if [ "${FILLER_PREFLIGHT:-0}" = 1 ]; then
 python3 "$ENGINE" boundary --effect start-server --job "$D/job.sh"
 exit 0
fi
# Runtime identity and enrollment are verified before any side effect.
python3 "$D/prelaunch_check.py" "$CT21_ENROLLMENT_RECEIPT"
export WINDOW_CONFIRMED=1
export CT21_RUNTIME_IDENTITY="$D/runtime-identity.json"
taskset -c "$FILLER_CPUS" "$BUILD/bin/llama-server" -m "$MODEL" --host 127.0.0.1 --port 18822 -np 1 -c 32768 -t 8 -b 512 -ub 512 --flash-attn on --jinja -ctk q8_0 -ctv q8_0 --no-mmap -ngl all --device ROCm0 --chat-template-file "$TEMPLATE" > "$D/server.log" 2>&1 &
pid=$!
sampler= suid= sbirth= uid= birth=
cleanup() {
 if [ -n "$sampler" ]; then
  if [ -n "$suid" ] && [ -n "$sbirth" ]; then python3 "$OLD/process_identity.py" stop "$sampler" "$suid" "$sbirth"; else kill "$sampler" 2>/dev/null || :; fi
  wait "$sampler" 2>/dev/null || :
  if ps -p "$sampler" >/dev/null; then echo 'owned sampler still alive' >&2; return 1; fi
 fi
 if [ -n "$uid" ] && [ -n "$birth" ]; then python3 "$OLD/process_identity.py" stop "$pid" "$uid" "$birth"; else kill "$pid" 2>/dev/null || :; fi
 wait "$pid" 2>/dev/null || :
 if ps -p "$pid" >/dev/null; then echo 'owned server still alive' >&2; return 1; fi
}
trap cleanup EXIT
read -r uid birth < <(python3 "$OLD/process_identity.py" capture "$pid" --parent "$$")
export CT21_SERVER_PID="$pid" CT21_SERVER_UID="$uid" CT21_SERVER_BIRTH="$birth"
fl_wait_own_port 18822 "$pid" 600
bash "$OLD/gpu_evidence.sh" "$pid" "$D/vram-samples.txt" & sampler=$!
read -r suid sbirth < <(python3 "$OLD/process_identity.py" capture "$sampler" --parent "$$")
export CT21_MONITOR_PID="$sampler" CT21_MONITOR_UID="$suid" CT21_MONITOR_BIRTH="$sbirth"
python3 "$D/direct_diagnostic.py" --url http://127.0.0.1:18822 --output "$D/run-exploratory-v1"
