# Hermes & Agent UX — Active Backlog

**Purpose**: dispatch. Agent-facing surfaces: REPL/UX, prompting, memory, output compression.

**Row contract** — one row per handoff, exactly one index owns each handoff. `Next action` is a single imperative line (≤140 chars) seeded from the handoff's own first open task; **status, evidence and history do not belong in rows** — status is generated into [`master-handoff-index.md`](master-handoff-index.md) and detail lives in `handoffs/active/.index-state.json`. Contract: [`handoff-index-authoring.md`](../../docs/guides/agent-workflows/handoff-index-authoring.md).

**History**: superseded narration for this index lives in [`../archived/hermes-agent-index-history-through-2026-08-10.md`](../archived/hermes-agent-index-history-through-2026-08-10.md).

**IDs are stable.** `HRM-NN` is a durable handle — cite it instead of a line number, and never reuse a retired one.

| ID | Track | Handoff | Next action | Deps |
|----|-------|---------|-------------|------|
| HRM-01 | harness selection and integration | [harness-selection-and-integration.md](harness-selection-and-integration.md) | HS-4 — Harness-selection decision gate: Hermes vs OpenCode vs an ACP-speaker, gated on HS-1 + HS-2. Default outcome preserved: (A) stays or… | — |
| HRM-02 | hermes outer shell | [hermes-outer-shell.md](hermes-outer-shell.md) | Multi-turn context (references prior answer) | — |
| HRM-03 | memento block reasoning compression | [memento-block-reasoning-compression.md](memento-block-reasoning-compression.md) | S2 Stage-1 format-learning smoke on Qwen3-0.6B (fill compliance/compression/MATH-500 table) | — |
| HRM-04 | minddr deep research mode | [minddr-deep-research-mode.md](minddr-deep-research-mode.md) | Phase-2: run a gfx90a (MI210) training-viability smoke now that the hardware gate flipped (was DGX-blocked) — BLOCKED 2026-07-29: GPU is id… | — |
| HRM-05 | reasoning compression | [reasoning-compression.md](reasoning-compression.md) | If validated: implement enforce mode (route easy→worker, hard→architect) | — |
| HRM-06 | security review skill | [security-review-skill.md](security-review-skill.md) | GATE-0 production-reachability, ordered BEFORE exploitability. CodeCrucible short-circuits on whether the code path is reachable in product… | — |
| HRM-07 | tool output compression | [tool-output-compression.md](tool-output-compression.md) | P4e — Decision gate: roll-out scope (no time estimate; data-driven). After 1 week of P4c data, decide per-command: (i) promote to default (… | — |

## Cross-domain

Edges to other domains go in the `Deps` column as bare IDs (e.g. `RTG-12`). Do **not** add a second row for a handoff another index owns.

## Reporting

After changing any row: run `python3 scripts/handoffs/index_state.py` to refresh generated state, then `--check` before committing.
