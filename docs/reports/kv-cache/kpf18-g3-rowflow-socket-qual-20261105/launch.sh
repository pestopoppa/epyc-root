#!/bin/bash
set -euo pipefail
D=/mnt/raid0/llm/tmp/kvfork/g3-rowflow-socket-qual-20261105
exec /bin/bash /mnt/raid0/llm/tmp/compute-flags/bin/rowflow/filler_run15.sh --id kpf18-g3-rowflow-socket-qual-20261105 --class cpu --role build --gpu-quiet none --min-window 300 --stop "$D/STOP" --workdir "$D" --complete-cmd 'test -s "${FILLER_DRYRUN_RESULT_PATH:-/mnt/raid0/llm/tmp/kvfork/g3-rowflow-socket-qual-20261105/out/RESULT.json}"' --cmd "python3 -B '$D/job.py'"
