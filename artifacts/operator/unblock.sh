#!/bin/bash
# unblock.sh — THE one command on return (rider R8).
#
# Applies every operator gate you ticked in
# coordination/session-bus/tokens/token-queue.md, skips the rest, and reports
# what it did. Add --plan to see what it would run without running anything.
#
# Deliberately a thin wrapper and NOT a generated, revision-pinned script: a new
# applier file per repair would be a new ratification chain in all but name, and
# MEASUREMENT_POLICY §Consolidated apply-time ratification forbids restarting a
# chain on repair. Repair re-presents the SAME gate with updated pins.
#
# This never commits, never `git add`s, and writes no bus file other than its
# receipt — single-writer stays intact and the coordinator-daemon transcribes the
# outcome on its next tick.
set -euo pipefail
exec /workspace/scripts/coordination/unblock_artifact.py apply "$@"
