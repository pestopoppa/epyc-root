#!/bin/bash
# gpu_slot_fold.sh: GPU validation of the champion FOLD CANDIDATE
#   fold/champion-kvu19-20261004 = champion 90c12df42 + KVU-19a (ac97e305a GPU, a0d0ae238 CPU) + KVU-19b commit 1 (1bceceb05)
#   KVU-19b commit 2 (c7f5ac9ad, WMMA seq tiles) is deliberately NOT in this candidate.
#
# For workspace-ec, in ONE coordinated MI210 window (:8083 and every other GPU user down). Budget <= 20 min:
#   1 exactness (harness v1 + v2 on ROCm0)                   ~1.5 min   < 3 GiB VRAM
#   2 perf2 kernel micro-bench, 27B FA shape, 2 rounds       ~3.5 min   < 3 GiB
#   3 27B DFlash2 coherence smoke, paired, 3 arms            ~4-5 min   ~33 GiB (Qwen3.8-27B-Q8_0 + DFlash2 drafter)
#   4 [CPU half, under region-lock 0-95] test-backend-ops FLASH_ATTN_EXT on ROCm0 (CPU reference eval),
#     the unified cases again with MIN_KV=0 and with SEQ_ROWS=0, then all comparisons     ~8 min
# No llama-server. GPU host threads: harness on 160-183 (as the KVU-19a/19b slots), the 27B on 184-191 (canonical recipe).
# Results: /mnt/raid0/llm/tmp/champion-fold-kvu19-20261004/slot-<ts>/summary.txt (VERDICT line first).
#
# Env: FORCE=1 skips the "GPU must be idle" refusal. RL_TIMEOUT (s, default 900) bounds the region-lock wait for step 4;
#      on timeout step 4 is reported INCOMPLETE, never PASS.
set -euo pipefail
F=/mnt/raid0/llm/tmp/champion-fold-kvu19-20261004
H1=/mnt/raid0/llm/tmp/fa-maskskip-20261003/harness/fa_harness          # KVU-19a harness, 86 cases (read-only)
H2=/mnt/raid0/llm/tmp/fa-maskskip-batched-20261004/harness/fa_harness2  # KVU-19a+19b harness, 141 cases (read-only)
CPUREF=/mnt/raid0/llm/tmp/fa-maskskip-batched-20261004/harness/out_cpu  # v2 CPU reference (made CPU-side)
CHAMP=/mnt/raid0/llm/kernels/builds/gpu-20260929-90c12df42/bin         # current champion GPU build
K19A=/mnt/raid0/llm/kernels/builds/gpu-20261003-a0d0ae238/bin          # KVU-19a store build
CAND=${CAND:-/mnt/raid0/llm/kernels/builds/gpu-20261004-1bceceb05/bin} # fold candidate GPU store build
CANDCPU=$F/cpu/out_v2                                                   # candidate CPU build's v2 outputs (made CPU-side)
M27=/mnt/raid0/llm/models/Qwen3.8-27B-Q8_0.gguf
D27=/mnt/raid0/llm/models/Qwen3.8-27B-DFlash2-Q8_0.gguf
RL=/workspace/repos/epyc-orchestrator/scripts/region-lock
LV=/workspace/repos/epyc-inference-research/scripts/utils/verify_ggml_linkage.sh

# ---------------------------------------------------------------- step 4 (re-entered under region-lock)
if [ "${1:-}" = "__cpuhalf" ]; then
    OUT=$2
    cd "$OUT"
    TBO="OMP_NUM_THREADS=24 env -u LD_LIBRARY_PATH nice -n 19 taskset -c 0-95 $CAND/test-backend-ops test -o FLASH_ATTN_EXT -b ROCm0"
    set +e
    eval "$TBO" > tbo_flash_attn_ext.log 2>&1; echo "tbo full rc=$?"
    eval "GGML_CUDA_FA_MASK_SKIP_MIN_KV=0 $TBO -p 'n_seq=|hint='" > tbo_unified_minkv0.log 2>&1; echo "tbo unified MIN_KV=0 rc=$?"
    eval "GGML_CUDA_FA_SEQ_ROWS=0 $TBO -p 'hint='" > tbo_hint_seqoff.log 2>&1; echo "tbo hint SEQ_ROWS=0 rc=$?"
    eval "GGML_CUDA_FA_MASK_SKIP=0 $TBO -p 'n_seq=|hint='" > tbo_unified_skipoff.log 2>&1; echo "tbo unified SKIP=0 rc=$?"
    exit 0
fi

OUT=$F/slot-$(date -u +%Y%m%dT%H%M%SZ)
mkdir -p "$OUT/h"
log() { echo "[$(date -u +%FT%TZ)] $*" | tee -a "$OUT/slot.log"; }
vram() { cat /sys/class/drm/card*/device/mem_info_vram_used 2>/dev/null | sort -n | tail -n 1; }
kfd() { ls /sys/class/kfd/kfd/proc 2>/dev/null | grep -c . || true; }

# ---------------------------------------------------------------- 0 preflight
for d in "$CAND" "$CHAMP" "$K19A"; do [ -x "$d/llama-server" ] || { echo "FAIL: $d is not a build bin dir"; exit 1; }; done
[ -d "$CANDCPU" ] || { echo "FAIL: $CANDCPU missing (CPU-side half of the fold not run)"; exit 1; }
log "VRAM before: $(vram) bytes, KFD procs: $(kfd), CAND=$CAND"
if [ "$(kfd)" != 0 ] && [ "${FORCE:-0}" != 1 ]; then
    log "REFUSED: $(kfd) KFD process(es) already on the GPU; free the MI210 first (or FORCE=1)"; exit 3
fi
"$LV" "$CAND/llama-speculative-simple" "$(dirname "$CAND")" > "$OUT/linkage.txt" 2>&1 && log "linkage PASS" || { log "linkage FAIL"; exit 1; }
strings "$CAND/libggml-hip.so" | grep -E '^GGML_CUDA_FA_(MASK_SKIP|MASK_SKIP_MIN_KV|SEQ_ROWS)$' | sort > "$OUT/knobs.txt"
[ "$(wc -l < "$OUT/knobs.txt")" = 3 ] || { log "FAIL: libggml-hip.so lacks a fold knob: $(tr '\n' ' ' < "$OUT/knobs.txt")"; exit 1; }
if nm -C "$CAND/libggml-hip.so" 2>/dev/null | grep -q plan_seq_tiles || strings "$CAND/libggml-hip.so" | grep -q plan_seq_tiles; then
    log "FAIL: libggml-hip.so carries the KVU-19b commit-2 planner (plan_seq_tiles): wrong build"; exit 1
fi

# From here on: never abort mid-slot; every step logs its rc and the summary decides.
set +e

# ---------------------------------------------------------------- 1 exactness (GPU only)
log "1 exactness"
cd "$OUT/h"
ex2() { # tag lib skip seq
    rm -rf "out2_$1"; mkdir -p "out2_$1"
    GGML_CUDA_FA_MASK_SKIP=$3 GGML_CUDA_FA_SEQ_ROWS=$4 LD_LIBRARY_PATH=$2 FA_DUMP_DIR="out2_$1" \
        timeout 900 taskset -c 160-183 "$H2" ROCm0 exact 24 > "exact2_$1.txt" 2>/dev/null
    log "  v2 $1 rc=$? $(tail -n 1 "exact2_$1.txt")"
}
ex1() { # tag lib skip min_kv
    rm -rf "out1_$1"; mkdir -p "out1_$1"
    GGML_CUDA_FA_MASK_SKIP=$3 GGML_CUDA_FA_MASK_SKIP_MIN_KV=$4 LD_LIBRARY_PATH=$2 FA_DUMP_DIR="out1_$1" \
        timeout 900 taskset -c 160-183 "$H1" ROCm0 exact 24 > "exact1_$1.txt" 2>/dev/null
    log "  v1 $1 rc=$? $(tail -n 1 "exact1_$1.txt")"
}
ex2 k19a    "$K19A" 1 1
ex2 on      "$CAND" 1 1
ex2 skipoff "$CAND" 0 1
ex2 seqoff  "$CAND" 1 0
ex2 alloff  "$CAND" 0 0
ex1 on      "$CAND" 1 4096
ex1 skipoff "$CAND" 0 4096
ex1 minkv0  "$CAND" 1 0

# ---------------------------------------------------------------- 2 perf2 (GPU only)
log "2 perf2"
for r in 1 2; do
    for arm in champ on seqoff; do
        case $arm in champ) LIB=$CHAMP; SEQ=1 ;; on) LIB=$CAND; SEQ=1 ;; seqoff) LIB=$CAND; SEQ=0 ;; esac
        GGML_CUDA_FA_SEQ_ROWS=$SEQ LD_LIBRARY_PATH=$LIB timeout 600 taskset -c 160-183 "$H2" ROCm0 perf 1 100 2>/dev/null \
            | sed "s/^/round=$r arm=$arm /" >> "$OUT/perf2_results.txt" || log "  perf2 $arm r$r rc=$?"
    done
done

# ---------------------------------------------------------------- 3 27B DFlash2 coherence smoke (GPU; host 184-191)
#   champ  = current champion build                          (reference)
#   off    = candidate, MASK_SKIP=0 SEQ_ROWS=0               must be byte-identical to champ (THE criterion)
#   on     = candidate, defaults, MIN_KV=0 (forces the scan at this short n_kv)  expected byte-identical too
log "3 27B DFlash2 smoke"
PROMPT=$'<|im_start|>user\nIn three short sentences, explain why the sky is blue and why sunsets are red.<|im_end|>\n<|im_start|>assistant\n<think>\n\n</think>\n\n'
smoke() { # tag bin envs...
    local tag=$1 bin=$2; shift 2
    local peak=0
    ( while :; do v=$(vram); echo "$v" >> "$OUT/vram_$tag.txt"; sleep 2; done ) & local sp=$!
    env -u LD_LIBRARY_PATH "$@" timeout 600 taskset -c 184-191 "$bin/llama-speculative-simple" \
        -m "$M27" -md "$D27" --spec-type draft-dflash --spec-draft-n-max 8 -ngl 99 -ngld 99 -dev ROCm0 -devd ROCm0 \
        -c 4096 -b 2048 -ub 2048 -ctk f16 -ctv f16 -fa on -t 8 --temp 0 --top-k 1 -s 42 -n 160 -p "$PROMPT" \
        > "$OUT/smoke_$tag.out" 2> "$OUT/smoke_$tag.err" || log "  smoke $tag rc=$?"
    kill "$sp" 2>/dev/null; wait "$sp" 2>/dev/null || true
    ps -p "$sp" > /dev/null 2>&1 && kill -9 "$sp" 2>/dev/null || true
    peak=$(sort -n "$OUT/vram_$tag.txt" | tail -n 1)
    log "  smoke $tag sha256=$(sha256sum < "$OUT/smoke_$tag.out" | cut -c1-16) bytes=$(wc -c < "$OUT/smoke_$tag.out") peakVRAM=$peak $(grep -E 'decoded|accept ' "$OUT/smoke_$tag.err" | tr '\n' ' ')"
}
smoke champ "$CHAMP"
smoke off   "$CAND" GGML_CUDA_FA_MASK_SKIP=0 GGML_CUDA_FA_SEQ_ROWS=0
smoke on    "$CAND" GGML_CUDA_FA_MASK_SKIP_MIN_KV=0

# ---------------------------------------------------------------- 4 CPU half under the region lock
log "4 test-backend-ops (region-lock 0-95, timeout ${RL_TIMEOUT:-900}s)"
TBO_STATE=done
"$RL" run --cpu-list 0-95 --role build --tag champion-fold --timeout-s "${RL_TIMEOUT:-900}" -- \
    "$F/gpu_slot_fold.sh" __cpuhalf "$OUT" 2>&1 | tee -a "$OUT/slot.log" || TBO_STATE=incomplete
grep -q "tbo full rc" "$OUT/slot.log" || TBO_STATE=incomplete
log "VRAM after: $(vram) bytes, KFD procs: $(kfd)"

# ---------------------------------------------------------------- summary (pure text processing)
cd "$OUT"
C="python3 $F/cmp_fold.py"
V=PASS
chk() { local name=$1; shift; local r; r=$("$@" 2>&1) || V=FAIL; echo "$name: $r"; }
{
  echo "## exactness (harness v2, $(grep -c '^case' h/exact2_on.txt) cases listed)"
  chk "E1 skip on == skip off (seq rows on)  [criterion]" $C h/exact2_on.txt ident h/out2_on h/out2_skipoff
  chk "E2 skip on == skip off (seq rows off) [criterion]" $C h/exact2_on.txt ident h/out2_seqoff h/out2_alloff
  chk "E3 SEQ_ROWS=0 == KVU-19a build         [criterion]" $C h/exact2_on.txt ident h/out2_seqoff h/out2_k19a
  chk "E4 seq rows on vs off: only vec-routed cases differ" $C h/exact2_on.txt vec_only h/out2_on h/out2_seqoff
  chk "E5 on vs CPU reference (19b out_cpu)  nmse<5e-4" $C h/exact2_on.txt ref h/out2_on "$CPUREF"
  chk "E6 on vs candidate CPU build          nmse<5e-4" $C h/exact2_on.txt ref h/out2_on "$CANDCPU"
  chk "E7 seqoff vs candidate CPU build      nmse<5e-4" $C h/exact2_on.txt ref h/out2_seqoff "$CANDCPU"
  echo "## exactness (harness v1, KVU-19a gate 3: ALL hash skip on == off)"
  a=$(tail -n 1 h/exact1_on.txt); b=$(tail -n 1 h/exact1_skipoff.txt); c=$(tail -n 1 h/exact1_minkv0.txt)
  if [ -n "$a" ] && [ "$a" = "$b" ] && [ "$a" = "$c" ] && [[ "$a" == ALL* ]]; then echo "E8 PASS v1 $a (on == skipoff == minkv0)"; else V=FAIL; echo "E8 FAIL v1 on='$a' skipoff='$b' minkv0='$c'"; fi
  echo
  echo "## 27B DFlash2 coherence smoke (greedy, 160 tokens)"
  hc=$(sha256sum < smoke_champ.out | cut -d' ' -f1); ho=$(sha256sum < smoke_off.out | cut -d' ' -f1); hn=$(sha256sum < smoke_on.out | cut -d' ' -f1)
  # S2 is exact by construction (the skip never changes arithmetic): any difference is a fold defect.
  if [ "$(wc -c < smoke_off.out)" -gt 100 ] && [ "$hn" = "$ho" ]; then echo "S2 PASS candidate skip on (MIN_KV=0) byte-identical to candidate skip off ($ho)"; else V=FAIL; echo "S2 FAIL candidate on=$hn off=$ho (or empty output)"; fi
  # S1: candidate (skip off) vs the current champion. Expected identical: the 27B's attention is hs=256, where the
  # KVU-19a slot found champion == 19a bit-identical. KVU-19a DOES change arithmetic order for hs=128 WMMA nb=32,
  # hs=40 and hs=192 shapes even with skip off (nmse <= 3e-7, slot-20261004T022552Z exact.txt), so a divergence is
  # not proof of a defect: it is reported DIVERGED (verdict INCOMPLETE -> read the two texts) rather than FAIL.
  if [ "$(wc -c < smoke_champ.out)" -gt 100 ] && [ "$hc" = "$ho" ]; then echo "S1 PASS candidate(skip off) byte-identical to champion ($hc)"
  elif [ "$(wc -c < smoke_champ.out)" -le 100 ]; then V=FAIL; echo "S1 FAIL champion output empty/short: broken probe"
  else
      off=$(cmp smoke_champ.out smoke_off.out 2>/dev/null | grep -oE 'byte [0-9]+' | cut -d' ' -f2)
      echo "S1 DIVERGED candidate(skip off) vs champion at byte ${off:-?} of $(wc -c < smoke_champ.out): review both texts below (coherent = acceptable FP reordering)"
      [ "$V" = FAIL ] || V=INCOMPLETE
      echo "  text (candidate off):"; sed 's/^/    | /' smoke_off.out | head -n 20
  fi
  for t in champ off on; do echo "  $t: $(grep -E 'decoded|accept ' smoke_$t.err | tr '\n' ' ') peakVRAM=$(sort -n vram_$t.txt | tail -n 1) $(grep -m1 -oE 'offloaded [0-9]+/[0-9]+ layers to GPU' smoke_$t.err)"; done
  echo "  text (champ):"; sed 's/^/    | /' smoke_champ.out | head -n 20
  echo
  echo "## test-backend-ops FLASH_ATTN_EXT ROCm0 ($TBO_STATE)"
  for f in tbo_flash_attn_ext tbo_unified_minkv0 tbo_hint_seqoff tbo_unified_skipoff; do
      if [ -s "$f.log" ]; then
          line=$(sed 's/\x1b\[[0-9;]*m//g' "$f.log" | grep -E '[0-9]+/[0-9]+ tests passed' | head -n 1)
          nf=$(sed 's/\x1b\[[0-9;]*m//g' "$f.log" | grep -c 'FAIL' || true)
          if [ -n "$line" ] && [ "$nf" = 0 ]; then echo "T PASS $f: $line"; else V=FAIL; echo "T FAIL $f: '${line:-no tally}' FAIL-lines=$nf"; fi
      else
          [ "$V" = FAIL ] || V=INCOMPLETE; echo "T INCOMPLETE $f: not run"
      fi
  done
  echo
  echo "## perf2 (median us/op over 2 rounds; informational, expectations in FOLD-CANDIDATE.md)"
  python3 - perf2_results.txt <<'PY'
import re, sys, statistics, collections
d = collections.defaultdict(list)
for l in open(sys.argv[1]):
    m = re.match(r'round=\d+ arm=(\S+) perf (.*) : ([\d.]+) us/op', l)
    if m: d[(m.group(2), m.group(1))].append(float(m.group(3)))
arms = ['champ', 'on', 'seqoff']
print('shape | ' + ' | '.join(arms))
for s in sorted({k[0] for k in d}, key=lambda s: (s.split()[0], s)):
    print(s + ' | ' + ' | '.join(f"{statistics.median(d[(s,a)]):.1f}" if d.get((s,a)) else '-' for a in arms))
PY
} > "$OUT/summary.body" 2>&1 < /dev/null
{ echo "VERDICT $V  fold candidate $(basename "$(dirname "$CAND")")  ($OUT)"; echo; cat summary.body; } > summary.txt
rm -f summary.body
log "done -> $OUT/summary.txt : VERDICT $V"
