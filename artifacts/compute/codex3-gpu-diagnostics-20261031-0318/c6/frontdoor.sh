#!/bin/bash
set -euo pipefail
unset PYTHONOPTIMIZE
HERE=$(dirname "$(readlink -f "$0")")
if [ "${1:-}" = --cpu-control ]; then
    [ "$#" -eq 3 ] || exit 64
    [ -z "${WS58_REGIONS:-}" ] || { echo 'CPU control cannot claim calendar allocation' >&2; exit 64; }
    (cd "$HERE"; sha256sum -c RUNTIME-CLOSURE.sha256 >/dev/null; sha256sum -c GPU-CLOSURE.sha256 >/dev/null)
    exec /usr/bin/python3 -B "$HERE/cpu_control.py" "$2" "$3"
fi
[ "$#" -eq 0 ] || exit 64
: "${WS58_REGIONS:?GPU calendar allocation required}"
if [ "$(/usr/bin/gcc -dumpfullversion 2>/dev/null || true)" != 15.2.0 ]; then
    exec sudo -n env -u DOCKER_HOST -u DOCKER_CONTEXT docker exec --user 1000:1000 -e WS58_REGIONS="$WS58_REGIONS" epyc-root /bin/bash "$HERE/frontdoor.sh"
fi
(cd "$HERE"; sha256sum -c RUNTIME-CLOSURE.sha256 >/dev/null; sha256sum -c ENGINE-CLOSURE.sha256 >/dev/null; sha256sum -c EXTERNAL-LOCK-CLOSURE.sha256 >/dev/null; sha256sum -c GPU-CLOSURE.sha256 >/dev/null)
id=refactor-c6-gpu-gak-diag-729599d69-20261031
job="taskset -c \"\$FILLER_CPUS\" /usr/bin/python3 -B '$HERE/gpu_calendar_job.py'"
complete="/usr/bin/python3 -B '$HERE/gpu_complete.py'"
exec /bin/bash "$HERE/engine/filler_run13.sh" --id "$id" --class gpu --no-fold-siblings --gpu-quiet exclusive --role build --min-window 1080 \
    --cmd "$job" --complete-cmd "$complete" --stop "$HERE/STOP-gpu" --workdir "$HERE"
