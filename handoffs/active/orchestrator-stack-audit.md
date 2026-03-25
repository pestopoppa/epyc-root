# Orchestrator Stack Lineup Audit

**Status**: BLOCKED (validation sweep running; additional models to download/benchmark)
**Priority**: HIGH
**Blocked by**: qwen35-frontdoor-benchmark.md (needs full-suite spec/lookup tests), active validation sweep
**Related**: qwen35-frontdoor-benchmark.md, full-benchmark-rescore.md (completed)

## Current Stack vs Rescored Quality

| Role | Model | Config | Quality | TPS | Verdict |
|------|-------|--------|---------|-----|---------|
| frontdoor | Qwen3-Coder-30B MoE6 | +spec+lookup | 71% | 47.1 | CHANGE |
| coder_escalation | Qwen2.5-Coder-32B | +spec+lookup+corpus | 74% | 39.4 | KEEP |
| architect_general | Qwen3-235B-A22B | full+spec | 69% | 6.1 | CHANGE |
| architect_coding | Qwen3-Coder-480B | full+spec+lookup | 73% | 9.0 | KEEP |
| ingest_long_context | Qwen3-Next-80B MoE4 | | 75% | 6.3 | KEEP |
| worker_explore | Qwen2.5-7B f16 | +spec | ~44% | 46.6 | ACCEPTABLE |
| worker_vision | Qwen2.5-VL-7B | baseline | 92% VL | 18.7 | KEEP |
| vision_escalation | Qwen3-VL-30B MoE4 | | 92% VL | 24.8 | KEEP |

## Change 1: Frontdoor

**Recommendation**: Qwen3.5-35B-A3B Q4_K_M (unsloth), config TBD

Best candidates from existing benchmarks:

| Config | Quality | Median TPS | Sustained TPS | Notes |
|--------|---------|------------|---------------|-------|
| unsloth Q4_K_M MoE4 | 90% | 23.8 | 12.6 | Best quality; MoE4 > baseline likely variance |
| unsloth Q4_K_M baseline | 87% | 22.0 | 12.2 | Safer bet (no MoE); same quality within noise |
| abliterated Q6_K MoE6 | 79% | 42.0 (bimodal) | 14.5 | 42 t/s median but 41% of questions at ~10 t/s |

Speed trade-off: 47 t/s → ~24 t/s (-49%). Still interactive (24 t/s = 1400 tok/min).

**~~Wild card: Qwen3.5-27B dense~~** — STALE (2026-03-25): ALL Qwen3.5 variants (0.8B–397B) are hybrid Delta Net (3:1 recurrent:attention), NOT pure attention. Spec decode is not viable — verification batches cost ~Nx single decode due to sequential recurrent processing. Baseline speeds: 9B ~12-14 t/s, 27B ~8-9 t/s. Quality: 9B Q4KM 75%, 27B Q6K 85%. Registry corrected to `architecture: ssm_hybrid`.

**Open questions (block implementation)**:
- Spec decode tested with 1 speed question only — inconclusive. Need full 70-question suite test.
- Prompt lookup tested with 1 question only — showed 13.5 t/s vs 23.8 baseline. Also inconclusive.
- Q6_K_moe6 "42 t/s" is bimodal: P25=10.2, median=42.9, P75=50.8, mean=34.8. For hard problems expect ~10 t/s sustained.
- IP: abliterated Q6_K_moe6 = 6/11 vs unsloth Q4_K_M = 9/11. Unsloth is clearly better at format compliance.
- Tool use / REPL compatibility not yet tested for any Qwen3.5.
- Only unsloth Q4_K_M exists on disk. All Q5/Q6/Q8 quants are abliterated (5-15pp quality penalty).
- **Qwen3.5-27B, 122B-A10B, 397B-A17B, 9B, 4B** not yet downloaded or benchmarked.

## Change 2: Architect General

**Recommendation**: Replace Qwen3-235B-A22B (69%) with Qwen3-Coder-480B (73%, shared with architect_coding)

235B failure analysis:
- IP: 1/11 (catastrophic format failures)
- LC: 1/6
- These are structural, not variance

480B at 73% (full experts, with spec) = 9.0 t/s. Better on every suite except general (8 vs 9, within noise). Same server can serve both architect roles since both would use full experts.

MoE override is per-server (`--override` at load time), not per-request. So:
- **Option A** (recommended): Both roles share one 480B server at full experts. Simple, 133GB freed.
- **Option B**: Two 480B instances (one moe6, one full). Memory: removes 235B (133GB) + adds 480B (~130GB at Q4_K_M with mmap sharing). Net ~neutral. Gives architect_general a faster config.

**Bigger question**: Qwen3.5-35B baseline (87%) outscores 480B full (73%). But the full Qwen3.5 family includes:
- **122B-A10B** (MoE, 10B active, ~65GB at Q4_K_M) — could be the ideal architect_general. More total params than 235B with SSM+MoE efficiency.
- **397B-A17B** (MoE, 17B active, ~200GB at Q4_K_M) — ultimate architect candidate if memory allows.
These need to be downloaded and benchmarked before deciding the architect swap.

## Roles Confirmed OK

- **coder_escalation** (74%, 39 t/s): No better 32B coder available. 39 t/s is sustained (spec+lookup+corpus).
- **ingest_long_context** (75%, 6.3 t/s): Only SSM model. Thinking variant gets 9/9 LC but leaks `<think>` tags.
- **worker_explore** (~44%, 46.6 t/s): Workers handle decomposed subtasks; failures escalate. gemma-3-12b (79%) tested with spec = 14.8 t/s, too slow for worker role.
- **worker_vision** (92% VL): Only VL model with tool calls. Qwen3-VL-4B is 93% but no tool calls.
- **vision_escalation** (92% VL, 24.8 t/s): Already optimal.

## Pre-Implementation Checklist

### Models to download (GGUF quants from HuggingFace)
- [ ] unsloth Qwen3.5-35B-A3B Q6_K / Q8_0 (if published — currently only Q4_K_M exists as non-abliterated)
- [x] **Qwen3.5-27B** (hybrid Delta Net, 28B) — spec decode NOT viable (baseline 8.8-9.4 t/s)
- [ ] **Qwen3.5-122B-A10B** (MoE, 10B active) — architect_general candidate (~65GB at Q4_K_M)
- [ ] **Qwen3.5-397B-A17B** (MoE, 17B active) — ultimate architect candidate (~200GB at Q4_K_M)
- [x] **Qwen3.5-9B** (hybrid Delta Net, 10B) — spec decode NOT viable (baseline 12.7-14.5 t/s)
- [x] **Qwen3.5-4B** (hybrid Delta Net, 5B) — benchmarked, spec decode NOT viable
- [ ] Qwen3.5-2B / 0.8B — draft model candidates for spec decode with 27B

### Benchmarks — Phase 1 (35B-A3B acceleration gaps)
- [ ] Qwen3.5 35B Q4_K_M spec decode: full 70-question suite (current data is 1-question only)
- [ ] Qwen3.5 35B Q4_K_M prompt lookup: full 70-question suite (current data is 1-question only)
- [ ] Qwen3.5 35B tool use / REPL format compatibility test with frontdoor system prompt

### Benchmarks — Phase 2 (new models)
- [x] Qwen3.5-27B baseline (hybrid — spec decode NOT viable, all variants converge ~12 t/s)
- [ ] Qwen3.5-122B-A10B baseline + MoE reduction sweep
- [ ] Qwen3.5-397B-A17B baseline + MoE reduction (if memory allows)
- [x] Qwen3.5-9B baseline (hybrid — spec decode NOT viable)
- [x] Qwen3.5-4B baseline (hybrid — spec decode NOT viable)

### Benchmarks — Phase 3 (validation)
- [ ] 480B as architect_general: 5 complex non-coding problems manually
- [ ] Best frontdoor candidate: 20-question validation seeding

### Implementation (after benchmarks)
- [ ] Update orchestrator_stack.py: frontdoor model + acceleration config
- [ ] Update orchestrator_stack.py: architect_general → 480B (or Qwen3.5 if benchmarks warrant)
- [ ] Update model_registry.yaml (both repos): role → model mappings, quality/throughput fields
- [ ] Update RESULTS.md with new stack lineup
- [ ] Run 20-question validation seeding across all roles on new stack
- [ ] Update progress report

## Closeout
- [ ] All pre-implementation benchmarks completed
- [ ] Frontdoor swapped and validated
- [ ] Architect_general swapped and validated
- [ ] Documentation updated
- [ ] Move to completed/
