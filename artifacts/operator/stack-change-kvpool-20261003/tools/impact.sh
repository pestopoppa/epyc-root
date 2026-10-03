#!/bin/bash
# impact.sh — gitnexus upstream impact for every edited symbol, plus the structural
# (grep-derived) consumer set, because the orchestrator index is stale. Read-only.
set -uo pipefail
ORCH=/mnt/raid0/llm/epyc-orchestrator
cd "$ORCH"
echo "orchestrator HEAD $(git rev-parse --short HEAD); gitnexus index (built from /workspace/repos at an old commit):"
for s in parse_props ContextLimit observe _lean_registry_step run_stack_change_pipeline; do
  echo "=== gitnexus impact $s --direction upstream"
  timeout 120 gitnexus impact "$s" --direction upstream --repo "$ORCH" 2>&1 \
    | grep -E '"(error|risk|impactedCount|name|filePath)"|commits ahead' | head -8
done
echo
echo "=== STRUCTURAL consumers of the ContextLimit fields this change touches (git grep, HEAD)"
git grep -n -E 'pool_tokens|shared_pool|\.kv_unified|slot_n_ctx|cap_binding|limit_for_url|limit_for_role|\.observe\(' \
  -- 'src/*.py' | grep -v '^src/backends/context_limits.py' | grep -v review_ledger | grep -v v1_subagent_link
echo
echo "=== STRUCTURAL consumers of _lean_registry_step / stack_manifest import order"
git grep -n -E '_lean_registry_step|from scripts.server.stack_manifest import' -- scripts/registry/stack_change_pipeline.py
