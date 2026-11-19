#!/bin/bash
set -euo pipefail
D=/mnt/raid0/llm/tmp/vidya-belief-substrate/exp01-ready-20261118/continuation
exec /bin/bash /mnt/raid0/llm/tmp/compute-flags/bin/rowflow/filler_run15.sh --id vidya-exp01-proxy-input-recovery-20261118-r2 --class cpu --role build --gpu-quiet none --min-window 5100 --stop "$D/STOP" --workdir "$D/engine-work" --precond-cmd "python3 $D/continuation_capture.py check" --complete-cmd "python3 $D/continuation_capture.py complete" --cmd "python3 $D/continuation_capture.py run"
