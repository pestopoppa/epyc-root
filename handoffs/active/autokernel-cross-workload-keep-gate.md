# AutoKernel Cross-Workload Keep Gate — census, blast-radius screen, multi-workload non-regression

**Status**: ACTIVE / STUB. The specification is complete. No implementation, build, inference or benchmark has been authorized or run.
**Created**: 2026-09-15 by research-intake Stage 4, at the operator's request. The steering ledger is in `.research-session.json` seq 6–8 of the noninf-20260914 lane. Operator, verbatim: *"seems like something that should be urgently built into autokernel. Can you write a detailed exposition of the matter along with your recommended spec as a distinct handoff please?"*
**Owner**: not yet assigned. Proposed owner: the INF-73 implementation owner (`autokernel-unified-20260908`). The subject is that program's serial controller and its required-target validation.
**Categories**: autonomous_research, hardware_optimization, benchmark_methodology
**Index row**: `inference-research-index.md` → INF-75 (proposed). **Domain**: inference research.
**Related (Deps edges)**:
- **INF-73** [`autokernel-unified-surface-program.md`](autokernel-unified-surface-program.md) is the parent.
  - It owns the serial controller, required-target validation, U2 floors, U3 oracle extension, §8.17C validation batch and OP-41.
  - This handoff specifies two design items that point here from that file.
- **INF-66** [`autokernel-rebuild-program.md`](autokernel-rebuild-program.md) supplies:
  - R23-48 (LOO), R23-53 (Q4_K-gated dead weight), R23-54 (serving-gate cadence), R23-55 (floor unit), R23-57 (headline admissibility), and the R23-28/29 transfer lessons.
- **INF-65** [`autokernel-champion-aggregate.md`](autokernel-champion-aggregate.md) supplies:
  - FOLD-2 G4 dispatch probe, the DO-NOT-FOLD ledger, and the 732389d6 three-workload standing.
- **INF-70** [`cpu-decode-roofline-program.md`](cpu-decode-roofline-program.md) supplies:
  - the `GGML_CPU_PROF` per-node census, the SYNC-17 knobs, and the sync17-fix2 regression.
- **INF-74** [`autokernel-concurrent-target-coordination.md`](autokernel-concurrent-target-coordination.md): the census forwards and non-regression arms are stage claims under its coordination.
- **EVL-47** [`vidya-belief-substrate-program.md`](vidya-belief-substrate-program.md): write-side wiring for census and classification records (task AKX-P4c).

> **Revision anchors.**
> - Root claims are cited against lane worktree `noninf-20260914` @ `1d9d31e5`, which matches origin/main.
> - Research code is cited at `epyc-inference-research` **`94c75914`**. The shared clone's HEAD `ae8e5ef9` does NOT contain it, so read it with `git show 94c75914:<path>`.
> - ggml source is cited at champion `ef81196d5` (`/mnt/raid0/llm/tmp/champ2`).
> - `AK/` means `scripts/kernel_rnd/autokernel/` in the research repo.
> - `NOT-FOUND` means the thing was searched for and does not exist at that revision.

---

## Start here

| task | what to do |
|---|---|
| **AKX-P0a** | Build the per-workload census producer out of the existing FOLD-2 G4 dispatch probe plus the GGUF `WorkloadCensus`. It needs no kernel patch (§6). |
| **AKX-P1** | Replay the screen observe-only on the historical keep set. Acceptance fixture: 732389d6 and sync17-fix2 (§12). |
| **Operator** | Four decisions in §13. None blocks P0 or P1. |

---

## 1. Operator decisions already taken — recorded, not re-opened

| decision | record |
|---|---|
| **ONE champion per production kernel tree stays the rule for SOURCE.** | Ratified in `agents/shared/OPERATING_CONSTRAINTS.md:126-131`. The reconcile incident is in `autokernel-champion-aggregate.md:24-33`. |
| **Per-model kernel forks: REJECTED.** Each fork multiplies merge-back, freeze and upstream-sync cost. | Operator, 2026-09-15 (steering seq 6–7). §3 below. |
| **ERA-style branching trees: DECLINED.** The operator said "agreed". | Steering seq 7 and `decisions_recorded` in `.research-session.json`. ERA's actual shape (executable in-loop scoring, post-hoc external comparison) is `intake-1370#record`. |
| **Model specialization is sanctioned in three forms only:** (1) runtime dispatch on a discriminator visible to the kernel, (2) a per-model/per-surface launch recipe, (3) per-model BUILD VARIANTS of one source commit. | Operator, 2026-09-15. §4 below. |
| **The fix is a screen plus a gate, not a lineage change.** | Operator: "should be urgently built into autokernel". |

---

## 2. Problem statement

The operator, verbatim (steering seq 6): *"sometimes autokernel finds keeps while optimizing a specific model which actually cause regressions in the champion for another model."*

AutoKernel decides a keep on **one target's** A/B. The keep then lands on the **one shared champion**, which every production workload runs.

Nothing at keep time asks what the patch does to the other workloads:
- The required-target validation that does exist runs **after** the keep has landed.
- It fails a row only on a **decisive** negative.
- A failed aggregate does not refuse or revert the keep (§2.3).

### 2.1 Recorded instances

**Instance 1 — champion `732389d6` vs production-consolidated-v9. Same kernel, opposite signs.**
Source: `autokernel-champion-aggregate.md:54-65`. The claim derivation is `progress/2026-09/2026-09-03-ak-rebuild-20260828.md:86-104`.

| workload | surface / recipe | result | evidence class |
|---|---|---|---|
| `gemma-4-26B-A4B-it-Q4_K_M` | dec-b4, recipe `gpu-production-model-direct-ab` | **+7.206% DECISIVE**. 174.26→186.76 t/s, 20 pairs, floor 0.456% | Bench-class paired A/B with a calibrated A/A floor. `AK/loop/historical_trajectory.py:130-138` labels it `era="gpu-cross-model-transfer"`. **The production recipe runs this model on CPU** (2 NUMA instances, MTP k=2, lean `model_registry.yaml:1616-1653`, no `device:` key), so this cell is **not** that workload's production-optimal configuration. Under `MEASUREMENT.md:156-165` it is an addendum, not a promotion argument. |
| `Qwen3.8-27B-Q8_0` (production `architect_general`, ROCm0) | dec-b4 (prefill) | **−1.414% DECISIVE**. 66.09→65.00 t/s, 20 pairs, floor 0.949% | Same class. It is a bench surface that cannot see DFlash2's decode effect (R23-26, `autokernel-rebuild-program.md:1420-1427`). |

Reading of this instance:
- The Q4_K keeps `7d2ea88b` (MMVQ crossover) and `732389d6` (Q4_K weight-block hoist) are hard-gated on `GGML_TYPE_Q4_K` and are therefore inert on Q8_0 (`2026-09-03 progress:49-62`, R23-29).
- The residual −1.4% on the 27B is **attributed** to the aggregate's shared DFlash2/feature machinery (`autokernel-champion-aggregate.md:61-65`).
- That attribution is an interpretation. **No dispatch or coverage evidence was recorded for it.** Producing that evidence is what this handoff is for.
- A related audit (R23-53, `autokernel-rebuild-program.md:2353-2361`): 22 of 52 historical tg128 keeps are Q4_K-gated and cannot fire on the Q8_0 production target. The product of solos was +252%; the MEASURED headline was +5.6%.

**Instance 2 — `inf70/sync17-fix2 @ 2516c9807`. Default-ON knobs are the regression.**
- **Claim:** −2.136%. Ratio 0.9786, CI [0.9771, 0.9804], p=0.0286, n=4v4 in one hot session, 24/24 outputs byte-identical.
- **Sources:**
  - DO-NOT-FOLD ledger, `autokernel-champion-aggregate.md:700-710`
  - RETEST-1 table, `autokernel-rebuild-program.md:1884`
- **Decomposition:**
  - C→P (the FIX-3 yield alone): −1.883%
  - P→F (the column split alone): −0.258%
  - The SYNC-19 model predicted +3.31%, so the sign was wrong.
- **Knobs on that lineage** (`cpu-decode-roofline-program.md:1630-1642`): `GGML_SCALE_SPLIT`, `GGML_SOLO_YIELD_ROWCOL`, `GGML_TINY_SOLO_CLAMP`. Which two are default-ON at `2516c9807` must be read from that commit. The ledger does not name them.
- **Relevance here:** this is a **fold-time** hazard, not a cross-model leak inside one run. A sweep that folds an "unfolded CPU branch" would bring in unconditioned default changes to shared CPU threading. Output identity is blind to that class, because outputs stayed byte-identical.

**Instance 3 — the transfer study: kernel regime changes with shape, so sign changes with surface.**
- R23-5 (`progress/2026-09/2026-09-01-ak-rebuild-20260828.md:9-40`): one change measured +17.259% on tg128, +3.834% on dec-b2, +1.178% on dec-b4, and **−1.462% (decisive) on dec-b8**. rocprofv3 shows the dominant kernel moving from MMVQ `ncols_dst=1`, to `ncols_dst=2`, to MMQ.
- The 1.5B screen model "dispatches no Q8_0 dequant and no gated_delta_net at all" (`2026-09-03 progress:26-32`).
- **This matters for the census:** even within one model, the fired-kernel set is a function of **batch shape**. A census must cover the recipe's shape envelope, not one decode token.

### 2.2 Why this is structural, not bad luck

The loop optimizes a scalar on one workload. The shared champion is judged on a vector of workloads.

A keep can pass its own gate and still lower another workload's value in three ways:
- **Unconditioned code:** the change fires on every workload.
- **A shared discriminator:** the change is gated on a property both workloads have.
- **Shared machinery with no discriminator at all.**

A later keep can also change what an earlier keep's code sees (§5). The measured precedent: a +1.0% lever became −1.39% after two later levers (R23-48, `autokernel-rebuild-program.md:2362-2372`).

### 2.3 What exists today, and the gaps

| exists (research `94c75914`) | what it does | gap for this problem |
|---|---|---|
| `AK/loop/serial_run.py:1196-1278` `_required_source_validation` | Folds current-tip rows for every `production`-enrolled target and every retained keep-author target (`:1222-1228`). The aggregate is `pending`/`failed`/`passed` (`:1250-1252`). | Runs **after** the keep lands on the shared tip. It is refreshed after child batches (`:1767`, `:1957`). A `failed` aggregate's only in-repo consumer found is `_pending_source_loo` (`:1285-1288`), which withholds LOO. **Nothing refuses or reverts the keep.** By `intake-1367#01` ("an external checker is insufficient if its output does not gate the loop"), today's row is an annotation, not a gate. |
| `AK/loop/surface_validation.py:110-135` `classify` | The intended target must PROMOTE. A non-author target uses `fold2_gates.ab_verdict`. | `AK/loop/fold2_gates.py:172-176` fails **only on a decisive negative**. A −0.9% move on a 0.949% floor passes, and many sub-floor losses compound unseen. This is "not demonstrably worse", not non-inferiority. |
| `AK/loop/serving.py:633-642` `check_unit`; `:1606-1622` `FloorReading.gate_floor`; `FloorUnitMismatch` `:592` | Floor/effect unit equality is enforced, and a missing `n` refuses (R23-55, research `eb8a88de`). | Reused as-is. It is the unit guard this gate needs. |
| `AK/loop/serving.py:1389` | `decisive = abs(effect)*100 >= floor_pct`. | No one-sided or non-inferiority form exists. A floor comparison is not the Annex K e-process (§8.1). |
| `AK/loop/fold2_gates.py:195-208` `run_dispatch_probe` + `:133-152` `parse_scheduler_graph` | `llama-bench -p 0 -n 16 -ngl 99 -r 1 -o json -v` under `GGML_SCHED_DEBUG=2`. Parses `node #…(OP)…[BACKEND]` into op × backend counts. Vacuous-pass guard at `:155-169`. | Hand-run and 27B-specific. Decode shape only. No types, shapes or fired kernels. **It produced the FOLD-2 G4 "27,516 nodes" observation** (`autokernel-champion-aggregate.md:653-661`; the literal 27,516 exists only in `AK/loop/test_fold2_gates.py:89`). |
| `AK/execution/t0_provider.py:2367-2397` `parse_sched_trace`, `:3157-3205` `collect_dispatch_trace` | A second scheduler-trace parser. Declared scope is `inter_backend` only (`:1408-1424`). | Explicitly cannot see kernel selection inside a backend (`:296-304`). |
| `AK/controller/workload_contract.py:101-145` `WorkloadCensus` / `read_census` | Tensor-type counts from the GGUF plus architecture, n_embd and dominant quant. | Weights only. No ops, shapes, backends or fired kernels. Not stored on `TargetRevision` (`AK/loop/campaign.py:427-440`). |
| `AK/evaluator/surface.py:1401` `derive_affected_surface`, `AffectedSurface` `:1325` (axes backends, link_targets, op_names, kernel_symbols, dispatch_predicates `:243-257`) | A diff→files→objects→symbols→ops→backends extractor with depfile provenance (`:765`). | Its symbol/build inputs are "a seam" with no producer (`AK/execution/t0_provider.py:275-282`). It is off the loop path (`AK/FOOTPRINT.md:186`). |
| `AK/controller/champion.py:324-340` `CompositionEvidence`; `compatibility` `:784-859`; `compatible_groups` `:862-877` | A composition-conflict schema with files/hunks/symbols/flags/`dispatch_predicates`. | Off the loop path (`AK/FOOTPRINT.md:208`). It never ran in a campaign (`autokernel-champion-aggregate.md:79-88`). Reusable as the footprint schema. |
| `AK/loop/source_loo.py:34-222` `execute_surface`, `omission_disposition` `:19-31` | One reverted-keep arm per keep on a surface, plus a rebaseline. | Reused at FOLD (§9). |
| `AK/loop/gates.py:88-134` `op_correctness` | `test-backend-ops -o MUL_MAT`. "53 seconds measured" (`:23`). | **Not a model forward.** Dispatch counters cannot ride it. `deterministic` (`:137-158`) runs llama-bench ×3 with `-n 8` but compares only return codes (`:157`). No token identity exists in the loop. |
| Operator doctrine: CLAUDE.md step 3 "Validate no regressions vs production (GPU + CPU)" | A promotion-time obligation. | Stated at promotion, not at keep. No mechanism is named. |

**Summary of the gap:** the loop has the pieces:
- unit-safe floors
- a dispatch probe
- a GGUF type census
- a diff→surface extractor
- a composition-conflict schema
- LOO
- a post-hoc multi-target row

What it lacks: (i) a per-workload census of what each graph **executes**, (ii) a proof of inertness, (iii) a non-inferiority statistic, and (iv) a refusal wired to the keep.

---

## 3. Why not per-model kernels or branching trees

| alternative | what it would buy | why it is rejected |
|---|---|---|
| **Per-model kernel forks** (one champion branch per model) | No cross-model interference by construction. | Every production tree is FROZEN and versioned-past (CLAUDE.md:48-53). N forks means N freeze runbooks, N upstream syncs, N promotion candidates, and N×M merge-back decisions for every shared fix. The incident that ratified ONE champion was exactly two lineages drifting (INC-20260831-champion-lineage-fork, `autokernel-champion-aggregate.md:24-33`). **Rejected by the operator 2026-09-15.** |
| **ERA-style branching tree** (keep a population of lineages, pick the argmax) | Exploration breadth. | ERA's retention is an in-loop executable score over author-built splits, with external comparison post hoc (`intake-1370#record`). It has no promotion step, so the merge-back problem is outside its scope. For a frozen kernel set it recreates lineage divergence. **Declined, and the operator agreed.** A parked-branch variant is recorded with a revisit trigger (INF-73 §5). |
| **Model-specific compute branches inside the one kernel** (sanctioned form 1) | Same benefit as forks, at the dispatch site. | Sanctioned. The cost is proving the branch's discriminator actually separates the workloads, which is Spec A/B here. |

The operator's own question (seq 6) was *"what's the difference between having multiple kernels vs model specific compute branches within a single kernel?"*

The answer that motivates this spec:
- **Nothing, for dispatch.** A discriminator branch compiled into one source tree is a per-model kernel at runtime.
- **Everything, for lineage.** There is one merge, one freeze, one upstream sync.
- The price of the in-tree form is that inertness on the other workloads must be **proven**, because it is no longer guaranteed by separate binaries.

---

## 4. Taxonomy of specialization

| form | mechanism | merge-back cost | when required | existing EPYC example |
|---|---|---|---|---|
| **(1) Runtime dispatch on a kernel-visible discriminator** | A branch on quant type, tensor shape, architecture, backend, thread count or CPU feature, inside one source tree. | **Zero.** It is one commit on the champion. | The mechanism's benefit or harm depends on a property the kernel can see. | Q4_K-gated keeps `7d2ea88b`/`732389d6` (`2026-09-03 progress:49-62`). The HIP MMVQ/MMQ crossover is chosen per type and `ne11` (`ggml/src/ggml-cuda/mmvq.cu:715-727`, `mmq.cu:296-313` @ ef81196d5). The CPU IQK path is gated per type and shape (`ggml/src/ggml-cpu/iqk/iqk_dispatch.cpp:229-257,382-417`). |
| **(2) Per-model / per-surface launch recipe** | Env knobs, flags, threads, placement and speculation in a codified recipe (recipes are code in git). | **Zero** for source. Recipe hash is part of identity (INF-73 §3.3). | The discriminator is not kernel-visible (e.g. THP, NUMA), or the knob is a runtime gate. | `GGML_NOHUGEPAGE_PROCESS=1` is CPU ON / GPU NOT SET (`autokernel-champion-aggregate.md:767-787`). `GGML_IQK=1` is a **runtime env gate**, not a CMake option (`autokernel-rebuild-program.md:179-183`). Per-role `-t/-np/--device` flags are in lean `model_registry.yaml`. |
| **(3) Per-model BUILD VARIANT of one source commit** | CMake defines or a PGO profile applied to **the same commit**, giving distinct binaries. | **Low.** One source lineage. N build recipes to reproduce and digest at promotion. | The specialization is compile-time (a define, a profile) and no runtime discriminator is cheap enough. | `ef81196d5` ships digested CPU and HIP builds recorded per surface (`cpu-decode-roofline-program.md:2502-2505`). v9 CPU vs HIP builds are symbol-identical to production (`autokernel-rebuild-program.md:185-190`). `build-hip` and `build-hip-mmqoff` exist in `/mnt/raid0/llm/tmp/champ2`. **Instrument builds are also form (3):** the `GGML_CPU_PROF` census build and the coverage build proposed in §6 are variants of one commit labelled NOT-TO-FOLD. |
| **(✗) Per-model source fork** | Separate branch or tree per model. | **High and multiplicative.** N freezes, N syncs, merge-back per shared fix. | Never. | **REJECTED** 2026-09-15. |

**Rule this handoff enforces:** a keep may specialize only through (1), (2) or (3). A keep that regresses a workload it touches must be converted into one of those forms, and then re-screened.

---

## 5. How a keep leaks across workloads

Notation: workload `w` is an author target or production workload. Patch `p`. `touch(p,w)` means code or data changed by `p` executes, or changes a decision, in `w`'s serving forward.

| class | description | example | can the screen PROVE inertness? | what catches it |
|---|---|---|---|---|
| **(a) Unconditioned change** | Code on a path every workload executes. | A generic `ggml_graph_compute_thread` change; sync17-fix2's default-ON yield/column split. | **No.** It is TOUCHED wherever the path executes. Inert only where the workload's loaded objects are byte-identical (T0, §7). | The Spec C non-regression gate on every TOUCHED workload. |
| **(b) Conditioned on a discriminator the other workload shares** | Gated on type/shape/backend, but `w` has that property. | A Q4_K keep on `Qwen3-VL-30B-A3B Q4_K_M` (ROCm0, a production workload, lean registry `:1654-1683`) or `Qwen3.5-122B UD-Q4_K_M`. A decode-shape keep on a recipe whose `np`/draft width reaches the same `ne11`. | **Yes, when the discriminator does not match `w`.** Differential coverage shows the guarded body never executes and the predicate outcome is unchanged (T1, §7). When it matches, TOUCHED. | Census intersection plus the gate. The remedy is to **narrow the discriminator** (add shape/arch/backend terms) and re-screen. |
| **(c) Shared machinery, no discriminator** | Allocator, scheduler split policy, threading/barriers, graph build, KV cache, fusion rules, spec-decode plumbing. | The attributed DFlash2/feature machinery residual (−1.414% on 27B). THP/page policy. | **Rarely.** Machinery executes everywhere by definition. Inert only by T0 object identity, or where the workload's recipe disables the path (a recipe-visible discriminator, form 2). | The gate. The remedy is a recipe knob (form 2), a runtime discriminator (form 1), or refusal. |
| **(d) Interaction at composition** | Keep A changes a predicate that routes `w` into keep B's code, or removes the stall B was paying for. | R23-48's +1.0% → −1.39% lever (`autokernel-rebuild-program.md:2365-2368`). | **Not per keep.** A per-keep INERT on `w` says nothing about the composed tree. | Spec D: re-census and non-regression on the **composed** candidate, plus LOO and the AK-GH-1 count. |

Two further failure shapes the screen must not miss:

- **Env-knob fall-through.** `GGML_TINY_SOLO_CLAMP` gated 10 ops, and outputs stayed bit-identical, so an output-diff oracle cannot see this class (INF-73 §3.3, `autokernel-unified-surface-program.md:709-712`, `:865-867`). The footprint must include knob read sites, and census records must carry effective env.
- **Callback-induced dispatch change.** A census taken with a per-node eval callback answering `ask=true` splits the graph into single-node views (`ggml/src/ggml-backend.cpp:1697-1711`). That defeats CPU fusion (`ggml-cpu.c:4054-4066`), tiny-solo collapsing (`:5088-5112`) and HIP fusion (`ggml-cuda.cu:2994`). **Such a census would report kernels production never runs, and miss fused ones.** The fired-kernel census must be callback-free.

---

## 6. Spec A — workload census

### 6.1 Workload set

**The set is resolved, not hand-listed.** Source: the serial campaign's resolved targets (`AK/loop/serial_roster.py:15-165`; `TargetSpec` `AK/loop/campaign.py:160-176`; `TargetRevision.enrolled_as`/`workload_signature` `:427-440`).

Membership rule, which reuses the existing rule at `serial_run.py:1222-1228` rather than inventing one:
- every `production`-enrolled target, at its **production-optimal registered recipe** (`MEASUREMENT.md:156-165`);
- plus every target that authored a keep retained on the tip.

Seed or candidate targets (e.g. GLM-5.3-Flash) are advisory unless a keep they authored is retained (`autokernel-unified-surface-program.md:1300-1310`).

Snapshot of the production LLM fleet on the llama.cpp kernel tree, from lean `/mnt/raid0/llm/epyc-orchestrator/orchestration/model_registry.yaml`. The file was compiled 2026-09-03 (`:13`). **Re-resolve it at implementation**, because INF-73 AKU-12c reports "seven production workloads plus the explicit GLM candidate" in the generated full-SMT campaign (`autokernel-unified-surface-program.md:3500-3506`).

| # | workload | quant | arch | backend / recipe | spec | registry |
|---|---|---|---|---|---|---|
| W1 | Qwen3.8-27B | Q8_0 | dense hybrid (GDN) | ROCm0, `-ngl all -t 8 -fa on`, np 1 | MTP k=8 | `:1684-1729`, `:2688-2747` |
| W2 | Qwen3-VL-30B-A3B + mmproj F16 | Q4_K_M | MoE | ROCm0, 1 slot | none | `:1654-1683` |
| W3 | Qwen3.6-35B-A3B-MTP | Q8_0 | MoE | CPU, 2 NUMA instances | MTP k=4 | `:1542-1587` |
| W4 | gemma-4-26B-A4B-it-ORIG + assistant-v6 Q8_0 | Q4_K_M | MoE | CPU, 2 NUMA instances, ubatch 512 | MTP k=2 | `:1616-1653` |
| W5 | Qwen3.5-122B-A10B | UD-Q4_K_M | MoE hybrid | CPU 0-95 single instance | MTP k=4 | `:1730-1766` |
| W6 | Qwen3-Next-80B-A3B | Q4_K_M | hybrid SSM+MoE | CPU, 2 instances | none (OPTIMUM) | `:1767-1803` |

Out of scope:
- **Embedders** (f16 encoders, CPU). Include them when a keep touches encoder-only ops.
- **Speech kernels** (whisper.cpp / qwentts.cpp). These are separate frozen trees with their own ggml generation, and a llama.cpp keep cannot reach them.

**Registry defects that bear on the census.** For `worker_math` and `toolrunner`, the `roles` entries still describe old models (`:2369-2379`, `:2613-2632`), while `server_mode` routes them to W4 (`:1630-1633`). The census keys on `server_mode`, which is what launches. The registry defect belongs to the registry owner.

### 6.2 Data model — `epyc.autokernel.workload_census.v1`

```text
WorkloadCensus.v1 (one per (workload, champion commit, build variant, recipe))
  identity:
    workload_id, workload_signature          # TargetRevision.workload_signature
    model: {path, sha256, architecture, n_embd}          # reuse controller/workload_contract.WorkloadCensus
    recipe: {recipe_ref, recipe_sha256, effective_env{}, argv[], threads, np, ubatch, draft_max, device}
    kernel: {tree, commit, build_variant, dso_digests{name: sha256}}   # every DSO actually loaded (verify_ggml_linkage)
    host: {cpu_model, isa_flags, gpu cc / gfx, driver}
    census_tool: {name, version, argv, env}
  weights:                                   # zero compute (GGUF header)
    tensor_types{type: count}, dominant_quant, buffer_types{name: count}   # CPU vs CPU_REPACK
  graph:                                     # observed, callback-free
    shape_envelope: [ {phase: prefill|decode|verify, n_tokens (ne11), n_seq} ... ]   # from the recipe
    per_shape: { nodes_total, splits, op_backend{(op, backend): count},
                 op_type{(op, dst_type, src0_type, src1_type): count},
                 op_shape_classes{(op, src0_type, ne-bucket): count} }
  fired:                                     # the part a proof can use
    hip_matmul_routes{(route, type, ne11): count}      # GGML_CUDA_LOG_MMVQ_ROUTE=2
    cpu_prof_paths{...}                                 # optional GGML_CPU_PROF instrument build
    coverage: {build_variant: coverage, profile_sha256, executed_lines_ref, branch_outcomes_ref}
  validity:
    observed: bool, vacuous_guards{nodes_total>MIN, expected_ops_present, device_seen, n_shapes==len(envelope)}
    freshness_key = H(model.sha256, recipe_sha256, kernel.commit, build_variant, dso_digests, host.isa/gpu)
```

### 6.3 How it is produced — the kernel-patch question

**Finding: the census needs NO kernel source patch.** Every layer except "fired kernel" comes from existing, unmodified mechanisms. "Fired kernel" comes from a **build variant of the same commit** (form 3), not a source change.

| layer | producer (existing) | patch? | limits |
|---|---|---|---|
| weights | `controller/workload_contract.read_census` (`:145`) extended with buffer types | no | Zero compute. |
| op × backend per shape | `fold2_gates.run_dispatch_probe` generalized: `GGML_SCHED_DEBUG=2` + `-v`. The line format is `node #%3d (%10.10s): %20.20s (%5.5s) [%5.5s %8.8s]` (`ggml-backend.cpp:975-990`; parsed at `fold2_gates.py:57-58,133-152`; `t0_provider.py:2367-2397`). Node/split totals come from `sched_reserve: graph nodes = %d` (`src/llama-context.cpp:682-692`). | no | No types or shapes in the line. Must run per shape in the envelope: `-p <ubatch>`, `-n` decode, and the np/draft widths. **Must use `llama-server`/`llama-bench` under the registered recipe**, because llama-bench cannot drive speculation (`MEASUREMENT.md:160-163`). Verify widths then need a short server request. |
| op × type × shape | A census-only pass through a custom eval callback that holds the sched handle and calls `ggml_backend_sched_get_tensor_backend` (`ggml-backend.h:335`). The stock `llama-eval-callback` (`examples/eval-callback/eval-callback.cpp:56-57`, `common/debug.cpp:171-186`) prints dst type only, no backend. | no (a tool, not ggml) | **Perturbs dispatch.** `ask=true` splits the graph (§5). Use it ONLY for the type/shape table, never for fired kernels. The tool build happens in an experimental worktree, never in the production tree. |
| HIP fired matmul route | `GGML_CUDA_LOG_MMVQ_ROUTE=2`. Prints route ∈ {CUBLAS_PRECHECK, MMVF, MMF, MMVQ, MMQ, CUBLAS, *_MMID} with type, cc, ne, ne11 (`ggml-cuda.cu:1822-1862,1893-1909,1941-1960`). The knob is also present in production v9 (`ggml-cuda.cu:1814`). | no | Does not cover fused MMVQ paths that bypass `ggml_cuda_mul_mat` (`ggml-cuda.cu:3537-3888`). |
| CPU fired path (partial) | The `-DGGML_CPU_PROF` instrument build: `GGML_CPU_PROF_NODES` TSV, `[mm_prof]`, `[iqk_prof]` (`ggml-cpu.c:3620-3635,3854-3992`; `iqk_dispatch.cpp:108-128`). Already used for the INF-70 per-node census (`cpu-decode-roofline-program.md:328-342,782`). | no (form-3 variant) | Not defined in any CMake file, so it is passed via CFLAGS. Path classes are dense/MoE/lm_head, not the exact kernel. SYNC-21 profiler-overhead caveat (`cpu-decode-roofline-program.md:1167-1172`). |
| **Executed lines and branch outcomes (the proof layer)** | **Coverage build variant** (`--coverage`, or clang `-fprofile-instr-generate -fcoverage-mapping`) of the same commit with the same CMake defines as the production variant. Use `-fprofile-update=atomic` for threaded CPU runs. | no (form-3 variant) | Host code only. HIP device kernels are covered through their host launch sites. Inlining/macro attribution is approximate at line level. Counter overhead makes it correctness-surface only. Whether ROCm-clang `.cu` host-side coverage links cleanly in `ggml-hip` is **UNVERIFIED** and is P0 acceptance item AKX-P0c. |

**What would need a kernel patch:**
- which repack variant sits in `src0->extra`
- whether IQK accepted a node or fell through at runtime (`iqk_dispatch.cpp:257,417`)
- a llamafile-sgemm refusal (`ggml-cpu.c:1386-1397`)
- in-kernel knob branches (`GGML_QSPLIT`, `GGML_VEC_Q8K`, `GGML_ROWCOL_SPLIT`)

Line/branch coverage observes all of these without a patch. The in-kernel alternative is a compiled-out `AK_DISPATCH_COUNT(site)` macro. That **is** a champion source change and goes through the experimental workflow; see §13 Q4.

### 6.4 Storage, freshness, era

- **Store:** `/mnt/raid0/llm/autokernel/loop-memory/census/<workload_id>/<freshness_key>.json`. This sits beside the floors (`serving.write_floor` pattern, `serving.py:1644-1734`). Content-addressed, append-only, with the coverage profile referenced by sha256.
- **Invalidation:**
  - A census is **invalid** when any freshness-key input changes: model sha, recipe sha (including effective env), champion commit, build variant, any loaded DSO digest, or host ISA/GPU.
  - A stale census **cannot** classify. The pair is UNKNOWN, which fails closed to TOUCHED.
  - It is never carried forward and never rescaled. This is the same laundering class as INF-73's re-baselining rule (`autokernel-unified-surface-program.md:698-704`).
- **Era:** the census is a structural observation, not a rate claim, so it has no instrument era. It **binds the kernel commit and host**. After a reboot or BIOS change (R23-64/65), the host key changes and censuses regenerate.
- **Base census cadence:** one census per workload per **champion-of-record / validated-candidate advance**, not per keep. Per-keep work is the differential in §7.

### 6.5 Compute class

| step | class | resource |
|---|---|---|
| GGUF type census | **zero-compute** | File read. |
| scheduler-debug, route-log and coverage forwards | **correctness-surface compute**: model load plus one short forward per envelope shape | Holds the workload's device. Occupies CPU DRAM bandwidth and cores. **Is a contaminant for any concurrent benchmark window**, so it goes through the same resource claim as an oracle (`cpu_region_lock`, GPU flock). It is not a benchmark window and yields no rate. |
| building instrument variants (coverage, CPU_PROF) | **build compute** | A pinned, locked build slot. Never unlocked: 19 of 21 build scripts are still unlocked (MEAS-2, `autokernel-unified-surface-program.md:1118`). |

**Can the census ride the existing correctness oracle?** No, not today:
- The loop oracle is `test-backend-ops -o MUL_MAT` with no model graph (`gates.py:88-134`).
- `deterministic()` runs llama-bench `-n 8` on the production-variant build and checks only return codes (`gates.py:137-158`).

**Recommendation:** make the census forward **the** loop's model-level correctness step. Run it on the coverage variant and add greedy token identity against the anchor variant. The loop currently lacks token identity, and `evaluator/correctness.py:2046-2107` has it but is not wired into `loop/run.py`. One correctness-surface forward then buys two things.

---

## 7. Spec B — patch footprint and intersection

### 7.1 Footprint extraction — `epyc.autokernel.patch_footprint.v1`

Static, zero-compute. Computed over `git diff parent..keep` (or the composed range at FOLD). It reuses `CompositionEvidence` fields (`controller/champion.py:324-340`) and `derive_affected_surface` (`evaluator/surface.py:1401`), which this task finally gives a producer.

```text
PatchFootprint.v1
  range: {parent, child, tree}
  files[], hunks[{file, old_range, new_range, kind: body|predicate|table|decl|build|comment}]
  symbols[]                         # functions/kernels whose bodies changed (depfile + compile_commands)
  dispatch_sites[{file:line, predicate_text, discriminators: {types[], ops[], shape_terms[], backend[], arch[], threads}}]
  env_knobs[{name, read_site, default_before, default_after}]     # getenv sites added/changed; default flips flagged
  build_flags[{name, before, after, variants_affected[]}]         # CMake/defines/PGO
  objects_expected_changed{variant: [dso...]}                     # from build graph; confirmed by T0 below
  change_class: kernel_body | dispatch_predicate | shared_machinery | recipe | build | mixed | opaque
  opaque_reasons[]                  # macro-generated, templated, JIT, device-only, generated tables
```

The static footprint is a **prediction**. It drives ordering, the expected-case budget and the remedy suggestion. **It is never sufficient for INERT.**

**Integrity precondition — the footprint range must be the tree that was MEASURED (AK-RH-1).** At research `94c75914` the author step verifies only the paths the actor *declares* (`AK/loop/actors.py:437`, `git status --porcelain -- <declared paths>`), while the oracle (`test-backend-ops`) and `llama-bench` are built from the whole candidate worktree (`AK/loop/run.py:358-427`) and the keep commits only the declared paths. An undeclared edit is therefore compiled into both the judges and the measured binary, is never reviewed, and is absent from `git diff parent..keep`. A footprint over that range would under-report TOUCHED, and a T0 digest comparison would compare the wrong objects. This spec therefore **requires AK-RH-1** (full dirty set == declared paths ∪ allowlist; `tests/**` and `tools/llama-bench/**` refused; filed from `intake-1387`, owner `autokernel-unified-surface-program.md`) before any P2 refuse-mode row is trusted. Until then, AKX-P1 computes the footprint over the **measured worktree's full dirty set** (`git status --porcelain` unscoped) and records any path outside the declared set as `opaque_reasons: undeclared_edit`, which makes every workload UNKNOWN for that keep.

### 7.2 Proof tiers

| tier | proof | compute | yields |
|---|---|---|---|
| **T0 — object identity** | Build the candidate for `w`'s build variant. Every DSO/executable `w` loads (the `verify_ggml_linkage.sh` set) is **byte-identical** to the anchor's, and the effective recipe/env is identical. | **Build compute only.** Zero inference. | **INERT-BY-CONSTRUCTION.** The strongest claim, with no shape caveat. |
| **T1 — differential coverage** | Coverage variant of anchor and candidate. Run `w`'s census forward over its full shape envelope on both. **INERT-BY-COVERAGE** iff (i) no line in any `body`/`table` hunk executed in the candidate run, AND (ii) for every executed `predicate` hunk line, the branch-outcome vectors are identical between anchor and candidate, AND (iii) each env-knob read site in the footprint is either not executed or reads the same effective value, AND (iv) the `hip_matmul_routes` multiset and the `op_backend` histogram are identical per shape. | **Correctness-surface compute**, two forwards. | Scope label `shape_envelope=<hash>`. It holds only for shapes exercised, and INF-73 §8.9's "detect no-op controls / unexpected fall-through / op coverage" is discharged by it. |
| **T2 — none available** | Stale census, unbuildable variant, coverage unsupported for a hunk (`opaque_reasons`), device-only code with no attributable host site, or a vacuous census. | — | **UNKNOWN.** |

This satisfies INF-73 P3 "Oracle extension: op-coverage diff for env-gated knobs (fall-through class)" (`autokernel-unified-surface-program.md:1045`). Clause (iii) is the fall-through detector, and it works where output identity cannot (§5).

### 7.3 Classification rules (fail-closed)

```text
classify(p, w):
  if census(w) missing or stale or not census.validity.observed:        -> UNKNOWN(reason)
  if T0 holds:                                                          -> INERT (by_construction)
  if footprint.change_class in {build} and w.variant in variants_affected -> TOUCHED
  if any env_knob default flip and knob read executed in census(w) (or coverage unavailable) -> TOUCHED
  if T1 evaluable:
       T1 holds                                                         -> INERT (by_coverage, envelope)
       else                                                             -> TOUCHED(executed_hunks, changed_branches, changed_routes)
  else                                                                  -> UNKNOWN(opaque_reasons)
decision_class = INERT if INERT else TOUCHED        # UNKNOWN => TOUCHED, always
```

Guards:
- **Author target:** always TOUCHED. It is gated by the existing keep rule.
- **Vacuous-pass guards** (the FOLD-2 G4 precedent, `autokernel-champion-aggregate.md:658-661`; the gate-guards rule, `autokernel-unified-surface-program.md:887-888`):
  - A census with `nodes_total ≤ MIN` (`fold2_gates.py:66`, 1000), missing expected ops, `device_seen=False`, or fewer shapes than the envelope is **not observed**, and the pair is UNKNOWN.
  - A coverage run whose total executed-line count in `ggml/src` is zero is **invalid**, not INERT.
  - An empty footprint (zero hunks) on a non-empty diff refuses the screen itself.
- **Zero-TOUCHED results are allowed, but must be witnessed.** Every INERT row carries its T0 digests or T1 profile hashes. A screen result with all workloads INERT and no witnesses refuses.

### 7.4 Evidence records

Each `(p, w)` writes one `epyc.autokernel.blast_radius_row.v1` into the campaign journal (`AK/journal.py` append discipline, per INF-73 §8.5):

```text
{keep_id, parent, child, workload_id, census_freshness_key, footprint_sha256,
 classification: INERT|TOUCHED|UNKNOWN, decision_class: INERT|TOUCHED,
 tier: T0|T1|none, witnesses: {dso_digests_anchor/candidate | coverage_profile_sha256 x2, shape_envelope_hash},
 touched_detail: {executed_hunks[], changed_branches[], changed_routes[], knob_reads[]},
 unknown_reason?, tool_versions, created_at}
```

Plus one `blast_radius_screen.v1` per keep:
- `{keep_id, workload_ids[], rows_ref[], touched_ids[], inert_ids[], unknown_ids[], screen_digest}`

**Record class:** these are **observations of structure**, not rate claims. They gate nothing on their own. They decide **which workloads the Spec C statistic must be run on**, and INERT rows are the explicit, witnessed reason a workload is excused. Under P-AK-SEARCH-1 these records stay inside the campaign (`measurement/protocols/kernel-research.md:93-118`).

---

## 8. Spec C — multi-workload non-regression keep gate

### 8.1 Statistical form

For each TOUCHED non-author workload `w`, define `θ_w = log(median_candidate / median_parent)` of the workload's registered metric. The metric is higher-better, and direction is confirmed from the recipe metric field (`TargetSpec.metric_direction`, `campaign.py:160-176`).

Hypotheses:
- **H0_w:** θ_w ≤ −δ_w (a regression at least as large as the margin)
- **H1_w:** θ_w > −δ_w (non-inferior)

Parameters and requirements:
- **Margin `δ_w`:** stated in the floor's own unit. `δ_w` = `k_δ · F_w`, where `F_w` is `w`'s calibrated floor. The operator sets `k_δ` (§13 Q1); the recommendation is 1.
- **Unit:** the effect unit must equal `F_w.unit` (arm | session | process). This is enforced by `FloorReading.gate_floor(effect_unit=…)` / `serving.check_unit`, and a mismatch raises `FloorUnitMismatch` and REFUSES (`serving.py:592,633-642,1606-1622`; R23-55).
  - A process-scoped knob (a RUNTIME_CONFIG arm or a THP-like knob) faces the session sd **2.793%**, not the arm sd **0.501%** (`autokernel-unified-surface-program.md:672-677`).
- **`n`:** the floor's `n` must be present (`gate_floor` refuses otherwise). Gating-floor calibration requires n ≥ 24 plus an interval (INF-73 §8.9, P2 checkbox `:1030`).
- **Decision statistic:** the **non-inferiority e-process** required by Annex K for any rate comparison (`measurement/protocols/kernel-research.md:280-290`). The paired-block construction, anytime-valid inspection and pre-committed stopping rule are all per Annex K (`:291-299`).
  - Reject H0_w when `e_w ≥ 1/α`.
  - At the `max_blocks` ceiling without rejection, the verdict is **NOT-SHOWN-NON-INFERIOR**, which is fail-closed.
  - The floor-rule point estimate and a labelled `descriptive` LCB ride beside it (Annex K forbids an LCB as the test).
- **Interim form, until the loop carries an e-process:**
  - The loop's existing keep rule is a floor comparison (`serving.py:1389`), not an e-process. The same non-conformance question applies to both, and this gate does not resolve it silently (§13 Q2).
  - Interim rule: refuse when `effect_w ≤ −F_w` (the existing `ab_verdict` decisive negative) **OR** when `effect_w − F_w < −δ_w`, i.e. the observed lower edge breaches the margin.
  - With `k_δ = 1` the second clause is `effect_w < 0` at the pre-registered n. That is deliberately conservative, and §10 prices its false-refusal rate.
  - Interim rows carry `statistic: floor_interim`.
- **Order control and anchor:** interleaved and randomized (AB/BA), with the anchor gate first (Annex K `:300-310`). A VOID window is `INVALID`, never a regression.
- **Comparator:** the keep's **parent** tip, i.e. the marginal effect, on `w`'s **own** registered production recipe and instrument. Cumulative drift is caught at Spec D against production_ref.
- **Serving vs bench:** where `w`'s production recipe uses speculation, llama-bench cannot exercise it (`MEASUREMENT.md:160-163`). Its row must be serving-class under the recipe; a bench cell is an addendum only. Cross-class comparison refuses (`MEASUREMENT.md:116-122`).

### 8.2 Multiplicity

The gate passes iff **every** TOUCHED workload rejects its H0. That is an intersection-union test: the probability of wrongly declaring all k non-inferior is ≤ α with **no correction** (each H0 tested at α).

Multiplicity therefore does not inflate false passes. It inflates **false refusals**: with per-workload power `π`, `P(pass | all truly null) = π^k`. §10 quantifies this, and it is why the census matters. Every workload moved to INERT removes a factor of `π`.

### 8.3 Ordering and early refusal

Among TOUCHED rows, run in ascending order of `cost_w / p_fail_w`:
- `cost_w`: the registered arm-seconds for `w`, using the INF-73 serial cost forecasts (last-8 / p75, `autokernel-unified-surface-program.md:180-187`).
- `p_fail_w`: a prior from the footprint's intersection weight. Use the census share of `w`'s nodes or matmul routes whose (op, type, shape) match the footprint's discriminators, and set it to 1 for shared machinery.

Rules:
- **Stop at the first NOT-SHOWN-NON-INFERIOR or REGRESSION.** Remaining rows are `not_run_after_refusal`, never `passed`.
- Anytime-valid e-processes permit an early per-row **pass** too.
- Same-backend rows run inside the author's held claim first. Other-backend rows are scheduled as charged validation stages (the existing `--validate-source-continuation` stage, `serial_run.py:1353-1356,1796-1799`).

### 8.4 When the gate runs

Recommended option **B**; the operator chooses in §13 Q3.
- **A (synchronous):** refuse before the keep commit. Blocks authoring on the slowest TOUCHED workload.
- **B (provisional-blocking):** the keep lands as `provisional`. Authoring may continue on the tip, but:
  - (i) the keep does not count toward the R23-54 four-keep cadence;
  - (ii) it cannot enter a `ValidationBatch` / `validated_candidate` (§8.17C, `autokernel-unified-surface-program.md:1988-2040`) or a FOLD;
  - (iii) a refusal automatically builds the derived candidate **without** that keep, using the existing LOO derived-candidate construction, not a blind revert on the live tip (`:2027-2030`), and journals `retracted_by_nonregression`;
  - (iv) descendants that touch the same hunks are re-screened.
- **Upgrade in both options:** the existing `required_source_validation.v1` aggregate is upgraded so that `failed` **refuses the keep**, instead of only withholding LOO (`serial_run.py:1285-1288`). That is the one-line gap between annotation and gate (`intake-1367#01`).

### 8.5 Refusal record and remedy path

`epyc.autokernel.nonregression_refusal.v1`:

```text
{keep_id, workload_id, statistic: eprocess|floor_interim, delta_w, F_w{value, unit, n, path},
 effect_w, e_w|None, blocks, verdict: REGRESSION|NOT_SHOWN_NON_INFERIOR,
 blast_radius_row_ref, touched_detail, remedy: {suggested_form: 1|2|3, discriminator_hint}}
```

**Remedy path:** re-gate the patch so it becomes INERT on `w`.
- **Form (1):** narrow the dispatch predicate using a discriminator that separates the author workload from `w`. The hint is computed from the census diff between the two (types, `ne11`, arch, backend, threads).
- **Form (2):** move the change behind a recipe knob that is default-OFF, ON only in the author's recipe.
- **Form (3):** as a last resort, a build define on the author's variant only.

The re-gated patch is a **new candidate**. It re-enters Spec B: new footprint, new T0/T1, and the author's own keep rule again. **A remedy never inherits the original's rows.**

The planner receives the refusal record as context through the existing belief/planner feedback path (INF-73 AKU-12b-SERVING-FEEDBACK).

### 8.6 Interactions

| existing mechanism | interaction |
|---|---|
| Serving gate (R23-43/44/54) | Unchanged for the **author** surface. Provisional keeps do not count toward `SERVING_GATE_EVERY_KEEPS=4` until the gate passes (option B). |
| Floors / R23-55 | Every row calls `gate_floor(effect_unit=…)`. A missing floor for a TOUCHED workload puts the row in `pending`, **never passed**. That schedules the workload's calibration as a prerequisite (INF-73 §8.17C calibration debt). |
| Headline admissibility ≥N (R23-57; undefined N, AK-OBJ-1 from the intake-1367 dive) | **This gate produces keep-decision rows, not headlines.** It does not need N. It must not be quoted as a headline either: rows are labelled `CANDIDATE` search verdicts (Annex K `:401`). If AK-OBJ-1 defines N, it binds Spec D's promotion-record numbers, not this gate. |
| AK-ACC-1 (`intake-1370#record`) | Keep-gate rows are selection-stratum evidence and **may not** feed Spec D or promotion numbers. Pair IDs are recorded for the disjointness check. |
| OP-41 (operator-owned admission control, lands after champion finalization, promotion and reboot; `autokernel-unified-surface-program.md:890-902`) | **What this gate needs from OP-41, without deciding it:** (i) arm-second reservations for other-backend TOUCHED rows, especially CPU W3–W6, whose windows are the expensive, contended ones; (ii) a correctness-surface class for census forwards, distinct from benchmark windows but still exclusive of concurrent benchmark arms; (iii) a rule that an unavailable window leaves rows `pending`, never passed. **Until OP-41 lands:** cooperative region-lock plus labelled contended arms, as today, and a row measured under unattributed foreign load is `INVALID`, not a regression. |
| Required-target validation (`serial_run.py:1196-1278`) | This gate **is** that aggregate, upgraded: non-author rows use §8.1 instead of `ab_verdict`, INERT rows are excused only with witnesses, and `failed` refuses. No second ledger. |

---

## 9. Spec D — composition / FOLD re-check

When it runs:
- at every `ValidationBatch` freeze (§8.17C);
- at every fold of an external lineage (e.g. an INF-70 branch);
- before any promotion proposal.

Steps:
1. **Champion-level census.** Regenerate the base census for every workload on the **composed** candidate, since the freshness key changed.
2. **Composed footprint vs production_ref** (and vs `validated_candidate`). Run the Spec B screen on the whole range, not the union of per-keep rows. A per-keep INERT is **not reusable**, because class (d) interactions are invisible per keep.
3. **Full-workload non-regression.**
   - Run §8.1 on every workload TOUCHED by the composed range. In practice this is almost every workload, because objects differ.
   - Use **confirmation-stratum fresh launches** (AK-ACC-1; Annex K selection/confirmation split, `kernel-research.md:311-323`).
   - Compare against **production_ref** at each workload's production-optimal recipe (`MEASUREMENT.md:156-165`). This catches sub-floor per-keep losses that compound.
   - CPU pass/GPU missing leaves the batch pending (§8.17C).
4. **LOO.** Run the existing `source_loo.execute_surface` per keep, per **TOUCHED** workload. INERT-by-T0 workloads need no LOO arm for that keep, which is a direct cost saving over INF-73's `n_keeps × n_surfaces` (`autokernel-unified-surface-program.md:855-861`).
5. **AK-GH-1 count** (`intake-1378#record`). Beside each LOO arm, record the keep-time effect. Count keeps whose LOO arm is at least as fast as the full bundle on any workload where the keep was TOUCHED. Report the count on the promotion record. It is zero extra compute.
6. **DO-NOT-FOLD ledger as a fixture.** A fold candidate containing `2516c9807` must screen TOUCHED on every CPU workload whose census executes the changed knob read sites. It must also flag `env_knobs[].default_after=ON`.

Refusal at FOLD names the keep(s) implicated by LOO. The remedy path is §8.5.

---

## 10. Compute budget

**Recorded inputs:**

| input | value | source |
|---|---|---|
| Floors | gemma dec-b4 GPU 0.456% @20; 27B dec-b4 0.949% @20; GPU tg128 FOLD-2 0.638% @20; loop GPU tg128 3.452% p95 @20; serving floor 4.581% @10; GLM CPU 7.801% | `2026-09-03 progress:95`; `champion-aggregate:54-60,657`; `unified:662`; `rebuild:1993`; `unified:24` |
| Unit sd | arm 0.501%, process launch 2.793% | `unified:672` |
| GPU claim-grade A/B | ≈20 min @20 pairs | `2026-09-03 progress:95-100` |
| GPU floor calibration | ≈1 h 15 min | same |
| CPU (GLM) | 5 iterations × 5 pairs in 248.2 min, ≈50 min/iteration including build and planner | `unified:22-25` |
| CPU LOO arm | ~6 min of arm time | `unified:857-858` |
| op oracle | 53 s | `gates.py:23` |
| Keep rate | 8 keeps / 50 loops on GLM | `unified:60-62` |

**Per-row sample size.**
- Take `F` as the p95 |A/A effect| at n=20. That implies `σ_pair ≈ F·√20/1.96` (ESTIMATE; normal approximation).
- For a true null (θ=0), one-sided α=0.025: `n ≈ ((z_α+z_β)·σ_pair/δ)²` = `20·((1.96+z_β)/1.96)² / k_δ²`.

| k_δ | power 0.8 | power 0.95 |
|---|---|---|
| 2 (≈ today's "not decisive negative") | ≈10 pairs | ≈17 pairs |
| 1 (recommended) | ≈41 pairs | ≈68 pairs |

The e-process costs somewhat more than this fixed-n figure. Treat the numbers as lower bounds, to be replaced by the P2 calibration.

**False refusal from multiplicity.**
- At power 0.8, `P(pass | k null TOUCHED workloads)` is 0.8^1 = 0.80, 0.8^3 = 0.51, 0.8^5 = 0.33.
- At power 0.95 it is 0.95, 0.86, 0.77.
- **Without the census, every keep faces k = W−1 = 5, and a third of genuinely harmless keeps would be refused at power 0.8.** The screen is what makes k small.

| class | what | per keep | ESTIMATE |
|---|---|---|---|
| **zero-compute** | footprint, GGUF census, classification logic, records, AK-GH-1 | all | seconds |
| **build compute** | T0 candidate build for the non-author variant; coverage variants for T1 | 1–3 builds | minutes each, on a locked build slot |
| **correctness-surface** | T1 forwards: anchor + candidate coverage × envelope shapes, for each workload not cleared by T0 | 0–5 workloads × 2 forwards | model load dominates. W5 (122B) and W6 are the slow loads. **Unmeasured; P0 records wall times.** |
| **benchmark window** | §8.1 rows for TOUCHED workloads only | 0–5 rows | GPU ≈ 20–70 min/row; CPU ≈ 50 min–2 h/row at k_δ=1 |

Scenarios:
- **Worst case** (shared-machinery keep, all five non-author workloads TOUCHED): two GPU rows plus three to four CPU rows, ≈ **5–9 h of arm time per keep** at k_δ=1. At 8 keeps / 50 loops this rivals the search itself. That is correct, because this is the high-risk class. Use it as the planner's incentive to author discriminator-gated patches.
- **Expected case, GPU device-kernel keep:** only `libggml-hip.so` differs, so T0 clears W3–W6 (CPU variant DSOs byte-identical) at zero inference. T1 decides W2 (the other ROCm0 workload). A Q4_K keep is **TOUCHED on W2** (Q4_K_M), which is exactly the production workload today's measurements never checked. ≈ 1 GPU row, ≈ 20–70 min.
- **Expected case, CPU type-gated keep:** `libggml-cpu.so` differs in both variants, so T0 clears nothing. T1 on W1/W2 usually clears it: G4 shows the 27B's CPU backend holds only 12 GET_ROWS (`champion-aggregate:656`). T1 on W3–W6 clears type-mismatched workloads using the census tensor-type sets. Residual: 1–2 CPU rows.
- **Base census per champion advance:** 6 workloads × (scheduler-debug + route-log/coverage forward), correctness-surface only, amortized over every keep until the next advance.

---

## 11. Failure modes, and how the spec avoids "computed guard never consulted"

| failure mode | guard |
|---|---|
| Gate computed, output not consulted (today's `failed` aggregate only withholds LOO) | `failed` **refuses** the keep (option A) or blocks cadence, validation batch and FOLD, then auto-retracts (option B). A test asserts a failed row changes the tip or blocks the batch. A warning-only code path fails CI (`intake-1367#01`). |
| Vacuous census or coverage (zero nodes, no `-v`, ANSI-mangled logs, the FOLD-2 G4 precedent) | §7.3 observation guards. An unobserved census gives UNKNOWN, which is TOUCHED. A zero-executed-lines coverage run is INVALID. |
| Empty TOUCHED set passes silently | Every INERT needs a witness. A screen with zero rows or zero witnesses refuses. `workload_ids` must equal the resolved required set, or the result refuses (mirrors `serial_run.py:1229-1232`). |
| Stale census reused after a model, recipe or commit change | Freshness key mismatch gives UNKNOWN. No carry-forward. |
| Callback-perturbed census (fusion split) | The fired-kernel layer is callback-free by construction (§6.3). |
| Knob fall-through invisible to output diff | T1 clause (iii) plus the footprint's `env_knobs`. The acceptance fixture uses sync17-fix2 and the `GGML_TINY_SOLO_CLAMP` class. |
| Cross-unit floor | `FloorUnitMismatch` refuses (existing). |
| Missing floor or unavailable window treated as pass | The row is `pending`. The aggregate is pending, never passed (existing three-valued fold, extended). |
| Shape-envelope blindness (dec-b8 sign flip) | T1 INERT is scoped to the envelope hash. The envelope is derived from the registered recipe (ubatch, np, draft_max), not chosen by the author. |
| Per-keep INERT reused at FOLD | Forbidden. Spec D recomputes on the composed range. |
| Selection-biased promotion number | AK-ACC-1 disjoint strata. Keep-gate rows cannot feed Spec D numbers. |
| Instrument build folded into champion | Coverage and CPU_PROF variants are labelled NOT-TO-FOLD instruments (the precedent is `bin-r1`, `autokernel-unified-surface-program.md:1684`). Production digests are verified by `verify_llama_cpp.sh`, and `strings` must show zero coverage/profiler symbols in candidate delivery builds (CLAUDE.md build-artifact rule). |
| Gate weakened to fit noise | `δ_w`, `k_δ`, α and `max_blocks` are pre-registered and journaled. Changing them voids affected rows (Annex K `:291-299`). |

---

## 12. Phased implementation plan

Global constraints:
- All builds happen in `llama.cpp-experimental` worktrees off the current champion, never the frozen production tree.
- Instrument variants are form-3 builds of an existing commit and require **no** kernel source change.
- Only the §13 Q4 counter option (a) would be a champion source change, which requires the four-step workflow (CLAUDE.md:48-53).
- Subagents do not launch or kill processes. Stage claims go through the owning loop session.

### P0 — census tooling (from existing mechanisms)

- [x] **AKX-P0a — generalize the G4 dispatch probe into a per-workload census producer.**
  - Lift `fold2_gates.run_dispatch_probe`/`parse_scheduler_graph` into `loop/census.py`, keeping the vacuous-pass guard.
  - Iterate the recipe's shape envelope (prefill ubatch, decode, np/draft verify width).
  - Emit `workload_census.v1`, with the `weights` layer from `workload_contract.read_census`.
  - Store under `loop-memory/census/`.
  - Hermetic tests: recorded 27B log fixture (`test_fold2_gates.py:89`); an ANSI-mangled vacuous log refuses.
  - **Acceptance:** fixture census matches 27,516 nodes / SSM_SCAN=0 / 12 CPU GET_ROWS; stale-key and zero-node cases return UNKNOWN.
  - Compute: zero for the tests; correctness-surface for live runs.
  - ✅ 2026-09-15 — research `e5c0d798`: `loop/census.py` owns the shape-envelope producer,
    workload-census-v1 schema, atomic storage and vacuous guards; the retained fixture proves 27,516 nodes,
    SSM_SCAN=0 and 12 CPU GET_ROWS, while stale, zero-node and ANSI-corrupted evidence stays UNKNOWN.
- [ ] **AKX-P0b — HIP route layer.**
  - Parse `GGML_CUDA_LOG_MMVQ_ROUTE=2` into `hip_matmul_routes`.
  - **Acceptance:** on a recorded W1 decode log, the route multiset is stable across two runs of the same build (A/A structural identity).
  - Compute: correctness-surface on ROCm0 under the GPU claim.
- [ ] **AKX-P0c — coverage build variant.**
  - Add a `coverage` variant to `controller/build_recipe.py` for CPU and HIP (same defines as production, plus coverage flags, plus atomic update).
  - Prove that it builds, that `ggml/src` host lines execute on a W1 and a W4 short forward, and that the production-variant digests are unchanged.
  - Record forward wall times per workload. These replace the §10 ESTIMATEs.
  - **Acceptance:** non-zero executed lines in `ggml-cpu.c` and `ggml-cuda.cu` host code. If HIP coverage does not link, record UNKNOWN-by-construction for device-only hunks and escalate §13 Q4.
  - Compute: build plus correctness-surface.
  - **Code checkpoint 2026-09-15 — research `ca16b055`:** distinct correctness-only CPU/HIP coverage
    recipes preserve the sealed base define prefixes and digests, append atomic host counters and HIP
    clang profile/mapping flags, and resolve by content identity. The required real builds and W1/W4
    executed-line acceptance remain open; no coverage result is yet claimed.
  - **Invalid W4 acceptance attempt 2026-09-15:** both coverage variants built, but the first CPU
    forward omitted `-no-cnv` and left stdin open. `llama-cli` entered its REPL, ran for 8,464 seconds
    and produced a 57.5 GiB stream of empty prompts before the owning session terminated exact PIDs
    1699977/1699975 and truncated that one log. The run is invalid despite emitted counters and the
    wrapper's misleading `rc=0`; rerun with `-no-cnv`, `stdin=DEVNULL`, a wall timeout and bounded
    stdout before checking executed lines or recording wall time.
- [ ] **AKX-P0d — base census for W1–W6 on the current champion-of-record.**
  - Compute: correctness-surface, six workloads, under stage claims.
  - **Acceptance:** six observed censuses with witnesses. W3–W6 CPU runs are inside region-lock windows, and foreign load is sampled (`foreign_load.py`).

### P1 — footprint and screen, observe-only, historical replay (acceptance test)

- [x] **AKX-P1a — footprint extractor.**
  - Give `evaluator/surface.derive_affected_surface` a producer (depfile + `compile_commands.json` + hunk classifier).
  - Emit `patch_footprint.v1` using `CompositionEvidence` field names.
  - **Acceptance:** on `7d2ea88b`, `732389d6` and `db18f393` the predicted discriminators are recorded, `732389d6`/`7d2ea88b` show `GGML_TYPE_Q4_K` terms, and `2516c9807`'s env-knob default flips are detected.
  - Compute: zero.
  - ✅ 2026-09-15 — research `a6d0464d`: the git-diff/compile-commands/depfile producer emits
    `patch_footprint.v1`, maps exact CompositionEvidence fields, fails closed on opaque touched files and
    detects the required historical Q4_K, HIP/CDNA2/shape and default-ON knob discriminators. The focused
    footprint/surface suite passed 223 tests plus 52 subtests.
- [ ] **AKX-P1b — replay 732389d6 (THE acceptance test).**
  - Workloads: W1 (27B Q8_0 ROCm0), W2 (VL-30B Q4_K_M ROCm0), W4 (gemma Q4_K_M, **both** its production CPU recipe and the recorded GPU dec-b4 surface).
  - Screen each keep in `0db32c06e..732389d6` against its parent, and the whole range against production v9 source built in an experimental checkout.
  - **Pass criteria:**
    1. `7d2ea88b` and `732389d6` classify **INERT on W1** (T0 or T1 with witnesses).
    2. Both classify **TOUCHED on W4-GPU**, and each is TOUCHED on W2 or explicitly INERT with a witness.
    3. **At least one change in the range classifies TOUCHED on W1.** The −1.414% decisive regression exists, so an all-INERT W1 result **falsifies the screen**, whatever else passes.
    4. The TOUCHED-on-W1 set is reported against the attribution "shared DFlash2/feature machinery". Agreement is recorded as structural support; disagreement is a finding, not a failure.
  - **Needs:**
    - coverage builds of each keep and its parent, plus the DFlash2/MoE-Spec range endpoints (≈6–8 build-variant builds);
    - two coverage forwards per (commit pair, workload);
    - the GPU claim for W1/W2;
    - a CPU region window for W4-CPU.
  - **No benchmark window:** the replay classifies against the **recorded** A/B verdicts, and measures nothing new.
- [ ] **AKX-P1c — replay sync17-fix2.**
  - Screen `2516c9807` against `ef81196d5` on the INF-70 CPU workload and on W1.
  - **Pass criteria:**
    - TOUCHED on the CPU workload, with `knob_reads` naming the default-ON knobs;
    - a footprint `env_knobs[].default_after` flip;
    - W1 classified by T1 with a witness (either outcome), not by inference from "it's a CPU patch".
  - Compute: build plus correctness-surface.
- [ ] **AKX-P1d — negative and positive controls.**
  - A comment-only patch must be INERT-by-T0 on all workloads.
  - A synthetic Q8_0-only dispatch change must be TOUCHED on W1/W3 and INERT on W2/W4/W6. W5 is decided by its census tensor-type set.
  - An env knob read with no default change must be INERT where the knob is unset.
  - Compute: build plus correctness-surface.

### P2 — gate in refuse mode

- [x] **AKX-P2-PRE — AK-RH-1 landed** (§7.1 integrity precondition): the author step verifies the full dirty set, refuses oracle/bench paths, and the kept commit equals the measured tree. P2 refuse-mode rows are untrusted until this is ticked. ✅ 2026-09-15 — research `bada71c2`; the S3-AKU-15 implementation and zero-compute regression fixtures prove all three preconditions before build/keep.
- [x] **AKX-P2a — upgrade `surface_validation.classify` for non-author rows** from `ab_verdict` to §8.1 (interim floor form, then e-process per §13 Q2). INERT rows are excused only with a `blast_radius_row` witness.
  - **Acceptance:** fixtures cover −0.9% @ 0.949% floor, which today passes and must now refuse at k_δ=1 (interim); a cross-unit floor refuses; a missing floor stays pending.
  - Compute: zero (fixtures).
  - ✅ 2026-09-15 — research `24725359`: non-author validation uses the interim k_delta=1 rule,
    refuses floor/effect unit mismatches, retains missing floors as pending, and accepts an INERT excuse only
    from a strict T0/T1 blast-radius witness. Fixtures cover the stated −0.9%@0.949% case.
- [x] **AKX-P2b — make `failed` gate.** `required_source_validation.v1` `failed` refuses (option A) or blocks cadence, ValidationBatch and FOLD and auto-builds the derived candidate without the keep (option B), per §13 Q3.
  - **Acceptance:** a test proves a failed row changes controller state. A warning-only path fails the test.
  - Compute: zero.
  - ✅ 2026-09-15 — research `57e9ddef`: option A is implemented narrowly. After persisting the
    aggregate in controller state, a failed required-source row raises `SerialRefused` with the failed
    target identities; both normal completion and recovery traverse this gate, so failure cannot remain a
    warning-only condition or advance into LOO/cadence.
- [x] **AKX-P2c — ordering and early refusal** (§8.3), with `not_run_after_refusal` rows.
  - Compute: zero (logic).
  - ✅ 2026-09-15 — research `5b8cd719`, `fe901100`, `a15a98e5`: failed rows outrank pending,
    remaining targets are recorded `not_run_after_refusal`, and the serial owner launches no successor after
    a failed aggregate. When a campaign explicitly enrolls an immutable per-commit priority receipt, it
    selects one row at a time by validated cost/p_fail (shared machinery p_fail=1) and refuses malformed,
    incomplete or changed evidence. The feature remains opt-in so existing campaigns do not acquire a new
    receipt dependency merely by upgrading the loop.
- [ ] **AKX-P2d — floors for every production workload** at its production-optimal recipe, n ≥ 24 plus an interval, carrying `unit`.
  - This is **benchmark-window compute** and is scheduled as calibration debt under OP-41 rules. Missing floors keep rows pending.
- [ ] **AKX-P2e — first live refuse-mode keep** in a GPU campaign.
  - **Acceptance:** one keep screened, rows written, and a gate decision journaled with witnesses.
  - Compute: benchmark window, TOUCHED rows only.

### P3 — FOLD / composition re-check

- [ ] **AKX-P3a — Spec D on ValidationBatch freeze:** composed census, composed footprint vs production_ref, full-workload rows on confirmation-stratum launches.
  - **Acceptance:** the batch cannot advance with any required row pending or failed. Per-keep INERT reuse is refused by test.
- [ ] **AKX-P3b — LOO restricted to TOUCHED workloads per keep**, plus the AK-GH-1 count on the promotion record.
  - **Acceptance:** a promotion record without the count or the LOO receipts refuses (the existing required-field rule).
- [ ] **AKX-P3c — DO-NOT-FOLD fixture:** a fold containing `2516c9807` refuses at screen plus gate.

### P4 — receipts, dashboard, belief wiring

- [ ] **AKX-P4a — dashboard card per keep.** Show the workload × {INERT(T0/T1)/TOUCHED/UNKNOWN} matrix, row verdicts and the refusal remedy. Register it under the hub plane rule with a health probe and a freshness envelope (`dashboard/README.md`).
- [ ] **AKX-P4b — champion standing is a workload vector.** It is never one number (R23-26), and each cell names its workload and recipe.
- [ ] **AKX-P4c — belief kernel write side.**
  - Census rows and blast-radius rows are verified structural findings. Filed 2026-09-15 as **SC81** in `vidya-belief-substrate-program.md`, with a candidate source row in `scripts/vidya/adapters/README.md` (CLAUDE.md: surface the wiring immediately, not at P0). Tick this item when SC81 lands with AKX-P0a.
  - Non-regression rows reuse the existing serving A/B archive/belief export (INF-73 "Aggregate serving gates feed the original archive and belief consumer").

---

## 13. Operator decisions (package: context · options · recommendation · default)

None of these blocks P0 or P1. Each blocks only its own P2/P3 item.

**Q1 — non-inferiority margin `δ_w = k_δ · F_w`.**
- *Context:* today's non-author rule tolerates a true regression up to ≈2F (0.95% floor → ≈1.9% undetected), and sub-floor losses compound across keeps.
- *Options:*
  - (a) k_δ=2, today's rule formalized: cheapest (≈10–17 pairs/row), weakest.
  - (b) k_δ=1: ≈41–68 pairs/row, catches losses ≥F.
  - (c) an absolute per-workload margin (e.g. 0.5%) with n solved from the floor: costliest on noisy CPU workloads.
- *Recommendation:* **(b)**, with Spec D's cumulative production_ref check catching what per-keep margins miss.
- *Default if unanswered:* (a) in refuse mode, so P2 is not blocked, with (b) computed and journaled beside it.

**Q2 — statistic authority: floor rule vs Annex K e-process.**
- *Context:* Annex K requires a non-inferiority/improvement e-process for every rate comparison and forbids an LCB as the test (`kernel-research.md:280-290`). The loop's existing keep rule is `|effect| ≥ floor` (`serving.py:1389`). This gate should not quietly adopt a form Annex K forbids, nor quietly declare the loop non-conformant.
- *Options:*
  - (a) Implement the e-process in the loop for both the keep rule and this gate.
  - (b) A human-only Annex K amendment ratifying a floor-based non-regression rule for in-campaign retain/abandon.
  - (c) Interim floor form, labelled `floor_interim`, until (a) lands.
- *Recommendation:* **(c) now, then (a)**. Refusing a keep inside the campaign is already within P-AK-SEARCH-1 authority (retain/abandon, `kernel-research.md:79-83`), so no amendment is needed to *refuse*. Only the statistic's form is at issue.
- *Default:* (c).

**Q3 — gate timing.**
- *Options:*
  - (a) Synchronous before commit: simplest and safest, but stalls authoring on CPU rows (~1–2 h each).
  - (b) Provisional-blocking (§8.4): authoring continues, and the keep cannot count, batch, fold or promote until its rows pass; refusal auto-retracts via derived candidate.
- *Recommendation:* **(b)**, with a cap of two provisional keeps outstanding per target so dependency chains stay short. Revisit trigger: "a keep is later shown to depend on an earlier rejected change" (the same trigger as the parked-branch ERA decline).
- *Default:* (a) for same-backend TOUCHED rows (cheap, inside the held claim), and (b) for other-backend rows.

**Q4 — fired-kernel proof instrument.**
- *Options:*
  - (a) Coverage build variant (form 3): no champion source change. Host code only. Device kernels are attributed via host sites.
  - (b) Compiled-out `AK_DISPATCH_COUNT(site)` macros in the champion source, with an authoring-contract rule that every new dispatch branch registers a site. Exact per-kernel counts including device-side routes, but it is a permanent champion source change that every future production version must prove compiled out (`strings`), and it enters through the experimental workflow.
  - (c) Both: (a) by default, (b) only for hunks (a) leaves UNKNOWN.
- *Recommendation:* **(a) now, and (c) if AKX-P0c or P1b shows more than 20% of historical keep × workload pairs UNKNOWN.**
- *Default:* (a).

Not operator decisions, handled in-spec:
- Workload-set membership reuses the existing `serial_run.py:1222-1228` rule.
- Speech kernels are out of scope (separate trees).
- OP-41 needs are stated in §8.6 and not decided here.

---

## 14. Key files

**Root (lane `noninf-20260914`)**
- `handoffs/active/autokernel-unified-surface-program.md`: parent (§3.2 U2 floors/unit `:659-704`; §3.3 fall-through `:706-712`; P3 oracle item `:1045`; OP-41 `:890-902`; §8.10 `:1474-1502`; §8.17C `:1988-2040`)
- `handoffs/active/autokernel-rebuild-program.md`: R23-26 `:1420`, R23-48 `:2362`, R23-53 `:2353`, R23-54 `:1813`, R23-55 `:1824`, R23-57 `:1944`
- `handoffs/active/autokernel-champion-aggregate.md`: 732389d6 standing `:47-65`, FOLD-2 `:653-661`, DO-NOT-FOLD `:700-710`, per-surface recipe `:767-787`
- `handoffs/active/cpu-decode-roofline-program.md`: SYNC-17 knobs `:1615-1642`, CPU_PROF census `:328-342`, SYNC-21 `:1167-1172`
- `progress/2026-09/2026-09-01-ak-rebuild-20260828.md` (transfer / dec-b8 sign flip), `progress/2026-09/2026-09-03-ak-rebuild-20260828.md` (Q4_K claim, screen-model kernel mismatch)
- `MEASUREMENT.md` (`:8-11` claim, `:116-122` class, `:156-165` promotion boundary), `measurement/protocols/kernel-research.md` (P-AK-SEARCH-1: authority `:77-118`, statistics `:276-323`)
- `agents/shared/OPERATING_CONSTRAINTS.md:126-131` (single champion), `:254-265` (decision packages)

**Research (`epyc-inference-research` @ `94c75914`, `AK/` = `scripts/kernel_rnd/autokernel/`)**
- `AK/loop/serial_run.py` (`_required_source_validation` `:1196-1278`, `_pending_source_loo` `:1285`)
- `AK/loop/surface_validation.py:110-135`
- `AK/loop/fold2_gates.py` (G4 probe `:195-208`, parser `:133-152`, guards `:155-176`)
- `AK/loop/serving.py` (units `:78-90`, `check_unit` `:633`, `compare` `:1239`/`:1389`, `FloorReading` `:1549-1629`, `write_floor`/`load_floor` `:1644-1783`)
- `AK/loop/source_loo.py`, `AK/loop/accumulate.py:100-118,533`, `AK/loop/gates.py:88-158`, `AK/loop/campaign.py:160-176,427-440`, `AK/loop/serial_roster.py`
- `AK/controller/workload_contract.py:101-145`, `AK/controller/champion.py:324-340,784-877`, `AK/controller/build_recipe.py`
- `AK/evaluator/surface.py:1325,1401`, `AK/execution/t0_provider.py:1408-1424,2367-2397,3157-3205`, `AK/evaluator/correctness.py:2046-2107`

**ggml (champion `ef81196d5`, `/mnt/raid0/llm/tmp/champ2`)**
- `ggml/src/ggml-backend.cpp` (sched debug `:958-990,1749-1750`; eval-callback splitting `:1697-1715`; `get_tensor_backend` `:1978-1985`)
- `src/llama-context.cpp:682-692` (graph node/split log)
- `ggml/src/ggml-cpu/ggml-cpu.c` (compute order `:2107-2120`; IQK hook `:1371-1377`; fusion/solo knobs `:5082-5112`; `GGML_CPU_PROF` `:3620-3992`), `ggml/src/ggml-cpu/iqk/iqk_dispatch.cpp`, `ggml/src/ggml-cpu/repack.cpp:4527-4551,4835-4842`
- `ggml/src/ggml-cuda/ggml-cuda.cu` (mul_mat route order `:1864-1960`; route log `:1822-1862`; fusion `:2994,3537-3888`), `mmvq.cu:698-727`, `mmq.cu:240-313`; `ggml/src/ggml-hip/CMakeLists.txt:59-95`

**Fleet**
- `/mnt/raid0/llm/epyc-orchestrator/orchestration/model_registry.yaml` (lean, compiled 2026-09-03; `server_mode` `:1541-1803`)

**Research intake**
- `research/intake_index.yaml`: `intake-1367#01` (§3.4 gating quote, dive-verified), `intake-1370#record` (ERA; AK-ACC-1), `intake-1378#record` (AK-GH-1), `intake-1375#record` (FML-bench; bearing only on process metrics, not relied on).
- Not relied on: intake-1381 / intake-1392 (serving-config tuning evidence, dive-verified 2026-09-15) bear on INF-73 U3's proposer, not on this gate.
