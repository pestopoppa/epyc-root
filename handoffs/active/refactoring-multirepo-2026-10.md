# Handoff: Refactoring — orchestrator, autopilot and AutoKernel (multi-repo debt program)

**Status**: IN PROGRESS: wave 1 partly implemented (unreviewed); stopped by the operator 2026-10-24
**Created**: 2026-10-07
**Updated**: 2026-10-24
**Priority**: High
**Scope**: epyc-orchestrator (`src/`, `scripts/`, `tests/`, `scripts/autopilot/`, `src/autopilot_core/`);
epyc-inference-research `scripts/kernel_rnd/autokernel/`; epyc-root `scripts/hooks/` (guard bugs found on the way)
**Estimated effort**: 382 findings → 26 packages (12 in wave 1, 14 in wave 2); ~150k LOC of approved deletion

Origin: cloud refactor-audit session (claude.ai/code session_01C4SLLAQhop8AA9rJJusAYj), run in an ephemeral
4-CPU container on fresh clones, never on the host. Evidence, data and tooling:
[`research/refactor-audit-2026-10/`](../../research/refactor-audit-2026-10/README.md). Bug report:
[`BUG-REPORT-autopilot-autokernel.md`](../../research/refactor-audit-2026-10/BUG-REPORT-autopilot-autokernel.md).

> **Index row (prepared, NOT applied):** this session does not edit index files (workspace-58 owns them,
> 2026-10-24). The owning session should add one row to `routing-and-optimization-index.md` (the index
> that owns the related `orchestration-robustness-audit-2026-07-11.md`, RTG-24), with the next free RTG id:
> `| RTG-<next> | refactoring program | [refactoring-multirepo-2026-10.md](refactoring-multirepo-2026-10.md) | review + merge the wave-1 refactor/* branches in the order in §Branches | refactor/hermetic-tests first |`

## Problem

The operator asked for a review of the heavily built codebases for best practice, documentation,
modularity, compute performance, ease of resolving bugs, clean and effective tests, and code-size bloat.
The trees grew at roughly 10:1 insertions to deletions. epyc-orchestrator is ~862k lines of Python (src 201k, scripts 274k,
tests 358k) and grew another ~90k in the 17 days from 2026-10-07 to 2026-10-24. AutoKernel is ~490k lines
(282k source, 209k tests): it was rebuilt to a 3,450-LOC loop budget and regrew +278k net in August and +185k in
September, and its own regrowth guard sits 37x over budget (95,260 code lines vs 2,560). The worst hotspots are
single functions of 2,902 lines (`autopilot.py` `_run_loop_inner`, cyclomatic complexity 324), 5,518
(`loop/run.py` `main`, complexity 1,166) and 1,006 (`openai_chat_completions`). Neither repo had working CI:
the orchestrator has none, and the AutoKernel guards workflow was disabled by hand on 2026-09-10 after 168
red runs (its test steps never ran even before that).

## Test baselines and coverage

| Suite | Where | Result | Notes |
|---|---|---|---|
| epyc-orchestrator, full | container, origin/main + `refactor/hermetic-tests`, 2026-10-24 | 20,815 collected; **20,496 passed, 127 failed, 21 errors** (63 min, `-n 2`) | Before `refactor/hermetic-tests` the conftest could not even be imported off the production host. Failing ids: `data/orch_baseline_failing_ids.txt` |
| AutoKernel, full | container, 2026-10-07 | **10,576 passed, 476 failed, 87 errors** (23 min, `-n 3`) | ~58% host-dependent (root uid, CPUs < 32/64, /mnt/raid0); the rest is real rot nobody saw because CI was off. `release/test_t3*` cannot be collected at any standard checkout path |
| epyc-root `scripts/hooks/tests` | container | 313 passed with the scanner fixes (296 at base); same 11 failed / 25 errors on both sides | |
| CI | GitHub | orchestrator: none; AutoKernel: `disabled_manually` since 2026-09-10 | |

Per-file coverage is not mapped here: the suite is too large for a source-to-test table. Coverage gaps that
block a refactor are named inside each package (e.g. B1-03/B5-02: only 9 tests drove the real autopilot
loop; 11+ tests pinned its source TEXT; 28 AutoKernel test files grep `run.py` source).

## Operator decisions (2026-10-24, [`OPERATOR-DECISIONS.md`](../../research/refactor-audit-2026-10/OPERATOR-DECISIONS.md))

1. **Evaluator regime**: batch every change to `eval_tower.py`, `rubric_scoring.py`,
   `src/autopilot_core/tier_specs.py` and `orchestration/eval_registry.yaml` into ONE era event (package P5),
   together with an AST-normalized evaluator fingerprint, so later comment, format and pure-refactor edits stop
   splitting the AP-55 regime. Merging P5 is the single regime break; the operator picks the time.
2. **AutoKernel prune**: delete all three unreachable planes (the unified/standalone control plane rejected on
   2026-09-09; the `discovery_*`/`gpu_source_*` stack; `release/`), staying current with main and re-proving
   reachability from the live entry points at the current origin/main HEAD before every stage.
3. **CI**: add orchestrator CI (pull_request + workflow_dispatch only) and repair the AutoKernel workflow
   (the operator re-enables it in GitHub).
4. **Scope**: full program, paced at about 2 concurrent agents. The account has no extra-usage credits, so the
   work spans several 5-hour usage windows.

Standing inputs: hermetic tests approved (2026-10-07); keep an eye on bloat (2026-10-07); kernel (llama.cpp)
defects go to the champion fold as CH-xx recommendations, never as production patches (relayed operator rule,
2026-10-24); workspace-58's live-path and file boundaries (§Coordination).

## Branches (all pushed 2026-10-24; rebased on origin/main unless noted; NONE reviewed by a second agent yet)

| Repo | Branch | Commits | Contents | Merge notes |
|---|---|---|---|---|
| epyc-root | `refactor/containment-scanner` | 3 | scanner bypass fixes; degraded-mode regression fix (main since 84b0de13 lets `sudo mount` through with no scanner); behaviour-change note | **Operator review required** (safety boundary for INC-20260823); see `scripts/hooks/CONTAINMENT-SCANNER-CHANGES-FOR-REVIEW.md` on the branch |
| epyc-root | `refactor/refactoring-plan` | this | this handoff, the bug report, all evidence | docs only |
| epyc-orchestrator | `refactor/hermetic-tests` | 1 | conftest stub kernel store + host-RAM fallback (no-ops on the host), `ORCHESTRATOR_PATHS_KERNEL_ROOT`, ni63 pin refresh | **merge first**; every orchestrator branch below contains it |
| epyc-orchestrator | `refactor/request-path` | 9 | O1 stage 1: per-request state on the shared LLMPrimitives (A1-02/A2-01/A1-M2), model/REPL calls off the event loop (A1-01), per-request cancellation (A1-M1), no_web context (A4-M1), shared backend build (A2-04), region-lock release (A2-13), skill ids (A1-17) | production request path: review carefully; stage 2 (A2-02…A2-16) not started |
| epyc-orchestrator | `refactor/config-registry` | 14 | O3: stack-priors parse cache (A3-01/A1-03), fail-closed compile (A3-02), Settings factories (A3-07), topology-cache poison (A3-08), shadow thread (A3-09), env-override and crash fixes (A3-M1, A3-04, A3-06), OCR timeout (A3-15), registry-cache lock (A3-05), shim race (A3-16/A4-08), env.sh root (A3-M2), registry backoff (A3-19) | rebased with ni63 pin conflicts resolved (upstream fixture kept; pins of files this branch changes refreshed) |
| epyc-orchestrator | `refactor/scripts-cleanup` | 11 | O6: name-pattern-kill scripts removed + guard (A5-M1), v9-binary reembed (A5-06), v8 pin (A5-07), seeding diagnostics (A5-04), banner (A5-12), preflight-gate (A5-22), mtmd (A5-M2); deletions of the retired E8 chain (A5-01/A6-19), seeding v2 fork (A5-05), and a **WIP** delete of `scripts/benchmark/deprecated/` (A5-11) | stage-2 commits have no test report; finish the WIP. Touches 30 files under `scripts/benchmark/` (workspace-58: no live launcher references them) |
| epyc-orchestrator | `refactor/test-hazards` | 4 | O7: fence tests no longer aim destructive payloads at the REAL wiki (A6-01), checkout-write leak guard (A6-02), tmp_path not fixed /mnt/raid0 dirs (A6-09) | no test report (interrupted) |
| epyc-orchestrator | `refactor/autopilot-loop` | 6 | P1 stage 1 (safety net): the real loop driven by a harness instead of source-text slicing (B1-03/B5-02), shared frontier-admission predicate (B5-08), hook containment (B1-15) | stage 2 (the loop bugs incl. B1-01 pause clobber) not started |
| epyc-orchestrator | `refactor/autopilot-gate` | 15 | P2: safety-gate seq upgrade (B2-02), one-sided MAD (B2-03, **changes what is admitted to learning**), refusal codes (B2-09), validator/replay (B2-20), hypervolume memo + fold + off-loop dashboard (B5-01), bounded snapshot replay (B5-M1), cluster identity (B5-M2), era guard (B5-16), dead modules (B5-09), `__init__` (B5-13), drop counts (B5-12) | B2-03 is a decision-semantics change: review it as such |
| epyc-inference-research | `refactor/autokernel-loop-bugs` | 1 | **WIP**: `run._git` checks git's exit status; failed rollback aborts the run (C1-05) | **do not merge to main**: AutoKernel launches are under an operator hold; workspace-58 merges it with a deliberate re-pin when the hold lifts |
| all three | `claude/vigilant-thompson-shpyh0` | — | superseded by the `refactor/*` branches above | ignore / delete |

Merge order (orchestrator): `refactor/hermetic-tests` → `refactor/config-registry` → `refactor/request-path`
→ `refactor/test-hazards` → `refactor/autopilot-gate` → `refactor/autopilot-loop` → `refactor/scripts-cleanup`.
Each branch rebased cleanly on origin/main on 2026-10-24; later upstream commits may need another rebase. Nothing
merged to orchestrator main is served until the shared clone is synced (operator approval).

## Issue inventory (summary; every finding with evidence, verifier notes and proposal is in the findings files)

| Unit | Findings | Sev ≥ 4 | Bloat est. (LOC) | Biggest problems |
|---|---|---|---|---|
| A1 API layer | 23 | 6 | 1,100 | blocking model/REPL calls on the uvicorn loop; shared per-request state; 1,006-line openai handler, 2 near-identical /chat/stream impls; per-request YAML and ps parsing in the dashboard |
| A2 inference hot path | 24 | 6 | 2,300 | per-request state on a shared LLMPrimitives reroutes requests under concurrency; read-timeout truncation reported as success; quadratic early-stop; 4 drifted llama_server lanes; 12 copies of the escalation chain |
| A3 config/registry/runtime | 27 | 3 | 2,700 | config declared 4 times; fail-open stack-priors compile; reset_config cannot refresh; poisoned caches |
| A4 REPL/tools/top level | 26 | 1 | 3,000 | production read_file swapped for an unchecked builtin; REPL web tools bypass role permissions and no_web; 4 parallel tool stacks |
| A5 orchestrator scripts | 28 | 2 | 45,000 | the retired E8 chain (32.6k incl. tests); a forked scripts/lib; 71 src→scripts imports; 196 sys.path hacks; name-pattern kills |
| A6 orchestrator tests | 20 | 2 | 5,200 | not hermetic; destructive payloads aimed at the real wiki; no CI; 89 assertion-free tests; ~50 source-text tests |
| B1 autopilot loop | 22 | 3 | 300 (+~9k movable) | 2,902-line `_run_loop_inner`; plain `save_state()` clobbers an operator pause (H4 class); 8 copies of the halt latch |
| B2 eval + safety gate | 22 | 1 | 1,250 | parse-failure telemetry zeroed on every T1/T2 trial; two-sided MAD admits regressions as improvements; per-question registry re-parse |
| B3 actions/planner/journal | 27 | 0 | 1,500 | pgrep name-pattern process picks; NaN passes bounds checks; journal deep-copied per trial |
| B4 satellites | 22 | 0 | 7,400 | applied one-shot ratifiers and era-pinned collectors still in tree; vendored judges unprotected |
| B5 autopilot_core + tests | 20 | 3 | 1,450 | exponential hypervolume per replayed trial (3.6-5.7 s, twice per trial); evaluator fingerprint hashes raw bytes |
| C1 AK loop core | 27 | 5 | 26,600 | 5,518-line `run.main`; `_git` ignores exit status; CI off |
| C2 AK loop periphery | 18 | 2 | 72,000 | the rejected unified/standalone plane (~61k incl. tests) still imported through 5 thin bridges |
| C3 AK controller | 24 | 1 | 37,000 | unreachable discovery_*/gpu_source_* stack; v9 digests pinned for "v10"; stdlib `resource` shadowed |
| C4 AK evaluator/execution (UNVERIFIED) | 18 | 3 | 5,700 | non-inferiority e-value labelled IMPROVEMENT; attestation never hashes the libggml DSOs |
| C5 AK release + top level (UNVERIFIED) | 16 | 7 | 65,000 | dormant release/ plane; guard counts only loop/; journal validator turns ImportError into "invalid payload" |
| C6 AK tests (UNVERIFIED) | 18 | 5 | 9,400 | CI cannot reach its test steps; 38 tests broken by a helper change; jobs=32 fixture vs CPU count |

(Bloat estimates overlap between C units; the approved three-plane prune is ~150k LOC including tests.)

## Wave 1: bugs, hazards, ruled deletions (packages in [`packages/wave1.json`](../../research/refactor-audit-2026-10/packages/wave1.json))

| Pkg | Theme | State 2026-10-24 |
|---|---|---|
| O1 | request path: concurrency, event loop, failure semantics | stage 1 done (9/9, on `refactor/request-path`); stage 2 (A2-02, A2-M1, A2-M2, A2-03, A2-05, A2-11, A2-16) not started |
| O3 | config/registry/runtime correctness + stack-priors cache | done (`refactor/config-registry`) |
| O4 | REPL/tools permission bypasses and structured-mode defects (A4-01 security) | not started |
| O5 | dashboard request-path cost | not started |
| O6 | scripts bugs + ruled deletions | stage 1 done; stage 2 partly done (A5-11 WIP; A5-23, A5-18, A5-02, A5-21 not started) |
| O7 | test-suite hazards | A6-01, A6-02, A6-09 committed; A6-M1, A6-03, A6-12, A6-13, A6-11, A6-17 not started |
| P1 | autopilot loop: safety net, then loop bugs | stage 1 done; stage 2 (B1-01 with its safety conditions, B1-M1, B1-M2, B1-04, B1-08, B1-09, B1-14, B1-13) not started |
| P2 | safety gate + autopilot_core | done (B2-11 skipped: upstream already split `check()`; B2-17 no change per verifier) |
| P3 | actions, config applicator, controller IO, planner, journal (B3-01 pgrep) | not started |
| P4 | autopilot satellites bloat (one-shot ratifiers, era-pinned family, dead modules) | not started |
| K1 | AutoKernel live-loop bugs and red tests | C1-05 WIP only |
| K2 | AutoKernel evaluator/execution integrity (C4-05, C4-06; verify first) | not started |

## Wave 2: decision-dependent and structural ([`packages/wave2.json`](../../research/refactor-audit-2026-10/packages/wave2.json))

| Pkg | Theme | Depends on |
|---|---|---|
| P5 | **evaluator: ONE batched era event**: B5-03 fingerprint normalization FIRST, then B2-01, B2-M1, B2-M2, B2-10, B5-06, B5-07, B2-19, perf B2-04/05/06, refactors B2-07/08/14/15/18/12/13, B5-14, B3-09; commit subjects prefixed `evaluator-era:` | P2 merged |
| K3 | **AutoKernel three-plane prune**, three stages (unified plane; discovery + release + adapters + arena; dead modules + doc-coupled suites); rebase on origin/main and re-prove the reachability closure before EVERY stage; never delete the three live evaluator modules the strip plan wrongly marks dead (C4-01); epyc-root consumers (C2-M1) listed, not edited | K1; operator hold lifted for merge |
| K4 | AutoKernel regrowth guard (ratchet at post-prune size, all of autokernel/ counted) + CI repair (independent steps, yaml dependency, floors from collection counts) | K3 |
| O8 | orchestrator CI (PR + manual only; hermetic suite minus a reviewed host-only list with reasons), honest `make gates` (format-check only changed files; 1,471 files fail a whole-tree check), ni63 pin design (record hashes for provenance instead of asserting a past commit's bytes; the pin is already red on main for `orchestrator_stack.py`) | hermetic-tests merged |
| D1 | autopilot `_run_loop_inner` decomposition (B1-02 staged seams) | P1 merged |
| D2 | API: openai_compat and /chat de-duplication | O1 merged |
| D3 | inference hot path: llama_server lanes, `_execute_turn`, escalation chain | O1 merged |
| D4 | AutoKernel `run.main` decomposition (behavioural tests first; evidence identities hash whole files: C1-M1) | K1, K3 merged |
| D5 | config/registry/runtime consolidation (region-lock: bug fixes only) | O3 merged |
| D6 | REPL/tools consolidation | O4 merged |
| D7 | orchestrator scripts structure (no `orchestrator_stack.py` restructuring) | O6 merged |
| D8 | orchestrator test-suite consolidation | last |
| D9 | autopilot remaining structure | P1, P3, P4 merged |
| D10 | AutoKernel remaining structure | K1, K2, K3 merged |

Deferred, not in any package ([`packages/deferred.json`](../../research/refactor-audit-2026-10/packages/deferred.json)):
A5-10, A5-16, A5-17, A5-19 restructure `scripts/server/orchestrator_stack.py`, a live path on the host (workspace-58,
2026-10-24); their proposals in `findings-orchestrator-core.md` are ready to run when that file is quiet.
C5-05 (delete the `campaign.py` CLI cluster, ~20k LOC) is a fourth plane the operator did not approve.
C1-22 disappears with the unified plane.

## How to resume

1. `python3 research/refactor-audit-2026-10/packages/mkpkg.py research/refactor-audit-2026-10/packages/wave1.json <scratch>/pkg`
   regenerates the per-package briefs (same for `wave2.json`).
2. `research/refactor-audit-2026-10/packages/impl_workflow_w2.js` is the implementer/reviewer prompt contract
   (one worktree per package, re-verify at HEAD, failing test first for bugs, one commit per finding, adversarial
   review of the diff). Point its paths at the new scratch dir.
3. Start each package from its pushed `refactor/*` branch (or from origin/main for unstarted packages), rebased on
   origin/main. Findings whose id appears in a commit subject are done. Status per finding:
   `research/refactor-audit-2026-10/data/finding-status.json`.
4. Every package needs its adversarial review before merge; none has had one.

## Coordination (workspace-58, 2026-10-24)

- Push only `refactor/<topic>` branches with an explicit refspec, rebased on origin/main; never main.
- Live paths on the host: no structural refactor of `scripts/server/orchestrator_stack.py`, `scripts/region-lock`,
  `src/runtime/*region_lock*`, `scripts/gitnexus-analyze.sh` (bug fixes only), and those keep their paths and
  CLIs. Never the llama.cpp trees. `scripts/benchmark/` and `scripts/kernel_rnd/autokernel/` are pinned by SHA by
  running jobs: merge with a deliberate re-pin.
- Do not hand-edit the index files, `.index-state.json`/`.index-graph.json`, `backlog-priority.json`,
  `wiki/source_manifest.json`, `progress/*-workspace-58.md`, `INCIDENT_LOG.md`, or the handoffs workspace-58 listed.

## Success criteria

1. Every finding is either implemented with a regression or characterization test, or recorded as skipped with
   a reason (already fixed, does not reproduce, unsafe).
2. The orchestrator suite collects and runs off the host, and no package adds a failure to the baseline set
   (`data/orch_baseline_failing_ids.txt`).
3. AutoKernel source shrinks by roughly the approved ~150k LOC, the live-loop and decision-arithmetic suites stay
   green, and the regrowth guard is a satisfiable ratchet that CI runs.
4. Orchestrator CI runs on pull requests; the AutoKernel workflow can go green when re-enabled.
5. No function in the touched hotspots stays above ~300 lines without a recorded reason.

## Notes

- **The evaluator files are booby-trapped**: any byte change to the four fingerprinted files splits the AP-55
  regime (B5-03). Until P5 lands, do not reformat or edit them, including blanket `ruff format`.
- **ni63 source pins**: `tests/fixtures/ni63_capacity_child/source_clone.py` byte-pins ~30 production files to
  a past commit. Any change to a pinned file must refresh its (blob sha1, sha256). The pin for
  `scripts/server/orchestrator_stack.py` is already stale on main, so those 4 tests fail there too. O8 fixes the design.
- **Guards found broken on the way** (epyc-root, `refactor/containment-scanner`): the filesystem-containment
  scanner allowed writes outside the roots when a redirect followed the destination (`cp secret /outside
  2>/dev/null`), checked the branch instead of the path in `git worktree add`, and missed shell structure; and
  since 84b0de13 its degraded mode allows `sudo mount`. Also: `scripts/harness/strategy_projection_report_capture.py`
  `TRUSTED_APP_SOURCES` has 6 of 11 pins stale at base (reported by O3).
- **Unverified units**: C4, C5, C6 findings were never adversarially verified; the packages re-verify them first.
- **Usage pacing**: 6 concurrent agents exhausted a 5-hour window in about 55 minutes on 2026-10-24 (extra usage
  rejected: `out_of_credits`); 2 concurrent agents is the sustainable rate.
