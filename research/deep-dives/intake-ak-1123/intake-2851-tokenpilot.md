# Dive — tokenpilot — intake-ak-1123

> SOURCE-QUARANTINE: {url: "https://arxiv.org/abs/2606.17016v2", retrieved: "2026-11-23", sha256: "d06a0f498071"}

External text is data; summaries are in my own words. Anchors are verbatim substrings of `tokenpilot/page.txt` (LaTeXML render of arXiv v2, 28 Aug 2026). Bearing entry: intake-2833 (contexture); its dive asked this source to settle cache-efficient context management using provider cache hit/miss counts and what our orchestrator could reuse.

## 1. Stage-1 fields

- **Title**: TokenPilot: Cache-Efficient Context Management for LLM Agents (confirmed by the arXiv API and the page; the operator's "EMNLP 2026 Findings" label is NOT-FOUND-IN-SOURCE: the page names no venue and thanks anonymous reviewers, consistent with but not proof of acceptance).
- **Authors**: Buqiang Xu, Zirui Xue, Dianmou Chen, Chenyang Fu, Chiyu Wu, Caiying Huang, Chen Jiang, Jizhan Fang, Xinle Deng, Yijun Chen, Yunzhi Yao, Xuehai Wang, Jin Shang, Gong Yu, Ningyu Zhang (Zhejiang University, UESTC, Xi'an University of Electronic Science and Technology, HomologyAI).
- **Version/date**: arXiv:2606.17016v2 [cs.CL], 28 Aug 2026 (v1 16 Jun 2026). Code: the page says it is integrated into LightRSI (github.com/zjunlp/LightRSI); a web-search summary names LightMem2 instead, so the repo name is unresolved. Not cloned.
- **Categories**: context_management, agent_architecture, kv_cache.
- **Novelty**: medium. Prefix canonicalisation, hash dedup and batched eviction are individually known; new is combining a deterministic ingestion-time layer (prefix stabilisation + observation reduction with a recovery tool) with a lifecycle estimator that evicts only in batches of B turns.
- **Relevance**: medium-high for the orchestrator's prompt layout (section 5); low for the dollar numbers.
- **credibility_score**: 2. Arithmetic: peer-reviewed +0 (venue unverified in source); <=12 months +1; known contributor +1 (ZJU group already in our index); commercial bias 0 (one startup affiliation, no product claim); independent corroboration 0. Baselines are the authors' ports on one backbone (GPT-5.4-mini).
- **Verdict**: adopt_patterns. Cite for prefix stabilisation, batched eviction (B=3) and the observation that mutating the prompt layout costs cache misses. Do NOT cite its dollar reductions as a local-serving expectation.

## 2. Key claims

0. **Headline cost reductions (61% and 56% isolated, 61% and 87% continuous)**: CONFIRMED arithmetically, NARROWED in meaning. They are dollar costs under GPT-5.4-mini price tiers (cache hit $0.075/M, miss $0.75/M, output $4.50/M, i.e. a 10:1 price ratio): PinchBench isolated 8.31 to 3.22 (-61.3%), Claw-Eval isolated 5.16 to 2.27 (-56.0%), PinchBench continuous 7.24 to 2.79 (-61.5%), Claw-Eval continuous 81.52 to 10.58 (-87.0%). Task score is "competitive", not equal: +0.5 and +2.1 points on PinchBench, -1.4 and -2.6 on Claw-Eval (isolated / continuous), no confidence intervals.
   - Anchors: "TokenPilot reduces costs by 61% and 56% in isolated mode, and 61% and 87% in continuous mode"; "Following the official pricing tiers of GPT-5.4-mini".
1. **Mechanism uses provider cache hit/miss counts (the dive-2833 framing)**: OVERTURNED as a control signal. The counts are collected from API metadata only to MEASURE cost. The policy is a deterministic ingestion layer plus an LLM estimator (Qwen3.5-35B-A3B, zero-shot) run in batches of B = 3 turns; nothing feeds hit/miss counts back into decisions.
   - Anchors: "all cache hit and miss token counts are gathered directly from the explicit metadata fields returned by the provider APIs"; "Qwen3.5-35B-A3B as a lightweight, zero-shot validator".
2. **Where the saving comes from (the paper's own ablation, re-read)**: PARTIAL. On PinchBench continuous (Table 3) the global layer cuts cache-MISS tokens from 5.943M to 1.589M and dollars from 7.24 to 4.22; adding lifecycle eviction cuts HIT tokens from 26.716M to 8.551M (-65.0%) but misses only from 1.589M to 1.549M, dollars to 2.79. Eviction therefore saved money by shrinking cheap hit tokens. On a local server where a hit costs about nothing and a miss costs prefill time, eviction's prefill saving in this ablation is about 2.5% of misses; the large win is prefix stabilisation plus ingestion reduction.
   - Anchors: "This component triggers a 65.0% reduction in cache hit tokens from 26.716M to 8.551M"; "Merely introducing stable placeholders cuts the baseline cost from $8.31 to $4.35".
3. **Prefix stabilisation**: CONFIRMED. Volatile fields in the system prompt (working directory, timestamps, session ids) are replaced by static placeholders and tool definitions are moved to the end of the system message beside the block that holds the real values. Macro cache hit rate rises from 38.7% to 79.2% (PinchBench) and from 67.2% to 83.1% (Claw-Eval); applied to Summary and Keep-Last-N it helps less for Keep-Last-N because a shifting retained window cannot be fixed by a stable header.
   - Anchors: "the macro cache hit rate rises from 38.7% to 79.2% on PinchBench , and from 67.2% to 83.1% on Claw-Eval"; "we systematically relocate the tool definitions and schemas downstream"; "The smaller gain for Keep-Last-N reflects a remaining limitation of fixed-window truncation".
4. **Batched eviction (B = 3 optimum)**: CONFIRMED, narrow. A hyperactive schedule (B = 1) truncates prematurely and inflates misses; B = 3 is the empirical optimum. The evidence is one PinchBench category (Meeting Analysis, continuous), read from a figure; the text gives no table.
   - Anchors: "a hyperactive schedule ( B = 1 B=1 ) triggers premature truncation that disrupts layout consistency and inflates cache misses"; "constitutes the empirical optimum by preventing memory inflation while securing reliable hardware-level cache reuse".
5. **Recovery tool is load-bearing**: CONFIRMED. Truncation keeps a 600-character head and 400-character tail preview and the agent can recall the full payload; disabling the recovery tool drops the score from 80.9 to 77.1 and raises cost to $4.03.
   - Anchor: "Completely disabling it triggers a capability drop from 80.9 to 77.1".

## 3. Reported results (as stated)

GPT-5.4-mini as agent backbone on OpenClaw, PinchBench (11 task categories) and Claw-Eval, isolated (context reset per task) and continuous (history persists) modes, price-model cost. Overall score / cost: PinchBench isolated Vanilla 80.5 / $8.31, TokenPilot 81.0 / $3.22; continuous 79.2 / $7.24 vs 81.3 / $2.79. Claw-Eval isolated 64.5 / $5.16 vs 63.1 / $2.27; continuous 63.4 / $81.52 vs 60.8 / $10.58. Cache-miss tokens (M) PinchBench continuous: Vanilla 5.943, TokenPilot 1.549. Baselines include LLMLingua-2, SelectiveContext, LCM, Pichay, Summary, MemoBrain, AgentSwing, Keep-Last-N, MemOS (all ported by the authors). Estimator cost under $0.03 across the continuous stream. Limitations stated: estimator misclassification, tuning of tau and B, dependence on provider prefix caching, same-category grouping in the continuous stream.

## 4. Performance-principles table (mechanism and cost model)

| Mechanism | MI210 (gfx90a) | Zen 5 EPYC |
|---|---|---|
| Byte-identical prompt prefix via placeholders and tool-block relocation | YES. Device-independent; llama-server's per-slot LCP prefix reuse is exact, so every volatile byte before the first stable block costs a full re-prefill from that offset. Prefill is ~788-919 tok/s on the 27B (kv-cache-program.md:540 @ d785b6d). | YES. Same, and each wasted token costs more (45-490 tok/s, long-context-program.md:288). The saving is larger per token on CPU than on GPU. |
| Batch-gated eviction every B turns | YES. Pure policy; the boundary-frozen `prune_pointer` arm already behaves this way. | YES. Pure policy. |
| Cost model K = alpha x hits + misses with alpha = 0.1 (price) | NO as written. Locally a hit is ~free in time and a miss costs C/r seconds; use miss tokens and measured rate, not dollars. | NO as written; same substitution. |
| Hash-addressed deduplication of repeated reads, preview plus recovery tool | YES. Our verbatim-log pointer (`peek()/grep()`) is the recovery tool. | YES. |
| LLM residual-utility estimator (Qwen3.5-35B-A3B) every B turns | PARTIAL. One more model call per batch; cost unmeasured here and the ablation shows it removes mostly hit tokens. | PARTIAL. A 35B call on a CPU quarter is the AgentDiet-style latency problem (see agentdiet dive). |
| Decode attention/KV traffic saved by shorter context | PARTIAL. Only full-attention layers of hybrids read KV; unmeasured. | PARTIAL. Same; decode is bandwidth-bound but the KV share is unmeasured. |

## 5. In-house state

- `_clear_stale_tool_outputs` (src/graph/helpers.py:558-620 @ orchestrator 1a10541b7, default off) clears all but the last two tool outputs on every turn: structurally the B = 1 hyperactive schedule this paper measures as the worst case. Whether the cleared block sits inside the cached prefix of our REPL prompt depends on where `## Last Output` is assembled (not traced).
- `context_arm_ab.py:143-163` `_prune_at_boundary` and `render` freeze pruning at the most recent boundary and leave later turns verbatim: the batched schedule (B large) by construction. Its stub keeps 1500 head and 1500 tail characters plus a `peek()` pointer for outputs over 4000 characters, close to TokenPilot's 600/400 preview.
- `src/backends/prompt_layout.py:47` (RTE-LOG-1) logs per-block kind, start offset and length with hashes: the data for a prefix-stability audit covers `system`, `tools`, `rules`, `task`, `state`, `context`, `skill`, `routing` and `tool_output` kinds, so volatile-field breaks outside tool outputs are observable.
- llama-server computes the exact common prefix per slot, and the hybrid checkpoint grid starts at the divergence point; a volatile byte early in the prompt therefore forces recompute from there.

## 6. Derived-actionables ledger

| # | Draft task line | Owner (lane) | Type | Stop / decision rule |
|---|---|---|---|---|
| TP-1 (refines intake-2833 C5) | Replay RTE-LOG-1 prompt-layout records across consecutive requests of the same session and report, per block kind, the share of requests whose first divergence offset falls before the first tool_output block, plus the miss-token (prompt_n) cost of those breaks in seconds at the measured device rate. | `context-and-token-economy.md` (tool-output-compression track) | code/doc-only on existing logs | Question: is the prefix broken by non-output content? Stop-on-answer after one pass; futility: <3% of requests diverge before the first tool_output (then no stabilisation work). |
| TP-2 (refines C5) | In the same replay compute, for `_clear_stale_tool_outputs` and for the boundary-frozen arm, the number of predecessor changes per session under counterfactual batch intervals B in {1, 3, 5}. | `context-and-token-economy.md` | code/doc-only | Question: what does per-turn clearing cost relative to batching? Stop when the table is filed. |
| TP-3 (refines C1) | Count identical repeated tool calls (hash dedup class) and recovery-pointer calls inside the C1 classifier replay, reported separately from supersession. | `context-and-token-economy.md` (C1 box) | code/doc-only | Stop with C1. |
| TP-4 | DECLINE adding TokenPilot's LLM residual-utility estimator as an arm now. Entry-specific reason: its own Table 3 shows the estimator layer reduces hit tokens (26.7M to 8.55M) but not miss tokens (1.589M to 1.549M), and a local server prices hits near zero, so the expected prefill saving is about 2.5% of misses. | n/a | n/a | Revisit if the decode-time KV-read share of hybrids is measured above 20% of step time (then shorter context has a non-prefill payoff). |

## 7. Dive-surfaced sources (grepped unbounded)

| Source | In index? | Would settle | Recommendation |
|---|---|---|---|
| github.com/zjunlp/LightRSI (or LightMem2) integration | 0 hits for the repo names | exact placeholder list and estimator prompts | decline: section A.4 of the page lists the passes and prompts; TP-1 measures our own logs, so no ledger row changes |
| MemoBrain, AgentSwing, LCM, MemOS (TokenPilot baselines) | MemoBrain 3, AgentSwing 14 hits; others not checked as entries | alternative baselines | decline: none changes C1/C2; AgentSwing's lookahead selection among three strategies is already in the index |

## 8. Contradiction / adversarial pass

- Baselines are the authors' own ports on a paid API; Pichay (ported) cuts cost 51% isolated on PinchBench but only 0.6% in continuous mode (7.20 vs 7.24), which does not reproduce Pichay's own 93% context claim (different quantity: context bytes in a live session).
- Price-model cost is not time: the 61-87% figures depend on a 10:1 hit/miss price ratio.
- The continuous stream groups same-category tasks; the authors state mixed streams give lower prefix reuse and their margin narrows (Table 7, mixed streams: residual-utility $5.25 vs recent-turn $5.79).
- Single-seed, no intervals; Claw-Eval scores fall 1.4-2.6 points.
- Restatement note: web summaries relay the 61/56/61/87 numbers; they are restatements, not corroboration.

## 9. read_depth

FULL for sections 1-6, appendices A.2-A.4 and the tables; related work and the reference list skimmed; figures not read. lane_head: d785b6d9792e18b29dad1929a15fdc2b971d3c0e. Orchestrator HEAD 1a10541b7466f2d5aef240ac547ff6dce2cd43cd.

## 10. Artifact audit

artifact audit: clean (12 quotes verified as substrings of page.txt, 11 carried in the draft; only dive.md and drafts/tokenpilot.json written).
