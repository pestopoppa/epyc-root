# ws58 2026-10-31 dive record: w1_agent

Markdown rendering of `w1_agent.yaml` (the original is kept beside it) so the wiki scanner sees this dive. Intake IDs are as the dive recorded them; read them as `#record` references. Digit runs of 12+ digits are written grouped.

```yaml
entries:
- id: intake-2565
  verification: dive-verified
  read_depth: FULL
  source_revision: 'claude.com article "Building agents: When to fold subagents into your main agent loop" (Diane Sarkis, dated October 22, 2026) HTML sha256-12 caf62ef7b78f, retrieved 2026-10-31'
  source_text_path: scratch:dive-ws58-20261031/dive/agent/fold.txt
  key_claims:
  - 'Anthropic Applied AI reports that across several enterprise deployments a single agent with skills frequently outperformed both the one-prompt design and the subagent design on quality, often at lower cost and latency per task (anecdotal; no table; one customer cited roughly 2x faster runtime for single loop vs multi-agent harness).'
  - 'Recommends building a small end-to-end eval first (10 golden examples is enough to start), folding subagents into skills plus MCP tools one at a time, comparing eval performance with and without the subagent, inspecting WHICH TASKS FLIPPED (not just the aggregate), running each task more than once, and keeping a subagent only if the folded version scores worse.'
  - 'Tool guidance: group tools by user intent, not one per API; tool choice tends to degrade beyond 30-50 tool definitions in the system prompt; use tool search with deferred loading; move hard preconditions into the tools. Subagents remain justified for (a) measurable context-bloat degradation, (b) parallel work needing fresh discardable windows, (c) tool-selection failure or conflicting system-prompt instructions.'
  reported_results:
  - 'one customer: roughly 2x faster runtime single agent loop vs multi-agent harness (anecdote, intro failure-modes section)'
  - 'Claude Code system prompt reduced by over 80% for more advanced models, including cuts from progressively disclosing skills and tools'
  - 'sample support agent: folding one subagent into another lowered latency but broke a previously passing process (failure appeared in 1 of 2 runs)'
  claim_verdicts:
  - {claim_index: 0, verdict: CONFIRMED, evidence: 'quote present; it is vendor-internal and qualitative, no numbers beyond the 2x anecdote'}
  - {claim_index: 1, verdict: PARTIAL, evidence: 'stage 1 omitted the task-flip inspection, repeat-runs rule and the keep-only-if-folded-scores-worse decision rule; routing-accuracy-while-orchestrator-exists is also stated'}
  - {claim_index: 2, verdict: CONFIRMED, evidence: '30-50 threshold and deferred loading both verbatim; no number is given for what deferred loading saves'}
  claim_anchors:
  - {claim_index: 0, locator: 'article, intro para 3', quote: 'a single agent with skills frequently outperformed both the one-prompt-for-everything design and the subagent design on quality, and often at a lower cost and latency per task.'}
  - {claim_index: 0, locator: 'article, Agent building failure modes / Latency', quote: 'saw a roughly 2x faster runtime with the latter.'}
  - {claim_index: 1, locator: 'article, Task-completion evals', quote: 'Even a set of 10 golden examples is enough to start.'}
  - {claim_index: 1, locator: 'article, Folding subagents ... via skills and tools', quote: 'Compare eval performance with and without the subagent.'}
  - {claim_index: 1, locator: 'article, Folding subagents ... via skills and tools', quote: 'run each task more than once, since a break like this one only showed up in one run out of two.'}
  - {claim_index: 2, locator: 'article, MCP tools', quote: 'once you exceed 30-50 tool definitions in the system prompt, tool choice tends to degrade.'}
  - {claim_index: 2, locator: 'article, MCP tools', quote: 'Use tool search with deferred loading, limit hard preconditions, and move any needed ones into the tools.'}
  - {claim_index: 1, locator: 'article, Subagents called as tools', quote: 'only recommend a full handoff, where the subagent takes over the conversation'}
  claim_corrections:
  - {claim_index: 1, effect: narrowed, note: 'Add: eval must cover every production chain of agents and every must-not-break rule; inspect flipped tasks; repeat runs. Keep-rule is "keep as subagent only if folded version scores worse".'}
  depends_on: []
  dive_corrections: 'No stage-1 claim was falsified. The article is single-vendor guidance with anecdotal numbers only (one 2x runtime figure, 80% Claude Code prompt cut); no independent head-to-head was found, so it is a design heuristic, not evidence. Dive added the three explicit subagent-justification conditions, the flipped-task and repeat-run eval rules, and the fact that it is written for cloud-frontier models whose thinking cannot be turned off (the "models are more capable" premise does not transfer unmeasured to our local Qwen3.x roles).'
  reader_should_conclude: 'Cite only as vendor design guidance: the 30-50 tool threshold, the three keep-a-subagent conditions, and the flipped-task fold eval procedure. Do NOT carry "single loop beats subagents" as a measured result for our stack; our delegate() roles are local CPU models with 4000-char truncated context and very different cost structure, so the premise must be re-measured on our own tasks.'
  not_read: 'Linked migration kit and /claude-api skills (not fetched); related-article cards.'

- id: intake-2559
  verification: dive-verified
  read_depth: FULL
  source_revision: 'arXiv:2510.03215v2 HTML sha256-12 3a7631811962, retrieved 2026-10-31 (v2 last revised 2 Mar 2026)'
  source_text_path: scratch:dive-ws58-20261031/dive/agent/c2c.txt
  key_claims:
  - 'C2C projects the Sharer KV-cache into the Receiver space and fuses it (Receiver cache kept via residual, per-layer learnable Gumbel-sigmoid gate, input-aware head weighting); both LLMs are frozen and only the fuser is trained. Layers are aligned terminal-first (last-to-last) and tokens aligned by decode/re-encode across tokenizers.'
  - 'Reported (A100, batch 1): accuracy +6.4-14.2% over individual models and +3.1-5.4% over text-to-text (T2T), average 2.5x latency speedup vs T2T. Table 4 (Receiver Qwen3-0.6B): MMLU-Redux 35.53 receiver-only, 41.03 T2T, 42.92 C2C with Qwen2.5-0.5B sharer (time 0.29s / 1.52s / 0.40s). C2C is SLOWER than receiver-alone (0.40 vs 0.29 s) but faster than T2T.'
  - 'Fusers are trained per Sharer-Receiver pair (500k OpenHermes samples, 1,929 steps for the main runs; less than 9 GPU hours for ~300 steps at the small scale). Limitations: a much weaker Sharer injects noise; O(N) multi-LLM scaling is only preliminary.'
  reported_results:
  - 'Abstract / s1: 6.4-14.2% higher avg accuracy than individual models; +3.1-5.4% over T2T; avg 2.5x speedup'
  - 'Sec 4.2 text: accuracy +11.00%, +9.64%, +11.88% over Receiver for the three sharers; +5.36%, +4.15%, +3.06% over T2T; speedups 3.46x, 1.51x, 14.41x over T2T'
  - 'Table 3 (Sharer Qwen2.5-0.5B, Receiver Qwen3-0.6B, MMLU-Redux): T2T sharer decodes 80 tokens = 1312 ms; C2C fusion 90 ms; sharer prefill 20 ms + 90 ms fusion'
  - 'Table 4, Qwen2.5-0.5B sharer: OpenBook 39.20 recv / 44.00 T2T / 52.60 C2C; ARC-C 41.04 / 49.48 / 54.52; C-Eval 32.04 / 35.88 / 41.77'
  - 'Table 4, Llama3.2-1B sharer: C2C 0.50 s vs T2T 0.75 s on MMLU-Redux (44.42 vs 43.32 acc); Qwen3-4B-Base sharer: T2T 7.54 s vs C2C 0.45 s'
  - 'Table 8 ablation: Project-only 20.70 avg, +Fuse 44.88, +Gate (C2C) 47.95'
  - 'Appendix A.5: agentic math flow GSM8K, C2C 62.55 vs multi-agent T2T +1.37; T-C2C 78.01 (partial; table read only via prose)'
  claim_verdicts:
  - {claim_index: 0, verdict: CONFIRMED, evidence: 's3.3 text'}
  - {claim_index: 1, verdict: PARTIAL, evidence: 'Stage 1 said "above each model alone and above T2T, lower latency than text handoff" - true, but all gains are on sub-4B Qwen/Llama receivers (0.6B), multiple-choice benchmarks, batch 1; abstract range 6.4-14.2% differs from the repo README range 8.5-10.5% (README is stale vs v2); C2C is slower than receiver alone'}
  - {claim_index: 2, verdict: CONFIRMED, evidence: 'training scheme A.3.5, limitation paragraph'}
  claim_anchors:
  - {claim_index: 1, locator: 'v2 abstract / s1', quote: 'It further outperforms the text communication paradigm by approximately 3.1-5.4%, while delivering an average 2.5× speedup in latency.'}
  - {claim_index: 1, locator: 'v2 s4.2 Efficiency, Table 3', quote: 'T2T requires the Sharer to decode 80 output tokens, incurring 1312ms of decoding overhead, whereas C2C replaces this sequential decoding with parallel cache fusion in 90ms.'}
  - {claim_index: 1, locator: 'v2 s4.1', quote: 'We use average inference time as the efficiency metric, measured using a single NVIDIA A100 GPU with batch size one.'}
  - {claim_index: 1, locator: 'v2 s4.2 Performance', quote: 'After applying C2C, accuracy increases by an average of 11.00%, 9.64%, and 11.88% across the three Sharers.'}
  - {claim_index: 0, locator: 'v2 s3.3.3', quote: 'the final layers of both models are aligned first, then the penultimate layers, and so on in reverse order until reaching the shallower model'}
  - {claim_index: 0, locator: 'v2 Fig 5 caption', quote: 'LLMs are frozen during training.'}
  - {claim_index: 2, locator: 'v2 Limitations', quote: 'Multi-LLM systems experience performance degradation when a much weaker Sharer provides noisy information to a stronger Receiver.'}
  - {claim_index: 2, locator: 'v2 A.3.5', quote: 'Training used 500,000 samples for one epoch with a macro batch size of 256, corresponding to 1,929 total training steps.'}
  - {claim_index: 2, locator: 'v2 A.4.x training cost', quote: 'With 300 training steps (less than 9 GPU hours), C2C achieves a comparable result to the final checkpoint.'}
  claim_corrections:
  - {claim_index: 1, effect: narrowed, note: 'Scope: Qwen3-0.6B receiver (largest scaling test is Qwen3 receivers with Qwen2.5-Instruct sharers in Fig 6), MC benchmarks, A100 bs1. Latency win is vs T2T only; C2C costs +0.11 s over receiver-alone on the 0.5B pair. Abstract and repo README ranges disagree (README stale).'}
  depends_on: []
  dive_corrections: 'Nothing falsified. Dive added: (1) C2C is a post-prefill KV rewrite - fused cache = receiver cache + gate*fuser(receiver_n, sharer_G(n)) - so it needs BOTH models prefilling the same tokens, and the saving is only the Sharer DECODE of the handoff text (80 tokens/1312 ms in Table 3); (2) assumes standard per-token K/V in every layer (Qwen/Llama dense); no hybrid-recurrent-state treatment; (3) accuracy tables are small-model MC QA (MMLU-Redux, OpenBook, ARC-C, C-Eval, LongBench), no agentic/coding/tool tasks except one GSM8K two-agent flow in the appendix.'
  reader_should_conclude: 'Cite C2C as a trained, per-pair, small-scale research result: +3-5 points over text handoff on MC QA at 0.6B receivers, and a latency win that is exactly the avoided sharer decode. Do NOT carry "2.5x faster" or "higher accuracy" to our 27B-35B roles, nor assume it works on hybrid/recurrent layers (Qwen3.8-Flash-Next, GDN models) without a layer-type design.'
  not_read: 'Appendix A.4.4 example outputs, Tables 5-7 and 9-14 individual cell values (read via prose), reference list.'

- id: intake-2576
  verification: dive-verified
  read_depth: PARTIAL
  source_revision: 'github.com/thu-nics/C2C @ 5eac72b (depth 1), retrieved 2026-10-31'
  source_text_path: scratch:dive-ws58-20261031/dive/agent/c2c_repo/README.md
  key_claims:
  - 'Released fusers cover small model pairs only; largest is Qwen3-8B receiver with Qwen2.5-7B-Instruct sharer (7 pairs total, all Qwen3 receivers 0.6B/1.7B/8B).'
  - 'Inference runs through HF transformers via a RosettaModel wrapper (rosetta/model/wrapper.py, 815 lines) with a kv_cache_index tensor; custom-pair training is supported (different dims, layers, heads, tokenizers).'
  - 'Apache-2.0; README says the paper was accepted at ICLR 2026. README also reports multi-sharer support as preliminary (2025/12) and a follow-up AKV "Cache Engineering for Agents" (2026/10).'
  reported_results:
  - 'README headline: 8.5-10.5% higher accuracy than individual models, 3.0-5.0% better than text communication, 2.0x latency speedup (differs from paper v2 abstract 6.4-14.2 / 3.1-5.4 / 2.5x - README is stale)'
  claim_verdicts:
  - {claim_index: 0, verdict: CONFIRMED, evidence: 'Supported Model Pairs table, 7 rows'}
  - {claim_index: 1, verdict: CONFIRMED, evidence: 'README How-to + rosetta/model/wrapper.py kv_cache_index'}
  - {claim_index: 2, verdict: CONFIRMED, evidence: 'LICENSE Apache; News 2026/01'}
  claim_anchors:
  - {claim_index: 0, locator: 'README.md Supported Model Pairs @ 5eac72b', quote: '| Qwen3-8B | Qwen2.5-7B-Instruct |'}
  - {claim_index: 1, locator: 'README.md Custom Model Pairs @ 5eac72b', quote: 'C2C supports arbitrary model pairs beyond those listed above.'}
  - {claim_index: 2, locator: 'README.md News @ 5eac72b', quote: 'Our paper is accepted by the ICLR'}
  - {claim_index: 0, locator: 'README.md intro @ 5eac72b', quote: 'with 2.0× speedup in latency.'}
  claim_corrections:
  - {claim_index: 0, effect: unaffected, note: 'Add: README headline numbers are older than paper v2; cite the paper, not the README.'}
  depends_on:
  - {entry: intake-2559, claim_index: 1, why: 'repo headline numbers duplicate the paper claims and are stale relative to v2'}
  dive_corrections: 'Confirmed. Added: README numbers disagree with paper v2; only HF transformers/CUDA path exists; there is no llama.cpp, GGUF, or recurrent-layer support. Repo is a research harness (rosetta package, 3.4k lines in model/) not a serving library.'
  reader_should_conclude: 'Use as the executable reference for the offline probe (released Qwen3-8B + Qwen2.5-7B-Instruct fuser at nics-efc/C2C_Fuser). Do not cite README accuracy/speed numbers.'
  not_read: 'Training scripts, recipe configs, AKV repo (only existence/licence checked via API).'

- id: intake-2562
  verification: dive-verified
  read_depth: PARTIAL
  source_revision: 'github.com/ekzhang/resin @ 37ae556 (depth 1), retrieved 2026-10-31'
  source_text_path: scratch:dive-ws58-20261031/dive/agent/resin_dive.txt   # concatenation of README, docs/architecture.md, cache-pool.md, numa.md, both SKILL.md, references/lessons.md
  key_claims:
  - 'Rust Engine owns request admission, batching, prefill chunking, one unified paged allocator and exact-token LRU prefix reuse; per-model Python runners get an immutable BatchPlan and own weights, kernels, CUDA graphs. (confirmed)'
  - 'Unified slab pool of equal-sized fungible slabs shared by full-history, sliding-window and recurrent-state groups; prefix snapshots restore attention, SWA and recurrent state at one LCM-aligned token boundary; MTP and DSpark speculative decoding supported in runners. (confirmed)'
  - 'Ships two agent skills (add-resin-model, optimize-resin-performance); self-described as not production quality; Apache-2.0. CORRECTION: README is NOT number-free - it claims DeepSeek-V4.1 and GLM-5.3 engines built in 12 hours "within 5-10% of DeepInfer" on Blackwell (charts external, no tables). All of it is CUDA/Blackwell GPU, no CPU engine.'
  reported_results:
  - 'README: standalone engines for DeepSeek-V4.1-Flash and GLM-5.3-Flash built in 12 hours that "rival vLLM and SGLang" (README wording); prefill and decode within 5-10% of DeepInfer (chart images external, not read)'
  - 'lessons.md case 9: V4.1 EP8 128K prefill 3.6910 s -> 1.9509 s via bounded consumer replay, explicitly labelled approximate (140-token consumer SWA tail; exact needed 2,560)'
  claim_verdicts:
  - {claim_index: 0, verdict: CONFIRMED, evidence: 'docs/architecture.md Rust Engine owns / Python runner owns lists'}
  - {claim_index: 1, verdict: CONFIRMED, evidence: 'cache-pool.md and architecture.md Prefix reuse, Speculative decoding sections'}
  - {claim_index: 2, verdict: PARTIAL, evidence: 'skills, WARNING, licence confirmed; "no numbers in text" (stage-1 note) is wrong - README gives a 12 hours and within 5-10% claim'}
  claim_anchors:
  - {claim_index: 0, locator: 'docs/architecture.md @ 37ae556', quote: 'The boundary is intentionally asymmetric: scheduling complexity belongs in the'}
  - {claim_index: 1, locator: 'docs/cache-pool.md @ 37ae556', quote: 'Slabs are fungible.'}
  - {claim_index: 1, locator: 'docs/architecture.md Prefix reuse @ 37ae556', quote: 'so a hit restores attention, sliding-window, and recurrent state at the same'}
  - {claim_index: 2, locator: 'README.md @ 37ae556', quote: 'This is not production-quality software.'}
  - {claim_index: 2, locator: 'README.md @ 37ae556', quote: 'within 5-10% of DeepInfer.'}
  - {claim_index: 2, locator: 'skills/optimize-resin-performance/SKILL.md @ 37ae556', quote: 'Keep observations, hypotheses and measured wins separate.'}
  - {claim_index: 2, locator: 'skills/optimize-resin-performance/SKILL.md @ 37ae556', quote: 'Repeat paired measurements when a claimed gain is close to run-to-run variation;'}
  - {claim_index: 2, locator: 'lessons.md case 9 @ 37ae556', quote: 'Inspect a reference'}
  claim_corrections:
  - {claim_index: 2, effect: narrowed, note: 'Numbers exist in README (12 hours, within 5-10% of DeepInfer on Blackwell, charts external). They are vendor-style comparison to another unreleased/obscure engine, not corroborated.'}
  depends_on: []
  dive_corrections: 'The technical filing is accurate. Dive corrected the "no numbers" note and established the real value: the two skills are a documented measurement discipline (paired A/B on one allocation, spread before calling a win, locate limiting interval via trace before touching kernels, matched-batch parity, approximate algorithms stay labelled, separate startup from warm). No part is usable as code for us: Rust+Python+CUDA/Blackwell, no CPU or ROCm path.'
  reader_should_conclude: 'Cite Resin as (a) a design reference for a unified pool with recurrent-state prefix snapshots at LCM-aligned boundaries (feeds KPF hybrid-prefix work), and (b) a source of AK-loop prompt text. Do not cite its performance claims.'
  not_read: 'docs/kernel-boundary.md, scheduler.md, cuda-graphs.md, distributed.md, metrics.md, models/ trees, lessons cases 1-8 and 10-13 (skimmed headings only), add-resin-model sections 3-6 (headings only).'

- id: intake-2553
  verification: dive-overturned
  read_depth: FULL
  source_revision: 'HF LiquidAI/d1-Omni-2B model card HTML sha256-12 6e403497c50c plus LiquidAI/d1-Omni-2B-GGUF card (lastModified 2026-10-28), retrieved 2026-10-31'
  source_text_path: scratch:dive-ws58-20261031/dive/agent/d1_dive.txt   # d1-Omni-2B card text followed by the GGUF card text
  key_claims:
  - 'd1-Omni-2B (2.17B, LFM3 backbone 24 layers: 13 gated short-conv, 5 SWA, 6 global attention; 128K context) returns typed calibrated answers in one forward pass with no generated tokens. (confirmed)'
  - 'Inputs: text/JSON state, images, video frames, audio clips and spoken questions, any number of named questions (default set_size 16). Question types noul, choice, score, text/number/date, number-with-range, box/boxes. (confirmed, more detail)'
  - 'CORRECTED: the card itself shows only Transformers (trust_remote_code), BUT a companion LiquidAI/d1-Omni-2B-GGUF repo exists (Q8_0 1.85 GB, BF16/F16 3.47 GB, mmproj files) with a llama.cpp path: "Supported in llama.cpp b11960 (v0.8.0) and newer", served through a /v1/systemone endpoint. GGUF path supports noul, choice and score only; multiple-choice, extraction, estimates and boxes are not supported yet. Our frozen production tree reports build 10303 and has no lfm3 arch and no systemone code.'
  - 'Card reports decision-suite scores and per-call latencies: 5.8 ms (H100) / 3.7 ms (MI325X) for one question, 12.4 / 8.2 ms with a 10-second clip, 52 / 43 ms for a 5K-token state, 21.1 ms one question on Apple M5 Pro (mps); no CPU-x86 row. License is LFM Open License v1.0 (not Apache/MIT).'
  reported_results:
  - 'Card Benchmarks (d1-Omni 2B / d1 2B / d1 3B): JevBench v1.4.1 75.3 / 77.9 / 76.2; DecisionBench (Hanno Labs) v1 76.4 / 77.1 / 73.1; Decision Bench v4 84.7 / 85.2 / 83.6; WorkflowEvals 77.1 / 81.6 / 74.4; Typed Decisions 63.1 / 61.3 / 65.0; Decision Index public suite v0.3 49.0 / 51.1 / 49.0'
  - 'Audio (effective accuracy, heard vs written): DecisionBench v1 routing and triage 78.2 vs 83.4; JevBench rows a voice can say 89.0 vs 87.6; SLURP intents 81.7 vs 87.4; Speech-MASSIVE 63.4 vs 85.2; spoken short states 22.8 vs 42.0; Belebele 41.8 vs 83.6'
  - 'Speed (warm after compile, bf16): H100 5.8 ms / 3 questions 7.7 ms / 1,154 states per s in a 64-state batch; MI325X 3.7 / 5.6 ms / 1,697 per s; M5 Pro 21.1 / 28.9 ms / 110 per s'
  claim_verdicts:
  - {claim_index: 0, verdict: CONFIRMED, evidence: 'card intro and model-details table'}
  - {claim_index: 1, verdict: CONFIRMED, evidence: 'Model details Input row; Question types table'}
  - {claim_index: 2, verdict: OVERTURNED, evidence: 'the card text names no llama.cpp path (true), but the HF model tree lists a GGUF quantization and its card documents llama.cpp b11960+ with /v1/systemone; the stage-1 implication that no llama.cpp path exists is false'}
  - {claim_index: 3, verdict: PARTIAL, evidence: 'latencies cover H100, MI325X and Apple M5 Pro; no CPU/x86 or MI210 row; JevBench v1.4.1 score is present (75.3)'}
  claim_anchors:
  - {claim_index: 0, locator: 'card intro', quote: 'It returns calibrated answers in one forward pass, without generating tokens.'}
  - {claim_index: 1, locator: 'card Inference / Question types', quote: 'Larger is faster and costs some accuracy on text.'}
  - {claim_index: 2, locator: 'GGUF card Use with llama.cpp', quote: 'Supported in llama.cpp b11960 (v0.8.0) and newer.'}
  - {claim_index: 2, locator: 'GGUF card Use with llama.cpp', quote: 'Multiple choice ("multiple": true), extraction, estimates and boxes are not supported yet.'}
  - {claim_index: 3, locator: 'card intro', quote: 'Millisecond decisions: 5.8 ms per decision on an NVIDIA H100 and 3.7 ms on an AMD MI325X, or 12.4 ms and 8.2 ms with a 10-second clip.'}
  - {claim_index: 3, locator: 'card Model details', quote: 'Without audio, use d1-2B: it is stronger on text and single boxes, reports missing values more often, and is better calibrated.'}
  - {claim_index: 3, locator: 'card Model details', quote: 'Long spoken passages lose much of their accuracy, most of all outside Latin-script languages.'}
  - {claim_index: 3, locator: 'card Model details', quote: 'LFM Open License v1.0'}
  claim_corrections:
  - {claim_index: 2, effect: overturned, note: 'A GGUF + llama.cpp (/v1/systemone) path exists upstream at b11960+; not in our v10 (10303) tree. It is a build cost (new arch + mmproj audio + endpoint), not a decline reason.'}
  - {claim_index: 3, effect: narrowed, note: 'All benchmark figures are vendor-reported; no CPU x86 or MI210 latency. d1-2B (no audio) is higher than d1-Omni on 7 of 9 listed decision rows, so for text routing d1-2B, not Omni, is the comparison model.'}
  depends_on: []
  dive_corrections: 'Overturned the "no GGUF/llama.cpp path" load-bearing claim: LiquidAI publishes d1-Omni-2B-GGUF and d1-2B-GGUF (HF API, updated 2026-10-28) with upstream llama.cpp support and a /v1/systemone endpoint covering noul/choice/score. Also: license is LFM Open License v1.0 (to be read before use), audio hurts on long/non-Latin speech, and the lineup includes text-only d1-2B and d1-3B that are not in the index and beat Omni on text. All scores are vendor-reported, none independently replicated here.'
  reader_should_conclude: 'Cite d1-Omni as a candidate local typed-decision backend with a real GGUF path, not as Transformers-only. Do not carry its benchmark scores as our expected accuracy; for the router/triage question compare d1-2B-GGUF (text) against the existing TD-23 incumbent, and for speech turn-taking measure d1-Omni on the CS-45 turn-taking corpus only after human-recorded strata exist.'
  not_read: 'Open d1 blog post and LFM3 blog (HTTP 200 for blog only; not read), LFM Open License text, d1-2B and d1-3B cards (existence/updated date via API only), .eval_results yaml.'

ledger:
- {row: AGENT-1, entries: [intake-2565], action: 'Run the fold article procedure as a zero-inference REPLAY over existing delegation records: for each delegate() role (worker_math, worker_general, worker_summarize, worker_vision, coder_escalation) compute from _delegations artifacts / delegation reports the share of traffic where role X is followed by role Y, plus tasks-flipped analysis between delegated and non-delegated (solo REPL) answers on the same eval items. Output: coupled-pair table and flip list.', grounding: 'src/repl_environment/routing.py:446-453 (_DELEGATABLE_ROLES = 6 roles incl. worker_math, worker_general, worker_summarize all served by the SAME Qwen3.6-35B-A3B-MTP-Q8_0 per orchestration/model_registry.yaml role rows); routing.py:578-587 (delegate prompt = 4000-char truncated context + brief)', owner: 'handoffs/active/routing-intelligence.md', posture: cheap-screen-now, benefit: 'finds roles that are subagent-in-name-only (three worker roles share one model and weights, so folding them is free); must keep per-role eval results unchanged', decision_rule: 'fold candidate only if flipped-task count is 0 on n>=2 repeats and held-out items; otherwise keep', reason: 'direct, zero-compute use of the article only concrete criterion that fits'}
- {row: AGENT-2, entries: [intake-2565], action: 'Count and cap the model-visible tool surface: REPL exposes ~55 globals (peek, grep, delegate, escalate, run_shell, registry_*, benchmark_*, ...) in environment.py _build_globals while tool_registry.yaml holds 55 further tools (TOOL/CALL/list_tools = already deferred). Record per-role advertised-tool counts in the prompt builder and compare against the 30-50 threshold; add a telemetry row. Evidence of existing failure: turn-1 grammar replay shows only 4/81 (4.9%) enforced and 26/685 (3.8%) non-enforced frontdoor REPL rows called any tool.', grounding: 'src/repl_environment/environment.py:414-560 (_build_globals), orchestration/tool_registry.yaml (55 tools, 8 categories), handoffs/active/agentic-serving-harness-fixes.md:670', owner: 'handoffs/active/agentic-serving-harness-fixes.md', posture: cheap-screen-now, benefit: 'tests whether tool-selection degradation (not capability) explains the 3.8-4.9% tool-call rate; direction: higher tool-use rate at equal or better pass', decision_rule: 'if advertised tool count per role > 50 AND a reduced-surface arm raises tool-call rate with pass not lower on a frozen 3-repeat set, promote the subset; else decline', reason: 'ties article threshold to measured symptom already in a handoff'}
- {row: AGENT-3, entries: [intake-2565], action: 'Add a per-fold eval: before folding any worker role into skills, require a frozen end-to-end set covering every production chain (architect -> coder_escalation, frontdoor -> worker_*) and every must-not-break rule, repeated >=2 times, reporting flipped tasks. Reuse tool-use-eval-contract sentinels + canonical judge suite as the set.', grounding: 'handoffs/active/tool-use-eval-contract.md (sentinels AUTOPILOT_TOOL_SENTINELS, get_eval_secret), routing-intelligence.md', owner: 'handoffs/active/tool-use-eval-contract.md', posture: monitor, benefit: 'prevents silent chain breaks when roles are merged', decision_rule: 'n/a (gate definition, not a probe)', reason: 'no fold is proposed yet; AGENT-1 decides whether any fold exists'}
- {row: AGENT-4, entries: [intake-2565], action: 'Do NOT adopt the article single-loop thesis for our CPU stack without measurement: the article premise is frontier models with thinking on; our workers are local quantised Qwen3.x on a BW-bound CPU where a separate small-context worker call is cheaper per token than extending one long context (every context token costs decode bandwidth).', grounding: 'handoffs/active/delegation-context-preassembly.md Strategic frame (BW-bound CPU makes context sharper)', owner: 'handoffs/active/delegation-context-preassembly.md', posture: knowledge-only, benefit: 'avoid importing a cloud-regime conclusion', decision_rule: 'n/a', reason: 'article gives no evidence on local-CPU cost structure'}
- {row: AGENT-5, entries: [intake-2559, intake-2576], action: 'Bounded offline probe on CPU (HF transformers, no llama.cpp): with released nics-efc/C2C_Fuser qwen3_8b+qwen2.5_7b fuser, run n=200 frozen items from a MC set the stack already scores (e.g. MMLU-Redux subset used in canonical suites) in 4 arms: Receiver-only, T2T (Sharer writes brief, 80-token cap), C2C, C2C with identity/zeroed gate (negative control). Six controls: (1) incumbent baseline arms above, same items; (2) paired-by-item design with McNemar; (3) A/A repeat of Receiver-only for the noise floor; (4) negative control = gate forced closed and a shuffled-sharer-cache (cache from a different item); (5) frozen item list and tokenizer/template pinned; (6) predeclared rule below. Record wall time per arm and sharer-prefill vs fusion time separately.', grounding: 'src/repl_environment/routing.py:578-593 (delegation is T2T with truncated context); intake-2576 README released pairs (largest Qwen3-8B/Qwen2.5-7B-Instruct)', owner: NEW:kv-cache-communication-probe, posture: cheap-screen-now, benefit: 'direction: accuracy up vs T2T at lower latency; must stay correct: negative controls must give no gain', decision_rule: 'promote to a pair-training scoping only if C2C beats T2T by >= 3 points paired (McNemar p<0.05) AND shuffled-cache control shows no gain AND latency <= T2T; stop if C2C <= receiver-only', reason: 'released weights make this a no-training screen; CPU for 7-8B bf16 prefill-only is tractable'}
- {row: AGENT-6, entries: [intake-2559, intake-2576], action: 'Design note (no compute): map C2C onto llama.cpp. Feasible path = out-of-process fuser. Receiver and Sharer each prefill the same prompt; read per-layer K/V from each via llama_state_seq_get_data (include/llama.h:881) or /slots/{id}?action=save (server-context.cpp:4849, needs --slot-save-path); apply fuser in torch on f16 cache; write back with llama_state_seq_set_data (llama.h:891) / action=restore; then decode. Constraints read: state is serialized per layer in cache dtype (kv_cache state_write, src/llama-kv-cache.cpp:2104+) so KV must be f16 not q8_0, V layout depends on v_trans/flash-attn, hybrid models write only attention-layer cache (recurrent state is separate), and cross-model rewrite needs token alignment between different tokenizers.', grounding: 'include/llama.h:876-895; tools/server/server-context.cpp:4832-4858; src/llama-kv-cache.cpp:2104', owner: NEW:kv-cache-communication-probe, posture: knowledge-only, benefit: 'sizes the build cost: new external tool + serialization parser, no src/ change', decision_rule: 'revisit only if AGENT-5 passes', reason: 'no change to frozen kernel; only worth building after the HF screen shows a gain'}
- {row: AGENT-7, entries: [intake-2559], action: 'Role-pair candidate list, ranked: (1) architect_critic / coder_escalation (Qwen3.8-27B Q8_0, dense KV-densest per model_registry.yaml:541) as SHARER -> worker_general/worker_summarize (Qwen3.6-35B-A3B MoE, receiver; must check whether its layers are all full attention - if hybrid, only attention layers fuse) because both share the Qwen family tokenizer so no alignment; (2) worker_general -> coder_escalation (reverse, weak-to-strong) is the paper noisy-sharer risk. Excluded: Qwen3.8-Flash-Next (SSM+attention hybrid, model_registry.yaml:2055) and worker_vision (VL tower). Pair-specific fuser training is the build cost (paper: 1,929 steps main runs; ~300 steps comparable) and has not been done at 27B-35B scale by anyone.', grounding: 'orchestration/model_registry.yaml role rows (coder_escalation, architect_critic, worker_general), model_registry.yaml:541,2055', owner: NEW:kv-cache-communication-probe, posture: monitor, benefit: 'only if AGENT-5 passes', decision_rule: 'trigger = AGENT-5 pass; no checkbox until then', reason: 'unfired broader-work trigger'}
- {row: AGENT-8, entries: [intake-2576], action: 'Read the thu-nics AKV repo (cache engineering for agents, follow-up to C2C, Apache-2.0, pushed 2026-10-21) before sizing any pair-training, since it may cover agent KV reuse without a per-pair trained fuser.', grounding: 'C2C README News 2026/10', owner: NEW:kv-cache-communication-probe, posture: cheap-screen-now, benefit: 'may be a cheaper route to KV reuse in agent loops', decision_rule: 'ingest-and-dive then decide', reason: 'surfaced source, not in index'}
- {row: AGENT-9, entries: [intake-2562], action: 'Copy the measurement-discipline text, not code, into the AK actor context: (a) record cache/graph/placement state and compare on the same allocation, (b) locate the limiting interval from a trace BEFORE kernel edits, (c) report the spread and do not call noise-sized differences wins, (d) approximate algorithms stay labelled, (e) separate startup from warm. Diff against program.md and the cross-workload keep gate to list only the lines NOT already present (Annex K e-process already covers paired A/B and floors).', grounding: 'handoffs/active/autokernel-research-loop.md:3583 (program.md is the control surface); autokernel-cross-workload-keep-gate.md:74 (paired A/B with floor)', owner: 'handoffs/active/autokernel-research-loop.md', posture: cheap-screen-now, benefit: 'only marginal: our rigor already exceeds the skill; expected gain is a handful of missing symptom-to-check rows (the "Observed symptom -> Check" table)', decision_rule: 'adopt a row only if absent from program.md and relevant to CPU/ROCm; else drop', reason: 'text diff, zero compute'}
- {row: AGENT-10, entries: [intake-2562], action: 'Use Resin docs/cache-pool.md + architecture.md Prefix reuse as design reference for hybrid prefix reuse: its snapshots are taken at an alignment equal to the LCM of all group block sizes and restore attention, SWA and recurrent state at the same boundary, with State snapshots in the same fungible pool. Compare with llama.cpp memory_recurrent::seq_cp which ignores p0/p1 and shares the tail cell.', grounding: 'handoffs/active/kv-prefix-fork-and-paged-attention.md:139 (seq_cp ignores p0/p1); :23 (KPF-11..19 hybrid prefix reuse ownership)', owner: 'handoffs/active/kv-prefix-fork-and-paged-attention.md', posture: knowledge-only, benefit: 'design input for the aligned-checkpoint approach to hybrid prefix reuse', decision_rule: 'n/a', reason: 'no code transfer; CUDA/Rust engine'}
- {row: AGENT-11, entries: [intake-2562], action: 'Decline engine/runner split as an adoption target: there is no CPU or ROCm runner, and production serving is llama.cpp (frozen v10). Treat the split as vocabulary only.', grounding: 'CLAUDE.md kernel freeze; Resin README CUDA/Blackwell only', owner: 'handoffs/active/speculative-decoding-mtp-refresh.md', posture: decline, benefit: 'n/a', decision_rule: 'n/a', reason: 'real technical constraint: no non-CUDA backend; a port is a rewrite, not a build cost justified by any measured gap'}
- {row: AGENT-12, entries: [intake-2553], action: 'Screen d1-Omni-2B-GGUF (Q8_0, 1.85 GB) and d1-2B-GGUF as local typed-decision backends on a separate, scratch-built upstream llama-server (b11960+ in its own build dir; production tree untouched). Probe: replay a frozen set of already-routed orchestrator tasks (route labels from routing-intelligence decisions) through /v1/systemone choice questions, 4 arms: d1-2B-GGUF, d1-Omni-2B-GGUF, the TD-23 incumbent readout, and the current learned MLP router; report accuracy, ECE (TD-18 receipt), per-call CPU latency at 1 and 16 questions. Six controls: incumbent arms on the same rows; paired per-row; A/A repeat for noise floor; permuted/opaque option keys and shuffled order as negative control (TD-16/Kev order-sensitivity); frozen rows and pinned GGUF sha; predeclared promote rule.', grounding: 'handoffs/active/typed-decision-plane.md:599 (TD-23 shared screen) and :467 (TD-20 serve Kev on llama.cpp-experimental, conditional); intake-1514 espetro fork', owner: 'handoffs/active/typed-decision-plane.md', posture: cheap-screen-now, benefit: 'one-pass heads replace generated JSON for triage; direction: lower latency with accuracy/ECE not worse than incumbent', decision_rule: 'promote to experimental-branch port only if d1 arm >= incumbent accuracy on held-out rows AND ECE <= incumbent AND p50 CPU latency at 16 questions <= incumbent; else stop', reason: 'GGUF exists, so the TD-20 conditional can be tested without writing a decision head'}
- {row: AGENT-13, entries: [intake-2553], action: 'Speech turn-taking decider test (only after human-recorded strata exist): d1-Omni-2B reads a short audio window and answers noul/score questions (end of turn? backchannel needed?) on the CS-45 corpus; compare against the CS-22 controller policy and the D1 bake-off cascade. Card limits to respect: spoken short states drop to 22.8 vs 42.0 written, long passages degrade, and no latency exists on x86 CPU or MI210.', grounding: 'handoffs/active/conversation-stack.md:92 (D1 bake-off not run), :85 (human_recorded stratum EMPTY, advance_eligible_strata)', owner: 'handoffs/active/conversation-stack.md', posture: monitor, benefit: 'a 2B one-pass decider may do endpointing in tens of ms; correctness must stay on the CS-45 gates', decision_rule: 'trigger = human_recorded stratum non-empty; then include as a CS-22 arm', reason: 'corpus gating already owned by conversation-stack'}
- {row: AGENT-14, entries: [intake-2553], action: 'Read LFM Open License v1.0 and the Open d1 blog before any use beyond a screen (licence is not Apache/MIT; sourcing policy is open-source only).', grounding: 'card License row; memory policy open-source only', owner: 'handoffs/active/typed-decision-plane.md', posture: cheap-screen-now, benefit: 'removes a licence blocker or confirms one', decision_rule: 'if redistribution/commercial use prohibited for our use, record as constraint for AGENT-12', reason: 'cheap and gating'}

dive_surfaced_sources:
- {source: 'https://github.com/thu-nics/AKV (Official implementation of paper "Cache Engineering for Agents"; Apache-2.0, pushed 2026-10-21; title checked via GitHub API description)', settles: 'whether agent KV reuse is possible without per-pair trained fusers', bears_on: intake-2559, recommend: ingest-and-dive}
- {source: 'https://huggingface.co/LiquidAI/d1-Omni-2B-GGUF', settles: 'the llama.cpp path and endpoint support matrix for d1 heads (noul/choice/score only)', bears_on: intake-2553, recommend: ingest-and-dive}
- {source: 'https://huggingface.co/LiquidAI/d1-2B-GGUF (and d1-3B-GGUF; text-only decision models, not in index)', settles: 'whether the text-only d1 is the right router comparator (card says it beats Omni on text and is better calibrated)', bears_on: intake-2553, recommend: ingest-and-dive}
- {source: 'https://www.liquid.ai/blog/open-d1 (HTTP 200; title not read)', settles: 'training and calibration method behind d1 heads, licence terms', bears_on: intake-2553, recommend: ingest-and-dive}
artifact_audit: clean
```
