# Research-intake Stage-3 plan: HipKittens GEMM ladder, Gluon tutorial and LLVM MFMA form (intake-1822..1826), 2026-09-26

**Status: APPROVED 2026-09-26 (operator, via coordinator; OD-1 accepted as recommended). Applied in Stage 4 on the same day.** P1–P8 were applied as written; P9 needed no rows. The one metadata addition beyond P8 is that intake-1823 also lists `deepseek-v41-flash-evaluation.md` in handoffs_updated, because the edited DS41-C52 line cites intake-1823.
Lane: `intake/hipkittens-gemm-20260926` (worktree `/mnt/raid0/llm/worktrees/intake-hipkittens-gemm-20260926`, rebased on
origin/main `c7d8d676`). Stage 4 applies exactly this plan, once approved, and nothing more.

## Evidence base
| Intake | Source | Verification | Verdict | Relevance |
|---|---|---|---|---|
| intake-1822 | AMD ROCm blog "An Educational GEMM Ladder for Helios GPUs" + HipKittens `kernels/cdna5/gemm/bf16fp32/gfx1250/` @ `be1c9184` | dive-verified | adopt_patterns | medium |
| intake-1823 | AMD ROCm blog "From Naive to Near-Peak … Gluon" + `ROCm/gfx950-gluon-tutorials` @ `4d7d632a` | dive-verified | adopt_patterns | medium |
| intake-1824 | AMD ROCm blog "LDS Optimizations on MI450" (gfx1250) | stage1-unverified | adopt_patterns (method only) | low |
| intake-1825 | arXiv 2609.15627v2 "DeepSeek-V4-Flash on AMD gfx90a" | dive-verified | adopt_patterns | medium |
| intake-1826 | LLVM PR #159493 (+ #148079) "Select VGPR MFMAs by default" | dive-verified | worth_investigating | high |

- Second readers re-found every claim anchor: 28/28 for 1822/1823 (four coverage gaps closed with added anchors), and
  the Stage-2b anchors for 1825/1826 (see `.research-session.json` `second_reader_2b`).
- No plan text quotes a number from intake-1824, the only `stage1-unverified` entry. Its sole plan use is a flagged
  method note (§8).
- Code facts cited below were read, not built, at `/mnt/raid0/llm/llama.cpp-experimental-fastload-ds41-20260925` @
  `cafb59c3`. Binary facts come from the production `libggml-hip.so.0.16.0` (sha256 `f26a166b…8079`, ggml-cuda
  source-identical to `cafb59c3`), extracted read-only by the intake-1823 dive; the second reader re-derived Q8_0 J=64
  and J=32 metadata and they MATCH.

## The findings that drive every item (dive-verified)
1. **MMQ on gfx90a is at its register ceiling at J=64.** Every `mul_mat_q` instance is 512 threads, 2 waves/SIMD,
   256-register cap, VGPR-form MFMA, 0 AGPR. Q8_0 J=64 sits at 256 VGPR with 37 spilled VGPRs and 12 spill reloads per
   hot-loop iteration. Q5_0, MXFP4 and IQ4_* spill similarly; Q2_K reloads 36. Q8_0 at J=48/32/16 uses 210/148/90 VGPR
   with 0 spills. (intake-1823)
2. **The MMQ hot loop has 4 `__syncthreads` per 256-K iteration, a single LDS buffer per operand, and no register
   prefetch** (`mmq.cuh:818-891`). gfx90a has `FeatureBackOffBarrier`, so global loads issued before a barrier can
   stay in flight across it. (intake-1822)
3. **Builtins available on ROCm 6.2 for gfx90a:** `sched_group_barrier` (DS_READ 0x100, MFMA 0x008), `sched_barrier`,
   `iglp_opt`, `s_setprio`, and dword `raw.buffer.load.lds`. **Not available:** split barriers, async b128 loads, TDM,
   clusters, WMMA, and `mfma_i32_16x16x32_i8`. (intake-1822)
4. **AGPR copy tax is a compiler default.** On ROCm 6.2, a kernel whose register ceiling exceeds 256 is selected in
   AGPR form and pays `v_accvgpr` copies. Kernels capped at 256 (launch-bounds min-blocks 2) are VGPR form; our own
   occupancy-2 MMA-FA kernels already show this. ROCm Core SDK 7.14.0 and 10.0.0 flip the default for all kernels
   (LLVM #159493). MMQ (512 threads) is unaffected either way. (intake-1823, intake-1826)
5. **Routing:** on CDNA2, dense Q8_0 uses MMQ only at ne11 ≤ 128, so an MMQ_MFMA ON/OFF A/B at pp512 exercises no
   MMQ-MFMA code (`mmq.cu:296-312`; second reader CONFIRMED). (intake-1822)
6. **The ladder's own numbers are vendor-rounded and bundled.** The in-code rung factors compound to about 1.79× rather
   than 1.88×, and L5, L10 and L12 each bundle several changes. No rung number is quoted as an expected gain below.
   (intake-1822)

## Operator decisions this plan needs (one, plus approval)
**OD-1 — the three sources the Stage-2b dive of intake-1825 surfaced.** All three resolved against arxiv.org with
matching titles. The Stage-2 close-out rule needs each of them ingested-and-dived or explicitly declined before Stage 3
can close.
- arXiv 2607.05147, DSpark. **Recommendation:** in Stage 4, record a re-encounter on intake-738 that sets its
  `arxiv_id`, which resolves 738's "no arXiv id exists" provenance note. Otherwise decline; no new entry.
- arXiv 2606.19348, the DeepSeek-V4 tech report. **Recommendation:** decline for this lane; ingest in a DS41-focused
  intake.
- arXiv 2609.19969, "DeepSeek-V4.1-Flash: Pushing the Limits of KV Cache Compression". **Recommendation:** decline for
  this lane; ingest in a DS41-focused intake. It bears on DS41's attention/KV facts, not on GEMM kernels.

Choosing the recommendation closes the gate. Choosing an ingest instead adds a Stage-2c round before approval.

## Gating (operator directive 2026-09-08)
*"No more pure kernel inference research until we have a FULLY consolidated champion collecting all GPU AND CPU
performance progress."*
- **P2 (AutoKernel MMQ seed set) and P1-b (INF03-AGPR-1) are GATED.** They are filed as tasks carrying an explicit
  `GATED` marker, so they are durable and dispatchable, but nothing runs until the operator lifts the directive.
- Every other item is an audit, documentation, correction or correctness-oracle item and is not gated.
- The DS41 CPU items (P5) ride the live DS41 campaign, which already carries operator authorization (DS41 §C,
  2026-09-23).

---

## P1 — `handoffs/active/agentic-rocm-kernel-authoring.md` (INF-03; active, not a pointer)
Append a new section at the end of the file:

```markdown
## Research Intake Update — 2026-09-26 (GEMM ladders and MFMA form on gfx90a; intake-1822..1826)

Dived: intake-1822 (HipKittens Helios GEMM ladder + code), intake-1823 (Gluon GEMM tutorial + repo, and a read-only
extraction of our production libggml-hip.so), intake-1825 (arXiv 2609.15627, DS-V4-Flash on MI250/gfx90a),
intake-1826 (LLVM #159493/#148079, MFMA VGPR/AGPR form). What transfers to gfx90a is lever ORDER and a short list of
ROCm 6.2 builtins (sched_group_barrier, iglp_opt, s_setprio, dword raw.buffer.load.lds); TDM, split barriers, clusters,
async b128 loads and WMMA do not exist here. MMQ at J=64 already spills at the 256-VGPR cap, so every register-affecting
candidate must pass a static audit first. The AGPR copy tax on <=256-thread MFMA kernels is a ROCm 6.2 compiler default
(intake-1826#record).

- [ ] **INF03-REGAUDIT-1 — Standing zero-GPU static register/ISA audit for gfx90a HIP kernels.** Promote the
  intake-1823 dive scripts (`/mnt/raid0/llm/tmp/dive-intake-1823/ourbuild/`: split_fatbin.py, analyze_kernels.py,
  loop_analysis.py, agpr_rule_check.py) into the research repo with a README. Per kernel, emit: symbol, workgroup
  size, agpr_count / accum_offset, total and arch VGPR, vgpr_spill_count, private bytes, in-hot-loop spill reloads,
  in-loop v_accvgpr_read/write, s_waitcnt drains per iteration, and MFMA placement relative to s_barrier. Scope: MMQ,
  MMA-FA, rocWMMA FA, mul_mat_f. It is the accept gate for any MMQ/FA register-affecting candidate: no timing
  before it passes. Reads existing binaries only. Belief-kernel write side: SC84 amendment (P6).
- [ ] **INF03-AGPR-1 — GATED (operator directive 2026-09-08). NH-1 MFMA-form arm on ROCm 6.2.** On an experimental
  branch from the v10 tip, change the <=256-thread `__launch_bounds__(N,1)` of mul_mat_f (mmf.cuh) and rocWMMA FA
  (fattn-wmma-f16.cu) to `(N,2)`, with a separate `amdgpu_num_vgpr(128)` arm (waves_per_eu also raises the scheduler's
  occupancy target). Compile for gfx90a with ROCm 6.2. Accept only if INF03-REGAUDIT-1 shows agpr=0, zero in-loop
  v_accvgpr copies and no new spills; then run a matched same-window ABA with correctness. Exclude MMA-FA DKQ>=192:
  a 256 cap there would trade copies for scratch spills. Evidence: intake-1826#record, intake-1823#record.
- [ ] **INF03-GLUON-X — record, not work: Gluon and the tutorial's tools do not transfer to gfx90a.** Upstream Triton
  rejects BufferLoadToLocal on CDNA2, and local Triton 3.1.0 predates Gluon. amdgcnas hard-codes gfx950 registers,
  misses gfx90a `buffer_*` spills, and deletes in-loop s_nop wholesale. llirSched's cycle table is gfx950-only (gfx90a
  16x16 MFMAs are 8-pass). Do not port. (intake-1823#record) — tick on filing ✅
- Register-pressure datapoint (cross-reference only): intake-1825 Table 5 reports a 32x32 INT8 MFMA gate at 165 VGPR plus
  32 KiB LDS collapsing occupancy on gfx90a. That is independent support for INF03-REGAUDIT-1.
```

- **Checkbox note:** INF03-GLUON-X is written pre-ticked (`- [x] … ✅ 2026-09-26`) because the dive settled it. It is
  a durable decline record, not work.

## P2 — `handoffs/active/autokernel-research-loop.md` (INF-06; active, not a pointer) — GATED
Append a new section at the end of the file:

```markdown
## Research Intake Update — 2026-09-26 (gfx90a MMQ seed set from the GEMM-ladder dives; GATED)

**GATED by the operator directive of 2026-09-08 (no pure kernel research until a fully consolidated champion).** These
are durable seeds for the GPU MMQ route, not a relaunch. Every seed must first pass INF03-REGAUDIT-1 statically, and
every measurement must use shapes that actually dispatch to MMQ on CDNA2: dense Q8_0/Q6_K/K-quants at ne11 <= 128
(Q4_K/Q5_K <= 256), Q4_0/1 and Q5_0/1 at any batch, or MoE with more than 64 experts. pp512 on a dense Q8_0 never
reaches MMQ. Target code: ggml-cuda/mmq.cuh `mul_mat_q_process_tile` :818-891, mmq-vec-dot.cuh, mmq-config-cdna.cuh.
Sources: intake-1822#record, intake-1823#record, intake-1826#record.

- [ ] **AK-MMQ-H3 — GATED. Pinned MFMA/VALU interleave in vec_dot_*_mma, with `__builtin_amdgcn_iglp_opt(0|1)` as
  the zero-authoring first arm, then hand-set `sched_group_barrier` groups.** Also issue the final MFMAs before
  `__syncthreads`, the gfx90a analogue of a split barrier. Falsifier: the ISA shows MFMAs sunk after s_barrier or
  unchanged order, or the MMQ kernel time does not move beyond the noise floor at ne11 in {16,32,64}.
- [ ] **AK-MMQ-H7 — GATED. Register-staged prefetch of the next K iteration's x/y tiles across the barrier** (enabled
  by gfx90a FeatureBackOffBarrier). Only for instances with VGPR headroom: J<=48, or K-quants whose J=64 loop is rolled.
  Falsifier: INF03-REGAUDIT-1 shows new spills or a vmcnt(0) at the barrier, or no time change.
- [ ] **AK-MMQ-H8 — GATED. y-tile fill via dword `llvm.amdgcn.raw.buffer.load.lds` plus a second y buffer** (the y
  fill is a lane-linear copy, mmq.cuh:853-878). The y double buffer drops 2 of 4 barriers per 256-K iteration. LDS
  fits for Q8_0/Q8_1/Q6_K layouts at J=64 (57,600 B) but not for Q2_K. Prior: the MMVQ prefetch that used the same
  intrinsic was net-negative. Falsifier: MMQ time within noise, or a correctness failure.
- [ ] **AK-MMQ-H10 — GATED. Remove the J=64 spill tax.** For types that spill at J=64 (Q8_0, Q5_0, MXFP4, IQ4_*,
  Q2_K), either select J=48 at 49-64 columns or restructure vec_dot to stay under 256 VGPR. Falsifier: spills unchanged,
  or the extra column tile costs more than the reloads saved.
- [ ] **AK-MMQ-H5 — GATED. nthreads / per-wave-tile sweep in mmq-config-cdna.cuh** (256 vs 512 threads at I=128;
  occupancy 2 is infeasible at I=128 because the x tile alone is 38,912 B). Each cell sits on one side of the ROCm 6.2
  AGPR rule: 256-thread arms get AGPR form with a 512 budget and copies; the rule changes on ROCm 7.14+. Record agpr,
  copies, spills and compiler with every cell.
- [ ] **AK-MMQ-SK — GATED, low prior. Stream-K off for MUL_MAT_ID small-M on CDNA MMQ.** Transfer is weak: intake-1825
  reports that split-K hurts BS1 small-M MoE in CKTile, not in MMQ.
- [x] **Recorded so it is not re-derived (dives 2026-09-26).** ✅ 2026-09-26
  - J=128 for Q8_0-layout types is KILLED at 512 threads: LDS fits (57,856 B) but VGPRs do not.
  - A register fragment ring in vec_dot is KILLED at J=64, which already spills.
  - An LDS-staged write-back is low value: each fp32 lane already writes 16 B.
  - The ladder's TDM, split-barrier, cluster-multicast, lock_simd, async b128 and partitioned-LDS rungs have no gfx90a
    counterpart; they are flagged for operator review, not dismissed.
```

## P3 — `docs/runbooks/rocm-upgrade-checklist.md` (runbook; not index-owned)
Append after the existing zero-GPU static-audit bullet (lines 40–44):

```markdown
- [ ] **MFMA form changes with the compiler (LLVM #159493, intake-1826).** ROCm 7.2.x keeps AGPR selection unless
  `-mllvm -amdgpu-mfma-vgpr-form=1`; TheRock 7.11/7.12 decide it by the inferred `amdgpu-agpr-alloc`; therock-7.13,
  ROCm Core SDK 7.14.0 and 10.0.0 select VGPR form by default, with AGPR form recovered only post-RA by
  AMDGPURewriteAGPRCopyMFMA (loop phis still TODO upstream). Add agpr_count / accum_offset, in-loop v_accvgpr
  read/write, the arch-VGPR cap and spill columns for mul_mat_f, rocWMMA FA, MMA FA (256-thread) and MMQ to the static
  audit, per compiler cell. Check that `amdgpu-agpr-alloc` is inferred, using IR from `-save-temps`: if it is not, the
  default split caps arch VGPRs at 128. gfx90a support on those releases: ROCm 10.0.0 compatibility matrix lists MI210;
  TheRock SUPPORTED_GPUS.md lists gfx90a as "Build Passing" only.
```

## P4 — `handoffs/active/autokernel-champion-aggregate.md` (INF-65; active) — correction note, no checkbox
Append under the settled CH-6 item (after its measured-results table, around line 262):

```markdown
  **Correction, 2026-09-26 (research intake intake-1822#record; second reader CONFIRMED): the 27B-Q8_0 pp512 row
  never exercised MMQ-MFMA.** On CDNA2, dense Q8_0 dispatches to MMQ only at ne11 <= 128 (`mmq.cu:296-312`), and
  with `GGML_HIP_NO_MMQ_MFMA` the fall-through is `ne11 < MMQ_DP4A_MAX_BATCH_SIZE` (64). So both arms ran hipBLAS
  for the dense matmuls. The flag also switches MFMA flash-attention selection and MFMA tile primitives, which is
  where any residual +0.50% would come from. CH-6's decision stands (the flag buys nothing where the fleet runs pp512),
  but the stated mechanism ("the regime where MFMA has least to offer") is wrong. An MMQ-MFMA question needs ubatch
  <= 128 (`-ub 128`, pp64/pp128) or an MoE/Q4_0 surface.
```

## P5 — `handoffs/active/deepseek-v41-flash-evaluation.md` (INF-77; active) and the DS41 inbox
- **Edit the existing DS41-C52 line** (the lane carries it at line 366): change "re-grade after the Stage-2 dives of
  intake-1783/1784 land" to "Stage-2 dives landed as intake-1822/1823 (renumbered from 1783/1784); the dives did not
  change the CPU set (not ladder-derived; stands on its own merit); add a static spill check of the gemm4xN
  disassembly before timing any register-raising variant (intake-1823#record)".
- Append two tasks under §C:

```markdown
- [ ] DS41-C53 — **Correctness oracle must exercise non-constant per-block scales.** Verify the AK kernel-mutation
  oracle's fixtures use varying Q8_0 `d` and Q4_K `d/dmin`/sub-scales. intake-1825 §5.3 reports a scale-layout bug on
  gfx90a that constant-scale fixtures hid (intake-1825#record). Read-only check; fix the fixture if constant.
- [ ] DS41-C54 — **Observation first: `attn_wo_a` grouped projection at nt=1.** From an existing DS41 profile, read
  the `attn_wo_a` node share and path: a 3D batched Q8_0 `ggml_mul_mat` over groups with a permuted src1,
  `src/models/deepseek41.cpp:1219-1224`. If material, admit a dedicated M=1 grouped-GEMV route to the AK scope. The GPU
  analogue in intake-1825 §8.3 is self-reported; CPU transfer is unproven.
```

- **DS41 inbox note (for the coordinator to place; this lane does not write the inbox):**

```text
# 42-ds41-dsv4-gfx90a-lessons-20260926 (research intake intake-1825, dive-verified; single-author self-report, cred 1)
(1) Oracle: DS-V4's E8M0 scale-layout bug passed constant-scale fixtures (arXiv 2609.15627v2 §5.3). Before trusting
    kernel-mutation parity, confirm the correctness oracle uses non-constant per-block scales (Q8_0 d; Q4_K d/dmin/sub-scales).
(2) wo_a: on GPU, V4's grouped wo_a output projection at M=1 was slow through the batched path; a dedicated GEMV gave
    +10.32% service (§8.3, self-reported). Our wo_a is a 3D batched Q8_0 mul_mat with permuted src1
    (deepseek41.cpp:1219-1224), inside the dense-Q8_0 class. Read its node share from an existing profile before
    proposing anything; CPU transfer is unproven.
(3) Determinism: their final-reduction and GEMM-shape changes broke first-token repeatability for 2/16 requests at 16K
    even with fixed-order reduction (§8.1). This supports the row-exact / batch-non-invariance rule (DS41-T4/T5).
Also: the gemm4xN note 41 now cites intake-1822 (was 1783); the dives left its CPU set unchanged.
No action on empty-tile skipping (the frozen tree sizes the indexer view by mask width).
```

## P6 — Belief-kernel wiring (`handoffs/active/vidya-belief-substrate-program.md`, SC84)
No new source row. SC84 (VB-VGPR-STATIC) already owns zero-GPU per-kernel register reads, and
`scripts/vidya/adapters/README.md:300` already has the row. Append one amendment bullet under SC84:

```markdown
- [ ] **SC84a — widen the SC84 tuple for INF03-REGAUDIT-1 (intake-1823/1826).** Add agpr_count, accum_offset,
  in-hot-loop spill reloads, in-loop v_accvgpr_read/write and the toolchain's MFMA-form regime (ROCm 6.2 rule vs
  #159493 default) to the native record before INF03-REGAUDIT-1 or INF03-AGPR-1 produce governed reads. OBSERVATION
  grade; no new grading rule.
```

## P7 — `handoffs/active/rocm-verify-profile-backend.md` (INF-48; active hardening)
```markdown
- [ ] **RVP-ATT-1 — desk check (no GPU): is an ATT thread-trace MFMA-efficiency metric obtainable on gfx90a with
  ROCm 6.2 rocprofv3?** If so, record the gfx90a MFMA cycle table it needs (16x16x16 = 8 passes, SISchedule.td:259 at
  rocm-6.2.0). Metric definition: total MFMA cycles over the average hot-loop iteration, per SIMD (intake-1823). Its
  only consumer is a future MMQ candidate.
```

## P8 — Intake-entry updates (Stage 4, research lane's own files)
- **intake-1822:** handoffs_updated = [agentic-rocm-kernel-authoring.md, autokernel-research-loop.md,
  autokernel-champion-aggregate.md]; integration_disposition `integrated`.
- **intake-1823:** handoffs_updated = [agentic-rocm-kernel-authoring.md, autokernel-research-loop.md,
  rocm-verify-profile-backend.md, vidya-belief-substrate-program.md]; `integrated`.
- **intake-1825:** handoffs_updated = [deepseek-v41-flash-evaluation.md, agentic-rocm-kernel-authoring.md];
  `integrated`.
- **intake-1826:** handoffs_updated = [agentic-rocm-kernel-authoring.md, autokernel-research-loop.md,
  vidya-belief-substrate-program.md] plus the runbook (named in disposition_evidence, not as a handoff); `integrated`.
- **intake-1824:** unchanged (`knowledge_only`).
- **intake-961:** append a dated dive_corrections line: "2026-09-26 (intake-1825#record): NARROWED — a modern ROCm
  Triton (3.7.1, ROCm 7.14) runs on gfx90a inside SGLang's DS-V4 path, but no Triton kernel is named or credited with
  a gain; upstream Gluon rejects BufferLoadToLocal on CDNA2 (intake-1823#record); local Triton is 3.1.0. Read 'open'
  as compiles-and-runs, not as a competitive path." Add a claim_corrections row with effect `narrowed` on the Triton
  claim, after identifying its index.
- **intake-738:** if OD-1 follows the recommendation, record a re-encounter note and set `arxiv_id: '2607.05147'`
  (title resolved 2026-09-26).
- Run `bash scripts/validate/validate_intake.sh`, then `python3 scripts/handoffs/index_state.py` and `--check`.

## P9 — Index rows
**None.** Every target handoff already has exactly one row: INF-03, INF-06, INF-48, INF-65, INF-77, and the vidya
program's own row. No new stub is proposed. `Next action` text is unchanged: none of these items displaces an owner's
current first open task. No master operator-queue row: OD-1 is intake-internal and is decided in this approval.

## Explicit declines (every ledger row not filed above)
| Item | Source | Reason |
|---|---|---|
| H1 y-double-buffer on its own | 1822 | Value only as the enabler inside AK-MMQ-H8 |
| H2 register fragment ring at J=64 | 1822/1823 | KILLED: already spilling at the cap |
| H4 J=128 at 512 threads | 1822/1823 | KILLED: VGPRs do not fit |
| H6 LDS-staged MMQ write-back | 1822 | fp32 lanes already write 16 B; the ladder's gain came from bf16 run doubling |
| Occupancy-2 MMQ | 1822 | Infeasible at I=128 (x tile 38,912 B) |
| Porting Gluon kernels, reusing amdgcnas or llirSched | 1823 | Blocked on gfx90a (see INF03-GLUON-X) |
| XCD / grid remap | 1823 | Single-die MI210; G17 already closed no-go |
| NH-1 for MMA-FA DKQ ≥ 192 | 1826 | A 256 cap trades copies for scratch spills |
| Peer-read all-reduce | 1825 | No TP on one MI210; revisit when the second MI210 lands, under `mi210-big-model-and-acceleration-roadmap.md` |
| Empty-C4-tile skipping | 1825 | Indexer view is mask-sized in the frozen tree |
| Offline FP4→INT8 expansion | 1825 | Paper's own negative; corroborates DS41 "lever is bytes" |
| GPU nibble LUT, sdot4, q8_1 activations, INT8 MFMA MMQ | 1825 | Already integrated in llama.cpp HIP |
| DS41-T7 GPU path lead | 1825 | 8×64 GB for V4-Flash; DS41 cannot be resident; different stack |
| CPU tinyBLAS set as ladder-derived | 1822 | Not ladder-derived; routed on its own merit via DS41 inbox note 41 (DS41-C52) |
| CPU software prefetch, epilogue hsum staging, cross-core B sharing | Stage 1 | Sequential streams (HW prefetcher); negligible; B already fully reused |
| RVP ownership of register audits | 1826 | INF-48 owns the launch/oracle boundary; the audit lives in INF-03 |
| Operator-declined Stage-2 sources (chipsandcheese ×3, Boehm, amd-brr, HK issues/X posts, llvm #216372, Gluon API docs, gfx942 branch, triton 44f9161a, aiter #179, tokenspeed #1655) | 1822/1823 | Operator decision 2026-09-26; recorded in dive_corrections |
| llvm #170335/#180751/#185604/#205901, issue #131954 | 1826 | Monitor at upgrade time; cited in the P3 runbook row |

## Flagged for operator review (not dismissed)
CDNA5/gfx1250-only mechanisms with no gfx90a counterpart today: TDM descriptor loads, split barriers
(`s_barrier_signal/wait`), workgroup clusters and multicast, `lock_simd` (hwreg 26), async b128 global→LDS, wave32
lane regularity, partitioned LDS, and `ds_load_tr` (intake-1824). They would matter only on CDNA4/5 hardware, and none
is in plan: the second card is also gfx90a.

## Stage-3 completeness gates
- [x] **Stage-2 close-out gate — closed 2026-09-26 by OD-1 (recommendations accepted).** The 1822/1823 surfaced sources are closed (2 ingested
      as 1825/1826; the rest declined by the operator and recorded). The three sources surfaced by the 1825 dive need
      OD-1.
- [x] Every Stage-1 preliminary actionable maps to a plan item or a decline. The GPU H1–H6 and CPU H1–H5 drafts: GPU
      in P2 or the declines; CPU via DS41 inbox note 41 / DS41-C52 (P5).
- [x] Every dive-ledger row (1822: 12, 1823: 6, 1825: 10, 1826: 3) maps to P1–P8 or the declines table.
- [x] Every steering-ledger row is a named item or a decline:
      - seq1 (operator framing) → P1, P2, P5;
      - seq2 (dive both, GGML_IQK_Q8_0 left to the loop) → dives done; no A/B filed;
      - seq3 (gate decision) → 1825/1826 dived, declines recorded, P1-b and P2 marked GATED.
- [x] No plan text quotes a number or mechanism from a `stage1-unverified` entry. intake-1824 is cited only for the
      mechanism names in the flagged list.
- [x] Frozen/pointer status checked: agentic-rocm-kernel-authoring, autokernel-research-loop,
      autokernel-champion-aggregate, deepseek-v41-flash-evaluation, rocm-verify-profile-backend and
      vidya-belief-substrate-program are all active with no "no new checkboxes" marker. The runbook is a doc.
      `gpu-acceleration-path.md` (superseded) and `mi210-q8-dequant-gemv-roofline.md` (MMVQ owner, not MMQ) are not
      used as owners.

## Stage 4 will report
The files changed; the checkbox counts (new open tasks: P1 2, P2 6, P3 1, P5 2, P6 1, P7 1; pre-ticked: P1 1, P2 1); the
edited line (DS41-C52); the correction note (CH-6); the intake-entry updates; `validate_intake.sh` and
`index_state.py --check` exit codes; and the lane close-out (push verified with `git cherry`, worktree and the backup
branch removed).
