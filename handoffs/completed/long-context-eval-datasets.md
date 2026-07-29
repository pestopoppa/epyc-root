# Long-Context Evaluation Datasets

**Status**: READY — all datasets downloaded, adapters integrated, validation passed
**Created**: 2026-03-26
**Updated**: 2026-04-05
**Priority**: MEDIUM
**Related**: kv-cache-quantization.md (Phase 3d TurboQuant validation)
**Performance context**: At long sequences (16K+), attention rises from 7-12% to 25-35% of per-token compute and transitions from memory-bound to compute-bound (GPU research intake-304/306, architecture-independent finding). This means long-context eval should measure both quality AND throughput — degraded throughput at long context may indicate attention becoming the bottleneck rather than weight GEMMs. Flash attention (`-fa`) impact is negligible at short context but significant at 16K+.

## Purpose

Collect publicly available long-context evaluation datasets for quality benchmarking of KV cache quantization at extended contexts (64K-128K+) and YaRN context extension evaluation.

## Datasets

### LongBench v2 (THUDM)
- **Paper**: arXiv 2308.14508 (v1), v2 is updated
- **Source**: `THUDM/LongBench-v2` (HuggingFace, parquet-native)
- **License**: MIT
- **Tasks**: 503 multiple-choice questions across long-context domains
- **Context**: 52K-1.5M chars (measured)
- **Disk**: 870 MB
- **Status**: DONE — downloaded, adapter integrated, validated
- **Note**: Using v2 because v1 uses deprecated HF loading scripts (incompatible with `datasets` v4.8+)

### RULER (NVIDIA)
- **Paper**: arXiv 2404.06654
- **Source**: https://github.com/hsiehjackson/RULER
- **License**: Apache 2.0
- **Tasks**: NIAH (needle retrieval) at configurable context lengths. Generates synthetic tasks on-demand.
- **Context**: Configurable 4K-128K+
- **Disk**: 0.6 MB (repo only, tasks generated at runtime)
- **Status**: DONE — cloned, adapter generates NIAH tasks with configurable length/count

### Needle-in-a-Haystack (Parameterized)
- **Source**: https://github.com/gkamradt/LLMTest_NeedleInAHaystack
- **License**: MIT
- **Tasks**: Parameterized needle retrieval across context lengths × needle positions
- **Context**: 16K-262K chars (measured), using real Paul Graham essays as haystack
- **Disk**: 7.2 MB
- **Status**: DONE — cloned, adapter generates matrix: 5 lengths × 5 depths = 25 test cases
- **Note**: Supersedes the single hardcoded 12K needle test in `benchmarks/prompts/v1/long_context.yaml`

### ZeroSCROLLS (tau)
- **Paper**: arXiv 2305.14196
- **Source**: `tau/zero_scrolls` (HuggingFace, raw zip download)
- **Tasks**: 10 tasks (gov_report, summ_screen_fd, qmsum, squality, qasper, narrative_qa, quality, musique, space_digest, book_sum_sort)
- **Context**: 11K-53K chars (measured, validation split)
- **Disk**: 543 MB
- **Status**: DONE — downloaded via huggingface_hub (raw zips), adapter integrated
- **Note**: Using validation split (test split has no labels — leaderboard submission only)

### L-Eval (L4NLP)
- **Paper**: arXiv 2307.11088
- **Source**: `L4NLP/LEval` (HuggingFace, raw JSONL download)
- **License**: CC-BY-4.0
- **Tasks**: 20 tasks — 7 Exam (closed-ended) + 13 Generation (open-ended)
- **Context**: 17K-116K chars (measured)
- **Disk**: 31 MB
- **Status**: DONE — downloaded via huggingface_hub (raw JSONL), adapter integrated
- **Note**: L-Eval uses `outputs` (plural) and `instructions` (list) fields

## Integration

### Adapter Module
`epyc-inference-research/scripts/benchmark/long_context_adapters.py` — 5 classes inheriting `BaseAdapter`:
- `LongBenchAdapter` — loads from local JSONL or HF directly
- `ZeroSCROLLSAdapter` — loads from extracted JSONL files
- `LEvalAdapter` — loads from downloaded JSONL files
- `RULERAdapter` — generates NIAH tasks at configurable context length
- `NeedleAdapter` — generates parameterized needle tests using Paul Graham essays

### Registration
- Added to `ADAPTER_SUITES` in `dataset_adapters.py`
- Added to `get_adapter()` dispatch via lazy import bridge
- Added to `ROLE_SUITE_MAP` in `suites.py`:
  - `ingest`, `long_context`: full battery (all 5 + existing `long_context`)
  - `frontdoor`, `architect`: `longbench` + `needle_parameterized`

### Scripts
- **Download**: `download_long_context_datasets.py [--force]`
- **Validate**: `validate_long_context_datasets.py [--sample N] [--suite NAME]`

### HF datasets v4 Compatibility
HF `datasets` v4.8+ dropped support for custom loading scripts. Workarounds:
- LongBench → use v2 (parquet-native)
- ZeroSCROLLS → download raw zip files via `huggingface_hub`, extract JSONL
- L-Eval → download raw JSONL files via `huggingface_hub`

## Key File Locations

| Resource | Path |
|----------|------|
| Dataset storage | `/mnt/raid0/llm/data/eval/` |
| Metadata manifest | `/mnt/raid0/llm/data/eval/metadata.json` |
| Adapter module | `epyc-inference-research/scripts/benchmark/long_context_adapters.py` |
| Download script | `epyc-inference-research/scripts/benchmark/download_long_context_datasets.py` |
| Validation script | `epyc-inference-research/scripts/benchmark/validate_long_context_datasets.py` |
| RULER repo | `/mnt/raid0/llm/data/eval/ruler/repo/` |
| Needle repo | `/mnt/raid0/llm/data/eval/needle/repo/` |
| Paul Graham essays | `/mnt/raid0/llm/data/eval/needle/repo/needlehaystack/PaulGrahamEssays/` |

## Next Steps (require inference)

1. Run KV cache quality comparison: TurboQuant hybrid buffer vs f16 at 64K-128K contexts
2. Run YaRN quality degradation curve: 256K → 512K → 1M with YaRN extension
3. Measure speed impact of YaRN extension at extended contexts
4. Use Qwen2.5-7B-Instruct (128K native context) as primary eval model
