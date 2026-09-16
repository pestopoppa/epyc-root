# 2026-09-16 — sub-cleanup (governance subagent)

Scope: stale checkboxes/rows (Part 1), operator-queue close/decision packages OP-3 / OP-19 / OP-20
(Part 2), `index_state.py --check` (Part 3). No inference, no process management, no commits.
Index rows are PREPARED here only; the owning main session applies them (CLAUDE.md ruling (b)).

## Part 1 — stale checkboxes

### Boxes ticked this session

| Handoff | Box | Evidence |
|---|---|---|
| `cpu-decode-roofline-program.md` (INF-70) | WRAP-10 | research `fc8c44de` (2026-09-14, on `origin/main`; the LOCAL research checkout is behind and does not show the files): adds `scripts/lib/qwen38_flash_next_recipe.py`, its test, `scripts/benchmark/serve_qwen38_flash_next.sh`, `scripts/lib/build_locked.sh`; Makefile:107 `PYTEST_SMOKE += ...`; recipe exports `GGML_NOHUGEPAGE_PROCESS: "1"` |
| `autopilot-sequential-allocation.md` (EVL-04) | SEQ-B2 | orchestrator `4c220b11` (2026-09-14, on `origin/main`): `refutation_record` written at `safety_gate.py:1847`; `refutation_of` at `readjudicate_sequential_candidates.py:107`; axis split `f2ad030e`; 17 tests |
| `learned-routing-controller.md` (RTG-15) | EPD-3-R2, EPD-3-R3 | orchestrator `9096a600` (2026-09-14, on `origin/main`): `embedder.py:32,261` `_serialize_task_ir` → `embedding_text_for`; `seeding_injection.py:81`; `seed_loader.py:482`; `tests/unit/test_one_embedding_convention_writers.py` |

### Already ticked (verified, no edit needed)

| Handoff | Box | Evidence |
|---|---|---|
| `numa-topology-cutover-resume-20260730.md` (INF-45) | P0-1 (`[x]` CLOSED 2026-08-24) | orch `5f08875a`, `6919b885`; root `a9b02275`. Caveat: closed as "gated work + fixture fixes"; 16 full-suite failures remain attributed to P0-0 / E8-era guard |
| `multimodal-pipeline.md` (INF-41) | S-9 (`[x]` 2026-08-12) | orch `cba55d49`; `start_tts` at `orchestrator_stack.py:2668`, `launch_manifest.yaml:101` `tts: 9002`. Stale prose remains at :115/:286 ("no start_tts()") and numa-topology :847 duplicate P0 |
| `llama-cpp-dsa-contribution.md` (INF-31) | D4 (`[x]` 2026-08-13) | root `c49a37c4` (diagnosis; progress/2026-08/2026-08-13-auditor.md). Box text itself leaves the exact `dequantize_V_bf16` line + upstream filing open |
| `qwen38-27b-replace-qwen36.md` (INF-60) | stack-change regen (`[x]` 2026-08-21) | orch `7483d7fb`, `0d145f4f` (first fully green check), `96498c3d` |
| `fable5-window2-findings-05c-...md` (EVL-48) | L14 (`[x]` 2026-08-14, DEAD) | root `4b6434a9`; research `scripts/kernel_rnd/autokernel/loop/seeds/negatives.json:56` |
| `eval-tower-architecture-audit-2026-07-20.md` (EVL-12) | A2 (`[x]`, CLOSED 2026-08-12) | orch `2a41c0bc`, `2416fabe`, `8d729ca1`. **Unowned residue**: bare `from question_pool import ...` shadow imports still at `seed_specialist_routing.py:998,1163`, `seed_specialist_routing_v2.py:920` |
| `shape-keyed-contention-gating.md` (RTG-35) | `_drive_admit_overlap_probes` stub (`[x]` 2026-08-23) | orch `4dd270ed` (impl), `7ac6870d`, `167248df`; real body at `shapekeyed_step2_smoke.py:1154`, called at :1290. Stale prose at :31-35 still calls it a stub |
| `fleet-fanout-measurement.md` (RTG-49) | FM-1 (`[x]` 2026-08-23) | root `3bdc9a84`; `scripts/coordination/fanout_timing.py`; `data/fanout_timing/` |

### NOT ticked

- **RTG-46 "Derive per-node ready/blocked"** (`handoff-index-and-backlog-graph.md:34`) — PARTIAL. The derivation landed
  in root `457abd40` (`index_state.py:451-505`, schema `index_graph.v2` at :600, `compute_ready.py` accepts v1 and v2,
  `tests/test_index_state_readiness.py`). But the box also requires "render blocked nodes distinctly on the :8100
  backlog graph", and `dashboard/static/handoffs.html` never reads `readiness`/`blocked_by` (its :1209 `n.blocked` is the
  blocked-checkbox count). The rendering is the remaining work.
- **INF-70 MEAS-2** (`cpu-decode-roofline-program.md:1002`, not on the list): `build_locked.sh` landed in the same
  `fc8c44de`, but the box also asks to ADOPT it as the standing build idiom. Left for the owner.

## Part 2 — operator-queue packages

### OP-3 — CLOSE package (recommend: delete the row)

Row: `| OP-3 | Zero-inference decision batch — residual dispatch_swarm_fanout items | routing-and-optimization-index.md | 2026-07-14 |`

Every residual of the 2026-07-14 bundle (`backlog-roi-audit-2026-07-14.md:53`; narrowed in
`../archived/master-handoff-index-history-through-2026-08-10.md:108`) is resolved or owned by a handoff with its own non-operator gate:

| Residual | State | Evidence |
|---|---|---|
| `dispatch_swarm_fanout` ownership | **DELETED** | orch `771348c8` (2026-06-16, ancestor of `main`) removes `src/swarm_fanout.py` (def at old :141) + its test; `git grep dispatch_swarm_fanout` in orch HEAD = 0 hits (only the default-off `swarm_fanout` FeatureSpec remains, `src/features.py:211,563`). Ruled delete/defer, not claimed: `routing-truth-restoration.md:30` W6-DECIDE ✅ 2026-07-14; `design-backlog-triage-2026-07-23.md:255` |
| E3 go/no-go | NO-GO/CLOSED | `batched-decode-measurement.md:149` ✅ 2026-07-18 |
| E4 CPU17/CPU18 re-promotions | decided (CPU17 measurement-only reopen; CPU18 gated) | `batched-decode-measurement.md:150` ✅ 2026-07-18 |
| MoE-spec reopen | closed in the 2026-07-18 Lane-B pass | archived history :108 |
| context-folding α-promotion | decided (design variant only; live flip needs held-out validation) | `context-folding-progressive.md:20` CF-2c.1 ✅ 2026-07-14 |
| MathSmith S2 free scan | done; remaining acquisition/conversion is owned | `mathsmith-hc-formalizer-eval.md:108` ✅; EVL-31 row |
| Wilson/McNemar consolidation | landed | `loops-and-dashboards-audit-2026-07-05.md:347` (`src/llm_primitives/stat_tests.py`, A1 2026-07-17) |
| agent-file-compression Phase 5 | measurement-gated, not an operator choice | `agent-file-prose-compression.md:61` (needs ≥95% compliance curves first) |

Stale prose to sweep (non-row, owner's call): `bulk-inference-campaign.md:496` (J14) and
`decision-aware-routing.md:212,214,222` still describe `dispatch_swarm_fanout` in `src/swarm_fanout.py`
as present; DAR-6 is FROZEN (`decision-aware-routing.md:3`), so J14/DAR-6.5 would need to rebuild it.

**Draft diff** — `handoffs/active/master-handoff-index.md`: delete the OP-3 row (no replacement).

### OP-19 — CLOSE package (recommend: delete the row)

Ruling `artifacts/operator/ruling_op19_e8_chain_20260827.json` is tracked on root `main`
(commit `1ee8bd7c`, 2026-08-27, ancestor of HEAD). It covers BOTH halves:

1. **E8 chain retired** — `ruling.e8_chain`: "RETIRED. B9 and B10 close as superseded, not as completed";
   ordinal 418 permanently unadjudicable; replay over the surviving corpus 5,324 re-scored / 0 divergences.
   `autopilot-decision-plane-audit-2026-07-22.md` already carries `[x]` B9/B10 with
   "CLOSED SUPERSEDED 2026-08-27" (:378).
2. **Reseed gate restated** — `ruling.gate` + `gate_scope_after_ruling` + `gates_bind_at_promotion_not_at_discovery`.
   Note it re-anchors to "the current eras" (cpu_bench E9, eval_quality E16) and scopes the gate to
   promotion, rather than literally restating an "E9 reseed"; that is a superset of what OP-19 asked.
   `CURRENT-CAMPAIGN.md:150` carries the restated gate and :147 the retirement banner.

**The "8 further handoffs"**: the ruling's `restatements` field says they "inherit this ruling without
needing individual edits" and names CURRENT-CAMPAIGN.md the single source of truth — so no per-file edit is
owed. Current grep for old-form gate language outside CURRENT-CAMPAIGN / master:
`autopilot-continuous-optimization.md`, `non-inference-backlog.md`, `stale-open-audit-2026-07-18.md`,
`session-bus-thin-dispatcher.md` (no OP-19 pointer); `moe-spec-cpu-spec-dec-integration.md`,
`loop-owned-fleet-implementation.md` (point at OP-19). Optional hygiene only.

**Residual that is NOT an operator item**: `autopilot-decision-plane-audit-2026-07-22.md:223`
`- [ ] E8 RE-ARM (2026-07-26)` (and the E8-successor boxes :298/:306/:311/:316/:410) remain `[ ]` while the
chain is retired; they should be closed SUPERSEDED by the owning session (EVL-03), citing the ruling.

**Draft diffs**
- `master-handoff-index.md`: delete the OP-19 row.
- `research-evaluation-index.md` EVL-03, next action `E8 RE-ARM (2026-07-26)` → 
  `Close E8 RE-ARM + E8-successor boxes SUPERSEDED per ruling_op19_e8_chain_20260827; then next open non-E8 box`.

### OP-20 — DECISION package: one `task_failed` scoring rule for both producers

**Context.** A row that fails for a non-infra reason (HTTP-400 client error, unparseable 200 body, model
error) gets disposition `task_failed` from the shared classifier
(`src/autopilot_core/measurement_guards.py:140-167,252-266,404-439`). The two producers turn that into
different quality numbers, so quality is not comparable across them
(`autopilot-continuous-optimization.md:2194-2203`). Choosing the semantics of a published quality
statistic changes which rows enter a denominator: that is the operator's call.

**Current behaviour (verified 2026-09-16, orchestrator HEAD).** The row's `eval_tower:1339` pointer is stale.
`_compact_question_result` (`eval_tower.py:1372-1378`) only records the disposition.

| Site | infra / scoring_failed | task_failed (non-infra) |
|---|---|---|
| EvalTower `_aggregate` — `scored_results = [r for r in results if not r.error]` (`scripts/autopilot/eval_tower.py:5359`) | EXCLUDED | **EXCLUDED** (a task_failed row always carries `error`) |
| EvalTower CJ-8 per-arm screen, `not r.error` filter (`eval_tower.py:~6937-6955`; its own comment calls the filter a proxy that wrongly drops task_failed) | EXCLUDED | **EXCLUDED** |
| Paired/e-process coercers via `is_quality_admissible` (`eval_tower.py:3337-3390`, `autopilot.py:1464-1495,1645-1664`) | EXCLUDED | WRONG (only for rows that survive the upstream filter) |
| Seeding `_build_role_result` (`scripts/benchmark/seeding_eval.py:374-395`) | `passed=None` → EXCLUDED | `passed=False` → **WRONG** |
| Seeding rewards (`seeding_eval.py:997-1006,1293-1305`, `seeding_rewards.py:452,528,540,558`, `seeding_legacy.py:346-360`) | skipped | `success_reward(False)` |

Note: a `seed_batch` trial's JOURNALED quality comes from `ctx.tower.hybrid_eval()`
(`scripts/autopilot/actions.py:~615`), i.e. the eval tower. The seeding-side WRONG shows up in MemRL
rewards/Q-values and `seeding_*.jsonl` counts. The cockpit already flags this with `OP20_CAVEAT`
(`scripts/autopilot/decision_cockpit.py:86-94,1039-1044`).

**Options**

- **A — non-infra → WRONG, infra → EXCLUDED in both (auditor's recommendation).** Change the eval tower
  only; the seeding path already behaves this way. The eval tower becomes self-consistent with its own
  `is_quality_admissible` predicate and the docstring at `eval_tower.py:2994-3007`.
  - *Tradeoffs:* EvalTower quality drops wherever task_failed rows exist. This is an instrument change, so
    it needs an `instrument_eras.yaml` eval_quality era boundary, and it must not land while a quality
    baseline is being collected (promotion-bound gate, `ruling_op19`). It is honest: a model that returns
    garbage is not "unmeasured". Reversible by revert. Cost ~0.5 day plus tests.
  - *Risk:* a mis-classified infra failure (for example an HTTP-400 caused by our own request builder) now
    scores WRONG. That argues for auditing `infra_failure_reason` coverage first. Today 400 → task_failed
    by design.
- **B — task_failed → EXCLUDED in both.** Change the seeding path (`passed=None`, no reward) and the paired
  coercers.
  - *Tradeoffs:* no eval-tower era break. But it hides real failures: a role that fails more often looks
    better, which is the fail-open the disposition taxonomy exists to prevent. It also throws away MemRL
    negative signal. Not recommended.
- **C — status quo plus the caveat.** No code change; keep `OP20_CAVEAT`.
  - *Tradeoffs:* free, but cross-producer quality stays non-comparable indefinitely, and the eval tower
    stays internally inconsistent (its aggregate excludes rows that its paired stats count as WRONG).

**Recommendation: A.** It is one rule, and it is the rule the shared predicate already encodes. Only one
producer changes, and the change is a measured instrument change with a clean era boundary.
Tie-breaker, if needed: the count of `task_failed` rows in the current-era eval journal (a zero-inference
read). If there are none, A is free.

**Default if no ruling:** C. The caveat stays, and OP-20 blocks any cross-producer quality comparison.

**Implementation sketch for A** (orchestrator):
```diff
--- scripts/autopilot/eval_tower.py  (_aggregate, ~:5359)
-        scored_results = [r for r in results if not r.error]
+        # OP-20: disposition, not `error`, decides admission. task_failed is
+        # quality evidence (WRONG); infra/scoring failures are excluded.
+        # Legacy rows with no disposition keep the old error-based rule.
+        def _admit(r):
+            disp = getattr(r, "disposition", "") or ""
+            if disp:
+                return is_quality_admissible(disp)
+            return not r.error
+        scored_results = [r for r in results if _admit(r)]
+        # a task_failed row must count as not-correct even if `correct` is unset
--- eval_tower.py (CJ-8 arm screen, ~:6944): same `_admit` in place of `not r.error`
--- src/autopilot_core/instrument_eras.yaml / orchestration/instrument_eras.yaml: new eval_quality boundary "OP-20 task_failed admitted as WRONG"
--- scripts/autopilot/decision_cockpit.py:86-94,1039-1044: drop OP20_CAVEAT once the era is live
```
Tests:
- Extend `tests/unit/test_infra_failed_disposition.py:577-590`. The no-disposition row stays error-decided.
  Add: task_failed + error → admitted and counted wrong; infra_failed → excluded.
- Update `tests/unit/test_decision_cockpit.py:273-274`.
- Keep `test_seeding_eval.py:707-722` unchanged; it already pins A for the seeding path.

Order of work: rule → era boundary → change (never mid-baseline).

## Drafted index-row diffs (PREPARED — main session applies)

No handoff in scope is fully complete, so there are no deletions or `completed/` moves. Each row is
re-pointed to its next open item. Only the `Next action` cell changes; ID, Track, Handoff and Deps are unchanged.

**inference-research-index.md**
- INF-45: `P0-1 — fix the 30 net-new breaking tests across 14 files; this blocks the commit` →
  `P0-0 — restore the dropped NUMA_FULL entries in derived stack_priors.yaml (the residual P0-1 failures are gated on it)`
- INF-41: `S-9 — wire start_tts() into orchestrator_stack.py (port 9002 reserved); capability exists, wiring does not` →
  `S-11 — register the Qwen3-TTS GGUF pair and the qwentts.cpp tree in the model manifest/registry (MRG-1); then a real :9002 /v1/audio/speech smoke`
- INF-31: `D4 — root-cause the HIP bf16 LIGHTNING_INDEXER numerical failure (flaky, ERR≈1.0,` →
  `D4 residual — pin the faulty line in the bf16 K-load path (dequantize_V_bf16) and file it upstream against ggml-cuda`
- INF-60: `Registry swap DONE; run stack_change_pipeline regen + stack-change checklist to verify live==config on next start` →
  `DFlash2 selection decision — blocked on np2/4/8 scaling, temp-0 greedy parity and the block-verify dispatch proof (owned under INF-62)`
- INF-70: `CLOSED 2026-09-08: champion = ef81196d5 + GGML_NOHUGEPAGE_PROCESS=1 at launch; next WRAP-10 lands PROD-1's recipe module; OP-40 unruled` →
  `CLOSED 2026-09-08: champion = ef81196d5 + GGML_NOHUGEPAGE_PROCESS=1 at launch; next WRAP-12 — correct the PROD-1 hybrid recipe and build-10221 figure where propagated (OP-40 folded into OP-41 under INF-73)`

**routing-and-optimization-index.md**
- RTG-35: ``Implement `_drive_admit_overlap_probes` at shapekeyed_step2_smoke.py:718 (bridge residual 2 — step-2 smoke drive loop)`` →
  `Tighten the llama-process waiver so it can tell a lineup member from a foreign server; flip the already-implemented enumerate_feasible box (:326)`
- RTG-46: `Work the 3 Prove2Me rows (2026-09-07); OPERATOR still owes the hub_supervisor.sh cron ruling` →
  `Render index_graph.v2 readiness/blocked_by on the :8100 backlog graph (derivation landed); then preserve re-point reasons and the promote-vs-inline rule; OPERATOR still owes the hub_supervisor.sh cron ruling (OP-9)`
- RTG-49: `FM-1 — collect per-subagent start/finish timestamps from Claude Code and Codex transcripts into a durable record` →
  `FM-2 Stage 1 — AdaMAST fixed-catalog grading pilot; FM-4 success/failure oracle gates FM-2 Stage 2`
- RTG-15: `EP-5 — re-run the probe only after the outcome-label defects are fixed` →
  `EPD-1-orig — make outcome updatable after INSERT (EPD-3-R2/R3 landed); then R1 re-embed in an operator window; then re-run EP-5`

**research-evaluation-index.md**
- EVL-04: `SEQ-B2 — wire refutation-counterfactual capture at stop time (safety_gate.py:1528 write-side + readjudicate split)` →
  `Fix E_quality trial starvation (allocation, not calibration); SEQ-B1 joint-vs-advisory rate gate is an OPERATOR decision`
- EVL-12: `A2 agent SCORE-02/XREPO-1/PATH-1 — make module identity deterministic. (PARTIAL ✅ 2026-07-20: ...` →
  `C2 LOSS-1/2 — loader accounting; plus the unowned A2 residue: bare question_pool imports in seed_specialist_routing{,_v2}.py`
- EVL-48: `L14 — KV-quant single-stream long-ctx: dense-Q8 and GDN full-global layers at 64k` →
  `L2 — quantize_q8_1 requant kill (low effort, do early)`
- EVL-03 (from OP-19): `E8 RE-ARM (2026-07-26)` →
  `Close E8 RE-ARM + E8-successor boxes SUPERSEDED per ruling_op19_e8_chain_20260827`

**master-handoff-index.md** (operator queue): delete the OP-3 and OP-19 rows. OP-20 stays; re-point its
stale pointer `eval_tower:1339` → `eval_tower._aggregate:5359`.

## Part 3 — `python3 scripts/handoffs/index_state.py --check`

Run twice, before and after this session's box edits. Both runs exit 1 with exactly **1 problem**:
`FRESHNESS: master index generated block is stale — run without --check`. That is the known stale generated block.
cite-check is clean (325 citations across 11 documents, 0 refuted/conflicted/dangling). There were no
coverage or schema failures. The write mode was NOT run: it rewrites the master index, which belongs to the main session.
