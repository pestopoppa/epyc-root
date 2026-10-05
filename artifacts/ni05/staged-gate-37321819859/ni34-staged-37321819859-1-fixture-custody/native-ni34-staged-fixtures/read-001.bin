#!/bin/bash
set -uo pipefail
phase="$1"; junit="$2"; limit="$3"; shift 3
python - "$phase" "$limit" <<'PY'
import json, os, sys
phase, limit = sys.argv[1:]
context = {"phase": phase, "scope": "offline root hook fixture command; private sub-gate originals remain in runner-private Git common storage and are never uploaded",
           "command_time_limit_s": int(limit), "termination_policy": "SIGINT then SIGKILL after 15 seconds",
           "configuration": {"NI31_NATIVE_ORIGINALS": os.environ.get("NI31_NATIVE_ORIGINALS", ""),
                             "NI31_POLICY_ORIGINALS": os.environ.get("NI31_POLICY_ORIGINALS", "")},
           "exclusions": ["inference", "live providers", "production kernel/store mutation", "API/unit replay", "entire-index privacy attestation", "dependency completeness", "private indexed filenames/bodies/logs", "original private sub-gate capsules"],
           "wrapper_context": "/workspace symlink to pinned root source; root /mnt/raid0/llm/epyc-root alias to the same source for the real Hermes checker; two empty disposable sibling Git repos; real generated installed wrappers and tracked root extras",
           "input_custody": "unchanged original runs 37299780302 and 37307260869 prefixes; complete digest manifest, no resealing or new historical tuples"}
with open(phase + "-context.json", "x") as output:
    json.dump(context, output, indent=2, sort_keys=True)
    output.write("\n")
PY
read_args=(--read-path ni34-capture-phase.sh --read-path "$phase-context.json"
  --read-path ni34-input-manifest.json
  --read-path "$GITHUB_WORKSPACE/recipe/.github/workflows/ni34-staged-gate-validation.yml"
  --read-path scripts/ci/native_conformance.py
  --read-path scripts/vidya/adapters/ci_conformance.py --read-path scripts/vidya/claim_tuple.py
  --read-path scripts/hooks/pii_staged_capture.py
  --read-path scripts/vidya/adapters/pii_staged_gate.py
  --read-path scripts/vidya/ingest_sources.py --read-path scripts/vidya/cli.py
  --read-path scripts/hooks/tests/test_pii_staged_capture.py
  --read-path tests/vidya/test_ingest_sources.py
  --read-path scripts/hooks/fixture_snapshot_provenance.py
  --read-path scripts/hooks/install_git_hooks.sh --read-path scripts/hooks/pre-commit.extras
  --read-path scripts/hooks/hermes_drift_precommit.sh --read-path scripts/hooks/observer_census_precommit.sh
  --read-path scripts/hooks/check_test_collectability.py
  --read-path scripts/hermes/skills/check_drift.py
  --read-path scripts/coordination/observer_census.py
  --read-path scripts/coordination/observer_registry.json
  --read-path .git/hooks/pre-commit --read-path .git/hooks/pre-commit.extras
  --read-path scripts/hooks/tests/test_fixture_snapshot_provenance.py
  --read-path scripts/hooks/tests/test_policy_snapshot_provenance.py
  --read-path scripts/hooks/tests/test_hook_worktree_resolution.py
  --read-path scripts/hooks/tests/test_precommit_wrapper.sh
  --read-path scripts/validate/pii_fixture_eval.py
  --read-path ni31-originals/ordinary-guards/native-ordinary-guards/receipt.json
  --read-path ni31-originals/ordinary-guards/native-ordinary-guards/execution-request.json
  --read-path ni31-originals/unit-synthetic/native-unit-synthetic/receipt.json
  --read-path ni31-originals/unit-synthetic/native-unit-synthetic/execution-request.json
  --read-path ni31-policy-originals/fixture-custody/native-ni31-fixture-custody/receipt.json
  --read-path ni31-policy-originals/fixture-custody/native-ni31-fixture-custody/execution-request.json
  --read-path ni31-policy-originals/caller-gates/native-ni31-caller-gates/receipt.json
  --read-path ni31-policy-originals/caller-gates/native-ni31-caller-gates/execution-request.json)
select_args=(--select NI34 --select "$phase")
if test "$phase" = ni34-staged-fixtures; then
  select_args+=(--select scripts/hooks/tests/test_pii_staged_capture.py
    --select scripts/hooks/tests/test_fixture_snapshot_provenance.py
    --select scripts/hooks/tests/test_policy_snapshot_provenance.py)
else
  select_args+=(--select scripts/validate/pii_fixture_eval.py
    --select scripts/hooks/tests/test_precommit_wrapper.sh
    --select scripts/hooks/tests/test_hook_worktree_resolution.py
    --select tests/vidya/test_ingest_sources.py::test_every_source_is_a_cli_choice_and_the_literal_list_does_not_drift
    --select tests/vidya/test_ingest_sources.py::test_every_source_has_an_end_to_end_fixture_or_a_named_exemption)
fi
python scripts/ci/native_conformance.py --cwd "$PWD" --junit "$junit" --output "native-$phase" \
  --repo "root_source=$PWD" --repo "recipe=$GITHUB_WORKSPACE/recipe" \
  "${read_args[@]}" "${select_args[@]}" -- \
  timeout --signal=INT --kill-after=15s "${limit}s" "$@"
status=$?
if test -f "native-$phase/command.log"; then cat "native-$phase/command.log"; fi
exit "$status"
