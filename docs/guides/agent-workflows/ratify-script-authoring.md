# Ratify and apply scripts - authoring rules

For scripts under `scripts/operator/` that an operator runs to sign a ratification and land its commits (for example `run_ak_q38fn_floor_accept_20261109.sh`). The signing rules themselves (human-only, typed operator name) live in `scripts/operator/lib/ratify_operator.sh` and `agents/shared/OPERATING_CONSTRAINTS.md`; this page holds only the landing rules.

- **Fetch and rebase immediately before the push, not only at startup.** A base fetched when the script starts goes stale while tests and the typed `RATIFY` confirmation run, and `origin/main` moves every couple of minutes. Do fetch, rebase and `serialized_push.py --agent <id> --repo . --push` as one step, then fetch again and prove the commit is an ancestor of `origin/main` before printing success. A refused push means re-run (applied items are skipped); never force. (origin: 2026-11-09 AutoKernel ratifications)
- **A `!` command has no TTY.** TTY-gated scripts refuse under `!`; hand the operator the command for a separate terminal, not chained with `&&`. Already canonical in `agents/shared/OPERATING_CONSTRAINTS.md` (origin INC-20260929-tty-gated-operator-scripts); stated here only so authors see it.
- **Pre-validate end to end** with the script's dry run (throwaway worktrees, nothing pushed) before handing it over; a failed operator-presented command is an agent defect.
