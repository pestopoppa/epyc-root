# C2 champion CAS: waiver of predeclared rule 1 (2026-10-23)

## Decision

On 2026-10-23 at about 07:15Z the operator chose "Advance C2 by waiver" through a decision question put by coordinator session 3c4ca599. Candidate C2 (`experimental/c-plus-nemotron-bolt-20261021` @ `49550eda5`) was then advanced to champion.

## What was waived

Only **rule 1** of the predeclared Q38FN CPU re-run rule (`/mnt/raid0/llm/tmp/c2-regate-20261021/PREDECLARED_b_rerun.md`, sha verified before use), for the two re-run attempts below. Rule 1 is the validity gate on the anchor arm (anchor CV at most 6%, and for run 3 a median floor of 45). Rule 2 was not waived: both runs passed it. No other gate was waived or relaxed.

## Evidence

| Run | Anchor (champion `dd3d9721c`) | Candidate (C2) | Effect | Candidate slower | Rule 1 | Rule 2 |
|---|---|---|---|---|---|---|
| Run 2, `runs/b-rerun-20261022T165626Z` | median 50.46, CV 6.5% | median 50.63, CV 2.8% | +0.34% | 4 of 12 pairs | INVALID: anchor CV above 6% | pass |
| Run 3, `runs/b-rerun-20261023T062543Z/compare-q38fn.json` | median 41.47, CV 8.4% | median 42.38, CV 2.9% | +2.17% | 1 of 12 pairs | INVALID: medians below 45 and anchor CV | pass |

Reasoning recorded by the operator's decision: in both runs the anchor arm's own dips (40.2 / 43.9 in run 2; 32.0 / 33.1 in run 3) are what break the CV gate while the candidate stays stable. In run 3 a host-wide slowdown of about 18% hit both arms equally. The sign of the effect is non-negative in both runs.

Other gates (`/mnt/raid0/llm/tmp/c2-regate-20261021/C2_CAS_DECISION.md`, section 1): e (GPU 27B A/B) PASS, c identity PASS, nemo PASS, vision PASS.

## CAS

Guarded `update-ref` at about 07:20Z in `/mnt/raid0/llm/llama.cpp`, `refs/heads/ak/champion/llama-cpp-ffc1bac82eec`:

- old: `dd3d9721ca37321ad9159520bbd9616e3d0d6228`
- new: `49550eda5a9c98f4f31b4cdaeeecadb355bbb8c3`

Fast-forward verified (C2 = C `f0c96dc1f` + 7 commits, zero `ggml/` diff against C). `ak-loop-tree` refreshed and clean at `49550eda5`. Store images `kernels/builds/{cpu,gpu}-20261021-49550eda5-c-nemotron` report `llama-server --version` 10411.

Not done: push of the champion ref to the `fork` remote (awaiting operator permission).
