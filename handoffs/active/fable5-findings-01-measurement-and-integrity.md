# Fable 5 findings 01 — Epistemic integrity & the optimizer↔evaluator game (facets 1+2, merged)

**Date**: 2026-06-12. **Status**: final consult output. **Scope**: brief §4.1 + §4.2, treated as one problem per the brief's own suspicion — confirmed correct to merge.
**Evidence**: 5-agent sweep (full reports archived; citations inline are `file:line` under `/mnt/raid0/llm/epyc-orchestrator` unless absolute) + first-hand reads of `program.md`, `short_term_memory.md`, live `autopilot_state.json` (trial 777), and adversarial re-verification of the load-bearing claims.

---

## 1. The reframe (read this before the architecture)

You asked: *"what architecture makes a recursive self-optimizer's evidence base provably uncontaminable?"* That is the right question second. The right question first is:

> **Your binding constraint is decision-grade evidence throughput — the rate at which the system can produce measurements that justify a decision. Everything else (contamination, planner gaming, halting loops, backlog stagnation) is downstream of an instrument whose resolution sits below the effect sizes being optimized.**

Measured, live (trials 714–776): T1 = a **fixed 43-question set** (seed=42, same questions every trial: `eval_tower.py:726-752`), quality quantum 3/43 ≈ **0.070**, MAD certification bar 0.103 (~1.5 question-flips), observed trial sd 0.058 (<1 flip), per-suite quantum **1.5** (2 q/suite), ~10 of 43 questions in permanently-zero suites and ~16 saturated — **effective discriminating n ≈ 10**. The planner's action space (flag toggles, seed batches) produces effects of 0–2 flips. Result, visible in the live `short_term_memory.md`: the same flags re-"confirmed" repeatedly at q=1.81–1.95, 69 of the last 120 trials labeled "revert" by a ±0.02 self-criticism rule that is 3.5× finer than one question flip, 5 frontier points after 777 trials. **The system is not learning slowly; it is measuring nothing and narrating the noise.**

Every contamination incident you fought is one of three distinct diseases that your brief lumps together as "contamination":

| Plane | Disease | Your incidents |
|---|---|---|
| **Metrology** (the instrument lied) | objective mis-measured or under-resolved | token double-count (speed ×1.55–2), per-suite 1.5 quantum deadlock (t707), tool_use measured 0 forever, T0 scale mismatch, dead throughput floor |
| **Decision policy** (right facts, wrong inference) | gates/aggregation misclassify | MAD over-exclusion of reproduced wins, T0 frontier pollution, baseline gate-lock, **live baseline ratchet (t775, see §4)** |
| **Narrative** (refuted stories resurrect) | hypotheses outlive their evidence | distill re-injection, falsifier recurrence, gate-lock story, @708 resumed-session fixation |

Architecture that fixes plane 3 without planes 1–2 produces a clean memory of noise. Fix order: **metrology → policy → narrative.**

## 2. The architecture ("name and theorem")

### 2.1 The evidence plane: event-sourced measurement ledger (CQRS for experiments)

**Name**: single append-only measurement ledger; every other store is a *derived view* — a pure fold over (ledger, policy-version). **Theorem**: if (a) facts are append-only with supersession events instead of in-place edits, (b) all derived state is recomputable from the ledger, and (c) nothing reaches the planner except through views that apply the exclusion policy, then any contamination is corrected by appending one supersession event and recomputing — no multi-store scrubs, no rewinds, no "did we purge FAISS too?" class of incident.

The decisive evidence that this is *cheap* for you: **the machinery already exists.** `src/autopilot_core/journal_reconstruction.py:68-236` already rebuilds the full archive shape (frontiers, HV history, representatives, exclusion telemetry) from journal rows alone — it is used by the dashboard but **not** by the runtime, which instead dual-writes the archive into `autopilot_state.json` via a second independent writer (`pareto_archive.py:174-220`) that has historically desynced from the journal (`scrub_journal.py:39-41`: "the Pareto archive is NOT touched"). The 2026-06-05 `autopilot_core` extraction was the first half of this architecture; promoting reconstruction to the runtime path is the second half. Six journal rewrites-in-place and ~10 state/strategy backups on disk are the cost of not having done it.

Concretely (high-level execution architecture, details yours):
- **Ledger** = the journal, append-only for real. A scrub becomes `{type: supersede, target_trial, reason, policy_version}` appended; readers fold supersessions. Backups become unnecessary; history edits become diffable and auditable.
- **Views** = Pareto archive, baselines, MAD windows, suite trends, STM — all recomputed on load (you already rebuild frontiers per-tier on load; finish the job). `autopilot_state.json` shrinks to genuinely operational state (counters, halts, circuit breakers).
- **Policy versioning**: exclusion rules, gate thresholds, and scoring versions get an id; every view is labeled with the policy id that produced it. When you fix a gate bug you bump the policy and views recompute — the t707/MAD/ratchet class of fixes stops requiring data surgery.
- **Provenance on every planner-prompt number**: each number carries `(trial_id | instrument@timestamp)`. Half your prompt already qualifies (journal/archive sections); half does not (`model_quality_signatures.yaml` hand-maintained, dated 2026-04-16, fed to the planner every trial: `autopilot.py:968,1670`; `memory_count`; batch telemetry). The critic's first standing instruction: *reject any claim citing a number without provenance.*

### 2.2 The metrology layer: sequential, paired, power-matched

**Name**: paired sequential testing with explicit error budgets. **Theorem** (the practical one): with a fixed question set, between-trial variance lives only in the few borderline questions; a paired test (McNemar on discordant pairs) detects a true 2-question improvement in 1–2 trials where your current trial-level aggregate can *never* certify it. Pairing is free statistical power you already paid the inference for and then discard at aggregation (`eval_tower.py:621-683` journals only aggregates).

- **Persist the per-question outcome vector** (43 bits/trial). This is the single highest-leverage change in the entire system, costing zero inference.
- **Keep/promote becomes sequential, not single-shot**: an SPRT/e-value style rule over the reproduction cluster you already maintain (`pareto_archive.upsert_representative` keeps per-fingerprint clusters with medians — the infrastructure is built). A config is *kept* when cumulative evidence crosses the boundary; *reproduction is a budgeted first-class action*, not a side effect the MAD filter argues with.
- **Spend questions where they discriminate**: drop the ~10 permanently-zero and ~16 saturated questions from the per-trial draw (zero Fisher information), rotate a holdout slice (see §3), and reserve large-n (150–200q) evals for promotion gates only. Also answer the open question: are the 5 always-zero suites (vl, usaco, instruction_precision, mode_advantage_hard, bigcodebench) even *passable* through the eval path, or is effective n actually 33? (Your own memory: "all-day FAIL on ONE suite = scoring artifact".)
- **Speed axis**: clean-pass trials currently enter the Pareto archive with raw single-trial speed at CV 9.1% (`autopilot.py:2424-2435`) — lucky draws manufacture frontier geometry. Median-cluster *all* admissions, not just within-noise ones; and re-anchor the dead throughput floor (`frontdoor_speed: 12.7` vs live ~50 aggregate; `safety_gate.py:727-728`, never refreshed by `update_tier` :493-505) so host-throttle remediation can actually fire.

### 2.3 The game layer: make honest reporting the only winning strategy

Your facet-2 question ("redesign so the planner's payoffs provably converge on the true frontier") mostly dissolves once the instrument can certify effects — a planner cannot game a measurement that requires sequential reproduction across a rotating holdout. What remains of the game design:

1. **Separation of powers**: the proposer must not choose its own measurement. Today the planner picks tier and (via `deep_eval` n) could silently change the quantum. Question selection, holdout rotation, and promotion thresholds belong to the evaluator side of the wall (the `program.md` trust boundary says this; enforce it in code, not prose).
2. **Holdout rotation as audit**: keep the fixed 38 for pairing power, but score every Nth trial on a disjoint random draw. A config whose fixed-set gain does not transfer to holdout is overfitting the instrument (your seed=42 forever is an open overfitting surface — `<answer>`-format and comma-format effects demonstrably move scores).
3. **Reward information, not frontier labels**: you already log PEAF forecasts and surprise (`peaf.py`). Promote surprise to the exploration bonus: actions are credited for *reducing posterior uncertainty about the response surface* (expected information gain), not for landing "frontier" tags on noise. This is the principled version of your stagnation/creativity fragments, and it gives the critic a quantitative basis for rejecting no-op proposals.
4. **The critic's contract**: today the critic re-receives the full 80KB planner prompt (`planner_coordinator.py:411-467`) — same evidence, same blind spots, double cost. Give the critic a *different* projection: per-question diffs, provenance flags, power analysis ("this proposal's expected effect is below the certification bar — reject as unmeasurable"). An adversarial critic with the same inputs is an echo; one with the measurement view is an auditor.

### 2.4 The narrative layer: regenerate, never replay

**Rule**: no persisted free-text store feeds the planner without passing the exclusion gate and carrying provenance links that are checked at read time. Hypotheses/insights are *recomputed from current facts* each time; a refuted narrative cannot re-enter because the facts it cites are superseded in the ledger.

Today's violations, each a live replay channel:
- `distill_knowledge` reads **raw** `journal.all_entries()` with no `bug_corrupted_by` filter (`actions.py:614-627`; `evolution_manager.py:106`) — only a legacy-scale text scrubber stands between corrupt rows and the strategy store.
- The frontier auto-store writes a strategy row keyed **only** on `pareto_status=="frontier"` (`autopilot.py:2470-2479`), so a within-noise representative admission writes narrative even as the adjacent log line claims "strategy learning still excluded" (:2390-2396).
- STM "Running Hypotheses" is a trial log with confirm/reject labels attached to noise (and its failure-pattern text is truncated mid-word — a narrative store that cannot even carry its evidence).
- The **resumed Claude CLI session** is an unaudited narrative store outside every scrub (the @708 fixation lived there). Policy: planner sessions are ephemeral by default; resume only with an explicit, provenance-stamped context replay that goes through the same gate. (You already detect stale-session phrases — `controller_io.py:361-390` — which is a sanitizer on a channel that shouldn't exist.)
- `program.md` is the largest narrative store of all: 46% of every planner prompt, containing refuted facts as ground truth (architect_coding:8084 — removed 2026-05-06; "512GB RAM"; pre-swap frontdoor; the OLD git-commit/revert loop that isn't how the system works; "NEVER STOP" contradicting your designed-halt machinery; a "15 per suite" sample-size claim that doesn't match the real 2/suite instrument). The planned "trim" is mis-framed as a token-budget task — it is an **integrity** task: split it into (a) a generated, provenance-checked "system card" (current instrument, current stack, current action contracts — machine-built from the registry/state each trial) and (b) a short, human-authored constitution of genuinely timeless policy. A planner whose constitution misdescribes the instrument *will* produce confabulated hypotheses; no memory hygiene can fix that.

## 3. Live defects found during this review (fix-now list, independent of any redesign)

1. **Baseline ratchet, ACTIVE NOW**: trial 775 (config-neutral seed_batch) auto-raised the T1 baseline to the all-time noise maximum 1.953 (`logs/autopilot.log:115569`; `baselines_by_tier['1']=1.9534…`). The modal honest outcome (1.814) is now a −7.1% "regression" → the −5% gate will fail ~half of honest trials, feeding spurious reverts/rollbacks/blacklist entries from today forward. `update_baseline` is monotonic-only (`safety_gate.py:935-941`). Until the sequential rule exists: require reproduction-cluster median (k≥3) for any baseline raise, or at minimum decay/refresh the baseline as a rolling median of passed trials.
2. **Double `gate.check()` per mutation/structural trial** (`actions.py:349/400/446/489` + `autopilot.py:2308`, same gate instance): MAD history double-append, `consecutive_failures` double-increment → rollback fires after 2, not 3.
3. **T0 `[:10]` slice** (`eval_tower.py:713`): the 28 harder sentinels added 2026-04-09 *to prevent saturation* are dead config; T0 history is `[3.0, 3.0, 3.0]` — a saturated gate costing wall time with zero discrimination.
4. **Flag experiments don't reach the system under test** (cross-cutting; full detail in findings-02 §3): `POST /config` mutates the `Features` singleton of **one of six** uvicorn worker processes (`config.py` → `set_features`; module-global per process; `orchestrator_stack.py:1210` workers=6; `structural_lab.py:404-412` posts once). Every `structural_experiment` flag trial has been evaluating a ~1/6-mutated system. Combined with §1's noise floor, the entire flag-toggle species' historical results are unmeasurable. This also retroactively explains the STM's serene parade of within-noise "confirmed" flag toggles.
5. **Throughput floor dead** (§2.2) — and with it the in-gate host-throttle remediation path.
6. **Self-criticism ±0.02 threshold** (`self_criticism.py:66-89`) — relabel as "no measurable change" below 1 quantum; stop feeding the planner a 58%-revert failure narrative about a flat config.
7. **Strategy-store frontier write leak** + **unfiltered distill input** (§2.4) — one-line gates each.

## 4. Decision gates (adopt vs hold)

- **Adopt the per-question ledger + paired tests immediately, unconditionally** — zero inference cost, pure win; it is also the prerequisite for every other gate below being measurable.
- **Adopt sequential keep/promote** when: ≥2 weeks of per-question vectors exist AND a replay shows ≥30% of historical keep/revert decisions flip under McNemar — (prediction: they will; if <10% flip, your current gates are better than this review thinks and you should hold).
- **Adopt runtime event-sourcing** when: the next incident requires touching ≥2 stores to clean, OR the dual-write drift check (`reconstruct_archive_from_journal_rows` vs live archive) shows any divergence. **This check was run during this review (2026-06-12, read-only): tier-1 frontiers match exactly ({256,610,736,775,776}); tier-2 DIVERGES — live archive holds {363}, journal reconstruction yields {363, 367}.** Trial 367 is frontier-worthy by the shared policy but absent from the runtime archive. The gate condition is met; the event-sourcing case is no longer hypothetical.
- **Adopt narrative-regeneration** in stages: gate the two leak paths now (one-liners); kill session-resume now (you already half-did); rebuild STM as a generated view when the ledger lands; split program.md this month — it is pre-statistical work and the planner reads it 50×/day.
- **Hold on**: any further gate/guard/sanitizer additions to the current pipeline (you have ~12; each new one is evidence the architecture is wrong), eval-tower verification work (EV-3/4/5 calibration) until the instrument itself is re-powered — calibrating an underpowered instrument is polishing the wrong lens.

## 5. What this resolves (the failure modes, named)

- *Scrub-resistant narratives* → impossible by construction (regeneration + provenance check at read).
- *Multi-store purge incidents* → one supersession event + recompute.
- *Gate oscillation (over-exclude wins ↔ over-admit noise)* → dissolved: sequential evidence accumulation replaces the single-shot significance argument the MAD filter and the ratchet are both losing.
- *Planner noise-mining and fixation loops* → the planner cannot be rewarded for unmeasurable effects, and its constitution finally describes the real instrument.
- *Operator trust* → an auditable ledger with policy versions turns "do we trust the frontier?" from archaeology into a query.
