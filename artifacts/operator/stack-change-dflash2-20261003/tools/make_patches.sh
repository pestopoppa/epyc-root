#!/bin/bash
# Produce ONE patch per repo: hand-edited sources + code + tests + the DECLARED contention
# matrix withdrawal. DERIVED files (lean, descriptors, priors, procedure enums, summary) are
# deliberately NOT in the patch: phase 7 regenerates them with `stack_change_pipeline.py update`
# in the real tree (DERIVATION.md: never hand-carry a derived file).
set -euo pipefail
PKG=/mnt/raid0/llm/tmp/stack-change-dflash2-20261003
A="$PKG/sandbox-base"      # pristine 2d97ade2 / 7b9bc565 sources (derived regenerated in-sandbox; excluded)
B="$PKG/sandbox-new"
OUT="$PKG/patches"
mkdir -p "$OUT/orchestrator" "$OUT/research"
ORCH_FILES=(
  orchestration/stack_topology.yaml
  orchestration/launch_manifest.yaml
  orchestration/contention_matrix.yaml
  stack_templates/default.yaml
  src/registry/drafter_selection.py
  src/registry/registry_compiler.py
  src/registry/registry_validator.py
  src/registry/stack_priors.py
  scripts/registry/stack_change_pipeline.py
  scripts/server/autokernel_enrollment.py
  scripts/server/orchestrator_stack.py
  scripts/server/stack_commands.py
  tests/unit/test_drafter_selection.py
  tests/unit/test_external_drafter_launch.py
  tests/unit/test_build_server_command_helpers.py
  tests/unit/test_orchestrator_stack_reload.py
  tests/unit/test_orchestrator_stack_threads.py
  tests/unit/test_scheduling_contention.py
  tests/unit/test_stack_change_pipeline.py
  tests/unit/test_stack_numa_evict.py
  tests/unit/test_stack_priors_compiler.py
)
emit() {  # emit <a-root> <b-root> <relpath>
  local a="$1/$3" b="$2/$3" la="a/$3"
  [ -e "$a" ] || { a=/dev/null; la=/dev/null; }
  diff -u --label "$la" --label "b/$3" "$a" "$b" || [ $? -eq 1 ]
}
{
  for f in "${ORCH_FILES[@]}"; do emit "$A/orchestrator" "$B/orchestrator" "$f"; done
} > "$OUT/orchestrator/stackchg-dflash2-20261003.orchestrator.patch"
emit "$A/research" "$B/research" orchestration/model_registry.yaml \
  > "$OUT/research/stackchg-dflash2-20261003.research.patch"
for p in "$OUT"/*/*.patch; do
  printf '%s  %s files, +%s -%s\n' "$p" "$(grep -c '^+++ ' "$p")" \
    "$(grep -c '^+[^+]' "$p")" "$(grep -c '^-[^-]' "$p")"
done
