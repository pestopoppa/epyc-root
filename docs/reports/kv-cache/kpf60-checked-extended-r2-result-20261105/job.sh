#!/bin/bash
set -euo pipefail
D=/mnt/raid0/llm/tmp/kvfork/kpf60-checked-extended-r2-20261105
: "${FILLER_STOPFILE:?}" "${FILLER_DEADLINE:?}"
python3 "$D/check.py"
if [[ ${FILLER_DRYRUN:-0} == 1 ]]; then
 python3 -c 'import os,sys;sys.exit(0 if len(os.sched_getaffinity(0))==4 else 1)'
 O="${FILLER_DRYRUN_RESULT_PATH:?}.build"
else O="$D/out"; fi
mkdir -p "$O"
python3 "$D/supervise.py" "$FILLER_STOPFILE" "$FILLER_DEADLINE" /usr/bin/g++ -std=c++17 -O2 -UNDEBUG -Wall -Wextra -Werror -I"$D" "$D/test_checked_counter.cpp" -o "$O/test_checked_counter" >"$O/compile.log" 2>&1
python3 "$D/supervise.py" "$FILLER_STOPFILE" "$FILLER_DEADLINE" "$O/test_checked_counter" >"$O/test.log" 2>&1
python3 "$D/check.py"
python3 "$D/finalize.py" "$O" "${FILLER_DRYRUN_RESULT_PATH:-}"
