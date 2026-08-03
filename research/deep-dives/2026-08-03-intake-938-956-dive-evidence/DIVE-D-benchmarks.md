# DIVE-D — SWE-Perf (951) / EffiBench-X (952) / SWE-fficiency (953)
Read at primary source incl. BOTH v1+v3 of SWE-fficiency and BOTH v1+v2 of SWE-Perf.

## 🔴 THIS DIVE OVERTURNED MY OWN EARLIER CORRECTION
I reported to the operator that the FAIR paper (intake-939) crossed rows citing SWE-fficiency, and
that 0.041x belonged to Gemini 2.5 Flash. **THAT CORRECTION WAS ITSELF WRONG.**
**v1 Table 2 lists `CLAUDE 4.5 SONNET 0.041x` and `GEMINI 2.5 FLASH 0.008x`.**
The FAIR citation is a **FAITHFUL v1 QUOTE ON BOTH LEGS** (81% correctness AND 4.1% speedup).
0.041x migrating to Gemini 2.5 Flash in v3 is COINCIDENCE, not the source of the citation.
CAUSE OF MY ERROR: v1 names its models ONLY in the results table, so a Stage-1/2 grep for "Sonnet"
in v1 hits nothing but the bibliography. **Version-pinned quotes are not optional in this literature.**

## RECOMMENDATION
**Adopt EffiBench-X as the INSTRUMENT (Python-only, 308-problem dated subset). Adopt SWE-Perf's
STATISTICS and SWE-fficiency's PLACEMENT CODE as the protocol. DECLINE both as harnesses.**

| | verdict |
| EffiBench-X local endpoint | **WORKS UNPATCHED** — effibench/llm.py does `OpenAI()` with NO ARGS after load_dotenv(), so OPENAI_BASE_URL + dummy OPENAI_API_KEY retargets it at llama-server. Model name free-form, no allowlist. **The operator's decisive question, answered YES.** |
| SWE-Perf code licence | **NONE AT ALL.** No LICENSE/COPYING/NOTICE on any branch; API license null; issue #6 "Under what license is this code?" OPEN SINCE 2025-11-07 with ZERO maintainer replies in 9 months. Default copyright = all rights reserved. Fails our policy outright. (Dataset separately Apache-2.0.) |
| SWE-fficiency disk | **~1.03 TB compressed** (498 x ~2.06 GB avg, manifest-verified: pandas 2.95GB, matplotlib 2.46, dask 2.40, scipy 2.35) vs 158 GB free w/ Docker root on the same fs already holding ~140 GB. |
| EffiBench-X disk | ~2.2 GB compressed images / ~7-8 GB after in-place commit(). Risk is OUTPUTS not images: ~25-45 GB per model across six languages; Python-only ~20 GB total. |

## THE DESIGN CONFLICT LARGELY DISSOLVES — and that is the finding
**ALL FOUR instruments already gate efficiency on correctness AT THE INSTANCE LEVEL.**
- SWE-Perf: `Performance = (1/N_total) sum P_i` — denominator is ALL SAMPLES, so a failing patch
  contributes 0. It is ALREADY FUSED. Fig 6 is the genuinely separate `Performance_pass` view,
  with the expert ceiling RE-COMPUTED PER METHOD (8.3/8.8/11.4) — exactly our own
  gate-scope-must-match-measured-subset axiom.
- SWE-fficiency: failures clamped to max(1/Speedup_gold, SR_min).
- EffiBench-X: "If the LLM-generated solution ... fails to pass all test cases ... its ET score is
  defined as zero."
- COFFE: efficient@k <= pass@k by construction.
=> COFFE's stated worry is ALREADY ANSWERED by instance-level gating in all four, INCLUDING SWE-Perf.
=> **Both entries' contradicting_evidence describes a disagreement the metric definitions do not support.**
The real disagreement is narrow: whether to ALSO PRINT correctness separately. Evidence says print it.

RANKING FLIPS — three independent instances:
1. SWE-Perf T2: Agentless 88.57 Apply / 70.71 Correct / **0.41%** Perf vs OpenHands 87.86 / 77.86 /
   **2.26%**. Robust to subset normalization (correct-only w/ per-method ceilings: 25.4% vs 6.8%).
2. **EffiBench-X T2 — a flip from an instrument that FUSES**: Gemini-2.5-Pro tops Pass@1 (79.43) and
   Memory Peak (75.60) but is 4th on Execution Time (47.82), behind Qwen3-32B (62.21 @ Pass@1 70.41).
   Derived conditional ET/Pass@1 ranges **0.44 to 0.88** — a 2x spread a single number destroys.
3. SWE-fficiency live leaderboard: GPT-5 0.1571 SR / 81.73 correct BEATS GPT-5.2 0.1482 / 88.96.
=> #2 is the resolution: **fusing and reporting correctness are not in tension.**

**RECOMMENDED SHAPE: ONE ranking key, THREE reported columns.** Rank on the fused, instance-gated,
expert-normalized score. Report beside it (a) correctness and (b) the DERIVED conditional
= fused / correctness, only above >=30 solved instances.
Failure mode each choice accepts:
- pure third-axis => SUBSET-SHIFT: a model correct only on easy low-headroom instances scores high on
  a soft subset and can GAME THE METRIC BY DELIBERATELY FAILING HARD INSTANCES. (Our own
  "full-machine gate on a partial-machine cell" error.)
- pure fused (COFFE) => ATTRIBUTION failure, compounded because efficient@k is BINARY (faster than best
  ground truth or not) so a 1.01x and a 100x win SCORE IDENTICALLY — it cannot reward the large
  algorithmic wins that are the entire point.
- our recommendation => DERIVED-QUANTITY failure; mitigate with the >=30 floor.

## 🔑 THE AGGREGATOR MATTERS MORE THAN THE AXIS QUESTION
SWE-fficiency v1->v3 is NOT a re-run. It is an AGGREGATION CHANGE:
v1 = harmonic mean, failures at 1/Speedup_gold, NO LOWER BOUND.
v3 = adds "a per-instance lower bound of SR_min = 0.001 so that patches with near-zero speedup ratios
do not dominate the harmonic mean".
Effect on Claude 4.5 Sonnet: **0.041x -> 0.116x (2.8x)** while its Table 3 patch-outcome row is
**BYTE-IDENTICAL in both versions** (19/5/44/33). Same trajectories, same correctness, 2.8x headline.
Demonstrated arithmetic (497 instances at SR=0.2 plus one outlier):
  one instance at 0.0005 -> harmonic mean 0.1110 | 0.001 -> 0.1429 | 0.01 -> 0.1926 | 0.2 -> 0.2000
**A SINGLE PATHOLOGICAL INSTANCE HALVES THE SCORE.**
=> BAN harmonic-mean-of-ratios. Use clipped arithmetic mean (bounded contribution by construction) or
a trimmed mean.

## KEY OVERTURNS
- **"Expert-normalized ratios act as a noise filter" — OVERTURNED, MECHANISM MISATTRIBUTED.**
  run_evaluation.py:158-176 RE-MEASURES pre_edit_perf_runtime IN THE SAME CONTAINER as the post-edit
  run; the cancellation is in the **PAIRED WITHIN-CONTAINER RATIO**. Speedup_gold is a STORED DATASET
  CONSTANT, so dividing by it is a per-instance rescaling that is **VARIANCE-NEUTRAL BY CONSTRUCTION**.
  Appendix N has NO UNNORMALIZED CONTROL ARM — its design cannot test the claim at all.
  => Our bench-cpu.md ALREADY does paired within-container ratios. The genuinely different mechanism
     worth pursuing is intake-939's AFFINE DRIFT CORRECTION (cross-epoch), which paired ratios do not address.
- **SWE-fficiency harness is LIVE and Apache-2.0** (Copyright 2026 Google LLC, byte-verified sha256
  eaed39fc..ac52, PyPI swefficiency 1.0.0, 3 tags / 2 releases). Stage 1 read it as "Coming Soon"
  because **the default branch is `swefficiency_base`, NOT `main`.** GitHub's NOASSERTION is a
  classifier artifact. => verdict adopt_patterns -> **adopt_component, scoped to the placement code.**
- **"eleven repos vs stated nine" — THE DISCREPANCY DOES NOT EXIST.** The competing number is 12
  ("the same 12 repositories used in SWE-bench"); Table 1 says 9; enumerating all 140 rows gives
  exactly 9 (xarray 54, sklearn 32, sympy 20, astropy 12, sphinx 8, seaborn 6, matplotlib 3,
  pylint 3, requests 2 = 140). django/flask/pytest drop to zero.
- **SWE-Perf licence language is v1-ONLY and was DELETED in the v2 camera-ready.** Stage 1 was right
  about v1 and stale on v2. Operative fact is worse: NO licence file at all.
- **SWE-fficiency paper CONTRADICTS its own code twice**: (a) Appendix F.2 says "no two vCPUs in the
  same group share a physical core" but the shipped default is `threads_per_core=2` — agent EXECUTED
  the module on our host: worker 0 gets cpuset_cpus='4,5,100,101', cores 4 and 5 WITH BOTH SIBLINGS.
  The invariant the code actually holds is "no physical core shared ACROSS workers."
  (b) Appendix C states no universal warmup; run_validation.py:230 has `perf_warmup: bool = True` and
  lines 562/639 run a full discarded pass.
- **v3 Appendix N reports v1-REGIME numbers**: Table 11 gives Claude 3.7 Sonnet 0.0476-0.0480 and
  Gemini 2.5 Flash 0.00794 — matching v1's 0.047x/0.008x, not v3's 0.024x/0.041x.
  **The published stability evidence was not produced under the published aggregation.**
- **GPT-5-mini 0.019x is a STALE v1 FIGURE INSIDE v3 PROSE**; v3 Tables 2 and 6 both say 0.039x.
  The same sentence updated "0.15->0.23" but not the model number. **Quote v3 from tables only.**
- **EffiBench-X: 623 problems PER LANGUAGE (3,738 total)**, confirmed three ways incl. parquet
  null-counts via HTTP range requests (all six languages nonnull=623, nulls=0).
- **EffiBench-X headline tables are SINGLE-EXECUTION**: no repeat/n_runs/median/warmup anywhere in the
  code, AND Table 2 values are byte-identical to the MINIMUM of Table 6's three-run study, 6 of 6.
  Direction is CONSERVATIVE (understates efficiency) — a rigor gap, not a flattering-number problem.
- **EffiBench-X C++ `-fsanitize=address` is DOCUMENTED BUT NEVER APPLIED** — the `flags` key is never
  read; actual command is `g++ -std=c++20 -O2 -o a.out`. The published C++ table is NOT REPRODUCIBLE
  with the released code.
- **AUTHOR LINKAGE: Mingzhe Du co-authors BOTH SWE-Perf (951) AND EffiBench-X (952).** See-Kiong Ng /
  Luu Anh Tuan link EffiBench-X to Mercury. **They are NOT independent instruments and must not be
  counted as mutual corroboration.** SWE-fficiency (Harvard/Google) and COFFE (CUHK/ZJU) ARE genuinely
  independent of them and of each other.

## RISKS ON THE INSTRUMENT WE'D ADOPT
- **FAIL-OPEN METRIC CORRUPTION (highest-priority operational risk)**: open issue #4 (2026-03-09,
  unanswered) "runtime and memory always return 0.0 when running evaluation". Mechanism verified:
  llm_sandbox/docker.py parses `runtime_ns max_memory_kb integral` and on ANY parse failure SILENTLY
  sets all three to 0.0; backend_utils.py:539-543 also defaults to 0.0.
  **This is our own named fail_open_defaults_conceal_their_own_corruption class, sitting on the exact
  metric we would adopt.**
- Hard blockers: `openjdk:21-jdk-bookworm` **404** (image deprecated; kills startup for ALL SIX langs
  because setup() iterates all six unconditionally) -> use eclipse-temurin:21-jdk or --skip-setup;
  and `generate_solution.py` has `from time import time` at line 5 but `time.sleep(...)` at line 123
  -> AttributeError on the first submitted task.
- Repo DEAD: 10 commits, last 2025-10-24, no releases, 4 open issues with ZERO maintainer replies ever.
- **Contamination filter INADEQUATE**: 315/623 (50.6%) carry NO DATE at all (every AtCoder/CodeChef/
  Aizu/Codeforces problem); the dated range is 2023-11-05 -> 2024-12-22, ENTIRELY INSIDE every
  2026-era model's training window. Only the 308 dated LeetCode/functional rows are checkable.
- Venue ambiguity: arXiv 2505.13004 is still **v1 only, comment "Under Review"** at 15 months, but the
  repo description reads [NeurIPS'25] and the README bibtex claims NeurIPS 2025.
  => credibility_score 1 arithmetic ("no venue located") should be RE-RUN.

## 🏆 THE BEST ADOPTABLE ARTIFACT IN THE DIVE IS NOT A BENCHMARK
`swefficiency/harness/cpu_assignment.py` — 196 lines, Apache-2.0, Google-authored, standalone, and it
produced CORRECT NUMA-and-SMT-aware cpusets on our EPYC 9655 THE FIRST TIME IT WAS RUN.
Emits cpuset_cpus + cpuset_mems, buckets by NUMA node, packs within a node. Best-in-class pinning of
the three. On our host: **23 fully isolated 4-whole-core workers at threads_per_core=1** (or 46 at the
shipped =2). Plus scripts/vm/setup_docker.sh pins dockerd itself off the measurement cores.
**Worth more to us than all 1.03 TB of the images it was written to schedule.**
BLOCKER TO RECORD: cpuset_mems binding at 16GB/container WILL FAIL on node 0 (2.5 GB free) — a region
claim must quiesce resident models on target nodes first.

## HOST FACTS ESTABLISHED
96 physical / 192 logical, **4 NUMA nodes (NPS4)**, 24 physical cores each.
Per-node free RAM: **node0 2.5 GB / node1 27 GB / node2 95 GB / node3 50 GB**.
158 GB disk free, Docker root on the same fs already holding ~140 GB (29 GB reclaimable incl. a 29 GB
rocm/vllm image). perf_event_paranoid=1. Docker 29.7.1 / overlay2. None of the six EffiBench-X base
images cached.

## ENTRY DISPOSITIONS
- intake-953 -> **dive-overturned** (retract the row-crossing correction; rewrite the version caveat as
  an AGGREGATION change; verdict adopt_patterns -> **adopt_component** scoped to cpu_assignment.py;
  demote the noise-filter claim; fix GPT-5-mini to 0.039x)
- intake-951 -> **dive-overturned** (replace the licence claim: NO licence at all; DELETE the
  eleven-vs-nine item; reframe contradicting_evidence[0] — Performance is already correctness-gated;
  verdict stays adopt_patterns for a DIFFERENT reason)
- intake-952 -> **dive-verified with material additions** (adopt_component HOLDS and STRENGTHENS —
  local endpoint works unpatched)

## LEDGER: 7 drafts, 6 declines
1 stand up EffiBench-X Python-only on the 308 dated problems -> DRAFT, architect-model-selection-bench.md
2 FAIL-OPEN ACCEPTANCE GATE before trusting any number (run canonical human solutions first, assert
  non-zero runtime/memory/integral on EVERY one) -> DRAFT, eval-tower-verification.md
3 adopt SWE-Perf's statistical gate (3 warm-up + 20 reps + IQR k=1 + Mann-Whitney alpha=0.1 +
  conservative-minimum-gain delta + delta>0.05 floor) -> DRAFT, measurement/protocols/bench-cpu.md.
  CHEAPEST HIGH-VALUE IMPORT; licence-free (a method, not code); ~23x CPU-time multiplier.
4 adopt cpu_assignment.py at threads_per_core=1 -> DRAFT, contention-model-device-and-load-axes-rider.md
5 BAN harmonic-mean-of-ratios; require bounded-contribution aggregator -> DRAFT, MEASUREMENT.md Sec 3
6 adopt fresh-child-process-per-repetition for ranking generated code -> DRAFT, autokernel-research-loop.md.
  NOTE THE DOCTRINAL CONFLICT: SWE-Perf WARMS caches deliberately; SWE-fficiency DEFEATS them. For
  ranking MODEL OUTPUT the anti-cache choice is correct.
7 metric shape: one ranking key + correctness + derived conditional -> DRAFT, architect-model-selection-bench.md
8 DECLINE SWE-Perf harness/dataset as a component (no licence, 180GB personal-account images, weaker pinning)
9 DECLINE running SWE-fficiency (1.03TB; ~0.19 author-hours/instance to extend)
10 DECLINE an efficiency axis over our existing SWE40/LCB — intake-939 measured original correctness
   tests clear the duration-spread gate for **<=3.8%** of problems. **Our sealed SWE40/LCB tasks
   PHYSICALLY CANNOT CARRY A TIMING SIGNAL.** Reopen only after evaluating COFFE's STGen.
11 DECLINE amending MEASUREMENT on "ratios are their own noise filter" — argument does not survive
12 DECLINE instruction counting in llama-bench (unchanged)
13 record the author-linkage correction -> DRAFT, entry edit + research-evaluation-index.md

## DIVE-SURFACED SOURCES
- **arXiv 2408.06450 ENAMEL** — HIGHEST VALUE. The SOLE citation SWE-fficiency uses to back the disputed
  "normalized metrics inherently reduce variability" claim; settling it resolves ledger item 11
  definitively. Cited INDEPENDENTLY by SWE-Perf, SWE-fficiency AND COFFE — the common ancestor of the
  cluster's eff@k design — and in intake-939's reference list. **Exists nowhere in the compendium.**
- **Mercury** (Du/Luu/Ji/Liu/Ng, NeurIPS D&B 2024) — peer-reviewed at a REAL venue (unlike EffiBench-X)
  by the SAME author cluster as 951 AND 952. Would establish how much of this cluster is one lineage,
  and may be a better-vetted alternative for the same job.
- **GSO** (Shetty et al. 2025) — already flagged at Stage 1; provides a per-task ORACLE EQUIVALENCE
  SCRIPT plus hidden performance tests, a third design point in the correctness-gating question.
- EffiBench (original, 2024) — completes the lineage; lower priority.
- **github.com/RidiculousBuffal/effibench-enhanced** (Apache-2.0, pushed **2026-07-29**) — a MAINTAINED
  FORK of a dead upstream, active five days ago. May already carry fixes for the openjdk 404, the
  time.sleep crash and the 0.0 fail-open. **Cheapest possible unblock for ledger item 1.**
- swefficiency.com/assets/leaderboard.json (18 entries, live, re-run past v3) — standing external
  reference with BOTH speedup_ratio and correctness columns.
