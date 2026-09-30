# Routing Intelligence: Factual-Risk Rollout

**Status**: ACTIVE. Live work is the routing audit RI-16..RI-20 (filed 2026-09-26). The factual-risk rollout (RI-10..RI-12) holds on `hold_quality_scored_no_lift` (packet 2026-07-06; § Start Here).
**Priority**: HIGH for RI-10 decision; MEDIUM for injection-risk fork after J14.
**Blocked by**: future scored factuality evidence showing enforce-arm lift, or an explicit operator-approved lower-evidence rollout decision.
**Completed ledger**: [`../completed/routing-intelligence-completed-through-2026-05-28.md`](../completed/routing-intelligence-completed-through-2026-05-28.md)
**Updated**: 2026-09-30 (RI-16 landed and deployed; RI-18 pre-registered, operator-approved)

## Start Here

**Current priority (2026-09-29):** RI-16, per-stage routing-decision latency (p50/p95) on live `/chat`; then RI-18, the
`_should_review` gate, unblocked by RI-22. The numbered steps below concern the older RI-10 factual-risk canary.

Do not implement the old Phase 4/5 sections from the completed ledger. They were superseded by RI-1 through RI-8 landing in March/April 2026. The next implementer should:

1. Pull current RI-10 canary data from logs before deciding anything; elapsed calendar time is not sufficient.
2. Confirm the current decision-ready sample still has enough arm-attributed rows in both enforce and shadow.
3. Use `scripts/analysis/ri10_canary_decision_report.py --scored-summary ...` to compare operational proxies with the attached scored factuality evidence. Current packet: `orchestration/reports/ri10_canary_decision_report_20260706T065654Z.{json,md}`.
4. Keep RI-11 frozen unless a future scored packet shows enforce-arm factuality lift, or the operator explicitly accepts a lower-evidence rollout decision.

Current 2026-07-06 refresh: live Fable/DS-E1 reads report `ri10_telemetry_collection_blocker=decision_ready`, and the scored canary response report is attached to the rollout decision packet. `epyc-orchestrator` `adf010b4` extends `ri10_canary_decision_report.py` with `--scored-summary`, generates `orchestration/reports/ri10_canary_decision_report_20260706T065654Z.{json,md}`, and records status `hold_quality_scored_no_lift`. The scored packet `ri10_canary_scored_summary_20260705T185001Z` is complete (`60/60` scored, no missing responses), but exact accuracy is tied (`3/30` enforce vs `3/30` shadow). The earlier 2026-07-04 reports (`ri10_canary_sample_report_20260704T095500Z.json`, `ri10_canary_sample_report_all_roles_20260704T005332Z.json`) and the 2026-07-05 `hold_quality_unscored` packet remain historical diagnostics only.

## Live Tasks

- [ ] **RI-10 — Shadow-to-enforce canary decision**: current canary is configured as 25% enforce / 75% shadow on `frontdoor`, `worker_general`, and `worker_vision`, and `7647b32e` exposes the chosen arm in routing progress metadata. The 2026-07-04 deterministic sampler fix makes future arm assignment stable per task id instead of process-RNG sampled, and the 2026-07-06 refresh shows telemetry depth and scored-response completeness are ready. Decision packet `20260706T065654Z` holds on `factuality_no_enforce_lift`; do not expand to RI-11 from favorable operational proxies alone. Decision requires:
  - controlled restart/window with `MEMRL_RETRIEVAL_RISK_CONTROL_ENABLED=true`; `ORCHESTRATOR_FACTUAL_RISK_MODE` is not the canary switch because it only accepts `off|shadow|enforce`;
  - >=50 arm-attributed high-risk samples or a documented reason to use a lower-powered decision; current refresh satisfies the depth gate with `31` enforce and `50` shadow high-risk rows;
  - no p95 latency regression >10%;
  - no cost regression >5% at equal factuality;
  - no unexplained escalation/review inflation >20%;
  - no 5xx/error cluster attributable to factual-risk scoring.
  - scored factuality/accuracy showing enforce-arm lift, or an explicit operator-approved lower-evidence decision. Current scored packet: `ri10_canary_scored_summary_20260705T185001Z` (`accuracy_delta=0.0`, token-F1 delta `+0.000531`).
- [ ] **RI-11 — Enforce expand**: if RI-10 passes, expand to frontdoor 100% plus worker_general for 7 days. Keep a rollback flag path to shadow.
- [ ] **RI-12 — Global enforce**: only after RI-11 passes; update dashboards/alerts and q-scorer baseline dependencies.
- [ ] **RI-9b — Threshold/Pareto sweep if thresholds change**: Package B already produced risk-distribution profiling. Run a fresh threshold sweep only if RI-10 suggests changing bands or enforcement thresholds.
- [ ] **RI-13 — Injection-risk classifier fork (DAR-6/J14)**: do not build until the cheap-first unconditional J14 swarm-fanout A/B clears its gate. If it clears, add an injection-risk axis to this handoff rather than burying it in DAR.
- [ ] **RI-X — New-model onboarding contract**: if learned-routing-controller P5.2 passes, document cold-start workflow here and link the `tools/onboard_specialist.py` wrapper from that handoff.

- [ ] **RI-16 — PRIORITY: measure end-to-end routing-decision latency on live `/chat`.** (filed 2026-09-26, code+live-process audit) A routed request makes ~3-4 embed+KNN lookups — role priors (`chat_routing.py:316-343` `_heuristic_role_priors` → `ClassificationRetriever`), route (`chat_pipeline/routing_decision.py:314` → `hybrid_router.py:388`), mode (`chat_routing.py:182` → `route_with_mode`), and the post-answer review gate (`chat_review.py:57-96`) — and none is timed; the "<1 ms MLP / 10-50 ms KNN" figures in docs are claims. Add per-stage timers to routing telemetry, report p50/p95 per stage and total, and set them beside typed routing (590 ms native single-token / ~2.5 s JSON, `typed-decision-plane.md`). Wire the telemetry into the belief kernel (`vidya-belief-substrate-program.md` VB-ROUTE-LAT).
  - 2026-09-29: the operator directs RI-16, then RI-18, as workspace-8d's next work, right after that day's wrap-up.
    Next step: add per-stage timers (role priors, route, mode, review gate, and the total) to the routing telemetry,
    with unit tests (zero inference). Then land them, do an API-only reload, and read p50/p95 per stage from live
    `/chat` requests.
  - 2026-09-30: landed as orch `78847544` (per-stage timers `memrl_init`, `priors`, `route`, `xmas`, `factual_risk`,
    `failure_veto`, `difficulty`, `trinity`, `route_total`, `mode`, `routing_context`, `review_gate`,
    `review_verdict`, `total`; a stage that did not run is `None`, never 0). `routing_path` + `stage_ms` ride the
    progress JSONL `routing_decision` and `task_completed`/`task_failed` events; reader
    `scripts/analysis/routing_stage_latency.py`. Deployed to the API 2026-09-30 04:52Z (master PID 1930724) by the
    NIB2-91 planned restart (`non-inference-backlog.md`). The box stays open: it ticks when p50/p95 per stage are read
    from live `/chat`. Belief-kernel adapter: `vidya-belief-substrate-program.md` VB-ROUTE-LAT.
- [ ] **RI-17 — compare live `/chat` routing against rules-only routing** on the same frozen workload (quality, cost, latency per request), so the KNN/memory layer has to earn its lookups. Reuse the counterfactual harness from `typed-decision-plane.md` TD-10 where it fits. (filed 2026-09-26)
- [ ] **RI-18 — evaluate the `_should_review` Q gate** (`chat_review.py:57-96`: KNN over the ANSWER text, `avg_q < review_low_q_threshold` → architect review; callers `repl_executor.py:782`, `direct_stage.py:227`, `stream_adapter.py:346`, `chat.py:1604`): measure trigger rate, review cost, and whether reviewed answers improve; keep, retune or remove. (filed 2026-09-26)
  - 2026-09-28: the "do reviewed answers improve" half waits on RI-22. Until RI-22 lands, the gate has not produced a
    usable verdict on the 27B, so a measurement now would count triggers and zero revisions.
  - 2026-09-29: unblocked. RI-22 is fixed in production (below), so the gate now returns real `OK`/`WRONG` verdicts on
    the 27B and an unparseable verdict is counted as `unavailable`. The "do reviewed answers improve" half can run.
  - 2026-09-29: the operator directs it next, after RI-16. Next step: read the trigger rate and review cost from the
    RI-22 verdict telemetry on live `/chat` (zero new code if RI-16's timers cover the gate), then run the
    "do reviewed answers improve" comparison.
  - 2026-09-30: live traffic cannot answer RI-18 (0 `POST /chat` from the RI-23 reload to ~00:30Z; 0 answer-review prompts and
    0 `v1_escalation` receipts in the whole tap window 2026-08-24 → 2026-09-29). Design: a forced-review
    counterfactual with exact policy evaluation, `/mnt/raid0/llm/tmp/ri18/DESIGN.md`. Instrument:
    `epyc-inference-research/scripts/benchmark/ri18_review_gate/` (research main
    `6b2366e2`). Orchestrator changes landed on orch main as `08edc054` (2026-09-30; NOT yet deployed — C1 goes
    live at the API-only reload the owning session times; the driver's in-process calls use `--code-root` at `08edc054`):
    - **C1** persistent `review_gate` tap event (`inference_tap.emit_request_event("review_gate", ...)`) for every gate
      evaluation on all five call sites; the three `_architect_verdict` callers switch to
      `_architect_verdict_with_status`.
    - **C2** `review_gate_score(state, role, answer, *, key_text=None) -> GateScore` accessor. `_should_review` is left
      untouched (gitnexus HIGH); the five call sites decide through the accessor (one KNN, timed into RI-16's
      `review_gate` stage), and a fixture-grid test pins `_should_review(...) == review_gate_score(...).triggered`,
      KNN key included.
    - **C3** `question_cap` (and `answer_cap`) on `build_review_verdict_prompt`, defaults 300/1500, so the production
      prompt is unchanged.
    - Belief-kernel wiring: `vidya-belief-substrate-program.md` VB-REVIEW-GATE (C1 events) and VB-RI18 (the
      `belief_measurements.jsonl` sidecar).
  - 2026-09-30 structural findings. These are **observations** (design §1: read-only code and data, no protocol);
    they gate nothing.
    - (a) **Answers under 50 chars skip the gate**, so it is inert on letter-only prompts. The UFH-13 frozen suite and
      pilot pool both end "Answer with the letter only"; on the A4 proxy (same base model) the median answer is 1 char
      and 58-77% are under 50 chars. So A2's review-gate trigger is structurally inert on the frozen letter-only suite
      (routed to `thesis-experiment-orchestrator-vs-strongest-model.md` TE-reopen).
    - (b) **The KNN never sees Q < 0.3 failures** (`min_q_value=0.3`): 5,484 of 33,293 frontdoor routing memories
      (16.5%) are invisible to it, and of the 27,809 retrievable ones only 8.4% have Q < 0.6. The reachable trigger
      rate is low by construction.
    - (c) **The verdict prompt truncates the question to 300 chars** (and the answer to 1,500). 86% of pilot-pool
      prompts exceed 300 chars, so the reviewer usually never sees the MC options.
  - **PRE-REGISTERED 2026-09-30, operator-approved in chat (Q1-Q3 as recommended).** Frozen 2026-09-30; changes are
    new registrations, never edits. Source: `/mnt/raid0/llm/tmp/ri18/DESIGN.md` §5 (operator questions §6).
    - **Question:** does the post-answer review (27B verdict → `worker_general` revision) improve frontdoor answers,
      and does the MemRL Q gate (`avg_q < 0.6` over an answer-keyed KNN) select the answers where it helps?
    - **Instrument:** `ri18_review_gate` driver at the served orch commit (pinned). Workload (Q2): S1 = the UFH-13
      pilot pool re-rendered, 453 items, render `ri18-brief-justify-v1` (the letter-only last line replaced by
      "Justify briefly (at most three sentences), then end with a final line `Answer: <letter>`"; sha pinned); S2 =
      `olympiadbench_hard`, 155 items (sha pinned). Not letter-only, and no LLM judge. Frozen 395 excluded (asserted).
      Production functions `_architect_verdict_with_status` / `_fast_revise` forced on every item. Gate computed
      offline against a sha-pinned store snapshot with the production retrieval config. Scorers:
      `extract_letter_answer` (S1), `math_symbolic` (S2). One sample per call. instrument_class = `serving`
      (production recipe, production functions); category OPTIMUM (production reviewer config).
    - **n:** 608 items (primary population = items with a scored original answer and the quality detector not fired;
      expected ≈ 560-600). Split: seeded (`seed=18`) 50/50 **tune (A) / confirm (B)**, stratified by suite.
    - **Primary metrics:** net(π) = fixed − broken per 100 items for π1 (review all eligible) and πQ(0.6)
      (production); AUROC of −avg_q for frontdoor-wrong; device-seconds per net fix (GPU and CPU separately).
    - **Power:** a paired test detects |net| ≥ 2.8·√D items at 80% power (D = discordant items). With D ≈ 40-120 on
      the full set, that is roughly 3-5 per 100 items; on split B alone, roughly 6-7 per 100 items. Effects below
      those are not excluded, and the verdict says so.
    - **Cost cap X (Q1):** at most 60 GPU device-seconds and at most 120 CPU device-seconds per net fix, and at most
      +20% added p50 latency on reviewed requests.
    - **Decision rule** (applied in order; each clause cites its CI):
      0. **VOID** if the canary pair fails in either direction, the `unavailable` rate exceeds 5%, the gate controls
         fail, or the served commit or store sha drifts. Fix, re-run; no decision.
      1. **DROP**: remove the gate, verdict and revision from all five call sites plus the `review_low_q_threshold`
         config. Applies if net(π1) has a 95% CI upper bound < 0, **or** if no policy in {π1, πQ(t*)} (t* tuned on A
         over t ∈ {0.30..1.00 step 0.05}, maximising net subject to review rate ≤ 50%) has a split-B net 95% CI lower
         bound > 0.
      2. **KEEP at 0.6** if πQ(0.6)'s net CI lower bound (full set) > 0, AUROC CI lower bound > 0.5, and neither
         πQ(t*) nor π1 beats it on split B by ≥ 2 net fixes per 100 items at a cost of at most 60 GPU device-seconds
         and at most 120 CPU device-seconds per net fix, with at most +20% added p50 latency on reviewed requests.
      3. **RETUNE to t*** if πQ(t*) has a split-B net CI lower bound > 0, AUROC CI lower bound > 0.5, and it beats
         πQ(0.6) on B by ≥ 2 per 100 at a cost of at most 60 GPU device-seconds and at most 120 CPU device-seconds
         per net fix, with at most +20% added p50 latency on reviewed requests.
      4. **REPLACE THE TRIGGER** (Q is uninformative): if the AUROC CI contains 0.5, π1's net CI lower bound > 0, and
         π1's cost per net fix is at most 60 GPU device-seconds and at most 120 CPU device-seconds, with at most +20%
         added p50 latency on reviewed requests. The Q gate goes, and review-all or a new trigger (e.g. the quality
         detector, or RI-9 factual risk; exploratory `avg_q_question` reported) goes to a decision package.
      5. If eligible gate@0.6 triggers number < 30, πQ(0.6)'s own net is reported **untested** (BOUNDED-NULL-1), and
         clauses 2 and 3 fall back to AUROC plus π1.
    - **Secondary (own rule; Q3 latitude granted):** V-full vs the production cap. If V-full's verdict sensitivity at
      equal or better specificity beats the cap-300 verdict on split B with a paired CI lower bound > 0, land
      `question_cap=1500` (C3) as the production reviewer prompt without a separate A/B (operator Q3, 2026-09-30:
      the reviewer verdict question cap 300 → 1500 may land under this rule), then re-run stages 3-4 on the banked
      answers only (replay, no frontdoor inference) before re-applying the rule.
    - **Reported regardless:** coverage by skip reason, precision/recall at every t (eligible and population),
      reviewer sensitivity/specificity/unavailable rate, revision fix/break/no-op rates, infra rate by reason, verdict
      and revision noise, per-stratum tables, and the external-validity caveat (closed-form tasks, not open chat).
    - **Stopping rule:** the split-B table is FINAL. No confirmation re-runs unless the result would change the
      decision.
  - 2026-09-30 **run plan** (instrument built and landed, no inference run yet). From the research repo root:
    `PY=/mnt/raid0/llm/epyc-orchestrator/.venv/bin/python; M="-m scripts.benchmark.ri18_review_gate.run_ri18"`;
    real: `$PY $M <segment> [args] --out /mnt/raid0/llm/tmp/ri18/run-v1 --run-id ri18-v1 --code-root <orch checkout at
    08edc054 or later>`; dry-run: the same with `--dry-run --out /mnt/raid0/llm/tmp/ri18/dev/dry --run-id dry`. Every
    segment is resumable per item and fsyncs per record. rc 3 = window refused/closed mid-segment (resume next
    window), 5 = VOID, 6 = instrument fault, 7 = all `:8083` slots busy, 9 = manifest drift.
    - `snapshot --source-root /mnt/raid0/llm/epyc-orchestrator` — right before the first `answer`; no inference.
    - `answer --suite s1` (453) and `answer --suite s2` (155) — CPU window (`open`, `loop_holds_claim=false`, item +
      120 s before `est_close_at`, re-checked per item); ~35-50 and ~30-50 min.
    - `verdict` (incl. V-full on S1) and `noise-verdict` — GPU `:8083`, one slot, no CPU window; ~18-27 and ~1-2 min.
    - `revise`, then `noise-revise` — CPU window; ~25-45 and ~3-7 min. The per-call frontdoor region claim is taken by
      `llm_call` itself (the segment sets the per-region-lock flags and asserts `:8070` → frontdoor instance 0).
    - `gate` — CPU embedders, CPU window, against the snapshot; < 3 min. `score` — offline, seconds.
    - Rule readings the driver encodes (confirm before the first `score`): clause 5 → clause 2 uses π1's full-set CI
      lower bound > 0 in place of πQ(0.6)'s; clause 3 adds "π1 full-set lower bound > 0"; "beats by ≥ 2 per 100" is
      the point estimate (paired CI cited); the latency cap is median added latency on reviewed requests ≤ 0.20 ×
      the median frontdoor wall time on those same requests.
      - ✅ CONFIRMED by the operator in chat on 2026-09-30 ("Confirm all four"), before any item ran: these four
        readings are part of the pre-registration. `score` may run once the segments complete.
- [ ] **RI-19 — fix or remove the MemRL `ClassificationRetriever` path.** The store holds 0 `classification` memories, so `classify_and_route`/`should_use_direct_mode` (`keyword_matcher.py:294,:373`, enabled by `classifier_config.yaml:110,113`) always fall back to keywords while still paying a retrieval. Either seed/write classification memories and show they beat keywords, or set `use_memrl: false` and delete the dead branch. (filed 2026-09-26)
- [ ] **RI-20 — close the `## Routing Intelligence` prompt-section gap.** The section (`prompt_builders/builder.py:287`) is added only on turn 0 of the streaming paths (`chat.py:1453` legacy, `chat_pipeline/stream_adapter.py:196` unified); the graph path (`graph/helpers.py:856-864`) passes no `routing_context`. Decide by A/B whether it helps, then wire it into the graph path or remove it from streaming. (filed 2026-09-26)
- RI-21 (2026-09-28, closed by the ARCHSWAP), RI-22 (2026-09-29, the 27B review verdict now parses) and RI-23 with
  RI-23a/RI-23b (2026-09-29, OP-69 option (a): thinking-on roles on the chat-completions lane, flag
  `thinking_roles_chat_lane`, live) are done. § *Completed Scope*.

## Dependency Graph

```text
AR-3 / production traffic
    -> RI-10 canary sample counts
        -> RI-11 expand
            -> RI-12 global enforce

RI-10 threshold pathology
    -> RI-9b threshold/Pareto sweep
        -> repeat RI-10 decision

DAR-6.5 unconditional J14 A/B pass
    -> RI-13 injection-risk classifier
        -> conditional swarm-fanout routing
```

## Forks And Mitigations

| Condition | Action |
|-----------|--------|
| RI-10 lacks high-risk samples | Keep canary; route traffic generation through AR-3/bulk-inference rather than changing thresholds blindly. |
| Enforce improves factuality but inflates cost | Sweep thresholds with RI-9b; prefer role-specific thresholds over global rollback. |
| Enforce regresses factuality or latency | Roll back to shadow; preserve logs and add a short failure analysis before retesting. |
| Verifier role lands via tri-role coordinator | Keep factual-risk review trigger as a substrate; Verifier may subsume review execution but not the risk signal. |
| SAE-feature classifier looks attractive | Treat as audit/interpretability layer only until difference-in-means and linear-probe baselines are run on the same v2 calibration slice. |
| Deep-research classifier work is needed | Use [`minddr-deep-research-mode.md`](minddr-deep-research-mode.md); do not expand this handoff for MindDR. |
| P3 consult gating becomes downstream consumer | Provide `factual_risk_score` / `difficulty_band` / shadow-routing signals as inputs to [`internal-interaction-lifecycle.md`](internal-interaction-lifecycle.md) P3 `should_consult()` policy; routing-intelligence owns signal QUALITY, not lifecycle. |

## Key Files

| Repo | Path | Purpose |
|------|------|---------|
| epyc-orchestrator | `src/classifiers/factual_risk.py` | prompt-side factual-risk scorer |
| epyc-orchestrator | `orchestration/classifier_config.yaml` | classifier/factual-risk config and thresholds |
| epyc-orchestrator | `src/api/routes/chat.py` | cheap-first bypass and request routing surface |
| epyc-orchestrator | `src/api/routes/chat_pipeline/routing.py` | plan review gate, failure graph veto, routing metadata |
| epyc-orchestrator | `src/escalation.py` | risk-aware escalation policy |
| epyc-orchestrator | `scripts/analysis/ri10_canary_sample_report.py` | RI-10 telemetry-depth gate |
| epyc-orchestrator | `scripts/analysis/ri10_canary_decision_report.py` | RI-10 operational-proxy + factuality-readiness decision packet |
| epyc-orchestrator | `scripts/analysis/ri10_canary_score_responses.py` | RI-10 scored factuality response report after quiet-window dispatch |
| epyc-research | `scripts/benchmark/seed_specialist_routing.py` | seeding/eval harness for A/B and threshold sweeps |
| epyc-research | `orchestration/factual_risk_calibration_v2.jsonl` | 2,600-example v2 calibration dataset |

## Completed Scope

| Scope | Outcome | Evidence |
|-------|---------|----------|
| Phase 0 telemetry | Delegation/routing telemetry fields repaired. | [completed ledger](../completed/routing-intelligence-completed-through-2026-05-28.md) |
| Phase 1 classifier module | Types/config/output parsers and keyword delegating wrappers completed. | [completed ledger](../completed/routing-intelligence-completed-through-2026-05-28.md) |
| Phase 2 MemRL classifier | `ClassificationRetriever` and exemplar seeding completed. | [completed ledger](../completed/routing-intelligence-completed-through-2026-05-28.md) |
| Phase 3 factual-risk scorer | Regex scorer and shadow logging completed. | [completed ledger](../completed/routing-intelligence-completed-through-2026-05-28.md) |
| Phase 4 enforcement code | RI-1 through RI-7 implemented and A/B tested; initial A/B underpowered. | [completed ledger](../completed/routing-intelligence-completed-through-2026-05-28.md) |
| Phase 5 seeding fields | RI-8 verified on `RoleResult`; v2 calibration dataset built via NIB2-34. | [completed ledger](../completed/routing-intelligence-completed-through-2026-05-28.md) |
| RI-10 arm telemetry repair | Routing now logs the sampled factual-risk canary arm as `routing_meta.factual_risk_mode`, and the plan-review gate reuses that persisted arm instead of resampling. Existing 2026-06-20 rows remain insufficient; collect fresh post-fix rows before a rollout decision. | `epyc-orchestrator` `7647b32e`; `uv run pytest -q tests/unit/test_factual_risk.py tests/unit/test_pipeline_routing.py` -> `110 passed` |
| RI-10 report/gate semantics hardening | `ri10_canary_sample_report.py` now distinguishes raw high-risk volume from decision-grade arm-attributed telemetry, separates historical missing-mode rows from the current telemetry-health window, and derives default canary-role scope from `classifier_config.yaml`. DS-E1/Fable5 aggregate gates stay blocked when only raw count is ready. The 2026-07-04 current report has `464` raw high-risk rows since canary start, `20` current-window high-risk rows with `0` missing mode, and all `20` current rows fall inside the widened canary role scope; the scope-free diagnostic returns the same current-window count, so the blocker is insufficient arm count/balance. | `orchestration/reports/ri10_canary_sample_report_20260704T005256Z.json`; `orchestration/reports/ri10_canary_sample_report_all_roles_20260704T005332Z.json`; `orchestration/reports/fable5_gate_report_20260704T005355Z.md` |
| RI-10 deficit surfacing | Current report consumers now expose the exact collection deficits instead of only repeating "not ready": `canary_role_sample_deficit=30`, `canary_arm_volume_deficit=30`, and balance deficits `enforce=9`, `shadow=0`, plus by-role and by-role-arm counts in DS-E1/Fable next-action evidence. DS-E1 also refreshes from live progress logs when the latest saved RI-10 artifact predates the new schema. | `epyc-orchestrator` `807939fa`; `uv run python -m pytest -q tests/unit/test_ri10_canary_sample_report.py tests/unit/test_dynamic_stack_evidence_packet.py tests/unit/test_fable5_gate_report.py` -> `47 passed` |
| RI-10 decision-ready refresh | Live Fable/DS-E1 reads now show RI-10 no longer blocks the aggregate gate: current-window arm counts are sufficient (`enforce_high_risk=31`, `shadow_high_risk=50`), role coverage is populated (`frontdoor=11/11`, `worker_general=10/23`, `worker_vision=10/16`), and the current deficit counters are zero. Treat the July 4 insufficient-sample notes above as historical pre-accrual state. | 2026-07-05 live read-only refresh; `ri10_telemetry_collection_blocker=decision_ready`; Fable gate after W8 repair blocks only on W6 audit clearance |
| RI-10 decision packet | Standalone decision report now joins current canary rows to task outcomes, escalation events, plan-review events, and optional scored-response evidence. Current packet is `hold_quality_scored_no_lift`: operational proxies favor enforce, but scored factuality has no exact-accuracy lift (`0.10` vs `0.10`). | `epyc-orchestrator` `adf010b4`; `orchestration/reports/ri10_canary_decision_report_20260706T065654Z.{json,md}`; `uv run pytest -q tests/unit/test_ri10_canary_decision_report.py tests/unit/test_ri10_canary_score_responses.py tests/unit/test_ri10_canary_request_plan.py` -> `19 passed` |
| RI-10 scored collection packet | Request planner now supports dataset-backed expected-answer rows, answer-key JSONL output, and self-leak filtering. Generated a balanced scored canary packet: `60` requests, `30` enforce / `30` shadow, `20` per canary role, answer key separated from payloads, and no nontrivial expected-answer leakage. | `epyc-orchestrator` `8455af52`; `orchestration/reports/ri10_canary_scored_request_plan_20260705T151725Z.{json,payloads.jsonl,answer_key.jsonl}`; `uv run pytest tests/unit/test_ri10_canary_request_plan.py -q` -> `7 passed`; `ruff` passed |
| RI-10 scored response scorer | Response scorer joins quiet-window response JSONL to the answer key, extracts common response shapes, scores deterministic answer equivalence, and summarizes accuracy/token-F1 by role and enforce/shadow arm. | `epyc-orchestrator` `92ab4de7`; `scripts/analysis/ri10_canary_score_responses.py`; `uv run pytest tests/unit/test_ri10_canary_score_responses.py tests/unit/test_ri10_canary_request_plan.py -q` -> `11 passed`; focused `ruff` and `py_compile` passed |
| RI-10 scored response result | Quiet-window scored response artifacts are complete: `60` rows, `60` scored, `0` missing; enforce and shadow exact accuracy tie at `3/30` each, with only a tiny token-F1 enforce delta. This closes the "unscored" blocker and replaces it with "no enforce factuality lift." | `orchestration/reports/ri10_canary_scored_summary_20260705T185001Z.{json,md}`; `orchestration/reports/ri10_canary_scored_rows_20260705T185001Z.jsonl` |
| G12 role-tier recalibration | AA-Omniscience frontdoor/worker/architect evidence completed; deterministic 4-class scoring accepted for role-tier recalibration; measured tier multipliers landed in orchestrator. Mode/canary/enforce decisions remain RI-10+ gates. | [bulk-inference-campaign](bulk-inference-campaign.md) |
| Research intake | AA-Omniscience, STOP, Qwen-Scope SAE caveats, BaRP/Conductor context captured. | [completed ledger](../completed/routing-intelligence-completed-through-2026-05-28.md) |
| RI-21, RI-22, RI-23 (+RI-23a, RI-23b), 2026-09-28/29 | Escalation map ends at `architect_general`; the review gate parses on the 27B; thinking-on roles speak chat-completions (OP-69 (a), live). | [completed ledger § 2026-09-29](../completed/routing-intelligence-completed-through-2026-05-28.md) |

## Research Intake Update — 2026-07-08: J-Space Interpretability (rec-009)

**Source**: Anthropic J-space (intake-782)

**Key finding**: Anthropic's J-space work on geometric interpretability of model representations could inform routing intelligence — understanding the geometric structure of model capabilities may enable better routing decisions than current embedding-based approaches.

**Applicability to EPYC**: Our current routing relies on embedding-based similarity (MemRL, factual-risk regex scorer, difficulty-signal regex features). J-space's geometric interpretability could provide a more principled routing substrate by mapping model capability geometry rather than prompt embedding similarity.

**Integration points**:
- Could replace/augment MemRL's embedding-based retrieval with geometric routing
- May enable the learned-head routing in `outer-coordinator-learned-head.md` with geometric priors
- Complements the tri-role architecture's role-axis by providing geometric capability mapping per role

**Action**: Monitor J-space development; evaluate integration with learned-head routing when the geometric interpretability substrate is available for open-weight models.

- [ ] **RI-JS-1** — monitor J-space interpretability tools for open-weight model compatibility
- [ ] **RI-JS-2** — evaluate geometric routing as an augmentation to MemRL embedding retrieval

## Research Intake Update — 2026-07-29: LFM2.5-Encoder-350M-Prompt-Router

**Filed as a `monitor_only` comparator, not a work item.** The MLP learned-routing controller
(Phase 1 complete; Phases 1.5–3 unfinished) owns the routing-classifier line — see
[`learned-routing-controller.md`](learned-routing-controller.md). LFM2.5-Encoder-350M-Prompt-Router
is a purpose-built prompt-router encoder and is therefore a useful external reference point for what
a dedicated router head buys over our MLP; it is **not** a replacement candidate, and opening it as
one would fork an already-unfinished program.

- [ ] **RI-CMP-1** — file LFM2.5-Encoder-350M-Prompt-Router as a `monitor_only` comparator against the MLP learned-routing controller. Do NOT open a work item: Phases 1.5-3 are unfinished and this is a comparator, not a replacement.
  - *2026-09-23 (intake-1502, intake-1501):* also file Laya (laya / laya-multilingual) as a `monitor_only` comparator — near
    chance zero-shot on routing (DDnim tier 9/20 and 5/20), its worst-calibrated bucket (choice:11+) is where an 11-way
    routing choice lands, and it re-encodes the state per question. Not a work item.

## Reporting Instructions

- Update [`routing-and-optimization-index.md`](routing-and-optimization-index.md) P6 after RI-10/11/12 status changes.
- Update [`bulk-inference-campaign.md`](bulk-inference-campaign.md) if AR-3/J-package traffic is used to collect RI samples.
- If a new injection-risk classifier is opened, add it here as RI-13 and cross-link DAR-6/J14.
- If a stack/model change changes role throughput or cost, update q-scorer baselines and note the dependency in the routing index.

## Research Intake Update — 2026-08-15 (harness selection as a routing dimension; intake-1140)

**Record only — no task, no build.** Filed because a plausible misreading of this source would push
routing work in the wrong direction, and the misreading was made once already during intake.

`intake-1140` (HarnessOpt-Bench, Scale AI) reports that "model choice has a larger effect than
coding-harness choice" — 0.142 vs 0.079 mean gain movement, about 1.8×. **That is not a routing
result, and citing it as one is backwards.** The harness varied in that contrast is the **optimizer's
own coding agent** (Claude Code vs opencode vs codex vs kimi-cli), not the harness being optimized.

On the **target** axis — the one our routing work cares about — the same paper's Table 3 is a
controlled swap where the harness is the only variable (same dataset, partition, rounds and target
model), and it shows the largest effects anywhere in the paper: OfficeQA 0.341 → 0.734,
BrowseComp-Plus 0.462 → 0.701, Terminal-Bench 0.241 → 0.607, GAIA 0.000 → 0.508. Converting those to
normalized gain and comparing against the best of **111** frontier-optimizer runs — an arithmetic the
dive performed and the paper never states — **the best off-the-shelf harness is statistically
unresolved from the best optimizer run on three of four tasks, and beats every optimizer on
Terminal-Bench by about 3.6 resolution bands.**

**The citable implication is therefore the opposite of the headline**: harness/scaffold selection is
worth about as much as an entire frontier-model optimization campaign, and should be treated as a
**first-class routing dimension rather than a fixed substrate**. Cite `intake-1140#record`, never as
"model > harness".

## Research Intake Update — 2026-09-17 (Jev typed-decision cluster; intake-1472/1473/1474/1487)

- [x] **RI-14 — Typed-decision fast path for closed-set routing questions.** Once TD-2 calibration lands, evaluate a Choice-style candidate-logit call as the routing classifier fast path; never gate on uncalibrated confidence; report agreement + calibration + wall time vs the current classifier. (Evidence: intake-1472/1473/1474/1487; owner stub `typed-decision-plane.md`, RTG-56.) ✅ 2026-09-29 — folded into TD-11 (`typed-decision-plane.md`; operator ruling Q5: TD-11 is the single typed-routing owner). The classifier comparison, the calibration rule and the intake-1501 question shape moved there.
  - *Question-shape template 2026-09-23 (intake-1501):* tier choice with criteria + ordinal effort score, with a 20-card OOD
    probe whose labels come from a distribution the arm was not tuned on.
- [ ] **RI-15 — (conditional) Generation-side comparator for factual_risk.** When factual_risk.py is assessed for shadow→enforce, report on the same rows a generation-side comparator (spec-OFF mean/min token log-prob of the served answer), not only the calibration set. Evidence: intake-1521 (zero-shot log-prob ties a simplified supervised router in distribution; no calibration measured).
  - *Cross-link (2026-09-29, Jev-techniques map §3.2):* the same intake-1521 log-prob signal is EV-CONF-2's
    salient-token confidence source on the autopilot eval surface (`autopilot-decision-plane-audit-2026-07-22.md`).
    Different surfaces, one evidence base: reuse EV-CONF-2's spec-OFF capture rather than building a second one.
