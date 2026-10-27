#!/bin/bash
set -euo pipefail
D=/mnt/raid0/llm/tmp/codex-ni-20261027-next-ranked-launcher/chat
[ "${FILLER_ID:?}" = rte-log-chat-live ]
[ ! -e "$D/STOP" ]
! compgen -G '/mnt/raid0/llm/tmp/compute-flags/HOLD_*' >/dev/null
sha256sum -c "$D/SOURCES.sha256"
if [ "${FILLER_PREFLIGHT:-0}" = 1 ]; then
 python3 -B "$D/deps/dryrun_check.py" boundary --effect rte-before-http --job "$D/job.sh"
 exit 0
fi
[ "${FILLER_CPUS:?}" = 0-95 ]
[ "$(awk '/Cpus_allowed_list/ {print $2}' /proc/self/status)" = 0-95 ]
[ -s "$D/binding.json" ]
ulimit -v 4194304
exec python3 -B "$D/probe.py" "$D/binding.json"
