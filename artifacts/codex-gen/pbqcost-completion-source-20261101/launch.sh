#!/bin/bash
set -euo pipefail
D=/mnt/raid0/llm/tmp/codex-ni-pbqcost-v2-20261101
ENGINE=/mnt/raid0/llm/tmp/compute-flags/bin/qual-v1/filler_run14.sh
CLAIM_CPUS="${WS58_QUAL_CPUS:-${FILLER_CPUS:-184-191}}"
/usr/bin/python3.13 -B "$D/source_seal.py"
exec bash "$ENGINE" \
  --id codex-ni-pbqcost-confirm-q-r3-20261101 \
  --class gpu --gpu-quiet exclusive --claim-cpus "$CLAIM_CPUS" \
  --role bench --min-window 6000 \
  --stop "$D/STOP" \
  --port 18397 \
  --complete-cmd "python3 -B '$D/completion_check.py'" \
  --workdir "$D" \
  --requires-tool /usr/bin/python3.13 \
  --requires-tool /usr/bin/taskset \
  --requires-tool /usr/bin/numactl \
  --qual-interpreter /usr/bin/python3.13 \
  --cmd "bash '$D/job.sh'"
