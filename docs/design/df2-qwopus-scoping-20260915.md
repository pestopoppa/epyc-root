# DF2-QWOPUS scoping: should we train a DFlash2 head for Qwopus3.8-27B-Flash?

**Date**: 2026-09-15 · **Status**: decision memo (desk work only: no inference, no GPU, no process management)
**Owning handoff**: [`dflash2-block-drafter-experimental-build.md`](../../handoffs/active/dflash2-block-drafter-experimental-build.md) → DF2-QWOPUS (index row INF-62)
**Claim grammar**: every number carries its unit, its n and its source. **MEASURED** means a recorded observation.
**PROJECTION** means arithmetic on measured inputs. **UNVERIFIED** means I could not confirm it. Vendor
figures are **CLAIMS** (MEASUREMENT.md).

---

## 0. The decision in one paragraph

**Do not spend card-days on training yet. Qwopus3.8 does not serve anything.** The only
evidence that the base drafter "does not transfer" is **one prompt of 160 tokens**. Run two cheap
gates first, which take GPU-hours and no card-days:

- **K1**: re-measure Qwopus on the DF2-4 12-prompt protocol, with a native-MTP `n-max` sweep, and
  run a quality A/B against Qwen3.8-27B on the architect/coder role suites.
- **K2**: only if K1 passes, run a warm-start pilot of about 1 card-day.

If DFlash2 gets built at all, build it as a **warm-start fine-tune** of the published Qwen3.8-27B
DFlash2 head. Do not train from scratch: a paper-scale run is about 90+ card-days of data generation
alone (§3).

---

## 1. What Qwopus serves

### 1.1 The premise needs correcting: Qwopus serves no role

- **Registry.** `epyc-orchestrator/orchestration/model_registry.yaml` has **0 matches** for `qwopus`
  (grep, 2026-09-15). The MI210 production process `:8083` backs:
  - `architect_general`, the primary role;
  - `coder_escalation`, which is an alias on the same process.

  Both run **Qwen3.8-27B-Q8_0** with `spec_type: draft-mtp`, `draft_max: 8` and a recorded
  `throughput: 47.79` (registry, unit t/s, n not recorded).
- **Origin of the model.** Qwopus3.8-27B-Flash was a **one-off, operator-directed eval** on
  2026-09-05. The record calls it *"One-off eval — not wired to the belief kernel"*
  (`progress/2026-09/2026-09-04-ak-rebuild-20260828.md:118-141`). No active handoff proposes it for a
  role.
- **Traffic share.**
  - Qwopus: **0%**, because it is not registered.
  - `architect_general` / `coder_escalation`: **UNVERIFIED**. I found no routing-share record in
    `handoffs/active`, `docs/design`, `wiki` or `progress/2026-09`.
- **"Serves at 45.7 t/s now" is not a serving figure.**
  - 45.7 t/s is the **base DFlash2 drafter** arm of the one-off bench.
  - The native-MTP arm was **45.5 t/s**.

### 1.2 What a t/s gain is worth there

A Qwopus drafter is worth **nothing** until two things are true:

- **(a) Qwopus earns a role.** On quality, the base rate is against it:
  - Stock Qwen3.6-27B Q8 beat **every** community 27B variant benched on the sealed SWE-oracle-40.
    Results were ThinkingCap 21/40, Fable-Fusion 19/40 and Laguna 17/40, against A3 23/40. That is
    **0 for 3** (`research/intake_index.yaml`, intake-924 notes).
  - Qwopus's own card concedes its MMLU-Pro mixed-set score is **lower than base** (CLAIM,
    [HF card](https://huggingface.co/Jackrong/Qwopus3.8-27B-Flash)).
  - Nobody has measured Qwopus quality on our suites.
- **(b) DFlash2 reaches production.**
  - Frozen v9 **cannot load** a DFlash2 GGUF (`wrong number of tensors; expected 81, got 58`,
    handoff :99-107).
  - DFlash2 exists only on the champion/experimental line. It needs a v10 promotion and a
    lean-registry-compiler change (`autokernel-champion-aggregate.md:418-426`).
  - By contrast, native MTP runs on v9 **today**.

**Is decode speed the binding constraint for the role?** **UNVERIFIED.** The role is an escalation
lane, so per-request latency matters more than aggregate throughput. But I found no record of queueing
or latency complaints on `:8083`. Qwen3.8-27B already has a DFlash2 head and serves on the same card, so
if speed on this role were binding, the lever would be **promoting DFlash2 for Qwen3.8-27B**, not
swapping in a fine-tune.

---

## 2. Expected gain

### 2.1 What the 2026-09-05 Qwopus numbers really are

I read them from the launch scripts still on disk. The raw server logs and response JSONs are **no
longer present** (`/mnt/raid0/llm/tmp/*_qwopus.sh`, checked 2026-09-15).

| arm | script | `--spec-draft-n-max` | workload | n |
|---|---|---|---|---|
| native MTP → 45.5 t/s, acc 0.590, len 3.36 | `mtp_qwopus.sh` | **4** | 1 prompt, `n_predict 160`, temp 0 | **1 run** |
| base DFlash2 → 45.7 t/s, acc 0.356, len 3.46 | `dflash_qwopus.sh` | **8** | the same single prompt | **1 run** |
| raw → 30.3 t/s (tg128) | `bench_qwopus.sh` | — | llama-bench `-r 3` | 3 reps |

Build: `anchor-cabac2563-clean`. The reference row in the handoff (Qwen3.8-27B + DFlash2 ≈ 72 t/s,
2.38×) comes from a **different protocol**:

- DF2-4: 12 olympiadbench prompts, 2048 cap, temp 0.6, **70.0 t/s**, weighted acc **0.62049**
  (19,960/32,168).
- Wiki 2026-09-04: 71.22 / 72.65 t/s.
- Champion headline: **79.25 t/s** at temp 0, `n_predict 384`, n=3 launches
  (`champion-max-performance-20260908.md`).

Three consequences:

1. **"Does not transfer (0.356)" rests on about 160 generated tokens from a single prompt.**
   Olympiadbench-style reasoning and prose give very different acceptance: an external tester
   measured 0.29 on prose against 0.62 for ours on olympiadbench (intake entry for
   incoai/Qwen3.8-27B-DFlash2-GGUF, `contradicting_evidence`). The size of the transfer gap is
   **not established**.
2. **The native-MTP arm ran at n-max 4, not at its tuned depth.** On Qwen3.8-27B, moving n-max from
   4 to 8 was worth **+8.7%** (51.03 → 55.46 t/s, 12 prompts, v9, handoff :119-122).
   `len = 1 + n·acc` checks out exactly: 1 + 4×0.590 = 3.36 and 1 + 7×0.356 = 3.49 ≈ 3.46.
3. The Qwopus MTP head looks **degraded against base** at the same depth:
   - Qwopus: acc 0.590 at n-max 4 (1 prompt).
   - Qwen3.8: acc 0.702 at n-max 4 (12 prompts).

   This fits the intake-924 hypothesis: a head frozen on a moved trunk loses acceptance. The two
   protocols differ, so this is **suggestive only**.

### 2.2 A realistic acceptance range for a trained head

| anchor | acceptance / accept length | source | grade |
|---|---|---|---|
| Base-on-base ceiling on our hardware | **0.620** (7 drafted/step) | DF2-4, 12 prompts, MI210 | MEASURED |
| Vendor Qwen3.8-27B GSM8K: DFlash2 vs its MTP | τ 5.46 vs 5.02 (+8.8%) | [inco.ai blog](https://inco.ai/blog/dflash2/) | CLAIM |
| Vendor card τ on the first 8 GSM8K examples | 5.13 (Q8_0) | incoai GGUF card | CLAIM, n=8 |
| DFlash-1 paper, Qwen3-8B | τ 6.49 greedy / 5.48 temp 1, with 800K samples × 6 epochs | [arXiv 2602.06036](https://arxiv.org/html/2602.06036v2) | CLAIM |
| Community warm-start DFlash2 retrain (GLM-5.3-Flash), 350,260 target-generated samples | τ 3.579 vs reference drafter 3.627 (**98.7%** of reference) | [canada-quant/GLM-5.3-Flash-DFlash2-E](https://huggingface.co/canada-quant/GLM-5.3-Flash-DFlash2-E), 500-prompt holdout | CLAIM |
| NeMo Automodel from scratch, Qwen3.8-27B | accept_len 1.0 → 1.544 after 300 steps (early, not converged) | [NeMo Automodel PR #3605](https://github.com/NVIDIA-NeMo/Automodel/pull/3605) | CLAIM |
| Transfer floor today | 0.356 | 1 prompt, 160 tokens | MEASURED, n=1 |

**Range (PROJECTION)**: a warm-start head fine-tuned on 20–50M Qwopus-generated tokens should land
at **acceptance 0.45–0.60**. The upper anchor is the base-on-base 0.62. The community warm-start
retrain reached 98.7% of its reference with roughly 10× more samples than we can afford, so matching
0.62 on a single card is optimistic. No evidence suggests a fine-tune head would **exceed** the
base-on-base figure.

### 2.3 The resulting t/s range

The model is `t/s ≈ raw × (1 + 7·a) / c`, where `raw` is the undrafted decode rate, `a` is the
acceptance rate and `c` is the per-step cost. It is fitted to two measured DFlash2 points:

- Qwen3.8: 70.0/29.4 at a = 0.620 gives c = 2.24.
- Qwopus: 45.7/30.3 at a = 0.356 gives c = 2.29.

I used c = 2.27 and Qwopus raw = 30.3 t/s. All rows are **PROJECTION, np=1**.

| trained acceptance | projected t/s | vs native MTP 45.5 (n-max 4) | vs projected tuned MTP ~49.5 |
|---:|---:|---:|---:|
| 0.45 | ~55 | +21% | +11% |
| 0.50 | ~60 | +32% | +21% |
| 0.55 | ~65 | +43% | +31% |
| 0.62 (parity) | ~71 | +56% | +43% |

- **Concurrency.** On Qwen3.8, DFlash2 beat MTP by +28% at 1 in-flight request and by +47% at 4 in-flight
  (DF2-5, one run per cell). The np=4 advantage would plausibly be larger, but that is **UNVERIFIED for
  Qwopus**.
- **Tuned MTP ~49.5 t/s** = 45.5 × 1.087, borrowing Qwen3.8's n-max 4→8 gain. Qwopus's lower
  acceptance may shrink that gain, so the plausible range is **46–50 t/s** (PROJECTION).

### 2.4 Do DFlash2 and native MTP compose?

**Within one server for one model they are alternatives. Across the stack they coexist.**

- **One server, one model: alternatives.** Read from the champion source
  (`/mnt/raid0/llm/tmp/fold-ef81196d5-src/common/speculative.cpp:2950-3005, 3180-3245`):
  - `--spec-type` does accept a comma list.
  - The implementations run in a fixed **priority order** (ngram → … → `draft-mtp` → … →
    `draft-dflash`). **The first one that yields a draft wins that step.**
  - Both `draft-mtp` and `draft-dflash` require the single `params.draft.ctx_dft`.
  - So `draft-mtp,draft-dflash` cannot stack. MTP would pre-empt DFlash2 on every step it drafts.
  - Not tested at runtime. This is a source read.
- **Across the stack: they coexist.** One kernel supports both, and each role's server chooses its
  own (`autokernel-champion-aggregate.md:418-426`).

For Qwopus, then, a DFlash2 head **replaces** native MTP. It does not add to it.

---

## 3. Cost

### 3.1 Data

**Paper recipe (DFlash-1, CLAIM)**:

- about 800K samples from Nemotron Post-Training V2 plus CodeAlpaca;
- **responses regenerated by the target**;
- seq len 3072, 6 epochs, AdamW at lr 6e-4;
- online or offline target features;
- H200s, with GPU-hours not stated.

The DFlash2 training data and compute are **not disclosed** (inco.ai blog, z-lab/dflash README). A
public DFlash2 trainer does exist: NeMo Automodel `train_dflash2`, **merged 2026-08-22**. It reproduces
the 81-tensor Qwen3.8 checkpoint layout exactly, and it ran with `sdpa` on 2 GPUs (CUDA) because
`flex_attention` failed.

**Why regeneration dominates.** Target-generated responses are the expensive part, because they come
from decode rather than prefill.

- Qwopus aggregate decode at np=8 is **unmeasured**. As a proxy, Qwen3.8 MTP at 8 in-flight measured
  104.9 t/s and DFlash2 155.0 t/s (DF2-5, one run per cell). I assume **~100 t/s**.
- Response length is assumed to be ~1,000 tokens per sample, borrowed from the community GLM-DFlash2
  recipe ([merryQiao/glm-dflash2](https://github.com/merryQiao/glm-dflash2)). **UNVERIFIED for
  Qwopus**, a "Flash" model trained for shorter reasoning.

| corpus | tokens | generation card-days at ~100 t/s (PROJECTION) |
|---|---:|---:|
| Pilot | 1.5M | ~0.17 (~4 h) |
| Scoped warm-start | 20M | ~2.3 |
| Scoped warm-start | 50M | ~5.8 |
| DFlash paper scale (800K × ~1K) | 800M | **~93** |

**Prompt sources.**

- **Role-matched first**: architect/coder prompts from our own traces or suites. They must be
  era-labelled, and the acceptance-gate prompts (the 12 olympiadbench prompts) must be **held out**.
- **Then public prompt sets**: the same classes the GLM warm-start used (ultrachat_200k,
  OpenR1-Math-220k, OpenCodeReasoning, evol-codealpaca-v1).
- Render every prompt with **Qwopus's own chat template** at the stack's `enable_thinking=false`.

### 3.2 Disk (157 GB free measured, not 178)

`df -h /mnt/raid0/llm` on 2026-09-15 showed **157 G available** (96% used). The "421 GB free" in the
09-05 progress note is stale.

The feature cache per token is **5 taps × 5120 hidden × 2 B (bf16) = 51,200 B/token**. The tap and
hidden sizes come from the drafter GGUF: `target_layers [6,20,34,48,62]`, `embedding_length 5120`.

| corpus | offline feature cache (bf16) | fits in 157 GB? |
|---|---:|---|
| 1.5M tokens | ~77 GB | yes, one shard with headroom |
| 20M tokens | ~1.0 TB | **no** |
| 50M tokens | ~2.6 TB | **no** |
| 800M tokens (paper) | ~41 TB (up to ~123 TB at a full 3072-token average) | **no** |

**Consequence**: a full offline cache is impossible. The only viable plan is a **rolling
capture → train → delete** loop:

- Keep generated token IDs only, at 4 B/token (50M tokens ≈ 200 MB).
- Capture one shard of 1–1.5M tokens.
- Train on it, then delete it.
- Re-capture for each additional epoch.

**Standing disk budget**:

| item | size |
|---|---:|
| one shard | ≤ ~77 GB |
| warm-start source `z-lab/Qwen3.8-27B-DFlash2` BF16 (UNVERIFIED as a safetensors download size) | 3.86 GB |
| one resumable checkpoint (1.9B drafter: bf16 weights + fp32 master + AdamW ≈ 16 B/param) | ~30 GB |
| **total** | **~110 GB** |

That leaves about 45 GB of headroom on a volume other sessions also write to.

### 3.3 MI210-days, and whether the ROCm venv supports the trainer

**Trainer environment.** Two gfx90a training venvs exist and are **verified for SFT/LoRA/GRPO**
(`frontier-f3-data-flywheel.md:38-49`, cleared 2026-08-12):

- `/mnt/raid0/llm/tools/geak-v1-rocm62-py312`: torch 2.5.1+rocm6.2, transformers 5.15.0
- `/mnt/raid0/llm/tools/train-rocm63-py313`: torch 2.7.1+rocm6.3

Neither has NeMo Automodel installed. NeMo Automodel on ROCm and the DFlash2 conv/selector modules
under HIP are **UNVERIFIED**.

**Hard blocker for online training.** Online training with a torch-side target means running the
Qwen3.5-family **Gated DeltaNet** layers in torch on ROCm. Those need flash-linear-attention Triton
kernels or a slow fallback, and FLA-on-ROCm is unproven here (see the declined SGLang FLA torch-ROCm probe,
`mi210-big-model-and-acceleration-roadmap.md` K28-R2). VRAM also blocks it: a BF16 27B target
(~54 GB) plus full training state for a 1.9B drafter (~30 GB) exceeds 64 GB.

**Recommended split.**

- **Capture features with llama.cpp on the Q8_0 GGUF.** GDN already works on HIP there, and the
  features then match the **serving** quant.
- **This needs a small feature-dump tool** on a `llama.cpp-experimental` branch, which is new code
  (UNVERIFIED effort, likely days of desk work, no card-days). The DFlash target-feature path already
  computes exactly these 5 taps.
- **Train in torch on the drafter only.** The target's `token_embd`/`output` tensors get dequantized
  from the GGUF.
- **Conversion back to GGUF already exists**: `conversion/qwen.py:633` registers `DFlash2DraftModel`
  in the champion source.

**Card-day estimate (PROJECTION)**:

| phase | pilot (1.5M tok) | scoped (20–50M tok, 1–2 epochs) |
|---|---:|---:|
| Response generation (~100 t/s) | ~0.17 | 2.3–5.8 |
| Feature capture (prefill ~844 t/s pp512 measured on Qwopus, n=3 reps; rolling) | ~0.02 | 0.3–1.4 |
| Training (1.9B drafter; 6N FLOPs; assumes 20–40 TFLOPS effective on the MI210, UNVERIFIED) | ~0.05 | 0.1–0.6 |
| Convert + DF2-4-protocol acceptance/t/s measurement | ~0.1 | ~0.1 |
| Env bring-up and debugging (NeMo/ROCm, dump tool) | ~0.2 | included |
| **total** | **~0.5–1** | **~3–8** |

**Verdict on the "2–5 days" recon.** It holds only for a **warm-start on ≤ ~25M generated tokens**.
From scratch at paper scale it is about 2 orders of magnitude off.

**Contention.** Generation, capture and training each need the MI210 exclusively. That is the same
card AutoKernel and `:8083` serving use. CPU-side generation on the EPYC is possible in principle, but
its CPU throughput is **UNVERIFIED**, and the CPU is itself campaign-owned.

### 3.4 Risk of drafter, tokenizer or arch incompatibility: LOW, with named residuals

Evidence the risk is low:

- **Arch and tokenizer**: the base Qwen3.8 DFlash2 drafter **loaded and ran coherently against
  Qwopus** on 2026-09-05. That proves `target_layers`, hidden size (5120) and vocab are compatible
  (1 run).
- The card states Qwopus is a Qwen3.8-27B fine-tune and mentions no tokenizer change (CLAIM).

Residual risks:

- **(i) Chat template.** The Jackrong family changed templates across releases (the Qwopus3.6 v2 vs
  Coder divergence, intake-924). Capture must use Qwopus's own template.
- **(ii) Quantized features.** If features are captured from the Q8_0 target, the head trains on
  serving-quant features. That is arguably better, but it departs from the published BF16-trained head.
- **(iii) The shared verify path still has open defects** (DF2-2, DF2-RNG). Those affect any drafter
  equally and are not specific to Qwopus.
- **(iv) Production reachability** (§1.2b): DFlash2 still needs a v10 promotion.

---

## 4. Cheaper alternatives

| alternative | cost | expected gain | notes |
|---|---|---|---|
| **Native MTP n-max sweep {2,3,4,6,8}** on Qwopus | ≤1 GPU-hour | +0–9% → **~46–50 t/s** (PROJECTION) | The 09-05 arm ran at n-max 4. It runs on **frozen v9 today**. |
| **Re-measure base DFlash2 on the 12-prompt protocol** | ~1 GPU-hour | Settles whether 0.356 holds; could show ≥0.45 on reasoning | The existing evidence is n=1 prompt. |
| **Retrain only the Qwopus MTP/nextn head** (1 layer, ~0.42B params; blk.64 is ~451 MB at Q8 by analogy to Qwen3.6, UNVERIFIED for 3.8) | Same generation cost as DFlash2. The cache is ~5× smaller (1 hidden instead of 5 taps). A trainer for qwen35 nextn is UNVERIFIED. | Ceiling ≈ Qwen3.8's own MTP on base, **~55 t/s** np=1 (55.2–55.46 measured on Qwen3.8) | Deploys on **v9 without promotion**. Its ceiling is below DFlash2's. |
| **n-gram drafter** | ~0 | **Do not count on it** | The earlier DF2-6b ngram parity claim was **RETRACTED** because ngram drafted 218 tokens against DFlash2's 4012 (handoff :315-331). NG3 (INF-50) declined ngram **everywhere** after its gain claim was retracted. The acceptance-headroom principle says ngram only fills a weak drafter's headroom, and it adds ~1.6% unconditional cost when composed. |
| **Smaller-scope DFlash2 warm-start pilot** (§5 K2) | ~0.5–1 card-day | Decides go/no-go on the full run | See §5. |
| **Skip** | 0 | 0 | Correct unless Qwopus earns a role. |

---

## 5. Options, recommendation, kill criterion

### Option A — Park DF2-QWOPUS until Qwopus earns a role
- **Cost**: 0 card-days.
- **Gain**: 0.
- **Pro**: no contention with AutoKernel or serving. It follows the 0-for-3 base rate for community
  27B variants.
- **Con**: leaves DF2-DRAFTER-CAPABILITY unbuilt, so the next model that needs a head starts cold.

### Option B — Cheap MTP levers only (n-max sweep, then maybe a nextn-head retrain)
- **Cost**: ≤1 GPU-hour for the sweep. A head retrain would cost about the same as Option C minus
  the 5-tap cache.
- **Gain**: ~46–50 t/s from the sweep. The retrain ceiling is ~55 t/s.
- **Pro**: deploys on **frozen v9**, with no promotion dependency.
- **Con**: the ceiling is ~20–30% below a good DFlash2 head.

### Option C — Staged warm-start DFlash2 fine-tune behind a pilot gate (recommended *if K1 passes*)
- **Cost**: ~0.5–1 card-day for the pilot, then ~3–8 card-days for the scoped run, plus desk work on
  the llama.cpp feature-dump tool and NeMo-on-ROCm bring-up.
- **Gain**: ~55–71 t/s at np=1 (PROJECTION), possibly more at np=4.
- **Pro**: builds DF2-DRAFTER-CAPABILITY once for every future fine-tune.
- **Con**: card contention, and value is gated on both a Qwopus role and a DFlash2 v10 promotion.

### Option D — From-scratch, paper-scale DFlash2 training
- **Cost**: ~93 card-days of generation, and a feature cache of ~41–123 TB that does not fit.
- **Rejected.** It is infeasible on one MI210 and 157 GB of free disk.

### Recommendation

1. **Now, in the next GPU window, ≤ ~4 GPU-hours total, zero training: run K1.**
   - **(a)** Qwopus on the DF2-4 12-prompt protocol, with three arms: none, native MTP at n-max
     {2,4,6,8}, and base DFlash2 at n-max 8. Report weighted acceptance and t/s.
   - **(b)** Quality A/B of Qwopus against Qwen3.8-27B on the `architect_general`/`coder_escalation`
     suites (E-7 terse template; math / mmlu_pro / gpqa_diamond / cruxeval), with no-think on both.
   - **Adopt the best MTP n-max regardless of outcome.** It is free.
2. **Desk work in parallel (no card-days).**
   - Install NeMo Automodel into a *new* ROCm venv. Do not modify the two verified ones: their split is
     deliberate.
   - Run a CPU-only import plus a 1-step forward/backward on a toy DFlash2 config.
   - Draft the llama.cpp feature-dump tool on an experimental branch.
3. **Only if K1 passes → Option C pilot (K2).** Otherwise **close DF2-QWOPUS as Option A** and move
   the capability work to DF2-DRAFTER-CAPABILITY against the next model that actually holds a role.

### Named kill criteria

- **K1 — role gate (cheap, ~4 GPU-hours).** **KILL** if Qwopus does not match or beat Qwen3.8-27B on
  the role suites. "Match" means within the suites' pre-registered noise band; if no band exists, it
  must be stated before the run. Serving speed cannot rescue a role loss. A faster Qwen3.8 is already
  available through DFlash2.
  - **Also KILL** if the 12-prompt base-DFlash2 acceptance on Qwopus comes out **≥ 0.55**. In that
    case the transfer gap is too small to pay for training; ship the base drafter instead.
- **K2 — warm-start pilot (~0.5–1 card-day).** Fine-tune the published Qwen3.8 DFlash2 head on 1.5M
  Qwopus-generated tokens (one rolling shard) and measure on the held-out 12-prompt protocol.
  - **GO** to the scoped run if weighted acceptance is **≥ 0.50**, projected ≈ 60 t/s, i.e. ≥ +20%
    over tuned MTP.
  - **KILL** if it is **< 0.45**, projected ≤ 55 t/s. That is within reach of Option B's nextn
    retrain, which needs no promotion.
  - **Between 0.45 and 0.50**, run one more shard, then apply the same thresholds once.

---

## 6. Proposed handoff and index text (prepared here; the owning session applies it)

**Handoff `dflash2-block-drafter-experimental-build.md`, replacing DF2-QWOPUS body text at :43-49:**

> - [ ] **DF2-QWOPUS — scoped 2026-09-15 → [`docs/design/df2-qwopus-scoping-20260915.md`](../../docs/design/df2-qwopus-scoping-20260915.md). No training card-days until K1 passes.**
>       **Premise correction**: Qwopus3.8 holds **no registry role** (0 matches in `model_registry.yaml`). The
>       09-05 "0.356 does not transfer" figure is **1 prompt / 160 tokens, n=1**, and that MTP arm ran at
>       **n-max 4** (`/mnt/raid0/llm/tmp/mtp_qwopus.sh`).
>       **K1 (next GPU window, ≤4 GPU-h)**: DF2-4 12-prompt protocol on Qwopus with three arms (none /
>       MTP n-max {2,4,6,8} / base DFlash2 n8), plus a role-suite quality A/B vs Qwen3.8-27B at no-think.
>       KILL if Qwopus loses the role A/B, or if base-DFlash2 acceptance comes out ≥0.55 (ship the base drafter).
>       **K2 (only if K1 passes, ~0.5–1 card-day)**: warm-start the Qwen3.8 DFlash2 head on 1.5M
>       Qwopus-generated tokens (rolling shard, ~77 GB). GO at weighted acceptance ≥0.50; KILL below 0.45.
>       From-scratch training is REJECTED (~93 card-days of generation; the 41+ TB cache cannot fit in 157 GB free).

**Index row INF-62, `Next action` cell (thin):**

> DF2-QWOPUS K1: Qwopus 12-prompt none/MTP-nmax-sweep/base-DF2 + role quality A/B vs Qwen3.8, no training until K1 passes (docs/design/df2-qwopus-scoping-20260915.md); then DF2-6b-bis, DF2-2

---

## Sources

- Local:
  - `handoffs/active/dflash2-block-drafter-experimental-build.md`
  - `handoffs/active/speculative-decoding-mtp-refresh.md`
  - `handoffs/active/autokernel-champion-aggregate.md`
  - `handoffs/active/frontier-f3-data-flywheel.md`
  - `docs/design/champion-max-performance-20260908.md`
  - `progress/2026-09/2026-09-04-ak-rebuild-20260828.md`
  - `research/intake_index.yaml`: intake-158, intake-737, intake-924, and the incoai DFlash2 GGUF and PR #27342 entries
  - `research/deep-dives/dflash-dart-diffusion-speculation.md`
  - `epyc-orchestrator/orchestration/model_registry.yaml`
  - champion source `/mnt/raid0/llm/tmp/fold-ef81196d5-src/{common/speculative.cpp,common/arg.cpp,conversion/qwen.py}`
  - `/mnt/raid0/llm/tmp/{mtp,dflash,bench}_qwopus.sh`
- External (fetched 2026-09-15; every figure is a CLAIM):
  - [arXiv 2602.06036](https://arxiv.org/html/2602.06036v2)
  - [inco.ai/blog/dflash2](https://inco.ai/blog/dflash2/)
  - [z-lab/dflash](https://github.com/z-lab/dflash) (no training recipe published)
  - [NeMo Automodel PR #3605](https://github.com/NVIDIA-NeMo/Automodel/pull/3605)
  - [canada-quant/GLM-5.3-Flash-DFlash2-E](https://huggingface.co/canada-quant/GLM-5.3-Flash-DFlash2-E)
  - [merryQiao/glm-dflash2](https://github.com/merryQiao/glm-dflash2)
  - [Jackrong/Qwopus3.8-27B-Flash](https://huggingface.co/Jackrong/Qwopus3.8-27B-Flash)
