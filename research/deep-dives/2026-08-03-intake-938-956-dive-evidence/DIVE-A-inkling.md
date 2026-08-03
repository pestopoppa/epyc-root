# DIVE-A — Inkling (intake-941, 942, 955) — ROLE CANDIDATE ASSESSMENT

## VERDICT
- worker_general: **NO**, decisively.
- architect_critic: **CONDITIONAL -> effectively NO**; condition is upstream, not ours.

## The speed arithmetic (the operator's stated axis)
- gemma4-26B-A4B incumbent: ~2.0 GB active-bytes/token -> 48.5 t/s CPU
  (our own roofline: fable5-window2-findings-05-intake-sweep-and-roofline.md:46)
- Inkling-Small UD-IQ2_M (82.4GB): 3.58 GB/tok
- Inkling-Small UD-IQ4_XS (127GB): 5.52 GB/tok
- => projected 13-28 t/s = **2-4x SLOWER** before novel-arch overhead
- Calibrating precedent: our DeepSeek-V4 port predicted 18-23 t/s from active-param
  extrapolation, actually delivered 9.13 t/s (~2.5x per-active-param compute penalty)
- worker_general is ALIASED BY worker_math + toolrunner and runs multi-instance:
  swapping 16GB -> 82-127GB in the hottest most-replicated lane is categorically wrong.

## architect_critic: parity, not a win, and it CLOSES a better path
- incumbent Qwen3.5-122B-A10B UD-Q4_K_M = 5.66 GB/tok; Inkling UD-IQ4_XS = 5.52 GB/tok. Parity.
- BUT the 122B has a MEASURED, eval-parity-passed fully-GPU-resident IQ2 path:
  **43.7 t/s single / 148.7 t/s aggregate on the MI210.**
- Inkling's smallest quant is 82.4GB and CANNOT fit 64GB VRAM -> adopting it PERMANENTLY
  CLOSES the role's best upgrade path. That is a capability regression, not a trade.

## PR #25731 — REJECTED UPSTREAM IN CURRENT FORM
- OPEN, isDraft TRUE, mergedAt null, REVIEW_REQUIRED. 4078 additions / 63 files. Updated 2026-08-03.
- pwilkin (MEMBER): "far too much sketchy CUDA stuff to get merged like that... what are those
  constants... Need a clear CPU version first, then we can add CUDA kernels - you can keep a fork"
- ngxson (COLLABORATOR): demands split into FOUR PRs (chat parser / text model / audio+vision / ggml)
- author conceded: "I probs should have not pressed 'Ready for Review'"
- **MTP IS EXPLICITLY STRIPPED**: conversion/inkling.py `_SKIP_PREFIXES` includes "model.mtp."
  and filter_tensors() returns None. MTP weights never reach the GGUF.
  => intake-955's "self-speculation available" is OVERTURNED *for the llama.cpp path*.
- Adds new global op GGML_OP_FLASH_ATTN_EXT_BANDED (GGML_OP_COUNT->102, RPC protocol bump)
- CPU reference DOES exist, but fast path gated on: flash_attn && head_dim in {64,128} &&
  KV cache type in {F32,F16,BF16}. Author: "get_n_kv_pos_contiguous() is 0 for multi-sequence ubatches."
  => fast path OFF for: multi-slot serving (our ConcurrencyAwareBackend), quantized KV, and -fa 0
  (llama-bench default). Fallback materializes a dense per-layer bias across 42 layers.

## INDEPENDENT NEGATIVE PERFORMANCE EVIDENCE (strongest datum in the dive)
jaholmesuk, 8xA100, in-thread 2026-07-19:
- inkling UD-Q4_K_XL **6.45 t/s** vs GLM-5.2-744B **24.0 t/s** on identical boxes (~25%)
- "All 8 GPUs sit at 0 to 6 percent utilization", **graphs reused = 0** every request,
  graph nodes 8985, graph splits 23; GGML_CUDA_DISABLE_GRAPHS=1 changed nothing
- diagnosis: "a ~9k-node graph rebuilt, re-split, re-allocated, re-serialized and launched
  node by node every token while the GPUs idle... banded rel-bias / shortconv path defeats
  llama-side graph reuse"
This is third-party measurement, NOT vendor restatement, and corroborates the fallback concern.

## CLAIM CORRECTIONS
- **77.6% and 80.2% are TWO DIFFERENT MODELS.** Inkling-Small = 80.2 SWE-bench Verified;
  975B flagship = 77.6. Small BEATS the flagship. Stage 1 filed these as one range.
- Retention ladder is **"Top-1% Retained (Accuracy Recovery)"** - a top-1 token-agreement
  recovery metric vs BF16, NOT a benchmark - and measured on the **975B flagship, not Small**.
  1-bit is a RANGE 74.2-77.4%, not a point. Cannot be applied to Inkling-Small at all.
- Retention table is on the DOCS page (941), NOT the GGUF repo page (942). Stage-1 mis-sourcing.
- 942 advertises `llama serve -hf ...` with NO mention of the required unmerged PR - source defect.
- Context DISPUTED: config.json 1048576 vs Artificial Analysis 256K for Small. Do not file 1M.
- Add UD-IQ1_S 74.8GB / UD-IQ1_M 78.8GB - the only quants leaving real headroom, and IQ1 is
  STUBBED in our GGML_IQK build. MXFP4_MOE 158GB.
- UD-Q4_K_M 163GB EXCEEDS 158GB free.

## AUP — FETCHED (Stage 1 never did). NOT A BLOCKER.
- Binding independently of Apache-2.0: "By accessing, downloading, or using any Model Materials,
  you agree to be bound by this Model AUP". Separate doc, not incorporated by reference.
- Behavioural prohibitions only (illegal use, child safety, weapons, automated consequential
  decisions, surveillance, fraud, unlicensed professional practice).
- NO restriction on commercial use, self-hosting, redistribution, fine-tuning. No termination clause.
- Entry should read "Apache-2.0 + binding behavioural AUP", not bare Apache-2.0.

## THE ONE FAVOURABLE FINDING
`sliding_window_size: 512` with local_layer_ids covering **35 of 42 layers** - only 7 global
attention layers. KV-cache cost far lower than 276B implies. Transferable signal for long-context
candidates generally.

## THIRD-PARTY QUALITY EVIDENCE (genuinely independent)
Artificial Analysis: Inkling-Small Index **40** (flagship 41, DeepSeek V4 Flash 40,
MiniMax-M3 44 @23B active, GLM-5.2 51 @40B active); AA-Briefcase 917 Elo vs flagship 839;
~24K output tokens/task (terse vs DeepSeek V4 Flash ~45K).

## ENTRY DISPOSITIONS
941 dive-verified w/ corrections; 942 dive-verified w/ corrections; 955 dive-verified w/ corrections.
(No entry fully overturned; several load-bearing specifics corrected.)

## LEDGER (8 rows)
1 worker_general adopt -> DECLINE (speed axis failed outright)
2 architect_critic adopt -> DECLINE NOW, re-examine on upstream merge
3 watch PR #25731 for split+merged text PR -> TASK, inference-acceleration-index.md
4 port arch ourselves -> DECLINE (4078 lines/63 files, rejected upstream, unresolved magic constants)
5 download weights to bench -> DECLINE (no quant both affordable and useful; nothing runs on frozen kernel)
6 consider 975B flagship -> DECLINE (270GB vs 158GB free; also scores LOWER than Small)
7 record SWA 35/42 KV pattern -> TASK, inference-acceleration-index.md
8 add "does arch defeat llama.cpp graph reuse?" to novel-arch intake screen -> TASK,
  deepseek-v4-flash-cpu-port.md  <- most reusable output of the dive

## PROCESS NOTE
architect_critic is NOT defined in stack_templates/default.yaml (only a comment references it).
Confirmed correct via contention_matrix.yaml / interaction_skills.yaml / progress 2026-08-01.
Matches a known open gap at numa-topology-cutover-resume-20260730.md:1034. Flagging only.
