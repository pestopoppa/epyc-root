#!/bin/bash
# Operator ratification — coordinator-seat refactor, 2026-08-12.
#
# Every item in artifacts/operator/RATIFICATION-PACKAGE-20260812.md that can be
# executed, in one script. Read that document for WHY each item exists, what it
# costs, and what happens if you skip it — this script is the HOW only.
#
# DRY RUN IS THE DEFAULT, per the house convention (serialized_push.py:6).
# Nothing is changed until you pass --apply.
#
#   ./artifacts/operator/ratify_20260812.sh                  # show what would happen
#   ./artifacts/operator/ratify_20260812.sh --apply          # do the safe items
#   ./artifacts/operator/ratify_20260812.sh --apply --all    # include the destructive ones
#   ./artifacts/operator/ratify_20260812.sh --apply --only gate,gitconfig
#
# ITEMS
#   gate       AUD-15  — add the auto-loaded instruction surfaces to the trust boundary
#   pgpu1      A2      — P-GPU-1 field 3 requires a verifier-produced linkage receipt
#   gitconfig  D1      — remove worktree.useRelativePaths from /etc/gitconfig (needs sudo)
#   orphans    E1      — delete the 5 neutralised backup checkouts        [destructive]
#   stash      E2      — drop the research repo's evidence stash          [destructive]
#   venv       D2      — remove the venv created into /workspace itself   [destructive]
#
# Destructive items are SKIPPED unless you pass --all or name them in --only.
# Every item is idempotent: re-running reports "already applied" rather than
# doing it twice or failing.

set -euo pipefail

REPO="${EPYC_ROOT:-/workspace}"
APPLY=0
ALL=0
ONLY=""
SAFE_ITEMS="gate pgpu1 gitconfig"
DESTRUCTIVE_ITEMS="orphans stash venv"
FAILED=()
DONE=()
SKIPPED=()

while [[ $# -gt 0 ]]; do
  case "$1" in
    --apply)  APPLY=1 ;;
    --all)    ALL=1 ;;
    --only)   ONLY="${2:-}"; shift ;;
    --only=*) ONLY="${1#*=}" ;;
    -h|--help) sed -n '2,30p' "$0" | sed 's/^# \{0,1\}//'; exit 0 ;;
    *) echo "unknown argument: $1 (try --help)" >&2; exit 2 ;;
  esac
  shift
done

cd "$REPO"

say()  { printf '\n\033[1m== %s\033[0m\n' "$*"; }
info() { printf '   %s\n' "$*"; }
ok()   { printf '   \033[32mOK\033[0m  %s\n' "$*"; }
skip() { printf '   \033[33m--\033[0m  %s\n' "$*"; }
bad()  { printf '   \033[31mFAIL\033[0m %s\n' "$*"; }
would(){ printf '   \033[36mwould\033[0m %s\n' "$*"; }

wanted() {
  local item="$1"
  if [[ -n "$ONLY" ]]; then
    [[ ",$ONLY," == *",$item,"* ]] && return 0 || return 1
  fi
  if [[ " $DESTRUCTIVE_ITEMS " == *" $item "* ]]; then
    [[ "$ALL" == "1" ]] && return 0 || return 1
  fi
  return 0
}

# ── gate — AUD-15 ────────────────────────────────────────────────────────────
item_gate() {
  say "gate (AUD-15) — trust-boundary entries for the auto-loaded instruction surfaces"
  local yaml="coordination/session-bus/human_only_paths.yaml"
  local pin="coordination/session-bus/human_only_paths.sha256"

  if grep -q "auto-loaded instruction surface" "$yaml" 2>/dev/null; then
    ok "already applied"; DONE+=("gate (no-op)"); return 0
  fi
  info "adds CLAUDE.md, agents/AGENT_INSTRUCTIONS.md, agents/shared/*.md to $yaml"
  info "then rewrites $pin so validate and the daemon audit agree"
  info "NOTE: this is a speed bump, not containment — the hook's layer 2 fails OPEN"
  info "      by design when the gate list cannot be parsed."
  if [[ "$APPLY" != "1" ]]; then would "edit $yaml + rewrite $pin + run validate"; return 0; fi

  cp -p "$yaml" "$yaml.bak-20260812"
  python3 - "$yaml" <<'PY'
import sys
p = sys.argv[1]
t = open(p).read()
anchor = '  - repo: epyc-root\n    glob: "measurement/protocols/*.md"'
if anchor not in t:
    sys.exit("anchor line not found — apply by hand, see the package doc")
new = '''  - repo: epyc-root
    glob: "CLAUDE.md"
    why: "auto-loaded instruction surface; a wrong premise here becomes every session's truth"
  - repo: epyc-root
    glob: "agents/AGENT_INSTRUCTIONS.md"
    why: "auto-loaded instruction surface; same amplifier as CLAUDE.md"
  - repo: epyc-root
    glob: "agents/shared/*.md"
    why: "shared policy loaded by every role overlay; generalises the MEASUREMENT_POLICY.md entry"
''' + anchor
open(p, "w").write(t.replace(anchor, new, 1))
PY
  sha256sum "$yaml" | awk '{print $1}' > "$pin"
  if python3 scripts/coordination/session_bus.py validate >/dev/null 2>&1; then
    ok "applied; pin rewritten; session_bus validate passes"
    DONE+=("gate")
  else
    bad "validate FAILED after the edit — restoring from $yaml.bak-20260812"
    mv "$yaml.bak-20260812" "$yaml"
    sha256sum "$yaml" | awk '{print $1}' > "$pin"
    FAILED+=("gate")
  fi
}

# ── pgpu1 — A2 ───────────────────────────────────────────────────────────────
item_pgpu1() {
  say "pgpu1 (A2) — P-GPU-1 field 3 requires a verifier-produced linkage receipt"
  local proto="measurement/protocols/gpu-cross-device.md"
  local marker="verifier-produced linkage receipt"

  if grep -q "$marker" "$proto" 2>/dev/null; then
    ok "already applied"; DONE+=("pgpu1 (no-op)"); return 0
  fi
  info "appends one clause to field 3: a recorded env STRING no longer satisfies it;"
  info "a receipt that inspected zero libraries is vacuous and does not satisfy it."
  info "Governs FUTURE claims only — do not re-grade the artifacts already"
  info "dispositioned in docs/reviews/gpu-linkage-retro-certification-20260812.md."
  if [[ "$APPLY" != "1" ]]; then would "append the clause to field 3 of $proto"; return 0; fi

  cp -p "$proto" "$proto.bak-20260812"
  python3 - "$proto" <<'PY'
import sys
p = sys.argv[1]
t = open(p).read()
anchor = "   reasoning/sampling flags, spec-dec mode."
if anchor not in t:
    sys.exit("field-3 anchor not found — apply by hand, see the package doc")
clause = anchor + (
    "\n   **The `LD_LIBRARY_PATH`/backend evidence is satisfied ONLY by a verifier-produced\n"
    "   linkage receipt captured against the running binary — verifier id and version, the\n"
    "   inspected library set with per-library resolved path and sha256, and the verdict —\n"
    "   never by a recorded environment string alone. A receipt that inspected no libraries\n"
    "   is vacuous and does not satisfy this field.** (Amended 2026-08-12: llama.cpp dlopens\n"
    "   `libggml-hip.so`, so a HIP-invoked run can execute wholly on CPU while `ldd` shows\n"
    "   nothing — INC-20260731, reproduced twice on 2026-08-12. Governs claims made after\n"
    "   this date; artifacts already dispositioned are not re-graded.)"
)
open(p, "w").write(t.replace(anchor, clause, 1))
PY
  ok "applied — review the diff and record it in the protocol's amendment log:"
  info "    git diff -- $proto"
  DONE+=("pgpu1")
}

# ── gitconfig — D1 ───────────────────────────────────────────────────────────
item_gitconfig() {
  say "gitconfig (D1) — remove worktree.useRelativePaths from /etc/gitconfig"
  local cur
  cur="$(git config --system --get worktree.useRelativePaths 2>/dev/null || true)"
  if [[ -z "$cur" ]]; then
    ok "already unset system-wide"; DONE+=("gitconfig (no-op)"); return 0
  fi
  info "currently: $cur — this is the system-level cause of the 2026-08-12 worktree"
  info "destruction. Repo-local false protects THIS repo only; every other clone on"
  info "the host is still exposed."
  if [[ "$APPLY" != "1" ]]; then would "sudo git config --system --unset worktree.useRelativePaths"; return 0; fi

  if sudo -n true 2>/dev/null || sudo true; then
    sudo git config --system --unset worktree.useRelativePaths
    if [[ -z "$(git config --system --get worktree.useRelativePaths 2>/dev/null || true)" ]]; then
      ok "unset"; DONE+=("gitconfig")
    else
      bad "still set after unset"; FAILED+=("gitconfig")
    fi
  else
    bad "sudo unavailable — run by hand: sudo git config --system --unset worktree.useRelativePaths"
    FAILED+=("gitconfig")
  fi
}

# ── orphans — E1 [destructive] ───────────────────────────────────────────────
item_orphans() {
  say "orphans (E1) — delete the 5 neutralised backup checkouts  [DESTRUCTIVE]"
  local dirs=(/mnt/raid0/llm/worktrees/mains/*.orphan-20260812T1035Z)
  if [[ ! -d "${dirs[0]:-/nonexistent}" ]]; then
    ok "already gone"; DONE+=("orphans (no-op)"); return 0
  fi
  info "these are git-inert already (their .git was renamed .git.disabled-20260812),"
  info "so nothing can write through them into a live lane. Deleting is optional."
  info "NEVER use 'git worktree prune' here — they are unregistered, and prune is"
  info "what caused the original destruction."
  local n; n="$(ls -d /mnt/raid0/llm/worktrees/mains/*.orphan-20260812T1035Z 2>/dev/null | wc -l)"
  if [[ "$APPLY" != "1" ]]; then would "rm -rf $n backup checkout(s)"; return 0; fi
  rm -rf /mnt/raid0/llm/worktrees/mains/*.orphan-20260812T1035Z
  ok "removed $n"; DONE+=("orphans")
}

# ── stash — E2 [destructive] ─────────────────────────────────────────────────
item_stash() {
  say "stash (E2) — drop the research repo's reconciliation evidence stash  [DESTRUCTIVE]"
  local r="$REPO/repos/epyc-inference-research"
  if ! git -C "$r" stash list 2>/dev/null | grep -q .; then
    ok "no stash present"; DONE+=("stash (no-op)"); return 0
  fi
  git -C "$r" stash list 2>/dev/null | sed 's/^/   /'
  info "6 superseded predecessor files, kept as evidence during the reconciliation."
  if [[ "$APPLY" != "1" ]]; then would "git -C repos/epyc-inference-research stash drop"; return 0; fi
  git -C "$r" stash drop
  ok "dropped"; DONE+=("stash")
}

# ── venv — D2 [destructive] ──────────────────────────────────────────────────
item_venv() {
  say "venv (D2) — remove the venv created into /workspace itself  [DESTRUCTIVE]"
  if [[ ! -f "$REPO/pyvenv.cfg" ]]; then
    ok "already gone"; DONE+=("venv (no-op)"); return 0
  fi
  info "$(grep -m1 '^command' "$REPO/pyvenv.cfg" 2>/dev/null || echo 'pyvenv.cfg present')"
  info "untracked AND un-ignored, so it is exposed to any 'git add -A' or 'git clean -x'."
  info "CHECK NOTHING IS USING IT FIRST — this script cannot know that."
  if [[ "$APPLY" != "1" ]]; then would "rm -rf $REPO/{bin,lib,lib64,pyvenv.cfg}"; return 0; fi
  rm -rf "$REPO/bin" "$REPO/lib" "$REPO/lib64" "$REPO/pyvenv.cfg"
  ok "removed"; DONE+=("venv")
}

# ── run ──────────────────────────────────────────────────────────────────────
printf '\033[1mRatification — 2026-08-12 coordinator-seat refactor\033[0m\n'
if [[ "$APPLY" == "1" ]]; then
  printf 'mode: \033[31mAPPLY\033[0m'
else
  printf 'mode: \033[36mDRY RUN\033[0m (pass --apply to execute)'
fi
[[ "$ALL" == "1" ]] && printf '   destructive items: \033[31mINCLUDED\033[0m'
[[ -n "$ONLY" ]] && printf '   only: %s' "$ONLY"
printf '\n'

for item in $SAFE_ITEMS $DESTRUCTIVE_ITEMS; do
  if wanted "$item"; then
    "item_$item" || { bad "$item raised an error"; FAILED+=("$item"); }
  else
    SKIPPED+=("$item")
  fi
done

say "summary"
[[ ${#DONE[@]}    -gt 0 ]] && info "done:    ${DONE[*]}"
[[ ${#SKIPPED[@]} -gt 0 ]] && info "skipped: ${SKIPPED[*]}  (--all, or --only <name>, to include)"
[[ ${#FAILED[@]}  -gt 0 ]] && bad  "failed:  ${FAILED[*]}"

cat <<'TAIL'

   Still needs a word from you — no script can decide these:
     * re-run the vision-cutover THROUGHPUT/VRAM numbers? (accuracy needs nothing)
     * model_registry.yaml:2478 attests architect_general baselines to an
       experimental-kernel "no gate" artifact, and it feeds q_scorer
     * Phase-7 §7 items 1-7: row edits, incl. four stale multimodal-pipeline rows
     * ~2 min of quiet host so mainC's scout cells become decision-grade
TAIL

[[ ${#FAILED[@]} -gt 0 ]] && exit 1
exit 0
