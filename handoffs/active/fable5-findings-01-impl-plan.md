# Fable 5 findings 01 — IMPLEMENTATION PLAN: the evidence plane

**Date**: 2026-06-12 (refinement pass, operator-requested — supersedes the original brief's "no implementation plans" constraint for this doc).
**Companion to**: `fable5-findings-01-measurement-and-integrity.md` (the architecture and evidence). This doc is the build plan: phases, exact touchpoints, schemas, rollout/shadow strategy, acceptance gates, risks. Phases are ordered so each is independently shippable and none blocks the running autopilot for more than a restart.

**Integrates the operator's question**: *"autopilot keeps reusing the same handful of debug-suite questions when our database is MUCH larger — should that be leveraged better?"* → **Affirmative, with a twist** (Phase 2): the fixed set is an *accident that bought you paired-design statistical power* — naive rotation would destroy that and make things worse. The right design uses the 53K pool three ways at once: a **designed paired core** (replaces the accidental seed=42 draw), a **rotating audit block** (anti-overfit + pool-level estimate), and **large fresh promotion evals** (the T2 you built but used 4 times). Detail in Phase 2.

---

## Phase 0 — Hotfixes (days; no architecture; stops live damage)

Each item: site → change → test.

| # | Defect | Site | Change | Acceptance |
|---|---|---|---|---|
| 0.1 | Baseline ratchet (live, t775) | `safety_gate.py:935-941` `update_baseline` | Require the candidate's config-fingerprint **reproduction cluster** (`pareto_archive.repro_clusters`) to have k≥3 members whose **median** exceeds the current baseline by ≥1 quantum, OR (interim, simpler) replace monotonic-max with rolling median of last 10 *passed* trials' quality. Also: one-time operator reset of `baselines_by_tier['1']` from 1.953 to the cluster-median of the current config (~1.84) | replay of trials 714–776 shows the modal outcome no longer violates; no single trial can move the baseline |
| 0.2 | Double `gate.check()` | handlers `actions.py:349,400,446,489` + loop `autopilot.py:2308` | handlers return their verdict with the result (`EvalResult.gate_verdict`); loop uses it if present instead of re-checking. (Alternative: memoize `check()` per trial-id inside the gate.) | MAD window gains exactly 1 entry/trial; `consecutive_failures` increments once; unit test with a failing mutation trial |
| 0.3 | Dead throughput floor | `safety_gate.py:493-505` `update_tier`, `:727-728` | `update_tier` refreshes `frontdoor_speed` (rename → `speed_floor_anchor`) as rolling median of passed-trial speeds **per `speed_metric_mode`** (the 12.7 was median-request-era; live is aggregate-batch). Floor = 0.8 × anchor | injecting a 35 t/s trial under a ~50 t/s anchor trips the floor branch (and thus the host-throttle remediation path) |
| 0.4 | T0 `[:10]` saturated gate | `eval_tower.py:701-724` | Decision fork (operator): (a) cheapest — drop T0 from `hybrid_eval` entirely (it discriminates nothing at 3.0-saturation and costs ~30s/trial); (b) use all 38 sentinels and re-derive the fast-reject threshold from one calibration batch. Recommend (a) now, (b) only if fast-reject ever mattered (journal shows 3 fast-rejects in 120 trials — it doesn't) | wall-time per trial drops; no behavior change on pass path |
| 0.5 | Self-criticism noise labels | `self_criticism.py:66-89` | threshold = `max(0.02, quality_quantum)` where quantum = 3/n from the eval result; below → label `unchanged` (new label), not keep/revert | replay: ≥60% of the last 120 keep/revert labels become `unchanged` |
| 0.6 | Strategy-store frontier leak | `autopilot.py:2470-2479` | add `and not learning_excluded_by` to the store condition | within-noise representative admission writes no strategy row; log line and behavior now agree |
| 0.7 | Distill reads corrupt rows | `actions.py:614-627` / `evolution_manager.py:106` | filter `bug_corrupted_by` + `learning_exclusion`-tagged rows before the LLM sees them (reuse `BENIGN_LEARNING_EXCLUSIONS` semantics: benign-excluded rows MAY pass as facts but carry a `within-noise` tag in the rendered text) | unit test: corrupted row never appears in distill prompt |
| 0.8 | Planner can't choose its own quantum | `eval_tower.evaluate`/`eval_t1/t2` | clamp/ignore planner-supplied `n`/`seed`; tier specs are server-side constants | `deep_eval` with custom n runs the spec'd n |

All Phase-0 items are deployable at the next autopilot restart (operator already restarts routinely); none touches the orchestrator API.

## Phase 1 — Per-question ledger + paired statistics (~1 week; the keystone)

**1.1 Stable question identity.** `qid = sha1(suite + '\x00' + prompt_text)[:16]` computed in `question_pool.py` at load. Pool file unchanged (id is derived, so pool edits create new ids — correct behavior: an edited question is a different item).

**1.2 Record per-question outcomes.** `eval_tower._aggregate` (`eval_tower.py:455-683`) emits `question_results: [{qid, suite, correct, latency_ms, tools_used}]` into `eval_details`. Size: ~43 × ~60B ≈ 3KB/trial JSONL growth — negligible (journal is 11MB/656 rows today). TSV untouched.

**1.3 Paired replay tool.** `scripts/autopilot/paired_stats.py`:
- `mcnemar(trial_a, trial_b)` → discordant counts (b,c), exact binomial p, odds ratio. Works on any two trials sharing ≥80% qids.
- `config_vs_baseline(fingerprint)` → pools all trials of that fingerprint vs all baseline-config trials; per-qid majority vote → McNemar on the item level (kills per-trial sampling noise entirely for the fixed core).
- This is also the **gate-acceptance experiment**: once ~2 weeks of vectors exist, replay keep/revert decisions; per findings-01 §4, ≥30% verdict flips ⇒ proceed to 1.4.

**1.4 Sequential keep/promote (replaces single-shot MAD on the improvement branch).** New `src/autopilot_core/sequential_verdict.py`:
- Per config-fingerprint, maintain an **e-process** against H0 "no better than baseline": for each new trial, per-question paired differences vs the baseline config's per-qid majority → e-value update (mixture e-test over Bernoulli effect sizes; or simpler: a grouped SPRT with α=0.05, β=0.2, effect floor = 1 core-question flip). Anytime-valid → the planner may evaluate a config any number of times without p-hacking — this is the property that makes a *self*-optimizer safe.
- Verdict states: `accumulating(k, e)` → `confirmed` (e ≥ 1/α) → eligible for baseline/archive plain admission; `refuted` (e ≤ β-bound); `abandoned` (budget exhausted).
- **Wiring**: `safety_gate.check` improvement branch (`:638-689`) calls SequentialVerdict instead of `_mad_significance`; `mad_noise`/`reproduction_confirmed` categories collapse into `accumulating` (the concept they were both approximating). `learning_exclusions.py` maps `accumulating` → benign (no strategy/AP-22 learning until `confirmed`).
- **Shadow rollout**: run both for 2 weeks; journal both verdicts; flip when disagreement analysis is reviewed. Keep MAD code behind `AUTOPILOT_LEGACY_MAD=1` for one release.

**1.5 Planner-visible power line.** Prompt assembly (`autopilot.py:1724-1806` trustworthiness section) gains one generated line: `Instrument: core n=40, quantum 0.075, MDE(single trial) 2 flips; sequential confirmation typically needs k≈3-5 trials for a 1-flip true effect.` The dispatch gate (`uncritiqued_dispatch_block_reason`) gains a rule: an experiment whose hypothesis names an expected effect below MDE must declare a reproduction plan (k trials) or be revised.

## Phase 2 — Leverage the 53K pool: the three-tier sampling architecture (operator's question — AFFIRMATIVE)

**Why not naive rotation**: with fresh random questions each trial, between-trial variance jumps from the observed sd≈0.83 flips to the iid binomial SE ≈ 3.2 flips at n=43 — every comparison gets ~4× *less* sensitive. The fixed set is why your trials are even as repeatable as they are. The pool's value is realized differently.

**Evidence base (dedicated pool sweep, 2026-06-12)**: pool = 53,181 questions / 19 suites (largest: general/MMLU 14,042; thinking 11,214; hotpotqa 7,405); T1 costs median **798s for 43q at concurrency 3 (~18.5 s wall/question; +10 questions ≈ +3.1 min, +23%)**; T2 = 494q ≈ 3.2h. **Of the fixed 43: ~8 can NEVER pass** — usaco×2 and instruction_precision×2 have `expected=''` and `_eval_question` only scores when `if not error and expected:` (`eval_tower.py:341-347`) so they are *never even scored*; bigcodebench×2 require pandas, which is **absent from the orchestrator venv** (verified import failure) so their unittest subprocess dies; vl×2 score 0/376 trials — note the first sweep's "no vision server" explanation was **wrong** (ports 8086/8087 verified live this session, and `image_path` IS forwarded end-to-end: `eval_tower.py:308,326` → `seeding_orchestrator.py:665-666`) — the vl cause is unresolved and needs ONE traced request. A further ~4 items are individually pegged-zero (incl. a likely scoring artifact: simpleqa expects "Dušan Lajović" under token-F1 and `_normalize_text` keeps diacritics, so "Dusan Lajovic" fails) and ~14 sit in saturated suites. **Net: ~10–14 of 43 questions carry all per-trial signal; the fixed-set quality ceiling is ≈2.44/3.0** — the planner's recurring "Investigate declining suites: instruction_precision (0.00)" directive is the system agonizing over structurally dead items.

**2.0 Instrument repair FIRST (before any core selection; ~2–3 days, mostly one-liners).**
1. Fix or consciously scope the `expected==''` gate: `code_execution`/`programmatic` methods score via test_code/verifiers and don't need a truthy `expected` — let them through (debug_scorer already handles it), or excise usaco/ip from T1.
2. `uv add pandas` (or excise the 2 bcb items); confirm which python3 the scoring subprocess resolves.
3. Trace ONE vl eval request end-to-end (servers up, plumbing present, score 0 — find the break: routing under force_role? vision stage not firing on the eval path? scoring?). Fix or excise.
4. NFKD-fold diacritics in `_normalize_text` (scan the pool for other diacritic-bearing expected answers — pure-python pass).
5. Journal T0 sentinel per-suite scores under distinct names (`sentinel_<suite>`) so they stop polluting pool-suite health reads (the historical "ip sometimes passes" was T0 sentinel rows).
6. **Persist the Seeder's per-question results** — it already builds `{suite, question_id, rewards, roles_tested}` per batch in memory and `_action_seed_batch` drops them (`species/seeder.py:296-303` vs `actions.py:155-198`); its seen-set also resets every restart (persist into `seeder_state`). This is free item-statistics data from 426 historical seed_batch actions' worth of machinery.

**2.1 Designed paired core (replaces the accidental seed=42/38).**
Reuse what exists: `load_questions_by_ids` (`question_pool.py:250-300`) is the natural hook for a curated core; every pool record already carries a difficulty `tier` 1–3; `sample_from_pool` already supports seen-set exclusion; the **29 unused harder sentinels** in `sentinel_questions.yaml` (dead behind the `[:10]` slice) are immediately available headroom material; ~5,000 stale per-question outcome records (Mar–Apr era: 3way checkpoints, seeding_diagnostics) serve as difficulty *priors* (pre-gemma4-swap, so priors only). The dormant `update_eval_registry.py` (per-suite stats with `curated: true` merge) is the item-analytics skeleton.
- Build `benchmarks/prompts/core_v2.jsonl` (~40 items) selected by item statistics, not by accident: from suites that *discriminate* (drop the ~10 always-0 and ~16 always-3 items — zero Fisher information), target per-item difficulty p∈[0.2, 0.8] under the current production config, stratified across the discriminating suites + tool_use sentinels.
- Until item stats exist (chicken-and-egg), bootstrap: run ONE calibration batch (~300 stratified questions × 3 reps ≈ 6 normal trials' wall time, operator-approved inference) to estimate per-item p; select the core from it. This calibration also produces the **first pool-level quality estimate with a CI** — something the system has never had.
- Core is **versioned** (`core_id` journaled per trial); comparisons/baselines/frontiers are per-core-version (you already learned this lesson the hard way with n=38↔43 frontier mixing).
- Refresh policy: quarterly or on drift (see 2.3), by swapping ≤20% of items; each swap bumps core version.

**2.2 Rotating audit block (~10 q/trial).**
- Each trial appends 10 fresh pool questions, stratified, seeded by `trial_id` (deterministic, reproducible). Journaled in the same per-question ledger keyed by qid.
- Purpose 1 — **overfit alarm**: maintain rolling correlation between core-delta and audit-delta per config; a config that improves the core but not the audit stream is gaming the core (formatting effects etc.). Surface as a planner-prompt flag + a gate warning.
- Purpose 2 — **pool-level estimator**: the audit stream accumulates ~200 fresh item-outcomes/day across the pool; over weeks this yields per-suite pool-level quality with shrinking CIs, and per-item difficulty stats for 2.1's refresh — the 53K database becomes the system's item bank instead of dead weight.
- Cost: +10/43 questions ≈ +23% eval wall (≈3 min/trial). Worth it; if too dear, run the audit block every 2nd trial.

**2.3 Item-analytics job (offline, no inference).** `scripts/autopilot/item_analytics.py`, run weekly or per-100-trials: per-qid attempts, p, point-biserial discrimination vs trial quality, last-seen; outputs (a) core-refresh candidates, (b) **broken-item report** — items with p=0 across all configs and formats are scoring/path artifacts, not hard questions (your comma-separator incident proves the class); (c) drift report on the always-0 suites. This directly resolves the open question of whether effective n is 43 or 33: today **5 suites are pinned at 0** (instruction_precision, bigcodebench, vl, usaco, mode_advantage_hard) — vl almost certainly cannot pass through the text /chat eval path at all, and bigcodebench/usaco depend on `code_execution` scoring working in-path. Verify each: artifact → fix or excise from T1; genuinely-hard → keep in promotion evals only, where n is large enough to register movement.

**2.4 Promotion eval = T2 made real.** A config reaching `confirmed` (Phase 1.4) triggers a **fresh stratified n=200–500 draw** (never-seen-recently qids; the pool affords ~100 such draws/year without reuse) — this is the generalization test, the thing T2 was for but ran 4 times. Promotion to baseline requires: sequential-confirmed on core AND promotion-eval delta ≥ 0 with CI excluding regression. Wall cost ~1–2h, paid only by winners (a few per month at current rates) — and this is exactly the workload the MI210-as-eval-engine (findings-03 G4) accelerates 5–10×.

## Phase 3 — Event-sourced runtime (1–2 weeks, after Phase 1 lands)

- **3.1 Single commit point**: trial finalization writes ONE journal row (with question_results, verdicts, exclusion record). `ParetoArchive` becomes an in-memory view: on startup, `journal_reconstruction.reconstruct_archive_from_journal_rows` (already exists, already proven — and already caught real drift: live T2 frontier {363} vs reconstructed {363,367}); during run, `archive.update` mutates only memory. Delete `ParetoArchive.save`'s read-merge-write into `autopilot_state.json` (`pareto_archive.py:174-220`) — `state.json` drops the `pareto_archive` key (one-time migration: keep legacy-read fallback for one release).
- **3.2 Rotation/compaction**: journal rotates per 1000 trials — chain segments with a **snapshot row** (full reconstructed view + policy version) as the first row of each new segment; rebuild = load snapshot + fold tail. Bounded startup cost forever.
- **3.3 Supersession events**: new row type `{type: "supersession", target_trial_ids, fields, reason, policy_version, actor}`. `scrub_journal.py` and every future "rewind/purge" becomes an append. Rewrite-in-place is removed (the function, not just the habit).
- **3.4 Baseline as a fold**: `Baseline` computed at load from (frontier, eligibility rules, policy version); `update_baseline` becomes an *event* (`baseline_promotion`) in the ledger, applied by the fold. The YAML stays a seed for cold start only. The fixture-clobber class dies permanently.
- **3.5 Acceptance**: (a) drift check passes by construction (it IS the load path); (b) kill -9 during a trial → WAL recovery reproduces identical views; (c) replay of the full historical journal (with its existing bug_corrupted_by tags as implicit supersessions) reproduces today's T1 frontier.

## Phase 4 — Narrative regeneration (parallel to Phase 3)

- **4.1 STM → generated view**: `short_term_memory.md` rebuilt each trial from the ledger (last-N trustworthy trials, open hypotheses with falsifiers + provenance trial-ids, suite trends). Delete the read-modify-write path; the file becomes cache. Mid-word truncation fixed by structure (render budgets per section, not char-chop).
- **4.2 Strategy provenance**: `strategies.db` rows gain `evidence_trial_ids JSON`; `retrieve()` filters rows any of whose evidence trials are superseded/excluded (extends the existing AP-28 staleness machinery, which already does this for file hashes — same pattern, ledger-keyed). Distill prompt template requires the LLM to cite trial-ids per insight; uncited insights are stored quarantined.
- **4.3 Session hygiene**: default `supports_resume=False` for the draft provider (delete `state['session_id']` persistence, `autopilot.py:1944`); replace with a generated "prior-decisions digest" (last k rows of `planner_archive.jsonl` — which becomes read-back-useful for the first time). Also archive failed draft calls (move `_append_planner_archive` before the early-return).
- **4.4 program.md split**: `constitution.md` (~150 lines, human-only: trust boundary, one-variable rule, risk policy, escalation rules) + `system_card.md` **generated at restart** from live sources: registry roles/ports/models (so "architect_coding:8084" class staleness is impossible), instrument spec (core version, n, quantum, MDE), action contracts with validator caps (the #776 class becomes self-documenting), known-dead-ends compiled from blacklist + closed handoffs. Generator: `scripts/autopilot/gen_system_card.py`; prompt assembly swaps `program.md` for the pair. Expected prompt shrink: ~46% → ~20% while *gaining* accuracy.

## Phase 5 — Game layer (after 1+2; small)

- **5.1 Critic measurement-view**: `build_critique_prompt` (`planner_coordinator.py:411-467`) stops embedding the full planner prompt; instead: proposed action + rationale + the power line + per-question diff summary of the relevant config history + provenance-missing flags. Critic instructions gain: reject unmeasurable-as-stated proposals (no reproduction plan below MDE), reject claims citing numbers without provenance.
- **5.2 Surprise-driven exploration**: PEAF surprise (already journaled) feeds `species_budget` rebalance: species credited by realized information gain (|surprise| of *confirmed* outcomes), not by frontier-tag counts. Cheap-kill already defined in program.md (r² gate) — keep it.
- **5.3 Audit-stream gaming alarm** (from 2.2) wired as a gate warning + planner flag.

## Sequencing & effort summary

| Phase | Effort | Depends on | Ships value alone? |
|---|---|---|---|
| 0 hotfixes | 2–4 days | — | yes (stops live damage) |
| 1 ledger+paired | ~1 week | 0 | yes (replay evidence + better gates) |
| 2 pool architecture | core: 2–3 days + 1 calibration batch; audit: 1 day; analytics: 2 days | 1 | yes (instrument power) |
| 3 event-sourcing | 1–2 weeks | 1 | yes (kills incident class) |
| 4 narrative regen | ~1 week | 3 for 4.1/4.2; 4.3/4.4 anytime | partially (4.4 is immediate) |
| 5 game layer | 2–3 days | 1, 2 | yes |

**Risks**: (R1) journal growth with question_results — bounded, ~3KB/trial; (R2) sequential-test misconfiguration — mitigated by 2-week shadow + replay; (R3) event-sourcing migration bugs — mitigated by the reconstruction already being battle-tested on the dashboard path + acceptance test 3.5c; (R4) core-selection bias (picking items the current config finds "medium" optimizes for the current config's neighborhood) — accepted and mitigated by audit block + quarterly refresh; (R5) operator workflow churn — every phase keeps the existing CLI/runbook surface.
