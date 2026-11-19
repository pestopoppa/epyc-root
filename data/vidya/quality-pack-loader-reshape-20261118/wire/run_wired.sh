#!/bin/bash
set -euo pipefail

ROOT=/mnt/raid0/llm/worktrees/mains/h-vidya-belief-substrate
D=/mnt/raid0/llm/tmp/vidya-belief-substrate/loader-diag-wire-20261118
cd "$D"
if [[ ${FILLER_DRYRUN:-0} == 1 ]]; then
    exec /usr/bin/python3 -B "$D/capture.py"
fi
rc=0
/usr/bin/python3 -B "$D/capture.py" || rc=$?
if [[ $rc -gt 1 ]]; then
    exit "$rc"
fi
/usr/bin/python3 -B - "$D/out/RESULT.json" <<'PY'
from pathlib import Path
import json
import os
import sys
from cpu_native import budget, deadline_epoch
from qwen4exp_cpu_loader_contract import TERMINAL

if json.loads(Path(sys.argv[1]).read_bytes())['status'] not in TERMINAL:
    raise SystemExit(1)
budget(deadline_epoch(os.environ['FILLER_DEADLINE']), Path(os.environ['FILLER_STOPFILE']), 1)
PY
exec /usr/bin/python3 -BI "$ROOT/scripts/vidya/canary/qwen4exp_cpu_loader_context.py" \
    "$D/out/qwen4exp_cpu_loader_diagnostic.json" "$D/out/planning-context" "$rc"
