# Audit: "Formalizing an Architect→Reviewer Control Plane" — report review + local adaptation

**Date:** 2026-07-16
**Audited artifact:** `tmp/deep-research-report.md` (operator-provided deep-research report; explicitly non-authoritative)
**Companion handoffs:** [`handoffs/active/reviewer-control-plane-index.md`](../../handoffs/active/reviewer-control-plane-index.md) (H0 — the series this audit anchors)
**Evidence base:** 4 exploration agents (orchestrator internals, experiments/models, governance, v7 kernel) + 13 Opus deep-dives executed during the planning session (intake-834..849)
**Scope:** what the report gets right, where it is wrong *for us*, and the adaptation decisions locked with the operator.

---

## Verdict

The report's central thesis is **sound and confirmed non-duplicative**: public frameworks provide orchestration primitives but no *review-governance layer* — typed decisions with bounded authority, evidence links, verifier precedence, and false-accept/false-reject (FA/FR) calibration accounting. Both the intake index (no prior entry frames an Architect→Reviewer control plane) and the Anthropic engineering set (intake: no post formalizes typed governed ReviewDecision contracts or an FA/FR decision-cost ledger) confirm this is a genuine extension, not reinvention.

Its **"build the stack" framing is wrong for this repo**. The machinery mostly exists, dormant:

| Report proposes | Already exists (dormant) | Gap that remains |
|---|---|---|
| Reviewer decision API | `src/proactive_delegation/review_service.py` (`ArchitectReviewService.review()/.review_plan()`), typed `ReviewDecision`/`ArchitectReview`/`IterationContext`; flags `plan_review`+`architect_delegation` OFF | evidence links, confidence, tripwire/advisory split, REQUEST_EVIDENCE, grammar-constrained emission |
| Typed artifacts (TaskSpec/PlanGraph) | `orchestration/task_ir.schema.json`, `architecture_ir.schema.json`, `procedure.schema.json` + `validate_ir.py` | `review_decision`/`candidate_package`/`verification_report` schemas |
| Trace store | `src/trace/store.py` (SQLite+FTS5, DECISION/VERIFY/SAFETY_VERDICT categories) — scaffolded, `events.sqlite` never materialized | materialize + REVIEW_* categories + live emit + `review_ledger` |
| Objective verifiers | `src/gate_runner.py` (format/lint/typecheck/unit), MCP run_tests/lint, `restricted_executor.py`, eval tower T0–T3, EV-9 rubric judge (default-off) | verifier-request adapter, three-valued outcomes, `config/gates.yaml` (missing on disk) |
| Calibration statistics | `src/autopilot_core/sequential_verdict.py` (e-process, Ville FPR), Bradley-Terry, rubric_scoring | FA **and FR** tolerance e-processes, decision ledger, near-miss corpus |
| Planner→critic separation | autopilot `planner_providers.py`: Claude planner + read-only codex_critic | adopt the typed decision schema (dogfooding, H8) |

**The work is therefore activation + instrumentation, not construction** — turn dormant machinery into a governed, measured control plane. That is the design center of the H0–H8 handoff series.

## What the report gets right (kept)

1. **Reviewer = judicial gate, not author.** Externally validated by MetaGPT's QA-no-authorship result and by the role-collapse literature. Kept as an invariant: ReviewDecision is non-mutating; repair routes to the author.
2. **Objective verifiers take precedence.** Validated hard: solver-in-loop lifted TravelPlanner 10%→93.9% (Hao 2404.11891); executable feedback beat LLM review in MetaGPT; the fix-guided verification filter cut false-rejects ~40pp (2603.00539). Refined by us into a **three-valued outcome** (PASS / FAIL-with-certificate / INCONCLUSIVE) because formalization incompleteness produces ~15% false-positives (Sistla 2509.26546) — precedence applies only to conclusive verdicts.
3. **FA/FR calibration as the core measurement.** Correct, and sharpened: the dominant measured failure is **false-reject overcorrection (10:1–440:1 over FA)** (2603.00539), so the ledger needs a *symmetric* FR-tolerance e-process, not the report's FA-leaning framing.
4. **Measurement before sophistication.** Matches MEASUREMENT.md; the series milestones (M1 observable → M2 measured → M3 compared → M4 governed) encode it.
5. **Typed decisions with discrete labels + advisory fields.** Kept, with the tripwire ⟂ advisory split (blocking boolean orthogonal to score/feedback) borrowed from `safety_gate.py`/Agents-SDK guardrail semantics.

## Where the report is wrong or incomplete for us (corrected)

1. **SWE-centrism.** The report addresses "autonomous software engineering"; our stack serves general/reasoning/math/summarize/ingest/vision/tool-use roles. **The control plane is domain-general** (operator directive 2026-07-16): the objective layer generalizes to eval-tower programmatic scorers, retrieval-grounding checks, math checkers, instruction-constraint checkers; evidence kinds include answer spans and scorer results, not just file_span/test_result; calibration is reported per-domain.
2. **Latency is under-weighted.** On a CPU stack, review overhead is the first-order cost: a plan-review/eval-routing regression measurably **halved** eval throughput on 2026-07-16 (~68 backend requests + 11–17 plan-review prompts per 50-question replay). Multi-role pipelines carry ~2–3× cost / ~8–10× latency in the critique literature, and multi-agent fan-out ~15× tokens (Anthropic) — with single-host parallel-reviewer latency modeling as **sum, not max**. Hence H-LB (latency/sampling budget) gates ALL enforce-mode, and the structural fix is the **two-turn reviewer** (heavyweight authors a cached rubric; a cheap model grades each candidate — authoring $0.245 vs grading $0.003 in Agentic Rubrics' economics).
3. **The framework survey is moot as an adoption question, valuable as a pattern mine.** The 2026-07-16 harness-selection boundary (Layer A moat behind `/v1`; Layer B needs an open-source cooperating harness; no bespoke harness) plus pydantic_graph already in `src/graph/` collapse "which framework to adopt" into four verdicts: **LangGraph = adopt_component** (SqliteSaver + interrupt/resume through the already-existing `run_task_lg` bridge; our persistence.py is write-only and never rehydrates), **OpenHands = mine_patterns** (+ serious HS-4 candidate, flagged weak on orthogonality), **OpenAI Agents SDK = mine_patterns ×7** (tripwire split, DelegationState, guardrail placement, TracingProcessor re-implementation, sticky decisions, as-tool/handoff distinction, is_enabled predicates), **MetaGPT = mine_patterns** (artifact-contract chain, boundary validation-gating, dependency-gated activation).
4. **The baseline table is an example, not a spec.** GLM-5.2 FP (~1.4TB+) is infeasible locally; the upper bound is replaced by a **bounded metered frontier-API judge-of-judge** (~100 sampled decisions, pinned model-id+date; operator-approved). The fixed 7-condition matrix is replaced by a **registry-driven staged tournament** (~240 models; pool pruning → autopilot-driven screening → paired N≥100 confirmation for Pareto-promising pairs), per operator directive.
5. **No GPU axis.** The report ignores the MI210 entirely. The operator-locked sequencing: (1) GPU drafter Stage-1 (α=1.0 gate cleared 2026-07-16; accelerates CPU architect/frontdoor now), (2) fast-architect residency quality gate (122B-IQ2 GPU-resident, 43.7 t/s = 2.2× CPU; IQ2==Q4 parity Δ0.0pp/n=212 but strict-IF weak 2/11 → grammar mandatory), (3) GLM-5.2 hot-expert offload path (expert-routing-skew profile is the go/no-go), (4) **CPU→GPU stream teleport** (v1 = re-prefill + spec-dec catch-up; break-even ≈150–250 remaining tokens with a resident target; mid-stream quant change = model swap → operator decision). GPU/kernel experiment tasks route to the parallel inference-research session's existing handoffs.
6. **Debate/appeal machinery does not survive evidence review.** Our regime (strong judge, no information asymmetry) is the debate literature's worst case (martingale null result; consultancy degrades judges). H7 defaults to ESCALATE; a single two-sided rebuttal round exists only as an opt-in, per-task-class gated on measured signed net-flip Δ>0.
7. **Reviewer prompt design is a measured attack surface the report doesn't cover.** Architect self-assessment/authority framing shifts verdicts by ~18–29pp; "explain-then-fix" prompting doubles overcorrection; verbosity bias lives in the weights. Hence: CandidatePackage sanitization, framing-neutral prompts, pointwise-only grading, Consistency-Rate reporting, and a bias-perturbation probe set as a reviewer-selection axis.

## Two P0 blockers discovered during audit (routed to the kernel handoff)

1. **JSON/GBNF grammar sampler crashes on the v7 HIP build** (`common/sampling.cpp:292`, v7-added grammar-prefill path; trivial-schema repro). Grammar-constrained emission is how a quantized reviewer produces schema-valid ReviewDecisions — hard blocker for typed decisions on v7.
2. **GLM-5.2 load path unverified**: `LLM_ARCH_GLM_DSA` ("glm-dsa") exists in-tree (`llama-arch.cpp:84`, model class + DSA KV-cache), but the unsloth UD-IQ2_M GGUF's arch string/tensor mapping is unreconciled and the load/coherence smoke was intentionally skipped 2026-07-16. Validation task, not new-arch authoring — but blocker-class for the reviewer target model.

## Adaptation decisions locked with the operator (2026-07-16)

1. GPU bets sequenced 1→4 (drafter → residency gate → GLM offload → teleport); GPU/kernel tasks appended to parallel-session-owned handoffs, no new standalone GPU handoffs.
2. Reviewer identity: **GLM-5.2 UD-IQ2_M cross-family target; Qwen3.5-122B-IQ2 GPU-resident interim**.
3. External judge-of-judge: approved, bounded.
4. Full 12-dive slate + framework verdicts: executed during planning (this document's evidence base).

## Scope cuts (deliberate, documented here and in H0)

No public benchmark **adapters** (acquisition only — suites are corpus-mining inputs); no full ArchBench (only the near-miss corpus slice); no reviewer rewrite/repair modes; no Qwen3.5-397B architect arm; no debate/role-swap machinery beyond the gated rebuttal option; no human-escalation UI (HS-4-gated); no new decision theory (Fable5 verdict: enforcement and deletion, not new theory).

## Pointers

- Handoff series: `reviewer-control-plane-index.md` (H0) → trace-materialization, typed-artifacts, decision-plane, calibration-accounting, model-ablations, glm52-capability-gates, latency-budget, escalation-policy, autopilot-integration.
- Dive evidence: intake-834..849 (`research/intake_index.yaml`) + thematic deep-dives in this directory (same date prefix).
- Dataset acquisitions: `/mnt/raid0/llm/datasets/BENCHMARKS.md`.
