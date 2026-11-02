# Stage-2b lit dives: selective classification / conformal abstention (ws58-jev)

Read route for all four: arxiv.org/html/<id>vN (LaTeXML) curled to disk, tag-stripped to .txt, read from disk. read_depth: FULL for 1705.08500 (short) and 2307.01928 (main text + appendix proofs skimmed); PARTIAL for 2107.11277 (survey; Sec 1-2, 5, 7 read in depth, application sections skimmed) and 2306.10193 (Sec 1-4, App A/B/C read; proofs and experiments skimmed). Quotes verified as exact substrings of the extracted .txt files (same dir). sha256 over the UTF-8 quote string.

## 1705.08500 Selective Classification for Deep Neural Networks
- Authors: Geifman, El-Yaniv
- Year: 2017 (v2 1 Jun 2017); venue: NeurIPS 2017 (per arXiv; venue not stated in HTML text read)
- Version read: v2 (latest=v2 on arxiv abs page, checked 2026-11-02)
- Route: html 1705.08500v2.html -> 1705.08500v2.txt

| # | quote | locator | sha256 |
|---|---|---|---|
| 1 | "Our method allows a user to set a desired risk level. At test time, the classifier rejects instances as needed, to grant the desired risk (with high probability)." | Abstract | 9e68b0b9b483a06546b634d41d84f6543f9c2b160e206dc74cdd9a9203ed9f42 |
| 2 | "(f,g) whose test error will be no larger than r∗ with probability of at least 1−δ." | Sec 1; Eq (2), Alg 1 (SGR), Thm 3.2 | 4af8d2577b6004d50dcd9948e841d87ea50a5d10aadecc2f8740c40c99cad632 |
| 3 | "While Theorem 3.2 always holds, we note that if κf is severely skewed (far from ideal), the bound of the resulting selective classifier can be far from the" | Sec 4 (footnote 1) | ee174a0024dfae53b59b593b23614dec93a7a2560c1734bb27940821deb39c8a |

## 2307.01928 Robots That Ask For Help (KnowNo)
- Authors: Ren, Dixit, Bodrova, Singh, Tu, Brown, Xu, Takayama, Xia, Varley, Xu, Sadigh + others
- Year: 2023; venue: CoRL 2023 (per arXiv; not stated in text read)
- Version read: v2 (latest=v2 on arxiv abs page, checked 2026-11-02)
- Route: html 2307.01928v2.html -> 2307.01928v2.txt

| # | quote | locator | sha256 |
|---|---|---|---|
| 1 | "In practice, we use a modest-sized calibration dataset (N=400) and δ=0.01, and adjust ϵ^ to achieve the desired 1−ϵ coverage (with probability 1−δ=0.99 over the sampling of the calibration set)." | Sec 3.1, after Eq (2) | 4a0097951403dca74b1ed12cff63adbbb044522158e483d1a627c3ab73f52be7 |
| 2 | "We emphasize that the CP coverage guarantees hold regardless of the accuracy of f^." | Sec 3.1 | f37a41b5ade6db045b202cd5431f22344c286c962248c3b7db179d1bc7997321 |
| 3 | "Another limitation is that, for the task guarantee to hold, the human needs to faithfully provide help when the robot needs it." | Sec 6 Conclusion, Limitations | d7c38873be937ff93900f7b7992f6dd04edf8c8dfd111d249edcc6cce4f407bc |

## 2107.11277 Machine Learning with a Reject Option: A survey
- Authors: Hendrickx, Perini, Van der Plas, Meert, Davis
- Year: 2021 (v3 21 Feb 2024); venue: Machine Learning journal 2024 (per arXiv; not stated in text read)
- Version read: v3 (latest=v3 on arxiv abs page, checked 2026-11-02)
- Route: html 2107.11277v3.html -> 2107.11277v3.txt

| # | quote | locator | sha256 |
|---|---|---|---|
| 1 | "Setting an appropriate rejection threshold τ is crucial for having an accurate dependent rejector. At a high level, the threshold is set in three main ways: using domain knowledge, adhering to user-provided constraints, or tuning it empirically based on some objective function." | Sec 5 Dependent rejector, Learning the rejection threshold | 06377fefd21f07164cee67037fc38d34fabfd72c6e5797a4c318bb25ce63854e |
| 2 | "However, in real-world scenarios, obtaining complete knowledge of class distributions is challenging, limiting the applicability of Chow’s rule (Shekhar et al.,, 2019)." | Sec 5, Learning the rejection threshold (precedes two-threshold Eq 8, Tortorella 2000) | d9f5c4dda580cc8e09b0ab70d7d2c13005d7e7450c19d01b575ba401a58fc980 |
| 3 | "First, when rejectors do not overlap (or when we are not interested in the example’s rejection type), one can simply combine the rejection sets by a logical o​r-rule: reject the example if any of the rejectors rejects it and assign such rejection type" | Sec 7 Combining multiple rejectors | 74747878773cd9b66d1c685d5cae7a0f0d4c5e0df1cdd14f37331cdcd673bc5d |

## 2306.10193 Conformal Language Modeling
- Authors: Quach, Fisch, Schuster, Yala, Sohn, Jaakkola, Barzilay
- Year: 2023 (v2 1 Jun 2024); venue: ICLR 2024 (per arXiv; not stated in text read)
- Version read: v2 (latest=v2 on arxiv abs page, checked 2026-11-02)
- Route: html 2306.10193v2.html -> 2306.10193v2.txt

| # | quote | locator | sha256 |
|---|---|---|---|
| 1 | "Importantly, however, this does not include multi-turn dialogue where successive prompts are dependent, or when there is distribution shift between calibration and testing." | App. A Assumptions (Assumption 1) | 1350c37211654bfff2adcfe4f2230aeabc88a3e35d96d0974c31548a4a3228be |
| 2 | "Unlike conformal prediction, however, λ can be multi-dimensional (e.g., consist of multiple thresholds)." | Sec 3 Background (Learn Then Test), Eq (3) | b3f5fc66d540a6e92c86b6ff45161c9891845045569fe98503b57af73184ac20 |
| 3 | "if kmax, the maximum number of samples drawn, is too low, then many levels of ϵ will be unattainable, and the method will fail to find a valid configuration (it will return null)." | App. B Limitations | f19a7db34fb3647be3a531d2ecd0860c0e0822acf9c28f1f8c792bd7e41e8896 |

## Limitations and minimum calibration sizes
- 1705.08500: assumes i.i.d. calibration sample S_m from the deployment distribution; guarantee is PAC (prob >= 1-delta over S_m), uses the Clopper-Pearson-style binomial tail bound (Lemma 3.1, Gascuel & Caraux 1992) on the accepted subset plus binary search over the threshold. No stated minimum m. Experiments: ~5000 calibration and ~5000 test samples (CIFAR-10), delta=0.001, no Bonferroni across the 6-7 targets. Derived (not stated in paper): with zero errors in n accepted examples the bound is 1-delta^(1/n), about ln(1/delta)/n, so a 2% target at delta=0.001 needs about 350 accepted examples; a 1% target about 700. Risk is selective (accepted-set) error, so coverage is what you pay.
- 2307.01928: the paper states N=400 calibration scenarios, delta=0.01 ("modest-sized"); no stated minimum. Derived: split-CP needs N >= 1/epsilon - 1 just to be non-trivial (epsilon=0.15 -> N>=6), plus Beta slack for the dataset-conditional guarantee. Requires i.i.d./exchangeable calibration and test scenarios; multi-step needs sequence-level calibration since contexts across steps are dependent. Guarantee needs a faithful labeller (human help) and a correct downstream executor; set-size/help-rate depends on score quality, validity does not.
- 2107.11277: survey, no sample-size guarantees. Value: taxonomy (ambiguity vs novelty rejection), threshold-learning routes (rate-targeted, constraint-based, cost-based/Chow), two-threshold reject band (Eq 8, Tortorella) and ordered/or-rule composition of rejectors (Sec 7). Notes Chow's rule needs known class distributions/calibrated posteriors, so it is fragile with estimated posteriors.
- 2306.10193: needs exchangeable/i.i.d. prompts (App. A Assumption 1; explicitly excludes multi-turn dependence and calibration/test shift; weighted p-values mentioned but not evaluated). Learn Then Test (Eq 3) controls risk over multi-dimensional lambda (multiple thresholds) via binomial-tail p-values + FWER-controlled multiple testing (Pareto Testing for >1 dim). No minimum n stated; experiments use 2,000 cal-train + 2,000 cal-val per task; k_max=20. Returns null when no valid configuration exists. Guarantees are marginal, not per input type. Admission function must be reliable (conservative admission is acceptable, Cor. A.1).

## Implications for the agent-harness typed judgment
Setting: two thresholds (category prob, confidence) -> resume / park / done; classify dry-run failures; replay saved inputs to see where a threshold change diverges.
1. Two thresholds = a 2-D lambda. Do not tune them independently by eyeball: LTT (2306.10193) is the one source that explicitly supports multi-threshold lambda with a risk guarantee (test grid of (tau_cat, tau_conf), binomial p-value each, FWER-correct, pick lowest-abstention valid point). The 1705.08500 SGR is 1-D (rank by one confidence); if a single scalar score is wanted, collapse the pair to one rank score and use SGR.
2. Define the risk per action, not overall. The costly error is "done" or "resume" issued wrongly; "park" is the abstention. Control the selective risk on {done, resume} decisions (1705.08500 Eq 1-2) and report coverage = fraction not parked. The survey (Sec 5/7) gives the two-threshold reject band and ordered rejector composition as the design vocabulary; ambiguity (low category prob margin) vs novelty (input unlike calibration data) are different rejections and may need separate gates.
3. Calibration set = labelled saved judgments. Labels must be ground truth (outcome after the fact), not the judge's own output. Exchangeability: the saved inputs must be drawn like future inputs; harness drift, new tools, or multi-step episode dependence (consecutive steps in one run are not i.i.d.; cf. KnowNo sequence-level calibration) break it. Subsample one decision per episode or calibrate at episode level. Recalibrate after prompt/model/tool changes.
4. Sizes: no paper gives a hard minimum; the usable rule is the binomial one derived above: to certify error <= r at confidence 1-delta you need roughly ln(1/delta)/r accepted, error-free-ish examples (r=0.05, delta=0.05 -> ~60; r=0.02, delta=0.001 -> ~350), and per-category slices multiply that. Reference points used by authors: N=400 (KnowNo), ~5000 (SGR), 2000+2000 (CLM). A guarantee is marginal; per-category (e.g. dry-run failure class) validity needs per-class calibration data.
5. Dry-run failure classification: treat it as ambiguity rejection with a "park/unknown" outcome; threshold choice via constraint form (min rejection s.t. error <= M, survey Sec 5) is the right objective. Guarantee holds regardless of classifier accuracy (KnowNo) but a poor score ranking yields low coverage (1705.08500 footnote 1: severely skewed kappa -> bound far from target).
6. Replay: because the SGR/LTT procedures are deterministic functions of (scores, labels, delta, target), replaying saved inputs under a changed threshold gives an exact divergence set; the caveat is that replaying on the calibration set itself is optimistic (threshold selected on it); hold out a test split (1705.08500 Sec 5 halves the validation set for exactly this) before claiming the new threshold's risk.
7. Caution on provenance: the guarantees are PAC/marginal statements about the sampling process; claim tuples should record n, delta, target, split and the exchangeability basis rather than the guarantee itself.
