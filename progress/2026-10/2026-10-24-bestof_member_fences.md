# 2026-10-24 bestof_member_fences

## OAB-28: best-of member `ak-check` fence

- Audited fresh root origin `7aad76d1a` and research origin `eb753e422`; the shared
  research checkout was dirty and behind, so review used an isolated worktree at the
  fetched research origin.
- The race fix is already in research commit `48ed3f77a` (2026-09-29): a pool with
  multiple sibling lanes has one worker-root fence; `pool.drive` gives member and winner
  checks that scheduler-visible fence through `AK_CHECK_FENCE`, and multi-worker
  best-of enables tail fencing. This shared-fence topology supersedes the old handoff's
  “disjoint fence directories” wording while preserving its safety intent.
- Added a controlled temporary-fence regression in research commit
  `9b4ddb6f2e4419c0ff29c08085ed2d83aae762b2`. With two logical members holding slots
  at once, the tail remains blocked after member A releases while B still holds its
  slot; after B releases, the tail enters and refuses both members' checks.
- Official grant `codex-ni-oab-fences-20261024` passed all 3 focused tests in 1.03 s:
  3 passed, 0 failures, 0 errors, 0 skips. JUnit:
  `/mnt/raid0/llm/tmp/codex-ni-20261024-oab28/evidence/run.jFtwMY4S/results.xml`.
- The tested source commit was published to research `main` via promotion commit
  `413f5b7f545b67e69ba9082b9a6c73514eb3a3f2`; remote `main` verified at that SHA.
  No production, scheduler, or kernel code changed. No real actor/model run was used.
- Prepared this root closeout worktree from fetched root `origin/main`
  `4ecf1780b7bc6648b705316702d25a730e89dfe5` for the owning main's handoff/index
  reconciliation. The README freshness check completed without warnings.
- Regenerated handoff index state; `index_state.py --check` passed with 0 problems.
  Its unchanged advisory output reports 138 handoffs without a declared `Scratch`
  field. Focused cite-check exited 0 (6 citations, 4 ok and 2 pre-existing review
  citations, intake-2386/2389). Vidya sync freshness is current at intake-2510 with
  lag 0. No README freshness warnings.

## Root handoff closeout

The owning main preserved OAB-28's original task text, checked it off with the date,
and documented why the actual shared-fence safety property supersedes the old
“disjoint” directory wording. The INF-78 next action now lists OAB-29/30 and OAB-34;
all other actions and dependencies remain intact. The generated master rollup now
reports 1174 open inference-research tasks (down from 1175). Do not represent the mock
two-member test as a live-model best-of run.
