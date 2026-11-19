#!/bin/bash
set -euo pipefail
D=/mnt/raid0/llm/tmp/kvu/kvu19b-target-marks-qual-r2-20261105
exec bash /mnt/raid0/llm/tmp/compute-flags/bin/rowflow/filler_run15.sh --id kvu19b-target-marks-qual-r2-20261105 --class cpu --role bench --gpu-quiet none --min-window 300 --stop "$D/STOP" --workdir "$D" --precond-cmd "printf '%s  %s\n' f7353b73e2b74ab0e38c4f46517d57ee3bdaf3bdfac5df6c1c20604865662113 '$D/inputs.json' | sha256sum -c" --cmd "bash '$D/job.sh'" --complete-cmd "python3 '$D/complete.py'"
