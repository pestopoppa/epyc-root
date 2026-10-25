#!/bin/bash
# ratify_ws58_retention_lessons_20261025.sh — ONE operator signature over three human-only change sets:
#
#   A  ws58 calendar lessons (5 hunks): agents/shared/OPERATING_CONSTRAINTS.md (3), agents/shared/SESSION_LIFECYCLE.md,
#      CLAUDE.md                                 artifacts/operator/ws58-calendar-lessons-20261025.human-only.patch
#   B  D2/D7: MEASUREMENT.md §5 "Evidence retention and reclamation" (the clause §6 already points to) + CHANGELOG
#      entry, plus the item-5 row of the 2026-08-03 AK ratification ledger
#                                                artifacts/operator/ws58-retention-s5-20261025.human-only.patch
#   C  D4: OPERATING_CONSTRAINTS.md → Destructive operations (citation check, 7-day trash hold, item 5 sanctioned
#      reclaim path) + the PreToolUse registration of scripts/hooks/check_destructive_scratch.sh in .claude/settings.json
#                                                artifacts/operator/ws58-destructive-ops-hook-20261025.human-only.patch
#   D  the hook itself (4 NEW files: scripts/hooks/check_destructive_scratch.sh, destructive_scratch_scan.py and its
#      37-case test). Not human-only, but scripts/hooks/ is D9 loop plane (operator ack per commit), so it rides in
#      this signed commit with a D9-ack line instead of landing unsigned
#                                                artifacts/operator/ws58-destructive-scratch-hook-files-20261025.patch
#   Package: artifacts/operator/ratify-ws58-retention-lessons-20261025.md
#
#   Review / dry run (default; full trial apply + receipt in a throwaway worktree, pushes nothing, keeps nothing):
#     bash scripts/operator/ratify_ws58_retention_lessons_20261025.sh
#   Sign, commit and push to main (the OPERATOR runs this, from a terminal):
#     RATIFY_OPERATOR='<your name>' bash scripts/operator/ratify_ws58_retention_lessons_20261025.sh --apply --attest RATIFY-WS58-RETENTION-LESSONS-20261025
#   Same, but leave the signed commit unpushed in the stage worktree (prints its path):
#     ... --apply --attest RATIFY-WS58-RETENTION-LESSONS-20261025 --no-push
#   Verify origin/main (read-only):
#     bash scripts/operator/ratify_ws58_retention_lessons_20261025.sh --verify
#
# ratify-targets: MEASUREMENT.md agents/shared/OPERATING_CONSTRAINTS.md agents/shared/SESSION_LIFECYCLE.md CLAUDE.md .claude/settings.json
#
# OPERATOR DECISIONS (2026-10-25): calendar lessons (A) "encode the lessons in project files"; D2/D7 "ratify the
# amended retention §5"; D4 "prepare the doctrine change plus the PreToolUse hook for signature". A workspace-58
# subagent prepared this bundle; only the operator applies it. Origin and per-hunk table: the package md above and
# docs/reference/tmp-loss-reconcile-2026-10-25.md (§5 D2, D4, D7).
#
# WHAT IT DOES (--apply), in order; ANY failure before the commit changes nothing anywhere:
#   1. checks the signer (typed --attest token; RATIFY_OPERATOR typed, not a default/system/agent name);
#   2. fetches origin/main and stages a detached scratch worktree of it under /mnt/raid0/llm/tmp. Everything below
#      happens in that worktree, never in your checkout. This script must be byte-identical to origin/main's copy;
#   3. preflight: the sha256 of each patch, the pre-state sha256 of all six targets, the four hook files ABSENT on
#      origin/main, the receipt index absent, the receipt checker clean, the push lock FREE;
#   4. `git apply --check` of A, B, C and D one at a time, then of A+B+C+D together. A failure aborts before any write;
#   5. applies A+B+C+D to the working tree, then runs postflight: the post-state sha256 of all six targets and the four
#      hook files, additions only (zero removed lines), each new rule head exactly once, settings.json parses with the
#      hook registered once, and the hook's own test passes;
#   6. emits the MEASUREMENT.md §5 consolidated receipt over all six states, then the decision receipt and the keyed
#      index;
#   7. commits exactly thirteen paths (six targets, four hook files, three receipts) on the detached stage, with a
#      D9-ack line naming the signer, and pushes HEAD:main through
#      scripts/coordination/serialized_push.py's push lock. A rejected push changes nothing on origin; re-run.
#
# WHAT IT DOES NOT DO: start, stop, reload or signal any process; touch any other file; run any purge. The hook becomes
# live in a session once that session's checkout of .claude/settings.json carries the registration, i.e. after the
# checkout syncs to main.
#
# IDEMPOTENT: origin/main already at all six post-state pins with the index present -> ALREADY RATIFIED, exit 0.
# Any half state (some targets amended, or index present without the amendment) is refused.
#
# ROLLBACK: `git revert <ratify commit>` on a fresh origin/main worktree, then push through serialized_push.py. That is
# a human-only write, so the operator runs it. The revert removes the doctrine, the §5 clause, the hook registration
# and the hook files in one step.
#
# BASE_REF (preparation only): a dry run may stage from another ref, such as the preparing branch before it lands.
# --apply always stages from a fresh origin/main.
set -euo pipefail
export PATH="/usr/bin:/bin:${PATH}"

SCRIPT_PATH="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/$(basename "${BASH_SOURCE[0]}")"
ROOT="${ROOT:-$(cd "$(dirname "$SCRIPT_PATH")/../.." && pwd)}"
SCRIPT_REL="scripts/operator/ratify_ws58_retention_lessons_20261025.sh"
STAGE_PARENT="/mnt/raid0/llm/tmp"
LOCK_AGENT="operator-ratify-ws58-retention"
SYS_PY="/usr/bin/python3"

GATE_ID="RATIFY-WS58-RETENTION-LESSONS-20261025"
PATCH_A="artifacts/operator/ws58-calendar-lessons-20261025.human-only.patch"
PATCH_B="artifacts/operator/ws58-retention-s5-20261025.human-only.patch"
PATCH_C="artifacts/operator/ws58-destructive-ops-hook-20261025.human-only.patch"
PATCH_D="artifacts/operator/ws58-destructive-scratch-hook-files-20261025.patch"
PATCHES=("$PATCH_A" "$PATCH_B" "$PATCH_C" "$PATCH_D")
PATCH_SHAS=(
  "be6928de0d61857cdef8a49d07969d91cf9c2b6f30194d65927baa0fcffea655"
  "e94621633d23460723d72926c77ef3185fe1c35d70c52a68501e720f00e20877"
  "523005b5a4b7af5b9f5060797ddbc0ef96f88a88fa92d7ca37b721671d1f1db0"
  "f393e7b50055556c5fb4d4e7629211c2e2579fb61a2ac82720ff43ae14f5f976"
)
PACKAGE_REL="artifacts/operator/ratify-ws58-retention-lessons-20261025.md"
CHECKER_REL="scripts/validate/check_ratification_receipts.py"
HOOK_TEST_REL="scripts/hooks/tests/test_destructive_scratch_hook.sh"
# new file | post-state sha256 (created by PATCH_D)
HOOK_FILES=(
  "scripts/hooks/check_destructive_scratch.sh|940d218b8b737d78f32dcb3b101d20f2b8acac854281889a8788fe824ac3256c"
  "scripts/hooks/destructive_scratch_scan.py|d89886e0023868085aa3edc0775a709780d1a90edd0dca12d62f56dbf22f790c"
  "scripts/hooks/tests/test_destructive_scratch_hook.sh|420c36d05880c422d5c9778e6574381d7edba821d474247b7053349929d583d8"
  "scripts/hooks/tests/destructive_scratch_cases.py|cbf195a21b695019569d9d35ff3845ff0576e5abcb7b1f04ccfaafa6cee03e24"
)
HOOK_CMD='bash "$CLAUDE_PROJECT_DIR/scripts/hooks/check_destructive_scratch.sh"'

# target | pre-state sha256 (root origin/main 2d934313e) | post-state sha256 (after A+B+C)
TARGETS=(
  "MEASUREMENT.md|8012422fa40a871e2d668904ee9c84fb449a1e25aff2d155a1249146e07d311a|07e8e91fdac9472bb53a979f260bae26e70d89dc53612cd2d6fd0dafec243a2c"
  "CLAUDE.md|7a7f20394c3999f011000df8bdba3da8ec464ebfaa468db66d2239d415c15220|14b9fe89a48e966dd7d5504fa10d74247c45bedf43797ff9eafee6565f891e1e"
  "agents/shared/OPERATING_CONSTRAINTS.md|d73ec5aa09994ae014c084800c8a26e0dcdeb1f0a2ff923e93c338e0459c9d6f|7e453c7b115b6f3f6b50623f2b6a2b2144a7210face10e8076cc7a7cb93cc6a8"
  "agents/shared/SESSION_LIFECYCLE.md|167a820f72bf5fddbded2f1b8dccbd430fc4dc1f04e1782b17023499e7548c59|8ef39caf39e962878c3ff52afd3d325afbe0a4b2522ec87f25705b4342966b42"
  ".claude/settings.json|f993ebfdb1f3bd1df8e50e7fcb236c033e483915db2a2245cc91eedee4aecbad|862be6151e732094dea8b9732101bacac5a7361a2c99b1f9ef86e5a91681f151"
  "artifacts/operator/autokernel-policy-draft/RATIFICATION_LEDGER.md|451a99431ad119e4862d5f806bb47341851cea181413c443049f99245c1697c5|83e7deb2bf496c573a05c364b335b1bcab9d8846349b0d7261bdbe399ccf58bc"
)
# rule heads each change set adds; each must occur exactly once in its file afterwards
ANCHORS=(
  "agents/shared/OPERATING_CONSTRAINTS.md|- **Scratch is scratch: nothing durable lives only in \`/mnt/raid0/llm/tmp\`.**"
  "agents/shared/OPERATING_CONSTRAINTS.md|**A dismissed or declined question pauses only the item it asked about**"
  "agents/shared/OPERATING_CONSTRAINTS.md|- **Codex and the compute calendar.**"
  "agents/shared/SESSION_LIFECYCLE.md|- **A result tick names its belief.**"
  "CLAUDE.md|That forbids inventing a run's **measurement** warrant."
  "MEASUREMENT.md|- **Evidence retention and reclamation** *(operator-ratified 2026-10-25, \`$GATE_ID\`)*"
  "MEASUREMENT.md|- **2026-10-25 (v2.x)** — AMENDMENT (§5, \`$GATE_ID\`)"
  "agents/shared/OPERATING_CONSTRAINTS.md|   - **Citation check: cited is not removable.**"
  "agents/shared/OPERATING_CONSTRAINTS.md|   **Purge only through \`scripts/safety/trash-sweep.sh\`, after at least 7 days in the trash.**"
  "agents/shared/OPERATING_CONSTRAINTS.md|5. **Reclaims go through the sanctioned path.**"
)
RECEIPT_REL="artifacts/operator/ratify_ws58_retention_lessons_20261025.json"
CONSOLIDATED_REL="artifacts/operator/ratify_ws58_retention_lessons_20261025.receipt.json"
INDEX_REL="artifacts/operator/receipts/$GATE_ID.json"

MODE="review"; ATTEST=""; DO_PUSH=1
while [ "$#" -gt 0 ]; do
  case "$1" in
    --dry-run|--review) MODE="review" ;;
    --apply)   MODE="apply" ;;
    --verify)  MODE="verify" ;;
    --no-push) DO_PUSH=0 ;;
    --attest)  shift; ATTEST="${1:-}" ;;
    *) echo "usage: $0 [--dry-run | --verify | --apply --attest $GATE_ID [--no-push]]" >&2; exit 64 ;;
  esac
  shift
done

say() { printf '%s\n' "$*"; }
die() { printf 'REFUSING: %s\n' "$*" >&2; exit 65; }
g() { git -c safe.directory='*' -C "$@"; }
sha() { sha256sum -- "$1" | awk '{print $1}'; }
ok() { printf '  ok    %s\n' "$*"; }

for tool in git sha256sum awk jq "$SYS_PY"; do command -v "$tool" >/dev/null || die "$tool not available"; done
[ -f "$ROOT/scripts/coordination/serialized_push.py" ] || die "ROOT=$ROOT is not an epyc-root checkout"
PUSHER="$ROOT/scripts/coordination/serialized_push.py"

# ---------------------------------------------------------------- 1. signer
if [ "$MODE" = "apply" ]; then
  [ "$ATTEST" = "$GATE_ID" ] || die "--apply needs the typed confirmation --attest $GATE_ID. Nothing written."
  [ -z "${BASE_REF:-}" ] || [ "${BASE_REF}" = "origin/main" ] || die "--apply always stages from origin/main; unset BASE_REF."
  # shellcheck source=/dev/null
  source "$ROOT/scripts/operator/lib/ratify_operator.sh"
  ratify_require_operator   # exits 65 on an unset/default/system/login/agent name
  say "signer: $RATIFY_OPERATOR"
fi

g "$ROOT" fetch -q origin main || die "cannot fetch origin main in $ROOT"
BASE="${BASE_REF:-origin/main}"
BASE_SHA="$(g "$ROOT" rev-parse --verify "$BASE^{commit}")" || die "cannot resolve $BASE"
say "== base $BASE = $BASE_SHA =="

# ---------------------------------------------------------------- verify (read-only, against origin/main)
if [ "$MODE" = "verify" ]; then
  vfail=0
  for t in "${TARGETS[@]}"; do
    IFS='|' read -r rel pre post <<<"$t"
    have="$(g "$ROOT" show "origin/main:$rel" | sha256sum | awk '{print $1}')"
    if [ "$have" = "$post" ]; then ok "$rel at post-state ${post:0:12}"
    else say "  FAIL  $rel is ${have:0:12}, post-state is ${post:0:12} (pre-state ${pre:0:12})"; vfail=1; fi
  done
  for f in "$RECEIPT_REL" "$CONSOLIDATED_REL" "$INDEX_REL"; do
    if g "$ROOT" cat-file -e "origin/main:$f" 2>/dev/null; then ok "$f on origin/main"
    else say "  FAIL  $f not on origin/main"; vfail=1; fi
  done
  [ "$vfail" -eq 0 ] && { say "VERIFIED: $GATE_ID is on origin/main, pinned and receipted."; exit 0; }
  exit 1
fi

# ---------------------------------------------------------------- 2. stage
STAGE="$(mktemp -d "$STAGE_PARENT/ratify-ws58-retention.XXXXXX")"
WT="$STAGE/root"
TMPD="$(mktemp -d "$STAGE/work.XXXXXX")"
WT_ADDED=0; KEEP_STAGE=0
cleanup() {
  local rc=$?
  if [ "$WT_ADDED" -eq 1 ] && [ "$KEEP_STAGE" -eq 0 ]; then
    # The stage is a throwaway detached worktree of $BASE. Its only content beyond $BASE is this run's
    # applied patches and receipts, which are reproducible from the patches, or already pushed.
    g "$ROOT" worktree remove --force "$WT" >/dev/null 2>&1 || say "WARN: could not remove stage worktree $WT"
  fi
  rm -rf "$TMPD"
  [ "$KEEP_STAGE" -eq 1 ] || rmdir "$STAGE" 2>/dev/null || true   # non-empty (a kept refused receipt) stays
  exit "$rc"
}
trap cleanup EXIT
g "$ROOT" worktree add -q --detach "$WT" "$BASE_SHA" || die "could not stage a worktree of $BASE"
WT_ADDED=1
ok "staged detached worktree $WT at ${BASE_SHA:0:12}"

# ---------------------------------------------------------------- 3. preflight
say "== preflight (mode=$MODE) =="
fail=0
pinchk() { # label expected found
  if [ "$2" = "$3" ]; then ok "$1 (${3:0:12})"; else printf '  FAIL  %s: expected %s, found %s\n' "$1" "$2" "$3"; fail=1; fi
}
staged_script_sha="$(sha "$WT/$SCRIPT_REL" 2>/dev/null || echo absent)"
if [ "$(sha "$SCRIPT_PATH")" = "$staged_script_sha" ]; then ok "this script is byte-identical to $BASE:$SCRIPT_REL"
elif [ "$MODE" = "apply" ]; then printf '  FAIL  this script differs from %s:%s (%s); run the copy on origin/main\n' "$BASE" "$SCRIPT_REL" "${staged_script_sha:0:12}"; fail=1
else say "  WARN  this script differs from $BASE:$SCRIPT_REL (review only)"; fi
for i in 0 1 2 3; do
  if [ -f "$WT/${PATCHES[$i]}" ]; then pinchk "patch ${PATCHES[$i]}" "${PATCH_SHAS[$i]}" "$(sha "$WT/${PATCHES[$i]}")"
  else say "  FAIL  ${PATCHES[$i]} not on $BASE"; fail=1; fi
done
for t in "${TARGETS[@]}"; do
  IFS='|' read -r rel pre post <<<"$t"
  have="$(sha "$WT/$rel")"
  if [ "$have" = "$post" ]; then say "  NOTE  $rel already at post-state"; fi
  pinchk "pre-state $rel" "$pre" "$have"
done
for h in "${HOOK_FILES[@]}"; do
  f="${h%%|*}"
  if [ -e "$WT/$f" ]; then say "  FAIL  $f already exists on $BASE (patch D creates it)"; fail=1; else ok "absent on $BASE (D creates it): $f"; fi
done
if [ -f "$WT/$PACKAGE_REL" ]; then ok "present on $BASE: $PACKAGE_REL"; else say "  FAIL  missing on $BASE: $PACKAGE_REL"; fail=1; fi
for f in "$RECEIPT_REL" "$CONSOLIDATED_REL" "$INDEX_REL"; do
  if [ -e "$WT/$f" ]; then say "  FAIL  $f already exists on $BASE (gate spent or half state)"; fail=1; fi
done
if "$SYS_PY" "$WT/$CHECKER_REL" --repo-root "$WT" >/dev/null 2>&1; then ok "receipt checker exits 0 before the amendment"
else say "  FAIL  receipt checker does not exit 0 before the amendment"; fail=1; fi
if [ "$MODE" = "apply" ] && [ "$DO_PUSH" -eq 1 ]; then
  st="$("$SYS_PY" "$PUSHER" --agent "$LOCK_AGENT" --repo "$ROOT" --lock-name push --status 2>&1 || true)"
  case "$st" in *FREE*) ok "push lock FREE" ;; *) say "  FAIL  push lock not free: $st"; fail=1 ;; esac
fi

# idempotence: everything already landed?
all_post=1
for t in "${TARGETS[@]}"; do
  IFS='|' read -r rel pre post <<<"$t"
  [ "$(sha "$WT/$rel")" = "$post" ] || all_post=0
done
if [ "$all_post" -eq 1 ] && [ -f "$WT/$INDEX_REL" ]; then
  say "ALREADY RATIFIED: $BASE carries all six post-state pins and $INDEX_REL. Nothing to do."; exit 0
fi

# ---------------------------------------------------------------- 4. git apply --check (each, then combined)
say "== git apply --check =="
for i in 0 1 2 3; do
  [ -f "$WT/${PATCHES[$i]}" ] || continue
  if g "$WT" apply --check "${PATCHES[$i]}" 2>"$TMPD/check.err"; then ok "apply --check ${PATCHES[$i]}"
  else printf '  FAIL  apply --check %s\n' "${PATCHES[$i]}"; sed 's/^/        /' "$TMPD/check.err"; fail=1; fi
done
if g "$WT" apply --check "${PATCHES[@]}" 2>"$TMPD/check.err"; then ok "apply --check A+B+C+D together (in order)"
else say "  FAIL  apply --check A+B+C+D together"; sed 's/^/        /' "$TMPD/check.err"; fail=1; fi
[ "$fail" -eq 0 ] || die "preflight failed against $BASE. Nothing was written anywhere. A moved target means REGENERATE the bundle (package md, section Regenerate); never force or fuzz."
say "  preflight clean"

# ---------------------------------------------------------------- 5. apply + postflight (stage only)
say "== apply (stage worktree, working tree only) =="
for t in "${TARGETS[@]}"; do IFS='|' read -r rel pre post <<<"$t"; mkdir -p "$TMPD/pre/$(dirname "$rel")"; cp "$WT/$rel" "$TMPD/pre/$rel"; done
STATE_ARGS=(); for t in "${TARGETS[@]}"; do IFS='|' read -r rel pre post <<<"$t"; STATE_ARGS+=(--state "$rel"); done
"$SYS_PY" "$WT/scripts/operator/ratification_receipt.py" capture --repo-root "$WT" "${STATE_ARGS[@]}" --out "$TMPD/pre.json" \
  || die "could not snapshot the pre-amendment state"
g "$WT" apply "${PATCHES[@]}" || die "git apply failed in the stage after a clean --check (nothing outside the stage changed)"

say "== postflight =="
pf=0
for t in "${TARGETS[@]}"; do
  IFS='|' read -r rel pre post <<<"$t"
  have="$(sha "$WT/$rel")"
  if [ "$have" = "$post" ]; then ok "post-state $rel (${have:0:12})"; else printf '  FAIL  post-state %s: expected %s found %s\n' "$rel" "$post" "$have"; pf=1; fi
done
for h in "${HOOK_FILES[@]}"; do
  rel="${h%%|*}"; post="${h#*|}"
  have="$(sha "$WT/$rel" 2>/dev/null || echo absent)"
  if [ "$have" = "$post" ]; then ok "new file $rel (${have:0:12})"; else printf '  FAIL  new file %s: expected %s found %s\n' "$rel" "$post" "$have"; pf=1; fi
done
anchor_args=(); for a in "${ANCHORS[@]}"; do anchor_args+=("$a"); done
if "$SYS_PY" - "$WT" "$TMPD/pre" "$HOOK_CMD" "${anchor_args[@]}" <<'PYEOF'
import difflib, json, sys
from pathlib import Path
wt, pre, hook_cmd, anchors = Path(sys.argv[1]), Path(sys.argv[2]), sys.argv[3], sys.argv[4:]
ok = True
for p in sorted(pre.rglob("*")):
    if not p.is_file():
        continue
    rel = p.relative_to(pre)
    a = p.read_text(encoding="utf-8").split("\n")
    b = (wt / rel).read_text(encoding="utf-8").split("\n")
    d = list(difflib.unified_diff(a, b, lineterm="", n=0))
    rem = [l for l in d if l.startswith("-") and not l.startswith("---")]
    add = [l for l in d if l.startswith("+") and not l.startswith("+++")]
    if rem:
        print(f"  FAIL  {rel}: {len(rem)} line(s) removed or rewritten; this bundle is additions only"); ok = False
    else:
        print(f"  ok    {rel}: additions only (+{len(add)})")
for spec in anchors:
    rel, needle = spec.split("|", 1)
    n = (wt / rel).read_text(encoding="utf-8").count(needle)
    if n != 1:
        print(f"  FAIL  {rel}: expected exactly one {needle[:70]!r}, found {n}"); ok = False
print(f"  ok    {len(anchors)} rule heads present exactly once" if ok else "  FAIL  rule-head check")
try:
    s = json.loads((wt / ".claude/settings.json").read_text(encoding="utf-8"))
    cmds = [h.get("command") for blk in s["hooks"]["PreToolUse"] if blk.get("matcher") == "Bash" for h in blk["hooks"]]
    if cmds.count(hook_cmd) != 1:
        print(f"  FAIL  settings.json: destructive-scratch hook registered {cmds.count(hook_cmd)}x on Bash"); ok = False
    else:
        print("  ok    settings.json parses; destructive-scratch hook registered once on PreToolUse Bash")
except Exception as exc:  # noqa: BLE001
    print(f"  FAIL  settings.json: {type(exc).__name__}: {exc}"); ok = False
sys.exit(0 if ok else 1)
PYEOF
then :; else pf=1; fi
if (cd "$WT" && bash "$HOOK_TEST_REL" >"$TMPD/hooktest.out" 2>&1); then ok "hook test: $(tail -1 "$TMPD/hooktest.out")"
else say "  FAIL  hook test"; sed 's/^/        /' "$TMPD/hooktest.out" | tail -20; pf=1; fi
[ "$pf" -eq 0 ] || die "postflight failed. Only the throwaway stage was touched; it is removed on exit. Nothing was committed or pushed."
say "  postflight clean"

# ---------------------------------------------------------------- 6. receipts
say "== MEASUREMENT.md §5 consolidated receipt =="
OPERATOR_NAME="${RATIFY_OPERATOR:-DRY-RUN-PREVIEW}"
EMIT_ANCHORS=(); for a in "${ANCHORS[@]}"; do EMIT_ANCHORS+=(--anchor "${a#*|}"); done
VALS=(--validation "python3 $CHECKER_REL --repo-root ."
      --validation "bash $HOOK_TEST_REL"
      --validation "python3 -c 'import json; json.load(open(\".claude/settings.json\"))'")
for t in "${TARGETS[@]}"; do
  IFS='|' read -r rel pre post <<<"$t"
  VALS+=(--validation "test \"\$(sha256sum $rel | cut -d' ' -f1)\" = $post")
done
receipt_rc=0
"$SYS_PY" "$WT/scripts/operator/ratification_receipt.py" emit \
  --repo-root "$WT" \
  --pre "$TMPD/pre.json" \
  --protocol-id MEASUREMENT-S5-EVIDENCE-RETENTION-AND-DESTRUCTIVE-OPS \
  "${EMIT_ANCHORS[@]}" \
  --ratification-id "$GATE_ID" \
  --script "$SCRIPT_PATH" \
  --operator "$OPERATOR_NAME" \
  --no-evidence-reason "governance and doctrine amendment, not a measured claim; the loss inventory that motivates it (244 real losses of handoff-cited tmp paths, removal events E0-E4) is narrated in the committed docs/reference/tmp-loss-reconcile-2026-10-25.md, whose working tables sit in scratch and are not cited as evidence" \
  "${VALS[@]}" \
  --out "$WT/$CONSOLIDATED_REL" || receipt_rc=$?
if [ "$receipt_rc" -ne 0 ]; then
  # The stage worktree is removed on exit; the refused receipt is copied beside it, so $STAGE survives for reading.
  if [ -f "$WT/$CONSOLIDATED_REL" ]; then
    cp "$WT/$CONSOLIDATED_REL" "$STAGE/refused.receipt.json"
    say "  refused receipt kept for reading: $STAGE/refused.receipt.json"
  fi
  die "consolidated receipt returned $receipt_rc (1 REFUSED, 2 COULD-NOT-CHECK). Nothing committed or pushed."
fi
ok "consolidated receipt RATIFIED-shape: $CONSOLIDATED_REL"

RATIFIED_AT="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
PATCH_PINS="$(for i in 0 1 2 3; do printf '%s %s\n' "${PATCH_SHAS[$i]}" "${PATCHES[$i]}"; done)"
STATE_PINS="$(printf '%s\n' "${TARGETS[@]}")"
WT="$WT" RECEIPT_REL="$RECEIPT_REL" INDEX_REL="$INDEX_REL" CONSOLIDATED_REL="$CONSOLIDATED_REL" GATE_ID="$GATE_ID" \
OPERATOR="$OPERATOR_NAME" TS="$RATIFIED_AT" BASE_SHA="$BASE_SHA" SCRIPT_SHA="$(sha "$SCRIPT_PATH")" \
SCRIPT_REL="$SCRIPT_REL" PACKAGE_REL="$PACKAGE_REL" PACKAGE_SHA="$(sha "$WT/$PACKAGE_REL")" \
PATCH_PINS="$PATCH_PINS" STATE_PINS="$STATE_PINS" "$SYS_PY" - <<'PYEOF' || die "could not write the decision receipt or keyed index. Nothing committed or pushed."
import json, os
e = os.environ
patches = [{"path": l.split(" ", 1)[1], "sha256": l.split(" ", 1)[0]} for l in e["PATCH_PINS"].splitlines() if l.strip()]
state = {}
for l in e["STATE_PINS"].splitlines():
    if l.strip():
        rel, pre, post = l.split("|")
        state[rel] = {"sha256_before": pre, "sha256_after": post}
doc = {
    "schema": "epyc.operating_constraints_amendment.v1",
    "gate_id": e["GATE_ID"],
    "status": "ratified",
    "ratified_at": e["TS"],
    "operator": e["OPERATOR"],
    "signature_channel": "operator-run script (--attest typed confirmation)",
    "operator_decisions": {
        "A": "2026-10-25: encode the ws58 calendar lessons in project files (human-only half)",
        "B": "2026-10-25 D2/D7: \"ratify the amended retention §5\"",
        "C": "2026-10-25 D4: \"prepare the doctrine change plus the PreToolUse hook for signature\"",
    },
    "change_sets": {
        "A": "OPERATING_CONSTRAINTS.md (scratch is scratch; dismissed question pauses only its item; Codex compute limits), SESSION_LIFECYCLE.md (a result tick names its belief), CLAUDE.md (recording conclusions is not inventing warrant)",
        "B": "MEASUREMENT.md §5 'Evidence retention and reclamation' (homes; reproducible data never carried; three durability classes aligned to the 2026-08-03 ruling; one reclamation predicate for every reclaimer; three-state verifier; no reclamation authority granted; the 2026-08-03 draft's autonomous-loop expiry grant NOT enacted) + CHANGELOG; RATIFICATION_LEDGER.md item-5 row",
        "C": "OPERATING_CONSTRAINTS.md Destructive operations (citation check; trash purge only via trash-sweep.sh after >=7 days; item 5 sanctioned reclaim path + hook) and the .claude/settings.json PreToolUse Bash registration of scripts/hooks/check_destructive_scratch.sh",
        "D": "the hook files themselves (scripts/hooks/check_destructive_scratch.sh, destructive_scratch_scan.py, tests/test_destructive_scratch_hook.sh, tests/destructive_scratch_cases.py); D9 loop plane, acked by this signature",
    },
    "drafted_from_outline": ["B: the reconcile doc states D2/D7 as an outline (widen predicate to every reclaimer, name citation sources, forbid size thresholds, purge-time re-check, align to the 08-03 ruling); the clause text was drafted from it, see the package md"],
    "origin": "docs/reference/tmp-loss-reconcile-2026-10-25.md (244 real losses of handoff-cited /mnt/raid0/llm/tmp paths; decisions D2, D4, D7)",
    "base_origin_main": e["BASE_SHA"],
    "patches": patches,
    "state": state,
    "package": {"path": e["PACKAGE_REL"], "sha256": e["PACKAGE_SHA"]},
    "consolidated_receipt": e["CONSOLIDATED_REL"],
    "applied_by": e["SCRIPT_REL"],
    "ratify_script_sha256": e["SCRIPT_SHA"],
    "processes_touched": [],
}
wt = e["WT"]
with open(os.path.join(wt, e["RECEIPT_REL"]), "x", encoding="utf-8") as fh:
    json.dump(doc, fh, indent=2, ensure_ascii=False); fh.write("\n")
os.makedirs(os.path.dirname(os.path.join(wt, e["INDEX_REL"])), exist_ok=True)
with open(os.path.join(wt, e["INDEX_REL"]), "x", encoding="utf-8") as fh:
    json.dump({"gate_id": e["GATE_ID"], "indexed_by": "ratify", "receipt": e["RECEIPT_REL"],
               "schema_version": "session_bus.receipt_index.v1", "status": "ratified"}, fh, indent=2, sort_keys=True)
    fh.write("\n"); fh.flush(); os.fsync(fh.fileno())
print(f"  ok    decision receipt {e['RECEIPT_REL']}")
print(f"  ok    keyed index      {e['INDEX_REL']}")
PYEOF
if "$SYS_PY" "$WT/$CHECKER_REL" --repo-root "$WT" >/dev/null 2>&1; then ok "receipt checker exits 0 after the amendment"
else die "receipt checker fails after the amendment. Nothing committed or pushed."; fi

COMMIT_PATHS=(); for t in "${TARGETS[@]}"; do COMMIT_PATHS+=("${t%%|*}"); done
for h in "${HOOK_FILES[@]}"; do COMMIT_PATHS+=("${h%%|*}"); done
COMMIT_PATHS+=("$RECEIPT_REL" "$CONSOLIDATED_REL" "$INDEX_REL")

if [ "$MODE" = "review" ]; then
  say ""
  say "DRY RUN COMPLETE: every check passed and the full apply + receipt pipeline ran in a throwaway stage."
  say "Nothing was committed or pushed, and the stage is removed on exit. --apply would commit these ${#COMMIT_PATHS[@]} paths on"
  say "${BASE_SHA:0:12} and push HEAD:main under the push lock:"
  printf '    %s\n' "${COMMIT_PATHS[@]}"
  say "Sign with ONE command:"
  say "    RATIFY_OPERATOR='<your name>' bash $SCRIPT_REL --apply --attest $GATE_ID"
  exit 0
fi

# ---------------------------------------------------------------- 7. commit + push (apply)
say "== commit (stage, detached at ${BASE_SHA:0:12}) =="
g "$WT" add -- "${COMMIT_PATHS[@]}"
staged="$(g "$WT" diff --cached --name-only HEAD | sort)"
want="$(printf '%s\n' "${COMMIT_PATHS[@]}" | sort)"
[ "$staged" = "$want" ] || die "stage index holds an unexpected path set; NOT committed. Staged: $(echo $staged)"
EPYC_D9_ACK="operator $RATIFY_OPERATOR signed $GATE_ID (D4: doctrine change plus the PreToolUse hook)" g "$WT" commit -q \
  -m "RATIFIED $GATE_ID: calendar lessons + MEASUREMENT.md §5 evidence retention + destructive-ops doctrine and hook (signed by $RATIFY_OPERATOR)" \
  -m "A: ws58 calendar lessons (OPERATING_CONSTRAINTS x3, SESSION_LIFECYCLE, CLAUDE.md). B: D2/D7 §5 'Evidence retention and reclamation' + CHANGELOG + AK ledger item-5 row. C: D4 Destructive operations (citation check, 7-day trash hold, sanctioned reclaim path) + PreToolUse registration of scripts/hooks/check_destructive_scratch.sh. Receipts: $RECEIPT_REL, $CONSOLIDATED_REL, $INDEX_REL. D: the hook files (scripts/hooks/, D9 loop plane). Package: $PACKAGE_REL. No process touched." \
  -m "D9-ack: operator $RATIFY_OPERATOR, by signing $GATE_ID (D4 approved 2026-10-25: prepare the doctrine change plus the PreToolUse hook for signature)" \
  || die "commit failed (a hook refused it?). Nothing pushed; the stage is removed on exit, re-run to retry."
COMMIT_SHA="$(g "$WT" rev-parse HEAD)"
ok "committed ${COMMIT_SHA:0:12}"

if [ "$DO_PUSH" -eq 0 ]; then
  KEEP_STAGE=1
  say ""
  say "SIGNED AND COMMITTED, NOT PUSHED (--no-push). The commit is $COMMIT_SHA in the stage worktree $WT."
  say "Publish it with:"
  say "    python3 $PUSHER --agent $LOCK_AGENT --repo $WT --lock-name push --acquire --token-file <tok>  # then"
  say "    git -C $WT push origin HEAD:refs/heads/main   # then --release"
  say "Remove the stage afterwards: python3 $ROOT/scripts/system/worktree_gate.py remove $WT"
  exit 0
fi

say "== push (serialized, push lock) =="
TOKDIR="$(mktemp -d "$STAGE/push-token.XXXXXX")"; chmod 700 "$TOKDIR"; TOK="$TOKDIR/lease.token"
"$SYS_PY" "$PUSHER" --agent "$LOCK_AGENT" --repo "$ROOT" --lock-name push --acquire --token-file "$TOK" >/dev/null \
  || die "could not take the push lock. Nothing pushed; re-run."
prc=0
AGENT_ID="$LOCK_AGENT" EPYC_PUSH_LOCK_HOLDER="$LOCK_AGENT" g "$WT" push -q origin HEAD:refs/heads/main || prc=$?
"$SYS_PY" "$PUSHER" --agent "$LOCK_AGENT" --repo "$ROOT" --lock-name push --release --token-file "$TOK" >/dev/null \
  || say "WARN: push lock release failed; check: python3 $PUSHER --agent $LOCK_AGENT --repo $ROOT --lock-name push --status"
rm -f "$TOK"; rmdir "$TOKDIR" 2>/dev/null || true
[ "$prc" -eq 0 ] || die "git push rejected (rc=$prc; origin/main probably moved). Nothing landed on origin; re-run to retry on the new tip."
g "$ROOT" fetch -q origin main
g "$ROOT" merge-base --is-ancestor "$COMMIT_SHA" origin/main || die "pushed, but $COMMIT_SHA is not on origin/main after fetch. Check by hand."

cat <<EOF

RATIFIED $GATE_ID by $RATIFY_OPERATOR.
  root main: $COMMIT_SHA (pushed under the push lock)
  receipts:  $RECEIPT_REL, $CONSOLIDATED_REL, $INDEX_REL
NO PROCESS WAS TOUCHED. The destructive-scratch hook goes live in each session once that session's checkout of
.claude/settings.json syncs to main.
POST-APPLY VERIFICATION (read-only):  bash $SCRIPT_REL --verify
ROLLBACK (operator): git revert $COMMIT_SHA on a fresh origin/main worktree, then push through serialized_push.py.
EOF
