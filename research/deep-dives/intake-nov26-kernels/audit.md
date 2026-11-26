# rrrrr4788/skillsbench-lift-reanalysis

PARTIAL at eef0fae38200676cee61ae345a057793bb668b78. Read README, split runner, frozen base/task/null/split tables and paper methods/results. No fresh controlled run or upstream raw trajectory inspection. Cutoff/max-gain/risk-averse gates +2.92/+2.95/+2.12 pp in replay, +4.5/+6.5/+5.7 pp shuffled, +0.12/−0.01/−0.33 pp held-out, all three CIs crossing zero. 219 of 1,421 cells are excluded from holdout and retrospective choices saw the full snapshot. Draws reuse records. Separately the decision-selected apparent-loss subset retains −9.93 pp [−16.80, −2.66] held-out. This does not establish harm per task or a beneficial policy.

[Primary source](https://github.com/rrrrr4788/skillsbench-lift-reanalysis)

## Evidence checked

- The archived runner holds one trial per condition out in every eligible cell. (reanalysis/skillgate_checks.py:L635-L643 @ eef0fae).
- The archives include a task table and 72,120 forest scores. (README.md:L25 @ eef0fae).
- The authors report no significant held-out benefit for the tested gating strategies. (paper/main.tex:L283 @ eef0fae).

## EPYC applicability

Hardware-independent statistical control. Upstream raw trajectories and review exports are external.

reanalysis/skillgate_checks.py:L620-L647,L657-L712; reanalysis/results/{base,null,split,tasks}.json and paper/main.tex:L246-L288,L322-L328 @ eef0fae. handoffs/active/eval-tower-program.md:L3206-L3214 @ a660ead and epyc-orchestrator scripts/autopilot/paired_stats.py:L310-L370 implement rerun control; SkillBank is downstream. (EPYC root a660ead17).

## Counterevidence and limits

Beyond Gain reports a different unaided-capability policy with a validity screen and no detectable reward cost on SkillsBench. Different policy, compatible with the audit. The audit fixed-policy CI is not an equivalence proof and its apparent-loss subset limits blanket claims.

## Derived action for review

Apply precommitted held-out policy and within-cell shuffled calibration at any SkillBank promotion. Freeze model/task/harness and thresholds, use disjoint tasks or new trials, archive per-trial decision/reward/graded/invalid/abstention denominators, compare always-load versus gate with existing paired and rerun logic, and predeclare minimum benefit and shuffle separation.

handoffs/active/eval-tower-program.md

## Sources surfaced

https://arxiv.org/abs/2610.32322 independent retirement control only if unindexed. https://github.com/SIMONLQY/SkillGate trains an RL routing policy; expand only for that separate design.
