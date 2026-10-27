#!/bin/bash
set -euo pipefail
B=/mnt/raid0/llm/tmp/codex-ni-20261027-inf75-w4-census-prep
D="$B/w5s"
N=/mnt/raid0/llm/tmp/codex-ni-20261027-inf75-census-prep
bash "$B/inspect-split.sh"
bash "$B/census-belief-test.sh"
bash "$B/flash-next-test.sh"
bash "$B/private-census-test.sh"
bash "$B/shape-test.sh"
bash "$B/window-test.sh"
export ORCHESTRATOR_REGISTRY_NO_COMPILE=1 PYTHONPATH="$B/orch-main:$B/research-main"
cd "$B/orch-main"
/mnt/raid0/llm/tmp/refactor-01a16fc3/ci/phase-b-candidate-venv/bin/python -B "$D/resolve_native_builder.py"
/usr/bin/python3 -B "$D/build_recipe.py"
/usr/bin/python3 -B "$D/bind_recipe.py"
