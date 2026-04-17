# Doc-to-LoRA Prototype

**Status**: ⚠️ QUEUED FOR ARCHIVE (2026-04-17 audit — 31d stale, use case "largely solved by existing tooling", Phase B blocked on cloud GPU). Findings 1-8 retained as reference. Move `active/` → `archived/` pending directory permissions fix.
**Created**: 2026-03-03
**Revised**: 2026-03-17 (added QVAC Fabric/BitNet research context, Finding 8, Phase A-bis)
**Priority**: P3 — low priority, high-effort experimental
**Effort**: High
**Source**: [Doc-to-LoRA paper (arxiv.org/pdf/2602.15902)](https://arxiv.org/pdf/2602.15902) | [Paper Breakdown](https://paperbreakdown.com/abs/2602.15902)

**Hardware constraint**: AMD EPYC 9655 (192 threads), GT 1030 (2 GB display-only). **No training-capable GPUs.** All Phase A validation runs on CPU. Hypernetwork retraining requires cloud GPU rental (Phase B).

## Relevance Assessment

### What the orchestrator already has
REPL workers solve the "large reference material" problem via tool-augmented retrieval: `peek()`, `file_read_safe()`, `web_search`, `web_research`. Workers pull context on demand rather than needing it pre-loaded. The REPL token cap issue (768 → 5000) was about output truncation, not input context pressure.

### Where Doc-to-LoRA could still add value
The remaining value proposition is narrow:
- **Latency on repeated lookups**: An adapter eliminates tool round-trips (fetch, read, synthesis) for knowledge already in the weights. Marginal gain given workers already run 15+ turns.
- **Small model compensation**: Pre-baked domain knowledge for `worker_fast` (1.5B) where the model is too small to reason well from retrieved context. An adapter might compensate. Speculative until benchmarked.
- **Persistent domain specialization**: Pre-generate adapters offline for static reference docs (stdlib, framework APIs, codebase modules). Load at startup, route by domain. No per-request generation cost.

### Why low priority
The core use case (avoiding context-stuffing for reference material) is largely solved by existing tooling. This handoff is preserved as reference material — the research findings (LoRA API surface, checkpoint availability, format conversion requirements, architecture constraints) are valuable if the need arises.

## Research Review

### Doc-to-LoRA: Instantly Internalizing Contexts
**Authors:** Rujikorn Charakorn, Edoardo Cetin, Shinnosuke Uesaka, Robert Tjarko Lange (Sakana AI)
**Code:** [github.com/SakanaAI/doc-to-lora](https://github.com/SakanaAI/doc-to-lora)

Hypernetwork that takes a document as input and generates LoRA adapter weights, enabling a model to "internalize" context without in-context learning or fine-tuning. Generates both adapter weights and scaling factors. Validated on SQuAD, DROP, ROPES, LongBench. Faster inference than context-based methods since the context is baked into weights.

## Critical Findings (Audit)

### Finding 1: llama.cpp LoRA hot-swap is ALREADY IMPLEMENTED

Our `production-consolidated-v2` branch has full LoRA API support:

| Capability | API | File |
|---|---|---|
| Load adapters at startup | `--lora PATH.gguf`, `--lora-scaled PATH:SCALE` | `common/arg.cpp:2496` |
| Load without activating | `--lora-init-without-apply` | `common/arg.cpp:3117` |
| List loaded adapters | `GET /lora-adapters` | `tools/server/server.cpp:196` |
| Set adapter scales globally | `POST /lora-adapters` with `[{"id":N,"scale":F}]` | `tools/server/server.cpp:197` |
| Per-request adapter override | `"lora":[{"id":0,"scale":1.0}]` in completion payload | `tools/server/server-task.cpp:270` |
| aLoRA (auto-activate on token) | Custom branch feature | `server-context.cpp:1097` |
| Intelligent cache clearing | Only clears KV cache when switching non-aLoRA adapters | `server-common.cpp:104-128` |

Existing test fixture: `tools/server/tests/unit/test_lora.py` uses `ggml-org/stories15M_MOE` LoRA from HuggingFace.

### Finding 2: Pretrained checkpoints exist for THREE model families

HuggingFace repo `SakanaAI/doc-to-lora` (6.5 GB total) contains:

| Checkpoint | Base Model | Steps | Gated? |
|---|---|---|---|
| `gemma_2b_d2l` | `google/gemma-2-2b-it` | 80,000 | Yes (Google auth) |
| `gemma_demo` | `google/gemma-2-2b-it` | 80,000 | Yes |
| `qwen_4b_d2l` | **`Qwen/Qwen3-4B-Instruct-2507`** | 20,000 | **No** |
| `mistral_7b_d2l` | **`mistralai/Mistral-7B-Instruct-v0.2`** | 20,000 | **No** |

**Qwen3-4B is the best validation target**: public (no auth), Qwen architecture family, smallest footprint (~1.68 GB checkpoint).

All checkpoints share identical hypernetwork architecture:
- 9-block Perceiver aggregator, 8 latent queries, 512 latent dim
- LoRA rank 8, targets `down_proj` only
- KL distillation loss + NEFTune noise (alpha=5.0)
- Qwen/Mistral checkpoints bootstrapped from the Gemma-80K checkpoint + 20K more steps

### Finding 3: D2L adapter format is NOT PEFT-compatible — custom conversion required

**D2L output format** (after `model.internalize(doc)`):
```python
model.generated_loras = {
    "down_proj": {
        "A": Tensor[1, n_layers, rank, d_in],    # e.g., [1, 36, 8, 9728] for Qwen3-4B
        "B": Tensor[1, n_layers, rank, d_out],    # e.g., [1, 36, 8, 2560] for Qwen3-4B
    }
}
```
After multi-chunk `combine_lora()`: effective rank = `(n_chunks + 1) * 8`.

**`convert_lora_to_gguf.py` expects** PEFT format:
- `adapter_config.json` with `lora_alpha`, `base_model_name_or_path`
- `adapter_model.safetensors` with keys like `base_model.model.model.layers.{n}.mlp.down_proj.lora_A.weight` (shape `[rank, d_in]`) and `.lora_B.weight` (shape `[d_out, rank]`)

**Conversion gap**: D2L stores B as `[rank, d_out]`; PEFT expects `[d_out, rank]` (transposed). D2L stores all layers in a single `[n_layers, rank, dim]` tensor; PEFT expects separate per-layer files. A custom `d2l_to_peft.py` bridge script is needed.

### Finding 4: CPU inference needs exactly 1 code patch

Minimal dependencies (no vllm, no DeepSpeed): `torch, transformers, peft, einops, jaxtyping, opt-einsum`

Required patch — `HyperLoRA.forward()` in `src/ctx_to_lora/modeling/hypernet.py`:
```python
# BREAKS on CPU:
with torch.autocast(device_type="cuda", dtype=torch.bfloat16):
    ...
# FIX:
device_type = "cuda" if next(self.parameters()).is_cuda else "cpu"
with torch.autocast(device_type=device_type, dtype=torch.bfloat16 if device_type == "cuda" else torch.float32):
    ...
```

Memory estimate for Qwen3-4B on CPU: ~8 GB (base) + ~1.68 GB (hypernetwork) + ~0.5 GB (working) ≈ **~10 GB RAM**.

### Finding 5: Qwen3-4B is NOT compatible with our production Qwen2.5 models

| Param | Qwen3-4B | Qwen2.5-7B (our worker) | Qwen2.5-Coder-1.5B (worker_fast) |
|---|---|---|---|
| `model_type` | `qwen3` | `qwen2` | `qwen2` |
| `hidden_size` | 2560 | 3584 | 1536 |
| `num_hidden_layers` | 36 | 28 | 28 |
| `intermediate_size` | 9728 | 18944 | 8960 |

A hypernetwork trained on Qwen3-4B **cannot** generate adapters for Qwen2.5 models — tensor shapes are fundamentally different. Production integration requires retraining (Phase B).

### Finding 6: No Qwen3-4B-Instruct GGUF exists locally

- **Available locally**: `Qwen3-4B-Thinking-2507-Q8_0.gguf` (fine-tuned variant)
- **Available upstream**: `Qwen/Qwen3-4B-GGUF` on HuggingFace (Q4_K_M = 2.5 GB, Q8_0 = 4.28 GB)
- **Conversion ready**: `convert_hf_to_gguf.py` has `Qwen3ForCausalLM` registered at line 4376

### Finding 7: Zero LoRA infrastructure in orchestrator

No `--lora` in `build_server_command()`, no `lora_path` in `ModelConfig`, no `"lora"` field in `_build_payload()`. Full integration is Phase B scope.

### Finding 8: llama.cpp training infrastructure — gap analysis vs QVAC Fabric

Our fork has `llama_opt_init()`, `llama_opt_epoch()` (`include/llama.h:1592-1620`) and working `examples/training/finetune.cpp`.

| Capability | Status | Details |
|---|---|---|
| Training API | Present | `llama_opt_init()`, `llama_opt_epoch()` in `include/llama.h` |
| Backward ops | Present | SILU_BACK, RMS_NORM_BACK, ROPE_BACK, OUT_PROD, OPT_STEP_ADAM (CUDA), CROSS_ENTROPY_LOSS_BACK |
| Masked loss | **Missing** | No `CROSS_ENTROPY_LOSS_MASKED` (QVAC adds this for assistant-only token loss). Workaround: mask at dataset level |
| Training precision | Constrained | F32 KV cache required — no F16 for OUT_PROD |
| BitNet LoRA compat | Structural | `bitnet.cpp` uses `build_lora_mm` at 6 call sites — LoRA adapters structurally compatible with BitNet inference |

**Conclusion**: CPU LoRA fine-tuning already possible via `finetune.cpp` for supported models. Masked loss is a convenience gap, not a blocker. QVAC's Vulkan/Metal GPU kernels are NOT APPLICABLE (GT 1030 display-only, no Vulkan compute).

Reference files:
- `/mnt/raid0/llm/llama.cpp/include/llama.h` (lines 1592-1620)
- `/mnt/raid0/llm/llama.cpp/examples/training/finetune.cpp`
- `/mnt/raid0/llm/llama.cpp/src/models/bitnet.cpp`

## References

- [Doc-to-LoRA paper](https://arxiv.org/pdf/2602.15902)
- [Paper Breakdown](https://paperbreakdown.com/abs/2602.15902)
- [Sakana AI repo](https://github.com/SakanaAI/doc-to-lora)
- [SakanaAI/doc-to-lora HuggingFace](https://huggingface.co/SakanaAI/doc-to-lora) — pretrained checkpoints
- llama.cpp LoRA API: `tools/server/server.cpp:196-197`, `tools/server/server-task.cpp:270`
- llama.cpp LoRA test: `tools/server/tests/unit/test_lora.py`
- llama.cpp LoRA converter: `convert_lora_to_gguf.py`
- PEFT tensor naming: `base_model.model.model.layers.{n}.mlp.down_proj.lora_{A,B}.weight`
- Worker token caps: `_repl_turn_token_cap()` in `src/graph/helpers.py`
- QVAC Fabric repo: [github.com/tetherto/qvac-fabric-llm.cpp](https://github.com/tetherto/qvac-fabric-llm.cpp) (Apache 2.0)
- QVAC BitNet blog: [huggingface.co/blog/qvac/fabric-llm-finetune-bitnet](https://huggingface.co/blog/qvac/fabric-llm-finetune-bitnet)
- BitNet 2B4T paper: [arxiv.org/abs/2504.12285](https://arxiv.org/abs/2504.12285) (MIT)
- BitNet 2B4T model: [huggingface.co/microsoft/bitnet-b1.58-2B-4T](https://huggingface.co/microsoft/bitnet-b1.58-2B-4T)
- llama.cpp training API: `include/llama.h:1592-1620`, `examples/training/finetune.cpp`

## Implementation Steps (Phase A — CPU Validation)

### Step 1: Smoke-test llama.cpp LoRA hot-swap (1-2 hours)

**Where**: `/mnt/raid0/llm/llama.cpp`
**Runs on**: CPU
**Purpose**: Confirm the LoRA API works end-to-end before investing in D2L

**Procedure**:
1. Download test LoRA + base model from existing test fixture URLs (see `tools/server/tests/unit/test_lora.py`)
2. Launch llama-server with `--lora-init-without-apply`
3. Test API surface:
   ```bash
   # List adapters (should show scale 0)
   curl http://localhost:9999/lora-adapters

   # Baseline completion (no LoRA)
   curl -X POST http://localhost:9999/completion -d '{"prompt":"Once upon a time","n_predict":50}'

   # Per-request LoRA activation
   curl -X POST http://localhost:9999/completion -d '{"prompt":"Once upon a time","n_predict":50,"lora":[{"id":0,"scale":1.0}]}'

   # Global scale change + deactivate
   curl -X POST http://localhost:9999/lora-adapters -d '[{"id":0,"scale":0.5}]'
   curl -X POST http://localhost:9999/lora-adapters -d '[{"id":0,"scale":0.0}]'
   ```
4. Measure: response time delta with LoRA on/off, memory delta (`/proc/PID/status` VmRSS)

**Acceptance**: All API calls work. Documented latency and memory numbers.

---

### Step 2: Clone and validate Doc-to-LoRA with Qwen3-4B on CPU (1-2 days)

**Where**: `/mnt/raid0/llm/doc-to-lora` (new clone)
**Runs on**: CPU via `transformers` (not vllm)
**Purpose**: Validate hypernetwork generates sensible LoRA weights on our hardware

**Prerequisites**:
- ~8 GB disk for Qwen3-4B-Instruct-2507 base model
- ~1.7 GB disk for hypernetwork checkpoint
- ~10 GB RAM for CPU inference
- No HuggingFace auth needed (both model and checkpoint are public)

**Procedure**:
1. Clone and set up minimal environment:
   ```bash
   cd /mnt/raid0/llm
   git clone https://github.com/SakanaAI/doc-to-lora.git
   cd doc-to-lora
   python -m venv .venv && source .venv/bin/activate
   pip install torch transformers peft einops jaxtyping opt-einsum huggingface-hub
   ```

2. Download Qwen checkpoint only:
   ```bash
   huggingface-cli download SakanaAI/doc-to-lora qwen_4b_d2l/checkpoint-20000/pytorch_model.bin qwen_4b_d2l/args.yaml --local-dir trained_d2l
   ```

3. Download Qwen3-4B-Instruct-2507 base model:
   ```bash
   huggingface-cli download Qwen/Qwen3-4B-Instruct-2507 --local-dir /mnt/raid0/llm/models/Qwen3-4B-Instruct-2507
   ```

4. **Apply the CPU patch** to `src/ctx_to_lora/modeling/hypernet.py` (see Finding 4)

5. Run CPU inference validation script (`scripts/cpu_inference.py`):
   ```python
   import torch
   from ctx_to_lora.model_loading import get_tokenizer
   from ctx_to_lora.modeling.hypernet import ModulatedPretrainedModel

   state_dict = torch.load(
       "trained_d2l/qwen_4b_d2l/checkpoint-20000/pytorch_model.bin",
       weights_only=False, map_location="cpu"
   )
   model = ModulatedPretrainedModel.from_state_dict(
       state_dict, train=False, use_sequence_packing=False,
       use_flash_attn=False,
       base_model_kwargs={"device_map": "cpu", "torch_dtype": torch.float32},
   )
   model.reset()
   tokenizer = get_tokenizer("Qwen/Qwen3-4B-Instruct-2507")

   doc = open("data/sakana_wiki.txt").read()
   model.internalize(doc)

   chat = [{"role": "user", "content": "Tell me about Sakana AI."}]
   chat_ids = tokenizer.apply_chat_template(
       chat, add_special_tokens=False, add_generation_prompt=True, return_tensors="pt"
   )
   outputs = model.generate(input_ids=chat_ids, max_new_tokens=256)
   print(tokenizer.decode(outputs[0]))
   ```

6. Measure: `internalize()` latency, `generate()` with/without context, peak RSS, `generated_loras` tensor shapes

**Acceptance**: Model generates factually grounded answers about the internalized document. Adapter tensor shapes match `[1, 36, 8, 9728]` / `[1, 36, 8, 2560]`.

**Risks**:
- CPU inference may be very slow (minutes per generation) — acceptable for validation
- `from_state_dict()` may have additional CUDA assumptions beyond the known autocast issue

---

### Step 3: Build D2L-to-PEFT-to-GGUF conversion pipeline (1 day)

**Where**: `/mnt/raid0/llm/doc-to-lora` and `/mnt/raid0/llm/llama.cpp`
**Runs on**: CPU
**Purpose**: Bridge D2L raw tensors → PEFT format → GGUF LoRA for llama.cpp

**This is the highest-risk step.**

**Part A — D2L to PEFT** (`scripts/d2l_to_peft.py`):
1. Extract `model.generated_loras` after `internalize()`
2. Reshape to per-layer PEFT format:
   ```python
   A = loras["down_proj"]["A"].squeeze(0)  # [36, 8, 9728]
   B = loras["down_proj"]["B"].squeeze(0)  # [36, 8, 2560]
   for layer_idx in range(A.shape[0]):
       prefix = f"base_model.model.model.layers.{layer_idx}.mlp.down_proj"
       peft_state_dict[f"{prefix}.lora_A.weight"] = A[layer_idx].contiguous()       # [8, 9728]
       peft_state_dict[f"{prefix}.lora_B.weight"] = B[layer_idx].T.contiguous()     # [2560, 8] — transposed!
   ```
3. Write `adapter_config.json` (r=8, target_modules=["down_proj"], task_type=CAUSAL_LM)
4. Save as `adapter_model.safetensors`

**Note on `lora_alpha`**: D2L uses learned `scaler_A`/`scaler_B` per-module, not standard alpha. May need to bake scaling into weights directly.

**Part B — PEFT to GGUF**:
```bash
cd /mnt/raid0/llm/llama.cpp
python convert_lora_to_gguf.py \
    --base /mnt/raid0/llm/models/Qwen3-4B-Instruct-2507 \
    --outfile /mnt/raid0/llm/models/d2l-qwen3-4b-test.gguf \
    --outtype f16 \
    /path/to/peft/adapter/dir/
```

**Part C — Validate in llama.cpp**:
1. Get Qwen3-4B-Instruct-2507 GGUF (convert from HF — need instruct variant specifically):
   ```bash
   python convert_hf_to_gguf.py /mnt/raid0/llm/models/Qwen3-4B-Instruct-2507 --outtype q8_0 \
       --outfile /mnt/raid0/llm/models/Qwen3-4B-Instruct-2507-Q8_0.gguf
   ```
2. Serve with adapter via `--lora-init-without-apply`
3. Compare answers with/without LoRA against Step 2 transformers output

**Acceptance**: Full pipeline D2L → PEFT → GGUF → llama.cpp produces valid adapters and comparable answers.

**Key risks**:
- `lora_alpha` / scaling factor mismatch — D2L uses learned scalers, not global alpha
- Multi-chunk docs produce effective rank > 8 — `convert_lora_to_gguf.py` handles arbitrary rank but adapter grows
- Need Instruct-2507 specifically (not base Qwen3-4B) since hypernetwork was trained on it

---

### Step 4: Quality benchmark — adapter vs context-stuffing (1 day)

**Where**: `/mnt/raid0/llm/doc-to-lora/scripts/benchmark_vs_context.py`
**Runs on**: CPU
**Purpose**: Quantify quality/latency trade-off

**Procedure**:
1. Prepare 30 questions from SQuAD dev set (D2L paper's primary benchmark)
2. For each question + context document, run:
   - **Path A (context-stuffing)**: Full document + question in prompt → Qwen3-4B completion
   - **Path B (D2L adapter)**: Document → `internalize()` → adapter → question-only prompt with LoRA
3. Score via F1 token overlap (standard SQuAD metric)
4. Measure per-query latency for both paths
5. Compute break-even: at what queries-per-document does Path B win?

**Acceptance**: Quantitative table with F1 scores and latency ratios.

**Note**: CPU latencies will be 10-100x slower than GPU, but quality comparison and latency ratio are hardware-independent.

---

### Step 5: Go/no-go decision gate

| Criterion | GO | DEFER | NO-GO |
|---|---|---|---|
| Quality (F1) | ≥ 80% of context-stuffing | 70-80% | < 70% |
| Adapter generation | Completes, tensors valid | Slow but works | Errors or garbage tensors |
| GGUF conversion | Full pipeline works | Fixable gaps | Fundamental incompatibility |
| llama.cpp hot-swap | Per-request override works | Minor issues | Cache thrashing / instability |
| Latency ratio | B/A < 1.0 after ≤5 queries | B/A < 1.0 after ≤20 queries | B/A never < 1.0 |

**GO → Phase B** (separate handoff): Rent cloud GPUs, retrain hypernetwork for production model (Qwen2.5-Coder-1.5B or Qwen2.5-7B), integrate into orchestrator.

**DEFER**: Promising but no GPU budget. Archive findings.

**NO-GO**: Quality gap too large or pipeline breaks. Archive with findings.

### Phase A-bis — BitNet 2B4T Quality Validation (Optional, 2 hours)

Independent of D2L pipeline. Purpose: baseline BitNet quality vs existing worker model.

**Procedure**:
1. Download `microsoft/bitnet-b1.58-2B-4T-GGUF` (TQ1_0, ~400 MB)
2. Serve with `llama-server -m bitnet-2B4T.gguf -c 4096 -np 1`
3. Run question pool subset (50 questions, coding + reasoning):
   ```bash
   cd /mnt/raid0/llm/epyc-inference-research
   python scripts/benchmark/seed_specialist_routing.py \
       --model bitnet-2b4t --questions 50 --categories coding,reasoning
   ```
4. Compare vs Qwen2.5-Coder-1.5B Q4_K_M on same questions
5. Record throughput (tok/s on CPU)

**Acceptance**: Quality comparison table. Decision: viable `worker_fast` candidate?

**Context**: QVAC benchmarks show BitNet 2B4T at 60-64% win rate vs Q4 Qwen3-1.7B (LLM-as-Judge). ARC 49.91, GSM8K 58.38. Memory: 0.4 GB vs ~2 GB for comparable models. Likely weaker than Qwen2.5-Coder-1.5B (code-specialized) but worth validating given 5x memory advantage.

---

## Phase B Scope (NOT this handoff — requires GO decision + cloud GPUs)

### Hypernetwork Retraining
- Retrain targeting production model (Qwen2.5-Coder-1.5B or Qwen2.5-7B-Instruct)
- Training config: 9-block Perceiver, rank 8, down_proj, 20K steps (same as SakanaAI Qwen config)
- Training code is model-agnostic — change `model_name_or_path` in YAML
- Estimated cost: ~$200-500 for 8x A100 spot instance, 2-5 days

### Orchestrator Integration
| File | Change |
|---|---|
| `epyc-orchestrator/src/registry_loader.py:37` | Add `lora_adapters` field to `ModelConfig` |
| `epyc-orchestrator/orchestration/model_registry.yaml` | Add `lora_adapters:` per role |
| `epyc-orchestrator/scripts/server/orchestrator_stack.py:637` | Emit `--lora`/`--lora-init-without-apply` in `build_server_command()` |
| `epyc-orchestrator/src/backends/llama_server.py:655` | Add `"lora"` field to `_build_payload()` |
| `epyc-orchestrator/src/llm_primitives/inference.py` | Add `adapter_id` to `InferenceRequest` |
| `epyc-orchestrator/orchestration/model_registry.yaml` | Add `bitnet_model:` entry if Phase A-bis shows viable quality |

## Files to Create (Phase A)

| File | Purpose |
|---|---|
| `/mnt/raid0/llm/doc-to-lora/` | Cloned repo |
| `/mnt/raid0/llm/doc-to-lora/scripts/cpu_inference.py` | CPU validation script (Step 2) |
| `/mnt/raid0/llm/doc-to-lora/scripts/d2l_to_peft.py` | D2L → PEFT format converter (Step 3A) |
| `/mnt/raid0/llm/doc-to-lora/scripts/benchmark_vs_context.py` | A/B benchmark (Step 4) |

## Verification Plan

| Step | Verification |
|---|---|
| Step 1 | `curl` commands against `/lora-adapters` and `/completion`; compare outputs with/without LoRA |
| Step 2 | Model answers factual questions about internalized document; `generated_loras` shapes match expected |
| Step 3 | `convert_lora_to_gguf.py` exits 0; llama-server loads adapter; answers match transformers output |
| Step 4 | F1 scores computed; latency table populated; break-even point calculated |

## Acceptance Criteria

- [ ] llama.cpp LoRA hot-swap verified with smoke test (Step 1)
- [ ] D2L repo cloned, Qwen3-4B checkpoint loaded on CPU, adapter generation working (Step 2)
- [ ] D2L → PEFT → GGUF conversion pipeline automated (Step 3)
- [ ] Quality comparison: adapter F1 vs context-stuffing F1 on SQuAD subset (Step 4)
- [ ] Latency analysis: adapter generation + inference vs context-stuffing, break-even computed (Step 4)
- [ ] GO/DEFER/NO-GO decision documented (Step 5)

## Research Intake Update — 2026-03-17

### QVAC Fabric BitNet LoRA (intakes 162-164)

**What**: llama.cpp fork (`qvac-fabric-llm.cpp`, Apache 2.0) with Vulkan/Metal GPU backends for BitNet ternary inference + LoRA fine-tuning on mobile GPUs (Adreno, Mali, Apple). Results: BitNet-1B LoRA fine-tuning in 3m31s (4090), 1h45m (iPhone 16); 131 tok/s inference on iPhone 16.

**Relationship to D2L**: Complementary, not competing. QVAC = traditional supervised LoRA fine-tuning on-device. D2L = zero-shot hypernetwork-generated adapters. Both produce GGUF LoRA adapters consumed by the same llama.cpp inference API.

**EPYC applicability**:
| QVAC Feature | Applicable? | Reason |
|---|---|---|
| GPU ternary compute kernels | **NO** | GT 1030 display-only, no Vulkan compute |
| Mobile LoRA fine-tuning | **NO** | No mobile deployment target |
| LoRA training APIs | **PARTIALLY REDUNDANT** | Our fork already has `llama_opt_init`/`llama_opt_epoch` (see Finding 8) |
| GGUF adapter format | **VALIDATED** | 30 MB adapters work end-to-end in their benchmarks |
| `CROSS_ENTROPY_LOSS_MASKED` | **USEFUL** | Only missing backward op for assistant-only token loss (workaround: dataset-level masking) |

**Actionable**: If traditional LoRA fine-tuning becomes desirable for Qwen2.5, our fork already has the infra. The only gap is masked loss (`CROSS_ENTROPY_LOSS_MASKED`), which can be worked around at the dataset level. No code cherry-picking recommended — fork divergence is high (b7248 vs production-consolidated-v2).

### BitNet b1.58 2B4T (intake 165)

**What**: Microsoft's official 2B ternary model (MIT license, 4T training tokens). Native 1.58-bit quantization with BitLinear layers, ternary weight mapping {-1, 0, +1}.

**Quality benchmarks**:
| Metric | BitNet 2B4T | Comparable |
|---|---|---|
| Memory | 0.4 GB | ~2 GB (Qwen2.5-1.5B Q4) |
| ARC | 49.91 | — |
| GSM8K | 58.38 | — |
| QVAC LLM-Judge vs Q4 Qwen3-1.7B | 60-64% win rate | Quality gap remains |

**Decision**: Not for production. Competitive with Qwen2.5-1.5B on general benchmarks but likely weaker than Qwen2.5-Coder-1.5B (code-specialized). The 5x memory advantage (0.4 vs 2 GB) is compelling only if quality holds — Phase A-bis provides the validation path.
