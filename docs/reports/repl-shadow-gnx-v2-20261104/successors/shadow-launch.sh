#!/bin/bash
set -euo pipefail
D=/mnt/raid0/llm/tmp/agentic-serving-harness-fixes/shadow-pilot
PY=/mnt/raid0/llm/epyc-orchestrator/.venv/bin/python
printf '%s  %s\n' 5b38a8efa5796d36d5006e24fc944aa96dbd64b3acd623ce1247840f4340b7d2 "$D/pilot.py" | sha256sum -c --quiet -
exec /bin/bash /mnt/raid0/llm/tmp/compute-flags/bin/rowflow/filler_run15.sh --id ufh14-repl-emb23a-private-pilot-20261104 --class cpu --role bench --port 19081,19082,19083 --min-window 3600 --stop "$D/STOP" --workdir "$D" --cmd "exec $PY $D/pilot.py" --complete-cmd "test -s $D/out/run-complete"
