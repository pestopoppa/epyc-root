# Unified Qwen3.5 Benchmark Sweep

**Status**: COMPLETE — Benchmarks done, stack recommendations ready, pending swap execution
**Created**: 2026-03-03
**Updated**: 2026-03-09
**Priority**: HIGH
**Workstream**: WS3
**Blocked by**: ~~WS2 (llama-cpp-upstream-rebase)~~ RESOLVED
**Target**: Full Qwen3.5 family benchmark + replace Qwen3-Coder-30B-A3B frontdoor

## Phase 1 Results — 35B-A3B Multi-Quant Sweep (COMPLETE)

### Phase 1 Scores (old: max_tokens=2048, pre-rescore)

| Model | Quality | Median TPS | Notes |
|-------|---------|------------|-------|
| **Qwen3.5 q4km MoE4** | **61/68 = 90%** | **23.8** | Best quality config (old scoring) |
| **Qwen3.5 q4km baseline** | **61/70 = 87%** | 12.4 | Consistent sustained TPS |
| Qwen3.5 q5ks baseline | 55/66 = 83% | 11.1 | math 10/10; fixes sum=185 |
| **Qwen3.5 q6k MoE6** | **52/66 = 79%** | **42.0** | Highest raw median; bimodal |

### Phase 1 RESCORED (2026-03-07, max_tokens=4096, Claude-as-Judge 0-3)

Old Phase 1 results were scored under 2048 max_tokens and deleted for rerun. Only Q4_K_M has been re-benchmarked so far. Q4KS/Q5KS/Q6K/Q8_0 results deleted — re-run in progress.

| Model | Quality | Avg TPS | Best Accel | Accel TPS | Notes |
|-------|---------|---------|------------|-----------|-------|
| **Qwen3.5 q4km baseline** | **151/183 = 83%** | 13.8 | moe6_lookup_n5 | 19.6 | 61q, 6 suites |
| Qwen3.5 q4km MoE4 | 143/183 = 78% | 13.7 | moe4_lookup_n5 | 18.8 | 61q, 6 suites |
| Qwen3.5 q4km MoE6 | 136/183 = 74% | 14.0 | moe6_lookup_n5 | 19.6 | 61q, 6 suites |
| **Qwen3.5 q4ks baseline** | **142/183 = 78%** | 13.9 | moe4 | 14.5 | 61q, 6 suites, avg 2.33 |
| **Qwen3.5 q5ks baseline** | **162/183 = 89%** | 12.5 | moe8_spec_q8_k8 | 13.3 | 61q, 6 suites, avg 2.66 |
| Qwen3.5 q6k/q8_0 | — | — | — | — | Re-run pending (next in sweep) |

### Key Phase 1 Findings
1. **Quality reversal**: Qwen3.5 q4km baseline (83%) beats frontdoor MoE4 (61%) and MoE6 (71%)
2. **All old frontdoor scores were inflated 20-30pp** by lazy scoring
3. **Spec decode is a bust for 35B**: All spec configs slower than plain MoE4 due to SSM checkpoint overhead
4. **Abliteration penalty**: q4ks/q5ks show degenerate looping vs unsloth q4km
5. **Old scores inflated**: max_tokens=2048 caused think-block truncation; 4096 gives more accurate (lower) scores
6. **35B Q4KS/Q5KS/Q6K/Q8_0 results lost**: Deleted during token budget fix, review CSVs preserved in git (`_rescored.csv`)

## Phase 2 Results — Dense Model Baselines (2026-03-07)

All dense models have 60-61 quality questions across 6 suites (agentic, coder, general, instruction_precision, math, thinking). Quality scored by Claude-as-Judge (0-3 scale per question). Scores marked `~` are partial (only 3 suites scored so far).

| Model | Size | Base t/s | #Q | Quality | Best Accel Config | Accel t/s | Delta |
|-------|------|----------|-----|---------|-------------------|-----------|-------|
| qwen35_2b_q4km | 1.5GB | 28.7 | 61 | 1.95 | lookup_n5 | 65.8 | +129% |
| qwen35_2b_q6k | 2GB | 30.2 | 60 | 1.67 | lookup_n4 | 57.4 | +90% |
| qwen35_2b_q8 | 2GB | 27.0 | 60 | 1.82 | lookup_n4 | 47.8 | +77% |
| qwen35_4b_q4km | 3GB | 16.2 | 61 | 2.20 | lookup_n5 | 16.3 | +1% |
| qwen35_4b_q6k | 4GB | 16.4 | 61 | 2.31 | lookup_n5 | 16.1 | -2% |
| qwen35_4b_q8 | 5GB | 15.2 | 61 | 2.30 | lookup_n5 | 22.7 | +49% |
| **qwen35_9b_q4km** | 6GB | 14.5 | 61 | **2.25** | lookup_n5 | 25.1 | +73% |
| qwen35_9b_q6k | 7GB | 13.4 | 61 | 2.13 | lookup_n5 | 20.7 | +54% |
| **qwen35_9b_q8** | 10GB | 12.7 | 60 | **2.41** | spec+lookup k16 | 17.7 | +39% |
| **qwen35_27b_q4km** | 16GB | 8.8 | 61 | **2.38** | spec k32 | 13.4 | +53% |
| **qwen35_27b_q6k** | 21GB | 9.4 | 61 | **2.54** | spec k4 | 13.1 | +40% |

### Key Phase 2 Findings
1. **2B lookup is extreme**: Q4KM gets +129% from lookup_n5 (28.7 → 65.8 t/s)
2. **4B lookup barely helps Q4KM/Q6K** (~1%) but gives +64% for Q8_0
3. **9B Q8 is best dense worker**: 80% quality, spec+lookup gets 17.7 t/s
4. **27B Q4KM**: 79% quality, spec k32 gets 13.4 t/s — comparable to 35B baseline
5. **Higher quant ≠ higher quality**: Think-block truncation penalizes larger quants (more verbose reasoning exhausts token budget)
6. **All dense models now fully scored** (61/61 questions each, 6 suites). Previous partial scores updated.

### Issues Found During Phase 2
- **candidate_roles bug**: 2B/4B models had `candidate_roles: [worker]` mapping to only 3 suites. Fixed to `[frontdoor, worker, coder, general]` for full 6-suite coverage.
- **Timeout too short**: `_TIMEOUT_SIZE_MULTIPLIER` raised from 3→10, `_TIMEOUT_SIZE_BUFFER` from 120→300 for 4096-token completions
- **Sentinel TPS values**: 3 questions across 3 models stored TPS=1,000,000 (timeout indicator), filtered from averages
- **--with-lookup flag added**: New CLI flag enables `--lookup` on server for all configs including baseline quality runs
- **35B variant results lost**: Q4KS/Q5KS/Q6K/Q8_0 sweep results (207+ each) deleted during token budget fix, never re-run. Review CSVs preserved in git.
- **Master benchmark table updated**: RESULTS.md now has all Qwen3.5 entries with per-suite scores

## Phase 2 — Full Family Sweep (THIS HANDOFF)

### Models (all verified on disk)

#### Dense Models
| Role | Model | File | Size |
|------|-------|------|------|
| `qwen35_2b_q4km` | Qwen3.5-2B | `unsloth/Qwen3.5-2B-GGUF/Qwen3.5-2B-Q4_K_M.gguf` | 1.2 GB |
| `qwen35_2b_q6k` | Qwen3.5-2B | `unsloth/Qwen3.5-2B-GGUF/Qwen3.5-2B-Q6_K.gguf` | 1.5 GB |
| `qwen35_2b_q8` | Qwen3.5-2B | `unsloth/Qwen3.5-2B-GGUF/Qwen3.5-2B-Q8_0.gguf` | 1.9 GB |
| `qwen35_4b_q4km` | Qwen3.5-4B | `unsloth/Qwen3.5-4B-GGUF/Qwen3.5-4B-Q4_K_M.gguf` | 2.6 GB |
| `qwen35_4b_q6k` | Qwen3.5-4B | `unsloth/Qwen3.5-4B-GGUF/Qwen3.5-4B-Q6_K.gguf` | 3.3 GB |
| `qwen35_4b_q8` | Qwen3.5-4B | `unsloth/Qwen3.5-4B-GGUF/Qwen3.5-4B-Q8_0.gguf` | 4.2 GB |
| `qwen35_9b_q4km` | Qwen3.5-9B | `unsloth/Qwen3.5-9B-GGUF/Qwen3.5-9B-Q4_K_M.gguf` | 5.3 GB |
| `qwen35_9b_q6k` | Qwen3.5-9B | `unsloth/Qwen3.5-9B-GGUF/Qwen3.5-9B-Q6_K.gguf` | 7.0 GB |
| `qwen35_9b_q8` | Qwen3.5-9B | `unsloth/Qwen3.5-9B-GGUF/Qwen3.5-9B-Q8_0.gguf` | 8.9 GB |
| `qwen35_27b_q4km` | Qwen3.5-27B | `unsloth/Qwen3.5-27B-GGUF/Qwen3.5-27B-Q4_K_M.gguf` | 16 GB |
| `qwen35_27b_q6k` | Qwen3.5-27B | `unsloth/Qwen3.5-27B-GGUF/Qwen3.5-27B-Q6_K.gguf` | 21 GB |

#### MoE Models (Downloaded)
| Role | Model | Path | Size |
|------|-------|------|------|
| `qwen35_122b_q4km` | Qwen3.5-122B-A10B | `unsloth/Qwen3.5-122B-A10B-GGUF/Q4_K_M/...-00001-of-00003.gguf` | ~69 GB (3 shards) |
| `qwen35_397b_q4kxl` | Qwen3.5-397B-A17B | `unsloth/Qwen3.5-397B-A17B-GGUF/UD-Q4_K_XL/...-00001-of-00006.gguf` | ~205 GB (6 shards) |

**NOTE**: Both 122B and 397B downloaded 2026-03-05. Not yet benchmarked.

#### Draft Models (Tier D — existing)
| Role | File | Size |
|------|------|------|
| `draft_qwen35_0_8b_q4_0` | `unsloth/Qwen3.5-0.8B-GGUF/Qwen3.5-0.8B-Q4_0.gguf` | 0.5 GB |
| `draft_qwen35_0_8b_q8_0` | `unsloth/Qwen3.5-0.8B-GGUF/Qwen3.5-0.8B-Q8_0.gguf` | 0.8 GB |

**No new draft models** — 2B is too slow on CPU to be a valid draft. The 0.8B models are the right size for drafting. 2B models are tested as worker/candidate models only.

## Code Changes Required

### 1. `results.py` — Add `get_slowest_questions()`

**File**: `/mnt/raid0/llm/epyc-inference-research/scripts/benchmark/results.py`

Add method to `ResultsManager` (after `load_result()` ~line 188):
```python
def get_slowest_questions(self, run_id, model_role, config_name="baseline", n=3):
```
- Loads baseline JSON, flattens all `suite -> qid -> tps`, sorts ascending
- Returns N slowest as `[{suite, question_id, prompt, tokens_per_second}]`
- Returns `[]` if no baseline exists

Add module-level convenience wrapper (matching `result_exists()` pattern ~line 385).

### 2. `run_benchmark.py` — Add `_run_speed_question()` + CLI flags

**File**: `/mnt/raid0/llm/epyc-inference-research/scripts/benchmark/run_benchmark.py`

**New function** near `_run_speed_test()` (~line 482):
- `_run_speed_question(suite_name, question_id, prompt)` — runs inference on a specific question
- Stores via `add_question_result()` (per-question with TPS) not `add_speed_result()`

**New CLI flags**:
- `--speed-questions N` (default 0 = existing fixed-prompt behavior)
- `--baseline-run RUN_ID` (pull slowest questions from a previous run — needed for 35B which has baselines in run `20260303_170903`)

**Main loop change** (lines 835-850, `if config.speed_test_only:` block):
- When `speed_questions > 0`: call `get_slowest_questions()` for N slowest baseline questions
- Loop `_run_speed_question()` over each
- Fallback to fixed prompt if no baseline results (with warning)

**Update `count_pending_tests()`**: count N tests per speed config when `speed_questions > 0`.

### 3. `model_registry.yaml` — New model entries

**File**: `/mnt/raid0/llm/epyc-inference-research/orchestration/model_registry.yaml`

Add after existing qwen35 block (~line 1083):
- 11 dense-FFN hybrid roles (2B×3, 4B×3, 9B×3, 27B×2) with `architecture: ssm_hybrid` (corrected 2026-03-25: ALL Qwen3.5 are hybrid Delta Net, not pure attention)
- 2 MoE roles (122B, 397B) with `architecture: qwen35moe`, `baseline_experts` and `override_key: qwen35moe.expert_used_count`
- All Qwen3.5 models: `constraints.forbid: [eagle, speculative_decoding, prompt_lookup]` (Delta Net recurrent layers make spec decode net-negative)
- MoE reduction ranges: 122B tests `[4,6]` (baseline 8), 397B tests `[4,6,8]` (baseline 10)

**Temperature overrides** on each Qwen3.5 role (from HuggingFace model cards):
```yaml
temperature_overrides:
  coder: 0.6
  instruction_precision: 0.6
  general: 0.7
  agentic: 0.7
  long_context: 0.7
  thinking: 1.0
  math: 1.0
```

**Draft model updates**:
- Update `draft_qwen35_0_8b_q4_0` and `draft_qwen35_0_8b_q8_0` compatible_targets: add `qwen3.5-27b`, `qwen3.5-9b`

### 4. `registry.py` — Temperature override helper

**File**: `/mnt/raid0/llm/epyc-inference-research/scripts/lib/registry.py`

Add helper:
```python
def get_temperature_override(self, role: str, suite: str) -> Optional[float]:
```

### 5. `run_benchmark.py` — Apply temperature overrides

In `_run_quality_question()` (~line 580) and new `_run_speed_question()`:
- After `params = get_inference_params(suite)`, check registry for `temperature_overrides`
- If present and suite name matches, override `params["temperature"]`

### 6. `executor.py` — Add `moe_spec_lookup` compound config

**File**: `/mnt/raid0/llm/epyc-inference-research/scripts/lib/executor.py`

- Add `Config.compound_moe_spec_lookup()` classmethod (after `compound_moe_spec` ~line 677)
- config_type: `"moe_spec_lookup"` — combines MoE override + draft model + lookup flag
- Only works in server mode (llama-server supports `--lookup` + `-md` together)

- **Fix**: `get_configs_for_architecture()` MoE branch (~lines 724-753) currently hardcodes compound configs at `MIN_SAFE_EXPERTS` (4) only. Change to loop over ALL tested expert counts including baseline. For an 8-expert model this means generating lookup/spec/spec+lookup at experts=[4, 6, 8]. The `inherits_quality_from` should reference the matching moe config (e.g. `moe6` for 6 experts, `baseline` for baseline experts).
- Add `moe_spec_lookup` compound generation alongside `moe_spec` and `moe_lookup` in the same loop

- Update `build_command()` (~line 908): add `moe_spec_lookup` case

- Update `ServerManager.start()` (~line 186): add `lookup: bool = False` parameter, append `"--lookup"` to cmd when True

- Update `_ensure_server()` in `run_benchmark.py`: handle `moe_spec_lookup` config_type

## Sweep Plan

### Non-Qwen3.5 MoE models (compound config gap)

The executor fix (looping compound configs over all expert counts) also affects existing MoE models that never had baseline+spec or baseline+lookup tested. Include these in the sweep:

| Model | Role | Compounds to test |
|-------|------|-------------------|
| Qwen3-Coder-30B-A3B | `frontdoor` | baseline+spec, baseline+lookup, baseline+spec+lookup, moeN+spec, moeN+lookup, moeN+spec+lookup |
| Qwen3-235B-A22B | `architect_general` | baseline+spec, moeN+spec (no lookup — 133GB) |
| Qwen3-Coder-480B-A35B | `architect_coding` | baseline+spec, moeN+spec (no lookup — 271GB) |
| Qwen3-30B-A3B-Thinking Q8 | `thinking_qwen3_30b_a3b_thinking_2507` | baseline+spec, moeN+spec (no lookup — 30GB) |
| Qwen3-30B-A3B-Thinking Q4_K_S | `thinking_qwen3_30b_a3b_thinking_2507_q4ks` | baseline+spec, baseline+lookup, baseline+spec+lookup, moeN+spec, moeN+lookup, moeN+spec+lookup |
| Qwen3-Coder-30B-A3B | `coder_qwen3_coder_30b_a3b` | same model as frontdoor — results copied |

Models that forbid spec decode (MiniMax, GLM, SSM hybrids) are unaffected — they only get MoE reduction configs.

### 35B-A3B (baselines exist in run `20260303_170903`):
- Skip baselines (already done)
- Run on 3 slowest baseline questions: lookup, spec, moe+lookup, moe+spec, moe+spec+lookup at each expert count

### Dense-FFN hybrid models (27B, 9B, 4B, 2B):
- Full baseline quality tests (all suites)
- ~~Then on 3 slowest baseline questions: spec decode, lookup (if <20GB), spec+lookup~~ — NOT VIABLE: all Qwen3.5 are hybrid Delta Net, spec decode is net-negative

### MoE models (122B, 397B) — downloaded, pending benchmark:
- Full baseline + MoE reduction quality tests (all expert counts)
- Then on 3 slowest baseline questions at EACH expert count (including baseline):
  - baseline(N) + lookup, baseline(N) + spec, baseline(N) + spec+lookup
  - E.g. for 122B (baseline=8): test at experts=[4,6,8] × {lookup, spec, spec+lookup}

## Execution

```bash
cd /mnt/raid0/llm/epyc-inference-research
MODELS=(
  qwen35_q4km              # 35B - has baselines, needs speed tests
  qwen35_2b_q4km qwen35_2b_q6k qwen35_2b_q8
  qwen35_4b_q4km qwen35_4b_q6k qwen35_4b_q8
  qwen35_9b_q4km qwen35_9b_q6k qwen35_9b_q8
  qwen35_27b_q4km qwen35_27b_q6k
  qwen35_122b_q4km
  qwen35_397b_q4kxl
)
# Qwen3.5 sweep
for model in "${MODELS[@]}"; do
  python scripts/benchmark/run_benchmark.py \
    --model "$model" --speed-questions 3 --server-mode \
    --baseline-run 20260303_170903
done

# Non-Qwen3.5 MoE models (compound config gap)
MOE_MODELS=(
  frontdoor
  architect_general
  architect_coding
  thinking_qwen3_30b_a3b_thinking_2507
  thinking_qwen3_30b_a3b_thinking_2507_q4ks
)
for model in "${MOE_MODELS[@]}"; do
  python scripts/benchmark/run_benchmark.py \
    --model "$model" --speed-questions 3 --server-mode
done
```

## Verification

1. Dry run: `python run_benchmark.py --dry-run --model qwen35_2b_q4km`
2. Smoke test on 2B: `python run_benchmark.py --model qwen35_2b_q4km --suite general --speed-questions 3 --server-mode`
3. Run sweep model-by-model
4. Manual validation: 20-question seeding on best frontdoor candidate

## Review Table — All Qwen3.5 Models (2026-03-09)

Base t/s = MOE8 for 35B models (8 active experts is default). MOE8+LU = lookup at 8 experts, no spec.
Quality = Claude-as-Judge avg (0-3 scale, max_tokens=4096, 61q across 6 suites).
† = rescored with 2048-token completions, not directly comparable. ★ = highest quality variant.
‡ 397B: baseline = 10 experts (61Q complete), quality scored on 35/61 only (10 agentic unscored).

```
┌──────────────────────────────┬───────┬──────────┬─────┬─────────┬──────────────────────┬──────────┬───────┬────────────┬───────┐
│ Model                        │ Size  │ Base t/s │ #Q  │ Quality │ Best Accel Config    │ Best t/s │ Delta │ MOE8+LU    │ LU Δ  │
├──────────────────────────────┼───────┼──────────┼─────┼─────────┼──────────────────────┼──────────┼───────┼────────────┼───────┤
│ ─── 35B-A3B MoE Variants ─── │       │          │     │         │                      │          │       │            │       │
│ Q4_K_M (baseline)            │ 20 GB │ 13.8     │ 61  │ 2.48    │ moe6+lu_n5           │ 19.6     │ +42%  │ 14.1 (n3)  │  +2%  │
│   └─ MoE4                   │   —   │ 13.7     │ 61  │ 2.34    │ moe4+lu_n5           │ 18.8     │ +37%  │     —      │   —   │
│   └─ MoE6                   │   —   │ 14.0     │ 61  │ 2.23    │ moe6+lu_n5           │ 19.6     │ +40%  │     —      │   —   │
│ Q4_K_S                       │ 20 GB │ 13.9     │ 61  │ 2.33    │ moe8+spec+lu_k24     │ 15.3     │ +10%  │ 13.7 (n4)  │  -1%  │
│ ★ Q5_K_S                    │ 22 GB │ 12.5     │ 61  │ 2.66    │ moe8+spec+lu_k8      │ 14.4     │ +15%  │ 11.8 (n4)  │  -6%  │
│ Q6_K                         │ 26 GB │ 12.3     │ 61  │ 2.59    │ moe8+spec+lu_k16     │ 14.4     │ +17%  │ 14.1 (n4)  │ +15%  │
│ Q8_0                         │ 33 GB │ 11.4     │ 61  │ 2.44    │ moe8+spec+lu_k16     │ 13.4     │ +18%  │ 11.3 (n4)  │  -1%  │
├──────────────────────────────┼───────┼──────────┼─────┼─────────┼──────────────────────┼──────────┼───────┼────────────┼───────┤
│ ─── Large MoE ───            │       │          │     │         │                      │          │       │            │       │
│ 122B-A10B Q4_K_M             │ 69 GB │  9.2     │ 61  │ 2.57    │ moe8+spec_q8_k8+lu   │ 12.6     │ +37%  │ 11.5 (n4)  │ +25%  │
│ 397B-A17B Q4_K_XL            │205 GB │ 10.4     │ 61‡ │ 2.17    │ moe10+lu_n5          │ 13.5     │ +29%  │ 13.4 (n4)‡ │ +28%  │
├──────────────────────────────┼───────┼──────────┼─────┼─────────┼──────────────────────┼──────────┼───────┼────────────┼───────┤
│ ─── Dense 27B ───            │       │          │     │         │                      │          │       │            │       │
│ 27B Q6_K                     │ 21 GB │  9.4     │ 61  │ 2.54    │ spec_k16             │ 13.6     │ +45%  │     —      │   —   │
│ 27B Q4_K_M                   │ 16 GB │  8.8     │ 61  │ 2.38    │ spec_k32             │ 13.4     │ +53%  │     —      │   —   │
├──────────────────────────────┼───────┼──────────┼─────┼─────────┼──────────────────────┼──────────┼───────┼────────────┼───────┤
│ ─── Dense 9B ───             │       │          │     │         │                      │          │       │            │       │
│ 9B Q8_0                      │ 10 GB │ 12.7     │ 60  │ 2.41    │ spec+lu_k16          │ 17.7     │ +39%  │     —      │   —   │
│ 9B Q4_K_M                    │  6 GB │ 14.5     │ 61  │ 2.25    │ lu_n5                │ 25.1     │ +73%  │     —      │   —   │
│ 9B Q6_K                      │  7 GB │ 13.4     │ 61  │ 2.13    │ lu_n5                │ 20.7     │ +54%  │     —      │   —   │
├──────────────────────────────┼───────┼──────────┼─────┼─────────┼──────────────────────┼──────────┼───────┼────────────┼───────┤
│ ─── Dense 4B (Worker) ───    │       │          │     │         │                      │          │       │            │       │
│ 4B Q6_K                      │  4 GB │ 16.4     │ 61  │ 2.31    │ lu_n5                │ 16.1     │  -2%  │     —      │   —   │
│ 4B Q8_0                      │  5 GB │ 15.2     │ 61  │ 2.30    │ lu_n5                │ 22.7     │ +49%  │     —      │   —   │
│ 4B Q4_K_M                    │  3 GB │ 16.2     │ 61  │ 2.20    │ lu_n5                │ 16.3     │  +1%  │     —      │   —   │
├──────────────────────────────┼───────┼──────────┼─────┼─────────┼──────────────────────┼──────────┼───────┼────────────┼───────┤
│ ─── Dense 2B (Worker) ───    │       │          │     │         │                      │          │       │            │       │
│ 2B Q4_K_M                    │1.5 GB │ 28.7     │ 61  │ 1.95    │ lu_n5                │ 65.8     │+129%  │     —      │   —   │
│ 2B Q6_K                      │  2 GB │ 30.2     │ 60  │ 1.67    │ lu_n4                │ 57.4     │ +90%  │     —      │   —   │
│ 2B Q8_0                      │  2 GB │ 27.0     │ 60  │ 1.82    │ lu_n4                │ 47.8     │ +77%  │     —      │   —   │
├──────────────────────────────┼───────┼──────────┼─────┼─────────┼──────────────────────┼──────────┼───────┼────────────┼───────┤
│ ─── Production (comparison)── │       │          │     │         │                      │          │       │            │       │
│ Qwen3-Coder-30B-A3B †       │ 17 GB │ 27.1     │ 61  │ 1.90†   │ moe4+spec+lu_k24     │ 45.3     │ +67%  │     —      │   —   │
│ Qwen3-235B-A22B †           │133 GB │  9.1     │ 61  │ 1.82†   │ moe8+spec_1.7b_k24   │ 13.7     │ +50%  │     —      │   —   │
│ Qwen3-Coder-480B-A35B †     │271 GB │  6.5     │ 35  │ 2.19†   │ moe8+spec_k24        │ 13.6     │+108%  │     —      │   —   │
└──────────────────────────────┴───────┴──────────┴─────┴─────────┴──────────────────────┴──────────┴───────┴────────────┴───────┘
```

### MOE8+LU Key Takeaways

- **Q6_K gets +15% from lookup alone** (12.3 → 14.1 t/s) — best lookup response among 35B variants
- **122B gets +25% from lookup alone** (9.2 → 11.5 t/s) — largest absolute gain, competitive with 35B
- **Q5_K_S loses -6% with lookup** — lookup n-gram cache may conflict with SSM prediction patterns
- **Q4_K_M gets only +2%** from lookup at full experts — MoE reduction (moe6+lu) is far better (+42%)
- For most variants, **spec+lookup compound beats lookup-only** by 10-20%

## Official Qwen3.5 Benchmark Comparison (from HuggingFace model cards)

```
┌──────────────────────────┬───────────┬──────┬───────────────┬──────────┬────────┬───────────┐
│ Model                    │ MMLU-Pro  │ GPQA │ LiveCodeBench │ HMMT Feb │ IFEval │ SWE-bench │
├──────────────────────────┼───────────┼──────┼───────────────┼──────────┼────────┼───────────┤
│ Qwen3-30B-A3B (prod FD)  │ 78.4      │ 70.4 │      —        │    —     │   —    │     —     │
│ Qwen3.5-2B               │ 66.5      │ 51.6 │      —        │    —     │   —    │     —     │
│ Qwen3.5-9B               │ 82.5      │ 81.7 │     65.6      │   83.2   │  91.5  │     —     │
│ Qwen3.5-35B-A3B          │ 85.3      │ 84.2 │     79.9      │   94.1   │   —    │     —     │
│ Qwen3.5-397B-A17B        │ 87.8      │ 88.4 │     83.6      │   94.8   │  92.6  │    76.4   │
└──────────────────────────┴───────────┴──────┴───────────────┴──────────┴────────┴───────────┘
```

### Official vs Our Scoring

- **397B is a powerhouse** officially (MMLU-Pro 87.8, GPQA 88.4, SWE-bench 76.4) but scores only 60% on our bench with 35 partial questions. Think-block truncation at 4096 tokens and missing agentic suite are likely causes.
- **9B officially outperforms Qwen3-30B-A3B** on MMLU-Pro (82.5 vs 78.4) and GPQA (81.7 vs 70.4), validating SSM architecture improvements.
- **35B-A3B is a massive jump** from Qwen3-30B-A3B across all official metrics (+7pp MMLU-Pro, +14pp GPQA).
- Our Claude-as-Judge scoring shows production frontdoor (Qwen3-30B-A3B) at 1.90/3.0 rescored — any Qwen3.5 model ≥9B significantly outperforms it.

## RESULTS.md Full Rescore (2026-03-09)

All production model entries in RESULTS.md corrected from lazy-scoring-inflated values to `_rescored.csv` values (2048-token completions). Qwen3.5 models scored fresh with 4096-token completions.

| Model | Quality (rescored) |
|-------|--------------------|
| Qwen3-Coder-30B-A3B baseline | 69%† |
| Qwen3-Coder-30B-A3B MoE4 | 62%† |
| Qwen3-Coder-30B-A3B MoE6 | 68%† |
| Qwen3-235B-A22B baseline | 64%† |
| Qwen3-235B-A22B MoE2 | 2%† |
| Qwen3-235B-A22B MoE4 | 54%† |
| Qwen3-235B-A22B MoE6 | 55%† |
| Qwen3-Coder-480B baseline | 80%† |
| Qwen3-Coder-480B MoE4 | 77%† |
| Qwen3-Coder-480B MoE6 | 84%† |
| Meta-Llama-3.1-70B | 61%† |
| Hermes-4-70B | 67%† |
| Qwen2.5-72B | 70%† |
| DeepSeek-R1-Distill-Llama-70B | 26%† |
| DeepSeek-R1-Distill-Llama-8B | 45%† |

## TPS Statistics (Median vs Mean) — 2026-03-09

Accel configs were tested on 2-4 slowest baseline questions only (small sample).

```
┌─────────────────────┬──────────────┬────────────────────┬──────────────┬────────────────────┐
│ Model               │ Base Median  │ Base Mean±SD       │ Accel Median │ Accel Mean±SD      │
├─────────────────────┼──────────────┼────────────────────┼──────────────┼────────────────────┤
│ ═══ FRONTDOOR CANDIDATES ═══                                                                │
│ frontdoor (30B-A3B) │ 34.8         │ 27.1 ± 14.6        │ 41.8         │ 45.3 ± 33.5 (n=3)  │
│ qwen35 Q5_K_S       │ 13.3         │ 12.5 ±  2.0        │ 13.4         │ 14.4 ±  2.0 (n=3)  │
│ qwen35 Q4_K_M       │ 13.5         │ 13.8 ±  2.0        │ 17.4         │ 19.6 ±  6.4 (n=3)  │
├─────────────────────┼──────────────┼────────────────────┼──────────────┼────────────────────┤
│ ═══ ARCHITECT CANDIDATES ═══                                                                │
│ architect_general   │  5.8         │  9.1 ±  4.0        │  6.8         │  7.0 ±  2.2 (n=3)  │
│ qwen35_122b         │  5.0         │  9.2 ±  5.3        │ 13.6         │ 12.6 ±  1.7 (n=3)  │
│ qwen35_397b         │ 13.3         │ 10.4 ±  5.1        │ 13.5         │ 13.5 ±  0.0 (n=3)  │
├─────────────────────┼──────────────┼────────────────────┼──────────────┼────────────────────┤
│ ═══ WORKER CANDIDATES ═══                                                                   │
│ qwen35_9b_q4km      │ 14.8         │ 14.5 ±  1.2        │ 25.2         │ 25.1 ±  1.5 (n=3)  │
│ qwen35_4b_q8        │ 14.4         │ 15.2 ±  3.2        │ 24.9         │ 22.7 ±  6.8 (n=4)  │
│ qwen35_2b_q4km      │ 25.0         │ 28.7 ± 15.7        │ 67.0         │ 65.8 ± 12.2 (n=4)  │
└─────────────────────┴──────────────┴────────────────────┴──────────────┴────────────────────┘
```

Key observations:
- **Frontdoor median (34.8) >> mean (27.1)**: A few long-thinking questions drag mean down. Median better represents interactive latency.
- **122B and architect_general have bimodal distributions**: Low medians (5.0, 5.8) with means nearly double — some questions run fast, others very slow.
- **397B baseline is consistent**: Median 13.3, accel median 13.5 with near-zero variance on 3 questions.
- **35B MoE quant variants cluster at ~13 t/s median**: Quantization has minimal speed impact for MoE (bottleneck is active-parameter bandwidth).

## Orchestrator Stack Recommendations — 2026-03-09

### Recommended Swaps

| Role | Current Model | Proposed Model | Quality Δ | Speed Δ | RAM Δ |
|------|---------------|----------------|-----------|---------|-------|
| architect_general | Qwen3-235B-A22B (1.82/3, 13.7 t/s) | **Qwen3.5-122B-A10B** (2.57/3, 12.6 t/s) | +0.75 (+25pp) | -1.1 t/s | **-64 GB** |
| worker_general | Meta-Llama-3-8B (1.83/3, 37.1 t/s) | **Qwen3.5-4B Q8_0** (2.30/3, 22.7 t/s) | +0.47 (+16pp) | -14.4 t/s | same |

### Under Consideration

| Role | Current Model | Candidate | Quality Δ | Speed Δ | Notes |
|------|---------------|-----------|-----------|---------|-------|
| frontdoor | Qwen3-Coder-30B-A3B (1.90/3, 45.3 t/s) | Qwen3.5-35B-A3B Q5_K_S (2.66/3, 13.4 t/s median) | +0.76 (+25pp) | -28.4 t/s median | Q5_K_S is abliterated (uncensored). Huge quality gain but 2.6x slower. Test moe6+lookup on Q5_K_S to close speed gap. |
| frontdoor | Qwen3-Coder-30B-A3B | Qwen3.5-35B-A3B Q4_K_M (2.48/3, 17.4 t/s median) | +0.58 (+19pp) | -17.4 t/s median | Middle ground: 83% quality, better accel response than Q5_K_S |
| architect_general | Qwen3-235B-A22B | Qwen3.5-397B-A17B (2.17‡/3, 13.5 t/s) | +0.35‡ | -0.2 t/s | +136GB RAM. Quality TBD (10 agentic questions unscored). Public benchmarks: MMLU-Pro 87.8, TAU2 86.7 |

### Keep (No Change)

| Role | Current Model | Reason |
|------|---------------|--------|
| architect_coding | Qwen3-Coder-480B-A35B | Purpose-built coder, 2.19/3 quality, 13.6 t/s. No Qwen3.5 match. |
| coder_escalation | Qwen2.5-Coder-32B | 2.79/3 quality @ 39.4 t/s — nothing competes. |
| worker_explore | Qwen2.5-7B | 2.70/3 @ 46.6 t/s with spec decode — hard to beat. |
| ingest_long_context | Qwen3-Next-80B-A3B | SSM architecture for 128K+ context. RULER 91.8% avg to 1M tokens. |

### Analysis Details

**architect_general → 122B (clear win)**:
- Public benchmarks: 122B beats 235B on MMLU-Pro (+2.3), GPQA (+5.5), TAU2-Bench (+21.0), BFCL-V4 (+17.4)
- Our benchmark: 2.57 vs 1.82 quality, similar speed (12.6 vs 13.7 t/s), half the RAM
- The agent/tool-use gap (TAU2 +21pp) is especially relevant for an architect role

**397B as alternative architect_general**:
- Public benchmarks dominate: MMLU-Pro 87.8, LiveCodeBench 83.6, SWE-bench 76.4
- Our quality: 2.17 on 35/61 scored (10 agentic questions pending). Likely to improve.
- Speed: 13.5 t/s with moe10+lookup — competitive with 122B (12.6 t/s)
- Cost: +136GB RAM (205GB vs 69GB). Worth it if quality comes in strong on remaining scoring.

**worker_general → 4B Q8_0**:
- Quality 2.30 vs 1.83 (+16pp), good for 'cheap answer first' policy
- Speed 22.7 vs 37.1 t/s — slower but still fast enough for a worker
- 4B Q6_K alternative: same quality (2.31) at 16.4 t/s, only 4GB

**frontdoor — the big question**:
- Q5_K_S: 89% quality, Rademacher abliterated (uncensored), but only 13.4 t/s median with best accel (+1% over baseline)
- Q4_K_M: 83% quality, 17.4 t/s median with moe6+lookup (+30% over baseline)
- Current: 63% quality but 34.8 t/s median baseline, 41.8 t/s accel
- **Gap to close**: Q5_K_S needs a better accel config. Test moe6+lookup (what works for Q4_K_M) on Q5_K_S.
- **Scoring comparability caveat**: Production models scored with 2048-token budget, Qwen3.5 with 4096. Re-scoring production at 4096 would give fairer comparison.

### Public Benchmark Context

All official Qwen3.5 benchmarks are BF16 (native precision). No public task-specific accuracy data exists per GGUF quant variant — only KL divergence/perplexity from Unsloth. Our benchmarks are the most granular quant-variant comparison available for Qwen3.5.

Qwen3.5 is robust to quantization (Unsloth/Benjamin Marie confirmed). Our data shows Q5_K_S > Q6_K > Q4_K_M > Q8_0 > Q4_K_S — the Q8_0 < Q5_K_S ordering likely reflects think-block truncation (more verbose reasoning in higher quants exhausts 4096-token budget).

## Open Items

- [ ] Score 397B agentic suite (10 questions with TPS data, 0 quality-scored)
- [ ] Test moe6+lookup on Q5_K_S (may close speed gap with Q4_K_M)
- [ ] Re-score production models with 4096-token budget for fair comparison
- [x] Execute swap: architect_general → Qwen3.5-122B-A10B Q4_K_M (deployed 2026-03-19, moe8+spec_q8_k8+lookup)
- [x] Execute swap: frontdoor → Qwen3.5-35B-A3B Q4_K_M (deployed 2026-03-19, moe6+lookup, 4×48t NUMA)
- [ ] Execute swap: worker_general → Qwen3.5-4B Q8_0 (pending traffic analysis)
- [ ] A/B test frontdoor with live traffic (Qwen3.5-35B now deployed)

## Closeout

- [x] Phase 1 complete: 35B multi-quant sweep done, frontdoor rescored
- [x] Code changes: `results.py` — `get_slowest_questions()`
- [x] Code changes: `run_benchmark.py` — `_run_speed_question()`, `--speed-questions`, `--baseline-run`
- [x] Code changes: `run_benchmark.py` — temperature override application
- [x] Code changes: `registry.py` — `get_temperature_override()` helper
- [x] Code changes: `executor.py` — `moe_spec_lookup` compound config + compound loop fix
- [x] Code changes: `executor.py` — `ServerManager.start()` lookup parameter
- [x] Registry entries added for dense models (2B, 4B, 9B, 27B) — 11 roles
- [x] Registry entries added for MoE models (122B, 397B) — 2 roles (not yet downloaded)
- [x] Draft model compatible_targets updated (added qwen3.5-27b, qwen3.5-9b)
- [x] ~~New draft `draft_qwen35_2b_q4km`~~ REMOVED (2B too slow as draft on CPU)
- [x] Temperature overrides added to all 18 Qwen3.5 roles
- [x] Dry run passes for all targets
- [x] Dense model baselines complete (2B, 4B, 9B, 27B — 60-61q each, 6 suites)
- [x] Dense model speed configs complete (lookup, spec, spec+lookup)
- [x] 35B Q4KM rescored with max_tokens=4096 (baseline 83%, MoE4 78%, MoE6 74%)
- [x] Master benchmark table (RESULTS.md) updated with all Qwen3.5 entries
- [x] candidate_roles fixed for 2B/4B models (worker → frontdoor/worker/coder/general)
- [x] --with-lookup CLI flag added to run_benchmark.py
- [x] Timeout constants boosted (multiplier 3→10, buffer 120→300)
- [x] Full quality scoring for all dense models (2B/4B/9B/27B all 61/61)
- [x] Quality scoring for 27B Q6K (61/61, avg 2.54 — best Qwen3.5 quality)
- [x] Quality scoring for 9B Q6K (61/61, avg 2.13)
- [x] Fixed 122B/397B registry (paths, removed "NOT YET DOWNLOADED")
- [x] Restored 35B variant review CSVs from git (Q6K/Q8_0 baseline + all MoE rescored)
- [x] Added `--skip-moe-reduction` CLI flag
- [x] Removed lookup model size threshold (was blocking Q4KS/Q5KS/Q6K/Q8_0)
- [x] Q4KS re-benchmarked and scored (61q, 2.33, baseline 13.9 t/s)
- [x] 35B Q5KS scored (61q, avg 2.66 — highest 35B quality)
- [x] 35B Q6K re-benchmarked and scored (61q, 2.59, baseline 12.3 t/s)
- [x] 35B Q8_0 re-benchmarked and scored (61q, 2.44, baseline 11.4 t/s)
- [x] 122B Q4_K_M benchmarked and scored (61q, 2.57, baseline 9.2 t/s)
- [x] 397B Q4_K_XL partially benchmarked (35q, 2.17, baseline 10.4 t/s)
- [x] RESULTS.md updated with all fresh Qwen3.5 entries + 122B/397B
- [x] RESULTS.md fully rescored (all production models corrected from lazy-scoring inflation)
- [x] Review table with MOE8+LU column saved to handoff
- [x] Official Qwen3.5 benchmark comparison table saved to handoff
- [ ] Update `model_registry.yaml` with measured performance fields
- [ ] 397B agentic quality scoring (10 questions unscored)
- [ ] Test moe6+lookup on Q5_K_S
- [ ] Re-score production models with 4096-token budget
- [x] TPS statistics (median/mean/SD) computed for all models
- [x] Stack swap recommendations documented
- [x] Public benchmark comparison integrated
- [x] Execute stack swaps: architect_general → 122B DONE, frontdoor → Qwen3.5-35B-A3B Q4_K_M DONE (2026-03-19)
- [ ] Execute worker_general swap → Qwen3.5-4B Q8_0 (pending traffic analysis)
- [ ] A/B test frontdoor candidates (Qwen3.5-35B now deployed, needs live validation)
- [ ] Move handoff to `completed/`
