# ROCm 10.2.0: Advancing Performance, Stability, and Developer Experience (AMD blog)

- **Intake**: intake-2724 (`intake-2724#record`)
- **Source**: https://rocm.blogs.amd.com/ecosystems-and-partners/rocm-10.2-blog/README.html
- **Verification**: dive-verified · read depth FULL
- **Disposition**: integrated; handoffs: rocm-kernel-authoring.md
- **Run**: intake-kspec-20261120 (research-intake Stage 2/2b, 2026-11-20)

## Reader should conclude

Companion of intake-2694. Cite the Skills names, the install command and the AITER scope. It says nothing about gfx90a; do not infer support or exclusion from it.

## Key claims (anchored)

0. AMD Skills now covers 12 AMD projects and this release adds three kernel and porting skills, including one that lets Moat port a CUDA project to ROCm and HIP; they install with npx skills add amd/skills.
   - ROCm CLI and AMD Skills: "This release adds three new skills for kernel work and porting"
   - ROCm CLI and AMD Skills: "A third skill allows Moat to port a CUDA project to run on AMD GPUs with ROCm and HIP"
   - ROCm CLI and AMD Skills: "Developers can add them all with npx skills add amd/skills"
   - ROCm CLI and AMD Skills: "The collection now covers 12 AMD projects"
1. Prebuilt AITER kernels are named only for Instinct MI300X, MI325X, MI350X and MI355X; on Radeon and Ryzen AI they compile at first use.
   - Frameworks: "Instinct MI300X, MI325X, MI350X and MI355X GPUs get prebuilt AITER kernels"
   - Frameworks: "On Radeon and Ryzen AI, the kernels compile automatically the first time they are used"
2. FlyDSL kernels in PyTorch are named for MI350 and TDM for MI450; the blog has no gfx90a, MI210 or ROCm 6.2 content.
   - Training / PyTorch: "FlyDSL kernels for MI350, Tensor Data Mover (TDM) for MI450"

## Claim corrections

- claim 0: **narrowed** — Companion of intake-2694, not a duplicate: the release notes have no Skills content. The blog names no hosting URL for the skills.
- claim 1: **unaffected** — Confirmed; Stage-1 omitted the compile-on-first-use note.

## Dive record

2026-11-20 Stage-2 dive (sonnet; full read). grep for gfx90a / MI210 / 6.2 = 0. Search (independent of the blog): ROCm/FlyDSL is a Python DSL + MLIR stack (docs say tested on ROCm 6.x/7.x; gfx90a codegen not established); jeffdaily/moat describes porting CUDA GitHub projects to ROCm/HIP; the exact skill name moat-cuda-to-rocm was not confirmed in the official catalog. Skills are agent text packages and do not require ROCm 10.2; what they emit must still target gfx90a/ROCm 6.2. In-house consumer: rocm-kernel-authoring.md agentic-rocm-kernel-authoring track. lane_head 1650e3d9315f (pre-rebase sibling of e9ee76c07; in-house cites @1650e3d) Stage-2 close-out (2026-11-20): AMD Skills catalog, FlyDSL docs and FlyDSL blog ingested as intake-2734..2736; github.com/jeffdaily/moat declined as unreachable (HTTP 404, gh api 404) and superseded by intake-2734's finding that Moat lives at github.com/AMD-Ecosystem/moat (ingested as intake-2746) and that moat-cuda-to-rocm IS named in the official catalog (this entry's dive said unconfirmed); github.com/ROCm/aiter release v0.1.29 declined (already cross-referenced; in-house AITER work covers it).

## Depends on

- intake-2694 (claim 2): The gfx90a-still-supported conclusion (release notes) is what keeps the skills applicable; this blog adds no counter-evidence.
