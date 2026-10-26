**Your question:** yes, this was the cloud session. It ran in a temporary cloud container (4 CPUs, no `/mnt/raid0`), not on the operator's host, and nothing was pushed.

All four findings are done, in 5 commits on `wt/p1` in `/workspace/wt/p1`. The worktree is clean and the scratch test `tests/unit/test_zz_scratch_p1.py` is deleted.

An earlier implementer had left most of the B1-03/B5-02 work uncommitted. Its tests all passed and I mutation-checked it before committing.

**"Mutation-checked"** below means: I made the named change to `scripts/autopilot/autopilot.py` (or the harness), confirmed the matching test fails, and the script then restored the file byte-for-byte.

### Per finding

| Finding | Status | Commits | Net LOC |
|---|---|---|---|
| B1-03 | done | `8a1cf80b` (shared with B5-02), `01776ab4` | +610, +34 |
| B5-02 | done (golden rows left out, see below) | `8a1cf80b`, `bf54c8aa` | +91 for `bf54c8aa` |
| B5-08 | done, with a small change to `autopilot.py` | `fac06621` | +44 (`autopilot.py` +19) |
| B1-15 | done, tests only | `d251d5bf` | +17 |

**B1-03 / B5-02 (`8a1cf80b`)**
- The 14 assertions that read `_run_loop_inner`'s source text, across 8 files, are now behaviour checks or AST checks. Test names and file names are unchanged.
- The loop harness moved to `tests/unit/autopilot_loop_harness.py`. It now records calls and has scripted inputs. It points state, lock, outbox, breadcrumb and blacklist files at a temp dir, and fails the run if the live tree changes.
- Added `tests/unit/test_autopilot_loop_halts.py`: one test for each of the 8 halts.
- Fixed the false comment in `test_autopilot_phase_status.py` that said the loop cannot run in a unit test.
- Mutation-checked, each turning the matching test red:
  - removing the pending-row argument at each of the 3 promotion call sites;
  - adding a save between the promotion decision and the journal write;
  - removing the pre-decision baseline snapshot, or ignoring the reconcile result;
  - always stamping the row "pending";
  - not clearing, or not popping, the served content around dispatch;
  - reordering the guard install, the leakage preflight, the in-flight marker clear and the lineage selection;
  - dropping the run manifest, either reproposal-rate hook call, or the health tracker's failure/success calls;
  - the health branch pausing, exiting, or not publishing its escalation fields;
  - removing each halt's pause latch, in turn.

**B1-03 (`01776ab4`)**
- `tests/unit/test_autopilot_loop_beliefs.py` had 4 more source-text checks, added after the audit. I ported them the same way; each is mutation-checked.
- `grep -rn 'source.index("def _run_loop_inner\|getsource(autopilot._run_loop_inner' tests` now returns 0 hits.

**B5-02 (`bf54c8aa`)**
- Added `tests/unit/test_autopilot_loop_lifecycle.py`:
  - a 3-trial run that checks trial counter, failure count and quality history carry over, plus the plot and checkpoint timing;
  - a paused loop polls without dispatching;
  - rollback after repeated failures;
  - a blacklisted action is journaled as invalid and never dispatched.
- Each case is mutation-checked.
- Golden journal-row JSON files were deliberately left out. Row contents are already pinned by the field-level checks, and whole-row snapshots would break on any new field, the same brittleness this work removes.

**B5-08 (`fac06621`)**
- New function `_is_clean_trial_representative()` in `autopilot.py`. The loop calls it, and so does the test copy of the loop (`Loop.trial` in `test_gate_frontier_c_and_b.py`). That copy used to work out frontier admission itself and had already drifted from the loop.
- New test `test_loop_admits_only_clean_passing_measured_config_trials` runs the real loop on 6 cases.
- Behaviour is unchanged. Before the function existed, the 29 tests that use the copy failed as expected.
- Mutation-checked: dropping each condition (exclusion, config identity, verdict, rate) and passing an empty exclusion at the loop's call site each turn tests red.

**B1-15 (`d251d5bf`)**
- The leak into pytest is contained by the harness (from `8a1cf80b`). It captures the loop's SIGINT/SIGTERM handlers, and afterwards removes the leakage observer and clears the promotion-guard provider.
- The new test checks the loop did install all three and that none survives the run. Removing either the signal capture or the provider reset turns it red.
- The audit's proposed fix in `autopilot.py` (undoing the hooks at shutdown) was not done, because this stage is tests-only. The daemon exits right after the loop, so production behaviour is unaffected.

### Test commands and results
All with `cd /workspace/wt/p1 && CI=true ORCHESTRATOR_MOCK_MODE=1 /workspace/repos/epyc-orchestrator/.venv/bin/python -m pytest -q -p no:cacheprovider -o addopts=""`:
- Final run, `-n 2`, on: `test_autopilot_loop_halts`, `test_autopilot_loop_lifecycle`, `test_autopilot_loop_beliefs`, `test_autopilot_sequential_wiring`, `test_gate_frontier_c_and_b`, `test_ap63_run_manifest_lineage`, `test_autopilot_phase_status`, `test_multitier_mutation_candidates`, `test_eval_leakage_operability`, `test_gate_frontier_live_scope`, `test_vb_ap53_reproposal_rate`, `test_autopilot_multitier_wiring`, `test_autopilot_exit_breadcrumb`, `test_autopilot_resume_halt_latch`: **383 passed, 3 skipped**.
- The skips are environment-gated and predate this work: "ROOT belief reader dev copy not present", "set GATE_FRONTIER_FULL_REPLAY=1", and one more in the reproposal-rate or eval-leakage file.
- Order check with `-p no:randomly`, no `-n`: seq-wiring + lifecycle + live-scope run in both orders, **90 passed, 1 skipped** each time.
- `ruff check` shows no new findings in any changed file compared with the base checkout.
- The mutation script and its result files are in `/tmp/claude-0/-home-user/2773a866-6e4b-53fa-9304-d5960d8e1337/scratchpad/P1/` (`mutate.py`, `res_*.txt`).

### For the integrator
- **`autopilot.py` change:** the only one is in `fac06621` (the new admission function plus its call site). Stage 2 will edit the same file in this worktree. `autopilot.py` is not in `SOURCE_PINS`, so no pin update was needed.
- **Test counts cited in epyc-root:** `test_ap63_run_manifest_lineage.py` is still 17. `scripts/vidya/adapters/README.md` cites `test_vb_ap53_reproposal_rate.py (12)`, but the file already had 14 tests at base. That citation was stale before this work; I left it for the owning session.
- **Mutation-check timing:** a mutation that sets `paused` in the health branch makes the harness poll until pytest's timeout (about 4 minutes). It is only reached under deliberate mutation.
- **Outside the package:** no other packages' files or epyc-root files were touched.