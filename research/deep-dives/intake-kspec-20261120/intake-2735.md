# FlyDSL documentation (landing page)

- **Intake**: intake-2735 (`intake-2735#record`)
- **Source**: https://rocm.docs.amd.com/projects/FlyDSL/en/latest/index.html
- **Verification**: dive-verified · read depth FULL
- **Disposition**: integrated; handoffs: rocm-kernel-authoring.md
- **Run**: intake-kspec-20261120 (research-intake Stage 2/2b, 2026-11-20)

## Reader should conclude

gfx90a is not in FlyDSL's architecture list; do not plan MI210 FlyDSL kernels without a compile probe.

## Key claims (anchored)

0. FlyDSL is a Python DSL and MLIR compiler stack for explicit-layout-algebra GPU kernels on AMD ROCm/HIP.
   - Intro: "a Python DSL and MLIR compiler stack for authoring high-performance GPU kernels with explicit layout algebra, targeting AMD ROCm/HIP GPUs"
1. The docs site is built from main and may describe APIs newer than the published package.
   - Note admonition: "This site is built from main and may describe APIs newer than the published package"
2. The docs expose kernel authoring, kernel tuning, in-kernel wave tracing and offline autotune guides.
   - Guides nav: "Kernel authoring Kernel tuning In-kernel wave tracing Offline autotune configs"

## Dive record

2026-11-20 Stage-2b dive (sonnet). Architecture matrix read outside the anchor file (ROCm/FlyDSL README raw; docs installation page): gfx942, gfx950, gfx1250, gfx11*/gfx120* RDNA; gfx90a absent; no ROCm floor stated (README says tested on ROCm 6.x and 7.x). No cdna2 atom module listed. Adds no kernel technique beyond intake-2697/intake-2703. A port to gfx90a is a build cost (wave64 and MFMA shared with gfx942), not a decline reason; viability unknown until a compile probe. lane_head b5c5fe7b4e63 Stage-2 close-out (2026-11-20): github.com/ROCm/FlyDSL declined as a further source (already indexed as intake-2703; gfx90a viability is a compile-probe question).
