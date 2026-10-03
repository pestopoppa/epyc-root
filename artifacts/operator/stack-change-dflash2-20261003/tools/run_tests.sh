#!/bin/bash
# Serial (no xdist) test run on one sandbox — light on the shared host while DS41 A/Bs run.
# usage: run_tests.sh <base|new>
set -uo pipefail
PKG=/mnt/raid0/llm/tmp/stack-change-dflash2-20261003
S="$PKG/sandbox-$1/orchestrator"
PY=/mnt/raid0/llm/epyc-orchestrator/.venv/bin/python
cd "$S" || exit 2
export PYTHONDONTWRITEBYTECODE=1
PROMOTION=(tests/unit/test_stack_change_pipeline_simulated_fixtures.py tests/unit/test_build_server_command_helpers.py
           tests/unit/test_seeding_infra.py tests/unit/test_seeding_infra_additional.py
           tests/unit/test_seeding_infra_branching.py tests/unit/test_seed_specialist_routing_main_and_retry.py)
RELATED=(tests/unit/test_stack_change_pipeline.py tests/unit/test_registry_compiler.py tests/unit/test_stack_priors_compiler.py
         tests/unit/test_registry_validator.py tests/unit/test_orchestrator_stack_reload.py tests/unit/test_orchestrator_stack_threads.py
         tests/unit/test_orchestrator_stack_validate_only.py tests/unit/test_orchestrator_stack_import_is_argv_safe.py
         tests/unit/test_stack_manifest_imports.py tests/unit/test_stack_change_guard.py tests/unit/test_default_template_topology_parity.py
         tests/unit/test_stack_numa.py tests/unit/test_stack_numa_evict.py tests/unit/test_stack_numa_reader_agreement.py
         tests/unit/test_scheduling_contention.py tests/unit/test_scheduling_contention_gate.py tests/unit/test_contention_matrix_live_recert.py
         tests/unit/test_contention_matrix_shape_labels.py tests/unit/test_contention_unmeasured_leg.py tests/unit/test_topology_concurrency.py
         tests/unit/test_chat_vision.py tests/unit/test_vision_routing.py tests/unit/test_vision_tools.py tests/unit/test_backend_topology_aliases.py)
NEW=()
[ -f tests/unit/test_drafter_selection.py ] && NEW=(tests/unit/test_drafter_selection.py tests/unit/test_external_drafter_launch.py)
echo "== promotion-gate set"; timeout 1800 "$PY" -m pytest -q -p no:cacheprovider -p no:randomly "${PROMOTION[@]}" 2>&1 | tail -4
echo "== related set";        timeout 1800 "$PY" -m pytest -q -p no:cacheprovider -p no:randomly -rf "${RELATED[@]}" 2>&1 | grep -E "^FAILED|passed|failed|error" | tail -40
if [ ${#NEW[@]} -gt 0 ]; then
echo "== new tests";          timeout 600 "$PY" -m pytest -q -p no:cacheprovider "${NEW[@]}" 2>&1 | tail -2
fi
