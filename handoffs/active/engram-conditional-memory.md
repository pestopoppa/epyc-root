# Engram — Conditional Memory via Scalable Lookup

**Status**: active (Track A closed negative; Track B proxy open)
**Created**: 2026-05-24 (via research intake)
**Updated**: 2026-06-12 (stale Track A queue reconciled with decision log)
**Categories**: memory_augmented, hardware_optimization, moe_optimization
**Owner**: TBD

## Current State & Next Action (TL;DR)

**Where we are**: Track A LongCat-Flash-Lite CPU probe closed negative on 2026-05-25. The model ran at production-relevant CPU rates, but gemma4-MTP dominated it on both decode speed and sentinel quality for `worker_general`; it is not a production replacement candidate on this stack. Track B Phase 0a CPU prep is complete and remains a separate research bet.
**Next action**: Track B Phase 0b GPU proxy only when ready to spend ~$50-150 on cloud/GPU time. The remaining inference-free debt is the Track A negative deep-dive/reporting update, not another Track A probe.
**Owner**: TBD — needs assignment.

If you are an agent landing on this doc and being asked to "make progress on Engram", do not restart Track A. Start with either the Track A negative deep-dive/reporting update, or Track B Phase 0b if a clean GPU budget/window has been explicitly authorized.

## Objective

Two tracks, **sequenced** (not parallelized at the start):

- **Track A — LongCat-Flash-Lite CPU probe** (low-effort, week-scale, RUN FIRST): get a production-deployed Engram-family architecture running on our EPYC stack as the first measurable Engram-style POC anywhere on CPU. Working GGUFs and a fork already exist; this is mostly download + build + measure.
- **Track B — Frozen-backbone Engram retrofit** (high-effort, month-scale research bet, GATED ON TRACK A + PROXY DERISK): graft a paper-faithful Engram layer onto a frozen Qwen3.6 backbone, train only the n-gram table + projections + conv + gate. The paper provides no direct evidence this works, so derisk on a 1.5B proxy before committing to Qwen3.6 surgery.

Hardware fit is the through-line motivation: EPYC 9655 with 1.1 TB DDR5 and ~460 GB/s aggregate BW makes us, in principle, the **best-provisioned single node on Earth** for an inference architecture where 25–46% of "sparse" parameters live in a deterministic-lookup table that wants ~10 KB/token of memory bandwidth.

## Sequencing Decision

```
                ┌──────────────────────────────┐
                │  Track A — Phases 0-5        │
                │  (LongCat CPU probe)         │
                │  ~1-2 weeks, no GPU needed   │
                └─────────────┬────────────────┘
                              │
                ┌─────────────▼────────────────┐
                │  Gate A: ≥35 t/s decode +    │
                │  quality ≥ Qwen3-30B-A3B?    │
                └─────────────┬────────────────┘
                              │
              ┌───────────────┴───────────────┐
            FAIL                             PASS
              │                                │
   ┌──────────▼──────────┐    ┌────────────────▼──────────────────┐
   │ Archive Track A,    │    │ START Track B Phase 0 (proxy)     │
   │ document negative.  │    │ IN PARALLEL with Track A Phase 6  │
   │ Reconsider Track B  │    │ deeper eval. Both run for ~1 week.│
   │ ONLY if user wants  │    └────────────────┬──────────────────┘
   │ pure-research bet.  │                     │
   └─────────────────────┘     ┌───────────────▼─────────────────┐
                               │  Gate B0: frozen-Engram         │
                               │  recovers ≥30% of co-trained    │
                               │  Engram gain on 1.5B proxy?     │
                               └───────────────┬─────────────────┘
                                               │
                                ┌──────────────┴───────────────┐
                              FAIL                            PASS
                                │                              │
                     ┌──────────▼──────────┐         ┌─────────▼──────────┐
                     │ Archive Track B,    │         │ Track B Phases 1-4 │
                     │ document negative.  │         │ (Qwen3.6 retrofit) │
                     │ Track A may still   │         │ ~1 month, GPU req. │
                     │ produce a worker    │         └────────────────────┘
                     │ candidate.          │
                     └─────────────────────┘
```

**Why this sequencing:**

1. **Track A is cheap to falsify and binary-informative.** If a production-deployed Engram-family checkpoint can't beat our deployed worker on CPU, that's a strong signal the entire family doesn't pay for itself in our regime — and it's a much stronger signal against Track B than anything the paper provides, because Track A measures *deployed reality* on *our exact hardware*.
2. **Track A success ≠ Track B validation** (the architectures differ — see comparison table below). But Track A success means the *primitive* of n-gram-lookup-augmented MoE inference is viable on CPU, which is a necessary precondition for Track B being worthwhile to pursue.
3. **Track B Phase 0 proxy derisk is independent of Track A's deeper evaluation** — once Gate A passes, the two can run truly concurrently: a single contributor on a rented H100 for proxy training, and a different (or same) contributor on EPYC for the deeper LongCat quality run. They share no compute and no codebase.
4. **Track B Phases 1-4 (Qwen3.6 surgery) require both gates passing.** This is the only multi-week-of-engineering commitment in either track; gate it hard.

## Research Context

| Intake ID | Title | Relevance | Verdict |
|-----------|-------|-----------|---------|
| intake-599 | Conditional Memory via Scalable Lookup (DeepSeek+PKU, arxiv:2601.07372) | high | new_opportunity |
| intake-600 | Pooling Engram Conditional Memory using CXL (workshop, arxiv:2603.10087) | low | worth_investigating |
| intake-502/504 | LongCat-Flash family (Meituan) — Lite variant ships Engram-style n-gram embeddings in production | medium | active POC candidate |

---

## What the Deep-Dive Established

### Architecture (paper-faithful version)

- **Hash:** multiplicative-XOR per-head, `hash = (Σ XOR_k t_k·m_k) mod P_head`. 64-bit ints. **K=8 distinct hash heads** per n-gram order. Per-head moduli are distinct primes just above `engram_vocab_size`. Collisions within a head are not resolved — the K-head ensemble + gating is the entire mitigation.
- **Keys:** 2-gram + 3-gram suffixes of *canonicalized* token IDs. DeepSeek's canonicalization map P collapses ~23% of vocab (NOT publicly released; would need to be rebuilt for any non-DeepSeek tokenizer).
- **Embedding dim:** `d_mem = 1280`. Concatenated across (n, k) heads → 2·8·1280 = 20,480-wide vector, projected by W_K / W_V to d_model.
- **Injection:** 27B is 30 layers; reference config uses layers [2, 15] but ablation reports [2, 6] is *better*. So early-layer insertion is critical — the paper hypothesizes Engram "relieves the backbone's early layers from static reconstruction."
- **Path:** scalar sigmoid gate (`α_t = σ(RMSNorm(h)·RMSNorm(W_K·e)/√d)` with a sqrt-signed-magnitude squash before sigmoid) → gated value → depthwise causal Conv1D (kernel=4, dilation=3, SiLU) → residual add into the stream *before* Attention and MoE at the inserted layer.
- **Zero-init:** Conv weights are zero-initialized so the model = un-augmented backbone at step 0. **NOT in the released demo code — must be added (2 lines).**

### Architecture (LongCat-Flash-Lite production deviation — IMPORTANT)

LongCat is *not* a paper-faithful reproduction. The differences:

| Aspect | Paper Engram | LongCat-Flash-Lite |
|---|---|---|
| Injection points | Per-layer at [2, 15] or [2, 6] | **Input embedding only** (1-shot) |
| Gate | Scalar sigmoid, content-aware | **None** — pure additive |
| Conv path | Depthwise causal Conv1D, kernel=4 dilation=3 | **None** |
| Normalization | RMSNorm × 2 inside gate | Divide by 13 (= 1 + 4·3) |
| n-gram orders | 2, 3 | **2, 3, 4** |
| Hash heads | 8 per order | **4 per order** (`emb_split_num=4`) |
| Hash function | Multiplicative-XOR | **Polynomial rolling hash** |
| Tokenizer | DeepSeek-V3 (128k vocab, canonicalized) | Custom LongCat (131k vocab, no canonicalization) |
| Slot count | ~280k/head (27B) | `78 × 131072 ≈ 10.2M`/head |
| Active params | 27B/40B research | 2.9–4.5B active / 68.5B total (~31.4B in n-gram tables) |

**Net:** LongCat is a simpler, cheaper, input-only "Engram-Lite." It validates that *some* version of n-gram-keyed memory works in production at MoE-scale, but it does NOT validate the paper's gating-and-conv mid-layer-injection path. Track A is a POC of the *family*, not a reproduction of the *paper*.

### Bandwidth + RAM math (from CXL follow-up paper)

- ~10 KB/token total at FP8 for paper-config (2 layers × 5 KB) at 70k tok/s → 0.7 GB/s lookup BW. **<0.2% of our DDR5 aggregate.**
- 100B-param embedding table → ~50 GB at FP8, ~100 GB at FP16. We have 1.1 TB headroom.
- LongCat-Flash-Lite at Q4_K_M: 37.4 GB on disk, ~51 GB resident with KV cache and activations. Trivial.

### Repo state (deepseek-ai/Engram)

- **422 lines** of Python in `engram_demo_v1.py`, plus paper PDF, figures, drawio. Nothing else.
- License: Apache-2.0 (safe to vendor).
- Maintainer dropped after day 3 (no engagement since 2026-01-14). 20 open issues, 0 closed. Open issue #16 "training code" — unanswered. Open issue #9 asking about LR scaling — unanswered.
- The Engram **module itself** is real and reusable (~250 LoC of substantive logic).
- **Missing:** training loop, dataloader, optimizer config, backbone-freeze hooks, zero-init, KV-cache support, PCIe prefetch / CUDA kernels, eval scaffolding. All of these the paper *describes* but did not release.
- Bug noted in open PR #15: `torch.from_numpy(...)` forces CPU-only execution; hash needs torch port for GPU.

### LongCat-Flash-Lite tooling state

- **Weights:** `meituan-longcat/LongCat-Flash-Lite` (HF, MIT license, BF16, ~138 GB).
- **GGUF:** `InquiringMinds-AI/LongCat-Flash-Lite-GGUF` (Q3_K_L through BF16; Q4_K_M = 37.4 GB recommended). Quality note from publisher: hallucination rate climbs sharply ≤Q3, n-gram tables are quant-sensitive.
- **llama.cpp fork:** `InquiringMinds-AI/llama.cpp` branch `longcat-flash-ngram`, head `56abe857` (2026-04-27). ~903 LoC delta across 15 files. **Cannot be upstreamed** — publisher disclosed it was Claude-Code-generated, which violates llama.cpp's AI-policy. Fine for our local use.
- **Upstream llama.cpp:** PRs #19167 + #19182 stalled draft since Jan, blocked on the base architecture not being landed first.
- **ik_llama.cpp:** zero LongCat code. Skip — use the InquiringMinds mainline fork.
- **vLLM:** issue #33528 open, no resolution. Memory overhead loading the 31.4B n-gram embedding remains a complaint.
- **CPU performance reports anywhere:** **none.** We would be the first.

---

## Track A — LongCat-Flash-Lite CPU Probe

### Hypothesis

LongCat-Flash-Lite Q4_K_M runs on EPYC 9655 NPS4 at ≥35 tok/s decode with quality ≥ Qwen3-30B-A3B on MMLU. If yes → file follow-on to evaluate against gemma4-26B-A4B MTP in the worker_general role. If no → publish the negative result, free the slot.

### Phase plan

**Phase 0 — Confirm freshness** (≤30 min, no compute)
- Check InquiringMinds GGUF repo head + llama.cpp fork branch still at `56abe857`.
- Confirm upstream PRs #19167 / #19182 still draft (no surprise landing that obsoletes the fork path).

**Phase 1 — Fetch** (bandwidth-bound, ~30 min)
- `huggingface-cli download InquiringMinds-AI/LongCat-Flash-Lite-GGUF LongCat-Flash-Lite-Q4_K_M.gguf` → `/mnt/raid0/llm/models/longcat-flash-lite-q4km/`.
- Verify sha256 against the HF README.
- Optionally fetch Q5_K_M (44.7 GB) as a quality reference; defer Q8_0 unless Q4_K_M shows quality concerns.

**Phase 2 — Build the fork** (~30 min)
- Clone `https://github.com/InquiringMinds-AI/llama.cpp` into `/mnt/raid0/llm/llama.cpp-experimental` per `feedback_experimental_repo.md`. Add as remote on the existing experimental tree if cleaner.
- Branch `longcat-flash-ngram`. Verify our existing experimental patches don't conflict (check the rebase log).
- Build with AOCC + AVX-512 + no CUDA + `KMP_BLOCKTIME=10` env. NPS4-native.
- Smoke-build `llama-cli`, `llama-bench`, `llama-server`.

**Phase 3 — Smoke test** (user-launched per `feedback_no_concurrent_inference.md`)
- Prepare (do not run unprompted):
  ```
  llama-cli -m longcat-flash-lite-q4km.gguf -p "What is 2+2?" -n 32 \
    -t 96 --numa distribute -fa 1 --no-display-prompt
  ```
- Sanity-check on user's go: no crash, non-garbage output, BPE pre-tokenizer warning absent (verify hash registered per InquiringMinds commit `e0ae3c14`).

**Phase 4 — Speed verify** (user-launched, `llama-bench` only — per `feedback_speed_verify_via_llama_bench.md`)
- Prepare commands for decode-only (`-n 128`) at 1K/4K/16K context, with full OMP env stack per `feedback_omp_env_stack_required.md`:
  ```
  OMP_PROC_BIND=spread OMP_PLACES=cores OMP_WAIT_POLICY=active \
  KMP_BLOCKTIME=10 numactl --interleave=all \
  llama-bench -m … -t 96 -fa 1 -n 128 -p 1024,4096,16384
  ```
- Record decode t/s. Falsification thresholds:
  - **<15 t/s** → n-gram path is broken or serialized; investigate or abandon.
  - **15–35 t/s** → working but not competitive with deployed Qwen3-30B-A3B (49 t/s); document and stop.
  - **≥35 t/s** → proceed to quality gate.
  - **≥60 t/s** → escalate priority, this is genuinely interesting.

**Phase 5 — Quality gate** (user-launched, manual or scripted via existing eval infra)
- 20-question MMLU subset + 5 agentic prompts (matched against an internal task we already use Qwen3-30B-A3B for).
- Compare blind. If LongCat ≥ Qwen3-30B-A3B on average → proceed.
- Watch for the published agentic weak spot (Meituan reports VitaBench = 7.0, very low).

**Phase 6 — Decision**
- Pass-all → file new handoff `longcat-engram-worker-evaluation.md` scoping a vs gemma4-MTP comparison in worker_general.
- Any-fail → write findings to `research/deep-dives/longcat-flash-lite-engram-cpu-poc.md`, update intake-504 contradicting_evidence with the verified measurement, archive this track of the handoff.

### Open risks for Track A

- **Quant sensitivity of n-gram tables.** Embedding tables typically prefer Q6_K+. Q4_K_M may degrade the lookup quality more than the backbone. If quality fails, retry at Q5_K_M before declaring negative.
- **n-gram cache thread safety.** If the InquiringMinds fork doesn't per-thread-isolate or lock the rolling-hash context, expect output corruption at high thread counts. Spot-check by running -t 12 vs -t 96 with same seed.
- **Zero-experts kernel.** Top-12 routing into 256 routed + 128 zero-experts should emit 0 FLOPs for zero-expert slots. If the kernel naively runs them, expect ~50% wasted decode.
- **Architectural variance.** LongCat is not paper-faithful (see comparison table). A positive result on Track A does **not** validate the paper's Engram for Track B purposes — it only validates the family.

---

## Track B — Frozen-Backbone Engram Retrofit (Research Bet)

### Hypothesis

A paper-faithful Engram layer (multiplicative-XOR hash + 8 heads × bigram/trigram + gated value + zero-init depthwise conv + residual add) inserted at the early layers of a *frozen* pretrained backbone can recover a meaningful fraction (≥30% derisk gate; ≥50% target) of the joint-training gain reported in the paper — measured on a small-scale proxy first, then promoted to Qwen3.6 or gemma4 if proxy passes.

### Why the paper provides only weak support

- **No frozen-backbone ablation in the paper.** The closest is §6.3 post-hoc Engram suppression which shows the *co-trained* backbone has learned to delegate to Engram. The complement — backbone never given the chance to delegate — is unstudied.
- **§6.2 finds Engram works best at early layers** (layer 2 best single-insertion; [2, 6] beats [2, 15]) precisely because it "relieves the backbone's early layers from static reconstruction." Once a pretrained backbone has already done that reconstruction with its dense FFNs, there is structurally less headroom.
- **Zero-init conv is gradient-compatible** with frozen backbone: at step 0 Y = 0 → no perturbation. Gradients flow into Engram parameters cleanly. This is the architectural reason to hope.
- Plausibly some fraction of paper's gain is "more compute at early layers" (which a frozen backbone can't get), and some fraction is "the table contents" (which a frozen backbone *can* learn). Ratio is unknown.

### Phase plan

**Phase 0 — Proxy derisk** (≤1 week, single H100/A100)
- Backbone: a 1.5B-parameter open model with clean public tokenizer (TinyLlama / SmolLM-1.7B). Freeze entirely.
- Engram: copy the demo's `Engram` module verbatim, add the missing zero-init for `short_conv.conv.weight` and `value_proj.weight`. Replace numpy hash with torch hash (PR #15 reference) so it runs on GPU.
- Insertion: a single Engram layer at depth ~2 (early). Optionally test [2, layer_floor(N/2)] as a second config.
- Data: 5–20 B tokens from FineWeb-Edu or RedPajama-v2. Match the paper's batch/seq if possible.
- Two-group AdamW: backbone (frozen — gradients masked or `requires_grad=False`), Engram (lr=5×backbone-equivalent, wd=0).
- **Reference comparator**: also train a tiny co-trained Engram model on the same data budget (same arch, but backbone unfrozen) so we can compute the frozen-fraction-of-gain ratio.
- **Gate**: frozen-backbone Engram recovers ≥30% of co-trained-backbone gain on held-out PPL and a 2-task eval (MMLU subset + LAMBADA). Below 30% → abandon Track B, document negative.
- Cost: ~24–48 H100-hours total, ~$50–150 cloud.

**Phase 1 — Tokenizer canonicalization** (if Phase 0 passes; ~2 days)
- The paper's vocab-canonicalization map P (~23% reduction) is NOT released. Rebuild for the chosen target tokenizer using lightweight rules: Unicode NFKC + case fold + whitespace normalize + punctuation collapse. Validate that the collapsed-vocab Engram doesn't degrade vs raw-vocab on Phase 0 setup before scaling.
- The repo's `CompressedTokenizer` (built on DeepSeek-V3's tokenizer) is a reusable template — swap the underlying `AutoTokenizer.from_pretrained(...)` and re-run the normalizer chain.

**Phase 2 — Layer-injection selection** (~2 days)
- For Qwen3.6 (64 layers) and gemma4-26B-A4B (target backbones), run a CKA-style alignment probe: which layers' representations most resemble the "shallow Engram-input" layers of the proxy that worked best? Inject there. Hypothesis: layers ~[2, 12] or [2, 32] for Qwen3.6; we'll let CKA decide.

**Phase 3 — Full-scale training** (if Phase 0–2 derisk; ~1–2 weeks single H100 OR ~3–5 days on 2× H100 FSDP)
- Backbone: Qwen3.6 (we have it deployed, tokenizer known, eval baselines established). Alternative: gemma4-26B-A4B (MTP path is well-understood).
- Engram-table sizing: target ~5–10% of backbone params (proxy result will refine this — paper's 25% is for co-training; frozen retrofit likely tolerates less).
- Training budget: ~20–50 B tokens. The Engram table is BW-cheap to train (sparse updates), the cost is dominated by backbone forward passes.

**Phase 4 — Inference deployment** (only if Phase 3 passes)
- Bake the Engram-extended Qwen3.6 to GGUF. This requires the Track A llama.cpp fork *plus* the paper-faithful gating-and-conv path (LongCat fork doesn't have these; we'd add them on top).
- Run on EPYC under our standard NPS4 + 96t + Q4_K_M operating point. The lookup BW is negligible (~0.7 GB/s) so decode speed should be ≈ backbone decode minus a small per-token gate+conv overhead.

### Required net-new engineering work (Phase 0)

| Component | Source |
|---|---|
| `Engram` module (hash + multi-head embed + gate + value_proj + short_conv) | **vendored from deepseek-ai/Engram** (~250 LoC, clean) |
| Zero-init of conv + value_proj weights | **add 2 lines** (not in repo) |
| GPU hash (replace numpy with torch ops) | **port from open PR #15** (~30 LoC) |
| HF forward-hook to splice Engram into chosen backbone layer | **write new** (~50 LoC) |
| Backbone freeze (`requires_grad=False`) | **write new** (~5 LoC) |
| Two-group AdamW (Engram lr=5×, wd=0) | **write new** (~10 LoC) |
| Dataloader + collator | **write new** (~30 LoC, stock HF) |
| Eval scaffolding (lm-eval-harness wiring) | **write new** (~50 LoC) |
| Logging (W&B or local TB) | **write new** (~20 LoC) |

**Total: ~400 LoC of new glue around ~280 LoC of vendored code. A one-week spike to a first proxy curve, single contributor, single GPU.**

### Falsification criteria (kill switches)

- Phase 0 proxy frozen-Engram recovers <30% of co-trained-Engram gain → **abandon Track B**, write up negative result.
- Gate α_t collapses to 0 (Engram unused) across most tokens during proxy training → indicates LR too low or gate normalization wrong; tune once, then if still failing → **abandon**.
- Phase 0 passes but Phase 1 tokenizer-canonicalization-rebuilt Engram regresses below raw-vocab baseline → **stay with raw vocab**, accept the larger table size.
- Phase 3 full-scale Engram-extended Qwen3.6 fails to beat baseline Qwen3.6 on held-out PPL → **archive, don't deploy.**

### Open risks for Track B

- **The paper might be wrong about retrofit feasibility being plausible.** §6.3 result is the strongest counter-signal we have. The proxy derisk in Phase 0 is the load-bearing gate; do not commit further compute without it.
- **Privacy/extraction risk** from deterministic n-gram memorization. Not blocking for self-hosted research, but worth flagging if outputs ever surface externally.
- **Training-data quality.** The paper's 262 B tokens are presumed DCLM-grade. Lower-quality data could starve the table.
- **GPU availability.** Phase 0 needs an actual GPU (rent or borrow). EPYC alone is not viable for the training step.

---

## Pointers

- Paper: https://arxiv.org/abs/2601.07372 / HTML: https://arxiv.org/html/2601.07372v1
- ar5iv mirror: https://ar5iv.labs.arxiv.org/abs/2601.07372
- CXL follow-up: https://arxiv.org/abs/2603.10087 (where the 5 KB/token/layer + 0.7 GB/s figure comes from)
- Demo repo: https://github.com/deepseek-ai/Engram (Apache-2.0, 422 LoC, abandoned by maintainers)
- LongCat-Flash-Lite weights: https://huggingface.co/meituan-longcat/LongCat-Flash-Lite
- LongCat GGUF: https://huggingface.co/InquiringMinds-AI/LongCat-Flash-Lite-GGUF
- LongCat llama.cpp fork: https://github.com/InquiringMinds-AI/llama.cpp tree `longcat-flash-ngram` head `56abe857`
- Upstream PRs (stalled): https://github.com/ggml-org/llama.cpp/pull/19167 and https://github.com/ggml-org/llama.cpp/pull/19182
- vLLM issue: https://github.com/vllm-project/vllm/issues/33528
- Third-party detailed writeup: https://arxiviq.substack.com/p/conditional-memory-via-scalable-lookup

## Decision Log

Append a line for each gate outcome. Format: `YYYY-MM-DD | <gate> | <result> | <evidence link> | <decision>`

- `2026-05-24 | Phase 0 freshness (Track A) | PASS | gh API: fork head 56abe85 unchanged, PRs #19167/#19182 still draft | proceed to Phase 2 build`
- `2026-05-24 | Phase 2 build (Track A) | PASS | cmake exit 0 in /mnt/raid0/llm/llama.cpp-longcat-probe (worktree on probe/longcat-build tracking inq/longcat-flash-ngram) | ready for Phase 3 GGUF probe, pending user approval per feedback_no_concurrent_inference.md`
- `2026-05-24 | Phase 0a Track B (identity-at-step-zero invariant) | PASS | 36/36 unit tests pass in 0.36s on CPU; engram-spike commit e3b88f0c in epyc-inference-research; max abs Engram output after identity init = 0 (atol 1e-6) on non-zero hidden states | architectural feasibility of frozen-backbone retrofit confirmed at step 0; proceed to GPU rental for Phase 0 proxy training when ready`
- `2026-05-25 | Phase 3 smoke (Track A) | PASS | LongCat-Flash-Lite Q4_K_M loads via InquiringMinds fork, "What is 2+2?" → "4" via /v1/chat/completions on port 8500 | proceed to bench`
- `2026-05-25 | Phase 4 speed (Track A, llama-bench, 96t -fa 1 -ub default, NPS-interleaved) | MIXED | LongCat-Lite Q4_K_M: pp512 322.65 t/s, pp4096 258.33 t/s, tg128 37.08 t/s. Qwen3.6-35B-A3B Q8 (frontdoor): pp512 439.31 t/s, pp4096 435.51 t/s, tg128 25.17 t/s. gemma4-26B-A4B Q4_K_M no-MTP (worker_general core): pp512 957.82 t/s, pp4096 891.39 t/s, tg128 47.71 t/s. gemma4-MTP production-measured 76.5 t/s (memory project_worker_general_swap_2026_05_08). | speed gate: above abandon threshold (15) but below escalate (60); LongCat decodes +47% vs Qwen3.6 frontdoor, −51% vs gemma4-MTP worker. Proceed to quality gate ON THE WORKER COMPARATOR since the speed gap to gemma4-MTP is the binding constraint.`
- `2026-05-25 | Phase 5 quality (Track A, sentinel_questions.yaml = 39 questions, --max-tokens 2048, --temperature 0) | FAIL vs worker, PASS vs frontdoor (likely) | LongCat-Lite Q4_K_M: 21/39 = 53.8%. gemma4-26B-A4B Q4_K_M MTP: 26/39 = 66.7%. **gemma4 dominates LongCat by +12.9pp.** Suite-level: gemma4 wins +4 on math (4/6 vs 0/6), +1 on instruction (4/4 vs 3/4), +1 on gpqa, +1 on thinking. LongCat wins +2 ONLY on hotpotqa. Both tie at agentic 1/3 = 33% (poor — both struggle on tool-use sentinels). LongCat's math 0/6 confirmed structural (not truncation — at 2048 tokens still 0/6); model generates correct-looking step reasoning but final-answer formatting diverges from expected literal. Qwen3.6 eval skipped — speed numbers + role context already determine the decision. Results: /mnt/raid0/llm/epyc-inference-research/research/engram-spike/eval/longcat-results-2048.json + gemma4-results.json. | LongCat is dominated by gemma4-MTP on BOTH axes (slower decode AND lower sentinel quality). It does NOT pass Gate A as a worker_general candidate.`
- `2026-05-25 | Phase 6 decision (Track A) | TRACK A CLOSED — NEGATIVE | LongCat-Flash-Lite Q4_K_M is not a viable replacement for any current production role on our stack: (a) worker_general — dominated by gemma4-MTP on both speed and sentinel quality; (b) frontdoor (Qwen3.6-35B-A3B Q8 at 25 t/s decode) — LongCat is +47% faster on decode but only 53.8% on sentinel including 33% agentic; for an agentic-routed frontdoor the quality regression isn't worth the speed bump. **Family verdict (not paper-faithful verdict): n-gram-augmented MoE inference on CPU IS technically viable at production-relevant rates (37 t/s decode on Q4_K_M 68B/4.5B-active) — we just happen to have better-tuned alternatives already deployed for our specific stack.** Track A archives without taking down our worker. | Write up findings to research/deep-dives/longcat-flash-lite-engram-cpu-poc.md; update intake-504 contradicting_evidence with the verified accuracy + speed numbers; Track B (frozen-backbone retrofit research bet) is unaffected — it's a different architecture (paper-faithful Engram, not LongCat's simplified input-only variant) and a different optimization (training own model, not adopting an existing checkpoint). Track B decision stays "proceed to Phase 0b GPU proxy when ready".`

## Anti-Rationalization (for this work specifically)

Recurring failure modes worth pre-empting:

| Tempting shortcut | Why it's wrong |
|---|---|
| "Track A passed speed gate, let's skip the quality gate and start using LongCat in production." | Speed without quality is a regression. Engram's headline benefit is *quality*, not speed; treat MMLU/agentic gate as binding. |
| "The paper says retrofitting should work because zero-init is gradient-compatible, let's skip Phase 0 proxy." | The paper says no such thing — it *omits* the retrofit ablation. Zero-init buys gradient-compatibility, not result-compatibility. The proxy derisk is the only direct evidence we'll have. |
| "Frozen-Engram recovered only 20% of co-trained gain on the proxy, but on a bigger backbone it'll be different." | The proxy is a *necessary* condition; small-scale wins generalize unevenly to large scale, small-scale losses almost always do generalize. <30% on the proxy = abandon. |
| "We can use 4-bit Engram tables on Phase 0 to save time." | Quantization sensitivity of the n-gram table is *unstudied* by both the paper and LongCat. Phase 0 must train + eval at full precision (bf16) to keep the measurement clean. |
| "Let's just try injecting Engram into Qwen3.6 directly — skip the proxy, the LoC is small." | The LoC is small but the *compute cost* of a 64-layer 36B-active forward+backward at scale is 20-40× the proxy. Discovering the experiment is broken at scale wastes those GPU-weeks. |
| "LongCat fork is AI-generated; we shouldn't touch it." | The policy concern is about *upstreaming*, not local research use. The fork is fine for our experiments; we just can't submit our patches back to ggml-org. |
| "We should benchmark LongCat on `run_benchmark.py` since it's already wired up." | See `feedback_speed_verify_via_llama_bench.md` — speed verification is `llama-bench` only, run manually by user. Do not auto-launch. |
| "Track B Phase 0 fits on the EPYC box, we don't need GPUs." | EPYC is BW-bound on FFN backward; you cannot train at any reasonable token-rate on CPU. Rent the GPU. |

## Operating Constraints That Apply

- **`feedback_no_concurrent_inference.md`** — every speed-verify run on EPYC needs explicit per-run user approval; do not launch llama-cli / llama-bench / llama-server without it.
- **`feedback_speed_verify_via_llama_bench.md`** — Track A Phase 4 uses `llama-bench` only, never `run_benchmark.py`.
- **`feedback_omp_env_stack_required.md`** — OMP env stack + `numactl --interleave=all` + `KMP_BLOCKTIME=10` mandatory for all benches.
- **`feedback_canonical_baseline_protocol.md`** — first speed gate uses canonical `taskset -c 0-95 -t 96 -fa 1` baseline before NPS4 variants.
- **`feedback_experimental_repo.md`** — the InquiringMinds llama.cpp fork must live in `/mnt/raid0/llm/llama.cpp-experimental`, not the production tree.
- **`feedback_gitignore_binaries.md`** — GGUF files and rented-GPU artifacts never get committed; add to `.gitignore` proactively.
- **`feedback_host_throttle_check.md`** + **`feedback_drop_caches_numa_eviction.md`** — verify host throttle state before Track A Phase 4, and re-warm with `numactl --interleave` after any drop_caches.
- **`feedback_sanity_check_before_compute.md`** — Track B Phase 0 proxy must produce DIFFERENT outputs vs the same-arch frozen-Engram-disabled baseline before committing to a full training run. Avoid the TIDE-style 20h wasted compute.

## Initial Action Queue (for the next agent landing here)

Copy this into a TaskCreate list when starting work:

1. [x] **Track A Phase 0** — `gh pr view 19167/19182 -R ggml-org/llama.cpp` + `gh api repos/InquiringMinds-AI/llama.cpp/branches/longcat-flash-ngram` confirm fork head `56abe85` and upstream PRs unchanged as of 2026-05-24. ✅
2. [x] **Track A Phase 1** — Q4_K_M GGUF present at `/mnt/raid0/llm/models/longcat-flash-lite-q4km/LongCat-Flash-Lite-Q4_K_M.gguf`. ✅
3. [x] **Track A Phase 2** — InquiringMinds fork built in worktree `/mnt/raid0/llm/llama.cpp-longcat-probe` (branch `probe/longcat-build` tracking `inq/longcat-flash-ngram` at `56abe857d`). `llama-cli`, `llama-server`, full toolchain present. ✅
4. [x] **Track A Phase 3** — smoke test passed on 2026-05-25: LongCat Q4_K_M loaded and answered a basic prompt through `/v1/chat/completions`. ✅
5. [x] **Track A Phase 4** — speed gate complete on 2026-05-25: LongCat Q4_K_M `tg128=37.08 t/s`, above abandon threshold but below gemma4-MTP production decode. ✅
6. [x] **Track A Phase 5** — quality gate failed vs worker on 2026-05-25: LongCat 21/39 = 53.8%, gemma4-MTP 26/39 = 66.7%. ✅
7. [x] **Track A Phase 6** — closed negative on 2026-05-25. Remaining debt: write `research/deep-dives/longcat-flash-lite-engram-cpu-poc.md` and update intake-504 contradicting evidence. ✅

Track B Phase 0a (non-inference prep — COMPLETE 2026-05-24):
8. [x] Vendor + refactor the demo Engram module into a clean importable package with config dataclasses (no global state). Drop mocked attn/moe stubs. ✅
9. [x] Add the **two missing zero-init lines** (`value_proj.weight`, `value_proj.bias`, `short_conv.conv.weight`) so identity is preserved at step 0. ✅
10. [x] Unit test the identity-at-step-zero invariant on CPU with non-zero hidden states. ✅ **PASS** at atol=1e-6.
11. [x] HF backbone splicing helper (`EngramLayerWrapper`, `splice_engram_into`) with raises on missing/stale input_ids. Tested with mock HF layer. ✅
12. [x] Two-group AdamW factory + freeze utilities + trainable-param helpers. ✅
13. [x] Pure-Python canonicalizer (NFKC + accent strip + lowercase + whitespace collapse) + offline build script for HF tokenizers. ✅

Track B Phase 0b (the actual GPU proxy run, only when ready to spend ~$50–150 cloud):
14. [ ] Rent H100-80GB or borrow A100s. Set up SmolLM-1.7B (preferred) or TinyLlama as backbone.
15. [ ] Run `scripts/build_canonicalizer.py --tokenizer HuggingFaceTB/SmolLM-1.7B --output canonicalizers/smollm-1.7b.json` to materialize the canonicalization map.
16. [ ] Write the training driver — uses `engram.EngramLayerWrapper`, `engram.freeze`, `engram.make_two_group_adamw` against a frozen SmolLM backbone. Add a co-trained reference run with backbone unfrozen on the same data budget.
17. [ ] Train both configs on 5–20 B tokens FineWeb-Edu. Same Engram-table size for both.
18. [ ] Compute recovery ratio on held-out PPL + MMLU subset + LAMBADA. Apply ≥30% gate. Record in Decision Log.

## Reporting Instructions

After any phase of either track:
1. Update `progress/2026-05/2026-05-24.md` (or the day's progress file when the work happens).
2. Update this handoff's Decision Log + phase checklist; record results inline.
3. If Track A passes its quality gate (Gate A): file `longcat-engram-worker-evaluation.md` and link from `inference-acceleration-index.md`.
4. If Track B proxy derisk passes (Gate B0): file `engram-retrofit-qwen36-spike.md` and link from this handoff.
5. If either track is killed by a falsification gate: write a deep-dive in `research/deep-dives/` documenting the negative measurement, and update intake-599 / intake-504 contradicting_evidence with the verified result.
6. When the handoff reaches a terminal state (both tracks resolved): move to `handoffs/completed/` and update `inference-acceleration-index.md`'s landscape table.
