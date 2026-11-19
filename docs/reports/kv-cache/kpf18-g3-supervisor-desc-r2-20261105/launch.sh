#!/bin/bash
set -euo pipefail
D=/mnt/raid0/llm/tmp/kvu/kpf18-supervisor-desc-r2-20261105
export ROWFLOW_REPO=/mnt/raid0/llm/worktrees/mains/h-kvu
printf '%s  %s\n' 'cc8c62adc9974201eea837c65b2ca6df0fe5f99e2b7a75c3bdcede7b82a46d69' "$D/SEALED.sha256" | sha256sum --status -c -
(cd "$D" && sha256sum --quiet -c SEALED.sha256)
export PYTHONDONTWRITEBYTECODE=1
exec /bin/bash /mnt/raid0/llm/tmp/compute-flags/bin/rowflow/filler_run15.sh --id kvu-kpf18-g3-supervisor-desc-r2-20261105 --class cpu --role build --gpu-quiet none --min-window 300 --stop "$D/STOP" --workdir "$D" --complete-cmd "python3 -B '$D/job.py' --complete" --cmd "python3 -B '$D/job.py'"
