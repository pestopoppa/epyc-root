#!/bin/bash
# ratify_op32_uniform_iq4xs_20260901.sh — OP-32: what do we do with the uniform
# IQ4_XS artifact of Qwen3.8-Flash-Next (qwen4exp)?
#
#   Review:  bash scripts/operator/ratify_op32_uniform_iq4xs_20260901.sh --show
#   Apply:   bash scripts/operator/ratify_op32_uniform_iq4xs_20260901.sh --apply B
#   Commit:  printed by --apply
#
# WHY THIS EXISTS. INF-68 (2026-08-31) measured, on ONE binary and an identical
# canonical recipe (interleave + no-mmap, t48/t64, r5, clean verified windows):
#
#     UD-IQ4_XS (shipped)   tg128  9.13 t/s   pp512 130.7
#     uniform IQ4_XS         tg128 10.52 t/s   pp512 161.2      = +15.2% decode
#
# The UD file's experts are IQ3_S x94 / IQ4_NL x43 / Q8_0 x5 — a dequant-heavy mix
# that is the slow path on the IQK decode kernels; uniform IQ4_XS (type 14) is the
# fast path. Evidence: epyc-inference-research data/inf68-uniform-iq4xs-ab-20260831
# (SHA256SUMS) @0dbc9992. Status per MEASUREMENT_POLICY: OBSERVATIONS (no codified
# protocol id / attestation) — sufficient to choose a baseline, NOT to promote.
#
# The decision matters twice over: it sets the denominator for every qwen4exp CPU
# kernel headline (INF-67's fused decoder), and it asks whether we serve the faster
# artifact. Those are separate questions and this script keeps them separate.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
PATCH="${REPO_ROOT}/artifacts/operator/op32-uniform-baseline-rule-20260901.patch"
TARGET="${REPO_ROOT}/agents/shared/MEASUREMENT_POLICY.md"
STAMP="$(date -u +%Y-%m-%dT%H:%M:%SZ)"

usage() { echo "usage: $0 --show | --apply {A|B|C}" >&2; exit 2; }

show() {
cat <<'OPTIONS'
OP-32 — uniform IQ4_XS for qwen4exp. Three options.

  A  ADOPT FOR SERVING AND BENCH.
     Gain:  +15.2% decode / +23-32% prefill for every qwen4exp CPU consumer, today.
     Cost:  the artifact is quant-from-quant (requantized FROM the UD file), so it
            inherits UD's imatrix tuning without being imatrix-tuned itself. Quality
            is UNVERIFIED beyond a greedy "Paris" sanity check. +4.4 GB on disk.
     Gate:  a codified attestation run AND a quality suite BEFORE any registry swap.
            This script does NOT swap the registry; it records the decision and
            emits those two prerequisites.

  B  KEEP UD FOR SERVING; UNIFORM BECOMES THE REQUIRED COMPARISON BASELINE.  [RECOMMENDED]
     Gain:  zero quality risk, and every future qwen4exp CPU headline is quoted
            against the honest denominator. INF-67's fused-decoder claim in
            particular stops being able to bank 15% of kernel-independent gain.
     Cost:  we knowingly serve ~15% slower than we could, pending a quality answer.
     Gate:  none. Reversible to A at any time by running this script again.

  C  REBUILD FROM SOURCE FIRST, THEN DECIDE.
     Gain:  a genuinely imatrix-clean uniform artifact — strictly better evidence
            than A, and the only version that settles the quality question properly.
     Cost:  the FP8 original was destroyed in the 2026-08-28 rm -rf; re-acquisition
            is ~185 GB (~9-16 MB/s, overnight) and is BLOCKED until the OP-33 disk
            reclaim lands. Decision deferred by days, not hours.
     Gate:  disk headroom, then download, then requantize, then re-run INF-68's A/B.

ALL THREE apply the same amendment to agents/shared/MEASUREMENT_POLICY.md (a human-only
path — which is why this is a script and not an agent edit). It closes the absorption
hole from BOTH directions, because they point opposite ways:
  - an ABSOLUTE headline is the SERVED artifact's number; a faster artifact we do not
    serve is named as available headroom, never as the headline (else we claim
    throughput nobody receives);
  - a DELTA is measured with the artifact held IDENTICAL on both arms, and quoting it
    against a needlessly slow artifact is a defect (else the artifact gap is credited
    to the work).
That rule holds regardless of which option you pick. Wording reviewed by the autokernel
lane 2026-09-01, which raised the first bullet — the original draft covered only the
second and could have been read as licensing a headline on an artifact production does
not serve.
OPTIONS
echo
echo "Amendment to be applied (${TARGET}):"
echo
cat "${PATCH}"
}

apply() {
    local choice="$1"
    case "${choice}" in A|B|C) ;; *) usage ;; esac
    [[ -f "${PATCH}" ]] || { echo "REFUSED: no patch at ${PATCH}" >&2; exit 1; }

    # --index: stages AND applies, refusing if the two disagree. Isolated staging —
    # never a blanket `git add` on a human-only path.
    git -C "${REPO_ROOT}" apply --index "${PATCH}"
    echo "Applied + staged: agents/shared/MEASUREMENT_POLICY.md (fastest-validated-artifact rule)"

    local rat="${REPO_ROOT}/artifacts/operator/ratify_op32_uniform_iq4xs_20260901.json"
    cat > "${rat}" <<JSON
{
  "id": "OP-32",
  "decision": "uniform IQ4_XS for qwen4exp (Qwen3.8-Flash-Next)",
  "choice": "${choice}",
  "ratified_utc": "${STAMP}",
  "evidence": {
    "repo": "epyc-inference-research",
    "path": "data/inf68-uniform-iq4xs-ab-20260831",
    "commit": "0dbc9992",
    "claim_status": "observations (no codified protocol id); sufficient to choose a baseline, not to promote",
    "measured": {
      "ud_iq4xs_tg128_t48": 9.13,
      "uniform_iq4xs_tg128_t48": 10.52,
      "decode_delta_pct": 15.2,
      "ud_iq4xs_pp512_t48": 130.7,
      "uniform_iq4xs_pp512_t48": 161.2
    }
  },
  "artifact": "/mnt/raid0/llm/models/unsloth/Qwen3.8-Flash-Next-GGUF/IQ4_XS-uniform/",
  "artifact_caveat": "quant-from-quant off the UD file; quality unverified beyond a greedy sanity check",
  "policy_amendment": "agents/shared/MEASUREMENT_POLICY.md — OPTIMUM measured on the fastest validated artifact; served artifact named alongside"
}
JSON
    git -C "${REPO_ROOT}" add "${rat}"
    echo "Wrote + staged: ${rat}"
    echo

    case "${choice}" in
      A) cat <<'NEXT'
CHOICE A — adopt for serving and bench. REQUIRED before any registry swap:
  1. Codified attestation run on the uniform artifact (bench_canonical + region lock).
  2. A quality suite vs the UD file — this artifact is quant-from-quant and unproven.
The registry is NOT touched by this script. File both as tasks on INF-68 and do not
swap the served model until both return.
NEXT
         ;;
      B) cat <<'NEXT'
CHOICE B — serving unchanged; uniform is the comparison baseline.
  - INF-68 closes: its outcome contract's "materially faster" branch is satisfied and
    the baseline question is answered.
  - INF-67 (fused decoder) must re-anchor its headline denominator to the uniform
    numbers before quoting any speedup.
Nothing else is required. Reversible to A by re-running this script with --apply A.
NEXT
         ;;
      C) cat <<'NEXT'
CHOICE C — rebuild from source first. PREREQUISITES, in order:
  1. OP-33 disk reclaim must land (the FP8 re-acquisition is ~185 GB).
  2. Re-download the pinned FP8 checkpoint (revision f88480ebce48...), one download
     at a time on this host — racing resume corrupts curl -C -.
  3. Requantize FP8 -> Q8_0 -> uniform IQ4_XS, then re-run INF-68's A/B.
The interim baseline stays the CURRENT uniform artifact; it is honest for speed
comparison and is labelled quant-from-quant wherever it is cited.
NEXT
         ;;
    esac

    echo
    echo "Commit with:"
    echo "  git -C ${REPO_ROOT} commit -m \"RATIFIED OP-32: uniform IQ4_XS — option ${choice}\""
}

[[ $# -ge 1 ]] || usage
case "$1" in
    --show)  show ;;
    --apply) [[ $# -eq 2 ]] || usage; apply "$2" ;;
    *)       usage ;;
esac
