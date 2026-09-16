#!/bin/bash
# SC75 / VB-WIRE-2: the belief-row hook for INF-70 serving arms. SOURCED by arm_cold.sh and
# arm_hot.sh; defines functions only, runs nothing on source.
#
# Contract (handoffs/active/vidya-belief-substrate-program.md, SC75 evidence):
#   * launch.json is written ONCE per launch, after placement is accepted (sc75_launch_json);
#   * at ARM END, right after the per-arm coresummary line, one call emits
#     <label>.belief_measurements.jsonl via scripts/vidya/adapters/inf70_serving_arm_capture.py
#     (sc75_capture_arm).
#   * CAPTURE-AFTER-MEASURE: nothing here runs while the client is measuring.
#   * The writer refuses a capture more than MAX_CAPTURE_LAG_S (3600 s) after the rows file was
#     last written, so the call sits immediately after the client, never in a later sweep.
#   * FAIL LOUDLY, NEVER ABORT: a missing launch.json field or a writer refusal prints
#     "SC75 CAPTURE FAILED", writes <label>.sc75_capture_failed next to the rows, and returns 0.
#     The measurement already happened, so it is kept; it just carries no belief row.
#
# Every function prints exactly one line on stdout, so arm scripts can put it in the timeline.

SC75_HARNESS_DIR=${SC75_HARNESS_DIR:-$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)}
SC75_ROOT=${SC75_ROOT:-$(cd "$SC75_HARNESS_DIR/../../.." && pwd)}
SC75_WRITER=${SC75_WRITER:-$SC75_ROOT/scripts/vidya/adapters/inf70_serving_arm_capture.py}
SC75_PRODUCER=${SC75_PRODUCER:-inf70-serving-harness1}

_sc75_fail() {  # <run_dir> <label> <message>
  local msg="SC75 CAPTURE FAILED for arm $2 (measurement kept, NO belief row): $3"
  echo "$msg" >&2
  { date -u +%FT%TZ; echo "$msg"; } > "$1/$2.sc75_capture_failed" 2>/dev/null
  echo "$msg"
}

# sc75_launch_json <out_json> <launch_id> <server_pid> <model_path> <version_line> <pinning> <bench_cpus>
sc75_launch_json() {
  local out
  out=$(python3 "$SC75_HARNESS_DIR/sc75_launch.py" write --out "$1" --launch-id "$2" --pid "$3" \
        --model "$4" --version-line "$5" --pinning "$6" --bench-cpus "$7" 2>&1) \
    || { echo "SC75 LAUNCH.JSON FAILED (arms will carry no belief row): $out" >&2
         echo "SC75 LAUNCH.JSON FAILED (arms will carry no belief row): $out"; return 0; }
  case "$out" in *MISSING*) echo "SC75 WARNING: $out -- capture will refuse at arm end" >&2;; esac
  echo "SC75 $out"
}

# sc75_arm_launch_json <session_json> <arm_json> <knob_payload>   (hot server: per-arm knobs)
sc75_arm_launch_json() {
  python3 "$SC75_HARNESS_DIR/sc75_launch.py" arm --session "$1" --out "$2" --knobs "$3" 2>&1 \
    || echo "SC75 per-arm launch.json failed for $2"
}

# sc75_capture_arm <run_dir> <label> <launch_json> <arm_start_epoch_s> [category]
sc75_capture_arm() {
  local run_dir=$1 lbl=$2 lj=$3 a0=$4 cat=${5:-CANDIDATE} started out rc
  rm -f "$run_dir/$lbl.sc75_capture_failed" 2>/dev/null
  [ -f "$SC75_WRITER" ] || { _sc75_fail "$run_dir" "$lbl" "writer not found: $SC75_WRITER"; return 0; }
  [ -f "$lj" ] || { _sc75_fail "$run_dir" "$lbl" "launch.json not found: $lj"; return 0; }
  out=$(python3 "$SC75_HARNESS_DIR/sc75_launch.py" check "$lj" 2>&1); rc=$?
  [ "$rc" -eq 0 ] || { _sc75_fail "$run_dir" "$lbl" "$out"; return 0; }
  started=$(date -u -d "@$a0" +%FT%TZ 2>/dev/null) \
    || { _sc75_fail "$run_dir" "$lbl" "bad arm start epoch '$a0'"; return 0; }
  out=$(python3 "$SC75_WRITER" --run-dir "$run_dir" --label "$lbl" --launch-json "$lj" \
        --arm-started-at "$started" --producer "$SC75_PRODUCER" --category "$cat" 2>&1); rc=$?
  if [ "$rc" -eq 0 ]; then
    echo "SC75 $out"
  else
    _sc75_fail "$run_dir" "$lbl" "writer rc=$rc: $(echo "$out" | tr '\n' ' ')"
  fi
  return 0
}
