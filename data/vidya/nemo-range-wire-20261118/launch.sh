#!/bin/bash
set -euo pipefail
D=/mnt/raid0/llm/tmp/vidya-belief-substrate/nemo-range-wire-20261118
printf '%s  %s\n' '5540e622341cba163798b635b444ff349dc63c37ae055abb272ecbf698cc2911' "$D/job.py" | sha256sum --check --status
exec /mnt/raid0/llm/tmp/compute-flags/bin/rowflow/filler_run15.sh --id vb-nemo-range-wire-20261118 --class cpu --role build --gpu-quiet none --min-window 120 --stop "$D/STOP" --workdir "$D" --cmd "/usr/bin/python3 -I -B $D/job.py run 2bdffaac2dcc83891b7779bf2800f0d857a972e601853ef3b92b02b10a9c041d" --complete-cmd "/usr/bin/python3 -I -B $D/job.py complete 2bdffaac2dcc83891b7779bf2800f0d857a972e601853ef3b92b02b10a9c041d"
