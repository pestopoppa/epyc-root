#!/bin/bash
# compile.sh <sandbox-name> — phase-3 compile + check on one sandbox (base | new | pristine).
# Writes only inside the sandbox and evidence/. Reads the live state file (read-only copy)
# so runtime_attestation compares the candidate declarations against the LIVE fleet.
set -uo pipefail
PKG=/mnt/raid0/llm/tmp/stack-change-kvpool-20261003
NAME="${1:?usage: compile.sh <base|new|pristine>}"
S="$PKG/sandbox-$NAME"
E="$PKG/evidence"
PY=/mnt/raid0/llm/epyc-orchestrator/.venv/bin/python
MASTER="$S/research/orchestration/model_registry.yaml"
export PYTHONDONTWRITEBYTECODE=1
mkdir -p "$E" "$S/orchestrator/logs"
cp -p /mnt/raid0/llm/epyc-orchestrator/logs/orchestrator_state.json "$S/orchestrator/logs/"
cd "$S/orchestrator"
"$PY" scripts/registry/stack_change_pipeline.py update --research-registry "$MASTER" > "$E/pipeline-update-$NAME.txt" 2>&1; echo "update rc=$?" >> "$E/pipeline-update-$NAME.txt"
"$PY" scripts/registry/stack_change_pipeline.py check  --research-registry "$MASTER" > "$E/pipeline-check-$NAME.txt" 2>&1;  echo "check rc=$?"  >> "$E/pipeline-check-$NAME.txt"
"$PY" "$PKG/tools/capacity_report.py" . > "$E/capacity-$NAME.txt" 2>&1
"$PY" "$PKG/tools/render_argv.py" . architect_critic 8083 > "$E/argv_8083-$NAME.txt" 2>&1
for f in pipeline-update pipeline-check; do echo "== $f-$NAME"; grep -E "^[a-z_]+: |error:|rc=" "$E/$f-$NAME.txt" | cut -c1-220; done
grep -E "GATE|\"ok\"|required_gib|architect_critic" "$E/capacity-$NAME.txt"
tail -1 "$E/argv_8083-$NAME.txt"
