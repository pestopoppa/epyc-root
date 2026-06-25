# Research & Evaluation — Coordination Index

**Status**: active
**Updated**: 2026-06-25
**Purpose**: dispatch surface for pre-production research, evaluation, and monitoring work. Production orchestrator changes should route through `routing-and-optimization-index.md`.

> Completed checklist and research-intake chronology was compacted to [`../archived/research-evaluation-index-history-through-2026-06-19.md`](../archived/research-evaluation-index-history-through-2026-06-19.md). Current task truth lives in the owning handoffs and machine artifacts named below.

## Current Queue

| Priority | Work | Owner / source | Gate |
|---|---|---|---|
| HIGH | N2 per-question ledger + sequential verdict readiness | [`evidence-plane-ledger-and-sequential-verdicts.md`](evidence-plane-ledger-and-sequential-verdicts.md) | Continue trusted vector and seq-shadow accrual; do not enable authority until readiness passes. |
| HIGH | N1+N4 evidence-plane instrument repair tails | [`evidence-plane-instrument-repair.md`](evidence-plane-instrument-repair.md) | W5 core_v2 remains no-go; W6/W8 need larger clean evidence windows. |
| HIGH | Eval-tower verification EV-4/8/9/10 | [`eval-tower-verification.md`](eval-tower-verification.md) | Re-sequenced after N2/N4 evidence substrate; EV-4/H5 is inference-gated.<br>• READY — DRACO rubric methodology (intake-713) → EV-9 (owning handoff), CPU-portable, no GPU: adopt separate positive/negative rubric weighting, multi-judge ranking-stability (reuse `src/bradley_terry.py`), and saturation testing (reject >90%-scoring sentinels; also a ch07 recommendation). DRACO's 4 content axes are an ADDITION to EV-9's 4 MindDR-process dims, not a swap. Production-query sampling is gated (substitute `frontier-f1-real-task-corpus` once ≥100 records). (added 2026-06-20 via research-intake batch deep-dive) |
| HIGH | Tulving K-MEM-1 interpretation/follow-up | `bulk-inference-campaign.md` Package K / P3b below | Completed/scored 2026-06-20; corrected in research `9e63af0` after parser repair. Mixed baseline (`avg F1=0.4309`, Simple Recall `0.5530`, chrono `0.1593`) now has a targeted follow-up manifest in research `2eb94f8`; use it before any memory-routing conclusion. |
| MED | Tool-output compression P4c-P4e | [`tool-output-compression.md`](tool-output-compression.md) | Top-up telemetry, registration smoke, rollout gate. |
| MED | Repo-readiness remediation pickup | [`repo-readiness-scorer.md`](repo-readiness-scorer.md) | Passive AutoPilot pickup JSON is generated (`mode=advisory_only`, `authority_gate=false`); live consumption still needs a separate default-off protocol. |
| MED | Real-task eval distribution | [`frontier-f1-real-task-corpus.md`](frontier-f1-real-task-corpus.md) | W2 compact corpus landed in orchestrator `e59577b7`: 372 training-eligible class+outcome rows, prompt text/hash refs omitted. Token telemetry for future rows landed in orchestrator `b8c8ac52`; the 2026-06-21 live token refresh clears the narrow token/class subgate (`213` training-eligible rows, `202` token payload rows, 0 prompt text). Historical conversation importer landed in orchestrator `b4b96580`; sidechain-excluded mixed source-family summary landed in orchestrator `13269679` with 1,246 prompt-free rows represented across `live_progress` and `historical_operator_conversation`. Orchestrator `40a87f3d` adds source-family weighted shares and passes the dominance gate (`historical=0.585007`, `live=0.414993`, max allowed `0.60`). Next: clean-window W3 EvalTower per-question ledger run; the first packaged concurrent-window attempt failed reliability and is not acceptance evidence. |
| MED | Granite embedder bench Phase B | [`granite-97m-r2-bench-plan.md`](granite-97m-r2-bench-plan.md) | A-fast corpus/harness verified; remaining prep is model artifacts/server recipes, then an embedder serving window only. No production model reload required. |
| MED | RoPE long-context matrix K-ROPE-1 | P10 below / clean-window manifest | Continue only in clean model-batched windows; worker path needs Gemma4 MTP serving fix before evidence. |
| LOW | Reasoning compression tails | [`reasoning-compression.md`](reasoning-compression.md), [`memento-block-reasoning-compression.md`](memento-block-reasoning-compression.md) | Enforce path blocked until signal is predictive; Memento S2/S3 remain gated. |
| LOW | Monitoring-only model/research watches | TQ3, Log-Linear GDN, YaRN, Ouro, SLIDERS, swarm/Strand, AgentWorld | Do not consume inference unless the owning handoff's gate is met. |

## Active Evaluation Packages

| Package | Current status | Next action |
|---|---|---|
| K-MEM-1 Tulving episodic | Completed/scored on `ingest_long_context` with `--server-mode --skip-moe-reduction`; research `b6edc64` packages raw run JSON/index/preflight and research `9e63af0` packages corrected scorer JSON/Markdown plus `tulving_failure_modes.md`. Scorer: `456/456` scored, missing ground truth `0`, avg F1 `0.4309`, Simple Recall `0.5530`, Chronological Awareness `0.1593`, avg decode `17.27 t/s`. Research `2eb94f8` adds `scripts/benchmark/build_tulving_followup_manifest.py` and `data/package_k/tulving_followup_20260619_141212_{manifest.jsonl,summary.md}`. | Treat as a mixed baseline: lexical entity/time/location recall is usable, event/detail and chronology are weak, and zero-answer hallucination checks fail. The follow-up slice has 120 ID-only rows: 40 zero-answer abstention, 40 event-content/detail recall, and 40 chronology-order cases. K-MEM no longer blocks the next throughput-sensitive lane. |
| G5 short-m@k clean-window | Frontdoor result is committed in research `7e9f67f` at `benchmarks/results/clean_window/short_mk_voting/frontdoor.json`: `status=complete`, `40` questions, `14/40` correct (`0.35` accuracy), GPQA `2/20`, MATH `12/20`, no completion errors. | Schedule remaining G5 roles only in clean model-batched windows; verify affinity/canonical preflight first and avoid blocked exact-boundary K-ROPE or stack mutation in the same window. |
| G11/G10 AA-Omniscience clean-window | Frontdoor run `20260620_035613` first exited after `24:57` with `26 completed`, `0 skipped`, and `1800 errors`; log `/mnt/raid0/llm/tmp/g11_frontdoor_20260620T035601Z.log`; partial `frontdoor_moe4_lookup_*`, `frontdoor_moe6_lookup_*`, and `frontdoor_moe8_lookup_*` files are speed-only telemetry. Triage found the 1800 errors were exactly `baseline`, `moe4`, and `moe6` quality rows falling through to missing subprocess binaries because the generated command omitted `--server-mode`. The corrected server-mode rerun completed under the same run id and is packaged in research `587c6cd`; deterministic-F1 scoring is packaged in research `92a5602` at `data/package_g/omniscience/`. Frontdoor baseline/moe4/moe6 OI is `0.2753` / `0.2725` / `0.2812`. Worker run `20260620_062750` completed with canonical preflight `data/preflight/2026-06-20_062737.json` and is packaged/scored in research `32f2c27`; worker baseline accuracy `0.1433`, avg F1 `0.2280`, hallucination rate `0.6829`, OI `0.2302`, avg decode `52.63 t/s`, labels `86` correct / `351` incorrect / `110` partial / `53` not attempted. Architect G10 run `20260620_081041` completed against resident `architect_general :8083` after canonical preflight `data/preflight/2026-06-20_081041.json`; research `b91d16c` packages/scored `600` baseline rows with accuracy `0.1317`, avg F1 `0.2103`, hallucination rate `0.4971`, OI `0.3173`, avg decode `11.05 t/s`, labels `79` correct / `259` incorrect / `101` partial / `161` not attempted. The combined factual-risk report is `ready_for_tier_update` with all expected roles present and a deterministic AA-Omniscience 4-class scoring policy accepted for role-tier recalibration. | Frontdoor, worker, and architect deterministic scorer evidence are packaged and aggregator-compatible (`3,000` total scored rows). G12 production multipliers are now updated in orchestrator to tier_1 `0.727978`, tier_2 `0.824178`, tier_3 `1.0`; mode/canary/enforce decisions remain separate telemetry gates. |
| K-ROPE-1 | Valid 4K/8K rows for frontdoor/architect/ingest and valid 16K rows for frontdoor/ingest are committed in research; worker rows are not evidence. | Fix/re-attest worker serving before counting worker RoPE cells; continue exact-boundary-safe chat-mode probes. |
| EV-4 / H5 Scoring Verifiers | Adapter loads 6,701 candidate-level verifier items after research `7c11920`. | Run calibration baseline only after evidence substrate sequencing is clear. |
| K-DIV-1 | Diversity metric code exists; semantic baseline requires embedder/model serving. | Keep thresholds gated until N2 ledger vectors and validation rows exist. |
| K-SKILL-1 | Decision logic and default-off accept-path wiring exist. | Run paired skill/no-skill validation before any accept-path authority. |

## Additional Active References

These handoffs are still active but currently sit behind specific evidence, model-availability, or policy gates. Keep them indexed; do not spend inference unless the owning gate is met.

| Handoff | Current role | Next action |
|---|---|---|
| [agent-file-prose-compression.md](agent-file-prose-compression.md) | Static agent-file compression pilot; Phase 3 eval is the blocker. | Write the runnable Phase 3 command, then evaluate per-model compliance curves. |
| [integration-test-coverage.md](integration-test-coverage.md) | Active test-gap backlog after Phases 1-4 compaction. | Add narrow integration tests only when a current failing surface or coverage tranche justifies it. |
| [mathsmith-hc-formalizer-eval.md](mathsmith-hc-formalizer-eval.md) | Formalizer evaluation gate. | Check model artifacts, then run the S4 mini-protocol. |
| [per-request-reasoning-budget.md](per-request-reasoning-budget.md) | Hybrid SSM/MoE reasoning-budget investigation. | Steps 3-4 need a running server; keep code changes gated by reproduction. |
| [rao-redel-substrate-spike.md](rao-redel-substrate-spike.md) | RAO/ReDel substrate spike; preflight passed and harness is prepared. | Execute Step 2 only in a clean inference window. |
| [sliders-local-validation.md](sliders-local-validation.md) | Parked speculative SLIDERS validation. | Do not integrate before KB-RAG/default-retrieval gates justify it. |
| [strand-rust-coder-rustevo2-verification.md](strand-rust-coder-rustevo2-verification.md) | Standalone RustEvo2 verification gate. | Launch only after approval; result gates swarm dataset work. |
| [eval-benchmark-cost-reduction.md](eval-benchmark-cost-reduction.md) | Mid-range difficulty filter (intake-727) for TB Core external evals — NOT autopilot (wrong objective: ranking ≠ regression detection; stable core has only 3/50 mid-range qids). Actionable for TB Core v0.1.1 re-evaluations only: 44–70% task reduction at ρ ≥ 0.87 rank fidelity after cold-start. | Gate behind TB Core adapter build (~1d: wrap `/v1/chat/completions` in Terminus-compatible Harbor adapter) + one baseline TB Core run. Separately: use autopilot per-qid pass-rate data for question pool *curation* — rotate permanently saturated/floor qids from `simpleqa`, `coder`, `general` stable core. |

## Dependency Graph

```text
N1/N4 instrument repair + N2 ledger readiness
  -> EV-4/H5 calibration authority
  -> K-DIV/K-SKILL thresholds and accept-path changes

Completed K-MEM baseline
  -> interpret low Tulving score / compare follow-up cells
  -> schedule next clean-window model-batched package

Weighted real-task corpus summary + token completeness
  -> real-suite v1 curation
  -> promotion eval real-task slice
```

## Key Files

| Resource | Path |
|---|---|
| Benchmark runners | `/mnt/raid0/llm/epyc-inference-research/scripts/benchmark/` |
| Tulving results | `/mnt/raid0/llm/epyc-inference-research/benchmarks/results/runs/20260619_141212/` |
| Tulving targeted follow-up | `/mnt/raid0/llm/epyc-inference-research/data/package_k/tulving_followup_20260619_141212_manifest.jsonl` |
| F1 compact real-task corpus | `/mnt/raid0/llm/epyc-orchestrator/orchestration/reports/real_task_corpus_20260620/real_tasks.training_eligible.compact.jsonl` |
| F1 mixed corpus summary | `/mnt/raid0/llm/epyc-orchestrator/orchestration/reports/real_task_corpus_mixed_20260620/summary.md` |
| F1 historical conversation sources | `/mnt/raid0/llm/cloud-llm-vault/epyc/claude/`, `/mnt/raid0/llm/cloud-llm-vault/claude/`, `/mnt/raid0/llm/claude-backups/` |
| F1 historical importer smoke | `/mnt/raid0/llm/tmp/f1-historical-smoke-20260620/manifest.json` |
| Repo-readiness passive AutoPilot pickup | `/mnt/raid0/llm/epyc-root/data/repo_readiness/repo_readiness_autopilot_pickup_2026-06-21.json` |
| Packaged G11 frontdoor raw-response run | `/mnt/raid0/llm/epyc-inference-research/benchmarks/results/runs/20260620_035613/` |
| Scored G11 frontdoor AA labels | `/mnt/raid0/llm/epyc-inference-research/data/package_g/omniscience/frontdoor_20260620_035613_aa_omniscience.jsonl` |
| Packaged G11 worker raw-response run | `/mnt/raid0/llm/epyc-inference-research/benchmarks/results/runs/20260620_062750/` |
| Scored G11 worker AA labels | `/mnt/raid0/llm/epyc-inference-research/data/package_g/omniscience/worker_general_20260620_062750_aa_omniscience.jsonl` |
| Clean-window manifest | `/mnt/raid0/llm/epyc-inference-research/docs/data/clean_window_measurement_manifest.json` |
| AA-Omniscience manifest | `/mnt/raid0/llm/epyc-inference-research/docs/data/aa_omniscience_measurement_manifest.json` |
| Eval-tower code | `/mnt/raid0/llm/epyc-orchestrator/scripts/autopilot/eval_tower.py` |
| Sequential verdict code | `/mnt/raid0/llm/epyc-orchestrator/src/autopilot_core/sequential_verdict.py` |

## Reporting

After completing a row, update the owning handoff, this index, `master-handoff-index.md` if priority changed, and `progress/YYYY-MM/YYYY-MM-DD.md`. Put measured artifacts in the owning repo and cite exact run directories or report filenames.
