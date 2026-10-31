#!/bin/bash
# workspace-58 (calendar owner): RAM admission check, called by grant writers BEFORE writing a grant.
#   ram_admit.sh <need_gib> [ds41]
# exit 0 = admit: MemAvailable - need >= MARGIN_GIB (earlyoom fires at 40 GiB available, so the margin is 64),
#               and, with "ds41", no live process maps or names a DS41-1017 shard (one DS41-class server host-wide).
# exit 1 = refuse (reason on stdout). Read-only: never signals anything.
set -u
NEED=${1:?need_gib}; MODE=${2:-}
MARGIN_GIB=64
AVAIL=$(awk '/^MemAvailable:/{print int($2/1048576)}' /proc/meminfo)
if [ $(( AVAIL - NEED )) -lt $MARGIN_GIB ]; then
  echo "refuse: MemAvailable ${AVAIL} GiB - need ${NEED} GiB < margin ${MARGIN_GIB} GiB"; exit 1
fi
if [ "$MODE" = ds41 ]; then
  out=$(/mnt/raid0/llm/tmp/codex3-next-backlog-20261031-0255/r2/assert_not_mapped.sh \
    /mnt/raid0/llm/models/antirez/deepseek-v4.1-flash-gguf/DeepSeek-V4.1-Flash-1017-MXFP4-experts-00001-of-00009.gguf 2>&1)
  rc=$?
  if [ $rc -ne 0 ]; then echo "refuse: DS41-class server live: $(echo "$out" | tr '\n' ' ' | cut -c1-200)"; exit 1; fi
fi
echo "admit: MemAvailable ${AVAIL} GiB, need ${NEED} GiB${MODE:+, $MODE clear}"
