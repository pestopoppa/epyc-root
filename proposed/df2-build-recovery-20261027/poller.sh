#!/bin/bash
set -euo pipefail
B=/mnt/raid0/llm/tmp/codex-ni-20261027-df2-row-exact-prep
R=$B/recovery
STOP=$R/STOP
if [[ ${FILLER_PREFLIGHT:-0} == 1 ]]; then STOP=$R/T1-STOP; else
 [[ -f $R/MAIN-ACCEPTANCE.txt && ! -L $R/MAIN-ACCEPTANCE.txt ]]
 grep -Fxq "packet-sha256=$(sha256sum "$R/RECOVERY-SOURCE.sha256" | cut -d' ' -f1)" "$R/MAIN-ACCEPTANCE.txt"
fi
exec /bin/bash "$B/deps/filler_run12.sh" --id codex-ni-df2-build-recovery-20261027 --class cpu --no-fold-siblings --role build --gpu-quiet none --min-window 600 --stop "$STOP" --workdir "$R" --cmd 'exec taskset -c "$FILLER_CPUS" /bin/bash /mnt/raid0/llm/tmp/codex-ni-20261027-df2-row-exact-prep/recovery/job.sh' --complete-cmd 'test -s /mnt/raid0/llm/tmp/codex-ni-20261027-df2-row-exact-prep/recovery/RECOVERY-COMPLETE && test -s /mnt/raid0/llm/tmp/codex-ni-20261027-df2-row-exact-prep/BUILD-COMPLETE && cmp -s /mnt/raid0/llm/tmp/codex-ni-20261027-df2-row-exact-prep/recovery/RECOVERY-COMPLETE /mnt/raid0/llm/tmp/codex-ni-20261027-df2-row-exact-prep/BUILD-COMPLETE'
