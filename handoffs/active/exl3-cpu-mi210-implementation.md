# EXL3 CPU and MI210 Implementation

**Status**: active experimental implementation program
**Created**: 2026-09-25 (via research intake, operator-approved 2026-09-25)
**Categories**: quantization, hardware_optimization, inference_serving, moe_optimization, local_inference
**Workstream**: Inference Acceleration
**Parent index**: [inference-research-index.md](inference-research-index.md) (`INF-80`)
**Historical predecessor**: [completed EXL3 CPU study](../completed/exl3-trellis-cpu-kernel.md) — retain its Qwen-specific CPU no-go; this program covers the broader CPU/gfx90a architecture gap
**Related infrastructure**: [agentic ROCm kernel authoring](agentic-rocm-kernel-authoring.md), [ROCm verify/profile backend](rocm-verify-profile-backend.md), [CPU roofline program](cpu-decode-roofline-program.md), [Vidya belief substrate](vidya-belief-substrate-program.md)

## Objective

Implement EXL3 as a project-owned experimental quantization path on EPYC 9655 and MI210/gfx90a. Build native kernels where required: optimized CPU decode, wave64 GPU decode, and MFMA GPU prefill. Deliver reproducible standalone operators first, then one llama.cpp experimental operator, mixed-K MoE dispatch, and measured hybrid CPU/GPU execution.

Production `production-consolidated-v10` is frozen. Start kernel work from a fresh current-production checkout on a new `llama.cpp-experimental` branch; build and measure the complete experimental candidate there.

## Research record inventory

| Intake IDs | Program area informed |
|---|---|
| `intake-1528#record`, `intake-1529#record`, `intake-1530#record`, `intake-1531#record`, `intake-1532#record`, `intake-1533#record` | Hopper report boundaries; ROCm/CUDA implementation references; corrected Marlin unpack baseline; MCG checkpoint structure; upstream CPU `mul1` path |
| `intake-1534#record`, `intake-1535#record`, `intake-1536#record`, `intake-1537#record` | RDNA port lessons and non-transferability; gfx90a instruction repertoire |
| `intake-1538#record`, `intake-1539#record`, `intake-1540#record`, `intake-1541#record`, `intake-1542#record` | CPU ISA/swizzle patterns; pinned-arena streaming; measurement harness; mixed-K loader and decode reference |
| `intake-1543#record`, `intake-1544#record`, `intake-1545#record`, `intake-1546#record`, `intake-1547#record`, `intake-1548#record`, `intake-1549#record`, `intake-1550#record` | Matched-count W4A16 comparison boundary; correctness hazards; Marlin/QQQ regime separation; model and teacher receipt patterns |
| `intake-1551#record`, `intake-1552#record`, `intake-1553#record`, `intake-1554#record`, `intake-1555#record`, `intake-1556#record` | Exact gfx90a identity; current pinned-arena lineage; AVX-512 layout; mixed-K ABI; unavailable pruning provenance; sustained-link probe scope |
| `intake-1557#record`, `intake-1558#record`, `intake-1559#record`, `intake-1560#record`, `intake-1561#record`, `intake-1562#record` | Deterministic gather; runtime-K/grouped dispatch; row-floor regression; sentinel slicing; low-batch fallback hole; grouped fallback contract |

## Settled research

- [x] **EXL3-R1 — Establish the architecture boundary.** Existing NVIDIA and RDNA kernels supply algorithms, layouts, and failure cases, but do not provide MI210 support or predict gfx90a performance. ✅ 2026-09-25
- [x] **EXL3-R2 — Establish the MI210 target.** Compile for exact `gfx90a`, wave64, and the chosen CDNA2 MFMA forms; `gfx9-generic` is insufficient. ✅ 2026-09-25
- [x] **EXL3-R3 — Establish separate decode and prefill regimes.** Decode starts with wave64 GEMV; prefill and wider batches get a separate MFMA path. ✅ 2026-09-25
- [x] **EXL3-R4 — Establish the CPU starting point.** Reuse upstream `mul1` scheduling, ISA, and swizzle patterns; begin MCG from an independent scalar oracle because no optimized MCG CPU path or transferable `mul1` fusion has been established. ✅ 2026-09-25
- [x] **EXL3-R5 — Establish the dispatch uncertainty.** Preserve unified runtime-K and grouped K-specialized paths until local EPYC and MI210 measurements select per-regime defaults. ✅ 2026-09-25
- [x] **EXL3-R6 — Establish the quality comparison boundary.** W4A16 is an alternative deployment family, but codec claims require matched teacher, architecture, expert plan, evaluation panel, and storage budget. ✅ 2026-09-25

## Implementation tasks

- [ ] **EXL3-1 — Freeze the backend-neutral artifact, metadata, oracle, and evidence contract.** Define a content-addressed canonical EXL3 manifest with tensor role/shape/order, K or `rate_x2`, codebook, trellis packing, Hadamard geometry, `suh`/`svh`, scaling, padding, and source revision. Reject unknown or conflicting metadata before allocation. Implement independent portable `mul1` and MCG reconstruction plus GEMV/GEMM references. Create project-owned K1–K8 synthetic vectors and mandatory revision-pinned real-weight `mul1` and MCG fixtures containing packed states, reconstructed tiles, transforms, and full operator outputs. Backend repacks must bind the canonical input digest. Before the first correctness, performance, or quality run, land the `VB-EXL3-CPU-GFX90A` writer and strict projection for `epyc.exl3.measurement.v1` and `epyc.exl3.verifier.v1`; this task cannot close before both are live. Measurement rows use the locator run × arm × backend × operator × shape × metric and carry producer/schema identity, producer hash, run/row IDs, self-hash, one metric with units and direction, exact category, protocol ID (empty when ineligible), repetitions and basis, date, attestation path/digest, raw vector, comparator/arm identity, experimental authority, and model/artifact/source/binary/library/toolchain/hardware/residency identities. Verifier rows use run × fixture × backend/path × proposition and additionally bind checker identity/hash, fixture and read-set digests, the exact `decided_proposition`, and verdict.

- [ ] **EXL3-2 — Implement and qualify the EPYC primitives.** Land scalar dense and indexed-expert operators first, then AVX-512BW/VNNI/VBMI `mul1` GEMV and an independently vectorized MCG path. Cover native and band-contiguous layouts, supported ISA tiers, K1–K8, one through four rows, tails, padding, guard-filled outputs, and real fixtures that cannot silently skip. Compare grouped-by-K dispatch outside the hot loop with per-expert runtime K. Start prefill with canonical reconstruction into the project GEMM provider; optimize a many-row path only after profiling.

- [ ] **EXL3-3 — Build the native gfx90a reconstruction oracle and wave64 decode GEMV.** Freeze the ROCm 6.2 build contract and record compiler, exact target ID, code-object version, XNACK/SRAMECC mode, emitted object hash, and disassembly. Validate wave64 lane maps and procedural integer state operations, then implement K3/K4 `mul1` and MCG first with FP32 accumulation and stable reduction. Cover dense and expert tensors, boundaries, bias, padded and unpadded projections, poisoned padding, and teardown without residue. The first architecture milestone is matching full operator outputs against EXL3-1 and EXL3-2 on both real fixtures.

- [ ] **EXL3-4 — Build the native gfx90a MFMA prefill path after EXL3-3 correctness.** Create a standalone FP16-input/FP32-accumulating 16×16×16 lane-map harness, decode packed trellis tiles into register or LDS fragments, apply the required transforms, and fuse them with MFMA. Compare folded and unfolded reconstruction against the same reference and record scratch, LDS, occupancy, HBM, launch, and latency data. Keep the GEMV and MFMA dispatch surfaces separate.

- [ ] **EXL3-5 — Make mixed-K MoE dispatch total and correct.** Carry device-visible half-bit K/rate and codebook metadata, projection pointer tables, and explicit local/global expert domains. Implement unified runtime-K and grouped K-specialized policies plus named batched, small-row, and single-expert fallbacks. Centralize eligibility in one capability truth table. Count/sort arrays may use sentinel E; local compute/gather tables have exactly E entries. Preserve routing-k order, explicit top-k bounds, deterministic fixed-order FP32 gather, and a separately labeled atomic mode. Exercise BC present/absent, extension present/absent, batch and routed-row thresholds, buckets below four experts, all-local/all-nonlocal/mixed slices, and every fallback. Require full operator-output or logit comparisons; token equality is insufficient.

- [ ] **EXL3-6 — Integrate exactly one EXL3 operator into fresh experimental llama.cpp.** Add the canonical loader, one linear/indexed-expert operation, scalar fallback, CPU backend, and HIP backend without editing frozen v10. Keep per-expert activation and output transforms in the operator contract instead of forcing them into a generic quant trait. Progress through single tensor, one expert, one MoE layer, multi-layer logits, then complete generation; exercise `mul1` and MCG separately before mixed-K. Prove the candidate binary and ggml libraries contain and postdate the implementation, and prove HIP residency during the active window.

- [ ] **EXL3-7 — Measure local policy and performance by regime.** On EPYC, sweep scalar/ISA tier, physical cores, NUMA placement, huge pages, layout, K, expert shape, and grouped versus runtime dispatch. On MI210, compare wave64 GEMV, MFMA, unified, grouped, and leftover-expert fallbacks across decode concurrency 1/8/16 and declared prefill shapes. Capture exact artifact/config identities, interleaved raw repetitions, dispersion, launch counts, rocprof traces, HBM traffic, full-output error, and in-window KFD/VRAM evidence. External NVIDIA rates remain context and never become EPYC/MI210 thresholds. The producer emits the versioned native measurement and verifier rows; strict adapters project eligible rows into `ClaimTuple`, and `claim_tuple.grade()` assigns the grade.

- [ ] **EXL3-8 — Implement hybrid CPU/MI210 streaming only after independent parity gates pass.** Build a failure-atomic HIP registered shared arena with explicit ownership, byte-exact DMA, async copy streams, deterministic teardown, and a ROCm sustained-link probe whose complete trace sets local thresholds. Stream only selected expert blocks, leave a configurable number on CPU, and record CPU GEMV, transfer, GPU kernel, overlap, fallback, and residency timelines. Compare whole-layer CPU offload, expert-split offload, GPU-only, and CPU-only under identical model residency and prompts.

- [ ] **EXL3-9 — Run the controlled EXL3 versus W4A16 decision study.** Produce or obtain arms from one teacher revision with identical architecture, expert count/keep plan, non-target tensors, tokenizer, evaluation panel, and declared storage budget. Persist full-vocabulary teacher-forced logits and separate codec, pruning, and runtime effects. Report quality, resident memory, artifact size, latency, and throughput as separate directed metrics. A pruned W4A16 deployment arm may be useful, but it cannot serve as the matched codec control. Treat expert-ranking provenance as unavailable until its source becomes revision-pinned and inspectable.

- [ ] **EXL3-10 — Build the complete regression and promotion package.** Run existing-quant CPU coverage, EXL3 CPU/HIP correctness and stability, long-context and mixed-batch checks, nonfinite and guard corruption checks, and complete-candidate performance observations. Rebuild the candidate from fresh production plus all EXL3 changes; never reconcile separately measured pieces by cherry-pick at promotion time. Experimental results may nominate a candidate but do not modify the frozen branch, kernel store, launcher, or lineup. Promotion remains a separate final operator decision with a rollback anchor and production-named rerun.

## Gates and critical path

`EXL3-1 → {EXL3-2, EXL3-3} → EXL3-4/5 → EXL3-6 → EXL3-7 → EXL3-8/9 → EXL3-10`

- **G1 format**: two independent references agree on procedural state decode; reconstructed fixture values and operator outputs meet the declared reference envelope; malformed metadata refuses.
- **G2 CPU**: scalar and every enabled ISA path agree across codebook/K/shape/layout fixtures; no fixture may skip silently.
- **G3 gfx90a decode**: real `mul1` and MCG outputs agree with the portable and CPU paths; no poisoned tail is consumed.
- **G4 prefill**: MFMA agrees with the reference and wins only its declared shape regime; otherwise it remains an experimental fallback.
- **G5 dispatch**: every truth-table cell executes its named path or named fallback without low-batch assertions, dropped buckets, sentinel reads, or silent mode changes.
- **G6 integration**: standalone and llama.cpp operators agree; non-EXL3 behavior remains unchanged; intended CPU/HIP libraries and active residency are proven.
- **G7 hybrid**: CPU-only, GPU-only, and hybrid outputs share the same correctness envelope; any performance claim includes both applicable local baselines.
- **G8 quality**: no EXL3-versus-W4A16 codec conclusion is emitted unless matched-arm identity checks pass.

## Explicit exclusions

- Do not bypass RDNA/ROCm architecture guards or transplant CUDA PTX, warp32 fragment maps, Blackwell split heuristics, launch constants, PDL policy, or probe thresholds into gfx90a.
- Do not predict EPYC or MI210 gains from NVIDIA, Xeon, Threadripper, RDNA, RTX, or GB10 results.
- Do not use the full GLM checkpoint as the first milestone or describe routed-expert CPU offload as a complete CPU-only runtime.
- Do not adopt misleading status output, ad hoc serving stderr, or stale backup-file payloads from experimental forks.
