#!/bin/bash
set -euo pipefail
W=/mnt/raid0/llm/tmp/emb-speed-20261020
export OMP_PROC_BIND=spread OMP_PLACES=cores OMP_WAIT_POLICY=active HF_HOME=$W/hf HF_HUB_OFFLINE=1
exec /workspace/repos/epyc-orchestrator/scripts/region-lock run --cpu-list 24-71 --role bench-cpu -- $W/venv/bin/python -I $W/bench2.py
