#!/bin/bash
set -euo pipefail
HERE=$(dirname "$(readlink -f "$0")")
[ "$#" -eq 0 ] || exit 64
: "${WS58_REGIONS:?real GPU calendar grant required}"
[ "$WS58_REGIONS" = mi210_0,72-79 ] || { echo 'wrong original-protocol GPU/CPU placement' >&2; exit 64; }
(cd "$HERE"; sha256sum -c PACKAGE-SHA256SUMS >/dev/null)
id=refactor-c6-gpu-27b-identity-r2-729599d69-20261031
job="taskset -c \"\$FILLER_CPUS\" /usr/bin/python3 -B '$HERE/gpu_identity_job.py'"
complete="/usr/bin/python3 -B '$HERE/consume_identity.py'"
exec /bin/bash "$HERE/engine/filler_run13.sh" --id "$id" --class gpu --claim-cpus 72-79 --gpu-quiet exclusive --role bench \
    --port 8197 --min-window 3600 --cmd "$job" --complete-cmd "$complete" --stop "$HERE/STOP-gpu" --workdir "$HERE"
