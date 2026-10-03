#!/bin/bash
# repro_stale_priors.sh — evidence for the pipeline fix: the CANDIDATE sources with the
# UNPATCHED stack_change_pipeline.py, derived files at HEAD, ONE `update`, then `check`.
# Throwaway copy; deleted at the end.
set -uo pipefail
PKG=/mnt/raid0/llm/tmp/stack-change-kvpool-20261003
R="$PKG/sandbox-repro"
E="$PKG/evidence/pipeline-stale-priors-repro.txt"
PY=/mnt/raid0/llm/epyc-orchestrator/.venv/bin/python
export PYTHONDONTWRITEBYTECODE=1
rm -rf "$R"; mkdir -p "$R"
cp -a "$PKG/sandbox-new/orchestrator" "$R/orchestrator"
cp -a "$PKG/sandbox-new/research" "$R/research"
rm "$R/orchestrator/orchestration/model_registry_full.yaml"
ln -s "$R/research/orchestration/model_registry.yaml" "$R/orchestrator/orchestration/model_registry_full.yaml"
cp -p "$PKG/sandbox-base/orchestrator/scripts/registry/stack_change_pipeline.py" "$R/orchestrator/scripts/registry/"
git -C /mnt/raid0/llm/epyc-orchestrator archive HEAD orchestration/model_registry.yaml orchestration/model_descriptors.yaml \
  orchestration/derived/stack_priors.yaml docs/generated/current_stack_summary.md orchestration/procedures \
  orchestration/procedure.schema.json | tar -x -C "$R/orchestrator"
rm -f "$R/orchestrator/orchestration/.lean_cache_key"
cd "$R/orchestrator"
{
  echo "# candidate sources + UNPATCHED pipeline; derived files at HEAD; ONE update then check"
  echo "== update (once)"
  "$PY" scripts/registry/stack_change_pipeline.py update --research-registry "$R/research/orchestration/model_registry.yaml" 2>&1 \
    | grep -E "^[a-z_]+: |error:" | grep -v -E "^(warnings|surface_warnings|promotion_gate|surface_inventory):"
  echo "== priors written by that update:"
  grep -n "effective_context_tokens: \(196608\|393216\)" orchestration/derived/stack_priors.yaml
  echo "== check (fresh process)"
  "$PY" scripts/registry/stack_change_pipeline.py check --research-registry "$R/research/orchestration/model_registry.yaml" 2>&1 \
    | grep -E "^[a-z_]+: |error:" | grep -v -E "^(warnings|surface_warnings|promotion_gate|surface_inventory):"
} > "$E" 2>&1
cd "$PKG"; rm -rf "$R"
cat "$E"
