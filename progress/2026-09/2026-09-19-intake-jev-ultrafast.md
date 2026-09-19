# 2026-09-19 — Research intake: browser-use/jev-ultrafast (intake-1493, intake-1494)

- Stages 1–4 complete; plan approved 2026-09-19. Lane worktree `intake-jev-ultrafast-20260918`.
- intake-1493 is dive-verified:
  - The repo passes its 31 offline tests.
  - The tweet's $0.0039 is derivable: 90,558 input tokens × $42 per billion, plus the text helper.
  - The 25% speedup splits roughly in half: fewer model requests (fewer stale invalidations) and less browser time.
- Transferable pattern: operation × speculative conditional-target heads in one typed call. Filed as TD-12..TD-15 in
  `handoffs/active/typed-decision-plane.md`. The tasks are unticked and the owner session is unchanged.
- Per operator steering, a new dormant stub `handoffs/active/browser-agent-surface.md` (UFH-10) keeps a future
  interactive browser surface from being lost.
- Validators: `validate_intake.sh` exit 0; `index_state.py --check` exit 0.

## Wrap-up (operator-invoked)

- Scratch clone `/workspace/tmp/intake-jev-ultrafast/` deleted. Before deleting, I confirmed the backup session file was byte-identical to git.
- Index pruning: 0 candidates from the generated prune screen, and nothing archived.
- Wiki compile sweep: the 9 changed sources were compiled into 7 pages, and the watermark was advanced (total_new 0).
  - Pages: routing-intelligence, tool-implementation, agent-architecture, benchmark-methodology, memory-augmented, knowledge-management, hardware-optimization.
  - Also fixed a line that was already on main in knowledge-management.md. Its bare `intake-882/883` citation cited overturned intake-883; it now uses `#record` form. That makes `index_state.py --check` exit 0.
- README freshness: pass. Lint: 0 errors.
- No lane: the session ran in a dedicated intake worktree (branch tracks origin/main), with pathspec commits.
