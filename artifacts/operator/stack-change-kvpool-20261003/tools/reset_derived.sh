#!/bin/bash
# reset_derived.sh <sandbox-name> — put the DERIVED files of a sandbox back to the committed
# HEAD state (git archive of the real orchestrator HEAD), so the next `update` starts from
# exactly what phase 7 starts from in the real tree. Read-only on the real repo.
set -euo pipefail
PKG=/mnt/raid0/llm/tmp/stack-change-kvpool-20261003
S="$PKG/sandbox-${1:?usage: reset_derived.sh <name>}/orchestrator"
ORCH=/mnt/raid0/llm/epyc-orchestrator
git -C "$ORCH" archive HEAD orchestration/model_registry.yaml orchestration/model_descriptors.yaml \
  orchestration/derived/stack_priors.yaml docs/generated/current_stack_summary.md \
  orchestration/procedures orchestration/procedure.schema.json | tar -x -C "$S"
rm -f "$S/orchestration/.lean_cache_key"
echo "derived files reset to $(git -C "$ORCH" rev-parse --short HEAD) in $S"
