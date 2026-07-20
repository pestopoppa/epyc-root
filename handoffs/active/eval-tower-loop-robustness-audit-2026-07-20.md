# Eval-Tower / Inference-Batch-Loop Robustness Audit (2026-07-20)

**Status: IMPLEMENTATION CHECKPOINT — original read-only audit plus executed Phase 0-3 unblock checklist.**
The original read-only review was triggered by the EV-4 `INFRA_BLOCKED` failure while working the P2
eval-tower entries of `inference-batch-loop.md`; five audits (4 subagent + 1 scoring, all
evidence-backed and independently spot-verified) produced the findings below. The 2026-07-20
follow-up implemented the checked Phase 0-3 agent-fixable items; EV-4 itself remains open.

**Sidecar checkpoint (2026-07-20T19:17Z, EV-4 still open):** the Phase-0 EV-4
unblock reached a real preflight checkpoint. `preflight_gate` now emits a separate
16-char contention topology hash and full registry hash. Fresh attestation
`coordination/inference-batch/attestations/20260720T191355.json` passed for EV-4
CPU roles `frontdoor+worker_general` with
`topology_hash=expected_topology_hash=8c8cfcbb13d2611d`. The prepare-only
`run_batch_entry.py --batch-entry /tmp/ev4-batch-entry.json` preflight reported
`blocking_reasons=[]`, `stack_contract.ok=true`, and `topology.verified=true`
with `live_hash=required_hash=8c8cfcbb13d2611d`. Root coordination verification:
`/mnt/raid0/llm/epyc-orchestrator/.venv/bin/python -m pytest scripts/coordination/tests/test_batch_ledger.py scripts/coordination/tests/test_batch_status_report.py -q`
=> 31 passed. This is not an EV-4 completion signal and does not flip EV-4.

**Cross-links:** [eval-tower-verification.md](eval-tower-verification.md), [inference-batch-loop.md](inference-batch-loop.md), [within-role-placement-state-machine.md](within-role-placement-state-machine.md), [v7-promotion.md](v7-promotion.md).

## Headline (corrected root cause)
The EV-4 failure is **three independent defects stacked**, and the premise that the *kernel* promotion
caused it is **wrong**:
1. **The stale contention matrix is the root** — and it went stale because of the **2026-07-17
   `vision_escalation` NUMA rebind (commit `139ba643`, 5 instances → 1)**, NOT the v7 kernel cutover.
   `topology_fingerprint` hashes only `(cpu_list, port, threads)` (`src/scheduling/contention.py:806-826`),
   so a pure kernel swap cannot move it; a *measured-role NUMA change* did. Reproduced: old shape →
   `df373c79cc4af06f`, live shape → `8c8cfcbb13d2611d`.
2. **The runner silently degraded** (fanout → concurrency=1) and then a **partial serial run was killed**
   leaving a **dirty stack + a decision-grade-looking empty result**.
3. **The batch entry itself is mis-pinned + the loop can't resume** it after an infra-block.

**Confirmed production-scope finding:** the same stale matrix has, since 2026-07-17, been silently
degrading **production cross-role concurrency** — `contention_gate` fail-closes background decode to
`QUEUE` and foreground to `DEGRADED_ALLOW` whenever `matrix_health() != OK`, and the shape-aware /
per-region-lock flags are live prod defaults (`orchestrator_stack.py:1648,1659`). (A related claim that
`safety_gate` blocks all v7 baseline writes **did NOT reproduce** — no `_baseline_eligible` symbol
exists; treat as unverified.)

## Constraints (read before touching anything)
- **Scoring semantics = human-amendment-only** (MEASUREMENT.md trust boundary names eval tower + scoring).
  Cluster E is now sequenced through EV-CONF: agent work may prepare the logprob plumbing and an
  operator-signed interim neutralization of the degenerate ECE input. EV-11b closed-bin ECE was
  operator-decided and implemented on 2026-07-20; the remaining operator amendment is the EV-CONF
  real-confidence / scoring-weight decision.
- **Shared tree / live parallel work:** at audit time, `scripts/autopilot/eval_tower.py` and
  `orchestration/contention_matrix.yaml` had parallel-session edits. The checked Phase 0-3 items
  below have since landed in the owning repos; remaining open items still need normal file ownership
  checks before editing.
- **Location note:** the runner + `eval_tower.py` live in **epyc-orchestrator** (not research). A stale
  duplicate exists at `epyc-orchestrator.wt-local-frontdoor/` — reconcile so edits don't diverge.

---

## Cluster A — Contention-matrix staleness (the systemic root) · agent-fixable (recert needs a bench)
| # | Sev | Finding (file:line) | Fix |
|---|---|---|---|
| A1 | ROOT | Matrix stale because the **vision rebind** moved the topology hash (`contention.py:806-826`; commit `139ba643`) — not the kernel. | Frame prevention around *measured-NUMA-role changes* (§H), not kernel promotion. |
| **A2** | **HIGH ✓prod** | Stale matrix **silently degrades live cross-role concurrency** — `contention_gate.matrix_health()` → `matrix_status()`; fail-closed `QUEUE`/`DEGRADED_ALLOW` (`contention_gate.py:131-139,244-252`); flags live. Every bg cross-role decode serialized since 2026-07-17, visible only in a counter. | Treat matrix recert as a **go-live blocker**; surface degraded state loudly, not just a metric. |
| A3 | HIGH | Vision matrix **data is semantically invalid**, not just hash-stale — pairs/n_way/instance_pairs (`contention_matrix.yaml:75-83,165-200,270-298`) describe the old 5-instance shape. A hash-only "bump to 8c8c" would certify **wrong geometry**. | **Re-MEASURE** vision (operator/quiet-window bench), never rehash. Forbid hash-only refresh. |
| A4 | HIGH | **No CI/pre-commit guard** binds the committed matrix hash to live `NUMA_CONFIG`; `test_real_matrix_against_live_numa_config` (`tests/unit/test_scheduling_contention.py:422-429`) **deliberately skips** the hash match; `scripts/validate/check_contention_matrix_fresh.py` is wired into nothing. | Un-skip the test to assert `matrix.topology_hash == topology_fingerprint_for_matrix(NUMA_CONFIG)`; wire the checker into pre-commit + stack-start (§H). |
| A5 | HIGH | The v7 EvalTower unblock certs are **uncommitted** (`M contention_matrix.yaml`), **role-narrow** (frontdoor+worker only), and **expire ~2026-08-19** (`eval_tower.py:630`) → a `git checkout` drops back to concurrency=1; a deferred re-break is built in. | Commit the certs (after A3 re-measure); lint that live topology is covered by a fresh hash or fresh cert; alert before expiry. |
| A6 | MED | Age-staleness keys on **file mtime** not the YAML `measured_at` (`contention.py:333-338`) → a cert append or `touch`/checkout resets the 30-day clock, masking an old measurement. | Compute age from `measured_at`. |
| A7 | MED | The **seeder** reads the matrix **unguarded** (`seeding_eval.py:141-147`) for background wave-pack admission, placement-blind → stale "allow" over-admits. | Gate wave-pack on `matrix_status==OK`/fresh cert; fail closed for bg when stale. |

## Cluster B — Runner robustness (`eval_batch_serving_evaltower_window.py` / `eval_tower.py`) · agent-fixable
| # | Sev | Finding (file:line) | Fix |
|---|---|---|---|
| B1 | HIGH | **Killed run leaves the stack dirty** — no `try/finally`, no signal handler, `run_eval_arm` catches `Exception` not `BaseException` (`:217`); rollback (`:393`) is skipped on SIGINT/kill → API stuck `eval_batch_serving=1` + warm `:18070`, no `summary.json`, poisons the next `--apply`. | Wrap activation→arms→rollback in `try/finally`; SIGINT/SIGTERM handlers → same rollback; write partial `summary.json{status:interrupted}`. |
| B2 | HIGH | `--min-eval-concurrency` guard is **opt-in (argparse default 1)** (`:803-808`) → default `/loop` invocation silently serializes; `_eval_concurrency` (`eval_tower.py:747-763`) fails closed to `1` on stale/exception/fleet-down with **no distinguishing reason**. | Require explicit `--min-eval-concurrency` OR `--allow-serial` for any `--apply`; have `_eval_concurrency` return a **structured reason**. |
| B3 | HIGH | **Degenerate/empty eval → `decision_grade=True, rc=0`** — `eval_t1` *returns* an `n_questions=0` result (`eval_tower.py:2454-2457`); `decision_grade` (`:402-412`) never checks `n_questions>0`. Feeds the rlvr scoring (Cluster E). | Gate `decision_grade` on `n_questions>=expected` AND `n_scored>0`/`reliability>0`; degenerate → blocker `rc=75` (pair speed with a garbage check). |
| B5 | MED | Fanout certified against **wrong role** — `AUTOPILOT_EVAL_BOTTLENECK_ROLE=frontdoor` (`:754`) but calibration forces traffic onto `worker_general` (safe-N=1) → over-subscription. | Resolve concurrency against the **forced role(s)** actually receiving traffic; take min across roles. |
| B4/B6/B7/B8/B9 | MED | B4 TOCTOU guard-time vs eval-time concurrency, no reconcile (`eval_tower.py:1805`). B6 tier path skips the live-stack contract check (verifier-only, `:581`). B7 **unbounded wall time** — serial branch has no no-progress timeout (`:1817-1841`) → *why it had to be killed*. B8 `e2_eval_driver_ab.py:504-527` **always exits 0** even on `blocked`/`incomplete`. B9 no idempotency preflight for a dirty frontdoor; `:18070` shared with E2 (`e2…:473`). | Reconcile actual vs min concurrency; run the contract gate in `build_report`; add an overall wall budget + serial no-progress timeout; non-zero exit on blocked/incomplete; detect/reclaim a stale frontdoor. |
| B10-12 | LOW | Misleading blocker text (always blames the matrix); guard is floor-only (env override beats the live-safe cap → over-subscribe); test gaps (no interrupt/rollback, no default-1, tests lock in B3). | Surface real reason; validate against live-safe cap; add the missing tests. |

## Cluster C — Preflight / gating · agent-fixable
| # | Sev | Finding (file:line) | Fix |
|---|---|---|---|
| C1 | HIGH | **The real killer is caught by no gate** — matrix freshness is only checked by `preflight_gate.check_contention_matrix_fresh` **and only on reload** (`LOOP_PROTOCOL.md:16`); EV-4 ran on the resident stack (no reload) → skipped; the entry even declares `contention_matrix: not_required` while being a fanout entry (`manifest.yaml:1435`). | Make matrix-freshness + topology-cert a **first-class precondition for every `*_eval_fanout` entry regardless of reload**; forbid `contention_matrix: not_required` on fanout entries at compile time. |
| C2 | HIGH | **health_check.sh false-positive** — 500 G session-init threshold (`:53`) mis-applied to a batch run needing a few MB, + a `/tmp/claude` mountpoint check (`:66`), both collapse to `exit 1` (`:168`) → `preflight_gate` `health_ok=False` → **every attestation fails** → override-fatigue. (Correctly checks `/mnt/raid0`, not a wrong mount. Doc-drift: `LOOP_PROTOCOL.md:17` wrongly blames a "security-audit step".) | Split batch vs session-init thresholds (`--profile`); make `/tmp/claude` advisory in batch context. |
| C3/C4/C5 | MED | C3 no advisory-vs-blocking **exit-code separation** → mask-everything overrides. C4 `host_health.py --remediate` uses **unsafe bare `drop_caches`** (`:415`), not `flush_cache_with_pause` (`:602`) → single-NUMA-node page pinning, depressed baseline (LOOP_PROTOCOL:14 prescribes the unsafe one). C5 `autopilot_precondition_gate.py` + the "mandatory dry-run" `run_batch_entry.py` are **built-but-unwired / nonexistent**. | Exit codes 0/1/2; point `--remediate` at the safe flush; wire the C2 gate into pick-next or delete the dead reference. |
| C6-C9 | LOW | C6 quiet-window **TOCTOU** (no lease). C7 throttle gate keyed on the efficiency *floor* → boost-clock loss invisible. C8 live-affinity **asserted not verified** on no-reload. C9 (**unconfirmed**) preflight hashes `sha256(registry yaml)` 64-char vs the runner's 16-char live-topology hash — two schemes, so a "matching" pin gives false assurance. | Short batch-loop lease; document/relax; verify affinity on no-reload; reconcile the two hash schemes (ties to D4). |

## Cluster D — Entries + ledger integration · agent-fixable
| # | Sev | Finding (entry / file:line) | Fix |
|---|---|---|---|
| D1 | **CRITICAL** | **`INFRA_BLOCKED` is a permanent wedge** — `pending()` only re-picks `READY` (`batch_ledger.py:77,291`); no `INFRA_BLOCKED→READY` transition exists; `retry_policy` is declarative-only; and 3 modules disagree (`batch_status_report.py:63` lists it "eligible" while `pending()` never returns it). Same for stale `RUNNING` after a crash. | Make `pending()` re-eligible `INFRA_BLOCKED`/stale-`RUNNING` under `retry_policy`, or add an explicit requeue that appends a `READY` row; unify the 3 eligibility sets. |
| D2 | HIGH | **EV-11 `also_flips` targets the wrong item** — `#RE-3` (review-finding suite, `backlog-roi-audit…:17`) instead of `#RE-1` (the math rebaseline, `:15`). A clean pass **falsely completes RE-3** and leaves RE-1 open. | `#RE-3` → `#RE-1`. |
| D3 | HIGH | **EV-4 has no checkbox anchor** — the handoff has only prose; `flip_checkbox` will raise, but the compiler's **loose substring resolver** (`compile_inference_batch.py:213`) matched `"EV-4"` in `**Status**` prose and recorded `resolved:True` (false assurance). Same defect resolves EV-11c to prose L411 not the real L412. | Add a real `- [ ] **EV-4` checkbox (or repoint `provenance.checkbox`); make the compiler validate with the **strict flip anchor**, not a substring. |
| D4 | HIGH | **EV-4 topology pin is wrong format AND value** — `4320d9b2…` (64-char) vs live `8c8cfcbb13d2611d` (16-char); every other entry uses the 16-char v6 `df373c79…`; schema types it as a bare string with no pattern (`inference_batch.schema.json:173`). Propagated from the `COORD-v7-promotion` row. | Repin to the certified v7 **16-char** hash; add a schema `pattern` so format drift fails compile. |
| D5 | HIGH | **v7 reconciliation incomplete** — only EV-4 was updated; **EV-5/7/8/10a/11/RE-4/H5-RM3 still declare v6 kernel + v6 topology** → they will `INFRA_BLOCK` identically; EV-5/EV-7 `depends_on EV-4`(v7) while declaring v6 (inconsistent across the edge). | Sweep all still-runnable EV entries to v7 era + v7 hash and recompile (the same reconciliation the P4 note demanded, which missed P2). |
| D6-D10 | MED/LOW | D6 `entry_verdict.decide()` can't distinguish a degenerate run from a pass — the gate `rule` text (metric-count / ECE-nondegeneracy) is unenforced (`entry_verdict.py:375-377`). D7 silent `entry_hash` drift after the post-run `--min-eval-concurrency` edit. D8 EV-11b gate is a soft `operator_gate`, not a structural `depends_on` (`pending()` ignores op-gates). D9 the EV-4 infra-block was **never written to `op-bundle.md`** — the recert ask is stranded in the ledger. D10 ledger append has no `flock`; large lines risk non-atomic writes. | Bind the concrete gate rule to a verifier signal before `pass`; warn on entry_hash drift; append the op-bundle row on infra-block; add advisory locking. |

## Cluster E — Scoring semantics · **EV-CONF sequenced; final scoring decision operator-only**
Credit: the EV-11 confidence-proxy insight came from the parallel research agent; verified + extended here.
- **E1 — the confidence proxy is a stub wired into live scoring.** `eval_tower.py` sets `confidence = float(correct)`, overridden only for `code_execution`/`rubric`; math suites are therefore **tautological** → ECE is **0.0 by construction**. Empirically confirmed: **1182/1182 journaled ECE values are exactly 0.0** (both `autopilot_journal*.jsonl` shards). The designed source — **logprob passthrough from `completion_probabilities`** — is stubbed (`:1697` comment; eval-tower-verification.md:38).
- **E2 — it is NOT an inert null instrument (corrects the "blast radius overstated" framing).** `safety_gate.py` has no `ece`, but `rlvr_tiers.py` uses it as a **`required_metric` for tiers 2–3** (`:66,72`) *and* a **score component**: `_calibration_component = clamp01(1.0 − ece)` (`:207`) feeds `0.65·acc + 0.20·rel + 0.10·calibration + 0.05·disc` (`:130`) and `… + 0.15·calibration` (`:151`). With ECE pinned to 0.0, **calibration is a constant 1.0 — a phantom max-signal worth 10–15 % of every RLVR tier score** that gates autopilot promotion.
- **E3 — the recommendation.** The EV-11b "open vs closed top bin" question is **downstream of and moot until** confidence is real. Flipping the binning alone ships a still-degenerate metric and burns an era-label. **Correctly-posed order:** (1) under EV-CONF, land logprob passthrough (`completion_probabilities → confidence`) and, with operator sign-off if scoring weights are touched, neutralize the degenerate ECE/AUC input as observation-only until confidence is real; (2) *then* the operator settles the binning against the `:2068` tripwire's measured 0.15–0.40 claim (which itself only bites where confidence decouples from correctness — code_execution/rubric — none of which appear in the 1182 math records).

## §H — Change-hardening (the operator's ask, retargeted)
The prevention is **not** kernel-promotion-specific — it's **any change to a measured NUMA role's shape**:
- **H1 — bind the matrix to the live topology, loudly.** (a) Un-skip `test_real_matrix_against_live_numa_config` so `matrix.topology_hash == topology_fingerprint_for_matrix(NUMA_CONFIG)` is asserted in CI; (b) wire `check_contention_matrix_fresh.py` into pre-commit **and** into stack-start `preflight_gate.attest` as a **hard** gate (not `observation_only`); (c) recert = **re-measure** changed roles, never a hash bump (A3).
- **H2 — promotion/change-routine step.** In `v7-promotion.md` (and any future `-vN`) add a **"recertify topology-dependent artifacts"** gate before promotion is declared done: enumerate + refresh (i) the contention matrix, (ii) placement caps, (iii) every batch entry's `required_topology_hash` pin. A kernel promotion is one *caller* of H1; the 2026-07-17 vision rebind is proof the trigger class is broader than kernels.

## Executable fix checklist (priority order)
> **Ownership (operator, 2026-07-20):** the **inference-batch-loop session (parallel codex agent) owns all loop/inference/runner files** — `coordination/inference-batch/*`, the loop tooling (`batch_ledger.py`, `compile_inference_batch.py`, `entry_verdict.py`), `eval_tower.py`, the runner, and `contention_matrix.yaml` — and executes **Phases 0–3 + the A3/A5 bench**. The **audit author owns only the non-loop epyc-root mechanisms**: the health_check `--profile` (✅ landed) and the CI matrix-hash guard (H1). Tags below — **[loop]** parallel agent · **[loop·op]** parallel agent + operator (bench / MEASUREMENT) · **[mech]** non-loop mechanism (audit author). Flip a box only when the fix lands *and* its Verify passes.

### Phase 0 — Unblock the loop
- [x] **[operator] A3/A5 — re-measure `vision_escalation` + regenerate the v7 matrix, then commit it.** ✅ 2026-07-20 — `scripts/server/contention_matrix.py run` re-measured 15 live v7 production-role pairs on topology `8c8cfcbb13d2611d`; canonical `contention_matrix.yaml` now validates fresh with 15 pairs / 6 same-role entries / 0 unknown pairs. The live recert artifact is `epyc-orchestrator/data/contention_matrix/v7-live-recert-20260720T180916Z/`.
- [x] **[agent] D1 — break the `INFRA_BLOCKED` wedge.** ✅ 2026-07-20 — `batch_ledger.pending()` and `batch_status_report.py` now share retry-policy pickability for `INFRA_BLOCKED` / stale `RUNNING`; post-recert verification shows latest EV-4 row remains `INFRA_BLOCKED` but EV-4 is eligible again via policy, not via a fake checkpoint.
- [x] **[agent] D4 — repin EV-4 `required_topology_hash`** to the certified v7 **16-char** hash + add a `pattern` to `inference_batch.schema.json:173`. ✅ 2026-07-20 — EV-4 pins `8c8cfcbb13d2611d`; schema rejects non-16-char hashes; manifest compile passes.
- [x] **[agent] D5 — sweep EV-5/7/8/10a/11/RE-4/H5-RM3 to v7 era + v7 pin** (`entries/20-eval-tower.yaml`); recompile. ✅ 2026-07-20 — the named EV/P2 rows are era-consistent on `production-consolidated-v7` + `8c8cfcbb13d2611d`; fanout rows require the v7 recert matrix.

### Phase 1 — Entry / ledger correctness [agent]
- [x] **D2 — `also_flips` `#RE-3` → `#RE-1`** on EV-11 (`20-eval-tower.yaml:619-620`). ✅ 2026-07-20 — `sources.lock.json` resolves EV-11's `also_flips` to `backlog-roi-audit-2026-07-14.md#RE-1`.
- [x] **D3 — add a real `- [ ] **EV-4` checkbox** to `eval-tower-verification.md` (or repoint `provenance.checkbox`) AND make `resolve_checkbox_refs()` (`compile_inference_batch.py:213`) use the **strict flip anchor**, not substring. ✅ 2026-07-20 — EV-4 and EV-11c each resolve to exactly one unchecked checkbox anchor in `sources.lock.json`.
- [x] **D9 — append the op-bundle row** for the EV-4 matrix-recert ask (`op-bundle.md`) per `LOOP_PROTOCOL.md:33`. ✅ 2026-07-20 — `EV-4-v7-contention-matrix-recert` is present in the operator bundle.
- [x] **D6/D7/D8 (med)** — bind the concrete gate `rule` (metric-count / ECE-nondegeneracy) to a verifier signal before `entry_verdict.decide()` emits `pass`; warn on `entry_hash` drift at pick-next; document EV-11b as a soft (non-structural) op-gate. ✅ 2026-07-20 — `entry_verdict.decide()` now refuses EV-4-style PASS unless metric completeness and non-degenerate confidence/ECE signals are supplied, downgrading binary `float(correct)` proxy evidence to the marginal branch when present; `batch_status_report.py` emits `entry_hash_drift` warnings for structurally eligible entries whose latest ledger row was recorded against a different manifest hash; `op-bundle.md` marks the exact `EV-11b-ece-binning-decision-recorded` gate satisfied while noting it remains a soft operator gate, not a structural dependency. Verify: `scripts/coordination/tests/test_entry_verdict.py`, `test_batch_status_report.py`, `test_batch_ledger.py` (55 passed); full coordination suite 117 passed; manifest validate 52/52.

### Phase 2 — Preflight / gating [agent]
- [x] **C1 — make matrix-freshness + topology-cert a precondition for every `*_eval_fanout` entry regardless of reload;** forbid `contention_matrix: not_required` on fanout entries at compile time. ✅ 2026-07-20 — compile lint rejects `eval_fanout` + `contention_matrix: not_required`; `run_batch_entry.py` blocks stale fanout matrices in preflight.
- [x] **[mech] C2/C3 — health_check.sh `--profile batch`** — ✅ landed `940522a8` (2026-07-20): batch profile relaxes the raid floor 500 G→20 G + demotes `/tmp/claude` to advisory; session-init unchanged; bad profile → exit 64; empty-df guarded. Verified batch→exit 0, session-init→exit 1. ✅ 2026-07-20 follow-up: `preflight_gate` now calls the root batch profile, keeps contention-matrix freshness hard-gated, and resolves v7 quarter live role ports from `NUMA_CONFIG`; role-scoped EV-4 preflight passes for live frontdoor/worker quarters.
- [x] **C4 — point `host_health.py --remediate` at `flush_cache_with_pause()`** (`:602`), not bare `drop_caches`; fix `LOOP_PROTOCOL.md:14`. ✅ 2026-07-20 — the CLI remediation path now uses pause + `drop_caches` + NUMA-interleave rewarm; `LOOP_PROTOCOL.md` names `health_check.sh --profile batch` and the safe remediation sequence. Verify: `tests/unit/test_host_health_pause_around_flush.py` (15 passed).
- [x] **C5 — wire `autopilot_precondition_gate` into pick-next** (or delete the dead `run_batch_entry.py` reference). ✅ 2026-07-20 — the mandatory batch-entry bridge (`epyc-inference-research/scripts/benchmark/run_batch_entry.py`) now imports the root-owned pure gate and blocks when live `autopilot.running` disagrees with `preconditions.autopilot`; entries with `autopilot:any` avoid live probing. Verify: `scripts/benchmark/tests/test_run_batch_entry.py` (32 passed) + root `test_autopilot_precondition_gate.py`.

### Phase 3 — Runner robustness [agent·coord — touches `eval_tower.py`]
- [x] **B1 — try/finally + SIGINT/SIGTERM rollback** so a killed run always rolls back `eval_batch_serving=1` + `:18070` and writes `summary.json{status:interrupted}`. ✅ 2026-07-20 — runner activation is wrapped in rollback-on-interrupt, and regression coverage verifies interrupted runs write non-decision-grade summaries after rollback.
- [x] **B3 — gate `decision_grade` on `n_questions>=expected` + `n_scored>=expected`/`reliability>0`;** degenerate → blocker `rc=75`. ✅ 2026-07-20 — empty/all-error and partially scored verifier/current-arm paths return `decision_grade=False` with degenerate status.
- [x] **B2 — require explicit `--min-eval-concurrency` OR `--allow-serial` for any `--apply`;** `_eval_concurrency` returns a structured reason. ✅ 2026-07-20 — default `--apply` now refuses without an explicit concurrency guard; EV-4 command includes `--min-eval-concurrency 3`.
- [x] **B5/B7 (med)** — resolve concurrency against the forced role(s) actually receiving traffic; add an overall wall budget + serial no-progress timeout. ✅ 2026-07-20 — EvalTower now computes fanout from the actual per-question `force_role` set and takes the minimum safe live cap across those roles; verifier-mode preflight passes its `--roles` set into the same resolver, so `--min-eval-concurrency` validates the roles EV-4 will actually hit. Serial fallback now has a finite batch wall budget and fails remaining questions closed with `eval_wall_budget_timeout`. Verify: `tests/unit/test_eval_tower_concurrency_metrics.py`, `test_eval_batch_serving_evaltower_window.py`, and `test_eval_verifier_mode.py` (81 combined passed with host-health coverage).
- [x] **B13 — EV-4 textual multiple-choice scorer blocker.** ✅ 2026-07-20 — `debug_scorer.py` now accepts configured textual multiple-choice labels such as `expected="incorrect"` with `choices=["correct","incorrect"]`, ranks overlapping textual matches by match end then choice length, and accepts parenthesized expected letters like `(B)` while preserving the legacy A-H letter contract for entries without choices. **Important:** this is a scoring-semantics change, so EV-4 is now ledgered `BLOCKED_PRECONDITION` until the B7 operator-reviewed scorer package signs it off; the interrupted `20260720T191550Z` run is diagnostic-only. Verify: `tests/unit/test_debug_scorer_multiple_choice.py` + `test_debug_scorer_code_execution.py` pass.
- [x] **B14 — `run_batch_entry.py` interrupt result preservation.** ✅ 2026-07-20 — the batch bridge now runs children in their own process group, terminates that group on timeout/SIGINT, and converts `KeyboardInterrupt` during execute into a structured `exit_code=130` result instead of losing the result JSONL path. Verify: `epyc-inference-research/scripts/benchmark/tests/test_run_batch_entry.py` stdlib runner (33 passed).
- [x] **B15 — B1 denominator leg + EV-11b closed-bin ECE.** ✅ 2026-07-20 — EvalTower `_aggregate` excludes errored rows from the quality denominator while preserving total/error observability in `details`, runner arms require full `n_scored` before decision-grade, and `_aggregate` now uses closed-top-bin `stat_tests.expected_calibration_error` with `ece_instrument_era=ev11b_closed_bin_2026_07_20`. Verify: `test_eval_tower_concurrency_metrics.py`, `test_eval_tower_ev11_stats.py`, `test_eval_batch_serving_evaltower_window.py`, and `test_eval_verifier_mode.py` (80 passed).

### Phase 4 — Prevention [agent]
- [x] **H1 — bind the matrix to live topology in CI + stack-start.** ✅ 2026-07-20 — `test_real_matrix_against_live_numa_config` now asserts the committed matrix hash equals `topology_fingerprint_for_matrix(NUMA_CONFIG)`; `preflight_gate.attest` keeps `check_contention_matrix_fresh.py` as a hard gate; the local pre-commit hook also runs the freshness check. Verify: `tests/unit/test_scheduling_contention.py` and live `check_contention_matrix_fresh.py` pass.
- [x] **H2 — add a "recertify topology-dependent artifacts" step to `v7-promotion.md`** (+ future `-vN`): matrix + placement caps + entry topology pins refreshed before promotion is declared done. ✅ 2026-07-20 — `v7-promotion.md` now records the recertification hardening as a checked promotion-routine item.

### Scoring Trust Boundary
- [ ] **Cluster E — scoring → tracked as EV-CONF in [eval-tower-verification.md](eval-tower-verification.md).** EV-11b closed-bin binning is implemented; **[agent]** interim (hold ECE/AUC observation-only so the constant-0.0 stops inflating the rlvr tier score, with operator sign-off before merge if scoring weights are touched) + **[agent]** the logprob-passthrough plumbing (`completion_probabilities → confidence`) remain open; **[operator]** owns the final real-confidence / gating decision.

## Provenance
5 audits, 2026-07-20: runner + contention-matrix + preflight + entries/ledger (4 read-only subagents) +
scoring (parallel research agent, verified here). Load-bearing claims spot-verified against source;
F2a (safety_gate baseline block) and C9 (hash-namespace) flagged **unconfirmed**. Later checked items in the executable checklist record the implemented follow-up.
