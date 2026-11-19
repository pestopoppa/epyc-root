#!/bin/bash
set -euo pipefail
D=/mnt/raid0/llm/tmp/kvfork/kpf623-byte-align-r2-20261105
exec /bin/bash /mnt/raid0/llm/tmp/compute-flags/bin/rowflow/filler_run15.sh --id kpf623-byte-align-r2-20261105 --class cpu --role build --gpu-quiet none --min-window 300 --stop "$D/STOP" --workdir "$D" --precond-cmd 'sha256sum -c SHA256SUMS' --complete-cmd "python3 -B '$D/worker.py' complete" --cmd "python3 -B '$D/worker.py'"
