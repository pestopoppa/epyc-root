#!/bin/bash
set -euo pipefail
D=/mnt/raid0/llm/tmp/codex-ni-20261027-meta-gpu-arch-ready/packet
B=/mnt/raid0/llm/tmp/codex-ni-20261027-meta-fix-prep
STOP=$D/STOP
if [[ ${FILLER_PREFLIGHT:-0} != 1 ]]; then unset FILLER_GPU_LOCK FILLER_RL FILLER_GRANTS_DIR FILLER_STATE_DIR FILLER_STUB_CMD; fi
[[ ! -e $D/ARCH-COMPLETE && ! -e $D/run ]] || { echo "REFUSED: prior attempt exists" >&2; exit 70; }
if [[ ${FILLER_PREFLIGHT:-0} == 1 ]]; then STOP=$D/T1-STOP; export FILLER_GPU_LOCK=$D/T1-GPU-LOCK; else
 [[ -s $D/MAIN-ACCEPTANCE.txt && -s /mnt/raid0/llm/tmp/codex-ni-20261027-meta-build-recovery/RECOVERY-ACCEPTED ]] || exit 70
fi
exec /bin/bash "$D/filler_run12.sh" --id codex-ni-meta-gpu-arch-20261027 --class gpu --gpu-quiet exclusive --claim-cpus 184-191 --no-fold-siblings --role build --min-window 3300 --stop "$STOP" --workdir "$D" --cmd 'exec taskset -c "$FILLER_CPUS" /bin/bash /mnt/raid0/llm/tmp/codex-ni-20261027-meta-gpu-arch-ready/packet/job.sh' --complete-cmd 'test -s /mnt/raid0/llm/tmp/codex-ni-20261027-meta-gpu-arch-ready/packet/ARCH-COMPLETE'
