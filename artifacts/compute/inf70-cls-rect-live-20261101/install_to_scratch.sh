#!/bin/bash
set -euo pipefail
SRC=/workspace/artifacts/compute/inf70-cls-rect-live-20261101
D=/mnt/raid0/llm/tmp/inf70-cls-rect-live-20261101
mkdir -p "$D"
test -x /mnt/raid0/llm/epyc-root/scripts/coordination/rowflow/filler_run15.sh
test -r /mnt/raid0/llm/epyc-root/scripts/inf70/harness1/client.py
install -m 0755 "$SRC/launcher.sh" "$SRC/run_live_arm.sh" "$D/"
install -m 0644 "$SRC/live_arm.py" "$SRC/validate_complete.py" "$D/"
mkdir -p "$D/state" "$D/results" "$D/evidence"
echo "installed CLS-RECT-1a row files into $D; spec remains at $SRC/spec.json"
