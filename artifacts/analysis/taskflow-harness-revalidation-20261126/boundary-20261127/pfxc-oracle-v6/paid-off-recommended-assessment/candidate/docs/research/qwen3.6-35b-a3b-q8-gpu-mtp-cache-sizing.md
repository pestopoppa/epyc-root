# Qwen3.6-35B-A3B-Q8 GPU MTP — `--cache-ram` Sizing Recipe (A3B)

**Model:** Qwen3.6-35B-A3B-MTP Q8_0 · **Geometry:** 32K context, np1 (draft_n_max=2)
**Recipe link:** [artifacts/serving-recipes/qwen3.6-35b-a3b-q8-gpu-mtp.json](../../artifacts/serving-recipes/qwen3.6-35b-a3b-q8-gpu-mtp.json)

---

## Source rows

| Row ID | File | SHA-256 |
|---|---|---|
| `taskflow-stage1-canary-r2-20261120` (tf1 r2) | `/mnt/raid0/llm/tmp/taskflow-stage1-canary-r2-20261120/out/server.log` | `85533337680e2dee4307f67fb0fda5e08beae1b122adc0f53cacf15a08c4e377` |
| `ak-pfxc-probe-gpu-20261120-r2` | `/mnt/raid0/llm/tmp/ak-pfxc-probe-gpu-20261120-r2/out/RESULT.json` | `1512c7b77500b66635c3ac23f46c4a3b6ff28c50f69d8066f5532bd65246f32d` |
| `prefix-cache-brief-20261120` | `/mnt/raid0/llm/tmp/prefix-cache-brief-20261120/BRIEF-autokernel.md` | `63c5843f7c524efcd216ad359a1589530da278d4f132a8954214ab4f0934ee96` |

**tf1 r2 (source row):** 41 `making room for prompt cache entry` evictions logged across ~10 min of concurrent work. Eviction pressure is visible only at the 10+ worktree scale.

**ak-pfxc-probe-gpu-20261120-r2:** Logged **0 evictions** at `--cache-ram=8192` MiB over an 8-task trace. Verdict: KEEP (PASS). Peak VRAM 37.68 GiB (c14) / 37.67 GiB (pfxc). No per-evicted-entry values because there were none.

---

## Entry sizes

All 41 evicted-entry sizes from tf1 r2 `server.log`, in source order:

| # | Log line | Size (MiB) |
|---|----------|-----------|
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

**Summary statistics (n=41, evicted entries only):**

- Range: **147.505 – 1348.877 MiB**
- Mean: 748.785 MiB
- Median: 812.094 MiB
- Nearest-rank p95 (rank 39/41): **1189.547 MiB**

> **Selection bias note:** These sizes come exclusively from evicted entries — the cache's LRU tail. Eviction-only sampling cannot establish whether the live-entry p95 is higher or lower than this sample; short-lived conversations that never reached eviction status are absent, and large entries that survived longer in cache may be over-represented. The direction of bias is unknown.

**Extraction command** (runnable against the original server log):

```bash
grep 'making room for prompt cache entry' \
  /mnt/raid0/llm/tmp/taskflow-stage1-canary-r2-20261120/out/server.log \
  | grep -oP 'size = \K[\d.]+' \
  | sort -g
```

---

## Cache sizing

**Sizing rule:**

```
cache-ram MiB = entries × nearest-rank p95 entry size
              = entries × 1189.547 MiB   (from tf1 r2 evicted-entry sample)
```

For **10 live conversations**:

```
ceil(10 × 1189.547) = 11896 MiB
→ rounded up to nearest 256 MiB: 12032 MiB
→ recommended starting budget: 12288 MiB (12 GiB, headroom for variance)
```

The 12288 MiB recommendation provides approximately 3.3% headroom above the raw p95-based calculation (11896 MiB) and allows for entry-size drift between runs. For additional live entries beyond 10, scale linearly:

```
cache-ram MiB (N entries) = ceil(N × 1189.547 / 256) × 256
```

**Expected gain:** 0–3 hit-rate points, only where eviction pressure hits a live conversation. Zero kernel work — purely a host-RAM budget adjustment.

**Falsification criterion:** If a probe replay logs **zero evictions at 8192 MiB for a 10-task trace**, then cache-ram sizing is not the limiting factor. The ak-pfxc-probe-gpu-20261120-r2 row logged 0 evictions at 8192 MiB over its observed 8-task trace; this result does not establish a general concurrency threshold. Eviction pressure is visible only in the tf1 r2 log at the 10+ worktree scale.

---

## VRAM budget

**np1 baseline:** The prefix-cache brief records **37.9 GiB peak VRAM at np1** (n_predict=384, ctx=16384, draft_n_max=2). This is the host-side VRAM footprint of the Q8_0 model loaded with ngl=99 on a single ROCm device.

**ak-pfxc-probe-gpu-20261120-r2 measurements:**

| Arm | Peak VRAM (GiB) | Evictions | Hit rate |
|---|---|---|---|
| c14 (canonical) | 37.68 | 0 | 0.7441 |
| pfxc (experimental) | 37.67 | 0 | 0.7741 |

The probe row's 37.67–37.68 GiB is distinct from the brief's 37.9 GiB np1 baseline; neither source attributes the difference, and no unsupported explanation is offered here.

**np1 → np2 transition note:** Before moving from np1 to np2, verify **incremental KV + recurrent memory** growth beyond the np1 baseline. The brief warns: "If taskflow moves to np2 (separate slot for title/compaction side-requests, keeps the main conversation resident), budget VRAM (37.9 GiB peak at np1) and host RAM accordingly."

The np2 memory estimate is **unvalidated**. Do not transfer this sizing recipe to a differently shaped canonical recipe — the geometry (32K ctx, np1, draft_n_max=2) matters for both entry sizes and VRAM consumption. Host cache RAM (`--cache-ram`) is separate from device VRAM; increasing one does not reduce the other.

**Recommendation:** Keep `--cache-ram` at 12288 MiB (12 GiB) as a starting point for controlled 10-worktree validation. Measure actual hit-rate improvement and confirm zero evictions before committing to this budget in production.
