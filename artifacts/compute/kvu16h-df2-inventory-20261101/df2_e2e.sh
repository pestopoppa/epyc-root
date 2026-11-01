#!/bin/bash
# Slot step (c) E2E instrument, one arm (GPU). Run ONLY inside an exclusive GPU window.
#
# usage: df2_e2e.sh <arm_build_dir> <out_dir> [--cap SEC(300)] [--port P(18094)] [--no-bench] [--no-server]
#                   [--npl 1,2,4] [--max-tokens 128] [--no-pin]
#
# Part 1  llama-batched-bench on the 27B, production FA shapes, NO drafter (llama-batched-bench has no
#         draft-model / DFlash support in src-champion: tools/batched-bench/batched-bench.cpp has no draft
#         code and -md/--spec-* are registered only for LLAMA_EXAMPLE_{SPECULATIVE,SERVER,CLI}):
#           -fa on -ctk q8_0 -ctv q8_0 -kvu -npp 2048 -ntg 128 -npl 1,2,4 -b 2048 -ub 2048 -ngl 99 -t 8
#         Note: with -npl 4 and -npp 2048 every PP step is one 2048-row ubatch -> the MMA (>32 row) path.
# Part 2  llama-server with the :8083 recipe (DFlash2 n-max 7, q8_0 KV, --kv-unified) at -np 4 -c 32768,
#         C = 1, 2, 4 concurrent greedy requests (the pinned olympiad prompts), aggregate generated tok/s
#         and drafter acceptance per C, plus the non-finite / garbage screen of df29_server.sh.
# Same PID/port/linkage/VRAM hygiene as df29_server.sh; hard wall cap.
set -euo pipefail
source /mnt/raid0/llm/tmp/v11-fa-ab-20261004/df29/df29_lib.sh

[ $# -ge 2 ] || { sed -n 2,16p "$0"; exit 2; }
ARMDIR=$(readlink -f "$1"); OUT=$2; shift 2
CAP=300; PORT=18094; BENCH=1; SERVER=1; NPL=1,2,4; MAXTOK=128; ARM=""
while [ $# -gt 0 ]; do
    case "$1" in
        --cap) CAP=$2; shift 2 ;;
        --port) PORT=$2; shift 2 ;;
        --no-bench) BENCH=0; shift ;;
        --no-server) SERVER=0; shift ;;
        --npl) NPL=$2; shift 2 ;;
        --max-tokens) MAXTOK=$2; shift 2 ;;
        --no-pin) export DF29_PIN=0; shift ;;
        --arm) ARM=$2; shift 2 ;;
        *) echo "unknown arg $1"; exit 2 ;;
    esac
done
BIN=$ARMDIR/bin
if [ -z "$ARM" ]; then
    case "$(basename "$ARMDIR")" in build-master-*) ARM=M ;; *-[A-Z]) ARM=${ARMDIR##*-} ;; *) ARM=$(basename "$ARMDIR") ;; esac
fi
mkdir -p "$OUT"; OUT=$(readlink -f "$OUT")
T0=$(date +%s); DEADLINE=$((T0 + CAP))

trap 'df29_cleanup' EXIT
trap 'echo "signal: cleaning up"; df29_cleanup; exit 130' INT TERM
exec > >(tee -a "$OUT/df2_e2e.log") 2>&1

if [ "$SERVER" = 1 ] && df29_port_busy "$PORT"; then echo "E2E arm=$ARM verdict=ERROR reason=port-$PORT-busy"; exit 2; fi
if ! df29_vram_preflight > "$OUT/vram_preflight.txt"; then
    cat "$OUT/vram_preflight.txt"; echo "E2E arm=$ARM verdict=ERROR reason=vram-preflight"; exit 2
fi
cat "$OUT/vram_preflight.txt"
env -u LD_LIBRARY_PATH bash "$DF29_LINKAGE" "$BIN/llama-server" "$ARMDIR" > "$OUT/linkage.txt" 2>&1 || true
DF29_MMAP_FLAG=(); DF29_HAS_DFLASH=0; DF29_HAS_NONFINITE_CHECK=0
df29_probe_flags "$BIN"
df29_start_sampler "$OUT/vram_samples.txt"
df29_start_watchdog $((CAP + 60)) df2_e2e.sh
pin=()
if [ "${DF29_PIN:-1}" = 1 ] && command -v numactl > /dev/null; then pin=(numactl --membind=3 -- taskset -c 184-191); fi

BENCH_LINE="bench=skipped"
if [ "$BENCH" = 1 ]; then
    left=$((DEADLINE - $(date +%s) - 150)); [ "$SERVER" = 0 ] && left=$((DEADLINE - $(date +%s) - 10))
    if [ "$left" -lt 60 ]; then left=60; fi
    df29_log "batched-bench (cap ${left}s)"
    env -u LD_LIBRARY_PATH -u HSA_OVERRIDE_GFX_VERSION LD_LIBRARY_PATH="$BIN:/opt/rocm/lib" \
        OMP_PROC_BIND=spread OMP_PLACES=cores OMP_WAIT_POLICY=active OMP_DYNAMIC=false \
        "${pin[@]}" "$BIN/llama-batched-bench" -m "$DF29_TARGET" -fa on -ctk q8_0 -ctv q8_0 -kvu \
        -npp 2048 -ntg 128 -npl "$NPL" -c 9216 -b 2048 -ub 2048 -ngl 99 --device ROCm0 -t 8 \
        "${DF29_MMAP_FLAG[@]}" > "$OUT/batched_bench.txt" 2>&1 &
    bpid=$!; DF29_PIDS+=("$bpid")
    ( sleep "$left"; ps -p "$bpid" > /dev/null 2>&1 && kill -TERM "$bpid" ) &
    tpid=$!; DF29_PIDS+=("$tpid")
    set +e; wait "$bpid"; brc=$?; set -e
    df29_kill_pid "$tpid" 2 || true   # stop the timer first so it can never fire at a recycled PID
    df29_kill_pid "$bpid" 5 || true
    grep -E '^\|' "$OUT/batched_bench.txt" | sed 's/^/    /' || true
    nan=$(grep -c -i -E '\bnan\b|non-finite' "$OUT/batched_bench.txt" || true)
    BENCH_LINE="bench_rc=$brc bench_rows=$(grep -c -E '^\|[ ]+[0-9]' "$OUT/batched_bench.txt" || true) bench_nan_lines=$nan"
fi

SERVER_LINE="server=skipped"
if [ "$SERVER" = 1 ]; then
    mode=dflash2; [ "$DF29_HAS_DFLASH" = 0 ] && mode=target-only
    args=(-m "$DF29_TARGET" -np 4 -c 32768 -t 8 -ub 2048 --flash-attn on --jinja -ctk q8_0 -ctv q8_0 --kv-unified
          "${DF29_MMAP_FLAG[@]}" -ngl all --cache-ram 0 --chat-template-file "$DF29_TEMPLATE" --device ROCm0 --metrics --slots)
    [ "$mode" = dflash2 ] && args+=(-md "$DF29_DRAFTER" -ngld 99 --spec-type draft-dflash --spec-draft-n-max 7 --device-draft ROCm0)
    log=$OUT/server.log
    df29_start_server "$BIN" "$log" "$PORT" "${args[@]}"
    hdl=$(( $(date +%s) + 150 )); [ "$hdl" -gt "$DEADLINE" ] && hdl=$DEADLINE
    set +e; df29_wait_health "$PORT" "$hdl"; hrc=$?; set -e
    if [ "$hrc" -ne 0 ] && [ "$mode" = dflash2 ] && [ "$ARM" = M ]; then
        df29_log "arm M: DFlash2 server did not come up (rc=$hrc) -> target-only"; df29_stop_server
        mode=target-only
        args=(-m "$DF29_TARGET" -np 4 -c 32768 -t 8 -ub 2048 --flash-attn on --jinja -ctk q8_0 -ctv q8_0 --kv-unified
              "${DF29_MMAP_FLAG[@]}" -ngl all --cache-ram 0 --chat-template-file "$DF29_TEMPLATE" --device ROCm0 --metrics --slots)
        df29_start_server "$BIN" "$log" "$PORT" "${args[@]}"
        hdl=$(( $(date +%s) + 150 )); [ "$hdl" -gt "$DEADLINE" ] && hdl=$DEADLINE
        set +e; df29_wait_health "$PORT" "$hdl"; hrc=$?; set -e
    fi
    if [ "$hrc" -ne 0 ]; then
        SERVER_LINE="server=ERROR(start rc=$hrc) mode=$mode"
    else
        df29_server_maps "$DF29_SERVER_PID" > "$OUT/server_maps.txt" || true
        IFS=',' read -r -a CS <<< "$NPL"
        for c in "${CS[@]}"; do
            [ $((DEADLINE - $(date +%s))) -lt 20 ] && { df29_log "deadline: skipping conc=$c"; continue; }
            set +e
            python3 "$DF29_DIR/df29_client.py" --mode conc --conc "$c" --port "$PORT" --pid "$DF29_SERVER_PID" \
                --log "$log" --prompts "$DF29_DIR/prompts/server_prompts.json" --kinds orig --out "$OUT" \
                --sampling greedy --max-tokens "$MAXTOK" --req-timeout 90 --deadline "$DEADLINE" &
            cp=$!; DF29_PIDS+=("$cp"); wait "$cp"; set -e
        done
        nf=$(grep -c 'non-finite target features' "$log" || true)
        SERVER_LINE="mode=$mode nonfinite_log=$nf $(python3 - "$OUT/conc.jsonl" <<'PY'
import json, sys
try:
    rows = [json.loads(l) for l in open(sys.argv[1]) if l.strip()]
except OSError:
    rows = []
print(" ".join(f"c{r['conc']}:agg={r['agg_tok_s']}tok/s,acc={r['acceptance']},ok={r['ok']}/{r['n']},garbage={r['garbage']}" for r in rows) or "no-conc-rows")
PY
)"
    fi
    df29_stop_server
fi
df29_kill_pid "$DF29_SAMPLER_PID" 5 || true
read -r PEAK BASE < <(awk 'NR==1{b=$2} {if($2>m)m=$2} END{if(NR==0) print "NA NA"; else printf "%.2f %.2f\n", m/1073741824, b/1073741824}' "$OUT/vram_samples.txt")
LINE="E2E arm=$ARM $BENCH_LINE $SERVER_LINE vram_peak_gib=$PEAK vram_base_gib=$BASE wall=$(( $(date +%s) - T0 ))s"
echo "$LINE" | tee "$OUT/verdict.txt"
