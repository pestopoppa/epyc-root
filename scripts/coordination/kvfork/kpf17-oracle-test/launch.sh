#!/bin/bash
set -euo pipefail
D=/mnt/raid0/llm/tmp/kvfork/kpf17-oracle-test-20261104
[[ $(sha256sum "$D/binding.json" | cut -d ' ' -f1) == BINDING_SHA256 ]]
exec /bin/bash "$D/filler_run15.sh" --id kvfork17-oracle-test-20261104 --class cpu --role build --gpu-quiet none --min-window 300 --stop "$D/STOP" --workdir "$D" --precond-cmd "python3 '$D/precondition.py'" --complete-cmd "python3 '$D/complete.py'" --cmd "python3 '$D/gdb_job.py'"
