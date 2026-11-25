# M2-recap-effort-topk: RECAP, effort-tier training, limits of Top-K (Stage-2 dive)

Entries: intake-2968 (RECAP, 2611.31258, s13), intake-2969 (effort training OPD vs RL, 2611.32131, s14), intake-2970 (limits of Top-K, 2611.32324, s15).
Lane head f19b902 (in-house line cites use `git show f19b902:path`). C21 tree @ 98ff8a4.
Read depth: s13 FULL (main text, ablations, appendix A-D). s14 PARTIAL (read: abstract, intro, S2-S3, S4 takeaways, S5 recipes, S6.1-6.2, A.3-A.5, B.1, B.2 Table 6; NOT read: S4.1-4.3 proofs in detail, S7 related work, Appendix B.3-B.6 per-benchmark tables, Appendix C proofs). s15 FULL for main text and appendices I-M (appendices A-H proofs/tables skimmed only via main-text pointers).

## Per-claim verdicts

### intake-2968 RECAP
| # | Claim | Verdict | Locator |
|---|---|---|---|
| 0 | Trains compaction with agent policy; full-context policy as self-teacher; reward = low distortion | CONFIRMED | S4.1 Eq 7-10 |
| 1 | Gradient splits into summary reward + on-policy self-distillation, no extra rollouts | CONFIRMED | S4.2 Eq 11-12; S4.3 |
| 2 | +4.6 BrowseComp-Plus, +4.3 SWE-bench Verified vs GRPO at 32K | CONFIRMED but NARROWED: 150 held-out BCP questions; RECAP 62.8 +-3.9 vs GRPO 58.2 +-1.5 (std is over 4 eval runs, not training seeds); one training run per method; SWE lambda picked on 100-problem val and the other lambdas give 46.3-49.8 (Table 3), so 51.1 is the best-of-4 on test-adjacent selection | Table 1, Table 3 |
| 3 | Both terms contribute | PARTIAL: g_sum alone is -1.5 on BCP (56.7 vs 58.2); g_post alone gives most of the gain (60.3 / 47.1); the combination is best | Table 2 |
| 4 | Fewer tool calls and tokens | CONFIRMED (BCP 19.9 vs 23.4 tools; SWE 145.6 vs 158.9) | Table 2, Fig 2 |

### intake-2969 Effort training
Operator summary check:
| Operator statement | Verdict | Locator |
|---|---|---|
| Length-penalized RL cuts AIME25 thinking 70% with no accuracy loss | PARTIAL: true for GLM-4.5-Air only (15.4k to 4.6k = -70%, acc 92.4 to 93.0). NOT true for Qwen3-8B, the Qwen-family case: -35% free (9.2k to 6.0k, 86.5 to 86.3), -53% costs 2.3 pts, -72% (2.6k) costs 9.8 pts (76.7). The entry's "Qwen3-8B AIME25 curves" are the worse-tolerance model | B.1 Tables 4-5 |
| Collapses tiers jointly | CONFIRMED: unscaled Mixed RL, all three tiers to ~330 tokens; rescaled variant keeps high but low truncates >65% | S3.2 |
| Multi-teacher OPD: low/medium use 58%/43% fewer thinking tokens than high | PARTIAL: not printed. Table 6 prints reductions vs the reference policy (medium -46.3%, low -60.8% at step 15; -45.0/-57.3 at step 20). 58/43 are arithmetic vs the high tier (3,771 and 5,160 vs 9,012 tokens). The printed 43%/61% in S3.4 is a different result (sparse-RL transfer to agentic tasks) | Table 6, S3.4 |
| High +3.1 over reference across 33 benchmarks | CONFIRMED: macro 71.0 vs 67.9 at step 15 (+2.8 at step 20), with 6.2% fewer tokens. Reference is itself a multi-teacher OPD checkpoint (A.4 note), so this is not a gain over an untouched base | S3.3, Table 6 |
| One token-level KL anchor on high separates tiers in one RL stage | CONFIRMED but SLOW: Recipe I needs ~80 steps flat, 123 steps to 97.7/70.7/49.6% of reference, and no separation on agent tasks. Only Recipe II (anchor + natural-language effort prompts) separates in 20-25 steps | S5.1, S5.2 |
Entry claims: 0 CONFIRMED; 1 CONFIRMED; 2 CONFIRMED (ratios 0.96-0.98, low 1.24 > medium 1.08 inverted); 3 PARTIAL (see prompt-only below).

**Prompt-only without RL: NOT-FOUND-IN-SOURCE.** Every effort result is a trained policy. There is no arm that gives the untrained base model the low/medium/high instruction text. Recipe II always trains with the prompts (GSPO 20/25 steps, batch 256) and is compared with the initialization evaluated only at high. So "natural-language effort descriptions separate tiers faster" means faster than discrete tags during RL, not that they work without RL. The three prompt texts are printed (S5.2), so a zero-training probe is cheap, but the paper supplies no prior for its result.

### intake-2970 Top-K limits
Operator summary check:
| Statement | Verdict | Locator |
|---|---|---|
| "Independent ranking unboundedly worse than joint support (133.2x in 4-position construction)" | CONFIRMED, with scope: hand-built toy (scalar values, binary downstream logits); ranking score is exact singleton-DELETION KL, not an attention or indexer score; Proposition 2 is for K=2 | S3.2-3.3 |
| exact-singleton Top-4 leaves >=10% improvement in 55/60, 49/60, 60/60 | CONFIRMED, with scope: relative KL headroom inside a 24-position pool, last-layer heads (2 heads x 30 prompts), 3 small models. Absolute scale is tiny: median dKL 1.9e-4 (Gemma) to 2.5e-3 (Qwen3.5-4B) | Table 2 |
| SwapCert catches 157/164 | CONFIRMED (52/55+48/49+57/60 = 157; 55+49+60 = 164), recall against the M=24 oracle only; 7 misses | S6.2 |
| Entry: "which of two positions is better flips for every K>=2" | CONFIRMED (Proposition 3, constructed); observed in 100%/100%/98.3% of oracle-positive cells | S3.4, S6.2 |
| Entry: attention-score supports beat recent and sink+recent at K=128/256 | CONFIRMED: Gemma K=128 KL 6.8e-4 vs 4.2e-2 recent vs 1.35e-2 sink+recent; all six model/budget cells | Table 3 |
Important counter-reading the entry misses: the exact-singleton ranker is NOT better than plain attention Top-K. In the paired SmolLM2 panel exact-singleton lowers joint KL in 38/120 cells, ties 34, raises 48. Attention Top-K also leaves >=10% headroom in 104/120 vs 108/120. So the paper does not show that a cheap scorer is the problem; it shows no marginal scorer is a joint optimum. Also: at K=4 the exact-singleton support flipped dense top-1 in only 4/180 cells, and 24-token greedy continuations were identical in 90/90 between attention and geometric Top-128.

## Adversarial pass
- WebSearch (3 queries total used across entries: 2 run). No independent replication or failed reproduction of any of the three found. Search surfaced a different "RECAP" (2610.22897, risk-controlled context adaptation) that is unrelated, so do not conflate. Related work surfaced: 2610.24991 (certified sparse attention), 2512.07647 (TV-distance theory of top-k sparse attention), 2608.06503, 2610.02163 (AutoCompact). All restatement/neighbors, not corroboration.
- RECAP: 4B model, one family, two tasks, thinking disabled, 150-question test; the 4.6 gain on BCP is about 1.2 sigma of the reported eval-run std. Distortion is never validated as a grader (no correlation of distortion with task success is reported).
- Effort: Baidu-internal models (ERNIE target) plus GLM-4.5-Air, DeepSeek-V4-Flash; curves "read from plotted training curves" for several numbers; the Qwen3-8B result is the least favourable.
- Top-K: single author, no systems evaluation (the paper says cache eviction and serving latency are a separate evaluation); BF16 batch-shape noise (max KL discrepancy 9.2e-5 in 4 Gemma cells) is the same order as the Gemma median dKL (1.9e-4).

## Key question answers

### Q1 RECAP: usable without training as a compaction grader?
Yes in principle, with changes. The score (Eq 8) is the per-token KL of next actions under summary-context vs full-context, summed over a continuation sampled under the summary. It needs: the same model scoring the same continuation tokens under two prefixes (summary context, full context). Implementation in the paper uses the sampled-token log-prob difference, not full-vocab KL (B.1). That is 1 prefill of the full history + continuation per candidate summary, plus the continuation rollout. llama-server can return prompt/token logprobs, so no training and no new kernel. Caveats: (1) the paper only uses it as a training signal; it never shows distortion predicts task success, so validating it against a behavioral outcome is the first step; (2) it grades behavior, not safety rules (a rule can be in the summary yet have no behavioral force, or vice versa; see CMP-3 failures); (3) needs the full context to fit once, at our context sizes a prefill of tens of K tokens on CPU (in-house: 94 s prefill for a real summary, context-and-token-economy.md:L65 @ f19b902).
In-house today: compaction is the multi-tier folding stack (`src/graph/compaction.py`, `session_summary.py`); grading is (a) identifier reference-miss detector `session_summary.py:355-366` + `CompactionQualityMonitor` `session_log.py:564-` (miss rate, give-up rate, REPL max-turns rate; context-and-token-economy.md TOC-CMP-1 L32, CF-3c L96 @ f19b902, live validation still open); (b) offline retrieval-proxy alpha sweep (CF-2c.0 L98: AP 0.940 vs 0.889); (c) LLM-judge semantic evaluator for the six-field brief, parked after three failed qualifications (L52); (d) behavioral A/B TOC-CMP-4 with blocked-actions-per-step (L76, open). The KL distortion score is a model-internal behavioral metric that none of these is; it would replace the failed judge lineage with a judge-free measure. Cheap form: take the paired boundary points TOC-CMP-4 already records, score summary arms with distortion on the same Qwen model. Note CMP-4's own prior: observation-dropping carries most of the effect and summarization adds ~3.6-4.4 pp (L157), so the grader should include a no-summary arm.

### Q2 Effort paper
Verified numbers above. Which need training: all. Prompt-only: not tested in the paper. In-house: stack-wide `enable_thinking=false` on all roles (harness-program.md:L1100-1101, I3 in routing-program.md:L686 @ f19b902); thinking budget plumbing exists but is default-off and unvalued (`thinking_budget_tokens`, context-and-token-economy.md:L1144, flag `repl_thinking_budget`); prompt-effort ladder E-1 designed (L3038) but E-2 curve unmeasured (L3041); `orchestration/reasoning_effort_certifications.yaml` has `role_certifications: {}`; no `reasoning_level` router action (routing-program.md:L337). Qwen3.8 template natively takes reasoning_effort in {low, medium, xhigh}; high renders identical to xhigh, none/minimal raise at thinking-on (harness-program.md:L1275-1278). So the implied zero-training probe is E-2 using the paper's three printed instruction texts as ladder rungs plus Qwen3.8's native low/medium/xhigh, on the pinned GPQA items, scoring by rescue rate. The paper adds two design facts for it: tiers can collapse toward high on agentic formats (rho ~0.96-0.98) even when trained, so measure ordering on agentic (REPL) tasks not only single-turn; and effort acts through number of turns on agent tasks. Nothing here implies local RL; the stack declined CPU training (L818).

### Q3 Top-K
(a) Exact vs approximate top-k: the paper says nothing about indexer top-k. Its selector is deletion-KL or attention score; ours is a learned lightning-indexer score on pooled blocks (`qwen4exp.cpp:L813-816` @ 98ff8a4: width = indexer_top_k + r - 1, whole blocks plus tail). The -EXACT box's bit-identity requirement (autokernel-akx-program.md:L1371-1375 @ f19b902) is an engineering gate (greedy identity as an oracle), not a quality claim, and in-house data support keeping it: GGML_CPU_TOPK_PAR failed greedy identity deterministically at P32K/P64K, and the exact variant closed on speed (P32K 0.0%). Set membership matters (softmax is permutation-invariant, so order matters only through tie-breaking at the boundary and fp summation). What the paper adds: boundary swaps change KL, but at the paper's scales the effect is small (K=128/256 rule differences 1e-5 to 1e-4 KL; 90/90 identical 24-token greedy outputs). That is a prior that an approximate top-k near the boundary is probably benign for quality, which would justify replacing greedy identity with a KL-vs-exact gate for any future approximate top-k. UNKNOWN-NEEDS-PROBE for our model: the indexer was trained with exact top-k, and K, depth (32K-64K) and hybrid GDN trunk differ from the paper.
(b) KV eviction gates: in-house gates are accuracy on 60 needle items (AM-PORT-2B: within 5 pts of FULL; EA 1/32 and L4@0.8 45/60 at keep 0.8, long-context-program.md:L916-918) and EA-POOL-SCREEN (L620-625) already asks the paper's question in coarse form (scorer resolution vs mechanics). Diagnosed failure there is scattered per-token eviction dropping single-digit needle tokens (L918), a contiguity/resolution problem, not a joint-renormalization interaction; the paper's headroom is relative-KL and tiny in absolute terms, so it does not explain our failures. Useful import: label-free dense-reference KL as a second metric beside accuracy (AM-PORT control.cpp already runs teacher-forced KLD controls, L926), and the KL-margin test (KL < m^2/2 certifies dense top-1) as a free per-step stability flag.
SwapCert cost: K(M-K) loss evaluations per (prompt, head) cell = 80 at M=24, K=4, each a one-head intervention plus downstream propagation (the paper says evaluation count and model-forward cost are distinct), versus 10,626 for the oracle. Over the 180 primary cells that is ~14,400 partial forwards. Cheap for a sampled diagnostic on a 4B model; NOT cheap as a gate for a 27B multi-layer mask (supports differ per head, layer, step; K of hundreds to thousands makes K(M-K) large). Also recall is only measured against the M=24 pool. Verdict: diagnostic on a small sample, not a gate.

## Principles table (kernel/systems)
| Principle | Source evidence | MI210 verdict | EPYC Zen 5 verdict | Why | Port cost |
|---|---|---|---|---|---|
| Joint support quality, not marginal rank, is the object of KV selection | S3, Table 2 | TRANSFERS-WITH-CHANGES (diagnostic only) | TRANSFERS-WITH-CHANGES | Math holds for any softmax set; but exact-singleton is no better than attention Top-K (38/120 vs 48/120), so no scorer swap is implied | audit harness only; no kernel |
| SwapCert one-swap audit as quality gate | S4, S6.2 | UNKNOWN-NEEDS-PROBE | UNKNOWN-NEEDS-PROBE | 80 partial forwards per head-cell; only validated at M=24, last-layer heads, 4B models | med: needs per-head intervention hook in llama.cpp |
| Exact top-k identity for indexer | not in paper | ALREADY-PRESENT (as gate) | ALREADY-PRESENT | Greedy-identity gate with -EXACT box; paper gives no reason to loosen | none |
| KL-vs-dense as label-free quality metric + m^2/2 top-1 certificate | S3.5, Table 5 | TRANSFERS | TRANSFERS | Needs teacher-forced dense reference; AM-PORT control.cpp already does KLD | low |
| Summary-vs-full-context next-action KL grader | RECAP Eq 8, B.1 | TRANSFERS (model-side only) | TRANSFERS-WITH-CHANGES | Needs 2 prefixes per summary; CPU prefill of full history is the cost | low-med: script over existing logprob API |

## Derived-actionables ledger
- KS-M2-1: Offline distortion-score grader for orchestrator compaction (summary vs full context, sampled-token KL), validated against TOC-CMP-4 blocked-actions and a no-summary arm. Owner context-and-token-economy.md (TOC-CMP-4 / CF-3c). Immediate (non-inference spec; run is queued compute).
- KS-M2-2: Add the paper's three effort instruction texts + Qwen3.8 native low/medium/xhigh as E-2 rungs; measure tier ordering on REPL/agentic tasks too. Owner context-and-token-economy.md E-2. Immediate.
- KS-M2-3: When any approximate top-k variant appears, gate it on teacher-forced KL-vs-exact (+ m^2/2 certificate) beside greedy identity. Owner autokernel-akx-program.md (Q38FN-INDEXER-TOPK-CPU). Monitor.
- KS-M2-4: Add dense-reference KL as second metric in EA-POOL-SCREEN / AM-PORT arms. Owner long-context-program.md EA-POOL-SCREEN. Immediate (the control exists).
- KS-M2-5: SwapCert as KV-eviction gate. Knowledge-only (cost and scope reasons above).

## Dive-surfaced sources
- arXiv 2610.24991 "Certified Sparse Attention via Perturbed Retrieval" (search result): bears on intake-2970; recommend ingest-and-dive (certified sparse attention is the constructive counterpart).
- arXiv 2512.07647 "A Mathematical Theory of Top-k Sparse Attention via Total Variation Distance" (search result): bears on intake-2970; recommend ingest-and-dive (positive guarantee under structure).
- arXiv 2610.02163 AutoCompact (search result): bears on intake-2968; decline (training-based, SFT on judge-corrected trajectories, nothing new for a no-training grader).
