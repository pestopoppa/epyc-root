#!/bin/bash
# Ratify the 2026-08-27 AutoKernel session's doctrine amendments.
#
# ONE command. Everything from this session that needs your signature is here.
#
# ---------------------------------------------------------------------------
# WHY THIS IS A SCRIPT YOU RUN AND NOT A COMMIT I MADE
# ---------------------------------------------------------------------------
# `agents/shared/*.md` is a human-only write path
# (coordination/session-bus/human_only_paths.yaml: "shared policy loaded by every
# role overlay"), enforced by scripts/hooks/check_trust_boundary_edit.sh. An agent
# that could edit its own operating constraints could widen its own authority, so the
# amendment is PREPARED here and applied under your signature.
#
# ---------------------------------------------------------------------------
# WHY IT WORKS IN A WORKTREE AND NOT IN /workspace
# ---------------------------------------------------------------------------
# The shared clone cannot fast-forward: a peer's uncommitted
# wiki/knowledge-management.md is also changed upstream, so git refuses (correctly,
# and atomically). /workspace therefore sits behind origin/main and cannot push. This
# script does its work in a throwaway worktree checked out at origin/main and
# publishes through the serialized push lock. /workspace is never modified.
#
# CAVEAT THAT BIT THE PREVIOUS VERSION, recorded here because it is the same hazard
# this amendment ratifies: a worktree contains only TRACKED files. Anything gitignored
# (e.g. wiki/.last_compile) is ABSENT there, so a check run inside the worktree reports
# it missing even when it exists in the real clone. The earlier version tested for that
# file in the worktree, concluded it had never existed, and aborted mid-run. Do not add
# checks here for untracked or ignored state.
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
#      reported "no progress" through a perfectly healthy build.
#
#   2. A PROBE REPORTS THE ABSENCE OF WHAT IT NEVER LOOKED AT. `ps … | grep … | head`
#      dropped the processes being searched for and produced a confident "the campaign
#      is DOWN" while all of them were alive. Same family: a mutation test run against
#      a tree that did not contain the mutated line passed VACUOUSLY; and a probe run
#      inside a git worktree reported gitignored state as absent, because a worktree
#      only ever contains tracked files.
#
# Into "Retry Policy":
#
#   3. A TERMINAL RAISE ON A RESUME PATH BECOMES AN INFINITE LOOP THE MOMENT RESTARTS
#      ARE ENABLED. AutoKernel's supervisor was clamped to max_restarts==0, so every
#      crash was a permanent exit. Lifting that clamp was correct and proved the resume
#      path worked — but it also converted an unreconcilable-inflight raise from "die
#      once" into a 30s restart loop heading for the 1000-restart cap.
#
# NOT IN SCOPE:
#   * OP-19 (E8 chain retirement / reseed-gate restatement) — needs a ruling, not a script.
#   * OP-28 (wiki compile watermark) — WITHDRAWN. It was raised on a false reading:
#     wiki/.last_compile is gitignored and therefore invisible inside a worktree, so it
#     looked like it had never existed. It has existed since 2026-08-25T15:11:14Z and
#     the real backlog is ~56 sources, a normal incremental amount. Nothing to decide.
#
# ---------------------------------------------------------------------------
# Usage
# ---------------------------------------------------------------------------
#   bash scripts/operator/ratify_20260827_session.sh --dry-run   # full rehearsal
#   bash scripts/operator/ratify_20260827_session.sh             # publish
#
# --dry-run performs EVERY step including the commit, in the throwaway worktree, and
# stops immediately before the push. It is a real rehearsal, not a preflight: if it
# prints "would publish", the publishing run will work.
#
# Idempotent, all-or-nothing, takes no compute, touches no kernel tree.
set -euo pipefail

ROOT="${ROOT:-/workspace}"
AGENT="${AGENT:-operator}"
WORK="/mnt/raid0/llm/tmp/ratify-20260827-apply"
BRANCH="ratify/session-20260827"
SENTINEL="The state file is not the phenomenon"
RETRY_SENTINEL="becomes an infinite loop the moment restarts are enabled"

DRY_RUN=0
for arg in "$@"; do
  case "$arg" in
    --dry-run) DRY_RUN=1 ;;
    *) echo "unknown argument: $arg" >&2; exit 64 ;;
  esac
done

say() { printf '%s\n' "$*"; }
die() { printf 'REFUSING: %s\n' "$*" >&2; exit 65; }

[ -d "$ROOT/.git" ] || die "not a git repository: $ROOT"

say "=== fetching origin"
git -C "$ROOT" fetch origin --quiet || die "fetch failed"

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

grep -q '^## Observation Windows' "$OC" || die "the 'Observation Windows' section moved"
grep -q '^## Retry Policy' "$OC" || die "the 'Retry Policy' section moved"
grep -q 'origin: INC-20260812-post-exit-vram-sample' "$OC" \
  || die "the Observation Windows origin line moved; re-derive the anchor"

if grep -qF "$SENTINEL" "$OC" && grep -qF "$RETRY_SENTINEL" "$OC"; then
  say "ALREADY RATIFIED: all three bullets are present on origin/main"
  exit 0
fi

say "PREFLIGHT OK — amending agents/shared/OPERATING_CONSTRAINTS.md"

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
"- **A probe reports the absence of what it never looked at.** Three shapes, one failure. (a)\n"
"  TRUNCATION: `| head`, `| cut`, `--limit` on a probe's OUTPUT silently shrink its window —\n"
"  `ps -eo … | grep … | head` dropped the supervisor, factory and compiler and produced a confident\n"
"  \"the campaign is DOWN\" while all three were alive. (b) WRONG TREE: a git worktree contains only\n"
"  TRACKED files, so a probe run there reports gitignored or untracked state as missing even when it\n"
"  exists in the real clone — this produced a whole operator decision request against a watermark\n"
"  that had existed for two days. (c) VACUOUS MUTATION: a mutation test whose injection did not\n"
"  land (the tree lacked the line being mutated) passes while testing nothing. Count before you\n"
"  truncate, run the probe in the tree the claim is about, and assert the mutation landed before\n"
"  trusting that it fired.\n"
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

grep -qF "$SENTINEL" "$OC" || die "postflight: observation bullet missing after apply"
grep -q 'A probe reports the absence' "$OC" || die "postflight: probe bullet missing"
grep -qF "$RETRY_SENTINEL" "$OC" || die "postflight: retry bullet missing"
grep -q '2026-08-27 AutoKernel' "$OC" || die "postflight: origin line not updated"
say "APPLIED: 3 bullets + origin line"

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
    "state-file-is-not-the-phenomenon",
    "probe-reports-absence-it-never-looked-at (truncation / wrong tree / vacuous mutation)",
    "terminal-raise-on-resume-becomes-a-loop-once-restarts-are-enabled"
  ],
  "evidence": "2026-08-27 AutoKernel v28-v31; each hazard produced a confident false reading in one investigation",
  "op19": "left-open — needs a ruling, not a script",
  "op28": "withdrawn — raised on a worktree-invisible gitignored watermark that had existed since 2026-08-25",
  "promotion_claim": false,
  "took_compute": false
}
JSON

say ""
say "=== DIFF FOR YOUR REVIEW ==="
git -C "$WORK" --no-pager diff -- agents/shared/OPERATING_CONSTRAINTS.md
say "=== END DIFF ==="
say ""

git -C "$WORK" add agents/shared/OPERATING_CONSTRAINTS.md \
                   artifacts/operator/ratify_20260827_session.json
git -C "$WORK" commit -q -m "ratify: 2026-08-27 measurement-instrument and restart-semantics hazards

Operator-signed amendment to agents/shared/OPERATING_CONSTRAINTS.md (human-only
path). Three hazards, each measured during the AutoKernel v28-v31 work and each
of which produced a confident false reading:

  - liveness of a long-running phase must come from artifact activity plus a
    live child, not a phase-boundary state file (a healthy 15-min HIP build read
    as 'no progress');
  - a probe reports the absence of what it never looked at, in three shapes:
    output truncated by head/cut/limit, a probe run in a worktree that by
    construction lacks gitignored state, and a mutation test whose injection
    never landed;
  - a terminal raise on a resume path becomes an infinite loop the moment
    restarts are enabled, so demoting those raises and lifting a restart clamp
    are one change, not two.

Receipt: artifacts/operator/ratify_20260827_session.json" \
  || die "commit failed"

COMMIT="$(git -C "$WORK" log --oneline -1)"
say "COMMITTED IN WORKTREE: $COMMIT"

if [ "$DRY_RUN" -eq 1 ]; then
  say ""
  say "DRY RUN COMPLETE — every step ran except the push."
  say "  would publish: $COMMIT"
  say "  origin/main is untouched. Re-run without --dry-run to publish."
  exit 0
fi

say "=== publishing under the serialized push lock"
python3 "$ROOT/scripts/coordination/serialized_push.py" \
  --agent "$AGENT" --repo "$WORK" --push \
  || die "push refused — nothing was published; origin/main is untouched"

say ""
say "DONE. origin/main carries the amendment; /workspace picks it up when it can fast-forward."
say "  OP-19 remains open by design. OP-28 is withdrawn (see the receipt)."
