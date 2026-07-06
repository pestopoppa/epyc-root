# Audit — Kernel-R&D loop + Orchestration Autopilot loop (and both dashboards)

**Status**: ACTIVE REVIEW — prioritized remediation roadmap with Phase-1 AutoPilot fixes landed
**Created**: 2026-07-05
**Author**: Fable 5 audit session (operator-directed: "audit the kernel improvement loop and its dashboard… could the orchestration autopilot loop/dashboard be improved also?")
**Method**: direct source reads + a read-only 7-facet audit workflow (deep-read → synthesize → adversarial gap-critic; 9 agents, 0 errors, ~1.1M subagent tokens). Every performance number here is an **OBSERVATION** in the MEASUREMENT.md sense (journal/log-derived, no protocol id) — it steers attention, it does not gate promotions. The highest-leverage fixes touch the **human-amendment-only** trust boundary and are flagged as operator-signed amendments, not agent edits.
**Scope of surfaces audited**: `epyc-orchestrator/scripts/autopilot/*` + `src/autopilot_core/*` (loop, generators, evidence/promotion/safety plane), `epyc-orchestrator/src/api/routes/dashboard*` (autopilot dashboard :8000), `epyc-inference-research/scripts/kernel_rnd/*` (kernel loop), `epyc-root/dashboard/*` (hub :8100). Related: [mi210-kernel-rnd-loop-proposal.md](mi210-kernel-rnd-loop-proposal.md), [master-handoff-index.md](master-handoff-index.md), the completed `fable5-findings-*` set.

## Main-thread review/action — 2026-07-05

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
- `epyc-orchestrator` `10a9596d` makes checkpoint restore/rollback rewind AP-22 short-term memory and the StrategyStore tree, and the live rollback path now closes/reopens StrategyStore handles after restore instead of leaving planner memory split from disk.
- `epyc-orchestrator` `1d452a40` first bounded GEPA prompt writes to each evaluation call by restoring the original prompt in a `finally` block.
- `epyc-orchestrator` `8031c7c4` then completed the true scratch prompt-root override: GEPA candidate evals copy the prompt tree into `tmp/gepa_prompt_roots`, write the candidate only there, tag eval questions with `_prompt_root`, and `/chat` resolves prompts through a request-scoped override that is accepted only under the configured scratch base. Candidate scoring no longer writes canonical prompt files.
- `epyc-orchestrator` `12839520` adds observation-only W8 paired-baseline diagnostics: each evaluated trial can journal `eval_details.seq_paired_baseline`, comparing its per-question vector with the latest trusted `seq_baseline_reference_draw` through the existing exact McNemar/sign-test primitive. The payload is explicitly `used_for_gating=false` and is computed only after SafetyGate/Pareto/baseline decisions, so it cannot change current keep/revert or promotion semantics.
- `epyc-orchestrator` `18c71bcc` adds outcome-first health signals to `phase_health_report.py`: journal-shard-derived frontier-admission staleness, baseline-promotion staleness, and recent keepable/wasted/learning-excluded rates. Default behavior is advisory; `--require-outcome-progress` turns the same signal into a strict blocker. A live smoke flags the current frontier stall at `172` trials since the latest frontier admission against the default threshold `150`.
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
- Focused validation passed across the touched slices: `49` planner/provider/launcher tests, `43` W6/readiness tests, `46` spend-breaker/economics tests, `233` action/dashboard tests, `49` structural/restore tests, `64` GEPA/prompt-root/API/eval propagation tests, `36` sequential/paired-diagnostics tests, `44` phase/restart/dashboard health tests, `138` rejected-draft/action/creativity tests, and `11` earlier GEPA integration tests, plus focused `py_compile`, `ruff`, and `git diff --check`.

Next measured extension:
- Let the current daemon continue until the next restart-safe boundary, then
  restart onto `24ab6170` if phase health reports runtime source drift. The next
  ordinary planner turn should prove that local drafts follow the W8-filtered
  action menu rather than proposing seed/deep deferrals that the critic must
  salvage.
- Build a two-stage planner provider after the one-shot local-ingest/local-
  frontdoor path has telemetry: `ingest_long_context` synthesizes a bounded
  planner brief, `frontdoor` or `worker_general` drafts the action from that
  brief, and Codex/Claude remain sampled audit or fallback critics. This is the
  orchestration-native target pattern; it should be A/B measured before
  becoming the default.

---

## Headline verdict

**Both loops are engineering-rich and outcome-poor.** They are among the best-built control planes in the estate (crash-safe journals, fail-closed gates, atomic contracts, an exclusion taxonomy, durable circuit breakers), but **every gate that converts *trials* into *durable value* is either statistically unreachable or unimplemented, and every health signal measures liveness, not yield.** The system can burn 750+ trials, exceed its planner budget, and freeze its Pareto frontier for a week while every surface reports "active, blockers: []".

Any fix that adds telemetry without adding an **outcome KPI + escalation rule** deepens the pathology.

### Verified evidence (independent counts, this session)
- **Effectively zero durable promotions.** The live journal (`orchestration/autopilot_journal.jsonl` + `_1.jsonl`) spans to **trial 1169** yet contains **exactly one `baseline_promotion` event** in its whole history. There are 229 "keep" decisions, but those are trial-level keep/revert outcomes (keep=229 / revert=374 / excluded=305 / unchanged=5 over 1,055 entries), **not** production promotions.
- **Frontier frozen ~7 days** (last admission ~trial 1005, 2026-06-28); W8 promotion trajectory is `stale_accumulating` with no replay-eligible candidate since the trial-1158 refutation. This is the single binding blocker on the whole promotion pipeline.
- **Generation mix is misaligned with the promotion gate.** The two *replayable* candidate types W8 promotion requires — `numeric_trial` and `structural_experiment` — got **8 trials total** out of 1,055; `seeder` alone consumed 529. The loop spends its evals on candidate types that structurally cannot promote.
- **The autopilot dashboard is observation-only**: `src/api/routes/dashboard.py` exposes **28 GET endpoints and 0 POST** — no pause/rewind/promote/reweight from the UI. It also computes `baseline_promotions` server-side and never renders them.
- **Kernel loop**: the verify harness (`kernel_eval.sh`) genuinely enforces correctness-first ordering (a FAIL exits before speed is ever measured), but its coherence gate marks **any non-empty output "coherent" when no baseline is supplied** → `correct=1`; there is **no PPL gate**; the Pareto frontier is **empty** (only a null-valued seed row ingested, no real sweep); and **rewind/purge — a named non-negotiable — is absent**.

### Why the orchestration gate is "dead by construction" (the mechanism)
The stall is a stack of independently-fatal statistical faults, each inside the human-owned trust boundary:
1. **Rate non-inferiority axis is era-blind.** `E_rate_noninf` compares each trial to a 120-row historical mean spanning the concurrency 3→1 eval-regime change: ~93% of z_rate observations are negative, max `E_rate` ever ~1.11 vs a threshold of 20. Because the joint rule refutes when *either* axis refutes, this one broken instrument kills quality-positive candidates and drags `combined_E` below the W8 replay floor.
2. **Sequential policy has ~zero power.** `confirm_e=20` within `max_k=12` needs sustained z≥0.57; observed max ~0.51, mean ~0.17. A genuine consistent z=0.17 improvement is guaranteed refuted. An anti-ratchet that can never fire is indistinguishable from a bug.
3. **Alpha wealth is a lifetime Bonferroni, exhausted.** ~54 fingerprints charged against a lifetime cap of ~20 → `new_fingerprint_confirmations_allowed=false` **permanently** — every future confirmation is pre-blocked even after (1) and (2) are fixed.
4. **The frontier speed axis is un-reproducible.** The 4-point frontier holds clean-window 66–69 t/s; today's ambient-contention evals read 14–33 t/s and can never dominate → 160+ consecutive "dominated" trials; HV frozen.
5. **`seq_accumulating` exclusions freeze both promotion paths at once** — the Pareto archive *and* the legacy 3-reproduction ratchet — so nothing accretes (`autopilot.py:5429`).
6. **The e-process's "fixed null" isn't fixed** — `_seq_inputs_for_trial` rebuilds it from a shifting 120-row window every trial, voiding anytime-validity even after (1) and (2).

**Upstream waste feeding the dead gate:** the generator layer proposes **inert candidates** (knobs behind OFF flags, single-flag toggles → 0 keeps in 119 trials; NSGA-II runs at 3–11 trials/surface ≈ random; critic-prose rejections have surface-banned all 8 numeric surfaces). It is expensive: planner spend ~$486/mo projected vs a **$250 budget that is only a status string** (unenforced, `digest.py:278`); routine trial **drafts go to metered cloud models** (`planner_providers.py` has only Claude + Codex providers) despite a 12-server self-hosted fleet and the open-source-only policy; ~18% of evals die mid-trial discarding all work; each eval costs ~750–900s at `concurrency=1` while 8 replicas idle.

### Kernel-R&D loop verdict
Promising skeleton, **not yet safe for autonomy, pointed at the wrong objective.** Phase 0 (`kernel_eval.sh`) + Phase 1 (`kernel_store.py`) genuinely enforce correctness-first ordering, append-only idempotent ingest, and atomic OBSERVATION-disciplined export — validated end-to-end **once** (prefetch +2.11%, MemUnitStalled −55%, byte-identical). But three of four load-bearing design promises are unimplemented: the coherence gate passes anything non-empty without a baseline; no PPL-within-ε gate exists; the advertised 3-axis Pareto is effectively 1-D and currently **empty** (absolute/aggregate t/s never populated by a real sweep); rewind/purge is absent. `MUL_MAT_ID` (the MoE op for the stated first workload) is ungated; the +2.11% headline has no variance/CI gate (AB_ROUNDS=2/REPS=3). **Phase 2 is ~40% built** — `kernel_sweep.sh` (inner sweep) exists but there is no nightshift scheduling, no store-guided next-point selection, no GPU cross-session lock, and no GPU-busy guard (`inference_guard.sh` watches host RAM only, blind to the MI210). Strategically, the loop optimizes single-stream GPU speed, which the campaign summary declares **structurally exhausted**, while its measured durable value landed on **capability/residency** (122B/80B IQ2 at eval-parity) — an axis the store cannot represent.

### Dashboards verdict
Two well-built **liveness** instruments that reproduce the central risk in the UI layer: neither answers *"is this loop producing value?"*
- **:8000 (autopilot)** — genuinely wired freshness contract, shard-aware journal reads for decision panels, statistically literate progress bars. But it never renders the `baseline_promotions` it computes; surfaces no keepable-rate / wasted-eval / alpha-wealth / trials-since-promotion; reads only the **frozen base journal shard** for trial-duration distributions (post-rotation trials missing — [[feedback_autopilot_journal_rotation_read_all_shards]]); still executes **dead v6 `/slots`** code shipping permanently-empty prompt/content fields at 2Hz ([[project_v6_slots_no_prompt_content]]); leaves **5 rendered panels outside the freshness registry**; wraps GEPA/Pareto updates in bare `catch{}` so frozen panels masquerade as data; and offers **zero steering affordances** (pause/rewind/quarantine live in shell tribal knowledge).
- **:8100 (hub)** — clean stdlib service, honest empty states, real tests. But the **kernel freshness badge classifies export-file mtime**, so a cron re-export of one row reads "fresh" forever; the Pareto panel is an empty shell fed by a contract whose throughput fields the producer never fills; the chart fabricates y-positions for null-aggregate points (`kernel.html:159`); and the backlog banner (488 open tasks, a vanity 53.9% all-columns denominator) aggregates without priority, staleness, or velocity — a **count, not a steering instrument**.

---

## Remediation roadmap (phased by risk + dependency)

Ranks reference the workflow synthesis; the adversarial critic's corrections are folded in. Effort S/M/L; impact low→transformative.

### Phase 0 — Stop-loss (operator action, zero engineering cost)
- **Pause the orchestration autopilot.** It is dead by construction, so continued operation yields ~0 promotions while burning ~$16/day planner spend and ~45 eval-wall-hours/week. Pause via **SIGTERM at a trial boundary** — `pause` is a no-op ([[feedback_autopilot_pause_broken_use_sigterm]]); leave the kernel loop and both dashboards running. Restart precondition (write into the master index): *amendment bundle approved + positive-control canary passes*. **Operator-owned; no autonomous action taken.**

### Phase 1 — Safe code fixes inside the autonomy boundary (no MEASUREMENT amendment)
- **[P1 · M · transformative] Paired per-question (McNemar) screening in `eval_tower.py`** — run candidate and baseline on the same question set/seed; feed the discordant-pair statistic into seq accumulation. **The largest power gain that needs no trust-boundary change** — it raises z per observation instead of lowering thresholds, de-risking the (slow) amendment queue. `paired_stats.py` already exists.
- **[P1 · M · transformative] Outcome-first stall detection + KPIs** — PARTIAL LANDED in `18c71bcc`: `phase_health_report.py`/`phase_status.py` now exposes journal-derived outcome blockers (frontier-admission staleness, baseline-promotion staleness) and recent keepable/wasted/learning-excluded rates; default is advisory and `--require-outcome-progress` makes it strict. Dashboard `baseline_promotions` + keepable/wasted cards already exist. Remaining work: render the phase-health outcome block where needed, add the :8100 hub card, backtest thresholds, and only then wire operator-configurable auto-pause/escalate through the durable pause latch.
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
  - [x] Contention matrix freshness: hash-scope false positive (live hash included auxiliary `eval_batch_frontdoor`; measured-role hash `df373c79cc4af06f` matched all along) — RESOLVED by the codex session (orch `3d1706c6` + `120498c9`: measured-role-subset hash centralized in `contention.py`, all consumers aligned, API reloaded, live `matrix_status: ok`; NO re-bench needed). Details: `contention-matrix-v6-quarter-refresh.md` ✅ 2026-07-05
- **[P1 · S · medium] Production-safety + parity fixes the synthesis dropped** — isolate GEPA per-candidate prompt writes (`gepa_optimizer.py:88`) from the live prompts dir (a crash leaves a mutated production prompt) via the existing WorktreeManager/isolation path; make the **W6 gaming comparator config-aware** (`audit_block_report.py:407` is blocking the Fable gate ~29 trials on a between-candidate-variance false positive); extend `cmd_restore` (`autopilot.py:6309`) to purge StrategyStore + AP-22 memory ([[feedback_autopilot_rewind_must_purge_strategy_store]] — the loop the scar was named for).

### Phase 2 — The human-owned MEASUREMENT amendment (ONE bundle, one operator sign-off)
Package these trust-boundary changes into a **single** proposal with a shared Ville-simulator attestation pack, so the critical path is one round-trip, not four. Agents produce the analysis; **the operator signs the change; never weaken a gate silently to "unblock" the loop.**
- **[P2 · rank 2] Era-fence the rate non-inferiority baseline** — compute `baseline_task_rate` only from rows matching current `eval_concurrency`+`speed_metric_mode`, or pair it against the scheduled `seq_baseline_draw` references (`autopilot.py:1943`). Short bridge: make the rate axis advisory (non-joint-refuting) until the fence lands.
- **[P2 · rank 4] Power-calibrate the sequential policy** — extend `empirical_ville_false_positive_rate` (`sequential_verdict.py:264`) with an alternative-hypothesis arm at the observed z distribution; target ~80% power at z≈0.15 with empirical false-confirm ≤0.05 (likely `max_k`→~40, drop the k=8 budget kill).
- **[P2 · rank 12] Re-price alpha wealth** — charge alpha at the confirmation/fresh-eval *stage* (not per journaled fingerprint), price it at the simulator-derived per-candidate false-confirm rate, and scope the budget to the active instrument era so rewinds restore wealth.
- **[P2 · critic] Freeze the sequential null per fingerprint** — snapshot `baseline_profile`+`baseline_task_rate` at a candidate's first seq observation; reuse it; restart accumulation if an era row lands mid-candidate. Ships in the bundle because it changes verdict inputs.
- **[P2 · rank 6] Re-anchor the frontier speed axis** — use the existing `frontier_rerun` machinery to re-measure the 4 representatives under today's protocol, or open a new Pareto epoch (`autopilot.py:3706`); record an ambient-load covariate per eval. Append an `instrument_eras.yaml` row (never edit). Must land **with** Phase-3 throughput (fan-out changes per-request t/s).

### Phase 3 — Prove the pipeline can promote, then re-open throughput
- **[P3 · rank 3 — operator-approved, NOT a silent edit] Unfreeze the Pareto archive** — admit `seq_accumulating` non-dominated trials to `upsert_representative` (`autopilot.py:5403`; same epistemic state as `mad_noise` per `learning_exclusions.py:63`), re-enabling reproduction clustering + the legacy ratchet as a fallback. **Caveat (critic):** this reactivates a sealed baseline-promotion pathway around the human-owned seq gate — treat as an operator-approved change with median-tested dominance preserved, not "a one-condition change plus tests."
- **[P3 · critic] Positive-control canary** — replay a **known-real** improvement (the unused 96t single-NUMA point, 49.1 t/s on 30B-A3B — [[project_96t_single_node_operating_point]]) end-to-end through generation→eval→confirmation→fresh-eval and require it to **promote**. The only direct test that separates "gate broken" from "nothing left to find." Keep it + a known-neutral twin as a **standing regression pair** after every instrument change/era row.
- **[P3 · critic] Eval-suite discriminability audit** (do before trusting P2 thresholds) — the flat 1.85–2.18 quality band may be a suite-ceiling / substring-scorer artifact ([[feedback_substring_scorer_comma_brittle]], [[feedback_eval_saturation_masks_model_gap]]), not candidate quality. Read-only per-question pass-rate + brittleness + minimum-detectable-effect analysis; if the effective quantum exceeds z≈0.15, fix the suite first, else P2's calibrated gate is calibrated against noise.
- **[P3 · rank 11, unbundled] Eval throughput** — land the queued `eval_batch_serving` telemetry pass (measured 4.86× wall-time) as a **decision-gated** codified-recipe run with operator approval + protocol id + attestation + an `instrument_eras.yaml` row; separately enable topology-safe `eval_concurrency`; persist per-question results so killed trials salvage work. Must land **with** the P2 speed re-anchor.

### Phase 4 — Kernel-R&D loop: harden before any Phase-2 autonomy
- **[P4 · rank 7 · transformative] Fail-closed correctness** — require a baseline for the coherence compare (no baseline → `NO_BASELINE`, never `correct=1`); add a `llama-perplexity` |ΔPPL|<ε gate; parameterize `test-backend-ops` to include **`MUL_MAT_ID`** (MoE op for the stated first workload); add a variance/CI gate on the A/B delta. Verify with a deliberately-degraded negative control + the validated prefetch positive control.
- **[P4 · rank 8, critic-corrected] Record absolute + aggregate t/s; add the value axis** — add a batched `llama-bench` pass so `aggregate_tps` + always-populated absolute single t/s exist (frontier is empty today); store a numeric correctness margin (ΔPPL, tbo pass-fraction) so the "3-axis" frontier is real; stop the hub chart fabricating y for null-aggregate points. Capability/residency (122B/80B IQ2 at eval-parity) is a **step function, not a Pareto axis** — record it as a separate **attested capability row**, don't force it onto the frontier.
- **[P4 · rank 9 · S] Purge/rewind by git_sha** — add `kernel_store.py purge --git-sha`/`rewind`; open the DB read-only for query commands; fix the broken insert/dup counter. **Hard precondition** for Phase-2 nightshift scheduling — a build+commit loop without purge pins reverted commits on the frontier forever.
- **[P4] Build the missing Phase-2 machinery** (nightshift schedule, store-guided next-point selection, GPU cross-session flock, MI210-aware busy guard) **only after** correctness + purge land.

### Phase 5 — Management / dashboard steering (both loops)
- **[P5 · rank 13, critic-corrected] Hub backlog as a steering instrument** — bucket open tasks by priority; flag handoffs untouched >30/90d into a probably-dead lane feeding an operator archive-review queue (index changes stay operator-approved per CLAUDE.md); fix `pct_done` to an open-scope denominator. **Do not** compute a burn-down ETA over the bulk-import-corrupted velocity series without fencing imported-vs-organic tasks first.
  - [x] Backlog % interpretability: board payload + banner now carry `activity_today` (handoff commits / files touched / boxes checked / boxes added since local midnight) with an explicit "prose-only — % cannot move" warning; root cause of the operator's second stale-board report (10+ commits, 0 checkbox flips) — epyc-root `ea561387` ✅ 2026-07-05
  - [x] Checkbox-discipline governance so the % moves when work happens: checklist-sync gate in `/wrap-up` (Claude + Codex skill copies) + always-loaded CLAUDE.md rule binding autonomous checkpoint commits — epyc-root `ea561387` ✅ 2026-07-05
  - [x] Bucket open tasks by priority in the backlog banner: root dashboard payload now emits priority buckets and the banner renders them as open handoff/task/untracked counts. ✅ 2026-07-06
  - [x] Probably-dead lane: handoffs untouched >30/90d or missing activity now surface as a sorted clickable archive-review candidate list in the backlog banner; index/archive changes remain operator-owned. ✅ 2026-07-06
  - [x] Promote the open-scope denominator (`pct_open_done`) to the headline next to `pct_all_done`. ✅ 2026-07-06
- **[P5] Kernel freshness badge on data recency** — classify on `max(runs[].ts)`, not export-file mtime.
- **[P5] Steering affordances** — close the "zero POST" gap: guarded operator actions (or, minimally, copy-exact SIGTERM/pause command chips) so pause/rewind/quarantine leave shell tribal knowledge.
- **[P5] Governance/attention tax** — 132 handoffs / 488 open tasks and a 224-line master index restating runtime state in ~6 places (near-daily alignment commits) are themselves a bottleneck; the outcome-KPI header + archive-review lane are the levers.

---

## If you can only do five things
1. **Pause the orchestration autopilot now** (Phase 0) — zero effort; stops provably-zero-yield burn; makes restart the forcing function for the amendment queue.
2. **Repair/demote the rate non-inferiority axis** (P2 rank 2) — the single biggest mechanical blocker; nothing downstream works while it refutes 93% of candidates.
3. **Power-calibrate seq + re-price alpha + freeze the null as ONE amendment bundle** (P2 ranks 4+12+critic) — one operator sign-off instead of four multi-day stalls; without it the gate stays uninformative and confirmations stay pre-blocked.
4. **Paired McNemar screening in `eval_tower`** (P1) — the largest power gain needing **no** amendment; makes the calibrated gate reachable at realistic effect sizes.
5. **Outcome-first stall detection with auto-escalation + positive-control canary as the resume gate** (P1 + P3) — the recurrence guard so the next regime drift surfaces in days, not six weeks, and the one is-this-producing-value view both loops lack.

---

## Cross-cutting risks to hold throughout
- **Instrument-regime drift is the root cause, not an incident** — concurrency 3→1 broke the rate axis; the clean post-cutover window broke the speed axis; the moving 120-row null broke anytime-validity. Record regime covariates (concurrency, ambient contention, `speed_metric_mode`) on **every** eval and fence comparisons by them, or the next infra change silently re-kills promotion.
- **Trust-boundary pressure runs both ways** — never let an agent weaken a gate to "unblock" the loop; but don't let the amendment queue stall while the loop burns money. The single bundle + enforced spend breaker address both.
- **Cross-loop coupling** — a kernel change reaching the fleet shifts orchestration eval t/s; add a kernel-promotion → orch era-row/re-anchor trigger.
- **Doc/runtime divergence** — the 3-axis kernel Pareto, the PPL gate, MutationGraph/diversity cadences, and several `program.md` cadences are advertised but unwired; the LLM planner consumes descriptions as capabilities → **wire or delete**.
- **Kernel Phase-2 autonomy is a latent safety hole** — enabling a nightshift build+commit loop before fail-closed correctness (P4 rank 7) and purge-by-git_sha (P4 rank 9) would pin wrong-but-nonempty kernels and reverted commits on the frontier; the GPU also needs its own busy-guard + cross-session flock.
- **Unbounded files** — `inference_tap_events.jsonl` (~475MB) already blinds panels under load; the timeline rebuild is O(full history) per commit with silent hook failures.

## Verification (how to confirm each fix, honoring MEASUREMENT.md)
- **Effectiveness KPIs (observations):** after Phase 1, `/dashboard/api/health` + `phase_health` report a named outcome blocker during the stall; the run-strip promotions/keepable-rate match an independent `jq` count over `autopilot_journal*.jsonl`.
- **Gate reachability (decisive):** the Phase-3 positive-control canary **promotes** through the repaired pipeline; a known-neutral twin distributes z_rate around 0. The single check proving the loop can produce value again.
- **Amendment attestations:** each P2 constant ships with a Ville-simulator report (power at z∈{0.1,0.15,0.2}, empirical false-confirm rate, n≥10k sims) as its attestation ref; era/epoch rows appended to `instrument_eras.yaml`, never edited.
- **Kernel loop:** the degraded negative control FAILs at PPL/coherence while passing the old non-empty check; the next real sweep produces a non-empty `pareto[]` with absolute + aggregate t/s on every OK row; `purge --git-sha` removes a row from both the store and the re-exported contract.
- **Throughput (decision-gated):** `eval_batch_serving` promotion is a codified-recipe run with operator approval, protocol id + attestation, quality parity (paired per-question) + wall-time delta; post-flip median `eval_wall_s` target <300s (from ~750s), killed-trial waste <5% (from ~18%).

## Key files
- **Orchestration loop:** `epyc-orchestrator/scripts/autopilot/autopilot.py`, `safety_gate.py`, `eval_tower.py`, `paired_stats.py`, `planner_coordinator.py`, `planner_providers.py`, `phase_health_report.py`, `phase_status.py`, `digest.py`, `audit_block_report.py`, `species/*`; `src/autopilot_core/sequential_verdict.py`, `learning_exclusions.py`, `instrument_era_guard.py`, `pareto_archive.py`; `orchestration/instrument_eras.yaml`; `MEASUREMENT.md`.
- **Orchestration dashboard:** `epyc-orchestrator/src/api/routes/dashboard.py`, `dashboard_panels.py`, `dashboard_freshness.py`, `dashboard_tap.py`, `dashboard.html`.
- **Kernel loop:** `epyc-inference-research/scripts/kernel_rnd/kernel_eval.sh`, `kernel_store.py`, `kernel_sweep.sh`; `handoffs/active/mi210-kernel-rnd-loop-proposal.md`.
- **Hub dashboard:** `epyc-root/dashboard/{server.py,handoff_parser.py,freshness.py,static/kernel.html,static/handoffs.html}`, `scripts/handoffs/build_handoff_timeline.py`.

## Provenance
- Workflow run `wf_37dce809-c0a` (7 facet audits + synthesis + gap-critic). Per-agent transcripts under the session's `subagents/workflows/wf_37dce809-c0a/`.
- Independent counts this session: journal keep/revert/species tallies, `baseline_promotion`=1 across trial-span 1169, dashboard GET/POST endpoint counts.
- Not modified: the master handoff index (index changes are operator-approval-only per CLAUDE.md). Link this handoff in from the index if you want it tracked in the active queue.
