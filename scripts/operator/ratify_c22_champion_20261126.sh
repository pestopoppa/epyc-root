#!/bin/bash
# ratify_c22_champion_20261126.sh -- ONE operator signature: accept C22 as the AutoKernel CHAMPION.
#
# WHAT YOU ARE SIGNING: C22 (llama.cpp-experimental-c22-composite-20261125 @ b1e1864cb) is the AutoKernel
# champion. This is NOT a production promotion. It promotes nothing, changes no production kernel, kernel
# store symlink or serving process, and does not write the model registry. Production stays
# production-consolidated-v10 (ffc1bac82). Promotion to production is a separate kernel-promotion run.
#
# Package (read it first):
#   /mnt/raid0/llm/tmp/ak-c22-composite-build-20261125/RATIFY-C22-PACKAGE.md
#   /mnt/raid0/llm/tmp/ak-c22-composite-build-20261125/RATIFY-C22-TEMPLATE.json
#
#   Review / dry run (default; writes nothing, pushes nothing):
#     bash /mnt/raid0/llm/epyc-root/scripts/operator/ratify_c22_champion_20261126.sh
#   Sign (the OPERATOR runs this):
#     bash /mnt/raid0/llm/epyc-root/scripts/operator/ratify_c22_champion_20261126.sh --attest --operator '<your name>'
#
# --attest re-runs every check below, then on a scratch worktree at a FRESH epyc-root origin/main writes
#   artifacts/operator/ratify_c22_champion_20261126.json          (signed copy of the template)
#   artifacts/operator/receipts/RATIFY-C22-CHAMPION-20261126.json (keyed index, C39 contract)
# in ONE commit, and pushes it as a fast-forward of origin/main under serialized_push.py's push lock.
# It refuses if either file already exists (token spent).
#
# Checks (each refuses on mismatch):
#   1. package + template sha256 against the pins below;
#   2. the composite worktree is on the champion branch at b1e1864cb, and the fork branch points at it;
#   3. both ce6fcbbde stores exist, BUILD-IDENTITY.json and SHA256SUMS match their pins, and every file in
#      SHA256SUMS verifies;
#   4. each gate row's RESULT.json exists with the pinned sha256 and a filed verdict.json; the A3B composite
#      row stopped at its interim futility look and has no RESULT.json, so its results.jsonl is pinned;
#   5. the template records the three operator decisions (DEVHANDOFF fold, equal-quality rule, serve
#      without q8wp) as taken.
#
# ROLLBACK: git revert the receipt commit. The previous champion is C21 98ff8a42a; production is unchanged.
set -euo pipefail
export PATH="/usr/bin:/bin:${PATH}"

TOKEN="RATIFY-C22-CHAMPION-20261126"
SCRIPT_PATH="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/$(basename "${BASH_SOURCE[0]}")"
ROOT_REPO="${ROOT_REPO:-/mnt/raid0/llm/epyc-root}"
RECEIPT_REL="artifacts/operator/ratify_c22_champion_20261126.json"
INDEX_REL="artifacts/operator/receipts/$TOKEN.json"
SYS_PY="/usr/bin/python3"
STAGE_PARENT="/mnt/raid0/llm/tmp"
LOCK_AGENT="operator-ratify-c22-champion"

PKG_DIR="/mnt/raid0/llm/tmp/ak-c22-composite-build-20261125"
PKG="$PKG_DIR/RATIFY-C22-PACKAGE.md";       PKG_SHA="bd711894a7cadc8293304efdd6a6ee1f61df6e2479676098d59542ef301e9731"
TPL="$PKG_DIR/RATIFY-C22-TEMPLATE.json";    TPL_SHA="88332d00302fef0358c5fd65c1e4e22e1c1b8bb72b42d335583b407ab58b90e3"

BRANCH="llama.cpp-experimental-c22-composite-20261125"
HEAD_SHA="b1e1864cb6e9f8a012b0be422e6c72ab477ded62"
KWT="/mnt/raid0/llm/llama-worktrees/c22-composite-20261125"

STORES=(  # name build_identity_sha256 sha256sums_sha256
  "gpu-20261126-ce6fcbbde-c22-composite 094423051b8904cce373ed2087391b7de17004c230d85c0e68bf5d8bc0e21cb6 a04da4395f920e844cd78dffb3050b5033048283291ffc472864b58f3ed21e26"
  "cpu-20261126-ce6fcbbde-c22-composite e4cd9b6f6ab7115c02920684c582687f325656a088e6482f33ff73f5d5f023c4 1d2b7df60e9936554802539f166804d9faaa36fe27254cd3098b81ebb0beb74f"
)
STORE_ROOT="/mnt/raid0/llm/kernels/builds"

ROWS=(  # label row_id file sha256  (file relative to /mnt/raid0/llm/tmp/<row_id>/out/)
  "G-27B-r5          ak-c22-composite-gate-27b-gpu-20261126-r5        RESULT.json   4f92f8efeb7d75ef7a72f12e2f09ec81e2d51d3aeb54102c935a231212883829"
  "G-Q38FN           ak-c22-composite-gate-q38fn-cpu-20261126         RESULT.json   284d2dc8b0da877d240dd3b71e86ae23346ad8c891cfb29a6f03fb92e82426aa"
  "draftwin-r2       ak-c22-q38fn-draftwin-confirm-cpu-20261126-r2    RESULT.json   6beea2b17f33f6a733e065e9328a6ac92a8203c65baab974e84938e121e54567"
  "DRAFTVOCAB-q-r3   ak-q38fn-draftvocab-quality-cpu-20261126-r3      RESULT.json   57afd0261a41964beb6d35da0076d23be5244b399cec2e68f398bc32965021e8"
  "A3B-composite     ak-c22-composite-gate-a3b-cpu-20261126           results.jsonl 7a4c62b53235f09017b5d5ed098d8b408817df8b4b9e0abc814eed34ba73a34b"
  "S1-r2             ak-c22-prodcfg-27b-gpu-20261126-r2               RESULT.json   0881f77eac239e786326b18639c7c7d317e0ff398c4408044be66de57d39b1f7"
  "Q-A3B-r1          ak-c22-prodcfg-quality-a3b-cpu-20261126          RESULT.json   7350dd44216bf0adcc4439dec07b7f0c4aa19e16610b452b9ed047b519bcdf69"
)

say() { printf '%s\n' "$*"; }
die() { printf 'REFUSING: %s\n' "$*" >&2; exit 1; }
sha() { sha256sum -- "$1" | awk '{print $1}'; }
g() { git -c safe.directory='*' -C "$@"; }

MODE="review"; OPERATOR=""
while [ $# -gt 0 ]; do
  case "$1" in
    --attest) MODE="attest"; shift;;
    --operator) [ $# -ge 2 ] || die "--operator needs a name"; OPERATOR="$2"; shift 2;;
    -h|--help) sed -n '2,36p' "$SCRIPT_PATH"; exit 0;;
    *) die "unknown argument: $1";;
  esac
done
[ "$MODE" = attest ] || [ -z "$OPERATOR" ] || die "--operator is only meaningful with --attest"

# ---------------------------------------------------------------- 0. signer
if [ "$MODE" = attest ]; then
  [ -n "$OPERATOR" ] || die "--attest requires --operator '<your name>'"
  OPERATOR="$("$SYS_PY" "$ROOT_REPO/scripts/operator/ratification_receipt.py" check-operator "$OPERATOR")" \
    || die "a ratification must carry the name of the human who ran it"
  say "signer: $OPERATOR"
fi

# ---------------------------------------------------------------- 1. package
say "== package =="
for p in "$PKG $PKG_SHA" "$TPL $TPL_SHA"; do
  f="${p% *}"; want="${p##* }"
  [ -f "$f" ] || die "missing $f"
  have="$(sha "$f")"; [ "$have" = "$want" ] || die "$f sha256 $have != pinned $want (package changed after preparation)"
  say "  ok  $f  $have"
done

# ---------------------------------------------------------------- 2. champion branch
say "== champion branch =="
[ -d "$KWT" ] || die "composite worktree $KWT missing"
have_br="$(g "$KWT" rev-parse --abbrev-ref HEAD)"; have_head="$(g "$KWT" rev-parse HEAD)"
[ "$have_br" = "$BRANCH" ] || die "worktree branch is $have_br, expected $BRANCH"
[ "$have_head" = "$HEAD_SHA" ] || die "worktree HEAD is $have_head, expected $HEAD_SHA"
say "  ok  $BRANCH @ $HEAD_SHA (worktree $KWT)"
remote_head="$(g "$KWT" ls-remote fork "refs/heads/$BRANCH" 2>/dev/null | awk '{print $1}' || true)"
if [ -n "$remote_head" ]; then
  [ "$remote_head" = "$HEAD_SHA" ] || die "fork/$BRANCH is $remote_head, expected $HEAD_SHA"
  say "  ok  fork/$BRANCH = $HEAD_SHA"
else
  say "  note: fork remote not reachable from here; local HEAD verified only"
fi

# ---------------------------------------------------------------- 3. stores
say "== kernel stores =="
for s in "${STORES[@]}"; do
  read -r name bid sums <<<"$s"; d="$STORE_ROOT/$name"
  [ -d "$d" ] || die "store $d missing"
  [ "$(sha "$d/BUILD-IDENTITY.json")" = "$bid" ] || die "$name BUILD-IDENTITY.json sha256 mismatch"
  [ "$(sha "$d/SHA256SUMS")" = "$sums" ] || die "$name SHA256SUMS sha256 mismatch"
  (cd "$d" && sha256sum -c --quiet --strict SHA256SUMS) || die "$name: SHA256SUMS does not verify"
  say "  ok  $name  BUILD-IDENTITY $bid  SHA256SUMS $sums ($(wc -l <"$d/SHA256SUMS") files verified)"
done

# ---------------------------------------------------------------- 4. gate rows
say "== gate rows =="
for r in "${ROWS[@]}"; do
  read -r label row file want <<<"$r"; base="$STAGE_PARENT/$row"; f="$base/out/$file"
  [ -f "$f" ] || die "$label: $f missing"
  have="$(sha "$f")"; [ "$have" = "$want" ] || die "$label: $f sha256 $have != pinned $want"
  if [ "$file" = RESULT.json ]; then
    [ -f "$base/verdict.json" ] || die "$label: $row has a RESULT.json but no filed verdict.json"
    v="$("$SYS_PY" -c 'import json,sys; d=json.load(open(sys.argv[1])); print(d.get("verdict") or d.get("decision") or "?")' "$base/verdict.json")"
    say "  ok  $label  $row  RESULT $have  verdict.json: $v"
  else
    [ ! -f "$base/out/RESULT.json" ] || die "$label: unexpected RESULT.json appeared; re-prepare the package"
    say "  ok  $label  $row  futility stop (no RESULT.json by design); results.jsonl $have; verdict in template"
  fi
done

# ---------------------------------------------------------------- 5. template contents + decisions
say "== template and operator decisions =="
"$SYS_PY" - "$TPL" "$HEAD_SHA" "$BRANCH" <<'PY' || die "template contents check failed"
import json, sys
t = json.load(open(sys.argv[1]))
assert t["champion"]["head"] == sys.argv[2] and t["champion"]["branch"] == sys.argv[3], "champion head/branch"
assert t["ratified_at"] is None and t["operator"] is None, "template is already signed"
assert t["preconditions_before_signature"] == [], "open preconditions"
d = t["operator_decisions"]
checks = [("devhandoff_fold", "CONFIRMED"), ("lossy_equal_quality_rule_cpu", "CONFIRMED"),
          ("q8wp_serving", "WITHOUT GGML_HIP_Q8W8")]
for key, needle in checks:
    c = d[key]["choice"]
    assert needle in c, f"{key}: {c!r}"
    print(f"  ok  {key}: {c}  ({d[key]['decided_at']}, {d[key]['channel']})")
PY

if [ "$MODE" = review ]; then
  say ""
  say "DRY RUN -- nothing written, nothing pushed. --attest would write, on fresh origin/main:"
  say "  $RECEIPT_REL"
  say "  $INDEX_REL"
  say "in one commit, pushed under the push lock. It promotes nothing and edits no registry."
  say "  Sign: bash $SCRIPT_PATH --attest --operator '<your name>'"
  say "DRY-RUN OK: $TOKEN -- all preconditions hold."
  exit 0
fi

# ---------------------------------------------------------------- 6. attest
PUSHER="$ROOT_REPO/scripts/coordination/serialized_push.py"
[ -f "$PUSHER" ] || die "$PUSHER missing"
g "$ROOT_REPO" fetch -q origin main || die "cannot fetch epyc-root origin main"
STAGE="$(mktemp -d "$STAGE_PARENT/ratify-c22-champion.XXXXXX")"; WT="$STAGE/root"
cleanup() { g "$ROOT_REPO" worktree remove --force "$WT" >/dev/null 2>&1 || true; rm -rf "$STAGE"; }
trap cleanup EXIT
g "$ROOT_REPO" worktree add -q --detach "$WT" origin/main || die "cannot add a scratch worktree"
[ ! -e "$WT/$INDEX_REL" ] || die "$INDEX_REL already exists on origin/main (token spent)"
[ ! -e "$WT/$RECEIPT_REL" ] || die "$RECEIPT_REL already exists on origin/main (token spent)"
mkdir -p "$WT/artifacts/operator/receipts"

TPL="$TPL" TPL_SHA="$TPL_SHA" PKG="$PKG" PKG_SHA="$PKG_SHA" TOKEN="$TOKEN" OPERATOR="$OPERATOR" \
SCRIPT_SHA="$(sha "$SCRIPT_PATH")" RECEIPT="$WT/$RECEIPT_REL" RECEIPT_REL="$RECEIPT_REL" INDEX="$WT/$INDEX_REL" \
"$SYS_PY" - <<'PY'
import datetime, json, os
e = os.environ
doc = json.load(open(e["TPL"], encoding="utf-8"))
doc["template_gate_id"] = doc.get("gate_id")
doc["gate_id"] = e["TOKEN"]
doc["status"] = "ratified"
doc["operator"] = e["OPERATOR"]
doc["ratified_at"] = datetime.datetime.now(datetime.timezone.utc).isoformat()
doc["signed_by_uid"] = os.getuid()
doc["signature_channel"] = "operator-run script (--attest --operator)"
doc["template_sha256"] = e["TPL_SHA"]
doc["package"] = {"path": e["PKG"], "sha256": e["PKG_SHA"]}
doc["ratify_script_sha256"] = e["SCRIPT_SHA"]
doc["effects"] = "records C22 as AutoKernel champion only; no promotion, no production change, no registry write"
with open(e["RECEIPT"], "x", encoding="utf-8") as fh:
    json.dump(doc, fh, indent=2, sort_keys=True); fh.write("\n"); fh.flush(); os.fsync(fh.fileno())
with open(e["INDEX"], "x", encoding="utf-8") as fh:
    json.dump({"gate_id": e["TOKEN"], "indexed_by": "attest", "receipt": e["RECEIPT_REL"],
               "schema_version": "session_bus.receipt_index.v1", "status": "ratified"},
              fh, indent=2, sort_keys=True)
    fh.write("\n"); fh.flush(); os.fsync(fh.fileno())
PY
g "$WT" add -- "$RECEIPT_REL" "$INDEX_REL"
g "$WT" commit -q -m "RATIFIED $TOKEN: C22 ($HEAD_SHA) is the AutoKernel champion (signed by $OPERATOR)" \
  -m "Champion ratification only: no promotion, production v10 unchanged, registry not written. Receipt $RECEIPT_REL; index $INDEX_REL." \
  || die "commit failed (a pre-commit hook refused it?)"

tokdir="$(mktemp -d "$STAGE/push-token.XXXXXX")"; chmod 700 "$tokdir"; tok="$tokdir/lease.token"; rc=0
"$SYS_PY" "$PUSHER" --agent "$LOCK_AGENT" --repo "$ROOT_REPO" --lock-name push --acquire --token-file "$tok" >/dev/null \
  || die "could not take the push lock"
AGENT_ID="$LOCK_AGENT" EPYC_PUSH_LOCK_HOLDER="$LOCK_AGENT" git -c safe.directory='*' -C "$WT" push origin HEAD:refs/heads/main || rc=$?
"$SYS_PY" "$PUSHER" --agent "$LOCK_AGENT" --repo "$ROOT_REPO" --lock-name push --release --token-file "$tok" >/dev/null \
  || say "WARN: push lock release failed -- check serialized_push.py --status"
[ "$rc" -eq 0 ] || die "git push rejected (rc=$rc; origin/main probably moved). Nothing was signed on origin; re-run."

cat <<EOF

RATIFIED $TOKEN by $OPERATOR.
  commit:  $(g "$WT" rev-parse --short HEAD) on origin/main
  receipt: $RECEIPT_REL
  index:   $INDEX_REL
NOTHING WAS PROMOTED. Production stays production-consolidated-v10; the registry is unchanged.
Promotion to production is a separate kernel-promotion run.
EOF
