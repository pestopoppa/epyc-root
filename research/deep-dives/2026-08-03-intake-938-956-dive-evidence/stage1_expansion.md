# Stage-1 Phase-3 EXPANSION — 2026-08-03 (candidates intake-947..956)

Cap: 10 per run. Used: 10. All dedup-checked unbounded → zero primary-field collisions.
(ThunderKittens' 2 whole-file mentions are inside other entries' notes — not a collision.)

## ⚠ SCHEMA-NORMALIZATION NOTE — MY DEFECT, NOT THE AGENTS'
The compact expansion schema I wrote listed `verdict: ...` and `credibility_score: N-or-null` WITHOUT
restating the enums. Consequently agents returned out-of-schema values: `verdict: dive`,
`verdict: decline-with-watch`, `novelty: novel`, and credibility scores of 7 and 8 against a 0–6 rubric.
Every value below is normalized per the rubric and the normalization is RECORDED, not silently applied
(same treatment as intake-936 on 2026-07-29, where an agent returned credibility 66 and novelty
'significant'). This is now the SECOND session with this failure — the fix belongs in the skill's
sub-agent dispatch contract, not in another one-off correction.

| entry | field | agent returned | normalized to | basis |
|---|---|---|---|---|
| HipKittens | novelty | `novel` | `high` | not an enum value |
| HipKittens | relevance | `low` | `medium` | in-domain (10 active MI210 handoffs), not actionable ≠ tangential |
| HipKittens | credibility | 8 | **5** | MLSys-2026 venue +2, ≤12mo +1, HazyResearch/Stanford +1, bias 0, AITER-merge corroboration +1 |
| HipKittens | verdict | `decline-with-watch` | `adopt_patterns` | not an enum value; matches house precedent intake-871 (ideas yes, artifact hardware-foreclosed) |
| benchmrk | credibility | 6 | **null** | `reported_results: NOT-FOUND-IN-SOURCE` → rubric's null branch |
| benchmrk | verdict | `dive` | `adopt_component` | not an enum value; it is a runnable Apache-2.0 scoring engine |
| Afterburner | credibility | 7 | **2** | preprint +0, 15mo → 0, known contributors +1, bias 0, corroboration +1 |
| Afterburner | verdict | `dive` | `adopt_patterns` | training unadoptable; metric design transfers |
| EffiBench-X | credibility | 8 | **1** | preprint +0, 15mo → 0, known contributors +1, bias 0, corroboration +0 |
| EffiBench-X | verdict | `dive` | `adopt_component` | Apache-2.0 + Docker self-hostable, confirmed |
| PIE | credibility | 8 | **3** | ICLR-2024 Spotlight +2, **>24mo −1**, Google/CMU/UPenn/DeepMind +1, bias 0, corroboration +1 |
| PIE | verdict | `dive` | `adopt_patterns` | gem5 mitigation not portable; the null-experiment protocol is |
| SWE-Perf | credibility | 8 | **4** | ICML-2026 accepted +2, v2 2026-07 ≤12mo +1, TikTok/NUS/XJTU +1, bias 0, corroboration +0 |
| SWE-Perf | verdict | `dive` | `adopt_patterns` | **license unresolved** → cannot commit to the artifact; the statistics port regardless |

---

## intake-947 — github.com/HazyResearch/HipKittens  (expanded_from intake-944)
repo · hardware_optimization, local_inference · **arXiv 2511.08083 also surfaced (dedup: clear, 0 mentions)**
"HipKittens: Fast and Furious AMD Kernels" — Hu, Wadsworth, Siddens, Winata, Fu, Swann, Osama, Ré, Arora
MIT · 448 stars · created 2025-10-31 · last push 2026-07-28 · 30 contributors · 15 branches · 24 open issues

### 🔴 THE DECISIVE ANSWER: **CDNA3-ONLY. NOT gfx90a. NOT our MI210.**
Evidence is structural, not just prose:
- README: *"We support CDNA3 and CDNA 4."*
- Install gated per-arch: *"For MI350X and MI355X with gfx950 arch"* / *"For MI300X/MI325X, use below docker
  for gfx942 arch"* + *"git checkout cdna3 # not the main branch!"*
- `include/` contains ONLY {cdna3, cdna4, udna1, pyutils}; `include/kittens.cuh` dispatches only on
  KITTENS_CDNA4 / KITTENS_UDNA1 / KITTENS_CDNA3. **No CDNA2 macro, no cdna2 directory** (checked on main
  AND the cdna3 branch), no gfx90a branch among 15.
- gfx90a/MI210/CDNA2 appear nowhere in README, arch dispatch, or issues.

**This is exactly the intake-679 trap** ("CDNA3-listed work must be treated as ports, not drop-in
reproductions") and it is why QuixiCore-ROCm — which forks this — is 🚧 on all 16 kernel families for us.
The most valuable thing this entry does is CLOSE a false lead before anyone spends on it.

- Claims: tile primitives generalize off NVIDIA to AMD; **1.2–2.4× over all available kernel baselines**
  on d=64 attention, GQA backwards, memory-bound kernels; competes with AMD hand-written assembly for
  GEMM/attention. Per-kernel absolute TFLOP/s vs rocBLAS/hipBLASLt/CK: NOT-FOUND-IN-SOURCE (PDF unfetched).
- Techniques: tile primitives sized to matrix cores · bank-conflict-free coalesced tile memory ops ·
  direct buffer loads (async) · **8-wave ping-pong and 4-wave interleave scheduling** · MFMA wrappers ·
  C++-embedded DSL.
- Credibility signal: HK kernels reportedly **merged into AMD's AITER as a backend (Mar 2026)** — vendor
  uptake is the strongest signal here.
- handoffs: agentic-rocm-kernel-authoring, mi210-mfma-compute-bound-paths, autokernel-research-loop,
  mi210-big-model-and-acceleration-roadmap, rocm-verify-profile-backend · intakes: 944, 679
- ACTIONABLES [unverified]: record as CDNA3-ONLY **with the kittens.cuh dispatch evidence** so no future
  session repeats intake-679 · mine the scheduling patterns (ping-pong/interleave, bank-conflict-free
  layouts) as arch-independent lessons for hand-written gfx90a MFMA paths · treat the AITER merge as a
  procurement datapoint — the AMD kernel-quality frontier is now CDNA3+, widening the MI210 gap.
- DIVE: low for execution (nothing runs on gfx90a), moderate for design.

## intake-948 — github.com/block/benchmrk  (expanded_from intake-943)
repo · benchmark_methodology, tool_implementation · Apache-2.0 · Go (no CGO) · 5 stars · 9 commits · 1 human author

### The key correction: it is the SCORING ENGINE, not the corpus.
- **Ships ZERO ground-truth cases.** Bring-your-own answer key. Tree scan confirms no annotation/corpus
  JSON anywhere. `examples/vulnerability-coverage` ships only README.md + ai-annotation-prompt.md.
  Dangling reference: a 2026-04-23 commit says "align defaults with bundled corpus" and examples/README.md
  cites `annotations/juice-shop-vulns.json` — **neither path exists on main.**
- So it does **not** close our dual-gold-corpus gap; it **defines the schema for one**.
- **Precision/FP is first-class**: TP/FP/FN, precision, recall, F1, accuracy, plus a `status: invalid`
  annotation type that exists specifically so false positives are scoreable. That is precisely the axis
  intake-845 (c-CRAB) flagged as missing ("binary pass-rate only; no precision/false-positive axis").
- Also: **tiered recall** (must/should/may), `--min-consensus` multi-annotator filtering, `--iterations`
  with mean ± σ and a CI-overlap test, coverage-overlap analysis, SQLite store.
- **Tool-agnostic via SARIF 2.1.0** — any tool writing `$OUTPUT_DIR/results.sarif`, via local script,
  `docker --network none`, or pre-run SARIF import. Ships semgrep/bandit/codeql wrappers. **An LLM
  reviewer wrapped to emit SARIF is a first-class scanner** — that is the hook for us.
- **Contamination argument worth importing**: *"Juice Shop, WebGoat, and OWASP Benchmark are in the
  training data of every large language model"* → recommends private, synthetic-fresh, or post-cutoff repos.
- 35 `_test.go` files; `make test` with race detector. reported_results: NOT-FOUND-IN-SOURCE.
- handoffs: eval-tower-verification, reviewer-calibration-accounting · intakes: 943, 845
- ACTIONABLES [unverified]: adopt the annotation envelope (cwes[], evidence[], status:invalid,
  annotated_by, criticality tier) as the dual-gold label schema · wrap our LLM reviewer as a SARIF-emitting
  scanner and score it against a Semgrep baseline · import the contamination rule into eval-tower.
- DIVE: read `internal/analysis` (matcher, metrics, cwemap, coverage) + `internal/corpus/annotations.go` —
  location-matching and FP-attribution is the hard part of any dual-gold verifier and it is ~24k of tested Go.

## intake-949 — arXiv 2505.23387 — Afterburner  (expanded_from intake-939)
paper · benchmark_methodology, training_distillation · Du, Luu, Liu, Qing, Huang, He, Liu, Ma, Ng · 2025-05 (v3 Jun 2025)
ID/title VERIFIED.

### The load-bearing claim is CONFIRMED — but materially weaker than the bare quote implies.
`degradation_claim_verified: CONFIRMED 0.33% → 7.33%` (Table 3 W%, Time, Qwen2.5-3B base vs AfterburnerGRPO).
**BUT the denominator moved.** F% (failed all tests) falls 72.00 → 38.33 in the same rows, so the base
model's 0.33% W% is measured over a ~28%-passing denominator. Per-passing-solution: ~1.2% (base) vs
~11.9% (GRPO) — a real ~10× degradation, but the raw 22× headline is **inflated ~2× by the correctness
change**. **Cite the pair only alongside F%.**
This is a clean worked instance of our own `gate-scope-must-match-measured-subset` lesson.

- Buckets: B% better-than-all-human / M% within-mediocre-human / W% worse-than-all-human / F% failed.
- GRPO keeps improving efficiency across iterations while SFT and DPO saturate. pass@1 47%→62%;
  beat-human-efficiency likelihood 31%→45%.
- Frontier ref in-paper: DeepSeek V3 Time (5.33, 80.67, 0.67, 13.67) — beats AfterburnerGRPO on M% and F%.
- Instrumentation: `time -v` + VmRSS sampled from `/proc/[pid]/status`; bootstrap CI B=128.
- Datasets: Venus (2,181 train / 300 test), APPS (10,000 problems).
- **Independence from intake-939 (FAIR): STRONG** — zero occurrences of Meta/FAIR/Facebook; no byline
  overlap. (Verified from this paper's side only.)
- handoffs: master-handoff-index, architect-bench-runbook, batched-decode-measurement,
  inference-acceleration-index · intakes: 939
- ACTIONABLES [unverified]: adopt the four-bucket B/M/W/F reporting shape — a speedup that also grows a
  Worse bucket is a different result, and MEASUREMENT.md claim grammar has no slot for it today ·
  codify the paired-denominator rule (never report a regression-rate delta without both arms' completion
  rate) · cross-check `time -v`+VmRSS+bootstrap against our llama-bench protocol (do we bootstrap at all?).

## intake-950 — arXiv 2302.07867 — PIE, "Learning Performance-Improving Code Edits"  (expanded_from intake-939)
paper · benchmark_methodology, training_distillation · Shypula, Madaan, Zeng, Alon, Gardner, Hashemi,
Neubig, Ranganathan, Bastani, Yazdanbakhsh (UPenn/CMU/Google/DeepMind) · v1 2023-02, **ICLR 2024 Spotlight** (v4 2023-11)

### VERSION MATTERS — and the commonly-repeated attribution is WRONG.
`version_read: v4` (ICLR-era). **The timing-noise material is NOT in v1** — v1's abstract never mentions
gem5 and frames results differently. The 1.91× figure belongs to the ICLR revision. v5 (2024-04) unread.

`spurious_speedup_claim_verified: CONFIRMED 1.91× — but read it precisely.` 1.91× is the **top-5% tail**
over 500 identical-vs-identical program pairs timed with Hyperfine. The **mean spurious speedup is 1.12×,
sd 0.36**. It is a tail statistic, not a typical error.

`timing_mitigation_adopted:` **deterministic full-system simulation (gem5), NOT hardware performance
counters** — *"we measure program performance using the gem5 ... full system detailed microarchitectural
simulator"*, Verbatim Intel Skylake config. **The "hardware performance counters" attribution circulating
elsewhere is an outside embellishment — do not repeat it.**

- Best system 6.86× mean speedup, optimizes 87.68% of test set by ≥10%; CodeLlama-13B w/
  performance-conditioned generation 5.65× vs 4.06× human reference.
- Dataset: 77,967 train / 2,544 val / 982 test pairs from CodeNet (C++).
- Metric: correctness-gated %OPT — must be ≥10% faster AND pass all unit tests.
- handoffs: autokernel-research-loop, rocm-verify-profile-backend, mi210-kernel-rnd-loop-proposal,
  batched-decode-measurement · intakes: 939
- ACTIONABLES [unverified]: **run the identical-pair null experiment on our own harness** (N≥500 A-vs-A
  kernel pairs; publish mean/sd/top-5% spurious speedup as the loop's noise floor; set the promotion
  threshold above the TAIL, not above 1.0) · adopt correctness-gated %OPT as the autokernel promotion
  predicate, replacing bare wall-clock argmax · gem5 is not portable to gfx90a — scope a determinism
  study rather than assuming counters fix it, because **the paper does not claim they do**.
- OPEN: is the 1.91× tail runtime-dependent? Noise for ms-scale GPU kernels may be far tighter than for
  sub-second CPU binaries. Host hardware / run count / warm-up for the null experiment: NOT-FOUND-IN-SOURCE.

## intake-951 — arXiv 2507.12415 — SWE-Perf  (expanded_from intake-939)
paper · benchmark_methodology · He, Liu, Du, Yan, Fan, Huang, Zheng, Yuan, Ma (XJTU / TikTok / NUS / UCSD)
v1 2025-07, v2 2026-07, **Accepted ICML 2026** · ID/title VERIFIED

- First **repo-level** LLM benchmark for code PERFORMANCE. 140 instances from real performance-improving
  merged PRs across 9 popular Python OSS repos, curated from **102,241 PRs**. Each ships codebase, target
  functions, perf tests, expert patch, executable env.
- **The gap is enormous and will not saturate**: Expert 100% Apply / 100% Correct / **10.85% Performance**;
  Gemini-2.5-Pro 95.00 / 83.57 / **1.48**; Claude-3.7-Sonnet 66.43 / 61.43 / **1.24**;
  +OpenHands (realistic) 87.86 / 77.86 / **2.26**; +Agentless 88.57 / 70.71 / **0.41**.
- **Apply/Correctness rank models DIFFERENTLY from Performance** — Agentless out-applies OpenHands but
  scores 0.41 vs 2.26. Strong argument for a third axis rather than a blended score.
- Models and experts optimize different layers: OpenHands patches target low-level data structures;
  expert patches emphasize high-level abstractions and data integrity.
- 🔑 **THE TRANSFERABLE PART — a ready-made noise discipline**: each unit test run **20×** after a
  3-test warm-up; **IQR outlier drop at k=1**; a gain counts only if **Mann-Whitney U p<0.1** vs the
  pre-patch distribution; the reported gain is a **conservative MINIMUM δ** (their Algorithm 1);
  non-significant speedups score **0**. Docker pinned to 1 core (collection) / 5 cores (evaluation).
- Two settings: oracle = FILE-level; realistic = REPO-level.
- ⚠ **LICENSE UNRESOLVED**: paper says code+dataset "will be released under an academic research license"
  with safety-critical-deployment restrictions; **no LICENSE file visible in the repo**. Under our
  open-source-only policy this gates artifact adoption — hence `adopt_patterns`, not `adopt_component`.
- Repo github.com/swe-perf/swe-perf · dataset HF SWE-Perf/SWE-Perf · site swe-perf.github.io
- handoffs: architect-bench-runbook, master-handoff-index, inference-acceleration-index · intakes: 939
- ACTIONABLES [unverified]: **port the noise protocol, not the tasks** (warm-up + 20 reps + IQR k=1 +
  Mann-Whitney p<0.1 + conservative-minimum gain) as the gate before any efficiency score enters the
  ladder · add Performance as a THIRD axis alongside Apply/Correctness, never folded in · 140 Docker
  instances at 5 pinned cores fits our box trivially, but parallel co-residency would violate the timing
  assumptions → needs a region claim.
- OPEN: source lists 11 repo names against a stated count of 9.

## intake-952 — arXiv 2505.13004 — EffiBench-X  (expanded_from intake-939)
paper · benchmark_methodology · Qing, Zhu, Du, Guo, Zhuo, Zhang, Zhang, Cui, Yiu, Huang, Ng, Luu · 2025-05
ID/title VERIFIED · **Apache-2.0, Docker-self-hostable — the cheapest entry point of the four**

- First **multi-language** code-efficiency benchmark. **6 languages** (Python, C++, Java, JavaScript,
  Ruby, Golang), **623 problems** from 5 competitive-programming platforms (Aizu, AtCoder, CodeChef,
  Codeforces, LeetCode), filtered to **post-Oct-2023** releases for contamination control.
- **Reference baseline is REAL human submissions**, not synthetic — accepted submissions via platform
  APIs + forum solutions + curated GitHub, retained only after verification.
- Three expert-normalized metrics, all clipped to 1: Execution Time `clip(T_human/T_llm, 0, 1)`,
  Memory Peak `clip(M_human/M_llm, 0, 1)`, and **Memory Integral** `A = ∫₀^T M(t)dt` (a time-weighted
  memory term we have no analogue for).
- **Best model reaches only ~62% of human efficiency**: Qwen3-32B ET 62.21 / MP 67.26 / MI 61.48 /
  Pass@1 70.41. DeepSeek-R1 61.33 / 69.41 / 60.06 / 72.79. Gemini-2.5-Pro ET 47.82. Claude-3.7-Sonnet ET 47.79.
- **Efficiency is language-dependent, not a model property**: dynamically-typed languages (Python, Ruby,
  JS) score consistently higher ET than Java/C++/Go — Python leads at 67.30% ET for DeepSeek-R1.
- Timing controls: Docker with **`--cpuset-cpus` explicitly "to prevent multiple benchmark executions
  from contending for the same core resources"**, 10 kHz (0.1 ms) profiler sampling, fixed AWS
  i7ie.metal-48xl (96 physical cores — same core count as our EPYC). Table 6 reports triple execution as
  mean (min, max); whether the HEADLINE table is multi-run is NOT-FOUND-IN-SOURCE.
- Scope limit, admitted in the paper: measures **algorithmic** efficiency, not systems/IO/SWE efficiency.
- github.com/EffiBench/EffiBench-X (Apache-2.0) · HF datasets EffiBench/effibench-x ·
  `python start_sandbox.py --type docker --host 127.0.0.1 --port 8000`
- handoffs: architect-bench-runbook, master-handoff-index, inference-acceleration-index · intakes: 939
- ACTIONABLES [unverified]: stand up the harness on a pinned cpuset region and produce a first ET/MP/MI
  reading for the current coder (Qwen-class Q4_K_M) — **quant-vs-efficiency is a wholly unmeasured axis
  for us** · reuse the normalization shape (score = expert/candidate, clipped to 1) as claim grammar so
  cross-language and cross-model numbers are commensurable · its cpuset-per-execution + 10 kHz sampler
  is directly portable; contrast with our taskset region-claim protocol.

## intake-953..956 — PENDING
SWE-fficiency (2511.06090) · COFFE (2502.02827) · thinkingmachines/Inkling-Small · KaedeTai eschamoe codebook

---
# (continued) — normalization additions for intake-953..955

| entry | field | agent returned | normalized to | basis |
|---|---|---|---|---|
| SWE-fficiency | credibility | 9 | **4** | ICML-2026 +2, v3 2026-06 ≤12mo +1, Google/Harvard +1, bias 0 (Gemini evaluated but does not win), corrob +0 |
| SWE-fficiency | verdict | `DIVE` | `adopt_patterns` | harness advertised "Coming Soon", not downloadable → cannot adopt the artifact |
| COFFE | credibility | 9 | **3** | FSE-2025 (Proc. ACM Softw. Eng., doi 10.1145/3715727) +2, 18mo → 0, CUHK/ZJU +1, bias 0, corrob +0 |
| COFFE | verdict | `adopt-methodology` | `adopt_component` | not an enum value; Apache-2.0 working rig is genuinely adoptable |
| Inkling-Small | credibility | 9 | **1** | vendor card +0, days old +1, TML major lab +1, commercial bias −1, corrob +0 |
| Inkling-Small | verdict | `dive` | `worth_investigating` | consistent with intake-941/942; port cost is the gate |

## intake-953 — arXiv 2511.06090 — SWE-fficiency  (expanded_from intake-939)
paper · benchmark_methodology, agent_architecture · Ma, Hashemi, Yazdanbakhsh, Swersky, Press, Li, Reddi,
Ranganathan (Google / Harvard) · v1 2025-11-08, v3 2026-06-27, **Appearing at ICML 2026** · ID/title VERIFIED

### 🔴 THIS OVERTURNS A FIGURE CARRIED BY intake-939 IN THIS SAME BATCH
`sonnet_claim_verified: PARTIALLY OVERTURNED.`
- Correctness leg **CONFIRMED**: Table 3 gives Claude 4.5 Sonnet 19% "Fails Tests" → 81% pass
  (81% is implied by the table, never printed).
- Speedup leg **OVERTURNED**: Sonnet's captured expert speedup is **0.116x (11.6%), not 4.1%**.
  **0.041x is GEMINI 2.5 FLASH's row in the same table** — the citing claim appears to have crossed rows.
- **VERSION CAVEAT — do not call this a fabrication.** The v1 abstract (2025-11) says "less than 0.15x"
  where v3 says "less than 0.23x", so the entire leaderboard was re-run between versions. The FAIR paper
  may have cited v1 faithfully. What is established: **no 4.1% Sonnet figure exists in v3.**
- ACTION: intake-939's `reported_results` must carry this correction inline rather than the bare figure.

- 498 tasks / 9 repos (astropy, dask, matplotlib, numpy, pandas, scikit-learn, scipy, sympy, xarray),
  **100% disjoint from SWE-bench**. Pass-to-pass optimization only — no new behavior.
- Headline: best model **Claude 4.5 Opus 0.225x** of expert speedup. GPT-5-mini (OpenHands) scores
  **0.019x here while scoring 62.6% on SWE-bench Verified** — SWE-bench strength does not transfer.
- Sonnet patch outcomes: 19% fail tests / 5% correct-but-slower-than-pre-edit / 44% correct-and-faster /
  33% correct-and-faster-than-expert. **~49% of its patches are correct but at-or-below expert speed** —
  exactly what a correctness-only ladder cannot see.
- Agents **satisfice**: median trajectory 30–50 turns against a 100-action cap. They stop early rather
  than exhaust budget.
- 🔑 **NOISE CONTROL — peer-reviewed statement of the discipline we enforce ad hoc**: fixed GCP
  n2-standard-64; each worker = 4 vCPUs pinned to disjoint logical-core groups with **no two vCPUs sharing
  a physical core**; container bound to the **NUMA memory node matching its physical cores**; Docker daemon
  + containerd pinned to a **reserved disjoint CPU set** so image work cannot steal cycles; images prebuilt
  so no install work is on the timed path; `timeit.repeat()` for the full distribution. Curation keeps only
  instances whose runtime improvement exceeds **2× the measurement std dev**. Verified **<0.5% SR variance**.
- 🔑 **NEW ARGUMENT WE SHOULD WEIGH**: the expert-normalized RATIO *is itself* the noise filter — "the
  expert-grounded speedup normalization used in SR acts as an effective noise filter". That is a
  principled candidate answer to our co-residency ranking-instability problem, since a ratio cancels
  host-level drift that absolute tok/s does not.
- ⚠ Harness **NOT downloadable today**: dataset live at HF swefficiency/swefficiency, but
  github.com/swefficiency/swefficiency is "Coming Soon". Paper states intent, not completion. No harness license.
- handoffs: architect-model-selection-bench, eval-tower-verification, research-evaluation-index,
  eval-benchmark-cost-reduction, tool-use-eval-contract · intakes: 939
- ACTIONABLES [unverified]: correct intake-939's provenance note · add an efficiency axis using
  SR-style expert-normalized ratios rather than absolute latency · evaluate the normalization argument as
  a **MEASUREMENT-constitution amendment candidate**.
- SURFACED: GSO (Shetty et al., 2025), cited as prior art on workload extraction, not in our compendium.

## intake-954 — arXiv 2502.02827 — COFFE  (expanded_from intake-939)
paper · benchmark_methodology · Yun Peng, Jun Wan, Yichen Li, Xiaoxue Ren (CUHK / Zhejiang)
arXiv 2025-02; **published FSE 2025**, Proc. ACM Softw. Eng. 2, Article FSE012, doi 10.1145/3715727 · ID VERIFIED

### 🏆 THE HIGHEST-VALUE FIND OF THE EXPANSION ROUND — it solves our measurement problem, not theirs.
**Instrument, don't time.** `CPU Time = InstructionCount × CPI × ClockCycleTime`; only instruction count
is a property of the program, and it **"does not increase even if the program execution is slowed or
stalled by external factors"** — i.e. **co-residency-immune by construction**.

- **Stability margin, measured**: instruction-count RSD vs wall-clock RSD — HumanEval **0.005% vs 5.65%**,
  MBPP 0.004% vs 5.31%, CodeContests 0.003% vs 2.37%, APPS 0.003% vs 2.47%. **>1000× more stable**, and
  linearly correlated with execution time at **Pearson 0.96–1.0**.
- This is a direct answer to the two measurement hazards this batch surfaced: intake-939's 41.2 pp
  co-resident ranking swing, and intake-950/PIE's spurious-speedup tail. Instruction counts do not move
  when a process is stalled.
- Measured with **Cirron** (perf-based), Ubuntu 20.04, Xeon 8358P, 128 cores.
- Protocol: **12 runs, drop highest and lowest, mean of 10**; 5 s per-measurement wall cap.
- Duration-spread by construction: generate 20 stressful tests/problem, keep the **5 with the highest
  instruction counts**.
- **Machine-independence is explicit**: absolute counts are rejected ("not meaningful as the same code
  solution has different CPU instruction counts in different machines"); efficient@k scores **only the
  ratio vs ground truth**.
- **Anti-circularity control worth copying**: stability was validated on the ORIGINAL correctness tests,
  not COFFE's own stressful tests, "to ensure a fair comparison since CPU instruction count is involved
  in building COFFE."
- **efficient@k** = pass@k where a solution counts only if correct AND beating the best ground-truth
  solution. Range 0..pass@k. Argues correctness and efficiency should be **fused, not two scores** — the
  opposite of SWE-Perf's three-axis design. **That is a genuine design disagreement to resolve, not noise.**
- Gap: best efficient@1 **46.97%** (DeepSeek V2 Coder, function) vs best pass@1 **79.90%** — a 31–45%
  drop across all 14 models. File-level speedups mostly <1.0, several <0.1 ("10× slower than ground truth").
- 756 problems (398 function-level from HumanEval+MBPP; 358 file-level from CodeContests+APPS).
- STGen: LLM stressful-test generation with contract inference + LLM-judge plausibility rejection;
  ~99% correct test cases, 96% line coverage; raises discriminability 11.9–43.1%.
- github.com/JohnnyPeng18/Coffe — Apache-2.0 (README-read, not LICENSE-byte-verified).
- ⚠ **PROVENANCE FLAG**: COFFE's "two single time measurements ... can differ as much as 1.91×" is the
  SAME 1.91× as intake-950/PIE and is almost certainly a **restatement of PIE, not independent
  corroboration**. Its RSD table IS original. Do not double-count the 1.91×.
- ⚠ **APPLICABILITY LIMIT WE MUST NOT IGNORE**: Equation 1 assumes CPI is constant. **Our own established
  finding is that CPU decode is bandwidth-bound**, which is precisely a non-constant-CPI regime. So
  instruction count is a strong metric for *generated-code* efficiency and a **questionable** one for our
  *inference-kernel* benchmarking. Do not port it to llama-bench without testing that assumption.
- handoffs: architect-bench-runbook, inference-acceleration-index, master-handoff-index · intakes: 939
- ACTIONABLES [unverified]: add the ladder's efficiency axis as **efficient@k over instruction counts**,
  not wall-clock · adopt trimmed-repetition (12 runs, drop min+max) and ratio-only scoring so numbers stay
  comparable across our heterogeneous hosts · evaluate **STGen separately** as a way to add duration-spread
  to our EXISTING correctness suites — it is the piece that fixes "small tests produce spurious speedups".
- OPEN: does Cirron/perf work under our `perf_event_paranoid`/container/ROCm environment?

## intake-955 — huggingface.co/thinkingmachines/Inkling-Small  (expanded_from intake-942)
repo · local_inference, moe_optimization, multimodal, context_extension, speculative_decoding
Thinking Machines Labs · created 2026-07-27 · apache-2.0 + **an unreviewed acceptable-use policy**

### 🔴 THE AUTHORITATIVE CONFIG OVERTURNS THE QUANTIZER-SUMMARY PICTURE. Port cost is HIGHER than intake-941 implied.
`config_json_fetched: true` — these are ground truth, not prose:
- **NO RoPE AT ALL.** config.json has **no `rope_theta`, no `rope_scaling`, no `partial_rotary_factor`**.
  Instead: `d_rel: 16`, `rel_extent: 1024`, `log_scaling_n_floor: 128000`, `log_scaling_alpha: 0.1`.
  Length extension is **attention log-scaling, not RoPE scaling**. (Semantics — Shaw-2018-style learned
  bias from q/k states — come from secondary WebSearch, NOT this repo; config proves only RoPE's absence.)
- **Per-layer short conv state PRESENT**: `use_sconv: true`, `sconv_kernel_size: 4` — a Mamba-style conv
  cache llama.cpp must allocate **alongside** KV.
- Hybrid attention **5:1**: `local_layer_ids` = 35 of 42 layers; global layers are 5, 11, 17, 23, 29, 35, 41.
  `sliding_window_size: 512`; GQA 4:1 (32 heads / 8 KV, head_dim 128).
- 42 layers · 256 experts · top-6 · 2 shared · hidden 4096 · per-expert intermediate 2048 ·
  `dense_intermediate_size: 16384` at `dense_mlp_idx: 2`.
- 🟢 **MTP IS PRESENT AND SHIPPED**: `mtp_config: {num_nextn_predict_layers: 8, ...}` with weights in a
  separate **`mtp.safetensors`**. **Self-speculation is architecturally available** — this contradicts
  intake-942's "no draft/MTP artifact", which was a correct finding *about the GGUF repo* but not about
  the base model. Both stand; scope them precisely.
- `model_max_length: 1048576` confirmed in config (README never states it).
- Modality encoders separable in principle: vision `hmlp` (4 layers, patch 40, temporal patch 2), audio
  `dmel` (80 mel bins, 16 kHz, ideally <2 min), both projecting into decoder_dmodel 4096; top-level
  `InklingForConditionalGeneration` / `inkling_mm_model` wrapping a nested `text_config`.
- **975B-A41B sibling CONFIRMED by this source**: "The larger Inkling model contains 975 billion total
  parameters with 41 billion active."
- **A v9 port would cost THREE new subsystems, not one**: (a) content-dependent relative attention bias
  replacing RoPE, (b) per-layer sconv state cache, (c) shared-expert-sink MoE routing
  (route_scale 8.0, sigmoid gate, use_gate_bias, norm_after_topk).
- handoffs: master-handoff-index, inference-acceleration-index, tq3-quantization-evaluation,
  batched-decode-measurement · intakes: 942
- OPEN: the **acceptable-use policy text was never fetched** — it is the only thing standing between
  "apache-2.0" and a real license verdict. No `modeling_*.py` ships in the repo.

## intake-956 — KaedeTai eschamoe codebook probe — PENDING
