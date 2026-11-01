# ws58 2026-10-31 dive record: w3_dec

Markdown rendering of `w3_dec.yaml` (the original is kept beside it) so the wiki scanner sees this dive. Intake IDs are as the dive recorded them; read them as `#record` references. Digit runs of 12+ digits are written grouped.

```yaml
entries:
- id: intake-2593
  verification: dive-verified
  read_depth: FULL
  source_revision: github.com/ggml-org/llama.cpp PR 29818 (merge a4cb4c61fd9d, 2026-10-02) via GitHub API incl. 6 comments, 6 review comments, tools/server/README.md and server-decision.cpp @a4cb4c6, retrieved 2026-10-31; frozen tree ffc1bac82 checked by git
  source_text_path: scratch:dive-ws58-20261031/dive/w3dec/src_2593.txt
  key_claims: &id001
  - 'PR 29818 (ggml-org/llama.cpp, merged 2026-10-02T09:56:05Z, merge commit a4cb4c61fd9d, 35 files, +2139/-15) adds POST /v1/systemone, a TypeSafe-API-compatible endpoint, plus conversion, libllama decision-head and server_decision_context support for 5 decision models: laya, julia-1, lev, openjev (+vision) and kev. It is a thin wrapper over existing embedding-model (BERT/ModernBERT/Qwen) infrastructure: the server switches input/output handling on the {arch}.decision.type GGUF key.'
  - 'API: request = state (string/object/array), optional images (data URLs), questions{id: {type, instructions, criteria}}; type is exactly choice | score | noul (no multi-select, extraction, estimates or boxes). Response per question: choice -> choice + probabilities (sum 1) + confidence 0..1; score -> expected level index + legend + probabilities + confidence; noul -> a single probability of true. usage.output_tokens is always 0; streaming unsupported; 400 invalid request, 501 non-decision model or missing mmproj. Option limits are per model (52 openjev, 255 laya). Questions of one request are answered independently (each is its own task, so they can land on different slots).'
  - 'Calibration/temperature: probabilities are softmaxes of the head outputs scaled by temperatures stored in the model file (GGUF keys decision.temperature.*, per question kind and, for some, bucketed by number of options; the server refuses temperature <= 0). The README states they are not guaranteed calibrated for the user''s data. The server exposes no request-time temperature override in the merged README.'
  - 'Parity evidence in the PR (reference -> llama.cpp, one synthetic customer-ticket request, 5 questions): worst |dp| of any probability is laya 8.4e-4, julia-1 2.2e-2, lev 5.2e-3, openjev 1.8e-4, kev-4b 1.3e-3. The reference is each model''s own Python implementation; this is one request, not a distribution.'
  - 'Model families supported at merge are decision heads on BERT/ModernBERT-style encoders (laya, julia-1, lev), a Qwen3-VL-based vision model (openjev) and Qwen3.5-based Kev; Clef (Cloudflare) was explicitly deferred to a follow-up and later models (d1 LFM3, vllm-d3, Granite-switch, H2O-Lightning, MiniCPM-OCR-Jev, pplx-decider) arrived in separate PRs. Build-number mapping: a user on build 11200 got 404 and was told the endpoint landed in b11361.'
  - 'Frozen production tree /mnt/raid0/llm/llama.cpp (HEAD ffc1bac82, committer date 2026-09-21) does NOT contain the endpoint: PR merge commit a4cb4c61 is not an ancestor of ffc1bac82, git grep -i systemone finds nothing, and tools/server has no *decision* file. Using any d1/Kev-class model through /v1/systemone therefore needs an experimental-branch port or a scratch upstream build (>= b11361 for the endpoint, >= b11960 for LFM3/d1-2B per intake-2582).'
  reported_results:
  - 'PR: merged 2026-10-02T09:56:05Z, 35 files, +2139/-15, merge commit a4cb4c61fd9d9c2066c7c1747821d3d65b8943bd'
  - Parity table worst |dp| laya 8.4e-4, julia-1 2.2e-2, lev 5.2e-3, openjev 1.8e-4, kev-4b 1.3e-3 (one synthetic request)
  - Endpoint landed in b11361 per a commenter; frozen tree ffc1bac82 (2026-09-21) predates it
  claim_verdicts:
  - claim_index: 0
    verdict: CONFIRMED
    evidence: PR header + body
  - claim_index: 1
    verdict: CONFIRMED
    evidence: README section; stage-1 recorded only 3 answer types from the d1 card, now sourced to upstream
  - claim_index: 2
    verdict: CONFIRMED
    evidence: server-decision.cpp L49-63 and README sentence
  - claim_index: 3
    verdict: CONFIRMED
    evidence: PR body parity table
  - claim_index: 4
    verdict: PARTIAL
    evidence: family list from PR + search of later PRs; later models are listed from PR titles only, not read
  - claim_index: 5
    verdict: CONFIRMED
    evidence: git merge-base/grep on the frozen tree (not quotable text; commands recorded in dive_corrections)
  claim_anchors:
  - claim_index: 0
    locator: PR 29818 header
    quote: merged_at=2026-10-02T09:56:05Z
  - claim_index: 0
    locator: PR 29818 body
    quote: 'Support 5 decision models: laya, julia-1, lev, openjev (+vision), kev'
  - claim_index: 0
    locator: PR 29818 body (Additional information)
    quote: Main part is `server_decision_context` that switches the input/output handling based on `{arch}.decision.type` gguf metadata.
  - claim_index: 1
    locator: tools/server/README.md @a4cb4c6 L1670-1700
    quote: '- `type`: One of `choice`, `score`, `noul`.'
  - claim_index: 1
    locator: tools/server/README.md @a4cb4c6
    quote: The questions of a request are answered independently, an answer does not depend on the other questions.
  - claim_index: 1
    locator: tools/server/README.md @a4cb4c6
    quote: '`usage`: `input_tokens` is the number of prompt tokens of all questions. `output_tokens` is always 0.'
  - claim_index: 1
    locator: tools/server/README.md @a4cb4c6
    quote: 'The number of options of a `choice` question is limited by the model, for example: 52 for openjev, 255 for laya.'
  - claim_index: 2
    locator: tools/server/README.md @a4cb4c6
    quote: The probabilities are scaled with the temperatures stored in the model file. They are not guaranteed to be calibrated for your data.
  - claim_index: 2
    locator: tools/server/server-decision.cpp @a4cb4c6 L49-63
    quote: const std::string prefix_temp = prefix + "temperature.";
  - claim_index: 3
    locator: PR 29818 body, parity table
    quote: worst diff, any probability | 8.4e-4 | 2.2e-2 | 5.2e-3 | 1.8e-4 | 1.3e-3
  - claim_index: 4
    locator: PR 29818 body TODO list
    quote: maybe support https://huggingface.co/Cloudflare/clef , just out 2 hours ago at the time writing this~~ planned as a follow-up
  - claim_index: 4
    locator: PR 29818 issue comment ServeurpersoCom 2026-10-03
    quote: your build 11200 predates this PR, /v1/systemone landed in b11361 so you just need to update.
  claim_corrections:
  - claim_index: 5
    effect: unaffected
    note: 'new claim appended by dive: frozen tree lacks the endpoint'
  depends_on: []
  dive_corrections: 'Stage-1 (intake-2581/2582) cited the PR only by number and merge date. Dive adds the full request/response schema, the temperature mechanism (GGUF decision.temperature.* keys, no request override), the per-model option limits, the parity table, the build mapping (b11361 for the endpoint) and a git check that the frozen tree has none of it (merge commit not an ancestor of ffc1bac82; no systemone string; no decision source file). Commands: git merge-base --is-ancestor a4cb4c61 ffc1bac82 returned non-ancestor; git grep -i systemone ffc1bac82 empty.'
  reader_should_conclude: 'Cite for the API contract, the temperature-in-GGUF fact and the parity-table scale (<=2.2e-2 on one request). Do NOT read the parity table as a calibration or batch-invariance result: one request, reference is each model''s own Python code.'
  not_read: Full diff of the 35 files (read file list, README, server-decision.cpp L40-66 and head only); later model PRs (d1/LFM3, vllm-d3, Granite switch) read by title only.
- id: intake-2594
  verification: dive-overturned
  read_depth: FULL
  source_revision: github.com/ggml-org/llama.cpp issue 30064 (closed 2026-10-07) + comment + timeline, fix PR 30100 (merge 7e8324f5feba), retrieved 2026-10-31 via GitHub API
  source_text_path: scratch:dive-ws58-20261031/dive/w3dec/src_2594.txt
  key_claims: &id002
  - Issue 30064 (opened 2026-10-06 by a user on build 11429, Apple M5 Max, Metal; closed 2026-10-07 by a maintainer) reported that ggml-org/Clef-GGUF Q8_0 returns /v1/systemone probabilities collapsed toward uniform (Paris->France 0.540 vs BF16 0.994; confidence 0.309 vs 0.991) while BF16 and Kev-4B Q8_0 were correct. The reporter's hypothesis was that the decision.* head tensors were quantized to Q8_0 and should stay BF16.
  - 'CORRECTED CAUSE: the hypothesis is wrong. The fix PR 30100 (merged 2026-10-07T13:41:50Z, commit 7e8324f5feba, +2 lines in ggml-metal-ops.cpp plus a test-backend-ops mode) shows a Metal-backend bug in the fused MUL_MAT+ADD path: when both ADD operands are mat-mul outputs (Clef''s head computes options = proj_option_context @ opt_ctx + proj_option_lexical @ lexical) the encoder picked the fused mat-mul''s own never-written output as the residual. Output is deterministic per memory layout, so it shifts with graph-optimize or fusion toggles. The same Q8_0 file is correct on the CPU backend and with GGML_METAL_FUSION_DISABLE=1.'
  - 'Affected: Metal backend (Apple GPUs), any quant whose head mat-muls take the MMA fused path (the PR test fails 27 of 28 cases pre-fix, the only pass being f16 n=2 below the MMA row threshold) and any graph with the x = W1@u + W2@v pattern. Not shown to affect CPU, CUDA or HIP; the issue and PR report only Metal and CPU. The BF16-head Q4_K_M success in the issue''s follow-up comment is a layout/path coincidence, not proof that heads must stay high-precision.'
  - 'Status: closed and fixed upstream (PR 30100 merged 2026-10-07; the PR bot flagged the description as AI-generated, the diff was reviewed by ggerganov). Workaround ''keep decision.* at BF16'' is unnecessary for this bug. Residual generic lesson that the dive confirms: a quantized or backend-specific decision-head file can return wrong probabilities while still returning a plausible argmax, so per-backend parity against a reference (CPU/BF16) is the only safe gate.'
  reported_results:
  - 'Clef Q8_0 vs BF16, Paris->France: 0.540 vs 0.994 (issue); Metal default billing 0.284 vs CPU/fixed 0.977 (PR 30100)'
  - 'Fix: +2 lines in ggml/src/ggml-metal/ggml-metal-ops.cpp, test-backend-ops mm2+mm mode fails 27/28 pre-fix, 168/168 post'
  claim_verdicts:
  - claim_index: 0
    verdict: CONFIRMED
    evidence: issue body numbers
  - claim_index: 1
    verdict: OVERTURNED
    evidence: stage-1 intake-2582 said head tensors being quantized was the cause; PR 30100 shows a Metal fusion bug and CPU is correct with the same Q8_0 file
  - claim_index: 2
    verdict: CONFIRMED
    evidence: PR 30100 test statement; Metal-only scope is from the sources, not a negative test on HIP
  - claim_index: 3
    verdict: CONFIRMED
    evidence: 'timeline: closed by ggerganov 2026-10-07T13:41:55Z after PR 30100 merge'
  claim_anchors:
  - claim_index: 0
    locator: issue 30064 title
    quote: 'Eval bug: Clef-GGUF Q8_0 /v1/systemone probabilities collapse toward uniform, while BF16 gives correct ones.'
  - claim_index: 0
    locator: issue 30064 body, Hardware
    quote: m5 Max Mac Studio w/128 GB of RAM
  - claim_index: 0
    locator: issue 30064 body, Possible Fix
    quote: keep the decision.* tensors at BF16 when quantizing.
  - claim_index: 1
    locator: PR 30100 body Overview
    quote: '`ggml_metal_op_mul_mat_mma` picks the residual of a fused `MUL_MAT+ADD` as "the ADD operand whose op is not `MUL_MAT`":'
  - claim_index: 1
    locator: PR 30100 body
    quote: Not a quantization issue — the same Q8_0 file is right on the CPU backend
  - claim_index: 1
    locator: PR 30100 body table
    quote: '| Metal, default | 0.284 | 0.431 |'
  - claim_index: 1
    locator: PR 30100 body table
    quote: '| CPU | **0.977** | 0.009 |'
  - claim_index: 1
    locator: PR 30100 header
    quote: merged=2026-10-07T13:41:50Z
  - claim_index: 2
    locator: PR 30100 body Test
    quote: On Metal at `48499d2e1` it fails **27 of 28** cases before
  - claim_index: 3
    locator: PR 30100 body
    quote: 'Fixes #30064.'
  claim_corrections:
  - claim_index: 1
    effect: overturned
    note: cause is a Metal MUL_MAT+ADD fusion residual-selection bug, not quantization of decision-head tensors
  depends_on: []
  dive_corrections: 'Stage-1 text (in intake-2582 key_claims) said decision-head tensors were quantized and that BF16-vs-Q8 parity must be checked per file. The first half is overturned: the cause is a Metal backend bug fixed in PR 30100 on 2026-10-07 and the same Q8_0 file is correct on CPU. The recommendation (check parity per file and backend) survives but for a different reason: backend fusion paths can silently corrupt a head.'
  reader_should_conclude: 'Cite as: a Metal-only fusion bug, fixed; not evidence that Q8_0 hurts decision heads. Do not carry the BF16-head recipe as a requirement. Do carry the test design (same file, CPU vs GPU, BF16 vs quant, per-backend).'
  not_read: Issue 30064 cross-referenced repos (oboete) not read; Clef model card not read.
- id: intake-2595
  verification: dive-verified
  read_depth: FULL
  source_revision: github.com/ggml-org/llama.cpp issue 30402 (open, 0 comments, build 11572/efe3626b1) + PR 30408 (merge cbe28bb3cb07) + issues 30482/31475/31150/29902/30073 + PR 30710/30567, retrieved 2026-10-31 via GitHub API; sha256 of paper not applicable
  source_text_path: scratch:dive-ws58-20261031/dive/w3dec/src_2595.txt
  key_claims: &id003
  - Issue 30402 (opened 2026-10-12 against build 11572 / efe3626b1 on CUDA RTX 4000 Ada; ggml-org/vllm-d3-mini-GGUF Q8_0, -np 3 -c 12288 -b 2048 -ub 2048 -sps 0) reports that a /v1/systemone noul answer for request A changes from 0.2839 alone to 0.449-0.450 on every run when a shorter request is decoded in the same batch. It is the vllm-d3 model, not a d1 model; no d1 or Kev model is shown affected by the issue itself.
  - 'Cause per the reporter''s title: the batch splitter split_equal cuts non-causal (bidirectional) prompts across ubatches, so a prompt whose tokens are partly in a later ubatch loses cross-chunk attention and its answer depends on what shares the batch. Maintainer PR 30408 (''model: fix vllm d3 multi seq case'', merged 2026-10-12T22:23:02Z, ~5 h after the report) adds the same invariant for the KV-cache memory paths: when attention is non-causal, keep all tokens of a sequence in one ubatch and use split_seq instead of split_equal (''non-causal + hybrid + multi seq''). The same invariant was fixed earlier for cache-less encoder models in #29902/#29903 (server batch capped to ubatch).'
  - 'Status: issue still OPEN at retrieval (2026-10-31), 0 comments, no maintainer triage and no retest after 30408, so whether 30408 closes it is UNCONFIRMED. The conditions are: bidirectional (non-causal) decision model + more than one concurrent request in the same decode (multiple slots/sequences of unequal length) + prompt shorter than ubatch. Reporter''s own condition: the longer request must be batched with a shorter one; equal-length (identical) companions were also tested in the repro script but the issue does not report their result.'
  - 'Related residual batch-sensitivity: issue 31475 (open, 2026-10-31) states bitwise equality of /v1/systemone probabilities is not guaranteed when shared-prefix scheduling changes the batch cuts (one synthetic probability moved by about 0.007), and the PR 29818 parity table shows julia-1 differing from its reference by up to 2.2e-2. So batch/schedule invariance has to be MEASURED per build, not assumed, even for causal Kev-style models.'
  - 'Other serving defects in the same family that bound a safe probe configuration: 500 ''the question and its options must fit in one batch'' when two questions share a prefix and -np >= 2 (issue 30482, fixed by PR 30710 merged 2026-10-17); router-mode concurrent requests killing the model instance (issue 31150, open, reported on an old build); -b is the logical and -ub the physical batch so a state longer than -ub fails (issue 30073, user error).'
  reported_results:
  - Alone 0.2839 vs batched with shorter request 0.449-0.450 (every run), vllm-d3-mini Q8_0, -np 3 -b 2048 -ub 2048
  - Issue state open, 0 comments at 2026-10-31; PR 30408 merged 2026-10-12T22:23:02Z (small diff, 5 files in src/)
  - 'Residual: 0.007 probability shift from batch cuts (issue 31475); julia-1 up to 2.2e-2 vs reference (PR 29818)'
  claim_verdicts:
  - claim_index: 0
    verdict: PARTIAL
    evidence: issue is about vllm-d3-mini; stage-1 framing of d1 batch dependence is not supported
  - claim_index: 1
    verdict: PARTIAL
    evidence: title states the cause; PR 30408 supports the mechanism but its relation to this issue is the maintainer-less inference
  - claim_index: 2
    verdict: CONFIRMED
    evidence: issue state/comments
  - claim_index: 3
    verdict: CONFIRMED
    evidence: issue 31475 body and PR 29818 table
  - claim_index: 4
    verdict: CONFIRMED
    evidence: issues 30482/30073/31150 bodies and PR 30710 body
  claim_anchors:
  - claim_index: 0
    locator: issue 30402 title
    quote: 'Eval bug: vllm-d3 answers change when a shorter request shares the batch (split_equal splits non-causal prompts)'
  - claim_index: 0
    locator: issue 30402 body
    quote: Sent alone, request A always gets noul = 0.2839. Batched with a shorter request it gets 0.449 to 0.450, on every run.
  - claim_index: 0
    locator: issue 30402 body, serve.sh
    quote: -ngl 99 -np 3 -c 12288 -b 2048 -ub 2048 -sps 0
  - claim_index: 0
    locator: issue 30402 body
    quote: 'version: 0.6.0-dev (build 11572, commit efe3626b1)'
  - claim_index: 1
    locator: PR 30408 patch src/llama-context.cpp
    quote: // non-causal attention needs the whole sequence in one ubatch
  - claim_index: 1
    locator: PR 30408 body
    quote: 'Not 100% sure but seems like there is a problem with the case: non-causal + hybrid + multi seq'
  - claim_index: 1
    locator: PR 30408 header
    quote: PR 30408 (merged 2026-10-12T22:23:02Z)
  - claim_index: 1
    locator: issue 29902 body
    quote: Server collects several questions up until n_batch, but Laya must process batch with one ubatch (cause no KV-memory)
  - claim_index: 2
    locator: issue 30402 header
    quote: state=open created=2026-10-12T17:38:11Z closed=None comments=0
  - claim_index: 3
    locator: issue 31475 body
    quote: Also, bitwise equality is not guaranteed because different batch cuts changed one synthetic probability by about `0.007`.
  - claim_index: 4
    locator: issue 30482 body
    quote: failed to get embeddings, the question and its options must fit in one batch
  - claim_index: 4
    locator: PR 30710 body
    quote: Limit the shared prompt prefix to each task's first required output position
  claim_corrections:
  - claim_index: 0
    effect: narrowed
    note: stage-1 filing described this as a generic decision-model batch-dependence; the report is for vllm-d3-mini, non-causal+hybrid, and no d1 model is shown affected
  depends_on: []
  dive_corrections: 'Stage-1 filing was a bare pointer. Dive narrows it to the vllm-d3 model, identifies the non-causal split_equal mechanism, finds the likely fix PR 30408 (merged hours after the report; no one has retested) and adds the open adjacent defects (31475 schedule sensitivity, 31150 router crash, 30482 500s fixed by 30710). The linked claude.ai artifact with the reporter''s proposed fix was not readable. Not asserted: that d1 (LFM3 conv/attention hybrid) or Kev are batch-sensitive.'
  reader_should_conclude: Cite for the invariant (non-causal sequences must stay whole in one ubatch) and for the test shape. Do not cite 30402 as proof that d1 is batch-dependent; do not assume 30408 fixes it until retested on a build containing cbe28bb3.
  not_read: Reporter's linked claude.ai artifact fix; commit comment 204575113 on efe3626b1; source of llama-batch.cpp split_equal/split_seq.
- id: intake-2596
  verification: dive-verified
  read_depth: FULL
  source_revision: arXiv:2610.28577v1 HTML sha256-12 720743b692be, retrieved 2026-10-31 (submitted 20 Oct 2026)
  source_text_path: scratch:dive-ws58-20261031/dive/w3dec/paper.txt
  key_claims: &id004
  - 'arXiv:2610.28577v1 (cs.CL, submitted 20 Oct 2026; title confirmed on the abs page: ''Cache Engineering for Agents''; Tsinghua University + CUHK, corresponding author Yu Wang) proposes cache engineering: the agent harness controls the ACTIVE KV cache with two operations beyond append. drop(P) removes selected KV entries from future attention while leaving retained entries, their position encodings and the logical token sequence unchanged; repos rotates retained keys with RoPE (K <- R(q) R(p)^-1 K, values unchanged), compacting positions to 0..r-1 and resetting the next position index. No re-prefill of retained context.'
  - 'Mechanism for the retained KV: a retained entry''s K/V were computed while attending to the since-dropped tokens, so it can still carry information from them (Figure 1, ''nested color blocks''); drop is NOT equivalent to deleting the text and re-prefilling. The paper''s primary policy is tool-response rolling drop (keep KV of the latest 12 tool responses, drop older ones), with repos triggered at a threshold equal to the Standard baseline''s summarization threshold.'
  - 'Prefix-matching correctness hazard (the load-bearing finding): cache state is history-dependent. The same token prefix and retained positions can have different KV under different drop/append/repos orders (Figure 5: C''s KV differs in all three trajectories that retain B and C), so ordinary token-prefix matching can reuse an incorrect state. AKV (built on SGLang) keys an extended radix tree on tokens PLUS operation history (drop nodes, reposition nodes, per-token position labels, exact vs ''retrigger'' matching), evicts dropped cache first and per positional version, and restores evicted segments in one prefill pass with segment-batch attention (queries split at drop/repos points; FFN still processes the whole sequence as one batch). Interface: stateless OpenAI-style request with messages plus cache{drop, reposition}.'
  - 'Agent results (Table 1; MiniMax-M2.7, GPT-OSS-120B, MiroThinker-1.7-Mini x BCP, GAIA-Text, SWE-Verified, xbench-DS): average score AKV 53.7 / 53.1 / 45.8 vs Standard 52.4 / 51.0 / 44.1 (+1.3 to +2.1 points), average cost AKV 4.4 / 7.3 / 14.8 vs Standard 5.0 / 11.2 / 20.4 cents; -27.7% cost vs Standard and -21.9% vs Text Engineering averaged over all 12 cells. Wins are not uniform (e.g. GPT-OSS-120B xbench 37.5 vs 38.5; MiniMax SWE 74.4 vs 75.2). Costs are API-price-table estimates (Groq, MiniMax, Qwen3-30B-A3B rates) from active tokens, with repos tokens charged at the cache-hit rate; not measured spend.'
  - 'Serving results (Table 2; GPT-OSS-120B, Top-80 longest SWE-Verified trajectories replayed at temperature 0 with ignore_eos, 8x A800-80GB BF16, 4 prefill + 4 decode GPUs, TP4, SGLang base): peak-throughput comparison AKV C=14 vs Standard C=12 gives 1.36x mean / 1.51x P95 latency, 1.53x input / 1.18x output throughput (input counts all logical tokens including dropped). Caveats: Standard at C>=14 is reported over a fixed one-hour window with unfinished requests; AKV''s higher-C rows are truncated at the first 30 completed tasks; replay length per method differs because each replays trajectories from its own policy; decode speedup comes mainly from shorter attention (Fig 12).'
  - 'Ablations and limits: repos raises BCP pass rate 55 -> 62 (Table 3/4, GPT-OSS-120B first 100 tasks) by removing a position limit, at higher cost 7.1 -> 10.9; dropping reasoning KV lowers pass rate vs tool-only drop; recursive self-improvement policies cut cost 15.6% (iter 3) and 17.8% (iter 6) vs Standard on 100 held-out BCP tasks (the abstract''s 7.1% is vs the expert policy); GPT-OSS-20B average 45.2 / 4.8 cents (Table 7); KV reads are 82.4% of API cost in their accounting. Authors'' stated limitation: linear-attention models are future work, so hybrid-SSM models (Qwen3.5/3.6 family in our fleet) are outside the evidence.'
  reported_results:
  - 'Table 1 avg score/cost: MiniMax AKV 53.7/4.4 vs Standard 52.4/5.0; GPT-OSS-120B 53.1/7.3 vs 51.0/11.2; MiroThinker 45.8/14.8 vs 44.1/20.4'
  - 'Table 2 peak: AKV C=14 51837 in / 369 out tok/s, 9.09 s mean, 28.49 s P95; Standard C=12 33832 / 313, 12.39 s, 43.16 s'
  - 'Table 3/4: Tool drop without repos BCP 55.0 cost 7.1; with repos 62.0 cost 10.9; Table 7 GPT-OSS-20B avg 45.2/4.8'
  claim_verdicts:
  - claim_index: 0
    verdict: CONFIRMED
    evidence: abstract + §3.3
  - claim_index: 1
    verdict: CONFIRMED
    evidence: §1 Fig 1 caption, §5.1
  - claim_index: 2
    verdict: CONFIRMED
    evidence: §4.2
  - claim_index: 3
    verdict: CONFIRMED
    evidence: 'Table 1 recomputed: +1.3/+2.1/+1.7 points; cost 27.7% and 21.9% from §5.2'
  - claim_index: 4
    verdict: CONFIRMED
    evidence: 'Table 2 recomputed: 51837/33832=1.53, 369/313=1.18, 12.39/9.09=1.36, 43.16/28.49=1.51; caveats added'
  - claim_index: 5
    verdict: CONFIRMED
    evidence: Tables 3/4/7, §5.4, §6
  claim_anchors:
  - claim_index: 0
    locator: v1 abstract
    quote: 'We formalize these cache operations and identify history dependence as a serving challenge: identical token sequences can yield different cache states under different cache operation sequences, making prefix matching insufficient for correct cache reuse.'
  - claim_index: 0
    locator: v1 §3.3 Drop
    quote: removes selected KV states from subsequent attention, while leaving the retained states, their position encodings, and the logical token sequence unchanged
  - claim_index: 1
    locator: v1 §1
    quote: Nested color blocks illustrate how retained KV can still carry information from dropped history.
  - claim_index: 1
    locator: v1 §5.1 Baselines
    quote: For AKV, we use a tool-response rolling-drop policy that retains the KV states of the latest 12 tool responses.
  - claim_index: 2
    locator: v1 §4.2.1
    quote: Token prefixes alone no longer determine cache states, so ordinary prefix matching can incorrectly reuse states from different cache operation histories
  - claim_index: 2
    locator: v1 §4.2.2
    quote: Only attention is segmented, while the FFN processes the full sequence as one batch.
  - claim_index: 2
    locator: v1 §4.2.3
    quote: 'Prefix matching checks both token and operation histories: matching position indices allow direct reuse, while differing indices require key rotation.'
  - claim_index: 3
    locator: v1 §5.2
    quote: AKV also reduces inference cost by 27.7% relative to Standard and 21.9% relative to Text Engineering, averaged across all three models and four benchmarks.
  - claim_index: 3
    locator: v1 §5.1 Metrics
    quote: deliberately overestimating the cost of key rotation for a conservative comparison.
  - claim_index: 4
    locator: v1 §5.1 Serving configuration
    quote: 'Serving experiments use eight NVIDIA A800-80GB GPUs: four for prefill and four for decode, with tensor parallelism of four.'
  - claim_index: 4
    locator: v1 App A.1.4
    quote: We use temperature 0 and ignore_eos=True to generate the prescribed number of tokens.
  - claim_index: 4
    locator: v1 App A.1.4
    quote: We therefore report these two runs over a fixed one-hour window, with some requests still unfinished at the cutoff.
  - claim_index: 5
    locator: v1 §5.4
    quote: The policies from iterations 3 and 6 reduce per-task cost by 15.6% and 17.8% relative to Standard, respectively.
  - claim_index: 5
    locator: v1 §1
    quote: KV cache reads take up 82.4% of the total API cost.
  - claim_index: 5
    locator: v1 §6 Limitations
    quote: Further exploration of cache engineering strategies, training agents under this scheme, and extending serving support to linear attention models remain future work.
  claim_corrections:
  - claim_index: 4
    effect: narrowed
    note: throughput/latency ratios hold for peak-vs-peak comparison but Standard C>=14 is a truncated one-hour window and replays use ignore_eos
  depends_on: []
  dive_corrections: 'Confirms the stage-1 AKV repo entry (intake-2590) against the paper and adds: exact drop/repos formulas, the segment-batch attention design, the repos-node reasoning (A.1.2), the replay/truncation caveats, and the linear-attention limitation. Intake-2590 numbers recompute from the tables. Nothing overturned.'
  reader_should_conclude: Cite for the history-dependence hazard and the drop/repos semantics. Cost numbers are price-table estimates and serving numbers are SGLang BF16 on 8xA800 with replayed trajectories; not transferable to llama.cpp on EPYC/MI210. Hybrid-SSM models are outside the evidence.
  not_read: Appendix A.1.1 kernel details, A.3, A.4 cost breakdowns, A.5 concurrent work, Figures (images), reference list, repo code.
new_entries:
- id: intake-2593
  arxiv_id: null
  url: https://github.com/ggml-org/llama.cpp/pull/29818
  source_type: repo
  title: 'llama.cpp PR 29818: /v1/systemone typed decision endpoint (laya, julia-1, lev, openjev, kev)'
  categories:
  - routing_intelligence
  - inference_serving
  - local_inference
  novelty: medium
  relevance: high
  discovered_via: expansion
  expanded_from: intake-2581
  verdict: worth_investigating
  ingested_date: '2026-10-31'
  authors:
  - ngxson (PR author)
  - ggml-org maintainers (review)
  key_claims: *id001
  techniques:
  - decision head on embedding models
  - server_decision_context
  - typed choice/score/noul answers
  - GGUF-stored softmax temperatures
  reported_results:
  - 'see key_claims: merge date, parity table'
  cross_references:
    chapters: []
    handoffs:
    - typed-decision-plane.md
    - routing-intelligence.md
    - learned-routing-controller.md
    experiments: []
    intake_entries:
    - intake-2581
    - intake-2582
    - intake-1498
  recommended_actions:
  - 'TD-23/TD-20: any local decision-model screen needs this endpoint on an experimental branch; see ledger W3DEC-1..5'
  credibility_score: null
  contradicting_evidence: null
  referenced_arxiv_ids: []
  notes: 'Upstream PR record; GitHub API incl. all comments. Not read: full diff.'
  verification: stage1-unverified
  handoffs_updated: []
  handoffs_created: []
  source_revision: github.com/ggml-org/llama.cpp PR 29818 (merge a4cb4c61fd9d, 2026-10-02) via GitHub API incl. 6 comments, 6 review comments, tools/server/README.md and server-decision.cpp @a4cb4c6, retrieved 2026-10-31; frozen tree ffc1bac82 checked by git
  reader_should_conclude: 'Stage-1 unverified: do not cite.'
- id: intake-2594
  arxiv_id: null
  url: https://github.com/ggml-org/llama.cpp/issues/30064
  source_type: repo
  title: 'llama.cpp issue 30064: Clef Q8_0 /v1/systemone probabilities collapse (Metal MUL_MAT+ADD fusion bug, fixed by PR 30100)'
  categories:
  - routing_intelligence
  - quantization
  - inference_serving
  novelty: low
  relevance: medium
  discovered_via: expansion
  expanded_from: intake-2582
  verdict: adopt_patterns
  ingested_date: '2026-10-31'
  authors:
  - freeformz (reporter)
  - nyo16 (fix PR 30100)
  key_claims: *id002
  techniques:
  - per-backend parity check
  - fusion toggles as bisect tool
  reported_results:
  - see key_claims
  cross_references:
    chapters: []
    handoffs:
    - typed-decision-plane.md
    experiments: []
    intake_entries:
    - intake-2582
  recommended_actions:
  - 'TD-23: include a CPU-vs-GPU and BF16-vs-Q8 parity gate; see ledger W3DEC-1'
  credibility_score: null
  contradicting_evidence: null
  referenced_arxiv_ids: []
  notes: Issue closed; cause is Metal fusion not quantization.
  verification: stage1-unverified
  handoffs_updated: []
  handoffs_created: []
  source_revision: github.com/ggml-org/llama.cpp issue 30064 (closed 2026-10-07) + comment + timeline, fix PR 30100 (merge 7e8324f5feba), retrieved 2026-10-31 via GitHub API
  reader_should_conclude: 'Stage-1 unverified: do not cite.'
- id: intake-2595
  arxiv_id: null
  url: https://github.com/ggml-org/llama.cpp/issues/30402
  source_type: repo
  title: 'llama.cpp issue 30402: vllm-d3 /v1/systemone answers change when a shorter request shares the batch (non-causal split_equal)'
  categories:
  - routing_intelligence
  - inference_serving
  - benchmark_methodology
  novelty: low
  relevance: medium
  discovered_via: expansion
  expanded_from: intake-2582
  verdict: adopt_patterns
  ingested_date: '2026-10-31'
  authors:
  - ivoras (reporter)
  key_claims: *id003
  techniques:
  - batch-invariance test with concurrent unequal-length requests
  - non-causal sequences stay in one ubatch
  reported_results:
  - see key_claims
  cross_references:
    chapters: []
    handoffs:
    - typed-decision-plane.md
    experiments: []
    intake_entries:
    - intake-2582
  recommended_actions:
  - 'TD-23: batch-invariance gate; see ledger W3DEC-2'
  credibility_score: null
  contradicting_evidence: null
  referenced_arxiv_ids: []
  notes: Open issue; fix PR 30408 likely but unconfirmed.
  verification: stage1-unverified
  handoffs_updated: []
  handoffs_created: []
  source_revision: github.com/ggml-org/llama.cpp issue 30402 (open, 0 comments, build 11572/efe3626b1) + PR 30408 (merge cbe28bb3cb07) + issues 30482/31475/31150/29902/30073 + PR 30710/30567, retrieved 2026-10-31 via GitHub API; sha256 of paper not applicable
  reader_should_conclude: 'Stage-1 unverified: do not cite.'
- id: intake-2596
  arxiv_id: '2610.28577'
  url: https://arxiv.org/abs/2610.28577
  source_type: paper
  title: Cache Engineering for Agents
  categories:
  - kv_cache
  - agent_architecture
  - inference_serving
  - context_management
  novelty: medium
  relevance: medium
  discovered_via: expansion
  expanded_from: intake-2590
  verdict: worth_investigating
  ingested_date: '2026-10-31'
  authors:
  - Tianyu Fu
  - Ruoxi Wang
  - Zihan Min
  - Zhongqi Ren
  - Zhihao Li
  - Tengxuan Liu
  - Shengxu Mu
  - Hanling Zhang
  - Yu Wang
  key_claims: *id004
  techniques:
  - KV drop
  - RoPE reposition
  - history-aware radix tree
  - drop-aware eviction
  - segment-batch attention
  - cache-as-tool
  - recursive self-improvement of cache policies
  reported_results:
  - 'see key_claims: Tables 1,2,3/4,7'
  cross_references:
    chapters: []
    handoffs:
    - kv-prefix-fork-and-paged-attention.md
    - context-folding-progressive.md
    - tool-output-compression.md
    experiments: []
    intake_entries:
    - intake-2590
    - intake-2559
  recommended_actions:
  - see ledger W3DEC-6..8
  credibility_score: 3
  contradicting_evidence: null
  referenced_arxiv_ids:
  - '2610.28577'
  notes: Companion paper of intake-2590 (repo). Read v1 HTML in full except appendices A.1.1, A.3, A.4, A.5. Single-lab, no peer review yet, price-table cost.
  verification: stage1-unverified
  handoffs_updated: []
  handoffs_created: []
  source_revision: arXiv:2610.28577v1 HTML sha256-12 720743b692be, retrieved 2026-10-31 (submitted 20 Oct 2026)
  reader_should_conclude: 'Stage-1 unverified: do not cite.'
ledger:
- row: W3DEC-1
  entries:
  - intake-2593
  - intake-2594
  action: 'Add a precision-and-backend parity gate to the TD-23 decision-backend screen BEFORE any quality or calibration number is read: for the chosen decision GGUF (d1-2B Q8_0 first), serve the BF16 file on CPU as reference, then Q8_0 on CPU, Q8_0 on HIP (MI210), and BF16 on HIP; send >=30 fixed state/question fixtures covering choice, score and noul types; record every probability, argmax, confidence and the build SHA, device and GGML env. 30064 proves a wrong-probability bug can look like quantization while the cause is a backend fusion path (Metal, fixed by 30100); the same class of risk applies to HIP fused mat-mul paths in a build we have not run. Test the exact pattern that broke: heads of the form W1@u + W2@v.'
  grounding: handoffs/active/typed-decision-plane.md:599 (TD-23 freezes backend/model revisions, retains per-row probabilities, reports ECE/Brier and probability divergence but has no BF16/Q8 or cross-backend parity row); handoffs/active/typed-decision-plane.md:464 (TD-18 receipt has n, ECE, Brier, 10 bins and no model-pin field)
  owner: handoffs/active/typed-decision-plane.md
  posture: cheap-screen-now
  benefit: 'Prevents a calibration or routing verdict resting on a corrupted head; direction = fewer silent wrong probabilities. Must stay correct: the reference is the BF16 CPU run of the SAME GGUF lineage, not the vendor Python numbers.'
  decision_rule: Per fixture set, stop (file as backend defect, do not calibrate) if any argmax flips or worst |dp| vs BF16-CPU exceeds 2.2e-2 (the worst parity gap upstream itself published, julia-1 in PR 29818); promote the Q8_0 file only if worst |dp| <= 2.2e-2 and 0 flips on CPU and HIP. The run itself rides the TD-23 mi210 window; fixture writing is zero-inference now.
  reason: Turns two upstream incidents into a predeclared gate the d1 probe lacks.
- row: W3DEC-2
  entries:
  - intake-2595
  - intake-2593
  action: 'Add a batch-/schedule-invariance gate to the same screen: serve with -np 3, -b = -ub = 2048 (state must fit one ubatch), send request A alone (x5), then A concurrently with a shorter, a longer and an identical companion (x5 each, with a blocker request to force co-batching, as in the 30402 repro), and also with -np 1; record A''s probabilities and the max per-run drift. Run it on a build that includes PR 30408 (cbe28bb3, merged 2026-10-12) and PR 30710 (shared-prefix cap, 2026-10-17); also run once WITHOUT 30408 on the same model to reproduce the defect and prove the harness can see it (a harness that cannot fail is not evidence).'
  grounding: handoffs/active/typed-decision-plane.md:599 (TD-23 crosses position, order, repeated calls and "irrelevant siblings" but not concurrent co-batching of unequal-length requests); handoffs/active/typed-decision-plane.md:464; /v1/systemone answers each question as an independent task that can land on different slots (PR 29818 README)
  owner: handoffs/active/typed-decision-plane.md
  posture: cheap-screen-now
  benefit: 'Determines whether a router built on a decision model is deterministic under production concurrency; must stay correct: -np and -ub of the probe equal the intended serving config.'
  decision_rule: Invariant if max |dp| across all companion types <= 1e-3 (and bitwise within the same schedule); between 1e-3 and 2.2e-2 -> restrict serving to -np 1 / serialized decisions and record the tolerance in the receipt; above 2.2e-2 or any argmax flip -> stop, file upstream with the repro. Issue 31475 already reports 0.007 shifts from batch cuts on Kev, so the 1e-3 line is expected to bind.
  reason: 30402 is open and 30408 untested; concurrency is exactly how the orchestrator would call a router.
- row: W3DEC-3
  entries:
  - intake-2593
  - intake-2581
  - intake-2582
  action: 'Plan the build route for any /v1/systemone work: the frozen v10 tree has neither the endpoint (PR 29818 merge a4cb4c61 is not an ancestor of ffc1bac82; no systemone string; no *decision* file in tools/server) nor LFM3 (needs >= b11960). Cheapest honest route = a scratch UPSTREAM checkout at a pinned post-2026-10-17 SHA used only as the measurement instrument (CPU and HIP builds under scratch, never touching the frozen tree), because porting 35 files/+2139 lines (llama-arch, llama-model, models/qwen35.cpp, modern-bert.cpp, server-*.cpp) onto llama.cpp-experimental cut from v10 would conflict with the fork''s qwen35 patches and is only justified if the screen promotes. TD-20 already takes the lighter route (new files only, no src/ change) for Kev; record that the d1 route needs src/ changes and so is a different, heavier port.'
  grounding: 'handoffs/active/typed-decision-plane.md:467 (TD-20: port common/decision.{h,cpp} + tools/kev as new files, branch from ffc1bac); CLAUDE.md production-immutability and experimental-branch rule; git check in this dive'
  owner: handoffs/active/typed-decision-plane.md
  posture: cheap-screen-now
  benefit: Avoids both a frozen-tree edit and a premature heavy port; keeps the screen runnable on an instrument whose differences from production are known.
  decision_rule: Promote to an experimental-branch port only if the TD-23 screen passes W3DEC-1/2 AND beats the constrained incumbent on the sealed set; otherwise the scratch upstream build is deleted after the receipts are filed.
  reason: Build cost estimated, not a decline reason.
- row: W3DEC-4
  entries:
  - intake-2593
  - intake-2582
  action: 'Record in the TD-18 calibration receipt the model pin that determines the probabilities: GGUF sha256, every decision.temperature.* metadata key/value (read with gguf-dump), llama.cpp build SHA, -b/-ub/-np, and the question kind plus option count (some temperatures are bucketed by option count). Calibrate on OUR post-temperature outputs; do not treat shipped temperatures as calibrated (README says so) and do not tune a request-time temperature (none is exposed).'
  grounding: handoffs/active/typed-decision-plane.md:464 (receipt "has no model-pin field"); tools/server/README.md @a4cb4c6 "probabilities are scaled with the temperatures stored in the model file"
  owner: handoffs/active/typed-decision-plane.md
  posture: primitive-now
  benefit: Makes calibration comparable across GGUF re-releases; zero-inference schema change.
  decision_rule: n/a (schema field); done when the receipt schema carries the fields and a zero-inference adapter populates them for a downloaded GGUF header.
  reason: Cheap, prevents uncalibrated-temperature mixups.
- row: W3DEC-5
  entries:
  - intake-2593
  - intake-2595
  action: 'Pin the serving-safe API subset for the probe and any shim: only choice/score/noul; options within the model limit (52 openjev, 255 laya; read from the model, d1 limits unread); state must fit one ubatch (use -ub, not -b; 30073); avoid router mode with concurrent decisions (31150 open, old build) and re-check shared-prefix 500s on builds before 30710. For the TD-19 shim direction (OUR path behind Kev''s /v1/systemone) keep response fields exactly: choice/probabilities/confidence, score/legend, noul, usage.output_tokens=0.'
  grounding: handoffs/active/typed-decision-plane.md:466 (TD-19 shim contract is Kev's; PR 29818 README is the llama.cpp-side contract); issues 30073, 31150, 30482
  owner: handoffs/active/typed-decision-plane.md
  posture: knowledge-only
  benefit: Fewer false failures in the screen; keeps the shim wire-compatible with both Kev's client and llama-server.
  decision_rule: n/a
  reason: Constraint list for the probe designer.
- row: W3DEC-6
  entries:
  - intake-2596
  - intake-2590
  action: 'Add one binding design line to the KV prefix-fork program: any future KV-editing operation (cell drop, position shift, ctx-shift variants) invalidates token-prefix matching as a correctness test; the orchestrator PrefixIndex and llama-server slot reuse key on prompt text/tokens only, so an edited slot must carry its operation history in its key or be excluded from reuse and from fork sources. Frozen v10 already has the primitives (llama_memory seq_rm/seq_add, --context-shift at common/arg.cpp:1562, used server-context.cpp:2985), but context-shift edits the slot token list too, so its prefix match stays self-consistent; AKV-style drop (text kept, KV removed) is the case that breaks it.'
  grounding: kv-prefix-fork-and-paged-attention.md:118-119 ("a client-side prefix structure cannot share KV the server does not share"); /workspace/repos/epyc-orchestrator/src/inference/prefix_index.py:36-38 (key = fingerprinted prompt text) and :1-12 (slot entries verified by /slots id_task); src/backends/llama_server.py:128-135,789 (cache_prompt default True)
  owner: handoffs/active/kv-prefix-fork-and-paged-attention.md
  posture: knowledge-only
  benefit: 'Prevents a silent wrong-KV reuse if cache editing is ever added; must stay correct: reuse is allowed only on equal token AND operation history.'
  decision_rule: n/a (design constraint); revisit if W3DEC-7 promotes.
  reason: The paper's load-bearing correctness finding mapped onto our actual prefix machinery.
- row: W3DEC-7
  entries:
  - intake-2596
  - intake-2590
  action: 'Zero-inference size screen before any AKV-style work: from existing orchestrator serving records and autopilot/REPL traces, compute for long agent loops the share of resident context tokens that are tool responses older than the latest 12 (the paper''s drop policy), per role/model, and the fraction of decode steps whose context exceeds 48K/96K (the paper''s summarization thresholds). Report median and P95 per role.'
  grounding: tool-output-compression.md and context-folding-progressive.md (current context-reduction levers are text-level); prefix_index.py:36-38 shows the serving fingerprint already records prompt text per request
  owner: handoffs/active/context-folding-progressive.md
  posture: cheap-screen-now
  benefit: 'Bounds the possible saving: paper reports -27.7% cost and 1.5x P95 on SGLang/A800 with replay, a number that cannot transfer to EPYC CPU decode without this share.'
  decision_rule: Escalate to W3DEC-8 only if old tool-response tokens are >=40% of resident context in the median long loop AND >=20% of decode steps exceed 48K tokens; otherwise decline AKV-style KV drop for our stack on measured grounds (CPU decode is bandwidth-bound, so only attention-read savings at long context pay).
  reason: Predeclared threshold; avoids building on a transferability assumption.
- row: W3DEC-8
  entries:
  - intake-2596
  - intake-2590
  action: 'Conditional on W3DEC-7: a bounded semantics probe on an attention-only role model on llama.cpp-experimental: compare (a) seq_rm of old tool-response cells + seq_add repositioning (the drop+repos analogue) vs (b) re-prefill of the text with those responses removed vs (c) full context, on a replayed REPL trace set, scoring next-token KL and task success. Hybrid-SSM roles (Qwen3.5/3.6 family) are excluded: their recurrent state integrates dropped tokens irreversibly and the paper lists linear attention as future work.'
  grounding: frozen tree common/arg.cpp:1562 and server-context.cpp:1281-1295,2985 (ctx-shift disabled for multimodal and some contexts); paper §6 Limitations
  owner: handoffs/active/kv-prefix-fork-and-paged-attention.md
  posture: monitor
  benefit: 'Would show whether retained-KV-carries-dropped-information helps (paper: repos+tool drop 55->62 BCP) or hurts on our models; must stay correct: compare against re-prefill, not only full context.'
  decision_rule: Do not start unless W3DEC-7 passes; then promote if (a) matches (c) within the noise floor on task success and (a) beats (b) on decode tokens/s at >=48K context; stop if success drops >2 points vs (c).
  reason: Gated behind a measurement; build costs (server-level op-history key, per-request drop spec) estimated as a P2-sized program, not a decline.
dive_surfaced_sources:
- source: https://github.com/ggml-org/llama.cpp/pull/30408
  settles: whether the non-causal multi-seq batch-split fix closes 30402 (read the full diff and llama-batch split_seq semantics)
  bears_on: intake-2595
  recommend: ingest-and-dive
- source: https://github.com/ggml-org/llama.cpp/pull/30100
  settles: the Metal fusion root cause of 30064 and test-backend-ops mm2+mm check; whether an equivalent residual-selection bug exists in the HIP/CUDA fusion encoders
  bears_on: intake-2594
  recommend: ingest-and-dive
- source: https://github.com/ggml-org/llama.cpp/issues/31475
  settles: 'shared-prefix scheduling changes probabilities by ~0.007 and the checkpoint-for-decision-tasks fix (3.8x throughput on Kev-4B at 4 slots): serving-throughput and invariance trade'
  bears_on: intake-2595
  recommend: ingest-and-dive
- source: https://github.com/ggml-org/llama.cpp/issues/31150
  settles: router-mode concurrent /v1/systemone instance death (old build; maintainer asked for retest)
  bears_on: intake-2593
  recommend: 'decline: reported on an outdated build and no repro on current master; revisit if the probe uses router mode'
- source: https://github.com/ggml-org/llama.cpp/pull/29832
  settles: alternative model-agnostic systemone/decision implementation (open) that may supersede the upstream server_decision_context path
  bears_on: intake-2593
  recommend: ingest-and-dive
artifact_audit: clean
```
