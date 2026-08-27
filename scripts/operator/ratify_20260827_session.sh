#!/bin/bash
# Ratify the 2026-08-27 AutoKernel session's doctrine amendments, and optionally
# close OP-28 (the wiki compile watermark).
#
# ONE command. Everything this session accumulated that needs your signature is
# in here; nothing else is pending.
#
# ---------------------------------------------------------------------------
# WHY THIS IS A SCRIPT YOU RUN AND NOT A COMMIT I MADE
# ---------------------------------------------------------------------------
# `agents/shared/*.md` is a human-only write path
# (coordination/session-bus/human_only_paths.yaml: "shared policy loaded by every
# role overlay"), enforced by scripts/hooks/check_trust_boundary_edit.sh. An agent
# that could edit its own operating constraints could widen its own authority, so
# the amendment is PREPARED here and applied under your signature.
#
# ---------------------------------------------------------------------------
# WHY IT WORKS IN A WORKTREE AND NOT IN /workspace
# ---------------------------------------------------------------------------
# The shared clone cannot fast-forward: a peer's uncommitted
# wiki/knowledge-management.md is also changed upstream, so git refuses (correctly,
# and atomically). /workspace therefore sits behind origin/main and cannot push. This
# script does all its work in a throwaway worktree checked out at origin/main, prints
# the diff for you to read, and publishes through the serialized push lock. /workspace
# is never touched and picks the change up whenever it can fast-forward.
#
# ---------------------------------------------------------------------------
# WHAT IT AMENDS  (agents/shared/OPERATING_CONSTRAINTS.md)
# ---------------------------------------------------------------------------
# Three hazards, all MEASURED on 2026-08-27 during the AutoKernel v28-v31 work, each
# of which produced a confident wrong answer that survived until it was re-verified.
#
# Into "Observation Windows" (which today covers windows that miss in TIME):
#
#   1. THE STATE FILE IS NOT THE PHENOMENON. A monitor watched only iteration-
#      completion fields in a controller state file. State moves at phase BOUNDARIES,
#      and a single-threaded HIP build sits between them for 15+ minutes, so it
#      reported "no progress" through a perfectly healthy build. Liveness of a long
#      phase must come from ARTIFACT ACTIVITY plus a live child process.
#
#   2. A TRUNCATED PROBE REPORTS THE ABSENCE OF WHAT IT NEVER LOOKED AT.
#      `ps -eo ... | grep ... | head` dropped the supervisor, factory and compiler
#      (they sorted below the cut) and produced a confident "the campaign is DOWN"
#      while all three were alive. Same family: a mutation test run against a tree
#      that did not contain the line being mutated passed VACUOUSLY, because the
#      injection was a no-op.
#
# Into "Retry Policy":
#
#   3. A TERMINAL RAISE ON A RESUME PATH BECOMES AN INFINITE LOOP THE MOMENT
#      RESTARTS ARE ENABLED. AutoKernel's supervisor was clamped to max_restarts==0,
#      so every crash was a permanent exit. Lifting that clamp was correct and proved
#      the resume path worked (scientific_attempts survived a crash) — but it also
#      converted an unreconcilable-inflight raise from "die once" into a 30s restart
#      loop heading for the 1000-restart cap. Enabling restarts and demoting terminal
#      raises on the resume path are ONE change, not two.
#
# ---------------------------------------------------------------------------
# OPTIONAL — OP-28 (master-handoff-index.md)
# ---------------------------------------------------------------------------
# `wiki/.last_compile` has NEVER existed, so compile_sources.py reports
# `total_new: 898` at every operator wrap-up while the wiki is in fact maintained by
# hand (32 pages, 27,440 lines). Passing --wiki-watermark=initialize takes option (a):
# declare pre-2026-08-27 sources compiled-by-hand and stamp the watermark now.
# WITHOUT the flag the wiki is not touched and OP-28 stays open. Never `--touch`
# casually: it asserts 898 uncompiled sources were compiled, which is the silent loss
# the wrap-up routine warns about — that is exactly why it is your decision.
#
# NOT IN SCOPE: OP-19 (E8 chain retirement / reseed-gate restatement). That needs your
# ruling, not a script.
#
# ---------------------------------------------------------------------------
# Usage
# ---------------------------------------------------------------------------
#   bash scripts/operator/ratify_20260827_session.sh --dry-run
#   bash scripts/operator/ratify_20260827_session.sh
#   bash scripts/operator/ratify_20260827_session.sh --wiki-watermark=initialize
#
# Idempotent: a second run detects the bullets are present and exits 0. All or
# nothing: preflight refuses the whole bundle on any anchor mismatch, and nothing is
# published unless every postflight check passes. Takes no compute, touches no kernel
# tree, starts no process.
set -euo pipefail

ROOT="${ROOT:-/workspace}"
AGENT="${AGENT:-operator}"
WORK="/mnt/raid0/llm/tmp/ratify-20260827-apply"
BRANCH="ratify/session-20260827"
SENTINEL="The state file is not the phenomenon"
RETRY_SENTINEL="becomes an infinite loop the moment restarts are enabled"

DRY_RUN=0; WIKI_MARK=""
for arg in "$@"; do
  case "$arg" in
    --dry-run) DRY_RUN=1 ;;
    --wiki-watermark=initialize) WIKI_MARK="initialize" ;;
    --wiki-watermark=*) echo "only --wiki-watermark=initialize is supported" >&2; exit 64 ;;
    *) echo "unknown argument: $arg" >&2; exit 64 ;;
  esac
done

say() { printf '%s\n' "$*"; }
die() { printf 'REFUSING: %s\n' "$*" >&2; exit 65; }

[ -d "$ROOT/.git" ] || die "not a git repository: $ROOT"
command -v git >/dev/null || die "git not found"

say "=== fetching origin"
git -C "$ROOT" fetch origin --quiet || die "fetch failed"

# ------------------------------------------------------------------ worktree
rm -rf "$WORK"
git -C "$ROOT" worktree add --detach "$WORK" origin/main >/dev/null 2>&1 \
  || die "could not create the apply worktree at $WORK"
cleanup() { git -C "$ROOT" worktree remove "$WORK" --force >/dev/null 2>&1 || true; }
trap cleanup EXIT

git -C "$WORK" checkout -q -B "$BRANCH" || die "could not create $BRANCH"
git -C "$WORK" branch --set-upstream-to=origin/main "$BRANCH" >/dev/null 2>&1 \
  || die "could not track origin/main"

OC="$WORK/agents/shared/OPERATING_CONSTRAINTS.md"
[ -f "$OC" ] || die "OPERATING_CONSTRAINTS.md missing in the worktree"

# ------------------------------------------------------------------ preflight
grep -q '^## Observation Windows' "$OC" || die "the 'Observation Windows' section moved"
grep -q '^## Retry Policy' "$OC" || die "the 'Retry Policy' section moved"
grep -q 'origin: INC-20260812-post-exit-vram-sample' "$OC" \
  || die "the Observation Windows origin line moved; re-derive the anchor"

ALREADY=0
if grep -qF "$SENTINEL" "$OC" && grep -qF "$RETRY_SENTINEL" "$OC"; then ALREADY=1; fi
if [ "$ALREADY" -eq 1 ]; then
  say "ALREADY RATIFIED: all three bullets are present on origin/main"
  [ -n "$WIKI_MARK" ] || exit 0
fi

if [ -n "$WIKI_MARK" ] && [ -f "$WORK/wiki/.last_compile" ]; then
  say "NOTE: wiki/.last_compile already exists — OP-28 already resolved; skipping the wiki step"
  WIKI_MARK=""
fi

say "PREFLIGHT OK"
say "  amend     : agents/shared/OPERATING_CONSTRAINTS.md (2 bullets in Observation Windows, 1 in Retry Policy)"
say "  worktree  : $WORK  (branch $BRANCH -> origin/main)"
say "  wiki step : ${WIKI_MARK:-<none — OP-28 stays open>}"
if [ "$DRY_RUN" -eq 1 ]; then say ""; say "DRY RUN — nothing written, nothing pushed."; exit 0; fi

# ------------------------------------------------------------------ apply
if [ "$ALREADY" -eq 0 ]; then
python3 - "$OC" <<'PY'
import sys
path = sys.argv[1]
s = open(path, encoding="utf-8").read()

obs_anchor = "(origin: INC-20260812-post-exit-vram-sample; Appendix)"
if obs_anchor not in s:
    sys.exit("Observation Windows anchor vanished between preflight and apply")

obs = (
"- **The state file is not the phenomenon.** For a phase that runs for minutes, a controller's\n"
"  state file only moves at phase BOUNDARIES — so \"state unchanged\" is the normal reading in the\n"
"  middle of one, and is indistinguishable from a wedge. Prove liveness from ARTIFACT ACTIVITY (new\n"
"  writes under the build/output tree) plus a live child process, and only then read the state file\n"
"  for *what phase* it is in. A monitor built the other way round reported \"no progress\" through a\n"
"  perfectly healthy 15-minute single-threaded HIP build.\n"
"- **A truncated probe reports the absence of what it never looked at.** `| head`, `| cut`, `--limit`\n"
"  and friends applied to a probe's OUTPUT silently shrink its window: `ps -eo … | grep … | head`\n"
"  dropped the supervisor, factory and compiler (they sorted below the cut) and produced a confident\n"
"  \"the campaign is DOWN\" while all three were alive. Count first and truncate second — or do not\n"
"  truncate a probe whose result is an absence claim. The same shape defeats a MUTATION TEST: an\n"
"  injection made against a tree that does not contain the line being mutated is a no-op, so the\n"
"  test passes vacuously and certifies nothing. Assert the mutation landed before trusting that it\n"
"  fired.\n"
)
s = s.replace(obs_anchor,
              obs + "\n(origin: INC-20260812-post-exit-vram-sample; and the 2026-08-27 AutoKernel\n"
                    "v28–v31 work, which produced all three false readings above within one\n"
                    "investigation; Appendix)", 1)

retry_anchor = "- After 3 failures, stop retrying and perform root-cause analysis.\n"
if retry_anchor not in s:
    sys.exit("Retry Policy anchor vanished between preflight and apply")

retry = (
"- **A terminal raise on a RESUME path becomes an infinite loop the moment restarts are enabled.**\n"
"  These are one change, not two. AutoKernel's supervisor was clamped to `max_restarts == 0`, so\n"
"  every crash was a permanent exit and the operator was the restart loop. Lifting the clamp was\n"
"  correct — the resume path worked, and a crashed campaign kept its accumulated state — but it also\n"
"  turned an unreconcilable-in-flight raise from \"die once\" into a 30-second restart loop heading\n"
"  for the 1000-restart cap. Before enabling restarts, every raise reachable on the resume path must\n"
"  be demoted to a recorded, advancing disposition: losing one attempt is correct, looping forever\n"
"  is not.\n"
)
s = s.replace(retry_anchor, retry_anchor + retry, 1)
open(path, "w", encoding="utf-8").write(s)
PY
fi

# ---------------------------------------------------------------- postflight
grep -qF "$SENTINEL" "$OC" || die "postflight: observation bullet missing after apply"
grep -q 'A truncated probe reports the absence' "$OC" || die "postflight: truncation bullet missing"
grep -qF "$RETRY_SENTINEL" "$OC" || die "postflight: retry bullet missing"
grep -q '2026-08-27 AutoKernel' "$OC" || die "postflight: origin line not updated"
say "APPLIED: 3 bullets + origin line"

WIKI_RESULT="not-requested"
if [ -n "$WIKI_MARK" ]; then
  VENVPY="${VENVPY:-$ROOT/repos/epyc-orchestrator/.venv/bin/python}"
  CS="$WORK/.claude/skills/project-wiki/scripts/compile_sources.py"
  [ -x "$VENVPY" ] || die "python not found at $VENVPY (set VENVPY=)"
  [ -f "$CS" ] || die "compile_sources.py missing in the worktree"
  ( cd "$WORK" && "$VENVPY" "$CS" --touch >/dev/null 2>&1 ) || die "compile_sources.py --touch failed"
  [ -f "$WORK/wiki/.last_compile" ] || die "wiki/.last_compile absent after --touch"
  WIKI_RESULT="initialized"
  say "APPLIED: wiki watermark initialised (OP-28 option (a))"
fi

# ------------------------------------------------------------------ receipt
RECEIPT="$WORK/artifacts/operator/ratify_20260827_session.json"
mkdir -p "$(dirname "$RECEIPT")"
cat > "$RECEIPT" <<JSON
{
  "schema": "epyc.operator.ratification.v1",
  "id": "ratify_20260827_session",
  "ratified_at": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
  "amends": [
    "agents/shared/OPERATING_CONSTRAINTS.md#observation-windows",
    "agents/shared/OPERATING_CONSTRAINTS.md#retry-policy"
  ],
  "adds": [
    "state-file-is-not-the-phenomenon (liveness by artifact activity)",
    "truncated-probe-and-vacuous-mutation (head/cut/limit on probe output)",
    "terminal-raise-on-resume-becomes-a-loop-once-restarts-are-enabled"
  ],
  "evidence": "2026-08-27 AutoKernel v28-v31; each hazard produced a confident false reading in one investigation",
  "wiki_watermark": "$WIKI_RESULT",
  "op28": "$( [ -n "$WIKI_MARK" ] && echo resolved-option-a || echo left-open )",
  "op19": "left-open — needs a ruling, not a script",
  "promotion_claim": false,
  "took_compute": false
}
JSON

# ------------------------------------------------------------------ review
say ""
say "=== DIFF FOR YOUR REVIEW ==="
git -C "$WORK" --no-pager diff -- agents/shared/OPERATING_CONSTRAINTS.md | sed -n '1,140p'
say "=== END DIFF ==="
say ""

# ------------------------------------------------------------------ publish
git -C "$WORK" add agents/shared/OPERATING_CONSTRAINTS.md \
                   artifacts/operator/ratify_20260827_session.json
[ -n "$WIKI_MARK" ] && git -C "$WORK" add wiki/.last_compile
git -C "$WORK" commit -q -m "ratify: 2026-08-27 measurement-instrument and restart-semantics hazards

Operator-signed amendment to agents/shared/OPERATING_CONSTRAINTS.md (human-only
path). Three hazards, each measured during the AutoKernel v28-v31 work and each
of which produced a confident false reading:

  - liveness of a long-running phase must come from artifact activity plus a
    live child, not a phase-boundary state file (a healthy 15-min HIP build read
    as 'no progress');
  - a probe truncated by head/cut/limit reports the absence of what it never
    looked at, and the same shape makes a mutation test pass vacuously;
  - a terminal raise on a resume path becomes an infinite loop the moment
    restarts are enabled, so demoting those raises and lifting a restart clamp
    are one change, not two.

Receipt: artifacts/operator/ratify_20260827_session.json" \
  || die "commit failed"

say "COMMITTED: $(git -C "$WORK" log --oneline -1)"
say "=== publishing under the serialized push lock"
python3 "$ROOT/scripts/coordination/serialized_push.py" \
  --agent "$AGENT" --repo "$WORK" --push \
  || die "push refused — nothing was published; origin/main is untouched"

say ""
say "DONE."
say "  origin/main now carries the amendment; /workspace picks it up when it can fast-forward."
say "  OP-19 remains open by design — it needs your ruling, not a script."
