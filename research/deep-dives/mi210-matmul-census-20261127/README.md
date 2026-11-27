# MI210 short-row and F32 dispatch census

The retained 27B DFlash2 windows have **zero F32 weight matmuls and zero fused MMVQ calls eligible for the upstream small-K change** in 156 observed target verify forwards. For A3B, the width-12 F32 router still costs 4.79 ms per grouped target forward on frozen v10. Experimental MMVF chunking already improved the corresponding np4 serving recipe by **1.082× [1.041, 1.124]**. Use that established path when comparing an additional implementation. The remaining split-K question is the A3B **M=1** shared-expert gate. Its measured ceiling can exceed a 1% served gate, and its current backends already use either weight-sharing MMVF or atomic split-K.

The census is diagnostic. Kernel durations are sums of observed dispatch durations. Elimination bounds assume that all targeted GPU time delays the request, with no extra launches, reads, writes or changed overlap. The profiling wrapper and route logging affect timing. The native samples are six fixed panels and use greedy synthetic prompts, so the ranges are request-window differences. No speedup interval is claimed from the profiles.

## F32 prefill and verify

One MI210 has 104 CUs. The private A3B visits use the immutable v10 `ffc1bac82` store, Qwen3.6-35B-A3B-MTP Q8_0, an f16 KV cache, a four-slot server, MTP n-max 2 and one or four simultaneous requests. The A3B GPU recipe is a shadow configuration. The frontdoor's served CPU route is outside this census. The retained 27B reference is V5I OFF from the C22 q8wp comparison, using the served-style greedy single-request DFlash2 recipe and Q8_0 KV.

| Frozen-v10 prefill shape | K | M | Actual N | Backend | Workgroups | Dispatches | Total kernel ms |
|---|---:|---:|---:|---|---:|---:|---:|
| 256-token prompt, router | 2048 | 256 | 252 | Tensile GSU1, 32×32 tile | 64 | 40 | 1.292 |
| 256-token prompt, shared gate | 2048 | 1 | 252 | Tensile GSU5, 16×64 tile | 20 | 40 | 0.731 |
| 1024-token prompt, router | 2048 | 256 | 1020 | Tensile GSU1, 32×32 tile | 256 | 40 | 2.264 |
| 1024-token prompt, shared gate | 2048 | 1 | 1020 | Tensile GSU5, 16×16 tile | 320 | 40 | 0.989 |
| Both prompts, router tail | 2048 | 256 | 4 | HIP MMF | 4 | 40 each | 4.559 / 4.554 |
| Both prompts, shared gate tail | 2048 | 1 | 4 | Tensile GSU5, 32×32 tile | 5 | 40 each | 0.669 / 0.702 |

Bulk M256 prefill is 0.65% and 0.57% of the corresponding 197.30 and 398.21 ms request windows. Even removing every bulk M256 dispatch stays below the 0.84% and 1% thresholds previously used for served router work. Eliminating both bulk shapes reaches 1.03% in the smaller cell and 0.82% in the larger cell. That smaller result requires eliminating almost all targeted GPU time to realize 1%. The narrower prompt tail is material on v10 and reaches the same MMF route that existing MMVF work addresses. Other v10 prefill windows in the replay track width 380, 480, 488, 496, 520, 1560 and 2032. The two larger grouped panels exercise different phase mixes. The dominant M256 bulk solution is always GSU1 in these captures.

| Decode shape, K=2048 | Width | Calls per grouped target forward | Workgroups per call | Kernel ms per grouped target forward |
|---|---:|---:|---:|---:|
| v10 M256 router, HIP MMVF | 1 | 40 | 256 | 0.291–0.293 |
| v10 M1 shared gate, HIP MMVF | 1 | 40 | 1 | 0.236 |
| v10 M256 router, HIP MMVF | 2 | 40 | 256 | 0.330 |
| v10 M1 shared gate, HIP MMVF | 2 | 40 | 1 | 0.266 |
| v10 M256 router, HIP MMVF | 3 | 40 | 256 | 0.352–0.386 |
| v10 M1 shared gate, HIP MMVF | 3 | 40 | 1 | 0.276–0.300 |
| v10 M256 router, HIP MMF | 12 | 40 | 4 | 4.795 / 4.791 |
| v10 M1 shared gate, Tensile GSU5 | 12 | 40 | 5 | 0.764 / 0.766 |
| C21 M256 router, HIP MMVF | 4 | 40 | 256 | 0.418 / 0.417 |
| C21 M1 shared gate, HIP MMVF | 4 | 40 | 1 | 0.345 / 0.343 |

The grouped v10 pair has 21 width-12 target forwards in each panel, alongside other observed widths. The respective totals for the width-12 router and shared gate are 116.734 and 116.685 ms. Dividing by all 96 and 92 API request-rounds gives **1.216 / 1.268 ms per API request-round**. Grouped target forwards and API request-rounds use different denominators because one GPU forward can verify several requests. The two C21 OFF request windows retained 38 and 39 steady verify forwards, dominated by width four. Their M1 share, including the small number of other widths, is **0.342 / 0.339 ms per steady forward**, or **1.38 / 1.37%** of each full request's reported decode time. The M1 bound leaves room above 1% if a candidate eliminates roughly 72% of its cost. The v10 width-12 M1 window is 0.167 / 0.175 ms per API request-round and already includes split-K initialization.

F32 MMVF hoists an FP32 weight pair before looping over verify columns. The existing C19 chunk lever reads the weight again for each column chunk and removes much of the wide-router MMF penalty. The controlled C19 chunk comparison achieved 2.0–3.4× at widths 9–16, which missed its 3× per-cell rule. The separate np4 served comparison was KEEP at 1.0817× [1.0407, 1.1244], with identity passing. The C21 M1 share and the v10 GSU5 share leave a bounded residual question. A fixed-order two-pass M1 comparison must use C21 MMVF at narrow widths and resolved Tensile GSU5 at applicable wider widths. Capture repeat bitwise results, total time including initialization and reduction, and a later request window. For CPU, first establish underoccupied cores after NPS4-local partitioning. This MI210 record supplies no CPU occupancy measurement.

### Resolved Tensile solution

Kernel names plus actual dispatch grids distinguish output tile count from launched workgroups after slicing. For example, the M1 N12 GSU5 kernel has one unsplit tile, five workgroups and a separate `Cijk_S` initializer. The exact GSU5 names in both installed gfx90a code-object variants contain 16 static `buffer_atomic_cmpswap` sites and zero global output-store instructions outside the atomic sequence. The trace shows accumulation into one initialized destination and no separate reduction dispatch for these GSU5 bins. The GSU1 kernels are ordinary output stores. There are no observed materialized per-slice arrays on these joined paths. An explicit two-pass candidate would write and read `4 × M × N × S` bytes of FP32 partials before writing `4 × M × N` bytes of final output. At M1, N12 and eight slices this is 384 B written plus 384 B read and a 48 B final write, so launch and CU occupancy matter more than the byte count. The exact symbols and static instruction witnesses are retained. [Tensile code-object audit](tensile-store-isa.txt)

## Fused Q8 short rows

Frozen-v10's width-one Q8_0 expert gate/up uses four wave64s, eight routed expert-group workgroups in the Y dimension, K=2048 and M=512. The strict predicate compares 64 Q8_0 blocks with four waves × 16 blocks/wave, so **stock small_k is false at exact fit**. The proposed inclusive cutoff would add those dispatches. The M512 shared gate/up uses the same K but already selects the forced four-row/eight-wave CDNA2 path. The trace also contains M2048/K512 shared down epilogues. A fusion template flag on those epilogues does not establish a gate + up weight pair.

| A3B v10 panel | API request-rounds | Exact-fit expert gate/up calls | Exact-fit upper bound ms/round | Already-forced shared gate/up calls | Shared upper bound ms/round |
|---|---:|---:|---:|---:|---:|
| Single request | 29 | 95 | 0.0640 | 95 | 0.0377 |
| Four concurrent requests | 96 | 5 | 0.0011 | 5 | 0.0006 |
| Later single request | 22 | 42 | 0.0379 | 42 | 0.0212 |
| Later four concurrent requests | 92 | 43 | 0.0091 | 43 | 0.0056 |

The A3B whole-request sums deliberately retain every possible width-one dispatch, including drafter calls. Eliminating both paired-weight bins reaches at most 0.49% of the corresponding single-request reported decode time in these panels. Widths two through four were observed and have zero eligible fused calls under the width-one launch guard.

The retained 27B DFlash2 V5I pair had 74 and 82 target verify forwards at widths 2, 4, 5, 6 and 8. Widths two and four had zero eligible calls and there was no observed target width-three or width-one verify in those requests. The source width-one fusion guard excludes width three. A C21 controlled width-one panel establishes the distinct dense route at Q8_0 K5120/M17408, 64 forced-fusion calls and 13.127 ms per controlled forward. Its other fused epilogues are K17408/M5120, 64 calls and 8.093 ms, and K6144/M5120, 16 calls and 3.554 ms. The dense route is selected by the CDNA2 four-row override. The strict small-K predicate does not admit any of these K values on its own. A retained C14 96-token plain decode request had 13,680 fused-small-geometry dispatches with 15.293 ms per requested token, including the initial prompt-tail dispatches. Its compressed trace dropped grids and cannot assign each occurrence to K/M. The width-one dense controlled number leaves meaningful time when serving plain decode. The observed DFlash2 mix and the intake's Q8_0 result give no basis to carry the gate/up split into this DFlash2 path. [Short-row data](AK-SHORT-ROW-CENSUS.json)

## Coverage and recovery

The raw census retains dispatch symbols, workgroups, elapsed time, K/M/N joins for the targeted weight types, and explicit unknown shape fields for unrelated quantized dispatches whose arguments are unavailable. F32 inputs are identified separately from the MTP layer's BF16 router. Per-bank ROCm traffic and individual runtime stores are unmeasured. The disassembly supports the known write paths, and a future two-pass run must account for its own partial-buffer writes. The holdout A3B windows use later input tokens and different lengths. The retained 27B files hold two distinct requests, and the C21 A3B windows are repeated visits to the same prompt. The findings do not establish the corresponding residual on all C22 production-config panels.

The first GPU smoke captured valid dispatches and failed rowflow rebooking because its fresh estimate receipt was absent. The launcher was repaired to emit the canonical measured receipt. The second smoke passed. The direct native visit held the MI210 claim with CPUs 184–191 and completed all six panels, with 39.68–39.97 GB of own-process VRAM during the windows. The filer recorded `pass rc=0 answer=CENSUS_CAPTURED`. That verdict records successful capture. [Row custody](rowflow-filed.txt), [capture source](capture-source.tar.gz), [dispatch census](dispatch-census.json)

The native trace archive is at `/mnt/raid0/llm/archive/compute-evidence/mi210-matmul-census-20261127/`. Both the compressed archive and all seven regenerated files passed SHA-256 verification. If the native scratch is unavailable, restore the verified archive to `/mnt/raid0/llm/tmp/codex-mi210-matmul-census-20261127/out/`. From that output directory, run `sha256sum -c /mnt/raid0/llm/archive/compute-evidence/mi210-matmul-census-20261127/NATIVE.sha256`. Run `python3 -B replay.py` in an eligible CPU window after restoring any missing sources listed in the pin manifest. It reuses the original 27B request segmentation and matches 156/156 verify forwards, independently substantiates the C21 A3B steady-window counts, and writes both census JSON files. `check-tensile.sh` verifies the store slices after replay. [Archive hashes](ARCHIVE.sha256), [source pins](source-pins.json)
