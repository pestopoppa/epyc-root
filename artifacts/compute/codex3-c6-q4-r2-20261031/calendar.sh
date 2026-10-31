#!/bin/bash
set -euo pipefail
HERE=$(dirname "$(readlink -f "$0")")
[ "$#" -eq 0 ] || { echo 'calendar frontdoor takes no arguments' >&2; exit 64; }
: "${WS58_REGIONS:?keeper must assign the CPU quarter}"
if [ "$(/usr/bin/gcc -dumpfullversion 2>/dev/null || true)" != 15.2.0 ]; then
    exec sudo -n env -u DOCKER_HOST -u DOCKER_CONTEXT docker exec --user 1000:1000 -e WS58_REGIONS="$WS58_REGIONS" epyc-root /bin/bash "$HERE/calendar.sh"
fi
(cd "$HERE"; sha256sum -c PACKAGE-SHA256SUMS)
ENGINE=/mnt/raid0/llm/tmp/refactor-c6-store-build-prep-20261030
(cd "$ENGINE"; sha256sum -c ENGINE-SHA256SUMS)
id=refactor-c6-35186-q4-two-cohort-cpu-r2-20261031
printf -v job '%q ' /usr/bin/python3 -B "$HERE/launch_calendar_job.py"
printf -v complete '%q ' /usr/bin/python3 -B "$HERE/consume_merged.py"
exec /bin/bash "$ENGINE/engine/filler_run13.sh" --id "$id" --class cpu --claim-cpus "$WS58_REGIONS" --role bench --gpu-quiet none \
    --min-window 1080 --cmd "taskset -c \"\$FILLER_CPUS\" $job" --complete-cmd "$complete" \
    --stop "$HERE/STOP" --workdir "$HERE"
