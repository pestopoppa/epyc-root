# Stop doing (from the 2026-11-19 autokernel session audit, Section D)

Source: `/mnt/raid0/llm/tmp/autokernel-session-audit-20261119.md`.

1. Re-typing the HARD RULES block in briefs (133 times) — `brief.py` renders `hard-rules.md`.
2. Hand-rolled per-row `until` loops (107) and more than one general watcher — one `watch_rows.sh`, re-armed.
3. Local "republish when the GPU frees" loops for dropped smokes — the allocator now owns queued
   smokes (B1); the loops create the two-runner race (B2).
4. Hand-writing records under `grants/` — send ids to Pipeline.
5. `git worktree remove --force` and `reset --hard` — dirty worktrees go to the operator with proof.
6. Reporting "published/queued" from an exit code, or "GPU idle/held" from `queue_status` text —
   prove with `ls ready/<id>.json` and `rocm-smi`.
7. Trusting a subagent's "smoke PASSed" or "pushed" — verify in hand-back triage.
8. Copying `estimate_s`, predicates or `check_complete` from a predecessor row — `row_scaffold.py --lint` flags it.
9. Booking three quarters or the whole quiet host for a 48-thread bench — width from literal threads.
10. Prose fallbacks for decisions when hook 19 misfires — use the decision tool; report the hook.
11. Waiting for the operator to ask for `/wrap-up` — wrap up at every filed result.
12. Ticking a box on a result from a different binary than the box names — that is a note.
