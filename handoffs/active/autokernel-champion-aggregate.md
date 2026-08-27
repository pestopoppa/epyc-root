# AutoKernel — the standing aggregate candidate (champion)

**Owner:** operator audit session, 2026-08-27. **Depends on:** INF-06 (campaign), INF-64 (repair track).
**Operator requirement, 2026-08-27:** *"There should ALWAYS be an aggregate production candidate that
holds all the experimented tweaks and is ready for promotion gate testing."* And: AutoKernel screens
against that aggregate, *"attempting to make it better"*, rather than re-deriving deltas against a
fixed production anchor.

## The finding that reframes this

**`champion.py` already implements composition, not best-of.** `compatible_groups` is documented as
*"Deterministic **maximal compatible sets**; no ranking and no gain inspection"*, and the module
contract is *"member results are never combined into a new result… Member performance fields are not
read anywhere in this module."* The composed tree is rebuilt and re-measured **as a whole** and must
earn its own T0/T1/T2 against the anchor; it even names a branch, `ak/champion/<tree>-<anchor12>`.

So the design is right and matches the requirement. Three things are wrong with the reality:

1. **It has never run.** `champion.py` is reachable only from `release/closeout.py` and
   `release/live_material.py`, never from the discovery controller. Dashboard funnel:
   `{candidate: 38, champion: 0, promotable: 0, strict_keep: 1}`.
2. **Nothing makes it always-exist.** Composition is an end-of-campaign release action, not a
   standing invariant.
3. **Discovery screens against the frozen anchor, not the champion**, so gains cannot compound.

## What may and may not go in — measured, not assumed

Audited 2026-08-27. Only **two** unpromoted items are real llama.cpp source diffs, and both fork off
v9 (`0db32c06e`) exactly:

| Arm | Branch | Size | ggml? | Status |
|---|---|---|---|---|
| MoE-Spec (`moe_spec_budget`) | `inf40-moespec-v9` @ `c7c37a0d9` | 8 files, ~81 LOC | none | flag-gated **default 0**; strongest genuine arm |
| DFlash2 block drafter | `ak/dflash2-qwen38-20260820` @ `2046c64e9` | 20 files | none | **ADMIT (operator, 2026-08-27)**: a PARALLEL spec-decode capability, not an MTP replacement — see the ruling below |

**Verified independently: their file sets overlap in exactly one file — `src/llama-context.cpp` —
and neither touches `ggml/`.** Composition is mechanically near-trivial.

Everything else on the intuitive list is a different class and must NOT be composed as a diff:

- **Already in v9**: `GGML_IQK` (since v8), MMQ `a6b4b5263`, HIP graphs (upstream default ON).
- **Build/runtime configuration**, not source: `GGML_HIP_MMQ_MFMA` (+26.6% prefill), `ubatch`
  512→1024 (+46.9%), `-fa` (+4.9%), `GGML_IQK`. These belong in the candidate's **build recipe**,
  which `champion.py` does not currently model — a real gap.
- **Retracted**: ngram 2.8× (warm-context self-copy artifact; corrected to −0.0%/+0.2%/+1.7% CPU and
  **−17.4%** on 122B-IQ2 GPU).
- **Unexploited source residue**: iqk `IQ1_S`/`IQ1_M` are vendored (`iqk_gemm_1bit.cpp`) but omitted
  from CMake, audited clean 2026-07-29, never staged; `iqk_flash_attn.cpp` present, not built.

**Do not seed the champion from the dashboard's 44 rows.** 43 are screening-only `promotion_claim:
false` observations with `"SEARCH RECORD, NOT A CLAIM"` receipts, and the single `strict_keep`
(+28.86% `GGML_IQK` prefill) is a positive-control canary re-measuring a feature already frozen into
production. Banking those would launder observations into a champion — the exact failure the
apparatus exists to prevent — and would destroy the comparability of every later result.

## Tasks

- [ ] **CH-1 — Seed Champion₀ = frozen v9 plus an explicit build recipe.** At worst the aggregate
  equals production, which immediately satisfies the standing requirement and gives discovery a
  stable baseline. Requires extending the champion model to carry a build recipe (config arms), not
  just a source diff.
- [ ] **CH-2 — Make "a champion always exists" an invariant**, re-seeded from production on every
  promotion, rather than an end-of-campaign action.
- [ ] **CH-3 — Screen against the champion** (SOLE baseline; settled by operator 2026-08-27) so
  gains compound. Production stays the promotion reference via the mandatory re-validation of the
  composed champion against the anchor at composition time.
- [ ] **CH-4 — Compose MoE-Spec as the first real arm** (`c7c37a0d9`). Note its evidence is currently
  below policy: n=3 where `MEASUREMENT_POLICY.md:37` requires ≥5 for a ≥5% claim, α −2.4pp, and the
  5-rep confirm was declined. The composed candidate must earn its own T0/T1/T2 regardless.
- [ ] **CH-5 — Run DF2-5 (np=8 concurrency) and DF2-6 (exact greedy parity), then admit DFlash2 as
  a parallel spec-decode capability.** Approved by the operator 2026-08-27. Attribute any DF2-6
  parity failure before charging it to DFlash2: the in-production MMQ patch `a6b4b5263` is
  numerically valid but NOT bit-exact. Needs GPU; sequence against the live campaign rather than
  killing it.
- [ ] **CH-7 — Build the manual→champion admission pipeline.** A documented, repeatable path to
  admit an externally developed source arm (branch + evidence manifest) as a champion MEMBER, with
  the composed candidate rebuilt and re-measured. This is the reusable mechanism for all future
  manual inference research, not a one-off for MoE-Spec and DFlash2.
- [ ] **CH-6 — Re-run the orphaned config leaders against the stable champion.** `MMQ_MFMA ON→OFF`
  (+26.6%) and `ubatch 512→1024` (+46.9%) are the highest-EV unexploited leads in the program and are
  currently stuck as *inconclusive* with sign conflicts and a 53.5pp spread — settleable in hours
  against a fixed baseline.

## Why this is safe

Production is FROZEN (`production-consolidated-v9` @ `0db32c06`, branch pattern pinned in
`human_only_paths.yaml`, `on_pin_mismatch: refuse`); AutoKernel builds only in throwaway worktrees
off `llama.cpp-experimental`; every discovery receipt is `promotion_claim: false` by construction.
Per the 2026-08-27 ruling ([`ruling_op19_e8_chain_20260827.json`](../../artifacts/operator/ruling_op19_e8_chain_20260827.json)),
gates bind at the PROMOTION boundary, not at discovery.

## Operator rulings — 2026-08-27

These settle the open questions in this handoff. Recorded here because they change what the
champion is *for*.

1. **AutoKernel is NOT responsible for promoting kernels to production.** It runs with minimal
   friction. Every promotion gate is operator approval at promotion time, *outside* AutoKernel.
   The champion is a standing, ready-to-test aggregate — not a release process.

2. **CH-3 settled: SOLE-CHAMPION screening.** Dual-arm is unnecessary. If Champion₀ = production and
   every step is measured better than the previous champion, each champion is by construction better
   than production. The drift risk is real — v29 and v31 both produced S1 positives (+4.89%, +5.37%)
   that flipped negative on replication — and it is caught by the mandatory re-validation of the
   COMPOSED champion against the production anchor at composition time, which `champion.py` already
   requires. That re-validation is not optional.

3. **DFlash2 is a PARALLEL spec-decode pathway, and the kernel must SUPPORT it.** Correcting an
   earlier mischaracterisation in this file: "`--spec-type` takes one value" binds a single *server
   instance*, not the kernel. Roles run separate servers, so one kernel supporting both spec types
   serves MTP for most of the stack and DFlash2 for Qwen3.8-27B at the same time. DFlash2 therefore
   composes as ADDED CAPABILITY, not a mutually-exclusive swap, and the earlier "policy-barred /
   not additive" framing is withdrawn. Not every model has a DFlash2 drafter head; current intent is
   Qwen3.8-27B only, with the rest of the stack staying on MTP. The lean registry compiler is
   adjusted at promotion time to select per role.

4. **Run the DFlash2 gates.** DF2-5 (np=8 concurrency) and DF2-6 (exact greedy parity) are approved
   to run. Note DF2-6 may fail for a reason unrelated to DFlash2: the in-production MMQ patch
   `a6b4b5263` is numerically valid but **not bit-exact**, so a parity failure must be attributed
   before it is charged to DFlash2.

5. **Manual research admits as a MEMBER, never as a claim.** `champion.py`'s contract already
   supports exactly this: "member results are never combined into a new result… a champion can cite
   only a *combined candidate's* passing T0/T1/T2 events against the current sealed production
   anchor." So an externally developed source arm enters as a member and the COMPOSED tree is
   rebuilt and re-measured; its original numbers are never inherited. The earlier caution in this
   file applies ONLY to the 43 config screening rows, which carry no source diff and therefore
   re-enter as build-recipe settings to be re-tested (CH-6), not as banked results.
