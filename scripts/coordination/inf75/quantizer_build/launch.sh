#!/bin/bash
set -euo pipefail
D=/mnt/raid0/llm/tmp/inf75-quantizer-7cdd7c97-20261102/packet
E=/mnt/raid0/llm/tmp/compute-flags/bin/rowflow/filler_run15.sh
exec bash "$E" --id inf75-quantizer-7cdd7c97-20261102 --class cpu --role build --min-window 2400 --stop /mnt/raid0/llm/tmp/inf75-quantizer-7cdd7c97-20261102/STOP --workdir "$D" --cmd "bash $D/job.sh" --complete-cmd "python3 $D/complete.py"
