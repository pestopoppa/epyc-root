#!/bin/bash
set -euo pipefail
D=/mnt/raid0/llm/tmp/df2/cafe4-modes-hip-r7-20261119
exec bash /mnt/raid0/llm/tmp/compute-flags/bin/rowflow/filler_run15.sh --id df2-cafe4-modes-hip-build-r7-20261119 --class cpu --role build --min-window 3600 --stop "$D/STOP" --workdir "$D" --precond-cmd "python3 $D/driver.py inputs" --cmd "python3 $D/driver.py build" --complete-cmd "python3 $D/driver.py check"
