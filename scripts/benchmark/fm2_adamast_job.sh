#!/bin/bash
# FM-2 Stage 1 job: sample -> normalize -> `adamast judge --taxonomy adamast/core/mast.json`, one judge call per trace,
# against a PRIVATE local llama-server (OpenAI-compatible). Runs inside a keeper grant only (see fm2_adamast_launch.sh).
# OUTCOME-BLIND: the normalizer strips outcome/final_gate_status; nothing here supplies an oracle. This is NOT a
# faithfulness measurement - the fixed catalog is applied as-is and the output is descriptive prevalence only.
# Resumable: sample manifest is frozen once; normalize and judge skip units already written.
# Required env (job refuses with rc 12 when unset; none is guessed):
#   FM2_RUN_DIR      run dir (scratch_root), e.g. /mnt/raid0/llm/tmp/fm2-adamast-20261110
#   FM2_ADAMAST_SRC  upstream AdaMAST checkout at 3c83d81c85937f5e8911fd96daa2ca38c1ad2585 with providers_base_url.patch applied
#   FM2_MODEL_GGUF   judge model GGUF (operator/registry choice; see ROW_SPEC.md "Undetermined")
#   FM2_SERVER_BIN   llama-server binary of a production-store kernel (cpu); LD_LIBRARY_PATH is set to its own dir
#   FM2_NORMALIZER   /abs/path/adamast_normalize.py (snapshot copy)
set -uo pipefail
: "${FM2_RUN_DIR:?}" "${FM2_ADAMAST_SRC:?}" "${FM2_MODEL_GGUF:?}" "${FM2_SERVER_BIN:?}" "${FM2_NORMALIZER:?}" \
  "${FILLER_CPUS:?}" "${FILLER_STOPFILE:?}" "${FILLER_THREADS:?}" "${FM2_PORT:?}" || exit 12
PY=/mnt/raid0/llm/epyc-orchestrator/.venv/bin/python     # explicit interpreter: has openai 2.31.0 (adamast deps not yet proven)
CLAUDE_ROOT=${FM2_CLAUDE_ROOT:-/home/node/.claude/projects/-workspace}
CODEX_ROOT=${FM2_CODEX_ROOT:-/home/node/.codex/sessions}
PER_STRATUM=${FM2_PER_STRATUM:-3}
SEED=${FM2_SEED:-fm2-adamast-20261110}
MAX_TRACE_CHARS=${FM2_MAX_TRACE_CHARS:-24000}
OUT=$FM2_RUN_DIR/out
mkdir -p "$OUT/traces" "$OUT/judged"
cd "$FM2_RUN_DIR"; ulimit -c 0
[ -e "$FILLER_STOPFILE" ] && { echo stop-file; exit 0; }
[ -x "$FM2_SERVER_BIN" ] && [ -s "$FM2_MODEL_GGUF" ] && [ -s "$FM2_ADAMAST_SRC/adamast/core/mast.json" ] || { echo "input missing"; exit 12; }
# content proof the patch is in the source tree (a directory name is not proof)
PATCHED="$(/usr/bin/grep -c 'ADAMAST_BASE_URL' "$FM2_ADAMAST_SRC/adamast/llm/providers.py")"
[ "${PATCHED:-0}" -ge 1 ] || { echo "providers.py lacks the base_url patch"; exit 12; }

# 1. frozen stratified sample (manifest written once; never re-sampled)
if [ ! -s "$OUT/manifest.json" ]; then
  ARGS=(--claude-root "$CLAUDE_ROOT")
  [ -d "$CODEX_ROOT" ] && ARGS+=(--codex-root "$CODEX_ROOT")
  /usr/bin/python3 -I -B "$FM2_NORMALIZER" sample "${ARGS[@]}" --per-stratum "$PER_STRATUM" --seed "$SEED" --manifest "$OUT/manifest.json.part" || exit 3
  mv -f "$OUT/manifest.json.part" "$OUT/manifest.json"
fi
# 2. normalize (--check: refuse if a sampled file's frozen prefix changed)
/usr/bin/python3 -I -B "$FM2_NORMALIZER" normalize --manifest "$OUT/manifest.json" --out-dir "$OUT" --check || exit 3

# 3. private judge server, own process group; pids captured by this job only
export LD_LIBRARY_PATH="$(dirname "$FM2_SERVER_BIN")"
taskset -c "$FILLER_CPUS" "$FM2_SERVER_BIN" -m "$FM2_MODEL_GGUF" --host 127.0.0.1 --port "$FM2_PORT" -t "$FILLER_THREADS" \
  -c 16384 -np 1 --jinja --reasoning off >"$OUT/server.log" 2>&1 &
SPID=$!
trap 'kill "$SPID" 2>/dev/null; sleep 5; ps -p "$SPID" >/dev/null 2>&1 && kill -9 "$SPID" 2>/dev/null; true' EXIT
for _ in $(seq 1 360); do
  /usr/bin/curl -sf "http://127.0.0.1:$FM2_PORT/health" >/dev/null 2>&1 && break
  ps -p "$SPID" >/dev/null 2>&1 || { echo "server died"; exit 4; }
  [ -e "$FILLER_STOPFILE" ] && exit 0
  sleep 5
done
# own-server proof: the listener on the port is OUR pid
LPID="$(ss -ltnpH "sport = :$FM2_PORT" | /usr/bin/sed -n 's/.*pid=\([0-9]*\).*/\1/p' | head -n1)"
[ "$LPID" = "$SPID" ] || { echo "port listener $LPID is not our server $SPID"; exit 4; }

# 4. one judge call per trace, resumable, stop-file honoured between traces
export OPENAI_API_KEY=local-not-a-secret ADAMAST_BASE_URL="http://127.0.0.1:$FM2_PORT/v1" PYTHONPATH="$FM2_ADAMAST_SRC"
rc=0
for T in "$OUT"/traces/*.jsonl; do
  [ -e "$FILLER_STOPFILE" ] && { echo "stop between items"; exit 0; }
  ID="$(basename "$T" .jsonl)"
  [ -s "$OUT/judged/$ID.json" ] && continue
  if "$PY" -B -m adamast judge --taxonomy "$FM2_ADAMAST_SRC/adamast/core/mast.json" --traces "$T" \
       --provider openai --model local --max-trace-chars "$MAX_TRACE_CHARS" --output "$OUT/judged/$ID.json.part"; then
    mv -f "$OUT/judged/$ID.json.part" "$OUT/judged/$ID.json"
    printf '{"unit_id":"%s","ok":true}\n' "$ID" >>"$OUT/results.jsonl"
  else
    printf '{"unit_id":"%s","ok":false}\n' "$ID" >>"$OUT/results.jsonl"; rc=1
  fi
done
exit $rc
