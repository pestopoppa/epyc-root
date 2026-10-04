#!/bin/bash
# gpu_slot_v11fa.sh — v11 FlashAttention routing A/B on the MI210 (gfx90a), ONE coordinated GPU slot.
# Run ONLY when workspace-ec has cleared the GPU (no :8083, no other GPU server). Hard budget 80 min (planned ~70).
# Results: /mnt/raid0/llm/tmp/v11-fa-ab-20261004/slot-<ts>/ ; read summary.txt first.
#
# Arms (one source = champion 90c12df42 unless noted; same harness binaries, libs chosen by LD_LIBRARY_PATH):
#   A   kernels/builds/gpu-20261004-90c12df42-A   rocWMMA FA ON  (champion recipe as is)
#   B   kernels/builds/gpu-20261004-90c12df42-B   rocWMMA FA OFF (exact v11 D=256 routing: TILE 3-32 rows, MMA >32)
#   C   kernels/builds/gpu-20261004-5026470c6-C   B + upstream #27870 (divergent barrier) + #28576 (fp32 VKQ on MFMA)
#   D   kernels/builds/gpu-20261004-fa5ebc0c8-D   C + CDNA D=256 MMA tuning (NCOLS_CAP.md), defaults: ncols2 by divisibility,
#       16-column cap (GQA 6 -> <256,256,8,2>, the only spill-free D=256 MMA config with fp32 VKQ)
#   D32 = D with GGML_CUDA_FA_CDNA_D256_MAX_COLS=32 (<256,256,16,2>)                                       [perf only]
#   D9  = D with GGML_CUDA_FA_CDNA_D256_MMA_MIN_ROWS=9 (MMA <8,2> instead of TILE for the 9-32-row band)    [perf only]
#   (gpu-20261004-2e0f9dd06-D = the superseded 32-column-only first cut; not used)
#   M   tmp/v11-fa-ab-20261004/build-master-11fe02151   plain upstream master (operator scope addition)
#   A+  (champion ON + picks) deliberately NOT built: PICKS_ON_ROUTE.md shows the ON champion never launches the MMA
#       kernel the picks touch for any production shape.
#
# Steps (DF2-9 on ALL arms first, as required):
#   (a) DF2-9:  a1 op-level nan/overflow probe (fa_v11 nan, CPU-exact refs)        ~1.5 min/arm
#               a2 model probe, no server (fa_nan_probe, 27B, FA outputs per R)     <= 2.5 min/arm
#               a3 server reproducer (df29_server.sh: orig 2026-08-27 cmd + prod)   <= 4.5 min/arm
#   (b) FA micro-bench (fa_v11 perf), 3 alternating rounds, arm order rotated per round   ~1 min/arm/round
#   (c) end to end (df2_e2e.sh: llama-batched-bench 27B np 1/2/4 + DFlash2 server C=1/2/4) — only if budget allows
#   (d) test-backend-ops -o FLASH_ATTN_EXT -b ROCm0 on B, C (+ D: gate for patch D), CPU reference under the region lock
#   then analyze_slot.py -> summary.txt + UPSTREAM-ISSUE-DRAFT.rendered.md (DRAFT ONLY, never posted)
#
# Hygiene: this script starts no server itself (the df29 scripts own and kill exactly their own PIDs); refuses to start
# if the GPU is busy; every arm's linkage is checked; every harness output carries the mapped libggml-hip path.
# env: SLOT_BUDGET_MIN (80), ARMS ("A B C D M"), SKIP_E2E=1, TBO_FULL=1 (no hsk filter), FORCE_GPU=1 (skip busy check)
set -uo pipefail

W=/mnt/raid0/llm/tmp/v11-fa-ab-20261004
H=$W/harness
DF=$W/df29
LOCK=/workspace/repos/epyc-orchestrator/scripts/region-lock
LINK=/workspace/repos/epyc-inference-research/scripts/utils/verify_ggml_linkage.sh
STORE=/mnt/raid0/llm/kernels/builds
declare -A DIR=(
    [A]=$STORE/gpu-20261004-90c12df42-A
    [B]=$STORE/gpu-20261004-90c12df42-B
    [C]=$STORE/gpu-20261004-5026470c6-C
    [D]=$STORE/gpu-20261004-fa5ebc0c8-D
    [M]=$W/build-master-11fe02151
)
ARMS=(${ARMS:-A B C D M})
BUDGET_S=$(( ${SLOT_BUDGET_MIN:-80} * 60 ))
T0=$(date +%s)
OUT=$W/slot-$(date -u +%Y%m%dT%H%M%SZ)
mkdir -p "$OUT"/{nan,det,probe,df29_server,perf,e2e,tbo}
log() { echo "[$(date -u +%FT%TZ) +$(( ($(date +%s) - T0) / 60 ))m] $*" | tee -a "$OUT/slot.log"; }
left() { echo $(( BUDGET_S - ($(date +%s) - T0) )); }
# fits <seconds>: true if that much budget remains (plus the reserve for step d)
RESERVE_D=${RESERVE_D:-600}
fits() { [ "$(left)" -ge $(( $1 + RESERVE_D )) ]; }
vram_used_mib() {
    local best=0 n
    for n in /sys/class/drm/card*/device; do
        [ -r "$n/mem_info_vram_total" ] || continue
        if [ "$(cat "$n/mem_info_vram_total")" -gt "$best" ]; then best=$(cat "$n/mem_info_vram_total"); used=$(cat "$n/mem_info_vram_used"); fi
    done
    echo $(( ${used:-0} / 1048576 ))
}

# ---------------------------------------------------------------- preflight
log "slot start, budget $((BUDGET_S / 60)) min, out=$OUT"
log "VRAM used before: $(vram_used_mib) MiB"
if [ "${FORCE_GPU:-0}" != 1 ] && [ "$(vram_used_mib)" -gt 4096 ]; then
    log "ABORT: GPU busy ($(vram_used_mib) MiB used). The slot needs the MI210 free (27B Q8_0 + drafter ~ 33 GiB)."
    exit 3
fi
for x in "$H/fa_v11" "$DF/fa_nan_probe" "$DF/df29_server.sh" "$DF/run_probe.sh" "$H/ref_cpu"; do
    [ -e "$x" ] || { log "ABORT: missing $x"; exit 2; }
done
: > "$OUT/arms.tsv"
GOOD=()
for a in "${ARMS[@]}"; do
    d=${DIR[$a]}
    if [ ! -x "$d/bin/llama-server" ] || [ ! -e "$d/bin/libggml-hip.so" ]; then log "arm $a: build missing ($d) — SKIPPED"; continue; fi
    if env -u LD_LIBRARY_PATH "$LINK" "$d/bin/llama-server" > "$OUT/linkage_$a.txt" 2>&1; then
        log "arm $a: linkage PASS ($(grep -m1 -o 'VERDICT rocwmma_fattn=[A-Z]*' "$d/PROVENANCE.md" 2>/dev/null))"
    else
        log "arm $a: linkage FAIL — SKIPPED (see linkage_$a.txt)"; continue
    fi
    [ "$a" = M ] && [ ! -x "$H/fa_v11_master" ] && log "arm M: fa_v11_master missing — op steps will report rc!=0 for M"
    GOOD+=("$a")
    printf '%s\t%s\t%s\n' "$a" "$d" "" >> "$OUT/arms.tsv"
done
printf '%s\t%s\t%s\n' "D32" "${DIR[D]}" "GGML_CUDA_FA_CDNA_D256_MAX_COLS=32" >> "$OUT/arms.tsv"
printf '%s\t%s\t%s\n' "D9" "${DIR[D]}" "GGML_CUDA_FA_CDNA_D256_MMA_MIN_ROWS=9" >> "$OUT/arms.tsv"
log "arms: ${GOOD[*]} (+ D32, D9 for perf)"

# ---------------------------------------------------------------- (a) DF2-9 on all arms
log "(a1) op-level nan/overflow probe"
for a in "${GOOD[@]}"; do
    FA_TIMEOUT=150 "$H/run_nan.sh" "${DIR[$a]}" "$OUT/nan/$a.txt" nan 2>&1 | tee -a "$OUT/slot.log"
done

log "(a2) model probe (fa_nan_probe, 27B, no server)"
for a in "${GOOD[@]}"; do
    pb=$DF/fa_nan_probe; [ "$a" = M ] && pb=$DF/fa_nan_probe_master
    if [ ! -x "$pb" ]; then log "probe $a: $pb missing — skipped"; continue; fi
    timeout 200 "$DF/run_probe.sh" "${DIR[$a]}" "$OUT/probe/$a" --arm "$a" --cap 150 --probe "$pb" 2>&1 | tail -n 1 | tee -a "$OUT/slot.log"
done

log "(a3) server reproducer (df29_server.sh: orig + prod)"
for a in "${GOOD[@]}"; do
    extra=(); [ "$a" = M ] && extra=(${DF29_M_ARGS:-})   # M: flags + target-only fallback are automatic in df29_server.sh
    timeout 300 "$DF/df29_server.sh" "${DIR[$a]}" "$OUT/df29_server/$a" --arm "$a" --cap 270 "${extra[@]}" 2>&1 \
        | grep -E '^DF29 ' | tee -a "$OUT/slot.log"
done
log "(a) done; VRAM now $(vram_used_mib) MiB"

# ---------------------------------------------------------------- (b) FA micro-bench, 3 alternating rounds
PERF_LABELS=("${GOOD[@]}")
for a in "${GOOD[@]}"; do [ "$a" = D ] && PERF_LABELS+=(D32 D9); done
n=${#PERF_LABELS[@]}
for r in 1 2 3; do
    if ! fits $(( n * 75 )); then log "(b) round $r skipped: budget"; break; fi
    log "(b) perf round $r"
    for i in $(seq 0 $((n - 1))); do
        lab=${PERF_LABELS[$(( (i + r - 1) % n ))]}
        arm=$lab; envs=()
        [ "$lab" = D9 ] && { arm=D; envs=(GGML_CUDA_FA_CDNA_D256_MMA_MIN_ROWS=9); }
        [ "$lab" = D32 ] && { arm=D; envs=(GGML_CUDA_FA_CDNA_D256_MAX_COLS=32); }
        env "${envs[@]}" FA_TIMEOUT=120 "$H/run_perf.sh" "${DIR[$arm]}" "$OUT/perf/${lab}_r$r.txt" 2>&1 | tee -a "$OUT/slot.log"
    done
done
# run-to-run bit-exactness of the never-before-shipped routes (TILE D=256 ncols2=2, MMA D=256/D=128): B, C, D only
for a in B C D; do
    [[ " ${GOOD[*]} " == *" $a "* ]] || continue
    if fits 120; then FA_TIMEOUT=120 "$H/run_nan.sh" "${DIR[$a]}" "$OUT/det/$a.txt" exact 2>&1 | tee -a "$OUT/slot.log"; fi
done

# ---------------------------------------------------------------- (c) end to end (optional)
if [ "${SKIP_E2E:-0}" != 1 ] && [ -x "$DF/df2_e2e.sh" ]; then
    for a in A B C D M; do
        [[ " ${GOOD[*]} " == *" $a "* ]] || continue
        if ! fits 330; then log "(c) e2e $a skipped: budget ($(left)s left)"; continue; fi
        log "(c) e2e $a"
        timeout 330 "$DF/df2_e2e.sh" "${DIR[$a]}" "$OUT/e2e/$a" --arm "$a" --cap 300 2>&1 | grep -E '^E2E ' | tee -a "$OUT/slot.log"
    done
fi

# ---------------------------------------------------------------- (d) test-backend-ops (CPU reference under the lock)
RESERVE_D=0
FILT=('-p' 'hsk=(128|256),')
[ "${TBO_FULL:-0}" = 1 ] && FILT=()
for a in B C D; do
    [[ " ${GOOD[*]} " == *" $a "* ]] || continue
    if ! fits 240; then log "(d) tbo $a skipped: budget ($(left)s left)"; continue; fi
    log "(d) test-backend-ops $a ${FILT[*]}"
    tl=$(( $(left) - 30 )); [ "$tl" -gt 900 ] && tl=900
    "$LOCK" run --cpu-list 0-95 --role build --tag v11fa --timeout-s 180 -- \
        env -u LD_LIBRARY_PATH LD_LIBRARY_PATH="${DIR[$a]}/bin" OMP_NUM_THREADS=24 \
        timeout "$tl" nice -n 19 taskset -c 0-23 "${DIR[$a]}/bin/test-backend-ops" test -o FLASH_ATTN_EXT -b ROCm0 "${FILT[@]}" \
        > "$OUT/tbo/$a.log" 2>&1
    rc=$?
    log "(d) tbo $a rc=$rc $(grep -h 'tests passed' "$OUT/tbo/$a.log" | tr '\n' ' ') fails=$(grep -c 'FAIL' "$OUT/tbo/$a.log")"
done

# ---------------------------------------------------------------- analysis
log "VRAM used after: $(vram_used_mib) MiB"
python3 "$W/analyze_slot.py" "$OUT" > "$OUT/analyze.log" 2>&1 || log "analyze_slot.py rc=$? (see analyze.log)"
log "done in $(( ($(date +%s) - T0) / 60 )) min -> $OUT/summary.txt"
