# AutoPilot: Continuous Recursive Optimization

> **Fold destination** (BRF-T7-F12, BRF-T7-1, route 1b, 2026-11-03): every former handoff of this plan target is a `## Track:` with its own gate marker: `autopilot-program`, `autopilot-sequential-allocation` (rows EVL-04 retired into RTG-02). The former `autopilot-program.md` body is `## Track: autopilot-program`; tracks those handoffs already had are lifted verbatim after their owner.

> **Fold destination** (BRF-T1-F20, BRF-T1-1, route 1a, 2026-11-02): renamed from `autopilot-continuous-optimization.md`; absorbs 11 handoff(s) as `## Track:` sections at the end of this file (`autopilot-dashboard-fidelity-audit-2026-07-22.md`, `autopilot-decision-plane-audit-2026-07-22.md`, `batched-edit-parallel-apply.md`, `bep-dcp-falsification-harness.md`, `evidence-plane-event-sourcing-and-narrative.md`, `evidence-plane-instrument-repair.md`, `evidence-plane-ledger-and-sequential-verdicts.md`, `loops-and-dashboards-audit-2026-07-05.md`, `objective-task-rate-goodput.md`, `orchestration-robustness-audit-2026-07-11.md`, `scaffold-autopilot-cost-lever-deployment.md`). The body above the first track is the former `autopilot-continuous-optimization.md`.

**Scratch**: `/mnt/raid0/llm/tmp/codex3-apme3-p66-checkpoint-20261031/` (checkpoint metadata scratch)

> **Current checkpoint — 2026-09-25.** AutoPilot remains intentionally stopped; inference resources are operator-owned. Production baseline evidence is ratified on the frozen v10 kernel. Any restart remains a separate explicit operator action. The immediate research-intake path freezes the existing EPYC replay inputs under **AP-DGM-PROV**, runs the Shinka-style control in **SEQ-SHINKA-1**, and only then adds DGM/HGM formulas under **AP-DGM-SEL**. No selector, objective transform, or autonomous-science result has production authority.

> **Compaction boundary.** Completed implementation history, dated runtime checkpoints, and the full pre-compaction ledger moved to [the 2026-06-21 through 2026-09-25 history sibling](../completed/autopilot-continuous-optimization-history-2026-06-21-through-2026-09-25.md). Earlier history remains in [the through-2026-06-20 sibling](../completed/autopilot-continuous-optimization-history-through-2026-06-20.md). This active file retains every open task and the context attached to it.

**Created**: 2026-03-08
**Updated**: 2026-09-25
**Location**: `epyc-orchestrator/scripts/autopilot/`

**Priority**: MEDIUM — T6 inference-ready (rank 58), 110 open but autopilot is intentionally stopped and restart is a separate operator action.

## Track: autopilot-program
<!-- gate: none -->

> Folded from the body of `handoffs/active/autopilot-program.md` (row RTG-02), from its first `##` section on, @ `e8deee0a4de8` on 2026-11-03 (BRF-T7-F12, route 1b, operator D1/D5). Headings demoted two levels; every box kept its text and ID.

## 2026-11-09 audit refresh

- **What changed:** true last Autopilot run is 2026-08-09T19:29Z (trial 1503), not 07-27; shards are `autopilot_journal.jsonl` (0-999) and `autopilot_journal_1.jsonl` (1000-1505). The relaunch will use a brand-new era (operator ratify script; the era/baseline files are human-only), so E8-era premises (SEQ-3, SEQ-B1, re-arm) were rewritten. New box AP-HOLD-RELEASE-REVIEW lists everything to re-review at hold-lift.
- **Current next action:** AP-DGM-PROV/SEL and SEQ-SHINKA-1 have no capture target (`select_lineage_parent` is deterministic); the immediate step is the menu-location design decision recorded under AP-DGM-PROV (recommended: option A, observe-only `eligible_parents` logging).
- **Doable now (no compute):** that decision and its observe-only logging code; offline analyses and code boxes tagged DOABLE in the RTG-02 audit.
- **Needs compute / the hold:** see AP-HOLD-RELEASE-REVIEW. Autopilot stays on operator HOLD; nothing here starts it.
- **Audit claim found wrong:** `preflight_audit.py` and `restart_readiness_report.py` do read the second shard (see the checklist item above).

#### Current execution map

1. Freeze the existing EPYC journal/candidate graph and its replay identities (**AP-DGM-PROV Phase A**).
2. Run the shared selector replay: Shinka-style policy first (**SEQ-SHINKA-1**), then DGM/HGM formulas (**AP-DGM-SEL**).
3. Keep autonomous research proposals behind deterministic evaluation, fixed budgets, complete denominators, and human promotion.
4. Resolve existing live-inference and operator gates only at their named boundaries; do not reinterpret a stopped loop as a software blocker.
5. Preserve the v10 production-kernel freeze and use experimental kernel lanes for any kernel-affecting work.

#### Active architecture boundary

AutoPilot proposes and evaluates numeric, prompt, routing, and code candidates through the orchestrator. Deterministic policy owns safety gates, budgets, archive admission, baseline promotion, and rollback. The research introduced in September adds replay and evidence contracts; it does not grant the model authority over measurement policy, scorers, production promotion, or the frozen kernel.

#### Open work


- [ ] **AP-HOLD-RELEASE-REVIEW** (added 2026-11-09): Immediately before the operator lifts the Autopilot hold, re-review every box that waits on the hold. Re-read each box's premise against the then-current kernel, lineup, era and code before any run is armed; tick, rewrite or close as needed. Boxes to re-review:
  - **RTG-02 (this file) NEEDS-RUN boxes:** AP-27, BSV-2, BSV-3, AP-19b, AP-29, AP-48, AP-WM-1b, AP-CH-2, BT-5b, AP-54b, AP-56, AP-70, AP-DGM-PROV, AP-DGM-SEL, SEQ-SHINKA-1, AP-55-ARM, BEP-2, DCP-6, W8, W8b, real_suite_v1 discriminability, W6f, W5 regime-profiled offered load, SEQ-3.
  - **RTG-09:** DAR-LAT-1, DAR-LAT-2, DAR-LAT-3, DAR-LAT-3i, P3-3, P3-4, LRC-1, TD-28.
  - **EVL-47:** VB-AP-FIRST-CYCLE, VB-AP-SPINUP-AP3-SCOPED, VB-CANARY-B-FRONTIER, SC14-B, VB-AP70-ROTATION-READ, P1-PHASE2, and the Autopilot half of VB-REFOCUS-NONEMPTY-READ-PROOF.
  - **Restart-preconditions checklist (from the 2026-11-09 audit; each must be re-proved at hold-lift):**
    - [ ] Operator explicitly lifts HOLD (P0.1) AFTER the next production kernel promotion + stack reorg.
    - [ ] `verify_llama_cpp.sh` + `verify_kernel_store.sh` pass; served binary proven by digest/ggml linkage (`verify_ggml_linkage.sh`), VRAM sampled during GPU roles.
    - [ ] Registry/launch_manifest lineup final; worker_fast, eval_batch_frontdoor, embedder `extra_recipes` resolved; literal `llama.cpp/build/bin` paths and ik_llama launcher text removed or proven unused.
    - [ ] Journal readers shard-aware. 2026-11-09 verified: `preflight_audit.py` (`_jsonl_paths`/`_load_jsonl`, :198-222) and `restart_readiness_report.py` (imports `_load_jsonl`, :855) DO read `autopilot_journal_1.jsonl`; the audit claim they read only the frozen shard was wrong. They use their own chain-walking helper, not `scripts/autopilot/journal_shards.py` (JRN-5); re-check that choice at hold-lift. restart_readiness_report, seq_readiness_report, archive_authority_report all clean.
    - [ ] Brand-new era fenced via operator ratify script (the era and baseline files are human-only): baseline reseated under the new era, E20 corpus (EV19) and current kernel; multi-tier T1/T2/T3 baselines re-proved vs the 2026-08-10 ratification.
    - [ ] SEQ gate decided (SEQ_VERDICT, SEQ_P0_2_BRIDGE) and AP-55 shadow->enforce plan; AP55 stays shadow for the first run.
    - [ ] Planner roster policy re-decided (`start_authority_daemon.py:109-113` pins a temporary two-Codex roster).
    - [ ] Start only via `start_authority_daemon.py` (env-gated); no bare `autopilot.py start`; no other llama-server/autopilot live.
    - [ ] Belief ingest canary armed; first post-hook trial verified; any new write-side capture (selector menu, decoding_id, holdout; see AP-DGM-PROV decision) shipped before the first model-producing run, else AP-DGM-* stay not_evaluable.
    - [ ] Orchestrator API reload ownership per CLAUDE.md; orchestrator at current main, loop-safety C1-C3 in.
    - [ ] Stale journal tail row 1505 "(killed)" / trial counter state (`autopilot_state.json`) checked before the first trial.

##### Remaining Work — Prioritized

- **[declined: ws58 2026-11-03 content-review: curiosity; no autopilot task names it]** AP-26: Test dspy.RLM for autopilot tasks — long-horizon benchmark analysis where metadata-first context exploration avoids context window limits

- [ ] AP-27: Formalize eval tower tiers (T0/T1/T2) as RLVR verification functions with deterministic reward signals per tier (state matching, not LLM-as-judge). **2026-07-11 partial scaffold**: `epyc-orchestrator` commit `7ee919d8` adds `src/autopilot_core/rlvr_tiers.py`, a pure observe-only reward contract with T0 binary, T1 calibrated continuous, and T2/T3 process-attributed reward views plus explicit blockers for missing calibration/process evidence. **2026-07-11 export slice**: `scripts/autopilot/export_rlvr_environment.py` exports prompt-free `ap27_rlvr_environment_row.v1` JSONL from EvalResult/journal artifacts for future RL training. **2026-07-11 report slice**: `EvalResult.to_grep_lines()` emits report-only `METRIC rlvr_*` lines without changing objectives, SafetyGate, Pareto, or journal schema. **2026-07-11 journal slice**: `epyc-orchestrator` commit `69445d43` adds observe-only `eval_details["rlvr_reward"]` journal payloads from the same deterministic contract via the lower-risk main-loop journal assembly point, avoiding the HIGH-risk `EvalTower._aggregate` path. This closes the code-only tier/reward design, offline export, report-only, and journal-payload pieces; AP-27 remains open for inference-dependent Ouro integration. **Implementation plan**: See [eval-tower-verification.md](eval-tower-program.md) EV-1–EV-7. Depends on EV-4 (calibration baseline) and P7 Ouro results.

###### AP-26/AP-27 operator gate packet - prepared 2026-07-11

This packet is staging only; it does not run live RLM tasks, start Ouro training/inference, change SafetyGate/Pareto objectives, or enable the planner spend breaker.

- **AP-26 dspy.RLM live test:** non-inference staging is complete when the RLM endpoint health check still passes and the candidate task has a bounded long-horizon trace fixture with an expected metadata-first win condition. The remaining acceptance evidence must come from a live operator-approved task window: same task against non-RLM and RLM paths, wall-clock/context-window diagnostics, exact model endpoints, and the error class if RLM fails. Do not count the existing `configure_rlm()` health check alone as AP-26 completion.
- **AP-27 RLVR export path:** current code supports prompt-free/offline RLVR rows only. Operator can preview/export existing rows with `cd /mnt/raid0/llm/epyc-orchestrator && python3 scripts/autopilot/export_rlvr_environment.py orchestration/autopilot_journal.jsonl orchestration/autopilot_journal_1.jsonl --output-jsonl orchestration/reports/ap27_rlvr_environment_20260711.jsonl --summary-json orchestration/reports/ap27_rlvr_environment_20260711.summary.json --source-label operator_gate_packet_20260711`. This remains observe/offline data prep.
- **Ouro boundary:** AP-27 stays open until an inference-dependent Ouro integration path exists and passes operator review. The RLVR export, report-only `METRIC rlvr_*` lines, and journal payloads are necessary scaffolding, not a training run or promotion gate.


##### Research Intake Update — 2026-08-09: Meta-Evolutionary Search Layer (rec-005)

- [ ] **AP-ME-1 — Per-operator context budgets.** `ShortTermMemory` (AP-22) is a single ~120-line
  budget shared across the whole loop. Give each operator its own bound. Seed values from the shipped
  OpenMLE-Evo config (`OpenMLE-Evo/tts_search/configs/search/airaevo.yaml`): global
  `max_related_cards 3`; improve `ancestor_k 3` / `sibling_k 3`; crossover `2` / `2`; debug
  `max_related_cards 8`. **Offline-first**: measure current per-operator context size before changing
  anything, so the change has a baseline to beat.
  - 2026-11-02 (ws58 BRF-T3-2, RPL-AP; zero inference): **offline baseline measured; the box stays open.** Code: orchestrator `95d663e5` `scripts/autopilot/operator_context_baseline.py` (+ `tests/unit/test_operator_context_baseline.py`, 4 tests). It re-renders, with the current `render_generated_stm`, the STM the controller saw before each of the 1,372 trials (both shards, supersessions folded) and attributes it to the dispatched operator. **Self-check:** the Running Hypotheses and Optimization Directions sections reproduce byte-identically the STM persisted at checkpoints t1425, t1500 and t1506. Failure Patterns differ only by the later AP-ME-6 typed-line rendering. **Baseline:** one shared bound (30 eligible entries / 2,000 tokens) for every operator. Median 1,970 tokens, p90 1,995; 63% of decisions truncated; **30 related cards** at the median against the OpenMLE seed of 3 (debug 8). Ancestor cards at the median: numeric_trial 3, structural_experiment 6, seed_batch 21, and 0 for prompt/code mutation and GEPA. Sibling cards are 0 (max 1) against the improve seed of 3. Failure cards at the median: 4–15 per operator. EPYC has no dispatched crossover or debug operator. Author inputs other than `description` (median 352 chars) are not journaled, and `mutation_author_context.v1.jsonl` has 0 records. **Residual:** implement the per-operator bound and measure it against this baseline. That second step needs prospective controller runs. Record: `docs/design/backlog-refactor-2026-11/t3-evidence/ap-me1-context-baseline-20261102.json`. [belief: cc]

- [x] **AP-ME1-ME3-SRC — implement default-off prospective assembled-context capture and recorded same-context crossover diagnostics.** ✅ 2026-10-06 — [MAIN source acceptance](../../artifacts/ni08/mutation-context-source-20261006/README.md), original native88/88; APPmain036f4e68. Baseline/budget change and actual donor-selection parent tasks remain open.

- [x] **AP-ME-3 — Complementarity cue for crossover donor selection**, replacing frequency ranking in ✅ 2026-10-31 — IMPLEMENTS `1ef19ab02c9387c33e076dcb1de1bfd08c76fa7f`; [published implementation, controls and provenance](https://github.com/pestopoppa/epyc-orchestrator/tree/22f4e87ff9eb9727248239f93c9f14177ae08c48/benchmarks/results/apme3-donor-selection-20261031); 46 model-free controls passed. [no-belief: software implementation and synthetic controls]
  `informed_crossover_candidates`. **BSV-3 already computes a semantic conflict severity** over shared
  subsystem, files touched, prompt sections touched, feature flags and behavior-signature delta. That
  is a complementarity signal with its sign flipped — crossover donor pairing and BSV-3 conflict
  scoring **must share one function** rather than be built twice with drifting definitions.
  - Implementation detail: both flags remain off by default. The real caller connects the actual writer to same-source native content, the unchanged shared BSV scorer, and PromptForge; incomplete provenance yields no pair. Each prompt donor is capped at 4096 UTF-8 bytes and combined encoded author context at 8192 bytes including trial IDs and hashes. SafetyGate and BSV bars are unchanged; no optimizer-performance, live-adoption or deployment claim.

- [x] **AP-ME-4 — Deterministic `error_signature` plus a repeated-failures counter.** Per the
  correction recorded in `autokernel-research-loop.md` §8.4.0, `ExperimentJournal.unfalsified_hypotheses()`
  is a recency window over the last five trials checking presence of a falsifier string only, and
  nothing marks a hypothesis resolved. A deterministic failure signature is the cheapest available
  upgrade and is a precondition for AP-ME-1's debug budget to select anything meaningful.

- [x] **AP-ME-6 — Negative-evidence rendering discipline.** intake-940#record's dive narrowed this from an
  exclusion filter to a *rendering* rule: a deterministic error signature per card plus a board-level
  repeated-error counter, rendered as one compact typed line rather than raw prior-attempt text.
  Failures still enter context — they enter it small. Pairs with AP-ME-4; feeds AP-ME-1's budgets.


✅ 2026-10-06 MAIN accepted AP-ME-4/6 source15e5b52e after [native21/21 original review](../../artifacts/ni08/failure-signatures-source-20261006/README.md), promoted APP26cb574f. Typed identity/scoped prior totals and compact negative rendering are complete at the source boundary; actual controller execution/rollout is not claimed. AP-ME-1 now permits its offline current-context baseline screening; AP-ME-3 shared-function caller research continues independently. No context-budget, safety-gate or promotion authority changed.


##### Deep-Dive Task Proposals — 2026-05-25 (intake-607 Code-as-Agent-Harness §5.2.1 / §5.2.3 / §5.2.4)

- [ ] **BSV-2 — Differential testing on accept.** Before promoting a mutation, run new vs old on the same sentinels and compare behavior (not just aggregate score). Prefer paired sequential execution under identical server/model snapshot for attribution; use parallel execution only when explicitly approved and when concurrency cannot contaminate latency measurements. Reuse the existing T0/T1 tower; the novelty is paired behavioral comparison. Gate on both scalar regression and signature diff severity. **2026-06-21 scaffold**: orchestrator `0943e7c0` adds `scripts/autopilot/bsv_paired_report.py`, a read-only paired report over already-journaled `question_results` vectors. It emits shared-qid coverage, McNemar/accuracy deltas, BSV signature severity, blockers, JSON/Markdown, and nonzero exit on a blocked candidate. Follow-up `5b29eead` adds `eval-result-pair`, so the same report can compare standalone paired-run EvalResult-like JSON artifacts without needing journal ingestion first. Orchestrator `939750c7` adds `scripts/autopilot/bsv_paired_runner.py`: a default-safe plan-only CLI that, with explicit `--run`, applies baseline/candidate params sequentially, evaluates the same core, writes baseline/candidate EvalResult JSON artifacts, restores baseline params by default, and emits the existing BSV paired report. Follow-up `a3570d8d` restores baseline params even when candidate application fails before candidate eval. Orchestrator `2bdb7abc` wires the mutation accept path behind default-off `AUTOPILOT_BSV2_ACCEPT_GATE`: prompt, GEPA, and code mutations run a pre-mutation baseline eval only when the flag is on, compare baseline/candidate EvalResult vectors through the paired-report backend, reject/revert on `gate_decision=block` or blocking signature severity, accept+annotate watch/pass cases, and preserve existing single-eval behavior when the flag is off. Remaining work is operator-approved live paired runs / rollout evidence before enabling the flag in production windows.

- [ ] **BSV-3 — Conflict-aware acceptance.** When two independently-accepted mutations touch the same subsystem (prompt + routing, two prompts, prompt + tool policy, context packer + batch editor), flag potential *semantic* conflict for review rather than blind compose. **2026-06-21 observe-only ledger landed in orchestrator `168e9bd8`**: under `AUTOPILOT_BSV_OBSERVE=1`, frontier/safety-passing trials now append a bounded `bsv_mutation_dependency_ledger` state row and journal `eval_details.bsv_observe.mutation_dependency` / `conflict_report`, keyed by `subsystem`, `files_touched`, `prompt_sections_touched`, `feature_flags`, `behavior_signature_delta`, and `parent_trial`. Conflict severity increases on shared subsystem/file/section/flag overlap, blocking BSV deltas, different behavior surfaces, or disjoint/opposing sentinel movement across accepted mutations. Still observe-only/default-off; open work is production conflict-policy enforcement after BSV-2 paired-gate rollout evidence is available.
  - [x] **BSV-3a — default-off diagnostic-state conflict policy.** `epyc-orchestrator` commit `d9b8a022` adds `AUTOPILOT_BSV3_CONFLICT_POLICY` (`off`/`observe`/`block`/`review`) inside the existing `AUTOPILOT_BSV_OBSERVE=1` post-SafetyGate/post-Pareto block. It can withhold only BSV ledger/incumbent diagnostic-state promotion on configured conflict severities; it does **not** alter SafetyGate, Pareto admission, action accept/revert behavior, blacklists, baselines, routing, or the planner spend breaker. ✅ 2026-07-11

###### BSV-2/BSV-3 operator rollout packet - prepared 2026-07-11

This packet is for rollout evidence only. It does not enable `AUTOPILOT_BSV2_ACCEPT_GATE`, does not switch `AUTOPILOT_BSV3_CONFLICT_POLICY` to enforcement, and does not change live accept/revert behavior.

- **Plan-only paired run preview:** `cd /mnt/raid0/llm/epyc-orchestrator && python3 scripts/autopilot/bsv_paired_runner.py --baseline-params '{}' --candidate-params @/path/to/candidate_params.json --output-dir orchestration/reports/bsv2_paired_preview_20260711`. Omit `--run` to keep it plan-only; plan mode prints target artifact paths but does not create the output directory or paired report.
- **Live paired evidence:** add `--run` only in an operator-approved quiet window. Leave baseline restoration enabled; `--no-restore` is reserved for an explicit operator decision to keep candidate params applied.
- **Evidence fields to inspect:** paired-report `gate_decision`, shared-qid coverage, accuracy delta, McNemar/statistical diagnostics, BSV signature severity, fleet/version marker, restored-baseline status, and any blocking `conflict_report` entries.
- **Promotion boundary:** `gate_decision=block` or blocking signature severity remains a no-go. BSV-3 `block`/`review` policy should not be promoted past observe-only until BSV-2 has live paired-run evidence under the same gate semantics.


##### Research Intake Update — 2026-07-14

- **[declined: ws58 2026-11-03 content-review: merged into the AP-29 gate as its post-wiring step]** **When AP-29 KnowledgeDistiller is wired** [too-big: conditional on owner-controlled AP-29 comparison and wiring] (currently deferred — see AP-29), apply an explicit **predictability + staleness gate** to it: what to precompute, for how many consumers, invalidate on stack/config change (framing from intake-819 + the 2026-05-20 predictability-co-objective note; adopt_patterns only, no importable artifact). This is a rider on AP-29, **not** new standalone scaffolding.


##### Research-intake integration — 2026-07-22 (measurement-discipline hardening + orx/OpenHyra patterns)

- **[declined: ws58 2026-11-03 content-review: duplicate — eval-tower EV-14b / EV-14b' own the baseline-asymmetry and re-measurement contract]** Harden keep/revert into an explicit self-scoring candidate contract: always retain a proven baseline (valid rollback before any experiment); accept only on a re-verified strict improvement measured under pinned determinism (fixed threads/seed, N-run mean); atomic config swap; require an inline validity note stating what the number does/doesn't prove — including "no gating on a locally-unmeasurable proxy without held-out re-verify"


##### 2026-07-25 — intake Stage-2a dive: GEPA is a guaranteed no-op (P0), plus three overturned premises

- [ ] **AP-19b — supervised first live `gepa_optimize` run (operator-watched), at next stack bring-up.** Operator decision 2026-07-25: blacklist stays lifted; the FIRST live exercise of the repaired path happens in a watched window before any unattended dispatch is relied on. One-shot run; watch the new ERROR path and the journal row. Risk posture verified: adapter evaluates in a SCRATCH prompt root (live frontdoor.md untouched during eval, `gepa_optimizer.py:92-113`), `_prompt_integrity_reason` guards at mutation creation AND apply, applies are git-snapshotted + auto-committed. Cold bring-up recipe: [`esc8-stack-restart-landmine-audit-2026-07-22.md`](../completed/esc8-stack-restart-landmine-audit-2026-07-22.md) § 2026-07-25. Corrected facts (absorbs AP-21): journals show only 8 gepa_optimize trials ever; the supervised run is the first real evidence, so judge GEPA on it, not on the historical no-op record.

- **[declined: ws58 2026-11-03 content-review: merged into AP-19b (the same supervised gepa question on corrected facts: 8 trials ever)]** **AP-21 re-open, on corrected facts.** Journals (all shards) show **only 8 `gepa_optimize` trials ever** (181, 182, 521, 536, 785, 882, 1137, 1144), exactly **one** ever `keep`. `gepa_ratio` is **absent from live `orchestration/autopilot_state.json`** — the 0.30 is a hardcoded fallback at `autopilot.py:8798` on the *autonomous-fallback* path, not stored state and not the primary dispatch. External evidence stands: arXiv 2607.14004 (Terminal-Bench 2.0, matched budgets) reports the GEPA-optimized agent transferring **below** the unoptimized baseline; 2602.01011 reports GEPA returning the seed prompt unchanged; 2606.19605 reproduces GEPA at −3.78 to +7.97 pp. **Gate on AP-19a.**

- [ ] **AP-29 gate before wiring — narrowed.** `KnowledgeDistiller` has **zero non-test callers** (uninstantiated, not flag-off), so this is a free design change now. **The genuine ask is an episodic-only control arm** (retain + delete, abstraction disabled) that the distiller must beat. Justification: arXiv 2605.12978 feeds **ground-truth solutions** through a streaming consolidator and drops a 19-problem ARC-AGI slice from **100% → 52.6%** at R10 — the fault is provably in the rewriting step. Carry the authors' caveat (*"two repeats per question"*, *"point estimates … rather than formal error bars"*).
  - 2026-11-01 source checkpoint: APP `0162aa16098a3cc8c98247f238ac7f2c6f80e63a`, proof `a1f4942edff28dd99c108a1299395a3ec00be8f6`, adds a matched episodic-only control and abstracting candidate using separately created temporary StrategyStores. Original raw IDs, explicit deletions, embedder and retrieval options are shared; only the candidate is passed to abstraction, and caller-selected live stores are not accepted. Seventeen native model-free tests passed, including real KnowledgeDistiller candidate and matched native retrieval. The non-test caller tripwire remains. This establishes the experiment primitive, not a quality winner or production wiring; AP-29 stays open pending the actual authorized comparison. [Source and raw evidence](https://github.com/pestopoppa/epyc-orchestrator/tree/a1f4942edff28dd99c108a1299395a3ec00be8f6/docs/evidence/ap29-episodic-control-20261101). No new quota tick. [no-belief: implementation and fixture controls]
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


##### 2026-07-29 — intake Stage-4: AP-29 write-gate budget, replayable objective comparison, and the prompt-optimizer of record

- [ ] **AP-29b — Compare correctness-first LEXICOGRAPHIC selection against the scalarized cost-aware reward in chapter 08 by DETERMINISTIC REPLAY over already-persisted autopilot trials.** No new inference: rescore saved outcomes and rebaseline only the objective axis that changed — exactly what `agents/shared/MEASUREMENT_POLICY.md` → *Deterministic replay before regeneration* prescribes. Journal shards (`autopilot_journal.jsonl` + `autopilot_journal_1.jsonl`) already carry the per-trial outcomes this needs.

- **[declined: ws58 2026-11-03 content-review: naming/documentation, no behaviour change]** **AP-29c — Name the prompt-optimizer of record as GEPA-class, and adopt compile-on-small-model / deploy-to-large as the CPU-first strategy.** GEPA's cross-model transfer: prompts optimized on **Qwen3-8B** scored **+9.00 aggregate on GPT-4.1-Mini**, beating every optimizer tuned directly on it — which is what makes compiling on a cheap local model economically viable here. Mark **BootstrapFewShot\*** superseded for 2026-era instruct models (**MIPROv2** buys only **+2.6** on Qwen3-8B and **REGRESSES** on AIME/LiveBench). Cost line for any compile is tracked in [`harness-selection-and-integration.md`](harness-program.md#track-harness-selection-and-integration) HS-11 (5k-25k LM calls ⇒ region-locked campaign). Sequencing: this is downstream of **AP-19a/AP-19b** — do not re-argue the GEPA pin (AP-42) before the repaired path has run live once.


##### AutoPilot end-to-end smoke test — 2026-08-03

First full smoke run of the trial loop. Four defects, three silent.

- [x] ~~**Reload the escaped live API at the inference owner's next safe boundary.** Named external~~ (closed 2026-10-29 audit: OBSOLETE → Premise gone: stale escaped API PID 3903691 no longer exists (/proc absent 2026-10-29, no uvicorn running as that pid); stale-process premise cleared by later stack restarts/reloads (reboot-gated-inventory A7 still li...)
      event: the session owning live inference must run the API-only
      `orchestrator_stack.py reload orchestrator` after its in-flight requests drain. Current PID
      3903691 is healthy but stale and carries `PYTEST_CURRENT_TEST` plus pytest `TMPDIR` /
      `ORCHESTRATOR_TMP_DIR`; this session did not kill or reload it across another session's live
      requests (reload-ownership rule, INC-20260728-reload-preemption).

- [x] ~~**E8 quality-baseline reseed — blocked on an operator source amendment pending since 2026-07-27.**~~ (closed 2026-10-29 audit: SUPERSEDED → handoff:143 own note 2026-09-16 + artifacts/operator/ruling_op19_e8_chain_20260827.json (exists) retires the E8 chain; note says closing is the owner call)
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

- [x] ~~**Run the canonical 79-question judge suite on Qwen3.6-27B-MTP-Q8_0.** Inherited from the three~~ (closed 2026-10-29 audit: OBSOLETE → Qwen3.6-27B-MTP-Q8_0.gguf is in model_registry.yaml deprecated_models graveyard (line ~750 of graveyard section); weights gone, instrument target no longer exists)
      `accepted_gaps.yaml` waivers removed 2026-08-03: the gap they waived (missing overall quality prior)
      is closed because quality now compiles per-axis with recorded basis, but their stated closing action
      was never done. The 27B's prior currently resolves 0.8597 via public `mmlu_pro`, not the canonical
      instrument.

- [ ] **Decide the lineup status of `worker_fast` (8102), `eval_batch_frontdoor` (18070) and the
      embedder `extra_recipes` (8096-8098).** They are declared in the launch manifest and so are
      painted as expected services, but none are running. Hidden from the regions-lock panel as a
      display fix; whether they should remain declared is a stack-config decision.


##### Backlog sweep 2026-08-03 — 21 agents, adversarially verified (8 PARTIAL, 1 CONFIRMED)

- [ ] **AP-58 — decide whether to reseed the speed axis on ANY eligible in-era frontier measurement**, since
      the same unreachability shape survives on the other early-return paths (`seq_inputs_unavailable`,
      `seq_not_confirmed`, the monotonic skip and the new `quality_not_measured`), so the speed fence stays
      open if quality never improves again after a speed-era boundary — a design decision, not a defect fix
      (`scripts/autopilot/safety_gate.py`) (found 2026-09-14, noninf sweep).

- [x] **AP-59 — decide whether the E8 quality-baseline reseed row closes as SUPERSEDED rather than done**, as ✅ 2026-10-29 (audit: Decision already answered: handoff:143 note records the E8 reseed row is superseded by ruling_op19_e8_chain_20260827.json (not RTG-02); owner only needs to close row 142 as SUPERSEDED) [no-belief: audit-reconciliation]
      it is superseded by `ruling_op19_e8_chain_20260827.json` and not by RTG-02's work
      (`handoffs/active/autopilot-continuous-optimization.md:1714`) (found 2026-09-14, noninf sweep).

- [x] **AP-60 — remove the import-time `Q_TD_WRITE` test trap** by snapshotting write enablement and match-k
      from the existing environment keys at each QScorer construction, preserving default-off/k10 and integer
      parsing. Set fixture environments before construction and prove existing instances retain their settings
      when later instances use different environments. Existing row-update/work-payload cases must remain.
      Current production launcher supplies the environment before construction; no serving reload is implied.
      ✅2026-10-07 — MAIN accepts original115/115 and exact APP publication; [source/custody](../../artifacts/ni08/ap60-instance-settings-source-20261007/README.md).
      The earlier pytest-always-False wording was overbroad: one fixture patched a module flag after construction,
      while another patched it before construction (found2026-09-14; refined2026-10-06 from APP816/sourceec852).

- [x] **AP-61 — stop hand-maintaining the invocation-log guard's module list**, since it covers five modules
      and will not notice a new route file reading the shared `get_invocation_log()`;
      `src/api/routes/openai_compat.py:285` already reads `repl._invoked_tools` correctly but sits outside the
      guarded set (found 2026-09-14, noninf sweep).
      ✅2026-10-06 — [MAIN source acceptance](../../artifacts/ni08/invocation-route-guard-source-20261006/README.md): all-current-route guard, method/direct-name negative controls, independent46-file Git/AST census; APPmain041ec98a exact source. Test-only/static validation, no runtime/native-quality claim.

- [x] **AP-62 — document the shared invocation ring's synchronisation contract**: `invoke()` appends from
      whatever thread is dispatching and the bound holds only because `deque.append` is atomic under CPython,
      which a future free-threaded or non-CPython build would not guarantee
      (`src/registry/tool_registry.py`) (found 2026-09-14, noninf sweep).
      ✅2026-10-07 — explicit per-instance append/snapshot/clear lock; dispatch outside lock. MAIN accepts original14/14 and exact APP publication; [source/custody](../../artifacts/ni08/ap62-invocation-ring-source-20261007/README.md).

- [x] **`request.files` vision input still has no telemetry image reference.** ✅ 2026-10-31 [no-belief: source and regression verification] APP `f92297de19b425887d1215ceee01e2c25cd30803`; [tests](../../artifacts/compute/codex3-ap-vision-telemetry-20261031/tests-upload.log).
      `vision_stage.py:76` treats `request.files` as vision input, but routing telemetry records
      neither a retained path nor displayable bytes for that form.
      - The committed fix emits bounded path-only metadata for the first direct image, retains no image bytes, and preserves existing precedence; archives are not expanded. The receipt also records 90 routing tests and Ruff passing; no service deployment or model-quality result is claimed. [no-belief: source and regression verification]

- [x] **Evidence-durability symlink guard covers the form that barely occurs.** ✅ 2026-10-30 [no-belief: source and regression verification] [source: epyc-inference-research@a4da03e04331cf7bc2e9af2600d87f3ca4efdaca; test: epyc-inference-research/scripts/validate/test_check_evidence_durability.py]
      `check_evidence_durability.py:306` — `inside_repo = (not absolute) or ...` is unconditionally
      True for relative paths, so `_is_scratch()` is never consulted for them. **416 of 421** registry
      citations are relative, and the remediation playbook tells remediators to use relative paths.
      Also: the new pre-commit wiring exists only as `.git/hooks/pre-commit.extras` on this host —
      unversioned, so no clone gets it.

      - Already fixed by research `a4da03e04` (ancestor of current main): resolve every citation before repo membership/scratch checks; tracked extras are installed by the ROOT hook installer. Eight isolated current-source relative-citation regressions pass. [Evidence](../../artifacts/compute/refactor-c5-r2-and-code-audits-20261030.json).

##### New instances of the same class, found by the critic, previously unowned

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

- [x] **`binding_router` is a parameter nobody passes, gating a whole feature.** `src/api/state.py:97` ✅ 2026-10-31 — orchestrator implementation `053c4858466fff785b7d745e2dc752210904915b`; `tests/unit/test_binding_router_routing.py` and Git capsule `artifacts/audit/binding-router-wiring-20261031/verification.md`; 135 routing tests pass. [no-belief: native software lifecycle/routing regression controls]
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
      - **2026-10-31 decision resolved: wire the existing chain.** The API lifespan constructs the router when the existing default-off flag is enabled, the actual heuristic routing caller passes that state instance to the classifier, and shutdown clears it. Native lifespan→registration→public-route tests prove a rule registered through the existing `RoutingBinding` API overrides the heuristic, while forced and explicit routes retain precedence. An enabled startup creates an empty registry until rules are explicitly registered; no configuration loader, default override, per-session isolation, live flag activation, or runtime reload is claimed. The old tripwire is replaced by behavioral tests. This supersedes the historical unchecked/no-fix annotation above.

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

- [x] **The metric's NAME and its new tooltip both overstate what it counts.** `contention_gate.py:325` — orchestrator `b387c5dded66`; 33 orchestrator + 6 ROOT tests; replacement evidence in APP `artifacts/audit/ni-legacy-autopilot-evidence-replacement-20261031.md`, committed by `cdac2ce9a73e5b79551919b1ea98cbdccf3123bd` (fresh 2026-10-31 source controls; original tmp log absent; historical work excluded from today's quota).
  increments inside `if nway_decision != PairDecision.ALLOW:` — **not** inside the
  `if _prec[nway_decision] > _prec[worst]:` test one line above. So it counts *"the N-way check fired
  non-ALLOW"*, not *"N-way was the binding constraint"*: if pairwise already said BLOCK and N-way says
  QUEUE, it still increments although N-way changed nothing. The dataclass comment at `:92` ("N-way set
  more restrictive than pairwise") is therefore inaccurate, and the new tooltip inherits it —
  *"restricted … beyond what the pairwise check alone allowed"* is now **operator-facing**.
  The subagent spotted the looseness in its own report and wrote the loose form into the UI anyway,
  which is the `§ Reporting Units` failure one level in: a LABEL asserting more than the number
  measures. *(Verified by `mainC` by reading the enclosing block, not the comment.)*
  ✅ 2026-10-30 — the counter now names its actual event, `contention_nway_non_allow_count`, and the
  operator panel says an N-way check returned non-ALLOW whether or not that changed the pairwise
  result. The unrelated admitted-decision count is no longer shown as its denominator. The counter
  increment and every admission decision are unchanged. Orchestrator commits
  `4b0eb6a9a932` (label), `de636086e679` (predicate regression), and `b387c5dded66` (rolling
  compatibility); the root dashboard changes are included in this checkpoint.
  Both dashboards prefer the new field and use nullish fallback to the deprecated
  `contention_nway_restricted_count` alias, preserving a real zero. Focused validation: 33
  orchestrator tests and 6 root tests passed, including real-Node old-key fallback, new-key
  precedence, and zero-value cases; Ruff and diff checks passed. Final compatibility log:
  `/mnt/raid0/llm/tmp/codex-ni-ap-nway-metric-audit-20261030/compat-focused-rerun-20261030.log`
  (SHA-256 `dc6ab57893870bdcc3b791c582332eb4d1fd7ffd2eb48f771efe45f68ebf718d`). The source commit
  `b387c5dded66` is public on orchestrator `main`. No admission policy, counter predicate, service, or
  measurement rule changed. [no-belief: code/API wording correction; no measurement]

- [x] **SIBLING SWEEP: six more runtime imports are hard, unguarded and declared NOWHERE** — the same ✅ 2026-10-31 — APP `eb19045c4f1d4db04e80cd9b680c1187b9d4ebb9`; [implementation evidence](https://github.com/pestopoppa/epyc-orchestrator/blob/eb19045c4f1d4db04e80cd9b680c1187b9d4ebb9/artifacts/audit/runtime-dependency-sweep-20261031/README.md). [no-belief: model-free implementation checks]
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
  - Completion limits: six runtime imports checked; five focused tests passed; actual UI constructor passed on Gradio 6.5.1; model-free CPU imports passed against exact Torch 2.9.0 / TV 0.24.0 / Transformers 5.22.1. Locked Gradio 6.15.1 was not tested at its exact version. No GPU, model-runtime, or deployment validation.

- **[declined: ws58 2026-11-03 content-review: duplicate — engineering-hygiene LOOP-57 / NIB2-TESTDEBT-1 own the red-test triage]** The ~77-test retired-topology failure bucket.

- **[declined: ws58 2026-11-03 content-review: a human-only-file correction with no behaviour change; route through a ratify script if the operator wants it]** `MEASUREMENT.md:148-158` still states the durability checker "fails on any citation resolving
      outside the repository" — now false after the retarget. Human-amendment-only; no owner assigned.

##### Operational hazards found this session

- [x] **Cosmetic follow-on — explicit escalation label.** ✅ 2026-10-29
  Orchestrator main `cdd828cd71969f94fc9d130ce464c9344f59c086` renders
  `health_escalated` as `phase health escalated`; the red `bad` class is preserved.
  Both inline script blocks parsed with Node; helper checks cover escalated, active and
  unknown labels. [no-belief: display-only correction; no measurement claim]

- [x] **Flaky under load, flagged to its owner:** `test_daemon_owned_state_ownership.py` (landed today) ✅ 2026-11-01 — closure hygiene; implemented 2026-10-31 in epyc-orchestrator@4b379a46f9f23aa3ee11d9acfbc0eafbbb301fa4:`tests/unit/test_daemon_owned_state_ownership.py` [closure: hygiene] [no-belief: test fixture repair, not a measurement claim]
  fails intermittently under full-suite `-n 16` while passing 19/19 in isolation and under `-n 8` on
  both trees. Ruled out as test method by the finder before reporting, not assumed.


##### Context accounting, `-np`, and the E8 blocker (2026-08-03, evening)

- **[declined: ws58 2026-11-03 content-review: resolved by the stack restarts since 2026-08-08 (P1-3)]** **Restart the stack so the `-np` change goes live.** The guard reports 12 live-process drift
      errors (`frontdoor expected 4, live 16`, etc.) — that is config != running, working correctly.
      Blocked only on the in-flight E8 calibration.

##### New tasks from this work

- [x] ~~**Regenerate the E8 context coverage scan.** `artifacts/operator/e8_quality_context_coverage_v4_20260727.json`~~ (closed 2026-10-29 audit: OBSOLETE → E8 context-coverage scan belongs to the E8 chain retired by ruling_op19_e8_chain_20260827.json (handoff:143); fleet shape it measured also replaced (v10, 2026-09-22 cutover))
      reports `required_tokens` in BYTES and was taken against the pre-2026-07-30 fleet. Every
      downstream artifact built on it — including the Options A-D decision package and the two 19 MB
      replacement-map candidates — inherits both errors. Rerun with real tokenization against the
      current shape before anyone acts on that decision.

- [x] **Per-instance `-np` cannot be declared.** `slots_by_shape` is keyed by shape CLASS (`full` / ✅ 2026-10-31 — orchestrator implementation `eda654775ddac4a7bec41b36563d7e4860cd895d`; tests `tests/unit/test_stack_priors_compiler.py`, `tests/unit/test_orchestrator_stack_reload.py`, and Git capsule `artifacts/audit/ni-instance-slots-20261031/verification.md`; 502 caller/admission/attestation tests pass, default runtime caches unchanged across 16 roles. [no-belief: declaration/compiler/runtime consistency controls]
      `half`), so two `full` instances of one role cannot differ. The compiled artifact is already
      per-PORT (`slots_by_port`) and `_resolve_parallel_slots` is explicitly "for the instance being
      launched, not for the role" — so this is a declaration-schema gap, not a plumbing migration.
      Same shape as the registry's own `kv_quant_by_shape` future-proofing note.
      - Optional `server_mode.<role>.serving_shape.slots_by_instance` maps declared ports to positive slot counts before shape/scalar/fallback resolution. The compiler reads its handed registry and retains the existing per-port artifact; native instance lookup, server argv, admission/attestation, capacity reporting, and local batch certification agree. Explicit topology and owner-registry data remain authoritative; heterogeneous URL pools use conservative per-member limits. The critical base resolver's behavior and independent eval-batch fallback remain unchanged. Four stale usage fixtures were corrected to the native attribution protocol after exact base/candidate controls; no production declaration, live capacity, reload, or inference changed.

- [ ] **Routing is not context-length aware.** Nothing inspects prompt length before choosing an
      instance, so a long prompt landing on a narrow slot gets a hard 400 rather than being routed to
      a wider instance or to `ingest_long_context`. The frontdoor group is heterogeneous by design
      (`:8070` 16,384/req vs `:8080`/`:8180` 65,536/req before this change), so the same request
      succeeds or fails depending on which instance takes it.

- [x] ~~**Settle Qwen3.6-27B's architecture — it gates a 2x context win on the MI210.** `:8083` runs~~ (closed 2026-10-29 audit: OBSOLETE → Premise gone: :8083 no longer serves Qwen3.6-27B (epyc-orchestrator src/config/models.py:297-299 comment: architect_critic/Qwen3.8 since 2026-09-27 swap); Qwen3.6-27B Q8_0/MTP weights are in the deprecated_models grav...)
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


##### Lost updates, stack-restart ergonomics, and `-np` live (2026-08-03, late)

- [x] **P1 code repair — configured-primary provenance.** Orchestrator main `63f34e9845b028b364a14ad0c618dc60ef96c0a1` measures only both configured primary instances, including faithful overlap; alternate placements emit existing unknown-pair entries. Actual writer→YAML→loader→public-policy controls preserve existing unknown traffic behavior, unqualified all-unknown output and correct mixed topology stamps.166 controls, Ruff and full `make gates` pass with task-private tools. Stored matrix and consumer policy unchanged; the old1.89 row is archival commentary, not a new measured result. The original re-bench below remains open. ✅ 2026-10-30 [no-belief: prospective writer source repair; no new ratio]

- [ ] **P1 — THE CONTENTION MATRIX ADMITS A DIFFERENTLY-MEASURED PRIOR AS A ROLE-PAIR VERDICT.** [too-big: live n-way policy and matched geometry rebench need gate owner]
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

- [x] **The legacy substring fallback FALSE-POSITIVES, and the evidence is comical:** orchestrator `d7aa9d952b5f6312cfef02059145e698c6735756`; 163 direct-caller + 39 EV6b tests; see `progress/2026-10/2026-10-30.md` → *AutoPilot legacy numeric-status false positive*. Applied to
  `outcome_details` it flagged 23 tasks as infra purely because **`"1.503s"` contains `"503"`**. Every
  one of its hits on the live journal was that. The dry-run deliberately uses only the structural
  `[ERROR:` anchor. This is the strongest argument yet for structural-over-substring classification —
  the fallback does not merely miss infra failures, it invents them. ✅ 2026-10-30 — the shared
  measurement guard now matches legacy numeric HTTP status tokens only as standalone ASCII codes,
  excluding adjacent letters, digits, underscores and decimal points; textual legacy fallbacks and
  structural precedence remain intact. Regression tests cover `1.503s`, `0.502s`, `1.504`, `1503`,
  `foo503bar`, `503s`, standalone/HTTP/status 503, actual `http_status=503`, the anchored `[ERROR:`
  path and legacy connection text through both classifier APIs. Private orchestrator commit
  `d7aa9d952b5f6312cfef02059145e698c6735756`; integrated source SHA: `b101d4c108c24ca9c24d0b443f32c11200236c61af1dc82c41a956d8929bd470`. Eight direct-caller suites passed
  163 tests; EV6b caller suite passed 39 tests; Ruff lint and diff checks passed. GitNexus at indexed
  source reports CRITICAL, 121 affected nodes and 19 direct callers; its index predates current main
  by 40 commits, while the edited function is unchanged between indexed checkout and private base.
  No live journal recount or service reload was performed. [no-belief: code-only classifier correction; no measurement]

- **[declined: ws58 2026-11-03 content-review: historical records; the ETR-1 era scoring supersedes them]** **8,855 failure records (pre-2026-07-27) have NO `work` payload at all** — nothing durable
  distinguishes infra from genuine, same mechanism as the seeding path. Unclassifiable, and stated as
  such rather than estimated.

- [x] **Close the write-side provenance gap — this is why the assessment above is unresolvable.** ✅ 2026-11-01 — APP IMPLEMENTS `7e67e78ce5e6cf3979420ef76d2fab038fd844fd`; [published Git proof and test receipt](https://github.com/pestopoppa/epyc-orchestrator/blob/99791dd82732a6ffccad1c79c67e9b019143ba66/artifacts/engineering/reward-write-provenance-20261031/code-commit-proof.json); 122 model-free controls. Authored facts carry prospectively; absent or conflicting facts remain unknown. Historical failures below remain open. [no-belief: prospective software source repair; no native-run measurement warrant]
  `seeding_injection.py`'s context builder must carry `disposition` / `infra_reason` / `http_status`
  on every reward, so the next occurrence IS filterable. Verbatim the belief-kernel rule: wiring the
  **write** is cheap and permanent; retrofitting the **read** is impossible.

- [ ] **Operator decision on the 419 update-path rows.** The progress log records `old_q` for each, so
  the depression is arithmetically reversible — but reversing it would also undo every LEGITIMATE
  wrong-answer signal in the same set, and no predicate separates them. Recommended: materialise the
  419 `(memory_id, old_q, new_q, ts)` as a read-only artifact and let the operator decide. **Do NOT
  purge** — a purge needs a predicate and there is none; any proxy destroys real negative signal.

- **[declined: ws58 2026-11-03 content-review: bookkeeping of a stale citation]** **Queue-hygiene correction, routed to the coordinator:** the B-bucket cited
  `numa-topology-cutover-resume-20260730.md:327` for this defect. That row is **P1-7
  `vision_escalation` has a PHANTOM 5-port fleet** — a different item, still open and untouched. The
  code defect was real; the row pointer was not. Screening caught it before dispatch.

- **[declined: ws58 2026-11-03 content-review: a lesson already in project memory, not a task]** **A HAZARD THAT CORRECTS OUR OWN STANDING ADVICE: `git commit -- <path>` BYPASSES THE INDEX.**
  It commits the WORKING-TREE state of that path, so it sweeps any other agent's uncommitted hunks in
  the SAME FILE. Pathspec commits protect against CROSS-FILE contamination only. This fleet has been
  telling itself "explicit pathspec commits" all session as though it were sufficient; it is not.
  The safe idiom when the target file is dirty with someone else's work is to filter your own hunks
  and `git apply --cached`, then commit from the index. *(Demonstrated live: the resume agent hit
  exactly this and used it to avoid sweeping 63 lines of another agent's in-flight work.)*

- [x] **`ImportError: cannot import name 'LLAMA_SERVER' ... circular import` prints on every stack ✅ 2026-10-30 [no-belief: source import regression verification] <!--[source: epyc-orchestrator@74c68a2a8e01a0f4a8c93a49fa32c0b85494f501; test: epyc-orchestrator/tests/unit/test_config.py; artifact: epyc-root/artifacts/compute/refactor-c5-r2-and-code-audits-20261030.json] -->
      command.** Fail-open — `runtime-facts selected-servers read failed` and the
      `ORCHESTRATOR_STACK_NUMA_MODE=both env-filter branch failed ... falling through to
      stack-priors`. Both degrade silently to a fallback path, so a real defect there would be
      invisible. It also makes genuine errors hard to spot in stack output.


      - Already fixed by orchestrator `74c68a2a8` (ancestor of current main), with kernel-store resolution preserved by `42b926ff0`. Self-contained path initialization removes the cycle;28 focused tests and a fresh NUMA=both CLI help pass without the reported warning. No production stack operation or reload. [Evidence](../../artifacts/compute/refactor-c5-r2-and-code-audits-20261030.json).
      - Git evidence: implementing APP `74c68a2a8e01a0f4a8c93a49fa32c0b85494f501`; committed `tests/unit/test_config.py`; retained ROOT `artifacts/compute/refactor-c5-r2-and-code-audits-20261030.json` (source-import regression summary).

##### Scorer repair and an unprovable outage (2026-08-04)

- **[declined: ws58 2026-11-03 content-review: a 2026-08-04 incident with no reproduction path; nothing recurred]** **UNEXPLAINED: every llama-server exited at ~07:00 on 2026-08-04 while whisper and tts —
      same stack start, two seconds apart, same parentage — survived.** That selectivity rules out
      container/host restart (uptime 5d17h), OOM (no kernel oom-kill, no earlyoom entry, 1,079 GB
      available), tool-shell reaping (own sid+pgid, parented to containerd-shim), nightshift
      (`inference_guard.sh` only reads), cron (none), and any repo script. Surviving evidence was
      one line — `srv operator(): cleaning up before exit...`, a signal handler. Six other claude
      sessions are live on this host; INC-20260731-broad-process-pattern-kills is the leading
      explanation and is NOT proven. Logs now append, so a recurrence is diagnosable. **If it
      recurs, capture `logs/llama-server-*.log` BEFORE restarting.**

- [x] **A THIRD SILENT-SCORING DEFECT, found while porting: the research repo's diverged <!-- ✅ 2026-08-23 [implementation: epyc-orchestrator 07a20a7cface6614c595f42981e385ae3695ee42 (2026-07-20), epyc-inference-research d876adfef50912cdeaad14b34d416dc9608479d9 (2026-08-23); tests: tests/unit/test_debug_scorer_code_execution.py, scripts/benchmark/tests/test_debug_scorer_b7_delegation.py; audit: epyc-inference-research/scripts/kernel_rnd/autokernel/evidence/p7_3a-current-suite-triage-20261031.md] [no-belief: historical source reconciliation; no new scoring measurement] -->
  `debug_scorer.py` answers an `entry_point` oracle with `assert f() == <expected text>`** — a
  ZERO-ARG assertion that a function taking arguments can never satisfy, so **correct answers scored
  False on every such row**. Ported the real execution plus the orchestrator's refusal; a test pins it.
  Same family as debugbench's reference-fails: the scorer rejecting right answers, not just accepting
  wrong ones.

- [x] **Unfenced Python scorer repair (2026-10-30).** Orchestrator `65b2b0e66b4da5ff718141bee1f87457b2b36149` preserves complete valid modules and future imports. Exact-source validation: 67 passed, one lifecycle test deselected with matched base/candidate zombie and drain evidence. The earlier 344-row estimate was not rescored; future measurements must pin the new scorer version. See `artifacts/audit/orch65b-unfenced-scorer-20261030.md`. [belief: cc]

- [x] **REGENERATE `ma_hard_code_001`** — hand-authored tracked YAML. ✅ 2026-10-31 RESEARCH `a0a3df0ff43a9a66fe1f1f05a9e24e9214511b70`; [test](../../artifacts/compute/codex3-ma-hard-code-001-20261031/TEST.log). [belief: cc]
  (`mode_advantage_hard.yaml:288-328`), two defects: `test_code` wires stdin and never asserts, AND
  the prompt ships the author's unresolved self-correction (says 3, then 6; correct answer is 6).
  ✅ 2026-10-31 — RESEARCH `a0a3df0ff43a9a66fe1f1f05a9e24e9214511b70`: corrected example and three executable input/output cases; native scorer accepts a correct bounded-path program and rejects wrong constants. [Test](../../artifacts/compute/codex3-ma-hard-code-001-20261031/TEST.log). The separate live-pool rebuild below remains open; no historical scores were re-derived. [belief: cc]

- **[declined: ws58 2026-11-03 content-review: stale — the pool has been rebuilt and restarted many times since 2026-08-04]** **The live pool still carries the OLD oracle** [too-big: pool-owner rebuild and instrument evidence remain unverified] — the rebuild takes effect on the next pool
  rebuild, which is a measurement-instrument boundary (`eval_tower` stamps instrument identity) and
  needs scheduling by the pool owner. Until then the 4 debugbench rows in `core_v2` still score
  vacuously, and **historical debugbench scores remain uninterpretable and were not re-derived**.

- [x] **Residual guard gap:** `vacuous_rows()` only inspects the substring family, so a *programmatic*
  row whose oracle is input-satisfiable would not be flagged. Debugbench is covered by its own build
  gate; nothing generic covers that class.

- **[declined: ws58 2026-11-03 content-review: a note, not a task]** **Stated limit, not hidden:** whether an ALTERNATIVE correct repair passes is bounded by argument
  (4-added-line cap + the prompt's "fix ONLY the bug"), not by measurement — no second reference exists
  in the data and upstream ships no executable tests, so no oracle over this dataset can do better.
  Test-pinned rather than left implicit.

- **[declined: ws58 2026-11-03 content-review: a dispatched August workflow with no consumer; its lens (essential vs incident-scarred) is the refactor program's job]** **Design-lens review of AutoPilot dispatched** (workflow `wf_50aef395-2a4`) — essential vs
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

##### 2026-08-04 — AutoPilot kept HALTING; the objective flipped to tasks/hour

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

- **[declined: ws58 2026-11-03 content-review: duplicate — kv-cache-program KVU-5 (preemption with slot save) owns it]** **AP-49 — Explore true live-decode checkpoint/resume only on a versioned experimental kernel.** The
      production llama-server defers slot save/restore while `slot->is_processing()`, so current migration is
      an idle-session KV handoff and cannot relocate an active decode. Prototype a token-boundary pause →
      checkpoint → restore → resume protocol that preserves KV plus sampler/RNG, grammar/tool-parser,
      speculative-decoder, request/stream ownership, cancellation, and exact output continuity. Start from
      fresh frozen production into `llama.cpp-experimental`; do not modify the production kernel. Require
      byte/token continuity tests, failure-atomic rollback, bounded pause/transfer cost, and a demonstrated
      advantage over request-boundary drain-and-switch before considering a new production version.


##### 2026-08-05 — Research intake: least-commitment diagnostics and compression safety

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


##### 2026-08-07 — reset-free trajectory refinement, proposal-only (intake-1016/1020)

- **[declined: ws58 2026-11-03 content-review: merged into AP-CH-2 (the adapter is the reset-free arm of that comparison)]** **AP-CH-1 — Add a default-off adapter that turns a bounded recent trajectory window into typed
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


##### Research Intake Update — 2026-08-15 (feedback-conditioned mutation; intake-1139/1143/1144)

- [ ] **P17.BT-5a — Retrospective feedback synthesizer (do this FIRST).** Consume logged
      (config, score) pairs from the existing autopilot trial history and emit a **directional** hint
      ("increase X", "decrease Y") for the proposal step. Offline, no new eval loop, no new inference
      over the historical corpus. Bench against the no-feedback baseline before wiring anything live.
      Admission test from `intake-1144`: feedback is **DIRECTIONAL iff it determines the SIGN of the
      change**; **non-directional** (names the offending dimension but withholds the sign) still beats
      a scalar and takes a narrowing path; neither → existing scalar path.
  - 2026-11-02 (ws58 BRF-T3-2, RPL-AP; zero inference): **synthesizer built and benched offline; verdict INCONCLUSIVE_INSUFFICIENT_COVERAGE, so 5b stays gated.** Code: orchestrator `95d663e5` `scripts/autopilot/feedback_synthesizer.py` (+ `tests/unit/test_feedback_synthesizer.py`, 7 tests). It reads both journal shards with supersessions folded and the STM trust filter, scores each trial as quality minus the median of the 10 preceding same-tier eligible trials, emits directional / non-directional / no hints per param (|Spearman rho| ≥ 0.30 named, bootstrap sign stability ≥ 0.80 directional), and benches in a leak-free walk-forward against the no-feedback baseline with a scrambled-sign control. Result over the retained corpus: 87 eligible (config, score) pairs (trials 1058–1505); only **8** trials touched a parameter that carried a directional hint at proposal time (follow 6, success 0.17; oppose 2, success 1.00; no-feedback baseline 0.375; uplift −0.21; scrambled p 0.75). Predeclared minimum: 20 hinted trials and 8 per arm. The threshold-free coverage ceiling is 21 hinted trials. 216 numeric_trial rows (every shard-0 row) logged empty params and cannot be pairs; they were not back-filled. The secondary speed objective is also inconclusive (9 hinted). **Residual:** re-run the committed script when the journal holds ≥ 20 hinted trials with ≥ 8 per arm. That needs new numeric trials with logged params, which means an operator-owned AutoPilot restart. Record: `docs/design/backlog-refactor-2026-11/t3-evidence/ap-p17bt5a-backtest-20261102.json`. [belief: cc]

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
      **cannot** be rescued this way — it lacks exactly these fields — which is precisely the point. [too-big: comparison writer depends on unfinished P17.BT-5a and 5b; handoff session owns integration]
  - 2026-10-31 source audit (codex-ni): this capture belongs at P17.BT-5b's prospective artifact-comparison writer, after P17.BT-5a shows signal. Neither writer exists on orchestrator main `bfa87454f482156b27b6e944af95bde46ddf4441`: `ParetoArchive.bt_tiebreak_topk()` compares numeric objective tuples, while `rubric_scoring.judge_ranking_stability()` derives fractional/tied preferences from scalar scores; neither receives candidate artifact text. These are not binary artifact comparisons to relabel. Research's static external pairwise adapter is a separate benchmark source. Keep this task open, with the content capture required when the P17.BT-5b writer is built; no quota completion or historical backfill. [no-belief: source dependency audit]

**Design fork to decide inside 5a/5b, not before**: `intake-1139` **resets** its feedback buffer on
every accepted candidate; `intake-1144` **accumulates** and subsamples, treating history as a durable
asset. Both are cited precedents; pick per pilot and record which.

**Cost note**: roughly 400–500 short structured-output calls per optimization run at the source's own
settings — short prompts, structured output, no long context (the buffer reset bounds it). A good
Qwen3.x-class MI210 workload. The source's whole pipeline ran on an **8B open-weight** model and beat
its comparator on 2 of 4 tasks there, so no frontier API is required. Cite `intake-1139#record`.


##### Research Intake Update — 2026-08-15 (acceptance cannot currently see a no-op; intake-1129/1141)

- [x] **SG-W1 — No-op guard.** ✅ 2026-10-30 [no-belief: source guard and tests] Refuse to promote a candidate whose config/diff is byte-identical to its
      parent, regardless of score. Under a stochastic LLM-graded objective a byte-identical candidate
      can score above its parent on noise alone, and `intake-1141`'s own data gives the magnitude: an
      **unchanged** harness scored 0.800 and 0.547 on the same suite. A few lines; zero exploration cost.

      - Orchestrator `e3adf8b097e09f7a4c3d582e26f95bdca077bbae` skips byte-identical prompt and GEPA candidates before eval/promotion; code, numeric and structural paths already reject no-op changes. All148 action tests passed against current-source archive. Baselines and score thresholds unchanged; no reload or live efficacy claim. [Evidence](../../artifacts/compute/refactor-hils2-and-source-guards-20261030.json).

- [x] **SG-W2 — Warrant as telemetry (explicitly NOT a gate).** ✅ 2026-10-31 — APP `48ade72dc443d70294ce0e9db127b6f065bf9376`; [tests](../../artifacts/compute/codex3-sg-w2-20261031/FINAL-v3.log). [belief: cc] Record whether an accepted edit cites
      an observed failure instance, without blocking on it. Structural obstacle to plan for:
      `SafetyGate.check()` takes only an `EvalResult`, so the action payload must be threaded to the
      gate. The full warrant gate is **deliberately deferred** until this telemetry says it matters,
      because the cost is real and measured — `intake-1134`'s equivalent guidance had the lowest
      variance *and* "prevented breakthrough modifications", and `intake-1140` found trace-reading
      share **negatively** correlated with gain (ρ −0.31 to −0.64). The cheapest exposure measurement
      is the known-null corpus filed as EV-14f in
      [`eval-tower-verification.md`](eval-tower-program.md).
      ✅ 2026-10-31 — APP `48ade72dc443d70294ce0e9db127b6f065bf9376` captures bounded explicit trial citations on action-local retention, resolves eligible journal negative evidence, and preserves unresolved/ineligible cases as UNKNOWN. The final trial verdict remains separate; this telemetry never gates acceptance. [Tests and journal round-trip](../../artifacts/compute/codex3-sg-w2-20261031/FINAL-v3.log). The known-null experiment and belief projection/canary remain open. [belief: cc]

- [x] **SG-W3 — Dispose of `src/diversity_gate.py`: wire it or delete it.** ✅ 2026-10-29 [no-belief: retirement of unused code; no measurement claim] [source: epyc-orchestrator@da31e38b6bafc1dbcd91739330d6ef0c4756c923; test: epyc-orchestrator/tests/unit/test_module_identity.py]
      Removed in orchestrator main `da31e38b6bafc1dbcd91739330d6ef0c4756c923`, together with
      tests that exercised only this unused surface. The live autopilot safety gate remains;
      the module-identity guard now requires both retired source gate paths to stay absent.
      Four relevant suites passed all 46 tests after integration.
      Original rationale: zero production importers,
      warn-only by default (`SAFETY_GATE_WARN_ONLY` defaults to `"1"`), renamed 2026-07-20 out of a
      bare-name collision with `scripts/autopilot/safety_gate.py` (the module the autopilot actually
      imports). Its `evaluate()` accepts on a raw `quality_delta > 0` with no resolution band, so it
      reads like a live acceptance surface and is not one — a subagent during the 2026-08-15 intake
      session read it as our live gate and was wrong. A plausible-looking second "SafetyGate" in the
      tree is a standing misreading hazard.

> **Owner note (2026-08-15).** SG-W1/W2/W3 were filed against `safetygate-rlvr-provenance-audit-2026-07-22.md` per the approved Stage-3 plan, then relocated here when that handoff was found already archived to `completed/` on `origin/main` (`3615bdc3`) — filing live tasks inside `completed/` would have been the result. Content unchanged.


##### Research Intake Update — 2026-09-07

- [x] **AP-51 — Diff THREE JIT admission rules against `ParetoArchive`.** ✅ 2026-10-06 MAIN accepted [the equation-by-equation comparison](../../docs/reference/ni08-admission-and-skill-granularity.md#ap-51-three-rules-act-at-different-stages), with current tier-local task-rate axes verified. Training-pair construction, bank retention and reward channels remain distinct; no code/gate or efficacy claim. `intake-1320#02`.

- **[declined: ws58 2026-11-03 content-review: a standing caution, not a task]** **AP-52 — STANDING CAUTION against the frozen-frontier-proposer contract.** Two prompted
      frontier editors reading real failure traces produced **net negative** deltas over 1,270
      held-out tasks (−4.3 ± 2.5 and −0.4 ± 3.6), with 1/9 and 3/9 failing validation outright.
      **PromptForge is that loop.** SafetyGate scores the same suite the mutation was proposed from;
      nothing measures out-of-sample transfer of an accepted mutation. Negative deltas concentrate in
      `rewrite_action` / `force_action` patches (all 4 REPLACE patches regress, but the single worst
      patch is hint-only CONSTRAIN — MHS-5, orchestrator `4f28e6c3`, pending merge), which ties this directly to **MHS-4** in
      [`promptforge-mutation-safety-contract.md`](autopilot-program.md#track-promptforge-mutation-safety-contract).
      The caution itself is zero-compute and lands with this row. **The held-out arm on accepted
      mutations is COMPUTE-GATED: filed, never run here** — it needs eval compute and belongs to
      another session. `intake-1323#record` (dive actionable D3). Dependency: MHS-4.

- [ ] **AP-54b — (COMPUTE-GATED, filed not run) wiki-fence A/B on eval rollouts.** Same eval suite
      with the knowledge fence armed vs. unarmed, paired per question. Also record touched paths in
      question results so the unarmed arm shows whether the wiki was read at all. Run only after the
      fence and path-recording land and the operator picks the arming mechanism (see AP-54).
      Owner: an eval-compute session.


##### Research Intake Update — 2026-09-14 (intake-1346…1366)

- [ ] **AP-56 — Determinism certification before N=1 promotion.** llama-server fixed seed and fixed
      slot count; replay the baseline action chain and require identical trajectories before trusting a
      single-run verdict. External, descriptive: promotion rate 7.9% (1,223 decisions) → 25.2% (131)
      after determinism. Inference-gated; measure the local signal change first. `intake-1355#01`.


##### Research Intake Update — 2026-09-15 (noninf-20260914: orx / auto-research critique cluster)

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
      - **[declined: ws58 2026-11-03 content-review: merged into AP-63 as its precondition]** **AP-63(b)** — lane-arbiter precondition: blocked on the OP-41 sequence above (champion
            finalised → production promotion → host reboot, operator-owned design).
      - **[declined: ws58 2026-11-03 content-review: merged into AP-63 as its post-restart check]** **AP-63c** — after the first post-restart trial, check (read-only) that its journal row
            carries a non-empty `run_manifest` whose `manifest_sha256` matches the in-flight marker it
            was dispatched under, plus a `lineage` block. A pre-dispatch skip must carry `{}`.
      - **[declined: ws58 2026-11-03 content-review: merged into AP-63 as its follow-on decision]** **AP-63d** — decide whether `parent_trial`'s consumers (config_diff, PEAF surprise r²,
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

- [x] **AP-66 (S3-AP-04) — NumericSwarm must tell INFEASIBLE configs to the sampler, not hide ✅ 2026-10-31 — IMPLEMENTS APP `464f129006c2968317f691ffac8a432a1e67a38e`; [tests and replay evidence](https://github.com/pestopoppa/epyc-orchestrator/tree/464f129006c2968317f691ffac8a432a1e67a38e/benchmarks/results/ap66-table-replay-20261031). [belief: cc]
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
  - Implementation accepted: the real numeric dispatch finalizes Optuna only after native gate observation; infeasible trials carry finite worst-observed qualified objectives and bounded normalized constraints, with crashes strictly worse than finite misses. Non-answers remain PRUNED/unknown; an ordinary wrong answer alone is not config-failure evidence. The first compatible objective anchor flushes durably pending cold-start failures; abrupt SIGKILL/power loss can still leave an unrelated RUNNING trial. Missing quality/cost/reliability provenance cannot seed the anchor; cost is a reported-tier estimate. Integrated caller/gate/sampler controls passed 112/112 on final source; raw receipts and source bindings are committed with the implementation. No live reload or activation.
  - Offline acceptance at the predeclared 100-call endpoint: FAIL/raw/bounded mean rule-infeasible rates were .782/.754/.754; at 50 they were .828/.828/.828, so no 50-call improvement is claimed. qLogNEHVI rates were .366/.191 at 50/100. Mean hypervolume at 50 was 54865.521/54865.521/54865.521 versus qLogNEHVI 41912.119; at 100 it was 60742.035/60202.704/60202.704 versus 41912.119 (requests/s × ms). Four arms, ten seeds, matched 20-row Sobol starts, and all 4000 stored/evaluated vectors were verified exact native table hits. Frequent joint-row repair before storage is disclosed (100-call FAIL/raw/bounded/qLogNEHVI fractions .800/.784/.784/.371); this is finite-table domain conditioning, not a production result. NSGA-II's default population size is 50. Earlier post-storage projection remains exploratory/NOT MET. This satisfies the literal offline rate-falls bar at 100, without statistical significance, hypervolume improvement, production optimizer gain or adoption claims. See the committed replay README and exact-row verifier above. [belief: cc]

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

- [x] **AP-69 (S3-AP-07) — label every planner-critic verdict kind=proposal_filter, never validation**, in the journal and any receipt/dashboard summarizing it. Orchestrator `e822e3788ec016be1f7ee06d13225179a6dc816e`; 271 tests; replacement evidence in APP `artifacts/audit/ni-legacy-autopilot-evidence-replacement-20261031.md`, committed by `cdac2ce9a73e5b79551919b1ea98cbdccf3123bd` (fresh 2026-10-31 source controls; original tmp log absent; historical work excluded from today's quota). The critic
      (local_frontdoor) reads only the planner's prose draft, which is the manuscript-only review
      shape (intake-1373#01). This is the autopilot twin of S3-AKU-05, with the kind enum widened to
      script / oracle / proposal_filter / llm_judge. Eval tower + safety_gate stay the validation
      path. **Implemented** in epyc-orchestrator `e822e3788ec016be1f7ee06d13225179a6dc816e`
      (initial writer `dff7dabbd4cc95ee2e310349cc0930e6eaa4eee4`, plus digest guard). Coordinator/archive
      and provider-health records mark only supported parsed critic decisions `proposal_filter`; absent
      and invalid decisions remain unknown. The prior-decision digest preserves a missing legacy kind as
      `unknown_legacy`, preserves only exact `proposal_filter`, and maps unsupported explicit values or
      malformed types to `unknown`. No grade, validation gate, threshold, or live service changed. Five
      focused files passed 271 tests; log `/mnt/raid0/llm/tmp/codex-ni-ap69-proposal-filter-20261030-orch2/VALIDATION-AP69-r3-20261030.log`
      (SHA-256 `736ab9a3a24f0cf778115c2d2a227e66883033457ad53dfc237e419ba936fb37`). ✅ 2026-10-30
      [no-belief: implementation/tooling; no new measurement]

- [ ] **AP-70 (S3-AP-08) — rotation-boundary generalisation drop, observe-only.** At every
      core-rotation boundary, score the outgoing incumbent on both the outgoing and the incoming
      draw. Journal drop = q(outgoing) − q(incoming) with both rotation indices. Report mean drop ±
      SE over K boundaries, with K fixed before reading. No fitness/archive/baseline/promotion
      effect without a separately approved protocol. It is also the atypical-observation probe
      (intake-1379#record). intake-1378#record.

      **Source-only partial, 2026-11-01:** Default-off AP-70 rotation-boundary instrumentation and
      its identity/refusal contracts are published in epyc-orchestrator `a464a03eca67d78b55f40d2a49eae8c09188226e`; [source evidence](https://github.com/pestopoppa/epyc-orchestrator/tree/29fdfc5a7cc229f1dcafee327f193b1623de0d32/artifacts/ap70-source-partial-20261101). Hosted run `41292163512` passed 50 source-contract tests. This remains source-only: no native K-boundary/model run, live AutoPilot or API reload, belief ingestion, or measured quality-drop/generalization conclusion. The observer is opt-in and prompt-incumbent scoped; unavailable, drifting, or unsupported identity is incomplete, and a model path hash does not authenticate model contents. No historical trial is backfilled. AP-70 stays open for prospective native readout and belief-reader/canary work. [no-belief: source implementation only; no new measurement]

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


##### Research Intake Update — 2026-09-25 (DGM, program search, and autonomous science)

- [ ] **AP-DGM-PROV — Freeze the shared EPYC selector-replay package.** Snapshot the existing AutoPilot journals, candidate graph or cached proposals, task order, candidate and outcome bytes, incumbent policy, selector/scorer revisions, archive and endpoint tie-breaks, budgets, model/decoding identity, and time/task holdout. Record immutable manifest and artifact digests and write through `VB-DGM-1`; do not fetch or recreate the external DGM benchmark for this phase. The package is the one input consumed by `SEQ-SHINKA-1` and `AP-DGM-SEL`. Sources: intake-1625#record, intake-1638#record, intake-1663#record, intake-1684#record, intake-1685#record, intake-1686#record.
  - **Implementation checkpoint 2026-09-26:** root commits `37e74b28`, `f434bad5`, and `e8ca0811` add the immutable freezer, historical audit, deterministic fixture, strict `VB-DGM-1` receipts, and belief-kernel projection. The audit froze both complete journal shards at SHA-256 `1c5a665922de5c81c53cc6dd4218a9597123c1a1d42347344104683758f70dbc` and `9f9fd39b8ed1db90b073782b9fe4c57a368b6c6e9c9bef6d4819b4b98aec408a`; it verified 393 sequential rows, 141 candidate IDs, 30,240 question outcomes, and all 22 parent pointers outside the sequential subset. The task remains open because the source bytes do not contain the original eligible menus, resolved model/decoding identity, selector revision/tie-break record, predeclared holdout, or paired same-task/seed/evaluator outcomes for unchosen parents. The sealed audit and twelve-row missing-field receipt are under `/mnt/raid0/llm/artifacts/ri9-selector-replay-20260926/historical-final/` with disposition `not_evaluable`; no derived menu or holdout was promoted to observed evidence. Completion now requires prospective write-side capture during a model-producing campaign.
  - **2026-11-09 next-action rewrite (RTG-02 audit, verified against code):** there is no selector menu to capture today. The live parent choice is `select_lineage_parent` (`experiment_journal.py:607`, rule `latest_committed_baseline_promotion_same_species`), a deterministic latest-same-species rule called at `autopilot.py:11411`; it never builds or logs a set of eligible parents, and the orchestrator has zero write-side fields for eligible menu, `decoding_id` or holdout. "Prospective capture" therefore has no implementation target yet. The immediate step is the design decision below, not a run. Replay of the existing 393-row record stays `not_evaluable` (see AP-DGM-PROV checkpoint).
  - **Decision needed (where the menu lives):** (A) log the candidate set the existing rule already implicitly ranks (all committed baseline promotions of the same species) as an observe-only `eligible_parents` field on each journal row, with `decoding_id`/holdout tag; zero behaviour change, smallest, but the menu is a derived set rather than a real choice. (B) make `select_lineage_parent` a real stochastic/ranked selector over an explicit pool (sequential-resume candidate pool plus same-species promotions), logging the pool, scores and RNG seed; this is the only option under which DGM/Shinka/HGM comparisons are about real decisions, but it changes loop behaviour and needs its own gate. (C) capture planner proposals as the menu; richest but couples to the planner roster and cost. **Recommendation: A first (observe-only, shipped before the first model-producing run so the new era produces evaluable rows), then B only if the replay on A-rows shows the incumbent rule is a measurable bottleneck.**

- [ ] **AP-DGM-SEL — Add DGM/HGM formulas to the shared selector replay after `SEQ-SHINKA-1`.** Reuse the exact frozen package, current-policy and score-only controls, holdout, raw per-decision outputs, complete invalid/failure/abstention denominator, and `VB-DGM-1` receipt. Vary only `{DGM transformed-score × inverse-valid-child, HGM clade/CMP}` after predeclaring cold-start semantics. Report parent-choice agreement, held-out continuation, time-split/bootstrap stability, and paired lineage outcomes. Stop if alternative policies choose the same parent on at least 95% of eligible decisions, differ without improving held-out continuation, or reverse across holdouts. A stable gain permits one bounded live paired follow-up; it grants no restart, policy switch, or production authority. Sources: intake-772#record, intake-1626#record, intake-1639#record, intake-1640#record, intake-1661#record.
  - **Implementation checkpoint 2026-09-26:** the same root commits implement source-parameterized DGM weights and seeded HGM Beta Thompson sampling with explicit validity, prior, pseudo-descendant, cold-start, tie, and RNG semantics. The runner retains every invalid/failure/abstention, reports choice agreement, paired held-out and lineage outcomes, chronological blocks, cluster bootstrap stability, and the predeclared stop rules. Twenty-nine focused tests pass, including future-leak, derived-menu, missing-counterfactual, digest-tamper, and incomplete-holdout refusals. Synthetic results are conformance-only under `/mnt/raid0/llm/artifacts/ri9-selector-replay-20260926/fixture-results-acceptance/`; the historical effect screen remains open and inference-gated by the missing prospective fields recorded under `AP-DGM-PROV`.
  - **2026-11-09 (RTG-02 audit):** blocked on the AP-DGM-PROV decision above (no selector menu exists to capture; inference is not the first blocker). The "ALE trigger" is defined in the dormant `AP-RI-ALE-1` record: a stable held-out gain by this screen or AP-DGM-SEL.

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


#### Nested open decisions retained during compaction

- [x] **OPERATOR: install the two declared deps into the live orchestrator `.venv`.** The ✅ 2026-10-29 (audit: epyc-orchestrator/.venv site-packages has onnxruntime-1.26.0 and tokenizers-0.22.2 installed (checked 2026-10-29); handoff:836 notes fa3daeac declared at pyproject.toml:43 + tests/unit/test_retrieval_deps.py) [no-belief: audit-reconciliation]
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

- [x] ~~**PRE-EXISTING: `eval_tower` and the seeding path DISAGREE about a `task_failure`, so the same~~ (closed 2026-10-29 audit: SUPERSEDED → AP-64 (handoff:726) explicitly "Closes the PRE-EXISTING eval_tower vs seeding disagree row" and carries the OP-20 ruling; AP-64 itself still open (no commit found))
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

#### Historical siblings

- [Historical ledger through 2026-06-20](../completed/autopilot-continuous-optimization-history-through-2026-06-20.md)
- [Historical ledger, 2026-06-21 through 2026-09-25](../completed/autopilot-continuous-optimization-history-2026-06-21-through-2026-09-25.md)

2026-10-06 MAIN acceptance: residual programmatic input-echo guard source completed with all23 original compatibility/refusal controls and APP byte-identical publication; [scope](../../artifacts/ni08/rtg02-echo-source-20261006/README.md). Live pool rebuild and alternative-repair measurement remain open.

##### Research scorer historical reconciliation — 2026-10-31

The argumentized entry-point implementation landed in orchestrator `07a20a7cface6614c595f42981e385ae3695ee42` on July 20; research replaced its diverged scorer with a fail-closed delegation shim in `d876adfef50912cdeaad14b34d416dc9608479d9` on August 23. The existing checkbox now carries the actual completion date and implementing commits. This is historical queue hygiene and earns no October 31 code completion credit; no historical result was rescored. Audit and test paths are preserved in research `f6630e61058c0ebebaa0467e70cedead8c4081da`. [no-belief: historical software-source reconciliation]

#### Typed decisions from intake-2604 (ws58 intake 2026-11-02; operator approved "Approve, go to Stage 4", D9 acknowledged for scripts/coordination)

Plan: [README.md](../../research/deep-dives/ws58-jev-20261102/README.md). **Order (operator, 2026-11-02):** (1) SA-1 + JEV-1; (2) SA-2, SA-3, JEV-3; (3) JEV-5 phase A, KT-1, KT-3; (4) the rest (JEV-2, JEV-4, JEV-6, SA-4, KT-2, KT-4, KT-5). JEV-5 phases B/C only after the operator has used phase A.

- [x] **JEV-1** ✅ 2026-11-02 epyc-orchestrator `26752665` [belief: cc] [S] `epyc-orchestrator orchestration/repl_memory/q_judge.py:153-161`: timeout, exception or unparseable output returns `(None, "unavailable")` instead of `SCORE: 1`; callers count unavailable separately; regression test (intake-2604#record). removes: the fail-open synthetic `SCORE: 1` strings and the parse default that reads an unanswered judge as a low score.
- [x] **JEV-2** ✅ 2026-11-02 epyc-orchestrator `488b31c9` [belief: cc] [M] `_classify_meta_halt` (`scripts/autopilot/autopilot.py:8293`) — landed as a deterministic rule (no typed_decisions call needed): a named StopReason enum plus a MetaHaltRecord and a `judge_state` (asked / not asked / unavailable) journal field; no shadow accuracy study. removes: the reproduction-count heuristic and the unnamed halt counter (`autopilot.py:10399`).

## Track: autopilot-dashboard-fidelity-audit-2026-07-22
<!-- gate: none -->

> Folded from `handoffs/active/autopilot-dashboard-fidelity-audit-2026-07-22.md` @ `b1bf3f3f7ade` on 2026-11-02 (BRF-T1-F20, route 1a, operator D1/D5; retired row RTG-03 → RTG-02). Body moved verbatim, headings demoted two levels to nest under this track; every open and closed box kept its text and ID.

### Autopilot / Orchestrator Dashboard Fidelity Audit — 2026-07-22

**Commission**: Operator, 2026-07-22. Read-only audit. Hypothesis under test (operator, verbatim):
the dashboard must be "properly wired to capture and faithfully display the fixes we've been
implementing" and "since it was built on top of flawed infra, it is probably flawed itself."

**Scope**: `src/api/routes/dashboard*.py` + the single static frontend `dashboard.html`
(served by `GET /dashboard`). No scripts/ dashboard server exists (only stack-management tools).
The epyc-root handoff-kanban hub on :8100 is out of scope (confirmed a distinct `service` node).

**Method / constraints honored**: read-only. 5 GET requests issued to `localhost:8000` dashboard
endpoints (topology×2, region_locks, contention; one snapshot attempt refused during a stack
handover). NO llama-server traffic (the `/topology` and `/region_locks` builders are `/proc`-scan
only — verified network-free; `/snapshot` and `/health` fan out to llama `/slots`/probes and were
deliberately NOT driven). No inference, no POSTs, no edits. EV-11c left undisturbed.
Mid-edit files (`scripts/server/*`, `src/config/models.py`, `src/registry/stack_priors.py`)
read from committed HEAD.

---

#### Executive summary

**The hypothesis is confirmed.** The dashboard inherits the data plane's central defect: it does
not read a single realized source of truth for fleet state. Its correctness is *coincidental* —
it depends on a launch-time environment variable (`ORCHESTRATOR_STACK_NUMA_MODE`) happening to
match the realized fleet.

The capstone proof, captured live on the same quarters-only fleet:

- **GET #1 `/dashboard/api/topology`** (routed to a uvicorn worker whose env was `full`) rendered
  `stack_numa_mode="full"`, flagged **all 12 live quarter servers `expected=False`** (i.e. rogue),
  and flagged **the 3 dead full ports (8070/8072/8085) as `expected-stack-server, running=False,
  expected=True`** (i.e. missing/down). This is a **fully inverted fleet-health picture**: the
  correct fleet reads as broken, and the intentionally-absent full servers read as expected.
- **GET #5 `/dashboard/api/topology`** minutes later (after a stack relaunch to an env=`quarter`
  master) rendered `stack_numa_mode="quarter"`, `0` rogue quarters, `0` missing fulls — **correct**.

Same realized fleet both times (12 quarters live, 3 fulls dead, verified by `ps`). The only thing
that changed was which launch env the serving worker inherited. The dashboard already computes the
realized fleet (`_discover_llama_ports()` — a `ps`/`/proc` scan) and uses it for the node list, but
it does **not** use it to derive `stack_numa_mode` or the `expected` flags. Those come from the env.

**Root cause (cross-cutting, defect-signature "duplicated state without a single SoT")**: the API
runs `uvicorn --workers 6`, and during the audit **three concurrent/successive worker pools carried
divergent env** — `ORCHESTRATOR_STACK_NUMA_MODE=full` (master 1778291), `=quarter` (master
1851981), and `UNSET` (worker 1854520). `active_stack_numa_mode()` therefore returns **full /
quarter / both** depending on which worker the load balancer picks. Two dashboard panels sampled
seconds apart genuinely disagreed: `/topology`→`full`, `/region_locks`→`quarter`. The
"coherent-snapshot" fix guarantees coherence *within* a worker; it provides none *across* the pool.

Every field sourced from per-process state inherits this fragmentation: contention-gate counters,
per-role scheduling, migration counters, and circuit-breaker state are all per-worker singletons and
show a 1-of-6 fragment (or empty) with no worker provenance. Fields sourced from the shared
filesystem/`/proc` (region-lock held-state, the rotating journal, the topology node list) are NOT
fragmented — which is exactly why those panels are the trustworthy ones.

Three fixes are faithfully wired (journal rotation, era-labeling, region-precise held-state).
Three states the recent fixes made honest are **blind spots** the dashboard never surfaces at all:
REL-1 eval error-rate, calibration/confidence provenance, and circuit-breaker/forced-role-fallback
events — the last being precisely the EV-11c incident class.

---

#### Fix-inventory fidelity table

| # | Fixed data-plane state | Dashboard verdict | Read path (file:line) | Proof |
|---|---|---|---|---|
| 1 | Topology / NUMA mode (env-first vs realized fleet) | **READS LYING SOURCE** (env-first; correctness coincidental) | `dashboard_topology.py:140` (env short-circuits before the hardened manifest reader `:150`); mode consumed at `dashboard.py:4839`, `:4636` (`expected_stack_services(mode)`), `:5131` | GET#1 env=full → inverted; GET#5 env=quarter → correct; same fleet |
| 2 | Placement / holder truth (`held_regions_by_role` exact sets) | **READS CORRECTED SOURCE** for held-state; **duplicated + partial** | region grid re-derives from `/proc/locks` via `_current_lock_owner_pids` inline `dashboard.py:998-1029`; never calls `cpu_region_lock.held_regions_by_role()` (`:419`) | GET#2 region-precise; `launch_selected` inherits Fix-1 inversion; eval lane (18072) bypasses locks |
| 3 | Error honesty REL-1 (excluded-error vs scored-wrong) | **BLIND SPOT** | REL-1 lives in `scripts/autopilot/eval_tower.py`; **no** dashboard route reads eval-tower/eval-batch reports | grep: no `eval_tower`/`excluded_error`/error-rate read in any route |
| 4 | Era awareness (E7 priors) | **READS CORRECTED SOURCE** | `_autopilot_era_regions()` `dashboard.py:2317`, applied in pareto `:4011`; KPIs `current_run_only=True` `:3393` | pareto "all_eras" era-labeled + speed-deinflated; default = current era |
| 5 | Calibration provenance (`confidence_is_real`) | **BLIND SPOT** | `confidence_is_real` only in `src/autopilot_core/rlvr_tiers.py`, `scripts/autopilot/eval_tower.py`; **no** route/HTML reference | grep: 0 hits for calibration/ECE/`confidence_is_real` in routes or `dashboard.html` |
| 6 | Circuit breakers / forced-role fallback | **BLIND SPOT** (+ fragmented where it exists) | breaker state only at `src/api/routes/health.py:224` (per-process `health_tracker`); `dashboard.html` never fetches `/health`; `forced_role_fallback` unsurfaced | grep of `dashboard.html` fetch list: no `/health`, no breaker/fallback panel |
| 7 | Journal rotation (numbered shards) | **READS CORRECTED SOURCE** | `_autopilot_journal_shards()` `dashboard.py:2390` + `_read_autopilot_journal_rows()` `:2425` read base + all `_<n>.jsonl` | rotated `autopilot_journal_1.jsonl` present on disk and included |
| 8 | Freshness contract (envelope + coherent snapshot) | **IMPLEMENTED but INSUFFICIENT** | `dashboard_freshness.py` classify/envelope/stamp; `value_consistency` used only at `dashboard.py:4324` | age-only; no value-consistency reconciles declared-mode vs realized fleet; coherence is intra-worker only |

---

#### Findings by severity

##### CRITICAL

**C1 — NUMA-mode / fleet-health inversion driven by launch env, non-deterministic across the
worker pool.** `active_stack_numa_mode()` (`dashboard_topology.py:122`) returns the value of
`ORCHESTRATOR_STACK_NUMA_MODE` *first* (line 140), before the hardened fail-closed manifest reader
(line 150, commit 22e32ec2) it was supposed to gate on. The live fleet is quarters-only (12 quarter
llama-servers; full ports 8070/8072/8085 dead — `worker_general` is even `placement_policy:
full_disabled`). When a serving worker's env is `full`, `expected_stack_services("full")` keeps only
the full instances (`stack_manifest._filter_by_numa_mode`), so in `_build_topology_nodes`
(`dashboard.py:4636`) the **live quarters get `expected=False` and the dead fulls become
`expected-stack-server` down rows** — the operator sees the healthy fleet as rogue and the absent
fulls as missing. Proven live: GET#1 (env=full) inverted; GET#5 (env=quarter) correct.

Two compounding causes make this un-self-correcting:
1. **Worker-pool env divergence.** `ps` + `/proc/<pid>/environ` showed concurrent masters/workers
   with `full`, `quarter`, and `UNSET`. `--workers 6` means a given poll hits a random worker, so
   `stack_numa_mode` can read `full` on one 5 s poll and `quarter` on the next.
2. **The intended fix is itself unusable.** The runtime-facts manifest
   (`/mnt/raid0/llm/tmp/orchestrator_runtime_facts.json`, written 09:08:44Z) carries the correct
   `runtime_stack.stack_numa_mode="quarter"` but `selected_servers=[]` / `selected_ports=[]`. The
   fail-closed guard (`_fail_closed_runtime_stack_numa_mode`, requires a non-empty lineup) correctly
   rejects it → returns `None` → falls to the env/`both` default. So even removing the env would
   yield `both`, not `quarter`. The launcher wrote the mode but not the lineup — an
   *intent-not-realized writer*.

The single authoritative source — the realized fleet from `_discover_llama_ports()` — is already
computed for the node list but is not used to derive the mode or the `expected` flags.

##### HIGH

**H1 — Circuit-breaker and forced-role-fallback state is a dashboard blind spot (EV-11c incident
class).** The EV-11c incident was *caused* by breakers tripping (deadline-starved 1 s calls) and the
orchestrator silently role-falling-back worker_math→worker_general 90×. Breaker state exists only at
`GET /health` (`routes/health.py:224`, per-process `health_tracker`, and it actively probes
llama-servers). `dashboard.html` never fetches `/health`; no panel surfaces breaker state or
`forced_role_fallback` churn. During exactly the incident the fixes were built for, the dashboard is
dark.

**H2 — REL-1 eval error-rate / reliability is a blind spot.** The REL-1 honesty guards (in-band
`[ERROR:` detection, forced-role integrity, error-row exclusion) live in the eval harness
(`scripts/autopilot/eval_tower.py`, `seeding_*.py`) and are written into eval reports. No dashboard
route reads eval-tower/eval-batch reports; nothing surfaces excluded-error rows vs wrong answers or
an error/reliability rate. The pareto/optimization "reliability" objective is autopilot
*trial-outcome* reliability, not eval error classification — the two must not be conflated by a
reader.

**H3 — Contention / scheduling panel shows a per-worker fragment as fleet truth.**
`contention.metrics_snapshot()` returns in-process `ContentionGate` singleton counters
(`contention_gate.py:439`, singleton `:461`). With `--workers 6`, `active_decodes_by_role`,
`contention_admitted_count`, blocked/wait counts reflect only the answering worker.
`per_role_scheduling` reads the per-process `_real_primitives._backends` and came back **empty** at
GET#3. Migration counters are likewise per-worker. No worker provenance is attached, and the
endpoint docstring mislabels the source as "from region-lock holders" (it is not — it is an
in-process counter). Numbers displayed without provenance; systematic undercount.

**H4 — Cross-worker snapshot incoherence.** The freshness/coherent-snapshot machinery guarantees one
`generated_at` *within* a worker's build, but different workers (divergent env, divergent in-process
counters) produce mutually inconsistent frames. `/topology`=`full` beside `/region_locks`=`quarter`
was observed. The "one coherent snapshot" contract does not hold across the 6-worker pool.

##### MEDIUM

**M1 — region_locks re-implements the held-set SoT instead of calling it.** The grid re-derives
holders from `/proc/locks` inline (`dashboard.py:998-1029`) rather than calling
`cpu_region_lock.held_regions_by_role()` (`:419`). Functionally region-precise today (same
`_current_lock_owner_pids` primitive, so it is NOT the over-reporting `active_region_holders` view —
good), but it is duplicated logic that can drift from the placement plane's SoT.

**M2 — `launch_selected` grid annotation inherits the Fix-1 inversion.** When env=`full`, the
region-lock display marks the dead full instance `launch_selected=True` and the live quarters
`launch_selected=False` (with a "not selected by stack_numa_mode=full" tooltip), i.e. the same
inverted selection story as C1. Held-state cells remain correct; the selection overlay is wrong.

**M3 — The active eval-batch serving lane is unattributed and lock-invisible.** EV-11c serves on
port 18072 (3 procs, `-np 14`), which renders as `extern_18072 / external-llama-server /
expected=False` and takes no interactive CPU region lock — so a live 4-wide eval shows `0` held
regions and `active_decodes_by_role: {}`. Faithful *for the interactive lane*, but the operator
watching a running eval sees no activity attributable to it.

**M4 — Calibration provenance has no plumbing.** `confidence_is_real` never reaches a dashboard
surface. Today that is a pure blind spot (calibration/ECE simply isn't shown); it becomes a
misdisplay risk the moment any panel starts showing confidence without carrying the flag.

##### LOW

**L1 — Journal concatenation is not era-sliced.** `_read_autopilot_journal_rows()` concatenates all
shards (Jun-27 base run + Jul-16 `_1` run) with no era filter. Quality-gating views are era-aware
(pareto era-labeling; KPIs `current_run_only`), but a current run that *straddles* the E7 boundary
(run start Jul-16 vs E7 ~Jul-18/20) could blend pre/post-E7 quality inside a single "current"
window. Low impact because the era-labeled pareto is the decision surface.

**L2 — Warm-only servers marked `expected` in `full` mode.** `worker_fast` (8102) and
`eval_batch_frontdoor` (18070) show `expected-stack-server / expected=True / running=False`; they are
warm/explicit-only and not normally launched, so "expected down" slightly overstates a problem.

##### No finding

**Fix 7 (journal rotation)** — clean. All shards read, freshness keyed to newest shard by mtime.

---

#### Prioritized fix list (file:line targets)

1. **[C1] Derive NUMA mode and `expected` from the realized fleet, not the env.** In
   `dashboard_topology.py:active_stack_numa_mode()` (122) and `expected_stack_services()` (461),
   demote `ORCHESTRATOR_STACK_NUMA_MODE` below a realized-fleet check built on the port set already
   returned by `_discover_llama_ports()` (347). A port that is live is `expected`; a configured-but-
   dead full is `absent-by-policy`, not `missing`. Treat the env as a spawn-time hint only.
2. **[C1] Repair the manifest writer's intent-not-realized gap.** The launcher must write
   `runtime_stack.selected_servers` / `selected_ports` alongside `stack_numa_mode`, so the hardened
   reader (`_fail_closed_runtime_stack_numa_mode`, `:150`) has a lineup to accept. (Writer lives in
   `scripts/server/runtime_facts_manifest.py`.)
3. **[C1/H4] Give the worker pool one env / one SoT.** Ensure all `uvicorn --workers 6` workers
   inherit an identical `ORCHESTRATOR_STACK_NUMA_MODE` (or, preferably per #1, none — read the
   realized fleet). Add a value-consistency check (reuse `dashboard_freshness.value_consistency`)
   that reconciles declared mode vs realized fleet and badges the topology panel when they diverge.
4. **[H1] Add a breaker/fallback panel.** Surface `health_tracker.get_status()` per endpoint URL and
   a `forced_role_fallback` event feed on the dashboard; key it to the realized fleet, not a role's
   private URL copy. Make it multi-worker-aware (aggregate or label the worker).
5. **[H2] Surface REL-1 eval error-rate.** Add a reader for the latest eval-tower/eval-batch report
   that displays excluded-error rows distinctly from wrong answers, plus an error/reliability rate.
6. **[H3] Fix contention-panel provenance.** Either aggregate the per-worker gate counters into a
   shared store, or label each reading with its worker PID and stop presenting it as fleet-wide;
   correct the endpoint docstring (`dashboard.py:635`) that claims "from region-lock holders".
7. **[M1] Replace the inline held-set derivation** (`dashboard.py:998-1029`) with a call to
   `cpu_region_lock.held_regions_by_role()` so the panel and the placement plane share one SoT.
8. **[M2] Recompute `launch_selected`** from the realized fleet once #1 lands (falls out for free).
9. **[M3] Attribute the eval-batch lane** (18072) to its role in `_discover_llama_ports`/port hints.
10. **[L1] Era-slice the KPI window**, not just the run window, when a run straddles an era boundary.

---

#### Evidence appendix (live captures)

- Realized fleet (`ps`, quarters-only): live `8080/8180/8280/8380` (frontdoor q0-3),
  `8082/8182/8282/8382` (worker_general q0-3), `8185/8285/8385/8485` (ingest q0-3), `8083`
  (architect), `8086/8087` (vision), `8090-8095` (embedders); **dead**: `8070`, `8072`, `8085`.
- Worker env divergence: PID 1778291=`full`, PID 1851981=`quarter`, PID 1854520=`UNSET`.
- Manifest `/mnt/raid0/llm/tmp/orchestrator_runtime_facts.json` @09:08:44Z:
  `runtime_stack.stack_numa_mode="quarter"`, `selected_servers=[]`, `selected_ports=[]`.
- GET#1 `/topology` (env=full worker): `stack_numa_mode=full`; frontdoor.q0-3 / worker_general.q0-3
  / ingest.q0-3 all `expected=False`; 8070/8072/8085 `expected-stack-server, running=False`.
- GET#5 `/topology` (env=quarter worker): `stack_numa_mode=quarter`; 0 rogue quarters, 0 missing
  fulls.
- GET#2 `/region_locks`: `stack_numa_mode=quarter`, quarters `launch_selected=True`, full
  `launch_selected=False`; 0 regions held (interactive lane idle; EV-11c on the 18072 eval lane).
- GET#3 `/contention`: `active_decodes_by_role={}`, `contention_admitted_count=0`,
  `per_role_scheduling=[]` (per-worker fragment).

---

#### Implementation record

**2026-07-22 — C1 + M2 landed** (`epyc-orchestrator@e97d4ed9`, branch
`spec-dec-mtp-refresh-2026-06-22`; owned dashboard route/template files + tests only).

- [x] **[C1] Realized-fleet-first NUMA-mode resolution** ✅ 2026-07-22 —
  `dashboard_topology.active_stack_numa_mode()` reworked to resolve
  **realized live fleet (bare-TCP probe via `scripts.server.realized_fleet.derive_realized_numa_mode`) > hardened runtime-facts manifest > `ORCHESTRATOR_STACK_NUMA_MODE` env hint > `both` default**. The env is
  demoted to a last-resort spawn-time hint, so a worker that inherited `full`
  can no longer invert a quarters-only fleet. New `active_stack_numa_mode_resolution()`
  returns provenance (`mode`/`source`/`realized`/`manifest`/`env`/`disagreements`).
- [x] **[C1] Realized probe runs in-process at request time, TTL-cached** ✅ 2026-07-22 —
  `_probe_realized_numa_mode()` (isolated seam) + `_cached_realized_numa_mode()` with
  a ~5s TTL so 2 Hz × 6-worker polling collapses to one probe. Fully fail-safe
  (any error → `None` → falls through to manifest/env/default).
- [x] **[C1/H4] Visible provenance annotation** ✅ 2026-07-22 — `stack_numa_mode_provenance`
  added to the `/topology`, `/region_locks`, and coherent `snapshot` payloads;
  `dashboard.html` renders a topology mode badge that goes amber and shows
  "env disagrees: full" when a lower-precedence source contradicts the realized fleet.
- [x] **[M2] `expected`/rogue + `launch_selected` inversion fixed** ✅ 2026-07-22 —
  both derive from the realized-first mode (fell out of C1): live quarters read
  `expected=True`, dead fulls are absent-by-policy, never surfaced as
  `expected-stack-server` down rows. Guarded by a 12-quarter + env=full inversion
  regression test.
- [x] **Tests** ✅ 2026-07-22 — realized-over-env, inversion regression,
  manifest-beats-env, manifest-rejected fallback ordering, TTL-cache probe-storm
  collapse, provenance badge (route-HTML). Existing dashboard suites kept green
  (realized probe neutralized in their fixtures). Two `test_dashboard_helpers`
  failures remain (`test_port_hints_follow_current_full_mode_priors`,
  `test_topology_activity_initializes_expected_embedder_bucket`) — **pre-existing
  and environmental** (they read the live host's empty `selected_servers` manifest;
  both fail identically on clean HEAD, unrelated to this change).

**Not done (deferred, still open):**

- [ ] **[C1 fix #2] Manifest writer intent-not-realized gap** — writer lives in
  `scripts/server/runtime_facts_manifest.py` (other-agent ownership); ESC-8 fixes
  already rewrote the writer to derive `selected_servers` from realized state, but
  the live manifest still shows an empty lineup — verify separately.
  **2026-08-11 (`mainB`) — screened, NOT actionable as written: the observation is CONFOUNDED and
  must not be "fixed".** `/mnt/raid0/llm/tmp/orchestrator_runtime_facts.json` (generated
  `2026-08-11T08:19:56Z`) does carry `selected_servers: None` — but **the stack is down**: nothing
  is listening on 8070/8072/8085/8080/8180 (checked). A writer that derives from *realized* state
  is **supposed** to emit an empty lineup when nothing is realized, so an empty manifest is
  evidence the ESC-8 rewrite WORKS, not that it failed. The row was filed while a lineup was
  presumably up, and re-reading it against a down stack inverts its meaning.
  Distinguishing "writer broken" from "nothing running" requires a live stack, i.e. **compute** —
  `inference`-owned, not this lane. Leaving the box open and untouched; re-verify during the
  P0-0 relaunch window, when a realized lineup exists to compare against.
  Related trap already recorded at P0-0 (`numa-topology-cutover-resume-20260730.md`): the derived
  priors are likewise a faithful record of a halves-only launch, not a corrupted file.
- [ ] **[C1 fix #3] One env / one SoT across the `--workers 6` pool** — process/launch
  concern (`scripts/server/*`), out of dashboard-file ownership.
- [x] **[E8-PANELS] Era-honest pareto/GEPA plots for E8** ✅ 2026-07-27 — implemented in
  orchestrator `64c05ca7` (7 files, +828/−48, 285 focused tests green), converging with
  Codex's independent region-lock membership fix (22:17 same night). Delivered: (A) E8 era
  pickup pinned by test against the live registry; (B) per-point `historical_instrument`
  labeling, faded historical series, E8 boundary annotation (label-never-rescale); (C) GEPA
  no-op provenance window 2026-06-04→`ed6288ea` hatched + caveat badge; (D) ALL live
  instances render in the region-lock panel with "n/a (no lock domain)"; (E — scope-extended)
  authority banner reads live holds ("quality: HELD pending E8 baseline; speed: pending E8
  numeric rerun N/16"); `decision_grade_possible=False` while any hold is open. Python-side
  takes effect at the deferred API reload (reseed trial boundary); HTML live on refresh.
  - [x] **[E8-PANELS-a] Reconcile the rerun counter fields** ✅ 2026-08-11 (`mainB`,
    `epyc-orchestrator` `98ed5c5f`): banner showed the gate marker's
    `frontier_rerun_required` count (0/16) while `frontier_rerun_pending_clear` carried the
    live 15/16 — unify which field the gate updates mid-run (cosmetic, confusing).
    **Root cause, and it was not cosmetic in the way the row assumed.** `completed_numeric_trials`
    was written onto the marker ONLY by `_clear_frontier_rerun_marker` — i.e. once the gate had
    already been satisfied. While the marker was OPEN it kept its creation value, `0`, even though
    the live count is recomputed from the journal every decision cycle and reached only the
    rationale. So it was not two fields disagreeing; it was **one field nothing updated mid-run**,
    read by three surfaces that each coped differently.
    Fix: the gate now writes `completed_numeric_trials` / `min_numeric_trials` back onto the open
    marker each cycle, and `gen_system_card` renders them as `[15/16]`.
    `optimization_brief.py:188` needed **no change** — it was already reading the right field.
    **Reporting only, deliberately.** Nothing gates on the number: the decision path uses the
    freshly computed local and `speed_hold` keys off `required`. A test pins that a missing or zero
    count still HOLDS the gate — the failure mode worth guarding against is a "cosmetic" fix that
    quietly wires a fail-closed hold to a display field. Skipped when `journal is None`, where the
    counter returns 0 and writing it would recreate the bug from the other direction.
    5 new tests; 719 passed across the autopilot/brief/system-card consumers (the 4 failures are the
    known pre-existing set: 3× P0-0, 1× the E8 v8 pin).
  - [x] **[E8-PANELS-b] Commit the ratified era-registry row**: an uncommitted `eval_quality`
    E8 row sits in `orchestration/instrument_eras.yaml` (output of the operator's quality-fence
    transaction; human-amendment provenance) — commit it with its receipt reference.
    **✅ 2026-08-12 (`mainA`, pulled from the generated bench and claimed) — the row IS committed;
    the premise was stale. But it landed WITHOUT its receipt reference, which is the half worth
    recording.**
    Verified against git, not the filesystem: the `eval_quality` E8 row is at
    `instrument_eras.yaml:170-176` on `HEAD` and has been committed since **`e2e5c035`
    (2026-07-27)** — so "an uncommitted E8 row sits in ..." has not been true for two weeks.
    **The provenance gap is real.** `e2e5c035`'s subject is *"fix: scope E8 candidate collection
    watcher"* and its body carries no receipt reference, so an operator-ratified trust-boundary
    row rode into the repo inside a bugfix commit. Anyone tracing that row's authority through
    `git log` lands on a watcher fix. The receipt does exist and matches:
    `artifacts/operator/ratify_e8_autopilot_quality_fence_20260726.json`, decision
    `RATIFY-E8-AUTOPILOT-QUALITY-FENCE`, ratified 2026-07-26T12:15:03Z, carrying
    `quality_era: {id: E8, scope: eval_quality, from: 2026-07-25T18:38:43Z}` — identical to the
    committed row.
    **I did NOT mint a receipt-index entry for it.** Ran
    `scripts/operator/check_ratifier_receipt_contract.sh` first: it reports *"on-disk ratified
    receipts lacking a keyed index: (none)"*, because the fence is satisfied by its own
    basename receipt under the contract's explicit guard. Creating an index entry would have
    manufactured an evidentiary artifact the contract does not ask for — and I would have done it
    on assumption rather than on the contract.
    **Separate live finding, NOT mine, filed on the bus:** that same checker **exits 1 today** —
    `MISSING-WRITE: ratify_and_apply_e8_quality_baseline_v4_20260727.sh (token=
    ATTEST-E8-CONTEXT-FEASIBILITY-AND-BASELINE-APPLY-20260727)`. A signable token script with no
    keyed-receipt write, i.e. a gate that could be signed without leaving an index entry. Routed
    to the E8 quality-baseline owner.
  - [x] **[E8-PANELS-c] Hub pct presentation** ✅ 2026-08-12 (`mainB`) — `pct_all_done` reads intake
    sweeps as decline (denominator inflation, see 2026-07-27 forensics) — surface absolute
    `all_tasks_done` + a newly-filed-tasks series on the :8100 hub (owner may also be
    loops-and-dashboards-audit-2026-07-05.md).
    **Both requested surfaces ALREADY EXISTED; the defect left was the guard protecting them.**
    Absolute: `handoffs.html:620` renders `bk.all_tasks_done` ("tasks completed (all tracked)").
    Newly-filed series: `:943` and `:994-995` (`newly_filed` / `tasks_newly_filed`, each falling
    back to `opened`). The percentage was *kept* rather than removed — a later design decision,
    commented in place — but scope-labelled, "% done · open scope" beside "% done · all scope",
    which addresses the same confusion by disambiguation instead of deletion.
    **What was actually broken: the frontend-contract test asserted a SPELLING, not a property.**
    `tests/test_handoff_parser.py` carried
    `assertNotIn("const pctAll = bk.pct_all_done", html)` — and that exact expression exists nowhere
    in the file, so the guard passed while `bk.pct_all_done` was still rendered through a different
    expression at `:704-705`. A guard that forbids one *way of writing* a thing does not forbid the
    thing. Rewritten to assert the property: if `bk.pct_all_done` is rendered at all, it must carry
    its scope label AND appear beside the open-scope figure.
    **Mutation-checked, because a guard I cannot make fail is the defect I was removing:** stripping
    the two scope labels while leaving the render in place makes the new assertion FAIL
    (`'% done · all scope' not found`); the old one passed on that same mutation. Restored, 42/42
    green.
- [x] **[E8-TRIALS-COLD] Validate restart-surface trial speed samples for cold-start
  contamination** ✅ 2026-07-27. Retrospective row-level audit cleared the sealed E8
  frontier: restart attempts 1442/1455 were tier-0 skips because AP-3 restart was disabled,
  so neither relaunched a role; trials 1443/1445/1453 each recorded all 65
  `cache_warm_state=warm` covariates. Only warm trial 1445 entered the sealed frontier
  (`[1445, 1446, 1450]`) and supplied its speed maximum. The terminalizer itself did not
  enforce or attest this predicate. Original concern: `spec_decode_role_restart` trials
  relaunch servers and may sample speed un-prewarmed (guardrail: cold-start collapses to
  24-35 t/s vs 55-70 warm; live tap showed worker at 18.3 t/s ~1 min post-restart; trials
  1443/1445/1453 logged s=8.4/9.7/4.4). Owner overlap: autopilot-decision-plane-audit §E8
  RE-ARM; filed here because the evidence surfaced via the dashboard tap. The E8 reseed's honest-instrument trials (q≈1.71–1.77) plot
  against pre-E8 points measured on the laxer instrument (q≈1.85–2.04 plateau), inviting a
  false regression read. The pareto panel's era machinery exists (`_autopilot_era_regions()`
  `dashboard.py:2317`, applied `:4011`, default=current era) but was certified for E7 — verify
  and fix three things: (a) era regions derive from the LIVE sources (`instrument_eras.yaml`
  E8 rows appended 2026-07-26 + `pareto_epoch_ts=1785004723` = the E8 fence), not hardcoded
  E7 boundaries — E8 trials must render as the current-era series with the boundary line
  annotated at 2026-07-25T18:38:43Z; (b) the QUALITY axis gets era labeling too — C1 showed
  only speed was era-fenced/de-inflated; pre-E7/E7/E8 quality points are different-instrument
  numbers (41-suite pool + B7 scorer + extractor fixes ≈ −0.1..−0.3 q systematic) and must be
  rendered as greyed "historical prior (era, instrument)" series, never one undifferentiated
  scatter. Never rescale values — label eras (append-only constitution). (c) GEPA/optimizer
  panel: hatch or grey the 2026-06-04→07-25 reflective-mutation NO-OP window (every reflection
  raised pre-LM-call; optimizer provenance broken) or suppress the panel until ≥1 post-fix
  GEPA trial exists; tooltip carries the provenance caveat. Panels stamp era + generated_at
  per the freshness contract.
- [x] **[E8-TRIALS-COLD-GUARD] Enforce restart/cold eligibility in future frontier
  terminalizers**: reject or quarantine restart-surface evidence until an affirmative
  prewarm/cache-warm predicate is present, and persist the predicate in the terminalization
  receipt. The 2026-07-27 retrospective clears E8 factually; it does not establish this
  forward instrument control. ✅ 2026-07-29: terminalization v2 computes an exact
  per-generation `cache_warm_state == warm` predicate from saved sidecars, binds it into both
  transition and completion receipt, and quarantines any cold/missing evidence. The pinned v1
  historical verifier remains available only with its original terminalizer hash.
- **[declined: ws58 2026-11-03 content-review: stretch; dashboard panels are owned by the hub (RTG-03), where the duplicate rows were retired]** **[H1] Circuit-breaker / forced-role-fallback panel** — deferred (stretch).
- **[declined: ws58 2026-11-03 content-review: stretch; same]** **[H2] REL-1 eval error-rate surface** — deferred (stretch).
- **[declined: ws58 2026-11-03 content-review: stretch bundle with no consumer]** **[H3] Contention-panel per-worker provenance**, **[M1] region_locks held-set
  SoT reuse**, **[M3] eval-batch lane attribution**, **[M4] calibration provenance**,
  **[L1] era-sliced KPI window** — untouched.

## Track: autopilot-decision-plane-audit-2026-07-22
<!-- gate: none -->

> Folded from `handoffs/active/autopilot-decision-plane-audit-2026-07-22.md` @ `b1bf3f3f7ade` on 2026-11-02 (BRF-T1-F20, route 1a, operator D1/D5; retired row EVL-03 → RTG-02). Body moved verbatim, headings demoted two levels to nest under this track; every open and closed box kept its text and ID.

### Autopilot Decision-Plane Adversarial Audit — 2026-07-22

**Type:** READ-ONLY adversarial audit (operator-commissioned 2026-07-22)
**Target:** the *consumer* layer — the code that reads eval/bench evidence and turns it into keep/revert/promote/keep decisions — in `/mnt/raid0/llm/epyc-orchestrator` (branch `spec-dec-mtp-refresh-2026-06-22`, HEAD `22e32ec2`).
**Instrument context:** the eval tower (the *producer*) just completed a two-day hardening (REL-1 excluded-error rows, hard-fail scorers, journal durability, real logprob confidence, E7 era pool rebuild). This audit asks whether the consumer turns that honest evidence into honest conclusions.
**Method:** every claim verified against actual code (file:line), actual SQLite queries, actual journal/state excerpts. No cited file is in the concurrent-edit flux set (`scripts/server/*`, `src/config/models.py`, `src/registry/stack_priors.py`); no HEAD-vs-worktree reconciliation was needed.

---

#### Executive Summary

The decision plane is **structurally strong on the SPEED axis and structurally blind on the QUALITY axis.** The single most important finding is an **asymmetry**:

- **Speed decisions are fully instrument-era-gated and fail-closed.** `pareto_epoch_ts` / `pareto_exclude_before_ts` are set to the E6 (v7 kernel) boundary `2026-07-20T13:30:13Z`; the Pareto archive is reconstructed from the append-only journal with era-exclusion + de-inflation applied; `strict_epoch` **raises** if an active speed era lacks its epoch timestamps (autopilot.py:5889-5890); and a `frontier_rerun_required` marker (currently OPEN, `completed_numeric_trials: 0 / min 16`) **forces** current-era numeric trials before the frontier can be exploited (autopilot.py:3430-3466). The Pareto archive also has a clean single source of truth: the state cache is torn down and re-derived from the journal fold ("journal fold is authoritative," autopilot.py:5907-5931).

- **Quality decisions have NO era fence at all.** The sequential-promotion e-process reads journal evidence filtered only by `core_id == "core_v1"` — a hardcoded constant (planner_evidence.py:23), not the live instrument era — with **no timestamp / era / `pareto_exclude_before_ts` / protocol filter** (autopilot.py:2846-2921, planner_evidence.py:103-123). `active_instrument_eras` contains only `autopilot_speed`/`cpu_bench`, **no `eval_quality` entry**. `quality_history` / `quality_history_by_tier` in state are **bare float lists with zero provenance** (defect #4 in its purest form). The fail-closed `instrument_era_guard.py` (scope `autopilot_quality`) exists but is **not imported by autopilot.py / safety_gate.py / actions.py**.

This matters **now, imminently**: the journal tail is trial 1437 @ `2026-07-16` (all pre-E7); state was last written `2026-07-21 09:19` (before the E7 boundary `2026-07-21T10:30`). The live EV-11c eval is producing the **first post-E7 quality evidence**. The next quality promote/revert that ingests it will pool a post-E7 number (79k/41-suite pool, B7 scorer) with pre-E7 `core_v1` baselines (21-suite, laxer scorer) into the **same** anytime-valid e-process wealth — exactly the contaminated-mixture the SEQ-1 provenance comment (autopilot.py:2860-2864) warns accrues wealth anti-conservatively.

The consumer's other failure-modes are **well-defended**: pause works (historical no-op fixed), the journal writer is durable (flock+fsync+torn-tail quarantine), the live decision loop and safety gate read all journal shards via the canonical helper, the meta-action loop is re-enabled with a two-depth guard, and every broad `except` in the promotion path fails **closed** (refuses to promote). The residual risks are the era-blindness above, a **HIGH** rewind/restore coverage gap (episodic vector store can silently desync; two live decision-gating stores are not purged), two **MEDIUM** journal-reader bugs in observability/preflight tooling (not the live loop), and a set of **inert derived-state mechanisms** (empty validity table, empty content-hash table, blind diversity guardrail).

**Lineage verdict (headline):** derived-state lineage **IS present** — 100% of strategy rows carry `created_at`, 99.9% carry `source_trial_id`, and 100% of journal rows carry `timestamp`, all mappable to the dated boundaries in `instrument_eras.yaml`. **Era-triage is feasible; a scratch rebuild is NOT the only honest option.** The caveat is that *no runtime consumer currently applies* instrument-era demotion to quality/strategy conclusions, and existing rows carry only a *timestamp* era stamp (no per-row content-hash / protocol id), so triage must be done by an offline, timestamp-keyed pass or a new era-aware retrieval filter.

**Findings by severity:** 1 CRITICAL · 3 HIGH · 6 MEDIUM · 5 LOW (plus reassuring counter-evidence noted inline).

---

#### CRITICAL

##### C1 — Quality promote/revert fires on mixed-era evidence (no era fence on the quality axis)
Defect signature #4 (numbers gating decisions without provenance) + #1 (state duplicated / no SSOT for era).

**The read path.** `_seq_inputs_for_trial` (autopilot.py:2830-2932) builds the null (baseline) profile and prior quality/rate observations from `journal.entries_with_supersessions()`. The only predicates applied per row are:
- `bug_corrupted_by` empty and `outcome_status ∉ {invalid, skipped}` (autopilot.py:2847-2850)
- `int(entry.tier) == tier` (autopilot.py:2851-2855)
- `str(seq.get("core_id") or DEFAULT_EVIDENCE_CORE_ID) != DEFAULT_EVIDENCE_CORE_ID → continue` (autopilot.py:2886; repeated at :2023 and :2440)

There is **no timestamp / era / `pareto_exclude_before_ts` / `pareto_epoch_ts` / protocol comparison anywhere in this loop.** `entries_with_supersessions()` takes no `since`/era argument (experiment_journal.py:789). Independently confirmed in `_seq_observation_rows` (planner_evidence.py:103-123): filters only on `core_id`, `candidate` present, and finite `z`.

**Why `core_id` does not fence eras.**
1. `DEFAULT_EVIDENCE_CORE_ID = "core_v1"` (planner_evidence.py:23) is a hardcoded constant. `_seq_inputs_for_trial` stamps every trial's decision evidence with this constant (`"core_id": DEFAULT_EVIDENCE_CORE_ID`, autopilot.py:2921) and passes it to `gate.check(..., core_id=...)` (autopilot.py:7817). The eval tower's real versioned era id (`EvalResult.core_id`, eval_tower.py:1527-1535) is **discarded** by the consumer.
2. The E7 scorer/pool rebuild did **not** mint a new `core_id`. Live journal (both shards, 1332 rows) has exactly two `seq.core_id` values: `None` (939 rows, legacy) and `"core_v1"` (393 rows). So pre-E7 and post-E7 evidence will both be `core_v1` and pool together.
3. `... or DEFAULT_EVIDENCE_CORE_ID` treats a MISSING `core_id` as the default — even a manual bump to `core_v2` would silently readmit every legacy `None` row.
4. E4 (the planned quality-instrument era with `core_id` + `policy_version`) is **not opened** in `instrument_eras.yaml` (only a trailing comment at line 119). `active_instrument_eras` = `{autopilot_speed: E6-autopilot-speed, cpu_bench: E6-cpu-kernel}` — no `eval_quality` key.

**The compared scalars carry no era stamp.** The regression gate compares `result.quality` against the persisted same-tier baseline scalar (safety_gate.py:1341-1350); the AP-24 keep/revert label compares `quality − baseline.quality_for_tier(tier)` (autopilot.py:7888, self_criticism.py:76-103). `quality_history` / `quality_history_by_tier` in `autopilot_state.json` are **bare float lists** — verified live: `quality_history = [1.85…, …, 1.96…]` (len 10), `quality_history_by_tier` = `{"0":[…], "1":[…], "2":[…], "3":[…]}` of bare floats — no timestamp, trial id, era, protocol, or n. These feed the MAD anti-noise check (median of history; safety_gate.py MAD_Z_THRESHOLD=2.0), so a post-E7 candidate is judged against a **pre-E7 bare-float median**.

**The guard exists but is unwired.** `src/autopilot_core/instrument_era_guard.py` ("fail-closed guards for activating era-bound AutoPilot instruments," scope `autopilot_quality`) is imported only by `eval_tower.py` and the offline `core_v2_promotion_report.py` — **not** by `autopilot.py`, `safety_gate.py`, or `actions.py`. Eval-instrument drift within a `core_id` is `log.warning`-ed, not failed closed (eval_tower.py:1537-1552), so drifted rows are still recorded and still pooled.

**Imminence.** Journal max trial = 1437 @ `2026-07-16T10:05:03` (all pre-E7). State mtime `2026-07-21 09:19` (pre-E7 boundary). EV-11c (2026-07-22) is generating the first post-E7 rows. The very next quality decision that consumes them is the one at risk.

**Impact:** honest post-E7 evidence produces a dishonest conclusion — a candidate can be confirmed/promoted or reverted on an e-process whose wealth mixes two instruments. This is the audit's core thesis realized. **Severity: CRITICAL.**

---

#### HIGH

##### H1 — Evidence identity is a hardcoded constant that ignores the real era stamp
Sub-finding of C1, called out separately because it is the concrete code defect to fix. The decision-bearing `seq.core_id` is the constant `"core_v1"` (autopilot.py:2921), overriding `EvalResult.core_id`. Combined with the `or DEFAULT` fallback (autopilot.py:2886/2023/2440), the era predicate is **inert**: it neither reflects the live era nor excludes un-stamped rows. Note (verified against live data): the real stamp is **not even present historically** — 0 of 1103 rows with populated `eval_details` carry `core_id` or `dataset_content_sha256`; the eval tower only began stamping them in the E7 hardening, which postdates the journal tail. So going forward the true identity is available in `eval_details` but the consumer discards it. **Severity: HIGH.**

##### H2 — Rewind/restore silently desyncs the episodic vector store and skips two live decision-gating stores
Defect signature #1 (no single source of truth across SQLite/FAISS layers) + #2 (silent).

The codified "rewind" is checkpoint/restore in `StructuralLab` (there is no separate `rewind` script; the `*.bak-rewind*` dirs are ad-hoc operator backups). Operator entrypoint `cmd_restore` (autopilot.py:8941-8949) and in-loop auto-rollback after 3 consecutive safety failures (autopilot.py:7850-7883) both call `lab.restore_checkpoint()` (structural_lab.py:147-208). Coverage:

- **Strategy store is SAFE (atomic).** `strategies.db` + `strategy_embeddings.faiss` + `strategy_id_map.npy` are co-located in `repl_memory/strategies/` (strategy_store.py:313-324) and restored as one `rmtree`+`copytree` unit (structural_lab.py:195-205). SQLite and FAISS cannot desync here. AP-22 short-term memory is restore-or-clear (structural_lab.py:186-193). This is the historically-flagged store, and it is correct.
- **Episodic/sessions store is SPLIT-RISK.** Its `episodic.db`, `embeddings.faiss`, `id_map.npy` are three **independent** `CHECKPOINT_FILES` entries (structural_lab.py:39-41) restored file-by-file with copy-**if-present** and **no clear-on-absent, no post-restore integrity rebuild** (structural_lab.py:164-169). Restoring a checkpoint that carries `episodic.db` but not `embeddings.faiss` leaves an OLD SQLite paired with a LIVE FAISS index — rowid↔faiss-id mapping breaks silently. Evidence this happens in practice: `repl_memory/sessions/` is littered with recovery artifacts (`id_map.pre-repair-*` ×7, `id_map.npy.broken-1779368503`, `id_map.npy.bak_pre_erase`, `id_map.npy.wipe-bak-*`).
- **Two live decision-gating stores are NOT checkpointed/purged at all:** `failure_blacklist.yaml` (BLACKLIST_PATH, autopilot.py:198; 20 KB, ACTIVE — gates which actions the planner may re-sample) and `orchestration/optuna_study.db` (454 KB, ACTIVE numeric-swarm study). A restore rolls state back but leaves these forward-dated. (For auto-rollback the blacklist asymmetry is arguably intentional — it appends the failing config before restoring — but for operator `cmd_restore` it is silent and undocumented.)

**Severity: HIGH** (strategy store safe, but episodic store can desync silently and two live gating stores are ignored).

##### H3 — `preflight_audit.py` journal reader stops at the first shard gap (JRN-7), and it gates autopilot start
Defect signature #2. `preflight_audit._jsonl_paths` (preflight_audit.py:199-209) for a base-file path uses `batch = 1; while True: if not (…_{batch}.jsonl).exists(): break` — a missing `_2` hides `_3`+ (the exact JRN-7 class the canonical `journal_shards.py` was written to eliminate). Its directory-invocation branch (preflight_audit.py:198) is correctly numeric via `_jsonl_batch_key`; only the base-file branch is buggy, and the default `JOURNAL_PATH` (preflight_audit.py:50/597) **is** the base file. Because preflight gates autopilot start, a shard gap → undercounted trials/coverage → mis-assessed readiness. **Severity: HIGH** (start-gating), reader currently benign only because no gap exists today.

---

#### MEDIUM

##### M1 — `strategy_validity` and `content_hashes` tables are EMPTY → the AP-28 validity-weighted ranking is inert
Defect signature #2/#4. Live `repl_memory/strategies/strategies.db`: `SELECT COUNT(*) FROM strategy_validity` = **0**, `content_hashes` = **0**. `_validity_score` (strategy_store.py:595-609) returns the 0.5 prior when no row exists → **all 1424 strategies are retrieved at uniform 0.5 validity**, regardless of whether structural_lab later disproved them. `update_validity` (strategy_store.py:510-544) is wired and called (structural_lab.py:874) but has produced no rows in the current store — the advertised "validity-weighted ranking, per-entry staleness" (module docstring) is a **no-op** today. The retrieval-time staleness proxy that DOES fire — `context_hash` (SHA-256 of `model_registry.yaml` + `frontdoor.md` + `worker_general.md`, strategy_store.py:576-593) — is **orthogonal to instrument eras**: E5/E6/E7 (kernel + eval-pool boundaries) do not touch those three files, so a pre-E7 strategy is not flagged stale by config-hash. **Severity: MEDIUM.**

##### M2 — `phase_status.py` journal reader sorts shards lexicographically (JRN-6)
`phase_status._journal_shards` (phase_status.py:382) = `sorted(journal_dir.glob("autopilot_journal*.jsonl"))` with **no key** → `autopilot_journal_10.jsonl` orders before `_2.jsonl` once the index reaches two digits. It reads every shard (no shard dropped) but appends rows out of trial order, corrupting any latest-trial/order-dependent logic. Observability/status reporter, not the live keep/revert loop. **Severity: MEDIUM.**

##### M3 — Action-local revert gate falls back to legacy-only gating on seq-input error
`_action_gate_check` (actions.py:879-886): `except Exception … return ctx.gate.check(eval_result)`. This disables the sequential path on error (conservative for the ratchet) but means an ephemeral mutation is then judged only by the legacy quality-floor/regression gate — a mutation the seq path would scrutinize can be **kept** if it clears the legacy floor. **Severity: MEDIUM.**

##### M4 — Journal `seq.core_id` records the constant, not the produced era; `keep_revert_decision` records INTENT
The journal row (autopilot.py:8366-8407) carries substantial lineage (`trial_id`, `timestamp`, `config_snapshot`, `config_diff`, `parent_trial`, `git_tag`, `metric_schema_version`, full `seq` block), but (a) `seq.core_id` is the constant `"core_v1"`, not the eval-tower era (defect #3, intent-not-realized for the identity field), and (b) `keep_revert_decision` is the **rule-based self-criticism label** (`quality − baseline`, self_criticism.py:76-103), not the realized config-revert outcome or `BaselineUpdateResult.updated`. Realized baseline state lives separately in `autopilot_state.json` (`Baseline.to_state_dict`, `seq_last_promotion_blocked`). A reader that trusts `keep_revert_decision` as realized state must reconcile against a different file. **Severity: MEDIUM.**

##### M5 — AP-37 diversity-stall guardrail is inert (blind for ~56 consecutive trials, no escalation)
`meta_optimizer.observe` (meta_optimizer.py:163-165): when `distinct2` or `semantic_embedding_agreement` is unavailable, status = `"signal_missing"`, `trigger = False`. Live `diversity_stall_state` shows `status: "signal_missing"` / reason `"distinct2 or semantic_embedding_agreement unavailable"` for **every** trial 1380-1436. So the diversity guardrail has been blind for ~56 trials with no escalation. It **fails safe** (never falsely recommends a rebalance), but the operator has no signal that a decision-influencing monitor is dark. **Severity: MEDIUM** (guardrail down, but fail-safe).

##### M6 — `mutation_graph.db` empty → mutation-outcome priors are absent (silent)
`repl_memory/mutation_graph.db` is 0 bytes; `MutationGraph.__init__` (mutation_graph.py:101-134) `CREATE TABLE IF NOT EXISTS` on connect, so reads of mutation-type × failure-pattern outcome priors return empty with no error. Not checkpointed by rewind (H2), so a state-loss event leaves it empty silently. Low live impact today (the graph is unused), but the planner's mutation priors are silently absent. **Severity: MEDIUM/LOW.**

---

#### LOW

- **L1 — `scripts/analysis/corpus_v1/common.py:332`** globs `autopilot_journal_*.jsonl` (trailing underscore) → **drops the base shard** (first 1000 trials) AND sorts lexicographically. Combined JRN-5(inverse)/JRN-6. Corpus-analysis tool, out of the decision path, but a real data-completeness bug.
- **L2 — Dashboard journal reader (`src/api/routes/dashboard.py:2390-2422`)** is a correct local numeric-sorted reader (Class B) but duplicates the canonical `journal_shards.py` logic — drift risk if one is fixed and not the other.
- **L3 — Default-OFF accept gates.** `_skill_efficacy_accepts` returns `True` when its arm is `None` (actions.py:964-965); `_bsv2_accepts` returns `True` when `baseline_result is None` (actions.py:1063-1064) — both admit-all unless `_SKILL_EFFICACY_GATE_ENV` / `_BSV2_ACCEPT_GATE_ENV` are set (actions.py:938-947). A coverage gap, not a silent-permit-on-error.
- **L4 — Killed-trial placeholder** (autopilot.py:5501-5522) does not set `outcome_status` (defaults `"ok"`, experiment_journal.py:250); it carries `quality=0.0` + `pareto_status="dominated"` + `bug_corrupted_by`, and the frontier path additionally requires `outcome_status=="ok"` AND real quality, so it cannot pollute the frontier. Cosmetic.
- **L5 — Stray 0-byte DBs** `repl_memory/strategy_store.db` (top-level) and `repl_memory/strategies/strategies.sqlite` are not read by any code (the live store is `repl_memory/strategies/strategies.db` via `DEFAULT_STRATEGY_PATH`). Harmless clutter, but a future mis-pointed reader would silently get an empty store.

---

#### Reassuring counter-evidence (verified solid — do NOT "fix")

- **Pause works** (historical no-op fixed 2026-05-24). The main loop `while not shutdown_requested:` (autopilot.py:6534) re-reads `_EXTERNAL_CONTROL_FIELDS = ("paused","pause_reason","_in_cache_flush")` (autopilot.py:5801) from disk **every iteration** (autopilot.py:6553-6560) and idles on `paused` (autopilot.py:6579-6596); `cmd_pause` writes under the H4 cross-process lock (autopilot.py:8842-8851). **Memory note `feedback_autopilot_pause_broken_use_sigterm` is STALE relative to code.**
- **Journal writer is durable.** `ExperimentJournal.record` (experiment_journal.py:552-583): full line serialized, single `write` under `fcntl.flock(LOCK_EX)` + `flush` + `os.fsync`; torn tail is quarantined to `.corrupt-<ts>` + truncated on next append (experiment_journal.py:369-429); mid-file corruption **raises** `ExperimentJournalCorruptError` (not silently dropped). Rotation is deterministic (`batch = trial_id // MAX_TRIALS_PER_FILE`, MAX=1000) with no lost/double-write window.
- **Live decision loop + safety gate read ALL shards correctly (Class A).** Both build `ExperimentJournal()` whose `_load_existing` iterates the canonical `journal_shards()` (experiment_journal.py:461); `safety_gate.py:284-288` reads `all_entries()`/`supersession_events()` transitively canonical.
- **Pareto archive has a single source of truth.** Speed-axis era params (`pareto_epoch_ts`, `pareto_pre_epoch_speed_factor`, `pareto_exclude_before_ts`) are read from state (autopilot.py:5866-5891) and applied to a **journal-fold reconstruction**; `strict_epoch` **raises** if an active speed era lacks them (autopilot.py:5889-5890); the cached `state["pareto_archive"]` is discarded and re-derived ("journal fold is authoritative," autopilot.py:5907-5931). `frontier_rerun_required` is **enforced**, not just recorded — it forces current-era numeric trials until `min_trials` (16) complete before clearing (autopilot.py:3430-3466); currently OPEN at `completed_numeric_trials: 0`.
- **Meta-action loop re-enabled + guarded, no t188 residue.** Live `consecutive_meta_actions = 0`, `trial_counter = 1438`, no `_meta_halt_reason`. Forced-substitution at N=1 converts a 2nd consecutive meta no-op into a measured `seed_batch` tagged `meta_action_forced_metric_trial` (autopilot.py:4381-4402, records intent-vs-realized); latched pause backstop at N≥5 survives restart via `_EXTERNAL_CONTROL_FIELDS` (autopilot.py:7598-7636).
- **Promotion path fails CLOSED on error.** `verdict.seq is None` → `update_baseline` refuses (safety_gate.py:1797-1809); `_baseline_eligible` `except → return False` (safety_gate.py:1684-1686); `_bsv2_accepts` `except → return False`/block (actions.py:1100-1115); `_seq_candidate_replay_payload` `except → None`. No permissive promote-on-error found. Promotion thresholds are conservative: baseline promotion needs `combined_E ≥ SEQ_PROMOTION_FINAL_CONFIRM_E (100)` AND `delta_ci.excludes_regression` (autopilot.py:2284-2293); candidate confirm needs `E_quality ≥ 20.0` AND `E_rate ≥ 20.0` (sequential_verdict.py:45-56, safety_gate.py:1182-1185); monotonic baseline uses strict `>` (safety_gate.py:1836-1844); near-tie keep/revert → `"unchanged"` (self_criticism.py:93-98); reproduction floor `BASELINE_PROMOTION_REPRO_MIN = 3`.

---

#### LINEAGE VERDICT (the derived-state triage question)

**Question:** For each derived store, do entries carry traceable lineage to the evidence that produced them, such that pre-E7-derived conclusions can be IDENTIFIED and selectively demoted (era-triage) — or is lineage absent, forcing a scratch rebuild?

**Answer: Lineage IS present. Era-triage is feasible. A scratch rebuild is NOT required.**

**Evidence — strategy store** (`repl_memory/strategies/strategies.db`, the live store; the top-level `strategy_store.db` is a 0-byte stray):

- 1424 rows. Schema carries lineage columns: `source_trial_id`, `created_at`, `evidence_trial_ids`, `context_hash` (strategy_store.py:330-355).
- Population: `created_at` on **100%** (range `2026-04-02` → `2026-07-11`); `source_trial_id` present on **1423/1424 (99.9%)**; `evidence_trial_ids` non-empty on 119 (patterns/conventions); `context_hash` on 1221/1424 (86%).
- Timestamp era-buckets vs `instrument_eras.yaml` boundaries: **244** pre-E2 (`<2026-06-01`), **1121** E2→E5, **59** E5→E6 (`2026-06-26T22:07:11`→`2026-07-20T13:30:13`), **0** E6→E7, **0** post-E7. → the ENTIRE store predates E6/E7; under strict era-triage every quality/speed-numeric conclusion demotes to historical prior, and every row is **individually classifiable** by `created_at`.
- Sample rows (evidence of usable lineage):
  - `journal-consult-gate-trial-1251 | source_trial_id=1251 | created 2026-07-07T14:21:57 | pattern | evidence_trial_ids=[1251] | ctx=c6533737f7c3`
  - `opseed-green-v6-tool-activation-latency | 1071 | 2026-07-03T09:53:20 | pattern | evidence_trial_ids=[1063,1065,1066,1067,1068,1069]`
  - oldest: `source_trial_id=5 | 2026-04-02T07:39:21 | prompt_forge | raw`

**Evidence — journal (primary quality/speed evidence):** every row carries `timestamp` (100%, ISO8601+tz), `git_tag` (present but empty on 215/1332 rows), `metric_schema_version` (`"1"` on 1317/1332), and REALIZED outcome fields (`outcome_status`: ok 1212 / skipped 57 / invalid 48; `pareto_status`: dominated 999 / frontier 85 / fast_reject 129; `keep_revert_decision`: revert 457 / excluded 411 / keep 229). A supersession mechanism (`bug_corrupted_by` on 246 rows) already quarantines evidence. **Caveat (verified):** no historical row carries `eval_details.core_id` or `dataset_content_sha256` (0 of 1103 populated) — those are new E7 eval-tower stamps that postdate the tail — so existing rows are era-classifiable by **timestamp only**, not by content hash. Given the dated era boundaries in `instrument_eras.yaml`, timestamp classification is sound.

**Evidence — Pareto archive:** journal-derived and already era-gated at read time (`exclude_before_ts` / `deinflate_before_ts`, autopilot.py:5917-5924); the `frontier_rerun_required.previous_marker.archive_snapshot` records `trial_ids`, `captured_at`, and the era reason — full lineage.

**Chain:** `strategy.source_trial_id` → journal trial → `timestamp` (+ `git_tag`) → dated `instrument_eras.yaml` boundary. This chain is intact on ~100% of derived rows.

**Therefore:**
- The operator can run an **offline, timestamp-keyed era-triage** that flags every strategy row (`created_at`) and every journal-derived conclusion (`timestamp`) as pre-/post-E7 and demotes pre-E7 quality/speed-numeric conclusions to hypothesis. **No scrub-to-zero is warranted.**
- BUT lineage being *present in the data* is not the same as being *applied by consumers*. Two gaps must be closed for the triage to actually bite: (1) the quality decision path applies **no** era filter (C1) — an offline triage of the strategy store will not stop the live e-process from pooling pre/post-E7 journal rows; (2) the strategy store's only runtime freshness signals (`context_hash` staleness, empty `strategy_validity`, journal supersession) are all **orthogonal to instrument eras**, so retrieval will keep surfacing pre-E7 strategies at full weight until an era-aware filter is added.

**Verdict in one line:** *Era-classify, don't scratch* — the data supports selective demotion; the missing piece is a consumer that reads the era, not a missing lineage.

---

#### Prioritized fix list (file:line targets)

1. **[CRITICAL, C1/H1] Era-fence the quality e-process.** In `_seq_inputs_for_trial` (autopilot.py:2830-2921) and `_seq_observation_rows` (planner_evidence.py:103-123), stop stamping the constant `"core_v1"` (autopilot.py:2921) and instead carry the eval-tower `EvalResult.core_id` / an `eval_quality` era label; add a timestamp/era exclusion analogous to the speed-axis `pareto_exclude_before_ts`. Wire `src/autopilot_core/instrument_era_guard.py` (scope `autopilot_quality`) into `autopilot.py`/`safety_gate.py` so cross-era pooling fails closed. Add an `eval_quality` key to `active_instrument_eras` at the E7 boundary and a `quality_epoch_ts`/`quality_exclude_before_ts` analog. **Do this before EV-11c post-E7 results feed a promote/revert.**
2. **[CRITICAL/C1] Give `quality_history` provenance.** `quality_history` / `quality_history_by_tier` (state; consumed safety_gate.py via autopilot.py:6337-6338, written back :8493-8494) must become records of `(value, trial_id, timestamp, core_id/era, n)` not bare floats, so the MAD median (safety_gate.py MAD_Z_THRESHOLD path) cannot silently mix eras.
3. **[HIGH/H2] Make restore atomic per store + purge or version the gating stores.** In `structural_lab.restore_checkpoint` (structural_lab.py:164-208): restore the episodic `episodic.db`+`embeddings.faiss`+`id_map.npy` as one unit with clear-on-absent + a post-restore FAISS↔SQLite integrity rebuild (mirror the strategy-dir `rmtree`+`copytree` at :195-205); add `failure_blacklist.yaml` (autopilot.py:198) and `optuna_study.db` to `CHECKPOINT_FILES` (structural_lab.py:37-46) or document/enforce the intended asymmetry in `cmd_restore` (autopilot.py:8941-8949).
4. **[HIGH/H3] Fix the preflight JRN-7 reader.** Replace the base-file `while True … break` in `preflight_audit._jsonl_paths` (preflight_audit.py:199-209) with `resolve_journal_paths()` from `journal_shards.py`.
5. **[MEDIUM/M2] Fix the phase_status JRN-6 reader.** `phase_status._journal_shards` (phase_status.py:382) → use `journal_shards()` (numeric-sorted) instead of bare `sorted(glob(...))`.
6. **[MEDIUM/M1] Repair or retire the validity/content-hash mechanism.** Either populate `strategy_validity` (ensure `update_validity`, strategy_store.py:510-544, is actually invoked on outcomes) or stop advertising validity-weighted ranking; add an instrument-era term to strategy retrieval (strategy_store.py:1684-1743) so `context_hash` staleness is not the only freshness signal.
7. **[MEDIUM/M3] Tighten the action-local gate fallback.** `_action_gate_check` (actions.py:879-886) should not silently fall back to legacy-only gating; surface the seq-input error and keep the seq scrutiny or fail closed.
8. **[MEDIUM/M5] Escalate a persistently-dark diversity signal.** `meta_optimizer.observe` (meta_optimizer.py:163-165) should raise/alert when `signal_missing` persists beyond a small streak, rather than silently reporting it every trial.
9. **[MEDIUM/M4] Separate INTENT from REALIZED in the journal.** Record the realized `BaselineUpdateResult.updated` / actual revert outcome alongside the self-criticism `keep_revert_decision` label (autopilot.py:8396) so a single journal row is self-describing.
10. **[LOW/L1,L2,L5] Housekeeping.** `corpus_v1/common.py:332` → include the base shard + numeric sort; collapse the dashboard Class-B reader (dashboard.py:2390-2422) onto `journal_shards.py`; delete the 0-byte stray DBs (`repl_memory/strategy_store.db`, `repl_memory/strategies/strategies.sqlite`).

---

*Audit performed read-only. No source file, index, or configuration was modified. Live eval EV-11c was not touched; no HTTP/inference/stack calls were issued. Counts and samples are from the live stores as of 2026-07-22.*

---

#### IMPLEMENTATION RECORD — C1/H1 quality-axis era fence (2026-07-22)

**Commit:** `epyc-orchestrator` `14cc929c` on `spec-dec-mtp-refresh-2026-06-22` (not pushed).
Mirrors the praised speed-axis pattern (`pareto_epoch_ts`/`pareto_exclude_before_ts`,
`strict_epoch`) onto the quality axis. **Inert when no active `eval_quality` era is set** —
every pre-existing gate/planner path is byte-identical, verified by 280 targeted unit tests
green (35 new). The CRITICAL C1/F1 blindness is closed before the first post-E7 promote/revert.

##### What landed
- [x] **`eval_quality` era key + startup migration** ✅ 2026-07-22 — `_migrate_eval_quality_era(state)`
  (autopilot.py, guarded/idempotent) seeds `active_instrument_eras.eval_quality` +
  `quality_epoch_ts` + `quality_exclude_before_ts` from the human-owned registry on next
  startup (code-path migration; the registry itself is NOT written). Falls forward to the
  `E7_EVAL_INSTRUMENT_BOUNDARY` code constant only when the registry is unreadable AND the
  clock is at/after the boundary; no-op before any boundary opens. Validated read-only against
  live `autopilot_state.json` (resolves `1784629800.0` = 2026-07-21T10:30Z; file untouched).
- [x] **Era-fence the quality evidence reads** ✅ 2026-07-22 — `_seq_inputs_for_trial` (the
  sequential e-process null/prior/alpha fold) and `format_planner_evidence_section` drop
  pre-boundary rows by `timestamp` (unparseable ts ⇒ excluded, fail-closed). Threaded at all
  three call sites via `quality_exclude_before_ts`. Pre-E7 rows are PRIORS (excluded from
  wealth/decisions), not deleted.
- [x] **Fail-closed SafetyGate re-baseline hold** ✅ 2026-07-22 — a pre-boundary (or era-mismatched)
  baseline vs the active era trips `quality_rebaseline_required`: `check()` SUPPRESSES the
  cross-era regression/per-suite/MAD legs (keeps the absolute quality floor + finite guard) and
  tags `quality_rebaseline_required`; `update_baseline()` REFUSES quality promotion with
  `ineligible_reason="quality_rebaseline_required"`. Both log loudly (ERROR, once) with the
  operator remediation. No promote/revert on quality crosses the boundary.
- [x] **Wire `instrument_era_guard` into the decision path** ✅ 2026-07-22 — new
  `active_eval_quality_era()` resolver added to `src/autopilot_core/instrument_era_guard.py`;
  autopilot.py now imports it (the audit's "guard exists but unwired" fix). Strict
  `_quality_epoch_params_from_state()` raises on a half-declared fence (speed-axis
  `strict_epoch` parity).
- [x] **`quality_history` provenance** ✅ 2026-07-22 — internal `_QualityObs(q, ts, era, core_id)`;
  legacy bare floats decode as pre-boundary (era=""); the MAD window filters to same-era
  samples so a post-E7 median can't be dragged by a pre-E7 window; persisted as the
  authoritative `quality_history_provenance_by_tier` (float mirror kept for external readers).
  `Baseline` carries + persists `eval_quality_era`.
- [x] **Tests** ✅ 2026-07-22 — boundary-straddle filtering, migration-from-era-less-state,
  re-baseline fail-closed (check suppression + update refusal), guard wiring, provenance
  round-trip + era-filtered MAD. Every existing autopilot/safety-gate suite kept green.

##### Era-registry row — NO new row required
The `E7-eval-instrument` row (scope `eval_quality`, `from: 2026-07-21T10:30:00Z`) **already
exists** in `orchestration/instrument_eras.yaml`. The implementation reads it as the source of
truth; the `E7_EVAL_INSTRUMENT_BOUNDARY`/`E7_EVAL_INSTRUMENT_ERA_ID` code constants only cite
that row for the fail-safe fallback and MUST stay in lockstep with it. **No human amendment of
the era registry or MEASUREMENT.md was made or is needed for this fix.**

##### What remains (owner action, out of this session's scope)
- [x] **Operator: clear the re-baseline hold (E7).** ✅ 2026-07-23 — reseed operator-applied for
  the E7 era (see master-handoff-index 2026-07-23 note: "era-fenced, reseed operator-applied").
  Original text retained: the hold is fail-closed BY DESIGN — it blocks automated quality
  promote/revert until a post-era baseline exists; reseeding baseline quality values is a
  measurement action across the human-amendment trust boundary.
- [x] **E8 RE-ARM (2026-07-26)** ✅ 2026-09-16 **CLOSED SUPERSEDED, not completed**, per operator
  ruling [`ruling_op19_e8_chain_20260827.json`](../../artifacts/operator/ruling_op19_e8_chain_20260827.json)
  (root `1ee8bd7c`). The ruling retires the E8 chain and re-anchors the reseed gate to the current eras
  (cpu_bench E9, eval_quality E16). The gate binds only at promotion. The E8-successor boxes below close
  under the same ruling. Original text retained: — **AutoPilot E8 baseline reseed = the gating task of the post-v8
  campaign (operator-directed; CPU lane, runs FIRST).** The v8 E8 era fence
  (`epyc-root/artifacts/operator/ratify_v8_era_fence_20260725.json`) demotes all pre-boundary
  speed/frontier evidence to historical prior AND requires **16 fresh v8-era numeric trials
  before AutoPilot speed maxima are trusted**; the same fail-closed re-baseline hold logic now
  applies against the E8 boundary. Procedure = the applied E7 reseed pattern: restart AutoPilot
  on the CURRENT frozen-v8 both-mode lineup (NO model changes until this completes — a
  mid-reseed model swap confounds era-change vs model-change), accumulate ≥16 fresh numeric
  trials + quality baseline reseed (`baseline_state.eval_quality_era: "E8"` + MAD
  `quality_history*` windows). Baseline-value writes that cross the trust boundary → prepare the
  human-only script and park it in the op-bundle; do NOT stall the campaign on it.
  Pre-restart check: verify the 2026-07-17 resume-preconditions (small-sample debugbench
  −1.5-gate trip on n_baseline=2; kv_compaction 500s) are fixed or still-relevant before
  resuming — re-thrash risk (~10 rollbacks on 2026-07-16) if skipped.
- [x] **E8 re-arm protocol/quality fence + empty-frontier bootstrap ratified** ✅ 2026-07-26 —
  operator receipts are durable; focused trust-boundary tests passed. The empty-frontier
  bootstrap deliberately has no `production_best` checkpoint until the v8-only frontier is
  rebuilt, so rollback restore warnings about its absence are expected and non-invalidating.
- [x] **E8 AutoPilot restarted on the frozen-v8 both-mode lineup** ✅ 2026-07-26 — exact
  `AUTOPILOT_SUPPRESSED_NUMERIC_SURFACES=kv_compaction` suppression is active; API remains
  `6/6`; no lineup or registry mutation was made.
- [x] **E8 numeric frontier accumulation** ✅ 2026-07-27 — exact-stop boundary reached
  `16/16/0` at trial `1458`; trial `1459` never dispatched. Trial `1457` was terminated
  before journal admission after an external GitNexus process overlapped its eval and is
  recorded as `autopilot_killed_mid_trial`. The authoritative current-era journal fold has
  16 eligible entries and reconstructs a three-point frontier (`1445`, `1446`, `1450`).
  Live marker terminalization remains a separate human transaction; no extra trial is needed.
- [x] **E8 quality reseed -- T1 tier evidence boundary** ✅ 2026-07-28 — clean v5 T1/r1,
  T1/r2, and T1/r3 are each terminal `50/50`, with `25` correct and zero final errors. The
  records are E8/core_v2 `e8_quality_full_pool_tier_baseline.v4`, `n=50`, and `q=1.5` under the
  repaired detached runtime-root contract (`43600480`). T1/r3 ordinal `32` incurred a
  scorer-side `ReadTimeout`; the protocol repaired it through exactly one deterministic
  scorer-tail replay, without regenerating inference, and the terminal row has `error: null`.
  T2/r1 is active. This is an evidence checkpoint only: it neither applies nor publishes the E8
  quality baseline.
- [x] **E8 v5 partial-resume provenance, runtime isolation, and exact-tail prompt reconstruction** ✅ 2026-07-28 — the bounded resume instrument now binds the held region claim to the real zero-byte lock, seals source/runtime provenance, and reconstructs full prompt-bearing generation inputs from the sealed public vectors before checking their hashes against both public and scorer-only vectors. This closes the failed-source path that sent a scorer-only row (no prompt and `question_id=unknown`) to the tail collector. Orchestrator commits `ecb8445c`, `c5acee57`, and `3484828f`; focused validation passed and independent review approved the bounded retry scope (`T2/r1` ordinals `98/99`, then fresh `T2/r2-r3`). This completes the instrument repair only, not collection, baseline application, or publication.
- [x] **E8 partial-r2 recovery/finalizer and consolidated-apply provenance instrument** ✅ 2026-07-28 — the recovery path now persists the exact three scorer replays plus the 438 generation obligations, validates the four segmented monitor windows, and produces a non-decision composite whose final resume scope is only fresh T2/r3. The one-token apply wrapper binds the exact composite/source hashes and is self-contained for a separate shell. Orchestrator `c9719229` supersedes the earlier instrument tip: plan schema v2 binds reconstruction and both downstream validators to the sealed T1 `core_v2`, reconstructs before any output write, and rejects legacy/mismatched intermediates. Focused validation passed `48` tests plus independent review and a no-inference real-vector preflight. This completed only executable evidence/provenance plumbing: the old failed partial-r2 namespace is ineligible audit evidence, and no baseline was collected, applied, or published.
- [x] **E8 terminal bridge and focused c1 mixed-tail successor instrument** ✅ 2026-07-28 — the experimental bridge now enforces a durable two-phase terminalization seal, exact source/hash bindings, sidecar-backed c1 evidence, and the six-row focused retry contract. Commits through `5568478f` in `/mnt/raid0/llm/worktrees/e8-terminal-bridge-20260728` passed `128` focused tests. Immutable failed attempts remain preserved at `e8_quality_baseline_v5_partial_r2_mixed_tail_c1_successor_20260728T193343Z` (wrong-request attempt, no valid collection) and `...T194407Z` (all six c1 requests completed). The latter correctly failed closed at `RACE.build_plan`: its predecessor journal response differed from the sealed EvalTower sidecar. This closes the bridge/instrument work only; it does not produce terminal evidence or authorize an apply.
- [x] **E8 c1 successor coherence-admission instrument repair** ✅ 2026-07-28 — root `1970977a` and E8 branch `a3738507` make P-BENCH-4, final-C1, the v5 wrapper, and the direct v5 adapter serialize on the same canonical trust-boundary lock. The repair removes final-C1's SIGKILL-stale private lock while retaining durable no-replace receipt publication; P-BENCH-4 recovery is unchanged. Targeted root/E8 suites passed `64 + 61` tests, and clean-environment validation passed with no inference, attestation, state, lineup, registry, or measurement mutation.
- [x] **E8 external-audit remediation integration checkpoint** ✅ 2026-07-29 — orchestrator main
  `56df82f5` merges the reviewed E8 closure chain `2962f9f3` (final-C1 successor binding),
  `88a1a43a` (recovery-evidence closure), and `4ae7447a` (ineligible candidate staging abort).
  The integrated E8 suite passed **322 tests**. This is an instrument/integration checkpoint only:
  it does **not** terminalize or ratify E8, collect a complete evidence bundle, apply a baseline, or
  publish one.
- [x] **E8 race-retry atomic-publication hardening** ✅ 2026-07-29 — orchestrator main
  `d24bc44f` and `1de17552` close the race-retry publication instrument: the producer writes only
  to a private sibling staging namespace, both producer and finalizer enforce the shared staged-tree
  validation, the producer validates before and after tree `fsync`, rechecks the immutable source
  bindings before its atomic no-replace publish, and records a durable abort plus no-replace
  quarantine when a post-publish durability step fails. The main-thread E8 suite passed **325
  tests**; Ruff, `py_compile`, and `git diff --check` were clean. This is publication-path hardening
  only: it neither executes final-C1/finalizer inference nor produces evidence, a receipt, an apply,
  or a published baseline.
- [x] **E8 original Tier-A post-fix audit** ✅ 2026-07-29 — independent re-audit against
  orchestrator `1de17552` passed **202 focused tests** and verified all six original Tier-A
  fail-open findings closed: the validator recomputes decision aggregates from canonical ledgers,
  sealed rows bind their real question identity and reject partial/degraded reuse, recovery requires
  execution proof, finalization is pinned to the reviewed tree, successor selection cannot weaken
  validation, and abort paths terminalize as ineligible audit evidence. **This is not E8
  terminalization:** structured timeout provenance remains an instrument-correctness blocker before
  fresh final-C1/finalizer evidence, the consolidated human receipt, or baseline application.
- [x] **E8 final-C1 capacity-fix ordinal generation** ✅ 2026-07-29 — under the ratified
  sequential `c1`/`q3` capacity-fix receipt, the two authorized generation obligations completed
  cleanly in
  `artifacts/operator/e8_quality_baseline_v5_partial_r2_final_c1_capacityfix_20260729T112433Z`:
  ordinal `97` (`leval_codeU_269`, sidecar SHA-256
  `352a5c0bfe3f03bfb3c52a8d6ff345acda413f7ac48a69dcfc2da7bf3a1e50ba`) and ordinal
  `279` (`leval_review_summ_382`, sidecar SHA-256
  `bd89f9e4d7e0a114518a7a0a729b5ea6322ea21e02728f9fc6795db40992a424`). No retry,
  timeout increase, baseline mutation, or admission occurred. The writer then failed closed in
  deterministic completion; `writer_abort.json` is
  `epyc.e8_quality_writer_abort.v1`, `terminal_aborted_no_admission`, with
  `no_auto_retry=true` and `no_admission=true`. The namespace remains immutable audit evidence,
  not final-C1 evidence.
- [x] **E8 lineage-composition deterministic completion successor** ✅ 2026-09-16 CLOSED SUPERSEDED (not completed) per `ruling_op19_e8_chain_20260827.json` (root `1ee8bd7c`; see E8 RE-ARM above) — repair the completion
  helper so its complete sealed 500-row journal resolves all authoritative immutable sidecars,
  rather than reading only its latest recovery sidecars. The failed capacity-fix namespace has an
  exact missing set of `418` ordinal provenances: `112` `imported_generation`, `295`
  `predecessor_generation`, and `11` `scorer_replay`. Build a no-inference successor with exact
  source/abort/sidecar pins, strict qid/question-id and nonpartial/nondegraded validation,
  byte-identical journal responses, atomic publication, and a typed success/failure run seal;
  leave the aborted source untouched.
- [x] **E8 universal abort terminalization** ✅ 2026-09-16 CLOSED SUPERSEDED (not completed) per `ruling_op19_e8_chain_20260827.json` (root `1ee8bd7c`; see E8 RE-ARM above) — wire the copy-only terminalizer into the
  `except` epilogue of every E8 runner (`v5`, reseed, resume, race-retry, mixed-tail repair,
  final-C1, and finalizer), with tests proving each injected failure publishes a durable terminal
  `run_seal.json`. The bounded offline terminal bridge is insufficient: each future abort would
  otherwise create another unsealed namespace requiring a bespoke recovery ceremony.
- [x] **E8 staged-input eligibility and race-retry layout repair** ✅ 2026-09-16 CLOSED SUPERSEDED (not completed) per `ruling_op19_e8_chain_20260827.json` (root `1ee8bd7c`; see E8 RE-ARM above) — prohibit finalization from
  accepting an unsealed `.staging-*` namespace merely because it is hash-pinned, and classify/fix
  the published race-retry layout that is structurally unvalidatable as committed. Confirm the
  live publication path before any successor/finalizer run; do not treat review prose as a
  runtime seal.
- [x] **E8 c1 required race/finalizer path** ✅ 2026-09-16 CLOSED SUPERSEDED (not completed) per `ruling_op19_e8_chain_20260827.json` (root `1ee8bd7c`; see E8 RE-ARM above) — execute only the protocol-required race/finalizer
  path against the repaired, revalidated instrument. **Structured timeout provenance and final-C1/
  finalizer inference remain open.** A c1 retry timeout remains a governed 300-second-budget
  decision; do not silently raise its timeout. This task does not authorize baseline application or
  publication.
  - [x] **Final-C1 capacityfix ordinals collected, but not admitted** ✅ 2026-07-29 — the ratified
    capacityfix source namespace
    `/mnt/raid0/llm/epyc-root/artifacts/operator/e8_quality_baseline_v5_partial_r2_final_c1_capacityfix_20260729T112433Z`
    contains clean generated sidecars for ordinal `97` / `leval_codeU_269`, SHA-256
    `352a5c0bfe3f03bfb3c52a8d6ff345acda413f7ac48a69dcfc2da7bf3a1e50ba`, and ordinal `279` /
    `leval_review_summ_382`, SHA-256
    `bd89f9e4d7e0a114518a7a0a729b5ea6322ea21e02728f9fc6795db40992a424`. The source tree is
    `b0a19752ad2fdbcd293a59ea448a7d801ea620282f735c624d559d3c423ca9b9`. This preserves the
    generated requests only; no final evidence, inference completion, state apply, or publication
    occurred.
  - [x] **Integrate scorer-isolation before deterministic-score replay, then re-run the bounded
    deterministic completion** — reviewed scorer isolation is orchestrator branch
    `codex/debug-scorer-isolation-20260729`, commit `79f3d2f35ddd00d21dc2fab235ff269db7c7dec7`.
    **ADJUDICATED 2026-08-12 (`auditor`, B9): the INTEGRATION half is DONE-UPSTREAM and
    verified** — both commits are ancestors of orchestrator `main`, merged 2026-07-29 in the
    required order (first-parent chain: `cb9e4b4b` merges isolation, `ad415448` merges bcb190 ON
    TOP of it), and the review verdict is builds-on-not-bypasses, proven by call-chain trace
    (completer → `independently_score_response` → `score_answer_deterministic` →
    `_load_orchestrator_debug_scorer` → the isolated `debug_scorer.score_answer`) plus bcb190's
    own sha-pinning of the scorer source (`_scorer_source_hashes` + runtime witness). Audit
    checkpoint: orchestrator branch `integrate/scorer-isolation-20260812` @ `3f734141`; 27/27 on
    the directly-changed suites. **The REPLAY half is BLOCKED-AND-LIKELY-MOOT**: the source
    evidence (`…capacityfix_20260729T112433Z`, sha-tree `b0a19752…`, and both failed completion
    attempts) exists NOWHERE — not on disk (exhaustive search), not in git (zero history);
    fabricating verdicts was correctly refused. And the E8 era this replay would feed advanced
    to E9 under operator signature 2026-08-11 22:15Z, so a fresh E9-era reseed (new generation,
    outside this row) supersedes the destroyed-evidence path either way. **Mootness ruling
    routed to the operator with `e8-token-retire`** (same decision family, morning note item 3);
    box stays open pending that ruling only.
    Its private per-invocation workspaces prevent BigCodeBench code-execution collisions. The
    successor replay is branch `codex/e8-bcb190-score-fix-20260729`, commit `8bc6eaa9`; it must be
    integrated second and reviewed against the isolation commit. Do not run new generation before
    deterministic replay of saved outputs is exhausted.
    **SECOND PASS 2026-08-12 (independent, overlaps the `auditor` note above — evidence:
    [`artifacts/audit/deterministic-rescore-fail-closed-20260812.md`](../../artifacts/audit/deterministic-rescore-fail-closed-20260812.md)):**
    integration and destroyed-evidence findings both CONFIRMED independently. Review was
    re-done at diff level rather than inherited: the fix swaps a shared `/mnt/raid0/llm/tmp`
    `NamedTemporaryFile` for a per-invocation `TemporaryDirectory` with `cwd` set to it in both
    execution paths, and closes a temp-file leak; `test_debug_scorer_code_execution.py` is
    **11 passed**, module-level and counted. The collision mechanism is now confirmed
    mechanically: BCB190's oracle `tearDown` runs `os.remove('test.db')` on a RELATIVE path, so
    concurrent rows deleted each other's database. `integrate/scorer-isolation-20260812`
    @ `3f734141` must NOT be merged — one audit commit on a stale base; merging reverts ~6,600
    lines of later `main`. **The REPLAY half was then executed against the corpus that does
    exist** (18 corpora, 6,746 rows under `orchestration/reports/`): **5,324 re-scored, 0
    divergences.** Tool `scripts/audit/deterministic_rescore_ledger.py`, 23 counted tests, 7
    mutants all killed.
  - [x] **Resolve the saved-output BigCodeBench score divergence fail-closed** — completion attempt
    `...deterministic_completion_20260729T124832Z` correctly refused admission because ordinal
    `418` / `bcb_BigCodeBench/190` stored `false` while deterministic code scoring returned `true`.
    **ADJUDICATED 2026-08-12 (`auditor`, B10, pairs with B9 above): BLOCKED-AND-LIKELY-MOOT for
    the same reason** — the saved outputs this ledger would bind (source bytes, before/after
    verdicts) were destroyed with the v5 evidence chain; no copy exists on disk or in git (the
    only `bcb_BigCodeBench/190` hits host-wide are unrelated /tmp probe copies with no
    provenance). No ledger was fabricated — FAIL-CLOSED held. The scorer-side fix is already
    upstream and verified (see B9 note). If the operator rules the E8 chain retired, this row
    closes as superseded; a fresh E9-era run would carry isolation from birth and never store
    the collision-class false. Routed with `e8-token-retire`. **CLOSED SUPERSEDED 2026-08-27 by operator ruling [`ruling_op19_e8_chain_20260827.json`](../../artifacts/operator/ruling_op19_e8_chain_20260827.json)** — the E8 chain is retired. The hold this row served is already closed (`autopilot_state.json.e8_quality_rebaseline` = `closed_operational_e15`, operator, 2026-08-08); `eval_quality` had in any case left E8 on 2026-08-05 and is now E16. Source bytes were swept by a `git clean -ffdx` on 2026-08-12 and were never tracked, so they are unrecoverable. Closed as SUPERSEDED, not completed; ordinal 418 stays permanently unadjudicable and no verdict was fabricated.
    Classification: the old scorer used shared `/mnt/raid0/llm/tmp` execution state, allowing a
    colliding `test.db`; the stored false has no execution witness. The correction ledger must bind
    source bytes, scorer source hashes, per-row before/after verdicts, and corrected sidecars before
    any new completion run.
    **SECOND PASS 2026-08-12 (independent, overlaps the `auditor` note above — evidence:
    [`artifacts/audit/deterministic-rescore-fail-closed-20260812.md`](../../artifacts/audit/deterministic-rescore-fail-closed-20260812.md)):**
    ordinal `418` remains UNADJUDICATED and no verdict was invented for it — destroyed-evidence
    finding independently confirmed by four searches. The bounded correction ledger was
    nonetheless BUILT and RUN over the live corpus
    ([`artifacts/audit/deterministic-rescore-ledger-20260812.json`](../../artifacts/audit/deterministic-rescore-ledger-20260812.json)),
    binding source bytes, scorer source hashes and per-row before/after verdicts as this row
    requires. **Corrections applied: 0** — 5,324 of 6,746 rows re-scored, zero stored-vs-rescored
    divergences. Three findings the row did not anticipate: (1) **232 rows store an in-band
    `[ERROR: …]` infrastructure failure as `correct: false`** — the same defect class biased the
    other way, excluded and reported rather than corrected up; (2) the pool's `scoring_method`
    disagrees with the method that actually ran on **52.7%** of rows, and joining on it
    manufactures ~629 phantom favourable "corrections" — a standing hazard for any future
    offline re-score; (3) **820 stored verdicts are permanently unauditable** (their corpus saved
    `answer_hash` but never `answer`). debugbench: **20 rows excluded-and-flagged by ordinal**,
    11 of them stored `true`; the oracle rebuild is scorer-side only — **0 pool rows use
    `code_patch`**, so all 4,253 debugbench pool rows remain vacuous.
  - [x] **Repair the historical producer-pin and abort-terminalization recurrence before final** ✅ 2026-09-16
    CLOSED SUPERSEDED (not completed) per `ruling_op19_e8_chain_20260827.json` (root `1ee8bd7c`); there is no final
    E8 promotion to gate. Original text retained: — **...before final E8 promotion** — independent review found that older producer namespaces can still be selected
    without a runtime `run_seal.json`, and the offline one-namespace terminal bridge does not make
    future producer aborts terminal by construction. Wire the copy-only terminalizer into each
    producer abort epilogue and require a pinned source seal for admission; verify the live
    race-retry publication path is structurally valid before publishing a replacement bundle. The
    immediate audit blocker is at `complete_e8_quality_baseline_v5_final_c1.py:139-166`: the
    ratified receipt binds the original producer helper while the live audit requires the current
    helper hash. Preserve the historical receipt pin and bind the runtime helper separately; never
    weaken or replace the original provenance check.
- [x] **E8 quality baseline reseed/apply** ✅ 2026-09-16 CLOSED SUPERSEDED (not completed) per `ruling_op19_e8_chain_20260827.json` (root `1ee8bd7c`). No E8 baseline was ever applied or published, and any future quality reseed runs against the current eval_quality era and binds at promotion — human-only protocol/source/apply scripts are
  prepared and parked. The earlier v4 collection is historical, non-decision evidence after the
  fixed-vector context defect. A first v5 launch failed before inference because its detached
  runtime root was wrong; the targeted fix is `43600480` on pushed branch
  `e8-v5-runtime-root-20260727` (`44` tests, Ruff, compile, and blocker-free preflight). Clean
  v5 T1/r1-r3 are complete and the old T2/r1 source is stopped after its two generation failures.
  The reviewed consolidated one-token wrapper is merged, but neither evidence nor state is applied.
  The tokenless recovery/finalizer sequence started on fresh output
  `e8_quality_baseline_v5_partial_r2_recovery_20260728T135608Z` after FG-2V released q0. Its
  later mixed-tail/c1 successor completed its six focused c1 requests but failed closed before
  race admission on a journal/sidecar coherence mismatch; the immutable evidence is retained.
  The coherence-admission and race-retry atomic-publication instruments are complete. The two
  latest final-C1 ordinals are clean but their namespace is terminal-aborted for the
  lineage-composition defect recorded above; deterministic successor completion plus universal
  abort/staging-layout repairs, then fresh finalizer inference, remain the immediate prerequisites
  to finalization.
  Do not apply or publish a baseline until that complete v5 evidence bundle and its single
  consolidated human trust-boundary action are ready.
- [x] **E8-LAUNCH-RACE — scope failed-start cleanup to the wrapper-owned launch** ✅ 2026-07-26.
  Independent review found that the initial rearm wrapper's global fallback `pgrep` cleanup
  could terminate a concurrent valid AutoPilot launch. The wrapper now records the returned
  supervisor and its direct child process groups, accepts a child only when its PPID matches
  that supervisor, and applies TERM → verify → KILL → verify only to those owned groups.
  Focused validation: `6 passed`; Ruff, ShellCheck warning level, `bash -n`, and
  `git diff --check` clean. A fail-closed live probe with the bootstrap receipt absent created
  no run directory and left no AutoPilot process.
- **[declined: ws58 2026-11-03 content-review: a pointer to other owners' files]** Non-owned audit findings untouched (other owners / other agents' flux files): H2
  rewind/restore atomicity (`structural_lab.py`), H3 preflight JRN-7 reader, M1 validity table,
  M2 phase_status reader, M3 action-local gate fallback (`actions.py`), M4/M5/M6, and the
  SafetyGate/RLVR audit's F2 (`export_rlvr_environment.py`, mid-edit by another agent).

---

#### HIGH — H4 (added 2026-07-22): The learned-routing Q signal is an append-only buffer, not Q-learning

Defect signature #4 (a number gating decisions that was never actually learned) + a write-path sibling of **H2** (the episodic store's integrity). Verified read-only against the `20260722T125604Z` snapshot; reproduced with the existing auditor `scripts/analysis/dar_write_path_audit.py` (unchanged, re-run).

##### Finding (reproduced)
- **99.695%** of 671,780 routing rows have `update_count = 0`. `store()` inserts a fresh row per observation; `update_q_value` (the TD apparatus DAR-1/2/3 build on) almost never fires.
- **643,874** update_count=0 rows collapse to **3,642** distinct `(objective, action)` pairs — **176.8x** duplication, max **7,889** rows for one pair.
- Rows carrying a learned (moved) Q: **0.305%**; DAR-2 could fire on ≤ **9.74%** (ceiling). The "learned router" is an append-only log.

##### Root cause (commit-dated)
The production scorer path `q_scorer._update_routing_memory` (and its escalation sibling) only TD-updates when `routing_decision.memory_id` is **already** set; otherwise it blind-appends via `store()`. But the **sole** production emitter of `ROUTING_DECISION`, `progress_logger.log_task_started` (progress_logger.py:366-377), **never populates `memory_id`** (`ProgressEntry.memory_id` defaults to `None`). So the update branch is **structurally unreachable from the progress-log path** — every scored routing decision falls through to append.
- `git blame`: the `if memory_id: … else: store()` structure is **original to `68df9787`** ("feat: MemRL episodic memory implementation", 2026-01-14) and never changed (only the `temporal_decay_rate` kwarg was added in `b3a5b4da`). **Append-only was the behavior since inception; the TD path was aspirational** — not a later regression that bypassed a working updater.
- The ~2,050 rows that *do* carry a learned Q come from a **different** writer: `score_external_result` (the MemRL/seeding/debug path), which *does* find-or-create by similarity + TD-update. Snapshot confirms: **1,706 / 2,050** learned rows have `context.source == "external"`; the progress-log path contributes ≈ none.

##### Fix (implemented, flag-gated OFF by default) — `ORCHESTRATOR_Q_TD_WRITE`
`orchestration/repl_memory/q_scorer.py`: when the append branch has no pre-linked `memory_id`, it now **find-or-updates** the existing `(objective, action)` routing row in place before appending. The "find" (`_find_existing_routing_memory`) uses the FAISS similarity index (fast) then requires an **exact** objective+action string match, so distinct objectives are never merged. TD math is unchanged (`update_q_value`, learning-rate + temporal-decay preserved).
- **`ORCHESTRATOR_Q_TD_WRITE` default OFF ⇒ byte-identical legacy append** (deployment is an explicit operator-boundary flip). Flag ON ⇒ in-place TD.
- The pre-linked-`memory_id` branch and the escalation path are unchanged. **Escalation (`_update_escalation_memory`) has the identical latent defect** (4,382 append-only rows) — left as a scoped follow-up; the routing defect is the audited/migrated one.
- TD math extracted to a pure `episodic_store.apply_td_update(...)` shared by the live path **and** the migration, guaranteeing identical replay math.

##### Migration (non-destructive, idempotent) — `scripts/maintenance/consolidate_q_append_only.py`
Chronologically replays the 643,874 append-only rows through `apply_td_update` (reward recovered per row via `r = 2q − 1`, valid for update_count=0), producing **one consolidated Q per `(objective, action)`** — the store the live path would have produced. Verified on a scratch copy: **671,780 → 31,548 rows** (3,642 TD-consolidated + 27,906 passthrough); biggest group 7,889 rows → one row `uc=7888`.
- **Non-destructive**: original `memories` table untouched; results in a new drop-in `memories_consolidated` table + `_q_consolidation_provenance` / `_q_consolidation_meta`.
- **`--dry-run`** (read-only, safe against the live DB) and a hard refusal to WRITE the live sessions store (copy to `/mnt/raid0/llm/tmp/` first).
- **Idempotent**: rebuilds deterministically from `memories` content.
- **Row classes preserved**: `update_count>0` (already-TD-updated, e.g. the external path) and objective-NULL rows **pass through verbatim** — a legitimately-distinct episodic class is not destroyed.
- **FAISS-sidecar consistency (ties to H2)**: the FAISS index / `id_map.npy` are **not touched**. Each consolidated row keeps its group's representative `id` + `embedding_idx`, so its vector + id_map entry stay valid. Collapsed duplicates' vectors become **orphaned-but-benign** — `retrieve_by_similarity` over-fetches and filters by SQLite membership, so an orphaned vector resolves to no row and is dropped. **No new SQLite↔FAISS desync class is introduced** (a later compaction can rebuild a compact index from the consolidated id set).

##### Poisoned-row verdict (seeding fix `3bfe2584`) — NOT store-identifiable
The in-band `[ERROR: …]` marker lives in the **answer text**, persisted in seed-run **report artifacts**, not in `episodic.db` (routing rows store only task_type / objective / priority). A 0.0 reward maps to `q = 0.5`, indistinguishable from a legitimately-wrong answer or a neutral default. **Poisoned rows cannot be reliably identified from store data.** Store-side **0.0-reward exposure** (proxy: `source=external ∧ uc=0 ∧ q==0.5 ∧ outcome=failure`) = **7,460 rows**, window **2026-05-25 → 2026-07-16** — an over-set (includes legitimate wrong answers). Excluding all of them would bias Q upward, so the migration does **not** guess: it prints the exposure and offers **`--exclude-memory-ids FILE`** for an operator list derived offline from the artifacts (era-triage decision).

##### Deploy plan (operator boundary — NOT executed here)
1. **Migrate first, on a copy.** `cp -r orchestration/repl_memory/sessions /mnt/raid0/llm/tmp/q_consolidate` → `python scripts/maintenance/consolidate_q_append_only.py --db /mnt/raid0/llm/tmp/q_consolidate/episodic.db --dry-run` then without `--dry-run`; inspect `memories_consolidated` + `_q_consolidation_meta`.
2. **Swap** (operator, during a quiesced write window with autopilot/API stopped): rename `memories`→`memories_pre_consolidation` and `memories_consolidated`→`memories` in the **live** `episodic.db` (or re-run the migration against the live copy in place). Optionally rebuild a compact FAISS index from the consolidated id set.
3. **Flip the flag** `ORCHESTRATOR_Q_TD_WRITE=1` and restart the API (so new observations TD-update the consolidated rows instead of re-appending). Order matters: migrate → swap → flag, so the first post-flip write finds a deduplicated store.
4. **Verify after**: `python scripts/analysis/dar_write_path_audit.py` — expect `update_count=0` fraction to fall and the duplication factor to approach 1.0 as new observations accrue; the DAR-2 "rows with learned Q" fraction should climb from 0.305%. Re-run the auditor as the DAR-2 effectiveness re-measure.

##### Deliverables / checkboxes
- [x] **Root-cause dated to `68df9787`** (append-only since inception; TD path aspirational) ✅ 2026-07-22
- [x] **Flag-gated in-place TD write path** (`ORCHESTRATOR_Q_TD_WRITE`, default OFF = byte-identical) ✅ 2026-07-22 — `q_scorer.py`, `episodic_store.apply_td_update`
- [x] **Idempotent non-destructive consolidation migration** with `--dry-run` / live-write guard / FAISS-safe design ✅ 2026-07-22 — `scripts/maintenance/consolidate_q_append_only.py`
- [x] **Poisoned-row verdict**: not store-identifiable; 7,460-row 0.0-reward exposure quantified; `--exclude-memory-ids` hook ✅ 2026-07-22
- [x] **Tests** (13): flag-off byte-identical, flag-on in-place TD + math, no cross-objective/action merge; migration replay-equivalence vs `update_q_value`, decay, idempotency, dry-run, exclude, passthrough, live-write refusal ✅ 2026-07-22
- [x] **Operator: run the deploy plan** (migrate → swap → flag → re-measure) at the scheduled boundary — the live 11h eval is routing through the current store right now; do NOT flip mid-eval. ✅ 2026-09-07 (on evidence at :489) — the plan was EXECUTED 2026-07-23: flag live (`845e7492` + reload), migration+table swap done (676,463→31,565 rows), audit confirms 1.0× duplication / 17.84% learned-Q; legacy table retained.
- [x] **Follow-up**: apply the same find-or-update to `_update_escalation_memory` (identical latent defect, 4,382 append-only escalation rows). ✅ 2026-07-29 — `orchestration/repl_memory/q_scorer.py`. `_find_existing_routing_memory` generalized to `_find_existing_memory(..., action_type=...)` and shared by both paths; the escalation branch now find-or-updates the existing `(reason, escalate:from->to)` row before appending. Identity key is `reason`, which is exactly what `build_memory_record` stores as `objective`, so the finder matches the field the row is stored under. `action_type` is pushed into the similarity query, so routing and escalation partitions can never cross. **`ORCHESTRATOR_Q_TD_WRITE` default OFF ⇒ byte-identical legacy append**, unchanged — deployment stays an operator-boundary flip. 7 new tests mirroring the routing set (flag-off append, flag-on in-place, `apply_td_update` math parity, distinct-reason and distinct-transition non-merge, pre-linked branch unchanged, cross-partition isolation); 92 passed, ruff clean.

- [x] ✅ 2026-07-23 **H4 Q-TD-write DEPLOYED**: flag live (845e7492 + reload), migration+table-swap executed (676,463→31,565), snapshot-refreshed audit confirms 1.0x duplication / 17.84% learned-Q. Legacy table + backup retained.
- [ ] **EV-CONF-2 — salient-token confidence source** (filed 2026-07-23): math AUROC 0.40 both arms = geomean anti-discrimination (length confounding). Build answer-token/salient-token confidence; re-baseline math AUROC before any math-domain confidence use. See ESC-7 draft §5.
  - *(2026-10-29, Codex refactor preparation.)* The original 200-row stratified manifest was reproduced byte-for-byte. The current orchestrator venv lacks `datasets`; a private loader resolved the historical bare GSM8K name to `openai/gsm8k`, then the unmodified adapter recovered all 1,819 questions. The original dataset SHA-256 and all 200 sampled qids passed the existing strict checks. The resulting private `--questions-jsonl` file was independently reopened through the actual probe loader: `/mnt/raid0/llm/tmp/codex-ev-conf2-20261029/questions.jsonl`, SHA-256 `798e4f3b973ffb7c153a1438904abec6cc81cc1a1b1a86a0db5a62221a6ee0af`. No inference was run. The current worker registry names Qwen; the original probe-era registry was extracted from orchestrator commit `88a2902d`, and its unmodified role loader resolves the original Gemma target, matching assistant and declared sampling. Future launchers should pin `/mnt/raid0/llm/tmp/codex-ev-conf2-20261029/registry-88a2902d.yaml` (SHA-256 `033d442fa14505fa9b2a667d3bf8089501e033a93ce023dfbf285f2ef3e87320`) and independently verify the live model. The original model and matching assistant remain absent. The historical September 21 GPU recipe predates SW-9 and does not contain the speculative-probability fix; its B-mtp arm is explicitly an artifact control, so that alone does not invalidate the original protocol. C5 source contains SW-9 and its later library exports the new sampler signatures; a fixed-kernel comparison would be separate and still needs a real behavioral smoke. Exact model identity and reconstruction notes: `/mnt/raid0/llm/tmp/codex-ev-conf2-20261029/FINDINGS.md`. This is preparation, not a math rebaseline. [no-belief: model-free preparation only]
  **Scoping (2026-07-23):** (a) Candidate sources, cheapest first: ANSWER-SPAN geomean (confidence
  over only the final-answer tokens — directly attacks length confounding; the boxed/final-answer
  extractor from SCORE-03/16 already locates the span); salient-token (min-prob or high-entropy
  decision tokens); self-consistency proxy (k-sample agreement — costs k× inference, last resort).
  (b) BLOCKER: per-token logprobs are NOT persisted (sidecar stores only the aggregate geomean) —
  offline re-scoring of E7c is impossible; EITHER extend the sidecar to persist the top-1 logprob
  vector per row (cheap, do first) THEN a ~200-row math probe suffices to compare sources, OR run
  a fresh instrumented probe. (c) Success gate: candidate source AUROC materially >0.5 on the math
  probe with ECE not degraded; then re-baseline math via a full arm and amend P-CAL. (d) Owner:
  eval-tower program, post-EV-BASELINE-E7 in priority order unless the operator promotes it.
  - **2026-09-16 (sub-evconf2): blocker (b) closed on the capture side.** Orchestrator `b98dee18` on branch
    `sub/evconf2-20260916`, merged to orchestrator `main` at `d8b915ee`.
    - What landed:
      - `scripts/autopilot/token_confidence.py` stores, per question-result sidecar row, the sampled-token logprob
        vector and the truncated top-k entropy vector (u16 millinats, 2 B/token, capped at 8192 tokens by
        keeping the head quarter plus the tail), plus the answer-span token indices from the SCORE-03/16
        `debug_scorer` extractors.
      - The key is additive (`token_logprobs`), so old sidecars stay readable. It is on by default;
        `AUTOPILOT_EVAL_TOKEN_LOGPROBS=0` turns it off.
      - Pure confidence sources: full/real-token/answer-span geomean, answer-span min, salient min-prob,
        high-entropy top-10%, and mean-entropy. Entropy is available because `n_probs=5` →
        `top_logprobs=5`. It is a lower bound from the top-k plus the lumped residual.
      - Offline tool `scripts/analysis/confidence_source_compare.py`: AUROC plus bootstrap CI, closed-bin ECE,
        paired ΔAUROC against the legacy geomean, and `--reweight-prevalence`.
      - 21 tests pass. The neighbouring eval tests pass too (406).
    - **FINDING (observation; source-read plus offline re-read of the E7c sidecar): the E7c math AUROC 0.40 is
      probably a speculative-decoding instrument artifact, not length confounding.**
      - llama.cpp `server-context.cpp` sets `result.prob = 1.0f; // set later` and `// TODO: set result.probs`
        for every draft-accepted token. The same code is in v7 (the E7c kernel) and v9.
      - E7c `worker_general`/`worker_math` both ran gemma-4-26B-A4B-it-ORIG-Q4_K_M with `draft-mtp`
        (`draft_max=2`) on the 4 CPU quarters.
      - In the E7c worker_general sidecar, 1335/1684 scored rows have `confidence == 1.0` at 6 d.p. and there
        are only 52 distinct values. The implied total NLL of a ~330-token derivation has a median of
        0.0005 nats, which real token probabilities cannot produce.
      - Mechanism: the geomean ≈ a handful of real tokens diluted by p=1 placeholders, so longer outputs look
        more confident. That matches the observed `-tokens_generated` AUROC of 0.58 (0.59 for worker_math).
      - The rounding also moves the sidecar-derived AUROC to 0.437, against the in-memory 0.401. ECE
        reproduces exactly.
      - Implication: every confidence source is void on any spec-on run, including the EV-4c code AUROCs if
        frontdoor ran MTP. The capture now marks placeholders (`n_placeholder`) and excludes them from the
        real-token sources. A kernel fix (populating accepted-token probs from the verify batch) is
        `llama.cpp-experimental` work.
    - **Probe spec (the next step; needs inference, not run):**
      - Rows: 200 math rows from the E7c dataset (sha256 `38e582cf…`, GSM8K+MATH-500). Draw 100 rows that E7c
        worker_general scored wrong and 100 it scored right (qid join, seed 42), so AUROC has about 100
        negatives. Score with `math_verify`, `production_temp_seed42`, `top_logprobs=20`.
      - Arms, same rows in each, served serially from ONE server:
        - **A, spec OFF.** This is the measurement.
        - **B, the same GGUF with `draft-mtp` ON.** This is the artifact control: it should reproduce
          AUROC < 0.5 with `n_placeholder` > 0.
      - Model and role: to be comparable with E7c, use **gemma-4-26B-A4B-it-ORIG-Q4_K_M in the
        worker_general role** with the E7c prompt path (`/v1/chat/completions`). Kernel and device differ
        from E7c (v7 CPU vs v9 HIP), so comparability is WITHIN the probe. Arm B stands in for E7c's
        instrument, and per-qid answer agreement with E7c is reported.
      - Read: `confidence_source_compare.py question_results.<arm>.jsonl --reweight-prevalence 0.7886`.
        Scoping (c) is read by a human from the per-source AUROC CI and ΔECE.
      - Runner gap: `eval_batch_serving_evaltower_window.py --mode math_rebaseline --n 200` can only draw
        unstratified rows, and only through the orchestrator role. A spec-off test port therefore needs
        either a stratified-qid option plus a role→test-port override, or a small direct llama-server
        driver that reuses the adapter, `score_answer_or_error` and `_EvalQuestionJsonlWriter`.
    - **GPU feasibility:**
      - Yes. gemma-4-26B-A4B Q4_K_M (16.8 GB) is proven correct on the MI210 HIP path, under MTP too
        (observation, `project_mi210_hip_graph_capture`). About 72k generated tokens per arm means minutes,
        not hours.
      - Qwen3.8-27B-Q8_0 (the live architect_general/coder_escalation on :8083) and Qwen3.6-35B-A3B-MTP-Q8_0
        (37.8 GB) also fit and are proven, but they are NOT E7c-comparable. Use them only as a
        generalization arm, and only with spec OFF, because the live :8083 runs MTP.
      - Serving on the GPU needs a spec-off test-port launch. That is an inference slot and a region claim,
        not a stack change.
  - **2026-09-16 (sub-evconf2-probe): runner gap closed and belief writer wired, zero inference.**
    - Orchestrator `f2e9ee07` + `7cc118da` (branch `sub/evconf2-probe-20260916`, from `b98dee18`, merged to `main` at `88a2902d`):
      `scripts/analysis/confidence_probe.py`, the direct driver.
      - Sample: seeded stratified draw (100 E7c-wrong and 100 E7c-right worker_general rows, seed 42). Row ids and
        qids are committed in `orchestration/reports/ev_conf2_probe/sample_manifest.json` (sample sha `66763b0b…`,
        source 1684 scored at 0.7886). The driver refuses to run if the dataset sha drifts from E7c `38e582cf…` or
        any qid drifts.
      - Requests: any OpenAI-compatible `--endpoint` over `/v1/chat/completions`, with the worker_general
        per-request sampling taken from the backend's own `_apply_deterministic_sampling` over the registry
        (temp 0.3, top_k 40, top_p 0.95, rp 1.1, seed 42). The direct-stage cap (2048) and stop list are used,
        the closing `</answer>` tag is restored, and `top_logprobs=20` is set. Scoring uses `math_verify`.
      - Persistence: rows go through `_EvalQuestionJsonlWriter` with the `token_logprobs` capture plus a `probe`
        key, one row at a time and resumable. `serving_identity.<arm>.json` records `/v1/models`, `/props` and
        `/slots`. `/props` `speculative.*` is recorded but untrusted, because llama-server fills it from
        sampling defaults.
      - **Arm A fails closed (exit 3)** on `/slots` speculative=true, on `timings.draft_n>0`, or on any
        placeholder token, and the offending row goes to `rejected.<arm>.jsonl`. Arm B refuses a server that
        never speculates.
      - Tests: 18 mocked-endpoint tests; the 342 neighbouring unit tests pass.
    - **Capture fix in the same commit:** the direct stage stops on `</answer>`, so the token stream ends inside
      the tag, and `locate_answer_span` then included the `<answer>` tag tokens in the "answer span". A new
      `unterminated_answer_tag` rule mirrors `_restore_stripped_answer_stop`.
    - **Runner recipes** (`confidence_probe.py --print-recipes`; NOT run):
      - Common launch: `env -u HSA_OVERRIDE_GFX_VERSION LD_LIBRARY_PATH=<build-fold-ef81196d5/bin>
        OMP_NUM_THREADS=1 taskset -c 184-191 …/build-fold-ef81196d5/bin/llama-server -m
        gemma-4-26B-A4B-it-ORIG-Q4_K_M.gguf --device ROCm0 -ngl 99 --jinja --reasoning off -fa on -ctk q8_0
        -ctv q8_0 -c 16384 -np 1 -t 8 -tb 8 -ub 512 --no-mmap --metrics --slots`.
      - **A-specoff** runs on :18381 with the common launch unchanged.
      - **B-mtp** runs on :18382 and adds `-md gemma-4-26B-A4B-it-assistant-v6-Q8_0.gguf -ngld 99 -devd ROCm0
        --spec-type draft-mtp --spec-draft-n-max 2 --spec-draft-p-min 0.0`.
      - Flag spellings were checked against the champion `libllama-common.so` strings.
      - Order: re-hash the binary, run `verify_ggml_linkage.sh`, then the `--manifest-only` dry draw. Then for
        each arm serially: launch, probe, `compare --out`, and the belief capture. Sample VRAM and KFD during
        each arm, and kill only the captured PID.
    - **Belief writer VB-EVCONF2:** root `c8c68662` (branch `sub/evconf2-root-20260916`, merged at root `1e1de5fb`, fix `4fe47225`). See
      `vidya-belief-substrate-program.md`.
    - **Contamination sweep:** the EV-4c code baselines were also served with `draft-mtp` on (frontdoor
      `draft_max=4`), but show no 1.0 saturation (0/820, 2/817), so their contamination is unmeasured, not
      absent. The citation list is in `progress/2026-09/2026-09-16-sub-evconf2.md`, and the caveat task is
      VB-EVCONF2-CAVEAT.
  - **2026-09-16 (wrap-up):** both orchestrator branches are merged (`d8b915ee`, `88a2902d`); the capture
    takes effect at the next AutoPilot restart / API reload. The A-specoff / B-mtp probe itself is still
    inference-gated and not run, so this box stays open.
  - **P-CAL caveat — operator decision 2026-09-16, option (a):** the ratify script merged at root `17619015`
    (`scripts/operator/ratify_pcal_specdec_contamination_20260916.sh`, wrapper
    `scripts/operator/run_pcal_ratify_20260916.sh`). **Waiting on the operator to run
    `run_pcal_ratify_20260916.sh`** (human-only trust boundary). Detail:
    `progress/2026-09/2026-09-16-sub-pcal-ratify.md`.
  **Intake 2026-09-23 (jev-exl3):** (i) before launching a separate spec-off server, test whether a per-request
  `"speculative.n_max": 0` on the live v10 server yields fully populated per-token probs — the probe's fail-closed checks on
  draft_n>0 and placeholder tokens detect a miss (intake-1521). (ii) External expectation for the spec-OFF math arm:
  mean-token-prob AUROC 0.690 on GSM8K (8-SLM range 0.662-0.723), ~0.72 across GSM8K/MultiArith/SVAMP, near-random on
  AQuA; a spec-OFF result near or below 0.5 points at the instrument first (intake-1525).
- [x] **EV-CONF-3 — llama.cpp-experimental: populate result.prob/probs for draft-accepted tokens — SUPERSEDED by SW-9** ✅ 2026-09-24 from verify-batch logits (v10 `server-context.cpp:4238-4244` TODO), for the next production candidate (v11); never patched into v10. Evidence: intake-1521. *Closed as a duplicate (operator-directed tidy 2026-09-26):* the same fix landed as [`speculative-decoding-mtp-refresh.md`](speculative-decoding.md#track-speculative-decoding-mtp-refresh) **SW-9** — `experimental/mtp-spec-probs-fix-20260924` @ `2b57340bf`, folded into the champion `ak/champion/llama-cpp-ffc1bac82eec` 2026-09-24 (draft-mtp `n_probs=8`: production 2/96 tokens with probs, candidate 96/96; speed-neutral). v10 untouched; carriage into production is the champion's v11 promotion (separately operator-gated), tracked there, not here.

- [x] ✅ 2026-07-23 COMPLETE — reseed APPLIED by operator (12:45:07Z; backup autopilot_state.pre-reseed-20260723T124507Z.json; gate reads T1 1.6 / T2 1.891, era E7-eval-instrument; fail-closed hold lifted on same-era designed-core ground) **EV-BASELINE-E7 — post-E7 full-pool baseline sweep (reseed prerequisite; filed 2026-07-23)**:
  the granted era-fence reseed is UNDERDETERMINED by current data — `baseline_state` is tier-keyed
  over the 41-suite E7 pool, while post-E7 measurements cover only math (E7c) + scoring_verifiers
  (EV-4c). Deriving `baselines_by_tier` from 2 suites would fabricate a tier baseline (the exact
  defect class this campaign eliminated). REQUIRED: a quiet-window T1/T2 eval sweep across the E7
  pool (autopilot-style fan-out, eval_batch, decision_grade rows) → then apply the reseed
  (baselines_by_tier + per_suite_quality_by_tier + counts + MAD windows from the sweep, stamped
  eval_quality_era: "E7-eval-instrument"). Partial seeding of only the 2 measured suites REJECTED:
  it would either lift the hold against an unrepresentative baseline or recreate cross-era
  comparison for the other 39 suites. The fail-closed hold stays (correctly) until the sweep runs.
  Measured suites available NOW for the sweep's cross-check: math quality (E7c), scoring_verifiers
  (EV-4c).

- [x] ✅ 2026-07-23 RESOLVED through six defect-fix iterations; baselines banked on core_v2 (T1 1.600 rel 0.90) + legacy T2 (1.891 rel 0.92), escalation-off declared **EV-BASELINE-E7 blocked on tier-arm error class (2 attempts, filed 2026-07-23)**: attempt 1
  errored 14/50 (knowledge-tool import failures — five client libs installed, tools now green in
  /health); attempt 2 errored 26/50 with errors CONCENTRATED in code-execution + agentic/heavy
  suites (debugbench/livecodebench/bigcodebench/usaco/tool_use/agentic/long_context all absent
  from the 24 scored; mean_tools_used 0.04 rules out tool-execution). Runner honestly refused
  both (current_eval_degenerate — the reliability floor working). NEXT: (a) wire the per-question
  sidecar into the TIER path (set_question_artifact_dir — calibration/math modes have it, tier
  does not: diagnosis-blocking gap); (b) rerun a small tier draw instrumented, classify the 26 by
  reason; (c) fix the class (suspects: client-side code-execution sandbox availability in the
  tier runner context vs the calibration path that worked, or per-suite deadline shape on heavy
  suites); (d) then the full sweep → reseed. The era-fence hold remains correctly closed.

- [x] ✅ 2026-07-23 (`epyc-orchestrator` `7e767df7`, not pushed) **SCORE-25: implement `f1_list` scorer**: the `tulving_episodic` suite
  (456 rows, whole suite, E7 expansion) declares `scoring_method: f1_list` — item-level F1 over
  parsed lists (distinct from B7 SCORE-24 token-multiset f1). Previously every row errored
  "Unknown scoring method" (honest REL-1 exclusion; ~0.6% of pool, 0-1 per tier draw).
  IMPLEMENTED in `scripts/benchmark/debug_scorer.py::_score_f1_list` — per-item (set-level) F1:
  greedy GT→pred matching, lenient `min(nb_pred,nb_gt)` precision denominator, group-0
  hallucination policy (empty gold + prediction ⇒ 0; empty gold + abstention "None" ⇒ 1). Per-item
  normalization reuses the B7 primitive `_normalize_text` (the one deliberate substitution vs the
  research `tulving_episodic_adapter` NFC normaliser — strictly more lenient, never fabricates a
  match; agrees with the reference on all 1544 cross-check cases). Gold is a JSON list; non-list ⇒
  `ScoringUnavailableError` (EXCLUDED, never False). Offline-verified on all 456 real pool rows
  (456/456 perfect-answer PASS, 0 errors, 0 false positives, 180/180 empty-gold abstention correct).
  ADDITIVE — no existing verdict changes (B7 golden-corpus pin still byte-stable). Golden fixtures
  in `tests/unit/test_debug_scorer_score25_26.py`. NOTE (unowned, left open): kuzu module missing in
  venv (6x ImportError, mutation-graph tools) — install or lazy-degrade.

- [x] ✅ 2026-07-23 (`bb3a9ebb` — bidirectional fence: text fenced off vision roles declaratively, image exempt from veto, vision failures in-band, HTTPStatusError structured) **Routing modality guard + backend HTTPStatusError handling (filed 2026-07-23, from tier
  forensics)**: MemRL routed a long-context TEXT longbench question to worker_vision (:8086) →
  HTTP 400 (context window); `select_initial_route` only forces vision ON image presence, never
  guards non-vision traffic AWAY from VL servers; and `LlamaServerBackend.infer` catches
  Timeout/RequestError but not HTTPStatusError, so 400s surface as raw in-band `[ERROR:` text.
  Fix: (a) modality guard in routing (text → never VL-only servers unless explicitly forced);
  (b) catch HTTPStatusError → structured failure_stage/reason. Non-trivial blast radius — needs
  its own tests; evidence in ev_baseline_e7_tier1 sidecar + agent report (04411baf).
- [x] ✅ 2026-07-23 (`epyc-orchestrator` `7e767df7`, not pushed) **SCORE-26: implement `structural_exact_match` scorer**: longcot_mini
  (402 rows) declares it; previously unknown → honest exclusion. IMPLEMENTED in
  `scripts/benchmark/debug_scorer.py::_score_structural_exact_match` — interpretation DERIVED from
  the suite's rows (golds are canonical JSON str/int/list/dict): parse-then-canonicalize-then-
  compare, NOT string equality. Final-answer anchor = text after the LAST `solution =` marker (B7
  last-occurrence convention; no marker ⇒ False, a task failure not a scorer error); recursive
  canonicalization (dict keys sorted, list order preserved, numeric scalars incl. numeric strings
  collapsed so `391365`==`"391365"`==`391365.0`, non-numeric string case PRESERVED for
  SMILES/FEN, whitespace collapsed); pure structural `==`. Byte-identical to the research reference
  `longcot_mini_adapter.score_structural` across all 2387 cross-check cases; offline-verified on all
  402 real pool rows (402/402 perfect-answer PASS, 0 errors, 0 false positives on wrong/no-marker/
  case-flipped answers). ADDITIVE — no existing verdict changes. Golden fixtures in
  `tests/unit/test_debug_scorer_score25_26.py`.
  **Wholesale-audit result (grep of every `scoring_method` in the 79,480-row pool vs the
  `score_answer` dispatch):** exactly TWO gaps existed — `f1_list` and `structural_exact_match` —
  BOTH now closed. Full gap table (method | rows | suites): `f1_list` 456 (tulving_episodic);
  `structural_exact_match` 402 (longcot_mini). All other declared methods already dispatched:
  `multiple_choice` 44,844, `f1` 12,426, `substring` 9,640, `exact_match` 4,219, `llm_judge` 3,806,
  `code_execution` 3,157, `programmatic` 529 (+ 1 row with no `scoring_method` field, benign). The
  class is closed wholesale — no other suite errors "Unknown scoring method".
- [x] **Hermeticize `tests/unit/test_dispatch_placement_state_machine.py` (filed 2026-07-23)** ✅ 2026-07-29: audited all 11 tests and completed the three-seam isolation (`active_region_holders` + lock acquisitor + `held_regions_by_role`) wherever the placement state machine runs. Added an exact-region helper tied to each synthetic holder set, patched the three residual live-host readers, and replaced the real 150 ms poll wait with deterministic clock/sleep stubs. Five consecutive focused runs: **11 passed** each in ~0.09 s; Ruff and `git diff --check` clean.
- [x] **Cross-role placement-test configuration hermeticity** ✅ 2026-07-29 (discovered during the state-machine audit): `tests/unit/test_dispatch_cross_role_placement.py` now pins its synthetic `worker_general=full_disabled` policy locally for the three DISPATCH-A acceptance tests, rather than depending on the live `burst_prefer_quarters` lineup. This restores the intended all-region-amplifier regression contract without touching production policy. Combined placement validation: **34 passed**; Ruff and `git diff --check` clean.

## Track: batched-edit-parallel-apply
<!-- gate: none -->

> Folded from `handoffs/active/batched-edit-parallel-apply.md` @ `b1bf3f3f7ade` on 2026-11-02 (BRF-T1-F20, route 1a, operator D1/D5; retired row RTG-04 → RTG-02). Body moved verbatim, headings demoted two levels to nest under this track; every open and closed box kept its text and ID.

### Batched Structured Editing + Parallel Apply Fan-out

**Status**: implementation-scoped draft — audit-refined 2026-05-25; production multi-file remediation is now the separate default-off edit transaction. BEP-2/J8 remains useful only as a decision experiment for the legacy structured patchset path, not as the critical remediation gate. 2026-06-28 safety follow-up: the sandbox promotion primitive now refuses live-tree promotion unless verification explicitly passed, closing the unverified-promote gap while keeping sandbox-only deterministic apply usable for analysis/tests. The BEP runner also now fail-closes under-evidenced DCP edits: if a patch touches a file listed in `omitted_context_paths`, preflight blocks the whole set before any sandbox mutation. A follow-up rollback hardening makes live promotion transactional across copy/delete phases: affected live files are backed up before mutation and restored if a later copy or unlink fails. The deterministic BEP-4 fan-out path is now real: independent files within a dependency stage apply concurrently in the sandbox, while declared dependency stages still serialize. Sandbox apply is now atomic on stage failure: affected sandbox paths are snapshotted before deterministic apply and restored if any stage fails, and the failed result clears successful apply metadata so callers cannot mistake a restored sandbox for a partial coherent diff. 2026-07-05 follow-up (`epyc-orchestrator` `8fb8f69a`): the live default-off batch-edit verifier can now stage a lightweight full-tree sandbox and run an explicit `ORCHESTRATOR_BATCH_EDIT_VERIFY_CMD` before promotion; unset env preserves the prior touched-file py_compile gate. 2026-07-06 follow-up (`epyc-orchestrator` `7afadc3d`): verifier-returned-False rows now emit a typed `verify_failed` manifest entry instead of an empty failure list, so BEP-2/J8 telemetry and live nudges can distinguish verifier failures from generic apply failures.
**Created**: 2026-05-25 (via `/research-intake` deep dive of intake-605 Repo Prompt)
**Categories**: agent_architecture, inference_serving, hardware_optimization, tool_implementation
**Source**: intake-605 (Repo Prompt — think-then-act XML edits + parallel sandboxed apply)
**Owning index**: [`routing-and-optimization-index.md`](routing-and-optimization-index.md) P23
**BEP-2 falsification-harness status**: [`bep-dcp-falsification-harness.md`](autopilot-program.md#track-bep-dcp-falsification-harness) (compacted 2026-05-28 — BEP-2 remediation is complete via default-off edit transaction; J8 is optional provenance for the legacy batch-edit path)

#### Objective

Two coupled, CPU-relevant levers borrowed from Repo Prompt's edit pipeline:
1. **Think-then-act batch editing** — let a heavy role spend its full reasoning budget then emit ONE complete structured edit/patch set, instead of interleaving many REPL tool-call round-trips into the reasoning chain.
2. **Parallel apply fan-out** — fan the per-file changes from that edit set out to cheap workers that apply (and optionally verify) them concurrently across NUMA quarters.

#### Strategic frame — why this is sharp on EPYC

- Our Root LM **interleaves** REPL tool calls into reasoning. Each round-trip is a fresh **prefill + decode** — and on EPYC 9655 decode is BW-bound and prefill is pure latency. N interleaved tool calls ≈ N round-trips of overhead.
- RP deliberately makes the reasoner **think to completion, then emit one structured XML edit set** (it exploits GPT-5 Pro's parallel-instance behavior; for us the motivation is round-trip cost, not a model quirk). Fewer round-trips = less cumulative prefill/decode overhead — **a plausibly real latency lever, and cheaply falsifiable.**
- RP then **fans the per-file edits out to cheap CLI agents applying in parallel in a sandbox**. This maps directly onto our proven NUMA concurrency strength: **32×6t concurrent split = +44–58% aggregate** (`project_concurrent_split_throughput`). "Heavy model plans → N cheap workers apply concurrently" is architecturally native to us.

#### What we already have

- **Root LM REPL loop** — interleaved code-gen → execute → observe (the baseline to beat). `epyc-orchestrator/src/README.md` Root LM pattern.
- **Escalation chain** (worker→coder→architect) — quality escalation, NOT a plan/apply split.
- **NUMA concurrency** — 32×6t split, +44–58% aggregate, zero code change (orchestrator config). The substrate for fan-out.
- **Meta-Harness Tier 2** — structured code mutation with `ast.parse()` validation + git-commit-before + sandbox discipline, but limited to a 4-file allowlist — a partial precedent for structured-edit application + safety gating.
- **TOON encoder** — structured-payload encoding for the edit set.

#### RP mechanism to mine

- **Think-then-act**: reasoner emits one **XML edit set** (per-file change list) after reasoning, no mid-reasoning tool calls. RP parses XML → per-file changes.
- **Parallel apply**: parsed per-file changes implemented in parallel by cheap agents in a sandbox; **reviewable diffs, machine-readable patches, sandbox-before-disk, granular accept/reject** (90-min tool timeout tolerates long reasoning).

#### Proposed tasks (implementation-grade after audit)

- [x] **BEP-1 — Batch-edit mode (think-then-act).** ✅ 2026-05-26 (flipped 2026-07-14; wired `ea5f010` behind `features().batch_edit_mode`, pure pieces done+tested). Add a coder/architect mode that produces a complete structured patch set (per-file hunks) in one shot after a bounded evidence-gathering phase, with no edit/apply tool calls interleaved through the reasoning chain. Define the patch schema as deterministic data, not free-form XML-only prose: `base_repo_sha`, per-file `path`, `base_content_sha256`, `operation`, hunks with line anchors or unified-diff body, expected postconditions, and declared cross-file dependencies. Reuse TOON for compact transport if useful, but validate into a typed Python object before touching disk. Default-off feature flag.
- [ ] **BEP-2 / J8 — CPU latency A/B for the legacy structured patchset path.** Head-to-head bench: batch-edit mode vs interleaved Root LM loop on a coding/edit workload — measure round-trip count, total prefill tokens, end-to-end latency, bundle/context size if DCP is enabled, patch-parse failure rate, apply failure rate, verification pass rate, and quality. This no longer gates practical multi-file coding remediation because the separate `force_mode="edit"` transaction has already solved that blocker. Run BEP-2/J8 only if its answer would change whether the legacy `batch_edit_mode` patchset path is kept, retired, or exposed as a narrow task-class knob. First run an offline replay with already-known patches to estimate deterministic apply overhead; then run inference. *(Inference-gated — prepare commands, user runs; standalone llama-bench only for raw speed per `feedback_speed_verify_via_llama_bench`.)*
- **[declined: ws58 2026-11-03 content-review: merged into BEP-2 as its conditional]** **BEP-3 — Autopilot search-space knob.** If BEP-2 is positive, expose batch-vs-interleaved as a StructuralLab boolean (or per-role/per-task-class knob) so autopilot can find where each wins. Wires into autopilot-continuous-optimization search space. The knob must be task-class aware because run-test-iterate tasks may require interleaving while mechanical multi-file edits may benefit from batching.
- [x] **BEP-4 — Parallel apply fan-out.** ✅ 2026-06-28 (flipped 2026-07-14; deterministic stage-local fan-out live; LM-repair lane tracked below). Given a BEP-1 patch set, first try deterministic patch application in parallel by file/process with no additional LM calls. Only if deterministic apply fails should an optional cheap-worker repair lane run, and that lane must be explicitly inference-gated. Collect per-file results; surface a combined reviewable diff plus a machine-readable failure manifest. Reuse the 32×6t concurrent-split harness for CPU parallelism, but preserve a dependency graph: files with declared cross-file ordering constraints or generated-code dependencies must serialize within their group.
- [ ] **BEP-5 — Sandbox-before-disk + granular accept/reject (general).** Generalize Meta-Harness Tier-2's git-commit-before / ast-validate discipline beyond the 4-file allowlist into a general "stage in sandbox/worktree → reviewable diff → independent verify → accept/reject per file or hunk → commit" apply path. Safety-gated — design most carefully (autonomous general code edits). Use base-hash preconditions to reject stale patches, forbid edits outside the declared scope, and always run a whole-repo verification pass after per-file verification because cross-file errors are invisible to isolated checks.
- [x] **BEP-4 telemetry hardening — typed verifier failures.** `apply_patchset_sandboxed()` now records `FailureType.VERIFY_FAILED` when an explicit verifier returns false without raising, preserving the machine-readable failure manifest expected by BEP-4/BEP-2 reports. Focused runner/hook tests passed (`34 passed`) and ruff was clean. ✅ 2026-07-06
- **[declined: ws58 2026-11-03 content-review: optional lane by its own text]** **BEP-4 residual — optional LM-repair lane.** When deterministic apply fails, run an optional cheap-worker repair lane (explicitly inference-gated, opt-in per `feedback_no_concurrent_inference`). Only remaining BEP-4 piece after the 2026-06-28 deterministic fan-out landed.
- [x] **BEP-6 — hashline vs `current_shas`: the granularity gap does not exist** (intake-1148#record, intake-1150#record, intake-1153, intake-1154) ✅ 2026-08-18. The Stage-1 premise — that hashline is line-granularity optimistic concurrency where ours is file-granularity — is **OVERTURNED**. Current hashline validates ONE 4-hex xxHash32 of the whole normalized file (`packages/hashline/src/format.ts:112-121`) and addresses lines by plain number; per-line hashes were removed in `30793c165`/`7c6457652` (May 2026). That is the same property `current_shas` already gives us. Two leniency details worth knowing if we ever revisit: the hash normalizes away trailing whitespace (a stale file differing only in trailing whitespace is ACCEPTED), and a 16-bit tag misses a stale edit ~1 in 65,536. **No change to our apply path is proposed.**
- **[declined: ws58 2026-11-03 content-review: a conditional rule ("if ever proposed")]** **BEP-7 — if an edit-format change is ever proposed, apply two external rules first.** (a) **PAIRING RULE** (intake-1154, aider): a format change without a matching *tolerant applier* is a different intervention — disabling flexible patching produced a **9x increase in editing errors** on aider's own benchmark. (b) **LINE-NUMBER TENSION** (intake-1153, Cursor): line-number emission is named as a tokenizer-level failure mode — a digit run tokenized as one token forces a single-forward-pass commit — and Cursor adopted aider search/replace blocks specifically to remove it. Both predate hashline; omp's shipped format moved *toward* line numbers with no published benchmark of it. Resolve by measurement, not authority. **Decision-relevant magnitude:** against `str_replace`, hashline's measured mean is **+2.97 pp** (14/19 models, sign p=0.064) — inside the benchmark's own 3.75 pp median test-retest spread. The +19.4 pp headline is against `apply_patch`, a baseline that source itself calls broken.

#### Open questions

- Does think-then-act hurt quality on tasks that genuinely need feedback mid-reasoning (run-test-iterate)? Likely task-dependent → hence the autopilot knob (BEP-3), not a global switch.
- Patch-application failure handling: if a fanned-out apply fails verification, retry that file only, or re-plan the whole set?
- BEP-4 vs `feedback_no_concurrent_inference` (no unapproved concurrent inference on EPYC): fan-out apply uses cheap workers concurrently — must respect the per-run-approval rule; design as opt-in, single-user-aware.
- Verification-sensor independence (ties to intake-607 §3.4.4): the per-file verify in BEP-4 should be an independent oracle (tests / type-check), not the applying model grading itself.

#### Audit refinements / missed gaps

1. **Deterministic apply should come before agent fan-out.** RP's "cheap agents apply" pattern is useful, but on our stack the safest and fastest first implementation is a typed patch parser plus deterministic applier. LM repair should be a fallback, not the baseline, otherwise BEP adds both inference risk and nondeterminism.
2. **Structured patch schema needs stale-base protection.** Every file patch must name the base hash it was planned against. If the file changed since planning, reject or re-plan that file; do not fuzzy-apply across unknown edits.
3. **Parallelism is by dependency component, not blindly by file.** Independent files can apply concurrently, but migrations, public API changes, generated code, import graph edits, and test fixture updates can require ordering. The patch schema should let the planner declare dependencies; the applier should also infer obvious conflicts such as two hunks touching the same file.
4. **Verification must have two layers.** Per-file syntax/type checks catch cheap failures early; whole-repo tests/type checks catch cross-file regressions. The final accept gate should be based on the whole-repo layer, not the median per-file result.
5. **Quality failure is not only "patch did not apply."** Track parse failures, over-broad diffs, undeclared file edits, generated-file churn, formatter-only noise, and "passes tests but violates requested behavior." These become BSV behavior-signature inputs.
6. **BEP and DCP should share manifests.** A batch edit planned from a DCP bundle should record the bundle ID and omitted-context manifest. If the patch touches a file that was only `codemap_only` or excluded, flag the plan as under-evidenced before apply.
7. **Rollback should be transactional.** Stage in a worktree or sandbox; never partially copy successful files into the main tree while failed files remain unresolved. Granular accept/reject is a review UX over a coherent staged diff, not piecemeal mutation of production files.

#### Dependencies / cross-cutting

- **delegation-context-preassembly** (sibling) — a pre-assembled bundle feeds a clean batch edit.
- **autopilot-continuous-optimization** — BEP-3 knob; BEP-2 latency/reliability objective.
- **NUMA concurrency** (`project_concurrent_split_throughput`) — BEP-4 substrate.
- **meta-harness (completed ledger)** — Tier-2 structured-mutation precedent → BEP-5 generalization base.
- Honors `feedback_no_concurrent_inference`, `feedback_speed_verify_via_llama_bench`.

#### Key file locations (targets)

- `epyc-orchestrator/src/README.md` Root LM loop / `src/orchestration/` — batch-edit mode (BEP-1).
- `epyc-orchestrator/scripts/autopilot/species/` (StructuralLab) — BEP-3 knob.
- 32×6t concurrent-split config (`orchestrator_stack.py`) — BEP-4 substrate.
- Meta-Harness Tier-2 mutation path — BEP-5 generalization base.

#### Reporting

Update this handoff + routing-index P23 after each BEP task; persist BEP-2 bench results incrementally per `feedback_incremental_persistence`.

#### Deferred live-wiring spec (build before J8) — the change to make once reviewed

The pure pieces are done + tested on main (merged 2026-05-26): `src/batch_edit.py` (PatchSet/validate/conflict/dependency + `apply_file_patch_to_text`), `src/batch_edit_parse.py` (`parse_patchset_from_model_output` + `BATCH_EDIT_INSTRUCTIONS` rider), flag `batch_edit_mode` (default off). What remains touches the production execution core, so it is specified here for a reviewed landing rather than shipped blind.

**1. BEP-4 runner — `apply_patchset_sandboxed(ps, *, repo_root, current_shas, verify_cmd)` (NEW, e.g. `src/batch_edit_runner.py`).** Pure-of-inference; testable with a temp git repo.
- `validate_patchset(ps)`; `check_stale_base(ps, current_shas)` → refuse stale (return failure manifest, do not apply); `detect_conflicts(ps)` → refuse overlaps.
- **Stage in a sandbox (BEP-5)**: `git worktree add` a scratch worktree at the workspace HEAD (preferred — real git, cheap), or copy touched files into a temp dir. NEVER mutate the live tree here.
- For each `dependency_stages(ps)` stage (files in a stage are independent → apply concurrently; stages serialize): apply each FilePatch — `create`/`modify` via `apply_file_patch_to_text`, `delete`/`rename` via filesystem ops — into the SANDBOX only. ✅ Deterministic stage-local fan-out is live as of 2026-06-28; optional LM repair and richer failure manifests remain separate follow-ups.
- **Verify in two layers** (audit #4): per-file syntax/type check, then a **whole-repo** `verify_cmd` (tests/type-check). ✅ Optional explicit verifier gate landed 2026-07-05 in `8fb8f69a`: setting `ORCHESTRATOR_BATCH_EDIT_VERIFY_CMD` switches staging to a lightweight tracked-repo snapshot with touched-file overlay and runs the command in that sandbox after py_compile. The accept gate is the whole-repo layer when configured, not the median per-file result.
- Return a structured result: `{applied:[...], failed:[{path, failure_type}], diff, verify_passed, sandbox_path}`. Failure types (audit #5): `parse`, `stale_base`, `conflict`, `apply_error`, `verify_failed`, `undeclared_file`, `over_broad`.
- **Promotion is separate + explicit**: only on `verify_passed` AND accept does the runner copy the sandbox result into the live tree (transactional — all-or-nothing, audit #7). For the **J8 A/B**, no production promotion is needed: apply-to-sandbox + measure (latency / parse-failure / apply-failure / verify-pass / quality) is the whole experiment.

**2. BEP-1 `_execute_turn` divergence (the flag-gated live hook).** ✅ WIRED 2026-05-26 (`ea5f010`), behind `features().batch_edit_mode` (default-off). Implemented in `src/graph/helpers.py` as `_maybe_batch_edit_turn(ctx, role, raw_llm_output)` (self-contained; called right before code extraction): parse patchset → `apply_patchset_sandboxed` (repo_root mirrors `file_mutation._get_project_root`, `verify_fn` = py_compile plus optional `ORCHESTRATOR_BATCH_EDIT_VERIFY_CMD`) → `promote_sandbox` if `result.ok` → `_finalize_batch_edit` (synthesize terminal FINAL summary). Returns `None` (fall through to REPL) when flag off / no patchset / parse fails; nudge tuple on apply/verify failure (live tree untouched). Prompt rider injected for coder/architect roles only. Default behavior is still touched-file py_compile; whole-repo verifier staging only activates when the env command is explicit. *(Original spec template below, for reference.)* In `src/graph/helpers.py:_execute_turn`, after `code = auto_wrap_final(code)` (~line 687):
```python
if features().batch_edit_mode:
    from src.batch_edit_parse import parse_patchset_from_model_output
    try:
        ps = parse_patchset_from_model_output(raw_llm_output)   # None if no ```patchset block
    except ValueError:
        ps = None   # present-but-malformed → nudge to re-emit, or fall back to REPL this turn
    if ps is not None:
        result = apply_patchset_sandboxed(ps, repo_root=..., current_shas=..., verify_cmd=...)
        return _finalize_batch_edit(state, result)   # synthesize FINAL(summary); NO REPL this turn
    # ps is None → fall through to the normal REPL loop (ZERO behavior change when no patchset)
```
The `BATCH_EDIT_INSTRUCTIONS` rider must be injected into the coder/architect system prompt when the flag is on (via `resolve_prompt(..., variant="batch-edit-v1")` or appended in the prompt builder) so the model emits a patchset instead of REPL code.

**3. Safety invariants that MUST hold even behind the flag** (mitigation policy): default-off; **sandbox-before-disk** — production files untouched until whole-repo verify passes AND accept; stale-base rejection; fall-back-to-REPL on `parse=None`; whole-repo verify is the accept gate; granular accept/reject is review UX over a coherent staged diff, never piecemeal mutation of production files.

#### Post-result conditional workflow + mitigation (BEP-2 / bulk-inference J8)

**2026-11-02 preparation:** The existing `epyc-orchestrator/scripts/benchmark/bep_ab.py` and five-task `data/bep_sandbox` corpus provide an A/B scaffold, but `--stub` writes reference solutions directly and does not exercise the legacy `PatchSet` runner. It therefore cannot supply the required deterministic-apply overhead replay. A scratch-only replay of known typed patches remains to be prepared, including verification of the resulting files. Existing live artifacts include incomplete runs and backend-circuit failures; they are not a J8 verdict. The current harness also needs usable prompt-token accounting, attempt-based parse/apply failure rates, and complete paired coverage before the stated decision rule can be evaluated. The five small synthetic tasks alone do not establish large-repository or general task-class performance. J8 remains an optional decision experiment about the legacy flag, not a gate for the edit transaction. Preparation outputs for the replay and metrics are registered in the handoff session's `awaiting/` directory; integrate them before publishing inference.

Replay and reporting contract: initialize each isolated task from its exact fixture bytes, derive typed patches with base hashes from those bytes, retain declared dependency order, and check both the independent verifier and the exact oracle post-state (including deletions and unchanged files). Ensure the sandbox contains untouched files required by the verifier. Never promote the replay. For J8, preserve the planned task × arm × repetition matrix and mark the gate unevaluable on missing, duplicate, or failed pairs; report matched latency and quality comparisons. Parse and apply rates need request-scoped attempt counts and their respective denominators; missing telemetry or zero eligible attempts is unavailable, not zero failures. Report token usage only when actually supplied, with coverage, and do not infer prefill from prompt length or silently equate prompt tokens with full context cost. The separate metrics patch draft must be reviewed and landed in an authorized orchestrator worktree before a decision-grade run.

Metrics implementation and test plan: [`bep2-metrics-proposal.md`](../../docs/design/bep2-metrics-proposal.md). This is a proposal; instrumentation and the live A/B remain unimplemented and unrun. Settle the handoff's overlapping non-pass threshold boundaries and the latency aggregation before executing the experiment.

**BEP-4 repair readiness (2026-11-02):** The existing failure nudge asks the current model to retry or use ordinary editing; it is not a separately routed cheap-worker repair lane. No repair-specific launcher was identified. A future opt-in repair must bound attempts, route the worker explicitly, treat its output as a new typed patchset, and re-run deterministic preflight, sandbox apply and independent verification without promoting failed results. A repair experiment needs its own scratch workload and decision rule; the J8 A/B launcher does not measure repair. BEP-5 is implementation work, and BEP-3 is conditional on J8, so neither is itself a ready inference row.

J8 is no longer the first critical gate for multi-file coding completion. The direct one-shot ablation and `force_mode="edit"` transaction already proved the practical diagnosis: the blocker was the read->edit->FINAL REPL/BEP protocol, not Qwen3.6 coding capability. Keep J8 as a separate decision experiment for the older structured patchset path:

- **Run J8 if** the result would change whether `batch_edit_mode` is kept, retired, or exposed as a narrow task-class/autopilot knob; if full-file edit transactions become too expensive for large repositories; if structured-patch provenance matters; or if BEP-3 needs task-class evidence.
- **Defer J8 if** the goal is routine coding completion reliability or near-term rollout of the already-built edit transaction. In that case J7, J9, J11, and passive J13-J15 are higher-leverage inference-window consumers.
- ✅ batch cuts end-to-end latency ≥15% AND quality within −1pp AND parse-failure ≤5% AND apply-failure ≤2% → proceed to **BEP-3** (autopilot task-class knob); keep flag available, default-off until BEP-3 localizes where batch wins.
- ⚠️ latency win but quality −1..−3pp OR parse/apply failures 5–15% → do NOT promote; harden BEP-1 prompt/parser; flag stays off; re-run only if structured-patch provenance or full-file-cost concerns remain material.
- ❌ no latency win OR quality < −3pp OR failures >15% → retire the legacy batch-vs-interleaved path; record NEGATIVE here + in intake-605. This does **not** invalidate the shipped edit-transaction remediation.

Mitigation/rollback: flag-off is instant rollback; sandbox isolation means a bad patch never reaches production; on any parse/validate failure the turn falls back to the existing REPL loop (no regression). Operator decision tree mirrored in [`bulk-inference-campaign.md`](eval-tower-program.md#track-bulk-inference-campaign) Package J § "Per-gate conditional workflows".

## Track: bep-dcp-falsification-harness
<!-- gate: none -->

> Folded from `handoffs/active/bep-dcp-falsification-harness.md` @ `b1bf3f3f7ade` on 2026-11-02 (BRF-T1-F20, route 1a, operator D1/D5; retired row RTG-05 → RTG-02). Body moved verbatim, headings demoted two levels to nest under this track; every open and closed box kept its text and ID.

### BEP-2 / DCP-6 Falsification Harness

**Status**: COMPACTED 2026-05-28 - BEP-2 remediation complete; DCP-6 offline replay closed 2026-06-12 and DCP-6a repair code landed on the live orchestrator branch at `2e2e0d3`. The live API launch marker already includes `2e2e0d3` and the reload/attestation primitive (`756c96b`), but the 2026-06-19 running-state attestation is caveated by feature-flag intent diffs (the other two 2026-06-19 caveats — ~~deleted llama-server executables~~, ~~missing `AUTOPILOT_TOOL_SENTINELS` on the API parent~~ — were falsified 2026-08-13 by `mainC`; see the DCP-6 row). The remaining J7 gate is now an operationally clean host-quiet attestation plus the inference run, not a code-provenance reload. Optional J8 provenance remains.
**Created**: 2026-05-26
**Updated**: 2026-07-06
**Priority**: MEDIUM
**Parent index**: [master-handoff-index.md](master-handoff-index.md), [routing-and-optimization-index.md](routing-and-optimization-index.md)
**Completed ledger**: [bep-dcp-falsification-harness-completed-through-2026-05-28.md](../completed/bep-dcp-falsification-harness-completed-through-2026-05-28.md)

#### Executor Start Here

The original BEP-2 read-loop blocker is remediated by the default-off `force_mode="edit"` edit transaction path. Do not rerun the full BEP harness build unless the batch-edit-vs-interleaved comparison is still valuable on its own. DCP-6 is the live independent evaluation path after DCP-4 advisory attach.

#### Outstanding Tasks

- [x] **DCP-6 offline replay**: CLOSED 2026-06-12. Scratch/task-root replay over 5 historical BEP tasks confirmed bundles read task files, not orchestrator files; all 7 existing required files were selected and budgets 500/1000/2000 all fit.
- [x] **DCP-6a content-depth/freshness repair**: branch `fix/dcp6a-context-depth-current` commit `530128b7` changes task-root search/packing so tiny task files are included as full files or padded slices instead of one-line snippets, and populates manifest `content_sha256`. Equivalent code landed on the current live branch at `2e2e0d3`. Focused current-lineage tests: 30 passed after landing.
- [x] **DCP-6b J7 runner safety prep**: ✅ 2026-07-06. Orchestrator `7c84f102` corrects `scripts/benchmark/dcp_j7_ab.py` so default mode is no-inference stub/schema validation; live inference now requires explicit `--real --host-quiet-confirmed` and still refuses while AutoPilot is running. Stub artifact `benchmarks/results/runs/dcp_j7/stub-20260706T033205Z/` validates the result schema and records the expected insufficient decision (`missing_latency_delta`, `quality_not_scored`).
- [ ] **DCP-6 deploy attestation + inference gate**: launch-code provenance is satisfied (`server_launch_git_sha=eeb8cce`, ancestor of `2e2e0d3` and `756c96b`; current API `git_sha=27e09a1`). Orchestrator `670aab4` records the 2026-06-19 `dcp6a-deploy-boundary-check` attestation with GitNexus drift clean and all 6 API workers sampled, but it is not a clean deploy gate because **feature-flag intent diffs remain** and the run still needs an **operationally clean host-quiet window**. Clear that remaining attestation warning at the next host-quiet boundary, then run inference and record top-up rate, token overhead, and success deltas.
  - **Two of the three original caveats are FALSIFIED — do not re-raise them** (falsified by `mainC` 2026-08-13; annotated here 2026-08-16). Original wording: *"...because ~~llama-server executable paths are deleted~~, feature-flag intent diffs remain, and ~~`AUTOPILOT_TOOL_SENTINELS` is absent from the API parent env~~."* Evidence: (a) `/mnt/raid0/llm/llama.cpp/build/bin/llama-server` **exists**, rebuilt 2026-08-10 22:40; (b) `AUTOPILOT_TOOL_SENTINELS` **is set at launch** — `/mnt/raid0/llm/epyc-orchestrator/scripts/server/orchestrator_stack.py:2198` `env["AUTOPILOT_TOOL_SENTINELS"] = "1"`. The 2026-06-19 attestation text is retained above as the historical record; the blocker list is what changed.
- **[declined: ws58 2026-11-03 content-review: optional by its own text]** **J8 optional provenance**: run the legacy batch-edit vs interleaved-REPL A/B only if the batch-edit path itself still needs a keep/kill result. It is no longer a blocker for multi-file coding completion.
- [x] **Cross-handoff cleanup**: keep production rollout decisions in [multi-file-coding-completion-capability.md](benchmark-suites.md#track-multi-file-coding-completion-capability), not here. ✅ 2026-07-29 — this handoff records DCP/BEP evidence and gates only; the multi-file capability handoff owns any rollout decision.

#### Dependency Forks

| Outcome | Next action |
|---|---|
| DCP-6a code is landed but the launch marker predates `2e2e0d3` | Reload at a clean boundary; do not mutate loaded-code provenance or inference measurements mid-run. |
| Launch marker includes `2e2e0d3` but running-state attestation is caveated | Fix/restart into a clean attested state before treating J7 as production-grade evidence. |
| DCP-6a code is deployed and running-state attestation is clean | Proceed to host-quiet inference gate. |
| DCP-6 inference improves success/top-up metrics within token budget | Promote DCP pre-assembly according to [delegation-context-preassembly.md](context-and-token-economy.md#track-delegation-context-preassembly). |
| DCP-6 inference is neutral or regressive | Keep DCP advisory/default-off and document the failure mode. |
| J8 A/B is not needed | Leave J8 as optional provenance; do not spend host-quiet time. |
| J8 is run and batch-edit loses to edit transaction | Close BEP batch mode as superseded; keep edit transaction as the product path. |

#### Completed Scope

| Scope | Result | Ledger |
|---|---|---|
| Phase 0 task-root surface audit | Complete. | [completed ledger](../completed/bep-dcp-falsification-harness-completed-through-2026-05-28.md) |
| Phases 1/1b/1c/2/3 harness build | Complete and dry-run validated. | [completed ledger](../completed/bep-dcp-falsification-harness-completed-through-2026-05-28.md) |
| BEP-2 read-loop investigation | Root cause corrected from model capability to protocol/tooling issue. | [completed ledger](../completed/bep-dcp-falsification-harness-completed-through-2026-05-28.md) |
| BEP-2 remediation | Default-off `force_mode="edit"` edit transaction built, hardened, and validated; rollout tracked elsewhere. | [completed ledger](../completed/bep-dcp-falsification-harness-completed-through-2026-05-28.md) |
| DCP-6 offline replay | Passed scratch-root/file-selection/budget correctness over 5 historical BEP tasks at budgets 500/1000/2000; exposed DCP-6a shallow-slice/hash blocker before inference. | `/mnt/raid0/llm/tmp/dcp6_offline_replay_20260612/summary.json` |
| DCP-6a branch replay + current landing | Branch `fix/dcp6a-context-depth-current` (`530128b7`) passed focused tests and replayed at budgets 500/1000/2000 with 100% file coverage, 100% line coverage, and 0 missing hashes; equivalent code landed on the live branch at `2e2e0d3` with focused current tests passing. | `/mnt/raid0/llm/tmp/dcp6a_current_offline_replay_20260612/summary.json` |
| DCP-6a launch-code provenance check | Live API reported `git_sha=27e09a1` and `server_launch_git_sha=eeb8cce`; `eeb8cce` includes both `2e2e0d3` and `756c96b`. Orchestrator `670aab4` records a caveated running-state attestation: graph drift clean and all 6 API workers sampled, but not a clean inference gate because of deleted llama-server binaries, flag intent diffs, and missing tool-sentinel env. | `/mnt/raid0/llm/epyc-orchestrator/orchestration/attestation/latest.md` |
| DCP-6b runner safety prep | Orchestrator `7c84f102` makes no-inference stub mode the default, keeps real inference behind explicit `--real --host-quiet-confirmed`, and records a fresh schema-only artifact. | `/mnt/raid0/llm/epyc-orchestrator/benchmarks/results/runs/dcp_j7/stub-20260706T033205Z/summary.json` |

#### Key Files

- `/mnt/raid0/llm/epyc-orchestrator/src/edit_transaction.py`
- `/mnt/raid0/llm/epyc-orchestrator/src/api/routes/chat.py`
- `/mnt/raid0/llm/epyc-orchestrator/src/repl_environment/task_root.py`
- `/mnt/raid0/llm/epyc-orchestrator/src/context_discovery.py`
- `/mnt/raid0/llm/epyc-orchestrator/scripts/benchmark/bep_ab.py`
- [delegation-context-preassembly.md](context-and-token-economy.md#track-delegation-context-preassembly)
- [batched-edit-parallel-apply.md](autopilot-program.md#track-batched-edit-parallel-apply)
- [multi-file-coding-completion-capability.md](benchmark-suites.md#track-multi-file-coding-completion-capability)
- [bulk-inference-campaign.md](eval-tower-program.md#track-bulk-inference-campaign)

#### Reporting Instructions

For DCP-6, update this handoff, [delegation-context-preassembly.md](context-and-token-economy.md#track-delegation-context-preassembly), [bulk-inference-campaign.md](eval-tower-program.md#track-bulk-inference-campaign), and the progress log with the replay/inference commands, metrics, and decision. For J8, explicitly state whether the run is provenance-only and whether it changes any production recommendation.

## Track: evidence-plane-event-sourcing-and-narrative
<!-- gate: none -->

> Folded from `handoffs/active/evidence-plane-event-sourcing-and-narrative.md` @ `b1bf3f3f7ade` on 2026-11-02 (BRF-T1-F20, route 1a, operator D1/D5; retired row RTG-13 → RTG-02). Body moved verbatim, headings demoted two levels to nest under this track; every open and closed box kept its text and ID.

### Evidence Plane — Event-Sourced Runtime + Narrative Regeneration

**Status**: W7/W8 landed on live branch 2026-06-13; W1a read-only journal archive diagnostics landed in `epyc-orchestrator` `9cc97bf`, W1 archive-authority preflight drift audit landed in `0e5e796`, W1 read-only archive drift report CLI landed in `20b082f`, W1 archive repair CLI landed in `5587e33`, W1 journal-authoritative runtime archive reads/cache removal landed in `3c3e016`, the live empty-journal lifecycle-save fallback to legacy `archive.save(state)` was retired in `6da83d0`, the legacy public `ParetoArchive.save()` state-cache API was removed in `f7a917c`, the generic public raw payload loader was narrowed to internal journal-authority replacement in `5843190`, `autopilot.py digest` gained explicit archive-source diagnostics in `26cc34f`, `autopilot.py plot` gained matching archive-source diagnostics in `d1a6229`, and `/dashboard/api/pareto` gained explicit `archive_authority` / legacy state-cache fallback diagnostics in `bdb1867`; the live repair/cache removal was executed after AutoPilot absence was verified, and strict archive-authority report now passes with `status=match` and `state_archive_cache=absent`; W3 journal snapshot event substrate landed in `5561f48` with read-only replay diagnostics in `26d875e`, default-dry-run builder CLI in `5035987`, one verified append-only live snapshot event through trial `804`, and bounded replay readiness reporting in `48d0ec1`; W4a baseline promotion ledger events landed in `0202835`, with read-only dashboard/replay/status/report evidence consumers in `5f6c81e`, `47c75de`, `3c5d98b`, diagnostic reconciliation hardening in `32b4497`, baseline fold cutover dry-run readiness in `b7e7321`, read-only baseline authority reporting in `3cd8116`, and generated system-card baseline folding in `2fcbcf7`; W5 generated STM preview scaffold landed in `fbef7a8` with explicit journal-path hardening in `e5205b1`, live prompt-memory generation landed in `cfa8525`, legacy mutable STM API cleanup landed in `3c3e016`, and generated STM runtime-artifact policy landed in `91d074d`; W2 append-only supersession substrate landed in `3ff7af4`, `scrub_journal.py` defaults to append-only supersession events in `702d785`, read-side supersession folding for archive/dashboard/replay reconstruction landed in `f08fabd`, prompt/trust read views landed in `73e569a`, Pareto recovery re-import now respects supersessions in `41d5e80`, distillation reads the folded journal view in `005e836`, PromptForge failure context filters superseded failures in `394c1bc`, dashboard progress/GEPA journal views fold supersessions in `cdeedcd`, offline analytics fold supersessions in `d21bbee`, preflight blacklist audit folds supersessions in `965f507`, the legacy in-place scrub path was retired in `2cb89f8`, and the gate-lock narrative scrubber now fails closed in `70e961c`; W6 strategy-retrieval/evidence guards landed in `0f07644`, `8a98868`, `e78a380`, `433f6e8`, `327218c`, `de07542`, `5544a6e`, `b5e71f8`, `c9871a8`, and `15f3ec8`, journal-keyed frontier strategy projection landed in `887de60`, and the frontier generated-projection audit/sync closed in `d9dd372`; W1/W4/W6 still open overall for baseline-as-fold live authority evidence/cutover, W4 cadence/fresh-draw finalization, post-repair restart preflight, any future archive-source consumer audits, and coordination with N2 ledger/readiness.
**Created**: 2026-06-12
**Priority**: HIGH — sequenced after [evidence-plane-ledger-and-sequential-verdicts.md](autopilot-program.md#track-evidence-plane-ledger-and-sequential-verdicts); the adoption gate is already MET (T2 drift observed, see Why)
**Spec**: [fable5-findings-01-impl-plan.md](../completed/fable5-findings-01-impl-plan.md) Phase 3 + Phase 4, and [fable5-findings-01-measurement-and-integrity.md](../completed/fable5-findings-01-measurement-and-integrity.md) §2.1/§2.4/§4 — read before claiming any waypoint
**Related**: [evidence-plane-instrument-repair.md](autopilot-program.md#track-evidence-plane-instrument-repair) · [autopilot-continuous-optimization.md](autopilot-program.md) · [../../MEASUREMENT.md](../../MEASUREMENT.md) §5 (the append-never-edit retroactivity rule this implements at runtime)

**Current snapshot — 2026-06-27T08:00Z**: the controlled v6-era restart window appended the guarded baseline seed event with exact readiness guards (`trial_counter=970`, `journal_max_trial_id=969`). Post-append readiness reports the baseline ledger fold ready, but runtime authority remains default-off behind the explicit `baseline_ledger_authority_enabled` gate. AutoPilot recovered stale trial `970` by journaling it as `autopilot_killed_mid_trial`, resumed detached at trial `971` with `--max-trials 2000` (PID `86308`, log `/mnt/raid0/llm/tmp/autopilot_v6_resume_detached_20260627T075406Z.log`), and is collecting W6 audit rows. Do not remove `baseline_state` or enable baseline ledger authority until the aggregate strict gate passes with `--require-seq-cutover --require-w6-audit`.

**Current authority refresh — 2026-07-04T20:25Z**: supersedes the
2026-06-27 baseline-authority warning above. Live read-only reports now show
the event-sourced authority path is active and strict restart-ready:
`restart_readiness_report.py --json --strict` reports `restart_ready=true`,
`archive_authority.ok=true`, `archive_authority.state_archive_present=false`,
snapshot replay `restart_readiness=tail_fold_ready`, and
`baseline_authority.status=ledger_authoritative` with
`authority_enabled=true`, `authority_source=ledger_fold`,
`state_baseline_present=false`, `event_count=1`, and no blockers. The archive
source surface audit still passes (`failed_count=0`). Treat W1 archive-authority
cutover and W4 baseline-authority cutover as live; remaining A8 work is W3
ongoing snapshot-tail hygiene, W6/future strategy-consumer audits, and N2/W8
promotion-evidence coordination rather than another baseline/pareto authority
flip.

**W6/W8 gate refresh — 2026-07-05T14:45Z**: W8's apparent stale-replay blocker
was a report-side artifact, not a live candidate-generation failure. Orchestrator
`6a1d5d2f` keeps unreplayable historical numeric candidates out of
`stale_accumulating_candidates` while preserving them as diagnostics. Live W8
now reports replay-eligible candidate `4b6b454ea4f884fd`,
`stale_accumulating_candidate_count=0`, and no replay-concentration warning. The
remaining strict Fable blocker is W6 audit clearance after the current-era trial
`1168` vs `1165` divergence (`core_delta=+0.18`, `audit_delta=-0.9`), with `29`
clean audited rows required to age the alarm out. Do not weaken W6 gaming
semantics unless future evidence shows a measurement artifact; current evidence
is a real audit drop, unlike the earlier flat-audit quantization issue.

**Snapshot-tail refresh — 2026-07-04T23:07Z**: W3 tail hygiene advanced while
AutoPilot trial `1142` was mid-eval, following the same completed-row snapshot
pattern used for the 2026-06-20 live append. `journal_snapshot_create.py --append --json`
appended a `journal_snapshot` event to
`orchestration/autopilot_journal_1.jsonl` through completed trial `1141`
(`trial_count=1021`, `ledger_event_count=6`, parent snapshot
`9d94145a0869...`, snapshot hash `69fcee75fd5c...`). Immediate replay
validation with `journal_snapshot_replay.py --json --allow-tail-fold --strict`
reported `bounded_replay_readiness=current`, `strict_readiness=current`,
`hash_status=match`, `journal_max_trial_id=1141`, and `tail_trial_count=0`.
Future W3 work is bounded-startup/ongoing-tail monitoring as trials accrue, not
another catch-up snapshot for the current shard.

**W6 consumer audit refresh — 2026-07-04T23:13Z**: main-thread and
`gpt-5.4-mini` read-only sidecar audit found no actionable raw StrategyStore
consumer remaining in live planner/action paths. Active consumers use
`retrieve_for_journal(..., journal=...)`, `retrieve_conventions(...,
journal=...)`, or store-owned compression/staleness/distillation selectors with
`journal` / `excluded_trial_ids`; the residual direct SQL surfaces are the
operator-seeded planner-hint path, legacy fallback branches that fail closed
when journal-aware selectors are required, and dashboard read-only graph
inspection. Focused validation passed for per-turn planner hint refresh,
operator-seed visibility, non-operator unprovenanced filtering, and convention
denylist/suppression behavior. Treat W6 as audit-current; future W6 work should
be triggered by a new StrategyStore consumer or regression, not by a generic
repeat migration pass.

#### Why

The journal already rebuilds the full archive shape (`journal_reconstruction.py`) but only for
the dashboard; the runtime dual-writes via a second path that has drifted: the 2026-06-12
read-only check found live T2 archive {363} vs journal reconstruction {363, 367} — trial 367
is frontier-worthy under the shared policy yet absent from the runtime archive (findings-01
§4). The event-sourcing case is no longer hypothetical. Phase 3 makes the journal the single
append-only ledger (archive/baseline = recomputed folds, scrubs = supersession events,
backups/rewinds obsolete); Phase 4 makes every narrative store a regenerated,
provenance-checked view so refuted stories cannot re-enter the planner.

#### Waypoints

- [x] **W1 — single commit point** ✅ 2026-07-14 (audit: 2026-07-04 refresh — archive_authority.ok=true, state_archive_present=false, cutover live) (impl 3.1, ~3–4 days): trial finalization writes ONE journal row; `ParetoArchive` becomes an in-memory view via `reconstruct_archive_from_journal_rows` at startup; delete `ParetoArchive.save`'s read-merge-write; `state.json` drops the `pareto_archive` key (legacy-read fallback one release). **W1a diagnostics scaffold landed 2026-06-14** in `epyc-orchestrator` `9cc97bf`: `ParetoArchive.from_archive_payload(...)` and `pareto_archive_from_journal_rows(...)` now build a read-only ParetoArchive-compatible view from append-only journal reconstruction, and read-only snapshots reject `update`, `upsert_representative`, `save`, `load`, and `mark_production_best` so diagnostics cannot mutate or promote state. `autopilot.py status`, `autopilot.py report`, and `autopilot.py digest` accept explicit `--archive-source state|journal-current-run|journal-all`; digest snapshots also render the selected archive source. The live loop, safety gate, and promotion paths are unchanged. The stale `cmd_digest` call to `archive.load(state)` is now backed by a real mutable `ParetoArchive.load()` method. The generic public `ParetoArchive.load_archive_payload()` compatibility surface was removed in `5843190`; AutoPilot's journal-authority helper now uses internal `_replace_from_archive_payload()` only. **Archive authority preflight audit landed 2026-06-14** in `0e5e796`: `scripts/autopilot/preflight_audit.py` now adds an `Archive Authority Drift` section before inference/e2e seeding, loads `autopilot_state.json` plus `autopilot_journal.jsonl`, reconstructs the append-only journal archive, compares normalized state-vs-journal archive views, checks snapshot replay readiness is not `prefix_invalidated`, and fails preflight on archive drift or journal max trial ID at/above `state.trial_counter`. **Archive authority drift report landed 2026-06-14** in `20b082f`: `scripts/autopilot/archive_authority_report.py` is a no-inference read-only CLI that reuses the preflight archive-authority diagnostic, emits Markdown or JSON, supports `--strict` for restart gates, reports entry-ID deltas, frontier-ID deltas, and common-entry semantic mismatches, and keeps snapshot readiness separate from archive drift status. The same commit tightened preflight's archive projection to compare archive semantics (`trial_id`, objectives, `eval_tier`, and meaningful representative metadata) instead of display/provenance fields such as `git_tag`, `species`, `timestamp`, or default `n_reproductions`. Live no-inference report evidence after the commit still showed restart-blocking drift: `status=drift`, `state_trial_counter=805`, `journal_max_trial_id=804`, `state_entries=259`, `journal_entries=257`, `state_frontier=7`, `journal_frontier=12`, snapshot readiness `current` / replay `archive_prefix_match`; deltas included 129 state-only entries, 127 journal-only entries, state-only frontier `[256]`, journal-only frontier `[77,118,146,166,190,207]`, and common-entry semantic mismatches on trials `569`, `668`, `680`, and `804`. `--json --strict --max-examples 3` exited 1 on that live drift as intended. **Archive authority repair CLI landed 2026-06-14** in `5587e33`: `scripts/autopilot/archive_authority_repair.py` is dry-run by default, reconstructs `pareto_archive` from append-only journal replay, preserves surrounding `autopilot_state.json` operational fields, creates a timestamped backup before `--write`, writes atomically through `state_store.save_state`, supports `--expect-trial-counter` to reject stale live writes, and postchecks repaired state through the archive authority report before declaring write readiness. Live dry-run evidence before writing reported `Archive repair status: ready`; before drift was `state_entries=259`, `journal_entries=257`, `state_frontier=7`, `journal_frontier=12`; projected postcheck aligned to `state_entries=257`, `journal_entries=257`, `state_frontier=12`, `journal_frontier=12`. The live repair was then executed after AutoPilot PIDs `3810659` and parent `3810657` were stopped and verified dead: `archive_authority_repair.py --write --expect-trial-counter 805 --max-examples 8` reported `Archive repair status: written`, created backup `orchestration/autopilot_state.json.bak-archive-repair-20260614T020530Z`, and postchecked `match` with `state_entries=257`, `journal_entries=257`, `state_frontier=12`, `journal_frontier=12`. Post-repair `archive_authority_report.py --strict --max-examples 8` exited 0 with no entry/frontier deltas or common-entry mismatches, `audit_archive_authority()` returned true with 685 rows loaded, `python3 -m json.tool orchestration/autopilot_state.json` passed, and clean `pgrep` showed no AutoPilot process. This repairs the current state projection but does not change live runtime archive-fold authority; W1 cutover remains open. Acceptance remains: the dual-write drift check passes by construction when the runtime load path itself is journal-backed.
- [x] **W2 — supersession events** (impl 3.3, ~1–2 days): new row type `{type: supersession, target_trial_ids, fields, reason, policy_version, actor}`; `scrub_journal.py` and every future rewind/purge become appends; rewrite-in-place removed from the default workflow. **Partial substrate landed 2026-06-13** in `epyc-orchestrator` `3ff7af4`: journal load/store preserves non-trial ledger rows, `append_supersession_event` writes append-only supersession metadata, and `scrub_journal.py --append-event` can add a supersession event without mutating existing trial rows. **Append-only scrub default landed 2026-06-14** in `702d785`: `scrub_journal.py` appends supersession events by default and `--append-event` remains a compatibility no-op. **Read-side folding landed 2026-06-13** in `f08fabd`: `journal_reconstruction.py` applies append-only supersession field overrides in memory for archive/dashboard/replay reconstruction, ignores event rows when selecting latest-run metadata, and emits `supersessions` archive metadata while leaving persisted trial rows unchanged. **Planner-facing journal reads landed 2026-06-13** in `73e569a`: `ExperimentJournal.entries_with_supersessions()` provides a non-mutating runtime read view, and `trustworthy_entries`, `trustworthiness_score`, `summary_text`, and `insights_text` now fold supersession events before building planner context. **Recovery read coverage landed 2026-06-13** in `41d5e80`: `_maybe_reimport_pareto_from_journal` uses the supersession-aware entry view when available, so crash recovery does not re-import a raw-clean trial that an append-only event marks bug-corrupted. **Strategy distillation read coverage landed 2026-06-13** in `005e836`: `_action_distill_knowledge` passes the supersession-aware journal view to `EvolutionManager.distill()` when available, so supersession corruption tags are not ignored when distilling outcomes into persistent StrategyStore memory. **PromptForge failure-context coverage landed 2026-06-13** in `394c1bc`: `recent_failures()` folds supersession events by default and excludes superseded `bug_corrupted_by` failures from mutation context, with `exclude_bug_corrupted=False` retained as the raw audit opt-out. **Dashboard journal-view coverage landed 2026-06-14** in `cdeedcd`: `fold_supersession_events()` is public and `dashboard.py` routes `/dashboard/api/autopilot_progress` and `/dashboard/api/gepa` through `_effective_journal_trial_rows()`, dropping non-trial event rows and excluding rows superseded as `bug_corrupted_by` from GEPA recent trials. **Offline analytics coverage landed 2026-06-14** in `d21bbee`: `paired_stats.py`, `item_analytics.py`, and `task_rate_goodput_replay.py` fold append-only supersession events at journal read/report boundaries and drop non-trial event rows from analysis inputs. **Preflight blacklist-audit coverage landed 2026-06-14** in `965f507`: `audit_blacklist()` folds append-only supersession events before collecting corrupted trial IDs, so stale blacklist entries sourced from trials later superseded as corrupted are caught by preflight. **Legacy rewrite retirement landed 2026-06-19** in `2cb89f8`: `scrub_journal.py --rewrite-in-place`, the JSONL/TSV rewrite helper, and the unused `ExperimentJournal.apply_scrub()` mutator are gone; the negative test now proves the retired flag is rejected and raw trial rows remain immutable. **Gate-lock narrative scrubber retirement landed 2026-06-19** in `70e961c`: `scripts/maintenance/scrub_gatelock_narrative.py` is now a fail-closed tombstone that exits 2 and points operators to append-only `scrub_journal.py` plus strict archive-authority validation, instead of mutating the journal, generated STM, strategies DB, FTS, or FAISS mirrors in place.
- [ ] **W3 — rotation snapshots** (impl 3.2, ~1 day): journal segments per 1000 trials chained with a snapshot row (full reconstructed view + policy version); rebuild = snapshot + tail fold. **W3a snapshot-event substrate landed 2026-06-14** in `epyc-orchestrator` `5561f48`: `ExperimentJournal` supports typed append-only `journal_snapshot` ledger rows with `through_trial_id`, `policy_version`, `actor`, `parent_snapshot_hash`, computed `snapshot_hash`, and a snapshot payload; `journal_snapshot_events()` and `latest_journal_snapshot_event()` return loaded snapshot events in ledger order. Snapshot rows do not count as trials and do not advance `next_trial_id`. **Read-only replay diagnostics landed 2026-06-14** in `26d875e`: pure `src/autopilot_core/journal_snapshot_replay.py` plus standalone `scripts/autopilot/journal_snapshot_replay.py` validate the latest `journal_snapshot` hash, count tail trials, compare a snapshot archive payload to current-policy prefix replay when an archive payload exists, and warn when post-snapshot supersession events target the snapshot prefix. **Default-dry-run builder landed 2026-06-14** in `5035987`: `scripts/autopilot/journal_snapshot_create.py` reconstructs the current full-journal archive payload, reports readiness, refuses duplicate/up-to-date snapshots unless `--force`, and appends a `journal_snapshot` only with explicit `--append`. One live append-only runtime event was then created with `python3 scripts/autopilot/journal_snapshot_create.py --append`, covering trial `804` with hash prefix `6b48abcf6923` at about `2026-06-14T01:25:24Z`; `journal_snapshot_replay.py --strict` verified `1` snapshot event, hash `match`, replay `archive_prefix_match`, and `tail_trials=0`. **Bounded replay readiness reporting landed 2026-06-14** in `48d0ec1`: snapshot replay diagnostics now report `bounded_replay_readiness` as `current`, `tail_unverified`, `prefix_invalidated`, or `not_ready`, while preserving hash and replay status separately; strict CLI mode now requires readiness `current`, not merely archive-prefix match. **Current-snapshot authority consumption landed 2026-06-20** in `f945f15`: `_journal_archive_payload_for_authority()` now uses the latest snapshot archive directly when `archive_payload_from_current_snapshot()` proves the snapshot is hash/prefix verified and has no post-snapshot tail; otherwise it keeps the existing full-journal replay path. **Representative replay-state snapshot live append completed 2026-06-20**: after `0c3c25ed`, a controlled append-only runtime snapshot was created through trial `892` while trial `893` was mid-eval, with hash `235ca94c4855`, parent `389faac1994f`, replay-state version `representative-replay-state-v1`, and `37` clusters. `journal_snapshot_replay.py --strict` verified `3` snapshot events, hash `match`, replay `archive_prefix_match`, `bounded_replay_readiness=current`, and `tail_trials=0`. The already-running W4/W6 AutoPilot process still predates the consumer code and was not restarted; the next controlled restart can consume the current snapshot directly, while future post-892 tails still rely on the bounded tail-fold path. Remaining acceptance: demonstrate bounded startup cost after a controlled restart and keep verifying post-snapshot tails as new trials accrue.
  - 2026-09-16: **segment chaining landed** in `epyc-orchestrator` `b7a61c02` (branch `sub/autopilot-evidence-20260916`, merged as orchestrator `753343f5`).
    - **Segment snapshots.** `ExperimentJournal.record()` now appends a `journal_snapshot` row (policy `journal-segment-snapshot-v1`, actor `experiment_journal.segment_rollover`) as the LAST row of the closing shard whenever the next trial starts a new 1000-trial segment. The row is parented on the previous snapshot hash and carries `snapshot.segment` metadata. It fails open, is skipped when a snapshot already covers the segment, and can be turned off with `segment_snapshots=False`. The build costs about 3.7 s per rotation on the live journal (dry run, 1372 trials).
    - **Chain verification.** `verify_snapshot_chain()` checks hash, parent linkage and monotonic `through_trial_id` across the whole chain. The live chain is `ok`: 7 events, head at trial 1458.
    - **Proof.** `tests/unit/test_journal_segment_snapshots.py` (10 tests) shows snapshot + tail fold == full fold on a 3-segment fixture, with and without a tail supersession.
    - **Two defects fixed.**
      - Prefix replay counted post-snapshot tail-only supersessions, so it reported false `archive_prefix_drift`.
      - The authority path consumed any verified snapshot whose `objective_policy` matched, ignoring `exclude_before_ts` and deinflation. An unscoped snapshot could therefore have handed pre-epoch entries to the live frontier. The new `_snapshot_scope_matches()` fails closed.
    - **Scoped snapshots**, follow-up `06cf82dc`.
      - Segment snapshots are folded under the live authority scope: objective policy plus `pareto_exclude_before_ts`. The scope is synced from state at startup and before each trial write, and active deinflation disables snapshots.
      - Diagnostics verify a prefix under the scope the snapshot recorded in its own payload.
      - The tail fold honours the recorded epoch and returns `None` if a tail row predates it.
      - Tests (14 total) cover a scoped snapshot verifying and being consumed under a matching live scope, and a mismatched scope falling back to full replay.
    - **Live finding (read-only).** The latest live snapshot, through trial 1458 (`terminalize_e8_speed_frontier.py`, 2026-07-27), is `prefix_invalidated`.
      - Under scope-aware replay, the only remaining difference is `t0_audit` (2 entries in the snapshot vs 0 in the replay). The terminalizer payload is not a pure fold, so the invalidation is correct.
      - Live startup therefore stays on full replay.
      - The live state epoch (`pareto_exclude_before_ts=1786378983`, 2026-08-10) is later than every journaled trial (the last is 2026-08-09, #1505), so the live frontier is currently empty of journal rows either way.
    - **Remaining acceptance.** The post-restart bounded-startup demonstration after the first automatic segment snapshot.
    - **Deploy.** Takes effect at the next AutoPilot restart; the first automatic segment snapshot lands at the 1999 → 2000 rollover.
- [x] **W4 — baseline as fold + acceptance suite** ✅ 2026-07-14 (audit: baseline_authority.status=ledger_authoritative, authority_enabled=true, state_baseline_present=false) (impl 3.4–3.5, ~2 days): `Baseline` computed at load; `update_baseline` becomes a `baseline_promotion` ledger event; YAML = cold-start seed only. **W4a evidence-event scaffold landed 2026-06-14** in `epyc-orchestrator` `0202835`: `ExperimentJournal` now has generic `append_ledger_event(...)` / `ledger_events(...)` plumbing plus typed `baseline_promotion` rows (`append_baseline_promotion_event(...)`, `baseline_promotion_events()`). Baseline-promotion rows have no `trial_id`, do not count as trials, do not advance `next_trial_id`, and do not affect supersession folds. AutoPilot appends the event only when the existing `SafetyGate.update_baseline(...)` result has `updated=True`; acceptance/rejection logic is unchanged. The append occurs after `archive.save(state)` and `save_state(state)` and is wrapped so event-write failures cannot change live decisions. Follow-on diagnostics expose those append-only events without changing authority: `5f6c81e` adds a current-run `baseline_promotions` summary to `/dashboard/api/pareto`, `47c75de` renders a `Baseline Promotion Evidence` table in `task_rate_goodput_replay.py` for promotion events whose source trial is present in the effective folded replay rows, and `3c5d98b` adds read-only `autopilot.py status`/`report` summary lines that fold to the latest `baseline_promotion` event snapshot and compare it with `autopilot_state.json:baseline_state`. **Diagnostic hardening landed 2026-06-14** in `32b4497`: reconciliation now lives in pure `src/autopilot_core/baseline_ledger.py`, returns structured statuses (`no_events`, `unreconstructable`, `missing_state_baseline`, `match`, `drift`), uses append-order latest valid snapshot semantics, compares canonicalized state snapshots, and reports event-quality mismatches as warnings only. **Baseline fold cutover dry-run readiness landed 2026-06-14** in `b7e7321`: `BaselineLedgerReconciliation` now includes `cutover_ready` and `cutover_blockers`; dry-run readiness is true only when every `baseline_promotion` event has a usable `baseline_state` snapshot, the append-order ledger fold matches current state baseline, and no warning diagnostics remain. **Read-only baseline authority report landed 2026-06-14** in `3cd8116`: `scripts/autopilot/baseline_authority_report.py` reports state-vs-ledger-fold readiness in text or JSON, supports `--json --strict`, exits 1 when strict mode is not cutover-ready, exits 2 for missing/non-object state or journal load errors, and writes nothing. The CLI uses `preflight_audit` defaults / `_load_jsonl` plus `src.autopilot_core.baseline_ledger.reconcile_baseline_ledger`. Live smoke on the current journal returned `ok=false`, `status=no_events`, and blocker `no baseline promotion events; YAML remains cold-start seed`, which is expected because no live baseline-promotion events exist yet. Malformed/incomplete events are tolerated by reporting but block dry-run cutover readiness. **Generated system-card baseline fold landed 2026-06-19** in `2fcbcf7`: when `autopilot_state.json:baseline_state` is absent, `scripts/autopilot/gen_system_card.py` folds append-only `baseline_promotion` events through `reconcile_baseline_ledger()` and uses the folded state as the card baseline source only when the fold is cutover-ready; otherwise it falls back to the YAML cold-start seed. **Runtime startup baseline fold landed 2026-06-20** in `c3d1b26`: AutoPilot startup now seeds `SafetyGate` from `baseline_state` while present, then from the append-only promotion ledger only when the same reconciliation rules are cutover-ready, otherwise falling back to the YAML cold-start path. This commit was not restarted into the already-running W4/W6 accrual process to avoid contaminating the evidence window. `autopilot_state.json:baseline_state` remains live authority until readiness/cutover evidence exists and the persistence helper has removed it through `apply_baseline_ledger_authority()`; W4 remains open for live promotion evidence, cutover proof, and cadence/fresh-draw finalization. Acceptance remains: kill -9 mid-trial → WAL recovery reproduces identical views; full-journal replay (existing `bug_corrupted_by` tags as implicit supersessions) reproduces today's T1 frontier.
- [x] **W5 — STM as generated view** (impl 4.1, ~1–2 days, needs W1): `short_term_memory.md` rebuilt each trial from the ledger (trustworthy last-N, hypotheses with falsifiers + provenance trial-ids); read-modify-write path deleted; per-section render budgets (kills mid-word truncation structurally). **Pre-cutover scaffold landed 2026-06-14** in `epyc-orchestrator` `fbef7a8`: `scripts/autopilot/stm_generated_view.py` renders a journal-derived read-only preview from folded entries, mirrors AP-22 trust filters by excluding bug-corrupted, non-`ok`, and learning-excluded rows, sanitizes legacy failure text, splits optimization directions deterministically, applies section and total budget caps, and prints to stdout only. **Journal-path hardening landed 2026-06-14** in `e5205b1`: an explicit missing or non-directory `--journal-dir` now exits with code `2` before constructing `ExperimentJournal`, so a typo does not create directories; valid existing explicit journal directories still render. **Live prompt-memory generation landed 2026-06-18** in `cfa8525`: AutoPilot startup, planner prompt construction, and post-journal trial finalization now call `ShortTermMemory.refresh_from_journal(...)`, which renders the folded append-only journal view and atomically writes the generated projection. **Legacy mutable STM cleanup landed 2026-06-18** in `3c3e016`: `TrialOutcome`, `ShortTermMemory.update()`, and the read-modify-write accumulator internals were removed; `ShortTermMemory` now only maintains the generated journal projection. **Tracked-runtime-artifact policy landed 2026-06-18** in `91d074d`: the generated projection moved to ignored `orchestration/autopilot_short_term_memory.md`, and tracked `scripts/autopilot/short_term_memory.md` was removed from source control.
- [ ] **W6 — strategy provenance** (impl 4.2, ~2 days, needs W1): `strategies.db` rows gain `evidence_trial_ids`; `retrieve()` filters rows citing superseded/excluded trials (extend the AP-28 staleness pattern, ledger-keyed); distill must cite trial-ids per insight or the insight is skipped/quarantined. Partial read-side guards: `005e836` makes `distill_knowledge` consume `entries_with_supersessions()` when available; `0f07644` makes `StrategyStore.retrieve()` accept `excluded_trial_ids` and derives initial exclusions from the folded journal view; `8a98868` adds the additive SQLite `evidence_trial_ids` column, stores analyzed/distilled trial IDs on StrategyStore entries, filters retrieval when any evidence trial intersects the folded journal exclusion set, broadens `_build_mutation_context` exclusions to corrupted, non-`ok`, explicitly excluded, and learning-excluded folded rows, and falls back to `source_trial_id` for legacy rows with empty evidence lists. **Per-insight evidence requirement landed 2026-06-14** in `e78a380`: the distillation prompt requires each insight to carry `evidence_trial_ids`; `EvolutionManager.distill()` validates those IDs against the analyzed rows, permits only the single-row fallback for one-row distillations, skips ungrounded multi-trial insights, and returns `status: skipped` if no grounded insight remains. **Promotion evidence propagation landed 2026-06-14** in `433f6e8`: `KnowledgeDistiller` reads evidence IDs from source rows and carries them through raw-to-pattern and pattern-to-convention promotions, so retrieval quarantine by excluded evidence IDs also hides promoted pattern/convention rows whose underlying evidence is superseded or excluded. **Folded evidence-view centralization landed 2026-06-18/19** in `327218c` and `de07542`: `excluded_strategy_evidence_trial_ids()` is the shared quarantine helper, `StrategyStore.retrieve_for_journal()` computes exclusions from the supplied journal, and `_build_mutation_context()` routes through that wrapper with a legacy-test-double fallback. **Convention audit-table evidence propagation landed 2026-06-19** in `5544a6e`: dedicated `strategy_conventions` audit rows now store, migrate, list, and propagate `evidence_trial_ids` during MDL compression and raw-to-pattern promotion. **Legacy quarantine fallback fail-closed behavior landed 2026-06-19** in `15f3ec8`: `KnowledgeDistiller` and `StructuralLab` now raise if a caller supplies a journal or explicit excluded-trial set but the injected store lacks `strategy_entries_for_distillation()` or `strategy_rows_for_compression()`, so journal-aware promotion cannot silently fall back to raw SQL. **Journal-keyed frontier strategy projection landed 2026-06-19** in `887de60`: AutoPilot no longer writes B1 frontier strategy rows before `journal.record()`; it records the `JournalEntry` first, then projects the row through deterministic `StrategyStore.store_frontier_journal_entry()` IDs (`journal-frontier-trial-<id>`), skipping non-frontier, non-`ok`, bug-corrupted, or learning-excluded rows and making retry/restart projection idempotent. **Frontier strategy generated-projection audit/sync landed 2026-06-19** in `d9dd372`: `StrategyStore.frontier_journal_projection_report()` audits folded-journal frontier rows against deterministic StrategyStore projections, `sync_frontier_journal_entries()` inserts only missing safe rows, and `scripts/autopilot/strategy_projection_report.py --strict` now reports a clean live view (`expected=59`, `projected=59`, `missing=0`, `unexpected=0`, `mismatch=0`). Remaining W6/W1 work: any future strategy-consumer audits before declaring full closure.
- [x] **W7 — session hygiene** (impl 4.3, ~half day, anytime): default `supports_resume=False` for the draft provider (delete `session_id` persistence); replace with a generated prior-decisions digest from `planner_archive.jsonl`; archive failed draft calls (move `_append_planner_archive` before the early-return). **Landed 2026-06-13**: `epyc-orchestrator` live branch `fix/substring-scorer-digit-separators` commit `9e5d861` (`Harden planner session hygiene`), rebased from original branch-ready `69a41f7`. AutoPilot remains paused; server/restart attestation is still pending.
- [x] **W8 — program.md split** (impl 4.4, ~2 days, anytime — this month per findings-01 §4): human-authored `constitution.md` (~150 lines) + `scripts/autopilot/gen_system_card.py` regenerating `system_card.md` at restart from live registry/state/instrument spec; prompt assembly swaps in the pair. **Landed 2026-06-13**: `epyc-orchestrator` live branch `fix/substring-scorer-digit-separators` commit `b4f328d` (`Split AutoPilot controller guidance`). The controller prompt now injects `constitution.md` plus a generated card derived from model registry, autopilot state, baseline, and tier specs; `program.md` is historical-only. The generated card explicitly removes `architect_coding` as a live role when absent from `server_mode`.

#### Gates & pitfalls

- Sequencing: Phase 3 lands after the ledger handoff's Phase 1 (per-question `question_results` must be in the rows being folded); W5/W6 hard-require W1; W7/W8 were independent and are now landed.
- W8 was an integrity task, not a token-budget trim — a planner whose constitution misdescribes the instrument produces confabulated hypotheses no memory hygiene can fix (findings-01 §2.4). Keep `system_card.md` source-derived; do not hand-edit stale topology into prompt guidance.
- Migration risk is bounded: reconstruction is battle-tested on the dashboard path and already caught real drift; run acceptance 3.5c (full historical replay) BEFORE deleting the dual-write.
- Append-only means append-only: no new sanitizers/scrubbers/gates bolted onto the old pipeline (findings-01 §4 hold-list); fixes become policy-version bumps + view recompute.
- `autopilot_state.json` still carries genuinely operational state (counters, halts, circuit breakers — `feedback_checkpoint_pareto_state`); only derived views move out.

#### Progress

- 2026-06-12: W7 branch-ready at `feat/planner-session-hygiene` commit `69a41f7`. GitNexus impacts were LOW for `plan_with_providers`, `ClaudePlannerProvider`, exact `controller_io.invoke_controller`, and `_run_loop_inner` (index stale vs current branch, treated conservatively). Validation: `python3 -m py_compile` on touched AutoPilot/test files passed; focused suite `tests/unit/test_autopilot_planner_providers.py tests/unit/test_autopilot_planner_coordinator.py tests/unit/test_autopilot_controller_io.py tests/unit/test_autopilot_actions.py` -> 84 passed, 1 pytest config warning; focused `ruff check` passed on non-debt touched files, and `ruff check --ignore F401` passed on `autopilot.py`/`test_autopilot_actions.py` due pre-existing F401 debt; `git diff --check` passed.
- 2026-06-13: Rebased W7 onto live branch `924ca50`, validated, and fast-forwarded `fix/substring-scorer-digit-separators` to `9e5d861`. GitNexus was refreshed to `924ca50` before impact checks; impacts were LOW for `plan_with_providers`, `ClaudePlannerProvider`, `controller_io.invoke_controller`, and `_run_loop_inner`. Validation on the rebased branch: `python3 -m py_compile` passed; `uv run --with pytest pytest -q tests/unit/test_autopilot_planner_providers.py tests/unit/test_autopilot_planner_coordinator.py tests/unit/test_autopilot_controller_io.py tests/unit/test_autopilot_actions.py tests/unit/test_skill_efficacy.py` -> 106 passed, 1 pytest config warning; focused ruff passed (excluding known pre-existing F401 debt in `test_skill_efficacy.py`; `autopilot.py`/`test_autopilot_actions.py` checked with `--ignore F401`); `git diff --check 924ca50..HEAD` passed.
- 2026-06-13: Landed W8 on live branch `b4f328d`. GitNexus impact before editing was LOW for `CONTROLLER_PROMPT_TEMPLATE`, `_build_prior_planner_decision_digest`, `_run_loop_inner`, and `build_budgeted_section_block` (the indexed `SECTION_BUDGETS` constant was ambiguous with no surfaced callers). Validation: `python3 -m py_compile scripts/autopilot/autopilot.py scripts/autopilot/gen_system_card.py scripts/autopilot/context_budget.py tests/unit/test_autopilot_system_card.py tests/unit/test_context_budget.py` -> pass; `uv run --with pytest pytest -q tests/unit/test_autopilot_system_card.py tests/unit/test_context_budget.py tests/unit/test_autopilot_actions.py` -> 42 passed; focused ruff passed on `gen_system_card.py`, `context_budget.py`, and `test_autopilot_system_card.py`; `autopilot.py` ruff passed with `--ignore F401` due pre-existing import debt; `python3 scripts/autopilot/gen_system_card.py --check` and `git diff --check` passed.
- 2026-06-13: Partial W2 append-only supersession substrate landed in `epyc-orchestrator` `3ff7af4`. GitNexus impact before editing was LOW for `ExperimentJournal`, `JournalEntry`, `scrub_journal.py`, and related system-card/runtime-state helpers. Validation: `python3 -m py_compile` on touched AutoPilot/journal/scrub/test files passed; focused pytest suite `tests/unit/test_autopilot_system_card.py tests/unit/test_journal_supersession_events.py tests/unit/test_journal_prompt_sanitization.py tests/unit/test_autopilot_recovery.py` -> 22 passed; focused ruff passed on touched files (`autopilot.py` checked with `--ignore F401` for pre-existing import debt); `git diff --check` passed; temp-journal CLI smoke verified `scrub_journal.py --append-event` appends a supersession event while leaving original trial-row trustworthiness unchanged.
- 2026-06-14: W2 append-only scrub default landed in `epyc-orchestrator` `702d785`. `scripts/autopilot/scrub_journal.py` now defaults to appending supersession events; existing trial rows are not rewritten unless the operator explicitly passes legacy `--rewrite-in-place`. Existing `--append-event` remains accepted as a compatibility no-op, and help/dry-run messaging names append-only as the default. Regression coverage in `tests/unit/test_scrub_journal.py` proves default scrub appends a supersession event while raw trial rows remain unmutated and folded trustworthiness sees the corruption tag; a second test proves `--rewrite-in-place` still performs the legacy row rewrite only when explicitly requested. Validation: `python3 -m py_compile scripts/autopilot/scrub_journal.py tests/unit/test_scrub_journal.py`; `uv run pytest -q tests/unit/test_scrub_journal.py tests/unit/test_journal_supersession_events.py tests/unit/test_journal_prompt_sanitization.py` -> 12 passed; `uv run ruff check scripts/autopilot/scrub_journal.py tests/unit/test_scrub_journal.py`; `git diff --check -- scripts/autopilot/scrub_journal.py tests/unit/test_scrub_journal.py` clean.
- 2026-06-19: W2 legacy in-place journal scrub path retired in `epyc-orchestrator` `2cb89f8`. `scrub_journal.py` no longer exposes `--rewrite-in-place`, no longer carries JSONL/TSV rewrite/backup code, and uses only append-only supersession events for writes. The unused `ExperimentJournal.apply_scrub()` in-memory mutation helper was removed; `matching_trial_ids()` remains as the non-mutating selector for append-only scrub previews/writes. Validation: GitNexus impact was LOW for `scripts/autopilot/scrub_journal.py` and MEDIUM for file-level `scripts/autopilot/experiment_journal.py` (`impactedCount=15`, no named processes); `py_compile`, `ruff`, `git diff --check`, focused scrub/supersession tests -> 10 passed, and adjacent scrub/supersession/recovery/preflight/replay/dashboard suite -> 128 passed. Orchestrator GitNexus refreshed current at `2cb89f8`.
- 2026-06-14: W3 snapshot-event substrate landed in `epyc-orchestrator` `5561f48`. `ExperimentJournal` now supports append-only typed `journal_snapshot` ledger events carrying `through_trial_id`, snapshot payload, `policy_version`, `actor`, optional `parent_snapshot_hash`, and a computed SHA-256 `snapshot_hash`; query helpers return all snapshot events and the latest event by append order. Snapshot events are non-trial rows and do not affect trial counts or next trial IDs. This is not a replay cutover: archive reconstruction, journal replay, and live AutoPilot authority remain unchanged until later consumers fold snapshots. Validation: `python3 -m py_compile` passed; `uv run ruff check` passed; `git diff --check` passed; `uv run pytest -q tests/unit/test_journal_supersession_events.py tests/unit/test_journal_prompt_sanitization.py tests/unit/test_autopilot_recovery.py` -> 34 passed.
- 2026-06-14: W3 snapshot replay diagnostics landed in `epyc-orchestrator` `26d875e`. New read-only helper `src/autopilot_core/journal_snapshot_replay.py` and CLI `scripts/autopilot/journal_snapshot_replay.py` validate the latest `journal_snapshot` event hash, count post-snapshot tail trials, compare snapshot archive payloads to current-policy prefix replay when an archive payload exists, and warn when post-snapshot supersession events target the snapshot prefix. The live CLI currently reports no snapshot events. This is still diagnostics only: live replay, archive reconstruction, baseline authority, and planner behavior remain unchanged. Validation: `python3 -m py_compile` passed; `uv run ruff check` passed; `git diff --check` passed; `uv run pytest -q tests/unit/test_journal_snapshot_replay.py tests/unit/test_journal_supersession_events.py tests/unit/test_autopilot_recovery.py` -> 34 passed.
- 2026-06-14: W3 snapshot builder CLI landed in `epyc-orchestrator` `5035987`. `scripts/autopilot/journal_snapshot_create.py` is dry-run by default, reconstructs the current full-journal archive payload, reports readiness, refuses duplicate/up-to-date snapshots unless `--force`, and appends only with explicit `--append`. Validation: `python3 -m py_compile` passed; `uv run ruff check` passed; `git diff --check` passed; `uv run pytest -q tests/unit/test_journal_snapshot_create.py tests/unit/test_journal_snapshot_replay.py tests/unit/test_journal_supersession_events.py` -> 17 passed. Live dry-run reported ready through trial `804` from `684` trial rows and `0` ledger events; replay still reported `0` snapshot events, confirming dry-run did not write. A later live append with `python3 scripts/autopilot/journal_snapshot_create.py --append` appended one `journal_snapshot` event through trial `804` with hash prefix `6b48abcf6923` at about `2026-06-14T01:25:24Z`; `python3 scripts/autopilot/journal_snapshot_replay.py --strict` then reported `1` snapshot event, hash status `match`, replay status `archive_prefix_match`, and `tail_trials=0`. A follow-up dry-run reported `up_to_date`, `684` trial rows, `1` ledger event, and parent hash `6b48abcf6923`. This live append is an append-only journal event, not a git-tracked code change and not live replay authority.
- 2026-06-14: W3 snapshot bounded replay readiness diagnostics landed in `epyc-orchestrator` `48d0ec1`. `src/autopilot_core/journal_snapshot_replay.py` now reports `bounded_replay_readiness` (`current`, `tail_unverified`, `prefix_invalidated`, `not_ready`) separately from hash status and replay status; `scripts/autopilot/journal_snapshot_replay.py --strict` now requires readiness `current`. Live diagnostics after the commit reported one snapshot through trial `804`, hash prefix `6b48abcf6923`, replay status `archive_prefix_match`, and bounded readiness `current`; `journal_snapshot_create.py` dry-run still reported `up_to_date`. This is a read-only diagnostic hardening step, not live replay/archive/baseline/planner authority cutover. Validation: `python3 -m py_compile` passed; `uv run ruff check` passed; `git diff --check` passed; `uv run pytest -q tests/unit/test_journal_snapshot_replay.py tests/unit/test_journal_snapshot_create.py tests/unit/test_journal_supersession_events.py` -> 18 passed; live `python3 scripts/autopilot/journal_snapshot_replay.py --strict` passed; live `python3 scripts/autopilot/journal_snapshot_create.py` passed. Main-lane GitNexus was re-indexed after the commit: 51,857 nodes, 88,913 edges, 300 flows.
- 2026-06-13: W2 read-side supersession folding landed in `epyc-orchestrator` `f08fabd`. `src/autopilot_core/journal_reconstruction.py` now folds append-only supersession events into reconstructed archive/dashboard/replay views in memory, keeps latest-run metadata selection on trial rows rather than event rows, and exposes `supersessions` archive metadata. `tests/unit/test_journal_supersession_events.py` proves supersession events exclude contaminated dominant trials while persisted trial rows remain unchanged. Validation: `uv run pytest -q tests/unit/test_journal_supersession_events.py tests/unit/test_autopilot_core_contracts.py tests/unit/test_dashboard_pareto_representative.py tests/unit/test_autopilot_recovery.py` -> 30 passed; `uv run ruff check src/autopilot_core/journal_reconstruction.py tests/unit/test_journal_supersession_events.py` passed; `git diff --check -- src/autopilot_core/journal_reconstruction.py tests/unit/test_journal_supersession_events.py` clean.
- 2026-06-13: W2 prompt/trust read views landed in `epyc-orchestrator` `73e569a`. `ExperimentJournal.entries_with_supersessions()` now folds append-only supersession events at read time without mutating `all_entries()`, and `trustworthy_entries`, `trustworthiness_score`, `summary_text`, and `insights_text` route through that view so planner-facing context excludes superseded contaminated trials. Regression coverage in `tests/unit/test_journal_supersession_events.py` proves a superseded trial is marked `CORRUPTED_BY=resource_contention` in summaries, excluded from trustworthy entries/insights, and raw journal rows remain unchanged. Validation: `python3 -m py_compile scripts/autopilot/experiment_journal.py tests/unit/test_journal_supersession_events.py`; `uv run pytest -q tests/unit/test_journal_supersession_events.py tests/unit/test_journal_prompt_sanitization.py tests/unit/test_autopilot_core_contracts.py` -> 20 passed; `uv run ruff check scripts/autopilot/experiment_journal.py tests/unit/test_journal_supersession_events.py`; `git diff --check -- scripts/autopilot/experiment_journal.py tests/unit/test_journal_supersession_events.py` clean.
- 2026-06-13: W2 crash-recovery read coverage landed in `epyc-orchestrator` `41d5e80`. `_maybe_reimport_pareto_from_journal` now queries `journal.entries_with_supersessions()` when available, so append-only events that mark a raw-clean trial bug-corrupted prevent live Pareto archive re-import after crash recovery while leaving `all_entries()` unmutated. Regression coverage in `tests/unit/test_autopilot_recovery.py` adds `test_reimport_skips_superseded_bug_corrupted_entry`. Validation: `python3 -m py_compile scripts/autopilot/autopilot.py tests/unit/test_autopilot_recovery.py`; `uv run pytest -q tests/unit/test_autopilot_recovery.py tests/unit/test_journal_supersession_events.py` -> 18 passed; `uv run ruff check scripts/autopilot/autopilot.py tests/unit/test_autopilot_recovery.py`; `git diff --check -- scripts/autopilot/autopilot.py tests/unit/test_autopilot_recovery.py` clean.
- 2026-06-13: W2/W6 distillation read coverage landed in `epyc-orchestrator` `005e836`. `_action_distill_knowledge` now passes `ctx.journal.entries_with_supersessions()` to `EvolutionManager.distill()` when available, falling back to `all_entries()` for compatibility, so append-only supersession corruption tags are not ignored when journal outcomes become persistent StrategyStore memory. Regression coverage in `tests/unit/test_autopilot_actions.py` uses fakes to prove the folded view is passed. Validation: `python3 -m py_compile scripts/autopilot/actions.py tests/unit/test_autopilot_actions.py`; `uv run pytest -q tests/unit/test_autopilot_actions.py tests/unit/test_evolution_manager_scrub.py tests/unit/test_journal_supersession_events.py` -> 33 passed; `uv run ruff check scripts/autopilot/actions.py tests/unit/test_autopilot_actions.py`; `git diff --check -- scripts/autopilot/actions.py tests/unit/test_autopilot_actions.py` clean.
- 2026-06-14: W1a read-only journal-backed archive diagnostics landed in `epyc-orchestrator` `9cc97bf`. `ParetoArchive.from_archive_payload(...)` and `pareto_archive_from_journal_rows(...)` now return a ParetoArchive-compatible read-only view reconstructed from append-only journal rows; mutation/promotion methods on read-only snapshots (`update`, `upsert_representative`, `save`, `load`, `mark_production_best`) raise so diagnostics stay separate from live mutation. `autopilot.py status` and `autopilot.py report` gained explicit `--archive-source state|journal-current-run|journal-all`; default remains `state`, and the live loop/safety gate/promotion paths are unchanged. The stale `cmd_digest` `archive.load(state)` call is now backed by a real mutable `ParetoArchive.load()` method. GitNexus was reindexed to `8a98868` before main-lane edits; reported impacts were LOW for `ParetoArchive`, `reconstruct_archive_from_journal_rows`, `_run_loop_inner`, `cmd_status`, and `cmd_report`; `9cc97bf` still needs a later main-lane reindex. Validation: `python3 -m py_compile` on touched modules/tests passed; `uv run ruff check` on touched modules/tests passed; `git diff --check` passed; `uv run pytest -q tests/unit/test_pareto_archive_tiers.py tests/unit/test_autopilot_recovery.py tests/unit/test_autopilot_core_contracts.py` -> 33 passed.
- 2026-06-14: W1 archive authority preflight audit landed in `epyc-orchestrator` `0e5e796`. `scripts/autopilot/preflight_audit.py` now includes `Archive Authority Drift` before inference/e2e seeding, reconstructs the append-only journal archive from `autopilot_journal.jsonl`, compares it with normalized `autopilot_state.json:pareto_archive`, checks latest snapshot bounded replay readiness is not `prefix_invalidated`, and fails preflight on authority drift or when journal max trial ID is at/above `state.trial_counter`. Unit coverage covers match, drift, journal-ahead warning, and temp-path smoke. Live no-inference audit evidence after commit: 685 journal rows loaded, `status=drift`, `state_entries=259`, `journal_entries=257`, `state_frontier=7`, `journal_frontier=12`; snapshot prefix remains `current` / `archive_prefix_match`, and follow-up delta check points to broader state/archive mismatch rather than prefix invalidation. This is a restart blocker and next archive repair/reconciliation item before AutoPilot resumes; it is not live archive authority cutover. Validation: `python3 -m py_compile scripts/autopilot/preflight_audit.py tests/unit/test_autopilot_preflight_audit.py`; `uv run ruff check scripts/autopilot/preflight_audit.py tests/unit/test_autopilot_preflight_audit.py`; `git diff --check`; `PYTHONDONTWRITEBYTECODE=1 uv run pytest -q -p no:cacheprovider tests/unit/test_autopilot_preflight_audit.py tests/unit/test_journal_snapshot_replay.py tests/unit/test_autopilot_recovery.py` -> 34 passed in 0.45s. GitNexus re-index after the commit completed incrementally (`changed=2`, `added=0`, `deleted=0`) in 40.5s: 51,945 nodes, 89,062 edges, 1,087 clusters, 300 flows.
- 2026-06-14: W1 archive authority drift report landed in `epyc-orchestrator` `20b082f`. New no-inference `scripts/autopilot/archive_authority_report.py` reports state-vs-journal archive authority drift in Markdown or JSON, supports `--strict` for restart gates, reuses the preflight diagnostic, and reports entry-ID deltas, frontier-ID deltas, and common-entry semantic mismatches. The same commit tightened preflight's archive projection to compare archive semantics instead of display/provenance metadata. Live no-inference report evidence: `archive_authority_report.py --max-examples 12` exited 0 and reported `status=drift`, `state_trial_counter=805`, `journal_max_trial_id=804`, `state_entries=259`, `journal_entries=257`, `state_frontier=7`, `journal_frontier=12`, snapshot readiness `current`, and replay `archive_prefix_match`; examples include state-only entries `269,281,283,287,288,297,298,301,302,303,304,306`, journal-only entries `10,15,16,18,28,29,47,52,53,56,59,61`, state-only frontier `[256]`, journal-only frontier `[77,118,146,166,190,207]`, and semantic mismatches on trials `569`, `668`, `680`, and `804`. `--json --strict --max-examples 3` exits 1 as intended on live drift. Validation: `python3 -m py_compile scripts/autopilot/preflight_audit.py scripts/autopilot/archive_authority_report.py tests/unit/test_autopilot_preflight_audit.py tests/unit/test_archive_authority_report.py`; `uv run ruff check` on the same paths; `git diff --check`; `PYTHONDONTWRITEBYTECODE=1 uv run pytest -q -p no:cacheprovider tests/unit/test_archive_authority_report.py tests/unit/test_autopilot_preflight_audit.py tests/unit/test_journal_snapshot_replay.py tests/unit/test_autopilot_recovery.py` -> 38 passed in 0.47s. GitNexus re-index after the commit completed incrementally (`changed=2`, `added=2`, `deleted=0`) in 45.6s: 52,003 nodes, 89,165 edges, 1,088 clusters, 300 flows.
- 2026-06-14: W1 archive authority repair CLI landed in `epyc-orchestrator` `5587e33`. New `scripts/autopilot/archive_authority_repair.py` is dry-run by default, reconstructs `pareto_archive` from append-only journal replay, preserves surrounding `autopilot_state.json` operational fields, creates a timestamped backup before `--write`, writes atomically through `state_store.save_state`, and supports `--expect-trial-counter` to refuse stale live writes. It postchecks the repaired state with the archive authority report and only reports write-ready when the postcheck is aligned. Live dry-run evidence before writing: `archive_authority_repair.py --max-examples 8` exited 0 with `Archive repair status: ready`; before drift was `state_entries=259`, `journal_entries=257`, `state_frontier=7`, `journal_frontier=12`, and after postcheck the projected state matched at `state_entries=257`, `journal_entries=257`, `state_frontier=12`, `journal_frontier=12`. Main-lane GitNexus re-index after the commit completed incrementally (`changed=0`, `added=2`, `deleted=0`) in 39.4s: 52,059 nodes, 89,269 edges, 1,091 clusters, 300 flows. Live operational repair then stopped AutoPilot PID `3810659` (`.venv/bin/python scripts/autopilot/autopilot.py start --no-controller`) and parent `3810657`, sent TERM, waited, and verified both PIDs dead before state write; clean `pgrep` after repair showed no AutoPilot process. `archive_authority_repair.py --write --expect-trial-counter 805 --max-examples 8` reported `Archive repair status: written`; before drift was `state_entries=259`, `journal_entries=257`, `state_frontier=7`, `journal_frontier=12`, and postcheck matched at `state_entries=257`, `journal_entries=257`, `state_frontier=12`, `journal_frontier=12`. Backup: `/mnt/raid0/llm/epyc-orchestrator/orchestration/autopilot_state.json.bak-archive-repair-20260614T020530Z`. Post-repair gates: `archive_authority_report.py --strict --max-examples 8` exited 0 with `status=match`, no entry/frontier deltas, no common-entry mismatches, and snapshot readiness `current` / `archive_prefix_match`; `audit_archive_authority()` returned true with 685 journal rows; `python3 -m json.tool orchestration/autopilot_state.json` passed. State size after repair is 383,979 bytes; backup size is 321,346 bytes; focused git status for the state/backup paths produced no tracked or untracked output, so runtime artifacts remain ignored/untracked by the root docs lane. Validation: `python3 -m py_compile scripts/autopilot/archive_authority_repair.py tests/unit/test_archive_authority_repair.py`; `uv run ruff check` on the same paths; `git diff --check`; `PYTHONDONTWRITEBYTECODE=1 uv run pytest -q -p no:cacheprovider tests/unit/test_archive_authority_repair.py tests/unit/test_archive_authority_report.py tests/unit/test_autopilot_preflight_audit.py tests/unit/test_journal_snapshot_replay.py tests/unit/test_autopilot_recovery.py` -> 43 passed in 0.59s.
- 2026-06-18: W1 runtime archive-authority save-path increment landed in `epyc-orchestrator` `5de68b8`. Trial-end and shutdown state saves now persist `pareto_archive` from the append-only journal reconstruction when a journal archive payload exists, with legacy `archive.save(state)` retained only as an empty-journal fallback. Recovery re-import still repairs the current in-memory archive, but no longer writes a one-off mutable snapshot before startup journal-authority sync can fold the full ledger. This advances W1 runtime authority but does not yet remove the legacy `pareto_archive` state key or all mutable archive APIs. Validation: GitNexus `_run_loop_inner` LOW (`impactedCount=2`) and `audit_archive_authority` LOW (`impactedCount=5`); `ruff`, `py_compile`, `git diff --check`, and `uv run pytest -q tests/unit/test_autopilot_recovery.py tests/unit/test_archive_authority_report.py tests/unit/test_archive_authority_repair.py tests/unit/test_autopilot_preflight_audit.py tests/unit/test_journal_snapshot_replay.py` -> 57 passed. The bounded AutoPilot run that was already active did not pick up this code path; it completed on old code and produced archive drift (`journal_only=[831]`, `state_only=[825]`), which was repaired with `archive_authority_repair.py --write --expect-trial-counter 832`; strict postcheck now reports `status=match`, `state_trial_counter=832`, `journal_max_trial_id=831`, and no entry/frontier deltas.
- 2026-06-18: W5 live STM prompt-memory cutover landed in `epyc-orchestrator` `cfa8525`. `ShortTermMemory.refresh_from_journal()` rebuilds the prompt memory from `ExperimentJournal.entries_with_supersessions()` through `stm_generated_view.render_generated_stm()`, atomically writes the generated `short_term_memory.md` projection, and returns the prompt text. `_run_loop_inner()` now refreshes the projection at startup, before planner prompt injection, and after each `journal.record(...)`; it no longer constructs `TrialOutcome` or calls `memory.update(...)` in the live loop. Validation: GitNexus impacts were LOW for `_run_loop_inner` (`impactedCount=2`), `ShortTermMemory` (`impactedCount=1`), and `stm_generated_view.py` (`impactedCount=0`); `ruff`, `py_compile`, `git diff --check`, and `uv run pytest -q -p no:cacheprovider tests/unit/test_stm_generated_view.py tests/unit/test_autopilot_recovery.py tests/unit/test_archive_authority_report.py tests/unit/test_archive_authority_repair.py tests/unit/test_autopilot_preflight_audit.py tests/unit/test_journal_snapshot_replay.py` -> 64 passed. Live read-only checks passed: `stm_generated_view.py --journal-dir orchestration --last-n 5` rendered against the real journal and `archive_authority_report.py --strict --max-examples 8` reported `status=match`, `state_entries=265`, `journal_entries=265`, `state_frontier=11`, `journal_frontier=11`. A bounded evidence run was relaunched with the new code using `setsid` as PID `2076193`, log `/mnt/raid0/llm/tmp/autopilot-shadow-resume-20260618T130028Z.log`: trial `832` was an invalid skip that added a `seed_batch(coder, math)` blacklist entry, trial `833` completed `numeric_swarm/memrl_retrieval` as dominated (`q=1.740`, reliability `0.96`, aggregate speed `27.01`, eval wall `1010.83s`), archive authority still matched after shutdown (`state_trial_counter=834`, `journal_max_trial_id=833`, entries/frontier aligned), sequential readiness advanced to trusted vectors `29` / raw vectors `36` / seq shadow rows `2`, and runtime artifacts were checkpointed in `0919126`. W5 remains open only for the tracked-runtime-artifact policy.
- 2026-06-18: W1 journal-authoritative runtime archive/cache removal and W5 mutable-STM cleanup landed in `epyc-orchestrator` `3c3e016`. AutoPilot now initializes the live mutable `ParetoArchive` from the append-only journal fold when available, removes cached `state["pareto_archive"]` instead of refreshing it on normal journal-authoritative saves, defaults operator `status`/`report`/digest archive reads to `journal-all`, and makes the SafetyGate archive-max/reproduction guard read the journal-backed frontier so baseline safety does not weaken after state-cache removal. `archive_authority_report.py` and preflight now treat an absent state archive cache as valid journal-authoritative mode, while `archive_authority_repair.py --write` removes the legacy cache after replay verification. The live state migration was executed with `--expect-trial-counter 834`, creating ignored backup `orchestration/autopilot_state.json.bak-archive-repair-20260618T133405Z`; post-migration strict report passed with `state_archive_cache=absent`, `state_entries=0`, `journal_entries=266`, `state_frontier=0`, `journal_frontier=11`, and `status=match`. `ShortTermMemory` no longer exposes `TrialOutcome` or `update()`; it only maintains the generated journal projection. Validation: GitNexus impacts were LOW for `_apply_journal_archive_authority`, `_save_state_with_journal_archive_authority`, `build_archive_authority_report`, `ShortTermMemory.update`, `_pareto_frontier_context`, and `SafetyGate._archive_frontier_entry`; `ruff`, `py_compile`, `git diff --check`, `uv run pytest -q -p no:cacheprovider tests/unit/test_autopilot_recovery.py tests/unit/test_archive_authority_report.py tests/unit/test_archive_authority_repair.py tests/unit/test_autopilot_preflight_audit.py tests/unit/test_journal_snapshot_replay.py tests/unit/test_safety_gate_baseline_eligibility.py tests/unit/test_stm_generated_view.py` -> 80 passed; broader safety/baseline/archive suite -> 64 passed; live status/report and SafetyGate frontier probe succeeded with the cache absent. Remaining W1 work: retire `ParetoArchive.save` legacy bootstrap after the compatibility window and finish ledger-keyed strategy view integration.
- 2026-06-19: W1 live legacy archive-save fallback retired in `epyc-orchestrator` `6da83d0`. `_save_state_with_journal_archive_authority()` no longer calls `archive.save(state)` when the journal has no archive-bearing rows; it logs the unavailable journal fold and persists lifecycle state directly via `save_state(state)` without writing a legacy `pareto_archive` cache. A regression test covers the empty-journal lifecycle-save path and fails if `archive.save()` is reintroduced there. Validation: GitNexus impact for `_save_state_with_journal_archive_authority` was LOW (`impactedCount=3`, AutoPilot process); `py_compile`, `ruff`, `git diff --check`, and `uv run pytest -q tests/unit/test_autopilot_recovery.py tests/unit/test_archive_authority_report.py tests/unit/test_archive_authority_repair.py tests/unit/test_autopilot_preflight_audit.py tests/unit/test_journal_snapshot_replay.py tests/unit/test_safety_gate_baseline_eligibility.py tests/unit/test_baseline_authority_report.py tests/unit/test_baseline_ledger.py` -> 97 passed.
- 2026-06-19: W1 public archive-save compatibility API removed in `epyc-orchestrator` `f7a917c`. `ParetoArchive.save()` is gone, so mutable archive objects can no longer directly persist a derived `state["pareto_archive"]` cache; persistence now stays with `state_store.save_state()` and the journal-authority helpers. Tests that previously exercised the legacy save path now assert the method is absent and keep coverage for explicit payload loading. Validation: file-level GitNexus impact for `scripts/autopilot/pareto_archive.py` was LOW (`impactedCount=8`, no named processes); `py_compile`, `ruff`, repo-wide `archive.save` reference search, `git diff --check`, focused archive/recovery tests -> 46 passed, adjacent A8 authority suite -> 112 passed. Orchestrator GitNexus was refreshed after an incomplete incremental attempt by a forced full rebuild and is current at `f7a917c`.
- 2026-06-20: W1 generic raw archive payload loader narrowed in `epyc-orchestrator` `5843190`. `ParetoArchive.load_archive_payload()` is no longer public API; the only mutable raw-payload replacement path is internal `_replace_from_archive_payload()` and is used by AutoPilot's journal-authority helper after folding the append-only journal. Regression coverage asserts the generic public loader remains absent. GitNexus impacts before the edit were LOW for `load_archive_payload` (`impactedCount=4`), `_apply_journal_archive_authority`, and `_run_loop_inner`. Validation: `py_compile`, `ruff`, `git diff --check`, focused archive/recovery/authority tests -> 48 passed, broader archive/preflight/snapshot/safety/baseline suite -> 103 passed, and `stack_change_guard.py --surface-summary-only --all-hardcoded-surfaces` passed. Orchestrator GitNexus was refreshed and is current at `5843190`.
- 2026-06-20: W1 digest archive-source diagnostics landed in `epyc-orchestrator` `26cc34f`. `autopilot.py digest` now accepts `--archive-source state|journal-current-run|journal-all`, threads the explicit source through the read-command archive helper, and records the selected archive source in the generated digest Markdown. This aligns `digest` with the existing `status`/`report` archive-source diagnostics without changing live loop, SafetyGate, promotion, or state-save behavior. GitNexus impacts before the edit were LOW for `cmd_digest` (`impactedCount=0`), `_archive_for_read_command` (`impactedCount=4`), and `generate_digest` (`impactedCount=1`). Validation: `py_compile`, `ruff`, focused recovery/economic-ledger tests -> 35 passed, broader archive/authority/baseline suite -> 101 passed, `autopilot.py digest --help` showed the new flag, and orchestrator GitNexus was refreshed/current at `26cc34f`.
- 2026-06-20: W1 plot archive-source diagnostics landed in `epyc-orchestrator` `d1a6229`. `autopilot.py plot` now accepts `--archive-source state|journal-current-run|journal-all`, threads the selected read source through `_archive_for_read_command()`, and prints the non-legacy source before generated plot paths. This closes the concrete read-command diagnostic mismatch left after `status`, `report`, and `digest` were aligned; it does not change plot rendering, live loop behavior, SafetyGate, promotion, or state-save behavior. GitNexus impacts before the edit were LOW for `cmd_plot` (`impactedCount=0`), `_archive_for_read_command` (`impactedCount=4`), and `generate_all_plots` (`impactedCount=1`). Validation: `ruff`, `py_compile`, focused `cmd_plot`/archive-source tests -> 3 passed, full `tests/unit/test_autopilot_recovery.py` -> 33 passed, `autopilot.py plot --help` showed the new flag, scoped `git diff --check` passed, and orchestrator GitNexus refreshed/current at `d1a6229`.
- 2026-06-14: W4a baseline promotion event scaffold landed in `epyc-orchestrator` `0202835`. `ExperimentJournal` now supports generic ledger events and typed `baseline_promotion` rows; those rows are non-trial ledger entries, do not advance trial IDs, and are excluded from supersession folds. AutoPilot appends a baseline-promotion event only after the existing safety gate accepts an update, and after `archive.save(state)` / `save_state(state)` have completed; event-write failures are wrapped and cannot alter live baseline decisions. `autopilot_state.json:baseline_state` remains the W4a source of authority, with events serving as evidence until baseline-as-fold is completed. GitNexus was fresh at `9cc97bf` before main-lane edits; reported impacts were LOW for `ExperimentJournal`, `_run_loop_inner`, and `SafetyGate`; `0202835` still needs a later main-lane reindex. Validation: `python3 -m py_compile scripts/autopilot/experiment_journal.py scripts/autopilot/autopilot.py tests/unit/test_journal_supersession_events.py tests/unit/test_autopilot_recovery.py`; `uv run ruff check scripts/autopilot/experiment_journal.py scripts/autopilot/autopilot.py tests/unit/test_journal_supersession_events.py tests/unit/test_autopilot_recovery.py`; scoped `git diff --check` passed; `uv run pytest -q tests/unit/test_journal_supersession_events.py tests/unit/test_autopilot_recovery.py tests/unit/test_safety_gate_baseline_eligibility.py` -> 38 passed.
- 2026-06-14: W4a baseline promotion evidence consumers landed in `epyc-orchestrator` `5f6c81e` and `47c75de`. `/dashboard/api/pareto` now includes `baseline_promotions` summarizing current-run `type=baseline_promotion` ledger events parsed from `autopilot_journal.jsonl`, and `task_rate_goodput_replay.py` now writes a `Baseline Promotion Evidence` table scoped to baseline-promotion events whose `source_trial_id` exists in the effective folded replay rows. The replay report tolerates malformed/incomplete promotion events and leaves archive reconstruction unchanged; both consumers are evidence-only and do not affect frontier reconstruction, live planner/safety-gate behavior, or `autopilot_state.json:baseline_state` authority. Impact before edit: GitNexus current at `0202835`; `pareto`, `_pareto_from_journal`, `_effective_journal_trial_rows`, `_write_report`, and `File:scripts/analysis/task_rate_goodput_replay.py` all reported LOW. Validation: `python3 -m py_compile src/api/routes/dashboard.py tests/unit/test_dashboard_helpers.py`; `uv run ruff check src/api/routes/dashboard.py tests/unit/test_dashboard_helpers.py`; `git diff --check -- src/api/routes/dashboard.py tests/unit/test_dashboard_helpers.py`; `uv run pytest -q tests/unit/test_dashboard_helpers.py` -> 59 passed. Replay validation: `python3 -m py_compile scripts/analysis/task_rate_goodput_replay.py tests/unit/test_task_rate_goodput_replay.py`; `uv run ruff check scripts/analysis/task_rate_goodput_replay.py tests/unit/test_task_rate_goodput_replay.py`; `git diff --check -- scripts/analysis/task_rate_goodput_replay.py tests/unit/test_task_rate_goodput_replay.py`; `uv run pytest -q tests/unit/test_task_rate_goodput_replay.py` -> 3 passed.
- 2026-06-14: W4 diagnostics increment landed in `epyc-orchestrator` `3c5d98b`. `autopilot.py status` and `autopilot.py report` now print read-only baseline-promotion ledger summary lines: promotion event count, latest event source/tier/quality transition/timestamp, and whether the latest event's `baseline_state` snapshot matches current `autopilot_state.json:baseline_state`. The fold is latest-event-snapshot diagnostics only; SafetyGate and live baseline authority still read state and are unchanged. Validation: `python3 -m py_compile` passed; `uv run ruff check` passed with the existing F401 ignore on the `autopilot.py` path; `git diff --check` passed; `uv run pytest -q tests/unit/test_autopilot_recovery.py tests/unit/test_journal_supersession_events.py` -> 28 passed.
- 2026-06-14: W4 diagnostic hardening landed in `epyc-orchestrator` `32b4497`. Baseline-promotion ledger reconciliation moved into pure `src/autopilot_core/baseline_ledger.py`, where AutoPilot status/report now receive structured statuses (`no_events`, `unreconstructable`, `missing_state_baseline`, `match`, `drift`) from append-order latest-valid-snapshot folds. The helper compares canonical state snapshots and surfaces event-quality mismatches as warning-only diagnostics. This remains a read-only evidence consumer; SafetyGate and live `autopilot_state.json:baseline_state` authority are unchanged. Validation: `python3 -m py_compile` passed; `uv run ruff check` passed with the existing F401 ignore where needed; `git diff --check` passed; `uv run pytest -q tests/unit/test_baseline_ledger.py tests/unit/test_autopilot_recovery.py tests/unit/test_journal_supersession_events.py` -> 35 passed.
- 2026-06-14: W4 baseline fold cutover dry-run readiness landed in `epyc-orchestrator` `b7e7321`. `src/autopilot_core/baseline_ledger.py` now returns `cutover_ready` and `cutover_blockers` on `BaselineLedgerReconciliation`; the dry-run is ready only when every `baseline_promotion` event has a usable `baseline_state` snapshot, the append-order ledger fold matches current `autopilot_state.json:baseline_state`, and there are no warning diagnostics. This is a dry-run acceptance signal only: no live baseline authority is flipped, and `autopilot_state.json:baseline_state` remains authoritative. Validation from the implementation lane: `python3 -m py_compile` on touched files passed; `uv run ruff check` on touched files passed; `uv run pytest -q tests/unit/test_baseline_ledger.py tests/unit/test_autopilot_recovery.py tests/unit/test_journal_supersession_events.py` -> 36 passed; `git diff --check` passed.
- 2026-06-14: W4 baseline authority report CLI landed in `epyc-orchestrator` `3cd8116a8bf709ca2d9331c616910a81ad393454`. New read-only `scripts/autopilot/baseline_authority_report.py` reports `baseline_state` versus the append-only `baseline_promotion` ledger fold and exposes dry-run cutover readiness in text or JSON. It supports `--json --strict`; strict exits 1 when not cutover-ready and exits 2 for missing/non-object state or journal errors. It uses `preflight_audit` defaults / `_load_jsonl` and `reconcile_baseline_ledger`, writes nothing, and does not flip baseline authority. Live smoke `python3 scripts/autopilot/baseline_authority_report.py --json` returned `ok=false`, `status=no_events`, and `cutover_blockers=["no baseline promotion events; YAML remains cold-start seed"]`, as expected on the current live journal. `autopilot_state.json:baseline_state` remains authoritative. Validation: worker py_compile on new files passed; worker ruff on new files passed; worker `pytest tests/unit/test_baseline_authority_report.py tests/unit/test_baseline_ledger.py` -> 14 passed; worker diff-check passed. Main agent also passed py_compile on report+baseline files, ruff on report+baseline files, and `pytest tests/unit/test_baseline_authority_report.py tests/unit/test_baseline_ledger.py tests/unit/test_autopilot_recovery.py tests/unit/test_journal_supersession_events.py` -> 43 passed.
- 2026-06-19: W4 generated system-card baseline ledger fold landed in `epyc-orchestrator` `2fcbcf7`. `gen_system_card.py` now reads `autopilot_state.json` once and, when `baseline_state` is absent, folds `baseline_promotion` events from `orchestration/autopilot_journal.jsonl` via `reconcile_baseline_ledger()` before falling back to `autopilot_baseline.yaml`. The generated card uses the folded ledger state only when the reconciliation is cutover-ready; SafetyGate/live authority remains state/YAML unless the runtime persistence helper has explicitly removed `baseline_state`. Validation: GitNexus impact for `scripts/autopilot/gen_system_card.py` was LOW (`impactedCount=1`, direct import by AutoPilot); `py_compile`, `ruff`, `gen_system_card.py --check`, focused system-card/baseline tests -> 26 passed, broader recovery/safety/baseline suite -> 70 passed, `git diff --check` passed, and orchestrator GitNexus refreshed current at `2fcbcf7`.
- 2026-06-20: W4 runtime startup baseline ledger fold landed in `epyc-orchestrator` `c3d1b26`. `_run_loop_inner()` now initializes `SafetyGate` through `_baseline_state_for_startup_gate()`: state cache wins while present; if absent, the append-only `baseline_promotion` ledger can seed the gate only when `reconcile_baseline_ledger()` says the fold is cutover-ready; otherwise startup falls back to the existing YAML seed path. This closes the read-path gap left after cache removal, while remaining inert on the current live journal (`baseline_authority_report.py --json` still reports `status=no_events`). The active W4/W6 accrual process predates the commit and was deliberately not restarted, so the fix is committed for the next controlled restart rather than deployed mid-window. Validation: GitNexus impacts LOW for `apply_baseline_ledger_authority` (`impactedCount=3`), `reconcile_baseline_ledger` (`impactedCount=14`), and `_run_loop_inner` (`impactedCount=2`); `python3 -m py_compile scripts/autopilot/autopilot.py tests/unit/test_autopilot_recovery.py`; `uv run pytest -q tests/unit/test_autopilot_recovery.py tests/unit/test_baseline_ledger.py tests/unit/test_baseline_authority_report.py tests/unit/test_autopilot_system_card.py` -> 64 passed; `uv run ruff check scripts/autopilot/autopilot.py tests/unit/test_autopilot_recovery.py`; scoped `git diff --check`; orchestrator GitNexus refreshed current at `c3d1b26`.
- 2026-06-20: W3 current-snapshot archive authority consumption landed in `epyc-orchestrator` `f945f15`. `src/autopilot_core/journal_snapshot_replay.py` now exposes `archive_payload_from_current_snapshot()`, and AutoPilot archive authority calls it before full replay. The helper returns a snapshot archive only when the existing diagnostic proves `bounded_replay_readiness=current`; tailed, hash-mismatched, prefix-invalidated, or archive-less snapshots return `None` and leave full replay in force. Live diagnostic remains `tail_unverified` with `tail_trial_count=79`, so this commit is committed for the next controlled restart but inert on the active W4/W6 accrual process. Validation: GitNexus impacts LOW for `build_snapshot_replay_diagnostic` (`impactedCount=9`) and `_journal_archive_payload_for_authority` (`impactedCount=6`); `python3 -m py_compile src/autopilot_core/journal_snapshot_replay.py scripts/autopilot/autopilot.py tests/unit/test_journal_snapshot_replay.py tests/unit/test_autopilot_recovery.py`; `uv run pytest -q tests/unit/test_journal_snapshot_replay.py tests/unit/test_autopilot_recovery.py tests/unit/test_archive_authority_report.py tests/unit/test_autopilot_preflight_audit.py` -> 68 passed; `uv run ruff check src/autopilot_core/journal_snapshot_replay.py scripts/autopilot/autopilot.py tests/unit/test_journal_snapshot_replay.py tests/unit/test_autopilot_recovery.py`; scoped `git diff --check`; orchestrator GitNexus refreshed current at `f945f15`.
- 2026-06-20: Post-repair restart preflight aggregation landed in `epyc-orchestrator` `fbb5ec04`. `scripts/autopilot/restart_readiness_report.py` now combines archive authority, snapshot replay, baseline authority, and sequential-cutover readiness into a single read-only restart gate. Ordinary restart passes when archive authority is aligned, the latest snapshot is either current or safely tail-foldable, and either ledger baseline fold or live `state.baseline_state` is available; `--require-seq-cutover` additionally fails closed until W4/W6 sequential authority has enough evidence. Live smoke after trial `893` reported `restart_ready=true`, archive `match`, snapshot `tail_fold_ready`, baseline source `state_baseline`, and sequential cutover blocked at trusted vectors `61/120` plus seq shadow rows `9/30`; the expected `--strict --require-seq-cutover` run exited 1. Validation: `py_compile`, `ruff`, scoped `git diff --check`, focused restart-readiness tests, and adjacent archive/baseline/snapshot/seq report tests -> 34 passed. Orchestrator GitNexus was refreshed current at `fbb5ec04`.
- 2026-06-20: Baseline ledger seed preflight landed in `epyc-orchestrator` `1a9b7cc2`. `scripts/autopilot/baseline_authority_seed.py` prepares an append-only `baseline_promotion` seed event from the current `autopilot_state.json:baseline_state` so W4 baseline-as-fold authority can be validated without waiting for a future live baseline promotion. It is dry-run by default, records proof metadata (`seeded_from_state_baseline`, `state_trial_counter`, `journal_max_trial_id`, and baseline tiers), and refuses `--append` while any `autopilot.py start` process is live. Live dry-run after trial `893` reported `Before: status=no_events events=0 cutover_ready=False`, `After: status=match events=1 cutover_ready=True`, and prepared a tier-2 event at `new_quality=1.5242914979757085`; the attempted live append with `--expect-trial-counter 894` exited 2 and refused to write while PIDs `655236/655243` were running. The baseline ledger is therefore now preflight-ready for the next controlled stop window, not yet cut over. Validation: GitNexus impact was MEDIUM on shared baseline reconciliation, so the implementation did not change shared fold semantics; new script/test surfaces only. `py_compile`, `ruff`, scoped `git diff --check`, focused seed/report/ledger tests -> 26 passed, and adjacent seed/report/ledger/restart/recovery tests -> 69 passed. Orchestrator GitNexus was refreshed current at `1a9b7cc2`.
- 2026-06-20: Baseline seed preflight was surfaced in aggregate restart readiness in `epyc-orchestrator` `44d8d9e6`. `scripts/autopilot/restart_readiness_report.py` now includes `baseline_authority.seed_preflight` plus summary fields for seed status, append readiness, and append requirement, so the next controlled stop window can see whether W4's baseline seed event is prepared before attempting a ledger-authority cutover. This remains read-only/report-only: no baseline event is appended, no authority source is flipped, and ordinary restart readiness remains separate from sequential/W6 cutover gates. Live strict smoke after trial `895` reported ordinary restart ready with baseline source `state_baseline`, seed preflight `ready`, `append_ready=true`, `append_required=true`, sequential evidence still `62/120` trusted vectors and `10/30` shadow rows, and W6 still alarmed at `34/30` audited rows with `potential_overfit_divergences=5`. Validation: `py_compile`, `ruff`, scoped `git diff --check`, focused restart-readiness/baseline tests -> 34 passed, plus live `restart_readiness_report.py --json --strict` smoke.
- 2026-06-20: Baseline seed append stale-window guard landed in `epyc-orchestrator` `d1b2a59b`. `baseline_authority_seed.py --append` now accepts `--expect-journal-max-trial-id` alongside `--expect-trial-counter`, refusing with status `journal_max_trial_id_mismatch` when the journal advanced past the readiness evidence being acted on. This keeps the next controlled-stop seed append tied to the exact durable journal max from the restart report instead of only the mutable state counter. Live dry-run after trial `901` still prepared a cutover-ready seed (`source_trial_id=901`, `state_trial_counter=902`, `journal_max_trial_id=901`); a mismatched append probe exited 2 with `journal_max_trial_id_mismatch`, and a matching append probe exited 2 with `live_autopilot_running` while PIDs `1091014/1091018` remained live. Validation: GitNexus impacts LOW for `build_baseline_seed_event` (`impactedCount=6`), `append_baseline_seed_event` (`3`), `baseline_authority_seed.py` (`2`), and `restart_readiness_report.py` (`1`); `py_compile`, `ruff`, scoped `git diff --check`, focused seed/restart tests -> 17 passed, adjacent Fable5/seed/restart suite -> 27 passed. Orchestrator GitNexus refreshed current at `d1b2a59b`.
- 2026-06-20: Baseline seed append guard values were surfaced in aggregate gates in `epyc-orchestrator` `1aabc54a`. `restart_readiness_report.py` now exposes `baseline_seed_append_expect_trial_counter` and `baseline_seed_append_expect_journal_max_trial_id` in both the summary and `baseline_authority.seed_preflight`; `fable5_gate_report.py` carries the same values in the `w4_w6_restart_cutover` section details. Live smokes reported `append_expect_trial_counter=902` and `append_expect_journal_max_trial_id=901` in both reports, so the next controlled-stop command can use readiness-artifact values directly. Validation: GitNexus impacts LOW for `_baseline_seed_preflight` (`impactedCount=4`), `_summary_report` (`5`), and `fable5_gate_report.py` (`0`); `py_compile`, `ruff`, scoped `git diff --check`, focused restart/Fable5/seed tests -> 27 passed. Orchestrator GitNexus refreshed current at `1aabc54a`.
- 2026-06-20: W3 safe snapshot tail fold landed in `epyc-orchestrator` `09416fd`. `archive_payload_from_verified_snapshot()` now covers the existing current-snapshot path plus a conservative bounded fold for ordinary post-snapshot trial tails, preserving frontier/hypervolume state, exclusions, supersession metadata, and `journal_max_trial_id` without invoking AutoPilot's full-replay fallback. The helper refuses tails with within-noise representative rows such as W4 `seq_accumulating`, because compact snapshots do not retain raw prefix samples for median recomputation. Live diagnostic still reports `tail_unverified` (`through_trial_id=812`, `tail_trial_count=79`, `tail_max_trial_id=891`), so the active W4/W6 process remains on old code and the current live tail still requires full replay. Validation: GitNexus impacts LOW for `archive_payload_from_current_snapshot` and `_journal_archive_payload_for_authority` (each `impactedCount=6`); py_compile on touched code/tests; focused snapshot/recovery tests -> 49 passed; adjacent archive/preflight/core suite -> 82 passed; ruff and scoped `git diff --check` passed.
- 2026-06-20: W3 representative replay-state snapshot payload landed in `epyc-orchestrator` `0c3c25ed`. Future `journal_snapshot_create.py` snapshots now include top-level `replay_state` with `representative-replay-state-v1` clusters, and `archive_payload_from_verified_snapshot()` can use that state to fold within-noise/`seq_accumulating` tails while preserving representative medians. Old snapshots without replay state still fail closed to full replay; no live snapshot was appended. Live dry-run showed a ready snapshot through trial `892` with `37` representative clusters and left persisted snapshot events at `2`. Validation: shared reconstruction impact was HIGH and deliberately not behavior-changed; edited builder/replay surfaces were LOW; py_compile, ruff, focused snapshot tests -> 15 passed, adjacent archive/preflight/core suite -> 87 passed. Remaining W3 gate: append a fresh snapshot with replay state in a controlled window, then verify bounded replay on the new snapshot before relying on it for startup cost.
- 2026-06-14: First W6 strategy-provenance read guard landed in `epyc-orchestrator` `0f07644`. `orchestration/repl_memory/strategy_store.py` `StrategyStore.retrieve()` now accepts optional `excluded_trial_ids` and skips rows whose `source_trial_id` is excluded; `scripts/autopilot/actions.py` `_build_mutation_context` derives that set from the supersession-aware journal view (`entries_with_supersessions()` when available). PromptForge/CodeMutation past-strategy context no longer retrieves strategies sourced from trials now marked `bug_corrupted_by` through append-only supersession events. Regression coverage in `tests/unit/test_strategy_store.py` covers `excluded_trial_ids`, and `tests/unit/test_autopilot_actions.py` covers propagation from the folded journal view to strategy retrieval. Validation: `python3 -m py_compile orchestration/repl_memory/strategy_store.py scripts/autopilot/actions.py tests/unit/test_strategy_store.py tests/unit/test_autopilot_actions.py`; `uv run pytest -q tests/unit/test_strategy_store.py tests/unit/test_autopilot_actions.py` -> 47 passed, 3 existing SWIG deprecation warnings; earlier broader run with `tests/unit/test_journal_supersession_events.py` -> 52 passed, same warnings; `uv run ruff check orchestration/repl_memory/strategy_store.py scripts/autopilot/actions.py tests/unit/test_strategy_store.py tests/unit/test_autopilot_actions.py`; `git diff --check --` on touched files clean.
- 2026-06-14: W6a strategy memory contamination guard increment landed in `epyc-orchestrator` `8a98868`. `StrategyStore` now carries `evidence_trial_ids` on entries, migrates existing SQLite databases with an additive `evidence_trial_ids TEXT DEFAULT '[]'` column, stores the full analyzed/distilled trial-ID set from `EvolutionManager.distill()`, and filters retrieval when any stored evidence trial intersects the folded journal exclusion set. `_build_mutation_context` now derives exclusions from folded journal rows that are corrupted, non-`ok`, explicitly excluded, or learning-excluded; legacy rows with empty evidence lists fall back to `source_trial_id` for exclusion. This is still a W6 increment, not full W6 closure, because per-insight evidence quarantine and W1 ledger-keyed strategy view integration remain open. Validation: `python3 -m py_compile` on touched modules/tests passed; `uv run ruff check` on touched modules/tests passed; `git diff --check` passed; `uv run pytest -q tests/unit/test_strategy_store.py tests/unit/test_autopilot_actions.py tests/unit/test_evolution_manager_scrub.py tests/unit/test_journal_supersession_events.py` -> 56 passed with only existing FAISS/SWIG deprecation warnings.
- 2026-06-14: W6b per-insight distillation evidence requirement landed in `epyc-orchestrator` `e78a380`. `EvolutionManager` now instructs the LLM to return `evidence_trial_ids` per insight, parses multiple common evidence-id shapes without trusting the response, validates IDs against the analyzed journal entries, and skips ungrounded multi-trial insights instead of writing broad batch-level evidence to StrategyStore. Single-row distillations can still fall back to the sole analyzed trial. If every extracted insight is ungrounded or malformed, distillation returns `status: skipped` with `reason: no grounded insights extracted` and no strategy rows are stored. This advances W6 provenance: `8a98868` remains the downstream retrieval quarantine by excluded evidence IDs, and full W1 ledger-keyed strategy view integration remains open.
- 2026-06-14: W6c promoted-strategy evidence propagation landed in `epyc-orchestrator` `433f6e8`. `KnowledgeDistiller` now loads stored `evidence_trial_ids` for raw/pattern rows, deduplicates the IDs, and passes them into new pattern and convention StrategyStore rows during raw-to-pattern and pattern-to-convention promotion. Retrieval quarantine by excluded evidence IDs therefore also suppresses promoted pattern/convention rows whose underlying evidence includes a superseded or excluded trial. This is still evidence propagation inside the StrategyStore view, not full W1 ledger-keyed strategy view integration. Validation: `python3 -m py_compile` passed; `uv run ruff check` passed; `git diff --check` passed; focused `uv run pytest -q tests/unit/test_knowledge_distiller.py tests/unit/test_autopilot_actions.py tests/unit/test_strategy_store.py` -> 55 passed, with 3 existing FAISS/SWIG warnings.
- 2026-06-18: W6 strategy evidence exclusion centralization landed in `epyc-orchestrator` `327218c`. `StrategyStore` now exposes `excluded_strategy_evidence_trial_ids()` as the shared folded-journal quarantine helper for corrupted, non-`ok`, explicitly excluded, and learning-excluded evidence rows; `_build_mutation_context()` now calls that helper instead of maintaining a caller-local exclusion fold. This reduces future bypass risk around supersession/learning-exclusion quarantine, but it remains an incremental W6 read-side guard rather than full W1 ledger-keyed strategy view integration. Validation: GitNexus impacts were LOW for `strategy_store.py` (`impactedCount=21`) and `_build_mutation_context` (`impactedCount=2`); `ruff`, `py_compile`, `git diff --check`, and `uv run pytest -q tests/unit/test_strategy_store.py tests/unit/test_autopilot_actions.py tests/unit/test_knowledge_distiller.py` -> 67 passed, with only existing FAISS/SWIG warnings.
- 2026-06-19: W6 journal-backed strategy retrieval wrapper landed in `epyc-orchestrator` `de07542`. `StrategyStore.retrieve_for_journal()` now owns the folded-journal exclusion computation for retrieval, and `_build_mutation_context()` passes the live journal into that store-level wrapper while retaining a compatibility fallback for legacy tests/doubles. This closes the mutation-context bypass that remained after `327218c`, but W6 stays open until the remaining compatibility surfaces and any other strategy retrieval consumers are audited. Validation: GitNexus impacts were LOW for `strategy_store.py` (`impactedCount=21`), `excluded_strategy_evidence_trial_ids` (`impactedCount=3`), and `_build_mutation_context` (`impactedCount=2`); `py_compile`, `ruff`, path-scoped `git diff --check`, focused strategy/action/distiller tests -> 84 passed, and the adjacent supersession/action/strategy/distiller suite -> 92 passed, with only existing SWIG/FAISS deprecation warnings. Orchestrator GitNexus was refreshed after the commit.
- 2026-06-19: W6 convention audit-table evidence propagation landed in `epyc-orchestrator` `5544a6e`. `StrategyStore` now migrates the dedicated `strategy_conventions` table with `evidence_trial_ids`, `add_convention()` persists normalized IDs, and `list_conventions()` exposes them. `StructuralLab` carries source evidence IDs into MDL-compressed convention audit rows, and `KnowledgeDistiller` passes evidence IDs when it records raw-to-pattern promotions in the convention side table. This removes a residual provenance blind spot in the audit/summary table; W6 remains open for remaining strategy-consumer and compatibility-surface audit. Validation: GitNexus impacts were LOW for `strategy_store.py` (`impactedCount=21`), `structural_lab.py` (`impactedCount=3`), and `knowledge_distiller.py` (`impactedCount=0`); `py_compile`, `ruff`, path-scoped `git diff --check`, focused structural-lab/distiller/strategy-store tests -> 47 passed, and the adjacent autopilot-action/supersession/structural-lab/distiller/strategy-store suite -> 107 passed, with only existing SWIG/FAISS deprecation warnings. Orchestrator GitNexus was refreshed and is current at `5544a6e`.
- 2026-06-19: W6 journal-aware strategy compression row selection landed in `epyc-orchestrator` `b5e71f8`. `StrategyStore.strategy_rows_for_compression()` now owns the raw-row selector used by MDL convention compression and applies the same folded-journal evidence quarantine as planner retrieval when a journal or explicit exclusion set is supplied. `StructuralLab.mdl_compress_strategies()` calls that API instead of directly selecting raw rows, so convention promotion cannot aggregate strategy rows whose source/evidence trial is superseded, failed, learning-excluded, or explicitly excluded by the folded journal view. This closed the concrete compression compatibility/API gap found after `5544a6e`. Validation: GitNexus impacts were LOW for `strategy_store.py` (`impactedCount=21`) and `structural_lab.py` (`impactedCount=3`); `py_compile`, `ruff`, path-scoped `git diff --check`, focused StrategyStore/StructuralLab tests -> 44 passed, and adjacent strategy/action/distiller/supersession suite -> 107 passed, with only existing SWIG/FAISS warnings. Orchestrator GitNexus was refreshed and is current at `b5e71f8`.
- 2026-06-19: W6 journal-aware strategy distillation promotion landed in `epyc-orchestrator` `c9871a8`. `StrategyStore.strategy_entries_for_distillation()` now owns L1/L2/L3 distillation row selection, applies folded-journal evidence quarantine and validity filtering, and returns the normalized entry dictionaries consumed by `KnowledgeDistiller`. `KnowledgeDistiller.distill()` accepts an optional folded journal or explicit exclusion set and uses the store-owned selector for both raw-to-pattern and pattern-to-convention promotion, so refuted strategy evidence cannot re-enter retrievable memory through a derived pattern or convention. This closes the remaining direct raw-SQL promotion surface found after `b5e71f8`; W6's remaining work is final W1 ledger-keyed strategy-view integration. Validation: GitNexus impacts were LOW for `knowledge_distiller.py` (`impactedCount=0`) and `strategy_store.py` (`impactedCount=21`); `py_compile`, `ruff`, path-scoped `git diff --check`, focused StrategyStore/KnowledgeDistiller tests -> 40 passed, and adjacent strategy/distiller/structural-lab/action/supersession/evolution suite -> 113 passed, with only existing SWIG/FAISS warnings.
- 2026-06-19: W1/W6 journal-keyed frontier strategy projection landed in `epyc-orchestrator` `887de60`. AutoPilot now builds the final `JournalEntry`, calls `journal.record(journal_entry)`, and only then projects a frontier strategy row through `StrategyStore.store_frontier_journal_entry()`. The projection uses deterministic IDs (`journal-frontier-trial-<trial_id>`), skips unsafe rows (non-frontier, non-`ok`, bug-corrupted, or learning-excluded), and is idempotent so restart/sync attempts cannot duplicate rows. This removes the pre-journal `strategies.db` side write that could previously leave strategy memory ahead of the append-only journal if AutoPilot crashed between the mutable strategy write and `journal.record()`. Validation: GitNexus impacts were LOW for `strategy_store.py`/`StrategyStore` (`impactedCount=21`) and `autopilot.py` (`impactedCount=0`); `py_compile`, `ruff`, path-scoped `git diff --check`, focused StrategyStore/recovery tests -> 66 passed, and adjacent action/sequential/supersession/distiller/structural-lab suite -> 91 passed, with only existing SWIG/FAISS warnings. Orchestrator GitNexus was refreshed and is current at `887de60`.
- 2026-06-19: W1/W6 frontier strategy generated-projection audit/sync landed in `epyc-orchestrator` `d9dd372`. The new projection report treats the folded journal as authority, expects `journal-frontier-trial-<trial_id>` rows for safe frontier journal entries, detects missing/unexpected/mismatched StrategyStore projections, and provides an explicit sync path that inserts only missing safe rows. Live audit/sync found 59 expected projections, inserted 59 missing rows into ignored runtime StrategyStore artifacts, and the final strict dry run was clean (`expected=59`, `projected=59`, `missing=0`, `unexpected=0`, `mismatch=0`). Caveat: embedders were down, so the one live sync used hash fallback vectors; after the run, `--write-missing` was hardened to fail closed unless semantic embedding preflight succeeds or `--allow-hash-fallback` is explicit. Validation: `py_compile`, `ruff`, scoped `git diff --check`, focused StrategyStore/projection-report tests -> 43 passed, adjacent action/recovery/supersession/distiller/structural-lab suite -> 153 passed, and orchestrator GitNexus was refreshed/current at `d9dd372`.
- 2026-06-13: W2 PromptForge failure-context coverage landed in `epyc-orchestrator` `394c1bc`. `ExperimentJournal.recent_failures()` now defaults to the supersession-aware view and excludes superseded `bug_corrupted_by` failures, while preserving `exclude_bug_corrupted=False` for raw audit reads. This prevents PromptForge mutation context from learning from contaminated failures marked by append-only supersession events. Regression coverage in `tests/unit/test_journal_supersession_events.py` proves a superseded `prompt_forge` failure is excluded by default, visible with the raw opt-out, and raw journal entries stay immutable. Validation: `python3 -m py_compile scripts/autopilot/experiment_journal.py tests/unit/test_journal_supersession_events.py`; `uv run pytest -q tests/unit/test_journal_supersession_events.py tests/unit/test_journal_prompt_sanitization.py tests/unit/test_autopilot_actions.py` -> 37 passed; `uv run ruff check scripts/autopilot/experiment_journal.py tests/unit/test_journal_supersession_events.py`; `git diff --check -- scripts/autopilot/experiment_journal.py tests/unit/test_journal_supersession_events.py` clean.
- 2026-06-14: W2 dashboard journal-view coverage landed in `epyc-orchestrator` `cdeedcd`. `src/autopilot_core/journal_reconstruction.py` now exposes public `fold_supersession_events()`, and `src/api/routes/dashboard.py` adds `_effective_journal_trial_rows()` for `/dashboard/api/autopilot_progress` duration samples and `/dashboard/api/gepa` recent-trial trajectory rows. The helper folds append-only supersession events, drops non-trial event rows, and makes GEPA recent trials skip rows superseded as `bug_corrupted_by` while leaving input rows immutable. Regression coverage in `tests/unit/test_dashboard_helpers.py` proves the fold is non-mutating, autopilot progress excludes superseded corrupted trial/event rows from sample counts, and GEPA status excludes superseded corrupted recent trials. Validation: `python3 -m py_compile src/autopilot_core/journal_reconstruction.py src/api/routes/dashboard.py tests/unit/test_dashboard_helpers.py`; `uv run pytest -q tests/unit/test_dashboard_helpers.py tests/unit/test_dashboard_pareto_representative.py tests/unit/test_journal_supersession_events.py tests/unit/test_autopilot_core_contracts.py` -> 77 passed; `uv run ruff check src/autopilot_core/journal_reconstruction.py src/api/routes/dashboard.py tests/unit/test_dashboard_helpers.py`; `git diff --check -- src/autopilot_core/journal_reconstruction.py src/api/routes/dashboard.py tests/unit/test_dashboard_helpers.py` clean.
- 2026-06-14: W2 offline analytics coverage landed in `epyc-orchestrator` `d21bbee`. `scripts/autopilot/paired_stats.py`, `scripts/autopilot/item_analytics.py`, and `scripts/analysis/task_rate_goodput_replay.py` now fold append-only supersession events using public `fold_supersession_events()` at journal read/report boundaries. Paired per-question stats, item analytics, and task-rate/goodput replay reports now match the supersession-aware archive/dashboard state and drop non-trial event rows from analysis inputs. Regression coverage: `tests/unit/test_paired_stats.py` proves `iter_journal_rows()` folds supersession events; `tests/unit/test_item_analytics.py` proves `load_journal()` folds valid rows while preserving loader semantics; `tests/unit/test_task_rate_goodput_replay.py` proves rendered report rows use folded values rather than raw superseded metrics. Validation: `python3 -m py_compile scripts/autopilot/paired_stats.py scripts/autopilot/item_analytics.py scripts/analysis/task_rate_goodput_replay.py tests/unit/test_paired_stats.py tests/unit/test_item_analytics.py tests/unit/test_task_rate_goodput_replay.py`; `uv run pytest -q tests/unit/test_paired_stats.py tests/unit/test_item_analytics.py tests/unit/test_task_rate_goodput_replay.py tests/unit/test_journal_supersession_events.py` -> 15 passed; `uv run ruff check scripts/autopilot/paired_stats.py scripts/autopilot/item_analytics.py scripts/analysis/task_rate_goodput_replay.py tests/unit/test_paired_stats.py tests/unit/test_item_analytics.py tests/unit/test_task_rate_goodput_replay.py`; `git diff --check --` on the touched analytics files clean.
- 2026-06-14: W2 preflight blacklist-audit coverage landed in `epyc-orchestrator` `965f507`. `scripts/autopilot/preflight_audit.py` `audit_blacklist()` now folds append-only supersession events before collecting corrupted trial IDs, so blacklist entries sourced from trials later superseded as corrupted are caught by preflight. Regression coverage in `tests/unit/test_autopilot_preflight_audit.py` adds a temp blacklist/journal fixture where `source_trial: 2` is only marked corrupted via a supersession event and `audit_blacklist()` returns false. Validation: `python3 -m py_compile scripts/autopilot/preflight_audit.py tests/unit/test_autopilot_preflight_audit.py`; `uv run pytest -q tests/unit/test_autopilot_preflight_audit.py tests/unit/test_journal_supersession_events.py` -> 8 passed; `uv run ruff check scripts/autopilot/preflight_audit.py tests/unit/test_autopilot_preflight_audit.py`; `git diff --check -- scripts/autopilot/preflight_audit.py tests/unit/test_autopilot_preflight_audit.py` clean.

#### Recent Checkpoint

- 2026-06-20: W6 journal-aware strategy specificity audit landed in `epyc-orchestrator` `c5cc40a5`. `StrategyStore.audit_insight_specificity()` now accepts a folded journal or explicit excluded trial IDs and filters rows through the same evidence quarantine as retrieval, compression, distillation, frontier projection, and staleness scans. Default behavior is unchanged for legacy callers, but operator audits can no longer surface refuted or learning-excluded strategy evidence as actionable specificity findings when supplied the journal view. Validation: GitNexus impact LOW for `audit_insight_specificity` and MEDIUM for the StrategyStore file overall; `py_compile`, `ruff`, scoped `git diff --check`, focused StrategyStore tests -> 40 passed, and adjacent W6 StrategyStore/StructuralLab/actions/distiller/projection suite -> 118 passed.
- 2026-06-20: W6 journal-aware strategy staleness scans landed in `epyc-orchestrator` `7287b880`. `StrategyStore.strategy_rows_for_staleness_scan()` now applies the same folded-journal evidence quarantine used by retrieval, compression, distillation, and frontier projection; `StructuralLab.staleness_invalidate_strategies()` uses that store-owned selector when a journal or explicit exclusion set is supplied and fails closed for legacy stores that cannot provide a journal-aware scan. This closes the raw StrategyStore row-scan compatibility surface where refuted evidence could still drive validity side effects or routing-checkpoint stale cascades. Validation: GitNexus impact LOW for `StructuralLab.staleness_invalidate_strategies`, LOW for the analogous store-owned selector surface, and MEDIUM for the StrategyStore file overall; `py_compile`, `ruff`, scoped `git diff --check`, focused StrategyStore/StructuralLab tests -> 55 passed, and adjacent W6 strategy/action/distiller/supersession/projection suite -> 125 passed.
- 2026-06-20: Archive-source surface audit landed in `epyc-orchestrator` `2154d37d`. The new read-only `scripts/autopilot/archive_source_surface_audit.py` codifies six residual archive-authority surfaces: operator read commands default to journal authority, dashboard state fallback is diagnostic, safety gate uses journal archive context, preflight retains a strict authority gate, repair removes the legacy state cache only with postcheck/stale-counter protection, and aggregate restart readiness includes archive authority. This is an audit guard, not W1/W4/W6 closure: authority flips, baseline ledger cutover, and live W4/W6 sequential deployment remain evidence-gated. Validation: `py_compile`, `ruff`, strict audit CLI text/JSON (`surfaces=6`, `failed=0`), focused audit tests -> 4 passed, and adjacent archive/preflight/dashboard/recovery suite -> 133 passed.
- 2026-06-20: Snapshot replay CLI tail-fold strict readiness landed in `epyc-orchestrator` `b4d88be6`. `scripts/autopilot/journal_snapshot_replay.py --strict` keeps the existing current-snapshot-only contract, while new `--allow-tail-fold --strict` accepts only when `archive_payload_from_verified_snapshot()` can materialize a restart-safe bounded tail fold. Live smoke over the active W4/W6 journal preserved the default failure (`bounded_replay_readiness=tail_unverified`, tail trial `893`, rc `1`) and passed the opt-in restart-safe gate (`strict_readiness=tail_fold_ready`, `tail_fold_payload_journal_max_trial_id=893`, rc `0`). This aligns the low-level snapshot diagnostic with aggregate restart readiness without changing AutoPilot startup authority or weakening default strict semantics. Validation: GitNexus impact MEDIUM for `build_snapshot_replay_diagnostic` and LOW for `archive_payload_from_verified_snapshot`; `py_compile`, `ruff`, focused snapshot/restart-readiness tests -> 19 passed; live CLI text/JSON smoke passed.
- 2026-06-21: Baseline ledger authority activation guard landed in `epyc-orchestrator` `fe2fe55c`. `apply_baseline_ledger_authority()` now requires both a cutover-ready ledger fold and explicit state flag `baseline_ledger_authority_enabled=true` before removing `baseline_state`, so an append-only baseline seed event cannot silently flip startup authority on the next save. `baseline_authority_report.py` and `restart_readiness_report.py` now surface `authority_enabled`; restart readiness keeps `authority_source=state_baseline` while the state cache is present. Live smoke after AutoPilot stopped at `trial_counter=930` reports baseline seed append `ready` with expected guards `trial_counter=930` and `journal_max_trial_id=929`, but `authority_enabled=false`; strict cutover remains blocked on N2/W6. Validation: GitNexus impacts LOW for the baseline authority/report targets; `py_compile`, `ruff`, focused baseline/recovery/restart/phase tests -> 82 passed; adjacent Fable5/seed/seq/audit/restart suite -> 46 passed; live ordinary restart readiness passed and strict `--require-seq-cutover --require-w6-audit` exited 1 as expected.
- 2026-06-21: Stopped AutoPilot phase health fix landed in `epyc-orchestrator` `af72216e`. `build_phase_health_report()` now treats a terminal `phase=stopped` heartbeat as healthy idle even though the process PID is dead and the heartbeat ages, while preserving dead-PID/stale blockers for active phases. This clears the false "stuck/dead active heartbeat" gate after a clean `--max-trials` exit. Live smoke reports `ok=true`, `status=stopped`, `pid_alive=false`, and no blockers for stopped PID `2412481`; Fable5 phase section is ready. Validation: GitNexus impact LOW (`impactedCount=6`); focused phase-status tests -> 11 passed as part of the 82-test suite above.
- 2026-06-21: W6 convention generated-view filtering landed in `epyc-orchestrator` `8c72719`. `StrategyStore.list_conventions()` now accepts an optional folded `journal` or explicit `excluded_trial_ids` and omits promoted convention rows whose `evidence_trial_ids` include superseded, failed, or learning-excluded trials. Default callers still see the full raw convention table, but journal-aware audits/dashboards can now avoid resurfacing refuted generated conventions. Validation: GitNexus impact LOW for `list_conventions`; `py_compile`, `ruff`, focused StrategyStore tests -> 41 passed, and adjacent W6 strategy/structural-lab/distiller/action/supersession suite -> 124 passed.
- 2026-06-21: W6 mutation-context legacy retrieval cleanup landed in `epyc-orchestrator` `b75b297`. `_build_mutation_context()` now requires `StrategyStore.retrieve_for_journal()` for planner-visible past strategy insights and skips strategy retrieval fail-closed when a legacy store lacks the folded-journal API, instead of falling back to raw `retrieve()`. This removes the last known mutation-context compatibility branch that could bypass the ledger-keyed strategy view. Validation: GitNexus impact LOW for `_build_mutation_context` and exact `retrieve_for_journal`; `py_compile`, `ruff`, and adjacent W6 action/strategy/structural-lab/distiller/supersession suite -> 125 passed.
- 2026-06-28: Archive-source empty-fallback audit refresh landed in `epyc-orchestrator` `44686922`. The static surface audit now matches the hardened runtime behavior from `91b860d0`: empty journal-backed read-command archives use a read-only empty archive and label the diagnostic as `<source>->empty-fallback`, not the retired mutable state-cache fallback. This preserves explicit `--archive-source state` as the only state-cache read path while keeping status/report/plot/digest defaulted to journal authority. Validation: GitNexus impact LOW for `_archive_for_read_command` (`impactedCount=4`) and LOW for the audit builder (`impactedCount=2`); strict `archive_source_surface_audit.py --json --strict` passed all 6 surfaces; focused audit/recovery tests -> 44 passed; `ruff`, `py_compile`, and scoped `git diff --check` passed.

#### Reporting

Tick waypoints + one-line progress entry; frontier/baseline claims per MEASUREMENT.md grammar with `policy_version` cited; on completion delete this handoff's master-index row and move to `completed/`.

## Track: evidence-plane-instrument-repair
<!-- gate: none -->

> Folded from `handoffs/active/evidence-plane-instrument-repair.md` @ `b1bf3f3f7ade` on 2026-11-02 (BRF-T1-F20, route 1a, operator D1/D5; retired row EVL-15 → RTG-02). Body moved verbatim, headings demoted two levels to nest under this track; every open and closed box kept its text and ID.

### Evidence Plane — Instrument Repair (Phase-0 hotfixes + pool sampling)

**Status**: IN PROGRESS — W1-W4b repair batch landed and full preflight passed 2026-06-13; stale `architect_coding` escalation hygiene, response/API-boundary hygiene, and Gate-3 hard-only launch hygiene are fixed; AutoPilot pre-clean-epoch artifacts `#786-#797` are quarantined, `#798` is a killed startup placeholder, and clean completed rows now include `#807-#812` with no infrastructure-collapse signature; W7 item analytics landed and now folds supersessions; preflight blacklist audit catches supersession-corrupted source trials; W5's 2026-06-15 repeat-calibration lineage remains demoted-to-prior (`33/40`, no promoted default), but orchestrator `080c4fa1` now adds a ledger-derived selector mode and a non-promoted `core_v2_ledger_20260703_min5` candidate (`40/40` selected, `79` eligible, `923` observed items, `77` current-era trusted vector rows, `25` untrusted rows, `849` pre-era rows fenced). W6 live-tree pytest/reporting checks pass, generated stack metadata and archive-authority preflight pass at `11/11`, orchestrator `51268f7` hardens direct AutoPilot startup against stale archive writeback, and W6 shadow-only live collection now has 38 audited trials in the current restart-readiness fold. Orchestrator `9a634a95` surfaces W6 audit status in `restart_readiness_report.py`, and `ff4864ed` changes cutover semantics from all-history sticky alarm to the trailing minimum audited window while still publishing cumulative anti-gaming history. Ordinary restart readiness stays separate, while `--require-w6-audit` is still blocked because the trailing-30 W6 gaming alarm is triggered (`potential_overfit_divergences=6`, cumulative divergences `7`). Sequential readiness is still volume-blocked in the same live fold (`trusted_vectors=67/120`, `seq_shadow_rows=15/30`). Trial `900` is a useful negative transfer datapoint: core quality improved over trial `899`, but audit quality dropped from `2.100` to `1.500`; trial `901` recovered audit quality to `2.400` but did not clear the active/cumulative W6 alarm or sample-size gates. The first 2026-06-20 bounded run exposed a new instrument integrity issue: default eval fanout trusted static topology even though the live fleet was full-only, and trials `889/890` showed broad request errors/crosstalk. Orchestrator `c13e5ae` now caps default eval concurrency by reachable live instances and records bounded `error_detail` in compact question rows. Trial `894` later wedged mid-`deep_eval`; orchestrator `97fa2843` adds `phase_health_report.py`, the stale heartbeat was detected, and recovery journaled `894` as `autopilot_killed_mid_trial`. The current bounded W4/W6 accrual run is live with `AUTOPILOT_SEQ_VERDICT=1`, W6 audit shadow flags, and `--max-trials 930` (wrapper PID `1091014`, Python PID `1091018`, log `/mnt/raid0/llm/tmp/autopilot_w4w6_codex_pair_after_alias_20260620T172927Z.log`); durable rows are recorded through trial `901`, and the current heartbeat shows trial `902` active in `dispatch_action`. Latest artifacts are in `epyc-orchestrator` `a4286a2d` (`seq_readiness_20260620T191636Z`, `w6_audit_block_20260620T191636Z`, and `fable5_gate_20260620T191636Z`).

**Current snapshot — 2026-06-28T21:35Z reboot wrap-up**: supersedes older trial-902/run-to-1048 and early frontier-restart details in the status history above. The v6 frontier/era fence is active (`pareto_exclude_before_ts=2026-06-26T22:07:11Z`). The prior v6 frontier closeout was reopened because `NumericSwarm` still used legacy Optuna study names after restart; orchestrator `f60197ec` now scopes persistent Optuna studies by `active_instrument_eras.autopilot_speed`, the AP-16 telemetry repair keeps frontier rows from carrying whole-library prompt-token artifacts, and orchestrator `46bb4b83` clears the rerun marker once the current-era numeric floor is met. The bad `00:44Z` AutoPilot restart (child PID `1186240`) was stopped because it had empty W4/W6 env flags. Stale pre-fix corrected daemons were also stopped before committed code resumed. The corrected run uses `AUTOPILOT_SEQ_VERDICT=1`, `AUTOPILOT_W6_AUDIT_BLOCK=1`, `AUTOPILOT_W6_AUDIT_N=10`, `AUTOPILOT_W6_AUDIT_EVERY_N_TRIALS=1`, `AUTOPILOT_W6_AUDIT_SHADOW_ONLY=1`, `AUTOPILOT_PLANNER_TIMEOUT=600`, and `--max-trials 2000`; `frontier_rerun_required.required=false` cleared after trial `#1016` with `8/8` completed current-marker numeric trials. A10 planner-hint distillation is applied and active: `44` deterministic `opseed-*` rows are present in StrategyStore/FTS, fresh retrieval finds the guardrail/table rows, and the live AutoPilot has `AUTOPILOT_PLANNER_HINTS=1`. Current pre-reboot Python PID is `2143322`; latest observed runtime state was trial `1051`, `planner_invoke`. Orchestrator `2682387a` makes `audit_block_report.py` accept an audited-row timestamp fence and makes `restart_readiness_report.py` default W6 cutover to `autopilot_state.json:pareto_exclude_before_ts`; follow-up W6 reporting fixes make not-yet-full trailing windows report finite sample-size/alarm horizons. Latest strict fold (`epyc-orchestrator/orchestration/reports/restart_readiness_20260628T213549Z.json`): archive authority aligned through journal max `1050`, baseline authority fold ready but disabled, sequential cutover ready (`193/120` trusted vectors, `116/30` seq-shadow rows), and W6 audit cutover ready (`32/30` current-era audited rows, `gaming_alarm=false`, no active or cumulative overfit divergences). Authority remains disabled/default-off because no deliberate cutover has been executed. After reboot, rerun strict readiness before any authority flip.

**Current promotion-readiness refresh — 2026-07-04T00:15Z**:
`epyc-orchestrator/orchestration/reports/core_v2_promotion_readiness_20260704T001543Z.{json,md}`
reconfirms the ledger-derived `core_v2_ledger_20260703_min5` candidate is
artifact-clean (`40` question rows) and selection-clean (`selected=40`,
`eligible=79`, `observed=923`, `source_rows=77`, unresolved `0`). Promotion
remains intentionally blocked only by the missing human-owned
`autopilot_quality` E4/core instrument-era row declaring the matching
`core_id`. Orchestrator `ea8a3e39` now makes the report emit a draft-only
operator era-row snippet under `operator_era_row_draft`; agents still must not
append it to `instrument_eras.yaml`. No code change or same-seed calibration
rerun is indicated before that operator decision.

**Prior addendum — 2026-07-05T03:40Z**: AutoPilot is live as PID `1397463`
with `--max-trials 2000` after the 2026-07-05 maintenance restart and is
currently in trial `1152` (`deep_eval`, tier `2`). A report-plane sidecar
audited W8/seq/restart/Fable reports and found no report-only bug: W8 remains
evidence-bound, with recent candidate `b738287be98c3372` blocked as
`unreplayable_action=seed_batch`, no fresh promotion eval, no sequential
confirmation, and no finalized candidate. Next action is still to collect a
recent replayable accumulating candidate, then fresh promotion-eval plus seq
confirmation evidence. Separately, orchestrator `c7590be6` enriches default-off
BSV observe signatures with already-journaled tool/route/latency process
signals; this does not change any authority gate.

**Current addendum - 2026-07-05T23:55Z**: AutoPilot is live as PID `3267768`
on orchestrator `a13a2948` with `--max-trials 3000`, local-ingest planner
drafting, local-frontdoor critique, Claude fallback, planner hints, tool
sentinels, sequential verdicts, and W6 audit accrual. The current W8
candidate-generation path is code-live: orchestrator `3364bdd7` repairs
critic-fallback deferrals into replayable candidate attempts, and `a13a2948`
repairs the empty-param numeric contract so a new `numeric_trial` with
`params={}` is an Optuna request whose concrete applied params are journaled by
dispatch. Trial `1194` is the first live canary: W8 fallback produced
`numeric_trial` on `chat_pipeline`, and NumericSwarm applied
`chat.try_cheap_first_quality_threshold=0.8742715026951258`. That canary
completed as a valid replayable attempt but was reverted for `tool_use`
regression and blacklisted only for the exact concrete param. The current live
state is trial `1196` in planner invocation after trial `1195` invalid-skipped
already-blacklisted `graph_router=true`; the remaining work is a different
keepable replayable candidate followed by sequential confirmation and fresh
promotion-eval proof.
Ordinary `seed_batch`, `deep_eval`, and `structural_prune` remain valid outside
the specific W8 candidate-generation blocker.

**Wrap-up addendum — 2026-07-05**: T3 semantics are now corrected to the
expert/hard workflow slice while preserving T3 `core_id` evidence continuity.
The latest eval-coverage report now surfaces tier detail and least-covered
non-sentinel suites: `2457` distinct qids / `24210` scored rows over stable
pool `52210`, upper-bound coverage `4.706%`, repeat factor `9.8535x`, with
T1 `1771/21133` (`8.3803%`, `255` eval-bearing trials), T2 `843/26667`
(`3.1612%`, `18` trials), and T3 `160/5431` (`2.9461%`, `1` trial). Least-
covered non-sentinel suites are `tool_use`, `agentic`, `skill_transfer`,
`long_context`, `real_suite_v1`, `mode_advantage_hard`, `mode_advantage`,
`coder`, `bigcodebench`, and `cruxeval`. This is planner pressure rather than
a blocker; A9 remains `attention/no_runnable_batches`. Orchestrator `4bc1711e`
also makes the generated AutoPilot PNGs render tier-segregated HV and Pareto
quality/speed series for T1/T2/T3, matching the live dashboard's same-tier view
without changing any production optimization or authority gate.

Current blockers before any next decision point:

- **Policy/evidence gating remaining**: W6 now satisfies the default `30` trusted audited-row minimum inside the active v6 era (`32/30` at wrap-up), with `gaming_alarm=false` and no active alarm-clearance debt; older `100` audited rows remain fenced historical priors. The remaining gate is operational, not data-volume: rerun strict readiness after reboot and perform any sequential/baseline authority flip only as an explicit cutover decision.
- **W5 ledger candidate exists; activation is fail-closed on era authority**: the stale repeat-calibration shortfall (`33/40`) is no longer the active selector blocker. Orchestrator `080c4fa1` produced `benchmarks/prompts/core_v2_ledger_20260703_min5.jsonl` plus `orchestration/reports/core_v2_selection_ledger_20260703_min5.json` from current-era ledger rows (`min_attempts=5`, selected `40/40`, unresolved `0`). Orchestrator `039bb287` adds the activation guard/report: EvalTower refuses configured designed cores unless `instrument_eras.yaml` has an active `autopilot_quality` row whose `core_id` matches. Orchestrator `ea8a3e39` refreshes `core_v2_promotion_readiness_20260704T001543Z` and emits the exact draft-only era row for operator review, while activation remains blocked until the human-owned row is appended and validated. Remaining W5 work is the operator era-promotion decision; do not rerun same-seed calibration as the default next step.
**Created**: 2026-06-12
**Priority**: NOW/HIGH — live damage: the t775 baseline ratchet is failing ~half of honest trials today
**Spec**: [fable5-findings-01-impl-plan.md](../completed/fable5-findings-01-impl-plan.md) Phase 0 + Phase 2 (exact sites/changes/acceptance per item) and [fable5-findings-01-measurement-and-integrity.md](../completed/fable5-findings-01-measurement-and-integrity.md) §3 (defect evidence) — read before claiming any waypoint
**Related**: [autopilot-continuous-optimization.md](autopilot-program.md) · [eval-tower-verification.md](eval-tower-program.md) (EV-4 calibration waits on this) · [../../MEASUREMENT.md](../../MEASUREMENT.md) §P-QUAL-T1/P-QUAL-PROMO (the instrument card this work realizes) · [../../repos/epyc-orchestrator/orchestration/instrument_eras.yaml](../../repos/epyc-orchestrator/orchestration/instrument_eras.yaml) — append era E4 when the repaired instrument lands · downstream: [evidence-plane-ledger-and-sequential-verdicts.md](autopilot-program.md#track-evidence-plane-ledger-and-sequential-verdicts)

#### Why

The autopilot's instrument resolution sits below the effect sizes being optimized: of the
fixed 43-question T1 set, ~8 can never pass (`expected=''` gate, missing pandas, vl unresolved)
and ~14 more are saturated — effective discriminating n ≈ 10–14 (spec Phase-2 evidence). On
top of that, eight live gate defects (worst: trial 775 ratcheted the T1 baseline to its
all-time noise max, so the −5% gate now fails the modal honest outcome) are actively writing
spurious reverts/blacklists. This handoff stops the live damage, repairs the dead questions,
then replaces the accidental seed=42 core with a designed, versioned sampling architecture
over the 53K pool. Sites, schemas and acceptance live in the spec — not duplicated here.

#### Waypoints

- [x] **W1 — ratchet + double-check hotfixes** (impl 0.1+0.2, ~1 day): `safety_gate.py` `update_baseline` now requires same-tier frontier reproduction evidence (min 3) and promotes the representative median; `gate.check()` caches verdicts per `EvalResult` so repeated calls do not double-count MAD/consecutive-failure state. One-time live-state reset applied: `orchestration/autopilot_state.json` `baselines_by_tier['1']` 1.9534883720930234 → 1.813953488372093, the 34-run same-config seed-batch median over trials 658-776.
- [x] **W2 — gate plumbing hotfixes** (impl 0.3–0.5, ~1 day): `Baseline.update_tier()` refreshes `frontdoor_speed`; `hybrid_eval()` skips T0 by default with legacy T0 gate behind `AUTOPILOT_HYBRID_T0_GATE=1`; self-criticism uses `max(0.02, 3/n)` and emits `unchanged` inside resolution. Remaining follow-up: optional historical last-120 label distribution report, if needed.
- [x] **W3 — narrative-leak + quantum clamps** (impl 0.6–0.8, ~half day): strategy-store writes require frontier + passed gate + not learning-excluded; distillation filters corrupt/excluded rows; `deep_eval` schema clamp explicitly rejects planner-supplied `n_questions`/`seed`. Acceptance covered by focused unit tests.
- [x] **W4 — instrument repair** (impl 2.0, 2–3 days): `expected==''` now scores only for expected-free scorers (`code_execution`, `programmatic`) and sampled empty-expected text-scorer rows are consciously replaced from the same suite; pandas is installed in the uv dev env; VL trace root cause was dual plumbing (image requests could enter learned text routing + OCR inherited a missing/stale `llama-mtmd-cli` path). Repairs landed in `acd0f7e`, `8446d86`, and `41b0ce8`: NFKD fold, T0 `sentinel_<suite>` namespacing, Seeder per-question seen-state persistence, image requests bypass learned text routing, OCR MTMD fallback/subprocess library path fix. Acceptance: seed-42 n=50/n=100/n=500 pool scan has zero unscoreable sampled rows; live OCRBench `vl_ocr_0124` EvalTower trace returns `BOGUS`, `correct=true`, `route_used=worker_vision`.
- [x] **W4b — executable-oracle pool repair** (zero-inference): 2026-06-13 commits `954d8fd` and `a3ec440` made `code_execution` require an executable oracle (`TEST_CASES`, real top-level asserts, unittest cases, or entry-point assertion), then made T1/T2 sampling draw suite-local scoreable rows first with global scoreable backfill. Preflight now gates on the actual sampled launch sets while quarantining raw invalid `code_execution` rows and fully unscoreable suites as diagnostics. Acceptance: full preflight passed 9/9; `Question Pool` had 53,181 rows, F1 tags 11,767/11,767, T1 sampled 100/100 unique, T2 sampled 500/500 unique, invalid `code_execution` quarantined 1,946/3,150, and `usaco` quarantined as fully unscoreable.
- [ ] **W5 — designed core_v2** (impl 2.1, 2–3 days + calibration): `benchmarks/prompts/core_v2.jsonl` (~40 items, per-item p∈[0.2,0.8], stratified), versioned `core_id` journaled per trial. **Current-lineage code substrate branch-ready 2026-06-14**: `epyc-orchestrator` worktree `/mnt/raid0/llm/tmp/core-v2-current-refresh-20260614`, unified branch `feat/w6-rotating-audit-block-current-20260614`, head `3a63bc1`, based on live HEAD `fad942c`. This includes the W5 loader commit `a3dd6d9` (opt-in `AUTOPILOT_T1_CORE_ID`/`AUTOPILOT_T1_CORE_PATH`, full-row/id-reference JSONL cores, fail-closed handling, `core_id` telemetry), selector commit `c29de28` (`Add core v2 selection utility`) to turn calibration/journal `question_results` into a candidate `core_v2.jsonl` plus JSON report, and `3a63bc1` (`Add core v2 calibration runner`) for repeat same-seed T1 calibration rows under `/mnt/raid0/llm/tmp/core_v2_calibration` without writing AutoPilot journal/archive state. The separate selector branch remains `/mnt/raid0/llm/tmp/core-v2-selection-tool-20260614` at `85417ba`; the stale provenance worktree remains `/mnt/raid0/llm/tmp/core-v2-prep-worktree` commit `a7be2bd`. **First real calibration batch completed 2026-06-15** (`core_v2_calibration_20260615T003043Z`, 3×300 same-seed T1 rows): repeat metrics were q/r `2.090/0.947`, `2.100/0.950`, and `2.050/0.933`. Strict selector gate did not pass: `selected_count=21`, `target_size=40`, `shortfall=19`, `unresolved_selected_count=0`; no `benchmarks/prompts/core_v2.jsonl` was promoted. Two-repeat extension `core_v2_calibration_ext2_20260615T050124Z` added q/r `2.060/0.920` and `2.100/0.957`, improving the strict selector to `selected_count=33`, `shortfall=7`, unresolved `0`, still no-go. No-go reports are in `epyc-orchestrator` `3037ec2` and `8db5292`. **2026-07-03 ledger-derived refresh**: orchestrator `080c4fa1` adds `core_v2_select.py --source ledger`, which loads folded rollover journals, applies `autopilot_state.pareto_exclude_before_ts`, excludes corrupted/skipped/invalid/no-vector rows, and writes provenance. It emitted non-promoted `core_v2_ledger_20260703_min5` with selected `40/40`, eligible `79`, observed `923`, current-era trusted rows `77`, untrusted rows `25`, pre-era fenced rows `849`, and unresolved `0`. **2026-07-03 activation guard**: orchestrator `039bb287` makes `EvalTower.eval_t1()` fail closed when `AUTOPILOT_T1_CORE_ID` is configured without a matching active `autopilot_quality` era `core_id`, adds `core_v2_promotion_report.py`, and records `core_v2_promotion_readiness_20260703T110529Z` showing artifact/selection OK and `missing_core_era` as the sole blocker. **2026-07-04 era-row draft**: orchestrator `ea8a3e39` updates the readiness report to include the draft-only E4/core `autopilot_quality` row in `core_v2_promotion_readiness_20260704T001543Z`; this is operator provenance, not an agent append. **Remaining W5**: operator-owned E4/core era promotion decision; optionally compare against the 2026-06-15 33 flip set. Do not treat the repeat-calibration no-go as the active blocker.
- [ ] **W6 — rotating audit block** (impl 2.2, 1 day): +10 fresh stratified pool questions/trial, trial-id-seeded; overfit alarm (core-delta vs audit-delta correlation) + pool-level estimator. **Current-lineage code substrate branch-ready 2026-06-14**: stacked on W5 in worktree `/mnt/raid0/llm/tmp/core-v2-current-refresh-20260614`, branch `feat/w6-rotating-audit-block-current-20260614`, commits `20a1573` (`Add default-off W6 rotating audit block`) and `1b9cbb2` (`Add W6 audit block report`). Adds default-off `AUTOPILOT_W6_AUDIT_BLOCK=1`, `AUTOPILOT_W6_AUDIT_N`, and `AUTOPILOT_W6_AUDIT_EVERY_N_TRIALS`; `dispatch_action()` threads `trial_counter` into `EvalTower`; T1 appends deterministic trial-id-seeded audit rows, journals compact per-qid `partition` fields, and exposes partition quality/count summaries in `eval_details.details`. The report tool reads partitioned journal rows and emits read-only core-vs-audit quality/divergence diagnostics. **Live-tree no-inference check 2026-06-15**: focused W6 pytest passed (`7 passed, 15 deselected`), and current-journal `audit_block_report.py` found `trial_count=701`, `audited_trial_count=0`. **Standalone W6 plumbing probe 2026-06-15**: `AUTOPILOT_W6_AUDIT_BLOCK=1 AUTOPILOT_W6_AUDIT_N=2 AUTOPILOT_W6_AUDIT_EVERY_N_TRIALS=1 AUTOPILOT_EVAL_CONCURRENCY=1 timeout 600s uv run python scripts/autopilot/core_v2_calibrate.py --calibration-id w6_audit_plumbing_20260615T082700Z --out-jsonl /mnt/raid0/llm/tmp/w6_audit/w6_audit_plumbing_20260615T082700Z.jsonl --n 5 --repeats 1 --seed 42 --trial-id-base 910010` wrote one standalone row with reliability `1.000`, partition counts `core=5` and `audit=2`, report `orchestration/reports/w6_audit_plumbing_20260615T082700Z.{json,md}` (`audit_quality_0_3=1.5`, `core_quality_0_3=1.8`). The aborted larger `3x100` smoke produced no JSONL row and is not evidence. **Shadow-only guard 2026-06-15**: Orchestrator `a4d510a` added default-on `AUTOPILOT_W6_AUDIT_SHADOW_ONLY=1`, so future W6 audit rows remain in the per-question ledger/reporting partitions while decision metrics stay paired-core-only unless the operator explicitly sets `AUTOPILOT_W6_AUDIT_SHADOW_ONLY=0`. **Startup hygiene 2026-06-15**: Orchestrator `51268f7` makes direct AutoPilot startup repair archive-authority drift from journal fold before lifecycle saves; validation included 58 archive/recovery/preflight tests, full preflight `11/11`, and no-trial start/shutdown. **Live collection posture 2026-06-20**: after trials `889/890` exposed that default eval fanout could overrun the current full-only fleet, orchestrator `c13e5ae` added live-fleet-capped default eval concurrency plus compact `error_detail` telemetry; focused validation passed (`44` pytest tests, ruff, diff-check). Orchestrator `9a634a95` adds W6 audit visibility to aggregate restart readiness, with `--require-w6-audit` blocking on the active gaming alarm. Current run `autopilot_w4w6_codex_pair_after_alias_20260620T172927Z` is live with `AUTOPILOT_W6_AUDIT_BLOCK=1`, `AUTOPILOT_W6_AUDIT_N=10`, `AUTOPILOT_W6_AUDIT_EVERY_N_TRIALS=1`, `AUTOPILOT_W6_AUDIT_SHADOW_ONLY=1`, and `--max-trials 930`; durable evidence is recorded through trial `901`, with heartbeat trial `902` active. Remaining W6 acceptance needs clean alarm-free audit evidence before any overfit/generalization policy claim.
- [x] **W7 — item analytics** (impl 2.3, 2 days, zero inference): landed on current F5 lineage 2026-06-13 in `epyc-orchestrator` commit `ab5df87` (`Add autopilot item analytics report`), a clean current-lineage cherry-pick of original branch-ready `cb577e0`. Added `scripts/autopilot/item_analytics.py` weekly/per-100-trials suite + future per-qid analytics, generated `orchestration/reports/item_analytics_2026-06-12.{md,json}` from 664 live journal rows, and verdicted the 5 pinned-zero/watchlist suites: `usaco`, `vl`, `instruction_precision`, and `bigcodebench` are historical artifact-contaminated; `mode_advantage_hard` is the remaining genuinely-hard candidate pending per-qid/core_v2 calibration. Current journal rows do not persist per-question vectors, so discrimination stays blocked on N2 ledger writes. Follow-up `d21bbee` makes `load_journal()` fold append-only supersession events while preserving loader semantics.
- [ ] **W8 — promotion evals** (impl 2.4, ~1 day wiring): `confirmed` candidates trigger a fresh stratified n=200–500 draw; promotion needs core-confirmed AND promotion-delta CI excluding regression. Acceptance: per MEASUREMENT.md P-QUAL-PROMO. **2026-07-05 report-plane status**: sparse-baseline false AP-24 failures are repaired in orchestrator `b2deb1b5`, benign `seq_accumulating` AP-24 `excluded` snapshots stay active in W8 trajectory reporting in `076699ff`, and the replay-eligibility refresh in `b8cb6e26` makes benign excluded accumulating candidates replayable in planner evidence. A fresh sidecar audit found the reports agree and no safe report-only bug remains. The stale `seed_batch` blocker state is superseded by the live `a13a2948` candidate-generation canary: trial `1194` produced a replayable `chat_pipeline` numeric attempt with applied threshold `0.8742715026951258`, then reverted on `tool_use` regression and blacklisted only that exact param. W8 remains open until a keepable replayable candidate gets sequential confirmation and fresh promotion-eval proof.

#### Gates & pitfalls

- W1-W4b are live in code and the question-pool launch gate is clear. Orchestrator API was reloaded on `2026-06-13` after `a338738`; full preflight passed 9/9 after `a3ec440`, and Gate-3 hard telemetry passed after the stale-role fix. Follow-up commits `4a7efbe` and `c62dbd8` harden chat response JSON serialization and log API-boundary failures explicitly. Gate-3 hard-only progress/timeout hygiene landed as `b1985be` and passed on a fresh one-worker API. The conservative resource-contention quarantine now covers `#786-#797`; runtime projections were restored from clean backup through `#785`, and completed clean-epoch rows `#799/#800` are dominated vector-bearing observations. Resume only in uncontested windows; do not overlap CPU-heavy indexing/embedding/certification work with measurement.
- Do NOT naively rotate the core: fresh-questions-per-trial multiplies trial variance ~4× (spec Phase-2 preamble). The fixed paired core is the design; the pool feeds audit/analytics/promotion instead.
- W5's calibration batch is inference — per-run operator approval required; W8 consumes `confirmed` verdicts from [evidence-plane-ledger-and-sequential-verdicts.md](autopilot-program.md#track-evidence-plane-ledger-and-sequential-verdicts).
- Core/instrument changes invalidate cross-version comparisons — bump `core_id`, append era E4 to `instrument_eras.yaml`, never mix n=38/n=43/core_v2 frontiers.
- The first sweep's vl explanation ("no vision server") was WRONG (ports live, plumbing present) — trace before fixing (`feedback_observe_before_diagnosing`).

#### Reporting

Tick waypoints + one-line progress entry per phase; claim numbers per MEASUREMENT.md grammar (e.g. `[P-QUAL-T1/core_v2, n, date]`); on completion delete this handoff's master-index row and move to `completed/`.

#### Checkpoints

- 2026-06-12 W1-W3 verification: `uv run pytest tests/unit/test_autopilot_core_contracts.py tests/unit/test_eval_tower_concurrency_metrics.py tests/unit/test_eval_tower_hybrid_eval.py tests/unit/test_autopilot_controller_io.py tests/unit/test_evolution_manager_scrub.py tests/unit/test_safety_gate_baseline_eligibility.py tests/unit/test_per_suite_regression_resolution.py tests/unit/test_self_criticism_resolution.py` → 81 passed; `git diff --check` clean. Autopilot was not running when the T1 state reset was applied; only API workers were live.
- 2026-06-12 W4 verification: API reload + `/config/attest` saw 6 homogeneous workers; OCR live request on `ocr_0124.png` returned `BOGUS` in 0.98s; EvalTower end-to-end trace for `vl_ocr_0124` returned `BOGUS`, `correct=true`, `route_used=worker_vision`, `tokens_generated=1`; pool scan after replacement sampler found n=50 bad=0, n=100 bad=0, n=500 bad=0 after replacing 1 `instruction_precision` + 4 `agentic` unscoreable rows; `uv run pytest ... test_lightonocr_llama_server.py` W4/routing suite → 319 passed, 5 warnings.
- 2026-06-12 W7 verification: `uv run --with pytest pytest tests/unit/test_item_analytics.py -q` → 4 passed, 1 pytest config warning; `uv run ruff check scripts/autopilot/item_analytics.py tests/unit/test_item_analytics.py` → pass; `uv run ruff format --check ...` → pass; `uv run python -m py_compile scripts/autopilot/item_analytics.py` → pass; generated report from `/mnt/raid0/llm/epyc-orchestrator/orchestration/autopilot_journal.jsonl`.
- 2026-06-13 W7 current-lineage landing: live branch `fix/substring-scorer-digit-separators` now includes `ab5df87` on top of F5 quarantine commit `a7b87c1`. Validation: `python3 -m py_compile scripts/autopilot/item_analytics.py tests/unit/test_item_analytics.py` -> pass; `uv run --with pytest pytest tests/unit/test_item_analytics.py -q` -> 4 passed; `uv run ruff check scripts/autopilot/item_analytics.py tests/unit/test_item_analytics.py` -> pass; `uv run ruff format --check scripts/autopilot/item_analytics.py tests/unit/test_item_analytics.py` -> pass; `uv run python scripts/autopilot/item_analytics.py --journal orchestration/autopilot_journal.jsonl --out-dir /mnt/raid0/llm/tmp/item-analytics-current-smoke-20260613` -> wrote JSON+MD report; `git diff --check HEAD~1..HEAD` -> pass.
- 2026-06-14 W7/preflight supersession follow-up: `epyc-orchestrator` `d21bbee` makes `scripts/autopilot/item_analytics.py` fold append-only supersession events at load time, and `965f507` makes `scripts/autopilot/preflight_audit.py audit_blacklist()` fold supersession events before collecting corrupted source-trial IDs. Validation: focused py_compile passed; `uv run pytest -q tests/unit/test_item_analytics.py tests/unit/test_autopilot_preflight_audit.py tests/unit/test_journal_supersession_events.py` covered the new fixtures across the two commits; focused ruff and `git diff --check` passed on the touched files.
- 2026-06-12 W5 prep verification: branch `feat/core-v2-instrument-prep` `a7be2bd`; GitNexus risk was HIGH for `EvalTower.eval_t1` / `_aggregate` and CRITICAL for `sample_from_pool`, so the branch does not touch `sample_from_pool` and remains opt-in/default-off. Validation: `python3 -m py_compile scripts/autopilot/eval_tower.py scripts/autopilot/safety_gate.py tests/unit/test_eval_tower_instrument_repair.py` -> pass; `uv run --with ruff ruff check scripts/autopilot/eval_tower.py scripts/autopilot/safety_gate.py tests/unit/test_eval_tower_instrument_repair.py` -> pass; focused pytest suite `tests/unit/test_eval_tower_instrument_repair.py tests/unit/test_eval_tower_concurrency_metrics.py tests/unit/test_autopilot_hle_fields.py tests/unit/test_safety_gate_baseline_eligibility.py tests/unit/test_eval_tower_hybrid_eval.py tests/unit/test_per_suite_regression_resolution.py tests/unit/test_token_accounting_invariant.py` -> 51 passed, 1 pytest config warning; `git diff --check` -> pass. `ruff format --check` is not claimed because these existing AutoPilot files would receive broad unrelated formatting churn.
- 2026-06-14 W5 current-lineage refresh: isolated worktree `/mnt/raid0/llm/tmp/core-v2-current-refresh-20260614`, branch `feat/core-v2-instrument-prep-current-20260614`, commit `a3dd6d9`, based on live orchestrator HEAD `fad942c`. GitNexus impact on the current eval path was HIGH (`EvalTower.eval_t1` 23 impacted symbols/modules, `hybrid_eval` 14 direct callers, `_aggregate` 31 impacted symbols/modules), so the refresh stayed isolated and did not touch live checkout during AutoPilot T2. Validation: `python3 -m py_compile scripts/autopilot/eval_tower.py scripts/autopilot/safety_gate.py tests/unit/test_eval_tower_instrument_repair.py tests/unit/test_eval_tower_hybrid_eval.py tests/unit/test_autopilot_hle_fields.py` -> pass; `uv run --with ruff ruff check scripts/autopilot/eval_tower.py scripts/autopilot/safety_gate.py tests/unit/test_eval_tower_instrument_repair.py tests/unit/test_autopilot_hle_fields.py` -> pass; focused pytest `tests/unit/test_eval_tower_instrument_repair.py tests/unit/test_eval_tower_concurrency_metrics.py tests/unit/test_autopilot_hle_fields.py tests/unit/test_safety_gate_baseline_eligibility.py tests/unit/test_eval_tower_hybrid_eval.py` -> 39 passed, 1 pytest config warning; `git diff --check` -> pass. Additional fail-closed tests cover missing core files, path-without-id misconfiguration, metadata/core-id mismatch, unscoreable full rows, and id-reference resolution through the existing pool loader.
- 2026-06-14 W5 offline selector substrate: initially isolated in `/mnt/raid0/llm/tmp/core-v2-selection-tool-20260614`, branch `feat/core-v2-selection-tool-20260614`, commit `85417ba`, then cherry-picked onto the unified W5/W6 branch as `c29de28`. Additive new script/test only: `core_v2_select.py` reads calibration/journal JSONL, treats missing `partition` as `core`, estimates per-item p(correct), stratifies medium-difficulty candidates, maps stable eval qids back to question-pool rows, and emits candidate `core_v2.jsonl` plus a JSON selection report. Validation: `python3 -m py_compile scripts/autopilot/core_v2_select.py tests/unit/test_core_v2_select.py` -> pass; `uv run --with ruff ruff check scripts/autopilot/core_v2_select.py tests/unit/test_core_v2_select.py` -> pass; `uv run --with pytest pytest -q tests/unit/test_core_v2_select.py` -> 5 passed, 1 pytest config warning; `git diff --check` -> pass. Combined validation after cherry-pick on the unified branch: py_compile + ruff for `core_v2_select.py`/`audit_block_report.py` and tests -> pass; `uv run --with pytest pytest -q tests/unit/test_core_v2_select.py tests/unit/test_audit_block_report.py` -> 9 passed, 1 pytest config warning. Current-journal dry run on 2026-06-14 selected only `5/40` candidates at `min_attempts=2` (`source_rows=700`, `observed_items=55`, `eligible_items=5`), confirming the real W5 batch still needs repeated same-seed calibration rather than unrelated random seeds.
- 2026-06-15 W5 real calibration no-go: standalone calibration `core_v2_calibration_20260615T003043Z` ran 3×300 same-seed rows against the neutral API and wrote only `/mnt/raid0/llm/tmp/core_v2_calibration/core_v2_calibration_20260615T003043Z.jsonl`. Repeat metrics were q/r `2.090/0.947`, `2.100/0.950`, and `2.050/0.933`; repeat 3 was noisier, with about 17 worker-path 504s, but no hard-crash signature. Strict selector parameters (`target_size=40`, `min_attempts=2`, `p in [0.2,0.8]`) yielded 21 eligible selected items from 300 observed, shortfall 19, unresolved 0; the outcome distribution was 197 always-correct, 82 always-wrong, 9 at `p=1/3`, and 12 at `p=2/3`. No `core_v2.jsonl` was promoted. Durable no-go report: `epyc-orchestrator` `3037ec2`, `orchestration/reports/core_v2_selection_core_v2_calibration_20260615T003043Z.no_go.json`.
- 2026-06-15 W5 extension no-go: standalone extension `core_v2_calibration_ext2_20260615T050124Z` ran 2×300 same-seed rows (`trial_id` 900003/900004) against the neutral API, while AutoPilot stayed paused at `trial_counter=822`. Extension repeat metrics were q/r `2.060/0.920` and `2.100/0.957`. Five-row strict selector parameters (`target_size=40`, `min_attempts=2`, `p in [0.2,0.8]`) yielded 33 eligible selected items, shortfall 7, unresolved 0; medium-band distribution was 4 at `p=0.2`, 5 at `p=0.4`, 5 at `p=0.6`, and 19 at `p=0.8`, with 80 always-wrong and 187 always-correct. No `core_v2.jsonl` was promoted. Durable extended no-go report: `epyc-orchestrator` `8db5292`, `orchestration/reports/core_v2_selection_core_v2_calibration_20260615T003043Z_plus_ext2.no_go.json`.
- 2026-07-03 W5 ledger-derived selector: orchestrator `080c4fa1` adds `--source ledger` to `scripts/autopilot/core_v2_select.py` and commits a non-promoted candidate/report pair (`benchmarks/prompts/core_v2_ledger_20260703_min5.jsonl`, `orchestration/reports/core_v2_selection_ledger_20260703_min5.json`). Live read-only probe: `selected=40`, `eligible=79`, `observed=923`, `source_rows=77`, `min_attempts=5`, `unresolved=0`, `era_fence_source=state`, `exclude_before_ts=1782511631.0`, `untrusted_rows=25`, `era_excluded_rows=849`. Validation: `uv run pytest tests/unit/test_core_v2_select.py tests/unit/test_core_v2_calibrate.py -q` (`10 passed`), `uv run ruff check scripts/autopilot/core_v2_select.py tests/unit/test_core_v2_select.py`, and `git diff --check`.
- 2026-07-03 W5 activation guard/report: orchestrator `039bb287` adds `src/autopilot_core/instrument_era_guard.py`, wires the guard into `EvalTower.eval_t1()`, and adds `scripts/autopilot/core_v2_promotion_report.py`. The generated report `orchestration/reports/core_v2_promotion_readiness_20260703T110529Z.{json,md}` says the `core_v2_ledger_20260703_min5` artifact has `40` question rows, selection evidence is OK (`selected=40`, `eligible=79`, `observed=923`, `source_rows=77`, unresolved `0`), and promotion is blocked only because `instrument_eras.yaml` has active E3 quality rows but no core-bearing E4 row. Validation: `uv run pytest tests/unit/test_eval_tower_instrument_repair.py tests/unit/test_core_v2_promotion_report.py -q` (`26 passed`), adjacent `test_core_v2_select.py test_core_v2_calibrate.py test_sequential_verdict.py test_autopilot_hle_fields.py test_real_suite_eval_packager.py -q` (`28 passed`), focused Ruff, and `git diff --check`.
- 2026-06-14 W6 rotating-audit current-lineage substrate: stacked on the W5 worktree in branch `feat/w6-rotating-audit-block-current-20260614`, commits `20a1573`, `1b9cbb2`, and unified head `3a63bc1`, still isolated from the live AutoPilot checkout. GitNexus impact stayed HIGH on the eval path (`EvalTower.eval_t1`, `_aggregate`, `hybrid_eval`) and LOW on `dispatch_action`/`QuestionResult`, so the patch remains default-off and branch-ready only. Validation for `20a1573`: py_compile on touched eval/action/test files -> pass; `uv run --with ruff ruff check scripts/autopilot/eval_tower.py scripts/autopilot/actions.py tests/unit/test_eval_tower_instrument_repair.py tests/unit/test_eval_tower_concurrency_metrics.py tests/unit/test_autopilot_actions.py tests/unit/test_eval_tower_hybrid_eval.py` -> pass; focused pytest `tests/unit/test_eval_tower_instrument_repair.py tests/unit/test_eval_tower_concurrency_metrics.py tests/unit/test_autopilot_actions.py tests/unit/test_eval_tower_hybrid_eval.py tests/unit/test_autopilot_hle_fields.py` -> 62 passed, 1 pytest config warning; downstream reader pytest `tests/unit/test_paired_stats.py tests/unit/test_item_analytics.py tests/unit/test_seq_readiness_report.py tests/unit/test_planner_evidence.py tests/unit/test_autopilot_core_contracts.py tests/unit/test_safety_gate_baseline_eligibility.py tests/unit/test_token_accounting_invariant.py` -> 50 passed, 1 pytest config warning; `git diff --check` -> pass. Validation for `1b9cbb2`: `python3 -m py_compile scripts/autopilot/audit_block_report.py tests/unit/test_audit_block_report.py` -> pass; `uv run --with ruff ruff check scripts/autopilot/audit_block_report.py tests/unit/test_audit_block_report.py` -> pass; `uv run --with pytest pytest -q tests/unit/test_audit_block_report.py` -> 4 passed, 1 pytest config warning; `git diff --check` -> pass. Additive W5 calibration-runner validation for `3a63bc1`: `python3 -m py_compile scripts/autopilot/core_v2_calibrate.py tests/unit/test_core_v2_calibrate.py` -> pass; `uv run --with ruff ruff check scripts/autopilot/core_v2_calibrate.py tests/unit/test_core_v2_calibrate.py` -> pass; `uv run --with pytest pytest -q tests/unit/test_core_v2_calibrate.py` -> 4 passed, 1 pytest config warning; `git diff --check` -> pass.
- 2026-06-15 W6 AutoPilot row batch: detached max-trials-832 run PID `2730020` completed trials `#822-#825` as clean dominated/excluded rows. `#822` q/s/r=`1.920/26.779/0.920` (`reproduction_confirmed`, code-mutation extraction failed so no code patch applied); `#823` q/s/r=`1.860/28.787/0.920` (`reproduction_confirmed`, `memrl_retrieval` numeric); `#824` q/s/r=`1.860/25.286/0.920` (`mad_noise`, `ure_uncertainty_shadow_log=false` structural experiment); `#825` q/s/r=`1.920/26.654/0.940` (`mad_noise`, `memrl_retrieval` numeric). `audit_block_report.py` on the live journal produced `trial_count=705`, `audited_trial_count=4`, core `126/200` (`1.890`), audit `25/40` (`1.875`), `delta_audit_minus_core=-0.015`, and potential overfit divergences `1`. Orchestrator git dirt remained limited to runtime `scripts/autopilot/short_term_memory.md`. The AutoPilot process remains alive, and follow-on trial `826` is in flight as a `deep_eval` tier-2 run.
- 2026-06-13 W4b launch-hygiene repair: `epyc-orchestrator` commit `954d8fd` tightened the deterministic code scorer so code-exec rows without executable tests no longer pass by merely importing; preflight now audits live EvalTower scoreability instead of stale hard-coded `usaco`/`web_research` labels; SearXNG default moved from the BGE server port `8090` to the live SearXNG service `8888`; six blacklist rows sourced from journal entries tagged `bug_corrupted_by` were removed. Validation: py_compile on touched scorer/preflight/eval/test files; focused pytest `tests/unit/test_debug_scorer_code_execution.py tests/unit/test_eval_tower_instrument_repair.py tests/unit/test_web_search_searxng_config.py` -> 11 passed; focused ruff passed; `git diff --check` passed. Initial full preflight passed 8/9 and exposed the Question Pool capacity gap that `a3ec440` superseded below.
- 2026-06-13 W4b sampler/preflight repair: `epyc-orchestrator` commit `a3ec440` added scoreable sample backfill and changed preflight to gate on the actual T1/T2 launch samples. Validation: py_compile passed; focused pytest suite -> 33 passed; focused ruff passed; `git diff --check` passed; full preflight after API reload PID `3460290` passed 9/9 with T1 sampled 100/100 unique and T2 sampled 500/500 unique. Gate-3 hard telemetry passed; soft `web_research` produced a full `/chat` 500 traced to stale `architect_coding` escalation/fallback rather than SearXNG.
- 2026-06-13 stale-role + API-boundary follow-up: `epyc-orchestrator` commit `a338738` rerouted `coder_escalation -> architect_general` and made `architect_general` terminal for proactive escalation. Focused validation passed (183 routing/langgraph/proactive/integration tests plus executor/repl escalation subsets), GitNexus was rebuilt, API reload PID `3486453` carried the sentinel/structured-output env, and Gate-3 hard telemetry passed again. The soft `web_research` probe still returned 500, but progress JSONL showed successful completion through `frontdoor -> coder_escalation -> architect_general`; repeated `/health` calls alternated clean vs degraded circuit state across the six uvicorn workers while direct probes stayed healthy. Follow-up single-worker launch hygiene landed as `4a7efbe` (non-finite chat response metrics are sanitized before JSON rendering) and `c62dbd8` (FastAPI response-validation/unhandled-exception handlers log tracebacks). A bounded single-worker soft probe stayed slow and was killed by the client after the useful diagnostic window; health remained ok and no new 500/traceback appeared. Fresh API reload PID `3531008` on `7e6ac9c` passed preflight 9/9, but Gate-3 hard telemetry stalled twice before first sentinel output and both clients were killed/verified gone; this was superseded by `b1985be` hard-only progress/timeout hygiene.
- 2026-06-13 Gate-3 hard-only + quarantine follow-up: `epyc-orchestrator` commit `b1985be` added per-request Gate-3 progress, request timeout, and soft-probe skip controls; full preflight and Gate-3 hard-only telemetry passed on a fresh one-worker API. Pause preservation during in-flight trials landed in `512dfb6`. Operator-conservative quarantine now covers journal rows `#786-#797` as `resource_contention_20260612`, except killed placeholders `#796/#798` as `autopilot_killed_mid_trial`; runtime projection was restored from clean backup through `#785`. Completed clean-epoch rows `#799/#800` wrote 55 vectors each, were dominated, and left T1 frontier `[256, 610, 736, 775, 776, 780]` unchanged. Supersession-event substrate and stale pause-reason cleanup landed afterward in `3ff7af4`; state is paused at `trial_counter=801` with no in-flight marker.

#### Research Intake Update — 2026-08-21 (Stage-2b, intake-1279#record)

- [ ] **(Z) Fix the llama-server log retention hole.** [too-big: retention ownership and missing-window cause require subsystem investigation] A correctness question about production
      (upstream #27442, disclosed 2026-08-20) **could not be answered from retained evidence**: no
      llama-server or orchestrator log on disk is newer than 2026-08-11, a nine-day gap spanning
      disclosure. Where the frontdoor log *does* cover, it is clean — 11,670 timing lines, zero
      instances of the failure signature, six healthy requests at ≥16K including one at 64,019 prompt
      tokens — which is a genuinely useful negative, but only for its window.
      Fix retention for `epyc-orchestrator/logs/llama-server-*.log`.
      **Recorded so it is not re-raised as a detector gap:** the `empty_generation` detector
      (`llama_server.py`, `_is_empty_long_generation`) is **active** at its 30 s default and its logger
      channel is retained. Because the failure occurs on a *cold full prefill* — minutes of CPU at
      17K+ tokens — that threshold is comfortably exceeded, so the detector is **not blind** to the
      mechanism and its silence is meaningful. Retention is the gap; the detector is not.

  - Historical partial checkpoint, 2026-10-30 (not task completion): orchestrator `4cd6622f37079f44477ed3f138cc99639ef71685` changes the remaining legacy shell truncation to append and adds a UTC launch boundary, matching the current stack launcher. The prior checkpoint reported a redirect fixture and syntax check, but that implementation commit contains no relevant production-retention regression test. No copy-truncate/rotation/cron/deletion or service operation was applied. This prevents loss of already emitted bytes across that launch path; historical missing windows cannot be reconstructed and emission/external-deletion guarantees are not inferred. [Evidence](../../artifacts/compute/refactor-c5-r3-and-source-closures-20261030.json).

  - Reopened 2026-10-31 after the operator audit: the redirect change is in an uncalled legacy script; the real production-path retention gap remains undiagnosed, with no relevant regression test. Production already appended before that legacy change. Diagnose the actual path, implement the fix and test it. Original task text and historical missing-window limitation remain unchanged. [Git evidence](../../artifacts/engineering/tick-integrity-20261031/log-retention-reopen.json). [no-belief: correction of premature completion; hygiene only]


  - Partial source checkpoint, 2026-10-31 (original task remains open): APP implementing `df0fd72bb4f7f43ab5cf5dd9cd949edf9d604e89`, published on main `448c6294388d471287ce38fc94f0e2805647fd81`, fixes a separate present-day production-wrapper default-path defect: the wrapper supplies its checkout only as a fallback after `.env` evaluation, preserving explicit environment/conditional `.env` settings and other shared-library callers. Actual shell controls pass 10/10, focused Ruff/shell checks and required `make gates` pass. This does not demonstrate that this wrapper caused the August gap: the actual stack already appended before that window, retained launch receipts begin in October, and no historical cleanup/rotation mechanism has been established. [Scoped Git evidence](../../artifacts/engineering/log-retention-wrapper-20261031/EVIDENCE.json); [regression source](https://github.com/pestopoppa/epyc-orchestrator/blob/df0fd72bb4f7f43ab5cf5dd9cd949edf9d604e89/tests/unit/test_production_launcher_paths.py). No task closure or quota credit. [belief: cc]

## Track: evidence-plane-ledger-and-sequential-verdicts
<!-- gate: none -->

> Folded from `handoffs/active/evidence-plane-ledger-and-sequential-verdicts.md` @ `b1bf3f3f7ade` on 2026-11-02 (BRF-T1-F20, route 1a, operator D1/D5; retired row EVL-16 → RTG-02). Body moved verbatim, headings demoted two levels to nest under this track; every open and closed box kept its text and ID.

### Evidence Plane — Per-Question Ledger + Sequential Verdicts (+ game layer)

**Current checkpoint - 2026-07-06T08:01Z W8 forced replay/AP-9 repair
deployed**: AutoPilot is live as PID `3935151` with
`--max-trials 3000`, launched through the canonical Fable authority daemon with
`AUTOPILOT_PLANNER_PRIMARY=local_frontdoor`,
`AUTOPILOT_PLANNER_CRITIC=local_worker`, Claude fallback, planner hints, tool
sentinels, sequential verdicts, and W6 audit flags. `phase_health_report.py
--require-current-code --json` reports trial `1217`,
`action_type=numeric_trial`, `phase=dispatch_action`, `pid_alive=true`, and
`code_stale=false` after the restart loaded orchestrator `e3b13edd`.

**Current checkpoint - 2026-07-14T00:00Z seq-fallback unblock**: the
authority daemon restarted cleanly with `AUTOPILOT_PLANNER_SPEND_BREAKER=0`
and `code_stale=false`, and live trial `1346` forced the seq
baseline-reference draw through retryable `seed_batch n=50` target
`seed_batch_n50_t1317_no_progress_infra`. Orchestrator commit `402e461b`
teaches the baseline-reference forcing and seq-gate preflight deferral paths to
prefer retryable seed fallback targets when the blocked target is
infra-contaminated, while preserving manual/token-gated blacklist purge for
durable bans. Validation already passed in the orchestration session:
`uv run --frozen pytest -q tests/unit/test_autopilot_sequential_wiring.py tests/unit/test_autopilot_actions.py`
returned `177 passed`, and `ruff` passed. This is a retry-only re-exploration
unblock, not a permit to purge durable blacklist entries automatically.

**Current checkpoint - 2026-07-14T17:42Z local-planner canary refresh**: the
canonical Fable authority wrapper was restarted through
`start_fable_authority_daemon.py` with absolute `--max-trials 1401` under
supervisor PID `2381139` and child PID `2381140`. The authority env now pins
`AUTOPILOT_PLANNER_PRIMARY=local_frontdoor`,
`AUTOPILOT_PLANNER_CRITIC=local_ingest`, Claude fallback, and
`AUTOPILOT_PLANNER_SPEND_BREAKER=0`; the prompt contract was hardened so
`json:autopilot_actions` must carry exactly one JSON object, not an array.
Dry-run validation confirmed the new split, and the focused ruff/pytest batch
passed (`41` tests). Log:
`/mnt/raid0/llm/tmp/autopilot_fable_authority_20260714T174249Z.log`.

**Current checkpoint - 2026-07-14T19:33Z planner-parser hardening**: commit
`51bbbf64` landed after `feeacb07` and makes `extract_critique()` fail closed
unless the critic emits a named `json:autopilot_critique` fence with a valid
explicit decision. Trial `1352` hit the paused boundary, the pause latch was
cleared, and the old supervisor/child `2381139` / `2381140` were stopped and
verified gone before the new daemon started at `2026-07-14T19:33:05Z`
(`supervisor=2491402`, `child=2491410`, `pid_age_verified_landed=true`).
Validation passed with `ruff` on
`scripts/autopilot/planner_coordinator.py` plus
`tests/unit/test_autopilot_planner_coordinator.py`, and
`uv run pytest tests/unit/test_autopilot_planner_coordinator.py -q`
reported `52 passed`.

First post-fix cycles were clean: trial `1353` produced a `local_frontdoor`
draft plus a valid approve fence from `local_ingest`; trial `1354` produced a
`local_frontdoor` draft plus a valid reject fence from `local_ingest`;
planner-provider-health stayed healthy. The remaining blocker is still the seq
gate's promotion fallback, which continues to redirect to `seed_batch n=50`
because `rate_axis_unreachable` is unresolved and P0.1-P0.3 remain pending.

**2026-07-06T16:44Z report refresh**: regenerated
`orchestration/reports/w8_promotion_trajectory_20260706T164403Z.{json,md}`
and `orchestration/reports/fable5_gate_report_20260706T164403Z.{json,md}`.
W8 remains `progressing` with replay-eligible candidates
`80aa44d93a242af5`, `289c4fc0fb5a334d`, and `d3f28243801548b2`, but Fable5
is still blocked because phase health is stale (AutoPilot PID `131226` is
gone), the W6 gaming alarm is still triggered, and tool-use activation is now
ready because the orchestrator launcher now sets
`AUTOPILOT_TOOL_SENTINELS=1` alongside `ORCHESTRATOR_STRUCTURED_TOOL_OUTPUT=1`.

Orchestrator `1639748a` is deployed in that daemon. It threads the current
`selectable_action_types` set into `planner_coordinator.plan_with_providers()`,
treats known-but-unavailable action types as unusable before critique, and
rejects critic revisions that reintroduce unavailable types. The first observed
post-restart planner turn used the fully local routine path: the spend breaker
selected `local_frontdoor/local_worker`, the local critic approved the draft,
and the higher-tier probe guard intentionally forced T3 pressure. This means the
old "deploy `1639748a` at boundary" instruction is complete.
Orchestrator `9522b76e` prevents the higher-tier probe guard from overriding a
planner-selected frontier-moving action while outcome progress is already
frontier-stalled, and `78ae65e6` escalates that stale-outcome signal from prompt
advice into a bounded pre-dispatch fallback: seed/eval/housekeeping actions are
replaced with a metric-bearing numeric trial when frontier admission is stale,
while `numeric_trial`, prompt/code/GEPA mutations, one-flag structural
experiments, and `train_routing_models` pass through unchanged.
Orchestrator `e3b13edd` repairs the last replay/dispatcher seam exposed by
trials `1213`-`1216`: W8 replay pressure now remains active while replay or
confirmation is still required, materialized multi-param NumericSwarm
candidates are force-replayable, and AP-9 is bypassed only for an exact
`seq_candidate_replay_forced` match on the current trial. Trial `1217` is now
evaluating the source-trial-`1197` `repl_executor` replay with
`repl.turn_token_cap=1964` and
`repl.frontdoor_non_tool_token_cap=866`; the earlier skipped rows remain audit
evidence and were not deleted.

Startup StrategyStore health remains exact (`1,420` SQLite rows, `1,420` FAISS
vectors, `1,420` FTS rows, `100.0%` coverage), so the stale-FAISS failure mode
is not active in this run. W8 itself remains open until a replayable candidate
becomes keepable and later receives sequential confirmation plus fresh
promotion-eval evidence. The next quiet-window evidence runs are DS-E1 KV
measurement, J12 think-loop probe, A9 contrast-replan collection,
`real_suite_v1`, then W8/Fable readiness reports. The same boundary reloaded the
orchestrator API, so dashboard fixes `554b71af` and `b81f3113` are now served:
tap-inferred holders stay visible when `/proc` reports the same physical holder,
and snapshot region-lock frames use the fresh scanner rather than the TTL cache.

**Prior checkpoint - 2026-07-05T23:58Z W8 local-planner canary live**:
AutoPilot is live as PID `3267768`; latest observed checkpoint is trial `1196`
`planner_invoke` with `--max-trials 3000`,
planner hints, tool sentinels, W6 audit accrual, sequential verdicts, and W4-W6
authority env. The running daemon is on orchestrator `a13a2948` and uses the
routine local planner path: `AUTOPILOT_PLANNER_PRIMARY=local_ingest`,
`AUTOPILOT_PLANNER_CRITIC=local_frontdoor`, and
`AUTOPILOT_PLANNER_CRITIC_FALLBACK=claude`. Startup verified StrategyStore
search health (`1,420` SQLite/FAISS/FTS rows, `100.0%` coverage).

The stale `2935890` / `local_worker` / Codex-critic restart target is
superseded. Orchestrator `3364bdd7` repaired the W8 critic-reject loop so W8
candidate-generation pressure rewrites fallback seed/deep/prune deferrals to a
replayable `numeric_trial` or one-flag `structural_experiment` before the
reject-loop guard. Orchestrator `a13a2948` repaired the empty-param contract:
a new `numeric_trial` with `params={}` is an Optuna request, while historical
rows that stayed empty remain unreplayable as logged. W8 only counts the row
after dispatch journals concrete applied params.

The first post-fix planner turn exercised the path: `local_ingest` drafted an
invalid no-op structural experiment, `local_frontdoor` rejected it, W8 fallback
substituted `numeric_trial` on `chat_pipeline`, and NumericSwarm materialized
`chat.try_cheap_first_quality_threshold=0.8742715026951258` before restarting
the API and entering T1 eval. Trial `1194` then failed safety on a `tool_use`
suite regression (`-1.200` vs `-0.600` threshold), was reverted, and
auto-blacklisted only the exact concrete `chat_pipeline` param. This proves the
local draft/local critic safety loop can recover into a replayable W8 candidate
attempt, but W8 remains open until a later candidate becomes keepable and
receives sequential confirmation plus fresh promotion-eval evidence.
Trial `1195` then invalid-skipped `structural_experiment` `graph_router=true`
because that exact action was already auto-blacklisted.

Clarification: ordinary `seed_batch`, `deep_eval`, and `structural_prune` are
not globally invalid AutoPilot strategies. They are currently unavailable only
for the specific W8 candidate-generation blocker because they cannot create the
replayable candidate row W8 needs. They remain valid for coverage, T2/T3
validation, and non-W8 work.

**Blacklist freshness audit - 2026-07-14**: preflight blacklist scanning now
walks journal batch shards, including `orchestration/autopilot_journal_1.jsonl`,
instead of reading only the base shard. That audit surfaced infra-contaminated
and stale blacklist entries, so the prompt wording now calls out blacklist
freshness, expiry, and purge scope explicitly. Retry-only re-exploration is
allowed for the audited infra cases we classified as repeatable transport
failures rather than durable semantic dead ends: trial `1302`
(`langgraph_coder`, connection-refused) and seed-batch no-progress infra cases
trial `1317` (`n=50`) and trial `1320` (`n=10`).

**Prior status — 2026-07-04T21:24Z W8 authority-env checkpoint**: W4/W6 authority wiring remains current, and AutoPilot is live as PID `1122670` at trial `1146` with `--max-trials 2000`, launched through `scripts/autopilot/start_fable_authority_daemon.py` in `epyc-orchestrator` `07883e63`. The launcher enforces `AUTOPILOT_SEQ_VERDICT=1`, W6 audit flags, `AUTOPILOT_PLANNER_HINTS=1`, `AUTOPILOT_TOOL_SENTINELS=1`, planner timeout `600`, and stepping stones. Strict Fable gate smoke (`fable5_gate_report.py --json --strict --require-current-code`) is clean: `ready=true`, blockers `[]`, and the only active next action is `collect_w8_promotion_eval_evidence`; phase health is current-code clean at trial `1146` in `planner_invoke` with `prompt_chars=62902`. The immediately prior bare-env daemon PID `3796930` was stopped after Fable detected missing authority/tool env; recovery journaled trial `1137` as `autopilot_killed_mid_trial`. `epyc-orchestrator` `0a6336c7` fixes the last W8 replay/report mismatch found in trial `1135`: benign AP-24 `keep_revert_decision=excluded` rows that are still `seq.state=accumulating` are now replay-eligible in AutoPilot, while reverted or failure-bearing excluded rows remain terminal. This aligns the live replay selector with the earlier report-plane fix `076699ff`, so the six stale accumulating W8 candidates are no longer silently skipped. The remaining W8 blockers are evidence, not wiring: `combined_E_below_required`, `fresh_promotion_eval_required`, and `seq_confirmation_required`. `epyc-orchestrator` `9b7a9ebe` closes the last StrategyStore startup-only path by refreshing planner-hint prompt rows and convention bindings before each controller prompt; with `AUTOPILOT_PLANNER_HINTS=1`, newly seeded StrategyStore rows are visible to planner prompts each turn. `epyc-orchestrator` `8185c0f7` extends `restart_readiness_report.py` with `--require-current-code`, phase heartbeat path/staleness controls, and Fable strict follow-up wiring, so W4/W6 restart/cutover checks fail closed when the live AutoPilot process predates runtime source changes.

**Current checkpoint — 2026-07-05T14:00Z**: AutoPilot is live as PID `2370903`
after the FAISS, tool-sentinel, and numeric-candidate harness repairs.
`phase_health_report.py --json --require-current-code` reports `status=active`,
trial `1168`, `phase=planner_invoke`, `code_stale=false`, blockers `[]`,
planner hints enabled, sequential verdict enabled, W6 audit accrual enabled,
and tool-sentinel env active. The API was reloaded with
`AUTOPILOT_TOOL_SENTINELS=1` plus `ORCHESTRATOR_STRUCTURED_TOOL_OUTPUT=1`, and
sampled worker attestation passed across six workers. The indexed episodic
FAISS mirror is now exact after orchestrator `a0148edd`: `526,729/526,729`
indexed vectors, matching `id_map.npy` and `reembedded.npz`, `100.0%` live
overlap, and `0` missing/stale IDs. Orchestrator `4400df02` constrains stale
broad numeric-surface blacklists to explicit human-scoped surface bans or
concrete params, so W8 candidate generation is no longer exhausted by stale
surface-level skips. Orchestrator `8be68732` fixes the REPL-pinned
tool-sentinel prompt contract so sentinels demand executable
`TOOL("get_eval_secret", ...)` code. Orchestrator `6a0d60af` normalizes
planner-friendly numeric params such as `keep_ratio` into applicator keys like
`kv.keep_ratio` and returns structured skip outcomes instead of handler no-ops.
Trial `1167` exposed the pre-fix `keep_ratio` handler no-op and should be read
as harness-bug evidence, not negative `kv_compaction` evidence. Trial `1156`
completed as T3 `deep_eval` evidence but is not W8 replayable because
`deep_eval` is observational. Trial `1158` refuted the latest W8 replayable
candidate, and trial `1159` was infrastructure-poisoned while the CPU stack was
down. Current W8 state remains blocked on the real next action:
`w8_candidate_generation_required: no replay-eligible accumulating candidate`.
Fresh promotion-eval evidence and seq confirmation are still absent until
AutoPilot produces a new keepable, replayable `numeric_trial` or
`structural_experiment` candidate.

**Prior checkpoint — 2026-07-05T05:34Z**: AutoPilot is live as PID `1634689`
after the trial `1153` completion / trial `1154` boundary restart. Stale PID
`1527127` was paused at the boundary, terminated with SIGTERM, and verified
gone. Gate-3 hard tool telemetry passed, the API is reloaded with
`AUTOPILOT_TOOL_SENTINELS=1`, and `phase_health_report.py --json
--require-current-code` reports `status=active`, trial `1154`, phase
`planner_invoke`, `code_stale=false`, planner hints enabled, sequential
verdicts enabled, and W6 audit accrual enabled. Orchestrator `026f8e29` is now
live in the daemon planner-evidence path and surfaces aggregate W8
replay-pressure. Orchestrator `a53a74ad` fixed the remaining W8 report/selector
mismatch: the trajectory report now checks journal `config_snapshot` payloads
the same way live AutoPilot replay selection does, so empty-params
`numeric_trial` rows and `seed_batch` candidates are not treated as
replay-eligible. Current W8 state remains blocked on the real next action:
`w8_candidate_generation_required: no replay-eligible accumulating candidate`.
Fresh promotion-eval evidence and seq confirmation are still absent; W8 needs a
new keepable, replayable `numeric_trial` or `structural_experiment` candidate
before promotion evidence can accrue. Orchestrator `c7590be6` enriches
default-off BSV observe signatures with already-journaled tool/route/latency
process signals, still observe-only and outside the authority path. Orchestrator
`9a6815c8` makes `deep_eval tier=3` the concrete planner example for thin T3
workflow coverage/frontier evidence while preserving tier 2 for
comprehensive/W8 promotion-eval evidence. Orchestrator `231e5050` makes W8
planner evidence spell out that `seed_batch` candidates are observational and
unreplayable; orchestrator `fd9dd3bd` adds `planner_evidence.py` to the
phase-health current-code drift guard.

**Prior deployment note — 2026-07-05T05:44Z/06:00Z**: Orchestrator `0dd63df9`
tightens the W8 replay-pressure prompt text after trial `1154` selected
`structural_prune` while W8 candidate generation was the live blocker.
`structural_prune` remains valid as an AutoPilot action, but it is not
replayable under the W8 fresh-promotion contract; W8 replay accepts only
`numeric_trial` with non-empty applied `params` or `structural_experiment` with
non-empty `flags`. Trial `1154` reached its boundary, reverted, and PID
`1671008` ran current code with this guidance until the later trial `1155`
boundary restart recorded above.

**Prior report — 2026-07-04T20:58Z**: live strict Fable smoke after the `0a6336c7` restart reported `ready=true`, blockers `[]`, phase trial `1137`, W8 stale accumulating count `6`, and next actions `collect_w8_promotion_eval_evidence` plus `activate_tool_use_sentinel_lane`. The selector smoke over the current journal chose stale candidate `a5dd4182e654c21e` from source trial `932`, proving the replay lane can drain benign excluded accumulating candidates. That daemon was later found to be missing the authority/tool env and was replaced by PID `1122670`. W8 remains not promotable until a replayed candidate reaches joint sequential confirmation and then passes the fresh promotion eval.

**Current-code readiness guard — 2026-07-04T11:10Z**: live smoke of `restart_readiness_report.py --json --strict --require-seq-cutover --require-w6-audit --require-current-code` returned `restart_ready=true`, blockers `[]`, `phase_health_ok=true`, `phase_health_status=active`, `phase_health_trial_id=1119`, `phase_health_code_stale=false`, `seq_cutover_ready=true`, and `w6_audit_cutover_ready=true`. The aggregate Fable report with `--require-current-code` also keeps the `w4_w6_restart_cutover` section ready; remaining blockers are unrelated DS-E1/A9 gates.

**Prior report — 2026-07-03T15:55Z**: refreshed artifacts `epyc-orchestrator/orchestration/reports/seq_readiness_20260703T152547Z.{json,md}`, `restart_readiness_20260703T152547Z.json`, and `fable5_gate_report_20260703T152547Z.{json,md}` kept W4/W6 ready (`trusted_vectors=221/120`, `seq_shadow_rows=144/30`, W6 audited rows `58/30`, `gaming_alarm=false`, restart readiness `true`). W8 remained evidence-bound rather than code-blocked: latest seq trial `1086`, candidate `968b0a9da524bdbe`, `combined_E=0.932744` versus required `100.0`, `seq_state=accumulating`, no pending/finalized fresh promotion eval, and open requirements `combined_E_below_required`, `fresh_promotion_eval_required`, `seq_confirmation_required`. Trajectory artifact `epyc-orchestrator/orchestration/reports/w8_promotion_trajectory_20260703T155509Z.{json,md}` showed `143` W8 snapshots across `35` candidates, `2` active recent replays, `5` refuted candidates, and `22` stale accumulating candidates.

**Historical status — 2026-06-20 W4/W6 accrual context**: W1/W2/W3/W5 are landed, W7 game-layer hardening is complete, and W4 default-off mechanism + shadow wiring are live but authority was disabled. With `AUTOPILOT_SEQ_VERDICT` off, runtime behavior stays legacy. With it on, AutoPilot can dual-log sequential shadow rows, thread per-question/task-rate evidence through central and action-local gates, journal failed-trial seq blocks, and only finalize baseline promotion after the fresh-eval/update-baseline path accepts. Current blocker is evidence volume plus W6 transfer risk, not missing code: the current aggregate restart-readiness fold after trial `902` reports trusted vectors `68 / 120` and seq shadow rows `16 / 30`. The same report includes W6 audit cutover status from `epyc-orchestrator` `9a634a95` and trailing-window semantics from `ff4864ed`: `w6_audited_trial_count=38` crosses the default `30` row minimum, but `--require-w6-audit` still fails because the trailing-30 W6 gaming alarm is triggered (`potential_overfit_divergences=6`; cumulative divergences `7`; `619c1f6d` reports `28` future clean audited rows needed to age active alarm events out if no new divergences occur). `epyc-orchestrator` `2a5454b4` now makes W6 audit cutover evidence use the same explicit trust metadata as sequential readiness, excluding bug-corrupted, skipped/invalid, and tier-0 audit-bearing rows; the live fold currently reports `w6_raw_audited_trial_count=38`, `w6_audited_trial_count=38`, and `w6_untrusted_audited_trial_count=0`, so the current alarm is not caused by an explicitly untrusted audit row. Trial `900` increased core quality versus trial `899` but dropped audit quality from `2.100` to `1.500`, so it strengthened the hold rather than supporting cutover; trial `901` recovered audit quality to `2.400` but does not clear the active/cumulative W6 alarm or sample-size gates, and trial `902` advanced sequential shadow progress without clearing cutover readiness. The 2026-06-20 accrual window exposed live-eval fanout contamination when the stack was full-only: trials `889/890` produced broad 5xx/error/crosstalk symptoms, so `epyc-orchestrator` `c13e5ae` now caps default eval concurrency by reachable live fleet instances and keeps bounded `error_detail` in compact question rows. Trial `894` later wedged mid-`deep_eval`; `epyc-orchestrator` `97fa2843` added a phase-health report, the stale PIDs were killed after ordinary restart readiness passed, and recovery journaled `894` as `autopilot_killed_mid_trial`. `epyc-orchestrator` `63e4dcba` exposes the same phase-health classification in dashboard process status, `887f50f5` refreshes the phase heartbeat from eval question progress, `b7f75e47` surfaces the health field in the dashboard UI, and `418d2599` will surface eval batch progress in phase/Fable5 reports after the next safe AutoPilot restart. `epyc-orchestrator` `092abb39` repairs direct `seq_readiness_report.py` CLI execution from the repo root; live direct JSON smoke now reports the same blockers (`68 < 120`, `16 < 30`) instead of failing on imports. The active bounded W4/W6 accrual run is `/mnt/raid0/llm/tmp/autopilot_w4w6_codex_pair_after_alias_20260620T172927Z.log`, wrapper PID `1091014`, Python PID `1091018`, `--max-trials 930`; durable rows are recorded through trial `902`, and the current heartbeat shows trial `903` active in `dispatch_action`. Latest artifacts are in `epyc-orchestrator` `a4286a2d` (`seq_readiness_20260620T191636Z`, `w6_audit_block_20260620T191636Z`, and `fable5_gate_20260620T191636Z`).
**Pre-reboot snapshot — 2026-06-28T21:35Z wrap-up**: supersedes older trial-902/run-to-1048 counts in the status history above. AutoPilot is live under the v6+iqk era with `--max-trials 2000`, corrected W4/W6 env, and activated A10 planner hints (`AUTOPILOT_PLANNER_HINTS=1`); current pre-reboot Python PID is `2143322`, with latest observed runtime state trial `1051`, phase `planner_invoke`. Sequential sample volume is sufficient (`trusted_vectors=193/120`, `seq_shadow_rows=116/30`), archive authority is aligned through journal max `1050`, and the guarded baseline seed append made the baseline ledger fold ready. W6 audit cutover now also passes inside the v6 era (`w6_audited_trial_count=32/30`, `gaming_alarm=false`, `gaming_alarm_clearance_clean_trials_required=0`). Authority was still disabled then because no deliberate cutover had been performed. Current proof artifact: `epyc-orchestrator/orchestration/reports/restart_readiness_20260628T213549Z.json`. The next decision gate after reboot is to rerun `restart_readiness_report.py --json --strict --require-seq-cutover --require-w6-audit`, then run/review the disagreement/cutover report before enabling sequential verdict or baseline authority.
**Created**: 2026-06-12
**Priority**: HIGH — the keystone change; owner of the Queue-3 restart bundle
**Spec**: [fable5-findings-01-impl-plan.md](../completed/fable5-findings-01-impl-plan.md) Phase 1 + Phase 5, and [fable5-findings-01c-sequential-verdict-spec.md](../completed/fable5-findings-01c-sequential-verdict-spec.md) (the full e-process: update rule, thresholds, state schema, exact wiring sites) — read before claiming any waypoint
**Related**: [bulk-inference-campaign.md](eval-tower-program.md#track-bulk-inference-campaign) Queue 3 — **J11/BSV-2 + K-SKILL-1 co-land at the same restart, flag-isolated** (`AUTOPILOT_BSV2_ACCEPT_GATE` / `AUTOPILOT_SKILL_EFFICACY_GATE`) · [evidence-plane-instrument-repair.md](autopilot-program.md#track-evidence-plane-instrument-repair) (Phase 2.0/2.1 prereqs for full power) · [autopilot-continuous-optimization.md](autopilot-program.md) · [../../MEASUREMENT.md](../../MEASUREMENT.md) §P-QUAL-T1 (decision rule = this handoff)
**History**: [evidence-plane-ledger-and-sequential-verdicts-history-through-2026-06-19.md](../archived/evidence-plane-ledger-and-sequential-verdicts-history-through-2026-06-19.md) preserves completed W1-W7 implementation chronology compacted out of this active handoff.

> **Live visibility update — 2026-06-20.** `epyc-orchestrator` `9cc932fe`
> (`Surface live eval progress from phase reports`) makes
> `build_phase_health_report()` fill missing in-flight eval counters from the
> active `logs/autopilot.log` tail when the heartbeat belongs to the live phase
> path and the running process predates structured eval counters. Heartbeat
> counters still win when present, and log-tail matches are trial-scoped. Live
> smoke during trial `902` reported `T2 450/500 (70% correct)` in both
> `phase_health_report.py --json` and the aggregate Fable5 phase section,
> without restarting or disturbing the W4/W6 accrual process.
> `epyc-orchestrator` `f5b1898a` then surfaced threshold-derived remaining
> counts in restart/Fable5 reports. Current live smoke after durable trial `902`
> shows `52` trusted-vector trials and `14` sequential-shadow rows still needed
> for N2 sample-size gates, while
> W6 audited rows are above floor (`38/30`) but blocked by the gaming alarm.
> `epyc-orchestrator` `619c1f6d` adds the W6 alarm clearance horizon: live
> smoke reports `28` future clean audited trials are needed to age the active
> alarm events out of the trailing-30 window, assuming no new divergences occur.

> **Live visibility update — 2026-06-21.** `epyc-orchestrator` `4cfe6567`
> (`Surface W4/W6 cutover horizon`) adds a combined strict-cutover horizon to
> `restart_readiness_report.py` and `fable5_gate_report.py`. The horizon is a
> read-only lower bound over remaining trusted-vector rows, seq-shadow rows,
> W6 audited rows, and W6 alarm-clearance rows; it does not change gate
> semantics. Live smoke during active trial `916` reports trusted vectors
> `81/120` (`39` remaining), seq-shadow rows `29/30` (`1` remaining), W6 audited
> rows `51/30` (`0` remaining), W6 alarm clearance `26`, and combined horizon
> `39` with blocker `seq_trusted_vectors`.
> Follow-up live smoke after durable trial `916` reports trusted vectors
> `82/120` (`38` remaining), seq-shadow rows `30/30` (`0` remaining), W6 audited
> rows `52/30` (`0` remaining), W6 alarm clearance `25`, and combined horizon
> `38` with blocker `seq_trusted_vectors`.
> `epyc-orchestrator` `bfd29e96` (`Wait for seeding responses after idle slots`)
> fixes a HIGH-risk seeding observability/evidence-quality issue in
> `_call_orchestrator_with_slot_poll`: after a slot reports idle while the HTTP
> request is still pending, the wrapper now gives the orchestrator response a
> short completion grace before emitting `slot_idle_orphan`. This targets false
> `[INFRA_SKIP] worker_general` rows without changing reward semantics.
> Follow-up live smoke after durable trial `917` reports trusted vectors
> `83/120` (`37` remaining), seq-shadow rows `31/30` (`0` remaining), W6 audited
> rows `53/30` (`0` remaining), W6 alarm clearance `29`, and combined horizon
> `37` with blocker `seq_trusted_vectors`.
> A guarded stop-window watcher is now resident as PID `1862928`. It waits for
> the current AutoPilot Python PID `1091018` to exit, requires
> `trial_counter >= 930`, `paused=False`, and no `_dispatch_deficiency`, runs
> ordinary `restart_readiness_report.py --json --strict`, appends the prepared
> baseline seed only if the report says append-ready/required with exact guard
> values, then restarts the same W4/W6 collection flags to
> `autopilot.py start --max-trials 970`. Runtime logs are under
> `/mnt/raid0/llm/tmp/w4w6_seed_then_continue_20260621T0358.log`. The watcher
> runs from a temp Python script so pgrep-based AutoPilot guards see only the
> real `autopilot.py start` process.

> **Live update — 2026-06-21T15:40Z.** The resumed W4/W6 accrual process is
> active on trial `934` T2. Latest strict readiness remains blocked at trusted
> vectors `97/120` (`23` remaining), seq shadow rows `44/30`, W6 audited rows
> `65/30`, and W6 alarm clearance `23` clean audited trials. Direct W6 audit
> reporting now matches the aggregate gate: `epyc-orchestrator` `0c593b23`
> defaults standalone `audit_block_report.py` CLI runs to a trailing-30 audited
> trial alarm window, while preserving all-history library semantics for
> explicit callers. Live direct smoke reports window `30/30`,
> `gaming_alarm=true`, clearance `23`, and `12` cumulative divergences.

#### Start Here

1. Let AutoPilot PID `3935151` continue current trial `1217` unless phase health
   fails. This is the current-code-clean forced replay of source trial `1197`;
   the next target is candidate outcome evidence, not another restart or a
   repeat AP-9 investigation.
2. Watch provider traces for local-planner quality.
   Under W8 pressure the prompt menu should no longer expose `seed_batch`,
   `deep_eval`, or `structural_prune` schemas. If local drafts still propose
   unavailable actions, repair the drafter prompt/normalizer or add a measured
   two-stage local provider rather than weakening the W8 dispatcher guard.
3. Finish W8 promotion eval evidence: orchestrator `33c16b47` makes forced fresh-promotion deep evals replay the pending candidate's exact numeric params or structural flags and fail closed for unreplayable candidates. Orchestrator `b62bc205` adds the Phase-2.4 confidence-interval non-regression guard: fresh promotion evals now need effective paired-question evidence (`r_eff`) and a one-sided delta lower bound that excludes regression before finalization, with the CI object recorded into promotion state. Orchestrator `2aa3b40c` wires the P-QUAL-PROMO draw contract: forced promotion evals use trial-seeded fresh T2 draws, n bounded to 200-500, qids seen in the last 60 days excluded, broken/artifact suites excluded via the latest item-analytics suite-health table, and fail closed if fewer than 200 fresh healthy scoreable questions remain. Continue live accrual until AutoPilot produces a keepable replayable candidate, then collect sequential confirmation and fresh promotion-eval evidence.
4. Run/review the disagreement/cutover report as follow-up documentation, not as a prerequisite to the already-executed authority restart.
5. Coordinate any future restart-bundle accept-path flips with J11/BSV-2 and K-SKILL-1 because all three are accept-path gates.

#### Why

Per-question outcomes are computed every trial and discarded at aggregation — pairing is free
statistical power already paid for (spec §2.2). Persisting the 43-bit vector enables McNemar
replay of 120 historical keep/revert decisions, and the 01c e-process (anytime-valid under the
planner's own optional stopping/continuation) replaces the single-shot MAD argument:
`mad_noise` and `reproduction_confirmed` collapse into `accumulating`, and the t775 ratchet
class becomes impossible by construction (baseline raises require `confirmed_improvement`).
This handoff owns the restart bundle: ledger + verdicts + the two campaign accept-path gates
land at ONE autopilot restart, each behind its own flag.

#### Waypoints

- [x] **W1 — qid + outcome vectors** (impl 1.1–1.2, ~1–2 days): derived stable `qid` from `suite + "\0" + prompt`; `eval_tower._aggregate` carries compact `question_results` on `EvalResult`; AutoPilot mirrors it to `eval_details.question_results`; TSV untouched. **Landed live 2026-06-13** on `epyc-orchestrator` branch `fix/substring-scorer-digit-separators` as `22a3874a` (`Journal per-question eval vectors`) after focused restart-bundle validation. Original stale-lineage worktree remains at `/mnt/raid0/llm/tmp/paired-stats-worktree`, branch `feat/paired-question-stats`, commit `3c17460`; prior current-lineage checkpoints are retained for provenance. Trusted vector history restarts at the clean epoch: `#799/#800` each carried 55 question results; `#789-#797` vector rows are quarantined and must not feed W4 evidence.
- [x] **W2 — paired replay tool** (impl 1.3, ~1 day, zero inference): `scripts/autopilot/paired_stats.py` (`summary`, `mcnemar`, `config-vs-baseline`). Decision gate: after ~2 weeks of vectors, replay historical keep/revert — ≥30% verdict flips ⇒ proceed to W3; <10% ⇒ hold and report (findings-01 §4). **Landed on current orchestrator branch 2026-06-13** as `9f6fc8e` (`Add paired question replay stats`), a clean cherry-pick of restart-bundle commit `c67575b`; validation: py_compile, `tests/unit/test_paired_stats.py` (3 passed), ruff on touched files, diff-check, and historical pre-restart live-journal summary `667 rows / 0 vector trials`. Follow-up `d21bbee` makes `iter_journal_rows()` fold append-only supersession events and drop non-trial event rows before paired-stat inputs. Trusted clean-epoch vector trials currently are `#799/#800`; W4 evidence should use the supersession-aware read path.
- [x] **W3 — sequential_verdict.py** (01c §1–2,§4; 2–3 days): landed in `epyc-orchestrator` `7e6ac9c` as pure `src/autopilot_core/sequential_verdict.py` plus package exports and `tests/unit/test_sequential_verdict.py`. Implements capped-Kelly e-process state, baseline per-qid profile statistic, rate non-inferiority transform, JSON-ready `seq` journal block, and rebuildable per-candidate view from journal rows or `(trial_id, z)` observations. Acceptance: 100,000-run deterministic null simulation returned false-positive rate `0.00551` at α=0.05; focused validation `26 passed`.
- [x] **W4 — joint verdict + wiring** (01c §3,§5): default-off mechanism, central AutoPilot shadow wiring, baseline/fresh-eval finalization, cached-verdict upgrade, fallback reselection, action-local gate threading, failed-trial denominator repair, fresh-eval pre-dispatch repair, and the post-reboot authority cutover are live. Current strict readiness on 2026-07-02 reports baseline authority enabled from `ledger_fold`, archive authority aligned through journal max `1061`, sequential cutover ready with trusted vectors `202 / 120`, and seq shadow rows `125 / 30`. Remaining authority tail is W8 promotion-eval evidence, not W4 wiring/cutover.
- [x] **W5 — planner power line + candidate blocks** (impl 1.5 + 01c §5.3, ~half day): landed in `epyc-orchestrator` `0bc1f32` as `src/autopilot_core/planner_evidence.py` plus the `### Evidence Power and Sequential Candidate Status` planner section after Pareto geometry. This is planner-only/read-only context: no safety gate, baseline authority, archive authority policy, or inference behavior changed. Dispatch-gate policy remains future work with W4/cutover decisions.
- [x] **W6 — shadow rollout + cutover** (01c §5.5, 2 weeks passive): dual-log `seq` alongside MAD verdicts; the post-reboot cutover is live under `AUTOPILOT_SEQ_VERDICT=1`. Current strict readiness on 2026-07-02 reports `seq_shadow_rows=125/30`, W6 current-era audited rows `41/30`, trailing-window `gaming_alarm=false`, `0` potential overfit divergences, and no W6 blockers. Continue W8 promotion-eval evidence collection and fail closed on any future strict-readiness regression or instrument-era reset.
- [x] **W7 — game layer** (impl 5.1–5.3, 2–3 days): critic measurement-view foundation landed in `epyc-orchestrator` `41c5c71` (`build_critique_prompt` stops echoing the 80KB planner prompt and now carries bounded power/constraint context); server-side production eval sampling clamp landed in `7492cf5` (`EvalTower.evaluate()` pins T1/T2 `n`/`seed`, dispatcher rejects malformed `deep_eval`, and calibration uses direct tier helpers for operator overrides); audit-stream gaming alarm landed in `8e4b1ec` as read-only `gaming_alarm` / `gaming_events` report fields; PEAF surprise budget credit landed in `4b09661` via `information_rate` / `budget_rate` while preserving legacy Pareto `rate`; per-question diff/provenance context landed in `749d38f` by adding truthy-only compact row flags (`scoring_method`, route/tools, error/partial/degraded/exogenous/retry markers) and planner evidence summaries (`diff=prev#...`, suite/partition counts, provenance flags) without exposing prompt or answer text.
- [x] **W8a — candidate-generation deferral guard**: orchestrator `854eff06` prevents W8 pressure from being spent on unreplayable ordinary deferrals by replacing `seed_batch`, `deep_eval`, `structural_prune`, and invalid structural actions with the first unblacklisted numeric trial fallback unless a sequential due-action owns the turn; planner evidence now states that new Optuna numeric trials are replayable when dispatch journals applied params. ✅ 2026-07-05
- [x] **W8a.1 — local-planner/W8 fallback contract repair**: orchestrator `3364bdd7` converts critic-fallback seed/deep/prune deferrals into replayable W8 candidate attempts before the reject-loop guard; orchestrator `a13a2948` teaches the critic/repeat shield that empty `numeric_trial.params={}` is an Optuna request, not the final replay artifact. Live AutoPilot PID `3267768` verified the path through `local_ingest` draft, `local_frontdoor` critique, W8 fallback, and concrete `chat_pipeline` applied param `0.8742715026951258` in trial `1194`; the candidate itself was reverted for `tool_use` regression, so this closes wiring proof but not W8 evidence. ✅ 2026-07-05
- [x] **W8a.2 — selectable-action provider coordination**: orchestrator `1639748a` threads the live `selectable_action_types` allowlist into `plan_with_providers()`, rejects known-but-currently-unavailable drafts before critique, applies the same guard to critic revisions, and adds regression coverage for the W8 `deep_eval` drafter waste case. The commit is pushed/indexed and live in AutoPilot PID `3795561`; trial `1210` verifies the post-deploy local `frontdoor` draft / local `worker` critique path before the higher-tier guard forced T3. ✅ 2026-07-06
- [x] **W8a.3 — outcome-stall dispatch guard**: orchestrator `9522b76e` stops the higher-tier probe guard from overriding an already frontier-moving planner action under frontier-stall pressure, and `78ae65e6` adds a bounded outcome-progress fallback that forces a metric-bearing numeric trial only when frontier admission is stale and the selected action is seed/eval/housekeeping rather than a frontier-moving action. Focused validation passed (`140` AutoPilot action/phase/provider tests), ruff, `py_compile`, `git diff --check`, push, and GitNexus refresh. A boundary restart loaded the patch; W8a.4 below is the current live replay-dispatch checkpoint. ✅ 2026-07-06
- [x] **W8a.4 — forced replay/AP-9 dispatcher repair**: orchestrator `e3b13edd` keeps W8 replay pressure active while replay/confirmation remains open, allows materialized multi-param NumericSwarm candidates to be replayed as one force-matched candidate, and bypasses AP-9 only when the current action exactly matches `seq_candidate_replay_forced`. Trial `1213`-`1216` skips exposed the seam; the state was cleaned without deleting journal evidence, GitNexus refreshed, focused validation passed (`203` tests + Ruff + diff-check), and live PID `3935151` is evaluating trial `1217` with the intended AP-9 replay bypass. ✅ 2026-07-06
- [x] **W8a.5 — retryable-aware seq fallback unblock**: orchestrator `402e461b` adds retryable-aware seed fallback selection for seq baseline-reference forcing and seq-gate preflight deferral while preserving manual/token-gated blacklist purge. Live trial `1346` forced the seq baseline-reference draw via retryable `seed_batch n=50` target `seed_batch_n50_t1317_no_progress_infra`, so infra-contaminated retry targets can be revisited without reopening durable blacklist bans. ✅ 2026-07-14
- [ ] **W8b — live candidate evidence after guard deploy**: continue W8 candidate attempts under the live selectable-action coordinator plus outcome-stall guard. Verify a keepable replayable candidate, then collect sequential confirmation and fresh promotion-eval evidence. The old restart/local-worker verification clause is superseded by the current `local_frontdoor`/local_worker` canary and selectable-action coordinator.

#### Gates & pitfalls

- Restart discipline: W1 + J11/BSV-2 + K-SKILL-1 shared the 2026-06-13 API reload boundary and are flag-isolated for attribution. Future authority flips still need a deliberate restart boundary and attribution plan.
- W4/W6 are now gated on readiness, not code availability. Do not wire authority on vibes: collect enough trusted vectors and seq shadow rows, then run the disagreement/cutover report.
- GitNexus impact for `EvalTower._aggregate` is HIGH (19 impacted symbols/modules across all eval/action paths on the 2026-06-13 current index), so W1 writer changes should land in a deliberate restart-bundle branch with focused aggregate/journal compatibility tests, not as opportunistic mid-run edits.
- Update the e-process per TRIAL, never per question (within-trial outcomes are dependent — 01c §1); core-version or policy-version change resets all `accumulating` candidates.
- Works on the accidental 43-set at lower power, but instrument-repair W4/W5 should land first or R_eff stays ~10–14.
- Sequential machinery credits improvements only — never let it delay damage control (01c §3).

#### Progress

- 2026-06-12: W1+W2 original branch-ready at `epyc-orchestrator` `feat/paired-question-stats` commit `3c17460`. Validation: 22 focused eval/journal/paired-stat tests passed; full ruff on new/nearby files passed; `ruff --select F821` on touched AutoPilot files passed; `py_compile`; `git diff --check`.
- 2026-06-12: Rebased/cherry-picked W1+W2 onto the current paused live lineage as `feat/paired-question-stats-current` commit `8dbdba5b`. Validation: `python3 -m py_compile` on touched AutoPilot files passed; focused suite `tests/unit/test_paired_stats.py tests/unit/test_autopilot_hle_fields.py tests/unit/test_eval_tower_concurrency_metrics.py tests/unit/test_eval_tower_instrument_repair.py tests/unit/test_safety_gate_baseline_eligibility.py` -> 30 passed, 1 pytest config warning; `git diff --check HEAD~2..HEAD` passed. Full ruff/format checks are not claimed because current-lineage `scripts/autopilot/autopilot.py` has pre-existing unused-import and formatting debt outside this branch's behavioral delta. Residual: merge/deploy at the restart bundle, then collect vector-bearing trial history before W3/W4.
- 2026-06-13: Refreshed W1+W2 onto current live lineage `ab5df87` as `feat/paired-question-stats-restart-current` tip `0855e3b`. GitNexus refreshed first; impact for `EvalTower._aggregate` was HIGH and `EvalResult` LOW, so this remains restart-bundle-only. Validation: `python3 -m py_compile scripts/autopilot/autopilot.py scripts/autopilot/eval_tower.py scripts/autopilot/safety_gate.py scripts/autopilot/paired_stats.py tests/unit/test_paired_stats.py tests/unit/test_autopilot_hle_fields.py tests/unit/test_eval_tower_concurrency_metrics.py` passed; `uv run --with pytest pytest -q tests/unit/test_paired_stats.py tests/unit/test_autopilot_hle_fields.py tests/unit/test_eval_tower_concurrency_metrics.py tests/unit/test_eval_tower_instrument_repair.py tests/unit/test_safety_gate_baseline_eligibility.py tests/unit/test_item_analytics.py` -> 34 passed, 1 pytest config warning; `uv run --with ruff ruff check scripts/autopilot/paired_stats.py tests/unit/test_paired_stats.py tests/unit/test_autopilot_hle_fields.py tests/unit/test_eval_tower_concurrency_metrics.py tests/unit/test_item_analytics.py` passed; `git diff --check HEAD~2..HEAD` passed; `paired_stats.py --journal /mnt/raid0/llm/epyc-orchestrator/orchestration/autopilot_journal.jsonl summary` -> 667 rows / 0 vector trials.
- 2026-06-13: Ported J11 observe-only BSV diagnostics onto the combined restart branch as `feat/restart-bundle-bsv-observe-current` tip `4c0e1b6`. Resolved the only conflict by preserving both N2 `question_results` and task-rate shadow fields alongside `eval_details.bsv_observe`. Validation: `python3 -m py_compile scripts/autopilot/autopilot.py scripts/autopilot/eval_tower.py scripts/autopilot/safety_gate.py scripts/autopilot/paired_stats.py scripts/autopilot/bsv_observe.py tests/unit/test_paired_stats.py tests/unit/test_bsv_observe.py tests/unit/test_autopilot_hle_fields.py tests/unit/test_eval_tower_concurrency_metrics.py` passed; `uv run --with pytest pytest -q tests/unit/test_bsv_observe.py tests/unit/test_behavior_signature.py tests/unit/test_paired_stats.py tests/unit/test_autopilot_hle_fields.py tests/unit/test_eval_tower_concurrency_metrics.py tests/unit/test_eval_tower_instrument_repair.py tests/unit/test_safety_gate_baseline_eligibility.py tests/unit/test_item_analytics.py` -> 64 passed, 1 pytest config warning; `uv run --with ruff ruff check scripts/autopilot/paired_stats.py scripts/autopilot/bsv_observe.py tests/unit/test_paired_stats.py tests/unit/test_bsv_observe.py tests/unit/test_behavior_signature.py tests/unit/test_autopilot_hle_fields.py tests/unit/test_eval_tower_concurrency_metrics.py tests/unit/test_item_analytics.py` passed; `git diff --check 0855e3b..HEAD` passed.
- 2026-06-13: Rebased the restart bundle onto live branch `924ca50` after DCP-6a and K-SKILL default-off wiring landed. New N2-only tip: `feat/paired-question-stats-restart-current` `83cb36c`; new combined N2+J11 observe tip: `feat/restart-bundle-bsv-observe-current` `c20985e`. Validation: `python3 -m py_compile` on AutoPilot/eval/paired/BSV/K-SKILL changed surfaces passed; `uv run --with pytest pytest -q tests/unit/test_bsv_observe.py tests/unit/test_behavior_signature.py tests/unit/test_paired_stats.py tests/unit/test_autopilot_hle_fields.py tests/unit/test_eval_tower_concurrency_metrics.py tests/unit/test_eval_tower_instrument_repair.py tests/unit/test_safety_gate_baseline_eligibility.py tests/unit/test_item_analytics.py tests/unit/test_autopilot_actions.py tests/unit/test_skill_efficacy.py` -> 107 passed, 1 pytest config warning; focused `ruff check` passed; `git diff --check 924ca50..HEAD` passed; paired-stats smoke over the live journal still reports 667 rows / 0 vector trials.
- 2026-06-13: After W7 planner-session hygiene landed live at `9e5d861`, rebased the restart bundle again. New N2-only tip: `feat/paired-question-stats-restart-current` `d32fafd`; new combined N2+J11 observe tip: `feat/restart-bundle-bsv-observe-current` `c63816b`. Validation: `python3 -m py_compile` on AutoPilot/eval/paired/BSV/K-SKILL/planner changed surfaces passed; `uv run --with pytest pytest -q tests/unit/test_bsv_observe.py tests/unit/test_behavior_signature.py tests/unit/test_paired_stats.py tests/unit/test_autopilot_hle_fields.py tests/unit/test_eval_tower_concurrency_metrics.py tests/unit/test_eval_tower_instrument_repair.py tests/unit/test_safety_gate_baseline_eligibility.py tests/unit/test_item_analytics.py tests/unit/test_autopilot_actions.py tests/unit/test_skill_efficacy.py tests/unit/test_autopilot_planner_providers.py tests/unit/test_autopilot_planner_coordinator.py tests/unit/test_autopilot_controller_io.py` -> 170 passed, 1 pytest config warning; focused ruff passed; `git diff --check 9e5d861..HEAD` passed; paired-stats smoke over the live journal still reports 667 rows / 0 vector trials.
- 2026-06-13: Landed the W2 replay tool on current orchestrator branch `fix/substring-scorer-digit-separators` as `9f6fc8e` while leaving W1's HIGH-impact writer out of the live branch. Validation: `python3 -m py_compile scripts/autopilot/paired_stats.py tests/unit/test_paired_stats.py`; `uv run --with pytest pytest -q tests/unit/test_paired_stats.py` -> 3 passed; `uv run --with ruff ruff check scripts/autopilot/paired_stats.py tests/unit/test_paired_stats.py`; `git diff --check HEAD~1..HEAD`; `paired_stats.py --journal orchestration/autopilot_journal.jsonl summary` -> 667 rows / 0 vector trials.
- 2026-06-14: W2 replay read path became supersession-aware in `epyc-orchestrator` `d21bbee`. `scripts/autopilot/paired_stats.py iter_journal_rows()` folds append-only supersession events and drops non-trial event rows before paired summaries/McNemar/config-vs-baseline inputs. Regression coverage in `tests/unit/test_paired_stats.py` verifies supersession folding; combined validation with item analytics, task-rate replay, and journal supersession tests passed (`15 passed`), with focused ruff and diff-check clean on touched analytics files.
- 2026-06-13: Refreshed W1 onto the actual current orchestrator HEAD in isolated worktree `/mnt/raid0/llm/tmp/paired-stats-head-worktree`. New branch `feat/paired-question-stats-current-head` tip `22a3874a`, based on `9f6fc8e` (current branch with W2 replay, X-MAS scaffold, ColGREP telemetry, BT cleanup, and controller guidance). Validation: `python3 -m py_compile scripts/autopilot/autopilot.py scripts/autopilot/eval_tower.py scripts/autopilot/safety_gate.py scripts/autopilot/paired_stats.py tests/unit/test_paired_stats.py tests/unit/test_autopilot_hle_fields.py tests/unit/test_eval_tower_concurrency_metrics.py`; `uv run --with pytest pytest -q tests/unit/test_paired_stats.py tests/unit/test_autopilot_hle_fields.py tests/unit/test_eval_tower_concurrency_metrics.py tests/unit/test_eval_tower_instrument_repair.py tests/unit/test_safety_gate_baseline_eligibility.py tests/unit/test_item_analytics.py` -> 34 passed, 1 known pytest config warning; focused ruff passed; `git diff --check HEAD~2..HEAD` passed; paired-stats live-journal smoke remains 667 rows / 0 vector trials.
- 2026-06-13: Merged/deployed the combined restart bundle onto live orchestrator branch: `22a3874a` W1 vectors, `fd84655e` J11/BSV observe-only, `d89b4a9` BSV review fixes, followed by launch-hygiene commit `954d8fd`. API reload PID `3447078` was healthy and OOM-protected; `paired_stats.py --journal orchestration/autopilot_journal.jsonl summary` reported `667 rows / 0 vector trials` because AutoPilot remained paused. Initial full preflight after `954d8fd` passed 8/9 and exposed a Question Pool capacity gap; `a3ec440` superseded that blocker below.
- 2026-06-13: W4b sampler/preflight follow-up landed as `a3ec440`; API reload PID `3460290` is healthy, OOM-protected, and has tool sentinel/structured output flags in the process environment. Full preflight now passes 9/9: T1 sampled 100/100 unique and T2 sampled 500/500 unique. Gate-3 hard telemetry passed, but the soft `web_research` full `/chat` probe returned 500 after stale `architect_coding` escalation/fallback; SearXNG itself is healthy. Superseded quarantine status: existing AutoPilot rows `#786-#792` are now tagged `resource_contention_20260612`, and state is paused cleanly at `trial_counter=793`.
- 2026-06-13: Stale-role hygiene landed as `a338738` and API reload PID `3486453` passed Gate-3 hard telemetry. The soft probe still returned 500, but the task completed successfully through `frontdoor -> coder_escalation -> architect_general`; repeated health probes showed worker-local six-worker circuit inconsistency. Later single-worker follow-up landed response JSON hardening (`4a7efbe`) and API-boundary failure logging (`c62dbd8`); a bounded soft `web_research` probe stayed slow and was killed by the client with server health still ok and no new 500/traceback. Next vector-history run should start from a clean API process, preferably `ORCHESTRATOR_UVICORN_WORKERS=1`, instead of treating the soft probe as an evidence-plane blocker.
- 2026-06-13: W3 pure sequential verdict module landed as `7e6ac9c`. Validation: `py_compile`; focused `ruff`; `pytest -q tests/unit/test_sequential_verdict.py tests/unit/test_autopilot_core_contracts.py tests/unit/test_paired_stats.py` -> 26 passed; deterministic `empirical_ville_false_positive_rate(runs=100000, horizon=12)` -> `0.00551`. API reload on `7e6ac9c` PID `3531008` passed full preflight 9/9, but Gate-3 hard telemetry stalled twice before first sentinel output and was stopped both times. After the second attempt, `/health` was degraded only by the known `http://localhost:8102` fallback circuit while direct probes stayed healthy and no new 500/traceback appeared. This stall was superseded by `b1985be`; W4 remains the safety-gate/update-baseline wiring step after clean vector-bearing history exists.
- 2026-06-13: Gate-3 hard-only driver hygiene landed as `b1985be` and passed after a fresh one-worker API reload. The contaminated AutoPilot restart window is treated conservatively by operator instruction: rows `#786-#797` are tagged `resource_contention_20260612` except killed placeholders `#796/#798`; runtime projection was restored from clean backup through `#785`, and the polluted Optuna base study was renamed/quarantined. Clean completed rows `#799/#800` each wrote 55 vectors after the repair window, were dominated, and left T1 frontier unchanged. Live state is paused at `trial_counter=801`; W4 remains gated on more trusted vector history rather than code availability.
- 2026-06-14: W5 planner evidence context landed in `epyc-orchestrator` `0bc1f32` (`Add planner evidence context to AutoPilot`). It adds read-only planner evidence context after Pareto geometry and validation passed on the main lane: py_compile; focused ruff; focused pytest `tests/unit/test_planner_evidence.py tests/unit/test_autopilot_system_card.py tests/unit/test_sequential_verdict.py` -> 22 passed; expanded pytest over core contracts/paired stats/archive authority/baseline authority -> 25 passed; preflight 10/10 passed; archive authority strict passes after runtime repair. W4 remains pending for clean vector history and safety-gate/update-baseline wiring.
- 2026-06-14: Clean AutoPilot window after repair ran through `trial_counter=813`; clean rows `#807-#812` include `#808` q=1.98 s=60.1 r=1.00, `#809` q=2.04 s=57.2 r=0.98, `#810` numeric `memrl_retrieval` q=2.04 s=56.7 r=1.00, `#811` q=1.92 s=58.1 r=0.98, and `#812` q=1.98 s=47.1 r=0.98. No infrastructure-collapse signature was observed. Archive repair wrote runtime backup `/mnt/raid0/llm/epyc-orchestrator/orchestration/autopilot_state.json.bak-archive-repair-20260614T045917Z` and restored state/journal match.
- 2026-06-14: Read-only sequential verdict readiness report landed in `epyc-orchestrator` `d446f68` as `scripts/autopilot/seq_readiness_report.py` plus `tests/unit/test_seq_readiness_report.py`. Validation on the main lane: py_compile for new files; ruff for new files; focused pytest `tests/unit/test_seq_readiness_report.py` -> 4 passed; adjacent pytest `tests/unit/test_seq_readiness_report.py tests/unit/test_paired_stats.py tests/unit/test_planner_evidence.py tests/unit/test_sequential_verdict.py` -> 26 passed. Live report over `orchestration` was blocked: trusted vectors 14, raw 21, untrusted 7 (`#789/#790/#791/#793/#794/#795/#797`), seq shadow rows 0, blockers `trusted history <120`, `seq shadow <30`, and no flip-rate denominator. This is W4/W6 readiness/reporting progress only; W4 enforcement and W6 cutover remain pending.

#### Reporting

Tick waypoints + one-line progress entry; verdicts claimed per MEASUREMENT.md grammar (`[P-QUAL-T1/seq-v1, E=…, k=…, date]`); on completion delete this handoff's master-index row and move to `completed/`.

#### Research Intake Update — 2026-07-16 (Reviewer control plane: decision≈question ledger alignment)

The new `review_ledger` (H4, [`reviewer-calibration-accounting.md`](reviewer-control-plane.md#track-reviewer-calibration-accounting)) is designed to FOLLOW this handoff's per-question-ledger conventions: one row per review decision (decision ≈ question), gold label + gold-source + instrument version + era columns, append-only, e-process monitoring on `src/autopilot_core/sequential_verdict.py` (FA-tolerance AND FR-tolerance — the symmetric pair is motivated by intake-836's measured 10:1-440:1 false-reject dominance). Alignment task RC-7 owns reconciliation; if ledger conventions here evolve, cross-update H4.

#### Research Intake Update — 2026-07-17 (TM-6 relationship contract)

The reviewer control plane's trace store documented its non-overlap contract with this pipeline (see `reviewer-trace-materialization.md` §TM-6): the trace store indexes the same append-only sources (journals/audit/progress) and adds an `emit://`-namespaced primary path ONLY for review-plane events that have no file source; this evidence-plane pipeline remains authoritative for trial/verdict events; `review_ledger` rows map to per-question-ledger shape via `to_question_ledger_row()` (RC-7).

## Track: loops-and-dashboards-audit-2026-07-05
<!-- gate: none -->

> Folded from `handoffs/active/loops-and-dashboards-audit-2026-07-05.md` @ `b1bf3f3f7ade` on 2026-11-02 (BRF-T1-F20, route 1a, operator D1/D5; retired row RTG-16 → RTG-02). Body moved verbatim, headings demoted two levels to nest under this track; every open and closed box kept its text and ID.

### Audit — Kernel-R&D loop + Orchestration Autopilot loop (and both dashboards)

**Status**: ACTIVE REVIEW — prioritized remediation roadmap with Phase-1 AutoPilot fixes landed
**Created**: 2026-07-05
**Author**: Fable 5 audit session (operator-directed: "audit the kernel improvement loop and its dashboard… could the orchestration autopilot loop/dashboard be improved also?")
**Method**: direct source reads + a read-only 7-facet audit workflow (deep-read → synthesize → adversarial gap-critic; 9 agents, 0 errors, ~1.1M subagent tokens). Every performance number here is an **OBSERVATION** in the MEASUREMENT.md sense (journal/log-derived, no protocol id) — it steers attention, it does not gate promotions. The highest-leverage fixes touch the **human-amendment-only** trust boundary and are flagged as operator-signed amendments, not agent edits.
**Scope of surfaces audited**: `epyc-orchestrator/scripts/autopilot/*` + `src/autopilot_core/*` (loop, generators, evidence/promotion/safety plane), `epyc-orchestrator/src/api/routes/dashboard*` (autopilot dashboard :8000), `epyc-inference-research/scripts/kernel_rnd/*` (kernel loop), `epyc-root/dashboard/*` (hub :8100). Related: [mi210-kernel-rnd-loop-proposal.md](../completed/mi210-kernel-rnd-loop-proposal.md), [master-handoff-index.md](master-handoff-index.md), the completed `fable5-findings-*` set.

#### Main-thread review/action — 2026-07-05

Reviewed by the main orchestration thread after several live AutoPilot repairs had already landed. Treat the original counts below as the audit's historical snapshot, not as current state.

Corrections from live code/journal review:
- W8 is no longer stale on the specific `trial-1158` blocker described here: `w8_promotion_trajectory_report` now sees replay-eligible candidate `4b6b454ea4f884fd`.
- W6 audit clearance is no longer a live strict blocker after `epyc-orchestrator` `113e36b0`: the comparator is candidate-aware, and the regenerated current report shows `220` audited trials, `gaming_alarm=false`, `gaming_alarm_clearance_clean_trials_required=0`, `cumulative_gaming_alarm=false`, and no core-inflation warning.
- The "8 replayable candidate trials" claim is stale: current all-shard journals have hundreds of `numeric_trial`/`structural_experiment` entries. The useful criticism is not raw absence anymore; it is whether those candidates are replayable, active-surface, and seq-confirmable.
- Dashboard shard reads and stale-panel freshness were already repaired by the time this review ran; the actionable dashboard tail remains outcome/yield KPIs and operator steering, not just liveness.
- The local-planner criticism was still actionable: `planner_providers.py` had only Claude/Codex providers for drafting before this slice.

Action landed:
- `epyc-orchestrator` `7036630c` adds an OpenAI-compatible `LocalPlannerProvider`, role aliases for `local`, `local_worker`, and `local_ingest`, and the Fable launcher default `AUTOPILOT_PLANNER_PRIMARY=local_ingest` / `AUTOPILOT_PLANNER_CRITIC=codex` when not explicitly overridden. Local drafting calls the orchestrator `/v1/chat/completions` endpoint with `x_orchestrator_role` and `x_disable_repl=true`.
- `epyc-orchestrator` `1f8f79e7` changes the live Fable default to
  `AUTOPILOT_PLANNER_PRIMARY=local_chat`, with Codex still the critic. This
  routes planner drafting through the orchestrator chat/router path instead of
  pinning the planner directly to `ingest_long_context`; direct `local_ingest`
  remains an alias for experiments and fallback.
- The coordinator now treats local-provider aliases as one underlying model for failover, and operator-approved Codex fallback drafts may dispatch without pausing if local drafting fails; the fallback is visible in planner archive telemetry.
- `epyc-orchestrator` `32567813` bypasses planner drafting for due sequential actions, so fresh evals, baseline draws, and W8 candidate replays no longer spend planner budget or wait on model deliberation.
- `epyc-orchestrator` `113e36b0` makes W6 gaming/core-inflation checks candidate-aware, eliminating the cross-candidate false positive that had been aging out via clean-row accrual instead of reflecting real overfit evidence.
- `epyc-orchestrator` `03dfac45` turns the planner budget line from a status string into an enforced spend breaker. When projected planner spend exceeds the configured threshold, the coordinator forces local-local planning (`local_chat` primary, `local_worker` critic by default after `1f8f79e7`) instead of continuing metered cloud drafts/critique.
- `epyc-orchestrator` `0875fb50` skips inert numeric and structural candidates before eval: no-change numeric params and structural no-op flag proposals now short-circuit without burning a T1/T3 measurement.
- `epyc-orchestrator` `45c118b8` adds outcome KPIs to the dashboard API/frontend: keepable rate, wasted-eval rate, learning-excluded rate, and current-code health.
- `epyc-orchestrator` `683a20ba` adds dispatch-boundary regression coverage for inert skips.
- `epyc-orchestrator` `b7518da0` stops seed-batch prompt contamination: StrategyStore planner hints stay planner-context only, Seeder ignores legacy `strategy_hints`, and the contaminated trials are superseded append-only in `autopilot_journal_1.jsonl` with `bug_corrupted_by=b7518da0`.
- `epyc-orchestrator` `b5cadba6` marks stale planner tap history on the dashboard: process-status now carries `planner_tap_mtime_s` and `planner_tap_precedes_autopilot_start`, and the panel text distinguishes current actions with no planner trace from live planner activity.
- `epyc-orchestrator` `10a9596d` makes checkpoint restore/rollback rewind AP-22 short-term memory and the StrategyStore tree, and the live rollback path now closes/reopens StrategyStore handles after restore instead of leaving planner memory split from disk.
- `epyc-orchestrator` `1d452a40` first bounded GEPA prompt writes to each evaluation call by restoring the original prompt in a `finally` block.
- `epyc-orchestrator` `8031c7c4` then completed the true scratch prompt-root override: GEPA candidate evals copy the prompt tree into `tmp/gepa_prompt_roots`, write the candidate only there, tag eval questions with `_prompt_root`, and `/chat` resolves prompts through a request-scoped override that is accepted only under the configured scratch base. Candidate scoring no longer writes canonical prompt files.
- `epyc-orchestrator` `12839520` adds observation-only W8 paired-baseline diagnostics: each evaluated trial can journal `eval_details.seq_paired_baseline`, comparing its per-question vector with the latest trusted `seq_baseline_reference_draw` through the existing exact McNemar/sign-test primitive. The payload is explicitly `used_for_gating=false` and is computed only after SafetyGate/Pareto/baseline decisions, so it cannot change current keep/revert or promotion semantics.
- `epyc-orchestrator` `18c71bcc` adds outcome-first health signals to `phase_health_report.py`: journal-shard-derived frontier-admission staleness, baseline-promotion staleness, and recent keepable/wasted/learning-excluded rates. Default behavior is advisory; `--require-outcome-progress` turns the same signal into a strict blocker. A live smoke flags the current frontier stall at `172` trials since the latest frontier admission against the default threshold `150`.
- [x] `epyc-orchestrator` `bd2ecc7d` fixes a provider-health false alarm
  exposed by forced W8 replays. `planner_provider_health_report.py` now reads
  the live phase payload and reports `waiting_for_planner_turn`/`ok=true` when
  the daemon is in a non-planner phase such as `dispatch_action`, while still
  treating a no-event `planner_invoke` window as `attention`. Focused planner
  health/lab tests passed (`23 passed`) with `ruff`, `py_compile`, and
  `git diff --check` clean. ✅ 2026-07-06
- `epyc-orchestrator` `080e3ac8` adds a durable operator outbox for critic-rejected operator-domain drafts (`orchestration/autopilot_operator_outbox.jsonl`) and renders the capped open outbox back into the planner prompt, preserving human/trust-boundary hypotheses without letting the planner keep redrafting them as autonomous actions.
- `epyc-orchestrator` `96b883cb` adds exact-signature repeat shielding for critic-rejected drafts. Re-emitting the same normalized action now becomes a non-executing invalid skip before dispatch; a materially changed retry has a different signature and remains eligible.
- `epyc-orchestrator` `224e3397` surfaces the journaled W8 paired-baseline diagnostics in `seq_readiness_report.py` as observation-only `paired_baseline_screening`, so absence/presence of those rows is visible in the readiness packet rather than buried per trial.
- `epyc-orchestrator` `e58c2bca` feeds outcome-progress pressure into the controller prompt: latest/frontier/promotion staleness plus recent keepable, wasted-eval, and learning-excluded rates are now planner-facing, non-authority context.
- [x] `epyc-orchestrator` `d006996b` hardens the local planner provider after the first live `local_chat` rollout failed: the default routine drafter is now `local_worker` with Codex critic, the OpenAI-compatible local URL uses `127.0.0.1`, transient local HTTP failures are retried, and local `[ERROR]` / `[MOCK]` payloads fail closed instead of being dispatched as planner text. The live AutoPilot PID still predates this commit; verify it after the next advisor-safe restart boundary. ✅ 2026-07-05
- [x] `epyc-orchestrator` `200d6ea` closes the adjacent CPU MTP launcher trap: same-file embedded MTP configs omit `-md` instead of double-loading, while worker_general keeps `-md` for its current separate assistant draft model. ✅ 2026-07-05
- [x] `epyc-orchestrator` `27fa7161`, `58904e36`, `3364bdd7`, and
  `a13a2948` supersede the stale local-worker/Codex restart target with the
  current canary contract: routine planning uses `local_ingest` draft,
  `local_frontdoor` critique, and `claude` fallback; W8 fallback rewrites
  seed/deep/prune deferrals into replayable candidate attempts; new
  empty-params numeric trials are treated as Optuna requests whose concrete
  params are journaled by dispatch. AutoPilot PID `3267768` is live on this
  path; trial `1194` evaluated `chat_pipeline` threshold
  `0.8742715026951258`, then reverted for `tool_use` regression, and trial
  `1195` invalid-skipped already-blacklisted `graph_router=true`; latest
  observed state is trial `1196` planner invocation. ✅ 2026-07-05
- [x] `epyc-orchestrator` `69cbe730` repairs a dashboard coherence regression:
  structured live taps with logical aliases now infer the physical CPU-lock
  role from topology/port metadata before painting the region grid, so
  concurrent streaming taps are not hidden just because one tap is labeled
  `coder_escalation` while the lock grid is keyed by `frontdoor`. ✅ 2026-07-05
- [x] `epyc-orchestrator` `ea47f672` separates the Regions Lock summary counts
  for real `/proc` holders, live structured tap requests, tap-inferred activity,
  and slot-inferred activity. This fixes the misleading `/proc holder
  instance(s)` label when the live-tap panel shows concurrent active requests
  that do not map one-for-one to process lock files. Focused dashboard route
  HTML tests passed (`22 passed`). ✅ 2026-07-06
- [x] `epyc-orchestrator` `a151d319` hardens local planner JSON extraction after
  the first fully local canary turn emitted a valid fenced action followed by an
  extra closing brace. Action and critique parsing now recover only the narrow
  case of a valid leading JSON object with trivial trailing bracket noise, then
  still run normal schema/critic validation. This fixes the observed
  `local_ingest` parse discard without accepting arbitrary prose as data.
  Focused controller/coordinator tests passed (`78 passed`). ✅ 2026-07-06
- [x] `epyc-orchestrator` `6d67c565` adds ordered provider-trace telemetry to
  `planner_archive.jsonl`: primary/fallback draft attempts record `ok`,
  `parse_ok`, action type, and unusable reason; primary/fallback critic attempts
  record `ok`, `parse_ok`, decision, confidence, and parse error. Archive rows
  now also carry `draft_action` and `final_action`, so local-only overnight runs
  can be audited without reconstructing the planner tap manually. Focused
  planner-coordinator tests passed (`41 passed`). ✅ 2026-07-06
- [x] `epyc-orchestrator` `8f3ce0b5` and `04a76fd1` close the next
  local-planner W8 drift: the first commit makes W8 candidate-generation
  availability explicit, and the second filters the prompt's Available Actions
  schemas to the currently selectable set. During W8 candidate-generation
  pressure, `seed_batch`, `deep_eval`, and `structural_prune` are now absent
  from the action menu rather than merely listed with a warning. Focused
  creativity/planner tests passed (`43 passed`), with `py_compile`, focused
  `ruff`, and `git diff --check` clean. ✅ 2026-07-06
- [x] `epyc-orchestrator` `c366e8aa` reconciles dashboard active-inference
  state before painting: CPU topology slot activity no longer promotes into
  active Live Inference / Regions Lock holders unless corroborated by
  structured tap rows or real `/proc` locks, while GPU/direct-access slot
  occupancy remains visible. The dashboard now consumes `display_activity` from
  the coherent snapshot. Focused dashboard helper/route tests passed
  (`135 passed`) and ruff was clean; API reload served build `c366e8aa`.
  ✅ 2026-07-06
- [x] `epyc-orchestrator` `3fff13fc` fixes the first bug exposed by that
  provider trace: a local `deep_eval tier 3` draft was correctly rejected by
  `local_frontdoor`, but the later higher-tier probe guard resurrected the same
  rejected shape over the safe fallback. Rejected-draft fallbacks now carry
  explicit provenance in the rationale, and the higher-tier guard will not
  override them in the same trial. Focused planner/action tests passed, then the
  full touched suites passed (`153 passed`). ✅ 2026-07-06
- [x] `epyc-orchestrator` `8b3220c7` and `8464986e` move the routine
  local-planner path to the observed fastest reliable split: `local_frontdoor`
  drafts the full controller prompt, `local_worker` critiques the reduced
  critique prompt, and `claude` remains the critic fallback. Local critique
  prompts now get the same hard fenced-JSON output contract as draft prompts.
  The first `local_frontdoor` canary drafted strict JSON in ~154s; the older
  `local_ingest` critic still emitted prose and required Claude fallback, which
  motivated the `local_worker` critic default. Focused provider/coordinator/
  launcher tests passed (`70 passed`). AutoPilot trial `1200` later failed
  safety on `tool_use` regression, and the daemon was restarted at the boundary
  as PID `3438615` with `code_stale=false`. ✅ 2026-07-06
- [x] `epyc-orchestrator` `26c8ec2c` adds a default-off two-stage local
  planner provider for the next canary: `local_brief_frontdoor` /
  `local_ingest_frontdoor` / `local_two_stage` first asks
  `ingest_long_context` for a bounded controller brief, then asks `frontdoor`
  to draft the normal fenced action/rationale; `local_brief_worker` uses
  `worker_general` as the second stage. Critique calls pass through to the
  final role, and planner archive rows include `local_briefed_planner` stage
  metadata. This is not live until a restart explicitly selects the alias.
  Focused provider/coordinator/launcher tests passed (`79 passed`), with the
  broader launcher/action/phase pass also green (`146 passed`). ✅ 2026-07-06
- [x] `epyc-orchestrator` `5c4e3560` closes the local-planner hardening tail.
  After the PID `3470012` restart, trial `1203` stayed on local providers:
  `local_frontdoor` drafted a `seed_batch`, `local_worker` rejected it, and the
  coordinator substituted a replayable `memrl_retrieval` numeric fallback
  instead of consuming another seed/deep deferral. NumericSwarm journaled
  concrete applied params before API reload and T1 eval. Focused planner/action
  tests passed (`189 passed`), ruff and `git diff --check` passed, and GitNexus
  was refreshed. ✅ 2026-07-06
- [x] `epyc-orchestrator` `6a016f25` closes the latest Regions Lock summary
  coherency gap: the panel now reports tap-inferred active CPU-region holders
  beside real `/proc` lock holders instead of implying that only the off-tap
  holder exists. Focused dashboard tests passed (`23 passed`), and GitNexus was
  refreshed. ✅ 2026-07-06
- [x] `epyc-orchestrator` `d76f0b5d` closes the follow-up quiet-holder
  coherence gap: the Regions Lock overlay now treats quiet/stalled open
  structured-tap requests as lock candidates, formats tap-inferred holders with
  a dedicated label helper, and distinguishes tap-inferred active holders from
  real `/proc` holders. Focused dashboard route/panel/helper tests passed
  (`147 passed`). ✅ 2026-07-06
- [x] **Local drafter quality tail**: `epyc-orchestrator` `24ab6170` fixes the
  next contradiction exposed by provider traces. The W8 action-availability
  section already removed `seed_batch`, `deep_eval`, and `structural_prune`
  from the selectable schemas during strict W8 candidate generation, but the
  higher-tier and eval-coverage pressure sections still told the local drafter
  to prefer T2/T3 `deep_eval` or seed coverage probes. Those sections now take
  the live W8 candidate-generation bit and preserve T2/T3 pressure only through
  available replayable candidate actions (`numeric_trial` with journaled
  applied params or one-flag `structural_experiment`). Focused creativity tests
  cover W8-active higher-tier pressure, coverage pressure, and no-scored-row
  behavior (`46 passed`), with `py_compile`, `ruff`, and `git diff --check`
  clean. The running AutoPilot PID predates this commit, so the remaining live
  canary is to restart at the next safe boundary and confirm local drafts stop
  proposing unavailable seed/deep deferrals. ✅ 2026-07-06
- [x] **Dashboard restart-guidance surface**: `epyc-orchestrator` `03f3917e`
  adds the read-only `autopilot_restart_advisor` envelope to
  `/dashboard/api/autopilot_progress` current-code health and renders compact
  `restart ready` / `restart wait for boundary` labels in the dashboard.
  Follow-up `9ed7b95f` aligns the advisor CLI default restart command with the
  operator's long-run budget (`--max-trials 3000`). Focused dashboard/advisor
  tests passed (`134 passed`), with `py_compile`, `ruff`, and `git diff
  --check` clean. The live API was reloaded as PID `3638698`; live advice for
  AutoPilot PID `3525618`/trial `1207` correctly says `wait_for_boundary`
  because the stale daemon is in active `seed_batch` dispatch. ✅ 2026-07-06
- [x] **Local-role planner failover**: `epyc-orchestrator` `bf9bece7`
  preserves the Codex-alias cross-model protection but stops sending
  `local_frontdoor` draft fallback to Claude when a distinct local role
  (`local_worker`) is already configured as the critic. Fallback drafts from a
  distinct local role can now be independently reviewed by the original local
  primary, so routine local-local operation remains local even when the spend
  breaker is inactive. Focused planner/provider tests passed (`65 passed`),
  launcher/advisor tests passed (`13 passed`), and focused `py_compile`,
  `ruff`, and `git diff --check` were clean. ✅ 2026-07-06
- [x] **Outcome-stall dispatch guard**: `epyc-orchestrator` `9522b76e`
  prevents the higher-tier probe guard from overriding a planner-selected
  frontier-moving action while outcome progress is already stalled, and
  `78ae65e6` makes the frontier-stale condition a bounded pre-dispatch
  constraint instead of prompt-only advice. When frontier admission is stale,
  passive/eval/housekeeping actions are replaced with the first available
  numeric trial fallback; already frontier-moving actions (`numeric_trial`,
  prompt/code/GEPA mutation, one-flag structural experiment, or
  `train_routing_models`) pass through. Focused AutoPilot action/phase/provider
  tests passed (`140 passed`), plus ruff, `py_compile`, `git diff --check`,
  push, and GitNexus refresh. The boundary restart loaded `78ae65e6` into live
  AutoPilot PID `3901517`; `phase_health_report.py --require-current-code
  --json` is clean. ✅ 2026-07-06
- [x] **Snapshot/region-lock freshness coherence**: `epyc-orchestrator`
  `b81f3113` makes `_snapshot_impl()` call the fresh region-lock scanner instead
  of replaying the TTL cached payload, so the snapshot stream cannot overwrite a
  newer direct `/dashboard/api/region_locks` poll in the browser. Regression
  coverage fails if `_snapshot_impl()` returns to `_region_locks_cached()`.
  GitNexus impact was LOW; validation passed focused helper tests, full
  `test_dashboard_region_locks.py` (`26 passed`), ruff, `py_compile`, and
  `git diff --check`. The boundary API reload is complete and
  `/dashboard/api/health` returned `status="ok"`. ✅ 2026-07-06
- Focused validation passed across the touched slices: `49` planner/provider/launcher tests, `43` W6/readiness tests, `46` spend-breaker/economics tests, `233` action/dashboard tests, `49` structural/restore tests, `64` GEPA/prompt-root/API/eval propagation tests, `36` sequential/paired-diagnostics tests, `44` phase/restart/dashboard health tests, `138` rejected-draft/action/creativity tests, and `11` earlier GEPA integration tests, plus focused `py_compile`, `ruff`, and `git diff --check`.

Next measured extension:
- Let current AutoPilot PID `3901517` continue from trial `1212` unless phase
  health fails. The next ordinary planner turn should prove that local drafts
  follow the W8-filtered action menu and that the outcome-stall guard no longer
  lets coverage probes or passive work preempt a frontier-moving action.
- Build a two-stage planner provider after the one-shot local-ingest/local-
  frontdoor path has telemetry: `ingest_long_context` synthesizes a bounded
  planner brief, `frontdoor` or `worker_general` drafts the action from that
  brief, and Codex/Claude remain sampled audit or fallback critics. This is the
  orchestration-native target pattern; it should be A/B measured before
  becoming the default.

---

#### Headline verdict

**Both loops are engineering-rich and outcome-poor.** They are among the best-built control planes in the estate (crash-safe journals, fail-closed gates, atomic contracts, an exclusion taxonomy, durable circuit breakers), but **every gate that converts *trials* into *durable value* is either statistically unreachable or unimplemented, and every health signal measures liveness, not yield.** The system can burn 750+ trials, exceed its planner budget, and freeze its Pareto frontier for a week while every surface reports "active, blockers: []".

Any fix that adds telemetry without adding an **outcome KPI + escalation rule** deepens the pathology.

##### Verified evidence (independent counts, this session)
- **Effectively zero durable promotions.** The live journal (`orchestration/autopilot_journal.jsonl` + `_1.jsonl`) spans to **trial 1169** yet contains **exactly one `baseline_promotion` event** in its whole history. There are 229 "keep" decisions, but those are trial-level keep/revert outcomes (keep=229 / revert=374 / excluded=305 / unchanged=5 over 1,055 entries), **not** production promotions.
- **Frontier frozen ~7 days** (last admission ~trial 1005, 2026-06-28); W8 promotion trajectory is `stale_accumulating` with no replay-eligible candidate since the trial-1158 refutation. This is the single binding blocker on the whole promotion pipeline.
- **Generation mix is misaligned with the promotion gate.** The two *replayable* candidate types W8 promotion requires — `numeric_trial` and `structural_experiment` — got **8 trials total** out of 1,055; `seeder` alone consumed 529. The loop spends its evals on candidate types that structurally cannot promote.
- **The autopilot dashboard is observation-only**: `src/api/routes/dashboard.py` exposes **28 GET endpoints and 0 POST** — no pause/rewind/promote/reweight from the UI. It also computes `baseline_promotions` server-side and never renders them.
- **Kernel loop**: the verify harness (`kernel_eval.sh`) genuinely enforces correctness-first ordering (a FAIL exits before speed is ever measured), but its coherence gate marks **any non-empty output "coherent" when no baseline is supplied** → `correct=1`; there is **no PPL gate**; the Pareto frontier is **empty** (only a null-valued seed row ingested, no real sweep); and **rewind/purge — a named non-negotiable — is absent**.

##### Why the orchestration gate is "dead by construction" (the mechanism)
The stall is a stack of independently-fatal statistical faults, each inside the human-owned trust boundary:
1. **Rate non-inferiority axis is era-blind.** `E_rate_noninf` compares each trial to a 120-row historical mean spanning the concurrency 3→1 eval-regime change: ~93% of z_rate observations are negative, max `E_rate` ever ~1.11 vs a threshold of 20. Because the joint rule refutes when *either* axis refutes, this one broken instrument kills quality-positive candidates and drags `combined_E` below the W8 replay floor.
2. **Sequential policy has ~zero power.** `confirm_e=20` within `max_k=12` needs sustained z≥0.57; observed max ~0.51, mean ~0.17. A genuine consistent z=0.17 improvement is guaranteed refuted. An anti-ratchet that can never fire is indistinguishable from a bug.
3. **Alpha wealth is a lifetime Bonferroni, exhausted.** ~54 fingerprints charged against a lifetime cap of ~20 → `new_fingerprint_confirmations_allowed=false` **permanently** — every future confirmation is pre-blocked even after (1) and (2) are fixed.
4. **The frontier speed axis is un-reproducible.** The 4-point frontier holds clean-window 66–69 t/s; today's ambient-contention evals read 14–33 t/s and can never dominate → 160+ consecutive "dominated" trials; HV frozen.
5. **`seq_accumulating` exclusions freeze both promotion paths at once** — the Pareto archive *and* the legacy 3-reproduction ratchet — so nothing accretes (`autopilot.py:5429`).
6. **The e-process's "fixed null" isn't fixed** — `_seq_inputs_for_trial` rebuilds it from a shifting 120-row window every trial, voiding anytime-validity even after (1) and (2).

**Upstream waste feeding the dead gate:** the generator layer proposes **inert candidates** (knobs behind OFF flags, single-flag toggles → 0 keeps in 119 trials; NSGA-II runs at 3–11 trials/surface ≈ random; critic-prose rejections have surface-banned all 8 numeric surfaces). It is expensive: planner spend ~$486/mo projected vs a **$250 budget that is only a status string** (unenforced, `digest.py:278`); routine trial **drafts go to metered cloud models** (`planner_providers.py` has only Claude + Codex providers) despite a 12-server self-hosted fleet and the open-source-only policy; ~18% of evals die mid-trial discarding all work; each eval costs ~750–900s at `concurrency=1` while 8 replicas idle.

##### Kernel-R&D loop verdict
Promising skeleton, **not yet safe for autonomy, pointed at the wrong objective.** Phase 0 (`kernel_eval.sh`) + Phase 1 (`kernel_store.py`) genuinely enforce correctness-first ordering, append-only idempotent ingest, and atomic OBSERVATION-disciplined export — validated end-to-end **once** (prefetch +2.11%, MemUnitStalled −55%, byte-identical). But three of four load-bearing design promises are unimplemented: the coherence gate passes anything non-empty without a baseline; no PPL-within-ε gate exists; the advertised 3-axis Pareto is effectively 1-D and currently **empty** (absolute/aggregate t/s never populated by a real sweep); rewind/purge is absent. `MUL_MAT_ID` (the MoE op for the stated first workload) is ungated; the +2.11% headline has no variance/CI gate (AB_ROUNDS=2/REPS=3). **Phase 2 is ~40% built** — `kernel_sweep.sh` (inner sweep) exists but there is no nightshift scheduling, no store-guided next-point selection, no GPU cross-session lock, and no GPU-busy guard (`inference_guard.sh` watches host RAM only, blind to the MI210). Strategically, the loop optimizes single-stream GPU speed, which the campaign summary declares **structurally exhausted**, while its measured durable value landed on **capability/residency** (122B/80B IQ2 at eval-parity) — an axis the store cannot represent.

##### Dashboards verdict
Two well-built **liveness** instruments that reproduce the central risk in the UI layer: neither answers *"is this loop producing value?"*
- **:8000 (autopilot)** — genuinely wired freshness contract, shard-aware journal reads for decision panels, statistically literate progress bars. But it never renders the `baseline_promotions` it computes; surfaces no keepable-rate / wasted-eval / alpha-wealth / trials-since-promotion; reads only the **frozen base journal shard** for trial-duration distributions (post-rotation trials missing — [[feedback_autopilot_journal_rotation_read_all_shards]]); still executes **dead v6 `/slots`** code shipping permanently-empty prompt/content fields at 2Hz ([[project_v6_slots_no_prompt_content]]); leaves **5 rendered panels outside the freshness registry**; wraps GEPA/Pareto updates in bare `catch{}` so frozen panels masquerade as data; and offers **zero steering affordances** (pause/rewind/quarantine live in shell tribal knowledge).
- **:8100 (hub)** — clean stdlib service, honest empty states, real tests. But the **kernel freshness badge classifies export-file mtime**, so a cron re-export of one row reads "fresh" forever; the Pareto panel is an empty shell fed by a contract whose throughput fields the producer never fills; the chart fabricates y-positions for null-aggregate points (`kernel.html:159`); and the backlog banner (488 open tasks, a vanity 53.9% all-columns denominator) aggregates without priority, staleness, or velocity — a **count, not a steering instrument**.

---

#### Remediation roadmap (phased by risk + dependency)

Ranks reference the workflow synthesis; the adversarial critic's corrections are folded in. Effort S/M/L; impact low→transformative.

##### Phase 0 — Stop-loss (operator action, zero engineering cost)
- **Pause the orchestration autopilot.** It is dead by construction, so continued operation yields ~0 promotions while burning ~$16/day planner spend and ~45 eval-wall-hours/week. Pause via **SIGTERM at a trial boundary** — `pause` is a no-op ([[feedback_autopilot_pause_broken_use_sigterm]]); leave the kernel loop and both dashboards running. Restart precondition (write into the master index): *amendment bundle approved + positive-control canary passes*. **Operator-owned; no autonomous action taken.**

##### Phase 1 — Safe code fixes inside the autonomy boundary (no MEASUREMENT amendment)
- **[P1 · M · transformative] Paired per-question (McNemar) screening in `eval_tower.py`** — run candidate and baseline on the same question set/seed; feed the discordant-pair statistic into seq accumulation. **The largest power gain that needs no trust-boundary change** — it raises z per observation instead of lowering thresholds, de-risking the (slow) amendment queue. `paired_stats.py` already exists.
- **[P1 · M · transformative] Outcome-first stall detection + KPIs** — PARTIAL LANDED in `18c71bcc`: `phase_health_report.py`/`phase_status.py` now exposes journal-derived outcome blockers (frontier-admission staleness, baseline-promotion staleness) and recent keepable/wasted/learning-excluded rates; default is advisory and `--require-outcome-progress` makes it strict. Dashboard `baseline_promotions` + keepable/wasted cards already exist. Remaining work: render the phase-health outcome block where needed, add the :8100 hub card, backtest thresholds, and only then wire operator-configurable auto-pause/escalate through the durable pause latch.
  - [x] :8100 hub outcome-first stall-detection card ✅ 2026-07-17 — mirrors a file-backed autopilot outcome contract (env AUTOPILOT_OUTCOME_JSON; wrapper or bare forms), honest degrade to :8000 when unexported; keepable/wasted/learning-excluded rates + frontier/promotion stall counters + blockers; freshness on semantic generated_at never mtime. epyc-root dashboard/{server.py,static/handoffs.html} (+16 tests, live smoke 16/16). NOTE: running hub serves pre-edit code until host-side restart.
  - [x] **:8100 hub process durability** — the bare `setsid` launch is NOT surviving host/session churn (died twice 2026-07-17: PID `1879248`, then restarted `2411377` @23:45; down again by 2026-07-18, restarted). Replace with a durable supervisor (`systemd --user` unit or a health-check-restart loop) so the hub + its freshness/outcome/kernel cards stay up without a manual relaunch. Owner: dashboard/infra. Non-inference. ✅ 2026-07-22
  - [x] Hub kernel chart no longer fabricates y for null-aggregate points (single-only variants omitted + disclosed); Pareto panel degrades honestly (throughput producer = epyc-inference-research kernel_rnd, out of dashboard scope); kernel freshness badge verified fixed (03485b28) + regression-locked; priority-bucket chips color-coded. epyc-root dashboard/static/kernel.html ✅ 2026-07-17
- **[P1 · M · high] Pre-eval inert-candidate skip** (narrowed) — before `hybrid_eval` in `dispatch_action` (`actions.py:459`), do a **static flag-dependency lookup** against the merged config and return `SkipOutcome('invalid','lever not active')` for knobs behind OFF flags (journaled, zero eval cost). Scope to statically-decidable cases only; do not claim to detect in-eval activation (kv-compaction firing) without dose-telemetry.
- **[P1 · S · high] Stop planner waste** — move `_maybe_force_seq_*` due-checks *ahead* of `plan_with_providers` (they consume journal/state only; ~38 metered draft+critique cycles were discarded post-hoc); add a durable **operator outbox** for operator-domain critic rejects (surfaced on the run strip) so the planner stops re-drafting the tool-sentinel lane; give `append_blacklist` a measured-harm reason-class + TTL decay so the 8 surface-wide numeric bans self-heal.
- **[P1 · M · high] Local planner tier + hard spend breaker** — add a `LocalPlannerProvider` (OpenAI-compatible against frontdoor) and route routine trial **drafts** local, reserving metered cloud for critique/escalation ([[feedback_fable5_godtier_architect_use]], [[feedback_opensource_only]]); make the $250 budget an **enforced** circuit breaker (today only a status string).
- **[P1 · S · medium] Dashboard integrity sweep** — DONE 2026-07-05 (superset landed; see `progress/2026-07/2026-07-05-dashboard-transport-hardening.md`):
  - [x] Duration scans confirmed already shard-aware (`_read_autopilot_journal_rows`) ✅ 2026-07-05
  - [x] Dead v6 `/slots` prompt/content reads + `_find_slot_by_objective` deleted (orch `216d089a`) ✅ 2026-07-05
  - [x] 5 panels registered + endpoints stamped (pareto, repo_readiness, optimization_brief, insight_graph, build_rev — health now folds 14 panels) ✅ 2026-07-05
  - [x] Bare `catch{}` → self-clearing in-panel error chips (`renderPanelErrorChip`) ✅ 2026-07-05
  - [x] Beyond the sweep — full transport hardening after the tap/locks/topology trio staled again: client wedge-killers + 15s transport watchdog, `_poll_all_slots` 2.5s deadline + `slots_poll_meta`, region-locks/port TTL caches + tap-enrich fail-open (reverts the f6209d78 coupling), rotation-proof tap reads + client fetch fallback + badge/content unification, health `serve_path` block + `?probe=snapshot`, SIGKILL chaos test, all pollers on timeout-bounded `fetchJSON`, MI210 :8802 first-class `mi210_gpu` node (operator-decided). Orch `1cea531a`→`581caccc`, deployed API PID `2839729` ✅ 2026-07-05
  - [x] Second wave — orphaned `autopilot_prompt_tap` surface retired end-to-end (orch `87c5f970`; writer never existed in-repo, file was 45d dead) ✅ 2026-07-05
  - [x] Second wave — panel renamed `regions lock` + GPU/extern device rows folded into both grid paths + off-pipeline "orphan inference" cards in the live tap panel + non-OK contention matrix renders as a loud incident line (orch `9ade5019`, operator request) ✅ 2026-07-05
  - [x] Second wave — no-op API restart guard: `EnvRestartApplicator` skips the restart when the live uvicorn env already matches (positive-match-only via `/proc/<pid>/environ`); `api_restart: performed|skipped_noop` journaled as an eval covariate; `config_applicator.py` added to phase-health drift list (orch `b1a21e79`; live at next AutoPilot launch) ✅ 2026-07-05
  - [x] Third wave — false "off-tap CPU-region holder" cards eliminated (recurring `worker_general.full` / `autopilot:numeric_trial` warning the operator kept seeing). Root cause is a monitoring false positive, NOT a leak: region locks are `fcntl.flock` read from `/proc/locks`, so the kernel releases them the instant the owner exits — a `/proc` holder is always a live dispatch. The tap-request set is parsed from a fixed ~1 MB tail of `inference_tap_events.jsonl` (rotates at 512 MB, 3× in 5 days under eval load → 1 MB spans only seconds), so a genuinely-running holder mid prompt-prefill (no chunk events yet, while concurrent cross-role chunk traffic pushes its `start` past the tail) goes invisible and mis-renders as off-tap; worsened as eval-batch volume rose. Fix: `_recover_offwindow_lock_holder_requests()` reconciles the `/proc` lock frame against the parsed window (same role+idx-or-pid rule as the client) and, for any otherwise-invisible active holder, does ONE bounded 8 MB reverse read to fold its newest still-running request back in — mirroring the existing `dashboard_tasks.py` reverse-grep recovery; gated so the streaming common path pays nothing. SSE structured-tap stream routed through the shared helper; misleading warning copy reworded (autopilot eval/numeric_trial IS tapped). Focused dashboard/tap suites green (`177 passed`). Orch `43578845`, deployed API PID `2963472` (API-only reload; autopilot untouched) ✅ 2026-07-10
  - [x] Fourth wave — region-locks GRID no longer hides running NUMA quarters. Two gates: (1) `active_stack_numa_mode()` defaulted `full` (nothing exports `ORCHESTRATOR_STACK_NUMA_MODE`) while the stack runs `both` — all quarter servers up/healthy — so the grid collapsed each role to its primary; defaulted it to `both` (explicit env overrides). (2) visible shapes were gated on the contention matrix's co-placement `instance_pairs`, hiding heavy-role (`ingest_long_context` 80B) quarters that have no pairs; visibility now follows the role's CONFIGURED instances (matrix still gates role inclusion + ×-blocking colour, measured data untouched). Result = operator-confirmed canonical map (architect=Full, worker_vision=q1, frontdoor/ingest=Half0+q0–q3, vision=Half1+q0–q3, worker_general=Full+q0–q3). `334 passed`. Orch `0c7218b5`, deployed API PID `559551`. NOTE: the config-compiler (`stack_priors`/`stack_change_guard`/`stack_templates`) `both`-migration is a SEPARATE in-flight parallel-session effort (template↔prior parity invariant across 5+ mode readers; committed `stack_priors.yaml` already `both` while template default lags → pre-existing `test_default_yaml_allows_generated_alias_ports` failure on clean HEAD) — NOT touched here; complete it by exporting `ORCHESTRATOR_STACK_NUMA_MODE=both` at launch ✅ 2026-07-11
- [x] Contention matrix freshness: hash-scope false positive (live hash included auxiliary `eval_batch_frontdoor`; measured-role hash `df373c79cc4af06f` matched all along) — RESOLVED by the codex session (orch `3d1706c6` + `120498c9`: measured-role-subset hash centralized in `contention.py`, all consumers aligned, API reloaded, live `matrix_status: ok`; NO re-bench needed). Details: `contention-matrix-v6-quarter-refresh.md` ✅ 2026-07-05
- [x] Outcome-health run-strip surface: orchestrator `c25d6f6e` forwards
  `autopilot_outcome_progress` in `/dashboard/api/process_status` and renders
  compact phase/outcome/code health chips in the AutoPilot run strip. This
  keeps outcome-stall KPIs visible where operators steer, without changing
  loop control. Focused dashboard suites passed (`165 passed`), plus `ruff`,
  `py_compile`, JS `node --check`, and `git diff --check`. Backend field
  deployment awaits the next orchestrator API reload. ✅ 2026-07-06
- [x] Optimization brief steering surface: `epyc-orchestrator` `eec1c2fe`
  adds a ruled-out-experiments summary to the operator optimization brief and
  dashboard renderer so the brief now surfaces fenced dead-ends plus malformed-
  surface churn, not just the current levers. Focused `optimization_brief`
  tests passed (`9 passed`) and the touched files stayed `py_compile`/`git
  diff --check` clean. ✅ 2026-07-06
- [x] Optimization brief ruled-out scrub: journal-aware filtering now removes
  bug-corrupted critic fences from the main ruled-out list and surfaces them
  separately from malformed-proposal churn; live API reload verified. ✅ 2026-07-08
- **[P1 · S · medium] Production-safety + parity fixes the synthesis dropped** — isolate GEPA per-candidate prompt writes (`gepa_optimizer.py:88`) from the live prompts dir (a crash leaves a mutated production prompt) via the existing WorktreeManager/isolation path; make the **W6 gaming comparator config-aware** (`audit_block_report.py:407` is blocking the Fable gate ~29 trials on a between-candidate-variance false positive); extend `cmd_restore` (`autopilot.py:6309`) to purge StrategyStore + AP-22 memory ([[feedback_autopilot_rewind_must_purge_strategy_store]] — the loop the scar was named for).

##### Phase 2 — The human-owned MEASUREMENT amendment (ONE bundle, one operator sign-off)
Package these trust-boundary changes into a **single** proposal with a shared Ville-simulator attestation pack, so the critical path is one round-trip, not four. Agents produce the analysis; **the operator signs the change; never weaken a gate silently to "unblock" the loop.**
- **[P2 · rank 2] Era-fence the rate non-inferiority baseline** — compute `baseline_task_rate` only from rows matching current `eval_concurrency`+`speed_metric_mode`, or pair it against the scheduled `seq_baseline_draw` references (`autopilot.py:1943`). Short bridge: make the rate axis advisory (non-joint-refuting) until the fence lands.
- **[P2 · rank 4] Power-calibrate the sequential policy** — extend `empirical_ville_false_positive_rate` (`sequential_verdict.py:264`) with an alternative-hypothesis arm at the observed z distribution; target ~80% power at z≈0.15 with empirical false-confirm ≤0.05 (likely `max_k`→~40, drop the k=8 budget kill).
- **[P2 · rank 12] Re-price alpha wealth** — charge alpha at the confirmation/fresh-eval *stage* (not per journaled fingerprint), price it at the simulator-derived per-candidate false-confirm rate, and scope the budget to the active instrument era so rewinds restore wealth.
- **[P2 · critic] Freeze the sequential null per fingerprint** — snapshot `baseline_profile`+`baseline_task_rate` at a candidate's first seq observation; reuse it; restart accumulation if an era row lands mid-candidate. Ships in the bundle because it changes verdict inputs.
- **[P2 · rank 6] Re-anchor the frontier speed axis** — use the existing `frontier_rerun` machinery to re-measure the 4 representatives under today's protocol, or open a new Pareto epoch (`autopilot.py:3706`); record an ambient-load covariate per eval. Append an `instrument_eras.yaml` row (never edit). Must land **with** Phase-3 throughput (fan-out changes per-request t/s).

##### Phase 3 — Prove the pipeline can promote, then re-open throughput
- **[P3 · rank 3 — operator-approved, NOT a silent edit] Unfreeze the Pareto archive** — admit `seq_accumulating` non-dominated trials to `upsert_representative` (`autopilot.py:5403`; same epistemic state as `mad_noise` per `learning_exclusions.py:63`), re-enabling reproduction clustering + the legacy ratchet as a fallback. **Caveat (critic):** this reactivates a sealed baseline-promotion pathway around the human-owned seq gate — treat as an operator-approved change with median-tested dominance preserved, not "a one-condition change plus tests."
- **[P3 · critic] Positive-control canary** — replay a **known-real** improvement (the unused 96t single-NUMA point, 49.1 t/s on 30B-A3B — [[project_96t_single_node_operating_point]]) end-to-end through generation→eval→confirmation→fresh-eval and require it to **promote**. The only direct test that separates "gate broken" from "nothing left to find." Keep it + a known-neutral twin as a **standing regression pair** after every instrument change/era row.
- **[P3 · critic] Eval-suite discriminability audit** (do before trusting P2 thresholds) — the flat 1.85–2.18 quality band may be a suite-ceiling / substring-scorer artifact ([[feedback_substring_scorer_comma_brittle]], [[feedback_eval_saturation_masks_model_gap]]), not candidate quality. Read-only per-question pass-rate + brittleness + minimum-detectable-effect analysis; if the effective quantum exceeds z≈0.15, fix the suite first, else P2's calibrated gate is calibrated against noise. **✅ 2026-07-17 — IMPLEMENTED: `scripts/analysis/eval_suite_discriminability.py` (`70bcca95`, 22 tests). Live audit CONFIRMED the suspicion: real_suite_v1 is underpowered (MDE 0.186 > 0.15 target) AND run-unstable (two runs on the same 50 qids → 0/50 vs 35/50, flip_rate 0.72). Fix the suite before trusting P2 thresholds / certifying OP-1.**
- [ ] **Fix `real_suite_v1` discriminability BEFORE certifying OP-1** (forward work from the audit above) — root-cause the run-instability first (two runs on the *same* 50 qids scored 0/50 vs 35/50 — scorer nondeterminism? substring-scorer brittleness [[feedback_substring_scorer_comma_brittle]]? seed/sampling handling?), then raise n / de-saturate so MDE < 0.15. Re-run `scripts/analysis/eval_suite_discriminability.py` to confirm. **Owner: eval-tower / parallel inference session** (validation needs eval runs). **Blocks OP-1** (§A00 #1 in the master index).
  - [x] **Root-cause the 0/50 vs 35/50 instability** ✅ 2026-09-24 (RTG-16) — not the scorer, the substring
    matcher or the seed: `real_suite_v1_eval_20260706T192007Z` is a TOTAL-OUTAGE run (50/50 `error=True`:
    12 `Backend unavailable (circuit open): :8070`, 38 no-progress-nudge escalations, `eval_concurrency=3`)
    and `eval_suite_discriminability.py` pooled its errors as wrong answers against the clean
    `…20260707T013009Z` run (35/50, 3 errors). Fixed in orch `8a829233`: error rows leave the flip vectors,
    error-dominated runs (error_rate ≥ 0.5, `--error-dominated-gate`) leave run-spread and are reported as
    `error_dominated_runs_excluded` / `run_stability_unmeasurable`; `pass_rate`/MDE unchanged (ETR-1 scoring).
    Re-scored on the two real ledgers: flags `run_unstable, brittle` → cleared, run_spread 0.70 → 0.0,
    MDE 0.267 unchanged. 25 tests pass. **Remaining = the MDE half only** (n=50 ⇒ MDE 0.267 > 0.15): needs
    a larger real_suite_v1 run — inference, eval-tower owner.
- **[P3 · rank 11, unbundled] Eval throughput** — land the queued `eval_batch_serving` telemetry pass (measured 4.86× wall-time) as a **decision-gated** codified-recipe run with operator approval + protocol id + attestation + an `instrument_eras.yaml` row; separately enable topology-safe `eval_concurrency`; persist per-question results so killed trials salvage work. Must land **with** the P2 speed re-anchor.

##### Phase 4 — Kernel-R&D loop: harden before any Phase-2 autonomy
- **[P4 · rank 7 · transformative] Fail-closed correctness** — require a baseline for the coherence compare (no baseline → `NO_BASELINE`, never `correct=1`); add a `llama-perplexity` |ΔPPL|<ε gate; parameterize `test-backend-ops` to include **`MUL_MAT_ID`** (MoE op for the stated first workload); add a variance/CI gate on the A/B delta. Verify with a deliberately-degraded negative control + the validated prefetch positive control.
- **[P4 · rank 8, critic-corrected] Record absolute + aggregate t/s; add the value axis** — add a batched `llama-bench` pass so `aggregate_tps` + always-populated absolute single t/s exist (frontier is empty today); store a numeric correctness margin (ΔPPL, tbo pass-fraction) so the "3-axis" frontier is real; stop the hub chart fabricating y for null-aggregate points. Capability/residency (122B/80B IQ2 at eval-parity) is a **step function, not a Pareto axis** — record it as a separate **attested capability row**, don't force it onto the frontier.
- **[P4 · rank 9 · S] Purge/rewind by git_sha** — add `kernel_store.py purge --git-sha`/`rewind`; open the DB read-only for query commands; fix the broken insert/dup counter. **Hard precondition** for Phase-2 nightshift scheduling — a build+commit loop without purge pins reverted commits on the frontier forever. **✅ 2026-07-17 — IMPLEMENTED: `purge`/`rewind --git-sha` (read-only inspect + dry-run-default + --force) + dup-counter fix (root cause: `total_changes` is cumulative-per-connection, never 0 after the first insert → every row mis-counted; fixed via `cursor.rowcount`). `a1f38cd`, 11 tests.**
- **[P4] Build the missing Phase-2 machinery** (nightshift schedule, store-guided next-point selection, GPU cross-session flock, MI210-aware busy guard) **only after** correctness + purge land.

##### Phase 5 — Management / dashboard steering (both loops)
- **[P5 · rank 13, critic-corrected] Hub backlog as a steering instrument** — bucket open tasks by priority; flag handoffs untouched >30/90d into a probably-dead lane feeding an operator archive-review queue (index changes stay operator-approved per CLAUDE.md); fix `pct_done` to an open-scope denominator. **Do not** compute a burn-down ETA over the bulk-import-corrupted velocity series without fencing imported-vs-organic tasks first.
  - [x] Backlog % interpretability: board payload + banner now carry `activity_today` (handoff commits / files touched / boxes checked / boxes added since local midnight) with an explicit "prose-only — % cannot move" warning; root cause of the operator's second stale-board report (10+ commits, 0 checkbox flips) — epyc-root `ea561387` ✅ 2026-07-05
  - [x] Checkbox-discipline governance so the % moves when work happens: checklist-sync gate in `/wrap-up` (Claude + Codex skill copies) + always-loaded CLAUDE.md rule binding autonomous checkpoint commits — epyc-root `ea561387` ✅ 2026-07-05
  - [x] Bucket open tasks by priority in the backlog banner: root dashboard payload now emits priority buckets and the banner renders them as open handoff/task/untracked counts. ✅ 2026-07-06
  - [x] Probably-dead lane: handoffs untouched >30/90d or missing activity now surface as a sorted clickable archive-review candidate list in the backlog banner; index/archive changes remain operator-owned. ✅ 2026-07-06
  - [x] Promote the open-scope denominator (`pct_open_done`) to the headline next to `pct_all_done`. ✅ 2026-07-06
  - [x] Separate backlog completion from intake growth ✅ 2026-07-27 — the headline/bar now
    use `pct_open_done` only, the hub surfaces absolute `all_tasks_done`, and the task-flow
    timeline adds first-observed `newly_filed` / `tasks_newly_filed` while retaining legacy
    `opened` fields for old consumers. Focused parser/timeline validation: `42 + 10` passed.
- **[P5] Kernel freshness badge on data recency** — classify on `max(runs[].ts)`, not export-file mtime.
- **[P5] Steering affordances** — close the "zero POST" gap: guarded operator actions (or, minimally, copy-exact SIGTERM/pause command chips) so pause/rewind/quarantine leave shell tribal knowledge.
- **[P5] Governance/attention tax** — 132 handoffs / 488 open tasks and a 224-line master index restating runtime state in ~6 places (near-daily alignment commits) are themselves a bottleneck; the outcome-KPI header + archive-review lane are the levers.

---

#### If you can only do five things
1. **Pause the orchestration autopilot now** (Phase 0) — zero effort; stops provably-zero-yield burn; makes restart the forcing function for the amendment queue.
2. **Repair/demote the rate non-inferiority axis** (P2 rank 2) — the single biggest mechanical blocker; nothing downstream works while it refutes 93% of candidates.
3. **Power-calibrate seq + re-price alpha + freeze the null as ONE amendment bundle** (P2 ranks 4+12+critic) — one operator sign-off instead of four multi-day stalls; without it the gate stays uninformative and confirmations stay pre-blocked.
4. **Paired McNemar screening in `eval_tower`** (P1) — the largest power gain needing **no** amendment; makes the calibrated gate reachable at realistic effect sizes.
  - Building block landed (A1, 2026-07-17): `paired_stats.py` now carries the `dataset_sha256`+`test_profile` equality gate (`require_matched_comparison`) alongside `mcnemar_from_vectors`; Wilson/ECE/ROC-AUC consolidated into `src/llm_primitives/stat_tests.py`. eval_tower screening hook = Wave-2 B1.
5. **Outcome-first stall detection with auto-escalation + positive-control canary as the resume gate** (P1 + P3) — the recurrence guard so the next regime drift surfaces in days, not six weeks, and the one is-this-producing-value view both loops lack.

---

#### Cross-cutting risks to hold throughout
- **Instrument-regime drift is the root cause, not an incident** — concurrency 3→1 broke the rate axis; the clean post-cutover window broke the speed axis; the moving 120-row null broke anytime-validity. Record regime covariates (concurrency, ambient contention, `speed_metric_mode`) on **every** eval and fence comparisons by them, or the next infra change silently re-kills promotion.
- **Trust-boundary pressure runs both ways** — never let an agent weaken a gate to "unblock" the loop; but don't let the amendment queue stall while the loop burns money. The single bundle + enforced spend breaker address both.
- **Cross-loop coupling** — a kernel change reaching the fleet shifts orchestration eval t/s; add a kernel-promotion → orch era-row/re-anchor trigger.
- **Doc/runtime divergence** — the 3-axis kernel Pareto, the PPL gate, MutationGraph/diversity cadences, and several `program.md` cadences are advertised but unwired; the LLM planner consumes descriptions as capabilities → **wire or delete**.
- **Kernel Phase-2 autonomy is a latent safety hole** — enabling a nightshift build+commit loop before fail-closed correctness (P4 rank 7) and purge-by-git_sha (P4 rank 9) would pin wrong-but-nonempty kernels and reverted commits on the frontier; the GPU also needs its own busy-guard + cross-session flock.
- **Unbounded files** — `inference_tap_events.jsonl` (~475MB) already blinds panels under load; the timeline rebuild is O(full history) per commit with silent hook failures.

#### Verification (how to confirm each fix, honoring MEASUREMENT.md)
- **Effectiveness KPIs (observations):** after Phase 1, `/dashboard/api/health` + `phase_health` report a named outcome blocker during the stall; the run-strip promotions/keepable-rate match an independent `jq` count over `autopilot_journal*.jsonl`.
- **Gate reachability (decisive):** the Phase-3 positive-control canary **promotes** through the repaired pipeline; a known-neutral twin distributes z_rate around 0. The single check proving the loop can produce value again.
- **Amendment attestations:** each P2 constant ships with a Ville-simulator report (power at z∈{0.1,0.15,0.2}, empirical false-confirm rate, n≥10k sims) as its attestation ref; era/epoch rows appended to `instrument_eras.yaml`, never edited.
- **Kernel loop:** the degraded negative control FAILs at PPL/coherence while passing the old non-empty check; the next real sweep produces a non-empty `pareto[]` with absolute + aggregate t/s on every OK row; `purge --git-sha` removes a row from both the store and the re-exported contract.
- **Throughput (decision-gated):** `eval_batch_serving` promotion is a codified-recipe run with operator approval, protocol id + attestation, quality parity (paired per-question) + wall-time delta; post-flip median `eval_wall_s` target <300s (from ~750s), killed-trial waste <5% (from ~18%).

#### Key files
- **Orchestration loop:** `epyc-orchestrator/scripts/autopilot/autopilot.py`, `safety_gate.py`, `eval_tower.py`, `paired_stats.py`, `planner_coordinator.py`, `planner_providers.py`, `phase_health_report.py`, `phase_status.py`, `digest.py`, `audit_block_report.py`, `species/*`; `src/autopilot_core/sequential_verdict.py`, `learning_exclusions.py`, `instrument_era_guard.py`, `pareto_archive.py`; `orchestration/instrument_eras.yaml`; `MEASUREMENT.md`.
- **Orchestration dashboard:** `epyc-orchestrator/src/api/routes/dashboard.py`, `dashboard_panels.py`, `dashboard_freshness.py`, `dashboard_tap.py`, `dashboard.html`.
- **Kernel loop:** `epyc-inference-research/scripts/kernel_rnd/kernel_eval.sh`, `kernel_store.py`, `kernel_sweep.sh`; `handoffs/completed/mi210-kernel-rnd-loop-proposal.md`.
- **Hub dashboard:** `epyc-root/dashboard/{server.py,handoff_parser.py,freshness.py,static/kernel.html,static/handoffs.html}`, `scripts/handoffs/build_handoff_timeline.py`.

#### Provenance
- Workflow run `wf_37dce809-c0a` (7 facet audits + synthesis + gap-critic). Per-agent transcripts under the session's `subagents/workflows/wf_37dce809-c0a/`.
- Independent counts this session: journal keep/revert/species tallies, `baseline_promotion`=1 across trial-span 1169, dashboard GET/POST endpoint counts.
- Not modified: the master handoff index (index changes are operator-approval-only per CLAUDE.md). Link this handoff in from the index if you want it tracked in the active queue.

## Track: objective-task-rate-goodput
<!-- gate: none -->

> Folded from `handoffs/active/objective-task-rate-goodput.md` @ `b1bf3f3f7ade` on 2026-11-02 (BRF-T1-F20, route 1a, operator D1/D5; retired row RTG-23 → RTG-02). Body moved verbatim, headings demoted two levels to nest under this track; every open and closed box kept its text and ID.

### Objective: task_rate Axis + Goodput Frontier Rebuild

**Status**: W3 FLIPPED AND LIVE ✅ 2026-08-04 — live dominance is `task_rate_4d_v1`
`(quality, seq_task_rate_qph, -cost, reliability)` (`afdd5d74`); legacy `median_request_tps` is now
the shadow series. Frontier restarted at the flip commit. Open: W3d (the superseded hold conditions,
incl. the still-live zero-quality/high-rate objection), W3e (retire the tier-cost axis — blocked by
positional consumers), W5 (regime-profiled offered load).
**Created**: 2026-06-12
**Updated**: 2026-08-04
**Priority**: ACTIVE — the flip landed on an operator decision; remaining work is axis hygiene (W3d/W3e) and the load-profile era (W5)
**Spec**: [fable5-findings-05-objective-design.md](../completed/fable5-findings-05-objective-design.md) — read before claiming any waypoint. Slots into [fable5-findings-01-impl-plan.md](../completed/fable5-findings-01-impl-plan.md) as Phase 1.6.
**Related**: [evidence-plane-instrument-repair.md](autopilot-program.md#track-evidence-plane-instrument-repair) (noise/admission rules the new axis inherits), [autopilot-continuous-optimization.md](autopilot-program.md) (live consumer), [MEASUREMENT.md](../../MEASUREMENT.md) §P-SPEED-OBJ (already names task_rate as the speed axis) + §5 era table (E3→E4 retire-view)

#### 2026-07-27 Operator re-prioritization — PIVOT-FIRST after bench closure

Operator (reviewing the E8 frontier): "optimizing [median_request_tps] is gameable — verbose
output pumps the metric; the only real-world metric is how quickly orchestration performs a
task, and how well." This is this handoff's thesis; elevated out of the dead lane as the
FIRST item of the post-closure robustness/workload-tuning pivot (master-index ★ block).
Key unlock: the 16 fresh E8 reseed trials (2026-07-26/27) are era-fenced, honest-instrument
rows — plausibly satisfying W3's quality-eligible-replay gate — and the replay is
deterministic journal recomputation (zero inference; per MEASUREMENT_POLICY.md →
*Deterministic replay before regeneration*). Sequence: replay E8 rows → task_rate/goodput
frontier → operator policy decision on the live vector flip (P-SPEED-OBJ already names
task_rate as the axis) → panels relabel (extends E8-PANELS-a axis-labeling task).

#### 2026-07-26 Staleness Review

The era prerequisite has advanced, but the
[design-backlog triage](../completed/design-backlog-triage-2026-07-23.md) still requires a
fresh quality-eligible replay: the previous task-rate frontier admitted
quality-floor violations. W3 therefore remains a narrowly gated replay and
policy decision, not a live-vector flip.

#### Why

The current Pareto vector is fully blind to token bloat: quality, t/s, and
reliability are all bloat-invariant, and the "cost" axis is a routing-tier
average, not a token count — so a verbose and a terse config at equal
correctness are Pareto-indistinguishable while differing 30% in wall-per-task
(spec §verdict). An entire manual research domain (TrimR, brevity limits,
enable_thinking=False, tool-output compression) exists as corrective work the
optimizer could not discover natively. `task_rate` = n / eval-wall-hours; both
inputs are journaled, so the axis replays over FULL journal history at zero inference.

#### Waypoints

- [x] **W1 — axis + shadow journal** (~half day): added task-rate helpers and policy constants in `src/autopilot_core/tier_specs.py`; `eval_tower._aggregate()` records `task_rate_qph`, `goodput_qph`, and `tokens_per_solved_task`; new journal rows include live legacy vector + shadow task-rate vector under policy labels.
- [x] **W2 — historical replay + bloat-artifact diff report** (~half day, ZERO inference): replay implemented via `scripts/analysis/task_rate_goodput_replay.py` and `journal_reconstruction` objective-policy replay. Full-journal report: `epyc-orchestrator/orchestration/reports/task_rate_goodput_replay_2026-06-12.md`. Follow-up `d21bbee` folds append-only supersession events before rendering report rows, so replay tables match supersession-aware archive/dashboard state. Follow-up `47c75de` adds a `Baseline Promotion Evidence` section scoped to `baseline_promotion` events whose source trial is present in the effective folded replay rows; malformed/incomplete events render as `n/a` rather than crashing the report.
- [x] **W3 — flip the vector** ✅ 2026-08-04 — LIVE. Operator threw the armed W3b-C tripwire
      ("Autopilot should use tasks/hr"). Landed as `task_rate_4d_v1`
      `(quality, seq_task_rate_qph, -cost, reliability)` in `afdd5d74`, **not** the planned 3-D
      vector, and **not** on the shadow rate metric. Three findings forced both departures:
      - The 3-D `task_rate_3d_v1` CANNOT be the live vector. Consumers index the tuple
        positionally past axis 1 — `safety_gate.py:2303` refuses `len(objectives) < 4`
        ("frontier representative missing objective tuple") and `pareto_archive.py` reads
        `[2]`/`[3]`. Going 3-D would not raise; it would **silently block every baseline
        promotion**. `tier_specs.objectives_from` is the documented chokepoint on
        CONSTRUCTION, but not on CONSUMPTION. So the 4-D shape is kept and axis 1's UNIT
        changes. **Retiring the tier-cost axis is therefore still open — see W3e.**
      - Axis 1 uses `seq_task_rate_qph`, not `task_rate_qph`. The latter divides the
        decision-partition question count by the FULL-batch wall clock: trial 775 scored
        202.9 qph @ 51.5 t/s vs trial 778 at 170.5 qph @ 49.8 t/s — a **19% objective gap
        from a 3% speed difference**, the rest being `n` moving 43→38. It also returns
        `0.0` for "unavailable" on **128 of 1,466** journal rows.
      - `dominates()` truncated via `zip()`, so a 3-D point vs a 4-D one compared qph
        against t/s and reliability against `-cost`. It now raises on shape mismatch.

      Verified live on trial 1472: `objectives_live_v1 = [2.025, 59.49, -0.5, 0.8]`,
      `objectives_legacy_v1 = [2.025, 14.78, -0.5, 0.8]`. Frontier restarted via
      `pareto_exclude_before_ts` at the flip commit (both vectors are 4-D, so nothing
      catches a mixed frontier by shape — the epoch fence is what separates them).
- [x] **W3d — the 2026-06-13 hold conditions were never satisfied; they were superseded.**
      Record why, so the hold is not silently re-derived: the flip shipped on an operator
      decision, not on the ">=2/5 legacy frontier points drop" proof threshold. The
      "raw `task_rate` admits a zero-quality high-rate frontier point" objection is still
      LIVE and unaddressed — quality remains a separate axis, so a zero-quality/high-rate
      point can still enter the frontier. Decide whether goodput (quality-scaled rate)
      should replace raw rate on axis 1, or whether the reliability floor is sufficient.
      **✅ 2026-08-12 (`mainA`, pulled from the generated bench and claimed) — RECORDED, and the
      objection is not merely still live: it is MEASURABLY REALISED, and the mechanism is worse
      than the row states.**
      **The live vector** (`tier_specs.py:328` `_rate_objectives_from_row`) is
      `(quality, rate, -cost, reliability)`, all maximised. Quality is read as
      `float(row.get("quality") or 0.0)`.
      **1. A zero-quality high-rate point genuinely cannot be excluded by dominance.** It is
      dominated only by a point that is at least equal on ALL FOUR axes. A point holding the max
      rate is unbeatable on rate, so nothing dominates it regardless of how bad its quality is.
      Pareto cannot fix this; only a floor or a scaled axis can. Searched for one — no
      `quality_floor` / `min_quality` / reliability floor exists in `src/autopilot_core/`.
      **2. The worse half: ABSENT quality is silently scored as ZERO.** `or 0.0` cannot
      distinguish *measured zero* from *never measured*. Measured over both journal shards:
      **231 of 1372 trial rows (16.8%) carry falsy or absent quality** and are therefore admitted
      to the frontier as zero-quality points. So the objection is not a hypothetical about a
      future bad point — one row in six is already in that state.
      **3. `objectives_measurable` promises more than it checks.** Its docstring reads *"True when
      this result carries every axis the live dominance vector needs"* and its body is
      `return seq_task_rate_qph_from(result) is not None` — it validates the RATE and nothing else.
      A row with no quality, cost or reliability passes a gate whose name and docstring both say
      it checked them. That is the same claim-without-witness shape as the era stamps and the
      `--validate-only` help text, sitting in the objective plane.
      **Why the hold was superseded, recorded so it is not silently re-derived:** the flip shipped
      on an operator decision, not on the `>=2/5 legacy frontier points drop` proof threshold the
      2026-06-13 hold named. The threshold was never met and never waived — it was overtaken. Any
      future reader finding the hold unsatisfied should NOT reinstate it; it is void, not pending.
  - [ ] **OPERATOR DECISION — goodput vs raw rate on axis 1.** Not mine to take, and it is bigger
    than a scoring tweak: per the 2026-08-11 rider, a metric change is structurally an **ERA
    BOUNDARY** and should be recorded as an era row rather than an edit. Three options: (a)
    quality-scaled goodput replaces raw rate on axis 1; (b) raw rate stays and a quality floor
    gates admission; (c) status quo, accepting that ~1 row in 6 enters at zero quality.
    **Recommend (b) plus a separate fix**: a floor addresses the dominance hole without redefining
    a banked axis, and the 231 absent-quality rows are a DATA defect that a metric change would
    silently paper over — `or 0.0` should distinguish absent from zero regardless of which option
    is chosen, or the same 231 rows will re-enter under goodput scored as zero goodput.

    **Independent half DONE ✅ 2026-09-14 (RTG-23, `epyc-orchestrator` `fb16d860`, zero inference).**
    `or 0.0` no longer scores absence as a measurement on ANY axis: `quality_from{,_row}` return
    `None` for absence (matching the `seq_task_rate_qph` convention), `_row_axis` reads a bare 0.0 on
    a row whose eval never ran as absence, the row builders return None and the live builder raises
    `UnmeasuredObjectiveError` when any declared axis is unmeasured, and `objectives_measurable` now
    delegates to the builder it gates (it checked the rate only). Consumers report absence as absence
    (dashboard `task_rate_status="quality_unmeasured"`, null goodput; planner evidence `n/a`).
    Replay over BOTH journal shards (1,372 trial rows, journals unmodified): builder-refused rows
    0 → 225, T0 audit entries 318 → 233, frontier sizes UNCHANGED (legacy 11/4/1, rate 13/8), and
    zero-quality frontier points 0 before and 0 after. The 231 falsy-quality rows are 225 rows whose
    eval never ran (224 T0 sentinel + 1 bug-corrupted T1) plus 6 genuine measured zeros — so the
    objection's DATA half is closed and its frontier half was never realised on current data. The
    DOMINANCE hole (a max-rate point cannot be dominated however bad its quality) is untouched and
    still needs option (a), (b) or (c). Downstream consumers carry the distinction: `551d0e48` stops
    `eval_batch_serving_evaltower_window.py` and `run_real_suite_v1_evaltower_window.py` defaulting
    `goodput_qph` to 0.0. Tests: `tests/unit/test_objective_absent_quality.py` (12) plus one per
    window script; `pytest tests -k "tier_spec or pareto or frontier or objective"` 155 passed /
    0 failed (143 on origin/main, same 0 failures).
- [ ] **W3e — retire the tier-cost axis from dominance** (deferred out of W3). The original
      W3 scope included dropping `-cost`; that is what made the vector 3-D and is blocked by
      the positional consumers above. Doing it means fixing `safety_gate.py:2303` and
      `pareto_archive.py`'s `[2]`/`[3]` reads to be axis-NAME-driven rather than positional.
      Until then `-cost` stays a dominance axis and the frontier is wider than intended.
      **2026-09-16 (`sub-autopilot-safety`) — the positional-consumer blocker is REMOVED; the axis
      drop itself is NOT done (box stays open).** Orchestrator `635a3467`, branch
      `sub/autopilot-safety-20260916`, unmerged. `TierSpec.axes`
      (`quality, rate, neg_cost, reliability`) plus `tier_specs.objective_value()`, which raises
      `ObjectiveShapeError` on a wrong-shape tuple. Converted: every `pareto_archive.py` semantic read
      (summary, summary_text, tier_overview, stepping stones + text, geometry + text, BT tiebreak key,
      parent utility), and in `safety_gate.py` `_pareto_frontier_context` and the reproduced-promotion
      override (now `promotion_fields_from_objectives`, which refuses any shape mismatch, not just
      `len < 4`). Behaviour is identical on real archives: `tests/unit/test_w3e_axis_name_reads.py`
      replays `legacy_4d_v1` + `task_rate_4d_v1` archives reconstructed from the stored journal
      (361 entries each) against golden values captured with the pre-W3e code (frontier ids, full
      dominance-pair sha256, every read), plus a forward test with a cost-less 3-axis tier.
      Targeted suites: 301 passed.
      **Remaining to finish W3e:** a new objective policy whose `TierSpec` drops `neg_cost` (axes +
      `objectives_from` + 3-D reference point), with its instrument-era stamp and frontier epoch
      fence. Positional `[0]`/`[1]`-only readers remain; they are unaffected by dropping axis 2:
      `journal_reconstruction.py:282` (deinflate), `progress_plots.py`, `dashboard.html`
      (`paretoDominates4` loops over 4 slots; a 3-D tuple still compares correctly, since both
      missing values read as 0).
      **Finding (not changed; this lane kept behaviour identical):**
      `safety_gate._pareto_archive_for_safety_guard` replays the journal under the DEFAULT
      `LEGACY_OBJECTIVE_POLICY` with no `exclude_before_ts`. So the archive-max guard and the
      "source trial is a same-tier frontier representative" promotion check run on the legacy t/s
      frontier, not the live `task_rate_4d` frontier, and over pre-flip rows too. Moving the guard to
      the live policy has a coupled hazard: the promotion override copies axis 1 into `speed` →
      `frontdoor_speed`, which would then hold q/h against the t/s 0.8× throughput floor (live
      `frontdoor_speed` today is 23.89, i.e. still t/s). Both must change together.
      **2026-09-16 (`sub-gate-frontier`):** the coupled finding is fixed on orchestrator branch
      `sub/gate-frontier-20260916` (on top of `sub/autopilot-safety-20260916`), **built, under review,
      unmerged**; box stays open (the axis drop is still to do). Detail:
      [`progress/2026-09/2026-09-16-sub-gate-frontier.md`](../../progress/2026-09/2026-09-16-sub-gate-frontier.md).
      **Operator decision D2 (2026-09-16):** option (c) — journal clean trials so they can be frontier
      representatives (today the candidate is journaled after `update_baseline`, so a clean trial never
      is one) — with option (b), N≥3 reproductions, as the interim promotion rule until (c) lands.
      **(c)+(b) built 2026-09-16 (operator decision; branch `sub/gate-frontier-20260916`, in the AutoPilot
      merge train, not yet on main):** clean trials are journaled as frontier representatives and handed to
      the promotion guard before the decision; an empty live frontier needs >= 3 comparable reproductions
      (`AUTOPILOT_EMPTY_FRONTIER_MIN_REPRO`); `promotion_rule` is recorded per trial; the guard fails closed on
      an unreadable archive. Served-config identity: explicit deltas, and for mutations the mutated-file sha
      (`f083a0cd`). Next restart: every tier starts under rule (b). The W3e axis drop itself is still open.

##### W6 — the eval instrument the rate axis is measured on (opened 2026-08-04)

Questions/hour is only meaningful relative to a fixed question set, so the flip made the
instrument's composition load-bearing in a way it never was under tokens/second.

- [x] **W6a — declare the tier mix** ✅ 2026-08-04 (`81be1e56`). The sampler stratified by
      SUITE only (`per_suite = n // len(suites)`); difficulty tier was never a sampling
      dimension, so the realized mix was a byproduct — the real seed-42 n=50 draw was
      **T1:24 / T2:15 / T3:11** and moved with `n` and with any pool edit. Operator chose
      **equal thirds**. Verified on the real 79,479-row pool: n=50 → 17/17/16, n=100 →
      34/33/33, 34 distinct suites still represented, deterministic. A starved tier is
      REPORTED, never backfilled from another tier. **Dashboard visibility ✅ 2026-08-09
      (`epyc-orchestrator` `9e7e5226`)**: GEPA and Pareto now distinguish the outer EvalTower
      lane from this inner difficulty mix. Current points render as `lane T1` plus
      `D1/D2/D3 17/17/16`, with the scored/target count, policy, core id, and rotation in
      point/row context; a bare `T1` no longer falsely implies T1-only decision questions.
- [x] **W6b — rotate the core draw so the optimizer cannot overfit one set** ✅ 2026-08-04
      (`ce6e4bea`). Operator: *"the draw should be somewhat randomized."* Rotating PER TRIAL
      was rejected with numbers: quality is a fraction-correct over n=50, so an independent
      draw each trial adds binomial error `sqrt(0.25/50)` = 7.1% ≈ **0.21 on the 0–3 scale**
      against a baseline near 1.5 — several times the effect sizes the ratchet detects.
      Rotation is per EPOCH (default 20 trials, env-overridable): fixed within a block,
      fresh between. Measured cross-block overlap **3/50, 0/50, 1/50**, mix 17/17/16 every
      rotation. n, mix and pool constant ⇒ expected difficulty unchanged ⇒ a rotation does
      NOT force a re-baseline.
- [x] **W6c — make instrument drift detectable across a restart** ✅ 2026-08-04 (`8e90948e`).
      `_DATASET_SHA_BY_CORE_ID` was a module-level dict, so drift was only visible WITHIN one
      process — and a pool edit lands while the daemon is DOWN. That is exactly how the
      2026-08-04 debugbench retarget passed unnoticed. Ledger persisted; tier mix compared
      too, because `dataset_content_sha256` deliberately does not hash `tier`.
- [ ] **W6d — decide whether the mix should be production-traffic-weighted rather than
      equal thirds.** Equal thirds was chosen as a clean default; a production-representative
      mix would make qph track real throughput more closely. Needs the production task-tier
      distribution, which was not established — the investigation was cut short. Cheapest to
      change while a frontier is already restarting.
- [x] **W6e — surface the generalization gap.** ✅ 2026-10-07 — [MAIN published source and fresh original38/38](../../artifacts/ni08/w6e-success-acceptance-20261007/README.md); descriptive producer only, no causal/calibrated overfitting or live-trial warrant. The W6 audit block already draws FRESH
      questions per trial (`_audit_seed(trial_id, core_id)`) but is `shadow_only=1`. Report
      core-vs-fresh score as an explicit overfitting signal, so epoch rotation is
      instrumented rather than assumed to be sufficient.
- [ ] **W6f — re-establish the T1 quality baseline on the new instrument.** Cleared
      2026-08-04 because equal thirds is a harder mix than the old T1-heavy draw and holding
      1.5357 would score every new trial as a regression and block all promotion. Old values
      preserved in state under `_pre_equal_thirds_baseline_record`. Blocked on trials landing
      on the new instrument; will self-seed via the SG-3/B3a explicit-seed path.
  - [x] **W3a — E8 quality-eligible replay EXECUTED** ✅ 2026-07-27 (Claude session, zero
    inference; report `epyc-orchestrator/orchestration/reports/task_rate_goodput_replay_e8_20260727.md`).
    Machinery green on the fresh era: 1356 journal rows parsed (0 malformed), state epoch
    scoping admitted exactly the **16 E8 reseed trials**; the 2026-06-13 blocker class is
    ABSENT on E8 rows (no zero-quality/low-quality frontier admissions — all task-rate
    frontier points q≥1.77, floor 1.0). Legacy frontier 3 points / HV 8.16; task-rate
    frontier 5 points / HV 150.33; task-rate ADDS trials 1444 (89.1 q/h, 1487 tok/solved)
    and 1456 (83.2 q/h). **Pre-registered drop criterion NOT met** (0/3 legacy points fall
    off; spec needs ≥2/3): the 16 homogeneous surface-sweep trials don't vary verbosity, so
    axis divergence hasn't had a chance to appear. Flip decision → operator (options below).
  - [x] **W3b — operator flip decision: OPTION C chosen** ✅ 2026-07-27 — dual-report
    interim: legacy stays the live dominance vector; task_rate/goodput surfaces on panels +
    telemetry immediately; flip armed on first observed divergence (amber tripwire badge when
    ≥2 legacy frontier points drop under task-rate). Options A (flip now) and B (silent hold)
    declined in favor of visibility-without-risk.
  - [x] **W3c — dual-report panel implementation** ✅ 2026-07-27 (orchestrator `3f21d760`,
    +508/−22, 296+2 tests green; canonical helpers reused from tier_specs + the replay module,
    zero math reimplemented; live-journal smoke reproduces the E8 report: legacy frontier
    {1445,1446,1450}, task-rate adds 1444/1456, tripwire quiet at dropped=0; activates at the
    queued API reload): pareto payload gains task_rate_qph/goodput_qph/tokens_per_solved + offered_load
    per entry (canonical helpers, no reimplementation); speed-axis toggle (median request t/s
    ↔ task_rate q/h); dual-report banner; server-side divergence tripwire. Display-only;
    dominance unchanged; ships at the queued API reload.
  - [x] **W3d-panel — panel activation verified live (2026-07-27)** ✅ 2026-07-27: API-only reload via
    `orchestrator_stack.py reload orchestrator` (performed while fixing the probe-env health
    flapping); `/dashboard/api/pareto` confirmed serving `task_rate_qph`, `goodput_qph`,
    `tokens_per_solved`, `offered_load` + divergence tripwire; 6/6 backend probes green
    post-reload.
- [ ] **W5 — regime-profiled offered load (NEXT INSTRUMENT ERA, pairs with batching
  integration; operator design decision 2026-07-27).** The trial eval's single fixed arrival
  pattern (closed-loop concurrency-3) means task_rate measures one operating point; configs
  can win that point while being wrong for sparse single-request traffic. Resolution chosen:
  regime-ADAPTIVITY stays in the router/placement layer (WP-12 burst machinery + placement
  surfaces are already AutoPilot-trialable); regime-REPRESENTATIVENESS moves into the eval —
  a small offered-load profile set (sparse-1 / steady-3 / burst-N), task_rate per profile,
  dominance on the steady profile or an F1-real-task-corpus-weighted mix. Explicitly REJECTED:
  baking regime-switching into the scalar (unauditable, newly gameable; violates
  one-number-one-protocol). The `offered_load` field landed in W3c future-proofs rows/panels
  for this.
- [x] **W4 — telemetry + doc truth** (~half day): `task_rate_qph`, `goodput_qph`, and `tokens_per_solved_task` are journaled; `scripts/autopilot/program.md` now states that EvalTower `speed` remains the current Pareto speed axis/host-throttle diagnostic, task-rate fields are shadow policy telemetry, and `tokens_per_solved_task` is the bloat diagnostic. The stale wall-occupancy `sum(tokens_generated[role] / throughput_tps[role])` proxy is explicitly marked as not computed/not live. `rg` found no other live system-card copy of that stale text.
- [x] **W5 — policy decision** (2026-06-13, zero inference): keep `task_rate_qph`, `goodput_qph`, and `tokens_per_solved_task` as shadow telemetry; leave live Pareto dominance on the current objective until preconditions below are met.
- [x] **W7 — disambiguate the W3d hold record and W3d-panel activation record.** ✅ 2026-10-07 — MAIN renames only the checked 2026-07-27 panel title; the historical hold title and both bodies remain unchanged. [Current-source explanation](../../docs/reference/rtg23-handoff-identity-and-cache-source-20261007.md).
- [x] **W8 — annotate or replace the `0.0`-for-unavailable sentinel in `task_rate_qph_from{,_row}`**, kept
      deliberately because they feed archived `eval_details.goodput_qph` history but guaranteed to bite whoever
      next reads them as measurements (`src/autopilot_core/tier_specs.py`) (found 2026-09-14, noninf sweep).
      ✅ 2026-10-07 — MAIN accepts optional display helper and explicit legacy-sentinel explanation after original3/3, full native/source custody and APP publication. [Scope/evidence](../../artifacts/ni08/rtg23-w8-display-source-20261007/README.md). Historical values/objective math and W9/W10 unchanged.
- [x] **W9 — do the same for `_float()`, which returns `0.0` for absence** and is used for other journal ✅ 2026-10-07
  MAIN accepted bounded source/evidence: [review](../../artifacts/ni08/rtg23-w9-display-source-20261007/README.md).
      fields — the same sentinel class, left as a follow-up by coordinator ruling
      (`src/autopilot_core/planner_evidence.py:521`) (found 2026-09-14, noninf sweep).
- [x] **W10 — find out why the live `pareto_archive` is empty** (`state["pareto_archive"]` has no keys), so ✅ 2026-10-31 [belief: cc] [source: APP 3c3e016c0f8a49e238c376a1f38493adbae74b40; artifact: artifacts/engineering/w10-archive-authority-20261031/README.md; historical closure hygiene, not quota]
      every count in RTG-23's table is journal replay rather than the live frontier: either expected
      post-flip epoch fencing or a silent loss (`orchestration/autopilot_state.json`) (found 2026-09-14,
      noninf sweep).
  - The answer was already recorded by ROOT `49af91a00d5f79e08c8cd66f8ddaf79a973d5c01`: the 2026-08-10 epoch excludes every prior journal trial through #1505. A 2026-10-31 read-only strict report on retained canonical inputs agrees (`authorized_empty_current_era`, no current-era rows, no legacy state cache). Journal authority removes that cache; no running AutoPilot was observed at this audit, so this is not a claim about a running process or later data. [Evidence](../../artifacts/engineering/w10-archive-authority-20261031/README.md). [belief: cc]

*Declined 2026-09-14: "no quality floor / admission gate exists anywhere in `src/autopilot_core/`" (`quality_floor`
/ `min_quality` grep returns only the replay report's local `QUALITY_FLOOR = 1.0`) — not filed because creating one
IS option (b) of the still-open **OPERATOR DECISION — goodput vs raw rate on axis 1** box above; it is the decision,
not a defect.*

#### 2026-06-13 Policy Decision

**Verdict: HOLD the live vector flip; continue shadow telemetry.**

Rationale:

- The replay did not meet the Fable proof gate: only 1/5 legacy canonical T1 frontier points fell off under `task_rate_3d_v1`; the proposed gate was >=2/5.
- Raw `task_rate` creates an obviously unsafe frontier point: trial 75 enters the task-rate frontier with quality 0.000 and goodput 0.00 because it completed quickly. Quality remains an axis, but the replay proves raw rate alone can preserve junk candidates as non-dominated noise.
- Findings-01 dependencies are not fully in place: per-question ledger, sequential verdicts, core_v2 repair, and E4 retire-view bootstrap are still pending, so flipping now would create another objective-era boundary before the evidence plane can certify effects.

Reopen W3 only after all of these are true:

- N2 per-question ledger + sequential e-process verdict path is live for the restart bundle.
- Instrument repair/core_v2 or equivalent E4 boundary is in force, with frontier/baseline retire-view mechanics ready.
- A replay of the chosen policy (`task_rate` with explicit quality eligibility, or a goodput-shaped variant) no longer admits zero-quality high-rate frontier entries.
- The replay either meets the original >=2/5 historical-frontier proof threshold or a documented shadow-period result shows task-rate/goodput changes live decisions without degrading quality/reliability.

#### Gates & pitfalls

- Wall time carries the same ~9% host-noise CV as t/s (spec caveat 1) — findings-01 Phase 1.4 sequential/median-cluster admission rules apply to the new axis unchanged; never single-trial rate claims.
- `task_rate` depends on question mix AND eval concurrency — both are instrument: fix per core-version, bump policy version on any change; per-suite wall telemetry attributes which suites pay the bloat.
- **2026-08-05 boundary prepared**: orchestrator `65aac3d6` bumps the live identifier to
  `task_rate_4d_v2_resource_lanes`, retains `task_rate_4d_v1` only for faithful historical
  replay, rejects mismatched snapshots from live archive authority, and refuses startup until
  state names the matching execution instrument. The E9 registry/state apply remains human-owned;
  no v2 measurements exist until that transaction is applied.
- Degenerate-terseness is bounded (quality is a co-equal axis); if a long-form role emerges, add a suite-level format-adequacy check — never re-reward tokens globally.
- Tool tokens stay excluded from the rate (already correct); tool use is priced by downstream correctness + wall cost.
- Replay is retire-view, not rewrite: journal rows are immutable; quality is NOT rescaled across eras (MEASUREMENT.md §5).

#### Reporting

Tick waypoints here + one-line progress entry; all rate numbers via the MEASUREMENT.md §2 claim grammar. The master-index N6 row was removed on 2026-06-13 after the hold decision; future W3 work belongs in the gated cluster until reopen criteria are met.

#### Checkpoints

- 2026-06-12 W2 replay result: 656 journal rows parsed, 0 malformed skipped; legacy canonical T1 frontier = 5 points, task-rate replay frontier = 8 points, admitted entries = 247 in both views. Dropped legacy point: trial 776 (quality 1.884, wall 804.5s, task_rate 192.42 q/h, goodput 120.82 q/h) dominated by trial 775 under task-rate. Fable proof criterion (`>=2 of 5`) was **not met**.
- Verification: `uv run pytest tests/unit/test_autopilot_core_contracts.py tests/unit/test_eval_tower_concurrency_metrics.py tests/unit/test_eval_tower_hybrid_eval.py tests/unit/test_autopilot_controller_io.py tests/unit/test_evolution_manager_scrub.py tests/unit/test_safety_gate_baseline_eligibility.py tests/unit/test_per_suite_regression_resolution.py tests/unit/test_self_criticism_resolution.py` → 81 passed; `git diff --check` clean.
- 2026-06-12 W4 doc-truth verification: `gitnexus impact File:scripts/autopilot/program.md --direction upstream` LOW; `rg` confirms the only remaining stale wall-occupancy phrase is the negated warning in the updated text; `git diff --check -- scripts/autopilot/program.md` clean. Landed in `epyc-orchestrator` `9bc4c3a`.
- 2026-06-13 W5 policy checkpoint: live dominance flip held. Shadow telemetry remains useful, but the NOW-class decision is closed as "do not flip yet"; W3 remains gated on N2/E4 and a quality-eligible replay.
- 2026-06-14 replay read-path follow-up: `epyc-orchestrator` `d21bbee` makes `scripts/analysis/task_rate_goodput_replay.py` fold append-only supersession events before rendered report rows. Regression coverage in `tests/unit/test_task_rate_goodput_replay.py` verifies folded values replace raw superseded metrics; combined analytics validation passed (`15 passed`) with focused ruff and diff-check clean.
- 2026-06-14 baseline-promotion evidence follow-up: `epyc-orchestrator` `47c75de` makes `task_rate_goodput_replay.py` report baseline promotion evidence scoped to effective folded replay rows. It does not affect legacy or task-rate archive reconstruction, and incomplete promotion events render safely. Validation: `python3 -m py_compile scripts/analysis/task_rate_goodput_replay.py tests/unit/test_task_rate_goodput_replay.py`; `uv run ruff check scripts/analysis/task_rate_goodput_replay.py tests/unit/test_task_rate_goodput_replay.py`; `git diff --check -- scripts/analysis/task_rate_goodput_replay.py tests/unit/test_task_rate_goodput_replay.py`; `uv run pytest -q tests/unit/test_task_rate_goodput_replay.py` -> 3 passed.

2026-10-07 W10 source-premise review: current APP deliberately removes the persisted pareto_archive cache and reconstructs in-memory authority from journal rows. [Pinned source/test explanation](../../docs/reference/rtg23-handoff-identity-and-cache-source-20261007.md) establishes that contract; it does not sample the current host state or live frontier. W10 stays open only for the owning runtime session to reconcile its actual live state/journal identity, if that historical live observation still needs disposition.

**Scratch**: `/mnt/raid0/llm/tmp/codex-ni06-main-20261006/`; W8 original custody `/mnt/raid0/llm/tmp/ni08-thesis-audit-20261006/`.

2026-10-07 MAIN source-reviewed W6e producer preparation at private APP `129a58c29d3ed1814caa1acfa29d14f604020886`. The existing partition means/counts feed optional descriptive diagnostics; positive gap means core quality exceeds fresh quality, counts include task_failed and exclude infra/scoring failures, and incomparable suite/question mixes are explicit. W6e and live trial gates remain unchecked until their actual scoped acceptance. VB-RTG23-W6E-SOURCE-CONFORMANCE and existing-journal informational VB-RTG23-W6E-DIAGNOSTIC-CARRY are filed before capture/consumption; shadow-only objective and historical trials are unchanged.


W6e source accepted2026-10-07 after separate fresh attempt2; original attempt1 and wrong prebinding remain intact. Optional journal informational carry remains independently tracked under VB-RTG23-W6E-DIAGNOSTIC-CARRY; objectives, shared quality grade, shadow-only behavior and historical rows are unchanged.

W6 optional journal informational carry accepted2026-10-07: [MAIN optional-carry source and original31/31](../../artifacts/ni08/w6e-journal-carry-success-acceptance-20261007/README.md). Actual authored raw block and certified canonical JSON support preserve strict frames/quality/objective/shared grade and absent legacy rows. Three real-writer markers/four projected original rows are authenticated; no live generalization or promotion warrant. The only previously unchecked task for this scope is VB-RTG23-W6E-DIAGNOSTIC-CARRY; the already accepted W6 producer tasks are not counted again.

## Track: orchestration-robustness-audit-2026-07-11
<!-- gate: none -->

> Folded from `handoffs/active/orchestration-robustness-audit-2026-07-11.md` @ `b1bf3f3f7ade` on 2026-11-02 (BRF-T1-F20, route 1a, operator D1/D5; retired row RTG-24 → RTG-02). Body moved verbatim, headings demoted two levels to nest under this track; every open and closed box kept its text and ID.

### Orchestration Robustness Audit — why fixes don't stick

**Status**: DELIVERED — operator review + decision points below
**Created**: 2026-07-11
**Author**: Fable 5 orchestrating session (operator-directed: "persistent bugs regress almost immediately after fixing… investigate deeply, review/audit all bug fixes/logs/progress reports, assess weaknesses and how they should be fixed")
**Method**: 4 parallel investigation streams, 20 subagents (10 corpus extractors over `progress/2026-04..07` (152 files), git forensics, handoff mining, state-source enumeration, dashboard dataflow map, test-history forensics; panel-trio fix→break chain reconstruction; speed-drop forensics; GEPA/Pareto stagnation forensics), followed by a **6-skeptic adversarial verification pass + completeness critic**. Verdicts below are post-verification; falsified sub-claims are marked. Numbers labeled *[audit-extracted]* come from this audit's own corpus extraction, not from any pre-existing in-repo catalog.
**Related**: [loops-and-dashboards-audit-2026-07-05.md](autopilot-program.md#track-loops-and-dashboards-audit-2026-07-05) (the standing loop audit — this document confirms its headline verdict and re-sequences its remediation), [autopilot-continuous-optimization.md](autopilot-program.md), [model-stack-single-source-update-pipeline.md](stack-lifecycle-program.md#track-model-stack-single-source-update-pipeline) (the existing SSoT workstream this audit says to *finish, not reinvent*).

---

#### Executive summary

**Root cause, one sentence: the system has no reliable way of knowing what it is actually running.** Configuration, code version, instrument health, and live dispatch state are each represented in multiple places that can silently disagree — and every recurring failure the operator experiences (dashboard whack-a-mole, dead promotion gate, phantom speed drops, fixes that regress "immediately") is some pair of those representations diverging. The June Fable5 review said it first: *"A system that cannot prove what is running cannot cure itself."* This audit substantiates that across ~250 extracted infra bugs, ~730 dashboard/autopilot commits, and 1,300+ autopilot trials, and converts it into a consequence-ranked remediation plan.

Quantified damage *[audit-extracted]*:
- **~251 orchestration-infra bugs** in the Apr–Jul progress record; **~28% are explicit re-fixes** of previously-fixed issues, rising 25%→~32% (Apr→Jul); July's extractor judged ~2/3 of July infra work regression re-fixing.
- **41% of all epyc-orchestrator commits** since May 1 land in just the dashboard+autopilot surfaces. `orchestrator_stack.py`: 55 commits, 6,560 lines churned, **net −292** — the same lifecycle logic rewritten repeatedly.
- **4462 REPL execution errors** per tap log rotation: 1262 `_final()` keyword arg crashes (models emit `FINAL(result=…)`, function only accepts positional), 403 unknown tool calls, 359 `ZeroDivisionError`. These silently terminate trials with tool errors rather than capturing the model's answer — quantified trial waste that compounds the unreachable promotion gate.
- Panel-trio (regions-lock/live-tap/topology): **9 fix waves, ~70 consistency commits**, fix→break latencies from hours to 46 days.
- Autopilot: **zero (or at most one) baseline promotion in its entire journal history**; last real frontier admission 304+ trials ago; ~60% of the last 500 trials dispatched candidates into a promotion gate that is unreachable by construction.
- "Deployed-but-not-live" (`code_stale` / stale-daemon) mentions: **2 (May) → 10 (Jun) → 76 (Jul)** — a 7× jump; fixes are being counted as landed while production runs old code.
- The **highest consequence-per-bug event fits none of the visible categories**: the autopilot died silently at trial 1302 (Jul 8, no crash message, no lock, no PID) and stayed dead ~23h with every dashboard reporting "active".

**The whack-a-mole mechanism (operator's panel-trio complaint), verified:** the three panels are join views over **eight sources with incompatible timescales** (kernel-instant `/proc/locks`; a ~1MB tail of a 512MB-rotating tap file = seconds of history; 2Hz `/slots` polls that lost identity fields at the v6 cutover; quasi-static config with divergent defaults). Reconciliation logic is **duplicated in three places** (client JS, per-endpoint enrichers, snapshot builder). Every fix picks an authority ordering for one panel pair, which changes what the third panel's join observes — the moles are conserved. The history shows a fuse↔decouple pendulum (Jun-28 fused failure domains → Jul-05 decoupled via TTL caches, forking freshness → Jul-06 re-fused into the coherent snapshot, ~20 commits + 2 same-day regressions). **Caveat from verification:** the coherent-snapshot work *did* cut dashboard churn ~5–10× after Jul-06 — server-side reconciliation works; it's simply unfinished, and the remaining client-side joins keep re-opening it.

---

#### The weakness model (post-verification)

Verdict key: each was attacked by a dedicated skeptic; ✂ marks sub-claims falsified and removed.

##### W1 — Config duplication with divergent defaults *(confirmed; "dominant" downgraded)*
Same fact independently resolved in 2–15 places with different hardcoded defaults: `ORCHESTRATOR_STACK_NUMA_MODE` (4 files/8 refs, **no writer anywhere**, false "launcher exports it" docstring; post-0c7218b5 the dashboard family defaults `both` while the config-compiler family still defaults `full`); `ORCHESTRATOR_PER_REGION_LOCKS` (10 files); role→port (5 authorities); tmp-dir (**two different env var names**); tap paths (~15 hardcoded copies, no shared constant); `paths` fallback silently redirecting to the **archived monorepo path** on config-load failure.
**Skeptic corrections:** not proven the *dominant* class (the standing audit's yield/gate diagnosis competes); the remediation is **not new** — it is the existing N11 / model-stack-single-source-update-pipeline strategy, still PARTIAL after a month, and the real cost is per-reader fail-closed migration, not artifact authoring. Direct precedent that compiled artifacts drift **when committed**: `derived/stack_priors.yaml` broke the template↔prior parity invariant on clean HEAD. A naive fail-loud flip broke ~8 config tests when actually attempted (2026-07-11).
**Fix (R1′):** finish/extend the existing SSoT pipeline to runtime facts (mode, behavior flags, ports, paths, instrument versions) as ONE launcher-regenerated manifest — **never git-committed, refreshed on full spawn AND API/daemon reload**; readers fail closed only after a manifest fixture is threaded through tests and ownership is defined for every entrypoint.

##### W2 — Ephemeral behavior gates *(directionally real; core evidence corrected)*
✂ *Falsified:* "launcher sets PER_REGION_LOCKS only into the llama-server child env" — wrong; `orchestrator_stack.py:1529` sets it in the **API** env, the live API carries the full gate block, and `reload orchestrator` → `start_orchestrator` **is** a working replay owner (this class was already hit and fixed twice: J6 placement flags, tool sentinels).
**Real residual hazard:** any restart that **bypasses** the sanctioned entrypoints (raw `uvicorn`, bare `autopilot.py start`, a watcher) silently reverts gates to consumers' `'0'` defaults; `start_fable_authority_daemon.py` exists precisely because the bare path looked healthy while dropping authority state.
**Fix:** enforce single sanctioned entrypoints (bypass = loud), and add **startup attestation**: every process logs its effective gate-set + config hash at boot; dashboard renders and diffs them. A persisted store adds provenance but is optional; if adopted, own the "store-write is a no-op on a running process" drift explicitly.

##### W3 — Observability derives what it should be served *(diagnosis fully confirmed; remediation redesigned)*
8 client-side cross-feed derivations, 10 bounded-tail file dependencies, **15 distinct coherence bandages** (the bandage inventory is itself the proof), two renderers for the same grid, identity correlation across two PID spaces, regex label parsing as correlation keys.
**Skeptic's viable design (replaces my original):** the uvicorn worker that dispatches a request already holds the region flock — have it **write a small JSON payload into the existing lock file under that flock** (pid, request_id, role, instance_idx, started_at). The dashboard already globs those files; this kills the PID-space correlation, the regex parsing, and the off-window recovery for the lock panel, and ties displayed state to lock lifetime (the timescale mismatch dies at the root). **Do not** demote tap files to pure audit logs (light/backend-managed-lock requests never take a region lock — tap remains authoritative for them + for content); keep the tap and lock panels *decoupled* rather than re-joined. Known accepted blind spot: direct-to-llama bench traffic (runs autopilot-paused). Migration is incremental — finish collapsing to the display-matrix renderer and delete the legacy JS path; **not** a 7k-line rewrite.

##### W4 — Tests ratchet snapshots, not invariants *(core confirmed; gap statement narrowed)*
The flagship bug's defending assertions were **born in the same commit as the bug** (e94ef7a1, 2026-07-06) and defended it for 5 days until 0c7218b5 — and it was *reviewable as wrong at the time* (quarter servers demonstrably running on Jul 3 and Jul 6). ~230 string-presence asserts are the only guard on 7,022 lines of browser JS.
✂ *Falsified:* "no reload-survival / no live-process integration test" — `tests/integration/test_dashboard_restart_recovery.py` (SIGKILL chaos test, e59bfa25) exists. The genuine gap is narrower: **no dashboard-vs-running-stack parity test**, and **no CI or pre-commit gate exists in either repo** — any test policy currently relies on manual discipline.
**Fix (R3′):** (a) hermetic invariant test — `expected_stack_services(mode)` must cover every `NUMA_CONFIG` instance for that mode (this exact test fails under e94ef7a1's assertions); (b) operational read-only parity smoke (listening ports vs rendered payload) run in quiet windows; (c) reader-agreement contract tests for every multiply-resolved value; (d) *replace* — don't delete — string-presence JS tests; (e) wire enforcement through `epyc-root` hooks since no CI exists.

##### W5 — Evidence plane: unreachable gate + unattested instruments *(outcome confirmed; mechanism corrected)*
✂ *Corrected mechanism:* the binding constraint is **not alpha-wealth exhaustion** (that block sits behind `if not seq.get("confirmed")` and only fires for new fingerprints — it is currently shadowed dead code). The binding gate is the **era-blind rate axis**: `confirmed` requires `E_quality≥20 AND E_rate≥20` (`safety_gate.py:789-810`), and `E_rate` caps at ~1.11 because the baseline window spans the concurrency 3→1 regime change — so `combined_E = min(...)` can never reach 20, let alone the 100 promotion floor. Alpha-wealth (genuinely 4.75× overspent) becomes binding only *after* the rate axis is fixed — remediation order matters.
Confirmed: the `tool_use` axis returned 0.0 for trials ~506–1302; its verdicts fossilized into **TTL-less blacklist entries** (`architect_delegation` t655, `specialist_routing` t664/t864) that still fence the operator's named levers and were *not* purged by the Jul-11 sentinel fix (✂ t1064 escalation removed from this list — that was a critic-rejection, not instrument fossilization). Blacklist TTLs already exist for post-1194 entries — the fix is a **backfill + era-fenced purge**, not a new mechanism. Contamination survives rewind (manual StrategyStore belief scrub still needed on Jul-11 despite fix 10a9596d).
**Fix:** (i) loop-side **gate-reachability preflight** modeling the E_rate ceiling (an alpha-only check would not stop the burn), exempting trials with promotion-independent value (seed_batch, baseline draws, deep_eval); (ii) **instrument attestation** — an eval axis must pass a known-good/known-bad control pair before its scores accrue evidence or feed blacklists (this is the audit's P3 canary, generalized); (iii) era-fenced blacklist purge now. Gate-semantics changes remain operator-signed per MEASUREMENT.md.

##### W6 — Process amplifiers *(re-ranked by evidence)*
✂ *Demoted:* monolith **size** (the 2026-05 split relocated stable logic; `dashboard.py`, itself born at that split, stayed the hottest surface; extracted modules have near-zero fix density but `snapshot`/`tasks` fix-*rates* exceed `dashboard.py`'s — churn tracks requirement volatility, not line count). ✂ *Demoted:* parallel-session collisions (**<1%** of fix commits — 2/550; the vivid ride-along anecdote inflated a minor cause).
**Promoted ranking:** (a) **half-done migrations to multiply-read values** — PRIMARY (the parity break, the both-mode split, the W8 report-vs-selector drift fixed 7× in July); (b) **shipping new components straight into the live loop** (local planner: 15 harden/repair commits in <24h — iteration is normal; the defect is no shadow lane); (c) governance bloat, now measured **worse than the standing audit recorded**: 378-line master index, 389 handoffs, 669 open checkboxes.
**Fix:** migration-discipline rule (a change to any multiply-read value must enumerate + update ALL readers in one change; gitnexus impact + epyc-root hooks as enforcement); shadow lane before live loop; adopt the standing audit's governance fixes rather than re-deriving them.

##### W7 — Deployed-but-not-live *(NEW — completeness critic)*
A fix that requires a restart that never happens: tested-green code inert while the stale daemon regresses. `code_stale`-class mentions grew 2→10→76 (May→Jul). This silently **inflates the apparent fix rate** and compounds W4: a green suite and a regressing production process coexist by construction.
**Fix:** "landed" is redefined as **live** — PID-age-verified restart is part of the fix's definition of done; extend the existing `--require-current-code` machinery from advisory to gating.

##### W8 — No process supervision / crash-cause attribution *(NEW — highest consequence-per-bug)*
The 23-hour silent death (trial 1302 → 1305) had no watchdog, no death-cause ledger, and every dashboard said "active". Preceded by repeated reload failures and auto-pauses that also went unattributed.
**Fix:** supervisor + heartbeat + death-cause ledger for the loop; treat as a Phase-0 peer of "pause/run" decisions.

##### W9 — Host-ops as a standing measurement confound *(NEW)*
Page-cache collapse (131GB free → chased as a `--membind` regression), concurrent-download poisoning, post-`drop_caches` NUMA pinning, CPU freq never journaled. Ties directly to the operator's "speed drops" report — see verdicts below.
**Fix:** journal per-timing-event covariates: `min_core_mhz`, `host_inflight`, `numa_balancing`, cache-warm state; filter speed analytics to ≥128-token generations.

##### W10 — REPL execution layer bugs waste trials *(NEW — concrete, measured, quick-fixable)*
Full REPL error taxonomy extracted from `repl_tap.log` (4462 errors, 4280 `CALL()` invocations vs only 93 `TOOL()` — models overwhelmingly emit `CALL()`). Three bugs silently waste trials at high volume:
- **`_final()` signature mismatch (1262 errors):** `context.py:169` declares `def _final(self, answer: str)` (positional-only). Models emit `FINAL(result=…)` (760) and `FINAL(secret=…)` (502). The TypeError terminates the trial with a tool error — the answer exists but the framework can't capture it. Source: `environment.py:418` maps `FINAL → self._final`.
- **Unknown tools (403 errors):** `get_eval_secret` (213) is gated by `AUTOPILOT_TOOL_SENTINELS=1` in `builtin_tools.py:40` — when off, the tool isn't registered but prompts still reference it. `search_files` (154), `get_time` (72), `fetch_stock_price` (34), `web_research` (16), `translate_text` (16), `start_service` (16) have no implementation in either the tool registry or REPL globals. Dispatch at `context.py:529-544` falls through `tool_registry.invoke()` → `ValueError` → `_globals` fallback → not found → propagates.
- **`ZeroDivisionError` (359 errors):** Models generate code that divides by zero. Not a framework bug — models need better numeric safety in generated code.
- **StrategyStore index degradation:** `sqlite=1424, faiss=1424 (99.9%), fts=1423 (99.9%)` — minor, 1 missing each in FAISS/FTS vs SQLite.
- **Trial 1304 killed mid-trial:** `autopilot_killed_mid_trial` — possible resource/stall issue (one instance).
**Fix (quick wins, hours):** (a) `_final()` accepts `**kwargs` and normalizes `result`/`secret` → `answer`; (b) either implement missing tools as stubs (returning descriptive "not available" responses) or remove their references from prompts so models don't call them; (c) confirm `AUTOPILOT_TOOL_SENTINELS=1` is set in all eval-bearing REPL sessions.

##### Dominant interactions (worse than any single class)
- **W5×W1:** era-blind instrument × multi-site rule resolution ⇒ blacklists nobody can trust or attribute — this pair, not either alone, killed the promotion pipeline.
- **W7×W4:** stale daemon × snapshot tests ⇒ green tests + regressing production, by construction.
- **W8×W6:** unsupervised loop × turn-driven observation ⇒ 23h dead, unnoticed.
- **W10×W5:** REPL execution bugs × unreachable gate ⇒ 1262+ answers silently dropped per log rotation, compounding the already-unreachable promotion gate with noise that masks genuine improvement signals.

---

#### Operator-reported symptoms — closed verdicts

**"Token speeds suddenly drop":** host is healthy (4.1–4.5GHz under load, `numa_balancing=0`, no PSI stall, no swap traffic; drop_caches/pinning ruled out in-window). ~90% of apparent drops are **measurement artifacts**: 1-token generations (fixed overhead ÷ 1 token), `speed_metric_mode` flips (aggregate vs median are incomparable), conc=1 vs conc=3 alternation (~37 vs ~10 t/s by design), eval routing-mix shifts, failed evals. Filtered to ≥128-token generations, every (role, shape) is steady across the window (worker_general.full 44–45 t/s; frontdoor.half0 ~32). Genuinely-felt slowdowns = interactive requests colliding with eval bursts (real, by-design; 40.5→11.9 t/s on 2-way overlap). Historic transient throttle is unfalsifiable because frequency is not journaled → W9 instrumentation. Note the `speed_metric_mode` trap was documented in the June Fable5 review and still poisons interpretation — a known-issue recurrence.

**"GEPA+Pareto stagnant for hundreds of trials":** structural, and predicted by the Jul-05 audit. None of the P2/P3 unblockers landed; the rate-axis ceiling makes `confirmed` unreachable; zero-or-one promotions in journal history; last real frontier admission 304+ trials ago; the rebuilt Pareto archive is empty (journal-recorded admissions don't survive the rebuild filter — itself a W1-class dual-view bug). GEPA specifically: 27% of species budget, **0 completed evals in 500 trials** (frontdoor prompt frozen under a "remove after restart" blacklist entry since Jun-05). The operator's "tool use and delegation never tweaked" intuition is **verified** — those levers are absent from the numeric catalogue, or fenced by blacklist entries earned while the tool_use axis was returning 0.0. **Concrete trial evidence (Jul-11):** trials 1300–1309 all dominated, mostly by `seq_accumulating` or `seq_stale_reference`; current trial 1310 just dispatched a `prompt_mutation` on `frontdoor.md` (appropriate pivot away from exhausted `numeric_trial` surfaces). Pareto frontier has only 5 points with tiny gap between q=2.040 and q=2.100. No inference/API errors in recent logs — stagnation is genuine search exhaustion, not infrastructure failure.

---

#### Remediation plan (consequence-ranked; dashboard cosmetics LAST)

**P0 — operator decisions (this week, mostly sign-offs):**
1. **Run/pause call on autopilot.** It is currently burning ~16min eval-wall + planner spend per candidate trial into an unreachable gate. Either pause candidate species until P0.2 lands, or accept the burn knowingly, or land the loop-side reachability preflight (W5-i) which keeps seed/baseline/deep_eval running.
2. **Sign the P2 amendment bundle — rate-axis era-fence FIRST** (it is the binding constraint; alpha re-price is secondary), power calibration, frozen null + the P3 positive-control canary. **Gate the bundle on the eval-discriminability audit** (promoted per the completeness critic — a saturated suite invalidates every calibrated threshold).
3. **Authorize the era-fenced blacklist purge** (t655/t664/t864 + frontdoor GEPA freeze) and re-open tool-use/delegation levers under the repaired axis.

**P1 — highest consequence-per-bug engineering (~days):**
4. **Loop supervision (W8):** supervisor + heartbeat + death-cause ledger.
5. **Deploy gap (W7):** PID-age-verified "landed"; `--require-current-code` becomes gating.
6. **Startup attestation (W2/W1):** every process logs effective gate-set + config hash; dashboard diffs them; bypassing sanctioned entrypoints becomes loud.
6a. **REPL `_final()` keyword arg fix (W10):** accept `**kwargs` on `_final()` and normalize `result`/`secret` → `answer`; eliminates 1262 TypeErrors per log rotation that silently waste trials with captured-but-undelivered answers.
6b. **Unknown tool cleanup (W10):** implement missing tools (`search_files`, `get_time`, etc.) as descriptive stubs or remove from prompts; confirm `AUTOPILOT_TOOL_SENTINELS=1` in all eval-bearing REPL sessions; eliminates 403 `ValueError: Unknown tool` errors per log rotation.

**P2 — structural (~1–2 weeks):**
7. **Finish the SSoT pipeline (R1′):** extend N11 to runtime facts; launcher-regenerated (never committed) manifest refreshed on spawn AND reload; per-reader fail-closed migration with test fixtures.
8. **Lock-file payload enrichment (R2′):** JSON under the already-held flock; collapse to the display-matrix renderer; tap stays authoritative for non-lock requests; panels stay decoupled.
9. **Host/eval covariates (W9):** journal `min_core_mhz`/`host_inflight`/`numa_balancing` per timing event; ≥128-token analytics filter.

**P3 — policy (ongoing):**
10. Migration-discipline rule enforced via gitnexus impact + epyc-root hooks (no CI exists — hooks are the only enforcement point).
11. Invariant-first tests: the hermetic NUMA-parity test, reader-agreement contracts, operational read-only smoke.
12. Shadow lane for new components before the live loop.
13. Measure the right things: **regressions-per-active-trial and promotions-per-100-trials**, not commit volume (the July commit-rate decline was a loop-outage artifact, not convergence — the "system is converging" reading is falsified).

**Explicit de-prioritizations:** stop the dashboard cosmetic fix waves (streetlight bias — consequences ranking: launcher/lifecycle > eval instrument > checkpoint-rewind ≫ dashboard); do not split monoliths for size; do not delete string-presence JS tests until replacements exist; do not re-derive governance fixes the standing audit already wrote.

---

#### Honest notes
- Two of this week's fixes by this session (43578845 off-tap recovery, 0c7218b5 region-locks grid) are correct locally but are themselves **W1-pattern spot-fixes**: 0c7218b5 aligned the dashboard family's default (`both`) while the config-compiler family still defaults `full` — the divergence persists one layer down. Even careful root-caused fixes inside this architecture reproduce the disease; that is the strongest argument for R1′.
- Two claims relayed to the operator mid-audit were corrected by verification and are retracted above: the alpha-wealth-as-binding-gate mechanism (real arithmetic, non-binding — the rate axis binds) and the PER_REGION_LOCKS reload-reversion mechanism (launcher does replay it on the sanctioned path; hazard is bypass-only).
- Promotion count discrepancy: journal key-scan found 0 `baseline_promotion` rows; the completeness critic counted 1 across 1169+ trials. Effectively none; not material to any conclusion.
- **W10 evidence source (Jul-11):** REPL error taxonomy extracted from `repl_tap.log` by this session — 4462 errors, 10 categories. The `_final()` keyword mismatch and unknown tool counts are verified by grep across the tap, not inferred. Model output pattern (4280 `CALL()` vs 93 `TOOL()`) is a confirmed emission bias — extraction handles both paths but it suggests the system prompt may need tuning toward `CALL()` as the preferred form.

#### Checkpoint completions — 2026-07-11
- [x] Autopilot sequential gate preflight now defers promotion-dependent candidate actions when rate-axis reachability is impossible or alpha wealth is exhausted, and pivots to baseline/reference draws ✅ 2026-07-11
- [x] Builtin compatibility tools now register `search_files`, `get_time`, `fetch_stock_price`, `translate_text`, `start_service` with safe/read-only behavior ✅ 2026-07-11
- [x] REPL `FINAL(...)` now accepts `answer`/`result`/`secret`/`value`/`response` aliases and rejects unsupported kwargs with a clear `ValueError` ✅ 2026-07-11
- [x] Autopilot supervisor/death ledger wrapper landed (`autopilot_supervisor.py`, `start_fable_authority_daemon.py` bounded restart/death-ledger defaults) ✅ 2026-07-11
- [x] Startup attestation landed (config digests, combined config hash, gate env capture, mismatch reporting, phase health display of tool/planner flags, including visible planner spend-breaker state) ✅ 2026-07-11
- [x] Planner spend-breaker hardening stayed opt-in for local planner runs: the coordinator default is now off when the env is absent, the authority daemon still pins `AUTOPILOT_PLANNER_SPEND_BREAKER=0`, and the live restart confirmed that env at `0` ✅ 2026-07-11
- [x] PID-age-verified preflight gate landed: `start_fable_authority_daemon.py --preflight` now exits nonzero unless the live PID is age-verified current; the live rejection on Dirac's MH-9 worker is expected because unreviewed runtime `controller_io.py` edits predate PID `1039446` ✅ 2026-07-11
- [x] Host timing covariates landed for P2.9: `host_health.py` now records `min_core_mhz`, `host_inflight`, `numa_balancing`, and cache/cache-memory state; `eval_tower.py` captures compact per-question host covariates plus `tokens_generated` and adds observe-only >=128-token speed analytics fields in `EvalResult.details` ✅ 2026-07-11

#### Checkpoint completions — 2026-07-14
- [x] W2 direct AutoPilot start bypass now fails closed in `epyc-orchestrator` commit `fc0be9bc`: `scripts/autopilot/autopilot.py start` exits `2` before taking the singleton lock when authority env is missing/mismatched, points operators to `scripts/autopilot/start_fable_authority_daemon.py`, and requires `AUTOPILOT_PLANNER_SPEND_BREAKER=0` rather than turning the spend breaker on. ✅ 2026-07-14
- [x] W8/Fable quiet-window evidence refreshed in `epyc-orchestrator` commit `5876a473`: `orchestration/reports/fable5_gate_report_20260714T111641Z.{json,md}` and `w8_promotion_trajectory_20260714T111641Z.{json,md}` confirm AutoPilot is stopped, W8 replay concentration is not warning, W4/W6 restart cutover is still blocked by the W6 gaming alarm, and the tool-use sentinel lane is ready but requires controlled API reload plus authority-daemon restart. ✅ 2026-07-14
- [x] HALO quiet-window spike closed as `completed-not-actionable`: operator-approved install succeeded, 3,532 spans were converted, the HALO canonical compatibility transform validated in `/tmp`, and the analyzer run failed before inference because local `/v1/responses` returned 404; outcome doc is `research/deep-dives/halo-spike-results-2026-07-14.md`. ✅ 2026-07-14
- [x] Controlled API reload plus authority-daemon recycle completed for the tool-sentinel lane: stale supervisor/child `1816107`/`1816109` were SIGTERM/SIGKILL verified dead, fresh supervisor `1890099` with child `1890100` resumed on `AUTOPILOT_TOOL_SENTINELS=1` and gate-3 profile, and the phase advanced to `planner_prompt_build` with `code_stale=false`, `tool_sentinels=true`, `w6_audit=true`, and `AUTOPILOT_PLANNER_SPEND_BREAKER=0`. ✅ 2026-07-14
- [x] Gate-3 latest verification hard-passed against orchestrator PID `1885933`: `get_eval_secret` returned `7/7` success rows, no-tool isolation passed, soft `WEB_RESEARCH: INFRA_FAIL` now fails closed as `web_research result failed (search_failed)`, and a forced web probe after reload still returned a relevant Python.org result through DDG fallback while preserving `success:true`. ✅ 2026-07-14

#### Checkpoint completions — 2026-07-16
- [x] Structural-experiment runtime contamination guard implemented in `epyc-orchestrator`: trial `1403` showed `plan_review=true` apply/attestation succeeded, gate failed, revert hit `[Errno 111] Connection refused`, and later journal rows no longer represented live flag state. The action now snapshots exact prior flags, refuses eval without a restore snapshot, requires strict apply/revert attestation, marks failed apply/revert paths `bug_corrupted`, and routes `eval_result.bug_corrupted_by` through learning exclusion before normal evidence accrual. Focused validation: `151 passed` across `test_autopilot_actions.py` and `test_classify_learning_exclusion.py`; live remediation set `plan_review=false` and attested 6 workers clean. Report: `/mnt/raid0/llm/epyc-orchestrator/orchestration/reports/autopilot_speed_regression_runtime_contamination_20260716.md`. ✅ 2026-07-16
- [x] Speed-regression/v7 read-only audit recorded: exact numeric frontier parameter replays confirmed current-floor throughput around `34.8-35.3 t/s`, but quality deltas are not clean model-quality evidence because qid vectors drifted and pre-fix runtime errors polluted rows. Kernel-lineage audit found the running production server was still the June 26 binary and v7 had IQK plus patch-equivalent ROCm fp8 guard coverage, so no production-kernel source edit was blamed; this 2026-07-16 interim gate was superseded by the 2026-07-20 `production-consolidated-v7` cutover. ✅ 2026-07-16

#### Tasks
- [ ] P0.1 operator run/pause decision on autopilot candidate species
- [ ] P0.2 P2 amendment bundle signed (rate-axis era-fence first) + discriminability gate + P3 canary
  - [x] W5 control-pair attestation report-only scaffold landed in `epyc-orchestrator` commit `7a2a7c89`: `hle_metrics.py` now journals default-off `oracle_adequacy.control_attestation` status (`disabled`/`no_controls`/`incomplete`/`failed`/`passed`) from supplied known-good/known-bad rows without changing SafetyGate, Pareto admission, learning exclusion, blacklists, or thresholds. Binding gate remains operator/policy-gated. ✅ 2026-07-11
  - [x] P0.2a report-only amendment evidence view landed in `epyc-orchestrator` commit `65d4cf40`: `fable5_gate_report.py` now surfaces rate-axis state, latest oracle control-pair attestation, eval discriminability/T3 hard-lane coverage, and RI-10 canary state under `p0_2_amendment_bundle_inputs` with empty blockers and explicit `operator_signing_required`; signed P2 amendment / binding rate-axis era-fence remains operator-gated. ✅ 2026-07-11
- [ ] P0.3 era-fenced blacklist purge + tool/delegation lever re-exploration
  - [x] P0.3a guarded purge planner/apply helper landed in `epyc-orchestrator` commit `a26e6c6a`; dry-run identified exactly the 5 audit-scoped entries (`frontdoor.md` prompt/GEPA freezes, t655, t664, t864) and preserves 49 others. Apply remains operator-gated by `--approval-token ERA_FENCED_BLACKLIST_PURGE_2026_07_11`. ✅ 2026-07-11
  - [x] P0.3b audit-scoped tool/delegation re-exploration landed in `epyc-orchestrator` commit `134ed346`: AutoPilot now marks the three automated instrument-era structural blacklist entries (`architect_delegation` t655, `specialist_routing` t664/t864) as retryable without rewriting YAML, preserves manual frontdoor prompt/GEPA freezes behind the approval token, and journals `p0_3_blacklist_reexploration_*` rationale when dispatching those retries. ✅ 2026-07-11

##### P0 operator gate packet - prepared 2026-07-11

This packet is command-discovery and evidence packaging only. It does not authorize a running autonomous session to pause/resume AutoPilot, sign measurement-policy changes, rewrite the blacklist, or enable the planner spend breaker.

- **P0.1 run/pause call:** inspect current-code and gate status before deciding:
  - `cd /mnt/raid0/llm/epyc-orchestrator && python3 scripts/autopilot/start_authority_daemon.py --preflight`
  - `cd /mnt/raid0/llm/epyc-orchestrator && python3 scripts/autopilot/autopilot_restart_advisor.py --json --strict`
  - `cd /mnt/raid0/llm/epyc-orchestrator && uv run --with pyyaml python scripts/autopilot/model_gate_report.py --json --require-current-code`
  - Decision boundary: keep candidate species running only as an explicit operator choice while the rate-axis/P2 amendment remains unsigned; otherwise pause candidate species or let the preflight/reachability deferral route only promotion-independent work.
- **Command paths repointed 2026-08-11 (`mainD`).** The three commands above pointed at
  `start_fable_authority_daemon.py` and `fable5_gate_report.py`, **neither of which exists** — they
  were renamed to `start_authority_daemon.py` and `model_gate_report.py` in the de-FABLE rename, and
  this handoff kept the old spelling. An operator working the P0.1 decision would have run three
  failing commands. Flags verified against the current scripts before rewriting, not assumed:
  `start_authority_daemon.py` provides `--preflight`, and `model_gate_report.py` accepts `--json`,
  `--require-current-code`, `--out-json` and `--strict`. Narration of past work below is left
  spelled as it was — those sentences describe what happened, and only *runnable* lines were changed.
- **P0.2 amendment bundle:** use the report-only evidence view, then sign outside AutoPilot:
  - `cd /mnt/raid0/llm/epyc-orchestrator && uv run --with pyyaml python scripts/autopilot/model_gate_report.py --json --out-json orchestration/reports/p0_2_amendment_bundle_inputs_20260711.json --out-md orchestration/reports/p0_2_amendment_bundle_inputs_20260711.md --require-current-code`
  - Inspect `p0_2_amendment_bundle_inputs`: rate-axis state, latest oracle control-pair attestation, eval discriminability / T3 hard-lane coverage, RI-10 canary state, and `operator_signing_required`.
  - Boundary: this report is non-binding. Any rate-axis era fence, calibration baseline, frozen null, threshold, or P3 canary adoption remains a MEASUREMENT.md human-amendment action.
- **P0.3 blacklist purge:** preview first, apply only with the explicit token:
  - Preview: `cd /mnt/raid0/llm/epyc-orchestrator && uv run --with pyyaml python scripts/autopilot/blacklist_purge_plan.py --print-md --report-json orchestration/reports/p0_3_blacklist_purge_plan_20260711.json --report-md orchestration/reports/p0_3_blacklist_purge_plan_20260711.md`
  - Apply, operator only: add `--apply --approval-token ERA_FENCED_BLACKLIST_PURGE_2026_07_11`.
  - Boundary: the automated re-exploration exception for t655/t664/t864 is already live without rewriting YAML; the destructive purge of manual frontdoor freezes stays gated.
- [x] P0.1 packet validation: `start_fable_authority_daemon.py --preflight` and `autopilot_restart_advisor.py --json --strict` both report AutoPilot PID `1039446` active on trial `1317`, `code_stale=true`, `restart_needed=true`, `safe_to_restart_now=false`, and `status=wait_for_boundary`; no pause/restart was performed. ✅ 2026-07-11
- [x] P0.1 report-action hardening landed in `epyc-orchestrator` commit `2b78c2f3`: `fable5_gate_report.py` now points the `recover_autopilot_phase` next action at `start_fable_authority_daemon.py --preflight` instead of the weaker phase-health-only report, with a regression test. ✅ 2026-07-11
- [x] P0.2 packet validation: the report-only amendment view ran to `/tmp`, with `p0_2_amendment_bundle_status=attention`, `rate_axis=below_required`, `control_attestation=missing`, `eval_discriminability=low_coverage`, `operator_signing_required=true`, and evidence gaps `rate_axis_below_required`, `control_attestation_missing`, `eval_discriminability_low_coverage`. ✅ 2026-07-11
- [x] OP-1/P0.2 bridge code landed in `epyc-orchestrator`; focused tests reported passing (`test_authority_consent`, `test_autopilot_phase_status`, `test_autopilot_sequential_wiring`, `test_autopilot_startup_attestation`, `test_safety_gate_sequential_verdict`). The operator-owned `orchestration/authority_consent.json` is `root:root` `0444`, so the main agent could not add `seq_p0_2_bridge` consent without non-interactive sudo. ✅ 2026-07-15
- [x] Remaining operator action: add `seq_p0_2_bridge` consent to `orchestration/authority_consent.json` or apply the formal MEASUREMENT amendment. ✅ 2026-10-29 (audit: orchestration/authority_consent.json:7-8 has seq_p0_2_bridge: "allow" granted 2026-07-15T21:50Z; history file autopilot-continuous-optimization-history-...:1611 reports bridge status enabled=true) [no-belief: audit-reconciliation]
- [x] P0.3 packet validation: dry-run purge preview still identifies `54` entries before, exactly `5` removable audit-scoped entries, and `49` preserved entries; destructive apply remains token-gated. ✅ 2026-07-11
- [x] P1.4 loop supervisor + death-cause ledger ✅ 2026-07-11
- [x] P1.5 PID-age-verified "landed" definition (`--require-current-code` gating) ✅ 2026-07-11
- [x] P1.6 startup attestation (gate-set + config hash logged and diffed) ✅ 2026-07-11
- [x] P1.6a REPL `_final()` keyword arg fix — accept `**kwargs`, normalize to `answer` (W10, 1262 wasted trials) ✅ 2026-07-11
- [x] P1.6b Unknown tool cleanup — stub or remove from prompts; confirm `AUTOPILOT_TOOL_SENTINELS=1` (W10, 403 wasted trials) ✅ 2026-07-11
- [x] P2.7 runtime manifest via existing SSoT pipeline (N11 extension) ✅ 2026-07-11
  - Runtime-only derived manifest now refreshes from stack lifecycle events and is kept out of git; the launcher writes `/mnt/raid0/llm/tmp/orchestrator_runtime_facts.json` on start/reload and best-effort after state save.
- [x] P2.8 lock-file JSON payload + display-matrix renderer collapse ✅ 2026-07-11
  - [x] P2.8a region-lock payload attribution landed in `epyc-orchestrator` commit `799f1655` ("Add region lock payload attribution") ✅ 2026-07-11
  - [x] P2.8b display-matrix renderer collapse landed in `epyc-orchestrator` commit `4de996ea` ("Collapse region lock grid onto display matrix") ✅ 2026-07-11
  - [x] P2.8c browser fallback removal landed in `epyc-orchestrator` commit `08e94997`: `dashboard.html` no longer reconstructs a region-lock grid from legacy `by_role`/PID data when the backend display matrix is unavailable; it shows an explicit diagnostic instead, so observability cannot silently fork lock authority again. ✅ 2026-07-11
- [x] P2.9 host covariates journaled per timing event ✅ 2026-07-11
- [ ] W1 runtime-facts consumption follow-up: remaining runtime-facts-backed reader consolidation stays open for surfaces beyond the validated stack-service slice; a live reader insertion for `/mnt/raid0/llm/tmp/orchestrator_runtime_facts.json` was prototyped and reverted after `gitnexus impact active_stack_numa_mode --repo epyc-orchestrator --direction upstream` returned HIGH risk (`22` upstream impacts across dashboard health/topology/node detail/snapshot/tap flows). Re-enter only with explicit acceptance of that blast radius; do not paper over this with another env/PID fallback.
  - [x] W1 runtime-facts stack-service slice landed in `epyc-orchestrator` commit `db62aa3f`: runtime facts manifest now records `runtime_stack.stack_numa_mode`, `selected_servers`, `selected_ports`, and effective paths; stack start/reload/stop refresh the manifest at persisted-state boundaries; dashboard `expected_stack_services()` uses validated runtime selected servers when no explicit `ORCHESTRATOR_STACK_NUMA_MODE` override exists, otherwise it falls back to static manifest behavior. ✅ 2026-07-14
- [x] P3.10 migration-discipline hook (all readers in one change) ✅ 2026-07-11
  - Root commit `6d023e9d` enforced stack-fact migration discipline with the pre-commit hook, validator, candidate gate integration, and focused tests; verified with `py_compile`, `bash -n`, targeted pytest, negative/positive CLI checks, and `git diff --check`.
- [x] P3.11 hermetic NUMA-parity invariant test + reader-agreement contracts ✅ 2026-07-11
  - Commit `608cc54c` landed the shared NUMA-mode normalization helper and aligned launcher, stack-priors, template, guard, and dashboard readers on the same contracts.
  - [x] P3.11a W4/W9 read-only topology parity smoke landed in `epyc-orchestrator` commit `8bbf3eb5`: `test_topology_parity_smoke_for_expected_listener_ports` verifies known-port scanning includes every expected `both` stack service, simulated discovered listeners render as running topology nodes, and undiscovered expected services remain represented as unloaded stack servers. ✅ 2026-07-11
  - Root-side durable record landed in `epyc-root` commit `269c19bb` (`Record topology parity smoke`). ✅ 2026-07-11
- [x] P3.13 regressions-per-active-trial + promotions-per-100-trials metrics ✅ 2026-07-11
  - Commit `fa0391a5` reported the active-trial outcome progress metrics in the phase-status/autopilot/dashboard path; verification stayed clean with Ruff, `py_compile`, the focused pytest batches, and `git diff --check`.
- [x] P3.12 shadow lane for new live-loop components ✅ 2026-07-11
  - Commit `d596b5b2` ("Gate live-loop dispatch on action availability") added the live-loop shadow lane: planner-selected dispatch now skips outside the active allowlist, while sequential/due/fresh-eval/baseline/candidate-replay paths keep their own policy gates.

*Index status: accepted by the operator-directed 2026-07-11 robustness implementation thread; discoverable from the master N2 row and the routing/autopilot dispatch row. Keep current runtime truth in `autopilot-continuous-optimization.md` + `phase_health_report.py --json`.*

#### Checkpoint completions — 2026-07-14
- [x] W1 runtime-facts reader slice completed in `epyc-orchestrator` commit `db62aa3f`: the runtime-facts manifest now records `runtime_stack.stack_numa_mode`, `selected_servers`, `selected_ports`, and effective paths; stack start/reload/stop refresh the manifest at persisted-state boundaries; dashboard `expected_stack_services()` uses validated runtime selected servers when no explicit `ORCHESTRATOR_STACK_NUMA_MODE` override exists. ✅ 2026-07-14
- [x] AutoPilot seq-preflight/live-allowlist deadlock fix completed in `epyc-orchestrator` commit `39fc3653`: deferred seq-gate replacement now bypasses the ordinary planner-selected live-loop allowlist, so retryable `seed_batch` fallbacks can dispatch after the preflight chooses them instead of looping on an allowlist rejection. ✅ 2026-07-14
- [x] Dashboard-region-lock topology rendering sidecar completed in `epyc-orchestrator` commit `774fed69` (`Fix dashboard region lock topology rendering`): the lock display now uses all configured instance topology, marks `launch_selected`, adds `launch_mode` plus `topology_mode=all_configured`, renders inactive configured shapes as `○`, labels all configured NUMA ports independent of expected launch mode, and updates the legend/status copy to distinguish active holder, selected/free, blocked, and configured inactive shapes. ✅ 2026-07-14

#### Checkpoint completions — 2026-07-11

---

#### Research Intake Interface — 2026-07-11 (external source; operator-review, NOT new tasks)

Research-intake **intake-798** ("The Gemma Challenge and the Case for Agent Collabs", HF + Google DeepMind) processed a large open agent-collaboration that ran an autonomous propose→eval→gate→promote loop over the exact same problem shape as autopilot. Its published coordination/verification design ([`gemma-bucket-sync/DESIGN.md`](https://huggingface.co/spaces/gemma-challenge/gemma-bucket-sync/blob/main/DESIGN.md)) is a **worked reference implementation of several properties this audit says autopilot lacks** — offered here as external corroboration + concrete design precedent for the existing W-fixes, *not* as new work items (deliberately no checkboxes added — this audit already flags 669 open checkboxes as bloat). All external claims are attributed; none are imperatives.

- **↔ W5 (unreachable/unattested evidence plane) — tightest interface.** Their verifier fires **only when a claim strictly beats the current champion** (SOTA trigger), re-runs it against a **private held-out prompt set**, and admits only within a tolerance band (±5% TPS) *and* a quality gate (PPL ≤ 2.42). That is a clean, cheap, **gate-reachability-respecting** verification design — the shape W5-i (loop-side reachability preflight) and W5-ii (instrument attestation via a known-good/known-bad control) are reaching for. Crucially, their **automated negative verdicts stay `pending`/re-triable; only human verdicts persist forever and are never overwritten** — the opposite of autopilot's **TTL-less fossilized blacklists** (t655/t664/t864). Lesson for the era-fenced purge (P0.3): automated fences should default to expiring/`pending`, human verdicts to sticky — matching MEASUREMENT.md's human-amendment-only boundary.
- **↔ W1/W2/W3/W7 ("no reliable way of knowing what is running").** Their answer is **structural single-writer**: only the server writes the central store, it **server-stamps every path** (agents never construct central paths), and the read model is **write-through so read-after-write is exact, with TTL only to catch out-of-band edits**. This is precisely the coherent-snapshot direction W3 confirms works (~5–10× churn cut post-Jul-06) and the launcher-regenerated single manifest R1′ proposes — an adjacent-domain existence proof that the structural-constraint approach (not RBAC, not more reconciliation bandages) is the one that converges.
- **↔ W8 (no supervision; 23h silent death) + W7 (deployed-but-not-live).** They run an **in-process watcher** that polls, enforces a 40-min cap, and on completion writes `job_status.json`/`job_logs.txt`; quota state is a **durable ledger that survives restarts and fails closed** (unreadable ledger ⇒ refuse, don't spend). Their honest note — *watcher state is in-memory and lost on restart, but the job still completes and writes `summary.json`, so loss is bounded* — is the exact **"authoritative state durable, in-memory reconstructable"** principle W8's supervisor+death-cause-ledger needs. Their **`reconcile` pass heals results left `pending` by a Space restart** — the missing primitive behind autopilot's empty-rebuilt-Pareto bug (journal admissions not surviving the rebuild filter, a W1-class dual-view).
- **↔ GEPA/Pareto "genuine search exhaustion" (operator symptom).** intake-798's headline failure mode is **Agent Collapse** — the swarm converged onto a narrow set of axes and avoided the hard wins (custom quant, large kernels, engine changes), driven partly by **message-board "context rot"** self-reinforcing early topics. This is the *swarm analogue of autopilot's search exhaustion*; their proposed remedies (explicit exploration incentives, taskforces/channels to break the reinforcement loop) are candidate framings for the P0.3 lever re-exploration and any anti-monoculture proposal-sampling work in [`meta-harness-optimization.md`](../completed/meta-harness-optimization.md) (updated this session).
- **↔ W5 eval-gaming / discriminability gate (P0.2).** Their PPL-only gate **was gamed** (agents held PPL under threshold while degrading MMLU-Pro/GPQA by 15/40 pts); they reactively added MMLU-Pro + GPQA-Diamond for top submissions. Independent, real-world confirmation of the audit's "a single cheap proxy will be gamed; a saturated/1-D suite invalidates every calibrated threshold" concern — argues the discriminability audit gating P0.2 should treat **multi-dimensional + evolving** gates as the steady state, not a fix.

See also the gemma4-specific kernel spinoff: [`gemma-challenge-kernel-techniques-v7.md`](rocm-kernel-authoring.md#track-gemma-challenge-kernel-techniques-v7).

Related checkpoint: MH-9 new-file mutation support landed in orchestrator commit `88639b1f`, closing the PromptForge checkpoint without changing any remaining audit tasks.

#### Audit catch 2026-07-21 — FAISS atomic-save orphans need a startup janitor (recurrence prevention)

37 GB of orphaned `.embeddings.faiss.<uuid>.tmp` files (67 files, Jul 5-20) were reclaimed from `orchestration/repl_memory/sessions/` on 2026-07-21. Root cause is structural, so they WILL re-accumulate: `faiss_store.py` writes tmp → verifies → `.replace()`, with cleanup in a `finally` — but **`finally` does not run on SIGKILL**, and this host runs `earlyoom` (which SIGKILLs by design) plus hard session terminations. Each interrupted save strands a ~2 GB tmp. One tmp was observed live mid-save during the cleanup (caught via `/proc/*/fd`, save completed normally), so any janitor MUST exclude open files, not just old ones.

- [x] Add a startup sweep to `faiss_store.py` (init path): unlink `.{index,id_map}.*.tmp*` in the store directory that are (a) older than 24h AND (b) not held open by any process (`/proc/*/fd` walk — `fuser` is not installed in the devcontainer). ~15 lines; prevents unbounded re-accumulation of ~2 GB/incident orphans. ✅ 2026-07-29 — `sweep_orphan_tmp_files()` in `orchestration/repl_memory/faiss_store.py`, called from `__init__` (orchestrator `1055e1db`). Open-file identity is `(st_dev, st_ino)` not path, since a tmp being written may already have been renamed. Janitor is best-effort and wrapped at the call site — housekeeping must never stop the store from opening. 6 tests, including a held-open orphan surviving the sweep and being reclaimed only once closed, and a raising sweep not breaking construction.
- [x] The 7 remaining tmp files from 2026-07-21 06:25-06:51 (5.1 GB) are candidates for the same sweep once older than 24h. ✅ 2026-07-29 — verified `find orchestration/repl_memory -type f -name '.*.tmp*'` returns zero targets, so no destructive action is warranted; the startup janitor remains covered by `tests/unit/test_faiss_store.py` (43 passed).

## Track: scaffold-autopilot-cost-lever-deployment
<!-- gate: none -->

> Folded from `handoffs/active/scaffold-autopilot-cost-lever-deployment.md` @ `b1bf3f3f7ade` on 2026-11-02 (BRF-T1-F20, route 1a, operator D1/D5; retired row RTG-32 → RTG-02). Body moved verbatim, headings demoted two levels to nest under this track; every open and closed box kept its text and ID.

### Scaffold CoT Cost-Lever — Autopilot Deployment (DESIGN Handoff)

**Status**: 🟡 DESIGN — architecture + task breakdown only. **NOT implemented; no code written; no measurement run.**
**Created**: 2026-07-06
**Owner**: unassigned (design ready for pickup)
**Kind**: episodic-memory-gated cost-lever deployment into autopilot's existing blended-cost optimization.

**Source study (all numbers below are OBSERVATIONS — MEASUREMENT.md, not decision-gating):**
- `handoffs/completed/gpu-cot-scaffold-sidecar.md` — full research arc (G1/G2/verifier/dense-generalization).
- `progress/2026-07/2026-07-06-cot-study-complete.md` — study close-out + the deployment implication paragraph.

> ⚠️ **LIVE-AGENT HAZARD.** A parallel agent is actively working the autopilot daemon right now (trials ~1197–1200, planner/critic changes landing). **Do not edit anything under `scripts/autopilot/` and do not restart the daemon while it is live.** Every `scripts/autopilot/*` reference below is a *read/verify* target for design, not an edit target, until the owning agent hands the daemon back. Coordinate before touching the planner action space.

---

#### 1. Objective

Deploy the CoT "scaffold sidecar" as an **episodic-memory-gated cost lever** inside autopilot's existing multi-objective optimization. The scaffold offloads a large CPU-hosted beneficiary's expensive reasoning to a GPU-resident Qwable-v1 reasoner (35B-A3B distilled; IQ4_XS fits MI210 residency), then runs the beneficiary in no-think mode guided by the injected scaffold. The three pieces of work: **(a)** register the composite *scaffold-then-nothink* route as a first-class fallback lever; **(b)** fold its **blended GPU+CPU** cost into the cost/speed signals autopilot already scores; **(c)** let episodic memory **learn per-task-class when to apply it** — gated to the beneficiary-must-answer regime where Qwable standalone cannot directly take the request because the beneficiary owns tools/context/role constraints. This is a gating + accounting problem on top of infrastructure that already exists; it is **not** a new optimizer.

---

#### 2. The finding in brief (OBSERVATION-grade)

From the GPU study (seed 42, production sampling, GPU-only, single-sample n=10–48 cells — all OBSERVATIONS):

- **Scaffold = robust, architecture-independent COST lever.** Caps the beneficiary's expensive-device (CPU-decode) tokens at ~**100–175** vs the **3,000–9,000** it burns reasoning on its own — a **20–50× CPU-decode-token reduction**, reasoning moved to the cheap GPU. Held across sparse-MoE 35B, dense-GDN 27B (176 vs 9041), and pure-dense gemma-31B (98 vs 3049).
- **Scaffold QUALITY benefit is HEADROOM-CONDITIONAL.** Rescues weak-and-overthinking beneficiaries (Qwen3.6-27B GPQA 6→9/10; sparse-MoE 35B 48→73%) but **no-ops already-saturated ones** (gemma-31B 8=8). ⇒ must be **gated**, applied only where the beneficiary's no-think path FAILS and it would otherwise over-reason.
- **Blended wall-clock objective (the thing to minimize at quality-parity):**
  ```
  T_scaffold = N_gen/r_GPU(gen) + N_gen/r_CPU_prefill(ben) + N_ans/r_CPU_decode(ben)
  T_ownthink = (N_reason + N_ans)/r_CPU_decode(ben)
  ```
  Scaffold wins when the beneficiary would over-reason (large `N_reason` on slow CPU decode) — exactly the weak-and-overthinking regime. Win is driven by the `r_GPU/r_CPU` ratio.
- **Verifier/selector (best-of-N) is MARGINAL (+2pp captured of an +8pp structural ceiling; errors are systematic not stochastic) and is explicitly NOT part of this deployment.**
- **Single-shot scaffold as a capability-*transplant* was FALSIFIED** on code (amplifier-not-substitute, arXiv:2605.28913). It is deployed here **only as a cost lever** in the gated regime, not as a general quality booster.
- **Qwable standalone is the primary reasoning route when allowed.** The GPQA standalone control ran after the scaffold reversal: Qwable standalone **77%** beat scaffold(Qwable→35B) **73%**, so the scaffold is a lossy fallback for beneficiary-must-answer cases, not the preferred way to use Qwable.

---

#### 3. Architecture / integration points (each grounded in verified code)

Repo root for all paths: `/mnt/raid0/llm/epyc-orchestrator` (symlinked `/workspace/repos/epyc-orchestrator`).

##### 3.1 Autopilot multi-objective safety gate — VERIFIED
- `scripts/autopilot/safety_gate.py:329-330`
  ```python
  def objectives(self) -> tuple[float, float, float, float]:
      return (self.quality, self.speed, -self.cost, self.reliability)
  ```
- `EvalResult` fields (`safety_gate.py:230-234`): `quality` (0-3, `fraction_correct*3`), `speed` (t/s — median-request in serial / aggregate-batch in concurrent; `speed_metric_mode` at :259), `cost` (**normalized 0-1**), `reliability` (fraction non-error).
- The 4D Pareto lives in `scripts/autopilot/pareto_archive.py` (and `src/autopilot_core/pareto_math.py`). `objectives()` is the tuple it ingests.
- **CRITICAL NUANCE (corrects the study's shorthand).** The study handoff (§"FORMAL OBJECTIVE", line 227) says the scaffold's blended cost "surfaces directly as the speed/cost axes." That is only *half* right, and the design must respect the distinction:
  - Pareto **`cost` is NOT wall-clock.** It is a normalized **memory/capacity `cost_tier`** average: `scripts/autopilot/eval_tower.py:1383-1385` → `cost = mean(cost_tier)/4.0`. `cost_tier` is a residency/capacity diagnostic (see `scripts/autopilot/program.md:123`, which *explicitly* states the old wall-occupancy proxy `sum(tokens/tps)` is **not** a live Pareto objective).
  - Blended GPU+CPU **wall-clock therefore enters via `speed` (t/s), not `cost`** — and only if the composite route is issued as a single timed request (eval_tower wraps each request in `elapsed = time.time() - start`, `eval_tower.py:1063,1135`, so an internal GPU pre-decode *would* be counted). But `speed = tokens/elapsed` blends tokens generated on two devices over one wall clock, so the raw t/s number is semantically muddy for a composite route. **See Task (b) — this is the core accounting design decision.**

##### 3.2 Reward / cost model (episodic Q-value) — VERIFIED
- `orchestration/repl_memory/q_reward.py:22` `compute_reward(...)`; the study's `cost_ratio` claim is real:
  - `q_reward.py:90-93`: `expected_elapsed = tokens_gen / baseline_tps`; `cost_ratio = elapsed / expected_elapsed`; `cost_penalty = cost_penalty_lambda * max(0, cost_ratio-1)`.
  - Correctness-gated: applied **only when `reward > 0`** (`q_reward.py:75`) — i.e. minimize-cost-subject-to-correctness, matching the study's framing.
  - `baseline_tps` is per-**role** (`config.baseline_tps_by_role`, `q_reward.py:78`); `elapsed` prefers `generation_ms` over `elapsed_seconds` (`q_reward.py:82-86`).
  - Also present: memory-tier penalty (dim 3, `q_reward.py:102-106`, `memory_cost_by_role`), quality-gap penalty (dim 2, :95-100).
- **This is a *different* cost surface from §3.1** — it is the **episodic-memory reward** driving Q-values (QScorer), keyed on a single role's single-device wall-clock. **A scaffold request spans two devices (GPU gen_ms + CPU decode_ms), which `cost_metrics` does not natively represent.** The `cost_metrics` dict keys consumed are `tokens_generated`, `role`, `generation_ms`, `elapsed_seconds`, `regret`, `speedup_vs_teacher` (`q_reward.py:76-116`) — none carries a second-device term today. **See Task (b).**
- Config object: `orchestration/repl_memory/q_scorer.py` `ScoringConfig` (:613), `QScorer` (:690); registry-derived priors `registry_baseline_tps_by_role` (:521), `registry_memory_cost_by_role` (:566).

##### 3.3 Episodic memory (where the gating policy lives) — VERIFIED
- `orchestration/repl_memory/episodic_store.py` — `EpisodicStore` (:136), `MemoryEntry` (:73) with `q_value` (default 0.5), `action_type`, `assigned_role`, `model_id`, and **`sub_decision`** (:97; intake-548 5-class taxonomy → `src/classifiers/subdecision_taxonomy.py`). Methods: `store` (:293), `retrieve_by_similarity(min_q_value=…)` (:522), `update_q_value` (:618), `count_by_combo` (:813).
- `orchestration/repl_memory/retriever.py` — `TwoPhaseRetriever` (:74); decision entry points `retrieve_for_routing` (:160), `retrieve_for_escalation` (:180), `retrieve_for_exploration` (:196), `retrieve_for_classification` (:214). `_scalarized_selection_score` (:46) blends `q_value` with a perf term. **This is the natural home for a `retrieve_for_scaffold_eligibility` decision** (or a new `sub_decision`/`action_type` value consumed by the existing routing retrieval).
- **Gating key** = task embedding + `sub_decision` (task-class) + **difficulty band** from `src/classifiers/difficulty_signal.py` (used already in routing, see §3.5). Episodic memory learns the Q-value of "apply scaffold" per (task-class, difficulty-band) cell.

##### 3.4 Planner / action space + capability registry — VERIFIED (READ-ONLY)
- `orchestration/capability_registry.yaml` — one row per tunable lever. Kinds (`:20-26`): `env | flag | numeric | prompt | registry-field | restart-class`. **All rows are `promotion_state: placeholder`, `actionable_by: "gated:evidence-plane-ledger.md Phase 1"`.** The closest analog to the scaffold lever is `per_role_enable_thinking` (`:141`, `kind: prompt`, `surface: chat_template_kwargs.enable_thinking`, `applicator: config_post`, roles `[architect_general, coder_escalation, frontdoor]`, evidence `+33pp`).
- W4 promotion preconditions (`capability_registry.yaml:8-13`): (1) applicator wired, (2) range validated vs a measurement protocol, (3) `kill_condition` written in the row, (4) one shadowed trial passes attestation.
- Loader/validator: `src/registry/capability_registry.py` `load_capability_registry` (:215), `CapabilityRegistryError`. Compiler: `scripts/registry/compile_capability_registry.py`. Tests: `tests/unit/test_capability_registry.py`.
- Planner reads it: `scripts/autopilot/autopilot.py:54-56` imports `load_capability_registry`.
- Action handlers keyed by `action_type` in `scripts/autopilot/actions.py`: `_action_numeric_trial` (:475), `_action_prompt_mutation` (:950), `_action_seed_batch` (:391), `_action_gepa_optimize` (:1020). A new lever is exercised through a handler of the matching kind.
- **OPEN QUESTION (design fork).** The scaffold is *not* a pure `prompt` kwarg like `enable_thinking` — it requires a **preceding GPU generator call** whose output is injected before the beneficiary decodes. So it is a **composite route**, not a single chat-template toggle. Options: (i) model it as a new `kind` (e.g. `route-composite`) in the registry with a dedicated applicator; (ii) model it as a `prompt`-kind lever whose applicator triggers the two-stage path at the routing layer (§3.5). **Decide this with the daemon-owning agent before adding any registry row** (see CLAUDE.md "Agents & Automation": no index/registry changes via sub-agents without explicit operator approval).

##### 3.5 Orchestrator routing / role layer (where the composite route attaches) — VERIFIED
- `src/api/routes/chat_pipeline/routing_decision.py` — `select_initial_route` (:64), `apply_failure_veto` (:103), `apply_ingest_triviality_guard(..., difficulty_band, ...)` (:152). Consumes `classify_and_route` (def in `src/classifiers/keyword_matcher.py`).
- `src/routing_bindings.py` — `BindingRouter.resolve(task_type) -> role` (:80), `prior_distribution` (:168). `src/roles.py` — `Role` enum (:68), `Tier` (:52).
- **Existing reasoning-effort lever the scaffold joins:** `src/graph/think_harder.py` — `_should_think_harder` (:80), `_build_think_harder_config` (:130). It already implements per-role ROI tracking (`_expected_think_harder_roi`, :29) and an effort ladder ("high ROI → larger token budget + **CoT prefix**", :134). **The scaffold-then-nothink composite is naturally one more rung on this effort axis** (nothink → think-budget → scaffold-then-nothink → ownthink → escalate). Attaching here reuses the ROI accounting instead of building a parallel one.
- Beneficiary no-think path: `enable_thinking` is applied in the backends — `src/backends/llama_server.py`, `src/chat_completions_roles.py`, `src/registry/registry_loader.py`. Assistant-prefix / context-advisory injection modes are native to `llama-server` (`continue_final_message`), per the study.
- **OPEN QUESTION.** There is no existing two-stage/"sidecar" composite executor in `src/`. The grep for `continue_final_message|prefill_assistant|scaffold|sidecar|two_stage` hit only tangential files (features, draft_cache, placement_policy). **The composite executor (call GPU reasoner → inject → call beneficiary nothink, as one timed request) does not exist yet and must be built** (Task a). Verify against `src/api/routes/chat_pipeline/` before choosing the attach point.

##### 3.6 GPU-reasoner hosting (Qwable on MI210) — VERIFIED
- MI210 HIP `llama-server` binary **exists**: `/mnt/raid0/llm/llama.cpp-mi210-hip/build-hip/bin/llama-server`.
- Qwable weights **staged**: `/mnt/raid0/llm/models/Qwable-v1-GGUF/Qwable-v1.IQ4_XS.gguf` (17.6 GB) and `Qwable-v1.Q8_0.gguf` (34.4 GB).
- **Quiet-host server/chat evidence added 2026-07-17**: `epyc-inference-research/data/qwable_reasoning_economics/qwable_quality_quiet_20260717T0645Z/` confirms bounded runner cleanup and sequential MI210 arms. IQ4 standalone returned valid fenced JSON at **99.27 t/s**, Q8 standalone returned valid fenced JSON at **103.04 t/s**, strict IQ4 prompt-only JSON returned exact JSON at **99.44 t/s**, and CPU IQ4 baseline returned strict JSON at **13.82 t/s**. Scaffold/selector stubs were parseable but semantically placeholder/arbitrary, so they are **not** deployment evidence.
- **Schema-mode acceptance closed for the harness boundary 2026-07-17**: after fixing `qwable_reasoning_economics_runner.py` so execute mode sends the planned payload, `epyc-inference-research/data/qwable_reasoning_economics/qwable_schema_fixed_quiet_20260717T0718Z/` returned exact strict JSON under top-level `json_schema` at **64.55 t/s**. This closes bounded schema acceptance, not task-quality acceptance.
- **Expanded standalone-routing quality gate closed 2026-07-17**: `epyc-inference-research/data/qwable_reasoning_economics/qwable_task_quality_iq4_plain_expanded_final_20260717T184136Z/` passed `18/18` on MI210 plain at **106.65 t/s**; `qwable_task_quality_iq4_ngram_expanded_final_20260717T184106Z/` passed `18/18` on MI210 `ngram-mod` at **106.66 t/s**; `qwable_task_quality_iq4_cpu_expanded_final_20260717T184207Z/` passed `18/18` on CPU plain at **15.96 t/s**. Treat plain reasoning-off IQ4_XS as the preferred standalone route; ngram is safe but neutral on this slice.
- **CPU standalone verifier artifact checked 2026-07-19**: `epyc-inference-research/data/qwable_reasoning_economics/qwable_cpu_verifier_standalone_20260719T021216Z/summary.compact.json` reports execute `exit_code=0`, `cpu_iq4_baseline` and `verifier_selector_stub` both `status=ok` on `--device none -ngl 0`, decode `13.9607/14.0744 t/s`, `finish_reason=stop`, and post-run ROCm `No KFD PIDs currently running`. The compact artifact has since been tracked in `epyc-inference-research`; raw run logs remain research scratch unless explicitly retained.
- **The GPU reasoner is NOT in `orchestration/model_registry.yaml`** — the only `device:` entry is `device: cpu` (:235); no mi210/gpu/sidecar role. In the study the MI210 server was launched ad-hoc (:8801/:8802).
- **No launcher script exists** for the MI210 reasoner (find over `epyc-orchestrator/scripts` + `epyc-inference-research/scripts` for `*mi210*` / `*hip*server*` returned nothing).
- **Managed-service template (the pattern to copy):** `scripts/server/orchestrator_stack.py` `start_whisper()` (:1836) and `start_handoff_dashboard()` (:1889) — both are non-CPU-model stack-managed services; whisper reuses a launcher script from another repo (`:1846`) and health-probes a port. A `start_scaffold_reasoner()` following this shape (launch MI210 `llama-server`, health-probe, register `ProcessInfo`) is the concrete hosting task.
- **Cross-cutting:** MI210 residency contends with any other GPU role (`fable5-window2-findings-05b` owns the residency budget / Gate R). Co-residency numbers from the study: Qwable-IQ4 (17.6) + qwen35 beneficiary (35.2) = 53 GB fits 64; Qwable-Q8 (34.4) + qwen35 (35.2) = 70 GB does **not** — Q8 co-resides only with the gemma beneficiary or runs sequentially.

---

#### 4. Prioritized task list (dependency-ordered)

Each task = concrete file(s) + acceptance check. Flip `- [ ]` → `- [x] … ✅ YYYY-MM-DD` on completion (checkbox discipline, CLAUDE.md).

##### Phase 0 — Coordinate & host
- [ ] **T0.1 — Confirm AutoPilot is stopped before touching `scripts/autopilot/*` or the registry.** *(Precondition restated 2026-08-11 by `mainC`: this read "coordinate with the live autopilot agent", and there is no such agent — AutoPilot is intentionally stopped and has been since its last run, so the step could never be satisfied as written. Verify the daemon is down directly, e.g. no `autopilot.py` process and no journal activity, rather than coordinating with anyone.)* Get operator approval for the capability-registry row (CLAUDE.md: no registry changes via sub-agents without explicit operator request). *Accept:* written go-ahead recorded here.
  - **2026-11-09 correction (RTG-02 audit):** the "stopped since 2026-07-27" date above is wrong. The true last run is **2026-08-09T19:29Z (trial 1503**; 1504 numeric_swarm skipped, 1505 "(killed)"). Journal shards: `orchestration/autopilot_journal.jsonl` (trials 0-999, frozen 2026-06-27) and `orchestration/autopilot_journal_1.jsonl` (trials 1000-1505). Proof of stopped remains a direct process/journal check, not coordination.
- [x] **T0.1a — Close bounded Qwable strict-output/schema harness evidence.** Quiet-host runner evidence landed for IQ4/Q8 standalone format, strict IQ4 prompt JSON, CPU baseline, and top-level `json_schema`; scaffold/selector stubs remain non-deployable. ✅ 2026-07-17
- [x] **T0.1b — Close first Qwable IQ4_XS vs Q8_0 task-quality slice.** Bounded server/chat runner passed `6/6` on MI210 for IQ4_XS (`112.15 t/s`) and Q8_0 (`113.62 t/s`), and `6/6` on CPU for IQ4_XS (`17.11 t/s`) and Q8_0 (`13.66 t/s`); no Q8-only quality advantage in the small deterministic slice. ✅ 2026-07-17
- [x] **T0.1c — Close expanded Qwable IQ4_XS standalone-routing quality gate.** Calibrated `default+expanded` suite passed `18/18` on MI210 plain (`106.65 t/s`), MI210 `ngram-mod` (`106.66 t/s`, neutral), and CPU plain (`15.96 t/s`). Research routing now prefers plain reasoning-off IQ4_XS standalone; scaffold remains beneficiary-must-answer fallback. ✅ 2026-07-17
- [x] **T0.1d — Check CPU standalone verifier artifact.** Artifact `qwable_cpu_verifier_standalone_20260719T021216Z` is execution-clean (`exit_code=0`), CPU-only (`--device none -ngl 0`), cleanup-clean (`No KFD PIDs currently running`), and records strict/fenced JSON responses for the baseline and verifier-selector stub arms. The compact artifact is tracked; raw run logs remain scratch unless explicitly retained. ✅ 2026-07-19
- [ ] **T0.2 — Stand up the GPU reasoner as a stack-managed service.** Add `start_scaffold_reasoner()` to `scripts/server/orchestrator_stack.py` mirroring `start_whisper()` (:1836): launch `/mnt/raid0/llm/llama.cpp-mi210-hip/build-hip/bin/llama-server` with `Qwable-v1.IQ4_XS.gguf`, pick a stable port, health-probe. Add a `scaffold_reasoner` entry to `orchestration/model_registry.yaml` with `device: gpu`. *Accept:* `orchestrator_stack.py status` shows the reasoner healthy; a manual `/v1/chat/completions` to its port returns a `<think>` block. *(No autonomous llama-bench — speed characterization needs a per-run go-ahead, `feedback_speed_verify_via_llama_bench`.)*

##### Phase 1 — Composite route (the mechanism)
- [ ] **T1.1 — Build the scaffold-then-nothink composite executor.** New path (verify attach point in `src/api/routes/chat_pipeline/`): call `scaffold_reasoner` → inject its output (assistant-prefix `continue_final_message` **or** system/context advisory — the study's mode answer is distribution-conditional, so make it a parameter) → call the beneficiary with `enable_thinking=false` (via the backend path in `src/backends/llama_server.py`). Issue as **one timed request** so `elapsed_s` (`eval_tower.py:1063`) captures both stages. *Accept:* one composite request returns the beneficiary's answer with the scaffold visible in the trace; beneficiary decode-token count is in the ~100–175 band the study observed.
- **[declined: ws58 2026-11-03 content-review: merged into T1.1]** **T1.2 — Attach it to the reasoning-effort ladder.** Wire the composite as one rung in `src/graph/think_harder.py` (`_build_think_harder_config`, :130) rather than a parallel mechanism, so per-role ROI tracking (`_expected_think_harder_roi`, :29) already covers it. *Accept:* `think_harder` can select `scaffold_then_nothink` as an effort level for an eligible role.

##### Phase 2 — Blended cost accounting (the objective)
- [ ] **T2.1 — Decide + implement the blended-cost representation.** Resolve the §3.1/§3.2 split: (i) ensure the composite request's total wall-clock (GPU gen + CPU prefill + CPU decode) lands in the `speed` axis via the single-timed-request design (T1.1); AND (ii) extend the episodic `cost_metrics` contract in `orchestration/repl_memory/q_reward.py` to carry a **second-device term** (GPU `generation_ms`) so `compute_reward`'s `cost_ratio` reflects blended cost, not just the beneficiary's single-role wall-clock. Options: a composite pseudo-role with a blended `baseline_tps`, or an additive GPU-cost term. *Accept:* a scaffold trial and an ownthink trial on the same task produce `cost_ratio`/`speed` values whose ordering matches the study's blended-cost inequality (scaffold cheaper in the over-reason regime).
- **[declined: ws58 2026-11-03 content-review: merged into T2.1]** **T2.2 — Verify the Pareto `cost` axis is not misused.** Confirm the scaffold does **not** get mis-scored on the memory `cost_tier` axis (`eval_tower.py:1383-1385`) as if it were free — the GPU residency is a real capacity cost. Decide whether the reasoner's residency should raise the composite route's `cost_tier`. *Accept:* documented decision + `cost_tier` assignment for the composite route.

##### Phase 3 — Episodic gating (learn when)
- [ ] **T3.1 — Add the scaffold-eligibility signal to episodic memory.** Introduce a `sub_decision`/`action_type` value (e.g. `scaffold_eligible`) in `src/classifiers/subdecision_taxonomy.py` + `orchestration/repl_memory/episodic_store.py` and a `retrieve_for_scaffold_eligibility` (or reuse `retrieve_for_routing`, `retriever.py:160`) keyed on task embedding × `difficulty_band` (`src/classifiers/difficulty_signal.py`). *Accept:* store/retrieve round-trips a scaffold Q-value for a (task-class, difficulty) cell; unit test alongside `tests/unit/test_episodic_store.py`.
- **[declined: ws58 2026-11-03 content-review: merged into T3.1]** **T3.2 — Reward wiring so Q-values learn the gate.** Ensure the composite route's outcome feeds `q_reward.compute_reward` (T2.1) so `update_q_value` (`episodic_store.py:618`) reinforces "apply scaffold" only where it wins (correct **and** blended-cost-cheaper). *Accept:* replay of a synthetic weak-and-overthinking trace drives the scaffold Q-value up; a saturated-task trace drives it down (matches the headroom-conditional finding).

##### Phase 4 — Offline replay + registry
- [ ] **T4.1 — Offline replay to learn the gating policy from existing traces.** Use the read-only journal replay path (`scripts/autopilot/journal_snapshot_replay.py` → `src/autopilot_core/journal_snapshot_replay.py`, `build_snapshot_replay_diagnostic`) and/or `scripts/autopilot/core_v2_select.py` to replay historical task traces and estimate, per task-class, where nothink fails + the beneficiary over-reasons (the eligible regime) — **without** live daemon perturbation. *Accept:* a per-task-class eligibility table with support counts, written to a report under `orchestration/reports/`.
- **[declined: ws58 2026-11-03 content-review: merged into T4.1]** **T4.2 — Register the lever (operator-gated).** After T0.1 approval, add a `scaffold_then_nothink` row to `orchestration/capability_registry.yaml` (kind per the §3.4 fork decision; `promotion_state: placeholder`; `kill_condition` written; roles = the eligible beneficiaries). Validate with `scripts/registry/compile_capability_registry.py` + `tests/unit/test_capability_registry.py`. *Accept:* loader accepts the row; row stays `placeholder`/gated until the measurement gate (§8) passes.

##### Phase 5 — Measurement gate + rollout
- [ ] **T5.1 — Codified measurement protocol for the deploy gate** (see §8). *Accept:* protocol-id assigned; quality-parity + blended-cost recipe written, operator-approved.
- **[declined: ws58 2026-11-03 content-review: merged into T5.1]** **T5.2 — Canary / shadow rollout.** Shadowed trials on the eligible task-classes only; verify no regression on the saturated/nothink-works classes; then promote the registry row past `placeholder` per W4 preconditions. *Accept:* canary meets the §8 gate; W4 (1) applicator wired, (2) range validated, (3) kill_condition, (4) shadowed trial attested — all satisfied.

---

#### 5. Dependency graph

```
T0.1 (coordinate/approve) ─┬─> T0.2 (host GPU reasoner)
                           │        │
                           │        v
                           │      T1.1 (composite executor) ──> T1.2 (effort ladder)
                           │                 │
                           │                 v
                           │      T2.1 (blended cost) ──> T2.2 (cost_tier decision)
                           │                 │
                           │                 v
                           │      T3.1 (episodic signal) ──> T3.2 (reward wiring)
                           │                 │
                           │                 v
                           │      T4.1 (offline replay) 
                           └─────> T4.2 (register lever, needs T0.1 approval + T2/T3)
                                             │
                                             v
                                   T5.1 (measurement protocol) ──> T5.2 (canary/rollout)
```
- **Blocking chain:** T0.2 → T1.1 → {T2.1, T3.1} → T4 → T5. T1.1 is the linchpin (nothing downstream measures without the composite request).
- T4.1 (offline replay) can run in parallel once T3.1's signal shape is fixed; it does **not** need the live daemon.
- T4.2 and T5.2 are **operator-gated** and must not proceed while the parallel autopilot agent holds the daemon.

---

#### 6. Cross-cutting concerns

- **GPU-reasoner residency/contention.** The MI210 is a shared, budgeted resource; `fable5-window2-findings-02-heterogeneous-gpu.md` owns the residency plan (Gate R) *(corrected 2026-08-18 from findings-05b, now archived)*. Adding a resident reasoner competes with any other GPU role. Respect the co-residency arithmetic (§3.6): IQ4_XS co-resides with a qwen35 beneficiary; Q8 does not.
- **Quality-parity gating (no regression where nothink already works).** The headroom-conditional finding is the whole point: the lever must be **inert on saturated/strong-nothink task-classes** (gemma-31B 8=8). The gate (§8) MUST include a no-regression check on those classes, not just a win check on the weak ones (`feedback_per_suite_gate_resolution_artifact`, `feedback_eval_saturation_masks_model_gap`).
- **Measurement-trust boundary.** The keep/deploy decision needs a **protocol-id**, not the study's observations (§8). MEASUREMENT.md and the eval tower are human-amendment-only.
- **Two distinct cost surfaces (do not conflate).** Pareto `cost` = memory `cost_tier` (§3.1); episodic reward `cost_ratio` = per-role wall-clock (§3.2); blended GPU+CPU wall-clock naturally lands on `speed` and on an *extended* `cost_metrics`. Getting this wrong makes the scaffold look free (it isn't — GPU residency + prefill tax are real).
- **Interaction with existing spec-dec/MTP routing.** The scaffold is orthogonal to MTP/NEXTN (text-level transfer, no vocab/KV sharing — study §"MTP is irrelevant"). It sits on the *reasoning-effort* axis (`think_harder`), not the draft/spec-dec axis. Verify the two levers compose (a scaffolded nothink request on an MTP-enabled beneficiary) rather than fight.
- **Live-parallel-agent hazard (autopilot).** Restated: no `scripts/autopilot/*` edits, no daemon restart, no registry/index change, while the owning agent is active. Design now; land under coordination.
- **Verifier/selector is out of scope.** Marginal on this stack (systematic not stochastic errors). Do not bundle it into this deployment.

---

#### 7. Measurement / deploy gate

Per `/workspace/CLAUDE.md` (Measurement & Claims) and `MEASUREMENT.md`:

- **All study numbers in §2 are OBSERVATIONS** (single-sample, GPU-only, seed 42) — usable for hypotheses, **never** to gate keep/deploy/promote. A decision-gating claim = `(metric, protocol-id, n/reps, date, host-attestation ref)`.
- **Quality-parity gate → P-QUAL-T1** (`MEASUREMENT.md:25-35`, the production autopilot trial-gate instrument card): **paired (same questions both arms), N ≥ 100/arm** for a production-role decision (the X-MAS lesson — a 20pp effect at N=25 collapsed to 4pp at N=100), every failure classified by reason, flag-state attestation in the run header. Arms: `nothink` vs `scaffold_then_nothink` vs `ownthink`, on **both** an eligible (weak-and-overthinking) and a saturated task-class.
- **Blended-cost / speed gate → P-BENCH-1/P-BENCH-2** (`MEASUREMENT.md:19-23`) via `bench_canonical.sh` / `canonical_recipe.py`, **operator-approved, never hand-typed**, with the composite request's GPU+CPU wall-clock captured end-to-end. Axis = `task_rate` (questions/eval-wall-hour) per findings-05.
- **Deploy rule:** promote the registry row past `placeholder` only when (a) P-QUAL-T1 shows quality-parity-or-better on the eligible class **and** no regression on the saturated class, (b) the blended-cost protocol shows a real wall-clock win in the eligible regime, and (c) W4 preconditions (`capability_registry.yaml:8-13`) are met. Journal rows carry `protocol_id`.

---

#### 8. Reporting instructions

- After each task: flip its `- [ ]` → `- [x] … ✅ YYYY-MM-DD` here; work discovered mid-flight gets its own `- [ ]` line. Prose-only status is invisible to the handoff dashboard (CLAUDE.md checkbox discipline).
- Log via `scripts/utils/agent_log.sh` (`agent_task_start`/`agent_task_end`); chronology to `progress/2026-07/`.
- Numbers stay **OBSERVATION** until run through the §7 codified recipes with operator approval; label them so in any update.
- The master-handoff-index pointer to this doc is added by the **main session**, not here (per task scope). Do not edit any index/master-index from this workstream.
- On promotion, fold the residency planning into `fable5-window2-findings-05b` (Gate R) rather than duplicating it.

---

#### 9. Key file locations (verified implementation targets)

| Concern | Path : symbol | Verified |
|---|---|---|
| 4D Pareto objective tuple | `scripts/autopilot/safety_gate.py:329` `objectives()` | ✅ |
| EvalResult fields / cost | `scripts/autopilot/safety_gate.py:230-234`; `eval_tower.py:1383-1385` (`cost=mean(cost_tier)/4`) | ✅ |
| Pareto archive | `scripts/autopilot/pareto_archive.py`; `src/autopilot_core/pareto_math.py` | ✅ |
| Request wall-clock (speed) | `scripts/autopilot/eval_tower.py:1063,1135` (`elapsed = time.time()-start`) | ✅ |
| Episodic reward / cost_ratio | `orchestration/repl_memory/q_reward.py:22,90-93` | ✅ |
| Reward config / QScorer | `orchestration/repl_memory/q_scorer.py:613,690` | ✅ |
| Episodic store | `orchestration/repl_memory/episodic_store.py:73,136,293,522,618` | ✅ |
| Episodic retrieval policy | `orchestration/repl_memory/retriever.py:74,160` | ✅ |
| Task-class taxonomy | `src/classifiers/subdecision_taxonomy.py`; `episodic_store.py:97` `sub_decision` | ✅ |
| Difficulty band | `src/classifiers/difficulty_signal.py` | ✅ |
| Capability registry (lever) | `orchestration/capability_registry.yaml` (`per_role_enable_thinking` :141); loader `src/registry/capability_registry.py:215` | ✅ |
| Planner reads registry | `scripts/autopilot/autopilot.py:54-56` | ✅ |
| Action handlers | `scripts/autopilot/actions.py:391,475,950,1020` | ✅ |
| Routing decision | `src/api/routes/chat_pipeline/routing_decision.py:64,152` | ✅ |
| Reasoning-effort ladder | `src/graph/think_harder.py:29,80,130` | ✅ |
| nothink / enable_thinking | `src/backends/llama_server.py`; `src/chat_completions_roles.py` | ✅ |
| Offline replay | `scripts/autopilot/journal_snapshot_replay.py`; `src/autopilot_core/journal_snapshot_replay.py`; `scripts/autopilot/core_v2_select.py` | ✅ |
| GPU reasoner binary | `/mnt/raid0/llm/llama.cpp-mi210-hip/build-hip/bin/llama-server` | ✅ |
| Qwable weights | `/mnt/raid0/llm/models/Qwable-v1-GGUF/{Qwable-v1.IQ4_XS.gguf, Qwable-v1.Q8_0.gguf}` | ✅ |
| Managed-service template | `scripts/server/orchestrator_stack.py:1836` `start_whisper()` | ✅ |
| Prod model registry | `orchestration/model_registry.yaml` (only `device: cpu` :235 — **no GPU role yet**) | ✅ |

##### Open questions (could not be verified — resolve during build, do not guess)
1. **Composite-route representation in the capability registry** — new `kind: route-composite` vs `prompt`-kind-with-two-stage-applicator (§3.4). Operator/daemon-owner decision.
2. **No existing two-stage/sidecar executor in `src/`** — the composite request path (§3.5) must be built; the exact attach point in `src/api/routes/chat_pipeline/` needs verification against the current pipeline.
3. **No MI210 reasoner launcher script exists** — must be written for T0.2 (whisper's launcher lives in `epyc-inference-research`; decide where the reasoner launcher lives).
4. **Blended `cost_metrics` extension** — whether to add a GPU `generation_ms` term to `q_reward.compute_reward` or model a composite pseudo-role with a blended `baseline_tps` (§3.2, T2.1).
5. **Injection mode** — assistant-prefix vs context-advisory is distribution-conditional in the study; make it a route parameter, characterize per task-class during T5.

## Track: autopilot-sequential-allocation
<!-- gate: RTG-02#autopilot-program, RTG-02#autopilot-dashboard-fidelity-audit-2026-07-22, RTG-02#autopilot-decision-plane-audit-2026-07-22, RTG-02#batched-edit-parallel-apply, RTG-02#bep-dcp-falsification-harness, RTG-02#evidence-plane-event-sourcing-and-narrative, RTG-02#evidence-plane-instrument-repair, RTG-02#evidence-plane-ledger-and-sequential-verdicts, RTG-02#loops-and-dashboards-audit-2026-07-05, RTG-02#objective-task-rate-goodput, RTG-02#orchestration-robustness-audit-2026-07-11, RTG-02#scaffold-autopilot-cost-lever-deployment -->

> Folded from `handoffs/active/autopilot-sequential-allocation.md` @ `e8deee0a4de8` on 2026-11-03 (BRF-T7-F12, route 1b, operator D1/D5; retired row EVL-04 → RTG-02). Body moved verbatim, headings demoted two levels to nest under this track; every open and closed box kept its text and ID.

### Autopilot Sequential Verdicts — the allocation rule, not the effect, was the binding constraint

> **Fold destination** (BRF-T1-F21, BRF-T1-1, route 1a, 2026-11-02): absorbs 1 handoff(s) as `## Track:` sections at the end of this file (`promptforge-mutation-safety-contract.md`). The body above the first track is the former `autopilot-sequential-allocation.md`.

**Status**: active — offline re-adjudication COMPLETE 2026-07-28 (zero inference). Two candidates sit
within ~10 trials of a confirm **inside `core_v1`** — but `core_v1` is closed and E8 is under a
fail-closed rebaseline hold, so SEQ-3 is gated on an operator era ruling (SEQ-3a) or a ~49-trial
clean re-run (SEQ-3b).
**Created**: 2026-07-28
**Priority**: HIGH — this determines whether the benchmark-Autopilot program was ever tested
**Categories**: benchmark_methodology, autonomous_research, routing_intelligence
**Parent index**: [research-evaluation-index.md](research-evaluation-index.md)
**Related**: [episodic-memory-integrity.md](memory-program.md) (separate store — the reseed
did not touch the journal)

#### The finding

Measured over **393 sequential trials / 141 candidates** in `orchestration/autopilot_journal*.jsonl`:

- **Median 1.0 trial per candidate** (mean 2.79, max 41). **90 of 141** candidate×era groups received
  exactly one trial.
- **0 of 121** refuted trials were killed by futility (`E <= futility_e = 0.05`). Every refutation
  came from the *budget* rule.
- The strongest candidate `70902e4b665474e7` trips `k>=8 and E<2.0` at k=8 with **E=1.68**, then
  climbs to **E_quality 11.55 by k=40 — while still labelled `refuted` the whole way.**

`confirm_e = 20.0` is the Ville bound for α=0.05 and is untouchable. **`budget = 8` and
`budget_min_e = 2.0` (`src/autopilot_core/sequential_verdict.py:44-57`) are a compute-allocation
heuristic with no bearing on anytime-validity.** Relaxing them is statistically free.

#### Re-adjudication result (2026-07-28, zero inference)

`scripts/analysis/readjudicate_sequential_candidates.py` re-folds the recorded per-trial `z` values
through the project's own `rebuild_candidate_view`, era-fenced by `core_id`, with `budget` and
`budget_min_e` relaxed and every other policy parameter untouched.

```
candidates CONFIRMED under the relaxed budget:              0
recorded 'refuted' that are NOT refuted once budget drops:  9
candidates still RISING when the run ended:                58

candidate           core      k          E     grow   need  recorded
70902e4b665474e7    core_v1  40    11.5507   1.0631      9  refuted
dd793a6ee43ce718    core_v1  24     8.7048   1.0943     10  refuted
85c3dcf25823c537    core_v1  15     2.7448   1.0696     30  refuted
db866b4a9fa37e03    core_v1  10     1.5856   1.0472     55  refuted
45129cc6ee5bac29    core_v1  12     1.5609   1.0378     69  refuted
```

**Verdict: the benchmark-Autopilot hypothesis is NOT falsified — it was never funded to a verdict.**
No candidate crosses `confirm_e` on evidence already purchased, but two are close and were still
rising steeply when cut.

**Caveat, stated plainly**: `need` is an *extrapolation* from the observed per-trial growth factor. It
assumes the effect persists at the same rate, which the data cannot guarantee — an e-process can
plateau or reverse. Treat it as a cost estimate for the next experiment, never as a predicted
outcome.

#### Two defects in the verdict machinery

- [x] **SEQ-A — DISSOLVED, not fixed** ✅ 2026-08-12 (`mainB` subagent). Closing the parent to match its
      children: SEQ-A0 landed the neutral mechanism (`43108014`) and SEQ-A1 is VOID, so this box was the
      last thing still presenting a refuted premise as open work. Re-derived rather than inherited:
      `f2ad030e` is an ancestor of orchestrator HEAD, its axis attribution is live in
      `scripts/analysis/readjudicate_sequential_candidates.py`, and `pytest -k "readjudicate or
      sequential_verdict"` → **54 passed, 5 skipped**. **Residual defect found and fixed while
      verifying**: that script's MODULE DOCSTRING still asserted *"56 of 393 … The label is STICKY"* as
      fact — `f2ad030e` corrected the code and the inline comment and left the docstring, which is the
      first thing a reader sees and the source every later citation of "56 of 393" came from. Retracted
      in place (not deleted, so the still-true `70902e4b665474e7` bullet above it cannot be re-read as
      evidence for staleness). Live question remains **SEQ-B1**, with the operator.

      **Original filing preserved verbatim below — read it only together with the ⚠ premise correction
      that follows it; the two are one record and the claim does not survive without the correction.**

      **SEQ-A (as originally filed) — the `refuted` label is STICKY.** `state_name()`
      (`sequential_verdict.py:131-138`) is a pure function of current state, so a candidate that
      outgrows the kill condition should read `accumulating` again. It does not: **56 of 393 trials
      carry `state="refuted"` while `E >= budget_min_e` and `k >= budget`** — the persisted label
      contradicts what the policy's own function returns for that very trial. `70902e4b665474e7`
      crosses E=2.0 at k=10 and stays labelled refuted to k=40 at E=11.55.

      **What it actually costs, measured 2026-07-28**: the label does NOT stop allocation — that
      candidate kept receiving trials to k=40. What `seq_refuted` does is exclude a candidate from
      **promotion and positive strategy distillation** (`learning_exclusions.py:111-119`). So **3
      candidates are permanently excluded by a condition they no longer meet**:

      | candidate | k | E_quality |
      |---|---|---|
      | `70902e4b665474e7` | 40 | **11.5507** |
      | `dd793a6ee43ce718` | 24 | **8.7048** |
      | `85c3dcf25823c537` | 15 | **2.7448** |

      Reported by `readjudicate_sequential_candidates.py` under *SEQ-A: STICKY REFUTED LABELS*.

      > ### ⚠ SEQ-A's PREMISE IS FALSE — measured, not argued (2026-08-11, `mainB`)
      >
      > **There is no stale label. There never was.** The heading above, the "56 of 393", and the
      > 3-candidate table are all artifacts of the detector that produced them.
      >
      > `readjudicate_sequential_candidates.py:203` tested `state == "refuted" AND E_quality >=
      > budget_min_e` — a **JOINT** verdict against a **SINGLE** axis. `safety_gate.py:1529` stamps
      > `state` refuted when **either** axis refutes (`q_name == REFUTED or rate_name == REFUTED`)
      > and **recomputes it on every trial**. So a healthy quality axis beside a refuted RATE axis
      > read as a label that had failed to update.
      >
      > It manufactured the entire population: per SEQ-B below, `E_rate_noninf` never exceeds 2.0
      > anywhere in the corpus (max **1.1100**) against `budget_min_e = 2.0`, so essentially every
      > candidate's rate axis refutes once `k >= budget`.
      >
      > Detector fixed at orchestrator **`f2ad030e`** (reporting only, zero semantic change). It now
      > attributes each `refuted` label to an axis. Measured against the real journal:
      >
      > | bucket | n |
      > |---|---|
      > | refuted on the QUALITY axis | 6 |
      > | refuted on the RATE axis ONLY (quality healthy) | **3** |
      > | **UNEXPLAINED — joint refuted, NEITHER axis** | **0** |
      >
      > The 3 are exactly `70902e4b665474e7`, `dd793a6ee43ce718`, `85c3dcf25823c537`. They are
      > **correctly labelled** by the joint rule. The empty third bucket is the finding: it is the
      > only thing that would be a genuinely stale label, and it does not exist.
      >
      > **Consequence for SEQ-A1 (below): the question it poses is not real.** Nothing needs
      > recomputing. The live question is **SEQ-B1** — joint gate vs quality-primary — because those
      > 3 candidates are precisely the case SEQ-B1 names: *"a candidate that buys quality with
      > throughput can never be promoted — which may be exactly what you want."* `coordinator-agent`
      > withdrew a Horn A instruction on this basis and is taking SEQ-B1 to the operator.
  - [x] **SEQ-A0 — the mechanism, built NEUTRAL so SEQ-A1 is a one-line switch** ✅ 2026-08-11
        (`mainB`, orchestrator `43108014`). `SequentialPolicy.sticky_refuted`, **default `False`** —
        seq-v1 semantics reproduced byte-for-byte, the 3 candidates below still flip exactly as
        before, **75 passed** across the sequential-verdict consumer set. **The set, named so the
        number is checkable** (`auditor` 2026-08-11: the original citation said "every
        sequential-verdict consumer", which is not reconstructable — their two reasonable guesses
        gave 41 and 131):
        `tests/unit/` × {`test_restart_readiness_report.py`, `test_seq_rate_axis_paired_measurement.py`,
        `test_seq_readiness_report.py`, `test_sequential_verdict.py`,
        `test_sequential_verdict_sticky_refuted.py`} — 5 files, selected by
        `grep -rln 'sequential_verdict\|EProcessState\|seq_readiness\|review_ledger' tests/unit/`.
        Re-run 2026-08-11 after the note: 75 passed, unchanged. Plus `EProcessState
        .first_refuted_k`, recorded unconditionally as the process folds forward: **observing that a
        stop happened is free, and is not the same as deciding it is permanent** — capturing it now
        is what lets SEQ-A1 be settled from data rather than by re-running `core_v1`, which is over
        (era E8). Persisted trial state untouched; the field defaults to `None` so a state rebuilt
        from an older record behaves identically (pinned by test).
        **Numbers re-derived, not inherited**: against `readjudicate_sequential_20260728.json`,
        exactly 3 candidates flip `refuted`→`accumulating` — `70902e4b665474e7` (k=40),
        `dd793a6ee43ce718` (k=24), `85c3dcf25823c537` (k=15). Confirms the figures above.
        **Deliberately takes no side.** A lane brief phrased SEQ-A as "the function silently
        un-refutes — make it sticky", i.e. the inverse of this handoff's framing. Both readings are
        true: the FUNCTION is non-sticky (`state_name()` has no memory), the PERSISTED LABEL reads
        `refuted` where the function would not. So "make it sticky" is not a bug fix — it is SEQ-A1
        horn 2, and deciding it silently would settle a human-amendment-only question on a phrasing.
        **CORRECTION 2026-08-11 (`mainB`), to my own sentence above:** I wrote that the persisted
        label is "sticky (never recomputed)". **That is false and I checked it only later.** It is
        recomputed on EVERY trial — `safety_gate.py:1529` stamps it from a JOINT rule
        (`q_name == REFUTED or rate_name == REFUTED`). The divergence is joint-vs-quality-only, not
        staleness. See the SEQ-A premise correction under SEQ-A1 below; it changes what SEQ-A1 is.
  - [x] **SEQ-A1 — VOID, superseded by the premise correction above** ✅ 2026-08-11 (`mainB`).
        Not "decided" — **dissolved**. Horn 1 ("recompute the verdict label per trial") is already
        what the code does; horn 2 ("keep stickiness") preserves a stickiness that does not exist.
        Recomputing from quality-only `state_name()` would not restore pure-function semantics, it
        would **drop the rate axis out of the verdict** — which is SEQ-B1, a different
        human-amendment-only question. Routed there; do not re-open this row.
        ~~SEQ-A1 — **OPERATOR DECISION**: recompute the verdict label per trial from `state_name()`
        (restoring the policy's own pure-function semantics), or keep stickiness and document it as
        "a stop decision is final". Either is defensible — a stopped e-process arguably *should*
        stay stopped — but the current state is neither: the label is sticky while allocation is
        not, so candidates keep burning trials whose evidence is then discarded. This changes which
        candidates are promotable, so it is **human-amendment-only** per MEASUREMENT.md.~~
- **[declined: ws58 2026-11-03 content-review: a corrected explanatory note; the decision is SEQ-B1]** **SEQ-B — the promotion gate is unreachable, but NOT because anything is broken.**
      **CORRECTED 2026-07-28** — I first wrote that "the rate e-process is frozen". **It is not.**
      Measured: `E_rate_noninf` takes **82 distinct values** (min 0.5213, median 0.9100, max 1.1100)
      and `z_rate` takes 179 distinct values with median **−0.8979** and only **7.9% positive**. The
      axis computes fine; it is reporting that candidates **genuinely do not improve throughput**.

      The gate is `combined_E = min(E_quality, E_rate_noninf)` (`autopilot.py:1953-1966`,
      `binding_joint` mode) against `required_E = 100.0`. For the top candidate that is
      `min(11.55, 0.556) = 0.556` — real quality evidence entirely masked by a real negative rate
      result. **18 of 393** trials ever exceed `E_rate 1.0`; **0** ever exceed 2.0.

      So this is a **policy question, not a defect**: do you want a JOINT gate (quality AND
      throughput, current `binding_joint`) or quality-primary with rate advisory? The advisory mode
      already exists — `quality_only_rate_advisory` — and was exercised in 35 trials under an
      operator bridge (`rate_axis_mode = operator_p0_2_rate_alpha_bridge`).
  - [ ] SEQ-B1 — **OPERATOR DECISION**: keep the joint gate, or move the rate axis to advisory. This
    - **2026-11-09 era rewrite (RTG-02):** SEQ-B1 numbers came from E8/core_v1 (E16..E20 since, rate axis carries wall-clock since E18). Re-pose the joint-gate question with fresh numbers under the new era; the decision stays human-amendment-only. The relaunch will use a brand-new instrument era, set by an operator ratify script because `orchestration/instrument_eras.yaml` and `orchestration/autopilot_baseline.yaml` are human-only (agents never edit them). E8-era premises here (core_v1 trials, E8 numbers, "E_quality 11.55 vs 20") are historical and must be re-derived under the new era before this box is acted on; the box stays open only for that reason.
        changes what counts as a promotion, so it is a measurement-trust-boundary change and is
        **human-amendment-only** per MEASUREMENT.md. Note that under a joint gate, a candidate that
        buys quality with throughput can never be promoted — which may be exactly what you want.

#### Tasks

- [x] SEQ-1 — Verify the k=8/allocation claims directly against the journal. ✅ 2026-07-28
- [x] SEQ-2 — Build and run the offline re-adjudication (zero inference). ✅ 2026-07-28
      Report: `orchestration/reports/readjudicate_sequential_20260728.json`
- [ ] SEQ-3 — **Resume the top candidate to a verdict. GATED — read the era problem first.**
  - **2026-11-09 era rewrite (RTG-02):** SEQ-3 premise is dead: its 393 trials are core_v1/E8 and eras run through E20 (`instrument_eras.yaml:571`); the "~9 more trials" figure does not transfer. The relaunch will use a brand-new instrument era, set by an operator ratify script because `orchestration/instrument_eras.yaml` and `orchestration/autopilot_baseline.yaml` are human-only (agents never edit them). E8-era premises here (core_v1 trials, E8 numbers, "E_quality 11.55 vs 20") are historical and must be re-derived under the new era before this box is acted on; the box stays open only for that reason.

    **The "~9 more trials" figure is only valid inside `core_v1`, and `core_v1` is over.**
    All 393 sequential trials carry `core_id: core_v1`, spanning 2026-06-18 → 2026-07-16. The
    current era is **E8** (`instrument_eras.yaml:166`, from 2026-07-25T18:38:43Z, scope
    `eval_quality`), which explicitly opens *"a fail-closed E8 AutoPilot rebaseline hold: pre-v8/E7
    baseline and MAD observations are historical priors until an operator-ratified E8
    quality-baseline reseed writes fresh values and windows."* `core_v1` has no era row at all —
    the only `core_id` the registry declares is `core_v2` (E4).

    Folding E8-instrument z's into a `core_v1` e-process would mix non-comparable evidence, which is
    the exact defect the era registry exists to prevent. So there are two honest paths:

  - [x] ~~SEQ-3a — **Bridge (cheap, needs an operator ruling).** If an operator judges the E8~~ (closed 2026-10-29 audit: SUPERSEDED → ruling_op19_e8_chain_20260827.json / 1ee8bd7cc: E8 chain retired, eval_quality left E8 on 2026-08-05 (now E16) so an E8-vs-core_v1 comparability era row is moot)
        instrument comparable to `core_v1` for this candidate's axis and records an era row saying
        so, then ~9-10 further trials (≈2.6 eval-hours at the historical ~935 s/trial) settle it.
        **This is a measurement-trust-boundary decision and is human-amendment-only** per
        MEASUREMENT.md — an agent must not make it.
  - **[declined: ws58 2026-11-03 content-review: era-stale (E8; the reward carries the wall-clock axis since E18)]** SEQ-3b — **Re-run clean under E8 (expensive, no ruling needed).** Restart the candidate at
        k=0 under the E8 instrument. At the observed growth of 1.0631×/trial it needs **~49 trials**
        to reach `confirm_e=20.0` — roughly **12.7 eval-hours**, not 2.6. Also gated on the E8
        quality-baseline reseed completing and being operator-ratified, since the hold is
        fail-closed.

    **Candidate identity for whoever runs it**: `70902e4b665474e7`, species `seeder`, tier 1,
    `core_id core_v1`, last trial `1067` (2026-07-03, git tag `autopilot/trial-1067`), config_diff
    `{n_questions: 18 → 16, suites: [...] → null}`, hypothesis "Seed 16 questions across all",
    last state `k=40 E_quality=11.5507 lambda=0.5 r_eff=11`.
- [x] **SEQ-B ROOT-CAUSED AND FIXED** ✅ 2026-08-04 (epyc-orchestrator `f1a6b23b`). **The prior
      SEQ-B text in this handoff was WRONG** — it read "the axis computes fine; it is reporting that
      candidates genuinely do not improve throughput". It did not compute fine, and the same
      candidates measure **+13% to +27% faster** once the measurement is paired.

      Root cause: a mis-paired measurement, not a mis-specified alternative.
      `EvalTower._aggregate_decision_partitions` returns an `EvalResult` whose `n_questions` counts
      only the DECISION partition (55) while `eval_wall_s` is the FULL batch's wall clock (65), and
      the incumbent comparator counted the full 65. Candidate rate = 55/wall vs incumbent 65/wall
      **on the same trial** — so an unchanged config measured 0.846x its own throughput, giving
      `z_rate = -0.208` every trial. `next_lambda` clipped the negative running mean to 0, the
      wealth factor became exactly 1.0, and it froze. Evidence: `E_rate_noninf == 0.9100` in
      **192 of 396 rows** — precisely `1 x (1 + 0.1 x -0.9)`, one update then frozen; `z_rate` at
      the clip floor in **199/396 (50%)**.

      Second defect, the same absence-vs-zero class as the reliability floor and
      `throughput_unmeasured`: `task_rate_qph_from` returns `0.0` as its "unavailable" sentinel
      while the guard tested `is not None`, so an UNMEASURABLE trial was consumed as a MEASURED
      zero questions/hour. Now returns `None` and the axis is skipped.

      Third: `rate_noninferiority_z` clipped `y` two-sided, which truncates the null-side lower
      tail, lifts `E[z]` above 0 under H0, and makes the wealth a **submartingale** — Ville does not
      apply. Fixed by lowering the clip to `-1.0` (never binds, since `y >= -1` identically).

      Replay over all 396: `z_rate` at clip floor 50% -> 0%, positive evidence 8% -> 69%, three
      candidates cross `E_rate = 20`, one reaches 222, **zero false confirms**. NO THRESHOLD CHANGED.

- [ ] **Decide whether to re-arm the sequential gate.** Currently `AUTOPILOT_SEQ_VERDICT=0`
  - **2026-11-09 era rewrite (RTG-02):** Daemon env today is `AUTOPILOT_SEQ_VERDICT=0`, `AUTOPILOT_SEQ_P0_2_BRIDGE=1` (`start_authority_daemon.py:96-97`); the "max E_quality 11.55 vs 20" evidence is E8-era. Re-evaluate re-arming only after the first new-era trials. The relaunch will use a brand-new instrument era, set by an operator ratify script because `orchestration/instrument_eras.yaml` and `orchestration/autopilot_baseline.yaml` are human-only (agents never edit them). E8-era premises here (core_v1 trials, E8 numbers, "E_quality 11.55 vs 20") are historical and must be re-derived under the new era before this box is acted on; the box stays open only for that reason.
      (operator unblock, 2026-08-04) because an unreachable gate meant AutoPilot could not ratchet at
      all. Re-arming changes what counts as a promotion -> human-amendment-only. **On current
      evidence re-arming would RE-BLOCK the ratchet rather than restore it**: post-fix the binding
      constraint is the QUALITY axis (max `E_quality` 11.55 vs bar 20). Coupled switch:
      `AUTOPILOT_SEQ_P0_2_BRIDGE` `1 -> 0` makes the rate axis binding again (advisory today).

- **[declined: ws58 2026-11-03 content-review: merged into SEQ-4 (the allocation replay answers it)]** **The real reason `E_quality` never cleared 20 is trial starvation, not calibration.**
      Measured over the journal: **89 of 141 candidates got exactly ONE trial** (median k = 1). An
      e-process accumulates multiplicatively; at k=1 it cannot clear any bar. The two leading
      candidates were close — `70902e4b665474e7` at k=40 reached E=11.55, **~9 trials short** at its
      observed growth, and `dd793a6ee43ce718` at k=24 reached 8.71, ~10 short. This is the same
      finding as the 2026-07-28 re-adjudication (`budget=8` / `budget_min_e=2.0` killed 121 of 121
      refutations, a compute heuristic with no bearing on anytime-validity). **Fix the allocation
      before concluding anything about `confirm_e = 20`.**

- [x] ✅ 2026-11-01 — APP `b336f50b7efb77644a492c707d4ffc503d69d744` plus `ddb6391714483740ac1c87e6fca7d3b797ef491c`; [49 focused controls and baseline proof](https://github.com/pestopoppa/epyc-orchestrator/blob/f55ad5d9cd3ce708b1704ba874d0605473feebeb/artifacts/engineering/seq-rate-era-fence-20261101/README.md). [belief: cc] **Rate-axis comparator has no era fence of its own.** The incumbent pool is the 120 most recent
      same-tier trials; `quality_exclude_before_ts` is scoped `eval_quality` only. Post-fix median
      measured lift is **+4%, inside the 5% margin**, so "candidates really are faster" cannot be
      distinguished from "the comparator lags a host that got faster". Main residual anti-conservative
      risk.

  - 2026-11-01 codex3 acceptance: The comparator and prior rate statistics now use the existing ratified speed-era cutoff, including the indirect action gate. Prior rate z requires an original strictly typed witness of both speed and quality cutoffs; missing, malformed and mismatched history is not retrofitted. Cached verdicts use the existing side-effect-safe upgrade path, so an unfenced cached statistic is never stamped as new evidence, failed caches do not become passes, and MAD/counters are not duplicated. The focused controls passed 49; a broader failure was independently reproduced on the original source bytes. This closes the engineering fence, not the historical host-drift question: no new speed boundary, threshold, activation or scientific comparison is claimed. [belief: cc]

- [x] SEQ-B3 — Delete the unused `_axis_refuted_factory`. ✅ 2026-10-29
      Orchestrator main `7678711d5b4aa4431abcd089a429b0561180aa29` removes the factory;
      source and test searches found no callers or tests binding it. The existing attribution
      and refutation suites passed all 23 tests after integration. Canonical `axis_refuted`
      and report logic remain unchanged. [no-belief: unused-code removal; no measurement claim]
- [x] ✅ 2026-10-31 SEQ-B4 — Decide explicitly whether the refutation record should carry `k_rate` alongside the QUALITY axis. Evidence: orch `bd2f7105a6b04fc9f9cffba0dff861c6e79c1c8d`; `tests/unit/test_seq_refutation_capture.py`; `/mnt/raid0/llm/tmp/refactor-seq-b4-20261031/TESTS.log` (36 pass). [no-belief: journal capture/reconstruction correction; policy thresholds unchanged]
      New live records and reconstruction use observed `k_rate`; legacy absent counts retain the prior fallback without invented history. Original gap: the QUALITY
      axis's `k`, which it currently reuses for both axes (matching the journal's single `k` and the reader)
      even though the two can differ when the rate axis was skipped on earlier trials
      (`scripts/autopilot/safety_gate.py:1780`) (found 2026-09-14, noninf sweep).

*Declined 2026-09-14: "the rate-axis comparator still has no era fence of its own" (`handoffs/active/autopilot-sequential-allocation.md:265`)
— not filed because it IS the open **Rate-axis comparator has no era fence of its own** box at that line.*

*Declined 2026-09-14: "no live journal row will carry a `refutation` record while the sequential path stays
default-off (`AUTOPILOT_SEQ_VERDICT=0`)" — not filed because re-arming is the open **Decide whether to re-arm the
sequential gate** box at `:249`, an operator decision, and the observation adds no separate action.*

- [x] SEQ-A — Sticky `refuted` label (above). ✅ 2026-10-29 (audit: handoffs/active/autopilot-program.md SEQ-A0 [x] (43108014, 2026-08-11) and SEQ-A1 [x] VOID 2026-08-11: question dissolved, routed to SEQ-B1; all children closed) [no-belief: audit-reconciliation]
- [x] ~~SEQ-B — Frozen baseline-promotion gate (above).~~ (closed 2026-10-29 audit: DUPLICATE → handoffs/active/autopilot-sequential-allocation.md:169 (canonical SEQ-B box); :287 is a pointer copy)
- [x] SEQ-4 — Re-examine the 9 candidates whose refutation does not survive the relaxed budget. ✅ 2026-07-29 — deterministic re-adjudication in [`readjudicate_sequential_20260728.json`](../../epyc-orchestrator/orchestration/reports/readjudicate_sequential_20260728.json) confirms all nine under the same era-fenced `core_v1` evidence; none reaches `confirm_e=20.0`.

      **Disposition:** `70902e4b665474e7` (E=11.5507, ~9 trials estimated) and
      `dd793a6ee43ce718` (E=8.7048, ~10 estimated) are the only credible continuation
      candidates, and are already represented by the SEQ-3 era-gated paths above. The
      remaining seven do not create an independent retry: `85c3dcf25823c537` needs an
      estimated ~30 trials; `db866b4a9fa37e03` ~55; `45129cc6ee5bac29` ~69;
      `4b6b454ea4f884fd` ~263; `3055f1e32fac0316` ~1699; and
      `b738287be98c3372` / `80aa44d93a242af5` were falling (growth <1). Those estimates
      are not forecasts; all are historical-`core_v1` priors and cannot be continued
      without the SEQ-3a bridge ruling or the clean SEQ-3b E8 restart.

- [ ] **SEQ-4 — zero-inference allocation replay: would a bandit allocator have reached confirm_e on the stored pool?** Re-fold the 141 stored candidates / 393 trials under (a) BaSE-style UCB/Thompson routing (intake-1456) and (b) fluid-style portfolio AUC objective (intake-1457); compare against the fixed budget=8 heuristic; report AUC-frontier vs endpoint. Offline only — does not touch the human-amendment-only SEQ-3/SEQ-B1 decision or re-arm any gate.

#### Rider — retroactive objective change: what survives it, what does not (2026-08-11)

**Operator position, 2026-08-11, ACCEPTED**: as long as results and progress are tracked diligently,
the to-be-optimized metric may be changed later, and whatever is needed to keep optimizing in the new
direction can be recomputed from that moment forward.

**Operator context**: the Pareto frontier is sparse today (models being swapped, infra bugs still
landing), so deliberately choosing throughput-penalized / quality-favoured configs is premature. The
operator may authoritatively choose them later. AutoPilot's hypervolume is quality × tasks-per-hour;
unless the tradeoff is exactly inversely proportional there should be a non-trivial interior optimum,
plausibly near the frontier's highest-curvature (knee) point.

##### F1 — the claim holds, CONDITIONALLY: re-aiming runs over stored COMPONENTS, never over stored SCALARIZATIONS

Verified in code, not taken on report:

- `experiment_journal.py:191-265` — `JournalEntry` persists the raw axes as top-level fields
  (`quality`, `speed`, `cost`, `reliability`), plus `eval_details`, `harness_metrics`, `seq`.
- `experiment_journal.py:336` — the direction comment is exactly as cited: the optimizer declares
  `directions=["maximize"]*4`, the third objective is NEGATED cost, so the raw `cost` field on the
  row is `lower_better`. The row stores raw cost; the sign lives in the reader.
- `experiment_journal.py:289` — `eval_details["objective_policy_live"]` is read per row, as cited.
- The objective vector is **derived at read time**, not stored:
  `tier_specs.py:344-366` `_policy_aware_objectives_from_row` dispatches on the row's own recorded
  policy; `tier_specs.py:328-341` `_rate_objectives_from_row` rebuilds `(quality, qph, -cost,
  reliability)` on demand; `tier_specs.py:220-230` `seq_task_rate_qph_from_row` recomputes
  tasks-per-hour from `question_results` + `eval_wall_s`. This is the mechanism that makes the
  operator's claim true — and it has already been exercised once, on the tokens/s → qph axis flip.

**The picture is more partial than the two cited lines alone suggest — state it plainly.** Measured
over `orchestration/autopilot_journal*.jsonl`, 1372 trial rows:

| write-side field | rows carrying it |
|---|---|
| 4 raw components (`quality`/`speed`/`cost`/`reliability`) | 1372 / 1372 |
| `eval_details.eval_wall_s` | 1147 / 1372 |
| `eval_details.question_results` (rate-axis numerator) | 523 / 1372 |
| `eval_details.objective_policy_live` | 534 / 1372 |
| `measurement` claim tuple (added 2026-08-10) | **0 / 1372** |

So: the 4-axis re-aim is fully retroactive; a re-aim needing the question ledger is retroactive over
~38% of history; and the era label is *inferred from absence* on the other ~61% —
`tier_specs.py:352-360` says so outright ("pre-flip rows … have no question ledger at all"). The
claim-tuple hook exists in code but has zero rows behind it yet.

This is the belief-kernel rule in CLAUDE.md, restated on a second store: the write side is cheap and
permanent, the read side cannot be retrofitted, and `benchmarks/results` (4,562 files, no write-side
hook, 0/200 sampled with a usable claim tuple) is the standing counterexample.

**A metric change is structurally an ERA BOUNDARY, and the machinery already exists.**
`epyc-orchestrator/orchestration/instrument_eras.yaml` was amended four times on 2026-08-11 under
operator signature (`53fc3250`, "4 rows, none struck"). **Recommendation: any future objective change
is recorded as an era row, never as an edit.**

##### F2 — the exception that matters: rescoring is retroactive, STOPPING is not

The sequential gate does not merely score candidates — it decides which ones keep GENERATING data
(`safety_gate.py:1528-1529`: `if q_name == STATE_REFUTED or rate_name == STATE_REFUTED: state =
"refuted"`). A candidate refuted under today's joint rule stops accumulating trials. Under a future
objective you can rescore every trial that exists; you cannot recover trials never run. **A stopping
rule is a data-generating decision wearing the costume of a scoring decision, and it is the one thing
a future metric change cannot undo.**

Concretely, and exactly the configuration class the operator says they may later want:
`70902e4b665474e7` (k=40), `dd793a6ee43ce718` (k=24), `85c3dcf25823c537` (k=15) stopped under the
joint gate because they buy quality with throughput.

- [x] SEQ-B2 — Capture the refutation counterfactual AT STOP TIME: record which axis refuted and the margin on the other. ✅ 2026-09-14 (`seqb2`, `epyc-orchestrator` `4c220b11`, branch `fix/noninf-seqb2`). Write side landed: `safety_gate.py::_sequential_verdict` now writes `block["refutation"]` (`seq-refutation-v1`: `refuting_axis`, `refuting_margin`, `other_axis`, `other_axis_margin`, `both_axes_refuted`, `n_trials_at_stop`, per-axis `{wealth,k,refuted,margin,threshold,rule}`, policy `thresholds`, `captured_at`) on the refuted branch ONLY — additive, legacy and non-stop rows load unchanged, no journal file on disk touched. The predicate is now ONE canonical definition (`sequential_verdict.axis_refutation` / `refutation_record`), and `readjudicate_sequential_candidates.py` was reduced to a thin delegation that PREFERS the live field (`refutation_of`) and falls back to reconstruction for pre-SEQ-B2 rows, tagging every reported row and JSON record with its provenance. Attribution mirrors the script's own `if/elif` exactly: quality first then rate, `both_axes_refuted` carried separately, `null` = the UNEXPLAINED bucket, an unmeasured axis never refutes. Sign convention documented: `margin = wealth - threshold`, negative = refuted, futility inclusive / budget strict. 17 new tests (`tests/unit/test_seq_refutation_capture.py`), including `test_live_and_reconstructed_agree_on_a_synthetic_candidate`; `pytest tests -k "sequential or safety_gate or readjudicat"` 268 → 271 passed, 0 failed. Clean against `fix/noninf-etr` (`merge-tree` exit 0). SEQ-B1 (joint-gate vs quality-primary) remains the operator's, untouched.

##### F3 — knee / max-curvature is not scale-invariant

Curvature of a Pareto frontier changes under rescaling of the axes. Quality is roughly [0,1] while
tasks-per-hour is order [0,600] (`tier_specs.py:203` returns `n / (wall/3600)`), so "the
highest-curvature point" is **undefined until a normalization is fixed — and the normalization
silently does the real work.** Hypervolume is also scale-dependent, but it forces the reference point
to be stated explicitly, which is why it is the more honest default.

**Recommendation**: if knee-selection is ever adopted, the normalization is a declared and ratified
quantity (an era row), not an implementation detail.

The operator's accompanying observation is correct and worth recording: a strictly inversely
proportional (hyperbolic) tradeoff makes every frontier point equivalent under a product objective, so
a genuine interior optimum requires curvature away from that.

##### Background, not an open question — SEQ-B1 posture

SEQ-B1 (joint gate vs quality-primary with rate advisory) remains human-amendment-only and
**UNDECIDED**. On 2026-08-11 the operator stated the current joint-gate behaviour **"is fine for
now"** and explicitly deferred the change to a future in which the frontier is well populated.
Recorded here as a dated operator position so nobody re-opens it as a defect: **the gate is working as
designed; nothing is broken.**

#### Why this is independent of the episodic-memory work

The candidate evidence lives in `orchestration/autopilot_journal*.jsonl`, a different store from
`orchestration/repl_memory/sessions/`. Journal mtimes (2026-06-27, 2026-07-27T08:23) predate the
2026-07-27T22:07 reseed, and `rebuild_candidate_view` folds *journal-derived* z sequences. **Scrubbing
and reseeding episodic memory cost this analysis nothing.**

#### Reporting

Record SEQ-3's outcome here with the trial count actually spent and the final E. If the candidate
crosses 20.0, the program has its first genuine confirm and the allocation rule should be
re-specified. If it plateaus, that is equally decision-grade — and far cheaper than the ~347
eval-hours already spent without a verdict.

#### Research Intake Update — 2026-09-25 (Shinka parent-selection replay)

- [ ] **SEQ-SHINKA-1 — Run the first policy screen over the shared selector-replay package.** Consume the immutable journal/candidate graph, incumbent policy, outcome bytes, task order, holdout, and digests frozen by `AP-DGM-PROV`; do not generate a second candidate campaign. Compare the incumbent with rank power-law and weighted score-times-inverse-offspring selection under the same eligible decisions, evaluator calls, proposer tokens/cost, and wall budget. Write per-decision choices and held-out continuation through `VB-DGM-1`, retaining invalid, failed, and abstained decisions in the denominator. Report choice agreement separately from outcome change and test time-split or bootstrap stability where the 393-trial / 141-candidate record permits it. Stop if policies select the same parent on at least 95% of eligible decisions, if differences do not improve held-out continuation over the incumbent and score-only controls, or if gains reverse across holdouts. A stable gain permits one bounded live paired follow-up and release of the ALE trigger; it does not authorize a selector change. Sources: intake-779#record, intake-1595#record, intake-1596#record.
  - **Implementation checkpoint 2026-09-26:** root commits `37e74b28`, `f434bad5`, and `e8ca0811` implement separate seeded rank-power-law and weighted score-times-inverse-offspring screens over one immutable package. `replay-both` seals two five-arm receipts plus one aggregate digest; fixtures prove denominator retention, paired continuation checks, chronological blocks, cluster bootstrap stability, and all stop rules. The real 393-row record cannot support the screen without inventing eligible menus, holdout assignment, model/decoding identity, or unchosen-parent outcomes, so the historical task remains open and inference-gated by prospective capture rather than being reported as a null result.
  - **2026-11-09 (RTG-02 audit):** blocked on the AP-DGM-PROV decision above (no selector menu exists to capture; inference is not the first blocker). The "ALE trigger" is defined in the dormant `AP-RI-ALE-1` record: a stable held-out gain by this screen or AP-DGM-SEL.

**Dormant follow-on:** a full ShinkaEvolve or ALE campaign becomes active only if this replay beats matched simple controls on held-out continuation, or a live long-horizon engineering campaign requires ALE-style evaluation. Until then, reuse this replay and its receipt rather than launching iterative candidate generation.

#### Research Intake Update — 2026-10-20 (harness cluster)

Operator-approved 2026-10-20 via research intake (plan sha256 1dc83054706ca0bae002602307b0d9ba6435b010be4d6ffd8a495a04605f3967). Monitor and knowledge records below are prose: no checkbox, no index next action.

- [x] **SEQ-5 — Lifetime promotion-attempt ledger and screening-channel diagnostics in `seq_readiness_report` (read-only; no gate change; zero inference).** Verified 2026-10-20: the `alpha_wealth` block (`scripts/autopilot/seq_readiness_report.py:395-428 @5d4ad2c0`) has no K_opened, union-bound or lifetime field; it counts every fingerprint with any journaled `seq.candidate`; and an attempt opened but interrupted before its fresh-eval row exists is not recoverable from the journal. Add (proposed names; keep existing keys untouched): `promotion_attempts_opened`, `promotion_attempts_finalized`, `promotion_attempts_failed_or_interrupted`, `promotion_alpha_per_attempt` (1/`SEQ_PROMOTION_FINAL_CONFIRM_E`, 0.01), `lifetime_false_promotion_bound` (per-attempt alpha x K_opened, the union bound), `promotion_alpha_per_attempt_for_declared_delta_life` (delta_life / K), `fingerprints_confirmed` (R), `est_false_confirm_fraction` (expected_false_confirms / max(R,1), a conservative all-null heuristic), `cumulative_rate_drift_bound` (promotions x `rate_noninferiority_margin` 0.05) and `rate_reference_is_latest_only` (true by construction: the rate and quality nulls are rolling medians and profiles over the 120 most recent incumbent-representative trials, `autopilot.py:3873-3938`). K_opened from the journal alone is a lower bound unless the pending-promotion state transition is also journaled; decide between reporting a lower bound and adding an append-only 'opened' journal event (a write-side change, still no gate change). Declare in the report what an instrument-era boundary does to charged alpha: today it resets the charged set (`quality_exclude_before_ts`, `autopilot.py:3847-3851`). The ledger is a derived fold of the already-ingested journal, not a new measurement source (descriptive-census stance); if it is ever cited to gate a promotion it needs a ClaimTuple first. Follow-up triggers: K_opened above about 5 per quarter reopens decision package DP-A option (b); fingerprint confirmations still binding after the era and rate-axis faults are fixed reopens DP-C option (b) (`intake-2174#01`, `intake-2188#00`, `intake-2187#02`). ✅ 2026-10-21
  - 2026-10-21 (noninf-gates) result. `promotion_attempt_ledger` in `src/autopilot_core/sequential_replay.py`; `seq_readiness_report.py` merges its keys into the `alpha_wealth` block (existing keys untouched) and prints a ledger line (epyc-orchestrator `ea8c7338`). Frozen input: journal snapshot sha256 `6bb790ba837c9ea23f9e6ebd1a8ff00e354baf196ec7fe830d02dd54fc8c5b4a` (autopilot_journal.jsonl 18257825 B + autopilot_journal_1.jsonl 19801823 B; 1372 rows).
  - Result: `promotion_attempts_opened` 0 (a LOWER BOUND, flag `promotion_attempts_opened_is_lower_bound` true), finalized 0, `promotion_alpha_per_attempt` 0.01, `lifetime_false_promotion_bound` 0.0, `fingerprints_confirmed` 0, `est_false_confirm_fraction` 0.0, `cumulative_rate_drift_bound` 0.0, `rate_reference_is_latest_only` true. The journal holds 141 tested fingerprints and zero rows with `seq.confirmed` or a fresh-eval promotion block, so K_opened is 0 and the DP-A (about 5 per quarter) and DP-C triggers are not met. Era boundary: `quality_exclude_before_ts` leaves 0 rows at or after the boundary, so the live charged set is empty; the report states that an instrument-era boundary resets charged alpha. The task's choice (report a lower bound vs add a write-side 'opened' event) is taken as lower bound; adding an event is a write-side change not made here.
- [x] **SEQ-6 — Counterfactual replay of the sequential gate under one frozen null per candidate (zero inference; no gate change).** Verified 2026-10-20: `ref_snapshot` does not exist in code; `_seq_inputs_for_trial` (`scripts/autopilot/autopilot.py:3812 @5d4ad2c0`) rebuilds the null from the 120 most recent incumbent-representative rows on every trial, so a kept candidate enters later nulls and each stored z was computed against the null as it stood then. Recompute each trial's quality z from stored `eval_details.question_results` under ONE frozen null per candidate (the profile as of its first trial) and report how many verdicts and E values change relative to the live rolling null. Anytime-validity needs the reference fixed before observation (`intake-2173#01`, `intake-2174#01`). Frozen input: the journal snapshot digest; denominator: all candidates with at least the live minimum of 3 baseline rows, the rest counted as not replayable; decision rule predeclared: report only. Changing the live null changes what counts as a promotion and belongs to the operator (human-amendment boundary). ✅ 2026-10-21
  - 2026-10-21 (noninf-gates) result. `frozen_null_replay` in `src/autopilot_core/sequential_replay.py` (epyc-orchestrator `ea8c7338`). Frozen input: journal snapshot sha256 `6bb790ba837c9ea23f9e6ebd1a8ff00e354baf196ec7fe830d02dd54fc8c5b4a` (autopilot_journal.jsonl 18257825 B + autopilot_journal_1.jsonl 19801823 B; 1372 rows). 119 (candidate, tier) groups with seq rows and vectors; 118 replayable; 1 not replayable (fewer than 3 baseline rows at its first trial).
  - 2026-10-21 (noninf-gates) mismatch characterization (epyc-orchestrator `c7abc05e`). Of the 97 trials whose journaled z the rebuilt null did not reproduce (all tier 1, trials 1050-1282: 60 revert, 37 excluded), 79 are explained by one cause: bug tag `backend_connectivity_pollution_20260708` (26 rows, trials 1049-1263) was applied retroactively, so the live null still contained those rows when the later trials ran. Treating it as present below trial 1225 (a cutoff FITTED on this journal, not a recorded fact) lifts matches from 236 to 315 of 333. 18 remain unexplained, clustered at trials 1225-1282 right after the cutoff (a single cutoff is an approximation of staged tagging). Ruled out by trying each: window 30/60/100/119/121/240/unbounded fixes 0 or 1 of 97 and breaks 137-222 matching trials, so 120 is right; dropping the tier filter, dropping the learning-exclusion rows and the incumbent-only rule all fix 0; the instrument-era fence is not a cause (no row is at or after the boundary); 1 trial (tier 2) has no rebuildable null. Rerun on the matching subset (112 of 118 groups, 294 steps; 6 groups with an unreproduced z dropped): the conclusion is unchanged: 2 groups change final verdict, 19 steps change, both groups cross confirm_e only under the frozen null, journal and rebuilt rolling cross in 0. With the cutoff rule on all groups: also 2 and 19. Ticked with the caveat that the 18 residual trials are unexplained.
  - Harness validation first: the journaled z is reproduced by rebuilding the rolling null from all usable same-tier rows in 236 of 333 trials; the current-code rule (incumbent-representative rows only) reproduces 0 of 323, so the journal predates that filter. Counterfactual figures are therefore frozen vs the REBUILT rolling null and carry that infidelity. Result: 2 of 118 groups change final verdict (both accumulating to confirmed under the frozen null), 19 of 323 steps change verdict, 23 groups have E moved by over 1 percent, median |log10 E ratio| 0.0, max 1.148. Groups crossing confirm_e: journal 0, rebuilt rolling 0, frozen 2 (candidates 70902e4b665474e7 E 11.55 to 162.33 and dd793a6ee43ce718 E 8.70 to 27.26). Report only; changing the live null is the operator's.
- [x] **SEQ-7 — Paired-z replay over accepted mutations: false-elite rate and rounds a stop rule would have saved (read-only, zero inference).** For each journal row with `keep_revert_decision == "keep"`, compute the paired discordant-pair statistic against its predecessor incumbent's per-question outcomes (`eval_details.question_results`; `paired_stats.mcnemar_from_vectors` and `compare_fingerprints` already exist) and report the share of accepted mutations whose paired statistic is below the 1.96 equivalent (false-elite rate) and the number of rounds a paired-z stop rule would have saved; without the paired screen the source loop showed phantom progress and never terminated (`intake-2176#03`). State the unit caveat in the result: an AutoPilot trial is one pass over about 37 scoreable questions (P-QUAL-T1), not three attempts per question, so the published screen cannot be copied verbatim and the available paired unit is the McNemar form. Frozen input: the journal snapshot digest; denominator: every keep row, rows lacking question_results counted separately; the result feeds HIL-2 item 11 and changes no gate. ✅ 2026-10-21
  - 2026-10-21 (noninf-gates) result. `paired_keep_replay` in `src/autopilot_core/sequential_replay.py` (epyc-orchestrator `ea8c7338`). Frozen input: journal snapshot sha256 `6bb790ba837c9ea23f9e6ebd1a8ff00e354baf196ec7fe830d02dd54fc8c5b4a` (autopilot_journal.jsonl 18257825 B + autopilot_journal_1.jsonl 19801823 B; 1372 rows). Statistic: z = (gained - lost) / sqrt(gained + lost) over shared qids against the previous keep row of the same tier that has a vector; significant means z >= 1.96.
  - 229 keep rows: 146 without `question_results` (counted), 1 without a predecessor vector, 82 with a paired statistic; 81 of 82 are below 1.96 (false-elite share 0.9878). By action type: numeric_trial 46 of 47, seed_batch 34 of 34, structural_experiment 1 of 1. Predeclared stop rule (stop a tier after 3 consecutive non-significant keeps): tier 1 triggers at trial 803, after which the journal holds 487 later tier-1 trials, 79 of them keep rows. Unit caveat per the task text: one trial is one pass over about 37 questions, so the McNemar form is the available unit. Most keep rows are seeding or numeric trials, not mutations, so the false-elite share describes ships as recorded, not mutation quality. Feeds HIL-2 item 11; no gate change.
- **M1 (monitor, 2026-10-20) — DP-A pending: lifetime promotion error budget.** Trigger: The operator decides, or the SEQ-5 report shows K_opened above about 5 per quarter. First step when it fires: Re-open DP-A option (b) with the measured K_opened. No immediate step remains: The only useful step (the ledger) is SEQ-5; an amendment is human-only.
- **M3 (monitor, 2026-10-20) — DP-C pending: rolling-window alpha budget.** Trigger: The operator decides, or the SEQ-5 report shows fingerprint confirmations binding after the era and rate-axis faults are fixed. First step when it fires: Re-open DP-C option (b). No immediate step remains: The budget is not the binding gate today (2026-07-11 audit); reporting is SEQ-5.
- **M11 (monitor, 2026-10-20) — Alpha and certificate follow-ons (earn-back on promotion, online e-BH, e-GAI, decaying-memory online FDR, Biometrics rejoinder, Safe Harness).** Trigger: DP-C option (b) adopted, or the HIL gate design needs a generation-versus-certification argument. First step when it fires: Read the listed sources before choosing a scheme. No immediate step remains: e-LOND was declined; the successors are unread at the wave cap.


##### Discovered quality-provenance defect — codex3, 2026-11-01

- [x] **SEQ-QUALITY-ERA-PROVENANCE — require original native evidence of the active quality-era fence for stored quality z and mismatched cached verdicts; never retrofit historical witnesses.** ✅ 2026-11-01 — APP implementation `59934bfa18913d5379984d9d61fb23129b42ea97`; [source-bound controls and original baseline failures](https://github.com/pestopoppa/epyc-orchestrator/blob/fb2036d93203eb4e5a87918ecf0572c29ba73fd3/artifacts/engineering/seq-quality-era-witness-20261101/README.md). [belief: cc]
  - Review of the rate fix exposed a separate quality path: a post-boundary timestamp did not prove that stored z used the quality-era comparator. The native writer now records the actual quality cutoff only after a finite quality statistic is computed. An active quality cutoff requires its matching typed witness; absent, mismatched or malformed historical values remain unqualified, while no-era behavior and the original raw baseline/alpha folds remain unchanged. Quality-only cache changes use the existing native upgrade without inventing a witness or resurrecting a failed verdict. The seven-file selection recorded 285 passes and two failures reproduced on the pre-change source bytes; after refreshing the nine unrelated peer paths, all 49 focused controls passed again against the refreshed checkout. The proof distinguishes both runs. The fixture index now reflects its HEAD and only protected DAR work remains dirty. No live journal, new cutoff, statistical rule, model call or gate activation. This is a newly discovered repair outside the standing WORK code queue and is not included in the two queue closures in this checkpoint. [belief: cc]

## Track: promptforge-mutation-safety-contract
<!-- gate: RTG-02#autopilot-program, RTG-02#autopilot-dashboard-fidelity-audit-2026-07-22, RTG-02#autopilot-decision-plane-audit-2026-07-22, RTG-02#batched-edit-parallel-apply, RTG-02#bep-dcp-falsification-harness, RTG-02#evidence-plane-event-sourcing-and-narrative, RTG-02#evidence-plane-instrument-repair, RTG-02#evidence-plane-ledger-and-sequential-verdicts, RTG-02#loops-and-dashboards-audit-2026-07-05, RTG-02#objective-task-rate-goodput, RTG-02#orchestration-robustness-audit-2026-07-11, RTG-02#scaffold-autopilot-cost-lever-deployment -->

> Folded from `handoffs/active/promptforge-mutation-safety-contract.md` @ `b1bf3f3f7ade` on 2026-11-02 (BRF-T1-F21, route 1a, operator D1/D5; retired row RTG-55 → EVL-04). Body moved verbatim, headings demoted two levels to nest under this track; every open and closed box kept its text and ID.

### PromptForge mutation safety contract (RTG-55)

**Status**: stub
**Created**: 2026-09-07 (research intake, operator-approved plan; successor of ../completed/meta-harness-optimization.md whose active pointer was retired 2026-08-23)
**Categories**: meta_harness, autopilot, safety
**Related**: [autopilot-continuous-optimization.md](autopilot-program.md) (RTG-02) · [eval-tower-verification.md](eval-tower-program.md) (EVL-14) · [agent-collab-rnd-harness.md](autokernel-loop.md#track-agent-collab-rnd-harness)

#### Objective

Constrain what a PromptForge mutation may DO — not merely which files it may touch — so that mutation
safety is a compile-time property of the harness rather than a promise made in prompt text. The
lineage's active pointer was retired 2026-08-23 and the completed ledger forbids new task checkboxes,
so this is a **new active stub, not a reopen**.

#### Research Context

| Entry | State | What it contributes |
|---|---|---|
| `intake-1323#record` | dive-verified | Harness-R1's typed return-effect contract, AST denylist, forbidden-text patterns, the ANTI-OVERRIDE prior, and the `examples/heldout_generalization/` corpus |
| `intake-1317#record` | dive-verified | Optimizer budget shape (constant in training-set size, large constant) |
| `intake-1320#record` | stage-1 / bearing | JIT admission-rule comparison context (the archive/admission half lives in AP-51) |

#### Tasks

- [x] **MHS-1 — Typed return-effect contract.** Constrain what a mutation may DO (a closed per-site
      effect enum, host-normalized and truncated), not only which FILES it may touch. Reference
      implementation: Harness-R1 `code_runner.py:31-34` + `_normalize_hook_result`, ~50 lines.
      *Highest value, cheapest.* `intake-1323#record` (dive actionable D0). Zero compute. ✅ 2026-09-14 — `MutationEffect`
      (`inert|constrain|expand|replace|unsafe|unknown`) with total `normalize()` (aliases in, unrecognised ⇒
      `UNKNOWN`, tokens truncated at 32 chars, reasons at 240); `CodeMutation.effect`/`.effect_reason`; both
      `apply_code_mutation*()` refuse `UNSAFE` and report `effect`. CONSTRAIN/REPLACE derived mechanically
      (answers Open Question 3 — no separate label needed). epyc-orchestrator `7d4b40a8`, tests
      `test_effect_enum_is_closed`, `test_effect_normalization`, `test_unrecognized_effects_normalize_to_unknown`,
      `test_classify_*`, `test_apply_rejects_unsafe_effect`, `test_apply_in_context_reports_effect`.
- [x] **MHS-2 — Close the MH-9 inertness hole.** The AutoMem `schema_evolution` `new_file` lane
      requires "default-inert" modules as **prompt text only** (`prompt_forge.py:1261-1277`) while
      `_validate_code_mutation`'s importlib step (`:1147`) executes the module top level
      **unsandboxed in the live repo**. Add an AST node denylist
      (`Import/ImportFrom/With/While/Lambda/ClassDef/Raise/Global/Delete/Yield/Await`) plus
      dunder/underscore `Name` + `Attribute` rejection over `new_file` proposals, modelled on
      `code_runner.py:64-103` and `:170-176`, so inertness is **compile-time, not a promise**. MH-9's
      own row already anticipated this ("keep edit-only allowlist until a stronger isolation story
      exists") — this IS that story. `intake-1323#record` (dive actionable D1). Zero compute. **Depends on MHS-1** (the effect
      enum is the denylist's contract). ✅ 2026-09-14 — the repo-write + in-process `importlib` step
      (`origin/main` `prompt_forge.py:1149`/`:1157`) is GONE; validation is static-only
      (`screen_static_safety`), with the ratified strict node denylist + underscore/dunder rejection for
      `new_file`, a capability denylist with original-file grandfathering, and the MH-9 prompt rewritten to
      the shape the screen admits (`MEMORY_SCHEMA_SHAPE_EXAMPLE` screened in CI, so prompt/denylist drift
      cannot recur). epyc-orchestrator `7d4b40a8` + `c27eec6c`; 100 tests incl.
      `test_validation_never_writes_the_target_file`, `test_validation_does_not_import_the_candidate_module`,
      `test_strict_profile_rejects_denylisted_nodes` (11 cases),
      `test_noop_mutation_of_every_allowlisted_file_passes`, `test_prompt_shape_example_passes_the_strict_screen`,
      `test_old_class_shaped_proposal_is_rejected_by_the_strict_screen`. Selection 40 → 140 passed.
- [x] **MHS-3 — Missing half of the transfer guard.** ✅ 2026-09-17 (landed with the AutoPilot merge train, orchestrator `a1a0251a` on main, which contains `6df6f0d8`; the notes below that say "not yet on main" predate the landing). `_UNIVERSAL_TRANSFER_RE`
      (`prompt_forge.py:83-88`) rejects OVER-generalization (`always|never|all tasks`); Harness-R1's
      `FORBIDDEN_TEXT_PATTERNS` (`harness_r1_patch.py:233-238`) rejects **UNDER**-generalization (a
      patch naming a specific eval task id / sample index / item id). We have **no** guard against a
      mutation memorising the eval set by naming its instances. Add an anti-leakage pattern set over
      accepted mutation text keyed to our suite/task identifiers. `intake-1323#record` (dive actionable D2). Zero compute.
      **Structural form (2026-09-15):** the refusal lives in _transfer_safety_verdict and returns
      valid=False when a mutation's added text — prompt mutations AND code_mutation mutated_content
      (string literals, comparisons) — shares a verbatim ≥8-token n-gram with, or an exact expected
      answer from, the current draw, sentinel_questions.yaml, tool_sentinels.yaml or the contrastive
      trace bank. Record the matched source id. It also refuses in-suite special-casing, which the
      current check allows (it refuses only suites absent from the source context).
      **Source-identity key:** it ALSO refuses a mutation whose few-shot or example content was
      derived from a trace of a question in the current draw. The key is the question id or sentinel
      id carried in the contrastive trace-bank records (actions.py trace context; eval_tower.py
      fixed 20-trial draw), not only a verbatim n-gram, because paraphrase bypasses n-gram matching.
      BAITBENCH entity-overlap and near-duplicate shortcuts had take-rates of 82.5% and 72.5%
      (intake-1395#record). One leakage checker serves prompt and code mutations. Instruction text
      ("don't overfit") is not the fix (intake-1379#record; intake-1395#record, where validity
      prompting moved -6.2 pp). EvilGenie partial-hardcoding class (intake-1387#record).
      ⏳ PARTIAL 2026-09-16 (`sub-autopilot-safety`, orchestrator `8219d8e8` on branch
      `sub/autopilot-safety-20260916`, NOT yet merged; box stays open: structural form completed on `sub/mhs3-complete-20260916`, see below): `EvalIdVocabulary` + `eval_leakage_reason()`
      in `prompt_forge.py`, applied to the ADDED text of prompt, code and GEPA mutations. The vocabulary
      comes from eval data, not a hand list: research `question_pool.jsonl` (required), `core_*.jsonl`
      and the sentinel YAMLs → 153,450 ids (pool ids, nested core qids, prompt-hash qids), 295 id
      families derived from them, and suite/id-stem anchored references, plus a qualified generic
      pattern (`sample #12`, `task_id == 17`). **Fail-closed**: a missing or unreadable pool rejects
      every mutation (`eval_leakage_vocabulary_unavailable`). Measured false positives: 0 over all 33
      current prompt + allowlisted code targets (a regression test pins this), and 1 file of 444
      docs/src files, where both hits were real instance references. Open Question 2: keyed on ids plus
      prompt-hash qids (content hashes of text); image-bound qids are not included.
      `tests/unit/test_prompt_forge_leakage_and_risk.py` (73 tests).
      Operability (loud fail-closed state: startup preflight, alarm after 3 consecutive
      `eval_leakage_vocabulary_unavailable` rejections, runbook `docs/guides/meta-harness-operator-guide.md` § 7)
      built on branch `sub/gate-frontier-20260916`, under review, unmerged (2026-09-16, `sub-gate-frontier`).
      **Structural form built 2026-09-16 (`sub-mhs3b`, orchestrator `6df6f0d8` on branch
      `sub/mhs3-complete-20260916`, built on `sub/gate-frontier-20260916`; carried by the AutoPilot merge train
      `sub/autopilot-train-20260916`, not yet on main; flip the box when it lands):** `_transfer_safety_verdict`
      and the GEPA path now also refuse, over the ADDED text: `eval_content_ngram_overlap` (verbatim >=8-token
      overlap with the pool/cores/sentinels or the rendered trace bank; hashed shingles packed with row id,
      ~1.3e-7 FP per shingle, template df >=32 dropped, anchor-or-15-token-run rule),
      `eval_expected_answer_leakage` (name-shaped 1-7 token answers), `eval_source_identity_leakage` (trace
      blocks resolved to question/sentinel ids; >=3 shared rare tokens, paraphrase-proof) and
      `eval_suite_special_casing` (keyed/phrase/mention, in-suite included). Matched source id in every reason.
      Same pass, cache and fail-closed state as the id vocabulary; harness text (prompts, src/, original) is never
      blamed. Real pool: 16 s cold, +590 MB RSS (index 173 MB, 1.37 GB transient peak), ~9 ms per edit. FP: 0/33
      live targets; content 0/91 historical mutations (special-casing 2/91 borderline); 2.4% of 467 whole
      src/docs files. Coverage 1998/2000 verbatim pool prompts. Runbook § 7 extended.
      `tests/unit/test_prompt_forge_content_leakage.py` (51 tests). Detail:
      `progress/2026-09/2026-09-16-sub-mhs3b.md`.
  - [x] **MHS-3a — remove the pool leak MHS-3 found in live harness text** ✅ 2026-09-16 (orchestrator
        `09bdb998` on main). Pool row `simpleqa_general_00912` (Aschoff / Bonn) was a worked example in
        `orchestration/prompts/rules.md` Example 4b and `DEFAULT_ROOT_LM_RULES`; both now use a synthetic
        example, and a dormant HumanEval/55 copy in `src/prompts/coder_system.txt` was replaced too. Takes
        effect at the next API reload (owned by the session that owns inference).
        Detail: `progress/2026-09/2026-09-16-sub-leak00912.md`.
  - [x] **MHS-3b — close the rewind hole: operator RATIFY of the checkpoint prompt re-pin.** ✅ 2026-09-17 RATIFIED by the operator (root `b8379d42`): all 10 checkpoint copies re-pinned to `18f8ea01`, originals in `/mnt/raid0/llm/backups/ckpt-leak-20260916/`. Operator chose
        option A (2026-09-16). Ten AutoPilot checkpoints, including production_best (multitier_v10), still
        carry the leaked `rules.md` (`b250c227…`), and `restore_checkpoint()` copies it back. Script landed on
        root main (`0e2bbc33`); the operator runs
        `bash -c 'bash <(git -C /mnt/raid0/llm/epyc-root show origin/main:scripts/operator/run_ckpt_leak_ratify_20260916.sh) --operator pestopoppa'`
        and types RATIFY (refuses while AutoPilot holds its lock). Detail: `progress/2026-09/2026-09-16-sub-ckpt-leak.md`.
  - [x] **MHS-3c — clean the out-of-scope leak copies** ✅ 2026-09-17 (all three scopes purged; `--verify` PASS on each) that MHS-3b leaves: 4 HumanEval/55 task memories in
        `episodic.db` (in every checkpoint and the live store) and Aschoff in `autopilot_state*.bak*`
        `last_traces`. Purge tool: orchestrator `41baad2b` (`scripts/maintenance/purge_eval_leak_memories_20260917.sh`),
        backups and receipt in `/mnt/raid0/llm/backups/episodic-leak-20260917/`.
    - [x] Offline stores and state backups purged ✅ 2026-09-17: 11 checkpoint/backup `episodic.db` copies
          (4 rows + FAISS entries each, health OK) and 15 state backups redacted. `--verify` PASS. The first run
          was cut off by a caller timeout at item 19 with no damage (the original was intact); the re-run finished.
    - [x] Live store purged ✅ 2026-09-17 during the API stop window (API down, verified): 4 memories removed,
          health OK, `--verify --include-live` PASS. The reloaded API reported 64,204 entries (was 64,208).
    - [x] Pinned production_best (multitier_v10) store ✅ 2026-09-17: purged with operator approval, 4 rows + FAISS, health OK, verify PASS incl. live+pinned.
          The new hashes are in `pinned_repin_proposal.json`. The v10 pins still name the pre-purge
          bytes until MHS-3d is ratified.
  - [x] **MHS-3d — operator RATIFY of the v10 episodic re-pin** (`RATIFY-V10-EPISODIC-REPIN-20260917`). From a host terminal: ✅ 2026-10-29 (audit: ratified: artifacts/operator/ratify_v10_episodic_repin_20260917.json + .receipt.json (emitted 2026-09-17), commit 810a6a829 'RATIFIED: v10 production checkpoint re-pinned after the HumanEval/55 eval-leak memory purge') [no-belief: audit-reconciliation]
        `docker exec -it -u node epyc-root bash -c 'bash <(git -C /mnt/raid0/llm/epyc-root show origin/main:scripts/operator/run_v10_episodic_repin_ratify_20260917.sh) --operator pestopoppa'`
        and type RATIFY. It re-pins `checkpoint_meta.json` (the three episodic file hashes and
        memory_count 63925 -> 63921; checkpoint_sha256 `a604276f` -> `3b457d98`) and the v10 receipt
        mirror, adds the amendments entries, and refuses while AutoPilot holds its lock. The dry-run
        preflight is clean against the real checkpoint. Its `--verify` supersedes the MHS-3b script's
        `--verify`, which the purge broke. Detail: `progress/2026-09/2026-09-17-sub-v10-repin.md`.
- [x] **MHS-4 — ANTI-OVERRIDE risk prior.** ✅ 2026-09-17 (landed with the AutoPilot merge train: orchestrator `8219d8e8` and `4f28e6c3` are on main via `a1a0251a`; the "pending merge" and "NOT YET ON MAIN" notes below predate that). Rank/gate mutations by CONSTRAIN (add a check, block a bad
      path, re-prompt) vs REPLACE (rewrite/force an action, hard-code an answer). In the released
      corpus the REPLACE-before-CONSTRAIN ordering holds on all 23 valid patches (REPLACE 4/4 negative,
      mean −8.4 pp; CONSTRAIN n=19, mean +3.9 pp), but the worst single patch is CONSTRAIN (−16.9 pp,
      hint-only), so the prior ranks risk and does not certify safety (MHS-5, orchestrator `4f28e6c3`);
      the trained editor converged constrain-only across all 9 patches and all 3 seeds. Encode as a
      mutation-type risk weight. `intake-1323#record` (dive actionable D4; the 2026-09-07 wording
      "every catastrophic regression came from an override" was refuted by MHS-5).
      Orchestrator `4f28e6c3` is on branch `sub/autopilot-safety-20260916`, pending merge. Zero compute. Consumer: AP-52 in
      [autopilot-continuous-optimization.md](autopilot-program.md).
      **IMPLEMENTED 2026-09-16, NOT YET ON MAIN — flip on merge** (`sub-autopilot-safety`, orchestrator `8219d8e8`, branch `sub/autopilot-safety-20260916`, unmerged): `MUTATION_EFFECT_RISK`
      (inert 0.05 < constrain 0.25 < expand 0.50 < replace 0.90 < unknown 1.0 < unsafe ∞), carried as
      `effect_risk` on both `CodeMutation` and `PromptMutation`. Prompt text is now classified too
      (`classify_prompt_effect`). `rank_mutations_by_risk()` orders candidates safest-first. The gate
      `AUTOPILOT_MUTATION_RISK_GATE` (default 1.0 refuses only unclassified effects; 0.9 means
      constrain/expand-only; it can only be tightened) runs at propose time and again at both code
      apply paths, and the proposer prompt now carries the anti-override rule. **Weights are an ordinal
      prior, uncalibrated**. MHS-5 below supports the ordering but shows CONSTRAIN is not
      regression-free. Same test file.
- [x] **MHS-5 — Mine `examples/heldout_generalization/` as a labelled contrastive corpus.** ✅ 2026-09-17 (orchestrator `4f28e6c3` on main via the train merge `a1a0251a`; the "unmerged" notes below predate that). 23
      patches, 3 editors, identical 10-failure evidence, 3 seeds, per-patch sha256, hook sets,
      validation errors, rescued/regressed counts over 1,270 held-out tasks; Apache-2.0.
      Discriminating features already extracted by the dive: effect kind, hook-set stability,
      benchmark-scaled length, rescue:regression ratio. MH-7's contrastive-trace capture is the
      existing consumer. Feeds MHS-4. `intake-1323#record` (dive actionable D7). Zero compute.
      **IMPLEMENTED 2026-09-16, NOT YET ON MAIN — flip on merge** (`sub-autopilot-safety`, orchestrator `4f28e6c3`, branch `sub/autopilot-safety-20260916`, unmerged): sparse-fetched
      Harness-R1 @ `411bb548` (the dive-verified revision). `scripts/autopilot/species/heldout_effect_corpus.py`
      derives `orchestration/datasets/harness_r1_heldout_effect_corpus.json` with labels only, no patch
      code: 27 cells, sha256-verified, effect kinds read by AST and mapped onto `MutationEffect`, plus
      hooks, code length, delta, and rescued/regressed counts. **Result (23 valid patches):** the MHS-4
      ORDERING holds. All 4 REPLACE patches regressed (mean −8.4 pp, rescue:regression 0.21); the 19
      CONSTRAIN patches averaged +3.9 pp (1.65). **But the claim "every catastrophic held-out
      regression came from an override patch" does NOT hold on this corpus.** The single worst valid
      patch (DeepSeek-V4-Pro alfworld seed 20260721, −83 on 490 = −16.9 pp, 130 regressed) is
      hint-only (`inject_hint`). A block-only patch also lost 34 (−6.9 pp). 4 of 19 CONSTRAIN patches
      regressed. Confound: 9 of the 19 CONSTRAIN patches come from the trained Harness-R1 editor.
      Consequence: the MHS-4 weights stay ordinal; the gate ranks risk, it does not certify safety
      (code comment and operator guide updated). **Belief-kernel note — APPLIED 2026-09-16 (`sub-own`):** the refuted text was
      the MHS-4 row's own rationale, not key claim 04 of the entry (the handoff's `#NN` numbers indexed
      the dive actionables ledger, so `#04` was a mis-anchor; claim 04 is the true transductive-scope
      claim). Recorded in `research/intake_index.yaml` (`intake-1323#record`) as `dive_corrections` item (13) and
      a `dive_entry_corrections` row (effect `narrowed` on dive item (6)); claim 04's `claim_corrections`
      note re-examined, still `unaffected`. Evidence cited as orchestrator `4f28e6c3` on
      `sub/autopilot-safety-20260916` (pending merge), corpus sha256 `09ae7365…efbc71`. The MHS-4 row now
      cites `intake-1323#record` with the qualified wording. `tests/unit/test_heldout_effect_corpus.py` (15 tests) pins
      both the ordering and the refutation. MH-7 wiring was not done (out of scope for this row).
- **[declined: ws58 2026-11-03 content-review: a record with no work, by its own text]** **MHS-6 (record, no work) — Optimizer budget shape.** Record it as **"constant in training-set
      size, LARGE constant"**: 1 + T_ReAct calls/iteration, T_ReAct 10–20 at B = N_train ⇒ 11–21
      metered calls, vs EvoSkill 2N/B and SkillOpt K_opt·N/B (K_opt 6–8). At our split sizes this is
      **more** absolute calls. The completed file's pointer to
      `handoffs/active/meta-harness-optimization.md` is DANGLING — that file does not exist — which is
      why this stub, not a reopen, is the right shape. `intake-1317#03`. Zero compute.
- [x] **MHS-7 — force the isolated mutation path.** `apply_code_mutation` writes the live tree directly ✅ 2026-10-31 — implementation APP `c91884ee5a38f7b4a2168c76fee1394a867e2e33`; `tests/unit/test_worktree_manager.py` and action controls; Git-retained proof `artifacts/audit/mhs7-isolated-mutation-20261031/` in APP main `a3c00d206a75044a2c01d67498f7bb633084eb0c` (433 focused tests, 162 correction controls). Existing transaction overlays main for evaluation; ordinary rejection/exception restores the preimage. [no-belief: deterministic mutation/commit safety controls; no measurement]
      (git-checkpointed) and the isolated `apply_code_mutation_in_context` exists but nothing requires its use
      (`scripts/autopilot/species/prompt_forge.py:~1440`) (found 2026-09-14, noninf sweep).
- [ ] **MHS-8 — tighten the apply gate to "only screened effects apply"**, since only `MutationEffect.UNSAFE`
      is refused today so `UNKNOWN` — the default on a hand-constructed `CodeMutation` — still applies; needs
      an audit of every construction site (`scripts/autopilot/species/prompt_forge.py`, apply gate)
      (found 2026-09-14, noninf sweep).
- [x] **MHS-9 — narrow `revert_code_mutation`'s new-file revert from `git add -A <path>` to an explicit ✅ 2026-10-29 (audit: orch 25c8e913 (2026-09-16, 'no commit sweep'): revert_code_mutation new-file path now calls _git_commit_paths([abs_path]) = git add -A -- <explicit pathspec> + commit --only (prompt_forge.py:1152,1466)) [no-belief: audit-reconciliation]
      pathspec**, the idiom the project's hygiene rules warn about
      (`scripts/autopilot/species/prompt_forge.py:~1478`) (found 2026-09-14, noninf sweep).
- [x] ✅ 2026-10-31 **MHS-10 — land a standalone formatting commit for `prompt_forge.py`**. Evidence: orch `86f9985e97f010c3a9702b5f923a6d793159ef3c`; `/mnt/raid0/llm/tmp/refactor-01a16fc3/mhs10-format-20261031/QUALIFY-R3.log` and `PROMOTION.json` in that directory. [no-belief: formatting-only change; identical type-comment AST, Ruff checks and 260 existing tests pass]
      Resolved the prior formatting dirt on
      `origin/main` (`ruff format --check` fails on a pristine clone), so future diffs stay readable
      (`scripts/autopilot/species/prompt_forge.py`) (found 2026-09-14, noninf sweep).
- [x] ✅ 2026-11-01 **MHS-11 — replace the operator guide's `prompt_forge.py` line-number citations with symbol names**,
      since `line 575` / `line 594` / `line 509` are already stale by hundreds of lines
      (`docs/guides/meta-harness-operator-guide.md`) (found 2026-09-14, noninf sweep). APP implementation `25d4bc71351437b45d400c36e986b502d94c3c5c`; artifact `artifacts/engineering/mhs11-promptforge-guide-20261101/VALIDATION.txt`; [no-belief: documentation-only]
- [x] **MHS-12 — eval-identity screen for code_mutation.** Refuse (MutationEffect.UNSAFE with reason) any mutation whose ADDED code reads workload_class, scoring_method, batch_id, request-metadata suite/tier keys or the literal "eval_batch", or removes/overrides force_role handling, in any allowlisted file. Grandfather existing references the way MHS-2 grandfathers imports. Fixtures: a chat.py mutation branching on workload_class == "eval_batch" is refused; a no-op chat.py mutation passes. Partly answers Open Question 2 (key on eval-identity fields, not only suite/task names). intake-1387#record. ✅ 2026-10-31 — APP implements `f579bcf92f2b11904176f662f6f6d06ed96947fe`; test `tests/unit/test_prompt_forge_eval_identity.py`; Git proof `artifacts/audit/mhs12-eval-identity-20261031/verification.md`. [no-belief: source implementation and native regression controls]
      ✅ 2026-10-31 — Implemented in epyc-orchestrator `f579bcf92f2b11904176f662f6f6d06ed96947fe`
      (`src/autopilot_core/mutation_guards.py`, `scripts/autopilot/species/prompt_forge.py`). Static AST
      delta screening flags added eval-identity reads and force-role removal/override while
      grandfathering existing references by expression, context and multiplicity; comments, docs and
      write-only matches are excluded. Scope-local forced-role handling covers early exits, false
      wrappers, selected receivers, setattr/delattr and grandfathered guarded calls. Native PromptForge
      screening emits `MutationEffect.UNSAFE` with reason before generic shrink/missing-name REPLACE handling;
      prior precedence for other cases is preserved and the screen is cached once. Native propose,
      action and apply paths reject before evaluation or writes. The final suite has 163 controls,
      including 57 new, with zero touched-file lint findings. The earlier broad run (272 passed, one
      documented baseline failure) was tied to the pre-delta hash and is not the final full-suite claim.
      `make` gates used fixture context and are not a full-repository failure. Evidence:
      `artifacts/audit/mhs12-eval-identity-20261031/verification.md`. Scope limits: no dynamic-alias or
      whole-program security proof; conservative benign changes may be refused. No live activation,
      threshold change or grade is claimed. [no-belief: source implementation and native regression controls]
- [x] **MHS-13 — Scoped-propose plus KEEP_BASE composer for PromptForge: design addendum (spec only; no run; HIL P0.4 ordering applies).** Two scoped candidates per mutation (a process lens and a domain lens, each told not to touch the other's dimension) and a composer that may merge, revise, adopt one or return KEEP_BASE, writing decision lines 'kept/revised/dropped -> edit -> evidence(count)' in which every kept edit names the trajectory moment that motivated it; an invalid proposal is retried once and then the stage inherits the parent. Include a structural pre-flight validator row (valid candidate or inherit; trigger line present; no template braces; referenced scripts exist) and compare each rule with the existing guards first (`mutation_extraction_failed`, `_UNIVERSAL_TRANSFER_RE`, `_prompt_integrity_reason`, MHS-2, MHS-3, MHS-4), dropping what they already cover. State which AP-54 and AP-55 helpers each stage reuses. Adoption is decided only by the PromptForge promotion gate and P-AB-1, never by the contrast between candidates; agreement among candidates is support, not independent proof (`intake-1995#01`, `intake-2148#00`, `intake-2148#06`); the published ablation is a single configuration (`intake-1995#record`). ✅ 2026-10-20
- [x] **MHS-14 — Mutation-record falsifiability fields and activation beacon for PromptForge (spec only; no run).** One optional annotation on the `PromptMutation` record (`scripts/autopilot/species/prompt_forge.py:296-310 @5d4ad2c0`): the trigger condition under which the edit fires; predicted fixed tasks and predicted at-risk tasks; an attribution signature (the trace feature that must appear if the edit fired); a no-trigger control slice on which output must be byte-identical or within a declared noise floor; `evidence_used` and `verification_checks` (how to confirm next iteration); and a deterministic activation beacon with a per-task fire count, where zero fires means uncredited, not harmless; the no-trigger control slice is what bounds a presence effect and it is required for any edit that stays resident in the prompt (`intake-1321#record`). Log observed versus predicted in the journal row of an accepted mutation (AP-53 holds rejected mutations only, `rejected_mutation_ledger.py:91-131`) and in the AP-53 record of a rejected one; the default-off `mutation_author_capture` hashes are the existing hash-level `evidence_used`. Compared first with MHS-3 (leakage in added text), MHS-4 (edit-class risk prior) and AP-55 (regime comparability): none records a predicted effect, a trigger, a locality control or fire counts. Protocol-bearing wording is a MEASUREMENT.md section 5 candidate, not applied (`intake-2145#04`, `intake-2165#00`, `intake-2166#00`, `intake-2146#05`, `intake-2176#03`). ✅ 2026-10-20
- [x] **MHS-15 — Warn-only, delta-only prompt interference lint for PromptForge mutations (pure function; never a reject).** Add `prompt_interference_lint(original, mutated)` in `prompt_forge.py` next to `_prompt_integrity_reason` (`:907 @5d4ad2c0`; the HIL-3 import-safe guard module does not exist yet, so the later extraction moves it with its siblings), reporting findings present in the mutated text and absent in the original: (a) verbatim duplicate lines or blocks, (b) MUST or ALWAYS versus NEVER or DO NOT sharing a scope noun, (c) conflicting priority markers, (d) the count of in-context examples the mutation adds (a deterministic bloat check; an LLM leakage judge is not adopted, an LLM judge is not a measurement). Findings go to `PromptMutation.safety_warnings` (`:306`; nothing reads that field today) and must also be surfaced in the journal `eval_details` or the AP-53 record, otherwise the lint is write-only. Acceptance: original equal to mutated yields zero findings on every file in `orchestration/prompts`; a fixture appending 'NEVER use X' beside an existing 'ALWAYS use X' is flagged; a fixture adding six examples is flagged. Then run the lint once in whole-file read-only mode over `orchestration/prompts` and record per-rule counts as the calibration baseline (13 of the 21 headline findings in the source were minor scope overlaps, so the false-positive rate must be known before the lint is trusted), filing any genuine contradiction as a prompt fix (`intake-2155#00`, `intake-2155#04`). How our served models resolve ALWAYS-versus-NEVER is unknown and is a monitor (M8), not part of this task. ✅ 2026-10-21
  - 2026-10-21 (noninf-gates) result. `prompt_interference_lint(original, mutated)` added beside `_prompt_integrity_reason` in `scripts/autopilot/species/prompt_forge.py` (epyc-orchestrator `29d66c27`, on origin/main). Rules: `duplicate`, `directive_conflict` (MUST/ALWAYS vs NEVER/DO NOT sharing a content word), `priority_conflict`, `examples_added` (threshold 3). Warn-only; appended to `PromptMutation.safety_warnings` after the verdict so it cannot change validity. Surfaced in AP-53 records (`interference_warnings`, additive) and in journal `eval_details.prompt_interference_warnings` via a new ctx.state key. GEPA proposals do not run `_attach_transfer_safety`, so they are not linted (open gap).
  - 2026-10-21 (noninf-gates) GEPA gap closed (epyc-orchestrator `ea820af8`): `_propose_via_gepa` now runs the same warn-only lint on valid proposals and the GEPA handler stashes the findings for `eval_details`; test `test_gepa_proposal_gets_the_warn_only_lint`; 272 prompt-forge tests and 163 actions tests pass.
  - Acceptance: `tests/unit/test_mhs15_prompt_interference_lint.py` (7 pass): original==mutated gives zero findings on every `orchestration/prompts/**/*.md` file; the NEVER-beside-ALWAYS fixture and the six-example fixture are flagged; pre-existing conflicts are not re-reported. 50 related unit tests pass.
  - Calibration (`scripts/autopilot/prompt_interference_calibration.py`, whole-file read-only, each file vs an empty original, 26 files): duplicate 2, directive_conflict 1, examples_added 1. Samples: duplicates are a template line in deep_search_agent.md and a code line in rules.md; the one directive_conflict (report_agent.md, shared word `report`) is a scope overlap, not a contradiction; examples_added is rules.md (13 example headings, legitimately example-heavy). No genuine contradiction found, so no prompt fix filed. Rule (b) matches on a single shared word, which is the false-positive source the task text warned about.
- [x] **MHS-16 — Cumulative-drift report over accepted ships (read-only; no gate change).** Verified 2026-10-20: `safety_gate.py` judges each ship against its predecessor (the tier baseline is overwritten at every promotion by `update_tier`, `scripts/autopilot/safety_gate.py:1533-1576 @5d4ad2c0`), checks only the aggregate (-5 percent) and per-suite deltas, and has no per-question passed-to-failed flip count and no same-bucket edit-concentration check. Build a report that replays journal rows with `keep_revert_decision == "keep"` (per-question vector in `eval_details.question_results`) together with the `baseline_promotion` events (`src/autopilot_core/baseline_ledger.py`) and reports, against the era's SEED baseline profile rather than the predecessor: per-question passed-to-failed flips, the cumulative per-suite delta, and the length of runs of consecutive promotions sharing one (mutation_type, target) bucket; add a warn-only same-bucket concentration flag. AP-53 holds rejected mutations only, so it may be annotated for rejects only. Changing what counts as a ship is human-amendment territory and out of scope (`intake-2166#02`, `intake-2166#03`, `intake-2164#00`). Frozen input: the journal snapshot digest; denominator: every keep row, rows lacking question_results counted separately and not dropped; decision rule: report only. ✅ 2026-10-21
  - 2026-10-21 (noninf-gates) result. `cumulative_drift_report` in `src/autopilot_core/sequential_replay.py`, run by `scripts/autopilot/gate_replay_reports.py` (epyc-orchestrator `ea8c7338`). Frozen input: journal snapshot sha256 `6bb790ba837c9ea23f9e6ebd1a8ff00e354baf196ec7fe830d02dd54fc8c5b4a` (autopilot_journal.jsonl 18257825 B + autopilot_journal_1.jsonl 19801823 B; 1372 rows). 229 keep rows; 146 have no `question_results` (counted, not dropped). Seed = first 3 vector-bearing keep rows per tier (no per-question seed profile is journaled; stated in the report).
  - Tier 1 (105 keep rows, 22 without vectors): seed trials 790, 791, 802; 80 rows compared; 63 rows with at least one passed-to-failed flip against the seed; max 2 flips in one row; 2 distinct questions ever flipped; longest same-bucket run 19, 15 runs of length 3 or more (warn flag set). Tier 0: 123 keep rows, none with vectors, longest run 36. Tier 2: 1 keep row. The journal ends 2026-08-09, before the quality-era boundary (1786378983.88 = 2026-08-10), so there is one era. Bucket here is (action_type, file/target) and most keep rows are `seed_batch`/`numeric_trial`, not mutations; only 5 are `prompt_mutation`. Per-suite cumulative deltas are in the report JSON. Report only; no gate change.
- [x] **MHS-17 — Predicted-effect calibration readout and the zero-fires wording fix (extends MHS-14).** (a) Read-only scoring function over journal and AP-53 predicted-versus-observed rows: deterministic per-mutation verdict by set intersection of predicted_fixed and predicted_at_risk with the observed fail-to-pass and pass-to-fail sets (no LLM); per-round precision and recall for fixes and for regressions, each beside a random-prediction baseline computed from panel size and observed flip rate; an explicit `unattributed regressions` list (intake-1132#record: at-risk prediction was near random, so it cannot be the regression screen). (b) Amend the MHS-14 sentence to read: zero fires means uncredited, not harmless; the no-trigger control slice is what bounds a presence effect and it is required for any edit that stays resident in the prompt (intake-1321#record). Acceptance: the scorer has fixture tests on a synthetic ledger and the MHS-14 sentence is replaced. Estimate: 1.5 days. ✅ 2026-10-21
  - 2026-10-21 (dpf-gates) result. (a) `scripts/autopilot/predicted_effect_calibration.py` (epyc-orchestrator `44d63a0b`): per-mutation verdict by set intersection of predicted_fixed and predicted_at_risk against observed fail-to-pass and pass-to-fail; per-round precision and recall for fixes and regressions beside a random baseline (k*F/n expected hits from panel size and observed flip count); explicit `unattributed regressions` list; unannotated rows counted not dropped. Fixture tests on a synthetic ledger: `tests/unit/test_mhs17_predicted_effect_calibration.py` (7 pass). No real readout exists: MHS-14 fields are not yet journaled. (b) The MHS-14 sentence is replaced (MHS-14 now reads: zero fires means uncredited, not harmless; the no-trigger control slice is required for any resident edit).

*Declined 2026-09-14: repoint the dangling pointer at `handoffs/completed/meta-harness-optimization.md:3` —
not filed because it is already recorded as the **Housekeeping rider (E0, owned elsewhere)** in this file's
Notes and named inside the open **MHS-6** box.*

**Cost yardstick (DERIVED-FROM-CONFIG, never a measurement)**: *"one engineer update ≈ one full sweep
of your eval suite"* — a reusable rule of thumb for pricing ANY outcome-grounded editor loop. It kills
this class of proposal on this host before anyone builds a design doc. `intake-1323#record` (dive actionable D9; handoff half;
the wiki half is queued for the compilation sweep).

#### Open Questions

1. Does the effect enum (MHS-1) need a per-mutation-site vocabulary, or is one closed host-wide enum
   sufficient for PromptForge's mutation sites as they exist today?
2. Does the anti-leakage pattern set (MHS-3) key on suite/task identifiers only, or also on fixture
   content hashes — and does the latter create its own maintenance surface?
3. Is the CONSTRAIN/REPLACE classification (MHS-4) derivable mechanically from the MHS-1 effect enum,
   or does it need a separate label?

#### Notes

- All six rows are **zero compute**. Nothing here requires inference, a model load, or an eval run.
- Dependency order: **MHS-1 → MHS-2**; **MHS-5 → MHS-4**.
- Index: this stub needs a new row in `routing-and-optimization-index.md` at the next free ID
  **RTG-55** — verify against `handoffs/archived/routing-and-optimization-index-history-*` before
  assigning, since retired IDs are never reused. **Row is PREPARED here; the owning session APPLIES.**
- Housekeeping rider (E0, owned elsewhere): the dangling pointer at
  `handoffs/completed/meta-harness-optimization.md:3` should be repointed at this stub or the clause
  deleted.

The [five execution-alignment triage labels](../../docs/reference/agent-run-failure-triage.md) provide descriptive failure-trajectory vocabulary for MHS-5 consumers. They are metadata, not held-out outcome grades or patch-safety predictions.

#### Research Intake Update — 2026-10-20 (harness cluster)

Operator-approved 2026-10-20 via research intake (plan sha256 1dc83054706ca0bae002602307b0d9ba6435b010be4d6ffd8a495a04605f3967). Monitor and knowledge records below are prose: no checkbox, no index next action.

- **M8 (monitor, 2026-10-20) — PromptForge guard follow-ons (additive-selection retest, LLM neutral reader, ALWAYS/NEVER severity probe, CONSTRAIN risk weight, gene-bank archive, cross-framework skills, unresolved-gaps list, saturated-suite skip, parent-in-pool selection, back-translation, proposer-spend review, red-team of our proposer).** Trigger: The named condition in each bullet (for example: the lint fires on a promoted CONSTRAIN mutation; MHS-7, MHS-8 and MHS-12 closed plus an idle window; AutoPilot runs several live configurations in one window). First step when it fires: Do the named step. No immediate step remains: Each is gated on an event that has not happened; MHS-15 covers the part that needs no event.
- **K4 (knowledge, 2026-10-20) — Gate-design confirmations and checks already done (guards fail closed; PACE subsumed by seq-v1; Two-Gate vacuous at our n; MHS-3 covers the literal-leak guard; REPL-EMB-2.1/2.2 already hold the lexical baseline; AU3 similarity floor exists; AP-54 scope; EGL not implemented; parallel_dispatch compared).** Retained use: Prevents re-filing the same checks.

## Track: lab-reliability-ladder

> Moved from `frontier-lab-automation.md` § Track: frontier-f2-self-running-lab on 2026-11-09 (operator, workspace-f2). Resume when the AutoPilot loop is relaunched: model-backed shadow jobs need the serving stack, which has been down by operator decision since about 2026-11-07. History and evidence stay in that handoff's progress log.

- [ ] **W3 — reliability ladder** (ongoing): `scripts/lab/promote_job.py` enforcing shadow → reviewed → autonomous from logged stats (shadow ≥10 runs scored vs a cloud-reference run; autonomous only for read_only report-class jobs at ≥90% accept-rate over 20 reviewed runs) — acceptance: promotion only via the script; every (input, local output, cloud reference, verdict) tuple saved as F3 gold data. **Gate scaffold landed current branch 2026-06-14**: cherry-picked from branch-ready `775d230`/`78f9b93` into `epyc-orchestrator` `5ab007f`/`bad8bb9`, adding promotion evaluation/reporting over `lab_task_record.v1` + `lab_review_verdict.v1`, cloud-reference/gold-tuple requirements, read-only autonomous restrictions, guarded jobs-file mutation, and `scripts/lab/record_verdict.py` for `lab_gold_tuple.v1` rows. **Promotion-ladder hardening landed 2026-07-06**: `epyc-orchestrator` `9ca7061c` now rejects stage skips/downgrades, requires operator-reviewed evidence for autonomous promotion, and requires referenced F3 gold tuple files to exist when evaluating from the queue path. Remaining W3 acceptance: collect real shadow/reviewed verdicts and use the script as the only promotion path. Operator 2026-11-07: keep open — nightly accumulation continues (≤2 of 10 scored shadow verdicts per job so far).
