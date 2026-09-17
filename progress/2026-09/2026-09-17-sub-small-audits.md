# 2026-09-17 — sub-small-audits (OBS-12, KB-WM-3, VB-RUNNER-PATHS-2; zero inference)

**Worktrees.** Both are off `origin/main` and both were removed at the end:

- root `/mnt/raid0/llm/worktrees/small-audits`
- research `/mnt/raid0/llm/worktrees/small-audits-r`

No inference was run and no process was started or stopped. Two read-only Explore subagents ran the
KB-WM-3 traces: one for the index files, one for the audit log.

**Commits (all on origin/main).**

| Repo | SHA | Task |
|---|---|---|
| root | `afb9745c` | OBS-12 interpreter sweep |
| root | `4120af69` | KB-WM-3 audit and fixes |
| research | `ae92ac5c` | VB-RUNNER-PATHS-2 |

## 1. OBS-12 — skill commands and their interpreter

**Method.** Today bare `/usr/bin/python3` (3.13) imports PyYAML and numpy only from `~/.local`, which
a devcontainer rebuild can wipe (OBS-11). `python3 -s` ignores that directory and so reproduces the
failing interpreter. The sweep ran every `.claude/skills` script, plus every script that a skill
tells the user to run with bare `python3`, under that interpreter.

**Findings.**

| Instance | Without PyYAML | Fix |
|---|---|---|
| `lint_wiki`, `query_wiki`, `seed_index`, `validate_intake` | told the user to `pip install pyyaml` | refuse on stderr, naming the venv command |
| `backfill_dispositions`, `resolve_intake_id` | raw ModuleNotFoundError | same guard |
| `compile_sources` | **ignored `wiki.yaml` silently**, so the effective `skip_filenames` lost `SCHEMA.md` | raise |
| `wiki_writer_review` | ignored the `wiki_writer` block silently | raise |
| `coordinator-agent/SKILL.md`: `tmux_adapter` | traceback | venv |
| `coordinator-agent/SKILL.md`: `merge_gate` | REFUSING | venv |
| `coordinator-agent/SKILL.md`: `session_bus` | `validate` skips its roster check; other commands need the roster | venv |
| `research-intake/references/taxonomy.md` | pointed at a bare `scripts/validate_intake.py` | points at `validate_intake.sh` |

Bare `python3` is still correct for the stdlib-only targets: `worker_checkpoint`, `index_state`,
`validate_agents` and `build_claude_md_matrix`.

**Guard.** `tests/skills/test_skill_interpreters.py` has 18 cases, and 16 fail on the pre-fix tree.

**Verification.** Every fixed command was run under the venv, and none failed on an import. Three
exited non-zero for real reasons:
- `lint_wiki`: 2 dangling links (OBS-12b).
- `compile_sources --check-manifest`: manifest drift.
- `tmux_adapter probe`: `mainA` is retired.

**Related suites (pass):** `tests/skills`, the `validate_intake` suites, `validate_doc_drift` and the
post-commit KB-RAG hook tests (83 passed).

**Follow-ups.**
- **OBS-12a.** CLAUDE.md's bus `drain`/`append` commands run through the `python3` shebang, and
  `_require_roster_id` needs PyYAML, so they have the same shape.
- **OBS-12b.** The wiki links still point at the old location of `security-review-skill.md`.

## 2. KB-WM-3 — the other three files untracked by `f1717d80`

**`.index-state.json`: SAFE.** It is derived from tracked sources and never read back, so no decision
depends on it.

**`.index-graph.json`: PARTIAL.** The dashboard and `compute_ready` handle absence explicitly: the
dashboard shows it as degraded, and `compute_ready` refuses to run. Three problems were fixed in the
row check:

- **Absence was invisible.** `backlog_row_check.index_graph_readiness` stays silent by design
  (AIR-13), so its empty result meant either "not blocked" or "not screened". The new
  `index_graph_status()` puts the graph's status in the premise screener's mechanical provenance. The
  model prompt is unchanged.
- **The advisory never fired for `blocked/` handoffs.** They looked for the graph next to themselves,
  but the only graph is in `active/`.
- **A crash.** A graph that was valid JSON but not an object raised AttributeError.

**Other observations.**
- The shared checkout's graph was generated 287 handoff commits behind origin/main.
- 28 lane worktrees hold their own copies, and five are still `index_graph.v1`.

Freshness checking is filed as KB-WM-6. It needs a decision because it would reverse AIR-13.

**`logs/agent_audit.log`: PARTIAL.** Writers resolve `LOG_DIR` to the shared checkout from any lane
worktree, so entries survive `git worktree remove`. Two things were wrong:

- **The live shards were not ignored.** `.gitignore` re-included `logs/agent_audit*.log`, so the 46
  shards were untracked but not ignored. A plain `git clean -fd` would delete them all, and
  `git add -A` would re-track them. The negation is removed.
- **The frozen legacy monolith was already gone** from the shared checkout, and every summary had
  silently lost the pre-2026-08-12 history.
  - Restored with `git show f1717d80^:logs/agent_audit.log` into
    `/mnt/raid0/llm/epyc-root/logs/agent_audit.log` (4402 lines, ignored).
  - `agent_log_analyze.sh` now warns when the file is missing and prints the recovery command.

Stale comments and docs were corrected:
- `agent_log.sh` said the legacy log is kept in git.
- `session_init.sh` printed `/mnt/raid0/llm/LOGS` as the audit-log directory.
- `WORKTREE_MIGRATION.md` named only the legacy file.

**Tests.**
- `test_premise_screener.py`: +6 cases, all failing before the fix.
- `test_agent_log_merge_format.sh`: 11/11.
- Also pass: `test_index_state_readiness`, `test_backlog_row_check`, `test_row_intake`,
  `test_mech_column_audit`, `test_check_lane_worktree` and `test_worker_runner`.

**Follow-up.** KB-WM-5: `logs/.current_session` is one file shared by every agent.

## 3. VB-RUNNER-PATHS-2 — guessed-root capture loaders

Three loaders now call `belief_capture.load_capture`, which reads `EPYC_ROOT` only and refuses
otherwise:
- `score_tulving_run.py`
- `occ1/run_occ1.py`
- `score_beam_run.py`, which has the same shape and is the loader `test_beam_adapter.py` exercises.

The fallback was a live risk, not a theoretical one. The shared clone at `/mnt/raid0/llm/epyc-root`
is behind origin/main and lacks all three capture modules.

**Tests.** The tests set `EPYC_ROOT` explicitly, and 10 new cases fail on the old code.
- With `EPYC_ROOT` unset: 118 passed, 11 skipped.
- With `EPYC_ROOT` pointing at root origin/main: 124 passed, 5 skipped (pyarrow).

**Follow-up.** VB-RUNNER-PATHS-3 covers the other hard-coded root defaults in research, including the
AutoKernel `EPYC_ROOT_REPO` default of `/workspace`.

## 4. Proposed index text (not applied; the owning session applies it)

Two rows name tasks that are now closed, so their "Next action" should move on:

- `pipeline-integration-index.md` **PIP-04** (`internal-kb-rag.md`):
  `KB-WM-5 — shard logs/.current_session per AGENT_ID; KB-WM-6 graph-freshness decision (rec b); then KB-GS-1 retrieval A/B`
- `routing-and-optimization-index.md` **RTG-22** (`non-inference-backlog.md`):
  `OBS-12a — system-python3 PyYAML check in health_check.sh, and the venv in CLAUDE.md bus commands; OBS-12b wiki dangling links at next compile`
- `research-evaluation-index.md` **EVL-47** (`vidya-belief-substrate-program.md`): no change.

**State check.** `scripts/handoffs/index_state.py --check` reports one problem: FRESHNESS, meaning
the master rollup is stale after these box flips. The master regen is left to the owning session and
was not committed here.
