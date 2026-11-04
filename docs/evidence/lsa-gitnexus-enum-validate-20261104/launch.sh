#!/bin/bash
set -euo pipefail
D=/mnt/raid0/llm/tmp/rope-ctx-assessment/lsa-screen-20261103/gitnexus-parser-debug-20261104/enum-validation
printf "%s  %s\n" "09b9d553dbd10a0ffe3daa05fbb372d061c89202c3f168dc6e0f581442f52745" "$D/readset.sha256" | sha256sum -c --status
sha256sum -c --status "$D/readset.sha256"
export FILLER_STATE_DIR="$D/state"
exec /mnt/raid0/llm/tmp/compute-flags/bin/rowflow/filler_run15.sh --id lsa-gitnexus-enum-validate-20261104 --class cpu --role build --gpu-quiet none --claim-cpus 0-1 --min-window 90 --stop "$D/STOP" --workdir "$D" --cmd "/usr/bin/python3 $D/job.py" --complete-cmd "test -f $D/complete"
