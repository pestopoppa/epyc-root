# arXiv 2607.01211 — impact on the EffiBench-X adoption decision (2026-08-12)

**VERDICT: SUPPORTS-WITH-CAVEATS** for the "Adopt EffiBench-X as the efficiency instrument,
Python-only, DATED-308" row in `handoffs/active/architect-model-selection-bench.md` (Instrument
selection). It does **not** pre-empt: the paper audits only the repo-level trio (GSO, SWE-Perf,
SWE-fficiency) and never evaluates EffiBench-X, ENAMEL, EvalPerf, COFFE or Mercury (intake-1104#00).
Paper: "Are Performance-Optimization Benchmarks Reliably Measuring Coding Agents?" (Chen, Sun, Shi,
Lo, Jiang — SMU/SJTU; zero author overlap with the Du lineage, see intake-1104#record notes).

## Load-bearing claims

1. **No EffiBench-X defect surfaced** — out of the audit's scope entirely (intake-1104#00). Our
   acceptance-gate findings (fail-open-to-0.0, is_passed inflation, openjdk image, import time, 2
   bad canonicals) remain the complete known defect list; nothing here adds to or contradicts them.
2. **DP-2 independently corroborated, out-of-lineage** (intake-1104#05): SWE-fficiency's harmonic
   mean with a 0.001 failure-floor lets its worst-10 tasks carry 58.5–82.8% of the score
   denominator; one clamped task (raw SR 0.00134) carries 33.6% of a submission's weight; a
   bounded-penalty diagnostic changes 6/8 ranks. Strongest quantitative evidence on record for the
   working convention "harmonic_mean over correct-only, sentinels FORBIDDEN".
3. **Rankings are scoring-rule-dependent** (intake-1104#04): official GSO vs SWE-fficiency rankings
   disagree on 9/28 pairwise comparisons over identical submissions — supports the operator's "one
   ranking key, three columns" shape (publish the key, expose correctness and the conditional).
4. **Replay validity is signal-magnitude-bound, not repetition-bound** (intake-1104#02, #03):
   SWE-Perf's own 20-rep + IQR + Mann-Whitney gate still leaves 129/138 reference patches without
   cross-machine support because its median signal is −0.03%. Reinforces (i) our gate's "timing is
   acceptance-grade, not ladder-grade" flag and (ii) the standing decline of an efficiency axis
   over SWE40/LCB (≤3.8% duration-spread clearable, intake-976).

## Must travel into the adoption/decision rows

- **GSO row (llama-cpp-python tasks)**: from the paper's released data, NEITHER task is among GSO's
  39 replay-valid (intake-1104#06): `218d361` reference patch fails to apply anywhere (0/12);
  `2bc1d97` base fails on EPYC Milan 3/3 (valid 3/3 on EPYC Turin, 1.97–2.02×). Local
  re-verification of both base commits + GSO's ≥1.2 rule is now a precondition of that arm.
- **SWE-Perf decline note** (":its statistical gate is kept"): keep the gate but carry
  intake-1104#03 — the gate is necessary, not sufficient, when the signal is near zero.
- **EffiBench-X ladder, when live**: publish per-task score weight + a per-task duration-spread
  column beside the DP-2 harmonic mean (intake-1104#08) so rank gaps are attributable.
- Declines for Mercury/SWE-Perf/SWE-fficiency-images stand — nothing here reopens them.
