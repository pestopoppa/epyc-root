# 2b-D — ENAMEL / EvalPerf / Mercury / GSO — the efficiency-metric ancestors

## HEADLINE
1. **The disputed claim is dead, and it died differently than we thought.** SWE-fficiency's "normalized
   metrics inherently reduce variability" **does not cite ENAMEL at all — it cites EvalPerf, and
   EvalPerf's text argues the OPPOSITE.** Our decline to amend the measurement constitution is now
   definitively correct, on STRONGER grounds than the ones we declined on.
2. **The cluster provides 5-6 INDEPENDENT DESIGN POINTS, NOT 8.**
3. **GSO is the standout adoption candidate AND IT CONTAINS llama.cpp.** MIT, NeurIPS'25, and
   **2 of its 102 tasks are `abetlen/llama-cpp-python` optimization tasks** — our own production domain,
   with EXPERT-COMMIT performance targets.

## THE ID RESOLUTION
- **2406.06647 = ENAMEL** "How Efficient is LLM-Generated Code?" — Qiu, Zeng, Ezick, Lott, Tong
  (UIUC + Qualcomm), **ICLR 2025**. The eff@k / right-censoring paper.
- **2408.06450 = EvalPerf / DPE** "Evaluating Language Models for Efficient Code Generation" —
  Jiawei Liu, Xie, Wang, Wei, Ding, Lingming Zhang (UIUC, the EvalPlus team), **COLM 2024** —
  **ALSO PEER-REVIEWED**, a fact my brief did not have and which decides Q5.
**OUR INDEX IS CLEAN.** Both IDs appear only inside intake-939's referenced_arxiv_ids, correctly, as two
distinct entries. The conflation lives purely in dive PROSE. No index repair needed.

## THE DECISIVE ANSWER: OVERTURNED, AND THE PREMISE WAS MISATTRIBUTED
SWE-fficiency Appendix N: "This observation aligns with related work finding that conversion to
normalized or percentage-based speedup metrics inherently reduces variability in final scores
**(Liu et al., 2024)**" -> its bibliography resolves that to **arXiv 2408.06450 = EvalPerf**.
`grep -ci "qiu|enamel|eff@k"` over SWE-fficiency v3 returns **0, 0, 0**. It NEVER cites ENAMEL.
**ENAMEL: NOT-FOUND-IN-SOURCE.** Its single normalization sentence is scale-comparability only ("so that
the scale of the score does not differ across problems"). Its variance reduction comes from (1) R=6
repeats + **Hodges-Lehmann estimator** and (2) **Rao-Blackwellization of the bootstrap estimator** —
neither is normalization.
**EvalPerf (the ACTUAL citation): OVERTURNED — the source says the opposite.** Sec A.2: "Relative
speedup ... its applicability becomes less clear across a broad range of tasks. This is because **the
degree of speedup varies significantly across different tasks** ... **This variability can lead to
confusion** ... To overcome these limitations, Differential Performance Evaluation (DPE) defines a new
metric." **EvalPerf introduces DPS *because* relative speedup is variable.** Its stability comes from
HARDWARE PERFORMANCE COUNTERS and from SELECTING LARGE COMPUTATIONS, not normalization.
**THIRD-PARTY CORROBORATION OF OUR DERIVED MECHANISM** — GSO Appendix D, a disjoint Berkeley group:
"Our metric controls for machine-specific variation by comparing generated optimizations against expert
developer implementations **in the same environment**, rather than measuring absolute speedups."
=> **CLOSE THE OPEN ITEM. The decline stands; the constitution needs no amendment.**
Deeper point: ENAMEL's own eff@k IS itself normalized, and so is the "speedup" baseline it beats — its
Sec C.3 comparison is normalized-vs-normalized. **The axis that mattered was CENSORING, never normalization.**

## RIGHT-CENSORING + eff@k — extracted implementably
Per-level score: f = (T_i - max_m t)^+ / (T_i - max_m t*), worst-case over the M_l cases in the level.
**THIS IS THE CENSORING INSTRUMENT**: once max_m t >= T_i the clamp makes f = 0 "regardless of the exact
value" — **the unknowable censored magnitude is DISCHARGED rather than IMPUTED.** The transferable
primitive: *make the score's dependence on the measurement vanish at exactly the point the measurement
becomes uninformative.*
Time limit T_i = alpha * max_{l,m} t*, alpha=2. Timing: R=6 repeats aggregated by **Hodges-Lehmann**
(median of pairwise means) for "robustness against outliers as well as high statistical efficiency".
Estimator: eff_i@k = sum_{r=k..n} [C(r-1,k-1)/C(n,k)] * e_(r) over ASCENDING order statistics.
**Theorem 1: unbiased, Var <= (k/n) Var[naive].** Measured SD **0.02/0.08 vs vanilla 0.20/0.25** at k=1/10.
Algorithm 1 is ~6 lines and numerically stable (the binomials overflow if computed directly):
  lambda_n = k/n; for r = n-1..k: lambda_r = lambda_{r+1} * (1 - (k-1)/r); sort e asc; return sum lambda_r e_(r)
**CAVEAT DERIVED FROM EQ.1, NOT STATED IN THE PAPER: eff@k SATURATES.** As t->0, f -> alpha*A/(alpha*A - B_l);
on the hardest level the ceiling is **alpha/(alpha-1) = 2** at alpha=2. **A 2x and a 1000x win over the
expert reference score identically.** eff@k retains magnitude only inside roughly a [0,2] band.

## EvalPerf DPS — graded but ORDINAL
Adaptively CLUSTERS reference solutions by efficiency, cutting where delta > bias + sqrt(w/t_bar) —
**a noise-aware threshold that WIDENS FOR SHORTER RUNTIMES**, motivated by their measurement that CV
rises as runtime falls. DPS = cumulative share of clustered references the candidate beats.
Measurand is **RETIRED INSTRUCTIONS via hardware counters** — "variance of repeated executions at most a
few hundred instructions" against "billions". **Cross-platform max CV 0.4% over 4 test beds.**
MAGNITUDE: PARTIAL — better than COFFE, worse than a raw ratio. COFFE's efficient@k is genuinely BINARY
(c_f = "correct solutions FASTER THAN THE BEST GROUND TRUTH", a hard threshold at 1.0x). DPS is GRADED
but **ORDINAL** — the score is where you land in the empirical distribution, so the magnitude->score
mapping is set by that distribution's SHAPE, not by physics; resolution capped by m >= 4 clusters.
It converts magnitude into RANK, which is exactly why it survives cross-platform and exactly why it
cannot tell you HOW MUCH faster.
**MAGNITUDE RETENTION RANKING**: GSO raw harmonic-mean speedup (unbounded, kept as explicit secondary)
> ENAMEL eff@k (continuous, ceiling 2) > Mercury Beyond (continuous, clipped) > EvalPerf DPS (ordinal)
> COFFE efficient@k = GSO Opt@K (binary).

## THE LINEAGE MAP — the Du bloc
Mingzhe Du is the hub on THREE papers: Mercury ∩ EffiBench-X = 3 shared authors (Du, Ng, Luu Anh Tuan);
Mercury ∩ SWE-Perf = 2 (Du, Qian Liu); SWE-Perf ∩ EffiBench-X = 1 (Du).
**Mercury is the ANCESTOR AND CONNECTOR of the pair we already established as non-independent.**
EffiBench-X additionally inherits EffiBench (4 of 5 authors carry over), so
**Mercury -> EffiBench(-X) -> SWE-Perf is ONE CONNECTED COMPONENT OF FOUR PAPERS.**
**THREE DISTINCT LIUS — DO NOT MERGE**: Jiawei Liu (EvalPerf, UIUC), Qian Liu (Mercury/SWE-Perf, Sea AI
Lab), Jinjian Liu (GSO, Berkeley). **The "Liu et al., 2024" ambiguity is precisely how the original
misattribution became plausible.**
ENAMEL and EvalPerf: same institution (UIUC), ZERO shared authors — different groups (Tong vs Lingming
Zhang). Genuinely independent; institutional proximity is a weak, not disqualifying, correlation.
**CONSEQUENCE FOR THE LADDER**: the apparent field-wide consensus that "efficiency scores must be
normalized against a reference distribution" is **HALF ONE LINEAGE.** The genuinely independent
instruments DIVERGE sharply: ENAMEL normalizes against ONE EXPERT SOLUTION with censoring; EvalPerf
against a CLUSTERED LADDER using instruction counts; GSO against a SINGLE HUMAN COMMIT in the same
container; COFFE against THE BEST GROUND TRUTH, binary. **Count the design space as four, not eight.**
CLEAN NOTE: SWE-fficiency (Harvard/GDM) is OUTSIDE the Du bloc and cited EvalPerf (UIUC) — so the
disputed claim is a **CROSS-LINEAGE MISREADING, a citation-hygiene failure, not a captured literature.**

## GSO — the standout, and it is ON OUR DOMAIN
Oracle-equivalence is a **GOLDEN-FILE CHARACTERIZATION TEST, not a test suite.** Six-function contract:
setup() [UNTIMED] / experiment(data) [THE TIMED REGION] / store_result / load_result /
check_equivalence(reference, current) / run_test(eqcheck, reference, prefix) -> float.
**The oracle is a stored JSON produced by running the same script against the PRE-optimization codebase**
— correctness is characterization against the codebase's own prior behaviour, not against a spec.
**AGGREGATION — THE SINGLE MOST TRANSFERABLE FINDING.** Harmonic mean over per-test speedups, chosen
explicitly over geometric mean citing Jacob & Mudge 1995: "A model achieving speedups of [0.1, 1000]
across two tests yields a geometric mean of 10, despite degrading performance on one test. In Section 5,
we show that **agents INDEED PERFORM SUCH OPTIMIZATIONS and thus can 'game' the geometric mean**."
Appendix E also rejects arithmetic mean and risk-adjusted geomean, because "we do not want symmetric
treatment - large wins on minor tests shouldn't hurt, only significant regressions matter." Harmonic
mean's "asymmetric sensitivity punishes slowdowns heavily, while almost ignoring large speedups."
Opt@K = Opt_{0.95}@K — 95% of the HUMAN EXPERT'S speedup, measured in the same container.
**Leading SWE-agents score <5%.**
**2 OF 102 TASKS ARE abetlen/llama-cpp-python** (~20.8 GB compressed) — the most on-domain evaluation
asset in this entire cluster.
TWO WEAKNESSES TO CARRY IF WE BORROW: (1) check_equivalence compares a REDUCED SUMMARY — in the shipped
example only `shape` plus `first_entries = replaced[:5]`; an optimization wrong outside that digest
PASSES, and the oracle is LLM-authored and only spot-checked. (2) **`timeit.timeit(..., number=1)` — a
SINGLE TIMED RUN per test.** Defence is breadth + harmonic-mean asymmetry, not repetition — materially
weaker than ENAMEL's R=6 + Hodges-Lehmann. **Import its AGGREGATION and EQUIVALENCE-CONTRACT discipline;
do NOT import its timing discipline.**

## MERCURY — REJECTED ON A HARD GATE, INGEST AS EVIDENCE ONLY
**The repo carries NO LICENCE FILE AT ALL** (default all-rights-reserved) and the dataset is CC BY-NC 4.0
over LeetCode content under a Fair-Use claim. Fails our open-source-self-hostable requirement ON THE CODE,
independent of the NC restriction. **It is the WORST-licensed of the four, not the better-vetted alternative.**
Three in-source defects: (1) **`Beyond` IS NOT A PERCENTILE despite the prose** — the formula is min-max
LINEAR INTERPOLATION, yet Figure 2's caption reads "outpacing 86.18% of collected solutions"; those
coincide only under uniformity, and the Limitations concede "we measure code efficiency under the
assumption that the code runtime is uniformly distributed." (2) Two-sided clipping **conflates WRONG with
MERELY-VERY-SLOW** (both -> 0). (3) **LeetCode contamination, conceded by a competitor with receipts** —
ENAMEL Table 9 scores Code Llama 34B Python at Mercury Beyond 0.424 and EffiBench 0.336 against ENAMEL
eff@1 0.268, concluding LLMs "have seen the public solutions on LeetCode ... but have never seen our
expert-written efficient solutions."
ANSWERING Q5 DIRECTLY: **NO.** Peer review is not the differentiator it appeared to be — EvalPerf is ALSO
peer-reviewed (COLM 2024) and beats Mercury on licence (Apache-2.0 vs none), maintenance, measurement
design (hardware counters vs wall-clock) and native local-endpoint support.

## ADOPTABILITY MATRIX
| | ENAMEL | EvalPerf | Mercury | GSO |
| licence(code) | Apache-2.0 | **Apache-2.0** | **NONE** | **MIT** |
| venue | ICLR 2025 | COLM 2024 | NeurIPS D&B 2024 | NeurIPS D&B 2025 |
| local endpoint | yes, trivially | **yes, NATIVELY (`--backend openai --base-url`)** | indirect | yes, indirectly |
| disk | **~234 MB** | ~100 MB | ~3 GB | **168 GB compressed / 102 images — DOES NOT FIT 158 GB** |
| compute | CPU-only, minutes-hours | **~15 min/model** | 256 tasks x K=5 | 3 h/task |
| isolation | **NONE — runs untrusted code in bare subprocesses, documented inability to kill try/except infinite loops** | subprocess + perf | sandboxed | **Docker per task — the only properly isolated one** |
| maintained | 2025-04 (17*) | **active 2025-10 (1790*)** | 2026-03 (87*) | **active 2026-07 (90*)** |
GSO disk detail: pandas 54.4 GB/34 tasks, numpy 46.6/36, **llama-cpp-python 20.8/2**, pillow-simd 9.5/7,
transformers 8.5/4, tokenizers 7.8/4, pydantic 7.0/4, pillow 5.4/4, tornado 4.3/4, datasets 3.9/3.
Same-repo tasks share base layers so realized disk is below the naive sum. **The llama-cpp-python pair
alone (~21 GB) is both affordable AND the most on-domain asset in the cluster.**
TWO HARD GATES: Mercury's missing licence; and **ENAMEL executes untrusted generated code with NO
CONTAINER on a host we share with other agents' llama-server processes** — adopt the METRIC, run it
under our own isolation, never `demo.py` as shipped.

## FOUR NEW ENTRIES PROPOSED (intake-957..960)
957 **ENAMEL 2406.06647** — novelty high, relevance high, credibility **3**, **adopt_patterns**
958 **EvalPerf 2408.06450** — novelty high, relevance high, credibility **4**, **adopt_component**
    (lowest friction in the cluster; native --base-url; ~15 min/model; ~100 MB)
959 **Mercury 2402.07844** — novelty low, relevance medium, credibility **3**, **not_applicable**
    (hard licence gate; ingest as lineage evidence only)
960 **GSO 2505.23671** — novelty high, relevance high, credibility **5**, **adopt_patterns**
    (highest credibility in the cluster; MIT; llama-cpp-python tasks)

## LEDGER: 13 rows
1 CLOSE the SWE-fficiency Appendix-N item — the citation is EvalPerf, which argues the opposite.
  **RESOLVED, decline confirmed.** Record the citation trail so it cannot reopen.
2 correct the dive-narrative ID record (index itself is clean)
3 adopt RIGHT-CENSORING as a scoring primitive for capped-wall-clock benches -> **measurement-constitution
  amendment, HUMAN-ONLY boundary; prepare the decision package, do not self-apply**
4 **ADOPT THE HARMONIC MEAN for aggregating per-test speedups; retire geometric mean where we use it.
  HIGHEST-VALUE SINGLE FINDING — GSO shows agents GAME geomean. Audit current aggregation sites first.**
5 adopt the Hodges-Lehmann estimator for aggregating R repeated timings -> drop-in
6 prototype instruction-count measurement for GENERATED-CODE scoring; **explicitly INVALID for our
  inference kernels, which are bandwidth-bound**
7 **PULL GSO's 2 llama-cpp-python tasks (~21 GB) and run them against our coder/architect roles.
  HIGHEST-VALUE ADOPTION — on-domain, MIT, expert-commit targets.**
8 run EvalPerf against our local endpoint — lowest friction, ~15 min/model
9 REJECT Mercury on the licence gate; ingest as evidence only
10 PERSIST the lineage finding in cross_references on all affected entries
11 **BLOCKING PRECONDITION on 3: if eff@k is adopted, run it under OUR OWN container isolation**
12 **ESCALATE to operator as options+tradeoffs: the magnitude-vs-threshold ladder design choice, now that
   the design space is complete — continuous-saturating (eff@k) / ordinal (DPS) / binary (efficient@k,
   Opt@K) / raw-ratio secondary (GSO). THIS IS THE ACTUAL LADDER DECISION.**
13 EXPLICIT DECLINE: GSO's single-shot number=1 timing and its reduced-digest equivalence check —
   recorded so a later session does not import them with the good parts

## FURTHER SOURCES (verified absent from the index)
1 **arXiv 2607.01211 "Are Performance-Optimization Benchmarks Reliably Measuring Coding Agents?" (2026)
  — directly meta-evaluates this entire cluster. HIGHEST-PRIORITY FOLLOW-UP; it may PRE-EMPT our whole
  ladder decision.**
2 arXiv 2402.02037 EffiBench — the direct ancestor; needed to close the lineage component
3 **Jacob & Mudge 1995 "Notes on Calculating Computer Performance" — GSO's cited authority for
  harmonic-mean aggregation. LOAD-BEARING for actionable 4; read before amending.**
4 Hodges & Lehmann 1963 — load-bearing for actionable 5
5 Bang & Tsiatis 2000 — ENAMEL's censoring authority
6 Casella & Robert 1996 — ENAMEL's Rao-Blackwellization authority
ARTIFACTS: gso-bench/gso-experiments (full eval logs+transcripts, lets us calibrate against published
agent runs WITHOUT SPENDING COMPUTE) · **GSO HackDetector** (reward-hacking detector for optimization
benchmarks — directly relevant to correctness-gating design) · gso-bench/scaffolds (Harbor integration,
the concrete path to pointing GSO at our local endpoint) · Cirron.
