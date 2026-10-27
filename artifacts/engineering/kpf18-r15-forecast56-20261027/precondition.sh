#!/bin/bash
set -euo pipefail
source /mnt/raid0/llm/tmp/codex-ni-20261027-kpf18-r15-repair/successor/config.sh
WATCH=/mnt/raid0/llm/tmp/codex-ni-20261027-kpf18-forecast56
hold_guard;source_guard
(cd "$WATCH" && sha256sum --quiet -c SOURCE.sha256) || refuse 'forecast watcher source drift'
grep -Fx "source-seal-sha256=$(sha256sum "$WATCH/SOURCE.sha256" | cut -d' ' -f1)" "$WATCH/MAIN-APPROVAL.txt" >/dev/null || refuse 'forecast watcher approval mismatch'
if [[ ${FILLER_PREFLIGHT:-0} == 1 ]];then
 [[ ${DRYRUN_NONCE:-} =~ ^[a-f0-9]{48}$ && ${FILLER_GRANTS_DIR:-} == "$BASE/dryrun/$DRYRUN_NONCE/grants" ]] || refuse 'isolated PF nonce'
 exit 0
fi
"$PY" -B -I -c 'import sys;sys.path.insert(0,sys.argv[1]);import guard;guard.sources();guard.tests_and_enrollment()' "$BASE"
exec "$PY" -B -I "$BASE/verify_pregrant.py" --id "$ID" --row-file /mnt/raid0/llm/tmp/codex-ni-20261027-kpf18-forecast56/ROW-ARMED.md --engine "$ENGINE"
