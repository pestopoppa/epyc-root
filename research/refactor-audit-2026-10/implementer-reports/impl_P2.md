P2 (stage 1) is finished: all 13 findings are dealt with. 11 are done across 14 commits, B2-11 is skipped because upstream already did most of it, and B2-17 gets no change on the verifier's ruling. All commits are in `/workspace/wt/p2` on branch `wt/p2`; nothing was pushed. On the relayed user question: yes, this ran in the ephemeral cloud container, not on the operator host (`/mnt/raid0` does not exist here).

## Per finding

| Finding | Status | Commit(s) | Net LOC |
|---|---|---|---|
| B2-02 | done (earlier implementer; re-checked green) | 205af0c0 | +71 (src +1, tests +70) |
| B2-03 | done (earlier implementer; re-checked) | 0ea4fd48 | +45 (src +21, tests +24) |
| B2-09 | done (earlier implementer; re-checked) | a390e273 | +50 (src -43, tests +93) |
| B2-11 | skipped-already-fixed (partly) | none | 0 |
| B2-20 | done (earlier implementer; re-checked) | db77016f | -45 (src -61, tests +16) |
| B2-17 | no change (verifier's ruling) | none | 0 |
| B5-01 | done (earlier implementer; re-checked) | 8ff7b9c0, 8e54b286, 22433db6 | +91, -24, +4 |
| B5-M1 | done (earlier implementer; re-checked) | 234fc7cf | +169 (src +66, tests +103) |
| B5-M2 | done | f7aa6691 | +55 (src +8, tests +47) |
| B5-16 | done | ed071de1 | -1 (src -23, tests +22) |
| B5-09 | done | f0093398 | -436 |
| B5-13 | done | ccda07a4 | -141 |
| B5-12 | done | 3c5264e0 | +35 (src +14, tests +21) |
| (test fix, not a finding) | done | 6a15b925 | +12 (tests only) |

- **B2-11:** upstream already split `check()` into pure leg functions with `GateEvidence` (HIL-6 S4); it is now 260 lines. B2-02 removed the closure. I did not do the rest of the proposal: a category-constants module touching 13 files, a `SeqEvidence` signature change and `verdict.legs`. The verifier expects that to add LOC, and it touches files other packages are editing.
- **B2-17:** there is still no producer for the control-attestation fields. The verifier says do not delete the parser. Wiring a producer would mean editing `eval_tower.py`, which is evaluator-fingerprinted.
- **B5-M2:**
  - **Fix:** one new `representative_cluster_key(row)` in `action_identity.py`: the served-config identity, falling back to the action fingerprint when there is none. It is now used by replay, both snapshot-fold sites, the live archive's `upsert_representative` calls in `autopilot.py`, and `safety_gate._prior_frontier_empty`.
  - **Test:** the new test `test_representative_clusters_split_by_served_config_identity` failed before the fix.
  - **Changed expectations:** three tests in `test_gate_frontier_c_and_b.py` now refuse through the earlier rule ("source has 2") instead of rule (b). The outcome is the same refusal; the archive's own cluster now holds 2.
  - **Goldens:** the fixture golden digests are unchanged.
  - **No version bump:** I did not bump `REPRESENTATIVE_REPLAY_STATE_VERSION`. The current-policy prefix check already invalidates any snapshot whose representatives change.
- **B5-16:** `active_eval_quality_era` now returns `invalid_registry` when the winning row has no `id` or no parseable `from`. I deleted both E7 fallbacks and a dead check in `autopilot.py`, and cut the comment in `instrument_era_guard.py` to three lines. The E7 constants are kept as historical pins. Two new tests failed before the fix.
  - Side effect worth knowing: `eval_tower.py`, which I did not modify, now stamps `unresolved/invalid_registry` for a malformed row where it used to stamp active or `empty_era_id`.
- **B5-09:** deleted `src/autopilot_core/attestation_trust.py`, `tests/unit/test_attestation_trust.py` and `scripts/autopilot/telemetry.py`. Nothing in orchestrator, research or root imports them. The root CI readsets that list them check out the orchestrator at pinned commits, so they are unaffected.
- **B5-13:** `src/autopilot_core/__init__.py` is now just its docstring. An AST scan of all three repos found only a test of the re-export itself, which I deleted. Every submodule imports cleanly in a fresh interpreter, and all 20,866 tests collect.
- **B5-12:**
  - **Telemetry:** added an `exclusions.unmeasured_objectives` slot. It counts 85 or 88 rows on the fixture depending on policy. It is merged through tail folds and shown in `src/api/routes/dashboard.html`.
  - **Snapshot labels:** `SEGMENT_SNAPSHOT_POLICY_VERSION` and `journal_snapshot_create.DEFAULT_POLICY_VERSION` go to v2.
  - **Goldens:** the golden test removes the new slot before hashing, so the original digests are re-asserted, not re-captured. A new synthetic test failed before.
- **6a15b925 (test fix):** `test_autopilot_sequential_wiring.py` leaks a module-global promotion-guard provider. That made `test_safety_gate_baseline_eligibility.py::test_reproduced_promotion_uses_representative_median_and_refreshes_frontdoor_speed` fail when run after it, in the base checkout too. An autouse fixture now clears it.

## Tests run
All with `cd /workspace/wt/p2 && CI=true ORCHESTRATOR_MOCK_MODE=1 /workspace/repos/epyc-orchestrator/.venv/bin/python -m pytest -q -p no:cacheprovider -o addopts="" -n 2 ...`:
- **Final combined run** (49 files listed in `/tmp/claude-0/-home-user/2773a866-6e4b-53fa-9304-d5960d8e1337/scratchpad/P2/final_tests.txt`: `test_safety_gate_*`, gate_frontier, journal, snapshot, hypervolume, contracts, recovery, sequential wiring, dashboard pareto/helpers, era, `test_w3e_axis_name_reads`, pareto, others): 924 passed, 3 failed, 1 skipped. The 3 are pre-existing (below).
- **Full golden replay:** `GATE_FRONTIER_FULL_REPLAY=1` on `tests/unit/test_gate_frontier_live_scope.py`: 30 passed.
- **Era suites** (`test_era_stamp_reachability`, `test_autopilot_eval_quality_era_fence`, `test_autopilot_baseline_calibration`, `test_instrument_era_guard_eval_quality`, `test_per_suite_regression_resolution`, `test_e8_quality_baseline_v5`): 138 passed, 12 failed. The 12 failures are identical to the base checkout.
- **Other suites:**
  - `test_journal_supersession_events`, `test_dashboard_helpers`, `test_restart_readiness_report`, `test_autopilot_preflight_audit`, `test_archive_authority_report`, `test_infra_failed_disposition`: 252 passed.
  - `test_sequential_verdict`, `test_autopilot_core_contracts`, `test_multitier_decision`, `test_rlvr_tiers`: 51 passed.
- **Collection:** `--collect-only tests`: 20,866 collected, no errors.
- **Lint:** `ruff check` on every file I changed: clean.

**Pre-existing failures** (each confirmed by running the same ids in `/workspace/repos/epyc-orchestrator`):
- `test_w3e_axis_name_reads.py::test_archive_reads_identical`, params `geometry-2-legacy_4d_v1`, `bt_tiebreak_topk-1-task_rate_4d_v1`, `parent_utility_ranking-2-legacy_4d_v1`: the same three fail in base and are in `orch_baseline2.txt`.
- `test_e8_quality_baseline_v5.py`: 12 tests that need `/mnt/raid0` paths; the same set fails in base.

## For the integrator
- **Expected snapshot drift after deploy:**
  - **What happens:** B5-M2 (identity-keyed representatives) and B5-12 (new exclusions key) both change the archive payload. Any snapshot cut before them will read as `archive_prefix_drift` / `prefix_invalidated` when `journal_snapshot_replay.py --strict --allow-tail-fold --json` is run on the host. The B5-M2 change only shows up where a snapshot holds representatives that carry a served-config identity.
  - **Consequences:** authority falls back to full replay, which is ~0.2-0.5 s after B5-01, and the preflight check still passes. This contradicts the B5-M1 deploy check that readiness must be unchanged.
  - **How it clears:** the next segment-rollover snapshot (v2), or `journal_snapshot_create.py --append` on the host.
- **Deploy (same as B5-01/M1):** the session that owns inference restarts autopilot at a trial boundary and runs `orchestrator_stack.py reload orchestrator` (API only). It also applies the W3 note to `handoffs/active/evidence-plane-event-sourcing-and-narrative.md` covering single diagnostic, journal-scoped cache, bug-tagged tails fold, identity-keyed clusters and v2 snapshots.
- **Edits outside the safety-gate/autopilot_core area:** `src/api/routes/dashboard.html` (B5-12), and `scripts/autopilot/experiment_journal.py` plus `journal_snapshot_create.py` (one-line policy labels). Also `scripts/autopilot/autopilot.py`, `tests/unit/test_gate_frontier_c_and_b.py` and `tests/unit/test_autopilot_sequential_wiring.py`. No `SOURCE_PINS` file was touched, and none of the forbidden or fingerprinted files.
- **Root follow-ups I could not make here:**
  - B5-09: drop the TransitionRecord input branch from `scripts/halo/convert_tap_to_otel.py`.
  - B5-09: fix the OTel row at `wiki/agent-architecture.md:3105`.
  - B5-09: correct the attestation-wiring claims in `progress/2026-06/2026-06-12.md` and `handoffs/completed/running-state-attestation.md`.
  - B5-12: add `unmeasured_objectives` to the exclusions line in `dashboard/static/autopilot.html:1162`.
- **No kernel (llama.cpp) defects** came up in this package.