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
- [x] **CH-3 — Screen against the champion** (SOLE baseline; settled by operator 2026-08-27) so
  gains compound. Production stays the promotion reference via the mandatory re-validation of the
  composed champion against the anchor at composition time. ✅ 2026-08-27 — no controller change was
  needed: the anchor arm has always been built from the instrument, and `_verify_instrument` only
  requires a descendant of the frozen production head. Instrument re-pinned to
  `ak/champion/llama-cpp-0db32c06e3e5` @ `5c278648a` (research `a086c95a`).
- [ ] **CH-4 — Compose MoE-Spec as the first real arm** (`c7c37a0d9`). Note its evidence is currently
  below policy: n=3 where `MEASUREMENT_POLICY.md:37` requires ≥5 for a ≥5% claim, α −2.4pp, and the
  5-rep confirm was declined. The composed candidate must earn its own T0/T1/T2 regardless.
- [ ] **CH-5 — Run DF2-5 (np=8 concurrency) and DF2-6 (exact greedy parity), then admit DFlash2 as
  a parallel spec-decode capability.** Approved by the operator 2026-08-27. Attribute any DF2-6
  parity failure before charging it to DFlash2: the in-production MMQ patch `a6b4b5263` is
  numerically valid but NOT bit-exact. Needs GPU; sequence against the live campaign rather than
  killing it.
- [x] **CH-7 — Build the manual→champion admission pipeline.** A documented, repeatable path to
  admit an externally developed source arm (branch + evidence manifest) as a champion MEMBER, with
  the composed candidate rebuilt and re-measured. This is the reusable mechanism for all future
  manual inference research, not a one-off for MoE-Spec and DFlash2. ✅ 2026-08-27 — exercised on
  both manual arms; DFlash2 is preserved rather than rediscovered, which was the operator's
  explicit requirement. The path is: external branch → merge onto the current champion → build with
  the house flags (**including `GGML_HIP_ROCWMMA_FATTN=ON`, see CH-8**) → gates → re-pin the
  instrument. See *The champion as built* below.

  One design note worth carrying: MoE-Spec and DFlash2 both touch `src/llama-context.cpp`, and
  `compatibility()` conservatively treats any two arms touching the same file as an explicit
  conflict — so as separate members they could **never** have composed. Synthesised into a single
  arm they compose trivially, and the combination earns its gates as a unit, so interactions get
  measured rather than assumed.
- [ ] **CH-6 — the config leaders. REVISED 2026-08-27: one of the two is not a lead at all.**
  The earlier framing ("the highest-EV unexploited leads… settleable in hours") is **withdrawn** for
  the ubatch arm, on source evidence:
  - **`ubatch 512→1024` (+46.9%) is a NULL ARM — do not re-run it.** llama.cpp clamps
    `n_ubatch = min(n_batch, n_ubatch)` (`src/llama-context.cpp:265`), and the screen passed
    `-b 512 -ub 1024`, so **both arms ran at an effective ubatch of 512 on one identical binary**.
    The +46.9% is a bimodal sample (`25409, 18083, 25372, 16175, 25381`) whose median landed on the
    fast mode, measured against an anchor bank ~30% below the independently established steady state
    (AK-BH-2, n=30: 24647 t/s vs this screen's 17275 anchor). Its `batch_up` sibling, equally null,
    reported +0.59% purely by landing on the other mode — two null arms 46pp apart. The "sign
    conflicts and 53.5pp spread" that made this look like a live lead were the artifact, not a
    signal. A guard now refuses this class at the producer (`run_autokernel_gpu_discovery.py`,
    research `c84ecdb7`), mutation-tested to fire on `ubatch_up` and stay silent on `ubatch`-down,
    `batch`, `batch_up`, `poll_zero` and `mmap`.
  - **`MMQ_MFMA ON→OFF` (+26.6%) is real** for `Qwen2.5-Coder-0.5B-Q4_K_M @ pp512, np=1, gfx90a`,
    independently reproduced at n=30 (+26.81%). But it is a **build-time** flag: `champion.py`
    requires source evidence for every member, so it cannot be constructed as one, and
    `discovery_static_registry` accepts no CMake flag from planner output. Re-run it as a
    build-config A/B on the champion, and note the open question is not the 0.5B pp512 number but
    whether it survives a real model at `-np > 1` — the champion's own state file records MMQ
    forcing *inverting* on MoE workloads (B2 −30%, B4 −21%, B8 −10.5%).
- [ ] **CH-8 (new, 2026-08-27) — AutoKernel's GPU builder omits the house flash-attention flag.**
  `discovery_deployment_factory.py:2052` passes only `GGML_HIP=ON`, `AMDGPU_TARGETS=gfx90a`,
  `GGML_NATIVE=OFF`, so every AutoKernel GPU candidate is built with `GGML_HIP_ROCWMMA_FATTN`
  **OFF** while production, the AK-BH factorial builds and the standalone DF2 build are all ON.
  Consequences: candidates are measured on a different flash-attention kernel than production runs,
  which undercuts transferability of any GPU result; and the OFF path is the one measured below to
  produce non-finite values at longer sequences under `-fa on`.
  **Operator decision required before changing it** — adding the flag changes the sealed build
  identity and breaks comparability with every prior GPU screen, so it is not a silent fix.
  Scope discipline: the non-finite behaviour was observed in the DFlash **target-feature** path;
  whether plain non-speculative decode also degrades at length on an OFF build is **not measured**
  and must not be asserted.

## The champion as built — 2026-08-27

`ak/champion/llama-cpp-0db32c06e3e5` @ `5c278648a4af2735587b4023613310ccf2341f46` — 35 files,
+3371/−146 over frozen v9, both merges clean, `llama-server` version 10139:

```
5bbcc5498  reviewed measurement instrument (correctness oracle, llama-bench, iqk sources)
 + c7c37a0d9  MoE-Spec  — per-batch top-B expert budget, --moe-spec-budget, default 0 (inert)
 + 2046c64e9  DFlash2   — block-diffusion drafter, a parallel --spec-type pathway
= 5c278648a  the champion
```

It exposes **both** `--moe-spec-budget` and `--spec-type draft-dflash` alongside `draft-mtp`, and it
loads the DFlash2 GGUF that frozen v9 refuses (`wrong number of tensors; expected 81, got 58`).

**The champion must be built ON the reviewed instrument.** A first attempt (`fdc56acb3`) was
synthesised onto raw v9 and was refused by `_instrument_review_receipt`. That refusal was correct:
it had dropped the measurement apparatus, so every screen would have run on a baseline missing its
own instruments. Exactly one pinned measurement blob changed in the rebuild — `llama-bench.cpp`
(MoE-Spec's 8-line env-var fallback for a flag that defaults to 0). `test-backend-ops.cpp`, the
correctness oracle that decides verdicts, is **unchanged**.

### The build flag that is not optional

`GGML_HIP_ROCWMMA_FATTN` **defaults to OFF** (`ggml/CMakeLists.txt:219`). On gfx90a with `-fa on`
the non-rocWMMA flash-attention path produces **non-finite values at longer sequence lengths**.
Measured on the champion built with it OFF: every one of the 12 pinned olympiadbench prompts failed
on task 0 —

```
E process: rejecting DFlash batch after 3020800/3020800 non-finite target features (limit=16)
E srv  decode: failed to process speculative batch
```

— while a 25-character prompt succeeded on the same binary. **Prompt length is the discriminator**,
which is why a short smoke test passes and hides it.

Attribution was verified rather than assumed. The first hypothesis — that merging MoE-Spec into
DFlash2 broke it — was **wrong**: the standalone DFlash2 build `2046c64e9` ran the identical prompts
and flags at 46.1 / 69.4 / 58.9 t/s with zero non-finite errors, and
`git diff 2046c64e9 5c278648a -- src/ common/` is **+67 insertions, 0 deletions**, so DFlash's
source is byte-identical between them. Rebuilt with the flag ON: all prompts pass, zero errors.
MoE-Spec is separately exonerated — it is guarded by `moe_spec_budget > 0` (`llama-graph.cpp:1985`)
and defaults to 0, so the champion carries the capability, not the behaviour.

Had the gates not been run before relaunching discovery, AutoKernel would have spent days screening
against a reference that fails on every real prompt.

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

## CH-1 implementation notes (groundwork done 2026-08-27)

Read of `champion.py` before writing any code:

- **A champion record already exists in empty form.** `_empty_champion(anchor, status=…,
  blocking=…, detail=…)` builds `{member_candidates: [], combined_candidate_id: None,
  last_t0/t1/t2: None, branch: ak/champion/<tree>-<anchor12>, …}` and validates it via
  `schemas.validate_champion`. `record_no_champion()` uses it with
  `status="no_champion", blocking=["NO_GREEN_COMPOSITION"]`.
- **The seed is a DIFFERENT state from `no_champion`.** `no_champion` means "we have nothing";
  Champion₀ means "the aggregate exists and currently equals production". The seed therefore wants
  zero members with an EMPTY blocking list — it is not blocked, it is simply empty.
- **The schema's always-green rule does not obstruct this**: the `blocking_conditions must not be
  empty while status is not 'pass'` check applies to the nested tier events (`last_t0/t1/t2`), and a
  seed has none.
- **BLOCKER, and it is correct-by-design**: `AnchorIdentity` refuses construction with
  `anchor.artifacts must be non-empty, unique, canonically sorted`. Each `AnchorArtifact` needs
  `backend`, `tool`, `binary_sha256`, `linkage_sha256`. So Champion₀ cannot be conjured — it must
  cite the REAL frozen-v9 binary and linkage digests, per backend (CPU and HIP). Those are exactly
  what `scripts/session/verify_llama_cpp.sh` already enforces, so the seeding routine should source
  them from the same place rather than inventing a second truth.
- Consequence for CH-1's shape: a `seed_champion(book, anchor)` entry point, plus a small helper
  that derives the production `AnchorIdentity` (including per-backend artifact digests) from the
  verified frozen tree. The build-recipe carrier (config arms) is a separate field the champion
  record does not model yet — that part is genuinely new.
