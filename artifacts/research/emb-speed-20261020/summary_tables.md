# Embedder speed pilot (timing screen only; NO retrieval-quality claim)

Claim: region-lock q1+q2 = CPUs 24-71 (48 physical cores, NUMA nodes 1-2; SMT siblings excluded). OMP_PROC_BIND=spread OMP_PLACES=cores OMP_WAIT_POLICY=active. CPU: AMD EPYC 9655.

## Load, RSS, params, tokens

| model | dtype | params(M) | load s | RSS delta MB | tokens/chunk |
|---|---|---|---|---|---|
| bge | torch.float32 | 335 | 0.10 | 35 | 216 |
| eg2_fp32 | torch.float32 | 744 | 1.46 | 3161 | 222 |
| eg2_bf16 | torch.bfloat16 | 744 | 1.36 | 268 | 222 |
| potion_code | float32/static | 0 | 0.09 | 31 | 198 |
| potion_base | float32/static | 0 | 0.04 | 29 | 216 |

(EG2 checkpoint loaded through sentence-transformers includes non-text towers; params/RSS are for the whole loaded module, only text path is run. Static-model RSS is file-backed/mmap and also small.)

## Encode throughput (documents) median of 3 timed reps, chunks/s (tokens/s); spread = (max-min)/median

| model | batch | threads | n chunks | chunks/s | tokens/s | spread % | contaminated? |
|---|---|---|---|---|---|---|---|
| bge | 1 | 1 | 16 | 0.9 | 173 | 0.1 | no |
| bge | 8 | 1 | 16 | 0.5 | 96 | 59.0 | no |
| bge | 32 | 1 | 16 | 0.6 | 123 | 44.2 | no |
| bge | 128 | 1 | 16 | 0.5 | 95 | 3.9 | no |
| bge | 8 | 16 | 256 | 5.1 | 1069 | 6.0 | POSSIBLY CONTAMINATED |
| bge | 32 | 16 | 256 | 4.5 | 932 | 7.4 | POSSIBLY CONTAMINATED |
| bge | 128 | 16 | 256 | 4.3 | 890 | 3.1 | POSSIBLY CONTAMINATED |
| bge | 1 | 4 | 64 | 1.6 | 305 | 55.3 | POSSIBLY CONTAMINATED |
| bge | 8 | 4 | 256 | 1.5 | 323 | 26.5 | POSSIBLY CONTAMINATED |
| bge | 32 | 4 | 128 | 1.2 | 246 | 25.8 | POSSIBLY CONTAMINATED |
| bge | 8 | 48 | 256 | 12.9 | 2696 | 7.1 | POSSIBLY CONTAMINATED |
| bge | 32 | 48 | 256 | 13.0 | 2721 | 1.1 | POSSIBLY CONTAMINATED |
| bge_b | 32 | 16 | 256 | 4.7 | 976 | 4.4 | POSSIBLY CONTAMINATED |
| eg2_bf16 | 1 | 1 | 16 | 4.8 | 959 | 1.5 | no |
| eg2_bf16 | 8 | 1 | 16 | 2.7 | 538 | 86.2 | no |
| eg2_bf16 | 32 | 1 | 16 | 2.6 | 527 | 62.5 | no |
| eg2_bf16 | 128 | 1 | 16 | 2.6 | 514 | 3.6 | no |
| eg2_bf16 | 8 | 16 | 256 | 24.2 | 5232 | 13.9 | POSSIBLY CONTAMINATED |
| eg2_bf16 | 32 | 16 | 256 | 19.9 | 4306 | 19.9 | POSSIBLY CONTAMINATED |
| eg2_bf16 | 128 | 16 | 256 | 21.0 | 4541 | 13.9 | POSSIBLY CONTAMINATED |
| eg2_bf16 | 1 | 4 | 64 | 9.3 | 1916 | 49.2 | POSSIBLY CONTAMINATED |
| eg2_bf16 | 8 | 4 | 256 | 7.4 | 1609 | 5.1 | POSSIBLY CONTAMINATED |
| eg2_bf16 | 32 | 4 | 128 | 7.0 | 1497 | 14.3 | POSSIBLY CONTAMINATED |
| eg2_bf16 | 8 | 48 | 256 | 31.2 | 6735 | 4.0 | POSSIBLY CONTAMINATED |
| eg2_bf16 | 32 | 48 | 256 | 41.7 | 9016 | 3.6 | POSSIBLY CONTAMINATED |
| eg2_fp32 | 1 | 1 | 16 | 1.7 | 347 | 0.8 | no |
| eg2_fp32 | 8 | 1 | 16 | 1.0 | 202 | 60.6 | no |
| eg2_fp32 | 32 | 1 | 16 | 1.0 | 192 | 69.3 | no |
| eg2_fp32 | 128 | 1 | 16 | 1.0 | 196 | 3.8 | no |
| eg2_fp32 | 8 | 16 | 256 | 8.9 | 1929 | 14.7 | POSSIBLY CONTAMINATED |
| eg2_fp32 | 32 | 16 | 256 | 8.5 | 1836 | 20.5 | POSSIBLY CONTAMINATED |
| eg2_fp32 | 128 | 16 | 256 | 8.6 | 1863 | 14.1 | POSSIBLY CONTAMINATED |
| eg2_fp32 | 1 | 4 | 64 | 2.6 | 534 | 57.6 | POSSIBLY CONTAMINATED |
| eg2_fp32 | 8 | 4 | 256 | 2.4 | 522 | 10.1 | POSSIBLY CONTAMINATED |
| eg2_fp32 | 32 | 4 | 128 | 2.7 | 579 | 23.2 | POSSIBLY CONTAMINATED |
| eg2_fp32 | 8 | 48 | 256 | 15.7 | 3386 | 8.4 | POSSIBLY CONTAMINATED |
| eg2_fp32 | 32 | 48 | 256 | 20.7 | 4481 | 7.4 | POSSIBLY CONTAMINATED |
| potion_base | 8 | n/a(single) | 4096 | 2680.5 | 579725 | 8.1 | POSSIBLY CONTAMINATED |
| potion_base | 32 | n/a(single) | 4096 | 2764.9 | 597977 | 102.8 | POSSIBLY CONTAMINATED |
| potion_base | 128 | n/a(single) | 4096 | 2617.8 | 566167 | 18.1 | POSSIBLY CONTAMINATED |
| potion_code | 8 | n/a(single) | 4096 | 2153.4 | 425706 | 4.5 | POSSIBLY CONTAMINATED |
| potion_code | 32 | n/a(single) | 4096 | 3895.4 | 770076 | 15.2 | POSSIBLY CONTAMINATED |
| potion_code | 128 | n/a(single) | 4096 | 1960.0 | 387465 | 7.6 | POSSIBLY CONTAMINATED |

Subsets: threads=1 -> 16 chunks, batch=1 -> 64 chunks, otherwise 256 chunks (fixed prefix of the 4,096-chunk corpus); model2vec rows use all 4,096 and are single-threaded.

## A/A noise floor (BGE vs BGE again, batch32 x16 threads, interleaved): 4.46 vs 4.67 chunks/s => 4.7% (unit: percent of chunks/s). Rep-to-rep spreads in the table above are the other floor estimate. Differences below the larger of these are not distinguishable.

## Single-query latency (200 queries x 3 reps, batch 1), ms

| model | threads | p50 | p95 | max (median over reps) | contaminated? |
|---|---|---|---|---|---|
| bge | 4 | 103.35 | 155.61 | 231.0 | POSSIBLY CONTAMINATED |
| eg2_bf16 | 4 | 41.31 | 55.02 | 120.3 | POSSIBLY CONTAMINATED |
| eg2_fp32 | 4 | 64.44 | 98.69 | 167.7 | POSSIBLY CONTAMINATED |
| bge | 16 | 65.10 | 83.91 | 172.5 | POSSIBLY CONTAMINATED |
| eg2_bf16 | 16 | 32.04 | 43.34 | 105.5 | POSSIBLY CONTAMINATED |
| eg2_fp32 | 16 | 48.73 | 66.37 | 134.2 | POSSIBLY CONTAMINATED |

## Index build, 4,096 chunks at best (batch>1, threads) config per model

| model | batch | threads | wall s (reps) | chunks/s |
|---|---|---|---|---|
| potion_code | 128 | single | 2.0 | 2046.4 |
| potion_base | 128 | single | 1.4 | 2836.4 |
| bge | 32 | 48 | 399.9, 316.1 | 11.6 |
| eg2_fp32 | 32 | 48 | 214.6, 224.6 | 18.7 |
| eg2_bf16 | 32 | 48 | 113.7, 109.6 | 36.7 |

- sanity: {'phase': 'sanity', 'model': 'bge', 'dim': 1024, 'finite': True, 'norm_min': 0.9999998807907104, 'norm_max': 1.0000001192092896}

- sanity: {'phase': 'sanity', 'model': 'eg2_fp32', 'dim': 768, 'finite': True, 'norm_min': 0.9999998807907104, 'norm_max': 1.0000001192092896}

- sanity: {'phase': 'sanity', 'model': 'eg2_bf16', 'dim': 768, 'finite': True, 'norm_min': 0.9980469942092896, 'norm_max': 1.0038959980010986}

- sanity: {'phase': 'sanity', 'model': 'potion_code', 'dim': 256, 'finite': True, 'norm_min': 0.9999999403953552, 'norm_max': 1.0000001192092896}

- sanity: {'phase': 'sanity', 'model': 'potion_base', 'dim': 256, 'finite': True, 'norm_min': 0.9999999403953552, 'norm_max': 1.0000001192092896}

- sanity: {'phase': 'sanity_bf16_vs_fp32', 'cos_mean': 0.999967634677887, 'cos_min': 0.9999218583106995, 'n': 200}

- sanity: {'phase': 'sanity_mrl256', 'dim': 256, 'norm_min': 0.9999998807907104, 'norm_max': 1.0, 'finite': True}
## Headline re-time at end (ABA, GPU queue still busy; 48 threads batch 32, 256 chunks; queries 200x3)

| model | chunks/s (median, spread%) | q p50/p95 ms @4thr | q p50/p95 ms @16thr | gpu_use at legs |
|---|---|---|---|---|
| bge | 12.0 (22%) | 130.0/199.9 | 68.9/95.1 | [0, 8, 66, 76, 99, 100] |
| eg2_fp32 | 18.5 (11%) | 79.1/130.0 | 53.3/68.1 | [0, 19, 81, 86, 99, 100] |
| eg2_bf16 | 41.8 (13%) | 52.7/71.0 | 33.3/41.5 | [0, 4, 85, 88, 89, 95, 98, 99, 100] |