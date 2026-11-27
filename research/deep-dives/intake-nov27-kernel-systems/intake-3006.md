# Beyond Counters: Instruction-Level GPU Hotspot Profiling with PC Sampling in ROCprofiler-SDK

[Primary source](https://rocm.blogs.amd.com/software-tools-optimization/pc-sampling-rocprofiler/README.html) · intake-3006 · 2026-11-27

AMD's 2026-11-26 guide layers kernel dispatch trace and counters with host-trap PC neighborhoods, stochastic wave issue and stall classification, then ATT as needed. A precompiled code object gives ISA attribution, while -g adds source-line mappings. Host trap uses host timing and wave-slot traps, has 1–2-instruction skid and lacks stall cause. Stochastic starts at CDNA3 and records per-wave issue, stall reason, wave count and JSON arbiter state. One MI300A/gfx942 under ROCm 10.1, 8192-cubed naive GEMM versus 16x16 LDS tiled, one timed launch after one warmup per binary, 357.1→118.0 ms. ~12.2x fewer WAITCNT samples was the two selected compute lines only (146,507 versus 12,008), not a kernel-wide WAITCNT reduction. Host-trap sample counts also change with wave residency and overhead, so preserve separate timing as the decision metric. The source attributes naive waiting specifically to uncoalesced B, but its example has B contiguous across x lanes in a row and the rewrite changes A/B traffic, staging and reuse together. The hotspot evidence supports wait localization, not isolated B causality. Blog's 2^20 stated hardware ceiling differs from the SDK docs' gfx942 advertised Max_Interval=2147483648 example, so query the actual installed capability and verify observed cadence.

handoffs/active/rocm-kernel-authoring.md:L1122-L1132 @ b93bd31; VATTN-LIMITER-1 at L1147. Use current ROCm 6.2 kernel traces/PMC and adopted rocprofv2 ATT adapter. MI210 host-trap can add hotspot-only evidence on an isolated compatible stack, capability- and privilege-gated. The EPYC 9655 has no use for rocprof; use CPU perf/IBS as an analogous source of evidence.

## Evidence

- The guide places the PC sampling tooling in ROCm 6.4 and later. [Introduction, HTML L785–788](https://rocm.blogs.amd.com/software-tools-optimization/pc-sampling-rocprofiler/README.html)
- MI200 can use host-trap hotspot sampling and lacks stochastic sampling. [Method 1 §When to Use, HTML L981](https://rocm.blogs.amd.com/software-tools-optimization/pc-sampling-rocprofiler/README.html)
- The worked GEMM example reports 357.1 ms for the naive kernel and 118.0 ms with 16×16 LDS tiling. [Real-World Use Case §Step 4 timing table, HTML L1406–1410](https://rocm.blogs.amd.com/software-tools-optimization/pc-sampling-rocprofiler/README.html)
- The WAITCNT reduction refers to two selected hot lines. [Real-World Use Case §Step 4 observations, HTML L1527](https://rocm.blogs.amd.com/software-tools-optimization/pc-sampling-rocprofiler/README.html)

## Scope and local transfer

Official AMD SDK docs confirm skid and gfx942 stochastic support, but advertise a higher gfx942 maximum in their configuration example. HPCToolkit's GPU profiling documentation independently corroborates ROCm 6.4 onset, MI200 host trap and skid, not AMD's GEMM numbers.



The 6.2 ATT adapter is already the approved stall classifier. A second route only earns its cost if it maps unresolved PCs on a separately qualified stack. Inventory build IDs and DWARF line tables for served MMQ, MMVQ and attention code objects; map representative addresses offline and record coverage for stripped objects. Keep host-trap collection behind an isolated compatible toolchain and driver capability check.

## MI210 sampling flow

For an isolated ROCm 6.4+ or TheRock candidate, record the driver, firmware, toolchain and exact served code-object identity. On versions exposing it, inspect `rocprofv3-avail info --pc-sampling` (SDK versions also document `rocprofv3 -L`). Require the gfx90a agent to advertise `host_trap` with a time interval. Choose an advertised interval and profile the pinned workload using the beta-enabled host-trap options from the installed SDK. Filter warm-up launches and join the target dispatch, code-object ID and sampled instruction offset to that ELF’s disassembly. Matching DWARF line tables permit a HIP file/line annotation; a stripped object still permits instruction-offset analysis. Record unmapped samples and distinct dispatch counts. Inspect neighboring instructions because the trap can skid. Compare with unprofiled wall time. Production 6.2 retains its separate ATT route for attribution. [AMD SDK reference](https://rocm.docs.amd.com/projects/rocprofiler-sdk/en/latest/how-to/using-pc-sampling.html)

## Sources surfaced

- https://rocm.docs.amd.com/projects/rocprofiler-sdk/en/latest/how-to/using-pc-sampling.html
