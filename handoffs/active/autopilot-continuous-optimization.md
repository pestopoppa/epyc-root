# AutoPilot: Continuous Recursive Optimization

> **Current checkpoint — 2026-09-25.** AutoPilot remains intentionally stopped; inference resources are operator-owned. Production baseline evidence is ratified on the frozen v10 kernel. Any restart remains a separate explicit operator action. The immediate research-intake path freezes the existing EPYC replay inputs under **AP-DGM-PROV**, runs the Shinka-style control in **SEQ-SHINKA-1**, and only then adds DGM/HGM formulas under **AP-DGM-SEL**. No selector, objective transform, or autonomous-science result has production authority.

> **Compaction boundary.** Completed implementation history, dated runtime checkpoints, and the full pre-compaction ledger moved to [the 2026-06-21 through 2026-09-25 history sibling](../completed/autopilot-continuous-optimization-history-2026-06-21-through-2026-09-25.md). Earlier history remains in [the through-2026-06-20 sibling](../completed/autopilot-continuous-optimization-history-through-2026-06-20.md). This active file retains every open task and the context attached to it.

**Created**: 2026-03-08
**Updated**: 2026-09-25
**Location**: `epyc-orchestrator/scripts/autopilot/`

## Current execution map

1. Freeze the existing EPYC journal/candidate graph and its replay identities (**AP-DGM-PROV Phase A**).
2. Run the shared selector replay: Shinka-style policy first (**SEQ-SHINKA-1**), then DGM/HGM formulas (**AP-DGM-SEL**).
3. Keep autonomous research proposals behind deterministic evaluation, fixed budgets, complete denominators, and human promotion.
4. Resolve existing live-inference and operator gates only at their named boundaries; do not reinterpret a stopped loop as a software blocker.
5. Preserve the v10 production-kernel freeze and use experimental kernel lanes for any kernel-affecting work.

## Active architecture boundary

AutoPilot proposes and evaluates numeric, prompt, routing, and code candidates through the orchestrator. Deterministic policy owns safety gates, budgets, archive admission, baseline promotion, and rollback. The research introduced in September adds replay and evidence contracts; it does not grant the model authority over measurement policy, scorers, production promotion, or the frozen kernel.

## Open work


### Remaining Work — Prioritized

- [ ] AP-26: Test dspy.RLM for autopilot tasks — long-horizon benchmark analysis where metadata-first context exploration avoids context window limits

- [ ] AP-27: Formalize eval tower tiers (T0/T1/T2) as RLVR verification functions with deterministic reward signals per tier (state matching, not LLM-as-judge). **2026-07-11 partial scaffold**: `epyc-orchestrator` commit `7ee919d8` adds `src/autopilot_core/rlvr_tiers.py`, a pure observe-only reward contract with T0 binary, T1 calibrated continuous, and T2/T3 process-attributed reward views plus explicit blockers for missing calibration/process evidence. **2026-07-11 export slice**: `scripts/autopilot/export_rlvr_environment.py` exports prompt-free `ap27_rlvr_environment_row.v1` JSONL from EvalResult/journal artifacts for future RL training. **2026-07-11 report slice**: `EvalResult.to_grep_lines()` emits report-only `METRIC rlvr_*` lines without changing objectives, SafetyGate, Pareto, or journal schema. **2026-07-11 journal slice**: `epyc-orchestrator` commit `69445d43` adds observe-only `eval_details["rlvr_reward"]` journal payloads from the same deterministic contract via the lower-risk main-loop journal assembly point, avoiding the HIGH-risk `EvalTower._aggregate` path. This closes the code-only tier/reward design, offline export, report-only, and journal-payload pieces; AP-27 remains open for inference-dependent Ouro integration. **Implementation plan**: See [eval-tower-verification.md](eval-tower-verification.md) EV-1–EV-7. Depends on EV-4 (calibration baseline) and P7 Ouro results.

#### AP-26/AP-27 operator gate packet - prepared 2026-07-11

This packet is staging only; it does not run live RLM tasks, start Ouro training/inference, change SafetyGate/Pareto objectives, or enable the planner spend breaker.

- **AP-26 dspy.RLM live test:** non-inference staging is complete when the RLM endpoint health check still passes and the candidate task has a bounded long-horizon trace fixture with an expected metadata-first win condition. The remaining acceptance evidence must come from a live operator-approved task window: same task against non-RLM and RLM paths, wall-clock/context-window diagnostics, exact model endpoints, and the error class if RLM fails. Do not count the existing `configure_rlm()` health check alone as AP-26 completion.
- **AP-27 RLVR export path:** current code supports prompt-free/offline RLVR rows only. Operator can preview/export existing rows with `cd /mnt/raid0/llm/epyc-orchestrator && python3 scripts/autopilot/export_rlvr_environment.py orchestration/autopilot_journal.jsonl orchestration/autopilot_journal_1.jsonl --output-jsonl orchestration/reports/ap27_rlvr_environment_20260711.jsonl --summary-json orchestration/reports/ap27_rlvr_environment_20260711.summary.json --source-label operator_gate_packet_20260711`. This remains observe/offline data prep.
- **Ouro boundary:** AP-27 stays open until an inference-dependent Ouro integration path exists and passes operator review. The RLVR export, report-only `METRIC rlvr_*` lines, and journal payloads are necessary scaffolding, not a training run or promotion gate.


### Research Intake Update — 2026-08-09: Meta-Evolutionary Search Layer (rec-005)

- [ ] **AP-ME-1 — Per-operator context budgets.** `ShortTermMemory` (AP-22) is a single ~120-line
  budget shared across the whole loop. Give each operator its own bound. Seed values from the shipped
  OpenMLE-Evo config (`OpenMLE-Evo/tts_search/configs/search/airaevo.yaml`): global
  `max_related_cards 3`; improve `ancestor_k 3` / `sibling_k 3`; crossover `2` / `2`; debug
  `max_related_cards 8`. **Offline-first**: measure current per-operator context size before changing
  anything, so the change has a baseline to beat.

- [ ] **AP-ME-3 — Complementarity cue for crossover donor selection**, replacing frequency ranking in
  `informed_crossover_candidates`. **BSV-3 already computes a semantic conflict severity** over shared
  subsystem, files touched, prompt sections touched, feature flags and behavior-signature delta. That
  is a complementarity signal with its sign flipped — crossover donor pairing and BSV-3 conflict
  scoring **must share one function** rather than be built twice with drifting definitions.

- [ ] **AP-ME-4 — Deterministic `error_signature` plus a repeated-failures counter.** Per the
  correction recorded in `autokernel-research-loop.md` §8.4.0, `ExperimentJournal.unfalsified_hypotheses()`
  is a recency window over the last five trials checking presence of a falsifier string only, and
  nothing marks a hypothesis resolved. A deterministic failure signature is the cheapest available
  upgrade and is a precondition for AP-ME-1's debug budget to select anything meaningful.

- [ ] **AP-ME-6 — Negative-evidence rendering discipline.** intake-940#record's dive narrowed this from an
  exclusion filter to a *rendering* rule: a deterministic error signature per card plus a board-level
  repeated-error counter, rendered as one compact typed line rather than raw prior-attempt text.
  Failures still enter context — they enter it small. Pairs with AP-ME-4; feeds AP-ME-1's budgets.


### Deep-Dive Task Proposals — 2026-05-25 (intake-607 Code-as-Agent-Harness §5.2.1 / §5.2.3 / §5.2.4)

- [ ] **BSV-2 — Differential testing on accept.** Before promoting a mutation, run new vs old on the same sentinels and compare behavior (not just aggregate score). Prefer paired sequential execution under identical server/model snapshot for attribution; use parallel execution only when explicitly approved and when concurrency cannot contaminate latency measurements. Reuse the existing T0/T1 tower; the novelty is paired behavioral comparison. Gate on both scalar regression and signature diff severity. **2026-06-21 scaffold**: orchestrator `0943e7c0` adds `scripts/autopilot/bsv_paired_report.py`, a read-only paired report over already-journaled `question_results` vectors. It emits shared-qid coverage, McNemar/accuracy deltas, BSV signature severity, blockers, JSON/Markdown, and nonzero exit on a blocked candidate. Follow-up `5b29eead` adds `eval-result-pair`, so the same report can compare standalone paired-run EvalResult-like JSON artifacts without needing journal ingestion first. Orchestrator `939750c7` adds `scripts/autopilot/bsv_paired_runner.py`: a default-safe plan-only CLI that, with explicit `--run`, applies baseline/candidate params sequentially, evaluates the same core, writes baseline/candidate EvalResult JSON artifacts, restores baseline params by default, and emits the existing BSV paired report. Follow-up `a3570d8d` restores baseline params even when candidate application fails before candidate eval. Orchestrator `2bdb7abc` wires the mutation accept path behind default-off `AUTOPILOT_BSV2_ACCEPT_GATE`: prompt, GEPA, and code mutations run a pre-mutation baseline eval only when the flag is on, compare baseline/candidate EvalResult vectors through the paired-report backend, reject/revert on `gate_decision=block` or blocking signature severity, accept+annotate watch/pass cases, and preserve existing single-eval behavior when the flag is off. Remaining work is operator-approved live paired runs / rollout evidence before enabling the flag in production windows.

- [ ] **BSV-3 — Conflict-aware acceptance.** When two independently-accepted mutations touch the same subsystem (prompt + routing, two prompts, prompt + tool policy, context packer + batch editor), flag potential *semantic* conflict for review rather than blind compose. **2026-06-21 observe-only ledger landed in orchestrator `168e9bd8`**: under `AUTOPILOT_BSV_OBSERVE=1`, frontier/safety-passing trials now append a bounded `bsv_mutation_dependency_ledger` state row and journal `eval_details.bsv_observe.mutation_dependency` / `conflict_report`, keyed by `subsystem`, `files_touched`, `prompt_sections_touched`, `feature_flags`, `behavior_signature_delta`, and `parent_trial`. Conflict severity increases on shared subsystem/file/section/flag overlap, blocking BSV deltas, different behavior surfaces, or disjoint/opposing sentinel movement across accepted mutations. Still observe-only/default-off; open work is production conflict-policy enforcement after BSV-2 paired-gate rollout evidence is available.
  - [x] **BSV-3a — default-off diagnostic-state conflict policy.** `epyc-orchestrator` commit `d9b8a022` adds `AUTOPILOT_BSV3_CONFLICT_POLICY` (`off`/`observe`/`block`/`review`) inside the existing `AUTOPILOT_BSV_OBSERVE=1` post-SafetyGate/post-Pareto block. It can withhold only BSV ledger/incumbent diagnostic-state promotion on configured conflict severities; it does **not** alter SafetyGate, Pareto admission, action accept/revert behavior, blacklists, baselines, routing, or the planner spend breaker. ✅ 2026-07-11

#### BSV-2/BSV-3 operator rollout packet - prepared 2026-07-11

This packet is for rollout evidence only. It does not enable `AUTOPILOT_BSV2_ACCEPT_GATE`, does not switch `AUTOPILOT_BSV3_CONFLICT_POLICY` to enforcement, and does not change live accept/revert behavior.

- **Plan-only paired run preview:** `cd /mnt/raid0/llm/epyc-orchestrator && python3 scripts/autopilot/bsv_paired_runner.py --baseline-params '{}' --candidate-params @/path/to/candidate_params.json --output-dir orchestration/reports/bsv2_paired_preview_20260711`. Omit `--run` to keep it plan-only; plan mode prints target artifact paths but does not create the output directory or paired report.
- **Live paired evidence:** add `--run` only in an operator-approved quiet window. Leave baseline restoration enabled; `--no-restore` is reserved for an explicit operator decision to keep candidate params applied.
- **Evidence fields to inspect:** paired-report `gate_decision`, shared-qid coverage, accuracy delta, McNemar/statistical diagnostics, BSV signature severity, fleet/version marker, restored-baseline status, and any blocking `conflict_report` entries.
- **Promotion boundary:** `gate_decision=block` or blocking signature severity remains a no-go. BSV-3 `block`/`review` policy should not be promoted past observe-only until BSV-2 has live paired-run evidence under the same gate semantics.


### Research Intake Update — 2026-07-14

- [ ] **When AP-29 KnowledgeDistiller is wired** (currently deferred — see AP-29), apply an explicit **predictability + staleness gate** to it: what to precompute, for how many consumers, invalidate on stack/config change (framing from intake-819 + the 2026-05-20 predictability-co-objective note; adopt_patterns only, no importable artifact). This is a rider on AP-29, **not** new standalone scaffolding.


### Research-intake integration — 2026-07-22 (measurement-discipline hardening + orx/OpenHyra patterns)

- [ ] Harden keep/revert into an explicit self-scoring candidate contract: always retain a proven baseline (valid rollback before any experiment); accept only on a re-verified strict improvement measured under pinned determinism (fixed threads/seed, N-run mean); atomic config swap; require an inline validity note stating what the number does/doesn't prove — including "no gating on a locally-unmeasurable proxy without held-out re-verify"


### 2026-07-25 — intake Stage-2a dive: GEPA is a guaranteed no-op (P0), plus three overturned premises

- [ ] **AP-19b — supervised first live `gepa_optimize` run (operator-watched), at next stack bring-up.** Operator decision 2026-07-25: blacklist stays lifted; the FIRST live exercise of the repaired path happens in a watched window before any unattended dispatch is relied on. One-shot run; watch the new ERROR path and the journal row. Risk posture verified: adapter evaluates in a SCRATCH prompt root (live frontdoor.md untouched during eval, `gepa_optimizer.py:92-113`), `_prompt_integrity_reason` guards at mutation creation AND apply, applies are git-snapshotted + auto-committed. Cold bring-up recipe: [`esc8-stack-restart-landmine-audit-2026-07-22.md`](../completed/esc8-stack-restart-landmine-audit-2026-07-22.md) § 2026-07-25.

- [ ] **AP-21 re-open, on corrected facts.** Journals (all shards) show **only 8 `gepa_optimize` trials ever** (181, 182, 521, 536, 785, 882, 1137, 1144), exactly **one** ever `keep`. `gepa_ratio` is **absent from live `orchestration/autopilot_state.json`** — the 0.30 is a hardcoded fallback at `autopilot.py:8798` on the *autonomous-fallback* path, not stored state and not the primary dispatch. External evidence stands: arXiv 2607.14004 (Terminal-Bench 2.0, matched budgets) reports the GEPA-optimized agent transferring **below** the unoptimized baseline; 2602.01011 reports GEPA returning the seed prompt unchanged; 2606.19605 reproduces GEPA at −3.78 to +7.97 pp. **Gate on AP-19a.**

- [ ] **AP-29 gate before wiring — narrowed.** `KnowledgeDistiller` has **zero non-test callers** (uninstantiated, not flag-off), so this is a free design change now. **The genuine ask is an episodic-only control arm** (retain + delete, abstraction disabled) that the distiller must beat. Justification: arXiv 2605.12978 feeds **ground-truth solutions** through a streaming consolidator and drops a 19-problem ARC-AGI slice from **100% → 52.6%** at R10 — the fault is provably in the rewriting step. Carry the authors' caveat (*"two repeats per question"*, *"point estimates … rather than formal error bars"*).
  - **PINNED 2026-08-12** — the gate premise is now a TRIPWIRE, not prose: orchestrator
    `015eb8e4`, `tests/unit/test_knowledge_distiller_tripwire.py`. It PASSES while
    `KnowledgeDistiller` has zero non-test callers and FAILS the moment anyone constructs one,
    so whoever wires AP-29 is forced to finish the chain rather than land a caller that quietly
    does nothing. AST-anchored on real `ast.Call` nodes, so a docstring mention cannot trip it.
    **Name trap recorded because it would have closed this row against the wrong class:**
    `scripts/autopilot/actions.py` wires an action called `distill_knowledge`, but it calls
    `EvolutionManager.distill` — a separate class that never touches `knowledge_distiller.py`.
    The module's own docstring claims it is "triggered every N=25 trials by the autopilot main
    loop"; that sentence describes `EvolutionManager`, not itself.
    *(Premise re-derived and mutation-checked independently by `mainC` before acceptance: zero
    real constructions by AST walk, and a construction added to a DIFFERENT tracked file than
    the author used fails the test.)*
  - **Already satisfied — do not file as asks**: raw-trajectory deletion (landed code does **reversible quarantine via validity decay**, `knowledge_distiller.py:316-319`) and unconditional consolidation (predicate is already MDL-gated, `:37-41`, `min_validity=0.10`). **Only the cadence trigger is unconditional.**
  - Prefer **grouped/batched** consolidation over per-checkpoint streaming; independently corroborated by intake-627 (parallel batch beats sequential online editing by +4.0/+6.8 pp).


### 2026-07-29 — intake Stage-4: AP-29 write-gate budget, replayable objective comparison, and the prompt-optimizer of record

- [ ] **AP-29b — Compare correctness-first LEXICOGRAPHIC selection against the scalarized cost-aware reward in chapter 08 by DETERMINISTIC REPLAY over already-persisted autopilot trials.** No new inference: rescore saved outcomes and rebaseline only the objective axis that changed — exactly what `agents/shared/MEASUREMENT_POLICY.md` → *Deterministic replay before regeneration* prescribes. Journal shards (`autopilot_journal.jsonl` + `autopilot_journal_1.jsonl`) already carry the per-trial outcomes this needs.

- [ ] **AP-29c — Name the prompt-optimizer of record as GEPA-class, and adopt compile-on-small-model / deploy-to-large as the CPU-first strategy.** GEPA's cross-model transfer: prompts optimized on **Qwen3-8B** scored **+9.00 aggregate on GPT-4.1-Mini**, beating every optimizer tuned directly on it — which is what makes compiling on a cheap local model economically viable here. Mark **BootstrapFewShot\*** superseded for 2026-era instruct models (**MIPROv2** buys only **+2.6** on Qwen3-8B and **REGRESSES** on AIME/LiveBench). Cost line for any compile is tracked in [`harness-selection-and-integration.md`](harness-selection-and-integration.md) HS-11 (5k-25k LM calls ⇒ region-locked campaign). Sequencing: this is downstream of **AP-19a/AP-19b** — do not re-argue the GEPA pin (AP-42) before the repaired path has run live once.


### AutoPilot end-to-end smoke test — 2026-08-03

First full smoke run of the trial loop. Four defects, three silent.

- [ ] **Reload the escaped live API at the inference owner's next safe boundary.** Named external
      event: the session owning live inference must run the API-only
      `orchestrator_stack.py reload orchestrator` after its in-flight requests drain. Current PID
      3903691 is healthy but stale and carries `PYTEST_CURRENT_TEST` plus pytest `TMPDIR` /
      `ORCHESTRATOR_TMP_DIR`; this session did not kill or reload it across another session's live
      requests (reload-ownership rule, INC-20260728-reload-preemption).

- [ ] **E8 quality-baseline reseed — blocked on an operator source amendment pending since 2026-07-27.**
      *Note 2026-09-16: superseded by operator ruling [`ruling_op19_e8_chain_20260827.json`](../../artifacts/operator/ruling_op19_e8_chain_20260827.json) (root `1ee8bd7c`). The ruling retires the E8 chain and re-anchors the reseed gate to the current eras; the gate binds only at promotion. The text below is historical, and closing this box is the owner's call.*
      The reseed preflight (`--prepare --t2-n 500`) returns `decision_grade: false` with five blockers,
      three of which are stack-shape (`24 unique selected ports`, `exactly five live frontdoors`,
      `both-mode endpoints healthy 6/6`) and two of which are the same missing operator receipt
      (`ratify_e8_quality_baseline_protocol_context_repair_20260727.json`). That receipt cannot be minted
      until the source vector is amended, because **51 fixed-vector rows do not fit the 32,768-token
      frontdoor** (3 in T1, 48 in T2; `required_tokens` ranges 33,052 → 4,328,998) and two more rows
      (`real_suite_v1_0043`, `needle_039`) declare a zero-capture-group `exact_match` pattern `\d+`.
      `artifacts/operator/e8_context_feasibility_amendment_decision_20260727.md` lays out Options A–D,
      recommends A (capacity-qualified replacement map), and defaults to **D — defer**. Nobody chose, so
      it defaulted, and five `--execute` attempts across 2026-07-26→29 all left `.staging-` bundles the
      runner forbids reusing. **This is the true critical path to quality promotion.**

- [ ] **Run the canonical 79-question judge suite on Qwen3.6-27B-MTP-Q8_0.** Inherited from the three
      `accepted_gaps.yaml` waivers removed 2026-08-03: the gap they waived (missing overall quality prior)
      is closed because quality now compiles per-axis with recorded basis, but their stated closing action
      was never done. The 27B's prior currently resolves 0.8597 via public `mmlu_pro`, not the canonical
      instrument.

- [ ] **Decide the lineup status of `worker_fast` (8102), `eval_batch_frontdoor` (18070) and the
      embedder `extra_recipes` (8096-8098).** They are declared in the launch manifest and so are
      painted as expected services, but none are running. Hidden from the regions-lock panel as a
      display fix; whether they should remain declared is a stack-config decision.


### Backlog sweep 2026-08-03 — 21 agents, adversarially verified (8 PARTIAL, 1 CONFIRMED)

- [ ] **AP-58 — decide whether to reseed the speed axis on ANY eligible in-era frontier measurement**, since
      the same unreachability shape survives on the other early-return paths (`seq_inputs_unavailable`,
      `seq_not_confirmed`, the monotonic skip and the new `quality_not_measured`), so the speed fence stays
      open if quality never improves again after a speed-era boundary — a design decision, not a defect fix
      (`scripts/autopilot/safety_gate.py`) (found 2026-09-14, noninf sweep).

- [ ] **AP-59 — decide whether the E8 quality-baseline reseed row closes as SUPERSEDED rather than done**, as
      it is superseded by `ruling_op19_e8_chain_20260827.json` and not by RTG-02's work
      (`handoffs/active/autopilot-continuous-optimization.md:1714`) (found 2026-09-14, noninf sweep).

- [ ] **AP-60 — remove the import-time `Q_TD_WRITE` test trap** with a fixture or a config-object read, since
      `Q_TD_WRITE = os.environ.get(...)` is evaluated at import so the branch production actually runs is
      `False` under pytest unless a test monkeypatches the module attribute — the standing coverage hazard for
      that whole write path, and why the pre-existing create-only tests passed for the bug's entire lifetime
      (`orchestration/repl_memory/q_scorer.py:52`) (found 2026-09-14, noninf sweep).

- [ ] **AP-61 — stop hand-maintaining the invocation-log guard's module list**, since it covers five modules
      and will not notice a new route file reading the shared `get_invocation_log()`;
      `src/api/routes/openai_compat.py:285` already reads `repl._invoked_tools` correctly but sits outside the
      guarded set (found 2026-09-14, noninf sweep).

- [ ] **AP-62 — document the shared invocation ring's synchronisation contract**: `invoke()` appends from
      whatever thread is dispatching and the bound holds only because `deque.append` is atomic under CPython,
      which a future free-threaded or non-CPython build would not guarantee
      (`src/registry/tool_registry.py`) (found 2026-09-14, noninf sweep).

- [ ] **`request.files` vision input still has no telemetry image reference.**
      `vision_stage.py:76` treats `request.files` as vision input, but routing telemetry records
      neither a retained path nor displayable bytes for that form.

- [ ] **Evidence-durability symlink guard covers the form that barely occurs.**
      `check_evidence_durability.py:306` — `inside_repo = (not absolute) or ...` is unconditionally
      True for relative paths, so `_is_scratch()` is never consulted for them. **416 of 421** registry
      citations are relative, and the remediation playbook tells remediators to use relative paths.
      Also: the new pre-commit wiring exists only as `.git/hooks/pre-commit.extras` on this host —
      unversioned, so no clone gets it.

### New instances of the same class, found by the critic, previously unowned

- [ ] **`memories.sub_decision` is 0 / 59,337 with no producer anywhere.** Column + index
      (`episodic_store.py:330,335`), dataclass field (`:173`), `store()` parameter (`:379`), INSERT
      binding (`:527,557`), and a passing `test_episodic_store_sub_decision.py`. `grep "sub_decision="`
      across `src/ scripts/ orchestration/` excluding the store and backfill script -> **zero hits**.
      `scripts/memory/backfill_sub_decision.py` exists and has never been run. Exact twin of
      `model_id` and `assigned_role`. Three agents ran its test and none noticed the column is empty.
      - **RE-DERIVED 2026-08-12 (`mainC`) — the finding HOLDS and is worse than filed, but it is
        NOT closed.** Producers outside the store and the never-run backfill: still ZERO. A
        read-only count over the checkpoint store gives **0 non-null of 642,328 rows**, an order of
        magnitude more data than the 59,337 recorded here and still entirely empty.
      - **Why nobody noticed, which is the reusable part.** `test_episodic_store_sub_decision.py`
        is 312 lines and green: it covers the enum, the normaliser, the column-and-index migration,
        the classifier token map and the backfill script — **everything except whether anything
        writes the column on the live path.** A test can cover all the machinery and never touch
        the question of whether the machinery is REACHED.
      - **Instrumented, not fixed** (orchestrator `6aa083be`): added
        `tests/unit/test_sub_decision_producer_tripwire.py`, which passes while the gap exists and
        FAILS the moment a producer appears — forcing whoever wires it to confirm the column
        actually POPULATES (a call site is not population), settle the backfill question and close
        this row. A second test guards the other direction, since silently DELETING the column
        would also leave this row describing something that no longer exists. Deliberately not
        `xfail`/`skip`: both are invisible in a green run, and invisibility is the defect.
      - **Box left unchecked deliberately** — the column is still inert. This makes the gap
        self-announcing; it does not resolve it. The fix is still a decision: wire a producer, or
        retire the column and its machinery on purpose.

- [ ] **`binding_router` is a parameter nobody passes, gating a whole feature.** `src/api/state.py:97`
      declares `binding_router: Any | None = None`, never assigned anywhere;
      `chat_routing.py:230`'s `if binding_router is not None:` guards the entire override block;
      `_classify_and_route_proactive` has zero callers. Flipping `features().binding_routing` does
      nothing because the `BindingRouter` is never constructed.
      - **RE-DERIVED 2026-08-12 (`mainC`) — HOLDS, and this row UNDERSTATES it.** The feature is
        dead at **three independent layers**, any one of which alone would be enough:
        (1) `BindingRouter()` appears exactly once in the tree, at `src/routing_bindings.py:19`,
        and that line is **inside a docstring Usage example** — never constructed in code;
        (2) `state.binding_router` is declared and never assigned;
        (3) the guard's **one production caller**, `src/api/routes/chat_routing.py:325`, calls
        `_classify_and_route(prompt, context, has_image=has_image)` and **omits the argument** —
        every other caller in the tree is a test. The flag is a fourth layer of inertness.
      - **Two of this row's three anchors had rotted**, which is why re-deriving mattered:
        `chat_routing.py` now lives under `src/api/routes/`, and `_classify_and_route_proactive` —
        the function this row names — **no longer exists at all**. The finding underneath survived
        the rot; the addresses did not.
      - **Instrumented, not fixed** (orchestrator `tests/unit/test_binding_router_tripwire.py`):
        one test per dead layer, each failing the moment that layer is wired, so whoever wires one
        is forced to wire the REST of the chain instead of landing a layer that silently does
        nothing — which is how this reached three dead layers. Layer 3 is pinned by the CALL SHAPE,
        not a line number, precisely because this row's own anchors rotted.
      - **Box left unchecked deliberately** — nothing is fixed. The decision is still open: wire the
        whole chain, or retire `binding_routing` and its machinery on purpose.

- [ ] **Ten fully-built, fully-tested, zero-production-importer modules** (1-3 test importers, 0
      production importers), incl. `src/mutation_ledger.py`, whose docstring asserts "the autopilot
      accept-path consults the ledger" — it does not.
      - **RE-DERIVED 2026-08-12 (`mainC`) — the COUNT is wrong and the row cannot be acted on as
        written, because it asserts "ten" without naming them.** Over **368 modules under
        `src/`**, the true figure is **at least 20**, not ten.
      - **The exact number is METHOD-DEPENDENT, and I am reporting that rather than a single
        figure.** Two independent passes disagree: a stem-match scan gives **24**, a
        dotted-import scan gives **22**, and they **agree on 20**. Four modules appear only in
        the stem scan (likely over-match on common words — `model_grader`, `federation`,
        `verbalized_sampling`, `tool_output_compressor_mcp`) and two only in the dotted scan
        (`radix_cache`, `safe_pickle`, which the stem scan missed via relative/dotted import
        forms). **20 is the defensible floor; 26 is the union.** A single number here would
        have been false precision — I ran the second pass as a cross-check on my own method
        and it disagreed with the first, which is the only reason this caveat exists.
      - **But the raw 24 is not the answer either: some are ENTRY POINTS, where zero importers is
        correct.** `src/cli_orch.py` is a declared console script (`orch = "src.cli_orch:main"` in
        `pyproject.toml`), and `src/mcp_server.py` is launched as a server rather than imported.
        Anyone acting on a bare importer count would have "cleaned up" a shipped CLI. The real
        list is 24 minus the declared entry points, and it needs a per-module read before anything
        is deleted.
      - **The named instance is CONFIRMED and is the worst of the cluster.**
        `src/mutation_ledger.py`'s docstring states verbatim that *"the autopilot accept-path
        constructs MutationRecords and consults the ledger before composing a new mutation onto the
        live config"*. `git grep` for `mutation_ledger|MutationLedger` across `src/` and `scripts/`,
        excluding the module itself, returns **nothing**. So BSV-3 conflict-aware acceptance is not
        in effect anywhere — and unlike ordinary dead code, this module **describes itself as
        live**, so a reader grepping for how conflict-aware acceptance works concludes it is wired.
      - **Instrumented, not fixed** (orchestrator `tests/unit/test_mutation_ledger_tripwire.py`):
        fails the moment the claim is softened OR the integration is built, so the docstring and
        the code can never silently drift apart again. Mutation-checked against a tracked file.
      - **Box left unchecked deliberately** — nothing is fixed, and the decision is per-module:
        wire BSV-3, or retire the ledger and correct its docstring. Same for the other 23.

- [ ] **The metric's NAME and its new tooltip both overstate what it counts.** `contention_gate.py:325`
  increments inside `if nway_decision != PairDecision.ALLOW:` — **not** inside the
  `if _prec[nway_decision] > _prec[worst]:` test one line above. So it counts *"the N-way check fired
  non-ALLOW"*, not *"N-way was the binding constraint"*: if pairwise already said BLOCK and N-way says
  QUEUE, it still increments although N-way changed nothing. The dataclass comment at `:92` ("N-way set
  more restrictive than pairwise") is therefore inaccurate, and the new tooltip inherits it —
  *"restricted … beyond what the pairwise check alone allowed"* is now **operator-facing**.
  The subagent spotted the looseness in its own report and wrote the loose form into the UI anyway,
  which is the `§ Reporting Units` failure one level in: a LABEL asserting more than the number
  measures. *(Verified by `mainC` by reading the enclosing block, not the comment.)*
  Fix is either wording (*"N-way check returned non-ALLOW"*) or moving the increment under the
  precedence test — a semantics decision for the contention-gate owner, not a wording tidy.

- [ ] **SIBLING SWEEP: six more runtime imports are hard, unguarded and declared NOWHERE** — the same
  defect class, found by AST-walking every import in `src/` against every `pyproject` table.
  `aiohttp` (`src/services/worker_pool.py:41`), `sqlalchemy` (`src/db/models/vision.py:19`,
  also `src/vision/search.py:10`), `langchain_core` (`src/graph/langgraph/nodes.py:19` — `langgraph`
  is declared but `langchain-core` is a separate distribution), `starlette`
  (`src/api/dashboard_cors.py:54` — transitively present via fastapi, so lower practical risk but no
  direct declaration backs a direct import), `gradio` (`src/gradio_ui.py:23`), and `torch`/
  `transformers` (`src/services/lightonocr_server.py:34-35`, function-level and unguarded, declared
  ONLY in the `colbert-export` extra — the exact declared-only-in-an-extra pattern `onnxruntime` had
  before its fix). *(Spot-verified by `mainC`: `aiohttp` and `sqlalchemy` both return ZERO pyproject
  declarations against a hard module-level import.)* A further ~14 are guarded with `try/except` and
  degrade explicitly — lower priority, listed in the subagent report. **UNOWNED**, reported not fixed.

- [ ] The ~77-test retired-topology failure bucket.

- [ ] `MEASUREMENT.md:148-158` still states the durability checker "fails on any citation resolving
      outside the repository" — now false after the retarget. Human-amendment-only; no owner assigned.

### Operational hazards found this session

- [ ] **Cosmetic follow-on, not acted on:** `dashboard.html:6305-6307` has no explicit case for
  `health_escalated`, so it renders via the generic `bad` fallback — correct and red today, but an
  explicit label would read better than the raw status string.

- [ ] **Flaky under load, flagged to its owner:** `test_daemon_owned_state_ownership.py` (landed today)
  fails intermittently under full-suite `-n 16` while passing 19/19 in isolation and under `-n 8` on
  both trees. Ruled out as test method by the finder before reporting, not assumed.


### Context accounting, `-np`, and the E8 blocker (2026-08-03, evening)

- [ ] **Restart the stack so the `-np` change goes live.** The guard reports 12 live-process drift
      errors (`frontdoor expected 4, live 16`, etc.) — that is config != running, working correctly.
      Blocked only on the in-flight E8 calibration.

### New tasks from this work

- [ ] **Regenerate the E8 context coverage scan.** `artifacts/operator/e8_quality_context_coverage_v4_20260727.json`
      reports `required_tokens` in BYTES and was taken against the pre-2026-07-30 fleet. Every
      downstream artifact built on it — including the Options A-D decision package and the two 19 MB
      replacement-map candidates — inherits both errors. Rerun with real tokenization against the
      current shape before anyone acts on that decision.

- [ ] **Per-instance `-np` cannot be declared.** `slots_by_shape` is keyed by shape CLASS (`full` /
      `half`), so two `full` instances of one role cannot differ. The compiled artifact is already
      per-PORT (`slots_by_port`) and `_resolve_parallel_slots` is explicitly "for the instance being
      launched, not for the role" — so this is a declaration-schema gap, not a plumbing migration.
      Same shape as the registry's own `kv_quant_by_shape` future-proofing note.

- [ ] **Routing is not context-length aware.** Nothing inspects prompt length before choosing an
      instance, so a long prompt landing on a narrow slot gets a hard 400 rather than being routed to
      a wider instance or to `ingest_long_context`. The frontdoor group is heterogeneous by design
      (`:8070` 16,384/req vs `:8080`/`:8180` 65,536/req before this change), so the same request
      succeeds or fails depending on which instance takes it.

- [ ] **Settle Qwen3.6-27B's architecture — it gates a 2x context win on the MI210.** `:8083` runs
      `q8_0/q8_0` KV = 130 KiB/token, already the memory-optimal SAFE point (the "safe pure-attention"
      config `q4_0/f16` is 162.5 KiB/token, WORSE than what runs today). The only further saving is
      `q4_0/q4_0` at 65 KiB/token, which the completed KV-quantization handoff says produces garbage
      at 32K on **pure-attention** models but is validated on **hybrid SSM** (PPL 1.2466 vs f16
      1.2510). Evidence conflicts: the registry computes KV over all **65 blocks** (implying every
      layer has KV -> pure attention), while a 110-day-old memory describes **Qwen3.5**-27B (previous
      generation) as hybrid SSM-Dense 3:1. If hybrid, `q4_0/q4_0` frees ~4 GiB and — with the VL
      model's KV dropped to q8_0 — the card fits `n_ctx 131072`: 46.59 non-KV + 8.13 + 6.00 = 60.72
      GiB, exactly today's budget. That doubles context on both GPU roles. Bounded test: read GGUF
      metadata, count KV layers, then a 65K needle check at `q4_0/q4_0`.


### Lost updates, stack-restart ergonomics, and `-np` live (2026-08-03, late)

- [ ] **P1 — THE CONTENTION MATRIX ADMITS A DIFFERENTLY-MEASURED PRIOR AS A ROLE-PAIR VERDICT.**
  `scripts/server/contention_matrix.py:306-313` has **inverted marker polarity**: when it substitutes
  a DISJOINT geometry for a downed primary it returns `(a, b, None)` — **no marker** — and it
  sets `"overlap_measured"` only in the FAITHFUL overlapping case. *(Verified by `mainC` at the
  source.)* So the marker fires on the honest measurement and is absent on the substituted one.
  **The consequence is already shipped.** `orchestration/contention_matrix.yaml:129-136` carries
  `frontdoor` + `ingest_long_context` measured on **disjoint HALVES** —
  giving `ratio 1.89, verdict "allow"`, unmarked. The codebase states the stakes itself
  (`src/scheduling/contention.py:528-536`): *the SAME pair overlapping node0-half primaries is 0.37
  BLOCK, on disjoint siblings 1.716 ALLOW — a role-keyed lookup cannot tell them apart.* `Pair`
  carries roles/ratio/verdict/samples/note and **no geometry**, and `pair_policy` keys on bare role
  names. The same file's `triples:` section still calls that pair catastrophic.
  So a favourable-geometry measurement enters the LIVE ADMISSION GATE as a general role-pair verdict.
  **TERMINOLOGY CORRECTED BY THE OPERATOR, and it makes this MORE live, not less.** I first wrote
  "disjoint quarters". There are **no quarter instances in production** — only halves and full.
  The shipped row is `cpu_list 0-47,96-143` vs `48-95,144-191`, **48 threads each = HALVES**,
  carrying legacy `label: "q0"/"q1"` quarter-era naming; the matrix holds **zero** 24-thread
  rows. *(Verified by `mainC`.)* So the favourable geometry is the CURRENT PRODUCTION SHAPE, not
  a retired one — the bad verdict is reachable today. **Sub-finding: the `q*` labels on
  half-sized instances are stale nomenclature that will mislead any reader — it misled me.**
  **OPERATOR HAS AUTHORISED A RE-BENCH (2026-08-12).** That is COMPUTE and `mainC` is lane
  `none`, so it is routed, not run here: it needs a compute-lane owner coordinating a region
  claim through `inference`. The re-bench must measure the pair in the OVERLAPPING geometry the
  gate will actually admit under, since the disjoint number is the one already on file.
  Repair alongside it — mark, refuse, or reroute to `n_way` — remains the gate owner's call.
  **UNOWNED for the code half; re-bench AUTHORISED and awaiting a compute lane.** Same subsystem and same class as the
  `contention_nway_restricted_count` label defect filed above: a value whose name asserts more than
  the measurement supports.

- [ ] **The legacy substring fallback FALSE-POSITIVES, and the evidence is comical:** applied to
  `outcome_details` it flagged 23 tasks as infra purely because **`"1.503s"` contains `"503"`**. Every
  one of its hits on the live journal was that. The dry-run deliberately uses only the structural
  `[ERROR:` anchor. This is the strongest argument yet for structural-over-substring classification —
  the fallback does not merely miss infra failures, it invents them. **UNOWNED.**

- [ ] **8,855 failure records (pre-2026-07-27) have NO `work` payload at all** — nothing durable
  distinguishes infra from genuine, same mechanism as the seeding path. Unclassifiable, and stated as
  such rather than estimated.

- [ ] **Close the write-side provenance gap — this is why the assessment above is unresolvable.**
  `seeding_injection.py`'s context builder must carry `disposition` / `infra_reason` / `http_status`
  on every reward, so the next occurrence IS filterable. Verbatim the belief-kernel rule: wiring the
  **write** is cheap and permanent; retrofitting the **read** is impossible.

- [ ] **Operator decision on the 419 update-path rows.** The progress log records `old_q` for each, so
  the depression is arithmetically reversible — but reversing it would also undo every LEGITIMATE
  wrong-answer signal in the same set, and no predicate separates them. Recommended: materialise the
  419 `(memory_id, old_q, new_q, ts)` as a read-only artifact and let the operator decide. **Do NOT
  purge** — a purge needs a predicate and there is none; any proxy destroys real negative signal.

- [ ] **Queue-hygiene correction, routed to the coordinator:** the B-bucket cited
  `numa-topology-cutover-resume-20260730.md:327` for this defect. That row is **P1-7
  `vision_escalation` has a PHANTOM 5-port fleet** — a different item, still open and untouched. The
  code defect was real; the row pointer was not. Screening caught it before dispatch.

- [ ] **A HAZARD THAT CORRECTS OUR OWN STANDING ADVICE: `git commit -- <path>` BYPASSES THE INDEX.**
  It commits the WORKING-TREE state of that path, so it sweeps any other agent's uncommitted hunks in
  the SAME FILE. Pathspec commits protect against CROSS-FILE contamination only. This fleet has been
  telling itself "explicit pathspec commits" all session as though it were sufficient; it is not.
  The safe idiom when the target file is dirty with someone else's work is to filter your own hunks
  and `git apply --cached`, then commit from the index. *(Demonstrated live: the resume agent hit
  exactly this and used it to avoid sweeping 63 lines of another agent's in-flight work.)*

- [ ] **`ImportError: cannot import name 'LLAMA_SERVER' ... circular import` prints on every stack
      command.** Fail-open — `runtime-facts selected-servers read failed` and the
      `ORCHESTRATOR_STACK_NUMA_MODE=both env-filter branch failed ... falling through to
      stack-priors`. Both degrade silently to a fallback path, so a real defect there would be
      invisible. It also makes genuine errors hard to spot in stack output.


### Scorer repair and an unprovable outage (2026-08-04)

- [ ] **UNEXPLAINED: every llama-server exited at ~07:00 on 2026-08-04 while whisper and tts —
      same stack start, two seconds apart, same parentage — survived.** That selectivity rules out
      container/host restart (uptime 5d17h), OOM (no kernel oom-kill, no earlyoom entry, 1,079 GB
      available), tool-shell reaping (own sid+pgid, parented to containerd-shim), nightshift
      (`inference_guard.sh` only reads), cron (none), and any repo script. Surviving evidence was
      one line — `srv operator(): cleaning up before exit...`, a signal handler. Six other claude
      sessions are live on this host; INC-20260731-broad-process-pattern-kills is the leading
      explanation and is NOT proven. Logs now append, so a recurrence is diagnosable. **If it
      recurs, capture `logs/llama-server-*.log` BEFORE restarting.**

- [ ] **A THIRD SILENT-SCORING DEFECT, found while porting: the research repo's diverged
  `debug_scorer.py` answers an `entry_point` oracle with `assert f() == <expected text>`** — a
  ZERO-ARG assertion that a function taking arguments can never satisfy, so **correct answers scored
  False on every such row**. Ported the real execution plus the orchestrator's refusal; a test pins it.
  Same family as debugbench's reference-fails: the scorer rejecting right answers, not just accepting
  wrong ones.

- [ ] **Scorer defect reported, not worked around:** `_extract_code_block` truncates UNFENCED code at
  the first blank line. Gating on the unfenced reference would cost 344 rows (15.85% vs 29.83%), so it
  is measured and reported rather than silently absorbed. **UNOWNED.**

- [ ] **REGENERATE `ma_hard_code_001`** — hand-authored tracked YAML
  (`mode_advantage_hard.yaml:288-328`), two defects: `test_code` wires stdin and never asserts, AND
  the prompt ships the author's unresolved self-correction (says 3, then 6; correct answer is 6).

- [ ] **The live pool still carries the OLD oracle** — the rebuild takes effect on the next pool
  rebuild, which is a measurement-instrument boundary (`eval_tower` stamps instrument identity) and
  needs scheduling by the pool owner. Until then the 4 debugbench rows in `core_v2` still score
  vacuously, and **historical debugbench scores remain uninterpretable and were not re-derived**.

- [ ] **Residual guard gap:** `vacuous_rows()` only inspects the substring family, so a *programmatic*
  row whose oracle is input-satisfiable would not be flagged. Debugbench is covered by its own build
  gate; nothing generic covers that class.

- [ ] **Stated limit, not hidden:** whether an ALTERNATIVE correct repair passes is bounded by argument
  (4-added-line cap + the prompt's "fix ONLY the bug"), not by measurement — no second reference exists
  in the data and upstream ships no executable tests, so no oracle over this dataset can do better.
  Test-pinned rather than left implicit.

- [ ] **Design-lens review of AutoPilot dispatched** (workflow `wf_50aef395-2a4`) — essential vs
      incident-scarred vs speculative, against Karpathy's autoresearch. Operator's sharpening:
      scar tissue is not only "justified, keep it" — a CLUSTER of scars is evidence the underlying
      design is wrong and was patched where symptoms surfaced. Apply that lens at synthesis. Three
      clusters already visible from 2026-08-03/04 alone: (1) *absence scored as failure* — patched
      separately in the reliability floor, the `throughput_unmeasured` branch, and the
      degraded-suites renderer, one root cause being that nothing distinguishes "no measurement"
      from "bad measurement"; (2) *lost updates on autopilot_state.json* — patched with a write
      lock, a daemon-absence gate, and a post-write verify, root cause being one whole-file
      document with 5+ writers and no ownership model; (3) *era provenance* — stamped independently
      for quality and speed with separate holds, root cause being no single provenance concept.

      **The refactoring frame (operator, 2026-08-04): simplifying does not mean REMOVING scar
      tissue — it means INTEGRATING it into the design.** A scar is a lesson bolted on as a runtime
      check. Integrating it moves the lesson into the structure, so the failure becomes
      unrepresentable rather than caught. The review's deliverable is therefore not a delete list;
      it is, for each scar cluster, the single structural change that makes the whole class of
      incident impossible:

      | Cluster | Bolted-on now | Integrated form |
      |---|---|---|
      | absence scored as failure | 3 guards: reliability floor, `throughput_unmeasured`, suite renderer | a measurement is `Measured(v)` or `Absent(reason)`; comparing `Absent` to a floor is not expressible, so no guard is needed |
      | lost updates on state | write lock + daemon-absence gate + post-write verify | fields carry owners; the writer API can only write fields it owns |
      | era provenance | quality stamped, then speed stamped separately, two holds | a value IS `(number, era)`; cross-era comparison is a type error, not a runtime hold |

      Each trades N runtime checks for one structural invariant. Rank candidates by (scars
      retired) x (blast radius of the change), and treat a cluster with no such integration as a
      finding in its own right.

### 2026-08-04 — AutoPilot kept HALTING; the objective flipped to tasks/hour

- [ ] **`dominates()` silently truncated mismatched objective tuples** — fixed to raise
      (`afdd5d74`), but the underlying shape is unowned: `safety_gate.py:2303` and
      `pareto_archive.py` read objective axes POSITIONALLY (`[2]`, `[3]`), so the "single
      chokepoint" `tier_specs.objectives_from` governs construction only. **A fifth scar in
      the same cluster**: no named-axis objective type, so every consumer re-derives the
      layout. Fixing it is the prerequisite for W3e (retiring the cost axis).
  - **VERIFIED 2026-08-12, not taken on the row's word.** The fix is real, complete and reachable:
    `src/autopilot_core/pareto_math.py:13-28` raises before the `zip`, it is the SOLE implementation
    (`pareto_archive.ParetoEntry.dominates` is a thin wrapper over the same import), all six call
    routes converge on it, and `tests/unit/test_objective_rate_flip.py::test_dominates_refuses_mixed_policy_comparison`
    pins it — mutation-checked by stripping the raise and watching that test fail. Landed `afdd5d74`.

- [ ] **AP-48 — Add backlog-aware adaptive full/split admission after the E13 burst baseline.** Treat
      E13's guarded split policy for router-owned EvalTower traffic as the conservative burst anchor,
      not the final general scheduler. Build an admission policy that uses arrival pressure, physical
      frontdoor/worker queue depth, and calibrated probability of a frontdoor-terminal answer to choose
      `homogeneous_native_batch` versus `mixed_role_split` at request boundaries. It may schedule a full
      instance only while downstream pressure is absent; when pressure appears, drain rather than preempt
      the active full request and switch subsequent admissions to complementary halves. Evaluate direct-only,
      mixed-pipeline, and randomly paced arrivals separately. Any live adoption opens a new execution/speed
      era so E13 questions/hour is never mixed with the adaptive denominator.

- [ ] **AP-49 — Explore true live-decode checkpoint/resume only on a versioned experimental kernel.** The
      production llama-server defers slot save/restore while `slot->is_processing()`, so current migration is
      an idle-session KV handoff and cannot relocate an active decode. Prototype a token-boundary pause →
      checkpoint → restore → resume protocol that preserves KV plus sampler/RNG, grammar/tool-parser,
      speculative-decoder, request/stream ownership, cancellation, and exact output continuity. Start from
      fresh frozen production into `llama.cpp-experimental`; do not modify the production kernel. Require
      byte/token continuity tests, failure-atomic rollback, bounded pause/transfer cost, and a demonstrated
      advantage over request-boundary drain-and-switch before considering a new production version.


### 2026-08-05 — Research intake: least-commitment diagnostics and compression safety

- [ ] **AP-WM-1 — Shadow-test loop-native least-commitment diagnostics; do not add a live selector.**
  Build one immutable offline comparison over archived proposals that share a common candidate frame and
  predeclared empirical demand weights. Every row must declare vocabulary provenance (regimes, surfaces,
  outcomes, contradictions), excluded alternatives, abstraction-construction cost, and either a canonical
  representation or semantics-preserving recoding fixtures. Compare explicit unsupported-scope width,
  demand-weighted compatible-future mass, and the K-rho representation-aliasing diagnostic against current
  information gain, novelty, and a raw-impurity/simple weighted-minority baseline. Score against held-out
  regime transfer and falsifier resolution using matched one-factor interventions; report per-regime and
  per-surface Kendall direction, conditional predictive value, mean/90th/worst sign error, effective-pair
  count/noise floor, and recoding stability. If recoding changes the ordering or a new diagnostic adds no
  stable decision signal beyond the simpler baseline, retain the simpler baseline. No result may affect
  fitness, archive admission, promotion, or authority without a separately approved decision-grade protocol.
  - [x] **AP-WM-1a — Implement and regression-test the immutable offline protocol. ✅ 2026-08-05**
    `epyc-inference-research/scripts/kernel_rnd/autokernel/offline_least_commitment.py` validates one common
    candidate/representation/demand frame, completed matched one-factor interventions, explicit metric
    directions, recoding coverage, and observe-only authority; it emits the full required report and has no
    live mutation API. A deterministic matched fixture proves the report and conservative simpler-baseline
    fallback.
  - [ ] **AP-WM-1b — Execute over AutoKernel's first real matched archive, observe-only.** Consume the
    deterministic AK-WM-2a output only after clean instrument provenance, current v9 controls, the CPU IQK
    proposal, proposal-v3 frame receipts, and completed matched interventions exist. Synthetic regression
    rows are protocol tests, never decision evidence; this path gains no live selector authority.


### 2026-08-07 — reset-free trajectory refinement, proposal-only (intake-1016/1020)

- [ ] **AP-CH-1 — Add a default-off adapter that turns a bounded recent trajectory window into typed
  prompt/subagent/skill/memory candidates.** The adapter may diagnose and propose only. Validate every
  payload against a local schema, cap repeated equivalent proposals, and emit ordinary candidate
  envelopes with source trajectory ids, proposer identity, component kind, before/after content, and
  claimed failure signature. It has no authority to write live prompts, execute generated Python,
  mutate skills/memory, select itself, or keep a change. Existing held-out evaluation, checkpoints,
  transactional keep/revert, privilege policy, and promotion authority remain outside the proposer.

- [ ] **AP-CH-2 — Compare reset-free and episodic proposal generation at equal budget.** Use the same
  completed trajectories, proposer model, token/tool budget, candidate schema, evaluator, and held-out
  task set. Report valid-candidate rate, duplicate/oscillation rate, held-out lift, regressions, cost,
  and wall time. The upstream 25/100-step cadence is not a default; cadence is a declared experimental
  variable. No live AutoPilot resume or acceptance-policy change follows from this task.


### Research Intake Update — 2026-08-15 (feedback-conditioned mutation; intake-1139/1143/1144)

- [ ] **P17.BT-5a — Retrospective feedback synthesizer (do this FIRST).** Consume logged
      (config, score) pairs from the existing autopilot trial history and emit a **directional** hint
      ("increase X", "decrease Y") for the proposal step. Offline, no new eval loop, no new inference
      over the historical corpus. Bench against the no-feedback baseline before wiring anything live.
      Admission test from `intake-1144`: feedback is **DIRECTIONAL iff it determines the SIGN of the
      change**; **non-directional** (names the offending dimension but withholds the sign) still beats
      a scalar and takes a narrowing path; neither → existing scalar path.

- [ ] **P17.BT-5b — Full feedback-conditioned mutation pilot, GATED on 5a showing signal.** Ship in ONE
      change with (i) a prospective **write-side trace hook** persisting
      `(candidate_id, champion_id, preference, feedback_text, accepted, streak_index)`, and (ii) a
      **scrambled-feedback control arm** — non-optional, because `intake-1139` measured **Random
      Feedback scoring BELOW no-feedback at all**, so bad critique is a net negative rather than a
      degraded positive. Reusable acceptance test: that source's own alignment design (true feedback
      preferred over a scrambled control 81% of 400 comparisons, p<10⁻¹⁰).

- [ ] **P17.BT-5c — Log pair CONTENT, not just ids.** Persist winner/loser candidate IDs **and both
      candidate artifact texts** on every pairwise comparison. Rationale from `intake-1143`: post-hoc
      rationales are **retrofittable** from (prompt, chosen, rejected), so logging pair content
      preserves a future offline option that logging ids alone destroys. Our existing P17.BT corpus
      **cannot** be rescued this way — it lacks exactly these fields — which is precisely the point.

**Design fork to decide inside 5a/5b, not before**: `intake-1139` **resets** its feedback buffer on
every accepted candidate; `intake-1144` **accumulates** and subsamples, treating history as a durable
asset. Both are cited precedents; pick per pilot and record which.

**Cost note**: roughly 400–500 short structured-output calls per optimization run at the source's own
settings — short prompts, structured output, no long context (the buffer reset bounds it). A good
Qwen3.x-class MI210 workload. The source's whole pipeline ran on an **8B open-weight** model and beat
its comparator on 2 of 4 tasks there, so no frontier API is required. Cite `intake-1139#record`.


### Research Intake Update — 2026-08-15 (acceptance cannot currently see a no-op; intake-1129/1141)

- [ ] **SG-W1 — No-op guard.** Refuse to promote a candidate whose config/diff is byte-identical to its
      parent, regardless of score. Under a stochastic LLM-graded objective a byte-identical candidate
      can score above its parent on noise alone, and `intake-1141`'s own data gives the magnitude: an
      **unchanged** harness scored 0.800 and 0.547 on the same suite. A few lines; zero exploration cost.

- [ ] **SG-W2 — Warrant as telemetry (explicitly NOT a gate).** Record whether an accepted edit cites
      an observed failure instance, without blocking on it. Structural obstacle to plan for:
      `SafetyGate.check()` takes only an `EvalResult`, so the action payload must be threaded to the
      gate. The full warrant gate is **deliberately deferred** until this telemetry says it matters,
      because the cost is real and measured — `intake-1134`'s equivalent guidance had the lowest
      variance *and* "prevented breakthrough modifications", and `intake-1140` found trace-reading
      share **negatively** correlated with gain (ρ −0.31 to −0.64). The cheapest exposure measurement
      is the known-null corpus filed as EV-14f in
      [`eval-tower-verification.md`](eval-tower-verification.md).

- [ ] **SG-W3 — Dispose of `src/diversity_gate.py`: wire it or delete it.** Zero production importers,
      warn-only by default (`SAFETY_GATE_WARN_ONLY` defaults to `"1"`), renamed 2026-07-20 out of a
      bare-name collision with `scripts/autopilot/safety_gate.py` (the module the autopilot actually
      imports). Its `evaluate()` accepts on a raw `quality_delta > 0` with no resolution band, so it
      reads like a live acceptance surface and is not one — a subagent during the 2026-08-15 intake
      session read it as our live gate and was wrong. A plausible-looking second "SafetyGate" in the
      tree is a standing misreading hazard.

> **Owner note (2026-08-15).** SG-W1/W2/W3 were filed against `safetygate-rlvr-provenance-audit-2026-07-22.md` per the approved Stage-3 plan, then relocated here when that handoff was found already archived to `completed/` on `origin/main` (`3615bdc3`) — filing live tasks inside `completed/` would have been the result. Content unchanged.


### Research Intake Update — 2026-09-07

- [ ] **AP-51 — Diff THREE JIT admission rules against `ParetoArchive`.** Eq. 4 (reward strict AND one
      efficiency dimension strict); Stage-III bank retention (reward ≥ frontier AND one dimension
      strict); Eq. 6's `I[r ≥ b_r]` gating. Pure design comparison over published equations,
      independent of that source's adverse empirical findings. `intake-1320#02`. Zero compute.

- [ ] **AP-52 — STANDING CAUTION against the frozen-frontier-proposer contract.** Two prompted
      frontier editors reading real failure traces produced **net negative** deltas over 1,270
      held-out tasks (−4.3 ± 2.5 and −0.4 ± 3.6), with 1/9 and 3/9 failing validation outright.
      **PromptForge is that loop.** SafetyGate scores the same suite the mutation was proposed from;
      nothing measures out-of-sample transfer of an accepted mutation. Negative deltas concentrate in
      `rewrite_action` / `force_action` patches (all 4 REPLACE patches regress, but the single worst
      patch is hint-only CONSTRAIN — MHS-5, orchestrator `4f28e6c3`, pending merge), which ties this directly to **MHS-4** in
      [`promptforge-mutation-safety-contract.md`](promptforge-mutation-safety-contract.md).
      The caution itself is zero-compute and lands with this row. **The held-out arm on accepted
      mutations is COMPUTE-GATED: filed, never run here** — it needs eval compute and belongs to
      another session. `intake-1323#record` (dive actionable D3). Dependency: MHS-4.

- [ ] **AP-54b — (COMPUTE-GATED, filed not run) wiki-fence A/B on eval rollouts.** Same eval suite
      with the knowledge fence armed vs. unarmed, paired per question. Also record touched paths in
      question results so the unarmed arm shows whether the wiki was read at all. Run only after the
      fence and path-recording land and the operator picks the arming mechanism (see AP-54).
      Owner: an eval-compute session.


### Research Intake Update — 2026-09-14 (intake-1346…1366)

- [ ] **AP-56 — Determinism certification before N=1 promotion.** llama-server fixed seed and fixed
      slot count; replay the baseline action chain and require identical trajectories before trusting a
      single-run verdict. External, descriptive: promotion rate 7.9% (1,223 decisions) → 25.2% (131)
      after determinism. Inference-gated; measure the local signal change first. `intake-1355#01`.


### Research Intake Update — 2026-09-15 (noninf-20260914: orx / auto-research critique cluster)

- [ ] **AP-63 (S3-AP-01) — close the two preconditions that have blocked the orx
      per-completion-refill shape since 2026-07-29 (rows at "Mine orx's experiment-tree lineage
      model" / "Mine orx's stacked bushes").** (a) Stamp the AP-1510 run manifest onto journal rows,
      not only the in-flight WAL marker; with it, make parent selection explicit (a stored parent
      id, not the same-species parent_trial heuristic). (b) The lane-arbiter precondition is
      re-pointed at **OP-41** alone: gflow, pueue and task-spooler were checked (intake-1369#record,
      intake-1382#record, intake-1383#record) and no off-the-shelf single-node queue models CPU/NUMA
      contention. OP-41 forbids any broker/scheduler/admission daemon until champion finalised →
      production promotion → host reboot, and the operator owns the design. (a) is unblocked
      zero-compute work; (b) is blocked on that named external sequence. intake-883#record.
      - [x] **AP-63(a)** ✅ 2026-09-17 — orchestrator `0286c170`. JournalEntry gains `run_manifest`,
            copied from the in-flight WAL marker for the same trial on main-loop rows, dispatcher-skip
            rows and the AUTOPILOT_KILLED placeholder. Undispatched rows and a mismatched or legacy
            marker get `{}`: nothing is built at write time, nothing is back-filled, and the claim tuple
            carries the digest. The same commit adds `lineage`, an explicit stored parent under rule
            `latest_committed_baseline_promotion_same_species`: the newest same-species trial with a
            `baseline_promotion` ledger event. A pending, bug-corrupted (also by supersession),
            other-species or later row never qualifies, and no accepted parent gives `None`, never a
            fallback. The old heuristic is recorded alongside and still drives `parent_trial`, so
            config_diff, PEAF, BSV and Pareto are unchanged. Root `scripts/vidya` carries the digest on
            autopilot-journal frames, ungraded. Tests: `test_ap63_run_manifest_lineage.py` (17). Takes
            effect at the next AutoPilot restart.
      - [ ] **AP-63(b)** — lane-arbiter precondition: blocked on the OP-41 sequence above (champion
            finalised → production promotion → host reboot, operator-owned design).
      - [ ] **AP-63c** — after the first post-restart trial, check (read-only) that its journal row
            carries a non-empty `run_manifest` whose `manifest_sha256` matches the in-flight marker it
            was dispatched under, plus a `lineage` block. A pre-dispatch skip must carry `{}`.
      - [ ] **AP-63d** — decide whether `parent_trial`'s consumers (config_diff, PEAF surprise r²,
            BSV-3 dependency rows) should switch from the same-species heuristic to
            `lineage.parent_trial_id`. This is a design choice for the orx refill shape, not a defect:
            it changes what a config diff is measured against.

- [ ] **AP-64 (S3-AP-02) — apply the OP-20 task_failed ruling to BOTH producers** (eval_tower and
      the seeding path), per the operator's ruling at the 2026-09-15 Stage-3 plan approval (S3-OP-01
      option a: non-infra task_failed → WRONG in both producers, infra → EXCLUDED in both), with a
      test that one run yields the same axis-0 quality from either producer. Closes the
      "PRE-EXISTING: eval_tower and the seeding path DISAGREE" row.

- [ ] **AP-65 (S3-AP-03) — decide whether _proxy_check binds.** It is the only leg built to catch a
      candidate whose entire gain is one easy suite, and it returns warnings, never violations ("an
      external checker whose output does not gate the loop", intake-1367#01). Either make it a
      violation at a stated threshold or record why a warning is the right strength. S3-AP-08's
      rotation-drop data is the empirical basis for any threshold.

- [ ] **AP-66 (S3-AP-04) — NumericSwarm must tell INFEASIBLE configs to the sampler, not hide
      them.** Split non-answers (preimage unavailable, no-change, infra) from INFEASIBLE answers
      (invalid config; dominance axis unmeasured because the config broke the eval). Tell the latter
      as COMPLETE with a constraint violation via NSGAIISampler(constraints_func=…), or failing that
      a Pareto-dominated objective vector — never TrialState.FAIL (GA parents are drawn from
      COMPLETE trials only), and never an out-of-scale penalty scalar (the covariance-poisoning
      pattern). **Encoding details:** (i) a crash/OOM/apply-error is strictly worse than ANY
      SLO/quality miss. Normalise every overage as overage/cap and set the crash violation to 1 +
      the maximum possible normalised overage, or give crashes their own constraint dimension. Never
      add a fixed crash constant to raw ms overages: in SLO-Guard, a miss more than 100 ms over cap
      ranks worse than a crash. (ii) Tell a FINITE worst-observed objective vector, never -inf;
      infinite objectives risk NaN crowding distance in the 4-objective NSGAIISampler. (iii) Record
      the outcome class (startup | preflight | runtime | slo_miss) as a trial user_attr. Unit tests:
      a penalized infeasible trial shifts the next suggestion away; a crash ranks below the worst
      SLO miss; no objective is non-finite. Do not cite SLO-Guard as evidence that the encoding
      helps, since 0 of its 300 trials crashed. **Acceptance (offline, before touching live
      autopilot):** replay on the LLMSYS-HPOBench SGLang table (Zenodo 20048594, CC-BY-4.0 data
      only, no GPL code vendored; one fidelity, 16 knobs, context_length ≥ 9216 deterministically
      infeasible). Arms: NSGAIISampler (FAIL), NSGAIISampler (constraints_func, raw violation),
      NSGAIISampler (constraints_func, normalised strictly-dominating violation, the third encoding
      arm), and BoTorchSampler qLogNEHVI with constraints_func, all with the same 20-point QMC/Sobol
      init, 50 and 100 trials, 10 seeds. Restrict all samplers to the observed per-knob value sets
      (CategoricalDistribution) so every proposal is an exact table hit; if any sampler must use
      continuous distributions, report snap rate with MinMax-normalised distance, never the
      unnormalised L1 API. Report infeasible-proposal rate AND hypervolume at equal trial count.
      Pass = infeasible-proposal rate falls under the constraint encoding. Results in scratch.
      (intake-1372#02; intake-1381#05; intake-1389#02, #04; intake-1390#01; intake-1393#01)

- [ ] **AP-67 (S3-AP-05) — planner-authored numeric trials must reach the sampler.** The
      explicit-params branch applies and evaluates without any study.tell, so NSGA-II is blind to
      every LLM trial. Record each completed explicit trial into the surface study
      (study.add_trial(create_trial(params, distributions, values)), tagged source=planner). Do NOT
      inject planner-authored FAILURES until AP-66 lands. intake-1372#05.

- [ ] **AP-68 (S3-AP-06) — measure whether planner numeric trials are the worst proposer arm.** From
      the journal, compute per-surface spread and step (normalized to bounds) for planner-sourced vs
      sampler-sourced numeric trials. This decides AP-67's priority. The exact-repeat rate of
      (surface, param, value) proposals is measured ONCE, inside AP-53's zero-compute re-proposal
      count, not twice. intake-1372#02.

- [ ] **AP-69 (S3-AP-07) — label every planner-critic verdict kind=proposal_filter, never
      validation**, in the journal and any receipt/dashboard summarizing it. The critic
      (local_frontdoor) reads only the planner's prose draft, which is the manuscript-only review
      shape (intake-1373#01). This is the autopilot twin of S3-AKU-05, with the kind enum widened to
      script / oracle / proposal_filter / llm_judge. Eval tower + safety_gate stay the validation
      path.

- [ ] **AP-70 (S3-AP-08) — rotation-boundary generalisation drop, observe-only.** At every
      core-rotation boundary, score the outgoing incumbent on both the outgoing and the incoming
      draw. Journal drop = q(outgoing) − q(incoming) with both rotation indices. Report mean drop ±
      SE over K boundaries, with K fixed before reading. No fitness/archive/baseline/promotion
      effect without a separately approved protocol. It is also the atypical-observation probe
      (intake-1379#record). intake-1378#record.

- [ ] **AP-71 (S3-AP-09) — PromptForge lineage-depth side-effect audit.** For every kept prompt
      file, reconstruct the keep lineage (git + journal). Tabulate against lineage depth: gated
      quality, prompt token length, count of added lines sharing a verbatim ≥8-token n-gram with any
      draw/sentinel/trace-bank question or expected answer, and _suite_mentions on added text. ICRH
      signature: quality up while a side-effect column rises with depth. intake-1379#record.

- [ ] **AP-72 (S3-AP-10) — metric-event physicality bound in SafetyGate.** A trial whose reported
      speed exceeds a physical bound (tokens/s above the surface roofline ceiling, or TTFT/TPOT
      below a hardware floor) is invalid, not a keep. Scoring runs from the harness's own canonical
      request set, outside any planner-editable path. Autokernel refuses above-roofline proposals at
      critic time, but autopilot's safety_gate bounds quality only. intake-1392#07, #10.


### Research Intake Update — 2026-09-25 (DGM, program search, and autonomous science)

- [ ] **AP-DGM-PROV — Freeze the shared EPYC selector-replay package.** Snapshot the existing AutoPilot journals, candidate graph or cached proposals, task order, candidate and outcome bytes, incumbent policy, selector/scorer revisions, archive and endpoint tie-breaks, budgets, model/decoding identity, and time/task holdout. Record immutable manifest and artifact digests and write through `VB-DGM-1`; do not fetch or recreate the external DGM benchmark for this phase. The package is the one input consumed by `SEQ-SHINKA-1` and `AP-DGM-SEL`. Sources: intake-1625#record, intake-1638#record, intake-1663#record, intake-1684#record, intake-1685#record, intake-1686#record.

- [ ] **AP-DGM-SEL — Add DGM/HGM formulas to the shared selector replay after `SEQ-SHINKA-1`.** Reuse the exact frozen package, current-policy and score-only controls, holdout, raw per-decision outputs, complete invalid/failure/abstention denominator, and `VB-DGM-1` receipt. Vary only `{DGM transformed-score × inverse-valid-child, HGM clade/CMP}` after predeclaring cold-start semantics. Report parent-choice agreement, held-out continuation, time-split/bootstrap stability, and paired lineage outcomes. Stop if alternative policies choose the same parent on at least 95% of eligible decisions, differ without improving held-out continuation, or reverse across holdouts. A stable gain permits one bounded live paired follow-up; it grants no restart, policy switch, or production authority. Sources: intake-772#record, intake-1626#record, intake-1639#record, intake-1640#record, intake-1661#record.

**Work consolidated into the shared replay**

- **AP-RI-CTRL-1** supplies the matched control ladder for the shared replay: incumbent, score-only, IID repeated sampling, sequential conditioned sampling, and incumbent-only Hill Sampling use the same frozen inputs, evaluator, budget, seeds, concurrency, and effective config. Retain every candidate and per-seed anytime trajectory. No separate campaign is created. Sources: intake-1628#record, intake-1642#record.
- **AP-RI-OBJ-1** may score an already-frozen candidate-by-instance matrix inside the same sandbox, without editing `MEASUREMENT.md`, protocols, production scorers, promotion gates, or live policy. If the shared package lacks that matrix, this work remains dormant until one exists. Source: intake-1592#record.

**Durable activation triggers — these are records, not active tasks**

- **AP-DGM-PROV external reproduction:** activate only when the shared replay shows a stable held-out gain and EPYC needs a transfer or authoritative DGM benchmark claim that the internal replay cannot support. Then pin `jennyzzt/dgm@a565fd2d1dca504ef5104a7cc0f3bdc4ab9b4fd2`, the historical SWE-bench revision, current v5 as a separate arm, external logs, all environment identities, and decontamination/access receipts. Treat mini-swe-agent as a separately versioned baseline. Sources: intake-1625#record, intake-1638#record, intake-1663#record, intake-1684#record, intake-1685#record, intake-1686#record.
- **AP-RI-ALE-1:** activate when `SEQ-SHINKA-1` or `AP-DGM-SEL` beats matched simple controls, or a selected long-horizon engineering campaign needs ALE-style evaluation. Compare iterative search with matched multistart under equal model, prompt, evaluator, private-call, concurrency, and wall budgets; retain every failure and endpoint-selection receipt. Sources: intake-1597#record, intake-1598#record, intake-1599#record.
- **AP-RI-SOLVER-1:** activate when a live campaign exposes a compact frozen NLP/MIP/CP candidate-by-instance problem. Add a pinned conventional solver, beginning with SCIP, with the mathematical model, solver identity/config, primal witness, independent replay, bound/gap, logs, hardware, and runtime. Source: intake-1643#record.
- **AP-RI-SMC-1:** activate when a proposed sampling policy claims theorem-backed authority. Before that claim can influence policy, instantiate its finite/asymptotic scope, decomposition, target/path, initial sampler, ratio and partition assumptions, resampling law, kernels, mixing constants, test-function class, approximation error, and exact conclusion. Sources: intake-1629#record, intake-1644#record, intake-1664#record, intake-1665#record, intake-1666#record, intake-1694#record, intake-1695#record.
- **AP-RI-SCAFFOLD-1:** activate when a live campaign needs scaffold evolution beyond the shared replay. Require repeated held-out evaluation, uncertainty and probability of improvement, matched Majority@k/IID/SCS controls, and complete raw candidate, token, cost, and wall-time records. Sources: intake-779#record, intake-1595#record.
- **AP-AISCI-1:** activate when EPYC begins proposal-to-execution scientific experiments. Then shadow append-only proposal, execution, replication, aggregation, filtering, and promotion nodes against the current loop; preserve all failed and filtered branches. Manuscript or venue scores remain separate from scientific validity. Sources: intake-780#record, intake-1609#record, intake-1610#record.


## Nested open decisions retained during compaction

- [ ] **OPERATOR: install the two declared deps into the live orchestrator `.venv`.** The
      declaration half is done; the install half was deliberately not run — `uv lock` / `uv sync`
      against a live shared environment is the environment owner's call, not a subagent's.
      `uv.lock` already resolves `onnxruntime 1.26.0` and `tokenizers 0.22.2` via the
      `colbert-export` extra, so a re-lock should not move any version, but the two new DIRECT
      requirements are not yet recorded in it.
    ✅ 2026-08-12 — **already fixed by `mainA` (`fa3daeac`)**, declared at `pyproject.toml:43`.
    Re-verified independently rather than trusted: the import is optional at the LANGUAGE level
    (`try/except ImportError` in `cross_encoder.py:92`) but load-bearing on the UNCONDITIONAL
    first-stage KB-RAG path, so the declaration was correct either way — an optional import used by
    an unconditional path still needs a manifest entry, or the module never has the capability.
    Guard test `tests/unit/test_retrieval_deps.py`, 6 tests; mutation (remove the declaration)
    2 failed / 4 passed, restored 6 passed. *(`mainC` re-confirmed the declaration and the tests.)*

- [ ] **PRE-EXISTING: `eval_tower` and the seeding path DISAGREE about a `task_failure`, so the same
  failure yields different quality depending on which subsystem measured it.** `eval_tower:1339`
  excludes every row whose disposition is not `SCORED` — including `task_failed`; the seeding path
  scores a non-infra `task_failure` as WRONG. Both are defensible in isolation and that is exactly
  why it survived: neither looks wrong on its own. But it makes a quality number NON-COMPARABLE
  across the two producers, which is a measurement-comparability defect rather than a bug in
  either. Surfaced by the B4 work and NOT introduced by it — the new disposition taxonomy is what
  made the disagreement legible. *(Verified by `mainC`: an HTTP-400 client error and an unparseable
  200 body both classify `task_failed`, and `legacy_error_type` maps that to `task_failure`.)*
  Needs one ruling, applied to both, rather than two local fixes.
  **RULED 2026-09-15 (S3-OP-01, option a); implementation is AP-64.**

- [ ] **OPERATOR DECISION, deliberately not taken by the subagent:** `:1960` also says reliability
  should have collapsed the run long before 70 questions. Early abort is a live-control-loop policy
  change — *how many consecutive infra-failed rows should abort an in-flight batch, and abort or
  continue-and-mark?* `RELIABILITY_FLOOR = 0.8` already blocks such a run at the gate (as RETRY),
  but only at the END, after the questions are spent. Everything not depending on that answer is done.

- [ ] **OPERATOR EDIT NEEDED — `human_only_paths.yaml` still calls safety gates unenforceable.**
  Its `conceptual:` block lists "safety gates" as prose-only; that is now **partially false**.
  Agent-typed execution of a derived copy IS enforced by `check_operator_apply_copy.sh`; daemon,
  cron and subprocess execution remain OS-level-only (separate uid / read-only mount). The file is
  human-amendment-only and the trust-boundary hook correctly refused the subagent, so this needs the
  operator. **Known scope limits, stated rather than implied:** a quoted or variable-expanded path
  is invisible (quoted runs are blanked so mentions stay legal — the same trade `check_process_
  pattern_kill.sh` makes), and a copy rewritten from scratch scores low and passes, deliberately.
  This does not make the gate unbypassable; it makes the CHEAP bypass — `cp` + `sed`, minutes of
  work, which is what actually happened — fail.

- [ ] **Behaviour change to ratify or reverse:** operator applies can no longer be run **from a
  worktree** (verified: exit 2 from a live worktree; ordinary worktree work and worktree pytest are
  unaffected, exit 0). Defensible — an apply mutates global state and should run from the canonical
  tree — but it is a real change and five mains work in worktrees. Operator call.

- [ ] **AP-55-ARM** — after one AutoPilot run in shadow (mode A), report how often enforce
      would have held a promotion (from the recorded shadow verdicts), then arm enforce plus
      seed re-runs (`AUTOPILOT_AP55_PROMOTION_GATE=enforce`, `AUTOPILOT_AP55_SEED_RERUN=1`).
      The operator pre-approved option B for after that review (2026-09-16). Needs the AutoPilot
      merge train (`sub/autopilot-train-20260916`, which carries the within-noise AP-55 hold fix
      `f76e65cd`) on orchestrator main first. Filed 2026-09-17 from `2026-09-16-sub-gate-frontier.md`.
      - 2026-09-17 **prepared, not flipped** (orchestrator `cd79b80e`; the train is on main as
        `a1a0251a`). **Gap closed:** in shadow mode `_holds()` returns `[]`, so the recorded
        `eval_details.ap55_promotion_gate.hold` is False on every row and its rate reads 0% no
        matter what. Each trial now also records `would_hold_enforce` (plus reasons) and
        `would_hold_strict`, using the same rule; an errored gate would hold.
        `start_authority_daemon.py` now pins `AUTOPILOT_AP55_PROMOTION_GATE=shadow` and
        `AUTOPILOT_AP55_SEED_RERUN=0`, so an inherited variable cannot arm the shadow run.
        **Runbook:**
        1. Run `python3 scripts/autopilot/ap55_shadow_review.py --since <shadow-run start ISO ts>`.
           It is read-only and reports would-hold count and rate over gated trials, attempted
           promotions and committed promotions, plus a reason histogram. Exit 3 means no shadow
           verdict is in the window, so flip nothing. Rows written before the counterfactual
           field are re-derived and labelled `reconstructed`.
        2. Report the committed-promotion figure.
        3. **The switch:** in `start_authority_daemon.py` `AUTHORITY_ENV`, set
           `AUTOPILOT_AP55_PROMOTION_GATE` `"shadow"` → `"enforce"` and `AUTOPILOT_AP55_SEED_RERUN`
           `"0"` → `"1"`.
        4. Restart through the wrapper; it binds only from then.

        Runbook copy: orchestrator `docs/autopilot/gate-frontier-live-scope-2026-09-16.md`.
        Live journal today: 0 gated rows, exit 3 (no shadow run yet). Tests:
        `test_ap55_arm_review.py` (7) and a launcher pin test.

## Historical siblings

- [Historical ledger through 2026-06-20](../completed/autopilot-continuous-optimization-history-through-2026-06-20.md)
- [Historical ledger, 2026-06-21 through 2026-09-25](../completed/autopilot-continuous-optimization-history-2026-06-21-through-2026-09-25.md)
