# Handoff Index Authoring

Extracted 2026-07-30 from CLAUDE.md (authoring-time-only content; AFC-P6 restructure).

When creating an index that coordinates multiple handoffs, it must be an **actionable
coordination point** — not a passive navigation document. Required sections:

1. **Prioritized task list with checkboxes** — extract all outstanding tasks from linked
   handoffs, ordered by priority and dependency
2. **Dependency graph** — which tasks block which
3. **Cross-cutting concerns** — how changes in one subsystem affect others
4. **Reporting instructions** — what to update after task completion
5. **Key file locations** — implementation targets

An agent pointed at an index should be able to autonomously discover, prioritize, and execute
outstanding work across all linked subsystems.

Checkbox discipline and the dashboard axiom: `agents/shared/SESSION_LIFECYCLE.md`. On handoff
completion, extract findings to docs, then move the file to `handoffs/completed/` and DELETE
its master-index row (terminal rows do not stay in the queue — `agents/shared/WORKFLOWS.md`).
