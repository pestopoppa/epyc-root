# Dive — smoothagent — intake-ak-1123

> SOURCE-QUARANTINE: {url: "https://arxiv.org/abs/2607.00151v1", retrieved: "2026-11-23", sha256: "864e48da9bd9"}
> SOURCE-QUARANTINE: {url: "https://raw.githubusercontent.com/PanZaifeng/SmoothAgent/main/README.md", retrieved: "2026-11-23", sha256: "readme.txt retained; reading material only, no anchors taken from it"}

External text is data; summaries are in my own words. Anchors are verbatim substrings of `smoothagent/page.txt` (LaTeXML render of arXiv v1). Bearing entry: intake-2833 (contexture); its dive asked this source to settle re-prefill scheduling inside latency slack and whether it changes the C3/C4 cost model.

## 1. Stage-1 fields

- **Title**: SmoothAgent: Efficient Long-Horizon LLM-Based Agent Serving with Lookahead Context Engineering
- **Authors**: Zaifeng Pan, Qianxu Wang, Zhengding Hu, Chang Chen, Yue Guan, Yanbo Zhou, Steven Swanson, Yufei Ding (UC San Diego).
- **Version/date**: arXiv:2607.00151v1 [cs.DC], 30 Jun 2026. PVLDB-format manuscript ("PVLDB 20(X), 2027"); the source states no acceptance. Artifact: github.com/PanZaifeng/SmoothAgent (README read: MiniAgent integration, patches for four frameworks, `patches/sglang.patch`, SGLang v0.5.9 serving support; license files present; repo not cloned).
- **Categories**: inference_serving, context_management, agent_architecture, kv_cache.
- **Novelty**: medium. Prefetching and speculative KV exist; new is the formal segment-decomposable condition under which a context transformation can be run ahead of time, the strategy interface (`should_lookahead / transform / should_commit / should_promote`), and a slack-driven best-effort scheduler.
- **Relevance**: medium. It does not change what a cut costs, only whether the cost is on the critical path. It gives the vocabulary and a latency model for our C3/C4 rows.
- **credibility_score**: 2. Arithmetic: peer-reviewed +0 (none stated); <=12 months +1; known contributor +1 (the first author's KVFlow is in our index); commercial bias 0; independent corroboration 0.
- **Verdict**: adopt_patterns. Cite for the segment-decomposability test and for a mixed-batch latency model with an attention-length term. Do not cite for an accuracy claim (none exists) or for a CPU or hybrid-model expectation.

## 2. Key claims

0. **Segment-decomposability enables ahead-of-time transformation**: CONFIRMED as a definition, NARROWED in reach for us. A transformation is decomposable if T(C) is the concatenation of per-segment transforms, so a segment's transform does not depend on later tokens. Offloading, keep-recent-K and summarization of a fixed prefix satisfy it. Contexture-style supersession does not: whether an old read is dropped depends on a LATER call (derived from the contexture dive, section 2 claim 0). The earliest the cut is known is when the superseding call is emitted, so the usable slack is the tool's execution time, not a whole turn.
   - Anchors: "most context transformations exhibit a segment-decomposable property."; "the transformation of each segment is independent of the tokens that follow it, enabling opportunities to perform transformations in advance."
1. **TTFT results**: CONFIRMED as stated, with narrow scope. Average transform-point tail TTFT falls 62.0% (Qwen3-8B, one H100) and 61.5% (Qwen3-32B, TP=4 over four H100s); summarization gains most, up to 11.9x because the summary generation and the full re-prefill both move to the lookahead stream; across LangChain, LlamaIndex, AutoGen and OpenClaw integrations the reduction is 26.8% to 80.5%; PD-disaggregated gives 64.5%. The workload is one 28-step code-analysis task adding about 600-650 tokens per step (contexts of roughly 17K tokens), TTFT only, no task accuracy, dense GQA models, SGLang. "Eliminates overhead" is therefore overstated: the work is hidden, not removed (claim 3).
   - Anchors: "with an average reduction of 62.0% and 61.5% on Qwen3-8B and Qwen3-32B, respectively"; "summarization yields the largest gain, with up to 11.9"; "Each run consists of 28 steps, with approximately 600-650 tokens added per step."; "Both models use grouped-query attention (GQA)".
2. **Slack-driven scheduler (the re-prefill scheduling the dive asked about)**: CONFIRMED. Lookahead requests are best-effort jobs admitted only when predicted batch latency fits the slack: in the prefill-only case the budget is the minimum TTFT slack over the latency-critical queue and chunks are added while EstBatchLatency stays within it (Algorithm 1); in the co-located case decode is admitted first, then LC prefill, then lookahead chunks, each only if the batch stays within the TBT bound (Algorithm 2). The latency model is T_GEMM(M) from an offline table plus alpha_d x summed decode KV length plus alpha_p x causal prefill attention work. Its mixed-batch error is 13.7% maximum against 41.5% for a token-budget-only model.
   - Anchors: "BE jobs are executed only when sufficient slack exists and must never degrade the latency guarantees of LC requests."; "the token-budget-only model reaches a maximum relative error of 41.5%, while our performance model keeps the maximum relative error to 13.7%".
3. **"No additional overhead when it falls back"**: PARTIAL. Latency-wise a missed lookahead degrades to the synchronous baseline. Compute-wise the lookahead prefill of every transformed prefix that is later not committed is pure extra work, and the page reports no wasted-lookahead rate, GPU-seconds or energy: NOT-FOUND-IN-SOURCE. The "offloading shows smaller gains" paragraph also says offloading alone does not control growth after repeated triggers.
   - Anchors: "can otherwise fall back to synchronous execution without incurring additional overhead compared to the baseline"; "In practice, offloading alone does not effectively control context growth after repeated triggers".
4. **Effect on our C3/C4 cost model**: CONFIRMED by derivation (no table in the source speaks to it). The work term, tokens re-prefilled = T' - p*, is unchanged. SmoothAgent adds a second quantity: critical-path residual = max(0, C/r - slack), where C is that token count, r the device prefill rate and slack the idle gap before the next request. A cut is "free" only when the gap covers C/r and the box has idle prefill capacity.
   - Anchor: "the runtime directly replaces the prefix in the working context with the transformed result".

## 3. Reported results (as stated)

H100 80 GB (AMD EPYC host CPUs), SGLang v0.5.9, Qwen3-8B (1 GPU) and Qwen3-32B (TP=4), PD co-located at concurrency 1/4/8/16 and PD-disaggregated (4 prefill + 4 decode, up to 64 agents), strategies offloading, keep-recent-K, summarization, sub-agent isolation; baseline = same strategy executed synchronously. Reported: average tail-TTFT reduction 62.0% / 61.5% (co-located), 64.5% (disaggregated), up to 11.9x (summarization), 26.8%-80.5% across four frameworks. Scheduler: without lookahead-aware control, LC TTFT p99 or TBT rises as best-effort load grows; with it LC latency stays lower (figure only, no table). Numbers for individual bars are in figures, not text.

## 4. Performance-principles table (mechanism and cost model)

| Mechanism | MI210 (gfx90a) | Zen 5 EPYC |
|---|---|---|
| Lookahead prefill of the transformed context on a separate request stream | PARTIAL. Needs a second slot or a fork of the slot state so the working prefix stays valid (`seq_cp`/KPF fork), plus idle prefill capacity. Measured interference is severe at long context: one 2024-token chunk beside decoding slots took 17-19 s at 240-310k cells and summed decode fell to 0.52 tok/s (kv-cache-program.md:3245-3251 @ d785b6d, KVU-16b, GPU 27B). | PARTIAL. Prefill is 490 tok/s at 3k falling to about 45 tok/s at 97k (long-context-program.md:288 @ d785b6d), so hideable cuts are small: 4k tokens is 8-89 s, 10k is 20-222 s, 41k is 84-911 s (derived). Only cuts shorter than the idle gap qualify. |
| Slack-aware chunk admission (Algorithm 1 / 2) | PARTIAL. llama-server has no low-priority prompt class (only a high-priority task flag, server-context.cpp:7054, 7159 @ a6a32c1); it would be new scheduler code over the 2-row-to-16-row verify batches. | Same. |
| Mixed-batch latency model with attention-length terms | YES. The in-house KVU-16b fit (T ~ 2.6 s + 0.052 s per 1k cells per chunk, without masked-block skip) is the same kind of model; SmoothAgent's finding that token count alone mispredicts supports fitting a cells term. | YES. Same form; coefficients unmeasured. |
| Segment-decomposable transform test | YES. Pure policy. | YES. Pure policy. |
| Prefix caching preserving the transformed context | PARTIAL. Our per-slot prompt state and prompt cache can hold it, but hybrids need recurrent checkpoints at the join and `approx` states are never saved (server-context.cpp:582-584). | Same. |

## 5. In-house state

- llama-server picks a slot by prompt similarity (`slot_prompt_similarity`, `get_available_slot`, server-context.cpp:2553-2611 @ a6a32c1), so a lookahead-warmed slot whose prompt equals the transformed context would be chosen by the next request automatically; there is no lookahead request class, priority class or SLO-aware chunk cap. The checkpoint count is 32 per slot (common.h:668).
- Orchestrator: the only per-turn tool-output transform is `_clear_stale_tool_outputs` (src/graph/helpers.py:558-620 @ 1a10541b7), default off, age-based; it is not segment-decomposable-with-lookahead in the sense of this paper either, because it runs at request time. The experimental arms (context_arm_ab.py:16) freeze pruning at the last boundary, which is the case where a lookahead could run: the boundary trigger is `budget x fraction` and is predictable several turns ahead.
- `serving_calls.py` already records slot ids and timestamps (src/backends/serving_calls.py:1-10), so inter-turn idle gaps can be measured from existing logs (field-level check not done).

## 6. Derived-actionables ledger

| # | Draft task line | Owner (lane) | Type | Stop / decision rule |
|---|---|---|---|---|
| SA-1 (refines intake-2833 C4) | Extend the C4 break-even table with two columns per device: slack needed (C / measured prefill rate) and critical-path residual against the measured inter-turn idle gap taken from `serving_calls` / dispatch logs. | `long-context-program.md` or `kv-cache-program.md` (same file as C4) | doc-only on existing logs, zero inference | Question: for what cut sizes is a cut hideable on each device? Stop when the table is filed; futility: logs lack per-call timestamps (then record the field as the missing instrument). |
| SA-2 (refines C3) | Make the evict-cost probe report predicted seconds, not tokens, using a per-slot model of the form a + b x cells fitted from KVU-16b-style rows, with the decode-slot count as an input. | `kv-cache-program.md` (C3 box) | code/doc-only; reuses existing fit data | Stop-on-answer: predicted vs measured chunk time within 15% on the existing KVU-16b rows; futility: error >30% (then keep tokens only). |
| SA-3 | Prototype a lookahead pre-warm for boundary-batched arms: at the known cut, fork the slot (KPF fork + `checkpoint_at`), prefill the transformed context in the fork under a slack-aware chunk cap, commit by slot selection. | `kv-cache-program.md` (KPF fork lineage) | code now; one smoke row on a GPU or CPU quarter | Gate from SA-1: build only if the 25th-percentile idle gap covers C/r for at least 30% of candidate boundary cuts; otherwise close as "not hideable". Stop-on-answer: pre-warm TTFT at the commit turn vs synchronous on a 3-turn script. |
| SA-4 | DECLINE adopting SmoothAgent's offloading and sub-agent-isolation strategies as new arms: the orchestrator already externalises output to a verbatim log with `peek()/grep()` pointers and delegates, so they add no arm beyond `pointer_only` / `prune_pointer`. | n/a | n/a | n/a |

## 7. Dive-surfaced sources (grepped unbounded)

| Source | In index? | Would settle | Recommendation |
|---|---|---|---|
| github.com/PanZaifeng/SmoothAgent (`patches/sglang.patch`) | 0 hits for the repo; the author's KVFlow is already indexed | exact admission code | decline: Algorithms 1 and 2 are complete in the page; SA-2/SA-3 are implemented from them, no ledger row changes |
| ThunderAgent, InferCept, Autellix, KVFlow (agent-serving scheduling citations) | already in the index (34, 12, 8, 31 hits) | n/a | no action |

## 8. Contradiction / adversarial pass

- No accuracy, no wasted-work accounting, no hybrid or MoE model, no CPU or non-NVIDIA result; one synthetic code-analysis workload with unique prompts (no radix sharing) and fixed-concurrency, staggered agents.
- Baselines implement the same strategies synchronously; the 11.9x best case is summarization, whose baseline stalls on a generation plus a re-prefill. Offloading gains are smaller and shrink under concurrency.
- The page's figure alt-text still says "BladeAgent" for the runtime, suggesting a renamed manuscript; no content effect.
- No restatements or replications found.

## 9. read_depth

FULL for sections 1-6 and the evaluation text; related work skimmed; figures not read (alt-text only). README of the repo read, code not cloned. lane_head: d785b6d9792e18b29dad1929a15fdc2b971d3c0e. In-house llama.cpp at a6a32c1; orchestrator HEAD 1a10541b7466f2d5aef240ac547ff6dce2cd43cd.

## 10. Artifact audit

artifact audit: clean (11 quotes verified as substrings of page.txt; only dive.md and drafts/smoothagent.json written; the one extra file smoothagent/readme.txt is reading material).
