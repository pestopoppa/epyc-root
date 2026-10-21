#!/bin/bash
# Chained, self-starting launcher for the DS41-1017 target-only baseline (A/A floor, then champion dd3d9721c vs candidate C f0c96dc1f).
# Starts itself: sleeps until the calendar slot, waits for the approval marker, then BLOCKS on the region lock (--timeout-s 0) and runs
# calibrate + compare inside ONE claim (all four CPU regions + gpu-quiet exclusive). It is NOT a notify-only watcher.
# Refuses (exit 3) unless APPROVED holds the sha256 of gate_1017.py and PREDECLARED.md exactly as reviewed.
# usage: chained_launch.sh [--start 2026-10-22T06:30:00Z] [--approval-wait-s 7200] [--dry-run]
# Flags: DONE / FAILED touched on completion (success AND failure); RUN_RECORD.json carries the floor path and verdict.
set -uo pipefail
D=/mnt/raid0/llm/tmp/ds41-1017-baseline-20261021
RL=/mnt/raid0/llm/epyc-orchestrator/scripts/region-lock
START=2026-10-22T06:30:00Z; APPROVAL_WAIT=7200; DRY=0; INNER=0
while [ $# -gt 0 ]; do case "$1" in
  --start) START=$2; shift 2;; --approval-wait-s) APPROVAL_WAIT=$2; shift 2;; --dry-run) DRY=1; shift;; --inner) INNER=1; shift;; --warmup-test) INNER=2; shift;;
  *) echo "bad arg $1" >&2; exit 2;; esac; done
say() { echo "[$(date -u +%FT%TZ)] $*" | tee -a "$D/chained_launch.log"; }
approved() { [ -f "$D/APPROVED" ] && (cd "$D" && sha256sum -c --quiet APPROVED >/dev/null 2>&1) && grep -q ' gate_1017.py$' "$D/APPROVED" && grep -q ' PREDECLARED.md$' "$D/APPROVED"; }
smoke_ok() { [ -f "$D/SMOKE_OK" ] && [ "$D/SMOKE_OK" -nt "$D/APPROVED" ]; }
fail() { say "FAILED: $*"; echo "$*" > "$D/FAILED"; exit "${2:-1}"; }
GB=/mnt/raid0/llm/kernels/builds
# Page-cache warm-up (main 2026-10-21, after the Sept bundle run (a) was voided by a cold-page-cache transient): read all 9 1017 shards
# sequentially into the page cache BEFORE the first launch, so the A/A series does not start during a cache flip. Not part of gate_1017.py.
warm_up() {
  local WARM_GLOB=${WARM_GLOB:-/mnt/raid0/llm/models/antirez/deepseek-v4.1-flash-gguf/DeepSeek-V4.1-Flash-1017-MXFP4-experts-0000?-of-00009.gguf}
  local f ft0 wt0 nwarm=0
  say "warm-up: MemAvailable $(awk '/MemAvailable/ {printf "%d GiB", $2/1048576}' /proc/meminfo), cached $(awk '/^Cached:/ {printf "%d GiB", $2/1048576}' /proc/meminfo)"
  wt0=$(date +%s)
  for f in $WARM_GLOB; do
    [ -f "$f" ] || fail "warm-up: shard missing: $f" 7
    ft0=$(date +%s); taskset -c 0-47 cat "$f" > /dev/null || fail "warm-up: read failed: $f" 7
    say "warm-up: $(basename "$f") $(stat -c %s "$f") B in $(( $(date +%s) - ft0 )) s"; nwarm=$((nwarm + 1))
  done
  say "warm-up: $nwarm shard(s) read in $(( $(date +%s) - wt0 )) s; MemAvailable now $(awk '/MemAvailable/ {printf "%d GiB", $2/1048576}' /proc/meminfo), cached $(awk '/^Cached:/ {printf "%d GiB", $2/1048576}' /proc/meminfo)"
}
if [ "$INNER" = 2 ]; then warm_up; exit 0; fi
if [ "$INNER" = 1 ]; then
  approved || fail "approval marker missing or does not match the files (inside claim)" 3
  smoke_ok || fail "SMOKE_OK missing or older than APPROVED (inside claim): the smoke gate (smoke_1017.py) must pass first" 3
  warm_up
  say "inside claim: calibrate (24 A/A pairs, cmp-pairs 5) on champion"
  python3 -I "$D/gate_1017.py" calibrate --pairs 24 --cmp-pairs 5 --out "$D/aa" --execute > "$D/calibrate.out" 2>&1; rc=$?
  say "calibrate rc=$rc"; [ "$rc" = 0 ] || fail "calibrate rc=$rc (see $D/calibrate.out)" 4
  FLOOR=$(ls "$D"/aa/floor-store/serving-floor.*.pairs-5.json 2>/dev/null | head -1)
  [ -n "$FLOOR" ] || fail "no floor file written" 5
  say "compare (5 pairs) champion dd3d9721c vs C f0c96dc1f, floor $FLOOR"
  python3 -I "$D/gate_1017.py" compare --pairs 5 --floor-file "$FLOOR" --anchor-build $GB/cpu-20261020-dd3d9721c --cand-build $GB/cpu-20261020-f0c96dc1f --out "$D/cmp" --execute > "$D/compare.out" 2>&1; rc=$?
  say "compare rc=$rc"
  python3 -I - "$D" "$FLOOR" "$rc" <<'PY'
import json, sys, os, datetime
d, floor, rc = sys.argv[1], sys.argv[2], int(sys.argv[3])
rec = {"schema": "epyc.ds41_1017_baseline.run_record.v1", "finished_utc": datetime.datetime.now(datetime.timezone.utc).strftime("%FT%TZ"),
       "floor_file": floor, "compare_rc": rc, "predeclared": os.path.join(d, "PREDECLARED.md")}
try:
    f = json.load(open(floor)); rec["floor"] = {k: f.get(k) for k in ("floor_pct", "unit", "n", "calibration_pairs", "comparison_pairs", "request_digest", "content_sha256", "instrument")}
except Exception as e: rec["floor_error"] = repr(e)
try:
    c = json.load(open(os.path.join(d, "cmp", "compare-1017.json"))); row = c.get("comparison", c)
    rec["compare"] = {k: row.get(k) for k in ("anchor_tok_s", "candidate_tok_s", "effect_pct", "floor_pct", "decisive", "pairs", "verdict")}
except Exception as e: rec["compare_error"] = repr(e)
json.dump(rec, open(os.path.join(d, "RUN_RECORD.json"), "w"), indent=1); print(json.dumps(rec, indent=1))
PY
  [ "$rc" = 0 ] && { touch "$D/DONE"; say "DONE"; exit 0; } || fail "compare rc=$rc" 6
fi
# ---- outer ----
start_epoch=$(date -u -d "$START" +%s) || fail "bad --start" 2
say "outer: slot start $START, approval wait ${APPROVAL_WAIT}s, dry=$DRY"
if [ "$DRY" = 1 ]; then approved && say "dry: approved" || say "dry: NOT approved"; smoke_ok && say "dry: SMOKE_OK fresh" || say "dry: no fresh SMOKE_OK yet"; say "dry: would sleep until $START then run: $RL run --cpu-list 0-95 --role bench --gpu-quiet exclusive --timeout-s 0 --tag ds41-1017-baseline -- $D/chained_launch.sh --inner"; exit 0; fi
rm -f "$D/DONE" "$D/FAILED"
while [ "$(date -u +%s)" -lt "$start_epoch" ]; do sleep 30; done
w=0; until approved && smoke_ok; do [ "$w" -ge "$APPROVAL_WAIT" ] && fail "not approved / no fresh SMOKE_OK by START+${APPROVAL_WAIT}s: nothing launched" 3; sleep 60; w=$((w + 60)); done
say "approved and smoke-gated; blocking on the region lock (timeout 0)"
exec "$RL" run --cpu-list 0-95 --role bench --gpu-quiet exclusive --timeout-s 0 --tag ds41-1017-baseline -- "$D/chained_launch.sh" --inner
