# Operator Decision Sheet — OP-12 / OP-15 (INF-37 candidate sources)

Ratification package `op12-op15-ratification-package-20260823` (prepared 2026-08-23).
Evidence and hunk-level descriptions: `README.md` in this directory. Execution vehicle:
`ratify_op12_op15.sh` (operator-run; nothing in this package executes without the operator).

**How to decide.** Each row below gives the question, the screening evidence (quoted from
`handoffs/active/mi210-q8-dequant-gemv-roofline.md`, INF-37; no numbers invented), the approve
path, and the decline path. Decline is a complete decision: the row stays open in the master
index, the candidate stays uncommitted, the preserved patch remains the single source of truth.
There is no hidden cost to declining either row.

---

## Row 1 — OP-15: commit the Q4_K branchless scale/min decoder (patch 03)

**Decision text (master-handoff-index).** "Approve or decline one experimental commit for the
Q4_K branchless scale/min decoder before a clean governed replay."

**What the commit is.** `03-inf37-q4k-branchless-scales-v9-20260811-0db32c06e.patch`
(`ggml/src/ggml-cuda/vecdotq.cuh`, +10/−7): replaces the divergent `if (j < 2)` six-bit
scale/min extraction in `vec_dot_q4_K_q8_1` with a branchless form (both candidate pairs
computed unconditionally, ternary select). Lane-local Q8 subgroup sums untouched. Hunk detail:
README §2.

**Evidence (handoff, 2026-08-11).** Correctness: 5/5 exact representative `m=17408,n=1,k=5120`
Q4_K repetitions passed; static ISA 1,452 bytes with three `s_cbranch_execz` and two `s_branch`
sites removed. Balanced two-control/two-candidate diagnostic: **−10.554%** median dispatch
duration (69,840 vs 78,080.5 ns) at the cost of **+9.238%** VALU/wave and **+11.538%**
INT32/wave. Verdict quoted in the handoff: *"directional evidence for reduced exec-mask/
control-flow cost, not an instruction-count win."* Receipt SHA-256 `de4241bd…` (diagnostic-paired-r3).
**Authority: diagnostic-only.** There is **no** clean governed replay yet — the replay is the
gate this approval opens.

**Approve.** Run the script; it commits patch 03 onto fresh branch
`experimental-v9-inf37-q4k-branchless-scales-20260823` from `0db32c06e`, then requires the clean
governed replay through the governed paired runner (correctness AND timing must reproduce)
before any promotion or model-level claim.

**Decline.** Nothing is committed; the patch stays preserved; the row stays open. The
diagnostic evidence remains on file either way. Note: declining does not retire the
Q4_K unpack mechanism — it just keeps this candidate out of the tree.

---

## Row 2 — OP-12: commit the one-file IQ2_XXS one-row VPOPCNT dispatch

**Decision text (master-handoff-index).** "Approve or decline one experimental commit for the
one-file IQ2_XXS one-row VPOPCNT dispatch; screening A/B is +5.733% at n=1 and parity at n=512."

**What the commit is.** One-file CPU change, `ggml/src/ggml-cpu/iqk/iqk_gemm_iquants.cpp`
(+13/−7 vs `0db32c06e`): a one-row-only template dispatch that keeps the arithmetic VPOPCNT
sign decoder exclusively for `kernels[0]` while every multi-row kernel keeps the table decoder.
**This is NOT one of the two preserved patches** (see Discrepancy below); its source survives in
the retained worktree `inf37-fancy-simd-v9-20260811`, and its diff SHA-256
`c2489248…` was re-verified against that worktree on 2026-08-23.

**Evidence (handoff, 2026-08-11).** The global revival of the VPOPCNT path was rejected first:
+5.753% at n=1 but **−9.511% at n=512** (r4 receipt `242cb61b…`) — the kill switch encoded a
real prompt-processing tradeoff. The one-row-only dispatch then measured, in the **fresh
governed replay (r5)**: n=1 **+5.733%** median across all ten blocks (range +5.325% to
+6.027%); n=512 **+0.020%** median parity (range −0.117% to +0.219%). Native correctness
**44/44** supported IQ2_XXS matmul cases plus the full quantization-function suite; AVX2-only
fallback compiled. Receipt SHA-256 `12dc4d95…`. **Remaining gate:** matched model-level TG/PP
confirmation before any promotion claim — no such numbers exist yet.

**Approve.** Run the script; it generates the diff from the retained worktree, **fails closed
if its SHA is not exactly `c2489248…`**, and commits onto fresh branch
`experimental-v9-inf37-fancy-simd-onerow-20260823` from `0db32c06e`. Then: matched model-level
TG/PP confirmation before any promotion claim.

**Decline.** Nothing is committed; the worktree-kept source remains the reference; the row
stays open. The screening evidence keeps its diagnostic value (the candidate stays
measured-not-promoted either way).

---

## Row 3 — Patch 04 (no decision row): commit the q8sum/ds.y diagnostic as provenance

**What it is.** `04-inf37-q4k-q8sum-v9-20260811-0db32c06e.patch` (`vecdotq.cuh`, +6/−8): removes
the two lane-local Q8 partial-sum dp4a operations per `QR4_K` iteration in
`vec_dot_q4_K_q8_1_impl_vmmq` and consumes the precomputed `block_q8_1.ds.y` sum instead.

**Evidence (handoff, 2026-08-11).** **Failed 5/5** representative Q4_K correctness cases
(relative errors 0.729–0.977 vs the 0.0005 limit; frozen v9 passed 5/5). Structural reason on
record: `ds.y` covers all 32 block elements, while each MMVQ lane needs its distinct 8-element
slice selected by `iqs`. Receipt SHA-256 `c8c055ff…`. *"No performance or promotion authority."*

**Recommendation — approve as provenance-only.** The failure receipt's exact source would
otherwise exist only as a reclamation-surviving patch. The script commits it onto
`experimental-v9-inf37-q4k-q8sum-20260823` with a message that explicitly records the failure
and grants no authority. This is not a decision about promoting anything; it is bookkeeping.

**Decline.** Also fine: the preserved patch file remains the single source of truth, and the
handoff's failure row already carries the receipt. If you decline, say so in the wrap-up so the
provenance gap (uncommitted failed diagnostic) is a known, recorded state.

---

## Discrepancy (read before deciding)

The package brief mapped the two preserved patches 1:1 onto OP-12/OP-15. The handoff does not
support that:

- **Patch 03 ↔ OP-15** is exact (decision text matches the patch).
- **Patch 04 is not the OP-12 candidate.** The handoff's OP-12 row text is the IQ2_XXS one-row
  VPOPCNT dispatch (CPU `iqk_gemm_iquants.cpp`), which was never part of the preserved patch
  set. Patch 04 is the correctness-failed q8sum/`ds.y` diagnostic and has **no** decision row.

Consequence: this package commits patch 03 under OP-15, patch 04 as provenance-only (Row 3),
and OP-12's actual one-file candidate from the retained worktree with SHA verification. If you
believe the intended mapping was different (e.g., you want patch 04 gated as part of OP-15),
say so and the script's commit messages can be adjusted before you run it.

## Evidence gaps (numbers the handoff does not contain)

1. **OP-15 clean governed replay numbers** — do not exist. The only numbers are the dirty
   diagnostic's (−10.554% / +9.238% / +11.538%). The approval is for *committing + replaying*,
   not for the -10.554% as a claim.
2. **OP-12 model-level TG/PP confirmation** — does not exist. The +5.733% / +0.020% figures are
   the screening governed replay at kernel shapes, not a model-level claim.
3. **Patch 04 performance numbers** — none exist or are claimable; it failed correctness.
4. **OP-12 candidate file fingerprint beyond the diff SHA** — the handoff records only the diff
   SHA-256 `c2489248…` (verified) and the r5 receipt; there is no recorded per-line diff text in
   the handoff, so the package re-derives the diff from the retained worktree at execution.

## After the decisions

Whatever you decide per row: the governed-replay gates (OP-15) and the model-level TG/PP gate
(OP-12) are required before any promotion; production `production-consolidated-v9` is frozen;
OP-11's main-push three-way merge is out of scope for this package and must not be touched by
its execution.
