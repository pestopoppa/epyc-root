# ws58 2026-10-31 dive record: w2_loop

Markdown rendering of `w2_loop.yaml` (the original is kept beside it) so the wiki scanner sees this dive. Intake IDs are as the dive recorded them; read them as `#record` references. Digit runs of 12+ digits are written grouped.

```yaml
entries:
- id: intake-2584
  verification: dive-verified
  read_depth: FULL
  source_revision: 'arXiv:2606.18023v1 HTML (sole version, 16 Jun 2026) + HF API Multilingual-Multimodal-NLP/LoopCoder-V2 sha b87cf3a, retrieved 2026-10-31'
  source_text_path: scratch:dive-ws58-20261031/dive/w2loop/lc_all.txt
  key_claims:
  - 'LoopCoder-v2 is a family of 7B Parallel Loop Transformer (PLT) coders (14 shared layers, hidden 5120, 40 heads / 8 KV groups, FFN 27648) trained from scratch on 18T tokens at loop counts R=1..4; PLT = cross-loop position offset (CLP) plus shared-KV gated sliding-window attention (G-SWA, w=64).'
  - 'Under matched SFT (6M examples) and evaluation, R=2 lifts SWE-bench Verified 43.0 -> 64.4 and the 10-benchmark average 38.0 -> 46.5; R=3 collapses to 27.6 (avg 36.9) and R=4 to 22.4 (avg 34.3). Non-monotonic in loop count.'
  - 'Latency/KV claim is architectural only: Table 1 gives sequential looping O(R*C_block) latency and O(RLSd) KV versus PLT ~C_block and O(LSd). No measured tokens/s, latency or memory number appears anywhere in the paper.'
  - 'A checkpoint is released (HF Multilingual-Multimodal-NLP/LoopCoder-V2, license apache-2.0, custom_code architecture IQuestPLTCoderForCausalLM, 362 downloads at retrieval). It is a transformers custom-code model, not a GGUF/llama.cpp architecture.'
  - 'The SWE-bench harness/scaffold is NOT named in the paper text; evaluation is stated only as each benchmark standard protocol and metric. All gains are single-run, single-seed, vendor-authored (IQuest Research / Beihang), no independent replication found.'
  reported_results:
  - 'Table 2 (Ours 7B rows; columns HE+/MultiPL-E/BCB/LCB/SWE/SWE-M/TB-v1/TB-v2/M2W/BFCL/Avg): R=1 81.1/69.5/40.1/27.4/43.0/14.0/26.3/11.2/35.3/32.2/38.0; R=2 84.1/73.9/46.1/35.4/64.4/31.0/34.2/21.0/34.5/40.1/46.5; R=3 75.0/69.8/43.3/28.6/27.6/11.0/30.0/12.2/35.1/36.3/36.9; R=4 76.8/67.3/40.8/24.5/22.4/9.3/26.3/9.0/41.4/39.5/34.3'
  - '§4.1: R=2 reaches 33.4% on agentic SWE-bench-CC. Training cost 1M GPU hours total (§3.1).'
  claim_verdicts:
  - {claim_index: 0, verdict: CONFIRMED, evidence: 'Abstract + §2.2 + Appendix B table'}
  - {claim_index: 1, verdict: CONFIRMED, evidence: 'Intro and Table 2 numbers match'}
  - {claim_index: 2, verdict: CONFIRMED, evidence: 'Table 1 is asymptotic; grep for tok/s, throughput, speedup finds nothing measured'}
  - {claim_index: 3, verdict: CONFIRMED, evidence: 'HF API json license:apache-2.0, custom_code tag'}
  - {claim_index: 4, verdict: CONFIRMED, evidence: 'no harness/scaffold named; eval protocol sentence is generic'}
  claim_anchors:
  - {claim_index: 0, locator: 'v1 Abstract', quote: 'Parallel loop Transformers (PLT) alleviate this cost through cross-loop position offsets (CLP) and shared-KV gated sliding-window attention'}
  - {claim_index: 1, locator: 'v1 §1', quote: 'including a gain on SWE-bench Verified from 43.0% to 64.4%'}
  - {claim_index: 2, locator: 'v1 §2.2', quote: 'yielding near-single-pass wall-clock latency'}
  - {claim_index: 3, locator: 'HF API model json', quote: 'license:apache-2.0'}
  - {claim_index: 4, locator: 'v1 §3.1 Evaluation Protocol', quote: 'We report the final supervised fine-tuning checkpoint for every model.'}
  claim_corrections:
  - {claim_index: 2, effect: narrowed, note: 'Index line ~112502 and any reading of the title as a speed result must not be cited as measured latency; it is a design property of PLT with no timing evidence.'}
  depends_on: []
  dive_corrections: 'Filed as a new entry (the index mention at ~112502 is prose only, no prior entry). Architecture is PLT (not plain sequential looping), checkpoint exists under Apache-2.0 but only as transformers custom code. The paper has no latency/throughput measurement and does not name the SWE-bench harness. Gain is real in-paper but single-seed and highly non-monotonic (R=3 below baseline), which undercuts the loop count as a free dial.'
  reader_should_conclude: 'Cite only as: a vendor 7B PLT coder reports 43.0 -> 64.4 SWE-bench Verified at R=2 with R=3/4 regressing, harness unnamed, no timings. Do NOT carry a speed or near-constant-latency claim as measured, and do not treat loop count as a runtime dial (each R is a separately trained model).'
  not_read: 'Per-loop interpretability figures (§3.2/§4.2 detail), related work, Table 6.'
- id: intake-2585
  verification: dive-verified
  read_depth: FULL
  source_revision: 'ggml-org/llama.cpp PR #29823 (open, head e79d8cab5 per comments, created 2026-10-01) body + issue comments; BrandeisPatrick/loop-transformer @ 599eed9 README/NOTES; retrieved 2026-10-31'
  source_text_path: scratch:dive-ws58-20261031/dive/w2loop/pr29823_all.txt
  key_claims:
  - 'PR #29823 (BrandeisPatrick, 324 additions, 9 files) adds a native ouro architecture to llama.cpp for ByteDance Ouro 1.4B/2.6B (+Thinking) and is NOT merged: state open at 2026-10-31.'
  - 'Loop mechanics: the whole decoder stack is applied 4 times per token with shared weights by reusing the Nanbeige4.2 machinery of #25994 (logical layers = physical x num_loops, one KV entry per loop and layer); adds sandwich norms; loop count is a LOAD-TIME constant set by --override-kv ouro.num_loops=int:N. There is NO per-token adaptive loop count and NO early exit: the early_exit_gate tensor is not converted.'
  - 'Correctness evidence is Apple M4 Metal: top-1 identical 829/829 vs HF at loops 1/2/4; GSM8K llama.cpp F16 26.0/67.0/80.5 at loops 1/2/4; PPL F16 104.4/16.43/9.53 at loops 1/2/4.'
  - 'Speed evidence: M4 llama-cli Ouro-1.4B F16 36.5 tok/s at 1 loop vs 9.5 tok/s at 4 loops (loop-transformer NOTES.md); third-party RTX 4080 Laptop CUDA Ouro-2.6B F16 64.2/33.5/22.8/17.4 tok/s at 1/2/3/4 loops. Decode scales ~1/R. No x86 CPU measurement exists anywhere in the sources.'
  - 'Looping only works at trained depth for some models: loop-transformer reports Nanbeige4.2 forced to 1 loop is degenerate (0.0 GSM8K, repetition) whereas Ouro (exit-gate trained at every step) degrades gracefully; and a lm-eval regex bug shrank the Ouro-vs-Qwen3-1.7B GSM8K margin from +12 to +1.5 under the verbatim rule.'
  reported_results:
  - 'PR body: logit parity table (829/829, max abs diff 0.21/0.11/0.34 at loops 1/2/4); GSM8K F16 26.0/67.0/80.5, transformers bf16 23.0/64.0/80.0; PPL Q8_0 9.54, Q4_K_M 9.84 at 4 loops; Ouro-2.6B Q8_0 90.0 on same GSM8K subset.'
  - 'Comment (Muuzzziiy): Ouro-1.4B tg128 F16/Q8_0/Q4_K_M 34.8/56.2/74.8 tok/s, Ouro-2.6B 17.9/28.1/39.5; loop scaling 2.6B F16 64.2/33.5/22.8/17.4; GSM8K 4-shot 79% F16, 77% Q4_K_M; -ngl counts logical layers (192) so -ngl 99 spilled to 1.6 tok/s.'
  claim_verdicts:
  - {claim_index: 0, verdict: CONFIRMED, evidence: 'GitHub API merged:false state:open'}
  - {claim_index: 1, verdict: CONFIRMED, evidence: 'PR body overview + diff reuse of #25994; early_exit_gate not converted'}
  - {claim_index: 2, verdict: CONFIRMED, evidence: 'PR body tables'}
  - {claim_index: 3, verdict: CONFIRMED, evidence: 'README/NOTES line and issue comment table'}
  - {claim_index: 4, verdict: CONFIRMED, evidence: 'loop-transformer README sections'}
  claim_anchors:
  - {claim_index: 1, locator: 'PR #29823 body Overview', quote: 'Ouro applies its whole decoder stack 4 times per token with shared weights'}
  - {claim_index: 1, locator: 'PR #29823 body Overview', quote: 'Loop count override: `--override-kv ouro.num_loops=int:N`.'}
  - {claim_index: 2, locator: 'PR #29823 body', quote: 'Checked against the HF reference on Ouro-1.4B (F16, Apple M4, Metal).'}
  - {claim_index: 3, locator: 'loop-transformer NOTES.md L1504-L1505', quote: 'llama-cli -m Ouro-1.4B-F16.gguf --override-kv ouro.num_loops=int:4   # 96 layers,  9.5 tok/s'}
  - {claim_index: 3, locator: 'PR #29823 body Also', quote: 'KV cache is one entry per loop and layer (96 logical layers for 1.4B), so decode is about 4x slower than a single pass'}
  - {claim_index: 4, locator: 'loop-transformer README', quote: 'Forcing Nanbeige below its trained two loops does not give a shallower'}
  claim_corrections:
  - {claim_index: 3, effect: narrowed, note: 'Stage-1 hope of a measured CPU speed is unmet: only Metal (M4) and CUDA numbers exist; the PR explicitly says decode is ~4x slower at 4 loops.'}
  depends_on: []
  dive_corrections: 'Not merged (open). Looping is static and load-time; no early exit and no per-token loop count despite Ouro being trained with a learned exit gate. KV is NOT shared across loops (one KV per loop x layer), so KV memory grows Rx. Both speed sources are non-EPYC. The sibling repo shows the headline Ouro advantage is fragile (scoring rule) and that post-training washes out looped advantage.'
  reader_should_conclude: 'Cite as: unmerged community port, correctness-validated on Metal, decode cost ~R x, KV cost R x, no CPU-x86 number. Do not claim llama.cpp supports Ouro or adaptive-depth inference.'
  not_read: 'Full 18.7 KB diff line by line (graph structure read through #25994 which it reuses); results/REPORT.md.'
- id: intake-2586
  verification: dive-verified
  read_depth: FULL
  source_revision: 'ggml-org/llama.cpp PR #25994 merged 2026-07-27T15:04:19Z (merge sha b77d646), diff + comments; frozen tree /mnt/raid0/llm/llama.cpp @ ffc1bac82; retrieved 2026-10-31'
  source_text_path: scratch:dive-ws58-20261031/dive/w2loop/pr25994_all.txt
  key_claims:
  - 'PR #25994 (zqlcode, 265 additions, 10 files) adds architecture nanbeige for Nanbeige4.2-3B (22 layers x num_loops=2) and was MERGED 2026-07-27 (created 2026-07-22).'
  - 'Graph implementation: load_arch_hparams expands logical layers to n_layer_phys x n_loops by copying per-layer head/ff arrays; load_arch_tensors creates only physical layer tensors and assigns layers[i + j*n_phys] = layers[i] (shared weights); each logical slot keeps its own KV index; num_loops is an optional GGUF key defaulting to 1; optional skip_loop_final_norm. Loop count is static per file.'
  - 'Review caught a signed-overflow bypass of the LLAMA_MAX_LAYERS guard (fixed by size_t bound) and noted num_loops should arguably be mandatory because silently falling back to 1 loop yields degraded output.'
  - 'Our frozen v10 tree (ffc1bac82, 2026-09-21) does NOT contain it: zero nanbeige matches in src/, gguf-py, convert_hf_to_gguf.py, no num_loops key in src/*.h, and #25994 merge sha b77d646 is not an ancestor of HEAD.'
  reported_results:
  - 'PR body reports no benchmark numbers (only a screenshot). Third-party (loop-transformer NOTES L1123): rewriting nanbeige.num_loops to 1 doubles decode speed (~40 tok/s on M4) but output degenerates.'
  claim_verdicts:
  - {claim_index: 0, verdict: CONFIRMED, evidence: 'GitHub API merged:true merged_at 2026-07-27T15:04:19Z'}
  - {claim_index: 1, verdict: CONFIRMED, evidence: 'diff src/models/nanbeige.cpp'}
  - {claim_index: 2, verdict: CONFIRMED, evidence: 'ggml-gh-bot automated review in comments'}
  - {claim_index: 3, verdict: CONFIRMED, evidence: 'git -C tree grep/log/merge-base executed this session'}
  claim_anchors:
  - {claim_index: 1, locator: 'PR #25994 body Runtime', quote: 'share physical weights across loops (separate KV slots)'}
  - {claim_index: 1, locator: 'PR #25994 diff src/models/nanbeige.cpp load_arch_tensors', quote: 'layers[i + j * n_phys] = layers[i];'}
  - {claim_index: 1, locator: 'PR #25994 diff nanbeige.cpp load_arch_hparams', quote: 'ml.get_key(LLM_KV_NUM_LOOPS, n_loops_u, false);'}
  - {claim_index: 0, locator: 'GitHub API pulls/25994', quote: 'merged_at 2026-07-27T15:04:19Z'}
  claim_corrections:
  - {claim_index: 3, effect: unaffected, note: 'Absence is structural in the frozen tree; the frozen tree is a fork carrying few upstream commits in the merge window (9 commits 07-20..07-30), so absence is expected, not a regression.'}
  depends_on: []
  dive_corrections: 'Confirms merge and mechanism. Looping is a pure graph unroll with weight sharing; each loop re-streams the full weight set (no weight-reuse scheduling), so decode weight bytes scale R x. Adds the quantified absence from v10.'
  reader_should_conclude: 'Cite: upstream has had a looped-arch path since 2026-07-27 (nanbeige, static num_loops=2), absent from v10; porting to an experimental branch is a cherry of ~265 lines, not a research problem. Do not cite quality or speed from the PR itself (none given).'
  not_read: 'conversion/nanbeige.py body beyond key names; ggml-gh-bot nits 4+ (tail of review).'
- id: intake-2587
  verification: dive-verified
  read_depth: FULL
  source_revision: 'divagr.com blog 2026-10-22 (update 2026-10-23) HTML sha n/a, + github.com/divagr18/qwenputer @ bec1a0c research/hidden-reasoning/README.md; retrieved 2026-10-31'
  source_text_path: scratch:dive-ws58-20261031/dive/w2loop/blog_all.txt
  key_claims:
  - 'Claim: under answer-only fine-tuning (LoRA plus unfrozen beta/decay projections, curriculum to 64 flips) on parity (light-switch flips), OLMo-Hybrid-7B (GDN beta up to 2) learns silent state tracking that generalises: 0.89 at 128 flips over 6 seeds (5 of 6 held, one never learned 64).'
  - 'Qwen3.5-4B (beta sigmoid-capped at 1) does NOT generalise: 0.55 at 128 flips (3 seeds; 2 of 3 learned 64, 0 of 2 held), i.e. coin flip, same as dense OLMo-3-7B 0.54 and as OLMo-Hybrid with beta capped at 1 (0.52, 6 seeds). So the headline is NOT Qwen3.5-4B parity; it is a failure case.'
  - 'Causal evidence for beta: capping OLMo-Hybrid beta at 1 (nothing else changed) drops it to chance; cap costs ~3.5% perplexity. Mechanism: bit lives in RNN state heads (L16 H2, L17 H4) but attention keeps a backup copy, so state-swap alone shows 0.00 effect while swap plus attention knockout shows 1.00.'
  - 'Scope limits stated by author: one task (parity), 3-6 seeds, artificial answer-only pressure not RL, a 3-cup shell game and 4-switch version at 64 flips were negative; Steifer 2026 shows a Qwen-style hybrid can still solve parity in one pass using attention, so possibility != what training finds.'
  reported_results:
  - 'README table: accuracy at 128 flips OLMo-Hybrid-7B 0.89 (0.53-1.00); capped 0.52 (0.49-0.56); Qwen3.5-4B 0.55; OLMo-3-7B 0.54. 5 of 6 vs 0 of 6 runs, one-sided Fisher p ~ 0.008.'
  - 'Planted compiled tracker inside Qwen3.5-4B ranked 1st of 864 heads by a blind detector (compiled beta=2 trackers track parity exactly over 100k tokens).'
  claim_verdicts:
  - {claim_index: 0, verdict: CONFIRMED, evidence: 'blog Result 1 + repo README table'}
  - {claim_index: 1, verdict: CONFIRMED, evidence: 'Qwen row 0.55; stage-1 framing of Qwen3.5 parity is the opposite of the finding'}
  - {claim_index: 2, verdict: CONFIRMED, evidence: 'Result 2 + mechanism section'}
  - {claim_index: 3, verdict: CONFIRMED, evidence: 'Limits section'}
  claim_anchors:
  - {claim_index: 0, locator: 'blog Result 1', quote: '0.89 at 128 flips, averaged over 6 seeds'}
  - {claim_index: 1, locator: 'blog Result 1', quote: 'Qwen 3.5 answered well till the training range and then essentially fell to a coin flip, scoring 0.55 at 128 flips'}
  - {claim_index: 2, locator: 'blog Result 2', quote: 'Capping β barely costs anything on normal text, perplexity goes up by about 3.5%.'}
  - {claim_index: 3, locator: 'blog Limits', quote: "It's 6 seeds per arm for the main OLMo-Hybrid comparison and 3 for the rest, and one task: parity."}
  claim_corrections:
  - {claim_index: 1, effect: reattributed, note: 'Any reading that Qwen3.5-4B reaches parity/hidden-tracking at 128 flips is wrong: it is the control that fails; hidden tracking is an OLMo-Hybrid (beta<=2) result.'}
  depends_on: []
  dive_corrections: 'Self-published single-author blog, not peer reviewed, no independent replication found. Direction for our stack is reassuring: Qwen-family GDN (sigmoid beta, confirmed in our tree at src/models/qwen3next.cpp:417) did not learn generalising silent tracking even under direct pressure.'
  reader_should_conclude: 'Cite as a single-task, small-seed result that beta<=1 GDN hybrids (Qwen3.5/3.8 family) failed to generalise hidden state tracking under artificial pressure; it is a CoT-monitorability research note with no performance lever for the serving stack. Do not cite as evidence that our hybrids can or cannot hide reasoning in general.'
  not_read: 'results/ raw jsonl, hcot code, the monitoring-tools follow-up post.'
new_entries:
- id: intake-2584
  arxiv_id: '2606.18023'
  url: https://arxiv.org/abs/2606.18023
  source_type: paper
  title: 'LoopCoder-v2: Only Loop Once for Efficient Test-Time Computation Scaling'
  categories: [local_inference, training_distillation, agent_architecture, inference_serving]
  novelty: medium
  relevance: medium
  discovered_via: expansion
  expanded_from: intake-2571
  verdict: worth_investigating
  ingested_date: '2026-10-31'
  authors: [Jian Yang, Shawn Guo, Wei Zhang, Mingjie Tang, Weifeng Lv, Ming Zhou, Bryan Dai]
  key_claims: ['7B PLT coder family (CLP offset + shared-KV G-SWA), loops 1-4, 18T tokens.', 'R=2 SWE-bench Verified 43.0->64.4; R=3 27.6; R=4 22.4.', 'Latency/KV constant in R is architectural only; no timings.', 'Apache-2.0 custom-code checkpoint on HF.', 'SWE harness not named; single-seed vendor result.']
  techniques: [parallel loop transformer, cross-loop parallelism offset, gated sliding-window attention with shared KV]
  reported_results: ['Table 2 Ours 7B avg 38.0 (R=1), 46.5 (R=2), 36.9 (R=3), 34.3 (R=4)']
  cross_references: {chapters: [], handoffs: [cpu-decode-roofline-program.md, gpu-acceleration-path.md], experiments: [], intake_entries: [intake-2571, intake-332]}
  recommended_actions: ['Monitor: llama.cpp PR for iquestpltcoder or independent replication; PLT decode equals batch-2 weight reuse, the one looped form that is roofline-favourable.']
  credibility_score: 2
  contradicting_evidence: ['R=3 and R=4 regress below the non-looped baseline in the same paper.']
  referenced_arxiv_ids: []
  notes: 'Dive-verified; see entries record.'
  verification: stage1-unverified
  handoffs_updated: []
  handoffs_created: []
  source_revision: 'arXiv:2606.18023v1'
  reader_should_conclude: 'Stage-1 unverified: do not cite.'
- id: intake-2585
  arxiv_id: null
  url: https://github.com/ggml-org/llama.cpp/pull/29823
  source_type: repo
  title: 'model : add support for Ouro (ByteDance looped LM) - llama.cpp PR #29823'
  categories: [local_inference, inference_serving]
  novelty: medium
  relevance: medium
  discovered_via: expansion
  expanded_from: intake-2547
  verdict: worth_investigating
  ingested_date: '2026-10-31'
  authors: [BrandeisPatrick]
  key_claims: ['Open, unmerged community Ouro port.', 'Static load-time loop count, KV per loop x layer, no early exit.', 'Parity validated on Metal only.', 'Decode ~1/R: 36.5 -> 9.5 tok/s (M4), 64.2 -> 17.4 (RTX 4080 laptop).', 'Loop advantages fragile under scoring and post-training.']
  techniques: [weight-shared layer unrolling, sandwich norms, --override-kv num_loops]
  reported_results: ['GSM8K F16 26.0/67.0/80.5 at loops 1/2/4', 'PPL 104.4/16.43/9.53']
  cross_references: {chapters: [], handoffs: [gpu-acceleration-path.md, cpu-decode-roofline-program.md], experiments: [], intake_entries: [intake-2547, intake-332, intake-2586]}
  recommended_actions: ['Bounded CPU loops=1/2/4 probe on an experimental branch (ledger W2LOOP-1).']
  credibility_score: null
  contradicting_evidence: null
  referenced_arxiv_ids: []
  notes: 'Companion repo BrandeisPatrick/loop-transformer (Apache-2.0) @ 599eed9.'
  verification: stage1-unverified
  handoffs_updated: []
  handoffs_created: []
  source_revision: 'PR #29823 open; loop-transformer @ 599eed9'
  reader_should_conclude: 'Stage-1 unverified: do not cite.'
- id: intake-2586
  arxiv_id: null
  url: https://github.com/ggml-org/llama.cpp/pull/25994
  source_type: repo
  title: '[Model] Add support for Nanbeige4.2 - llama.cpp PR #25994'
  categories: [local_inference, inference_serving]
  novelty: medium
  relevance: medium
  discovered_via: expansion
  expanded_from: intake-2547
  verdict: worth_investigating
  ingested_date: '2026-10-31'
  authors: [zqlcode]
  key_claims: ['Merged 2026-07-27.', 'Layer unroll with shared weights and separate KV; static num_loops.', 'Review fixed size_t overflow guard.', 'Absent from frozen v10.']
  techniques: [weight-shared layer unrolling]
  reported_results: []
  cross_references: {chapters: [], handoffs: [cpu-decode-roofline-program.md], experiments: [], intake_entries: [intake-2547, intake-2585]}
  recommended_actions: ['Use as base for experimental-branch looped probe (W2LOOP-1).']
  credibility_score: null
  contradicting_evidence: null
  referenced_arxiv_ids: []
  notes: 'Merge sha b77d646.'
  verification: stage1-unverified
  handoffs_updated: []
  handoffs_created: []
  source_revision: 'merged b77d646'
  reader_should_conclude: 'Stage-1 unverified: do not cite.'
- id: intake-2587
  arxiv_id: null
  url: https://divagr.com/blog/hybrid-models-can-hide-reasoning-in-their-rnn-state
  source_type: blog
  title: 'Hybrid models can hide reasoning in their RNN state'
  categories: [ssm_hybrid, benchmark_methodology]
  novelty: medium
  relevance: low
  discovered_via: expansion
  expanded_from: intake-2550
  verdict: new_opportunity
  ingested_date: '2026-10-31'
  authors: [Divyansh Agrawal]
  key_claims: ['OLMo-Hybrid (beta<=2) 0.89 at 128 flips.', 'Qwen3.5-4B (beta<=1) 0.55, fails.', 'Capping beta causes the loss; ~3.5% PPL.', 'Single task, few seeds, artificial pressure.']
  techniques: [GDN write strength beta, state-swap plus attention knockout, compiled weights]
  reported_results: ['Table: 0.89 / 0.52 / 0.55 / 0.54 at 128 flips']
  cross_references: {chapters: [], handoffs: [], experiments: [], intake_entries: [intake-2550]}
  recommended_actions: ['Knowledge only; one-line structural check of GDN beta in our tree (done: sigmoid at qwen3next.cpp:417).']
  credibility_score: 1
  contradicting_evidence: null
  referenced_arxiv_ids: []
  notes: 'Companion repo github.com/divagr18/qwenputer @ bec1a0c.'
  verification: stage1-unverified
  handoffs_updated: []
  handoffs_created: []
  source_revision: 'blog 2026-10-22; qwenputer @ bec1a0c'
  reader_should_conclude: 'Stage-1 unverified: do not cite.'
ledger:
- row: W2LOOP-1
  entries: [intake-2585, intake-2586]
  action: 'On an experimental llama.cpp branch freshly cut from production v10, cherry #25994 plus #29823 (about 590 added lines) and measure Ouro-1.4B Q8_0/Q4_K_M at --override-kv ouro.num_loops=int:1/2/4 on EPYC CPU (one quarter and full socket): tok/s, achieved GB/s vs the roofline Axis-B weight-stream figure, GSM8K 100-problem subset, and a non-looped Qwen3-1.7B at matched quant as comparator.'
  grounding: 'cpu-decode-roofline-program.md:146 (DRAM 460.8 GB/s, decode bandwidth-bound) and :533 Axis B weight stream; gpu-acceleration-path.md:248 "Not llama.cpp compatible" is now stale for Nanbeige (merged) and Ouro (open PR).'
  owner: handoffs/active/cpu-decode-roofline-program.md
  posture: cheap-screen-now
  benefit: 'Direction: quality per resident weight byte (RAM/capacity) up, tok/s per weight byte down; must stay correct on logit parity vs published M4 table and on loops=1 degeneracy (expected 104 PPL).'
  decision_rule: 'Six controls: (1) same build, only num_loops varies; (2) ABA alternation for host drift; (3) canonical OMP/NUMA recipe and verified live affinity; (4) matched quant and prompt, greedy; (5) logit top-1 parity vs HF reference on 20 prompts; (6) non-looped comparator at matched size and quant. Promote to a role-fit study only if loops=4 decode >= 0.35x of loops=1 on CPU (prediction from M4/CUDA is ~0.26x) or loops=2 holds >= 90% of loops=4 GSM8K; otherwise knowledge-only.'
  reason: 'Only way to turn the 4x M4 slowdown into an EPYC-specific number; port cost is small (merged code plus a 324-line PR).'
- row: W2LOOP-2
  entries: [intake-2584]
  action: 'Monitor triggers: (a) llama.cpp or vLLM PR adding iquestpltcoder / PLT, (b) an independent replication of LoopCoder-v2 R=2 SWE-bench Verified, (c) a timing number for PLT decode. Any one fires ingest-and-dive on it.'
  grounding: 'No timing in paper; PLT executes loop r of token i together with loop r-1 of token i-1 which equals a 2-token batch over the same weights, the only looped form that does not multiply weight bytes (cpu-decode-roofline-program.md:533 Axis B).'
  owner: handoffs/active/cpu-decode-roofline-program.md
  posture: monitor
  benefit: 'Direction: capability per weight byte with near-flat decode cost; must stay correct on SWE harness replication.'
  decision_rule: 'Do not build a PLT kernel (CLP shift, frozen first-loop KV plus width-64 SWA, per-head gate) until a trigger fires; then estimate as build cost.'
  reason: '7B Apache-2.0 checkpoint exists but is transformers custom code with no GGUF; single-seed, harness-unnamed vendor gain.'
- row: W2LOOP-3
  entries: [intake-2587]
  action: 'Knowledge-only: record that our GDN graph hard-caps beta at 1 (src/models/qwen3next.cpp:417 ggml_sigmoid) matching the Qwen3.5 control that failed to generalise hidden tracking; no probe.'
  grounding: '/mnt/raid0/llm/llama.cpp/src/models/qwen3next.cpp:417 (beta = ggml_sigmoid(b)); Qwen3.8-Flash-Next serves architect_general (model_registry.yaml:412).'
  owner: handoffs/active/cpu-decode-roofline-program.md
  posture: knowledge-only
  benefit: 'No performance lever; CoT-monitorability context for architect roles only.'
  decision_rule: 'Revisit if a replication on Qwen-family weights shows generalising silent tracking or a new hybrid with beta>1 enters the lineup.'
  reason: 'One task, few seeds, single-author blog; implication for served models is reassuring not actionable.'
- row: W2LOOP-4
  entries: [intake-2585, intake-2586]
  action: 'Correct the stale note in gpu-acceleration-path.md ~line 248 (intake-332 "Not llama.cpp compatible") to say nanbeige looped arch merged 2026-07-27 and Ouro is PR #29823 open; owning session applies.'
  grounding: 'gpu-acceleration-path.md:248.'
  owner: handoffs/active/gpu-acceleration-path.md
  posture: primitive-now
  benefit: 'Avoids a wrong premise in future planning.'
  decision_rule: 'n/a (text fix).'
  reason: 'Gap closed in place per Act, Do not Defer; subagent prepares, owning session applies.'
dive_surfaced_sources:
- {source: 'github.com/huskydoge/Awesome-Loop-Models', settles: 'Census of ~152 loop-model entries (found in loop-transformer NOTES)', bears_on: intake-2584, recommend: 'ingest-and-dive'}
- {source: 'arXiv:2604.21106 (iso-depth scaling law, phi=0.46 per loop; ID taken from loop-transformer NOTES, not title-checked)', settles: 'Marginal value of a loop vs a real layer', bears_on: intake-2585, recommend: 'ingest-and-dive'}
- {source: 'github.com/Thrillcrazyer/LoopUS (Qwen3-1.7B looped retrofit with exit threshold)', settles: 'Whether a Qwen3-based looped model with adaptive exit exists for our lineup', bears_on: intake-2585, recommend: 'ingest-and-dive'}
artifact_audit: clean
```
