# KVU-16h follow-up + arm C — pool pinning by the HIP-graph mmvq q8_1 cache, and its fix (2026-10-04T11:32:09Z)

- run `/mnt/raid0/llm/tmp/kvu16h-vram-20261004/results/fuc-20261004T110509Z`
- **verdict: CONFIRMED** (basis: own-pid KFD)
- arm A t7a growth 5.828 GiB over 21 events (model 6.09 GiB at 0.29/event); ctrl 0.062 GiB; arm B (graphs off) t7a 0.051 GiB
- checks: {'t7a_reproduces': True, 'ctrl_flat': True, 'armB_flat': True, 'shim_big_allocs_in_events': True, 'shim_pins_in_nodraft': True}
- graphs-off decode cost (median tok/s): {'nodraft_tps_A': 31.38, 'nodraft_tps_B': 29.63, 'drafted_tps_A': 59.08, 'drafted_tps_B': 61.62}
- **KVU-16i**: KVU-16i runtime term = 1.42 GiB (bounded warm-up) ONLY for traffic without single-slot no-draft decodes; every 'speculative.n_max 0 decode -> fresh prefill' transition adds ~0.28 GiB with no bound below OOM (pinned buffers are invisible to the pool's OOM flush). Gate: no per-request n_max 0 against :8083 (bench runners use scratch servers), or GGML_CUDA_DISABLE_GRAPHS=1 at the decode cost shown, or fix the cache on llama.cpp-experimental (dedicated exact-size pool / release at capture end)
- **arm C (fix 656c9a66b, graphs ON): HOLDS** — {'fix': 'HOLDS', 'armC_t7a_growth_gib': 0.057, 'armC_t7a_events': 21, 'armA_t7a_growth_gib': 5.828, 'checks': {'armC_t7a_has_events': True, 'armC_t7a_flat': True, 'armC_no_mmvq_pool_pins': True, 'armC_arena_bounded': True}, 'decode_tps': {'nodraft_A': 31.38, 'nodraft_C': 31.7, 'nodraft_C_over_A': 1.0102, 'drafted_A': 59.08, 'drafted_C': 61.97, 'drafted_C_over_A': 1.0489}, 'arena': {'n': 1, 'mib': 4.0}}

## armA

- result: {'pid': 2107702, 'load_s': 6.0, 'aborted': None, 'error': None, 'skipped': [], 'peak_own_gib': 58.487, 'soft_ceiling_hit': False, 'extra_env': {}}

| phase | req | non-200 | KFD growth GiB | events | model GiB | KFD in events GiB | per event | shim pool_big GiB | big in events | mmvq pins (in nodraft) | nonpool GiB | tps nodraft / drafted | T7#1 fidelity prompt_n= / pred= | mmvq arena n / MiB |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| warm | 2 | 0 | 0.923 | 0 | 0.0 | 0 | None | 0.647 | 0.0 | 0 (0) | 3.571 | None / 43.49 | 0/0 , 0/0 | 0 / 0.0 |
| ctrl | 24 | 0 | 0.062 | 0 | 0.0 | 0 | None | 0.0 | None | 0 (0) | 0.0 | None / 61.38 | 24/24 , 24/24 | 0 / 0.0 |
| t7a | 48 | 0 | 5.828 | 21 | 6.09 | 5.931 | 0.282 | 5.885 | 1.0 | 324 (324) | 0.0 | 31.38 / 59.08 | 48/48 , 48/48 | 0 / 0.0 |
| t7b2 | 8 | 0 | 0.904 | 3 | 0.87 | 0.898 | 0.299 | 0.887 | 1.0 | 68 (68) | 0.0 | 28.95 / 41.89 | 0/0 , 0/0 | 0 / 0.0 |

Per request (event = pin->prefill transition by the H1 rule):

| phase | tag | nodraft | prompt_n | pred | event | dKFD GiB | pool_big MiB | mmvq pins |
|---|---|---|---|---|---|---|---|---|
| warm | warm24000 | False | 23917 | 64 |  | 0.921 | 662.4 | 0 |
| warm | warm2500 | False | 2946 | 64 |  | 0.002 | 0.0 | 0 |
| ctrl | mbpp_0391|dflash2 | False | 483 | 41 |  | 0.0 | 0.0 | 0 |
| ctrl | mbpp_0303|dflash2 | False | 243 | 200 |  | 0.031 | 0.0 | 0 |
| ctrl | mbpp_0508|dflash2 | False | 278 | 57 |  | 0.022 | 0.0 | 0 |
| ctrl | bcb_BigCodeBench/547|dflash2 | False | 251 | 88 |  | 0.002 | 0.0 | 0 |
| ctrl | bcb_BigCodeBench/512|dflash2 | False | 329 | 200 |  | 0.002 | 0.0 | 0 |
| ctrl | debugbench_flood-fill_cpp|dflash2 | False | 836 | 200 |  | 0.004 | 0.0 | 0 |
| ctrl | leetcode_the-number-of-the-smallest-unoccupied-chair|dflash2 | False | 777 | 200 |  | 0.002 | 0.0 | 0 |
| ctrl | ma_multi_015|dflash2 | False | 249 | 200 |  | 0.0 | 0.0 | 0 |
| ctrl | gsm8k_00739|dflash2 | False | 244 | 200 |  | 0.0 | 0.0 | 0 |
| ctrl | gsm8k_00115|dflash2 | False | 279 | 200 |  | 0.0 | 0.0 | 0 |
| ctrl | gsm8k_00041|dflash2 | False | 313 | 200 |  | 0.0 | 0.0 | 0 |
| ctrl | gpqa_diamond_cot_5fd3fe9084c9|dflash2 | False | 325 | 200 |  | 0.0 | 0.0 | 0 |
| ctrl | gpqa_diamond_cot_8116937b0ca6|dflash2 | False | 298 | 200 |  | 0.0 | 0.0 | 0 |
| ctrl | phybench_electricity_25|dflash2 | False | 295 | 200 |  | 0.0 | 0.0 | 0 |
| ctrl | mmlu_pro_law_01532|dflash2 | False | 472 | 2 |  | 0.0 | 0.0 | 0 |
| ctrl | mmlu_pro_health_05883|dflash2 | False | 347 | 2 |  | 0.0 | 0.0 | 0 |
| ctrl | ifeval_3456|dflash2 | False | 241 | 200 |  | 0.0 | 0.0 | 0 |
| ctrl | ifeval_322|dflash2 | False | 225 | 9 |  | 0.0 | 0.0 | 0 |
| ctrl | ifeval_1481|dflash2 | False | 273 | 200 |  | 0.0 | 0.0 | 0 |
| ctrl | ifeval_1129|dflash2 | False | 256 | 139 |  | 0.0 | 0.0 | 0 |
| ctrl | real_suite_v1_0003|dflash2 | False | 250 | 200 |  | 0.0 | 0.0 | 0 |
| ctrl | real_suite_v1_0032|dflash2 | False | 264 | 53 |  | 0.0 | 0.0 | 0 |
| ctrl | simpleqa_general_01814|dflash2 | False | 213 | 8 |  | 0.0 | 0.0 | 0 |
| ctrl | hellaswag_06230|dflash2 | False | 259 | 2 |  | 0.0 | 0.0 | 0 |
| t7a | mbpp_0391|dflash2 | False | 483 | 41 |  | -0.004 | 0.0 | 0 |
| t7a | mbpp_0391|nodraft | True | 483 | 41 |  | -0.104 | 0.0 | 239 |
| t7a | mbpp_0303|dflash2 | False | 243 | 200 | **EVENT** | 0.279 | 287.0 | 0 |
| t7a | mbpp_0303|nodraft | True | 243 | 200 |  | 0.0 | 0.0 | 7 |
| t7a | mbpp_0508|dflash2 | False | 278 | 57 | **EVENT** | 0.279 | 287.0 | 0 |
| t7a | mbpp_0508|nodraft | True | 278 | 57 |  | 0.0 | 0.0 | 2 |
| t7a | bcb_BigCodeBench/547|dflash2 | False | 251 | 88 | **EVENT** | 0.281 | 287.0 | 0 |
| t7a | bcb_BigCodeBench/547|nodraft | True | 251 | 88 |  | 0.0 | 0.0 | 7 |
| t7a | bcb_BigCodeBench/512|dflash2 | False | 329 | 200 | **EVENT** | 0.283 | 287.0 | 0 |
| t7a | bcb_BigCodeBench/512|nodraft | True | 329 | 200 |  | 0.0 | 0.0 | 7 |
| t7a | debugbench_flood-fill_cpp|dflash2 | False | 836 | 200 | **EVENT** | 0.283 | 287.0 | 0 |
| t7a | debugbench_flood-fill_cpp|nodraft | True | 836 | 200 |  | 0.0 | 0.0 | 7 |
| t7a | leetcode_the-number-of-the-smallest-unoccupied-chair|dflash2 | False | 777 | 200 | **EVENT** | 0.283 | 287.0 | 0 |
| t7a | leetcode_the-number-of-the-smallest-unoccupied-chair|nodraft | True | 777 | 200 |  | 0.0 | 0.0 | 2 |
| t7a | ma_multi_015|dflash2 | False | 249 | 200 | **EVENT** | 0.283 | 287.0 | 0 |
| t7a | ma_multi_015|nodraft | True | 249 | 200 |  | 0.0 | 0.0 | 7 |
| t7a | gsm8k_00739|dflash2 | False | 244 | 200 | **EVENT** | 0.281 | 287.0 | 0 |
| t7a | gsm8k_00739|nodraft | True | 244 | 200 |  | 0.0 | 0.0 | 7 |
| t7a | gsm8k_00115|dflash2 | False | 279 | 200 | **EVENT** | 0.283 | 287.0 | 0 |
| t7a | gsm8k_00115|nodraft | True | 279 | 200 |  | 0.0 | 0.0 | 2 |
| t7a | gsm8k_00041|dflash2 | False | 313 | 200 | **EVENT** | 0.283 | 287.0 | 0 |
| t7a | gsm8k_00041|nodraft | True | 313 | 200 |  | 0.0 | 0.0 | 2 |
| t7a | gpqa_diamond_cot_5fd3fe9084c9|dflash2 | False | 325 | 200 | **EVENT** | 0.283 | 287.0 | 0 |
| t7a | gpqa_diamond_cot_5fd3fe9084c9|nodraft | True | 325 | 200 |  | 0.0 | 0.0 | 7 |
| t7a | gpqa_diamond_cot_8116937b0ca6|dflash2 | False | 298 | 200 | **EVENT** | 0.283 | 287.0 | 0 |
| t7a | gpqa_diamond_cot_8116937b0ca6|nodraft | True | 298 | 200 |  | 0.0 | 0.0 | 2 |
| t7a | phybench_electricity_25|dflash2 | False | 295 | 200 | **EVENT** | 0.283 | 287.0 | 0 |
| t7a | phybench_electricity_25|nodraft | True | 295 | 200 |  | 0.0 | 0.0 | 2 |
| t7a | mmlu_pro_law_01532|dflash2 | False | 472 | 2 | **EVENT** | 0.283 | 287.0 | 0 |
| t7a | mmlu_pro_law_01532|nodraft | True | 472 | 2 |  | 0.0 | 0.0 | 0 |
| t7a | mmlu_pro_health_05883|dflash2 | False | 347 | 2 |  | 0.0 | 0.0 | 0 |
| t7a | mmlu_pro_health_05883|nodraft | True | 347 | 2 |  | 0.0 | 0.0 | 0 |
| t7a | ifeval_3456|dflash2 | False | 241 | 200 |  | 0.0 | 0.0 | 0 |
| t7a | ifeval_3456|nodraft | True | 241 | 200 |  | 0.0 | 0.0 | 7 |
| t7a | ifeval_322|dflash2 | False | 225 | 9 | **EVENT** | 0.283 | 287.0 | 0 |
| t7a | ifeval_322|nodraft | True | 225 | 9 |  | 0.0 | 0.0 | 2 |
| t7a | ifeval_1481|dflash2 | False | 273 | 200 | **EVENT** | 0.283 | 287.0 | 0 |
| t7a | ifeval_1481|nodraft | True | 273 | 200 |  | 0.0 | 0.0 | 2 |
| t7a | ifeval_1129|dflash2 | False | 256 | 139 | **EVENT** | 0.283 | 287.0 | 0 |
| t7a | ifeval_1129|nodraft | True | 256 | 139 |  | 0.0 | 0.0 | 2 |
| t7a | real_suite_v1_0003|dflash2 | False | 250 | 200 | **EVENT** | 0.283 | 287.0 | 0 |
| t7a | real_suite_v1_0003|nodraft | True | 250 | 200 |  | 0.0 | 0.0 | 7 |
| t7a | real_suite_v1_0032|dflash2 | False | 264 | 53 | **EVENT** | 0.283 | 287.0 | 0 |
| t7a | real_suite_v1_0032|nodraft | True | 264 | 53 |  | 0.0 | 0.0 | 2 |
| t7a | simpleqa_general_01814|dflash2 | False | 213 | 8 | **EVENT** | 0.283 | 287.0 | 0 |
| t7a | simpleqa_general_01814|nodraft | True | 213 | 8 |  | 0.0 | 0.0 | 2 |
| t7a | hellaswag_06230|dflash2 | False | 259 | 2 | **EVENT** | 0.283 | 287.0 | 0 |
| t7a | hellaswag_06230|nodraft | True | 259 | 2 |  | 0.0 | 0.0 | 0 |
| t7b2 | 2000|drafted | False | 2542 | 1500 |  | 0.004 | 0.0 | 0 |
| t7b2 | 2000|nodraft_cached | True | 4 | 1500 |  | 0.0 | 0.0 | 32 |
| t7b2 | 2000|needle | False | 2387 | 17 | **EVENT** | 0.289 | 291.1 | 0 |
| t7b2 | 2000|needle_nodraft | True | 4 | 17 |  | 0.0 | 0.0 | 2 |
| t7b2 | 16000|drafted | False | 15969 | 1500 | **EVENT** | 0.281 | 287.0 | 0 |
| t7b2 | 16000|nodraft_cached | True | 4 | 1500 |  | 0.002 | 0.0 | 32 |
| t7b2 | 16000|needle | False | 15814 | 18 | **EVENT** | 0.328 | 329.7 | 0 |
| t7b2 | 16000|needle_nodraft | True | 4 | 18 |  | 0.0 | 0.0 | 2 |

## armC_fix

- result: {'pid': 1084687, 'load_s': 6.0, 'aborted': None, 'error': None, 'skipped': [], 'peak_own_gib': 51.751, 'soft_ceiling_hit': False, 'extra_env': {}}

| phase | req | non-200 | KFD growth GiB | events | model GiB | KFD in events GiB | per event | shim pool_big GiB | big in events | mmvq pins (in nodraft) | nonpool GiB | tps nodraft / drafted | T7#1 fidelity prompt_n= / pred= | mmvq arena n / MiB |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| warm | 2 | 0 | 0.921 | 0 | 0.0 | 0 | None | 0.647 | 0.0 | 0 (0) | 3.571 | None / 38.54 | 0/0 , 0/0 | 0 / 0.0 |
| t7a | 48 | 0 | 0.057 | 21 | 6.09 | 0.051 | 0.002 | 0.0 | None | 0 (0) | 0.004 | 31.7 / 61.97 | 48/48 , 48/48 | 1 / 4.0 |

Per request (event = pin->prefill transition by the H1 rule):

| phase | tag | nodraft | prompt_n | pred | event | dKFD GiB | pool_big MiB | mmvq pins |
|---|---|---|---|---|---|---|---|---|
| warm | warm24000 | False | 23918 | 64 |  | 0.921 | 662.4 | 0 |
| warm | warm2500 | False | 2945 | 64 |  | 0.0 | 0.0 | 0 |
| t7a | mbpp_0391|dflash2 | False | 483 | 41 |  | 0.002 | 0.0 | 0 |
| t7a | mbpp_0391|nodraft | True | 483 | 41 |  | 0.004 | 0.0 | 0 |
| t7a | mbpp_0303|dflash2 | False | 243 | 200 | **EVENT** | 0.029 | 0.0 | 0 |
| t7a | mbpp_0303|nodraft | True | 243 | 200 |  | 0.0 | 0.0 | 0 |
| t7a | mbpp_0508|dflash2 | False | 278 | 57 | **EVENT** | 0.022 | 0.0 | 0 |
| t7a | mbpp_0508|nodraft | True | 278 | 57 |  | 0.0 | 0.0 | 0 |
| t7a | bcb_BigCodeBench/547|dflash2 | False | 251 | 88 | **EVENT** | 0.0 | 0.0 | 0 |
| t7a | bcb_BigCodeBench/547|nodraft | True | 251 | 88 |  | 0.0 | 0.0 | 0 |
| t7a | bcb_BigCodeBench/512|dflash2 | False | 329 | 200 | **EVENT** | 0.0 | 0.0 | 0 |
| t7a | bcb_BigCodeBench/512|nodraft | True | 329 | 200 |  | 0.0 | 0.0 | 0 |
| t7a | debugbench_flood-fill_cpp|dflash2 | False | 836 | 200 | **EVENT** | 0.0 | 0.0 | 0 |
| t7a | debugbench_flood-fill_cpp|nodraft | True | 836 | 200 |  | 0.0 | 0.0 | 0 |
| t7a | leetcode_the-number-of-the-smallest-unoccupied-chair|dflash2 | False | 777 | 200 | **EVENT** | 0.0 | 0.0 | 0 |
| t7a | leetcode_the-number-of-the-smallest-unoccupied-chair|nodraft | True | 777 | 200 |  | 0.0 | 0.0 | 0 |
| t7a | ma_multi_015|dflash2 | False | 249 | 200 | **EVENT** | 0.0 | 0.0 | 0 |
| t7a | ma_multi_015|nodraft | True | 249 | 200 |  | 0.0 | 0.0 | 0 |
| t7a | gsm8k_00739|dflash2 | False | 244 | 200 | **EVENT** | 0.0 | 0.0 | 0 |
| t7a | gsm8k_00739|nodraft | True | 244 | 200 |  | 0.0 | 0.0 | 0 |
| t7a | gsm8k_00115|dflash2 | False | 279 | 200 | **EVENT** | 0.0 | 0.0 | 0 |
| t7a | gsm8k_00115|nodraft | True | 279 | 200 |  | 0.0 | 0.0 | 0 |
| t7a | gsm8k_00041|dflash2 | False | 313 | 200 | **EVENT** | 0.0 | 0.0 | 0 |
| t7a | gsm8k_00041|nodraft | True | 313 | 200 |  | 0.0 | 0.0 | 0 |
| t7a | gpqa_diamond_cot_5fd3fe9084c9|dflash2 | False | 325 | 200 | **EVENT** | 0.0 | 0.0 | 0 |
| t7a | gpqa_diamond_cot_5fd3fe9084c9|nodraft | True | 325 | 200 |  | 0.0 | 0.0 | 0 |
| t7a | gpqa_diamond_cot_8116937b0ca6|dflash2 | False | 298 | 200 | **EVENT** | 0.0 | 0.0 | 0 |
| t7a | gpqa_diamond_cot_8116937b0ca6|nodraft | True | 298 | 200 |  | 0.0 | 0.0 | 0 |
| t7a | phybench_electricity_25|dflash2 | False | 295 | 200 | **EVENT** | 0.0 | 0.0 | 0 |
| t7a | phybench_electricity_25|nodraft | True | 295 | 200 |  | 0.0 | 0.0 | 0 |
| t7a | mmlu_pro_law_01532|dflash2 | False | 472 | 2 | **EVENT** | 0.0 | 0.0 | 0 |
| t7a | mmlu_pro_law_01532|nodraft | True | 472 | 2 |  | 0.0 | 0.0 | 0 |
| t7a | mmlu_pro_health_05883|dflash2 | False | 347 | 2 |  | 0.0 | 0.0 | 0 |
| t7a | mmlu_pro_health_05883|nodraft | True | 347 | 2 |  | 0.0 | 0.0 | 0 |
| t7a | ifeval_3456|dflash2 | False | 241 | 200 |  | 0.0 | 0.0 | 0 |
| t7a | ifeval_3456|nodraft | True | 241 | 200 |  | 0.0 | 0.0 | 0 |
| t7a | ifeval_322|dflash2 | False | 225 | 9 | **EVENT** | 0.0 | 0.0 | 0 |
| t7a | ifeval_322|nodraft | True | 225 | 9 |  | 0.0 | 0.0 | 0 |
| t7a | ifeval_1481|dflash2 | False | 273 | 200 | **EVENT** | 0.0 | 0.0 | 0 |
| t7a | ifeval_1481|nodraft | True | 273 | 200 |  | 0.0 | 0.0 | 0 |
| t7a | ifeval_1129|dflash2 | False | 256 | 139 | **EVENT** | 0.0 | 0.0 | 0 |
| t7a | ifeval_1129|nodraft | True | 256 | 139 |  | 0.0 | 0.0 | 0 |
| t7a | real_suite_v1_0003|dflash2 | False | 250 | 200 | **EVENT** | 0.0 | 0.0 | 0 |
| t7a | real_suite_v1_0003|nodraft | True | 250 | 200 |  | 0.0 | 0.0 | 0 |
| t7a | real_suite_v1_0032|dflash2 | False | 264 | 53 | **EVENT** | 0.0 | 0.0 | 0 |
| t7a | real_suite_v1_0032|nodraft | True | 264 | 53 |  | 0.0 | 0.0 | 0 |
| t7a | simpleqa_general_01814|dflash2 | False | 213 | 8 | **EVENT** | 0.0 | 0.0 | 0 |
| t7a | simpleqa_general_01814|nodraft | True | 213 | 8 |  | 0.0 | 0.0 | 0 |
| t7a | hellaswag_06230|dflash2 | False | 259 | 2 | **EVENT** | 0.0 | 0.0 | 0 |
| t7a | hellaswag_06230|nodraft | True | 259 | 2 |  | 0.0 | 0.0 | 0 |

## armB_nographs

- result: {'pid': 1136735, 'load_s': 6.0, 'aborted': None, 'error': None, 'skipped': [], 'peak_own_gib': 51.737, 'soft_ceiling_hit': False, 'extra_env': {'GGML_CUDA_DISABLE_GRAPHS': '1'}}

| phase | req | non-200 | KFD growth GiB | events | model GiB | KFD in events GiB | per event | shim pool_big GiB | big in events | mmvq pins (in nodraft) | nonpool GiB | tps nodraft / drafted | T7#1 fidelity prompt_n= / pred= | mmvq arena n / MiB |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| warm | 2 | 0 | 0.918 | 0 | 0.0 | 0 | None | 0.647 | 0.0 | 0 (0) | 3.571 | None / 43.18 | 0/0 , 0/0 | 0 / 0.0 |
| t7a | 48 | 0 | 0.051 | 21 | 6.09 | 0.051 | 0.002 | 0.0 | None | 0 (0) | 0.0 | 29.63 / 61.62 | 48/48 , 48/48 | 0 / 0.0 |

Per request (event = pin->prefill transition by the H1 rule):

| phase | tag | nodraft | prompt_n | pred | event | dKFD GiB | pool_big MiB | mmvq pins |
|---|---|---|---|---|---|---|---|---|
| warm | warm24000 | False | 23921 | 64 |  | 0.918 | 662.4 | 0 |
| warm | warm2500 | False | 2944 | 64 |  | 0.0 | 0.0 | 0 |
| t7a | mbpp_0391|dflash2 | False | 483 | 41 |  | 0.0 | 0.0 | 0 |
| t7a | mbpp_0391|nodraft | True | 483 | 41 |  | 0.0 | 0.0 | 0 |
| t7a | mbpp_0303|dflash2 | False | 243 | 200 | **EVENT** | 0.029 | 0.0 | 0 |
| t7a | mbpp_0303|nodraft | True | 243 | 200 |  | 0.0 | 0.0 | 0 |
| t7a | mbpp_0508|dflash2 | False | 278 | 57 | **EVENT** | 0.022 | 0.0 | 0 |
| t7a | mbpp_0508|nodraft | True | 278 | 57 |  | 0.0 | 0.0 | 0 |
| t7a | bcb_BigCodeBench/547|dflash2 | False | 251 | 88 | **EVENT** | 0.0 | 0.0 | 0 |
| t7a | bcb_BigCodeBench/547|nodraft | True | 251 | 88 |  | 0.0 | 0.0 | 0 |
| t7a | bcb_BigCodeBench/512|dflash2 | False | 329 | 200 | **EVENT** | 0.0 | 0.0 | 0 |
| t7a | bcb_BigCodeBench/512|nodraft | True | 329 | 200 |  | 0.0 | 0.0 | 0 |
| t7a | debugbench_flood-fill_cpp|dflash2 | False | 836 | 200 | **EVENT** | 0.0 | 0.0 | 0 |
| t7a | debugbench_flood-fill_cpp|nodraft | True | 836 | 200 |  | 0.0 | 0.0 | 0 |
| t7a | leetcode_the-number-of-the-smallest-unoccupied-chair|dflash2 | False | 777 | 200 | **EVENT** | 0.0 | 0.0 | 0 |
| t7a | leetcode_the-number-of-the-smallest-unoccupied-chair|nodraft | True | 777 | 200 |  | 0.0 | 0.0 | 0 |
| t7a | ma_multi_015|dflash2 | False | 249 | 200 | **EVENT** | 0.0 | 0.0 | 0 |
| t7a | ma_multi_015|nodraft | True | 249 | 200 |  | 0.0 | 0.0 | 0 |
| t7a | gsm8k_00739|dflash2 | False | 244 | 200 | **EVENT** | 0.0 | 0.0 | 0 |
| t7a | gsm8k_00739|nodraft | True | 244 | 200 |  | 0.0 | 0.0 | 0 |
| t7a | gsm8k_00115|dflash2 | False | 279 | 200 | **EVENT** | 0.0 | 0.0 | 0 |
| t7a | gsm8k_00115|nodraft | True | 279 | 200 |  | 0.0 | 0.0 | 0 |
| t7a | gsm8k_00041|dflash2 | False | 313 | 200 | **EVENT** | 0.0 | 0.0 | 0 |
| t7a | gsm8k_00041|nodraft | True | 313 | 200 |  | 0.0 | 0.0 | 0 |
| t7a | gpqa_diamond_cot_5fd3fe9084c9|dflash2 | False | 325 | 200 | **EVENT** | 0.0 | 0.0 | 0 |
| t7a | gpqa_diamond_cot_5fd3fe9084c9|nodraft | True | 325 | 200 |  | 0.0 | 0.0 | 0 |
| t7a | gpqa_diamond_cot_8116937b0ca6|dflash2 | False | 298 | 200 | **EVENT** | 0.0 | 0.0 | 0 |
| t7a | gpqa_diamond_cot_8116937b0ca6|nodraft | True | 298 | 200 |  | 0.0 | 0.0 | 0 |
| t7a | phybench_electricity_25|dflash2 | False | 295 | 200 | **EVENT** | 0.0 | 0.0 | 0 |
| t7a | phybench_electricity_25|nodraft | True | 295 | 200 |  | 0.0 | 0.0 | 0 |
| t7a | mmlu_pro_law_01532|dflash2 | False | 472 | 2 | **EVENT** | 0.0 | 0.0 | 0 |
| t7a | mmlu_pro_law_01532|nodraft | True | 472 | 2 |  | 0.0 | 0.0 | 0 |
| t7a | mmlu_pro_health_05883|dflash2 | False | 347 | 2 |  | 0.0 | 0.0 | 0 |
| t7a | mmlu_pro_health_05883|nodraft | True | 347 | 2 |  | 0.0 | 0.0 | 0 |
| t7a | ifeval_3456|dflash2 | False | 241 | 200 |  | 0.0 | 0.0 | 0 |
| t7a | ifeval_3456|nodraft | True | 241 | 200 |  | 0.0 | 0.0 | 0 |
| t7a | ifeval_322|dflash2 | False | 225 | 9 | **EVENT** | 0.0 | 0.0 | 0 |
| t7a | ifeval_322|nodraft | True | 225 | 9 |  | 0.0 | 0.0 | 0 |
| t7a | ifeval_1481|dflash2 | False | 273 | 200 | **EVENT** | 0.0 | 0.0 | 0 |
| t7a | ifeval_1481|nodraft | True | 273 | 200 |  | 0.0 | 0.0 | 0 |
| t7a | ifeval_1129|dflash2 | False | 256 | 139 | **EVENT** | 0.0 | 0.0 | 0 |
| t7a | ifeval_1129|nodraft | True | 256 | 139 |  | 0.0 | 0.0 | 0 |
| t7a | real_suite_v1_0003|dflash2 | False | 250 | 200 | **EVENT** | 0.0 | 0.0 | 0 |
| t7a | real_suite_v1_0003|nodraft | True | 250 | 200 |  | 0.0 | 0.0 | 0 |
| t7a | real_suite_v1_0032|dflash2 | False | 264 | 53 | **EVENT** | 0.0 | 0.0 | 0 |
| t7a | real_suite_v1_0032|nodraft | True | 264 | 53 |  | 0.0 | 0.0 | 0 |
| t7a | simpleqa_general_01814|dflash2 | False | 213 | 8 | **EVENT** | 0.0 | 0.0 | 0 |
| t7a | simpleqa_general_01814|nodraft | True | 213 | 8 |  | 0.0 | 0.0 | 0 |
| t7a | hellaswag_06230|dflash2 | False | 259 | 2 | **EVENT** | 0.0 | 0.0 | 0 |
| t7a | hellaswag_06230|nodraft | True | 259 | 2 |  | 0.0 | 0.0 | 0 |

