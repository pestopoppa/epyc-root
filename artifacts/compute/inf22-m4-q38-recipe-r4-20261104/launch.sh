#!/bin/bash
set -euo pipefail
base=/mnt/raid0/llm/tmp/inf22-m4-q38-recipe-r4-20261104
exec /mnt/raid0/llm/tmp/compute-flags/bin/rowflow/filler_run15.sh --id inf22-m4-q38-recipe-r4-20261104 --class cpu --claim-cpus 0-95 --role bench --min-window 6900 --stop "$base/STOP" --workdir "$base/source" --self-claim --cmd "$base/job.sh" --complete-cmd "/usr/bin/python3 $base/complete.py"
