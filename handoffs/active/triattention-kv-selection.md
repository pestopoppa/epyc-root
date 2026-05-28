# KV Cache Selection/Eviction - Expected Attention Active Work

**Status**: COMPACTED 2026-05-28 - Expected Attention deployed; active only for S8 autopilot profiles and S9 auto-trigger.
**Created**: 2026-04-08
**Updated**: 2026-05-28
**Priority**: MEDIUM
**Categories**: kv_cache, inference_serving, memory_bandwidth
**Parent index**: [inference-acceleration-index.md](inference-acceleration-index.md)
**Completed ledger**: [triattention-kv-selection-deployment-completed-through-2026-05-28.md](../completed/triattention-kv-selection-deployment-completed-through-2026-05-28.md)

## Executor Start Here

Expected Attention is already the production path. Do not reopen S1/S4/S5/S6/S7 as if this were still an evaluation stub. The current implementation work is role-profile exploration for autopilot, then orchestrator auto-trigger wiring once stable profiles exist.

## Outstanding Tasks

- [ ] **S8 autopilot exploration**: sweep `keep_ratio` and `layer_weights` per production role; persist Pareto profiles with quality, speed, cost, and reliability axes.
- [ ] **S9 orchestrator auto-trigger**: blocked until S8 produces stable role profiles. Wire learned profiles, not hardcoded defaults.
- [ ] **S2 TriAttention concentration validation**: optional comparator only; no longer blocks Expected Attention deployment.
- [ ] **S3 selection plus quantization stacking**: reopen after S8 only if stacked compression is a production need. Otherwise evaluate Attention Matching or another high-compression path first.

## Minimal S8 Artifact

```text
Role:
Model:
Context/workload:
keep_ratio candidates:
layer_weight candidates:
Pareto winner:
Quality delta:
Speed/cost delta:
Reliability notes:
```

## Dependency Forks

| Outcome | Next action |
|---|---|
| S8 finds stable per-role profiles | Promote S9 orchestrator auto-trigger wiring and update the relevant model/role registry. |
| S8 profiles vary heavily by prompt or model | Keep manual/autopilot-exploration mode; do not hardcode defaults in orchestrator. |
| S8 quality loss is unacceptable at useful ratios | Close auto-trigger path for now and retain manual compaction only. |
| Production needs higher compression than Expected Attention provides | Reopen S3 stacking or compare Attention Matching before adding more kernel complexity. |

## Completed Scope

| Scope | Result | Ledger |
|---|---|---|
| S4 kernel port | Complete in `llama-kv-compress.h/.cpp`; production kernel commit `4babc8fe3`. | [completed ledger](../completed/triattention-kv-selection-deployment-completed-through-2026-05-28.md) |
| S1 PPL at 50% | PASS: Qwen3-1.7B 0.86 and Qwen3.5-35B 1.096, under the 1.10 gate. | [completed ledger](../completed/triattention-kv-selection-deployment-completed-through-2026-05-28.md) |
| S5 multi-ratio sweep | 90-75 identical, 50 safe, 25 aggressive, 10 cliff. | [completed ledger](../completed/triattention-kv-selection-deployment-completed-through-2026-05-28.md) |
| S6 server integration | `/slots/{id}?action=compact&scorer=expected_attention` landed. | [completed ledger](../completed/triattention-kv-selection-deployment-completed-through-2026-05-28.md) |
| S7 autopilot integration | `kv_compress.py`, `slot_compact`, and `program.md` Tier 4.5 landed. | [completed ledger](../completed/triattention-kv-selection-deployment-completed-through-2026-05-28.md) |

## Key Files

- `/mnt/raid0/llm/llama.cpp/llama-kv-compress.h`
- `/mnt/raid0/llm/llama.cpp/llama-kv-compress.cpp`
- `/mnt/raid0/llm/epyc-orchestrator/src/`
- `/mnt/raid0/llm/epyc-orchestrator/program.md`
- `/mnt/raid0/llm/epyc-inference-research/`
- `research/deep-dives/triattention-kv-selection-cluster.md`

## Reporting Instructions

After S8 runs, update this handoff with the artifact fields above and the decision on S9. If S9 opens, update [inference-acceleration-index.md](inference-acceleration-index.md), [routing-and-optimization-index.md](routing-and-optimization-index.md) if autopilot behavior changes, and [master-handoff-index.md](master-handoff-index.md).
