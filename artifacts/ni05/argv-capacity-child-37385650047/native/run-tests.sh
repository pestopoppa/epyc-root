#!/usr/bin/env bash
set -euo pipefail
umask 077
cd "$APP_CHECKOUT"
mkfifo -m 600 "$RESULT_DIR/stdout.pipe" "$RESULT_DIR/stderr.pipe"
tee "$RESULT_DIR/pytest.stdout" < "$RESULT_DIR/stdout.pipe" &
stdout_tee=$!
tee "$RESULT_DIR/pytest.stderr" < "$RESULT_DIR/stderr.pipe" >&2 &
stderr_tee=$!
env_args=(
  "PATH=$UV_PROJECT_ENVIRONMENT/bin:/usr/local/bin:/usr/bin:/bin"
  "TMPDIR=$RUNNER_PRIVATE_TMP" "XDG_CACHE_HOME=$RUNNER_PRIVATE_CACHE"
  "CI=true" "ORCHESTRATOR_MOCK_MODE=true"
  "MODULE_ID=$MODULE_ID" "MODULE_PATH=$MODULE_PATH"
  "EXPECTED_CASES=$EXPECTED_CASES" "RESULT_DIR=$RESULT_DIR"
  "UV_PROJECT_ENVIRONMENT=$UV_PROJECT_ENVIRONMENT"
  "ORCHESTRATOR_PATHS_LLAMA_CPP_BIN=$ORCHESTRATOR_PATHS_LLAMA_CPP_BIN"
  "ORCHESTRATOR_PATHS_LLAMA_MTMD=$ORCHESTRATOR_PATHS_LLAMA_MTMD"
  "ORCHESTRATOR_PATHS_LLAMA_SERVER=$ORCHESTRATOR_PATHS_LLAMA_SERVER"
  "EPYC_RESEARCH_ROOT=$EPYC_RESEARCH_ROOT"
  "AUTOPILOT_EVAL_ID_VOCAB_SOURCES=$AUTOPILOT_EVAL_ID_VOCAB_SOURCES"
  "PYTHONUNBUFFERED=1" "PYTHONNOUSERSITE=1" "PYTHONDONTWRITEBYTECODE=1"
)
if [[ ${HOME+x} ]]; then env_args+=("HOME=$HOME"); fi
setsid env -i "${env_args[@]}" "$UV_PROJECT_ENVIRONMENT/bin/python" -m pytest \
  -vv --tb=short -p no:cacheprovider --basetemp="$RESULT_DIR/pytest-tmp" \
  --rootdir="$APP_CHECKOUT" "$MODULE_PATH" \
  --junitxml="$RESULT_DIR/original-pytest.xml" \
  > "$RESULT_DIR/stdout.pipe" 2> "$RESULT_DIR/stderr.pipe" &
test_pgid=$!
printf '%s\n' "$test_pgid" > "$RESULT_DIR/test-pgid"
chmod 600 "$RESULT_DIR/test-pgid"
deadline=$((SECONDS + INNER_TIMEOUT_SECONDS))
timed_out=0
while jobs -pr | grep -Fxq "$test_pgid"; do
  if (( SECONDS >= deadline )); then
    timed_out=1
    kill -TERM -- "-$test_pgid" 2>/dev/null || true
    for _ in $(seq 1 20); do
      jobs -pr | grep -Fxq "$test_pgid" || break
      sleep 1
    done
    if jobs -pr | grep -Fxq "$test_pgid"; then
      kill -KILL -- "-$test_pgid" 2>/dev/null || true
    fi
    break
  fi
  sleep 1
done
set +e
wait "$test_pgid"
test_status=$?
wait "$stdout_tee"
stdout_status=$?
wait "$stderr_tee"
stderr_status=$?
set -e
rm -f "$RESULT_DIR/stdout.pipe" "$RESULT_DIR/stderr.pipe" "$RESULT_DIR/test-pgid"
if [[ "$timed_out" == 1 ]]; then test_status=124; fi
python - "$RESULT_DIR/test-status.json" "$test_status" "$timed_out" "$stdout_status" "$stderr_status" <<'PY'
import json, sys
from pathlib import Path
target = Path(sys.argv[1])
target.write_text(json.dumps({"schema": "ni63_66.test_status.v1",
    "exit_code": int(sys.argv[2]), "inner_timeout": bool(int(sys.argv[3])),
    "stdout_tee_exit": int(sys.argv[4]), "stderr_tee_exit": int(sys.argv[5])},
    sort_keys=True) + "\n", encoding="utf-8")
target.chmod(0o600)
PY
exit "$test_status"
