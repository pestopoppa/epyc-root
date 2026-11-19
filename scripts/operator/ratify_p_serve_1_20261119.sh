#!/bin/bash
# ratify_p_serve_1_20261119.sh — P-SERVE-1: the kernel-champion serving A/B instrument protocol lands in
# Annex K, with its section-2 registry row and CHANGELOG entry.
#
#   Review (default, writes nothing):   bash scripts/operator/ratify_p_serve_1_20261119.sh
#   Apply + receipts + commit (ONE):    RATIFY_OPERATOR=<name> bash scripts/operator/ratify_p_serve_1_20261119.sh --apply
#   Apply + receipts, no commit:        RATIFY_OPERATOR=<name> bash scripts/operator/ratify_p_serve_1_20261119.sh --apply --no-commit
#   Verify the post-state (read-only):  bash scripts/operator/ratify_p_serve_1_20261119.sh --verify
#
# Or run it all from an isolated worktree off origin/main, with a typed confirmation:
#   bash scripts/operator/run_p_serve_1_ratify_20261119.sh --operator <name>
#
# AUTOKERNEL BOX RATIFY-MEAS-2 (parent RATIFY-MEAS-1, ratified 2026-09-08). Prepared by an agent for the
# operator's signature; NOT applied. Decision package: artifacts/operator/p-serve-1-decision-20261119.md.
#
# WHY. MEASUREMENT.md section 2 has no protocol row for the kernel-champion SERVING A/B instrument (the
# harness that produces the serving floor, the serving gate and the production headline;
# instrument_class=serving). Every serving number the AutoKernel campaign quoted therefore cites no
# protocol and is admissible only as an observation. P-SERVE-SEL-1 (Annex Q) is a different instrument
# (selection-policy load sweeps, unit = arm).
#
# WHAT THE AMENDMENT DOES (artifacts/operator/p-serve-1-20261119.patch; additions only, 0 lines removed)
#   measurement/protocols/kernel-research.md   (Annex K)
#     - appends section "P-SERVE-1 — Kernel-champion serving A/B instrument (RATIFIED 2026-11-19)":
#       recipe pins, per-launch residency proof (R23-60), unit = process, floor calibration (matched n in
#       24-256, interval), headline admissibility (>= 14 launches per arm), the gate rule, an
#       enforcement-state list, grammar. It DESCRIBES what loop/serving.py, serving_gate.py,
#       floor_units.py, headline_admissibility.py and accumulate.py already enforce, citing file:function.
#       Byte-identical to artifacts/operator/staged/p-serve-1-20261119.md.
#   MEASUREMENT.md
#     - section 2: one registry row appended at the end of the table (status ✅ 2026-11-19, annex K)
#     - CHANGELOG: one 2026-11-19 entry prepended (required by section 5)
#   Both MEASUREMENT.md blocks are verbatim in artifacts/operator/staged/p-serve-1-20261119.measurement-md.md,
#   which also records WHY Annex K and not Annex Q or a new annex.
#
# WHAT IT DOES NOT DO. It takes no measurement, changes no threshold, gate or code, re-verdicts nothing, and
# touches no other protocol. It does not touch coordination/session-bus/human_only_paths.yaml. Nothing here
# starts a process, takes compute, or uses the network.
#
# WHY IT NEEDS YOU. MEASUREMENT.md and measurement/protocols/*.md are human-amendment-only
# (coordination/session-bus/human_only_paths.yaml; invariant 15). An agent prepared this bundle. Only the
# operator applies it.
#
# PINS. Any mismatch is refused. If a target has moved, REGENERATE the bundle; never force or fuzz.
#   patch                              a63ca5e4e30a03cba1f209ceee94ec1895301916dbb4de7c79f86c4fc17dd73b
#   staged annex text                  e48cfbb5c6420d153cb1c81a6235475fa5b4ac095a0c7662dec3729f22a4d364
#   staged MEASUREMENT.md snippets     9210c1a7765970b0dea1df02f1d466b80117b07a6c5dfe48066a3209047b7ad9
#   MEASUREMENT.md         pre-state   bd9f2762be78557a14fa6097f748476b3f6cb3eb155aaa888116abf51ddb02a8
#   MEASUREMENT.md         post-state  92199cbbfa3500da8a41cd6803fe7ba99165365f96b4a5b15183a16a2f580152
#   protocols/kernel-research pre-state  c086e4ee9f7bffd3e25f6f88636a780ca0aa1827589bc115a5ddafe749559315
#   protocols/kernel-research post-state c5bd00d760bb70e1f300930268913b0cb002c6d05fe3712937ae320d5175dc4e
# The pre-state pins match epyc-root origin/main 9ed706cf4 (2026-11-19). A stale checkout is refused:
# fast-forward it first.
#
# COMMIT. --apply commits exactly the five paths below on ROOT's current branch, through a private
# index seeded from HEAD, after re-hashing the staged targets against the post-state pins. Nothing a
# peer has staged in a shared index rides along. Preflight also proves all five paths clean first.
# Pushing is left to you (scripts/coordination/serialized_push.py); the command is printed.
#
# ALL OR NOTHING. Preflight refuses the whole bundle on any single mismatch; if postflight or the receipt
# fails, apply restores both targets from backup and removes the receipts.
#
# IDEMPOTENT. When both targets sit at their post-state pins and the decision receipt and keyed index
# exist, a re-run prints ALREADY RATIFIED and exits 0 without writing. Every other partial state is
# refused and left for resolution by hand.
#
# ROOT defaults to the checkout this script lives in. Override it with ROOT=<epyc-root checkout>.
set -euo pipefail

SCRIPT_PATH="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/$(basename "${BASH_SOURCE[0]}")"
ROOT="${ROOT:-$(cd "$(dirname "$SCRIPT_PATH")/../.." && pwd)}"
SCRIPT_REL="scripts/operator/ratify_p_serve_1_20261119.sh"

PATCH_REL="artifacts/operator/p-serve-1-20261119.patch"
STAGED_ANNEX_REL="artifacts/operator/staged/p-serve-1-20261119.md"
STAGED_SNIPPET_REL="artifacts/operator/staged/p-serve-1-20261119.measurement-md.md"
PATCH="$ROOT/$PATCH_REL"
MEAS_REL="MEASUREMENT.md"
K_REL="measurement/protocols/kernel-research.md"
TARGETS=("$MEAS_REL" "$K_REL")
GATE_ID="RATIFY-P-SERVE-1-20261119"
RECEIPT_REL="artifacts/operator/ratify_p_serve_1_20261119.json"
INDEX_REL="artifacts/operator/receipts/$GATE_ID.json"
# Beside the decision receipt, not in receipts/: that directory is the keyed-index namespace, and
# check_ratifier_receipt_contract.sh reports a non-pointer file there as UNRESOLVED-TARGET.
CONSOLIDATED_REL="artifacts/operator/ratify_p_serve_1_20261119.receipt.json"
RECEIPT="$ROOT/$RECEIPT_REL"
INDEX="$ROOT/$INDEX_REL"
CONSOLIDATED="$ROOT/$CONSOLIDATED_REL"
COMMIT_PATHS=("$MEAS_REL" "$K_REL" "$RECEIPT_REL" "$INDEX_REL" "$CONSOLIDATED_REL")
COMMIT_SUBJECT="RATIFIED: P-SERVE-1 — kernel-champion serving A/B instrument protocol, Annex K (RATIFY-MEAS-2, 2026-11-19)"
CHANGELOG_ANCHOR='- **2026-11-19 (v2.x)** — AMENDMENT (Annex K, new protocol `P-SERVE-1`): the kernel-champion serving'
REGISTRY_ANCHOR='| P-SERVE-1 | Kernel-champion serving A/B instrument:'
ANNEX_HEADING='## P-SERVE-1 — Kernel-champion serving A/B instrument (RATIFIED 2026-11-19)'

PATCH_SHA256="a63ca5e4e30a03cba1f209ceee94ec1895301916dbb4de7c79f86c4fc17dd73b"
STAGED_ANNEX_SHA256="e48cfbb5c6420d153cb1c81a6235475fa5b4ac095a0c7662dec3729f22a4d364"
STAGED_SNIPPET_SHA256="9210c1a7765970b0dea1df02f1d466b80117b07a6c5dfe48066a3209047b7ad9"
MEAS_PRE_SHA256="bd9f2762be78557a14fa6097f748476b3f6cb3eb155aaa888116abf51ddb02a8"
MEAS_POST_SHA256="92199cbbfa3500da8a41cd6803fe7ba99165365f96b4a5b15183a16a2f580152"
K_PRE_SHA256="c086e4ee9f7bffd3e25f6f88636a780ca0aa1827589bc115a5ddafe749559315"
K_POST_SHA256="c5bd00d760bb70e1f300930268913b0cb002c6d05fe3712937ae320d5175dc4e"

MODE="review"; DO_COMMIT=1
for arg in "$@"; do
  case "$arg" in
    --review|--dry-run) MODE="review" ;;
    --apply)            MODE="apply" ;;
    --verify)           MODE="verify" ;;
    --no-commit)        DO_COMMIT=0 ;;
    -h|--help)          sed -n '2,70p' "$SCRIPT_PATH"; exit 0 ;;
    *) echo "usage: $0 [--review | --apply [--no-commit] | --verify]   (default: --review, writes nothing)" >&2; exit 64 ;;
  esac
done
# The signer is TYPED, never defaulted: unset, system-account (node, root, id -un) and
# agent-id names are refused before anything is written (2026-09-27 governance repair).
source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/lib/ratify_operator.sh"
[ "$MODE" != "apply" ] || ratify_require_operator
if [ "$DO_COMMIT" -eq 0 ] && [ "$MODE" != "apply" ]; then
  echo "usage: --no-commit only makes sense with --apply" >&2; exit 64
fi

say() { printf '%s\n' "$*"; }
die() { printf 'REFUSING: %s\n' "$*" >&2; exit 65; }
sha() { sha256sum "$1" | awk '{print $1}'; }

command -v python3   >/dev/null || die "python3 not on PATH"
command -v sha256sum >/dev/null || die "sha256sum not on PATH"
command -v git       >/dev/null || die "git not on PATH"
for t in "${TARGETS[@]}"; do [ -f "$ROOT/$t" ] || die "$t not found under ROOT=$ROOT"; done
[ -f "$ROOT/scripts/operator/ratification_receipt.py" ] \
  || die "section-5 receipt tool missing at $ROOT/scripts/operator/ratification_receipt.py"

# ---------------------------------------------------------------- bundle pins (what you review is what lands)
[ -f "$PATCH" ] || die "patch not found at $PATCH"
[ -f "$ROOT/$STAGED_ANNEX_REL" ]   || die "staged annex text not found at $ROOT/$STAGED_ANNEX_REL"
[ -f "$ROOT/$STAGED_SNIPPET_REL" ] || die "staged MEASUREMENT.md snippets not found at $ROOT/$STAGED_SNIPPET_REL"
got="$(sha "$PATCH")"
[ "$got" = "$PATCH_SHA256" ] || die "patch hash mismatch: expected $PATCH_SHA256, found $got. The text you reviewed is not the text that would be applied."
got="$(sha "$ROOT/$STAGED_ANNEX_REL")"
[ "$got" = "$STAGED_ANNEX_SHA256" ] || die "staged annex hash mismatch: expected $STAGED_ANNEX_SHA256, found $got."
got="$(sha "$ROOT/$STAGED_SNIPPET_REL")"
[ "$got" = "$STAGED_SNIPPET_SHA256" ] || die "staged snippet hash mismatch: expected $STAGED_SNIPPET_SHA256, found $got."

# Structural tie between the reviewable staged text and the target files: the annex section is the
# staged file appended verbatim after one blank line, and each fenced MEASUREMENT.md block from the
# snippet file is present verbatim exactly once. Used by postflight and --verify.
check_landed() { # check_landed <MEASUREMENT.md> <kernel-research.md> <pre-kernel-research.md or ->
  python3 - "$1" "$2" "$3" "$ROOT/$STAGED_ANNEX_REL" "$ROOT/$STAGED_SNIPPET_REL" <<'PYEOF'
import re, sys
meas_p, q_p, k_pre_p, annex_p, snip_p = sys.argv[1:6]
meas = open(meas_p, encoding="utf-8").read()
q = open(q_p, encoding="utf-8").read()
annex = open(annex_p, encoding="utf-8").read()
snip = open(snip_p, encoding="utf-8").read()
ok = True
blocks = re.findall(r"```\n(.*?)```\n", snip, re.S)
if len(blocks) != 2:
    print(f"  FAIL  staged snippet file: expected 2 fenced blocks, found {len(blocks)}"); ok = False
for b in blocks:
    n = meas.count(b)
    if n != 1:
        print(f"  FAIL  MEASUREMENT.md: staged block present {n}x (want 1): {b.splitlines()[0][:70]!r}"); ok = False
if not q.endswith("\n" + annex):
    print("  FAIL  kernel-research.md does not end with the staged annex text verbatim"); ok = False
if k_pre_p != "-":
    k_pre = open(k_pre_p, encoding="utf-8").read()
    if q != k_pre + "\n" + annex:
        print("  FAIL  kernel-research.md post-state != pre-state + blank line + staged annex text"); ok = False
if q.count("## P-SERVE-1 ") != 1:
    print("  FAIL  kernel-research.md: P-SERVE-1 heading not present exactly once"); ok = False
row = [l for l in meas.split("\n") if l.startswith("| P-SERVE-1 |")]
if len(row) != 1 or not row[0].rstrip().endswith("| ✅ 2026-11-19 | K |"):
    print(f"  FAIL  MEASUREMENT.md: registry row for P-SERVE-1 missing, duplicated or not '✅ 2026-11-19 | K'"); ok = False
if ok:
    print("  ok    staged text landed verbatim (annex appended; registry row + CHANGELOG entry present once)")
sys.exit(0 if ok else 1)
PYEOF
}

meas_now="$(sha "$ROOT/$MEAS_REL")"
k_now="$(sha "$ROOT/$K_REL")"
meas_post=0; [ "$meas_now" = "$MEAS_POST_SHA256" ] && meas_post=1
# A LATER amendment may be appended after the annex (the AutoKernel bundle appends P-AK-SEARCH-1-A5a). So
# "post-state" is: the file, or its prefix ending exactly at the single staged-annex occurrence, hashes to the pin.
K_VIEW="$ROOT/$K_REL"; K_VIEW_TMP=""; k_eff="$k_now"
if [ "$k_now" != "$K_POST_SHA256" ]; then
  K_VIEW_TMP="$(mktemp)"; trap 'rm -f "$K_VIEW_TMP"' EXIT
  k_eff="$(python3 - "$ROOT/$K_REL" "$ROOT/$STAGED_ANNEX_REL" "$K_VIEW_TMP" <<'PYEOF'
import hashlib, sys
q = open(sys.argv[1], "rb").read(); a = open(sys.argv[2], "rb").read()
i = q.find(a)
if i < 0 or q.find(a, i + 1) >= 0:
    print("none")
else:
    pre = q[: i + len(a)]
    open(sys.argv[3], "wb").write(pre)
    print(hashlib.sha256(pre).hexdigest())
PYEOF
)"
  [ "$k_eff" = "$K_POST_SHA256" ] && K_VIEW="$K_VIEW_TMP"
fi
k_post=0;    [ "$k_eff"    = "$K_POST_SHA256"    ] && k_post=1

# ---------------------------------------------------------------- --verify (read-only)
if [ "$MODE" = "verify" ]; then
  say "== verify (ROOT=$ROOT, read-only) =="
  vf=0
  vpin() { if [ "$2" != "$3" ]; then printf '  FAIL  %-48s expected %s found %s\n' "$1" "$2" "$3"; vf=1
           else printf '  ok    %-48s (%s)\n' "$1" "${3:0:12}"; fi; }
  vpin "MEASUREMENT.md post-state hash" "$MEAS_POST_SHA256" "$meas_now"
  vpin "kernel-research.md post-state hash (annex prefix)" "$K_POST_SHA256" "$k_eff"
  check_landed "$ROOT/$MEAS_REL" "$K_VIEW" - || vf=1
  for f in "$RECEIPT" "$INDEX" "$CONSOLIDATED"; do
    if [ -f "$f" ]; then printf '  ok    %-48s\n' "present: ${f#"$ROOT"/}"
    else printf '  FAIL  %-48s\n' "present: ${f#"$ROOT"/}"; vf=1; fi
  done
  if [ -f "$RECEIPT" ] && [ -f "$INDEX" ] && [ -f "$CONSOLIDATED" ]; then
    python3 - "$RECEIPT" "$INDEX" "$CONSOLIDATED" "$GATE_ID" "$RECEIPT_REL" "$PATCH_SHA256" \
      "$STAGED_ANNEX_SHA256" "$MEAS_PRE_SHA256" "$MEAS_POST_SHA256" "$K_PRE_SHA256" "$K_POST_SHA256" <<'PYEOF' || vf=1
import json, sys
(receipt_p, index_p, cons_p, gate, receipt_rel, patch_sha, annex_sha,
 mpre, mpost, qpre, qpost) = sys.argv[1:12]
ok = True
def bad(msg):
    global ok; ok = False; print(f"  FAIL  {msg}")
r = json.load(open(receipt_p, encoding="utf-8"))
i = json.load(open(index_p, encoding="utf-8"))
c = json.load(open(cons_p, encoding="utf-8"))
if r.get("status") != "ratified" or r.get("gate_id") != gate: bad("decision receipt: status/gate_id")
if r.get("protocol_id") != "P-SERVE-1": bad("decision receipt: protocol_id")
if not r.get("operator") or not r.get("applied_at"): bad("decision receipt: operator / applied_at")
if r.get("patch", {}).get("sha256") != patch_sha: bad("decision receipt: patch sha256")
if r.get("staged_text", {}).get("annex", {}).get("sha256") != annex_sha: bad("decision receipt: staged annex sha256")
st = r.get("state", {})
if st.get("MEASUREMENT.md") != {"sha256_before": mpre, "sha256_after": mpost}: bad("decision receipt: MEASUREMENT.md hashes")
if st.get("measurement/protocols/kernel-research.md") != {"sha256_before": qpre, "sha256_after": qpost}: bad("decision receipt: kernel-research.md hashes")
if i.get("gate_id") != gate or i.get("status") != "ratified" or not str(i.get("receipt", "")).endswith(receipt_rel):
    bad("keyed index does not point at the decision receipt as ratified")
if c.get("verdict") != "RATIFIED" or c.get("protocol_id") != "P-SERVE-1" or c.get("ratification_id") != gate:
    bad(f"consolidated receipt: verdict={c.get('verdict')!r} protocol_id={c.get('protocol_id')!r}")
if ok: print("  ok    decision receipt, keyed index and section-5 consolidated receipt agree with the pins")
sys.exit(0 if ok else 1)
PYEOF
  fi
  dirty="$(git -C "$ROOT" status --porcelain -- "${COMMIT_PATHS[@]}" 2>/dev/null || echo 'GIT-STATUS-FAILED')"
  if [ -n "$dirty" ]; then printf '  FAIL  %-48s\n%s\n' "five paths committed and clean at HEAD" "$dirty"; vf=1
  else printf '  ok    %-48s (%s)\n' "five paths committed and clean at HEAD" "$(git -C "$ROOT" rev-parse --short HEAD)"; fi
  if [ "$vf" -ne 0 ]; then
    say "VERIFY FAILED: P-SERVE-1 is not (fully) ratified in $ROOT."
    exit 1
  fi
  say "VERIFIED: P-SERVE-1 is ratified, receipted and committed in $ROOT."
  exit 0
fi

# ---------------------------------------------------------------- idempotence / partial states
if [ "$meas_post" -eq 1 ] && [ "$k_post" -eq 1 ]; then
  if [ -f "$RECEIPT" ] && [ -f "$INDEX" ]; then
    say "ALREADY RATIFIED: both targets are at their post-state pins and $RECEIPT_REL and $INDEX_REL exist. Nothing to do."
    say "Check it with: ROOT=$ROOT bash $SCRIPT_PATH --verify"
    exit 0
  fi
  die "half-applied state: both targets are amended, but the receipt ($([ -f "$RECEIPT" ] && echo present || echo MISSING)) or the keyed index ($([ -f "$INDEX" ] && echo present || echo MISSING)) is not. Resolve by hand."
fi
if [ "$meas_post" -ne "$k_post" ]; then
  die "half-applied state: MEASUREMENT.md post=$meas_post, kernel-research.md post=$k_post. Resolve by hand."
fi
[ -f "$RECEIPT" ]      && die "$RECEIPT_REL already exists, but the targets are not amended. Resolve by hand."
[ -f "$INDEX" ]        && die "keyed index $INDEX_REL already exists, so this gate is already spent. Double-signing is refused."
[ -f "$CONSOLIDATED" ] && die "$CONSOLIDATED_REL already exists. Resolve by hand."

# ---------------------------------------------------------------- preflight
say "== preflight (ROOT=$ROOT, mode=$MODE, commit=$DO_COMMIT) =="
fail=0
pin() { # pin <label> <expected> <found>
  if [ "$2" != "$3" ]; then
    printf '  FAIL  %-48s expected %s\n        %-48s found    %s\n' "$1" "$2" "" "$3"; fail=1
  else
    printf '  ok    %-48s (%s)\n' "$1" "${3:0:12}"
  fi
}
printf '  ok    %-48s (%s)\n' "patch hash" "${PATCH_SHA256:0:12}"
printf '  ok    %-48s (%s)\n' "staged annex text hash" "${STAGED_ANNEX_SHA256:0:12}"
printf '  ok    %-48s (%s)\n' "staged MEASUREMENT.md snippets hash" "${STAGED_SNIPPET_SHA256:0:12}"
pin "MEASUREMENT.md pre-state hash" "$MEAS_PRE_SHA256" "$meas_now"
pin "kernel-research.md pre-state hash" "$K_PRE_SHA256" "$k_now"

if grep -qF 'P-SERVE-1' "$ROOT/$MEAS_REL" "$ROOT/$K_REL"; then
  printf '  FAIL  %-48s\n' "P-SERVE-1 not yet in either target"; fail=1
else
  printf '  ok    %-48s\n' "P-SERVE-1 not yet in either target"
fi

# The five commit paths must carry no unrelated edits, staged or unstaged, or the commit would sweep
# a peer session's hunk into this amendment (shared-clone hazard).
dirty="$(git -C "$ROOT" status --porcelain -- "${COMMIT_PATHS[@]}" 2>/dev/null || echo 'GIT-STATUS-FAILED')"
if [ -n "$dirty" ]; then printf '  FAIL  %-48s\n%s\n' "commit paths clean in git" "$dirty"; fail=1
else printf '  ok    %-48s\n' "commit paths clean in git"; fi

if git -C "$ROOT" apply --check "$PATCH" 2>/dev/null; then
  printf '  ok    %-48s\n' "patch applies cleanly (no fuzz)"
else
  printf '  FAIL  %-48s\n' "patch applies cleanly (no fuzz)"; fail=1
fi

if [ "$fail" -ne 0 ]; then
  die "preflight failed: $ROOT is not in the state this bundle was prepared against (epyc-root origin/main 9ed706cf4). Stale checkout: fast-forward it first. Moved target: regenerate the bundle. Nothing written."
fi
say "  preflight clean"

if [ "$MODE" = "review" ]; then
  say ""
  say "== amendment diff (${PATCH_REL}) =="
  cat "$PATCH"
  say ""
  say "REVIEW ONLY: would apply the diff above to ${TARGETS[*]} (post-state pins ${MEAS_POST_SHA256:0:12} / ${K_POST_SHA256:0:12}),"
  say "write $RECEIPT_REL, $INDEX_REL and $CONSOLIDATED_REL, and commit those five paths. Nothing written."
  say "Apply with: RATIFY_OPERATOR=<your-name> ROOT=$ROOT bash $SCRIPT_PATH --apply"
  exit 0
fi

# ---------------------------------------------------------------- apply
APPLIED_AT="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
OPERATOR="$RATIFY_OPERATOR"
TMPD="$(mktemp -d)"
trap 'rm -rf "$TMPD" "$K_VIEW_TMP"' EXIT
cp "$ROOT/$MEAS_REL" "$TMPD/MEASUREMENT.md.bak"
cp "$ROOT/$K_REL"    "$TMPD/kernel-research.md.bak"
PRE="$TMPD/pre.json"
restore() {
  cp "$TMPD/MEASUREMENT.md.bak" "$ROOT/$MEAS_REL"
  cp "$TMPD/kernel-research.md.bak" "$ROOT/$K_REL"
  rm -f "$RECEIPT" "$INDEX"
}

say ""
say "== apply =="
python3 "$ROOT"/scripts/operator/ratification_receipt.py capture --repo-root "$ROOT" \
  --state "$MEAS_REL" --state "$K_REL" --out "$PRE" \
  || die "could not snapshot the pre-amendment state; nothing written"

# Working tree only, never --index: staging happens below, into a private index, after postflight.
git -C "$ROOT" apply "$PATCH" || { restore; die "git apply failed; targets restored. Nothing changed."; }

# ---------------------------------------------------------------- postflight
say ""
say "== postflight =="
pf=0
pin_pf() { if [ "$2" != "$3" ]; then printf '  FAIL  %-48s expected %s found %s\n' "$1" "$2" "$3"; pf=1
           else printf '  ok    %-48s (%s)\n' "$1" "${3:0:12}"; fi; }
pin_pf "MEASUREMENT.md post-state hash" "$MEAS_POST_SHA256" "$(sha "$ROOT/$MEAS_REL")"
pin_pf "kernel-research.md post-state hash" "$K_POST_SHA256" "$(sha "$ROOT/$K_REL")"
check_landed "$ROOT/$MEAS_REL" "$ROOT/$K_REL" "$TMPD/kernel-research.md.bak" || pf=1
# Append-or-version: not one ratified line may be removed or rewritten.
if python3 - "$TMPD/kernel-research.md.bak" "$ROOT/$K_REL" "$TMPD/MEASUREMENT.md.bak" "$ROOT/$MEAS_REL" <<'PYEOF'
import sys, difflib
ok = True
for a_path, b_path in ((sys.argv[1], sys.argv[2]), (sys.argv[3], sys.argv[4])):
    a = open(a_path, encoding="utf-8").read().split("\n")
    b = open(b_path, encoding="utf-8").read().split("\n")
    removed = [l for l in difflib.unified_diff(a, b, lineterm="", n=0)
               if l.startswith("-") and not l.startswith("---")]
    if removed:
        print(f"  FAIL  {b_path}: {len(removed)} line(s) removed or rewritten; additions only expected")
        for line in removed[:5]:
            print(f"        {line[:90]!r}")
        ok = False
if ok:
    print("  ok    additions only in both targets")
sys.exit(0 if ok else 1)
PYEOF
then :; else pf=1; fi
if [ "$pf" -ne 0 ]; then
  restore
  die "postflight failed: targets restored from backup. Nothing changed."
fi
say "  postflight clean"

# ---------------------------------------------------------------- consolidated receipt (MEASUREMENT.md section 5)
say ""
say "== section-5 consolidated receipt =="
mkdir -p "$ROOT/artifacts/operator/receipts"
receipt_rc=0
python3 "$ROOT"/scripts/operator/ratification_receipt.py emit \
  --repo-root "$ROOT" \
  --pre "$PRE" \
  --protocol-id P-SERVE-1 \
  --protocol-new \
  --anchor "$CHANGELOG_ANCHOR" \
  --anchor "$REGISTRY_ANCHOR" \
  --ratification-id "$GATE_ID" \
  --script "$SCRIPT_PATH" \
  --operator "$OPERATOR" \
  --no-evidence-reason "new protocol text, not a measured claim: no measurement has been taken under P-SERVE-1; the text describes what epyc-inference-research loop/serving.py, serving_gate.py, floor_units.py, headline_admissibility.py and accumulate.py already enforce (research main a794f5b54) and changes no threshold, gate or code; AutoKernel box RATIFY-MEAS-2, left out of RATIFY-MEAS-1 (2026-09-08)" \
  --validation "bash scripts/validate/check_claims_grammar.sh --files $K_REL $STAGED_ANNEX_REL" \
  --out "$CONSOLIDATED" || receipt_rc=$?
if [ "$receipt_rc" -ne 0 ]; then
  refused="${CONSOLIDATED%.receipt.json}.refused-$(date -u +%Y%m%dT%H%M%SZ).receipt.json"
  [ -f "$CONSOLIDATED" ] && mv "$CONSOLIDATED" "$refused"
  restore
  die "consolidated receipt returned $receipt_rc (1 REFUSED, 2 COULD-NOT-CHECK). Amendment rolled back; the receipt is kept at ${refused#"$ROOT"/} for reading."
fi

# ---------------------------------------------------------------- decision receipt + keyed index
if ! python3 - "$RECEIPT" "$INDEX" "$APPLIED_AT" "$GATE_ID" "$CONSOLIDATED_REL" "$RECEIPT_REL" \
     "$OPERATOR" "$PATCH_SHA256" "$PATCH_REL" "$SCRIPT_REL" "$(sha "$SCRIPT_PATH")" \
     "$STAGED_ANNEX_REL" "$STAGED_ANNEX_SHA256" "$STAGED_SNIPPET_REL" "$STAGED_SNIPPET_SHA256" \
     "$MEAS_PRE_SHA256" "$MEAS_POST_SHA256" "$K_PRE_SHA256" "$K_POST_SHA256" <<'PYEOF'
import sys, json, os
(receipt, index, applied_at, gate, consolidated_rel, receipt_rel, operator, patch_sha, patch_rel,
 script_rel, script_sha, annex_rel, annex_sha, snip_rel, snip_sha,
 meas_pre, meas_post, k_pre, k_post) = sys.argv[1:20]
doc = {
  "schema": "epyc.measurement.protocol_amendment.v1",
  "decision": "CREATE-PROTOCOL-P-SERVE-1",
  "gate_id": gate,
  "operator_decision": "ratify P-SERVE-1 (kernel-champion serving A/B instrument) so the serving floor, serving gate and headline cite a section-2 protocol instead of being observations",
  "ratified_at": applied_at,
  "applied_at": applied_at,
  "operator": operator,
  "status": "ratified",
  "protocol_id": "P-SERVE-1",
  "annex": "K",
  "annex_path": "measurement/protocols/kernel-research.md",
  "amendment_class": "new protocol (append to the owning annex; no new annex)",
  "registry_status": "✅ 2026-11-19",
  "protocol_summary": {
    "scope": "kernel/build/runtime-config effect on served decode throughput under the registered production recipe; fresh llama-server launch per sample; instrument_class=serving; unit = process; distinct from P-SERVE-SEL-1 (Annex Q)",
    "primary_metric": "aggregate decode tok/s = sum over np slots of predicted_per_second (higher-better); effect = median(candidate)/median(anchor) - 1",
    "recipe": "recipe_hash, launch argv, resolved-recipe build digests, paired ABBA order (matched_process_v2, 1-64 pairs), np/slots, frozen request digest",
    "residency": "R23-60: sampled across the whole launch; proven needs the window to contain the request phase and >= 1 GiB VRAM; refuted raises ServingNotResident; unsampled is unproven (recorded, not refused)",
    "floor": "unit process; matched floor n in 24-256 with a descriptive interval; legacy v1 floor n not enforced (listed in the enforcement state)",
    "headline": "independent process launches, >= 14 per arm (28 total) at sd 2.793%, MDE 3.0%, alpha .05 two-sided, power .80",
    "gate": "unit mismatch refuses; decisive = |effect| >= floor; PROMOTE only for a decisive, positive, non-regressing effect",
  },
  "provenance": "AutoKernel box RATIFY-MEAS-2 (left out of RATIFY-MEAS-1, 2026-09-08); bundle prepared by an agent from epyc-inference-research main a794f5b54",
  "not_granted": "no measurement, compute window, threshold change, code change or re-verdict of an earlier serving number",
  "patch": {"path": patch_rel, "sha256": patch_sha},
  "staged_text": {
    "annex": {"path": annex_rel, "sha256": annex_sha},
    "measurement_md_snippets": {"path": snip_rel, "sha256": snip_sha},
  },
  "state": {
    "MEASUREMENT.md": {"sha256_before": meas_pre, "sha256_after": meas_post},
    "measurement/protocols/kernel-research.md": {"sha256_before": k_pre, "sha256_after": k_post},
  },
  "tracking": {"autokernel_box": "RATIFY-MEAS-2", "parent": "RATIFY-MEAS-1",
               "decision_package": "artifacts/operator/p-serve-1-decision-20261119.md"},
  "consolidated_receipt": consolidated_rel,
  "applied_by": {"path": script_rel, "sha256": script_sha},
}
with open(receipt, "x", encoding="utf-8") as fh:
    json.dump(doc, fh, indent=2, ensure_ascii=False); fh.write("\n")
os.makedirs(os.path.dirname(index), exist_ok=True)
with open(index, "x", encoding="utf-8") as fh:
    json.dump({"gate_id": gate, "indexed_by": "ratify",
               "receipt": "/workspace/" + receipt_rel,
               "schema_version": "session_bus.receipt_index.v1", "status": "ratified"},
              fh, indent=2, sort_keys=True)
    fh.write("\n"); fh.flush(); os.fsync(fh.fileno())
print(f"  decision receipt: {receipt}")
print(f"  keyed index:      {index}")
PYEOF
then
  restore; rm -f "$CONSOLIDATED"
  die "could not write the decision receipt or keyed index. Amendment rolled back."
fi

BRANCH="$(git -C "$ROOT" rev-parse --abbrev-ref HEAD)"
if [ "$DO_COMMIT" -eq 0 ]; then
  say ""
  say "APPLIED, NOT STAGED, NOT COMMITTED (--no-commit). Commit exactly these five paths:"
  say "    git -C $ROOT add -- ${COMMIT_PATHS[*]}"
  say "    git -C $ROOT commit -m '$COMMIT_SUBJECT'     # only if nothing else is staged in this index"
  say "Then: ROOT=$ROOT bash $SCRIPT_PATH --verify"
  exit 0
fi

# ---------------------------------------------------------------- commit (private index)
say ""
say "== commit on $BRANCH =="
# A PRIVATE index seeded from HEAD, holding only these five paths: nothing a peer has staged in the
# shared index rides along, and no pathspec commit re-reads the working tree. The staged blobs of
# both targets are re-hashed against the post-state pins before committing.
PIDX="$TMPD/private.index"
MSGF="$TMPD/commit_msg.txt"
cat > "$MSGF" <<EOF
$COMMIT_SUBJECT

AutoKernel box RATIFY-MEAS-2: P-SERVE-1 is applied here by the operator
through scripts/operator/ratify_p_serve_1_20261119.sh. All pins were
verified and the section-5 consolidated receipt returned RATIFIED.

Annex K (measurement/protocols/kernel-research.md) gains P-SERVE-1, the
kernel-champion serving A/B instrument: a fresh llama-server launch per
sample under the registered production recipe, paired ABBA, with its recipe
pins, per-launch residency proof (R23-60), process-unit floor, headline
admissibility (>= 14 independent launches per arm) and gate rule. It
describes what loop/serving.py, serving_gate.py, floor_units.py,
headline_admissibility.py and accumulate.py already enforce and changes no
threshold, gate or code. MEASUREMENT.md gains the section-2 registry row
(2026-11-19, K) and a CHANGELOG entry. Additions only.

Receipts: $RECEIPT_REL,
$CONSOLIDATED_REL, $INDEX_REL.

Operator-applied by $OPERATOR
EOF
commit_manual="git -C $ROOT add -- ${COMMIT_PATHS[*]} && git -C $ROOT commit -F <message>"
GIT_INDEX_FILE="$PIDX" git -C "$ROOT" read-tree HEAD \
  || die "could not seed a private index from HEAD. The amendment and receipts ARE applied (not rolled back). Commit by hand: $commit_manual"
GIT_INDEX_FILE="$PIDX" git -C "$ROOT" add -- "${COMMIT_PATHS[@]}" \
  || die "could not stage into the private index. The amendment and receipts ARE applied (not rolled back). Commit by hand: $commit_manual"
staged_meas="$(GIT_INDEX_FILE="$PIDX" git -C "$ROOT" show ":$MEAS_REL" | sha256sum | awk '{print $1}')"
staged_k="$(GIT_INDEX_FILE="$PIDX" git -C "$ROOT" show ":$K_REL" | sha256sum | awk '{print $1}')"
if [ "$staged_meas" != "$MEAS_POST_SHA256" ] || [ "$staged_k" != "$K_POST_SHA256" ]; then
  die "a staged target does not match its post-state pin (MEASUREMENT.md ${staged_meas:0:12}, kernel-research.md ${staged_k:0:12}): something edited it after postflight. NOT committed; the amendment and receipts are applied in the working tree. Inspect: git -C $ROOT diff -- ${TARGETS[*]}"
fi
staged_list="$(GIT_INDEX_FILE="$PIDX" git -C "$ROOT" diff --cached --name-only HEAD | sort)"
expected_list="$(printf '%s\n' "${COMMIT_PATHS[@]}" | sort)"
[ "$staged_list" = "$expected_list" ] \
  || die "the private index holds an unexpected path set; NOT committed. Staged: $(echo $staged_list)"
if GIT_INDEX_FILE="$PIDX" git -C "$ROOT" commit -q -F "$MSGF"; then
  # Bring the checkout's own index up to the new HEAD for OUR five paths only.
  git -C "$ROOT" reset -q -- "${COMMIT_PATHS[@]}" \
    || say "  WARNING: 'git reset -q -- <five paths>' failed; run it by hand so the index matches HEAD."
  sha_c="$(git -C "$ROOT" rev-parse --short HEAD)"
  say "  committed $sha_c on $BRANCH:"
  git -C "$ROOT" show --stat --format='  %s' HEAD | sed 's/^/  /'
else
  die "the commit failed. The amendment and receipts ARE applied in the working tree (not rolled back). Commit by hand: $commit_manual"
fi

say ""
say "RATIFIED and committed. Not pushed. Check, then publish:"
say "    ROOT=$ROOT bash $SCRIPT_PATH --verify"
if [ "$BRANCH" = "main" ]; then
  say "    python3 $ROOT/scripts/coordination/serialized_push.py --agent operator --repo $ROOT --fetch --push"
else
  say "    git -C $ROOT push origin $BRANCH     # then land $BRANCH on main"
fi
say ""
say "Then the owning session closes the RATIFY-MEAS-2 box in the AutoKernel handoff (tick with a belief tag)."
