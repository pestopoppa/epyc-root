# Orchestrator Lifecycle & Stabilization Closure

Extracted 2026-07-30 from `agents/shared/WORKFLOWS.md` (single-campaign RLM closure checklist
with orchestrator-internal field names; AFC-P6 restructure). Still-useful operational guidance
for orchestrator lifecycle work in `epyc-orchestrator`:

1. Prefer API-only reload: `python3 scripts/server/orchestrator_stack.py reload orchestrator` —
   subject to reload ownership (`agents/shared/OPERATING_CONSTRAINTS.md` → Inference and
   Benchmarks).
2. In restricted environments, socket-based health/probe commands may require escalated
   execution; treat sandbox `PermissionError` on local sockets as an environment constraint,
   not an orchestration regression.
3. Validate fixes with both unit coverage and contention probes; lock/delegation changes are
   not complete until seeded contention runs confirm no stale lock holders.
4. Treat response diagnostics as first-class acceptance criteria:
   `delegation_diagnostics.break_reason`, `budget_diagnostics.*`, and `error_code` must be
   explicit on bounded failures.
5. Keep roadmap status synchronized with evidence.
