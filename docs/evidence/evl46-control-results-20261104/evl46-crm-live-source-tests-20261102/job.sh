#!/bin/bash
set -euo pipefail
D=/mnt/raid0/llm/tmp/evl46-live-unit-20261102
ROOT=/mnt/raid0/llm/worktrees/codex-evl46-live-source
export PYTHONPATH="$ROOT/scripts/autopilot/evals/dtap:$ROOT"
cd "$ROOT"
python -c 'import json; from harness.crm_source_manifest import verify_manifest; p="/mnt/raid0/llm/tmp/evl46-live-unit-20261102/source.json"; x=json.load(open(p)); verify_manifest(p,x["source_commit"],x["source_tree_sha256"])'
if [[ ${FILLER_DRYRUN:-0} == 1 ]]; then
  LOG="${FILLER_DRYRUN_RESULT_PATH:?}.pytest.log"
  OUT="$FILLER_DRYRUN_RESULT_PATH"
else
  LOG="$D/pytest.log"
  OUT="$D/result.json"
fi
python -m pytest -q -p no:cacheprovider -c /dev/null --confcutdir=scripts/autopilot/evals/dtap/tests scripts/autopilot/evals/dtap/tests/test_crm_pair.py scripts/autopilot/evals/dtap/tests/test_tool_contract.py | tee "$LOG"
python "$D/result.py" "$LOG" "$OUT"
