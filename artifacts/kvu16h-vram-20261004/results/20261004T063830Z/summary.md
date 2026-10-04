# KVU-16h — :8083 VRAM growth attribution

- run `/mnt/raid0/llm/tmp/kvu16h-vram-20261004/results/20261004T063830Z`; argv source: /mnt/raid0/llm/epyc-orchestrator/logs/server_launches/8083.json (launched_at 2026-10-04T02:48:09.776Z, pid 1703677, argv_sha256 b865820d557f, launcher scripts/server/orchestrator_stack.py reload architect_critic, stack_commit ff92a580ea1a)
- argv: `numactl --membind=3 -- taskset -c 184-191 /mnt/raid0/llm/kernels/builds/gpu-20260921-ffc1bac82/bin/llama-server -m /mnt/raid0/llm/models/Qwen3.8-27B-Q8_0.gguf --host 127.0.0.1 --port 8083 -np 4 -c 393216 -t 8 -ub 2048 --flash-attn on --jinja -ctk q8_0 -ctv q8_0 --kv-unified --no-mmap -ngl all --cache-ram 65536 --chat-template-file /mnt/raid0/llm/models/chat-templates/epyc-qwen3x-v1-terse.jinja -md /mnt/raid0/llm/models/Qwen3.8-27B-DFlash2-Q8_0.gguf -ngld 99 --spec-type draft-dflash --spec-draft-n-max 7 --device ROCm0 --slot-save-path /mnt/raid0/llm/cache/kv_slots/architect_critic --device-draft ROCm0`
- shim: True; -lv 4; ceiling 62.5 GiB; budget 60.0 min; elapsed 33.5 min; arm B {'choice': 'ub512', 'why': 'forced by --arm-b'}
- question: production :8083 went 51.69 -> 58.88 -> 59.77 GiB while serving (KVU-16b at 310k cells added 0); the gate is 62 GiB.

## armA

- server pid 416066; own KFD after load 50.770 GiB; serving peak 52.189 GiB; **growth 1.420 GiB**; shim ON (576 events)
- **verdict: MIXED (largest share): legacy pool (target) = 0.58 of 1.42 GiB (41%)**
- plateau: PLATEAU (mix1 -0.02, mix2 -0.00 GiB)
- idle_release: long idle delta +0.000 GiB

| phase | dur s | KFD end GiB | delta GiB | peak GiB | card end | rocm-smi end | shim net GiB (top classes) | residual GiB | log: reserve / compute-buf / pool / mismatch / idle-save / restore |
|---|---|---|---|---|---|---|---|---|---|
| load | 66.0 | 50.770 | +50.770 | 50.770 | 50.782 | 50.782 | model|target +25.36; kv|target +17.43; compute|target +3.31 | - | 4 / 4 / 0 / 0 / 0 / 0 |
| short | 62.3 | 51.069 | +0.299 | 51.069 | 51.081 | 51.081 | compute|target +0.20; rocblas|draft +0.03; pool_leg/mmq|target +0.01 | +0.061 | 2 / 2 / 0 / 0 / 3 / 0 |
| sweep | 130.5 | 51.909 | +0.840 | 51.909 | 51.925 | 51.925 | pool_leg/cublas_f16|draft +0.50; pool_leg/cublas_f16|target +0.29; rocblas|target +0.03 | +0.027 | 0 / 0 / 0 / 0 / 36 / 0 |
| prefill80k | 215.5 | 51.901 | -0.008 | 51.909 | 51.917 | 51.917 | - | - | 0 / 0 / 0 / 0 / 3 / 0 |
| dec4 | 113.4 | 51.930 | +0.028 | 51.930 | 51.947 | 51.947 | - | - | 0 / 0 / 0 / 0 / 6 / 0 |
| mix1 | 194.6 | 51.910 | -0.020 | 51.930 | 51.930 | 51.930 | - | - | 0 / 0 / 0 / 0 / 6 / 0 |
| mix2 | 193.2 | 51.908 | -0.002 | 51.910 | 51.933 | 51.933 | - | - | 0 / 0 / 0 / 0 / 6 / 0 |
| t7c | 178.7 | 51.908 | +0.000 | 51.908 | 51.939 | 51.939 | - | - | 0 / 0 / 0 / 0 / 6 / 0 |
| nodraft | 89.1 | 51.900 | -0.008 | 51.908 | 51.935 | 51.935 | pool_leg/mmq|target -0.01; pool_leg/fattn|target +0.00; pool_leg/mmv|target +0.00 | -0.006 | 0 / 0 / 0 / 0 / 6 / 0 |
| idlecache | 67.6 | 52.189 | +0.289 | 52.189 | 52.225 | 52.225 | pool_leg/cublas_f16|target +0.28 | +0.004 | 0 / 0 / 0 / 0 / 6 / 2 |
| longidle | 180.0 | 52.189 | +0.000 | 52.189 | 52.225 | 52.225 | - | - | 0 / 0 / 0 / 0 / 0 / 0 |
| teardown | 0.5 | 0.535 | -51.654 | 0.535 | 49.594 | 52.225 | model|target -25.36; kv|target -17.43; compute|target -3.51 | -0.023 | 0 / 0 / 0 / 0 / 0 / 0 |

### Candidates

| candidate | evidence | GiB | verdict |
|---|---|---|---|
| ggml-cuda legacy pool (NO_VMM: GGML_HIP_NO_VMM=ON, no pool_vmm symbols) | shim ggml_cuda_pool_leg::alloc net | 1.08 | PRIMARY |
| compute-buffer realloc beyond the reserve | shim sched/gallocr buffers + mismatch WARN x0 | 0.20 | contributes |
| rocBLAS / hipBLASLt workspaces | shim allocs inside librocblas/libhipblas* | 0.06 | ruled out (<10%) |
| DFlash2 drafter buffers | shim classes with ctx=draft | 0.53 | contributes |
| slot save/restore (--cache-ram, idle-slot caching) | idlecache phase KFD delta +0.289; idle saves 6, restores 2 | 0.29 | CHECK |
| HIP runtime internal (HIP graphs: GGML_HIP_GRAPHS=ON; code objects) | residual = KFD - shim | 0.08 | ruled out (<10%) |

### Growth by allocator (load idle end -> last serving phase)

| allocator | GiB |
|---|---|
| legacy pool (target) | +0.576 |
| legacy pool (draft) | +0.501 |
| compute-buffer realloc (target) | +0.195 |
| HIP runtime internal (residual: graphs, code objects, kernarg) | +0.085 |
| rocBLAS/hipBLAS(Lt) (draft) | +0.031 |
| rocBLAS/hipBLAS(Lt) (target) | +0.031 |

### Top allocation call chains (shim, bytes allocated over the whole arm)

| class | GiB | chain (innermost first) |
|---|---|---|
| model|draft | 27.27 | `ggml_backend_cuda_buffer_type_alloc_buffer < alloc_tensor_range < ggml_backend_alloc_ctx_tensors_from_buft_impl.constprop.0 < ggml_backend_alloc_ctx_tensors_from_buft < llama_model_base::load_tensors < llama_model_load < llama_model_load_from_file_impl < llama_model_load_from_file` |
| kv|target | 12.75 | `ggml_backend_cuda_buffer_type_alloc_buffer < alloc_tensor_range < ggml_backend_alloc_ctx_tensors_from_buft_impl.constprop.0 < ggml_backend_alloc_ctx_tensors_from_buft < llama_kv_cache::llama_kv_cache < llama_memory_hybrid::llama_memory_hybrid < llama_model::create_memory < llama_context::llama_conte` |
| kv|target | 9.35 | `ggml_backend_cuda_buffer_type_alloc_buffer < alloc_tensor_range < ggml_backend_alloc_ctx_tensors_from_buft_impl.constprop.0 < ggml_backend_alloc_ctx_tensors_from_buft < llama_memory_recurrent::llama_memory_recurrent < llama_memory_hybrid::llama_memory_hybrid < llama_model::create_memory < llama_cont` |
| compute|target | 3.51 | `ggml_backend_cuda_buffer_type_alloc_buffer < ggml_gallocr_reserve_n_impl < ggml_backend_sched_reserve < llama_context::graph_reserve < llama_context::sched_reserve < llama_context::decode < llama_decode < server_context_impl::decode` |
| compute|target | 3.31 | `ggml_backend_cuda_buffer_type_alloc_buffer < ggml_gallocr_reserve_n_impl < ggml_backend_sched_reserve < llama_context::graph_reserve < llama_context::sched_reserve < llama_context::llama_context < llama_init_from_model < common_init_result::common_init_result` |
| compute|draft | 2.09 | `ggml_backend_cuda_buffer_type_alloc_buffer < ggml_gallocr_reserve_n_impl < ggml_backend_sched_reserve < llama_context::graph_reserve < llama_context::sched_reserve < llama_context::llama_context < llama_init_from_model < common_speculative_init_result::common_speculative_init_result` |
| pool_leg/cublas_f16|target | 0.57 | `ggml_cuda_pool_leg::alloc < ggml_cuda_mul_mat_cublas < ggml_cuda_graph_evaluate_and_capture < ggml_backend_cuda_graph_compute < ggml_backend_sched_graph_compute_async < llama_context::graph_compute < llama_context::process_ubatch < llama_context::decode` |
| pool_leg/cublas_f16|draft | 0.50 | `ggml_cuda_pool_leg::alloc < ggml_cuda_mul_mat_cublas < ggml_cuda_graph_evaluate_and_capture < ggml_backend_cuda_graph_compute < ggml_backend_sched_graph_compute_async < llama_context::graph_compute < llama_context::process_ubatch < llama_context::encode` |
| kv|draft | 0.20 | `ggml_backend_cuda_buffer_type_alloc_buffer < alloc_tensor_range < ggml_backend_alloc_ctx_tensors_from_buft_impl.constprop.0 < ggml_backend_alloc_ctx_tensors_from_buft < llama_kv_cache::llama_kv_cache < llama_kv_cache_iswa::llama_kv_cache_iswa < llama_kv_cache_iswa::llama_kv_cache_iswa < llama_model:` |
| rocblas|target | 0.06 | `_rocblas_handle::_rocblas_handle < rocblas_create_handle < hipblasCreate < ggml_cuda_mul_mat_cublas < ggml_cuda_graph_evaluate_and_capture < ggml_backend_cuda_graph_compute < ggml_backend_sched_graph_compute_async < llama_context::graph_compute` |
| pool_leg/mmq|draft | 0.01 | `ggml_cuda_pool_leg::alloc < void mul_mat_q_switch_J< < ggml_cuda_mul_mat_q < ggml_cuda_graph_evaluate_and_capture < ggml_backend_cuda_graph_compute < ggml_backend_sched_graph_compute_async < llama_context::graph_compute < llama_context::process_ubatch` |
| pool_leg/fattn|target | 0.00 | `ggml_cuda_pool_leg::alloc < void launch_fattn<256, 1, 1> < void ggml_cuda_flash_attn_ext_vec_case<256,  < ggml_cuda_graph_evaluate_and_capture < ggml_backend_cuda_graph_compute < ggml_backend_sched_graph_compute_async < llama_context::graph_compute < llama_context::process_ubatch` |
| pool_leg/mmv|target | 0.00 | `ggml_cuda_pool_leg::alloc < ggml_cuda_mul_mat_vec_q < ggml_cuda_graph_evaluate_and_capture < ggml_backend_cuda_graph_compute < ggml_backend_sched_graph_compute_async < llama_context::graph_compute < llama_context::process_ubatch < llama_context::decode` |
| pool_leg/other|draft | 0.00 | `ggml_cuda_pool_leg::alloc < ggml_cuda_mul_mat_q < ggml_cuda_graph_evaluate_and_capture < ggml_backend_cuda_graph_compute < ggml_backend_sched_graph_compute_async < llama_context::graph_compute < llama_context::process_ubatch < llama_context::encode` |

### Compute buffers / breakdown

- load reserve: ROCm0 3392.33 MiB (t 1791095922.6)
- load reserve: ROCm_Host 1616.34 MiB (t 1791095922.6)
- load reserve: ROCm0 2143.68 MiB (t 1791095923.2)
- load reserve: ROCm_Host 1980.17 MiB (t 1791095923.2)
- EXIT breakdown ROCm0 (MI210): total 65520 = free 12242 + (self 47408 = model 25972 + context 17844 + compute 3592) + unaccounted 5869 MiB

### Log lines per phase (first matches)

- **load**: reserve: `0.03.260.601 I sched_reserve: reserving ...`; compute_buffer: `0.03.362.523 I sched_reserve:      ROCm0 compute buffer size =  3392.33 MiB`; breakdown: `0.00.704.014 I common_memory_breakdown_print: | memory breakdown [MiB] | total    free     self   model   context   compute    unaccounted |`; checkpoint: `0.04.060.048 I srv    load_model: context checkpoints enabled, max = 32, min spacing = 8192`
- **short**: reserve: `1.05.991.861 I sched_reserve: reserving ...`; compute_buffer: `1.06.100.249 I sched_reserve:      ROCm0 compute buffer size =  3592.33 MiB`; idle_save: `1.05.989.951 I slot process_sing: id  0 | task -1 | saving idle slot to prompt cache`; checkpoint: `1.06.270.233 I slot create_check: id  3 | task 0 | created context checkpoint 1 of 32 (pos_min = 52, pos_max = 52, n_tokens = 53, size = 150.662 MiB)`
- **sweep**: idle_save: `2.08.414.571 I slot process_sing: id  0 | task -1 | saving idle slot to prompt cache`; clear_prompt: `2.08.447.878 I slot prompt_clear: id  3 | task -1 | clearing prompt with 128 tokens`; checkpoint: `2.09.050.856 I slot create_check: id  2 | task 28 | created context checkpoint 1 of 32 (pos_min = 399, pos_max = 399, n_tokens = 400, size = 157.443 MiB)`
- **prefill80k**: idle_save: `4.19.092.702 I slot process_sing: id  0 | task -1 | saving idle slot to prompt cache`; clear_prompt: `4.19.190.292 I slot prompt_clear: id  3 | task -1 | clearing prompt with 12793 tokens`; checkpoint: `6.45.536.974 I slot create_check: id  2 | task 202 | created context checkpoint 1 of 32 (pos_min = 77796, pos_max = 77796, n_tokens = 77797, size = 189.650 MiB)`
- **dec4**: idle_save: `7.54.557.417 I slot process_sing: id  0 | task -1 | saving idle slot to prompt cache`; clear_prompt: `7.54.854.205 I slot prompt_clear: id  2 | task -1 | clearing prompt with 79908 tokens`; checkpoint: `7.57.477.268 I slot create_check: id  0 | task 271 | created context checkpoint 1 of 32 (pos_min = 990, pos_max = 990, n_tokens = 991, size = 168.993 MiB)`
- **mix1**: idle_save: `9.48.373.112 I slot process_sing: id  0 | task -1 | saving idle slot to prompt cache`; clear_prompt: `9.48.812.051 I slot prompt_clear: id  0 | task -1 | clearing prompt with 1994 tokens`; checkpoint: `operator(): id  3 | task 633 | erased invalidated context checkpoint (pos_min = 991, pos_max = 991, n_tokens = 992, n_swa = 0, pos_next = 0, size = 169.013 MiB)`
- **mix2**: idle_save: `13.03.021.846 I slot process_sing: id  1 | task -1 | saving idle slot to prompt cache`; clear_prompt: `13.03.226.899 I slot prompt_clear: id  1 | task -1 | clearing prompt with 31919 tokens`; checkpoint: `or(): id  0 | task 765 | erased invalidated context checkpoint (pos_min = 29982, pos_max = 29982, n_tokens = 29983, n_swa = 0, pos_next = 0, size = 189.650 MiB)`
- **t7c**: idle_save: `16.16.346.249 I slot process_sing: id  0 | task -1 | saving idle slot to prompt cache`; clear_prompt: `16.16.501.906 I slot prompt_clear: id  0 | task -1 | clearing prompt with 1362 tokens`; checkpoint: `6.42.464.729 I slot create_check: id  0 | task 901 | created context checkpoint 1 of 32 (pos_min = 13903, pos_max = 13903, n_tokens = 13904, size = 189.650 MiB)`
- **nodraft**: idle_save: `19.15.046.313 I slot process_sing: id  1 | task -1 | saving idle slot to prompt cache`; clear_prompt: `19.15.171.516 I slot prompt_clear: id  1 | task -1 | clearing prompt with 15951 tokens`; checkpoint: `or(): id  0 | task 936 | erased invalidated context checkpoint (pos_min = 13903, pos_max = 13903, n_tokens = 13904, n_swa = 0, pos_next = 0, size = 189.650 MiB)`
- **idlecache**: idle_save: `20.44.054.319 I slot process_sing: id  0 | task -1 | saving idle slot to prompt cache`; clear_prompt: `20.44.101.922 I slot prompt_clear: id  1 | task -1 | clearing prompt with 2219 tokens`; cache_restore: `20.49.718.399 I srv          load:  - found better prompt with f_keep = 0.999, sim = 1.000`; checkpoint: `20.44.608.602 I slot create_check: id  2 | task 1148 | created context checkpoint 1 of 32 (pos_min = 360, pos_max = 360, n_tokens = 361, size = 156.681 MiB)`
- **teardown**: breakdown: `24.51.608.754 I common_memory_breakdown_print: | memory breakdown [MiB] | total    free     self   model   context   compute    unaccounted |`

## armB_ub512

- server pid 3905741; own KFD after load 47.813 GiB; serving peak 48.607 GiB; **growth 0.794 GiB**; shim ON (52 events)
- **verdict: MIXED (largest share): legacy pool (draft) = 0.31 of 0.79 GiB (39%)**
- plateau: PLATEAU (mix1 +0.79, mix2 +0.01 GiB)

| phase | dur s | KFD end GiB | delta GiB | peak GiB | card end | rocm-smi end | shim net GiB (top classes) | residual GiB | log: reserve / compute-buf / pool / mismatch / idle-save / restore |
|---|---|---|---|---|---|---|---|---|---|
| load | 64.0 | 47.813 | +47.813 | 47.813 | 47.825 | 47.825 | model|target +25.36; kv|target +17.43; compute|target +1.95 | - | 4 / 4 / 0 / 0 / 0 / 0 |
| mix1 | 218.6 | 48.600 | +0.787 | 48.600 | 48.614 | 48.614 | pool_leg/cublas_f16|draft +0.31; pool_leg/cublas_f16|target +0.29; compute|target +0.05 | +0.078 | 2 / 2 / 0 / 0 / 6 / 0 |
| mix2 | 221.1 | 48.607 | +0.007 | 48.607 | 48.623 | 48.623 | - | - | 0 / 0 / 0 / 0 / 6 / 0 |
| teardown | 0.3 | 48.607 | +0.000 | - | 48.623 | 48.623 | model|target -25.36; kv|target -17.43; compute|target -2.00 | +48.048 | 0 / 0 / 0 / 0 / 0 / 0 |

### Candidates

| candidate | evidence | GiB | verdict |
|---|---|---|---|
| ggml-cuda legacy pool (NO_VMM: GGML_HIP_NO_VMM=ON, no pool_vmm symbols) | shim ggml_cuda_pool_leg::alloc net | 0.60 | PRIMARY |
| compute-buffer realloc beyond the reserve | shim sched/gallocr buffers + mismatch WARN x0 | 0.05 | ruled out (<10%) |
| rocBLAS / hipBLASLt workspaces | shim allocs inside librocblas/libhipblas* | 0.06 | ruled out (<10%) |
| DFlash2 drafter buffers | shim classes with ctx=draft | 0.34 | contributes |
| slot save/restore (--cache-ram, idle-slot caching) | idlecache phase KFD delta -; idle saves 0, restores 0 | 0.00 | not run |
| HIP runtime internal (HIP graphs: GGML_HIP_GRAPHS=ON; code objects) | residual = KFD - shim | 0.08 | contributes |

### Growth by allocator (load idle end -> last serving phase)

| allocator | GiB |
|---|---|
| legacy pool (draft) | +0.306 |
| legacy pool (target) | +0.292 |
| HIP runtime internal (residual: graphs, code objects, kernarg) | +0.085 |
| compute-buffer realloc (target) | +0.049 |
| rocBLAS/hipBLAS(Lt) (target) | +0.031 |
| rocBLAS/hipBLAS(Lt) (draft) | +0.031 |

### Top allocation call chains (shim, bytes allocated over the whole arm)

| class | GiB | chain (innermost first) |
|---|---|---|
| model|draft | 27.27 | `ggml_backend_cuda_buffer_type_alloc_buffer < alloc_tensor_range < ggml_backend_alloc_ctx_tensors_from_buft_impl.constprop.0 < ggml_backend_alloc_ctx_tensors_from_buft < llama_model_base::load_tensors < llama_model_load < llama_model_load_from_file_impl < llama_model_load_from_file` |
| kv|target | 12.75 | `ggml_backend_cuda_buffer_type_alloc_buffer < alloc_tensor_range < ggml_backend_alloc_ctx_tensors_from_buft_impl.constprop.0 < ggml_backend_alloc_ctx_tensors_from_buft < llama_kv_cache::llama_kv_cache < llama_memory_hybrid::llama_memory_hybrid < llama_model::create_memory < llama_context::llama_conte` |
| kv|target | 9.35 | `ggml_backend_cuda_buffer_type_alloc_buffer < alloc_tensor_range < ggml_backend_alloc_ctx_tensors_from_buft_impl.constprop.0 < ggml_backend_alloc_ctx_tensors_from_buft < llama_memory_recurrent::llama_memory_recurrent < llama_memory_hybrid::llama_memory_hybrid < llama_model::create_memory < llama_cont` |
| compute|target | 2.00 | `ggml_backend_cuda_buffer_type_alloc_buffer < ggml_gallocr_reserve_n_impl < ggml_backend_sched_reserve < llama_context::graph_reserve < llama_context::sched_reserve < llama_context::decode < llama_decode < server_context_impl::decode` |
| compute|target | 1.95 | `ggml_backend_cuda_buffer_type_alloc_buffer < ggml_gallocr_reserve_n_impl < ggml_backend_sched_reserve < llama_context::graph_reserve < llama_context::sched_reserve < llama_context::llama_context < llama_init_from_model < common_init_result::common_init_result` |
| compute|draft | 0.52 | `ggml_backend_cuda_buffer_type_alloc_buffer < ggml_gallocr_reserve_n_impl < ggml_backend_sched_reserve < llama_context::graph_reserve < llama_context::sched_reserve < llama_context::llama_context < llama_init_from_model < common_speculative_init_result::common_speculative_init_result` |
| pool_leg/cublas_f16|draft | 0.31 | `ggml_cuda_pool_leg::alloc < ggml_cuda_mul_mat_cublas < ggml_cuda_graph_evaluate_and_capture < ggml_backend_cuda_graph_compute < ggml_backend_sched_graph_compute_async < llama_context::graph_compute < llama_context::process_ubatch < llama_context::encode` |
| pool_leg/cublas_f16|target | 0.29 | `ggml_cuda_pool_leg::alloc < ggml_cuda_mul_mat_cublas < ggml_cuda_graph_evaluate_and_capture < ggml_backend_cuda_graph_compute < ggml_backend_sched_graph_compute_async < llama_context::graph_compute < llama_context::process_ubatch < llama_context::decode` |
| kv|draft | 0.17 | `ggml_backend_cuda_buffer_type_alloc_buffer < alloc_tensor_range < ggml_backend_alloc_ctx_tensors_from_buft_impl.constprop.0 < ggml_backend_alloc_ctx_tensors_from_buft < llama_kv_cache::llama_kv_cache < llama_kv_cache_iswa::llama_kv_cache_iswa < llama_kv_cache_iswa::llama_kv_cache_iswa < llama_model:` |
| rocblas|draft | 0.06 | `_rocblas_handle::_rocblas_handle < rocblas_create_handle < hipblasCreate < ggml_cuda_mul_mat_cublas < ggml_cuda_graph_evaluate_and_capture < ggml_backend_cuda_graph_compute < ggml_backend_sched_graph_compute_async < llama_context::graph_compute` |
| pool_leg/mmq|target | 0.00 | `ggml_cuda_pool_leg::alloc < void mul_mat_q_switch_J< < ggml_cuda_mul_mat_q < ggml_cuda_graph_evaluate_and_capture < ggml_backend_cuda_graph_compute < ggml_backend_sched_graph_compute_async < llama_context::graph_compute < llama_context::process_ubatch` |
| pool_leg/other|target | 0.00 | `ggml_cuda_pool_leg::alloc < ggml_cuda_mul_mat_q < ggml_cuda_graph_evaluate_and_capture < ggml_backend_cuda_graph_compute < ggml_backend_sched_graph_compute_async < llama_context::graph_compute < llama_context::process_ubatch < llama_context::decode` |
| pool_leg/mmv|target | 0.00 | `ggml_cuda_pool_leg::alloc < ggml_cuda_mul_mat_vec_q < ggml_cuda_graph_evaluate_and_capture < ggml_backend_cuda_graph_compute < ggml_backend_sched_graph_compute_async < llama_context::graph_compute < llama_context::process_ubatch < llama_context::decode` |
| pool_leg/fattn|target | 0.00 | `ggml_cuda_pool_leg::alloc < void launch_fattn<128, 2, 1> < void ggml_cuda_flash_attn_ext_vec_case<128,  < ggml_cuda_graph_evaluate_and_capture < ggml_backend_cuda_graph_compute < ggml_backend_sched_graph_compute_async < llama_context::graph_compute < llama_context::process_ubatch` |

### Compute buffers / breakdown

- load reserve: ROCm0 2000.28 MiB (t 1791097420.7)
- load reserve: ROCm_Host 404.28 MiB (t 1791097420.7)
- load reserve: ROCm0 537.14 MiB (t 1791097421.2)
- load reserve: ROCm_Host 493.54 MiB (t 1791097421.2)
- EXIT breakdown ROCm0 (MI210): total 65520 = free 15912 + (self 45866 = model 25972 + context 17844 + compute 2050) + unaccounted 3741 MiB

### Log lines per phase (first matches)

- **load**: reserve: `0.03.255.626 I sched_reserve: reserving ...`; compute_buffer: `0.03.286.860 I sched_reserve:      ROCm0 compute buffer size =  2000.28 MiB`; breakdown: `0.00.701.399 I common_memory_breakdown_print: | memory breakdown [MiB] | total    free     self   model   context   compute    unaccounted |`; checkpoint: `0.03.897.581 I srv    load_model: context checkpoints enabled, max = 32, min spacing = 8192`
- **mix1**: reserve: `1.04.086.951 I sched_reserve: reserving ...`; compute_buffer: `1.04.118.050 I sched_reserve:      ROCm0 compute buffer size =  2050.28 MiB`; idle_save: `1.04.084.651 I slot process_sing: id  0 | task -1 | saving idle slot to prompt cache`; checkpoint: `1.04.958.355 I slot create_check: id  2 | task 1 | created context checkpoint 1 of 32 (pos_min = 482, pos_max = 482, n_tokens = 483, size = 159.065 MiB)`
- **mix2**: idle_save: `4.43.112.111 I slot process_sing: id  1 | task -1 | saving idle slot to prompt cache`; clear_prompt: `4.43.401.562 I slot prompt_clear: id  1 | task -1 | clearing prompt with 31796 tokens`; checkpoint: `or(): id  0 | task 230 | erased invalidated context checkpoint (pos_min = 31244, pos_max = 31244, n_tokens = 31245, n_swa = 0, pos_next = 0, size = 189.650 MiB)`
- **teardown**: breakdown: `8.23.910.248 I common_memory_breakdown_print: | memory breakdown [MiB] | total    free     self   model   context   compute    unaccounted |`

## Arm comparison: armA vs armB_ub512

- growth after load: armA +1.420 GiB (all phases) vs armB_ub512 +0.794 GiB (mix1+mix2 only)
- mix1/mix2 deltas: A -0.020/-0.002 vs B +0.787/+0.007 GiB
- **NOT shown bounded by this flag** (rule: B growth <= 50% of A's and B's mix2 delta < 0.25 GiB). Caveat: A's mix phases ran after other shapes had already grown the pool.

## KVU-16i runtime term (proposal)

- `vram_runtime_growth_gib` for :8083 = serving peak - after-load = 1.420 GiB in this run (production observed +8.08 from 51.69 to 59.77 and still rising); evidence `armA/vram.jsonl`
- attribution: MIXED (largest share): legacy pool (target) = 0.58 of 1.42 GiB (41%)

## How the candidates are decided

1. Growth G = own-pid KFD at the end of the last serving phase - at the end of the post-load idle.
2. The shim ledger splits G by the call chain of every public hipMalloc/hipFree (net live bytes per class in the window); residual = G - shim = HIP-runtime-internal memory.
3. The largest group is the named allocator (ATTRIBUTED if >= 60% of G, else MIXED). Pool route cublas_f16 = the Q8_0 ne11>128 hipBLAS path (MMQ is used only for ne11 <= 128 on CDNA2).
4. Cross-checks: exit breakdown compute column vs the load reserve (gallocr growth); the ~llama_context mismatch WARN; per-phase steps (first occurrence of a larger shape) and the mix2 plateau; the idlecache phase delta (slot save/restore lives in host RAM by source).
5. Arm B: BOUNDED if its growth <= 50% of arm A's and mix2 adds < 0.25 GiB.
