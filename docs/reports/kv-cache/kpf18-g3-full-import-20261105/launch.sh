#!/bin/bash
set -euo pipefail
D=/mnt/raid0/llm/tmp/kvu/kpf18-g3-full-import-20261105
printf '%s  %s\n' e80ef6be717a82129c4254998f2cfd56ff44e7f30e01fb492c310b488a64a80f "$D/job.py" | sha256sum --status -c -
printf '%s  %s\n' 0bdb5f18033d041a43f1ca7031b6c6c97a4daa83dee597a80973d8268e1fef1e "$D/worker.py" | sha256sum --status -c -
exec bash /mnt/raid0/llm/tmp/compute-flags/bin/rowflow/filler_run15.sh --id kvu-kpf18-g3-full-import-20261105 --class cpu --role build --gpu-quiet none --min-window 300 --stop "$D/STOP" --workdir "$D" --complete-cmd "python3 -B '$D/job.py' --complete" --cmd "python3 -B '$D/job.py'"
