# Stage-3 Action Plan — EXL3 Throughput and Serving Closure Addendum

**Session**: `intake-exl3-sglang-throughput-20260925`  
**Created**: 2026-09-25  
**Status**: proposed; operator approval is required before Stage 4  
**Base program**: [`INF-80`](../handoffs/active/exl3-cpu-mi210-implementation.md)  
**Earlier approved plan**: [`intake-stage3-plan-2026-09-25-exl3-cpu-mi210.md`](intake-stage3-plan-2026-09-25-exl3-cpu-mi210.md)

## 1. Decision

The research has reached diminishing returns. The final wave added implementation-critical contracts, but none of its sources provides CPU, HIP, ROCm, gfx90a, or MI210 EXL3 compute code or measurements. Further broad expansion would mostly add NVIDIA variants, adjacent speculative-serving work, or duplicated lineage.

Stage 4 should amend the existing `INF-80` program and the existing DFlash2 handoff. It should not create a second EXL3 program, a new stub, or another domain-index row.

The path remains custom-kernel-first:

1. Freeze native packed EXL3 metadata and independent scalar oracles.
2. Build EPYC and gfx90a operators against that contract.
3. Establish codec-only correctness and throughput.
4. Integrate one complete target into experimental llama.cpp.
5. Measure the whole serving envelope, including c1/c8/c16 decode, prefill, capacity, recurrent state, and later speculative decoding.

The external throughput rows are workload targets and attribution inputs. They are not local pass thresholds until their prompt, output, cache, concurrency, and runtime identities can be reproduced.

## 2. Plan-completeness gates

| Gate | Status |
|---|---|
| Stage-2 close-out gate | PASS — 27 final-wave entries resolved; 86 unique declines and 13 deduplications recorded; no pending source |
| Per-claim second reader | PASS — all final-wave claim anchors accepted after correction |
| Stage-1 preliminary actionables | PASS — THR-1 through THR-4 map to P3/P4 below |
| Dive-derived actionables | PASS — all 88 session entries map in §6 |
| Steering ledger | PASS — all nine rows map in §7 |
| Unverified claims in tasks | PASS — task rationale uses `dive-verified` or explicitly corrected `dive-overturned` records |
| Target handoff status | PASS — both target handoffs are active and neither is a frozen handoff or compatibility pointer |
| Index ownership | PASS — no new handoff; existing `INF-80` and DFlash2 rows remain the sole owners |
| Belief-kernel wiring | PASS — research-intake records already use the registered research-intake adapter; `INF-80` already owns `VB-EXL3-CPU-GFX90A` before local runs |

## 3. Stage-4 handoff edits

### P1 — Amend `handoffs/active/exl3-cpu-mi210-implementation.md` research inventory and settled findings

Append `intake-1563` through `intake-1575` and `intake-1708` through `intake-1782` to the research inventory as the throughput and serving closure corpus. Use grouped ranges and `#record` references rather than duplicating 88 titles.

Append these completed research findings under **Settled research**:

```markdown
- [x] **EXL3-R7 — Freeze the native-packed execution contract.** The strongest transferable implementation pattern is per-logical-matrix metadata plus a plan/bind/run lifecycle over native packed tensors, caller-owned persistent scratch, fixed capacities, and fail-closed codebook/device checks. The CUDA implementations do not transfer to gfx90a; the contracts do. (`intake-1756#00`, `intake-1756#01`, `intake-1757#00`, `intake-1757#01`, `intake-1757#02`) ✅ 2026-09-25
- [x] **EXL3-R8 — Freeze the first real MCG fixture and oracle boundary.** Uniform K4/MCG is the first real fixture. The independent project oracle must cover packed windows and lane placement; generation identity and a quality receipt do not substitute for raw reconstruction parity. Source-available Brandon code remains evidence-only unless license review authorizes reuse. (`intake-1756#02`, `intake-1758#00`, `intake-1758#02`, `intake-1758#03`) ✅ 2026-09-25
- [x] **EXL3-R9 — Freeze the throughput attribution boundary.** Published NVIDIA rates combine target quantization, speculative acceptance, scheduler behavior, graph capture, attention/KV precision, and recurrent-state handling. CPU/MI210 qualification must measure operator and full-stack envelopes separately. (`intake-1563#record`, `intake-1564#record`, `intake-1754#record`, `intake-1779#record`) ✅ 2026-09-25
- [x] **EXL3-R10 — Freeze the full-stack correctness boundary.** Exactness is proposition-specific: packed reconstruction, operator output, recurrent state, verifier acceptance, and complete autoregressive token equality require separate oracles and fail-capable controls. (`intake-1760#00`, `intake-1760#01`, `intake-1760#02`, `intake-1763#00`, `intake-1763#01`, `intake-1765#record`, `intake-1767#record`) ✅ 2026-09-25
- [x] **EXL3-R11 — Close broad literature expansion.** No reviewed source supplies CPU/gfx90a EXL3 throughput or invalidates the custom-kernel path. Reopen research only for actual CPU/gfx90a EXL3 code, a changed ABI/reconstruction rule, evidence invalidating the correctness path, or matched raw evidence that changes a gate. ✅ 2026-09-25
```

### P2 — Tighten EXL3-1, EXL3-3, and EXL3-5 around the packed ABI

Append these acceptance bullets beneath the named tasks:

**Under EXL3-1:**

```markdown
  - Use projection-major native packed tensors without repacking. Give every logical Q/K/V and gate/up/down matrix its own trellis, transform vectors, codebook marker, tensor role, source digest, and local/global expert domain. Unknown or ambiguous mappings fail before allocation. (`intake-1756#00`, `intake-1757#00`)
  - Re-derive the three-instruction MCG window decoder and lane map into project-owned scalar fixtures. Treat the Apache-licensed donor as a second oracle; keep source-available ShapleyMCG code evidence-only unless separately cleared. (`intake-1756#02`, `intake-1758#03`)
  - Pin one real uniform-K4 MCG tensor plus synthetic K1–K8/MUL1/MCG vectors. A fixture passes only when packed-state decode, reconstructed tile, transforms, and full operator output are checked independently. (`intake-1758#00`, `intake-1758#02`)
  - Use nonfinal teacher-logit windows for harness development and reserve the 25-window final panel for one frozen qualification. Keep quality, reconstruction, and performance receipts separate. (`intake-1759#00`, `intake-1759#01`, `intake-1759#02`)
```

**Under EXL3-3:**

```markdown
  - Translate format semantics and lane ownership into wave64; do not transplant CUDA warp32 geometry. The first gfx90a milestone is native packed K4/MCG GEMV matching the scalar and EPYC full operator outputs on the same real fixture. (`intake-1756#01`, `intake-1756#02`)
```

**Under EXL3-5:**

```markdown
  - Expose `plan`, `bind`, and `run` phases. Planning fixes token, route, tile, decode, and prefill capacities; binding maps one caller-owned arena into stable views; `run` performs no allocation. Runtime identity binds model, tensor role, codebook, capacity, scratch, backend, and source digest. (`intake-1756#00`, `intake-1757#02`)
  - Refuse capture-time fallback, capacity overflow, unknown codebook, conflicting MCG/MUL1 markers, exhausted scheduler slices, and ambiguous source mappings. Boundary tests sweep both sides of every tile and scheduler transition. (`intake-1757#01`, `intake-1757#02`, `intake-1772#02`)
  - Benchmark concentrated, spread, and randomized expert routing. Report the route histogram with every sparse-kernel result so a favorable routing distribution cannot stand in for general throughput. (`intake-1758#record`)
```

### P3 — Tighten EXL3-7 into a throughput-parity program

Append beneath **EXL3-7**:

```markdown
  - The mandatory serving grid is bare target plus later MTP/DFlash2 arms at decode concurrency 1/8/16, declared prefill lengths, fixed prompt and output token IDs, no accidental cache hits, and explicit cold/warm state. Report aggregate and per-request decode, full-wall throughput, TTFT, prefill, verifier steps, acceptance by position, resident memory, and context/request capacity. (`intake-1563#record`, `intake-1564#record`, `intake-1754#record`, `intake-1778#record`, `intake-1780#record`)
  - Measure standalone reconstruction, GEMV/GEMM, one layer, bare-target serving, and speculative serving as separate arms. Attribute gains among target bytes, kernel efficiency, scheduling/graph overhead, attention/KV, recurrent state, and accepted tokens per verification step. (`intake-1564#record`, `intake-1779#record`)
  - Use same-box candidate/control interleaving, hard regression floors, absolute reference checks, fail-closed path counters, and raw per-request rows. A differential pass is invalid when the baseline shares the defect. (`intake-1779#00`, `intake-1779#01`, `intake-1779#02`)
  - Preserve the published CIRU and NVIDIA numbers as workload-specific targets. Local success requires matching the reproducible workload envelope and explaining remaining gaps; no external value becomes a CPU/MI210 claim or a universal threshold. (`intake-1563#record`, `intake-1564#record`, `intake-1754#record`)
```

This files the operator direction that CPU/MI210 must reach the useful serving rates. It turns that direction into reproducible local gates without assuming identical absolute performance across different hardware.

### P4 — Tighten EXL3-9 comparator admission

Append beneath **EXL3-9**:

```markdown
  - Reject a W4A16/NVFP4 comparator until its exact module allocation, expert count, pruning plan, teacher revision, non-target precision, tokenizer, runtime, KV format, and evaluation panel are recorded. The official and community artifacts are distinct arms, not one generic “four-bit” baseline. (`intake-1753#record`, `intake-1775#00`, `intake-1776#00`, `intake-1781#00`, `intake-1782#00`)
  - Before admission, verify fused gate/up scale equality or compensate each half, independently reconstruct sampled matrices, reconcile all expected tensors, and run multilingual byte-token probes. A corrupted ModelOpt artifact cannot establish an EXL3 quality advantage. (`intake-1770#00`, `intake-1770#01`, `intake-1770#02`)
  - Keep task scores, teacher-forced KL/top-1, artifact size, resident memory, context capacity, decode, prefill, and serving throughput as separate directed metrics. Only matched teacher/architecture/module coverage can support a codec claim. (`intake-1759#record`, `intake-1775#01`, `intake-1776#01`, `intake-1781#01`, `intake-1782#01`)
```

### P5 — Tighten EXL3-10 full-stack regression

Append beneath **EXL3-10**:

```markdown
  - Require target-only A/A, fresh-process A/A, forced-reject target-argmax, and c1/c8/c16 fail-capable token/logprob hashing before reading speculative output differences. Stable scores alone do not prove deterministic execution. (`intake-1761#record`, `intake-1765#00`, `intake-1765#02`, `intake-1767#00`, `intake-1767#02`)
  - Test packed GDN decode against an independent FP32 sigmoid-beta one-step oracle and a long recurrence. Do not make verification imitate a defective BF16 round trip. (`intake-1762#record`, `intake-1763#00`, `intake-1763#01`, `intake-1763#02`, `intake-1764#00`)
  - State each decided proposition explicitly: valid verifier acceptance, packed operator equality, recurrent-state equality, or complete autoregressive token-sequence equality. A pass on one proposition cannot clear another. (`intake-1760#record`, `intake-1766#record`)
```

### P6 — Amend `handoffs/active/dflash2-block-drafter-experimental-build.md`

Append after **DF2-13**:

```markdown
- [ ] **DF2-EXL3 — Integrate speculative serving only after the EXL3 target passes codec-only CPU/HIP gates.** Bind the exact target and drafter revisions, keep draft and target quant methods separate, and require fail-closed tensor/sidecar loading. For Qwen GDN, test direct ReplaySSM commit over short, long, concurrent, reject-heavy, cache-reuse, uniform, and nonuniform paths. Cap both admission and execution allocation for sliding-window drafters. If GLM is selected, validate hidden-plus-residual contraction only on the DFlash path and verify k→k+1 capture mapping. Report acceptance, verifier cost, target throughput, context capacity, and concurrency separately. (`intake-1768#record`, `intake-1769#record`, `intake-1771#record`, `intake-1777#record`, `intake-1778#record`, `intake-1780#record`)

**LiLiCorr monitor:** Revisit candidate-lattice correction only when the native EXL3 target is stable and ordinary DFlash/DSpark serving has passed correctness and throughput gates. Until then it has no active checkbox; the H100 paper and open SGLang implementation add no CPU/gfx90a evidence. (`intake-1773#record`, `intake-1774#record`)
```

### P7 — Progress record

Append a short entry to `progress/2026-09/2026-09-25.md` recording that Stage 4 applied this addendum, naming the two handoffs and the final validator results. Do not copy external throughput values into the progress log as local results.

## 4. Index and stub decisions

- **New stubs**: none.
- **Domain-index rows**: none. `INF-80` already has exactly one row in `inference-research-index.md`; the DFlash2 handoff already has an owner.
- **Master index**: no edit. This plan adds no operator-only decision.
- **Existing row next action**: no edit. `INF-80` correctly remains at EXL3-1, which this addendum sharpens.

## 5. Intake-entry dispositions for Stage 4

| Entries | Disposition | `handoffs_updated` | Evidence text |
|---|---|---|---|
| `intake-1563`–`1575` | `integrated` | EXL3; DFlash2 where already cross-referenced | P1–P6 absorb the end-to-end throughput, loader, cache/state, and speculative-serving actions |
| `intake-1708`–`1759` | `integrated` | EXL3; DFlash2 for drafter/speculation records | P1–P6 absorb portable CPU/HIP donors, ABI/loaders, serving controls, comparator design, and target/draft fixtures |
| `intake-1760`–`1772` | `integrated` | EXL3; DFlash2 for `1765`–`1771` where applicable | P2/P4/P5/P6 absorb exactness, recurrence, A/A, state commit, allocation, scale, and scheduler-boundary actions |
| `intake-1773`, `intake-1774` | `monitor` | none | Trigger is native EXL3 target stability plus ordinary speculative-serving qualification; no active task before it fires |
| `intake-1775`–`1782` | `integrated` | EXL3; DFlash2 for serving/drafter records | P3/P4/P6 absorb comparator identity, serving contracts, absolute/differential gates, capacity, and acceptance/throughput separation |

For each integrated entry, Stage 4 fills `integration_disposition: integrated`, the exact target filename(s) in `handoffs_updated`, and `disposition_evidence` naming the plan item. For the two monitor entries, Stage 4 fills `integration_disposition: monitor`, leaves both handoff lists empty, and records the trigger above.

All 86 Stage-2g declines and 13 deduplications are already recorded in bearing entries and `.research-session.json`; Stage 4 must not turn them into tasks.

## 6. Source-ledger coverage

| Intake set | Plan disposition |
|---|---|
| `1563`–`1567` | P1/P3: full serving envelope, exact target/draft identity, and throughput attribution |
| `1568`, `1575`, `1708`, `1718` | P1/P2: CPU/reference donors, type-safe packed ABI, native gfx90a implementation |
| `1569`–`1574`, `1709`–`1724` | P2/P3/P5/P6: packed cache/workspace, loader completeness, recurrent state, batch/layout, and speculative controls |
| `1725`–`1737` | P2/P5/P6: draft architecture, packed-operator dispatch, loader mapping, and component-level qualification |
| `1738`–`1755` | P1/P3/P4/P5/P6: EXL3/W4A16 evidence boundary, full-stack receipts, loader guards, quality and speculative serving |
| `1756`–`1759` | P1/P2/P3/P4: packed ABI, MCG oracle, real fixture, quality panel, routing distributions |
| `1760`–`1767` | P5: proposition-specific exactness, FP32 recurrence, forced reject, A/A, and fail-capable concurrency |
| `1768`–`1769`, `1771` | P6: state commit, GLM contraction/capture, paired sliding-window allocation |
| `1770`, `1772` | P2/P4: comparator scale admission and defensive scheduler boundaries |
| `1773`–`1774` | Monitor in P6; no active checkbox |
| `1775`–`1782` | P3/P4/P6: exact comparator identities, serving contracts, absolute gates, capacity, and acceptance/throughput separation |

Every recommended action in the 88-entry session corpus is represented by one of these rows or by the recorded saturation declines. Architecture-specific CUDA instructions, Blackwell rates, superseded fixes, generic tooling, and additional unmatched artifacts are explicit declines rather than implementation tasks.

## 7. Steering-ledger coverage

| Seq | Operator direction | Plan disposition |
|---:|---|---|
| 1 | Ingest the CIRU EXL3/SGLang artifact | Closed by `intake-1563`–`1566`; P1/P3 consume it |
| 2 | Reach the useful published throughput | P3 is the local throughput-parity program |
| 3–8 | Proceed with recommended research waves | Closed research authorizations; the resulting entries map in §6 |
| 9 | Stop after this wave if diminishing returns and proceed to Stage 3 | P1 records saturation; no further broad wave; this plan is Stage 3 |

## 8. Validation required in Stage 4

1. `python3 .claude/skills/research-intake/scripts/validate_intake.py`
2. `bash scripts/validate/validate_intake.sh`
3. `python3 scripts/handoffs/index_state.py --check`
4. `python3 scripts/vidya/cli.py cite-check --as-of <stage4-timestamp>`
5. Confirm only the plan-named handoffs, intake index/session state, and progress file changed.
6. Confirm production `llama.cpp` and the kernel store remain untouched.

## 9. Exact Stage-4 write set

- `handoffs/active/exl3-cpu-mi210-implementation.md`
- `handoffs/active/dflash2-block-drafter-experimental-build.md`
- `research/intake_index.yaml`
- `.research-session.json`
- `progress/2026-09/2026-09-25.md`

No handoff index, master index, production kernel, chapter, adapter registry, or new stub is in scope.
