# HARBOR: Automated Harness Optimization

**Intake**: intake-2659 · **Verification**: dive-verified · **Read depth**: FULL · **Source**: https://arxiv.org/abs/2604.20938

## What the dive found

2026-11-06 Stage-2 dive (read_depth FULL; arXiv 2604.20938v1, 14 pages). The formulation is competently stated but the evidence does not support the attribution role it was recruited for. HARBOR's best pick ties the manual peak (17/89 vs 17/89); the mean of five picks is 16.6/89 vs a 15/89 baseline (+1.6 passes, inside a corrected +/-5.9-pass 90% interval); there is no random/grid/TPE control; and the solver is warm-started from the manual A-D log it is compared against. The only +5 is against a manual config BELOW baseline. The search budget is unauditable: 3.5 units, 9.826 units, ~1.71 equivalents and ~5.2 from wall clock cannot all describe the same run, and the unit is never defined. The one experiment that would separate 'search found good flags' from 'the flags were already known-good' (single-flag pass counts, Table I) is defined and withheld, while the authors concede the pick reduces to compression-only. Its Oracle gap (17 vs 81 of 89) is an argument FOR conditional selection, i.e. for a decision graph, not against one. Second-reader note: arithmetic in reported_results (7.49x/7.67x) is dive arithmetic from printed endpoints, not a quoted figure.

## Claims and corrections

- claim 0: **narrowed** — The formalisation is Bayesian optimisation, but the evaluated artifact replaces its three defining pieces: ridge for SAAS+NUTS, a linear tensor-product kernel for the Matern-5/2 prior, and per-candidate EHVI for joint qNEHVI (p.9 VII-e). The reported numbers test a reduced solver, not the section-VI spec.

- claim 1: **narrowed** — The abstract's five names map onto nine section-III flags, not five: context compaction is two flags (tiered compressor + ACON gate), speculative tool prediction is PASTE, and self-evaluation and Reflexion are also flags.

- claim 2: **overturned** — The accounting does not close: five m=89 evaluations alone exceed the stated 3.5-unit budget; 19 m=8 evaluations = 152 task-runs = 1.71 m=89-equivalents, not 9.826; wall clock implies ~5.2 units. The unit is never defined. Payoff is not established: mean 16.6/89 vs baseline 15/89 (+1.6, inside the corrected +/-5.9 noise floor), a TIE with the manual B peak at 17/89, and the only +5 is against D (12/89), which is below baseline. The solver is warm-started from the manual A-D log it is compared against.

- claim 3: **narrowed** — No grid, random, TPE or Hyperband control exists anywhere in section VIII or Appendix A; the only comparators are all-flags-off, two manual configs and the oracle. One run per config, no repeats, no seeds. The paper's +/-3-pass Wilson half-width is the ~68% value; the correct 90% width is +/-5.8 to 6.1 passes, which puts the reported gaps inside noise. The separating single-flag ablation is defined (Table I) but its pass counts are never reported.


## Anchors

intake-2659 carries 9 verbatim claim anchors; see `research/intake_index.yaml` for quotes, locators and hashes.


## Actionables

Stage-3 plan: `research/intake-stage3-plan-2026-11-06-harness-inference.md`.
