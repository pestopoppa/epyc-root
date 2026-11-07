# EXL3 CPU and MI210 Implementation

> **Fold destination** (BRF-T1-F5, BRF-T1-1, route 1a, 2026-11-02): renamed from `exl3-cpu-mi210-implementation.md`; absorbs 2 handoff(s) as `## Track:` sections at the end of this file (`iqk-iquant-enablement.md`, `tq3-quantization-evaluation.md`). The body above the first track is the former `exl3-cpu-mi210-implementation.md`.

**Scratch**: `/mnt/raid0/llm/tmp/exl3-graph-replay/` · worktrees: `/mnt/raid0/llm/worktrees/exl3-graph-*` (new graph-replay work; historical evidence paths below remain unchanged)

**Status**: active experimental implementation program
**Created**: 2026-09-25 (via research intake, operator-approved 2026-09-25)
**Categories**: quantization, hardware_optimization, inference_serving, moe_optimization, local_inference
**Workstream**: Inference Acceleration
**Parent index**: [inference-research-index.md](inference-research-index.md) (`INF-80`)
**Historical predecessor**: [completed EXL3 CPU study](../completed/exl3-trellis-cpu-kernel.md) — retain its Qwen-specific CPU no-go; this program covers the broader CPU/gfx90a architecture gap
**Related infrastructure**: [agentic ROCm kernel authoring](rocm-kernel-authoring.md#track-agentic-rocm-kernel-authoring), [ROCm verify/profile backend](rocm-kernel-authoring.md#track-rocm-verify-profile-backend), [CPU roofline program](cpu-decode-roofline-program.md), [Vidya belief substrate](vidya-belief-substrate-program.md)

**Priority**: MEDIUM — T6 inference-ready (rank 33), 43 open; low-bit work is scoped to the DS41/Q38FN lanes only, so routine rather than campaign-critical.

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
| `intake-1563#record`–`intake-1575#record`, `intake-1708#record`–`intake-1782#record` | Throughput and serving closure corpus: native-packed ABI/lifecycle, MCG fixtures/oracles, full-stack correctness, comparator admission, and workload-specific throughput attribution |

## Settled research

- [x] **EXL3-R1 — Establish the architecture boundary.** Existing NVIDIA and RDNA kernels supply algorithms, layouts, and failure cases, but do not provide MI210 support or predict gfx90a performance. ✅ 2026-09-25
- [x] **EXL3-R2 — Establish the MI210 target.** Compile for exact `gfx90a`, wave64, and the chosen CDNA2 MFMA forms; `gfx9-generic` is insufficient. ✅ 2026-09-25
- [x] **EXL3-R3 — Establish separate decode and prefill regimes.** Decode starts with wave64 GEMV; prefill and wider batches get a separate MFMA path. ✅ 2026-09-25
- [x] **EXL3-R4 — Establish the CPU starting point.** Reuse upstream `mul1` scheduling, ISA, and swizzle patterns; begin MCG from an independent scalar oracle because no optimized MCG CPU path or transferable `mul1` fusion has been established. ✅ 2026-09-25
- [x] **EXL3-R5 — Establish the dispatch uncertainty.** Preserve unified runtime-K and grouped K-specialized paths until local EPYC and MI210 measurements select per-regime defaults. ✅ 2026-09-25
- [x] **EXL3-R6 — Establish the quality comparison boundary.** W4A16 is an alternative deployment family, but codec claims require matched teacher, architecture, expert plan, evaluation panel, and storage budget. ✅ 2026-09-25
- [x] **EXL3-R7 — Freeze the native-packed execution contract.** The strongest transferable implementation pattern is per-logical-matrix metadata plus a plan/bind/run lifecycle over native packed tensors, caller-owned persistent scratch, fixed capacities, and fail-closed codebook/device checks. The CUDA implementations do not transfer to gfx90a; the contracts do. (`intake-1756#00`, `intake-1756#01`, `intake-1757#00`, `intake-1757#01`, `intake-1757#02`) ✅ 2026-09-25
- [x] **EXL3-R8 — Freeze the first real MCG fixture and oracle boundary.** Uniform K4/MCG is the first real fixture. The independent project oracle must cover packed windows and lane placement; generation identity and a quality receipt do not substitute for raw reconstruction parity. Source-available Brandon code remains evidence-only unless license review authorizes reuse. (`intake-1756#02`, `intake-1758#00`, `intake-1758#02`, `intake-1758#03`) ✅ 2026-09-25
- [x] **EXL3-R9 — Freeze the throughput attribution boundary.** Published NVIDIA rates combine target quantization, speculative acceptance, scheduler behavior, graph capture, attention/KV precision, and recurrent-state handling. CPU/MI210 qualification must measure operator and full-stack envelopes separately. (`intake-1563#record`, `intake-1564#record`, `intake-1754#record`, `intake-1779#record`) ✅ 2026-09-25
- [x] **EXL3-R10 — Freeze the full-stack correctness boundary.** Exactness is proposition-specific: packed reconstruction, operator output, recurrent state, verifier acceptance, and complete autoregressive token equality require separate oracles and fail-capable controls. (`intake-1760#00`, `intake-1760#01`, `intake-1760#02`, `intake-1763#00`, `intake-1763#01`, `intake-1765#record`, `intake-1767#record`) ✅ 2026-09-25
- [x] **EXL3-R11 — Close broad literature expansion.** No reviewed source supplies CPU/gfx90a EXL3 throughput or invalidates the custom-kernel path. Reopen research only for actual CPU/gfx90a EXL3 code, a changed ABI/reconstruction rule, evidence invalidating the correctness path, or matched raw evidence that changes a gate. ✅ 2026-09-25

## Implementation tasks

- **[declined: ws58 2026-11-03 content-review: a PROPOSED HIP-capture extension of the standalone EXL3 path, which is PARKED for the 27B (EXL3-X0: no speed case) and has no DS41/Q38FN consumer (operator: low-bit = DS41/Q38FN lanes only)]** **EXL3-GRAPH-1 — PROPOSED: support caller-owned outer HIP capture on the standalone unified EXL3 path.** Recover the device-resident metadata/replay application omitted when safeguards and overhead attribution were filed. Add bounded device-resident route/count/order inputs through the existing plan/bind arena, keeping eager execution and fail-closed capacity/identity checks. Specify the capture envelope; qualify changed routing and token lengths within it against the existing full-output oracle. Missing/stale metadata, overflow and unsupported fallback must refuse before output writes. Reuse the live EXL3 verifier/measurement writer and strict projection, binding exact propositions, fixture/read-set/producer identities and all failures. After the existing device correctness gates pass, compare eager and replay latency on identical frozen fixtures with interleaved repetitions, a complete denominator and a predeclared overhead disposition. No claimed speedup, parked 27B integration reopening, frozen-kernel edit or production change; GPU execution requires the owning session's coordinated claim/window. This is a filed implementation proposal, not execution authorization. [Review](../../docs/reviews/research-intake-practical-applications-20261004.md); record discussion: intake-1569#record.

- [x] **EXL3-1 — Freeze the backend-neutral artifact, metadata, oracle, and evidence contract.** ✅ 2026-09-26. Define a content-addressed canonical EXL3 manifest with tensor role/shape/order, K or `rate_x2`, codebook, trellis packing, Hadamard geometry, `suh`/`svh`, scaling, padding, and source revision. Reject unknown or conflicting metadata before allocation. Implement independent portable `mul1` and MCG reconstruction plus GEMV/GEMM references. Create project-owned K1–K8 synthetic vectors and mandatory revision-pinned real-weight `mul1` and MCG fixtures containing packed states, reconstructed tiles, transforms, and full operator outputs. Backend repacks must bind the canonical input digest. Before the first correctness, performance, or quality run, land the `VB-EXL3-CPU-GFX90A` writer and strict projection for `epyc.exl3.measurement.v1` and `epyc.exl3.verifier.v1`; this task cannot close before both are live. Measurement rows use the locator run × arm × backend × operator × shape × metric and carry producer/schema identity, producer hash, run/row IDs, self-hash, one metric with units and direction, exact category, protocol ID (empty when ineligible), repetitions and basis, date, attestation path/digest, raw vector, comparator/arm identity, experimental authority, and model/artifact/source/binary/library/toolchain/hardware/residency identities. Verifier rows use run × fixture × backend/path × proposition and additionally bind checker identity/hash, fixture and read-set digests, the exact `decided_proposition`, and verdict.
  - Use projection-major native packed tensors without repacking. Give every logical Q/K/V and gate/up/down matrix its own trellis, transform vectors, codebook marker, tensor role, source digest, and local/global expert domain. Unknown or ambiguous mappings fail before allocation. (`intake-1756#00`, `intake-1757#00`)
  - Re-derive the three-instruction MCG window decoder and lane map into project-owned scalar fixtures. Treat the Apache-licensed donor as a second oracle; keep source-available ShapleyMCG code evidence-only unless separately cleared. (`intake-1756#02`, `intake-1758#03`)
  - Pin one real uniform-K4 MCG tensor plus synthetic K1–K8/MUL1/MCG vectors. A fixture passes only when packed-state decode, reconstructed tile, transforms, and full operator output are checked independently. (`intake-1758#00`, `intake-1758#02`)
  - Use nonfinal teacher-logit windows for harness development and reserve the 25-window final panel for one frozen qualification. Keep quality, reconstruction, and performance receipts separate. (`intake-1759#00`, `intake-1759#01`, `intake-1759#02`)
  - Completion evidence: research `bc9ac47b` implements the closed content-addressed manifest, independent MUL1/MCG scalar decode, explicit FP32-FMA/FP16-RNE materialization, GEMV/GEMM references, synthetic K1–K8 vectors, three revision-pinned real fixtures, repack binding, and both evidence writers. Root `6b8f9e85` implements strict projection and CLI discovery. Main review passed 17 portable tests and 44 adapter/dispatcher tests; 76 fixture receipts plus two exhaustive Apache-donor receipts verify the frozen contract.

- [x] **EXL3-2 — Implement and qualify the EPYC primitives.** ✅ 2026-09-26. Land scalar dense and indexed-expert operators first, then AVX-512BW/VNNI/VBMI `mul1` GEMV and an independently vectorized MCG path. Cover native and band-contiguous layouts, supported ISA tiers, K1–K8, one through four rows, tails, padding, guard-filled outputs, and real fixtures that cannot silently skip. Compare grouped-by-K dispatch outside the hot loop with per-expert runtime K. Start prefill with canonical reconstruction into the project GEMM provider; optimize a many-row path only after profiling.
  - Completion evidence: research `0e683fc0` implements scalar dense/indexed operators, AVX-512BW/VNNI/VBMI MUL1, an independent vector MCG path, both layouts, K1–K8, rows 1–4, tails, padding, bias, guards, fail-before-write preflight, real fixtures, and external-BLAS reconstruction/prefill. Normal and ASan/UBSan qualification each passed 719,096 checks; main independently repeated the normal suite. Research `e6dc43b9` records the q3/CPU95 claimed grouped-K versus runtime-K comparison against the actual captured mixed-K payload: eight measurement rows plus one verifier row passed strict projection. Median differences ranged from 0.33% to 5.98% by ISA in this fixed-order, cache-resident sample, so no dispatch default was selected. The rows are protocol-ineligible observations with no promotion authority.

- [ ] **EXL3-3 — Build the native gfx90a reconstruction oracle and wave64 decode GEMV.** Freeze the ROCm 6.2 build contract and record compiler, exact target ID, code-object version, XNACK/SRAMECC mode, emitted object hash, and disassembly. Validate wave64 lane maps and procedural integer state operations, then implement K3/K4 `mul1` and MCG first with FP32 accumulation and stable reduction. Cover dense and expert tensors, boundaries, bias, padded and unpadded projections, poisoned padding, and teardown without residue. The first architecture milestone is matching full operator outputs against EXL3-1 and EXL3-2 on both real fixtures. [check: which low-bit lane (DS41 or Q38FN) consumes the native gfx90a EXL3 oracle/GEMV (EXL3-3/3a/4/5)? The operator limited low-bit work to those lanes and EXL3 is parked for the 27B; name the lane or park the chain]
  - Translate format semantics and lane ownership into wave64; do not transplant CUDA warp32 geometry. The first gfx90a milestone is native packed K4/MCG GEMV matching the scalar and EPYC full operator outputs on the same real fixture. (`intake-1756#01`, `intake-1756#02`)
  - Source, exact-target build, host truth-table, and real-fixture transport are complete in research `9e4fa162`. Research `b02b1889` adds an explicit Inference Main owner-run authority path while keeping delegated execution provider/lease gated; 13 authority and refusal tests pass. Research `48253e78` refreshes the source-bound build receipt after that launcher change. The current ROCm 6.2 code object targets `gfx90a:xnack-:sramecc+`, hashes to `7dc947dcbaa055fbac49a19f606038229289ab99f721db0e76936136be676a71`, and contains 20 wave64 kernels. G3 remains open until the same propositions execute on `mi210_0` with an exclusive physical claim and in-window residency evidence; the current owner preflight refuses live foreign KFD occupancy.
  - **First device run, 2026-10-03 (partial; G3 and G4 NOT met; attribution corrected 2026-11-02).** Inside the INF-80 X0 window, owner-run authority `owner:inference:EXL3-3`, exclusive `mi210_0` claim and in-window KFD residency were recorded for all three real fixtures (`/mnt/raid0/llm/tmp/x0-27b-quants/results/exl3/exl3-3-real-{mul1-k3,mul1-k4,mcg-k4}-20261003T151909Z/`). Each `stdout.jsonl` records `materialized_weight_fp32_fma_v1`, `compute=gemv`, `status=pass` after exact canonical full-output comparison, and saves `operator-output.gemv.f32`. The subsequent MFMA prefill comparison failed its existing abs=1e-5, rel=1e-4 envelope: mul1-k3 index 9 actual −0.0198101 vs −0.0198266; mul1-k4 index 10 −0.00217858 vs −0.00216186; mcg-k4 index 8 0.076089 vs 0.076071. The common error label did not name the mode; `snapshot/test_runtime.hip:229` establishes the test order and tolerances. Each binary returned rc 1 and the overall sealed verifier failed; the GEMV passes were not separately sealed verifier propositions. Root cause and full G3/G4 coverage remain unestablished.
  - [ ] **EXL3-3a — resolve the real-fixture oracle envelope and qualify GEMV and MFMA.** (filed 2026-10-03; corrected 2026-11-02) Preserve exact canonical wave64 GEMV equality; investigate the MFMA mismatch against its existing abs=1e-5, rel=1e-4 envelope. Declare and justify any changed MFMA envelope before a rerun, then run the three real fixtures with distinct sealed propositions and complete the remaining G3/G4 gates. [too-big: oracle arithmetic semantics and acceptance envelope require handoff-owned science]
    - **2026-11-02 correction:** The observed discrepancy above was MFMA, not GEMV. Keep the existing exact wave64 GEMV comparison and investigate MFMA against its declared envelope; if the MFMA envelope changes, declare and justify it before rerun. Run the three pinned fixtures with separately sealed propositions and finish remaining G3/G4 gates. This task remains open.
  - [ ] **EXL3-3b — the claimed-run teardown guard turns a passing binary into rc 2.** [too-big: source fix landed; synthetic device rerun belongs to inference owner] (filed 2026-10-03) `scripts/kernel_rnd/exl3_gfx90a/claimed_run.py` takes two teardown samples 20 ms apart and sets `code = code or 2` if the exited PID is still listed in KFD. On the synthetic run the first sample still listed PID 1670889 after the process was reaped (`pid_alive` false) and the second was empty — a KFD bookkeeping lag, not residue. Poll until the PID leaves KFD or a bounded timeout (fail only on the timeout), keep the samples in `residency.json`, add a test, then re-run the synthetic suite.
    - 2026-11-02: CPU build prerequisite row `exl3-3b-build-r2-20261102` passed rc=0; source-bound receipt `/mnt/raid0/llm/tmp/exl3-3b-build-r2-20261102/build/build.json` binds accepted research `e46b01b94e37b6c7134cb304b41863ef3677c32b`, fixed wrapper SHA-256 `833d9d8dde2bd2868ff67d8a90c595f2ca91bc2a931ba7d1aebffef405a58f7e`, runtime SHA-256 `6458c3ea6556116814ce8e404b94b121339c3487aa5b5ede2faab77f55c25dcb` and target `gfx90a:xnack-:sramecc+`. All listed hashes match; `execution=not_run`. The GPU rerun still needs a supported keeper-authority and single journaled physical-claim integration: filler and `claimed_run.py` currently contend for the same lock, and a grant is not a legacy lease. Reviewable work packet `/mnt/raid0/llm/tmp/compute-flags/handoff-sessions/exl3-cpu-mi210/contract-route.txt`; no authority bypass or device execution is implied.
    - [x] **EXL3-3B-SOURCE — implement bounded teardown polling with retained samples and full synthetic source controls.** Research proposal `edcae4ac1d6e6b222c38dd1942c7acc54ba13a9c`; captured child PID only, monotonic1s/20ms bounded wait, unknown/persistent KFD census refuses. Existing carrier verification is VB-EXL3-3B-CONFORMANCE. This source slice grants no device run or physical parent acceptance. ✅ 2026-10-07 — MAIN accepted [source and original39/39](../../artifacts/ni08/exl3-teardown-source-20261007/README.md).

- [ ] **EXL3-4 — Build the native gfx90a MFMA prefill path after EXL3-3 correctness.** Create a standalone FP16-input/FP32-accumulating 16×16×16 lane-map harness, decode packed trellis tiles into register or LDS fragments, apply the required transforms, and fuse them with MFMA. Compare folded and unfolded reconstruction against the same reference and record scratch, LDS, occupancy, HBM, launch, and latency data. Keep the GEMV and MFMA dispatch surfaces separate.
  - The standalone MFMA source and exact-target build are complete in research `9e4fa162`, with two emitted MFMA instructions and host-side folded/unfolded contract checks. G4 remains open until MI210 correctness and shape-regime performance execute under an exclusive physical claim.
  - 2026-10-03 first device run (with EXL3-5, `/mnt/raid0/llm/tmp/x0-27b-quants/results/exl3/exl3-45-synthetic-20261003T151909Z/`): `procedural_fp16_and_wave64_lane_map` pass (131,072 state cases, 69,632 packed cases, 1,024 MFMA cells); the standalone synthetic operator suite passes 279,967 assertions; `real_fixture_parity` not run, no performance arm. The binary passed, but the wrapper returned rc 2 from its teardown guard (EXL3-3b), so the sealed verifier row reads `fail`. G4 still needs the real-fixture MFMA comparison and the shape-regime performance data.

- [ ] **EXL3-5 — Make mixed-K MoE dispatch total and correct.** Carry device-visible half-bit K/rate and codebook metadata, projection pointer tables, and explicit local/global expert domains. Implement unified runtime-K and grouped K-specialized policies plus named batched, small-row, and single-expert fallbacks. Centralize eligibility in one capability truth table. Count/sort arrays may use sentinel E; local compute/gather tables have exactly E entries. Preserve routing-k order, explicit top-k bounds, deterministic fixed-order FP32 gather, and a separately labeled atomic mode. Exercise BC present/absent, extension present/absent, batch and routed-row thresholds, buckets below four experts, all-local/all-nonlocal/mixed slices, and every fallback. Require full operator-output or logit comparisons; token equality is insufficient.
  - Expose `plan`, `bind`, and `run` phases. Planning fixes token, route, tile, decode, and prefill capacities; binding maps one caller-owned arena into stable views; `run` performs no allocation. Runtime identity binds model, tensor role, codebook, capacity, scratch, backend, and source digest. (`intake-1756#00`, `intake-1757#02`)
  - Refuse capture-time fallback, capacity overflow, unknown codebook, conflicting MCG/MUL1 markers, exhausted scheduler slices, and ambiguous source mappings. Boundary tests sweep both sides of every tile and scheduler transition. (`intake-1757#01`, `intake-1757#02`, `intake-1772#02`)
  - Benchmark concentrated, spread, and randomized expert routing. Report the route histogram with every sparse-kernel result so a favorable routing distribution cannot stand in for general throughput. (`intake-1758#record`)
  - The total capability table, 256-expert/E+1 boundary, unified/grouped policies, named fallbacks, deterministic and atomic gather, fixed caller arena, identity binding, and 512 MiB capacity refusal are implemented in research `9e4fa162`. Main review passed 5,579 host/static checks across all 5,120 truth-table cells. G5 remains open until every path is exercised on MI210 under an exclusive physical claim.
  - 2026-10-03 first device run (same synthetic run as EXL3-4): all five named paths launched on `mi210_0` under the exclusive claim — unified 124, grouped 16, batched fallback 12, small-row fallback 200, single-expert fallback 236 — inside the 279,967 passing assertions. Not flipped: the sealed verifier row reads `fail` because of the EXL3-3b teardown false positive; re-run after EXL3-3b and flip on a clean rc 0.

- [x] **EXL3-X0 — Bytes-elasticity and equal-bytes quality pre-gate on the production 27B (operator-approved 2026-10-03, ahead of EXL3-6).** In one exclusive :8083 window, run unsloth UD-Q4_K_M against the incumbent Q8_0 (same publisher, byte-identical) through the DFlash2-np4 serving recipe and the production shape, 3 launches per arm, ABA. Add KLD of Q4_K_M against Q8_0 on the MI210. Decision rule, fixed in advance: if Q4_K_M is under +10% serving speed, EXL3 has no speed case on the 27B; park EXL3-6/7 for it and settle VRAM with GGUF. If it is at or above +10%, fund a performance-grade wave64 kernel (EXL3-P) with a 5-agent-day kill. EXL3-3/4/5 device correctness piggybacks on the same window. turboderp `Qwen3.8-27B-exl3` 4.00bpw is on disk for real-tensor correctness and the later equal-bytes comparison. Plan: `/mnt/raid0/llm/tmp/x0-27b-quants/PLAN.md`. ROI review: [`docs/reviews/exl3-roi-20261003.md`](../../docs/reviews/exl3-roi-20261003.md).
  - ✅ 2026-10-03 — **verdict: NO SPEED CASE.** Report: `/mnt/raid0/llm/tmp/x0-27b-quants/results/report.md` (per-launch JSON beside it; `summary.json`). Same v10 kernel store, 3 fresh launches per arm, HIP residency proven every launch.
    - *Canonical shape* (np4 server, 16k f16 KV, DFlash2 n_max 8; harness `serving.py::_measure_once`): np1 Q4_K_M 69.53 ± 0.31 vs Q8_0 76.36 ± 0.71 tok/s (**−8.9%**); np4 aggregate 167.38 ± 3.39 vs 156.22 ± 7.08 (**+7.1%**).
    - *Production :8083 shape* (np4, `-c 393216 --kv-unified`, q8_0 KV, DFlash2 n_max 7), np1 solo decode, temperature 0: ~2k **+3.6%** (42.62 vs 41.16), ~50k **+0.4%** (37.25 vs 37.11). Default-sampling sensitivity (not the gate): ~2k −13.9%, ~50k −20.8%; Q8_0's spread there is wide (sd 3.6–5.4 tok/s).
    - *Quality* (KLD of Q4_K_M vs Q8_0, wiki.test.raw, `-c 512`, 60 chunks, MI210): mean KLD 0.007607 ± 0.000201, median 0.0030, 99.9% 0.276, same-top-p 96.10 ± 0.16%, PPL ratio 1.000137 ± 0.001172.
    - *VRAM at the production shape* (own-PID peak, sampled during each launch): Q8_0 52.08 GiB, Q4_K_M 40.72 GiB — **Q4_K_M frees 11.36 GiB**.
    - *Rule applied* (fixed in PLAN.md before measuring): Q4_K_M is under +10% at every np1 shape (−8.9%, +3.6%, +0.4%), so EXL3 has no speed case on the 27B. **EXL3-6 and EXL3-7 are parked for the 27B** (see their notes) and EXL3-P is not funded. The VRAM question is a GGUF choice, below.
    - The folded UFH14-A2 DFlash2 probe ran in this window; its numbers live in [`agentic-serving-harness-fixes.md`](harness-program.md#track-agentic-serving-harness-fixes) UFH14-A2.
    - **Challenged 2026-10-04 by EXL3-LB1 seed #1 (n=1 per arm, confirmation pending — EXL3-LB1b).** X0 measured the *kernel as shipped*: on v10 the Q4_K verify GEMMs at ne11 5–8 ran on MMVQ at 9–15% of roofline (EXL3-LB1 first measurement). With the seed #1 route fix the same production shape gives Q4_K_M 53.4 tok/s at ~2k temp0 (+30% vs X0's Q8_0 41.2) and 41.8 at ~50k (+13% vs Q8_0 37.1). The X0 *rule application* stands for the v10 kernel; the *conclusion* "no speed case for low-bit on the 27B" does not survive the fix if LB1b confirms. Reopen path: EXL3-X0c.
  - [ ] **EXL3-X0b — settle the 27B's GGUF quant in the post-MI210-#2 topology.** (filed 2026-10-03) **Trigger-gated (operator 2026-10-03): no quant switch without a significant speedup — reopen only if AutoKernel unlocks big low-quant gains (EXL3-LB1a).** Was: operator decision, waiting on the second MI210's arrival: keep Q8_0, or take UD-Q4_K_M (mean KLD 0.0076, same-top-p 96.1%, +11.36 GiB free at the production shape, no decode gain at np1). Inputs: the X0 report above. Not an EXL3 task; it lands as a stack change when the topology is redrawn.
    - 2026-10-04: **the operator's trigger is met, pending confirmation.** EXL3-LB1 seed #1 (an AutoKernel-seeded low-quant kernel fix) puts UD-Q4_K_M at +30% (2k) / +13% (50k) over Q8_0 at the production shape on n=1 per arm. Do not switch on n=1: EXL3-LB1b confirms first, then EXL3-X0c re-runs the quant comparison. The master-index operator-queue row (the old OP-71 question, reworded around the new speed case) is PREPARED in the ak-ds41-main 2026-10-04 wrap-up output and is added by the owning session only after LB1b confirms. (re-scoped 2026-11-03 from Qwen3.6-27B X0 numbers (KLD 0.0076): deleted model; settle the quant for Qwen3.8-27B (fresh KLD needed))
  - [ ] **EXL3-X0c — re-run the X0 production-shape comparison (Q8_0 vs UD-Q4_K_M) on the seed #1 build, if EXL3-LB1b confirms.** (filed 2026-10-04) 3 launches per arm, ABA, temp0 and default sampling, ~2k and ~50k, plus a Q8_0-on-seed-#1 arm (the route also touches Q6_K, so Q8_0's own number must be re-measured on the same binary). KLD from X0 carries over (same files). Output: the decision package for EXL3-X0b — speed gain, KLD 0.0076, +11.36 GiB VRAM — for the operator. (re-scoped 2026-11-03 from Qwen3.6-27B X0 comparison: deleted model; re-run on Qwen3.8-27B (fresh KLD and UD-Q4_K_M needed) or fold into LB1d)

- [ ] **EXL3-LB1 — Low-bit GPU decode kernels as an AutoKernel GPU target (operator discussion 2026-10-03; sequenced after X0 + KLD, preferably on MI210 #2).** Rationale: MI210 has about 14 vector ops per HBM byte against about 38 on an RTX 3090 (spec-sheet arithmetic, not measured), so low-bit decode should hit an instruction/occupancy wall well before the bandwidth roofline; llama.cpp HIP Q4_K decode sits at 35.1% of roofline against Q8_0 50.2% ([`mi210-q8-dequant-gemv-roofline.md`](rocm-kernel-authoring.md#track-mi210-q8-dequant-gemv-roofline), quant ladder). This is the same question EXL3-P would answer with a new format, asked of the GGUF formats we already serve. Seeding (absorbs LB1a): when hypotheses-fable.md lands, feed its 10-15 seeds to the AK GPU low-bit planner/critic.
  - **First measurement:** rocprof per-kernel roofline fraction (achieved bytes/s ÷ peak, per dispatch) of Q4_K versus Q8_0 `mul_mat_vec_q` (MMVQ) and small-M MMQ (ne11 in {2,4,8,16}) at the 27B's real GEMV/GEMM shapes, with VGPR count and waves/SIMD recorded per kernel. Use the X0 Q4_K_M and Q8_0 GGUFs, on a fresh experimental build from the v10 tip.
  - **Prior that may falsify the premise:** INF-06 §22 ([`autokernel-research-loop.md`](autokernel-loop.md#track-autokernel-research-loop) "The quant ladder and the occupancy knee") found batch-1 decode partitions on VGPR occupancy (≤64 VGPR = 8 waves), not on bits or unpack arithmetic, and IQ4_XS was the fastest rung. Read the first measurement against that: if Q4_K's gap is occupancy, the campaign targets register pressure and IQ4_XS-class formats, not unpack instruction count.
  - **Campaign gate:** open an AutoKernel GPU campaign only if X0 shows a low-bit speed case on the 27B (Q4_K_M at least +10% serving) or the first measurement shows a kernel-addressable gap of at least 10 pp of roofline at serving shapes. Otherwise record the measurement and stop.
  - **First measurement DONE 2026-10-03** (report `/mnt/raid0/llm/tmp/lb1-profile-20261003/report.md`, `summary.json`; v10 kernel store `gpu-20260921-ffc1bac82`, rocprof v1, graphs disabled, peak 1638.4 GB/s; 27B Q8_0 and UD-Q4_K_M, plus gemma4-31B Q4_K_M and Qwen3-VL-30B-A3B Q4_K_M). Decode (M=1) MMVQ % of HBM roofline on the 27B: Q8_0 **70.2%** (73.5% of kernel time), Q6_K 63.2%, IQ4_XS 56.0%, Q5_K 47.7%, Q4_K 46.5%. The same-model Q8_0→Q4_K gap is **+23.6 pp**. Small-M: Q8_0 MMQ ~31% at M=8 and M=16; Q4_K MMVQ at M=8 only 9.4% on the 27B. `quantize_q8_1` takes 5.9% (Q8_0) / 7.0% (Q4_K_M) of decode kernel time. 433 weight-matmul dispatches per token on the Q8_0 27B (~1,860 dispatches per token in total). Non-weight kernels take 27–31% of decode kernel time on the dense models and 62% on the 30B-A3B — headroom no format change touches.
    - Read against the gate: the roofline arm (≥10 pp at serving shapes) is met on the measurement; whether the gap is *kernel-addressable* (occupancy vs unpack, per INF-06 §22) is what the hypothesis pass decides. The X0 arm is not met (no speed case).
    - Next: a Fable reviewer seeds 10–15 hypotheses for AutoKernel's planner/critic (operator directive 2026-10-03: Fable seeds, it does not plan) into `/mnt/raid0/llm/tmp/lb1-profile-20261003/hypotheses-fable.md`; low-quant work may span several models, and the goal is a champion advance.
  - **[declined: ws58 2026-11-03 content-review: merged into EXL3-LB1 as its seeding step]** **EXL3-LB1a — hand the Fable hypothesis seeds to an AutoKernel GPU low-bit campaign.** (filed 2026-10-03) When `hypotheses-fable.md` lands, feed the 10–15 seeds to the planner/critic as candidates, scope the campaign across the models the profile covers, and gate keeps on serving speed paired with a correctness check.
  - **Seed #1 measured 2026-10-04 — `akm-gfx90a-kq-mmvq-route-m5-8`: route Q4_K/Q6_K/IQ4_XS/IQ4_NL/IQ3_S to MMQ at ne11 ≥ 5 on CDNA2.** Commit `289cbafa3` on `experimental/kq-mmvq-route-m5-8-20261003` (one file, `ggml/src/ggml-cuda/mmvq.cu`, matches the existing Q8_0 ne11≥5 route); build `kernels/builds/gpu-20261003-289cbafa3-kqroute`; baseline A = champion `gpu-20260929-90c12df42`. Results: `/mnt/raid0/llm/tmp/kqroute-build-20261003/results/20261004T021143Z/` (`report.txt`, `bench.*.json`, `tbo.*`, `x0b/{A,B}/shape_b.q4.rep1.json`).
    - *Correctness:* `test-backend-ops` 60/60 on both A and B. Not bit-exact vs the old route (int8 MFMA, different summation order): DFlash2 acceptance at ~2k temp0 0.41 → 0.40.
    - *Production shape* (X0 shape-b harness: :8083 argv from `DFLASH2_LIVE`, np4, `-c 393216 --kv-unified`, q8_0 KV, DFlash2 n_max 7 → verify ne11 = 8; 27B UD-Q4_K_M; **n = 1 launch per arm**, 2 requests per row, B ran first): ~2k temp0 38.9 → 53.4 tok/s (**+37%**); ~2k default 34.0 → 42.9; ~50k temp0 36.5 → 41.8 (**+15%**); ~50k default 32.1 → 41.8. Own-PID peak VRAM 40.7 GiB both arms, HIP residency proven.
    - *llama-bench* (A = mean of 2 runs, B = 1 run, ABA): gemma-4-31B Q4_K_M pp5 +60%, pp6 +84%, pp7 +109%, pp8 +129%, pp9/pp16 +21–22%, tg128 +1.4% → seed H1 ALIVE. 27B UD-Q4_K_M (mixed Q4_K/IQ4_XS/Q6_K): pp8 +11.8%, but pp4 −32%, pp5 −42%, pp9/pp16 −20%. pp4 is on a route the commit does not change (ne11 ≤ 4), so the single B run is perturbed at least there; a per-type cost (Q6_K or IQ4_XS losing on MMQ at ne11 5–7 where Q4_K wins) is the alternative. Both are open until LB1b/LB1c.
  - [ ] **EXL3-LB1b — confirm seed #1 at the production shape: 3 launches per arm, ABA.** (filed 2026-10-04) Same harness and argv as the 10-04 run; re-run the 27B llama-bench pp4–pp16 with 3 B runs. Pass = the production-shape decode gain holds outside the A spread at ~2k and ~50k with 60/60 correctness.
  - [ ] **EXL3-LB1c — per-type MMVQ-vs-MMQ sweep at ne11 4–9 on gfx90a.** (filed 2026-10-04) For each of Q4_K, Q6_K, IQ4_XS, IQ4_NL, IQ3_S (and Q5_K/Q3_K for reference) time both kernels at the 27B and gemma-4-31B real shapes; set the crossover per type rather than one ne11 ≥ 5 cut for all. Read against INF-06 §22 (occupancy knee).
  - [ ] **EXL3-LB1d — fold the confirmed route into the AutoKernel GPU champion.** (filed 2026-10-04) After LB1b (and LB1c's per-type thresholds, if they differ), land it as a GPU champion keep via the four-step workflow; it is a v11 candidate, never a v10 patch. Then EXL3-X0c.

- [ ] **EXL3-6 — Integrate exactly one EXL3 operator into fresh experimental llama.cpp.** *PARKED for the 27B (2026-10-03): EXL3-X0 found no speed case under its pre-registered rule (Q4_K_M under +10% at every np1 shape). Open only for a model or shape where a bytes-elasticity pre-gate shows one.* Add the canonical loader, one linear/indexed-expert operation, scalar fallback, CPU backend, and HIP backend without editing frozen v10. Keep per-expert activation and output transforms in the operator contract instead of forcing them into a generic quant trait. Progress through single tensor, one expert, one MoE layer, multi-layer logits, then complete generation; exercise `mul1` and MCG separately before mixed-K. Prove the candidate binary and ggml libraries contain and postdate the implementation, and prove HIP residency during the active window.
  - **CPU backend on Qwen3.8-Flash-Next (Q38FN), 2026-10-03.** The 27B park does not cover Q38FN on CPU, where the work proceeded. Branch `experimental/exl3-cpu-20261003` (worktree `/mnt/raid0/llm/worktrees/llama-exl3-cpu-20261003`, forked from champion `90c12df42`, not pushed), 13 commits `c02961978`..`20192b81d`; status and runbook: `EXL3-CPU-STATUS.md` in that worktree, design `EXL3-CPU-DESIGN.md`.
  - [x] **EXL3-6c1 — design + GGUF importer.** ✅ 2026-10-03 — `tools/exl3/exl3_import.py` (native band8 + `.exl3_suh/.exl3_svh`, or materialized F16); decode and materialized-weight hashes bit-exact vs EXL3-1 on all 10 mul1 fixtures; `--check` block correlation ≥ 0.979 (K3 experts) / ≥ 0.9988 (K5 dense).
  - [x] **EXL3-6c2 — ggml types + CPU executor.** ✅ 2026-10-03 — `GGML_TYPE_EXL3_1..8` (ids 60..67, buun convention) and EXL3M_1..8 (68..75, MCG via fp32), `ggml-cpu/exl3.cpp` on MUL_MAT / MUL_MAT_ID: int8 GEMV (VNNI/VBMI), fp32 GEMM prefill, split-K for < 32-unit ops. `test-exl3` ALL PASS: scalar ≡ VNNI ≡ VBMI and multi-thread ≡ 1-thread bit-exact; vs canonical reference GEMV rel-L2 ≤ 1.0e-2, GEMM ≤ 5e-4. Sealed as 9 `epyc.exl3.verifier.v1` rows, all pass: `/mnt/raid0/llm/tmp/exl3-cpu-20261003/evidence/verifier-20261003T190510Z/` (commit `e3e638dc9`).
  - [x] **EXL3-6c3 — llama integration.** ✅ 2026-10-03 — loader aux map, `build_lora_mm{,_id}` attach, draft heads borrowing an EXL3 tensor carry its aux, INF-64 fused decode bypassed for EXL3. 4-layer truncation, native vs materialized F16: KLD mean 9.6e-5 (ub 128) / 1.63e-4 (ub 1), same-top 97.0%; MTP draft smoke loads and returns the greedy text.
  - [x] **EXL3-6c4 — full-model artifact built.** ✅ 2026-10-03 — `/mnt/raid0/llm/models/exl3-gguf/Qwen3.8-Flash-Next-EXL3-3.05bpw/` (49.7 GB + the shared 28.8 GB PLE split), 445 EXL3 tensors with all 890 aux; importer `--check` over 48 layers + head, worst block correlation 0.9787. Not yet loaded in llama.cpp.
  - [ ] **EXL3-6c5 — full-model window (main session, memory/CPU heavy).** Load + greedy smoke, then speed (codified recipe, `GGML_FUSED_DECODE_OFF=1`) and quality (PPL vs UD-IQ4_XS; the IQ4_XS-uniform arm I was measured once below and the file is retired 2026-10-20 (keeper UD-IQ4_XS), so U is the only reference from here; no high-precision Q38FN base on disk for KLD). Runbook in `EXL3-CPU-STATUS.md` → *Window runbook*. Emit `epyc.exl3.measurement.v1` rows.
    2026-10-04 — **measured in CPU window 2, step 1** (ak-ds41-main, 04:41-04:59Z under the q0-q3 region claim;
    durable copy [`artifacts/cpu-window2-20261004/step1_exl3_full/`](../../artifacts/cpu-window2-20261004/step1_exl3_full/)).
    Arms: E = EXL3 3.05 bpw on the EXL3 tree, U = UD-IQ4_XS (reference) and I = IQ4_XS-uniform on the champion; 3
    serpentine rounds, one llama-bench launch per arm per round.
    - Load + greedy smoke: loads and serves; vs U, p1 identical over 48 tokens, p2 differs at token 45, p3 at token 22.
    - PPL (wiki.test.raw c512, 40 chunks): E 2.8909, U 2.9925, I 3.5244 → **E −3.4% vs U**; I +17.8%.
    - Speed vs U: pp5 **−30.9%** [−31.3, −29.4] (slower 3/3); pp256 −16.7% and tg128 −6.8% **inconclusive**.
    - Verdict: EXL3 3.05 bpw buys a small, not-resolvable-as-quality PPL edge at a decisive verify-shape (pp5) cost on
      CPU. The PPL caveat applies: wikitext overlaps Q38FN's memorised n-gram set and a Q8_0 KLD floor is 0.022-0.027.
    - Still open for this box: the `epyc.exl3.measurement.v1` rows were not emitted. Emit them from the durable copy with
      `epyc-inference-research/scripts/kernel_rnd/exl3/evidence.py` `write()` (identities need model/binary digests;
      `identity.sha256` and the linkage files are in the copy), then tick.
    2026-10-25 — **correctness half re-run** (calendar item `exl3-6c5-quality`, one CPU quarter, build role, 08:09Z COMPLETE;
    predeclaration sha256 `216b4110…ecb4f7`, rule applied mechanically). Both arms on the SAME EXL3-tree binary
    (`experimental/exl3-cpu-20261003` @ `20192b81d`, libggml-cpu sha `50343614…`), so the tree no longer confounds U.
    - PPL (wiki.test.raw c512, 40 chunks): E 2.8909 ± 0.0591, U 2.9925 ± 0.0632 → **−3.40%, QUALITY_NOT_WORSE**
      (not within stderr; REPRODUCES_10_04 on both values). Non-inferiority on PPL only, never "better" (10-04 caveat).
    - Greedy smoke vs U: **SMOKE = FAIL** by the predeclared prefix rule. p1 shares 8 characters (minimum 100): both
      answer " Paris." and then continue differently, E with a short explanation and a `<think>` turn, U with a list of
      capitals. p2 shares 102 (minimum 40) and p3 148 (minimum 40), both pass. E loads and every output is ≥ 20 characters.
      The 10-04 run had p1 identical over 48 tokens, but its U ran on the champion build, not the EXL3 tree.
    - No speed figure (the 10-04 speed result stands). Evidence: research `data/exl3-6c5-quality/` (logs, texts, digests, RUN_RECORD,
      VERDICT, SHA256SUMS; committed `84ae00217`, on main via `237a7a789`).
    - Box stays open: the `epyc.exl3.measurement.v1` rows are still not emitted (EXL3-6c5a below).
    - 2026-10-28: smoke prefix p1 8 chars vs min 100 (FAIL; p2 102>=40, p3 148>=40 pass); PPL_E/PPL_U-1 = -3.40% vs <= +1.0% → correctness-only (smoke FAIL is the valid verdict; PPL QUALITY_NOT_WORSE, non-inferiority only, no rate read). Box NOT ticked (EXL3-6c5a/6c5b open). Evidence: /mnt/raid0/llm/tmp/cal-1025/exl3-6c5-quality/VERDICT.json. [belief: cc]
    - [ ] **EXL3-6c5a — emit the `epyc.exl3.measurement.v1` rows, then ingest (filed 2026-10-25, from the 10-24 prose "still open" line).** Run `epyc-inference-research/scripts/kernel_rnd/exl3/evidence.py` `write()` over the 10-04 durable copy (`artifacts/cpu-window2-20261004/step1_exl3_full/`) and research `data/exl3-6c5-quality/` (identities from their digests), then `cli.py ingest exl3-measurement --only-new`. No compute. Done when the rows exist and the ingest frame count is cited here; then tick EXL3-6c5.
      - 2026-10-31 bounded progress: Research `23689feccffaafe516a643963c0e93c020f81982` published `docs/research/exl3-6c5a-original-evidence-20261031.md`, inventorying the missing original E model-digest binding and 10-04 raw speed vectors. This adds no rows, frames or grade. The original smoke remains FAIL; PPL remains QUALITY_NOT_WORSE only. EXL3-6c5a and its parent stay open; no new quota.
    - [ ] **EXL3-6c5b — decide what the p1 smoke FAIL means (filed 2026-10-25).** Both p1 texts are coherent and agree on the answer; they diverge right after it. Read the first-divergence token's top-2 margin from the staged texts (re-run p1 with `--n-probs 2` on the same binary and quarter, about 10 min, correctness class) and record whether it is a near-tie (benign greedy divergence between two 4-bit-class files) or a real defect. Done when the margin is recorded and the smoke result is classified.
  - [x] **EXL3-6c6 — EXL3 CPU microbench re-run.** ✅ 2026-10-04 The 2026-10-03 17:46Z attempt in the CPU window refused on host load (rc 3, `ds41-scope-20260926/pause_measure.log`). Re-run in the next window.
    2026-10-04: EXL3-6c5 (full model) and this microbench are both steps of CPU window 2 (`/mnt/raid0/llm/tmp/ds41-scope-20260926/pause_measure2.sh`, output `/mnt/raid0/llm/tmp/cpu-window2-20261004/`). The window is armed and waits for DS41's measurement boundary. It holds q0–q3 for about 60–90 min, and DS41 is not stopped.
    2026-10-04 04:59Z: **refused again** (rc 3, load preflight) — workspace-ec subagents ran unlocked CPU work inside the held window (INC-20261004-subagent-unlocked-cpu-in-held-window in `docs/reference/agent-config/INCIDENT_LOG.md`). Re-scheduled as backlog item c1 (`/mnt/raid0/llm/tmp/cpu-backlog-20261004/c1/run.sh`, ~10 min; `/mnt/raid0/llm/tmp/backlog-schedule-20261004.md` row 1).
    2026-10-04 07:26Z: **measured** as backlog item c1 under a 0-95 region claim (`/mnt/raid0/llm/tmp/cpu-backlog-20261004/c1/runs/20261004T072620Z/mb/REPORT.txt`; DS41 and Q38FN shapes, N=1 and N=3, DRAM regime). **EXL3 CPU GEMV streams about 2× fewer bytes per second than GGUF**: e.g. DS41 `attn_q_b` 1280×32768 at N=1, EXL3_K4 (donor VBMI native) 120.3 µs ≈ 174 GB/s-equivalent vs IQ4_XS 55.3 µs ≈ 403 GB/s and Q4_K 46.1 µs ≈ 512 GB/s; the best EXL3 variant (K2 swizzled) still trails IQ4_XS on most shapes. Our `mul1` reference GEMVs are 2–3 orders slower (correctness path, not a speed path). Read with EXL3-6c5: on CPU, EXL3 has no decode speed case at these bit widths; any case is quality per byte. MXFP4-vs-Q4_K (DS41-C114a, c2) likewise showed no speed case (×1.00 N=1, ×1.04 N=3).
  - [ ] **EXL3-6c7 — executor performance items** (before or driven by the c5 profile): fold the per-op prep barrier into the producer, merged gate|up with per-segment `suh`, VNNI tier target attributes for portable builds, prefill band decode for 9–30-row MoE groups, the K3 indexer `index_qk_proj`. Re-emit verifier rows after any executor change.

- [ ] **EXL3-7 — Measure local policy and performance by regime.** *PARKED for the 27B with EXL3-6 (2026-10-03, EXL3-X0 rule).* On EPYC, sweep scalar/ISA tier, physical cores, NUMA placement, huge pages, layout, K, expert shape, and grouped versus runtime dispatch. On MI210, compare wave64 GEMV, MFMA, unified, grouped, and leftover-expert fallbacks across decode concurrency 1/8/16 and declared prefill shapes. Capture exact artifact/config identities, interleaved raw repetitions, dispersion, launch counts, rocprof traces, HBM traffic, full-output error, and in-window KFD/VRAM evidence. External NVIDIA rates remain context and never become EPYC/MI210 thresholds. The producer emits the versioned native measurement and verifier rows; strict adapters project eligible rows into `ClaimTuple`, and `claim_tuple.grade()` assigns the grade.
  - The mandatory serving grid is bare target plus later MTP/DFlash2 arms at decode concurrency 1/8/16, declared prefill lengths, fixed prompt and output token IDs, no accidental cache hits, and explicit cold/warm state. Report aggregate and per-request decode, full-wall throughput, TTFT, prefill, verifier steps, acceptance by position, resident memory, and context/request capacity. (`intake-1563#record`, `intake-1564#record`, `intake-1754#record`, `intake-1778#record`, `intake-1780#record`)
  - Measure standalone reconstruction, GEMV/GEMM, one layer, bare-target serving, and speculative serving as separate arms. Attribute gains among target bytes, kernel efficiency, scheduling/graph overhead, attention/KV, recurrent state, and accepted tokens per verification step. (`intake-1564#record`, `intake-1779#record`)
  - Use same-box candidate/control interleaving, hard regression floors, absolute reference checks, fail-closed path counters, and raw per-request rows. A differential pass is invalid when the baseline shares the defect. (`intake-1779#00`, `intake-1779#01`, `intake-1779#02`)
  - Preserve the published CIRU and NVIDIA numbers as workload-specific targets. Local success requires matching the reproducible workload envelope and explaining remaining gaps; no external value becomes a CPU/MI210 claim or a universal threshold. (`intake-1563#record`, `intake-1564#record`, `intake-1754#record`)

- [ ] **EXL3-8 — Implement hybrid CPU/MI210 streaming only after independent parity gates pass.** Build a failure-atomic HIP registered shared arena with explicit ownership, byte-exact DMA, async copy streams, deterministic teardown, and a ROCm sustained-link probe whose complete trace sets local thresholds. Stream only selected expert blocks, leave a configurable number on CPU, and record CPU GEMV, transfer, GPU kernel, overlap, fallback, and residency timelines. Compare whole-layer CPU offload, expert-split offload, GPU-only, and CPU-only under identical model residency and prompts.

- **[declined: ws58 2026-11-03 content-review: requires producing EXL3 and W4A16 arms from one teacher revision (a training/quantization-pipeline study) with no served-model decision attached]** **EXL3-9 — Run the controlled EXL3 versus W4A16 decision study.** Produce or obtain arms from one teacher revision with identical architecture, expert count/keep plan, non-target tensors, tokenizer, evaluation panel, and declared storage budget. Persist full-vocabulary teacher-forced logits and separate codec, pruning, and runtime effects. Report quality, resident memory, artifact size, latency, and throughput as separate directed metrics. A pruned W4A16 deployment arm may be useful, but it cannot serve as the matched codec control. Treat expert-ranking provenance as unavailable until its source becomes revision-pinned and inspectable.
  - Reject a W4A16/NVFP4 comparator until its exact module allocation, expert count, pruning plan, teacher revision, non-target precision, tokenizer, runtime, KV format, and evaluation panel are recorded. The official and community artifacts are distinct arms, not one generic “four-bit” baseline. (`intake-1753#record`, `intake-1775#00`, `intake-1776#00`, `intake-1781#00`, `intake-1782#00`)
  - Before admission, verify fused gate/up scale equality or compensate each half, independently reconstruct sampled matrices, reconcile all expected tensors, and run multilingual byte-token probes. A corrupted ModelOpt artifact cannot establish an EXL3 quality advantage. (`intake-1770#00`, `intake-1770#01`, `intake-1770#02`)
  - Keep task scores, teacher-forced KL/top-1, artifact size, resident memory, context capacity, decode, prefill, and serving throughput as separate directed metrics. Only matched teacher/architecture/module coverage can support a codec claim. (`intake-1759#record`, `intake-1775#01`, `intake-1776#01`, `intake-1781#01`, `intake-1782#01`)

- [ ] **EXL3-10 — Build the complete regression and promotion package.** Run existing-quant CPU coverage, EXL3 CPU/HIP correctness and stability, long-context and mixed-batch checks, nonfinite and guard corruption checks, and complete-candidate performance observations. Rebuild the candidate from fresh production plus all EXL3 changes; never reconcile separately measured pieces by cherry-pick at promotion time. Experimental results may nominate a candidate but do not modify the frozen branch, kernel store, launcher, or lineup. Promotion remains a separate final operator decision with a rollback anchor and production-named rerun.
  - Require target-only A/A, fresh-process A/A, forced-reject target-argmax, and c1/c8/c16 fail-capable token/logprob hashing before reading speculative output differences. Stable scores alone do not prove deterministic execution. (`intake-1761#record`, `intake-1765#00`, `intake-1765#02`, `intake-1767#00`, `intake-1767#02`)
  - Test packed GDN decode against an independent FP32 sigmoid-beta one-step oracle and a long recurrence. Do not make verification imitate a defective BF16 round trip. (`intake-1762#record`, `intake-1763#00`, `intake-1763#01`, `intake-1763#02`, `intake-1764#00`)
  - State each decided proposition explicitly: valid verifier acceptance, packed operator equality, recurrent-state equality, or complete autoregressive token-sequence equality. A pass on one proposition cannot clear another. (`intake-1760#record`, `intake-1766#record`)

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

## Research intake 2026-10-22 — SLQ / IST-DASLab / kaitchup Qwen3.8-27B SLQ (intake-2461..2493)

Source: research intake session intake-ist-slq-20261022, Stage-3 plan `/mnt/raid0/llm/tmp/intake-ist-slq-20261022/stage3/STAGE3_PLAN.md` (sha256 db108374cd1bd164e5baaac2586b9d3abf26daaba46aec4085192e4b0c0232ad); operator ruling 2026-10-22 approved a subset. Trigger prose and knowledge notes from that plan are still pending the operator and are not filed here.

- [x] **EXL3-EAR1 — Add an EAR column to llama-perplexity --kl-divergence on llama.cpp-experimental (intake-2461, intake-2464).** (filed 2026-10-22 via research intake, operator-approved 2026-10-22) In tools/perplexity/perplexity.cpp (the KLD per-token loop, about L175-252 @ ffc1bac82) accumulate the full-vocabulary sum of min(p_base, q) and the top-10-renormalized variant SLQ's evaluation.py uses, and print both beside Mean KLD and Same top p; branch from the current production tip, v10 stays frozen. Acceptance: EAR(base, base) = 1.0; 1 - sqrt(KLD/2) <= EAR <= 1 on every run (Pinsker); one cross-check against a Python recomputation from saved logits. The build is a CPU build-role job under region-lock --cpu-list (about 20-40 min); first measurements ride the next scheduled KLD pass (NEW-10 or NEW-13 in iqk-iquant-enablement.md), since EXL3-X0D was declined.
  - 2026-10-22 (workspace-58): code landed, NOT built yet. Branch `experimental/ear-kld-column-20261022` @ `782c11ae4` from the champion tip `dd3d9721c` (pushed to fork; v10 untouched): `tools/perplexity/kld-ear.h` (pure `kld_ear_compute`, full vocab + SLQ top-10 renorm), `kl_divergence_result` + per-token loop accumulate both, and a NEW `====== EAR statistics ======` block is appended after `Same top p` (`EAR full vocab`, `EAR top10 renorm`, `EAR Pinsker floor`, `EAR Pinsker check`); every pre-existing line is unchanged. `tests/test-kld-ear.cpp` passes in a file-scoped g++ compile (EAR(base,base)=1 within 16/65535, Pinsker, naive reference, ties). `tools/perplexity/kld-ear-crosscheck.py` recomputes the EAR lines from two saved base files. Build + unit test + tiny smoke (Qwen2.5-Coder-0.5B Q8_0 base vs Q4_K_M: EAR(base,base), Pinsker, byte-identity of old lines vs the champion binary, Python cross-check) are armed as filler `ear1-build` (`/mnt/raid0/llm/tmp/fillers-ws58-ear1/ear1_launch.sh`), waiting for a calendar grant. Receipts for the first real pass: `qwen4exp_quality_capture.py --mode kld-quantcmp` (VB-QUANTCMP-WIRE).
  - ✅ 2026-10-22 — **built and accepted.** Filler `ear1-build` ran 19:38:54-19:40:12Z on q3 (build role, 24 threads), rc=0, at `782c11ae43c75a0d291399896f833a370d52e319`. `test-kld-ear` all checks passed. Smoke on Qwen2.5-Coder-0.5B: EAR(base, base) full 99.998% / top10 99.999% (= 1.0 within fp16 logit rounding); Q4_K_M vs Q8_0 base: EAR full 91.21%, top10 92.82%, Pinsker floor 85.70% (floor <= EAR <= 1 holds); the 46 pre-existing stdout lines are byte-identical to the champion store binary `kernels/builds/cpu-20261020-dd3d9721c/bin`; Python cross-check from saved logits: pass. Results `/mnt/raid0/llm/tmp/fillers-ws58-ear1/results/20261022T193854Z/` (`result.txt`). First real EAR measurement rides the next scheduled KLD pass (NEW-10 re-run uses the v10 store binary, so it carries no EAR column; NEW-13 or a later quantcmp pass on this build does).

- *Declined (operator, 2026-10-22): EXL3-X0D, the A/B of the ISTA-DASLab Qwen3.8-27B GSQ-RCO IQ3_S/IQ3_XXS GGUFs (intake-2481#record) against the served Q8_0 — "not worth it".*
- *Declined (operator, 2026-10-22): EXL3-LB1E, extending the LB1c per-type sweep to IQ3_XXS/IQ2_S/IQ2_XS/IQ2_XXS/Q2_K — it was only motivated by the X0D file.*
- *Declined (operator, 2026-10-22): EXL3-EAR2, the BF16-anchored KLD/EAR run — its 55.6 GB BF16 download only served the 27B quant question.*
- *Declined (operator, 2026-10-22): downloading the kaitchup Qwen3.8-27B-SLQ-EAR98/98.5/99 checkpoints (intake-2462#record, ledger A-L2; option A not taken) — vLLM/Humming CUDA-only, not loadable on MI210, EPYC or llama.cpp, and no smaller than our Q8_0 at EAR99.*

- [ ] **QUANT-HEAD-1 — Audit and price 4-bit `output.weight` / `token_embd` on the served GGUFs.** **Owner: AutoKernel** (2026-11-06) — seeded as AK-QH-A, AK-QH-B in research seed file 08 (`loop/seeds/hypotheses/`, cpu-quant-gdn) (ee33ddc36), anchor C7r 62cb6a6af. The head is read in full every token and never amortises, so at 4-bit blocks it is the largest remaining per-token read. Audit every served DS41/Q38FN GGUF (current type, bytes per token, expected saving), then price one Q4_K conversion arm on the same model against WikiText-2 and the six-task set at the existing floor. Accept only if bytes per token fall and no task regresses beyond its recorded sigma; otherwise record the null. (intake-2646#record) [belief: pending]
- [ ] **QUANT-ROT-1 — Run the offline activation-rotation probe at a fixed per-32-block budget.** **Owner: AutoKernel** (2026-11-06) — seeded as AK-QR-1 in research seed file 08 (`loop/seeds/hypotheses/`, cpu-quant-gdn) (ee33ddc36), anchor C7r 62cb6a6af. On one real Q4_K row, simulate no rotation, a 32-wide Hadamard, a magnitude-sorted channel permutation, and KLT composed with Hadamard, measuring q8_K window error, block amax/clipping error and dKLD. Pre-register the MambaQuant prediction: rotation has a positive sign and its effect shrinks as scale granularity narrows. No kernel, no converter change. Stop when one arm beats the control by more than the window-error noise, else record the null. (intake-2648#record, intake-2645#record) [belief: pending]

## Track: iqk-iquant-enablement
<!-- gate: none -->

> Folded from `handoffs/active/iqk-iquant-enablement.md` @ `6a4026f0ab50` on 2026-11-02 (BRF-T1-F5, route 1a, operator D1/D5; retired row INF-26 → INF-80). Body moved verbatim, headings demoted two levels to nest under this track; every open and closed box kept its text and ID.

### iqk IQ-quant Enablement — shipped in v8, residual research active

**Status**: PROMOTED AND FROZEN IN v8 — `production-consolidated-v8` at `67a433bf45a8a091d83b4ea0b32ff0735fd51800`, `llama-server` version `10107`. The terminal both-mode lineup passed `24/24` smoke and `6/6` API; final-freeze attestation `artifacts/operator/ratify_v8_final_freeze_20260725.json` has SHA `e7fce2c5cd720940fc84b669f57b78a61589fd8baef9b4e03030ed0dc4a3175b`. The CPU Q4 architect remains live at `8083`. The campaign-scoped WAIVE-Q8 means v8 makes no Q8 performance or non-regression claim. See the 2026-07-25 audit section for residual post-v8 work.
**Created**: 2026-07-21 (via research-intake deep dive on intake-872/873)
**Priority**: POST-v8 RESEARCH — the production enablement defect is closed;
NEW-6, trellis gates, and the remaining riders below stay open.
**Branch**: ~~`iqk/enable-iquants-v7-20260721` @ `f78ec18fe`, worktree `/mnt/raid0/llm/llama.cpp-iqk-iquants`~~ **superseded 2026-07-25** — the v8 branch re-implemented this as `b8ad9d292` (same 5-type whitelist + tests + IQ3_XXS small-shape NMSE guard) WITHOUT merging `f78ec18fe`; the worktree branch is historical after the v8 freeze.
**Superseded branch**: `iqk/enable-iquants-20260721` @ `e06f5368f` (off the experimental tip, only 3 of 5 types) — do not use
**Related**: [tq3-quantization-evaluation.md](quantization-and-low-bit.md#track-tq3-quantization-evaluation), [glm52-reviewer-capability-gates.md](reviewer-control-plane.md#track-glm52-reviewer-capability-gates), [v7-promotion.md](../completed/v7-promotion.md), completed [iqk-port.md](../completed/iqk-port.md)

---

#### Executor start here

B1-B5 are complete in frozen v8. Start from the unchecked post-v8 tasks below;
do not rebuild or re-promote the frozen production branch.

#### Why this matters (the case for doing it now)

**1. We are paying for an optimisation we are not receiving.** `GGML_IQK=1` exists to swap in ik_llama's AVX-512 GEMM kernels — measured **+7.9-8.8% decode on Q4_K** and **+22-49% prefill** on other quant families during the original port. But iqk dispatches **per quant type** through `iqk_typeA_supported` (`ggml/src/ggml-cpu/iqk/iqk_dispatch.cpp`), and that whitelist contained only K-quants and legacy quants. `iqk_set_kernels_iquants` and `iqk_convert_iquants_q80_r8` were linker stubs returning `false`. So on an IQ-quant model the flag accelerates the attention and shared-expert tensors and **falls back to the stock kernel for the parameter bulk** — with no error, no warning, and no log line. It looks enabled and is mostly inert.

**2. It is not one model — it is every IQ-quant model in the registry.** Tensor counts parsed directly from GGUF headers (2026-07-21, header bytes only):

| Model | Tensors covered by this change | Not covered |
|---|---:|---|
| **GLM-5.2 UD-IQ2_M** | **221** (148 IQ2_XXS + 71 IQ3_XXS + 2 IQ2_S) | IQ4_XS ×4 |
| **Qwen3.5-122B-A10B UD-IQ2_M** | **143** (94 IQ2_XXS + 47 IQ3_XXS + 2 IQ2_S) | IQ4_XS ×1 |
| **Qwen3-Next-80B-A3B i1-IQ2_M** | **433** (414 IQ2_S + 19 IQ3_S) — **54% of all 807 tensors** | — |
| **Hy3-IQ1_M-mtp** | **157** (79 IQ3_XXS + 78 IQ2_XXS) | IQ1_M ×82 (needs the still-stubbed 1bit family) |

In every case the covered tensors are the MoE routed experts (`ffn_gate_exps` / `ffn_up_exps` / `ffn_down_exps`). For a 256-expert/8-active MoE those *are* the model: the parameter bulk, the dominant term in decode bandwidth, and the dominant term in prefill FLOPs. **Qwen3-Next-80B is the biggest proportional beneficiary** — more than half its tensor count — which was not obvious before the headers were parsed, and is a reason not to treat this as a GLM-only fix.

**3. The code already predicted this exact failure.** `iqk_stubs.cpp:8-12`, written at port time:

> *"The registry shows ZERO use of IQ-quants … so these families are stubbed to satisfy the linker … **If/when we adopt IQ-quants (e.g. future GLM IQ2), these MUST be replaced with the real ik kernels + their block types — do not leave them stubbed for a quant we deploy.**"*

That was correct when written — the registry genuinely had no IQ-quant models. Four have since been added. This is a stale-assumption defect with a written expiry condition that has passed, not a design gap.

**4. The change is small because the hard work was already done.** The 202KB kernel file `iqk_gemm_iquants.cpp` was vendored during the port and simply never added to the build. `IQ2_XXS=16`, `IQ2_XS=17`, `IQ3_XXS=18`, `IQ3_S=21`, `IQ2_S=22` are **native ggml enum values** — so no type registration, no `type_traits` growth, no `GGML_TYPE_COUNT` change, no GGUF format change, no requantisation, and no downloads. Three files, +13/−2.

**5. Expected payoff, stated honestly.** Prefill-dominant, decode-modest. Decode at 2-3 bpw sits deep in the memory-bandwidth-bound regime where the original port measured ~0% on Q8_0; the +22-49% figures came from prefill. GLM-5.2 prompts run 3-12K tokens and its measured decode is 2.49 t/s (5.33 with MTP), so prefill is the operative axis for that role. **Do not promote this on an assumed decode win** — B3 exists to measure it.

#### What changed (initial enablement plus v8 hardening)

| File | Change |
|---|---|
| `ggml/src/ggml-cpu/CMakeLists.txt` | add `ggml-cpu/iqk/iqk_gemm_iquants.cpp` to the build |
| `ggml/src/ggml-cpu/iqk/iqk_stubs.cpp` | remove the two `return false` stubs so the real symbols link |
| `ggml/src/ggml-cpu/iqk/iqk_dispatch.cpp` | whitelist IQ2_XXS, IQ2_XS, IQ2_S, IQ3_XXS, IQ3_S, and IQ4_XS; reject Q2_K/Q3_K before activation quantization |

The initial five IQ2/IQ3 types use `iqk_gemm_iquants.cpp`. Final v8 commit
`8890e2b14` also enables native IQ4_XS through the already-vendored
`iqk_gemm_kquants.cpp` kernel (`set_kernels` at `:2724`, conversion at `:2780`) and
adds compile-time dispatch assertions. The `*_R4` repacked variants remain ik-only
and unreachable from our GGUFs. IQ1_M remains excluded because its 1-bit family is
still stubbed.

**Pre-verified statically (no build):** every `GGML_TYPE_*` referenced by `iqk_gemm_iquants.cpp` resolves — the five natives from `ggml.h`, the `*_R4` variants via the `iqk_ext_types.h` shim, and `Q8_2_X4` via `#define … 99` in `iqk_config.h:18` (used only inside comments in this file).

#### Why it is not already on production v7

Verified 2026-07-21: host load average ~48, seven llama-servers resident, and a **decision-grade architect-model-selection bench in flight on the production v7 binary** — including arm `A1_qwen35_122b_iq2m`, one of the four affected models. Rebuilding production would have corrupted an active measurement. Independently, CLAUDE.md freezes production kernels and routes all kernel work through experimental branches, and a no-regression claim across four models requires inference evidence we could not gather.

#### Outstanding tasks (require a quiet window)

- [x] **B1 — Build.** ✅ 2026-07-25 — re-anchored to v8: `b8ad9d292` compiles `iqk_gemm_iquants.cpp` in `build-v8-cpu`/`build-v8-hip`/`build-v8-sanitize`; `test-iqk-ser` + `test-iqk-valid-control` pass on all three builds. Historical HIP CTest was `56/59`, with all 3 failures classified baseline with paired differentials; exact-tip HIP is `59/62` with the same 3 failure classes. This is not a green full-HIP-CTest claim. Exact-tip CPU and sanitizer qualification and paired evidence are durable under `epyc-inference-research/data/kernel-v8-candidate/`. The commit also fixed real UB in the kernels AND in the native `arch/x86/quants.c` reference paths (load-bearing for test validity).
- [x] **B2 — Correctness before speed, operator-scoped.** ✅ 2026-07-25 — exact 6-arm/24-task, three-model attestation `epyc.iqk_real_model_correctness.attestation.v1`, bound to exact tip `67a433bf4`, passed at `epyc-inference-research/data/kernel-v8-candidate/iqk-real-model-correctness/run-20260725T102000Z-67a433bf4/` (nested `101945Z`). It covers GLM-5.2-IQ2, Qwen3-Next-80B-IQ2, and Hy3-IQ1 with same-seed IQK-on/off coherence, anti-garbage, and per-token-logprob evidence. The qwen3.5-122B B2 arm is omitted under the separate operator instruction to skip its regression tests. GPU-IQ2 arm excluded; CPU Q4 architect remains live. Laguna CPU/IQK is excluded by operator direction in favor of GPU IQ2, so this does not claim a Laguna IQK-on/off test.

  **2026-07-25 operator correction / provenance:** this session incorrectly treated the R7 "A4 suffices" benchmark verdict as an executed Qwen3.5-122B deprecation. It is a pending operator lineup decision, not a serving-lineup change. The restored both-mode contract serves the CPU Q4 architect on `8083`; only its B2 regression arm remains out of scope under the separate regression-skip instruction.
- [x] **B3 — Speed.** ✅ 2026-07-25 — the ratified `P-BENCH-PREFILL-1`
  matrix passed all 14 executed v7/v8 pairs with zero throughput failures at
  `epyc-inference-research/data/kernel-v8-candidate/cpu-prefill-regression/run-20260725T155655Z-v4-waive-q8-kfd-procrace-swapoff/summary.json`.
  IQK-on utility ratios `(pp2048, tg128)` were GLM-5.2 `(1.4274, 1.0013)`,
  Hy3 `(1.3297, 1.0035)`, and Qwen3-Next `(1.3900, 0.9875)`; all three
  satisfy the ratified IQ rule. The operator's campaign-scoped WAIVE-Q8
  excludes four Qwen3.6 Q8 arms, so v8 makes no Q8 performance or
  non-regression claim.
- [x] **B4 — Non-IQ regression check.** ✅ 2026-07-25 — Gemma Q4 passed the
  ratified throughput check at `1.0830x` pp2048 and `1.0075x` tg128. The
  terminal paired quality gate used one pinned 200-question MMLU-Pro +
  195-question GPQA set and produced exact v7/v8 ties with zero errors:
  worker Gemma Q4 `36.5% / 24.6%`, architect Qwen3.5-122B Q4
  `63.5% / 56.9%`. Evidence is committed in research at `965e353e` under
  `data/kernel-v8-candidate/quality-gate/run-20260725T204443Z-fullcontract-both-mode/`.
  - 2026-07-25 audit note: **this exact risk class already materialized** — `b8ad9d292` incidentally reclassified Q2_K/Q3_K activations Q8_2_X4→Q8_K, engaging never-validated iqk kquant kernels and corrupting Hy3 output (caught on live output at 20:47Z, NOT by tests; fixed same day by `1977a5d78` + static_asserts). The measured non-IQ check is therefore NOT a formality for v8 — it is mandatory, and default CI still cannot catch a re-introduction (see NEW-4 below).
- [x] **B5 — Promote.** ✅ 2026-07-26 — promoted and frozen as `production-consolidated-v8` at `67a433bf45a8a091d83b4ea0b32ff0735fd51800` (version `10107`). Terminal both-mode lineup passed `24/24` smoke and `6/6` API; final-freeze attestation `artifacts/operator/ratify_v8_final_freeze_20260725.json` SHA `e7fce2c5cd720940fc84b669f57b78a61589fd8baef9b4e03030ed0dc4a3175b`. Do not hand-patch the frozen production kernel.

- [x] **NEW-8 — Q38FN IQ\*_K/KS self-quant, measured in ik_llama.cpp before any port.** (filed 2026-10-04) Operator ruling
  2026-10-03/04: self-quant allowed "exceptionally if justifiable" (lifts the no-requant constraint for this
  option only). Evidence: [`docs/reviews/cpu-quant-research-20261003.md`](../../docs/reviews/cpu-quant-research-20261003.md) §3.3 #3 / §4.
  - Step 0: `/mnt/raid0/llm/ik_llama.cpp` @ `c04881fc0` has **no `qwen4exp` arch**. Fetch newer ik upstream
    into a scratch worktree and build it there. Measurement instrument only: ik is deprecated as a serving
    path, and its binaries never serve. Prove build currency (binary mtime vs commit date) before reading any number.
    - *(2026-10-28 private build and metadata preparation.)* Isolated upstream source `/mnt/raid0/llm/tmp/refactor-01a16fc3/inf26-new8-ik-upstream-20261028` at `1c5ea124098890184b297023cd9fc9655451b1ec` contains `qwen4exp` and IQ*_K/KS support. An incremental Release CPU build at `/mnt/raid0/llm/tmp/refactor-01a16fc3/inf26-new8-ik-cpu-build-20261028` completed the quantizer, perplexity, bench, server and imatrix targets with IQK mul-mat, flash attention and all-quants enabled. The binaries are newer than the source commit and the bench resolves this build's libraries. A header-only scan of the existing UD-IQ4_XS shards matched 144 expert tensors (48 each gate/up/down); input identities were stat-checked, not freshly fully hashed. The scan and bounded resource log are in `/mnt/raid0/llm/tmp/refactor-01a16fc3/inf26-new8-mapping-check-20261028/`. The Q8 source and a real model load remain outstanding; no quantization, quality or performance result is claimed. [belief: cc]
  - Step 1, source and base: no high-precision Q38FN GGUF is on disk. Pull unsloth `Q8_0/` (188.2 GB, about 5.8 h
    at ~9 MB/s, one download at a time) as both quantize source (`--allow-requantize`) and KLD base. BF16 (354 GB)
    is cleaner but leaves under 50 GB free once an output arm exists (500 GB free on 2026-10-04). Caveat: a Q8_0
    reference has a KLD floor of about 0.022–0.027.
  - Step 2: imatrix, then quantize 1–2 arms: IQ4_KS or IQ3_K gate/up, IQ5_KS/IQ4_KS dense, IQ4_NL down (640-wide).
    About 85–100 GB per arm.
  - Step 3: in the same ik binary, measure UD-IQ4_XS and the new arm(s) (IQ4_XS-uniform dropped: retired 2026-10-20, keeper UD-IQ4_XS): `--kl-divergence` (mean KLD,
    same-top-1), PPL, `llama-bench -p 5,256 -n 128` r3, and the serving shape (MTP d4, verify N=5). Compare ratios
    within ik only, never absolute numbers across trees.
  - Budget: about 3–5 CPU-window hours excluding the download (imatrix ≤ 30 min, quantize ~0.5–1.5 h per arm, KLD
    ~7 min per file plus base, bench ~25 min), in a DS41 pause window with DS41 unloaded. Peak disk ≈ 188 + 2×95 +
    25 (logits) ≈ 400 GB; delete Q8_0 after the base logits are saved.
  - **Justifiable means all of:** the IQ\*_K arm is ≥ +8% decode vs UD at the serving shape; ≥ +3.4–4.5% (the admission
    floor) over IQ4_XS-uniform, otherwise the zero-port file swap dominates (INF-70 XFER-3) — **criterion
    retired 2026-10-20**: the operator retired the uniform file (keeper UD-IQ4_XS), which takes the zero-port
    swap off the table, and the 2026-10-04 EXL3 window measured it at +17.8% PPL vs UD
    (`exl3-cpu-mi210-implementation.md`, EXL3-6c5), so it is no quality-equivalent competitor. Mean KLD ≤ UD's and
    same-top-1 within 1 pp; a paired per-item task eval no worse than UD. If any fails, the port is closed. If all
    pass, port in `llama.cpp-experimental`: register about 15 types (decide the ID policy first), compile the vendored
    iqk kernels and quantizer, respect the `715383cde` OOB class — 2–4 sessions.
  - 2026-10-04 (ak-ds41-main, backlog drain): backlog item c3 (IQ4_K/IQ4_KS on Q38FN via the ik instrument) is
    **BLOCKED** on this item's Steps 0 and 1. Checked on disk: `/mnt/raid0/llm/ik_llama.cpp` has no `qwen4exp` arch,
    no IQ4_K/KS Q38FN GGUF exists, and no Q8_0/BF16 Q38FN source exists. So c3 cannot run inside the drain; it needs
    the scratch ik build (Step 0) and the ~5.8 h Q8_0 download (Step 1) first. Schedule:
    `/mnt/raid0/llm/tmp/backlog-schedule-20261004.md` row 3. Justification bar: INF-70 XFER-3 (uniform IQ4_XS is
    +24-34% faster than UD at +17.8% PPL, `artifacts/cpu-window2-20261004/`). [declined: operator 2026-11-03 model-audit: operator: not pursuing Q38FN self-quant; production UD-IQ4_XS and GSQ IQ3_XXS on disk]

- [x] **NEW-9 — Compare Magnitude's CPU IQ2/IQ3 decode and VNNI repack against iqk (documentation-only, zero compute).** ✅ 2026-10-20 — each difference classed (decode-bound / prefill-GEMM-bound / layout-only) in the note below; NEW-5 not reversed; NEW-6(b) fed. Read `inference/seismic/native-cpu/src/weights.rs` (IQ grid CPU decode, rows16/rows8 repack; the vector-coded representation near L1271) and its x86v4vnni `dot_u8_i8` path in `/mnt/raid0/llm/tmp/dive-1979/repo` @ `940e51b` against `ggml/src/ggml-cpu/iqk/iqk_gemm_iquants.cpp` for IQ2_XXS, IQ2_XS and IQ3_XXS (IQ1 is stubbed and out of scope). Record any decode-then-int8-dot structure iqk lacks, cross-checked against NEW-5 (NO-GO: VPDPBUSD is not a decode win on this Zen5 host) and NEW-6(a)(f) (no 16-wide func16 kernels, no zmm variant). Done when each difference is classed decode-bound, prefill/GEMM-bound or layout-only and either feeds a NEW-6 rider or is closed with its reason; no build and no bench.
  - **Factual note 2026-10-20 (NEW-9; read-only, no build, bench or run; checkbox left open for main review).** Sources: Magnitude `inference/seismic/native-cpu/src/weights.rs` @ `940e51b`; production tree `ggml/src/ggml-cpu/iqk/iqk_gemm_iquants.cpp` and `iqk_mul_mat.cpp` @ `ffc1bac82` (the x86 branch is `#ifdef __x86_64__` at `iqk_gemm_iquants.cpp:12` to `#else` at `:2817`; file last changed `b8ad9d292`). Cross-checked against NEW-5 and NEW-6(a)(b)(f).
  - **Decode-then-int8-dot structure.** Magnitude decodes each 32-value packet to signed i8 codes (`weights.rs:1296-1304` `grid_codes`; `Grid::dot_q8` `:1452-1480`) and takes an integer dot per packet via `dot_i8_i8` (`:632-643`): VPDPBUSD with a +128 weight offset and a per-call activation-sum correction (`:635-639`), or AVX2 maddubs (`:640-641`). iqk already has this structure in its direct x86 IQ kernels: EvenSignHelper plus VPDPBUSD (`iqk_gemm_iquants.cpp:685-691`, under HAVE_FANCY_SIMD) or VPMADDUBSW (`:693-696`), and the `minv = 43` offset in `DequantizerIQ2XXS` (`:137-224`). So the decode-then-int8-dot form itself is not missing from iqk. What iqk has and gates off for these types is the decode-then-int8 repack: `iqk_convert_iq2_xxs_q8_k_r8` (`:1909`), `iqk_convert_iq2_xs_q8_k_r8` (`:1961`), `iqk_convert_iq3_xxs_q8_k_r8` (`:2464`). `is_dequant_better` returns `type` unchanged for IQ2_XXS, IQ2_XS, IQ2_S, IQ3_XXS and IQ3_S (`iqk_mul_mat.cpp:297-306`), so the repack is not taken for them. Magnitude has no repack step at all: rows16 planar rows are decoded at use (`weights.rs:1415-1433`).
  - Differences and class:
    1. **Sign placement and dot form.** Magnitude: weight-side sign, then VPDPBUSD with +128 offset and correction (`weights.rs:632-639`). iqk GEMV path: activation-side sign with unsigned grid magnitudes (`iqk_gemm_iquants.cpp:199-202`, `:207-211`, into `multiply_add_1` `:685-691`). iqk q8_K path: weight-side sign with the minv=43 offset. Class: **decode-bound** (inner per-packet dot of the GEMV-shaped `dot_q8`). Closed: the offset and correction are extra work per packet, and VPDPBUSD is the form NEW-5 measured as no decode win on this host (NEW-5 NO-GO, `iqk_gemm_iquants.cpp:683-717`). No new lever.
    2. **Group-16 (IQ2_XS) dot.** Magnitude runs two full 32-lane dots per packet, each with the other half of the activations zeroed (`weights.rs:1472-1476`), each with its own correction. Class: **decode-bound**. Closed: redundant lanes by construction; nothing to import.
    3. **Repack.** Magnitude: none. iqk: the convert path exists but is gated off for these types (`iqk_mul_mat.cpp:297-306`) and is reached only when `npt >= 16` (`:618-619`). Class: **layout-only** (the repack is the layout change). Feeds **NEW-6(b)** as the gated path only: Magnitude supplies no root cause for the Zen4 correctness issue. The NEW-6(b) locator `iqk_mul_mat.cpp:246-254` is stale at this tip: that range is the dispatch loop; the gate is at `:297-306`.
    4. **Tile width.** Magnitude's rows8 tile is 8 rows (`weights.rs:122-130`; Grid ROWS8 names at `:1313`, `:1337`, `:1366`). iqk: k_nr=16 under HAVE_FANCY_SIMD, 8 otherwise (`iqk_gemm_iquants.cpp:1910-1916`); `func16 = nullptr` for the plain IQ types (`:2754`). Class: **prefill/GEMM-bound**. Feeds **NEW-6(a)**: Magnitude has no 16-wide IQ kernel, so it gives no evidence either way; (a) stays open.
    5. **Vector width.** Magnitude's VNNI path is 256-bit `_mm256_dpbusd_epi32` (`weights.rs:618-627`) with no 512-bit variant. Class: **prefill/GEMM-bound**. Feeds **NEW-6(f)** as a cross-check only: the same 256-bit pattern appears in Magnitude and it has no zmm reference; (f) stays open.
    6. **Scale and factor.** Magnitude: odd scale `2s+1` per 16 or 32 values with one f32 factor per 256 (`weights.rs` `Grid::packet`, impl `:1387-1412`). iqk: `2s+1` in `load_scales` and d = 0.125 * f16 (inside `:137-224`). Class: **layout-only** (storage placement; same arithmetic). Closed: no kernel gain.
    7. **Sign parity.** Same trick: Magnitude `signs.count_ones() & 1` (`weights.rs:1296-1304`); iqk EvenSignHelper popcount (`iqk_gemm_iquants.cpp:71-91`). No difference. Closed.
  - Verdict: no decode-then-int8-dot structure is missing from iqk's direct IQ2/IQ3 kernels. The only candidate, the repack path, is gated at `iqk_mul_mat.cpp:297-306` and reaches NEW-6(b) as a pointer only. NEW-5 is not reversed by this reading. No build, bench or run.

#### Decision gates

- **B2 fails on any model** → do not promote; isolate kernel vs convert path, and consider a narrower whitelist (e.g. IQ2_XXS + IQ3_XXS only).
- **B3 shows a decode regression** → may still be worth promoting if prefill dominates for the affected roles, but that becomes an operator call with numbers attached, not an assumption.
- **B4 shows any non-IQ delta** → stop. An additive dispatch change must not move the K-quant path; a delta means something else moved.

#### Adjacent: the KT/trellis family (folded in from tq3-quantization-evaluation.md)

**Format boundary (2026-09-25):** IQ*_KT and EXL3 are distinct tensor formats, codebooks, loaders, and
kernel paths. T2/T3 below govern IQ*_KT only. Project-owned EXL3 CPU and MI210 work is tracked by
[`exl3-cpu-mi210-implementation.md`](quantization-and-low-bit.md) (`INF-80`) and may proceed independently.

Chasing the *trellis* stub is what uncovered the IQ-quant defect above, but the two are not comparable in cost and should not be sequenced together.

**Trellis is 3-6 days and medium-high risk, not a flag flip.** `iqk_gemm_ktquants.cpp` is absent from `CMakeLists.txt`; the `block_iq2_kt`/`block_iq4_kt` structs do not exist in our tree (only in `/mnt/raid0/llm/ik_llama.cpp`); and the KT types are **synthetic casts at 153-158 against `GGML_TYPE_COUNT = 43` with no `type_traits` row**, so a KT GGUF cannot load at all — the same OOB class commit `715383cde` already had to fix once. Honouring ik's IDs against a dense `type_traits` array ripples into the CUDA/HIP per-type tables. KT is also CPU-only, so the MI210 cannot participate.

**And the bpw arithmetic undercuts the motivating use case.** `block_iq2_kt` is 68 B per 256 weights = **2.125 bpw**, versus **IQ2_XXS at 2.0625 bpw** — trellis is *larger* than what GLM-5.2 already uses, so it saves zero bandwidth while adding per-weight arithmetic. It is a **quality-at-equal-bpw play mis-framed as a speed play**. Against Q4_K_M the saving is ~17.5%, but our own iqk data (+7.9-8.8% on Q4_K, ~0% on Q8_0) shows we are not fully bandwidth-saturated at 4-bit, so added arithmetic eats into it. ik's own author states KT quants are "generally slower for token generation on CPU due to likely compute bottleneck".

**Sequencing (do not reorder):**
- [x] **T1 — Do B1-B5 above first.** ✅ 2026-07-26 — satisfied by the
  frozen v8 promotion; continue with T2 only under its separate gate.
- [ ] **T2 — Gate trellis in `ik_llama.cpp`, not in our tree.** `/mnt/raid0/llm/ik_llama.cpp` is already on disk and is the reference implementation. Build it in a scratch dir purely as a measurement instrument and bench IQ4_KT vs Q4_K_M and IQ2_KT vs IQ2_XXS *there*. This answers the whole question without porting anything. Needs operator inference approval; it is a bench harness, not a second serving binary.
  - [x] **EXP01-PILOT — bounded EXP-01 pilot for T2/T3 (BRF-T4-EXP01, backlog-refactor 2026-11 manifest package EXP-01).** [inference] ✅ 2026-11-04 [belief: cc]
    - [x] **EXP01-SMOKE-ISOLATION — isolate qualification data from official measurements.** Repair the Qwen3.6-35B-A3B EXP-01 launcher so four-CPU smoke outputs cannot become official quarter-run repetitions; reject resumed allocation and native thread-count mismatches. Acceptance: repaired `brf-exp01-trellis-pilot-20261104-r3` passes publisher smoke on 0-3 with separate native result and official `run-r3/results.jsonl`; preserve the declared estimator and stop rules. Evidence: `docs/evidence/exp01-pilot-smoke-isolation-20261104.json`. ✅ 2026-11-04 [belief: cc]
    Route (operator decision 2026-11-02, decision tool): "proxy screen, then port". The LOW-BIT lane rule (DS41/Q38FN only) is waived for THIS pilot only:
    the waiver covers this box and its two rows and nothing else (no other quant or trellis work, and T3's own identity is unchanged). The pilot is a futility
    screen on a model the instrument can load. Port condition: IQ4_KT beating Q4_K_M on the screen (the tg128 ratio band clears 0.95 and the paired
    24-item slice is not worse) triggers the `qwen4exp` port into an ik scratch worktree, plus a Q38FN requant from Q8_0; a futility result ends the screen
    and the port is not started.
    Proxy identity: Qwen3.6-35B-A3B (`general.architecture` `qwen35moe`, loaded by the instrument) requantized from its on-disk Q8_0
    `/mnt/raid0/llm/models/Qwen_Qwen3.6-35B-A3B-Q8_0.gguf` (36914690368 B, sha256 `afddb074…dbd5`; the registry carries no sha, so the pin is the HF LFS
    etag, equal to a local `sha256sum`) by the instrument's `llama-quantize --allow-requantize` into Q4_K_M (control), IQ4_KT, IQ2_XXS and IQ2_KT. IQ3_KT is
    not an arm of the manifest and is not built. Arm shas are pinned in `models.env` from the built files, outside any grant.
    Shared caveat (every arm, so the screen stays relative): all arms are requantized from Q8_0 rather than from a high-precision source, and none uses an
    imatrix of its own (r2 supersedes this: every arm shares ONE imatrix generated in the BUILD row, see the 2026-11-03 republish note; no `--ignore-imatrix-rules`). Absolute quality is not evidence; ratios and paired per-item flips are.
    Instrument: the read-only `/mnt/raid0/llm/ik_llama.cpp` @ `c04881fc0f31dae5f8ec59c1d683889f0c9dfa11` (clean tracked state;
    `build/ggml/src/libggml.so` sha256 `06d6cfac…8b74b` carries 21 `iq4_kt` strings; `build/bin/llama-bench` `58194ccf…af55`); linkage stays inside the ik build.
    Metric: tg128 tokens/s (higher is better), IQ4_KT/Q4_K_M and IQ2_KT/IQ2_XXS ratios, plus paired per-item correctness flips on the 24 items.
    Control: Q4_K_M (speed A/A spread + the same 24 items for quality). Bounds: 2 pairs × 3 launches/arm interleaved ABAB + 24 items × 2 quants;
    one CPU quarter, ≤90 min, hard stop at grant end.
    Stop rule (`docs/guides/agent-workflows/measurement-sufficiency.md`): planned look per launch from launch 2; stop-on-answer when the tg128 ratio band clears
    1.00, stop-on-futility when it lies wholly below 0.95, hard cap = the 90 min grant; all are operational decisions, never a T3 gate result; the quality pass stays open.
    - [x] **EXP01-WEIGHTS-RETENTION** — `/mnt/raid0/llm/tmp/brf-exp01` is KEEP: 4 good A3B quants remain after the failed-build Q4_K_M was trashed (2026-11-06 disk triage, operator-adhoc-ops). Reclaim them once the EXP01 pilot row is filed, or move them under `models/` if kept. [no-belief: not-a-result] 2026-11-07 DONE (operator-approved): pilot is filed (r3/r4, port HOLD); `models/` and `build/` (~58 GB) trashed via guarded_rm, scripts/logs/iqk-new.md kept; quants rebuildable from Q8_0.
    Eval set (pinned): `/mnt/raid0/llm/tmp/brf-exp01/items/exp01-items-24.jsonl`, 24 items, sha256 `96dc98cf6b2cfdd65897f1deaf2b6f8481225d013851262cf08d6171f150fdbc`.
    Seed 20261102 draw (`/mnt/raid0/llm/tmp/brf-exp01/bin/make_items.py`, a pure function of the pool sha) of 12 `cruxeval` (exact_match) + 12 `general` MMLU (multiple_choice) items from the canonical
    `epyc-inference-research/benchmarks/prompts/question_pool.jsonl` (sha256 `73a2ed5a…818f8b`); ChatML user turn + empty think block, greedy 256 tokens; item hash = sha256(prompt+expect_regex).
    Rows (both via `publish_row.py` with `ROWFLOW_REPO=/mnt/raid0/llm/views/epyc-root-main`, handoff_task `quantization-and-low-bit.md:EXP01-PILOT` (`iqk-iquant-enablement.md` is not a handoff file), scratch_root `/mnt/raid0/llm/tmp/brf-exp01`):
    BUILD `brf-exp01-trellis-build-20261102-r2` (supersedes r1; `/mnt/raid0/llm/tmp/brf-exp01/build_launcher.sh`, one CPU quarter, role build, min-window 4500 s; arms land in `models/`, about 58 GB, 325 GB free at publish)
    then MEASURE `brf-exp01-trellis-pilot-20261102` (`/mnt/raid0/llm/tmp/brf-exp01/launcher.sh`, one CPU quarter, role bench, min-window 5400 s, engine `filler_run15.sh`, job `/mnt/raid0/llm/tmp/brf-exp01/bin/job.sh`).
    Dependency and smoke sequencing: the allocator has no dependency field, so `/mnt/raid0/llm/tmp/brf-exp01/bin/precond.sh` FAILS CLOSED (rc 1, first line `build row … not complete`) until
    `/mnt/raid0/llm/tmp/brf-exp01/build/BUILD-DONE.json` exists, each arm's size/mtime matches it, every `*_SHA` is pinned and the ITEMS sha matches. The smoke IS the dry run and runs the real
    precond, so a smoke before the build completes FAILS by design; the MEASURE row is published, and its smoke run, at the end of the BUILD row (BUILD-DONE present, arm shas pinned),
    never before. It counts as ready only on smoke PASS.
    est: ~3000 s (MEASURE) from `/mnt/raid0/llm/tmp/brf-exp01/fixture-run/results.jsonl` (2 s per 0.6B launch plus ~45 s model load, scaled to 35B; 12 launches + 48 llama-cli items);
    est: ~3900 s (BUILD) from `/mnt/raid0/llm/tmp/brf-exp01/fixture/quant-IQ4_KT.log` (87 s on 8 cores for 0.6B, scaled by parameter count x58 and 24 cores = ~1700 s per KT arm; Q4_K_M ~85 s, IQ2_XXS ~250 s, 4 source reads).
    An end-to-end self-test on a non-identity fixture (Qwen3-0.6B requantized to Q4_K_M/IQ4_KT by the instrument) passed validity, linkage, mechanism-selected,
    looks, quality capture and summary; its numbers are not EXP-01 evidence (fixture tg128 ratio 0.64 is a plumbing check only).
    - 2026-11-03 BRF-T4 close-out (ws58): **NO VERDICT, nothing was measured.** The BUILD row `brf-exp01-trellis-build-20261102` ended rc=4 after 3 s (22:10:33Z), although rowflow
      shows it `done`. Its `plan-IQ2KT` unit returned rc=1 (`Missing importance matrix for tensor blk.0.attn_gate.weight in a very low-bit quantization`; `build/plan-IQ2KT.log`
      sha256 `df3ac0336156…`). The job forced `--ignore-imatrix-rules` for IQ2_XXS only, and the smoke planned IQ4_KT only. No arm exists and BUILD-DONE is absent, so MEASURE
      `brf-exp01-trellis-pilot-20261102` was never published and no smoke ran. The `post_build.sh` watcher is still polling and was not re-run.
      Repaired in scratch, not run: `bin/build_job.sh` now forces IQ2_KT the same way (the shared no-imatrix caveat now covers both 2-bit arms), and resume skips only successful
      units. Next: republish BUILD as `brf-exp01-trellis-build-20261102-r2`. [no-belief: no measurement produced]
    - 2026-11-03 republish (ws58, BRF-T4 follow-up): BUILD `brf-exp01-trellis-build-20261102-r2` published (`priority_rank` 1, one CPU quarter, min-window 6000 s, estimate 5700 s, smoke PASS on 0-3). The earlier scratch repair (`--ignore-imatrix-rules` for IQ2_KT) is replaced, because a 2-bit trellis arm quantized without an imatrix is garbage: the row first runs unit `imatrix` (`llama-imatrix` on the Q8_0 source, calibration `/mnt/raid0/llm/tmp/brf-exp01/calib/wiki.test.raw`, a copy of `data/wiki.test.raw`, sha256 `bfe9eb16ab9987fb88bde4ea9a30a00f2a45db01dfc14bad78d05325789c4f12`, 32 chunks x 512 tokens, timeout 3000 s, about 1800 s of the estimate; preflight fails closed on the calibration sha), then `llama-quantize --imatrix` for all four arms (one shared imatrix, so the screen stays relative). The smoke plans IQ4_KT and plans IQ2_KT with the rule bypassed (dry-run shape check: 9.7 GB, rc 0); the with-imatrix plan units run in the real row and fail closed in seconds. `BUILD-DONE.json` is stamped `row=…-r2`, and `precond.sh` and `post_build.sh` refuse any other stamp. **Owner step: after the r2 build completes, run `bash /mnt/raid0/llm/tmp/brf-exp01/bin/post_build.sh` once** (pins the arm shas, runs precond, publishes MEASURE `brf-exp01-trellis-pilot-20261102`, whose smoke is its dry run). No new watcher is armed; the stale r1 watcher pid 1371548 (old script inode) is not relied on. [no-belief: no measurement produced]
- [ ] **T3 — Port only if T2 wins.** Gate: IQ4_KT must reach **≥95% of Q4_K_M tg128** under the canonical protocol **and** show a measurable task-eval win (paired per-item flips vs the reference; report PPL/KLD beside it as fidelity context only — a near-baseline KLD/PPL ordering is not a quality ordering, intake-1510, intake-1519#05). Slower than 95% ⇒ **DROP permanently** — 17.5% fewer bytes that decode slower is strictly dominated.
- NOTE: no `IQ*_KT` GGUF exists under `/mnt/raid0/llm`, and public KT producers (ubergarm, ik-community) cover giant MoEs we do not serve. Viterbi is the **encoding** cost only — at inference the trellis LCG runs forward — so self-quantising is hours on 192 cores plus an imatrix, not prohibitive, but not free.

#### Key files

- Worktree / branch: `/mnt/raid0/llm/llama.cpp-iqk-iquants`, `iqk/enable-iquants-v7-20260721` @ `f78ec18fe`
- Kernel: `ggml/src/ggml-cpu/iqk/iqk_gemm_iquants.cpp` (set_kernels `:2760-2775`, converters `:2810-2814`)
- Dispatch: `ggml/src/ggml-cpu/iqk/iqk_dispatch.cpp`
- Stubs: `ggml/src/ggml-cpu/iqk/iqk_stubs.cpp`
- GLM-5.2 tensor map: `/mnt/raid0/llm/tmp/gguf-inspect-20260721/`

#### Reporting instructions

Append build/bench artifacts and protocol ids here, update [tq3-quantization-evaluation.md](quantization-and-low-bit.md#track-tq3-quantization-evaluation) with the outcome, and flip B1-B5 / T1-T3 with `✅ YYYY-MM-DD`. All numbers are OBSERVATIONS under MEASUREMENT.md until produced by a codified recipe with operator approval.

---

#### Addendum 2026-07-21 — the 1-bit family, and why KT must be gated outside our tree

##### A. The stubbed 1-bit family (IQ1_M / IQ1_S) — folded in for the kernel session

`iqk_set_kernels_1bit` and `iqk_convert_1bit_q80_r8` are still `return false` stubs in
`iqk_stubs.cpp`, exactly like the IQ-quant pair was. The consequence today:

- **Hy3-IQ1_M-mtp** has **82 IQ1_M tensors** (`blk.*.ffn_gate.weight` and friends) that this
  change does **not** cover. Its other 157 IQ3_XXS/IQ2_XXS tensors do get accelerated by B1-B5,
  so Hy3 is partially fixed — the 1-bit remainder is the leftover.
- No other registry model currently carries IQ1_* tensors, so Hy3 is the sole beneficiary as of
  2026-07-21.

Whether this is as cheap as the IQ-quant un-stub is **unverified** and must be checked before it
is scheduled — the IQ-quant case was cheap for a specific reason (native enum values, kernel
already vendored), and that reason has to be re-established here rather than assumed:

- [x] **B6 — Scope the 1bit family.** ✅ 2026-07-29 static source audit at frozen
  `production-consolidated-v8` `67a433bf45a8a091d83b4ea0b32ff0735fd51800`: (a)
  `ggml-cpu/iqk/iqk_gemm_1bit.cpp` is vendored but omitted from the CPU CMake source list; (b) both
  architecture variants implement the native `IQ1_S` and `IQ1_M` cases in
  `iqk_set_kernels_1bit` and `iqk_convert_1bit_q80_r8` (the latter routes exactly those two types);
  (c) they are native `GGML_TYPE_IQ1_S=19` / `GGML_TYPE_IQ1_M=29`; and (d) their
  `block_iq1_s`/`block_iq1_m` plus core and CPU `type_traits` already exist. The source also carries
  ik-only `_R4`/BN paths, but `iqk_ext_types.h`/`iqk_ext_blocks.h` already provide their compile-only
  shims, so enabling the standard pair needs no enum, block-layout, or traits change. **Conclusion:
  clean same-shape candidate as B1-B5**; stage only on a fresh experimental branch and retain the
  normal build/correctness/measurement gates. No build, server, benchmark, or production-tree change
  was made by this audit.
- NOTE: the payoff is narrower than B1-B5 — one model, 82 tensors — so do not let it block B5.

##### B. Why the KT/trellis gate belongs in `ik_llama.cpp`, not our tree (operator question)

The premise of the question is right: we **did** fold ik_llama's work into our fork at v6, and
v7 carries it. But what was folded is the **iqk GEMM kernel subsystem** — the `mul_mat` dispatch
path gated by `GGML_IQK`. The **KT block types and their format plumbing were deliberately not
folded**, which is precisely what `iqk_stubs.cpp` documents.

Verified in our tree at `production-consolidated-v7 @ 6ad45fa3f`:

| capability | our tree | ik_llama.cpp |
|---|---|---|
| `IQ2_KT`/`IQ4_KT` in the public `ggml_type` enum (`ggml/include/ggml.h`) | **0 references** | present |
| KT rows in the `type_traits` table (`ggml/src/ggml.c`) | **0 references** | present |
| `llama-quantize` can *produce* a KT GGUF | **0 references** — no KT option | present |
| `GGML_TYPE_COUNT` | 43 (KT ids are 153-158) | extended |

So our binary can neither **produce** a KT GGUF nor **load** one. A KT tensor would index
`type_traits` out of bounds — the same OOB class commit `715383cde` already had to fix once.

That is the whole argument, and it is narrower than "use ik because it's better": **to answer
"is IQ4_KT worth 3-6 days of porting?" you must first create an IQ4_KT GGUF and read it back, and
only ik_llama.cpp can currently do either.** Using it as a *measurement instrument* to decide
whether to build the capability in our tree is not a second serving path and does not reopen the
deprecation — CLAUDE.md deprecates ik_llama as a **serving** binary, which this is not.

The alternative is legitimate and should be stated plainly: **do the port first and measure in our
own tree.** That is the cleaner end-state and avoids touching a deprecated tree at all. It simply
costs the 3-6 days up front on a question whose expected answer is unfavourable — IQ2_KT is
2.125 bpw against the 2.0625 bpw IQ2_XXS we already run (so *negative* bandwidth), and ik's own
author reports KT as slower for CPU token generation. Spending the port to find that out inverts
the usual order of cheap-test-then-build.

**Operator's call.** If the deprecated-tree usage is unwelcome, T2 should be replaced by "port on
`llama.cpp-experimental` and measure there", accepting the cost. Either way T1 (B1-B5) comes first
and is unaffected.


#### Laguna S 2.1 intake integration — 2026-07-22
_Via /research-intake Stage-2 (intake-880); see [laguna-s21-cpu-port.md](kernel-champion-and-promotion.md#track-laguna-s21-cpu-port)._
- [x] Add Laguna-S-2.1-UD-IQ2_M as the 5th beneficiary model to the B2/B3 gate list. ✅ 2026-07-25 — recorded and operator-scoped to GPU IQ2; it is not a B2 CPU IQK-on/off-tested model. Its routed-expert bulk is IQ2_XXS(51%)+IQ3_XXS(37%)+IQ2_S(1.4%) = the same set the committed `iqk/enable-iquants-v7-20260721` branch already accelerates (89.9% of the model); only 2 IQ4_XS tensors (2.3%) stay uncovered, the same remnant GLM-5.2/Qwen already carry — NO new kernel needed

---

#### 2026-07-25 v8 audit (Claude session, operator-requested) — residual defects + new tasks

Full 4-agent audit of the v8 carrying commits (`b8ad9d292`, `1977a5d78`). Verified against
measured GLM-5.2 UD-IQ2_M GGUF headers: the five native types cover **89.1% of bytes**
(IQ2_XXS 51.5% + IQ3_XXS 36.7% + IQ2_S 0.9%), IQ4_XS is 2.9% (4 MoE down-expert tensors),
Q2_K/Q3_K 1.5%, Q8_0 2.2%. Both GEMV and GEMM are enabled, dense + MoE, no batch gating;
runtime gating/fallback is clean (GGML_IQK=0 → zero overhead; non-AVX512 → functional #else
paths). Findings ordered by leverage:

- [x] **NEW-1 (perf, ~3 lines) — enable IQ4_XS dispatch.** ✅ 2026-07-25 — landed in `8890e2b14`; focused CPU/sanitizer evidence passed. A real compiled IQ4_XS kernel
  already exists (`iqk_gemm_kquants.cpp:2712-2714` via `DequantizerIQ4XS`, routed at
  `iqk_mul_mat.cpp:906-917`) but the type is excluded from `iqk_typeA_supported`, so it is
  never reached. The landed change adds it to the dispatch whitelist + `iqk_weight_uses_q8_k` + the
  `repack.cpp` parity list, closing the last 2.9% of GLM-5.2 bytes (and the IQ4_XS remnants on
  122B/Laguna) at near-zero risk. Same B2-style correctness gate applies. (IQ4_NL likewise
  exists unused — registry-irrelevant today, note only.)
- [x] **NEW-2 (perf waste, defect) — stop paying the Q2_K/Q3_K double penalty.** ✅ 2026-07-25 — landed in `8890e2b14`; focused CPU/sanitizer evidence passed. Before the fix,
  Q2_K/Q3_K remained in `iqk_typeA_supported` but could never pass `MulMat::prepare` → every such
  matmul under `GGML_IQK=1` paid the full cooperative Q8_2_X4 activation quantize +
  `ggml_barrier` (`iqk_dispatch.cpp:146-162`, MoE `:229-264`) and THEN falls back to native
  rerunning from scratch — pure per-call waste on GLM-5.2's blk.48/78 expert layers — while
  `repack.cpp:4544-4546` simultaneously withheld these tensors from CPU_REPACK. The landed
  change removes both types before activation quantization, restores v7 behavior, and fixes
  the stale header comment that claimed "Q8_K for Q2_K/Q3_K".
- [x] **NEW-3 (correctness risk, NDEBUG) — invalid-expert-ID OOB on the fallback path.** ✅ 2026-07-25 — landed in `8890e2b14`; focused CPU/sanitizer evidence passed. The
  iqk MoE hook zeroes/skips invalid expert ids (`iqk_dispatch.cpp:239-262`), but the native
  path that Q2_K/Q3_K experts fall back to only `assert()`s id validity (`ggml-cpu.c:1649`) —
  a no-op under NDEBUG, then an OOB row-mapping write. The invalid-id scenario is exactly what
  `test-iqk-ser` exists for; the fallback path was unprotected. The landed change adds an
  explicit NDEBUG-safe bounds guard that zeroes inactive invalid routes.
- [x] **NEW-4 (test gap) — close default CI's IQK corruption gap.** ✅ 2026-07-25 — landed in `8890e2b14`; focused CPU/sanitizer evidence passed. Before the fix, the
  new `test-backend-ops` IQ cases compare against a sound `use_ref` reference, but nothing in
  ctest exports `GGML_IQK=1`, so default runs exercise only native kernels; the only
  iqk-engaging default test is `test-iqk-ser` — a **structural** smoke (MUL_MAT_ID, IQ2_XXS
  only, one shape, no numerical comparison vs reference). The Hy3 corruption would pass
  default CI. The landed change adds a `GGML_IQK=1` ctest variant of the MUL_MAT/MUL_MAT_ID backend-ops
  cases for all 5 types + dense GEMV/GEMM shapes, and extends `test-iqk-ser` to numerically
  compare iqk-vs-control within NMSE tolerance.
- [x] **NEW-5 (Zen5 decode experiment, cheap) — GEMV inner loop is on the disfavored
  instruction.** ✅ 2026-07-25 — NO-GO: `160/216` focused evidence did not justify the change; source restored. `multiply_add_1` (`iqk_gemm_iquants.cpp:683-717`) selects the
  **VPDPBUSD** (`_mm256_dpbusd_epi32`) branch under HAVE_FANCY_SIMD on this host, while the
  **VPMADDUBSW** variant sits in the same function's `#else`. Prior Zen5 measurement
  (`project_zen5_vnni_vs_maddubs`) found VPMADDUBSW faster; the GEMM path already uses
  maddubs+VPDPWSSD. A/B the swap on the decode path (expectations modest — decode is BW-bound
  — but it is a compile-time toggle test). NOTE: this is moving OFF VNNI, i.e. NOT the killed
  "AVX-512VNNI vec_dot" ledger item.
- [ ] **NEW-6 (prefill headroom, post-v8 riders, one bundle):** (a) `func16` 16-wide kernels
  are `nullptr` for the plain IQ types (`iqk_gemm_iquants.cpp:2754`) — prefill capped at
  8-column micro-kernels; (b) the large-Ny `Q8_K_R16` convert-repack path is disabled in
  `is_dequant_better` (`iqk_mul_mat.cpp:246-254`) over an un-root-caused Zen4 correctness
  issue — root-cause it rather than leave ik's 16-wide prefill path off; (c) fused MoE
  up/gate exists (`iqk_mul_mat.cpp:811`) but no GGML hook calls it; (d) `iqk_flash_attn.cpp`
  is not in the build; (e) the IQ3_XXS `n_rows>=32` NMSE gate (`iqk_dispatch.cpp:88-93`) is an
  accuracy exclusion that was shape-gated, not root-caused — thin numerical margin by
  admission; (f) all kernels are 256-bit ymm — no zmm variant exists (Zen5 512-bit datapath +
  `k_x_step`/`IQK_MAX_NY` tiling inherited from ik's Zen4 tuning, unexamined). None of these
  gate v8 promotion; they are the next iqk perf tranche.
  - **Locator correction 2026-10-20 (factual, box text not rewritten):** the NEW-6(b) gate site is `iqk_mul_mat.cpp:297-306 @ffc1bac82` (IQ2_XXS/IQ2_XS/IQ2_S/IQ3_XXS/IQ3_S return `type` unchanged in `is_dequant_better`). The `:246-254` locator in (b) is stale: that range is the dispatch loop.
  - **NEW-6(b) evidence correction 2026-11-02:** the blanket “un-root-caused” wording above is stale for IQ4_XS: the INF-70 node trace identified gross errors in its IQ4_XS → Q8_K_R16 repack at `nrc_y >= 32 && npt >= 16`, and `99425578d` excluded IQ4_XS; the later C9 stale-binary investigation confirmed that exclusion was absent from the binary under test. See `progress/2026-09/2026-09-03-inf70-audit.md` sections “P0 ROOT-CAUSED” and “C9 ROOT CAUSE”. Production `ffc1bac82` also excludes the five IQ2/IQ3 types, but that IQ4_XS finding alone does not establish a per-type cause or justify enabling their paths. Trace each converter, repacked layout and consumer against the reference and existing tests before designing qualification; NEW-6 remains open. [belief: cc]
- [x] **NEW-7 (evidence hygiene, do before container restart):** ✅ 2026-07-25 — durable
  exact-tip CPU/HIP/sanitizer CTest evidence is under
  `epyc-inference-research/data/kernel-v8-candidate/{exact-tip-build,final-focused,sanitize-final}/`;
  paired thread-safety and quant-selection evidence is under
  `data/kernel-v8-candidate/pre-final-audit-evidence/run-20260725T0945Z/paired-thread-quant/`.
  The post-`6c44557bf` thread-safety rerun passed. Historical HIP was `56/59`, all 3 failures
  classified baseline with paired differentials; exact-tip HIP is `59/62` with the same three
  failure classes, not green.

#### Research intake 2026-10-21 — open-model backdoors, control-vector projection, Qwen3.8 post-train (research intake entries 2191–2213, see research/intake_index.yaml)

- [x] **NEW-11 — iqk coverage table for the ISTA-DASLab GSQ-RCO Q38FN builds (text only, no weights).** From the four published tensor-allocation files, compute per build the byte-weighted share of routed-expert bytes on iqk-accelerated types versus native fallback types (Q2_0, IQ4_NL, IQ1_M) before any download decision (intake-2206#01). ✅ 2026-10-21: table in epyc-inference-research `artifacts/intake-backdoor-cvec-20261021/NEW-11-gsq-rco-iqk-coverage.md` (c5661c5f9 lineage, cd9b3cfa6). Routed-expert non-iqk (decode/prefill): Q2_0 100/100%, IQ2_XS 35/35%, IQ3_XXS 36/45%, IQ3_S 41/62%; recommend IQ3_XXS first, skip Q2_0, IQ3_S conditional; download call stays operator's.
  - IQ3_S conditional resolved 2026-10-22 (workspace-58): **not pulled.** IQ3_XXS cleared the load smoke but failed PPL/KLD (NEW-10 verdict FAIL), so this table's IQ3_S condition is not met.
- [x] **NEW-10 — GSQ-RCO arm for Q38FN versus served UD-IQ4_XS.** After NEW-11 and an operator disk/download call, pull IQ3_XXS and IQ3_S from ISTA-DASLab at sha ed59f920 (not the community relay); v10 load smoke, then PPL plus mean KLD and same-top-1 against one shared reference, then coherence at production prompt length; only on a pass, the serving-shape bench; record which layers fall back to non-iqk types; the card's --lazy-mode flag does not exist in v10 (intake-2206#04). ✅ 2026-10-22 — DONE, verdict **FAIL** (G1-G3 miss the strict predeclared bars); the GSQ IQ3_XXS arm is closed for serving and IQ3_S is not pulled. Verdict block below.
  - Operator disk/download call made 2026-10-22: IQ3_XXS first (~65 GB); IQ3_S only if needed. The download is booked by workspace-58 (calendar owner).
  - 2026-10-22 (workspace-58): **download started, quality row armed, pass rule pinned.** Not ticked.
    - Download: the true size is **75.84 GB**, not ~65 GB. Shard 1 is 47.04 GB (sha `219ea929…`) and shard 2 is 28.80 GB (`per_layer_token_embd`, sha `316b46f3…`, identical across all four builds). It goes to `/mnt/raid0/llm/models/ISTA-DASLab/Qwen3.8-Flash-Next-GSQ-RCO-GGUF/IQ3_XXS/` and is pinned to `ed59f920`; the repo is public and ungated, so no token is used. Free space after: ~530 GB, above the 200 GB floor.
    - The download is one sequential job, `/mnt/raid0/llm/tmp/new10-q38fn-20261022/dl/download_iq3xxs_v2.sh` (PID 2076182, started 14:28:24Z, ~10 MB/s, ETA ~16:35Z). It writes the end flag `/mnt/raid0/llm/tmp/compute-flags/NEW10_IQ3XXS_DL_ENDED` (`rc`, `time`, `bytes`, `sha`) and checks sha256 against the HF API `lfs.oid`. v1 had a 404 URL (the `IQ3_XXS/` subfolder was missing); main killed it with operator approval.
    - Quality row: FILLERS `new10-q38fn-iqxxs-quality` is ARMED (owner workspace-58, block-correctness, CPU, one quarter, about 50 min estimated, 30 min minimum window, peak host RAM 168 GiB). Launcher: `filler_run7.sh --repeat`. The job script is `/mnt/raid0/llm/tmp/new10-q38fn-20261022/job/new10_quality_job.sh`.
    - The job first runs its precondition (download rc=0 and sha OK, else rc=5), then `ram_admit 168`. The steps after that: v10 store load smoke, then llama-perplexity UD-IQ4_XS on wiki.test.raw (c512, b512, 40 chunks, the EXL3-6c5 Q38FN recipe) with `--kl-divergence-base` as the ONE shared reference. Next, GSQ `--kl-divergence`, then coherence_gate on 5 greedy prompts (two of at least 4096 prompt tokens, plus 40/90/250-token prose). It ends with the per-layer non-iqk fallback list. The header predicts 96 native tensors (58 IQ4_NL, 38 Q2_0) and 12 decode-only IQ3_XXS tensors across all 48 layers.
    - Pass rule, pinned before any run: `/mnt/raid0/llm/tmp/new10-q38fn-20261022/job/PREDECLARED.json`, sha256 `1a5e5ca94146bf14aab0eb1cd30100ba230015ef5e8ac9c37e29aef8ca60a81b`. Every bar is required:
      - G1: mean ln(PPL(Q)/PPL(base)) ≤ 0.005, one-sided (the 2026-10-06 low-bit contract).
      - G2: mean KLD ≤ 0.1045. This is the survey rule "≤ 1.25 × UD's", times UD's published 0.0836.
      - G3: same-top-1 ≥ 88.55%, from the "within 1 pp" rule applied to UD's published 89.55%.
      - G4: zero coherence regressions.
      - G2 and G3 are TRANSLATIONS of reference-based gates onto a UD base, because no high-precision Q38FN base is on disk.
    - PASS authorises only the serving-shape speed bench. FAIL closes the arm, and IQ3_S is not pulled. Adoption still needs the paired task eval as sized by NEW-14 (landed 223b0e298): a 2 pp margin, required N from `degradation_stats.py size`, and the one-sided exact verdict. NEW-14 landed after the pin, so it is recorded in a non-rule addendum, `job/PREDECLARED.ADDENDUM-NEW14.md` (sha `e4f33abb…`); the bars are unchanged.
    - Belief kernel: the job writes `out/quantcmp_receipt.json` (`epyc.quantcmp.receipt.v0`) for the VB-QUANTCMP-WIRE adapter.
    - The card's `--lazy-mode` flag is not used.
  - 2026-10-22 evening (workspace-58): **strict bars kept, download done, first quality run aborted at its smoke step and root-caused.** NEW-10 stays open.
    - Operator ruling: keep the strict predeclared bars (`job/PREDECLARED.ADDENDUM-OPERATOR-BARS.md`); `PREDECLARED.json` sha `1a5e5ca9…` unchanged.
    - [x] IQ3_XXS download: ENDED rc=0 sha=OK at 16:27:55Z, 75.84 GB, both shards verified against the HF lfs oids (`/mnt/raid0/llm/tmp/compute-flags/NEW10_IQ3XXS_DL_ENDED`). ✅ 2026-10-22
    - First run `new10-q38fn-iqxxs-quality` FAILED rc=19 at the smoke step, 19:36Z (granted q3 19:30Z): the production CPU `llama-completion` aborted with SIGABRT "double free or corruption (out)" after a NaN on the first fused decode token. Log `/mnt/raid0/llm/tmp/new10-q38fn-20261022/out/smoke.log`. No quality number was produced.
    - Root cause (subagent, RCA notes `/mnt/raid0/llm/tmp/new10-ple-rca-20261022/`): not the PLE tensor type. GSQ stores `blk.*.ffn_down_shexp` as IQ4_NL (UD uses Q8_0); under `GGML_IQK=1` CPU_REPACK interleaves it (`iq4_nl_8x8`), and v10's fused single-token decode (`qwen4exp-fused.cpp` `lora_mm`) ignores the repack, so layer 0 goes NaN → layer-1 router all-NaN, `best=-1` → `probs[-1]=-INF` heap write → glibc abort. Same chain as FD-DIV-1 (`cpu-fused-decoder-blocks.md`).
    - The job's actual defect: it ran without the registered Q38FN serving env `GGML_FUSED_DECODE_OFF=1` (`model_registry.yaml`). Added to `CPU_ENV` for both arms; addendum `job/PREDECLARED.ADDENDUM-FUSED-OFF.md`, sha256 `e4aade94e31be3764d35cc1998581c72b096250ebd0a53e5bac9ad3893a04a26`. Bars unchanged; G1-G3 perplexity never enters the fused path.
    - [x] **NEW-10 quality re-run with the serving env (`GGML_FUSED_DECODE_OFF=1`).** Booked tonight on q3 after `dhm-mining-full` (writer `grant-night-q3-20261022.sh` v2, 90 min grant, cap 02:30Z). Done when `out/` holds the G1-G4 verdict against the unchanged `PREDECLARED.json` and the `quantcmp_receipt.json`; on PASS book the serving-shape bench (with the fused path off, as served), on FAIL close the arm. (filed 2026-10-22, workspace-58)
      ✅ 2026-10-22 — ran on q3 (re-placed by the q3 writer), COMPLETE 20:23:33Z; verdict FAIL, arm closed.
  - 2026-10-22 late evening (workspace-58): **NEW-10 verdict FAIL — the GSQ IQ3_XXS arm is closed for serving.** Source: `/mnt/raid0/llm/tmp/new10-q38fn-20261022/out/VERDICT.md` and `RESULT.json`, against the unchanged `PREDECLARED.json` (sha `1a5e5ca9…`) plus `PREDECLARED.ADDENDUM-FUSED-OFF.md` (sha `e4aade94…`, run with `GGML_FUSED_DECODE_OFF=1`). Production v10 CPU store binaries (`10303`, `cpu-20260921-ffc1bac82`); one shared logits base from the served UD-IQ4_XS; wiki.test.raw c512/b512/40 chunks.
    | Gate | Value | Bar | Result |
    |---|---|---|---|
    | G0 load smoke | rc 0, non-empty, all finite | — | PASS |
    | G1 mean ln(PPL(Q)/PPL(base)) | 0.0150 ± 0.0100 | ≤ 0.005 | FAIL |
    | G2 mean KLD (nats/token) | 0.322 ± 0.007 | ≤ 0.1045 | FAIL |
    | G3 same-top-1 | 82.9% ± 0.4 | ≥ 88.55% | FAIL |
    | G4 coherence | 0 regressions, 4 needs_review, 1 identical | 0 regressions | gate INCOMPLETE (passes the bar's letter; not eyeballed) |
    - PPL (descriptive, lower = better): UD-IQ4_XS 2.9925 ± 0.063 (base run), GSQ IQ3_XXS 3.0346 ± 0.062. Median KLD 0.062, max 9.73: the mean is carried by a heavy tail.
    - Fallback census: 96 native (non-iqk) tensors and 12 decode-only iqk IQ3_XXS tensors, as the header predicted (`out/fallback_layers.json`).
    - Consequences: no serving-shape speed bench; the NEW-14 paired task gate is not run (moot on FAIL); **IQ3_S is not pulled** by the predeclared rule (NEW-11: IQ3_S only if IQ3_XXS clears the load smoke and PPL/KLD). The four G4 needs_review texts under `out/coh/` are not eyeballed: declined, because G1-G3 already close the arm and no decision reads G4.
    - Weights: the operator ruled (2026-10-22 ~20:5xZ) KEEP the 75.8 GB IQ3_XXS weights until NEW-13 runs, then delete them (task under NEW-13).
    - Belief kernel: `out/quantcmp_receipt.json` is a job-written `epyc.quantcmp.receipt.v0` and is **refused** by the VB-QUANTCMP-WIRE strict reader (`qwen4exp_quality_reader.read_project` → `ValueError: unsupported receipt schema`, checked at this wrap-up). Capture task VB-QUANTCMP-NEW10 is filed in `vidya-belief-substrate-program.md`; it must run before the weights are deleted.

- Trigger (no checkbox): the GSQ code release adds a GGUF IQ-type or Q2_0 export path or a Qwen3.8-Flash-Next recipe. Then assess self-quantising with it (the paper's GGUF evidence covers K-quants only, intake-2207#01).

#### Research intake 2026-10-22 — SLQ / IST-DASLab / kaitchup Qwen3.8-27B SLQ (intake-2461..2493)

Source: research intake session intake-ist-slq-20261022, Stage-3 plan `/mnt/raid0/llm/tmp/intake-ist-slq-20261022/stage3/STAGE3_PLAN.md` (sha256 db108374cd1bd164e5baaac2586b9d3abf26daaba46aec4085192e4b0c0232ad); operator ruling 2026-10-22 approved a subset. Trigger prose and knowledge notes from that plan are still pending the operator and are not filed here.

- [x] **NEW-13 — Zero-training prefill/decode weight-set handoff probe on CPU for Q38FN (intake-2467, intake-2485).** (filed 2026-10-22 via research intake, operator-approved 2026-10-22; after NEW-10's IQ3_XXS download) On a fresh llama.cpp-experimental branch, a tools/ harness prefills in one llama_context with the served UD-IQ4_XS (P), copies the sequence state (llama_state_seq_get_data/set_data: KV plus recurrent state) into a second context holding the GSQ-RCO IQ3_XXS (D), then teacher-forces a 256-token held-out continuation and records per-token KLD against one shared reference. Arms: A D-only, B P->D, C P-only, D reverse (D prefill, P decode). N = 120 passages of 2048 + 256 tokens, paired bootstrap 95% CI, R = (KLD_A - KLD_B)/KLD_A. Gate 0: KLD_A - KLD_C < 0.005 nats means uninformative, stop. PASS: R >= 0.25 with CI lower bound > 0.10 and coherence OK; FAIL: R < 0.10 or CI spans 0, record refuted and close. PMPD only tested nested quantizations, so a FAIL at independent quants does not refute PMPD. Compute (estimates): correctness class, region-lock --cpu-list 0-95, one process, RAM = both GGUFs mmap'd, 2-4 h plus about 1 h for arm D.
  - 2026-10-22 late evening (workspace-58): harness **in progress** — another workspace-58 subagent is building it on `experimental/new13-weight-handoff-20261022` (no runs yet). BACKLOG until armed, then booked on the 10-23 calendar (0-95, correctness, 2-4 h + ~1 h for arm D). NEW-10's FAIL does not cancel NEW-13: the probe asks whether a P prefill rescues D's decode, and a weak D is the case it tests.
  - ✅ 2026-10-23 — **COMPLETE 13:52Z, verdict PASS** (workspace-58). Harness `experimental/new13-weight-handoff-20261022` @ `6b3ac87fe` (tools/ only); rule `job/PREDECLARED.json` sha `c27090ff…` (unchanged); reference **P** chosen by the operator 06:32Z (served UD-IQ4_XS = arm C; `job/REFERENCE.json`, read-only). Ran on 0-95 in two grants (10:05-11:17Z, 46/120 passages, then 12:14-13:52Z). Source: `/mnt/raid0/llm/tmp/new13-weight-handoff-20261022/out/VERDICT.md` (sha `a505a3a0…`) and `RESULT.json` (sha `b3811466…`).
    | Gate | Value | Bar | Result |
    |---|---|---|---|
    | Gate 0 informative | KLD_A − KLD_C = 0.213 [0.197, 0.233] nats | ≥ 0.005 | informative |
    | R = (KLD_A − KLD_B)/KLD_A | 0.2828, paired bootstrap 95% CI [0.2458, 0.3219] | R ≥ 0.25 and CI_low > 0.10 | PASS |
    | Coherence (B vs C) | 0 regressions, 4 needs_review, long prompts ≥ 4096 | 0 regressions | OK |
    - Mean KLD (nats/token, 120 passages × 256 tokens, lower = better): A (GSQ IQ3_XXS only) 0.213, B (UD prefill → GSQ decode) 0.153, C (UD only) 0, D (GSQ prefill → UD decode) 0.101; reverse R_rev = 0.525 [0.485, 0.563]. Same-top-1 vs C: A 84.2%, B 85.9%, D 90.0%. Self-test state round trips ~1.1e-7.
    - **Speed caveat (descriptive only, not gated).** Teacher-force tok/s: A 15.9, B 15.8, C 21.9, D 22.6; prefill P 236.5, D 203.3. The GSQ IQ3_XXS decode is ~27% slower than UD-IQ4_XS on this CPU (15.9 vs 21.9), so B's quality recovery buys no speed: a P→D handoff is slower than serving P alone. The PASS shows that a high-bit prefill state transfers into a low-bit decoder, not that the handoff is a serving win.
    - Per the predeclared PASS branch: open C-L3, no kernel work yet (below). Derived, declined (not filed): the C-L4 ODP-port trigger (Stage-3 plan `intake-ist-slq-20261022` C-L4 needs ≥ 25% KLD-gap recovery AND a capacity or speed case). The recovery leg is met (R 0.28), but there is no speed case (decode −27%) and no capacity case is stated, so it is not triggered. The 4 coherence needs_review texts (`out/coh/`) are not eyeballed: the gate passes on 0 regressions and no decision reads them.
    - Belief kernel: `out/handoff_receipt.json` is a hand-written `epyc.new13.receipt.v0` that no strict reader accepts. Filed VB-NEW13-WIRE in `vidya-belief-substrate-program.md`.
  - [x] **C-L3 — NEW-13 follow-on: the same P→D handoff on a low-bit (IQ2_XXS-class) dense pair of an already-served 27B-class model, with ppl/coherence at production prompt length (opened by NEW-13's predeclared PASS branch, 2026-10-23; Stage-3 plan `intake-ist-slq-20261022` C-L3, intake-2467).** It calibrates against the paper's untrained-prefill reference (27B IQ2_XXS: MMLU-Pro 70.50 weight-only vs 76.06 with an RTN-NVFP4 prefill) and checks DFlash2 acceptance with P-produced hidden states. No kernel work yet. **Carry NEW-13's speed caveat**: on Q38FN the low-bit decoder was ~27% slower than the served quant, so C-L3 must report decode tok/s beside KLD, and must state a capacity or speed case before anything is built on it. Gate: an operator disk/download call for the IQ2_XXS GGUF (Stage-3 plan). Done when the predeclared KLD/coherence verdict and the descriptive speed table are recorded here. (filed 2026-10-23, workspace-58 wrap-up) ✅ 2026-10-23 **CLOSED SUPERSEDED, not completed** (operator 2026-10-23: the 27B IQ2 pair is dropped, and the live follow-on is C-L3-Q38FN below).
    - *Re-scoped 2026-10-23 (operator): "27B runs on Q8 on the GPU. We don't need to explore IQ2 there (except maybe to study kernel optimisation for those quants). Q38FN kernels are much more important to run in lower quants, if quality can be kept comparable and speed increased."* So C-L3's 27B IQ2_XXS pair is DROPPED. The live follow-on is C-L3-Q38FN below; the GSQ IQ3_XXS weights are kept for it.
  - [ ] **C-L3-Q38FN — make Q38FN low-bit decode faster than the served UD-IQ4_XS at comparable quality (operator 2026-10-23).** Evidence: NEW-13 PASS (UD prefill → GSQ IQ3_XXS decode recovers 28% of the KLD gap, R 0.28 [0.25,0.32]), but GSQ IQ3_XXS teacher-forced decode is ~28% SLOWER (15.8-15.9 vs 21.9-22.6 tok/s on 0-95). Step 1 (no compute): profile why. Is IQ3_XXS on an iqk fast path for these shapes? NEW-10 recorded 12 decode-only iqk fallback tensors; Q2_0 ffn_down_exps also matter. Step 2: an experimental kernel branch (AutoKernel low-bit lane) targeting IQ3_XXS/Q2_0 decode on CPU. Step 3: re-run NEW-13 arm B speed + a quality gate vs UD at production prompt length. Weights: /mnt/raid0/llm/models/ISTA-DASLab/Qwen3.8-Flash-Next-GSQ-RCO-GGUF/IQ3_XXS/ (kept).
    - *(2026-10-29, NI existing-artifact profile.)* NEW-13's one-token teacher-forced log `/mnt/raid0/llm/tmp/new13-weight-handoff-20261022/out/kld.log` (SHA-256 `a4405424a2c8aa7015adb64a629465e7320d998717b7ba64943057acf5d2b212`) records IQK MoE engagement for IQ3_XXS weights with Q8_K activation. Frozen v10 dispatch allows that path for one token and routes wider calls to the NMSE-guarded native fallback; NEW-10's type census records 38 Q2_0 and 58 IQ4_NL native tensors alongside 12 decode-only IQ3_XXS IQK tensors. This confirms path participation, not the cause or share of the approximately 27% lower throughput: no per-kernel timings were captured. The causal profile and speed/quality objective remain open; completed arm-P/P2 probes were not rerun. Profile detail `/mnt/raid0/llm/tmp/codex-ni-inf26-cl3-step1-profile-20261029/PROFILE.md` (SHA-256 `21be5260215bc075b78b26ca4b734b14cfc46c855373edd29b4fd08729ffb583`). [belief: cc]
    - [x] **C-L3-Q38FN-PROFILE-PREP-01a16fc3:** prepared and sent the diagnostic profile packet at NEXT priority; source-bound preflight `fbbb711cf768de5b0ad9361a27fa9cd1d5a9075818de4da3` and model-free perf-window and cleanup fixtures passed. The one-repetition synthetic decode comparison uses 48 threads, CPUs 0–95 and exclusive GPU quiet; requested 3600 s (minimum 1800), 200 GiB RAM plus 64 GiB admission margin. Receipt `bfac3cd3-2605-4df3-9095-cd66e7225c21` proves transport only: consumption, arming and execution unconfirmed. This does not reproduce the historical teacher-forced slowdown; parent remains open. Packet `/mnt/raid0/llm/tmp/refactor-01a16fc3/cl3-q38fn-next-profile-ready/READINESS.md`. ✅ 2026-10-27 [no-belief: tooling preparation]
    - [x] **C-L3-Q38FN arm P — UD with ONLY ffn_gate/up_exps IQ3_S→IQ4_XS, every other tensor at its UD type (filed + started 2026-10-24, workspace-58; operator: "check cheap PPL first").** Survey: UD keeps attn/ssm/shexp/hc at Q8_0, down_exps IQ4_NL/Q8_0, output Q6_K, gate/up mostly IQ3_S, so the old uniform file's +17.8% PPL came from degrading the Q8_0 tensors. Arm P is 96970 MiB vs 89332. v1 (09:21Z): PPL P 2.9701 vs UD 2.9761 (both without GGML_IQK, recorded as a sidecar); coherence VOID (harness ran without the serving env, so the fused decode default-ON made even UD garbage, see FD-DIV-2). v2/P2 re-run (recipe env, llama-server chat) COMPLETED 2026-10-25 and the speed A/B (pp256 >= +27%, pp5 >= +19%, tg128 >= -2.0%, INDICATIVE on one quarter) COMPLETED: **P2 PPL 2.979 (lower better, bar <= 3.10) vs paired UD 2.9868; UD control and P2 coherence PASS (p1 Paris in first 120 chars; P2 outputs 448/463 chars, common prefix 236 >= 40); speed INDICATIVE FAIL: pp256 +31.91% (pass), pp5 -6.12% (fail), tg128 -8.85% (fail) => P2 does NOT ship, no kernel-wide performance claim.** This ticks the arm-P/P2 probe (harness repair + speed half) ONLY; the parent **C-L3-Q38FN stays OPEN** (faster low-bit decode at comparable quality is not achieved) and the other INF-26 tasks are untouched. MAIN acceptance: `/mnt/raid0/llm/tmp/codex-ni-20261025-coordination/inf26-armp-MAIN-ACCEPTED.md` (audit packet sha 156b8f22..., addendum e8fe5f82...). Do not rerun the completed probes. Jobs: `/mnt/raid0/llm/tmp/ws58-q38fn-armP-20261024/`, `/mnt/raid0/llm/tmp/ws58-q38fn-armP2-20261024/`, `/mnt/raid0/llm/tmp/ws58-q38fn-armP2-speed-20261024/`. ✅ 2026-10-25 (filed 2026-10-27, workspace-58 wrap) [no-belief: probe closure on a completed INDICATIVE run; no run ClaimTuple is minted retroactively, and the cc register row is added only after this commit exists]
      - *(2026-10-27, workspace-58.)* Evidence: arm P2 recipe preserved at `docs/reference/agent-config/recipes/q38fn-armP2-20261024/` (job.sh, pins.txt, genpins.py, launcher.cmd, VERDICT.md); 101 GB GGUF `q38fn-armP2.gguf` reclaimed 2026-10-27 (no-ship); rebuild from recipe.
  - [x] **NEW-13-RM — delete the GSQ-RCO IQ3_XXS weights once NEW-13 has run (operator ruling 2026-10-22: keep until NEW-13 runs, then delete).** Path `/mnt/raid0/llm/models/ISTA-DASLab/Qwen3.8-Flash-Next-GSQ-RCO-GGUF/IQ3_XXS/` (75.84 GB, 2 shards). Order: NEW-13 arms A-D done and recorded, and VB-QUANTCMP-NEW10 captured (it needs these weights), then delete with operator-confirmed `scripts/safety/guarded_rm.sh`. Delete NEW-10's 5.07 GB logits base `/mnt/raid0/llm/tmp/new10-q38fn-20261022/out/ud_iq4xs.kldbase` in the same step unless NEW-13 reuses it; keep `VERDICT.md`, `RESULT.json` and the receipts. Done when both are gone and the deletion is recorded here. (filed 2026-10-22, workspace-58 wrap-up) **Decided 2026-10-23 (operator): KEEP the GSQ weights — not deleted (C-L3 scope to be settled); ✅ 2026-10-23.**
    - *(2026-10-23 14:0xZ, workspace-58 wrap-up.)* Both preconditions are now met: NEW-13 COMPLETE (PASS, above), and VB-QUANTCMP-NEW10 captured AND ingested into the ledger (13:55Z, `vidya-belief-substrate-program.md`). **Pending operator: keep the weights for C-L3, or delete them now** (operator-queue row OP-NEW13-RM). Premise check for that decision: the Stage-3 plan scopes C-L3 to a 27B-class IQ2_XXS dense pair, not to these Q38FN weights, so keeping them only helps if C-L3 is re-scoped to re-use Q38FN GSQ. NEW-13 does not reuse NEW-10's `ud_iq4xs.kldbase`. The VB recapture's `out/vb-capture/base-a1.kldbase` was written by the capture and is another logits base, so delete it in the same step.
- [x] **NEW-14 — Size the NEW-10 and T2 (and NEW-12, if it is ever un-held) paired task gates before they run (intake-2483#record, intake-2484).** (filed 2026-10-22 via research intake, operator-approved 2026-10-22) Replace 'a paired per-item task eval no worse than UD' with a declared margin (default 2 pp) and an item count read from the paired-TOST tables of arXiv 2608.15046, or report the margin the available n supports; add the one-sided exact degradation verdict from EV-DEGR1 beside the two-sided P-PAIRED verdict, printing n_discordant and direction.

  *NEW-14 note 2026-10-22 (workspace-58).* Helper: `scripts/autopilot/degradation_stats.py` in epyc-orchestrator (commit 0993affc; tests `tests/unit/test_degradation_stats.py`). `python -m scripts.autopilot.degradation_stats verdict --b B --c C` prints n_discordant, direction (b = baseline correct/candidate wrong vs c) and the one-sided exact p (scipy binomtest, alternative=greater); `size --p-flip P [--n N] [--margin 0.02]` prints required N, power at N and the margin N supports. Required N = ceil(p_flip*(2.486/delta)^2), one-sided alpha 0.05, 80% power (intake-2484#02; our arithmetic from the paper's SNR relation, no N table is in the paper). The 'no worse than UD' criterion is replaced by: declared margin 2 pp (default). The exact one-sided verdict tests H0 'no degradation', not equivalence within the margin, so it is printed beside the two-sided P-PAIRED verdict and the gate additionally states required N for the margin; report `margin_supported_by_n` when N falls short). For reference the dive's reading of arXiv 2608.15046 Table 1 puts pooled churn-based need near 1.9k paired items for 2 pp (stage-3 ledger A-L7); our own arithmetic gives the grid below. The paper's TOST tables themselves were not re-derived here.
| p_flip (grid, not an estimate) | delta 1 pp | 2 pp | 3 pp | 5 pp |
|---|---|---|---|---|
| 5% | 3091 | 773 | 344 | 124 |
| 10% | 6181 | 1546 | 687 | 248 |
| 15% | 9271 | 2318 | 1031 | 371 |
| 20% | 12361 | 3091 | 1374 | 495 |
  Per-gate inputs (all blanks; none invented): **NEW-10** (Q38FN IQ3_XXS/IQ3_S vs served UD-IQ4_XS) N = ____ (task-bank paired items), p_flip = ____ (measure: UD-IQ4_XS vs UD-IQ4_XS rerun on the bank, greedy); **NEW-13** has no task gate (KLD bootstrap, N=120 passages) - out of scope; **T2** (IQ4_KT vs Q4_K_M, IQ2_KT vs IQ2_XXS in ik scratch) N = ____, p_flip = ____ (measure: Q4_K_M and IQ2_XXS self-rerun flip floors). NEW-12 is HELD; if un-held, size it the same way. At 2 pp the gate needs 773-3091 items for p_flip 5-20%; a 250-item bank supports only ~3.5-7 pp.

- *NEW-12 — HELD (operator 2026-10-22: "stick to NEW-10 and then we reassess later"); no checkbox, no compute booked.* Q38FN allocation transplant plus bytes-budgeted per-tensor type allocator from the Stage-3 plan (intake-2470#record, intake-2466#record, intake-2487#record). Reassess after NEW-10's IQ3_XXS quality result. If it is ever run, use the lean form: one candidate at a time, no P0 ISTA GSQ-weights comparison, ~190 GB disk peak, and delete the Q8_0 source at the end.

## Track: tq3-quantization-evaluation
<!-- gate: none -->

> Folded from `handoffs/active/tq3-quantization-evaluation.md` @ `6a4026f0ab50` on 2026-11-02 (BRF-T1-F5, route 1a, operator D1/D5; retired row INF-54 → INF-80). Body moved verbatim, headings demoted two levels to nest under this track; every open and closed box kept its text and ID.

### TQ3 / TurboQuant Quantization — Monitor List

**Status**: monitoring / stop-list active for current sub-2-bit candidate reruns (do NOT merge TQ3_1S — see rationale below)
**Created**: 2026-04-01 (via research intake)
**Updated**: 2026-08-21 (July steering supersedes the old broad speed-probe loop; PR #21089 monitoring CLOSED — the PR was closed unmerged upstream 2026-06-02)
**Categories**: quantization, hardware_optimization

> **⚠ STEERING (2026-07-19) — deprioritize the sub-2-bit breadth probes.** Bonsai-8B/27B `Q1_0`,
> Ternary `Q2_g64`, and Ternary `Q2_0` were probed on experimental-v7 and are **speed-only,
> quality-blocked or broken-load** (Q1_0 6/8 instruction-format; Q2_g64 6/8 + empty `<think>`;
> Q2_0 won't load — 498/498 tensors short, noncanonical packing). **Do NOT keep running speed
> reruns on these.** Reopen ONLY on a *specific* quality path: a producer/transcode fix for the
> Q2_0 layout, or a prompt/template fix with a hypothesis for the instruction-format miss. Full
> results + verdicts: [`../../docs/reference/model-probe-scoreboard.md`](../../docs/reference/model-probe-scoreboard.md).
> Freed cycles → operator-gated v7 promotion work (OP-2 / P-GPU-1 / AXA-2 / GLM accept-control).

#### Status as of 2026-04-21

Backburner monitoring. PR #21038 remains merged and auto-enabled in production v3 (confirmed 2026-04-17). PR #21089 (TBQ3_0/TBQ4_0 CPU KV cache kernels) **was CLOSED UNMERGED upstream on 2026-06-02** — re-verified against the GitHub API 2026-08-21: `state closed`, `merged false`, `merged_at null`, last update 2026-06-03. This line previously read "still open — no movement since last review", contradicting the verified 2026-07-29 finding at the checklist item below; the stale claim is corrected rather than carried forward. ChunkKV proposal unchanged. TQ3_1S rejection stands (immaturity + wrong target; see rationale below). Next revisit: only on a NEW upstream PR or a merged successor — there is nothing left to monitor on #21089.

#### Why NOT to Merge TQ3_1S

1. **Immature**: 3 commits, 1 contributor, no peer review, no CPU kernels, undocumented conversion tool
2. **Wrong target**: Only benchmarked on Qwen3.5-27B vs Q4_0. No Q4_K_M comparison. No Qwen2.5 tests. Author warns smaller models are "much less forgiving"
3. **We don't need VRAM savings**: Our EPYC 9655 setup has ample RAM/VRAM. Q4_K_M fits comfortably. Bottleneck is throughput, not capacity
4. **Upstream going different direction**: ggerganov himself is working on Hadamard rotation for existing quant types (PR #21038) — no new types needed
5. **MoE risk**: WHT rotation creates ~367K ghost activations per forward pass, shattering sparse routing. Not applicable to dense Qwen2.5-Coder-32B but relevant for Qwen3.5 hybrid

#### What to Monitor Instead (High Priority)

##### PR #21038 — ggerganov's Hadamard Rotation ✅ LANDED
- **What**: Applies WHT rotation to ALL existing KV cache quant types (Q4_0, Q5_0, Q8_0 etc.)
- **Impact**: Q4_0 KV cache PPL improves 25-77% on small models. Q8_0 with rotation matches FP16 on reasoning benchmarks
- **Why it matters**: Free quality improvement — no model re-quantization needed, just rebuild llama.cpp
- **Status**: ✅ MERGED upstream as commit `744c0c731` (2026-04-01). Auto-enables in `production-consolidated-v3` when KV types are quantized. `--kv-hadamard` flag removed from orchestrator config (was our prior custom WHT impl, now redundant).
- **URL**: https://github.com/ggml-org/llama.cpp/pull/21038

##### PR #21089 — CPU TurboQuant KV Cache (TBQ3_0/TBQ4_0)
- **What**: 3-bit and 4-bit KV cache quantization with CPU kernels
- **Impact**: 5.2x KV cache compression with minimal PPL loss. Extends effective context length
- **Status**: CLOSED UNMERGED upstream 2026-06-02 (GitHub PR metadata checked 2026-07-29); no TBQ code entered the local production tree.
- **URL**: https://github.com/ggml-org/llama.cpp/pull/21089

##### ChunkKV (arXiv:2502.00299) — Training-Free KV Compression
- **What**: Chunk-level KV cache compression preserving semantic structure. No retraining required
- **Impact**: Retains 12% of KV cache matching full cache quality. 26.5% throughput improvement via layer-wise index reuse
- **Why it matters**: Works on existing pretrained models — directly applicable to our stack
- **URL**: https://arxiv.org/abs/2502.00299

###### 2026-07-29 feasibility assessment

**Disposition: technically implementable as an experimental llama.cpp candidate; do not treat it as
an existing-server toggle or a production patch.** ChunkKV selects complete contiguous chunks from
the observed-query attention matrix, retains a recent observe window, and reuses selected indices
across adjacent layers. The paper evaluates chunk sizes 3–30 and reports 10 as its robust default
([paper §3.2–3.3](https://arxiv.org/html/2502.00299#S3),
[§4.4](https://arxiv.org/html/2502.00299#S4)). Its published quality and throughput figures are
observations on different models/runtimes, not an EPYC decision claim.

The production tree already contains the adjacent substrate: `src/llama-kv-compress.cpp` is compiled
and the server's `POST /slots/{id}?action=compact` path performs idle-slot Expected-Attention eviction.
That is **not a faithful ChunkKV implementation**. Expected Attention derives a future-attention proxy
from raw K/V; ChunkKV requires the actual attention scores from the final prefill queries. Summing the
existing per-token proxy into chunks would be a useful *ChunkEA* derivative, but must not be reported
as reproducing the paper. The server also deliberately leaves evicted positions gapped because its
prompt/checkpoint state tracks logical positions independently; eviction creates reusable KV capacity,
not an allocated-buffer shrink or immediate logical-context extension.

If scheduled, start from fresh production on `llama.cpp-experimental`, never the frozen production
tree: (1) capture the bounded observe-window attention scores at prefill, (2) implement ordered
top-k chunk selection plus recent-window protection, (3) reuse indices only behind a per-model
ablation, and (4) compare Full KV / current Expected Attention / faithful ChunkKV on a long-context
retrieval and quality suite with the same cache budget. This is an experimental-kernel feature and
needs its own operator-approved measurement window; no implementation or model run is authorized
during the E5 host hold.

#### Research Context

| Intake ID | Title | Relevance | Verdict |
|-----------|-------|-----------|---------|
| intake-246 | llama.cpp-tq3 — TQ3_1S Weight Quantization | medium | worth_investigating (monitor) |
| intake-245 | MSA: Memory Sparse Attention | low | not_applicable (training-only) |
| intake-828 / 829 | BitNet (2310.11453) / b1.58 (2402.17764) — foundational ternary; bitnet.cpp TQ1_0/TQ2_0 already integrated in the epyc-llama fork | medium | already_integrated |

#### Action Items

- [x] Watch PR #21038 for merge — ✅ LANDED 2026-04-01 as commit `744c0c731`, auto-enables in v3
- [x] Evaluate PR #21089 when merged — test TBQ3_0 KV cache on Qwen2.5-Coder-32B context extension ✅ 2026-07-29 — upstream closed the PR unmerged on 2026-06-02 (no `mergedAt`; last update 2026-06-03), and the local tree contains no #21089/TBQ commit. No build, benchmark, or runtime action was taken. Reopen only for a new upstream PR or a merged successor.
- [x] Read ChunkKV paper — assess if implementable in llama.cpp ✅ 2026-07-29 — experimental-only
  feasibility memo above: the required existing substrate is server-side Expected-Attention eviction,
  but a faithful ChunkKV port requires observed-prefill attention capture and ordered chunk selection;
  do not equate the two.
- [ ] Prototype faithful ChunkKV only on a fresh `llama.cpp-experimental` tree after an
  operator-approved long-context measurement window; compare it with Full KV and the existing
  Expected-Attention compactor at equal cache budgets before considering promotion.
- **[declined: ws58 2026-11-03 content-review: unbounded conditional (upstream adoption + multi-model benchmarks) with no trigger]** Revisit TQ3_1S weight quant only if: upstream adopts + multi-model benchmarks + Q4_K_M comparison + CPU kernels

---

#### Research Intake Update — 2026-05-21

##### AngelSlim toolkit + sub-2-bit weight quantization track

- **[intake-590] AngelSlim toolkit (arxiv:2602.21233)** — Tencent Hunyuan model-compression toolkit. CC-BY-4.0 (per paper) / custom proprietary (per GitHub README) — license inconsistency to resolve before code adoption. Bundles four un-indexed Tencent techniques: Sherry (1.25-bit, intake-591), Tequila (ternary QAT, intake-593), DAQ (delta-aware PTQ, intake-594), SpecExit (intake-592). Verdict: cherry-pick the algorithms + the upstream llama.cpp PR; do NOT adopt the toolkit wholesale (vLLM/SGLang/transformers-first runtime focus).
- **[intake-591] Sherry — 1.25-bit hardware-efficient ternary quantization (arxiv:2601.07892, ACL 2026)** — 3:4 fine-grained sparsity packs 4 weights into 5 bits (power-of-two-aligned 1.25 bpw, SIMD-compatible). Introduces "Arenas" annealing residual synapse to prevent weight-trapping / representational collapse during QAT. LLaMA-3.2-1B: zero accuracy loss vs SOTA ternary baselines, 25% bit savings, 10% speedup on Intel i7-14700HX. AngelSlim/Hy-MT1.5-1.8B-1.25bit-GGUF release is the public reference artefact (440 MB, claimed 1.5x decode speedup).
- **Concrete upstream path**: llama.cpp PR #22836 (STQ1_0 kernel) — sub-2-bit weight quant kernel from Tencent. This is the directly mergeable artefact into our `epyc-llama` fork. Watch consolidated HERE as of 2026-06-12 (formerly on [`llama-cpp-kernel-push-rebase`](../completed/llama-cpp-kernel-push-rebase.md), now archived).
- **[intake-593] Tequila — Trapping-free Ternary Quantization (arxiv:2509.23809)** — QAT method that identifies "deadzone trapping" failure mode and repurposes deadzone-trapped weights as dynamic biases. Claims >4% ARC gain over SOTA ternary, within <1% of FP, 3.0x speedup. Limitation: training-time only — adoption requires Tencent-released Tequila-trained checkpoints (none verified today) or in-house QAT cycle. Deferred.
- **[intake-594] DAQ — Delta-Aware Quantization (arxiv:2603.22324)** — Data-free PTQ preserving post-training deltas (RL / DPO / instruction-tune) via Sign-Preservation-Rate and Cosine-Similarity-of-ΔW metrics instead of reconstruction-error minimization. Claims to recover style-specific capabilities lost under standard PTQ. Limitation: tested in FP8 only at abstract time, where standard PTQ already near-lossless. The load-bearing question (does DAQ help at INT4 / INT2?) is unanswered. Becomes relevant only if/when we move below Q4_K_M. Deferred.

##### Delta from this handoff's KV-cache scope

This handoff (`tq3-quantization-evaluation`) tracks **KV-cache** quantization (TurboQuant, TQ3_1S, ChunkKV). The AngelSlim track is **weight** quantization. The portable artefact for both is the same `epyc-llama` rebuild infrastructure but the kernels and PRs are independent. Sub-2-bit weight quant gets its own coordination point: [[angelslim-techniques-evaluation]].

##### Caveats (Tier 2b)

- **Sherry is QAT, not PTQ** (correction logged 2026-05-21). Sherry trains on ~10B tokens of UltraFineWeb-style data and cannot be applied to an arbitrary pretrained worker the way GPTQ/AWQ/Q4_K_M can. The STQ1_0 llama.cpp kernel (PR #22836) is generic inference, but real adoption is gated on Tencent (or another party) releasing Sherry-QAT'd checkpoints of a stack-relevant base model. Today only Hy-MT1.5-1.8B and HY-1.8B-2bit are public Sherry-QAT'd weights.
- Sherry evaluated only to 3B params on Intel i7-14700HX (laptop class). Generalization to 7B-122B class on EPYC 9655 (12-channel DDR5, BW-bound regime per `feedback_cpu_decode_bw_bound`) is unverified — the 10% speedup pattern may not transfer.
- All Tequila / DAQ accuracy claims are Tencent self-reported with no third-party reproduction at intake time. ACL 2026 acceptance lifts Sherry credibility specifically (intake-591 credibility=4); intake-593/594 remain credibility=1.

##### Action Items (added 2026-05-21; STQ1_0 watch consolidated here 2026-06-12)

- **[declined: ws58 2026-11-03 content-review: unbounded upstream watch; research intake is the watch]** **Monitor llama.cpp PR #22836 (STQ1_0 kernel) for merge — SINGLE OWNER: this handoff** (consolidated from `llama-cpp-kernel-push-rebase`, archived to [`../completed/llama-cpp-kernel-push-rebase.md`](../completed/llama-cpp-kernel-push-rebase.md) 2026-06-12). On merge: cherry-pick into the next `production-consolidated-v5` (or successor) branch alongside any other pending kernel work.
- **[declined: ws58 2026-11-03 content-review: rides the retired watch; 1.25-bit Hy-MT1.5-1.8B is on no lineup path]** When STQ1_0 lands **with an x86 vec_dot** (see the 2026-08-12 check below — merge alone is not the
      trigger): llama-bench AngelSlim/Hy-MT1.5-1.8B-1.25bit-GGUF on EPYC 9655 canonical baseline (taskset -c 0-95 -t 96 -fa 1; per `feedback_canonical_baseline_protocol`); compare decode t/s vs Q4_K_M equivalent. If positive at kernel level, note scaling Sherry to worker-class models is gated on a QAT pipeline we do not have (only Hy-MT1.5-1.8B / HY-1.8B-2bit are public Sherry-QAT'd weights).
- [x] **PR #22836 status checked, and the trigger above re-scoped ✅ 2026-08-12.** As of 2026-08-12 the PR is
      `state: open`, `merged: false` (opened 2026-05-08, last touched 2026-08-10 — alive, not abandoned). The
      load-bearing new fact: its 17 changed files include `ggml/src/ggml-cpu/arch/arm/quants.c` and
      `ggml/src/ggml-cpu/arch-fallback.h` and **no `arch/x86/` file at all** — `arch-fallback.h` is exactly the
      mechanism that routes non-ARM targets to the generic **scalar** `quants.c`. So on Zen 5, a merged #22836
      gives us STQ1_0 *correctness*, not STQ1_0 *speed*. The CUDA sibling #23332 ("CUDA: add STQ1_0
      dequantization kernel") was **closed unmerged** 2026-05-22, so there is no GPU path either. Benching the
      1.25-bit artefact on merge-day would therefore not test Sherry's 1.5× claim; it would test whether
      1.3125 bpw's ≈3.4× weight-traffic reduction vs Q4_K_M survives scalar dequant ALU cost — a different
      question, and one `feedback_cpu_decode_bw_bound` predicts we lose. Re-derive with
      `curl -sS https://api.github.com/repos/ggml-org/llama.cpp/pulls/22836/files`. Mirrored in
      [`angelslim-techniques-evaluation.md`](angelslim-techniques-evaluation.md), whose checklist row also
      mislabelled #22836 as "AngleSlim kernels" and has been corrected.
- **[declined: ws58 2026-11-03 content-review: deferred with no trigger ("not actionable today")]** Defer Tequila + DAQ until QAT or sub-4-bit deployment is in scope; not actionable today

#### Research Intake Update — 2026-07-02

##### New Related Research
- **[intake-756] "NVIDIA Qwen3.6-27B-NVFP4"** (HF model card; official NVFP4 4-bit-float checkpoint)
  - **Relevance:** A concrete, official-NVIDIA **FP8-parity accuracy table** for a two-level block-scaled FP4 format — a useful *external bar* for our CPU 4-bit path (Q4_K_M / TQ3) and a comparison point vs MXFP4. NVFP4 = FP4 E2M1 elements, block_size 16, per-block FP8 E4M3 scale + per-tensor FP32 scale (finer block + higher-precision scale than MXFP4's 32/E8M0). Only transformer-block linears are quantized; attention linears + **KV cache stay FP8**.
  - **Reported results:** near-lossless vs FP8 — MMLU Pro 86.3 (FP8 86.1), GPQA Diamond 85.5 (86.0), AIME 2025 92.7 (93.1), IFBench 65.5 (65.1); ~2.5× memory (16→4 bits/param), ~22 GB weights.
  - **Delta from current approach / verdict = not_applicable (operator-review flagged):** NVFP4 is **GPU-native** (Blackwell/Hopper + vLLM), **not GGUF/llama.cpp-loadable**, and MI210 (gfx90a) has **no FP4/FP8 tensor path** — matching the intake-339 (gemma-4 NVFP4) precedent. Creative uses preserved: (a) the checkpoint's **Apache-2.0 BF16 source is freely re-quantizable to GGUF Q4_K_M/TQ3** for CPU (unsloth already ships Qwen3.6-27B-GGUF, tracked under qwen36-27b-cpu-feasibility); (b) use the FP8-parity table as a target — *does our CPU 4-bit path match FP8 as tightly?*; (c) MTP-head-preserved NVFP4 siblings mirror our MTP direction.
  - **Open question for TQ3 eval:** is a two-level (block FP8 + tensor FP32) scale worth emulating in a CPU K-quant variant, or is the accuracy delta below our decision-gating threshold?


#### Research Intake Update — 2026-07-14

##### New Related Research — lossless weight-compression sub-area (new to the corpus)
Three URLs plus reference-chasing opened a sub-area the compendium had **no** prior entry for: **lossless, entropy-coded weight compression** (exploiting the highly-skewed BF16 *exponent* distribution). All neighbors to date (TQ3 intake-246, TurboQuant intake-191, REAP intake-181) are **lossy**. Verdict across the cluster: **worth_investigating / adopt_patterns — NOT deployable at our operating point** (all yield ~11–12 bits/weight, ~2.5× larger than production Q4_K_M ~4.5 bpw).

- **[intake-815] "Lossless Model Compression Experiment"** (blog, brianbell-x)
  - Relevance: medium — directionally aligned with our BW-bound decode thesis; a 12-bit GEMV prototype ran at **0.733× BF16 time on an A40** (decode-on-the-fly can beat dense BF16 when bandwidth-bound).
  - Key technique: K15 sign-exponent encoding + byte-split; bit-exact over all 59,509 tensors of GLM-5.2 753B (30.168% smaller, lossless).
  - Delta from current approach: lossless ~11–12 bpw does **not** beat our lossy Q4_K_M footprint; GPU microbenchmark only, CPU decode untested.
- **[intake-816] "ZipNN: Lossless Compression for AI Models"** (arxiv:2411.05239, IBM/MIT-IBM/BU; credibility 4)
  - Relevance: medium — reference lossless-NN method; ~33% BF16 savings, bit-exact; the exponent-skew insight is the core idea.
  - Delta: framed as a **storage/download** optimization (>1 EB/month HF traffic), not inference-time bandwidth; decode ~1.2–2.5 GB/s would compete with our decode bandwidth.
- **[intake-817] "DFloat11 / Dynamic-Length Float"** (arxiv:2504.11651; credibility 4)
  - Relevance: low — bit-exact BF16 → ~11 bpw with a **GPU/CUDA-only** on-the-fly decode kernel; no CPU path, MI210 would need a full HIP port.
  - Delta: ~11 bpw is ~2.4× larger than Q4_K_M; headline 1.85–38.83× gains are vs BF16+CPU-offload, not vs on-GPU lossy quant.
- **[intake-818] "ZipServ: Hardware-Aware Lossless Compression"** (arxiv:2603.17435; verdict adopt_patterns; credibility 4 [audit-corrected from 3])
  - Relevance: low deploy / real conceptual — **fixed-length** (branch-free) exponent code + a **"load-compressed, compute-decompressed" fused GEMM** keeping weights compressed in the bandwidth-critical path. (ASPLOS'26 acceptance declared in the arXiv Comments field — same author-declared basis as ZipNN's IEEE Cloud and DFloat11's NeurIPS 2025.)
  - Delta: NVIDIA-Tensor-Core-locked, benchmarked only vs FP16; 1.51× lossless footprint is dominated by our lossy Q4_K_M.

##### Transferable patterns (for a future CPU/ROCm bit-exact path only)
1. The BF16 **exponent distribution is the entire compressibility budget** — a fixed-length ~3-bit exponent code (ZipServ) avoids variable-length serialization stalls.
2. "**Load-compressed, compute-decompressed**" — keep weights compressed on the bandwidth-critical path and decode into registers.

##### New outstanding tasks
- **[declined: ws58 2026-11-03 content-review: storage/download savings only; no inference or orchestration decision depends on it]** Decide (operator): is lossless exponent-coding worth a CPU/AVX-512 spike **only** as (a) staging/download savings for **full-precision FP16/BF16 source checkpoints retained for re-quantization** (NOT already-quantized GGUFs — those are near-max-entropy and compress negligibly, so the ~238GB UD-IQ2 GLM staging artifact is *not* a beneficiary), or (b) is lossy Q4/Q8 dominance decisive enough to close the lossless-weight thread? Default lean: close for inference, note for storage logistics only if we keep BF16 sources on the 120GB-SSD/3.7TB-raid host. If the storage direction is ever taken, track it under `model-stack-update-pipeline-audit.md` (staging / re-quantization logistics), not here — tq3's scope is lossy quant for the inference path.


#### Research Intake Update — 2026-07-16

##### New Related Research — PrismML Bonsai-27B + foundational BitNet papers
Batch intake (8 URLs + 3 reference-chased papers). The Bonsai family extends intake-384 (Ternary Bonsai 8B) to 27B; two foundational BitNet papers were genuine index gaps (0 prior matches) despite their descendants being tracked.

- **[intake-820] "Bonsai 27B" announcement** (prismml.com blog) + **[intake-821] Bonsai-27B whitepaper** (24pp PDF, fully parsed) + **[intake-822] Bonsai-demo repo**
  - Relevance: PrismML's post-training binary/ternary weight transform, now at 27B (Qwen3.6-27B base). Self-reported: ternary 80.5 avg @1.71 bpw / 5.9 GB, 1-bit 76.1 @1.125 bpw / 3.9 GB vs FP16 85.0. Ships **GGUF Q1_0/Q2_0 via a PrismML llama.cpp fork (`prism` branch)** with prebuilt CPU/CUDA/Vulkan/ROCm/Metal binaries across 27B/8B/4B/1.7B — materially more EPYC-testable than the intake-384 blog was.
  - Key deltas vs intake-384: adds a 4-bit KV-cache quant with a claim that low-bit weights confer near-lossless KV-quant tolerance (~12–15× less output forward-KL on-policy vs FP16-KV); adds the DSpark speculative drafter; first Bonsai carrying CoT/tool-use intact at 27B; claims the code-gen weakness is fixed (coding 82–86 retained).
  - **✅ Source-claim VERIFIED (2026-07-16 deep-dive):** the claim is correct. **Q1_0 (the 1-bit Bonsai format) is upstream** — llama.cpp PR #21273 by PrismML (`khosravipasha`), merged 2026-04-06 ("support inference for … 1-bit Bonsai models which are native in Q1_0") — and `GGML_TYPE_Q1_0` (type 41) **is already in production-consolidated-v6**. **Q2_0** (PrismML's distinct new ternary type, group-128, *not* upstream TQ1_0/TQ2_0 — see llama.cpp discussion #22019) merged upstream **2026-07-07** (PR #24448 CPU / #25419 Metal; CUDA #25707 open) — **after** the v6 cutover (2026-06-26), so it is **not** in v6. intake-384's 2026-04-17 "Q1_0 not upstreamed" note was already stale when written.
  - Caveat: custom kernels target MLX + CUDA; EPYC production is AVX-512 CPU + MI210 (gfx90a). The GGUF *formats* (Q1_0/Q2_0) and the KV-tolerance / DSpark *patterns* are portable; the kernels are not drop-in. credibility 0–1 (vendor self-report, no independent corroboration). Verdict worth_investigating. `backlog-roi-audit-2026-07-14` already declined pulling the 8B into this watch; the 27B does not change that unless a GGUF + EPYC kernel path is confirmed.
- **[intake-828] BitNet (arxiv:2310.11453)** — the seminal 1-bit-from-scratch / BitLinear paper. Verdict **superseded** by its own ternary successor b1.58 (which EPYC already supports via TQ1_0/TQ2_0). credibility 4. Kept as canonical reference.
- **[intake-829] BitNet b1.58 (arxiv:2402.17764)** — THE 1.58-bit ternary paper underpinning this whole thread. credibility 4, worth_investigating. **Load-bearing distinction:** b1.58 is train-from-scratch QAT (FP16 parity only ≥3B); Bonsai (intake-821) is a POST-training transform. We have no from-scratch pretraining pipeline, so b1.58's headline result is not directly reproducible — its value is as the reference framing the PTQ-transform vs pretrained-ternary axis for the tq3 / AngelSlim / Sherry / Tequila evaluations.

##### New outstanding tasks
- [x] Verify the "Q1_0 merged upstream / Q2_0 migrating" claim (intake-822): **VERIFIED** — Q1_0 upstream (PR #21273, already in v6); Q2_0 upstream 2026-07-07 (PR #24448), NOT in v6 (post-cutover). Both PrismML-authored; Q2_0 ≠ upstream TQ1_0/TQ2_0 (discussion #22019). ✅ 2026-07-16
- [x] Bonsai-27B Q1_0 quiet-host CPU+MI210 quality/prompting gate executed on experimental v7: corrected completion-mode runner passed 6/8 strict-output probes (`ok`, minified JSON, simple math on both devices) but failed the six-word instruction probe on both devices. Evidence: `/mnt/raid0/llm/epyc-inference-research/data/bonsai_q1_quality_gate/bonsai_q1_quality_clean_20260717T0755Z/summary.json`. Verdict: loadable/partially coherent, **not role-ready**. ✅ 2026-07-17
- [x] Ternary Bonsai Q2_g64 quiet-host CPU+MI210 quality/throughput follow-up executed on experimental v7: strict gate passed 6/8 only, failing the short-instruction probe on both devices. Raw p512/tg128 control measured MI210 `25.69` prompt / `10.53` decode t/s and CPU `25.27` prompt / `8.39` decode t/s. A realistic MI210 structured-copy CLI pair showed `ngram-mod` improves generation `9.8 -> 22.9` t/s, but this is speed-only because output retained empty `<think>` tags. Evidence: `/mnt/raid0/llm/epyc-inference-research/data/ternary_q2_g64_quality_gate/ternary_q2_g64_quality_20260717Tcodex/summary.json` and `throughput_observation.json`. Verdict: acceleration-interesting, **not role-ready**. ✅ 2026-07-17
- [x] Bonsai-8B Q1_0 current-build MI210 throughput probe executed on experimental v7 `d1e5a20eb`: `/mnt/raid0/llm/tmp/v7-bonsai8b-gpu-bench-current-20260718T141319Z/` used `llama-bench -dev ROCm0 -ngl 99 -fa on -p 2048,8192 -n 1024 -r 3` after relinking the HIP bench target. Results: `pp2048 2349.46 ± 1.11 t/s`, `pp8192 1750.72 ± 0.41 t/s`, `tg1024 38.37 ± 0.01 t/s`; post-run ROCm showed `0%` VRAM and no KFD PIDs. This is speed-only observation evidence; it does not override the Bonsai-27B quality/prompting gate or make Bonsai role-ready. ✅ 2026-07-18
- [x] Bonsai-8B Q1_0 current-build MI210 context repeat executed on experimental v7 `6a8dd5ea6`: `/mnt/raid0/llm/epyc-inference-research/data/bonsai_current_v7/bonsai8b_mi210_context_6a8dd5ea68_20260719T052624Z/summary.json` measured `pp512 2414.00`, `pp4096 2062.67`, `pp16384 1284.44`, `tg1024 36.74 t/s`; cleanup verified no KFD PIDs. This supersedes the older `/tmp` artifact for current-tip speed context but remains speed-only and does not make Bonsai role-ready. ✅ 2026-07-19
- [x] Bonsai-27B Q1_0 current-v7 MI210 `llama-bench` context probe executed on experimental v7 `d1e5a20eb`: `/mnt/raid0/llm/epyc-inference-research/data/bonsai_current_v7/bonsai27_q1_mi210_llama_bench_20260718T150243Z/` used `-dev ROCm0 -ngl 99 -fa on -p 2048,8192 -n 1024 -r 2`. Results: `pp2048 798.59 ± 0.40 t/s`, `pp8192 759.19 ± 1.72 t/s`, `tg1024 11.24 ± 0.00 t/s`. This confirms the local 27B Q1 path remains decode-slow on MI210 and is speed-only evidence; the 6/8 quality gate still blocks role readiness. ✅ 2026-07-18
- [x] Ternary Bonsai Q2_g64 current-v7 MI210 `llama-bench` context probe attempted on experimental v7 `d1e5a20eb`: `/mnt/raid0/llm/epyc-inference-research/data/bonsai_current_v7/ternary_bonsai_q2_g64_mi210_llama_bench_20260718T150707Z/` used `-dev ROCm0 -ngl 99 -fa on -p 2048,8192 -n 1024 -r 2`, emitted only `pp2048 25.68 ± 0.01 t/s`, then remained CPU-bound with `0%` GPU and no decode row until manually terminated. Treat as a current bench-path/acceleration failure and partial speed observation, not quality evidence. ✅ 2026-07-18
- [x] Ternary Bonsai Q2_g64 current-v7 MI210 short-instruction retry executed: `/mnt/raid0/llm/epyc-inference-research/data/ternary_q2_g64_quality_gate/ternary_q2_g64_mi210_short_instruction_current_v7_20260718T151711Z/summary.json` returned `prevents overfitting, ensures generalization, measures true performance.` instead of exactly six lowercase words. This confirms the instruction-following blocker survives the current v7 binary. ✅ 2026-07-18
- [x] Ternary Bonsai Q2_0 raw GGUF layout verifier completed: `/mnt/raid0/llm/epyc-inference-research/data/bonsai_current_v7/ternary_bonsai_q2_layout_contract_20260718Tcodex.json` parses header/tensor-info without `gguf-py` tensor reshape or llama.cpp model loading. Result: Q2_0 has `498/498` Q2_0 tensors short under current-v7 standard 18-byte/block `Q2_0`; sibling Q2_g64 has `0/498` mismatches. ✅ 2026-07-18
- *Moved to [`model-evaluation-queue.md`](model-evaluation-queue.md) § Track: meq-carve-tq3-quantization-evaluation on 2026-11-03 (BRF-T1-MEQ, operator D2): "Parked operator-review candidate : the GGUFs already EXIST and …".*

#### Research Intake Update — 2026-07-21 (QTIP trellis quantization — and we already ship the stubbed kernels)

- **[intake-873] "QTIP: Quantization with Trellises and Incoherence Processing"** (arxiv:2406.11235; Tseng/Sun/Hou/De Sa, Cornell RelaxML) — credibility 4; surfaced by expansion from **[intake-872]** (exllamav3/EXL3, which is a streamlined QTIP variant).
  - Relevance: trellis-coded quantization is a **distinct algorithm family absent from our entire low-bit track** (TQ3/TurboQuant, Sherry, Tequila, DAQ, PrismML are all scalar or ternary). It reaches effective quantization dimension >100 via a bitshift/LFSR trellis with *computed* rather than stored codebooks (1MAD/3INST), on top of Hadamard incoherence processing — the same primitive we already validated and landed for KV cache.
  - **The integration cost is unusually low: our v6 fork ALREADY CONTAINS the iqk trellis kernel family, stubbed out as `return false` because the registry showed zero usage** (see completed `iqk-port.md`). QTIP is the paper that family implements; ik_llama.cpp exposes it as IQ1_KT/IQ2_KT/IQ3_KT/IQ4_KT (1.75-4.0 bpw), using integer 3INST-style arithmetic chosen specifically because 16-bit integer dot products are ~2x faster on CPUs without native fp16.
  - Reported: Llama-2-70B @ 2 bit Wikitext2 3.78 vs QuIP# 3.91 vs AQLM 3.94; Llama-3-70B @ 2 bit 4.97 vs QuIP# 5.77 (largest margin). Decode throughput on par with QuIP# (25.8 vs 25.9 tok/s, RTX 4090).
  - **Three reasons to measure rather than adopt.** (1) The paper **never benchmarks against llama.cpp/GGUF quants** and reports **no CPU number of any kind** — so "QTIP beats IQ-quants at equal bpw" is unsupported in the direction we care about. (2) Our own strongest counter-datapoint: `kv-cache-quantization.md` records TurboQuant full-fix at 573 tok/s vs Hadamard+q4_0 at 1279 tok/s on EPYC 9975 — **2.2x slower**; compute-per-weight dequant has historically lost to plain q4_0 on AVX-512. QTIP's computed codes are cheaper than codebook lookup, so this is suggestive, not dispositive. (3) Zero-shot accuracy at 2 bit is within noise of QuIP# on 3 of 4 tasks — the advantage is concentrated in perplexity, not downstream task quality.
  - Also note exllamav3's own author concedes GGUF i-quants "hold up well" against SOTA formats, so the headroom over what we already run is modest.

- **[declined: operator 2026-11-03 model-audit: superseded by EXP01-PILOT (ik scratch-instrument route chosen; production-v6 wording obsolete)]** Operator-review candidate (bounded measurement, NOT a deployment): rebuild on `llama.cpp-experimental` with the iqk trellis kernels un-stubbed and `llama-bench` IQ4_KT/IQ3_KT against production Q4_K_M under the canonical baseline protocol, paired with a correctness/garbage check. Production `production-consolidated-v6` is FROZEN — experimental branch only. Gating question is narrow: does per-weight Viterbi decode cost exceed the bandwidth it saves at our operating point? [intake-873]
- [x] Coordinate the sub-2-bit angle with [angelslim-techniques-evaluation.md](angelslim-techniques-evaluation.md) rather than opening a parallel track. ✅ 2026-07-29 — ownership is now explicit: this handoff retains KV-cache/TurboQuant/trellis investigation; AngelSlim retains QAT weight-quant/STQ1_0 and its public reference artifacts. Both remain experimental-only and deployment-deferred; they share rebuild infrastructure, not a benchmark or promotion claim. [intake-873]

#### Deep-Dive Correction — 2026-07-21 (Trellis is NOT a flag flip; but our IQ-quant kernels ARE stubbed under a model we deploy)

Supersedes the trellis actionable in the 2026-07-21 intake section above. Verified against the canonical tree 2026-07-21.

**The trellis bench is 3-6 days, not a flag flip.** The stub is real (`ggml/src/ggml-cpu/iqk/iqk_stubs.cpp:35`), but four things are missing and they compound:
1. `iqk_gemm_ktquants.cpp` is **not in the build** — `ggml/src/ggml-cpu/CMakeLists.txt:55-61` lists only `iqk_mul_mat / iqk_gemm_kquants / iqk_gemm_legacy_quants / iqk_quantize_min / iqk_stubs / iqk_dispatch`.
2. The `block_iq2_kt` / `block_iq4_kt` structs **do not exist in our tree** (only in `/mnt/raid0/llm/ik_llama.cpp/ggml/src/ggml-common.h:670,682`), so the file cannot compile here.
3. The types are synthetic casts OUTSIDE the enum (`GGML_TYPE_IQ2_KT ((ggml_type)153)` … `IQ1_KT 158`) while `ggml.h:433` has `GGML_TYPE_COUNT = 43`. No `type_traits` row ⟹ `ggml_blck_size`/`ggml_row_size` index out of bounds ⟹ **a KT GGUF cannot load at all**. Same OOB class that commit `715383cde` already had to fix for ik-only types.
4. Honoring ik's IDs 153-158 against a dense `type_traits` array ripples into CUDA/HIP per-type tables; the alternative is a sparse shim. Most underestimated item.
Plus: no CUDA/ROCm path, so KT is CPU-only and the MI210 cannot participate.

**And the bpw arithmetic kills the GLM use case.** From ik's static asserts: `block_iq2_kt` = `QK_K/4 + QK_K/64` = 68 B/256 weights = **2.125 bpw**, versus **IQ2_XXS at 2.0625 bpw** — which is what GLM-5.2 actually uses. Trellis is *larger*: zero bandwidth saved, arithmetic added. It is a **quality-at-equal-bpw play mis-framed as a speed play**. Against Q4_K_M the saving is ~17.5%, but our own iqk data (+7.9-8.8% on Q4_K, ~0% on Q8_0) shows we are NOT fully BW-saturated at 4-bit, so added per-weight arithmetic eats into it rather than riding free. ik's own author states KT quants are "generally slower for token generation on CPU due to likely compute bottleneck". Mechanism differs from the TQ3 failure (computed codes vectorize; TQ3's codebook gathers did not — 573 vs 1279 t/s, 2.2x) but the outcome likely rhymes.

**THE ACTUAL CHEAP WIN — and it is the condition `iqk_stubs.cpp:11-12` explicitly warned about.** GLM-5.2 UD-IQ2_M's tensor histogram is `F32 709 | Q8_0 476 | Q5_K 313 | IQ2_XXS 148 | Q6_K 82 | IQ3_XXS 71 | IQ4_XS 4 | IQ2_S 2 | Q2_K 2`. But `iqk_typeA_supported` (`iqk_dispatch.cpp:58`) lists ONLY Q4_K/Q5_K/Q6_K/Q2_K/Q3_K/Q8_0/Q4_0/Q5_0/Q4_1/Q5_1 — **every IQ type is excluded**, and `iqk_set_kernels_iquants` is a `return false` stub (`iqk_stubs.cpp:26`). So `GGML_IQK=1` on GLM-5.2 accelerates attention and shared experts and does **nothing for the 221 routed-expert tensors that dominate both decode bandwidth and prefill FLOPs.**

Unlike KT this needs **none** of the hard parts: `IQ2_XXS=16`, `IQ3_XXS=18`, `IQ2_S=22` are already native v6/v7 enum values (no enum growth, no `type_traits` change, no GGUF change, no requant, no download), and the real kernels are already vendored and complete — `iqk_gemm_iquants.cpp` (202KB) has `set_kernels` cases at `:2760-2791` and the prefill convert path `iqk_convert_iq{2_xxs,2_s,3_xxs}_q8_k_r8` at `:2810-2813`. The known OOB hazard (converters returning ik-only `Q8_K_R8`) already has its `iqk_row_size()` fix landed.

- [x] **STEP 1 (~1 day, do first):** requested IQ2_XXS/IQ3_XXS/IQ2_S source wiring is already present in frozen v10ffc1: real iquant source is registered, two entrypoints are no longer stubs, and dispatch enables the requested types. ✅ 2026-10-07 — [MAIN four-blob source adjudication](../../artifacts/ni08/inf54-current-iq-source-adjudication-20261007/README.md). Current source also supports IQ4_XS; the historical instruction to leave it native is superseded. No compiled binary, runtime/performance/quality or trellis acceptance; STEP2/3 remain open. Do not repeat this port or modify frozen production.
- **[declined: operator 2026-11-03 model-audit: superseded by EXP01-PILOT (duplicate of T2, same ik_llama scratch-instrument measurement)]** **STEP 2 (gate, needs operator inference approval):** measure IQ4_KT vs Q4_K_M and IQ2_KT vs IQ2_XXS **inside `/mnt/raid0/llm/ik_llama.cpp` as a scratch measurement instrument** — the reference implementation is already on disk, so the whole speed/quality decision can be made without porting anything into v7. Not a second serving binary; a bench harness.
- **[declined: operator 2026-11-03 model-audit: superseded by T3 (duplicate of T3 (port only if the trellis gate wins))]** **STEP 3 (only if Step 2 wins):** the 3-6 day port. **Decision-flipper:** IQ4_KT must reach >=95% of Q4_K_M tg128 under the canonical protocol AND show a measurable task-eval win (paired per-item flips vs the reference; report PPL/KLD beside it as fidelity context only — a near-baseline KLD/PPL ordering is not a quality ordering, intake-1510, intake-1519#05). Slower than 95% ⇒ DROP permanently — 17.5% fewer bytes that decode slower is strictly dominated.
- NOTE: no IQ*_KT GGUF exists under `/mnt/raid0/llm`, and public KT producers (ubergarm, ik-community) cover the giant MoEs (DeepSeek-V3/R1, Kimi-K2.x, GLM-4.5/4.6/4.7), NOT the models we serve. Viterbi is the *encoding* cost only — decode runs the trellis LCG forward — so self-quantizing is hours on 192 cores plus an imatrix, not prohibitive, but it is not free either.
- NOTE: `/mnt/raid0/llm/llama.cpp-experimental` is a proper worktree on `experimental-v7-refresh-20260716` @ `8bb53c520`, **3 ahead / 0 behind** production — correctly fresh-pulled. It is currently DIRTY with in-flight GDN/CONCAT work, so trellis/iquant work needs its own branch off it, not a merge into that state.

##### Ownership moved — 2026-07-21

Both the IQ-quant un-stub and the KT/trellis sequencing now live in **[iqk-iquant-enablement.md](quantization-and-low-bit.md#track-iqk-iquant-enablement)** (tasks B1-B5 and T1-T3 respectively), so there is one owner and one ordering. The analysis above stands; the executable tasks moved.

**EXL3 ownership update (2026-09-25):** native EXL3 CPU and MI210/gfx90a implementation is owned by
[`exl3-cpu-mi210-implementation.md`](quantization-and-low-bit.md) (`INF-80`). This monitor remains
the quantization context owner. IQ*_KT execution remains with `INF-26`; its T2/T3 gates do not gate EXL3.

Two corrections to the section above, from the tensor-header parse: the whitelist covers **five** native types (IQ2_XXS, IQ2_XS, IQ2_S, IQ3_XXS, IQ3_S), not three — matching exactly what `iqk_gemm_iquants.cpp` implements in both its kernel and converter switches. And the change benefits **all four** IQ-quant registry models, not GLM-5.2 alone; **Qwen3-Next-80B i1-IQ2_M gains the largest share (433 of 807 tensors, 54%)**.

#### 2026-08-03 — intake Stage-2: the Escha 2-bit assessment, and a quant-choice trap it exposes

_Via `/research-intake` Stage-2 on intake-945/946/956 (`EschaLabs/Qwen3.6-35B-A3B-Escha-W2`). Ingested as
part of the standing search for a faster `worker_general`; see
[`architect-model-selection-bench.md`](model-evaluation-queue.md) for the role-level verdict._

**The `eschamoe` format itself is unusable here.** It is closed CUDA sm_80-120 with no ROCm path — the
same wall as the rest of the quantization×kernel co-design school (ZipServ, EXL3, Sakana are all
ROCm-excluded). That closure is now recorded across the corpus so it is not re-derived source by source.

**But the model underneath is worth a look, and the quant choice is not the obvious one.** If
`Qwen3.6-35B-A3B` is benched as a `worker_general` candidate, the size-matched option to the Escha build
is `UD-Q2_K_XL` — and taking it would be a mistake:

```
ggml/src/ggml-cpu/iqk/iqk_dispatch.cpp:73-74   (frozen production-consolidated-v8, read-only)
    static_assert(!iqk_typeA_supported(GGML_TYPE_Q2_K));
    static_assert(!iqk_typeA_supported(GGML_TYPE_Q3_K));
```

Q2_K and Q3_K are **statically asserted out of the iqk path**, so a Q2_K build forfeits iqk acceleration
entirely — on a workload where iqk is worth +33–43% prefill. `UD-IQ3_XXS` is on the five-type native
whitelist above, is **13.2 GB** (inside `worker_general`'s existing 16 GB budget), and keeps the
acceleration. **Choose IQ3_XXS over the size-matched Q2_K_XL**; the ~1 GB size difference is not worth
the dispatch loss.

- [x] Assess the `eschamoe` W2 format for our stack — NO, closed CUDA sm_80-120, no ROCm path ✅ 2026-08-03
- [x] Record the Q2_K/Q3_K iqk `static_assert` as a standing quant-selection constraint, verified read-only against the frozen tree ✅ 2026-08-03
- **[declined: ws58 2026-11-03 content-review: a rule, not a task]** If `Qwen3.6-35B-A3B` is benched, use `UD-IQ3_XXS` (13.2 GB, iqk-native), never the size-matched `UD-Q2_K_XL`
- **[declined: ws58 2026-11-03 content-review: waits on a blocked third-party author; curiosity with no stack decision]** **Deferred with a named trigger** — the third-party codebook reverse-engineering probe (intake-956) stays `stage1-unverified`; its author is blocked, 2–4 weeks. Reopen only if that probe publishes a decoder, and only then to ask whether the format is reimplementable rather than portable

#### Research Intake Update — 2026-08-22 (Stage-2b, KIVI arXiv:2402.02750)

- [ ] **G3 (G) — close the instrument gap: run a multi-step generation eval against quantized KV.**
      **This is the real finding of the KIVI dive, and it is a gap in OUR evidence, not in our code.**
      KIVI reports **no perplexity anywhere** and explicitly rejects single-decode-step metrics as
      unsuitable for studying compressed KV. Its data show why: on Llama-2-7B the same 2-bit damage
      costs CoQA ~7% while collapsing GSM8K by ~57% (13.50 → 5.76). **Our entire first-party quality
      case for quantized KV is perplexity plus needle-in-a-haystack** — exactly the instrument class
      that survives damage which multi-step reasoning does not.
      Protocol: GSM8K (or the canonical judge suite's reasoning subset) at f16 KV vs production
      q8_0/q8_0 vs q4_0/q4_0, rotation ON, on one pure-attention model and one Qwen3.x GDN hybrid.
      Paired questions, exact-match scored, **persisted per question** (each persisted unit is a drain
      point). Production temp + seed 42 per bench defaults.
      **Gate:** any config showing a reasoning delta outside noise **while perplexity and NIAH stay
      flat** replicates KIVI's central instrument finding on our own stack — and would be the
      strongest reason yet to revisit KV-quant defaults. A flat result closes the question and
      retires the concern permanently.
- [ ] **(G, cheap) A/B the asymmetric quantizer against our rotation.** `-ctk q4_0` (symmetric) vs
      `-ctk q4_1` (asymmetric), rotation ON, same group size, one pure-attention model, plus
      `llama-bench` decode t/s to price the extra scale word.
      **Gate:** a quality delta outside noise means the Hadamard rotation has NOT fully normalised the
      distribution and KIVI's asymmetry is live for us. A tie — the prediction, since a rotated
      distribution is near zero-mean — closes it permanently for one short bench.
- **[declined: ws58 2026-11-03 content-review: diagnostic curiosity; G3 (multi-step generation eval vs quantized KV) is the decider and stays]** **G5 (G) — reproduce KIVI's Figure 2 / Table 2 on OUR architecture.** Dump per-channel key
      magnitudes from the attention layers of a production Qwen3.x GGUF at a fixed prompt, with and
      without `LLAMA_ATTN_ROT_DISABLE=1`, and compute per-group max/RMS at G=32.
      **Gate:** a near-flat rotated ratio establishes the redundancy conclusion **first-party** and
      deprioritises G3 and G4. Surviving outliers would make rotation placement (pre- vs
      post-RoPE) live — that is the trigger for B1 below, and the only one. **Nobody has measured
      whether key-channel outliers even exist under per-head QK-RMSNorm, or in a GDN/attention
      hybrid — KIVI's four ablated models all predate QK-norm.**
      **Scope caveat that bounds the whole result:** only **10 of 40** layers of the frontdoor are
      full attention, so only those have a KV cache at all. A per-channel key dump covers a quarter
      of the stack by construction; report it as such and never as a whole-model statement.
      [intake-1286#record]

#### Research Intake Update — 2026-08-23 (Stage-2b: massive activations, alignment collapse)

##### H11 (Z, RECORDED) — the three KV mitigations our tree does not have, audited read-only against frozen v9

Verified 2026-08-23 by static read of the canonical tree at
`0db32c06e3e550065b78311a6031ef3dd2c4f27c` (read-only; nothing built, nothing run). The KV-cache
write path carries **none** of the three mitigations the massive-activations literature assumes when
it reports a dynamic-range hazard:

- **No per-channel scaling.** `llama_kv_cache::cpy_k` (`src/llama-kv-cache.cpp:1311-1344`) and
  `cpy_v` (`:1346-1400`) are pure `ggml_set_rows` into the cache tensor. There is no scale tensor,
  no calibration pass and no per-channel state anywhere in the path — the *only* transform between
  the attention output and the stored bytes is the block quantizer for `type_k` / `type_v`.
- **No clipping.** Zero occurrences of `clip` or `clamp` in `src/llama-kv-cache.cpp`. An outlier is
  stored at whatever the block scale can represent; nothing bounds it first.
- **No attention-sink special-casing.** Zero occurrences of `sink` in `src/llama-kv-cache.cpp`.
  Attention sinks *do* exist in this tree, but only as a **softmax bias in the graph**
  (`ggml_flash_attn_ext_add_sinks`, `src/llama-graph.cpp:2497`; `ggml_soft_max_add_sinks`, `:2554`).
  They never exempt a token from KV quantization. **Do not read "llama.cpp has sinks" as "llama.cpp
  protects sink tokens from quantization" — different mechanisms, different files.**

The one mitigation we **do** carry is the orthonormal self-inverse Walsh-Hadamard rotation, gated at
`src/llama-kv-cache.cpp:319-336` (`attn_rot_k` / `attn_rot_v`, requiring `ggml_is_quantized(type)`
and `n_embd_head % 64 == 0`, defeatable by `LLAMA_ATTN_ROT_DISABLE`). That is the whole of our
outlier defence, and it is exactly the lever G5 probes.

- **[declined: ws58 2026-11-03 content-review: unbounded monitor; research intake is the watch]** **(Z, monitor) Watch the Zunhai Su / Startlux group for a hybrid-model KV-quant METHOD.**
      RotateKV (IJCAI 2025), KVSink (COLM 2025) and Oscar are the closest published relatives of the
      fixed 64-wide Walsh-Hadamard we already ship. **No hybrid-model KV-quantization method exists
      today**: arXiv 2608.12149 is a *characterisation* precursor — it measures activation magnitude
      across architectures and prescribes nothing for a GDN/attention hybrid. Re-check the group's
      publication list each intake wave and **pin the revision checked**; a monitor row with no
      pinned revision is how the log-linear gate fired six months late. [intake-1280#record]

##### G2 (G) — measure our actual KV outlier ratio, and produce the number the paper omits

**Owner: this handoff. Both compute planes were held elsewhere during wave 2; this is filed for
whoever holds the plane next, not run here.**
On the **10 full-attention layers only**, capture K **after QK-norm and after RoPE** and V **at
cache-write**, for ~200 prompts spanning real traffic. Report, **per layer and per head, K and V
separately**: `max/median` and `max/p99.9`. Also capture the residual stream so the figures bridge
to the paper's units. **A pooled max÷median is not the measurement** — pooling hides exactly the
asymmetry this exists to find (`vidya-belief-substrate-program.md` SC50 caveat (d)).
The paper reports only a bare max-absolute value and **never a median**, so no dynamic-range figure
exists anywhere in the literature for this architecture class. We can produce the number it lacks.
Prerequisite `Z11` (harness choice — prefer a llama.cpp `cb()` tap over the transformers/PyTorch
hook harness, because the GGUF path is the one that quantizes).
**Gate:** if V's `max/median` materially exceeds K's, `-ctv` is the risk surface and V-side defaults
are reopened. **If both are unremarkable (< ~50×), close the whole massive-activations line for this
stack as measured-and-negative**, so it is never re-opened from an abstract. [intake-1280#record]

##### G4 (G) — paired behavioural drift across our KV configs (IFEval, FP16-anchored CondFlip)

**Owner: this handoff.** IFEval subset **N >= 250**, greedy `t=0` seed 42, **one model held
constant**, sweeping `-ctk`/`-ctv` over `{f16/f16, q8_0/q8_0, q8_0/q4_0, q4_0/q8_0, f16/q4_0}`.
Score **FP16-anchored paired ConditionalFlip** — the fraction of FP16-baseline passes that flip to
failure under the quantized arm — **not** aggregate pass rate. The two are different quantities and
are not interchangeable (SC50 caveat (b)). Report perplexity drift beside CondFlip on every arm; the
decoupling is the whole point.
**Instrument note:** this is the IFEval axis, not a refusal/safety suite — a safety benchmark suite
is an explicit decline for a single-operator research stack, and CondFlip carries the transferable
lesson (perplexity is blind to behavioural drift) onto an axis we actually serve.
**Gate:** any config with **CondFlip > 5% while PPL drift < 2%** reproduces the decoupling and makes
a behavioural gate **mandatory** before any future KV-default change. **All configs < 2% ⇒ our
group-32 granularity is doing the work**, and perplexity-plus-NIAH was retrospectively adequate —
close the line. [intake-1291#record]
*Flip-counting amendment 2026-09-23 (intake-1510, intake-1519#00, intake-1519#05):* also count leapfrogs (FP16-fail → quant-pass), report C→I
and I→C separately plus net direction, and use greedy decoding or a measured FP16-vs-FP16 flip floor before reading any
flip count — sampled 16-bit runs differ by 23.5% flips.

##### B1 (B, blocked on G5) — pre-RoPE vs post-RoPE rotation placement

**Upstream item: G5.** RotateKV's ablation implies post-RoPE rotation alone is insufficient **at 2
bits**; we run 4/8, and the frozen tree stores rotated post-RoPE keys by construction. **Do not open
until G5 shows outliers *surviving* rotation.** If G5's rotated ratio is near-flat, this is a
**permanent decline**, not a deferral — record it as declined and stop.

##### B2 (B, blocked on G4) — confirm the K/V asymmetry direction, then generalise or drop it

**Upstream item: G4**, specifically its `q4_0/q8_0` vs `q8_0/q4_0` pair — those two arms are the
decisive comparison and neither is optional. If K-dominance holds on our stack, generalise it into a
standing **"quantize V before K"** selection rule and write it into the registry's KV defaults so it
is not re-derived per model. Third-party direction to test against, **never to adopt as a
baseline**: K-projection quantization accounts for 76-102% of alignment damage in 8 of 9 models at
4-bit, with a measured Qwen K:V ratio of 154x (K-only 92.2% flip vs V-only 0.6%). If our arms
disagree with that direction, ours governs. [intake-1291#record]

#### Research Intake Update — 2026-08-22 (Stage-2b, intake-1280 massive activations)

##### Deprioritisation record — our hybrid is the LEAST massive-activation-exposed one measured

`arXiv:2608.12149` (intake-1280#record) characterises massive activations across five linear-attention
architectures, four hybridization ratios, two scales and twelve large open checkpoints — **including
ours**. Two things follow for this handoff, and the second is the reason this is a *record* rather
than a task.

**1. The ratio convention, so nobody re-derives it wrong.** §2 defines ρ = L / L_FA, so a "ρ:1"
configuration has one full-attention layer per ρ sequence-mixing layers; Table 4 confirms it
(Hybrid-3:1 = 16 linear + 8 full of 24). **Production Qwen3.6-35B-A3B is 10 full-attention layers of
40, i.e. ρ = 4** — not one of the paper's trained arms; it sits between 3:1 and 6:1. **Cite §2 and
Table 4, never Appendix C.1**, which calls Qwen3.5 "a fixed 3:1 pattern" while stating in the same
sentence that it has 40 layers with 10 full attention — the informal literal sense, contradicting the
paper's own formula. The full convention record, with the corroborating read of
`src/models/qwen35moe.cpp:25-36`, lives in
[log-linear-gated-deltanet-readiness.md](../completed/model-architecture-readiness-completed-20261107.md#track-log-linear-gated-deltanet-readiness); it is not duplicated
here.

**2. At ρ = 4 our family shows the smallest massive activations of every hybrid the paper measured.**

| Checkpoint | ρ | Peak first-token magnitude |
|---|---|---|
| **Qwen3.5-35B-A3B, Base *and* Instruct** | **4** | **30** (all six domain panels) |
| Kimi-Linear-48B-A3B Base / Instruct | ≈ 3.9 (27 mixers: 20 KDA + 7 MLA) | 180–240 / 300 |
| Qwen3.5-122B-A10B / 397B-A17B | 4 | 60 / 75 (120 on CodeSearchNet) |
| Zamba2-1.2B | — | 300 |
| Nemotron-H 8B / 47B / 56B | ≈ 6.4 at 56B | 750–1800 |

**Caveat, carried verbatim because it is the difference between a datum and a folklore number:** these
are *"PEAK FIRST-TOKEN MAGNITUDE, read from the y-axis upper bounds of Figure 20 (these are UPPER
BOUNDS on the plotted peak, not tabulated values — the paper tabulates no peak magnitudes)"*. And the
paper's own Table 7 caption restricts magnitude comparisons to **within an architecture and scale**,
so the cross-family column above is *suggestive, not measured*.

**Why the Kimi Linear row is nonetheless the load-bearing one.** It is **ratio-matched** — ρ ≈ 3.9
against our 4 — and it is 6–10× more exposed. Ratio therefore does not explain the gap. What does is
**output gating on the full-attention layers**, which the paper independently identifies as the
dominant attenuator (adding FA output gates "markedly attenuates" the spikes; removing all GDN output
gates produces "only a moderate increase" — the effect tracks gate *placement*, not gate count). Our
family ships that gating natively: `src/models/qwen35moe.cpp:349-354`. The paper also concedes the
ratio story does not generalise — the *sparsest*-attention family it measured (Nemotron-H, ρ ≈ 6.4)
shows the *largest* magnitudes, and "magnitude has no consistent monotonic relationship with parameter
count". **So no ratio-based extrapolation to our stack is supported; only the direct Qwen3.5
measurement bears on us, and it is reassuring.** One generation's caveat: the paper measures Qwen3.5,
production is Qwen3.6-35B-A3B — same architecture, different checkpoint.

**Disposition: deprioritise, do not close.** This lowers the prior; it does not settle anything,
because the paper **contains no quantization experiment of any kind** ("quantization" appears once, in
a related-work paragraph) and **reports no median anywhere**, so *no dynamic-range ratio can be
computed from it* — the one number that would tell us whether our KV cache is exposed. The row that
would close the line as measured-and-negative is the first-party outlier-ratio measurement already
filed against this handoff (max/median and max/p99.9 for K and V separately, on the 10 full-attention
layers). Until it runs, **do not re-open this line from an abstract** — that is what this record
exists to prevent.

#### Research Intake Update — 2026-10-20 (LittleBit and LittleBit-2: QAT-only sub-1-bit references — monitor)

- **[intake-1977] LittleBit (arXiv 2506.13771) and [intake-2022] LittleBit-2 (arXiv 2603.00042)** — verdict: reference only, not a candidate. Both are quantization-aware training with knowledge distillation per model (LittleBit-2 changes only the initialisation, Joint-ITQ), the layer is two binary low-rank paths plus FP16 scales (not a ggml block type), embeddings and lm_head are outside the bits-per-weight count, no inference kernel is released (the 11.6x figure is one Llama-2-70B MLP-layer GEMV on an A100, inherited by LittleBit-2), and quality at 0.1 bpw stays about 2.7x FP16 perplexity on Llama-2 7B (`intake-1977#record`, `intake-2022#record`). This matches the b1.58 framing above (QAT, not PTQ). **Monitor trigger:** a post-training variant, or a published CPU/HIP inference kernel for the two-path layer, appears in the SamsungLabs/LittleBit repository or an arXiv follow-up; until then no serving-path, kernel or microbenchmark work. Low-bit effort stays on the PTQ IQ1/IQ2/IQ3 lanes for DS41/Q38FN (ppl + NMSE + coherence; see `iqk-iquant-enablement.md`). Closed with reason 2026-10-20: a two-binary-GEMM CPU microbench (speed-only without QAT'd weights; a layer of a few MB at 0.1 bpw is L3-resident) and an init-only Joint-ITQ NMSE comparison (no downstream path without per-model QAT and a new kernel). The one transferable observation, that a shared orthogonal rotation of SVD latent factors is free at inference, belongs to the rotation/incoherence-processing family already tracked at the QTIP entry (intake-873) above.

#### Research Intake Update — 2026-10-22

- **K8 — ternary ASR encoder kernel as a reference design (intake-underdog-bark-20261021; knowledge, no task).** The thrush-ternary-v2 packed format is readable (spec and decode verified in the intake-2344 dive) and mudler/parakeet.cpp carries a group-128 int8-activation ternary kernel with a 16-row interleave, a reference for any future TQ2_0 AVX-512-VNNI path; no new low-bit model lane is opened (operator steering: low-bit work stays on the DS41 and Q38FN lanes), and the redux model itself was declined for STT on French quality (intake-2344#record, intake-2347#record).

#### Research intake 2026-10-22 — SLQ / IST-DASLab / kaitchup Qwen3.8-27B SLQ (intake-2461..2493)

Source: research intake session intake-ist-slq-20261022, Stage-3 plan `/mnt/raid0/llm/tmp/intake-ist-slq-20261022/stage3/STAGE3_PLAN.md` (sha256 db108374cd1bd164e5baaac2586b9d3abf26daaba46aec4085192e4b0c0232ad); operator ruling 2026-10-22 approved a subset. Trigger prose and knowledge notes from that plan are still pending the operator and are not filed here.

- [x] **TQ3-PWR1 — State power and add an exact one-sided degradation verdict before STEP 3 and G4 run (intake-2484).** (filed 2026-10-22 via research intake, operator-approved 2026-10-22) For each task-eval gate print n_discordant, the direction (b vs c) and the one-sided exact binomial p beside the two-sided P-PAIRED McNemar (keep two-sided for preference gates), and state power first: required N is about p_flip x (2.486/delta)^2 at one-sided alpha 0.05 and 80% power, with p_flip from a measured same-model flip floor; at p_flip 10%, G4's N >= 250 detects only about 5-point drops (about 26% power at 2 points), so record G4 as a coarse screen unless N is raised. The P-PAIRED protocol block itself is human-amendment-only and is not edited.

  *TQ3-PWR1 note 2026-10-22 (workspace-58).* Helper: `scripts/autopilot/degradation_stats.py` in epyc-orchestrator (commit 0993affc; tests `tests/unit/test_degradation_stats.py`). `python -m scripts.autopilot.degradation_stats verdict --b B --c C` prints n_discordant, direction (b = baseline correct/candidate wrong vs c) and the one-sided exact p (scipy binomtest, alternative=greater); `size --p-flip P [--n N] [--margin 0.02]` prints required N, power at N and the margin N supports. Required N = ceil(p_flip*(2.486/delta)^2), one-sided alpha 0.05, 80% power (intake-2484#02; our arithmetic from the paper's SNR relation, no N table is in the paper).
  Required N (items) at the grid below; the ONLY inputs that matter are blanks until measured:
| p_flip (grid, not an estimate) | delta 1 pp | 2 pp | 3 pp | 5 pp |
|---|---|---|---|---|
| 5% | 3091 | 773 | 344 | 124 |
| 10% | 6181 | 1546 | 687 | 248 |
| 15% | 9271 | 2318 | 1031 | 371 |
| 20% | 12361 | 3091 | 1374 | 495 |
  Per-gate inputs: **G4** N >= 250 (gate text); p_flip = ____ (measure: FP16-vs-FP16 greedy t=0 seed 42 rerun on the same IFEval subset, per the 2026-09-23 flip-counting amendment; no estimate exists yet). At N=250 the minimum detectable net drop at 80% power is 4.97 pp at p_flip 10% (3.52 pp at 5%, 7.03 pp at 20%); power for a 2 pp drop is 26% / 41% / 17% at p_flip 10% / 5% / 20% -> record G4 as a COARSE SCREEN (about 5 pp class) unless N is raised to the table value. **STEP 3** N = ____ (task-bank item count, not yet fixed); p_flip = ____ (measure: Q4_K_M-vs-Q4_K_M rerun, or Q4_K_M vs IQ4_KT sampler-matched flip floor, on that bank). Print the one-sided verdict beside the two-sided P-PAIRED McNemar (kept two-sided for preference gates); P-PAIRED block untouched. Fill the blanks and re-run `size` before either gate executes.

- [x] **EXP01-IMATRIX-SHEXP** [inference] Make the EXP-01 trellis screen buildable: the ik `llama-imatrix` output (`/mnt/raid0/llm/tmp/brf-exp01/build/imatrix.dat`, 560x512 calib) has no entries for shared-expert tensors (`blk.N.ffn_*_shexp`), so IQ2_XXS refuses to quantize. Options: an imatrix tool/flag that records shexp tensors, or a per-tensor type override for shexp only (documented in the arm identity). Then rerun the build row and publish the measure row (`bin/post_build.sh`). Stop rule: the pilot's own futility/answer looks. Done when: all four arms build and the measure row records a screen verdict in EXP01-PILOT.

- 2026-11-04 EXP01-PILOT filing correction (measure `brf-exp01-trellis-pilot-20261102-r2`, build r5): build r5 passed with all four arms; pilot execution rc=0 and captured 3 launches per arm plus 48 quality records, but the speed comparison is **INCONCLUSIVE**. `run/speed-Q4KM-1.json` records `n_threads=4` from the smoke before the official grant; the remaining 11 launches record `n_threads=24`. The launcher resumed smoke units in the official output directory. Thus the IQ4_KT/Q4_K_M ratio 1.1019, band [0.7973, 1.4065], mixes resource allocations. Dropping that launch post hoc (0.955 descriptive ratio) is not a declared estimator, and the prior EXPAND conclusion is withdrawn. IQ2_KT/IQ2_XXS band [0.8909, 0.9656] also did not meet the declared futility stop. Quality counts were IQ4_KT 14/24 versus Q4_K_M 12/24; the small slice establishes no task-eval win. Keep EXP01-PILOT and T2/T3 open; repair smoke/official result isolation and rerun the same bounded screen before deciding on a port. All six terminal rows have owner FILED receipts. [belief: cc]

- 2026-11-04 EXP01-PILOT successor: `brf-exp01-trellis-pilot-20261104-r3` published after four-CPU publisher SMOKE PASS; smoke native result is under its per-attempt dryrun directory, official results under `/mnt/raid0/llm/tmp/brf-exp01/run-r3/results.jsonl`. Same four arms, three launches per arm, 24 pinned items for Q4_K_M/IQ4_KT, unchanged estimator and stopping rules. File the new run before deciding on port/futility; the parent pilot remains open.

- 2026-11-04 EXP01-PILOT final bounded result: isolated row `brf-exp01-trellis-pilot-20261104-r3` rc=0, all 12 speed launches on 24 threads within the official grant, 48 quality records. IQ4_KT/Q4_K_M 0.9630, operational band [0.9436, 0.9824]; IQ2_KT/IQ2_XXS 0.9610, band [0.9392, 0.9828]. Neither declared stopping condition reached before the three-launch-per-arm cap. Quality 14/24 versus 12/24, paired wins/losses 2/0; no established quality win. **Bounded pilot complete; decision inconclusive; no port trigger.** T2/T3 remain open. Findings and optional follow-up decision: [EXP01 report](../../docs/findings/exp01-trellis-proxy-pilot-20261104.md); original evidence [FILING.json](../../docs/evidence/exp01-pilot-r3-20261104/FILING.json). [belief: cc]

- 2026-11-04 **operator approved extension** (EXP01 follow-up decision package, [EXP01 report](../../docs/findings/exp01-trellis-proxy-pilot-20261104.md)): the operator chose the alternative over hold-port — extend only IQ4_KT versus Q4_K_M to a predeclared cap of eight launches per arm on one CPU quarter, same proxy identities (`models.env` pinned shas), same declared estimator, planned looks and stop rules (answer: band wholly above 1.00; futility: band wholly below 0.95), speed-only, hard cap 600 s. Fresh isolated output `run-r4/` (no reuse of r3 launches). Still exploratory/decision-support: no port, no T3 gate result; a separately declared, adequately powered paired quality comparison remains required before any port.
- [x] **EXP01-EXT — run and file the operator-approved IQ4_KT vs Q4_K_M eight-launch speed extension.** [inference] Row `brf-exp01-trellis-ext-20261104-r4` (launcher `/mnt/raid0/llm/tmp/brf-exp01/launcher_r4.sh`, job `bin/job_r4.sh` = r3 job with `PAIRS=Q4KM:IQ4KT`, `LAUNCHES=8`, `CAP_S=600`, `SPEED_ONLY=1`), result `/mnt/raid0/llm/tmp/brf-exp01/run-r4/results.jsonl`. Model: Qwen3.6-35B-A3B proxy (IQ4_KT and Q4_K_M requantized from Q8_0, pinned shas in `models.env`), ik_llama.cpp reference instrument. stop-on-answer when the tg128 IQ4_KT/Q4_K_M band lies wholly above 1.00 at a planned look; stop-on-futility when the band lies wholly below 0.95; hard cap 8 launches/arm or 600 s; gate-class = futility-only. Done when: the row is terminal and its SUMMARY (ratio, band, look verdicts, 24-thread allocation check) is filed here and in the EXP01 report with the port decision restated (hold unless the band clears; quality still unresolved).
  - ✅ 2026-11-04 `brf-exp01-trellis-ext-20261104-r4` filed inconclusive (terminal, 8 interleaved launches/arm rc0): IQ4_KT/Q4_K_M tg128 ratio 0.953, band [0.9373, 0.9687] (means 34.21 vs 35.90 tok/s) wholly below 1.00, straddles the 0.95 bar, neither stop rule fired; speed-only, quality not run. Port decision: HOLD (band does not clear 1.00). [no-belief: row verdict filed via churn file_result]
