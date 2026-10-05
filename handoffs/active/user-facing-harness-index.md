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
| UFH-13 | thesis experiment (PARKED) | [thesis-experiment-orchestrator-vs-strongest-model.md](thesis-experiment-orchestrator-vs-strongest-model.md) | ARCHSWAP-3b A-3 frontdoor scout-stage claim sample; else PARKED until autopilot trains on the swapped stack, then TE-reopen | — |
| UFH-14 | agentic serving harness fixes | [agentic-serving-harness-fixes.md](agentic-serving-harness-fixes.md) | UFH14-DEPLOY-EC-2 live proofs; A6a sandbox leak (053c3bd82) + planted read; A3a one-warm re-run; A4a post-compaction re-prefill | INF-77, UFH-01 |
| UFH-01 | harness selection and integration | [harness-selection-and-integration.md](harness-selection-and-integration.md) | HS-4 P0.4b/c — republish the Harness Card (HS-7) and freeze OpenCode at tag v1.18.31=014614d3; then P0-split | RTG-09 |
| UFH-03 | memento block reasoning compression | [memento-block-reasoning-compression.md](memento-block-reasoning-compression.md) | S2 Stage-1 format-learning smoke on Qwen3-0.6B (fill compliance/compression/MATH-500 table) | — |
| UFH-04 | minddr deep research mode | [minddr-deep-research-mode.md](minddr-deep-research-mode.md) | Phase-2 — Provision a pinned gfx90a training env, then run the MI210 training-viability smoke; the run waits on E5 Stage-B host release | — |
| UFH-05 | reasoning compression | [reasoning-compression.md](reasoning-compression.md) | If validated: implement enforce mode (route easy→worker, hard→architect) | — |
| UFH-07 | tool output compression | [tool-output-compression.md](tool-output-compression.md) | Trajectory-artifact prerequisite (one grep-able log per task + live peek/grep audit), then TOC-SP-3 quote receipt | — |
| UFH-08 | harness improvement loop | [harness-improvement-loop.md](harness-improvement-loop.md) | HIL-1 — list the loop-friendly feature-map homes from hs4-shell doc §3, separating the mutable arm from policy documents | UFH-01 |
| UFH-09 | fuzzy workflow authoring gui | [fuzzy-workflow-authoring-gui.md](fuzzy-workflow-authoring-gui.md) | FW-1 — sketch the two-layer workflow example as a pseudocode loop block, and record what the GUI must expose | — |
| UFH-10 | browser agent surface | [browser-agent-surface.md](browser-agent-surface.md) | Dormant — revisit when a workflow needs interactive browsing; mechanism advances via RTG-56 TD-12..15 | RTG-56, RTG-33 |
| UFH-11 | AMD AI Lab website publication | [amd-ai-lab-website-publication.md](amd-ai-lab-website-publication.md) | WEB-1 — obtain the contact destination and reviewed-page launch choice for GitHub Pages | — |
| UFH-12 | repl embedding retrieval | [repl-embedding-retrieval.md](repl-embedding-retrieval.md) | REPL-EMB-2.2 offline recall eval (wire VB-UFH12-RETR first) | UFH-07, INF-78, EVL-37, UFH-01 |

## Cross-domain

Edges to other domains go in the `Deps` column as bare IDs (e.g. `RTG-12`). Do **not** add a second row for a handoff another index owns.

## Reporting

After changing any row: run `python3 scripts/handoffs/index_state.py` to refresh generated state, then `--check` before committing.
