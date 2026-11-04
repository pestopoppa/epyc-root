#!/bin/bash
set -euo pipefail
P=/mnt/raid0/llm/tmp/agentic-serving-harness-fixes/gs-frozen-query-v2
ID=ufh12-gs-frozen-query-v2-20261104
if [[ ${1-} == --complete ]]; then [[ -s "$P/DONE.json" ]]; exit $?; fi
if [[ ${1-} == --job ]]; then
 sha256sum --quiet -c "$P/source.sha256"
 /usr/bin/python3 -B "$P/check_inputs.py"
 export OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 PYTHONDONTWRITEBYTECODE=1
 exec /mnt/raid0/llm/epyc-orchestrator/.venv/bin/python -B "$P/run.py"
fi
[[ $# == 0 ]] || exit 64
exec /bin/bash /mnt/raid0/llm/tmp/compute-flags/bin/rowflow/filler_run15.sh --id "$ID" --class cpu --role bench --port 19111,19112 --min-window 5400 --cmd "/bin/bash $P/launch.sh --job" --stop "$P/STOP" --complete-cmd "/bin/bash $P/launch.sh --complete" --workdir "$P"
