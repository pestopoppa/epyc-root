#!/bin/bash
# ratify_op12_op15.sh — OP-12/OP-15 ratification execution script (INF-37)
#
# Operator-run only, AFTER the operator has decided OP-12 and OP-15
# (decision sheet: report.md in this directory; evidence: README.md).
#
# What this does, per approved row:
#   1. Validates the two preserved Q4_K patches (existence + SHA-256).
#   2. Creates FRESH branches from recorded HEAD 0db32c06e in the shared
#      llama experimental tree and commits each candidate onto its own
#      branch with a message naming the decision id + patch provenance.
#   3. PRINTS (does not execute) the governed-replay gate reminder.
#
# What this NEVER does: push, build, inference, production-kernel changes.
# It also never touches the OP-11 main-push three-way merge.
#
# Branch/worktree model: each candidate gets a DEDICATED git worktree
# under $WT_ROOT so the (possibly dirty) shared main checkout of
# $EXP is never switched.
set -euo pipefail

EXP=/mnt/raid0/llm/llama.cpp-experimental
PRESERVED=/mnt/raid0/llm/autokernel/preserved-uncommitted-20260823
RECORDED_HEAD=0db32c06e3e550065b78311a6031ef3dd2c4f27c
WT_ROOT=/mnt/raid0/llm/llama.cpp-worktrees/op12-op15-ratification-20260823

PATCH_OP15="$PRESERVED/03-inf37-q4k-branchless-scales-v9-20260811-0db32c06e.patch"
PATCH_P04="$PRESERVED/04-inf37-q4k-q8sum-v9-20260811-0db32c06e.patch"

SHA_OP15_PATCH=ec761ac51743cfbad38901eb4cb40faf5a7ad8e561e096d03d002ae1eb0a5eab
SHA_P04_PATCH=11f7ea9e4f63a9b2d3607164c328dc7af32838f9e38162eb6056dc049f91b063

# OP-12 candidate source: retained worktree (kept per reclamation MANIFEST),
# never part of the preserved patch set.
OP12_WT=/mnt/raid0/llm/autokernel/worktrees/inf37-fancy-simd-v9-20260811
OP12_FILE=ggml/src/ggml-cpu/iqk/iqk_gemm_iquants.cpp
SHA_OP12_DIFF=c24892485af0bddedc641b4ae764302a3c7dc070ed2d765c8e820c01f680b470

BRANCH_OP15=experimental-v9-inf37-q4k-branchless-scales-20260823
BRANCH_P04=experimental-v9-inf37-q4k-q8sum-20260823
BRANCH_OP12=experimental-v9-inf37-fancy-simd-onerow-20260823

log()  { printf '\n== %s\n' "$*"; }
die()  { printf '\nFATAL: %s\n' "$*" >&2; exit 1; }

# ---------------------------------------------------------------- preflight
log "Preflight"

[ -d "$EXP" ] || die "experimental tree $EXP not found"
[ "$(git -C "$EXP" rev-parse --show-toplevel)" = "$EXP" ] || die "$EXP is not the expected git worktree"
git -C "$EXP" cat-file -e "$RECORDED_HEAD^{commit}" || die "recorded HEAD $RECORDED_HEAD does not exist in $EXP"
[ -d "$PRESERVED" ] || die "preserved patch directory $PRESERVED not found"
[ -f "$PATCH_OP15" ] || die "patch 03 not found: $PATCH_OP15"
[ -f "$PATCH_P04" ] || die "patch 04 not found: $PATCH_P04"
git -C "$EXP" config user.email  >/dev/null 2>&1 || die "no git user.email configured in $EXP — set it before running"
git -C "$EXP" config user.name   >/dev/null 2>&1 || die "no git user.name configured in $EXP — set it before running"

if [ -e "$WT_ROOT" ]; then
    die "worktree root $WT_ROOT already exists — refusing to clobber (remove stale candidates first)"
fi

printf '%-52s %s\n' "$(basename "$PATCH_OP15")" "$(sha256sum "$PATCH_OP15" | cut -d' ' -f1)"
printf '%-52s %s\n' "$(basename "$PATCH_P04")"  "$(sha256sum "$PATCH_P04"  | cut -d' ' -f1)"
[ "$(sha256sum "$PATCH_OP15" | cut -d' ' -f1)" = "$SHA_OP15_PATCH" ] || die "patch 03 SHA-256 mismatch — do not proceed"
[ "$(sha256sum "$PATCH_P04"  | cut -d' ' -f1)" = "$SHA_P04_PATCH"  ] || die "patch 04 SHA-256 mismatch — do not proceed"

[ -d "$OP12_WT" ] || die "OP-12 source worktree $OP12_WT missing — OP-12 cannot be committed (re-verify its fate before approving OP-12)"

# ----------------------------------------------------- per-row confirmation
# Default is DECLINE. The decline path: the row stays open in the master
# index, the candidate stays uncommitted/preserved, nothing is created.
log "Per-row approval"

read -r -p "OP-15: commit Q4_K branchless scale/min decoder (patch 03) -> $BRANCH_OP15? [y/N] " ans
if [[ "${ans,,}" != "y" ]]; then
    log "OP-15 DECLINED — skipping; row stays open (decline path: report.md)"
else
    OP15_APPROVED=1
fi

read -r -p "Patch 04: commit q8sum/ds.y diagnostic as PROVENANCE ONLY (no decision row, measured-failed)? -> $BRANCH_P04? [y/N] " ans
if [[ "${ans,,}" != "y" ]]; then
    log "Patch 04 DECLINED — skipping; the preserved patch remains the single source of truth"
else
    P04_APPROVED=1
fi

read -r -p "OP-12: commit one-file IQ2_XXS one-row VPOPCNT dispatch (diff SHA-verified) -> $BRANCH_OP12? [y/N] " ans
if [[ "${ans,,}" != "y" ]]; then
    log "OP-12 DECLINED — skipping; row stays open (decline path: report.md)"
else
    OP12_APPROVED=1
fi

if [ -z "${OP15_APPROVED:-}${P04_APPROVED:-}${OP12_APPROVED:-}" ]; then
    log "Nothing approved — nothing to do. Exiting."
    exit 0
fi

# ------------------------------------------------------------- OP-15 commit
if [ -n "${OP15_APPROVED:-}" ]; then
    log "OP-15: committing branchless scale/min decoder (patch 03)"
    WTDIR="$WT_ROOT/$BRANCH_OP15"
    git -C "$EXP" worktree add "$WTDIR" -b "$BRANCH_OP15" "$RECORDED_HEAD"
    git -C "$WTDIR" apply --check "$PATCH_OP15"
    git -C "$WTDIR" apply "$PATCH_OP15"
    git -C "$WTDIR" add ggml/src/ggml-cuda/vecdotq.cuh
    git -C "$WTDIR" commit -m "inf37(q4k): branchless six-bit scale/min decoder — OP-15 approved (2026-08-23 ratification package)" \
        -m "Decision: OP-15 (handoffs/active/mi210-q8-dequant-gemv-roofline.md INF-37; master-handoff-index OP-15)." \
        -m "Provenance: preserved-uncommitted-20260823/03-inf37-q4k-branchless-scales-v9-20260811-0db32c06e.patch" \
        -m "  (worktree inf37-q4k-branchless-scales-v9-20260811 @ 0db32c06e; SHA-256 ec761ac5…)" \
        -m "Screening: diagnostic-paired-r3 receipt de4241bd… — 69,840 vs 78,080.5 ns median (-10.554%)," \
        -m "  236.5 vs 216.5 VALU/wave (+9.238%), 87 vs 78 INT32/wave (+11.538%), 5/5 Q4_K correctness reps." \
        -m "DIAGNOSTIC-ONLY authority: clean governed replay REQUIRED before any promotion or model-level claim."
    git -C "$WTDIR" log --oneline -1
    git -C "$WTDIR" show --stat --oneline HEAD | tail -3
fi

# ------------------------------------------------- patch 04 provenance commit
if [ -n "${P04_APPROVED:-}" ]; then
    log "Patch 04: committing q8sum/ds.y diagnostic as provenance-only"
    WTDIR="$WT_ROOT/$BRANCH_P04"
    git -C "$EXP" worktree add "$WTDIR" -b "$BRANCH_P04" "$RECORDED_HEAD"
    git -C "$WTDIR" apply --check "$PATCH_P04"
    git -C "$WTDIR" apply "$PATCH_P04"
    git -C "$WTDIR" add ggml/src/ggml-cuda/vecdotq.cuh
    git -C "$WTDIR" commit -m "inf37(q4k): preserve q8sum/ds.y diagnostic — measured-failed, provenance only (2026-08-23)" \
        -m "No decision row: this candidate FAILED 5/5 representative Q4_K correctness cases" \
        -m "  (relative errors 0.729–0.977 vs 0.0005 limit) — receipt c8c055ff…; ds.y covers all 32 block" \
        -m "  elements while each MMVQ lane needs its 8-element slice (iqs). No promotion authority." \
        -m "Provenance: preserved-uncommitted-20260823/04-inf37-q4k-q8sum-v9-20260811-0db32c06e.patch" \
        -m "  (worktree inf37-q4k-q8sum-v9-20260811 @ 0db32c06e; SHA-256 11f7ea9e…)." \
        -m "Purpose: keep the exact source of the c8c055ff… failure receipt available post-reclamation."
    git -C "$WTDIR" log --oneline -1
    git -C "$WTDIR" show --stat --oneline HEAD | tail -3
fi

# ------------------------------------------------------------- OP-12 commit
if [ -n "${OP12_APPROVED:-}" ]; then
    log "OP-12: committing one-file IQ2_XXS one-row VPOPCNT dispatch"
    [ -d "$OP12_WT" ] || die "OP-12 source worktree $OP12_WT missing (fail-closed)"
    TMPDIFF="$(mktemp)"
    trap 'rm -f "$TMPDIFF"' EXIT
    git -C "$OP12_WT" diff "$RECORDED_HEAD" -- "$OP12_FILE" > "$TMPDIFF"
    SHA_DIFF="$(sha256sum "$TMPDIFF" | cut -d' ' -f1)"
    printf 'OP-12 candidate diff SHA-256: %s\n' "$SHA_DIFF"
    [ "$SHA_DIFF" = "$SHA_OP12_DIFF" ] || die "OP-12 candidate diff does NOT match recorded SHA c2489248… — do not commit"
    WTDIR="$WT_ROOT/$BRANCH_OP12"
    git -C "$EXP" worktree add "$WTDIR" -b "$BRANCH_OP12" "$RECORDED_HEAD"
    git -C "$WTDIR" apply --check "$TMPDIFF"
    git -C "$WTDIR" apply "$TMPDIFF"
    git -C "$WTDIR" add "$OP12_FILE"
    git -C "$WTDIR" commit -m "inf37(iqk): one-row VPOPCNT IQ2_XXS sign dispatch — OP-12 approved (2026-08-23 ratification package)" \
        -m "Decision: OP-12 (handoffs/active/mi210-q8-dequant-gemv-roofline.md INF-37; master-handoff-index OP-12)." \
        -m "Provenance: retained worktree inf37-fancy-simd-v9-20260811 @ 0db32c06e; candidate diff SHA-256 c2489248…" \
        -m "Screening (governed replay r5, receipt 12dc4d95…): 44/44 IQ2_XXS matmul + quant-fn suite; n=1" \
        -m "  +5.733% median (range +5.325% to +6.027%); n=512 parity +0.020% median (range -0.117% to +0.219%)." \
        -m "GATE: matched model-level TG/PP confirmation REQUIRED before any promotion claim."
    git -C "$WTDIR" log --oneline -1
    git -C "$WTDIR" show --stat --oneline HEAD | tail -3
fi

# --------------------------------------------- governed-replay gate reminder
# PRINTED ONLY — nothing here is executed.
cat <<'GATE'

========================================================================
 GOVERNED-REPLAY GATE REMINDER (printed; not executed — the operator owns
 the next steps)
========================================================================
 OP-15  -> branch experimental-v9-inf37-q4k-branchless-scales-20260823:
           run the CLEAN governed replay through the governed paired
           runner. The clean candidate must reproduce correctness AND
           timing before any promotion or model-level claim; the dirty
           diagnostic cannot satisfy this gate (handoff row, receipt
           de4241bd… is diagnostic-only).

 OP-12  -> branch experimental-v9-inf37-fancy-simd-onerow-20260823:
           run matched model-level TG/PP confirmation before any
           promotion claim (handoff row, receipt 12dc4d95… is the
           screening replay, not the model-level gate).

 BOTH   -> No push was performed, no build, no inference. Commits exist
           ONLY on the three experimental branches above. Production
           production-consolidated-v9 is untouched.

 OP-11  -> still governs the main-push three-way merge. Do NOT fold this
           package's branches into that merge, and do not touch the
           merge while it is in flight.

 AFTER  -> the replay gates close, promotion follows the normal
           version-past-production path (new production version, full
           candidate build validated as a whole). Nothing here is a
           promotion.
========================================================================
GATE

# ------------------------------------------------------------------- banner
cat <<'BANNER'

>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>
  EXECUTE ONLY AFTER OPERATOR APPROVAL
  You are the operator. By having run this script you have executed the
  OP-12/OP-15 decisions recorded above. Declined rows were skipped and
  remain open; approved rows are now committed on fresh experimental
  branches from 0db32c06e in the shared llama tree (worktrees under
  $WT_ROOT). Nothing was pushed, built, or inferred.
  Next: the governed-replay gates above, then (only then) promotion.
  Re-check each commit:  git -C "$WT_ROOT/<branch>" log -1
<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<
BANNER

exit 0
