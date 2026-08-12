#!/bin/bash
# ---------------------------------------------------------------------------
# H-1 DISCARD — the scratch-pane verification protocol.
#
# WHAT IS STILL OPEN, AND WHY THIS IS A SCRIPT RATHER THAN A RUNBOOK PARAGRAPH.
# C55 measured, against live panes on 2026-08-12, that a Claude Code composer
# holding queued text ignores a BARE keystroke: `Enter`, `C-m`, `C-u` and a
# `BSpace` loop up to 100 iterations each left the text exactly where it was.
# Prefixing an ordinary character and a settle delay fixed SUBMIT. It did NOT
# fix DISCARD: `space` + `C-u` was never measured, and `Escape` — the obvious
# next candidate — is UNTESTED and hazardous to fire blind at a live main:
# a single Escape interrupts a running turn, and a double Escape opens the
# rewind picker. So the discard verb is deliberately NOT implemented on a guess
# (`tmux_adapter.py` still fails honestly instead); THIS SCRIPT is how that gap
# gets closed, by producing the measurement first.
#
# It runs the three candidates against a DISPOSABLE `claude` TUI in a scratch
# tmux session, re-reading the composer after each through the adapter's own
# read path (`_read_composer_row`) rather than by eye — the same instrument the
# adapter itself decides on, so a result here transfers to the adapter without
# a second interpretation step.
#
# NEVER RUN THIS AGAINST A ROSTER PANE. It types sacrificial text and presses
# interrupt-class keys. Two independent refusals below enforce that: the session
# name may not be the live session, and the resolved target may not be any
# endpoint in the roster.
#
# Results go in the C55 negative-results table style — the negative rows are the
# point, they are what cost an hour to establish the first time.
#
# Usage:  scripts/coordination/verify_composer_keys.sh [--session NAME] [--keep]
set -euo pipefail

REPO_ROOT="${REPO_ROOT:-/workspace}"
ADAPTER="$REPO_ROOT/scripts/coordination/tmux_adapter.py"
CONFIG="$REPO_ROOT/coordination/session-bus/config.yaml"
SESSION="composerkeys-$$"
WINDOW="scratch"
KEEP=0
SACRIFICIAL="SACRIFICIAL-TEXT-DO-NOT-SUBMIT-$$"
SETTLE_S=1.0
TUI_BOOT_S=12

while [[ $# -gt 0 ]]; do
    case "$1" in
        --session) SESSION="$2"; shift 2 ;;
        --keep)    KEEP=1; shift ;;
        -h|--help) sed -n '2,30p' "$0"; exit 0 ;;
        *) echo "unknown argument: $1" >&2; exit 2 ;;
    esac
done

PY="${PYTHON:-python3}"
command -v tmux >/dev/null || { echo "tmux not found" >&2; exit 3; }

# ---------------------------------------------------------------------------
# REFUSAL 1: the session name. `agent` is the live roster session, and so is
# whatever `tmux.live_session` currently says — read it rather than hardcoding
# it, because a config change must not silently un-protect the fleet.
# ---------------------------------------------------------------------------
LIVE_SESSION="$("$PY" - "$CONFIG" <<'EOF' || echo agent
import sys
try:
    import yaml
    cfg = yaml.safe_load(open(sys.argv[1], encoding="utf-8")) or {}
    print(str((cfg.get("tmux") or {}).get("live_session") or "agent"))
except Exception:
    print("agent")
EOF
)"
if [[ "$SESSION" == "agent" || "$SESSION" == "$LIVE_SESSION" ]]; then
    echo "REFUSING: --session $SESSION is the live roster session. This script types" >&2
    echo "sacrificial text and presses interrupt-class keys; it may only ever run in a" >&2
    echo "throwaway session. Pick another name." >&2
    exit 4
fi

# ---------------------------------------------------------------------------
# REFUSAL 2: the roster itself, derived from the DATA rather than from the one
# session name refusal 1 knows about. It refuses if the scratch session is the
# session component of ANY tmux roster endpoint, or if the exact target matches
# one. That is not a restatement of refusal 1: today every roster endpoint lives
# under `agent`, but the roster is edited by hand, and the day a row names a
# second session refusal 1 keeps passing while this one starts refusing. A guard
# whose only reachable case is another guard's case is not a guard.
#
# Fails CLOSED: an unreadable roster refuses, because "I could not check" is not
# "it is safe".
# ---------------------------------------------------------------------------
TARGET="$SESSION:$WINDOW"
ROSTER_VERDICT="$("$PY" - "$CONFIG" "$SESSION" "$TARGET" <<'EOF'
import sys
try:
    import yaml
    cfg = yaml.safe_load(open(sys.argv[1], encoding="utf-8")) or {}
except Exception as exc:
    print(f"REFUSE roster unreadable ({exc}) — fail closed")
    raise SystemExit(0)
session, target = sys.argv[2].strip(), sys.argv[3].strip()
for e in cfg.get("roster") or []:
    if not isinstance(e, dict):
        continue
    ep = str(e.get("endpoint") or "")
    if not ep.startswith("tmux:"):
        continue
    rest = ep.split(":", 1)[1].strip()
    if rest == target or rest.split(":")[0] == session:
        print(f"REFUSE {target} collides with roster endpoint {ep!r} ({e.get('id')})")
        raise SystemExit(0)
print("OK")
EOF
)"
if [[ "$ROSTER_VERDICT" != "OK" ]]; then
    echo "REFUSING: $ROSTER_VERDICT" >&2
    exit 4
fi

cleanup() {
    if [[ "$KEEP" == "1" ]]; then
        echo "--keep: leaving session $SESSION alive for inspection." >&2
        return
    fi
    tmux kill-session -t "$SESSION" 2>/dev/null || true
}
trap cleanup EXIT

# ---------------------------------------------------------------------------
# The read path is the ADAPTER'S OWN. Reading the composer with a bespoke
# capture-pane parser here would measure a different instrument than the one
# that has to act on the result.
# ---------------------------------------------------------------------------
read_composer() {
    "$PY" - "$ADAPTER" "$TARGET" <<'EOF'
import importlib.util, sys
spec = importlib.util.spec_from_file_location("ta_verify", sys.argv[1])
m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
row, failure = m._read_composer_row(sys.argv[2])
if failure:
    print(f"UNREADABLE: {failure}")
else:
    print((row or "").strip() or "<empty>")
EOF
}

holds_text() {   # 0 == the sacrificial text is still in the composer
    read_composer | grep -qF "$SACRIFICIAL"
}

RESULTS=()
record_result() {   # name, verdict, observed
    RESULTS+=("$1|$2|$3")
}

start_tui() {
    tmux kill-session -t "$SESSION" 2>/dev/null || true
    tmux new-session -d -s "$SESSION" -n "$WINDOW" claude
    sleep "$TUI_BOOT_S"
}

type_sacrificial() {
    # `-l` is literal: no key-name interpretation, so the text lands as text.
    tmux send-keys -t "$TARGET" -l "$SACRIFICIAL"
    sleep 2
}

# Each candidate gets a FRESH TUI. A candidate that half-worked would otherwise
# leave the pane in a state that decides the next candidate's result for it —
# and "the composer is empty" would then be evidence for the wrong key.
run_candidate() {   # label, then the key sequence as a shell function name
    local label="$1" runner="$2"
    start_tui
    type_sacrificial
    if ! holds_text; then
        record_result "$label" "INVALID" "sacrificial text never landed — candidate not tested"
        return
    fi
    "$runner"
    sleep 2
    local observed; observed="$(read_composer)"
    if [[ "$observed" == UNREADABLE:* ]]; then
        record_result "$label" "UNREADABLE" "$observed"
    elif echo "$observed" | grep -qF "$SACRIFICIAL"; then
        record_result "$label" "no-op; text stays" "$observed"
    else
        record_result "$label" "CLEARED" "$observed"
    fi
}

cand_space_ctrl_u() {
    tmux send-keys -t "$TARGET" " "
    sleep "$SETTLE_S"
    tmux send-keys -t "$TARGET" C-u
}

cand_space_escape() {
    tmux send-keys -t "$TARGET" " "
    sleep "$SETTLE_S"
    tmux send-keys -t "$TARGET" Escape
}

cand_bare_escape() {
    tmux send-keys -t "$TARGET" Escape
}

echo "scratch session : $SESSION   (live session is '$LIVE_SESSION' — not touched)"
echo "sacrificial text: $SACRIFICIAL"
echo

run_candidate "space + ${SETTLE_S}s + C-u"    cand_space_ctrl_u
run_candidate "space + ${SETTLE_S}s + Escape" cand_space_escape
run_candidate "bare Escape"                   cand_bare_escape

echo
echo "## Composer discard candidates — measured $(date -u +%Y-%m-%dT%H:%M:%SZ)"
echo
echo "| Sent | Result | Composer after |"
echo "|---|---|---|"
for r in "${RESULTS[@]}"; do
    IFS='|' read -r name verdict observed <<< "$r"
    printf '| `%s` | %s | %s |\n' "$name" "$verdict" "${observed:0:80}"
done
echo
echo "Known-negative baseline for comparison (C55, live panes, 2026-08-12):"
echo "\`Enter\` alone, \`C-m\` alone, bare \`Ctrl-U\`, \`BSpace\` x100 — all no-ops, text stays."
echo
echo "If exactly one candidate reads CLEARED, that is the sequence to implement as"
echo "the adapter's discard. If none does, discard stays unimplemented and the"
echo "adapter keeps failing honestly — do NOT ship a guess."
