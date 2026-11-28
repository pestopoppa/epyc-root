#!/bin/bash
set -euo pipefail
umask 077
D=/mnt/raid0/llm/tmp/w66-prefill-budget-20261128
R=/workspace/.worktrees/q8-convcore-20261127
cd "$D"
ulimit -c 0
/usr/bin/sha256sum --check --status SOURCE.sha256
exec /bin/bash /mnt/raid0/llm/tmp/compute-flags/bin/rowflow/filler_run15.sh \
  --id codex-ap-w66-budget-gpu-20261128 --class gpu \
  --claim-cpus 88-95 --role bench --gpu-quiet exclusive --gpu-threads 88-95 \
  --min-window 240 --port 28690 --cmd "/usr/bin/taskset -c 88-95 /usr/bin/python3 -I -B $D/job.py --root $R" \
  --complete-cmd "/usr/bin/python3 -I -B $D/check_complete.py" --stop "$D/STOP" --workdir "$D"
