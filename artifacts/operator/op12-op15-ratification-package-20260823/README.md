# OP-12 / OP-15 Ratification Package — INF-37 candidate sources (2026-08-23)

**Purpose.** Evidence summary + operator-executed commit script for the two open INF-37
experimental-source decisions that gate committing the preserved Q4_K candidate patches
(reclaimed-worktree capture, `preserved-uncommitted-20260823/`).

**Decisions covered.** OP-12 (IQ2_XXS one-row VPOPCNT dispatch) and OP-15 (Q4_K branchless
scale/min decoder), both owned by `handoffs/active/mi210-q8-dequant-gemv-roofline.md` (INF-37),
both open since 2026-08-11 (`handoffs/active/master-handoff-index.md` rows).

**Boundary.** This package commits to **experimental branches only**, in the shared llama
experimental tree (`/mnt/raid0/llm/llama.cpp-experimental`, a worktree of the same repo as
production `/mnt/raid0/llm/llama.cpp`). It does **not** touch `production-consolidated-v9`
(frozen at `0db32c06e`), does not push, does not build, does not run inference. **OP-11 still
governs the main-push three-way merge — this package does not touch it** (see below).

---

## 1. The preserved patches (single source of truth — not modified)

Source: `/mnt/raid0/llm/autokernel/preserved-uncommitted-20260823/` (`MANIFEST.md` rows 03, 04).

| Patch | File | Delta | SHA-256 (verified 2026-08-23) |
|---|---|---|---|
| `03-inf37-q4k-branchless-scales-v9-20260811-0db32c06e.patch` | `ggml/src/ggml-cuda/vecdotq.cuh` | +10/−7 | `ec761ac51743cfbad38901eb4cb40faf5a7ad8e561e096d03d002ae1eb0a5eab` |
| `04-inf37-q4k-q8sum-v9-20260811-0db32c06e.patch` | `ggml/src/ggml-cuda/vecdotq.cuh` | +6/−8 | `11f7ea9e4f63a9b2d3607164c328dc7af32838f9e38162eb6056dc049f91b063` |

Both patches were captured as `git diff` from the recorded HEAD **`0db32c06e3e550065b78311a6031ef3dd2c4f27c`**
(frozen v9), which is the tip of both source branches (`experimental-v9-inf37-q4k-branchless-scales-20260811`,
`experimental-v9-inf37-q4k-q8sum-20260811`). Both apply cleanly to `0db32c06e` (context verified
against `git show 0db32c06e:ggml/src/ggml-cuda/vecdotq.cuh`).

## 2. What each patch changes (exact hunks)

### Patch 03 — branchless six-bit scale/min decoder (`vec_dot_q4_K_q8_1`, single hunk `@@ -890,13 +890,16 @@`)

Replaces the divergent `if (j < 2) { … } else { … }` extraction of the Q4_K six-bit scale/min
pairs into `aux[0..1]` with a branchless form:

- `j_low = j & 1` selects the low block; three loads `scale0 = scales[j_low+0]`,
  `scale1 = scales[j_low+2]`, `packed = scales[j_low+4]`;
- both candidate value pairs are computed unconditionally — the "direct" pair
  (`scale0/1 & 0x3f3f`) and the "packed" pair (`(packed & 0x0f0f) | ((scale0/1 & 0xc0c0) >> 2)`,
  plus the `>> 4` variant for the second element);
- a final ternary select `aux[0] = j < 2 ? direct0 : packed0;` (same for `aux[1]`).

Semantically equivalent to the original (verified against the `0db32c06e` source by hunk
comparison). The old form executed 3 unique `scales[]` loads inside one branch; the new form
issues both paths' loads unconditionally (up to 6 unique loads), consistent with the measured
+9.238% VALU/wave. **The lane-local Q8 subgroup sums are left untouched.**

### Patch 04 — q8sum / `ds.y` substitution (three hunks)

- Hunk 1 (`@@ -504,7 +504,7 @@`): `vec_dot_q4_K_q8_1_impl_vmmq` signature
  `const float * __restrict__ d8` → `const float2 * __restrict__ ds8`.
- Hunk 2 (`@@ -515,10 +515,8 @@`): inside the `#pragma unroll` loop, removes the two lane-local
  partial-sum dp4a operations
  (`dot2 = ggml_cuda_dp4a(0x01010101, u[2*i+1], ggml_cuda_dp4a(0x01010101, u[2*i+0], 0))`) and
  rewrites the accumulation to consume the precomputed block sums:
  `sumf_d += ds8[i].x * (dot1 * sc[i]);` and `sumf_m += ds8[i].y * m[i];`.
- Hunk 3 (`@@ -873,7 +871,7 @@` + `@@ -902,14 +900,14 @@`): in the caller
  `vec_dot_q4_K_q8_1`, `float d8[QR4_K]` → `float2 ds8[QR4_K]`, the fill loop reads the full
  `ds8[i] = __half22float2(bq8i->ds)` instead of `d8[i] = __low2float(bq8i->ds)`, and the call
  site is updated.

`block_q8_1.ds` is a `half2` whose `.y` is the sum over **all 32 block elements**, while each
MMVQ lane needs the sum of its distinct **8-element slice** selected by `iqs`. This is the
structural defect behind the measured 5/5 correctness failure (below). The impl has exactly one
caller — the MMVQ function (the MMQ path uses its own `_impl_mmq`) — so blast radius is the
MMVQ path of `vec_dot_q4_K_q8_1` only, one file.

## 3. Screening evidence per row (quoted from the handoff; no numbers invented)

### OP-15 — Q4_K branchless scale/min decoder (candidate = **patch 03**)

Handoff rows "**Test a correctness-preserving branchless six-bit scale/min decoder.** ✅ 2026-08-11"
and the open gate row "**Commit only after explicit experimental-tree approval, then clean-replay
the branchless decoder through the governed paired runner.**":

- The rebuilt gfx90a backend **passed all five exact representative `m=17408,n=1,k=5120` Q4_K
  correctness repetitions**; static ISA size remained **1,452 bytes** while the specialization
  lost **three `s_cbranch_execz` and two `s_branch` sites**.
- Balanced two-control/two-candidate diagnostic: **69,840 vs 78,080.5 ns median (−10.554%)**
  dispatch duration, while the candidate executed **236.5 vs 216.5 VALU/wave (+9.238%)** and
  **87 vs 78 INT32/wave (+11.538%)**. Quoted verdict: *"directional evidence for reduced
  exec-mask/control-flow cost, not an instruction-count win."*
- Receipt: `inf37-q4k-branchless-scales-20260811/diagnostic-paired-r3/receipt.json`, SHA-256
  `de4241bd26b77f5dac7df746d165034b67e6f8105133daf0359142a97dd35d5d`.
- **Authority: diagnostic-only.** The source is uncommitted, so the result is explicitly
  diagnostic-only; the dirty diagnostic cannot satisfy the promotion gate. **No clean governed
  replay numbers exist yet** — that is the gate this approval opens.

### OP-12 — IQ2_XXS one-row VPOPCNT dispatch (candidate = one-file `iqk_gemm_iquants.cpp` diff — **NOT** one of the two preserved patches; see §5)

Handoff rows under "Investigate the permanently-dead `z_HAVE_FANCY_SIMD` AVX512-VPOPCNTDQ IQ2
sign path…" and the row "**With OP-12 approval, commit the one-file IQ2_XXS one-row dispatch and
run matched model-level TG/PP confirmation before any promotion claim.**":

- **Global revival was rejected:** governed ten-block A/B at IQ2_XXS `m=4096,k=14336` improved
  `n=1` by **+5.753%** median but regressed `n=512` by **−9.511%** median (r4 receipt SHA-256
  `242cb61b122b39324316d020d1a2a4bc4be4c17ec3008a66f5ecaf7a2a7c2a91`).
- The **one-row-only template dispatch** preserves the arithmetic VPOPCNT sign decoder
  exclusively for `kernels[0]` while every multi-row kernel keeps the table decoder. Native
  correctness passed **44/44** supported IQ2_XXS matmul cases plus the full
  quantization-function suite; the AVX2-only fallback compiled.
- **Fresh governed replay (r5):** `n=1` improved **+5.733%** median across all ten blocks
  (range **+5.325% to +6.027%**); `n=512` returned to parity at **+0.020%** median
  (range **−0.117% to +0.219%**).
- Receipt: `inf37-iq2-fancy-simd-ab-v9-20260811-r5/receipt.json`, SHA-256
  `12dc4d95a8b208f97ce8c82ab7917f4e6aa28872a90c5fc85f15b72f07fa73ea`.
- Candidate diff SHA-256 **`c24892485af0bddedc641b4ae764302a3c7dc070ed2d765c8e820c01f680b470`**
  against frozen v9 `0db32c06e…` — **verified on 2026-08-23** to match the live diff of the
  retained source worktree `/mnt/raid0/llm/autokernel/worktrees/inf37-fancy-simd-v9-20260811`
  (`ggml/src/ggml-cpu/iqk/iqk_gemm_iquants.cpp`, +13/−7).
- **Remaining gate after commit:** matched model-level TG/PP confirmation before any promotion
  claim. No model-level TG/PP numbers exist yet.

### Patch 04 — q8sum / `ds.y` (no decision row; measured-failed)

Handoff row "**Author and test one surgical Q4_K unpack hypothesis.** ✅ 2026-08-11":

- The candidate removed the two lane-local Q8 partial-sum `dp4a` operations per `QR4_K`
  iteration and consumed the already-stored `block_q8_1.ds.y` sum. **It failed 5/5**
  representative Q4_K correctness cases (**relative errors 0.729–0.977** versus the 0.0005
  limit), while frozen v9 passed 5/5. Structural reason: `ds.y` covers all 32 block elements,
  whereas each MMVQ lane needs a distinct 8-element slice selected by `iqs`.
- Receipt SHA-256 `c8c055ff43f022ae4c61e3142b0278c15a807476db03aa29d16a50b6dbb25eea`;
  *"the one-file diagnostic remains uncommitted and has no performance or promotion authority."*
- **No decision row exists for this patch.** It is preserved so the failure receipt has its
  exact source; committing it (as provenance) or leaving it uncommitted are both valid — see
  `report.md`.

## 4. What approving means operationally

For each approved row, the operator runs `ratify_op12_op15.sh` (this directory), which:

1. validates both preserved patches (existence + SHA-256 against the values in §1);
2. creates **fresh branches from the recorded HEAD `0db32c06e…`** in the shared llama
   experimental tree, one per decision, applying each patch with `git apply --check` then
   `git apply`, and commits with a message naming the decision id and the patch provenance:
   - `experimental-v9-inf37-q4k-branchless-scales-20260823` ← patch 03 (OP-15);
   - `experimental-v9-inf37-q4k-q8sum-20260823` ← patch 04 (provenance of the failed diagnostic);
   - `experimental-v9-inf37-fancy-simd-onerow-20260823` ← the OP-12 one-file dispatch diff,
     SHA-256-verified against `c2489248…` and taken live from the retained source worktree
     (fail-closed if the worktree is gone or the hash does not match);
3. prints (does not execute) the subsequent governed-replay gate reminder;
4. ends with an explicit *execute only after operator approval* banner.

Approving **does not promote anything.** After the commits land, the required next step per the
handoff gates is:

- **OP-15:** clean governed replay of the branchless decoder through the governed paired runner
  — the clean candidate must reproduce correctness and timing before any promotion or
  model-level claim (the dirty diagnostic cannot satisfy this gate).
- **OP-12:** matched model-level TG/PP confirmation before any promotion claim.

Both candidates remain experimental-branch-only until those gates close; production
`production-consolidated-v9` is frozen and untouched by this package.

## 5. OP-11 — untouched by this package

OP-11 governs the **main-push three-way merge** (root `main` 90 ahead / 111 behind
`origin/main`, 103 files changed on both sides; `handoffs/active/master-handoff-index.md`,
row OP-11, and `handoffs/active/loop-owned-fleet-implementation.md` §OP-11). This package
creates branches and commits in the llama experimental tree only; it never touches root `main`
or the llama `main` push. **Do not fold any OP-11 action into this package's execution.**

## 6. Mapping discrepancy (brief vs. handoff) — must be read before deciding

The package brief mapped the two preserved patches 1:1 onto OP-12/OP-15. The handoff does not
support that for patch 04:

- **Patch 03 ↔ OP-15** is exact (the handoff's OP-15 row text is literally the branchless
  scale/min decoder).
- **Patch 04 is NOT the OP-12 candidate.** The handoff's OP-12 row text is the *one-file
  IQ2_XXS one-row VPOPCNT dispatch* — a CPU-side `iqk_gemm_iquants.cpp` change that was never
  part of the preserved patch set (it survives in the retained worktree
  `inf37-fancy-simd-v9-20260811`, kept per the reclamation MANIFEST). Patch 04 is the
  correctness-*failed* q8sum/`ds.y` diagnostic with no decision row of its own.

Consequences for the package: OP-12's commit (Branch C) sources its diff live from the retained
worktree with hash verification; patch 04's commit (Branch B) is framed as provenance-only, not
as a decision. See `report.md` §Discrepancy for the full statement.

## 7. Package files

| File | Role |
|---|---|
| `README.md` | this evidence summary |
| `ratify_op12_op15.sh` | operator-executed commit script (validates → branches → applies → commits → prints replay gate → banner) |
| `report.md` | per-row decision sheet: question, evidence, approve path, decline path |

Prepared 2026-08-23 (preparation only; nothing committed, nothing pushed, no builds or
inference run).
