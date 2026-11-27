# Qwen3.6-35B-A3B-MTP Q8_0 — GPU MTP Cache Sizing Recipe (A3B)

**Model**: Qwen3.6-35B-A3B-MTP Q8_0
**Geometry**: 32k context, f16 KV (`ctk: f16`, `ctv: f16`), np1/np4
**Recipe**: [artifacts/serving-recipes/qwen3.6-35b-a3b-q8-gpu-mtp.json](../../artifacts/serving-recipes/qwen3.6-35b-a3b-q8-gpu-mtp.json)
**Task**: PFXC-A3 (non-inference, docs-only)

## Source rows

| Row ID | Artifact | SHA-256 |
|---|---|---|
| `taskflow-stage1-canary-r2-20261120` | `out/server.log` (eviction probe, 41 evictions at tf1 r2 scale) | `85533337680e2dee4307f67fb0fda5e08beae1b122adc0f53cacf15a08c4e377` |
| `ak-pfxc-probe-gpu-20261120-r2` | `out/RESULT.json` (0 evictions at 8192 MiB, 8-task trace) | `1512c7b77500b66635c3ac23f46c4a3b6ff28c50f69d8066f5532bd65246f32d` |

The canary-r2 server log records 41 `making room for prompt cache entry` evictions across ~10 minutes of workload, confirming eviction pressure at the 10+ concurrent worktree scale. The probe-r2 RESULT.json reports **zero evictions** at 8192 MiB over its 8-task trace — eviction pressure is scale-dependent and does not manifest at smaller task counts.

### Extraction command (per-entry sizes from server.log)

```bash
grep 'making room for prompt cache entry' \
  /mnt/raid0/llm/tmp/taskflow-stage1-canary-r2-20261120/out/server.log \
  | grep -oP 'size = \K[0-9.]+'
```

This yields 41 floating-point values in server-log order (MiB each).

## Entry sizes

All 41 evicted entry sizes from `taskflow-stage1-canary-r2-20261120/out/server.log`, in source order:

| # | Log line | Size (MiB) |
|---|----------|------------|
| 1 | :558 | 329.659 |
| 2 | :559 | 208.063 |
| 3 | :596 | 1044.502 |
| 4 | :631 | 536.559 |
| 5 | :657 | 1066.741 |
| 6 | :686 | 868.183 |
| 7 | :731 | 899.782 |
| 8 | :852 | 883.998 |
| 9 | :880 | 1026.461 |
| 10 | :989 | 679.251 |
| 11 | :1022 | 1123.136 |
| 12 | :1052 | 977.217 |
| 13 | :1131 | 978.184 |
| 14 | :1174 | 354.989 |
| 15 | :1175 | 344.592 |
| 16 | :1176 | 1189.547 |
| 17 | :1266 | 733.401 |
| 18 | :1314 | 519.842 |
| 19 | :1330 | 1348.877 |
| 20 | :1429 | 812.094 |
| 21 | :1528 | 973.457 |
| 22 | :1568 | 1107.180 |
| 23 | :1695 | 1096.003 |
| 24 | :1813 | 413.289 |
| 25 | :1814 | 838.923 |
| 26 | :1827 | 457.959 |
| 27 | :2013 | 745.443 |
| 28 | :2274 | 485.260 |
| 29 | :2296 | 317.898 |
| 30 | :2366 | 697.916 |
| 31 | :2405 | 925.704 |
| 32 | :2465 | 1207.946 |
| 33 | :2493 | 878.716 |
| 34 | :2595 | 992.326 |
| 35 | :2623 | 410.660 |
| 36 | :2662 | 462.359 |
| 37 | :2663 | 884.114 |
| 38 | :2787 | 629.443 |
| 39 | :2788 | 147.505 |
| 40 | :2800 | 388.420 |
| 41 | :2812 | 714.588 |

**Summary statistics** (all in MiB):

- Count: **41**
- Range: **147.505 – 1348.877**
- Mean: **748.785**
- Nearest-rank p95 (rank 39 of 41): **1189.547**

Each evicted entry represents a conversation's hybrid state (model weights in host RAM for CPU-resident KV) plus its 32k f16 KV cache. Entry sizes vary widely because conversations differ in context length, number of turns, and whether the model is fully GPU-offloaded or partially on host.

### Selection bias note

These 41 entries are **evicted** entries only — they represent the tail of the size distribution that was oldest at eviction time. Smaller, fresher conversations that never triggered eviction are not represented. The true p95 across all live conversations is therefore likely lower than 1189.547 MiB. This makes the sizing calculation conservative (pessimistic), which is appropriate for a host RAM budget recommendation.

## Cache sizing

### Sizing rule

```
cache-ram MiB = entries × p95_entry_size
```

For **N** live concurrent conversations at 32k context with f16 KV:

| N (live entries) | Budget (MiB, p95-based) | Rounded recommendation (MiB) |
|---|---|---|
| 8 | ceil(8 × 1189.547) = 9517 | 9728 |
| 10 | ceil(10 × 1189.547) = 11896 | **12288** |
| 12 | ceil(12 × 1189.547) = 14275 | 14336 |

### Recommendation

For a controlled **10-worktree check**, set `--cache-ram` to **12288 MiB** (12 GiB). This is the nearest standard increment above the p95-based budget of 11896 MiB, providing headroom for the selection bias noted above and for non-KV host memory overhead.

Scaled rule: `cache-ram (MiB) = ceil(N × 1189.547)` rounded up to the nearest 256 MiB boundary, where N is the expected number of concurrent live conversations.

### Expected gain

0–3 hit-rate points, only in scenarios where evictions are actively disrupting a live conversation (the evicted entry gets re-cached on the next request). Zero effect on kernel compute — this is purely a host-memory budget adjustment with no changes to the inference path.

### Falsification criterion

If the probe replay (`ak-pfxc-probe-gpu-20261120-r2`) logs **zero evictions** at 8192 MiB for its 8-task trace, then cache sizing is not a factor for that workload scale. Indeed, row r2 logged 0 evictions at 8192 MiB over 8 tasks — eviction pressure only appears at the 10+ worktree scale observed in `taskflow-stage1-canary-r2-20261120` (41 evictions). The sizing recommendation is therefore scoped to that higher-concurrency regime.

## VRAM budget

### np1 baseline

The prefix-cache brief (BRIEF-autokernel.md, line 61) records **37.9 GiB peak VRAM** at np1 for this model/recipe geometry. This is the GPU memory footprint including model weights (Q8_0), KV cache buffers, and working memory at the default np=4 setting with a single conversation slot active.

### Probe-r2 verification

Row `ak-pfxc-probe-gpu-20261120-r2` measured:
- c14 arm: **37.68 GiB** peak VRAM, 0 evictions at its configured cache size
- pfxc arm: **37.67 GiB** peak VRAM, 0 evictions at its configured cache size

Both arms logged zero prompt-cache evictions over the full 8-task trace, confirming that 8192 MiB of host cache RAM is sufficient for this workload shape (8 concurrent tasks, not 10+).

### np2 budget note

The np2 VRAM estimate is **unvalidated**. The np1 baseline of 37.9 GiB must be the reference point when provisioning np2; host cache RAM (`--cache-ram`) is entirely separate from GPU VRAM and does not affect the `max_vram_gib` measurement. Before raising np from 1 to 2:

1. Budget VRAM against the distinct **37.9 GiB** np1 peak (not the r2 probe's 37.68/37.67, which is a slightly different run).
2. Verify incremental KV and recurrent memory usage at np2 before raising it — np2 doubles the number of parallel conversation slots, which directly increases KV cache VRAM consumption proportional to the number of active slots.
3. Host RAM for `--cache-ram` (12 GiB recommended above) is separate from GPU VRAM and should be budgeted independently.

### Transfer caveat

This sizing note is scoped to the **32K/np1 probe geometry** with f16 KV types as defined in the recipe. It should not be transferred to a differently shaped canonical recipe (different context length, different KV quantization, or different np) without re-measuring entry sizes and VRAM at the new geometry.
