#!/bin/bash
set -uo pipefail

ROOT=/mnt/raid0/llm/tmp/codex-ni-native-successors-20261101/inf12
SOURCE=/mnt/raid0/llm/tmp/codex-ni-v2-gpu-20261101
BASE=/mnt/raid0/llm/models/Qwen3-4B-Instruct-2507
ADAPTER=/mnt/raid0/llm/models/delta-mem_qwen3_4b-instruct
PY="$ROOT/venv/bin/python"
EVAL="$ROOT/code/deltamem/eval/official_memory_agent_bench.py"
EXT=/mnt/raid0/llm/external_MemoryAgentBench
INTERNAL_MODE=${1:-}
if [[ "$INTERNAL_MODE" == --complete ]]; then
  target="$ROOT/outputs/RESULT.json"
  if [[ "${WS58_QUAL:-0}" == 1 ]]; then target="${FILLER_RESULTS_DIR:?}/${FILLER_QUAL_PHASE:?}/RESULT.json"; fi
  [[ -s "$target" ]] || exit 1
  "$PY" - "$target" <<'PYC'
import json,sys
p=json.load(open(sys.argv[1]));assert p.get('full_gate_completed') is True or p.get('fixture_completed') is True
PYC
  exit $?
fi
if [[ $# -gt 1 || ( -n "$INTERNAL_MODE" && "$INTERNAL_MODE" != --smoke && "$INTERNAL_MODE" != --cutoff-test && "$INTERNAL_MODE" != --cleanup-capture-failure-test && "$INTERNAL_MODE" != --deadline-test && "$INTERNAL_MODE" != --stop-test && "$INTERNAL_MODE" != --entry-context-test ) ]]; then
  echo "job.sh accepts only its private model-free lifecycle fixtures" >&2
  exit 2
fi
OUTROOT="$ROOT/outputs"
if [[ "$INTERNAL_MODE" == --entry-context-test ]]; then OUTROOT="$OUTROOT/entry-context-tests"; fi
if [[ "$INTERNAL_MODE" == --cutoff-test || "$INTERNAL_MODE" == --cleanup-capture-failure-test ]]; then OUTROOT="$OUTROOT/cutoff-tests"; fi
if [[ "$INTERNAL_MODE" == --deadline-test || "$INTERNAL_MODE" == --stop-test ]]; then OUTROOT="$OUTROOT/monitor-tests"; EVAL="$ROOT/deps/fake_eval_sleep.py"; fi
mkdir -p "$OUTROOT"

export PYTHONDONTWRITEBYTECODE=1
export PYTHONPATH="$ROOT/triton36-overlay:$ROOT/code:$EXT${PYTHONPATH:+:$PYTHONPATH}"
export TRITON_CACHE_DIR="$ROOT/triton36-cache"
export HF_HOME="$ROOT/hf-home"
export HF_HUB_CACHE="$ROOT/hub-cache"
export HF_DATASETS_CACHE="$ROOT/datasets-cache"
export NLTK_DATA="$ROOT/nltk_data"
export TIKTOKEN_CACHE_DIR="$ROOT/tiktoken-cache"
export HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 HF_DATASETS_OFFLINE=1
export HF_HUB_DISABLE_XET=1 TOKENIZERS_PARALLELISM=false
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1
export PYTORCH_HIP_ALLOC_CONF=max_split_size_mb:512
# This job has one evaluator process per arm, never torch.distributed peers.
# The recorded cleanup predicate is intentionally direct-child-only.
export WORLD_SIZE=1 RANK=0 LOCAL_RANK=0
unset MASTER_ADDR MASTER_PORT DIST_TIMEOUT_MINUTES
if [[ "$INTERNAL_MODE" != --cutoff-test && "$INTERNAL_MODE" != --cleanup-capture-failure-test && "$INTERNAL_MODE" != --deadline-test && "$INTERNAL_MODE" != --stop-test ]]; then
  [[ "${G2_PIN_FINGERPRINT:-}" =~ ^[0-9a-f]{64}$ ]] || { echo "missing/invalid G2_PIN_FINGERPRINT" >&2; exit 2; }
  cmp "$ROOT/code/MemoryAgentBench/utils/eval_other_utils.py" "$EXT/utils/eval_other_utils.py"
fi
if [[ "$INTERNAL_MODE" == --smoke ]]; then
  export G2_MODE=smoke
elif [[ "$INTERNAL_MODE" != --deadline-test && "$INTERNAL_MODE" != --stop-test ]]; then
  unset G2_MODE || true
fi

check_entry_context() {
  local expected_cpus now end deadline
  if [[ "${G2_MODE:-full}" == smoke ]]; then
    expected_cpus=184-185
    local token=${INF12_SMOKE_LOCK_TOKEN:-} token_file=${INF12_SMOKE_LOCK_FILE:-}
    [[ "$token" =~ ^[a-f0-9]{32}$ && "$token_file" == "$ROOT/launcher-state/.smoke-$token" && -f "$token_file" && ! -L "$token_file" ]] || {
      echo "smoke entry refused: missing launcher-owned GPU-lock handoff" >&2; return 1;
    }
    [[ "$(cat "$token_file")" == "$token" ]] || { echo "smoke entry refused: lock handoff token mismatch" >&2; return 1; }
    [[ ! -e "$ROOT/STOP" ]] || { echo "smoke entry refused: STOP is present" >&2; return 1; }
  else
    [[ "${FILLER_ID:-}" == codex-ni-inf12-gate2-triton36-v3-20261101 || "${WS58_QUAL:-0}" == 1 ]] || { echo "normal entry refused: unexpected/missing FILLER_ID" >&2; return 1; }
    local normal_cpus="${FILLER_CPUS:-}"
    # Test-only relocation lets the normal grant-context gate be exercised on
    # the isolated prep pair. This variable is honored only by the no-model
    # fixture mode and cannot alter smoke or scheduled execution.
    if [[ "$INTERNAL_MODE" == --entry-context-test && "${INF12_TEST_CPU_SCOPE:-}" == 50-51 ]]; then
      normal_cpus=50-51
    fi
    [[ "${FILLER_CPUS:-}" == "$normal_cpus" ]] || { echo "normal entry refused: expected FILLER_CPUS=$normal_cpus" >&2; return 1; }
    if [[ "${WS58_QUAL:-0}" == 1 && "${FILLER_QUAL_PHASE:-}" == cutoff ]]; then
      [[ "${FILLER_STOPFILE:-}" == "$(dirname "${WS58_QUAL_RESULTS:?}")/cutoff.stop" ]] || { echo "cutoff entry refused: wrong nonce-bound STOP" >&2; return 1; }
    else
      [[ "${FILLER_STOPFILE:-}" == "$ROOT/STOP" ]] || { echo "normal entry refused: unexpected/missing FILLER_STOPFILE" >&2; return 1; }
    fi
    [[ "${FILLER_END:-}" =~ ^[0-9]+$ && "${FILLER_DEADLINE:-}" =~ ^[0-9]+$ ]] || { echo "normal entry refused: missing hard end/deadline" >&2; return 1; }
    now=$(date +%s); end=$FILLER_END; deadline=$FILLER_DEADLINE
    (( end > deadline && deadline - now >= 300 )) || { echo "normal entry refused: insufficient valid work deadline" >&2; return 1; }
    [[ ! -e "$FILLER_STOPFILE" ]] || { echo "normal entry refused: STOP is present" >&2; return 1; }
    expected_cpus="$normal_cpus"
  fi
  "$PY" - "$expected_cpus" <<'PY'
import os, sys
expected = {int(x) for part in sys.argv[1].split(',') for x in (range(int(part.split('-')[0]), int(part.split('-')[1])+1) if '-' in part else [part])}
actual = set(os.sched_getaffinity(0))
if actual != expected:
    raise SystemExit(f"affinity mismatch: expected={sorted(expected)} actual={sorted(actual)}")
print("ENTRY_AFFINITY_OK", ",".join(map(str, sorted(actual))))
PY
}

# Private source fixture: execute the exact normal grant-context gate and exit before evaluator setup.
if [[ "$INTERNAL_MODE" == --entry-context-test ]]; then
  check_entry_context || exit 1
  echo "NORMAL_ENTRY_CONTEXT_OK"
  exit 0
fi

mkdir -p "$OUTROOT"
RUN_ID="$(date -u +%Y%m%dT%H%M%SZ)-$$"
RUN_DIR="$OUTROOT/$RUN_ID"
mkdir -p "$RUN_DIR"
if [[ "$INTERNAL_MODE" == --cutoff-test || "$INTERNAL_MODE" == --cleanup-capture-failure-test || "$INTERNAL_MODE" == --deadline-test || "$INTERNAL_MODE" == --stop-test || "${G2_MODE:-full}" == smoke ]]; then
  RESULT_DIR="$RUN_DIR/results"
else
  # A new immutable pin set gets an isolated resume namespace. Re-arms with
  # identical source/model/data manifests continue the same question records.
  RESULT_DIR="$OUTROOT/full-results-$G2_PIN_FINGERPRINT"
  if [[ "${WS58_QUAL:-0}" == 1 ]]; then RESULT_DIR="${FILLER_RESULTS_DIR:?}/${FILLER_QUAL_PHASE:?}"; fi
fi
mkdir -p "$RESULT_DIR"
printf '%s\n' "$RUN_ID" > "$OUTROOT/LAST-RUN"
STATE="$RUN_DIR/STATE.json"
SAMPLES="$RUN_DIR/GPU-SAMPLES.tsv"
LOG="$RUN_DIR/job.log"
PARTIAL=0
WORK_STARTED=false
CHILD_PID=
CHILD_START_TICKS=
LAST_CHILD_PID=
LAST_CHILD_TICKS=
DIRECT_CHILD_REAPED=true
START_WALL=$(date +%s)
START_ISO=$(date -u +%Y-%m-%dT%H:%M:%SZ)
STATE_PHASE=preflight

write_state() {
  local status=$1 rc=$2 state_pid state_ticks
  state_pid=${CHILD_PID:-$LAST_CHILD_PID}
  state_ticks=${CHILD_START_TICKS:-$LAST_CHILD_TICKS}
  "$PY" - "$STATE" "$RUN_ID" "$status" "$rc" "$START_ISO" "$START_WALL" "$DIRECT_CHILD_REAPED" "$state_pid" "$state_ticks" "$STATE_PHASE" "$WORK_STARTED" <<'PY'
import json, os, sys, time
p, rid, status, rc, started, wall0, direct_child_reaped, child_pid, child_ticks, phase, work_started = sys.argv[1:]
if status == "partial" and work_started != "true": status = "resource-wait"
terminal = status in {"complete", "partial", "failed", "resource-wait"}
now = time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())
payload = {"run_id": rid, "status": status, "phase": phase,
           "rc": int(rc) if rc else None, "started_at": started,
           "updated_at": now, "ended_at": now if terminal else None,
           "wall_s": int(time.time())-int(wall0), "partial": status == "partial", "work_started": work_started == "true",
           "direct_child_reaped": direct_child_reaped == "true",
           "cleanup_scope": "direct-child-only",
           "descendants_censused": False,
           "child_pid": int(child_pid) if child_pid else None,
           "child_start_ticks": child_ticks or None}
tmp = p + ".tmp"
with open(tmp, "w", encoding="utf-8") as f:
    json.dump(payload, f, sort_keys=True); f.write("\n"); f.flush(); os.fsync(f.fileno())
os.replace(tmp, p)
fd=os.open(os.path.dirname(p), os.O_RDONLY); os.fsync(fd); os.close(fd)
PY
}

if [[ "$INTERNAL_MODE" != --cutoff-test && "$INTERNAL_MODE" != --cleanup-capture-failure-test && "$INTERNAL_MODE" != --deadline-test && "$INTERNAL_MODE" != --stop-test ]]; then
  if ! "$PY" - "$ROOT" <<'DISKPY' >> "$LOG" 2>&1
import os, sys
v=os.statvfs(sys.argv[1]); free=v.f_bavail*v.f_frsize
print(f"DISK_ADMISSION free_bytes={free} required_bytes={170*1024**3} output_GiB=20 reserve_GiB=150")
if free < 170*1024**3: raise SystemExit(75)
DISKPY
  then write_state resource-wait 75; exit 75; fi
fi
# Apply and validate the pinned HIP allocator setting before model loading.
# This C++ API parses/applies the exact string without initializing CUDA.
"$PY" - <<'PY' >> "$LOG" 2>&1 || { rc=$?; write_state failed "$rc" || true; exit "$rc"; }
import os, torch
setting = os.environ.get("PYTORCH_HIP_ALLOC_CONF", "")
if setting != "max_split_size_mb:512":
    raise SystemExit(f"unexpected HIP allocator setting: {setting!r}")
torch.cuda.memory._set_allocator_settings(setting)
backend = torch.cuda.memory.get_allocator_backend()
if backend != "native":
    raise SystemExit(f"unexpected allocator backend: {backend}")
print(f"HIP_ALLOCATOR_SETTINGS_APPLIED backend={backend} setting={setting} cuda_initialized={torch.cuda.is_initialized()}")
PY

capture_child_identity() {
  local pid=$1 stat tail
  stat=$(cat "/proc/$pid/stat" 2>/dev/null) || return 1
  tail=${stat##*) }
  set -- $tail
  CHILD_START_TICKS=${20}
  LAST_CHILD_PID=$pid
  LAST_CHILD_TICKS=$CHILD_START_TICKS
}

same_captured_child_alive() {
  [[ -n "${CHILD_PID:-}" && -n "${CHILD_START_TICKS:-}" ]] || return 1
  local stat tail state ticks
  stat=$(cat "/proc/$CHILD_PID/stat" 2>/dev/null) || return 1
  tail=${stat##*) }
  set -- $tail
  state=$1; ticks=${20}
  [[ "$ticks" == "$CHILD_START_TICKS" && "$state" != Z && "$state" != X ]]
}

direct_child_alive() {
  local pid=$1 stat tail state
  stat=$(cat "/proc/$pid/stat" 2>/dev/null) || return 1
  tail=${stat##*) }
  set -- $tail
  state=$1
  [[ "$state" != Z && "$state" != X ]]
}

same_captured_child_entry() {
  [[ -n "${CHILD_PID:-}" && -n "${CHILD_START_TICKS:-}" ]] || return 1
  local stat tail ticks
  stat=$(cat "/proc/$CHILD_PID/stat" 2>/dev/null) || return 1
  tail=${stat##*) }
  set -- $tail
  ticks=${20}
  [[ "$ticks" == "$CHILD_START_TICKS" ]]
}

reap_child() {
  local pid=$CHILD_PID rc=0 i
  [[ -n "$pid" ]] || return 0
  DIRECT_CHILD_REAPED=false
  if same_captured_child_alive; then kill -TERM "$pid" 2>/dev/null || true; fi
  if [[ -z "${CHILD_START_TICKS:-}" ]]; then
    # $pid is our unreaped direct child from $!, so its PID cannot be reused
    # until this shell waits for it. This path handles /proc identity-capture
    # failure without losing the only safe child handle.
    kill -TERM "$pid" 2>/dev/null || true
    for i in {1..30}; do direct_child_alive "$pid" || break; sleep 0.1; done
    if direct_child_alive "$pid"; then kill -KILL "$pid" 2>/dev/null || true; fi
    for i in {1..20}; do direct_child_alive "$pid" || break; sleep 0.1; done
    if direct_child_alive "$pid"; then
      echo "CLEANUP_UNVERIFIED_DIRECT_CHILD pid=$pid" >> "$LOG"
      return 1
    fi
    wait "$pid" || rc=$?
    echo "DIRECT_CHILD_REAPED pid=$pid rc=$rc identity_unavailable=true" >> "$LOG"
    CHILD_PID=; CHILD_START_TICKS=; DIRECT_CHILD_REAPED=true
    return 0
  fi
  for i in {1..30}; do same_captured_child_alive || break; sleep 0.1; done
  if same_captured_child_alive; then kill -KILL "$pid" 2>/dev/null || true; fi
  for i in {1..20}; do same_captured_child_alive || break; sleep 0.1; done
  if same_captured_child_alive; then
    echo "CLEANUP_UNVERIFIED pid=$pid start_ticks=$CHILD_START_TICKS" >> "$LOG"
    return 1
  fi
  wait "$pid" || rc=$?
  if same_captured_child_entry; then
    echo "CLEANUP_UNVERIFIED_AFTER_WAIT pid=$pid start_ticks=$CHILD_START_TICKS" >> "$LOG"
    return 1
  fi
  echo "CHILD_REAPED pid=$pid start_ticks=$CHILD_START_TICKS rc=$rc" >> "$LOG"
  CHILD_PID=; CHILD_START_TICKS=; DIRECT_CHILD_REAPED=true
}

on_signal() {
  local sig=$1
  trap - TERM INT HUP
  PARTIAL=1
  echo "signal=$sig at $(date -u +%FT%TZ)" >> "$LOG"
  reap_child || { write_state failed 125 || true; exit 125; }
  write_state partial 75 || true
  exit 75
}
trap 'on_signal TERM' TERM
trap 'on_signal INT' INT
trap 'on_signal HUP' HUP

write_state starting ""
if [[ "$INTERNAL_MODE" != --cutoff-test && "$INTERNAL_MODE" != --cleanup-capture-failure-test && "$INTERNAL_MODE" != --deadline-test && "$INTERNAL_MODE" != --stop-test ]] && ! check_entry_context; then
  write_state failed 70 || true
  exit 70
fi
if [[ "$INTERNAL_MODE" != --cutoff-test && "$INTERNAL_MODE" != --cleanup-capture-failure-test && "$INTERNAL_MODE" != --deadline-test && "$INTERNAL_MODE" != --stop-test ]]; then
  # Verify large immutable inputs only after the poller/grant and effective
  # affinity checks. This keeps the keeper startup path short while ensuring
  # no evaluator/model starts before every pinned input passes.
  STATE_PHASE=validating-pinned-inputs
  write_state running "" || { write_state failed 125 || true; exit 125; }
  if ! ( cd "$ROOT" && sha256sum --check SOURCE-SHA256SUMS MODEL-SHA256SUMS DATA-SHA256SUMS TRITON36-SHA256SUMS ALLOCATOR-SHA256SUMS ) >> "$LOG" 2>&1; then
    echo "REFUSED: model/data/Triton content does not match pinned manifests" >> "$LOG"
    write_state failed 70 || true
    exit 70
  fi
  if ! cmp "$ROOT/code/MemoryAgentBench/utils/eval_other_utils.py" "$EXT/utils/eval_other_utils.py" >> "$LOG" 2>&1; then
    echo "REFUSED: external evaluator helper differs from pinned local helper" >> "$LOG"
    write_state failed 70 || true
    exit 70
  fi
fi

run_eval() {
  local split=$1 source=$2 arm=$3 cap=${4:-0}
  local tag="${split}__${source}__${arm}"
  local json="$RESULT_DIR/${tag}.json" jsonl="$RESULT_DIR/${tag}.jsonl"
  local args=("$PY" "$EVAL" --split "$split" --source "$source"
    --model-path "$BASE" --device cuda:0 --dtype bfloat16 --attn-implementation sdpa
    --eval-batch-size 1 --seed 42 --temperature 0 --local-files-only
    --datasets-cache-dir "$HF_DATASETS_CACHE" --hub-cache-dir "$HF_HUB_CACHE"
    --external-memory-agent-bench-root "$EXT" --output-json "$json" --output-jsonl "$jsonl" --pin-fingerprint "$G2_PIN_FINGERPRINT")
  if [[ "$arm" == delta ]]; then args+=(--delta-adapter-dir "$ADAPTER"); fi
  if [[ $cap -gt 0 ]]; then args+=(--max-test-samples 1 --smoke-question-count "$cap"); fi
  if [[ "${G2_MODE:-full}" != smoke ]]; then
    [[ ! -e "$FILLER_STOPFILE" ]] || { echo "STOP before task: $tag" >> "$LOG"; return 75; }
    (( $(date +%s) < FILLER_DEADLINE )) || { echo "deadline before task: $tag" >> "$LOG"; return 75; }
  fi

  echo "START $tag $(date -u +%FT%TZ)" | tee -a "$LOG"
  STATE_PHASE="starting:$tag"
  local event_path="$RUN_DIR/native-events/$tag.json" ack_path="$RUN_DIR/native-events/$tag.ack"
  G2_GPU_SAMPLES="$SAMPLES" G2_RUN_TAG="$tag" G2_NATIVE_EVENT_PATH="$(if [[ "${WS58_QUAL:-0}" == 1 ]]; then echo "$event_path"; fi)" G2_NATIVE_EVENT_ACK="$(if [[ "${WS58_QUAL:-0}" == 1 ]]; then echo "$ack_path"; fi)" "${args[@]}" >> "$LOG" 2>&1 &
  CHILD_PID=$!
  WORK_STARTED=true
  DIRECT_CHILD_REAPED=false
  if ! capture_child_identity "$CHILD_PID"; then
    echo "CHILD_IDENTITY_UNAVAILABLE pid=$CHILD_PID" >> "$LOG"
    STATE_PHASE="running-identity-unavailable:$tag"
    write_state running "" || true
    reap_child || return 125
    return 125
  fi
  local child_start=$CHILD_START_TICKS
  echo "CHILD_STARTED pid=$CHILD_PID start_ticks=$child_start" >> "$LOG"
  STATE_PHASE="running:$tag"
  write_state running "" || { reap_child || true; return 125; }
  local rc=0 stop_reason=
  while same_captured_child_alive; do
    local now
    now=$(date +%s)
    if [[ "${WS58_QUAL:-0}" == 1 && -s "$event_path" && ! -e "$ack_path" ]]; then
      "$PY" "$ROOT/native_event_ack.py" "$tag" "$event_path" "$ack_path" "$RUN_DIR" "${WS58_MANIFEST_PATH:?}" "${FILLER_QUAL_PHASE:?}" "${WS58_QUAL_CUTOFF_EVENT:-}" "${WS58_QUAL_NONCE:-}" || { reap_child || true; return 70; }
    fi
    if [[ "${G2_MODE:-full}" == smoke ]]; then
      if [[ -e "$ROOT/STOP" ]]; then stop_reason=stop-file
      elif (( now - START_WALL >= 285 )); then stop_reason=smoke-cap
      fi
    else
      if [[ -e "$FILLER_STOPFILE" ]]; then stop_reason=stop-file
      elif (( now >= FILLER_DEADLINE )); then stop_reason=work-deadline
      fi
    fi
    if [[ -n "$stop_reason" ]]; then
      echo "stop_reason=$stop_reason tag=$tag" >> "$LOG"
      reap_child || return 125
      return 75
    fi
    sleep 1
  done
  wait "$CHILD_PID" || rc=$?
  if same_captured_child_entry; then
    echo "CHILD_REAP_UNVERIFIED pid=$CHILD_PID start_ticks=$CHILD_START_TICKS" >> "$LOG"
    DIRECT_CHILD_REAPED=false
    return 125
  fi
  echo "CHILD_REAPED pid=$CHILD_PID start_ticks=$CHILD_START_TICKS rc=$rc" >> "$LOG"
  LAST_CHILD_PID=$CHILD_PID
  LAST_CHILD_TICKS=$CHILD_START_TICKS
  CHILD_PID=; CHILD_START_TICKS=; DIRECT_CHILD_REAPED=true
  STATE_PHASE="validating:$tag"
  write_state running "" || return 125
  echo "END $tag rc=$rc $(date -u +%FT%TZ)" | tee -a "$LOG"
  if [[ $rc -ne 0 ]]; then return "$rc"; fi
  [[ -s "$json" && -s "$jsonl" ]] || { echo "missing_result $tag" >> "$LOG"; return 70; }
  "$PY" - "$json" "$jsonl" "$tag" <<'PY' >> "$LOG" 2>&1 || return 70
import json, sys
j, jl, tag = sys.argv[1:]
payload=json.load(open(j, encoding="utf-8"))
rows=[json.loads(line) for line in open(jl, encoding="utf-8") if line.strip()]
if not isinstance(payload.get("data"), list) or not payload["data"] or not rows:
    raise SystemExit("empty_result:"+tag)
if len(payload["data"]) != len(rows):
    raise SystemExit("json_jsonl_count_mismatch:"+tag)
if any(not isinstance(r,dict) or not str(r.get("output","")).strip() for r in rows):
    raise SystemExit("empty_prediction:"+tag)
print("RESULT_OK", tag, "records", len(rows))
PY
}

printf 'timestamp\ttag\tpid\tstart_ticks\tphase\tkfd_proc_present\thip\n' > "$SAMPLES"
if ! "$PY" - <<'PY' >> "$LOG" 2>&1
import pathlib
import triton

expected = pathlib.Path('/mnt/raid0/llm/venv/lib/python3.12/site-packages/triton').resolve()
actual = pathlib.Path(triton.__file__).resolve().parent
if triton.__version__ != '3.6.0' or actual != expected:
    raise SystemExit(f'unexpected Triton runtime: version={triton.__version__} path={actual}')
print(f'TRITON_RUNTIME version={triton.__version__} path={actual}')
PY
then
  write_state failed 70 || true
  exit 70
fi
if [[ "$INTERNAL_MODE" == --deadline-test || "$INTERNAL_MODE" == --stop-test ]]; then
  echo "MONITOR_FIXTURE mode=$INTERNAL_MODE exercising run_eval child polling" >> "$LOG"
  set +e
  run_eval Accurate_Retrieval eventqa_131072 base 1
  rc=$?
  set -e
  if [[ "$rc" == 75 ]]; then
    write_state partial 75
    exit 75
  fi
  write_state failed "$rc" || true
  echo "MONITOR_FIXTURE_UNEXPECTED_RC rc=$rc" >> "$LOG"
  exit "$rc"
fi
if [[ "$INTERNAL_MODE" == --cleanup-capture-failure-test ]]; then
  echo "CLEANUP_CAPTURE_FAILURE_TEST_ONLY no evaluator/model/GPU path" >> "$LOG"
  /bin/sleep 300 >> "$LOG" 2>&1 &
  CHILD_PID=$!
  LAST_CHILD_PID=$CHILD_PID
  DIRECT_CHILD_REAPED=false
  # Emulate the exact post-Popen /proc identity-capture failure boundary.
  CHILD_START_TICKS=
  reap_child || { write_state failed 125 || true; exit 125; }
  if direct_child_alive "$LAST_CHILD_PID"; then
    echo "CLEANUP_CAPTURE_FAILURE_TEST_CHILD_STILL_ALIVE pid=$LAST_CHILD_PID" >> "$LOG"
    write_state failed 125 || true
    exit 125
  fi
  write_state complete 0
  exit 0
fi
if [[ "${WS58_QUAL:-0}" == 1 ]]; then
  [[ "${FILLER_QUAL_PHASE:-}" == normal || "${FILLER_QUAL_PHASE:-}" == cutoff ]] || { write_state failed 70; exit 70; }
  [[ "${WS58_QUALIFIER_PATH:-}" == /mnt/raid0/llm/tmp/compute-flags/bin/qual-v3-native/qualify_launcher.py ]] || { write_state failed 70; exit 70; }
  qual_rc=0
  run_eval Accurate_Retrieval eventqa_65536 base 1 || qual_rc=$?
  if [[ $qual_rc == 0 && "$FILLER_QUAL_PHASE" == normal ]]; then
    run_eval Accurate_Retrieval eventqa_full base 1 || qual_rc=$?
  fi
  "$PY" "$ROOT/native_qual_result.py" "$RUN_DIR" "$RESULT_DIR" "${WS58_QUAL_PROOF:?}" "${WS58_MANIFEST_PATH:?}" "$qual_rc" || { write_state failed 70; exit 70; }
  if [[ $qual_rc == 75 ]]; then write_state partial 75; exit 75; fi
  if [[ $qual_rc != 0 ]]; then write_state failed "$qual_rc"; exit "$qual_rc"; fi
  write_state complete 0
  exit 0
fi
if [[ "$INTERNAL_MODE" == --cutoff-test ]]; then
  echo "CUTOFF_TEST_ONLY no evaluator/model/GPU path" >> "$LOG"
  # Match the smoke's two sequential model subprocesses: reap the first
  # normally, then let the forced deadline interrupt/reap the second.
  /bin/sleep 0.1 >> "$LOG" 2>&1 &
  CHILD_PID=$!
  WORK_STARTED=true
  DIRECT_CHILD_REAPED=false
  capture_child_identity "$CHILD_PID" || { echo "CUTOFF_TEST_FIRST_IDENTITY_FAILED" >> "$LOG"; exit 125; }
  echo "CHILD_STARTED pid=$CHILD_PID start_ticks=$CHILD_START_TICKS" >> "$LOG"
  first_rc=0
  wait "$CHILD_PID" || first_rc=$?
  if same_captured_child_entry; then
    echo "CUTOFF_TEST_FIRST_REAP_UNVERIFIED pid=$CHILD_PID" >> "$LOG"
    DIRECT_CHILD_REAPED=false
    write_state failed 125
    exit 125
  fi
  LAST_CHILD_PID=$CHILD_PID; LAST_CHILD_TICKS=$CHILD_START_TICKS
  echo "CHILD_REAPED pid=$CHILD_PID start_ticks=$CHILD_START_TICKS rc=$first_rc" >> "$LOG"
  CHILD_PID=; CHILD_START_TICKS=; DIRECT_CHILD_REAPED=true
  # Remain alive past the real 285 s smoke deadline so the in-job deadline,
  # signal trap, and captured-child cleanup are exercised unchanged.
  /bin/sleep 300 >> "$LOG" 2>&1 &
  CHILD_PID=$!
  WORK_STARTED=true
  DIRECT_CHILD_REAPED=false
  capture_child_identity "$CHILD_PID" || { echo "CUTOFF_TEST_CHILD_IDENTITY_FAILED" >> "$LOG"; exit 125; }
  echo "CHILD_STARTED pid=$CHILD_PID start_ticks=$CHILD_START_TICKS" >> "$LOG"
  local_rc=0
  wait "$CHILD_PID" || local_rc=$?
  if same_captured_child_entry; then
    echo "CUTOFF_TEST_REAP_UNVERIFIED pid=$CHILD_PID" >> "$LOG"
    DIRECT_CHILD_REAPED=false
    write_state failed 125
    exit 125
  fi
  LAST_CHILD_PID=$CHILD_PID; LAST_CHILD_TICKS=$CHILD_START_TICKS
  echo "CHILD_REAPED pid=$CHILD_PID start_ticks=$CHILD_START_TICKS rc=$local_rc" >> "$LOG"
  CHILD_PID=; CHILD_START_TICKS=; DIRECT_CHILD_REAPED=true
  write_state complete 0
  exit 0
fi
if [[ "${G2_MODE:-full}" == smoke ]]; then
  # One real first eventqa_65536/base record is a bounded representative smoke.
  # It does not validate the full-context eventqa_full OOM repair; the full Gate 2
  # matrix below retains eventqa_full unchanged for the scheduled diagnostic.
  run_eval Accurate_Retrieval eventqa_65536 base 1 || { rc=$?; if [[ $rc == 75 ]]; then write_state partial 75; else write_state failed "$rc"; fi; exit "$rc"; }
  base_json="$RESULT_DIR/Accurate_Retrieval__eventqa_65536__base.json"
  base_jsonl="$RESULT_DIR/Accurate_Retrieval__eventqa_65536__base.jsonl"
  "$PY" - "$RUN_DIR/SMOKE.json" "$START_ISO" "$START_WALL" "$RUN_ID" "$base_json" "$base_jsonl" "$SAMPLES" <<'PY' || { rc=$?; write_state failed "$rc"; exit "$rc"; }
import hashlib, json, os, sys, time
out, started, wall0, rid, json_path, jsonl_path, samples_path = sys.argv[1:]
from deltamem.eval.official_eval_utils import resume_record_sha256
for path in (json_path, jsonl_path):
    if not os.path.isfile(path) or os.path.getsize(path)==0: raise SystemExit("missing smoke result: "+path)
result=json.load(open(json_path,encoding="utf-8"))
records=[json.loads(line) for line in open(jsonl_path,encoding="utf-8") if line.strip()]
if len(result.get("data",[])) != 1 or len(records) != 1: raise SystemExit("smoke scope mismatch")
record=records[0]
identity=record.get("resume_identity",{})
if record.get("record_index") != 0 or identity.get("question_index") != 0: raise SystemExit("smoke identity mismatch")
if identity.get("split") != "Accurate_Retrieval" or identity.get("source") != "eventqa_65536": raise SystemExit("smoke source identity mismatch")
if record.get("resume_integrity_sha256") != resume_record_sha256(record): raise SystemExit("smoke resume-row integrity mismatch")
if not str(record.get("output","")).strip(): raise SystemExit("empty real output")
if not isinstance(record.get("query_time_len"),(int,float)) or record["query_time_len"] <= 0: raise SystemExit("missing real generation timing")
samples=[line.rstrip("\n").split("\t") for line in open(samples_path,encoding="utf-8") if line.strip()]
tag="Accurate_Retrieval__eventqa_65536__base"
if not any(len(row)==7 and row[1]==tag and row[4]=="after_generate" and row[5]=="1" and row[6].startswith("6.") for row in samples): raise SystemExit("no own-process ROCm/KFD sample after smoke generation")
wall=int(time.time())-int(wall0)
payload={"run_id":rid,"started_at":started,"ended_at":time.strftime("%Y-%m-%dT%H:%M:%SZ",time.gmtime()),
  "scope":"one real first question from Accurate_Retrieval/eventqa_65536/base using the unchanged official context/truncation path; smoke only, not Gate 2 result. The full eventqa_full context repair remains unverified",
  "real_generation_seconds":round(float(record["query_time_len"]),3),"wall_s":wall,
  "model":"/mnt/raid0/llm/models/Qwen3-4B-Instruct-2507; adapter=/mnt/raid0/llm/models/delta-mem_qwen3_4b-instruct",
  "arm":"base","result_json":json_path,"result_json_sha256":hashlib.sha256(open(json_path,"rb").read()).hexdigest(),
  "result_jsonl":jsonl_path,"result_jsonl_sha256":hashlib.sha256(open(jsonl_path,"rb").read()).hexdigest(),
  "record_index":0,"writer_ok":True,"cleanup_scope":"direct-child-only",
  "launcher_path":"/mnt/raid0/llm/tmp/codex-ni-native-successors-20261101/inf12/launch.sh"}
tmp=out+".tmp"
with open(tmp,"w",encoding="utf-8") as f: json.dump(payload,f,sort_keys=True,indent=2); f.write("\n"); f.flush(); os.fsync(f.fileno())
os.replace(tmp,out)
fd=os.open(os.path.dirname(out),os.O_RDONLY); os.fsync(fd); os.close(fd)
PY
else
  # Full Gate 2 matrix: all four official splits and all source configs, both arms.
  declare -a TASKS=(
    'Accurate_Retrieval eventqa_131072' 'Accurate_Retrieval eventqa_65536'
    'Accurate_Retrieval eventqa_full' 'Accurate_Retrieval longmemeval_s*'
    'Accurate_Retrieval ruler_qa1_197K' 'Accurate_Retrieval ruler_qa2_421K'
    'Conflict_Resolution factconsolidation_mh_262k' 'Conflict_Resolution factconsolidation_mh_32k'
    'Conflict_Resolution factconsolidation_mh_64k' 'Conflict_Resolution factconsolidation_mh_6k'
    'Conflict_Resolution factconsolidation_sh_262k' 'Conflict_Resolution factconsolidation_sh_32k'
    'Conflict_Resolution factconsolidation_sh_64k' 'Conflict_Resolution factconsolidation_sh_6k'
    'Long_Range_Understanding detective_qa' 'Long_Range_Understanding infbench_sum_eng_shots2'
    'Test_Time_Learning recsys_redial_full' 'Test_Time_Learning icl_banking77_5900shot_balance'
    'Test_Time_Learning icl_clinic150_7050shot_balance' 'Test_Time_Learning icl_nlu_8296shot_balance'
    'Test_Time_Learning icl_trec_coarse_6600shot_balance' 'Test_Time_Learning icl_trec_fine_6400shot_balance'
  )
  for arm in base delta; do
    for task in "${TASKS[@]}"; do
      read -r split source <<< "$task"
      run_eval "$split" "$source" "$arm" || {
        rc=$?
        if [[ $rc -eq 75 ]]; then
          write_state partial 75
          echo "stopped_on=$split/$source/$arm rc=$rc" >> "$LOG"
          exit 75
        fi
        write_state failed "$rc"
        echo "failed_at=$split/$source/$arm rc=$rc" >> "$LOG"
        exit "$rc"
      }
    done
  done
  "$PY" "$ROOT/summarize_full.py" >> "$LOG" 2>&1 || { rc=$?; write_state failed "$rc"; echo "full_summary_rc=$rc" >> "$LOG"; exit "$rc"; }
  "$PY" "$ROOT/finalize_full.py" "$G2_PIN_FINGERPRINT" >> "$LOG" 2>&1 || { rc=$?; write_state failed "$rc"; exit "$rc"; }
fi
write_state complete 0
exit 0
