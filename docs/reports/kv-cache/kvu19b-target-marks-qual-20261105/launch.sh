#!/bin/bash
set -euo pipefail
D=/mnt/raid0/llm/tmp/kvu/kvu19b-target-marks-qual-20261105
exec bash /mnt/raid0/llm/tmp/compute-flags/bin/rowflow/filler_run15.sh --id kvu19b-target-marks-qual-20261105 --class cpu --role bench --gpu-quiet none --min-window 300 --stop "$D/STOP" --workdir "$D" --precond-cmd "printf '%s  %s\n' eabc48752f7b39d90e4fd4071e09fea945c6bdf7c071581a5326868adb177264 '$D/inputs.json' | sha256sum -c" --cmd "bash '$D/job.sh'" --complete-cmd "python3 '$D/complete.py'"
