# Research & Evaluation — Active Backlog

**Purpose**: dispatch. Benchmarks, scorers, audits, research programs and their findings.

**Row contract** — one row per handoff, exactly one index owns each handoff. `Next action` is a single imperative line (≤140 chars) seeded from the handoff's own first open task; **status, evidence and history do not belong in rows** — status is generated into [`master-handoff-index.md`](master-handoff-index.md) and detail lives in `handoffs/active/.index-state.json`. Contract: [`handoff-index-authoring.md`](../../docs/guides/agent-workflows/handoff-index-authoring.md).

**History**: superseded narration for this index lives in [`../archived/research-evaluation-index-history-through-2026-08-10.md`](../archived/research-evaluation-index-history-through-2026-08-10.md).

**IDs are stable.** `EVL-NN` is a durable handle — cite it instead of a line number, and never reuse a retired one.

| ID | Track | Handoff | Next action | Deps |
|----|-------|---------|-------------|------|
| EVL-01 | agent file prose compression | [agent-file-prose-compression.md](agent-file-prose-compression.md) | AFC-P5.E3 — run the n=30 compliance campaign. READY but HELD (operator: "I will tell | — |
| EVL-02 | model evaluation queue | [model-evaluation-queue.md](model-evaluation-queue.md) | Rank the queue by lane fit; next: AMSB-C390-1 Coder390 vs 27B same-harness A/B, then the EffiBench-X adoption decision | — |
| EVL-03 | autopilot decision plane audit 2026 07 22 | [autopilot-decision-plane-audit-2026-07-22.md](autopilot-decision-plane-audit-2026-07-22.md) | EV-CONF-2 — build an answer-span/salient-token confidence source, then re-baseline math AUROC before any math-domain use | — |
| EVL-04 | autopilot sequential allocation | [autopilot-sequential-allocation.md](autopilot-sequential-allocation.md) | After RTG-02 prospective capture, run both sealed Shinka variants without derived menus or counterfactual outcomes | RTG-02 |
| EVL-08 | canonical judge suite revamp | [benchmark-suites.md](benchmark-suites.md) | Coordinate CJ-13 live agreement/cost acceptance with its MI210 owner; retain CJ-16's separate cascade evaluation | — |
| EVL-10 | episodic memory integrity | [episodic-memory-integrity.md](episodic-memory-integrity.md) | Run M-12i model-free diagnostic replay after full-CPU bench release under an exclusive claim; keep M-12f metric construction separate | — |
| EVL-14 | eval tower verification | [eval-tower-program.md](eval-tower-program.md) | Retain EV-PROTO and live calibration acceptance | — |
| EVL-15 | evidence plane instrument repair | [evidence-plane-instrument-repair.md](evidence-plane-instrument-repair.md) | W5 — Promote core_v2 once the operator rules on the E4/core autopilot_quality era row; then collect alarm-free W6 audit evidence | — |
| EVL-16 | evidence plane ledger and sequential verdict | [evidence-plane-ledger-and-sequential-verdicts.md](evidence-plane-ledger-and-sequential-verdicts.md) | W8b — Continue live W8 candidate attempts; confirm a keepable replayable candidate, then collect sequential and promotion-eval evidence | — |
| EVL-20 | fable5 window2 findings 02 heterogeneous gpu | [fable5-window2-findings-02-heterogeneous-gpu.md](fable5-window2-findings-02-heterogeneous-gpu.md) | F1 — per-split GPU/CPU timing under static -cmoe on one MoE model; report | — |
| EVL-21 | fable5 window2 findings 03 portfolio and mas | [fable5-window2-findings-03-portfolio-and-master-queue.md](fable5-window2-findings-03-portfolio-and-master-queue.md) | G1 · Ratify P-GPU-1 (operator; measurement trust boundary — human-amendment-only). findings-02 §5 | — |
| EVL-24 | frontier f2 self running lab | [frontier-f2-self-running-lab.md](frontier-f2-self-running-lab.md) | W3 — Collect real shadow/reviewed lab verdicts and use scripts/lab/promote_job.py as the only job-promotion path | — |
| EVL-25 | frontier f3 data flywheel | [frontier-f3-data-flywheel.md](frontier-f3-data-flywheel.md) | W3 — run a GRPO pass that demonstrates learning: a movable reward, completion cap above natural length, pre-registered pass rule | — |
| EVL-27 | frontier f6 upstream publication | [frontier-f6-upstream-publication.md](frontier-f6-upstream-publication.md) | W1 — Build the D2 CPU sparse prompt-processing path per llama-cpp-dsa-contribution.md (D1 superseded by #23346); profile, then PR | — |
| EVL-29 | intake derived work 2026 07 25 | [intake-derived-work-2026-07-25.md](intake-derived-work-2026-07-25.md) | Re-open ID-3/AP-21 on corrected trial support; dispatch accepted retrospective proposals through their application owners | — |
| EVL-36 | repl session memory maturity | [repl-session-memory-maturity.md](repl-session-memory-maturity.md) | D-f1 live lease validation at its inference-owner boundary | — |
| EVL-37 | repl turn efficiency | [repl-turn-efficiency.md](repl-turn-efficiency.md) | Obtain S4-T1 live seeding proof at its inference-owner boundary; ingest the first granted real Omega capture via VB-S4-OMEGA-FIRST-AB | — |
| EVL-43 | sliders local validation | [sliders-local-validation.md](sliders-local-validation.md) | Operator decision: KB-RAG K7 precondition fired — evaluate SLIDERS DB+SQL alternative (Phase 0 falsification) now, or keep parked? | — |
| EVL-44 | stale open audit 2026 07 18 | [stale-open-audit-2026-07-18.md](stale-open-audit-2026-07-18.md) | Recast x-mas-text-routing to telemetry-watch; internal-kb-rag stays active (KB-WM-6, KB-GS-1..4 open since 09-17) | — |
| EVL-47 | vidya belief substrate program | [vidya-belief-substrate-program.md](vidya-belief-substrate-program.md) | VB-CANARY-GATE-1: re-run both loop canaries after Codex C1-C3 land; VB-CC-PILOT register; GNX-REINDEX-1 receipt | — |
| EVL-48 | fable5 window2 findings 05c mi210 lever cate | [fable5-window2-findings-05c-mi210-lever-category-matrix.md](fable5-window2-findings-05c-mi210-lever-category-matrix.md) | L2 — quantize_q8_1 requant kill (L14 done: 4b6434a9, DEAD) | — |
| EVL-49 | reboot gated inventory and staging | [reboot-gated-inventory-and-staging.md](reboot-gated-inventory-and-staging.md) | S-05 — capture current pool/placement and actual owner window; retain accepted saved-E1 source capture | INF-06, INF-07, RTG-46 |
| EVL-52 | dev harness trace mining | [dev-harness-trace-mining.md](dev-harness-trace-mining.md) | DHM-4 operator labels (30-item pilot, private); DHM-5.2 paired turn-1 probe (Codex subagent, opencode); DHM-8 hook proposal | RTG-41 |

## Cross-domain

Edges to other domains go in the `Deps` column as bare IDs (e.g. `RTG-12`). Do **not** add a second row for a handoff another index owns.

## Reporting

After changing any row: run `python3 scripts/handoffs/index_state.py` to refresh generated state, then `--check` before committing.
