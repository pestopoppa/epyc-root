# Model-Capability Descriptors: The Model-Agnosticism Interface

**Status**: W1 branch-ready; W2 compiler enrichment branch-ready, registry evidence gaps still open
**Created**: 2026-06-12
**Priority**: MED — compiler can start today (no blockers); the Phase-3 cascade tail is GATED and predicted to stay so
**Spec**: [fable5-findings-02-impl-plan.md](fable5-findings-02-impl-plan.md) Phase 2 (+ Phase 3 for the gated tail) and [fable5-findings-02-routing-decision-architecture.md](fable5-findings-02-routing-decision-architecture.md) §3 — read both before claiming any waypoint
**Related**: [retrain-routing-models.md](retrain-routing-models.md) (descriptor-conditioned predictor is the post-retrain shape), [routing-truth-restoration.md](routing-truth-restoration.md) (its W5 stopgap is replaced here; its W8 gates the tail), [MEASUREMENT.md](../../MEASUREMENT.md) §5 item 5 (registry provenance comments are the ONLY measurement witness — never reformat them away)

## Why

Routing intelligence is keyed to role names and dies on stack change (the
2026-05-25 reset; standing rule: index by model, never by role). The research
registry already holds per-model benchmark records the router never reads —
the single missing interface between months of benchmarking and the serving
system. A versioned capability descriptor per model makes a model swap a data
update: the predictor transfers, launch args travel with the model, routing survives.

## Waypoints

- [x] **W1 — schema** (~1 day): `orchestration/model_descriptors.yaml`, one entry per MODEL (canonical id `family-params-quant`), NEVER per role; fields per spec 2.1: quality suite_vector with source/eval_protocol, speed with bench provenance, acceleration (spec_type, draft_compat, enable_thinking, kv), serving (binary, numa_policy, mlock), descriptor_version + compiled_at. Branch-ready in `epyc-orchestrator` worktree `/mnt/raid0/llm/tmp/model-descriptor-worktree`, branch `feat/model-capability-descriptors`, commit `578eb8a` (`Add model capability descriptor seed`). W1 deliberately records role/server conflicts as explicit `known_gaps` instead of resolving them by hand.
- [ ] **W2 — compiler** (~2 days): `scripts/registry/compile_descriptors.py`; sources = research registry + lean registry + bench artifacts; REFUSES to emit a descriptor with missing load-bearing fields (lists gaps instead); runs at stack launch (compose with the existing `--compile-registry` path) and on registry change; converts free-text provenance comments into structured `measured: {date, protocol, value}` fields. Acceptance: clean compile for ≥80% of deployed models (spec §6 gate). Scaffold branch-ready at `e7ca893` (`Add model descriptor compiler`); enrichment branch-ready at `32b8c65` (`Enrich model descriptors from registry evidence`): default-off `--compile-descriptors`, strict refusal, `--allow-incomplete` diagnostic mode, focused tests, read-only research-registry enrichment for `ctx_max`/thinking evidence, role-endpoint serving evidence for dedicated VL roles, and benchmark-date extraction from nested performance blocks. Residual: live allow-incomplete compile has 2/8 clean deployed descriptor identities; live strict compile still refuses the remaining registry evidence gaps.
- [ ] **W3 — first consumers** (~2 days, no router redesign): q_scorer cost model (replaces routing-truth-restoration W5 stopgap), seeder per-role eval config, `orchestrator_stack` acceleration args (spec/MTP/enable_thinking travel with the model — kills the `_NO_SPEC_DECODE`/ik-binary special-case class), eval-tower model signatures replacing hand-maintained `orchestration/model_quality_signatures.yaml` (stale since 2026-04-16, fed to the planner every trial). Acceptance: planner-prompt signatures show `compiled_at` within 7 days.
- [ ] **W4 — simulated model-SWAP CI** (~1 day): replace one role's descriptor with a candidate model's; replay a day of routing decisions + launch-arg generation; PASS = data-only change, zero code edits. Acceptance: passes for 2 candidate models. This is the standing model-agnosticism gate and the precondition for autopilot-proposed model swaps (Stack-Config axis).
- [ ] **W5 — GATED tail: unified cascade (Phase 3)** (2–3 weeks IF ever opened): one calibrated bilinear `P(success | task_features, model_descriptor)` (isotonic, ECE-reported, abstain band) + explicit `cost(model, placement_state)` + ω scalarization; cheap-first/escalation/think-harder become arms of the same argmax; 2-week shadow then staged migration per spec 3.3. Gate: DAR-1 regret replay ≥5% AND per-question eval vectors exist (findings-01). Prediction on record: stays gated.

## Gates & pitfalls

- Registry provenance lives in free-text YAML comments — a reformat DESTROYS the only witness (MEASUREMENT.md §5 item 5); the compiler must read-and-convert, never rewrite the source registries in place.
- Refuse-on-incomplete is load-bearing: silent defaults would re-create the exact stale-signature disease this replaces.
- Sweep-era registry values are demote-to-prior (MEASUREMENT.md §5): re-measure queue ordered by consumer impact, q_scorer first.
- W5 stays closed until BOTH gate conditions hold; no speculative predictor work. Placement/contention is out of scope entirely (separate, working, safety-critical — spec §5).

## Reporting

Tick waypoints + one-line progress entry; delete the master-index row on completion; numbers via MEASUREMENT.md §2 claim grammar.

## Progress

- 2026-06-12: W1 branch-ready (`578eb8a`). Added the descriptor seed for 9 deployed/wired local inference targets plus schema tests. Validation: `pytest tests/unit/test_model_descriptors_schema.py -q` -> 4 passed; `ruff check`; `ruff format --check`; YAML type check; `git diff --check`.
- 2026-06-12: W2 scaffold branch-ready (`e7ca893`). Added `src/registry/model_descriptors.py`, `scripts/registry/compile_descriptors.py`, default-off stack flags `--compile-descriptors` / `--allow-incomplete-descriptors`, and compiler tests. Validation: descriptor/compiler tests -> 7 passed; stack-manifest import suite -> 50 passed; `ruff check` on new compiler/test files; formatter check; `py_compile`; live allow-incomplete dry-run -> 8 model descriptors with gaps; live strict dry-run exits 1 with explicit missing-field list.
- 2026-06-12: W2 enrichment branch-ready (`32b8c65`). Compiler now promotes explicit research-registry `max_context` / `disable_thinking` evidence without mutating source registries, extracts nested performance benchmark dates into `measured.date`, marks role-local VL endpoints as serving evidence, and tags `mmproj`/vision roles with `vision` modality. Live allow-incomplete dry-run: 8 deployed descriptor identities, 2 clean (`gemma-4-26b-a4b-it-q4-k-m`, `qwen3.6-35b-a3b-q8-0`); live strict dry-run still refuses 15 residual gaps across 6 identities. Validation: descriptor/compiler/schema tests -> 9 passed; `ruff check`; `py_compile`; `git diff --check`. GitNexus impact/detect-changes could not resolve the model-descriptor worktree despite fresh index/registration; manual blast radius was descriptor CLI + stack start hook + descriptor tests.
