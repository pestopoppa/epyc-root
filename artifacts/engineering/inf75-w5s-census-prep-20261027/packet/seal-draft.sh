#!/bin/bash
set -euo pipefail
D=/mnt/raid0/llm/tmp/codex-ni-20261027-inf75-w4-census-prep/w5s
B=${D%/w5s}
N=/mnt/raid0/llm/tmp/codex-ni-20261027-inf75-census-prep
O="$B/orch-main"
R="$B/research-main"
J=/mnt/raid0/llm/tmp/refactor-01a16fc3/c5-candidate/jobs/cpu
[ -f "$D/recipes.json" ] && [ -f "$D/native-builder.json" ] && [ -f "$D/OWNER-RECIPE-BOUND.json" ]
{
 rg --files "$D/runtime/autokernel" "$B/root-main/scripts/vidya" | rg '\.py$'
 printf '%s\n' "$D/job.sh" "$D/launch.sh" "$D/driver.py" "$D/build_recipe.py" "$D/resolve_native_builder.py" "$D/recipes.json" "$D/native-builder.json" "$D/OWNER-RECIPE-BOUND.json" "$D/requests-prefill.json" "$D/requests-decode.json" "$D/requests-verify.json" "$D/deps/filler_run12.sh" "$D/deps/dryrun_check.py" "$D/server_probe_full.py" "$D/foreign_load.py" "$D/native-full-touch.py" "$D/verify_ggml_linkage.sh" "$B/private_census.py" "$B/flash_next_census.py" "$B/split_inspect.py" "$B/server_evidence_full.py" "$B/census_belief.py" "$B/model.sha256" "$N/affinity_scope.py" "$N/owner_start.py" "$N/orchestrator-native-export/scripts/server/stack_numa_evict.py" "$N/source-turn-2/libcensus-native.so" "$N/native_trace.c" "$R/orchestration/model_registry.yaml" "$O/orchestration/model_registry.yaml" "$O/orchestration/stack_topology.yaml" "$O/scripts/server/orchestrator_stack.py" "$O/scripts/server/stack_numa.py" "$O/scripts/server/stack_env.py" "$O/scripts/server/stack_manifest.py" "$O/scripts/server/stack_runtime.py"
 printf '%s\n' "$J/BUILD_COMPLETE" "$J/ELF.sha256" "$J/BUILD.log" "$J/job.sh" "$J/source-files.sha256" "$N/source-turn-2/instrument-identity.sha256"
 printf '%s\n' "$D/deps/dryrun_disk_policy.json" "$D/seal-draft.sh" "$D/rss_watch.py" "$D/pf-shim.sh" "$D/bind_recipe.py" "$D/BUILD-RECEIPT-PATH" "$D/PYTHON.sha256"
 printf '%s\n' "$D/window_test.py" "$B/flash_next_test.py" "$B/private_census_test.py" "$B/census_belief_test.py" "$B/shape_test.py" "$B/window-test.sh" "$B/model-free-tests.sh" "$B/complete-fixture.sh"
} | while IFS= read -r p; do realpath -e "$p"; done | sort -u | xargs -r sha256sum > "$D/SOURCES.sha256"
sha256sum -c "$D/SOURCES.sha256" > "$D/SOURCE-CHECK.log"
