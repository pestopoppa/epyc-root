#!/bin/bash
set -euo pipefail
B=/mnt/raid0/llm/tmp/codex-ni-20261027-kpf62-yarn-selfcheck
STOP="$B/STOP"
if [[ ${FILLER_PREFLIGHT:-0} == 1 ]]; then STOP="$B/T1-STOP"; else [[ -s "$B/MAIN-APPROVAL.txt" ]] || exit 70; fi
exec /bin/bash "$B/deps/filler_run12.sh" --id kpf62-yarn-selfcheck-20261027 --class cpu --no-fold-siblings --role build --gpu-quiet none --min-window 900 --stop "$STOP" --workdir "$B" --cmd 'exec taskset -c "$FILLER_CPUS" /bin/bash /mnt/raid0/llm/tmp/codex-ni-20261027-kpf62-yarn-selfcheck/capture-body.sh' --complete-cmd 'test -s /mnt/raid0/llm/tmp/codex-ni-20261027-kpf62-yarn-selfcheck/CAPTURE-DONE.json'
