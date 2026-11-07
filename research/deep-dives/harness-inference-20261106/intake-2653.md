# Handoff Debt: The Rediscovery Cost When Coding Agents Take Over Interrupted Tasks

**Intake**: intake-2653 · **Verification**: dive-verified · **Read depth**: FULL · **Source**: https://arxiv.org/abs/2606.02875

## What the dive found

2026-11-06 Stage-2 dive (read_depth FULL; arXiv 2606.02875v2, 17 pages read from disk; venue confirmed as EMNLP 2026 main, pp. 17110-17126, DOI 10.18653/2026.emnlp-main.738, same title and both authors). Direction of the result: structured handoff is not measurably better than a free-form summary - Qwen->Qwen +4.4pp (CI crosses zero, p=0.134) vs +5.0pp, at 660k vs 602k prompt tokens, i.e. structure costs 9.6% MORE. The measured payload is the evidence class: validation evidence at the handoff point is worth +14.7pp and failure evidence +16.1 to +19.4pp, while the changed-files list is worth only +4.0pp (successor can git diff it). No per-field ablation exists; the field list is a template, not a proven ranking. Caveats recorded: 34% of handoff points are 'already solved; preserve' (not takeovers), 181 points nest in 75 tasks and the bootstrap did not cluster, Table 2's prompt-token column is almost certainly a per-run median (the paper never says), wall-clock is collected and deliberately not compared, and an 'event' is an LLM action OR a tool observation, so 99->55 events is roughly 50->27 model calls.

## Claims and corrections

- claim 0: **unaffected** — Design confirmed. Add the nesting when citing: 181 handoff points nest inside 75 source tasks, so the effective N is 181 paired observations, not the 724 runs (181 x 4 views) or 2,172 total across three successors.

- claim 1: **narrowed** — The field list is not the schema. The paper proposes 'changed files, validation evidence, uncertainty, rollback risk, and verification' in the contribution bullet, but the rendered contract (App C) is 7 deterministic fields (repository change state; changed source files; non-source artifacts observed; validation outcome after latest source change; latest predecessor validation command; latest validation evidence; continuation-state label) plus 7 model-filled fields (problem understanding; work completed; evidence observed; observed failures/error evidence; remaining uncertainty; rollback notes; recommended next action). There is no field named 'verification'; it renders as 'rollback notes'.

- claim 2: **unaffected** — Character ordering is exact: raw trace 87k median / 150k P90 / 471k max vs structured 10.0k and summary 9.8k. Raw trace holds the largest solved-rate delta for all three successors (+6.1, +6.6, +14.9 pp, CI-clear), but it is also 811k vs 602k prompt tokens in Qwen->Qwen, so 'largest gain' is not 'best handoff'.

- claim 3: **narrowed** — Numbers are literal but the basis must be stated: -60% and -63% are both against repository-only (1.63M), not against each other. Structured is 660k vs summary 602k, i.e. structure costs 9.6% MORE prompt tokens than free-form summary, and the Qwen->Qwen accuracy difference (+4.4 pp vs +5.0 pp) has a CI that crosses zero (p=0.134). 'Structured beats summary' is not supported.


## Anchors

intake-2653 carries 12 verbatim claim anchors; see `research/intake_index.yaml` for quotes, locators and hashes.


## Actionables

Stage-3 plan: `research/intake-stage3-plan-2026-11-06-harness-inference.md`.
