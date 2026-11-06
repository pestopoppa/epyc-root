#!/bin/bash
# launch_local_inference.sh — manually launch the local C6 inference servers.
#
# Usage:
#   ./launch_local_inference.sh cpu  [--clean] [--dry-run]
#   ./launch_local_inference.sh gpu  [--dry-run]
#   ./launch_local_inference.sh both [--clean] [--dry-run]
#   ./launch_local_inference.sh stop [cpu|gpu]
#   ./launch_local_inference.sh status [cpu|gpu]
#   ./launch_local_inference.sh logs [cpu|gpu]
#
# Defaults are the winners of artifacts/compute/local-launch-optimization-20261106.
# Override any of these with environment variables:
#
#   CPU_STORE  CPU_MODEL  CPU_MTP  CPU_MTP_ON  CPU_NP  CPU_CTX  CPU_THREADS
#   CPU_KV  CPU_UNIFIED  CPU_FA  CPU_PORT
#   GPU_STORE  GPU_MODEL  GPU_DFLASH  GPU_NP  GPU_CTX  GPU_KV  GPU_NMAX
#   GPU_UNIFIED  GPU_CPUS  GPU_CACHE  GPU_PORT
#   STATE_DIR
#
# Examples:
#   CPU_NP=1 CPU_CTX=262144 ./launch_local_inference.sh cpu
#   GPU_NP=1 GPU_CTX=196608 ./launch_local_inference.sh gpu
#   GPU_KV=q8_0 GPU_NMAX=7 ./launch_local_inference.sh gpu
#   ./launch_local_inference.sh stop
#
# The script only ever stops PIDs recorded in its own pidfiles. It never uses
# a broad process-name or argv pattern, because this is a shared host.
#
# Measured 2026-11-06 (54k-token prompt, greedy, C6 champion stores):
#   CPU thread optimum flips with context: t48 wins at 8-28k (16.07 at 28k),
#   t96 wins at 55k+ (16.05 vs 14.29 at 54,329 prompt). Default is 96 for the
#   57k serving workload; use CPU_THREADS=48 for short-context (8k) serving.
#   MTP stays ON. At t48/55k, no-MTP was slightly better (15.07 vs 14.29), but
#   both are below t96+MTP (16.05); at t96/55k, no-MTP collapses to 12.86.
#   Default is t96 + MTP for the 57k workload.
#   GPU np4/262k f16 n8: ~43.5 tok/s; np1/196k: ~43.0; 16k greedy: ~71.
#   Slower variants (do NOT use as defaults): IQK-FA ON, q8_0 KV, unified KV,
#   DFlash2 n7. Keep f16 / n8 / no-kv-unified.
#   For one long stream, GPU_NP=1 GPU_CTX=196608 is equal speed with more
#   headroom. CPU np1/65536 helped t48/28k but was slower at t96/55k
#   (14.52 vs 16.05); keep CPU np4/262144.

set -euo pipefail

# ---------------------------------------------------------------------------
# Defaults — set from the 2026-11-06 local-launch matrix.
# ---------------------------------------------------------------------------
CPU_STORE="${CPU_STORE:-/mnt/raid0/llm/kernels/builds/cpu-20261105-65da39eb1-c6fold2}"
CPU_MODEL="${CPU_MODEL:-/mnt/raid0/llm/models/unsloth/Qwen3.8-Flash-Next-GGUF/UD-IQ4_XS/Qwen3.8-Flash-Next-UD-IQ4_XS-00001-of-00003.gguf}"
CPU_MTP="${CPU_MTP:-/mnt/raid0/llm/models/unsloth/Qwen3.8-Flash-Next-GGUF/MTP/mtp-Qwen3.8-Flash-Next-shared-Q8_0.gguf}"
CPU_NP="${CPU_NP:-4}"
CPU_CTX="${CPU_CTX:-262144}"
CPU_THREADS="${CPU_THREADS:-96}"
CPU_KV="${CPU_KV:-f16}"
CPU_UNIFIED="${CPU_UNIFIED:-0}"
CPU_FA="${CPU_FA:-0}"
# MTP is ON by default: t96+MTP is the 55k winner (16.05); t96/no-MTP collapses to 12.86.
CPU_MTP_ON="${CPU_MTP_ON:-1}"
CPU_PORT="${CPU_PORT:-8074}"

GPU_STORE="${GPU_STORE:-/mnt/raid0/llm/kernels/builds/gpu-20261106-65da39eb1-c6fold2}"
GPU_MODEL="${GPU_MODEL:-/mnt/raid0/llm/models/Qwen3.8-27B-Q8_0.gguf}"
GPU_DFLASH="${GPU_DFLASH:-/mnt/raid0/llm/models/Qwen3.8-27B-DFlash2-Q8_0.gguf}"
GPU_NP="${GPU_NP:-4}"
GPU_CTX="${GPU_CTX:-262144}"
GPU_KV="${GPU_KV:-f16}"
GPU_UNIFIED="${GPU_UNIFIED:-0}"
GPU_NMAX="${GPU_NMAX:-8}"
GPU_CPUS="${GPU_CPUS:-184-191}"
GPU_CACHE="${GPU_CACHE:-1}"
GPU_PORT="${GPU_PORT:-8083}"

STATE_DIR="${STATE_DIR:-${XDG_STATE_HOME:-$HOME/.local/state}/epyc-local}"
mkdir -p "$STATE_DIR"

CPU_LOG="$STATE_DIR/cpu.log"
GPU_LOG="$STATE_DIR/gpu.log"
CPU_PID="$STATE_DIR/cpu.pid"
GPU_PID="$STATE_DIR/gpu.pid"

log()  { printf '[%s] %s\n' "$(date +%H:%M:%S)" "$*"; }
die()  { log "ERROR: $*" >&2; exit 1; }
pid_of() { [ -f "$1" ] && cat "$1" || true; }
alive() {
  local p; p="$(pid_of "$1")"
  [ -n "$p" ] && kill -0 "$p" 2>/dev/null
}

usage() {
  sed -n '2,32p' "$0" | sed 's/^# \{0,1\}//'
}

require_file() {
  [ -e "$1" ] || die "missing required file: $1"
}

stop_one() {
  local name="$1" pidfile="$2" pid
  pid="$(pid_of "$pidfile")"
  if [ -z "$pid" ]; then
    log "$name: no pidfile ($pidfile)"
    rm -f "$pidfile"
    return 0
  fi
  if ! kill -0 "$pid" 2>/dev/null; then
    log "$name: stale pidfile (PID $pid not running)"
    rm -f "$pidfile"
    return 0
  fi
  log "$name: stopping PID $pid"
  kill -TERM "$pid" 2>/dev/null || true
  for _ in $(seq 1 60); do
    kill -0 "$pid" 2>/dev/null || break
    sleep 1
  done
  if kill -0 "$pid" 2>/dev/null; then
    log "$name: SIGTERM timed out; sending SIGKILL to PID $pid"
    kill -KILL "$pid" 2>/dev/null || true
  fi
  rm -f "$pidfile"
  log "$name: stopped"
}

wait_health() {
  local name="$1" port="$2" pidfile="$3" timeout="${4:-900}" pid health
  pid="$(pid_of "$pidfile")"
  for ((i = 0; i < timeout; i += 2)); do
    if ! kill -0 "$pid" 2>/dev/null; then
      log "$name: server exited during load"
      tail -n 60 "$STATE_DIR/$name.log" 2>/dev/null || true
      return 1
    fi
    health=$(curl -fsS --max-time 2 "http://127.0.0.1:$port/health" 2>/dev/null || true)
    if [[ "$health" == *'"status"'* ]]; then
      log "$name: healthy on :$port (PID $pid)"
      return 0
    fi
    sleep 2
  done
  log "$name: did not become healthy on :$port within ${timeout}s"
  tail -n 60 "$STATE_DIR/$name.log" 2>/dev/null || true
  return 1
}

clean_cpu() {
  local target="${1:-58}"
  log "CPU: evicting page cache (target ${target} GiB/node)"
  /mnt/raid0/llm/tmp/inf70/evict_nodes_force.sh "$target" | tee "$STATE_DIR/evict.log"
  if ! grep -q 'EVICT OK' "$STATE_DIR/evict.log"; then
    log "CPU: WARNING eviction did not reach ${target} GiB/node; continuing"
  fi
}

cpu_argv() {
  local args=(
    "$CPU_STORE/bin/llama-server"
    -m "$CPU_MODEL"
    -np "$CPU_NP" -c "$CPU_CTX"
    -t "$CPU_THREADS" -tb "$CPU_THREADS"
    -b 2048 -ub 512
    -ctk "$CPU_KV" -ctv "$CPU_KV"
    --device none -ngl 0 -fa on
    --host 127.0.0.1 --port "$CPU_PORT" --metrics --slots
    --load-threads 96
    --no-mmap --no-webui
    -lv 4
  )
  if [ "$CPU_MTP_ON" = "1" ]; then
    args+=(
      -md "$CPU_MTP" -ngld 0
      --spec-type draft-mtp --spec-draft-n-max 4
      --device-draft none --draft-p-min 0.5
    )
  fi
  if [ "$CPU_UNIFIED" = "1" ]; then
    args+=(--kv-unified)
  else
    args+=(--no-kv-unified)
  fi
  if [ "$CPU_FA" = "1" ]; then
    args+=(--cpu-iqk-fa on)
  fi
  printf '%s\0' "${args[@]}"
}

cpu_env() {
  printf '%s\0' \
    env \
    "LD_LIBRARY_PATH=$CPU_STORE/bin" \
    GGML_FA_SPLIT_KV=0 \
    GGML_FUSED_DECODE_OFF=1 \
    GGML_IQK=1 \
    GGML_NOHUGEPAGE_PROCESS=1 \
    OMP_DYNAMIC=false \
    OMP_PLACES=cores \
    OMP_PROC_BIND=spread \
    OMP_WAIT_POLICY=active
}

gpu_argv() {
  local args=(
    "$GPU_STORE/bin/llama-server"
    -m "$GPU_MODEL"
    -np "$GPU_NP" -c "$GPU_CTX"
    -t 8 -tb 8
    -b 2048 -ub 2048
    -ctk "$GPU_KV" -ctv "$GPU_KV"
    --device ROCm0 -ngl 99 -fa on
    --host 127.0.0.1 --port "$GPU_PORT" --metrics --slots
    -md "$GPU_DFLASH" -ngld 99
    --spec-type draft-dflash --spec-draft-n-max "$GPU_NMAX"
  )
  if [ "$GPU_UNIFIED" = "1" ]; then
    args+=(--kv-unified)
  else
    args+=(--no-kv-unified)
  fi
  if [ "$GPU_CACHE" = "1" ]; then
    args+=(--cache-ram 32768 --ctx-checkpoints 8)
  fi
  printf '%s\0' "${args[@]}"
}

gpu_env() {
  printf '%s\0' env -u HSA_OVERRIDE_GFX_VERSION "LD_LIBRARY_PATH=$GPU_STORE/bin"
}

launch_cpu() {
  local clean="${1:-0}" dry="${2:-0}"
  require_file "$CPU_STORE/bin/llama-server"
  require_file "$CPU_MODEL"
  require_file "$CPU_MTP"
  if alive "$CPU_PID"; then
    die "CPU server already running (PID $(pid_of "$CPU_PID")); run 'stop cpu' first"
  fi
  [ "$clean" = "1" ] && clean_cpu 58

  local -a envs args
  mapfile -d '' envs < <(cpu_env)
  mapfile -d '' args < <(cpu_argv)
  if [ "$dry" = "1" ]; then
    printf '%q ' "${envs[@]}" taskset -c 0-95 numactl --interleave=all "${args[@]}"
    echo
    return 0
  fi
  log "CPU: launching Q38FN on :$CPU_PORT (np=$CPU_NP ctx=$CPU_CTX t=$CPU_THREADS kv=$CPU_KV fa=$CPU_FA)"
  nohup "${envs[@]}" taskset -c 0-95 numactl --interleave=all "${args[@]}" > "$CPU_LOG" 2>&1 &
  echo $! > "$CPU_PID"
  wait_health cpu "$CPU_PORT" "$CPU_PID" 900
  print_one cpu
}

launch_gpu() {
  local dry="${1:-0}"
  require_file "$GPU_STORE/bin/llama-server"
  require_file "$GPU_MODEL"
  require_file "$GPU_DFLASH"
  if alive "$GPU_PID"; then
    die "GPU server already running (PID $(pid_of "$GPU_PID")); run 'stop gpu' first"
  fi
  local -a envs args
  mapfile -d '' envs < <(gpu_env)
  mapfile -d '' args < <(gpu_argv)
  if [ "$dry" = "1" ]; then
    printf '%q ' "${envs[@]}" taskset -c "$GPU_CPUS" "${args[@]}"
    echo
    return 0
  fi
  log "GPU: launching Qwen3.8-27B + DFlash2 on :$GPU_PORT (np=$GPU_NP ctx=$GPU_CTX kv=$GPU_KV n_max=$GPU_NMAX)"
  nohup "${envs[@]}" taskset -c "$GPU_CPUS" "${args[@]}" > "$GPU_LOG" 2>&1 &
  echo $! > "$GPU_PID"
  wait_health gpu "$GPU_PORT" "$GPU_PID" 900
  print_one gpu
}

print_one() {
  local name="$1" port pidfile pid
  case "$name" in
    cpu) port="$CPU_PORT"; pidfile="$CPU_PID" ;;
    gpu) port="$GPU_PORT"; pidfile="$GPU_PID" ;;
    *) die "unknown target $name" ;;
  esac
  pid="$(pid_of "$pidfile")"
  echo "== $name =="
  if [ -z "$pid" ] || ! kill -0 "$pid" 2>/dev/null; then
    echo "not running"
    return 0
  fi
  ps -o pid,lstart,etime,pcpu,rss,comm -p "$pid" --no-headers || true
  printf 'health: '
  curl -fsS --max-time 3 "http://127.0.0.1:$port/health" 2>/dev/null || printf 'unreachable'
  echo
  curl -fsS --max-time 5 "http://127.0.0.1:$port/props" 2>/dev/null | python3 -c '
import json,sys
d=json.load(sys.stdin)
print("model:", d.get("model_path"))
print("build:", d.get("build_info"))
print("slots:", d.get("total_slots"))
' 2>/dev/null || true
  curl -fsS --max-time 5 "http://127.0.0.1:$port/slots" 2>/dev/null | python3 -c '
import json,sys
for s in json.load(sys.stdin):
    nt=(s.get("next_token") or [{}])[0]
    print("slot {}: n_ctx={} processing={} decoded={}".format(
        s.get("id"), s.get("n_ctx"), s.get("is_processing"), nt.get("n_decoded")))
' 2>/dev/null || true
  grep -E 'THP_enabled|Cpus_allowed_list|VmRSS' "/proc/$pid/status" 2>/dev/null || true
  numastat -p "$pid" 2>/dev/null | tail -n 4 || true
  if [ "$name" = "gpu" ]; then
    rocm-smi --showuse --showpower 2>/dev/null | grep -E 'GPU use|Graphics Package Power' || true
  fi
}

logs_one() {
  local name="$1" logfile
  case "$name" in
    cpu) logfile="$CPU_LOG" ;;
    gpu) logfile="$GPU_LOG" ;;
    *) die "unknown target $name" ;;
  esac
  tail -n 120 "$logfile" 2>/dev/null || echo "no log: $logfile"
}

main() {
  local cmd="${1:-}"; shift || true
  local clean=0 dry=0 target=all
  if [ "$cmd" = "stop" ] || [ "$cmd" = "status" ] || [ "$cmd" = "logs" ]; then
    if [ $# -gt 0 ] && [[ "$1" != --* ]]; then
      target="$1"; shift
    fi
  fi
  while [ $# -gt 0 ]; do
    case "$1" in
      --clean) clean=1 ;;
      --dry-run) dry=1 ;;
      *) die "unknown option: $1 (try --help)" ;;
    esac
    shift
  done
  case "$cmd" in
    cpu) launch_cpu "$clean" "$dry" ;;
    gpu) launch_gpu "$dry" ;;
    both)
      launch_gpu "$dry"
      launch_cpu "$clean" "$dry"
      ;;
    stop)
      case "$target" in
        all) stop_one cpu "$CPU_PID"; stop_one gpu "$GPU_PID" ;;
        cpu) stop_one cpu "$CPU_PID" ;;
        gpu) stop_one gpu "$GPU_PID" ;;
        *) die "stop target must be cpu, gpu, or all" ;;
      esac
      ;;
    status)
      case "$target" in
        all) print_one cpu; echo; print_one gpu ;;
        cpu) print_one cpu ;;
        gpu) print_one gpu ;;
        *) die "status target must be cpu, gpu, or all" ;;
      esac
      ;;
    logs)
      case "$target" in
        all) logs_one cpu; echo; logs_one gpu ;;
        cpu) logs_one cpu ;;
        gpu) logs_one gpu ;;
        *) die "logs target must be cpu, gpu, or all" ;;
      esac
      ;;
    ""|-h|--help|help) usage ;;
    *) usage; exit 2 ;;
  esac
}

main "$@"
