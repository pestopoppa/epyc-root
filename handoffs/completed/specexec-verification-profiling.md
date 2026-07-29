# Handoff: SpecExec Verification Profiling

**Status**: completed
**Created**: 2026-03-07
**Completed**: 2026-03-10
**Blocked by**: None
**Blocks**: hsd-hierarchical-self-speculation, tree-speculation-numa-drafting
**Results**: `epyc-inference-research/docs/experiments/specexec-verification-profile.md`

## Objective

Confirm or deny the SpecExec thesis on EPYC 9655 hardware: **verifying N tokens costs approximately the same as verifying 1 token** because the bottleneck is weight-loading from RAM, not compute. Pure measurement, zero code changes. Produce publication-quality data and plots for research documentation.

## Background

Chapter 10 (`epyc-inference-research/docs/chapters/10-advanced-speculative-decoding.md`) surveys 23 papers on advanced speculation techniques. The central finding (SpecExec) is that on bandwidth-bound hardware, verification batch size has near-zero marginal cost. Current production uses linear speculation with `--draft-max 16-24`. If the thesis holds, trees of hundreds of nodes could be nearly free to verify, potentially yielding 5-9x additional speedup.

## Existing Infrastructure

Reuse and extend existing scripts rather than creating new ones:

| Script | Path | Reuse |
|--------|------|-------|
| `run_benchmark.py` | `epyc-inference-research/scripts/benchmark/` | Unified runner — supports `spec` config type, records acceptance_rate per question |
| `sidecar_benchmark.py` | `epyc-inference-research/scripts/benchmark/` | Server-mode benchmark — captures `draft_n`/`draft_n_accepted` from HTTP API |
| `run_draft_discovery.sh` | `epyc-inference-research/scripts/benchmark/` | K-sweep with acceptance rate extraction |
| `bench_tree_speculation.sh` | `epyc-inference-research/scripts/benchmark/` | Tree param sweep — n_parallel × p_split, CSV with acceptance rates |
| `output_parser.py` | `epyc-inference-research/scripts/lib/` | `parse_acceptance_rate()`, `parse_timings()` for CLI output extraction |

Orchestrator telemetry (already wired):
- `InferenceResult` carries `n_tokens_drafted`, `n_tokens_accepted`, `acceptance_rate` (`model_server.py:132-135`)
- `llama_server.py` logs `"Spec accept: %d/%d"` at INFO level (lines 317-325, 579-587)

Phase 3 should use `sidecar_benchmark.py` or `run_benchmark.py` rather than raw CLI, to leverage this existing telemetry pipeline. Phase 1-2 use `llama-bench` (raw CLI) since they measure isolated latency, not end-to-end speculation.

## Phase 1 — Batch Verification Latency Curve

Use `llama-bench` to measure prompt-processing time across batch sizes. The `-p` flag varies batch size (prompt processing = parallel verification analog), `-n 0` disables generation. The metric is **pp time vs batch size**.

```bash
llama-bench -m <model> -p 1,2,4,8,16,32,64,128,256,512 -n 0 \
  --numa distribute -t 96 -r 3 -o csv
```

Measurement controls:
- Default warmup (do NOT use --no-warmup)
- Also run with `--numa isolate` to characterize cross-node penalty
- Use `--mmap 0` (preload, default) for consistent bandwidth measurement
- Drop page caches between model switches: `sync && echo 3 > /proc/sys/vm/drop_caches`

Models to profile (use registry names — executor resolves paths via `model_registry.yaml`):

| Model | Registry Name | Size | Expected Behavior |
|-------|---------------|------|-------------------|
| Qwen3.5-27B-Q4_K_M | `Qwen3.5-27B-Q4_K_M` | 16 GB | Definitely bandwidth-bound, near-flat curve |
| Qwen3.5-9B-Q4_K_M | `Qwen3.5-9B-Q4_K_M` | 5.3 GB | Likely bandwidth-bound |
| Qwen2.5-7B-Instruct-f16 | `Qwen2.5-7B-Instruct-f16` | 15 GB | Bandwidth reference (f16) |
| Qwen3.5-0.8B-Q8_0 | `Qwen3.5-0.8B-Q8_0` | 775 MB | May become compute-bound at large N |

**Expected**: Near-flat latency curve for 9B+ models (bandwidth-bound). Inflection point for 0.8B model where compute begins to dominate.

**Output**: CSV files per model, matplotlib plot of latency vs batch size.

## Phase 2 — Draft Model Cost Profiling

Measure per-token generation time for each draft candidate (registry names used where available):

| Draft Model | Registry Name | Size | Notes |
|-------------|---------------|------|-------|
| Qwen3.5-0.8B-Q4_0 | `Qwen3.5-0.8B-Q4_0` | 484 MB | |
| Qwen3.5-0.8B-Q8_0 | `Qwen3.5-0.8B-Q8_0` | 775 MB | |
| Qwen2.5-0.5B-Instruct | `Qwen2.5-0.5B-Instruct-Q8_0` | 949 MB | Registry has Q8_0; handoff originally said f16. Use Q8_0 per registry. |
| Qwen3-Coder-0.75B | `Qwen3-Coder-Instruct-DRAFT-0.75B-32k-Q4_0` | 448 MB | |
| Qwen3-0.6B-Q8_0 | `Qwen3-0.6B-Q8_0` | 768 MB | |
| Llama-3.2-1B-Instruct-f16 | — (not in registry, add first) | 2.4 GB | Path: `/mnt/raid0/llm/models/Llama-3.2-1B-Instruct-f16.gguf`. Add to `model_registry.yaml` before profiling. |
| Gemma-3-1B-IT-Q8_0 | `Gemma-3-1B-IT` | 1.0 GB | |
| DeepSeek-R1-Distill-Qwen-1.5B | `DeepSeek-R1-Distill-Qwen-1.5B` | 1.1 GB | |

Compute **critical ratio**: `T_draft_per_token / T_target_verify`. This ratio determines the break-even point: how many draft tokens can be generated before drafting cost exceeds verification savings.

**Output**: Table with per-token cost and T_draft/T_target ratios for each draft model against each target.

## Phase 3 — Large-K Linear Speculation Test

Push `--draft-max` higher using existing server flags:

**Test pairs**:
- **Qwen3.5-9B + Qwen3.5-0.8B** (same-family, both on disk)
- **Qwen3.5-27B + Qwen3.5-0.8B** (same-family, larger target)
- **Qwen2.5-7B + Qwen2.5-0.5B** (production pair, both on disk)

**K values**: 16 (current production), 32, 64, 128

**Prompts**: Use standard benchmark questions from `question_pool.py`
(`/mnt/raid0/llm/epyc-inference-research/scripts/benchmark/question_pool.py`).
Select 20 prompts spanning `coder` and `thinking` suites for reproducibility.

**Metrics**: Acceptance rate curve, end-to-end throughput (tokens/s), cliff detection (where throughput plateaus or drops).

**Output**: Table and plot of throughput vs K for each pair.

## Phase 4 — HSD Integration Design Document

Read the HSD codebase and map capped branch resampling to llama.cpp:

- `common_sampler_sample_and_accept_n()` in `common/sampling.cpp`
- Called in `server-context.cpp` (search: `common_sampler_sample_and_accept_n`; currently line 2891, may shift with upstream changes)

Document:
- What functions change
- Estimated LOC
- Expected gain (theoretical + bounded by Phase 1-3 data)
- Risk assessment

## Phase 5 — Publication-Quality Output

Produce:
1. CSV data files for all measurements (stored in `epyc-inference-research/data/specexec/`)
2. Plot script (`epyc-inference-research/scripts/benchmark/plot_verification_profile.py`) generating:
   - Latency vs batch size curves (per model)
   - Draft model cost comparison bar chart
   - Large-K throughput vs K curves (per pair)
3. Summary table in box-drawing format
4. Publish to `epyc-inference-research/docs/experiments/specexec-verification-profile.md`
5. Update Chapter 10 with empirical validation results

## Validation Checklist

- [ ] Latency curve data for 4 models × 10 batch sizes, with plots
- [ ] Draft model timing table with per-token cost and T_draft/T_target ratios
- [ ] Large-K speculation throughput results for 3 pairs × 4 K values
- [ ] HSD integration design document (functions, LOC, expected gain)
- [ ] All results published in research docs with supporting plots

## Files

| Action | File |
|--------|------|
| Create | `epyc-inference-research/data/specexec/` (directory for CSV output) |
| Create | `epyc-inference-research/docs/experiments/specexec-verification-profile.md` |
| Create | `epyc-inference-research/scripts/benchmark/profile_verification_cost.sh` (thin wrapper: loops `llama-bench` across models, collects CSVs) |
| Create | `epyc-inference-research/scripts/benchmark/plot_verification_profile.py` |
| Update | `epyc-inference-research/docs/chapters/10-advanced-speculative-decoding.md` (add empirical section) |

**No code modifications** to llama.cpp or orchestrator.

## Conflict Analysis

No conflicts with: qwen35-frontdoor-benchmark, orchestrator-stack-audit, routing-intelligence, or any other active handoff. This is a pure measurement workload.

## Closeout

Update `logs/agent_audit.log`, `progress/2026-03/YYYY-MM-DD.md`, this handoff status, Chapter 10.
