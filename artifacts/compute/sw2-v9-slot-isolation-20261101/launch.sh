#!/bin/bash
set -euo pipefail
D=/mnt/raid0/llm/tmp/sw2-v9-slot-isolation-20261101
cd "$D"
export FILLER_RL="$D/region-lock"
sha256sum -c --quiet "$D/SOURCE-SHA256SUMS"
exec /bin/bash /mnt/raid0/llm/epyc-root/scripts/coordination/rowflow/filler_run15.sh --id sw2-v9-slot-isolation-20261101 --class cpu --role build --min-window 900 --stop "$D/STOP" --workdir "$D" --complete-cmd "test -s $D/run/TERMINAL.json" --cmd "env OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 HIP_VISIBLE_DEVICES=-1 ROCR_VISIBLE_DEVICES=-1 /usr/bin/python3 -B $D/worker.py"
