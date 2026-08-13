# mainB — Land A14 GateDecision-echo (merge-ready)

**You are mainB** (roster id `mainB`, lanes `[gpu, none]`). Bootstrap: run
`session_bus.py provision --agent mainB`, then `drain --agent mainB --triage`, then execute.

## Premise (from the coordinator handover, 2026-08-11)

A14 — GateDecision echo — was reported **done and merge-ready**, parked on branch
`a14-gatedecision-echo` @ `a7d7bdb6` in `epyc-orchestrator`, pending a merge window cleared with
`inference`. That state is days old; verify it rather than trust it.

## Task

1. Confirm the branch `a14-gatedecision-echo` and its commit `a7d7bdb6` still exist and are unmerged;
   confirm the work is complete (its suite green).
2. Gate the merge: `python3 scripts/coordination/merge_gate.py check --repo epyc-orchestrator`.
   A **gated** verdict means you produce a pre-validated command and hold — do not apply it.
3. The "merge window with inference" gate was about orchestrator reload coupling. The orchestrator
   stack is currently **mostly down** (only the dashboard is up), so reload coupling is likely moot —
   state your reasoning, do not assume. If a real window is needed, request it from `inference` via
   the bus (note: `kind=compute-request` is not yet in the schema — mainD is fixing that — so use
   `kind=status` + `payload.request_kind=compute-request` for now).

## Constraints

- lanes `[gpu, none]`: no GPU/compute without an inference-granted window.
- **Do NOT push.** Commit locally only — push freeze pending operator ruling.

## Note

Your `compute-request-schema-gap` finding (`msg-20260813T110107Z-25-mainB`) is actioned: mainD owns
the schema fix. You are not assigned it.
