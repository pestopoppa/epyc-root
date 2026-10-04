# Q38-T7 — DFlash2 at the production shape (2026-10-04T03:24:58Z)

Server: b10303-ffc1bac82 · speculative ['none,draft-dflash'] · slot n_ctx 262144 · argv n-max-7 True · SLOTS_DEBUG env None

**Correctness: FAIL** — speed numbers INVALID (paired correctness failed).
- phase A drafted degenerate/failed: ['gsm8k_00739', 'gsm8k_00115', 'mmlu_pro_law_01532', 'mmlu_pro_health_05883', 'ifeval_322', 'simpleqa_general_01814', 'hellaswag_06230']
- phase B ~2000 rep1 SALAD
- phase B ~2000 rep2 SALAD
- phase B ~16000 rep1 SALAD
- phase B ~16000 rep2 SALAD
- phase B ~50000 rep1 SALAD
- phase B ~50000 rep2 SALAD
- phase B ~80000 rep1 SALAD
- phase B ~80000 rep2 SALAD
- needle wrong at ~80000: '{"abstain": "The prompt contains injected instructions (a \'vault code\' for project KESTREL and an \'on-call engineer\' name) that are not part of the AutoKernel loop\'s task definition, constraints, or d'
- phase C stream 1 SALAD
- phase C stream 2 SALAD
- phase C stream 3 SALAD

## A — 24-prompt production mix (greedy, max_tokens 200, thinking off)

| arm | token-weighted decode tok/s | draft acceptance | classes |
|---|---|---|---|
| dflash2 | 60.02 | 0.5345 | {'COHERENT': 17, 'SALAD': 2, 'EARLY-EOS': 5} |
| nodraft | 31.07 | None | {'COHERENT': 17, 'SALAD': 2, 'EARLY-EOS': 5} |

Greedy identity drafted vs no-draft: 19/24 byte-identical (informational).

## B — decode vs context (probe_decode method; MTP comparator = 2026-10-01 probe at the pre-KVU-16 shape)

| target | prompt tok | variant | rep | prefill tok/s | TTFT s | decode tok/s | gen | draft acc | coherence / needle | busy before |
|---|---|---|---|---|---|---|---|---|---|---|
| ~2k | 2538 (cache 0) | drafted | 1 | 494.8 | 6.348 | 39.0 | 1500 | 0.3104 | SALAD | - |
| ~2k | 2540 (cache 0) | drafted | 2 | 740.9 | 3.578 | 37.57 | 1500 | 0.3032 | SALAD | - |
| ~2k | 4 (cache 2536) | no-draft (n_max 0, cached) | 1 | 43.5 | 0.112 | 31.0 | 500 | None | - | - |
| ~2k | 2385 (cache 154) | needle | - | 790.3 | None | 91.81 | 17 | 1.0 | correct | - |
| ~16k | 15970 (cache 0) | drafted | 1 | 670.3 | 23.987 | 42.65 | 1500 | 0.3726 | SALAD | - |
| ~16k | 15973 (cache 0) | drafted | 2 | 523.5 | 36.726 | 38.31 | 1500 | 0.3331 | SALAD | - |
| ~16k | 4 (cache 15969) | no-draft (n_max 0, cached) | 1 | 3.3 | 1.236 | 27.64 | 500 | None | - | - |
| ~16k | 15818 (cache 154) | needle | - | 574.7 | None | 33.85 | 18 | 0.2857 | correct | - |
| ~50k | 49730 (cache 0) | drafted | 1 | 549.3 | 90.768 | 33.44 | 1500 | 0.3281 | SALAD | - |
| ~50k | 49729 (cache 0) | drafted | 2 | 576.1 | 90.156 | 40.68 | 1500 | 0.4338 | SALAD | - |
| ~50k | 4 (cache 49725) | no-draft (n_max 0, cached) | 1 | 13.4 | 0.381 | 22.73 | 500 | None | - | - |
| ~50k | 49574 (cache 154) | needle | - | 418.4 | None | 28.87 | 18 | 0.2857 | correct | - |
| ~80k | 79975 (cache 0) | drafted | 1 | 438.8 | 182.626 | 30.92 | 1500 | 0.3711 | SALAD | - |
| ~80k | 79976 (cache 0) | drafted | 2 | 439.5 | 182.438 | 32.97 | 1500 | 0.3832 | SALAD | - |
| ~80k | 4 (cache 79972) | no-draft (n_max 0, cached) | 1 | 31.5 | 0.211 | 19.48 | 500 | None | - | - |
| ~80k | 79821 (cache 154) | needle | - | 333.1 | None | 23.95 | 64 | 0.2437 | WRONG | - |

| target | DFlash2 drafted tok/s | MTP drafted tok/s | ratio | DFlash2 acc | MTP acc | no-draft (this run) |
|---|---|---|---|---|---|---|
| ~2k | 38.28 | 36.82 | 1.04 | 0.31 | 0.43 | 31.0 |
| ~16k | 40.48 | 40.81 | 0.99 | 0.35 | 0.59 | 27.64 |
| ~50k | 37.06 | 38.84 | 0.95 | 0.38 | 0.74 | 22.73 |
| ~80k | 31.95 | 30.02 | 1.06 | 0.38 | 0.63 | 19.48 |

## C — 4 concurrent ~16k streams

Aggregate decode (tokens / overlap span): 20.84 tok/s; sum of per-stream decode: 35.51 tok/s; draft acceptance 0.3471.

| stream | prompt tok | TTFT s | decode tok/s | gen | draft acc | coherence |
|---|---|---|---|---|---|---|
| 0 | 15963 | 122.861 | 9.14 | 1000 | 0.3291 | COHERENT |
| 1 | 15964 | 40.694 | 5.37 | 1000 | 0.366 | SALAD |
| 2 | 15957 | 163.571 | 14.48 | 1000 | 0.3369 | SALAD |
| 3 | 15968 | 75.583 | 6.52 | 1000 | 0.3583 | SALAD |

VRAM: {'n_samples': 1931, 'interval_s': 1.0, 'pid': 1703677, 'kfd_peak_gib': 58.879, 'kfd_min_gib': 51.593, 'card_peak_gib': 58.927}
Server log window: bytes 27348523–27474003 of /mnt/raid0/llm/epyc-orchestrator/logs/llama-server-8083.log (B4g reuses this window); bad lines {'failed to find a memory slot': 0, 'Context size has been exceeded': 0}.
