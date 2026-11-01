#!/bin/bash
set -euo pipefail
out=/mnt/raid0/llm/tmp/codex3-wrapup-20261101-current/docs-build
export PYTHONPATH="$out/deps:/mnt/raid0/llm/tmp/codex3-ci-actor-admission-20261101/deps"
export ORCH_REPO=/mnt/raid0/llm/epyc-orchestrator RES_REPO=/mnt/raid0/llm/epyc-inference-research
export PYTHONDONTWRITEBYTECODE=1
python3 -m pip install --target "$out/deps" -r requirements-docs.txt > "$out/install.log" 2>&1
bash scripts/docs/build-site-src.sh > "$out/populate.log" 2>&1
python3 scripts/docs/rewrite-links.py > "$out/rewrite.log" 2>&1
python3 scripts/docs/build-recent-results.py > "$out/recent.log" 2>&1
python3 -m mkdocs build --verbose > "$out/mkdocs.log" 2>&1
