#!/bin/bash
# ratify_ak_search_1_a4_runtime_recipe_20260927.sh — P-AK-SEARCH-1-A4: the AutoKernel controller may
# ADOPT a runtime configuration of its own experimental serving launch (OpenMP placement, load-thread
# caps, kernel env switches, threads, CPU list, NUMA policy) under its own strict gates.
#
#   Review (default, writes nothing):   bash scripts/operator/ratify_ak_search_1_a4_runtime_recipe_20260927.sh
#   Apply + receipts + commit (ONE):    bash scripts/operator/ratify_ak_search_1_a4_runtime_recipe_20260927.sh --apply
#   Apply + receipts, no commit:        bash scripts/operator/ratify_ak_search_1_a4_runtime_recipe_20260927.sh --apply --no-commit
#
# OPERATOR DIRECTIVE (2026-09-27, given in session): runtime and recipe knobs like OpenMP placement are
# decided by AutoKernel itself, not escalated to the operator. The DS41 campaign loop must be able to
# A/B runtime-config arms and adopt winners under its own gates. First consumer: DS41-C57
# (/mnt/raid0/llm/tmp/ds41-c57-cpu0-20260927/DS41-C57-findings-and-decision-packages.md, decision
# package A): OMP_PLACES=cores gives 96 places for 48 threads and libgomp sleeps at barriers; any
# 48-place list spins, ~+9.5% median decode tok/s.
#
# WHY AN AMENDMENT. P-AK-SEARCH-1 authorizes ranking/retaining/composing SOURCE candidates against an
# immutable anchor. A2 lets a runtime-parameter SCREEN run, but a screen is non-promotable and nothing
# names a path by which a confirmed runtime nominee becomes the execution recipe; no clause sets a
# numerics rule for a runtime arm that is not bit-exact. A3/A3.1 imply that a recipe change moves the
# epoch but never frame it as the controller adopting one.
#
# WHAT THE AMENDMENT DOES (artifacts/operator/ak-search-1-a4-runtime-recipe-adoption-20260927.patch)
# Additions only, 0 lines removed. Append-or-version per MEASUREMENT.md section 5.
#   measurement/protocols/kernel-research.md
#     - an EXTENDED 2026-09-27 line under the P-AK-SEARCH-1 header, beside the A1/A2/A3/A3.1 lines
#     - a new appended section P-AK-SEARCH-1-A4:
#         Clause 1  sixth authority: adopt one declared runtime field of the full selected launch as the
#                   experimental execution recipe, only after (a) single-field recipe-constructor delta,
#                   (b) strict runtime admission under a PROSPECTIVE statistics declaration (anchor A/A +
#                   neutral calibration, measured control panel, calibrated paired selection + separate
#                   confirmation), (c) unchanged correctness precedence, (d) a durable adoption receipt
#         Clause 2  adoption is a measurement-epoch boundary: the runtime surface enters declared host
#                   state; floors/calibration recompute; a composition compounded under the old recipe
#                   loses its magnitude until re-measured
#         Clause 3  a non-bit-exact runtime arm gets no tolerance of its own: only the evaluator's
#                   existing coherence gate (differing outputs admitted solely vs a bitwise_unstable anchor)
#         what does NOT change: no serving/production/registry/lineup/era effect; denials 1,2,5,6 stand
#   MEASUREMENT.md
#     - one 2026-09-27 CHANGELOG entry (required by section 5)
#
# WHAT IT DOES NOT DO. No production recipe change, no registry/lineup edit, no banking/readiness/
# promotion change, no evaluator or threshold change. It does not touch
# coordination/session-bus/human_only_paths.yaml. Nothing here starts a process or takes compute;
# the only network use is one `git fetch` of the research repo to verify the implementation is merged.
#
# WHY IT NEEDS YOU. MEASUREMENT.md and measurement/protocols/*.md are human-amendment-only
# (coordination/session-bus/human_only_paths.yaml; invariant 15). An agent prepared this bundle on
# lane lane/ak-runtime-arms-a4-20260927. Only the operator applies it.
#
# PINS. Any mismatch is refused. If a target has moved, REGENERATE the bundle; never force or fuzz.
#   patch                                   2ab398c88612067932d1afd20a445e180c7caddfce14faa2b4418209f75fb7dd
#   MEASUREMENT.md             pre-state    73f09cacca8c1dcb8eaed5c57cebec860b0f35a757e3e9efc32827f20fd3cbc4
#   MEASUREMENT.md             post-state   2f90524e6e3d44ffb711a8b495ea0e5574ddf7ab198346e06731c7188b88fd4e
#   protocols/kernel-research  pre-state    6d3ecd9451578c7dab1af07dd0e192e2cb69eb3ed7a971abad4cdb0ec0d36a54
#   protocols/kernel-research  post-state   59dc902c1ad3947be60ecd3fc88becffea9aa38069bd0022d9c078ded3691c6b
# The pre-state pins match epyc-root origin/main e043cfa3.
#
# COMMIT / IDEMPOTENCE: identical to ratify_op60_measurement_epoch_20260926.sh (private index seeded
# from HEAD, exactly five paths, staged blobs re-hashed against the post pins; ALREADY RATIFIED on a
# re-run; every partial state refused).
set -euo pipefail

SCRIPT_PATH="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/$(basename "${BASH_SOURCE[0]}")"
ROOT="${ROOT:-$(cd "$(dirname "$SCRIPT_PATH")/../.." && pwd)}"
SCRIPT_REL="scripts/operator/ratify_ak_search_1_a4_runtime_recipe_20260927.sh"

PATCH_REL="artifacts/operator/ak-search-1-a4-runtime-recipe-adoption-20260927.patch"
PATCH="$ROOT/$PATCH_REL"
MEAS_REL="MEASUREMENT.md"
KR_REL="measurement/protocols/kernel-research.md"
TARGETS=("$MEAS_REL" "$KR_REL")
GATE_ID="RATIFY-AK-SEARCH-1-A4-RUNTIME-RECIPE-20260927"
RECEIPT_REL="artifacts/operator/ratify_ak_search_1_a4_runtime_recipe_20260927.json"
INDEX_REL="artifacts/operator/receipts/$GATE_ID.json"
# Beside the decision receipt, not in receipts/: that directory is the keyed-index namespace, and
# check_ratifier_receipt_contract.sh reports a non-pointer file there as UNRESOLVED-TARGET.
CONSOLIDATED_REL="artifacts/operator/ratify_ak_search_1_a4_runtime_recipe_20260927.receipt.json"
RECEIPT="$ROOT/$RECEIPT_REL"
INDEX="$ROOT/$INDEX_REL"
CONSOLIDATED="$ROOT/$CONSOLIDATED_REL"
COMMIT_PATHS=("$MEAS_REL" "$KR_REL" "$RECEIPT_REL" "$INDEX_REL" "$CONSOLIDATED_REL")
COMMIT_MSG="RATIFIED: P-AK-SEARCH-1-A4 — AutoKernel may adopt a runtime recipe of its own experimental launch under strict runtime admission; adoption is an epoch boundary (operator directive 2026-09-27)"

PATCH_SHA256="2ab398c88612067932d1afd20a445e180c7caddfce14faa2b4418209f75fb7dd"
MEAS_PRE_SHA256="73f09cacca8c1dcb8eaed5c57cebec860b0f35a757e3e9efc32827f20fd3cbc4"
MEAS_POST_SHA256="2f90524e6e3d44ffb711a8b495ea0e5574ddf7ab198346e06731c7188b88fd4e"
KR_PRE_SHA256="6d3ecd9451578c7dab1af07dd0e192e2cb69eb3ed7a971abad4cdb0ec0d36a54"
KR_POST_SHA256="59dc902c1ad3947be60ecd3fc88becffea9aa38069bd0022d9c078ded3691c6b"

RESEARCH="${RESEARCH:-/mnt/raid0/llm/epyc-inference-research}"
# 4b3fcc9f: declared runtime arms, runtime-surface epoch input, adoption receipt (the implementation A4 names).
RESEARCH_COMMITS=(4b3fcc9f)

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
  die "preflight failed: $ROOT is not in the state this bundle was prepared against (epyc-root origin/main e043cfa3). Stale checkout: fast-forward it first. Moved target: regenerate the bundle. Nothing written."
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
               "## P-AK-SEARCH-1-A3.1 — the A3 epoch is the measurement epoch (RATIFIED 2026-09-26)",
               "## P-AK-SEARCH-1-A4 — runtime-recipe adoption by the controller (RATIFIED 2026-09-27)",
               "### Clause 3 — runtime arms that are not bit-exact",
               "**EXTENDED 2026-09-27 by `P-AK-SEARCH-1-A4`**"):
    if kr.count(needle) != 1:
        print(f"  FAIL  expected exactly one occurrence of: {needle[:80]!r}"); ok = False
if ok:
    print("  ok    additions only; A3 Clause 1 and A3.1 preserved verbatim; A4 present once")
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
  --anchor '- **2026-09-27 (v2.x)** — AMENDMENT (Annex K, `P-AK-SEARCH-1-A4`): the AutoKernel controller may' \
  --ratification-id "$GATE_ID" \
  --script "$SCRIPT_PATH" \
  --no-evidence-reason "authority amendment, not a measured claim; every adoption it permits must itself pass the strict runtime admission it names; the implementation is code at epyc-inference-research 4b3fcc9f, verified merged in origin/main by this script's preflight; the motivating observation (DS41-C57 OMP_PLACES barrier sleep, ~+9.5% median) is a probe finding at /mnt/raid0/llm/tmp/ds41-c57-cpu0-20260927/, not a claim this amendment makes" \
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
  "decision": "AK-SEARCH-1-A4-CONTROLLER-ADOPTS-RUNTIME-RECIPE",
  "gate_id": gate,
  "operator_decision": "operator directive 2026-09-27 (given in session): runtime and recipe knobs like OpenMP placement are decided by AutoKernel itself under its own gates, not escalated",
  "ratified_at": ts,
  "operator": operator,
  "status": "ratified",
  "protocol_id": "P-AK-SEARCH-1",
  "clause": "P-AK-SEARCH-1 'What this protocol authorizes' (sixth authority), new section P-AK-SEARCH-1-A4",
  "annex": "K",
  "amendment_class": "amendment",
  "authority": {
    "adds": "adopt one declared runtime field (threads, CPU list, NUMA policy, or a policy-listed env key) of the full selected serving launch as the experimental execution recipe",
    "conditions": ["single-field recipe-constructor delta; runtime surface sealed (A2 bank rule)",
                   "strict runtime admission under a prospective statistics declaration: anchor A/A + neutral calibration, measured control panel, calibrated paired order-randomized selection window, separate confirmation window",
                   "correctness precedence unchanged: op correctness on the candidate recipe; evaluator correctness/determinism/coherence gates on every original output",
                   "durable adoption receipt"],
    "epoch": "adoption is a measurement-epoch boundary: the runtime surface digest enters declared host state; floors and calibration recompute; compositions compounded under the replaced recipe lose their magnitude until re-measured",
    "numerics": "a non-bit-exact runtime arm passes only through the evaluator's existing coherence gate (differing outputs admitted solely against a bitwise_unstable anchor)",
  },
  "implementation": {"repo": "epyc-inference-research",
                     "commits": {"4b3fcc9f": "declared runtime arms (loop/runtime_arms.py), runtime-surface epoch input (loop/run.py, loop/epoch_aliases.py), adoption receipt"}},
  "rationale": "runtime configuration is a property of the measured recipe, not of the kernel; without an adoption authority every runtime finding (DS41-C57: OMP_PLACES barrier sleep, ~+9.5% median decode) became an operator escalation although the strict runtime admission already exists in the loop",
  "not_granted": "no production recipe, registry, lineup, era or cutover change; no banking, readiness, promotion or evaluator/threshold change; reduced screens never adopt; every P-AK-SEARCH-1 denial stands",
  "patch": {"path": patch_rel, "sha256": patch_sha},
  "state": {
    "MEASUREMENT.md": {"sha256_before": meas_pre, "sha256_after": meas_post},
    "measurement/protocols/kernel-research.md": {"sha256_before": kr_pre, "sha256_after": kr_post},
  },
  "tracking": {"first_consumer": "DS41-C57 decision package A (handoffs/active/deepseek-v41-flash-evaluation.md)"},
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
say "Then: the DS41 owning session swaps in the prepared runtime-arm inputs at a batch boundary"
say "(campaign inputs/next/omp; steps in the research lane report)."
