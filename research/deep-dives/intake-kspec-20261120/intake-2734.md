# Skills catalog - AMD Skills documentation

- **Intake**: intake-2734 (`intake-2734#record`)
- **Source**: https://rocm.docs.amd.com/projects/amd-skills/en/latest/catalog.html
- **Verification**: dive-verified · read depth FULL
- **Disposition**: integrated; handoffs: rocm-kernel-authoring.md
- **Run**: intake-kspec-20261120 (research-intake Stage 2/2b, 2026-11-20)

## Reader should conclude

Cite the skill names and roles. The FlyDSL skills target gfx942/gfx950; do not treat them as MI210 execution arms. Use the Moat wave64 checklist as reading material for HIP porting.

## Key claims (anchored)

0. The catalog lists flydsl-kernel-authoring and flydsl-kernel-trace-analysis, both sourced from FlyDSL.
   - Server-native table: "flydsl-kernel-authoring Write, review, and understand FlyDSL GPU kernels for AMD GPUs"
1. moat-cuda-to-rocm adds a ROCm/HIP backend to a CUDA project while the CUDA build keeps working side by side.
   - Cross-stack table: "moat-cuda-to-rocm Add a ROCm/HIP backend to a CUDA project so it runs on AMD GPUs while the CUDA build keeps working side by side"
2. Most skills are federated from the product team repository; a few are maintained in-repo in amd/skills.
   - Intro: "Most skills are federated: the product team maintains the skill in its own repository"
   - Intro: "Skills marked in-repo are maintained directly in amd/skills"
3. flydsl-kernel-trace-analysis collects rocprofv3 instruction-level traces and counters for a GPU kernel.
   - Server-native table: "Collect rocprofv3 instruction-level traces and counters for a GPU kernel"

## Dive record

2026-11-20 Stage-2b dive (sonnet; catalog read in full; SKILL.md bodies read from github.com/amd/skills raw files, outside the anchor file). Corrects intake-2724's dive: moat-cuda-to-rocm IS in the official catalog; Moat lives at github.com/AMD-Ecosystem/moat (MIT); jeffdaily/moat is a wrong owner (404). flydsl-kernel-authoring targets gfx942/gfx950 with ROCm 7.2 and does not mention gfx90a; flydsl-kernel-trace-analysis is rocprofv3 ATT plus hotspot analysis and is not FlyDSL-specific (ATT on gfx90a/ROCm 6.2 unverified); moat-cuda-to-rocm carries a wave32/wave64 semantic checklist (64-bit lane masks, zero-init, stream order) and names MI200-class CDNA in its wave64 gate. In-house stance: rocm-kernel-authoring.md:L2249-L2251 @b5c5fe7 (GEAK/FlyDSL scoped to gfx942/gfx950, not a current MI210 arm). CPU: none. Surfaced github.com/amd/skills and github.com/AMD-Ecosystem/moat (wave-2 candidates). lane_head b5c5fe7b4e63
