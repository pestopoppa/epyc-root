# Deep Dive: Qwen3.6-27B "Dense" Spec-Decoding (RTX 4090 community note) — CPU Feasibility for EPYC

**Date**: 2026-04-24
**Intake**: intake-455 (inline community note, `inline:qwen36-27b-spec-decoding-rtx4090-2026-04-24`)
**Model**: Qwen3.6-27B (released 2026-04-22, HuggingFace `Qwen/Qwen3.6-27B`, Apache 2.0)
**Draft candidate**: Qwen3-1.7B Q4_K_M (same-family)
**Question**: Is Qwen3.6-27B viable as a CPU coder/worker on EPYC 9655, with or without speculative decoding, and what throughput should we expect?

## Executive Summary

**The community note's 5.9× GPU claim is a bookmark, not an action item — CPU feasibility is the real question, and the honest answer is "competitive with our current hybrid SSM models at ~7–10 t/s, not a step-change."**

The critical correction up front: Qwen3.6-27B is **not a true dense transformer**. Per the HuggingFace model card and MarkTechPost/HackerNoon coverage, the architecture is `16 × (3 × (Gated DeltaNet → FFN) → 1 × (Gated Attention → FFN))` = 64 layers with a **3:1 Gated-DeltaNet : Gated-Attention ratio** and dense FFN. This is the **same hybrid SSM-Dense pattern as Qwen3.5-27B** (which `feedback_qwen35_27b_architecture` already characterized: 48 DeltaNet + 16 attention layers, spec-dec dead on CPU). The marketing calling it "dense" refers to **dense FFN** (no MoE routing), not dense attention. Every load-bearing implication for our stack — spec-dec viability, throughput shape, NUMA-4-way behavior — should be reasoned from the hybrid-SSM side of the architecture, not the dense side.

The intake's relevance flag (`low`) should move to **`medium-low`** on the strength of the model as a **coder_escalation candidate** (77.2 SWE-bench Verified, Claude-4.5-Opus-competitive per HackerNoon/Simon Willison coverage). The GPU spec-dec claim does not move the relevance dial; the model drop itself does, because it is the first 27B-active open-weight coder that plausibly outperforms Qwen2.5-Coder-32B at the same quant footprint.

The CPU throughput answer is known with high confidence *before* any measurement, because the architecture class is identical to Qwen3.5-27B (which we have measured): **7.5–9 t/s single-instance, ~30 t/s NUMA-4-way aggregate, BW-bound at ~24% of the 460 GB/s roofline**. The measurement is still worth running — it is cheap and confirms the transfer — but it will not change the deployment decision. That decision hinges on the **quality eval**, not the throughput eval.

## The Community Note — What to Trust and What to Discount

### 5.9× peak is best-case, 3-run avg is ~127 tok/s
The note reports 154 / 125 / 99 tok/s across 3 runs on RTX 4090, with acceptance rates 85% / 65% / 50%. The **mean is 126 tok/s @ 67% acceptance**, and the variance (54 tok/s range, 35pp acceptance range) is larger than the headline delta to the next-best config. The 5.9× number divides 154 against 26 tok/s from Ollama's default (no spec-dec, KV not quantized, no FA). An apples-to-apples `ik_llama.cpp` no-spec-dec baseline is missing — we should assume the 5.9× is closer to **2.5–3× over a tuned non-spec baseline**, not 5.9× over an inference engine in good faith. When an anonymous community note reports a 3-run sample with ~50 pp acceptance-rate range, the peak run is selection-biased — the reporter observed three numbers and chose which framed the strongest headline. The **median (125 tok/s)** is the number to remember, and even that is GPU-only.

### Same-family draft heuristic: the durable takeaway
The one result worth banking is architectural: **Qwen3-1.7B Q4_K_M beats a Qwen3-4B distilled draft on net throughput (154 vs 85 tok/s) despite lower acceptance**. The draft forward-pass cost dominates the acceptance gain past a certain ratio — smallest-draft-that-preserves-vocabulary wins. This confirms the same-family heuristic for any future target where we revisit speculative decoding.

The converse corollary is worth noting because it is the trap we avoided with our earlier DFlash work: **a fancy custom-trained draft (DFlash, MTP, distilled) can lose to a vanilla same-family smaller model** when the custom draft's forward-pass cost on the target hardware is higher than the simple alternative. The community note's 1.7B-beats-4B result is the GPU version of the same phenomenon we measured on CPU. Any future CPU draft work on dense/hybrid targets should default to "smallest-same-family" as the null hypothesis and require strong evidence to deviate.

### 128K–192K context scaling: plausible or optimistic?
Sustained 126–159 tok/s at 128K–192K with Q4 KV + FA is **optimistic but not impossible on a 24 GB card**. Q4 KV of a 27B hybrid at 128K ≈ 3–4 GB (reduced by the 3:1 GDN ratio — only 16 of 64 layers hold conventional KV at all, the other 48 hold small recurrent state); FA keeps attention compute bounded. The bigger risk is **acceptance-rate collapse on long contexts** (cited elsewhere: Qwen acceptance went 61% → 0.9% → 0.0% across consecutive vLLM requests in issue #36872) — a single-run anecdote doesn't disprove the failure mode. This is also **exactly the regime where EPYC would most want speculative decoding** (long-context decode is the one place CPU tokens/sec matters visibly to a user waiting on a large refactor) — so a durable answer for 128K+ decode would be structurally valuable, but the community note doesn't deliver one.

### Contradicting evidence summary
- **thc1006 19-config sweep** on Qwen3.6-35B-A3B + 0.8B draft, RTX 3090, post-PR-#19493 (2026-04-19): **no net speedup**. Note this is MoE hybrid, not dense hybrid — architectures differ. Relevant here because it establishes that even on recent GPUs (Ampere), spec-dec results on 3.6-family hybrids can be null; the 4090-Ada-Lovelace + specifically-dense-FFN result in intake-455 is one combination that works, not a general claim.
- **vLLM issue #36872**: Qwen3.5-35B-A3B-FP8 spec-dec gibberish, throughput collapse. Demonstrates that acceptance-rate stability across consecutive requests is not guaranteed even when a single run looks good.
- **Our own CPU history** (`handoffs/completed/ssm-hybrid-acceleration.md`): on Qwen3.5-27B specifically (same architecture class), "2-token batch ≈ Nx single decode cost due to sequential recurrent processing. Spec-dec is not viable — verification batches cost ~Nx single decode."
- **Net**: three independent signals that **non-verification-wall regimes are the exception, not the norm** for Qwen3.5/3.6 hybrid family. The intake-455 GPU result is a positive outlier, not a durable datapoint.

## CPU Feasibility for EPYC 9655

### Model memory footprint at Q4_K_M
Unsloth ships `unsloth/Qwen3.6-27B-GGUF` with Q4_K_M at **16.8 GB** (file size). Active per-token weight read ≈ 0.55 bytes/param × 27B ≈ **14.9 GB/token** (file size includes metadata/bias; active bytes is slightly less). This sits comfortably on a single NUMA quarter (48 threads, ~115 GB DRAM budget per NPS4 node), with room for KV cache and scratch. The 16.8 GB weight set replicates across 4 NUMA quarters for NUMA-4-way concurrency = 67.2 GB on-host weight memory — a reasonable tax given our 1.1 TB budget, and well under the 330 GB shared-weights footprint currently used by the full production stack. No storage or mlock concerns.

A Q8_0 quant (~28–29 GB projected from the Q4_K_M / param ratio) would also fit, and on prior 27B hybrid testing Q8 was actually **faster** than Q4 for decode — see `qwen36-production-upgrade.md`: "Q8 faster than Q4 (25.6 vs 24.4)" for 35B-A3B, and `feedback_cpu_decode_bw_bound` explains why on dense/hybrid workloads: quant-specific dequant cost shifts the effective bytes/token. Worth including Q8_0 in the probe sweep if disk budget permits.

### Expected decode throughput without spec-dec (BW roofline)
Using the calibrated EPYC 9655 BW figure from `feedback_cpu_decode_bw_bound` and `cpu-inference-optimization-index.md` — **460 GB/s effective** aggregate across 12-channel DDR5-6000 (not 920; the 920 figure in the task description is theoretical peak, not effective):

| Quantity | Value |
|---|---|
| Effective aggregate BW (12-channel DDR5-6000) | 460 GB/s |
| Active weights / token (Q4_K_M, 27B) | ≈ 14.9 GB |
| **Theoretical BW ceiling** | **460 / 14.9 ≈ 30.9 tok/s** |
| Observed BW utilization on hybrid Q4 (from 27B 7.5 t/s ref) | ≈ 24% of roofline |
| **Projected realistic single-instance decode** | **~7.5–9 tok/s** |

This matches the existing measurement in `progress/2026-04/2026-04-24.md` — "Qwen3.5-27B dense hybrid ≈ 7.5 t/s — pure BW-bound on the 27B dense weight read per token." Qwen3.6-27B should **decode at the same ~7–10 tok/s range** on EPYC 9655 with 96–192t, since the architecture class, active-weight bytes, and BW roofline are unchanged; only post-training weights moved.

A narrower-thread NUMA-4-way variant (4×48t single-instance decode at ~7.5 t/s each) would yield **~30 tok/s aggregate** if concurrent-request load can exploit it — comparable to the current frontdoor (Qwen3.5-35B-A3B, ~50 agg) but at 15 GB footprint per instance rather than 20 GB.

### Does spec-dec help CPU at all?
The `feedback_qwen35_27b_architecture` memory states: "spec-dec is dead on CPU for this model [Qwen3.5-27B] (exhaustively tested)... The Delta Net recurrent layers have critical implications: sequential token processing on CPU (kills spec-dec)." Qwen3.6-27B **inherits this architecture wholesale** — same 3:1 GDN:attention ratio, same DeltaNet recurrent formulation. This is the central claim that needs to be tested against the new model card, not assumed: the architecture dump from the Qwen3.6-27B config (`16 × (3 × GDN → FFN → 1 × GatedAttn → FFN)`, 48 GDN heads, 128 head dim) is byte-for-byte the same **shape** as 3.5-27B. No announced change to the GDN recurrence formulation. The post-training differences (MTP training, preserve_thinking) do not touch the forward-pass dependency structure.

The verification-wall mechanism: to verify N draft tokens, the target must process them through 48 sequential GDN layers, each of which maintains recurrent state. On CPU there is **no parallel scan** — each token traverses the recurrence in sequence, so N-token batch verification costs ≈ N × single-decode, not the ≈ 1× of pure-attention verification. The draft savings cannot amortize the verification cost. Our prior testing on 3.5-27B (captured in `handoffs/completed/ssm-hybrid-acceleration.md`) measured this directly: a 2-token verification batch cost **~1.9× single-decode**, not the ~1.05× that pure attention delivers.

**The "dense" label in intake-455 does not change this** — the FFN being dense (vs MoE) is irrelevant; what kills CPU spec-dec is the **GDN recurrence**, which is present in both 3.5-27B and 3.6-27B. Unless Qwen3.6-27B's GDN implementation has a materially different recurrence shape than 3.5-27B's (no evidence for this in the model card or community reviews), **spec-dec remains CPU-dead for this architecture**. The community note's 5.9× GPU result is enabled specifically by GPU parallel-scan kernels for GDN recurrence — a capability that has no CPU counterpart in llama.cpp today.

The only way CPU spec-dec becomes viable for this family is the **log-linear GDN** path tracked in `log-linear-gated-deltanet-readiness.md` — O(log L) state that would permit parallel verification even on CPU. Still blocked on pretrained log-linear checkpoints (no vendor has released one for a Qwen-class target yet).

### Comparison to current production 35B-A3B
| Metric | Qwen3.5-35B-A3B (production) | Qwen3.6-27B (candidate) |
|---|---|---|
| Architecture | Hybrid SSM + MoE (3B active / 35B total) | Hybrid SSM + Dense FFN (all 27B active) |
| Active bytes/token (Q4_K_M) | ≈ 1.8 GB (A3B sparsity × Q4) | ≈ 14.9 GB |
| BW roofline / token | 460 / 1.8 ≈ 255 tok/s | 460 / 14.9 ≈ 31 tok/s |
| Measured single-instance decode | ~12.7 t/s | ~7.5–9 t/s (projected) |
| Measured NUMA-4-way aggregate | ~50.8 t/s | ~30 t/s (projected) |
| BW utilization (of roofline) | ~5% (weakly BW-limited) | ~24% (BW-bound) |

The 35B-A3B wins on **per-instance decode and NUMA aggregate** by a large margin because A3B sparsity reduces active-weight reads by ~8×. Qwen3.6-27B can't beat this on raw throughput for CPU decode. Its case has to be made on **quality per token**, not tokens per second.

Note that the 35B-A3B **utilization is only ~5% of roofline** — its bottleneck is not DRAM bandwidth but rather expert routing overhead + the GDN recurrent-state serial dependency. The 27B dense-active model is closer to the BW ceiling (~24%) and has *less* headroom from any remaining CPU optimization work; there is no latent throughput to unlock via CPU1/CPU4/CPU3 levers. Conversely, the 35B-A3B has **huge** headroom to the BW ceiling, which is exactly what CPU1 TP-sharding is trying to exploit (and why the CPU-optimization index focuses there, not on dense-27B workloads).

## Is Qwen3.6-27B the right architecture for EPYC?

### "Dense" vs A3B MoE — different operating points
A3B MoE is the correct operating point for CPU-bandwidth-bound decode because it **shrinks the per-token weight read** dramatically (3B active vs 27B active = 9× less bytes/token). Qwen3.6-27B pays full-27B bytes on every token — the exact opposite of what CPU inference wants. HOWEVER: A3B's 3B active path has a **quality ceiling** that a 27B active path does not — the 8+1 experts per token do not compose arbitrary capability. The 27B active path can reason end-to-end with every parameter. The published SWE-bench Verified numbers concretize this: 3.6-35B-A3B 73.4%, 3.6-27B 77.2% — the dense-FFN 27B beats its MoE sibling on hard agentic coding by ~4 pp despite being smaller. This is the case for keeping the 27B in the stack as a quality escalation target, not as a throughput play.

### Does 27B active have a place in the EPYC stack?
Possibly, in one specific role: **coder escalation / deep-thinking slot** where throughput matters less than quality and the user is already willing to wait for 8–10 tok/s. Current `coder_escalation` is Qwen2.5-Coder-32B Q4KM at ~43.3 t/s (4×48t aggregate); Qwen3.6-27B would be materially slower per request (~7–9 t/s per instance) but brings **SWE-bench Verified 77.2** (vs Qwen2.5-Coder's ~54-60% range on the same benchmark) and **preserve_thinking / MTP-trained weights**. This is a legitimate quality-vs-speed trade for the escalation slot that might not be worth it for frontdoor.

Against `worker_explore` (currently Qwen3-Coder-30B-A3B Q4KM, 39.1 t/s per instance): Qwen3.6-27B loses on throughput by ~4–5× and doesn't obviously win on quality at the worker role's request shape — worker_explore requests are typically high-breadth exploration where A3B's speed advantage matters. Not a swap candidate.

Against `frontdoor` (Qwen3.5-35B-A3B Q4KM, ~50 t/s aggregate): Qwen3.6-27B is net worse (throughput collapses, latency increases, quality gain narrower at frontdoor-typical prompts which are routing decisions and small syntheses). Not a swap candidate.

Against `architect_coding` (REAP-246B Q4KM, 16.5 t/s aggregate, 139 GB): different operating point entirely — architect handles multi-file refactors at long context where the 246B active path is the capacity floor. Qwen3.6-27B cannot replace it.

### Candidate role: coder escalation — only
The narrow-but-real case is **coder_escalation** on difficult agentic coding requests where the request is already routed to escalation *because* frontend spec-dec / A3B didn't produce a solution. In that regime, a 7–9 t/s Qwen3.6-27B with SWE-bench 77.2 beats a 43 t/s Qwen2.5-Coder with SWE-bench ~55%, because the latter isn't solving the problem at any speed. Latency of an escalation request is already expected to be tens of seconds — the user is waiting for *quality*, not throughput. This is the only EPYC slot where the dense-27B-active trade-off makes sense.

A secondary consideration: Qwen3.6-27B could supplement (not replace) the 35B-A3B frontdoor as a **second-opinion / escalation path for hybrid-moe-reject requests**. The orchestrator already has the routing primitives for this kind of conditional escalation (`RoundRobinBackend`, q-scorer). This is orchestrator work, not inference work, and should not be scoped into the CPU probe.

## Refined Assessment

**Relevance: upgrade from `low` to `medium-low`** (not full medium). Justification: the community GPU claim is non-portable and not the reason for the upgrade. The upgrade is because the **Qwen3.6-27B model itself** is a fresh, Apache-2.0, CPU-loadable candidate with genuinely strong coding benchmarks that warrants a CPU throughput/quality probe for the **coder_escalation slot specifically**. The overall CPU picture (7–9 t/s, BW-bound, spec-dec dead per hybrid SSM inheritance) is known with high confidence even before any measurement, so the probe is cheap. Full `medium` would require an architectural signal we do not have — e.g., if the 3.6 GDN had a materially different state shape than 3.5, or if an independent benchmark confirmed the 128K-context claim on CPU.

**Novelty: stays medium.** The same-family small-draft heuristic is a durable (but already-known) architectural point. The model's post-training gains are interesting but not architecturally novel. The 3:1 GDN-hybrid pattern is identical to 3.5-27B — zero architectural novelty vs the prior generation. The one genuinely new signal is **MTP-trained weights in a dense-FFN Qwen**, which enables native multi-token prediction at serve time on GPU — but native MTP only helps CPU when paired with a parallel-scan GDN kernel we do not currently have. Keep novelty at medium on the merits of (a) the small-draft heuristic and (b) the MTP-trained dense-FFN being a new training-recipe datapoint; do not upgrade to high.

**What to record in intake**: add a one-liner noting that the "dense" descriptor in the community note is misleading — Qwen3.6-27B is hybrid Gated-DeltaNet + Gated-Attention with dense FFN, same architecture class as Qwen3.5-27B. This affects spec-dec reasoning in any future read, and is the single most important correction to propagate to downstream consumers of the intake record.

## Concrete Next Actions

Actions are ordered by decisive value per unit effort. Items 1 and 2 are in-scope for immediate EPYC work; items 3–5 are gating/governance only.

1. **CPU throughput probe (cheap, decisive)** — download `unsloth/Qwen3.6-27B-GGUF` Q4_K_M (16.8 GB), bench single-instance decode on 48/96/192 threads and NUMA-4-way aggregate using the existing `bench_numa_*.sh` harness. Expected: ~7.5–9 t/s per instance, ~30 t/s aggregate. Anything materially different from this range is a surprise worth investigating. Report in the same table shape as `qwen36-production-upgrade.md` for consistency. Budget: one afternoon of wall time, < 100 GB disk.
2. **Coder escalation A/B — quality only** — against Qwen2.5-Coder-32B on the same agentic-coding eval harness used for the 3.6-35B-A3B benchmark (per `qwen36-production-upgrade.md`). If Qwen3.6-27B hits the SWE-bench numbers claimed (77.2), it's a candidate to replace coder_escalation even at 5× lower throughput. If it doesn't, close the evaluation.
3. **Do NOT run CPU spec-dec experiments** — architecturally foreclosed by the GDN verification-wall inherited from 3.5-27B. Repeating the experiment would be compute waste. Cite `handoffs/completed/ssm-hybrid-acceleration.md` and `feedback_qwen35_27b_architecture` in the handoff close-out.
4. **Bookmark for GPU-acquisition trigger** — the 154 tok/s RTX 4090 claim is the first published Qwen3.6-27B + 1.7B-draft GPU datapoint. At GPU-acquisition trigger, attempt reproduction (use ik_llama.cpp flags as cited: `--draft-max 12 --draft-min 3 --draft-p-min 0.6`). Target: match or exceed 126 tok/s mean (not the 154 peak).
5. **If probe confirms ~8 t/s and coder eval passes** — open a sibling handoff under `qwen36-production-upgrade.md` for the coder-escalation swap; do not mix with the 35B-A3B architect upgrade tracked there. The handoff should explicitly scope to coder_escalation only — frontdoor and worker_explore are out of scope and should not be revisited.

## Risks and Caveats

1. **The CPU probe cost is low but not zero.** One download (16.8 GB Q4_K_M, ~17 GB Q8_0 if we also want it), one afternoon of bench time, and the re-calibration work in `progress/`. Acceptable if the probe is used to justify the escalation slot swap; wasted if no escalation-eligible workload exists.
2. **SWE-bench Verified 77.2 is Qwen-reported.** Independent replications on third-party infrastructure (Simon Willison spot-checked — [primary reference](https://simonwillison.net/2026/Apr/22/qwen36-27b/)) are consistent, but no adversarial red-team benchmark has been published yet. Treat the number as a strong upper bound on real-world coder quality.
3. **Preserve_thinking / MTP served features may not all be exposed** through the current llama.cpp patch set. Before the coder-escalation swap, verify that the relevant serve-time flags (`preserve_thinking`, MTP step size) are plumbed through our orchestrator. If they are not, the quality-per-token argument weakens.
4. **Storage budget on `/mnt/raid0`** is under pressure from GLM-5.1-REAP (325 GB) and other recent downloads. The 16.8 GB Q4_K_M fits, but if we also want Q8_0 for comparison (~29 GB) the combined add should be scoped against the GLM-5.1 eval's 92 GB remaining window in `glm51-reap-cpu-evaluation.md`.

## Open Questions

- Does the Q8_0 > Q4_K_M decode-speed pattern observed on 35B-A3B transfer to 27B dense-FFN hybrid? (Hypothesis: yes, because dequant overhead is similar and the dense FFN spends proportionally more time in matmul than A3B's tiny active path.) Settled by the probe in Next Action #1.
- Is MTP-trained weights worth anything on CPU *without* parallel-scan GDN kernels? (Hypothesis: no — the MTP head produces candidate tokens, but verifying them still traverses the same sequential GDN recurrence that kills conventional spec-dec.) Would need a one-off test with MTP enabled to confirm, probably not worth the C++ cost to wire up.
- Would `--reasoning on --reasoning-format deepseek --jinja` (the GLM-5.1 flag set) compose cleanly with preserve_thinking on Qwen3.6-27B? Relevant if we want the "deep thinking" escalation to feature-stack both.

## Sources

- Primary model: [Qwen/Qwen3.6-27B on HuggingFace](https://huggingface.co/Qwen/Qwen3.6-27B)
- GGUF build: [unsloth/Qwen3.6-27B-GGUF](https://huggingface.co/unsloth/Qwen3.6-27B-GGUF) (Q4_K_M = 16.8 GB)
- Architecture details: [Qwen3.6-27B architecture — Mervin Praison](https://mer.vin/2026/04/qwen3-6-27b-dense-hybrid-attention-and-thinking-preservation/), [HackerNoon coverage](https://hackernoon.com/qwen36-27b-brings-open-weight-vision-and-coding-power), [MarkTechPost release summary](https://www.marktechpost.com/2026/04/22/alibaba-qwen-team-releases-qwen3-6-27b-a-dense-open-weight-model-outperforming-397b-moe-on-agentic-coding-benchmarks/)
- Coding benchmark context: [Simon Willison — Qwen3.6-27B: Flagship-Level Coding in a 27B Dense Model](https://simonwillison.net/2026/Apr/22/qwen36-27b/), [Build Fast with AI review](https://www.buildfastwithai.com/blogs/qwen3-6-27b-review-2026), [Let's Data Science](https://letsdatascience.com/news/qwen36-27b-delivers-flagship-coding-in-27b-dense-model-fd698bba)
- Community-note origin: intake-455 (inline, 2026-04-24) — tracked in `handoffs/active/gpu-acceleration-path.md` and `handoffs/active/qwen36-production-upgrade.md`
- Prior-art CPU measurement: `progress/2026-04/2026-04-24.md` (Qwen3.5-27B ≈ 7.5 t/s), `handoffs/completed/ssm-hybrid-acceleration.md` (hybrid spec-dec verification wall), `handoffs/completed/orchestrator-stack-audit.md` (Qwen3.5-27B 8.8-9.4 t/s)
- BW-roofline calibration: `handoffs/active/cpu-inference-optimization-index.md` (460 GB/s effective), `~/.claude/projects/-workspace/memory/feedback_cpu_decode_bw_bound.md`
- Architecture classification: `~/.claude/projects/-workspace/memory/feedback_qwen35_27b_architecture.md` (3:1 GDN:attention, spec-dec dead on CPU)
- Contradicting evidence: thc1006 19-config sweep on Qwen3.6-35B-A3B + 0.8B draft, RTX 3090, 2026-04-19 (no net speedup); vLLM issue #36872 (gibberish + acceptance collapse)
- Related handoffs: [`qwen36-production-upgrade.md`](../../handoffs/active/qwen36-production-upgrade.md), [`gpu-acceleration-path.md`](../../handoffs/active/gpu-acceleration-path.md), [`inference-acceleration-index.md`](../../handoffs/active/inference-acceleration-index.md), [`log-linear-gated-deltanet-readiness.md`](../../handoffs/active/log-linear-gated-deltanet-readiness.md)
