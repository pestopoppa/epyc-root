#!/bin/bash
set -euo pipefail
B=/mnt/raid0/llm/tmp/codex-ni-20261027-kpf62-yarn-selfcheck
if [[ ${FILLER_PREFLIGHT:-0} == 1 ]]; then
 [[ ${FILLER_ID:-} == kpf62-yarn-selfcheck-20261027 && ${FILLER_CPUS:-} == 0,1 ]] || exit 70
 sha256sum --quiet -c "$B/SOURCE.sha256"
 /usr/bin/python3 -B "$B/deps/dryrun_check.py" boundary --job "$B/capture-body.sh" --effect generated-yarn-selfcheck
 exit 0
fi
[[ -s "$B/MAIN-APPROVAL.txt" && ! -L "$B/MAIN-APPROVAL.txt" ]] || exit 70
grep -Fx "source-seal-sha256=$(sha256sum "$B/SOURCE.sha256" | cut -d' ' -f1)" "$B/MAIN-APPROVAL.txt" >/dev/null
sha256sum --quiet -c "$B/SOURCE.sha256"
exec /mnt/raid0/llm/tmp/refactor-01a16fc3/ci/phase-b-candidate-venv/bin/python -B "$B/resource-watch.py" --limit-kib 4194304 /mnt/raid0/llm/tmp/refactor-01a16fc3/ci/phase-b-candidate-venv/bin/python -B "$B/job.py"
