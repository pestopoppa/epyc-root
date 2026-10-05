#!/bin/bash
set -uo pipefail
phase="$1"
junit="$2"
context="$3"
shift 3
python - "$phase" "$context" <<'CONTEXT'
import json, os, sys
phase, context = sys.argv[1:]
allowed = ("CI", "ORCHESTRATOR_MOCK_MODE", "ORCHESTRATOR_PATHS_LLAMA_CPP_BIN",
           "ORCHESTRATOR_PATHS_LLAMA_MTMD", "ORCHESTRATOR_PATHS_LLAMA_SERVER")
record = {"phase": phase, "context": context,
          "configuration": {key: os.environ.get(key, "") for key in allowed},
          "synthetic_host_ram_gib": 1024 if context == "synthetic-host-unit" else None,
          "command_time_limit_s": 360 if context == "synthetic-host-unit" else None,
          "termination_policy": "SIGINT then SIGKILL after 30 seconds" if context == "synthetic-host-unit" else "",
          "scope_completion": "time-bounded attempt; interruption does not establish full unit completion" if context == "synthetic-host-unit" else "named selected fixture cases",
          "excluded_collection_modules": (["tests/unit/test_gpu_shadow_lane.py",
               "tests/unit/test_gpu_shadow_lane_p2.py", "tests/unit/test_gpu_shadow_lane_preflight.py"]
               if context == "synthetic-host-unit" else []),
          "excluded_live_nodes": (["tests/unit/test_openai_backend.py::TestOpenAIBackendIntegration",
               "tests/unit/test_anthropic_backend.py::TestAnthropicBackendIntegration",
               "tests/unit/test_prompt_compressor.py::TestPromptCompressorIntegration::test_real_compression",
               "tests/unit/test_pdf_router.py::TestPDFRouterIntegration",
               "tests/unit/test_retrieval.py::test_cross_encoder_real_model_discriminates"]
               if context == "synthetic-host-unit" else
               ["tests/unit/test_openai_backend.py::TestOpenAIBackendIntegration"]
               if phase.startswith("api-") else []),
          "live_exclusion_reason": "provider inference, real LLMLingua/ONNX model, or host PDF tool fixtures outside offline scope",
          "exclusion_reason": "strict production GPU store import contract; no offhost store fabricated"
               if context == "synthetic-host-unit" else ""}
with open(phase + "-context.json", "x") as output:
    json.dump(record, output, sort_keys=True)
CONTEXT
read_args=(--read-path ni05-capture-phase.sh --read-path "$phase-context.json"
  --read-path ci-control/.github/workflows/ni05-candidate-validation.yml
  --read-path root-capture-binding/scripts/ci/native_conformance.py
  --read-path root-capture-binding/scripts/vidya/adapters/ci_conformance.py
  --read-path root-capture-binding/scripts/vidya/claim_tuple.py
  --read-path root-capture-binding/scripts/vidya/ingest_sources.py
  --read-path root-capture-binding/scripts/vidya/cli.py
  --read-path tests/conftest.py --read-path src/features.py
  --read-path src/api/routes/config.py --read-path src/runtime/config_attestation.py
  --read-path src/config/__init__.py --read-path src/config/models.py
  --read-path src/registry/kernel_paths.py
  --read-path src/scheduling/device_model.py --read-path scripts/server/stack_manifest.py
  --read-path scripts/benchmark/md_self_draft_ab.py
  --read-path scripts/corpus/build_static_ngram_cache.py
  --read-path tests/fixtures/offhost_unit_bootstrap.py
  --read-path orchestration/model_registry_full.yaml
  --read-path orchestration/launch_manifest.yaml
  --read-path orchestration/gpu_shadow_lane_np_ceiling.yaml)
# Explicit declared readscope; this is not a claim to include all dependencies.
python -c 'import sys; from pathlib import Path; sources = [str(p) for p in sorted(Path("tests/unit").rglob("*.py")) if p.is_file()]; assert sources, "empty declared unit readscope"; Path(sys.argv[1]).open("x").write("\n".join(sources) + "\n")' "$phase-unit-readpaths.txt" || exit "$?"
read_args+=(--read-path "$phase-unit-readpaths.txt")
while IFS= read -r source; do
  read_args+=(--read-path "$source")
done < "$phase-unit-readpaths.txt"
python root-capture-binding/scripts/ci/native_conformance.py \
  --cwd "$GITHUB_WORKSPACE" --junit "$junit" --output "native-$phase" \
  --repo "orchestrator=$GITHUB_WORKSPACE" \
  --repo "research=$GITHUB_WORKSPACE/research-binding" \
  --repo "root_capture=$GITHUB_WORKSPACE/root-capture-binding" \
  --repo "recipe=$GITHUB_WORKSPACE/ci-control" \
  "${read_args[@]}" --select "$phase" --select "$context" -- "$@"
capture_status=$?
if test -f "native-$phase/command.log"; then cat "native-$phase/command.log"; fi
exit "$capture_status"
