#!/bin/bash
set -uo pipefail
D=/mnt/raid0/llm/tmp/gpu-serving-tie-in/p5-sphinx-second-20261104
python3 /mnt/raid0/llm/worktrees/mains/h-gpu-serving-tie-in/scripts/utils/safe_download.py --dest "$D" -- docker pull swebench/sweb.eval.x86_64.sphinx-doc_1776_sphinx-8593@sha256:bf09a4f64ca8a2dd3c9e2d252d640ed0239e6b2927fa524e40b6cde7aa0fafc0
rc=$?
printf "%s\n" "$rc" > "$D/pull.exit"
if [[ "$rc" == 0 ]]; then touch "$D/pull.done"; else touch "$D/pull.failed"; fi
exit "$rc"
