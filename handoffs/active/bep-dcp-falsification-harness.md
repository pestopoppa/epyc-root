# BEP-2 / DCP-6 Falsification-Harness Construction

status: REVIEWED / READY TO BUILD (2026-05-26)
owner: claude session handoff; operator review incorporated
related:
  - handoffs/active/batched-edit-parallel-apply.md (BEP source; BEP-1/4/5 merged, `_execute_turn` divergence wired `ea5f010`)
  - handoffs/active/delegation-context-preassembly.md (DCP source; DCP-1/2/3 merged, DCP-4 wired `31ea6d4`)
  - data/bulk_inference_2026_05_26/execution_manifest.jsonl (Package J rows J7/J8)

---

## Executive Decision

Proceed with the harness build, but **do not implement the original narrow "write-only edit-root" plan**. That was safe for preventing direct writes to the orchestrator repo, but it was not fair or complete enough for a falsification A/B.

Use a single orchestrator instance with a new default-off task-root override:

- `ORCHESTRATOR_EDIT_ROOT` remains the env var name for compatibility with the draft.
- Its semantics are broader: **model-facing task workspace root**, not merely "write destination".
- Registry, model config, sessions, orchestration logs, patch ledgers, and production state remain on the real `project_root`.
- Model-facing reads, writes, test cwd, batch-edit repo root, and DCP file discovery must point at the scratch task repo during BEP/DCP A/B.

This is preferred over a second sandbox orchestrator instance because it keeps the production config/runtime identical while isolating only the task workspace. A second instance is a fallback only if Phase 0 proves the task-root split cannot be made unambiguous.

## Why This Exists

BEP (J8) and DCP (J7) are wired behind default-off flags and have unit coverage, but their inference falsification gates cannot be run correctly with the current eval assets.

Two concrete gaps were found on 2026-05-26 while attempting to launch BEP-2:

1. **No valid multi-file-edit workload.** Existing eval suites are Q&A or coding-answer benchmarks. `batch_edit_mode` only diverges when the root LM emits a fenced `patchset` block for file edits, so those suites do not exercise the BEP path.
2. **The live edit/read/test paths target the orchestrator repo.** The interleaved REPL write path (`file_mutation`) and the batch path (`_batch_edit_repo_root`) resolve to `get_config().paths.project_root`. Running free-form model-generated edits there is unsafe. The existing `ORCHESTRATOR_PATHS_PROJECT_ROOT` redirect is too broad because it also relocates registry/tool config/session/log paths.

Therefore BEP-2/DCP-6 are **build-then-run**. This handoff owns the safe harness build and the decision gates so the eventual result is a real keep/kill signal, not a harness artifact.

## Hard Invariants

- **No orchestrator self-mutation**: during A/B, all model-driven workspace mutations land in a throwaway scratch git repo, never the orchestrator checkout.
- **Same workspace semantics across arms**: the baseline interleaved arm and the batch-edit treatment arm must both read, write, grep, test, and verify against the same scratch repo for the same task.
- **Config untouched**: registry, stack config, model registry, session state, logs, progress, patch ledgers, and orchestrator runtime files remain rooted at real `project_root`.
- **DCP reads scratch**: when DCP is evaluated, context discovery and rendered file bodies must come from the scratch repo, not from the orchestrator repo.
- **Independent verifier**: task success is judged by deterministic checks (`pytest`, script, grep/assertion), never by the applying model.
- **Fair turn budget**: the interleaved baseline gets enough turns to finish; otherwise the latency/quality comparison is rigged in favor of batch mode.
- **Fresh repo per task-arm-rep**: reset scratch to pristine state before every task x arm x repetition.
- **Incremental persistence**: write result rows after every task-arm-rep, not only at the end.
- **J6 paused only for inference**: code/workload/driver build is concurrent-safe with J6; actual A/B runs require a quiet host per `feedback_no_concurrent_inference`.
- **Default-off production behavior**: unset env vars preserve today's behavior.

## Phase 0 - Surface Audit And Task-Root Contract (required before code)

Before implementing any override, enumerate every model-facing filesystem surface and classify it as either **task-root** or **project-root**. This phase is non-optional; it prevents the exact class of flawed harness where writes go to scratch while tests/readbacks still hit the orchestrator repo.

### Required Classification

| Surface | Current anchor | A/B anchor | Reason |
|---|---|---|---|
| `file_write_safe` write/read/backup target | caller path validated against allowed paths | **task-root** | Baseline interleaved edits must mutate scratch. |
| `peek(file_path=...)`, `grep(file_path=...)`, `list_dir`, `file_info` | user-provided path validated by `ALLOWED_FILE_PATHS` | **task-root for relative task paths** | The model must inspect the same scratch repo it edits. |
| `run_shell` cwd | `_get_project_root()` | **task-root** | Verifiers/tests run by the model must exercise scratch. |
| `run_python_code` cwd | config tmp dir | project-root/tmp is OK unless task imports local files | If task verification uses repo-local imports, prefer driver-side verifier over model-side `run_python_code`; otherwise explicitly set cwd/task path support. |
| `_batch_edit_repo_root()` | `_get_project_root()` | **task-root** | Treatment must stage/promote into scratch, not orchestrator. |
| `apply_patchset_sandboxed(... repo_root=...)` | caller-provided | **task-root** | Same reason. |
| `promote_sandbox(... repo_root=...)` | caller-provided | **task-root** | For A/B promotion means scratch promotion only. |
| DCP `_file_reader_fn` | `_get_project_root()` | **task-root** | DCP bundle must package the task repo. |
| DCP `code_search_fn` / ColGREP root | production source root | **task-root** | Search candidates must come from the task repo. |
| patch preparation/approval ledgers | `project_root/orchestration/patches` | project-root or disabled | Patch ledgers are orchestration metadata, not task files. During A/B, prefer disabled. |
| `log_append` | `project_root/logs` | project-root | Runtime/audit log, not task content. |
| registry/config/session/procedure/checkpoints | `project_root/orchestration/...` | project-root | Runtime control plane must remain real. |

### Phase 0 Commands / Checks

Use code search and a short written inventory:

```bash
cd /mnt/raid0/llm/epyc-orchestrator
rg -n "_get_project_root|ALLOWED_FILE_PATHS|file_write_safe|run_shell|run_python_code|_batch_edit_repo_root|dcp_pre_assembly|code_search|Path\\.write_text|open\\(.+[wa]" src/repl_environment src/graph src/api/routes src/context_discovery.py
```

Then write a small `data/bep_sandbox/task_root_surface_audit.md` with:

- each surface found,
- selected anchor (`task-root` or `project-root`),
- implementation touchpoint,
- unit/integration test that proves the choice.

### Phase 0 Exit Gate

Do not start Phase 1 until all of these pass:

- a model-facing write to `cart.py` lands under scratch;
- a model-facing read/grep/list of `cart.py` reads scratch;
- a model-facing shell test runs from scratch;
- batch-edit treatment promotes only into scratch;
- DCP bundle renders scratch files;
- orchestrator registry/config/log paths remain real;
- orchestrator checkout git diff is unchanged after the safety test.

## Phase 1 - Task-Root Override (code, default-off)

Implement `ORCHESTRATOR_EDIT_ROOT` as a **model task-root override**.

### Required Accessors

Add accessors in a single module that both REPL and graph helpers can import without circular coupling. Preferred location: `src/repl_environment/task_root.py` or equivalent.

Required behavior:

```python
def get_project_root() -> Path:
    """Existing orchestration project root from config/fallback."""

def get_task_root() -> Path:
    """Return ORCHESTRATOR_EDIT_ROOT when set, else project_root."""

def resolve_task_path(path: str | Path) -> Path:
    """Resolve relative task paths under task root; preserve absolute paths only if they are under task root."""
```

Rules:

- If `ORCHESTRATOR_EDIT_ROOT` is unset: `get_task_root() == get_project_root()` and behavior is unchanged.
- If set: path must exist, be a directory, and preferably contain `.git` or an explicit harness marker such as `.bep_sandbox_root`.
- Reject paths that resolve outside task root for model-facing file operations.
- Relative file paths in prompts should resolve under task root.
- Absolute paths are allowed only when they resolve under task root, except for explicit project-root metadata paths not exposed as model workspace operations.

### Required Code Touchpoints

Update these surfaces:

- `src/repl_environment/file_mutation.py`
  - `_file_write_safe`: resolve target through task root; backup existing scratch file under scratch; path validation uses task-root-aware rules.
  - Do **not** move `log_append` or patch ledger directories.
  - During A/B, disable `_prepare_patch` / `_apply_approved_patch` or make them task-root-aware but keep ledgers project-root. Simpler: driver prompt forbids patch tools and harness asserts no patch ledger side effects.
- `src/repl_environment/file_exploration.py`
  - `peek(file_path=...)` and `grep(file_path=...)`: resolve relative task paths under task root.
  - `list_dir` / `file_info` equivalents must follow the same rule.
- `src/repl_environment/external_access.py`
  - `run_shell`: cwd becomes task root when `ORCHESTRATOR_EDIT_ROOT` is set.
  - Keep command allowlist unchanged.
  - `run_python_code`: document whether it remains tmp-rooted; if local imports are needed, add an optional cwd or rely on driver-side verifiers.
- `src/graph/helpers.py`
  - `_batch_edit_repo_root()` returns task root.
  - `_maybe_batch_edit_turn` artifacts include `task_root`, `batch_edit_status`, and failure classification.
- `src/api/routes/chat_delegation.py`
  - DCP `_file_reader_fn` roots at task root during DCP A/B.
  - DCP code search must use the scratch repo, not production `COLGREP_DEFAULT_PATH`.
- `src/repl_environment/environment.py`
  - Ensure `ALLOWED_FILE_PATHS` or `_validate_file_path()` permits the task root at runtime. Be careful: `ALLOWED_FILE_PATHS` is currently class-level and computed at import time; env changes after import may not be reflected unless validation consults `get_task_root()` dynamically.

### Required Tests

Add focused unit tests before any inference:

| Test | Required assertion |
|---|---|
| unset env | existing project-root behavior unchanged |
| file write | relative `cart.py` writes under scratch; orchestrator repo unchanged |
| file read | `peek/grep/list_dir/file_info` observe scratch |
| shell cwd | `run_shell("pwd")` or a deterministic command reports scratch cwd |
| batch root | `_batch_edit_repo_root()` returns scratch when env set |
| DCP root | rendered DCP bundle includes scratch file content and not orchestrator file content |
| metadata roots | logs/registry/session/patch ledgers still use project-root or are disabled as specified |
| escape rejection | `../outside.py` and absolute outside paths are rejected |

Commit Phase 1 alone. This is the checkpoint that makes the experiment safe.

## Phase 1b - Batch Runner Correctness Fixes (code, before rename/delete tasks)

The current BEP runner must be audited before including rename/delete tasks.

Observed risk from code review:

- `apply_patchset_to_dir()` handles `DELETE` and `RENAME`, but `promote_sandbox()` currently copies only `result.diff_paths`.
- If delete/rename paths are not represented in `diff_paths`, a sandbox verify can pass while promotion fails to reflect the delete/rename in the scratch repo.

Required action:

- Either fix `promote_sandbox()` to transactionally promote create/modify/delete/rename operations, with tests;
- Or exclude delete/rename tasks from the first BEP-2 falsification workload.

Recommended: fix promotion now if cheap; otherwise start with create/modify-only tasks and make rename/delete a later runner-hardening task.

Required tests if fixed:

- delete removes the target in scratch promotion;
- rename moves old path to new path in scratch promotion;
- failed verify promotes nothing;
- partial promote cannot leave scratch run repo half-mutated.

## Phase 1c - BEP Telemetry Hooks (code, before A/B)

The current `_maybe_batch_edit_turn()` can fall through silently on malformed patchsets. That is acceptable for production safety but not for BEP-2 measurement.

Add telemetry fields to the response artifact, session artifact, or driver-observable logs:

- `batch_edit_flag_enabled`
- `patchset_present`
- `patchset_absent`
- `patchset_malformed`
- `patchset_parse_error`
- `apply_failed`
- `verify_failed`
- `promote_failed`
- `promoted`
- `fell_back_to_repl`
- `task_root`
- `touched_files`

For BEP-2, a malformed present patchset counts as parse failure even if the turn later succeeds through the normal REPL path. An apply/verify failure counts against BEP treatment reliability even if the model recovers in a later turn. Record both first-failure and final verifier result.

## Phase 2 - Scratch Repo And Workload

Create a pristine template git repo under `data/bep_sandbox/template/` and tasks under `data/bep_sandbox/tasks.jsonl`.

Use **five synthetic tasks** for the first cheap falsification. Synthetic is acceptable because the gate is asymmetric:

- Failure on hand-designed sweet-spot tasks is enough to stop or rework BEP.
- Success is **not** enough for broad promotion; it only advances BEP to a mined/real-task confirmation before BEP-3.

### Task Requirements

Each task row:

```json
{
  "id": "bep_cart_total",
  "prompt": "...",
  "initial_repo_ref": "template commit or fixture id",
  "expected_files_touched": ["cart.py", "checkout.py", "tests/test_checkout.py"],
  "verifier_cmd": "python -m pytest -q",
  "quality_signal": "verifier_pass",
  "why_batch_sweet_spot": "cross-file mechanical edit with clear target",
  "disallowed_shortcuts": ["hardcode test output", "skip tests"],
  "max_turns": 8
}
```

Recommended first workload:

1. create a new helper and call it from an existing module;
2. modify two modules plus tests for a shared API rename (no filesystem rename unless Phase 1b fixed it);
3. add validation in one file and error handling in a caller;
4. update a dataclass/schema and all uses across two files;
5. add a small feature spanning module, CLI entry, and tests.

Avoid tasks that can be solved by a one-line change, pure Q&A, or prompt-only output.

### Real/Mined Confirmation Requirement

If synthetic BEP-2 is positive, add a Phase 4b confirmation with 5-10 mined/real edit tasks before BEP-3/autopilot exposure. Candidate sources:

- prior coding sessions with small multi-file patches;
- existing unit-test failures with known fix commits;
- simple SWE-style tasks that fit local CPU time;
- handoffs that already include deterministic verification.

## Phase 3 - A/B Driver

Build `scripts/benchmark/bep_ab.py`.

### Run Shape

For each task x arm x repetition:

1. create fresh scratch copy from template;
2. set `ORCHESTRATOR_EDIT_ROOT` to scratch;
3. start/restart API with the arm flag;
4. POST `/chat` with:
   - task prompt;
   - `force_role=coder_escalation`;
   - generous `max_turns`;
   - deterministic-ish inference params where supported;
5. run driver-side `verifier_cmd` in scratch;
6. collect metrics;
7. append result row immediately.

### Arm Scheduling

Do not run one monolithic baseline block followed by one monolithic treatment block.

Use blocked/randomized order to reduce wall-clock confounds:

- preferred for 2 reps: `off -> on -> on -> off`;
- preferred for 3+ reps: randomize task order within each ABBA block;
- record `block_id`, `arm_order`, API start time, git sha, topology hash, and host quiet check for every block.

One API restart per arm block is acceptable. Restart-per-task is not required unless host noise or API warmup effects are detected.

### Required Metrics

Per row:

- `run_id`
- `task_id`
- `rep`
- `block_id`
- `arm` (`baseline_interleaved` or `batch_edit`)
- `arm_order`
- `orchestrator_git_sha`
- `api_start_time`
- `topology_hash`
- `host_quiet`
- `task_root`
- `flags`
- `max_turns`
- `turns_used`
- `wall_time_s`
- `prompt_tokens_total`
- `completion_tokens_total`
- `prefill_tokens_total` if available
- `batch_edit_flag_enabled`
- `patchset_present`
- `patchset_malformed`
- `parse_fail`
- `apply_fail`
- `verify_fail`
- `promote_fail`
- `fell_back_to_repl`
- `verifier_cmd`
- `verifier_exit_code`
- `quality_pass`
- `files_touched`
- `unexpected_files_touched`
- `stdout_path`
- `stderr_path`
- `transcript_path`

Persist to:

- `data/bep_sandbox/results.jsonl` incrementally;
- `data/bep_sandbox/runs/<run_id>/` for transcripts, logs, scratch repo metadata, and verifier outputs.

## Phase 4 - BEP-2 Run And Decision (host quiet; J6 paused)

Procedure:

1. checkpoint J6/autopilot state;
2. SIGTERM J6 autopilot if pause is still unreliable (`feedback_autopilot_pause_broken_use_sigterm`);
3. confirm host quiet and no competing inference;
4. run `bep_ab.py`;
5. aggregate;
6. update this handoff, `batched-edit-parallel-apply.md`, Package J manifest rows, and progress log;
7. relaunch J6 if it still has remaining soak time.

### BEP-2 Gate

Use the original falsification thresholds:

- **PROCEED to mined/real confirmation, then BEP-3 only if confirmed**:
  - median wall-time latency >= 15% down;
  - quality within -1 percentage point;
  - parse failure <= 5%;
  - apply failure <= 2%;
  - no orchestrator repo mutation;
  - no unexpected file touch outside task root.
- **REWORK**:
  - latency win but quality -1 to -3 pp;
  - or parse/apply failures 5-15%;
  - or telemetry incomplete but results otherwise promising.
- **STOP negative**:
  - no latency win;
  - or quality < -3 pp;
  - or parse/apply/verify/promote failures > 15%;
  - or any orchestrator self-mutation;
  - or task-root isolation failure.

Record negative results explicitly. A negative is useful: it keeps `batch_edit_mode` default-off and prevents BEP-3 churn.

## Phase 4b - Real/Mined Confirmation (conditional)

Only run if synthetic BEP-2 passes.

Build a small mined set (5-10 tasks) and rerun the same driver. This confirmation decides whether BEP-3 is worth exposing to autopilot. The synthetic pass alone is not enough to update autopilot search spaces or production priors.

Gate for BEP-3 exposure:

- synthetic pass and mined/real pass both positive;
- no task-root violations;
- telemetry complete;
- per-task variance understood;
- failures explainable and below thresholds.

## Phase 5 - DCP-6 (after BEP-2 decision)

Run DCP after BEP because BEP is the cheaper falsification and validates the shared task-root harness.

### DCP Harness Differences

- Flag: `ORCHESTRATOR_DCP_PRE_ASSEMBLY` on vs off.
- Workload: delegation-heavy tasks where architect/frontdoor delegates to specialist and the specialist needs code context.
- Scratch repo is reused, but prompts must force a real delegation path rather than a direct frontdoor answer.
- DCP file reader and code search must point at scratch.
- Reactive discovery stays enabled in both arms.

### Required DCP Metrics

All BEP driver fields that apply, plus:

- `bundle_build_ms`
- `bundle_tokens_estimated`
- `bundle_tokens_rendered`
- `bundle_entries`
- `bundle_files_full`
- `bundle_files_slices`
- `bundle_files_codemap_only`
- `bundle_manifest_path`
- `top_up_count`
- `reactive_code_search_count`
- `reactive_grep_count`
- `reactive_file_read_count`
- `hallucinated_file_refs`
- `context_contamination_failures`

If top-up count is not already logged, add a counter before running DCP-6. Do not infer top-ups from prose after the fact.

### DCP-6 Gate

- **Keep advisory / consider second confirm**:
  - prefill and latency down;
  - quality >= baseline;
  - top-up rate <= 20%;
  - no increase in hallucinated file refs or context contamination.
- **Tune/re-run**:
  - quality flat but top-up > 20%;
  - bundle too small/large;
  - high omitted-file requests;
  - stale codemap or token-estimation errors.
- **Shelve / flag off**:
  - quality drop;
  - no latency win;
  - context contamination increases;
  - DCP reads production project instead of scratch;
  - telemetry missing for top-ups.

## Key Files

| Path | Role |
|---|---|
| `src/repl_environment/task_root.py` or equivalent | New shared task-root accessor; keep project-root and task-root semantics separate. |
| `src/repl_environment/file_mutation.py` | Interleaved write path; task-root writes only. |
| `src/repl_environment/file_exploration.py` | Model-facing read/list/grep path; task-root relative paths. |
| `src/repl_environment/external_access.py` | `run_shell` cwd must become task-root during A/B. |
| `src/repl_environment/environment.py` | Dynamic path validation must include task root, not stale class-level allowed paths only. |
| `src/graph/helpers.py` | `_batch_edit_repo_root()` and BEP telemetry. |
| `src/batch_edit_runner.py` | `apply_patchset_sandboxed` / `promote_sandbox`; fix or exclude delete/rename. |
| `src/api/routes/chat_delegation.py` | DCP file reader and code search root must be task-root aware. |
| `data/bep_sandbox/{template,tasks.jsonl,results.jsonl}` | Scratch repo template, workload, incremental results. |
| `scripts/benchmark/bep_ab.py` | BEP A/B driver. |
| `scripts/benchmark/dcp_ab.py` or shared driver mode | DCP A/B driver. |

## Resolved Review Questions

1. **Use `ORCHESTRATOR_EDIT_ROOT`, not a second orchestrator instance**, but define it as model-facing task root. Config/control-plane paths stay real.
2. **Use five synthetic tasks for first falsification.** Passing synthetic tasks advances to mined/real confirmation; it does not by itself justify BEP-3/autopilot exposure.
3. **Use API restart per arm block with ABBA/randomization.** Avoid one monolithic off block followed by one monolithic on block.
4. **Build BEP-2 fully first, then DCP-6.** DCP reuses the harness after BEP validates the shared task-root machinery.

## Build Checklist

- [ ] Phase 0 surface audit committed to `data/bep_sandbox/task_root_surface_audit.md`.
- [ ] Phase 1 task-root override implemented and unit-tested.
- [ ] Phase 1b runner promotion for delete/rename fixed or first workload excludes delete/rename.
- [ ] Phase 1c BEP telemetry emitted and observable by driver.
- [ ] Phase 2 scratch repo template and five tasks added.
- [ ] Phase 3 BEP driver persists incremental rows and artifacts.
- [ ] Dry run with fake/stub LLM proves task-root isolation and result schema without inference.
- [ ] BEP-2 inference run performed only with host quiet / J6 paused.
- [ ] BEP result updates this handoff, source BEP handoff, Package J manifest, and progress log.
- [ ] DCP driver/harness built only after BEP-2 decision.

## Reporting

After each phase:

- append a short result section here;
- update `progress/2026-05/2026-05-26.md` or the current day progress log;
- commit per repo with hash;
- update Package J manifest row status;
- record whether data is baseline-eligible or diagnostic-only.

The A/B run decisions update:

- `batched-edit-parallel-apply.md` for BEP-2;
- `delegation-context-preassembly.md` for DCP-6;
- `bulk-inference-campaign.md` Package J rows J7/J8;
- `routing-and-optimization-index.md` P22/P23 if task status changes.

## Builder Prompt

Use this when starting the implementation agent:

```text
You are implementing the reviewed BEP-2 / DCP-6 falsification harness. Read /workspace/AGENTS.md first and obey GitNexus requirements. Then read:

- /workspace/handoffs/active/bep-dcp-falsification-harness.md
- /workspace/handoffs/active/batched-edit-parallel-apply.md
- /workspace/handoffs/active/delegation-context-preassembly.md
- /workspace/handoffs/active/bulk-inference-campaign.md Package J rows J7/J8

Your first job is NOT to run inference. Build the harness safely.

Key decisions already made:

- Use ORCHESTRATOR_EDIT_ROOT as a model-facing task-root override, not merely a write-root.
- Keep registry/config/session/log/control-plane paths on the real project_root.
- Route model-facing reads, writes, run_shell cwd, batch-edit repo root, and DCP file discovery to the scratch task root.
- Build BEP-2 first; DCP-6 comes after BEP-2 decides.
- Use five synthetic sweet-spot tasks for cheap falsification; a positive synthetic result requires mined/real confirmation before BEP-3.
- Use API restart per arm block with ABBA/randomized ordering, not one monolithic off block then one monolithic on block.
- Do not run inference until Phase 0-3 are complete, tested, committed, and the operator approves the host-quiet run.

Implementation order:

1. Phase 0: inventory every model-facing filesystem surface and write data/bep_sandbox/task_root_surface_audit.md.
2. Phase 1: implement task-root override with default-off behavior and tests.
3. Phase 1b: fix delete/rename promotion or exclude delete/rename tasks.
4. Phase 1c: add BEP telemetry for absent/malformed/apply/verify/promote/fallback states.
5. Phase 2: create scratch repo template and five deterministic verifier tasks.
6. Phase 3: build bep_ab.py with incremental JSONL persistence and artifact directories.
7. Run only fake/stub dry-runs. Stop before real inference and report commands, tests, artifacts, and remaining host-quiet run command.

Hard gates:

- orchestrator checkout must remain unmodified by fake/model task writes;
- scratch repo must receive both baseline and treatment writes;
- DCP bundle must read scratch files when DCP flag is evaluated;
- telemetry must distinguish malformed patchset from patchset absent;
- no baseline/Pareto/scheduling priors are updated from these diagnostic harness runs.
```

---

## Build Log

- **2026-05-26 Phase 0 — surface audit COMPLETE** (orchestrator `19f8883`). `data/bep_sandbox/task_root_surface_audit.md`: 15 surfaces classified task-root vs project-root, grounded in code. Key finding — surfaces #1–#4 (write/peek/grep/list/file_info) funnel through ONE chokepoint, `_validate_file_path` (`environment.py:489`, realpath + ALLOWED_FILE_PATHS), so the relative-path + ALLOWED_FILE_PATHS redirect there covers them all; `run_shell` cwd (#5), `code_search`/ColGREP root (#7), `_batch_edit_repo_root` (#8), DCP file_reader/code_search (#10/#11) are separate swaps; `code_search`/ColGREP root flagged as possibly needing a CLI-arg.
- **2026-05-26 Phase 1 — task-root accessor FOUNDATION done** (orchestrator `3396c0b`). `src/repl_environment/task_root.py` (`get_task_root`/`task_root_active`/`resolve_task_path`) + 8 tests (default-off parity, active redirect, nonexistent-dir fallback). Foundation only — nothing calls it yet.

### NEXT (Phase 1 redirects — SECURITY-CRITICAL, do with fresh care)

Wire `get_task_root()`/`resolve_task_path()` into the surfaces, each behind `task_root_active()` (default-off parity) + an exit-gate test:
1. **`environment.py` `_validate_file_path` (#1) + `_get_allowed_file_paths` (#2)** — relative paths resolve via `resolve_task_path`; append task-root to ALLOWED_FILE_PATHS when active. ⚠️ This is the security path-validation hot path — the highest-care edit; verify default-off parity exhaustively (covers write/peek/grep/list/file_info #3/#4).
2. **`external_access.py:207` `run_shell` cwd (#5)** → `get_task_root()` when active.
3. **`code_search.py:117` `_code_search` ColGREP root (#7)** — confirm how ColGREP takes its search root (CLI arg vs cwd) first.
4. **`helpers.py:341` `_batch_edit_repo_root` (#8)** → `get_task_root()`.
5. **`chat_delegation.py` `_maybe_dcp_seed_context` file_reader + code_search (#10/#11)** → `get_task_root()`.
Then run the 8 Phase-0 exit-gate tests. Phases 1b (BEP delete/rename promotion fix-or-exclude), 1c (BEP telemetry states), 2 (scratch repo + 5 tasks), 3 (`bep_ab.py`) follow. STOP before real inference (host-quiet approval required).

- **2026-05-26 Phase 1 — surface redirects COMPLETE** (orchestrator `b15e2b5`). All 6 model-facing surfaces honor `get_task_root()`/`resolve_task_path()` when `task_root_active()`, default-off parity otherwise: `_validate_file_path` #1/#2 (covers write/peek/grep/list/file_info), `run_shell` cwd #5, `code_search` #7 (index-free scratch walk — ColGREP/NextPLAID are indexed over the prod corpus so can't search scratch), `_batch_edit_repo_root` #8, DCP file_reader #10. **Verification**: 8 active-behavior exit-gate tests (`test_task_root_surfaces.py`: relative→scratch resolve, run_shell cwd=scratch, code_search returns scratch, batch repo_root=scratch) + dcp4 tests updated to the real env mechanism + **246-test default-off parity sweep** (code_search/file_mutation/external_access/environment/file_exploration unchanged when env unset). Phase-0 exit-gate checklist items 1-6 covered by tests; 7-8 (control-plane real, checkout unchanged) hold by construction (only task-root surfaces switched; control-plane keeps `_get_project_root`) + the parity sweep.

### REMAINING (next increments)

- **Phase 1b** — BEP delete/rename promotion: check `promote_sandbox` handles delete (remove from live) + rename (move), else exclude delete/rename from the Phase-2 tasks. Decide fix-or-exclude.
- **Phase 1c** — BEP telemetry: `_maybe_batch_edit_turn` must distinguish + record {patchset absent, malformed, apply-failed, verify-failed, promote-failed, fallback}. **Hard gate: malformed ≠ absent.** Currently both return None indistinguishably.
- **Phase 2** — `data/bep_sandbox/template/` scratch repo + 5 deterministic synthetic sweet-spot tasks (`tasks.jsonl`) with independent verifiers.
- **Phase 3** — `scripts/benchmark/bep_ab.py`: per task×arm, reset scratch, set `ORCHESTRATOR_EDIT_ROOT`, restart API with flag (ABBA/randomized ordering), `/chat` force_role=coder_escalation high max_turns read `answer`, run verifier, incremental JSONL + artifact dirs.
- Then stub/fake dry-runs only. **STOP before real inference** (Phases 0-3 complete+tested+committed+explicit host-quiet go-ahead — hard gate).

- **2026-05-26 Phases 1b/1c/2/3 — COMPLETE + dry-run-validated.** 1b: delete/rename promotion fixed in batch_edit_runner (ApplyResult.deleted_paths/renamed_paths; promote unlinks deletions+rename-sources) + 2 tests (`618d38a`). 1c: `_maybe_batch_edit_turn` records distinct states (absent vs malformed [the hard gate], applied/verify_failed/apply_failed/promote_failed) via `_BATCH_EDIT_STATE_COUNTS` + 2 tests (`618d38a`). 2: `data/bep_sandbox/tasks.jsonl` — 5 deterministic tasks (create/multi-file-modify×2/rename/bugfix), each verifier validated to fail-initial/pass-solution (`36cefeb`). 3: `scripts/benchmark/bep_ab.py` — ABBA arm-block ordering, fixed scratch reset per task×arm×rep, incremental JSONL, PYTHONDONTWRITEBYTECODE; HARD inference gate (real run refused without --host-quiet-confirmed + no autopilot); **stub dry-run: 20 rows all verifier-PASS** (`2729b11`). **All Phases 0-3 done; real BEP-2 A/B awaits J6-paused + operator host-quiet go-ahead.** (Note: the live A/B's ORCHESTRATOR_EDIT_ROOT changing topology will make the matrix "stale" — use the standalone path or accept diagnostic mode, as the dual-half probe did.)
