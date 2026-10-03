#!/bin/bash
# rebase_sandboxes.sh — the orchestrator HEAD moved under preparation (2586a7bb, KV-pool
# decision step 1, touches src/backends/context_limits.py). Save this change's edited files,
# rebuild base/new from the CURRENT HEADs, and carry over every edited file whose base is
# unchanged at the new HEAD. context_limits.py is re-done by hand on the new base.
set -euo pipefail
PKG=/mnt/raid0/llm/tmp/stack-change-kvpool-20261003
ORCH=/mnt/raid0/llm/epyc-orchestrator
W="$PKG/work"
CARRY=(scripts/registry/stack_change_pipeline.py tests/unit/test_stack_change_pipeline.py stack_templates/default.yaml)
mkdir -p "$W/old-base" "$W/mine"
for f in "${CARRY[@]}" src/backends/context_limits.py tests/unit/test_context_limits_model_cap.py; do
  mkdir -p "$W/mine/$(dirname "$f")" "$W/old-base/$(dirname "$f")"
  cp -p "$PKG/sandbox-new/orchestrator/$f" "$W/mine/$f"
  if [ -f "$PKG/sandbox-base/orchestrator/$f" ]; then cp -p "$PKG/sandbox-base/orchestrator/$f" "$W/old-base/$f"; fi
done
cp -p "$PKG/sandbox-new/research/orchestration/model_registry.yaml" "$W/mine/master.yaml"
for f in "${CARRY[@]}"; do
  git -C "$ORCH" show "HEAD:$f" | cmp -s - "$W/old-base/$f" || { echo "REFUSING: $f moved at HEAD; re-do by hand" >&2; exit 3; }
  echo "unchanged at HEAD: $f"
done
rm -rf "$PKG/sandbox-base" "$PKG/sandbox-new" "$PKG/sandbox-pristine"
bash "$PKG/tools/build_sandbox.sh" base 2>&1 | grep -v safe.directory
bash "$PKG/tools/build_sandbox.sh" new 2>&1 | grep -v safe.directory
for f in "${CARRY[@]}" tests/unit/test_context_limits_model_cap.py; do
  cp -p "$W/mine/$f" "$PKG/sandbox-new/orchestrator/$f"
done
cp -p "$W/mine/master.yaml" "$PKG/sandbox-new/research/orchestration/model_registry.yaml"
echo "rebased onto orchestrator $(git -C "$ORCH" rev-parse --short HEAD)"
