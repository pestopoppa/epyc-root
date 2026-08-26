#!/bin/bash
# R4b alias-ratification driver: generate worksheet -> interactive pass -> dry-run -> real emit -> verify.
# Usage:  bash scripts/vidya/ratify_aliases.sh [worksheet]
set -euo pipefail

WS="${1:-.vidya/aliases-worksheet.yaml}"
AT="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
ACTOR="${ALIAS_REVIEWER:-operator}"

if [ ! -f "$WS" ]; then
    echo "== generating worksheet (resumable; re-run keeps decisions) =="
    python3 scripts/vidya/cli.py alias-candidates --out "$WS" --at "$AT" --index research/intake_index.yaml
fi

echo "== interactive pass =="
if ! python3 scripts/vidya/alias_ratify.py --worksheet "$WS"; then
    PASS_RC=$?
else
    PASS_RC=0
fi
if [ "$PASS_RC" -eq 2 ]; then
    echo "quitting early — resume later with the same command; decisions already written are kept"
    exit 2
fi
# 0 = pass complete now; 3 = no rows were pending (already judged) — both proceed to emit

echo "== dry run (no ledger writes) =="
python3 scripts/vidya/cli.py alias-emit "$WS" --at "$AT" --actor "$ACTOR" --dry-run

echo "== real emit =="
python3 scripts/vidya/cli.py alias-emit "$WS" --at "$AT" --actor "$ACTOR"

echo "== verify chain + checkpoint =="
python3 scripts/vidya/cli.py verify
