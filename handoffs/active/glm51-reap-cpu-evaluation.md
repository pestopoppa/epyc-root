# GLM-5.1-555B-A14B-REAP — CPU Evaluation (Q4_K_M GGUF)

**Status**: new (download pending)
**Created**: 2026-04-22 (via research intake deep-dive revision of intake-427)
**Updated**: 2026-04-22
**Categories**: moe_optimization, local_inference, model_evaluation
**Priority**: MEDIUM (stack simplification candidate, storage-constrained)
**Parent index**: [`inference-acceleration-index.md`](inference-acceleration-index.md)
**Related**: [`reap-moe-expert-pruning.md`](../completed/reap-moe-expert-pruning.md), [`gpu-acceleration-path.md`](gpu-acceleration-path.md)

## Objective

Evaluate GLM-5.1-555B-A14B-REAP Q4_K_M GGUF as a potential single-model replacement for both architect_general (Qwen3.5-122B-A10B, 69GB) and architect_coding (REAP-246B-A35B, 139GB). Combined 208GB replaced by a single 325GB model with 14B active params per token drawing from 192 specialized experts.

## Research Context

| Intake ID | Title | Relevance | Verdict |
|-----------|-------|-----------|---------|
| intake-427 | 0xSero/GLM-5.1-555B-A14B-REAP-GGUF (REVISED) | high | new_opportunity |
| intake-281 | GLM-5: from Vibe Coding to Agentic Engineering | reference | background |
| intake-181 | REAP: Why Pruning Prevails for One-Shot MoE Compression | reference | already_integrated |

## Model Specifications

| Property | Value |
|----------|-------|
| **Architecture** | `GlmMoeDsaForCausalLM` (DSA + MLA + MoE) |
| **Total params** | 555B (REAP'd from 744B base) |
| **Active params/token** | ~14B (top-8 routing from 192 experts) |
| **Experts/layer** | 192 (pruned from 256 by REAP 25%) |
| **Layers** | 78 |
| **Context window** | 131,072 tokens |
| **GGUF source** | `0xSero/GLM-5.1-555B-A14B-REAP-GGUF` |
| **GGUF size (Q4_K_M)** | 325GB (single file) |
| **Quantization** | Mixed: Q8_0 (attention, shared expert, DSA indexer, dense layers 0-2) + Q4_K/Q6_K (routed experts) |
| **llama.cpp flags** | `--reasoning on --reasoning-format deepseek --jinja` |
| **llama.cpp arch** | `LLM_ARCH_GLM_DSA` (PR#19460, DSA indexer tensors loaded but forward pass not implemented — dense MLA fallback) |

## Published Benchmarks (0xSero, Q4_K_M GGUF)

| Suite | Metric | Score | Repetition Loops |
|-------|--------|-------|------------------|
| Terminal-Bench (50) | Proxy Pass | 44/50 (88%) | 0/50 |
| SWE-bench Pro (50) | Proxy Pass | 33/50 (66%) | 0/50 |
| GSM8K (50) | Correct | 30/50 (60%) | 0/50 |
| HLE (50) | Correct | 9/50 (18%) | 0/50 |
| Degeneration fuzz (45) | Borderline | 4/45 (8.9%) | No hard failures |

**Comparison targets** (our current production):
- architect_general (Qwen3.5-122B-A10B): quality 2.57/3, 4.3 t/s, 69GB
- architect_coding (REAP-246B-A35B): quality 82%, 8.0 t/s, 139GB

## Storage Constraint

| Metric | Value |
|--------|-------|
| RAID0 free (current) | 417GB |
| Model download | 325GB |
| RAID0 free (post-download) | 92GB |
| architect_general (reclaimable) | 69GB |
| architect_coding (reclaimable) | 139GB |
| RAID0 free (post-swap, if successful) | 300GB |

**Mitigation**: Phase 1 audits cold models. If 92GB interim free is insufficient, temporarily offload a non-production model. Successful replacement nets 300GB free (better than many states in project history).

## Known Risks

| Risk | Severity | Mitigation |
|------|----------|------------|
| GLM-4.7 quality precedent | Medium | GLM-4.7 scored 43% with SEVERE repetition loops in EPYC benchmarks. GLM-5.1 is a different generation with DSA+MLA, but caution warranted. Phase 3 smoke test catches this. |
| DSA indexer unimplemented | Low (short ctx) / High (long ctx) | Dense MLA fallback works for <8K context. For 131K, the indexer would be critical. Fork development target — tensors already loaded. |
| NUMA characteristics unknown | Medium | 325GB model may not split cleanly across NUMA nodes. Phase 4 benchmarks both single-192t and NUMA-2x96t configs. |
| 444B variant trap | Critical | The 444B/154-expert GGUF is BROKEN (29% degeneration). Only the 555B/192-expert variant should be used. DO NOT download the 444B variant. |
| Storage during evaluation | Low | 92GB free is tight but manageable — no concurrent model downloads during eval. |

## Evaluation Plan

### Phase 1 — Pre-Download Storage Audit
- [ ] Verify RAID0 free space (`df -h /mnt/raid0/llm/`)
- [ ] Identify cold models in `/mnt/raid0/llm/models/` that could be offloaded if 92GB is insufficient
- [ ] Confirm the correct HuggingFace repo: `0xSero/GLM-5.1-555B-A14B-REAP-GGUF` (NOT the 444B variant)
- [ ] Verify file name pattern: `GLM-5.1-555B-A14B-REAP-Q4_K_M*.gguf`

### Phase 2 — Download
- [ ] `huggingface-cli download 0xSero/GLM-5.1-555B-A14B-REAP-GGUF --local-dir /mnt/raid0/llm/models/0xSero_GLM-5.1-555B-A14B-REAP-GGUF`
- [ ] Verify download integrity (file size matches 325GB)

### Phase 3 — Smoke Test (GATE: abort on repetition loops)
- [ ] Load model: `llama-server -m <path> -ngl 0 -c 8192 -np 1 --jinja --reasoning on --reasoning-format deepseek --host 127.0.0.1 --port 8090`
- [ ] Test 5 basic prompts: greeting, code generation, reasoning, structured output, tool calling
- [ ] Check for repetition loops (the failure mode that killed GLM-4.7 and the 444B variant)
- [ ] **GATE**: Any repetition loops → abort evaluation, document failure mode

### Phase 4 — Throughput Benchmark (GATE: abort if < 4.3 t/s)
- [ ] Single-model 192t: `numactl --interleave=all llama-server -m <path> -t 192 ...`
- [ ] NUMA 2x96t: two instances on NUMA node 0 and node 1 respectively
- [ ] Record: prefill tok/s, generation tok/s, time-to-first-token
- [ ] Compare against architect_general (4.3 t/s) and architect_coding (8.0 t/s)
- [ ] **GATE**: If generation tok/s < 4.3 (worse than current slowest architect), evaluate whether quality gain justifies throughput loss. If < 2.0 t/s, abort.

### Phase 5 — Quality Eval Phase 1: General Knowledge
- [ ] Run AA-Omniscience suite via `run_benchmark` against GLM-5.1-REAP
- [ ] Run same suite against architect_general (Qwen3.5-122B) for direct comparison
- [ ] Record: accuracy, hallucination rate, abstention rate
- [ ] Compare quality scores (need >= 2.50/3 to match architect_general's 2.57/3)

### Phase 6 — Quality Eval Phase 2: Agentic Coding
- [ ] Run agentic coding subset (Terminal-Bench-style + SWE-bench-style tasks)
- [ ] Run same suite against architect_coding (REAP-246B) for direct comparison
- [ ] Record: pass rate, code correctness, tool-calling accuracy
- [ ] Compare against 82% quality baseline

### Phase 7 — Stack Simplification Analysis (if quality parity+)
- [ ] Compute RAM savings: 208GB freed - 325GB used = net 117GB more disk, but 1 model instead of 2
- [ ] Evaluate routing simplification: remove 2-tier architect routing, single escalation target
- [ ] Assess NUMA allocation impact: 325GB across 2 NUMA nodes vs current split
- [ ] Document throughput tradeoff: expected tok/s vs current architect models

### Phase 8 — Production Swap (if viable)
- [ ] Add `glm51_reap_architect` role to `model_registry.yaml`
- [ ] Update Q-scorer baselines (RI-0 pattern from routing-intelligence.md)
- [ ] Update NUMA allocation config
- [ ] Remove or demote architect_general and architect_coding roles
- [ ] Run routing regression tests
- [ ] Delete old model files to reclaim 208GB

### Phase 9 — Document Failure (if not viable)
- [ ] Record specific failure mode (quality regression? throughput? repetition? storage?)
- [ ] Retain model if disk permits, or delete to reclaim 325GB
- [ ] Update this handoff status to "concluded — not viable" with findings
- [ ] Add to monitoring: DSA indexer implementation in llama.cpp fork (single highest-leverage event)

## Open Questions

- [ ] Does llama.cpp load the Q4_K_M GGUF without patches? (DSA indexer tensors present but unused in forward pass)
- [ ] Repetition loop risk: GLM-4.7 had severe issues — does GLM-5.1 REAP truly fix this?
- [ ] NUMA config: 325GB requires 2x96t minimum — what are the cross-NUMA latency characteristics for a model this large?
- [ ] Context length: Can we validate the 131K context claim on EPYC hardware with dense MLA fallback?
- [ ] Spec decode: Is there a draft model compatible with GLM-5.1 architecture?
