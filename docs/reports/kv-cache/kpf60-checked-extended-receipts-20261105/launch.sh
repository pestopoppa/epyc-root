#!/bin/bash
set -euo pipefail
D=/mnt/raid0/llm/tmp/kvfork/kpf60-checked-extended-receipts-20261105
export FILLER_DISK_FLOOR_GIB=150
exec /bin/bash /mnt/raid0/llm/tmp/compute-flags/bin/rowflow/filler_run15.sh --id kpf60-checked-extended-receipts-20261105 --class cpu --role build --gpu-quiet none --min-window 300 --stop "$D/STOP" --workdir "$D" --precond-cmd "printf '%s  %s\n' 'e4fa736d678e68a292e2568c3bf418fcce3a276587d27cd79d6966a91500b902' '$D/inputs.json' | sha256sum -c && python3 '$D/check.py'" --complete-cmd "python3 '$D/complete.py'" --cmd "bash '$D/job.sh'"
