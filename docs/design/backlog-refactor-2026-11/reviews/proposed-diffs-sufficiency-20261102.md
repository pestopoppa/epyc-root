# PROPOSED diffs — measurement sufficiency (reconciled against origin/main 4ffa29969, 2026-11-02)

Commit `4ffa29969` "Make measurement-sufficiency principle project-wide guidance" (another ws58 agent) landed before these proposals were applied. Status per item:

| item (v7 §A.2c proposal) | status on main | evidence |
|---|---|---|
| `docs/guides/agent-workflows/measurement-sufficiency.md` — futility-only paragraph citing OP-ABSEQ / OP-PQP / OP-ALPHAWIN | **LANDED** | `## Formal-gate cells: futility-only interim looks` (`:25-:27`), names all three OP decisions |
| `docs/guides/agent-workflows/handoff-index-authoring.md` — sufficiency/stop-rule field in the box contract | **LANDED** | `## Measurement tasks carry a stop rule` (`:47-:49`): `Stop rule:` field — question, expected effect vs sample-size error, checkpoints… |
| `.claude/skills/research-intake/SKILL.md` — every measurement task drafted with a sufficiency block | **LANDED** | Stage-3 item 6 (`:576-:578`), formal-gate cells futility-only |
| `.claude/skills/inference-backlog-scheduling/SKILL.md` — no stop rule ⇒ not READY | **LANDED** (not in my v7 list; covers the publish-gate intent) | 4ffa29969 stat |
| wiki (`wiki/benchmark-methodology.md`) and case-study copy (`rtg58-case-study-20261102.md`) | **LANDED** | 4ffa29969 stat |
| Research-intake Stage 4: run `python3 scripts/handoffs/task_lint_v2.py migrate <edited handoffs>`; a new inference box failing field `s` blocks application | **STILL MISSING** — proposal kept (below) | `grep -n task_lint .claude/skills/research-intake/SKILL.md` → none on main |
| `task_lint_v2.py` field `s` (inference box must state its stop rule; `migrate` hard, `publish` refuses) + tests | **STILL MISSING** on main (code lives in the audit dir; lands with migration commit 0) | `/mnt/raid0/llm/tmp/ws58-csh/task_lint_v2.py`, `test_task_lint_v2.py` 21/21 |

## Remaining proposed diff — `.claude/skills/research-intake/SKILL.md` (Stage 4)

```diff
@@ (Stage 4 — apply the approved plan; after the index_state.py --check step) @@
+- Run `python3 scripts/handoffs/task_lint_v2.py migrate <every handoff edited by the plan>`. A newly authored inference box that fails field `s` (no `Stop rule:` / sufficiency block, per `docs/guides/agent-workflows/measurement-sufficiency.md` and the authoring guide's "Measurement tasks carry a stop rule") blocks the plan's application; NEEDS-OWNER / NEEDS-OPERATOR / NEEDS-DECOMPOSITION tags are allowed only on pre-existing boxes being migrated, never on a box the intake drafts.
```

The row-template wording in the authoring guide already uses `Stop rule:`; `task_lint_v2.SUFF` accepts `stop rule`, so the lint and the landed template agree without further change.
