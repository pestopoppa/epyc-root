#!/bin/bash
set -euo pipefail
B=/mnt/raid0/llm/tmp/codex-ni-20261027-kpf62-fixed-build
STOP="$B/STOP"
if [[ ${FILLER_PREFLIGHT:-0} != 1 ]]; then
 [[ -f "$B/MAIN-ACCEPTANCE.txt" && ! -L "$B/MAIN-ACCEPTANCE.txt" ]] || exit 70
else
 STOP="$B/T1-STOP"
fi
exec /bin/bash "$B/deps/filler_run12.sh" --id kpf62-native-g1-fixed-build-20261027 --class cpu --no-fold-siblings --role build --gpu-quiet none --min-window 3300 --stop "$STOP" --workdir "$B" --cmd 'exec taskset -c "$FILLER_CPUS" /bin/bash /mnt/raid0/llm/tmp/codex-ni-20261027-kpf62-fixed-build/build-body.sh' --complete-cmd '/bin/bash /mnt/raid0/llm/tmp/codex-ni-20261027-kpf62-fixed-build/check-complete.sh'
