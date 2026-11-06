# Local launch matrix — analysis

Generated: 2026-11-06T16:04:20Z

> `cpu_code_*_28k` arms are invalid for throughput: the concatenated code prompt ended at a boundary that made the model emit EOS on the first token (`predicted_n=1`, 1e6 sentinel). They remain in `SUMMARY.md`/raw `runs/` but are excluded from the ranking below.

## CPU

| rank | arm | np | ctx | thr | KV | unified | spec | prompt_n | tok/s | mean | accept | NUMA dev% |
|---:|---|---:|---:|---:|---|---|---|---:|---|---:|---:|---:|
| 1 | cpu_ref_8k_t48 | 1 | 8192 | 48 | f16 | False | draft-mtp n4 | [127] | [46.977] | 46.977 | 0.78947 | 2.91 |
| 2 | cpu_code_t48_mtp_16k | 4 | 262144 | 48 | f16 | False | draft-mtp n4 | [14089, 4] | [29.371] | 29.371 | 0.94712 | 5.93 |
| 3 | cpu_code_t48_mtp_8k | 4 | 262144 | 48 | f16 | False | draft-mtp n4 | [7167, 4] | [29.35] | 29.35 | 0.85981 | 5.86 |
| 4 | cpu_champ_t48_32k | 4 | 262144 | 48 | f16 | False | draft-mtp n4 | [27781, 4] | [16.069] | 16.069 | 0.37097 | 5.18 |
| 5 | cpu_champ_t96_50k | 4 | 262144 | 96 | f16 | False | draft-mtp n4 | [54329, 4] | [16.049] | 16.049 | 0.75238 | 7.03 |
| 6 | cpu_champ_t96_np1_32k | 1 | 65536 | 96 | f16 | False | draft-mtp n4 | [27781, 4] | [15.794] | 15.794 | 0.46154 | 3.52 |
| 7 | cpu_champ_t96_unified_32k | 4 | 262144 | 96 | f16 | True | draft-mtp n4 | [27781, 4] | [15.232] | 15.232 | 0.48361 | 5.0 |
| 8 | cpu_champ_t96_32k | 4 | 262144 | 96 | f16 | False | draft-mtp n4 | [27781, 4] | [15.189] | 15.189 | 0.48361 | 5.2 |
| 9 | cpu_fa_t96_32k | 4 | 262144 | 96 | f16 | False | draft-mtp n4 | [27781, 4] | [15.153] | 15.153 | 0.60606 | 5.34 |
| 10 | cpu_champ_t96_kvq8_32k | 4 | 262144 | 96 | q8_0 | False | draft-mtp n4 | [27781, 4] | [15.115] | 15.115 | 0.56818 | 4.46 |
| 11 | cpu_champ_t48_nomtp_50k | 4 | 262144 | 48 | f16 | False | none n4 | [54329, 4] | [15.066] | 15.066 |  | 5.74 |
| 12 | cpu_champ_t96_nomtp_32k | 4 | 262144 | 96 | f16 | False | none n4 | [27781, 4] | [14.95] | 14.95 |  | 4.23 |
| 13 | cpu_champ_t48_np1_50k | 1 | 65536 | 48 | f16 | False | draft-mtp n4 | [54329, 4] | [14.875] | 14.875 | 0.65865 | 4.87 |
| 14 | cpu_fa_t48_32k | 4 | 262144 | 48 | f16 | False | draft-mtp n4 | [27781, 4] | [14.735] | 14.735 | 0.45726 | 5.14 |
| 15 | cpu_champ_t96_np1_50k | 1 | 65536 | 96 | f16 | False | draft-mtp n4 | [54329, 4] | [14.518] | 14.518 | 0.59259 | 5.54 |
| 16 | cpu_champ_t48_50k | 4 | 262144 | 48 | f16 | False | draft-mtp n4 | [54329, 4] | [14.292] | 14.292 | 0.61233 | 6.21 |
| 17 | cpu_champ_t96_nomtp_50k | 4 | 262144 | 96 | f16 | False | none n4 | [54329, 4] | [12.861] | 12.861 |  | 6.3 |
| 18 | cpu_champ_t96_np1_nomtp_50k | 1 | 65536 | 96 | f16 | False | none n4 | [54329, 4] | [12.752] | 12.752 |  | 4.96 |

Raw max (not a cross-prompt/context comparison): **cpu_ref_8k_t48** at **46.977 tok/s**. The 8k, 28k prose, 55k prose and code-prompt rows are different workloads; use the progress entry for the like-for-like calls.

## GPU

| rank | arm | np | ctx | thr | KV | unified | spec | prompt_n | tok/s | mean | accept | NUMA dev% |
|---:|---|---:|---:|---:|---|---|---|---:|---|---:|---:|---:|
| 1 | gpu_ref_np1_16k | 1 | 16384 | 8 | f16 | False | draft-dflash n8 | [1853] | [71.057] | 71.057 | 0.63992 | 39.98 |
| 2 | gpu_np2_262k_f16_n8_50k | 2 | 262144 | 8 | f16 | False | draft-dflash n8 | [54329, 4] | [43.771] | 43.771 | 0.44037 | 36.74 |
| 3 | gpu_np4_262k_f16_n8_50k | 4 | 262144 | 8 | f16 | False | draft-dflash n8 | [54329, 4] | [43.557] | 43.557 | 0.44037 | 35.39 |
| 4 | gpu_np4_262k_f16_n7_50k | 4 | 262144 | 8 | f16 | False | draft-dflash n7 | [54329, 4] | [43.497] | 43.497 | 0.44037 | 35.43 |
| 5 | gpu_np1_64k_node1_50k | 1 | 65536 | 8 | f16 | False | draft-dflash n8 | [54329, 4] | [43.164] | 43.164 | 0.44988 | 55.05 |
| 6 | gpu_np1_196k_f16_n8_50k | 1 | 196608 | 8 | f16 | False | draft-dflash n8 | [54329, 4] | [43.047] | 43.047 | 0.44988 | 39.22 |
| 7 | gpu_np1_64k_f16_n8_50k | 1 | 65536 | 8 | f16 | False | draft-dflash n8 | [54329, 4] | [42.764] | 42.764 | 0.44988 | 36.84 |
| 8 | gpu_np4_262k_q8_n7_prod_50k | 4 | 262144 | 8 | q8_0 | True | draft-dflash n7 | [54329, 4] | [41.854] | 41.854 | 0.45972 | 40.41 |
| 9 | gpu_np4_262k_q8_n7_50k | 4 | 262144 | 8 | q8_0 | False | draft-dflash n7 | [54329, 4] | [40.136] | 40.136 | 0.44037 | 35.44 |

Raw max (not a cross-prompt/context comparison): **gpu_ref_np1_16k** at **71.057 tok/s**. The 8k, 28k prose, 55k prose and code-prompt rows are different workloads; use the progress entry for the like-for-like calls.

