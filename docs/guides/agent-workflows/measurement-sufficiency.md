# Measurement sufficiency and early stopping

Use this operational guide for long inference and benchmark work. Its purpose is to obtain the information needed for a decision with no unnecessary compute. The measurement constitution and the applicable protocol remain authoritative; this guide does not amend a gate, sample count, scoring rule or trust boundary.

## Before launch

1. State the decision and its scope: what outcome would change the next action, and what conclusion is actually required? Check retained runs, valid controls and deterministic rescoring first. Verify identity, coverage and provenance before reusing evidence.
2. Record a compact stop contract in the handoff or run declaration: question and decision; units and population/strata; controls and matching; the smallest useful coverage; practical threshold with its authority; planned interim looks and uncertainty method; stop, continue and inconclusive conditions; maximum resource/time budget; output, safe stop and resume locations. Use the applicable protocol's required values; do not invent a substitute pass threshold. If no interim decision is valid, say so and retain the required coverage.
3. Arrange bounded, independently preserved units and a safe stop between them where possible. Maintain the cache or other state needed for a valid continuation. Verify the harness writes usable incremental records and identifies failed, truncated and missing units. Make monitoring cheap and ensure a stop cannot launch a successor inadvertently.
4. For inference on a population, choose sampling and uncertainty methods suitable for the design: pairing, dependence within sessions, strata and nonrandom completion order matter. Predeclare a valid sequential method or planned looks with appropriate error control when a formal statistical claim requires it. Ordinary confidence intervals repeatedly inspected until favorable are not automatically valid. A simple early descriptive comparison can still guide an operational decision when labeled accordingly.

## During the run

At planned looks, inspect the actual usable observations, denominators, coverage, failures, controls and any relevant drift. Preserve the exact records and identities underlying each decision. Stop as soon as valid evidence settles the scoped decision or a predeclared futility condition applies; continue if more units could materially change the decision and are required. Stop a user-directed run at the requested boundary. A timeout, crash or resource eviction is an interruption, not an evidence-based decision.

Distinguish these outcomes in the record:

- **Gate satisfied or failed:** only when the authoritative protocol permits that verdict and its applicable requirements are met.
- **Scoped counterexample:** a valid failing instance can refute an all-cases claim within that instance's scope; it cannot establish population frequency or complete unrelated cells.
- **Operational decision on partial evidence:** give the observed result, decision and limitations; do not relabel it a gate result.
- **Incomplete or inconclusive:** preserve the progress and next useful action; do not silently count missing or truncated units as passes.

Report the number and selection of units, dependence and relevant differences between arms. A completed-first subset can be biased; similarly sized prompts need not have identical histories. Avoid extrapolating a whole workload from an unrepresentative subset. If the protocol fixes sample size or coverage, a post-hoc stop may save resources but leaves that gate incomplete unless the protocol explicitly permits the verdict.

## Formal-gate cells: futility-only interim looks

Until the operator decides OP-ABSEQ / OP-PQP / OP-ALPHAWIN, a formal-gate cell (promotion or ratification evidence) may stop early **only for futility**. An interim look may never declare a gate pass; stop-on-answer applies to operational and diagnostic questions. Worked case: [RTG-58 case study](../../reference/measurement-sufficiency/rtg58-case-study-20261102.md) (two planned 4–5 h runs became one long and two short runs with an unambiguous answer).

## Compact run declaration

`Question/decision: … | evidence already usable: … | units/strata/control: … | minimum coverage: … | looks/method/threshold: … | stop/continue/inconclusive: … | cap: … | records and safe resume: … | gate or diagnostic: …`

For short deterministic tasks, a sentence giving the question and completion condition is sufficient. For a matrix, apply the contract at the level of the actual decision: an early failure of one cell is not automatically a failure of every cell.
