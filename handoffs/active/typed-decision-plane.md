# Typed Decision Plane — one-pass typed decisions over the local stack

**Status**: stub
**Created**: 2026-09-17 (via research intake, operator-approved 2026-09-17)
**Categories**: routing_intelligence, cost_aware_routing, inference_serving, tool_implementation, agent_architecture
**Parent index**: [routing-and-optimization-index.md](routing-and-optimization-index.md)
**Evidence**: intake-1472, intake-1473, intake-1474, intake-1485, intake-1486, intake-1487, intake-1490 (all dive-verified); intake-1476#record (application survey, anecdote-grade)

## Objective

Give the orchestrator a first-class one-pass decision call: declared typed questions (choice / score / noul)
in, per-question values + probabilities + a caller-computed confidence statistic out, with no autoregressive
JSON generation, and with locally measured behaviour before any gate uses it. Operator steering 2026-09-17:
"extremely relevant for the orchestrator where json schemas are passed and tool use is important ... guarantees
exact tool use and also a pretty large overall speed boost ... may also be relevant for fast routing and
episodic memory writing."

## Research Context

| Intake ID | What it settles | Use |
|-----------|-----------------|-----|
| intake-1472 | Public typed-decision spec (primitives, one-call parallel questions, confidence is an undisclosed statistic) | Contract for the local implementation |
| intake-1473 | MIT reference implementation over generic LLM APIs (per-request schema, corrective retries, normalization, local confidence stats, injection guard) | Pattern set to transplant onto llama.cpp |
| intake-1474 | Independent evidence that candidate-softmax confidence is NOT calibrated (65% of wrong 7B fields >0.90) and the real local speedup is 3.4–7.9x, not 40–200x | Hard constraint: no gate before local calibration |
| intake-1485 | Paired Jev-vs-fast-LLM run: measured p50 176 ms vs 215 ms; fixture agreement scene-dependent | External datapoint; baseline is fast, so no multiplier transfer |
| intake-1486 | Independent rerank reproduction: Jev tied with Cohere Pro (nDCG 0.692 vs 0.691, CI crosses 0); Jev Choice order-sensitive 24.7% | Guarantees are not quality; order effects must be measured |
| intake-1487 | Fully local pinned one-pass implementation: 5.21x vs same-model JSON on a 3090; 20.03 decisions/s parallel reuse; reuse drifts 5–6/777 argmaxes | Local mechanism + acceptance envelope |
| intake-1490 | Independent audit of jevlike: shipped shuffled-context control was defective; informed-vs-blind lift ~25 pts after correcting | Verification discipline for our own measurements |

## Tasks

- [ ] **TD-1 — Implement the local typed-decision call path over the frozen v9 server.** Per-request JSON-Schema
  generation from declared questions (choice/score/noul), one chat completion with `response_format
  json_schema`, client-side decode + validation with corrective retry, expected-value scoring, local confidence
  statistics (fixed formulas + one documented alternative), and a per-call diagnostics record. Cite intake-1472
  (contract) and intake-1473 (pattern set). Acceptance: a fixture of ≥20 questions returns schema-valid typed
  answers with per-question probabilities; malformed-output retry path exercised.
- [ ] **TD-1a — Native candidate-scoring fast path (the actual speed lever).** Implement the local one-pass mechanism:
  enum-constrained single-token readout with per-question probabilities (`response_format json_schema` enum +
  `n_probs`/`completion_probabilities`) over a shared prompt prefix with prompt-cache reuse, batching multiple
  questions into as few requests as the server allows. Benchmark it against TD-1's JSON-schema generation path —
  wall time, output tokens, argmax agreement, and cache-reuse drift (intake-1487 measures 5-6/777 argmax flips
  under BF16 reuse; intake-1474 measures 3.4-7.9x for the pattern vs same-model naive JSON). Acceptance: our own
  speedup and drift numbers; TD-5 remains gated on TD-2 calibration regardless of the speed result.
- [ ] **TD-2 — Measure cross-question contamination and confidence calibration before any gate.** On a frozen
  EPYC decision set: (a) question-order permutation on one batched call vs single-question calls, report
  top-answer flips; (b) ECE / reliability of the local confidence statistic per model and schema. Acceptance:
  contamination and calibration numbers recorded in a measurement artifact; TD-5 is BLOCKED until this lands.
- [ ] **TD-3 — Measure speculative fan-out locally.** Fixed state, N batched questions in one call vs N
  singleton calls, cache-warm; report serial-sum and concurrent wall-clock plus token cost. Acceptance: our own
  numbers replace any vendor batching multiplier in internal documents.
- [ ] **TD-4 — Closed-set tool-argument selection pilot.** Map tool arguments to closed sets (Literal → Choice,
  list[Literal] → multi-choice, bool → Noul) with per-argument confidence; compare against the current
  free-form tool-call path on exact-match argument correctness and wall time. Citation: intake-1472 pattern,
  intake-1473 adapter. Coordinate with `tool-use-eval-contract.md` (TU-TD-1 there).
- [ ] **TD-5 — One shadow integration after TD-2 passes.** Wire the typed-decision call into exactly one live
  surface as a shadow arm (routing classifier or judge, chosen by the owning handoff), gated on TD-2's
  calibration result. Acceptance: shadow agreement + calibration reported; no enforcement without operator approval.

## Open Questions

- Which confidence statistic, if any, survives local calibration well enough to gate an action?
- Does the frozen v9 server's json_schema→GBNF converter accept the nested probability-map schemas the adapter generates?
- Does question-order contamination on our stack reproduce the 24.7% seen in intake-1486, or is it smaller at our batch sizes?

## Notes

All numbers above are from dive-verified entries; none may be promoted to a deployment measurement until TD-2/TD-3
produce our own. This stub follows the 2026-09-17 operator steering; the vendor's own documentation states confidence
is an undisclosed statistic and calibration is group-level only.
