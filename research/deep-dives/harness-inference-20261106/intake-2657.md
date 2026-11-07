# Reuse, Rewrite, or Reject: Evidence-Constrained Trace Reuse for Repeated Mobile GUI Control

**Intake**: intake-2657 · **Verification**: dive-verified · **Read depth**: FULL · **Source**: https://arxiv.org/abs/2610.31712

## What the dive found

2026-11-06 Stage-2 dive (read_depth FULL; arXiv 2610.31712v1, 21 pages). The mechanism claim survives intact; the number sentence is OVERTURNED by a denominator swap. On AndroidWorld tokens fall 78.0-89.6%, reuse is 82.0-87.5% and speedup is 1.2-1.9x (3/5 agents >=1.5x, none at 2x); the 70.7-79.8% reuse and 2-4x multipliers are the real-device blocks. The speedup is honest wall-clock (end-to-end, matched boundaries) but averaged only over pairs where BOTH arms succeeded, with no variance, no per-cell N and no host description. Two success columns are constructed products, not measurements: AndroidWorld 'success with replay' is base x conditional (stated unable to exceed base), and the real-device column is an arithmetic product whose measured counterpart is 93.0-98.0%. The paper's own explanation of the modest AndroidWorld result is the transferable datum: pre- and post-action UI acquisition is 40.02% of wall-clock, which is why removing model calls yields only ~1.5x. The admission gate is a three-group checklist, not a certificate. Second-reader pass (2026-11-06): the three-group enumeration used in claim 2 is rendered in Figure 3 and section A.4 but no single anchor quotes the enumeration; cite the groups as derived from the figure, not as a quoted list.

## Claims and corrections

- claim 0: **unaffected** — Mechanism confirmed (p.1, p.5 Fig. 3). Two additions: the decision space is three-valued (REUSE / REWRITE / REJECT), and the memory unit is a transition with a checked outcome, reused locally rather than as a whole-script replay.

- claim 1: **overturned** — The sentence merges two evaluations. On AndroidWorld (Table 1, Table 8) tokens fall 78.0-89.6%, reuse is 82.0-87.5%, and speedup is 1.2-1.9x with 3/5 agents >=1.5x and 0/5 >=2x (mean 1.54x). The 70.7-79.8% reuse and 2x+ multipliers belong to the REAL-DEVICE blocks (1.8-3.9x), not AndroidWorld. 'Approximately 80% on average' is the authors' aggregation and is not a reported mean.

- claim 2: **unaffected** — The admission gate is a three-group checklist (context alignment; input contract; safety + observability) plus pre-check/post-check/fallback and record-time exclusions - NOT a certificate: no numeric risk bound, no evidence threshold, no bound tool receipt. Contrast intake-2652's six-field omission certificate.


## Anchors

intake-2657 carries 10 verbatim claim anchors; see `research/intake_index.yaml` for quotes, locators and hashes.


## Actionables

Stage-3 plan: `research/intake-stage3-plan-2026-11-06-harness-inference.md`.
