# Stage-1 collected results — 2026-08-03 batch (candidate intake-938..946)

Dedup sweep: unbounded over 937 entries (937 arxiv_id, 937 url) + whole-file mention check.
ZERO collisions for all 9 sources. `duplicate` forbidden for every entry in this batch.
Submitted URLs = 10, but `2607.25970` appeared twice → **9 unique sources**.

## PARENT-VERIFIED FACTS (checked by me, not by agents)

- **arXiv title verification** (independent, via arxiv.org/abs): all three IDs map to the titles the
  agents reported. 2607.28568 = Frontis-MA1; 2607.25970 = Reinforcement Learning for Code Optimization;
  2607.28272 = MemHarness. **No cross-contamination** despite the scratchpad filename collision below.
- **Scratchpad collision**: sibling agents wrote to a generically-named `scratchpad/paper.txt`. The
  Frontis agent caught it, re-extracted to a unique filename, and verified provenance (149 "Frontis"
  hits) before reading. Combined with the title check above, no result is contaminated. Process fix for
  future runs: mandate unique scratchpad filenames in the dispatch prompt.
- **STORAGE — CROSS-AGENT CONTRADICTION, RESOLVED AGAINST THE GGUF AGENT.**
  `df -h /mnt/raid0` → **3.7T size, 3.4T used, 159G AVAIL, 96% used**. `/mnt/raid0` and `/` are the same
  device (st_dev 45); `/mnt/raid0/llm/models` alone is 2.3T.
  The Inkling-Small-GGUF agent wrote "storage is a non-issue (largest realistic candidate 82-163 GB
  against 3.7 TB raid0)" — it reasoned from TOTAL capacity, not FREE space. **That is wrong.**
  The Inkling-docs agent was right. Consequences:
  - UD-IQ2_M (82.44 GB) fits.
  - UD-Q3_K_XL (119.55 GB) / UD-IQ4_XS (127.41 GB) fit, tightly.
  - **UD-Q4_K_M (162.54 GB) does NOT fit** → the proposed "UD-IQ2_M + UD-Q4_K_M quant-control arm"
    is not currently runnable without a reclamation pass.
  - **Inkling-975B UD-IQ1_S (270 GB) does NOT fit.**

---

## intake-938 candidate — arXiv 2607.28272 — MemHarness: Memory Is Reconstructed, Not Replayed
paper · memory_augmented, agent_architecture, training_distillation, context_management
novelty **medium** · relevance **medium** · credibility **3** · verdict **adopt_patterns**
Shanghai AI Lab + ZJU/Fudan/SJTU/ANU/USTC. Submitted 2026-07-30.

Agent self-caught a fabrication: the HTML render's reference list carried 2303.11366 (Reflexion) and
2210.03629 (ReAct), present nowhere in the PDF. Removed; all figures re-derived via `pdftotext`.

- Retrieve → **critique/reconstruct against current state** → act, in ONE policy. Reconstruction ability
  emerges from GRPO, not supervision. Explicit `<EMPTY>` rejection path.
- ALFWorld 85.2% vs GRPO 76.4% vs RL+Raw-Memory 70.1%. WebShop 75.6 vs 66.1.
- **Mem0+GRPO 52.0 / SimpleMem+GRPO 54.5 — both far BELOW plain GRPO 76.4.** Naive memory injection is
  actively harmful, not neutral.
- **Latent guidance**: memory-free ablation 83.0 still beats RL-only 76.4 → memory as a TRAINING-TIME
  scaffold discardable at serve time = zero inference-path cost. Best fit for a frozen-kernel stack.
- CAVEAT: gradient-free viability NOT established. The generic-LLM reconstruction arm keeps the
  GRPO-trained actor; on WebShop it (71.8) scores BELOW raw-memory injection (72.6).
- ⚠ **DISAMBIGUATION REQUIRED**: intake-698 is "Memory is Reconstructed, Not **Retrieved**"
  (2606.06036, Ji/Li/Hooi, graph memory, LoCoMo/LongMemEval). One word apart, genuinely distinct.
- handoffs: unified-trace-memory-service, engram-conditional-memory, delta-mem-reproduction,
  skillbank-distillation, harness-selection-and-integration, agent-collab-rnd-harness,
  minddr-deep-research-mode, frontier-f4-continuity-backup, orchestrator-conversation-management,
  autopilot-continuous-optimization
- intakes: 698, 930, 935, 899, 936, 089, 346, 612, 613, 135, 265, 326
- DIVE: is reconstruction reachable WITHOUT RL? (cold-start vs GRPO ckpt isolates it) · read the actual
  prompts + `<EMPTY>` criterion · per-step token overhead (unreported) · ALFWorld/WebShop polarity flip vs 935.

## intake-939 candidate — arXiv 2607.25970 — Reinforcement Learning for Code Optimization
paper · benchmark_methodology, training_distillation, autonomous_research
novelty **high** · relevance **high** · credibility **4** · verdict **adopt_patterns**
FAIR/Meta + Inria (Chambon, Zheng, Decugis, Sagot, Synnaeve — the CWM / BigO(Bench) group).

**The value here is measurement engineering, not RL.** We cannot run the training (8-32 H100 nodes/run).

- **Naive runtime reward does essentially nothing** (+0.6 pts at p30) — the failure is reward/measurement
  plumbing, not the idea.
- **Timing on the machines doing the work is unusable**: moves ranking by **41.2 pp**; and it is NOT
  recoverable — post-hoc regression onto isolated timings gives **negative cross-validated R² over
  36,660 pairs**. A contended measurement is not a measurement.
- **Affine drift correction against a stored reference pool** raises stored-vs-fresh Spearman 0.54 → 0.96.
- **Duration-filterability gate**: robust CV (IQR/median) ≥ 0.3. Original tests pass for ≤3.8% of
  problems; purpose-built optimization tests reach 48.2%.
- **Table 3 = first ablated, quantified evidence for lexicographic fitness**: additive blend of
  correctness+speed costs **7.8 pass@1 pts** (46.9→39.1); pure-speed objective **collapses the policy to
  0.0** on all four percentiles. Our `autokernel-research-loop.md` / `mi210-kernel-rnd-loop-proposal.md`
  assert this rule from scar tissue; this is external, ablated confirmation.
- **Binary > bucketed > continuous** — discretization filters measurement noise before the gradient.
- **Offline replay simulator** screens reward designs on 1 CPU × minutes instead of 8-32 GPU-nodes × days;
  predictive diagnostics are ordering-related (monotonicity, steepness), NOT noise (rs=-0.002).
- Emergent **harness-stripping** reward hack: models delete class wrappers / method dispatch / "unused
  interface structure" — slow at runtime, load-bearing for the harness. Our C6 checks don't look for this.
- Headline gains: p50 18.0→31.3 (Qwen 7B), 30.7→50.4 (CWM 32B); p30 13.7→30.9 (+125%).
- Known inconsistency: abstract says 14% vs 28% complexity-class; body+conclusion say 13% vs 22%.
- handoffs: autokernel-research-loop, rocm-verify-profile-backend, agentic-rocm-kernel-authoring,
  mi210-kernel-rnd-loop-proposal, agent-collab-rnd-harness, architect-model-selection-bench,
  eval-tower-verification, safetygate-rlvr-provenance-audit-2026-07-22, meta-harness-optimization
- intakes: 660, 661, 664, 666, 667, 674, 677, 678, 874, 875, 370, 403, 571
- **GAP FOUND**: compendium has deep coverage of GRPO-as-algorithm and speedup-rewarded GPU *kernel*
  generation, and **ZERO** coverage of code-runtime-efficiency as a model capability. Afterburner
  (2505.23387), SWE-fficiency (2511.06090), SWE-Perf (2507.12415), PIE (2302.07867), EffiBench-X
  (2505.13004), COFFE (2502.02827) are ALL absent from 937 entries.
- DIVE: artifact release/license (decides adopt_patterns vs adopt_component) · Appendices A + C as a
  standalone measurement-methodology reference · the 14/28 vs 13/22 conflict · does affine correction
  survive translation to GPU kernel timing · unexplained Table 4 p100 48.2 vs 54.8 regression.

## intake-940 candidate — arXiv 2607.28568 — Frontis-MA1 (AI4AI / recursive self-improvement)
paper · autonomous_research, agent_architecture, context_management, training_distillation, benchmark_methodology
novelty **high** · relevance **high** · credibility **1** · verdict **adopt_patterns**
Horizon Research / Frontis.AI + Tsinghua (Ning Ding, Bowen Zhou) + ZJU/SJTU/GaTech. 2026-07-30.

- Trains the **improver itself**: four atomic program-evolution operators (Draft, Improve, Debug,
  Crossover) are the shared interface between post-training and inference-time search.
- First indexed entry where the *variation operator* is the object of gradient-based post-training —
  our whole evolutionary cluster (DGM 772, ShinkaEvolve 779, "Evolve the Harness" 753, ML-Master 413)
  is train-free.
- MLE-Bench Lite Medal Avg 39.39 → 60.61 (model swap, harness fixed); 71.21 with Evo-Max.
- Clean 2×2: fix harness/swap model AND fix model/swap harness, on two independent benchmarks.
- **Three-factor non-greedy parent selection** (quality / progress-gain / novelty, 1.0/0.6/0.3).
- **Operator-conditioned on-demand memory synthesis** (vertical=ancestor, horizontal=sibling) with
  **explicit negative-evidence marking** so known failures aren't re-serialized into child context.
  −41.7% total tokens, −50.3% prompt tokens, **+84.3% new-best-per-1M-tokens**. Improve-prompt p99
  389.0K → 54.3K chars (−86.1%) — the win is concentrated in the tail.
- Pre-execution LLM-judge reward-hack gate (reward −0.5, skip sandbox).
- Whole eval ran at 12 h/task on **ONE RTX 4090 capped at 12 GB VRAM** — a smaller envelope than an MI210.
- **credibility 1**: vendor tech report whose headline is beating GPT-5.5+Codex; zero independent
  replication found. Run-to-run std is **±7.73–8.57%**, so the 3.03pp margin over GPT-5.5 is almost
  certainly not separable (references run once each).
- handoffs: autopilot-continuous-optimization, meta-harness-optimization (+completed variant),
  context-folding-progressive (completed variant), autokernel-research-loop
- intakes: 772, 413, 753, 779, 780, 781, 720, 148, 886, 898, 117
- DIVE: are weights actually downloadable + GGUF-convertible under frozen v8 · Appendix C.4 selector
  hyperparameters · does the 21.22pp gain survive ±7.73% std · Appendix B.4 async-rollout study ·
  can OpenMLE-Gym wrap OUR tasks (kernel search, autopilot configs) not just Kaggle-shaped ones.

## intake-941 candidate — unsloth.ai/docs/models/inkling
blog (vendor docs = the announcement post; `/blog/inkling` is 404 and the blog index links to /docs/models/*)
novelty **high** · relevance **high** · credibility **1** · verdict **worth_investigating**

- **Inkling = open-weight multimodal MoE family from Thinking Machines Labs.** 975B-total/41B-active
  flagship + 276B-total/12B-active Small. Text+image+audio in, text out. **Apache-2.0**, 1M context.
- **llama.cpp support is an UN-MERGED DRAFT PR (#25731)**, authored by Unsloth's own founder
  (danielhanchen) — so not independent validation of arch maturity. Against FROZEN
  production-consolidated-v8 this is the most expensive class of intake outcome.
- PR-reported arch (NOT on the assigned page): 55 sliding-window + 11 global layers, **banded
  content-dependent relative position bias INSTEAD of RoPE**, per-layer short conv state, 256 experts
  (top-6 + 2 shared), vision + audio. Non-RoPE position bias and per-layer conv state both touch code
  paths v8 does not have.
- Vendor accuracy-retention ladder: 1-bit 74.2–77.4%, 2-bit 81.0%, 3-bit 88.7%, 4-bit 94.4%, 6/8-bit
  99.8%. **METRIC UNDEFINED** — the page never names the benchmark or task.
- Claimed SWEBench-Verified 77.6%; HLE text 29.7%; AIME 2026 97.1%; GPQA-D 87.2%. Scores dated Jul 14 2026.
- `reasoning_effort` is a **continuous 0.00–0.99 knob** — finer-grained than our binary `enable_thinking`.
- handoffs: tq3-quantization-evaluation, architect-model-selection-bench, large-moe-expert-parallelism,
  multimodal-pipeline, glm51-reap-cpu-evaluation, llama-cpp-dsa-contribution, laguna-s21-cpu-port,
  deepseek-v4-flash-cpu-port, reasoning-compression
- intakes: 699, 871, 870, 880, 279, 281, 739, 694, 654, 325, 320, 682, 391, 721, 722, 723
- NOTE: `reasoning-compression.md:473` cites "Thinking Machines Lab analysis" — that is their RESEARCH
  BLOG on on-policy distillation, a different artifact. NOT prior coverage of Inkling.
- DIVE: target PR #25731 and the model's technical report, NOT this page (page is a run-guide with no
  architecture section, no release date, no throughput, no methodology for its accuracy numbers).

## intake-942 candidate — huggingface.co/unsloth/Inkling-Small-GGUF
repo · quantization, moe_optimization, local_inference, inference_serving, multimodal
novelty **high** · relevance **high** · credibility **null** · verdict **worth_investigating**

- **HARD GATE, VERIFIED LOCALLY BY THE AGENT** (read-only grep of the frozen tree): GGUF declares
  `general.architecture = inkling`; `/mnt/raid0/llm/llama.cpp` @ `production-consolidated-v8` has 138
  `LLM_ARCH_*` entries ending at `DFLASH` — **no `LLM_ARCH_INKLING`** anywhere in llama-arch.h/.cpp,
  src/, convert_hf_to_gguf.py, or gguf-py. **None of these 115 files load on production today.**
- Arch: 42 layers, 6-of-256 routed + 2 shared experts, hybrid local/global attention, 276B/12B-active.
- **Full quant ladder enumerated from the HF tree API** (115 files, 23 quant dirs, 3.32 TB repo):
  UD-IQ1_S 74.77 · UD-IQ1_M 78.83 · UD-IQ2_XXS 82.29 · **UD-IQ2_M 82.44** · UD-Q2_K_XL 87.94 ·
  UD-IQ3_XXS 97.93 · UD-IQ3_S 107.46 · UD-Q3_K_M 119.35 · UD-Q3_K_XL 119.55 · UD-IQ4_XS 127.41 ·
  UD-IQ4_NL 130.09 · UD-Q4_K_S 152.34 · MXFP4_MOE 158.04 · UD-Q4_K_M 162.54 · UD-Q4_K_XL 163.27 ·
  UD-Q5_K_S 184.21 · UD-Q5_K_M 196.09 · UD-Q5_K_XL 196.66 · UD-Q6_K 218.91 · UD-Q6_K_XL 239.71 ·
  Q8_0 280.28 · UD-Q8_K_XL 288.42 · BF16 527.41 GB. Plus mmproj-{F32,F16,BF16}. **No imatrix published.**
- **IQ1-stub is NOT the blocker** — the full IQ2/IQ3/IQ4_XS/K ladder is offered, so IQ1 can be avoided.
- **No GPU-resident arm exists**: smallest file 74.77 GB > MI210's 64 GB HBM. Offload/hot-expert only.
- **No draft/EAGLE/MTP artifact** in any of the 115 files → no spec-dec partner in this repo.
- **Chat-template risk**: 22,680-char recursive Jinja using `dictsort(case_sensitive=true)`,
  `tojson(ensure_ascii=false, separators=...)`, `namespace()`, and a hand-rolled JSON whitespace scanner.
  Whether minja executes it correctly is open and is a plausible silent-wrong-output source.
- **Odd metadata**: `bos_token == eos_token == <|content_model_end_sampling|>`. Confirm intentional.
- Eval table is copied verbatim from the base card, measures **BF16**, vendor self-report, no harness.
  SimpleQA Verified 20.6% is the standout weakness (vs DeepSeek V4 Flash 34.1%).
- ⚠ **PARENT CORRECTION**: agent's "storage is a non-issue" is WRONG — only **159 GB free**. UD-Q4_K_M
  (162.54 GB) does NOT fit; the proposed IQ2+Q4 two-arm design needs reclamation first.
- handoffs: architect-model-selection-bench, laguna-s21-cpu-port, deepseek-v4-flash-cpu-port,
  tq3-quantization-evaluation, iqk-iquant-enablement, cpu-prefill-compute-large-models,
  glm52-reviewer-capability-gates, glm51-reap-cpu-evaluation, multimodal-pipeline,
  mi210-big-model-and-acceleration-roadmap, speculative-decoding-mtp-refresh,
  inference-acceleration-index, llama-cpp-upstream-rebase (completed)
- intakes: 699, 880, 879, 391, 682, 279, 281, 328, 861, 870, 871, 325, 654
- DIVE (3 questions, all desk-verifiable, no download, no inference): (1) is `inkling` merged upstream
  and does the merge include mmproj/audio · (2) routed-expert tensor types in UD-IQ2_M via shard-header
  parse (intake-870 method) → decides whether iqk reaches the decode-dominant bytes · (3) does minja
  render the 22.7 KB template.

## intake-943 candidate — engineering.block.xyz/blog/codecrucible-a-blueprint-for-llm-driven-sast
blog · agent_architecture, tool_implementation, context_management, cost_aware_routing, benchmark_methodology
novelty **medium** · relevance **high** · credibility **4** · verdict **adopt_patterns**
Block, Inc. (Carpene, Rosenzweig, Kitis; +Stanton). Published 2026-07.

- **Inverts the standard architecture**: LLM as PRIMARY analyzer over whole-repo concatenation, not a
  validator of CodeQL/Semgrep nominations. Snippet-anchored systems are recall-capped by the upstream engine.
- Pipeline: scope/filter → **pre-model budget gate** (`--dry-run`, `--max-cost` BEFORE any model call) →
  overhead/chunk budget → conditional cheap feature-detection pass (buys budget for the expensive pass) →
  chunking (fallback only, never slices files) → open-ended discovery → **deterministic dedup** →
  LLM audit → SARIF rebuild.
- **FP control is the transferable part**: asymmetric two-pass (generous first, precision-tuned second);
  auditor primed with an **over-reporting prior** + four obligations (prove reachability, prove no
  mitigation, collapse duplicates to root cause, prove production reachability first when tests excluded);
  **deterministic dedup keyed by (location, CWE) keeping highest severity, ordered BEFORE the LLM audit**;
  generic "please validate" prompts explicitly rejected in favor of CWE-specific injected guidance.
- **NEGATIVE RESULT**: heavy prompt scaffolding did NOT materially beat a short Carlini-style CTF prompt;
  the short one was cheaper and faster. **No numbers given** — not citable as evidence.
- **NO precision/recall/FP-rate published for its own tool, on any corpus.** The one reproducible datum is
  n=1 (Copy Fail, $9 / 7 min) which **FAILED unaided** and only partially succeeded once handed the
  answer-shaped operator steer.
- Open source **Apache-2.0**, verified live: github.com/block/codecrucible (Go, 105 stars) AND
  **github.com/block/benchmrk** — "a harness for measuring whether static analysis security tools actually
  find the bugs". benchmrk is the highest-value surfaced artifact.
- Models used: GPT 5.5 Cyber + Claude Opus 4.7 via `--provider databricks`. **No local/self-hosted model
  named anywhere**; whether the provider layer accepts an OpenAI-compatible base URL is unverified and
  decides adopt_patterns vs adopt_component.
- Our `/workspace/.claude/skills/security-review/SKILL.md` ALREADY has the two-pass + eight gates (from
  intake-658). **Net-new deltas**: (a) dedup stage — we have none at all, (b) (location,CWE) keying,
  (c) hard pre-model cost gate, (d) cheap-gate-buys-budget pattern.
- **Design disagreement worth flagging**: our skill suppresses at emission ("do not output generic
  checklist results"); they run a deliberately generous first pass and suppress in a separate call.
- **Counterweight — intake-836**: LLM code reviewers over-correct, false-reject exceeding false-accept
  3×–440×. CodeCrucible tunes hard for precision with **zero FR measurement** — exactly the exposure H4's
  symmetric FA/FR e-processes exist to catch.
- Source citation error to not propagate: the post calls arXiv:2402.13291 "Snyk's CodeReduce paper"; that
  ID is *DeepCode AI Fix* — CodeReduce is a technique inside it.
- handoffs: security-review-skill, reviewer-control-plane-index, reviewer-decision-plane,
  reviewer-calibration-accounting, reviewer-typed-artifacts, reviewer-escalation-and-human-gate-policy,
  eval-tower-verification, scoring-infra-standardization, repo-readiness-scorer,
  privacy-hygiene-precommit-hooks, hermes-outer-shell
- intakes: 658, 836, 834, 843, 875, 845, 330, 900, 736, 657
- SAST/CodeQL/Semgrep/SARIF/CWE genuinely absent from the corpus (3 incidental hits, all unrelated).
- DIVE: the REPO not the post (post fully extracted) — provider base-URL support · the three shipped
  prompt sets incl. CWE-specific audit guidance · `scan_audit.go` confidence thresholds · benchmrk as an
  executable ground-truthed corpus for reviewer-calibration-accounting v1.

## intake-944 candidate — github.com/QuixiAI/QuixiCore
repo · hardware_optimization, quantization, benchmark_methodology, local_inference, agent_architecture
novelty **medium** · relevance **high** · credibility **null** · verdict **worth_investigating**

- **NOT an agent framework/orchestrator/inference engine** — a 92 KB, 4-week-old, single-author
  (Eric Hartford / `ehartford`), MIT **kernel-contract + conformance-registry** repo for six
  separately-hosted native backends (CUDA, Metal, ROCm, XPU, Gaudi, CPU). Zero kernel code.
- The two backends that matter are **forks of HazyResearch/ThunderKittens (CUDA) and HipKittens (ROCm)**.
- **ROCm column is 🚧 on all 16 kernel families and explicitly CDNA3-scoped — we are CDNA2/gfx90a.**
  QuixiCore-CPU ships with **license: null** (no license at all) and is validated on Apple AArch64 +
  Intel Sapphire Rapids, **never AMD Zen5**. Not adoptable today on either count.
- Created 2026-07-05, last push 2026-08-02, ~18-20 commits, 37 stars, 13 open issues, ONE contributor.
  Credibility basis: git shortlog + CI presence + API metadata, NOT README prose. Real CI on conformance
  vectors; commit messages specific and non-marketing.
- **Two locally falsifiable GGUF claims** (zero inference, read-only source inspection of our own tree):
  (1) E8M0 code 255 yields `+Inf` in GGUF vs `NaN` in MX formats, because ggml "reconstructs the scale by
  bit-punning the code into the fp32 exponent field with no special cases";
  (2) IQ2_XXS decode = "four dependent random reads of a 256-entry grid plus a sign-table read".
- `AGENTS.md` imposes an independent perf gate on AI contributors (hardware, driver, command line, git
  commit, warmups, iterations, median, variance, explicit keep/reject) — **convergent with MEASUREMENT.md**;
  cite as external corroboration, adopt nothing verbatim.
- reported_results: **NOT-FOUND-IN-SOURCE** — no benchmarks, speedups, or accuracy figures anywhere.
- **THE ACTUAL FIND IS A CROSS-REFERENCE**: `HazyResearch/HipKittens` (MIT, 448 stars, AMD tile
  primitives) appears **NOWHERE** in the 937-entry index, handoffs, docs, or research tree — and it is on
  the critical path of ten active MI210/kernel handoffs. "ThunderKittens" appears only twice, both as
  passing mentions inside other entries.
- handoffs (all ACTIVE, zero in completed/): agentic-rocm-kernel-authoring, rocm-verify-profile-backend,
  gpu-acceleration-path, mi210-mfma-compute-bound-paths, mi210-q8-dequant-gemv-roofline,
  cpu-shape-specialized-gemv-decode, k28-fused-chunked-gdn-kernel-research,
  gemma-challenge-kernel-techniques-v7, gpu-drafter-mi200-investigation,
  mi210-big-model-and-acceleration-roadmap
- intakes: 664, 667, 674, 675, 677, 678, 679, 307, 497, 447, 191, 194
- ehartford ↔ Dolphin/cognitivecomputations is **PROBABLE BUT UNCONFIRMED** (login + commit author name
  only; org states no affiliation).
- DIVE: **dive HipKittens, not QuixiCore.** The umbrella would exhaust quickly. Spend ~20 min verifying
  the two GGUF claims against our own tree.

## intake-945 candidate — www.eschalabs.com
blog (org homepage) · quantization, moe_optimization, inference_serving, local_inference, hardware_optimization
novelty **medium** · relevance **high** · credibility **null** · verdict **worth_investigating**

- Homepage is a **single tagline behind a JS shell** — "Escha Labs, The LLM Compression Company".
  `/about` and `/blog` both **404**. Near-zero extractable content.
- Commercial entity ("Escha Labs Inc."), HF org type Company, 11 team members. **No founders, no
  investors, no funding, no pricing, no API found** across targeted searches.
- Two artifacts only, both ~4 days old (first release ~2026-07-30): the W2 model and
  `EschaLabs/escha-runtime-qwen3moe` (Apache-2.0 runtime).
- **Runtime is NVIDIA-ONLY** (CC 8.0–12.0, Ampere–Blackwell), Linux x86-64, on **proprietary Escha CUDA
  kernels**, via an SGLang fork (multi-user) or ZML (single-stream). **No GGUF, no llama.cpp, no ROCm, no
  CPU path.** Our GPU is gfx90a. Structurally foreclosed.
- **publishes_methodology: false** — the recipe is marketing prose ("model-aware fine tuning and
  recovery"). No paper, no quantizer source, no datasets. There is no pattern to extract, only an
  outcome to verify — which is why this is `worth_investigating` and NOT `adopt_patterns`.
- **Why relevance is HIGH anyway**: they compressed **Qwen3.6-35B-A3B — our production frontdoor model**
  — to 2-bit. That lands directly on the active `tq3-quantization-evaluation.md` /
  `angelslim-techniques-evaluation.md` sub-2-bit monitor line, where our own candidates are
  **quality-blocked by an explicit 2026-07-19 stop-list** whose reopen criterion is "a *specific* quality path".
- **Sharpest connection**: `angelslim-techniques-evaluation.md` states our sub-2-bit adoption is gated on
  "somebody releasing Sherry-QAT'd checkpoints of a base model we actually run". Escha is that somebody
  and that is that model — **but they shipped it in a proprietary format, so the gate does not open.**
  That is a risk the handoff's plan does not currently account for.
- Same foreclosure pattern as **intake-3413 (DFlash)** — filed consistently.
- Open MoE-specific question: tq3 warns rotation-based methods "shatter MoE sparse routing (~367K ghost
  activations)". Escha is a 256-expert MoE; how routing fidelity is preserved is unanswered.
- handoffs: tq3-quantization-evaluation, angelslim-techniques-evaluation, qwen36-27b-cpu-feasibility,
  architect-model-selection-bench, glm51-reap-cpu-evaluation, gpu-serving-tie-in-program,
  mi210-big-model-and-acceleration-roadmap, inference-acceleration-index, kv-cache-quantization
- intakes: 387, 391, 590, 591, 593, 594, 166, 182, 461
- Explicit NON-tie-in: `gpu-serving-tie-in-program.md` is a llama.cpp/GGUF gfx90a slot — orthogonal to an
  NVIDIA-CUDA runtime. Noted to prevent a false linkage.
- DIVE: **agent recommends AGAINST diving this URL** — exhausted; the remaining org questions are
  unpublished, not merely unfetched. Higher value: the runtime repo (is W2 portable to ggml, or welded to
  CUDA primitives?) and the model card's discussions tab.
- Recommends **zero bench time** — nothing is runnable on our hardware.

## intake-946 candidate — huggingface.co/EschaLabs/Qwen3.6-35B-A3B-Escha-W2
STILL RUNNING at time of writing.
