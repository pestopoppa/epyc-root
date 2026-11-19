#!/bin/bash
set -euo pipefail
D=$(cd -- "$(dirname -- "$0")" && pwd -P)
IK=/mnt/raid0/llm/ik_llama.cpp
SRC=${EXP01_RECOVERY_SRC:?}
SRC_SIZE=${EXP01_RECOVERY_SRC_SIZE:?}
SRC_SHA=${EXP01_RECOVERY_SRC_SHA:?}
ROW_ID=vidya-exp01-proxy-input-recovery-20261118
# imatrix (2026-11-03): IQ2_KT / IQ2_XXS refuse to quantize without one, so the row GENERATES it (unit "imatrix", part of this row's compute)
# from a pinned calibration text (wikitext-2 test split, copied from /mnt/raid0/llm/data/wiki.test.raw) and EVERY arm uses that same file.
CALIB=$D/calib/wiki.test.raw
CALIB_SHA=bfe9eb16ab9987fb88bde4ea9a30a00f2a45db01dfc14bad78d05325789c4f12
IMAT_CHUNKS=${EXP01_RECOVERY_CHUNKS:?}; IMAT_CTX=512     # -no-fug/-no-fmoe: fused up-gate hid every ffn_gate tensor from the r3 imatrix; whole pinned calib (~580 x 512): 32 chunks left MoE experts unrouted (r2: no imatrix for blk.38.ffn_down_exps)
OUT=${EXP01_RECOVERY_OUT:?}; M=$OUT/models; R=$OUT/results.jsonl; IMAT=$OUT/imatrix.dat
STOP=${FILLER_STOPFILE:-$OUT/STOP}
CPUS=${FILLER_CPUS:?}; NT=${FILLER_THREADS:?}
mkdir -p "$OUT" "$M"; touch "$R"
export LD_LIBRARY_PATH="$IK/build/ggml/src:$IK/build/src"   # own ggml (three-generation hazard)
Q="$IK/build/bin/llama-quantize"
QUANT_ARGS=(--imatrix "$IMAT")
if [[ ${EXP01_RECOVERY_MODE:?} == smoke ]]; then
  QUANT_ARGS+=(--custom-q '^blk[.]0[.]ffn_up[.]weight$=iq4_kt,.*=q8_0')
fi
have() { grep "\"unit\": *\"$1\"" "$R" 2>/dev/null | grep -E '"rc": 0[,}]|"ok": true' >/dev/null; }   # only a SUCCESSFUL unit counts as done (2026-11-03: a failed unit used to be skipped on resume)
emit() { python3 -c 'import json,sys; print(json.dumps(json.loads(sys.argv[1])))' "$1" >> "$R"; }
stopping() { [ -e "$STOP" ] || [ "$(date +%s)" -ge "$FILLER_DEADLINE" ]; }
bounded() {
  local limit=$1 remaining
  shift
  remaining=$((FILLER_DEADLINE - $(date +%s)))
  [ "$remaining" -gt 0 ] && [ ! -e "$STOP" ] || return 124
  [ "$limit" -le "$remaining" ] || limit=$remaining
  timeout --foreground --kill-after=10s "$limit" taskset -c "$CPUS" "$@"
}

# ---- unit 0: preflight (cheap; also the smoke's first unit) ----
if ! have preflight; then
  sz=$(stat -c %s "$SRC"); free_gib=$(df -BG --output=avail "$M" | tail -1 | tr -dc 0-9)
  commit=$(git -C "$IK" rev-parse HEAD); dirty=$(git -C "$IK" status --porcelain --untracked-files=no | wc -l)
  csha=$(sha256sum "$CALIB" | cut -d' ' -f1); ok=true; [ "$csha" = "$CALIB_SHA" ] || ok=false; [ -x "$IK/build/bin/llama-imatrix" ] || ok=false
  [ "$sz" = "$SRC_SIZE" ] || ok=false; [ "$free_gib" -ge 70 ] || ok=false; [ "$dirty" = 0 ] || ok=false
  [ "$commit" = c04881fc0f31dae5f8ec59c1d683889f0c9dfa11 ] || ok=false
  emit "{\"unit\":\"preflight\",\"kind\":\"build\",\"ok\":$ok,\"src\":\"$SRC\",\"src_size\":$sz,\"src_size_pinned\":$SRC_SIZE,\"src_sha256_pinned\":\"$SRC_SHA\",\"free_gib\":$free_gib,\"need_gib\":70,\"ik_commit\":\"$commit\",\"ik_tracked_dirty\":$dirty,\"calib\":\"$CALIB\",\"calib_sha256\":\"$csha\",\"calib_sha256_pinned\":\"$CALIB_SHA\",\"cpus\":\"$CPUS\",\"threads\":$NT,\"caveat\":\"requant-from-Q8_0 and ONE shared imatrix (generated in this row from the pinned calibration text, $IMAT_CHUNKS x $IMAT_CTX tokens, computed on the Q8_0 source) used by EVERY arm; no --ignore-imatrix-rules\"}"
  if [ "$ok" != true ]; then echo "preflight FAILED (see $R)"; exit 3; fi
fi
python3 -c 'import json,sys; v=[json.loads(l) for l in open(sys.argv[1]) if "\"preflight\"" in l][-1]; sys.exit(0 if v["ok"] else 1)' "$R" || { echo "preflight not ok"; exit 3; }
rm -f "$M"/.partial-*.gguf

# ---- plan units: llama-quantize --dry-run (writes nothing) per KT type, so a type/arch/shape defect fails in seconds, not 28 min in ----
plan() { # $1 type  $2 arm  $3 timeout_s
  local u="plan-$2" s e rc=0 q
  have "$u" && return 0
  s=$(date +%s.%N)
  bounded "$3" "$Q" --dry-run --allow-requantize "${QUANT_ARGS[@]}" "$SRC" "$OUT/plan-$2.gguf" "$1" "$NT" > "$OUT/$u.log" 2>&1 || rc=$?
  e=$(date +%s.%N); q=$(grep -m1 "quant size" "$OUT/$u.log" | tr -d '"' | cut -c1-160 || true)
  emit "{\"unit\":\"$u\",\"kind\":\"build-plan\",\"arm\":\"$2\",\"type\":\"$1\",\"rc\":$rc,\"duration_s\":$(python3 -c "print(round($e-$s,1))"),\"note\":\"$q\"}"
  [ "$rc" = 0 ] || { echo "$u FAILED rc=$rc (see $OUT/$u.log)"; exit 4; }
}

# ---- unit: imatrix (the compute that unblocks IQ2_KT / IQ2_XXS). llama-imatrix on the Q8_0 source, CPU, pinned calibration text, bounded ----
if ! { have imatrix && [ -s "$IMAT" ]; }; then
  stopping && { echo "stop/deadline before imatrix"; exit 4; }
  s=$(date +%s.%N); rc=0; rm -f "$IMAT.partial"
  bounded 3000 "$IK/build/bin/llama-imatrix" -m "$SRC" -f "$CALIB" -o "$IMAT.partial" --chunks "$IMAT_CHUNKS" -c "$IMAT_CTX" -b "$IMAT_CTX" -ub "$IMAT_CTX" -t "$NT" --no-ppl -no-fug -no-fmoe > "$OUT/imatrix.log" 2>&1 || rc=$?
  e=$(date +%s.%N)
  if [ "$rc" = 0 ] && [ -s "$IMAT.partial" ]; then mv "$IMAT.partial" "$IMAT"; elif [ "$rc" = 0 ]; then rc=5; fi
  isz=$(stat -c %s "$IMAT" 2>/dev/null || echo 0); ish=$([ "$isz" -gt 0 ] && sha256sum "$IMAT" | cut -d' ' -f1 || echo none)
  emit "{\"unit\":\"imatrix\",\"kind\":\"build-imatrix\",\"rc\":$rc,\"duration_s\":$(python3 -c "print(round($e-$s,1))"),\"threads\":$NT,\"cpus\":\"$CPUS\",\"calib\":\"$CALIB\",\"calib_sha256\":\"$CALIB_SHA\",\"chunks\":$IMAT_CHUNKS,\"ctx\":$IMAT_CTX,\"out\":\"$IMAT\",\"size\":$isz,\"sha256\":\"$ish\"}"
  [ "$rc" = 0 ] || { echo "imatrix FAILED rc=$rc (see $OUT/imatrix.log)"; exit 4; }
fi
plan IQ4_KT IQ4KT-im 900
if [[ ${EXP01_RECOVERY_MODE:?} == official ]]; then
  plan IQ2_KT IQ2KT-im 900
fi

# ---- arms: cheap first, so a short window still yields the control + the 2-bit control ----
ARMS="Q4KM:Q4_K_M:Qwen3.6-35B-A3B-Q4_K_M IQ2XXS:IQ2_XXS:Qwen3.6-35B-A3B-IQ2_XXS IQ4KT:IQ4_KT:Qwen3.6-35B-A3B-IQ4_KT IQ2KT:IQ2_KT:Qwen3.6-35B-A3B-IQ2_KT"
if [[ $EXP01_RECOVERY_MODE == smoke ]]; then
  ARMS="IQ4KT:IQ4_KT:Qwen3-0.6B-IQ4_KT"
fi
for a in $ARMS; do
  arm=${a%%:*}; rest=${a#*:}; ty=${rest%%:*}; name=${rest#*:}; u="quant-$arm"
  have "$u" && continue
  stopping && { echo "stop/deadline before $u"; exit 4; }
  s=$(date +%s.%N); rc=0
  bounded 5400 "$Q" --allow-requantize "${QUANT_ARGS[@]}" "$SRC" "$M/.partial-$name.gguf" "$ty" "$NT" > "$OUT/$u.log" 2>&1 || rc=$?
  e=$(date +%s.%N)
  if [ "$rc" = 0 ]; then mv "$M/.partial-$name.gguf" "$M/$name.gguf"; fi
  sz=$(stat -c %s "$M/$name.gguf" 2>/dev/null || echo 0)
  emit "{\"unit\":\"$u\",\"kind\":\"build\",\"arm\":\"$arm\",\"type\":\"$ty\",\"rc\":$rc,\"duration_s\":$(python3 -c "print(round($e-$s,1))"),\"threads\":$NT,\"cpus\":\"$CPUS\",\"out\":\"$M/$name.gguf\",\"size\":$sz,\"extra\":\"${QUANT_ARGS[*]}\"}"
  [ "$rc" = 0 ] || { echo "$u FAILED rc=$rc"; exit 4; }
done

if [[ $EXP01_RECOVERY_MODE == smoke ]]; then
  exit 0
fi

# ---- all four present: the manifest precond.sh gates on (size+mtime only; sha256 is pinned outside the grant) ----
python3 - "$M" "$R" "$OUT/BUILD-DONE.json" "$ROW_ID" "$IMAT" <<'PY'
import json, os, sys
m, r, out = sys.argv[1:4]
names = {"Q4KM": "Q4_K_M", "IQ2XXS": "IQ2_XXS", "IQ4KT": "IQ4_KT", "IQ2KT": "IQ2_KT"}
d = {}
for arm, t in names.items():
    p = f"{m}/Qwen3.6-35B-A3B-{t}.gguf"; st = os.stat(p)
    d[arm] = {"path": p, "size": st.st_size, "mtime": int(st.st_mtime)}
tmp = out + ".tmp"; json.dump({"unit": "build-done", "row": sys.argv[4], "imatrix": sys.argv[5], "arms": d}, open(tmp, "w"), indent=1); os.replace(tmp, out)
print(json.dumps({"unit": "build-done", "arms": list(d)}), file=open(r, "a"))
PY
echo "BUILD-DONE"
