# ws58 2026-10-31 dive record: w5_verif

Markdown rendering of `w5_verif.yaml` (the original is kept beside it) so the wiki scanner sees this dive. Intake IDs are as the dive recorded them; read them as `#record` references. Digit runs of 12+ digits are written grouped.

```yaml
answer: 'Port race/deadlock now; port equivalence only if a cheap probe shows it catches something. Race checking needs addresses, not values, and our kernels share LDS across waves: in the v10 gfx90a code object, MMVQ has 161/279 kernels with s_barrier, MMQ 147/672, FA-mma 138/302, FA-vec 41/49. In AK GPU work, 236/627 unique mechanisms and 15/31 keeps touch sync. Build at the AMDGCN ISA level (disassembled code object), not LLVM IR: IR hides the inline-asm waits and LDS-DMA ordering, and cannot check ISA-edited candidates. Cost: 8-11 kLoC new Rust plus ~12 kLoC reused, 6-9 engineer-weeks; first milestone MMVQ plus FA-vec. Equivalence is declined for quant kernels on coverage (~75% of AK GPU rows are bit-level). For FA/GDN/mmvf, seeded sub-tolerance mutants decide. KERN-8 becomes a task targeting MMQ/FA register-allocation pathologies.'
# Evidence base (read-only; no builds, no GPU):
# - v10 gfx90a code object: production kernel store /mnt/raid0/llm/kernels/production/gpu/libggml-hip.so.0.16.0, split
#   into 135 per-TU gfx90a code objects and disassembled with ROCm llvm-objdump --mcpu=gfx90a (7059 kernel symbols, 6.19M
#   lines). The scratch is in scratch:dive-ws58-20261031/dive/verif/opcodes_by_family.json (disassembly scratch moved to trash via guarded_rm). Per-family
#   counts (kernels with s_barrier / with ds_*): MMVQ 161/166 of 279, plus 2 with an LDS-DMA buffer_load...lds; MMQ
#   147/147 of 672; FA-mma 138/138 of 302; FA-tile 126/136 of 376; FA-vec 41/41 of 49 (1 with an atomic); GDN 0/0 of 32;
#   quantize 2/2 of 126; dequant/convert 4/4 of 54; argsort/topk 2/2 of 26.
#   Distinct opcodes (lexical classification, approximate): MMVQ 178 (26 memory, 15 ctrl/sync, 43 float-opaque, 94
#   integer); MMVQ+FA-vec 228; all hot families 316; whole library 398. The scaffold lowers 8.
# - Source anchors (frozen tree @ffc1bac82):
#   - mmvq.cu:1038-1093 is a gfx90a LDS-DMA double buffer (raw buffer_load...lds, then asm s_waitcnt vmcnt(0), then
#     sched_barrier, whose comment reads "MANDATORY - else the compiler hoists the LDS consumer above the wait", then
#     __syncthreads). It is env-gated: GGML_CUDA_Q8_PREFETCH, default 0 (mmvq.cu:1713-1716).
#   - mmvq.cu:804-830: CDNA2 MMVQ uses 4 or 8 warps, so the cross-warp tmp_shared reduction is a real inter-wave hazard,
#     and the AK keep akm-cdna2-q8-b1-eight-warp-four-row changed its geometry.
#   - quantize.cu:100-117 holds hand-placed s_nop DPP wait states.
#   - The MMQ stream-k fixup is a separate kernel launch (mmq.cuh:1366), and blocks write per-block tmp_fixup slots
#     (mmq.cuh:887).
#   - The FA-vec cross-block protocol is atomicAdd/atomicExch (fattn-vec.cuh:534,569). The MI210 FA dispatch is MMA_F16
#     for head dim <=256 (fattn.cu:571-588).
#   - gated_delta_net.cu uses warp_reduce only (no LDS, no barrier).
#   - DFlash2 has no GPU kernel of its own: it is host logic (common/speculative.cpp:1290-1405, selector_top_k becomes
#     sampler top_k) over the ggml argsort/top-k kernels.
# - ptx_verifier @a39292a: volta_graph 2361 LoC and volta_graph_check 7709 LoC are ISA-independent.
#   - The graph model has Access, barrier generations, AsyncIssue/AsyncComplete and GroupCommit
#     (volta_graph/src/model.rs:34-83). barrier_epoch.rs and memory_conflict.rs are the race/deadlock checks.
#   - volta_amd_analysis (1678 LoC) is gfx950-only (lower/mod.rs:43). It models wave64 lanes and pending registers, has
#     no exec-mask model, and "records no events yet ... passes every graph check vacuously" (analysis.rs:49-50). Its
#     race path therefore currently proves nothing.
#   - volta_ptx_analysis (43 kLoC) is the PTX frontend and is not reusable.
# - AK corpus (/mnt/raid0/llm/autokernel/loop-memory/patches, experiments.md; grep over changed lines, approximate):
#   - 627 unique GPU mechanisms, 236 touch barrier/__shared__/shuffle/DPP/atomic lines. Of those touching sync: barrier
#     77, __shared__ 74, DPP/cross-lane 214, atomic 10, stream-k 23.
#   - 15 of 31 keeps touch sync.
#   - Experiment rows by target: MMVQ/vec_dot 659, quantize_q8_1 192, fattn 183, dequant 139, MMQ 126, rms_norm 122,
#     rope 52, GDN 24.
#   - No GPU race incident is recorded, and none could be, because no detector exists (t0_provider.py:305-307,:3662).
# - The research repo already has scripts/kernel_rnd/gfx90a_isa_audit.py (1061 LoC: fatbin split, kernel descriptor,
#   notes, per-kernel disassembly). It is the input stage for both tasks (agentic-rocm-kernel-authoring.md
#   INF03-REGAUDIT-1/2). INF03-REGAUDIT-1 measured MMQ Q8_0 J=64 at 256 VGPR with 37 spills, and MMA-FA DKQ>=192 at 512
#   VGPR with hundreds of reloads per iteration. AK-MMQ-H10 (J-cap) came back NEGATIVE (agentic:1224-1227).
# Coverage matrix (race / deadlock / equivalence), with Volta's limits applied:
#   MMVQ: race YES (LDS cross-warp reduction; LDS-DMA with vmcnt as the completion point); deadlock YES (early return
#     after barrier); equivalence NO, because the quant unpack is bit-level. Only the fp reduction epilogue is
#     real-valued.
#   MMQ: race YES (12 barrier sites in mmq.cuh; tmp_fixup slots are disjoint per block, so they are checkable as global
#     write sets); deadlock YES; equivalence NO (quant; stream-k changes CTA responsibilities; Volta checks CTA0 only).
#   FA-mma/tile: race YES (KV_max is mask-derived, so feed the concrete test mask); equivalence PARTIAL. Online softmax is
#     in Volta's sum p*e^h class, but -inf masking is outside the reals, and only CTA0 with parallel_blocks=1 is checked.
#   FA-vec: race YES within a workgroup; the cross-workgroup atomic completion protocol is OUT (UNKNOWN); equivalence
#     only with a single block.
#   GDN: race N/A (no LDS or barrier; wave-synchronous); equivalence PARTIAL-YES (polynomial x exp(g) recurrence). It
#     needs cross-lane DPP/swizzle value semantics, which original Volta lacks.
#   DFlash2 selector / argsort / top-k: race small (2/26 kernels with barrier); equivalence NO (data-dependent sort).
#   dequant/convert, quantize_q8_1: race negligible; equivalence NO (bit-level, rounding). KERN-4 enumeration owns these.
#     The inline-DPP s_nop wait states are a hardware-hazard class, not a race, and get a lint in RVP-RACE-2 M2.
# Level choice:
#   - HIP source: would need a C++/template frontend and misses compiler scheduling. Rejected.
#   - LLVM IR (-emit-llvm): about 60 IR ops plus amdgcn intrinsics, but waitcnts are not yet inserted (SIInsertWaitcnts
#     runs later), inline asm is opaque (mmvq.cu:1063, quantize.cu:108, common.cuh:749), the sched_barrier hoist hazard is
#     invisible, and ISA-edited KERN-8 candidates have no IR. Rejected for race.
#   - AMDGCN ISA from the built code object (the same artifact as C5-ISA-1 and INF03-REGAUDIT): chosen. Float/MFMA ops are
#     handled by one generic opaque rule, so the exact-semantics work is about 150 integer + 48 memory + 16 control ops.
# RVP-RACE-1 (plan text) review:
#   - It WOULD catch whether served-shape repetition sees a deleted source barrier at 3 sites.
#   - It would NOT catch:
#     (a) races that cannot manifest because the workgroup is a single wave (needs a waves-per-WG control);
#     (b) deletions the compiler masks (it keeps an s_waitcnt lgkmcnt) or turns into reordering (needs an ISA proof of
#         s_barrier absence, as KERN-1 required);
#     (c) timing-dependent WAR races in double buffers, which appear only when DMA outruns compute;
#     (d) ISA-only defects (a dropped vmcnt wait, a consumer hoisted above the wait), because source mutation cannot
#         create them;
#     (e) any site it did not mutate.
#   - Its decision rule is also weaker than KERN-1's: "passes in all 20 runs" should be "passes in >=1 of 20", because a
#     single-shot gate accepts a race that slips through 1 time in 20. Amended text below.
tasks:
- task_id: RVP-RACE-1
  owner: handoffs/active/rocm-verify-profile-backend.md
  text: '- [ ] **RVP-RACE-1 — Measure whether the correctness gate can see a race at all (intake-2557#record, intake-2570#record).** GPU: in a llama.cpp-experimental worktree from the v10 tip build seeded-race HIP mutants, each deleting one barrier: MMQ tile load (mmq.cuh barrier sites), MMVQ cross-warp tmp_shared reduction (mmvq.cu nwarps 4 and 8 routes), MMVQ LDS-DMA double buffer (mmvq.cu:1063-1065, run with GGML_CUDA_Q8_PREFETCH=1), FA-mma tile softmax; prove each mutant structurally (s_barrier count of that kernel in the disassembled gfx90a code object drops vs the unmutated build) and record waves-per-workgroup at each served shape (a single-wave site is excluded as not a race). Run the AK served-shape test-backend-ops case set 20x per mutant and 20x on the unmutated build (frozen case manifest, per-run raw verdicts and NMSE kept). CPU: build test-backend-ops with ThreadSanitizer using LLVM libomp with Archer annotations and run the threaded ops on the v10 anchor. Decision rule: a GPU mutant that passes the gate in >=1 of 20 runs is a measured race miss; the unmutated build must pass 20/20; the mutant set becomes the fixture set of RVP-RACE-2 either way. The v10 anchor must produce zero TSAN reports beyond a documented suppression list.'
  acceptance: 'Per-mutant table (site, s_barrier delta, waves/WG, pass count out of 20, max NMSE) plus the 20/20 control, committed with raw verdicts; TSAN anchor report with suppression list; fixtures handed to RVP-RACE-2.'
  replaces_rows: [KERN-1, KERN-10, PRE-2557, PRE-2570]
- task_id: RVP-RACE-2
  owner: handoffs/active/rocm-verify-profile-backend.md
  text: '- [ ] **RVP-RACE-2 — gfx90a AMDGCN race/deadlock executor as the GPU race_detector_id (intake-2570#record, intake-2557#record).** Not trigger-gated: 236 of 627 unique AK GPU mechanisms and 15 of 31 keeps touch sync, and v10 already ships hand-ordered LDS-DMA (mmvq.cu:1038-1093). Build in Rust on the MIT ptx_verifier @a39292a, reusing volta_graph and volta_graph_check (barrier_epoch, memory_conflict) unchanged, and extending volta_amd_analysis from gfx950/8 opcodes to gfx90a. Input is the disassembled code object of the built candidate (split with research scripts/kernel_rnd/gfx90a_isa_audit.py, the same artifact as C5-ISA-1). Launch grid, workgroup size and kernarg come from a small HIP launch-capture shim on a correctness-only served-shape run. Model: a concrete integer/address lattice with float/MFMA results opaque; exec mask; wave64 with per-wave program order (one event per wave-instruction, with the byte footprint of active lanes, plus an intra-instruction lane write-write check); ds_* complete at lgkmcnt; buffer_load...lds as AsyncIssue/AsyncComplete, completed conservatively at vmcnt(0); s_barrier as barrier generations; any branch or address that depends on an opaque value yields UNKNOWN (fail-closed, never ACCEPT). Index inputs (MoE ids, FA mask) are fed concretely. M1 (3-4 eng-weeks, the MMVQ + FA-vec opcode set, 228 distinct on v10): check WG0, the last WG and all boundary/tail WGs per served shape. M1 is accepted when it gives 0 findings on v10 MMVQ (both nwarps routes, plus q8pf with GGML_CUDA_Q8_PREFETCH=1) and on FA-vec at the AK served shapes, flags 100% of the RVP-RACE-1 MMVQ/FA mutants plus 2 ISA-only mutants that source mutation cannot make (delete the q8pf s_waitcnt vmcnt(0); move the first LDS read of a tile above its s_barrier; reassembled with clang -target amdgcn-amd-amdhsa -mcpu=gfx90a), and finishes in <=10 min per kernel instance on one core. Any production finding is triaged to a true race or a model bug before acceptance. M2 (+2-3 weeks): MMQ, FA-mma, FA-tile, quantize, argsort/topk (316-opcode union, MFMA/AGPR opaque); cross-WG global write-set overlap on sampled WGs (MMQ tmp_fixup disjointness); deadlock via barrier epochs; a gfx90a wait-state hazard lint for inline-asm regions (quantize.cu:100-117 DPP s_nop) cross-checked against an LLVM-compiled reference. The FA-vec atomic completion protocol is declared out of scope (UNKNOWN). M3: register as race_detector_id in execution/t0_provider.py for GPU routes whose diff or ISA touches barrier/__shared__/ds_/s_waitcnt/LDS-DMA/inline asm, after M1+M2 acceptance. Budget 8-11 kLoC new plus about 12 kLoC reused, 6-9 engineer-weeks, Codex-delegable; zero GPU time beyond the capture runs.'
  acceptance: 'M1 receipt: per-kernel verdicts (ACCEPT/RACE/UNKNOWN) on v10 MMVQ+FA-vec at the frozen served-shape manifest with 0 RACE; a mutant table showing every RVP-RACE-1 MMVQ/FA mutant and both ISA-only mutants flagged; runtime per instance. M3 done when t0_provider emits a non-null race_detector_id for a sync-touching GPU candidate.'
  replaces_rows: [KERN-2, KERN-11]
- task_id: RVP-EQV-1
  owner: handoffs/active/rocm-verify-profile-backend.md
  text: '- [ ] **RVP-EQV-1 — Decide the equivalence-checker port by measured miss rate, quant kernels declined on coverage (intake-2570#record, intake-2557#record).** Decision part 1, decline: no Volta-class equivalence for MMVQ, MMQ, quantize_q8_1 or dequant. They are bit-level (nibble unpack, rounding), which Volta does not cover (floats are reals, conversions are the identity), and they make up about 75% of AK GPU experiment rows (1116 of 1497). KERN-4 enumeration owns decode exactness. Decision part 2, a deciding probe for the real-valued subclass (FA-mma/FA-tile at parallel_blocks=1, GDN recurrence, mmvf float GEMV). In a llama.cpp-experimental worktree from the v10 tip, build 8 seeded sub-tolerance algebraic mutants: FA online-softmax rescale skipped only when the running max changes after the first KV tile; FA KV loop dropping the last KV column; FA-tile dropping one tail tile at a non-multiple context; GDN exp(g) decay dropped at a chunk boundary; GDN beta dropped for one head; mmvf dropping the final partial k-block at ne00 % tile != 0; and two controls with an O(1) error. Prove each mutant structurally (ISA diff of that kernel). Run the AK served-shape gate plus the AKX-ALL-31 edge families and the KERN-5 worst-element bound, 5 seeds each, on a frozen case manifest, keeping per-mutant per-seed raw verdicts and NMSE; the unmutated v10 build must pass 5/5 seeds. Decision rule: if any non-control mutant survives every gate on >=1 seed, open the equivalence milestone for that subclass on the RVP-RACE-2 interpreter (symbolic float values, v_exp_f32 as 2^x, cvt as identity, the 2 MFMA lane layouts in use, DPP/swizzle value moves, FA and GDN reference specs; estimate 4-6 kLoC, 4-6 engineer-weeks; advisory, never a speed-blocking gate, because intake-2555 Table 2 shows proof-restricted FA at 0.78x vs 1.37x). If all are caught, record the catch table and close the equivalence port with that table as the reason. Correctness-only, so no quiet host is needed.'
  acceptance: 'Catch table (mutant x gate x seed, with NMSE) committed with the 5/5 control; one of two outcomes recorded: an equivalence milestone opened with its named subclass, or the port closed with the table as its reason; the quant-kernel decline recorded with the 1116/1497 coverage count.'
  replaces_rows: [W5VERIF-2]
- task_id: C5-ISA-2
  owner: handoffs/active/agentic-rocm-kernel-authoring.md
  text: '- [ ] **C5-ISA-2 — GCN-Gym: LLM-edited AMDGCN for a compute-bound gfx90a kernel whose limiter is register allocation (intake-2555#record, intake-2556#record).** Not trigger-gated, because the HIP-source levers on the target are measured out: AK-MMQ-H10 (J-cap) NEGATIVE, the ak-27b-gpu-verify stream-k MMQ hypotheses were all refused or retired, and the ROCm 6.2 AGPR copy tax and MMQ spills are compiler-side (INF03-REGAUDIT-1: Q8_0 J=64 at 256 VGPR with 37 spills; MMA-FA DKQ>=192 at 512 VGPR with hundreds of reloads per iteration). Build a standalone harness (1-2 weeks). Extract the gfx90a .s of one kernel from an experimental v10-tip build via gfx90a_isa_audit.py; let the agent edit it with unified-diff patch tools; reassemble with clang -target amdgcn-amd-amdhsa -mcpu=gfx90a; load with hipModuleLoad; replay the served-shape launches (the RVP-RACE-2 capture shim); diff-test against the hipcc kernel with the AK oracle (host-double for Q8_0); require gfx90a_isa_audit.py diff to exit 0, and the RVP-RACE-2 verdict once M2 lands. Target 1: MMQ Q8_0 J=64 prefill tile. Target 2: MMA-FA DKQ>=192. Run 3 runs per target at a fixed declared token budget on a frozen shape manifest; time on the GPU window with ABBA (>=2 pairs) against the hipcc incumbent, keeping per-run raw candidate .s, oracle outputs and timings. Decision rule: if >=1 of 3 runs on a target reaches >=1.05x kernel time at the served prefill shape, passes the oracle, and its ABBA intervals do not overlap the incumbent, open an experimental-tree code-object override path for that kernel as an ISA-rung AK arm; otherwise record the null with traces and stop the ISA rung for that kernel class.'
  acceptance: 'Harness committed in the research repo; for each target, 3 run records (patched .s hash, oracle verdict, audit diff exit, ABBA timings) and the predeclared decision recorded.'
  replaces_rows: [KERN-8]
rows:
- {row: W5VERIF-1, entries: [intake-2570, intake-2557], action: 'Record the race/deadlock/equivalence coverage matrix per hot gfx90a kernel family (v10 code-object counts and source anchors in this file header) in rocm-verify-profile-backend.md beside RVP-RACE-2, so later scoping cites measured coverage, not the paper scope.', maps_to: RVP-RACE-2}
- {row: W5VERIF-2, entries: [intake-2570], action: 'Equivalence-port decision: decline for bit-level quant kernels on coverage (1116/1497 AK GPU experiment rows); a seeded sub-tolerance mutant probe decides the FA/GDN/mmvf subclass.', maps_to: RVP-EQV-1}
- {row: W5VERIF-3, entries: [intake-2570], action: 'Fix the RVP-RACE-1 decision rule (>=1 of 20 passes is a miss, not all 20), add waves-per-WG and ISA s_barrier-delta controls, add the LDS-DMA site, and make its mutants RVP-RACE-2 fixtures rather than its trigger.', maps_to: RVP-RACE-1}
- {row: W5VERIF-4, entries: [intake-2570, intake-2557], action: 'Level choice for the gfx90a checker is AMDGCN ISA from the built code object, not LLVM IR or HIP source: IR lacks waitcnts and the inline-asm semantics the AMD hot paths rely on, and cannot see ISA-edited (C5-ISA-2) candidates.', maps_to: RVP-RACE-2}
entries: []
```
