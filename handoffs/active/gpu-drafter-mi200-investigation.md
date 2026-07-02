# GPU-Drafter on MI200 — Frontdoor Acceleration + CPU-Tier Spec-Dec

**Status**: PATCHED-PENDING-RETEST 2026-06-19 - CPU-testable N5 alpha still has no acceptance-rate evidence; tree speculative branch sequence capacity is fixed in llama.cpp `a6c793fc6`, so the next gate is a clean aligned qwen35/frontdoor retest
**Created**: 2026-05-27 (via session synthesis + companion `/research-intake` run)
**Categories**: speculative_decoding, hardware_optimization, inference_serving, local_inference
**Hardware gate**: contingent on MI200-class GPU (MI210 or MI250/X) acquisition. GT 1030 (currently present) is BW-poorer than CPU and not viable for any role here — see § GT 1030 falsification. **→ MI210 INSTALLED 2026-07-02; the fork's HIP build leg is verified on gfx90a and first GPU benchmarks are in — hardware gate now OPEN (see § 2026-07-02 Advancement).**

> **Fable 5 review (2026-06-12)**: per operator instruction ALL GPU stages remain HW-GATED (MI210 ~July). The α gating measurement (this file's §Gating Measurement) is CPU-testable NOW = master-index row N5. fable5-findings-03 reorders post-arrival priorities: frontdoor residency + eval-engine acceleration BEFORE the drafter farm (Stage 1 keeps its ≥1.3× kill-gate).

> **N5 blocker / rescope (updated 2026-06-14)**: the CPU-testable alpha attempt for target `/mnt/raid0/llm/models/Qwen_Qwen3.6-35B-A3B-Q8_0.gguf` with draft `/mnt/raid0/llm/models/Qwen3-1.7B-Q8_0.gguf` at `gamma=3` is invalid evidence. Both `llama-server` and `llama-cli` abort in the current production llama.cpp external-draft path with `init: invalid seq_id[1][0] = 1 >= 1`, `get_logits_ith: invalid logits id 1`, and `common/sampling.cpp:152: GGML_ASSERT(logits != nullptr) failed` through `common_speculative_state_tree::draft` / `common_speculative_draft`. Metadata confirms the stale premise: target tokenizer is qwen35 (`n_vocab=248320`, EOS `248046`, BOS/PAD `248044`), while Qwen3-1.7B is qwen2 (`n_vocab=151936`, EOS `151645`, BOS/PAD `151643`).
>
> Qwen3.5-0.8B Q8/Q4 are still the right qwen35-family candidates by token/merge arrays. A disposable, metadata-aligned draft copy outside git at `/mnt/raid0/llm/scratch/n5/Qwen3.5-0.8B-Q8_0.frontdoor-specials.gguf` changed BOS/EOS/PAD to the frontdoor target values (`bos=248044`, `eos=248046`, `pad=248044`); token arrays, merges, and token_type already matched. With that copy, `llama-speculative` passed compatibility and ran, proving special-token metadata was the first blocker. It still emitted repeated M-RoPE decode failures even with `--draft 1`; draft2/draft4 were worse. Do **not** route N5 through Qwen3-1.7B or bin any Qwen3.5-0.8B crash/compatibility/fail-closed smoke as alpha evidence. The immediate safety patch is llama.cpp private-fork commit `53e9a6550` (`Fail closed on speculative decode errors`), which prevents crashes/fake success by exiting `llama-speculative` non-zero on decode failure and making shared speculative draft/tree paths return empty drafts on negative `llama_decode`. Real performance alpha remains blocked until the underlying qwen35/qwen35moe M-RoPE/GDN decode-position/rollback issue is fixed, or a non-failing draft path is found. TLI/SLEM or train/retrofit work is still required before Qwen3-1.7B is decision-useful.
>
> **N5 repair update (2026-06-19)**: llama.cpp commit `a6c793fc6` (`Fix tree speculative draft sequence capacity`) fixes the concrete tree-spec sequence-shape bug behind `invalid seq_id[...] = 1 >= 1`. The tree implementation was allocating both the draft context and batch as single-sequence while later creating branch sequence ids `1..31`; the patch centralizes `SPEC_TREE_MAX_SEQS=32`, applies it to tree draft-context initialization, applies it to the tree batch allocation, and replaces the hard-coded branch guard. Validation: GitNexus impact on `common_speculative_state_tree::draft` was LOW; `git diff --check`; `cmake --build build --target llama-speculative -j $(nproc)`; `cmake --build build --target llama-server -j $(nproc)`. Two disposable server smokes were attempted on port `19087` with 2-thread CPU-only model pairs, but both exited during model load before decode under the current loaded/no-GPU environment; PIDs were verified gone. Treat this as a code unblock for the `seq_id >= 1` failure, not alpha evidence. The next valid N5 action is a clean aligned qwen35/frontdoor retest that actually reaches draft/verify and reports acceptance data.
>
> **N5 sidecar status (2026-06-27)**: the qwen35-compatible path still has **no valid acceptance-rate evidence**. The aligned scratch draft `/mnt/raid0/llm/scratch/n5/Qwen3.5-0.8B-Q8_0.frontdoor-specials.gguf` clears tokenizer metadata, but the path still needs a clean retest that reaches draft/verify after the qwen35/qwen35moe M-RoPE/GDN decode-position failures. The inspected llama.cpp tree was at `91745611f`, not the required clean retest commit `a6c793fc6`; both `a6c793fc6` and safety commit `53e9a6550` exist in history. Do not run the alpha smoke from the current tree without first moving to the required retest commit/build and rerunning compatibility.
>
> **N5 harness update (2026-06-27)**: research `scripts/benchmark/n5_frontdoor_drafter_retest.sh` now packages the clean-window retest path. Default mode is no-inference and writes `preflight.json` plus `commands.sh`; `--execute` is fail-closed unless the active llama.cpp worktree is at `a6c793fc6`, `53e9a6550` is in the lineage, the rebuilt `llama-server` is fresh enough, the aligned draft/target files exist, the compatibility checker can import `gguf`, the measurement port is free, and AutoPilot/live `llama-server` blockers are cleared or explicitly overridden. The live dry-run correctly blocked on current HEAD `91745611f`, missing `gguf` in `python3`, active AutoPilot, and live stack servers. This is a reproducibility unblock only; it still emits no alpha evidence until a clean-window execute reaches draft/verify and records `draft_n`/`draft_n_accepted`.

---

## Thesis

**The MI200 adds a latency tier on top of the existing CPU+RAM serving tier — it does not replace it.** The CPU tier already runs at cloud-API-competitive 20–50 t/s under the canonical NPS4 stack (per `feedback_canonical_baseline_protocol`). The GPU's role is to lift the *hot* latency-critical path — frontdoor + its drafters — into the 100+ t/s regime, while architect and workers remain CPU-resident at their already-competitive baseline.

**Concretely:** host the frontdoor Qwen3.6-35B-A3B on the MI200, host a verified frontdoor drafter on the same device only after a validated qwen35-compatible or repaired external-draft path exists, and use any remaining VRAM as a drafter farm for selected CPU-resident roles. Qwen3-1.7B is no longer a valid matched-vocab assumption for this target; Qwen3.5-0.8B is the correct qwen35-family candidate to repair/test first, and the metadata-aligned scratch copy proves the special-token compatibility gate is clearable. It is still not alpha-ready because the speculative path now fails in qwen35/qwen35moe M-RoPE/GDN decode-position handling. Architect (Qwen3.5-122B) does not fit on MI210 anyway. Workers are throughput-amortized and don't need the latency lift.

---

## Design Space — Why Frontdoor (and Not Architect) on GPU

| Factor | Frontdoor on GPU | Architect on GPU |
|---|---|---|
| VRAM fit (MI210, 64 GB) | Qwen3.6 ~18 GB at Q4 + 1 GB drafter + KV → ~25 GB, ~40 GB headroom | Qwen3.5-122B ~65 GB at Q4 → **does not fit** even without KV |
| Traffic frequency | Hot path; every user turn | Cold path; planning steps only |
| Latency sensitivity | TTFT + tok/s define UX | Tolerates seconds-to-minutes |
| Drafter co-location | Verified drafter only after qwen35/qwen35moe M-RoPE/GDN decode-position repair or a non-failing draft path; fail-closed handling is landed but is safety containment, not alpha evidence | Doesn't fit alongside the model |
| Bystander effects | `worker_summarize` shares frontdoor process per `project_stack_consolidation_2026_05` → moves with it for free | n/a |

The choice is forced by VRAM and reinforced by every other axis.

---

## Hardware Math — MI200 vs GT 1030

### GT 1030 falsification (decisive negative on current hardware)

- GT 1030 has **~30 GB/s** memory bandwidth — *less* than a single CPU NUMA node can sustain (~100–200 GB/s of the 460 GB/s aggregate).
- For a BW-bound workload (LLM decode), the GT 1030 runs a 1 B Q4 drafter at **~20 ms/token** vs **~3–6 ms/token** on CPU.
- The "drafter offload" argument requires the GPU to be BW-richer than the displaced CPU work. GT 1030 inverts that. **No spec-dec configuration on this card pays off.**

### MI200 BW envelope

| SKU | GCDs | Per-GCD HBM | Per-GCD BW |
|---|---|---|---|
| MI210 | 1 | 64 GB HBM2e | 1.6 TB/s |
| MI250 / MI250X | 2 | 64 GB HBM2e each | 1.6 TB/s each, 3.2 TB/s aggregate |

1.6 TB/s/GCD ≈ **3.5× CPU aggregate, ~8–16× what a single CPU role sustains.** This is the regime where GPU-side drafting is unambiguously cheap.

### Per-token drafter cost on MI200 (Q4 weights, BW-bound)

| Drafter | Weights | Per-token (MI200) | Per-token (CPU) |
|---|---|---|---|
| Qwen3-0.6B Q4 | ~400 MB | ~0.25 ms | ~3–4 ms |
| Qwen3-1.7B Q4 | ~1.0 GB | ~0.6 ms | ~6–10 ms |
| 4 B Q4 | ~2.4 GB | ~1.5 ms | ~10–15 ms |
| 8 B Q4 | ~5 GB | ~3 ms | ~25–35 ms |

For $k{=}6$ chunks, drafter cost (1.5–18 ms) is fully hidden inside the verify window (100–250 ms on CPU targets). On the GPU itself the frontdoor verify is even faster, so spec-dec acceleration cascades.

### MI210 single-GCD vs MI250 dual-GCD

**MI210 (single 1.6 TB/s pool):** frontdoor + drafters share. A frontdoor at 18 GB / 1.6 TB/s ≈ ~85 t/s solo upper bound; drafter chunks steal ~5–10% of GCD time per spec-dec round, scaling linearly with the number of co-resident drafters. At 3–4 drafters: ~15–30% frontdoor throughput loss. Still likely net positive after spec-dec acceleration (1.5–2.0× expected), but tradeoff is real.

**MI250 / MI250X (dual GCD):** clean partition. Frontdoor + its own drafter on GCD0; spillover drafters for CPU targets on GCD1. No GCD-internal contention. **This is the architecturally cleanest target.**

---

## Cross-Tokenizer Speculative Decoding — Math + Status

### Why it matters here

If we ever want a non-Qwen drafter (cheaper, semantically better-aligned for a workload, or available off-the-shelf), the spec-dec acceptance criterion breaks because draft and target distributions live over different sample spaces.

### Framing as transport

The cleanest framing: both tokenizers induce distributions on a **shared underlying byte / character space**. That byte space is the canonical reference measure that makes correctness recoverable.

Two recoverability strategies:

1. **Byte / character canonicalization (no learning).** Decode both distributions to bytes, perform rejection at byte-prefix boundaries. Used by Huggingface's `assistant_tokenizer` path; the rigorous version (Timor et al. 2025, arxiv:2502.05202) reports ~1.5–2× speedups on cross-tokenizer pairs vs ~2–3× for matched-vocab. Cost is statistical (boundary-stall, canonical-tokenization bias), not computational. Compute overhead is single-digit microseconds per chunk — free.
2. **Learned vocabulary coupling.** A coupling network $\pi(x_{\text{drf}}, x_{\text{tgt}} \mid c)$ whose marginals match each tokenizer's induced distribution. Transport-flavored; biased unless carefully constrained. Examples: ZeTT (Minixhofer & Ponti 2024, arxiv:2405.07883), EVA (Xu et al. 2024, arxiv:2404.09492), FVT (Gee et al. 2024, arxiv:2402.09977).

### What we know without measurement

- Cross-tokenizer adds ~zero compute and ~10–30% acceptance-rate erosion vs matched-vocab.
- On GPU-side drafting, the absolute economics remain positive in published results.
- The two distributions don't disagree on *labels* — they disagree on *segmentation policy*. They live on different σ-algebras over the same byte base space. Byte canonicalization is the rigorous push to the common refinement.

### Status

- Cross-tokenizer is required for Qwen3-1.7B -> Qwen3.6 unless a tokenizer-retrofit/training route produces a qwen35-compatible artifact. The 2026-06-14 metadata check shows the target tokenizer is qwen35 (`n_vocab=248320`) while the Qwen3-1.7B draft is qwen2 (`n_vocab=151936`).
- Qwen3.5-0.8B Q8/Q4 match the target token/merge arrays and remain the correct qwen35-family candidates to repair/test first. The disposable aligned copy at `/mnt/raid0/llm/scratch/n5/Qwen3.5-0.8B-Q8_0.frontdoor-specials.gguf` proves the special-token metadata mismatch is clearable: aligned BOS/EOS/PAD let `llama-speculative` pass compatibility and run. They are still not alpha-ready because aligned runs emit repeated M-RoPE decode failures even at `--draft 1`; production tree speculation also fails on the qwen35/qwen35moe rollback/position path. N5 is therefore blocked on repairing that decode path, disabling/avoiding it, or finding a non-failing draft path before any acceptance-rate binning.

---

## MTP Head Split — Trunk on CPU, Head on GPU

### Idea

Gemma4-26B-A4B (deployed as `worker_general` per `project_worker_general_swap_2026_05_08`) currently runs MTP self-spec-dec entirely on CPU. The architecture admits a split:

```
CPU trunk forward → hidden_t (~10 KB)
  ↓ PCIe (~1 µs)
GPU MTP module 1 → token t+1 + hidden_t+1
  ↓ on-GPU
GPU MTP module 2 → token t+2 + hidden_t+2
  ↓ on-GPU (chained, no PCIe per step)
  ↓ PCIe (~1 µs)
CPU trunk verify ← draft tokens
```

### VRAM cost (Gemma4-26B-style, hidden ~5120)

| Component | Size at Q4 |
|---|---|
| 1 MTP module | ~250–400 MB |
| 4 chained modules | ~1.0–1.6 GB |
| LM head copy (optional, can transfer logits via PCIe instead) | ~650 MB |
| Token embedding copy (optional, can lookup via PCIe) | ~650 MB |

**~1–3 GB depending on replication strategy.** Trivial against 64 GB.

### Estimated gain

Current worker_general: 76.5 t/s with MTP self-spec-dec on CPU (per `project_gemma4_mtp_launch_recipe`, +36% over no-MTP). Splitting:

- MTP heads on GPU: 10× faster execution; no longer competes with trunk for CPU DRAM BW
- Estimated: **~90–105 t/s** (rough; order-of-magnitude only).

### Implementation cost

- ik_llama.cpp PR #1744 fused MTP into the main inference path; no "MTP head as separate compute device" abstraction exists.
- Splitting requires real llama.cpp engineering work (~1–2 weeks: partial-graph offload, PCIe sync points, double-buffering).
- **Do not pursue this before the simpler external-drafter retest validates GPU-side drafting at all.**

---

## Reopening `project_slot_promotion_shelved`

The 2026-04-28/29 shelving decision (dispatcher v1 net-negative on Qwen3.6 + Qwen3-1.7B drafter) was made with drafter + target **both** on CPU, sharing DRAM channels. **Drafter placement was a missed axis in the reopen criteria.**

Memory entry `project_slot_promotion_shelved` lists these reopen triggers:
- Larger drafter
- Non-greedy verifier
- Long-context workload
- High drafter-target disagreement workload

Add as a 5th explicit trigger:

> **Drafter on dedicated compute (GPU)**, removing DRAM BW contention with the target. The original net-negative result confounded "spec-dec is bad" with "drafter steals BW from target."

The clean retest is the experiment described below.

---

## The Gating Measurement — $\alpha$(frontdoor drafter → Qwen3.6)

**This remains the single highest-leverage measurement in this investigation, but N5 still has no acceptance-rate evidence as of 2026-06-19.** A single number - the production-traffic acceptance rate of a validated frontdoor drafter against Qwen3.6 at $\gamma=3$ - gates three independent downstream investments. The attempted Qwen3-1.7B measurement does not supply that number because the pair is tokenizer-incompatible. Qwen3.5-0.8B Q8/Q4 match the qwen35 token/merge arrays, and the scratch aligned Q8 copy clears special-token compatibility. The 2026-06-19 tree sequence-capacity fix removes the `seq_id >= 1` shape failure from the tree path, but it must be followed by a clean aligned qwen35/frontdoor retest before any decision-grade acceptance data exists.

Acceptable evidence must come from one of these paths:

- a Qwen3.5-0.8B aligned-metadata draft path that passes linear `llama-speculative` without negative `llama_decode` returns and actually drafts tokens;
- the fixed llama.cpp external-draft tree path from `a6c793fc6`, followed by a clean aligned qwen35/frontdoor server smoke that actually drafts tokens; fail-closed behavior alone is safety containment, not performance evidence;
- a non-M-RoPE target/draft path that can answer the CPU alpha question without confusing it with qwen35/qwen35moe path bugs;
- a ported heterogeneous-vocabulary algorithm such as Timor TLI/SLEM, or a trained/retrofitted drafter that makes Qwen3-1.7B compatible enough to evaluate after the external-draft path is usable.

Produced automatically by Stage 1 once spec-dec is enabled at frontdoor (llama-server logs `draft acceptance rate = ...` per release event, same format as the gemma4 MTP measurement done 2026-05-27). Crash/error/fail-closed runs, including `/workspace/repos/epyc-inference-research/data/specdec_frontdoor_alpha/20260614_054820/`, the single-sequence Qwen3.5-0.8B CLI smoke, aligned `llama-speculative` M-RoPE failures, and server fallback logs from `53e9a6550`, must not be binned.

**Decision rule (3 bins):**

| Measured $\alpha$ on validated path | Stage 2 (frontdoor on GPU + own drafter) | Stage 3 (cascade / multi-drafter frontdoor path) | Stage 5 (FastDraft custom-train) | SpecDec++ adaptive-K |
|---|---|---|---|---|
| **$\alpha \geq 0.7$** | proceed | **add cascade** (intake-042 breakeven met; geometric tail worth exploiting) | skip — already near ceiling | low EV (K=2-3 likely optimal) |
| **$0.55 \leq \alpha < 0.7$** | proceed | skip cascade (gain collapses to ~0) | skip — marginal $\alpha$ lift from training doesn't amortize | **likely +EV** if per-position variance is high; measure K-sweep $K \in \{2, 4, 6, 8\}$ first |
| **$\alpha < 0.55$** | proceed | skip cascade | **train custom drafter** (intake-624 gating criterion met; code-heavy roles like coder_escalation are highest priority) | gated on K-sweep showing optimal $K \geq 4$ |

**Why this works:** all three downstream investments converge on the same underlying signal — how well the drafter aligns with the production target's next-token distribution on real traffic. Cascade exploits the *tail* of high acceptance (geometric decay needs a tall geometric tail); custom training pays off when off-the-shelf is leaving acceptance on the table; adaptive-K pays off when acceptance variance is large enough that optimal K varies across positions. **The same number, $\alpha$, tells you whether each lever is worth pulling.**

**Replicates for other roles:** the same gating measurement protocol applies to `coder_escalation` only after the drafter/target vocabulary contract is explicit. **Custom training is most likely to pay off on the coder role** per FastDraft's HumanEval $\alpha = 0.65$ result (intake-624) — measure first, train only if the gate condition holds.

**DSpark / DeepSpec trained-drafter path (intake-737/738):** the DSpark semi-autoregressive draft head (parallel backbone + single-token correction) is a candidate trained drafter alongside FastDraft in the **Stage-5** column, gated by the **same α bins** above. DeepSpec (MIT) is the training/eval pipeline; the incoming MI210 could host draft-head training for gemma4-26B-A4B / Qwen3 (its default is an 8-GPU node, so single-MI210 retraining is unproven). CAVEAT: gemma4 native MTP self-spec is already ~76.9% acceptance ("saturated", Stage 0) with Stage-4 EV only +10-15% → **low headroom**; frame the comparison as *DSpark α vs the already-saturated ~77% MTP baseline*. DSpark's utilization-keyed adaptive-verification-depth controller ≈ the SpecDec++ adaptive-K lever (intake-620) — both GPU-side and inert on the CPU-testable N5 α path; **compare, don't double-count**.

See [`research/deep-dives/2026-05-27-cross-tokenizer-specdec-and-mtp.md`](../../research/deep-dives/2026-05-27-cross-tokenizer-specdec-and-mtp.md) § Action item #6 for the rationale chain.

---

## 2026-06-14 Advancement - Metadata Alignment and Fail-Closed Patch

- **Disposable aligned draft created outside git**: `/mnt/raid0/llm/scratch/n5/Qwen3.5-0.8B-Q8_0.frontdoor-specials.gguf`, copied from Qwen3.5-0.8B Q8. Original draft omitted BOS/add_bos and had `pad=248055`; target frontdoor special tokens are `bos=248044`, `eos=248046`, `pad=248044`. Token arrays, merges, and token_type already matched the target.
- **Compatibility result**: aligned `llama-speculative` passed compatibility and ran, proving special-token metadata was the compatibility blocker. It then emitted repeated M-RoPE decode failures even with `--draft 1`; draft2/draft4 were worse. Logs: `/tmp/n5_qwen35_0_8b_q8_aligned_linear_speculative_draft1_20260614_062055.log` and `/tmp/n5_qwen35_0_8b_q8_aligned_linear_speculative_20260614_062011.log`.
- **Safety containment landed in llama.cpp fork**: commit `53e9a6550` (`Fail closed on speculative decode errors`) changes `examples/speculative/speculative.cpp` so the CLI exits non-zero on `llama_decode` failures, and changes `common/speculative.cpp` so shared speculative draft/tree paths return empty drafts and clear draft state on negative `llama_decode` returns. This lets `llama-server` fall back instead of sampling invalid logits.
- **Validation before commit**: `git diff --check -- common/speculative.cpp examples/speculative/speculative.cpp`; `cmake --build /mnt/raid0/llm/llama.cpp/build-n5-linear-test --target llama-speculative llama-server -j 16`; patched `llama-speculative` exited `RC=1` on the known M-RoPE decode failure (`/tmp/n5_qwen35_0_8b_q8_aligned_linear_speculative_draft1_failclosed2_20260614_062517.log`); patched isolated `llama-server` with `LD_LIBRARY_PATH=/mnt/raid0/llm/llama.cpp/build-n5-linear-test/bin` returned HTTP 200 and stayed alive while logging `common_speculative_decode_ok: tree ... llama_decode failed` (`/tmp/n5_qwen35_0_8b_q8_aligned_server_failclosed_ldpath_20260614_062635.log`, response `/tmp/n5_qwen35_0_8b_q8_aligned_server_failclosed_ldpath_response_20260614_062635.json`).
- **Operator hygiene**: without `LD_LIBRARY_PATH`, the isolated executable loaded production shared libs and reproduced the old abort (`/tmp/n5_qwen35_0_8b_q8_aligned_server_failclosed_20260614_062552.log`). Future isolated llama.cpp tests must bind the matching build's shared libraries.
- **Conclusion**: N5 is no longer blocked on tokenizer metadata alone. Aligned metadata clears compatibility, but Qwen35/Qwen35moe external speculation still has M-RoPE/GDN decode-position failures. Speeds from these CPU-only/contention smokes are observations only and must not gate performance decisions.

## 2026-06-19 Advancement - Tree Speculative Sequence Capacity

- **Root cause addressed**: tree speculation allocated the draft context/batch for one sequence while its DySpec frontier creates branch sequence ids `1..31`. That matched the observed `invalid seq_id[...] = 1 >= 1` failure.
- **Patch landed**: llama.cpp `a6c793fc6` centralizes `SPEC_TREE_MAX_SEQS=32`, widens only tree speculation's draft context and batch capacity, and uses the same constant for the branch guard. Linear draft speculation remains single-sequence.
- **Validation**: GitNexus upstream impact for `common_speculative_state_tree::draft` was LOW; `git diff --check`; `cmake --build build --target llama-speculative -j $(nproc)`; `cmake --build build --target llama-server -j $(nproc)`.
- **Smoke status**: disposable server smokes on port `19087` did not reach decode. The obsolete tiny model failed GGUFv1 load, and two modern small-model attempts exited during model load under the current no-GPU/loaded environment. All attempted PIDs were verified gone. Do not count these as acceptance-rate evidence.
- **Next gate**: rerun the aligned qwen35/frontdoor N5 smoke in a clean window and bin alpha only if the path reaches draft/verify and emits real acceptance data.

## N5 Retest Preflight Checklist

This is the bounded no-inference checklist for the next frontdoor drafter alpha retest. Do not start the smoke until every item below is true.

1. Confirm the llama.cpp tree-spec fix is the active build:
   - repo HEAD is `a6c793fc6`
   - the safety containment patch `53e9a6550` is present in the same tree
   - the binaries under `build/` were rebuilt after those commits
   - current tree mismatch noted 2026-06-27: inspected HEAD was `91745611f`, so the retest preflight was **not** satisfied
   - `scripts/benchmark/n5_frontdoor_drafter_retest.sh --strict` must report `status=ready` before any execute attempt
2. Confirm the test pair is the qwen35-compatible one, not the stale Qwen3-1.7B pair:
   - target: `Qwen_Qwen3.6-35B-A3B-Q8_0.gguf`
   - draft: `Qwen3.5-0.8B-Q8_0.gguf` or the aligned scratch copy at `/mnt/raid0/llm/scratch/n5/Qwen3.5-0.8B-Q8_0.frontdoor-specials.gguf`
3. Confirm the draft path is metadata-aligned before any server run:
   - BOS/EOS/PAD must be `248044/248046/248044`
   - token arrays, merges, and token_type must still match
4. Confirm the run will emit decision-grade evidence:
   - `llama-server` metrics must expose `draft acceptance rate`
   - any later acceptance binning must come from draft/verify traffic, not from crash, model-load, or fail-closed logs
5. Use the existing harnesses as controls only:
   - `scripts/benchmark/bench_tree_speculation_server.sh` already parses acceptance stats, but its built-in pairs are not the N5 frontdoor pair
   - `scripts/benchmark/bench_numa_qwen35_sweep.sh` and `scripts/benchmark/bench_hispec_external.sh` are useful for regression control, not for the N5 frontdoor alpha itself
6. Keep the smoke command explicit and minimal:
   - `numactl --interleave=all /mnt/raid0/llm/llama.cpp/build/bin/llama-server -m <target> -md <draft> --draft-max 1 -t 96 -np 1 -c 8192 -ub 8192 -fa on -ctk q8_0 -ctv q8_0 --port <free-port> --metrics --jinja --reasoning auto`
   - if the binary is launched outside the build tree, bind the matching shared libraries with `LD_LIBRARY_PATH` so it does not fall back to production libs
   - prefer the generated `commands.sh` from the N5 harness so the exact `LLAMA_CPP_DIR`, `LLAMA_SERVER`, `PYTHON_BIN`, model paths, and result directory are captured with the run

---

## Retest Plan (gated on MI200 acquisition)

### Stage 0 — Baseline measurement (pre-acquisition, cheap)

- **Action**: extract `n_predicted` / `n_accepted` per slot from current worker_general (Gemma4 MTP) logs. Verify MTP self-spec-dec is in a healthy regime (≥60% accept) before designing around it.
- **Cost**: log analysis only. No new compute.
- **DONE 2026-05-27** (no autopilot interference, log-only read of `worker-explore-8072.log`, 19h 31m process lifetime, 472 release events):
  - Token-weighted aggregate acceptance: **76.9%** (`draft-max=2 --draft-p-min 0.0 --spec-type mtp`)
  - Long tasks (≥50 gen tokens, n=289): **77.1%**, with 48% of events at ≥0.9 acceptance and ~10% at <0.6 (task-heterogeneity tail)
  - **Gate met.** MTP self-spec-dec is saturated; not the limiting factor for worker_general throughput.
  - **Implication for Stage 4 (MTP head split):** since MTP heads are already cheap and acceptance is already saturated, the GPU split mostly buys (a) CPU BW released for trunk, (b) marginally cheaper MTP heads. Revised ceiling estimate: **+10–15%** on worker_general (76.5 → ~84–88 t/s), not the +15–35% in § MTP Head Split. Stage 4 EV is lower than originally framed.
  - **Implication for stage ranking:** Stage 2 (frontdoor on GPU + validated drafter after external-draft repair) overtakes Stage 4 in EV by a wide margin. Running frontdoor (`Qwen3.6-35B-A3B-Q8_0` on `:8080`) currently launches with **no `-md` / no `--spec-type` flag at all** — zero spec-dec speedup today. Adding spec-dec + GPU placement is a 2–3× play, vs +10–15% for the MTP-split.

### Stage 1 — External GPU drafter for CPU-resident frontdoor (validated vocabulary path only)

- Place Qwen3.6 on CPU (current state).
- Place a validated drafter on the MI200 only after Qwen3.5-0.8B aligned-metadata linear/server smokes pass on the `a6c793fc6` tree-capacity fix and emit real draft/verify acceptance data, or after a different non-failing draft path is found. The fail-closed patch must be present for safety but does not satisfy the alpha gate.
- Run llama.cpp's spec-dec path with cross-device drafter + target.
- **Gate**: ≥1.3× end-to-end speedup on frontdoor workload, plus usable alpha evidence. If this fails for a valid pair, no other GPU-drafter configuration will pay off.

### Stage 2 — Frontdoor on GPU + drafter on same GPU (the production design)

- Place Qwen3.6 on MI200 GCD0 (or single GCD on MI210).
- Place the validated frontdoor drafter on same device.
- Compare against Stage 1 (CPU frontdoor + GPU drafter) and against pure-CPU baseline.
- **Expected**: 2–3× over pure-CPU baseline on TTFT and tok/s. This is the deployment target.

### Stage 3 — Drafter farm for CPU-resident roles

- Add a second drafter on the same GPU device targeting `coder_escalation` (or another CPU-resident role).
- Verify concurrent drafter execution on GPU is contention-free (HBM headroom is large; should be fine).
- Measure aggregate system throughput vs Stage 2.

### Stage 4 — MTP head split for Gemma4 worker_general

- *Only* after Stages 1–3 validate the architecture. Requires llama.cpp engineering (1–2 weeks).
- **Expected**: +15–35% on worker_general (76.5 → 90–105 t/s, rough estimate).

### Stage 5 — Cross-tokenizer experiments (optional)

- Try non-Qwen drafters with byte-canonical acceptance on specific roles.
- Reference algorithms: Timor et al. 2025 (arxiv:2502.05202).
- Gate: only if a non-Qwen drafter beats the validated baseline drafter path on a specific workload (e.g., code-specialized drafter for coder role).

---

## Open Questions

1. **Can any validated qwen35-compatible path draft tokens?** The aligned Qwen3.5-0.8B Q8 copy clears compatibility, and llama.cpp `a6c793fc6` fixes the tree branch sequence-capacity failure that produced `invalid seq_id >= 1`. The next gate is rerunning a clean aligned linear/server smoke before any server alpha binning. The current Qwen3-1.7B and Qwen3.5-0.8B crash/fallback/model-load outputs cannot be used as alpha evidence.
2. **Which MI200 SKU?** MI210 single-GCD vs MI250/X dual-GCD changes the contention story. MI250/X is architecturally cleaner; MI210 is likely cheaper used. Worth concrete pricing scan before committing.
3. **PCIe-NUMA placement.** Under NPS4, each CPU NUMA node owns separate PCIe lanes. Which CPU node's lanes host the GPU determines latency to each CPU-resident role. Worth `lspci -vv` + `numactl --hardware` audit at install time. Cost is µs-scale, not catastrophic, but it tilts which CPU-role pairs best with which drafter slot.
4. **ROCm + custom llama.cpp fork.** gfx90a (MI200) is supported in upstream llama.cpp; need to verify HIP build leg in our fork including the v5 kernels (CPU2 AVX-512BW won't apply but other knobs do). **→ RESOLVED 2026-07-02**: HIP build leg verified on gfx90a (fp8 guard fix; isolated worktree branch `mi210-hip-enable` @ `0ebf1b4d7`); gemma4-31B + NEXTN MTP and qwen35 (GDN) both decode on ROCm0. See § 2026-07-02 Advancement.
5. **Coder_escalation placement.** Currently CPU-resident, sharing the frontdoor process per `project_stack_consolidation_2026_05`. If frontdoor moves to GPU, does coder follow it, or do they un-share? VRAM allows both if needed.
6. **Architect spec-dec on CPU.** Architect stays on CPU. Does it benefit from its own drafter (e.g., Qwen3.5-9B drafting Qwen3.5-122B), and would that drafter live on CPU or in spare GPU VRAM? Probably the latter — same "drafter farm" pattern.
7. **Power / thermal envelope.** MI200 family is 300–500 W TDP. The current EPYC chassis power/cooling budget needs verification.

---

## Cross-References

### Memories
- `project_slot_promotion_shelved` — primary precedent; this handoff adds drafter-placement as the missed-axis reopen trigger
- `completed/hybrid-ssm-slot-promotion-spec-dec.md` — historical warning that the Qwen3.6 + Qwen3-1.7B vocab-compatible premise was likely wrong; 2026-06-14 metadata check confirms the mismatch
- `project_gemma4_mtp_launch_recipe` — MTP launch params currently in use
- `project_worker_general_swap_2026_05_08` — current Gemma4 worker_general deployment
- `project_stack_consolidation_2026_05` — frontdoor + summarize share `:8070`
- `feedback_qwen3x_enable_thinking_false` — frontdoor / architect chat-template requirement (applies on GPU too)
- `feedback_cpu_decode_bw_bound` — explains why GT 1030 fails and why MI200 wins
- `feedback_canonical_baseline_protocol` — the baseline the CPU tier already runs at
- `feedback_classify_eval_failures_by_reason` — apply to Stage 1+ failure attribution

### Companion intake (in flight at handoff creation time)
A `/research-intake` run was dispatched in parallel against 7 papers — see § Research Intake Update below (will be appended by the intake skill on completion). Intake IDs will be cross-linked into the stages above where they ground specific claims.

Reference list with intake IDs (intake completed 2026-05-27):
- intake-617 / arxiv:2502.05202 — Timor et al. 2025, ICML (3 algorithms: **SLEM**, **SLRS**, **TLI** — see deep-dive)
- intake-618 / arxiv:2405.07883 — Minixhofer & Ponti 2024, ZeTT (NeurIPS)
- intake-619 / arxiv:2404.09492 — Xu et al. 2024, EVA / Bridging Vocabularies (NAACL)
- intake-042 (dedup) / arxiv:2312.11462 — Chen et al. 2023, Cascade Speculative Drafting (NeurIPS 2024)
- intake-620 / arxiv:2405.19715 — Huang et al. 2024, SpecDec++ (COLM 2025)
- intake-621 / arxiv:2412.19437 — DeepSeek-AI 2024, DeepSeek-V3 Technical Report (MTP section)
- intake-622 / arxiv:2402.09977 — Gee et al. 2024, Fast Vocabulary Transfer (EMNLP 2022 Industry)

**Expansion finds (Tier 1 reference chasing during companion intake run, both high-relevance, not yet deep-dived):**
- intake-623 / arxiv:2404.19737 — Gloeckle et al. 2024, **Parallel MTP** (Meta FAIR, NeurIPS spotlight). Parallel-head architecture vs DeepSeek-V3's sequential — relevant to MTP-split design choice (parallel heads compose better with trunk-on-CPU/head-on-GPU split).
- intake-624 / arxiv:2411.11055 — Zafrir et al. 2025, **FastDraft** (Intel, ACL 2025). Drafter-training pipeline complement to Timor; relevant to "train custom drafter" vs "off-the-shelf Qwen3" decision.

**Full technical synthesis with per-paper math, mechanisms, numbers, and 5 load-bearing corrections to this handoff:** [`research/deep-dives/2026-05-27-cross-tokenizer-specdec-and-mtp.md`](../../research/deep-dives/2026-05-27-cross-tokenizer-specdec-and-mtp.md).

Key corrections to apply to this handoff from the deep-dive (in order of materiality):
1. **§ Cross-Tokenizer** — replace "byte canonicalization" framing with the explicit SLEM/SLRS/TLI distinction; **TLI** is the operational starting point, not byte-level.
2. **§ MTP Head Split** — current production models ship $D=1$, so "chained-on-GPU" is structurally unavailable today. Mechanically sound for future $D \geq 2$ or EAGLE-style auxiliary drafters.
3. **§ Stage 4 EV** — already revised in the Stage 0 measurement block.
4. **§ Stage 5 (cross-tokenizer)** — recommended starting algorithm is TLI, not SLEM. Reference impl is HuggingFace Transformers PR #35029.
5. **Cascade (intake-042) consideration for Stage 2+** — Qwen3-0.6B → Qwen3-1.7B → Qwen3.6 stack is structurally net-positive on MI200 *only* if a validated heterogeneous-vocab or retrofitted qwen35-compatible Qwen3-1.7B path measures $\alpha_{1.7 \to 3.6} \geq 0.7$. The current 2026-06-14 Qwen3-1.7B crash artifact, Qwen3.5-0.8B compatibility-control smoke, aligned M-RoPE failures, and fail-closed server fallback cannot supply that alpha.

### Related handoffs (potential intake cross-link targets)
- `cpu-inference-optimization-index.md` — CPU stack baseline this handoff layers on top of
- `inference-acceleration-index.md` — spec-dec lineage including the v1 dispatcher experiment
- `moe-spec-cpu-spec-dec-integration.md` — MoE-specific spec-dec lever still live

---

## Notes

- This handoff is **observation-and-design** stage. No code change, no hardware change. Implementation gated on MI200 acquisition + Stage 0 baseline measurement.
- Per `feedback_observe_before_diagnosing`: each stage of the retest plan must produce primitive evidence (actual t/s, actual `n_accepted`, actual PCIe bytes) before any closure claim.
- Per `feedback_classify_eval_failures_by_reason`: if Stage 1 fails, classify by reason (PCIe latency? ROCm build issue? acceptance-rate erosion? thermal?) before generalizing to "GPU drafter doesn't work."
- Per CLAUDE.md research-intake rule: this stub was created in response to a direct user request. The companion `/research-intake` dispatch was likewise user-approved.

---

## Research Intake Update — 2026-05-27

Companion `/research-intake` run completed in this session against the 7-paper reading list referenced in § Companion intake above. Intake IDs are assigned and cross-linked below.

### New Related Research

- **[intake-617] "Accelerating LLM Inference with Lossless Speculative Decoding Algorithms for Heterogeneous Vocabularies"** (arxiv:2502.05202, ICML 2025 oral)
  - Relevance: **Direct foundation** for cross-tokenizer GPU drafter placement. Removes the chapter-01 "exact tokenizer compatibility" wall — Algorithm 2 (SLEM, string-level exact match) is already merged in HuggingFace Transformers; Algorithm 4 (TLI, token-level intersection) gives the most lossless variant at 12–85% vocab overlap.
  - Key technique: three lossless algorithms (SLEM string-level, SLRS string-level rejection sampling, TLI token-level intersection) — drafter and target distributions transported via shared string-byte canonical form.
  - Reported results: Gemma-2-9b + vicuna-68m on CNN-DM 37.5 vs 27.7 t/s; Gemma-2-9b + gemma-2-2b on SCROLLS 30.5 vs 13.4 t/s; up to 2.8× over autoregressive (ICML abstract claim).
  - Delta from current approach: the original plan assumed a matched-tokenizer Qwen3-1.7B drafter for Qwen3.6-35B, but the 2026-06-14 metadata check found qwen2 vs qwen35 tokenizer mismatch. With Timor SLEM/TLI on a GPU drafter, the drafter pool expands to *any* small model in VRAM regardless of tokenizer — directly unlocks the "drafter farm" pattern in § Open Questions Q4.

- **[intake-618] "Zero-Shot Tokenizer Transfer"** (arxiv:2405.07883, NeurIPS 2024)
  - Relevance: Complementary mechanism — if Timor's logit-space transport is too lossy on a given pair, ZeTT can retrofit a *new* tokenizer onto an existing drafter (hypernetwork-predicted embeddings, no retraining). Gives an offline path to a matched-vocab drafter from a mismatched candidate.
  - Key technique: hypernetwork conditioned on tokenizer spec predicts embedding/lm-head matrix for arbitrary new tokenizer.
  - Reported results: XLM-R/XNLI ~1% accuracy loss, +16% inference speedup; Mistral-7B 3-5% drop recoverable with 800M tokens continued training.
  - Delta from current approach: ZeTT is a **drafter-prep** technique (offline), Timor is a **runtime** technique (online). They stack — ZeTT to expand the drafter candidate pool, Timor to serve cross-tokenizer pairs at inference.
  - Caveat (from Tier 2b): hypernetwork training is expensive (one-time per base architecture); numeric-tokenization mismatch degrades GSM8K. Likely a backup plan not a default.

- **[intake-619] "Bridging the Gap between Different Vocabularies for LLM Ensemble" (EVA)** (arxiv:2404.09492, NAACL 2024)
  - Relevance: Cross-tokenizer projection at the logit level — closest published precedent for the byte-canonical reference measure framing discussed in this session. Not directly a SD paper, but the projection-matrix mechanism (overlapping-token-anchored alignment + top-t/threshold/variance noise reduction) is the same math as TLI without the speculative-decoding wrapper.
  - Key technique: train projection matrices from overlapping-vocab anchors, project all logits into a unified space, ensemble at each generation step.
  - Reported results: GSM8K +10.61, Flores Zh-En +1.98 BLEU; matrices ~1 MB each.
  - Delta: confirms the cross-tokenizer transport in § Thesis is *mathematically tractable* — EVA does it without speculative decoding, Timor does it with. EVA is the older, simpler ablation point.

- **[intake-042] "Cascade Speculative Drafting" (CS Drafting)** (arxiv:2312.11462, ICML 2024) — **DUPLICATE detected; no new intake entry**
  - Already in index since 2026-03-14 as intake-042. Re-surfaced in this session's reading list as background for the "drafter farm" / multi-tier drafter pattern (vertical + horizontal cascade).
  - Relevance to this handoff: vertical cascade (recursively smaller drafters down to a Max-Gram statistical model) is directly applicable to the spare-VRAM drafter-farm question (§ Open Questions Q4–Q5). Horizontal cascade (different drafter sizes per token position) is the formal version of "draft the easy tokens with a tiny model, the hard ones with a bigger one" — relevant once GPU drafter latency budget is measured.
  - Existing intake-042 entry covers the algorithmic content; this session's relevance update is recorded here in the handoff rather than duplicating the intake row.

- **[intake-620] "SpecDec++: Boosting Speculative Decoding via Adaptive Candidate Lengths"** (arxiv:2405.19715, COLM 2025)
  - Relevance: Adaptive draft-length predictor is the right control surface for a GPU drafter where PCIe round-trip cost is non-trivial. Fixed γ over-drafts (wasted PCIe) or under-drafts (idle GPU). SpecDec++'s acceptance-prediction head + MDP threshold stop is the principled controller.
  - Key technique: train a lightweight binary classifier on the draft model's hidden states to predict per-token acceptance probability; stop drafting when cumulative rejection probability exceeds a learned threshold.
  - Reported results: 2.04× Alpaca / 2.26× GSM8K / 2.23× HumanEval (each 7-11pp over fixed-γ baseline).
  - Delta: directly applicable to Stage 1 of this handoff — once frontdoor+drafter co-locate on MI200, SpecDec++ replaces fixed-γ in llama.cpp's spec-dec loop. Independently corroborates `cpu-inference-optimization-index.md` "adaptive γ" line item.
  - Caveat (from Tier 2b): training the acceptance head has known class-imbalance and signal-sparsity issues — see contradicting_evidence on the intake entry.

- **[intake-621] "DeepSeek-V3 Technical Report" (MTP section)** (arxiv:2412.19437, Dec 2024) — scoped to MTP contribution only per session brief.
  - Relevance: Direct precedent for the "split MTP head off the trunk" architecture in § Thesis. DeepSeek-V3 MTP is *sequential* (depth-D modules, each with its own transformer block sharing embedding+output head with main model), not parallel like Gloeckle. D=1 in V3.
  - Key technique: D sequential MTP modules, each TRM_k + projection M_k ∈ R^{d×2d}; trained with averaged cross-entropy at each depth; weighted λ=0.3→0.1 across training.
  - Reported results: ablation shows MTP improves HumanEval (20.7→26.8% small, 44.5→53.7% large), GSM8K (25.4→31.4%); no TPS numbers — paper says modules "can be directly discarded" at inference or used for SD.
  - Delta: validates the **separability** assumption central to this handoff — DeepSeek-V3 explicitly designs the MTP heads to be discardable and/or run as speculative drafters detached from the trunk. Same separability the Gemma4 deployment relies on (`project_gemma4_mtp_launch_recipe`). Strongest published evidence that head-on-GPU + trunk-on-CPU is structurally sound.

- **[intake-622] "Fast Vocabulary Transfer for Language Model Compression" (FVT)** (arxiv:2402.09977)
  - Relevance: Weakest of the seven for this handoff. FVT initializes new-tokenizer embeddings by averaging old-tokenizer sub-token embeddings — a precursor to ZeTT/WECHSEL. Useful only if we need to retrofit a domain-specific tokenizer onto a candidate drafter (e.g., shrink a coder drafter's vocab to a Python-heavy subset).
  - Key technique: novel-token embedding = mean of original-tokenizer decomposition's embeddings; identity for shared tokens.
  - Reported results: 15-55% model-size reduction, 1.07×-1.40× inference speedup alone (1.96×-2.76× with distillation), F1 drop ≤3.65pp worst case on CoNLL03.
  - Delta: would only matter if we go down the path of *custom drafter compilation*. Lower priority than ZeTT for the same role.

### Expansion entries (Tier 1 reference chase, ≤10 cap)

- **[intake-623] Gloeckle et al., "Better and Faster Large Language Models via Multi-Token Prediction"** (arxiv:2404.19737, NeurIPS 2024 spotlight, Meta FAIR) — discovered via DeepSeek-V3 reference. Parent of the entire MTP head family this handoff exploits. Parallel-MTP (Gloeckle) vs sequential-MTP (DeepSeek-V3) is the design fork.
- **[intake-624] Zafrir et al., "FastDraft: How to Train Your Draft"** (arxiv:2411.11055, ACL 2025, Intel) — discovered via Timor reference. Trains drafters specifically against vocab-mismatched targets (Phi-3-mini, Llama-3.1-8B); 10B tokens / 8 Gaudi-2 / <24h; up to 2-3× memory-bound speedup on Intel Core Ultra. Closest commercial-grade procedure for *building* the drafter that Timor SLEM/TLI then serves.

### Mapping to handoff stages

- Stage 0 (CPU baseline, no GPU) — unchanged. No intake dependency.
- Stage 1 (frontdoor + validated drafter on MI200 after Qwen3.5-0.8B aligned-metadata linear/server smokes run without qwen35/qwen35moe M-RoPE/GDN decode failures, or after an alternate CPU alpha path) — **SpecDec++ (intake-620)** belongs here as the γ controller.
- Stage 2 (drafter farm using cross-vocab drafters from spare VRAM) — **Timor SLEM/TLI (intake-617)** is the runtime mechanism; **Cascade vertical/horizontal (intake-042)** governs how multiple drafters compose; **EVA (intake-619)** is the underlying logit projection theory; **FastDraft (intake-624)** is the procedure to *make* the drafters; **ZeTT (intake-618)** is the offline backup to retrofit tokenizers.
- Stage 3 (head-on-GPU / trunk-on-CPU MTP split) — **DeepSeek-V3 MTP (intake-621)** + **Gloeckle MTP (intake-623)** are the architectural precedents.
- All stages — **FVT (intake-622)** stays in the index but is not on the critical path.

### Chapter update flag

Chapter 01 § "Tokenizer Compatibility Constraints" currently states: *"Speculative decoding requires exact tokenizer compatibility between draft and target models."* This is **no longer accurate** as of ICML 2025 (Timor et al., intake-617) + HuggingFace Transformers PR #35029 (Algorithm 2 merged). The constraint is now: *"...unless using a heterogeneous-vocabulary algorithm (SLEM merged in HF; SLRS / TLI in active research)."* Flagged for chapter rewrite — handoff intake skill does NOT modify chapter files directly per its skill-boundary rule.

Chapter 10 § "Heterogeneous Processor Partitioning" (line ~240) is the natural location for cross-referencing this entire GPU-drafter handoff once Stage 0/1 numbers exist.

## Research Intake Update — 2026-06-03

### New Related Research
- **[intake-660] "CUDA Agent: Large-Scale Agentic RL for High-Performance CUDA Kernel Generation"** (arxiv:2602.24286, ByteDance Seed + Tsinghua AIR)
  - Relevance: this handoff is **explicitly MI210-gated**, and the MI210 (CDNA2/gfx90a, 64 GB) is now expected ~July 2026 with active user intent to author custom AMD kernels. Beyond the spec-dec *topology* this handoff designs, the MI210 will need **hand-tuned HIP kernels** (attention, MoE dispatch, dequant) to hit the 100+ t/s frontdoor target — CUDA Agent is a methodology for generating exactly those, via an automated verify+profile reward loop, instead of manual authoring.
  - Key technique: open, skill-augmented agentic kernel-dev harness (`verification.py` correctness gate vs torch reference + `profiling.py` speedup-vs-baseline reward + `compile.sh` build), multi-turn ReAct loop; reward design lessons (discrete schedule over raw speedup; multi-turn is load-bearing).
  - Reported results: SOTA on KernelBench (2.11× geomean vs torch.compile; 100/100/92% faster-rate L1/L2/L3).
  - Delta from current approach: complementary, not competing. This handoff allocates *which model runs where* on the MI210; CUDA Agent could *author the HIP kernels* that make those placements fast. **Caveats**: CUDA-only today (needs hipify/hipcc/rocprof port + a ROCm KernelBench analog); RL training needs a GPU cluster (single MI210 can't retrain — drive the open harness with an existing coder model instead); checkpoint unreleased + base model is closed SaaS (harness + 6K dataset are the open, usable parts). Tracked as a candidate spike for "once MI210 is racked."

## Research Intake Update — 2026-06-03 (LLM-kernel-generation cluster deep-dive)

The MI210 frontdoor/drafter placements this handoff designs will need hand-tuned **HIP kernels** (attention, MoE dispatch, dequant). Deep-dived the kernel-generation cluster (intake-660–679) for an *automated authoring* path; spun out [`agentic-rocm-kernel-authoring.md`](agentic-rocm-kernel-authoring.md) + its backend [`rocm-verify-profile-backend.md`](rocm-verify-profile-backend.md). The NVIDIA/Intel cluster (660–673) is methodology-only, but **AMD's own GEAK (674) / Apex (675) / AgentKernelArena (679) are AMD-native ROCm and largely reusable — GEAK is demonstrated on gfx90a (MI250X = MI210 ISA)** — so authoring these HIP kernels is materially de-risked. Full reasoning: [deep-dive](../../research/deep-dives/agentic-rocm-kernel-authoring-geak-synthesis.md).

- **Lead path** = train-free controller (EvoEngineer intake-666 + CudaForge profiler-Judge intake-662) driven by an existing coder model — runs on a single MI210, NO training cluster, opensource_only-compatible.
- **Decline**: RL training of a bespoke kernel model (CUDA Agent 660 / CUDA-L1 661 / Kevin 663 need a multi-GPU cluster) — but harvest their reward design + anti-reward-hacking gates.
- **Complementary, not competing** with this handoff: this allocates *which model runs where* on the MI210; the new handoffs *author the HIP kernels* that make those placements fast.

## Research Intake Update — 2026-07-02

### New Related Research
- **[intake-737] DeepSeek DeepSpec** (MIT draft-model train/eval framework; DSpark/DFlash/EAGLE-3) — a concrete MI210 draft-head training pipeline; released checkpoints target Qwen3-4B/8B/14B + gemma-4-12B-it. Default assumes an 8-GPU CUDA node — 1× MI210 is far from that, so single-card retraining is unproven. Slots into §The Gating Measurement as a Stage-5 trained-drafter path.
- **[intake-738] DSpark** (semi-AR draft head + GPU-utilization adaptive-verification-depth) — candidate trained-drafter alternative to native MTP heads, gated by the same α bins; its adaptive-depth controller overlaps SpecDec++ (intake-620) and is CPU-inert. Vendor speedups (57-85%) are GPU + unreproduced — observations only. Low headroom on gemma4 (native MTP already ~77% saturated).

---

## 2026-07-02 Advancement — MI210 Installed, HIP Build Verified, First GPU Benchmarks

**The hardware gate for this entire handoff is now OPEN.** The MI210 (gfx90a, CDNA2, 64 GB HBM2e) is installed and passed into the devcontainer (`--device=/dev/kfd --device=/dev/dri --group-add=992`), with **ROCm 6.2.0 bind-mounted at `/opt/rocm`**; `rocminfo`/`rocm-smi`/`hipcc` all work. Full session record: [`progress/2026-07/2026-07-02-mi210.md`](../../progress/2026-07/2026-07-02-mi210.md); memory `project_mi210_gpu_inference`. All numbers below are **first-pass OBSERVATIONS** (contended host — the 28-proc production CPU stack was live at ~106 load; operator-approved GPU-only runs), not decision-gating per MEASUREMENT.md.

- **Open Question #4 RESOLVED — the fork's HIP build leg works on gfx90a.** Isolated worktree `/mnt/raid0/llm/llama.cpp-mi210-hip` (branch `mi210-hip-enable`) off `production-consolidated-v6`, `-DGGML_HIP=ON -DAMDGPU_TARGETS=gfx90a -DGGML_HIP_ROCWMMA_FATTN=ON -DGGML_HIP_MMQ_MFMA=ON`. One build break: `ggml-cuda/vendors/hip.h` guards the OCP fp8 typedefs on `HIP_VERSION>=60200000`, but ROCm 6.2 ships only the `_fnuz` fp8 types (OCP landed in ROCm 6.3) → every TU fails; fix = bump the guard to `>=60300000` (committed `0ebf1b4d7`). Runtime gotcha: `BUILD_SHARED_LIBS=ON` + the container's inherited `LD_LIBRARY_PATH` (production CPU build first, no `libggml-hip.so`) → SIGSEGV; must prepend `.../llama.cpp-mi210-hip/build-hip/bin:/opt/rocm/lib`. `llama-cli --list-devices` → `ROCm0: AMD Instinct MI210 (65416 MiB free)`.
- **GPU-side MTP spec-dec demonstrated (evidence for Stage 4 / § MTP Head Split).** gemma-4-31B-it-Q4_K_M target + the 514 MB NEXTN head (`gemma-4-31B-it-assistant-v6-Q8_0`) both offloaded to ROCm0 via `--spec-type draft-mtp -ngl 99 --spec-draft-ngl 99` (llama-server only — the CLI/speculative example is NOT MTP-wired). Result: decode **43.25 t/s = 1.44× over plain (30.01)**, draft **acceptance 59.7%** (163/273), mean accept length **2.79** of n_max=3, per-position (0.758, 0.593, 0.440). gemma4 + NEXTN have full HIP op coverage; the per-step hidden-state hop is a ~µs PCIe memcpy, not CPU compute. Direct evidence that head-on-GPU MTP is structurally sound on the MI210 (vs the CPU-only MTP baseline in Stage 0 = 76.9% accept).
- **qwen35 (GDN / hybrid-SSM) decodes CLEAN on the GPU HIP path.** Qwen3.6-27B-Q8_0 (arch `qwen35`, gated-delta-net + full attention) ran at **28.69 t/s** with `-ngl 99`, **no M-RoPE/GDN decode failures**. The v6 fork's `ggml-cuda` has full delta-net/ssm-conv kernels (a strict superset of the `dflash` tree, incl. `gated_delta_net.cu`). This is a notable contrast with the CPU external-draft / tree-spec qwen35 failures in the N5 blocker notes above — it localizes those failures to the **CPU speculative codepath**, not the qwen35 forward pass. (Does NOT by itself supply N5 α — that gate is about frontdoor *drafter* acceptance — but it removes "qwen35 can't decode on our stack" as a GPU-path concern.)
- **Vulkan on gfx90a is DEFINITIVELY IMPOSSIBLE** (complements the GT 1030 falsification). RADV enumerates zero devices for CDNA2; no Vulkan ICD (RADV / AMDVLK / amdgpu-pro) targets the compute-only Instinct MI200 family. Use HIP/ROCm.
- **Kernel roofline — real tuning headroom (motivates [`agentic-rocm-kernel-authoring.md`](agentic-rocm-kernel-authoring.md)).** llama.cpp gfx90a decode reaches only ~33% (Q4_K) / ~47% (Q8_0) of the MI210's ~1.64 TB/s HBM roofline; same-model Qwen3.6-27B confirms Q4_K is partly dequant-bound (Q8 766 GB/s vs Q4 537 GB/s). Flash-attn does not help decode here (`-fa 0` beats `-fa 1`); default MMQ beats forced rocBLAS. The residual gap is CDNA2 kernel maturity — the direct target for the ROCm kernel-authoring handoffs.
- **vLLM comparison — DONE.** The official `rocm/vllm:rocm6.2_mi300` image is hard-locked to MI300 (`config.py` raises "built for MI300 only") — dead end, removed. The VERIFIED gfx90a image `rocm/vllm:rocm6.4.1_vllm_0.10.1_20250909` (upstream ROCm/vllm, `PYTORCH_ROCM_ARCH=gfx90a;...`, no MI300 lock; env `TORCH_BLAS_PREFER_HIPBLASLT=0` / `VLLM_USE_TRITON_FLASH_ATTN=1` / `VLLM_ROCM_USE_AITER=0`) computes on gfx90a and supports Qwen3. **RESULT (Qwen3-8B matched fp16): per-stream decode llama.cpp-HIP 62.45 t/s (62% roofline) vs vLLM ~69 t/s (69% roofline) = vLLM +11%; vLLM batched throughput 1129 out tok/s @ 32 concurrent (its continuous-batching serving win; llama.cpp tested single-stream only). KEY: at fp16 (no dequant) llama.cpp reaches 62% roofline — the earlier ~47% (Q8) / 33% (Q4) ceiling is a QUANTIZED MMQ-dequant artifact, NOT general kernel immaturity; vLLM's fp16 per-stream edge is modest, its decisive advantage is batched serving.** Quantized-vs-quantized (vLLM AWQ/fp8 vs llama.cpp Q4/Q8) not measured; vLLM 0.10.1 predates our `gemma4`/`qwen35` archs, hence Qwen3-8B.
