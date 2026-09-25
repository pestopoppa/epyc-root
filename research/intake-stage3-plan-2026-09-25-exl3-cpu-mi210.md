# Stage-3 Action Plan — EXL3 on EPYC and MI210/gfx90a

**Session**: `intake-exl3-mi210-20260925` · **Created**: 2026-09-25 · **Mode**: plan — operator approval is required before Stage-4 handoff, index, adapter-register, or intake-disposition writes
**Lane**: worktree `/mnt/raid0/llm/worktrees/intake-exl3-mi210-20260925`, branch `intake/exl3-mi210-20260925`, HEAD `a6a3f99ac8883a6f73c02d7bbcb91a4916a90c97`
**Intake state**: `intake-1528` through `intake-1562`; 35 entries; validator `exit 0` with 1,558 entries; all selected and surfaced sources resolved
**Implementation posture**: custom CPU and HIP kernels are first-class work. Production v10 remains frozen. Implementation begins on a fresh `llama.cpp-experimental` branch from the current production tip.

## 1. Recommendation

Create one active implementation program, `INF-80`, rather than reopening the completed, operator-confirmed `INF-71` Qwen CPU study. The earlier no-go priced one model's CPU weight-stream savings at one operating point. It did not implement MCG, dense EXL3, a native gfx90a path, mixed-K dispatch, or hybrid CPU/MI210 execution. The operator's current objective is an architecture enablement program covering those missing surfaces.

The program should build one backend-neutral EXL3 artifact and reference layer, then three native operator families:

1. EPYC scalar plus AVX-512/VNNI/VBMI decode for `mul1` and MCG.
2. MI210 wave64 GEMV for decode and short routed-expert batches.
3. MI210 FP16-input, FP32-accumulating MFMA for prefill and wider batches.

Grouped K-specialized and unified runtime-K dispatch remain available until local EPYC and MI210 measurements select a policy. Hybrid CPU/GPU streaming begins only after the independent CPU and GPU operators pass the same reference gates.

The first meaningful hardware milestone is one real `mul1` expert and one real MCG expert producing matching full operator outputs through the portable oracle, optimized EPYC path, and MI210 wave64 path. A public “first on gfx90a” claim requires a fresh public-artifact search and a replayable receipt at the time of the result.

## 2. Plan-completeness gates

| Gate | Status |
|---|---|
| Every Stage-1 preliminary actionable promoted or explicitly declined | PASS — §9 maps all four |
| Every dive-derived actionable filed or explicitly declined | PASS — §9 maps A1–A9, B1–B7, C1–C6, E1–E7, F1–F5 and D1–D4 |
| Every steering-ledger row filed or explicitly closed | PASS — §3 maps seq 1–10 |
| No unverified number, metric, or mechanism used in a task | PASS — proposed task content uses only `dive-verified` or corrected `dive-overturned` entries |
| Every dive-surfaced source ingested and dived or operator-declined | PASS — all 23 accepted declines are recorded in bearing entries; final two were accepted at 2026-09-25T12:11:12Z |
| Every target checked for frozen/pointer status | PASS — §4; no completed/frozen/pointer handoff owns live work |
| One domain-index owner for every new stub | PASS — `INF-80` only, in `inference-research-index.md` |

## 3. Steering ledger

| Seq | Operator direction | Disposition |
|---:|---|---|
| 1 | Build a viable CPU and MI210 path that can capture the gains seen on NVIDIA | File as the `INF-80` objective and EXL3-1 through EXL3-10 |
| 2 | Custom kernels are explicitly welcome | File as the native EPYC, wave64 GEMV, and MFMA paths in EXL3-2/3/4 |
| 3 | Aim to be first on this hardware architecture | File as an aspirational reproducible gfx90a milestone; require a fresh landscape check before claiming priority |
| 4 | Proceed with all recommended dives | Closed research authorization; Stage-2 base dives completed; no additional implementation task |
| 5 | Proceed as recommended | Closed research authorization; Stage-2b wave 1 completed; no additional implementation task |
| 6 | Clarify whether W4A16 is an EXL3 alternative | File EXL3-9. W4A16 is an alternative deployment quantization family; matched local evidence will decide between deployments |
| 7 | Proceed as recommended | Closed research authorization; wave 2 and accepted declines completed |
| 8 | Proceed as recommended | Closed research authorization; wave 3 and accepted declines completed |
| 9 | Proceed as recommended | Closed research authorization; wave 4 and accepted decline completed |
| 10 | Accept declines and move to Stage 3 | Closed Stage-2 gate and produced this plan; no separate implementation task |

Stage 4 will fill these exact references into `.research-session.json.steering_ledger[].plan_ref`: seq 1 → `INF-80 objective`; seq 2 → `EXL3-2/3/4`; seq 3 → `EXL3-3`; seq 6 → `EXL3-9`; seq 4/5/7/8/9/10 → `CLOSED-RESEARCH-WAVE`.

## 4. Ownership and status audit

| Candidate | Status found | Stage-3 decision |
|---|---|---|
| `handoffs/completed/exl3-trellis-cpu-kernel.md` / retired INF-71 | Completed; operator-confirmed no-go for the earlier Qwen CPU lever | Historical evidence only; do not edit or reopen |
| `tq3-quantization-evaluation.md` / INF-54 | Active monitoring umbrella | Add an ownership pointer; no EXL3 implementation tasks |
| `iqk-iquant-enablement.md` / INF-26 | Frozen v8 result plus active post-v8 research | Add a format-separation pointer; IQ*_KT gates do not gate EXL3 |
| `agentic-rocm-kernel-authoring.md` / INF-03 | Active gfx90a authoring and verification program | Add `INF-80` as a consumer; no duplicate kernel tasks |
| `autokernel-research-loop.md` / INF-06 | Active document; current GLM campaign explicitly stopped | No Stage-4 edit. Consider EXL3 as a future seed only after reference correctness exists |
| `cpu-decode-roofline-program.md` / INF-70 | Main campaign closed; active residual holder; contains retired INF-71 record | Add a scoped successor pointer without changing the old no-go |
| `vidya-belief-substrate-program.md` / EVL-47 | Active evidence transport owner | Add one prospective write-side task; no kernel ownership |
| `master-handoff-index.md` | Router and operator-decision queue only | No row; this plan contains no new operator-only implementation decision |

## 5. New stub — `handoffs/active/exl3-cpu-mi210-implementation.md` (owner: `INF-80`)

Full proposed content:

```markdown
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
```

## 6. Existing handoff edits

These are ownership/pointer edits. They do not duplicate `INF-80` tasks.

### 6.1 `tq3-quantization-evaluation.md`

Append under `### Ownership moved — 2026-07-21`:

```markdown
**EXL3 ownership update (2026-09-25):** native EXL3 CPU and MI210/gfx90a implementation is owned by
[`exl3-cpu-mi210-implementation.md`](exl3-cpu-mi210-implementation.md) (`INF-80`). This monitor remains
the quantization context owner. IQ*_KT execution remains with `INF-26`; its T2/T3 gates do not gate EXL3.
```

### 6.2 `iqk-iquant-enablement.md`

Append at the start of `## Adjacent: the KT/trellis family`:

```markdown
**Format boundary (2026-09-25):** IQ*_KT and EXL3 are distinct tensor formats, codebooks, loaders, and
kernel paths. T2/T3 below govern IQ*_KT only. Project-owned EXL3 CPU and MI210 work is tracked by
[`exl3-cpu-mi210-implementation.md`](exl3-cpu-mi210-implementation.md) (`INF-80`) and may proceed independently.
```

### 6.3 `agentic-rocm-kernel-authoring.md`

Add to the top-level `**Related**` list:

```markdown
- [`exl3-cpu-mi210-implementation.md`](exl3-cpu-mi210-implementation.md) — `INF-80` consumer of the
  gfx90a verify/profile substrate; EXL3 implementation and acceptance remain owned there
```

### 6.4 `cpu-decode-roofline-program.md`

Append to the checked `INF-71 — EXL3 mul1 trellis experts` block:

```markdown
**Successor scope (2026-09-25):** the no-go above remains authoritative for that Qwen CPU operating point.
It does not decide the broader MCG/dense/gfx90a/hybrid architecture program now owned by
[`exl3-cpu-mi210-implementation.md`](exl3-cpu-mi210-implementation.md) (`INF-80`). Do not reuse retired `INF-71`.
```

### 6.5 `vidya-belief-substrate-program.md`

Append under the prospective write-side task section:

```markdown
- [ ] **VB-EXL3-CPU-GFX90A — wire EXL3 experimental receipts on the WRITE side before the first measured run.**
  Before the first correctness, performance, or quality-producing run, add producer-authored native schemas
  `epyc.exl3.measurement.v1` and `epyc.exl3.verifier.v1`, plus strict projections for both source kinds. Measurement
  rows use the locator run × arm × backend × operator × shape × metric; verifier rows use run × fixture × backend/path
  × proposition. Both carry schema and producer identity/hash, run/row IDs, self-hash, date, exact category, protocol
  ID (empty when ineligible), attestation path/digest, comparator/arm identity, experimental/no-promotion authority,
  and model/artifact/source/binary/library/toolchain/hardware/residency identities. Measurement rows contain exactly
  one metric with units and `metric_direction`, repetitions and `reps_basis`, and the raw vector. Verifier rows add
  checker identity/hash, fixture and read-set digests, exact `decided_proposition`, and verdict. Strict adapters accept
  only post-hook rows, project eligible native records into `ClaimTuple`, and delegate grading to `claim_tuple.grade()`.
  Historical runs are pre-hook and emit zero tuples; no new grading rule or production authority.
```

No task is added to `autokernel-research-loop.md`: EXL3 is not a tuning seed until EXL3-1 and the first native correctness gate exist, and the current campaign remains stopped.

## 7. Domain index row

Append exactly one row to `handoffs/active/inference-research-index.md`:

```markdown
| INF-80 | exl3 cpu mi210 implementation | [exl3-cpu-mi210-implementation.md](exl3-cpu-mi210-implementation.md) | EXL3-1 — Freeze the backend-neutral artifact, metadata, oracle, and evidence contract. | — |
```

`Deps` is deliberately `—`: open rows in INF-03, INF-70, or EVL-47 must not block artifact/oracle work. Phase-specific dependencies are stated inside the handoff. Do not add a master-index row and never reuse retired `INF-71`.

After the row lands, run `python3 scripts/handoffs/index_state.py`, then `python3 scripts/handoffs/index_state.py --check`; both must exit 0.

## 8. Vidya source-table row

Append these rows to `scripts/vidya/adapters/README.md` before any EXL3 correctness, performance, or quality-producing run:

```markdown
| EXL3 CPU/gfx90a performance and quality receipts (`INF-80`) | measurement | **Prospective; `epyc.exl3.measurement.v1` write side required before the first correctness, performance, or quality-producing run (`VB-EXL3-CPU-GFX90A`).** Locator: run × arm × backend × operator × shape × metric. Producer-authored, self-hashed rows carry schema/producer identity and hash, run/row IDs, one metric with units and `metric_direction`, exact category, protocol ID (empty when ineligible), repetitions and `reps_basis`, date, attestation path/digest, raw vector, comparator/arm identity, experimental/no-promotion authority, and model/artifact/source/binary/library/toolchain/hardware/residency identities. Strict adapters accept only post-hook rows, project eligible records into `ClaimTuple`, and delegate grading to `claim_tuple.grade()`; no backfill or production authority. | pending `VB-EXL3-CPU-GFX90A` |
| EXL3 CPU/gfx90a correctness receipts (`INF-80`) | verifier | **Prospective; `epyc.exl3.verifier.v1` write side required before the first correctness, performance, or quality-producing run (`VB-EXL3-CPU-GFX90A`).** Locator: run × fixture × backend/path × proposition. Producer-authored, self-hashed rows carry schema/producer and checker identities/hashes, run/row IDs, fixture/read-set digests, exact `decided_proposition`, verdict, date, exact category, protocol ID (empty when ineligible), attestation path/digest, comparator/arm identity, experimental/no-promotion authority, and model/artifact/source/binary/library/toolchain/hardware/residency identities. Strict adapters accept only post-hook rows, project eligible records into `ClaimTuple`, and delegate grading to `claim_tuple.grade()`; no backfill or production authority. | pending `VB-EXL3-CPU-GFX90A` |
```

## 9. Actionable completeness map

### 9.1 Stage-1 preliminary actionables

| Preliminary row | Stage-3 disposition |
|---|---|
| `intake-1533` CPU proposal from public `mul1` reference | Promoted to EXL3-1/2; MCG remains independent |
| `intake-1529` MI210 feasibility spike | Promoted to EXL3-3/4; direct RDNA port declined |
| `intake-1528` NVIDIA target-band idea | Narrowed and promoted to EXL3-7 as external context only; local thresholds required |
| `intake-1530` CUDA as mathematical/test reference | Promoted to EXL3-1/3/4/5; CUDA launch transplant declined |

Stage 4 will preserve these original rows as historical Stage-1 hypotheses and add `stage3_actionable_map` to `.research-session.json`; it will not rewrite their quoted `[unverified]` text as if it were a dive result.

### 9.2 Derived actionable map

| Filed item | Actionable IDs mapped exactly once |
|---|---|
| EXL3-1 | EXL3-A1, EXL3-A7, EXL3-B1 |
| EXL3-2 | EXL3-A4, EXL3-A5, EXL3-B2, EXL3-C3 |
| EXL3-3 | EXL3-A2, EXL3-C1 |
| EXL3-4 | EXL3-A3, EXL3-E4 |
| EXL3-5 | EXL3-B4, EXL3-C4, EXL3-E3, EXL3-E5, EXL3-E6, EXL3-F1, EXL3-F2, EXL3-F4 |
| EXL3-6 | EXL3-A6 |
| EXL3-7 | EXL3-A8, EXL3-B5, EXL3-F3 |
| EXL3-8 | EXL3-B3, EXL3-C2, EXL3-E1, EXL3-E2 |
| EXL3-9 | EXL3-A9, EXL3-B6, EXL3-C5 |
| EXL3-10 | program-wide regression and frozen-production boundary derived from the operator mandate and repository workflow |

### 9.3 Derived declines

| IDs | Explicit decline |
|---|---|
| EXL3-D1, EXL3-D2 | Do not bypass RDNA guards or transplant CUDA PTX, warp32 mappings, or Blackwell splits to gfx90a |
| EXL3-D3, EXL3-B7, EXL3-C6, EXL3-E7, EXL3-F5 | Do not transfer foreign performance, policies, launch/probe constants, status/diagnostic behavior, unavailable provenance, or stale snapshot payloads to EPYC/MI210 |
| EXL3-D4 | Do not begin with the full GLM artifact or present hybrid routed-expert offload as complete CPU inference |

## 10. Accepted surfaced-source declines

All 23 are closed and recorded in the named bearing entries. Stage 4 will copy this list into `.research-session.json.explicit_declines` as completed research dispositions, without creating tasks:

| Bearing | Declined as a separate intake/task |
|---|---|
| `intake-1528` | FxTwitter v2 duplicate thread endpoint |
| `intake-1531` | `IST-DASLab/marlin#7`, the original unresolved H100 issue |
| `intake-1532` | `malaiwah/glm52-exl3-vast`, an NVIDIA deployment already covered by checkpoint evidence |
| `intake-1533` | ExLlamaV3 issues `#326` and `#254`: ambiguous Threadripper report and unimplemented predictive expert caching |
| `intake-1537` | rocWMMA API guide and `ROCm/rocWMMA`, duplicates already represented by `intake-303` |
| `intake-1542` | `MiaAI-Lab/GLM-5.3-Flash-EXL3-2x-DGX-Sparks` and `vcruz305/GLM-5.3-Flash-EXL3-K2-DGX-Spark-recipe` |
| `intake-1556` | ExLlamaV3 issues `#368` and `#372`: Windows hugepage and superseded packaging issues |
| `intake-1534` | Luke458 gfx12 assembly patch and `CarouselAether/rocm_exl3#4` RDC issue |
| `intake-1535` | `ROCm/legacy-rocm-build#6273`, a generic symptom report without EXL3 causality |
| `intake-1540` | ExLlamaV3 PR `#331`, historical pinned-arena baseline context |
| `intake-1544` | `Zeuss5/cuda-exl3#5`, NVIDIA MLA-prefill recalibration |
| `intake-1545` | unavailable `tpurtell/glm-5.3-flash-ext3-2x-rtx` and unrelated vLLM PR `#51540` |
| `intake-1552` | commit `abad6a1`, Python memfd/documentation already anchored in the bearing entry |
| `intake-1554` | commit `329e051`, host-readback cleanup already anchored in the bearing entry |
| `intake-1558` | NVIDIA RTX PRO 6000 datasheet, used only to correct the record |
| `intake-1561` | commit `39a0310`, static ABI test that cannot reproduce the low-batch/no-BC GPU crash |
| `intake-1562` | commit `2dd7c2c`, backup-file cleanup with no kernel or measurement evidence |

## 11. Intake-entry updates for Stage 4

No new `dive_corrections` are planned; Stage 2 already recorded every correction and accepted source decline.

- `intake-1528` through `intake-1562`:
  - `handoffs_created: [exl3-cpu-mi210-implementation.md]`
  - `integration_disposition: integrated`
  - `disposition_evidence: ["Routed into the active INF-80 CPU/gfx90a implementation program by the operator-approved 2026-09-25 Stage-3 plan."]`
- Entries supporting the prospective measurement contract (`intake-1528`, `intake-1530`, `intake-1531`, `intake-1541`, `intake-1543`–`intake-1547`, `intake-1550`–`intake-1552`, `intake-1554`, `intake-1556`–`intake-1562`) also get:
  - `handoffs_updated: [vidya-belief-substrate-program.md]`
- `intake-1555` gets the common `integrated` fields above with this specific evidence replacing the common sentence:
  - `disposition_evidence: ["The unavailable observation source is routed into INF-80 EXL3-9 as a fail-closed provenance guard; no quality task may depend on its unseen contents."]`

Where an entry already contains an empty `handoffs_updated` or `handoffs_created` field, Stage 4 will replace the empty list in place rather than add a duplicate key.

## 12. Stage-4 execution order after approval

1. Create `handoffs/active/exl3-cpu-mi210-implementation.md` from §5.
2. Apply the four ownership pointers and the one Vidya task from §6.
3. Add the single `INF-80` row from §7; regenerate and check index state.
4. Add the prospective source-table row from §8.
5. Apply the intake dispositions in §11 and the session mappings in §§3/9/10.
6. Run `bash scripts/validate/validate_intake.sh`, `python3 scripts/handoffs/index_state.py --check`, `python3 scripts/vidya/cli.py cite-check --as-of 2026-09-25T23:59:59Z`, and `git diff --check`.
7. Report exact files, new open/completed checkbox counts, explicit declines, and validator results. No kernel code, benchmark, production branch, kernel-store, or live-process change occurs in Stage 4.

## 13. Approval boundary

Approval of this plan authorizes only the Stage-4 documentation, index, source-register, intake-disposition, and session-ledger edits named above. The resulting `INF-80` handoff is the durable implementation owner. Kernel implementation then follows the repository's experimental-kernel workflow; production promotion remains a later human boundary.
