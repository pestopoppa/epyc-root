#!/bin/bash
# STEP 3b: LOAD-ONLY PREFLIGHT. Can the candidate open every model in the derived scope?
#
# 2026-09-22: the champion could not load the gemma4 MTP drafter -- contradictory
# n_layer_nextn invariants, a standalone NextN head where nextn == n_layer_all. Four of
# eight gated CPU roles were unservable. It was found by a FAILED BENCH ARM, an hour into
# a bench window. Loading every in-scope model once takes minutes and needs no bench,
# no recipe and no comparator.
#
# One load per DISTINCT (model, draft model) pair, at a token context, `--no-warmup`,
# no requests. The pair matters: the gemma4 defect was in the DRAFTER, and a target-only
# load would have passed it.
#
# Without --apply this is a DRY RUN: it still asserts every precondition (binary, model
# files, draft files, free probe port) and exits non-zero if any fails. With --apply it
# starts one server at a time, waits for /health, and stops the PID IT CAPTURED --
# SIGTERM, confirm dead, escalate to SIGKILL. It never pattern-matches a process name.
#
# usage: loadcheck.sh <candidate-build-dir> [--backend cpu|gpu] [--apply] [--port N]
set -euo pipefail
ORCH="${ORCH:-/mnt/raid0/llm/epyc-orchestrator}"
BUILD="${1:?usage: loadcheck.sh <candidate-build-dir> [--backend cpu|gpu] [--apply] [--port N]}"
shift
BACKEND=""; APPLY=0; PORT=18777
while [ $# -gt 0 ]; do
  case "$1" in
    --backend) BACKEND="$2"; shift 2 ;;
    --apply) APPLY=1; shift ;;
    --port) PORT="$2"; shift 2 ;;
    *) echo "FAIL: unknown argument $1"; exit 2 ;;
  esac
done

BIN="$BUILD/bin/llama-server"
[ -x "$BIN" ] || { echo "FAIL: no executable llama-server at $BIN"; exit 1; }

cd "$ORCH"
TMP=$(mktemp -t loadcheck-plan.XXXXXX.json)
trap 'rm -f "$TMP" "$TMP.plan"' EXIT
ARGS=(--json); [ -n "$BACKEND" ] && ARGS+=(--backend "$BACKEND")
uv run python scripts/validate/kernel_freeze_scope.py "${ARGS[@]}" > "$TMP"

# Join the derived scope to the priors' launch REQUIREMENTS, which is where the draft
# model path lives. Emits one plan line per distinct (model, draft) pair.
SCOPE_JSON="$TMP" uv run python - > "$TMP.plan" <<'PY'
import json, os, sys
from pathlib import Path
import yaml

scope = json.loads(Path(os.environ["SCOPE_JSON"]).read_text())
priors = yaml.safe_load(Path("orchestration/derived/stack_priors.yaml").read_text())

req = {}
def walk(node):
    if isinstance(node, dict):
        if "launch" in node and isinstance(node["launch"], dict):
            r = (node["launch"].get("requirements") or {})
            if node.get("server_role"):
                req[node["server_role"]] = r
        for v in node.values():
            walk(v)
    elif isinstance(node, list):
        for v in node:
            walk(v)
walk(priors)

seen, problems = {}, []
for backend, rows in sorted(scope.items()):
    for row in rows:
        r = req.get(row["role"], {})
        draft = r.get("draft_model_path") or ""
        key = (backend, row["model_path"], draft)
        seen.setdefault(key, []).append(row["role"])
for (backend, model, draft), roles in sorted(seen.items()):
    for p in (model, draft):
        if p and not Path(p).exists():
            problems.append(f"{backend}: missing file for {','.join(roles)}: {p}")
    # '|' and not '\t': tab is an IFS WHITESPACE character, so `read` collapses two
    # adjacent tabs and an empty draft field silently shifts every later field left.
    print("|".join([backend, model, draft, ",".join(sorted(roles))]))
if problems:
    print("\n".join("PROBLEM\t" + p for p in problems), file=sys.stderr)
    sys.exit(1)
PY

echo "== load-only preflight plan =="
N=0
while IFS='|' read -r B MODEL DRAFT ROLES; do
  N=$((N+1))
  echo "  [$B] $(basename "$MODEL")"
  [ -n "$DRAFT" ] && echo "        + draft $(basename "$DRAFT")"
  echo "        roles: $ROLES"
done < "$TMP.plan"
echo "  $N distinct load(s); binary $BIN"

if ss -ltnH "sport = :$PORT" 2>/dev/null | grep -q .; then
  echo "FAIL: probe port $PORT is in use; pass --port with a free one"; exit 1
fi

if [ "$APPLY" != 1 ]; then
  echo "DRY RUN: preconditions asserted, nothing loaded. Re-run with --apply to load."
  exit 0
fi

RC=0
while IFS='|' read -r B MODEL DRAFT ROLES; do
  echo "== loading $(basename "$MODEL") [$B] =="
  CMD=("$BIN" -m "$MODEL" --host 127.0.0.1 --port "$PORT" -c 4096 --no-warmup)
  [ -n "$DRAFT" ] && CMD+=(--model-draft "$DRAFT")
  [ "$B" = "gpu" ] && CMD+=(-ngl 999)
  LOG=$(mktemp -t loadcheck.XXXXXX.log)
  env -u LD_LIBRARY_PATH "${CMD[@]}" >"$LOG" 2>&1 &
  PID=$!                     # the ONLY pid this script will ever signal
  OK=0
  for _ in $(seq 1 180); do
    if ! kill -0 "$PID" 2>/dev/null; then break; fi
    if curl -sf "http://127.0.0.1:$PORT/health" >/dev/null 2>&1; then OK=1; break; fi
    sleep 1
  done
  if [ "$OK" = 1 ]; then
    echo "  LOADED"
  else
    echo "  FAIL: did not reach /health (roles affected: $ROLES). Last lines:"
    tail -15 "$LOG" | sed 's/^/     /'
    RC=1
  fi
  if kill -0 "$PID" 2>/dev/null; then
    kill -TERM "$PID" 2>/dev/null || true
    for _ in $(seq 1 30); do kill -0 "$PID" 2>/dev/null || break; sleep 1; done
    if kill -0 "$PID" 2>/dev/null; then
      kill -KILL "$PID" 2>/dev/null || true; sleep 2
    fi
    if kill -0 "$PID" 2>/dev/null; then
      echo "  FAIL: pid $PID survived SIGKILL -- stop and resolve by hand"; RC=1
    fi
  fi
  rm -f "$LOG"
done < "$TMP.plan"

[ "$RC" = 0 ] && echo "LOAD PREFLIGHT PASS" || echo "LOAD PREFLIGHT FAIL"
exit $RC
