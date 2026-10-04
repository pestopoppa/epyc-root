# GPU slot gpu-slot-ak-20261004: KVU-16b replay (fixed predicate) + P3v2, KVU-19a+19b build

> **Attribution tag: every skip-ON arm is `19a+19b-combined (incl. commit 2)` (build c7f5ac9ad).** Commit 2 (WMMA seq tiles) is NOT in the KVU-19 fold (19a + commit 1 only) and regresses aligned 4x8 verify ~14%; do not attribute skip-ON numbers to the fold. Skip-OFF arms (MASK_SKIP=0 SEQ_ROWS=0) are the production-equivalent v10 path and carry the `-b 512` stack-change evidence.

Results `/mnt/raid0/llm/tmp/gpu-slot-ak-20261004/results/20261004T050808Z`. Build dir `/mnt/raid0/llm/kernels/builds/gpu-20261004-c7f5ac9ad/bin`; scratch port :18183; budget 93.0 min; value order `kvu_off_b2048,kvu_off_b512,kvu_on_b2048,kvu_on_b512,p3`; started 2026-10-04T05:08:09Z, finished 2026-10-04T06:20:04Z (71.9 min).

- server build_info `b10312-c7f5ac9ad`; argv source {'source': '/mnt/raid0/llm/epyc-orchestrator/logs/server_launches/8083.json (launch 2026-10-04T02:48:09.776Z, pid 1703677, argv_sha256 b865820d557f)', 'sha256': 'b865820d557feac6a513e47324f0f58b4d60cb98275b2b2db6c1aca9f199ad64'}
- argv transforms: binary /mnt/raid0/llm/kernels/builds/gpu-20260921-ffc1bac82/bin/llama-server -> /mnt/raid0/llm/kernels/builds/gpu-20261004-c7f5ac9ad/bin/llama-server; source launch prefix 'numactl --membind=3 -- taskset -c 184-191' -> PREFIX 'numactl --membind=3 -- taskset -c 184-191'; --port 8083 -> 18183; --slot-save-path /mnt/raid0/llm/cache/kv_slots/architect_critic -> /mnt/raid0/llm/tmp/gpu-slot-ak-20261004/results/20261004T050808Z/kvu_on_b2048/slots; -b (absent) -> 2048; -lv (absent) -> 4

## Timeline (value order, caps)

| item | status | verdict | rc | wall min | replay cap min | note |
|---|---|---|---|---|---|---|
| kvu_off_b2048 | ok | CAPPED | 0 | 20.56 | 20.0 |  |
| kvu_off_b512 | ok | CAPPED | 0 | 21.55 | 20.0 |  |
| kvu_on_b2048 | ok | PASS | 0 | 14.21 | 20.0 |  |
| kvu_on_b512 | ok | PASS | 0 | 15.61 | 20.0 |  |
| p3 pair1 | skipped | - | - | - | - | budget: 21.1 min left < 31.5 for an ON+OFF pair |
| p3 pair2 | skipped | - | - | - | - | budget: 21.1 min left < 31.5 for an ON+OFF pair |

## KVU-16b replay: 4 x ~80k staggered, fixed decoding predicate

| metric | original (v10, no skip, b2048, broken predicate) | kvu_on_b2048 | kvu_off_b2048 | kvu_on_b512 |
|---|---|---|---|---|
| env / -b -ub | v10 / 2048 2048 | skip on / 2048 2048 | skip off / 2048 2048 | skip on / 512 512 |
| live knobs | - | {'LD_LIBRARY_PATH': '/mnt/raid0/llm/kernels/builds/gpu-20261004-c7f5ac9ad/bin:/opt/rocm/lib'} | {'GGML_CUDA_FA_MASK_SKIP': '0', 'GGML_CUDA_FA_SEQ_ROWS': '0', 'LD_LIBRARY_PATH': '/mnt/raid0/llm/kernels/builds/gpu-20261004-c7f5ac9ad/bin:/opt/rocm/lib'} | {'LD_LIBRARY_PATH': '/mnt/raid0/llm/kernels/builds/gpu-20261004-c7f5ac9ad/bin:/opt/rocm/lib'} |
| verdict | PASS (invalid) | PASS | CAPPED | PASS |
| wall s (capped?) | 1690.5 | 781.2 (False) | 1222.7 (True) | 926.1 (False) |
| TTFT own-send s, req 0..3 | 181.4, 343.6, 544.6, never | [165.9, 164.8, 175.2, 178.1] | [154.2, 316.0, 526.7, None] | [163.9, 195.1, 238.0, 232.7] |
| first token since t0 s | [181.4, 525.1, 1069.7, None] | [165.9, 330.7, 505.9, 684.1] | [154.2, 470.2, 997.0, None] | [163.9, 359.0, 597.0, 829.7] |
| max requests decoding at once | 3 (true; reported 4) | 4 | 3 | 4 |
| max resident tokens | 310461 | 322505 | 267643 | 325556 |
| max resident while all 4 decode | - (invalid) | 322435 | 0 | 325485 |
| decode tok/s per req, all decoding | {'0': 0.0, '1': 0.16, '2': 0.22, '3': 0.14} | {'2': 7.95, '1': 7.83, '0': 9.0, '3': 8.28} | {} | {'2': 7.67, '1': 9.66, '0': 10.67, '3': 8.82} |
| KFD peak GiB (replay sampler) | 58.88 | 51.71 | 51.69 | 48.59 |
| KFD own peak GiB (arm, 1 Hz, load..teardown) | - | 51.71 | 51.69 | 48.59 |
| KFD own at healthy / after replay GiB | 51.69 / 58.88 | 50.77 / 51.71 | 50.77 / 51.69 | 47.81 / 48.59 |
| bad log lines | {'failed to find a memory slot': 0, 'Context size has been exceeded': 0} | {'failed to find a memory slot': 0, 'Context size has been exceeded': 0} | {'failed to find a memory slot': 0, 'Context size has been exceeded': 0} | {'failed to find a memory slot': 0, 'Context size has been exceeded': 0} |
| request -> slot/task (log agrees?) | i0:s1 i1:s2 i2:s3 i3:s0 | i0:s2/t34 i1:s1/t115 i2:s0/t197 i3:s3/t280 | i0:s2/t34 i1:s1/t115 i2:s0/t197 i3:s3/t280 | i0:s2/t34 i1:s1/t259 i2:s0/t494 i3:s3/t740 |
| coherence sha | - | 821d2f3d3a563435 | 821d2f3d3a563435 | 821d2f3d3a563435 |

## Seconds per server iteration (one prefill chunk) vs occupied cells

Median s/iteration [mean chunk tokens, mean decoders] per 40k bucket of occupied cells D (prefilling slot's processed + every decoding request's prompt + generated), from the per-iteration prompt_progress events; `s/2048` normalises the chunk to 2048 tokens. Original = REPORT.md §1 (v10, no skip, b2048).

| D (k cells) | original s/2048 | kvu_on_b2048 s/iter [chunk, dec] | kvu_on_b2048 s/2048 | kvu_off_b2048 s/iter [chunk, dec] | kvu_off_b2048 s/2048 | kvu_on_b512 s/iter [chunk, dec] | kvu_on_b512 s/2048 |
|---|---|---|---|---|---|---|---|
| 0-40 | 3.81 | 3.165 [2048, 0] | 3.17 | 2.994 [2048, 0] | 2.99 | 0.838 [512, 0] | 3.35 |
| 40-80 | 5.67 | 4.773 [1950, 0] | 4.89 | 4.747 [1950, 0] | 4.83 | 1.25 [506, 0] | 5.04 |
| 80-120 | 7.92 | 3.235 [2040, 1] | 3.25 | 6.943 [2040, 1] | 6.97 | 1.009 [504, 1] | 4.1 |
| 120-160 | 9.84 | 4.992 [1851, 1] | 5.23 | 9.002 [1851, 1] | 9.29 | 1.434 [490, 1] | 5.91 |
| 160-200 | 13.21 | 3.429 [2032, 2] | 3.46 | 12.554 [2032, 2] | 12.65 | 1.215 [496, 2] | 5.02 |
| 200-240 | 14.91 | 5.19 [1775, 2] | 5.62 | 14.561 [1775, 2] | 14.94 | 1.709 [490, 2] | 7.07 |
| 240-280 | 17.13 | 3.543 [2024, 3] | 3.59 | 16.054 [2024, 3] | 16.24 | 1.184 [476, 2.96] | 5.0 |
| 280-320 | 18.87 | 5.255 [1789, 3] | 5.59 | - | - | 1.621 [488, 3] | 6.8 |
| 320-360 | - | - | - | - | - | 1.841 [321, 3] | 7.97 |

Per-decoder decode tok/s inside each bucket (decode tokens / iteration seconds / decoders):

| D (k cells) | kvu_on_b2048 | kvu_off_b2048 | kvu_on_b512 |
|---|---|---|---|
| 0-40 | - | - | - |
| 40-80 | - | - | - |
| 80-120 | 0.823 | 0.385 | 2.712 |
| 120-160 | 0.828 | 0.414 | 2.592 |
| 160-200 | 0.936 | 0.244 | 2.829 |
| 200-240 | 0.614 | 0.239 | 2.14 |
| 240-280 | 0.811 | 0.158 | 3.29 |
| 280-320 | 0.735 | - | 2.155 |
| 320-360 | - | - | 3.004 |

## Per-request decode tok/s while each prefill runs (window: prefill's first progress -> its first token)

| arm | prefilling req | window s | iterations | prefill tok/s | median s/iter | decode tok/s per decoding req | sum |
|---|---|---|---|---|---|---|---|
| kvu_on_b2048 | i=0 | 165.8 | 40 | 481.6 | 3.94 | - | - |
| kvu_on_b2048 | i=1 | 164.7 | 41 | 482.5 | 4.09 | i0: 0.826 | 0.826 |
| kvu_on_b2048 | i=2 | 174.9 | 42 | 454.1 | 4.24 | i0: 0.772, i1: 0.698 | 1.47 |
| kvu_on_b2048 | i=3 | 177.7 | 42 | 449.2 | 4.27 | i0: 0.624, i1: 0.861, i2: 0.81 | 2.295 |
| kvu_off_b2048 | i=0 | 154.2 | 40 | 518.0 | 3.84 | - | - |
| kvu_off_b2048 | i=1 | 315.8 | 41 | 251.6 | 8.0 | i0: 0.402 | 0.402 |
| kvu_off_b2048 | i=2 | 526.5 | 42 | 150.9 | 13.05 | i0: 0.273, i1: 0.209 | 0.482 |
| kvu_off_b2048 | i=3 (cut by cap) | 208.4 | 12 | 126.4 | 16.05 | i0: 0.158, i1: 0.144, i2: 0.206 | 0.508 |
| kvu_on_b512 | i=0 | 163.8 | 157 | 487.5 | 1.04 | - | - |
| kvu_on_b512 | i=1 | 195.0 | 160 | 407.6 | 1.22 | i0: 2.641 | 2.641 |
| kvu_on_b512 | i=2 | 237.7 | 163 | 334.2 | 1.45 | i0: 2.604, i1: 2.289 | 4.893 |
| kvu_on_b512 | i=3 | 232.2 | 166 | 343.8 | 1.4 | i0: 3.075, i1: 2.946, i2: 1.89 | 7.911 |

Original (v10, no skip, b2048; REPORT.md §1): decoders summed 0.46 (i=1 prefill), 0.54 (i=2), 0.56 tok/s (i=3); prefill 440/232/146/115 tok/s for i=0..3.

## Against the root-cause predictions (REPORT.md §4)

- skip OFF/ON s per 2048 at D 240-280k: 16.244 / 3.586 = 4.53x (predicted ~3.5x for KVU-19a alone at the i=3 end state)
- ON b2048 vs ON b512 s/iteration at D 280-320k: 5.255 / 1.621 = 3.24x shorter iterations; decode per decoder 0.735 vs 2.155 tok/s (predicted ~4x decode while prefilling from -b 512; prefill rate roughly unchanged at depth)
- kvu_on_b2048: decode sum while i=3 prefills 2.295 tok/s (original 0.56)
- kvu_off_b2048: decode sum while i=3 prefills 0.508 tok/s (original 0.56)
- kvu_on_b512: decode sum while i=3 prefills 7.911 tok/s (original 0.56)
- VRAM: the original grew from 51.69 GiB at load to 58.88 under concurrent prefill+decode (REPORT.md §3); compare 'KFD own at healthy / after replay' and 'KFD own peak' above, and the -lv 4 breakdown below.

## Memory (-lv 4): load-time buffers and the exit breakdown

### kvu_on_b2048

```
0.02.134.619 I common_memory_breakdown_print: | memory breakdown [MiB] | total    free     self   model   context   compute    unaccounted |
0.02.134.649 I common_memory_breakdown_print: |   - ROCm0 (MI210)      | 65520 = 60480 + (47208 = 25972 +   17844 +    3392) +      -42168 |
0.02.134.654 I common_memory_breakdown_print: |   - Host               |                   2904 =  1288 +       0 +    1616                |
14.09.239.579 I common_memory_breakdown_print: | memory breakdown [MiB] | total    free     self   model   context   compute    unaccounted |
14.09.239.590 I common_memory_breakdown_print: |   - ROCm0 (MI210)      | 65520 = 12718 + (47408 = 25972 +   17844 +    3592) +        5393 |
14.09.239.594 I common_memory_breakdown_print: |   - Host               |                   2904 =  1288 +       0 +    1616                |
(load lines 57; growth/pool debug lines 2)
```

### kvu_off_b2048

```
0.00.786.728 I common_memory_breakdown_print: | memory breakdown [MiB] | total    free     self   model   context   compute    unaccounted |
0.00.786.758 I common_memory_breakdown_print: |   - ROCm0 (MI210)      | 65520 = 60480 + (47208 = 25972 +   17844 +    3392) +      -42168 |
0.00.786.763 I common_memory_breakdown_print: |   - Host               |                   2904 =  1288 +       0 +    1616                |
20.30.946.548 I common_memory_breakdown_print: | memory breakdown [MiB] | total    free     self   model   context   compute    unaccounted |
20.30.946.567 I common_memory_breakdown_print: |   - ROCm0 (MI210)      | 65520 = 12736 + (47408 = 25972 +   17844 +    3592) +        5375 |
20.30.946.573 I common_memory_breakdown_print: |   - Host               |                   2904 =  1288 +       0 +    1616                |
(load lines 57; growth/pool debug lines 2)
```

### kvu_on_b512

```
0.00.718.932 I common_memory_breakdown_print: | memory breakdown [MiB] | total    free     self   model   context   compute    unaccounted |
0.00.718.962 I common_memory_breakdown_print: |   - ROCm0 (MI210)      | 65520 = 60480 + (45816 = 25972 +   17844 +    2000) +      -40776 |
0.00.718.967 I common_memory_breakdown_print: |   - Host               |                   1692 =  1288 +       0 +     404                |
15.34.256.127 I common_memory_breakdown_print: | memory breakdown [MiB] | total    free     self   model   context   compute    unaccounted |
15.34.256.144 I common_memory_breakdown_print: |   - ROCm0 (MI210)      | 65520 = 15956 + (45866 = 25972 +   17844 +    2050) +        3697 |
15.34.256.148 I common_memory_breakdown_print: |   - Host               |                   1692 =  1288 +       0 +     404                |
(load lines 57; growth/pool debug lines 2)
```

## Coherence spot-checks (greedy, enable_thinking=false; text saved, no classifier)

| launch | sha | finish | tokens | text (first 160 chars) |
|---|---|---|---|---|
| kvu_off_b2048 | 821d2f3d3a563435 | stop | 79 | Sunlight contains all colors, but shorter blue wavelengths scatter more effectively in the atmosphere than longer red wavelengths, making the sky appear blue du |
| kvu_off_b512 | 821d2f3d3a563435 | stop | 79 | Sunlight contains all colors, but shorter blue wavelengths scatter more effectively in the atmosphere than longer red wavelengths, making the sky appear blue du |
| kvu_on_b2048 | 821d2f3d3a563435 | stop | 79 | Sunlight contains all colors, but shorter blue wavelengths scatter more effectively in the atmosphere than longer red wavelengths, making the sky appear blue du |
| kvu_on_b512 | 821d2f3d3a563435 | stop | 79 | Sunlight contains all colors, but shorter blue wavelengths scatter more effectively in the atmosphere than longer red wavelengths, making the sky appear blue du |

- identical-text groups: {"821d2f3d3a563435": ["kvu_off_b2048", "kvu_off_b512", "kvu_on_b2048", "kvu_on_b512"]}

## P3v2 A1 (L0_base -> L3 ~355k with 3 parked neighbours -> L0_after), ON vs OFF

- not run (budget) — see the timeline.
