#!/bin/bash
set -euo pipefail
D=/mnt/raid0/llm/tmp/kvfork/kpf17a-gpu-preserve
[[ $(sha256sum "$D/identity.json" | cut -d ' ' -f1) == 8dbc7ac1ac533bfdaa0c746b9119d845babbbb1b16b02479d9329159d795362f ]]
exec bash "$D/filler_run15.sh" --id kvfork17a-gpu-preserve-20261102 --class gpu --gpu-quiet exclusive --no-fold-siblings --role build --gpu-threads 184-191 --min-window 300 --stop "$D/STOP" --workdir "$D" --precond-cmd "python3 $D/job.py --check" --cmd "python3 $D/job.py" --complete-cmd "test -f $D/out/COMPLETE"
