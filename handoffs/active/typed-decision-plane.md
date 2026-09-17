# Typed Decision Plane — one-pass typed decisions over the local stack

**Status**: in progress — **Owner: research-intake session `intake-jev-sageattn`** (operator-assigned 2026-09-17). Implementation lives in `epyc-orchestrator` on branch `intake/jev-typed-decisions-20260917` (worktree `/mnt/raid0/llm/worktrees/sub-jev-tdp-orch`).
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

- [x] **TD-1 — Implement the local typed-decision call path over the frozen v9 server.** ✅ 2026-09-17 (epyc-orchestrator branch `intake/jev-typed-decisions-20260917`: `src/typed_decisions/` types/schema/runner/confidence, flag `typed_decisions` default off, not wired to any route; 31 unit tests green; native mode deliberately deferred to TD-1a). Per-request JSON-Schema
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
  **2026-09-17 live validation (27B, MI210): IMPLEMENTED BUT NOT YET USABLE.** The native arm fails closed — 1/24 decisions, 23 typed `native_unknown_candidate` failures (emitted tokens 'fal'/'set' are not the declared candidate strings) because candidate strings were presumed single-token without tokenizer access; the JSON arm ran 24/24 clean in 36.7 s. No speedup number may be claimed until candidate matching is tokenizer-aware (TD-1b).
- [x] **TD-2 — Measure cross-question contamination and confidence calibration before any gate.** On a frozen
  EPYC decision set: (a) question-order permutation on one batched call vs single-question calls, report
  top-answer flips; (b) ECE / reliability of the local confidence statistic per model and schema. Acceptance:
  ✅ 2026-09-17 measured on MI210 (GPU, frozen-v9 HIP server; receipts + vidya frames ingested; metric_direction recorded): contamination flip rate 6.25% (27B, 3/48 pairs) vs 37.5% (LFM2.5-2.6B, 18/48) on the 24-question decision set; calibration accuracy 91.7% / mean confidence 0.8875 / ECE 0.0625 / Brier 0.078 (27B) vs 50.0% / 0.567 / 0.267 / 0.313 (LFM) — one 27B miss at ~0.90 confidence, so the tail is not empty. TD-5 gate: SATISFIED for a first shadow.
- [x] **TD-3 — Measure speculative fan-out locally.** Fixed state, N batched questions in one call vs N
  singleton calls, cache-warm; report serial-sum and concurrent wall-clock plus token cost. ✅ 2026-09-17 measured on the GPU (LFM2.5-2.6B): 3 batched calls vs 12 singleton calls over 3 states x 4 questions = 1.54x serial/wall speedup at 100% agreement; the saving is per-call overhead at this small state size. **Long-context replication (2026-09-17, Qwen3.6-35B-A3B, three 40k-char states): 3.22x (33.9 s batched vs 109.2 s singleton).** The agreement metric in that run is NOT interpretable — the fan-out probe catalogue is deliberately content-neutral, so its answers are unanchored. Vendor multipliers stay banned.
- [x] **TD-1b — Tokenizer-aware native candidates.** Obtain each candidate's token id(s) from the server (`/tokenize`) or a tokenizer before building the native grammar and matching probabilities; native mode must not presume single tokens, and multi-token candidates must fall back to JSON mode explicitly. ✅ 2026-09-17 mechanically fixed and live-validated on Qwen3.6-35B-A3B (MI210): candidate tokenization via the server /tokenize seam, grammar positions as exact-token terminals `<[id]>` (quoted literals expand per-character — that was the `fal` failure), probability rows matched by token id. Result: **0 `native_unknown_candidate` failures, 8/24 `native_unsupported_candidates` by design** (mammal/reptile/oregon/vermont/arizona/alaska tokenize multi-token), 16/24 natively resolved, **1.03 s vs 19.4 s = 18.9x faster** than the JSON arm. NOT yet semantically equivalent: agreement 11/16, native accuracy 68.8% vs JSON 91.7% on the overlap (a false-bias on noul) -> TD-1c.
- [ ] **TD-1c — Native semantic parity.** Close the 5/16 disagreement between native and JSON arms before the speed is trusted: check the native prompt's answer cueing vs the JSON prompt, whether the candidate slice is over pre- or post-grammar probabilities, and per-position conditioning (later answers are generated after earlier ones). Acceptance: native-vs-JSON agreement >= 15/16 on the 24-question set with native accuracy within noise of JSON's, or a written explanation of why single-token readout cannot reach parity.
- [ ] **TD-3b — Meaningful fan-out agreement.** Extend the fan-out study to accept the real question catalogue (batched vs singleton on the 24-question set) so agreement measures semantics, not unanchored choices.
- [ ] **TD-4 — Closed-set tool-argument selection pilot.** Map tool arguments to closed sets (Literal → Choice,
  list[Literal] → multi-choice, bool → Noul) with per-argument confidence; compare against the current
  free-form tool-call path on exact-match argument correctness and wall time. Citation: intake-1472 pattern,
  intake-1473 adapter. Implementation + 19 unit tests landed 2026-09-17 (`src/typed_decisions/tool_args.py`); the live pilot against the free-form path is the remaining step. Coordinate with `tool-use-eval-contract.md` (TU-TD-1 there).
- [x] **TD-5 — One shadow integration after TD-2 passes.** Wire the typed-decision call into exactly one live
  surface as a shadow arm (routing classifier or judge, chosen by the owning handoff), gated on TD-2's
  calibration result. **2026-09-17: IMPLEMENTED + SMOKE-VALIDATED.** `src/typed_decisions/shadow.py` wired at `routing.py` (`_plan_review_gate`), flag `typed_decisions_shadow` default off, fixed canonical order, non-blocking bounded daemon (MAX_PENDING=4, drops counted), fail-open, JSONL log via `ORCHESTRATOR_TYPED_DECISIONS_SHADOW_LOG`. Live smoke against the 35B produced one well-formed record (incumbent + decisions + confidences + prompt/state hashes). Next: enable it for a real window and accumulate labeled outcomes (the calibration set), then report agreement + calibration. No enforcement without operator approval.

## Open Questions

- Which confidence statistic, if any, survives local calibration well enough to gate an action?
- Does the frozen v9 server's json_schema→GBNF converter accept the nested probability-map schemas the adapter generates?
- Does question-order contamination on our stack reproduce the 24.7% seen in intake-1486, or is it smaller at our batch sizes?

## Notes

All numbers above are from dive-verified entries; none may be promoted to a deployment measurement until TD-2/TD-3
produce our own. This stub follows the 2026-09-17 operator steering; the vendor's own documentation states confidence
is an undisclosed statistic and calibration is group-level only.
