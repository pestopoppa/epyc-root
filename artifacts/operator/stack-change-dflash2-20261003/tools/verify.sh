#!/bin/bash
# Phase-3/5 verification on sandbox-pristine = CURRENT HEADs (git archive) + this package's patches.
# Reads the live state file (read-only copy) so runtime attestation compares against the live fleet.
set -uo pipefail
PKG=/mnt/raid0/llm/tmp/stack-change-dflash2-20261003
S="$PKG/sandbox-pristine"
E="$PKG/evidence"
PY=/mnt/raid0/llm/epyc-orchestrator/.venv/bin/python
MASTER="$S/research/orchestration/model_registry.yaml"
export PYTHONDONTWRITEBYTECODE=1
mkdir -p "$E" "$S/orchestrator/logs"
cp -p /mnt/raid0/llm/epyc-orchestrator/logs/orchestrator_state.json "$S/orchestrator/logs/"
cd "$S/orchestrator"
"$PY" scripts/registry/stack_change_pipeline.py update --research-registry "$MASTER" > "$E/pipeline-update.txt" 2>&1
"$PY" scripts/registry/stack_change_pipeline.py check  --research-registry "$MASTER" > "$E/pipeline-check.txt" 2>&1
"$PY" "$PKG/tools/capacity_report.py" . > "$E/capacity.txt" 2>&1
"$PY" "$PKG/tools/render_argv.py" . architect_critic 8083 > "$E/argv_8083.txt" 2>&1
"$PY" -c "import sys; sys.path.insert(0,'.'); from scripts.server import orchestrator_stack as o; print(' '.join(o._build_vision_command(8086,'worker',0)))" > "$E/argv_8086.txt" 2>&1
sed -e "s|^ORCH=/mnt/raid0/llm/epyc-orchestrator\$|ORCH=$S/orchestrator|" \
    -e "s|^PY=\"\$ORCH/.venv/bin/python\"\$|PY=$PY|" \
    -e "s|check --numa-mode \"\$NUMA\"|check --numa-mode \"\$NUMA\" --research-registry $MASTER|" \
    /workspace/.claude/skills/stack-change/scripts/preflight.sh > "$PKG/tools/preflight_scratch.sh"
bash "$PKG/tools/preflight_scratch.sh" "$E/preflight-classified.txt" > /dev/null 2>&1; echo "preflight rc=$?" >> "$E/preflight-classified.txt"
bash "$PKG/tools/run_tests.sh" pristine > "$E/tests.txt" 2>&1
for f in pipeline-update pipeline-check; do echo "== $f"; grep -E "^[a-z_]+: |error:|BOOTSTRAP" "$E/$f.txt" | cut -c1-200; done
grep -E "GATE|\"ok\"|required_gib" "$E/capacity.txt"
tail -1 "$E/argv_8083.txt"; cat "$E/argv_8086.txt"; tail -1 "$E/preflight-classified.txt"
grep -E "^==|passed|failed|^FAILED" "$E/tests.txt"
