#!/bin/bash
# Shared helpers for df29_server.sh / df2_e2e.sh / run_probe.sh. Sourced, never executed.
# Contract: every process this library starts is recorded by PID, and df29_cleanup kills exactly
# those PIDs (SIGTERM -> wait -> SIGKILL -> verify with ps -p). No name-pattern kills, ever.

DF29_DIR=$(dirname "$(readlink -f "${BASH_SOURCE[0]}")")
DF29_TARGET=/mnt/raid0/llm/models/Qwen3.8-27B-Q8_0.gguf
DF29_DRAFTER=/mnt/raid0/llm/models/Qwen3.8-27B-DFlash2-Q8_0.gguf
DF29_TEMPLATE=/mnt/raid0/llm/models/chat-templates/epyc-qwen3x-v1-terse.jinja
DF29_LINKAGE=/workspace/repos/epyc-inference-research/scripts/utils/verify_ggml_linkage.sh
# 27B Q8_0 27.05 GiB + DFlash2 Q8_0 1.92 GiB + KV/compute/HIP context headroom.
DF29_VRAM_NEED_GIB=${DF29_VRAM_NEED_GIB:-38}

DF29_PIDS=()          # every background PID we own (server, sampler, client)
DF29_SERVER_PID=""
DF29_SAMPLER_PID=""

df29_ts() { date -u +%FT%TZ; }
df29_log() { echo "[$(df29_ts)] $*"; }

# MI210 sysfs node: the card whose vram_total is the largest (64 GiB board).
df29_vram_node() {
    local best="" bestv=0 f v
    for f in /sys/class/drm/card*/device/mem_info_vram_total; do
        [ -r "$f" ] || continue
        v=$(cat "$f" 2>/dev/null || echo 0)
        if [ "$v" -gt "$bestv" ]; then bestv=$v; best=$(dirname "$f"); fi
    done
    echo "$best"
}

df29_vram_used() { local n; n=$(df29_vram_node); [ -n "$n" ] && cat "$n/mem_info_vram_used" 2>/dev/null || echo -1; }
df29_vram_total() { local n; n=$(df29_vram_node); [ -n "$n" ] && cat "$n/mem_info_vram_total" 2>/dev/null || echo -1; }

# KFD process list (read-only). Each /sys/class/kfd/kfd/proc/<pid> is a process holding the GPU.
df29_kfd_procs() {
    local d p
    for d in /sys/class/kfd/kfd/proc/*; do
        [ -d "$d" ] || continue
        p=$(basename "$d")
        printf '  kfd pid=%s %s\n' "$p" "$(tr '\0' ' ' < "/proc/$p/cmdline" 2>/dev/null | cut -c1-160)"
    done
}

# Refuse to run if the GPU lacks room for the 27B + drafter. Prints the reason; returns 1 on refusal.
df29_vram_preflight() {
    local used total free_gib
    used=$(df29_vram_used); total=$(df29_vram_total)
    if [ "$used" -lt 0 ] || [ "$total" -le 0 ]; then echo "VRAM sysfs unreadable"; return 1; fi
    free_gib=$(( (total - used) / 1073741824 ))
    echo "VRAM used=$((used / 1048576)) MiB total=$((total / 1048576)) MiB free=${free_gib} GiB need=${DF29_VRAM_NEED_GIB} GiB"
    df29_kfd_procs
    [ "$free_gib" -ge "$DF29_VRAM_NEED_GIB" ]
}

df29_port_busy() { ss -Hltn "sport = :$1" 2>/dev/null | grep -q .; }

# background VRAM sampler: one line per second "epoch used_bytes" into $1
df29_start_sampler() {
    local out=$1 node
    node=$(df29_vram_node)
    ( while :; do printf '%s %s\n' "$(date +%s)" "$(cat "$node/mem_info_vram_used" 2>/dev/null || echo -1)"; sleep 1; done ) > "$out" 2>/dev/null &
    DF29_SAMPLER_PID=$!
    DF29_PIDS+=("$DF29_SAMPLER_PID")
}

df29_vram_peak_gib() {  # $1 = sampler file; prints peak and baseline (first sample) in GiB
    awk 'NR==1{b=$2} {if($2>m)m=$2} END{if(NR==0){print "peak=NA base=NA"} else printf "peak=%.2f base=%.2f\n", m/1073741824, b/1073741824}' "$1" 2>/dev/null
}

# watchdog: TERM the calling script ($$) after $1 s, but only if $$ is still that script ($2 in its cmdline),
# so a recycled PID can never be hit. The watchdog's own sleep is killed with it.
df29_start_watchdog() {
    local secs=$1 marker=$2
    ( sp=""; trap '[ -n "$sp" ] && kill "$sp" 2> /dev/null; exit 0' TERM
      sleep "$secs" & sp=$!; wait "$sp"
      if tr '\0' ' ' < "/proc/$$/cmdline" 2> /dev/null | grep -q -- "$marker"; then
          echo "[watchdog] wall cap ${secs}s hit -> TERM $$"; kill -TERM $$ 2> /dev/null
      fi ) &
    DF29_PIDS+=($!)
}

# kill exactly one PID we own: TERM, wait up to $2 s, KILL, verify.
df29_kill_pid() {
    local pid=$1 grace=${2:-20} i
    [ -n "$pid" ] || return 0
    ps -p "$pid" > /dev/null 2>&1 || return 0
    kill -TERM "$pid" 2>/dev/null || true
    for ((i = 0; i < grace * 2; i++)); do ps -p "$pid" > /dev/null 2>&1 || break; sleep 0.5; done
    if ps -p "$pid" > /dev/null 2>&1; then kill -KILL "$pid" 2>/dev/null || true; sleep 1; fi
    wait "$pid" 2>/dev/null || true
    if ps -p "$pid" > /dev/null 2>&1; then echo "WARNING: pid $pid survived SIGKILL"; return 1; fi
    return 0
}

df29_stop_server() {
    if [ -n "$DF29_SERVER_PID" ]; then
        df29_log "stopping server pid $DF29_SERVER_PID"
        df29_kill_pid "$DF29_SERVER_PID" 30 && df29_log "server pid $DF29_SERVER_PID confirmed dead"
        DF29_SERVER_PID=""
    fi
}

df29_cleanup() {
    local p
    df29_stop_server
    for p in "${DF29_PIDS[@]}"; do df29_kill_pid "$p" 5 > /dev/null || true; done
    DF29_PIDS=()
}

# flag mapping per build (champion fork vs upstream master), decided from the binaries' STRINGS — never by
# executing them (a HIP-linked llama-server --help would initialise ROCm / open /dev/kfd).
# Sets DF29_MMAP_FLAG (array), DF29_HAS_DFLASH (0/1), DF29_HAS_NONFINITE_CHECK (0/1).
df29_probe_flags() {
    local bin=$1 strs
    local f
    strs=$(for f in "$bin"/libllama-common.so* "$bin/llama-server" "$bin/libllama-server-impl.so"; do
               [ -f "$f" ] && strings "$f"
           done 2> /dev/null || true)
    if grep -q -F -- '--no-mmap' <<< "$strs"; then DF29_MMAP_FLAG=(--no-mmap)
    elif grep -q -F -- '--load-mode' <<< "$strs"; then DF29_MMAP_FLAG=(-lm none)   # master: --no-mmap -> --load-mode
    else DF29_MMAP_FLAG=(); fi
    if grep -q -F 'draft-dflash' <<< "$strs"; then DF29_HAS_DFLASH=1; else DF29_HAS_DFLASH=0; fi
    # the reject-on-non-finite guard is a champion-fork addition (common/speculative.cpp:1542); upstream has none
    if grep -q -F 'non-finite target features' <<< "$strs"; then DF29_HAS_NONFINITE_CHECK=1; else DF29_HAS_NONFINITE_CHECK=0; fi
}

# start llama-server: $1=bin dir, $2=log, $3=port, rest = server args (without binary/host/port).
# Exec chain env -> numactl -> taskset -> llama-server keeps $! == server PID.
df29_start_server() {
    local bin=$1 log=$2 port=$3; shift 3
    local pin=()
    if [ "${DF29_PIN:-1}" = 1 ] && command -v numactl > /dev/null; then
        pin=(numactl --membind=3 -- taskset -c 184-191)   # production :8083 placement (GPU host lane)
    fi
    env -u LD_LIBRARY_PATH -u HSA_OVERRIDE_GFX_VERSION \
        LD_LIBRARY_PATH="$bin:/opt/rocm/lib" \
        OMP_PROC_BIND=spread OMP_PLACES=cores OMP_WAIT_POLICY=active OMP_DYNAMIC=false \
        "${pin[@]}" "$bin/llama-server" --host 127.0.0.1 --port "$port" "$@" > "$log" 2>&1 &
    DF29_SERVER_PID=$!
    DF29_SERVER_START_TIME=$(python3 "$DF29_DIR/port_owner.py" --pid "$DF29_SERVER_PID" || true)
    DF29_PIDS+=("$DF29_SERVER_PID")
    echo "$DF29_SERVER_PID" > "$log.pid"
    printf '%s\n' "$bin/llama-server --host 127.0.0.1 --port $port $*" > "$log.argv"
}

# wait for /health == 200; returns 0 ok, 1 died, 2 timeout
df29_wait_health() {
    local port=$1 deadline=$2 code
    while [ "$(date +%s)" -lt "$deadline" ]; do
        ps -p "$DF29_SERVER_PID" > /dev/null 2>&1 || return 1
        local owner_rc=0
        python3 "$DF29_DIR/port_owner.py" --pid "$DF29_SERVER_PID" --port "$port" \
            --birth "$DF29_SERVER_START_TIME" || owner_rc=$?
        if [ "$owner_rc" = 2 ]; then return 3; fi
        if [ "$owner_rc" = 0 ]; then
            code=$(curl -s -m 2 -o /dev/null -w '%{http_code}' "http://127.0.0.1:$port/health" || true)
            if [ "$code" = 200 ]; then
                # Recheck after the response: a foreign listener must not inherit readiness.
                python3 "$DF29_DIR/port_owner.py" --pid "$DF29_SERVER_PID" --port "$port" \
                    --birth "$DF29_SERVER_START_TIME" || return 3
                return 0
            fi
        fi
        sleep 1
    done
    return 2
}

# proof of which libs the RUNNING server mapped (read-only /proc)
df29_server_maps() {
    local pid=$1
    grep -o -E '/[^ ]*lib(ggml[^ /]*|llama[^ /]*)\.so[^ ]*' "/proc/$pid/maps" 2>/dev/null | sort -u
}
