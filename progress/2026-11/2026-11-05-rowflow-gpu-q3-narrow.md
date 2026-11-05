# 2026-11-05 — rowflow gpu-q3 NARROW (operator: "Narrow + emergency deploy")

- Decision: a GPU grant holds gpu-quiet + its host threads t184-191; a GPU TIMING grant also holds their SMT-sibling
  cores 88-95 and NEVER the rest of q3 (72-87 + siblings 168-183 stay grantable to CPU rows). Replaces "GPU timing holds
  all of q3". Evidence: q38p4b-int8-20261105 refused "needs gpu-quiet,q3,t184..t191: q3 busy" while an 8-core AITER
  build held 80-87/176-183.
- rowflow.py (frozen, emergency gate): `GPU_Q3_TOKENS` = gpu-quiet + c88-95 + t184-191; `lends` always empty; publish
  refuses a gpu-q3 contract touching 72-87 (`GPU_TIMING_NEVER_HELD`); declared `gpu-q3` is 8 cores. GPU correctness /
  production rows unchanged (gpu + 184-191).
- Tests: `test_rowflow_q3_coexist.py::GpuTimingNarrow` (holds never include 72-87; 8-core q3 build + GPU timing grant
  concurrently, both orders; old-rule negative control); replay scenarios `gpu-timing-narrow-q3-concurrent-with-8core-build`
  and `-build-beside-open-timing`; gate negative control runs the scenario against a candidate copy with the old
  whole-q3 option and requires it to FAIL. Unit 308 passed, replay 34 passed.
- rowflow2: `grant_need` = parse_cpus → timing_need → `gpu_timing_need` (gpu exclusive, not quiet: + 88-95 via
  `Need.fixed`); `admit/_pick/_make_hold/fits_need` honour it; oracle `rf2.oracle_need`; incident `test_8`. 54 passed.
- Docs: SKILL.md §2, design doc decision 8, gitnexus-compute-claims note.
