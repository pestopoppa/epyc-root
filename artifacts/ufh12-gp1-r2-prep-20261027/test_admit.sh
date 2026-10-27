#!/bin/bash
set -euo pipefail
D=/mnt/raid0/llm/tmp/codex-ni-20261027-ufh12-shipped-parity/successor
X="$D/admit-sandbox"
mkdir -p "$X/grants" "$X/state"
export FILLER_FLAGS_DIR="$X" FILLER_GRANTS_DIR="$X/grants" FILLER_STATE_DIR="$X/state" FILLER_POLL=1 FILLERS_MD="$X/ROW.md"
bash "$D/poller.sh" > "$X/poller.log" 2>&1 & pid=$!
cleanup() { kill -TERM "$pid" 2>/dev/null || true; wait "$pid" 2>/dev/null || true; sleep 3; if ps -p "$pid" >/dev/null; then echo 'poller not reaped' >&2; exit 70; fi; }
trap cleanup EXIT
sed -n '35,36p' /mnt/raid0/llm/tmp/compute-flags/FILLERS.md > "$X/ROW.md"
sed "s@; NO PID, CONDITIONAL@; pid=$pid@; s@| BACKLOG |@| ARMED |@; s@| n | n | /workspace@| n | y | /workspace@; s@blocker=harness fix: owner selects quarter and applies row; @@" "$D/ROW.md" >> "$X/ROW.md"
sleep 2
/usr/bin/python3 -B /mnt/raid0/llm/worktrees/ufh12-shipped-parity-root/scripts/coordination/validate_fillers.py --file "$X/ROW.md" --row codex-ni-ufh12-gp1-r2-20261027 --for-grant
GRANT_OK_TEST_FILLERS="$X/ROW.md" /mnt/raid0/llm/tmp/compute-flags/grant_ok.sh codex-ni-ufh12-gp1-r2-20261027 8 --window-s 1500 --regions 72-95 --pid "$pid"
