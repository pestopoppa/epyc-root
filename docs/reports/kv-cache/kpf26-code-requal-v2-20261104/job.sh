#!/bin/bash
set -euo pipefail
D=/mnt/raid0/llm/tmp/kv-prefix-fork/kpf26-code-requal-v2-20261104
ORCH=/mnt/raid0/llm/tmp/kv-prefix-fork/kpf26-api-belief-orch
MODEL=/mnt/raid0/llm/models/Qwen3.6-35B-A3B-MTP-Q8_0.gguf
arm=${1:?arm}; case "$arm" in off) PORT=18978; API=18078; FLAGS=0;; on) PORT=18979; API=18079; FLAGS=1;; *) exit 2;; esac
: "${FILLER_ID:?}" "${FILLER_CPUS:?}" "${FILLER_END:?}" "${FILLER_DEADLINE:?}" "${FILLER_STOPFILE:?}"
server_pid= api_pid=
cleanup(){ for p in "$api_pid" "$server_pid"; do if [[ -n "$p" ]] && kill -0 "$p" 2>/dev/null; then kill -TERM "$p" 2>/dev/null || :; for _ in {1..30}; do kill -0 "$p" 2>/dev/null || break; sleep 1; done; if kill -0 "$p" 2>/dev/null; then kill -KILL "$p" 2>/dev/null || :; fi; wait "$p" 2>/dev/null || :; fi; done; }
trap cleanup EXIT INT TERM
# Fail closed on source, retained ELF contents, and library-tree identity before spawn.
EXPECTED_ORCH_COMMIT=868275acb64ef3d490ecac6952518ae187fe74d3
[[ "$(git -C "$ORCH" rev-parse HEAD)" == "$EXPECTED_ORCH_COMMIT" ]] || { echo "KPF26 source pin mismatch" >&2; exit 2; }
[[ -z "$(git -C "$ORCH" status --porcelain --untracked-files=normal)" ]] || { echo "KPF26 source dirty" >&2; exit 2; }
/usr/bin/python3 "$D/verify_elf_manifest.py" --bin "$D/bin" --manifest "$D/BINARIES.sha256" --closure "$D/LINKAGE-CLOSURE.json"
LD_LIBRARY_PATH="$D/bin" bash /mnt/raid0/llm/epyc-inference-research/scripts/utils/verify_ggml_linkage.sh "$D/bin/llama-server" "$D/bin"
run=$(mktemp -d "$D/${arm}.XXXXXX"); mkdir -m 700 "$run/trace" "$run/slots"
cd "$ORCH"
LD_LIBRARY_PATH="$D/bin" taskset -c "$FILLER_CPUS" "$D/bin/llama-server" -m "$MODEL" --host 127.0.0.1 --port "$PORT" -np 4 -c 98304 -t 8 -tb 8 -ub 2048 --flash-attn on --jinja -ctk q8_0 -ctv q8_0 --no-mmap --cache-ram 0 --chat-template-file /mnt/raid0/llm/models/chat-templates/epyc-qwen3x-v1-terse.jinja --spec-type draft-mtp --spec-draft-n-max 4 --reasoning off --device none --device-draft none --kv-unified --no-cache-idle-slots --slot-fork-min-tokens 1024 --metrics --slot-save-path "$run/slots" >"$run/server.log" 2>&1 & server_pid=$!
printf "%s\n" "$server_pid" >> "${FILLER_PIDFILE:?}"
for _ in {1..180}; do kill -0 "$server_pid" 2>/dev/null || exit 1; curl -fsS --max-time 2 "http://127.0.0.1:$PORT/health" >/dev/null 2>&1 && break; [[ ! -e "$FILLER_STOPFILE" ]] || exit 75; sleep 1; done
curl -fsS --max-time 3 "http://127.0.0.1:$PORT/health" >/dev/null
if [[ "${FILLER_SMOKE:-0}" == 1 ]]; then
  /usr/bin/python3 "$D/native_smoke.py" --pid "$server_pid" --port "$PORT" --arm "$arm" --out "${FILLER_DRYRUN_RESULT_PATH:?}"
  exit 75
fi
PY=/workspace/repos/epyc-orchestrator/.venv/bin/python
"$PY" scripts/trace/kpf26_prepare_smoke.py --output "$run/packet" --server-pid "$server_pid" --url "http://127.0.0.1:$PORT" --role frontdoor --model "$MODEL" --grant-id "$FILLER_ID"
# Preserve the actual fixture and scorer, but use the same pinned long-root scope in each arm.
"$PY" "$D/rebind_packet.py" "$run/packet" "$PORT"
RID=$("$PY" -c 'import json,sys; print(json.load(open(sys.argv[1]))["request_id"])' "$run/packet/api-request.json")
env PYTHONPATH="$ORCH" PRIVATE_PORT="$PORT" PRIVATE_API="$API" ORCHESTRATOR_SERVER_URLS_FRONTDOOR="http://127.0.0.1:$PORT" ORCHESTRATOR_CROSS_ROLE_DISJOINT_PLACEMENT=1 ORCHESTRATOR_PREFIX_INDEX="$FLAGS" ORCHESTRATOR_PREFIX_INDEX_FORK="$FLAGS" ORCHESTRATOR_PREFIX_INDEX_LPM="$FLAGS" ORCHESTRATOR_PREFIX_INDEX_LPM_MAX_SKIPS=1 ORCHESTRATOR_PREFIX_INDEX_TRUNK_MIN_TOKENS=1024 ORCHESTRATOR_KPF26_TRACE_REQUEST_ID="$RID" ORCHESTRATOR_KPF26_TRACE_DIR="$run/trace" taskset -c "$FILLER_CPUS" "$PY" "$D/private_api.py" src.api:app >"$run/api.log" 2>&1 & api_pid=$!
printf "%s\n" "$api_pid" >> "${FILLER_PIDFILE:?}"
for _ in {1..90}; do kill -0 "$api_pid" 2>/dev/null || exit 1; curl -fsS --max-time 2 "http://127.0.0.1:$API/health" >/dev/null 2>&1 && break; [[ ! -e "$FILLER_STOPFILE" ]] || exit 75; sleep 1; done
curl -fsS --max-time 3 "http://127.0.0.1:$API/health" >/dev/null
"$PY" scripts/trace/kpf26_api_smoke.py --packet "$run/packet" --api-url "http://127.0.0.1:$API" --api-pid "$api_pid" --trace-dir "$run/trace" --output "$run/result"
"$PY" - "$run" "$D" "$arm" <<'PY'
import json,sys,os
from pathlib import Path
run,d,arm=map(Path,sys.argv[1:]); row={'arm':str(arm),'result':str(run/'result/result.json'),'belief':str(run/'result/belief_measurements.jsonl'),'scope':'prospective-real-code-three-scout-diagnostic-not-kpf26-gate'}
with (d/(str(arm)+'-results.jsonl')).open('a') as f:f.write(json.dumps(row)+'\n');f.flush();os.fsync(f.fileno())
PY

if [[ "${FILLER_DRYRUN:-0}" != 1 ]]; then touch "$D/$arm.COMPLETE"; fi
