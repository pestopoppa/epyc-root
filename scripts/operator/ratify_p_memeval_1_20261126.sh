#!/bin/bash
# ratify_p_memeval_1_20261126.sh — OP-42: P-MEMEVAL-1 admits Tulving 200ch/100K and BEAM 128K as the M-12
# memory-on vs memory-off instruments. New protocol section appended to Annex Q
# (measurement/protocols/quality-eval.md), plus its section-2 registry row and CHANGELOG entry in MEASUREMENT.md.
#
# Prepared by an agent (opsign-20261126) from the P-SERVE-1 ratifier (RATIFY-MEAS-2, 2026-11-19), which is
# the precedent for a new-protocol MEASUREMENT amendment. NOT applied. Operator decision 2026-11-26
# (master-handoff-index commit 23e33d5ca): "OP-42 admit both + one window". The window is NOT in this bundle.
#
#   Validate only (writes nothing):  ROOT=<fresh epyc-root worktree at origin/main> bash <this> --validate-only
#   Apply + receipts + commit:       RATIFY_OPERATOR=<name> ROOT=<worktree> bash <this> --apply
#   Verify post-state (read-only):   ROOT=<worktree> bash <this> --verify
#
# The staged text, the patch and this script live beside each other in this directory; at apply time they are
# copied into the tree (artifacts/operator/staged/, artifacts/operator/, scripts/operator/) and committed with
# the receipts, so the committed record holds exactly what was reviewed.
#
# WHAT IT DOES NOT DO. No measurement, compute window, threshold, gate or code change; no re-verdict of the
# 2026-09-18 M-12a runs; no eval-pool registration; nothing on coordination/session-bus/human_only_paths.yaml.
#
# ratify-targets: MEASUREMENT.md measurement/protocols/quality-eval.md
set -euo pipefail

SRC_SCRIPT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/$(basename "${BASH_SOURCE[0]}")"
SRC_DIR="$(dirname "$SRC_SCRIPT")"
: "${ROOT:?set ROOT=<fresh epyc-root worktree at origin/main>}"
ROOT="$(cd "$ROOT" && pwd)"
SCRIPT_REL="scripts/operator/ratify_p_memeval_1_20261126.sh"
SCRIPT_PATH="$ROOT/$SCRIPT_REL"

PATCH_REL="artifacts/operator/p-memeval-1-20261126.patch"
STAGED_ANNEX_REL="artifacts/operator/staged/p-memeval-1-20261126.md"
STAGED_SNIPPET_REL="artifacts/operator/staged/p-memeval-1-20261126.measurement-md.md"
PATCH="$SRC_DIR/p-memeval-1-20261126.patch"
SRC_ANNEX="$SRC_DIR/p-memeval-1-20261126.md"
SRC_SNIPPET="$SRC_DIR/p-memeval-1-20261126.measurement-md.md"
MEAS_REL="MEASUREMENT.md"
K_REL="measurement/protocols/quality-eval.md"
TARGETS=("$MEAS_REL" "$K_REL")
GATE_ID="RATIFY-P-MEMEVAL-1-20261126"
RECEIPT_REL="artifacts/operator/ratify_p_memeval_1_20261126.json"
INDEX_REL="artifacts/operator/receipts/$GATE_ID.json"
# Beside the decision receipt, not in receipts/: that directory is the keyed-index namespace, and
# check_ratifier_receipt_contract.sh reports a non-pointer file there as UNRESOLVED-TARGET.
CONSOLIDATED_REL="artifacts/operator/ratify_p_memeval_1_20261126.receipt.json"
RECEIPT="$ROOT/$RECEIPT_REL"
INDEX="$ROOT/$INDEX_REL"
CONSOLIDATED="$ROOT/$CONSOLIDATED_REL"
COMMIT_PATHS=("$MEAS_REL" "$K_REL" "$RECEIPT_REL" "$INDEX_REL" "$CONSOLIDATED_REL" "$SCRIPT_REL" "$PATCH_REL" "$STAGED_ANNEX_REL" "$STAGED_SNIPPET_REL")
COMMIT_SUBJECT="RATIFIED: P-MEMEVAL-1 — Tulving 200ch/100K + BEAM 128K admitted as M-12 instruments, Annex Q (OP-42, 2026-11-26)"
CHANGELOG_ANCHOR='- **2026-11-26 (v2.x)** — AMENDMENT (Annex Q, new protocol `P-MEMEVAL-1`): admits Tulving 200ch/100K and BEAM 128K'
REGISTRY_ANCHOR='| P-MEMEVAL-1 | Memory-on vs memory-off long-context recall'
ANNEX_HEADING='## P-MEMEVAL-1 — Memory-on vs memory-off long-context recall instruments, Tulving 200ch and BEAM 128K (RATIFIED 2026-11-26)'

PATCH_SHA256="37275a395336c7d914eeacb60f118c781be67ed2e897dfebe9be439731462530"
STAGED_ANNEX_SHA256="33b550172fa84a3bb4f940050e762a1b3615c8747b301bbeed2ff5950dd3d70d"
STAGED_SNIPPET_SHA256="5918108365b4619aceba170f40d5bbe5a1a0397de4c53663f1919b5e9789d984"
MEAS_PRE_SHA256="53e04ad15dd635a6b463e6446e8ab58764ad97be66166793189120f8527dc745"
MEAS_POST_SHA256="f9d3121aa67a4f02c59accd2107fde71382bff895945e6c7a007c5dd17df4818"
K_PRE_SHA256="480c11ece338e00e9e21f5c6a232c0e0ef6d3ade4d54ae167a358eeaa4d045e1"
K_POST_SHA256="dcb07b7837243f15d2e8cac90cf41f3668681a6bf3bdc58ff55df919c9f40bfa"

MODE="review"; DO_COMMIT=1
for arg in "$@"; do
  case "$arg" in
    --review|--dry-run|--validate-only) MODE="review" ;;
    --apply)            MODE="apply" ;;
    --verify)           MODE="verify" ;;
    --no-commit)        DO_COMMIT=0 ;;
    -h|--help)          sed -n '2,22p' "$SRC_SCRIPT"; exit 0 ;;
    *) echo "usage: $0 [--review | --apply [--no-commit] | --verify]   (default: --review, writes nothing)" >&2; exit 64 ;;
  esac
done
# The signer is TYPED, never defaulted: unset, system-account (node, root, id -un) and
# agent-id names are refused before anything is written (2026-09-27 governance repair).
source "$ROOT/scripts/operator/lib/ratify_operator.sh"
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
[ -f "$SRC_ANNEX" ]   || die "staged annex text not found at $SRC_ANNEX"
[ -f "$SRC_SNIPPET" ] || die "staged MEASUREMENT.md snippets not found at $SRC_SNIPPET"
got="$(sha "$PATCH")"
[ "$got" = "$PATCH_SHA256" ] || die "patch hash mismatch: expected $PATCH_SHA256, found $got. The text you reviewed is not the text that would be applied."
got="$(sha "$SRC_ANNEX")"
[ "$got" = "$STAGED_ANNEX_SHA256" ] || die "staged annex hash mismatch: expected $STAGED_ANNEX_SHA256, found $got."
got="$(sha "$SRC_SNIPPET")"
[ "$got" = "$STAGED_SNIPPET_SHA256" ] || die "staged snippet hash mismatch: expected $STAGED_SNIPPET_SHA256, found $got."

# Structural tie between the reviewable staged text and the target files: the annex section is the
# staged file appended verbatim after one blank line, and each fenced MEASUREMENT.md block from the
# snippet file is present verbatim exactly once. Used by postflight and --verify.
check_landed() { # check_landed <MEASUREMENT.md> <quality-eval.md> <pre-quality-eval.md or ->
  python3 - "$1" "$2" "$3" "$SRC_ANNEX" "$SRC_SNIPPET" <<'PYEOF'
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
    print("  FAIL  quality-eval.md does not end with the staged annex text verbatim"); ok = False
if k_pre_p != "-":
    k_pre = open(k_pre_p, encoding="utf-8").read()
    if q != k_pre + "\n" + annex:
        print("  FAIL  quality-eval.md post-state != pre-state + blank line + staged annex text"); ok = False
if q.count("## P-MEMEVAL-1 ") != 1:
    print("  FAIL  quality-eval.md: P-MEMEVAL-1 heading not present exactly once"); ok = False
row = [l for l in meas.split("\n") if l.startswith("| P-MEMEVAL-1 |")]
if len(row) != 1 or not row[0].rstrip().endswith("| ✅ 2026-11-26 | Q |"):
    print(f"  FAIL  MEASUREMENT.md: registry row for P-MEMEVAL-1 missing, duplicated or not '✅ 2026-11-26 | Q'"); ok = False
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
  k_eff="$(python3 - "$ROOT/$K_REL" "$SRC_ANNEX" "$K_VIEW_TMP" <<'PYEOF'
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
  vpin "quality-eval.md post-state hash (annex prefix)" "$K_POST_SHA256" "$k_eff"
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
if r.get("protocol_id") != "P-MEMEVAL-1": bad("decision receipt: protocol_id")
if not r.get("operator") or not r.get("applied_at"): bad("decision receipt: operator / applied_at")
if r.get("patch", {}).get("sha256") != patch_sha: bad("decision receipt: patch sha256")
if r.get("staged_text", {}).get("annex", {}).get("sha256") != annex_sha: bad("decision receipt: staged annex sha256")
st = r.get("state", {})
if st.get("MEASUREMENT.md") != {"sha256_before": mpre, "sha256_after": mpost}: bad("decision receipt: MEASUREMENT.md hashes")
if st.get("measurement/protocols/quality-eval.md") != {"sha256_before": qpre, "sha256_after": qpost}: bad("decision receipt: quality-eval.md hashes")
if i.get("gate_id") != gate or i.get("status") != "ratified" or not str(i.get("receipt", "")).endswith(receipt_rel):
    bad("keyed index does not point at the decision receipt as ratified")
if c.get("verdict") != "RATIFIED" or c.get("protocol_id") != "P-MEMEVAL-1" or c.get("ratification_id") != gate:
    bad(f"consolidated receipt: verdict={c.get('verdict')!r} protocol_id={c.get('protocol_id')!r}")
if ok: print("  ok    decision receipt, keyed index and section-5 consolidated receipt agree with the pins")
sys.exit(0 if ok else 1)
PYEOF
  fi
  dirty="$(git -C "$ROOT" status --porcelain -- "${COMMIT_PATHS[@]}" 2>/dev/null || echo 'GIT-STATUS-FAILED')"
  if [ -n "$dirty" ]; then printf '  FAIL  %-48s\n%s\n' "commit paths committed and clean at HEAD" "$dirty"; vf=1
  else printf '  ok    %-48s (%s)\n' "commit paths committed and clean at HEAD" "$(git -C "$ROOT" rev-parse --short HEAD)"; fi
  if [ "$vf" -ne 0 ]; then
    say "VERIFY FAILED: P-MEMEVAL-1 is not (fully) ratified in $ROOT."
    exit 1
  fi
  say "VERIFIED: P-MEMEVAL-1 is ratified, receipted and committed in $ROOT."
  exit 0
fi

# ---------------------------------------------------------------- idempotence / partial states
if [ "$meas_post" -eq 1 ] && [ "$k_post" -eq 1 ]; then
  if [ -f "$RECEIPT" ] && [ -f "$INDEX" ]; then
    say "ALREADY RATIFIED: both targets are at their post-state pins and $RECEIPT_REL and $INDEX_REL exist. Nothing to do."
    say "Check it with: ROOT=$ROOT bash $SRC_SCRIPT --verify"
    exit 0
  fi
  die "half-applied state: both targets are amended, but the receipt ($([ -f "$RECEIPT" ] && echo present || echo MISSING)) or the keyed index ($([ -f "$INDEX" ] && echo present || echo MISSING)) is not. Resolve by hand."
fi
if [ "$meas_post" -ne "$k_post" ]; then
  die "half-applied state: MEASUREMENT.md post=$meas_post, quality-eval.md post=$k_post. Resolve by hand."
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
pin "quality-eval.md pre-state hash" "$K_PRE_SHA256" "$k_now"

if grep -qF 'P-MEMEVAL-1' "$ROOT/$MEAS_REL" "$ROOT/$K_REL"; then
  printf '  FAIL  %-48s\n' "P-MEMEVAL-1 not yet in either target"; fail=1
else
  printf '  ok    %-48s\n' "P-MEMEVAL-1 not yet in either target"
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
  die "preflight failed: $ROOT is not in the state this bundle was prepared against (epyc-root origin/main 23e33d5ca). Stale checkout: fast-forward it first. Moved target: regenerate the bundle. Nothing written."
fi
say "  preflight clean"

if [ "$MODE" = "review" ]; then
  say ""
  say "== amendment diff (${PATCH_REL}) =="
  cat "$PATCH"
  say ""
  say "REVIEW ONLY: would apply the diff above to ${TARGETS[*]} (post-state pins ${MEAS_POST_SHA256:0:12} / ${K_POST_SHA256:0:12}),"
  say "write $RECEIPT_REL, $INDEX_REL and $CONSOLIDATED_REL, and commit those five paths. Nothing written."
  say "Apply with: RATIFY_OPERATOR=<your-name> ROOT=$ROOT bash $SRC_SCRIPT --apply"
  exit 0
fi

# ---------------------------------------------------------------- apply
APPLIED_AT="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
OPERATOR="$RATIFY_OPERATOR"
TMPD="$(mktemp -d)"
trap 'rm -rf "$TMPD" "$K_VIEW_TMP"' EXIT
cp "$ROOT/$MEAS_REL" "$TMPD/MEASUREMENT.md.bak"
cp "$ROOT/$K_REL"    "$TMPD/quality-eval.md.bak"
PRE="$TMPD/pre.json"
restore() {
  cp "$TMPD/MEASUREMENT.md.bak" "$ROOT/$MEAS_REL"
  cp "$TMPD/quality-eval.md.bak" "$ROOT/$K_REL"
  rm -f "$RECEIPT" "$INDEX" "$ROOT/$PATCH_REL" "$ROOT/$STAGED_ANNEX_REL" "$ROOT/$STAGED_SNIPPET_REL" "$ROOT/$SCRIPT_REL"
}

say ""
say "== apply =="
python3 "$ROOT"/scripts/operator/ratification_receipt.py capture --repo-root "$ROOT" \
  --state "$MEAS_REL" --state "$K_REL" --out "$PRE" \
  || die "could not snapshot the pre-amendment state; nothing written"

mkdir -p "$ROOT/artifacts/operator/staged" "$ROOT/scripts/operator"
cp "$PATCH" "$ROOT/$PATCH_REL"; cp "$SRC_ANNEX" "$ROOT/$STAGED_ANNEX_REL"; cp "$SRC_SNIPPET" "$ROOT/$STAGED_SNIPPET_REL"; cp "$SRC_SCRIPT" "$ROOT/$SCRIPT_REL"
# Working tree only, never --index: staging happens below, into a private index, after postflight.
git -C "$ROOT" apply "$PATCH" || { restore; die "git apply failed; targets restored. Nothing changed."; }

# ---------------------------------------------------------------- postflight
say ""
say "== postflight =="
pf=0
pin_pf() { if [ "$2" != "$3" ]; then printf '  FAIL  %-48s expected %s found %s\n' "$1" "$2" "$3"; pf=1
           else printf '  ok    %-48s (%s)\n' "$1" "${3:0:12}"; fi; }
pin_pf "MEASUREMENT.md post-state hash" "$MEAS_POST_SHA256" "$(sha "$ROOT/$MEAS_REL")"
pin_pf "quality-eval.md post-state hash" "$K_POST_SHA256" "$(sha "$ROOT/$K_REL")"
check_landed "$ROOT/$MEAS_REL" "$ROOT/$K_REL" "$TMPD/quality-eval.md.bak" || pf=1
# Append-or-version: not one ratified line may be removed or rewritten.
if python3 - "$TMPD/quality-eval.md.bak" "$ROOT/$K_REL" "$TMPD/MEASUREMENT.md.bak" "$ROOT/$MEAS_REL" <<'PYEOF'
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
  --protocol-id P-MEMEVAL-1 \
  --protocol-new \
  --anchor "$CHANGELOG_ANCHOR" \
  --anchor "$REGISTRY_ANCHOR" \
  --ratification-id "$GATE_ID" \
  --script "$SCRIPT_PATH" \
  --operator "$OPERATOR" \
  --no-evidence-reason "instrument admission, not a measured claim: no measurement is taken or re-verdicted under P-MEMEVAL-1 by this amendment; it fixes the arm, scorer, judge and admission rules the M-12 handoff (memory-program.md M-12/M-12a/M-12b/M-12c) and the 2026-09-16 OP-42 readiness package already specify, and changes no threshold, gate or code; operator decision OP-42, 2026-11-26" \
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
  "decision": "CREATE-PROTOCOL-P-MEMEVAL-1",
  "gate_id": gate,
  "operator_decision": "OP-42 decided 2026-11-26 (master-handoff-index 23e33d5ca): admit BEAM 128K and Tulving 200ch/100K as M-12's instruments (+ one inference window, granted separately, not by this receipt)",
  "ratified_at": applied_at,
  "applied_at": applied_at,
  "operator": operator,
  "status": "ratified",
  "protocol_id": "P-MEMEVAL-1",
  "annex": "Q",
  "annex_path": "measurement/protocols/quality-eval.md",
  "amendment_class": "new protocol (append to the owning annex; no new annex)",
  "registry_status": "✅ 2026-11-26",
  "protocol_summary": {
    "instrument_T": "Tulving 200ch/100K, Udefault_Sdefault_seed0, 686 q/arm, arms none/retrieved/full, deterministic score_tulving_run, headline five-bin Simple Recall incl. bin 0",
    "instrument_B": "BEAM 128K (100K split), 400 q/arm, arms full/rag/trace, nugget judge != reader fixed across arms, BEAM fold, abstention excluded, admit_beam_runs.py + 8-item checklist gate",
    "common": "prompt-matched arms, reader pinned by recipe_hash, no truncation rule (>=196608 ctx/slot), one result dir per arm, belief sidecar per arm",
  },
  "provenance": "memory-program.md M-12; progress/2026-09/2026-09-16-sub-op42-readiness.md; bundle prepared by an agent (opsign-20261126) from the P-SERVE-1 ratifier",
  "not_granted": "no compute window, measurement, threshold, routing, promotion, eval-pool registration or re-verdict of the 2026-09-18 M-12a runs",
  "patch": {"path": patch_rel, "sha256": patch_sha},
  "staged_text": {
    "annex": {"path": annex_rel, "sha256": annex_sha},
    "measurement_md_snippets": {"path": snip_rel, "sha256": snip_sha},
  },
  "state": {
    "MEASUREMENT.md": {"sha256_before": meas_pre, "sha256_after": meas_post},
    "measurement/protocols/quality-eval.md": {"sha256_before": k_pre, "sha256_after": k_post},
  },
  "tracking": {"operator_queue": "OP-42", "handoff": "handoffs/active/memory-program.md M-12"},
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
  say "Then: ROOT=$ROOT bash $SRC_SCRIPT --verify"
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

OP-42 (operator decision 2026-11-26): P-MEMEVAL-1 is applied here by the
operator through $SCRIPT_REL. All pins were verified and the section-5
consolidated receipt returned RATIFIED.

Annex Q (measurement/protocols/quality-eval.md) gains P-MEMEVAL-1: Tulving
200ch/100K (instrument T, deterministic scorer, bin 0 in the headline) and
BEAM 128K (instrument B, nugget judge != reader, abstention excluded,
admit_beam_runs.py gate) as the M-12 memory-on vs memory-off instruments.
MEASUREMENT.md gains the section-2 registry row (2026-11-26, Q) and a
CHANGELOG entry. Additions only. No compute window is granted here.

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
  die "a staged target does not match its post-state pin (MEASUREMENT.md ${staged_meas:0:12}, quality-eval.md ${staged_k:0:12}): something edited it after postflight. NOT committed; the amendment and receipts are applied in the working tree. Inspect: git -C $ROOT diff -- ${TARGETS[*]}"
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
say "    ROOT=$ROOT bash $SRC_SCRIPT --verify"
if [ "$BRANCH" = "main" ]; then
  say "    python3 $ROOT/scripts/coordination/serialized_push.py --agent operator --repo $ROOT --fetch --push"
else
  say "    git -C $ROOT push origin $BRANCH     # then land $BRANCH on main"
fi
say ""
say "Then the memory-program owner records OP-42 as applied in memory-program.md M-12 and books the one window (M-12a first, M-12b second)."
