#!/bin/bash
set -euo pipefail
D=/mnt/raid0/llm/tmp/codex3-evl34-r11-budget-v7-ab-20261030
M=/mnt/micron/codex3-evl34-deepdive-r9-20261030
cd "$D"
[[ $(id -u) == 1000 ]]
export PATH=/opt/rocm/bin:/usr/bin:/bin PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/mnt/micron/codex3-lanes/orchestrator:/mnt/raid0/llm/epyc-orchestrator/.venv/lib/python3.11/site-packages
case "${1:-}" in
 --preflight) exec "$M/bin/python3.11" -B "$D/source_preflight.py";;
 --smoke) exec "$M/bin/python3.11" -B "$D/campaign_smoke.py" --calibration-smoke48;;
 --job) exec "$M/bin/python3.11" -B "$D/campaign_job.py";;
 *) exit 64;;
esac
