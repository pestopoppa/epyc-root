#!/bin/bash
set -euo pipefail
D=/mnt/raid0/llm/tmp/kvu/kvu16a-row-r3-20261104
read -r actual _ < <(sha256sum "$D/source-catalog.json")
[ "$actual" = 651363d22635ed8d974d36517ab3e7622c8d8675032f7056421b0f2b15e89007 ] || { echo "source catalog changed" >&2; exit 65; }
export FILLER_RL="$D/region-lock"
exec /mnt/raid0/llm/tmp/compute-flags/bin/rowflow/filler_run15.sh --id handoff-kvu16a-shape-load-r3-20261104 \
 --class gpu --role bench --gpu-quiet exclusive --claim-cpus 184-191 --gpu-threads 184-191 \
 --min-window 600 --stop "$D/STOP" --port 19763 --workdir "$D" \
 --cmd "python3 $D/job.py" --complete-cmd "python3 $D/complete.py"
