# User-Facing Harness — Active Backlog

**Purpose**: dispatch. Agent- and user-facing surfaces: REPL/UX, prompting, memory, output compression. Named for the *surface*, not for any one implementation — the shell is OpenCode (HS-4, 2026-09-16) and the agent-loop features live in the orchestrator.

**Row contract** — one row per handoff, exactly one index owns each handoff. `Next action` is a single imperative line (≤140 chars) seeded from the handoff's own first open task; **status, evidence and history do not belong in rows** — status is generated into [`master-handoff-index.md`](master-handoff-index.md) and detail lives in `handoffs/active/.index-state.json`. Contract: [`handoff-index-authoring.md`](../../docs/guides/agent-workflows/handoff-index-authoring.md).

**History**: superseded narration for this index lives in [`../archived/user-facing-harness-index-history-through-2026-08-10.md`](../archived/user-facing-harness-index-history-through-2026-08-10.md).

**IDs are stable.** `UFH-NN` is a durable handle — cite it instead of a line number, and never reuse a retired one.

**UFH-13, the thesis experiment, is PARKED (operator, 2026-09-28)** until an autopilot run trains escalation on the
swapped stack. The 2026-09-27 narrowing no longer ranks work. Boxes marked `❄ FROZEN 2026-09-27` stay frozen for their
inference-bearing steps only; their design and documentation work may proceed (`CURRENT-CAMPAIGN.md`, 2026-09-28).

| ID | Track | Handoff | Next action | Deps |
|----|-------|---------|-------------|------|
| UFH-13 | thesis experiment (ACTIVE 2026-10-29) | [thesis-experiment-orchestrator-vs-strongest-model.md](thesis-experiment-orchestrator-vs-strongest-model.md) | ARCHSWAP-3b A-3 frontdoor scout-stage claim sample; else PARKED until autopilot trains on the swapped stack, then TE-reopen | — |
| UFH-01 | harness selection and integration | [harness-program.md](harness-program.md) | Run UFH-TE-2 serving-identity dispatch guard, then HIL-RE-1 claim grammar; P6 EP probe in parallel | RTG-09 |

## Cross-domain

Edges to other domains go in the `Deps` column as bare IDs (e.g. `RTG-12`). Do **not** add a second row for a handoff another index owns.

## Reporting

After changing any row: run `python3 scripts/handoffs/index_state.py` to refresh generated state, then `--check` before committing.
