# Framework adoption shortcuts: verdict-driven assessments vs named orchestrator modules

**Date:** 2026-07-16
**Companion handoffs:** [`reviewer-control-plane-index.md`](../../handoffs/active/reviewer-control-plane-index.md) (H0 adoption-shortcuts table), [`reviewer-trace-materialization.md`](../../handoffs/active/reviewer-trace-materialization.md) (H1), [`harness-selection-and-integration.md`](../../handoffs/active/harness-selection-and-integration.md) (HS-1/HS-4)
**Sources:** intake-847 (LangGraph 1.0, cred 6/6) · intake-848 (OpenHands, 6/6) · intake-849 (OpenAI Agents SDK, 6/6) · intake-839 (MetaGPT, 5/6)
**Operator question answered:** "are we leveraging mature tooling or building unnecessarily from scratch?" — mostly the latter is FALSE (bespoke-on-purpose for the trust boundary), with **one genuine adopt_component and three pattern mines**.

---

## LangGraph — ADOPT_COMPONENT (the one real shortcut)

Material finding: LangGraph is **already a declared dependency** (`pyproject.toml`: `langgraph>=0.2.0`, `langgraph-checkpoint-sqlite>=2.0.0`) with a dormant Phase-1 bridge (`src/graph/langgraph/bridge.py::run_task_lg(checkpointer=...)`, flag `langgraph_bridge=False`). Gap analysis of our own code: `persistence.py::SQLiteStatePersistence` is **write-only** (`load_next()` always None — never rehydrates) and `resume_token.py` restores only ~8 control-flow fields → we are materially behind on durable cross-restart resume and replay/time-travel, the two hardest battle-tested pieces LangGraph ships (SqliteSaver; `interrupt()`/`Command(resume=)`; `get_state_history()`). We are AHEAD on interrupt-trigger policy (`should_halt()`, `decision_gates.py`) and compile-time edge safety (pydantic_graph Union returns) — keep those.
**Adopt:** SqliteSaver through the existing bridge; review gates on interrupt/resume, shadow-first (H1 TM-7, H3). **Scope:** imports strictly `langgraph` + `langgraph-checkpoint-sqlite`. **Hazard:** node re-execution on resume → `_execute_turn`/REPL side effects must be idempotent.

## OpenAI Agents SDK — MINE_PATTERNS ×7 (no dependency)

Fully local-compatible (base_url + chat_completions; `set_trace_processors` removes the OpenAI exporter → zero platform coupling), but primitives are inseparable from Agent/Runner. Patterns adopted: (P1) tripwire ⟂ advisory split → `ArchitectReview`; (P2) shadow→enforce — `safety_gate.warn_only` already does this, propagate to review_service (**we are ahead of the SDK**); (P3) durable `DelegationState` + interruption records (LangGraph SqliteSaver = substrate, this = payload shape); (P4) as-tool vs handoff delegation modes made explicit in `delegator.py`; (P5) guardrail placement — complexity-gated per-subtask review + single final-aggregate review (latency lever); (P6) TracingProcessor 6-method push interface **re-implemented** over `src/trace/store.py`; (P7) sticky decision cache in `IterationContext` + `is_enabled` predicates on `RoutingBinding.active`. Also validated ahead-of-SDK: priority-ordered `BindingRouter`.

## OpenHands — MINE_PATTERNS (runtime); serious-but-orthogonality-weak HS-4 candidate

Runtime: replacing `restricted_executor.py` would be a category error (in-process sub-ms REPL vs Docker REST round-trip; minimum-imports violation) — but its **EventStream** (append-only Action/Observation log) + client/server action-executor split are the blueprint for a *future* untrusted-code tier (our bytecode-only isolation is genuinely weak). `gate_runner.py` is orthogonal (OpenHands has no verifier-gate concept).
Harness: mechanically the strongest HS-4 fit yet — MIT, `/v1` to bare llama.cpp via base_url, `LLM.extra_headers` forwards on every request (**x_* passthrough works**; per-turn dynamism needs N named configs or a ~10-line patch), headless `--json` JSONL. But it ships its own full Layer-B loop + Docker substrate → adopting it imports a *competing orchestrator* (Cross-Cutting-Concern-#1 instantiated). Verdict recorded into HS-1: audit as serious candidate, score against orthogonality/minimum-imports; a thin OpenCode-style shell is likely cheaper to make cooperate.

## MetaGPT — MINE_PATTERNS (contracts, not the system)

Independently validates two of our invariants: **reviewer-no-authorship** (QA reports, author debugs) and **executable feedback outranks LLM review** (+4.2/+5.4pp; LLM reviews "hallucinated"). Steal: artifact-chain shapes with explicit interface/data-structure + dependency fields (their revision-rounds 2.5→0.83 win); **schema validation gates every role boundary** (their #1 fragility is soft prompt-enforced schemas); dependency-gated activation + subscribe-by-artifact-type. Heed the critique literature: accountable/validated handoffs swing ±15-36pp; multi-role tax ~2-3× cost / 8-10× latency; **a single strong model beat the pipeline outright** → the control plane's standing floor is "beat a single augmented LLM" (H-LB LB-7), and cheap tasks short-circuit the chain. Their AFlow pivot concedes fixed SOPs don't generalize → contracts stay domain-general, plans are generated per-task.

## Bottom line

The bespoke pieces that stay bespoke are bespoke for a reason (measurement trust boundary; evolutionary autopilot; the typed-decision/calibration layer no framework ships). The imported wins: durable execution (LangGraph component), seven governance-semantics patterns (SDK), one future-tier blueprint (OpenHands), and contract discipline (MetaGPT) — all scoped to named modules with minimum-imports intact.
