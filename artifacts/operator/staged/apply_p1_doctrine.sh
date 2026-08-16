#!/bin/bash
# apply_p1_doctrine.sh — Loop-Owned Fleet, Phase 1 (P1-2 / P1-3 / P1-4), human-only half.
#
#   ./apply_p1_doctrine.sh                      # DRY RUN — show the plan, change nothing
#   ./apply_p1_doctrine.sh --apply              # apply every item
#   ./apply_p1_doctrine.sh --apply --only CLAUDE_MD
#   ./apply_p1_doctrine.sh --verify             # re-run the post-apply gates only
#
# WHY THIS IS A SCRIPT AND NOT A COMMIT.
#   `agents/shared/*.md`, `CLAUDE.md` and `agents/AGENT_INSTRUCTIONS.md` are hash-pinned in
#   coordination/session-bus/human_only_paths.yaml, and scripts/hooks/check_trust_boundary_edit.sh
#   refuses agent Write/Edit on them (PreToolUse). That is INVARIANTS 4 and 10 working as designed
#   — containment, not an obstacle. So the new content is STAGED here and an operator applies it.
#   Nothing in this script uses sed/cp tricks to launder an agent edit past the hook: it copies
#   whole reviewed files, under your hand, after you have read them.
#
# SAFETY PROPERTIES
#   * DRY RUN IS THE DEFAULT. Nothing is written without --apply.
#   * EVERY TARGET IS SHA256-PINNED to the content it had when this package was built. If a target
#     drifted (another session edited it), that item ABORTS and the others still run.
#   * EVERY SOURCE IS SHA256-PINNED too, so a truncated or tampered staged file is caught.
#   * IDEMPOTENT. A target already byte-identical to its source reports SKIP.
#   * SELF-VERIFYING. After applying, it runs the structure validator, the reference validator
#     (asserting THESE files add no unresolved reference — the repo already has 13 pre-existing
#     cross-repo ones), an anchor resolver, and the RFC-2119 directive-count gate.
#   * NOTHING IS COMMITTED. Review `git diff`, then commit with an EXPLICIT pathspec.

set -euo pipefail

# P1_REPO exists so this script can be REHEARSED against a shadow copy of the tree before it is
# ever pointed at the real one. It defaults to the real repo; the rehearsal is how the package was
# proved runnable without an agent writing to a human-only path.
REPO="${P1_REPO:-/workspace}"
cd "$REPO"
STAGE=artifacts/operator/staged

APPLY=0
VERIFY_ONLY=0
ONLY=()

while [[ $# -gt 0 ]]; do
  case "$1" in
    --apply)  APPLY=1; shift ;;
    --verify) VERIFY_ONLY=1; shift ;;
    --only)   ONLY+=("$2"); shift 2 ;;
    -h|--help) sed -n '2,30p' "$0"; exit 0 ;;
    *) echo "unknown arg: $1" >&2; exit 64 ;;
  esac
done

say()  { printf '\n\033[1m== %s\033[0m\n' "$*"; }
ok()   { printf '   \033[32mOK\033[0m    %s\n' "$*"; }
skip() { printf '   \033[33mSKIP\033[0m  %s\n' "$*"; }
warn() { printf '   \033[33mWARN\033[0m  %s\n' "$*"; }
bad()  { printf '   \033[31mFAIL\033[0m  %s\n' "$*"; }
note() { printf '         %s\n' "$*"; }

FAILED=0

wants() {
  [[ ${#ONLY[@]} -eq 0 ]] && return 0
  local s; for s in "${ONLY[@]}"; do [[ "$s" == "$1" ]] && return 0; done
  return 1
}

sha() { sha256sum "$1" | awk '{print $1}'; }

# ------------------------------------------------------------------ the items
# name | staged source | destination | sha256(destination BEFORE) | sha256(source)
ITEMS=(
"OPERATING_CONSTRAINTS|$STAGE/OPERATING_CONSTRAINTS.md|agents/shared/OPERATING_CONSTRAINTS.md|0a3b37ec5d856d1b1af48cd1de3e3ead8b0f91cfaa176f4a07c154fd3a469ab5|8688e41006c87ecf6a40a392fbc0ab00ec19f97e90cacc07ed9c1dca3bc270a4"
"SESSION_LIFECYCLE|$STAGE/SESSION_LIFECYCLE.md|agents/shared/SESSION_LIFECYCLE.md|b148f64b16b958b746a8f331942ffaac9e1ba7abed18a23fb3b824936b18c38c|a667fb86073fdafb50b2b2ff152f403df5706514e4d9d79ff4814b06b79f4d1d"
"CLAUDE_MD|$STAGE/CLAUDE.md|CLAUDE.md|8275ecc2f147a3472da1e949227abede83a6c40af707a80cf6941066d16993bd|c5b1030ac71d71a41fc8073969950e6418965f12b44f5535b58c6ae439960a42"
"AGENT_INSTRUCTIONS|$STAGE/AGENT_INSTRUCTIONS.md|agents/AGENT_INSTRUCTIONS.md|550a484de6ce4adb26c426b1ba5f8653bde79ed2b28a7f8eafbbd6b6a448acc8|b38ab38e6c6a0d302710ec4dd24cd385952738ecd9faca187469d7619b9536ec"
)

# RFC-2119 directive-count gate. P1-4 moved incident STORIES to an appendix; the number of
# DIRECTIVES must never fall. Baselines measured on the pinned pre-apply content.
#   name | pre-apply total | required post-apply minimum
# CLAUDE_MD is the one legitimate DECREASE: P1-2 replaced restatements with citations, so its
# count moves 40 -> 46 here only because the rulings were added; the two keywords it does lose
# ("this SHOULD ALWAYS be the case") survive verbatim in the canonical fan-out section.
DIRECTIVES=(
"OPERATING_CONSTRAINTS|agents/shared/OPERATING_CONSTRAINTS.md|41|60"
"SESSION_LIFECYCLE|agents/shared/SESSION_LIFECYCLE.md|13|26"
"CLAUDE_MD|CLAUDE.md|40|46"
"AGENT_INSTRUCTIONS|agents/AGENT_INSTRUCTIONS.md|10|12"
)

# --------------------------------------------------------------------- plan
if [[ $APPLY -eq 0 && $VERIFY_ONLY -eq 0 ]]; then
cat <<'PLAN'
LOOP-OWNED FLEET — Phase 1 doctrine collapse, human-only half (P1-2 / P1-3 / P1-4)

  OPERATING_CONSTRAINTS   agents/shared/OPERATING_CONSTRAINTS.md      269 -> 366 lines
      P1-2  Canonical home for fan-out, dispatch-by-task-text, observation windows and reload
            ownership. Five merges pulled IN from copies that were about to be deleted (see the
            companion notes): the coordinator's "tightest instance, never an exemption" clause,
            INC-20260728-idle-mains as fan-out's second origin, the AUD-2 typed-row enforcement,
            the "or approve" extension of the reload prohibition, and the invariant-13 vs
            name-your-count reconciliation for absence claims.
      P1-3  NEW section "Doctrine rulings — 2026-08-16" — the canonical home the handoff names.
      P1-4  Five incident narratives moved OUT of the instruction path into an appendix; each
            rule keeps a one-line (origin: …) pointer. Directives 41 -> 60, none lost.

  SESSION_LIFECYCLE       agents/shared/SESSION_LIFECYCLE.md          113 -> 174 lines
      P1-3a The "major checkpoints, not every task" cadence is RETIRED. New "## Wrap-up cadence"
            section states the binding per-task rule — and fixes the DANGLING citation in
            agents/commands/wrap-up.md, which already points at a heading that did not exist.
      P1-3b Subagent PREPARES index edits, owning session APPLIES.
      P1-2  Four merges into the checkbox axiom (the never-tick scope, the "you may say a box is
            stale" carve-out, the frozen-handoff exception, the blocked/partial checkpoint
            states) and two into the liveness rule. Fixes a second broken pointer:
            MEASUREMENT_POLICY.md -> *Observation windows*, a section that does not exist.
      P1-4  Incident narratives moved to an appendix. Directives 13 -> 26, none lost.

  CLAUDE_MD               CLAUDE.md                                   227 -> 226 lines
      P1-2  Five full restatements become citations: checkbox, dispatch-by-task-text,
            observation windows, fan-out, three-state liveness. The fan-out citation now SIGNALS
            the "When NOT to fan out" exceptions, which existed in 1 of 7 copies.
      P1-3b The blanket sub-agent prohibition is reworded to the ruling: PREPARE vs APPLY.
      NEW   Pointers to agents/shared/INVARIANTS.md and to the doctrine rulings.
            The API-reload MECHANICS (orchestrator_stack.py, autopilot handling) are the SOLE
            copy in the corpus and are deliberately left untouched.

  AGENT_INSTRUCTIONS      agents/AGENT_INSTRUCTIONS.md                 94 -> 102 lines
      P1-2  Fan-out restatement becomes a citation that names the exceptions; INVARIANTS.md added
            to the read order (it was reachable from no auto-loaded surface); an Observation
            Windows pointer added (the file deep-linked three other rules but not that one).

Run:  ./apply_p1_doctrine.sh --apply          (or --apply --only <NAME>)
Then: git diff -- CLAUDE.md agents/   and commit with an EXPLICIT pathspec.

Already landed and NOT redone here: commit b5ae002d (BUS_PROTOCOL.md, agents/commands/wrap-up.md,
docs/guides/agent-workflows/*, the coordinator SKILL.md). agents/shared/INVARIANTS.md is already
applied; this package CITES it and never rewrites it.
Applied outside this script (unprotected paths, already in the working tree):
agents/coordinator-agent.md (P1-6, rewritten), agents/auditor-main.md, agents/inference-main.md,
.claude/skills/coordinator-agent/SKILL.md.
PLAN
exit 0
fi

# ------------------------------------------------------------------- apply
if [[ $VERIFY_ONLY -eq 0 ]]; then
for row in "${ITEMS[@]}"; do
  IFS='|' read -r NAME SRC DST WANT_DST WANT_SRC <<<"$row"
  wants "$NAME" || continue
  say "$NAME  ->  $DST"

  if [[ ! -f "$SRC" ]]; then bad "staged source missing: $SRC"; FAILED=1; continue; fi
  GOT_SRC=$(sha "$SRC")
  if [[ "$GOT_SRC" != "$WANT_SRC" ]]; then
    bad "staged source has changed since this package was built"
    note "expected $WANT_SRC"
    note "found    $GOT_SRC"
    note "Refusing to install unreviewed content. Re-review $SRC, then update the pin."
    FAILED=1; continue
  fi
  ok "source pin matches"

  if [[ ! -f "$DST" ]]; then bad "destination missing: $DST"; FAILED=1; continue; fi
  GOT_DST=$(sha "$DST")
  if [[ "$GOT_DST" == "$WANT_SRC" ]]; then skip "already applied (byte-identical)"; continue; fi
  if [[ "$GOT_DST" != "$WANT_DST" ]]; then
    bad "TARGET DRIFTED — another session edited $DST after this package was built"
    note "expected $WANT_DST"
    note "found    $GOT_DST"
    note "Aborting THIS item only; the others are unaffected. Reconcile with:"
    note "    diff $DST $SRC"
    FAILED=1; continue
  fi
  ok "target pin matches (no drift)"

  cp "$SRC" "$DST"
  ok "installed ($(wc -l < "$DST") lines)"
done
fi

# ------------------------------------------------------------------ verify
say "VERIFY 1 — agent structure validator"
if python3 scripts/validate/validate_agents_structure.py; then ok "passes"; else bad "structure validator FAILED"; FAILED=1; fi

say "VERIFY 2 — agent reference validator (attributable, not a total)"
# The repo is ALREADY red with 13 pre-existing unresolved cross-repo refs. A frozen total would
# fail for another session's reason, which teaches people to ignore the gate. So: does any
# unresolved reference name one of THESE files as its source?
REFOUT=$(python3 scripts/validate/validate_agents_references.py 2>&1 || true)
MINE=$(printf '%s\n' "$REFOUT" | grep -cE '^- (CLAUDE\.md|agents/AGENT_INSTRUCTIONS\.md|agents/shared/(OPERATING_CONSTRAINTS|SESSION_LIFECYCLE|INVARIANTS)\.md|agents/coordinator-agent\.md) ->' || true)
TOTAL=$(printf '%s\n' "$REFOUT" | grep -c '^- ' || true)
if [[ "$MINE" -eq 0 ]]; then
  ok "these files introduce 0 unresolved references"
  note "($TOTAL unresolved refs exist repo-wide, all from other files, all pre-dating this package)"
else
  printf '%s\n' "$REFOUT" | grep -E '^- (CLAUDE\.md|agents/AGENT_INSTRUCTIONS\.md|agents/shared/|agents/coordinator-agent\.md)' | sed 's/^/         /'
  bad "$MINE dangling reference(s) attributable to this package"
  FAILED=1
fi

say "VERIFY 3 — inbound anchors still resolve"
# Deleting or renaming a heading silently breaks every deep link into it. These are the anchors
# other files point AT inside the files this package rewrote.
python3 - <<'PY' || FAILED=1
import os, re, sys, pathlib
ROOT = pathlib.Path(os.environ.get("P1_REPO", "/workspace"))
REQUIRED = [
    ("agents/shared/OPERATING_CONSTRAINTS.md", "act-dont-defer--the-admission-test-for-escalating-at-all"),
    ("agents/shared/OPERATING_CONSTRAINTS.md", "operator-decision-requests"),
    ("agents/shared/OPERATING_CONSTRAINTS.md", "parallel-subagent-fan-out--the-default-working-mode-of-every-main"),
    ("agents/shared/OPERATING_CONSTRAINTS.md", "dispatching-backlog-work--the-task-text-is-the-identity"),
    ("agents/shared/OPERATING_CONSTRAINTS.md", "observation-windows--a-sample-that-misses-the-phenomenon-proves-nothing"),
    ("agents/shared/OPERATING_CONSTRAINTS.md", "inference-and-benchmarks"),
    ("agents/shared/SESSION_LIFECYCLE.md", "reading-another-sessions-liveness--three-states-not-two"),
]
# Prose (non-anchor) citations that four other files depend on, by heading TEXT.
REQUIRED_HEADINGS = [
    ("agents/shared/SESSION_LIFECYCLE.md", "## Wrap-up cadence"),
    ("agents/shared/SESSION_LIFECYCLE.md", "## Pre-reboot wrap-up is mandatory, not checkpoint-gated"),
    ("agents/shared/OPERATING_CONSTRAINTS.md", "## Doctrine rulings — 2026-08-16"),
]
def slug(h):
    s = re.sub(r"[*`_]", "", h.strip().lower())
    s = re.sub(r"[^a-z0-9 -]", "", s)
    return s.replace(" ", "-")
bad = []
for rel, anchor in REQUIRED:
    text = (ROOT / rel).read_text(encoding="utf-8")
    slugs = {slug(h) for h in re.findall(r"^#{1,6}\s+(.*)$", text, re.M)}
    if anchor not in slugs:
        bad.append(f"{rel}#{anchor} — ANCHOR GONE, deep links into it are now dead")
for rel, heading in REQUIRED_HEADINGS:
    if heading not in (ROOT / rel).read_text(encoding="utf-8"):
        bad.append(f"{rel} — required heading missing: {heading}")
if bad:
    print("   FAIL  " + "\n   FAIL  ".join(bad)); sys.exit(1)
print(f"   OK    all {len(REQUIRED)} deep-link anchors and {len(REQUIRED_HEADINGS)} cited headings present")
PY

say "VERIFY 4 — RFC-2119 directive count (P1-4 proof: stories moved, directives kept)"
for row in "${DIRECTIVES[@]}"; do
  IFS='|' read -r NAME PATHV BEFORE MIN <<<"$row"
  NOW=$(python3 "$STAGE/rfc2119_count.py" "$PATHV" | awk '/TOTAL=/{sub(/.*TOTAL=/,"");sub(/ .*/,"");print}')
  if [[ "$NOW" -ge "$MIN" ]]; then
    ok "$NAME: $BEFORE -> $NOW directives (floor $MIN)"
  else
    bad "$NAME: $BEFORE -> $NOW directives, below the floor of $MIN — a directive was LOST"
    FAILED=1
  fi
done

say "VERIFY 5 — no restatement crept back in"
python3 - <<'PY' || true
import os, pathlib, re
ROOT = pathlib.Path(os.environ.get("P1_REPO", "/workspace"))
# Each phrase is the load-bearing sentence of a rule whose canonical home is named. Finding it
# anywhere else means a citation turned back into a copy.
# Each phrase is from the rule's BODY, never its heading — a heading string also appears in
# every legitimate citation, which would make this gate fire on correct work (observed during
# the rehearsal, before this package shipped).
CHECKS = [
    ("3–5 subagents run CONCURRENTLY", "agents/shared/OPERATING_CONSTRAINTS.md"),
    ("more tokens on coordination than on work", "agents/shared/OPERATING_CONSTRAINTS.md"),
    ("Anchor rot is structural", "agents/shared/OPERATING_CONSTRAINTS.md"),
    ("An absence claim needs PERSISTENCE", "agents/shared/OPERATING_CONSTRAINTS.md"),
    ("Heartbeats lie, and it is the READER who pays", "agents/shared/SESSION_LIFECYCLE.md"),
    ("446 seconds stale", "agents/shared/SESSION_LIFECYCLE.md"),
    ("four of eight", "agents/shared/OPERATING_CONSTRAINTS.md"),
]
files = [ROOT/"CLAUDE.md"] + sorted((ROOT/"agents").glob("*.md")) + sorted((ROOT/"agents/shared").glob("*.md"))
issues = []
for phrase, home in CHECKS:
    holders = [str(f.relative_to(ROOT)) for f in files
               if phrase in f.read_text(encoding="utf-8")]
    extra = [h for h in holders if h != home]
    if home not in holders:
        issues.append(f"canonical copy MISSING: '{phrase}' not in {home}")
    if extra:
        issues.append(f"restated outside its home: '{phrase}' also in {', '.join(extra)}")
if issues:
    print("   WARN  " + "\n   WARN  ".join(issues))
else:
    print("   OK    each headline rule has exactly one full copy, in its canonical home")
PY

# -------------------------------------------------------------------- wrap
say "RESULT"
if [[ $FAILED -ne 0 ]]; then
  bad "one or more items or gates failed — read the output above before committing"
  exit 1
fi
ok "all items applied or skipped, all gates green"
git status --porcelain -- CLAUDE.md agents/ | sed 's/^/   /' || true
cat <<'TAIL'

   NOTHING WAS COMMITTED. This is a shared clone — a pathspec-less commit sweeps other
   sessions' work. Review, then commit with an explicit pathspec:

     git diff -- CLAUDE.md agents/
     git commit -m "P1-2/P1-3/P1-4/P1-6: doctrine dedup, rulings, narrative appendices" -- \
       CLAUDE.md agents/AGENT_INSTRUCTIONS.md agents/shared/OPERATING_CONSTRAINTS.md \
       agents/shared/SESSION_LIFECYCLE.md agents/coordinator-agent.md agents/auditor-main.md \
       agents/inference-main.md .claude/skills/coordinator-agent/SKILL.md

   Then tick P1-2, P1-3, P1-4 and P1-6 in handoffs/active/loop-owned-fleet-implementation.md.
TAIL
