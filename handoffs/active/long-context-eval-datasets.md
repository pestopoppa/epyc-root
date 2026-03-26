# Long-Context Evaluation Datasets

**Status**: STUB — datasets to collect for TurboQuant quality validation
**Created**: 2026-03-26
**Priority**: MEDIUM
**Related**: kv-cache-quantization.md (Phase 3d TurboQuant validation)

## Purpose

Collect publicly available long-context evaluation datasets used by the TurboQuant/QJL papers for quality benchmarking of KV cache quantization at extended contexts (64K-128K+).

## Datasets

### LongBench (THUDM)
- **Paper**: arXiv 2308.14508
- **Source**: https://huggingface.co/datasets/THUDM/LongBench
- **License**: MIT
- **Tasks**: 21 tasks across 6 categories (single-doc QA, multi-doc QA, summarization, few-shot, synthetic, code completion)
- **Context**: 5K-15K tokens average, max ~30K
- **Status**: TODO

### RULER
- **Paper**: arXiv 2404.06654
- **Source**: https://github.com/hsiehjackson/RULER
- **License**: Apache 2.0
- **Tasks**: Needle retrieval, variable tracking, aggregation, QA at configurable lengths
- **Context**: Configurable 4K-128K+
- **Status**: TODO

### Needle-in-a-Haystack
- **Source**: https://github.com/gkamradt/LLMTest_NeedleInAHaystack
- **License**: MIT
- **Tasks**: Single needle retrieval at various depths and context lengths
- **Context**: Configurable
- **Status**: PARTIAL — basic needle test implemented in bench_kv_cache_quant.sh

### ZeroSCROLLS
- **Paper**: arXiv 2305.14196
- **Source**: https://huggingface.co/datasets/tau/zero_scrolls
- **Tasks**: 10 tasks: summarization, QA, aggregation over long documents
- **Context**: 10K-100K+ tokens
- **Status**: TODO

### L-Eval
- **Paper**: arXiv 2307.11088
- **Source**: https://huggingface.co/datasets/L4NLP/LEval
- **License**: CC-BY-4.0
- **Tasks**: 20 tasks spanning exam, writing, summarization, math
- **Context**: 3K-60K tokens
- **Status**: TODO

## Integration Plan

1. Download datasets to `/mnt/raid0/llm/data/eval/`
2. Create adapter scripts in `/mnt/raid0/llm/epyc-inference-research/scripts/benchmark/`
3. Key comparison: TurboQuant hybrid buffer vs f16 at 64K-128K contexts
4. Use Qwen2.5-7B-Instruct (128K native context) as primary eval model
