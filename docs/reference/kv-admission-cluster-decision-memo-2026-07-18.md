# KV Admission Cluster Decision Memo - 2026-07-18

## Scope

This memo uses existing evidence only. It does not change active handoffs, production configuration, or inference plans. All measurements and ratios below are **observation-grade** unless explicitly stated otherwise; none are decision-gating under `MEASUREMENT.md`.

## Current Evidence

- StreamingLLM is the missing floor for the May KV-admission cluster. The sink-plus-window scaffold exists, disabled by default, but the 4-axis floor sweep is still pending. Until that sweep exists, LU-KV, KVP, ForesightKV, SP-KV, and PBKV cannot be rank-ordered against the simplest viable baseline.
- Expected Attention is already the deployed KV selection path. Its open work is role-profile exploration and auto-trigger policy, not proof that selection works at all.
- Attention Matching has working infrastructure and old positive evidence, but the current handoff explicitly requires a refresh on current long-context/coding traffic before any new rollout decision.
- Memento block masking has runtime feasibility evidence, but deployment remains blocked on S2 format/quality evidence from a trained adapter. It should not drive KV admission decisions yet.
- KV quantization is already a production configuration axis and remains orthogonal to selection/eviction methods.

## New CPU KV Matrix

Artifact:
`/mnt/raid0/llm/epyc-inference-research/data/kv_admission_cpu_v7/kv_admission_cpu_qwen06b_matrix_20260718T203506Z/summary.json`

Shape: **observation-grade** `llama-bench` on `Qwen_Qwen3-0.6B-Q8_0.gguf`, prompt `2048`, generation `256`, `3` reps, `96` threads, CPU-only flags `-ngl 0 -dev none -fa 1`, experimental-v7 CPU binary.

Results, all **observation-grade**:

| KV mode | Prompt t/s | Decode t/s | Read |
|---|---:|---:|---|
| default f16/f16 | 1809.91 | 91.37 | Best prompt and decode in this small CPU matrix |
| q8_0/q8_0 | 744.17 | 87.34 | Worst prompt; decode trails default |
| q8_0/q4_0 | 1252.44 | 90.14 | Decode is 1.032x q8_0/q8_0, 0.986x default |
| q4_0/q4_0 | 1276.15 | 90.29 | Effectively tied with q8_0/q4_0 decode |

Interpretation: this does **not** justify changing KV quant defaults. It weakens any assumption that q8_0/q4_0 is a generally better CPU default: on this small model, f16/f16 wins, q8_0/q4_0 only beats q8_0/q8_0 on decode, and q4_0/q4_0 is effectively tied with q8_0/q4_0. The useful default remains role/model/context-specific, with quantization treated as a rider or memory-capacity lever unless a current role-shaped measurement proves otherwise.

## What Cannot Be Decided Yet

- Whether sink-plus-window at the target budgets is already good enough to demote attention-kernel methods.
- Whether LU-KV deserves promotion as the next attention-kernel method; that only follows if StreamingLLM degrades materially at the `50%` budget on representative workloads.
- Whether KVP or ForesightKV offer enough incremental value over the floor to justify RL/fine-tuning or kernel complexity.
- Whether SP-KV has any local value beyond a demoted/watch status, because the cited external refutation still needs our internal floor result.
- Whether PBKV should run sequentially after StreamingLLM or in parallel; PBKV remains strategically open because it composes at the orchestrator layer, but the floor still informs its baseline comparison.

## Cluster Disposition

- **Keep open**: StreamingLLM floor sweep. This is the next gating measurement.
- **Keep open**: PBKV, because it composes with sink-plus-window and can operate above the kernel layer.
- **Keep open, refresh-gated**: Attention Matching, only after current-stack long-context/coding refresh and comparison against Expected Attention/StreamingLLM.
- **Keep open, training-gated**: Memento, only after S2 format compliance, compression ratio, quality delta, and decode stability evidence.
- **Defer**: LU-KV until StreamingLLM shows a meaningful 50%-budget degradation; if the floor is strong, demote it.
- **Defer/demote pending floor**: KVP and ForesightKV, because their extra complexity cannot be priced without the floor. ForesightKV is additionally fine-tuning-infra-gated.
- **Demote/watch**: SP-KV unless the internal StreamingLLM floor unexpectedly fails where SP-KV would plausibly help.
- **No default change**: KV quant mode defaults should not move based on the new Qwen3-0.6B CPU matrix.

## Next Minimal Measurement

Run the smallest StreamingLLM floor slice that can answer the cluster gate before expanding the matrix:

- One current representative long-context/coding workload.
- One production-relevant model lane already used for long-context decisions.
- Full-KV control plus StreamingLLM at `50%` budget; add `25%` only if the `50%` result is not clearly decisive.
- Include current default KV precision and one F16 KV control only if needed to isolate quantization interaction.
- Report accuracy/quality delta first, then throughput/memory observations. Do not promote, demote, or change defaults from throughput-only evidence.

Decision rule for that minimal slice: if the `50%` StreamingLLM floor preserves the workload within the existing handoff's quality tolerance, demote LU-KV/KVP/ForesightKV implementation priority and keep PBKV/role-policy work open. If it fails materially, promote LU-KV as the next frozen-weights-compatible attention-kernel candidate and keep PBKV open as a composing orchestrator-layer path.
