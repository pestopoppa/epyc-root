#!/bin/bash
set -euo pipefail
D=/mnt/raid0/llm/tmp/speculative-decoding-mtp/sr8-fresh-edit-20261105
# Replace 4f7a9e04f1aa9f1fb98a6ac6c4daff53de9dbad0fc82521ffc13c4e1f7c8629e with the hash of the sealed runtime.sha256 at publication.
exec bash /mnt/raid0/llm/tmp/compute-flags/bin/rowflow/filler_run15.sh --id sr8-fresh-edit-gpu-20261105 --class gpu --gpu-threads 184-191 --port 18453 --min-window 7200 --stop "$D/STOP" --workdir "$D" --precond-cmd "printf '%s  %s\n' '4f7a9e04f1aa9f1fb98a6ac6c4daff53de9dbad0fc82521ffc13c4e1f7c8629e' '$D/runtime.sha256' | sha256sum -c - && (cd '$D' && sha256sum -c runtime.sha256) && python3 '$D/precheck.py' && PYTHONDONTWRITEBYTECODE=1 python3 '$D/check_parser.py' && PYTHONDONTWRITEBYTECODE=1 python3 '$D/check_analysis.py'" --cmd "python3 $D/supervise.py $D/STOP \$FILLER_DEADLINE python3 $D/native_worker.py" --complete-cmd "python3 $D/check_complete.py"
