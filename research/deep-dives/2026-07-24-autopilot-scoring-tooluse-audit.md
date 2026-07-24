# Autopilot scoring & tool-use audit (orchestrator, read-only)

Date: 2026-07-24 · Scope: `/mnt/raid0/llm/epyc-orchestrator` · Trigger: architect-bench `extract_letter_answer` verbose-penalty incident; canonical scorer now at `epyc-inference-research/scripts/benchmark/answer_scoring.py`.

## Executive summary

- **Q1 (memrl reward): NOT AFFECTED (live path).** The production TD reward contains **zero regex answer extraction** — success is a structural flag (non-empty, no `[ERROR`/`[Max turns` prefix), cost terms are telemetry+priors, and the latency penalty is length-normalized (`expected = tokens_gen/baseline_tps`), so verbose-but-correct is not under-rewarded. The only extraction-derived rewards are the **externally injected** eval/seeding rewards, scored by the orchestrator's B7-hardened `debug_scorer` which already handles bare-letter-final-line and last-match — the incident bug class does not apply there either.
- **Q2 (judge parsing): bug class present, but every affected path is dormant or reward-decoupled.** `model_grader._extract_classification` is last-line-only (bug class applies) but has **no callers**; the proactive-review judge (parse-fail → reject-ish, candidate truncated to **500 chars**) couples to reward but its gating flags are declared-off in production; the live architect verdict gate fails open and never touches reward.
- **Q3 (tool use): a real, production-live tool-execution loop exists** — bespoke Python-REPL protocol (`TOOL()/CALL()/FINAL()`), **not** llama-server native function calling. A tool-use eval already runs through the orchestrator (`force_mode="repl"` sentinels + `get_eval_secret` + telemetry contract gate); an architect coding/tool-use eval is runnable today via `call_orchestrator_forced(force_role="architect_general", force_mode="repl")`. Wired-but-dead: `ChatRequest.tools` is accepted and never consumed.
- **Q4: 10 independent extraction/parsing implementations found**; two share the first-match/last-line bug-class residue (rescue paths only), one is dead, three are dormant. Recommend vendoring the canonical `answer_scoring` contract into the orchestrator with a shared golden-corpus drift test (data-only cross-repo coupling, consistent with the orchestrator→research DATA dependency).

No ⚠ PRODUCTION FINDING: the live reward path does not text-extract answers, and all judge-parse couplings into reward are behind flags currently declared off.

---

## Q1 — memrl reward path

### Entry points and call chain

`score_completed_task` / `score_completed_task_for_request` / `score_completed_task_with_mode` (`src/api/services/memrl.py:183-256`) are fire-and-forget wrappers that submit `state.q_scorer._score_task(task_id)` to a 4-thread pool (`memrl.py:147-157, 173-180`). The QScorer is constructed with `use_claude_judge=False` — "Basic mode only - no LLM required" (`memrl.py:390-394`); the LLM-judge path (`orchestration/repl_memory/q_judge.py`) is **dormant in the live API**.

`QScorer._score_task` (`orchestration/repl_memory/q_scorer.py:779-894`) reads the task trajectory from the progress log, assembles TASK_STARTED / ROUTING_DECISION / TASK_COMPLETED-or-FAILED / gate / escalation / plan-review events, computes the reward, and TD-updates the episodic store:

- Reward: `q_reward.compute_reward` (`orchestration/repl_memory/q_reward.py:49-175`), delegated at `q_scorer.py:930-942`.
- TD update: `EpisodicStore.update_q_value` — `Q ← Q_decayed + α(r − Q_decayed)` (`orchestration/repl_memory/episodic_store.py:657-686`), via `_update_routing_memory` (`q_scorer.py:1119-1203`; find-or-update path live since `ORCHESTRATOR_Q_TD_WRITE=1`, `scripts/server/orchestrator_stack.py` ~line 1683).

### Reward composition — is anything text-extraction-derived?

`compute_reward` inputs (`q_reward.py:74-175`):

| Component | Source | Extraction-derived? |
|---|---|---|
| Base reward (success 1.0 / partial 0.3 / failure −0.5) | `task_outcome.outcome` — the `success=` bool passed to `log_task_completed` by each pipeline stage | **No** (structural, see below) |
| Gate penalty (−0.1 each) | GATE_FAILED events | **Never fires**: the only emitter is `progress_logger.py:538` and grep finds **no caller in `src/`** — gate_penalty is structurally 0 in the live path |
| Escalation penalty (−0.15 each) | ESCALATION_TRIGGERED events | No — emitted by error classification / model-calling-`ESCALATE()` (explicit REPL function, `src/repl_environment/routing.py:206-216`; graph emitters `src/graph/langgraph/nodes.py:358-388`), not by scanning answer text |
| Plan-review adj (+0.1/−0.2) | PLAN_REVIEWED events (`src/api/routes/chat_review.py:413`) | Judge-derived, **but `plan_review` is declared-off in production** (`orchestrator_stack.py:1573`) — never emitted live |
| Latency penalty | `cost_ratio = elapsed / (tokens_gen / baseline_tps)` (`q_reward.py:139-143`) | No — and **length-normalized**: a verbose answer raises `tokens_gen` and `expected_elapsed` proportionally, so verbosity per se is penalty-neutral; only sub-baseline throughput is penalized |
| Quality-gap & memory-tier penalties | Role priors from stack_priors (`q_reward.py:145-156`) | No |
| Teacher regret/speedup, web-research diversity | Telemetry counters (`q_reward.py:158-172`) | No |

### The `success` flag per live stage (all structural, no extraction)

- Direct: `success = bool((answer or "").strip()) and not answer.startswith("[ERROR")` — `src/api/routes/chat_pipeline/direct_stage.py:244`.
- REPL/graph: `success = not answer.startswith("[ERROR") and not answer.startswith("[Max turns")` — `repl_executor.py:650`.
- Delegation: `success = not answer.startswith("[ERROR")` — `delegation_stage.py:200`.
- Streaming: `success = result is not None and result.is_final` — `stream_adapter.py:405`.
- Vision: `success=True` unconditionally — `vision_stage.py:347-349`.
- Proactive: `success=result.all_approved` — `proactive_stage.py:203-205`. **This one IS judge-derived** (see Q2) but the stage is gated on `features().parallel_execution` (`proactive_stage.py:96`) which is **declared-off** in production (`orchestrator_stack.py:1575`) — dormant.

A verbose-but-correct answer cannot fail any live `success` check; there is no path where extraction failure converts a correct answer into `failure_reward`.

### External reward injection (the extraction-derived half, by design)

`POST /chat/reward` (`src/api/routes/chat.py:236-259`) → `store_external_reward` (`memrl.py:272-315`) → `q_scorer.score_external_result` (`q_scorer.py:1290-1387`). Callers: seeding pipeline (`scripts/benchmark/seeding_injection.py:111,131`), research-repo `replay_missing_rewards.py`, deprecated `orchestrator_eval.py`. Rewards are binary `success_reward(passed)` (`scripts/benchmark/seeding_rewards.py:452-467`), where `passed` comes from `score_answer_deterministic` (`scripts/benchmark/seeding_scoring.py:63-72`) → the **orchestrator's own** `debug_scorer.py` (explicitly path-pinned to avoid the research copy winning an import race, `seeding_scoring.py:32-60`).

**Does that scorer share the incident bug class? No.** `debug_scorer._extract_multiple_choice_letter` (`scripts/benchmark/debug_scorer.py:245-274`) is B7-hardened: Strategy 1 takes the **LAST** `answer is/: X` match (:248-251), Strategy 2 matches a bare letter **on its own line** anywhere and takes the last (:253-257) — exactly the case the stale research regex dropped — plus bold-letter and start-of-output strategies. Exact-match's last resort is the final line (:123-126), also verbose-tolerant. Important eval hygiene detail: forced-role real-mode probes **skip internal background scoring** (`should_skip_background_scoring`, `memrl.py:210-221`), so eval rewards enter only via the injection path — no double-scoring.

Residual divergence vs the canonical contract (`epyc-inference-research/scripts/benchmark/answer_scoring.py:15-61`): orchestrator covers A-H (canonical A-J); orchestrator Strategy 5 takes the *last standalone letter anywhere* (`debug_scorer.py:269-272`) — a false-**positive** risk (e.g. the article "A" matches `\b([A-H])\b`), where the canonical version accepts a lone candidate only (`answer_scoring.py:57-60`). This is score-inflation risk, not a verbose penalty.

### Verdicts

| Path | Verdict | Why |
|---|---|---|
| Live internal TD reward (`_score_task` → `compute_reward`) | **NOT AFFECTED** | No answer-text extraction anywhere; success structural; latency term length-normalized (`q_reward.py:139-143`) |
| External injected rewards (seeding/eval → `/chat/reward`) | **NOT AFFECTED** (for the incident bug class) | `debug_scorer` handles bare-letter-final-line + last-match (`debug_scorer.py:245-274`); scorer-unavailability raises instead of mis-scoring (`debug_scorer.py:35-46`, `seeding_scoring.py:75-111`) |
| Proactive-delegation reward (`all_approved`) | **PARTIALLY** (bug class applies; **not reachable**) | Judge-derived success + 500-char candidate truncation (Q2); `parallel_execution=False` in production (`orchestrator_stack.py:1575`) |
| ClaudeAsJudge graded rewards | **PARTIALLY** (bug class applies; **not reachable**) | `_parse_score` silently defaults to 1/3 on unparseable judge output (`q_judge.py:159-175`); `use_claude_judge=False` in the live config (`memrl.py:391`) |

Fraction of reward that is text-extraction-derived: **0% of the live internal reward; 100% of the injected eval rewards** (by design — and that scorer is the hardened one).

## Q2 — judge parsing

### `model_grader.grade_answer` / `_extract_classification` — bug class PRESENT, code DEAD

`_extract_classification` parses **only the last non-empty line** of the judge's response for a choice letter (`src/pipeline_monitor/model_grader.py:173-184`). A verbose judge that appends anything after its letter ("…so my classification is B. Let me know if…") returns `classification=None` → `score=None` (`model_grader.py:161-163`); the record is kept (not dropped, not retried, not defaulted) with a null score — silently shrinking the graded sample in whatever aggregates over it, i.e. the same "penalize models/judges that keep talking" class.

**Reachability: none.** Repo-wide grep finds callers only in `tests/unit/test_model_grader.py`; nothing in `src/`, `scripts/`, or the research repo invokes `grade_answer`/`grade_diagnostic_batch`/`load_grading_specs`. The three grading specs (`orchestration/grading_specs/*.yaml`) are load-able but never loaded in production. Verdict: **bug class applies, path dead**.

### `review_service.review` — the one judge whose verdict couples to reward (dormant)

- The reviewer sees at most the **first 500 chars** of the candidate output (`src/proactive_delegation/review_service.py:420`; quick mode 200 chars, :428). A verbose-but-correct specialist whose conclusion lands after char 500 is judged on its preamble — a direct structural bias against showing work.
- Verdict parse: `_parse_review_response` strips code fences, then `json.loads`, then first-`{`-to-last-`}` rescue; **hard parse failure returns `{"decision": "request_changes"}`** (fail-closed) — review_service.py, `_parse_review_response` (~line 610-640 region; warning + fallback dict).
- Decision → reward: APPROVE → `sr.success=True`; REJECT → `success=False`; max-iterations without approval → failure (`src/proactive_delegation/delegator.py`, `_execute_with_review` iteration loop; REJECT branch and max-iteration fall-through). `all_approved = all(r.success or partial)` (`delegator.py:478-481`) → `log_task_completed(success=all_approved)` (`delegator.py:485-491`, `proactive_stage.py:203-205`) → memrl reward. ESCALATE decisions additionally log escalations (−0.15 each; `delegator.py`, ESCALATE branch).
- Plan review is the opposite polarity: unparseable/invalid decisions normalize to `"ok"` (**fail-open**, `review_service.py:538-541`), and errors return None/non-blocking (:570-587).

**Reachability:** `parallel_execution`, `architect_delegation`, `plan_review` are all declared-off in the production wave overrides (`orchestrator_stack.py:1567-1579`, comment: "Wave-2 paths have been dormant for months"). Per-request `allow_delegation=True` can still enable delegated mode (`delegation_stage.py:96-101`) — so any future eval that flips it on inherits the 500-char-truncation bias into reward. Verdict: **bug class applies (truncation + parse-fail-→-reject); not reachable under current flags**.

### `rubric_review.grade_candidate` — the robust one (also dormant)

Grader output is extracted with a brace-depth/string-aware balanced-JSON scanner tolerant of surrounding prose and fences (`src/proactive_delegation/review_grammar.py:265-300`), so verbosity around the JSON is harmless. Parse failure is accounted per-pass (`rubric_review.py:493-501`); **all-passes-failed raises `RubricGradingError`** (loud, :455-459) instead of defaulting; a missing per-item grade scores a conservative 0 with `graded=False` recorded (:531-535). This is the best judge-parsing contract in the repo — and it has **no callers** outside tests (reviewer-control-plane H2; constrained-decoding GBNF generation exists in `review_grammar.py` but "driving llama.cpp with these grammars… is out of scope", :20-22). Verdict: **not affected; dormant**.

### Live-but-reward-decoupled judge parses (for completeness)

- `_architect_verdict` (`src/api/routes/chat_review.py:82-122`, called from `direct_stage.py:222-240`): prefix-parse — `OK*` → keep, `WRONG*` → revise; anything else (a verbose judge that buries its verdict) is silently ignored → fail-open, review efficacy degrades, reward untouched.
- `q_judge.ClaudeAsJudge._parse_score` (`q_judge.py:159-175`): line-prefix `SCORE:` scan; unparseable → score 1/3 "middle-low" silently. Dormant (`memrl.py:391`).

## Q3 — tool-use wiring map

### (a) Is there a working tool-execution loop? Yes — live in production

End-to-end path (`/chat`, REPL mode — the default fallback mode for non-trivial prompts, `src/api/routes/chat_routing.py:144-196`):

1. **Mode selection**: `_select_mode` returns `direct` or `repl` ("REPL is the universal superset", `chat_routing.py:153-157`); `react` is unified into REPL structured mode.
2. **Environment**: `repl_executor` builds `REPLEnvironment(tool_registry=state.tool_registry, role=initial_role, tool_context=…)` (`src/api/routes/chat_pipeline/repl_executor.py:333-344`) and runs the typed-node graph loop `run_task(task_state, task_deps)` (`repl_executor.py:553-560`; nodes in `src/graph/`).
3. **Model turn**: the model emits *Python code*; it is AST-security-checked, unicode-sanitized, and `exec`'d in restricted globals (`src/repl_environment/environment.py:256-348, 1292-1346`).
4. **Tool call**: `TOOL(name, **kw)` / `CALL("name", **kw)` inside that code dispatches `tool_registry.invoke(tool_name, self.role, …)` (`src/repl_environment/context.py:440-560`, invoke at :547-556) with request-local telemetry (`_invoked_tools`, :440-448 — deliberately not the process-global invocation log).
5. **Result** returns as the expression value/stdout into the REPL state; the loop continues until `FINAL(answer)` (`environment.py:746-775`) or max turns.
6. **ReAct**: same machinery with `structured_mode=True`, 5-turn loop, early-stop on `FINAL(`/`CALL(` regexes (`src/api/routes/chat_pipeline/stages.py:127-245`).

**Production-live, not dormant**: the stack launcher sets `ORCHESTRATOR_TOOLS=1`, `ORCHESTRATOR_SCRIPTS=1`, `ORCHESTRATOR_REACT_MODE=1`, `ORCHESTRATOR_CASCADING_TOOL_POLICY=1`, `AUTOPILOT_TOOL_SENTINELS=1` (`scripts/server/orchestrator_stack.py:1719-1743`), and every registry flag is materialized as `ORCHESTRATOR_FEATURE_*` from `default_prod` (`:1591-1608`). Tools registered at startup: builtin code/data/file/compat tools (`src/builtin_tools.py:28-44`), manifest tools under `src/tools/{code,web,file,data}` via `tool_loader`, optional MCP-backed tools (`src/registry/tool_registry.py:596-601`, `orchestration/mcp_servers.yaml`).

### (b) Native function calling or bespoke protocol? Bespoke.

- No `tools=` is ever sent to llama-server: the backend payload supports only `json_schema`/`grammar` constraint fields (`src/backends/llama_server.py:1144-1147`); grep of `src/backends/` finds no tools/tool_choice key.
- The OpenAI-compat endpoint (`/v1/chat/completions`) **accepts** `tools`/`tool_choice` but converts them into a prompt bridge instructing the model to use `CALL("tool_name", …)` (`src/api/routes/openai_compat.py:166-205, 232-234`) and **never emits `tool_calls` back** — metadata stamps `native_tool_contract: "internal_repl_execution"`, `response_tool_calls: "not_emitted"` (`openai_compat.py:260-273`). Caller-defined tools therefore cannot actually execute (there is no client callback); only server-registered tools with matching names run.
- **Wired-but-dead**: `ChatRequest.tools`/`tool_choice` (`src/api/models/requests.py:241-249`, docstring claims REPL exposure) have **no consumer anywhere in the `/chat` pipeline** (grep across `chat.py`, `chat_pipeline/*`, `repl_environment/*`, `graph/*`). `call_orchestrator_forced` dutifully forwards them (`scripts/benchmark/seeding_orchestrator.py:825-827`) into that dead field. Also flag-off: `deferred_tool_results`, `script_interception` (`src/features.py:105-107` region).

### Role grants — does the architect have tool access?

Registry `tool_permissions` blocks exist for exactly two roles: frontdoor (web+file+data, `orchestration/model_registry.yaml:1297-1301`) and worker_general (file+data, no web, `write_file` forbidden, `:1688-1695`). `architect_general` (`:1410`) has **no block**, so `load_role_permissions` skips it (`src/registry/tool_registry.py:337-349`). Consequence depends on the policy engine:

- Legacy path: unknown role → **deny** (`tool_registry.py:400-404`).
- Cascading path (**what production runs**, `ORCHESTRATOR_CASCADING_TOOL_POLICY=1`): no global policy layers are ever registered (no `add_global_policy` callers) and no role layer exists → `resolve_policy_chain` starts from `all_tools` and nothing narrows it (`src/tool_policy.py:120-149`) → **architect_general gets every registered tool by default-allow fall-through**. Fine for an eval; worth an explicit policy layer before any hostile-input scenario.

### (c) Running a coding/tool-use eval through the orchestrator — mostly already built

- **Existing tool-use eval**: the eval tower appends tool-use sentinels to T0 when `AUTOPILOT_TOOL_SENTINELS=1` (`scripts/autopilot/eval_tower.py:2255-2290`): questions pin `force_mode="repl"`, require a counted `get_eval_secret` call, and score against runtime-minted tmpfs secrets (`src/builtin_tools.py:38-42, 51-82`; `src/tools/eval_secret.py:1-45`). The telemetry contract (counts, per-tool success, request-local isolation) is separately gated by `scripts/autopilot/gate3_tool_telemetry.py:1-44`. Response-side signals: `tools_used`, `tools_called`, `tool_timings` on `ChatResponse` (`src/api/models/responses.py:112-117`).
- **Harness entry point**: `call_orchestrator_forced(prompt, force_role=…, force_mode="direct"|"repl"|"delegated", …)` (`scripts/benchmark/seeding_orchestrator.py:681-830`) — already used by the eval tower (`eval_tower.py:2584, 2656-2661`) and the model-grader/llm-judge paths. Forced-role real-mode probes skip internal MemRL scoring (`memrl.py:210-221`), keeping eval reward injection clean.
- **What an architect tool-use/coding eval needs**: (1) `force_role="architect_general", force_mode="repl"` — works today; architect has blanket tool access under cascading policy; (2) scoring via `debug_scorer` `code_execution` (`debug_scorer.py:389+`) or the Scoring-Verifiers adapter (`scripts/benchmark/scoring_verifiers_adapter.py`); (3) if the eval wants *custom* tools, they must be **registered server-side** (like `get_eval_secret`) — caller-supplied `tools=` will not execute (dead on `/chat`, prompt-bridge-only on `/v1`); (4) if delegated-mode behavior is in scope, pass `allow_delegation=True` per-request (`delegation_stage.py:96-101`) — and note that flips on the Q2 review-truncation path.

## Q4 — scoring/extraction inventory & consolidation

| # | Implementation | Purpose | Mechanism | Verbose-penalty risk | Live? | Could adopt canonical contract? |
|---|---|---|---|---|---|---|
| 1 | `scripts/benchmark/debug_scorer.py` (score_answer + 10 methods) | Seeding + eval-tower scoring; **feeds injected MemRL rewards** | Multi-strategy regex (last-match, own-line letters), code exec, math_verify, llm_judge; hard-fails on scorer unavailability (:35-46) | **Low** (B7-hardened); residual: A-H not A-J; loose last-standalone-letter fallback = false-positive risk (:269-272) | Yes (eval/seeding) | **Yes — primary target.** Replace `_extract_multiple_choice_letter`/exact-match extraction with canonical `extract_letter_answer`/`extract_exact_answer` |
| 2 | `src/graph/answer_resolution.py` | REPL max-turns/budget rescue extraction | `FINAL()` regex; `_PROSE_ANSWER_RE` **first-match** `.search` (:79) + bare `[A-D]` line (:84) | **Medium** (first-match on repeated "answer is…" picks the earliest — stale-class cousin), but rescue-only and rescue *grants* success | Yes (rescue path) | Yes — swap `_extract_prose_answer` internals for canonical last-match semantics |
| 3 | `src/api/routes/chat_delegation_decision.py` | Architect TOON `D\|/I\|` decision parse + MCQ rescue | First-match `D\|[A-D]` (:66), answer-is rescue (:162), last-`D\|X` fallback (:176-180) | Low-medium (affects answer fidelity, not reward; `success` only checks `[ERROR`) | Delegated mode: off by default, per-request opt-in | Partially — MCQ rescue block could call canonical extractor |
| 4 | `src/pipeline_monitor/model_grader.py` | Post-hoc diagnostic grading (judge) | Judge letter from **last non-empty line only** (:173-184); None on miss | **High** (bug class) | **Dead** — zero callers | Yes, if ever revived; otherwise delete |
| 5 | `src/proactive_delegation/review_service.py` | Architect review of subtasks/plans → `all_approved` reward | JSON extract w/ fence strip + `{…}` rescue; parse-fail → request_changes; **candidate truncated to 500 chars** (:420) | **High** (truncation bias + fail-closed parse), couples to reward | Dormant (flags off, `orchestrator_stack.py:1573-1575`) | Should adopt `review_grammar.parse_review_decision` + drop/raise the truncation before any re-enable |
| 6 | `src/proactive_delegation/rubric_review.py` + `review_grammar.py` | Two-turn rubric author/grade | Balanced-JSON scanner, schema-validated, loud on total parse failure | **None** (best-in-repo contract) | Dormant (no callers; H2 pending) | Is itself a candidate house standard for judge output |
| 7 | `orchestration/repl_memory/q_judge.py` (ClaudeAsJudge) | Optional graded rewards | `SCORE:` line-prefix parse; silent default 1/3 (:159-175) | Medium (silent default) | Dormant (`use_claude_judge=False`, `memrl.py:391`) | Yes — or replace with rubric_review contract |
| 8 | `scripts/autopilot/rubric_scoring.py` | Eval-tower rubric judge + deterministic T1 fallback | Judge prompt + heuristic scores; `_length_score` rewards up to 250 words (:330-333) | None (mildly **pro**-verbose in fallback) | Yes (eval tower) | Orthogonal (rubric, not answer extraction) |
| 9 | `src/api/routes/chat_review.py` `_architect_verdict` | Live answer-review gate | `OK`/`WRONG` prefix parse (:117-120); fail-open | Low (no reward coupling; verbose judge silently neuters review) | Yes | Could emit via review_grammar schema instead |
| 10 | `src/classifiers` quality_detector (+ `_quality_escalate`, `stages.py:45-72`) | Degeneration detection → cheap→coder swap | Text heuristics, not answer extraction | None identified (repetition/garbage detection) | Yes | N/A |

(`src/bradley_terry.py` audited: pure ranking math over already-computed scores — no extraction, excluded.)

### Cross-repo packaging constraint & recommendation

The dependency map records orchestrator→research as a **DATA** dependency, not code (CLAUDE.md Dependency Map; `.claude/dependency-map.json`), and `seeding_scoring.py:32-60` documents exactly why runtime cross-repo imports are dangerous here (import-order-dependent scorer identity). So do **not** import the research lib at runtime. Recommended shape:

1. **Vendored canonical module**: copy `answer_scoring.py` (and `code_exec_scorer.py` if the coding eval adopts it) into `epyc-orchestrator/scripts/benchmark/` as a clearly-marked vendored file with an upstream commit pin in its header; `debug_scorer` imports extraction primitives from it (path-pinned, same trick as `seeding_scoring._load_orchestrator_debug_scorer`).
2. **Contract-tests-as-data**: commit the same golden corpus (B7 corpus + the verbose/bare-letter regression fixtures from the 2026-07-24 incident) as a JSONL fixture in **both** repos; each repo's CI runs its own scorer over it. A drift test compares the vendored file's hash against the pinned upstream hash and fails with a "re-vendor" instruction. This keeps the coupling data-only, satisfying the dependency-map constraint while making silent divergence impossible.

## Recommended 1c actions

1. **Vendor the canonical extraction contract into `debug_scorer`** (swap `_extract_multiple_choice_letter` + exact-match extraction internals; keep `debug_scorer`'s dispatch, error taxonomy, and code-exec/math paths). Effort: **M**. Risk: changes eval verdicts at the margins (A-H→A-J widening; removal of the loose last-standalone-letter fallback will *lower* some scores that were false positives) — run the golden corpus + one paired re-score of a recent eval batch before/after, and era-label the change per MEASUREMENT.md.
2. **Add the shared golden-corpus drift test (both repos) + upstream-hash pin.** Effort: **S**. Risk: none at runtime; CI-only.
3. **Fix `answer_resolution._extract_prose_answer` to last-match semantics** (or delegate to the vendored extractor) and extend the bare-letter rescue beyond A-D. Effort: **S**. Risk: rescue path only; changes which answer is rescued on multi-"answer is" outputs — strictly closer to the model's final statement.
4. **Before any re-enable of `parallel_execution`/`architect_delegation`: remove or raise the 500-char review truncation and route verdicts through `review_grammar.parse_review_decision`** (schema-validated, accounting-friendly), and add a regression test that a correct answer with a >500-char preamble is approvable. Effort: **M**. Risk: longer reviewer prompts cost architect tokens; measure review latency before/after. This is the single change that removes the only judge→reward verbose bias in the codebase.
5. **Delete or quarantine `model_grader.py`** (dead, bug-class-carrying; its specs dir is unused) — or, if the post-hoc grading idea is wanted, rebuild it on the rubric_review contract. Effort: **S**. Risk: none (no callers).
6. **For the architect tool-use/coding eval**: build on `call_orchestrator_forced(force_role="architect_general", force_mode="repl")` + server-registered eval tools (the `get_eval_secret` pattern) + `tools_called`/`tool_timings` telemetry; score with `debug_scorer` `code_execution` / Scoring-Verifiers. Either wire `ChatRequest.tools` into the REPL bridge (M) or explicitly document it as unsupported and strip the misleading field docstring (S). Risk note: architect currently has blanket tool access via cascading default-allow — add an explicit role policy layer if the eval includes adversarial prompts.

---
*Audit was read-only; no source, handoff, or index files were modified. All line numbers refer to working-tree state on 2026-07-24.*
