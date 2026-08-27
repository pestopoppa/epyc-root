#!/bin/bash
# Ratify: two measurement-INSTRUMENT hazards into the Observation Windows doctrine,
# and (optionally) resolve OP-28 by initialising the wiki compile watermark.
#
# WHY THIS IS A SCRIPT YOU RUN AND NOT A COMMIT I MADE
# ----------------------------------------------------
# `agents/shared/*.md` is a human-only write path (coordination/session-bus/human_only_paths.yaml:39,
# "shared policy loaded by every role overlay"), enforced by scripts/hooks/check_trust_boundary_edit.sh.
# An agent that could edit its own operating constraints could widen its own authority, so the
# amendment is prepared here and applied under your signature.
#
# WHAT IT AMENDS  (agents/shared/OPERATING_CONSTRAINTS.md, section "Observation Windows")
# The existing section covers windows that miss the phenomenon in TIME. Both hazards below were
# measured on 2026-08-27 during the AutoKernel v28 launch, and both produced a CONFIDENT FALSE
# READING that survived until it was re-verified:
#
#   1. SIGNAL CHOICE. A v28 monitor watched only iteration-completion fields in a controller state
#      file. State moves at phase boundaries; a single-threaded (`-j1`) HIP build sits between them
#      for 15+ minutes. The monitor reported "no progress" while the anchor arm was actively
#      compiling. Liveness of a long-running phase must be read from ARTIFACT ACTIVITY (build-tree
#      writes) plus a live child process — never from a phase-boundary state file.
#
#   2. OUTPUT TRUNCATION. `ps -eo ... | grep ... | head` truncated away the very processes being
#      looked for (they sorted below the cut), and the conclusion drawn was "the campaign is DOWN"
#      when supervisor, factory and compiler were all alive. A probe truncated by `head`/`cut`/
#      `--limit` reports the absence of what it never looked at. This is a NINTH member of the
#      "ways a check passes for the wrong reason" family already recorded in this repo.
#
# Both are appended as bullets to the existing section; no existing text is rewritten, and the
# section's origin line gains this incident alongside INC-20260812.
#
# OPTIONAL — OP-28 (master-handoff-index.md:50). `wiki/.last_compile` has NEVER existed, so
# `compile_sources.py` reports `total_new: 898` at every operator wrap-up while the wiki is in fact
# maintained by hand (32 pages, 27,440 lines). Passing --wiki-watermark=initialize takes option (a):
# declare pre-2026-08-27 sources compiled-by-hand and stamp the watermark now. WITHOUT the flag this
# script does not touch the wiki at all and OP-28 stays open. Never run `--touch` casually: it
# asserts 898 uncompiled sources were compiled, which is the silent loss the wrap-up routine warns
# about — that is exactly why this is your decision and not mine.
#
# NOT IN SCOPE. OP-19 (E8 chain retirement / reseed-gate restatement) is a substantive ruling with
# consequences across 8+ handoffs and INF-40's registry patch; it needs your words, not a script.
#
# ALL OR NOTHING. Preflight refuses the whole bundle on any mismatch; apply restores from backup if
# postflight fails. Nothing here starts a process, touches a kernel tree, or takes compute.
#
# Usage:
#   bash scripts/operator/ratify_observation_instrument_hazards_20260827.sh --dry-run
#   bash scripts/operator/ratify_observation_instrument_hazards_20260827.sh
#   bash scripts/operator/ratify_observation_instrument_hazards_20260827.sh --commit
#   bash scripts/operator/ratify_observation_instrument_hazards_20260827.sh --commit --wiki-watermark=initialize
#
# Idempotent: a second run detects the bullets are present and exits 0 without writing.
set -euo pipefail

ROOT="${ROOT:-/workspace}"
OC="$ROOT/agents/shared/OPERATING_CONSTRAINTS.md"
RECEIPT="$ROOT/artifacts/operator/ratify_observation_instrument_hazards_20260827.json"
COMPILE_SOURCES="$ROOT/.claude/skills/project-wiki/scripts/compile_sources.py"
VENVPY="${VENVPY:-$ROOT/repos/epyc-orchestrator/.venv/bin/python}"
RATIFIED_AT="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
SENTINEL="The state file is not the phenomenon"

DRY_RUN=0; DO_COMMIT=0; WIKI_MARK=""
for arg in "$@"; do
  case "$arg" in
    --dry-run) DRY_RUN=1 ;;
    --commit)  DO_COMMIT=1 ;;
    --wiki-watermark=initialize) WIKI_MARK="initialize" ;;
    --wiki-watermark=*) echo "only --wiki-watermark=initialize is supported" >&2; exit 64 ;;
    *) echo "unknown argument: $arg" >&2; exit 64 ;;
  esac
done

say() { printf '%s\n' "$*"; }
die() { printf 'REFUSING: %s\n' "$*" >&2; exit 65; }

# ------------------------------------------------------------------ preflight
[ -f "$OC" ] || die "OPERATING_CONSTRAINTS.md not found at $OC"
grep -q '^## Observation Windows' "$OC" \
  || die "the 'Observation Windows' section is not where this amendment expects it"
grep -q 'origin: INC-20260812-post-exit-vram-sample' "$OC" \
  || die "the Observation Windows origin line has moved; re-derive the anchor before applying"

if grep -qF "$SENTINEL" "$OC"; then
  say "ALREADY RATIFIED: the instrument-hazard bullets are present in $OC"
  [ -n "$WIKI_MARK" ] || exit 0
fi

if [ -n "$WIKI_MARK" ]; then
  [ -f "$COMPILE_SOURCES" ] || die "compile_sources.py not found at $COMPILE_SOURCES"
  [ -x "$VENVPY" ] || die "python not found at $VENVPY (set VENVPY=)"
  if [ -f "$ROOT/wiki/.last_compile" ]; then
    say "NOTE: wiki/.last_compile already exists — OP-28 appears already resolved; wiki step will be skipped"
    WIKI_MARK=""
  fi
fi

say "PREFLIGHT OK"
say "  amend      : $OC  (2 bullets + origin line, in 'Observation Windows')"
say "  receipt    : $RECEIPT"
say "  wiki step  : ${WIKI_MARK:-<none — OP-28 stays open>}"
if [ "$DRY_RUN" -eq 1 ]; then say ""; say "DRY RUN — nothing written."; exit 0; fi

# ------------------------------------------------------------------- apply
BACKUP="$(mktemp)"; cp "$OC" "$BACKUP"
restore() { cp "$BACKUP" "$OC"; say "postflight failed — $OC restored from backup"; }

if ! grep -qF "$SENTINEL" "$OC"; then
  python3 - "$OC" <<'PY'
import sys
p = sys.argv[1]
s = open(p, encoding="utf-8").read()
anchor = "(origin: INC-20260812-post-exit-vram-sample; Appendix)"
if anchor not in s:
    sys.exit("anchor line vanished between preflight and apply")

bullets = (
"- **The state file is not the phenomenon.** For a phase that runs for minutes, a controller's\n"
"  state file only moves at phase BOUNDARIES — so \"state unchanged\" is the normal reading in the\n"
"  middle of one, and is indistinguishable from a wedge. Prove liveness from ARTIFACT ACTIVITY (new\n"
"  writes under the build/output tree) plus a live child process, and only then read the state file\n"
"  for *what phase* it is in. A monitor built the other way round reported \"no progress\" through a\n"
"  perfectly healthy 15-minute `-j1` HIP build.\n"
"- **A truncated probe reports the absence of what it never looked at.** `| head`, `| cut`, `--limit`\n"
"  and friends applied to a probe's OUTPUT silently shrink its window: `ps -eo ... | grep ... | head`\n"
"  dropped the supervisor, factory and compiler (they sorted below the cut) and produced a confident\n"
"  \"the campaign is DOWN\" while all three were alive. Count first and truncate second — or do not\n"
"  truncate a probe whose result is an absence claim. Same family as the enumerated ways a check\n"
"  passes for the wrong reason: the input, not the assertion, is what was empty.\n"
)

s = s.replace(anchor,
              bullets + "\n(origin: INC-20260812-post-exit-vram-sample; and the 2026-08-27 AutoKernel\n"
                        "v28 launch, which produced both false readings above within one investigation;\n"
                        "Appendix)", 1)
open(p, "w", encoding="utf-8").write(s)
PY
fi

# ---------------------------------------------------------------- postflight
grep -qF "$SENTINEL" "$OC" || { restore; die "postflight: sentinel bullet not present after apply"; }
grep -q 'A truncated probe reports the absence' "$OC" || { restore; die "postflight: second bullet missing"; }
grep -q '2026-08-27 AutoKernel' "$OC" || { restore; die "postflight: origin line not updated"; }
say "APPLIED: 2 bullets + origin line in $OC"

WIKI_RESULT="not-requested"
if [ -n "$WIKI_MARK" ]; then
  "$VENVPY" "$COMPILE_SOURCES" --touch >/dev/null 2>&1 \
    || { restore; die "compile_sources.py --touch failed; OPERATING_CONSTRAINTS.md restored"; }
  [ -f "$ROOT/wiki/.last_compile" ] || { restore; die "wiki/.last_compile absent after --touch"; }
  WIKI_RESULT="initialized $(cat "$ROOT/wiki/.last_compile" 2>/dev/null | head -c 40)"
  say "APPLIED: wiki watermark initialised (OP-28 option (a)) — $WIKI_RESULT"
fi

mkdir -p "$(dirname "$RECEIPT")"
cat > "$RECEIPT" <<JSON
{
  "schema": "epyc.operator.ratification.v1",
  "id": "ratify_observation_instrument_hazards_20260827",
  "ratified_at": "$RATIFIED_AT",
  "amends": ["agents/shared/OPERATING_CONSTRAINTS.md#observation-windows"],
  "adds": [
    "state-file-is-not-the-phenomenon (liveness by artifact activity, not phase-boundary state)",
    "truncated-probe-reports-absence-it-never-looked-at (head/cut/limit on probe output)"
  ],
  "evidence": "2026-08-27 AutoKernel v28 launch; both hazards produced confident false readings in one investigation",
  "wiki_watermark": "$WIKI_RESULT",
  "op28": "$( [ -n "$WIKI_MARK" ] && echo resolved-option-a || echo left-open )",
  "promotion_claim": false,
  "took_compute": false
}
JSON
say "RECEIPT: $RECEIPT"
rm -f "$BACKUP"

if [ "$DO_COMMIT" -eq 1 ]; then
  cd "$ROOT"
  git add agents/shared/OPERATING_CONSTRAINTS.md "$RECEIPT"
  [ -n "$WIKI_MARK" ] && git add wiki/.last_compile 2>/dev/null || true
  git commit -m "ratify: observation-window instrument hazards (state-file liveness, truncated probes)

Operator-signed amendment to agents/shared/OPERATING_CONSTRAINTS.md (human-only
path). Adds two bullets to Observation Windows, both measured 2026-08-27 during
the AutoKernel v28 launch, where each produced a confident false reading:

  - liveness of a long-running phase must come from artifact activity plus a
    live child, not from a phase-boundary state file (a healthy 15-min -j1 HIP
    build read as 'no progress');
  - a probe truncated by head/cut/limit reports the absence of what it never
    looked at (a truncated ps produced 'the campaign is DOWN' while supervisor,
    factory and compiler were all alive).

Receipt: artifacts/operator/ratify_observation_instrument_hazards_20260827.json"
  say "COMMITTED."
  say "NOTE: /workspace cannot fast-forward while a peer's wiki/knowledge-management.md is dirty."
  say "      Publish with: python3 scripts/coordination/serialized_push.py --agent <you> --repo . --push"
fi

say ""
say "DONE. OP-19 is deliberately NOT in this bundle — it needs your ruling, not a script."
