# Scorer-Fork Drift Audit — Seeding/Routing vs Eval-Tower B7 Scorer

**Commissioned:** operator, 2026-07-22 · **Type:** READ-ONLY audit · **Author:** audit session
**Scope:** Does the seeding / specialist-routing scoring path carry any defect class that the
eval tower's B7 program fixed? Are there additional forks (research repo) that do?
**Method:** static read of both repos + offline execution of the actual scorer functions on
synthetic strings (pure functions, no inference, no HTTP, no stack). Proof harnesses under
`/mnt/raid0/llm/tmp/scorer-audit-scratch/proof*.py`.

---

## Executive Summary

**Headline: the seeding deterministic-scoring path is NOT an independent scorer fork.**
`scripts/benchmark/seeding_scoring.py::score_answer_deterministic` explicitly loads and
**delegates to the orchestrator's B7-hardened `scripts/benchmark/debug_scorer.py`** — pinned
under `sys.modules['epyc_orch_debug_scorer']` via same-directory `importlib` (the A2/SCORE-02
fix, `2a41c0bc`). Proven at runtime: seeding resolves to
`/mnt/raid0/llm/epyc-orchestrator/scripts/benchmark/debug_scorer.py` and returns **verdict-for-verdict
identical** results to a direct `debug_scorer.score_answer` call on every synthetic case
(proofs P-01…P-13). **Therefore every value-returning B7 fix is inherited by the seeding path
with ZERO scoring drift**: SCORE-03 final-answer-region, SCORE-06 boundary substring +
comma/digit-separator, SCORE-16 nested-`\boxed{}`, SCORE-24 multiset F1 + capture-group guard,
SCORE-23 `str()`-wrap, multiple-choice textual-label + overlap, llm_judge fast-path boundary
anchoring, SCORE-21 vacuous-oracle rejection, SCORE-25 unknown-verifier rejection.

**The real pre-B7 fork is the RESEARCH repo's `scripts/benchmark/debug_scorer.py`** (758 lines
vs the orch copy's 1087). It is a stale copy that carries **every defect class B7 fixed**
(proven: "63" matches "630"; nested `\boxed{}` missed; set- not multiset-overlap F1; letter-only
multiple-choice; unknown verifier → silent substring "correct"; entry_point → synthesized
`assert solve()==42` executed; `assert True` vacuous oracle accepted; llm_judge → silent
substring fallback; `math_verify` method entirely absent; non-string expected → AttributeError).
**But it is NOT on the specialist-routing seed path** — there is no `seeding_*.py` / `seed_specialist_routing.py`
fork in the research repo (searched; none exist). The research `debug_scorer.py` is consumed only
by research **benchmark/experiment** scripts (`score_outputs.py`, `eval_tale_budget.py`,
`eval_trimr.py`, `memory_viability_runner.py`, `short_mk_voting.py`, `qwable_verifier_selector_runner.py`,
`review_f1/harness.py`). Its blast radius is **research benchmark conclusions, not routing seeds
or the MemRL policy.**

**Where the seeding path DOES still drift from the eval tower — three REL-1 accounting/robustness
gaps, and two of them reach the MemRL reward store:**

1. **[HIGH] In-band `[ERROR:` / circuit-open answers are scored as WRONG (0.0 reward into MemRL).**
   The eval tower has an explicit REL-1 Guard 1 (`eval_tower.py:2448-2465`, `_inband_error_text`)
   that converts an HTTP-200 `answer="[ERROR: Backend unavailable (circuit open): ...]"` (with
   `error=None`) into an **excluded error row**. The seeding path has **no such guard**:
   `_build_role_result` (`seeding_eval.py:322-329`) classifies only `resp["error"]` via
   `INFRA_PATTERNS`, and the seeding HTTP wrapper (`seeding_orchestrator.py:787-808`) only surfaces
   structured `error_code`/`error_detail`, never an in-band `[ERROR:` answer. Proven (P-11):
   seeding scores the circuit-open banner as `False`. That `False` becomes a **binary 0.0 reward
   injected into MemRL** (`_inject_3way_rewards_http`) — the learned router is trained that the role
   "failed" when in fact the backend was unavailable. Seeding's `INFRA_PATTERNS` *does* contain
   `"circuit open"` / `"backend unavailable"`, so the list is **complete**; the defect is the
   **application point** (error-field only, never the answer text).

2. **[HIGH/MED] `ScoringUnavailableError` is uncaught in the seeding path → crash or silent drop.**
   B7's raise-based fixes (SCORE-04/05 entry_point-without-oracle, `math_verify` unavailable/bad-gold,
   llm_judge unreachable, SCORE-25 unknown verifier) make `score_answer` **raise**. The eval tower's
   per-question `try/except Exception` (`eval_tower.py:2575-2591`) turns that raise into an
   `error`-stamped `QuestionResult`, later excluded from the denominator (`:2991`
   `scored_results = [r for r in results if not r.error]`) — REL-1 correct. The seeding path calls
   `score_answer_deterministic` at `seeding_eval.py:329` with **no try/except**, and no caller up to
   the main loop wraps it: `_eval_single_config` → `evaluate_question_3way` → the driver's
   `try: … finally:` at `seed_specialist_routing.py:341/643` has **no `except`**. So a raise from the
   **main 3-way path crashes the entire seed run**; on the **debugger-retry path** it is swallowed by
   the `except Exception … "non-fatal"` at `:640-641` and the question **silently vanishes** (no row,
   no error accounting). Proven (P-08, P-09): seeding raises `ScoringUnavailableError` /
   `ValueError` on entry_point / unknown-verifier inputs, identical to orch. This is a
   robustness/accounting drift, not a mis-score — it never produces a *wrong verdict*, but it can
   halt a long seed run or silently shrink the sample.

3. **[MED] Seeding does not persist raw response text as a first-class field.** `seeding_telemetry.py`
   and `seeding_checkpoint.py` contain **zero** `answer` fields (grep `-c` = 0); rewards go to MemRL
   as binary pass/fail only. Raw output is recoverable solely via fragile log-**tap** byte offsets
   (`RoleResult.tap_offset_bytes/tap_length_bytes`). So a scorer fix or a suspected parse-failure
   **cannot be cleanly re-scored offline** for seeding runs — the exact capability the architect bench
   *does* have (`architect_bench_rescore.py`: "runner persists full response text … scorer fix
   applied to completed runs without GPU"). This is the `feedback_parse_failure_rate_is_a_scoring_artifact`
   memory ("store responses to re-score offline") only partially satisfied.

**Also surfaced (out of primary scope, flag for follow-up):** a **THIRD** scorer implementation,
research `v7_quality_gate_runner.score_response` (+ `extract_boxed`, numeric→set→sympy math
equivalence), backs the **architect model-selection bench** (`architect_bench_rescore.py`). It is a
separate lineage, **not covered by B7's golden corpus**, and gates a real decision (architect choice).
Recommend a parity check against the B7 golden corpus before the architect bench is decision-graded.

**Net:** the condemned-quality worry — that specialist-routing seeds are selected on pre-B7 scoring —
is **largely unfounded for the deterministic verdict itself** (seeding runs the B7 scorer). The live
exposure is narrower but real: **REL-1 in-band/circuit-open misclassification poisons MemRL rewards**,
and scorer-unavailability is not accounted (crash/drop). The pre-B7 *scoring* defects live in the
research `debug_scorer.py`, which drives research benchmarks, not routing.

---

## Defect-Class Matrix

Legend — **FIXED** = B7 hardening present; **INHERITED** = seeding delegates to the fixed orch scorer
(zero drift); **DEFECT** = pre-B7 behavior present (proven wrong verdict); **N/A** = path not
implemented here; **GAP** = drift specific to this path.

| Defect class | Eval-tower (orch `debug_scorer`/`eval_tower`) | Seeding path (`seeding_scoring`→orch) | Research fork (`epyc-inference-research/.../debug_scorer.py`) | Proof |
|---|---|---|---|---|
| **SCORE-03** final-answer-region extraction | FIXED — `_final_answer_region` gates colon/quote fallback (`debug_scorer.py:970-979`, used `:154,166`) | **INHERITED** (correct=False on CoT-vs-final) | **DEFECT** — colon fallback scans whole answer; matches earlier "answer: 42" → True | P-03 |
| **SCORE-04/05** entry_point oracle / infra→ERROR | FIXED — requires executable `entry_point_cases`/`test_code`; `repr()`-embeds; OSError→`ScoringUnavailableError`; safe-identifier guard (`:429-495`) | **INHERITED** (raises `ScoringUnavailableError`) — *but raise not caught by seeding → crash/drop (GAP-2)* | **DEFECT** — synthesizes+executes `assert solve()==42` (`:324-326`); string expected→NameError; OSError→False | P-08 |
| **SCORE-06** boundary-anchored substring | FIXED — `_contains_text_unit` word-boundaries + digit-separator strip (`:642-672,982-994`) | **INHERITED** ("63"↛"630"=False; "479,001,600"↔"479001600"=True) | **DEFECT** — plain `in` (`:508-511`): "63"∈"630"→True; comma form→False | P-01, P-02 |
| **SCORE-16** boxed-answer fallback | FIXED — brace-balanced nested `_extract_boxed_answer` (`:946-967`, used `:114`) | **INHERITED** (nested `\boxed{\frac{1}{2}}`→True) | **DEFECT** — single-level `\boxed\{([^{}]+)\}` misses nested → False | P-06 |
| **SCORE-21** vacuous-oracle rejection | FIXED — `_has_executable_assertion` rejects `assert True` (`:361-376,435`) | **INHERITED** (`assert True`→False) | **DEFECT** — appends & runs `assert True` → any answer passes → True | P-10, P-07 |
| **SCORE-23** `str()`-wrap non-string expected | FIXED — `expected = "" if None else str(expected)` (`:71`) | **INHERITED** (int expected 42→True) | **DEFECT** — no wrap; `expected.strip()` on int → AttributeError | P-12 |
| **SCORE-24** multiset F1 + capture-group guard | FIXED — `Counter` multiset overlap (`:726-731`); `_compile_single_group_pattern` guard (`:937-943`) | **INHERITED** (cat×3 vs cat cat dog→True; 2-group→ValueError) | **DEFECT** — `set(...)&set(...)` (`:564`)→False; 2-group→AttributeError | P-05, P-04 |
| **Multiple-choice** textual-label + overlap | FIXED — `_extract_multiple_choice_text_index`, `max(matches)` end/length overlap, letter guard normalization (`:175-292`) | **INHERITED** (textual "black cat"→True) | **DEFECT** — letter-only; textual expected → False | P-06b |
| **llm_judge fast-path boundary anchoring** | FIXED — `_contains_text_unit` fast-path; judge-unreachable→`ScoringUnavailableError` (no substring fallback) (`:796,831-841`) | **INHERITED** ("cat"∉"concatenate" boundary; raise on dead judge — *GAP-2 uncaught*) | **DEFECT** — plain substring fast-path; judge dead → **silent substring fallback** (`:655-658`) | P-13 |
| **Infra-error classification (REL-1)** | FIXED — Guard 1 in-band `[ERROR:`→error row (`eval_tower.py:2448-2465`); Guard 2 forced-role mismatch (`:2467+`); structured `error_code` | **GAP** — `INFRA_PATTERNS` list is complete but applied to `resp["error"]` **only**, never the in-band answer; **no** forced-role guard → circuit-open scored WRONG → 0.0 MemRL reward | N/A (research fork not on this path) | P-11 |
| **Parse-failure raw-response storage** | Persists per-question rows w/ answers (eval-tower window / package_real_suite) | **GAP** — telemetry/checkpoint store **0 answer fields**; only recoverable via fragile log-tap offsets → weak offline re-score | Research runner persists full text (`architect_bench_rescore` re-score works) | grep `-c answer` = 0 |
| **SCORE-07** rubric range-validation | FIXED in eval tower (B7b `df…`, RATIFIED 2026-07-21) — range-VALIDATE not clamp | **N/A** — seeding has no rubric path; `scoring_method="rubric"`→`ValueError` (would crash, not mis-score) | N/A | P-14 |
| **SCORE-08/09** rubric provenance / empty≠1.0 | FIXED in eval tower (B7b) — `rubric_source` provenance; empty rubric ≠ 1.0 | **N/A** — no rubric path in seeding | N/A | P-14 |
| **SCORE-12** phantom `pass_rate` confidence | FIXED in eval tower (B7b) — phantom static read removed; EV-CONF real confidence | **N/A** — seeding does not compute rubric/confidence rows | N/A | — |
| **`math_verify` method** (SCORE-01 lineage) | FIXED — real threaded `_score_math_verify`, `parsing_timeout=None`/`timeout_seconds=None`, gold-defect→ERROR, model-parse-fail→False (`:846-922`) | **INHERITED** (method present; raises on unavailable — *GAP-2 uncaught*) | **DEFECT** — `math_verify` **absent from scorers dict** → `ValueError: Unknown scoring method` on every MATH row | P (math block) |

---

## Proofs (input → output)

All produced by `/mnt/raid0/llm/tmp/scorer-audit-scratch/proof{,2,3,4}.py` run under the orchestrator
venv. `seeding` = `seeding_scoring.score_answer_deterministic`; `orch`/`research` =
`debug_scorer.score_answer` from the respective repo copy.

**Identity (A):** `seeding._load_orchestrator_debug_scorer().__file__` →
`/mnt/raid0/llm/epyc-orchestrator/scripts/benchmark/debug_scorer.py` (seeding uses the orch copy).

```
P-01  SCORE-06  ("The count is 630 items", "63", substring)      orch=False  seeding=False  research=True   [correct=False]
P-02  SCORE-06b ("Result: 479,001,600.", "479001600", substring) orch=True   seeding=True   research=False  [correct=True]
P-03  SCORE-03  ("The answer: 42\nActually the final result is 43", "42", exact_match)
                                                                  orch=False  seeding=False  research=True   [correct=False; research colon-scans whole answer]
P-04  SCORE-24b (extract_pattern "(a)(b)", f1)                    orch=RAISE ValueError(one capture group)   research=RAISE AttributeError('tuple' no strip)
P-05  SCORE-24  ("cat cat cat", "cat cat dog", f1 thr .5)         orch=True   seeding=True   research=False  [multiset F1=.667 vs set F1=.333]
P-06  SCORE-16  ("...\boxed{\frac{1}{2}}", "\frac{1}{2}", exact)  orch=True   seeding=True   research=False  [nested-brace boxed]
P-06b MC        ("The answer is black cat.", "black cat", multiple_choice, choices=[black cat,cat,dog])
                                                                  orch=True   seeding=True   research=False  [textual label]
P-07  SCORE-21  ("assert True" test_code, code_execution)         orch=False                 research=True   [vacuous oracle]
P-08  SCORE-04/05 (entry_point="solve", no oracle, code_execution) orch=RAISE ScoringUnavailableError  seeding=RAISE ScoringUnavailableError  research=True [executes synth assert]
P-09  SCORE-25  (verifier="typoed_verifier_name", programmatic)   orch=RAISE ValueError  seeding=RAISE ValueError  research=True [silent substring→junk correct]
P-10  SCORE-21  (seeding delegate, "assert True")                 seeding=False            [inherits rejection]
P-11  REL-1     seeding("[ERROR: Backend unavailable (circuit open): http://localhost:8082]", "42", substring) = False
                seeding._classify_error(None)="none"  ;  _classify_error(<same text as error field>)="infrastructure"
                → in-band answer with error=None is scored as a WRONG answer (0.0 reward), never excluded.
P-12  SCORE-23  ("42", expected=int 42, exact_match)              orch=True   seeding=True   research=RAISE AttributeError('int' no strip)
P-13  llm_judge fast-path  _contains_text_unit("we concatenate strings","cat")=False (orch)  ;  "cat" in "…concatenate…"=True (research)
P-14  rubric    seeding(…, "rubric") = RAISE ValueError: Unknown scoring method: rubric   [no rubric path in seeding]
math  research.score_answer("x","x","math_verify") = RAISE ValueError: Unknown scoring method: math_verify  ; orch has _score_math_verify=True
```

---

## Verdict-Flow / Decision-Impact Map

- **Seeding deterministic verdict** (`RoleResult.passed`) → `compute_3way_rewards` → **binary reward
  1.0/0.0** → `_inject_3way_rewards_http` → **orchestrator MemRL reward store** (trains the learned
  routing policy `P(success|action)` per `project_learned_routing_controller`). Infra errors
  (`error_type=="infrastructure"`, i.e. `passed=None`) are **skipped** from reward injection
  (`seeding_eval.py:1196-1197`) — so the *classification* of a failure as infra vs task decides
  whether a 0.0 reward is written. This is why GAP-1 (in-band circuit-open misclassified as
  task-fail) directly **poisons the router**, and GAP-2 (uncaught scorer-unavailability) can crash
  a seed run or silently drop questions from the reward sample.
- **Seeding also feeds** `print_3way_summary` tallies and the debugger's per-batch regression logic —
  same verdict, same exposure.
- **Research `debug_scorer.py`** → research benchmark/experiment scripts → research benchmark numbers
  and analysis (compaction, memory, voting, verifier-selection). **Not** the routing-seed pipeline,
  **not** the lean/model registry directly. Decision-impact: research conclusions can be silently
  wrong (all pre-B7 classes), but no routing seed is selected on it.
- **`v7_quality_gate_runner.score_response`** (research) → `architect_bench_rescore` → **architect
  model-selection bench** (`project_architect_model_selection_bench`). Separate scorer lineage;
  unaudited vs B7 golden corpus.

---

## Prioritized Fix List (ranked by decision-impact)

1. **[HIGH · corrupts MemRL] Add REL-1 in-band `[ERROR:`/circuit-open + forced-role guards to the
   seeding scoring path.** Port the eval tower's `_inband_error_text` (and forced-role serving-mismatch)
   check into `_build_role_result` (`seeding_eval.py:320-329`) **before** scoring: if `not error` and
   the answer is an in-band `[ERROR:` banner, set `error_type="infrastructure"` (→ `passed=None`, →
   reward-skip). This closes the poisoned-reward path. (List contents already complete; only the
   application point is missing.)

2. **[HIGH/MED · crash / silent drop] Catch `ScoringUnavailableError` (and `ValueError` from
   unknown-method/verifier) at the seeding scoring boundary and convert to an excluded row.** Wrap the
   `score_answer_deterministic` call (`seeding_eval.py:329`) so a scorer-unavailability raise becomes an
   `error_type`-stamped result excluded from reward injection — matching `eval_tower.py:2575-2591`/`:2991`.
   Prevents one MATH/PhysReason/HumanEval-entry_point row from crashing a long seed run or silently
   vanishing from the sample.

3. **[MED · re-score capability] Persist raw response text in seeding telemetry/checkpoint.** Add the
   `answer` (and `expected`/`scoring_method`/`scoring_config`) to the seeding per-question record so a
   future scorer fix or parse-failure investigation can re-score seed runs offline without re-inference
   (parity with `architect_bench_rescore`). Today only fragile tap byte-offsets exist.

4. **[MED · research conclusions] Retire or hard-alias the research `debug_scorer.py` to the orch B7
   copy.** It is a fully pre-B7 fork (all classes proven). Either delete it and repoint its consumers,
   or make them load the orchestrator copy by path (the A2 pattern). Until then, treat any research
   benchmark scored by it as pre-B7 (observation, not decision-grade).

5. **[LOW/FOLLOW-UP · architect decision] Parity-check `v7_quality_gate_runner.score_response` against
   the B7 golden corpus** before the architect-selection bench is decision-graded; it is a third,
   uncovered scorer lineage.

---

### Appendix — files inspected

- Eval-tower B7 scorer: `/mnt/raid0/llm/epyc-orchestrator/scripts/benchmark/debug_scorer.py` (1087 L, B7 commits `07a20a7c`, `8f24679a`, `0ddce51d`; B7b golden-corpus extension)
- Seeding scorer facade: `/mnt/raid0/llm/epyc-orchestrator/scripts/benchmark/seeding_scoring.py` (delegates; own `INFRA_PATTERNS`)
- Seeding eval/driver: `.../seeding_eval.py` (`_build_role_result:304`, scoring `:329`), `.../seed_specialist_routing.py` (driver `try/finally:341/643`), `.../seeding_orchestrator.py` (HTTP `:787-838`)
- Eval-tower REL-1 guards: `/mnt/raid0/llm/epyc-orchestrator/scripts/autopilot/eval_tower.py` (`:2448-2465`, `:2575-2591`, `:2991`)
- Research fork: `/mnt/raid0/llm/epyc-inference-research/scripts/benchmark/debug_scorer.py` (758 L, pre-B7)
- Third fork: `/mnt/raid0/llm/epyc-inference-research/scripts/benchmark/v7_quality_gate_runner.py` (via `architect_bench_rescore.py`)
- SCORE-NN taxonomy source: `/workspace/handoffs/active/eval-tower-architecture-audit-2026-07-20.md` (rows SCORE-01..25, B7 checklist items)
- Proof harnesses: `/mnt/raid0/llm/tmp/scorer-audit-scratch/proof{,2,3,4}.py`

---

## Implementation Record — seeding-path honesty fixes (2026-07-22)

Implemented by the seeding-path fix session (owner files: `seeding_scoring.py`,
`seeding_orchestrator.py` + tests; wiring in `seeding_eval.py`). No process
management, no network, offline verification only (throwaway interpreters +
mocked responses + targeted pytest). All 61 targeted seeding-scorer tests pass;
`ruff` clean on the three source files.

- [x] **Fix 1 [HIGH · MemRL] — in-band `[ERROR:`/circuit-open answers → EXCLUDED, not scored WRONG** ✅ 2026-07-22
  - `seeding_scoring._inband_error_text()` added (mirror of `eval_tower._inband_error_text`, anchored at start-of-answer after `lstrip`).
  - `seeding_scoring._classify_error()` now classifies any `[ERROR:`-prefixed error string as `infrastructure` (so a generic in-band banner not matching an `INFRA_PATTERNS` substring is still excluded, matching eval-tower REL-1 intent).
  - `seeding_orchestrator._surface_inband_error()` added and wired into all three `call_orchestrator_forced` response-assembly sites (200 path, 4xx/5xx path, watcher path): copies an in-band `[ERROR: ...]` answer into `data["error"]` (+`failure_reason="inband_error"`) only when no structured error is already present. Raw `answer` untouched.
  - `_build_role_result` also applies Guard 1 directly (defense-in-depth) so any resp reaching scoring with an in-band banner is excluded even if not surfaced upstream. Result: `error_type="infrastructure"` → `passed=None` → reward-skipped (`seeding_eval.py` reward block keys on `error_type=="infrastructure"`).
- [x] **Fix 2 [HIGH/MED · crash/silent-drop] — `ScoringUnavailableError`/`ValueError` caught → excluded row, run continues** ✅ 2026-07-22
  - `seeding_scoring.score_answer_or_error()` added: wraps the B7 scorer, returns `(bool, None)` for a normal verdict or `(None, "scoring_unavailable: …" | "scoring_error: …")` on a scorer raise — never propagates.
  - `_build_role_result` now scores via `score_answer_or_error`; a `None` verdict is stamped `error_type="infrastructure"` (excluded) and logged. Covers BOTH the main 3-way path and the debugger-retry path (both route through `evaluate_question_3way → _build_role_result`); the driver no longer crashes and no question silently vanishes.
- [x] **Fix 3 [MED · re-score] — raw answer + scoring context persisted for offline re-score** ✅ 2026-07-22
  - Verified the raw per-role `answer` was **already** persisted in the checkpoint JSONL via `dataclasses.asdict(RoleResult)` — the audit's finding-3 proof (`grep -c answer = 0`) checked the two *source* files, not the serialized artifact; confirmed on a live checkpoint (`answer` field present per role). Added a regression test guarding the round-trip.
  - The real offline-rescore gap was the missing scoring context: `ThreeWayResult.expected` is truncated to 200 chars and `scoring_method`/`scoring_config` were not stored. `evaluate_question_3way` now writes `metadata["scoring_context"] = {expected (untruncated), scoring_method, scoring_config}`, persisted via the same `asdict` path. A completed seed run is now re-scorable without re-inference (parity with `architect_bench_rescore`).
- [x] **Forced-role fallback mismatch — verified + delegation-aware fix applied** ✅ 2026-07-22
  - `seeding_scoring._forced_role_serving_mismatch()` added (mirror of eval-tower Guard 2). Applied in `_build_role_result` **gated on `allow_delegation is False`**. Verification finding: a verbatim port would be a NEW defect — the seeding ARCHITECT config runs `allow_delegation=True`, where `routed_to != force_role` is the *expected* delegated behavior; firing there would wrongly exclude every architect delegation and itself poison MemRL. Guard 2 therefore fires only for the delegation-OFF configs (SELF:direct, SELF:repl, VL-architect direct) where a `routed_to` mismatch genuinely means a silent circuit-open cross-role fallback.

### Files changed (all under `/mnt/raid0/llm/epyc-orchestrator`)
- `scripts/benchmark/seeding_scoring.py` (owned) — `_inband_error_text`, `_forced_role_serving_mismatch`, `score_answer_or_error`, `_classify_error` in-band prefix rule.
- `scripts/benchmark/seeding_orchestrator.py` (owned) — `_surface_inband_error` + 3 wiring sites.
- `scripts/benchmark/seeding_eval.py` (wiring, not in owner set but on the seeding path; no concurrent owner) — Guards 1/2 + scorer-catch in `_build_role_result` (new `allow_delegation` param threaded from `_eval_single_config`); `scoring_context` in `evaluate_question_3way`.
- Tests: `tests/unit/test_seeding_scoring.py`, `tests/unit/test_seeding_orchestrator.py`, `tests/unit/test_seeding_eval.py`.

### Duplication / follow-up notes for later unification
- `_inband_error_text` and `_forced_role_serving_mismatch` are **local copies** of the `scripts/autopilot/eval_tower.py` reference implementations (that file is owned by another session and was READ-only for parity). Recommend a later unification into one shared module imported by both the eval tower and the seeding path.
- **Residual (out of scope, flagged):** `scripts/benchmark/seeding_legacy.py:~331` (the *deprecated* `ComparativeResult` path, `evaluate_question`) still scores via a bare `score_answer_deterministic` with the same pre-guard pattern (no in-band/forced-role guard, no scorer-unavailability catch) and can `_inject_rewards_http`. It is imported `# noqa: F401` (unused) by the live driver and is **not** the active 3-way MemRL path, so it was left untouched — but it is a parallel copy of the same defect and should get the same treatment if ever reactivated.
- **Deviation from audit finding-3 literal wording:** the raw `answer` was already persisted; the substantive fix delivered is the scoring-context persistence that actually enables the stated purpose (offline re-scoring), plus a guarding test.
