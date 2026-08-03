# 2b-E — arXiv 2607.27271 (RLPF) — the independence test for intake-939

## HEADLINE: PARTIAL — and the KIND matters. The corroboration is ARCHITECTURAL, NOT EMPIRICAL.
RLPF is a genuinely independent group that independently arrived at a correctness-gated staged reward,
and its RELEASED CODE implements a strictly separated outer gate. Real convergent-design evidence.
**BUT: every reward arm RLPF tested is correctness-gated. There is NO blended arm and NO ungated arm
anywhere in the paper or the code.** RLPF therefore CANNOT show that gating beats blending — it never
ran the comparison. Its ablations test WHICH GATED TERMS matter, not WHETHER THE GATE matters.

## TWO FURTHER MATERIAL FINDINGS
1. **RLPF's design CONTRADICTS intake-939's WINNING arm.** 939's winner was the COLLAPSED CONJUNCTION
   (correct-but-slow -> full failure reward). RLPF explicitly and deliberately does the OPPOSITE:
   `epsilon = 0.05` exists SOLELY to guarantee every correct program outranks every failed one.
   RLPF is the TWO-GATE/OUTER-GATE family — **939's RUNNER-UP** — in a strictly stronger form.
   => Two capable groups, OPPOSITE CHOICES within the same family.
2. **RLPF's "runtime-only" baseline is NOT 939's "optimization-only" arm.** The code comment is
   explicit: "CRR (correctness gating) is preserved by the `not correct` branch above." It is a GATED
   continuous speed reward, and it did NOT collapse (37.9% CRR vs 11.1% base).
   **939's collapse-to-0.0 claim receives NO independent test here.**

## INDEPENDENCE: CONFIRMED (authorship) — BUT A DEPENDENCY THE BRIEF DID NOT ANTICIPATE
Authors: Jing, Cui, Hu, Chen, Shi, Fan, Liu, Yang, Zhang, Chen, Li*, Song. HKUST/NYU/SWUPL/HKU/MODEIO.AI.
ZERO overlap with FAIR (Synnaeve/Zheng appear only as authors of a CITED work, RLEF). ZERO overlap with
the Afterburner group. Does NOT cite 2607.25970. Submitted 2026-07-29 vs 939's 2026-07-28 — one day
apart, mutual citation IMPOSSIBLE. 7 shared references = convergent on the same problem, not derivative.
**BUT PerfCodeBench IS THE AUTHORS' OWN BENCHMARK** (Jing et al., arXiv 2605.15222) — **7 of its 8
authors are also RLPF authors, including the same first author.** RLPF trains on it, evaluates on it,
and draws EVERY headline number from it. Same non-independence pattern as intake-949/952 (Mingzhe Du),
and it MIRRORS 939's own weakness (DMC-Optim is FAIR's self-built corpus).
**BOTH papers' headline numbers rest on self-built, externally-unrun corpora.**
Only external instrument touched: EffiBench-X, +3.9% geometric-mean ET / 57.9% win rate, and the paper
states plainly the table "does not establish statistical significance."

## THE REWARD, EXTRACTED AND CODE-VERIFIED
Success: FBR = C*1[T_c<T_b]; RBR = C*1[T_c<=T_r]; CGRE = C*clip((T_b-T_c)/(T_b-T_r),0,1);
         R_succ = CGRE + 0.16*FBR + 0.10*RBR
Failure ladder (939 has NO analogue): s(NX)=-0.05 < s(NC)=0.00 < s(NR)=+0.05 < s(WO)=+0.10
Final: R = s(sigma) if incorrect; else max{s(WO) + eps, R_succ}, eps=0.05
Verified in released code/reward.py: `reward = max(reward, shape_wrong_output + 0.05)` with the comment
"epsilon = 0.05 creates a strict gap above s(WO)=0.10, so every correct program scores at least 0.15".

## THE ABLATION TABLE (n=306, ONE SEED, no CIs)
RLPF full 54.58 CRR / 46.41 FBR / 25.82 RBR / **14.97 Slow-CRR** / 38.58 CGRE
w/o FBR 40.52 | w/o RBR 39.87 | w/o shaping 39.54 | runtime-only(GATED) 37.91
**RLVR correctness-only 50.00 CRR but Slow/CRR 36.60** | Qwen3-32B base 11.11
WHAT IT ESTABLISHES WELL: at near-matched correctness, correctness-only training leaves **36.6% of its
correct programs no faster than baseline vs 15.0% for RLPF**. On the paper's own transition counts
(+58/-13), McNemar chi2 ~28.5, **p<0.0001**. That leg is ROBUST.
WHAT IT DOES NOT: the CORRECTNESS leg is marginal (+34/-20, McNemar **p~0.06**). The three component
ablations differ by 1-2 tasks out of 306 — statistically indistinguishable, and the authors say so:
"Point estimates favor the full reward but cannot establish component necessity."

## PAPER/CODE DISCREPANCY — THE SMOKING GUN
Eq. 2 defines RBR = 1[T_c <= T_r]. Released reward.py applies an **UNDOCUMENTED `rbr_tolerance = 0.02`**
(`t_model <= t_ref * 1.02`). The code comment attributes it to timing noise that "can push a candidate
that is literally the reference source over t_ref by a few microseconds."
**The authors OBSERVED the hazard at the threshold, PATCHED IT WITH A 2% FUDGE, and did NOT report it.**
All published RBR figures carry 2% slack Eq. 2 does not state. It is a measured admission that their
harness cannot resolve sub-2% differences — while CGRE, the headline metric, is a CONTINUOUS function
of exactly those differences.

## MEASUREMENT: IT INHERITS THE TIMING HAZARD ALMOST COMPLETELY
- Reward execution runs ON THE SAME BOX as 32B GRPO rollout generation. CUDA tasks timed on the TRAINING
  GPUs. No isolation, no taskset/numactl, no affinity, no quiescing anywhere in the harness.
- Measure-ONCE during training; median-of-3 at eval only.
- **Fresh candidate timing / DISK-CACHED baseline timing, zero drift correction**
  (`PERFCODEBENCH_USE_BASE_REF_CACHE` defaults TRUE, `USE_CANDIDATE_CACHE` defaults FALSE).
  This is PRECISELY the stored-vs-fresh comparison 939's affine recalibration exists to fix.
- No duration-spread admission gate. No CV screen.
- Real partial mitigation: CGRE is a RATIO normalized by the task's own (T_b - T_r) gap, cancelling a
  multiplicative environment factor. But 939's Appendix A shows the ADDITIVE term does NOT cancel in a
  ratio and dominates for fast tests — most of this suite outside the OpenMP/CUDA tail.
NET: RLPF's LARGE effects (101x, 51x, median 4.77x) survive. Its threshold metrics near parity, and any
future use of this harness to rank CLOSE variants, do not.

## ARTIFACTS
Code github.com/HKUST-KnowComp/RLPF, 4 commits, 1 star, **NO LICENCE FILE** — README: "A standalone
license has not yet been added." Weights on HF. **Benchmark tasks NOT in the repo.**
Compute: 597 GPU-hours (74.6h x 8 A800-80GB) for the full run; ~4,000 GPU-hours for the reported study.

## PerfCodeBench AS A FIFTH INSTRUMENT: NOT YET. TRACK, DON'T ADOPT.
1,854 executable performance tasks (train 1413 / val 135 / test 306, family-disjoint). Each supplies a
fixed interface, a BASELINE implementation, an EXPERT-OPTIMIZED reference, a correctness oracle and a
harness. Languages: C++ 1087, Java 176, C 162, Go 160, Python 144, **CUDA 125**.
ATTRACTIVE: the ONLY member of the cluster with genuine SYSTEMS content (OpenMP atomics, SIMD string
processing, bitmap filtering, packed integer decoding, CUDA reductions/scans/tiled transpose) and the
only one supplying BOTH a baseline AND an expert reference per task — which is what makes a normalized
gap-closure metric possible. Much closer to MI210 kernel work than LeetCode-style tasks.
FAILS THE BAR TODAY: not independent (same group); NOT RELEASED (only an anonymous.4open.science review
link; no licence); **CUDA is 5.2% of the test split (16/306) and is NVIDIA-only (`_detect_nvcc()`), no
ROCm/HIP path**. Re-check in ~60 days.

## EFFECT ON intake-939 — no credibility change; ONE CLAIM MUST BE NARROWED
- credibility 4 UNCHANGED. Its +2 came from intake-949 and intake-950, both disjoint. Adding RLPF would
  DOUBLE-COUNT a corroboration that is architectural only. Ceiling reached regardless.
- **NARROW key_claim 6.** Currently "Correctness must gate the speed signal as an OUTER gate; additive
  or blended reward is actively harmful, and a pure-speed objective collapses the policy outright."
  (a) "as an OUTER gate" was ALREADY wrong per DIVE-E — 939's own winner is the CONJUNCTION. RLPF now
      makes the stakes concrete by independently choosing the outer gate and REJECTING the conjunction
      BY DESIGN. Rewrite to the property both share: "No speed credit for an incorrect candidate.
      WHICH gate form is best is UNSETTLED — 2607.25970 Table 3 favours the hard conjunction;
      2607.27271 Eq. 6 independently chose a strictly-separated outer gate and never tested the conjunction."
  (b) "additive or blended reward is actively harmful" — UNCHANGED, still single-group.
  (c) "a pure-speed objective collapses the policy" — still single-group, AND NOW NEEDS A GUARD so no
      future pass mistakes RLPF's gated "runtime-only" arm for it.
- **STRENGTHENED FROM A DIFFERENT DIRECTION.** 939's test-suite claim (robust CV >= 0.3 satisfied for
  <=3.8% of problems with original tests vs 48.2% with purpose-built ones) now has GENUINE INDEPENDENT
  EMPIRICAL CORROBORATION — not from RLPF, but from **arXiv 2607.07619** (Le, Xu, Wang, Chen), which
  RLPF cites in its Limitations. Different group, different method (30 reps/task + statistical testing
  across EffiBench, Enamel, EvalPerf, Mercury; 1,538 tasks), same conclusion: **only 6.11% of purportedly
  performant reference implementations show a statistically significant improvement on the ORIGINAL
  tests**, and purpose-built performance tests raise detection to 24-25%.
  **That is the strongest corroboration this dive produced — and it is for a DIFFERENT 939 claim than
  the one we set out to test.**

## PROPOSED NEW ENTRY: intake-957, arXiv 2607.27271
novelty medium · relevance high · credibility 3 · verdict **adopt_patterns**
(adopt_component BLOCKED: no licence file; benchmark tasks not in repo)

## LEDGER: 4 ADOPT, 1 ADOPT-as-evidence, 1 PROPOSE, 3 DECLINE/DEFER
1 **eps-separated staircase** as MI210 loop fitness -> ADOPT (reward.py is a working reference impl)
2 **PRE-CORRECTNESS PROGRESS LADDER** -> ADOPT. **HIGHEST-VALUE TRANSFER IN THIS DIVE.** Our loop
  currently treats ALL non-verifying kernels as EQUAL failures; ranking hipcc-fail < runtime-fail <
  wrong-output gives a SEARCH GRADIENT in the regime where most MI210 candidates die. 939 has no analogue.
3 **CGRE normalized gap closure** (T_base-T_cand)/(T_base-T_ref) -> ADOPT. **CLOSES THE GAP DIVE-C/E
  LEFT OPEN**: DIVE-E DECLINED 939's binary/bucketed finding as gradient-specific and harmful to
  hill-climbing; RLPF supplies the CONTINUOUS form a search actually needs.
4 **Slow/CRR conditional diagnostic** for architect-model-selection-bench.md -> ADOPT (among a model's
  CORRECT outputs, what fraction is no faster than baseline — separates correctness inflation from
  genuine efficiency gain)
5 RLPF's harness as a NEGATIVE EXAMPLE for our timing discipline -> ADOPT AS EVIDENCE. An independent
  group shipped the uncorrected fresh/cached form. Cite in MEASUREMENT.md era handling.
6 log `rbr_tolerance = 0.02` as a MEASUREMENT ANTI-PATTERN -> ADOPT. **Grep released code for
  undocumented tolerances before trusting any threshold metric.** New instance of a known defect class.
7 re-run 939's "WHICH gate form" question on our own loop via the offline-replay screen at ~zero GPU
  cost -> PROPOSE, needs operator approval, autokernel-research-loop.md
8 train/fine-tune anything from RLPF -> DECLINE (597 GPU-hours on 8xA800; inference-only host)
9 adopt PerfCodeBench -> DEFER ~60 days (no licence, anonymous link, nvcc-bound, CUDA 5.2% of test split)
10 use RLPF as EMPIRICAL corroboration that gating beats blending -> **DECLINE. The comparison does not
   exist in the paper.**

## FURTHER SOURCES SURFACED
- **arXiv 2607.07619 "Rethinking Code Performance Benchmarks for LLMs" (Le, Xu, Wang, Chen) —
  HIGHEST VALUE OF THIS DIVE.** Independently corroborates 939's duration-spread claim by a completely
  different route. 4 benchmarks, 1538 tasks, 30 reps each + statistical testing -> only **6.11%** of
  "performant" references are significantly faster; 209 of 308 manually-analysed non-significant cases
  contain REAL improvements the ORIGINAL TESTS FAIL TO EXPOSE; their generated performance-oriented
  tests reach 24-25% detection. RECOMMEND IMMEDIATE STAGE-2b DIVE.
- arXiv 2605.15222 PerfCodeBench — the instrument behind every RLPF number
- arXiv 2602.17684 CodeScaler — learned reward models to REDUCE RELIANCE ON ONLINE EXECUTION, which
  directly addresses our most expensive constraint (serial MI210 measurement)
- arXiv 2605.28409 Offline RL for code gen — the cheap-compute branch
- arXiv 2601.14523 LLM-Powered Evolutionary Code Optimization on a Phylogenetic Tree — train-free
  evolutionary search over code variants; STRUCTURALLY THE CLOSEST PUBLISHED ANALOGUE TO OUR MI210 LOOP
- arXiv 2604.05137 EffiPair — relative/contrastive efficiency feedback WITHOUT absolute timing, a
  possible route AROUND the timing hazard
- arXiv 2601.11895 DevBench; arXiv 2510.18471 CodeRL+
- **ALREADY INDEXED, ACTION NEEDED: intake for arXiv 2505.11480 (SuperCoder).** RLPF describes it as
  comparing "correctness-guided speedup with a speedup-only reward" — a potential THIRD independent
  instance of the gating comparison, and **the only one that may contain the UNGATED ARM both RLPF and
  939 lack.** RECOMMEND CHECKING WHETHER THAT SPECIFIC ABLATION WAS CAPTURED DURING ITS INGEST — it may
  be the empirical corroboration this dive was looking for and did not find.
