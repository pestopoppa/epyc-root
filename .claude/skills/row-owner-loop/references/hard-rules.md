# HARD RULES (rendered into every subagent brief by `scripts/brief.py`)

Version line below is the marker a hook can check for. Bump it on any change.

<!-- HARD-RULES-BEGIN -->
HARD-RULES v1 (row-owner-loop, 2026-11-19)
1. Process management: kill only PIDs you started yourself and verify with `ps -p`; never `pkill`/`pgrep` by name; no service or API reloads.
2. Never launch the AutoKernel loop.
3. Never touch the frozen production trees (`/mnt/raid0/llm/llama.cpp`, whisper.cpp, qwentts.cpp) or `kernels/production/*`; never commit in the shared clone `/workspace` — work in your own worktree from `origin/main`.
4. Git: never `--force`, `prune`, `gc`, `reset --hard`, or `worktree remove --force`; pathspec-limited commits (never `git add -A` / `.`); push only via `python3 /workspace/scripts/coordination/serialized_push.py --agent <owner> --push`, branch on its exit code (never `| grep PUSH`), fetch/rebase and retry on a race; then plain `git worktree remove` + `branch -D`.
5. Write targets are literal paths (the containment hook refuses `$VAR/...`; a refused compound command skips everything after it), one write per command, verify by content.
6. No inference or timing runs outside a published row or a granted region; no local compiles without a region-lock claim or a booked build row (see BUILD below).
7. Never hand-write records under `compute-flags/grants/`, `ready/` or `operator-ratify/`; never apply a ratify bundle for real — the operator signs.
8. Rows: no copied `estimate_s`, `smoke_predicate` or `check_complete` from another row; reseal `SOURCE.sha256` after every edit; every row dir comes from `mk_ak_row.py` (never a hand copy); run `mk_ak_row.py --reseal` / `polar --lint` before publish; never run a row or its smoke by hand (`H.require_grant`).
9. Commit messages end with the session's Co-Authored-By / Claude-Session trailer lines.
10. Before hand-back: stop every background task you started (TaskStop / kill your own pid); report only what you verified.
<!-- HARD-RULES-END -->
