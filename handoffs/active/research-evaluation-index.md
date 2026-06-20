# Research & Evaluation — Coordination Index

**Status**: active
**Updated**: 2026-06-20
**Purpose**: dispatch surface for pre-production research, evaluation, and monitoring work. Production orchestrator changes should route through `routing-and-optimization-index.md`.

> Completed checklist and research-intake chronology was compacted to [`../archived/research-evaluation-index-history-through-2026-06-19.md`](../archived/research-evaluation-index-history-through-2026-06-19.md). Current task truth lives in the owning handoffs and machine artifacts named below.

## Current Queue

| Priority | Work | Owner / source | Gate |
|---|---|---|---|
| HIGH | N2 per-question ledger + sequential verdict readiness | [`evidence-plane-ledger-and-sequential-verdicts.md`](evidence-plane-ledger-and-sequential-verdicts.md) | Continue trusted vector and seq-shadow accrual; do not enable authority until readiness passes. |
| HIGH | N1+N4 evidence-plane instrument repair tails | [`evidence-plane-instrument-repair.md`](evidence-plane-instrument-repair.md) | W5 core_v2 remains no-go; W6/W8 need larger clean evidence windows. |
| HIGH | Eval-tower verification EV-4/8/9/10 | [`eval-tower-verification.md`](eval-tower-verification.md) | Re-sequenced after N2/N4 evidence substrate; EV-4/H5 is inference-gated. |
| HIGH | Tulving K-MEM-1 interpretation/follow-up | `bulk-inference-campaign.md` Package K / P3b below | Completed/scored 2026-06-20; corrected in research `9e63af0` after parser repair. Mixed baseline (`avg F1=0.4309`, Simple Recall `0.5530`, chrono `0.1593`) needs targeted follow-up before any memory-routing conclusion. |
| MED | Tool-output compression P4c-P4e | [`tool-output-compression.md`](tool-output-compression.md) | Top-up telemetry, registration smoke, rollout gate. |
| MED | Real-task eval distribution | [`frontier-f1-real-task-corpus.md`](frontier-f1-real-task-corpus.md) | W2 needs two-week soak and >=100 real records before W3 suite curation. |
| MED | Granite embedder bench Phase B | [`granite-97m-r2-bench-plan.md`](granite-97m-r2-bench-plan.md) | Embedder serving window only; does not require production model reload. |
| MED | RoPE long-context matrix K-ROPE-1 | P10 below / clean-window manifest | Continue only in clean model-batched windows; worker path needs Gemma4 MTP serving fix before evidence. |
| LOW | Reasoning compression tails | [`reasoning-compression.md`](reasoning-compression.md), [`memento-block-reasoning-compression.md`](memento-block-reasoning-compression.md) | Enforce path blocked until signal is predictive; Memento S2/S3 remain gated. |
| LOW | Monitoring-only model/research watches | TQ3, Log-Linear GDN, YaRN, Ouro, SLIDERS, swarm/Strand, AgentWorld | Do not consume inference unless the owning handoff's gate is met. |

## Active Evaluation Packages

| Package | Current status | Next action |
|---|---|---|
| K-MEM-1 Tulving episodic | Completed/scored on `ingest_long_context` with `--server-mode --skip-moe-reduction`; research `b6edc64` packages raw run JSON/index/preflight and research `9e63af0` packages corrected scorer JSON/Markdown plus `tulving_failure_modes.md`. Scorer: `456/456` scored, missing ground truth `0`, avg F1 `0.4309`, Simple Recall `0.5530`, Chronological Awareness `0.1593`, avg decode `17.27 t/s`. | Treat as a mixed baseline: lexical entity/time/location recall is usable, event/detail and chronology are weak, and zero-answer hallucination checks fail. K-MEM no longer blocks the next throughput-sensitive lane. |
| G5 short-m@k clean-window | Frontdoor run active on resident port `8070`; target artifact `benchmarks/results/clean_window/short_mk_voting/frontdoor.json` is not yet evidence until the runner exits and JSON validates. | Package and commit the frontdoor artifact after completion; then schedule remaining G5 roles only in clean model-batched windows. |
| K-ROPE-1 | Valid 4K/8K rows for frontdoor/architect/ingest and valid 16K rows for frontdoor/ingest are committed in research; worker rows are not evidence. | Fix/re-attest worker serving before counting worker RoPE cells; continue exact-boundary-safe chat-mode probes. |
| EV-4 / H5 Scoring Verifiers | Adapter loads 6,701 candidate-level verifier items after research `7c11920`. | Run calibration baseline only after evidence substrate sequencing is clear. |
| K-DIV-1 | Diversity metric code exists; semantic baseline requires embedder/model serving. | Keep thresholds gated until N2 ledger vectors and validation rows exist. |
| K-SKILL-1 | Decision logic and default-off accept-path wiring exist. | Run paired skill/no-skill validation before any accept-path authority. |

## Dependency Graph

```text
N1/N4 instrument repair + N2 ledger readiness
  -> EV-4/H5 calibration authority
  -> K-DIV/K-SKILL thresholds and accept-path changes

Completed K-MEM baseline
  -> interpret low Tulving score / compare follow-up cells
  -> schedule next clean-window model-batched package

Real-task corpus soak
  -> real-suite v1 curation
  -> promotion eval real-task slice
```

## Key Files

| Resource | Path |
|---|---|
| Benchmark runners | `/mnt/raid0/llm/epyc-inference-research/scripts/benchmark/` |
| Tulving results | `/mnt/raid0/llm/epyc-inference-research/benchmarks/results/runs/20260619_141212/` |
| Clean-window manifest | `/mnt/raid0/llm/epyc-inference-research/docs/data/clean_window_measurement_manifest.json` |
| AA-Omniscience manifest | `/mnt/raid0/llm/epyc-inference-research/docs/data/aa_omniscience_measurement_manifest.json` |
| Eval-tower code | `/mnt/raid0/llm/epyc-orchestrator/scripts/autopilot/eval_tower.py` |
| Sequential verdict code | `/mnt/raid0/llm/epyc-orchestrator/src/autopilot_core/sequential_verdict.py` |

## Reporting

After completing a row, update the owning handoff, this index, `master-handoff-index.md` if priority changed, and `progress/YYYY-MM/YYYY-MM-DD.md`. Put measured artifacts in the owning repo and cite exact run directories or report filenames.
