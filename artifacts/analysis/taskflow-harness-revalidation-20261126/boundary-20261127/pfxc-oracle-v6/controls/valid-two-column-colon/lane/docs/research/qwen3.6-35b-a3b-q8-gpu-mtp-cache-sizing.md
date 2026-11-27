# Qwen3.6-35B-A3B-MTP Q8_0 — `--cache-ram` Sizing Recipe (A3B Companion)

**Model:** Qwen3.6-35B-A3B-MTP Q8_0
**Geometry:** 32K context, f16 KV, hybrid state (state + 32k f16 KV cache)
**Scope:** np1 probe geometry; recipe-only recommendation (no kernel work)
**Canonical recipe geometry:** `np=4`, `ctx=16384` (see linked artifact); the 12288 MiB recommendation below applies only to the 32K/np1 controlled check and must not transfer automatically to that recipe.
**Linked artifact:** [artifacts/serving-recipes/qwen3.6-35b-a3b-q8-gpu-mtp.json](../../artifacts/serving-recipes/qwen3.6-35b-a3b-q8-gpu-mtp.json)
(SHA-256 `d3a3cf4f935a00dd9b020ea409f52a26caedfe3cf2325f636ae7c4edd5cf302b`; bytes preserved verbatim.)

---

## Source rows

| # | Source path (on probe host) | Row ID / label | SHA-256 |
|---|-----------------------------|----------------|---------|
| 1 | `/mnt/raid0/llm/tmp/taskflow-stage1-canary-r2-20261120/out/server.log` | `taskflow-stage1-canary-r2-20261120` | `85533337680e2dee4307f67fb0fda5e08beae1b122adc0f53cacf15a08c4e377` |
| 2 | `/mnt/raid0/llm/tmp/ak-pfxc-probe-gpu-20261120-r2/out/RESULT.json` | `ak-pfxc-probe-gpu-20261120-r2` | `1512c7b77500b66635c3ac23f46c4a3b6ff28c50f69d8066f5532bd65246f32d` |
| 3 | `/mnt/raid0/llm/tmp/prefix-cache-brief-20261120/BRIEF-autokernel.md` | `prefix-cache-brief-20261120` | `63c5843f7c524efcd216ad359a1589530da278d4f132a8954214ab4f0934ee96` |

Row 1 (server.log) is the eviction probe: 41 `making room for prompt cache entry` warnings, each with the size of the evicted entry.
Row 2 (RESULT.json) is the independent probe: 0 evictions at 8192 MiB over 8 tasks, verdict KEEP.

---

## Entry sizes

All 41 per-entry sizes (MiB), in source (chronological) order from server.log:

| # | Line | Size (MiB) | # | Line | Size (MiB) |
|---|------|------------|---|------|------------|
|  1 |   :558 |  329.659  | 21 |  1528 |  973.457  |
|  2 |   559 |  208.063  | 22 |  1568 | 1107.180  |
|  3 |   596 | 1044.502  | 23 |  1695 | 1096.003  |
|  4 |   631 |  536.559  | 24 |  1813 |  413.289  |
|  5 |   657 | 1066.741  | 25 |  1814 |  838.923  |
|  6 |   686 |  868.183  | 26 |  1827 |  457.959  |
|  7 |   731 |  899.782  | 27 |  2013 |  745.443  |
|  8 |   852 |  883.998  | 28 |  2274 |  485.260  |
|  9 |   880 | 1026.461  | 29 |  2296 |  317.898  |
| 10 |   989 |  679.251  | 30 |  2366 |  697.916  |
| 11 |  1022 | 1123.136  | 31 |  2405 |  925.704  |
| 12 |  1052 |  977.217  | 32 |  2465 | 1207.946  |
| 13 |  1131 |  978.184  | 33 |  2493 |  878.716  |
| 14 |  1174 |  354.989  | 34 |  2595 |  992.326  |
| 15 |  1175 |  344.592  | 35 |  2623 |  410.660  |
| 16 |  1176 | 1189.547  | 36 |  2662 |  462.359  |
| 17 |  1266 |  733.401  | 37 |  2663 |  884.114  |
| 18 |  1314 |  519.842  | 38 |  2787 |  629.443  |
| 19 |  1330 | 1348.877  | 39 |  2788 |  147.505  |
| 20 |  1429 |  812.094  | 40 |  2800 |  388.420  |
|    |      |           | 41 |  2812 |  714.588  |

**Summary statistics:**

- Count: 41 evicted entries
- Range: 147.505 – 1348.877 MiB
- Sorted ascending, nearest-rank p95 = 1189.547 MiB (rank 39 of 41)

**Runnable extraction command** (from the pinned server.log):

```python
import re, math, sys

path = "/mnt/raid0/llm/tmp/taskflow-stage1-canary-r2-20261120/out/server.log"
sizes = []
with open(path) as f:
    for line in f:
        m = re.search(r'making room for prompt cache entry, removing oldest entry \(size = ([0-9.]+) MiB\)', line)
        if m:
            sizes.append(float(m.group(1)))

sizes.sort()
n = len(sizes)
rank = math.ceil(0.95 * n)
print(f"count={n} min={sizes[0]:.3f} max={sizes[-1]:.3f}")
print(f"p95 (nearest-rank idx {rank})={sizes[rank-1]:.3f}")
print(f"10-entry ceiling={math.ceil(10 * sizes[rank-1])} MiB")
```

---

## Cache sizing

**Sizing rule:**

```
cache-ram MiB = entries × p95_entry_size
```

For 10 live conversations (the 10+ concurrent worktree scale where evictions were observed):

```
cache-ram MiB = 10 × 1189.547 = 11895.47 MiB → ceil = 11896 MiB
```

**Recommendation: 12288 MiB (12 GiB) starting host RAM budget.**

- 12288 MiB is the next 4096 MiB boundary above 11896 MiB, providing ~3.3% headroom over the raw p95 sum.
- This budget targets a controlled 10-worktree check with Qwen3.6-35B-A3B-MTP Q8_0 at 32K context, f16 KV, np1.
- For N live entries (N > 10), scale linearly: `cache-ram MiB = N × 1189.547`, rounded up to the nearest 4096 MiB boundary.
- The canonical recipe uses `np=4`, `ctx=16384`; this 12288 MiB recommendation applies only to the 32K/np1 controlled check and must not transfer automatically to that recipe.

**Expected gain:** 0–3 hit-rate points, only where evictions hit a live conversation. Zero kernel work required — this is a pure recipe sizing change.

**Falsification criterion:** A probe replay logging zero evictions at 8192 MiB for a 10-task trace would indicate sizing is not the factor. (The independent probe `ak-pfxc-probe-gpu-20261120-r2` observed zero evictions at 8192 MiB over 8 tasks, but eviction pressure only manifests at the 10+ worktree scale seen in `taskflow-stage1-canary-r2` with 41 evictions.)

**Selection bias note:** The 41 entry sizes come exclusively from *evicted* entries. Eviction-only sampling omits all retained entries (those that survived in the cache across the full trace), so the bias direction is unknown: retained entries could be larger or smaller than evicted ones. The 41 evictions do not prove that 8192 MiB is undersized for live conversations — they only show that, at the 10+ worktree scale in `taskflow-stage1-canary-r2`, the cache evicted 41 entries under the observed workload. The p95-based sizing rule targets the 95th percentile of the observed eviction distribution; without knowledge of the retained-entry distribution, the sizing may under- or over-estimate. The 12288 MiB recommendation includes 3.3% headroom over the raw ceil but remains a controlled-check starting point, not a production guarantee.

**8 GiB baseline context:** At 32K context with hybrid state + 32k f16 KV, entries range 330–1005 MiB (per the brief). 8 GiB holds approximately 8–12 conversations. The 41 evictions in `taskflow-stage1-canary-r2` were observed at the 10+ worktree scale; the independent probe `ak-pfxc-probe-gpu-20261120-r2` logged 0 evictions at 8192 MiB over 8 tasks, indicating eviction pressure is workload- and scale-dependent.

---

## VRAM budget

**np1 baseline (separate from host cache RAM):**

- `ak-pfxc-probe-gpu-20261120-r2` (8-task trace): peak VRAM 37.68 GiB (c14 arm) / 37.67 GiB (pfxc arm). Zero prompt-cache evictions at 8192 MiB `--cache-ram`.
- np1 brief baseline: 37.9 GiB peak VRAM.
- Host cache RAM (`--cache-ram`) is separate from GPU VRAM. The `--cache-ram` budget lives on host memory and does not count against the GPU's VRAM budget.

**np2 memory estimate: unvalidated.**

- The np2 memory footprint has not been measured on this model/geometry. Before raising np, verify incremental KV + recurrent memory on np2 relative to the np1 baseline (37.9 GiB peak).
- np2 adds a separate slot for title/compaction side-requests while keeping the main conversation resident. The additional VRAM for the second slot must be measured and confirmed before any np2 deployment.
- Budget np2 against the distinct 37.9 GiB np1 peak and add the measured np2 incremental delta. Do not transfer the np1 cache sizing to np2 without validation on the differently shaped np2 geometry.

**Row cross-reference:**

- `taskflow-stage1-canary-r2-20261120`: 41 evictions at 8 GiB cache → eviction pressure confirmed at 10+ worktree scale.
- `ak-pfxc-probe-gpu-20261120-r2`: 0 evictions at 8192 MiB over 8 tasks → no eviction pressure at this scale; VERDICT KEEP. The probe's 8-task trace is smaller than the eviction-triggering 10+ worktree scale, so zero evictions at 8192 MiB does not falsify the need for larger cache at the higher scale.

**Recommendation summary:**

| Parameter | Value |
|-----------|-------|
| `--cache-ram` (10 worktrees) | 12288 MiB (12 GiB) |
| Sizing formula | `ceil(N × 1189.547 / 4096) × 4096` MiB for N entries |
| np1 peak VRAM | 37.9 GiB (brief baseline); 37.67–37.68 GiB (probe r2) |
| np2 VRAM | Unvalidated — measure incremental KV/recurrent before raising np |
| Expected hit-rate gain | 0–3 points (eviction-dependent only) |
