#!/bin/bash
#maxjob_s=6000
# T3 speed screen for CH-19 (fused MoE up+gate+SwiGLU, --cpu-fused-moe-upgate on|off).
# NOT a queue job for the correctness runner: it is TIMING and runs ONLY inside an exclusive
# full-host CPU window. Every arm goes through bench_canonical.sh (the only sanctioned llama-bench
# entry point), which takes its own `region-lock run --cpu-list 0-95 --role bench-canonical` claim
# per invocation (waits for it), pre-evicts 40 GiB/NUMA node, and requires an in-window placement proof.
#
# Design (predeclared):
#   model   Qwen3.6-35B-A3B-MTP-Q8_0 (frontdoor; separate ffn_gate_exps/ffn_up_exps, so the fusion applies)
#   recipe  canonical_recipe.py: taskset -c 0-95 numactl --interleave=all, -t 96 -fa 1 -mmp 0,
#           OMP_PROC_BIND=spread OMP_PLACES=cores OMP_WAIT_POLICY=active OMP_DYNAMIC=false,
#           GGML_IQK=1 GGML_IQK_Q8_0=1; llama-bench default -b 2048 -ub 512
#   tests   pp512 and tg128 at depth 0 and depth 8192 (-d 0,8192)
#   arms    OFF = --cpu-fused-moe-upgate off, ON = --cpu-fused-moe-upgate on; same binary, same process recipe
#   order   strict ABAB: PAIRS x (OFF, ON), one llama-bench process per arm, -r REPS inside each
#           -> each arm gets PAIRS*REPS reps (default 5*3 = 15) from PAIRS independent processes
#   valid   ON arm: "[iqk] ACTIVE: fused MoE up+gate" MUST be in that arm's log, else INVALID.
#           OFF arm: the marker MUST be absent, else INVALID. wrapper rc != 0 (incl. placement skew) -> INVALID.
#   verdict per test: median over valid pairs of (ON t/s / OFF t/s); keep only if the gain is >= the
#           window noise floor (measured same-window; not decided here).
# Preflight: one short ON invocation (-p 0 -n 8 -r 1); no marker -> abort before spending the window.
#
# Duration estimate (honest, unmeasured for this build): per arm invocation ~ pre-evict 30-60 s +
# load 35 GB (-mmp 0) 20-40 s + pp512/tg128 at d0 (4 runs each incl. warmup, ~35 s) + d8192
# (the 8192-token depth is re-prefilled before every run: ~4 x 2 x 30 s = ~250 s) ~= 5.5-6.5 min.
# 10 arm invocations + preflight (~2 min) ~= 60-70 min; budget 100 min (maxjob_s=6000).
set -euo pipefail
ulimit -c 0

PAIRS=${PAIRS:-5}
REPS=${REPS:-3}
DEPTHS=${DEPTHS:-0,8192}
S=/mnt/raid0/llm/worktrees/intake-fixes-20261020
B=$S/build-ch19/bin
MODEL=/mnt/raid0/llm/models/Qwen3.6-35B-A3B-MTP-Q8_0.gguf
BENCH=/mnt/raid0/llm/epyc-inference-research/scripts/benchmark/bench_canonical.sh
EXPECT_COMMIT=57d96e2cb61d6f1e8772c25b42e5bf31e6f9af47
MARK="fused MoE up+gate"
OUT=/mnt/raid0/llm/tmp/intake-fixes-20261020/t3-ch19-screen/$(date -u +%Y%m%dT%H%M%SZ)
mkdir -p "$OUT"
REC="$OUT/records.jsonl"

for f in "$B/llama-bench" "$B/libggml-cpu.so" "$MODEL" "$BENCH"; do [ -e "$f" ] || { echo "DEP_MISSING $f"; exit 3; }; done
HEAD=$(git -C "$S" rev-parse HEAD)
[ "$HEAD" = "$EXPECT_COMMIT" ] || echo "NOTE: worktree HEAD $HEAD != build commit $EXPECT_COMMIT (binary provenance below is what counts)"
BUILT_FROM=$(grep -m1 -oE 'src=[0-9a-f]{40}' /mnt/raid0/llm/tmp/intake-fixes-20261020/ch19-t3-build.log | cut -d= -f2 || true)
BIN_SHA=$(sha256sum "$(readlink -f "$B/llama-bench")" | cut -d' ' -f1)
CPU_SHA=$(sha256sum "$(readlink -f "$B/libggml-cpu.so")" | cut -d' ' -f1)
LLAMA_SHA=$(sha256sum "$(readlink -f "$B/libllama.so")" | cut -d' ' -f1)
# grep -c, not grep -q: -q exits early, strings takes SIGPIPE and pipefail turns a hit into a failure
[ "$(strings -a "$(readlink -f "$B/libggml-cpu.so")" | grep -c ggml_backend_cpu_set_fused_moe_upgate)" -gt 0 ] \
    || { echo "FAIL: libggml-cpu.so has no ggml_backend_cpu_set_fused_moe_upgate (stale build)"; exit 1; }
cat > "$OUT/provenance.json" <<EOF
{"built_from": "$BUILT_FROM", "worktree_head": "$HEAD", "llama_bench_sha256": "$BIN_SHA",
 "libggml_cpu_sha256": "$CPU_SHA", "libllama_sha256": "$LLAMA_SHA", "model": "$MODEL",
 "pairs": $PAIRS, "reps": $REPS, "depths": "$DEPTHS", "start": "$(date -u +%FT%TZ)"}
EOF
echo "out=$OUT built_from=$BUILT_FROM bench_sha=$BIN_SHA cpu_sha=$CPU_SHA"

# arm <tag> <on|off> <depths> <wrapper args...>: one bench_canonical.sh invocation (-p/-n/-r are wrapper
# options; -d must go after `--`, which REPLACES the wrapper's extra-arg list); writes $OUT/<tag>/{run.log,bench.jsonl}
DRYFLAG=(); [ "${DRY:-0}" = 1 ] && DRYFLAG=(--dry-run)   # DRY=1: validate wiring only, no inference
arm() {
    local tag=$1 sw=$2 depths=$3; shift 3
    local d="$OUT/$tag"; mkdir -p "$d"
    local rc=0
    "$BENCH" -m "$MODEL" "$@" --binary "$B/llama-bench" --source-root "$S" --library-path "$B" \
        --ggml-iqk 1 --ggml-iqk-q8-0 1 --log-dir "$d/canonical" "${DRYFLAG[@]}" \
        -- -d "$depths" --cpu-fused-moe-upgate "$sw" -o jsonl > "$d/run.log" 2>&1 || rc=$?
    local has=0; grep -q "$MARK" "$d/run.log" && has=1
    grep -E '^\{' "$d/run.log" > "$d/bench.jsonl" || true
    local valid=1 why=ok
    if [ "$rc" -ne 0 ]; then valid=0; why="wrapper_rc=$rc"; fi
    if [ "$sw" = on ]  && [ "$has" -ne 1 ]; then valid=0; why="ON arm without fused marker"; fi
    if [ "$sw" = off ] && [ "$has" -ne 0 ]; then valid=0; why="OFF arm with fused marker"; fi
    [ -s "$d/bench.jsonl" ] || { valid=0; why="no jsonl rows"; }
    python3 - "$d/bench.jsonl" "$REC" "$tag" "$sw" "$has" "$valid" "$why" "$rc" "$BIN_SHA" "$CPU_SHA" "$BUILT_FROM" <<'PY'
import json, sys
src, rec, tag, sw, has, valid, why, rc, bsha, csha, built = sys.argv[1:]
rows = [json.loads(l) for l in open(src) if l.strip()] or [{}]
with open(rec, "a") as f:
    for r in rows:
        f.write(json.dumps({"arm": tag, "switch": sw, "marker": int(has), "valid": int(valid), "why": why,
            "wrapper_rc": int(rc), "llama_bench_sha256": bsha, "libggml_cpu_sha256": csha, "built_from": built,
            "n_prompt": r.get("n_prompt"), "n_gen": r.get("n_gen"), "n_depth": r.get("n_depth"),
            "cpu_fused_moe_upgate_field": r.get("cpu_fused_moe_upgate"), "avg_ts": r.get("avg_ts"),
            "stddev_ts": r.get("stddev_ts"), "samples_ts": r.get("samples_ts"), "raw": r}) + "\n")
PY
    echo "$(date -u +%FT%TZ) $tag switch=$sw marker=$has valid=$valid ($why)"
    return 0
}

# Preflight: prove the ON path engages on this model before spending the window.
arm preflight-on on 0 -p 0 -n 8 -r 1
if [ "${DRY:-0}" != 1 ] && ! grep -q "$MARK" "$OUT/preflight-on/run.log"; then
    echo "ABORT: preflight ON arm shows no fused marker -- the fusion does not engage on $MODEL; no timing run."
    echo "RESULT t3-ch19-screen pass=0 fail=1"; exit 1
fi

for p in $(seq 1 "$PAIRS"); do
    arm "p$p-A-off" off "$DEPTHS" -p 512 -n 128 -r "$REPS"
    arm "p$p-B-on"  on  "$DEPTHS" -p 512 -n 128 -r "$REPS"
done

python3 - "$REC" "$OUT/summary.txt" <<'PY'
import json, sys, statistics as st
rows = [json.loads(l) for l in open(sys.argv[1])]
rows = [r for r in rows if not r["arm"].startswith("preflight")]
key = lambda r: (r["n_prompt"], r["n_gen"], r["n_depth"])
out = []
inval = sorted({r["arm"] + ": " + r["why"] for r in rows if not r["valid"]})
out.append(f"invalid arms: {len(inval)}" + "".join("\n  " + x for x in inval))
tests = sorted({key(r) for r in rows if r["valid"] and r["avg_ts"] is not None}, key=lambda k: (k[2] or 0, k[1] or 0))
for k in tests:
    name = (f"pp{k[0]}" if k[0] else f"tg{k[1]}") + f" @ d{k[2]}"
    per = {}
    for r in rows:
        if r["valid"] and key(r) == k and r["avg_ts"] is not None:
            pair = r["arm"].split("-")[0]
            per.setdefault(pair, {})[r["switch"]] = r["avg_ts"]
    ratios = [v["on"] / v["off"] for v in per.values() if "on" in v and "off" in v]
    offs = [v["off"] for v in per.values() if "off" in v]; ons = [v["on"] for v in per.values() if "on" in v]
    if ratios:
        out.append(f"{name:16s} OFF median {st.median(offs):8.2f} t/s  ON median {st.median(ons):8.2f} t/s  "
                   f"ON/OFF median {st.median(ratios):.4f} (pairs={len(ratios)}, min {min(ratios):.4f}, max {max(ratios):.4f})")
    else:
        out.append(f"{name:16s} no complete valid pair")
open(sys.argv[2], "w").write("\n".join(out) + "\n")
print("\n".join(out))
PY
echo "end=$(date -u +%FT%TZ)" > "$OUT/end.txt"
nin=$(python3 -c "import json; print(sum(1 for l in open('$REC') if not json.loads(l)['valid'] and not json.loads(l)['arm'].startswith('preflight')))")
echo "RESULT t3-ch19-screen pass=$((nin == 0 ? 1 : 0)) fail=$((nin == 0 ? 0 : 1)) invalid_rows=$nin out=$OUT"
[ "$nin" -eq 0 ]
