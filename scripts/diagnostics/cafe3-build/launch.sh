#!/bin/bash
set -euo pipefail
D=/mnt/raid0/llm/tmp/df2/cafe3-cpu-build-20261119
exec bash /mnt/raid0/llm/tmp/compute-flags/bin/rowflow/filler_run15.sh --id df2-cafe3-full-cpu-build-20261119 --class cpu --role build --min-window 2400 --stop "$D/STOP" --workdir "$D" --precond-cmd "python3 $D/driver.py inputs" --cmd "python3 $D/driver.py build" --complete-cmd "python3 $D/driver.py check"
