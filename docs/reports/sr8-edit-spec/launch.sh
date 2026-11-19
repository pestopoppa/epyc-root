#!/bin/bash
set -euo pipefail
D=/mnt/raid0/llm/tmp/speculative-decoding-mtp/sr8-edit-spec
exec bash /mnt/raid0/llm/tmp/compute-flags/bin/rowflow/filler_run15.sh --id sr8-bep-lookup-gpu-20261104 --class gpu --gpu-threads 184-191 --port 18431 --min-window 7200 --stop "$D/STOP" --workdir "$D" --precond-cmd "sha256sum -c $D/runtime.sha256 && python3 $D/precheck.py" --cmd "python3 $D/supervise.py $D/STOP \$FILLER_DEADLINE python3 $D/native_worker.py" --complete-cmd "python3 $D/check_complete.py"
