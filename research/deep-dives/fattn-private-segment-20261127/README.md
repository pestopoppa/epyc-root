# MI210 attention private-segment audit

**Close `FATTN-PRIVATE-SEGMENT` on absent path.** The audited production and C22 sources already use a fixed-width V load in the MMA routine changed by upstream PR #33161. The PR’s 512-head, `2 × 8` MMA specialization resolves to a `NO_DEVICE_CODE` stub on gfx90a. The scratch-bearing kernels that did dispatch use two other V-load implementations. There is no constant-length treatment to compare in these builds. [Operator row and stop rule](../../../handoffs/active/briefs/FATTN-PRIVATE-SEGMENT.md) · [Upstream one-line change](https://github.com/ggml-org/llama.cpp/pull/33161/files)

## Executed kernels

The join covers 24 retained MI210 trace files, 29 trace cases or request windows, and 19 build-specific device symbols. The table counts main attention dispatches. The ISA counts are static instructions in the matched kernel body. Private bytes are recorded per work-item in the code object and agree with the dispatch trace. [Trace cases](cases.json) · [Full join and instruction excerpts](join.json)

| Build and cases | Main attention specialization | Hits | VGPR / AGPR | VGPR spills | Private B | Scratch loads / stores |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| Production v10, 16 generated tokens, Distill-Qwen 1.5B, f16 KV | Vector `D=128, ncols=1` | 476 | 102 / 0 | 0 | 0 | 0 / 0 |
| Production v10, 128 generated tokens, Qwen2.5-Coder 0.5B, f16 KV | Vector `D=64, ncols=1` | 3,096 | 98 / 0 | 0 | 0 | 0 / 0 |
| Production v10 A3B, 256-token / 1,024-token prefills, f16 KV | WMMA `D=256, ncols=16, nwarps=4, VKQ_stride=64, float` | 22 / 22 | 192 / 16 | 0 | 0 | 0 / 0 |
| Production v10 A3B, six request panels, f16 KV | Vector `D=256, ncols=1` | 217 | 100 / 0 | 0 | 0 | 0 / 0 |
| Production v10 A3B, concurrent four 512-token requests, f16 KV | Vector `D=256, ncols=2` | 33 | 118 / 0 | 0 | 144 | 346 / 365 |
| C22 OFF / RF1 / RF2, 27B verify, KV=32,768, q=1 and q=8 | `gv_fattn_kernel` KC=32 / KC=16 and `gv_rf_kernel<false,true,1>` | 6,257 / 7,865 / 4,409 | 186 / 0, 180 / 0, 248 / 68 | 0 | 0 | 0 / 0 |
| C22 RF4, same 27B verify inputs | `gv_rf_kernel<true,false,2>` | 5,194 | 256 / 0 | 14 | 60 | 14 / 14 |
| C22 RF6 build, OFF / RF1 / RF6, KV=32,768 and 65,536, q=1 and q=8 | `gv_fattn_kernel` KC=32 / KC=16 / RF6 KC=16 | 9,940 / 12,560 / 14,195 | 186 / 0, 180 / 0, 214 / 0 | 0 | 0 | 0 / 0 |
| C22 RF7 build, smoke KV=32,768, q=1 | `gv7_kernel` | 10,376 | 202 / 0 | 0 | 0 | 0 / 0 |

Both v10 A3B prefills ran with 4,096-token slot capacity, so 256 and 1,024 are prompt lengths. The four-request 512-token panel launched the private-frame vector symbol 33 times among 369 main attention dispatches. Its traced kernel durations sum to 5.76 ms, about 16.2% of the 35.60 ms summed for main attention in that panel. The later four-request 768-token panel dispatched the other two attention kernels and had zero hits of the private-frame symbol. The decode panels contain prefill and generation, with request boundaries available but no per-dispatch KV argument or measurement of scratch bytes. This is a dispatch census with profiled kernel durations and does not establish a latency effect or a scratch-traffic rate. [Census native run identity and actual argv](../mi210-matmul-census-20261127/run.json) · [Request windows and residency](../mi210-matmul-census-20261127/requests.json)

RF4 initializes its scratch resource `s[52:55]` from the incoming private-segment descriptor and adds the wave offset. All 28 sites address that resource in `[4,56]` byte slots. The V source reads use a fixed `block_q8_0` layout, eight dwords plus one halfword, in `fattn-gqa-verify.cu:749–773` at `2f7f5b0df`. `KDIRECT` separately keeps two raw K blocks in registers at lines 775–785. The scratch instructions access spilled private values and the disassembly does not identify a runtime V-load length that they implement. The 14 compiler-reported spills, the 28 ISA sites and the 5,194 dispatches answer different questions. No counter or PC sample here measures how often the sites ran. [RF4 native results](/mnt/raid0/llm/tmp/ak-vattn-limiter-counters-gpu-20261124/out/RESULT.json)

The v10 two-column vector frame initializes its own `s[0:3]` private resource and has both fixed-offset and `offen` scratch accesses. The compiler reports zero register spills. The V input path in `fattn-vec.cuh:93–109,331–380` instead uses `D`, `nthreads_V` and `V_rows_per_thread` as compile-time quantities and loads from `V + k*nb21`. The ISA shows private temporaries being materialized but cannot alone attribute all slots to named source variables. The traced WMMA kernel is the `float`-typed template in `fattn-wmma-f16.cu:23–26`; its V loop and its padded shared accumulator are at lines 93, 144 and 335–379. The 264-element shared accumulator stride for `D=256` is separate from the logical V-load width.

## Head padding and partial KV tiles

- In v10 `ffc1bac82` (`fattn-mma-f16.cuh` blob `17bb58932a6ef6db481e5765083ed3ec7eb67c1b`), lines 952–963 assert `DV % (2*nbatch_V2) == 0` and pass `(i0_start + 2*nbatch_V2 - i0_start)/2` half2 elements. There is no `DVp` padded-head branch. The `oob_check` and `k_VKQ_sup` arguments still bound the KV dimension, which is independent of V head padding. ROCm disables `CP_ASYNC_AVAILABLE` in `common.cuh:290–292`. C22 RF1/2/4, RF6 and RF7 have the same V-bound expression in header blob `6c2c6f04721f4cb2e291caca5954f24e3ced00e6`.
- The candidate cited by the PR has a 512-element unpadded V head. v10 `fattn.cu:555–605` selects other implementations for AMD widths above 256 except the 320/256 case. The MMA device entry point rejects DKQ 512 in `fattn-mma-f16.cuh:1768–1772`. Both v10 and RF7 gfx90a objects contain the corresponding 512/512 `2 × 8` symbol with 16 B private and zero compiler spills. Its ISA calls the unsupported-device handler. No selected trace dispatched it. [Stub metadata, code-object hashes and ISA](join.json)
- The v10 reference suite passed 2,868 supported FLASH_ATTN_EXT cases. It includes f16 `D=128`, query count 75, KV=113 (partial KV tile) and KV=512 (aligned), as well as `D=80` and KV=113. Those logs establish reference correctness for the supported shapes. They do not exercise the upstream `DVp != DV` branch, which is absent in these sources. [v10 reference suite](/mnt/raid0/llm/tmp/ak-c14-c6-dispatch-reprofile-20261119-r2/out/logs/run-v10-backend-ops-FLASH_ATTN_EXT.txt)
- The C22 RF6 comparison uses KV=32,768 as train and 65,536 as holdout, q=1 and q=8, `D=256`, 24 query heads, 4 KV heads and q8_0 K/V. The dispatch traces use `tail=0`. The reference logs separately pass `tail=1001` cases at 32,768 and 65,536 for OFF/RF1/RF6. The first RF7 binary only supplied a KV=32,768, q=1, `tail=0` smoke trace. Its full row failed correctness before timed holdout work, including eight listed tail cases. This audit does not treat RF7 as deployed or the smoke as a complete gate. [RF6 reference and results](/mnt/raid0/llm/tmp/ak-c22-vattn-rf6-gate-gpu-20261124-r2/out/RESULT.json) · [RF7 gate result](/mnt/raid0/llm/tmp/ak-c22-vattn-rf7-op-gpu-20261125/out/RESULT.json)

## Verification

The replay reads the sealed host library from each build and checks the resolved ELF against its store `SHA256SUMS`. It extracts the individual gfx90a ELF payloads from `.hip_fatbin`, joins raw mangled or fully demangled dispatch names to metadata, and disassembles the matched function with the installed ROCm LLVM. Object SHA-256, byte range in the host ELF, exact symbols, VGPR/AGPR/SGPR resources, LDS, private bytes and the scratch-related instructions are in [join.json](join.json). The v10 f16-vector translation unit’s original `.o` disambiguates device copies of the 128×1 symbol and its split-combine helper. The program hashes the original translation unit’s embedded gfx90a payload and takes the matching copy from the checked library. The production A3B trace’s repeated mask/combine helpers are shown with their dispatch IDs and zero private bytes, with no per-object attribution for those auxiliaries. All main attention kernel names in those windows joined exactly. No host ELF here advertises a GNU build ID, so the joins use manifest-verified ELF SHA-256 and per-object SHA-256.

```sh
python3 audit.py cases.json /tmp/fattn-private-segment-replay.json
cmp join.json /tmp/fattn-private-segment-replay.json
```

The replay used the rowflow light CPU grant `build-codex-fattn-private-segment-20261127T153420Z-2587c1`. The GPU data was reused from the archives and the census row. This audit launched no GPU jobs and used no production edits. RF4’s private register spills and the v10 A3B two-column vector private frame are separate observations for their owning performance work.

Next: ROCm kernel authoring owner files the absent-path closure and records the A3B vector-frame observation with the MI210 census.
