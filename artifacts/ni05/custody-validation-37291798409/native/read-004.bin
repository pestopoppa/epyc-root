#!/bin/bash
set -euo pipefail

: "${ORCHESTRATOR_ROOT:?set to checkout of the pinned orchestrator source}"
EXPECTED_SOURCE_COMMIT=3047a02211c97fd1d5071b7665bf2ae4e08925a9
EXPECTED_SOURCE_SHA256=b9c84d5a751934a078c4590a9a57083e11d0d4cc7497b45a5a8b3cbe53503566
SOURCE="$ORCHESTRATOR_ROOT/scripts/benchmark/package_a_instrumented_eval.sh"
HEALTH_BLOCK_START='# Health check — require API availability before starting the eval.'
HEALTH_BLOCK_END='# Create output directory'
TMP_ROOT="${RUNNER_TEMP:-/tmp}"
TMP_DIR="$(mktemp -d "$TMP_ROOT/ni24-health-preflight.XXXXXX")"
trap 'rm -rf "$TMP_DIR"' EXIT
BLOCK="$TMP_DIR/health-preflight.sh"

actual_commit="$(git -C "$ORCHESTRATOR_ROOT" rev-parse HEAD)"
[[ "$actual_commit" == "$EXPECTED_SOURCE_COMMIT" ]]
printf '%s  %s\n' "$EXPECTED_SOURCE_SHA256" "$SOURCE" | sha256sum -c -

awk -v start="$HEALTH_BLOCK_START" -v end="$HEALTH_BLOCK_END" '
  $0 == start { copying=1; found_start=1 }
  $0 == end && copying { found_end=1; exit }
  copying { print }
  END { if (!found_start || !found_end) exit 1 }
' "$SOURCE" > "$BLOCK"

/bin/bash -n "$SOURCE"
/bin/bash -n "$BLOCK"
if grep -Eq '(^|[[:space:]])(fuser|kill|nohup|uvicorn|sleep)([[:space:]]|$)|orchestrator_stack\.py' "$BLOCK"; then
  echo 'FAIL: health preflight includes process lifecycle behavior' >&2
  exit 1
fi

run_probe() {
  local curl_rc="$1" output status
  set +e
  output="$(CURL_RC="$curl_rc" BLOCK_PATH="$BLOCK" /bin/bash -euo pipefail -c '
    curl() { return "$CURL_RC"; }
    source "$BLOCK_PATH"
    printf "%s\n" "__AFTER_PREFLIGHT__"
  ' 2>&1)"
  status=$?
  set -e
  printf '%s\n' "$output"
  return "$status"
}

set +e
healthy_output="$(run_probe 0)"
healthy_status=$?
failed_output="$(run_probe 22)"
failed_status=$?
set -e

[[ "$healthy_status" -eq 0 ]]
grep -Fq '✓ Orchestrator healthy' <<<"$healthy_output"
grep -Fq '__AFTER_PREFLIGHT__' <<<"$healthy_output"
[[ "$failed_status" -eq 1 ]]
grep -Fq 'health check failed at http://localhost:8000/health' <<<"$failed_output"
grep -Fq 'owning session' <<<"$failed_output"
! grep -Fq '__AFTER_PREFLIGHT__' <<<"$failed_output"

printf 'NI24 preflight source and both curl outcomes passed; no real API or lifecycle command invoked.\n'
