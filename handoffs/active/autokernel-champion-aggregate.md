# AutoKernel — the standing aggregate candidate (champion)

**Owner:** operator audit session, 2026-08-27. **Depends on:** INF-06 (campaign), INF-64 (repair track).
**Operator requirement, 2026-08-27:** *"There should ALWAYS be an aggregate production candidate that
holds all the experimented tweaks and is ready for promotion gate testing."* And: AutoKernel screens
against that aggregate, *"attempting to make it better"*, rather than re-deriving deltas against a
fixed production anchor.

## Start here — open work (2026-09-29)

**The champion is `1bceceb05` on `ak/champion/llama-cpp-ffc1bac82eec`** (v10 lineage; advanced 2026-10-04 by the
KVU-19 fold, `90c12df42` → `1bceceb05`, fast-forward; see the fold ledger entry below). This is the GLOBAL champion
branch. Builds: `kernels/builds/cpu-20261004-1bceceb05` and `kernels/builds/gpu-20261004-1bceceb05`. Resolve the tip
live before quoting it.

**Fold ledger — 2026-10-04, KVU-19 fold** (executed by workspace-ec, ledgered by ak-ds41-main):
- **Folded:** `ac97e305a` (KVU-19a FA masked-block skip, GPU), `a0d0ae238` (its CPU half), `1bceceb05` (KVU-19b commit 1:
  `n_seq` hint routes rows-are-sequences batches to the vec kernel). Fast-forward of `90c12df42`, no conflicts, moved with a
  guarded CAS `update-ref`, so the champion shas are exactly the shas the store images were built from. `ak-loop-tree`
  refreshed with `read-tree -m -u` (clean). Pushed to fork.
- **Held out:** KVU-19b commit 2 `c7f5ac9ad` (WMMA sequence tiles): ~14% slower on aligned 4×8 verify and it breaks its own
  skip-on ≡ skip-off exactness (6/119 cases); its planner is confirmed absent from the folded binary. Rework is with
  workspace-ec.
- **Gates (fold slot VERDICT PASS):** G0 kernel-coverage fold-check PASS, 0 losses (no GPU coverage; the slot is the GPU
  gate). Exactness E1–E8 PASS (skip on ≡ off, bit-identical). CPU harness 86 + 141 cases bit-identical, CPU
  test-backend-ops 5178/5178; GPU test-backend-ops 2949/2949 + 81/81 ×3. 27B DFlash2 paired smoke: champion ≡ skip-off ≡
  skip-on, byte-identical (36% accept).
- **Perf:** 4×1 decode at 327k occupied cells 9.17 → 5.51 ms; single-row FA with 114k foreign cells 2335 → 284 µs. At
  serving scale (KVU-16b replay on the combined 19a+19b build, `artifacts/gpu-slot-ak-20261004/`), the skip made each
  prefill chunk 4.5× cheaper at 240–280k occupied cells.
- **Serving-level (P3 v2 A1, 2026-10-04 09:11Z, champion image `gpu-20261004-1bceceb05`, same binary, skip ON vs OFF):** at
  L3 ≈355k occupied cells with 3 parked neighbours, drafted 34.98 vs 15.74 tok/s (2.22×; loss vs L0 −0.19% vs −55.4%),
  no-draft 21.53 vs 8.45 (2.55×; −1.4% vs −60.3%); no-draft text sha identical ON = OFF; VRAM own peak 51.7 GiB. Meets
  KVU-19b's "L3 loss < 10%" for single-sequence decode with neighbours. `/mnt/raid0/llm/tmp/gpu-slot-ak-20261004/results/20261004T091103Z/`.
- **Standing receipt:** champion-only, measured against the recorded v10 baseline (FOLD-2 G5 `ef81196d5`, 20 launches,
  median 31.30 tok/s, unpaired by operator rule); result pending at filing.
- **Loop anchors:** DS41 and Q38FN anchors still have `90c12df42` as an ancestor but are not the champion; both reseed on
  `1bceceb05` at relaunch (INF-77 DS41-C121).
- **Production:** carried by v11 via kernel-promotion (full candidate validated as a whole; no interim v10.x). Before any sweep folds "an unfolded
CPU branch", read the **DO-NOT-FOLD ledger** below.

DS41's champion of record on its own campaign lineage is `a1faab471e83`, with 4 serving-gated keeps (DS41-C68,
+7.113%). Folding them into the global champion is DS41-C47/C68, owned by workspace-76:
[`deepseek-v41-flash-evaluation.md`](deepseek-v41-flash-evaluation.md).

| task | what to do |
|---|---|
| **V6R-4a / V6R-4c** | Ride the v11 candidate gate (the fast loader; V6R-4c PARKED by the operator 2026-09-27) |
| **V6R-4b** | Operator: OP-58, ratify the forward-port rule |
| **HEAD-3** | The 35B np=24/32 ceiling; needs an operator go for ~12 min of exclusive GPU |
| **CH-8** | AutoKernel's GPU builder omits `GGML_HIP_ROCWMMA_FATTN` |
| **CH-14 / CH-16** | Manual-research loop runbook (start from `scripts/benchmark/serving_evidence_refresh_runbook.md`, research repo); correct the loop champion's inflated per-commit claims |
| **FOLD-0 / V6R-1..3** | INF-70's residual fold items; v6-fork triage (DiffT-V2, KV context-shift, paged-attn) |
| **not on this page** | `AK-INST-3`, `AK-INST-2`, `AK-DEPLOY-2` live in [`autokernel-restart-and-strip.md`](autokernel-restart-and-strip.md). |

Closed work and superseded champion-state narration: § *Completed Scope*.

## Completed Scope

| Scope | Where |
|---|---|
| CH-1 … CH-7, CH-9 … CH-13, the CH-1 implementation notes, CHAMP-2, CHAMP-3 | [completed ledger](../completed/autokernel-champion-aggregate-completed-through-2026-09-29.md) |
| Champion-state narration: RECONCILED 2026-08-31 (`a2728701`, +12.618% tg128), STANDING 2026-09-03 (`732389d6`), CONSOLIDATION 2026-09-08 (`ef81196d5`) | [archived history](../archived/autokernel-champion-aggregate-history-through-2026-09-29.md) |

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

- CH-1 … CH-7 are done (2026-08-28/30); CH-6 settled that neither config leader belongs in the champion. § *Completed Scope*.
- [ ] **CH-8 (new, 2026-08-27) — AutoKernel's GPU builder omits the house flash-attention flag.**
  `discovery_deployment_factory.py:2052` passes only `GGML_HIP=ON`, `AMDGPU_TARGETS=gfx90a`,
  `GGML_NATIVE=OFF`, so every AutoKernel GPU candidate is built with `GGML_HIP_ROCWMMA_FATTN`
  **OFF** while production, the AK-BH factorial builds and the standalone DF2 build are all ON.
  Consequences: candidates are measured on a different flash-attention kernel than production runs,
  which undercuts transferability of any GPU result; and the OFF path is the one measured below to
  produce non-finite values at longer sequences under `-fa on`.
  **RULED 2026-08-28, and done.** Operator: *"if it leads to better performance finds, I don't care
  if it breaks comparability with prior GPU screens. We only added the GPU recently anyways."*
  Prior GPU screens are therefore **superseded, not reconciled** — they were taken on a kernel
  configuration production does not run. Two flags changed in
  `discovery_deployment_factory.py` (research `71db62e9`):

  | flag | was | now |
  |---|---|---|
  | `GGML_HIP_ROCWMMA_FATTN` | unset → CMake default **OFF** | **ON** |
  | `GGML_NATIVE` | explicitly **OFF** | **ON** |

  `GGML_NATIVE` was ruled the same way and for the same reason: every reference build on this host
  is ON, and matching production is what makes a find transferable. It is the portability trade
  taken deliberately — OFF is what a portable build wants, and this is a single-host program.
  Verified by mutation test that both survive `_sealed_cmake_defines()` rather than being dropped
  as unknown keys (only the RPATH keys are force-overridden there), and confirmed present in the
  live v33 execution closure.

  The repo README gained a *"Build configuration — read this before forking or reproducing"*
  section at the operator's request, recording which flags are host-specific and why, so a fork
  knows these numbers hold for this hardware and these flags and that reproducing them elsewhere
  means re-measuring rather than re-reading.

  Scope discipline, unchanged: the non-finite behaviour was observed in the DFlash
  **target-feature** path; whether plain non-speculative decode also degrades at length on an OFF
  build is **not measured** and is not asserted.
- CH-9 is done (2026-08-28): § *Completed Scope*.
- [ ] **CH-17 (new, 2026-10-03) — every kernel freeze re-selects each role's spec-decode recipe.** A v-next
  promotion checklist item (kernel-promotion skill and its `promotion_gates.yaml`, and the v11 candidate gate
  with V6R-4a). Origin: the 2026-08-27 ruling 3 said "adjust the lean registry compiler at promotion time"; the
  v10 freeze (`ffc1bac82`) was even qualified on DFlash2 vs MTP (np4 ratio 1.239), yet the promotion only re-ran
  `stack_change_pipeline.py update`, and :8083 kept `draft-mtp` until 2026-10-03 (drafter-compile DESIGN §4 item
  8, `/mnt/raid0/llm/tmp/drafter-compile-20261001/DESIGN.md`). Acceptance: for each served model, list the
  drafters the new kernel supports (`llama-server --help` spec types; master `drafters`), compare the
  qualification evidence per drafter, and either change `stack_topology.yaml` `drafter_selection` or record
  "selection unchanged, because …" in the promotion receipt. The step blocks the freeze until done. Now that
  DRAFT-SEL-1 makes the selection a compile input, this is a data edit, not a compiler change.

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
   *(2026-10-03: the compiler adjustment was NOT made at the v10 promotion; it landed only with
   STACKCHG-DFLASH2-20261003 as DRAFT-SEL-1, orch `d3233170`. :8083 serves DFlash2 since then. The
   freeze-time re-selection that would have caught it is CH-17.)*

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

## Open follow-on from 2026-08-28

- CH-10 … CH-13 are done (2026-08-28): § *Completed Scope*.
- [ ] **CH-14 (new, 2026-08-28) — document the manual-research loop as a runbook.** CH-7 + CH-13
      now compose into a complete loop (research → admit → gate → attest → visible standing), but
      it is only reconstructible by reading two handoffs and three scripts. Write it up in
      `docs/guides/` as the standing procedure, with the authority boundary stated explicitly so a
      future session does not "simplify" it by emitting a campaign receipt.

## 2026-08-30 — the champion finally has a measured effect against production on the DEFAULT path

CH-12 (retracted and corrected on 2026-08-28) established that the champion's measured effect vs
production existed *on the DFlash2 serving path production cannot reach at all*. What did **not**
exist was an effect on the default path beyond "no regression": CH-4's rows were 748.34 → 768.83
pp512 and 28.21 → 28.20 tg128, read honestly as no change.

**That gap is now closed, for the LOOP champion.** Note the two champions are different objects
and must not be conflated: CH-4/CH-12 measured the *manual-admission* champion `5c278648a`
(MoE-Spec + DFlash2); what follows measures the *loop* champion `5ad3e36d` on
`ak/loop-champion-20260828`, 36 commits above frozen v9.

| surface | production `0db32c06` | champion `5ad3e36d` | effect | floor | reading |
|---|---|---|---|---|---|
| **tg128** | 264.918 tok/s | 287.499 tok/s | **+8.524%** | 1.188% (calibrated) | **decisive by 7.2×** |
| **pp512** | — | — | +0.090% | 0.029% (uncalibrated) | **NO CHANGE** |

Both arms built fresh from named commits with the identical recipe · 20 alternating pairs · one
claim held across both surfaces · neither arm drifting · 40/40 resident · clocks pinned 1700 MHz on
all 80 invocations · correctness oracle rc=0, `2/2 backends passed`, on **both** arms. Stored as
`/mnt/raid0/llm/autokernel/loop-memory/champion-vs-production.json`
(`epyc.autokernel.champion_vs_production.v1`), five capability entries each carrying its evidence
path. The pp512 `decisive=True` is a floor artifact — and the changed files predict ~0 prefill
independently, since the 36 commits touch only the matrix-*vector* decode path and FA-vec and
nothing in `mmq.*`.

- [x] **CH-15 — the house recipe reproduces production's frozen build on BOTH backends.**
      ✅ 2026-08-30. Established by comparing *artifacts* rather than flags: production's shipped
      `libggml-cpu.so` vs our fresh v9 build, **584 defined symbols each, zero diff**; production's
      `libggml-hip.so` vs ours, **918 distinct device kernels each, zero symbols unique to either
      side**. This matters here because `champion.py`'s anchor identity and CH-1's build recipe both
      rest on our recipe standing in for production's, which was previously unevidenced.
      Follow-on, filed in INF-66 as **R18-A**: flip `build_recipe.py:43`'s
      `PRODUCTION_RECIPE_IS_VERIFIABLE = False` with this evidence attached.
- [ ] **CH-16 — the loop champion's per-commit claims are inflated 20× and must be corrected where
      a reader of the branch will land.** The 36 commit messages on `ak/loop-champion-20260828`
      claim gains **compounding to +171.7%** (arithmetic sum +101.8%) against a measured block
      effect of **+8.524%** — the same cumulative-attribution defect as run 17's (INF-66 D14) at
      twenty times the magnitude. **No individual percentage on that branch is a marginal effect.**
      Commit messages are immutable, so the correction goes at the tip
      (`NOTES-attribution.md`) and into `loop/program.md`'s *Settled — do not re-open* section.
      Owned by INF-66 as **R18-C**; listed here because this page is where someone comes to ask
      what the champion is worth. **Blocked on run 19 finishing** — `ak-loop-tree` is off limits
      while it runs.

## FOLD — INF-70 CPU kernel work into THE champion (operator request 2026-09-07)

Plan: [`docs/design/inf70-cpu-fold-into-champion-20260907.md`](../../docs/design/inf70-cpu-fold-into-champion-20260907.md).
Same lineage (fork `270b48ed6` on this branch), merge-tree **0 conflicts**; two default-ON blockers on
the CPU side must be fixed first; PROD-2 was operator-deferred 09-06 and today's request reverses it.

- [x] **FOLD-OP — operator decided 2026-09-07** ✅: (a) fold IS wanted — no reversal ceremony needed,
      folding at the right time is fine (NOTE: the CPU work is NOT yet in the champion; it sits on
      `inf70/champion @ 6f032c48d`, forked from this lineage but unmerged); (b) **timing: fold as soon as
      run 29 ends — the operator will stop it to reboot the machine; that reboot boundary is the fold
      trigger.** Do not stop run 29 for the fold; do not hand FOLD-0 to `inf70-audit` yet — this was a
      preliminary investigation for clarity on blockers. Surface FOLD-0 to `inf70-audit` when the
      run-29 / reboot boundary approaches, so the fold-ready commit is prepared in time.
- [ ] **FOLD-0 (`inf70-audit`, own branch)** — *note 2026-09-08: the re-base onto the CPU champion
      (`inf70/champion3` @ `9c4f73e29`) was done by INF-70 inside the fold candidate, so `ef81196d5` already
      carries champion3; the remaining FOLD-0 items below are theirs to close in their own turn*: fold-ready commit on `6f032c48d` — `GGML_OP_MOE_TOPK_NORM`
      opt-in (or CUDA kernel + test-backend-ops case), INF-64 fused decode opt-in, `ggml-alloc.c` stray
      define; re-run greedy bit-identity + `test-backend-ops -b CPU`; record the PROD-2 reversal in the
      INF-70 ledger; **push** `inf70/champion` (private clone today).
- [x] **FOLD-1 (champion owner)** ✅ 2026-09-08: loop stopped at the boundary (verified dead), pre-fold GPU tip
      tagged `ak/pre-fold-gpu-tip-20260908` (pushed), fold candidate `ef81196d5` built at
      `/mnt/raid0/llm/tmp/build-fold-ef81196d5`; `verify_ggml_linkage.sh` PASS.
- [x] **FOLD-2 gates, SAME merged tree** ✅ 2026-09-08 — all PASS with real tallies on `ef81196d5`:
      G1 `test-backend-ops -o SSM_SCAN -b ROCm0` 7/7 OK (incl. K=4/K=3 rollback), G2 MUL_MAT 1140/1140 OK
      (326 unsupported type combos), G3 GATED_DELTA_NET 39/39, G4 dispatch **observed** (`llama-bench -v` +
      `GGML_SCHED_DEBUG=2`: 27,516 nodes, SSM_SCAN=0, SSM_CONV 576 + GATED_DELTA_NET 576 on ROCm0, CPU holds only
      12 GET_ROWS), G5 tg128 vs gen-021 **+0.052%** (20 pairs, floor 0.638%, not decisive). Result file
      `/mnt/raid0/llm/tmp/fold-window-20260908/fold2-result.json`. NOTE: the first G1-G4 run reported PASS with
      **OK=0** (ANSI-coloured verdicts defeated the `\bOK\b` match; `llama-bench` swallowed scheduler logs
      without `-v`) — structural guards added: a gate PASSES only with ≥1 case run AND an agreeing `N/N tests
      passed` tally, and the graph check only with a plausible node count AND the expected recurrent ops present.
- [x] **FOLD-3** ✅ 2026-09-08 — **fast-forward + push, NOT a relaunch** (operator directive: no relaunch):
      `ak/champion/llama-cpp-0db32c06e3e5` `bff30cebe` → **`ef81196d5`** (`--ff-only`, tip == candidate) at
      11:16:49Z, lineage verified (`bff30cebe`, `445e93a8`, `9c4f73e29`, production `0db32c06e` all ancestors),
      worktree clean, pushed to fork `pestopoppa/llama.cpp`. Production branch untouched. Consolidated champion =
      GPU tip (6 unconfirmed keeps) + CPU champion3 `9c4f73e29`. PROD-1 still owes the CPU launch recipe before
      any promotion headline.

### CONSOLIDATION COMPLETE — `ef81196d5`, 2026-09-08

- [x] **FOLD-4 — consolidation is CLOSED; there are no CPU keeps pending** ✅ 2026-09-08. INF-70 reported
      its final RETEST-1 results at ~12:10Z with **no keeps to fold**. The consolidated champion is
      **`ef81196d5`** on `ak/champion/llama-cpp-0db32c06e3e5` = GPU tip `bff30cebe` + CPU champion3
      `9c4f73e29`, FOLD-2 G1–G5 all PASS. The operator's standing condition — *no kernel research until a
      FULLY consolidated champion* — is **satisfied**. Loop relaunch remains a **separate operator go**;
      nothing on this page launches or schedules it.

#### Inherited v6-fork candidates — from INF-32, archived 2026-09-14

`llamacpp-v6-consolidation.md` (INF-32) was archived 2026-09-14 as superseded by v9. Its three
unresolved `NEEDS-OPERATOR-REVIEW` rows are relocated here so they do not vanish with the page. They
are **un-triaged candidates, NOT queued folds** — nothing here is scheduled, and each is subject to the
operator's standing gate on new kernel research. Full context:
[`llamacpp-v6-consolidation.md`](../archived/llamacpp-v6-consolidation.md). The other two rows on that
page are closed: SWA slot-reuse (`d1c72d7fc`/`603702769`) and `--moe-n-expert` (`86901388a`) both
verified **DROP** 2026-08-12 — the SWA pair is a per-sequence-blind regression, and v9 already covers
expert masking with stock `--override-kv <arch>.expert_used_count=int:N`.

- [ ] **V6R-1 — Differential-Transformer-V2 arch (`36ceed44d` / `23973ea66`)**: eval-gated, not in the
      deployed registry. Triage question is whether any registry model wants the arch at all before any
      port cost is spent.
- [ ] **V6R-2 — streaming KV context-shift controls (`632ce0f92`)**: check first whether v9/upstream
      already ships equivalent context-shift controls (the `--moe-n-expert` outcome is the precedent —
      the stock flag had arrived).
- [ ] **V6R-3 — paged-attn upstream-overlap**: the v6 work was resolved and runtime-verified on branch
      `f1-paged-attn` @ `112022a0b` (iswa graph block-table wiring `ea50522a7`; opt-in, off-by-default,
      bit-exact on plain Qwen3.6-35B and SWA gemma-4-31B) but was never folded. It is build-10079-era
      against a 10241-class champion, so folding means a re-base and a re-measure at the current floor.
- [x] **V6R-4 — parallel model load (repack + reader), lost in the v6 bundled revert.** ✅ 2026-09-25 (main-ak-seat)
      The OpenMP repack parallelization (`52ddd3200`, 2025-12-21; upstream PR #18239 closed unmerged) left the
      lineage when v6 Stage 1a `814e81782` was reverted as a whole (`358f0c748`); full record in
      `docs/reference/agent-config/INCIDENT_LOG.md` → INC-20260925. Re-ported onto the v10-lineage champion as
      `25132e042` (test restored and extended, 150/150 bit-exact) plus a parallel pread reader run as an OpenMP team,
      `90c12df42` (`--load-threads` / `LLAMA_ARG_LOAD_THREADS`; the old loader thread was pinned to CPU 0 by libgomp
      under `OMP_PROC_BIND=spread`). Bit-exact (tokens, KL on logits); 27B load 3.2x warm / 2.1x cold. Under
      `GGML_IQK=1` the DS41 recipe touches no CPU_REPACK tensor, so the reader is the whole DS41 win.
      **Champion advanced** `ak/champion/llama-cpp-ffc1bac82eec` `2b57340bf` → `90c12df42`, pushed to the fork
      (workspace-8d notified). Gates (research `a5906f24`, `data/champion-advance-fastload-20260925/`): DS41 519 GB
      load 254.0 / 277.7 s (anchor) → 98.2 s (fast loader), with a 262.6 s single-thread control on the same binary;
      production-recipe decode A/B cut by the operator after one pair (frontdoor 42.23 vs 41.79 tok/s, 0.99,
      identical output). Builds: `kernels/builds/cpu-20260925-90c12df42` (candidate) and
      `cpu-20260925-2b57340bf` (base), ggml linkage PASS. The DS41 campaign re-anchored on it (INF-77 DS41-C32).
  - [ ] **V6R-4a — carry the fast loader into production v11.** It rides the champion, so a v11 promotion from the
        champion tip inherits it; the promotion checklist must still prove it. Acceptance, at the v11 candidate
        gate: `25132e042` and `90c12df42` are ancestors of the candidate; `tests/test-repack-parallel` passes;
        a CPU load with auto load threads is measured against v10 on one production model; and the decode A/B
        that was cut at one pair here is run to the promotion protocol's full pair count.
        2026-10-01 (V6R-4d): the GPU half of champion `90c12df42` is validated no-regression vs v10, with SW-9
        exercised on GPU (pp +0.39%, tg -0.46%, floor 2%; identity and residency PASS). A v11 candidate built from a
        descendant tip, such as the DS41-C68 fold, still reruns that A/B (`gpu-champion-ab`) on its own full GPU build.
  - [ ] **V6R-4b — operator ratification of the forward-port rule** (OP-58 when the index row lands). Proposed
        text for `CLAUDE.md` § *Experimental Kernel Workflow*: forward-port one feature per commit; before
        reverting a bundled commit, split it and revert only the gated-out parts; a feature's test travels with it
        through every consolidation. Origin: INC-20260925. The operator ratifies; no session edits `CLAUDE.md` for
        this.
        2026-10-04 correction and status: INC-20260925 lost **our own** OpenMP parallel repack (`52ddd3200`,
        upstream PR #18239 closed unmerged) in the bundled v6 Stage 1a revert. It did not lose an upstream kernel.
        `docs/reference/agent-config/INCIDENT_LOG.md` already says this correctly. Repeat the correction wherever a
        summary calls the lost code "upstream". The operator was offered the OP-58 sign-off package in chat on
        2026-10-04, and it is still **unratified**. Nothing else depends on it. The DS41-C116 kernel-preservation
        gate (`kernel_coverage.py`, G0 at fold, research `4f8f11c7`) now enforces the "test travels with the
        feature" half in code, without the rule being ratified.

  - [ ] **V6R-4c — the fast loader's AUTO reader team must equal the compute thread count.** Found by INF-77 DS41-C57
        (2026-09-27, `/mnt/raid0/llm/tmp/ds41-c57-cpu0-20260927/`). `llama-model-loader.cpp:1689` sizes the auto pread
        team as `min(32, max_threads)`. Under GNU libgomp with `OMP_PLACES=cores` over 96 places, a 32-thread team
        ahead of the 48-thread compute team leaves libgomp throttled, and every decode barrier sleeps: about -11% tok/s
        and up to 13% request spread on DS41. The isolated long-wait micro-bench reproduces it (`gomp/results3.txt`).
        Fix on an experimental branch from the current champion tip, in the `90c12df42` lineage: default the auto team to
        `n_threads` (the compute `-t`), keeping `--load-threads` / `LLAMA_ARG_LOAD_THREADS` as the override. Acceptance:
        bit-exact load (tokens plus KL on logits, as for V6R-4); load time within noise of today's auto setting; and DS41
        under `OMP_PLACES=cores` spins (median OMP voluntary switches ~0) with no `--load-threads` flag. Check whether
        production v10 carries the fast loader; production resolves libomp with `KMP_BLOCKTIME=10`, so it is expected to
        be unaffected, but that is unmeasured. Rides V6R-4a into v11. Until it lands, DS41 carries the recipe arm (DS41-C59).
    - PARKED 2026-09-27 (operator): Loader-default fix prepared at e665242f0 (branch `experimental/loader-team-follows-threads-20260927`, 7 lines in `common/common.cpp` `common_model_params_to_llama`: auto load threads follow `-t`, plus the matching `--load-threads` help string in `common/arg.cpp`; cut from the AK champion tip `90c12df42`, pushed to fork), not built or benchmarked. The runtime-arm flag covers DS41 now (DS41-C59, `--load-threads 48`); resume by taking e665242f0 through the experimental workflow (build, then this item's acceptance: bit-exact load, load time within noise, DS41 spinning with no flag) into the champion, and from there into v11 via V6R-4a.

  - [x] **V6R-4d — live GPU no-regression validation of the champion's HIP build.** ✅ 2026-10-01 (all parts done; V6R-4d.2 below) The GPU half of the champion now
        exists: **`kernels/builds/gpu-20260929-90c12df42`**, the HIP (gfx90a) twin of `cpu-20260925-90c12df42`, built
        2026-09-29 (workspace-8d, operator-approved). It uses recipe `gfx90a-house-v1`, and its CMakeCache is identical
        to v10's `gpu-20260921-ffc1bac82` on every GGML/LLAMA/target/compiler entry. It reports `10308 (90c12df42)`.
        SW-9 is compiled in: `libllama-common.so` exports both `out_dists` overloads of
        `common_sampler_sample_and_accept_n`, and v10 GPU has 0. `verify_ggml_linkage.sh` PASS. RUNPATH carries no empty
        element. Record: that directory's `PROVENANCE.md`. No `ggml-cuda`/`ggml-hip` source differs from v10, so the
        GPU risk is host-side (server, sampling, loader). **No live check has been run.** The MI210 is full with the
        production 27B (67.0/68.7 GB). Gate: the 2nd MI210, or an operator-approved displacement window. Acceptance:
        the GPU device appears in the startup log, speed is within the floor of `production/gpu` on the production 27B,
        output is byte-identical at `n_probs=0`, and draft-mtp `n_probs>0` returns probs on every token. **Standing
        rule: every future champion advance produces BOTH a CPU and a GPU store build of the same commit**
        (single-champion invariant: one commit, one build per device). A CPU-only advance leaves the GPU path on a
        pre-advance build; that is how SW-9 went five days without a GPU build.
      - 2026-09-29 07:05-07:09Z — **attempted in the bundled :8083 window; not completed.** The A/B step
        (`/mnt/raid0/llm/tmp/gpu-champion-ab/`, order P C P on :8197, host threads on 72-79) failed three times in a
        row on over-strict per-arm checks, each before the first probe. No A/B number exists. :8083 was restored on
        v10 each time (thesis handoff ARCHSWAP-4).
        - 07:05Z: the `--slot-save-path` dir was never created, so llama-server rejected the argument.
        - 07:07Z: the device-line regex expected `using device ROCm0` / `offloaded N/N layers`. The v10 server prints
          neither at verbosity 3; its only ROCm line is a sampler-support warning.
        - 07:08Z: the thread-affinity check reported `OUTSIDE:[0..7]`. ROCr's async-event thread (wchan
          `kfd_wait_on_events`) has its affinity reset to 0-191 by the runtime. This is normal: it is identical in all
          four live GPU processes (production :8083 and :8086, whisper, tts).
        - Fixed offline the same day. Every per-arm check (device, placement, `/props`, watcher, sampler) is now an
          `ab_probe.py` subcommand that prints what it saw. `selftest/live_checks.sh` runs each check read-only against
          today's arm logs and the live production servers.
        - **Re-planned for the vision (:8086) window.** That window tests identity, speed and residency only:
          Qwen3-VL has no MTP drafter, so it cannot exercise SW-9.
        - **The SW-9 GPU check (draft-mtp `n_probs>0`) needs an MTP model**: a :8083 window or the 2nd MI210.
      - [x] **V6R-4d.0 — harden the A/B per-arm checks.** ✅ 2026-09-29 — every check (device by KFD VRAM ≥ 1 GB,
            per-thread placement re-checked after the probe, `/props`, a paused-mode watcher, the summary) is an
            `ab_probe.py` subcommand that prints what it saw; `selftest/live_checks.sh` passes 24/24 read-only against
            the arm logs and live :8083/:8086 (`/mnt/raid0/llm/tmp/gpu-champion-ab/`). Lesson:
            INC-20260929-dry-run-missed-live-checks.
      - [x] **V6R-4d.1 — run the champion HIP A/B in the vision (:8086) window.** Tests identity, speed and residency
            (`vision_ab.sh`). Needs a DS41 pause coordinated with workspace-76 over the bus; this is not an operator
            decision.
            ✅ 2026-10-01 — **covered, superseded by V6R-4d.2.** The vision window was planned only because no MTP
            window existed. The production-27B A/B below checks identity, speed and residency on the production
            model itself, plus SW-9, so a separate :8086 run would add nothing.
      - [x] **V6R-4d.2 — the SW-9 GPU check (draft-mtp `n_probs>0` returns probs on every token)** on an MTP model: a
            :8083 window (DS41 pause, workspace-76) or the 2nd MI210.
            ✅ 2026-10-01 — **PASS** (workspace-8d). Run 12:14 to 12:16:40Z in workspace-76's DS41 pause, on the
            production model Qwen3.8-27B Q8_0 with its MTP draft. The MI210 device lock was held for the A/B only.
            - Builds: P = production v10 `kernels/production/gpu` (`gpu-20260921-ffc1bac82`, build_info
              b10303-ffc1bac82); C = champion `kernels/builds/gpu-20260929-90c12df42` (b10308-90c12df42).
            - Arms: P C P on :8197, host threads `-t 8` on cores 72-79, membind 3.
            - Every arm was checked for KFD VRAM residency, its own `libggml-hip` mapped, placement OK, and
              `/props` build_info.
            - pp/tg tok/s: P 886.9/39.01, C 884.4/38.83, P 875.1/39.00.
            - RESULT: `PASS=True; identity C==P True; P-self True; pp_tps_median +0.39% (floor 2.00%);
              tg_tps_median -0.46% (floor 2.00%); sw9_C_all_probs=True; sw9_P_gap=True`. That is, C returns probs on
              every draft-mtp token and v10 P still shows the gap.
            - Restore: production :8083 relaunched on v10 (PID 1677674, slot dir `architect_critic`), /health ok.
            - Evidence: run dir `/mnt/raid0/llm/tmp/gpu-champion-ab/runs/w8083-20261001T121346Z/` (`result.json`
              sha256 `ef3b32b79c043b772abb8cc152f52ceb1f0b4a1d43ea85c399e6676ef18a5821`, schema
              `epyc.gpu_champion_ab.result.v1`); log `/mnt/raid0/llm/tmp/gpu-champion-ab/run_27b_ab_lockonly.log`.
            - Implication: the GPU side of the champion `90c12df42` is no-regression vs v10, with the SW-9 fix
              exercised on GPU. The v11 consequence is recorded under V6R-4a.

#### DO-NOT-FOLD ledger — branches that exist on the CPU lineage and must NOT be picked up by a sweep

| branch @ commit | disposition | why | condition if ever folded |
|---|---|---|---|
| `inf70/sync17-fix2` @ `2516c9807` | **DO NOT FOLD — CLAIM, and the claim is a REGRESSION** | **−2.136%** (ratio 0.9786, CI [0.9771, 0.9804], p=0.0286, n=4v4 in one hot session, 24/24 outputs byte-identical). Both knobs default **ON** on that branch, **and that default IS the regression**. | If ever folded, **both knobs must flip default OFF**. Its value is as an **instrument**, not a keep. |

**Why this negative is admissible where SYNC-19's was not.** The `P` arm is a *directional positive
control*: the knob demonstrably reaches dispatch, confirmed by per-arm server knob readback. Decomposition
of the −2.136%: **C→P (FIX-3's yield alone) −1.883%**; **P→F (column split alone) −0.258%**. The tiny-solo
run was the better choice — the same barrier arithmetic that refuted `inf10-gemv-fusion`. SYNC-19's model
predicted **+3.31%**; the sign is wrong.

- CHAMP-2 (THP shim: KEEP) and CHAMP-3 (multi-launch headline with a session-unit CI) are done (2026-09-08): § *Completed Scope*.

---

## CHAMPION MAXIMUM-PERFORMANCE HEADLINES — 2026-09-08, TWO MODELS (the postable numbers)

**Canonical, citable artifact: [`docs/design/champion-max-performance-20260908.md`](../../docs/design/champion-max-performance-20260908.md).**
Quote from there; do not re-derive from this summary and do not re-type the recipe.

### First headline model — Qwen3.8-27B-Q8_0 (dense, DFlash2 drafter)

Champion `ef81196d5` (everything folded), Qwen3.8-27B-Q8_0, MI210 gfx90a, DFlash2 drafter, canonical serving
recipe `qwen3.8-27b-q8-gpu-dflash2-np4` with **only `np` varied**, 3 launches per point, **residency `proven` on
all 12 launches**, peak VRAM 33.1–43.1 GiB, sclk pinned 1700 MHz. Unit: **LAUNCH**.

| slots (`np`) | aggregate tok/s | per slot | p95 dev across 3 launches | runs |
|---:|---:|---:|---:|---|
| 1 | **79.25** | 79.25 | 0.44% | 79.2, 79.2, 79.6 |
| 2 | 109.41 | 54.70 | 1.60% | 109.4, 108.9, 111.2 |
| 4 | 167.76 | 41.94 | 3.33% | 167.8, 162.2, 169.7 |
| 8 | **179.12** | 22.39 | 1.82% | 182.4, 178.2, 179.1 |

> **79.25 tok/s single user · 179.12 tok/s aggregate at peak concurrency.**

- **`np=4` is the operating point.** The curve turns over hard between 4 and 8 slots: **+6.8% aggregate for
  roughly HALF the per-user rate.** np=4 delivers **93.7% of peak aggregate** while each user still sees
  ~42 tok/s. The canonical recipe is already np=4 — this **confirms** the standing choice, it does not change it.
- **Dispersion GROWS with concurrency** (0.44% at np=1 → 3.33% at np=4). A single reading at np=4 is far less
  trustworthy than one at np=1; anything gated at np=4 must state its `n`. Directly relevant to R23-61.

Raw: `/mnt/raid0/llm/tmp/maxperf-20260908/sweep.json` + `sweep.log`; promoted into the research repo (`data/`) at
commit `48a6f6f2`.

- [x] **HEAD-1 — file the maximum-performance sweep as a canonical citable artifact** ✅ 2026-09-08
      (`docs/design/champion-max-performance-20260908.md`; referenced from this page).

### SECOND HEADLINE MODEL — Qwen3.6-35B-A3B-MTP-Q8_0, same champion, same GPU (2026-09-08 19:37:30-20:14:00Z)

Recipe `qwen3.6-35b-a3b-q8-gpu-mtp` (**new**, research `c3e362a1`), **MTP self-drafting — no separate
drafter**, `draft_n_max=4`, only `np` varied. 24 launches, **residency `proven` 24/24**, 2,952 samples,
sclk flat 1700 MHz at *every* point. Unit: **LAUNCH**. Details and per-point `recipe_hash`:
`docs/design/champion-max-performance-20260908.md` §6.

| slots (`np`) | aggregate tok/s | per slot | p95 dev | peak VRAM | launches |
|---:|---:|---:|---:|---:|---:|
| **1** | **112.68** | 112.68 | **2.70%** | 36.61 GiB | **6** |
| 2 | 130.54 | 65.27 | 1.38% | 36.90 GiB | 3 |
| 4 | 189.57 | 47.39 | 1.13% | 37.50 GiB | 3 |
| 8 | 242.75 | 30.34 | 1.23% | 38.78 GiB | 3 |
| 12 | 268.12 | 22.34 | 1.88% | 40.16 GiB | 3 |
| **16** | **310.96** | 19.43 | 2.53% | 41.37 GiB | 3 |

> **112.68 tok/s single user · 310.96 tok/s aggregate at 16 slots — and 16 slots is the HIGHEST MEASURED
> POINT, NOT the ceiling.**

- **IT HAS NOT SATURATED.** Marginal aggregate gain per step: +15.85% (1→2), +45.22% (2→4), **+28.05%**
  (4→8), +10.45% (8→12), **+15.98%** (12→16). The last step is the *second largest* — the decay is not even
  monotonic. Peak VRAM at np=16 is **41.4 of 64 GiB**, growing ~1.2 GiB per doubling: memory is not the
  constraint either. 24 and 32 slots were offered and the operator declined (*"lets stop here"*). Filed as
  **HEAD-3** so the unfinished curve is a recorded decision, not a gap.
- **IT BEATS THE 27B AT BOTH ENDS — and this is ARCHITECTURE, NOT A KERNEL RESULT.** +42.2% single-user
  (112.68 vs 79.25) and +73.6% peak aggregate (310.96 vs 179.12), despite being the larger file on disk
  (35.21 GiB vs 27.05 GiB, or 28.97 GiB counting the 27B's DFlash2 drafter). **Same binary on both runs.**
  The 27B is `qwen35`, dense, 65 blocks, d=5120, FFN 17408 — every token reads essentially all of it. The 35B
  is `qwen35moe`, 41 blocks, d=2048, **8 of 256 experts routed per token** plus one shared expert of width
  512. Decode is weight-bandwidth-bound, so the rate tracks bytes *read per token*, not bytes on disk.
  **Anyone who reads "35B > 27B" as a kernel result concludes the champion scales with model size, which is
  the opposite of true.**
- **THE TWO MODELS GET DIFFERENT OPERATING-POINT ADVICE, structurally.** The 27B curve turns over at 4→8
  (+6.8% aggregate for ~half the per-user rate) → **np=4**, 93.7% of peak, ~42 tok/s per user. The 35B is
  still climbing at 16 → **np=16** of what was measured, 311 aggregate, ~19 tok/s per user. A dense model
  saturates the memory system early; an MoE at low batch does not, because extra concurrent tokens route
  into expert reads that are already being paid for.
- **THE np=1 SPREAD IS A PROPERTY OF THIS MODEL, NOT A SMALL SAMPLE.** Doubling n did not tighten it:
  2.350% p95 dev at n=3 → **2.696% at n=6** (slightly *wider*). Against the 27B's **0.44%** at the same slot
  count on the same GPU in the same window — a **6.1×** difference. **Every single-user headline for the 35B
  must carry that ~2.7% between-launch dispersion**; a 27B-grade ±0.5% precision is not available on this
  model at np=1 and implying one is a `FLOOR-UNIT-1` violation.

- [x] **HEAD-2 — Qwen3.6-35B-A3B GPU concurrency sweep measured and filed** ✅ 2026-09-08
      (24 launches, residency proven 24/24; recipe `qwen3.6-35b-a3b-q8-gpu-mtp` committed at research
      `c3e362a1`; numbers in `docs/design/champion-max-performance-20260908.md` §6).
- [ ] **HEAD-3 — the 35B concurrency ceiling is UNMEASURED above np=16.** The curve had not saturated
      (+15.98% on the last step, the second-largest of the six) and VRAM stood at 41.4 of 64 GiB. `np=24`
      and `np=32` were offered on 2026-09-08 and the operator said *"lets stop here"* — so this is a
      **recorded decision, not an oversight**. Reopening costs ~2 launches × 2 points ≈ 12 min of exclusive
      GPU. Blocked on nothing but an operator go for the host. Until it is run, **never quote 310.96 tok/s
      as a maximum** — it is the highest measured point.
- [x] **HEAD-4 — promote the 35B sweep out of scratch into the research repo `data/`.** ✅ 2026-09-16
      Research `data/ak-champion-maxperf-35b-2026-09-08/` (JSON/logs/`sweep.py` at `8c5a9652`; the other two
      as-executed scripts, `SHA256SUMS` and a README step correction at `1eb4a89b`). Files byte-identical to
      scratch; every table value recomputed from the JSON and matched `docs/design/champion-max-performance-20260908.md` §6.
      Belief-kernel write-side wiring filed as SC82 in `vidya-belief-substrate-program.md` (the 2026-09-08 sweeps are pre-hook).
- [x] **MTP-27B-1 — the 27B is ALSO MTP-capable, and that is the missing PROD-BASE-1 denominator.** ✅ 2026-09-21
      — v9 measured on the 27B with MTP self-draft (`mtp-Qwen3.8-27B-Q8_0.gguf`, recipe
      `qwen3.8-27b-q8-gpu-mtp`) at ctx 65536: **61.32 / 85.76 / 136.06 / 169.63** across np 1/2/4/8. That IS the
      denominator; the champion on DFlash2 gives 80.87 / 108.75 / 168.64 / 184.48, ratios **1.319 / 1.268 /
      1.239 / 1.088**. Recipe-to-recipe, each kernel at the best configuration it can run (operator direction). The
      Qwen3.8-27B GGUF carries the MTP head (`blk.64.nextn.eh_proj/.enorm/.hnorm/.shared_head_norm`,
      `qwen35.nextn_predict_layers = 1`) — the same shape the 35B has at `blk.40`. It could not be expressed
      as a recipe until `c3e362a1` made `spec_decode.drafter` optional, so it has never been measured through
      the loop. **MTP self-draft is exactly what frozen production supports for this model** (v9 cannot load
      the DFlash2 GGUF at all), so a `qwen3.8-27b-q8-gpu-mtp` recipe is the denominator PROD-BASE-1 needs.
      Write the recipe, sweep `np`, and the champion-vs-production comparison becomes measurable on a lane
      production actually has. Depends on PROD-BASE-1 for the production-side arm; the champion-side arm is
      runnable today. Blocked on nothing but host time.

## ⚠ THERE IS NO CHAMPION-VS-PRODUCTION RATIO FOR THIS CONFIGURATION, AND THERE NEVER WAS ONE

**Production v9 never ran this lane.** `artifacts/operator/ratify_v9_final_freeze_20260811.json` →
`production_certification` records:

| field | value |
|---|---|
| `qwen36_27b_q8_dflash` | `lane_ineligible_acceptance_below_floor` |
| `dflash_kernel_capability` | `certified` |
| `dflash_lineup_enabled` | **`false`** |

So production was frozen with the DFlash drafter **compiled in but deliberately NOT enabled for the 27B** —
acceptance was below floor at the time. The v9 qualification summary
(`artifacts/operator/v9-qualification-20260810T235723Z-0db32c06e/summary.json` →
`gates.gpu_candidate_functional_observation`) carries GPU decode for **other roles only**: architect native MTP
**53.359** tok/s, coder (request_cap 0, no draft activity) **30.268**, worker vision **96.671** — and that block
is itself stamped `decision_grade: false`.

Three separate reasons the comparison does not exist:

1. **Different model.** The key is `qwen36_27b_q8_dflash` — **Qwen3.6**-27B, not 3.8. Qwen3.8-27B replaced
   Qwen3.6-27B-MTP-Q8_0 in production only on 2026-08-20/21, **nine days after** this freeze.
2. **Different drafter, and the frozen binary cannot load ours.** Frozen v9 **rejects the DFlash2 GGUF outright**
   — `wrong number of tensors; expected 81, got 58`. Production's ceiling for Qwen3.8-27B is **MTP self-draft**,
   not DFlash2.
3. **The lane was disabled on purpose.** `dflash_lineup_enabled: false` is a decision, not an omission.

> **The champion's advantage on this surface is partly a CAPABILITY, not a speed delta.** Anyone quoting a
> champion-vs-production ratio for Qwen3.8-27B + DFlash2 is quoting a number that was never measured, because
> production cannot produce the denominator.

- [x] **PROD-BASE-1 — if a champion-vs-production headline is ever wanted, measure production AT ITS OWN BEST.** ✅ 2026-09-21
      Its own `np` sweep, whatever spec configuration it actually supports (MTP self-draft for Qwen3.8-27B),
      under the same host discipline and with residency proven — **never** forcing production through the DFlash2
      recipe, which measures a lane it does not have and would report a capability gap as a speed gap. Until that
      exists, the champion headline stands **alone**, as an absolute number, with no ratio attached. Not blocked
      on anything; not scheduled — it needs the host and an operator go.

## METHODOLOGICAL CAUTION — a BENCH-surface number is not a SERVING number

**Recorded as an error of mine, 2026-09-08.** I quoted the `tg128` llama-bench figures (production 29.4 /
champion 31.0, **+5.63%**) as "single-stream GPU decode". That was wrong.

**`llama-bench` cannot do speculative decoding at all.** `tg128` is therefore a **bench PROXY** for a serving
path that has a drafter in it, and it understates the real single-stream serving rate by **~2.5×**
(**79.25** measured on the recipe vs **31.0** on the bench surface). It also violated the standing rule that
**headline numbers come from the production recipe**.

| surface | valid use | invalid use |
|---|---|---|
| `tg128` / llama-bench | **A/B kernel comparison** — both arms share the surface, so the drafter's absence cancels | **any absolute headline**, any cross-surface ratio, anything the operator would post |
| serving recipe (`serving.calibrate_floor` / the gate) | absolute headlines, operating-point choice, capacity claims | — |

The +5.63% tg128 delta is **not retracted as an A/B** — it remains a valid kernel-vs-kernel comparison on its own
surface. What is retracted is its use as a **rate**. Compiled into the wiki with the R23-58 bounded null.

- [x] **METH-BENCH-1 — the bench-vs-serving distinction is recorded where headlines are formed** ✅ 2026-09-08
      (this page, `docs/design/champion-max-performance-20260908.md`, and the wiki compile).

**RATIFIED INTO THE CONSTITUTION BY THE OPERATOR, 2026-09-08 — this rule is no longer campaign-local.**
The operator ran `scripts/operator/ratify_measurement_bench_vs_serving_20260908.sh --apply`; committed as
`b05c4433` (154 additions to `MEASUREMENT.md`, 35 to the agent digest, zero deletions, no code, no threshold,
no gate behaviour changed). This caution is now **`INSTRUMENT-CLASS-1`** in `MEASUREMENT.md`, alongside
**`FLOOR-UNIT-1`** (a floor carries its `unit`, is calibrated at n≥24, and records `n` and an interval) and
**`BOUNDED-NULL-1`** (a null states the effect sizes its power excludes and cites a both-directions positive
control). `autokernel-rebuild-program.md` → **RATIFY-MEAS-1** is closed.

**The open successor is `RATIFY-MEAS-2`** (`autokernel-rebuild-program.md`): there is **no `P-SERVE-*`
protocol row in the registry**, so every serving number this campaign quotes — including both headlines above —
formally cites no protocol. That is the next amendment, and it was deliberately left out of RATIFY-MEAS-1
rather than smuggled in.
