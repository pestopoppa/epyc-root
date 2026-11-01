# ws58 2026-10-31 dive record: w2_spec

Markdown rendering of `w2_spec.yaml` (the original is kept beside it) so the wiki scanner sees this dive. Intake IDs are as the dive recorded them; read them as `#record` references. Digit runs of 12+ digits are written grouped.

```yaml
new_entries:
- id: intake-2577
  arxiv_id: null
  url: https://github.com/vllm-project/vllm/issues/55357
  source_type: repo
  title: 'vLLM #55357: Qwen3.8-Flash-Next (qwen4_exp) + MTP episodic 0% draft acceptance and repetition collapse in thinking block'
  categories: [speculative_decoding, inference_serving, ssm_hybrid]
  novelty: medium
  relevance: high
  discovered_via: expansion
  expanded_from: intake-2572
  verdict: adopt_patterns
  ingested_date: '2026-10-31'
  authors: [vLLM issue reporter (NVFP4 SM120 pod), tgmerritt, ZJY0516, jschmied]
  key_claims:
  - 'Reporter: vLLM nightly 73029d4 serving Qwen3.8-Flash-Next NVFP4 with MTP n=3 shows episodic windows of exactly 0 draft acceptance (~2,000 drafted, 0 accepted), generation pinned at 64-70 tok/s vs 95-135 healthy, and endless repetition inside the thinking block ending only at finish_reason=length; lifetime acceptance 20% (5.35M drafted / 1.09M accepted) over 2,923 ten-second windows.'
  - 'Reporter attribution (generic engine-level MTP/spec-decode state bug, supported by a Gemma 4 26B failure with the same signature) is NOT established: a commenter notes Gemma is not mamba, and the later root-cause comment says the Gemma observation is a different mechanism.'
  - 'Root cause found in-thread by jschmied (GB10 reproducer): with speculation configured the Mamba block table has 1+num_speculative_blocks columns, the prefill state slots are passed as a strided column view, the PLE short-conv Triton kernels load the slot with unit stride, so prefill rows r>=1 write conv state into request 0 speculative checkpoint blocks; trigger = two or more prompts prefilled in the same scheduler step. Acceptance collapse is downstream of corrupted target output, not a drafter fault. Fix is vLLM PR #55375 (API: closed, merged 2026-09-05T14:02Z); jschmied reports 0 of 20 corrupted cells after the fix vs 30-50% before.'
  - 'Architecture specificity: the fixed mechanism is specific to the vLLM qwen4_exp PLE short-conv kernels plus the vLLM Mamba block-table layout; it does not transfer by code to llama.cpp, but the failure class (per-request recurrent-state corruption visible only under batch-composition conditions with speculation configured) is the relevant risk for any hybrid-model spec-decode path.'
  techniques: [MTP speculative decoding, per-request acceptance telemetry, multi-prefill-step reproducer, strided state-index bug]
  reported_results:
  - 'Issue body Fingerprint table: lifetime draft acceptance 20% (5.35M drafted / 1.09M accepted); healthy 50-85% at 95-135 tok/s; collapse windows 0.000 per position at 64-70 tok/s; worst request 4h57m to the 1M window.'
  - 'jschmied comment 2026-09-05T11:08Z table: dev401 MTP n=3 cache on, batches with >=1 corrupted request 0/10, 3/10, 4/10, 4/10, 4/10, 5/10 for c=1/2/3/4/5/8; dev352 no speculation 0/46; cache off c=4 1/3.'
  - 'jschmied comment 13:00Z: fix takes corrupted-cell rate from 30-50% to 0 of 20 cells.'
  cross_references:
    chapters: []
    handoffs: [cpu-decode-roofline-program.md, qwen-mtp-llamacpp-port.md, speculative-decoding-mtp-refresh.md]
    experiments: []
    intake_entries: [intake-2572]
  recommended_actions:
  - 'Add a per-request acceptance-collapse plus repetition canary to the Flash-Next MTP serving gate (SPEC2-1).'
  - 'Add a simultaneous-multi-prefill equal-length concurrency probe, MTP on vs off, to G2-CONC (SPEC2-2).'
  credibility_score: 2
  contradicting_evidence:
  - 'Reporter generic-engine-bug attribution is contradicted by the thread: ZJY0516 (Gemma not mamba) and jschmied (Gemma is a different mechanism, no PLE layer).'
  referenced_arxiv_ids: []
  notes: 'Primary text = GitHub REST API issue JSON + comments JSON (5 comments), retrieved 2026-10-31. Issue state open at retrieval. Reporter hours-long single-pod episodes were not explicitly tied to the multi-prefill trigger by the reporter; jschmied explains episodic behaviour by the need for two prompts landing in one prefill-only step. Related issue numbers listed by the reporter (#47194, #52475, #53180, #52244, #54713, llama.cpp #28158/#28286) were NOT read.'
  verification: stage1-unverified
  handoffs_updated: []
  handoffs_created: []
  source_revision: 'vllm-project/vllm issue 55357 via GitHub API, issue.json sha256-12 0c7bd11c8a93, comments.json sha256-12 ed5a6ffd104e, retrieved 2026-10-31'
  reader_should_conclude: 'Stage-1 unverified: do not cite.'
- id: intake-2578
  arxiv_id: '2606.15007'
  url: https://arxiv.org/abs/2606.15007
  source_type: paper
  title: 'Nemotron 3 Ultra: Open, Efficient Mixture-of-Experts Hybrid Mamba-Transformer Model for Agentic Reasoning'
  categories: [speculative_decoding, training_distillation, ssm_hybrid, moe_optimization]
  novelty: medium
  relevance: medium
  discovered_via: expansion
  expanded_from: intake-2548
  verdict: adopt_patterns
  ingested_date: '2026-10-31'
  authors: [NVIDIA]
  key_claims:
  - 'Sec 3.4 MTP Boosting continues training the MTP head from the MOPD checkpoint with the backbone frozen for the whole phase; only the MTP head receives gradient updates.'
  - 'Train/inference mismatch fix: the hidden states fed to MTP step k are sampled from the set produced at MTP steps 1..k-1, instead of only the previous step outputs, to mimic the noisy mixed backbone/MTP hidden-state context at inference.'
  - 'Loss: temperature-scaled forward KL against the backbone logits (T=2, T^2 factor, N_mtp=7 steps), gold-token cross-entropy disabled; data = on-policy rollouts from the MOPD checkpoint at temp 1 over Nemotron-Post-Training-Dataset-v2 and Nemotron-RL-Super-Training-Blends prompts; 12K steps, global batch 64, sequences capped at 8K tokens.'
  - 'Result (SPEED-Bench qualitative split, draft length 7, Table 6): average acceptance length 4.387 -> 4.584 greedy and 4.165 -> 4.331 at temp 1; every listed category improves; authors state relative speculative-decoding speedup gains of 3.15% (summarization) to 5.82% (coding). No ablation separates the sampled-hidden-state change from the KL loss within Sec 3.4.'
  techniques: [MTP boosting, frozen-backbone head fine-tuning, forward-KL self-distillation, hidden-state sampling over MTP steps]
  reported_results:
  - 'Table 6 Average (greedy; temp1 in parens): Nemotron 3 Ultra 4.387 (4.165); +MTP-Boosting 4.584 (4.331); Qwen3.5-397B-A17B 4.580 (4.423); DeepSeek-V4-Flash 2.667 (2.500).'
  - 'Table 6 Coding 5.152 (4.739) -> 5.452 (4.872); Math 5.127 (4.661) -> 5.343 (4.733); Roleplay 2.801 (2.767) -> 2.940 (2.856).'
  - 'Table 6 caption: relative speedup improvements from 3.15% on summarization to 5.82% on coding (derived from acceptance length by the authors; no wall-clock setup given in the section).'
  cross_references:
    chapters: []
    handoffs: [dflash2-block-drafter-experimental-build.md, speculative-decoding-mtp-refresh.md, cpu-decode-roofline-program.md]
    experiments: []
    intake_entries: [intake-2548]
  recommended_actions:
  - 'Record the recipe as a training option under DF2-DRAFTER-CAPABILITY / any future Flash-Next head refresh (SPEC2-4); no probe until a trainable head exists.'
  credibility_score: 2
  contradicting_evidence: null
  referenced_arxiv_ids: []
  notes: 'Only Sec 3.4 settled (as scoped). Source = arxiv.org/html/2606.15007 (v1 only; submitted 12 Jun 2026). Abs-page title matched. Table 6 reached via HTML-to-text; the Average, Coding, Math, Roleplay rows read cleanly, other category rows present in nem.txt lines ~1136-1196. Hardware/serving setup for the SPEED-Bench AL measurement not stated in Sec 3.4 and not hunted elsewhere.'
  verification: stage1-unverified
  handoffs_updated: []
  handoffs_created: []
  source_revision: 'arXiv:2606.15007v1 HTML sha256-12 e351966ed0be, retrieved 2026-10-31'
  reader_should_conclude: 'Stage-1 unverified: do not cite.'
entries:
- id: intake-2577
  verification: dive-verified
  read_depth: FULL
  source_revision: 'vllm-project/vllm issue 55357 via GitHub API, issue.json sha256-12 0c7bd11c8a93, comments.json sha256-12 ed5a6ffd104e, retrieved 2026-10-31'
  source_text_path: scratch:dive-ws58-20261031/dive/w2spec/issue.txt
  key_claims:
  - 'Reporter: vLLM nightly 73029d4 serving Qwen3.8-Flash-Next NVFP4 with MTP n=3 shows episodic windows of exactly 0 draft acceptance (~2,000 drafted, 0 accepted), generation pinned at 64-70 tok/s vs 95-135 healthy, and endless repetition inside the thinking block ending only at finish_reason=length; lifetime acceptance 20% (5.35M drafted / 1.09M accepted) over 2,923 ten-second windows.'
  - 'Reporter attribution (generic engine-level MTP/spec-decode state bug, supported by a Gemma 4 26B failure with the same signature) is NOT established: a commenter notes Gemma is not mamba, and the later root-cause comment says the Gemma observation is a different mechanism.'
  - 'Root cause found in-thread by jschmied (GB10 reproducer): with speculation configured the Mamba block table has 1+num_speculative_blocks columns, the prefill state slots are passed as a strided column view, the PLE short-conv Triton kernels load the slot with unit stride, so prefill rows r>=1 write conv state into request 0 speculative checkpoint blocks; trigger = two or more prompts prefilled in the same scheduler step. Acceptance collapse is downstream of corrupted target output, not a drafter fault. Fix is vLLM PR #55375 (API: closed, merged 2026-09-05T14:02Z); jschmied reports 0 of 20 corrupted cells after the fix vs 30-50% before.'
  - 'Architecture specificity: the fixed mechanism is specific to the vLLM qwen4_exp PLE short-conv kernels plus the vLLM Mamba block-table layout; it does not transfer by code to llama.cpp, but the failure class (per-request recurrent-state corruption visible only under batch-composition conditions with speculation configured) is the relevant risk for any hybrid-model spec-decode path.'
  reported_results:
  - 'Issue body Fingerprint table: lifetime draft acceptance 20% (5.35M drafted / 1.09M accepted); healthy 50-85% at 95-135 tok/s; collapse windows 0.000 per position at 64-70 tok/s; worst request 4h57m to the 1M window.'
  - 'jschmied comment 2026-09-05T11:08Z table: dev401 MTP n=3 cache on, batches with >=1 corrupted request 0/10, 3/10, 4/10, 4/10, 4/10, 5/10 for c=1/2/3/4/5/8; dev352 no speculation 0/46; cache off c=4 1/3.'
  - 'jschmied comment 13:00Z: fix takes corrupted-cell rate from 30-50% to 0 of 20 cells.'
  claim_verdicts:
  - {claim_index: 0, verdict: CONFIRMED, evidence: 'issue body Summary and Fingerprint table; self-reported telemetry, single pod'}
  - {claim_index: 1, verdict: CONFIRMED, evidence: 'ZJY0516 comment and jschmied 13:00Z comment both reject the cross-model inference; claim is about the reporter attribution being unestablished'}
  - {claim_index: 2, verdict: PARTIAL, evidence: 'mechanism and fix come from a third-party commenter reproducing on GB10 with FP8-mixed checkpoint and temp-0 pairs; the thread does not show the original NVFP4 SM120 hours-long episodes ceasing after the fix. PR #55375 merged status from GitHub pulls API, diff not read.'}
  - {claim_index: 3, verdict: PARTIAL, evidence: 'specificity to qwen4_exp PLE conv confirmed in thread; llama.cpp non-applicability by code is my inference: llama.cpp does not contain the vLLM Triton kernel or block-table. llama.cpp issues #28158/#28286 cited only by the reporter and NOT read.'}
  claim_anchors:
  - {claim_index: 0, locator: 'issue body Summary', quote: 'generation pins to the 1-token/step spec-decode floor (~66 tok/s vs 95–135 tok/s healthy at 50–85% acceptance on the same pod)'}
  - {claim_index: 1, locator: 'comment ZJY0516 2026-09-05T01:51Z', quote: 'Gemma is not mamba, so the bug is not specific to mamba'}
  - {claim_index: 1, locator: 'comment jschmied 2026-09-05T13:00Z', quote: 'Your Gemma 4 observation would be a different mechanism (no PLE layer there)'}
  - {claim_index: 2, locator: 'comment jschmied 2026-09-05T11:08Z', quote: 'the corruption starts when two or more prompts are prefilled in the same scheduler step with MTP enabled.'}
  - {claim_index: 2, locator: 'comment jschmied 2026-09-05T13:00Z', quote: 'The PLE short-conv kernels load the slot with a unit stride'}
  - {claim_index: 2, locator: 'comment jschmied 2026-09-05T13:00Z', quote: 'Without speculation the view is contiguous (one column)'}
  - {claim_index: 3, locator: 'issue body Related upstream', quote: 'llama.cpp side, same model family: ggml-org/llama.cpp#28158 (MTP/DFlash emits OOB token id), #28286 (draft-MTP cross-slot contamination under --parallel>1)'}
  claim_corrections:
  - {claim_index: 1, effect: narrowed, note: 'Issue title/body headline implies a generic engine MTP bug; the thread root-causes the Qwen-family trigger to a qwen4_exp-specific kernel stride bug.'}
  - {claim_index: 3, effect: narrowed, note: 'Do not cite as a llama.cpp defect; cite only as a risk class that motivates a canary.'}
  depends_on: []
  dive_corrections: 'Stage-1 record created in the same pass. The issue headline reads as a generic MTP acceptance collapse and attributes it to engine-level draft-group state divergence; the in-thread comments overturn that framing: the Qwen-family cause is a strided state-slot index passed to PLE short-conv kernels under speculation configured, hit when two or more prompts prefill in one scheduler step, fixed by PR #55375 merged 2026-09-05. The repetition loop and 0% acceptance are downstream symptoms of corrupted target conv state, not a drafter-vs-thinking-text phenomenon, so the premise that acceptance collapses because in-thinking text is repetitive (a healthy drafter predicts loops trivially) is wrong direction: the collapse causes the loop. Architecture-specific (vLLM + qwen4_exp PLE conv), mechanism does not map onto llama.cpp code.'
  reader_should_conclude: 'Cite as: an episodic Flash-Next MTP acceptance collapse in vLLM was root-caused by a commenter to a strided Mamba state-index bug in the qwen4_exp PLE short-conv kernels, triggered by multi-prefill scheduler steps, fixed by merged PR #55375. Do NOT carry: the generic engine-bug framing, the Gemma cross-model inference, or any claim that llama.cpp MTP shares the defect. Use as justification for a per-request acceptance/repetition canary and a simultaneous-prefill concurrency probe.'
  not_read: 'PR #55375 diff, PRs #52244/#54713/#55467, issues #47194/#52475/#53180/#50837/#39273, llama.cpp #28158/#28286, reporter raw state dump (not provided), jschmied determinism-investigation notes.'
- id: intake-2578
  verification: dive-verified
  read_depth: PARTIAL
  source_revision: 'arXiv:2606.15007v1 HTML sha256-12 e351966ed0be, retrieved 2026-10-31'
  source_text_path: scratch:dive-ws58-20261031/dive/w2spec/nem.txt
  key_claims:
  - 'Sec 3.4 MTP Boosting continues training the MTP head from the MOPD checkpoint with the backbone frozen for the whole phase; only the MTP head receives gradient updates.'
  - 'Train/inference mismatch fix: the hidden states fed to MTP step k are sampled from the set produced at MTP steps 1..k-1, instead of only the previous step outputs, to mimic the noisy mixed backbone/MTP hidden-state context at inference.'
  - 'Loss: temperature-scaled forward KL against the backbone logits (T=2, T^2 factor, N_mtp=7 steps), gold-token cross-entropy disabled; data = on-policy rollouts from the MOPD checkpoint at temp 1 over Nemotron-Post-Training-Dataset-v2 and Nemotron-RL-Super-Training-Blends prompts; 12K steps, global batch 64, sequences capped at 8K tokens.'
  - 'Result (SPEED-Bench qualitative split, draft length 7, Table 6): average acceptance length 4.387 -> 4.584 greedy and 4.165 -> 4.331 at temp 1; every listed category improves; authors state relative speculative-decoding speedup gains of 3.15% (summarization) to 5.82% (coding). No ablation separates the sampled-hidden-state change from the KL loss within Sec 3.4.'
  reported_results:
  - 'Table 6 Average (greedy; temp1 in parens): Nemotron 3 Ultra 4.387 (4.165); +MTP-Boosting 4.584 (4.331); Qwen3.5-397B-A17B 4.580 (4.423); DeepSeek-V4-Flash 2.667 (2.500).'
  - 'Table 6 Coding 5.152 (4.739) -> 5.452 (4.872); Math 5.127 (4.661) -> 5.343 (4.733); Roleplay 2.801 (2.767) -> 2.940 (2.856).'
  - 'Table 6 caption: relative speedup improvements from 3.15% on summarization to 5.82% on coding (derived from acceptance length by the authors; no wall-clock setup given in the section).'
  claim_verdicts:
  - {claim_index: 0, verdict: CONFIRMED, evidence: 'Sec 3.4 Training Procedure'}
  - {claim_index: 1, verdict: CONFIRMED, evidence: 'Sec 3.4 Training Procedure, hidden states sampled from MTP steps 1..k-1'}
  - {claim_index: 2, verdict: CONFIRMED, evidence: 'Sec 3.4 Data and Loss'}
  - {claim_index: 3, verdict: CONFIRMED, evidence: 'Table 6 and caption; 4.584-4.387 = +0.197 AL (+4.5%) greedy; setup hardware not stated in section'}
  claim_anchors:
  - {claim_index: 0, locator: 'v1 Sec 3.4 Training Procedure', quote: 'The backbone is fixed for the entire training phase, and only the MTP head receives gradient updates.'}
  - {claim_index: 2, locator: 'v1 Sec 3.4 Loss', quote: 'We use a temperature-scaled forward-KL loss against the backbone’s logits.'}
  - {claim_index: 2, locator: 'v1 Sec 3.4 Data', quote: 'The MTP head was trained on these rollouts for 12K steps at a global batch size of 64, with sequences capped at 8K tokens.'}
  - {claim_index: 3, locator: 'v1 Table 6 caption', quote: 'yielding relative speculative-decoding speedup improvements from 3.15% on summarization tasks to 5.82% on coding tasks.'}
  claim_corrections: []
  depends_on: []
  dive_corrections: 'Stage-1 record created in the same pass; abs page title matched the expected Nemotron 3 Ultra paper. Section 3.4 verified as scoped. Note the speedup percentages are acceptance-length-derived relative figures (3.15-5.82%), much smaller than the headline impression of boosting; the AL gain is +0.2 on average at draft length 7.'
  reader_should_conclude: 'Cite Sec 3.4 as one vendor-reported recipe (frozen backbone, forward-KL T=2, sampled MTP hidden states, 12K steps bs64) giving +0.2 average acceptance length at draft length 7 on SPEED-Bench. Do NOT carry it as a wall-clock speedup, as a CPU/llama.cpp result, or as evidence the sampled-hidden-state trick vs the KL loss is responsible (no ablation).'
  not_read: 'Everything outside Sec 3.4 and Table 6 except scattered MTP mentions (RL rollout MTP k sweep, deployment sections); SPEED-Bench reference not read.'
ledger:
- {row: SPEC2-1, entries: [intake-2577], action: 'Add a per-request MTP health canary to the Flash-Next serving gate: flag any request with >=64 drafted tokens and zero accepted, or a repeated n-gram window in the generated tail (reuse coherence_gate tiers 0-2), and log per-request accepted/drafted from llama-server timings. Run on the existing G2-CONC corpus.', grounding: 'handoffs/active/cpu-decode-roofline-program.md:660-680 (PROD-1 recipe with draft-mtp n-max 4 and coherence_gate constants; no per-request acceptance floor named); speculative-decoding-mtp-refresh.md:223 (MTP parallelism must be verified per runtime)', owner: handoffs/active/cpu-decode-roofline-program.md, posture: cheap-screen-now, benefit: 'catches silent runaway/zero-acceptance requests that aggregate acceptance hides (issue lifetime 20% looked like a tuning problem); correctness unchanged', decision_rule: 'promote to recipe constant if the canary runs clean on the canonical recipe at -np 1 and np the recipe is validated at; any request tripping it blocks the recipe until explained', reason: 'issue shows aggregate acceptance masked an hours-long per-request failure'}
- {row: SPEC2-2, entries: [intake-2577], action: 'Extend G2-CONC with a simultaneous-multi-prefill probe: c in {2,3,5} identical-length prompts differing by a salt, issued at the same instant, temp 0, ignore-eos 128 tokens, MTP on vs MTP off, compare every request token-for-token to its solo -np 1 output; also record per-request acceptance.', grounding: 'handoffs/active/cpu-decode-roofline-program.md:672-680 (G2-CONC nrc_y>=32 concurrency gate must be run on the named binary); issue.txt jschmied 11:08Z table (0/46 corrupted with no speculation vs 30-50% with MTP n=3 at c>=2)', owner: handoffs/active/cpu-decode-roofline-program.md, posture: cheap-screen-now, benefit: 'reveals batch-composition-dependent state corruption in the llama.cpp recurrent/GDN slots under MTP (the vLLM bug class); correctness work needs no quiet host', decision_rule: 'any MTP-on request diverging from the solo reference while MTP-off matches = stop-ship for that recipe; 0 divergences over >=10 batches per c = pass for that binary', reason: 'the vLLM trigger was invisible to sequential probes'}
- {row: SPEC2-3, entries: [intake-2577], action: 'Note thinking-mode default sampling repetition risk: issue says model card recommends presence_penalty 0-2 and attributes loops to degenerate state amplified by temp 1.0 / top_k 20 / top_p 0.95; check the Flash-Next architect_general request sampler against the card and add the repetition detector from SPEC2-1 to thinking-on traffic only.', grounding: 'handoffs/active/cpu-decode-roofline-program.md:660-680 (recipe fixes spec flags but names no sampler repetition guard)', owner: handoffs/active/cpu-decode-roofline-program.md, posture: monitor, benefit: 'bounded cost of runaway thinking; do not change sampling without quality gate', decision_rule: 'act only if SPEC2-1 trips on a real request', reason: 'amplifier, not cause, per the thread'}
- {row: SPEC2-4, entries: [intake-2578], action: 'Add to DF2-DRAFTER-CAPABILITY the Nemotron Sec 3.4 head/drafter fine-tune recipe as an option: freeze target, sample hidden states from earlier draft steps, forward-KL T=2 to target logits on target on-policy rollouts at temp 1 (reference scale: 12K steps, bs 64, 8K seq).', grounding: 'handoffs/active/dflash2-block-drafter-experimental-build.md:196 (DF2-DRAFTER-CAPABILITY pipeline row); speculative-decoding-mtp-refresh.md cross-cutting note that draft-head is a small BW slice and expert-verification overhead is the CPU wall', owner: handoffs/active/dflash2-block-drafter-experimental-build.md, posture: knowledge-only, benefit: 'gain reported is +0.2 AL at draft length 7 (about 4.5% greedy), and our fleet runs n-max 3-4 where the deep-position gain is smaller; revisit only if a trainable Flash-Next MTP head becomes a lever', decision_rule: 'promote to a probe only if measured per-position acceptance at n-max 4 on Flash-Next shows a deep-position drop worth more than a few percent end to end', reason: 'small expected gain at our draft depth, vendor-reported, no ablation'}
- {row: SPEC2-5, entries: [intake-1724], action: 'Answer only (no entry): the z-lab card text does not say how the DFlash2 selector (top-16, rank-256 transition score) was trained, and reports no tau gain over DFlash 1 for Qwen3.8-27B. The inco.ai blog (sha256-12 99dc56f49911) gives the selector score S_t(a,b)=U_t(b)+<A(a) o H(h_t),B(b)>, with U_t the DFlash logit, A/B 256-d token embeddings, H a context gate; no training objective stated beyond that DFlash and DSpark drafters were trained by the authors under matched setups. Reported gains are on Qwen3-4B GSM8K five-layer: selector alone (no conv) 4.27 -> 4.61 at T=0 and 3.78 -> 4.25 at T=1 (+0.34/+0.47), vs DSpark correction 4.49/4.08, with +2.0M params and +0.6% latency; oracle top-16 reaches 6.79. Full DFlash 2 vs DFlash on Qwen3.5-4B: mean 4.92 -> 5.97 (+1.05, 21%). On Qwen3.8-27B the only comparison is vs MTP and a community DSpark: mean 4.28 / 3.62 / 4.80 (card H200 table: MTP 3.74-5.02, DFlash2 4.10-5.46); there is NO DFlash-1 row for the 27B target.', grounding: 'dive/w2spec/blog.txt lines 150-200 and 309-360, dive/w2spec/dflash2_readme.md; handoffs/active/dflash2-block-drafter-experimental-build.md:196 DF2-DRAFTER-CAPABILITY needs the selector training recipe, which is unpublished in both sources; code at github.com/z-lab/dflash NOT read', owner: handoffs/active/dflash2-block-drafter-experimental-build.md, posture: knowledge-only, benefit: 'prevents citing a 27B tau gain over DFlash-1 that does not exist; selector training recipe must be recovered from code or a paper before DF2-DRAFTER-CAPABILITY can claim a training pipeline', decision_rule: 'next step is a read-only look at github.com/z-lab/dflash (and incoai GitHub) for the selector training loss; if absent the row stays knowledge-only', reason: 'asked question; sources do not contain the requested training detail'}
dive_surfaced_sources:
- {source: 'https://github.com/vllm-project/vllm/pull/55375', settles: 'exact fix (stride argument to PLE conv kernels) and merge status; which other short-conv consumers assume unit stride', bears_on: intake-2577, recommend: 'ingest-and-dive'}
- {source: 'https://github.com/ggml-org/llama.cpp/issues/28286', settles: 'draft-MTP cross-slot contamination under --parallel>1 in llama.cpp, directly relevant to np>1 MTP serving on the frozen v10 tree', bears_on: intake-2577, recommend: 'ingest-and-dive'}
- {source: 'https://github.com/jschmied/qwen38-flash-next-gb10 (notes/determinism-investigation.md)', settles: 'per-cell data and method for the multi-prefill reproducer', bears_on: intake-2577, recommend: 'ingest-and-dive'}
- {source: 'https://github.com/z-lab/dflash', settles: 'DFlash2 selector training objective and recipe for DF2-DRAFTER-CAPABILITY', bears_on: intake-1724, recommend: 'ingest-and-dive'}
artifact_audit: clean
```
