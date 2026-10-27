#!/bin/bash
set -euo pipefail
B=/mnt/raid0/llm/tmp/codex-ni-20261027-ufh12-gs-rehearsal/wiring
FACET=${1:?facet}; [[ "$FACET" == tokens || "$FACET" == scores ]] || exit 64
R=$(/usr/bin/python3 -B "$B/enrollment.py" "$B/INSTALL-RECEIPT.json" "$B/SOURCE.sha256") || exit 70
if [[ ${FILLER_PREFLIGHT:-0} == 1 ]]; then
  sha256sum --quiet -c "$B/SOURCE.sha256"
  /usr/bin/python3 -B "$B/deps/dryrun_check.py" boundary --job "$B/job.sh" --effect owned-eg2-bge-server-start
  exit 0
fi
[[ -n ${FILLER_CPUS:-} && -n ${FILLER_ID:-} ]] || exit 70
sha256sum --quiet -c "$B/SOURCE.sha256"
if [[ -z ${GS_FIXTURE_ROOT:-} ]]; then
 [[ ${FILLER_ID} == "ufh12-gs-$FACET-20261027" && ${FILLER_CPUS} == 24-47 && -f "$B/REVIEWED.sha256" ]] || exit 70
 ! compgen -G '/mnt/raid0/llm/tmp/compute-flags/HOLD_*' >/dev/null || exit 70
 grant="/mnt/raid0/llm/tmp/compute-flags/grants/$FILLER_ID.grant"
 [[ -f "$grant" ]] && grep -Eq '^regions=24-47 start=[^ ]+ end=[^ ]+$' "$grant" || exit 70
 [[ $(awk '/Cpus_allowed_list/ {print $2}' /proc/self/status) == "$FILLER_CPUS" ]] || exit 70
 grep -Fx "$(sha256sum "$B/SOURCE.sha256")" "$B/REVIEWED.sha256" >/dev/null || exit 70
 sha256sum --quiet -c "$B/REVIEWED.sha256"
else
 [[ "$FILLER_ID" == ufh12-gs-fixture ]] || exit 70
 case "$(realpath "$GS_FIXTURE_ROOT")/" in "$B/test-run/tmp/"*) ;; *) exit 70;; esac
fi
exec 8>"$B/facets-serialization.lock"
flock -n 8 || { echo 'other G-S facet holds shared ports or results' >&2; exit 75; }
PY=/mnt/raid0/llm/epyc-orchestrator/.venv/bin/python
H=/mnt/raid0/llm/tmp/repl-emb-211-20261024
BIN="$H/llama-src/build-cpu/bin/llama-server"; LIB="${BIN%/*}"
EG="$H/gguf/embeddinggemma-2-BF16.gguf"; BG=/mnt/raid0/llm/models/bge-large-en-v1.5-f16.gguf
COPY=/mnt/raid0/llm/tmp/cal-1025/ufh12-reqb/copy
TOOL=/mnt/raid0/llm/worktrees/orch-ufh12-reqb-5c9875330/scripts/migration/reembed_stores_eg2.py
LINK=/mnt/raid0/llm/epyc-inference-research/scripts/utils/verify_ggml_linkage.sh
OUT="$B/results"; mkdir -p "$OUT" "$B/tranches"
if [[ -n ${GS_FIXTURE_ROOT:-} ]]; then
 BIN="$GS_FIXTURE_ROOT/server"; LIB="$GS_FIXTURE_ROOT"; EG="$GS_FIXTURE_ROOT/eg.gguf"; BG="$GS_FIXTURE_ROOT/bg.gguf"; COPY="$GS_FIXTURE_ROOT/copy"; TOOL="$GS_FIXTURE_ROOT/fixture.py"; LINK="$GS_FIXTURE_ROOT/link.sh"; OUT="$GS_FIXTURE_ROOT/results"
else
 [[ $(sha256sum "$EG" | cut -d' ' -f1) == 68bae29d62fb8c7d23e98d21fd4662753ddd636e6b62b8a70dfe059a9844f216 ]] || exit 70
 [[ $(sha256sum "$BG" | cut -d' ' -f1) == 3379a0e9cea28fc6d7136df8ea7a88ef99ccce5963b9a6f7af9609997be762e3 ]] || exit 70
 [[ $(sha256sum "$BIN" | cut -d' ' -f1) == a2e62037e37ff0391017bd68fec421f271f94c2dfb1df3e767ff45abeeb4c01b ]] || exit 70
 sha256sum --quiet -c "$B/LIBS.sha256"
fi
for port in 19111 19112; do if (echo >/dev/tcp/127.0.0.1/$port) 2>/dev/null; then echo "occupied port $port" >&2; exit 70; fi; done
T=$(mktemp -d "$B/tranches/tranche.XXXXXXXX"); pids=()
cleanup() {
 local bad=0
 for pid in "${pids[@]}"; do if kill -0 "$pid" 2>/dev/null; then kill "$pid" 2>/dev/null || :; fi; done
 for pid in "${pids[@]}"; do
  for _ in 1 2 3 4 5; do kill -0 "$pid" 2>/dev/null || break; [[ $(awk '/^State:/ {print $2}' "/proc/$pid/status" 2>/dev/null) != Z ]] || break; sleep 1; done
  if kill -0 "$pid" 2>/dev/null; then kill -KILL "$pid" 2>/dev/null || :; fi
  wait "$pid" 2>/dev/null || :
  if kill -0 "$pid" 2>/dev/null; then echo "owned process $pid survived" >&2; bad=1; fi
 done
 if [[ -n ${GS_FIXTURE_ROOT:-} && ${GS_FIXTURE_FAIL_CLEANUP:-0} == 1 ]]; then bad=1; fi
 return "$bad"
}
trap cleanup EXIT
export LD_LIBRARY_PATH="$LIB" OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1
bash "$LINK" "$BIN" "$LIB" > "$T/linkage.log"
ARGS=(--copy "$COPY" --tool "$TOOL" --out "$OUT" --bge-model "$BG" --eg2-model "$EG" --server-bin "$BIN")
"$PY" "$B/diagnostic.py" prepare "${ARGS[@]}"
if [[ -z ${GS_FIXTURE_ROOT:-} ]]; then "$PY" - "$OUT/manifest.json" <<'PY'
import json,sys
m=json.load(open(sys.argv[1]))
assert m['counts']=={'episodic':64514,'strategy':1428}
assert sum(map(len,m['selection'].values()))==500
PY
fi
taskset -c "$FILLER_CPUS" "$BIN" -m "$EG" --host 127.0.0.1 --port 19111 -np 1 -c 2048 -t 4 --embeddings --pooling mean -b 2048 -ub 2048 --embd-normalize 2 --no-mmap >"$T/eg2.log" 2>&1 & pids+=("$!")
[[ -z ${FILLER_PIDFILE:-} ]] || printf '%s\n' "${pids[-1]}" >> "$FILLER_PIDFILE"
if [[ "$FACET" == scores ]]; then
 taskset -c "$FILLER_CPUS" "$BIN" -m "$BG" --host 127.0.0.1 --port 19112 -np 1 -c 512 -t 4 --embeddings --pooling cls --embd-normalize 2 --no-mmap >"$T/bge.log" 2>&1 & pids+=("$!")
 [[ -z ${FILLER_PIDFILE:-} ]] || printf '%s\n' "${pids[-1]}" >> "$FILLER_PIDFILE"
fi
for ix in "${!pids[@]}"; do
 port=19111; model="$EG"; if [[ "$ix" == 1 ]]; then port=19112; model="$BG"; fi
 ready=0
 for _ in {1..120}; do
  kill -0 "${pids[$ix]}" 2>/dev/null || exit 70
  if curl -fsS "http://127.0.0.1:$port/health" >/dev/null && ss -ltnp "sport = :$port" | grep -F "pid=${pids[$ix]}," >/dev/null; then ready=1; break; fi
  sleep 1
 done
 [[ $ready == 1 ]] || exit 70
 curl -fsS "http://127.0.0.1:$port/v1/models" > "$T/model-$port.json"
 grep -F "${model##*/}" "$T/model-$port.json" >/dev/null || exit 70
 ps -o pid=,lstart=,args= -p "${pids[$ix]}" > "$T/process-$port.txt"
 { sed 's/^.*) //' "/proc/${pids[$ix]}/stat" | awk '{print "start_ticks=" $20}'; awk '/^Cpus_allowed_list:/ {print}' "/proc/${pids[$ix]}/status"; } >> "$T/process-$port.txt"
 [[ $(awk '/^Cpus_allowed_list:/ {print $2}' "/proc/${pids[$ix]}/status") == "$FILLER_CPUS" ]] || exit 70
 cp "/proc/${pids[$ix]}/maps" "$T/maps-$port.txt"
 if [[ -z ${GS_FIXTURE_ROOT:-} ]]; then
  if grep -E 'lib(ggml|llama)' "$T/maps-$port.txt" | grep -vF "$LIB/"; then exit 70; fi
  grep -F "$LIB/libggml-base" "$T/maps-$port.txt" >/dev/null || exit 70
  awk '/lib(ggml|llama)/ {print $NF}' "$T/maps-$port.txt" | sort -u | while IFS= read -r lib; do
   canonical=$(readlink -f "$lib"); line=$(sha256sum "$canonical")
   grep -Fx "$line" "$B/LIBS.sha256" >/dev/null || exit 70
   printf '%s\n' "$line"
  done > "$T/mapped-libs-$port.sha256"
  sha256sum --quiet -c "$T/mapped-libs-$port.sha256"
 fi
done
"$PY" - "$T" "$FILLER_ID" "$FILLER_CPUS" "$FACET" "$EG" <<'PY'
import json,sys,datetime,hashlib,pathlib
p=pathlib.Path(sys.argv[1]); files={str(x.resolve()):hashlib.sha256(x.read_bytes()).hexdigest() for x in p.iterdir() if x.is_file() and (x.name=='linkage.log' or x.name.startswith(('maps-','model-','process-','mapped-libs-')))}
model=pathlib.Path(sys.argv[5]).resolve()
h=hashlib.sha256()
with model.open('rb') as f:
 for block in iter(lambda:f.read(1024*1024),b''): h.update(block)
(p/'context.json').write_text(json.dumps({'region_lock_claim':sys.argv[2], 'cpu_list':sys.argv[3], 'facet':sys.argv[4], 'started_at':datetime.datetime.now(datetime.timezone.utc).isoformat(), 'server_proof':files, 'synthetic':bool(__import__('os').environ.get('GS_FIXTURE_ROOT')), 'model_path':str(model),'model_sha256':h.hexdigest()},sort_keys=True))
PY
set +e
budget=$(( ${FILLER_DEADLINE:?} - $(date -u +%s) - 90 ))
((budget>0)) || exit 75
((budget<=900)) || budget=900
"$PY" "$B/diagnostic.py" "$FACET" "${ARGS[@]}" --eg2-url http://127.0.0.1:19111 --bge-url http://127.0.0.1:19112 --context "$T/context.json" --budget-seconds "$budget" >"$T/diagnostic.log" 2>&1
rc=$?
"$PY" "$R/scripts/vidya/producers/ufh12_gs_capture.py" --out "$OUT" --facet "$FACET" --context "$T/context.json" >"$T/capture.log" 2>&1
crc=$?
set -e
printf 'diagnostic_rc=%s capture_rc=%s\n' "$rc" "$crc" > "$T/status"
[[ $crc == 0 ]] || exit "$crc"
if ! cleanup; then echo 'owned process cleanup failed' >&2; exit 71; fi
trap - EXIT
if [[ $rc == 0 && -z ${GS_FIXTURE_ROOT:-} ]]; then printf '%s\n' "capture=$(cat "$T/capture.log")" > "$B/COMPLETE.$FACET"; fi
exit "$rc"
