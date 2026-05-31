# Routing & Optimization — Coordination Index

**Created**: 2026-03-25
**Purpose**: Actionable entry point for agents working on routing, optimization, and stack infrastructure. Read this first — it tells you what needs doing, in what order, and where to find the details.

---

## How to Use This Index

1. **Read the outstanding tasks below** — they are ordered by priority and dependency
2. **Check the dependency graph** — some tasks unblock others
3. **Read the relevant handoff** for implementation details before starting work
4. **After completing a task**, update both the handoff AND this index (mark task done, update status)
5. **Check cross-cutting concerns** before modifying any subsystem — changes cascade

---

## Standing Comparative Context

Before proposing or revising routing/coordination architecture, read [`research/deep-dives/trinity-evolved-llm-coordinator-methodology.md`](../../research/deep-dives/trinity-evolved-llm-coordinator-methodology.md) (intake-474, ICLR 2026, Sakana AI). Trinity is the most direct prior art for the lightweight-learned-coordinator-over-heterogeneous-pool thesis we are pursuing. The deep-dive cross-checks Trinity's choices against ours on architecture, training signal, optimizer, action space, and pool composition — and lists the portable lessons (tri-role action space, sep-CMA-ES cold-start, block-ε-separability diagnostic, SVD-FT) and the non-portable ones (penultimate-token finding, frontier-closed-pool gain numbers). Reference it explicitly when arguing for a routing-architecture change so we know which Trinity lever the change does or does not echo.

**Routing/coordination design-space reference points (added 2026-04-28)**: four published systems anchor the current research landscape for learned routing and coordination heads:

- **BaRP** (intake-495, arxiv:2510.07429) — bandit-feedback training + 2-D preference-vector conditioning. **EPYC adopts patterns** at DAR-3 (motivation), DAR-4b (preference vector + cost τ), and via the routing-policy lens.
- **LLM Bandit** (intake-496, arxiv:2502.02743) — IRT score predictor + model identity vectors + IRT-stratified cold-start onboarding. **EPYC adopts patterns** at LRC P4.1.3 (P19.9, IRT feature audit), LRC P5 (P19.10, IRT-stratified cold-start), and DAR-5.
- **Trinity** (intake-474, arxiv:2512.04695) — sep-CMA-ES on a 0.6B SLM + 10K head with tri-role `(LLM, role)` action space. **EPYC tracks selectively** — tri-role architectural change (P19.1) is a real candidate; sep-CMA-ES is the realistic CPU-feasible escalation path if DAR-3/4 underdeliver.
- **Conductor** (intake-493, arxiv:2512.04388) — 7B GRPO-trained coordinator emitting `(worker_id, NL_subtask, access_list)`. **EPYC treats as competitive intelligence ONLY** (NOT a target architecture; OC-0.6 captures the comparison row, with explicit "what to learn from / what NOT to copy" framing). GPU-class architecture, out of CPU stack.

When making a routing-architecture proposal, name which of these four (and which Trinity lever from the deep-dive) the proposal echoes — and which it deliberately does not. Closure-inflation discipline applies: do not generalize "Conductor's 7B is out of scope" into "no learned coordinator could ever work" — the four systems are distinct points, not a single architecture.

---

## Subsystem Status

| Subsystem | Handoff | Status | Next Action |
|-----------|---------|--------|-------------|
| Routing Intelligence | [`routing-intelligence.md`](routing-intelligence.md) | **COMPACTED 2026-05-28** — Phases 0-5 history moved to completed ledger; RI-10 canary remains the live decision | Pull current canary sample counts → RI-10 decision → RI-11/RI-12 only if no regression |
| AutoPilot / AutoResearch | [`autopilot-continuous-optimization.md`](autopilot-continuous-optimization.md) | **RUNNING — restart validated 2026-05-31 ~22:53** (planner-context meta-loop fixed `dcfc9eb` B/A/C: `reproduction_confirmed` semantic split + benign-exclusion decouple + durable `paused` halt + attribution guard; runtime poison pruned; tier-seg `c75b69d..f031e33` integrated on top). Planner pivoted off the spiral to a real `numeric_trial` on first turn; `--max-trials 300`, bg pid 3740635. See handoff banner. | Monitor toward trial 300 (honest T1 frontier best, not saturated T0 `2.400`); watch credits (`out_of_credits`/overage-rejected but `status:allowed` in 5h window). Deferred: host-health auto-remediation on regression. |
| Stack Startup NUMA Prewarm | [`numa-page-cache-prewarm.md`](../completed/numa-page-cache-prewarm.md) | ✅ **COMPLETE 2026-05-29** (archived) — codified `[1.5]` page-cache prewarm passed cold-cache P5; previously-collapsed shared GGUFs are ~25% per NUMA node, 27.3 s cold prewarm time | Monitor future cold starts for regression; re-open the archived handoff if symptom recurs |
| Dynamic Stack | [`dynamic-stack-concurrency.md`](dynamic-stack-concurrency.md) | **COMPACTED 2026-05-28** — Phases B-D complete; DS-6/DS-7 design ledger split to completed history | DS-E1 evidence packet → DS-7 profile codification; DS-6 only if evidence proves static pre-warm insufficient |
| Within-Role Placement + KV Migration | [`within-role-placement-state-machine.md`](within-role-placement-state-machine.md) | **WP-0/WP-1/WP-2/WP-3/WP-4/WP-5-scaffold IMPLEMENTED 2026-05-26** MERGED TO MAIN (`epyc-orchestrator` merge `fe6805c`; tip now `15350fe`; 155/155 dispatcher-adjacent tests at merge). WP-2/WP-3/WP-4 ship behind env flags (ORCHESTRATOR_PLACEMENT_STATE_MACHINE, ORCHESTRATOR_REVERSE_MIGRATION) defaulting off; WP-0/WP-1/WP-5-scaffold are live. WP-3 dropped the speculative load-transition trigger (could not preempt mid-decode); shipped transactional MigrationTransaction + policy gating + migration_budget_ms threading on the existing session-handover trigger. | **WP-6 / WP-7 / WP-5 full ratification** — all inference-gated, awaiting operator approval + measurement. WP-3/WP-4 gate verifications also inference-gated. |
| Cross-Role Contention + Placement | [`shape-keyed-contention-gating.md`](shape-keyed-contention-gating.md) | **A/A-1 + B CODE-COMPLETE END-TO-END; C prep only. Remaining = rollout-only, no code.** Step 1 (GLOBAL region mutex) staged at `orchestrator_stack.py:1121` default but API NOT reloaded (live autopilot). Step 2 (dispatch-side caller passes real `candidate_topology_idx`) DONE 2026-05-31 — `inference.py` defers coarse pre-gate, `concurrency_aware._dispatch` gates per-candidate, `contention_gate.admit()` threads idx; 146-test suite green. Both shape-aware flags still default off → inert. C only has pure `select_backfill_candidate`; heavy veto/barrier/pressure-skip untouched. | Rollout: (1) after autopilot wraps, reload to arm Step 1; (2) observe blocked-pair/wait/throughput + verify dashboard attribution survives GLOBAL lock; (3) flip `SHAPE_AWARE_CONTENTION=1` after live smoke (disjoint admit / overlap queue); (4) switch A placement to exact-region snapshot; (5) C behavior changes under an epoch boundary. |
| KV Cache Quantization | [`kv-cache-quantization.md`](../completed/kv-cache-quantization.md) | COMPLETE — Hadamard deployed, TQ/PQ abandoned | Historical reference; monitor upstream TurboQuant from inference index |
| Context Folding | [`context-folding-progressive.md`](context-folding-progressive.md) | **COMPACTED 2026-05-28** — core phases and Phase 2d preserved in completed ledger. | CF-L5 max-compression validation, CF-3c live quality-monitor validation, CF-2c.0 alpha sweep, CF-DD8 gap analysis. |
| Conversation Management | [`orchestrator-conversation-management.md`](../completed/orchestrator-conversation-management.md) | COMPLETE (B1-B7 + integration) | Historical reference |
| LangGraph Migration | [`langgraph-migration.md`](../completed/langgraph-migration.md) | COMPLETE / historical migration infrastructure | Historical reference; reopen only for a fresh LangGraph migration push |
| ~~CC Local Integration~~ | ~~[`claude-code-local-constellation-routing.md`](../archived/claude-code-local-constellation-routing.md)~~ | ARCHIVED — superseded by Hermes outer shell | — |
| Retrain Routing Models | [`retrain-routing-models.md`](retrain-routing-models.md) | **BLOCKED 2026-05-25** after episodic-memory reset invalidated classifier/GAT/SkillBank artifacts | Wait for ~500+ fresh routing memories, then retrain classifier, GraphRouter, and SkillBank; also listed in [`../blocked/BLOCKED.md`](../blocked/BLOCKED.md) |
| Meta-Harness Optimization | [`meta-harness-optimization.md`](meta-harness-optimization.md) | **COMPACTED 2026-05-28** — Tier 1/2, MH-4/5, and HLE-1/2 preserved in completed ledger. | MH-6/7/9 plus HLE-3/J9 observe-only validation; Tier 3 outer loop remains deferred. |
| Web Research Pipeline | [`searxng-search-backend.md`](searxng-search-backend.md) | SX-1–4 done; CA-1–5 ready now; SX-5/6 + CA-6/7 gated on AR-3/Camofox. Claude Code bash bridge moved to completed: [`searxng-bash-websearch-bridge.md`](../completed/searxng-bash-websearch-bridge.md). | CA-1–5 (Crawl4AI steps 2+3) can start independently; runtime/container activation stays here |
| Internal Interaction Lifecycle | [`internal-interaction-lifecycle.md`](internal-interaction-lifecycle.md) | **NEW 2026-05-31** — A2A-style `Interaction` abstraction (delegate / consult / verify / route) replacing implicit delegation loop shape; consult sibling for "advise vs delegate" pattern; sibling `interaction_skills.yaml` for typed skill contracts | P1 lifecycle refactor (no behavior change) — confirm 4 P2 open decisions and first consult site (`worker_general` → `architect_general` `review_before_commit`) |
| Decision-Aware Routing | [`decision-aware-routing.md`](decision-aware-routing.md) | NEW — 4-phase experiment (regret → contrastive → SPO+ → bilinear) | DAR-1 offline regret analysis (no code changes) |
| Learned Routing Controller | [`learned-routing-controller.md`](learned-routing-controller.md) | Phase 1 P1.1-P1.4+P1.6 DONE — 92% val acc, per-class thresholds calibrated | P1.5 enable flag, Phase 1.5 logit probe |
| Environment Synthesis (5th species) | [`agent-world-env-synthesis.md`](agent-world-env-synthesis.md) | NEW 2026-04-22 — stub/in-planning; Phase 1 training-free, Phase 2 GPU-gated (intake-444, DD6) | AW-1: scaffold `env_synth/` module |
| Deep Research Mode | [`minddr-deep-research-mode.md`](minddr-deep-research-mode.md) | REFRESHED 2026-05-28 — Phase 1 scaffold landed; MD-9 A/B is the live gate; Phase 2 GPU-gated | MD-9: sentinel A/B with EV-9 rubric if available; keep dispatcher wiring deferred until pass |
| Tri-Role Coordinator | [`tri-role-coordinator-architecture.md`](tri-role-coordinator-architecture.md) | REFRESHED 2026-05-28 — TR-1/2/3.1/3.2 landed; TR-3.3/3.4 telemetry gates next | TR-3.3: collect >=1 week role-shadow telemetry; TR-3.4 non-degenerate distribution check |
| Outer-Coordinator Learned Head | [`outer-coordinator-learned-head.md`](outer-coordinator-learned-head.md) | REFRESHED 2026-05-28 — SCOPING/PARKING ONLY; no implementation until dependency gates or measured Claude-loop bottleneck | OC-0 only when triggered by measured ROI; archive as not_pursued if replaceable token fraction <20% |
| ~~Stack Audit~~ | ~~[`orchestrator-stack-audit.md`](../completed/orchestrator-stack-audit.md)~~ | ARCHIVED 2026-03-29 | Purpose fulfilled by NUMA + REAP deployments |

---

## Outstanding Tasks (Priority Order)

### P0 — Wiring Bugs (infrastructure built but not connected)

These are HIGH priority because the code exists but isn't wired up. Low effort, high value.

- [x] **STACK-0: NUMA page-cache prewarm before server launch** — COMPLETE 2026-05-29. `scripts/server/stack_commands.py::cmd_start` now runs `[1.5] Page-cache prewarm` over the post-filter launch set, deduped by inode, with an emergency skip flag. Cold-cache P5 passed: 120.1 GiB warmed in 27.3 s, affected shared GGUFs split ~25% per NUMA node, latest checked autopilot trial 123 at 66.74 aggregate t/s. See [`numa-page-cache-prewarm.md`](../completed/numa-page-cache-prewarm.md).

- [x] **AP-1: Wire `failure_context` into PromptForge dispatch** — ✅ 2026-03-29. `dispatch_action()` now extracts last 5 PromptForge failures from journal and passes `failure_context` + `per_suite_quality` to `propose_mutation()`. Also added `journal` parameter to `dispatch_action()`.

- [x] **AP-2: Feed failure narratives into controller prompt** — ✅ 2026-03-29. `summary_text()` now appends compact failure analysis (truncated to 200 chars) for failed trials. Controller can see why trials failed.

- [x] **AP-3: Populate `parent_trial` and `config_diff` journal fields** — ✅ 2026-03-29. `parent_trial` set to most recent trial from same species. `config_diff` computed as key-level delta between current and parent config_snapshot.

- [x] **RI-0: Fix Q-scorer frontdoor baseline** — ✅ 2026-03-29. Updated `baseline_tps_by_role`: frontdoor 19.6→12.7 (moe6, no lookup), architect_coding 7.0→8.0 (REAP-246B). Also updated `memory_cost_by_role` for architect_coding: 5.0→3.5 (139GB vs 271GB).

### P1 — Routing Intelligence Phase 4 (risk-aware enforcement)

Phases 0-3 built the risk scorer and put it in shadow mode. Phase 4 makes it affect routing decisions. **Prerequisite**: calibration dataset (labeled prompts with known risk levels — source from simpleqa failures + seeding diagnostics).

- [x] **RI-1: Build calibration dataset** — ✅ 2026-03-29. `build_factual_risk_calibration.py` extracts 2,000 labeled examples (1,314 high, 616 low, 70 medium) from seeding_diagnostics.jsonl (781 with eval ground truth) + question_pool.jsonl (1,219 tier-based). Output: `orchestration/factual_risk_calibration.jsonl`.

- [x] **RI-2: Cheap-first risk bypass** — ✅ 2026-03-29. `_try_cheap_first()` now returns `None` (skip) when `routing.factual_risk_band == "high"`. High-risk factual prompts go directly to normal pipeline.

- [x] **RI-3: Plan review gate risk integration** — ✅ 2026-03-29. `_plan_review_gate()` forces review when `factual_risk_band == "high"` AND `factual_risk_mode == "enforce"`, regardless of complexity heuristics.

- [x] **RI-4: Escalation policy risk-awareness** — ✅ 2026-03-29. `EscalationPolicy.decide()` triggers think-harder on FIRST failure (not penultimate retry) when `risk_band == "high"` and `risk_score > 0.5`. Early deep thinking is cheaper than multiple shallow retries.

- [x] **RI-5: Failure graph veto modulation** — ✅ 2026-03-29. Factual risk scoring moved BEFORE failure graph veto. Threshold modulated: high→0.3, medium→0.5, low→0.7 (was hardcoded 0.5). High-risk prompts trigger more conservative specialist vetoing.

- [x] **RI-6: Structured review objective** — ✅ 2026-03-29. Both progress log and MemRL episode storage now include `task_type`, `risk_band`, `verification_focus`. Feedback truncation raised from 100→200 chars.

- [x] **RI-7: A/B test Phase 4** — ✅ 2026-03-31. Ran 70 questions per arm (10/suite × 7 suites). Results: all differences NS (p > 0.4). Direct: off 61.4% vs enforce 62.9% (p=0.86). REPL: off 48.6% vs enforce 42.9% (p=0.50). Architect: off 55.7% vs enforce 52.2% (p=0.68). **Verdict**: enforce mode neither helps nor hurts at this sample size. Underpowered (70 vs target 500/arm) — re-run with larger sample recommended before rollout. Bug fixes: added `ORCHESTRATOR_FACTUAL_RISK_MODE` env var override, fixed `features().factual_risk_mode` AttributeError in routing.py.

### P2 — AutoPilot Structural Improvements

Medium priority. These improve autoresearch effectiveness before it starts running at scale.

- [x] **AP-4: `lab failures` query at species proposal time** — ✅ 2026-03-29. Added `journal.recent_failures(species, n)` method. Already wired into AP-1's PromptForge dispatch (extracts last 5 failures for the species).

- [x] **AP-5: Per-suite quality trends in controller prompt** — ✅ 2026-03-29. Added `journal.suite_quality_trend(last_n)` method returning per-suite quality over time. Added `### Suite Quality Trends` section to controller prompt template with decline/improve direction indicators.

- [x] **AP-6: Persist `_consecutive_failures` counter** — ✅ 2026-03-29. `SafetyGate.__init__()` accepts `consecutive_failures` param. Loaded from / saved to `autopilot_state.json` each trial.

- [x] **AP-7: Invalidate stale Optuna trials after regime changes** — ✅ 2026-03-29. Added `NumericSwarm.mark_epoch(reason)` + `_study_name()` with epoch suffix. Called in `dispatch_action()` after accepted prompt mutations and structural experiments. Old studies preserved for history, new studies start clean.

- [x] **AP-8: Hypothesis-mechanism tracking on JournalEntry** — ✅ 2026-03-29. Added `hypothesis: str` and `expected_mechanism: str` fields to `JournalEntry` dataclass. JSONL load/save updated. Fields available for Strategy Store retrieval.

### P3 — Routing Intelligence Phase 5 (seeding integration)

- [x] **RI-8: Add risk fields to `RoleResult`** — ✅ Verified 2026-03-29. Fields exist at `seeding_types.py:230-234` with `factual_risk_` prefix: `factual_risk_score`, `factual_risk_adjusted`, `factual_risk_band`, `factual_risk_features`. Original probe used wrong naming convention; actual implementation is correct.

- [ ] **RI-9b: Threshold/Pareto sweep if thresholds change** — Package B already produced initial risk-distribution profiling. Reuse the seeding `--suite` mechanism only if RI-10 indicates band thresholds or enforcement thresholds need adjustment. (→ Package B, see [`bulk-inference-campaign.md`](bulk-inference-campaign.md))

### P4 — Observability Infrastructure (Dynamic Stack Phase B)

These unblock data-driven stack scheduling.

- [x] **DS-1: Instrument queue depth telemetry** — ✅ 2026-03-29. `RoundRobinBackend` now tracks per-instance active/total counts, idle instances, seconds since last request. `get_stats()` exposes all. Queue depth injected into `routing_meta` in `_route_request()`.

- [x] **DS-2: Instrument escalation rate telemetry** — ✅ 2026-03-29. `AppState.record_escalation(from, to)` tracks total escalations and per-path counts (e.g., "frontdoor→coder"). Wired into streaming chat.py (2 call sites) and graph helpers. `get_stats()` returns escalation_rate and escalations_by_path.

- [x] **DS-3: Add `--slot-save-path` to production launches** — ✅ 2026-03-29. `build_server_command()` appends `--slot-save-path <cache_dir>/kv_slots/<role>` for all roles. Per-role subdirectories created automatically.

- [x] **DS-4: Log stack state alongside routing telemetry** — ✅ 2026-03-29. `routing_meta["stack_state"]` populated from `state.registry.roles` with model name, tier, and instance count. Logged via `log_task_started()` in progress JSONL.

### P5 — AutoResearch Bootstrap (Phase A)

- [x] **AR-1: Establish debug suite baseline** — ✅ 2026-03-30. 3-way eval on 105 questions (15/suite × 7 suites). Direct 57.3%, REPL 43.1%, Architect 52.4%. Tools hurt 2.7× more than help (24 vs 9). Median pipeline latency 181s. Baseline written to `orchestration/autopilot_baseline.yaml`. Per-suite breakdown pending (output JSON lost to pipe error; re-run needed for granular data).

- [x] **AR-2: Smoke test autoresearch loop** — ✅ 2026-03-29. Dry-run 5 trials passed: journal writes (JSONL + TSV), parent_trial linkage, consecutive_failures persistence, Pareto archive, safety gate all functional. matplotlib missing (non-fatal).

- [x] **AR-3/J6: Relaunch live autoresearch run** — ✅ 2026-05-31. Planner-context meta-loop fixed (`dcfc9eb` B/A/C), runtime poison pruned (journal 184/186/187 + 65 strategy rows + meta-counter), and relaunched in `draft_critique` mode at `--max-trials 300` (bg pid 3740635). First post-resume turn pivoted off `distill_knowledge` to a real `numeric_trial` — spiral broken. Now running toward trial 300; watch credits (`out_of_credits`/overage-rejected, `status:allowed` in 5h window). Status source of truth: handoff banner + `progress/2026-05/2026-05-31.md`. (→ [`bulk-inference-campaign.md`](bulk-inference-campaign.md))

### P6 — Routing Intelligence Phase 6 (controlled rollout)

Depends on Phase 4 A/B results.

- [ ] **RI-10: Shadow → enforce canary decision** — 🔄 ACTIVE since 2026-04-06. Canary mode live: 25% enforce on frontdoor, 75% shadow. Before acting, pull current logs; elapsed time alone does not satisfy the gate. Require >=50 high-risk samples unless explicitly accepting a lower-powered decision, no p95 latency regression >10%, no cost regression >5% at equal factuality, no unexplained escalation/review inflation >20%, and no 5xx/error cluster attributed to factual-risk scoring. Then choose RI-11, threshold rework, or rollback to shadow.

- [ ] **RI-11: Enforce expand** — Frontdoor 100% + worker_general, 7 days.

- [ ] **RI-12: Enforce global** — All roles. Set up monitoring dashboards.

### P7 — Dynamic Stack Implementation (Phases C-F+)

Depends on observability (P4) and autoresearch baseline (P5). The active handoff is compacted: completed DS-B/DS-C/DS-D design and DS-6/DS-7 gap details live in [`../completed/dynamic-stack-concurrency-completed-through-2026-05-28.md`](../completed/dynamic-stack-concurrency-completed-through-2026-05-28.md); current work lives in [`dynamic-stack-concurrency.md`](dynamic-stack-concurrency.md).

> **Ownership note (2026-04-17)**: This handoff has dual relevance. Phases B-E (stack exploration, QuarterScheduler, templates, autoresearch) are routing-and-optimization concerns owned here. **Phase F (KVCOMM F1-F4) is inference-acceleration-adjacent** — it compounds with AM compaction L4b and affects cross-NUMA cache coherence. Phase F status is cross-listed in `inference-acceleration-index.md` landscape table for discoverability. Single source of truth remains this file + the underlying handoff.

- [ ] **DS-E1 / DS-5: Phase E evidence packet** — Before coding scheduler changes, collect Package B throughput baselines, RI-10 escalation data, DS-5/autoresearch model roster findings, production KV-size measurements, and mixed-role NUMA contention evidence. If these are missing, update the source handoffs instead of expanding DS-6. (→ Package D, see [`bulk-inference-campaign.md`](bulk-inference-campaign.md))

- [ ] **DS-6-live: Deterministic quarter scheduler revalidation gate** — Implement only if DS-E1 shows static pre-warm leaves material throughput/latency on the table. If triggered, use the completed ledger's resolved design: dynamic backend mutation API, liveness heartbeat, quarter-fixed ports, drain protocol, idle tracking, and retry-compatible degradation.

- [ ] **DS-7-live: Stack profile codification** — Encode one evidence-backed workload profile at a time, validate with `--validate-only`, and avoid speculative profile proliferation. Completed schema/CLI/migration/resource-budget details are in the completed ledger.

- [ ] **DS-F1-F4: KVCOMM optional research fork** — Do not treat as a deployment queue item. Revisit only after Attention Matching P2 and then test q4_0 offset feasibility; continue only if shared-codebase quality remains >95%.

#### Within-Role Placement + KV Migration (siblings to DS-6/DS-7; NEW 2026-05-25)

Tracked in [`within-role-placement-state-machine.md`](within-role-placement-state-machine.md). Each phase is independently shippable behind an env flag with a metric gate; phases described in detail in the handoff.

- [x] **WP-0: Revert risky default** ✅ 2026-05-26 (`33bfe20`). `AUTOPILOT_EVAL_CONCURRENCY` default reverted from 4 to 1; helper + env knob preserved. 29/29 baseline tests green.
- [x] **WP-1: Topology-safe per-role concurrency** ✅ 2026-05-26 (`cab27ac`). `compute_max_safe_concurrency(numa_config, role)` + live `max_safe_concurrency(role)` added to `src/runtime/instance_topology.py`; default for autopilot now reads bottleneck role (frontdoor → 3). Live values match the handoff table (frontdoor=3, worker_general=1, etc.). 15 new tests in `tests/unit/test_topology_concurrency.py`.
- [x] **WP-2: Placement state machine (no migration; queue-instead-of-overlap)** ✅ 2026-05-26 (`3d94a03`). New `src/scheduling/placement.py` (`evaluate_placement`, `Place`, `Queue`, `QueueReason`); `ConcurrencyAwareBackend._dispatch` refactored behind `ORCHESTRATOR_PLACEMENT_STATE_MACHINE=1`; legacy path preserved when flag off. 17 unit + 4 integration tests.
- [x] **WP-3: Transactional migration + policy gating + budget honoring** ✅ 2026-05-26 (`b4d5161`). MigrationTransaction state machine (`src/scheduling/migration_transaction.py`, 7 states); `_migrate_kv` refactored to drive it; policy gate on the existing session-handover trigger (FULL_DISABLED + QUEUE_ONLY skip); `ChatRequest.migration_budget_ms` extracted and threaded. The speculative load-transition trigger inside the WP-2 poll loop was explored and removed — `_migrate_kv` cannot preempt mid-decode, so it doesn't unblock the queue (rationale in commit body + `_dispatch` comment). 20 + 8 tests.
- [x] **WP-4: Reverse migration (quarter→full when load drops)** ✅ 2026-05-26 (`66a8bfc`). `_release` triggers `_maybe_spawn_reverse_migration`; four guards (full-idle cooldown 2s default, session-recency window 30s default, per-session cap 5 default, in-flight de-dup); behind `ORCHESTRATOR_REVERSE_MIGRATION=1`. 11 tests covering each guard.
- [~] **WP-5: Full-machine roles (worker_general, architect_general)** — SCAFFOLD ✅ 2026-05-26 (`29e95b4`). `RolePlacementPolicy` enum (`solo_prefer_full` / `burst_prefer_quarters` / `full_disabled` / `queue_only`) + `get_placement_policy(role, numa_config=None)` accessor; all roles default to conservative SOLO_PREFER_FULL (no live behavior change). 18 tests. **Full ratification deferred** — requires autopilot observability data + per-role decision (set `placement_policy: '...'` in NUMA_CONFIG).
- [ ] **WP-6: Matrix extension + re-bench** — Sweep within-role instance pairs in `scripts/server/contention_matrix.py`; update YAML schema with `instance_pairs` and `topology_hash`. Gate: CV ≤ 5% across 3 runs and runtime fails closed on topology/YAML hash mismatch. **Blocked: requires user-approved inference runs.**
- [ ] **WP-7: Production rollout + autopilot tuning** — Matrix-aware default fan-out; 24-hour gate. Documentation in `wiki/autopilot-tuning.md`. **Blocked: requires WP-6 + 24-hour autopilot run.**

### P8 — AutoPilot Design Philosophy Imports

Lower priority refinements.

- [x] **AP-9: Tighter per-trial scope** — ✅ 2026-04-05. `_validate_single_variable()` in `autopilot.py` rejects multi-file prompt mutations, multi-flag structural experiments, and multi-param explicit numeric trials before dispatch.

- [x] **AP-10: Simplicity criterion for PromptForge** — ✅ 2026-03-29. After safety gate passes, checks prompt size increase >20% with quality delta <0.02 — reverts if criterion violated.

- [x] **AP-11: Git worktree isolation for PromptForge** — ✅ 2026-04-05. `worktree_manager.py` creates temp worktrees per trial. `ExperimentContext` handles apply/accept/reject with auto-reject safety default. PromptForge gains `apply_mutation_in_context()` + `apply_code_mutation_in_context()`. 5 tests.

- [x] **AP-12: Explicit eval trust boundary** — ✅ 2026-03-29. Added trust boundary table to `program.md` showing OUTSIDE (species-modifiable) vs INSIDE (immutable eval) files.

- [x] **AP-13: Grep-parseable metric output** — ✅ 2026-04-05. `EvalResult.to_grep_lines()` emits `METRIC key: value` lines. Logged after each eval in the autopilot main loop. Extract via `grep METRIC autopilot.log`.

- [x] **AP-14: Structured deficiency classification** — ✅ 2026-04-07. `DeficiencyCategory` enum (9 values) in `experiment_journal.py`. `SafetyVerdict.categories` list tags each violation. `deficiency_category` field on `JournalEntry`. Dispatch-level shrinkage/consecutive_failures via `state["_dispatch_deficiency"]` side channel.

- [x] **AP-15: Species field verification audit** — ✅ 2026-04-07. Audit found 3/5 species (Seeder, NumericSwarm, StructuralLab) produce empty `hypothesis`. Added fallback logic in main loop: species-specific hypothesis generation + `action.get("type")` as final `expected_mechanism` fallback.

- [x] **AP-16: Instruction token budget tracking** — ✅ 2026-04-07. `instruction_token_count` and `instruction_token_ratio` on `EvalResult` + `JournalEntry`. `_count_instruction_tokens()` in `eval_tower.py` scans `orchestration/prompts/*.md`. `to_grep_lines()` emits `METRIC instruction_tokens` + `METRIC instruction_ratio`. Warning at >20%. State tracks `_last_instruction_ratio` for AP-17.

- [x] **AP-17: Structural pruning in StructuralLab** — ✅ 2026-04-07. `structural_prune` action type in `dispatch_action()`. `prune_block()` method on StructuralLab removes heading-delimited sections. Acceptance: safety gate passes AND instruction_token_ratio decreases. Revert on rejection. Added to controller prompt template.

### P8b — Web Search Over-Reliance Fix (from Package B Omega audit)

Package B Phase 4 found 7/10 suites where REPL mode hurts accuracy vs direct. Root cause: the model web-searches for answers instead of reasoning. `rules.md` actively encouraged this with "Use Python computation, web_search, or llm_call to VERIFY your answer."

- [x] **WS-1: Fix tool selection guidance** — ✅ 2026-04-09. **Root cause**: `DEFAULT_ROOT_LM_RULES` in `src/prompt_builders/constants.py` (not `rules.md`) was the actual prompt. It said "when in doubt, search first" and "Use web_research for: any factual question." Replaced with priority-ordered guidance: compute → direct answer → reason → search only for genuine gaps. Also updated `rules.md` (secondary, used when `config.rules_file` is set). Arm B running with fix — preliminary check showed 100% web search before fix; monitoring for improvement.
- [ ] **WS-2: Re-run Omega measurement post-fix** — Compare direct vs REPL accuracy with updated prompts. Target: REPL ≥ direct on ≥5/10 suites (currently 2/10).
- [x] **WS-3: Cascading tool policy for web denial** — ✅ 2026-04-09. Implemented belt-and-suspenders enforcement: `NO_WEB_TASK_TYPES` constant in `tool_policy.py` (math, coder, thinking, instruction_precision). `tool_context` param added to `REPLEnvironment`. Context threaded through `_invoke_tool`/`_list_tools` → `ToolRegistry.invoke()`/`list_tools()` with `context` param. All 4 REPL creation sites (`repl_executor.py`, `stream_adapter.py`, `stages.py`) derive `no_web` from `routing.task_ir["task_type"]`. Feature flag `cascading_tool_policy` enabled by default (validated in prod). 5 new tests in `test_tool_policy.py` (32 total, all passing). **BUG FOUND 2026-04-09**: `routing.py:56` hardcoded `task_type: "chat"` so `NO_WEB_TASK_TYPES` never matched. Fixed: role→task_type derivation added after routing (worker_math→math, coder_*→coder, thinking_reasoning→thinking).

### P10 — GEPA PromptForge Integration (2026-04-12 research intake)

Source: intake-327/345/240. GEPA reflective trace analysis (ASI) + evolutionary Pareto search. 35x fewer rollouts than GRPO. Compatible with local inference. See [`autopilot-continuous-optimization.md`](autopilot-continuous-optimization.md) P10.

- [x] **AP-18: DSPy + GEPA setup** — ✅ 2026-04-12. `dspy>=2.5.0` in pyproject.toml. `src/dspy_signatures/` with 3 signatures + config. 8 tests.
- [x] **AP-19: GEPA frontdoor optimization** — ✅ Folded into AR-3 Package D (2026-04-12). `gepa_optimizer.py` adapter + `gepa` mutation type in PromptForge (30% of trials). 10 integration tests.
- [x] **AP-20: GEPA Full Program Adapter eval** — ✅ Folded into AR-3 Package D (2026-04-12). Resolved by comparing GEPA vs LLM mutation acceptance rates in AR-3 journal.
- [ ] **AP-21: PromptForge GEPA refactor** — Conditional on AR-3 data. If GEPA dominates Pareto frontier → increase ratio to 100%.

### P11 — Autopilot Controller Upgrades (2026-04-12 research intake)

Source: intake-328/329 (MiniMax 3-component harness), intake-349 (dspy.RLM), intake-320 (RLVR). See [`autopilot-continuous-optimization.md`](autopilot-continuous-optimization.md) P11.

- [x] **AP-22: Short-term memory per trial** — ✅ 2026-04-12. `short_term_memory.py` (4-section markdown, token-budgeted, CLI reset).
- [x] **AP-23: Self-criticism step** — ✅ 2026-04-12. `self_criticism.py` (rule-based, no inference cost).
- [x] **AP-24: Keep/revert protocol** — ✅ 2026-04-12. 3 new JournalEntry fields, wired into controller loop.
- [x] **AP-25: dspy.RLM infrastructure setup** — ✅ 2026-04-12. `configure_rlm()` in config.py, `test_connection()` health check.
- [ ] **AP-26: dspy.RLM integration testing** — Test benchmark analysis via REPL exploration. Needs inference. (→ also bulk-inference Package H)
- [ ] **AP-27: RLVR eval tower formalization** — Formalize T0/T1/T2 as verification functions. Needs inference for validation. Depends on P7 Ouro eval. (→ also bulk-inference Package H)

### P10b — Context Folding Phase 2d (2026-04-12 research intake)

Source: intake-316 (LTM Unsolved gap analysis: FORGETTING axis), intake-326 (MemPalace patterns). Phase 2d completion details now live in [`context-folding-progressive` completed ledger](../completed/context-folding-progressive-completed-through-2026-05-28.md). All non-inference.

- [x] **CF-P1: Validity timestamps** — ✅ 2026-04-12. Fields + serialization + all 3 creation sites populated.
- [x] **CF-P2: Supersession detection** — ✅ 2026-04-12. `check_supersession()` with 8 regex patterns.
- [x] **CF-P3: Metadata filtering** — ✅ 2026-04-12. `topic_tags` + `_extract_topic_tags()` (7 categories).
- [x] **CF-P4: Hybrid raw+derived** — ✅ 2026-04-12. `is_raw` field, serialization ready. Raw window logic pending production wiring.

### P10c — Meta-Harness Tier 2b (2026-04-12 research intake)

Source: intake-338/345. Tier 2b completion details now live in [`meta-harness-optimization` completed ledger](../completed/meta-harness-optimization-completed-through-2026-05-28.md).

- [x] **MH-4: GEPA as search algorithm** — ✅ Folded into AR-3 Package D (2026-04-12). GEPA integrated as PromptForge mutation type. Journal collects Pareto frontier contributions by mutation source.
- [x] **MH-5: Agent Lightning trace collection** — ✅ 2026-04-12. `telemetry.py` with TelemetryCollector, TransitionRecord, OTLP spans, JSONL export.

### P12 — Web Research Pipeline: SearXNG + Crawl4AI (2026-04-14 / updated 2026-05-05)

Source: intake-359/360/361 (SearXNG), intake-372 (Crawl4AI). Full four-step chain: SearXNG (step 1, search) → Crawl4AI (steps 2+3, scrape+crawl) → Camofox (step 4, browser, intake-524). SX-1–4 done. CA-1–5 (Crawl4AI steps 2+3) are independent — no AR-3 gate, no Camofox dependency, can start now. See [`searxng-search-backend.md`](searxng-search-backend.md).

- [x] **SX-1: Docker container deployment** — ✅ 2026-04-14. SearXNG in `DOCKER_SERVICES` (port 8090). Config: `config/searxng/settings.yml`.
- [x] **SX-2: `_search_searxng()` implementation** — ✅ 2026-04-14. JSON API backend in `search.py` with DDG fallback.
- [x] **SX-3: Engine tuning** — ✅ 2026-04-14. Google inactive, DDG/Brave/Wikipedia/Qwant weighted, per-engine timeout 3.0s.
- [x] **SX-4: `unresponsive_engines[]` telemetry** — ✅ 2026-04-14. Logged on every call with failures.
- [ ] **SX-5: Load test** — Folded into AR-3 Package D Phase 6b. Web_research sentinel suite (50q) validates under real query patterns.
- [ ] **SX-6: Swap default** — Feature flag `ORCHESTRATOR_SEARXNG_DEFAULT=1` ready. Gated on AR-3 warmup trial. See bulk-inference-campaign.md Phase 6b.

### P13 — Decision-Aware Q-Scorer Routing (2026-04-14 deep-dive research)

Source: intake-366 deep-dive. Diagnosed pathology: difficulty signal has zero predictive spread (P0 validation). Current Q-scorer uses predict-then-optimize (TD-learn Q-values, argmax). Decision-aware learning aligns training with routing DECISIONS. Our N=3-5 routing is trivially tractable — SPO+ is convex with closed-form gradients, no RL infrastructure needed. See [`decision-aware-routing.md`](decision-aware-routing.md).

- [x] **DAR-1: Offline regret analysis** ✅ 2026-04-15 — Replay logged decisions, compute regret = Q(best) - Q(chosen). Result: 96% uniform Q-values (near-zero predictive spread confirmed). No code changes needed.
- [x] **DAR-2: Contrastive Q-score update** ✅ 2026-04-15 — ~50 lines in `q_scorer.py`. Pairwise ranking loss + `_compute_contrastive_adjustment()`. Modified `_compute_reward()` + `update_q_value()`. Unit test deferred.
- [ ] **DAR-3: SPO+ with exploration** — ~100 lines. Convex surrogate loss + 10% epsilon-greedy exploration in `retriever.py` L225-368 for counterfactual data. Blocks on DAR-2 Q-signal validation. **2026-04-28 motivation note added (intake-495)**: BaRP frames this as the train/test mismatch fix — DAR-3 adopts the bandit-feedback rationale with a convex surrogate loss instead of REINFORCE.
- [ ] **DAR-4: Model-feature-conditioned Q** — ~200 lines. Bilinear scorer replacing per-action Q-tables. Zero cold-start for new models. New `bilinear_scorer.py` module.
- [ ] **DAR-4b: Inference-time preference vector + cost scaling τ** (NEW 2026-04-28, from intake-495 BaRP) — ~50–100 lines, 1–2 sessions. 2-D preference vector `ω = (ω_perf, ω_cost)` modulating the trained DAR-4 bilinear scorer at inference WITHOUT retraining. Cost scaling τ as runtime knob. Per-tenant or per-task ω override. Independent of DAR-4 if DAR-4 slips — applies to existing per-action Q-table too. See `decision-aware-routing.md` DAR-4b.
- [ ] **DAR-5: IRT-augmented prompt features + learned model identity vectors** (NEW 2026-04-28, from intake-496 LLM Bandit) — ~150 lines, 3–5 sessions, conditional on DAR-4. Replaces hard-coded model-feature specs with end-to-end learned model identity vectors; augments prompt embedding with IRT (latent_difficulty, latent_discrimination). Decision gate: ≥ 2-pt val acc improvement to promote. See `decision-aware-routing.md` DAR-5.
- **Future routing signal (2026-04-15 deep-dive)**: intake-378 identifies branching density (Propose step ratio) as a runtime quality signal. High branching = unproductive exploration. 21pp generalization gap on Llama3.1-8B from reasoning pattern quality alone. Could feed DAR-4 bilinear scorer as a prompt/output feature: branch-heavy outputs warrant stronger models. Implementation: `quality_detector.py` branching density (see `routing-intelligence.md`). Cross-ref: `research/deep-dives/sft-generalization-reasoning-patterns.md`.

### P14 — AutoPilot Iteration Strategy Upgrade (2026-04-20 deep-dive synthesis)

Source: intake-413 (HCC), intake-414 (Token Savior), intake-415 (Context Mode). Synthesis deep dive: `research/deep-dives/autopilot-iteration-strategy-synthesis.md`. See [`autopilot-continuous-optimization.md`](autopilot-continuous-optimization.md) for full context.

4-phase improvement plan for AutoPilot knowledge accumulation, retrieval quality, and context budget management. Phase 1 is directly implementable from the synthesis document.

- [/] **AP-28: Strategy Memory Upgrade** — **CODE LANDED 2026-05-08** (epyc-orchestrator commit `ad25ade`). FTS5 parallel index + RRF fusion in `retrieve()`, per-entry `context_hash` + 0.5x staleness penalty, Bayesian validity weighting on the existing NIB2-41 strategy_validity table, `entry_type` column for L1/L2/L3 hierarchy. Zero-downtime ALTER + idempotent FTS5 backfill. 18 unit tests pass (8 backward-compat + 10 new). Activation: AR-3 restart picks up the new code; `backfill_fts()` runs at first store init.
- [/] **AP-29: Knowledge Distillation Pipeline** — **CODE LANDED 2026-05-08** (epyc-orchestrator). New `orchestration/repl_memory/knowledge_distiller.py`. L1→L2→L3 promotion (≥3 in-species → pattern; ≥3 species OR ≥10 sources → convention). MDL compression check, greedy cosine clustering, source-row quarantine via existing validity counter, audit row in `strategy_conventions`. **WIRING DEFERRED**: `distiller.distill(trial_id)` call at the autopilot 25-trial auto-checkpoint is intentionally not added during AR-3 runtime; wire on next autopilot restart. 6 unit tests pass.
- [/] **AP-30: Controller Context Budget** — **CODE LANDED 2026-05-08** (epyc-orchestrator). New `scripts/autopilot/context_budget.py` exposing `truncate_to_budget`, `apply_section_budget`, `format_strategies_tiered`, `gate_eval_output`, `build_budgeted_section_block`. `SECTION_BUDGETS` caps 14 sections + 5KB eval-output gate. **WIRING DEFERRED**: replacing `build_controller_prompt` glue + flat strategy injection in `dispatch_action` deliberately not done during AR-3 runtime; replace on next autopilot restart. 13 unit tests pass.
- [/] **AP-31: Mutation Knowledge Graph** — **CODE LANDED 2026-05-08** (epyc-orchestrator). New `scripts/autopilot/species/mutation_graph.py` — sidecar SQLite store of (mutation_type, failure_pattern, target_file, outcome) quadruples. Decision support: `best_mutation_for`, `avoid_for`, `pareto_best_sections`, `informed_crossover_candidates`. **WIRING DEFERRED**: PromptForge `propose_mutation` should `record()` at cycle end and consult `informed_crossover_candidates` for the `crossover` mutation type; do on next autopilot restart. 9 unit tests pass.

### P16 — Strategy Store + PromptForge Safety (2026-04-22 research intake deep-dive)

Source: intake-425 (Memory Transfer Learning, arXiv:2604.14004). Deep dive confirms 4 adoptable patterns for autopilot strategy_store and PromptForge mutation safety. See [autopilot-continuous-optimization.md](autopilot-continuous-optimization.md) Research Intake Update 2026-04-21.

- [ ] **AP-32: Insight format for strategy_store entries** — Adopt the `(title, description, generalized_content)` format with no task-specific implementation details for new strategy_store entries. Audit existing entries for over-specificity. Task-agnostic insights outperform task-specific by +1.1%. ~50 LoC in `strategy_store.py`. Validates HCC L3 upgrade path (AP-29).
- [ ] **AP-33: Negative transfer safety gates for PromptForge** — Implement 3 mutation safety checks based on negative transfer taxonomy: (1) domain-mismatched anchoring detector (reject mutations that import patterns from mismatched benchmark suites), (2) false validation confidence flag (warn when mutation success is based on <5 trials), (3) misapplied best-practice filter (reject mutations that generalize suite-specific patterns). ~100 LoC in `prompt_forge.py` safety section.
- [ ] **AP-34: Validate N=3 embedding retrieval** — Confirm that our FAISS top-3 cosine retrieval matches or exceeds any LLM-based reranking we might consider. Paper shows: embedding similarity (0.630 avg) > LLM reranking (0.598) > adaptive rewriting (0.608). Run ablation: top-1 vs top-3 vs top-5 on next AR-3 run. Zero code changes — configuration experiment via autopilot.

### P17 — Environment Synthesis Species (2026-04-22 deep-dive integration, DD6)

Pointer — full plan tracked in [`agent-world-env-synthesis.md`](agent-world-env-synthesis.md). Phase 1 is training-free and CPU-feasible today; Phase 2 is GPU-gated (post-DGX-Spark). Makes env-synth the 5th autopilot species (alongside Seeder/NumericSwarm/PromptForge/StructuralLab), providing a concrete Tier 3 outer-loop rebuild recipe for meta-harness.

- [ ] **P17 rollup**: see `agent-world-env-synthesis.md` AW-1..AW-9 — entry points: AW-1 (`env_synth/` module scaffold), AW-6 (48h arena bootstrap).

### P18 — Deep Research Mode (2026-04-22 deep-dive integration, DD7)

Pointer — full plan tracked in [`minddr-deep-research-mode.md`](minddr-deep-research-mode.md). As of the 2026-05-28 audit, Phase 1 scaffolding is already landed (flag, classifier, prompts, pydantic_graph package, rubric fields, sentinel suite). The live gate is MD-9 A/B; dispatcher wiring and Phase 2 RL remain blocked until that result exists.

- [ ] **P18 rollup**: see `minddr-deep-research-mode.md` MD-1..MD-14. Current entry point is MD-9: run `deep_research_sentinel.yaml` control/treatment A/B. Use EV-9 rubric scoring if available; otherwise structural-only scoring can inform but cannot promote default-on.

### P19 — Trinity-Derived Coordinator/Routing Tasks (2026-04-26 deep-dive integration)

Source: deep-dive [`research/deep-dives/trinity-evolved-llm-coordinator-methodology.md`](../../research/deep-dives/trinity-evolved-llm-coordinator-methodology.md) on intake-474 (TRINITY: An Evolved LLM Coordinator, ICLR 2026, Sakana AI). Trinity is the most direct prior art for our lightweight-learned-coordinator-over-heterogeneous-pool thesis. The deep-dive cross-checks Trinity's design choices against ours and produces nine portable lessons. **Standing reference**: link the deep-dive when arguing for any routing-architecture change so we know which Trinity lever the change does or does not echo.

These tasks live across multiple handoffs. This section is the index roll-up — for implementation detail, follow the linked handoff phases.

**Architectural change (orthogonal to optimizer)**:

- [/] **P19.1**: TR-1 through TR-5 in [`tri-role-coordinator-architecture.md`](tri-role-coordinator-architecture.md). **REFRESHED 2026-05-28**: TR-1 taxonomy, TR-2 data layer, and TR-3.1/3.2 heuristic shadow classifier have landed. Current gate is not more schema work; it is TR-3.3/3.4 telemetry: collect production-like `trinity_role_shadow` logs, prove role distribution is non-degenerate, and capture representative true/false examples. TR-4 prompt/dispatch wiring waits on that diagnostic. TR-5 remains paired A/B (>=N=200/arm) with `ROLE_AWARE_ROUTING` default-off unless the gain/regression gate passes.

**Methodology audits on Learned Routing Controller**:

- [/] **P19.2**: P4.1 in [`learned-routing-controller.md`](learned-routing-controller.md). **Phase A (audit) DONE 2026-05-07; Phase B (3-variant ablation) deferred pending explicit per-run inference approval + FAISS rebuild.** Audit findings: (1) current pool method confirmed CLS (`orchestrator_stack.py:862`); (2) data-scale finding — handoff says 174K labels, actual on-disk state is ~8K memories (production episodic.db at /mnt/raid0/llm/.../episodic.db has 8,115 rows); (3) FAISS index is currently reset (385KB live vs 32MB .bak from Apr 28); (4) Phase B is cheap (~10-15min wall-clock total: 3× BGE invocations × ~40s + 3 head retrains × seconds), but requires crossing the inference threshold. Phase B script + decision-gate logic written into the LRC handoff. With n=8K (not 174K), the original ≥1 pp gate produces a binomial CI half-width of ~3-4 pp — recommended to require |Δ| ≥ 4 pp for statistical confidence. Recommended sequencing: bundle Phase B with P19.9 (P4.1.3 IRT variant) into a single inference run.
- [ ] **P19.3**: P4.2 in [`learned-routing-controller.md`](learned-routing-controller.md). Block-ε-separability diagnostic on our routing landscape (full-rank vs block-diagonal-10 vs diagonal head). Tells us whether Trinity's optimizer-choice argument applies to our problem geometry. **Gates P19.5** (sep-CMA-ES spike).
- [ ] **P19.4**: P4.3 in [`learned-routing-controller.md`](learned-routing-controller.md). SVD-scale fine-tuning trial on BGE backbone (~9K extra params, claimed +3-4 points in Trinity's ablation). Cheaper than LoRA, applicable independent of all other Phase 4 work.
- [ ] **P19.5**: P4.4 in [`learned-routing-controller.md`](learned-routing-controller.md). sep-CMA-ES cold-start spike for routing surfaces lacking episodic labels. Population λ≈45, m=16, ≈10h overnight at 32-way concurrency for feasibility test. **Prerequisites**: P19.3 (block-ε diagnostic favourable) + Math-Verify adoption (cross-cutting concern #13) so eval-tower can serve as fitness oracle.

**Methodology audit on Decision-Aware Routing**:

- [x] **P19.6**: DAR-1.5 in [`decision-aware-routing.md`](decision-aware-routing.md). ✅ **DONE 2026-05-07** — analytical audit complete. Verdict: **DAR-3 unblocked unconditionally** (per-action Q-table substrate has `ε_H=0` exactly by construction; Trinity's REINFORCE pathology cannot transfer to a discrete lookup architecture). **DAR-4 conditional on P19.3** (bilinear scorer's shared `W` matrix introduces high coupling by design — if P19.3 confirms our landscape is block-ε-separable, DAR-4 needs rank-restriction `W ≤ rank-k` or sep-CMA-ES; if P19.3 falsifies, naïve full-rank bilinear is appropriate). **DAR-4b unblocked** (inference-time blending, no training gradient). Key insight: REINFORCE's pathology is parameter coupling × high-variance scalar advantage — `ε_H` is determined by the scorer's *architectural coupling pattern*, not the loss form. Per-action tables are decoupled-by-construction; bilinear/deep policies are coupled-by-design. Full deliverable in DAR-1.5 audit sub-section appended to `decision-aware-routing.md`.

**Documentation update**:

- [x] **P19.7**: ✅ **DONE 2026-05-07** — chapter 08 updated with the 4-class methodological framing (RL-trained / preference-trained / confidence-cascade / ES-trained) + Trinity entry (canonical ES-trained router) + Conductor entry (companion design-space reference). Cross-links to LRC P4.1-4.4, tri-role TR-1..5, DAR-1.5 audit, outer-coordinator OC-0 in epyc-root. Caveats called out: pool-heterogeneity discount on inner-pool projections, six-author Trinity/Conductor overlap (not independent corroboration), MAST inter-agent misalignment.

**Speculative scoping**:

- [ ] **P19.8**: OC-0 in [`outer-coordinator-learned-head.md`](outer-coordinator-learned-head.md). **REFRESHED 2026-05-28**: keep as scoping/parking only. Do not draft OC-1 or implementation work until tri-role/DAR/LRC dependency gates progress or a measured Claude-loop token/latency bottleneck exists. OC-0 outcome fork: <20% replaceable Claude decision cost -> close `not_pursued`; >50% and uniform decisions -> rules-first replacement; >50% and context-dependent decisions with a usable fitness signal -> learned-head spike proposal.

**Bandit-feedback / IRT cold-start routing (intake-495/496 derived, NEW 2026-04-28)**:

- [ ] **P19.9**: LRC P4.1.3 in [`learned-routing-controller.md`](learned-routing-controller.md). Bundle an IRT-feature variant into the P4.1 feature-position audit. Train a quick IRT score predictor over BGE pooled output that emits `(latent_difficulty, latent_discrimination)` per prompt; include as a 4th variant alongside BGE-CLS / BGE-mean / BGE-last. Decision gate: ≥1 pt val-acc improvement → escalate to a separate phase plan (cross-link to DAR-5). Bundled with P4.1 — +1 session, no separate ablation infrastructure. Source: intake-496 (LLM Bandit).
- [ ] **P19.10**: LRC Phase 5 in [`learned-routing-controller.md`](learned-routing-controller.md). IRT-stratified cold-start onboarding. P5.1 (IRT discrimination scorer, ~80–100 LoC, ~2 sessions) + P5.2 (cold-start A/B re-onboarding existing specialist with 50 IRT-stratified prompts vs on-disk full sweep, ~70 LoC harness, 1 session) + P5.3 (conditional production rollout if P5.2 passes). Decision gate: ≤ 5% relative error on each baseline feature AND ≥ 5× faster than full sweep wall-clock. **This is the most actionable single experiment from intakes 495/496** — if it passes, every future model swap compresses from a multi-hour sweep to a ~30-minute calibration. Source: intake-496 (LLM Bandit).
- Pointer: DAR-4b and DAR-5 (intake-495/496 patterns adopted at the Q-scorer layer) are tracked at P13 above, not duplicated here.

**Dependency chain summary**:

```
P19.7 (chapter doc)         ──independent──
P19.4 (SVD-FT trial)        ──independent──
P19.2 (feature-position)    ──independent──
P19.6 (DAR-1.5 audit)       ──DONE 2026-05-07; verdict conditional on P19.3 outcome──
P19.3 (block-ε diagnostic)  ──gates P19.5──
P19.5 (sep-CMA-ES spike)    ──needs P19.3 favourable + Math-Verify adoption──
P19.1 (tri-role TR-1..5)    ──independent of all P19.2-6, can run in parallel; TR-1 is its own hard gate──
P19.8 (outer-coord scoping) ──gated until tri-role + DAR + LRC Phase 4 all land──
```

**Recommended execution order** (by cheapness × informativeness):
1. ~~P19.6 (DAR-1.5 audit — 1 session, analytical)~~ ✅ DONE 2026-05-07
2. ~~P19.7 (chapter update — 1 session, doc only)~~ ✅ DONE 2026-05-07
3. P19.2 Phase A (audit, no inference) ✅ DONE 2026-05-07; **Phase B (3-variant ablation) deferred** — needs explicit per-run BGE inference approval, ~10-15 min wall-clock when authorized
4. P19.4 (SVD-FT trial — moderate, 2-3 sessions)
5. P19.3 (block-ε diagnostic — moderate, 3-5 sessions) **← gates DAR-4 architecture per DAR-1.5**
6. P19.1 (tri-role TR-1 scoping in parallel — start anytime)
7. Conditional on above: P19.5 (sep-CMA-ES spike if P19.3 favourable + Math-Verify shipped)
8. Long-term: P19.1 TR-2..5 (after TR-1 review)
9. Speculative: P19.8 (only after the above land and reveal pain points)

### P20 — HALO Trace-Loop Spike (2026-04-30 deep-dive integration)

Pointer — full plan tracked in [`halo-trace-loop-spike.md`](halo-trace-loop-spike.md). Source: intake-517/518 deep-dive at [`research/deep-dives/halo-rlm-trace-loop-integration.md`](../../research/deep-dives/halo-rlm-trace-loop-integration.md). 1-day spike + 4-criterion go/no-go gate; conditional Day 2 manual lift of three net-new patterns into existing scoped work (do NOT vendor halo-engine).

Touches autopilot directly: lifted patterns land in `autopilot-continuous-optimization.md` (dev/test_normal split as anti-overfitting guard for Pareto frontier; failure-mode taxonomy seed labels for trace-clustering) and `meta-harness-optimization.md` Tier 3 (six-tool trace-query analyzer surface + two-file JSONL+byte-offset trace store, ~230 LoC into `unified-trace-memory-service.md` T1+T5).

- [ ] **P20.1**: HALO-1 pre-flight install + local-llama-server backend swap (~30 min)
- [ ] **P20.2**: HALO-2 OTel converter for autopilot telemetry (~30 LoC, 4h)
- [ ] **P20.3**: HALO-3 4-criterion go/no-go gate (4h, end of Day 1)
- [ ] **P20.4**: (conditional) HALO-4 manual pattern lift into autopilot/meta-harness/unified-trace-memory-service
- [ ] **P20.5**: HALO-5 spike close-out doc

AppWorld dataset (intake-516) DEFERRED. Already emits OTLP-shaped spans via `scripts/autopilot/telemetry.py:to_otlp_span` since 2026-04-12 — no new emission infra required.

### P21 — Test-Time-Compute Techniques (2026-05-24 research intake + deep-dive)

Source: `/research-intake` of OptiLLM (intake-601) + expansion intakes 602/603/604. Full analysis + autopilot-scope determination in [`research/deep-dives/optillm-test-time-techniques.md`](../../research/deep-dives/optillm-test-time-techniques.md). **Sequencing decision (user, 2026-05-24): DeepConf-offline FIRST, then the method-selection axis.** Both are orchestrator-side and become autopilot-tunable *only after* a dedicated session builds + sanity-checks them and wires a flag/knob surface (see `program.md` "Out-of-Action-Space" gated rows — autopilot must NOT propose these until the surfaces exist).

**P21.A — DeepConf-offline (intake-603), highest ROI.** Logprob-based trace filtering: N parallel llama-server completions with `top_logprobs`, bottom-10% group-confidence scoring, keep top-η%, confidence-weighted majority vote. Needs only `top_logprobs` (already exposed) — no fork change. Token reduction is a direct BW win.
- [x] **P21.A1** ✅ 2026-05-24 — DeepConf offline scorer + live runner + `Features.deepconf` flag (default-OFF), 41 tests. Built in an isolated worktree during the spike; no live worktree or branch is required for the remaining bulk-inference run. Adapter handles both legacy and OpenAI-style `top_logprobs[].logprob` (the real production shape).
- [x] **P21.A2** ✅ 2026-05-24 — **DECISIVE NEGATIVE.** Live Qwen3.6 (`:8080`), thinking ON, 4 hard Qs × 6 traces (autopilot stopped). DeepConf vote 3/4 = plain majority 3/4 (no gain); top-1 **confidence** only 1/4; correct-vs-wrong confidence gap **−0.158**. Model is overconfident on wrong short answers → confidence-filtering *hurts*. Full data in [`research/deep-dives/optillm-test-time-techniques.md`](../../research/deep-dives/optillm-test-time-techniques.md) §P21.A Outcome.
- [x] **P21.A3 / A4** ❌ 2026-05-24 — **DO NOT PROCEED.** No accuracy benefit over majority + N× generation/`n_probs` cost. `program.md` gate updated to "do-not-wire (A2 negative)". Treat this as a closed negative spike, not a pending branch dependency. Revisit only with a much larger trace budget or a better-calibrated model (the confidence metric itself is anti-correlated here).

**P21.B — Method-selection axis (intake-601), second.** A "which test-time technique" axis above role-routing. Reference: OptiLLM pattern only — its local modules are transformers-only and NOT usable over llama-server (see deep-dive). Start with `self_consistency` (only cheap llama.cpp-compatible technique needing no `n`); MCTS/PlanSearch/RTO also work; avoid BoN/MoA/CEPO (need `n` multi-sampling llama.cpp lacks).
- [ ] **P21.B1**: Build the method axis + wrappers + a method-routing classifier/flags in `src/` (dedicated session).
- [ ] **P21.B2**: Hand the per-query-class method policy + thresholds to autopilot (StructuralLab + PromptForge); remove the `program.md` gate row.

**P21.C — out of autopilot scope (tracked, not scheduled here):** CoT-decoding (intake-602) + DeepConf-online → `epyc-llama-experimental` fork spike + BW roofline + **manual** speed bench, gated on P21.A proving worthwhile. Follow-up intake of 17 OptiLLM-cited papers + AutoThink SSRN 5253327 → future `/research-intake` run.

### P15 — Parallel Seeding via NUMA Quarter Isolation (merged 2026-04-21 from `parallel-seeding-eval.md`)

Independent workstream — 2× AR-3 throughput by running 2 concurrent eval streams on dedicated port sets. No contention, no changes to existing seeding scripts, no inference dependency on implementation side. **Cross-ref**: `non-inference-backlog.md` NIB2-12 (implementation) and NIB2-29 (port-doc update).

**Problem**: AR-3 evaluates questions sequentially through the 3-way pipeline. With 192 CPU threads and 30 model servers, seeding utilization is ~13%. Each trial takes 20-40 minutes. Quarter instances (8180-8381) receive zero traffic from seeding.

**Design**: Run 2 concurrent eval streams (not 4 — architect_general and architect_coding each have only 2 instances).

| Stream | frontdoor | coder | worker | architect_gen | architect_code |
|--------|:---------:|:-----:|:------:|:-------------:|:--------------:|
| A | 8080 | 8081 | 8082 | 8083 | 8084 |
| B | 8180 | 8181 | 8182 | 8183 | 8184 |

**New files** (existing scripts untouched):

| File | Purpose |
|------|---------|
| `scripts/benchmark/parallel_seeding.py` | NEW — parallel orchestrator. Imports from existing seeding_eval/orchestrator. Splits questions across 2 streams. ThreadPoolExecutor(2). Thread-safe checkpoint. |
| `scripts/benchmark/seeding_port_sets.py` | NEW — port set definitions (STREAM_A, STREAM_B). |

**Key details**:
- Pass `server_urls` dict in ChatRequest to pin each stream to its port set (field already exists)
- Scope slot erasure to stream's own ports only
- Thread lock around checkpoint JSONL writes
- Ingest (1 instance, 8085) could contend — rare in seeding, acceptable

**Expected impact**: 2× throughput (10-20 min trials instead of 20-40). Same quality/speed measurements (no cross-stream contention). Fallback: use original `seed_specialist_routing.py` if anything breaks.

**Deferred**: 4-stream parallelism — requires adding 3rd/4th architect instances on remaining NUMA quarters.

- [ ] **PS-1: Implement `parallel_seeding.py` + `seeding_port_sets.py`** — ~200 LoC total. Tracked as NIB2-12 in non-inference-backlog.
- [ ] **PS-2: Update `orchestrator_stack.py` port docs** — reflect 8080-8084 / 8180-8184 stream split once PS-1 lands. Tracked as NIB2-29.

### P9 — Legacy Cleanup & Operational Debt

Extracted from archived `rlm-orchestrator-roadmap.md` (Section 4, Follow-On Tasks). Independent — can be done any time.

- [x] **LC-1: Delegation SLO report** — ✅ 2026-04-04. `scripts/server/delegation_slo_report.py` parses progress JSONL logs, computes p50/p95/p99 latency, success/failure/timeout rates, delegation lineage distribution, escalation paths, per-role latency breakdown. Supports `--date`, `--from/--to`, `--json`.

- [x] **LC-2: Chain anomaly detection** — ✅ 2026-04-05. `scripts/server/chain_anomaly_detector.py` parses progress JSONL for: escalation path concentration, role concentration, failure rate, multi-hop anomaly, stale tasks, wave stalls, failure patterns. Supports `--date`, `--from/--to`, `--json`.

- [x] **LC-3: Remove `worker_code` legacy naming** — ✅ 2026-03-29. Removed from model_registry.yaml (both full and lean), orchestrator_stack.py port map, inference.py comment, 2 doc chapters. Historical benchmark JSON preserved.

- [x] **LC-4: Shared-result cache for delegation** — ✅ 2026-04-05. `delegation_cache.py` — in-memory SHA-256 keyed cache (brief+target), 1h TTL, 200 max entries. Integrated into architect delegation loop: cache check before specialist execution, store after compression. Cache hits in `delegation_diagnostics`. 10 tests.

- [x] **LC-5: Fix health probe for `full:` prefix URLs** — ✅ 2026-04-04. `_probe_core_backends()` in `health.py` now strips `full:` prefix and takes first URL from comma-separated lists before probing.

---

## Cross-Cutting Concerns

Check these before modifying any subsystem — changes in one affect the others.

### 1. Q-Scorer Baselines ↔ Stack Config
`routing-intelligence.md` § baselines defines per-role t/s used by `q_scorer.py`. If the stack changes (different models, instance counts), `baseline_tps_by_role` MUST update. ~~**Current issue**: frontdoor baseline stale (RI-0).~~ ✅ Fixed 2026-03-29 (frontdoor 19.6→12.7, architect_coding 7.0→8.0).

### 2. Routing Quality → Stack Capacity
High escalation rate from routing means more specialist instances needed. Low escalation rate means more frontdoor instances may be optimal. Routing classifier quality directly affects what the scheduler provisions.

### 3. Autoresearch Scope Includes Stack
The `program.md` governs what autoresearch can modify. Stack-config (models, instances, NUMA, tiers) is an optimization axis alongside routing params and prompts. StructuralLab species handles stack experiments.

### 4. Factual Risk → Resource Allocation
When risk-aware routing goes to enforce (RI-2 through RI-6), high-risk prompts trigger escalation to larger models. The stack scheduler must anticipate architect demand from the risk score distribution.

### 5. Conversation Logs Feed All Three
Observed patterns inform routing (Q-value training), autopilot (experiment evaluation), and stack (demand patterns, tier utilization). This mirrors episodic memory's Q-value accumulation loop.

**Operationalized 2026-04-25**: [`unified-trace-memory-service.md`](unified-trace-memory-service.md) (stub) collapses `agent_audit.log` + `progress/` + `autopilot_journal.{tsv,jsonl}` + `autopilot_state.json` into a single SQLite query layer for cross-source provenance queries during autopilot debugging and post-nightshift analysis. **Not** a replacement for autopilot's evolutionary memory (`repl_memory/strategy_store.py`, episodic store, skill bank) or Hermes's conversation memory — those remain domain-specific. Cross-link: include `trial_id` in both the unified store and `strategy_store` so an insight can link back to its source events.

### 6. KV Cache Config ↔ Stack Capacity
`kv-cache-quantization.md` — Hadamard + q4_0 K / f16 V is the production KV config. DS-3 (`--slot-save-path`) interacts with KV quantization config — if KV type changes, save/restore format may need updating. Dynamic stack assembly (DS-6) must account for per-model KV quantization when computing memory budgets.

### 7. Context Folding ↔ AutoResearch Baseline
`context-folding-progressive.md` Phase 0-1 (compaction trigger + two-level condensation) changes session quality behavior. The autoresearch baseline (AR-1) should be captured AFTER Phase 0-1 is deployed, or the "before" number will reflect a compaction policy that is about to change. Phase 3 process rewards feed MemRL Q-value enrichment (routing-intelligence Phase 5). **Updated 2026-04-05**: Phase 2 now includes free-zone threshold sweep and helpfulness scoring (intake-261/262); Phase 3 now includes role-aware compaction profiles that parameterize aggressiveness per orchestrator role. Phase 3b role profiles will directly affect autopilot token costs — `worker_explore` gets more aggressive compaction than `worker_coder`. **Updated 2026-04-05 (session 4)**: Phase 1+ (SegmentCache), 2c (helpfulness scoring), 3a (process rewards), 3b (CompactionProfile + CompactionQualityMonitor) all code-complete with 32 unit tests. Feature flags: `segment_cache_dedup`, `helpfulness_scoring`, `process_reward_telemetry`, `role_aware_compaction` (all off by default).
**Updated 2026-04-06**: Phase 2c ByteRover enhancement (intake-267) adds compound retention scoring (access_count, importance_score, maturity_tier with hysteresis) to `segment_helpfulness()`. Design documented in handoff. Implementation after Package C — uses Package C Δ_k ground truth for weight calibration.

### 9. Instruction Budget ↔ PromptForge Mutations
intake-272 (ETH Zurich) shows context files increase inference cost by 20%+ without improving success rates. Every PromptForge mutation that adds instructions must be evaluated against instruction overhead (AP-16). AP-17 provides the corrective mechanism — structural pruning to reduce instruction load. Agent files should target ≤400 words of toolchain-only instructions (intake-271). This constrains both `prompt_mutation` and `code_mutation` species: quality gains that come with >15% instruction overhead increase should be scrutinized.

### 10. GEPA ↔ Multiple Subsystems
`autopilot-continuous-optimization.md` P10 (GEPA PromptForge Integration) and `meta-harness-optimization.md` Tier 2b/MH-4 (GEPA as search algorithm) evaluate the same technique from two perspectives. Autopilot owns implementation (AP-18–21: DSPy signature wrapping, optimize_anything, Full Program Adapter). Meta-harness evaluates whether GEPA's Pareto-frontier selection outperforms our current top-1 selection as a search algorithm. Results from either inform the other. Source: 2026-04-12 research intake (intake-327/345/240).

### 11. SearXNG Backend ↔ Web Search Pipeline (P8b)
`searxng-search-backend.md` replaces the DDG/Brave scraping layer that P8b's WS-1/WS-2/WS-3 fixes operate on. SearXNG is orthogonal to prompt-level over-reliance fixes but changes the search result quality and metadata available to the pipeline. When SearXNG is deployed: (a) WS-2 Omega re-measurement should use SearXNG results, not DDG HTML, (b) `unresponsive_engines[]` telemetry feeds the same monitoring pipeline as DS-1 queue depth. Source: 2026-04-14 research intake (intake-359/360/361).

### 12. Decision-Aware Routing ↔ Difficulty Signal ↔ AP-27
`decision-aware-routing.md` P13 addresses the zero-predictive-spread pathology diagnosed in Package B Phase 4 (research-eval P0). If contrastive Q-scoring (DAR-2) resolves the flat-band problem, `difficulty_signal.py` may become useful as a routing feature again. DAR-4 (model-feature-conditioned Q) interacts with AP-27 (RLVR eval tower) because the verification framework must evaluate the new routing reward signal. Source: 2026-04-14 deep-dive research (intake-366).

### 13. Math-Verify Ground Truth ↔ Decision-Aware Routing
intake-377 (2026-04-15 deep-dive) shows exact-match scoring underestimates math model capability by ~66% (Math-Verify accuracy 0.1328 vs lm-eval-harness 0.0802). DAR-3/DAR-4 reward signals in `decision-aware-routing.md` derive from eval tower scoring. If Q-scorer trains on exact-match rewards that systematically undercount correct math answers, Q-values will be biased toward models producing parseable outputs, not correct ones. Math-Verify must be adopted in the scoring pipeline before DAR-3 SPO+ training begins. See `eval-tower-verification.md` Research Intake Update 2026-04-15 for integration caveats (NOT symmetric, NOT thread-safe). Deep dive: `research/deep-dives/math-verify-integration-analysis.md`.

### 8. Conversation Mgmt B2 ↔ Context Folding Phase 1
`orchestrator-conversation-management.md` B2 (protected-zone compression from Hermes/OpenGauss) and `context-folding-progressive.md` Phase 1 (two-level condensation) both modify session compaction behavior. They must be sequenced — context-folding Phase 1 should land first as the structural upgrade, then B2's protected-zone logic can layer on top. Alternatively, B2's tool-pair sanitization (`_sanitize_tool_pairs()`) could be extracted as a standalone prerequisite for both. **Updated 2026-04-05**: Context-folding Phase 3b (role-aware compaction profiles) must align with B2's role taxonomy — the `CompactionProfile` roles must match the conversation management role definitions. **Updated 2026-04-05 (session 4)**: `CompactionProfile` roles now defined (`architect`, `worker_coder`, `worker_explore`, `worker_fast`) with `get_compaction_profile()` in `session_log.py`. B2 can now reference these profiles directly. `segment_helpfulness()` + `prioritized_compaction()` available as building blocks for B2's protected-zone logic.

---

## Dependency Graph

```
✅ P0 (wiring bugs) ──────────── DONE (AP-1–3, RI-0)
✅ P1 (routing Phase 4 code) ─── DONE (RI-2–6). RI-1 + RI-7 need compute.
✅ P2 (autopilot structural) ─── DONE (AP-4–8, 10, 12)
✅ P4 (observability) ─────────── DONE (DS-1–4)
✅ CF Phase 0+1 ───────────────── DONE (trigger + two-level condensation)
✅ P8 (autopilot refinements) ─── DONE (AP-9, 11, 13)
✅ P9 (legacy cleanup) ────────── DONE (LC-1–5)
  │
  ├── ✅ PACKAGE A ──────────────── DONE (2026-04-06, 635 decisions, thresholds recalibrated)
  │     │                            CF Phase 1 validation + difficulty signal + RI-9 profiling + TrimR
  │     │                            Output: data/package_a/<timestamp>/
  │     │
  │     ├── ✅ PACKAGE B ────────── DONE (2026-04-10). TrimR +6pp, tool A/B +4pp, WS-3 validated, Omega measured.
  │     │     │                       RI-9 + TrimR + difficulty + Omega + tool A/B
  │     │     │
  │     │     └── PACKAGE D (active) ── AR-3 trial ~78 + RI-10 Canary (to 2026-04-27) + CF-3c + DS-5
  │     │                               AR-3 relaunched with 39 sentinels. LG Phase 3 INGEST flag not yet flipped.
  │     │
  │     ├── PACKAGE C ────────────── CF Eval Batch (~½d, individual models, independent)
  │     │                             CF Phase 2a/2b/2c
  │     │
  │     └── PACKAGE E ────────────── Vision + Hermes validation (~1h, independent)
  │
  ├── DS-C (pre-warm deploy) ──── HIGH PRIORITY. No dependencies.
  │     Add 1×96t + 4×48t instances for frontdoor/coder/worker.
  │
  ├── DS-D (concurrency router) ── Depends on DS-C.
  │
  ├── P5 (autoresearch) ──────── AR-3 relaunch = Package D.
  │
  ├── P3 (routing Phase 5) ──── depends on P1 A/B results
  │
  └── DS-E/F (templates, prediction) ── after DS-D + P5 data
```

---

## Reporting

After completing any task group, update:
1. The task checkbox in this index (mark `[x]`)
2. The relevant handoff document (update status, add implementation notes)
3. `progress/YYYY-MM/YYYY-MM-DD.md` with session summary
4. `CHANGELOG.md` if the change is significant

---

## Upstream Dependencies

This index consumes data and findings from:

| Source | Handoff | What It Provides |
|--------|---------|-----------------|
| Inference acceleration | [`inference-acceleration-index.md`](inference-acceleration-index.md) | Benchmark results, model speed/quality data, NUMA deployment findings. Stack config changes originate from acceleration work. |
| KV cache quantization | [`kv-cache-quantization.md`](../completed/kv-cache-quantization.md) | Production KV config (`--kv-hadamard -ctk q4_0 -ctv f16`), memory budget inputs for stack planning. |

Changes in upstream handoffs may invalidate assumptions in this index (e.g., model speed numbers, memory footprints). After any upstream deployment, verify RI-0 baseline and stack table in `dynamic-stack-concurrency.md`.

## Related Infrastructure

These handoffs are tracked in other indices but have cross-cutting impact here:

| Handoff | Index | Relevant Aspects |
|---------|-------|-----------------|
| [`context-folding-progressive.md`](context-folding-progressive.md) | this index | Phase 3a process rewards feed routing intelligence; Phase 3b role-aware profiles affect per-role token costs; Phases 0-2 compaction mechanics |
| [`tool-output-compression.md`](tool-output-compression.md) | research-evaluation | RTK/native hooks reduce context pressure, interacts with autopilot token costs |
| [`reasoning-compression.md`](reasoning-compression.md) | research-evaluation | TrimR/difficulty_signal shares scorer infra with factual-risk routing |
| [`bulk-inference-campaign.md`](bulk-inference-campaign.md) | this index | Packages B-E consolidate 14 inference tasks; B feeds RI-9/TrimR, D feeds AR-3/RI-10/DS-5 |
| ~~[`rlm-orchestrator-roadmap.md`](../completed/rlm-orchestrator-roadmap.md)~~ | archived | Follow-on tasks extracted to P9. |
| [`searxng-search-backend.md`](searxng-search-backend.md) | standalone | Web search backend replacement; affects P8b search pipeline and ColBERT reranker input |
| [`decision-aware-routing.md`](decision-aware-routing.md) | this index (P13) | Decision-aware Q-scorer: contrastive + SPO+ + bilinear model-feature scoring |
| [`unified-trace-memory-service.md`](unified-trace-memory-service.md) | standalone (stub 2026-04-25) | Cross-source provenance store over `agent_audit.log` + `progress/` + `autopilot_journal.*` + `autopilot_state.json`. Operationalizes Cross-Cutting Concern §5 above. Read-only query layer; no migration of existing writers. Useful during autopilot debugging and post-nightshift "why did we decide X" investigations. |

---

## Key File Locations

| What | Where |
|------|-------|
| Factual risk scorer | `epyc-orchestrator/src/classifiers/factual_risk.py` |
| Q-scorer baselines | `epyc-orchestrator/orchestration/repl_memory/q_scorer.py` |
| Autopilot scripts | `epyc-orchestrator/scripts/autopilot/` |
| Autoresearch strategy | `epyc-orchestrator/scripts/autopilot/program.md` |
| Safety gate | `epyc-orchestrator/scripts/autopilot/safety_gate.py` |
| Classifier config | `epyc-orchestrator/orchestration/classifier_config.yaml` |
| Stack launcher | `epyc-orchestrator/scripts/server/orchestrator_stack.py` |
| Round-robin backend | `epyc-orchestrator/src/backends/round_robin.py` |
| Seeding types | `epyc-orchestrator/scripts/benchmark/seeding_types.py` |
| Model registry (full) | `epyc-inference-research/orchestration/model_registry.yaml` |
| Debug suite pool | `epyc-inference-research/benchmarks/prompts/question_pool.jsonl` |
| Model registry (lean) | `epyc-orchestrator/orchestration/model_registry.yaml` |
| KV cache config | `epyc-llama` production branch (`--kv-hadamard` flag in `orchestrator_stack.py`) |

## Research Intake Update — 2026-04-07

### New Related Research (intake-275 deep-dive)
- **[intake-275] "PufferLib 4.0"** — Not directly applicable, but deep-dive uncovered lightweight RL routing alternatives:
  - **BaRP** (arXiv:2510.07429): Lightweight policy network + bandit feedback, preference-conditioned. 16.8% better than GraphRouter at 50% less cost. Most directly applicable to our stack.
  - **PROTEUS** (arXiv:2604.00136): Lagrangian RL with explicit cost constraints. Minimizes cost subject to accuracy floor — matches our cost-aware routing philosophy.
  - **LLM Bandit** (arXiv:2502.02743): Online bandit that transfers across unseen models.
  - **Key insight**: A tiny MLP routing policy (~5-10k params, 2x64 hidden) trained via PPO on our seeding diagnostics data could replace heuristic routing rules. Sub-microsecond inference. Deploy as 50 lines of C linked into orchestrator.
  - **vs xRouter (7B)**: xRouter reads full prompt text; tiny MLP operates on pre-extracted classifier features. We already have the feature pipeline (factual_risk, difficulty_signal, keyword classification). The RL policy sits on top.
  - **Action**: Queue BaRP, PROTEUS, LLM Bandit for next intake batch. Evaluate offline RL feasibility on Package A data.

## Research Intake Update — 2026-04-22

### New Related Research (intake-425/426 deep-dive)
- **[intake-425] "Memory Transfer Learning: How Memories are Transferred Across Domains in Coding Agents"** (arxiv:2604.14004)
  - 4 adoptable patterns for strategy_store and PromptForge: (1) Insight abstraction format `(title, description, generalized_content)` with no task-specific details, (2) N=3 embedding retrieval validation (embedding > LLM reranking > adaptive rewriting), (3) negative transfer safety gates (3-category taxonomy), (4) task-agnostic > task-specific insights (+1.1%). See P16 (AP-32/33/34) above.
- **[intake-426] "Dive into Claude Code: The Design Space of Today's and Future AI Agent Systems"** (arxiv:2604.14228)
  - Graduated trust model for routing confidence thresholds: new models start conservative (~20% auto-approve at <50 sessions), relax as benchmarks accumulate (40% at 750+ sessions). Pattern applicable to RI-10 canary and learned routing controller work. No new task code — design pattern absorbed into existing P6/P13.
  - Input-only classification (anti-gaming pattern): Claude Code's permission classifier sees user request + tool call but NOT model reasoning — prevents model from influencing its own safety gate. Validates current `factual_risk.py` design which classifies on input features only. No code change needed.

## Research Intake Update — 2026-05-19

### Evolution Strategies at LLM scale — full-cluster ingest with mandatory evaluation protocol

This batch adds four ES-at-LLM-scale papers that together significantly expand the gradient-free post-training tier of this index. **Read together they sharpen — not just extend — what we can say about ES vs gradient RL for routing/coordinator training.**

- **[intake-532] EGGROLL** (arxiv:2511.16652, Foerster lab — Oxford/Mila, Courville/Whiteson/Hodjat/Miikkulainen lineage)
  - **Mechanism**: rank-r perturbations recover near-inference arithmetic intensity at hyperscale → ~100× throughput at billion-parameter scale, 91% of pure batch-inference throughput.
  - Pretrains int8 nonlinear RNNs (EGG) end-to-end with no backprop; competitive with GRPO for RWKV post-training on countdown/GSM8K.
  - **EPYC role**: natural escalation beyond Trinity sep-CMA-ES (intake-474) on the routing/coordinator stack. PDF body could not be parsed directly (binary); content from project landing page + arxiv abstract.

- **[intake-563] Evolution Strategies at Scale** (arxiv:2509.24372, Cognizant AI Labs)
  - **Result that matters most for EPYC**: pop=30 suffices for billion-parameter LLM fine-tuning. 30 parallel forward passes on a 1B GGUF fit in 1.1 TB RAM with the NUMA-concurrent stack (per `project_concurrent_split_throughput`) — opening a CPU-only fine-tuning path for small drafters/q-scorer heads that would otherwise have no training avenue.
  - Outperforms PPO/GRPO across multiple axes (long-horizon tolerance, robustness, reduced reward-hacking, training stability).
  - Erodes the "EGGROLL requires huge populations" framing: if pop=30 is enough, EGGROLL's throughput advantage shrinks at the actual operating point.

- **[intake-564] ESSA** (arxiv:2507.04453, T-Bank/Yandex lineage) — **single most EPYC-relevant paper in the cluster**
  - **INT4/INT8 quantized inference for fitness evaluation** — the only ES-LLM paper that runs the optimizee in low-bit quant. This is exactly what EPYC's CPU stack does best (`project_q8_8x8_avx512bw_outcome` documents +31.8% at 1t for our AVX-512BW Q8_0 kernel).
  - LoRA-SVD parameter-space restriction (~thousands of singular values vs billions of weights) keeps the search space tractable at modest population sizes.
  - +12.6% GSM8K, +22.5% IFEval; 6× faster than GRPO on 128 GPUs to near-optimal.
  - **Concrete spike candidate (CPU-only, no GPU acquisition required)**: take a Qwen2.5-7B Q4_K_M GGUF, instantiate a ~512-singular-value LoRA-SVD parameter space, run a 200-iteration ES loop (population=16, NES variant) with GSM8K-test as fitness oracle on EPYC. Spike succeeds if any GSM8K delta >2pp under <1 nightshift of compute. **Defer until user approval per `feedback_no_concurrent_inference` and `feedback_speed_verify_via_llama_bench`.**

- **[intake-565] Matching Accuracy, Different Geometry** (arxiv:2604.01499, Hoy/Wang/Pan — Harvard + Miami) — **the qualifying study**
  - ES and GRPO **match on task accuracy** but produce **nearly orthogonal update directions** in parameter space.
  - ES induces **substantially larger off-task KL drift** than GRPO; ES updates are broad, GRPO localized.
  - Sequential continual-learning: ES competitive **only when iteration budget is capped** — otherwise catastrophic forgetting is worse than GRPO.
  - **Why this matters**: EGGROLL/ES-at-Scale/ESSA all report accuracy parity with GRPO. None of them report off-task KL or continual-learning behavior. Hoy 2026 shows the equal-accuracy outcome **masks materially different model behavior off-task**.

**ES-LLM evaluation protocol (mandatory before any in-house ES spike)**:
1. **Accuracy on training task** (standard).
2. **Accuracy AND KL on ≥1 held-out off-task distribution** (per Hoy 2026 off-task drift finding).
3. **Linear-mode-connectivity to the gradient-trained baseline** when available (sanity check that the solution sits on the same loss basin).
4. **Iteration-budget control as a first-class hyperparameter** in any sequential/continual-learning setting (Hoy 2026: this is the critical knob preventing forgetting).

Trinity (intake-474) is **grandfathered**: its frozen-backbone sep-CMA-ES-on-a-small-head design sidesteps the off-task-drift mechanism (backbone weights don't move). New full-parameter ES proposals **must** meet the four-point protocol above before adoption.

### Post-deep-dive stub spawn — handoffs/active/

The May 2026 cluster deep-dives (8 documents, `research/deep-dives/2026-05-19-*.md`) spawned **4 ready-to-claim handoff stubs** wired into the master priority queue items #42-#45:

- **[`rao-redel-substrate-spike.md`](rao-redel-substrate-spike.md)** (master P#42 HIGH) — RAO substrate via ReDel toolkit; 3-step gated spike; depth=1 default per Wang reproduction caveat; wires 5-sub-decision orchestration-trace taxonomy into episodic store.
- **[`x-mas-text-routing.md`](x-mas-text-routing.md)** (master P#44 HIGH) — heterogeneous text-MAS lookup (domain × function → winner-model) on our 4-model stack; **zero llama.cpp changes**; composes with `learned-routing-controller.md` as a routing prior. **Cheap-kill failure mode**: if gemma4-26B-A4B wins ~all cells, heterogeneity is moot and the spike aborts.
- **[`delta-mem-reproduction.md`](delta-mem-reproduction.md)** (master P#43 HIGH) — δ-mem released-checkpoint reproduction + M.3 KV-Extension prototype + δ-mem GGML port. Falsified baseline finding: current B1 User Modeling = functionally M.1 Prefix → collapses at low capacity.
- **[`streaming-llm-baseline.md`](streaming-llm-baseline.md)** (master P#45 MED) — gate for the KV-reduction cluster prioritization (LU-KV / KVP / ForesightKV / PBKV / SP-KV all measured against sink+window floor).

**ES cluster status** (intake-532/563/564/565): still tracked under the Hoy 2026 4-gate protocol above. ESSA spike (CPU-feasible via Q4_K_M LoRA-SVD) remains the prime ES-cluster candidate but is **lower priority than the 4 stubs above** because it requires per-bench user approval per `feedback_no_concurrent_inference` and the Trinity retroactive audit (cheapest ES gate) is not yet scheduled.

## Research Intake Update — 2026-05-25 (intake-605/607 deep dive)

Deep dive of **intake-605 (Repo Prompt)** + **intake-607 (Code as Agent Harness)** — full feature reverse-engineering + open-problems read. intake-605 relevance raised medium→high (reframed from "closed-source, not deployable" to **competitor-feature-mining**: the open-source-only rule governs *deploy*, not *analyze*). Spawned **2 new handoffs** (P22/P23) + **task additions to 4 existing handoffs** (P24/P25). 2026-05-25 audit pass converted the initial brainstorm into implementation-grade contracts: provenance-bearing context bundles, deterministic-first patch apply, calibrated harness metrics, process-level behavior signatures, uncertainty calibration gates, and governed failure-memory retrieval. Inference-gated tasks honor `feedback_no_concurrent_inference` + `feedback_speed_verify_via_llama_bench`.

### P22 — Budget-Bounded Context Pre-Assembly for Delegation (intake-605)

New handoff [`delegation-context-preassembly.md`](delegation-context-preassembly.md). The *assemble* side of context engineering (context-folding owns *evict*). Sharper on CPU than the cloud system it came from (unearned tokens = DRAM-at-decode; bloated prefill = pure latency).

- [x] **DCP-1** ContextBundle data model + per-file `full|slices|codemap_only` modes w/ merged line-ranges, content hashes, source provenance, inclusion/exclusion reasons, and stable manifest IDs (substrate; net-new)
- [x] **DCP-2** Budget-bounded two-pass assembly loop (cheap metadata ranking → selective body reads → token-verify→add/drop/slice→fit); budget is a per-role parameter with explicit reserves, not a fixed 60k
- [x] **DCP-3** CodeMaps-as-budget-class via dependency-free AST codemap producer with content-hash/index-commit cache and stale-index fallback (GitNexus runtime dependency deferred)
- [x] **DCP-4** Wire pre-assembly into dispatcher/escalation as a seed bundle plus bounded reactive top-ups (flag default-off; reactive discovery remains enabled; validated by `tests/unit/test_dcp4_wiring.py`)
- [ ] **DCP-5** Non-prescriptive discovery prompt as a PromptForge mutation (A/B via autopilot), preserving evidence and uncertainty while withholding solutions
- [ ] **DCP-6** Eval on delegation-heavy workload: prefill/latency/quality/top-up count/hallucinated refs/context contamination vs reactive-discovery baseline (offline replay first; inference-gated) — **CODE-READY 2026-05-27** (DCP-4 advisory attach landed/default-off; no longer blocked by BEP read-loop)

### P23 — Batched Structured Editing + Parallel Apply Fan-out (intake-605)

New handoff [`batched-edit-parallel-apply.md`](batched-edit-parallel-apply.md). Think-then-act batch edit (collapse tool round-trips) + fan per-file apply across NUMA quarters.

**2026-05-26/28 — P22/P23 code wired (default-off) + falsification harness compacted.** BEP `_execute_turn` divergence (`ea5f010`) + DCP-4 advisory pre-assembly (`31ea6d4`) are wired behind `batch_edit_mode` / `dcp_pre_assembly` (both default-off, tested). BEP-2 remediation is now the separate default-off edit transaction; [`bep-dcp-falsification-harness.md`](bep-dcp-falsification-harness.md) remains active for DCP-6 and optional J8 provenance only, with task-root harness history in its completed ledger.

**2026-05-27 — BEP-2 diagnosis superseded the original rework gate.** The direct one-shot ablation proved Qwen3.6 can solve the five multi-file/read-first tasks 5/5 with the same verifiers; the failure was the read->peek->edit->FINAL REPL/BEP contract. The default-off `force_mode="edit"` transaction is now built/hardened as the practical remediation. Therefore **J8/BEP-2 is optional**: run it only to decide the legacy structured patchset/batch-edit path's keep/retire/task-scope fate. **DCP-6 is separate and code-ready** because DCP-4 advisory attach is already wired/default-off.

- [ ] **BEP-1** Batch-edit mode: bounded evidence phase, then emit one typed structured patch set with base repo/file hashes and cross-file dependency metadata (flag default-off)
- [ ] **BEP-2 / J8** CPU latency A/B vs interleaved Root LM loop — round-trips/prefill/latency/quality plus parse/apply/verify failure rates (offline replay first; inference-gated) — **OPTIONAL DECISION EXPERIMENT 2026-05-27** for the legacy `batch_edit_mode` path only; not the practical multi-file remediation gate
- [ ] **BEP-3** Autopilot StructuralLab knob batch-vs-interleaved (gated on BEP-2 positive)
- [ ] **BEP-4** Deterministic-first parallel apply fan-out across 32×6t NUMA split + independent per-file verify; optional LM repair lane only after explicit inference approval
- [ ] **BEP-5** General sandbox/worktree-before-disk + stale-base rejection + granular accept/reject over a coherent staged diff; whole-repo verify before commit

### P24 — Harness-Level Evaluation Metrics + Oracle Adequacy (intake-607 §5.2.1 / §5.2.7)

Tasks added to [`meta-harness-optimization.md`](meta-harness-optimization.md) (HLE-1/2/3) and [`autopilot-continuous-optimization.md`](autopilot-continuous-optimization.md) (HLE-4). Stop optimizing the harness against final-task-success alone; score intermediate behavior + an oracle-adequacy meta-metric; adopt hold-model-fixed/vary-harness benchmarking.

- [x] **HLE-1** Per-component harness metrics from structured traces with evidence event IDs and confidence: execution fidelity, feedback interpretation, planning stability, memory coherence, recovery rate (meta-harness) — rule-based observe-only implementation landed in epyc-orchestrator `9222a19`
- [x] **HLE-2** Oracle-adequacy meta-metric per suite including blind spots, shortcut risk, determinism, and review status (meta-harness; addresses P8b web-search-shortcut) — default oracle-adequacy registration landed in epyc-orchestrator `9222a19`
- [ ] **HLE-3** Harness-isolating benchmark lane: fixed model/server/retrieval snapshot, vary one harness component at a time (meta-harness)
- [ ] **HLE-4** Per-component metrics as observe-only fields first, then Pareto co-objectives/guardrails only after predictive-signal analysis (autopilot)

**Additional task additions (existing handoffs):**
- **Uncertainty-routed escalation** → [`decision-aware-routing.md`](decision-aware-routing.md) URE-1/2/3 (calibrated decision uncertainty as a second escalation axis; bounded approval-as-harness-state; uncertainty as routing feature only after ECE/abstention gates) — intake-607 §5.2.5.
- **Experiential memory** → [`unified-trace-memory-service.md`](unified-trace-memory-service.md) EXM-1/2/3 (index failed trajectories with root-cause/avoidance metadata; externalize lifecycle-managed working state; governed-experience tier) — intake-607 §3.2.1/§3.2.3.

### P26 — Swarm Scoring & Routing Cluster (intake-614/615/616, 2026-05-27 research intake)

Three interlocking tasks emerged from intake-614/615/616 (Fortytwo Network — swarm inference with peer-ranked consensus). They share a single Bradley-Terry implementation; do not duplicate it across handoffs.

- [x] **P26.1 ✅ 2026-05-27 (cheap axis-vote proxy form)** — **Bradley-Terry tiebreak in NumericSwarm**: P17.BT-1 + P17.BT-2 landed in epyc-orchestrator (commit `2e51c86`; repair `60ed552`; scale-bias fix `56ee9fc`; rename + scope-honesty `45df95c`). Shared module **now at `src/bradley_terry.py`** (moved from `scripts/autopilot/` during DAR-6 scaffolding on 2026-05-27 to keep it a single source of truth) + `ParetoArchive.bt_tiebreak_topk()` wired into stagnation-handler rich prompt. 24 new unit tests pass. **Important caveat: the wired path uses axis-vote / Borda counting over the already-recorded 4D objectives, NOT Fortytwo-style peer-ranked consensus from independent judge models** — that is P17.BT-4 and is INFERENCE-GATED + deferred. P17.BT-3 (falsification autopilot run) is the next gate. Tracked in [`autopilot-continuous-optimization.md`](autopilot-continuous-optimization.md) § P17. **Shared BT module now also consumed by P26.2 (DAR-6.4) and P26.3 (swarm-distillation Phase 3) — do not reimplement.** Sub-task IDs use `P17.BT-N` namespace to avoid collision with existing `AP-37/38/39/40` from the 2026-05-23/24 constrained-creativity + launcher-threadcount work.
- [x] **P26.2 ✅ partial 2026-05-27 (scaffolding done; A/B inference-gated as J14)** — **DAR-6 swarm-fanout routing mode**: DAR-6.1 feature flag (`features().swarm_fanout`, default-off prod+test), DAR-6.3 dispatch (`dispatch_swarm_fanout` in `src/swarm_fanout.py`), DAR-6.4 BT aggregator (`bradley_terry_aggregate`) all landed. 15 new unit tests pass. **No production routing change** — default-off + no default aggregator (caller must opt in to both). Remaining: DAR-6.2 (injection-risk classifier in [`routing-intelligence.md`](routing-intelligence.md), not yet built — only needed for conditional routing; cheap-first DAR-6.5 A/B can run unconditionally without it) + DAR-6.5 itself (J14 in [`bulk-inference-campaign.md`](bulk-inference-campaign.md)). Tracked as DAR-6 in [`decision-aware-routing.md`](decision-aware-routing.md).
- [ ] **P26.3 — Swarm-as-dataset-generator pipeline** (HIGH-conditional): full multi-week pipeline at [`swarm-dataset-distillation.md`](swarm-dataset-distillation.md). Gated on [`strand-rust-coder-rustevo2-verification.md`](strand-rust-coder-rustevo2-verification.md) (Phase 1 verification of the founder's RustEvo2 claim). If gate clears, this becomes the highest-value harvest from the Fortytwo intake. **BT dependency already satisfied** — Phase 3 uses the same `src/bradley_terry.py` module shared with P26.1/P26.2.

**Sibling consolidation**: [`autopilot-continuous-optimization.md`](autopilot-continuous-optimization.md) § Scoring Upgrade Backlog now ties this entry together with prior intake-248 (SiliconSwarm) and intake-269 (TPO/CEM) scoring-mechanism upgrades. Read that section before starting any P26.x work to avoid redundant CEM / BT implementations.

### P25 — Regression-Safe Self-Improvement: Behavior-Signature Versioning (intake-607 §5.2.3 / §5.2.4)

Tasks added to [`autopilot-continuous-optimization.md`](autopilot-continuous-optimization.md). We are ahead on scalar regression gating but merge improvements syntactically — a new config can silently break a prior Pareto win.

- [ ] **BSV-1** Behavior signature per archive member; include final outcome plus route path, tool sequence, escalation path, latency/token buckets, harness metrics, and oracle-adequacy version
- [ ] **BSV-2** Differential testing on accept (paired new-vs-old on same sentinels; prefer sequential controlled runs unless concurrency is explicitly approved; compare behavior and scalar score)
- [ ] **BSV-3** Conflict-aware acceptance for mutations touching the same subsystem with a mutation-dependency ledger and signature-delta severity classes

### Cross-cutting / dependencies (this batch)

- **P22 ↔ context-folding-progressive**: assemble vs evict; must share segment-importance heuristics (extends CCC #7).
- **P22 → P23**: a pre-assembled bundle feeds a clean think-then-act batch edit.
- **P24 ↔ P25 ↔ HALO (P20)**: per-component metrics are candidate fields for the HALO analyzer surface; harness-isolating benchmarks gate both.
- **P24/P25 ↔ AP-27 (RLVR eval tower)**: the verifier must score the augmented reward/objectives.
- **URE ↔ CCC #12** (decision-aware routing ↔ difficulty signal) and **eval-tower P8 calibration** (uncertainty must be calibrated).
- **P24/P25/URE/EXM shared schema — OWNED by [`unified-trace-memory-service.md`](unified-trace-memory-service.md) § "Shared Harness/Trace Schema"** (gap-fix 2026-05-25): `harness_metrics`, `oracle_adequacy`, `behavior_signature`, approval records, and `failure_case`/`working_state` are ONE versioned event family in `src/trace`, cross-linked by `event_id`. HLE/BSV/URE consume it; they must not define private schemas. **Build the shared schema first.**

**Implementation spine (cross-handoff critical path, gap-fix 2026-05-25):**

```
[EXM-1/EXM-2 shared trace schema in src/trace]   ← foundation, build first  (DONE: merged to main 2026-05-26)
        │
        ├─► HLE-1 (writes harness_metrics) ─► HLE-2 (oracle_adequacy)
        │        └─► HLE-3 (harness-isolating bench lane) ─► gates clean attribution for all evals
        │        └─► HLE-4 (autopilot consumes metrics, observe-only first)
        │        └─► BSV-1 (behavior_signature reuses the family) ─► BSV-2 ─► BSV-3
        │        └─► URE-2 (approval record links behavior_signature) ; URE-1 calib ─► URE-3
        │
[DCP-1 ContextBundle]  ─► DCP-2 ─► DCP-3 ─► DCP-4 ─► DCP-5 ─► DCP-6   (DCP-1/DCP-2/DCP-3/DCP-4 DONE; DCP-6 inference gate remains)
        └─(shared manifest)─► BEP-1 (batch edit records bundle ID) ─► BEP-4 ─► BEP-5 ; optional BEP-2/J8 decision ─► BEP-3
```

Recommended build order (non-inference): **(1)** EXM shared schema → **(2)** HLE-1/HLE-2 + DCP-1 + BEP-1 → **(3)** HLE-3 harness-isolating lane → **(4)** DCP-2/3/4, BEP-4/5 deterministic appliers, BSV-1, URE-1 logging-only → then the inference gates. **2026-05-27 update:** EXM schema, DCP-1/2/3/4, BEP edit-transaction remediation, HLE-1/2 observe-only metrics, and HLE-4 journal plumbing are now built; remaining work is mostly inference gates plus BSV/URE follow-through.

**Inference-gated eval order (gap-fix 2026-05-25, revised 2026-05-27):** all intake-607/605 inference gates are consolidated in [`bulk-inference-campaign.md`](bulk-inference-campaign.md) **Package J** to run in one operator window: **DCP-6 = J7, BEP-2 = J8, HLE-4 = J9, URE-1 = J10 (shadow), BSV-2 = J11**. J8 is no longer first or mandatory; it is a legacy batch-edit decision experiment. Current cheap-kill order: DCP-6 (J7) and HLE-4 observe-only (J9) are the directly actionable gates; URE-1 (J10) can accumulate passively during any run; BSV-2 (J11) runs per mutation; J8 runs only if its answer would change the `batch_edit_mode` keep/retire/task-scope decision. HLE-3's fixed-model lane underlies them so deltas attribute to the harness, not model drift. Each gate still requires its live-wiring prereq to be present and labelled in the manifest.

- Source of record: intake-605 + intake-607 `deep_dive` fields in `research/intake_index.yaml`. Surfaced in master priority queue items #51/#52.
