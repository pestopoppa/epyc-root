# Stack-change checklist (reusable)

Reusable per-change checklist for any model-stack change. It was retired from the handoff
`model-stack-change-standardization-audit.md` (row RTG-18, retired under backlog-refactor D4 on 2026-11-02).
The audit and its work packages are kept in
[`handoffs/completed/model-stack-change-standardization-audit.md`](../../../handoffs/completed/model-stack-change-standardization-audit.md).
This is a checklist, not a backlog: the steps are plain list items (deliberately not task boxes, so the backlog sweep and task lint never see them) and are copied as boxes into each change's own ticket. The
end-to-end procedure is the `stack-change` skill (`.claude/skills/stack-change/SKILL.md`).

Use this sequence for future stack changes. Steps marked "no inference" should be runnable by CI.

> **⚠ THESE BOXES ARE UNCHECKED BY DESIGN — DO NOT DISPATCH OR FLIP THEM.**
> This is a **reusable per-change runbook**, not a task list. Every `- [ ]` below is a step to be
> executed *during a stack change*, so it has no completion state outside one. Flipping any of them
> asserts that a per-change procedure is permanently done, and the next stack change would inherit a
> runbook that reads as already-executed — the checklist would silently stop being run.
>
> Noted 2026-07-29 by `auditor` because the automated backlog sweep classified two of these steps as
> dispatchable `none`-lane work: **TOP-40 row #12 (`:229`) and the runner-up bench row (`:230`)** in
> `coordination/session-bus/tasks/BACKLOG-DISPATCH-QUEUE.md`. The sweep's own column even labels the
> section `update-checklist`, so the evidence was already in the row. Any future sweep must treat a
> section framed *"use this sequence for future …"* as a template, not a backlog. Verified against
> the whole of `handoffs/active/`: this is the only section in the tree with dispatched template
> rows (`multimodal-pipeline.md § Review cadence` is the one other true recurring checklist, and
> none of its boxes are in the queue).

- Identify the change type: role model swap, shared-server consolidation, role retirement, tier change, port/slot change, context change, acceleration/draft/MTP change, or benchmark-only candidate addition.
- Update structured inputs only:
  - `epyc-orchestrator/orchestration/model_registry.yaml` `server_mode.*` for live deployment topology.
  - `epyc-orchestrator/orchestration/model_descriptors.yaml` for physical model identity and measured/candidate evidence.
  - `epyc-inference-research/orchestration/model_registry.yaml` only for comprehensive benchmark/candidate history, with measurement-status semantics.
  - `scripts/server/stack_manifest.py` only where launcher metadata still lacks generated ownership.
- Compile descriptors, preserving gaps instead of inventing values.
- Compile stack priors.
- Sync procedure role enums (`python3 scripts/registry/sync_procedure_role_enums.py --check`).
- Run loose guard, all-surface guard, and strict guard.
- Run focused unit tests for stack priors, guard, enum sync, q_scorer, admission, and any touched consumer.
- Run simulated model-swap tests:
  - shared mmap swap (`frontdoor`/`coder_escalation` style)
  - role retirement (`architect_coding` style)
  - HOT/WARM tier change (`architect_general` or `ingest_long_context` style)
- Update only generated operator summaries or explicitly historical docs.
- Before launch, require fresh generated priors and a guard pass or an explicit diagnostic override.
- After launch, compare running PIDs/ports/flags/binaries against stack priors and restart stale processes if needed.

**Last run (2026-07-14) recorded:**

- Descriptors compiled preserving gaps — `model_descriptors.yaml` reached `status: compiled` after `54b7c77`.
- Stack priors compiled — `stack_priors.yaml` reached `status: compiled` after `54b7c77`.
- Procedure role enums verified current via `scripts/registry/sync_procedure_role_enums.py --check` (`OK`).
- Loose, all-surface and strict guards run post-`03ed49f`: loose clean, strict clean, all-surfaces blocker waiver gone.

> *Restored 2026-08-11 by `mainC`.* These four results had been recorded by **flipping the template
> boxes to `[x]`**, which asserted that a per-change checklist was permanently complete — so the next
> model-stack change would have skipped compile, enum-sync and the three guards, reading them as
> already done. The evidence is preserved here verbatim; the steps above are unchecked because they
> must run **for every change**. Note this corruption predates the 2026-07-29 backlog sweep (these
> carry ✅ 2026-07-14 dates), so the sweep did not cause it — the sweep only made the class visible.
> Found by sweeping checked boxes inside DO-NOT-FLIP sections across `handoffs/active/`, not by
> following queue rows.
