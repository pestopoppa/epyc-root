# Research & Evaluation — Active Backlog

**Purpose**: dispatch. Benchmarks, scorers, audits, research programs and their findings.

**Row contract** — one row per handoff, exactly one index owns each handoff. `Next action` is a single imperative line (≤140 chars) seeded from the handoff's own first open task; **status, evidence and history do not belong in rows** — status is generated into [`master-handoff-index.md`](master-handoff-index.md) and detail lives in `handoffs/active/.index-state.json`. Contract: [`handoff-index-authoring.md`](../../docs/guides/agent-workflows/handoff-index-authoring.md).

**History**: superseded narration for this index lives in [`../archived/research-evaluation-index-history-through-2026-08-10.md`](../archived/research-evaluation-index-history-through-2026-08-10.md).

**IDs are stable.** `EVL-NN` is a durable handle — cite it instead of a line number, and never reuse a retired one.

| ID | Track | Handoff | Next action | Deps |
|----|-------|---------|-------------|------|
| EVL-01 | agent file prose compression | [agent-file-prose-compression.md](agent-file-prose-compression.md) | AFC-P5.E3 — run the n=30 compliance campaign. READY but HELD (operator: "I will tell | — |
| EVL-02 | architect model selection bench | [architect-model-selection-bench.md](architect-model-selection-bench.md) | Decide :596 EffiBench-X adoption once the 2607.01211 ingest lands; gpqa_diamond_cot arm per ROI rule | — |
| EVL-03 | autopilot decision plane audit 2026 07 22 | [autopilot-decision-plane-audit-2026-07-22.md](autopilot-decision-plane-audit-2026-07-22.md) | E8 RE-ARM (2026-07-26) — AutoPilot E8 baseline reseed = the gating task of the post-v8 | — |
| EVL-04 | autopilot sequential allocation | [autopilot-sequential-allocation.md](autopilot-sequential-allocation.md) | SEQ-A: make the refuted label sticky in state_name() so re-adjudication cannot silently un-refute | — |
| EVL-05 | backlog roi audit 2026 07 14 | [backlog-roi-audit-2026-07-14.md](backlog-roi-audit-2026-07-14.md) | RE-1 · Math-Verify scoring flip + re-baseline (S, med-ROI; intake-377/379) — the math_verify scorer is landed in orchestrator but zero pool… | — |
| EVL-06 | benchmark results dashboard | [benchmark-results-dashboard.md](benchmark-results-dashboard.md) | File artifact ingestion and the UI as tasks — the Status line says both remain open but all 7 boxes are closed | — |
| EVL-07 | bulk inference campaign | [bulk-inference-campaign.md](bulk-inference-campaign.md) | K-LCM-1 — LongCoT-Mini calibration run (~500-easy deterministic long-horizon suite) | — |
| EVL-08 | canonical judge suite revamp | [canonical-judge-suite-revamp.md](canonical-judge-suite-revamp.md) | CJ-1a — corpus is already cached (gpqa_diamond 198 rows); build the judge slate from it | — |
| EVL-09 | design backlog triage 2026 07 23 | [design-backlog-triage-2026-07-23.md](design-backlog-triage-2026-07-23.md) | OPERATOR: rule on each item in the 2026-07-23 design triage; the doc carries no boxes, so nothing can be dispatched | — |
| EVL-10 | episodic memory integrity | [episodic-memory-integrity.md](episodic-memory-integrity.md) | M-11a — first re-distil; INFERENCE-gated, do not run without an approved window | — |
| EVL-11 | eval benchmark cost reduction | [eval-benchmark-cost-reduction.md](eval-benchmark-cost-reduction.md) | BLOCKED: needs Harbor adapter + TB Core baseline (agent-world-env-synthesis) before MR/TB filter applies | — |
| EVL-12 | eval tower architecture audit 2026 07 20 | [eval-tower-architecture-audit-2026-07-20.md](eval-tower-architecture-audit-2026-07-20.md) | A2 agent SCORE-02/XREPO-1/PATH-1 — make module identity deterministic. (PARTIAL ✅ 2026-07-20: the debug_scorer leg landed in 2a41c0bc — see… | — |
| EVL-13 | eval tower loop robustness audit 2026 07 20 | [eval-tower-loop-robustness-audit-2026-07-20.md](eval-tower-loop-robustness-audit-2026-07-20.md) | H2.v9 — remeasure the contention matrix under frozen v9 after E8 quality collection — live dashboard topology and region-lock payloads alre… | — |
| EVL-14 | eval tower verification | [eval-tower-verification.md](eval-tower-verification.md) | EV-4 — decision-grade HE-R+ calibration baseline through the inference-batch loop, after contention recert | — |
| EVL-15 | evidence plane instrument repair | [evidence-plane-instrument-repair.md](evidence-plane-instrument-repair.md) | W5 — designed core_v2 (impl 2.1, 2–3 days + calibration): benchmarks/prompts/core_v2.jsonl (~40 items, per-item p∈0.2,0.8, stratified), ver… | — |
| EVL-16 | evidence plane ledger and sequential verdict | [evidence-plane-ledger-and-sequential-verdicts.md](evidence-plane-ledger-and-sequential-verdicts.md) | W8b — live candidate evidence after guard deploy: continue W8 candidate attempts under the live selectable-action coordinator plus outcome-… | — |
| EVL-17 | fable5 architecture review 2 | [fable5-architecture-review-2.md](fable5-architecture-review-2.md) | Run the preflight named under Run configuration, or retire the review if the Window-2 findings superseded it | — |
| EVL-18 | fable5 window2 findings 00 executive summary | [fable5-window2-findings-00-executive-summary.md](fable5-window2-findings-00-executive-summary.md) | Extract to docs and move to completed/ — findings record, no remaining work | — |
| EVL-19 | fable5 window2 findings 01 optimizer integri | [fable5-window2-findings-01-optimizer-integrity.md](fable5-window2-findings-01-optimizer-integrity.md) | R2-current — accrue a current-era, trusted per-question ledger sufficient for a reproducible ≥40-item core selection. Do not promote the Ju… | — |
| EVL-20 | fable5 window2 findings 02 heterogeneous gpu | [fable5-window2-findings-02-heterogeneous-gpu.md](fable5-window2-findings-02-heterogeneous-gpu.md) | F1 — per-split GPU/CPU timing under static -cmoe on one MoE model; report | — |
| EVL-21 | fable5 window2 findings 03 portfolio and mas | [fable5-window2-findings-03-portfolio-and-master-queue.md](fable5-window2-findings-03-portfolio-and-master-queue.md) | G1 · Ratify P-GPU-1 (operator; measurement trust boundary — human-amendment-only). findings-02 §5 | — |
| EVL-22 | fable5 window2 findings 05 intake sweep and  | [fable5-window2-findings-05-intake-sweep-and-roofline.md](fable5-window2-findings-05-intake-sweep-and-roofline.md) | Extract the intake-sweep + roofline findings to docs and move to completed/ — no remaining work | — |
| EVL-23 | frontier f1 real task corpus | [frontier-f1-real-task-corpus.md](frontier-f1-real-task-corpus.md) | File the W2+ real-task harvester work as tasks — Status reads IN PROGRESS but all 10 boxes are closed | — |
| EVL-24 | frontier f2 self running lab | [frontier-f2-self-running-lab.md](frontier-f2-self-running-lab.md) | W3 — reliability ladder (ongoing): scripts/lab/promote_job.py enforcing shadow → reviewed → autonomous from logged stats (shadow ≥10 runs s… | — |
| EVL-25 | frontier f3 data flywheel | [frontier-f3-data-flywheel.md](frontier-f3-data-flywheel.md) | W3 — GPU fine-tunes (MI210 present since 2026-07-02; the HW gate is CLEARED. The DATA gate is now satisfied by 100 trusted reviewed triage… | — |
| EVL-26 | frontier f4 continuity backup | [frontier-f4-continuity-backup.md](frontier-f4-continuity-backup.md) | W2 — the job (half day): scripts/backup/backup_critical.sh — restic preferred (dedupe+encryption, open-source) or snapshot-copy fallback. T… | — |
| EVL-27 | frontier f6 upstream publication | [frontier-f6-upstream-publication.md](frontier-f6-upstream-publication.md) | W1 — D2 PR spearhead (1–2 weeks; specced in llama-cpp-dsa-contribution.md): the prompt-processing sparse path the PR author asked for help… | — |
| EVL-28 | granite 97m r2 bench plan | [granite-97m-r2-bench-plan.md](granite-97m-r2-bench-plan.md) | File the outstanding HF model-artifact step as a task, or close Phase A and retire the bench plan | — |
| EVL-29 | intake derived work 2026 07 25 | [intake-derived-work-2026-07-25.md](intake-derived-work-2026-07-25.md) | ID-2 — pin the gepa dependency; installed is 0.0.26 and unpinned | — |
| EVL-30 | integration test coverage | [integration-test-coverage.md](integration-test-coverage.md) | Keep as the integration-test standing-constraint holder; no dispatchable task by design | — |
| EVL-31 | mathsmith hc formalizer eval | [mathsmith-hc-formalizer-eval.md](mathsmith-hc-formalizer-eval.md) | If no GGUF exists, convert from HF weights (convert_hf_to_gguf.py + llama-quantize, Q4_K_M and Q8_0) | — |
| EVL-32 | meta harness optimization | [meta-harness-optimization.md](meta-harness-optimization.md) | Retire this compatibility pointer once its 14 active citations are redirected to the owning harness handoffs | — |
| EVL-33 | per request reasoning budget | [per-request-reasoning-budget.md](per-request-reasoning-budget.md) | Step 3: implement fix (force </think> / suppress think scaffold at budget=0 for hybrid SSM), needs running server | — |
| EVL-34 | rao redel substrate spike | [rao-redel-substrate-spike.md](rao-redel-substrate-spike.md) | Run a naturally-delegating workload A/B (HotpotQA/DeepDive or small base model) before Step 3 escalation | — |
| EVL-35 | re4 protocol redesign | [re4-protocol-redesign.md](re4-protocol-redesign.md) | RE-4.2 — non-saturation probe (operator quiet-window, current v9 topology re-attested, autopilot stopped): frontdoor-only, two-phase, R=409… | — |
| EVL-36 | repl session memory maturity | [repl-session-memory-maturity.md](repl-session-memory-maturity.md) | D-a5 — If DataFrame persistence is ever wanted, use a typed columnar codec, not the | — |
| EVL-37 | repl turn efficiency | [repl-turn-efficiency.md](repl-turn-efficiency.md) | S4 Omega A/B: measure turns per task, token cost per task, and accuracy delta. This gates suggestion, verbosity, and any extra tool-surface… | — |
| EVL-38 | repo readiness scorer | [repo-readiness-scorer.md](repo-readiness-scorer.md) | Close remaining root L5.self_optimizing_loop gap (13-item queue) | — |
| EVL-39 | rlm contested claims self evaluation | [rlm-contested-claims-self-evaluation.md](rlm-contested-claims-self-evaluation.md) | E1 — RESCOPED BY E0: measure Base vs Depth-1 first, not depth-1 vs depth-2. E0 showed | — |
| EVL-40 | safetygate rlvr provenance audit 2026 07 22 | [safetygate-rlvr-provenance-audit-2026-07-22.md](safetygate-rlvr-provenance-audit-2026-07-22.md) | Extract the SafetyGate/RLVR provenance findings to docs and move to completed/ — all 9 boxes closed | — |
| EVL-41 | scorer fork drift audit 2026 07 22 | [scorer-fork-drift-audit-2026-07-22.md](scorer-fork-drift-audit-2026-07-22.md) | Unify the _inband_error_text / _forced_role_serving_mismatch local copies (seeding 3bfe2584) with eval_tower's originals into one shared mo… | — |
| EVL-42 | scoring infra standardization | [scoring-infra-standardization.md](scoring-infra-standardization.md) | 1b — migrate research consumers to the canonical lib and delete each duplicate extractor | — |
| EVL-43 | sliders local validation | [sliders-local-validation.md](sliders-local-validation.md) | Operator decision: KB-RAG K7 precondition fired — evaluate SLIDERS DB+SQL alternative (Phase 0 falsification) now, or keep parked? | — |
| EVL-44 | stale open audit 2026 07 18 | [stale-open-audit-2026-07-18.md](stale-open-audit-2026-07-18.md) | Re-anchor GEMV to its 2 live graph-fusion tasks; move the deprioritized SIMD Phase 0–5 plan to a closed appendix | — |
| EVL-45 | strand rust coder rustevo2 verification | [strand-rust-coder-rustevo2-verification.md](strand-rust-coder-rustevo2-verification.md) | Phase B single-instance RustEvo2 bench (USER APPROVAL REQUIRED) - Strand, Qwen2.5-Coder-14B base, gemma4 worker, sequential | — |
| EVL-46 | tool use eval contract | [tool-use-eval-contract.md](tool-use-eval-contract.md) | TU-DTAP-1 — Import a reviewed, bounded Apache-2.0 DTAP subset into a disposable local runner. | — |
| EVL-47 | vidya belief substrate program | [vidya-belief-substrate-program.md](vidya-belief-substrate-program.md) | SC15 — drain the 129-correction queue, cited head first: `cli.py corrections --as-of <ts>` | — |
| EVL-48 | fable5 window2 findings 05c mi210 lever cate | [fable5-window2-findings-05c-mi210-lever-category-matrix.md](fable5-window2-findings-05c-mi210-lever-category-matrix.md) | L12 — n-gram/prompt-lookup on GPU: 27B-Q8 + fp16 over code/JSON/prose sets, sweeping the three ngram spec types | — |
| EVL-49 | reboot gated inventory and staging | [reboot-gated-inventory-and-staging.md](reboot-gated-inventory-and-staging.md) | S-01 — re-pin the 25 uptime-capped inference-batch entries to the v9 era and the live topology hash | INF-06, INF-07, RTG-46 |

## Cross-domain

Edges to other domains go in the `Deps` column as bare IDs (e.g. `RTG-12`). Do **not** add a second row for a handoff another index owns.

## Reporting

After changing any row: run `python3 scripts/handoffs/index_state.py` to refresh generated state, then `--check` before committing.
