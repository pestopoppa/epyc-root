#!/bin/bash
set -euo pipefail
B=/mnt/raid0/llm/tmp/codex-ni-20261027-inf75-w4-census-prep
N=/mnt/raid0/llm/tmp/codex-ni-20261027-inf75-census-prep
export PYTHONPATH="$B/w5s:$B:$N:$B/w5s/runtime"
exec /usr/bin/python3 -B "$B/w5s/window_test.py"
