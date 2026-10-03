#!/bin/bash
# Serial (no xdist) test run on one sandbox — light on the shared host while DS41 A/Bs run.
# usage: run_tests.sh <base|new|pristine>
set -uo pipefail
PKG=/mnt/raid0/llm/tmp/stack-change-kvpool-20261003
S="$PKG/sandbox-$1/orchestrator"
PY=/mnt/raid0/llm/epyc-orchestrator/.venv/bin/python
cd "$S" || exit 2
export PYTHONDONTWRITEBYTECODE=1
# = stack_change_pipeline.PROMOTION_GATE_TARGETS
PROMOTION=(tests/unit/test_stack_change_pipeline_simulated_fixtures.py tests/unit/test_build_server_command_helpers.py
           tests/unit/test_seeding_infra.py tests/unit/test_seeding_infra_additional.py
           tests/unit/test_seeding_infra_branching.py tests/unit/test_seed_specialist_routing_main_and_retry.py)
# Compile/launch/guard chain (as the DFLASH2 precedent) + every consumer of the context limits
# and the drafter projection this change touches.
RELATED=(tests/unit/test_stack_change_pipeline.py tests/unit/test_registry_compiler.py tests/unit/test_stack_priors_compiler.py
         tests/unit/test_registry_validator.py tests/unit/test_orchestrator_stack_reload.py tests/unit/test_orchestrator_stack_threads.py
         tests/unit/test_orchestrator_stack_validate_only.py tests/unit/test_orchestrator_stack_import_is_argv_safe.py
         tests/unit/test_stack_manifest_imports.py tests/unit/test_stack_change_guard.py tests/unit/test_default_template_topology_parity.py
         tests/unit/test_stack_templates_v2.py tests/unit/test_model_descriptor_compiler.py
         tests/unit/test_stack_numa.py tests/unit/test_stack_numa_evict.py tests/unit/test_stack_numa_reader_agreement.py
         tests/unit/test_drafter_selection.py tests/unit/test_external_drafter_launch.py
         tests/unit/test_context_overflow_handling.py tests/unit/test_kv_pool_long_prefill.py tests/unit/test_oab8_scouts.py tests/unit/test_admission.py
         tests/unit/test_graph_compaction_budgets.py tests/unit/test_openai_compat_roles.py
         tests/unit/test_openai_compat_default_golden.py tests/unit/test_backend_topology_aliases.py)
NEW=()
[ -f tests/unit/test_context_limits_model_cap.py ] && NEW=(tests/unit/test_context_limits_model_cap.py)
echo "== promotion-gate set"; timeout 1800 "$PY" -m pytest -q -p no:cacheprovider -p no:randomly "${PROMOTION[@]}" 2>&1 | tail -1
echo "== related set";        timeout 1800 "$PY" -m pytest -q -p no:cacheprovider -p no:randomly -rf "${RELATED[@]}" 2>&1 | grep -E "^FAILED|^ERROR|passed|failed|error" | tail -40
if [ ${#NEW[@]} -gt 0 ]; then
echo "== new tests";          timeout 600 "$PY" -m pytest -q -p no:cacheprovider -p no:randomly "${NEW[@]}" 2>&1 | tail -1
fi
