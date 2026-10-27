#!/bin/bash
set -euo pipefail
R=/mnt/raid0/llm/tmp/codex-ni-20261027-quarter-recovery-variants/meta
B=/mnt/raid0/llm/tmp/codex-ni-20261027-meta-fix-prep
STOP=$R/STOP
if [[ ${FILLER_PREFLIGHT:-0} == 1 ]]; then STOP=$R/T1-STOP; else
 /bin/bash "$R/retirement-guard.sh"
 [[ -f $R/MAIN-ACCEPTANCE.txt && ! -L $R/MAIN-ACCEPTANCE.txt ]] || exit 70
 grep -Fxq "recovery-manifest-sha256=$(sha256sum "$R/RECOVERY.SHA256SUMS" | cut -d' ' -f1)" "$R/MAIN-ACCEPTANCE.txt" || exit 70
fi
exec /bin/bash "$B/deps/filler_run12.sh" --id codex-ni-meta-recovery-q0-20261027 --class cpu --no-fold-siblings --role build --gpu-quiet none --min-window 300 --stop "$STOP" --workdir "$R" --cmd 'exec taskset -c "$FILLER_CPUS" /bin/bash /mnt/raid0/llm/tmp/codex-ni-20261027-quarter-recovery-variants/meta/recovery-body.sh' --complete-cmd 'test -s /mnt/raid0/llm/tmp/codex-ni-20261027-meta-build-recovery/RECOVERY-ACCEPTED'
