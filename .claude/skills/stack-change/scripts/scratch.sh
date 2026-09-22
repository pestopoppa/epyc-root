#!/bin/bash
# scratch.sh — phase 1. Copy every HAND-EDITED source from both repos into a
# scratch tree, so phases 2-5 can run without touching a real tree.
#
# WHY THIS EXISTS. On 2026-09-22 the transform ran directly against the real
# master registry. Two things followed. A subagent that had been told "the patch
# stays a patch" saw an unexplained modification and reverse-applied it --
# correctly, against the brief it held -- briefly undoing work the operator had
# asked for. And every preflight failure had to be fixed in place and re-run,
# one error at a time, nine pipeline runs in sixteen minutes with the stack down.
#
# A scratch tree fixes both: nothing to revert, and preflight can report every
# violation at once because it is reading a complete candidate, not a
# half-edited live tree.
set -euo pipefail

RESEARCH=/mnt/raid0/llm/epyc-inference-research
ORCH=/mnt/raid0/llm/epyc-orchestrator
TS="$(date -u +%Y%m%dT%H%M%SZ)"
DEST="${1:-/mnt/raid0/llm/tmp/stack-change-${TS}}"

# The hand-edited source set, from DERIVATION.md. Derived files are NOT copied:
# a scratch copy of a generated file is a trap, because editing it there looks
# like it worked and is discarded at the next compile.
RESEARCH_SRC=( orchestration/model_registry.yaml )
ORCH_SRC=(
  orchestration/stack_topology.yaml
  orchestration/launch_manifest.yaml
  scripts/server/stack_numa.py
  src/config/models.py
  src/roles.py
  stack_templates/default.yaml
)

mkdir -p "$DEST/research" "$DEST/orchestrator"
missing=0
for f in "${RESEARCH_SRC[@]}"; do
  if [ ! -f "$RESEARCH/$f" ]; then echo "MISSING source: $RESEARCH/$f" >&2; missing=1; continue; fi
  mkdir -p "$DEST/research/$(dirname "$f")"; cp -p "$RESEARCH/$f" "$DEST/research/$f"
done
for f in "${ORCH_SRC[@]}"; do
  if [ ! -f "$ORCH/$f" ]; then echo "MISSING source: $ORCH/$f" >&2; missing=1; continue; fi
  mkdir -p "$DEST/orchestrator/$(dirname "$f")"; cp -p "$ORCH/$f" "$DEST/orchestrator/$f"
done
[ "$missing" -eq 0 ] || { echo "REFUSING: a declared source is absent; the source set in DERIVATION.md is stale" >&2; exit 2; }

# Provenance: the exact commits the scratch was taken from, so the package can
# say what it was diffed against and `git apply` cannot land on a moved tree.
{
  echo "{"
  echo "  \"schema\": \"epyc.stack_change_scratch.v1\","
  echo "  \"taken_at\": \"$(date -u +%Y-%m-%dT%H:%M:%SZ)\","
  echo "  \"research_head\": \"$(git -C "$RESEARCH" rev-parse HEAD 2>/dev/null)\","
  echo "  \"orchestrator_head\": \"$(git -C "$ORCH" rev-parse HEAD 2>/dev/null)\","
  echo "  \"research_dirty\": $(git -C "$RESEARCH" diff --quiet 2>/dev/null && echo false || echo true),"
  echo "  \"orchestrator_dirty\": $(git -C "$ORCH" diff --quiet 2>/dev/null && echo false || echo true)"
  echo "}"
} > "$DEST/PROVENANCE.json"

echo "scratch: $DEST"
echo "  research     : ${#RESEARCH_SRC[@]} file(s)"
echo "  orchestrator : ${#ORCH_SRC[@]} file(s)"
echo "  provenance   : $DEST/PROVENANCE.json"
grep -qE '"(research|orchestrator)_dirty": true' "$DEST/PROVENANCE.json" && \
  echo "  NOTE: a source tree has uncommitted changes; the package diffs against the WORKING TREE, not HEAD"
exit 0
