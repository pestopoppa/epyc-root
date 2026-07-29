# Progress — 2026-04-22 (Kernel Push)

## Session: llama.cpp Kernel Push + TIDE Implementation (2026-04-20 → 2026-04-22)

Major multi-day session spanning rebase, cherry-picks, reasoning mode fix, TIDE early-exit infrastructure, and calibration tooling.

### Rebase & Cherry-Picks

- Emergency cherry-picks on v3: 4 commits (56666fa60, ddf03c6d9, d7ff074c8, 3fc65063d) fixing Qwen3.6 think-loops
- Qwen3.6 quality retest: 16/16 previously-failing questions now PASS
- Full rebase: production-consolidated-v4 created from upstream HEAD (81df3f7cf)
- 33 commits on upstream, pushed to fork remote
- `--lookup` flag retired (upstream `--spec-type ngram-simple` supersedes)
- Tree speculation DySpec re-ported to upstream's refactored speculative framework
- DiffTransformer V2 adapted to upstream's `build_attn` API change (`wo_s` param)

### Reasoning Mode Fix

- Root cause identified: cherry-pick 56666fa60 removes budget sampler, model never emits `</think>`
- Fix: `--reasoning-budget 4096` forces `</think>` after N tokens
- Validated: model produces `reasoning_content` + `content` with `finish_reason: stop`
- Wired into `executor.py` and model registry

### TIDE Implementation

- `n_layer_exit` infrastructure added to `llama_context` (public API + CLI flag)
- Graph builder early termination in `qwen35moe`, `gemma4-iswa`, `minimax-m2`
- Critical bug found and fixed: ggml graph cache silently reused old graph when `n_layer_exit` changed (`sched_need_reserve = true`)
- `server-tide.h`: router MLP evaluator + adaptive exit logic with hysteresis
- C++ calibration tool (`tools/tide-calibrate/`) with two modes:
  - **Full-states**: dumps raw hidden states per checkpoint (for Qwen3.6, 84GB)
  - **Single-pass callback**: captures `l_out` tensors via `cb_eval` in ONE forward pass (36x faster)
- Critical callback bug: return `false` from data phase aborts graph execution. Fixed to return `true`.
- Calibration completed: Qwen3.6 (1000 samples, 23 min), SG4-31b (running), M2.7 (queued)

### Gemma4 Retest

- 2/7 previously-failing questions now pass on SG4-31b
- Remaining 5 failures are model-level repetition collapse (google-deepmind/gemma#622), not template issues

### Key Metrics

| Metric | Before | After |
|--------|--------|-------|
| Qwen3.6 quality | 0% pass | 16/16 pass (chat template fix) |
| Qwen3.6 reasoning | infinite loops | bounded reasoning with `--reasoning-budget 4096` |
| TIDE early exit | no dynamic exit | validated 30/40 layers = +7% on MoE (projected +15-25% with router) |
| Calibration speed | 0.046 samples/s (pairwise) | 0.72 samples/s (single-pass callback) = 16x improvement |
| Tree spec | broken on upstream refactor | re-ported to upstream's refactored framework, builds clean |

### Branch State

| Branch | Status |
|--------|--------|
| `production-consolidated-v3` | current production (with 4 cherry-picks) |
| `production-consolidated-v4` | 33 commits on upstream, pushed to fork, TIDE-ready |

## Update: TIDE Projection Results (2026-04-23)

### Speed Validation
- **Critical bug found and fixed**: `n_layer_exit` was never wired from `common_params` to `llama_context_params` in `common.cpp`. All previous speed tests ran all layers. 
- After fix: graph nodes 3657 → 1832 (50% reduction at layer 32/64)
- **Qwen3.6-27B at layer 32/64: 8.4 t/s vs 4.8 baseline = 1.76x speedup**
- Qwen3-1.7B at layer 7/28: coherent output with projection (proved concept on small model)

### Projection Quality
- Linear projection (5120×5120 = 105 MB) maps layer-L hidden state → output_norm space
- cos=1.0 on calibration data (synthetic text) for all exit layers and all models
- On unseen prompts: produces garbage at layer 32/64 — projection doesn't generalize beyond calibration distribution
- Qwen3.6-35B MoE: partially coherent but language mixing artifacts
- RMSNorm per-exit (element-wise): FAILS — can't rotate, only scale (cos=0.45)

### Key Findings
1. **Speed: CONFIRMED** — n_layer_exit produces real 1.76x speedup at 50% layers
2. **Quality: UNSOLVED** — linear projection doesn't generalize to unseen prompts
3. **Next steps**: Fine-tune LM head adapter per exit layer, or try bottleneck adapter (5120→256→5120)

### Models Downloaded
- Qwen3.6-27B-Q8_0.gguf (26.6 GB) — downloaded, calibrated
- Qwen3.6-27B-Q4_K_M.gguf (15.7 GB) — downloaded, not yet calibrated

### Calibration Data Collected
- Qwen3.6-35B-A3B Q8_0: 1000 samples (callback, 23 min)
- SG4-31b Q4_K_M: 1000 samples (callback, 68 min)
- M2.7 Q8_0: 1000 samples (callback, 59 min)
- Qwen3.6-27B Q8_0: 500 samples with l_out + result_norm (callback, 7 min)
- Qwen3-1.7B Q8_0: 5000 samples with l_out + result_norm (callback, 5.4 min)
