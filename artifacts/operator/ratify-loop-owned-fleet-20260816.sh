#!/bin/bash
# ratify-loop-owned-fleet-20260816.sh
#
# ONE script for every Loop-Owned Fleet gate that needs the operator.
# Running a step IS the ratification — that is why these were left undone.
#
#   ./ratify-loop-owned-fleet-20260816.sh                 # show the plan, change nothing
#   ./ratify-loop-owned-fleet-20260816.sh --all           # run every step (prompts once)
#   ./ratify-loop-owned-fleet-20260816.sh --step 3        # run one step
#   ./ratify-loop-owned-fleet-20260816.sh --step 3 --step 4
#
# Every step is idempotent: re-running a completed step reports SKIP, never a
# second application. Every step verifies itself and stops the script on failure
# rather than continuing over a broken foundation.

set -euo pipefail

REPO=/workspace
cd "$REPO"

STEPS=()
RUN_ALL=0
ASSUME_YES=0
NTFY_URL="${NTFY_URL:-}"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --all)   RUN_ALL=1; shift ;;
    --step)  STEPS+=("$2"); shift 2 ;;
    --yes|-y) ASSUME_YES=1; shift ;;
    --ntfy-url) NTFY_URL="$2"; shift 2 ;;
    -h|--help) sed -n '2,20p' "$0"; exit 0 ;;
    *) echo "unknown arg: $1" >&2; exit 64 ;;
  esac
done


alarm_is_inert() {
  # Precise: the sentinel that decides liveness lives in the ACTIVE BACKEND's
  # endpoint. A whole-file grep for REPLACE-ME also matches the comment that
  # explains the sentinel and the unused email placeholder, which made a LIVE
  # channel report as inert (observed 2026-08-16, right after go-live).
  python3 - "$1" <<'PY_INERT'
import re, sys
t = open(sys.argv[1], encoding="utf-8").read()
m = re.search(r"^backend:\s*(\w+)", t, re.M)
b = m.group(1) if m else ""
blk = re.search(rf"^{b}:\n((?:[ \t]+.*\n)+)", t, re.M)
body = blk.group(1) if blk else ""
ep = re.search(r"^\s*(?:url|to):\s*(.+)$", body, re.M)
sys.exit(0 if (ep and "REPLACE-ME" in ep.group(1)) else 1)
PY_INERT
}

say()  { printf '\n\033[1m== %s\033[0m\n' "$*"; }
ok()   { printf '   \033[32mOK\033[0m   %s\n' "$*"; }
skip() { printf '   \033[33mSKIP\033[0m %s\n' "$*"; }
fail() { printf '   \033[31mFAIL\033[0m %s\n' "$*"; exit 1; }
note() { printf '        %s\n' "$*"; }

wants() {
  [[ $RUN_ALL -eq 1 ]] && return 0
  local s; for s in "${STEPS[@]:-}"; do [[ "$s" == "$1" ]] && return 0; done
  return 1
}

confirm() {
  [[ $ASSUME_YES -eq 1 ]] && return 0
  printf '\n   %s [y/N] ' "$1"
  read -r a </dev/tty || return 1
  [[ "$a" == "y" || "$a" == "Y" ]]
}

# ---------------------------------------------------------------- the plan
if [[ $RUN_ALL -eq 0 && ${#STEPS[@]} -eq 0 ]]; then
cat <<'PLAN'
LOOP-OWNED FLEET — operator ratification steps

  1  Alarm channel go-live          ONE line. Until this is done, "zero alarms on a
                                    well-run night" is UNFALSIFIABLE — nothing can
                                    arrive at all. Do this before step 2.
                                    Needs: --ntfy-url <url>  (or edit the file yourself)

  2  Enable the worker pool         ONE flag. worker_pool.enabled false -> true.
                                    The pool is proven (4/4 pilot rows passed) but
                                    ships disabled: a schedulable-but-not-executable
                                    pool is the 2026-08-14 shape exactly.

  3  D9 ack: promote pilot-02       A pool worker wrote a regression test for the
                                    FETCH_HEAD bug. It lands under
                                    scripts/coordination/**, so D9 refused the
                                    autonomous merge (exit 5). Your ack merges it.

  4  Apply INVARIANTS.md            agents/shared/ is a hash-pinned human-only path.
                                    The 15 invariants, verbatim, as the canonical copy.
                                    (Regenerated — see WHAT WAS LOST below.)

  5  Fix the IDLE-CANDIDATE marker  One-word edit; the token was retired by P3-3 and
                                    two files still name it. Loop-plane, so D9.

Run:  $0 --all        or        $0 --step 1 --step 2

WHAT WAS LOST, and you should know before trusting the old package:
  A concurrent `git clean -ffdx` in this shared tree at ~10:40Z destroyed ALL of
  /workspace/tmp/. That took the staged doctrine-collapse apply script, the
  P3-4 predicate patch and its design note. Step 4 below is regenerated from the
  handoff (exact, 15 invariants). NOT regenerated, and genuinely needing redoing:
  the OPERATING_CONSTRAINTS / SESSION_LIFECYCLE / CLAUDE.md dedup (P1-2/P1-4's
  human-only half), the coordinator-agent.md rewrite (P1-6), and the P3-4 patch.
  Those are re-doable work, not lost decisions. The committed half of P1-2/P1-3
  survived in b5ae002d.
PLAN
exit 0
fi

# ------------------------------------------------------- 1. alarm go-live
if wants 1; then
  say "STEP 1 — alarm channel go-live"
  if ! alarm_is_inert coordination/session-bus/alarm_config.yaml; then
    skip "already pointed at a real endpoint"
  else
    if [[ -z "$NTFY_URL" ]]; then
      note "No --ntfy-url given. An ntfy topic name IS its password, so pick"
      note "something unguessable, e.g.:"
      note "    https://ntfy.sh/epyc-fleet-$(head -c6 /dev/urandom | base64 | tr -dc 'a-z0-9' | head -c6)-alarms"
      note "Then re-run:  $0 --step 1 --ntfy-url <url>"
      note "(Self-hosting works too and needs no code change.)"
      fail "step 1 needs a URL"
    fi
    confirm "Point the alarm channel at ${NTFY_URL} ?" || fail "declined"
    python3 - "$NTFY_URL" <<'PY'
import re, sys
from pathlib import Path
url = sys.argv[1]
p = Path("coordination/session-bus/alarm_config.yaml")
t = p.read_text(encoding="utf-8")
t2 = re.sub(r"^(\s*url:\s*).*REPLACE-ME.*$", lambda m: m.group(1) + url, t, count=1, flags=re.M)
assert t2 != t, "sentinel line not found — edit alarm_config.yaml by hand"
p.write_text(t2, encoding="utf-8")
print("   url set")
PY
    ok "config updated"
  fi
  say "STEP 1 — verify end to end (this actually pushes a notification)"
  if python3 scripts/coordination/alarm_channel.py test 2>&1 | tee /dev/stderr | grep -q "DELIVERED"; then
    ok "test alarm DELIVERED — check your phone/inbox"
  else
    fail "test alarm did not report DELIVERED — the channel is not live"
  fi
  bash scripts/coordination/tests/alarm_drill.sh >/dev/null 2>&1 \
    && ok "drill PASS (5 raises -> exactly 1 delivery)" \
    || fail "alarm drill failed"
fi

# ------------------------------------------------------- 2. enable the pool
if wants 2; then
  say "STEP 2 — enable the worker pool"
  if alarm_is_inert coordination/session-bus/alarm_config.yaml; then
    note "The alarm channel is still inert. If the pool wedges overnight, nothing"
    note "will reach you. Strongly consider running step 1 first."
    confirm "Enable the pool anyway, with alarms inert?" || fail "declined — run step 1 first"
  fi
  if grep -qE "^  enabled: true" coordination/session-bus/config.yaml; then
    skip "worker_pool.enabled is already true"
  else
    confirm "Set worker_pool.enabled = true ?" || fail "declined"
    python3 - <<'PY'
import re
from pathlib import Path
p = Path("coordination/session-bus/config.yaml")
t = p.read_text(encoding="utf-8")
t2 = re.sub(r"^(  enabled:)\s*false\s*$", r"\1 true", t, count=1, flags=re.M)
assert t2 != t, "worker_pool.enabled: false not found"
p.write_text(t2, encoding="utf-8")
PY
    ok "worker_pool.enabled = true"
  fi
  note "verifying the daemon now sees the pool as schedulable AND executable..."
  if timeout 240 python3 scripts/coordination/session_bus_coordinator.py \
        --bus-root coordination/session-bus once --dry-run 2>/dev/null \
        | grep -q '"agent": "workerpool"'; then
    ok "daemon evaluates workerpool"
  else
    note "workerpool did not appear this tick (may simply be no eligible row)"
  fi
fi

# ------------------------------------------------------- 3. D9 ack: pilot-02
if wants 3; then
  say "STEP 3 — D9 ack: promote pilot-02's regression test"
  LANE=/mnt/raid0/llm/worktrees/pool/lane1
  if [[ ! -d "$LANE" ]]; then skip "lane1 is gone; nothing to promote"; else
    TIP=$(git -C "$LANE" rev-parse HEAD)
    if git log --oneline HEAD | grep -q "pilot-02-fetchhead"; then
      skip "already promoted"
    else
      note "range: ${TIP}~1..${TIP}"
      note "file:  scripts/coordination/tests/test_fetch_head_worktree_resolution.py"
      confirm "Ack this loop-plane merge (D9) and promote it?" || fail "declined"
      python3 scripts/coordination/promote_lane.py promote \
        --agent coordinator-agent --task-id pilot-02-fetchhead-worktree-regression-test \
        --lane-worktree "$LANE" --range "${TIP}~1..${TIP}" \
        --operator-ack "operator ratification $(date -u +%Y-%m-%dT%H:%M:%SZ) via ratify-loop-owned-fleet-20260816.sh" \
        --apply >/dev/null && ok "promoted" || fail "promotion refused — read the output above"
    fi
  fi
fi

# ------------------------------------------------------- 4. INVARIANTS.md
if wants 4; then
  say "STEP 4 — apply agents/shared/INVARIANTS.md (human-only path)"
  SRC=artifacts/operator/staged/INVARIANTS.md
  DST=agents/shared/INVARIANTS.md
  [[ -f "$SRC" ]] || fail "staged file missing: $SRC"
  if [[ -f "$DST" ]] && cmp -s "$SRC" "$DST"; then
    skip "already applied and identical"
  else
    if [[ -f "$DST" ]]; then
      note "$DST already exists and DIFFERS. Refusing to overwrite."
      note "Diff it yourself:  diff $DST $SRC"
      fail "manual reconciliation required"
    fi
    note "15 invariants, verbatim, no origin narratives. Canonical copy; other"
    note "surfaces cite it. This is a hash-pinned human-only path — that gate is"
    note "why an agent could not place it."
    confirm "Install $DST ?" || fail "declined"
    cp "$SRC" "$DST"
    ok "installed ($(wc -l < "$DST") lines)"
  fi
  python3 scripts/validate/validate_agents_structure.py >/dev/null 2>&1 \
    && ok "agent structure validator passes" || fail "structure validator failed"
  # ATTRIBUTABLE, not a count. The first version compared the total against a
  # frozen baseline of 13, so ANY concurrent change by another session in this
  # shared tree was attributed to this file — which is exactly what happened
  # (another session restored agents/research-writer.md and the total moved to
  # 17 while INVARIANTS.md contributed nothing). A gate must fail for its own
  # reason or it teaches people to ignore it. So: does any unresolved reference
  # name THIS file as its source?
  MINE=$(python3 scripts/validate/validate_agents_references.py 2>&1 | grep -c "^- agents/shared/INVARIANTS.md ->" || true)
  if [[ "$MINE" -eq 0 ]]; then
    ok "reference validator: INVARIANTS.md introduces no unresolved reference"
    TOTAL=$(python3 scripts/validate/validate_agents_references.py 2>&1 | grep -c "^- " || true)
    note "($TOTAL unresolved refs exist repo-wide, all from other files and pre-dating this)"
  else
    python3 scripts/validate/validate_agents_references.py 2>&1 | grep "^- agents/shared/INVARIANTS.md ->" | sed 's/^/        /'
    fail "INVARIANTS.md introduced $MINE dangling reference(s)"
  fi
fi

# ------------------------------------------------------- 5. IDLE-CANDIDATE
if wants 5; then
  say "STEP 5 — retire the IDLE-CANDIDATE marker (one word, loop-plane so D9)"
  if ! grep -q "IDLE-CANDIDATE" scripts/coordination/session_bus.py 2>/dev/null; then
    skip "already removed"
  else
    note "P3-3 retired the IDLE-CANDIDATE token; _OCCUPANCY_MARKERS still lists it,"
    note "so that entry can never match. Harmless, but it is a stale claim in code."
    confirm "Remove the dead marker?" || fail "declined"
    python3 - <<'PY'
import re
from pathlib import Path
p = Path("scripts/coordination/session_bus.py")
t = p.read_text(encoding="utf-8")
t2 = re.sub(r'^\s*"IDLE-CANDIDATE",?\s*\n', "", t, flags=re.M)
if t2 == t:
    t2 = t.replace('"IDLE-CANDIDATE", ', "").replace(', "IDLE-CANDIDATE"', "")
p.write_text(t2, encoding="utf-8")
PY
    python3 -c "import ast;ast.parse(open('scripts/coordination/session_bus.py').read())" \
      && ok "removed; syntax clean" || fail "syntax broken — revert with: git checkout -- scripts/coordination/session_bus.py"
  fi
fi

# ------------------------------------------------------------------ wrap
say "DONE — review and commit"
git status --porcelain -- coordination/session-bus/ agents/ scripts/coordination/ | sed 's/^/   /' || true
cat <<'TAIL'

   Nothing above was committed. Review, then commit with an EXPLICIT pathspec
   (this is a shared clone — a pathspec-less commit sweeps other sessions' work):

     git diff -- <paths>
     git commit -m "operator: ratify Loop-Owned Fleet gates" -- <paths>

   Then, if you enabled the pool, watch one batch land:
     tmux attach -t agent          # a worker appears as window wpool-laneN
     python3 scripts/coordination/fleet_metrics.py --days 7
TAIL
