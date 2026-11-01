#!/bin/bash
set -euo pipefail
F=/mnt/raid0/llm/tmp/compute-flags
BIN=${WS58_QUAL_BIN:-$F/bin/qual-v1}
while :; do
  python3 -I "$BIN/science_scoreboard.py" --flags "$F" --output "$F/SCOREBOARD.md" >> "$F/scoreboard.log" 2>&1 || :
  sleep 600
done
