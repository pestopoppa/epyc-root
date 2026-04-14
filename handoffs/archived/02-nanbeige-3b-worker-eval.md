# Nanbeige4.1-3B Worker Evaluation

**Status**: ARCHIVED (2026-04-05) — superseded by Qwen3-Coder-30B-A3B worker decision
**Created**: 2026-03-03
**Priority**: ~~P0~~ — superseded; worker tier uses 30B-A3B, not 3B/7B class
**Move to**: `handoffs/archived/` when directory permissions allow
**Effort**: Low
**Source**: [Nanbeige4.1-3B (huggingface.co/papers/2602.13367)](https://huggingface.co/papers/2602.13367)

## Research Review

### Nanbeige4.1-3B: Small Model That Reasons, Aligns, and Acts
**Authors:** Chen Yang, Guangyue Peng et al. (Nanbeige LLM Lab)

First open-source 3B model simultaneously excelling at agentic behavior (600+ tool-call turns), code generation, and reasoning. Outperforms 30B-32B models on coding (LCB-V6: 76.9 vs Qwen3-32B 55.7) and math (AIME 2026: 87.4 vs 75.8). Training innovations: progressive reward modeling (point-wise → pair-wise), complexity-aware code rewards (gates time-complexity reward on correctness), synthetic data for deep search.

**Orchestrator Relevance: VERY HIGH.** Direct candidate for our worker model tier:
- **600+ tool-call agentic**: Matches our REPL workflow where workers iterate many turns
- **3B parameters**: Would run extremely fast on our EPYC hardware, potentially replacing 7B workers
- **Complexity-aware RL**: Their technique of gating algorithmic efficiency rewards on correctness parallels our solution file persistence approach (fix first, optimize second)
- **Progressive reward modeling**: Could inform how we train/select specialist routing
- **BFCL-V4 tool use: 56.5%** — best-in-class for small models, directly relevant to our tool permission system

### Key Benchmark Numbers
| Benchmark | Nanbeige-3B | Qwen3-32B | Gap |
|-----------|-------------|-----------|-----|
| LCB-V6 (coding) | 76.9 | 55.7 | +21.2 |
| AIME 2026 (math) | 87.4 | 75.8 | +11.6 |
| BFCL-V4 (tool use) | 56.5 | — | Best-in-class 3B |

## References

- [Nanbeige4.1-3B paper](https://huggingface.co/papers/2602.13367)
- [BFCL-V4 (Berkeley Function Calling Leaderboard)](https://gorilla.cs.berkeley.edu/leaderboard.html)
- [GAIA benchmark](https://huggingface.co/gaia-benchmark)
- Current worker model: Qwen2.5-7B (explore worker on port 8082)
- Seeding infrastructure: `/mnt/raid0/llm/epyc-inference-research/scripts/benchmark/seed_specialist_routing.py`
- Model registry: `/mnt/raid0/llm/epyc-orchestrator/orchestration/model_registry.yaml`

## Implementation Steps

### 1. Acquire and convert model
- Download Nanbeige4.1-3B from HuggingFace
- Convert to GGUF format for llama.cpp inference
- Quantize at Q4_K_M and Q8_0 for comparison
- Place in `/mnt/raid0/llm/models/nanbeige-3b/`

### 2. Benchmark against Qwen2.5-7B on seeding suite
- Run full seeding suite with both models on identical question pool
- Compare: coding accuracy, tool-call success rate, turn count, tokens consumed
- Key suites: `thinking`, `coder`, `math`, `agentic`
- Record throughput (tokens/sec) for both models

### 3. Test REPL workflow compatibility
- Verify model follows tool-call format expected by orchestrator
- Test solution file read/patch workflow
- Test session log integration
- Validate output stays within token caps

### 4. If quality holds: create model registry entry
- Add to `model_registry.yaml` with appropriate role assignments
- Configure as worker alternative in orchestrator stack
- A/B test in production routing

## Acceptance Criteria

- [ ] Model downloaded, converted to GGUF, quantized
- [ ] Seeding benchmark completed against Qwen2.5-7B baseline
- [ ] Throughput comparison documented (expecting 2x+ improvement at 3B vs 7B)
- [ ] REPL workflow compatibility verified
- [ ] Decision documented: adopt as worker / keep as alternative / reject
