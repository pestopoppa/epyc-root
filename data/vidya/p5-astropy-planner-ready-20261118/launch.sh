#!/bin/bash
set -euo pipefail
D=/mnt/raid0/llm/tmp/vidya-belief-substrate/astropy-project-20261118/row
printf '%s  %s\n' '7ef7da7baad82bb206dd372cf252fbf144c6c8db99ffd19341deddba9469a250' "$D/job.py" | sha256sum --check --status
exec /mnt/raid0/llm/tmp/compute-flags/bin/rowflow/filler_run15.sh --id vb-p5-astropy-planner-acceptance-20261118 --class cpu --role build --gpu-quiet none --min-window 120 --stop "$D/STOP" --workdir "$D" --cmd "/usr/bin/python3 -I -B $D/job.py run cdf3013191c03c12d77fa089a78262574ef50e2d19338985499269c275fcde14" --complete-cmd "/usr/bin/python3 -I -B $D/job.py complete cdf3013191c03c12d77fa089a78262574ef50e2d19338985499269c275fcde14"
