# DIVE-E — intake-939, arXiv 2607.25970 (FAIR "RL for Code Optimization"), 125pp incl. Appendices A-G

## DISPOSITION: dive-verified. verdict adopt_patterns STANDS. credibility 4 STANDS.
Every load-bearing MEASUREMENT number verified exactly. Four things change what we do.

## 1. ARTIFACT GATE: RESOLVED NEGATIVE AND CLOSED (was "unresolved")
- Sec C.3 VERBATIM: "CES is a pre-existing remote execution backend... **building the service itself
  is not a contribution of this paper**" and "outside the scope of this paper." Internal Meta infra.
- ZERO release language in 125pp. No "we release", no "available at", no Data Availability,
  no Reproducibility statement, no ancillary files.
- Table 46 (p125) lists licences of CONSUMED assets only. Nothing produced by the paper appears.
- Only 2 code URLs: containers/bubblewrap (3rd party) and facebookresearch/BigOBench (their PRIOR
  paper) — fetched, verified: no DMC-Optim, no CES, CC-BY-NC.
- No DMC-Optim on HuggingFace.
=> **adopt_component is UNREACHABLE. Mark resolved-negative so no future pass re-opens it.**
USABLE ANYWAY: the paper text is **CC BY 4.0**, so Appendices A and C can be quoted at length into
MEASUREMENT.md with attribution. Source corpus (CodeContests) is Apache-2.0, so the recipe is
reproducible from open inputs — unreleased, not unbuildable.

## 2. THE ABSTRACT IS WRONG BY ITS OWN FIGURE
Agent RENDERED p.24 (Fig 8 text is vector-drawn, doesn't extract). Bottom row "Any complexity improves",
N=174/177/154: Optim-RL vs RLVR = **13** (adversary 2); Human vs RLVR = **22** (adversary 6);
Human vs Optim-RL = 16 (adversary 7).
Figure 8, Sec 6 AND the Conclusion all agree on **13 vs 22**. The abstract's **14/28 appears NOWHERE
else in the paper.** Two further defects in the abstract sentence: its "relative to the fastest correct
human submissions" framing is misleading (both figures are vs RLVR as common adversary; true
head-to-head is 16 vs 7), and "about half" (14/28=50%) contradicts the body's "more than half" (13/22=59%).
=> CITE 13 vs 22 WITH Fig 8 AND N. NEVER QUOTE 14/28.
Judge caveats to carry: speed-ID accuracy 68% overall, **59% on human-vs-model pairs**; 22% of speed
wins unclassifiable and excluded; manual review found complexity categorisation correct 94.8%.

## 3. THE TABLE 4 REGRESSION IS REAL — AND NEWLY CORROBORATED ON A SECOND BENCHMARK
Table 4, Qwen 2.5 32B, pre-exec absolute filter tau=2s: **48.2**/31.2/19.2/6.3 vs Standard RLVR
54.8/21.1/9.4/2.4. p100 is -6.6 vs RLVR and -11.8 vs MC+opt.tests (60.0). Paper never mentions it.
NOT a transcription artifact, on three grounds:
 (a) the Qwen 7B tau=2s row matches Table 3's collapsed-binary cell DIGIT FOR DIGIT
 (b) only p100 is anomalous; the other three cells are strong — a slip wouldn't spare three cells
 (c) **DECISIVE: Table 5 LCB transfer, SAME arm, Qwen 2.5 32B tau=2s: pass@1 45.6 vs Standard RLVR
     52.7 = -7.1.** Two benchmarks, same direction => rules out typesetting error.
Scale: reported p100 95% CI half-widths are +-1.4 / +-1.1 elsewhere; 6.6 pts = 4-6 half-widths.
=> QUALIFIES the abstract's "while preserving pure-correctness scores": true for the reported-best
POST-execution configs, FAILS for the PRE-EXECUTION FILTERING FAMILY on Qwen 2.5 32B, on both benchmarks.

## 4. THE 41.2 pp IS MISCHARACTERIZED IN OUR ENTRY (my error, propagated from Stage 1)
Sec C.2: "Across 23 problems and 425 reruns, repeated local re-execution moved the mean-percentile
score by 41.2 percentage points **peak-to-peak on average**"; within-problem std 10.961pp, worst
range 73.743pp. It is **rerun-to-rerun instability of the LOCAL HARNESS, measured with NO STATED
ADDED LOAD** — NOT a local-vs-CES delta and NOT a co-residency-under-load number.
The separate contention experiment (724 jobs) reported COMPLETION failures (294/724 at zero added
load -> 613/724 at 200%), not timing swings.
**MISSING COMPARATOR that makes it quotable: CES mean-percentile std = 2.1 pp (Table 31).**
STRONGER UNFILED DIAGNOSTIC: local execution makes **81.1% of problems look duration-filterable
vs 48.2% on CES**. Robust CV is SCALE-INVARIANT, so a uniform speedup cannot explain this —
contended timing MANUFACTURES SPREAD. Sharpest single diagnostic in the appendix; absent from our filing.
Also: at a 0.1s timeout local execution inflates pass@1 by 21.3x/32.8x/50.3x/20.0x over CES, and
under local timing the 7B BASELINE OUTRANKS the 7B optimization model — the ranking INVERTS.
End-to-end: 8 local-execution RL variants attempted; the correctness-only one completed, **all 7
optimization variants died** (OOM then distributed-comm failures, 160-1620 of 5000 steps, 4-8x slower).

## 5. OUR "OUTER GATE" CLAIM IS PARTIAL — THE WINNER IS A CONJUNCTION
Table 41 definitions:
 - **Collapsed** (WINNER) `R=(1+c~)(1+g)/2 - 1` — hard CONJUNCTION; correct-but-slow collapses to the
   FULL FAILURE REWARD (-1)
 - **Two-gate** (RUNNER-UP) `R=(1+c~)(1+g)/4 - (1-c~)/2` — outer gate; correct-but-slow gets 0.
   **THIS is the analogue of our lexicographic axiom, and it scores LOWER at strict percentiles**
   (45.7/26.1/14.9/4.9 vs collapsed 46.9/29.2/17.4/5.7)
 - Additive blend `R=lambda*c + (1-lambda)*g`, consumes plain c_cor not strict c~
Table 3 VERIFIED DIGIT-FOR-DIGIT: collapsed-binary 46.9/29.2/17.4/5.7; two-gate-binary 45.7/26.1/14.9/4.9;
additive-blend-binary 39.1/24.4/13.7/5.2; optimization-only 0.0/0.0/0.0/0.0 (binary AND bucketed);
multitask-binary 38.0/22.7/12.5/4.4.
**WHAT IT LICENSES**: the ablated property is "NO SPEED CREDIT FOR AN INCORRECT CANDIDATE" (collapsed
and two-gate both have it, beating the three that don't at every percentile). It is NOT evidence that
the outer-gate form specifically is best. Cite as: blending cost **7.8 pts** vs the best gated arm
(46.9->39.1) and **6.6 pts** vs the outer-gate arm (45.7->39.1); pure-speed collapsed to 0.0 everywhere.

## 6. APPENDIX A — THE REUSABLE CORE (Monte-Carlo, RL removed)
Noise model Eq3-4: `d_obs = d_true(1+eps_mult) + eps_add`; decisive derived quantity is the RELATIVE
ADDITIVE BURDEN `r_add = eps_add/d_true`. Anchored on the measured 53ms intercept: at 53ms the
perturbation is >= HALF the observed duration for **75.9% of LCB and 52.4% of DMC-Optim executions**;
at 100ms it exceeds the ENTIRE duration for 68.8% / 46.3%.
Sim spec fully reproducible (A.3): LogNormal base durations, (mu,sigma)=(-2.3,0.5) LCB-like /
(1.0,0.5) DMC-like, N=35 vs 122 tests, Delta=0.2, eta~N(0,0.15^2), 3000 trials. Timeout metric given
an ORACLE threshold chosen after the fact — so all timeout curves are OPTIMISTIC.
Three conclusions in the authors' order:
 1. additive noise is the right abstraction for FAST suites
 2. **FIX THE DATA REGIME FIRST** — threshold tuning cannot rescue a fast-test regime: "it only
    searches for a narrow operating window in a measurement setting where thresholded decisions are
    intrinsically brittle." Empirical: across all training configs LCB timeout pass@1 at the tightest
    threshold spans only **1.0 point (29.6->30.6)** — the metric compresses real differences to nothing.
 3. relative aggregation survives longer than a hard timeout — under ADDITIVE noise timeout falls to
    RANDOM GUESSING across the whole threshold sweep while win-rate stays clearly above.
    **The regime split is specifically an additive-noise phenomenon.**
Metric screen (D.3, 17 candidates): winner is PLAIN MEAN per-test percentile (CV-diff std 3.8 affine,
within-problem 3.0+-1.0). **Trimming and filtering HURT** (5.1/3.5, up to 4.8/5.3). Don't add trimming.

## 7. THE C.8/C.9 COUPLING — the real argument for recalibration
- C.8: across two NOMINALLY IDENTICAL campaigns on fixed infrastructure, **alpha moved 1.0%**
  (0.6306->0.6243) but **beta moved 28%** (53ms -> 38ms).
- C.9: at strict percentiles **beta is the DOMINANT lever**. Reducing beta 0.0498->0.0344s collapses
  baseline p10 pass@1 from **38.8% to 1.2%**. Reason: "the intercept is the larger perturbation in the
  fast-reference regime"; pooled median duration 0.099s, only 6.87% > 1s.
**The parameter that drifts most under nominally-unchanged conditions is the parameter the strict
metric is most sensitive to.** That is far stronger than "Spearman 0.54->0.96".
HONESTY NOTE: C.9 bottom panels show stricter calibration WIDENS the optimization-RL advantage
(45%->141%->233% as beta tightens) because the baseline loses its top decile faster — so
miscalibration in the strict direction INFLATES apparent wins. Record the bias direction.
Affine fit itself: alpha=0.6306, beta=0.0529s, R2_CV=0.993, 1,369,381 pooled obs from 26,675,153 raw
pairs, leave-one-PROBLEM-out. Multiplicative-only reaches only 0.900 — the 53ms intercept is the point.

## 8. TRANSFER TO GPU KERNEL TIMING — honest, per mechanism
TRANSFERS WELL: Appendix A regime argument (eps_add maps to kernel-launch + host-dispatch, arguably a
  BETTER fit than CPU; conclusion "fix the workload regime before tuning any threshold" is
  regime-independent; generalises our own intake-664 finding).
TRANSFERS WELL: timeout -> win-rate / per-shape percentile aggregated by plain mean.
TRANSFERS WITH REAL RISK: affine drift correction. Their alpha/beta was fit across one runtime on one
  CPU fleet where a fleet change plausibly IS global scale+offset. A ROCm/LLVM codegen change on gfx90a
  is frequently NOT affine — it can alter register allocation/occupancy for one kernel and not another.
  BUT the paper hands us the exact test: leave-one-KERNEL-out CV across a ROCm epoch boundary.
  High CV R2 -> adopt. Negative CV R2 -> cross-epoch results are unrecoverable and must be re-executed
  (also decisive). **Carry the PROTOCOL and the FALSIFICATION CRITERION, not alpha=0.6306.**
PARTIAL, GATE WEAK FOR US: robust CV >= 0.3. Their definition is spread across TESTS within a problem,
  deliberately NOT across candidate solutions — they feared bias from an incidental human solution pool,
  **a concern that does not bind us since we generate our own variants.** Given bandwidth-bound decode,
  duration is near-linear in bytes moved, so any sweep spanning ~0.5x-8x of working set passes 0.3
  trivially. Necessary but NOT sufficient => compute BOTH forms; the across-VARIANT spread is the
  discriminative one.
DIRECTION ONLY, NOT EVIDENCE: the 41.2pp / negative-R2 pair. Their contention mechanism (general-purpose
  Linux node running inference + orchestration + logging + sandbox on the same cores) differs in KIND
  from MI210 co-residency (one device, kernels serialise per stream, dominant risk is a second
  llama-server holding HBM + host-side launch-thread contention). Import as an explicitly-labelled
  EXTERNAL CPU-process-wall-clock result. Overclaiming here is exactly the gate-scope error our own
  entry warns about.
DOES NOT TRANSFER: binary > bucketed > continuous. Mechanism is gradient-specific ("before it reaches
  the gradient steps"); our loop has no gradient, and a binary speed signal destroys the magnitude a
  hill-climbing search needs. => DECLINE the entry's "test coarse buckets" action as filed.

## 9. OTHER CORRECTIONS
- 2605.28751 shares **4 of 5 authors, not 3** (Chambon, Zheng, Decugis, Synnaeve; only Sagot absent).
  Non-independence STRONGER than filed. Cited twice in load-bearing positions.
- credibility 4 UNAFFECTED: the corroboration came from intake-949 (Afterburner) and intake-950 (PIE),
  both disjoint.
- Claim 1 qualifier is load-bearing: "+0.6pp does nothing" is true only on the BASE test regime;
  on OPTIMIZATION tests the same naive reward gives +3.2/+3.4 at p30 (Table 24).
- Simulator ceiling (Table 45): diagnostics NON-PREDICTIVE at p100 (all p>0.11); only predictive at
  p30 (deviation -0.832, quality-corr 0.787, steepness 0.723); variance-around-trend USELESS everywhere
  (r_s=-0.002, p=0.994). Authors: "still unclear whether offline diagnostics can reliably rank the
  remaining viable configurations."
- **This paper repeats the already-overturned SWE-fficiency 4.1% Sonnet figure in Sec 1 AND Sec 7.
  Do not quote it.** (Overturned at ingest by intake-953.)
- Minor internal inconsistency: C.7 variance decomposition sums to 0.02933 vs stated total 0.02994
  (~2% unaccounted). Doesn't affect the 97.1% conclusion; flag so we don't propagate false precision.
- NO independent evaluation/replication/criticism exists (paper is 6 days old). Only a secondary
  tech-press restatement with a garbled figure ("up to 64%") — explicitly NOT a source.

## 10. C.4-C.6 FALLBACK POLICY (novel, portable)
Rule: a locally-recovered success on a TIMING test is reclassified as a TIMEOUT at the limit; on a
CORRECTNESS test the local verdict is kept as pass/fail but its DURATION IS NEVER IMPORTED.
Rationale (C.4): "a local rerun under different pressure can return a FASTER time for a generation that
was WORSE on the real backend — importing that local runtime would reverse the signal."
Eq.9 exposure: P(fallback)=1-(1-f)^n; at f=0.1%, n=150 => **13.9% of rollouts touch fallback**;
at f=2%, n=30 => 45.5%. Alternatives costed and rejected: discarding affected trajectories loses ~80%
of data at f=2%/n=80 AND biases toward smaller test suites.

## LEDGER: 9 drafts, 1 decline, 1 no-change
Owners: autokernel-research-loop.md (x4), rocm-verify-profile-backend.md (x3),
mi210-kernel-rnd-loop-proposal.md, architect-model-selection-bench.md, MEASUREMENT.md Sec 6a hook
DECLINE: "test coarse buckets against continuous throughput deltas" — gradient-specific mechanism.

## DIVE-SURFACED SOURCES (8; top candidate is a strong independence test)
- **arXiv 2607.27271 RLPF** (Jing/Cui/Hu/Song, 2026-07-29) — FULLY DISJOINT authorship, contemporaneous
  (one day later), no Meta/FAIR, different benchmark (PerfCodeBench), STAGED correctness-then-performance
  reward = an INDEPENDENT instance of gate-correctness-before-speed. Would convert intake-939's headline
  reward result from single-group to CORROBORATED. Reports 11.1%->54.6% correct-and-runnable,
  8.1%->38.6% relative efficiency. **HIGHEST-VALUE STAGE-2b CANDIDATE FROM THIS DIVE.**
- arXiv 2512.21326 (Sida Wang, "Measuring all the noises of LLM evals") — directly relevant to
  MEASUREMENT.md; we don't bootstrap variance at all. CAVEAT: Wang is Meta FAIR => methodology source,
  NOT independent corroboration.
- arXiv 2606.16062 (Auditing Reward Hackability in Code RL Envs) — 28.5% of SWE-bench Verified accept a
  Docker-verified INCORRECT patch; bears on C6.
- arXiv 2406.06647 ENAMEL (ICLR 2025) — RIGHT-CENSORING + eff@k; a technique we hold nowhere and the
  natural instrument for kernel timings hitting a wall-clock cap.
- arXiv 2404.18864 (Performance-Aligned LLMs) — correctness-gated CONTINUOUS speedup reward from a
  disjoint group = the counter-case to binary-beats-continuous.
- arXiv 2506.05817 CodeContests+ — nearest OPEN substitute for the unreleased test-construction half.
- (already ours) intake-954 COFFE — counter-based ranking as the alternative to wall-clock.
- cryptobriefing.com coverage — EXPLICITLY NOT A SOURCE, recorded so a future pass doesn't mistake it.
