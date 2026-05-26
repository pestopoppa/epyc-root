# BEP-2 / DCP-6 Falsification-Harness Construction

status: DRAFT (awaiting operator review before build) — 2026-05-26
owner: claude (this session) · review: operator
related:
  - handoffs/active/batched-edit-parallel-apply.md  (BEP source; BEP-1/4/5 merged, _execute_turn divergence wired ea5f010)
  - handoffs/active/delegation-context-preassembly.md  (DCP source; DCP-1/2/3 merged, DCP-4 wired 31ea6d4)
  - data/bulk_inference_2026_05_26/execution_manifest.jsonl  (Package J rows J7/J8)

## Why this exists

The BEP (J8) and DCP (J7) code is wired behind default-off flags + unit-tested, but their
**inference falsification gates** (BEP-2, DCP-6) cannot be run with what's on hand. Two gaps,
discovered 2026-05-26 while attempting to launch BEP-2:

1. **No multi-file-edit workload.** The eval suites are Q&A benchmarks (MMLU / math /
   coding-*answer*). `batch_edit_mode` only diverges when the root LM emits a fenced
   ```patchset for *file edits* — those suites never do, so they can't exercise (or measure)
   the batch path.
2. **The live edit paths write to the orchestrator's own repo.** Both the interleaved REPL
   path (`file_mutation`) and the batch path (`_batch_edit_repo_root`) resolve their write
   target from `get_config().paths.project_root` = the orchestrator repo. Running free-form
   model-generated edits there is unsafe (the model could modify orchestrator code). The only
   existing redirect, `ORCHESTRATOR_PATHS_PROJECT_ROOT`, *also* relocates the registry / tool
   config / repl sessions / logs (all derived from project_root) → breaks the orchestrator.

So BEP-2/DCP-6 are **build-then-run**. This handoff tracks the harness construction so the
experiments are *safe* (no orchestrator self-mutation) and *fair* (both arms identical except
the flag), and so a flawed harness doesn't yield a wrong keep/kill verdict.

## Hard invariants (must hold)

- **Sandbox isolation**: during an A/B, ALL model-driven file writes (both arms) land in a
  throwaway scratch git repo — NEVER the orchestrator's `project_root`. Verified before any
  inference run.
- **Config untouched**: the edit-root redirect must NOT move registry / tool config / repl
  sessions / logs — only the file-write target. (This is the crux; see Phase 1.)
- **J6 paused during inference** (`feedback_no_concurrent_inference`): the *build* is
  concurrent-safe with the J6 soak; only the actual A/B runs require a quiet host.
- **Independent verifier** (`feedback_no_concurrent_inference` §, BEP audit #7): task success
  is judged by a deterministic test/check, never by the applying model.
- **Fair max_turns**: the interleaved arm needs enough turns to finish multi-edit tasks; the
  batch arm is ~1 turn. Set `max_turns` generously so interleaved isn't truncated (else the
  latency/quality comparison is rigged). Record turns used per arm.
- **Fresh repo per run**: reset the scratch repo to its pristine state before every task×arm.

## Phase 1 — Narrow, safe edit-root override (code, ~½ day)

Add an env-gated edit-root that redirects ONLY file writes, leaving config/logs/patches alone.

- New accessor `_get_edit_root() -> Path`: returns `os.environ["ORCHESTRATOR_EDIT_ROOT"]` if
  set (+ exists), else `get_config().paths.project_root`. Default unset → **zero behavior
  change** (production keeps editing project_root, the current self-modification behavior).
- Use `_get_edit_root()` ONLY in the actual write path:
  - `src/repl_environment/file_mutation.py` — the `_file_write_safe` resolve + path validation
    (NOT the `logs/` (line 54), `orchestration/patches/` (144/191/241/298), or subprocess `cwd`
    (157/253/264) uses — those stay on `_get_project_root()`).
  - `src/graph/helpers.py:_batch_edit_repo_root()` — honor the same override.
- **Audit needed**: enumerate every code path the REPL uses to write a file (there may be more
  than `_file_write_safe`), so the interleaved arm is fully sandboxed. Grep `_get_project_root`
  + any `open(...,'w')` / `Path.write_text` under `repl_environment/`.
- Unit test: with `ORCHESTRATOR_EDIT_ROOT=/tmp/x`, a write lands in `/tmp/x`; logs/patches
  still resolve under project_root; unset → project_root.
- **Commit** this alone (flag-gated, default-off, no behavior change) before touching anything
  else. Checkpoint.

## Phase 2 — Scratch repo + workload (~½ day)

- A pristine template git repo under `data/bep_sandbox/template/` (committed; small).
- **3–5 tasks**, each: `{id, prompt, files (initial state), verifier_cmd, expected}`. Cover the
  batch-edit sweet spot — multi-file edits with cross-file dependency:
  - e.g. "add `def total()` to `cart.py` and use it in `checkout.py`; running `python -m pytest`
    passes test_total".
  - Mix: 1 single-file create, 2 multi-file modify, 1 modify-with-dependency, 1 rename.
- `verifier_cmd` is a deterministic check (pytest / python -c / grep), run in the (promoted)
  scratch repo → pass/fail = quality signal. Independent of the model.
- Store as `data/bep_sandbox/tasks.jsonl`. Document each task's intent + why it exercises batch.

## Phase 3 — A/B driver (~½ day)

`scripts/benchmark/bep_ab.py`:
- For each task × arm (off/on) × repetition: reset scratch repo → pristine; set
  `ORCHESTRATOR_EDIT_ROOT` to the scratch copy; restart API with `ORCHESTRATOR_BATCH_EDIT_MODE`
  = 0 (baseline) / 1 (treatment) (flag is per-process → arm = API restart, batched across tasks);
  POST `/chat` (field `prompt`, `force_role=coder_escalation`, high `max_turns`, read `answer`);
  run `verifier_cmd`; record.
- Metrics per (task, arm): turns (round-trips), end-to-end latency, prefill tokens (from
  `_meta`), parse-failure (patchset present-but-malformed), apply-failure (sandbox apply/verify
  fail), quality (verifier pass 0/1).
- Aggregate: median latency Δ, quality Δpp, parse-fail rate, apply-fail rate, mean turns Δ.
- **Persist incrementally** per (task, arm, rep) to `data/bep_sandbox/results.jsonl`
  (`feedback_incremental_persistence`).

## Phase 4 — Run + decide (host: J6 PAUSED)

Falsification gate (from batched-edit-parallel-apply.md):
- **PROCEED → BEP-3**: batch latency ≥15% down AND quality within −1pp AND parse ≤5% AND apply ≤2%.
- **REWORK (loop BEP-1)**: latency win but quality −1..−3pp OR parse/apply 5–15%.
- **STOP (NEGATIVE)**: no latency win OR quality < −3pp OR failures > 15% → flag off permanently,
  record the negative result in batched-edit-parallel-apply.md.

Procedure: SIGTERM the J6 autopilot (checkpoint first; `pause` is a no-op — `feedback_autopilot_pause_broken_use_sigterm`) → confirm host quiet → run `bep_ab.py` → record + commit → relaunch J6.

## Phase 5 — DCP-6 (sibling, after BEP-2 decides)

Same harness shape, different knob + workload:
- Flag: `ORCHESTRATOR_DCP_PRE_ASSEMBLY` on vs off.
- Workload: delegation-heavy tasks (architect → specialist) where the specialist needs code
  context. Reuse the scratch repo + tasks framed as delegations.
- Extra metric: **top-up rate** (specialist reactive `code_search`/grep calls after the seed) —
  needs counting; check whether it's already logged, else add a counter.
- Gate: prefill+latency DOWN AND quality ≥ baseline AND top-up ≤ 20% → keep advisory (consider
  seed-primary after a 2nd confirm); quality flat but top-up > 20% → tune discovery depth /
  ColGREP top-k / per-role budget, re-run; quality DROP or no latency win → shelve, flag off.

## Key files

| Path | Role |
|------|------|
| `src/repl_environment/file_mutation.py` | interleaved write path → add `_get_edit_root()` (Phase 1) |
| `src/graph/helpers.py` | `_batch_edit_repo_root()` → honor override; `_maybe_batch_edit_turn` (wired ea5f010) |
| `src/batch_edit_runner.py` | `apply_patchset_sandboxed` / `promote_sandbox` (repo_root arg — already param) |
| `data/bep_sandbox/{template,tasks.jsonl,results.jsonl}` | scratch repo + workload + results (Phase 2/3) |
| `scripts/benchmark/bep_ab.py` | A/B driver (Phase 3) |

## Open questions for review

1. **Edit-root override scope** — OK to add `ORCHESTRATOR_EDIT_ROOT` (default unset = today's
   behavior)? Or prefer a different isolation (e.g., run the whole A/B against a *second*
   orchestrator instance pointed at a sandbox project_root, accepting the config-copy cost)?
2. **Workload realism** — are 3–5 synthetic edit tasks an acceptable falsification basis, or do
   you want real tasks mined from prior coding sessions / a SWE-style set?
3. **Arm = API restart** — batching tasks per arm (one restart per flag value) is efficient but
   means the two arms run at different wall-clock times; acceptable, or interleave (restart per
   task — expensive)?
4. **Scope** — build BEP-2 fully first + decide, then DCP-6? (recommended) Or both harnesses then
   both runs?

## Reporting

After each phase: append result here, update progress log, commit per-repo, report hashes.
Checkpoint (commit) after Phase 1 (override), Phase 2 (workload), Phase 3 (driver) before any
inference. The A/B run + decision updates batched-edit-parallel-apply.md (BEP-2) /
delegation-context-preassembly.md (DCP-6) + the manifest J7/J8 rows.
