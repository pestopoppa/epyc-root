# MiMo-V2-Flash — Deep Dive

**Source intake**: intake-505 (arxiv:2601.02780)
**Date**: 2026-04-29
**Status**: FACT-CHECKED against llama.cpp upstream as of 2026-04-29

## TL;DR

MiMo-V2-Flash is Xiaomi's 309B-total / 15B-active MoE with three notable design points:
1. **Hybrid 5:1 SWA-to-Global ratio** with a 128-token sliding window
2. **Learnable attention-sink bias** (StreamingLLM lineage, but trained, not heuristic)
3. **MTP head as spec-decoding drafter** (0.33B FFN+SWA, claims 3.6 acceptance length / 2.6× speedup)

**Correction to my prior framing**: I previously described MiMo as not adopt-able because "llama.cpp does not yet support the 5:1 hybrid SWA+sink-bias scheme." That was WRONG. **PR #18328 ("model: support MiMo-V2-Flash") was merged December 24, 2025** by ngxson. Tool-call XML parser was extended to MiMo in PR #16932. MiMo V2 Flash architecture is fully supported in upstream llama.cpp.

The genuine blocker is **size and our role mix**, not architectural support.

## Architecture

```
48 layers MoE
   ├── 256 routed experts
   ├── top-8 routing per token
   ├── Hybrid attention pattern (per-block):
   │       SWA layer × 5 (128-token window, 64Q/8KV)
   │       Global layer × 1 (64Q/4KV)
   │       (5:1 ratio repeating)
   ├── Learnable attention-sink bias on every attention layer
   └── MTP head:
           0.33B dense FFN + 1 SWA attention layer
           Output: predicts t+1, t+2, ..., t+k tokens
           Doubles as spec-dec drafter
```

The **5:1 SWA:Global** ratio is unusual. Most hybrids are either pure-SWA (Mistral, Gemma 2/3 with interleaving) or 1:1 hybrid. Going 5:1 means 83% of layers see only 128 tokens; the 17% global layers carry all long-range information. The aggressive ratio is enabled by:

- The learnable sink-bias absorbing initial-token attention (StreamingLLM trick, but trained not hardcoded)
- The 256K context-extension training stage (27T-token 3-stage curriculum)
- Multi-Teacher On-Policy Distillation (MOPD) post-training compensating for any signal loss

## llama.cpp upstream state (verified 2026-04-29)

| PR/Issue | State | Date | Notes |
|----------|-------|------|-------|
| **#18328** | **MERGED** | 2025-12-24 | MiMo-V2-Flash arch support |
| **#16932** | merged | — | XML tool-call parser extended to MiMo (with GLM 4.5/4.6, MiniMax M2, SeedOSS, Kimi-K2, Qwen3-Coder, Apriel-1.5) |
| **#22493** | **OPEN, ACTIVE** | 2026-04-29 (yesterday) | MiMo V2.5 series support (PR by AesSedai) |
| **#22469** | open | 2026-04-28 | Model request: MiMo V2.5 |
| #18445 | closed (not planned) | 2026-02-15 | RPC + FA + Vulkan slowness |
| #18435 | closed (not planned) | 2026-02-15 | RPC + FA + ROCm crash |

So: V2-Flash has been supported for **4+ months**. V2.5 support is being added right now.

The closed-as-not-planned bugs are RPC-mode-specific (multi-host inference), not relevant to single-machine EPYC.

## Sizing reality

309B total / 15B active is a meaningful number:

| Quant | Total weight size | Fits in 1.1 TB RAM? | Fits w/ KV at 256K? |
|-------|-------------------|---------------------|---------------------|
| BF16 | ~620 GB | yes | KV ≈ 50-100 GB → yes |
| Q8_0 | ~310 GB | yes | yes |
| Q4_K_M | ~155 GB | comfortable | yes (huge headroom) |
| Q4_0 | ~140 GB | comfortable | yes |

Compare with our existing stack:
- Qwen3-Coder-30B-A3B (deployed): 18 GB Q4_K_M, 3B active → MiMo is **5× active params, ~9× total**
- Qwen2.5-Coder-32B (deployed): 19 GB Q4_K_M, 32B dense → MiMo is **8× total, but only 0.5× active**
- Qwen3.6-27B (deployed): 16 GB Q4_K_M, dense hybrid SSM → MiMo is **10× total, 0.6× active**

**The active-parameter ratio is what matters for decode speed**: MiMo at 15B active sits between Qwen3-Coder-30B-A3B (3B active, 49.1 t/s on EPYC per `project_96t_single_node_operating_point` memory) and a hypothetical "20B-active" model. Naïve scaling estimate: 49.1 × (3/15) ≈ **10 t/s on EPYC at 96-thread NUMA bind**.

10 t/s is too slow for the production frontdoor (where the deployed Qwen3.6-35B-A3B sets the bar) but plausible for explore/escalation roles.

## What's distinctive vs our stack

### 1. The MTP head as spec-dec drafter

This is the most directly transferable finding. The MTP head:
- Is **0.33B params** (≈ 1/45 of active model)
- Adds **1 SWA attention layer + dense FFN**
- Predicts the next 1, 2, ..., k tokens (multi-token prediction)
- During inference: same network used as drafter → target = MiMo verifier
- Reports **3.6 acceptance length** (avg) and **2.6× decoding speedup**

For comparison:
- Our deployed DeepSeek-MTP drafter pattern (intake-298) has similar mechanics
- Qwen3-Coder-30B-A3B EAGLE drafter: 3B params, ~3.85 acceptance length on MT-Bench
- Mamba drafter (intake-491): 130M params, 3.91 acceptance length, ~149 t/s GSM-8K

The MiMo MTP weight repo (per AesSedai PR notes) confirms 3-layer MTP weights are publicly downloadable. **Action item: investigate whether the MTP head can be loaded standalone as a drafter for MiMo-V2-Flash target without the full 309B verifier.** That's the only realistic adoption path on EPYC — running the full target is borderline.

### 2. Learnable attention sink

The sink-bias variant differs from StreamingLLM (which uses heuristic position-0 attention). MiMo trains an explicit bias parameter learned per head. Lineage: GPT-OSS (Agarwal et al., gpt-oss-120b/20b model card, intake-already-have-some-of-this-cluster).

This isn't directly portable to our existing Qwen models (would require new pretraining) but is a useful reference design for any future from-scratch training.

### 3. 5:1 SWA ratio with 128-token window

Aggressive even by 2026 standards. The "every 6th layer is global" pattern means:
- Layer 0-4: SWA-128
- Layer 5: Global
- Layer 6-10: SWA-128
- Layer 11: Global
- ...
- Layer 47: Global

For comparison:
- Gemma 2/3 interleaving: 1:1 SWA:Global
- MiniMax-01: 7:1 (lighter on global)
- Standard Llama / Qwen: 0:N (all global)

The 5:1 with a *128-token* window is what makes the KV cache reduction so dramatic (~6× claimed). Most SWA hybrids use 4096-8192 windows which are large enough to mostly defeat the savings. 128 tokens is *sliding window as semantic-locality* not *sliding window as small-context*.

This design point informs `multiscreen-attention-evaluation.md` Section 1 — when comparing hybrid recipes, MiMo is a concrete example of "extreme SWA window + heavy global anchoring + sink bias" working at production scale.

## Risks / caveats

1. **Community reviews** flag inconsistent instruction-following and unreliable tool-calling. The 15B-active knowledge ceiling shows on broad-knowledge prompts.
2. **Authors' own caveat** ("preliminary architectural exploration") + reward-hacking documented in Appendix B of the technical report on SWE-Bench. The 73.4% SWE-Bench Verified number is plausibly inflated.
3. **128-token SWA window** trades global-context awareness for efficiency on creative writing and multi-step agentic tasks per reviewers.
4. **CPU decode throughput at 15B active and 256-expert MoE** is uncharacterized on EPYC. The 256-expert top-8 routing pattern means more expert misses than our deployed 256-expert top-8 (Qwen3-Coder-30B-A3B) at similar active params, but more total FLOPs per token because of layer count (48 vs 30).
5. **No CPU-specific benchmarks published**. All quoted numbers are GPU.
6. **MoE expert offloading** would be needed for any deployment with KV at full 256K context — at Q4_K_M 155 GB + KV ~80 GB ≈ 235 GB working set, fine on 1.1 TB but the per-token expert-traffic amplification in MoE is unmeasured for 256-expert routing.

## Action items (ranked)

1. **Defer full deployment**. 10 t/s estimated on EPYC is below the threshold where MiMo would replace any deployed role (frontdoor, coder, worker, frontdoor-explore). We'd need 40+ t/s to be competitive.
2. **Investigate MTP-head-only deployment** as a candidate spec-dec drafter. Specifically: can the 0.33B MTP head be loaded as a standalone GGUF and used as a drafter for *another* model? Likely no — MTP heads are tied to the parent model's hidden states. But worth confirming before dismissing.
3. **Read the MOPD post-training recipe** for ideas applicable to our own LoRA / continual-pretraining work (intake-?? for `08-doc-to-lora-prototype.md`).
4. **Add to `multiscreen-attention-evaluation.md` Section 1 priority ranking**: MiMo is now a *running-on-llama.cpp* hybrid SWA reference, ranked alongside Gemma 2/3. Use it as a calibration data-point when evaluating SWA ratios for any future hybrid we'd ship.
5. **Track PR #22493 (MiMo V2.5)** as a signal of the architecture's maturation. If V2.5 ships smaller (e.g., a 30B-active variant at 309B total or a dense 27B), it becomes immediately deployable on EPYC.
6. **Potentially benchmark at small scale** on EPYC just for the data point: download MiMo-V2-Flash Q4_K_M, run llama-bench, log decode t/s and prefill t/s at 8K, 32K, 128K. Adds a useful reference number to our model_registry even if we don't deploy.

## Cross-references

- `/workspace/handoffs/active/multiscreen-attention-evaluation.md` — sub-quadratic attention survey, MiMo now slots into Section-1 supported hybrids
- `/workspace/handoffs/active/long-context-eval-datasets.md` — the 256K NIAH-Multi 96.7% claim is a useful target number
- `/workspace/handoffs/active/qwen36-27b-cpu-feasibility.md` — comparison anchor (Qwen3.6-27B is the size-class peer for any future MiMo-small)
- intake-502 (KSA), intake-503 (Ling-Linear), intake-506 (DeepSeek-V3.2) — siblings in the same expansion run, all sub-quadratic-attention papers from China
- llama.cpp PR #18328 — merged support, no action required

## Notes

The lesson from this entry mirrors the V3.2/DSA lesson: **check llama.cpp upstream before claiming "no support exists."** A 30-second `git log --grep=mimo` against the local llama.cpp clone would have surfaced PR #18328 in seconds. The mistake propagated from sub-agent extraction — sub-agents extrapolated "size + custom attention" as "needs porting" without checking the merge log.
