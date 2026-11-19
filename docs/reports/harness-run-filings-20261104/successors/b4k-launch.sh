#!/bin/bash
set -euo pipefail
D=/mnt/raid0/llm/tmp/agentic-serving-harness-fixes/b4k-successor
PY=/mnt/raid0/llm/epyc-orchestrator/.venv/bin/python
printf '%s  %s\n' da58a571f991181407e496f28fc4d2129ece21e2e7271c4edddfaecbc7430692 "$D/job.py" | sha256sum -c --quiet -
exec /bin/bash /mnt/raid0/llm/tmp/compute-flags/bin/rowflow/filler_run15.sh --id ufh14-b4k-nothink-successor-20261104 --class gpu --role bench --gpu-quiet exclusive --claim-cpus 184-191 --port 18183 --min-window 10800 --stop "$D/STOP" --workdir "$D" --precond-cmd "$PY $D/job.py --check" --cmd "exec $PY $D/job.py" --complete-cmd "test -s $D/out/COMPLETE"
