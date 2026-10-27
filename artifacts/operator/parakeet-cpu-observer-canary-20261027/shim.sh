#!/bin/bash
set -euo pipefail
[ "${FILLER_PREFLIGHT:-0}" = 1 ]
[ "${#DRYRUN_NONCE}" -ge 32 ]
[ "$(awk '/Cpus_allowed_list/ {print $2}' /proc/self/status)" = 48-49 ]
[ "$1" = run ]; shift
while [ "$#" -gt 0 ] && [ "$1" != -- ]; do shift; done
[ "$#" -gt 0 ]; shift
exec "$@"
