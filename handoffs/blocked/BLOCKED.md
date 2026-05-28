# Blocked Tasks

**Last Updated**: 2026-05-27

This index tracks work that cannot proceed until an external condition changes. It includes files physically in `handoffs/blocked/` and active handoffs whose status is explicitly `BLOCKED`.

## Current Blocked Work

| Task | Blocked On | Priority | Handoff | Current State |
|------|------------|----------|---------|---------------|
| Retrain routing models + GraphRouter + SkillBank | Accumulate ~500+ fresh routing memories after episodic-memory reset | HIGH | [`../active/retrain-routing-models.md`](../active/retrain-routing-models.md) | Active handoff marked `BLOCKED`; verify memory count before retraining. |
| Ouroboros multi-model validation | Multiple validated worker models; old Nanbeige/MiroThinker dependencies need review against current model stack | MEDIUM | [`09-ouroboros-multi-model-validation.md`](09-ouroboros-multi-model-validation.md) | Historical blocked handoff still has open acceptance criteria; should be re-triaged before implementation. |

## Reporting Instructions

When a blocker clears:

1. Update this table.
2. Update the handoff's status line.
3. Move the handoff back to `active/` if it was physically blocked.
4. Update the owning domain index and `handoffs/active/master-handoff-index.md`.

When blocked work is superseded or completed, move it to `handoffs/completed/` or `handoffs/archived/` and remove it from this table.
