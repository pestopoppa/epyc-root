# User-Facing Harness — Active Backlog

**Purpose**: dispatch. Agent- and user-facing surfaces: REPL/UX, prompting, memory, output compression. Named for the *surface*, not for any one implementation — Hermes is the current candidate, not a commitment.

**Row contract** — one row per handoff, exactly one index owns each handoff. `Next action` is a single imperative line (≤140 chars) seeded from the handoff's own first open task; **status, evidence and history do not belong in rows** — status is generated into [`master-handoff-index.md`](master-handoff-index.md) and detail lives in `handoffs/active/.index-state.json`. Contract: [`handoff-index-authoring.md`](../../docs/guides/agent-workflows/handoff-index-authoring.md).

**History**: superseded narration for this index lives in [`../archived/user-facing-harness-index-history-through-2026-08-10.md`](../archived/user-facing-harness-index-history-through-2026-08-10.md).

**IDs are stable.** `UFH-NN` is a durable handle — cite it instead of a line number, and never reuse a retired one.

| ID | Track | Handoff | Next action | Deps |
|----|-------|---------|-------------|------|
| UFH-01 | harness selection and integration | [harness-selection-and-integration.md](harness-selection-and-integration.md) | HS-4 P0.4 — live OpenCode acceptance after API reload + GPU hold ends; meanwhile P0-MCP-a/b (venv python, session_id) | — |
| UFH-03 | memento block reasoning compression | [memento-block-reasoning-compression.md](memento-block-reasoning-compression.md) | S2 Stage-1 format-learning smoke on Qwen3-0.6B (fill compliance/compression/MATH-500 table) | — |
| UFH-04 | minddr deep research mode | [minddr-deep-research-mode.md](minddr-deep-research-mode.md) | Phase-2 — Provision a pinned gfx90a training env, then run the MI210 training-viability smoke; the run waits on E5 Stage-B host release | — |
| UFH-05 | reasoning compression | [reasoning-compression.md](reasoning-compression.md) | If validated: implement enforce mode (route easy→worker, hard→architect) | — |
| UFH-07 | tool output compression | [tool-output-compression.md](tool-output-compression.md) | P4e — once P4c telemetry has enough calls, decide per command whether run_bash_compressed is promoted, kept optional, or dropped | — |
| UFH-08 | harness improvement loop | [harness-improvement-loop.md](harness-improvement-loop.md) | HIL-1 — once HS-4 Phase 0 is integrated, list which feature-map homes are loop-friendly (mutable as files, deterministic to eval) | UFH-01 |
| UFH-09 | fuzzy workflow authoring gui | [fuzzy-workflow-authoring-gui.md](fuzzy-workflow-authoring-gui.md) | FW-1 — sketch the two-layer workflow example and record what the GUI must expose | UFH-01, RTG-56 |

## Cross-domain

Edges to other domains go in the `Deps` column as bare IDs (e.g. `RTG-12`). Do **not** add a second row for a handoff another index owns.

## Reporting

After changing any row: run `python3 scripts/handoffs/index_state.py` to refresh generated state, then `--check` before committing.
