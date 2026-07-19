# GLM MTP Contract-Generalization Audit - 2026-07-19

Scope: CPU/no-GPU, zero-inference source and artifact read for B6. No builds, no
server starts, no inference.

## Verdict

The current GLM-5.2 native-MTP scaffold is correctly scoped as a single-NextN
implementation. That is not a hidden blocker for the present artifact: both the
GLM-5.2 UD-IQ2_M contract and the no-inference Qwen3.5-27B MTP contract report
exactly one appended NextN block.

Do not promote this as a multi-head/general MTP implementation. The generic
speculative driver can chain multiple heads, but the relevant model graph must
select heads with `cparams.nextn_layer_offset`. The newer `step35` and `hy_v3`
graphs do that; `qwen35`, `qwen35moe`, `cohere2moe`, and the current
DeepSeek32/GLM-DSA graph are only proven for the observed single-head contracts.

## Contract Comparison

| Contract | Architecture | Block count | NextN layers | Tail layer | NextN tensors |
|---|---:|---:|---:|---:|---|
| `docs/data/glm52_nextn_tensor_contract_20260718.json` | `glm-dsa` | 79 | 1 | 78 | `nextn.eh_proj`, `nextn.enorm`, `nextn.hnorm`, optional `nextn.shared_head_norm`; no separate nextn embed/head |
| `data/cpu_no_inference/qwen35_27b_mtp_tensor_contract_20260719T002352Z/contract.json` | `qwen35` | 65 | 1 | 64 | same required projection/norm pattern plus optional shared-head norm |

## Code-Path Anchors

- `/mnt/raid0/llm/llama.cpp-experimental/src/models/deepseek32.cpp:42`
  loads `LLM_KV_NEXTN_PREDICT_LAYERS` for the shared DeepSeek32/GLM-DSA model.
- `/mnt/raid0/llm/llama.cpp-experimental/src/models/deepseek32.cpp:82`
  iterates all physical layers, marking `i >= n_layer` as NextN tail layers.
- `/mnt/raid0/llm/llama.cpp-experimental/src/models/deepseek32.cpp:141`
  loads the GLM/DeepSeek32 NextN projection/norm tensors on those tail layers.
- `/mnt/raid0/llm/llama.cpp-experimental/src/models/deepseek32.cpp:504`
  exposes post-final-norm target hidden state through `res->t_h_nextn` when
  `n_layer_nextn > 0`.
- `/mnt/raid0/llm/llama.cpp-experimental/src/models/qwen35.cpp:492`
  asserts `n_layer_nextn > 0`, and `:493` asserts `n_layer_nextn == 1`; that is
  the older single-head precedent.
- `/mnt/raid0/llm/llama.cpp-experimental/src/models/step35.cpp:370`
  documents the multi-block pattern and uses `cparams.nextn_layer_offset`.
- `/mnt/raid0/llm/llama.cpp-experimental/src/models/hy-v3.cpp:247`
  uses the same `hparams.n_layer() + cparams.nextn_layer_offset` selection.
- `/mnt/raid0/llm/llama.cpp-experimental/common/speculative.cpp:1632`
  reads `llama_model_n_layer_nextn`; `:1678` enables head chaining only when
  `n_mtp_layers > 1 && !is_mem_shared`; `:1803` and `:1901` select per-head
  offsets during process/draft.

## Checkbox-Ready Findings

- [x] **B6 contract-generalization audit**: GLM-5.2 and Qwen3.5-27B contract
  artifacts both show `nextn_predict_layers=1`; the current GLM scaffold is
  safe to describe as single-NextN and should not be widened to a multi-head
  claim without code work plus tests. ✅ 2026-07-19
- [ ] **B6 multi-head follow-up, only if a future GLM/DSA artifact reports
  `nextn_predict_layers>1`**: port the `step35`/`hy_v3`
  `nextn_layer_offset` selection pattern into the GLM/DeepSeek32 MTP graph,
  then add an arch test that exercises offsets beyond zero.
- [ ] **B6 runtime gate remains**: after GLM reviewer quality re-clears, run
  numerical/coherence and live draft-counter A/B with enough generated tokens
  to measure alpha; one-token/eight-token scaffold smokes are not throughput or
  acceptance evidence.

## Bench Window Need

No uncontended bench window is needed for this audit result. Follow-up runtime
alpha/quality/throughput still requires an operator-approved uncontended bench
window after GLM quality recovery.
