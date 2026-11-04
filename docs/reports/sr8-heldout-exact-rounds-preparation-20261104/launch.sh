#!/bin/bash
set -euo pipefail
D=/mnt/raid0/llm/tmp/df2/sr8-heldout-v2
exec bash /mnt/raid0/llm/tmp/compute-flags/bin/rowflow/filler_run15.sh --id sr8-bep-heldout-exact-rounds-20261104 --class gpu --gpu-threads 184-191 --port 18453 --min-window 7200 --stop "$D/STOP" --workdir "$D" --precond-cmd "printf '%s  %s\n' 'b715644d4237a4088c43cac8f2bfd5e163d45276179bf0082c6aaeed2e1eb6db' '$D/runtime.sha256' | sha256sum -c - && (cd '$D' && sha256sum -c runtime.sha256) && python3 '$D/precheck.py' && PYTHONDONTWRITEBYTECODE=1 python3 '$D/check_parser.py'" --cmd "python3 $D/supervise.py $D/STOP \$FILLER_DEADLINE python3 $D/native_worker.py" --complete-cmd "python3 $D/check_complete.py"
