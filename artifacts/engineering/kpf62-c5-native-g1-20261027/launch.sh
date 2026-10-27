#!/bin/bash
set -euo pipefail
source /mnt/raid0/llm/tmp/codex-ni-20261027-kpf62-c5-api-port/guard.sh
hold_guard; source_guard
mode=${1:?build or capture}
case "$mode" in build|capture) ;; *) refuse 'bad mode'; exit 70;; esac
[[ ${FILLER_ID:-} == "kpf62-native-g1-$mode-20261027" && ${FILLER_STOPFILE:-} == "$BASE/STOP" ]] || refuse 'actual filler identity required'
[[ -s $BASE/BUILD-T1-PASSED.txt ]] || refuse 'build T1 proof required'
grep -Fx "source-seal-sha256=$(sha256sum "$BASE/SOURCE.SHA256SUMS" | cut -d' ' -f1)" "$BASE/BUILD-T1-PASSED.txt" >/dev/null || refuse 'T1 source drift'
if [[ $mode == capture ]]; then [[ -s $BASE/build-receipt.json ]] || refuse 'build dependency absent'; fi
# Official filler grants the literal CPU mask and owns the captured process group.
cd "$BASE"
exec "$PY" -B -s "$BASE/resource-watch.py" "$PY" -B -s "$BASE/job.py" --mode "$mode"
