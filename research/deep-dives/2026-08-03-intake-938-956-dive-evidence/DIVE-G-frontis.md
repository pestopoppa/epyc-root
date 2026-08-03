# DIVE-G — intake-940 Frontis-MA1 -> dive-verified (verdict adopt_patterns HOLDS, credibility 1 HOLDS)

## THE STATISTICAL RECONSTRUCTION (the dive's core contribution)
Every `mean +- SD` row in Table 9 admits EXACTLY ONE integer medal-count triple out of 22. Agent
brute-forced all triples in [0,22]^3 against sample-SD (ddof=1) and population-SD (ddof=0) at +-0.02
and +-0.10pp. Every row resolved UNIQUELY, always under **population-SD**; sample-SD is EXCLUDED.
| Arm                          | Reported      | Reconstructed per-run |
| Frontis-MA1-35B + Evo-Max    | 71.21 +-8.57  | **59.09 / 77.27 / 77.27** |
| Frontis-MA1-35B + Evo        | 60.61 +-7.73  | 50.00 / 63.64 / 68.18 |
| Qwen3.6-35B-A3B + Evo (ctrl) | 39.39 +-5.67  | 31.82 / 40.91 / 45.45 |
| Frontis-MA1-30B + Evo        | 53.03 +-4.29  | 50.00 / 50.00 / 59.09 |
| Qwen3-30B-Thinking + Evo     | 34.85 +-2.14  | 31.82 / 36.36 / 36.36 |
=> **ONE OF THE THREE HEADLINE RUNS SCORED 59.09% — BELOW the 68.18% it claims to beat**, and below
Claude Opus 4.8 (63.64) and Gemini 3.5 Flash (63.64) from the same panel.
=> The paper's +- **UNDERSTATES DISPERSION BY 22.5%** vs the unbiased sample SD (7.73 -> 9.46).
=> The official openai/mle-bench leaderboard reports **SEM, not SD** (verified: recurring +-1.52 = SEM of
   a 3-seed 22-task run). Restated in the leaderboard's own convention: **71.21 +- 6.06 SEM** against a
   board where typical entries sit at **+-1.52**. Their runs are ~4x LESS REPRODUCIBLE than typical.

## SUPPORTED (exactly one scientific claim)
**Execution-grounded post-training improves an MLE-search harness over its own frozen base model.**
- 35B 39.39 -> 60.61: COMPLETE RANK SEPARATION (all 3 treated > all 3 control). Exact one-sided
  permutation p = **0.05** — the FLOOR achievable at 3-vs-3; the design cannot produce stronger evidence.
  Welch t=3.13, df=3.67, p=0.040.
- 30B 34.85 -> 53.03: also complete rank separation, Welch p=0.013.
- Jointly, Fisher-combined **p ~= 0.018.** This is the one thing the paper establishes.
ALSO CREDIBLE (engineering, matched design, 66 task-runs/harness, same checkpoint+seed+12h budget):
tokens 129.3M->75.3M (-41.7%), prompt tokens -50.3%, Improve prompt mean 102.8K->35.7K chars,
**p99 389.0K->54.3K (-86.1%)**, Crossover p99 -81.3%. Single-configuration, no repeats, no dispersion.

## UNSUPPORTED
- **"Exceeds GPT-5.5+Codex by 3.03pp"** — baseline is **n=1, no error bar, SELF-RUN** (not on the
  official leaderboard). Margin = **exactly 2 medal outcomes out of 66 task-runs** (1/66 = 1.515pp)
  = **0.50 SEM**. Clopper-Pearson on the n=1 baseline [45.13, 86.14]; 95% CI on the 3-run mean
  [45.13, 97.29].
- Harness swap 53.03 -> 60.61: the AIRA-Evo row is **ABSENT FROM TABLE 9 ENTIRELY** — the only
  comparison in the paper with no dispersion. Welch p ~= 0.30 even granting the baseline zero variance.
  A PAIRED analysis over the 66 matched task-runs would be far more powerful; paired counts not reported.
- Evo -> Evo-Max on the same checkpoint: **p = 0.264**.
- ALL cross-vendor Evo comparisons: GLM-5.2 p=0.62, Kimi K2.6 p=0.43, Grok-4.5 p=0.50, MiniMax M3 p=0.81.
- **"+84.3% new-best per 1M tokens"** decomposes as 1.0742 (new-bests, +7.4%) x 1.7171 (token reduction,
  +71.7%). **88.3% of the log-ratio gain is the DENOMINATOR.** It restates the cost claim; it is not an
  independent yield result. DO NOT CARRY THIS FIGURE.
- NatureBench transfer, BOTH directions: n=10, no repeats, each task = 10pp. Model swap = a 2-TASK delta
  (best-case one-sided p=0.25); harness swap = 3 tasks (p=0.125). Neither reaches 0.05 under the most
  favourable possible pairing. Their own D.2 concedes it.
- "12 GPU-hours on one RTX 4090" for the 71.21% row: PARTIAL. Evo-Max "enables asynchronous multi-GPU
  parallel search"; shipped config has time_budget 43200 (12h sandbox) but
  model_plus_sandbox_time_budget **64800 (18h)**, and footnote 3 EXCLUDES model-inference cost. The 35B
  is served on separate accelerators via SGLang.
STRONGEST MICRO-EVIDENCE: Improve ops setting a new best 44/931 (4.73%) -> 72/769 (9.36%), unclustered
z=3.77 p=1.6e-4 — but clustered inside 22 tasks x 3 runs, so effective n is far smaller. Suggestive.

## FOUR OVERTURNS — THREE OF THEM OF MY OWN BRIEF'S PREMISES
1. **Appendix B.4 DOES quantify the async speedup: 1.91x** ("mean step time 97.0 min synchronous vs
   50.8 min asynchronous across 40 matched steps", task-balance CoVs 1.56%/2.06%). My brief said it
   declines to quantify. WRONG.
2. **Appendix C.4 does NOT contain the weight schedule or temperature.** It gives only functional forms.
   1.0/0.6/0.3 appears ONLY in Sec 6.5 case-study prose.
3. **The gym contract is NOT general.** It is `evaluate(y_true: DataFrame, y_pred: DataFrame) -> float`
   plus validate_submission, scoring a prediction file against data/private/test_answer.csv. **It cannot
   express a throughput-measurement task** — that would need the agent's own program to self-report
   throughput, precisely the surface B.6 exists to close.
4. **OpenMLE-Tasks ships ZERO BYTES OF TASK DATA**, while its README and docs/release.md both state
   1,415 tasks ship built data/public and data/private.

## THE ZERO-DATA FINDING (verified from the dataset's OWN integrity manifest)
checksums.sha256, 42,078 entries: **0 CSV/parquet/zip/npy, 0 paths under data/public or data/private.**
Extensions: .py 24,833 / .json 11,507 / .txt 5,730 / .md 4 / .jsonl 1.
task_index.jsonl has exactly 5,758 records (4,343 recipe / 1,415 built_task), **5,735 with EMPTY
download_url**, package_bytes summing to **608.6 GB of REBUILD cost** behind Kaggle auth and
per-competition rule acceptance.
Dataset README claims: "Ready-to-use Task packages | Built data/public, data/private, and runtime
scripts | 1,415" and "Each directory under tasks/ is already built." docs/release.md: "full task-package
data is released for 1,415 tasks." **All three are FALSE against the shipped manifest.**
Their own Appendix E gives ML-Agent a daggered tick + footnote for exactly this class of partial release.

## SELECTOR WEIGHTS: THE PAPER AND THE CODE DISAGREE
Released code (identical in OpenMLE-Evo/third_party/aira-evo/.../experience.py:10-15 and
OpenMLE-ERL/RL/airaevo_experience.py:29):
  DEFAULT_PARENT_UTILITY_WEIGHTS = {"score":1.0, "delta":0.4, "novelty":0.25,
                                    "official_score_missing_penalty":2.0}
**0.6 / 0.3 appear NOWHERE as selector weights.** Reconstructing the case study, 10.47%->17.09% is
consistent with lambda_delta ~= 0.6 (predicts ~17.6%) and NOT with the shipped 0.4 (predicts ~14.9%):
**the case study used an UNRELEASED configuration.**
Full spec: score = direction-aware min-max, ties->0.5; progress = max(0, s_i - s_i^parent) against the
STRONGEST parent, normalized by max delta, POSITIVE-ONLY (regressions get neither credit nor penalty);
novelty = 1/sqrt(1+N_f) over auto-detected method family; U = 1.0*s + 0.4*d + 0.25*v sampled by
softmax(U/tau) with **tau = 1.0 FIXED**. The 4th term is DEAD (hardcoded to 0.0 in the loop).
Selection uses SELF-VALIDATION only, with an in-code comment that using the sandbox/official score
"would leak test feedback into the search controller."
**Island structure is INACTIVE**: num_islands 1, migration_prob 0.0, initial_temp = final_temp = 1.0.
C.4's "for a sampled island I" describes machinery switched OFF in every released profile.
AUTHORS' OWN CAVEAT (6.5): "the end-to-end difference from original AIRA-Evo should not be attributed to
the three weights alone." **There is NO selector-only ablation anywhere in the paper.**

## "NEGATIVE-EVIDENCE MARKING" IS NARROWER THAN OUR ENTRY STATES
Not an exclusion filter, not a typed negative-evidence field. It is a **RENDERING DISCIPLINE**: a
deterministic error_signature per card + a board-level repeated_errors counter, rendered as a named
prompt line (repeated_errors_to_avoid in _build_crossover_experience_memory; current_error_signature +
repeated_errors + "Related previous debug/error memories" in _build_debug_experience_memory).
Failures STILL ENTER the context — as one compact typed line instead of raw prior-attempt text.

## ARTIFACTS ARE REAL AND BETTER THAN STAGE 1 ASSUMED
- Frontis-MA1-35B: **71.93 GB** BF16, 15 shards + model-vision-mtp.safetensors, UNGATED. 86 downloads.
- **Frontis-MA1-35B-GGUF: Q4_K_M 21.17 GB** + F16 mmproj 899 MB + SHA-256 manifest. Tested on
  llama.cpp b9637; our binary reports 10107 (newer). general.architecture = qwen35moe, 733 tensors,
  expert_count 256 / used 8, full_attention_interval 4, SSM keys present.
  **Does NOT publish an MTP draft variant** — the MTP head exists in the BF16 repo only.
- **LICENCE: CC BY-NC 4.0 (NON-COMMERCIAL)** on all four model repos + code + SFT corpus.
  WARNING: both GGUFs carry `general.license = apache-2.0` IN THE HEADER KV, contradicting the repo
  licence. Anything auto-extracting licence from GGUF metadata reads the WRONG ANSWER.
- OpenMLE-SFT-Traces: REAL, 26,259 rows / 220.9 MB, matches the claim. RL traces NOT released.
- **Evaluation sandbox NOT RELEASED** — client-only for /api/v1/jobs. Hard blocker for reproducing tables.
- Their own docs/validation.md: "**Neither validation independently reproduces paper tables.**"
- Full pull of all four model repos = 173.6 GB against 158 GB free.

## THE BASE MODEL IS OUR PRODUCTION FRONTDOOR, AND OUR FROZEN KERNEL ALREADY SUPPORTS IT
Base = Qwen/Qwen3.6-35B-A3B, Apache-2.0. Frontis-MA1-35B/config.json is SEMANTICALLY IDENTICAL to it
(zero differing keys). We hold Qwen3.6-35B-A3B-MTP-Q8_0.gguf on disk; it is our production frontdoor.
production-consolidated-v8 @ 67a433bf4 already carries src/models/qwen35moe.cpp (32,974 B),
conversion/qwen.py:628 registering Qwen3_5MoeForConditionalGeneration, LLAMA_VOCAB_PRE_TYPE_QWEN35 = 46,
LLM_KV_FULL_ATTENTION_INTERVAL, PROJECTOR_TYPE_QWEN3VL. **NO PR, NO EXPERIMENTAL BRANCH NEEDED.**
Architecture OVERTURNED as "plain Qwen3 MoE": it is a HYBRID SSM/ATTENTION MoE — 40 layers
(30x linear_attention + 10x full_attention, every 4th), hidden 2048, 256 experts/top-8, vocab 248,320,
max_pos 262,144, mtp_num_hidden_layers 1, plus a 27-layer SigLIP-style vision tower. Matches our
feedback_qwen35_27b_architecture.md note. "Qwen3.6" is a weights refresh on the 3.5 architecture.

## NO INDEPENDENT REPLICATION OR CRITIQUE EXISTS
25 search variants EN+ZH, HN Algolia (1 story, 2 pts, 0 comments), GitHub+HF APIs.
Repo: **0 issues open AND closed**, 0 PRs, discussions disabled, 0 watchers, 6 forks with ZERO
divergence, 18 commits from 2 author accounts. 0 HF discussions on all 4 model repos.
HF paper page 170 upvotes, 2 comments (one the author posting the abstract, one a bot).
All coverage is abstract restatement. Only hedge anywhere is aiweekly's: "all of this is self-reported,
single-paper, and measured on benchmarks the same team scoped."
**The official leaderboard has been FROZEN to new submissions since 2026-04-24 — no verification path
currently exists.**

## TABLE 11 IS NOT A COMPLETE LEADERBOARD AUDIT
Caption claims an audit "against the official MLE-Bench leaderboard as of July 2026" but OMITS
MARS+ (78.79), PiEvolve (80.30), LoongFlow (77.27), Disarray (90.91) — ALL ABOVE 71.21%.
Third-party numbers that ARE printed all match openai/mle-bench exactly (verified 8 of them).
Also: MiniMax M2.7 + Claude Code printed as 45.50%, which is NOT a multiple of 1/22 (10/22 = 45.45%).

## LEDGER: 4 drafts, 5 declines
1 parent-relative-gain term for the autopilot archive -> DRAFT AP-PS-1, autopilot-continuous-optimization.md
  (novelty already covered by diversity_coverage_penalty AP-35 done 2026-07-11; score by hypervolume/BT
  tiebreak; GAIN is the one factor with no analogue). Offline-replayable at ZERO inference.
2 typed failure evidence (error_signature + repeated_errors, rendered) -> DRAFT AP-PS-2, same handoff
3 operator-conditioned on-demand context assembly -> DRAFT CF-OD-1, context-folding-progressive.md rider
  (carry the p99 tail collapse; DO NOT carry the +84.3% yield figure)
4 pre-execution reward-hack gate -> DRAFT AK-RH-1, autokernel-research-loop.md (+ a
  trust_model_validation_score=false equivalent so self-reported timings never enter the record)
5 run MLE-Bench Lite locally -> DECLINE as scoped; RE-SCOPE to a 2-3 task smoke serving the 21GB Q4_K_M
  on CPU and leaving the MI210 as sandbox. (158 GB vs 158 GB free; 792 sandbox-GPU-hours; sandbox unreleased)
6 evaluate Frontis-MA1-35B-GGUF as a coding/architect candidate -> DECLINE FOR NOW, FLAG TO OPERATOR as
  the highest-leverage finding: a 21 GB Q4_K_M fine-tune of our own frontdoor model, loadable TODAY.
  BUT the card states the reported scores "measure the canonical model with the OpenMLE-Evo harness, NOT
  GGUF one-shot generation" — **there is NO published one-shot number at any precision.** Narrow-domain
  (Kaggle MLE program synthesis), NON-MTP in GGUF form (our frontdoor uses the MTP variant), CC BY-NC.
7 wrap our optimization tasks in OpenMLE-Gym -> DECLINE, contract mismatch SETTLED. What IS portable is
  the four-operator search LOOP, not the gym; the NatureBench adapter proves the runtime can be pointed
  at a foreign evaluator.
8 adopt the async-rollout speedup -> DECLINE, out of scope (RL rollout collection; we do no RL training)
9 CITATION RULE -> DRAFT, operator call. Only two claims may EVER be cited: (a) execution-grounded
  post-training improves an MLE harness over its own frozen base, 2/2 backbones, complete rank
  separation, joint p~=0.018; (b) operator-conditioned context assembly cuts prompt TAIL ~7x in a
  matched 66-task-run comparison. **Everything else, including "beats GPT-5.5+Codex", is UNSUPPORTED.**

## DIVE-SURFACED SOURCES (8)
- arXiv 2410.07095 MLE-Bench (ICLR 2025) — the authoritative contamination treatment (Dolos plagiarism
  detection, rule-violation logs, token-probability familiarity probe, obfuscated-description variant).
  Establishes that **strategy-level reuse is acknowledged as UNDETECTABLE** — exactly the channel
  Frontis's SHA-256 exact-string dedup cannot touch.
- arXiv 2511.09904 CTRL-ALT-DECEIT (NeurIPS 2025) — frontier agents SANDBAG and implant backdoors in MLE
  tasks; general monitors reach only 0.60 AUC. Qualifies ANY self-graded agentic MLE number.
- arXiv 2604.11806 "Finding Widespread Cheating on Popular Agent Benchmarks" — thousands of cheating runs
  across 28+ submissions on 9 benchmarks; likely cause of the 2026-04-24 leaderboard freeze.
- **github.com/InternScience/MLEvolve + arXiv 2606.11926 — 80.30% Lite at 12h on 1xH200, SOURCE
  AVAILABLE. The ACTUAL efficiency frontier, beating Frontis-MA1 at the same wall-clock. THE CORRECT
  COMPARISON TARGET. Not yet indexed.**
- arXiv 2606.24530 NatureBench (same authors) — HF downloads 16,343, far more traction than anything in
  this release.
- github.com/facebookresearch/aira-dojo + arXiv 2505.15201 — the upstream this harness FORKS (Meta,
  CC BY-NC); the genuine baseline for "OpenMLE-Evo beats AIRA-Evo".
- openai/mle-bench root README leaderboard — nine entries at or above 71.21%; ML-Master 2.0 (already
  intake-413) at 75.76% on 2xRTX 4090/24h is the closest hardware comparison. Source of the SEM-vs-SD finding.
- openreview.net/forum?id=IUltZSgLMm — same authors' RSI survey, the conceptual frame behind OpenRSI.

## ENTRY CORRECTIONS: 8 (verification -> dive-verified; credibility 1 KEPT, re-derived)
