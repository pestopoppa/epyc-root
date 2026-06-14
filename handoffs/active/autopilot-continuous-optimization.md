# AutoPilot: Continuous Recursive Optimization

**Status**: **PAUSED 2026-06-13 clean-epoch checkpoint** after operator-directed resource-contention quarantine. Stale `architect_coding` escalation/fallback hygiene is fixed, response serialization/API-boundary hygiene landed, Gate-3 hard-only telemetry passed, and the contaminated pre-clean epoch is scrubbed out of live projections. Completed clean-epoch rows `#799/#800/#801/#802` are vector-bearing; `#802` is a clean T1 frontier point. Supersession-aware reads now cover reconstruction, planner trust/summary/insight views, Pareto recovery re-import, distillation/retrieval into StrategyStore memory including evidence-trial exclusion and per-insight evidence requirements, PromptForge failure context, dashboard progress/GEPA journal views, offline analytics, and preflight blacklist audit; journal scrub defaults to append-only supersession events. `autopilot.py status`/`report` can opt into read-only journal-backed archive diagnostics via `--archive-source`, but default state-backed status and all live loop/safety gate/promotion behavior remain unchanged. Baseline-promotion ledger events now append as evidence after accepted baseline updates; dashboard Pareto and task-rate/goodput replay expose that evidence read-only, while `autopilot_state.json:baseline_state` remains authoritative.

> **Current state - 2026-06-13 (post-quarantine clean restart checkpoint).** Operator decision: assume the pre-clean-epoch `#786+` contention window is corrupted and stop boundary forensics. Rows `#786-#797` are tagged `bug_corrupted_by=resource_contention_20260612` except killed placeholders `#796/#798`; `#792` remains an explicit killed/quarantined placeholder. After K7 certification completed, fresh preflight passed 9/9 and Gate-3 hard-only telemetry passed with 7 counted `get_eval_secret` calls plus no-tool isolation.
> - Superseding operator instruction expanded the conservative band to all pre-clean-epoch artifacts observed after `#786`: `#786-#797` are now tagged `resource_contention_20260612` except killed placeholders `#796/#798`, which remain `autopilot_killed_mid_trial`. Trial `#798` came from the failed `nohup`/startup-recovery attempt and is not measurement evidence.
> - Runtime projection was restored from clean backup `autopilot_state.json.bak-clear-inflight792-1781337063`; Optuna base study `autopilot_memrl_retrieval` was renamed/quarantined; API PID `3694043` was reloaded with clean env and no `ORCHESTRATOR_MEMRL_RETRIEVAL_*` variables.
> - Clean completed rows `#799/#800/#801/#802` are untagged with 55 per-question vectors each; `#802` completed cleanly as a T1 frontier point (q=`2.073`, median speed=`42.56` t/s, aggregate speed=`51.34` t/s, reliability=`1.000`) while baseline promotion was correctly skipped because it was not a reproduced same-tier representative.
> - Supersession-aware read paths now cover archive/dashboard/replay reconstruction (`f08fabd`), planner-facing trust/summary/insight context (`73e569a`), crash-recovery Pareto re-import (`41d5e80`), distillation into persistent StrategyStore memory (`005e836`), StrategyStore retrieval first by source trial (`0f07644`) and then by stored evidence-trial lists (`8a98868`), per-insight distillation evidence enforcement (`e78a380`), PromptForge failure context (`394c1bc`), dashboard progress/GEPA journal views (`cdeedcd`), offline analytics (`d21bbee`), and preflight blacklist audit (`965f507`) without mutating raw journal rows. `scrub_journal.py` now defaults to append-only supersession events (`702d785`), with legacy row rewriting only behind explicit `--rewrite-in-place`.
> - Read-only archive diagnostics landed in `9cc97bf`: `status`/`report` can compare `state`, `journal-current-run`, or `journal-all` through `--archive-source`; journal-derived snapshots reject mutation/promotion methods. Default remains `state`, and live mutation/promotion still uses the existing runtime paths.
> - Baseline promotion events landed in `0202835`: accepted `SafetyGate.update_baseline(...)` updates append non-trial `baseline_promotion` ledger rows after state/archive saves. Follow-on evidence consumers landed in `5f6c81e` and `47c75de`: `/dashboard/api/pareto` exposes current-run `baseline_promotions`, and `task_rate_goodput_replay.py` reports a `Baseline Promotion Evidence` table scoped to effective folded replay rows. Event append failures and malformed/incomplete report events are tolerated; `autopilot_state.json:baseline_state` remains authoritative for now.
> - `autopilot_state.json` is paused at `trial_counter=803`, `in_flight_trial=null`; tmux session `epyc-autopilot-20260613` is alive and waiting at the pause latch.
> - BGE repair completed healthy and the routing MLP is staged, not live. K-RAG K7 certification is complete; do not overlap any future CPU-heavy indexing/embedding/certification work with AutoPilot measurement.
>
> **Outstanding**: (1) keep `#786-#797` quarantined as historical audit rows only. (2) Continue clean AutoPilot vector-history collection from `#803` only in uncontested windows. (3) Use clean-epoch vector history for N2 W4 wiring/cutover and measured core_v2 calibration/selection.
**Created**: 2026-03-08
**Updated**: 2026-06-14 (AutoPilot paused at clean boundary after `#802`; `#786-#797` are quarantined, `#798` is killed-startup audit, and clean completed vector rows begin at `#799-#802`. N2 ledger/replay, W3 pure sequential verdicts, and J11 observe-only BSV are live in code; W4b preflight passes; stale-role and response/API-boundary hygiene landed; append-only supersession substrate and stale pause-reason cleanup landed in `3ff7af4`, scrub default switched to append-only in `702d785`, with supersession folding into archive/dashboard/replay reconstruction in `f08fabd`, planner trust/summary/insight views in `73e569a`, Pareto recovery re-import in `41d5e80`, distillation journal reads in `005e836`, StrategyStore retrieval filtering in `0f07644`, StrategyStore evidence-trial exclusion in `8a98868`, per-insight distillation evidence enforcement in `e78a380`, PromptForge failure-context filtering in `394c1bc`, dashboard progress/GEPA journal-view folding in `cdeedcd`, offline analytics folding in `d21bbee`, preflight blacklist-audit folding in `965f507`, read-only journal archive diagnostics for status/report in `9cc97bf`, baseline-promotion evidence events in `0202835`, and read-only baseline-promotion dashboard/replay evidence in `5f6c81e`/`47c75de`. See current-state banner and `progress/2026-06/2026-06-14.md`.)
**Location**: `epyc-orchestrator/scripts/autopilot/`

> **Fable 5 review (2026-06-12)**: the review's architecture recommendations now have owning handoffs: [evidence-plane-instrument-repair.md](evidence-plane-instrument-repair.md) (LIVE t775 baseline-ratchet hotfix + dead-question repair), [evidence-plane-ledger-and-sequential-verdicts.md](evidence-plane-ledger-and-sequential-verdicts.md) (per-question ledger + e-process verdicts; owns the next restart bundle), [evidence-plane-event-sourcing-and-narrative.md](evidence-plane-event-sourcing-and-narrative.md), and [objective-task-rate-goodput.md](objective-task-rate-goodput.md) (task_rate replaces the t/s axis). Full diagnosis: fable5-findings-01 + -05.

> ### 🚀 RESTART RUNBOOK — 2026-06-04 (read this before restarting the autopilot daemon)
> **State going in:** no autopilot daemon running. Last real run shut down **cleanly at trial 500 / `--max-trials`** with a full checkpoint (state/episodic/faiss, 190591 memories) — not a crash. New build is committed (`8d8c10a` + `c2033e4`, branch `fix/substring-scorer-digit-separators`) but **not yet exercised**: the binding-critic + invalid-action-feedback path is **pending the next restart**.
> **Launch:**
> - The counter is at the **500 cap** — pass `--max-trials` as an **absolute** target **>500** or it exits immediately with "Max trials reached (500)".
> - Planner mode now defaults to **`draft_critique`** (the secondary critic is BINDING: a valid `revised_action` is dispatched, a `reject` routes to the safe fallback). To stage/roll back to the old advisory-only behavior instead, export **`AUTOPILOT_PLANNER_MODE=shadow_critique`** in the launch env BEFORE starting.
> - Orchestrator should be up first: flag validation reads live state via `POST /config`; if it's down, `structural_experiment` flag proposals return non-blacklisting `skipped` (not fatal, but no flag experiments run). Use `orchestrator_stack.py` for orchestrator/llama lifecycle.
> **Confirm healthy activation (watch `logs/autopilot.log`):**
> - Mode is `draft_critique` (env unset → code default at `planner_coordinator.py:112`; or check the planner decision archive).
> - First trials **execute** instead of repeating the OLD failure — i.e. NO more endless `WARNING: Invalid flag experiment: graph_router ... requires specialist_routing`. Expect either a valid two-step (enable `specialist_routing` first, then `graph_router`) or a clean critic substitution.
> - New positive markers: `critic_rejected`, `Auto-blacklisted: Nx invalid|critic-rejected`, `consecutive rejected drafts`, binding critic substitutions taking effect (not just logged-and-ignored as in the old shadow mode).
> **STOP and escalate (operator review) if any of these latch `paused=True` in state — these are DESIGNED halts, not crashes; do NOT auto-restart through them:**
> - `skip_action_loop` — repeated non-executing actions.
> - `critic_reject_loop` — planner keeps drafting actions the critic overrides.
> - `meta_action_loop` — pre-existing meta-spin guard.
> Background + rationale: the "Binding critic is now the DEFAULT" note under **Safety Mechanisms** below, and `progress/2026-06/2026-06-04.md`.

> ### ✅ 2026-06-04 (ALL PIECES LANDED — pending operator API reload + autopilot restart to DISPLAY) — MAD over-exclusion POLICY CORRECTION: quality-noise gate must not block multi-objective Pareto admission
> **(1) Live archive / optimization engine** ✅: `ParetoArchive.upsert_representative` admits ONE robust-median representative per **stable config fingerprint** for trusted within-noise trials; dominance tested on the cluster **median**, not a lucky per-trial speed sample; cluster persists; subsumes the empty-frontier bootstrap. Admission keys on `(trusted, same-tier 4-D non-dominance, fingerprint dedup)` — NOT `reproduction_confirmed` (which is now planner-narrative only). Tolerant `ParetoEntry.from_dict`. Commits **`e67d6ee`** + wiring in parallel **`8d8c10a`**.
> **(2) Journaling de-overload** ✅ (**`8e28ba2`**): `mad_noise` joined `BENIGN_LEARNING_EXCLUSIONS` → a trusted within-noise trial is NO LONGER journaled as `bug_corrupted_by` (that field now means only genuine corruption: kills/reloads/commit-SHA). AP-22 suppression unaffected (keys on `learning_excluded_by` + `eval_details.learning_exclusion`). Re-import guard skips representative-managed rows.
> **(3) Dashboard parity** ✅ (**`206a07a`**): `_pareto_from_journal` now classifies rows (genuine-corruption skip / tier-0 audit / trusted-within-noise / normal), clusters within-noise rows by fingerprint, and admits ONE robust-median representative per config — mirroring the live archive (dominance on median). **Fingerprint corrected (both archive + dashboard)**: keyed on the FULL action signature, not just flags — empirically almost every trial runs with empty flags and the action determines the outcome, so flags-only collapsed the whole run into one dominated blob. Verified against the live journal: the q1.816/reliability-1.0 representative now appears on the reconstructed frontier (max trial 392, was 363).
> **(4) Step-5 history hygiene** ✅ (operational scrub, no code): root cause = the legacy-flat→tiered migration (`safety_gate.py:486`) seeded T0-dominated flat history (q≈2.4) into tiers ≥1, poisoning their MAD bands. Migration is compat-load-bearing (resume tests depend on it) and there's no safe permanent threshold (tier-1 scale is 0–3), so the fix is a **one-time state scrub**: removed the 2.4 artifacts from `quality_history_by_tier["1"]` (2) + `["2"]` (1); backup `orchestration/archived_backups/autopilot_state.json.pre-mad-scrub-20260604`. **Verified**: a q1.816 tier-1 reproduction now tags `reproduction_confirmed` (was plain `mad_noise`). Baseline-drift sub-item is self-limited by piece 1 (within-noise no longer calls `update_baseline`).
> **REMAINING = operator display only**: the orchestrator API (PID 2485045, started 03:07) runs the OLD `dashboard.py` — **reload the orchestrator API** to serve the new reconstruction; **restart autopilot** to load the new archive/journaling. Until then the engine logic is fixed but the live panel still shows the old reconstruction. Tests: 47+ across the touched suites; 330 dashboard/autopilot/pareto/gate green. Details: `progress/2026-06/2026-06-04.md`.
> **Treated as a policy correction, not a plotting bug** (the dashboard "frozen at 363" is the symptom). **Verified chain**: `safety_gate.py:563` MAD test is **quality-only** (`_mad_significance`, `:517`); `reproduction_confirmed` still maps to archive exclusion (`autopilot.py:1103-1119`, "no NEW point" `:1106`); live `archive.update` skipped at `autopilot.py:2199` (bootstrap only when `frontier_size(tier)==0`, `:2188`); dashboard mirrors it by skipping `bug_corrupted_by` rows (`dashboard.py:1272`). **Evidence**: raw 4-D domination test → **8 of 11 `mad_noise`-excluded tier-1 trials are non-dominated** vs the live frontier (q1.816 / reliability 1.0 region, entirely missing — neither `77 [q1.58]` nor `256 [rel0.974]` dominates it). The autopilot converged to a real frontier-worthy point; the archive logic hid it. **Nuance**: 5 of those are the *same* `seed_batch` config with speed scattered 43.8→60.75 t/s (~9% CV host noise) — so a naive "admit all `mad_noise`" would poison the frontier with throughput variance. **Fix shape (agreed)**: (1) capture first ✅; (2) split decision model — `mad_noise` keeps suppressing AP-22/strategy learning but no longer equals "not archive-worthy"; (3) on `reproduction_confirmed`, admit ONE representative Pareto point per canonical config via **robust medians over the reproduction cluster** (all objectives, not just speed); (4) guardrail — key by **stable config fingerprint**, not trial id; (5) update `tests/unit/test_safety_gate_mad.py:161` + `tests/unit/test_classify_learning_exclusion.py:66`; (6) step-5 — why tier-1 got *plain* `mad_noise` not `reproduction_confirmed` (suspect tier-1 `baseline.quality_for_tier(1)` missing/zero → predicate `:588-596` `base_q>0` fails). Recurring **defect B** from the 2026-05-31 incident ([[feedback_autopilot_noise_window_not_contention]]). Details + data: `progress/2026-06/2026-06-04.md`.

> ### ✅ 2026-06-05 — autopilot-core contract extraction landed (orchestrator `05ee0d9`)
> The MAD/dashboard/archive policy is now centralized in pure `src/autopilot_core` contracts: `action_identity.py`, `learning_exclusions.py`, `pareto_math.py`, and `journal_reconstruction.py`. `scripts/autopilot/autopilot.py`, `scripts/autopilot/pareto_archive.py`, and `src/api/routes/dashboard.py` now share the same canonical action fingerprinting, benign-vs-genuine exclusion policy, Pareto dominance/hypervolume helpers, and journal reconstruction. This also fixed the immediate static issues from the refactor plan: frontier strategy-store `hypothesis` / `expected_mechanism` use-before-assignment, missing type imports, and the `stack_commands.py` checkpoint/import wrapper duplication.
> **Verification:** GitNexus impact checks were LOW for touched high-use symbols; focused lint passed on touched autopilot/server/dashboard/core surfaces; required focused suite passed (**77 passed**); dashboard helper/route suites passed (**91 passed**); stack process/checkpoint/manifest suites passed (**72 passed**). **Remaining:** runtime behavior is intentionally unchanged; the operator still needs API reload + autopilot restart to display/load the prior MAD parity fixes, and the larger controller/dashboard split remains future work.

> ### ✅ 2026-06-04 — plot paths untangled: docs PNGs fixed (matplotlib); dashboard panel is separate + correctly current (orchestrator `648b36e`)
> Operator reported the dashboard GEPA/Pareto panel stopped gaining data ~trial 363 though the trial counter read 481. **Two distinct plot paths — only one was broken.** **(1) The docs/README/handoff PNG artifact** (`orchestration/autopilot_plots/*.png`, generated by `progress_plots.py` via a fire-and-forget `autopilot.py plot` subprocess every `PLOT_INTERVAL=10` trials, `autopilot.py:2173`) WAS broken: `matplotlib` was imported by `progress_plots.py` but **never declared** in `pyproject.toml`; a venv rebuild on 05-31 12:07 dropped it, every render raised `ModuleNotFoundError`, `generate_all_plots()` caught it and **exited 0**, and the reaper (`phase_status.reap`) only warns on non-zero exit → logged false `[async] plots-trial-N complete`. PNGs froze at `2026-05-31 12:48`. **Fixed `648b36e`**: declared `matplotlib>=3.10.9` (`uv add` + `uv.lock`); `generate_all_plots` gained `raise_on_error` (default False); `cmd_plot` now `sys.exit(1)` on failure → reaper surfaces `failed rc=1`. Verified success=0 / simulated-missing-dep=1 / `py_compile`; live cadence render fired post-install (~12:50) and succeeded. **(2) The dashboard panel is NOT that artifact** — it renders client-side from `GET /dashboard/api/pareto` (`dashboard.py::_pareto_from_journal`), reconstructing from `autopilot_journal.jsonl` per-request (no PNG, no autopilot dep — the modularized design). It is **correctly current**: caps at trial 363 because all 17 journal trials after 363 are excluded by design — 9 `bug_corrupted_by` (mad_noise/killed) skipped at `dashboard.py:1272-1274`, 8 tier-0 fast-reject audit-only (dim dots to 376) at `:1284`, **0** clean tier≥1. Verified by curling the live endpoint (frontier 77/256, dominated max 363, t0_audit max 376). So the "frozen frontier" is a **data** issue (no plottable trial since 363; 377–392 all tier-1 `mad_noise`) — likely **MAD over-exclusion** ([[feedback_autopilot_noise_window_not_contention]]), NOT a rendering bug. AutoPilot then **completed at `trial_counter=500` (`--max-trials 500`) and exited** — now down. **Next**: MAD over-exclusion investigation. Details: `progress/2026-06/2026-06-04.md`.

> ### ✅ 2026-06-03 — convergence-trap UNBLOCKED + live-confirmed (orchestrator `0c9af0f`, `b4bc605`; test fix this session)
> The planner was frozen (66 trials/24h, 0 admissions, frontier stuck at #256) operating on a false `memory_count=0`. **Root cause**: `Seeder._get_memory_count()` / `StructuralLab._get_memory_count()` imported `episodic_store.EpisodicStore` to count routing memories; in stripped runtimes the import failed on `numpy`, the exception was swallowed, and both returned `0` — poisoning the controller prompt so `train_routing_models` looked permanently blocked. Fixed with stdlib `sqlite3` counts (live DB = **175,482** routing rows). Added: planner `Action Availability` prompt section + viable-tail gating (drops `slot_compact` on empty slots, `train_routing_models` when not-converged/insufficient, recovery-only `reset_memories`/`rollback`/`distill_knowledge`); `Seeder.export_state()`/`restore_state()` persisting `td_errors`+`batch_count`+`consecutive_converged` every metric-bearing trial (legacy `td_errors`-only fallback). Codex provider stopped hardcoding `gpt-5.3-codex` (rejected on ChatGPT accounts) → uses account default unless `AUTOPILOT_CODEX_MODEL` set. **This session**: fixed the 2 pre-existing `test_autopilot_creativity.py` HV-noise-floor failures (`_hypervolume_history` → tier-aware `_hv_hist()`); 79 touched tests green; reloaded orchestrator API (PID `1943995`, loads `src/api` telemetry plumbing) and resumed AutoPilot (PID `1944777`, trial 358). **Live confirmation, trial 358**: `memory_count=175532` (false-zero gone), planner elected the previously-blocked `train_routing_models`, and codex returned a substantive `revise confidence=0.89` critique. **Follow-on blocker FIXED same session (`2cd8b87`, pending daemon restart)**: `train_routing_models` extraction/classifier/graph_router subprocesses failed `[Errno 2] No such file or directory: 'python'` (daemon runs under `.venv/bin/python`, bare `python` not on PATH); all 3 spawns now use `sys.executable` + regression test. **Daemon restarted to load it** (PID `1971340`, trial 360; source verified via `inspect.getsource`); first real training run is CPU-heavy (GAT 300s) and flag-gated (no live-routing change). Details: `progress/2026-06/2026-06-03.md`.

> ### ✅ 2026-06-02 — speed-objective token double-count fixed + Pareto speed rebase (orchestrator `1a38588`,`2447aed`,`73fd179`,`03f0038`,`24db862`,`d74a8bf`)
> AUDIT (Caveat 1): `LLMPrimitives(InferenceMixin)` shares one `total_tokens_generated`; the backend's exact count (`inference.py:772`, since 02-01) AND a char-estimate (`primitives.py:640`, since 04-12) both fire per real call → speed objective inflated. **Live probe proved it**: `tokens_generated=115` = backend (fixed, single-count); old code = 178 = **1.55×** (thinking req; no-thinking eval ≈2×). Fix = snapshot-guard the 3 accounting sites + invariant doc + regression test (`test_token_accounting_invariant.py`, 81 tests green). **Earlier "≈2× / 120 vs 60" was an unverified overstatement.** Tool telemetry now records per trial; `tool_helpfulness = P(correct|tools)−P(correct|no tools)` is a planner PRIOR, never a Pareto objective; `program.md` steers free T1/T2. Speed rebase: cleared archive (state-only) + `pareto_epoch_ts` boundary; **empty-frontier bootstrap** (`2447aed`) admits the first within-noise above-baseline trial (256 @ honest 59.68 t/s); dashboard **option (iii)** (`d74a8bf`) de-inflates pre-epoch speeds ×0.5 in place so the correction is visible (old 77@35.9 below new 256@59.7). Self-inflicted bugs fixed en route: STM non-numeric `Best quality` crash (`73fd179`), over-eager rebase-flag self-clear crash-loop (`03f0038`). Autopilot relaunched clean (singleton), trial 285. Details + process lessons: `progress/2026-06/2026-06-02.md`.

> ### 2026-06-01 — metric-free meta-loop guard, dashboard repair, and live restart
> Follow-up to the 2026-05-31 planner-context work: AutoPilot halted at 23:22 after five consecutive
> metric-free `distill_knowledge` actions. The halt was correct as a final guard, but too late; the loop
> now forces a measured `seed_batch` if the planner proposes a meta no-op after any prior consecutive meta
> action (`scripts/autopilot/autopilot.py::_force_metric_action_after_meta`, covered in
> `tests/unit/test_autopilot_actions.py`). Runtime pollution from trials 188/189/190 was backed up to
> `orchestration/autopilot_rewind187_backup_20260531_232720/`, removed from live journal/state/memory, and
> the daemon was relaunched from trial 187. Dashboard false "orphan inference"/blank-panel behavior was
> hardened with no-store headers, cache-busted fetches, `autopilot_progress` fallbacks, visible render/stream
> errors, and SSE initial-tail fetch fallbacks for planner/autopilot panels. Orchestrator was reloaded after
> the fix (API PID 4104652) and no-store headers verified by curl. At wrap-up AutoPilot PID 3793619 was
> alive, `process_status.phase=dispatch_action`, and `autopilot_progress` reported trial 208 `seed_batch`
> in flight. Trial 207 completed with `q=0.395`; safety skipped baseline update versus baseline 1.484.
> Details: `progress/2026-06/2026-06-01.md`.

> ### ✅ 2026-06-01 — gate-lock narrative FULL CLOSURE + tier-segregated dashboard (orchestrator `28d41a9`, `471b396`, `0d07da5`)
> The 2026-05-31 closure was PARTIAL because it scrubbed the strategy store but missed the **actual
> recurrence vector: the journal `falsifier` field**. The planner reads recent falsifiers every trial,
> regenerates the "stale/gate-locked baseline" story, and re-distills it — so strategy-store-only scrubs
> never held. Fixed by scrubbing ALL planner read-sources in one stopped pass (`scripts/maintenance/
> scrub_gatelock_narrative.py`, `0d07da5`): journal falsifier (22 trials), `short_term_memory.md` (5 gate-lock
> lines), `strategies.db` (16 rows + FTS + faiss + id_map rebuilt to 390). `episodic.db` left untouched
> (its "2.900" hits were microsecond timestamps). No rewind — outcomes/Pareto preserved. **Verified it held
> through a distill cycle**: 6 fresh insights, all narrative-free. Dashboard now renders all per-tier Pareto
> frontiers with shape+color (T1 circle / T2 square / T0 dim triangle audit), dominated points tier-colored,
> T0 audit frontier dashed, per-tier hypervolume (`28d41a9`, `471b396`). **T2 confirmed accessible** — pool
> ~50k q across 15 suites, `deep_eval` action wired to `tower.evaluate(tier=2)`; T2 frontier empty only
> because the planner hasn't elected a `deep_eval` yet (open item: seed it). Details: `progress/2026-06/2026-06-01.md`.

> ### ⚠️ 2026-05-31 — baseline gate-lock/frontier/planner-context contamination PARTIAL CLOSURE (orchestrator `a231556`, `89e6c9f`, `ec9622d`, `20ea4d5`, `ebd5647`)
> The safety gate ran with a never-achieved `baseline.quality`, so the regression gate
> force-reverted every honest trial and the planner looped on no-op `distill_knowledge`
> (77/81 trials 190→271 ran zero inference). All corruption paths closed and the deferred
> items cleared (details: `progress/2026-05/2026-05-31.md`):
> - **Save-path leak** (live trigger): `Baseline.save()` wrote to `DEFAULT_BASELINE_PATH`, so running
>   `test_safety_gate_baseline_eligibility` (fixture q=2.9) overwrote the real `autopilot_baseline.yaml`.
>   Fixed via `Baseline.source_path` (`a231556`). Baseline restored to `quality: 1.16`.
> - **Load guard** (`89e6c9f`): `Baseline.load()` now rejects a persisted quality above the Pareto
>   frontier max (2.9 is within [0,3] scale but unachievable → would re-lock). `update_baseline()` takes
>   `source_trial_id` + enforces archive-first ordering.
> - **No-op anti-repeat** (`a231556`): `META_NOOP_ACTIONS` (distill_knowledge, reset_memories) no longer
>   increment `trial_counter`; `MAX_CONSECUTIVE_META=5` halts a stuck planner.
> - **Rewind to trial 180** (operator-chosen, pre-planner-launch): journal trimmed <180, archive
>   `all_entries` 177→163 (frontier 8 intact ≤166), 226 orphan tags `trial-180..568` deleted.
> - **Strategy-store purge**: distill spiral wrote 784/1025 strategies encoding the bogus 2.900/9.900
>   gate-lock narrative (survives journal rewind). Purged to 241 clean (`source_trial_id<180`); FAISS
>   rebuilt via `reconstruct()`; db==FAISS==241, 0 contamination.
> - **Tier-0 frontier pollution closed** (`ec9622d`): T0 fast-reject trials remain in `all_entries`
>   for audit but no longer enter the Pareto frontier, hypervolume, or archive-max gate. Live archive
>   rebuilds to the honest T1 frontier (`best_quality≈1.895`), not saturated T0 `2.400`.
> - **Distill re-injection closed** (`20ea4d5`): `EvolutionManager.distill()` now sanitizes journal
>   failure text before prompting and before writing strategies. Live JSONL/TSV/AP-22 memory cleanup
>   leaves 0 legacy `9.900/-6.900` hits; six re-contaminated `source_trial_id>=180` strategies purged
>   and DB/FAISS/id_map are all 241.
> - **Planner-context stale telemetry closed** (`ebd5647`): `ExperimentJournal.summary_text()` hides
>   T0 production-quality metrics and all `bug_corrupted_by` metrics/reasons, so in-scale stale
>   `q=2.400` / `2.900` claims cannot re-enter the planner through recent-trial summaries. Trials
>   180–183 were tagged `bug_corrupted_by=ec9622d`; `summary_text(20)` verifies no `q=2.400` or
>   `2.900` remains. HV history was backfilled from T1/T2 archive entries only and docs plots refreshed.
>
>
> **CONFIRMED empirically 2026-05-31 18:40** (capped restart, fix `e236327` committed): re-launched
> `draft_critique` with `--max-trials 191` (note: `--max-trials` is an ABSOLUTE counter target, not
> "N more" — `--max-trials 3` against `trial=188` exits instantly). The fix is **forward-only** and
> did NOT break the loop: planner's first action was `distill_knowledge` again, re-halted at
> `consecutive_meta=6`, critique still cited the stale `think_harder q=1.816` keep. Autopilot left
> DOWN. The committed write-time fix alone was insufficient.
>
> **CLEANED 2026-05-31 20:56-22:05 UTC**: one-time runtime state prune completed while autopilot was
> stopped. Removed trial IDs 184/186/187 from active JSONL/TSV journals, removed `[t184]`/`[t186]`/
> `[t187]` AP-22 short-term-memory bullets, pruned 65 active strategy-store rows from the contaminated
> meta/distill window (`source_trial_id=184` and `188`), rebuilt SQLite FTS + FAISS/id-map to 241/241/241,
> deleted dangling local tags `autopilot/trial-184`, `autopilot/trial-186`, and `autopilot/trial-187`,
> and left `autopilot_state.json` at `paused=true`, `trial_counter=188`, `consecutive_meta_actions=0`,
> with no `_dispatch_deficiency` / `_meta_halt_reason`. Verification: active journal has no
> `bug_corrupted_by=mad_noise`; strategy retrieval has no active `#184`/`#186`/`#187`, `mad_noise`, or
> "continue exploring this surface" hits. Backups live outside the repo at
> `/mnt/raid0/llm/tmp/autopilot-prune-20260531-205634/`.
>
> **RESOLVED + RESTARTED 2026-05-31 ~22:53 UTC (orchestrator `dcfc9eb`).** The forward-only `e236327`
> was superseded by the full B→A→C fix: **B** `safety_gate.py` adds `reproduction_confirmed` (within-noise
> reproduction of an above-baseline established level) + drops reverted trials from the MAD window — MAD
> statistic unchanged (the tested invariant "same level above baseline is not a NEW improvement" is
> preserved; no baseline re-anchor); **B→C bridge** `classify_learning_exclusion`/`learning_exclusion_criticism`
> emit a benign convergence reason and `BENIGN_LEARNING_EXCLUSIONS` keeps `bug_corrupted_by` EMPTY for it
> (so `trustworthiness_score` no longer lumps confirmations with kills/reloads/SHA-invalidations); **A**
> meta-loop halt now latches `paused=true` (terminal-until-resume; survives supervisor restart),
> `_classify_meta_halt` labels converged-vs-stuck, and resume resets `consecutive_meta_actions`; **C** planner
> trust block surfaces a reproduction-convergence count + an ATTRIBUTION GUARD ("exclusions are valid
> classifications, NOT host noise; don't claim a noise window without host-health evidence") + a host-health
> line. GitNexus impact LOW on all targets; 152 autopilot-suite tests pass. Verified the 5 tier-seg commits
> (`c75b69d..f031e33`) landed on top with `dcfc9eb` as ancestor and `reproduction_confirmed`'s `base_q`
> correctly rebased to `quality_for_tier(result.tier)`.
> Staged restart (`--max-trials 300`, bg pid 3740635, log `/mnt/raid0/llm/tmp/autopilot-restart.log`): the
> planner's first post-resume turn explicitly cited the ATTRIBUTION GUARD + host-health-nominal, abandoned
> the host-noise narrative, read think_harder as CONVERGED, and pivoted to a NEW surface (`numeric_trial
> monitor`) — real trial in flight, `consecutive_meta_actions=0`. Credits: planner calls `status:"allowed"`
> within the 5h window despite `out_of_credits`/overage-rejected (~$3.4/turn). **Now running autonomously
> toward trial 300.** Deferred: host-health auto-remediation on regression (separate follow-up; would not have
> fixed this incident). Detail: `progress/2026-05/2026-05-31.md`.

## Autopilot Delegation Expansion — 2026-05-20

Search space expanded with 4 new NumericSwarm surfaces + 3 new StructuralLab-experimentable flags. Total new knobs: **7** (4 numeric + 3 boolean).

**NumericSwarm surfaces added** (`scripts/autopilot/species/numeric_swarm.py`):
- `repl_executor` (2 knobs): `repl.turn_token_cap` [256–4096], `repl.frontdoor_non_tool_token_cap` [256–4096]
- `repl_budget` (2 knobs, gated by `worker_call_budget` / `task_token_budget` flags): `repl.worker_call_budget_cap` [5–100], `repl.task_token_budget_cap` [50K–500K]
- `kv_compaction` (3 knobs, runtime-applied via `kv_compress.compress_slot()`): `kv.keep_ratio` [0.25–0.90], `kv.keep_first` [2–16], `kv.n_future` [64–1024]

**HOT_SWAP_FEATURES additions** (`scripts/autopilot/config_applicator.py`): `structured_tool_output`, `content_cache`, `model_fallback` — promoted from the `rlm-orchestrator-roadmap.md` R6 default-off candidate matrix.

**New applicator path**: `apply_kv_compact()` in `config_applicator.py` routes `kv.*` trials to `kv_compress.compress_slot()` per role (uses existing `PRODUCTION_PORTS` mapping). `apply_params()` now dispatches across three buckets: hot_swap, env_restart, kv_compact.

**Caveats captured at wire-in time**:
- `repl.turn_token_cap` and `repl.frontdoor_non_tool_token_cap`: when `difficulty_signal` mode is `enforce`, `_repl_turn_token_cap()` returns hardcoded band-adaptive values from `_BAND_TOKEN_BUDGETS` and ignores the env var. The sweep affects only the flat-cap path. If fANOVA importance is low, next step is env-var-ifying the band-adaptive dict.
- `repl.worker_call_budget_cap` and `repl.task_token_budget_cap`: sweep is meaningful only when corresponding feature flag is on. StructuralLab should toggle the flags ON before these surfaces yield signal.
- `kv.keep_ratio` lower bound clipped at 0.25 (program.md notes "below 0.25 format degrades").

**Handoff promotion**: see `research-evaluation-index.md` §P11 for outcome-observation checkboxes (P11.1, P11.1b, P11.1c, P11.1d).

## Architecture

A continuous agent loop that autonomously optimizes orchestration intelligence through 4 optimizer "species", a tiered evaluation tower, 4D Pareto archive, and safety gates.

```
Controller (Claude CLI meta-reasoning)
  ├── Species 0: Seeder (per-role eval → Q-value training)
  ├── Species 1: NumericSwarm (Optuna NSGA-II → hot-swap config)
  ├── Species 2: PromptForge (LLM prompt mutation → .md hot-swap)
  └── Species 3: StructuralLab (flags + routing model lifecycle)
  │
  EvalTower: T0 (10q/30s) → T1 (100q/5m) → T2 (500+/30m)
  ParetoArchive: 4D (quality × speed × -cost × reliability; speed is median request t/s for serial evals, aggregate batch t/s for concurrent same-trial eval batches)
  SafetyGate: quality floor + per-suite guard + routing diversity
```

## File Structure

```
epyc-orchestrator/scripts/autopilot/
  autopilot.py              # Main controller + CLI (start|status|pause|resume|report|plot|checkpoint|restore)
  experiment_journal.py     # Dual TSV + JSONL logging with rotation
  pareto_archive.py         # 4D non-dominated sorting + hypervolume indicator
  safety_gate.py            # Quality floor, regression guards, rollback triggers
  eval_tower.py             # Tiered evaluation wrapping seeding infrastructure (on_question callback for TUI)
  config_applicator.py      # Hot-swap vs restart parameter routing
  meta_optimizer.py         # Species budget rebalancing + stagnation detection
  phase_status.py           # Phase heartbeat + async auxiliary-task runner
  progress_plots.py         # 6 matplotlib visualizations (auto-updated)
  sentinel_questions.yaml   # 10 curated T0 validation questions
  program.md                # Human-editable autoresearch strategy document
  failure_blacklist.yaml    # Known-bad configs species must not re-propose
  species/
    __init__.py
    seeder.py               # 3-way eval + reward injection + convergence monitoring
    numeric_swarm.py        # Optuna multi-objective + cluster-based robust selection
    prompt_forge.py         # Claude CLI prompt mutation (targeted_fix, compress, crossover...)
    structural_lab.py       # Checkpointing, training, distillation, memory reset

epyc-orchestrator/orchestration/
  autopilot_state.json      # Persistent state (Pareto archive, trial counter, budgets)
  autopilot_journal.tsv     # Human-readable experiment log
  autopilot_journal.jsonl   # Machine-readable experiment log
  autopilot_baseline.yaml   # Frozen baseline metrics
  autopilot_checkpoints/    # Timestamped routing intelligence snapshots
  autopilot_plots/          # Auto-generated progress visualizations
  /mnt/raid0/llm/tmp/autopilot_phase.json{,l}  # Dashboard-visible loop phase heartbeat
  repl_memory/strategy_store.py  # FAISS+SQLite strategy memory (species retrieval)
```

## Key Data Structures

```python
# Action types the controller can emit
{"type": "seed_batch", "n_questions": 50, "suites": ["coder", "thinking"]}
{"type": "numeric_trial", "surface": "memrl_retrieval", "params": {}}
{"type": "prompt_mutation", "file": "frontdoor.md", "mutation": "targeted_fix"}
{"type": "structural_experiment", "flags": {"skillbank": true}}
{"type": "train_routing_models", "min_memories": 500}
{"type": "distill_skillbank", "teacher": "claude", "categories": ["routing"]}
{"type": "reset_memories", "keep_seen": true, "keep_skills": true}
{"type": "deep_eval", "tier": 2}
{"type": "rollback", "to_checkpoint": "production_best"}

# EvalResult (from eval_tower → safety_gate → pareto_archive)
EvalResult(tier, quality, speed, cost, reliability, per_suite_quality, routing_distribution)
# Parallel eval metadata in details/JSONL: speed_metric_mode, eval_concurrency,
# median_request_tps, aggregate_tps, eval_wall_s.

# ParetoEntry (4D: quality↑, speed↑, -cost↑, reliability↑)
ParetoEntry(trial_id, objectives, config_snapshot, species, git_tag, parent_trial, ...)

# JournalEntry (TSV columns + JSONL full detail)
JournalEntry(trial_id, timestamp, species, action_type, tier, quality, speed, cost,
             config_diff, parent_trial, failure_analysis, hypothesis, expected_mechanism, ...)
```

## Routing Intelligence Lifecycle

```
SEED (3-way eval) → Q-values accumulate
    │ [500+ memories?]
    ▼
CHECKPOINT → TRAIN MLP + GAT
    │ [A/B passes?]
    ▼                    ↘ RESTORE checkpoint
CHECKPOINT + ENABLE routing_classifier + graph_router
    │ [Q-values stable?]
    ▼
DISTILL SkillBank
    │ [A/B passes?]
    ▼                    ↘ RESTORE checkpoint
CHECKPOINT (production_best) + ENABLE skillbank
    │ [plateau?]
    ▼
CHECKPOINT + RESET (selective) + RESEED → back to top
```

## Safety Mechanisms

| Gate | Threshold | Action |
|------|-----------|--------|
| Quality floor | avg < 2.0/3.0 | Reject |
| Regression | Δq < -0.05 vs baseline | Reject |
| Per-suite | Δq < -0.1 any suite | Reject |
| Routing diversity | >80% architect | Reject |
| Throughput floor | <80% baseline effective speed | Reject |
| Consecutive failures | 3 × T0 fail | Auto-rollback |
| **Code mutation deep validation** | Syntax + shrinkage + public names + import test | Reject (added 2026-04-04) |
| **Catastrophic shrinkage** | >50% size reduction (code or prompt) | Reject (added 2026-04-04) |
| **Revert commit** | All reverts are git-committed | Prevents corruption as HEAD (added 2026-04-04) |
| **Planner critique failure** | Active Codex critic returns unparseable output, timeout, nonzero rc, or empty response | Fail closed through reconciliation to a safe action (added 2026-05-31) |
| **Controller action schema** | Unknown keys, missing required keys, invalid enums, or bounded-range violations | Reject before dispatch for all 14 action types (added 2026-05-31) |
| **Dirty mutation target** | Pending git status on a forge-mutated code file or prompt target/path | Skip before write/commit; git errors fail closed as dirty (added 2026-05-31) |

**Parallel-dispatch metric policy (2026-05-26 audit)**: concurrent EvalTower fan-out is valid only inside one trial's own eval batch; separate trials must not run concurrently in one autopilot process. Concurrent fan-out intentionally trades lower individual request t/s for higher aggregate batch throughput. `EvalResult.speed` and Pareto objective #2 are the effective speed for the eval mode: median request t/s for serial evals, aggregate batch t/s for concurrent same-trial eval batches. Concurrent runs also journal `speed_metric_mode`, `median_request_tps`, `aggregate_tps`, `eval_concurrency`, and `eval_wall_s`, so the planner does not infer a regression from raw per-instance slowdown while diagnostics still expose it.

**Dispatch-latency / idle-visibility policy (2026-05-26 hardening)**: the dashboard CPU-region table is a placement-readiness view, not proof that autopilot is alive or actively dispatching. `phase_status.py` now writes `/mnt/raid0/llm/tmp/autopilot_phase.json{,l}` so the dashboard can show whether the loop is stopped, paused, in health backoff, building the planner prompt, invoking the planner, dispatching, journaling, checkpointing, or scheduling async artifacts. Auxiliary plot/digest work may run asynchronously (`AUTOPILOT_ASYNC_AUX=1`, `AUTOPILOT_ASYNC_WORKERS=2`) after durable journal/state mutation; checkpointing remains synchronous. Seeder role evals may fan out with `AUTOPILOT_SEED_ROLE_CONCURRENCY=auto`, but only in contention-matrix-safe background waves with same-port and heavy-port guards. The high-blast-radius request caller contracts remain unchanged; request-level `trial_id`/`batch_id` stamping through `call_orchestrator_forced` is a separate accepted-risk follow-up, not part of this hardening.

**Controller-mode relaunch safety policy (2026-05-31 hardening)**: the Claude->Codex planner loop is safe to run only when `AUTOPILOT_PLANNER_MODE=draft_critique` uses the fail-closed coordinator path from `d5c3a2f` or later. Under active critique, Codex parse failures and provider failures no longer default to approve. The universal action validator rejects schema drift before dispatch, closing the silent-drop class where the planner and critic approve fields the executor ignores. Mutation actions also check target cleanliness before any write: code mutation checks its resolved allowlisted file, prompt mutation and GEPA check the whole `orchestration/prompts/` path because PromptForge stages that directory, and structural prune checks its exact prompt file. This prevents forge commits from sweeping pre-existing shared-clone work in a target path.

**Binding critic is now the DEFAULT (2026-06-04, epyc-orchestrator `8d8c10a`)**: `AUTOPILOT_PLANNER_MODE` defaults to `draft_critique` (was `shadow_critique`) — the critic is binding without explicit opt-in. `AUTOPILOT_PLANNER_MODE=shadow_critique` is the rollback/staging knob. A reject/revise that substitutes the draft no longer bypasses the feedback loop: the rejected draft is fingerprinted, counted, surfaced in the next prompt, and auto-blacklisted on repeat (`_record_rejected_draft`), and `MAX_CONSECUTIVE_REJECTED_DRAFTS` durably halts a planner the critic keeps overriding. Builds on the invalid-action feedback fix (`c2033e4`): the planner/critic now see live feature-flag state + dependency rules, the last non-executing action, and the blacklist. Takes effect on next autopilot restart.

## Integration Points

| Component | Path | Integration |
|-----------|------|-------------|
| Seeding 3-way | `scripts/benchmark/seed_specialist_routing.py` | Seeder wraps `evaluate_question_3way` + `_inject_3way_rewards_http` |
| Question pool | Research: `scripts/benchmark/question_pool.py` | EvalTower draws T1/T2 validation questions |
| Optuna | Research: `scripts/benchmark/optuna_orchestrator.py` | NumericSwarm reuses TPE/cluster patterns |
| Claude Debugger | `src/pipeline_monitor/claude_debugger.py` | PromptForge reuses Popen+session+git pattern |
| Episodic memory | `orchestration/repl_memory/episodic_store.py` | Seeder monitors count/convergence |
| Memory reset | `scripts/session/reset_episodic_memory.sh` | StructuralLab calls with selective flags |
| SkillBank | `orchestration/repl_memory/skill_bank.py` | StructuralLab triggers distillation |
| Config hot-swap | `src/api/routes/config.py` (POST /config) | ConfigApplicator routes flag changes |
| Feature flags | `src/features.py` (43 flags + validate()) | StructuralLab proposes flag combos |
| Strategy store | `orchestration/repl_memory/strategy_store.py` | Species retrieve past insights before proposals |

## Train/Validate Split

- **Training** (Seeder): 579 debug suite questions + 53K pool → Q-value training via per-role eval
- **Validation** (EvalTower): HF benchmark questions (MMLU, GSM8K, etc.) → system quality (end-to-end, `force_role=""`)
- Prevents overfitting: debug suites train routing intelligence, benchmarks validate generalization

## Phase 5: Per-Role Seeder (2026-04-17)

The original 3-way eval (SELF:direct, SELF:repl, ARCHITECT) was a pre-autopilot simplification that prevented Q-values from learning per-model preferences (96% uniform after 7,211 decisions). Replaced with dynamic per-role eval.

**Key changes:**
- `discover_active_roles()` reads `server_mode` from model_registry.yaml → 6 active roles
- `evaluate_question_per_role()` tests each role with `force_mode=""` (natural mode) + `allow_delegation=True`
- Rewards keyed by role name (e.g., "frontdoor", "architect_general") not abstract classes ("SELF:direct")
- Periodic role refresh every 10 batches for stack change resilience

**Adaptation surface** (when stack changes): only `seeding_types.py` needs updates — `ROLE_PORT`, `SEEDING_EXCLUDED_ROLES`, `_REGISTRY_KEY_TO_ROLE`. See `wiki/autonomous-research.md` for full table.

**Deferred**: `route_per_role()` in retriever.py (follow-up once per-role Q-values accumulate).

## Evolution: Seeding → AutoResearch

```
Seeding (passive eval, human fixes)
  → Claude-Debugger (active anomaly detection + Claude fixes during seeding)
    → AutoPilot (4-species continuous optimization)
      → AutoResearch (autonomous hypothesis-driven optimization)
```

The Claude-Debugger's capabilities are **subsumed into the autoresearch framework**: anomaly detection runs as post-trial analysis, hot-fix generation is replaced by PromptForge's `targeted_fix` mutation, session monitoring is replaced by SafetyGate's consecutive failure detection + auto-rollback.

### Stack-Config as Optimization Axis

| Axis | Species | Application Method |
|------|---------|-------------------|
| Model selection per role | StructuralLab | Restart (edit model_registry.yaml + orchestrator_stack.py) |
| Instance counts | StructuralLab | Restart |
| NUMA topology | StructuralLab | Restart |
| Tier assignment (HOT/WARM/COLD) | StructuralLab | Restart (mlock flags) |
| Acceleration flags | NumericSwarm | Restart (draft_max, moe_experts, lookup) |
| Cascade depth | StructuralLab | Restart (add/remove routing tiers) |
| General model prompting | PromptForge | Hot-swap (prompt .md files) |
| TOON compression | NumericSwarm | Hot-swap (encoding params) |

### program.md — Autoresearch Strategy Document

Located at `scripts/autopilot/program.md`. Human-editable strategy guiding autonomous experimentation:
- **Immutable boundary**: Evaluation methodology, scoring, safety gates, core orchestrator code
- **Mutable scope**: Prompts, configs, registry, stack topology, feature flags, specialist pipelines
- **Goal metric**: Debug suite pass rate (deterministic, no LLM judge) for fast iteration
- **Git-based ratchet**: Every improvement is a commit; degradations are reverted
- **Known dead ends**: Documents approaches that have been empirically exhausted

Key principles: one variable per experiment (clean attribution), simplicity criterion (reject disproportionate complexity), NEVER STOP, failure memory (never retry known-bad approaches).

### Related Handoffs

- [`dynamic-stack-concurrency.md`](dynamic-stack-concurrency.md) — Full NUMA scheduling architecture, Phases B-D complete
- [`routing-and-optimization-index.md`](routing-and-optimization-index.md) — Umbrella view of all optimization subsystems
- [`meta-harness-optimization.md`](meta-harness-optimization.md) — Execution trace feedback for PromptForge (3-tier plan)

## Usage

```bash
# Start optimization loop
python scripts/autopilot/autopilot.py start

# Start without Claude CLI controller (autonomous mode)
python scripts/autopilot/autopilot.py start --no-controller

# Dry run (no API calls, synthetic results)
python scripts/autopilot/autopilot.py start --dry-run --max-trials 10

# Check status
python scripts/autopilot/autopilot.py status

# Pause/resume
python scripts/autopilot/autopilot.py pause
python scripts/autopilot/autopilot.py resume

# Generate report / plots
python scripts/autopilot/autopilot.py report
python scripts/autopilot/autopilot.py plot

# Checkpoint / restore
python scripts/autopilot/autopilot.py checkpoint --production-best
python scripts/autopilot/autopilot.py restore
```

## Numeric Parameter Surfaces

| Surface | Key Params | Application |
|---------|-----------|-------------|
| memrl_retrieval | q_weight, min_similarity, min_q_value, confidence_threshold, semantic_k, prior_strength | Hot-swap via env + restart |
| think_harder | min_expected_roi, token_budget_min/max, cot_roi_threshold | Hot-swap via env + restart |
| chat_pipeline | try_cheap_first_quality_threshold | Hot-swap via env + restart |
| monitor | entropy_threshold, repetition_threshold, entropy_spike_threshold | Hot-swap via env + restart |
| escalation | max_retries, max_escalations | Hot-swap via env + restart |

## Dependencies

- Python 3.11+
- `optuna` (pip install optuna) — NumericSwarm Bayesian optimization
- `matplotlib` (already installed) — Progress plots
- `httpx` (already installed) — API calls
- `scikit-learn` (optional) — Cluster-based robust selection
- `claude` CLI (on PATH) — Controller meta-reasoning (optional, --no-controller for autonomous mode)

## Implementation Status

All core infrastructure verified in code as of 2026-04-01:

- [x] AP-1: Wire `failure_context` into PromptForge dispatch (2026-03-29)
- [x] AP-2: Feed failure narratives into controller prompt via `summary_text()` (2026-03-29)
- [x] AP-3: Populate `parent_trial` and `config_diff` journal fields (2026-03-29)
- [x] AP-4: `lab failures`-style query — `journal.recent_failures()` (2026-03-29)
- [x] AP-5: Per-suite quality trends in controller prompt (2026-03-29)
- [x] AP-6: Persist `consecutive_failures` counter across sessions (2026-03-29)
- [x] AP-7: Invalidate stale Optuna trials after regime changes — `mark_epoch()` (2026-03-29)
- [x] AP-8: Hypothesis + expected_mechanism tracking on JournalEntry (2026-03-29)
- [x] AP-10: Simplicity criterion — reject >20% prompt growth for <0.02 quality (2026-03-29)
- [x] AP-12: TUI 4-panel live monitor (`--tui` flag) (2026-03-22)
- [x] AR-2: Smoke test passed — 5 dry-run trials verified (2026-03-29)
- [x] SafetyGate `analyze_failure()` — structured violation narrative (2026-03-15)
- [x] StrategyStore (FAISS+SQLite) built in `repl_memory/strategy_store.py` (2026-03-15)
- [x] Cost tracking — `estimated_cost` field on `RoutingResult` (2026-03-15)
- [x] B1: Wire `strategy_store.retrieve()` into PromptForge species (2026-04-01)
- [x] B2: Failure blacklist — `failure_blacklist.yaml` with auto-append (2026-04-01)
- [x] B3: Execution trace feedback — `inference_tap.log` → PromptForge (2026-04-01)
- [x] B4: `insights_text()` on ExperimentJournal (2026-04-01)
- [x] B5: Cross-species fertilization via insights injection (2026-04-01)
- [x] #4: Evolution Manager species — 5th species for knowledge distillation (2026-04-01)
- [x] #5: Skeptical re-questioning gate — `_proxy_check()` in SafetyGate (2026-04-01)
- [x] #6: Forbidden proxy seeding — known dead ends in `failure_blacklist.yaml` (2026-04-01)
- [x] #7: Context budget management — auto-checkpoint every 25 trials (2026-04-01)
- [x] #8: Per-species token budget — `SPECIES_TOKEN_BUDGETS` in meta_optimizer (2026-04-01)
- [x] Tier 2: Code mutations in PromptForge — `code_mutation` action type + allowlist (2026-04-01)
- [x] Deep code mutation validation — shrinkage + public names + import test (2026-04-04)
- [x] Catastrophic shrinkage guard — >50% reduction blocked for code and prompts (2026-04-04)
- [x] Revert commits — reverts auto-committed to prevent corruption as HEAD (2026-04-04)
- [x] TUI on_question for EvalTower — prompt panel shows actual questions during deep eval (2026-04-04)
- [x] Hybrid eval gate — T0 fast-reject + T1 real gate replaces saturated T0-only eval (2026-04-04)
- [x] Tier-aware safety gate — quality floor and regression scaled by eval tier (2026-04-04)
- [x] Baseline recalibration — recalibrated to T1/T2 scale (q=1.16) from inflated T0 scale (2026-04-04)

## Remaining Work — Prioritized

### HIGH priority (next compute session)

1. **AR-3 continuation**: Relaunch with new Phase 5 per-role seeder — `python scripts/autopilot/autopilot.py start --tui`
   - Run 2 (2026-04-02–04): 46 trials, 7 frontier. One useful change: `get_direct_answer_prefix()` in resolver.py (q 2.4→3.0)
   - **Corruption incident**: Trial ~25 replaced escalation.py (454→3 lines). API down 11+ hours. Safety hardened (5 gaps fixed).
   - ~~T0 saturated at q=3.0~~ **FIXED**: Hybrid eval (T0 fast-reject + T1 real gate) now gives honest signal per trial.
   - Baseline recalibrated to T1 scale (q=1.16). Safety gate tier-aware.
   - Phase 5 seeder refactor (2026-04-17) completed — restart with fresh baseline.

*(AP-14/15/16/17 moved to Completed Work — all ✅ 2026-04-07 per routing-and-optimization-index P11. See Implementation Status section below.)*

### P10 — GEPA PromptForge Integration (intake-327/345/240)

Source: hermes-agent-self-evolution (DSPy+GEPA), GEPA Full Program Adapter (93% MATH), GEPA paper (ICLR 2026 Oral). GEPA uses reflective trace analysis (ASI = Actionable Side Information) for 35x fewer rollouts than GRPO. Compatible with local inference (Ollama/vLLM format). 3-example minimum. MIT licensed.

- [x] AP-18: Install DSPy, wrap 3 routing prompts as DSPy Signatures — ✅ 2026-04-12. `dspy>=2.5.0` added to pyproject.toml. `src/dspy_signatures/` package: FrontdoorClassifier, EscalationDecider, ModeSelector signatures + config.py (configure_local_lm, configure_rlm). 8 smoke tests.
- [x] AP-19: GEPA frontdoor optimization — ✅ **Integrated into AR-3** (2026-04-12). `gepa_optimizer.py` adapter + `gepa` mutation type in PromptForge. 30% of PromptForge trials use GEPA evolutionary optimization via `OrchestratorGEPAAdapter` (evaluates through orchestrator API with sentinel questions). AR-3 journal collects comparison data automatically. 10 tests pass.
- [x] AP-20: GEPA Full Program Adapter eval — ✅ **Folded into AR-3** (2026-04-12). Resolved by comparing GEPA vs LLM mutation acceptance rates + Pareto frontier contributions in AR-3 journal after ~50 trials. No separate inference run needed.
- [ ] AP-21: PromptForge GEPA refactor decision — **Conditional on AR-3 data**. If GEPA trials dominate Pareto frontier after 50+ trials → increase GEPA ratio from 30% to 100%. If no improvement → keep mixed or revert to LLM-only.

### P11 — Autopilot Controller Upgrades (intake-328/329/349/320)

Source: MiniMax M2.7 3-component self-evolution harness (100+ autonomous rounds), dspy.RLM (WASM sandbox + sub_lm pattern), Unsloth RLVR (environment-first RL).

- [x] AP-22: Add `short_term_memory.md` per trial — ✅ 2026-04-12. `ShortTermMemory` class in `short_term_memory.py` (load/update/clear/to_text). Persists as markdown with 4 sections (hypotheses, directions, failures, context). Token-budgeted (~120 lines). Injected into CONTROLLER_PROMPT_TEMPLATE. CLI: `autopilot.py reset-memory`.
- [x] AP-23: Add explicit self-criticism step before next proposal — ✅ 2026-04-12. `self_criticism.py` with rule-based `generate_self_criticism()`. `SelfCriticism` dataclass (what_went_wrong, why, what_should_change, optimization_directions, keep/revert). Inserted between Evaluate and Record in controller loop. No inference cost.
- [x] AP-24: Formalize keep/revert protocol with structured forward-looking reasoning — ✅ 2026-04-12. `keep_revert_decision` and `optimization_directions` fields on JournalEntry. Centralized in `generate_self_criticism()`. Directions feed into short-term memory accumulator.
- [x] AP-25: Set up dspy.RLM with llama-server `/v1/` endpoint — ✅ 2026-04-12. `configure_rlm(main_lm_url, sub_lm_url)` in `src/dspy_signatures/config.py`. Coder as main LM, frontdoor as sub_lm. `test_connection()` health check. Integration testing deferred to AP-26 (needs inference).
- [ ] AP-26: Test dspy.RLM for autopilot tasks — long-horizon benchmark analysis where metadata-first context exploration avoids context window limits
- [ ] AP-27: Formalize eval tower tiers (T0/T1/T2) as RLVR verification functions with deterministic reward signals per tier (state matching, not LLM-as-judge). **Implementation plan**: See [eval-tower-verification.md](eval-tower-verification.md) EV-1–EV-7. Depends on EV-4 (calibration baseline) and P7 Ouro results.

### P17 — Bradley-Terry Tiebreak Under Hypervolume Stagnation (intake-615)

Source: arxiv:2510.24801 — Fortytwo: Swarm Inference with Peer-Ranked Consensus. The Bradley-Terry-style aggregation over pairwise rankings is the formal generalization of "pairwise comparison with confidence" that NumericSwarm currently approximates via 4D Pareto + hypervolume scalarization. Their published +17.21pp on GPQA-Diamond over majority voting is the empirical evidence that BT extracts ordering signal a scalar can't.

**Sub-task IDs use the `P17.BT-N` namespace** to avoid collision with the existing `AP-37 / AP-38 / AP-39 / AP-40` IDs already used by the 2026-05-23/24 constrained-creativity + launcher-threadcount work (see Implementation Status table line 769+).

**Concrete integration** (~50 LOC, falsifiable in one autopilot run):

- [x] **P17.BT-1 ✅ 2026-05-27** (epyc-orchestrator commit `2e51c86`): Shared module `src/bradley_terry.py` landed. Pure function `bradley_terry_rank(items, win_matrix) -> BTResult` with `bradley_terry_from_pairs` and `bradley_terry_from_scores` convenience wrappers; diagnostics for disconnected graphs, Condorcet cycles, dominance skew; dual convergence criteria (tight numerical + ranking-stability for perfectly-separable data where MLE is at infinity). 16 unit tests in `tests/unit/test_autopilot_bradley_terry.py`. Shared with [`swarm-dataset-distillation.md`](swarm-dataset-distillation.md) Phase 3 and [`decision-aware-routing.md`](decision-aware-routing.md) DAR-6.4 — do not duplicate.
- [x] **P17.BT-2 ✅ 2026-05-27** (epyc-orchestrator commit `2e51c86`): New method `ParetoArchive.bt_tiebreak_topk(k=5)` + rich-prompt wiring in `_build_exploration_block`.
  - **What it actually does**: builds pairwise win-scores from the four existing objective axes (axis-vote / Borda count over recorded 4D objectives), then runs BT on those. The pairwise inputs are **NOT independent model judgments** of candidate outputs — they are mechanical comparisons of already-known scalar objectives. This is a **cheap axis-vote proxy** that uses the BT engine on data we already have, NOT the Fortytwo-style peer-ranked consensus described in intake-615.
  - **What it does NOT do**: run actual peer-evaluation across independent model judges (which would require new inference). The Fortytwo-faithful version would have N judges score each candidate and aggregate — INFERENCE-GATED and out of scope for P17.BT-2.
  - **Why this is still useful**: hypervolume scalarization collapses 4 axes into one number and can hide candidates that consistently beat peers across axes without being scalar-dominant. Axis-vote BT surfaces those as exploration seeds. Strictly cheaper and weaker signal than peer-ranked consensus.
  - **Top-K selection is range-normalized (scale-bias resolved 2026-05-27 commit `56ee9fc`)**: at `pareto_archive.py:348-358` each axis (obj − ref) is divided by `(max_e(obj) − ref)` across the frontier before summing, so every axis contributes on [0, 1] regardless of physical magnitude. The candidate set fed to BT is no longer biased by speed-in-t/s magnitude swamping reliability-in-[0,1]. Remaining limitation is the proxy-vs-peer-judge axis (still axis-vote, not judge-model — that's P17.BT-4 below).
  - 8 new unit tests in `tests/unit/test_autopilot_bt_tiebreak.py`. The axis-vote helper remains tested as an offline/shared diagnostic, but the live rich-prompt injection and stagnation-reason append were removed at `b8c0611` after P17.BT-3 failed to certify seed-level value.
- [x] **P17.BT-3 CLOSED 2026-06-12; cleanup landed 2026-06-13**: Falsification over the existing run passed sample size (341 rich/stagnation-fired trials, 75 logged BT disagreements) but could not certify the exact seed-level gate because the journal/logs do not persist BT top ID, hypervolume-top ID, or chosen-seed lineage. Available proxy outcomes were weak/clustered (`current frontier`: 2/75 disagreement events vs 9/266 no-disagreement rich events; cluster-start next-10 frontier: 1/7 vs 8/34 thinned no-disagreement rich prompts). Verdict: do not queue P17.BT-4. The cosmetic `bt_tiebreak_hint` rich-prompt block was removed from live orchestrator at `b8c0611` while AutoPilot was paused; `ParetoArchive.bt_tiebreak_topk()` remains as an offline/shared diagnostic.
- [x] **P17.BT-4 KILLED/DEFERRED 2026-06-12** — *true Fortytwo-style peer-ranked BT*: do not queue judge-model pairwise scoring from the current evidence. Reopen only after an explicitly instrumented P17.BT-3 rerun persists BT top ID, hypervolume-top ID, chosen seed/action lineage, and shows a positive seed-level signal.

**Cross-task interactions** (see § Scoring Upgrade Backlog below): the BT module here is the SAME algorithm that [`swarm-dataset-distillation.md`](swarm-dataset-distillation.md) Phase 3 needs for filtering swarm-generated candidate completions (where the pairwise inputs WILL be real judge-model scores, not axis-votes). Implementing P17.BT-1 here unlocks that handoff's Phase 3 too.

### Scoring Upgrade Backlog (consolidation 2026-05-27)

Three "Research Intake Update" sections have surfaced **scoring-mechanism** upgrades for NumericSwarm over the past ~6 weeks. They are not three independent ideas — two of them operate on the *selection step* and partially substitute, one operates on *information sharing across species* and is orthogonal. Consolidating here so a future agent does not implement them redundantly.

| # | Source | Operates on | What it changes | Status | Interactions |
|---|---|---|---|---|---|
| 1 | intake-248 (SiliconSwarm@Ensue) | Cross-species info-sharing | Shared-memory + insights publishing every iteration; one agent's dead-end prevents others repeating | **Applied** (B1, B4, B5 — see § Research Intake Update — 2026-04-18 and DD-strategy-store) | Orthogonal to the two below; do not subsume |
| 2 | intake-269 (TPO / Cross-Entropy Method) | Selection step (sampler) | Replace NSGA-II/Optuna with CEM-style Gaussian-fit-to-elites on the 23-param numeric surface; particularly when hypervolume stagnates | **DESIGN NOTE only** — never operationalized; see § Research Intake Update — 2026-04-26 | Substitutes with the BT tiebreak on the same stagnation trigger; implement **one first**, A/B against the other |
| 3 | intake-615 (Fortytwo BT) | Selection step (tiebreak) | When scalarization is the noisy step, BT-rank the top-K Pareto candidates and pick by ranking confidence | **P17 above (this section)** — implementation specified, falsification gate defined | See #2 — same trigger surface |

**Recommended sequencing**:
1. Land P17.BT-1 (the shared BT module) — cheapest, ~50 LOC, also unblocks [`swarm-dataset-distillation.md`](swarm-dataset-distillation.md). **Done 2026-05-27** (orchestrator commit `2e51c86`).
2. Land P17.BT-2 (axis-vote BT tiebreak prompt experiment) — cheap proxy using already-recorded data. **Done 2026-05-27** (same commit), then removed from the live rich prompt at `b8c0611` after negative/non-certifying P17.BT-3 analysis.
3. P17.BT-3 falsification closed 2026-06-12 negative/non-certifying; cosmetic rich-prompt hint removed at `b8c0611` on 2026-06-13.
4. P17.BT-4 is killed/deferred; do not spend judge-model inference on peer-ranked BT from this evidence.
5. Because P17.BT-3 failed to certify seed-level value, revisit intake-269 TPO/CEM only after the N2 evidence-plane redesign gives selector experiments enough attribution to be meaningful.
6. Continue extending the SiliconSwarm cross-species sharing pattern as orthogonal optimization; do not bundle with #2/#3 work.

### DEFERRED (explicit reasons)

2. ~~**GEPA integration** (intake-240)~~: **PROMOTED to P10** (2026-04-12). Deep-dive confirmed GEPA works with local inference, 35x cheaper than GRPO, 3-example minimum. No longer needs to wait for AR-3 PromptForge limitations — GEPA is strictly better.
3. **Hard-negative training data** (intake-176): Contrastive negatives for routing classifier. Only relevant when 500+ memories exist for retraining.
4. ~~**Git worktree isolation for PromptForge**~~: ✅ 2026-04-05. Implemented `worktree_manager.py` with `WorktreeManager` + `ExperimentContext`. Auto-reject safety default prevents corruption incidents like AR-3 trial ~25.
5. **Convention locking** (intake-150): Lock baseline parameters from species modification. Premature without more trials.

### Design considerations (no implementation needed)

6. ~~**Tighter per-trial scope**~~: ✅ 2026-04-05. Implemented as code enforcement via `_validate_single_variable()` in `autopilot.py`. Rejects multi-file, multi-flag, and multi-param actions before dispatch.
7. **Explicit eval trust boundary**: Document that EvalTower scoring code is immutable — species must never modify it. Add to `program.md` constraints.

## Research References

| Intake | Paper | Key Insight | Applied? |
|--------|-------|-------------|----------|
| 108 | EvoScientist (arxiv:2603.08127) | Evolution Manager separates knowledge distillation from execution | Informed Evolution Manager species design (#4) |
| 106 | Agentic Critical Training (arxiv:2603.08706) | GRPO-based self-reflection for quality-aware agents | Background — AutoPilot evaluates via benchmark tower instead |
| 105 | PostTrainBench (arxiv:2603.08640) | Autonomous post-training plateaus after ~5h | Calibrates expectations for AR-3 run length |
| 142 | Cheat-Sheet Distillation (arxiv:2509.20820) | Difficulty-focused distillation outperforms broad textbook style | Applies to `distill_skillbank` in StructuralLab |
| 148/149 | AutoResearch + PraxLab | Tight constraints + failure memory + git ratchet | Core design of `program.md` and failure blacklist |
| 150 | GPD (get-physics-done) | Skeptical re-questioning, forbidden proxies, convention locks | Informed items #5-7 in remaining work |
| 176 | ReasonIR (arxiv:2504.20595) | Hard-negative training data for routing classifier | Deferred (#10) until 500+ memories |
| 240 | GEPA (arxiv:2507.19457) | Pareto-aware prompt evolution, 35x fewer rollouts vs RL | Deferred (#9) — potential PromptForge replacement |
| 244 | Meta-Harness (arxiv:2603.28052) | Execution trace feedback +15pts over score-only | **Applied** (B3) — traces fed to PromptForge |
| 248 | SiliconSwarm@Ensue | Cross-agent knowledge transfer breaks plateaus | **Applied** (B1, B4, B5) — strategy store + insights + cross-species |
| 265 | Omni-SimpleMem (arxiv:2604.01007) | Bug fixes > tuning on broken baselines; 6-type discovery taxonomy; 4 suitability properties (we pass all 4) | AP-14 deficiency classification, AP-15 field audit |
| 271 | Skill Issue: Harness Engineering (HumanLayer) | Harness config drives ~28 TerminalBench-2 rank delta; 14-22% instruction overhead; CLI > MCP heuristic | AP-16, AP-17 |
| 272 | Evaluating AGENTS.md (ETH Zurich, 2602.11988) | Context files REDUCE success rates, +20% cost; help only when docs absent; thin-map not tested | AP-16, AP-17 |
| 273 | Context Rot (Chroma) | Shuffled > structured for RETRIEVAL only; semantic similarity compounds degradation | Background — informs CF experiments |
| 274 | The Complexity Trap (2508.21433) | Observation masking matches LLM summarization at 50% cost; hybrid 7-11% further | Validates two-layer compression architecture |
| 312 | Mismanaged Geniuses Hypothesis (Zhang/Khattab) | Decomposition space design is the key variable; 4B RLM→100% MRCRv2 via composition | Theoretical foundation for P10/P11 |
| 320 | Unsloth RL Environments | RLVR (verifiable rewards) maps 1:1 to eval tower; environment-first RL design | AP-27 |
| 327 | Hermes Agent Self-Evolution (NousResearch) | GEPA reflective trace analysis + 6-stage optimization loop; $2-10/run via API | P10 (AP-18–21) |
| 328/329 | MiniMax M2.7 Self-Evolution | 3-component harness (memory+feedback+optimization), 100+ autonomous rounds, 30% improvement | P11 (AP-22–24) |
| 345 | GEPA Full Program Adapter | 93% MATH (vs 67% base); evolves signatures+modules+control flow; 35x fewer rollouts | P10 (AP-20) |
| 349 | dspy.RLM Module | Metadata-first REPL exploration; sub_lm pattern; works with OpenAI-compatible /v1/ endpoint | P11 (AP-25–26) |

## Known Issues — KV Cache seq_add Crash on Qwen3.5 Hybrids (2026-04-15, PATCHED)

architect_general (Qwen3.5-122B-A10B, ports 8083+8183) crashed with assertion failure in `llama-kv-cache.cpp:614`:
```
GGML_ASSERT(hparams.n_pos_per_embd() == 1 && "seq_add() is only supported for n_pos_per_embd() == 1")
```

**Root cause**: Qwen3.5 architecture uses `LLAMA_ROPE_TYPE_IMROPE` (interleaved multi-rope, `n_pos_per_embd() == 4`) — same positional encoding as Qwen3-VL vision models, even in text-only mode. The `seq_add()` and `seq_div()` functions in `llama_kv_cache` had overly conservative assertions blocking any model with `n_pos_per_embd() != 1`. The crash triggered when the server's context checkpoint system called `seq_add` during KV chunk reuse (prompt cache hit with position shift). `get_can_shift()` also returned false, which would have caused `GGML_ABORT` if reached.

**Impact**: architect_general went down around trial 204, causing `routing_distribution` to collapse to `{"frontdoor": 1.0}`. Quality dropped from q≈2.10 to q≈1.14. Trials 204-215 data is tainted (frontdoor-only, no escalation routing). Autopilot's short-term memory has been annotated with operator note explaining the crash.

**Fix (2026-04-15)**: Patched 3 locations in `llama-kv-cache.cpp`:
1. Removed `GGML_ASSERT(n_pos_per_embd() == 1)` from `seq_add()` — the underlying `pos_add()` operates on scalar base position, and K-shift already handles IMROPE correctly (falls back to NEOX-style rotation via `build_rope_shift()`, see `@ngxson` workaround at line 1884)
2. Removed same assertion from `seq_div()`
3. Removed `n_pos_per_embd() > 1` guard from `get_can_shift()` — K-shift graph builder already supports IMROPE

Both NUMA instances relaunched with patched binary. Fix applies to all Qwen3.5 hybrids (QWEN35, QWEN35MOE arches). Dense models (Qwen3, Qwen3MOE) were unaffected (use NEOX rope, `n_pos_per_embd() == 1`).

**Verification needed**: Run seed_batch trials to confirm architect routing restored and quality recovers to q≈2.10.

## Known Issues — Architect Think-Block Loop (2026-04-14, RESOLVED 2026-04-15)

Qwen3.5-122B-A10B on `architect_general` enters degenerate `<think>` block loops during routing decisions. Model closes a think block, emits partial answer, then re-opens `<think>` repeatedly — burning the full 512-token budget per attempt.

**Root cause (revised 2026-04-15)**: The `--jinja` server flag loads Qwen3.5's native chat template, which includes `<think>`/`</think>` block scaffolding. The template itself primes the hybrid SSM+MoE model into think mode. Previous mitigations (`--reasoning off`, `_architect_early_stop()` streaming detection) were insufficient — the jinja template injects thinking preamble before `--reasoning` can suppress it.

**Fix applied (2026-04-15)**: Removed `--jinja` flag from architect_general server launch entirely. Without `--jinja`, llama-server falls back to generic ChatML template which has no thinking scaffolding — model never enters think mode. Also removed now-unnecessary `--reasoning off`. All other roles retain `--jinja`. Change in `orchestrator_stack.py:build_server_command()`.

**Previous mitigations (superseded)**:
- `--reasoning off` server flag (commit 0591952) — insufficient, jinja template still primed thinking
- `_architect_early_stop()` streaming detection (2026-04-14) — band-aid, didn't prevent wasted tokens
- `repeat_penalty`/`temperature` tuning — never applied, no longer needed

## Staleness Notes

- `optuna_orchestrator.py`: TPE/cluster patterns reusable; parameter ranges stale (predate current config/models.py)
- `seed_specialist_routing.py`: Canonical source at `epyc-orchestrator/scripts/benchmark/` (1,449 lines)
- `orchestrator_self_management.md` Phase 9: Deferred Optuna loop; architecture evolved significantly
- `pre-split-optimization-ab-test-plan.md`: Decision function reusable; specific paths broken post-split

## Verification Plan

1. **Smoke test**: `python autopilot.py start --dry-run --max-trials 5`
2. **Seeder integration**: Run 20-question batch, verify reward injection
3. **NumericSwarm**: Create Optuna study, suggest trials, verify cluster selection
4. **PromptForge**: Propose mutation, apply, verify git snapshot
5. **Full loop**: 10 trials across all species, verify journal + Pareto + safety gate
6. **Overnight**: 8-hour unattended run, check hypervolume trend

## Research Intake Update — 2026-04-06

### New Related Research
- **[intake-265] "Omni-SimpleMem: Autoresearch-Guided Discovery of Lifelong Multimodal Agent Memory"** (arxiv:2604.01007)
  - Relevance: AutoResearchClaw is a 23-stage autonomous research pipeline — directly comparable to our 4-species AutoPilot architecture
  - Key technique: Multi-agent debate + self-healing execution; autonomous experiment loop (~50 experiments)
  - Reported results: +411% F1 on LoCoMo, +214% on Mem-Gallery; bug fixes (+175%) > all hyperparameter tuning combined
  - Delta from current approach: Their finding that bug fixes and architectural changes vastly outperform hyperparameter tuning validates prioritizing Species 2 (PromptForge) and Species 3 (StructuralLab) over Species 1 (NumericSwarm). Consider increasing structural species budget allocation. The 23-stage pipeline with debate is more sophisticated than our 4-species approach — may inform future species design.

- **[intake-267] "ByteRover: Agent-Native Memory Through LLM-Curated Hierarchical Context"** (arxiv:2604.01599)
  - Relevance: Agent-native memory where the LLM itself curates knowledge in hierarchical markdown files — validates autopilot state management direction
  - Key technique: Hierarchical Context Tree with importance scoring + recency decay; sub-100ms retrieval
  - Delta from current approach: Our autopilot_state.json is a flat JSON store. ByteRover's hierarchical approach with LLM-driven curation could inform how autopilot manages its experiment journal and Pareto archive for better context retrieval across long runs.

### Deep-Dive Correction (2026-04-06)
**Caveat on intake-265**: The "bug fixes > tuning" headline is misleading. The baseline was catastrophically broken (F1=0.117 vs SimpleMem SOTA 0.432) — a missing `response_format=json_object` caused 9x verbosity. The finding generalizes to "fixing broken systems beats tuning broken systems," not "structural always beats numeric." Our AutoPilot operates on a functioning system where NumericSwarm is in the right regime. **No species budget rebalancing needed from this paper alone.** However, two small improvements validated: (1) add structured deficiency classification to experiment_journal.py error handling, (2) ensure all species populate hypothesis/expected_mechanism journal fields. The 4 autoresearch suitability properties (scalar metrics, modular architecture, fast iteration, version-controlled modifications) are a useful checklist — our AutoPilot satisfies all 4.

## Research Intake Update — 2026-04-12

### New Related Research
- **[intake-327] "Hermes Agent Self-Evolution"** (NousResearch) — DSPy+GEPA skill optimization
  - Relevance: Directly applicable to PromptForge species — evolutionary optimization of skills/prompts without GPU
  - Key technique: GEPA reflective evolutionary search with execution trace analysis
  - Delta from current approach: Our PromptForge uses LLM-guided mutation. GEPA uses evolutionary + Pareto-optimal selection. Their $2-10 per run is API-based; adapting to local models eliminates cost. Guardrails (test validation + human review) are more conservative than our safety gates.
- **[intake-338] "Agent Lightning"** (Microsoft Research) — Zero-code agent optimization
  - Relevance: Three optimization modes (RL, prompt optimization, SFT) map to our species: RL→NumericSwarm, prompt→PromptForge
  - Key technique: Framework-agnostic tracing + optimization. Zero code change adoption.
  - Delta from current approach: Agent Lightning could optimize our orchestrator without modifying existing code. The trajectory-level aggregation addresses our per-question vs per-trajectory eval gap.
- **[intake-344] "LightningRL: Hierarchical Credit Assignment"** (arxiv:2508.03680)
  - Relevance: Solves autopilot evaluation granularity problem — attributes task success to specific orchestrator decisions
  - Key technique: Per-LLM-request credit assignment + reward scoring, compatible with PPO/GRPO
  - Delta from current approach: We evaluate at task-level (T0/T1/T2). LightningRL enables per-step attribution. Could dramatically improve PromptForge mutation signal quality.
- **[intake-345] "GEPA Full Program Adapter: 93% MATH"** (DSPy tutorial)
  - Relevance: Evolves entire program structure (not just prompts) — 93% vs 67% baseline on MATH
  - Key technique: GEPA evolving DSPy signatures, modules, and control flow with as few as 3 examples
  - Delta from current approach: PromptForge only mutates prompt templates. GEPA Full Program Adapter could evolve routing logic, tool definitions, and escalation pipeline. The +26pp improvement is transformative.

### Deep-Dive Synthesis (2026-04-12)
**Cross-cutting finding from 26-entry deep-dive**: Four converging research threads point to a major autopilot upgrade path:
1. **GEPA** (intake-327/345): Reflective trace analysis + evolutionary Pareto search. 35x more efficient than GRPO. 3-example minimum. Compatible with our local inference (Ollama/vLLM format). **Priority #1 for PromptForge upgrade.**
2. **dspy.RLM** (intake-349): Metadata-first context exploration via REPL sandbox. Sub-LM pattern maps to our coder+frontdoor stack. Directly addresses context window limitation for long autopilot runs. **Priority #2 for autopilot infrastructure.**
3. **MiniMax M2.7 self-evolution** (intake-328/329): Three-component harness (short-term memory markdown + self-criticism + forward-looking optimization) over 100+ autonomous rounds. Pattern directly implementable in our controller. Add `short_term_memory.md` per trial, explicit self-feedback step before next proposal, and formalized keep/revert protocol.
4. **Unsloth RLVR** (intake-320): Our eval tower IS an RLVR environment. Formalize T0/T1/T2 as verification functions, not just benchmarks. Design reward signals per tier. If cloud GPU becomes available, export environments for actual model RL training.

**Architectural theme**: All entries converge on "context efficiency through structured indirection" — sandbox over prompt, REPL over context, reflection over gradient, retrieval over fullcontext. Validates our multi-model approach over single-model scaling.

## Research Intake Update — 2026-04-14

### New Related Research
- **[intake-363] "LLM-as-a-Verifier"** (github.com/llm-as-a-verifier)
  - Relevance: General-purpose verification framework using logprob-based scoring with criteria decomposition — directly relevant to AP-27 eval tower formalization as an alternative to LLM-as-a-Judge
  - Key technique: R(t,τ) = (1/CK) Σ p_θ(v_g|t,c,τ)·φ(v_g) — multi-criteria, repeated verification, granularity scaling
  - Reported results: Terminal-Bench 2: 86.4% (from 81.8%), SWE-Bench Verified: 77.8% (from 76.1%)
  - Delta from current approach: AP-27 specifies "state matching, not LLM-as-judge" for verification functions. LLM-as-a-Verifier offers a middle ground — uses LLM logprobs but for structured verification rather than open-ended judgment. Gemini API dependency is a blocker for local deployment.
- **[intake-371] "ThinkPRM: Process Reward Models That Think"** (arxiv:2504.16828)
  - Relevance: Generative PRM that verifies solution steps via verification chain-of-thought — applicable to eval tower step-level attribution
  - Key technique: Fine-tunes long-CoT models as verbalized step-wise reward models; achieves PRM800K parity with only 1% of labels
  - Reported results: 8% better OOD on GPQA-Diamond, 4.5% on LiveCodeBench vs discriminative PRMs
  - Delta from current approach: Our T0/T1/T2 tiers are outcome-level. ThinkPRM enables per-step process reward attribution within evaluation, complementing LightningRL (intake-344) per-step credit assignment.
- **[intake-370] "Aletheia: RLVR for Code Verifiers"** (arxiv:2601.12186)
  - Relevance: Systematic ablation of RLVR training recipes across model scales — directly informs AP-27 verification function design
  - Key technique: Scale-dependent optimization recipes — small verifiers need on-policy training; large need negative samples + thinking traces
  - Reported results: Compute-optimal roadmap for practitioner deployment
  - Delta from current approach: Our eval tower targets are fixed tiers. Aletheia shows that the training recipe matters more than architecture at small scales — relevant if we export environments for RL training per intake-320.
- **[intake-368] "SWE-RM: Execution-Free Feedback for SWE Agents"** (arxiv:2512.21919)
  - Relevance: MoE reward model (30B total, 3B active) providing execution-free feedback — relevant to eval tower reward signal design
  - Key technique: MoE architecture with controlled data composition experiments; classification accuracy and calibration critical for RL
  - Reported results: Qwen3-Coder-Flash 51.6%→62.0%, Qwen3-Coder-Max 67.0%→74.6% on SWE-Bench Verified
  - Delta from current approach: SWE-RM shows TTS performance doesn't guarantee RL effectiveness — our eval tower must separately validate classification accuracy and calibration, not just pass rates.

**Synthesis**: The 5 verification research entries above (intake-363/367/368/370/371) are consolidated into a standalone handoff: [eval-tower-verification.md](eval-tower-verification.md). That handoff provides the implementation plan (EV-1–EV-7) for ECE/AUC metrics, ThinkPRM deployment, cross-family verification, and Scoring Verifiers benchmark integration that these papers motivate. AP-27 now points to that handoff as its implementation plan.

### Future AR-3 Signal: Branching Density (2026-04-15 deep-dive)

intake-378 (arxiv:2604.01702) identifies Propose step ratio as a quality metric for reasoning traces. High branching density (>0.30) indicates unproductive exploration — the model is diverging across alternative approaches rather than converging on a solution.

**Relevance to AR-3**: If a config change (PromptForge mutation, StructuralLab flag, NumericSwarm param) causes higher average branching density in solver outputs, that is a negative signal even if accuracy is unchanged — the model is working harder for the same result, increasing cost.

**Lightweight implementation**: Add branching keyword scan to T0/T1 eval output analysis. Report as `METRIC branching_density: X.XX` via existing `to_grep_lines()` mechanism in `safety_gate.py`. The SafetyGate quality floor could incorporate: reject trials where branching density increases without quality gain.

**Priority**: LOW — only relevant when AR-3 experiments touch solver behavior (prompt mutations, model swaps, reasoning budget changes). Cross-ref: `routing-intelligence.md` (Category C quality signal), `research/deep-dives/sft-generalization-reasoning-patterns.md`.

## Research Intake Update — 2026-04-17

### New Related Research

- **[intake-394] "Evolver: GEP-Powered Self-Evolution Engine for AI Agents"** (repo: EvoMap/evolver)
  - Relevance: directly overlaps with the PromptForge species and the autopilot governance/safety layer — Evolver implements a protocol-bound evolution pattern with primitives (Gene/Capsule/EvolutionEvent JSONL assets, protected source files, strategy presets) that mirror what our autopilot safety gates already need.
  - Key technique: GEP (Genome Evolution Protocol) — auditable, protocol-constrained prompt evolution; strategy preset weighting (innovate/optimize/repair intent mix, e.g. 80/15/5 balanced vs 0/20/80 repair-only); log-signal extraction for selector-driven prompt routing; protected-source-files to prevent self-overwrite.
  - Reported results: none (no benchmarks, no empirical claims in README).
  - Delta from current approach: adds an **auditability-first asset schema** (Gene/Capsule/EvolutionEvent) as a reference to compare against our own PromptForge artifact scheme; the protected-source-files pattern is directly adoptable as a safety gate for autopilot mutations. Not adopt_component (Node.js, tied to evomap.ai hub, no benchmarks). Cross-refs intake-327 (GEPA/DSPy), intake-328 (MiniMax self-evolving).

- **[intake-404] "Target Policy Optimization"** (arxiv:2604.06159)
  - Relevance: TPO's core mechanism — construct target distribution `q_i ∝ p_old * exp(score/η)`, fit via cross-entropy — is mathematically the Cross-Entropy Method (CEM). Directly applicable to NumericSwarm as an alternative or augmentation to NSGA-II for the 23-param numeric surface.
  - Key technique: Closed-form target distribution from scored samples + cross-entropy fitting. No policy gradients, no clipping, no critic. Temperature η controls exploration (robust across 0.25-2.0).
  - Reported results: On bandits (closest analog to autopilot trials): TPO converges fastest with lowest misalignment to oracle gradient. Multi-epoch stable where GRPO oscillates destructively.
  - Delta from current approach: NumericSwarm uses NSGA-II (Optuna) with per-surface studies and 4D Pareto scoring. A CEM sampler would: (1) maintain Gaussian N(μ,Σ) per surface, (2) sample K configs, (3) score via eval tower, (4) refit to elite set weighted by scalarized Pareto score (hypervolume contribution). Requires scalarizing the 4D objectives — hypervolume contribution is the natural choice. Full control surface embedding (66+ dims with flags + text mutations) is infeasible due to heterogeneous action space and expensive evaluations. **Concrete integration point**: when `hypervolume_slope() < 0.001` triggers stagnation detection in `pareto_archive.py`, switch from NSGA-II to CEM sampling as the exploration boost mechanism (currently just increases exploration weight). Code reference: `numeric_swarm.py:99` (sampler init), `pareto_archive.py:188-200` (stagnation detection).

## Research Intake Update — 2026-04-18

### New Related Research

- **[intake-412] "DeepPlanning: Benchmarking Long-Horizon Agentic Planning"** (arxiv:2601.18137)
  - Relevance: Benchmark for long-horizon agent planning with verifiable constraints. 26 frontier models evaluated across travel planning (minute-level scheduling, 9 APIs) and shopping planning (15 APIs, coupon timing). Even GPT-5.2-high only achieves 44.6% case accuracy. Rule-based automated scoring aligns with our ch07 benchmark construction philosophy.
  - Key insight for autopilot: Reasoning-equipped models consistently outperform non-reasoning variants. Parallel tool use improves effectiveness-efficiency trade-offs. Error analysis of 140 failed trajectories shows global optimization failures are most prevalent — directly relevant to autopilot's multi-step planning quality assessment.
  - Delta from current approach: Potential benchmark addition for evaluating autopilot planning quality. Layered task generation methodology (solution-centric reverse generation) could inform synthetic eval task construction for AR-3 runs.

## Research Intake Update — 2026-04-20

### New Related Research

- **[intake-413] "Toward Ultra-Long-Horizon Agentic Science: Cognitive Accumulation for ML Engineering"** (arxiv:2601.10402)
  - Relevance: HCC (Hierarchical Cognitive Caching) maps directly to AutoPilot's memory architecture gap — `strategy_store.py` is flat where HCC is L1/L2/L3 tiered. ML-Master 2.0 achieves 56.44% SOTA on MLE-Bench using this approach.
  - Key technique: L1 (execution traces, volatile) → L2 (phase summaries, semi-stable) → L3 (cross-task wisdom, persistent). Promotion operators P1/P2 trigger at phase/task boundaries.
  - **Deep dive**: `research/deep-dives/hcc-cognitive-accumulation-autopilot.md` — maps HCC tiers to `short_term_memory.py` (≈L1), missing L2 consolidation, `strategy_store.py` (≈L3 structurally but flat functionally). Proposes concrete `knowledge_distiller.py` (~300 LoC) for L1→L2→L3 promotion.
  - Delta from current approach: AutoPilot stores individual strategy insights but never distills patterns across trials. HCC provides the missing consolidation/promotion pipeline.

- **[intake-414] "Token Savior Recall — 97% Token Reduction MCP Server"** (repo: mibayy/token-savior)
  - Relevance: Four extractable patterns for `strategy_store.py`: (1) RRF hybrid retrieval (BM25+FAISS), (2) content-hash staleness detection, (3) MDL convention promotion, (4) progressive disclosure.
  - **Deep dive**: `research/deep-dives/token-savior-extractable-patterns.md` — concrete schema changes, Python code sketches, priority ordering (staleness > RRF > disclosure > MDL).
  - Delta from current approach: strategy_store has no staleness detection (stale strategies from changed configs never expire) and pure FAISS retrieval misses exact-term matches.

- **[intake-415] "Context Mode — Context Window Optimization for AI Coding Agents"** (repo: mksglu/context-mode)
  - Relevance: Subprocess sandbox (99% output reduction) and 5KB threshold gating applicable to eval tower output in controller prompt.
  - **Deep dive**: `research/deep-dives/context-mode-tool-compression-patterns.md` — estimated 30-50% context reduction in eval-heavy autopilot sessions.
  - Delta from current approach: eval tower output inflates controller prompt with no budget control; threshold gating + FTS5 indexing would index large outputs and serve relevant excerpts.

### Synthesis Deep Dive

**`research/deep-dives/autopilot-iteration-strategy-synthesis.md`** — 4-phase improvement plan:

| Phase | What | Target | Scope | Status |
|-------|------|--------|-------|--------|
| 1 (AP-28) | Strategy Memory Upgrade | `strategy_store.py` | +FTS5/RRF, staleness detection, Bayesian validity (~200 LoC) | **CODE LANDED 2026-05-08** (`ad25ade`); active on AR-3 restart |
| 2 (AP-29) | Knowledge Distillation Pipeline | new `knowledge_distiller.py` | L1→L2→L3 tier promotion, MDL consolidation (~300 LoC) | **CODE LANDED 2026-05-08** (`4cdc77e`); wiring deferred |
| 3 (AP-30) | Controller Context Budget | `autopilot.py`, `eval_tower.py` | Progressive disclosure, 5KB gating, token budgets (~150 LoC) | **CODE LANDED 2026-05-08** (`2d4d18f`); helpers in `scripts/autopilot/context_budget.py`, wiring deferred |
| 4 (AP-31) | Mutation Knowledge Graph | `prompt_forge.py` | mutation×failure×outcome tracking, informed crossover (~200 LoC) | **CODE LANDED 2026-05-08** (`49b920c`); sidecar at `scripts/autopilot/species/mutation_graph.py`, wiring deferred |

Phase 1 is directly implementable from the synthesis document. Phases 1+2 parallelize with Phase 3.

**Wiring checklist (AP-29/30/31 — apply on next autopilot restart):**

1. AP-29: at the existing 25-trial auto-checkpoint in `autopilot.py`, instantiate `KnowledgeDistiller(strategy_store).distill(trial_counter)` and log the resulting `DistillationStats`.
2. AP-30: replace flat strategy injection in `dispatch_action` (~line 548) with `format_strategies_tiered()`; wrap eval-tower output return through `gate_eval_output()`; pass each section in `build_controller_prompt` through `apply_section_budget()`.
3. AP-31: in `PromptForge.propose_mutation` cycle end, call `MutationGraph().record(MutationOutcome(...))`. In `_build_mutation_prompt` for `crossover`, inject `informed_crossover_candidates(target_file)` as a "preferred sections" hint.

Test coverage as of 2026-05-08: 46 unit tests across the four AP modules (`tests/unit/test_strategy_store.py`, `test_knowledge_distiller.py`, `test_context_budget.py`, `test_mutation_graph.py`) — all passing.

## Research Intake Update — 2026-04-21

### New Related Research
- **[intake-425] "Memory Transfer Learning: How Memories are Transferred Across Domains in Coding Agents"** (arxiv:2604.14004)
  - Relevance: Cross-domain memory pooling from heterogeneous benchmarks improves coding agent performance by 3.7%. The "Insight" abstraction (title + description + generalizable content, no task-specific details) maps directly to strategy_store entry format. Finding that simple embedding retrieval (cosine on text-embedding-3-small) outperforms LLM reranking validates our FAISS-based approach.
  - Key technique: Four memory representations (Trajectory/Workflow/Summary/Insight) with cross-domain pooling; negative transfer taxonomy (domain-mismatched anchoring, false validation confidence, misapplied best-practice transfer).
  - Reported results: +3.7% average across 6 benchmarks; MTL (431 memories) outperforms AgentKB (5,899 memories) by +1.7%.
  - Delta from current approach: The negative transfer taxonomy is directly actionable for PromptForge mutation safety gates. The finding that task-agnostic insights outperform task-specific insights (+1.1%) suggests strategy_store should favor abstract patterns over concrete implementation traces. Caveat: "Memory Transplants" (ICLR 2026 Workshop) finds architecture transfer is system-dependent and weaker solvers benefit most — the 3.7% gain may not hold for stronger models.

## Research Intake Update — 2026-04-22

### New Related Research

- **[intake-438] "Mind DeepResearch Technical Report"** (arxiv:2604.14518, Li Auto)
  - Relevance: Production multi-agent framework (Planning + DeepSearch + Report) with four-stage training (SFT cold-start + Search-RL + Report-RL + preference alignment). Architecture parallels EPYC's Tier A/B/C role-specialization.
  - Key technique: Agent role specialization via SFT, RL specialization per agent role, multi-dimensional rubric evaluation.
  - Reported results: BrowseComp-ZH 45.7%, WideSearch 46.5%, SOTA 51.8 on MindDR Bench at ~30B scale.
  - Delta from current approach: Our AR-3 explores prompt/structural mutations at the autopilot layer. MindDR explores the agent-role training layer (RL specialization). The two are orthogonal and complementary — RL agent specialization is a longer-term path we haven't opened. Tier 2b contradicting-evidence not run.

- **[intake-441] "Where does output diversity collapse in post-training?"** (arxiv:2604.16027)
  - Relevance: PromptForge mutation diversity depends on base-model output diversity. Paper shows post-training (SFT especially) systematically narrows output distribution — inference-time prompting can't recover training-time diversity loss. This constrains how much diversity PromptForge mutations can realistically generate.
  - Key finding: Diversity loss decomposes into quality-control and residual/genuine-narrowing components; task-dependent.
  - Delta: Factor diversity-collapse awareness into model-selection decisions. When evaluating new post-trained checkpoints for autopilot (e.g., next architect swap), add a diversity metric alongside accuracy.

- **[intake-444] "Agent-World: Scaling Real-World Environment Synthesis for Evolving General Agent Intelligence"** (arxiv:2604.18292)
  - Relevance: Autonomous environment + task discovery with controllable difficulty. Addresses capability-gap identification challenge that parallels autopilot's goal of finding useful mutations.
  - Key technique: Agentic Environment-Task Discovery + Continuous Self-Evolving Agent Training + Multi-env RL + dynamic task synthesis + MCP integration.
  - Reported results: Agent-World-8B/14B beat proprietary baselines across 23 agent benchmarks; scaling correlates with environment diversity.
  - Delta: Environment synthesis as a scaling lever is a different axis from our AR-3 prompt/structural mutation space. Could inform future extensions (e.g., AR-4 that synthesizes new benchmark tasks rather than optimizing against a fixed suite). Tier 2b not run on beat-proprietary claim.

## Deep-Dive Integration — 2026-04-22

### P16 — Strategy Memory Safety Gates (intake-425 + DD4)

Tracked in `routing-and-optimization-index.md` P16. Three adoptable patterns:

- **AP-32: Insight format audit** — adopt `(title, description, generalized_content)` format with no task-specific implementation details for new strategy_store entries. Audit existing entries for over-specificity. ~50 LoC in `strategy_store.py`. Converges with AP-28 (strategy memory upgrade, FTS5+RRF).
- **AP-33: Negative-transfer safety gates** for PromptForge — 3 mutation safety checks (domain-mismatched anchoring detector; false validation confidence flag when mutation success is based on <5 trials; misapplied best-practice filter rejecting mutations that generalize suite-specific patterns). ~100 LoC in `prompt_forge.py`.
- **AP-34: Validate N=3 embedding retrieval** — confirm FAISS top-3 cosine matches or exceeds LLM reranking. Paper shows embedding similarity (0.630 avg) > LLM reranking (0.598) > adaptive rewriting (0.608). Zero code — configuration experiment on next AR-3.

### Environment Synthesis Species → dedicated handoff

Agent-World (DD6, intake-444) env-synth is now a 5th autopilot species, tracked in a dedicated handoff: [`agent-world-env-synthesis.md`](agent-world-env-synthesis.md). Phase 1 training-free and CPU-feasible today (AW-1 `env_synth/` module scaffold is the entry point). Phase 2 multi-env GRPO GPU-gated. Journal-event format (`EnvSynthAction` with `environment_id`/`tool_set`/`synthesized_tasks` fields) will follow AP-3 journal conventions.

### PromptForge diversity-coverage term (DD4-A7)

**Problem**: intake-441 shows post-training diversity loss is structural (in weights). Our mutation search can exhaust "diverse-looking but weight-constrained" space quickly.

**Fix**: add a diversity-coverage term to PromptForge's mutation scoring: penalize mutations that fall into FAISS-dense regions of the mutation embedding space. ~2h once the DD4 diversity baseline lands (NIB2-42 — inference-gated; EV-8 metric fns already landed 2026-04-22).

- [ ] **AP-35**: Implement `diversity_coverage_penalty()` in `scripts/autopilot/species/prompt_forge.py` (⚠ path moved from `prompt_forge.py` in the `species/` refactor — verified 2026-06-04). Use existing FAISS index of strategy_store embeddings (live usage in `species/evolution_manager.py` / `species/structural_lab.py` / `actions.py`). Penalty = -log(density) at the mutation's embedding location.
- [ ] **AP-36**: Wire into the mutation-scoring path. ⚠ **Stale (2026-06-04)**: `_score_mutation()` no longer exists — mutation scoring was refactored into the `species/` evolution framework; re-identify the current scoring site (`species/evolution_manager.py` / `structural_lab.py`) before wiring.

> **EV-8 gate status (2026-06-04 review)**: AP-35/36/37 are gated on EV-8's **inference baseline**, not the whole of EV-8. EV-8's metric functions + `EvalResult` fields already **landed 2026-04-22** (`src/tools/diversity/metrics.py`, `src/safety_gate.py`); what remains is the 1-day diversity baseline run (NIB2-42, inference-gated) the `-log(density)` penalty calibrates against, plus the `to_grep_lines()` wiring.

### GEPA rebalance trigger (DD4-A8)

**Problem**: if mutation diversity stalls (distinct-2 on generated mutations drops below baseline for N trials), species-budget rebalance should trigger before quality regresses.

**Fix**: extend MetaOptimizer with a diversity-stall signal. ~1-2h.

- [ ] **AP-37**: Add `distinct2_history` to MetaOptimizer state. Trigger rebalance when `distinct2_t / distinct2_baseline < 0.8` for 10 consecutive trials. **Amended 2026-04-22 post Tier 2b**: couple with `semantic_embedding_agreement` to avoid rebalancing on surface-level distinct-2 drops that don't reflect real diversity collapse (arXiv 2506.00514 metric-gaming critique). Rebalance trigger: distinct-2 drops AND semantic agreement drops AND Verbalized Sampling recovery probe fails to close >50% of the gap. Depends on EV-8's inference baseline (metric functions already landed 2026-04-22 — see EV-8 gate status note above).

### Cross-references

- `routing-and-optimization-index.md` P14/P16/P17/P18
- `eval-tower-verification.md` EV-8 (diversity metrics — required prerequisite for AP-35; metric fns landed 2026-04-22, inference baseline pending)
- `agent-world-env-synthesis.md` (full env-synth plan)
- `/workspace/research/deep-dives/diversity-collapse-posttraining.md`
- `/workspace/research/deep-dives/agent-world-environment-synthesis.md`

## Research Intake Update — 2026-04-24

### New Related Research

- **[intake-451] "Meta-Harness (official reference code)"** (`github.com/stanford-iris-lab/meta-harness`)
  - Relevance: official companion code for intake-244 (the Meta-Harness paper this handoff's meta-controller echoes). ONBOARDING.md + `domain_spec.md` template is a direct analogue of autopilot's role-spec scaffolding.
  - Key technique: agent-tasks scaffold evolution on terminal_bench_2 — the closest open-source analog to autopilot's code-mutation search space. `claude_wrapper.py` proposer-logging pattern fits PromptForge's audit trail.
  - Delta: cherry-pick ONBOARDING/domain-spec pattern for autopilot's new-role onboarding. Read terminal_bench_2 before any Tier-2b code-mutation upgrade. Do not wholesale port — repo is explicitly "cleaned up version of paper code, not tested beyond running."

## Research Intake Update — 2026-04-26

### New Related Research

- **[intake-474] "TRINITY: An Evolved LLM Coordinator"** (arxiv:2512.04695, ICLR 2026, Sakana AI)
  - Relevance to autopilot: Trinity is the *outer-coordinator analogue* — a learned head that picks per-turn `(LLM, role)` from a heterogeneous pool, replacing what we currently do with Claude in the autopilot loop. The user observation flagged in the deep-dive: our outer Claude-driven layer is the closer Trinity match than our inner inference pool, since Claude vs cheap-frontdoor vs specialist-coder is a wider quality gradient than the all-open inner pool.
  - Key technique: Qwen3-0.6B + 10K-parameter linear head, trained with sep-CMA-ES against terminal binary task reward. Multi-turn protocol: full transcript passed each turn, Verifier-acceptance termination at K≤5.
  - Reported results: 21.9% mean relative-error reduction over the 2nd-best multi-agent baseline across LiveCodeBench / Math500 / MMLU / RLPR. The numbers are *heterogeneous-pool-specific* — discount appropriately for our setup.
  - Delta from current autopilot: autopilot accumulates Q-values over many trials and feeds back into routing decisions. Trinity replaces the per-turn coordination decision itself with a learned head trained against task fitness. **A scoping handoff** [`outer-coordinator-learned-head.md`](outer-coordinator-learned-head.md) **was created 2026-04-26 to evaluate whether replacing part of this loop is worthwhile.** Phase OC-0 (scoping document) gates everything; OC-0.1 explicitly requires reading this handoff and `scripts/autopilot/` to inventory the per-turn decisions Claude makes today.
  - **Action when OC-0 starts**: ensure the autopilot decision inventory (OC-0.1) is exhaustive — missing decisions in the inventory will undersell or oversell the cost-benefit estimate (OC-0.4).
  - Deep-dive: [`research/deep-dives/trinity-evolved-llm-coordinator-methodology.md`](../../research/deep-dives/trinity-evolved-llm-coordinator-methodology.md), especially section 2.3 ("pool-homogeneity caveat … where does Claude fit?").

## Research Intake Update — 2026-04-27

### New Related Research

- **[intake-479] "Co-Evolving LLM Decision and Skill Bank Agents for Long-Horizon Tasks (COSPLAY)"** (arxiv:2604.20987)
  - Relevance: directly parallels the closed-loop optimization motif here — a learnable skill bank co-evolved with the decision agent, with skills extracted, refined, and updated continuously from unlabeled rollouts. Adjacent to the completed `skillbank-distillation` handoff (recursive evolution + confidence scoring) and to intake-261 (Skill0 / SkillRL).
  - Key techniques: (1) **skill contracts** — schema upgrade for skill-bank entries that bind preconditions/postconditions to each skill, enabling consistent retrieval and reuse; (2) **closed-loop refinement from unlabeled rollouts** — skill discovery pipeline that mines rollouts for new skills and updates contracts based on reward delta, not requiring labeled trajectories.
  - Reported results: 8B base LLM with COSPLAY beats four frontier LLM baselines on single-player game benchmarks (+25.1% avg reward); evaluated across six game environments; competitive on multi-player social reasoning games.
  - Delta from current approach: autopilot already has the closed-loop scaffold (Pareto frontier + checkpointed `autopilot_state.json`). Two adoptable patterns: (a) **skill contracts** as a schema upgrade for any future skill-evolution path (formalize pre/postconditions instead of free-text), and (b) **reward-delta-driven refinement** from unlabeled production traces as a lighter alternative to manually authored eval suites — useful if AP-35 expands toward online optimization with implicit signals. Verdict: `adopt_patterns`, not full framework adoption.

## Research Intake Update — 2026-04-28

### New Related Research

- **[intake-498] "Agentic World Modeling: Foundations, Capabilities, Laws, and Beyond"** (arxiv:2604.22748, Chu et al., 42 authors)
  - **Deep-dive**: [`research/deep-dives/agentic-world-modeling-levels-laws-taxonomy.md`](../../research/deep-dives/agentic-world-modeling-levels-laws-taxonomy.md) — comprehensive read with EPYC-stack mapping.
  - Relevance: HIGH (bumped from medium after deep-dive). Survey introduces a "Levels × Laws" taxonomy: capability levels L1 Predictor / L2 Simulator / **L3 Evolver** × four governing-law regimes physical/digital/social/scientific. Autopilot as currently architected is a textbook **L3-Evolver / Digital-laws** instance — the species loop autonomously revises its own model (routing/prompts/structure) based on AR-3 evaluation evidence under software-contract constraints.
  - **L3 governance recipe (Section 5.4) maps line-for-line onto autopilot SafetyGate**: regression gate ↔ quality floor; robustness gate ↔ per-suite guard; rollback policy ↔ Pareto-archive replacement; canary policy ↔ T0/T1/T2 tiered eval tower. Vocabulary alignment is essentially free.
  - **Four evaluation principles (Section 6.1) testable in existing AR-3 today** — long-horizon coherence, intervention sensitivity, constraint consistency, closed-loop use. Adoption cost is rubric documentation + per-cycle reporting; value is identifying intervention-sensitivity gaps in the species framework (e.g., disabling species 0/1/2/3 individually should produce predictable Pareto-front shifts).
  - Adoption plan (CPU-feasible, do now): (1) document L3-Evolver / Digital-regime framing in this handoff's Architecture section, (2) extend AR-3 reporting to label scores by the four principles, (3) verify autopilot SafetyGate implements all four governance prescriptions with explicit reporting; identified gap: SafetyGate uses Pareto-front replacement rather than explicit rollback semantics — worth a one-pager on whether these are equivalent.
  - **Beyond-L3 framing for Species 3 (StructuralLab)**: paper Section 8.2 introduces "governing laws themselves become learnable" as an open direction. StructuralLab modifying flags + routing model lifecycle is the closest EPYC instance, but **do not over-claim** (per closure-inflation feedback memory). We have one species hooking the operating rules of the others, not a principled meta-learning loop. Honest framing only.
  - Cross-cutting: also relevant to `agent-world-env-synthesis.md` (L2-Simulator → L3-Evolver bridge) and `meta-harness-optimization.md` (Tier 3 = another L3-Evolver / Digital instance); the three handoffs should share the four-principle evaluation rubric.
  - MREP (Minimal Reproducible Evaluation Package, Section E.6) is **proposed but not released**. Set watch on matrix-agent/awesome-agentic-world-modeling and arxiv:2604.22748 for shipment; if released, run autopilot through it as external sanity check.
  - Verdict: `adopt_patterns` (vocabulary + four-principle rubric + governance completeness check), NOT full framework adoption.

## Research Intake Update — 2026-04-30

### New Related Research

- **[intake-517] "HALO — Hierarchical Agent Loop Optimizer"** (`github.com/context-labs/halo`, MIT, by inference.net / Context Labs) and **[intake-518] halo-engine PyPI** (pip-installable wrapper, MIT, v0.1.2 released 2026-04-29)
  - Relevance: **HIGH**. Verdict: `adopt_patterns`. HALO is the closest external analogue to autopilot's closed-loop trace → analysis → harness-mutation → re-evaluate cycle. Reported deltas on AppWorld test_normal SGC: Sonnet 4.6 62.5% → 73.2% (+10.7 pts), Gemini 3 Flash 37.5% → 48.2% (+10.7 pts). Findings independently verified against source traces. Built on the foundational RLM paper Zhang/Kraska/Khattab arxiv:2512.24601 (already in our index as **intake-153**).
  - Three concrete patterns worth lifting into autopilot (NOT framework adoption):
    1. **General-harness-overfits-single-trace observation as a design constraint** — argues against using a generic Claude-Code-style coding agent for trace analysis at scale; favors a specialized analyzer (RLM-style, or our own custom).
    2. **dev/test_normal split discipline** — explicit unseen split is a stronger overfitting guard than autopilot's Pareto-archive replacement alone. Cross-ref `feedback_checkpoint_pareto_state.md`.
    3. **Concrete failure-mode taxonomy** (hallucinated tool calls, redundant args, refusal loops, semantic correctness) as **seed labels** for autopilot's trace-clustering pass.
  - Tier 2b contradicting evidence (from RLM literature, applies transitively): production deployment of RLM-based loops faces latency spikes, cost variance, "format collapse"; many OSS RLM implementations pin max_depth=1; recursive-depth claim harder to operationalize than paper implies. Apply skeptically when sizing the analysis-loop budget.
  - Cross-ref intake-153 (RLM foundational paper) — already in index, already verdict `already_integrated` with ~80% pattern coverage. HALO is an applied implementation of those patterns, not a new technique.
  - Action: when an AP-35-class species iteration considers a "trace analyzer" role, evaluate the halo-engine package as a reference implementation (MIT, 2.5 MB, single CLI). Defer adopt_component until a small spike confirms report quality on EPYC orchestrator traces, not just AppWorld.

#### Deep-dive refinement (2026-04-30) — concrete spike scoped, see halo-trace-loop-spike

Deep-dive at [`/workspace/research/deep-dives/halo-rlm-trace-loop-integration.md`](../../research/deep-dives/halo-rlm-trace-loop-integration.md). Spike handoff at [`halo-trace-loop-spike.md`](halo-trace-loop-spike.md) — ready to claim.

The 1-day spike has a 4-criterion go/no-go gate at end of Day 1 PM. Conditional Day 2 lifts patterns into existing scoped work; **no halo-engine vendoring**. Patterns that affect autopilot specifically:

- **dev/test_normal split discipline** as an anti-overfitting guard for the Pareto frontier — explicit unseen-split is stronger than Pareto-archive replacement alone (per `feedback_checkpoint_pareto_state.md`).
- **Failure-mode taxonomy seed labels** (hallucinated tool calls, redundant args, refusal loops, semantic correctness) for autopilot's trace-clustering pass.

Most autopilot infrastructure that HALO would build is already done: `telemetry.py:to_otlp_span` (OTLP emission since 2026-04-12), trace-driven mutator (Tier-1 done), code-mutation search (Tier-2 done), GEPA evolution (intake-345 done), RLM REPL recursion (intake-153 R1-R6 done at ~80% pattern coverage). The spike specifically tests whether HALO's *analyzer* surface produces actionable findings against our autopilot trial telemetry — it is NOT a wholesale autopilot rewrite.

---

## Session 2026-05-16 — Recovery + host-health integration + journal purge

### Trigger

Autopilot was running 8.5h producing garbage data. Quality had collapsed from the April plateau (1.14 avg) to 0.6-0.9 today. User asked "Can we review the autopilot's progress?"

### Root-cause chain (verified)

1. **gemma4 worker_general spinning 95 cores idle.** Yesterday's `OMP_WAIT_POLICY=passive` fix had silently broken MTP first-decode coordination (`llama_decode ret=-3`, server hangs forever on first request). Reverting passive → active brought MTP back but then the libomp team busy-loops between requests.
2. **architect_general crashed.** GGML_ASSERT in `common_speculative_state_tree::draft` — Qwen3.5-122B's M-RoPE refuses position rollback when speculative draft tokens are rejected. Persistent across np=1/np=2 attempts. Mitigated by setting `_NO_SPEC_DECODE = {"architect_general"}` in orchestrator launcher — disables -md flag for architect, retains moe_expert_reduction.
3. **Half the stack down.** Ports 8080/8081/8083/8084 had no listening processes; seeder's `model_registry.yaml` `port:` fields pointed at those quarter-mode ports while launcher used full-mode 8070/8071/8072. Seeder `[INFRA_SKIP] worker_general` resulted from this mismatch, not from gemma4 actually being unreachable.
4. **Duplicate Qwen3.6-35B Q8 server.** frontdoor (8070) + coder_escalation (8071) running TWO copies of same GGUF — 72 GB duplicate mlock + 2× competing 96-thread OMP teams. Removed in `ROLE_LAUNCH_META`: coder_escalation aliased onto frontdoor's server via `shared_with_first_n`. **+69% frontdoor throughput** from removing the contention.
5. **Registry cross-section conflict.** `architect_general` had `acceleration` in BOTH `server_mode.X` and `roles.X` with **different `type:` values** (`moe_expert_reduction` vs `speculative_decoding`). RegistryLoader silently picked one; my edits to the other no-op'd, costing ~2h of debugging time.

### Fixes landed in code

| Fix | File | Verified |
|---|---|---|
| `KMP_BLOCKTIME=10` for binary_override roles (gemma4 MTP) | `orchestrator_stack.py:1944` (worker_pool branch) | gemma4 idle cores 95.05 → 0.00; threads sleep on `futex_wait_queue`; frontdoor +78% / coder +207% / ingest +177% throughput |
| `_NO_SPEC_DECODE = {"architect_general"}` gate | `orchestrator_stack.py:1659` | architect serves cleanly at 12.5 t/s (was crashing) |
| `_renice_all_threads(pid, 19)` per-thread renice helper | `orchestrator_stack.py:1251` | all 289 gemma4 threads at nice=19 on fresh launch (CLI `renice -p PID` only does lead thread) |
| Same-GGUF consolidation: `frontdoor.shared_with_first_n = [coder_escalation, worker_summarize]` | `orchestrator_stack.py:371-388` | 36 GB freed; one OMP team |
| `load_state()` drops non-ProcessInfo stubs | `orchestrator_stack.py:820-832` | `status` / `stop --all` no longer crash on dict entries |
| Registry validator on `cmd_start` | `src/registry/registry_validator.py` (new) | strict-load + cross-section + same-GGUF-same-port checks; catches the architect dup |
| Registry compile from master (opt-in `--compile-registry`) | `src/registry/registry_compiler.py` (new) | SHA-256 cache key; transitive draft/alias dep resolution; produces 10-role lean view |
| Host-health auto-remediation | `scripts/autopilot/host_health.py` (new) + `safety_gate.py` (wire-in) | Throttle / freq / page-cache detection; auto-runs `sudo /usr/local/sbin/autopilot-flush-cache` before attributing throughput violation to config |
| Master registry `architect_general` reconciliation | `epyc-inference-research/orchestration/model_registry.yaml:559+` / `:1170+` | `roles.X.acceleration` no longer references swapped-out Qwen3-235B-A22B |
| **AP-38 (2026-05-23): constrained-creativity planner** — stagnation-gated rich-prompt fragment (gated on `hv_slope_10 < eps` OR `trustworthy < 5` OR 3-trial action-type streak); tail samples promoted from candidates to seeds; 6-axis rubric collapsed to 3 orthogonal axes (info_gain / coherence / cost-adjusted usefulness); fusion preference + quote-don't-regenerate anti-drift rule; `JournalEntry` gets `falsifier` + `rubric_scores` fields via `autopilot_rationale` sidecar block; new `ExperimentJournal.unfalsified_hypotheses()` helper surfaces still-open claims to next planner pass | `scripts/autopilot/{autopilot.py, controller_io.py, experiment_journal.py, program.md}` + `tests/unit/{test_autopilot_controller_io.py, test_autopilot_creativity.py}` | **67/67 autopilot unit tests passing**. End-to-end LLM smoke ran 2026-05-24 (`/workspace/tmp/smoke_rationale.py` + saved response): action + rationale both parse, rubric carries all 3 axes + synthesis_note, Claude noticed the open falsifiers were resolved and chose `distill_knowledge` instead of another seed. Deep-dive: [`research/deep-dives/2026-05-23-creativity-constrained-tail-search.md`](../../research/deep-dives/2026-05-23-creativity-constrained-tail-search.md) (HTML companion in same directory) |
| **AP-39 (2026-05-24): pull-forward of AP-38 deferred items** — `STAGNATION_HV_EPS` now auto-calibrates from `ParetoArchive.hv_slope_noise_floor()` (k × rolling std, clipped to `[1e-6, 1e-3]` so only ever tightens; on live state with 211 hv entries calibrated to 1.0e-5). `JournalEntry.stagnation_signal: str` records which gate signal fired per trial (empty for lean trials); new `ExperimentJournal.action_diversity_by_gate(window)` returns per-bucket Shannon entropy + distinct-action-type counts so the lean-vs-rich diversity comparison surfaces naturally as the next autopilot run accumulates trials — no separate experiment needed | `scripts/autopilot/{autopilot.py, experiment_journal.py, pareto_archive.py}` + `tests/unit/test_autopilot_creativity.py` (+4) | **67/67 autopilot unit tests passing**. Closes AP-38's "end-to-end smoke", "behavioral check ≥20 trials", "calibrate STAGNATION_HV_EPS" deferred items |
| **AP-40 / OS-1 (2026-05-24): launcher per-instance thread count + role-quartering audit + autopilot pause-around-flush** — Two coupled fixes prompted by the frontdoor throughput investigation. **(1)** `build_server_command()` was called without `numa_instance`; `_resolve_thread_count` always returned `instances[0][2]` so every frontdoor quarter got `-t 96` instead of `-t 48` (the workaround in `_build_worker_explore_command` lines 336-343 was the only role that handled this correctly). Fix threads `numa_instance` through to all callers; workaround removed. **(2)** Phase 0.5 quarter-fit benches showed `ingest_long_context` (12.3 t/s/quarter), `vision_escalation` (20.1 t/s/quarter, best of any role), `worker_vision` (11.4 t/s/quarter) all qualify for the full+4×quarter ConcurrencyAwareBackend pattern that frontdoor + worker_general use today. Added quarter entries to NUMA_CONFIG for these 3 roles + wired their URLs in `src/config/models.py` with the `full:` prefix. Also migrated frontdoor's full instance from NUMA_NODE0 (NPS2-era half-socket leftover) to NUMA_FULL + `numactl --interleave=all` for consistency with worker_general/architect_general. **(3)** Discovered + fixed cached-state pause bug: `autopilot.py pause` was a no-op on running autopilots because `state` was loaded once at `autopilot.py:701` and `save_state(state)` after each trial clobbered any externally-set True. Fix reloads `paused`/`_in_cache_flush` from disk at the top of every iteration. **(4)** New `host_health.flush_cache_with_pause()` does pause → flush → NUMA-interleave-rewarm all role GGUFs serially → restore paused state. Wired into `safety_gate._hh_remediate()` and the new operator-facing wrapper `flush_cache_safely.py`. New `DeficiencyCategory.EXOGENOUS_CACHE_FLUSH` so trials completing during a flush window get journal-quarantined like AP-39's EXOGENOUS_RELOAD. | `scripts/server/{orchestrator_stack.py, stack_numa.py}` + `scripts/autopilot/{autopilot.py, experiment_journal.py, host_health.py, safety_gate.py, program.md}` + new `scripts/autopilot/flush_cache_safely.py` + `src/config/models.py` + new tests in `tests/unit/{test_orchestrator_stack_threads.py, test_host_health_pause_around_flush.py}` | **80/80 autopilot+launcher unit tests passing**. Phase 0 benches at `/workspace/tmp/phase0_bench_results.txt` showed the launcher fix will NOT recover frontdoor's regression (today's 10 t/s ≈ achievable ceiling on contended stack — Q8 35B's BW-bound under current concurrent load; the per-instance fix is correctness, not throughput). Stack restart deferred to operator. Phase 0 finding worth flagging: NPS4 single-quarter pattern that worked beautifully on 30B Q4 (46.6 t/s) does NOT transfer to 35B Q8 (8.9 t/s) — Q8 needs more BW than one quarter provides. So frontdoor's quartering at -t 48 gives slightly LOWER per-quarter than the old -t 96; the topology stays for concurrent-serving capacity but per-quarter solo perf is now correct-but-modest. |
| **AP-41 (2026-05-28): dual-provider draft/critique planner** — planner invocation is now provider-coordinated: Claude remains the default drafter, Codex can serve as fallback drafter and secondary critic, provider failures trip a circuit breaker, and the executor still receives one canonical `autopilot_actions` block. Default mode is conservative `shadow_critique`: fallback is active, but critic revisions are logged rather than applied. Active critic reconciliation requires `AUTOPILOT_PLANNER_MODE=draft_critique`. | `scripts/autopilot/{autopilot.py, planner_providers.py, planner_coordinator.py}` + `tests/unit/{test_autopilot_planner_providers.py,test_autopilot_planner_coordinator.py}` | **52/52 focused tests passing**: controller IO, provider parsing, coordinator fallback/critique/circuit tests, recovery, and GEPA import coverage. `gitnexus impact invoke_controller --direction upstream --repo epyc-orchestrator --include-tests`: LOW, confined to Autopilot loop. README/wiki wrap-up note: wiki compile saw unrelated parallel handoff edits, so AP-41 is documented here and in progress only; no broad wiki synthesis was committed from this session. |
| **AP-42 (2026-05-31): controller relaunch safety closure** — Closing fixes for running J6 in controller mode instead of seeder-only mode. Codex critic stdin handoff repaired; active `draft_critique` no longer approves parse/invoke failures; `_ACTION_SCHEMAS` covers all 14 controller actions so prompt/critic/executor field drift is rejected at the universal gate; `slot_compact` prompt/schema/handler agreement restored; mutation dirty-target fence blocks writes and forge commits when the exact target file/path already has pending shared-clone work. | `scripts/autopilot/{planner_coordinator.py,planner_providers.py,controller_io.py,autopilot.py,actions.py}` + `tests/unit/{test_autopilot_planner_coordinator.py,test_autopilot_controller_io.py,test_autopilot_actions_dirty_fence.py}` | Commits: `d5c3a2f` pushed; `af84514` and `e58a79c` local-only ready to push. **145/145 focused autopilot tests passing**, `py_compile` ok, `git diff --check` ok. Live relaunch was attempted after hardening: WAL recovery journaled killed trials 188/189; trial 190 produced a real Codex critique (`revise`, confidence 0.89) and dispatched `rollback`. Current wrap-up state: no autopilot process running, `in_flight_trial=190` still present, journal max `189`, `consecutive_failures=0`; restart/recovery is pending before J6 can continue. |
| **AP-43 (2026-05-31): baseline/frontier/distillation contamination closure** — Closed the full re-contamination chain after the relaunch audit. `Baseline.save()` path leak fixed by `a231556`; `89e6c9f` adds load-path archive-max and archive-first baseline promotion; `ec9622d` excludes Tier-0 fast-reject trials from Pareto frontier/hypervolume/archive-max while retaining them in `all_entries`; `20ea4d5` scrubs legacy-scale failure text in `EvolutionManager.distill()` input and output. Live cleanup scrubbed journal JSONL/TSV + AP-22 memory, purged six `source_trial_id>=180` strategies, and rebuilt DB/FAISS/id_map to 241 with 0 legacy `9.900/-6.900` hits. | `scripts/autopilot/{safety_gate.py,pareto_archive.py,species/evolution_manager.py}` + `tests/unit/{test_safety_gate_baseline_eligibility.py,test_baseline_scale_guard.py,test_pareto_archive_tiers.py,test_evolution_manager_scrub.py}` + runtime backup `orchestration/legacy_scale_cleanup_backup_20260531_122902/` | Tests: 46 archive/safety/recovery, 23 actions/creativity, and 31 distill/scrub/safety checks passed. Autopilot is stopped after cleanup. Next restart should begin at trial 569 against baseline `quality: 1.16`, with the archive target anchored to T1 best quality ~1.895 instead of saturated T0 `2.400`. |
| **AP-44 (2026-05-31): planner-context stale telemetry closure** — Closed the third leak: in-scale stale planner reasoning (`q=2.400`, `2.900`) in recent journal summaries and trials 180–183 could still bias draft planning even after archive/frontier/distill fixes. `summary_text()` now downclasses T0 as audit-only and hides all bug-corrupted metrics/reasons; progress plots use the same T1/T2 + trustworthy filters. Trials 180–183 were tagged `bug_corrupted_by=ec9622d`; HV history was backfilled from T1/T2 archive entries only; docs plots refreshed. | `scripts/autopilot/{experiment_journal.py,progress_plots.py}` + `tests/unit/{test_journal_prompt_sanitization.py,test_progress_plots_filters.py}` + `docs/autopilot/*.png` | Commit `ebd5647` passed 47 focused autopilot tests, `py_compile`, and `git diff --check`. A restart probe ran trial 184 to T1 q=1.816 and marked it `mad_noise`; unrelated autopilot tool-policy mutation `d50b77c` was reverted by `12d6afb` after existing `test_tool_policy.py` rejected it. No autopilot process is running. Current state: `trial_counter=185`, `in_flight_trial=None`, `consecutive_meta_actions=0`. |
| **AP-45 (2026-05-31): learning-excluded keep-signal closure** — Closed the planner-context poison that caused the trial-188 meta-loop halt: `mad_noise` trials already skipped archive/AP-22 learning, but the journal still stored self-criticism as `keep` with “continue exploring this surface,” which the planner interpreted as evidence while also seeing no trustworthy progress. Learning-excluded trials now get explicit `SelfCriticism(... keep_or_revert="excluded" ...)` before journaling, with controller-facing text saying not to treat the outcome as a keep/config-efficacy signal. | `scripts/autopilot/{autopilot.py,self_criticism.py,experiment_journal.py}` + `tests/unit/test_classify_learning_exclusion.py` | GitNexus impact LOW for `classify_learning_exclusion`, `_run_loop_inner`, `JournalEntry`, and `ExperimentJournal.summary_text`. Validation: 21 focused learning-exclusion/journal/MAD tests passed; 89 broader autopilot unit tests passed; `py_compile` and `git diff --check` passed. Autopilot remains down pending operator restart decision. |
| **AP-46 (2026-05-31): historical poison-state prune** — Closed the forward-only gap left by AP-45. Existing rows 184/186/187 and the meta/distill strategy rows already written before the code fix were removed from the active runtime state so the next planner prompt cannot cite them as evidence. | Runtime state only: `orchestration/autopilot_journal.{jsonl,tsv}`, `orchestration/autopilot_state.json`, `scripts/autopilot/short_term_memory.md`, `orchestration/repl_memory/strategies/*`, and local tags `autopilot/trial-{184,186,187}`. Backups: `/mnt/raid0/llm/tmp/autopilot-prune-20260531-205634/`. | Verified active journal has no trial IDs 184/186/187 and no `bug_corrupted_by=mad_noise`; `ExperimentJournal.trustworthiness_score()` reports only `autopilot_killed_mid_trial:17` and `ec9622d:4`; strategy SQLite/FTS/FAISS/id-map all count 241 with no active `#184`/`#186`/`#187`, `mad_noise`, or “continue exploring this surface” hits; state is `paused=true`, `trial_counter=188`, `consecutive_meta_actions=0`, no dispatch/halt latch. No inference or live trial was run. |

### Journal data purged

Polluted trials 314-322 (today's run) removed from `autopilot_journal.tsv` + `.jsonl`. Backups at `orchestration/autopilot_journal.{tsv,jsonl}.bak-20260509-094821`. Pareto archive in `autopilot_state.json` did not contain those trials (state.json wasn't updated mid-trial). Trial counter at 323; next trial keeps that ID (no gap-renumbering).

### Frontdoor throughput investigation — open

User noted bench CSVs (`epyc-inference-research/benchmarks/results/reviews/qwen36_q8_0_baseline.csv`) show 25-30 t/s per-question for Qwen3.6-35B Q8, while current measurement is 12.5 t/s.

git bisect across 62 llama.cpp commits between April 24 (`e734a682`) and May 2 (`2ffbdbbba`) identified the first-bad commit as **`2ffbdbbba` — "fix: gate TIDE dynamic early exit"**. The pre-fix binary silently dropped ~12.5% of layers for ALL models via TIDE, producing **+30% throughput AT THE COST OF corrupted output**. Reproduced verbatim: `--n-layer-exit 5..56` on current binary, real bench prompt → output emits `TargetExceptionTargetException`, `TemplateName`, mixed CJK garbage (matching the commit message's description). **TIDE was the inflated bench number; your fix was correct.**

But: even with the April 20 binary (pre-TIDE entirely, head `81df3f7c`), bench recipe in TOTAL isolation (all other servers killed, fresh `drop_caches`, 1068 GB mem free) only delivers **12.13-12.48 t/s**, not 26. CPU boost is correct (3.9 GHz all-core, 4.5 GHz single-core peak). The 26 t/s bench-era number is currently unreproducible. Most likely cause per `feedback_host_throttle_check`: sustained multi-day uptime (6d 18h) with cumulative throttle that `drop_caches` no longer fully restores.

**Next test (operator action)**: reboot, then re-run bench-recipe in isolation. If 25 t/s recovers, host-state hypothesis confirmed and no code action needed. If still 12.5, the binary or model file state has genuinely changed since April 20 and needs deeper investigation.

### Autopilot relaunch readiness

- Runtime poison state cleared: active journal rows 184/186/187 removed; AP-22 short-term memory refs removed; 65 contaminated strategy rows pruned; strategy SQLite/FTS/FAISS/id-map aligned at 241.
- State is restart-order-independent: `paused=true`, `trial_counter=188`, `consecutive_meta_actions=0`, no `_dispatch_deficiency`, no `_meta_halt_reason`.
- Local dangling tags `autopilot/trial-184`, `autopilot/trial-186`, and `autopilot/trial-187` deleted.
- Autopilot remains down/paused. No inference or live trial was run during cleanup.

**Awaiting operator decision on credits/overage and explicit restart/resume timing.**

## Research Intake Update — 2026-05-20

### New Related Research

- **[intake-571] "ECHO: Terminal Agents Learn World Models for Free"** (Papailiopoulos et al., MSR AI Frontiers; PDF, no arxiv)
  - **Relevance**: The autopilot loop IS a terminal agent (bash + orchestrator tool calls). ECHO's "predict-the-environment" auxiliary loss is the training-time analogue of what autopilot already does empirically — gather rollouts, observe terminal responses. If/when we train a small specialized model for autopilot's coordinator role, ECHO-style auxiliary loss is a cheap add-on.
  - **Key technique**: Joint action + observation prediction on the same GRPO rollout; no masking; ~2× over baseline GRPO across Qwen3 family.
  - **Delta from current approach**: Pure training-time technique, GPU-gated. Out of scope for the current CPU-only autopilot, but worth noting in the gpu-acceleration-path watchlist alongside SkillRL and Endless-Terminals (intake-574). The pattern itself (treat all bytes in a rollout as training signal, not just policy bytes) is a useful frame even for non-training contexts — e.g., consider whether the Pareto archive should also score "tool-response predictability" as a co-objective.

### ECHO Deep-Dive Refinement — 2026-05-20

**ECHO authors and exact numbers corrected** (local PDF read at `/tmp/echo.pdf`): authors are Shrivastava/Awadallah/Papailiopoulos (MSR), not the earlier-guessed Gandhi/Garg/Goodman. Exact loss `L_total = L_GRPO + 0.05 · L_Env`. TB-2.0 pass@1: Qwen3-8B 2.70%→5.17%, Qwen3-14B 5.17%→10.79%. **Verifier-free claim is overstated** — Table 4 shows env-only fine-tune REGRESSES TBLite by −3.9pp from seed. Advertised public repo `github.com/microsoft/echo-rl` is 404 as of 2026-05-20; no training code, no checkpoints. Reproduction requires 8×B200, infeasible even on a single DGX Spark.

**EPYC-actionable spinoff (NOT ECHO)** — borrows the "prediction error = understanding" intuition without any training:

- **PEAF (Prediction-Error-As-Feature, NEW work item, LOW priority, doable today)**: For each probe the autopilot controller proposes, log an **expected-terminal-output** prediction (a tiny LM call against a current SOTA local model) BEFORE running the probe. Then measure surprise (e.g., token-overlap or perplexity of actual response under the predictor) and persist it alongside the probe's reward in the Pareto archive. Test whether surprise correlates with config-quality gradient. If it does, promote to an explicit Pareto co-objective. Cost: logging-only; ~zero compute overhead per probe. Cheap-kill criterion: if surprise has no correlation (r²<0.1) with gradient over 200+ probes, abandon. This is NOT a reproduction of ECHO — it is an inference-time analogue of the underlying intuition, and is the only ECHO-adjacent thing buildable on CPU today.

## Deep-Dive Task Proposals — 2026-05-25 (intake-607 Code-as-Agent-Harness §5.2.1 / §5.2.3 / §5.2.4)

Two ideas from the Code-as-Agent-Harness survey land on the Pareto-archive optimizer. Audit pass converted the brainstorm into concrete acceptance and storage contracts.

> **Schema dependency (gap-fix 2026-05-25):** `behavior_signature` (BSV-1) and the `harness_metrics` fields HLE-4 consumes live in the **shared trace schema owned by [`unified-trace-memory-service.md`](unified-trace-memory-service.md) § "Shared Harness/Trace Schema"**, not a private autopilot store. Reuse `event_id` links; do not duplicate payloads. Shared schema lands before BSV-1/HLE-4 writes.

- [x] **HLE-4 — Harness-level objective dimensions (beyond the 4D Pareto).** The current archive optimizes quality × speed × −cost × reliability on *task outcomes*. The paper argues final-task-success is a noisy single bit that rewards shortcut configs. Add the per-component harness metrics defined in [`meta-harness-optimization.md`](meta-harness-optimization.md) HLE-1 (execution fidelity, feedback interpretation, planning stability, memory coherence, recovery rate) as **observe-only fields first**, then promote them to guardrails or co-objectives only after they show predictive signal. Required implementation pieces:
  - ✅ Extend `EvalResult` / journal JSONL with `harness_metrics`, `oracle_adequacy`, and `metric_schema_version` (`931e43c`).
  - ✅ Compute rule-based HLE-1 metrics and register HLE-2 oracle-adequacy defaults in observe-only form (`9222a19`).
  - ✅ Analyze N trials: 2026-06-12 snapshot contained 580 metric-bearing trials (`51..779`). `execution_fidelity` and `planning_stability` separate keep/revert but are not independent enough to promote; `feedback_interpretation`, `memory_coherence`, and `recovery_rate` fail signal/missingness gates.
  - Cheap-kill result: current rule metrics remain diagnostic/advisory and do not enter Pareto selection. Any future HLE promotion requires N2 per-question ledgers/sequential verdicts and a redesigned metric with independent predictive signal.
- [ ] **BSV-1 — Behavior-signature versioning for archive integrity.** We are AHEAD of the paper on raw regression gating (quality floor, per-suite guard Δq<−0.1, throughput floor, auto-rollback, git-committed reverts). The remaining gap: a newly-accepted config can silently break a *prior* Pareto win because improvements are merged syntactically, not behaviorally. Attach a **behavior signature** to each archive member. Minimum signature fields: per-sentinel final outcome, normalized answer hash, route path, tool-call sequence hash, escalation path, latency bucket, token bucket, key harness metrics, and oracle-adequacy version. Store both a compact hash for fast diff and an expanded JSON vector for explanation.
- [ ] **BSV-2 — Differential testing on accept.** Before promoting a mutation, run new vs old on the same sentinels and compare behavior (not just aggregate score). Prefer paired sequential execution under identical server/model snapshot for attribution; use parallel execution only when explicitly approved and when concurrency cannot contaminate latency measurements. Reuse the existing T0/T1 tower; the novelty is paired behavioral comparison. Gate on both scalar regression and signature diff severity. *(Inference-gated — respect `feedback_no_concurrent_inference`; design as a paired-eval lane the user launches.)*
- [ ] **BSV-3 — Conflict-aware acceptance.** When two independently-accepted mutations touch the same subsystem (prompt + routing, two prompts, prompt + tool policy, context packer + batch editor), flag potential *semantic* conflict for review rather than blind compose. Implement a mutation-dependency ledger keyed by `subsystem`, `files_touched`, `prompt_sections_touched`, `feature_flags`, `behavior_signature_delta`, and `parent_trial`. Conflict severity should increase when two mutations improve different sentinels while producing opposing route/tool/signature changes.

**Audit refinements / missed gaps**:

1. **Behavior signatures must include process, not just answers.** Final-answer hashes miss regressions where a config gets the right answer via forbidden web-search leakage, extra escalations, or much higher cost. Include route/tool/escalation/token features.
2. **Diff severity needs a policy.** Not every signature change is bad. Define severity classes: `benign` (format-only/latency bucket unchanged), `watch` (route/tool path changed but score same), `blocking` (prior Pareto sentinel flips pass→fail, forbidden shortcut appears, or cost/latency bucket crosses guardrail).
3. **Paired eval must control model state.** KV warmth, server reloads, exogenous restarts, and concurrent traffic can swamp a harness delta. BSV-2 should record fleet marker/version and reuse the exogenous-restart metadata already added in the resilience work.
4. **Archive compatibility needs migration.** Existing Pareto entries lack signatures. Backfill what can be computed from journals/traces and mark older entries `signature_confidence=partial`; do not compare partial and full signatures as equal evidence.
5. **HLE-4 and BSV should share storage.** Store harness metrics and behavior signatures in the same journal/trace event family so AP-27 verifiers and HALO/P20 analyzers read one schema.

Sibling: the **PEAF** item above (prediction-error-as-feature) is independent — HLE-4/BSV are about *what we measure and how we gate*, PEAF is about *a new feature to log*. Roll-up: [`routing-and-optimization-index.md`](routing-and-optimization-index.md) P24/P25. Interacts with AP-27 (RLVR eval tower — the verifier must score the augmented objectives). Source: intake-607 `deep_dive` in `research/intake_index.yaml`.

## Post-result conditional workflow + mitigation (HLE-4 / J9, BSV-2 / J11)

**HLE-4 (J9) — observe-only result.** Pre-run wiring is built: `EvalResult`/journal JSONL fields landed in `931e43c`, and HLE-1/HLE-2 observe-only computation/registration landed in `9222a19` (shared schema owned by `unified-trace-memory-service.md`). The 2026-06-12 analysis over 580 metric-bearing trials keeps current metrics diagnostic/advisory only: `execution_fidelity` and `planning_stability` separate keep/revert but mostly mirror existing quality/reliability/safety signals; `feedback_interpretation` is low-confidence/low-variance; `memory_coherence` is constant; `recovery_rate` is missing on 99.3% of rows. No Pareto co-objective/guardrail promotion before N2 per-question ledgers/sequential verdicts and a redesigned metric with independent predictive signal. Mitigation remains: low-signal/low-confidence metrics never gate; oracle-adequacy flags shortcut-prone suites so they cannot drive promotion.

**BSV-2 (J11) — mutation accept gate.** Pre-run wiring: `compute_behavior_signature` (done) wired into the archive accept-path + a paired-eval lane. Per candidate mutation, paired new-vs-old on the same sentinels → `diff_signatures` severity: `benign` → auto-accept; `watch` (route/tool changed, outcomes equal) → accept + log; `blocking` (prior-pass sentinel regressed, forbidden shortcut, or cost guardrail crossed) → **REJECT, do not promote**; shared-subsystem touch → BSV-3 conflict-ledger review. Mitigation: gate accept on BOTH scalar regression AND signature severity; partial-confidence signatures cannot certify `benign` (audit #4); git-committed revert remains the backstop. Operator decision trees mirrored in [`bulk-inference-campaign.md`](bulk-inference-campaign.md) Package J.

## Research Intake Update — 2026-05-27

### New Related Research

- **[intake-615] "Fortytwo: Swarm Inference with Peer-Ranked Consensus"** (arxiv:2510.24801)
  - Relevance: closer formal analog to NumericSwarm Pareto scoring than the SiliconSwarm@Ensue entry (intake-248) already feeding B1/B4/B5. Bradley-Terry-style aggregation over peer rankings is the explicit version of "pairwise comparison with confidence" we approximate via 4D Pareto + hypervolume.
  - Key technique: heterogeneous models generate independently → pairwise-rank each other's full completions → reputation-weighted Bradley-Terry aggregation → winner.
  - Reported results: +17.21pp on GPQA-Diamond (85.90 vs 68.69 majority voting); 0.12% vs 6.20% prompt-injection degradation.
  - Delta from current approach: NumericSwarm uses NSGA-II/Optuna over a 23-param numeric surface scored by an eval tower. A Bradley-Terry mode would replace the 4D scalarization with pairwise peer judgments on candidate configurations' eval-tower outputs — useful when the scalarization is the noisy step (high hypervolume variance) and the judging is cheap. Concrete integration probe: when `hypervolume_slope() < 0.001` triggers stagnation, instead of (or before) switching to CEM sampling per the intake-269 TPO note, run pairwise judging of the top-K candidates and let the BT-aggregated ranking break ties. Code reference: `numeric_swarm.py:99` (sampler init), `pareto_archive.py:188-200` (stagnation detection).
  - Caveat: claim that the same swarm "beats GPT-5/Claude Opus/Gemini" is founder-marketing only — the paper's actual baseline is majority voting.

- **[intake-614] Fortytwo Network — chunk-ranking pipeline (unpublished founder claim)**
  - Relevance: if real and disclosed, chunk-ranking = mid-stream cross-model ranking against milestones during single-shot generation, which would let an ensemble vote without paying N-rounds latency. That is a primitive we currently do NOT have any analog of in the autopilot loop or the orchestrator. Tracked as a watch item until they publish.

## 2026-06-07 — Per-suite regression gate made resolution-aware (trial-707 halt fixed)

Autopilot self-halted 06-06 @ trial 708 (`critic_reject_loop`). Root cause: the per-suite
regression gate used a fixed `-0.1` floor against per-suite scores quantized to `{0,1.5,3.0}`
(~2 questions/suite on the hybrid T1 eval). One question flipping = a `-1.5` "regression" =
15× the floor, so the gate fired every seeder trial → `mad_noise`-excluded → planner looped on
`seed_batch` → critic halted it. The planner's eval-artifact diagnosis was correct; the codex
critic's "broken-instrument, no evidence" rejection was wrong (evidence = the quantized per-suite
METRIC lines). This is the concrete mechanism behind the long-standing **MAD over-exclusion** open item.

Landed (epyc-orchestrator, uncommitted): `per_suite_regression_threshold()` widens the floor to
the coarser single-flip quantum `3/n` using new `EvalResult.per_suite_counts` +
`Baseline.per_suite_counts_by_tier` (empty ⇒ legacy `-0.1`); `classify_learning_exclusion()` now
treats `mad_noise`/`reproduction_confirmed` as benign **only when `verdict.passed`** (trial 707
failed 3 per-suite checks yet was admitted as a "trusted within-noise representative"); `autopilot.py`
failed-but-not-benign trials skip the clean archive/baseline update. 11 new tests; patched gate
clears the exact trial-707 numbers. Full write-up: `epyc-root/progress/2026-06/2026-06-07.md`.

**Outstanding (operator):** (1) baseline-count refresh is optional — result-side counts already fix
it and baseline counts self-populate on the next clean T1 trial; a live refresh eval is operator-run.
(2) Restart is an operator call — `autopilot_state.json` was externally rewritten 06-07 16:04 to
`paused=false`/counter=0 (already restart-ready, but not done by the fix session).

## Research Intake Update — 2026-06-10

### New Related Research
- **[intake-692] "Economy of Minds: Emerging Multi-Agent Intelligence with Economic Interactions" (EoM)** (arxiv:2606.02859, Qi/Kakade/Lakkaraju/Du, Harvard/MIT)
  - Relevance: a Hayekian agent **economy** whose population lifecycle maps onto autopilot species management — agents accumulate wealth from environmental rewards; **wealthy (effective) agents are mutated via exploitation, bankrupt (ineffective) agents are replaced via exploration**. This is a clean conceptual analog for autopilot's Pareto/cost-aware species selection and for decision-aware-routing reward shaping.
  - Key technique: auction-allocated action rights + peer-to-peer payments → decentralized credit assignment with **no explicit communication protocol**; economic selection drives emergent multi-step reasoning from weak-agent init.
  - Reported results: outperforms stronger monolithic baselines across five agentic tasks (abstract-level; per-task numerics not published).
  - Delta from current approach: **adopt the pattern, not the system.** The literal auction/payment machinery presumes many concurrent agent instances + per-action auctions — incompatible with the EPYC single-stack, no-concurrent-inference, sequential-load constraint. Transferable: the wealth-gated-mutation / bankruptcy-gated-replacement lifecycle and local-reward credit assignment as inputs to species management. Not peer-reviewed yet; no independent reproduction.

### Deep-Dive Refinement (2026-06-12) — downgrade to metaphor-mostly
EoM's "auction" is fixed-bid first-price (= static priority + random tie-break, `hayekmas/base/mas.py`) and its wealth ledger is the **softmax-over-effectiveness bandit autopilot already runs**: `ExperimentJournal.species_effectiveness()` (`experiment_journal.py:759`, `rate = pareto/total`) → `MetaOptimizer.rebalance()` → weighted-random `select_species()` (`meta_optimizer.py:136`). EoM's only novel content — **bucket-brigade temporal credit assignment** — needs a multi-step **live-reward episode with N concurrent agents**, which the sequential single-config trial policy (+ no-concurrent-inference rule) doesn't have → **non-portable**. **No decision-aware-routing action** (routing is single-shot; bucket-brigade only helps multi-step live-reward episodes). One *optional* ~60-LOC item: a `SpeciesLedger` replacing `rebalance()`'s hand-tuned constants (`0.30 + rate*0.2`, floors, stagnation boosts) with a rent+reward `softmax(wealth)`. **Gate:** `AUTOPILOT_SPECIES_LEDGER=shadow` for ≥80 trials (never routes), KEEP only if ledger weights predict next-window Pareto contribution strictly better AND remove ≥3 magic numbers; else close as `metaphor_only` (likely DROP — same Pareto signal). No auctions, no payments, no species deletion. Full: `research/deep-dives/2026-06-12-economy-of-minds.md`.
