#!/bin/bash
set -euo pipefail
B=/mnt/raid0/llm/tmp/codex-ni-20261027-ufh12-gs-rehearsal/wiring
FACET=${1:-scores}; [[ "$FACET" == scores || "$FACET" == tokens ]] || exit 64
STOP="$B/STOP.$FACET"
[[ ${FILLER_PREFLIGHT:-0} != 1 ]] || STOP="$B/T1-STOP"
exec /bin/bash "$B/deps/filler_run12.sh" --id "ufh12-gs-$FACET-20261027" --class cpu --no-fold-siblings --role build --gpu-quiet none --min-window 900 --stop "$STOP" --workdir "$B" --cmd "exec taskset -c \"\$FILLER_CPUS\" /mnt/raid0/llm/epyc-orchestrator/.venv/bin/python $B/deps/rss-watch.py /bin/bash $B/job.sh $FACET" --complete-cmd "test -s $B/COMPLETE.$FACET"
