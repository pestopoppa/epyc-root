# amd/skills: Official AMD catalog of AI agent skills

- **Intake**: intake-2745 (`intake-2745#record`)
- **Source**: https://github.com/amd/skills
- **Verification**: dive-verified · read depth PARTIAL
- **Disposition**: integrated; handoffs: autokernel-loop.md, coordination-and-churn-pipeline.md, rocm-kernel-authoring.md
- **Run**: intake-kspec-20261120 (research-intake Stage 2/2b, 2026-11-20)

## Reader should conclude

Use the wave64 fault list as a static-scan source for HIP candidate diffs. Do not adopt the rocprofv3 ATT collection recipe on ROCm 6.2; only its analysis layer ports.

## Key claims (anchored)

0. amd/skills is federated: product teams maintain skills in their own repositories and amd/skills vendors a copy.
   - README federation: "Most skills are federated: the product team maintains the skill in its own repository, and amd/skills vendors a copy."
1. The catalog includes a CUDA-to-ROCm porting skill, a kernel evaluator and a rocprofv3 trace-analysis skill that maps stall hotspots to source lines and produces an optimization plan.
   - README catalog: "Collect rocprofv3 instruction-level traces and counters for a GPU kernel, map the top stall hotspots back to source lines, and produce an optimization plan."
   - README catalog: "Add a ROCm/HIP backend to a CUDA project so it runs on AMD GPUs while the CUDA build keeps working side by side."
   - README catalog: "Evaluate GPU kernel correctness and performance, compare kernel implementations"
2. The CPU serving skill targets vLLM with zentorch on EPYC, not llama.cpp.
   - README catalog: "Serve LLMs on AMD EPYC CPUs with vLLM and zentorch"

## Dive record

2026-11-20 Stage-2b wave-2 dive (sonnet; PARTIAL: README plus moat-cuda-to-rocm SKILL.md index and references faults-wavefront.md, faults-numerics.md (part), validation.md, no-hip-equivalent.md, and flydsl-kernel-trace-analysis/SKILL.md read in a shallow clone @ 2470f33cbd47; other skills not read). Repo-file evidence (not machine-anchorable): faults-wavefront.md lists measured wave64 hazards: 64-bit __ballot/__activemask truncated to 32-bit, 32-bit mask arithmetic (1<<K) on 64-lane masks, logical 32-lane warps calling wave-wide collectives, blockDim/warpSize==0 on sub-wavefront blocks, __smid() up to 125 on a 104-CU gfx90a GCD overrunning per-CU pools, size-threshold kernels unreachable by small harnesses (gfx90a memory fault above 3072 elements), plus a validate-both-widths / cross-arch consistency rule; all measurements cite ROCm 7.x, none 6.x. The ATT skill's rocprofv3 + advanced_thread_trace collection does not run on our stack: rocprofv3 6.2 has no thread trace, only rocprofv2 --plugin att (rocm-kernel-authoring.md:L1535 @901b3fe); only its stall taxonomy and occupancy math port. Magpie, FlyDSL and skillscope repos declined (already covered or governance-only). lane_head 901b3fe44a30
