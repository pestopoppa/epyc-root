#!/bin/bash
set -euo pipefail
unset PYTHONOPTIMIZE
HERE=$(dirname "$(readlink -f "$0")")
if [ "${1:-}" = --cpu-control ]; then
    [ "$#" -eq 3 ] || exit 64
    [ -z "${WS58_REGIONS:-}" ] || { echo 'CPU control cannot borrow calendar grant' >&2; exit 64; }
    (cd "$HERE"; sha256sum -c PACKAGE-SHA256SUMS >/dev/null)
    exec /usr/bin/python3 -B "$HERE/cpu_server_control.py" "$2" "$3"
fi
[ "$#" -eq 0 ] || exit 64
: "${WS58_REGIONS:?actual GPU calendar grant required}"
if [ "$(/usr/bin/gcc -dumpfullversion 2>/dev/null || true)" != 15.2.0 ]; then
    exec sudo -n env -u DOCKER_HOST -u DOCKER_CONTEXT docker exec --user 1000:1000 -e WS58_REGIONS="$WS58_REGIONS" epyc-root /bin/bash "$HERE/frontdoor.sh"
fi
exec /bin/bash "$HERE/calendar.sh"
