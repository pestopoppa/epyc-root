#!/bin/bash
set -euo pipefail
ID=evl46-crm-posthash-20261104
D=/mnt/raid0/llm/tmp/canonical-judge-suite-revamp/live-pair-20261104
PY=/mnt/raid0/llm/epyc-orchestrator/.venv/bin/python
TOOL=/mnt/raid0/llm/worktrees/codex-evl46-live-source/scripts/autopilot/evals/dtap/tools/crm_posthash.py
APP=/mnt/raid0/llm/worktrees/codex-evl46-live-source
PYTHONPATH="$APP/scripts/autopilot/evals/dtap:$APP" "$PY" - "$D/source.json" <<'PY_SOURCE'
import json, pathlib, sys
from harness.crm_source_manifest import verify_manifest
path=pathlib.Path(sys.argv[1]); source=json.loads(path.read_bytes())
verify_manifest(path, 'ec063054d2d7e2e801b130d124fec18683a96a15', source['source_tree_sha256'])
PY_SOURCE
if [[ "${FILLER_DRYRUN:-0}" == 1 ]]; then
  # crm_posthash's dry branch emits a synthetic fixture record, never a live model result.
  exec "$PY" "$TOOL"
fi
[[ "${FILLER_ID:-}" == "$ID" ]] || { echo "unexpected row id" >&2; exit 64; }
[[ -n "${FILLER_DEADLINE:-}" && -n "${FILLER_STOPFILE:-}" ]] || { echo "missing rowflow deadline/stop contract" >&2; exit 64; }
RUN="$D/run"
[[ -f "$RUN/claim.close.json" && -s "$RUN/journal.jsonl" ]] || { echo "parent close or pair journal missing" >&2; exit 65; }
[[ -s "$D/input.json" && -s "$D/posthash/config.json" ]] || { echo "preflight input/config missing" >&2; exit 65; }
python3 - "$D/posthash/config.json" "$D/input.json" "$RUN/claim.close.json" "$RUN/journal.jsonl" "$D/posthash/posthash.json" <<'PY'
import json, pathlib, sys
cfg = json.loads(pathlib.Path(sys.argv[1]).read_text())
expected = dict(input_manifest=sys.argv[2], claim_close=sys.argv[3], pair_journal=sys.argv[4], posthash_result=sys.argv[5])
if cfg != expected: raise SystemExit(f"config paths differ from completed parent pair: {cfg!r}")
PY
export CRM_POSTHASH_CONFIG="$D/posthash/config.json"
exec "$PY" "$TOOL"
