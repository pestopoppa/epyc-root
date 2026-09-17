# Research & Evaluation — Active Backlog

**Purpose**: dispatch. Benchmarks, scorers, audits, research programs and their findings.

**Row contract** — one row per handoff, exactly one index owns each handoff. `Next action` is a single imperative line (≤140 chars) seeded from the handoff's own first open task; **status, evidence and history do not belong in rows** — status is generated into [`master-handoff-index.md`](master-handoff-index.md) and detail lives in `handoffs/active/.index-state.json`. Contract: [`handoff-index-authoring.md`](../../docs/guides/agent-workflows/handoff-index-authoring.md).

**History**: superseded narration for this index lives in [`../archived/research-evaluation-index-history-through-2026-08-10.md`](../archived/research-evaluation-index-history-through-2026-08-10.md).

**IDs are stable.** `EVL-NN` is a durable handle — cite it instead of a line number, and never reuse a retired one.

| ID | Track | Handoff | Next action | Deps |
|----|-------|---------|-------------|------|
| EVL-01 | agent file prose compression | [agent-file-prose-compression.md](agent-file-prose-compression.md) | AFC-P5.E3 — run the n=30 compliance campaign. READY but HELD (operator: "I will tell | — |
| EVL-02 | architect model selection bench | [architect-model-selection-bench.md](architect-model-selection-bench.md) | Decide :596 EffiBench-X adoption once the 2607.01211 ingest lands; gpqa_diamond_cot arm per ROI rule | — |
| EVL-03 | autopilot decision plane audit 2026 07 22 | [autopilot-decision-plane-audit-2026-07-22.md](autopilot-decision-plane-audit-2026-07-22.md) | EV-CONF-2 — build an answer-span/salient-token confidence source, then re-baseline math AUROC before any math-domain use | — |
| EVL-04 | autopilot sequential allocation | [autopilot-sequential-allocation.md](autopilot-sequential-allocation.md) | SEQ-B2 done (4c220b11); next open item is the rate-axis era fence — SEQ-B1/SEQ-3 are operator decisions | — |
| EVL-05 | backlog roi audit 2026 07 14 | [backlog-roi-audit-2026-07-14.md](backlog-roi-audit-2026-07-14.md) | RE-1 — re-baseline math suites under math_verify (EV-11c) once EV-CONF real-confidence plumbing lands | — |
| EVL-07 | bulk inference campaign | [bulk-inference-campaign.md](bulk-inference-campaign.md) | K-LCM-1 — LongCoT-Mini calibration run (~500-easy deterministic long-horizon suite) | — |
| EVL-08 | canonical judge suite revamp | [canonical-judge-suite-revamp.md](canonical-judge-suite-revamp.md) | CJ-3d — wire a representative BFCL-V3 sample on the native function-call path (key bfcl_v3), then CJ-3e discrimination | — |
| EVL-09 | design backlog triage 2026 07 23 | [design-backlog-triage-2026-07-23.md](design-backlog-triage-2026-07-23.md) | REFERENCE SNAPSHOT, not a task list — cite it; dispatchable work lives in eval-tower-verification.md and autopilot-control-plane-integration | — |
| EVL-10 | episodic memory integrity | [episodic-memory-integrity.md](episodic-memory-integrity.md) | M-12a Tulving 200ch/100K three-arm run (compute-gated, OP-42); M-12e scorer prerequisite closed dcb769c1 | — |
| EVL-11 | eval benchmark cost reduction | [eval-benchmark-cost-reduction.md](eval-benchmark-cost-reduction.md) | BLOCKED: needs Harbor adapter + TB Core baseline (agent-world-env-synthesis) before MR/TB filter applies | — |
| EVL-12 | eval tower architecture audit 2026 07 20 | [eval-tower-architecture-audit-2026-07-20.md](eval-tower-architecture-audit-2026-07-20.md) | E1 ARCH-1 — finish splitting the eval_tower god-module: extract the concurrency ladder, one import bootstrap, rubric-parsing sidecar | — |
| EVL-13 | eval tower loop robustness audit 2026 07 20 | [eval-tower-loop-robustness-audit-2026-07-20.md](eval-tower-loop-robustness-audit-2026-07-20.md) | ETR-4 — Guard the unguarded r.rubric_threshold_source read in _compact_question_result with getattr (eval_tower.py:1413) | — |
| EVL-14 | eval tower verification | [eval-tower-verification.md](eval-tower-verification.md) | EV-6b fail-closed role→model cross-family check (zero compute); EV-14a re-run held for realized roles, then EV-4 | EVL-13 |
| EVL-15 | evidence plane instrument repair | [evidence-plane-instrument-repair.md](evidence-plane-instrument-repair.md) | W5 — Promote core_v2 once the operator rules on the E4/core autopilot_quality era row; then collect alarm-free W6 audit evidence | — |
| EVL-16 | evidence plane ledger and sequential verdict | [evidence-plane-ledger-and-sequential-verdicts.md](evidence-plane-ledger-and-sequential-verdicts.md) | W8b — Continue live W8 candidate attempts; confirm a keepable replayable candidate, then collect sequential and promotion-eval evidence | — |
| EVL-19 | fable5 window2 findings 01 optimizer integri | [fable5-window2-findings-01-optimizer-integrity.md](fable5-window2-findings-01-optimizer-integrity.md) | R2-current — Accrue a current-era trusted per-question ledger for a reproducible ≥40-item core selection; do not reuse the July-3 set | — |
| EVL-20 | fable5 window2 findings 02 heterogeneous gpu | [fable5-window2-findings-02-heterogeneous-gpu.md](fable5-window2-findings-02-heterogeneous-gpu.md) | F1 — per-split GPU/CPU timing under static -cmoe on one MoE model; report | — |
| EVL-21 | fable5 window2 findings 03 portfolio and mas | [fable5-window2-findings-03-portfolio-and-master-queue.md](fable5-window2-findings-03-portfolio-and-master-queue.md) | G1 · Ratify P-GPU-1 (operator; measurement trust boundary — human-amendment-only). findings-02 §5 | — |
| EVL-24 | frontier f2 self running lab | [frontier-f2-self-running-lab.md](frontier-f2-self-running-lab.md) | W3 — Collect real shadow/reviewed lab verdicts and use scripts/lab/promote_job.py as the only job-promotion path | — |
| EVL-25 | frontier f3 data flywheel | [frontier-f3-data-flywheel.md](frontier-f3-data-flywheel.md) | W3 — run a GRPO pass that demonstrates learning: a movable reward, completion cap above natural length, pre-registered pass rule | — |
| EVL-26 | frontier f4 continuity backup | [frontier-f4-continuity-backup.md](frontier-f4-continuity-backup.md) | restic backend landed 2026-08-23; real run blocked on operator-named off-array target | — |
| EVL-27 | frontier f6 upstream publication | [frontier-f6-upstream-publication.md](frontier-f6-upstream-publication.md) | W1 — Build the D2 CPU sparse prompt-processing path per llama-cpp-dsa-contribution.md (D1 superseded by #23346); profile, then PR | — |
| EVL-29 | intake derived work 2026 07 25 | [intake-derived-work-2026-07-25.md](intake-derived-work-2026-07-25.md) | ID-2 DONE 2026-08-23 (gepa==0.0.26 declared direct, f8bc4d2b); VERSION choice stays gated behind AP-19b | — |
| EVL-30 | integration test coverage | [integration-test-coverage.md](integration-test-coverage.md) | Keep as the integration-test standing-constraint holder; no dispatchable task by design | — |
| EVL-31 | mathsmith hc formalizer eval | [mathsmith-hc-formalizer-eval.md](mathsmith-hc-formalizer-eval.md) | If no GGUF exists, convert from HF weights (convert_hf_to_gguf.py + llama-quantize, Q4_K_M and Q8_0) | — |
| EVL-32 | minimax h3 video generation eval | [minimax-h3-video-generation-evaluation.md](minimax-h3-video-generation-evaluation.md) | OPERATOR scope decision: is video gen a product need? If yes, download Ref2VA + 10Eros beta4 INT8 (~165 GB) | — |
| EVL-33 | per request reasoning budget | [per-request-reasoning-budget.md](per-request-reasoning-budget.md) | PRB-T4-RERUN — GPU re-run of TALE-EP on the refreshed pool (4 suites, n=400); then Step 3 budget=0 think-scaffold fix | — |
| EVL-34 | rao redel substrate spike | [rao-redel-substrate-spike.md](rao-redel-substrate-spike.md) | Run a naturally-delegating workload A/B (HotpotQA/DeepDive or small base model) before Step 3 escalation | — |
| EVL-35 | re4 protocol redesign | [re4-protocol-redesign.md](re4-protocol-redesign.md) | RE-4.2 — Run the non-saturation probe in an operator quiet window: frontdoor-only, two-phase, R=4096, 30 rows; gate accuracy in (10%,90%) | — |
| EVL-36 | repl session memory maturity | [repl-session-memory-maturity.md](repl-session-memory-maturity.md) | D-f1 — verify the D-f session lease under the live 6-worker API (concurrent /chat on one session serializes, no lost checkpoint) | — |
| EVL-37 | repl turn efficiency | [repl-turn-efficiency.md](repl-turn-efficiency.md) | Repair the RTE-Prefix harness, then measure isolated legacy vs stable cache reuse before any default flip | — |
| EVL-38 | repo readiness scorer | [repo-readiness-scorer.md](repo-readiness-scorer.md) | DONE 2026-08-25 — root L5.self_optimizing_loop closed (vidya-loop detector; queue 13→6, remainder frozen llama L5) | — |
| EVL-39 | rlm contested claims self evaluation | [rlm-contested-claims-self-evaluation.md](rlm-contested-claims-self-evaluation.md) | E1 — measure Base vs Depth-1 on synthetic NIAH with the E1a strict+lenient scorer; report latency and tokens separately | — |
| EVL-41 | scorer fork drift audit 2026 07 22 | [scorer-fork-drift-audit-2026-07-22.md](scorer-fork-drift-audit-2026-07-22.md) | DONE 2026-08-23 — shared measurement_guards module (verified 2 defs); research debug_scorer now a B7 delegation shim (d876adfe) | — |
| EVL-42 | scoring infra standardization | [scoring-infra-standardization.md](scoring-infra-standardization.md) | 1c-fix (b)+(d) done 2026-09-17; 1d — pin a runnable test env for the research repo's eval-scorer tests | — |
| EVL-43 | sliders local validation | [sliders-local-validation.md](sliders-local-validation.md) | Operator decision: KB-RAG K7 precondition fired — evaluate SLIDERS DB+SQL alternative (Phase 0 falsification) now, or keep parked? | — |
| EVL-44 | stale open audit 2026 07 18 | [stale-open-audit-2026-07-18.md](stale-open-audit-2026-07-18.md) | Close or relocate internal-kb-rag to completed and x-mas-text-routing to telemetry-watch | — |
| EVL-45 | strand rust coder rustevo2 verification | [strand-rust-coder-rustevo2-verification.md](strand-rust-coder-rustevo2-verification.md) | Phase B single-instance RustEvo2 bench (USER APPROVAL REQUIRED) - Strand, Qwen2.5-Coder-14B base, gemma4 worker, sequential | — |
| EVL-46 | tool use eval contract | [tool-use-eval-contract.md](tool-use-eval-contract.md) | TU-GR-1 — add the grader-isolation clause (graders unreachable from the agent sandbox + transcript tripwire) | — |
| EVL-47 | vidya belief substrate program | [vidya-belief-substrate-program.md](vidya-belief-substrate-program.md) | Continue SC65/SC66 and SC76; live AutoKernel source-KEEP codegen tuple/reader is wired | EVL-50 |
| EVL-48 | fable5 window2 findings 05c mi210 lever cate | [fable5-window2-findings-05c-mi210-lever-category-matrix.md](fable5-window2-findings-05c-mi210-lever-category-matrix.md) | L2 — quantize_q8_1 requant kill (L14 done: 4b6434a9, DEAD) | — |
| EVL-49 | reboot gated inventory and staging | [reboot-gated-inventory-and-staging.md](reboot-gated-inventory-and-staging.md) | S-01 — re-pin the 25 uptime-capped inference-batch entries to the v9 era and the live topology hash | INF-06, INF-07, RTG-46 |
| EVL-50 | conversational memory eval instruments | [conversational-memory-eval-instrument.md](conversational-memory-eval-instrument.md) | CME-3 — carry the BEAM harness-defect note on every BEAM number quoted outside the SC68 tuple | EVL-10 |

## Cross-domain

Edges to other domains go in the `Deps` column as bare IDs (e.g. `RTG-12`). Do **not** add a second row for a handoff another index owns.

## Reporting

After changing any row: run `python3 scripts/handoffs/index_state.py` to refresh generated state, then `--check` before committing.
