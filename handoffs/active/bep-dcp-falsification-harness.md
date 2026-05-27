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

## BEP-2 Real-Run Investigation & PARKING (2026-05-27)

Operator granted host-quiet go-ahead; J6 paused; ran the first real BEP-2 A/B. **The "stub-validated"
harness had multiple real-path defects that stub mode structurally could not catch (stub bypasses
`_chat` and the REPL entirely).** Four distinct issues found, in order:

1. **mock_mode** (FIXED `22b03c0`) — `bep_ab._chat` payload omitted `mock_mode:false`/`real_mode:true`;
   `ChatRequest.mock_mode` defaults True (safety), so every "response" was `[MOCK] Processed prompt…`
   at ~0.02s. Real `/chat` verified working (`PONG`).
2. **force_mode** (FIXED `c407137`) — payload omitted `force_mode:"repl"`; coder routed to `direct`
   (turns=1, prose/code-block answer, no edits), so the batch-edit divergence (`helpers.py:852`) was
   never reached and quality was 0 in BOTH arms.
3. **baseline doesn't edit** — with real+repl, the OFF/baseline coder returned the code as a FINAL()
   text answer and never wrote a file (turns=3, scratch empty). The ON arm only "won" because the
   batch rider forces a structured patchset. Added a symmetric **`interleaved_edit_rider`** feature
   flag + per-turn rider (`1bad0e1`: `batch_edit_parse` instruction/builder, `features` flag+field,
   `helpers._execute_turn` gated `elif`, `bep_ab` per-arm wiring). Production-safe (default-off).
   Result: model now ATTEMPTS edits but **loops to turns=8 max without writing**.
4. **write target not redirected** — `_file_write_safe` (`file_mutation.py`) only *validated* the
   resolved scratch path but *wrote to the raw `path`* (process-cwd-relative). Phase 1 wired path
   VALIDATION but never rewrote the WRITE TARGET. Fixed to `resolve_task_path(path)` when
   `task_root_active()` (`1bad0e1`, default-off parity, gitnexus LOW). **No effect on the symptom** —
   baseline still turns=8, no file in scratch.

**PARKED — and the park stands.** I wrote this up as "root cause unconfirmed / REPL behavior not
observable from logs"; the operator review below showed that was **WRONG on both counts**. Park decision
was still correct (stopping beat blind patching), but the diagnosis was already available.

### Operator review (2026-05-27) — corrections + BINDING rework plan
Operator reviewed + reproduced the failures.

- **ACTUAL root cause of #3/#4:** `INTERLEAVED_EDIT_INSTRUCTIONS` (`batch_edit_parse.py:~61`) told the
  model to use `open("…","w")`, but the REPL security layer **forbids `open()`** (`security.py`
  FORBIDDEN_CALLS includes `open`). The baseline coder literally could not write — it looped doing
  `content = …; FINAL("done")` (plainly visible in `/mnt/raid0/llm/tmp/repl_tap.log:~41489`) → turns=8.
  The `_file_write_safe` write-redirect (#4) was irrelevant — the model never reached that surface. **The
  rider must require `file_write_safe(...)` and explicitly forbid `open()`.**
- **My "not observable" claim was wrong:** `repl_tap.log` (1.3 MB) had the per-turn trace the whole time;
  I only checked `orchestrator.log` (HTTP access lines). The "needs observability-first instrumentation"
  framing was over-stated — the tap already exists; it just needs to be *read* and *attached to artifacts*.

**Operator findings — fix ALL before any rerun:**
1. **[High] Task-root isolation is LEAKY.** `_validate_file_path` (`environment.py:~500`) *appends* the
   scratch root to the global `ALLOWED_FILE_PATHS`, so with task-root active `/tmp/outside_abs.py` and
   `../outside.py` STILL validate (reproduced). Required behavior: when `task_root_active()`, the allowed
   set must be the **scratch root ONLY** (drop the global prefixes) so writes outside scratch are rejected.
2. **[High] Stub dry-run validated nothing real.** Stub writes known-good solutions directly
   (`bep_ab.py:64`), bypassing `/chat`, routing, REPL, mode selection, and the model write tools — exactly
   why mock_mode/force_mode/file-write semantics escaped until live inference. The "exercises full plumbing"
   claim (`bep_ab.py:15`) is false; stub only covers scratch-reset + verifier + ABBA sequencing.
3. **[High] Baseline rider points at a blocked API** (root cause above) → rewrite around `file_write_safe`,
   forbid `open()`.
4. **[Med] Behavior was observable** → attach per-session `repl_tap.log` slices to bep_ab artifacts.
5. **[Med] bep_ab rows can't support the formal gate.** Rows record a small subset (`bep_ab.py:179`); the
   gate needs topology_hash, flags, transcript paths, touched files, parse/apply/promote state (this
   handoff's Artifact schema, ~L290). Current rows are diagnostic-only, not decision-grade.
6. **[Med] Missing regression test:** with `ORCHESTRATOR_EDIT_ROOT=<tmp>`, `_file_write_safe("cart.py", …)`
   must create `<tmp>/cart.py`, NOT cwd/project-root (existing mutation tests use absolute paths only —
   `test_repl_file_mutation.py:101`).

**Binding gate before resume (operator):** (a) fix the task-root leak #1; (b) rewrite the interleaved rider
around `file_write_safe`, forbid `open()` #3; (c) attach per-session REPL-tap slices to bep_ab artifacts #4;
(d) expand bep_ab row schema to full gate fields #5; (e) add the `_file_write_safe` task-root regression
test #6; (f) add a **no-inference real-path canary** — POST `/chat` with mocked deterministic LLM outputs,
asserting `mock_mode=false`, `real_mode=true`, `mode=repl`, scratch writes in BOTH arms, and **no outside
path validates**; (g) THEN one **live single-task smoke** before any full ABBA. **No valid BEP-2 result may
be inferred from the existing runs.**

Prior fixes (`22b03c0`, `c407137`, `1bad0e1`) stand and are production-safe (all flags default-off). **DCP-6
stays parked** (reuses this harness). Invalid runs quarantined under `data/bep_sandbox/INVALID-*`.

### Also resolved this window (not BEP)
- **n_way size-2 cross-role re-bench: NOT NEEDED** (closed). The `pairs:` matrix uses *full* instances
  (idx0), which were always correctly pinned; the affinity bug only mis-pinned *quarters* (already
  re-benched: within-role `9a414a9`, n_way size-3+ `4363dae`). The "J4b/J4c re-run pending" prose flag
  was over-conservative for the size-2 full-pair cells.

## Rework-gate execution (2026-05-27, cont.) — leak fix + canary DONE; OFF arm STILL blocked

Worked the operator gate, no-inference pieces first (commit orch `f7a2cb0`, all production-safe / default-off):
- **(a) task-root isolation leak FIXED** — `_validate_file_path` allows the scratch root ONLY when
  `task_root_active()` (was appending it to the global `llm_root`+`/tmp` set; scratch lives under `/tmp`
  so every outside path validated). `/tmp/x`, `../x`, the orchestrator tree now rejected; realpath both
  sides. **Verified non-vacuous**: reverting the fix makes the canary + regression escape-tests FAIL.
- **(b) interleaved rider REWRITTEN** → instruct `file_write_safe(path, content)`, explicitly forbid
  `open()` (the original rider pointed at `open()`, which `security.py` forbids).
- **(e) regression tests** (`test_task_root_surfaces.py`): write lands in scratch / escapes rejected /
  outside-path validation rejected when active.
- **(f) no-inference CANARY** (`test_bep_canary.py`, 6 tests): real-mode-not-mock, force_mode=repl accepted,
  REPL write→scratch, outside write rejected, `open()` forbidden. **338 REPL/file/task-root parity tests +
  6 canary green.**
- **`_log_append`** hardened: redirect under scratch when task-root active (parity otherwise) + reject
  non-basename `log_name` (pre-existing `../../etc/passwd` traversal that `_validate_file_path`'s `/mnt/raid0/llm`
  prefix had allowed).

**(g) live single-task smoke (J6 paused, host quiet, affinity certified) — t1, BOTH arms via real `/chat`:**
- **ON arm (batch_edit=1): PASS** — turns=2, `mathutil.py` written to scratch, verifier PASS. The harness,
  scratch, task-root, write path, and verifier all work end-to-end with real inference.
- **OFF arm (interleaved_rider=1): STILL FAILS** — turns=8 (max), `[Max turns reached]`, scratch empty,
  verifier fail. **The rider rewrite did NOT fix it.**

**Refined diagnosis (still not a confirmed fix path — do not patch blind):** the OFF-arm turns produced
**zero `repl_tap.log` entries** across all 8 turns (the tap at `helpers.py:985` fires only when the model
output is extracted as executable REPL *code*). Combined with the operator's earlier `content=…; FINAL("done")`
observation, this means the real coder in interleaved mode emits prose/non-tool output that never reaches
`execute()` → never calls `file_write_safe` → loops to max turns. Since the CANARY proved
`file_write_safe`→scratch works when *called*, the problem is purely that **the real coder will not drive the
interleaved tool loop for these tasks** — it strongly prefers emitting the whole artifact (which is exactly
why the ON/batch arm succeeds in 2 turns). This may be a genuine finding (interleaved is not this coder's
natural grain) rather than a harness bug.

**True remaining blocker = OFF-arm REPL-turn observability.** `repl_tap.log` did not capture the OFF-arm
turns in the reloaded-API path (the ON arm returns early before the tap; the OFF arm apparently never reaches
it). Next rework step (observability-FIRST, before ANY further baseline change): instrument the OFF-arm
executor path directly — log, per turn, the raw model output and whether/why it is or isn't extracted as
executable code — to confirm the "emits-prose, never-calls-a-tool" hypothesis. THEN decide: (i) a stronger
interleaved prompt/few-shot that forces tool calls, or (ii) accept that batch-edit is the only viable mode for
this coder and reframe BEP-2's claim accordingly. **(c) repl_tap→bep_ab artifacts and (d) full bep_ab row
schema are downstream of a working OFF arm — deferred until then.** Smoke log: `logs/bep_smoke_*.log`.

### RESOLVED (2026-05-27) — OFF arm fixed; the "emits-prose / not-its-natural-grain" diagnosis was WRONG

Added flag-gated per-turn observability `_bep_turn_trace` (`helpers.py`, env `ORCHESTRATOR_BEP_TURN_TRACE=1`,
default-off, commit `0958436`) capturing the raw model output + whether it calls `file_write_safe`/`open`/`FINAL`.
It cracked the OFF-arm failure through **three** layers, each correcting a prior guess:
1. **Layer 1 — empty output + timeout.** The OFF turns produced EMPTY model output and `chat_completions
   stream … timed out`, NOT prose. The "emits-prose, never-calls-a-tool" writeup above was **wrong**. Cause:
   the rider said "do NOT answer with a code block", but the REPL turn stops at the closing ```` ``` ```` fence
   (`helpers.py:750-752`); with no fence the stop never fires → generation runs to the limit → timeout → empty.
2. **Layer 2 — unclosed block.** A code-block rider made the model emit the correct
   `file_write_safe(...)` + `FINAL("done")` in ONE block, but the REPL early-stops on `FINAL(` (`helpers.py:757`)
   BEFORE the closing fence → unclosed block → extraction fails → no execute → loop → timeout (file_write_safe
   was *present* in the output but never ran; the canary had already proven it works when executed).
3. **Layer 3 — FIX.** One-action-per-turn rider (write in a CLOSED block, `FINAL` on a separate turn; commit
   `f3fefd1`). The block closes → executes → file written.

**Live smoke now PASS/PASS** (J6 paused, host quiet, affinity certified): **OFF arm turns=1, "Wrote 32 bytes
… mathutil.py", verifier PASS**; ON arm turns=2, verifier PASS. `repl_tap` now captures the OFF turns (closed
block reaches `execute()`). **The interleaved baseline IS viable for this coder** — the parked
"not-its-natural-grain" reframe is retracted.

**Status: UNPARKED for harness validation.** Gate items DONE: (a) leak fix, (b) rider, (e) regression, (f)
canary, observability, (g) single-task smoke PASS/PASS. **Remaining before a decision-grade A/B:** (c) attach
per-session `repl_tap`/`bep_turn_trace` slices to bep_ab artifacts; (d) expand bep_ab rows to the full schema
(topology_hash/flags/transcripts/touched-files/parse-apply-promote); then run the full 5-task ABBA across both
arms and evaluate the BEP-2 gate. (Note: the OFF arm's `file_write_safe` content must match the task exactly —
multi-file/modify tasks t2/t3/t4 not yet smoke-tested; do that within the full ABBA.) Obs logs:
`logs/bep_obs*.log`, `logs/bep_smoke2_*.log`; trace: `$tmp_dir/bep_turn_trace.jsonl`.

### (c)+(d) DONE + full ABBA in-flight (2026-05-27)

`bep_ab` is now decision-grade (`e88429d`): (c) real runs set `ORCHESTRATOR_BEP_TURN_TRACE=1` and save each
task's per-turn trace slice to `<out>/traces/<task>-<arm>-blkN.jsonl`; (d) full per-row schema (flags,
`topology_hash`, `touched_files`, `batch_edit_states` parsed from `orchestrator.log`, trace summary) + run-level
`meta.json` with an `orch_checkout_unchanged` proof + a final BEP-2 gate computation. Stub dry-run validated.

**Full 5-task ABBA launched** (`results-abba-20260527-074259`; J6 paused trial 25, affinity certified).
**Early in-flight finding:** OFF arm `t1_create_util` PASS (turns=1, wrote file); OFF arm `t2_add_and_use`
(multi-file) FAIL (turns=8, touched=[]). **The one-action-per-turn rider works for single-file create but does
NOT yet generalise to multi-file/modify (t2/t3/t4).** Per `feedback_observe_before_diagnosing`, NOT diagnosed
yet — the per-task trace artifacts are captured; diagnose from `traces/t2_add_and_use-off-*.jsonl` (what the model
emits across the 8 turns) AFTER the run, then refine the rider for multi-file (likely: write each file in its
own closed block across turns, FINAL only after all writes confirmed). Gate verdict pending run completion. The
**harness is validated** (single-file both arms PASS); the multi-file OFF-arm generalisation is the open item for
a decision-grade A/B. DCP-6 still downstream (reuses harness).

**ABBA stopped at 8/20 + multi-file finding (2026-05-27, evidence-grounded from traces).** Killed the run once
the pattern was clear (saved ~20 min of timeout). Partial dataset preserved: `results-abba-20260527-074259/`
(8 rows + `traces/` + `meta.json`, `orch_checkout_unchanged=true`). Results: only **t1_create_util passes (both
arms)**; **t2–t5 fail the OFF arm** (turns=8, touched=0) and **t2 also fails the ON arm** (turns=3, touched=0).
**Cause (observed in `traces/t2_add_and_use-off-blk0.jsonl`):** for tasks that require reading existing files
first (modify/add/rename/bugfix), the OFF coder emits a `peek('calc.py')`/`peek('main.py')` read block — then
re-emits the *identical* read block every turn for 8 turns, never calling `file_write_safe`, never `FINAL`. It
loops on the READ step. t1 passes only because "create file with exactly X" needs no read. **OPEN (hypothesis,
do not write as fact until confirmed from the tap):** whether the `peek` *result* is fed back into the next
turn's prompt (`last_output`) or the model ignores it — confirm via `repl_tap.log` (which logs executed code +
RESULT) for a t2 session, OR add the peek result to `_bep_turn_trace`. **Two other open items surfaced:** (i)
`batch_edit_states` came back empty in rows (`be=-`) — the (d) telemetry parse from `orchestrator.log` isn't
capturing the `batch_edit_state=` lines (offset/worker-log issue) — fix before trusting parse/apply rates; (ii)
the ON/batch arm also fails the multi-file tasks (t2), so this is NOT purely an OFF-rider problem — the 5 tasks /
verifiers / read-feedback path need review. **The harness mechanics are validated (t1 both arms); the read-loop
on multi-file tasks is the next blocker for a decision-grade A/B — diagnose from the tap, do not blind-fix.**
J6 resumed on production (pid 2350351).

### Read-loop ROOT-CAUSED + FIXED (2026-05-27, flag-gated) — supersedes the "OPEN hypothesis" above

Diagnosed from the parked traces (operator pushed back on the deferral — and rightly: the diagnosis needed **no inference**, only reading `bep_turn_trace.jsonl` + `repl_tap.log`). **Both failure modes are harness bugs — not model capability, not "interleaved-baseline unviable":**

- **A — write-loop / "timeout":** `_execute_turn` (helpers.py:~757) sets `_early_stop_check = FINAL( or CALL( detected`, which aborts streaming the instant `FINAL(` appears — *before* the closing ` ``` ` fence. When the model emits `file_write_safe(...)` + `FINAL("done")` in one block (trace TASK #2), the raw output ends unclosed → `extract_code_from_response` returns nothing → identical re-prompt → 6 repeats → stream timeout. Tasks that write *without* FINAL in the block (TASK #3/#4) keep their fence and succeed in one turn.
- **B — read-loop:** confirms the prior hypothesis. The `peek()` output IS fed back (the general `repl_tap.log` shows `NameError`/`ValueError` returned to the model), but the REPL has **no identical-non-advancing-turn breaker**, so the model re-emits the identical read until the turn budget burns out. Confirmed beyond BEP: `repl_tap.log:86–101`/`:427–439` show unknown-tool / undefined-name calls looping 3× identically.

**FIX (orchestrator `3e9ab5e`, flag-gated default-off via `ORCHESTRATOR_REPL_LOOP_GUARD=1`):**
- Fix A `_repair_unclosed_code_fence`: closes an unclosed ` ``` ` fence before extraction (preserves the token-saving early-stop; only changes the currently-broken case).
- Fix B `_loop_guard_repeat` + prompt nudge: counts identical non-advancing turns and injects a "LOOP DETECTED — act on what you read, or FINAL" nudge once it repeats, instead of silently re-prompting.
- 9 unit tests (`tests/unit/test_repl_loop_guard.py`) + 88 neighbor tests green. `_execute_turn` is gitnexus-CRITICAL (14 impacted / 9 processes) → flag-gating keeps prod a true no-op until validated. `bep_ab.py` enables the flag for both A/B arms.

**Status: loop-guard verification FAILED (2026-05-27 host-quiet A/B `results-abba-loopguard`).** The flag-gated loop-guard did NOT fix the multi-file loop — OFF-arm multi-file tasks still emit byte-identical `peek()` blocks for all 8 turns (fresh trace `results-abba-loopguard/traces/t2_add_and_use-off-blk0.jsonl`; t1 single-file create still passes in 1 turn). **Env-propagation ruled OUT** (I'd wrongly named it the prime suspect): `orchestrator_stack.py:976` builds the API env as `os.environ.copy()` (full passthrough, no allowlist) and `ORCHESTRATOR_BEP_TURN_TRACE` (set the same way) reached the API — traces were written — so `ORCHESTRATOR_REPL_LOOP_GUARD` reached it too. The loop-guard CODE ran; the **advisory nudge just didn't override the model's greedy read-first prior**. **Lead (UNCONFIRMED — not a finding):** `last_output` IS passed to the prompt builder (helpers.py:679-682) but is compressed (649) and old `<<<TOOL_OUTPUT>>>` blocks are stripped (296-350) — the model may be losing the file contents it read, hence re-reading. Next (no third reflexive patch): confirm whether the `peek` result survives into turn-2's actual prompt, THEN a deliberate fix (preserve the most-recent tool output, or a hard loop-break — not another nudge). Fix `3e9ab5e` stays flag-gated **default-OFF** (zero prod effect; loop-guard NOT enabled for J6). (Secondary: `batch_edit_states` `be=-` capture gap.) DCP-6 downstream.
