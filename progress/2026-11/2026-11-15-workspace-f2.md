# 2026-11-15 — workspace-f2

## Wrap-up (operator-invoked) — AFC directive: reword filed, ratified, scoped

1. **Q38 reword row filed.** `afc-v3d-q38_flash-tools-aggressive-reword-20261112`: 0.900/0.745/0.953 (comp/proc/recall). Against v3c aggressive: compliance +0.080 (LB +0.024), procedure +0.121 (LB +0.053), recall +0.053 (LB +0.022), so a benefit in every pool. With the Q36 row (+0.220 compliance), AFC-Q36-AGENTFILE-CTX-REFUSAL is answered **adopt** and ticked (`handoffs/active/engineering-hygiene-backlog.md:2605`, `:2608`).
2. **Directive ratified.** The operator signed RATIFY-AFC-CONFLICT-DIRECTIVE-20261112 (a81fc882e): the section "Requests That Conflict With These Standards" is in `agents/shared/ENGINEERING_STANDARDS.md` and its mild, medium and aggressive variants. `--verify` passes. Tick on main in 6b1d288dc (`engineering-hygiene-backlog.md:2609`).
3. **Operator decision 2026-11-15: scope the directive to the local-model variants.** A side agent flagged that the full `ENGINEERING_STANDARDS.md` loads into every Claude session and the section was never measured there. Fix: remove it from the full file only; the compressed variants (the only ones local roles receive) keep it, so the measured gain stays.
   - Ratify script `scripts/operator/ratify_afc_directive_scope_20261115.sh`, pushed in cf53a7891; its dry run passes (removals only, 7 lines, full file back to pre-a81fc882e sha f319dece).
   - Open box under AGENTFILE-INJECT-DEPLOY step 2 (`engineering-hygiene-backlog.md:2642`). It awaits the operator's signature and is NOT ticked.
   - **Lesson:** an edit to `agents/shared/` lands in every Claude session's start-up context. A measurement on local models does not cover that audience, so the decision package must name the audience it measured and the one it did not.
4. **Ratify-script lessons.**
   - fish needs `env VAR=value cmd`; the bash `VAR=value cmd` form fails there.
   - On a busy main the push races; a rejection lands nothing, so just re-run.
   - A removal-only ratify needs an `--anchor` that still exists after the change, or the receipt protocol check fails.
   - Throwaway stage worktrees go through `git worktree remove`, never to the trash. Trashing them left dangling worktree entries that had to be restored and removed properly.
5. **Pipeline.** The agent-file package (AGENTFILE-INJECT-DEPLOY) and TOOLPERM-DENY-DEFAULT still wait on the production relaunch and the contention-matrix refresh (relaunch queue item 1). Nothing is running for workspace-f2. No ended-but-unfiled rows: the three `inf85-w3-*-20261110` rc=1 receipts were superseded by the filed `-r3-20261111` rows.

| Repo | Files |
|---|---|
| epyc-root | this file, `wiki/` pages from the scoped compile |
