# Research & Evaluation — Active Backlog

**Purpose**: dispatch. Benchmarks, scorers, audits, research programs and their findings.

**Row contract** — one row per handoff, exactly one index owns each handoff. `Next action` is a single imperative line (≤140 chars) seeded from the handoff's own first open task; **status, evidence and history do not belong in rows** — status is generated into [`master-handoff-index.md`](master-handoff-index.md) and detail lives in `handoffs/active/.index-state.json`. Contract: [`handoff-index-authoring.md`](../../docs/guides/agent-workflows/handoff-index-authoring.md).

**History**: superseded narration for this index lives in [`../archived/research-evaluation-index-history-through-2026-08-10.md`](../archived/research-evaluation-index-history-through-2026-08-10.md).

**IDs are stable.** `EVL-NN` is a durable handle — cite it instead of a line number, and never reuse a retired one.

| ID | Track | Handoff | Next action | Deps |
|----|-------|---------|-------------|------|
| EVL-02 | model evaluation queue | [model-evaluation-queue.md](model-evaluation-queue.md) | Rank the queue by lane fit; next: AMSB-C390-1 Coder390 vs 27B same-harness A/B, then the EffiBench-X adoption decision | — |
| EVL-04 | autopilot sequential allocation | [autopilot-sequential-allocation.md](autopilot-sequential-allocation.md) | After RTG-02 prospective capture, run both sealed Shinka variants without derived menus or counterfactual outcomes | RTG-02 |
| EVL-08 | canonical judge suite revamp | [benchmark-suites.md](benchmark-suites.md) | Coordinate CJ-13 live agreement/cost acceptance with its MI210 owner; retain CJ-16's separate cascade evaluation | — |
| EVL-10 | episodic memory integrity | [memory-program.md](memory-program.md) | Run M-12i model-free diagnostic replay after full-CPU bench release under an exclusive claim; keep M-12f metric construction separate | — |
| EVL-14 | eval tower verification | [eval-tower-program.md](eval-tower-program.md) | Retain EV-PROTO and live calibration acceptance | — |
| EVL-29 | intake derived work 2026 07 25 | [frontier-lab-automation.md](frontier-lab-automation.md) | Re-open ID-3/AP-21 on corrected trial support; dispatch accepted retrospective proposals through their application owners | — |
| EVL-37 | repl turn efficiency | [repl-turn-efficiency.md](repl-turn-efficiency.md) | Obtain S4-T1 live seeding proof at its inference-owner boundary; ingest the first granted real Omega capture via VB-S4-OMEGA-FIRST-AB | — |
| EVL-47 | vidya belief substrate program | [vidya-belief-substrate-program.md](vidya-belief-substrate-program.md) | VB-CANARY-GATE-1: re-run both loop canaries after Codex C1-C3 land; VB-CC-PILOT register; GNX-REINDEX-1 receipt | — |
| EVL-49 | reboot gated inventory and staging | [reboot-gated-inventory-and-staging.md](reboot-gated-inventory-and-staging.md) | S-05 — capture current pool/placement and actual owner window; retain accepted saved-E1 source capture | INF-06, INF-45, RTG-34 |
| EVL-52 | dev harness trace mining | [dev-harness-trace-mining.md](dev-harness-trace-mining.md) | DHM-4 operator labels (30-item pilot, private); DHM-5.2 paired turn-1 probe (Codex subagent, opencode); DHM-8 hook proposal | EVL-10 |

## Cross-domain

Edges to other domains go in the `Deps` column as bare IDs (e.g. `RTG-12`). Do **not** add a second row for a handoff another index owns.

## Reporting

After changing any row: run `python3 scripts/handoffs/index_state.py` to refresh generated state, then `--check` before committing.
