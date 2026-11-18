#!/bin/bash
# EXP-01 pilot job (BRF-T4-EXP01 / INF-26 iqk-iquant-enablement.md T2). Bounded, resumable, incremental.
# Manifest: docs/design/backlog-refactor-2026-11/backlog-experiment-manifest-20261102.json package EXP-01 .pilot
# Instrument: /mnt/raid0/llm/ik_llama.cpp (read-only reference instrument, NOT a serving path).
# Inputs: MODELSET env file (Q4KM IQ4KT IQ2XXS IQ2KT [ITEMS]); OUT dir. Unit = one llama-bench launch / one item.
# Stop rules (exploratory/decision-support; an early stop is an OPERATIONAL decision, never a gate result):
#   stop-on-answer   pair ratio band (tg128 B/A) lies wholly above 1.00 or wholly below 0.95 at a planned look (>=2 launches/arm)
#   stop-on-futility pair band wholly below 0.95 -> remaining launches of that pair cannot move the >=95% rule; record, gate stays open
#   band = ratio of means +/- 2*sqrt(sdA^2/nA+sdB^2/nB)/meanA  (preliminary, this instrument's own spread; no imported floor)
set -euo pipefail
CAPTURE_DIR=${EXP01_CAPTURE_DIR:?A sealed prospective EXP01 source packet is required}
if [[ ${1:-} == --capture-control ]]; then
  exec python3 "$CAPTURE_DIR/diagnostic.py"
fi
if [[ ${1:-} != --capture-official ]]; then
  echo 'Use a fresh prospective capture packet and an explicit EXP01 capture mode.' >&2
  exit 2
fi
if [[ ${FILLER_DRYRUN:-0} == 1 ]]; then
  echo 'Publisher smoke must use the separate capture-control entry point.' >&2
  exit 2
fi
MODELSET=${MODELSET:-/mnt/raid0/llm/tmp/brf-exp01/models.env}
OUT=${OUT:?A fresh EXP01 output directory is required}
IK=${IK:-/mnt/raid0/llm/ik_llama.cpp}
export LAUNCHES=${LAUNCHES:-3}           # pilot: 3 launches/arm
CAP_S=${CAP_S:-5400}              # pilot cap: <= 90 min wall
PP=${PP:-512}; TG=${TG:-128}
CPUS=${FILLER_CPUS:-0-3}; THREADS=${FILLER_THREADS:-4}
STOP=${FILLER_STOPFILE:-$OUT/STOP}
T0=$(date +%s); END=$(( T0 + CAP_S )); [ -n "${FILLER_DEADLINE:-}" ] && [ "$FILLER_DEADLINE" -lt "$END" ] && END=$FILLER_DEADLINE
export OUT MODELSET IK PP TG CAP_S EXP01_CONTROL_END="$END" FILLER_STOPFILE="$STOP"
export EXP01_JOB_SOURCE="${BASH_SOURCE[0]}"
python3 "$CAPTURE_DIR/capture.py" begin-official "$OUT"
R="$OUT/results.jsonl"
touch "$R"
trap 'rc=$?; python3 "$CAPTURE_DIR/capture.py" terminal-official "$OUT" "$rc" || exit 4' EXIT
# shellcheck disable=SC1090
source "$MODELSET"
export LD_LIBRARY_PATH="$IK/build/ggml/src:$IK/build/src"   # own ggml (three-generation hazard)
BENCH="$CAPTURE_DIR/bench.sh"; CLI="$CAPTURE_DIR/cli.sh"
have() { grep -q "\"unit\": *\"$1\"" "$R"; }
emit() {
  python3 "$CAPTURE_DIR/capture.py" emit "$R" "$1"
}
stopping() { [ -e "$STOP" ] || [ "$(date +%s)" -ge "$END" ]; }

# Refuse resume across allocations: a smoke unit must never become a measured launch.
python3 - "$R" "$CPUS" "$THREADS" <<'PY_RESUME'
import json,sys
for line in open(sys.argv[1]):
    r=json.loads(line)
    if r.get('kind')=='speed' and (r.get('cpus')!=sys.argv[2] or r.get('threads')!=int(sys.argv[3])):
        raise SystemExit('refuse mismatched allocation in resumed speed units')
PY_RESUME

# ---- validity + mechanism (unit "validity", once) ----
if ! have validity; then
  # ik is a monolithic-libggml tree (no libggml-base), so the verifier's vacuity guard always trips on it; accept ONLY when
  # every inspected library resolves inside $IK/build (zero BAD, libggml.so + libllama.so OK) and the sole FAIL is that guard.
  link_rc=0; bash /mnt/raid0/llm/epyc-inference-research/scripts/utils/verify_ggml_linkage.sh "$IK/build/bin/llama-bench" "$IK/build" > "$OUT/linkage.log" 2>&1 || link_rc=$?
  if [ "$link_rc" -ne 0 ] && ! grep -q '^  BAD ' "$OUT/linkage.log" && grep -q '^  OK   libggml.so ' "$OUT/linkage.log" \
     && grep -q '^  OK   libllama.so ' "$OUT/linkage.log" && grep -q 'libggml-base.so seen *: 0' "$OUT/linkage.log"; then
    echo "ACCEPTED: monolithic ik libggml; all inspected libs inside $IK/build" >> "$OUT/linkage.log"; link_rc=0
  fi
  kt_syms=$(strings "$IK/build/ggml/src/libggml.so" | grep -ci 'iq4_kt' || true)
  emit "$(/mnt/raid0/llm/epyc-inference-research/.venv/bin/python3 -I "$CAPTURE_DIR/identity.py" "$MODELSET" "$IK" "$link_rc" "$kt_syms")"
fi
python3 - "$R" <<'EOF' || { echo "validity FAILED -> REVISE (see results.jsonl)"; exit 3; }
import json,sys
v=[json.loads(l) for l in open(sys.argv[1]) if '"validity"' in l][-1]
sys.exit(0 if v["ok"] else 1)
EOF

# ---- speed pairs, interleaved ABAB, one launch = one unit ----
PAIRS="Q4KM:IQ4KT IQ2XXS:IQ2KT"
look() { python3 "$CAPTURE_DIR/look.py" "$R" "$1" "$2"; }
for i in $(seq 1 "$LAUNCHES"); do
  for p in $PAIRS; do
    a=${p%%:*}; b=${p##*:}; fa=${!a:-}; fb=${!b:-}
    [ -n "$fa" ] && [ -n "$fb" ] || continue
    if python3 - "$R" "look-$a-$b" <<'PY_STOP'
import json, sys
with open(sys.argv[1]) as result:
    stopped = any(row.get("unit") == sys.argv[2] and row.get("stop") in ("answer", "futility")
                  for row in map(json.loads, result))
raise SystemExit(0 if stopped else 1)
PY_STOP
    then continue; fi
    for arm in "$a" "$b"; do
      u="speed-$arm-$i"; have "$u" && continue
      stopping && { echo "stop/cap reached before $u"; break 3; }
      f=${!arm}; s=$(date +%s.%N)
      rc=0; EXP01_LAUNCH_UNIT="$u" taskset -c "$CPUS" "$BENCH" -m "$f" -p "$PP" -n "$TG" -r 1 -t "$THREADS" -o json > "$OUT/$u.json" 2> "$OUT/$u.err" || rc=$?
      e=$(date +%s.%N)
      emit "$(python3 - "$OUT/$u.json" "$u" "$arm" "$i" "$rc" "$s" "$e" "$f" "$CPUS" "$THREADS" <<'EOF'
import json,sys
p,u,arm,i,rc,s,e,f,cpus,threads=sys.argv[1:]
d={"unit":u,"kind":"speed","arm":arm,"launch":int(i),"rc":int(rc),"duration_s":round(float(e)-float(s),2),"gguf":f,"cpus":cpus,"threads":int(threads)}
try:
    for r in json.load(open(p)):
        if r.get("n_gen",0)>0: d["tg"]=r["avg_ts"]; d["tg_n"]=r["n_gen"]
        elif r.get("n_prompt",0)>0: d["pp"]=r["avg_ts"]; d["pp_n"]=r["n_prompt"]
        d["build_commit"]=r.get("build_commit"); d["type_k"]=r.get("model_type")
        if r.get("n_threads") != int(threads): raise ValueError("native n_threads does not match allocation")
except Exception as x:
    d["parse_error"]=str(x); d["rc"]=4
    for key in ("tg","pp","tg_n","pp_n"): d.pop(key,None)
print(json.dumps(d))
EOF
)"
    done
    [ "$i" -ge 2 ] && emit "$(look "$a" "$b")"
  done
done

# ---- quality slice (24 items x control + intervention), greedy, per-item records ----
if [ -n "${ITEMS:-}" ] && [ -f "${ITEMS:-/nonexistent}" ]; then
  python3 "$CAPTURE_DIR/quality.py" "$R" "$ITEMS" "$CLI" "$CPUS" "$THREADS" "$END" "$STOP" Q4KM="${Q4KM:-}" IQ4KT="${IQ4KT:-}"
else
  have quality-gap || emit '{"unit":"quality-gap","kind":"quality","status":"not-run","reason":"no pinned task-eval item set (ITEMS unset); quality pass is not reducible and stays open"}'
fi
python3 "$CAPTURE_DIR/look.py" "$R" SUMMARY SUMMARY "$(( $(date +%s) - T0 ))" > "$OUT/SUMMARY.json"
cat "$OUT/SUMMARY.json"
