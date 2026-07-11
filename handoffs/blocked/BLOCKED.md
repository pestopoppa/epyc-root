# Blocked Tasks

**Last Updated**: 2026-07-11

This index tracks work that cannot proceed until an external condition changes. It includes files physically in `handoffs/blocked/` and active handoffs whose status is explicitly `BLOCKED`.

## Current Blocked Work

| Task | Blocked On | Priority | Handoff | Current State |
|------|------------|----------|---------|---------------|
| Swarm-as-Dataset-Generator — Narrow-Domain SFT Distillation | [`../active/strand-rust-coder-rustevo2-verification.md`](../active/strand-rust-coder-rustevo2-verification.md) Phase B Pass@1 result and GO/NO-GO disposition | HIGH-conditional | [`swarm-dataset-distillation.md`](swarm-dataset-distillation.md) | Stub only. Do not start P1-P5 until the operator-approved RustEvo2 bench produces a decision. Active-path compatibility pointer remains at [`../active/swarm-dataset-distillation.md`](../active/swarm-dataset-distillation.md). |

Removed 2026-06-12 (Fable 5 portfolio pass): Ouroboros multi-model validation → moved to [`../archived/09-ouroboros-multi-model-validation.md`](../archived/09-ouroboros-multi-model-validation.md) — never executed, references a deprecated model stack (pre-30B-A3B/gemma4 worker swaps); closure note in the file.

Removed 2026-06-12 (BGE repair complete): Retrain routing models + GraphRouter + SkillBank → returned to active work in [`../active/retrain-routing-models.md`](../active/retrain-routing-models.md). Post-repair diagnose-only report was HEALTHY with 275,960 FAISS vectors and 94.6% coverage.

## Reporting Instructions

When a blocker clears:

1. Update this table.
2. Update the handoff's status line.
3. Move the handoff back to `active/` if it was physically blocked.
4. Update the owning domain index and `handoffs/active/master-handoff-index.md`.

When blocked work is superseded or completed, move it to `handoffs/completed/` or `handoffs/archived/` and remove it from this table.
