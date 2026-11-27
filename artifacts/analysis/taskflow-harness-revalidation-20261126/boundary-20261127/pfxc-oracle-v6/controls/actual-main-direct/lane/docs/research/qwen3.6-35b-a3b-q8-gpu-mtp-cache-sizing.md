# A3B prompt-cache sizing companion (PFXC-A3)

Model: Qwen3.6-35B-A3B-MTP Q8_0. Companion to the [canonical recipe](../../artifacts/serving-recipes/qwen3.6-35b-a3b-q8-gpu-mtp.json), whose bytes and arguments are unchanged. The recommendation applies to the **32K context / np1 probe geometry**, f16 KV plus hybrid recurrent state. The canonical recipe uses ctx=16384, np=4, kv_unified=false; these estimates must not be transferred to that different geometry without validation.

## Source rows

Evidence: [staged source excerpts](../../.taskflow-refs/external/pfxc/pfxc-source-excerpts.txt) and [PFXC-A3 handoff](../../.taskflow-refs/epyc-root@9cd1c942a3ad9edce34ba42b8eaf796156e8be72/handoffs/active/kernel-champion-and-promotion.md).

- `taskflow-stage1-canary-r2-20261120` (tf1 r2), `out/server.log`: original `/mnt/raid0/llm/tmp/taskflow-stage1-canary-r2-20261120/out/server.log`, full SHA-256 `85533337680e2dee4307f67fb0fda5e08beae1b122adc0f53cacf15a08c4e377`. The 41 `making room for prompt cache entry` evictions supply the sizes below and evidence of pressure at 10+ worktrees.
- `ak-pfxc-probe-gpu-20261120-r2`, `out/RESULT.json`: original `/mnt/raid0/llm/tmp/ak-pfxc-probe-gpu-20261120-r2/out/RESULT.json`, full SHA-256 `1512c7b77500b66635c3ac23f46c4a3b6ff28c50f69d8066f5532bd65246f32d`. Filed KEEP on 2026-11-20. Both arms recorded **0 evictions at 8192 MiB on the 8-task trace**; there are no per-evicted-entry values. Peak VRAM: **37.68 GiB c14 / 37.67 GiB pfxc**.
- `prefix-cache-brief-20261120/BRIEF-autokernel.md`, lines 60–62, full SHA-256 `63c5843f7c524efcd216ad359a1589530da278d4f132a8954214ab4f0934ee96`: supplies the distinct **37.9 GiB peak at np1** baseline for np2 planning.

These full-artifact hashes are pinned as reported in the staged excerpts, not recomputed from the excerpts. No fresh run or measurement was performed.

## Entry sizes

All 41 evicted-entry sizes in original source order from `taskflow-stage1-canary-r2-20261120`; line numbers refer to its server log. Units are MiB.

| Order | Log line | Entry MiB |
| --- | --- | ---: |
| 1 | 558 | 329.659 |
| 2 | 559 | 208.063 |
| 3 | 596 | 1044.502 |
| 4 | 631 | 536.559 |
| 5 | 657 | 1066.741 |
| 6 | 686 | 868.183 |
| 7 | 731 | 899.782 |
| 8 | 852 | 883.998 |
| 9 | 880 | 1026.461 |
| 10 | 989 | 679.251 |
| 11 | 1022 | 1123.136 |
| 12 | 1052 | 977.217 |
| 13 | 1131 | 978.184 |
| 14 | 1174 | 354.989 |
| 15 | 1175 | 344.592 |
| 16 | 1176 | 1189.547 |
| 17 | 1266 | 733.401 |
| 18 | 1314 | 519.842 |
| 19 | 1330 | 1348.877 |
| 20 | 1429 | 812.094 |
| 21 | 1528 | 973.457 |
| 22 | 1568 | 1107.180 |
| 23 | 1695 | 1096.003 |
| 24 | 1813 | 413.289 |
| 25 | 1814 | 838.923 |
| 26 | 1827 | 457.959 |
| 27 | 2013 | 745.443 |
| 28 | 2274 | 485.260 |
| 29 | 2296 | 317.898 |
| 30 | 2366 | 697.916 |
| 31 | 2405 | 925.704 |
| 32 | 2465 | 1207.946 |
| 33 | 2493 | 878.716 |
| 34 | 2595 | 992.326 |
| 35 | 2623 | 410.660 |
| 36 | 2662 | 462.359 |
| 37 | 2663 | 884.114 |
| 38 | 2787 | 629.443 |
| 39 | 2788 | 147.505 |
| 40 | 2800 | 388.420 |
| 41 | 2812 | 714.588 |

Range: **147.505–1348.877 MiB**. Nearest-rank p95 is ascending rank `ceil(0.95 × 41) = 39`: **1189.547 MiB**. This sample supersedes the brief's rough 330–1005 MiB range.

Runnable extraction from the staged excerpts (repository root), preserving source order:

```sh
python3 - <<'PY'
from pathlib import Path
from decimal import Decimal, ROUND_CEILING
import re
source = Path('.taskflow-refs/external/pfxc/pfxc-source-excerpts.txt').read_text()
rows = re.findall(r'^\s*(\d+):.*making room for prompt cache entry.*size = ([0-9.]+) MiB', source, re.M)
assert len(rows) == 41
for order, (line, size) in enumerate(rows, 1):
    print(order, line, size)
sizes = sorted(Decimal(size) for _, size in rows)
rank = int((Decimal('0.95') * len(sizes)).to_integral_value(rounding=ROUND_CEILING))
p95 = sizes[rank - 1]
print('count/range/p95:', len(sizes), sizes[0], sizes[-1], p95)
print('10-entry MiB before headroom:', (10 * p95).to_integral_value(rounding=ROUND_CEILING))
PY
```

Selection bias: this is an **eviction-only sample**, not a census of live conversations. It selects oldest entries removed under pressure and excludes retained or never-evicted entries. Repeated events need not be distinct conversations. Workload, age and cache policy can bias sizes in either direction; this p95 is a planning estimate, not a guaranteed bound or measured live-entry p95.

## Cache sizing

Rule: **cache-ram MiB = ceil(live entries × p95 entry size)** before headroom. For 10 live entries, `ceil(10 × 1189.547) = 11896 MiB`. Recommend **`--cache-ram 12288` (12 GiB)** as the starting host prompt-cache budget for a controlled **10-worktree, 32K/np1** check. That leaves 392 MiB (about 3.3%) above the rounded estimate: modest headroom, not proven sufficient capacity. Budget other server, OS and worktree host memory separately.

For additional live entries, scale `ceil(N × 1189.547)` MiB and add explicit headroom; do not keep a fixed 12288 MiB cap. For example, 12 entries need 14275 MiB before headroom. The brief's 8 GiB ≈ 8–12 conversations is a rough workload-dependent estimate, not a guarantee at 10+ worktrees.

`taskflow-stage1-canary-r2-20261120` shows 41 evictions; `ak-pfxc-probe-gpu-20261120-r2` shows none on its smaller 8-task trace. The latter does not satisfy the 10-task falsification. If a comparable 10-task replay at 8192 MiB logs zero evictions, sizing is not a factor for that trace. A future controlled check should retain entry-size and eviction logs and determine whether removed entries belong to still-live conversations.

Expected gain is 0–3 hit-rate points only where eviction removes live conversations, with zero kernel work; this is not a new measured gain. The probe's 3.0-point arm difference cannot be attributed to extra cache capacity: both arms had zero evictions.

## VRAM budget

Host `--cache-ram` is separate from VRAM. Raising the host cache does not provide GPU headroom. Budget np2 against the brief's distinct **37.9 GiB np1 peak**, separately from the **37.68/37.67 GiB** peaks in `ak-pfxc-probe-gpu-20261120-r2`. The host-cache eviction sizes in `taskflow-stage1-canary-r2-20261120` do not measure incremental GPU slot memory.

The **np2 memory estimate is unvalidated**: `VRAM(np2) ≈ 37.9 GiB + incremental second-slot KV/recurrent memory + incremental graph/workspace memory`, plus operating headroom. The supplied evidence does not quantify those increments. Verify actual incremental KV and recurrent-state allocations and peak workspace for the intended context/slot geometry before raising np. Neither doubling the full model footprint nor treating host entry MiB as the GPU increment is supported.

np2 could keep the main conversation resident while title/compaction requests use another slot, but no np2 fit or benefit is claimed. This recommendation remains scoped to the 32K/np1 probe geometry, not the differently shaped canonical 16K/np4 recipe.
