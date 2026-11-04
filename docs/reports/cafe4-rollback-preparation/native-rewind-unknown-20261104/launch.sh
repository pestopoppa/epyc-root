#!/bin/bash
set -euo pipefail
D=/mnt/raid0/llm/tmp/df2/cafe4-native-rewind-20261104
exec bash /mnt/raid0/llm/tmp/compute-flags/bin/rowflow/filler_run15.sh --id cafe4-v10-native-rollback-fault-20261104 --class cpu --role bench --min-window 900 --stop "$D/STOP" --workdir "$D" --precond-cmd "sha256sum -c $D/runtime.sha256" --cmd "bash $D/job.sh" --complete-cmd "python3 $D/runtime.py check"
