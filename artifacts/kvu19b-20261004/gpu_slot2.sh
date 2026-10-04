#!/bin/bash
# gpu_slot2.sh — GPU validation of KVU-19b (FA masked-KV skip for BATCHED decode across sequences, --kv-unified),
# for ONE coordinated MI210 slot. Small loads only (peak about 3 GiB VRAM): no llama-server, no 27B.
# Run ONLY when the main session (workspace-ec) says the GPU is free. About 45-60 min.
# Results land in /mnt/raid0/llm/tmp/fa-maskskip-batched-20261004/slot2-<ts>/ (summary.txt first).
#
# Arms (all on the same harness binaries; only the libs and env knobs differ):
#   base  = champion 90c12df42 (unpatched)                      kernels/builds/gpu-20260929-90c12df42
#   k19a  = KVU-19a, per-tile skip only                          kernels/builds/gpu-20261003-a0d0ae238
#   on    = KVU-19b store build, defaults                        kernels/builds/gpu-20261004-c7f5ac9ad ($NEW)
#   seqoff= KVU-19b with GGML_CUDA_FA_SEQ_ROWS=0 (== KVU-19a behaviour, in-binary control)
#   skipoff/alloff = KVU-19b with GGML_CUDA_FA_MASK_SKIP=0 (exactness controls)
set -euo pipefail
T=/mnt/raid0/llm/tmp/fa-maskskip-batched-20261004
BASE=/mnt/raid0/llm/kernels/builds/gpu-20260929-90c12df42/bin
K19A=/mnt/raid0/llm/kernels/builds/gpu-20261003-a0d0ae238/bin
NEW=${NEW:-/mnt/raid0/llm/kernels/builds/gpu-20261004-c7f5ac9ad/bin}
GEMMA=/mnt/raid0/llm/models/gemma-3-1b-it-Q8_0.gguf     # head dim 256, like the 27B
OUT=$T/slot2-$(date -u +%Y%m%dT%H%M%SZ)
mkdir -p "$OUT"
RUN="taskset -c 160-183"
log() { echo "[$(date -u +%FT%TZ)] $*" | tee -a "$OUT/slot.log"; }
vram() { rocm-smi --showmeminfo vram 2>/dev/null | grep 'Used' | awk '{print $NF}' | head -n 1; }

[ -x "$NEW/llama-server" ] || { echo "FAIL: NEW=$NEW is not a build bin dir"; exit 1; }
log "VRAM before: $(vram)  NEW=$NEW"
/workspace/repos/epyc-inference-research/scripts/utils/verify_ggml_linkage.sh "$NEW/llama-batched-bench" > "$OUT/linkage.txt" 2>&1 \
    && log "linkage PASS" || { log "linkage FAIL (see linkage.txt)"; exit 1; }

# 1. Exactness (harness v2: the 64 KVU-19a cases + 34 multi-sequence cases with the n_seq hint).
#    on == skipoff bit-identical is THE criterion (skip on vs off). seqoff == k19a bit-identical (no regression).
#    on vs seqoff: bit-identical except the cases routed to the vec kernel (every row a different sequence).
log "1 exact"
cd "$T/harness"
./run_exact2.sh "$K19A" k19a    1 1
./run_exact2.sh "$NEW"  on      1 1
./run_exact2.sh "$NEW"  skipoff 0 1
./run_exact2.sh "$NEW"  seqoff  1 0
./run_exact2.sh "$NEW"  alloff  0 0
{
  echo "== on vs skipoff (skip on vs off, seq layouts on): must be all bit-identical";  python3 cmp2.py out_on out_skipoff exact_on.txt
  echo "== seqoff vs alloff (skip on vs off, seq layouts off): must be all bit-identical"; python3 cmp2.py out_seqoff out_alloff exact_on.txt
  echo "== seqoff vs k19a (new build with layouts off == KVU-19a): must be all bit-identical"; python3 cmp2.py out_seqoff out_k19a exact_on.txt
  echo "== on vs seqoff (layouts on vs off): bit-identical except vec-routed cases (hint >= nb, hs 128/256, not bf16)"; python3 cmp2.py out_on out_seqoff exact_on.txt
  for a in on seqoff k19a; do echo "== $a vs CPU reference (out_cpu, made CPU-side)"; python3 cmp2.py out_$a out_cpu exact_on.txt --ref; done
} > "$OUT/exact.txt" 2>&1
cp exact_*.txt "$OUT/"

# 2. Kernel micro-benchmark, 27B shape (hs 256, 4 KV heads, GQA 6, q8_0): single-sequence regression shapes and the
#    multi-sequence shapes (4 sequences x 16k/80k cells, 1 or 8 rows each, even/uneven, kvu vs per-sequence streams).
log "2 kernel perf"
rm -f perf2_results.txt
for r in 1 2 3; do
    for arm in base k19a on seqoff; do
        case $arm in
            base)   LIB=$BASE; SEQ=1 ;;
            k19a)   LIB=$K19A; SEQ=1 ;;
            on)     LIB=$NEW;  SEQ=1 ;;
            seqoff) LIB=$NEW;  SEQ=0 ;;
        esac
        GGML_CUDA_FA_SEQ_ROWS=$SEQ LD_LIBRARY_PATH=$LIB timeout 1800 $RUN ./fa_harness2 ROCm0 perf 1 100 2>/dev/null \
            | sed "s/^/round=$r arm=$arm /" >> perf2_results.txt
    done
done
cp perf2_results.txt "$OUT/perf2_results.txt"

# 3. Model level (gemma-3-1b, q8_0 KV): 4 sequences x 16k cells decoding in one batch per step.
#    draft 1 = batched decode; draft 8 = drafted verify of all 4; first_draft 1 = one decodes while 3 verify.
#    kvu=0 on the new build is the no-kvu reference the kvu arms should approach.
log "3 p3batch"
cd "$T/p3batch"
rm -f p3batch_results.txt
for r in 1 2 3; do
    for cfg in "1 1" "8 8" "8 1"; do
        set -- $cfg; D=$1; FD=$2
        for arm in k19a on seqoff nokvu; do
            case $arm in
                k19a)   LIB=$K19A; SEQ=1; KVU=1 ;;
                on)     LIB=$NEW;  SEQ=1; KVU=1 ;;
                seqoff) LIB=$NEW;  SEQ=0; KVU=1 ;;
                nokvu)  LIB=$NEW;  SEQ=1; KVU=0 ;;
            esac
            out=$(GGML_CUDA_FA_SEQ_ROWS=$SEQ LD_LIBRARY_PATH=$LIB timeout 900 $RUN ./p3batch "$GEMMA" 16384 4 100 "$D" "$KVU" q8_0 "$FD" 2>/dev/null | tail -n 1)
            echo "round=$r arm=$arm $out" >> p3batch_results.txt
        done
    done
done
cp p3batch_results.txt "$OUT/p3batch_results.txt"

# 4. llama-batched-bench, 4 concurrent decodes (KVU-19a slot shape), -kvu vs -no-kvu. Target: on -kvu S_TG ~ -no-kvu.
log "4 batched-bench"
for arm in base k19a on seqoff; do
    case $arm in
        base)   B=$BASE; SEQ=1 ;;
        k19a)   B=$K19A; SEQ=1 ;;
        on)     B=$NEW;  SEQ=1 ;;
        seqoff) B=$NEW;  SEQ=0 ;;
    esac
    for kvu in -kvu -no-kvu; do
        [ "$arm" = seqoff ] && [ "$kvu" = -no-kvu ] && continue
        GGML_CUDA_FA_SEQ_ROWS=$SEQ env -u LD_LIBRARY_PATH $RUN "$B/llama-batched-bench" -m "$GEMMA" -c 66560 -b 2048 -ub 2048 -ngl 99 -fa on \
            -ctk q8_0 -ctv q8_0 -dev ROCm0 $kvu -npp 16384 -ntg 128 -npl 4 --output-format jsonl \
            > "$OUT/bb_${arm}${kvu}.jsonl" 2> "$OUT/bb_${arm}${kvu}.log" || log "batched-bench $arm $kvu rc=$?"
    done
done

# 5. test-backend-ops FLASH_ATTN_EXT on the store build; the unified cases again with the scan forced for every n_kv
#    and with the per-sequence layouts off.
log "5 test-backend-ops"
TBO="OMP_NUM_THREADS=24 env -u LD_LIBRARY_PATH nice -n 19 $RUN $NEW/test-backend-ops test -o FLASH_ATTN_EXT -b ROCm0"
eval "$TBO" > "$OUT/tbo_flash_attn_ext.log" 2>&1 || log "test-backend-ops rc=$?"
eval "GGML_CUDA_FA_MASK_SKIP_MIN_KV=0 $TBO -p 'hint='" > "$OUT/tbo_unified_minkv0.log" 2>&1 || log "test-backend-ops minkv0 rc=$?"
eval "GGML_CUDA_FA_SEQ_ROWS=0 $TBO -p 'hint='" > "$OUT/tbo_unified_seqoff.log" 2>&1 || log "test-backend-ops seqoff rc=$?"
grep -h "tests passed" "$OUT"/tbo_*.log | tee -a "$OUT/slot.log"

# Summary
{
  echo "KVU-19b GPU slot summary ($OUT)"; echo
  echo "## exactness"; cat "$OUT/exact.txt" | grep -E "^==|cases"; echo
  echo "## kernel perf (median us/op over 3 rounds)"
  python3 - "$OUT/perf2_results.txt" <<'PY'
import re, sys, statistics, collections
d = collections.defaultdict(list)
for l in open(sys.argv[1]):
    m = re.match(r'round=\d+ arm=(\S+) perf (.*) : ([\d.]+) us/op', l)
    if m: d[(m.group(2), m.group(1))].append(float(m.group(3)))
shapes = sorted({k[0] for k in d}, key=lambda s: (s.split()[0], s))
arms = ['base', 'k19a', 'on', 'seqoff']
print('shape | ' + ' | '.join(arms))
for s in shapes:
    print(s + ' | ' + ' | '.join(f"{statistics.median(d[(s,a)]):.1f}" if d.get((s,a)) else '-' for a in arms))
PY
  echo; echo "## p3batch (tok/s, all rounds)"; cat "$OUT/p3batch_results.txt"
  echo; echo "## batched-bench S_TG / S_PP"
  for f in "$OUT"/bb_*.jsonl; do echo "$(basename "$f") $(python3 -c "import json,sys; d=json.loads(open('$f').read().strip().splitlines()[-1]); print('S_TG', round(d['speed_tg'],1), 'S_PP', round(d['speed_pp'],1))" 2>/dev/null)"; done
  echo; echo "## test-backend-ops"; grep -h "tests passed" "$OUT"/tbo_*.log
} > "$OUT/summary.txt" 2>&1

log "VRAM after: $(vram)"
log "done -> $OUT (summary.txt)"
