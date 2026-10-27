#!/bin/bash
set -euo pipefail
B=/mnt/raid0/llm/tmp/codex-ni-20261027-meta-fix-prep
STOP=$B/STOP
if [[ ${FILLER_PREFLIGHT:-0} == 1 ]]; then STOP=$B/T1-STOP; else
 [[ -f $B/MAIN-ACCEPTANCE.txt && ! -L $B/MAIN-ACCEPTANCE.txt ]] || exit 70
 grep -Fxq "packet-sha256=$(sha256sum "$B/SOURCE.SHA256SUMS" | cut -d' ' -f1)" "$B/MAIN-ACCEPTANCE.txt" || exit 70
fi
exec /bin/bash "$B/deps/filler_run12.sh" --id codex-ni-meta-fix-build-20261027 --class cpu --no-fold-siblings --role build --gpu-quiet none --min-window 3300 --stop "$STOP" --workdir "$B" --cmd 'exec taskset -c "$FILLER_CPUS" /bin/bash /mnt/raid0/llm/tmp/codex-ni-20261027-meta-fix-prep/build-body.sh' --complete-cmd 'test -s /mnt/raid0/llm/tmp/codex-ni-20261027-meta-fix-prep/BUILD-COMPLETE'
