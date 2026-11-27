# Using PC sampling

[Primary source](https://rocm.docs.amd.com/projects/rocprofiler-sdk/en/latest/how-to/using-pc-sampling.html) · intake-3020 · 2026-11-27

Official ROCprofiler-SDK 1.4.2 documentation. Enumerate supported combinations using rocprofv3 -L/--list-avail; example gfx90a advertises host_trap/time, while gfx942 provides stochastic/cycle/pow2 and issue or stall information. Host trap can skid up to two instructions including across branch edges. Docs give an example gfx942 max interval 2^31 versus blog's 2^20 stated hardware ceiling, so capability advertisement and measured setup should govern any experiment. ROCm 7.0 firmware corrections are for MI300X and do not create MI210 stochastic support. Versioned 6.4.1 source documents gfx90a or later and host trap time-based microsecond configuration, still subject to actual availability.

Current ROCm 6.2 production and approved rocprofv2 trace do not change. On the MI210 use optional host-trap on a compatible isolated SDK/driver only once capability is actually advertised. Host CPU 9655 can contribute analogous CPU sampling through its own tools.

## Evidence

- The ROCprofiler SDK example advertises host-trap time sampling on gfx90a. [PC sampling availability and configuration, HTML L703–713](https://rocm.docs.amd.com/projects/rocprofiler-sdk/en/latest/how-to/using-pc-sampling.html)
- Host-trap samples may appear up to two instructions from the actual latency site. [Host-trap PC sampling and arbitrary sampling skid, HTML L1590–1592](https://rocm.docs.amd.com/projects/rocprofiler-sdk/en/latest/how-to/using-pc-sampling.html)
- The SDK documents sampling support on AMD GPUs starting at gfx90a. [Introduction, HTML L472](https://rocm.docs.amd.com/projects/rocprofiler-sdk/en/docs-6.4.1/how-to/using-pc-sampling.html)

## Scope and local transfer

Versioned ROCm documentation and HPCToolkit corroborate host trap on MI200+ and skid. The SDK reference clarifies the blog's ambiguous phrase 'arbitrary sampling skid' as up to two instructions, including around branches; interval ceiling mismatch remains.



The 6.2 ATT adapter is already the approved stall classifier. A second route only earns its cost if it maps unresolved PCs on a separately qualified stack. Inventory build IDs and DWARF line tables for served MMQ, MMVQ and attention code objects; map representative addresses offline and record coverage for stripped objects. Keep host-trap collection behind an isolated compatible toolchain and driver capability check.

## Sources surfaced

No additional decision-changing source identified.
