#!/bin/bash
# ratify_op60_measurement_epoch_20260926.sh — P-AK-SEARCH-1-A3.1: the A3 epoch is the MEASUREMENT
# epoch. Planner-history comparability and the do-not-repeat gate stop keying on actor configuration.
#
#   Review (default, writes nothing):   bash scripts/operator/ratify_op60_measurement_epoch_20260926.sh
#   Apply + receipts + commit (ONE):    bash scripts/operator/ratify_op60_measurement_epoch_20260926.sh --apply
#   Apply + receipts, no commit:        bash scripts/operator/ratify_op60_measurement_epoch_20260926.sh --apply --no-commit
#
# OPERATOR DECISION OP-60 (2026-09-26, given in session): switch AutoKernel planner-history
# comparability AND the do-not-repeat gate from the full epoch to the measurement epoch.
# Tracked as OP-60 in handoffs/active/master-handoff-index.md and DS41-C40 in
# handoffs/active/deepseek-v41-flash-evaluation.md.
#
# WHAT IS BEING CLARIFIED. Ratified P-AK-SEARCH-1-A3 Clause 1 (measurement/protocols/kernel-research.md)
# says: "An epoch is the SHA-256 of the anchor commit, the build recipe, and the declared host state,
# taken together." It never names actor configuration. The implementation folded the campaign's
# actor roster into host_state anyway, via `enrolled_manifest_digest` (the digest of the whole
# resolved manifest, including its `actors` and `fallbacks` blocks). So every change to WHO plans,
# authors or critiques moved the epoch. In the week ending 2026-09-26 there were four such changes;
# one critic swap moved the full epoch e0aefe6a -> e384c2ad with anchor, target, recipe, instrument,
# requests and floor unchanged. Each change hid prior same-anchor results from the planner and let
# the do-not-repeat gate re-admit mechanisms that had already been measured.
#
# A measured speed or correctness result does not depend on which actor authored the patch. The
# measurement epoch is the same inputs minus actor configuration:
#   ResolvedCampaign.measurement_digest / measurement_epoch, epyc-inference-research main d643d794
#   (scripts/kernel_rnd/autokernel/loop/campaign.py, loop/run.py). Resume checkpoints already bind
#   on it (research 3cbdccea, lane ak-author-medium).
#
# AMENDMENT OR CLARIFICATION? Both readings are recorded in the annex text. By the TEXT, actor config
# was never "host state", so this is a clarification. By the IMPLEMENTATION, every A3 epoch recorded
# so far includes the actor roster, so the recorded epoch changes. The operator's ruling takes the
# first reading. The annex states the change in recorded epochs, so nothing depends on the label.
#
# WHAT THE AMENDMENT DOES (artifacts/operator/ak-search-1-a3-1-measurement-epoch-20260926.patch)
# Additions only, 0 lines removed. Append-or-version per MEASUREMENT.md section 5.
#   measurement/protocols/kernel-research.md
#     - a CLARIFIED 2026-09-26 line under the P-AK-SEARCH-1 header, beside the A1/A2/A3 lines
#     - a pointer paragraph directly under A3 Clause 1's epoch sentence (which stays verbatim)
#     - a new appended section P-AK-SEARCH-1-A3.1, with:
#         1a  measurement epoch = anchor + recipe + declared host state, EXCLUDING actor config
#             (planner/author/critic models and backends, efforts, thinking, limits, prompt knobs,
#             the manifest's actors/fallbacks roster and any digest that folds it in)
#         1b  planner-history comparability AND the do-not-repeat gate key on it
#         1c  legacy rows with no measurement identity FAIL CLOSED to the full-epoch comparison
#         both readings (text vs implementation), the rationale, and what does NOT change
#         (the full epoch stays the provenance key; every A3/P-AK-SEARCH-1 denial stands)
#   MEASUREMENT.md
#     - one 2026-09-26 CHANGELOG entry (required by section 5)
#
# WHAT IT DOES NOT DO. It grants no banking, composition, readiness, promotion or retro-
# certification. It changes no code, no threshold and no other protocol. It does not touch
# coordination/session-bus/human_only_paths.yaml, so that file's .sha256 pin needs no update.
# Nothing here starts a process, takes compute, or touches the network beyond one `git fetch` of
# the research repo to verify that the cited implementation is merged.
#
# WHY IT NEEDS YOU. MEASUREMENT.md and measurement/protocols/*.md are human-amendment-only
# (coordination/session-bus/human_only_paths.yaml; invariant 15). An agent prepared this bundle.
# Only the operator applies it.
#
# PINS. Any mismatch is refused. If a target has moved, REGENERATE the bundle; never force or fuzz.
#   patch                                   0282cf4e747893d3561ffe0fa748305350b138faad72feac347b03b4389a588e
#   MEASUREMENT.md             pre-state    62a4e72e3e8508fecbf917d938d3577f0c6abe3da4c1fd47b50d31828093dd60
#   MEASUREMENT.md             post-state   abfd4f2c8a7dc70a6586a0090b1d233e1b87f18bc62bf5cf0d043abfa859409a
#   protocols/kernel-research  pre-state    be876a76e9b0f6edb1ef81ac489083e172270429cf7e986b933171ea54e39316
#   protocols/kernel-research  post-state   6d3ecd9451578c7dab1af07dd0e192e2cb69eb3ed7a971abad4cdb0ec0d36a54
# The pre-state pins match epyc-root origin/main 9c4933d7. A stale checkout is refused:
# fast-forward it first.
#
# COMMIT. --apply commits exactly the five paths below on ROOT's current branch, through a private
# index seeded from HEAD, after re-hashing the staged targets against the post-state pins. Nothing a
# peer has staged in a shared index rides along. Preflight also proves all five paths clean first.
# Pushing is left to you (root: scripts/coordination/serialized_push.py); the command is printed.
#
# IDEMPOTENT. When both targets sit at their post-state pins and the decision receipt and keyed index
# exist, a re-run prints ALREADY RATIFIED and exits 0 without writing. Every other partial state is
# refused and left for resolution by hand.
#
# ROOT defaults to the checkout this script lives in. Override it with ROOT=<epyc-root checkout>.
set -euo pipefail

SCRIPT_PATH="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/$(basename "${BASH_SOURCE[0]}")"
ROOT="${ROOT:-$(cd "$(dirname "$SCRIPT_PATH")/../.." && pwd)}"
SCRIPT_REL="scripts/operator/ratify_op60_measurement_epoch_20260926.sh"

PATCH_REL="artifacts/operator/ak-search-1-a3-1-measurement-epoch-20260926.patch"
PATCH="$ROOT/$PATCH_REL"
MEAS_REL="MEASUREMENT.md"
KR_REL="measurement/protocols/kernel-research.md"
TARGETS=("$MEAS_REL" "$KR_REL")
GATE_ID="RATIFY-OP60-MEASUREMENT-EPOCH-20260926"
RECEIPT_REL="artifacts/operator/ratify_op60_measurement_epoch_20260926.json"
INDEX_REL="artifacts/operator/receipts/$GATE_ID.json"
# Beside the decision receipt, not in receipts/: that directory is the keyed-index namespace, and
# check_ratifier_receipt_contract.sh reports a non-pointer file there as UNRESOLVED-TARGET.
CONSOLIDATED_REL="artifacts/operator/ratify_op60_measurement_epoch_20260926.receipt.json"
RECEIPT="$ROOT/$RECEIPT_REL"
INDEX="$ROOT/$INDEX_REL"
CONSOLIDATED="$ROOT/$CONSOLIDATED_REL"
COMMIT_PATHS=("$MEAS_REL" "$KR_REL" "$RECEIPT_REL" "$INDEX_REL" "$CONSOLIDATED_REL")
COMMIT_MSG="RATIFIED: P-AK-SEARCH-1-A3.1 — the A3 epoch is the measurement epoch; planner history and do-not-repeat stop keying on actor config (OP-60, 2026-09-26)"

PATCH_SHA256="0282cf4e747893d3561ffe0fa748305350b138faad72feac347b03b4389a588e"
MEAS_PRE_SHA256="62a4e72e3e8508fecbf917d938d3577f0c6abe3da4c1fd47b50d31828093dd60"
MEAS_POST_SHA256="abfd4f2c8a7dc70a6586a0090b1d233e1b87f18bc62bf5cf0d043abfa859409a"
KR_PRE_SHA256="be876a76e9b0f6edb1ef81ac489083e172270429cf7e986b933171ea54e39316"
KR_POST_SHA256="6d3ecd9451578c7dab1af07dd0e192e2cb69eb3ed7a971abad4cdb0ec0d36a54"

RESEARCH="${RESEARCH:-/mnt/raid0/llm/epyc-inference-research}"
# d643d794: measurement_digest / measurement_epoch (the implementation this clause names).
# 3cbdccea: resume and pending views already bind on the measurement epoch.
RESEARCH_COMMITS=(d643d794 3cbdccea)

MODE="dry-run"; DO_COMMIT=1
for arg in "$@"; do
  case "$arg" in
    --dry-run)   MODE="dry-run" ;;
    --apply)     MODE="apply" ;;
    --no-commit) DO_COMMIT=0 ;;
    *) echo "usage: $0 [--dry-run | --apply [--no-commit]]   (default: --dry-run, writes nothing)" >&2; exit 64 ;;
  esac
done

say() { printf '%s\n' "$*"; }
die() { printf 'REFUSING: %s\n' "$*" >&2; exit 65; }
sha() { sha256sum "$1" | awk '{print $1}'; }

command -v python3   >/dev/null || die "python3 not on PATH"
command -v sha256sum >/dev/null || die "sha256sum not on PATH"
command -v git       >/dev/null || die "git not on PATH"
for t in "${TARGETS[@]}"; do [ -f "$ROOT/$t" ] || die "$t not found under ROOT=$ROOT"; done
[ -f "$ROOT/scripts/operator/ratification_receipt.py" ] \
  || die "section-5 receipt tool missing at $ROOT/scripts/operator/ratification_receipt.py"

# ---------------------------------------------------------------- patch pin
[ -f "$PATCH" ] || die "patch not found at $PATCH"
got="$(sha "$PATCH")"
[ "$got" = "$PATCH_SHA256" ] || die "patch hash mismatch: expected $PATCH_SHA256, found $got. The text you reviewed is not the text that would be applied."

# ---------------------------------------------------------------- idempotence / partial states
meas_now="$(sha "$ROOT/$MEAS_REL")"
kr_now="$(sha "$ROOT/$KR_REL")"
meas_post=0; [ "$meas_now" = "$MEAS_POST_SHA256" ] && meas_post=1
kr_post=0;   [ "$kr_now"   = "$KR_POST_SHA256"   ] && kr_post=1
if [ "$meas_post" -eq 1 ] && [ "$kr_post" -eq 1 ]; then
  if [ -f "$RECEIPT" ] && [ -f "$INDEX" ]; then
    say "ALREADY RATIFIED: both targets are at their post-state pins and $RECEIPT_REL and $INDEX_REL exist. Nothing to do."
    exit 0
  fi
  die "half-applied state: both targets are amended, but the receipt ($([ -f "$RECEIPT" ] && echo present || echo MISSING)) or the keyed index ($([ -f "$INDEX" ] && echo present || echo MISSING)) is not. Resolve by hand."
fi
if [ "$meas_post" -ne "$kr_post" ]; then
  die "half-applied state: MEASUREMENT.md post=$meas_post, kernel-research.md post=$kr_post. Resolve by hand."
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
pin "MEASUREMENT.md pre-state hash" "$MEAS_PRE_SHA256" "$meas_now"
pin "kernel-research.md pre-state hash" "$KR_PRE_SHA256" "$kr_now"

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

# The implementation the clause names must be MERGED, not merely present in the object store.
# Fetch first, so origin/main is current rather than whatever this clone last saw.
if git -C "$RESEARCH" fetch -q origin 2>/dev/null; then
  printf '  ok    %-48s\n' "research fetch origin"
  for c in "${RESEARCH_COMMITS[@]}"; do
    if git -C "$RESEARCH" merge-base --is-ancestor "$c" origin/main 2>/dev/null; then
      printf '  ok    %-48s\n' "research $c merged in origin/main"
    else
      printf '  FAIL  %-48s\n' "research $c merged in origin/main"; fail=1
    fi
  done
else
  printf '  FAIL  %-48s\n' "research fetch origin"
  printf '        cannot fetch %s; implementation merge status is unverifiable (network or auth?)\n' "$RESEARCH"
  fail=1
fi

if [ "$fail" -ne 0 ]; then
  die "preflight failed: $ROOT is not in the state this bundle was prepared against (epyc-root origin/main 9c4933d7). Stale checkout: fast-forward it first. Moved target: regenerate the bundle. Nothing written."
fi
say "  preflight clean"

if [ "$MODE" = "dry-run" ]; then
  say ""
  say "== amendment diff (${PATCH_REL}) =="
  cat "$PATCH"
  say ""
  say "DRY RUN: would apply the diff above to ${TARGETS[*]} (post-state pins ${MEAS_POST_SHA256:0:12} / ${KR_POST_SHA256:0:12}),"
  say "write $RECEIPT_REL, $INDEX_REL and $CONSOLIDATED_REL, and commit those five paths. Nothing written."
  say "Apply with: ROOT=$ROOT bash $SCRIPT_PATH --apply"
  exit 0
fi

# ---------------------------------------------------------------- apply
RATIFIED_AT="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
TMPD="$(mktemp -d)"
trap 'rm -rf "$TMPD"' EXIT
cp "$ROOT/$MEAS_REL" "$TMPD/MEASUREMENT.md.bak"
cp "$ROOT/$KR_REL"   "$TMPD/kernel-research.md.bak"
PRE="$TMPD/pre.json"
restore() {
  cp "$TMPD/MEASUREMENT.md.bak" "$ROOT/$MEAS_REL"
  cp "$TMPD/kernel-research.md.bak" "$ROOT/$KR_REL"
  rm -f "$RECEIPT" "$INDEX"
}

say ""
say "== apply =="
python3 "$ROOT/scripts/operator/ratification_receipt.py" capture --repo-root "$ROOT" \
  --state "$MEAS_REL" --state "$KR_REL" --out "$PRE" \
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
pin_pf "kernel-research.md post-state hash" "$KR_POST_SHA256" "$(sha "$ROOT/$KR_REL")"
# Append-or-version: not one ratified line may be removed or rewritten, and A3 Clause 1's epoch
# sentence must survive verbatim beside its clarification.
if python3 - "$TMPD/kernel-research.md.bak" "$ROOT/$KR_REL" "$TMPD/MEASUREMENT.md.bak" "$ROOT/$MEAS_REL" <<'PYEOF'
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
kr = open(sys.argv[2], encoding="utf-8").read()
for needle in ("attempt. An epoch is the SHA-256 of the anchor commit, the build recipe, and the declared host\nstate, taken together.",
               "## P-AK-SEARCH-1-A3 — epoch-scoped memory across campaigns (RATIFIED 2026-08-31)",
               "## P-AK-SEARCH-1-A3.1 — the A3 epoch is the measurement epoch (RATIFIED 2026-09-26)",
               "### Clause 1c — legacy rows fail closed"):
    if kr.count(needle) != 1:
        print(f"  FAIL  expected exactly one occurrence of: {needle[:80]!r}"); ok = False
if ok:
    print("  ok    additions only; A3 Clause 1 preserved verbatim; A3.1 present once")
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
python3 "$ROOT/scripts/operator/ratification_receipt.py" emit \
  --repo-root "$ROOT" \
  --pre "$PRE" \
  --protocol-id P-AK-SEARCH-1 \
  --anchor '- **2026-09-26 (v2.x)** — CLARIFICATION (Annex K, `P-AK-SEARCH-1-A3.1`): the epoch in A3 Clause 1 is' \
  --ratification-id "$GATE_ID" \
  --script "$SCRIPT_PATH" \
  --no-evidence-reason "definitional clarification of an epoch identity, not a measured claim; the implementation it names is code at epyc-inference-research d643d794 and 3cbdccea, verified merged in origin/main by this script's preflight; the observed epoch movement (e0aefe6a -> e384c2ad on one critic swap) is recorded in handoffs/active/deepseek-v41-flash-evaluation.md DS41-C40" \
  --validation "bash scripts/validate/check_claims_grammar.sh --files $KR_REL" \
  --out "$CONSOLIDATED" || receipt_rc=$?
if [ "$receipt_rc" -ne 0 ]; then
  refused="${CONSOLIDATED%.receipt.json}.refused-$(date -u +%Y%m%dT%H%M%SZ).receipt.json"
  [ -f "$CONSOLIDATED" ] && mv "$CONSOLIDATED" "$refused"
  restore
  die "consolidated receipt returned $receipt_rc (1 REFUSED, 2 COULD-NOT-CHECK). Amendment rolled back; the receipt is kept at ${refused#"$ROOT"/} for reading."
fi

# ---------------------------------------------------------------- decision receipt + keyed index
if ! python3 - "$RECEIPT" "$INDEX" "$RATIFIED_AT" "$GATE_ID" "$CONSOLIDATED_REL" "$RECEIPT_REL" \
     "${RATIFY_OPERATOR:-${USER:-unknown}}" "$PATCH_SHA256" "$PATCH_REL" "$SCRIPT_REL" \
     "$MEAS_PRE_SHA256" "$MEAS_POST_SHA256" "$KR_PRE_SHA256" "$KR_POST_SHA256" <<'PYEOF'
import sys, json, os
(receipt, index, ts, gate, consolidated_rel, receipt_rel, operator, patch_sha, patch_rel,
 script_rel, meas_pre, meas_post, kr_pre, kr_post) = sys.argv[1:15]
doc = {
  "schema": "epyc.measurement.protocol_amendment.v1",
  "decision": "AK-SEARCH-1-A3-EPOCH-IS-MEASUREMENT-EPOCH",
  "gate_id": gate,
  "operator_decision": "OP-60 (2026-09-26, given in session): switch planner-history comparability and the do-not-repeat gate from the full epoch to the measurement epoch",
  "ratified_at": ts,
  "operator": operator,
  "status": "ratified",
  "protocol_id": "P-AK-SEARCH-1",
  "clause": "P-AK-SEARCH-1-A3 Clause 1 (epoch definition), clarified by new section P-AK-SEARCH-1-A3.1",
  "annex": "K",
  "amendment_class": "clarification",
  "readings": {
    "text": "A3 Clause 1 defines the epoch as anchor commit + build recipe + declared host state and never names actor configuration; on this reading the implementation over-reached and A3.1 is a clarification (the operator's ruling).",
    "implementation": "research folded the actor roster into host_state via enrolled_manifest_digest (manifest incl. actors/fallbacks) from the day A3 shipped, so every recorded A3 epoch includes it; on this reading A3.1 changes the recorded epoch.",
  },
  "measurement_epoch": {
    "includes": ["anchor commit", "build recipe",
                 "declared host state: CPU/GPU execution digests, frozen request set, enrolled target, manifest measured content (manifest minus actors/fallbacks), CPU screen scope, serving instrument"],
    "excludes": ["planner/author/critic models and backends", "reasoning efforts", "thinking settings",
                 "context and output limits", "prompt knobs",
                 "manifest actors/fallbacks roster and any digest that folds it in (enrolled_manifest_digest, manifest_digest)"],
    "keyed_uses": ["planner-history comparability (A3 Clause 1 ranking; Clause 2 cross-epoch boundary)",
                   "do-not-repeat gate (already-measured-in-epoch)"],
    "legacy_rows": "records without a measurement identity fail closed to the full-epoch comparison; never presumed same-epoch",
    "full_epoch": "still recorded; remains the provenance key for archive rows, history and status",
  },
  "implementation": {
    "repo": "epyc-inference-research",
    "commits": {"d643d794": "ResolvedCampaign.measurement_digest / measurement_epoch (loop/campaign.py, loop/run.py)",
                "3cbdccea": "resume and pending views bind on the measurement epoch (lane ak-author-medium)"},
  },
  "rationale": "a measured speed/correctness result does not depend on which actor authored the patch; under the full epoch every actor change (four in the week ending 2026-09-26) hid prior same-anchor results from the planner and re-admitted already-measured mechanisms; one critic swap moved the full epoch e0aefe6a -> e384c2ad with anchor, target, recipe, instrument, requests and floor unchanged",
  "not_granted": "no banking, composition, readiness contribution, promotion or retro-certification; every P-AK-SEARCH-1 denial and precondition stands",
  "patch": {"path": patch_rel, "sha256": patch_sha},
  "state": {
    "MEASUREMENT.md": {"sha256_before": meas_pre, "sha256_after": meas_post},
    "measurement/protocols/kernel-research.md": {"sha256_before": kr_pre, "sha256_after": kr_post},
  },
  "tracking": {"operator_queue": "handoffs/active/master-handoff-index.md OP-60",
               "handoff_task": "handoffs/active/deepseek-v41-flash-evaluation.md DS41-C40"},
  "consolidated_receipt": consolidated_rel,
  "applied_by": script_rel,
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
  say "    git -C $ROOT commit -m '$COMMIT_MSG'     # only if nothing else is staged in this index"
  exit 0
fi

# ---------------------------------------------------------------- commit (private index)
say ""
say "== commit on $BRANCH =="
# A PRIVATE index seeded from HEAD, holding only these five paths. Two shared-clone hazards are
# closed at once: nothing a peer has staged in the shared index rides along (a bare `git commit`
# would take it), and no pathspec commit re-reads the working tree (which would take a peer's hunk
# in the same file). Before committing, the staged blobs of both targets are re-hashed against the
# post-state pins, so an edit landing between postflight and staging is refused, not committed.
PIDX="$TMPD/private.index"
commit_manual="git -C $ROOT add -- ${COMMIT_PATHS[*]} && git -C $ROOT commit -m '$COMMIT_MSG'"
GIT_INDEX_FILE="$PIDX" git -C "$ROOT" read-tree HEAD \
  || die "could not seed a private index from HEAD. The amendment and receipts ARE applied (not rolled back). Commit by hand: $commit_manual"
GIT_INDEX_FILE="$PIDX" git -C "$ROOT" add -- "${COMMIT_PATHS[@]}" \
  || die "could not stage into the private index. The amendment and receipts ARE applied (not rolled back). Commit by hand: $commit_manual"
staged_meas="$(GIT_INDEX_FILE="$PIDX" git -C "$ROOT" show ":$MEAS_REL" | sha256sum | awk '{print $1}')"
staged_kr="$(GIT_INDEX_FILE="$PIDX" git -C "$ROOT" show ":$KR_REL" | sha256sum | awk '{print $1}')"
if [ "$staged_meas" != "$MEAS_POST_SHA256" ] || [ "$staged_kr" != "$KR_POST_SHA256" ]; then
  die "a staged target does not match its post-state pin (MEASUREMENT.md ${staged_meas:0:12}, kernel-research.md ${staged_kr:0:12}): something edited it after postflight. NOT committed; the amendment and receipts are applied in the working tree. Inspect: git -C $ROOT diff -- ${TARGETS[*]}"
fi
staged_list="$(GIT_INDEX_FILE="$PIDX" git -C "$ROOT" diff --cached --name-only HEAD | sort)"
expected_list="$(printf '%s\n' "${COMMIT_PATHS[@]}" | sort)"
[ "$staged_list" = "$expected_list" ] \
  || die "the private index holds an unexpected path set; NOT committed. Staged: $(echo $staged_list)"
if GIT_INDEX_FILE="$PIDX" git -C "$ROOT" commit -q -m "$COMMIT_MSG"; then
  # Bring the checkout's own index up to the new HEAD for OUR five paths only, so they do not show
  # as staged reversals. Other paths in a shared index are left exactly as they were.
  git -C "$ROOT" reset -q -- "${COMMIT_PATHS[@]}" \
    || say "  WARNING: 'git reset -q -- <five paths>' failed; run it by hand so the index matches HEAD."
  sha_c="$(git -C "$ROOT" rev-parse --short HEAD)"
  say "  committed $sha_c on $BRANCH:"
  git -C "$ROOT" show --stat --format='  %s' HEAD | sed 's/^/  /'
else
  die "the commit failed. The amendment and receipts ARE applied in the working tree (not rolled back). Commit by hand: $commit_manual"
fi

say ""
say "RATIFIED and committed. Not pushed. Publish:"
if [ "$BRANCH" = "main" ]; then
  say "    python3 $ROOT/scripts/coordination/serialized_push.py --agent operator --repo $ROOT --fetch --push"
else
  say "    git -C $ROOT push origin $BRANCH     # then land $BRANCH on main (it carries the script, the patch and this commit)"
fi
say ""
say "Then: delete the OP-60 row from handoffs/active/master-handoff-index.md, and the owning session"
say "ticks DS41-C40 in handoffs/active/deepseek-v41-flash-evaluation.md and switches planner history and"
say "the do-not-repeat gate to the measurement epoch in the research repo."
