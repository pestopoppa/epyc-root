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
- The coordinator now treats local-provider aliases as one underlying model for failover, and operator-approved Codex fallback drafts may dispatch without pausing if local drafting fails; the fallback is visible in planner archive telemetry.
- `epyc-orchestrator` `32567813` bypasses planner drafting for due sequential actions, so fresh evals, baseline draws, and W8 candidate replays no longer spend planner budget or wait on model deliberation.
- `epyc-orchestrator` `113e36b0` makes W6 gaming/core-inflation checks candidate-aware, eliminating the cross-candidate false positive that had been aging out via clean-row accrual instead of reflecting real overfit evidence.
- `epyc-orchestrator` `03dfac45` turns the planner budget line from a status string into an enforced spend breaker. When projected planner spend exceeds the configured threshold, the coordinator forces local-local planning (`local_ingest` primary, `local_worker` critic by default) instead of continuing metered cloud drafts/critique.
- `epyc-orchestrator` `0875fb50` skips inert numeric and structural candidates before eval: no-change numeric params and structural no-op flag proposals now short-circuit without burning a T1/T3 measurement.
- `epyc-orchestrator` `45c118b8` adds outcome KPIs to the dashboard API/frontend: keepable rate, wasted-eval rate, learning-excluded rate, and current-code health.
- `epyc-orchestrator` `683a20ba` adds dispatch-boundary regression coverage for inert skips.
- Focused validation passed across the touched slices: `49` planner/provider/launcher tests, `43` W6/readiness tests, `46` spend-breaker/economics tests, and `233` action/dashboard tests, plus focused `py_compile`, `ruff`, and `git diff --check`.

Next measured extension:
- Restart AutoPilot at the next trial boundary so the post-launch commits (`03dfac45`, `0875fb50`, `45c118b8`, `683a20ba`) become live. Then collect one-shot `local_ingest` planner telemetry under the spend breaker.
- Build a two-stage planner provider after the one-shot local drafter has telemetry: `ingest_long_context` synthesizes a bounded planner brief, `frontdoor` or `worker_general` drafts the action from that brief, and Codex remains an escalation/critic option only when spend policy permits. This is the orchestration-native target pattern; it should be A/B measured against one-shot `local_ingest` before becoming the default.

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
- **[P1 · M · transformative] Outcome-first stall detection + KPIs** — extend `phase_health_report.py`/`phase_status.py` with outcome blockers (no admission in N trials, HV slope ≈0 over M days, baseline age > K days, spend-triggered-with-zero-promotions); render `baseline_promotions` + keepable-rate + wasted-eval-rate + trials-since-promotion as a run-strip card on `dashboard.html`; add a file-backed autopilot outcome card to the :8100 hub; wire an operator-configurable auto-pause+escalate threshold (backtest-derived default) via the existing durable pause latch. Backtest: replay current shards; confirm it flags the trial-1005 freeze within N.
- **[P1 · M · high] Pre-eval inert-candidate skip** (narrowed) — before `hybrid_eval` in `dispatch_action` (`actions.py:459`), do a **static flag-dependency lookup** against the merged config and return `SkipOutcome('invalid','lever not active')` for knobs behind OFF flags (journaled, zero eval cost). Scope to statically-decidable cases only; do not claim to detect in-eval activation (kv-compaction firing) without dose-telemetry.
- **[P1 · S · high] Stop planner waste** — move `_maybe_force_seq_*` due-checks *ahead* of `plan_with_providers` (they consume journal/state only; ~38 metered draft+critique cycles were discarded post-hoc); add a durable **operator outbox** for operator-domain critic rejects (surfaced on the run strip) so the planner stops re-drafting the tool-sentinel lane; give `append_blacklist` a measured-harm reason-class + TTL decay so the 8 surface-wide numeric bans self-heal.
- **[P1 · M · high] Local planner tier + hard spend breaker** — add a `LocalPlannerProvider` (OpenAI-compatible against frontdoor) and route routine trial **drafts** local, reserving metered cloud for critique/escalation ([[feedback_fable5_godtier_architect_use]], [[feedback_opensource_only]]); make the $250 budget an **enforced** circuit breaker (today only a status string).
- **[P1 · S · medium] Dashboard integrity sweep** — route `autopilot_progress` duration scans through the shard-aware reader; delete dead v6 `/slots` prompt/content reads + `_find_slot_by_objective`; register the 5 unregistered panels in the freshness registry; replace bare `catch{}` with in-panel error chips.
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
