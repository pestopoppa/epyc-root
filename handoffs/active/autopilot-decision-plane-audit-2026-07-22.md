# Autopilot Decision-Plane Adversarial Audit — 2026-07-22

**Type:** READ-ONLY adversarial audit (operator-commissioned 2026-07-22)
**Target:** the *consumer* layer — the code that reads eval/bench evidence and turns it into keep/revert/promote/keep decisions — in `/mnt/raid0/llm/epyc-orchestrator` (branch `spec-dec-mtp-refresh-2026-06-22`, HEAD `22e32ec2`).
**Instrument context:** the eval tower (the *producer*) just completed a two-day hardening (REL-1 excluded-error rows, hard-fail scorers, journal durability, real logprob confidence, E7 era pool rebuild). This audit asks whether the consumer turns that honest evidence into honest conclusions.
**Method:** every claim verified against actual code (file:line), actual SQLite queries, actual journal/state excerpts. No cited file is in the concurrent-edit flux set (`scripts/server/*`, `src/config/models.py`, `src/registry/stack_priors.py`); no HEAD-vs-worktree reconciliation was needed.

---

## Executive Summary

The decision plane is **structurally strong on the SPEED axis and structurally blind on the QUALITY axis.** The single most important finding is an **asymmetry**:

- **Speed decisions are fully instrument-era-gated and fail-closed.** `pareto_epoch_ts` / `pareto_exclude_before_ts` are set to the E6 (v7 kernel) boundary `2026-07-20T13:30:13Z`; the Pareto archive is reconstructed from the append-only journal with era-exclusion + de-inflation applied; `strict_epoch` **raises** if an active speed era lacks its epoch timestamps (autopilot.py:5889-5890); and a `frontier_rerun_required` marker (currently OPEN, `completed_numeric_trials: 0 / min 16`) **forces** current-era numeric trials before the frontier can be exploited (autopilot.py:3430-3466). The Pareto archive also has a clean single source of truth: the state cache is torn down and re-derived from the journal fold ("journal fold is authoritative," autopilot.py:5907-5931).

- **Quality decisions have NO era fence at all.** The sequential-promotion e-process reads journal evidence filtered only by `core_id == "core_v1"` — a hardcoded constant (planner_evidence.py:23), not the live instrument era — with **no timestamp / era / `pareto_exclude_before_ts` / protocol filter** (autopilot.py:2846-2921, planner_evidence.py:103-123). `active_instrument_eras` contains only `autopilot_speed`/`cpu_bench`, **no `eval_quality` entry**. `quality_history` / `quality_history_by_tier` in state are **bare float lists with zero provenance** (defect #4 in its purest form). The fail-closed `instrument_era_guard.py` (scope `autopilot_quality`) exists but is **not imported by autopilot.py / safety_gate.py / actions.py**.

This matters **now, imminently**: the journal tail is trial 1437 @ `2026-07-16` (all pre-E7); state was last written `2026-07-21 09:19` (before the E7 boundary `2026-07-21T10:30`). The live EV-11c eval is producing the **first post-E7 quality evidence**. The next quality promote/revert that ingests it will pool a post-E7 number (79k/41-suite pool, B7 scorer) with pre-E7 `core_v1` baselines (21-suite, laxer scorer) into the **same** anytime-valid e-process wealth — exactly the contaminated-mixture the SEQ-1 provenance comment (autopilot.py:2860-2864) warns accrues wealth anti-conservatively.

The consumer's other failure-modes are **well-defended**: pause works (historical no-op fixed), the journal writer is durable (flock+fsync+torn-tail quarantine), the live decision loop and safety gate read all journal shards via the canonical helper, the meta-action loop is re-enabled with a two-depth guard, and every broad `except` in the promotion path fails **closed** (refuses to promote). The residual risks are the era-blindness above, a **HIGH** rewind/restore coverage gap (episodic vector store can silently desync; two live decision-gating stores are not purged), two **MEDIUM** journal-reader bugs in observability/preflight tooling (not the live loop), and a set of **inert derived-state mechanisms** (empty validity table, empty content-hash table, blind diversity guardrail).

**Lineage verdict (headline):** derived-state lineage **IS present** — 100% of strategy rows carry `created_at`, 99.9% carry `source_trial_id`, and 100% of journal rows carry `timestamp`, all mappable to the dated boundaries in `instrument_eras.yaml`. **Era-triage is feasible; a scratch rebuild is NOT the only honest option.** The caveat is that *no runtime consumer currently applies* instrument-era demotion to quality/strategy conclusions, and existing rows carry only a *timestamp* era stamp (no per-row content-hash / protocol id), so triage must be done by an offline, timestamp-keyed pass or a new era-aware retrieval filter.

**Findings by severity:** 1 CRITICAL · 3 HIGH · 6 MEDIUM · 5 LOW (plus reassuring counter-evidence noted inline).

---

## CRITICAL

### C1 — Quality promote/revert fires on mixed-era evidence (no era fence on the quality axis)
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

## HIGH

### H1 — Evidence identity is a hardcoded constant that ignores the real era stamp
Sub-finding of C1, called out separately because it is the concrete code defect to fix. The decision-bearing `seq.core_id` is the constant `"core_v1"` (autopilot.py:2921), overriding `EvalResult.core_id`. Combined with the `or DEFAULT` fallback (autopilot.py:2886/2023/2440), the era predicate is **inert**: it neither reflects the live era nor excludes un-stamped rows. Note (verified against live data): the real stamp is **not even present historically** — 0 of 1103 rows with populated `eval_details` carry `core_id` or `dataset_content_sha256`; the eval tower only began stamping them in the E7 hardening, which postdates the journal tail. So going forward the true identity is available in `eval_details` but the consumer discards it. **Severity: HIGH.**

### H2 — Rewind/restore silently desyncs the episodic vector store and skips two live decision-gating stores
Defect signature #1 (no single source of truth across SQLite/FAISS layers) + #2 (silent).

The codified "rewind" is checkpoint/restore in `StructuralLab` (there is no separate `rewind` script; the `*.bak-rewind*` dirs are ad-hoc operator backups). Operator entrypoint `cmd_restore` (autopilot.py:8941-8949) and in-loop auto-rollback after 3 consecutive safety failures (autopilot.py:7850-7883) both call `lab.restore_checkpoint()` (structural_lab.py:147-208). Coverage:

- **Strategy store is SAFE (atomic).** `strategies.db` + `strategy_embeddings.faiss` + `strategy_id_map.npy` are co-located in `repl_memory/strategies/` (strategy_store.py:313-324) and restored as one `rmtree`+`copytree` unit (structural_lab.py:195-205). SQLite and FAISS cannot desync here. AP-22 short-term memory is restore-or-clear (structural_lab.py:186-193). This is the historically-flagged store, and it is correct.
- **Episodic/sessions store is SPLIT-RISK.** Its `episodic.db`, `embeddings.faiss`, `id_map.npy` are three **independent** `CHECKPOINT_FILES` entries (structural_lab.py:39-41) restored file-by-file with copy-**if-present** and **no clear-on-absent, no post-restore integrity rebuild** (structural_lab.py:164-169). Restoring a checkpoint that carries `episodic.db` but not `embeddings.faiss` leaves an OLD SQLite paired with a LIVE FAISS index — rowid↔faiss-id mapping breaks silently. Evidence this happens in practice: `repl_memory/sessions/` is littered with recovery artifacts (`id_map.pre-repair-*` ×7, `id_map.npy.broken-1779368503`, `id_map.npy.bak_pre_erase`, `id_map.npy.wipe-bak-*`).
- **Two live decision-gating stores are NOT checkpointed/purged at all:** `failure_blacklist.yaml` (BLACKLIST_PATH, autopilot.py:198; 20 KB, ACTIVE — gates which actions the planner may re-sample) and `orchestration/optuna_study.db` (454 KB, ACTIVE numeric-swarm study). A restore rolls state back but leaves these forward-dated. (For auto-rollback the blacklist asymmetry is arguably intentional — it appends the failing config before restoring — but for operator `cmd_restore` it is silent and undocumented.)

**Severity: HIGH** (strategy store safe, but episodic store can desync silently and two live gating stores are ignored).

### H3 — `preflight_audit.py` journal reader stops at the first shard gap (JRN-7), and it gates autopilot start
Defect signature #2. `preflight_audit._jsonl_paths` (preflight_audit.py:199-209) for a base-file path uses `batch = 1; while True: if not (…_{batch}.jsonl).exists(): break` — a missing `_2` hides `_3`+ (the exact JRN-7 class the canonical `journal_shards.py` was written to eliminate). Its directory-invocation branch (preflight_audit.py:198) is correctly numeric via `_jsonl_batch_key`; only the base-file branch is buggy, and the default `JOURNAL_PATH` (preflight_audit.py:50/597) **is** the base file. Because preflight gates autopilot start, a shard gap → undercounted trials/coverage → mis-assessed readiness. **Severity: HIGH** (start-gating), reader currently benign only because no gap exists today.

---

## MEDIUM

### M1 — `strategy_validity` and `content_hashes` tables are EMPTY → the AP-28 validity-weighted ranking is inert
Defect signature #2/#4. Live `repl_memory/strategies/strategies.db`: `SELECT COUNT(*) FROM strategy_validity` = **0**, `content_hashes` = **0**. `_validity_score` (strategy_store.py:595-609) returns the 0.5 prior when no row exists → **all 1424 strategies are retrieved at uniform 0.5 validity**, regardless of whether structural_lab later disproved them. `update_validity` (strategy_store.py:510-544) is wired and called (structural_lab.py:874) but has produced no rows in the current store — the advertised "validity-weighted ranking, per-entry staleness" (module docstring) is a **no-op** today. The retrieval-time staleness proxy that DOES fire — `context_hash` (SHA-256 of `model_registry.yaml` + `frontdoor.md` + `worker_general.md`, strategy_store.py:576-593) — is **orthogonal to instrument eras**: E5/E6/E7 (kernel + eval-pool boundaries) do not touch those three files, so a pre-E7 strategy is not flagged stale by config-hash. **Severity: MEDIUM.**

### M2 — `phase_status.py` journal reader sorts shards lexicographically (JRN-6)
`phase_status._journal_shards` (phase_status.py:382) = `sorted(journal_dir.glob("autopilot_journal*.jsonl"))` with **no key** → `autopilot_journal_10.jsonl` orders before `_2.jsonl` once the index reaches two digits. It reads every shard (no shard dropped) but appends rows out of trial order, corrupting any latest-trial/order-dependent logic. Observability/status reporter, not the live keep/revert loop. **Severity: MEDIUM.**

### M3 — Action-local revert gate falls back to legacy-only gating on seq-input error
`_action_gate_check` (actions.py:879-886): `except Exception … return ctx.gate.check(eval_result)`. This disables the sequential path on error (conservative for the ratchet) but means an ephemeral mutation is then judged only by the legacy quality-floor/regression gate — a mutation the seq path would scrutinize can be **kept** if it clears the legacy floor. **Severity: MEDIUM.**

### M4 — Journal `seq.core_id` records the constant, not the produced era; `keep_revert_decision` records INTENT
The journal row (autopilot.py:8366-8407) carries substantial lineage (`trial_id`, `timestamp`, `config_snapshot`, `config_diff`, `parent_trial`, `git_tag`, `metric_schema_version`, full `seq` block), but (a) `seq.core_id` is the constant `"core_v1"`, not the eval-tower era (defect #3, intent-not-realized for the identity field), and (b) `keep_revert_decision` is the **rule-based self-criticism label** (`quality − baseline`, self_criticism.py:76-103), not the realized config-revert outcome or `BaselineUpdateResult.updated`. Realized baseline state lives separately in `autopilot_state.json` (`Baseline.to_state_dict`, `seq_last_promotion_blocked`). A reader that trusts `keep_revert_decision` as realized state must reconcile against a different file. **Severity: MEDIUM.**

### M5 — AP-37 diversity-stall guardrail is inert (blind for ~56 consecutive trials, no escalation)
`meta_optimizer.observe` (meta_optimizer.py:163-165): when `distinct2` or `semantic_embedding_agreement` is unavailable, status = `"signal_missing"`, `trigger = False`. Live `diversity_stall_state` shows `status: "signal_missing"` / reason `"distinct2 or semantic_embedding_agreement unavailable"` for **every** trial 1380-1436. So the diversity guardrail has been blind for ~56 trials with no escalation. It **fails safe** (never falsely recommends a rebalance), but the operator has no signal that a decision-influencing monitor is dark. **Severity: MEDIUM** (guardrail down, but fail-safe).

### M6 — `mutation_graph.db` empty → mutation-outcome priors are absent (silent)
`repl_memory/mutation_graph.db` is 0 bytes; `MutationGraph.__init__` (mutation_graph.py:101-134) `CREATE TABLE IF NOT EXISTS` on connect, so reads of mutation-type × failure-pattern outcome priors return empty with no error. Not checkpointed by rewind (H2), so a state-loss event leaves it empty silently. Low live impact today (the graph is unused), but the planner's mutation priors are silently absent. **Severity: MEDIUM/LOW.**

---

## LOW

- **L1 — `scripts/analysis/corpus_v1/common.py:332`** globs `autopilot_journal_*.jsonl` (trailing underscore) → **drops the base shard** (first 1000 trials) AND sorts lexicographically. Combined JRN-5(inverse)/JRN-6. Corpus-analysis tool, out of the decision path, but a real data-completeness bug.
- **L2 — Dashboard journal reader (`src/api/routes/dashboard.py:2390-2422`)** is a correct local numeric-sorted reader (Class B) but duplicates the canonical `journal_shards.py` logic — drift risk if one is fixed and not the other.
- **L3 — Default-OFF accept gates.** `_skill_efficacy_accepts` returns `True` when its arm is `None` (actions.py:964-965); `_bsv2_accepts` returns `True` when `baseline_result is None` (actions.py:1063-1064) — both admit-all unless `_SKILL_EFFICACY_GATE_ENV` / `_BSV2_ACCEPT_GATE_ENV` are set (actions.py:938-947). A coverage gap, not a silent-permit-on-error.
- **L4 — Killed-trial placeholder** (autopilot.py:5501-5522) does not set `outcome_status` (defaults `"ok"`, experiment_journal.py:250); it carries `quality=0.0` + `pareto_status="dominated"` + `bug_corrupted_by`, and the frontier path additionally requires `outcome_status=="ok"` AND real quality, so it cannot pollute the frontier. Cosmetic.
- **L5 — Stray 0-byte DBs** `repl_memory/strategy_store.db` (top-level) and `repl_memory/strategies/strategies.sqlite` are not read by any code (the live store is `repl_memory/strategies/strategies.db` via `DEFAULT_STRATEGY_PATH`). Harmless clutter, but a future mis-pointed reader would silently get an empty store.

---

## Reassuring counter-evidence (verified solid — do NOT "fix")

- **Pause works** (historical no-op fixed 2026-05-24). The main loop `while not shutdown_requested:` (autopilot.py:6534) re-reads `_EXTERNAL_CONTROL_FIELDS = ("paused","pause_reason","_in_cache_flush")` (autopilot.py:5801) from disk **every iteration** (autopilot.py:6553-6560) and idles on `paused` (autopilot.py:6579-6596); `cmd_pause` writes under the H4 cross-process lock (autopilot.py:8842-8851). **Memory note `feedback_autopilot_pause_broken_use_sigterm` is STALE relative to code.**
- **Journal writer is durable.** `ExperimentJournal.record` (experiment_journal.py:552-583): full line serialized, single `write` under `fcntl.flock(LOCK_EX)` + `flush` + `os.fsync`; torn tail is quarantined to `.corrupt-<ts>` + truncated on next append (experiment_journal.py:369-429); mid-file corruption **raises** `ExperimentJournalCorruptError` (not silently dropped). Rotation is deterministic (`batch = trial_id // MAX_TRIALS_PER_FILE`, MAX=1000) with no lost/double-write window.
- **Live decision loop + safety gate read ALL shards correctly (Class A).** Both build `ExperimentJournal()` whose `_load_existing` iterates the canonical `journal_shards()` (experiment_journal.py:461); `safety_gate.py:284-288` reads `all_entries()`/`supersession_events()` transitively canonical.
- **Pareto archive has a single source of truth.** Speed-axis era params (`pareto_epoch_ts`, `pareto_pre_epoch_speed_factor`, `pareto_exclude_before_ts`) are read from state (autopilot.py:5866-5891) and applied to a **journal-fold reconstruction**; `strict_epoch` **raises** if an active speed era lacks them (autopilot.py:5889-5890); the cached `state["pareto_archive"]` is discarded and re-derived ("journal fold is authoritative," autopilot.py:5907-5931). `frontier_rerun_required` is **enforced**, not just recorded — it forces current-era numeric trials until `min_trials` (16) complete before clearing (autopilot.py:3430-3466); currently OPEN at `completed_numeric_trials: 0`.
- **Meta-action loop re-enabled + guarded, no t188 residue.** Live `consecutive_meta_actions = 0`, `trial_counter = 1438`, no `_meta_halt_reason`. Forced-substitution at N=1 converts a 2nd consecutive meta no-op into a measured `seed_batch` tagged `meta_action_forced_metric_trial` (autopilot.py:4381-4402, records intent-vs-realized); latched pause backstop at N≥5 survives restart via `_EXTERNAL_CONTROL_FIELDS` (autopilot.py:7598-7636).
- **Promotion path fails CLOSED on error.** `verdict.seq is None` → `update_baseline` refuses (safety_gate.py:1797-1809); `_baseline_eligible` `except → return False` (safety_gate.py:1684-1686); `_bsv2_accepts` `except → return False`/block (actions.py:1100-1115); `_seq_candidate_replay_payload` `except → None`. No permissive promote-on-error found. Promotion thresholds are conservative: baseline promotion needs `combined_E ≥ SEQ_PROMOTION_FINAL_CONFIRM_E (100)` AND `delta_ci.excludes_regression` (autopilot.py:2284-2293); candidate confirm needs `E_quality ≥ 20.0` AND `E_rate ≥ 20.0` (sequential_verdict.py:45-56, safety_gate.py:1182-1185); monotonic baseline uses strict `>` (safety_gate.py:1836-1844); near-tie keep/revert → `"unchanged"` (self_criticism.py:93-98); reproduction floor `BASELINE_PROMOTION_REPRO_MIN = 3`.

---

## LINEAGE VERDICT (the derived-state triage question)

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

## Prioritized fix list (file:line targets)

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

## IMPLEMENTATION RECORD — C1/H1 quality-axis era fence (2026-07-22)

**Commit:** `epyc-orchestrator` `14cc929c` on `spec-dec-mtp-refresh-2026-06-22` (not pushed).
Mirrors the praised speed-axis pattern (`pareto_epoch_ts`/`pareto_exclude_before_ts`,
`strict_epoch`) onto the quality axis. **Inert when no active `eval_quality` era is set** —
every pre-existing gate/planner path is byte-identical, verified by 280 targeted unit tests
green (35 new). The CRITICAL C1/F1 blindness is closed before the first post-E7 promote/revert.

### What landed
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

### Era-registry row — NO new row required
The `E7-eval-instrument` row (scope `eval_quality`, `from: 2026-07-21T10:30:00Z`) **already
exists** in `orchestration/instrument_eras.yaml`. The implementation reads it as the source of
truth; the `E7_EVAL_INSTRUMENT_BOUNDARY`/`E7_EVAL_INSTRUMENT_ERA_ID` code constants only cite
that row for the fail-safe fallback and MUST stay in lockstep with it. **No human amendment of
the era registry or MEASUREMENT.md was made or is needed for this fix.**

### What remains (owner action, out of this session's scope)
- [x] **Operator: clear the re-baseline hold (E7).** ✅ 2026-07-23 — reseed operator-applied for
  the E7 era (see master-handoff-index 2026-07-23 note: "era-fenced, reseed operator-applied").
  Original text retained: the hold is fail-closed BY DESIGN — it blocks automated quality
  promote/revert until a post-era baseline exists; reseeding baseline quality values is a
  measurement action across the human-amendment trust boundary.
- [ ] **E8 RE-ARM (2026-07-26) — AutoPilot E8 baseline reseed = the gating task of the post-v8
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
- [ ] **E8 c1 required race/finalizer path** — execute only the protocol-required race/finalizer
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
  - [ ] **Integrate scorer-isolation before deterministic-score replay, then re-run the bounded
    deterministic completion** — reviewed scorer isolation is orchestrator branch
    `codex/debug-scorer-isolation-20260729`, commit `79f3d2f35ddd00d21dc2fab235ff269db7c7dec7`.
    Its private per-invocation workspaces prevent BigCodeBench code-execution collisions. The
    successor replay is branch `codex/e8-bcb190-score-fix-20260729`, commit `8bc6eaa9`; it must be
    integrated second and reviewed against the isolation commit. Do not run new generation before
    deterministic replay of saved outputs is exhausted.
  - [ ] **Resolve the saved-output BigCodeBench score divergence fail-closed** — completion attempt
    `...deterministic_completion_20260729T124832Z` correctly refused admission because ordinal
    `418` / `bcb_BigCodeBench/190` stored `false` while deterministic code scoring returned `true`.
    Classification: the old scorer used shared `/mnt/raid0/llm/tmp` execution state, allowing a
    colliding `test.db`; the stored false has no execution witness. The correction ledger must bind
    source bytes, scorer source hashes, per-row before/after verdicts, and corrected sidecars before
    any new completion run.
  - [ ] **Repair the historical producer-pin and abort-terminalization recurrence before final
    E8 promotion** — independent review found that older producer namespaces can still be selected
    without a runtime `run_seal.json`, and the offline one-namespace terminal bridge does not make
    future producer aborts terminal by construction. Wire the copy-only terminalizer into each
    producer abort epilogue and require a pinned source seal for admission; verify the live
    race-retry publication path is structurally valid before publishing a replacement bundle.
- [ ] **E8 quality baseline reseed/apply** — human-only protocol/source/apply scripts are
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
  The coherence-admission and race-retry atomic-publication instruments are complete; structured
  timeout provenance and final-C1/finalizer inference remain the immediate prerequisites to
  finalization.
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
- [ ] Non-owned audit findings untouched (other owners / other agents' flux files): H2
  rewind/restore atomicity (`structural_lab.py`), H3 preflight JRN-7 reader, M1 validity table,
  M2 phase_status reader, M3 action-local gate fallback (`actions.py`), M4/M5/M6, and the
  SafetyGate/RLVR audit's F2 (`export_rlvr_environment.py`, mid-edit by another agent).

---

## HIGH — H4 (added 2026-07-22): The learned-routing Q signal is an append-only buffer, not Q-learning

Defect signature #4 (a number gating decisions that was never actually learned) + a write-path sibling of **H2** (the episodic store's integrity). Verified read-only against the `20260722T125604Z` snapshot; reproduced with the existing auditor `scripts/analysis/dar_write_path_audit.py` (unchanged, re-run).

### Finding (reproduced)
- **99.695%** of 671,780 routing rows have `update_count = 0`. `store()` inserts a fresh row per observation; `update_q_value` (the TD apparatus DAR-1/2/3 build on) almost never fires.
- **643,874** update_count=0 rows collapse to **3,642** distinct `(objective, action)` pairs — **176.8x** duplication, max **7,889** rows for one pair.
- Rows carrying a learned (moved) Q: **0.305%**; DAR-2 could fire on ≤ **9.74%** (ceiling). The "learned router" is an append-only log.

### Root cause (commit-dated)
The production scorer path `q_scorer._update_routing_memory` (and its escalation sibling) only TD-updates when `routing_decision.memory_id` is **already** set; otherwise it blind-appends via `store()`. But the **sole** production emitter of `ROUTING_DECISION`, `progress_logger.log_task_started` (progress_logger.py:366-377), **never populates `memory_id`** (`ProgressEntry.memory_id` defaults to `None`). So the update branch is **structurally unreachable from the progress-log path** — every scored routing decision falls through to append.
- `git blame`: the `if memory_id: … else: store()` structure is **original to `68df9787`** ("feat: MemRL episodic memory implementation", 2026-01-14) and never changed (only the `temporal_decay_rate` kwarg was added in `b3a5b4da`). **Append-only was the behavior since inception; the TD path was aspirational** — not a later regression that bypassed a working updater.
- The ~2,050 rows that *do* carry a learned Q come from a **different** writer: `score_external_result` (the MemRL/seeding/debug path), which *does* find-or-create by similarity + TD-update. Snapshot confirms: **1,706 / 2,050** learned rows have `context.source == "external"`; the progress-log path contributes ≈ none.

### Fix (implemented, flag-gated OFF by default) — `ORCHESTRATOR_Q_TD_WRITE`
`orchestration/repl_memory/q_scorer.py`: when the append branch has no pre-linked `memory_id`, it now **find-or-updates** the existing `(objective, action)` routing row in place before appending. The "find" (`_find_existing_routing_memory`) uses the FAISS similarity index (fast) then requires an **exact** objective+action string match, so distinct objectives are never merged. TD math is unchanged (`update_q_value`, learning-rate + temporal-decay preserved).
- **`ORCHESTRATOR_Q_TD_WRITE` default OFF ⇒ byte-identical legacy append** (deployment is an explicit operator-boundary flip). Flag ON ⇒ in-place TD.
- The pre-linked-`memory_id` branch and the escalation path are unchanged. **Escalation (`_update_escalation_memory`) has the identical latent defect** (4,382 append-only rows) — left as a scoped follow-up; the routing defect is the audited/migrated one.
- TD math extracted to a pure `episodic_store.apply_td_update(...)` shared by the live path **and** the migration, guaranteeing identical replay math.

### Migration (non-destructive, idempotent) — `scripts/maintenance/consolidate_q_append_only.py`
Chronologically replays the 643,874 append-only rows through `apply_td_update` (reward recovered per row via `r = 2q − 1`, valid for update_count=0), producing **one consolidated Q per `(objective, action)`** — the store the live path would have produced. Verified on a scratch copy: **671,780 → 31,548 rows** (3,642 TD-consolidated + 27,906 passthrough); biggest group 7,889 rows → one row `uc=7888`.
- **Non-destructive**: original `memories` table untouched; results in a new drop-in `memories_consolidated` table + `_q_consolidation_provenance` / `_q_consolidation_meta`.
- **`--dry-run`** (read-only, safe against the live DB) and a hard refusal to WRITE the live sessions store (copy to `/mnt/raid0/llm/tmp/` first).
- **Idempotent**: rebuilds deterministically from `memories` content.
- **Row classes preserved**: `update_count>0` (already-TD-updated, e.g. the external path) and objective-NULL rows **pass through verbatim** — a legitimately-distinct episodic class is not destroyed.
- **FAISS-sidecar consistency (ties to H2)**: the FAISS index / `id_map.npy` are **not touched**. Each consolidated row keeps its group's representative `id` + `embedding_idx`, so its vector + id_map entry stay valid. Collapsed duplicates' vectors become **orphaned-but-benign** — `retrieve_by_similarity` over-fetches and filters by SQLite membership, so an orphaned vector resolves to no row and is dropped. **No new SQLite↔FAISS desync class is introduced** (a later compaction can rebuild a compact index from the consolidated id set).

### Poisoned-row verdict (seeding fix `3bfe2584`) — NOT store-identifiable
The in-band `[ERROR: …]` marker lives in the **answer text**, persisted in seed-run **report artifacts**, not in `episodic.db` (routing rows store only task_type / objective / priority). A 0.0 reward maps to `q = 0.5`, indistinguishable from a legitimately-wrong answer or a neutral default. **Poisoned rows cannot be reliably identified from store data.** Store-side **0.0-reward exposure** (proxy: `source=external ∧ uc=0 ∧ q==0.5 ∧ outcome=failure`) = **7,460 rows**, window **2026-05-25 → 2026-07-16** — an over-set (includes legitimate wrong answers). Excluding all of them would bias Q upward, so the migration does **not** guess: it prints the exposure and offers **`--exclude-memory-ids FILE`** for an operator list derived offline from the artifacts (era-triage decision).

### Deploy plan (operator boundary — NOT executed here)
1. **Migrate first, on a copy.** `cp -r orchestration/repl_memory/sessions /mnt/raid0/llm/tmp/q_consolidate` → `python scripts/maintenance/consolidate_q_append_only.py --db /mnt/raid0/llm/tmp/q_consolidate/episodic.db --dry-run` then without `--dry-run`; inspect `memories_consolidated` + `_q_consolidation_meta`.
2. **Swap** (operator, during a quiesced write window with autopilot/API stopped): rename `memories`→`memories_pre_consolidation` and `memories_consolidated`→`memories` in the **live** `episodic.db` (or re-run the migration against the live copy in place). Optionally rebuild a compact FAISS index from the consolidated id set.
3. **Flip the flag** `ORCHESTRATOR_Q_TD_WRITE=1` and restart the API (so new observations TD-update the consolidated rows instead of re-appending). Order matters: migrate → swap → flag, so the first post-flip write finds a deduplicated store.
4. **Verify after**: `python scripts/analysis/dar_write_path_audit.py` — expect `update_count=0` fraction to fall and the duplication factor to approach 1.0 as new observations accrue; the DAR-2 "rows with learned Q" fraction should climb from 0.305%. Re-run the auditor as the DAR-2 effectiveness re-measure.

### Deliverables / checkboxes
- [x] **Root-cause dated to `68df9787`** (append-only since inception; TD path aspirational) ✅ 2026-07-22
- [x] **Flag-gated in-place TD write path** (`ORCHESTRATOR_Q_TD_WRITE`, default OFF = byte-identical) ✅ 2026-07-22 — `q_scorer.py`, `episodic_store.apply_td_update`
- [x] **Idempotent non-destructive consolidation migration** with `--dry-run` / live-write guard / FAISS-safe design ✅ 2026-07-22 — `scripts/maintenance/consolidate_q_append_only.py`
- [x] **Poisoned-row verdict**: not store-identifiable; 7,460-row 0.0-reward exposure quantified; `--exclude-memory-ids` hook ✅ 2026-07-22
- [x] **Tests** (13): flag-off byte-identical, flag-on in-place TD + math, no cross-objective/action merge; migration replay-equivalence vs `update_q_value`, decay, idempotency, dry-run, exclude, passthrough, live-write refusal ✅ 2026-07-22
- [ ] **Operator: run the deploy plan** (migrate → swap → flag → re-measure) at the scheduled boundary — the live 11h eval is routing through the current store right now; do NOT flip mid-eval.
- [ ] **Follow-up**: apply the same find-or-update to `_update_escalation_memory` (identical latent defect, 4,382 append-only escalation rows).

- [x] ✅ 2026-07-23 **H4 Q-TD-write DEPLOYED**: flag live (845e7492 + reload), migration+table-swap executed (676,463→31,565), snapshot-refreshed audit confirms 1.0x duplication / 17.84% learned-Q. Legacy table + backup retained.
- [ ] **EV-CONF-2 — salient-token confidence source** (filed 2026-07-23): math AUROC 0.40 both arms = geomean anti-discrimination (length confounding). Build answer-token/salient-token confidence; re-baseline math AUROC before any math-domain confidence use. See ESC-7 draft §5.
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
- [ ] **Hermeticize test_dispatch_placement_state_machine.py (filed 2026-07-23)**: the solo-goes-full seam fix (97ce58b8) closed ONE live-state coupling; siblings still read live host lock seams under traffic (observed: a different test flaked once during a live eval, passed on rerun; suite takes 80-97s against live traffic vs mocked-instant). Audit every test in the file for the three-seam patch pattern (active_region_holders + lock acquisitor + held_regions_by_role) and mock all timing waits.
