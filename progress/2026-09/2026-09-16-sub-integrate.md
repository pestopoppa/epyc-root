# 2026-09-16 — sub-integrate (integration agent)

Merged reviewed branches in fresh detached worktrees on `origin/main`. Every push ran under the
`push` serialization lock (acquire, verify first parent == origin/main, raw push, release). No
inference and no process management.

## epyc-orchestrator — pushed `753343f5` (from `92bbeb06`)

| Branch | Merge SHA |
|---|---|
| `sub/tooling-orch-20260916` | `370dc715` |
| `sub/cleanup2-20260916` | `dec73e25` |
| `sub/reviewer-artifacts-20260916` | `bdf76ab3` |
| `sub/nextaction-sweep-20260916` | `864c3b3b` |
| `sub/autopilot-evidence-20260916` | `753343f5` |

- Tests (orchestrator `.venv`): all 16 test files touched by the merges, including test_output_spill,
  test_kb_rag_query_telemetry, test_repl_file_exploration, test_repl_environment, AP-53/AP-55/W3,
  RA-9/RA-12/RM-5 and contention. Result: **567 passed**.
- `tests/unit -k "journal or snapshot or rejected or fingerprint"`: **463 passed, 10 skipped, 1 xfailed**.
- `sub/ap54-fence-20260916` was NOT merged.

### Round 2 — pushed `d748b4c7` (from `753343f5`)

| Branch | Merge SHA |
|---|---|
| `sub/memeval-orch-20260916` (`dae95a86`) | `e15fa7d6` |
| `sub/trace-bm25-20260916` (`6302b381`) | `21172688` |
| `sub/utm-m78-20260916` (`74418b3c`, UTM-M7/M8) | `d748b4c7` |

- Tests:
  - debug_scorer unit files, including the new transport test: **79 passed**.
  - trace suites before utm-m78: **36 passed**.
  - `tests/unit/test_trace*.py` on the combined tree: **44 passed**.
  - Tests that import debug_scorer or trace: **317 passed, 4 xfailed**.
- Push: the orchestrator guard also accepted the push, with `EPYC_PUSH_LOCK_HOLDER=sub-integrate`
  set.
- Not merged: research `sub/memeval-20260916`, which is getting a resume-bug fix.

## epyc-inference-research — pushed `9777a3d5` (from `6575c33c`)

- `sub/nextaction-sweep-20260916`: **only 88b1160d was integrated.** It was cherry-picked as
  `04124a54`, then merged with `--no-ff` as `9777a3d5`.
- Why: the branch is based on the stale local `main`, so a plain merge would also have published
  `1780fa7b` (on main as `56ef1404`). That commit holds 37 unreviewed INF-70 evidence files, which belong to the inf70 lane.
  The branch's `ae8e5ef9` is already upstream by patch-id.
- Tests: `scripts/benchmark/test_question_pool.py` + `test_dataset_adapters.py`: **8 passed**.
- Not merged: the gpu-prep, gpu-runner, memeval and akfix branches.

## epyc-root — pushed `d9273d36` (from `b65138a0`)

| Step | SHA |
|---|---|
| merge `sub/tooling-root-20260916` | `719ac638` |
| fix: kb_rag_query_length README row, wrap-up Step 5 scoped touch, SKILL.md OP-34 adopted, WIKI-DRAFT BLOCKER 2 lifted | `b35553b8` |
| merge `sub/rtg46-readiness-20260916` | `e0a600a5` |
| merge `sub/memeval-root-20260916` (added by the main session; README adjacent-row conflict resolved by keeping both sides) | `1105598d` |
| `index_state.py` regeneration (`--check` had failed on freshness; exits 0 after) | `d9273d36` |

- The wrap-up `--touch` guidance is in **Step 5** (Wiki Compilation), not Step 7, so the
  scoped-touch documentation went there.
- Tests (orchestrator `.venv`): compile_sources, kb_rag_query_length adapter, handoff-graph
  readiness, handoff timeline and inf70_serving_arm adapter. Result: **93 passed, 1 skipped**.
- Full `tests/vidya`: 1171 passed, 1 failed, 12 errors. All of the failures and errors are in
  `test_autokernel_serving_feedback.py`, which no merge touched. Cause:
  `KeyError: 'EPYC_RESEARCH_ROOT'` (environment dependency).
- Root pre-push guard: the push also needs `EPYC_PUSH_LOCK_HOLDER=<lock agent id>` in the
  environment. The orchestrator and research guards did not ask for it.
- Not merged: `sub/harness-evidence-20260916` and the orchestrator/research memeval branches.

## Batch 2

### epyc-inference-research — pushed `6459a86e` (from `9777a3d5`)
- `sub/memeval-20260916` (commits `ccc41d4b`, `87991705` and the resume fix `194a83a9`) merged with
  `--no-ff`.
- The branch base was clean (it was missing only `9777a3d5`), so no cherry-pick was needed.
- Its orchestrator dependency, `dae95a86`, was already on `main` (merge `e15fa7d6`).
- Tests (orchestrator `.venv`): test_judge_beam_run, test_beam_adapter, test_score_tulving_run,
  test_tulving_context_mode, test_tulving_episodic_adapter and test_build_tulving_followup_manifest.
  Result: **180 passed, 9 skipped**.
- The 9 skips:
  - 5 `test_beam_adapter.py:108` tests need `pyarrow` (ml venv).
  - 1 `test_beam_adapter.py:468` test needs the epyc-root beam capture, which is not on this host.
  - 3 `test_score_tulving_run.py` tests (:352, :375, :464) report "epyc-root not on this host".

### epyc-root — pushed `874a6bc9` (from `c57b0b6c`)
- `sub/memeval-root-fix-20260916` (`6c1484a9`) merged as `4e851e33`.
- Ticks commit `874a6bc9`:
  - UTM-M7/M8: the notes now say re-implemented and integrated (orchestrator `d748b4c7`).
  - RTG-46: three boxes ticked, and the layout SHA recorded (`e0a600a5`).
  - EVL-12 C2: the sub-box was added and ticked, and the parent was closed (research `04124a54` / `9777a3d5`).
  - RTG-35: the waiver box was ticked (`864c3b3b`).
  - RA-9 (3 boxes) and RA-12: ticked (`bdf76ab3`).
  - KB-RAG C7/H2 and TOC-SP-2: ticked (`370dc715`).
  - Two pre-existing bare `intake-1299` citations were changed to `#record` so cite-check passes.
  - The master index was regenerated; `--check` reports 0 problems.
- The evidence notes were ported from the uncommitted drafts in `/workspace`, one box block at a
  time. Each block diff was verified to be note-only. The `/workspace` copies still carry the
  "pending" wording, so the owning session must reconcile them against `origin/main`.
- Tests: inf70 arm, kb_rag adapter and handoff timeline: 63 passed.

## Batch 3 (sub-integrate3)

### Pushed
All merges below are `--no-ff` merges built in fresh worktrees from `origin/main` and pushed under
the push lock. Each first parent was re-verified against `origin/main` before its push.

**epyc-inference-research**
- `eb55e457`: merges `1eb4a89b` only. That is the 35B max-perf promotion completion; `38d82ebe` is
  held for autokernel.
- `sha256sum -c SHA256SUMS` in `data/ak-champion-maxperf-35b-2026-09-08/` returned 8/8 OK.

**epyc-root**
- `8abf6984`: `sub/misc-fixes-root-20260916` (`896dedcd`, `83e460fd`).
  - With `EPYC_RESEARCH_ROOT` unset, `test_autokernel_serving_feedback` gives 13 skipped.
  - cite-check found no blocking citations. `index_state --check` reports 0 problems.
- `86be4a5e`: `sub/harness-evidence-20260916` (`034dccbe`, `31d95ad8`).
  - `test_hub_manifest_launch` passed 38/38, `test_hub_deploy_sync` passed, and
    `test_hub_stale_source` passed 6/6.
  - `test_dashboard_panels` plus `_redteam` passed 147.
- `1e1de5fb`: `sub/evconf2-root-20260916` (`c8c68662`).
  - The README source-table conflict was resolved by keeping both rows.
- `4fe47225`: fix commit on top of the EV-CONF-2 merge. `resolve_spec_state` now returns
  `unknown`, not `off`, when the `/slots` declaration is missing or mixed (`[None]`,
  `[False, None]`). Two tests were added, and `test_confidence_source_adapter` passes 17/17.
- `87109bb2`: `sub/vidya-wire-20260916` (`e04c44a2`).
  - README rows: kept vidya-wire's versions of the tulving, BEAM, INF-70, KB-RAG and ParEval rows,
    and kept main's EV-CONF-2 row.
  - The rollup was regenerated.
  - `tests/vidya`: 1220 passed, 80 skipped (the expected 1201, plus 19 EV-CONF-2 tests).
  - The README's three overturned citations (`intake-896`, `intake-896#03`, `intake-1245`) were
    left alone. `scripts/` is outside the gate's scanned prefixes, so they do not block a commit.

**epyc-orchestrator**
- `827737ea`: `sub/tripwire-fix-20260916` (`b8e6bfd0`).
- `d8b915ee`: `sub/evconf2-20260916` (`b98dee18`).
- `88a2902d`: `sub/evconf2-probe-20260916` (`f2e9ee07`, `7cc118da`).
- Tests (`.venv`): tripwire + mutation_ledger + ap53 passed 26. `test_ev_conf2_*` +
  `test_eval_tower_*` passed 260.

### OCC-1 fixes (NOT pushed; for review)
Research `sub/occ1-20260916` @ `2f053f61` (on top of `070db22a`):
- **Port.** The reader moved from `:8090` (the production embedder) to test port **18431**. That
  port is absent from `launch_manifest.yaml` and was not listening.
- **Port parameter.** The port is now `launch_reader.sh --port N` (or `OCC1_PORT`) and
  `run_occ1.py --port N`. The launcher refuses a port that is already listening.
- **Belief sidecar.** `report` now writes the SC85 sidecar through the root capture module. A VOID
  report writes nothing and removes a stale sidecar. A writer refusal exits 3.
  `--no-belief-measurements`, `--run-id` and `--protocol-id` control it.
- **Tests.** 26 pass. One of them uses the real root writer when `EPYC_ROOT` points at the root
  branch.

Root `sub/occ1-root-20260916` @ `1d5f5314`:
- `adapters/occ1_optical_compression_capture.py` is the writer plus `validate_row`.
  `adapters/occ1_optical_compression.py` is the strict reader.
- A new `cli.py ingest occ1` source, a README source row, and SC85 in
  `vidya-belief-substrate-program.md`, left unticked until merge. (SC83 and SC84 were already
  taken.)
- The rows per arm are F1 and EM, plus, for each image arm, the paired F1 delta (with CI, McNemar p
  and verdict) and the prompt-token ratio. Each row also carries the suite fingerprint, the serving
  identity and the prereg digest.
- The locator is the run, and a VOID run is refused.
- `protocol_id` is empty, so every tuple is `Judged/Located` until an OCC protocol is codified
  (SC85b).
- `tests/vidya`: 1259 passed, 80 skipped. `index_state --check` reports 0 problems.

Both branches merge cleanly against `origin/main` (checked with `merge-tree`). The worktrees I
created have been removed. `sub-occ1` is left in place because it belongs to that agent.
