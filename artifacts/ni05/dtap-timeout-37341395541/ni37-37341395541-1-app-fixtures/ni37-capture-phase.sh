#!/bin/bash
set -u
phase=$1
shift
python - "$phase" <<'PY'
import json, os, sys
from pathlib import Path
phase = sys.argv[1]
context = {
    "phase": phase,
    "scope": "approved synthetic DTAP fixture command; real trusted producer/judges and sole verifier reader, no endpoint request",
    "app_source_sha": os.environ["APP_SOURCE_SHA"],
    "root_source_sha": os.environ["SOURCE_SHA"],
    "dependency_scope": "pytest9.1.1 plus PyYAML6.0.3 from the checked-in app uv.lock; selected recorded dependency alignment, not a full frozen lock install",
    "native_write_boundary": "opt-in run_matrix original pre-request before any endpoint factory/run; original traces and terminal recomputation before receipt",
    "primary_metrics": "benign task_success higher; attack_success lower; count/rate components descriptive",
    "censoring": "actual terminal native TimeoutError only; recovered retries not censored; non-timeout errors retained in finished denominator; empty rate null",
    "private_custody": "owned 0700 test hierarchy under runner HOME; original source/trace/request/terminal/receipt bodies remain private and are not uploaded",
    "public_proof": "existing CI original JUnit/log/readset; root phase generated safe five-unit fixture projection and native artifact digests only, no private filenames/body/argv",
    "applicability": "synthetic reviewed dry-run fixtures and typed fault controls only; network calls replaced by named urlopen fixture",
    "command_time_limit_s": 180,
    "termination_policy": "inner SIGINT then SIGKILL after 15 seconds",
    "outer_capture_time_limit_s": 240,
    "outer_termination_policy": "native CI producer SIGTERM then SIGKILL after 15 seconds; interrupted or incomplete originals remain diagnostic",
    "exclusions": ["live transport applicability", "inference", "production/provider access", "performance", "promotion", "field robustness rates", "entire dependency completeness", "private body/filename/argv export", "old-run backfill"]}
with open(phase + "-context.json", "x") as output:
    json.dump(context, output, indent=2, sort_keys=True)
    output.write("\n")
PY
read_args=(--read-path "$phase-context.json"
  --read-path "$GITHUB_WORKSPACE/recipe/.github/workflows/ni37-dtap-timeout-validation.yml"
  --read-path ni37-capture-phase.sh --read-path scripts/ci/native_conformance.py
  --read-path scripts/vidya/adapters/dtap_timeout_report.py
  --read-path scripts/vidya/adapters/ci_conformance.py
  --read-path scripts/vidya/claim_tuple.py --read-path scripts/vidya/canonical.py
  --read-path scripts/vidya/frames.py --read-path scripts/vidya/ledger.py
  --read-path scripts/vidya/cli.py --read-path scripts/vidya/ingest_sources.py
  --read-path tests/vidya/test_dtap_timeout_report.py
  --read-path tests/vidya/test_ingest_sources.py
  --read-path "$GITHUB_WORKSPACE/app-source/uv.lock"
  --read-path "$GITHUB_WORKSPACE/app-source/scripts/autopilot/evals/dtap/cases.json"
  --read-path "$GITHUB_WORKSPACE/app-source/scripts/autopilot/evals/dtap/README.md"
  --read-path "$GITHUB_WORKSPACE/app-source/scripts/autopilot/evals/dtap/tests/conftest.py"
  --read-path "$GITHUB_WORKSPACE/app-source/scripts/autopilot/evals/dtap/tests/test_dtap_harness.py"
  --read-path "$GITHUB_WORKSPACE/app-source/scripts/autopilot/evals/dtap/tests/test_judge_guard.py")
for input in "$PWD"/scripts/vidya/adapters/*.py \
  "$GITHUB_WORKSPACE"/app-source/scripts/autopilot/evals/dtap/harness/*.py \
  "$GITHUB_WORKSPACE"/app-source/scripts/autopilot/evals/dtap/harness/shims/*.py \
  "$GITHUB_WORKSPACE"/app-source/scripts/autopilot/evals/dtap/judges/*/judge.py \
  "$GITHUB_WORKSPACE"/app-source/scripts/autopilot/evals/dtap/fixtures/*.json; do
  read_args+=(--read-path "$input")
done
generated_args=()
if test "$phase" = ni37-app-fixtures; then
  select_args=(--select scripts/autopilot/evals/dtap/tests/test_dtap_harness.py
    --select scripts/autopilot/evals/dtap/tests/test_judge_guard.py)
else
  select_args=(--select tests/vidya/test_dtap_timeout_report.py
    --select tests/vidya/test_ingest_sources.py)
  generated_args=(--generated-output ni37-safe-native-projection.json)
fi
timeout --signal=TERM --kill-after=15s 240s python scripts/ci/native_conformance.py \
  --cwd "$PWD" --junit "$phase.xml" --output "native-$phase" \
  --repo "root_source=$PWD" --repo "recipe=$GITHUB_WORKSPACE/recipe" \
  --repo "app_source=$GITHUB_WORKSPACE/app-source" \
  "${read_args[@]}" "${select_args[@]}" "${generated_args[@]}" -- \
  timeout --signal=INT --kill-after=15s 180s "$@"
status=$?
if test -f "native-$phase/command.log"; then cat "native-$phase/command.log"; fi
exit "$status"
