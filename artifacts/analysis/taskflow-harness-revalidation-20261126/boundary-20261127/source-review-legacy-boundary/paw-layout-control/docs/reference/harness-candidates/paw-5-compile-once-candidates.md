# PAW-5 — Compile-once candidate list

**Status**: candidates filed, compilation deferred. **Prerequisites**: PAW-1 and PAW-2 must land before any compile-once run is executed. All runs below are unexecuted.

## Purpose

Identify ≤3 recurring fuzzy subtasks in the current agent loops and file each as a compile-once candidate with a direct-model baseline, separated from existing deterministic classification or formatting logic. Each candidate names its loop seam, its immutable source revision, the compiled specialist, the direct-model baseline, and a comparison protocol with labelled outcomes for both arms (including abstention/invalid-output behaviour).

FW-1 sketch (§1 worked example) consumed this enumeration; it does not repeat it. JSON repair is struck per 2026-09-29 — `typed-decision-plane.md` TD-21's live shared repair helper (`src/structured_output/repair.py`, used at `repl_executor.py:793`) owns and solves that subtask.

---

## Candidate: Tool-output classification (error-category residue)

**Loop seam**: orchestrator graph worker-turn failure routing. The graph calls `classify_error()` in `src/graph/error_classifier.py` at six duplicated call sites (`nodes.py:232, 283, 347, 464, 568, 671, 776`). When none of its ~30 substrings match, the function falls through to `ErrorCategory.UNKNOWN`. The downstream deterministic gates (`_should_think_harder`, `_should_retry`, `_should_escalate`, `_check_approval_gate` in `src/graph/decision_gates.py`) branch on that category. The **only** fuzzy step is classifying the `UNKNOWN` residue into one of the six known categories.

**Immutable source revision**: `epyc-orchestrator@332ceb2e14d16f2031bd17b1f7c839ce8276a24b` (staged: `src/graph/context_arm_ab.py`; error_classifier and decision_gates referenced in FW-1 handoff).

**Compile-once candidate**: A compiled specialist that maps an error string (+ bounded tail of the worker's last output + tool_outputs envelope) to a closed-set `ErrorCategory` choice, trained on labelled `UNKNOWN`-class failures extracted from graph failure records. The specialist replaces only the fuzzy residue classification; deterministic gates remain code.

**Direct-model baseline**: A small LLM called via `LLMPrimitives` (through the typed-decision runner, one `choice` question over the six named categories — `UNKNOWN` deliberately excluded as an option) with a single corrective retry on schema violation / invalid label. Same input window: error string (head, bounded), last output tail, tool_outputs envelope, current role.

**Comparison**: **Identical inputs**: For each of ≥50 real `UNKNOWN`-class errors from the graph's failure records, both arms receive the same triple `(error_string_head, last_output_tail, tool_outputs_envelope)` with the same bounded lengths and the same role label.
- **Labelled outcomes**: Each arm outputs a category (or abstains). Outcome columns: `predicted_category`, `correct` (boolean vs ground truth), `confidence`, `retry_count`, `latency_ms`. Ground truth is assigned by an operator-reviewed annotation set (≥3 annotators per item, majority vote; disagreements flagged for review).
- **Abstention / invalid output**: If the model returns a label outside the closed set or fails schema validation after one corrective retry, it abstains and routes to `F1.fallback` (category = `UNKNOWN`, continue at G1 exactly as today). Transport errors also route to `F1.fallback`. The fallback is a declared node on the canvas — nothing leaves the loop.
- **Budget**: Compile-once specialist runs in < 50 ms per item; direct-model baseline budgeted at B_parse = 1 corrective retry (small-role call). Cost comparison: per-item latency and total token cost over the full test set.

---

## Candidate: Transcript / log filtering quality (context-arm pruning)

**Loop seam**: orchestrator context-window management in `context_arm_ab.py` (`epyc-orchestrator@332ceb2e14d16f2031bd17b1f7c839ce8276a24b`). The `_prune_at_boundary()` function (line 162) prunes old turn outputs using a hard heuristic: if output > 4000 chars, keep first 1500 + pointer + last 1500; then iteratively clear remaining outputs to token-budget × fraction. This is deterministic formatting, but the **quality** of what survives pruning — whether the retained text actually preserves task-relevant information for the next model turn — is a fuzzy decision today: the heuristic has no feedback loop and no measure of downstream impact.

**Immutable source revision**: `epyc-orchestrator@332ceb2e14d16f2031bd17b1f7c839ce8276a24b` (staged file: `src/graph/context_arm_ab.py`).

**Compile-once candidate**: A compiled specialist that, given a sequence of turn outputs and the remaining token budget, decides which turns to prune, which to truncate, and how much to retain — optimising for downstream task-completion signal rather than a fixed character threshold. The specialist emits a pruning plan (per-turn action: keep / truncate-to-N / clear) as structured output.

**Direct-model baseline**: A small LLM called at each boundary event with the full turn list and budget, asked to produce the same per-turn pruning plan via a typed-decision question (closed-set action labels: `keep`, `truncate:<N>`, `clear`). Same input window: all turns up to the boundary, current token count, budget limit.

**Comparison**: **Identical inputs**: For each session with ≥3 turns that hit a pruning boundary, both arms receive the same turn list (role, code output, error) and the same `(budget, fraction)` parameters.
- **Labelled outcomes**: Each arm outputs a per-turn action plan. Outcome columns: `actions` (list of per-turn decisions), `tokens_after`, `relevance_score` (measured by whether key facts/entities from pruned turns reappear correctly in the final answer on a held-out subset). Ground truth relevance is measured by entity-fact recall: extract named entities and factual claims from each turn, then check whether they appear in the session's final answer.
- **Abstention / invalid output**: If the model returns an action label not in the closed set or fails schema validation after one corrective retry, it abstains and falls back to `_prune_at_boundary()` (the deterministic heuristic). The fallback is a declared node — nothing leaves the pruning path.
- **Budget**: Compile-once specialist runs per boundary event; direct-model baseline is a single LLM call at each boundary. Cost comparison: per-boundary latency, total token cost across all boundaries in a session.

---

## Candidate: Routing predicate evaluation (multi-stage routing decisions)

**Loop seam**: REPL executor `repl_executor.py` (`epyc-orchestrator@332ceb2e14d16f2031bd17b1f7c839ce8276a24b`) makes several heuristic-based routing decisions before entering the graph:

1. **Long-context detection** (line 668): `context_chars > LONG_CONTEXT_CONFIG["threshold_chars"]` → switch to REPL exploration strategy with a capped turn budget.
2. **Two-stage summarization eligibility** (`_should_use_two_stage()` at line 586): heuristic on prompt + context text to decide whether to attempt two-stage summarization before entering the graph.
3. **Schema validation gate** (line 709): `_get_features().final_schema_validation` → inject schema preamble into the initial REPL context.

Each of these is a binary routing predicate today, implemented as simple boolean checks or keyword heuristics. None reads session-level signals (previous turn outcomes, role history patterns, tool-use success rates) that could make the decision more accurate. The fuzzy subtask is: **given the full request context and session state, should this request take path A or path B?**

**Immutable source revision**: `epyc-orchestrator@332ceb2e14d16f2031bd17b1f7c839ce8276a24b` (staged file: `src/api/routes/chat_pipeline/repl_executor.py`).

**Compile-once candidate**: A compiled specialist that evaluates routing predicates (long-context strategy, two-stage summarization, schema preamble injection) based on the full request payload plus session state signals. The specialist emits a structured routing decision per predicate with a confidence score. This replaces the heuristic boolean checks while keeping the deterministic downstream code paths unchanged.

**Direct-model baseline**: A small LLM called once at pipeline entry with the same request + session context, asked to produce routing decisions for each predicate via typed-decision questions (closed-set binary choices). Same input window: prompt, context, task_type, skill_context, tool_required flags, session history (if any), feature flags.

**Comparison**: **Identical inputs**: For each incoming request that reaches the REPL executor stage, both arms receive the same `ChatRequest` payload and session state.
- **Labelled outcomes**: Each arm outputs a routing decision per predicate. Outcome columns: `predicate_name`, `decision` (A or B), `confidence`, `correct` (boolean — measured by whether the chosen path leads to task completion within budget on a held-out test set). Ground truth is derived from retrospective analysis: for requests where the heuristic choice was suboptimal (e.g., long-context request that didn't need exploration, or summarizable request where two-stage was skipped), the correct routing is known.
- **Abstention / invalid output**: If the model returns a decision outside the closed set or fails schema validation after one corrective retry, it abstains and falls back to the existing heuristic (the deterministic code path). The fallback is declared — nothing leaves the pipeline.
- **Budget**: Compile-once specialist runs once per request at pipeline entry; direct-model baseline is a single LLM call per request. Cost comparison: per-request latency overhead vs improvement in routing accuracy (measured by downstream task completion rate and turn efficiency).

---

## Prerequisites

- **PAW-1** must land before compilation begins. This candidate list does not execute any runs.
- **PAW-2** must land before compilation begins. This candidate list does not execute any runs.
- All three candidates are compile-once only: the compiled specialist is built once against a fixed training corpus and then evaluated in comparison mode. No iterative refinement or online learning is planned at this stage.

## Notes on scope

- JSON repair is **not** included as a candidate (struck 2026-09-29; `typed-decision-plane.md` TD-21's shared repair helper at `src/structured_output/repair.py:793` in `repl_executor.py` owns and solves it).
- No runtime changes, model calls, evidence claims, or handoff edits are made by this document. It is a planning artifact only.
- The FW-1 worked example (§2 loop block) uses Candidate 1 (tool-output classification) as its primary illustration; the same two-layer graph pattern applies to Candidates 2 and 3 with their respective deterministic gates.
