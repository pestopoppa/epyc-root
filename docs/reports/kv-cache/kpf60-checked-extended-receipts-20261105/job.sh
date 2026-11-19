#!/bin/bash
set -euo pipefail
D=/mnt/raid0/llm/tmp/kvfork/kpf60-checked-extended-receipts-20261105
: "${FILLER_STOPFILE:?}" "${FILLER_DEADLINE:?}"
python3 "$D/check.py"
if [[ ${FILLER_DRYRUN:-0} == 1 ]]; then python3 -c 'import os; assert len(os.sched_getaffinity(0))==4'; fi
mkdir -p "$D/attempts"
O=$(mktemp -d "$D/attempts/attempt.XXXXXXXX")
cp "$D/checked_counter.hpp" "$D/test_checked_counter.cpp" "$O/"
python3 "$D/supervise.py" "$O/compile.receipt.json" "$FILLER_STOPFILE" "$FILLER_DEADLINE" /usr/bin/g++ -std=c++17 -O2 -UNDEBUG -Wall -Wextra -Werror -I"$O" "$O/test_checked_counter.cpp" -o "$O/test_checked_counter" >"$O/compile.log" 2>&1
python3 "$D/supervise.py" "$O/test.receipt.json" "$FILLER_STOPFILE" "$FILLER_DEADLINE" "$O/test_checked_counter" >"$O/test.log" 2>&1
python3 "$D/check.py"
python3 "$D/finalize.py" "$O" "${FILLER_DRYRUN_RESULT_PATH:-}"
