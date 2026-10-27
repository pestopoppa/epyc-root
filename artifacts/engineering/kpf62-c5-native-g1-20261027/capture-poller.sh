#!/bin/bash
set -euo pipefail
B=/mnt/raid0/llm/tmp/codex-ni-20261027-kpf62-c5-api-port
STOP="$B/STOP"
if [[ ${FILLER_PREFLIGHT:-0} == 1 ]]; then STOP="$B/CAPTURE-T1-STOP"; else [[ -s "$B/CAPTURE-APPROVAL.txt" && -s "$B/build-receipt.json" ]] || exit 70; fi
exec /bin/bash "$B/deps/filler_run12.sh" --id kpf62-native-g1-capture-20261027 --class cpu --no-fold-siblings --role build --gpu-quiet none --min-window 900 --stop "$STOP" --workdir "$B" --cmd 'exec taskset -c "$FILLER_CPUS" /bin/bash /mnt/raid0/llm/tmp/codex-ni-20261027-kpf62-c5-api-port/capture-body.sh' --complete-cmd 'test -s /mnt/raid0/llm/tmp/codex-ni-20261027-kpf62-c5-api-port/CAPTURE-DONE.json'
