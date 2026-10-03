#!/bin/bash
# Produce ONE patch per repo: hand-edited sources + code + tests. DERIVED files (lean,
# descriptors, priors, procedure enums, summary) are deliberately NOT in the patch: phase 7
# regenerates them with `stack_change_pipeline.py update` in the real tree (DERIVATION.md).
set -euo pipefail
PKG=/mnt/raid0/llm/tmp/stack-change-kvpool-20261003
A="$PKG/sandbox-base"      # git archive of the current HEADs
B="$PKG/sandbox-new"       # A + this change's source edits
OUT="$PKG/patches"
mkdir -p "$OUT/orchestrator" "$OUT/research"
ORCH_FILES=(
  scripts/registry/stack_change_pipeline.py
  src/backends/context_limits.py
  stack_templates/default.yaml
  tests/unit/test_context_limits_model_cap.py
  tests/unit/test_stack_change_pipeline.py
  tests/unit/test_stack_templates_v2.py
  tests/unit/test_kv_pool_long_prefill.py
)
emit() {  # emit <a-root> <b-root> <relpath>
  local a="$1/$3" b="$2/$3" la="a/$3"
  [ -e "$a" ] || { a=/dev/null; la=/dev/null; }
  diff -u --label "$la" --label "b/$3" "$a" "$b" || [ $? -eq 1 ]
}
{
  for f in "${ORCH_FILES[@]}"; do emit "$A/orchestrator" "$B/orchestrator" "$f"; done
} > "$OUT/orchestrator/stackchg-kvpool-20261003.orchestrator.patch"
emit "$A/research" "$B/research" orchestration/model_registry.yaml \
  > "$OUT/research/stackchg-kvpool-20261003.research.patch"
# Nothing else in the sandbox may differ from base except derived outputs and caches.
echo "== unlisted differences (derived outputs/caches expected only):"
diff -rq "$A/orchestrator" "$B/orchestrator" -x __pycache__ -x .pytest_cache -x logs 2>/dev/null \
  | grep -v -F -e src/backends/context_limits.py -e stack_templates/default.yaml \
      -e test_context_limits_model_cap.py -e scripts/registry/stack_change_pipeline.py -e tests/unit/test_stack_change_pipeline.py -e tests/unit/test_stack_templates_v2.py -e tests/unit/test_kv_pool_long_prefill.py || true
for p in "$OUT"/*/*.patch; do
  printf '%s  %s files, +%s -%s\n' "$p" "$(grep -c '^+++ ' "$p")" \
    "$(grep -c '^+[^+]' "$p")" "$(grep -c '^-[^-]' "$p")"
done
