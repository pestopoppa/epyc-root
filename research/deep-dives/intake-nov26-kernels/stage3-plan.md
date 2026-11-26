# Proposed filing for the November 26 research intake

**Decision requested** — approve the work packets below for filing. The evidence includes upstream measurements on other hardware. EPYC performance effects remain hypotheses.

## Decisions and owners

| Packet | Owner | Decision |
|---|---|---|
| P1 | kv-cache-program | Restore destination-only error recovery for device checkpoints on the experimental kernel and add valid, absent-storage, truncated-header and partial-read regression cases. |
| P2 | eval-tower-program | Add a task-level replay report for skill gating that records effective skills, scorer requirements, within-cell shuffled labels and held-out decisions. |
| P3 | autokernel-loop | Count eligible fused small-K MMVQ calls in retained 27B and A3B traces at widths one through four. |
| P4 | cpu-decode-roofline-program | Replay existing per-layer expert routes against a capacity-bounded static GPU pool and price NUMA-local cold routes and deduplicated long-prefill uploads. |
| P5 | speculative-decoding | Compare the released DFly2 target and drafter mappings with the local full-attention KV layout, sparse-index epoch and rollback semantics. |
| P6 | kv-cache-program | Add fixed-width repeat and cross-width first-divergence comparisons to the long-context determinism diagnosis using retained inputs and dispatch receipts. |
| P7 | cpu-decode-roofline-program | Identify whether either KDA exponential loop executes in Q38FN CPU traces and bound its contribution to decode and prefill. |
| P8 | speculative-decoding | Extend the frozen-logit sampler fixture to record retained support, drawn token and full versus post-filter probabilities at boundary ties. |
| P9 | kv-cache-program | Trace recurrent-state ownership and residual state-sized copies across rollback, slot reuse and phase transitions on CPU and HIP. |
| M1 | rocm-kernel-authoring | Check BF16 MFMA compiler compatibility when a clang-23 toolchain candidate enters qualification. |
| M2 | speculative-decoding | Consider sharing scratch when a single-sequence 27B configuration misses its fit bound by shareable scheduler bytes. |
| M3 | quantization-and-low-bit | Compare nested-plane decoding at equal realized bytes and quality for a capacity-constrained target. |
| M4 | speculative-decoding | Test a matched boosted head or budget a one-card training step once local traces put the limitation in draft acceptance. |
| M5 | speculative-decoding | Test draft-only exemplars when a served repeated-task family uses a compatible separate draft model. |
| M6 | speculative-decoding | Retain request-local RNG and filtered-score semantics for a consumer that requires reproducible stochastic sampling across slots. |
| M7 | kv-cache-program | Use phase-invariant recurrent updates and indexed pool writes where a first difference or copy profile identifies recurrent state. |
| M8 | routing-program | Compare task-specific delegation guidance against both plan-only and unguided routing before enabling heterogeneous delegation. |
| M9 | harness-program | Test hindsight allocation for a specific local distillation budget once eligible evidence-labeled trajectories exist. |
| M10 | eval-tower-program | Assess retirement separately from observed skill uplift when a named skill/model pair is scheduled for removal. |

## Hardware decisions behind the proposed boxes

| Source | MI210 | Zen 5 EPYC |
|---|---|---|
| Short-row MMVQ | At upstream head 8d9e8f2 the threshold changes from strict to inclusive when the K blocks fit in one block iteration and more than one warp participates. Recompute that capacity with the CDNA warp table. The second loop changes the order of gate-weight reads while retaining fusion and the existing shared reduction. Guard both reads and stores at partial expert rows. | The CPU dispatcher uses a different quantized dot path. Only import a short-row layout change after showing the equivalent fused access pattern. |
| Invariant dispatch | Identify whether the first difference comes from a different reduction geometry across widths, or competing atomic contributors at the same width. The full invariant arm failed the existing implementation-cost screen. HIP slowdown is unknown. | Pin IQK/llamafile selection, thread layout and reduction order in a diagnostic replay. A seed alone does not fix the logits. |
| Recurrent state | The GDN implementation uses a 64-token canonical chunk, FP32 boundary state and open-chunk scratch. Boundary state alone cannot resume an arbitrary partial chunk. Include scratch, slot epoch and rollback position in the replay contract. | Check the CPU recurrent-state view, phase transitions and vector tails. A fixed chunk has a storage and latency cost on both devices. |
| Any-Rate | Decode packed bitplanes by row. Count codebook and padding bytes, LDS bank conflicts, live tables and wave occupancy. Native FP8 is unnecessary. | Reference unpack first; use AVX-512 byte permutation on split tables where available. Compare fused dot versus pre-expansion, including NUMA-local bandwidth. |
| DFly2 | Distinguish the target layer’s KV address from the last accepted token’s sparse index. A stale slot or index after rollback breaks the contract even if the buffers fit. | Saving a separate drafter cache competes with scattered cache-line reads and expert weights. Record those costs separately for dense and sparse targets. |
| HSM/HSGD | Section 4.4 samples an aligned backbone or previous MTP state uniformly **per token position at each training step**; exponential sparse replacement is a separate variant. HSGD samples a gradient stop after the first step without changing forward values. Four-GB300 per-device memory cannot establish one-card fit. | A trained head retains the serving graph. Measure acceptance by position and total time for the chosen draft length. |
| Static expert pool | Size for 64 GB minus non-expert weights, KV, scratch and safety margin; count each cold expert upload once per long prefill. | Pin cold weights to the executing NPS4 domain. Price cold GEMV and the CPU/GPU join separately at short and long phases. |
| Partner scratch and checkpoint restore | HIP reports ROCm. Upstream scratch sharing also requires compatible backend/buffer lists and nonoverlapping execution. ON_DEVICE restore reads a host header that identifies device-resident storage. A valid host transfer timing cannot verify that reader. | Shared error containment must discard pending writes before destruction, remove partial destination state and preserve unrelated slots. CPU is a useful first regression arm. |

## Filing details

Six gpt-6.2-sol research agents participated across initial reads, deep dives, expansion and independent second reading. Root review compared the current C21 checkpoint reader, HIP backend identifier, existing kernel census, current skill evaluator and owning handoffs. The source-by-source hardware analysis and remaining source limits are in [the dive index](README.md).

Use one existing owner per box. Apply each approved box with handoff_box.py add under its track backlog. Monitor packets are prose only. Existing index rows point to these owners. Regenerate index state at approved close-out. Compute scheduling, experimental kernels and promotion follow existing owner gates.

Before each immediate empirical screen, freeze input hashes, build/configuration and split. Preserve raw paired outputs, held-out cases, and attempted, failed, skipped, invalid and abstained counts. Include baseline and A/A timing error for speed claims. Deterministic fixtures require all declared cases to pass. Formal gates allow futility-only interim looks. Missing controls yield insufficient evidence. Only source changes, fixtures and replay of retained data belong to the non-inference boxes. New model executions require separately readied inference rows.

Checkpoint recovery, skill evaluation, route replay and sampler fixtures can proceed independently. Serialize edits to a shared owner. Stochastic replay cannot settle greedy arithmetic drift. A reachability or byte census gates each corresponding hardware implementation.

### P1 · kv-cache-program

C21 state_seq_set_data constructs its device reader and checks mem_storage before the catch. Its catch only logs. KPF-17 exercises partial restore; Q8-SERVED-CKPT-COPY-1 uses the host writer and times transfers. Neither checks this failure boundary.

A source-pinned regression on two populated slots must return zero on failure, clear any partially modified destination as required, preserve the neighbor, and round-trip valid state. Repeat on a new sequence ID and in reverse slot order. Log each case and return value. Require a CPU build proof before model-backed evaluation and HIP residency proof before claiming device coverage.

Place in the `kv-prefix-fork-and-paged-attention` track backlog.

```text
- [ ] **KPF-RESTORE-RECOVERY** [non-inference] Restore destination-only error recovery for device checkpoints on the experimental kernel and add valid, absent-storage, truncated-header and partial-read regression cases.
      · done when: KPF-RESTORE-RECOVERY.json contains valid_count, failed_destination_removed, survivor_hash_equal, deferred_writes_after_failure. All valid restores succeed, no write survives discard and every neighbor hash matches.
      · gate: none        · inputs: `handoffs/active/kv-cache-program.md`
```

**Companion brief** · author `intake`. Where: `epyc-root:handoffs/active/kv-cache-program.md, epyc-root:research/deep-dives/intake-nov26-kernels/30318.md`. Approach: Restore destination-only error recovery for device checkpoints on the experimental kernel and add valid, absent-storage, truncated-header and partial-read regression cases. Acceptance: KPF-RESTORE-RECOVERY.json contains valid_count, failed_destination_removed, survivor_hash_equal, deferred_writes_after_failure. All valid restores succeed, no write survives discard and every neighbor hash matches. The owner reviews the receipt against the controls above. Compile `brief.py compile KPF-RESTORE-RECOVERY` after approved filing.

### P2 · eval-tower-program

At orchestrator faa783c7, scripts/autopilot/skill_efficacy.py:313 and :352 aggregate suite-keyed efficacy. EV-10a and AEI-RERUN-FLIP can consume a diagnostic replay while the skill-bank activation policy stays with its current owner.

Freeze archive hashes, paired seeds, grader revision, effective inventories and folds. Compare the current suite gate, no gate and selected gate on the same cells. Refit the policy on each permuted training fold. Score untouched later trials and unseen task families separately with paired intervals. Publish cell-level outcomes including missing and timed-out arms. Stop if effective-arm identity or split independence cannot be established; a gain inside the null band cannot authorize gating.

Place in the `scoring-infra-standardization` track backlog.

```text
- [ ] **EV-SKILL-NULL-REPLAY** [non-inference] Add a task-level replay report for skill gating that records effective skills, scorer requirements, within-cell shuffled labels and held-out decisions.
      · done when: EV-SKILL-NULL-REPLAY.json contains paired_cells, effective_manifest_by_arm, heldout_delta, shuffled_delta, missing_arm_count. Each cell has a traceable manifest or explicit exclusion and zero training/holdout overlap.
      · gate: none        · inputs: `handoffs/active/eval-tower-program.md`
```

**Companion brief** · author `intake`. Where: `epyc-root:handoffs/active/eval-tower-program.md, epyc-root:research/deep-dives/intake-nov26-kernels/2611.33943.md`. Approach: Add a task-level replay report for skill gating that records effective skills, scorer requirements, within-cell shuffled labels and held-out decisions. Acceptance: EV-SKILL-NULL-REPLAY.json contains paired_cells, effective_manifest_by_arm, heldout_delta, shuffled_delta, missing_arm_count. Each cell has a traceable manifest or explicit exclusion and zero training/holdout overlap. The owner reviews the receipt against the controls above. Compile `brief.py compile EV-SKILL-NULL-REPLAY` after approved filing.

### P3 · autokernel-loop

The split changes reads in fused short rows, the inclusive cutoff changes eligibility, and C17 already carries fa221af5d for odd expert stores. The measured RTX Q8 case was flat.

Pin trace digests, graph and candidate SHA. Emit op, quant type, K, rows, fused flag, width and frequency or unknown for every cell. Check later traces from each role. A verified zero closes that role. For hits compare split only, threshold only and both against current dispatch around exact-fit K. Include odd expert tails on wave64 before measuring time.

Place in the `autokernel-research-loop` track backlog.

```text
- [ ] **AK-SHORT-ROW-CENSUS** [non-inference] Count eligible fused small-K MMVQ calls in retained 27B and A3B traces at widths one through four.
      · done when: AK-SHORT-ROW-CENSUS.json contains quant_type, K, output_rows, fused, ncols, eligible_calls. All requested model/width cells have a count or an explicit unresolved reason.
      · gate: none        · inputs: `handoffs/active/autokernel-loop.md`
```

**Companion brief** · author `intake`. Where: `epyc-root:handoffs/active/autokernel-loop.md, epyc-root:research/deep-dives/intake-nov26-kernels/33019.md`. Approach: Count eligible fused small-K MMVQ calls in retained 27B and A3B traces at widths one through four. Acceptance: AK-SHORT-ROW-CENSUS.json contains quant_type, K, output_rows, fused, ncols, eligible_calls. All requested model/width cells have a count or an explicit unresolved reason. The owner reviews the receipt against the controls above. Compile `brief.py compile AK-SHORT-ROW-CENSUS` after approved filing.

### P4 · cpu-decode-roofline-program

INF-45 already owns the route tap. Reuse it for DS41 and A3B; 64 GB is total device capacity. The paper’s 512-token crossover and dual-Xeon bandwidth cannot fix the NPS4 crossover.

Freeze trace manifest, expert sizes, host bandwidth evidence and HBM reservations for weights, KV, scratch and allocator margin. Fill the remaining bytes by utility across layers. Fit on early turns, score later whole sessions. Return per-turn hits, cold rows, unique bytes, join bound and invalid/unattributed counts. Compare same capacity, loading and phase threshold to current placement and host-only. Stop if the saved bytes cannot exceed the join cost within timing uncertainty, or if route identities are missing.

Place in the `moe-routing-tap-and-locality-measurement` track backlog.

```text
- [ ] **MOE-STATIC-POOL-REPLAY** [non-inference] Replay existing per-layer expert routes against a capacity-bounded static GPU pool and price NUMA-local cold routes and deduplicated long-prefill uploads.
      · done when: MOE-STATIC-POOL-REPLAY.json contains reservations_bytes, pool_bytes, unique_upload_bytes, cold_rows, join_bound_ms. The pool fits after reservations and all route rows reconcile to resident, cold or unresolved.
      · gate: none        · inputs: `handoffs/active/cpu-decode-roofline-program.md`
```

**Companion brief** · author `intake`. Where: `epyc-root:handoffs/active/cpu-decode-roofline-program.md, epyc-root:research/deep-dives/intake-nov26-kernels/2611.11533.md`. Approach: Replay existing per-layer expert routes against a capacity-bounded static GPU pool and price NUMA-local cold routes and deduplicated long-prefill uploads. Acceptance: MOE-STATIC-POOL-REPLAY.json contains reservations_bytes, pool_bytes, unique_upload_bytes, cold_rows, join_bound_ms. The pool fits after reservations and all route rows reconcile to resident, cold or unresolved. The owner reviews the receipt against the controls above. Compile `brief.py compile MOE-STATIC-POOL-REPLAY` after approved filing.

### P5 · speculative-decoding

INF-77 consumes the sparse selection. INF-50 can separately reuse target KV on full-attention layers, but a dense model supplies no target sparsity. A contract inventory can decide whether a converter or cache export is the next real dependency.

Record exact weight/config revisions, source layer pairs, strides, dtype, ownership and one-step index timestamp. Walk representative released mappings against DS41 and the dense 27B control. Require a defined KV read and epoch across accept, reject and slot reuse before any execution probe. Mark unsupported layers and absent weights explicitly.

Place in the `dflash2-block-drafter-experimental-build` track backlog.

```text
- [ ] **DF2-TARGET-KV-CONTRACT** [non-inference] Compare the released DFly2 target and drafter mappings with the local full-attention KV layout, sparse-index epoch and rollback semantics.
      · done when: DF2-TARGET-KV-CONTRACT.json contains layer_map, kv_stride, selection_epoch, rollback_owner, missing_artifacts. Each requested architecture has an ABI verdict for accept, reject and slot reuse.
      · gate: none        · inputs: `handoffs/active/speculative-decoding.md`
```

**Companion brief** · author `intake`. Where: `epyc-root:handoffs/active/speculative-decoding.md, epyc-root:research/deep-dives/intake-nov26-kernels/2611.34776.md`. Approach: Compare the released DFly2 target and drafter mappings with the local full-attention KV layout, sparse-index epoch and rollback semantics. Acceptance: DF2-TARGET-KV-CONTRACT.json contains layer_map, kv_stride, selection_epoch, rollback_owner, missing_artifacts. Each requested architecture has an ABI verdict for accept, reject and slot reuse. The owner reviews the receipt against the controls above. Compile `brief.py compile DF2-TARGET-KV-CONTRACT` after approved filing.

### P6 · kv-cache-program

RKA-BATCH-INV-CENSUS-1 closed with five of six ops requiring changes. Q8IP-DET2 and devhandoff/Pando require a same-width baseline; fixed geometry cannot repair racy summation. This supplements GPU-27B-LONGCTX-SECOND-NONDET without reopening the full audit arm.

Freeze model, store digest, prompt bytes, state, seeds and launch choices. Replay OFF/OFF and width-1/verify on identical logits inputs where captured. Preserve first mismatched op, tensor bits, route, reduction geometry and missing captures. Hold out later long prompts. Stop on a located first mismatch or insufficient captures; measure HIP cost for that isolated path only after a matched input reproduces.

Place in the `kv-unified-stack-rollout` track backlog.

```text
- [ ] **KV-NONDET-FIRST-DIFF** [non-inference] Add fixed-width repeat and cross-width first-divergence comparisons to the long-context determinism diagnosis using retained inputs and dispatch receipts.
      · done when: KV-NONDET-FIRST-DIFF.json contains prompt_sha, repeat_pair, width_pair, first_different_op, reduction_route. Each replay distinguishes within-width variation from width-dependent differences or records missing inputs.
      · gate: none        · inputs: `handoffs/active/kv-cache-program.md`
```

**Companion brief** · author `intake`. Where: `epyc-root:handoffs/active/kv-cache-program.md, epyc-root:research/deep-dives/intake-nov26-kernels/32081.md`. Approach: Add fixed-width repeat and cross-width first-divergence comparisons to the long-context determinism diagnosis using retained inputs and dispatch receipts. Acceptance: KV-NONDET-FIRST-DIFF.json contains prompt_sha, repeat_pair, width_pair, first_different_op, reduction_route. Each replay distinguishes within-width variation from width-dependent differences or records missing inputs. The owner reviews the receipt against the controls above. Compile `brief.py compile KV-NONDET-FIRST-DIFF` after approved filing.

### P7 · cpu-decode-roofline-program

CAFE-5 treats GDN rows. A generic GDN count leaves backend-specific KDA call reachability unresolved; Intel AVX2 results do not measure Zen 5.

Pin graph, model, ISA, row lengths and trace windows; emit per-loop counts, time share and missing fields. Repeat on a later prompt. Stop on proven zero or an Amdahl bound smaller than the paired timing error. Otherwise compare scalar and AVX-512 at actual sizes, scalar tails, exceptional inputs and recurrent-state error before throughput.

Place in the `cpu-decode-roofline-program` track backlog.

```text
- [ ] **CPU-KDA-EXP-CENSUS** [non-inference] Identify whether either KDA exponential loop executes in Q38FN CPU traces and bound its contribution to decode and prefill.
      · done when: CPU-KDA-EXP-CENSUS.json contains model, graph, cpu_isa, kda_count, self_time, upper_bound. Both decode and prefill have a confirmed upper bound or an identified missing witness.
      · gate: none        · inputs: `handoffs/active/cpu-decode-roofline-program.md`
```

**Companion brief** · author `intake`. Where: `epyc-root:handoffs/active/cpu-decode-roofline-program.md, epyc-root:research/deep-dives/intake-nov26-kernels/33077.md`. Approach: Identify whether either KDA exponential loop executes in Q38FN CPU traces and bound its contribution to decode and prefill. Acceptance: CPU-KDA-EXP-CENSUS.json contains model, graph, cpu_isa, kda_count, self_time, upper_bound. Both decode and prefill have a confirmed upper bound or an identified missing witness. The owner reviews the receipt against the controls above. Compile `brief.py compile CPU-KDA-EXP-CENSUS` after approved filing.

### P8 · speculative-decoding

SPEC-PIT.1 addresses distribution equivalence. A passing PIT result cannot establish that a reported log probability refers to the deployed filtered support.

Hash rows, seeds and sampler chain; test top-k, top-p, min-p, both orders, no-op, infinities and exact ties. Compare native support to a whole-tie reference with identical inputs, then repeat on held-out row permutations. Emit every support and denominator; reject ambiguous probability labels. File a compatibility result. Serving policy requires a separate gate.

Place in the `dflash2-block-drafter-experimental-build` track backlog.

```text
- [ ] **SPEC-FILTER-TIES** [non-inference] Extend the frozen-logit sampler fixture to record retained support, drawn token and full versus post-filter probabilities at boundary ties.
      · done when: SPEC-FILTER-TIES.json contains fixture_sha, row, key, filter_order, support, token, full_logprob, retained_logprob. All frozen and held-out cases match their declared reference semantics or record the first discrepancy.
      · gate: none        · inputs: `handoffs/active/speculative-decoding.md`
```

**Companion brief** · author `intake`. Where: `epyc-root:handoffs/active/speculative-decoding.md, epyc-root:research/deep-dives/intake-nov26-kernels/9619.md`. Approach: Extend the frozen-logit sampler fixture to record retained support, drawn token and full versus post-filter probabilities at boundary ties. Acceptance: SPEC-FILTER-TIES.json contains fixture_sha, row, key, filter_order, support, token, full_logprob, retained_logprob. All frozen and held-out cases match their declared reference semantics or record the first discrepancy. The owner reviews the receipt against the controls above. Compile `brief.py compile SPEC-FILTER-TIES` after approved filing.

### P9 · kv-cache-program

Earlier replay optimization moved control counts on device. State-pool ownership, strided writes and slot safety remain separate from seed determinism and from chunk arithmetic.

Pin trace and source revisions plus the initial state; follow each pointer, dtype and byte count across gather, transition and scatter. Compare direct-write candidates to current device replay counts. Include a later trace and poisoned non-target slots. Report unresolved copies separately; stop at no remaining transfer. Require unique destination slots and read-before-write fences before any aliasing experiment.

Place in the `kv-prefix-fork-and-paged-attention` track backlog.

```text
- [ ] **KPF-STATE-COPY-CENSUS** [non-inference] Trace recurrent-state ownership and residual state-sized copies across rollback, slot reuse and phase transitions on CPU and HIP.
      · done when: KPF-STATE-COPY-CENSUS.json contains slot, dtype, source, destination, bytes, barrier, phase. Every state-sized copy in the pinned paths has one owner or an explicit unresolved alias.
      · gate: none        · inputs: `handoffs/active/kv-cache-program.md`
```

**Companion brief** · author `intake`. Where: `epyc-root:handoffs/active/kv-cache-program.md, epyc-root:research/deep-dives/intake-nov26-kernels/9644.md`. Approach: Trace recurrent-state ownership and residual state-sized copies across rollback, slot reuse and phase transitions on CPU and HIP. Acceptance: KPF-STATE-COPY-CENSUS.json contains slot, dtype, source, destination, bytes, barrier, phase. Every state-sized copy in the pinned paths has one owner or an explicit unresolved alias. The owner reviews the receipt against the controls above. Compile `brief.py compile KPF-STATE-COPY-CENSUS` after approved filing.

### M1 · rocm-kernel-authoring

DF2-11-BF16 concerns the executed BF16 route. The upstream patch addresses compiler operand types and supplies no CDNA runtime measurement.

Trigger on an actual LLVM 23 qualification build for gfx90a. Compare old/new fragments and emitted ISA at both compilers; run BF16 op parity and DF2 target-route smoke using the candidate binary.

### M2 · speculative-decoding

The upstream guard literally requires CUDA; the fork names HIP ROCm. The C21 scheduler lacks the sharing primitive. DEV-INJECT removes a transfer and does not establish safe aliasing.

Trigger on a measured fit failure with target/draft scratch live ranges that do not overlap. Record separate buffers, buffer types, async completion, realloc and actual peak. Test eligibility by capabilities and preserve independent fallback.

### M3 · quantization-and-low-bit

Single-rate comparisons need all LUT and alignment overhead. No MI210 or Zen5 performance evidence; on-device LPDDR energy estimate cannot rank either platform.

Trigger when a proposed multi-rate deployment identifies the exact layers/rates and an incumbent that misses its fit or quality target. Run integer bit unpack against reference bytes, compare shared row tables in LDS and AVX-512 byte-permute/split tables with scalar tails, then paired KLD and held-out throughput against incumbent EXL3/GGUF.

### M4 · speculative-decoding

Published memory is per GPU in a four-GB300 configuration. CPU and MI210 serving need acceptance-by-position and wall time at the same K before a head switch.

Trigger on a per-position acceptance deficit with a compatible frozen backbone/head pair and priced training baseline. Log optimizer/gradient/activation/weights and allocator peak in a single-device microbatch dry fit; retain HSM mix and HSGD detach probability separately.

### M5 · speculative-decoding

The existing DFlash2 path shares model features; a classical separate-proposal verifier is the consumer. Additional KV and prefill may overwhelm acceptance gains.

Require stable shared tokenizer, true proposal probabilities and a family with disjoint exemplar and evaluation prompts. Compare target alone, symmetric draft, length-matched irrelevant and task-matched exemplars at equal cache state; measure TTFT and full session time.

### M6 · speculative-decoding

SPEC-RNG.1 at lines 679–688 already tested keyed RNG. Position-keyed draws do not resolve earlier logit drift; no reason to repeat a served sweep merely from this release.

Trigger on a recorded fixed-logit replay difference at equal seed and offset under reorder, recycle or filter-boundary ties, or a consumer requiring full versus retained log probabilities. Compare frozen logits/filters first.

### M7 · kv-cache-program

No native CUTE/SM100 kernel on MI210; fixed chunking can sacrifice occupancy and state pooling needs an ownership and alias contract. CPU state rows are already under CAFE-5.

Trigger on equal initial state/input and first mismatch in the GDN transition across phase or a measured recurrent-state copy. Compare fixed chunking, zero padding and tail at a fixed logical token. Verify poison slots, repeated indices, dtype and fences separately for the pool branch.

### M8 · routing-program

P3 chaining is gated. Delegation report persistence records handles; it cannot by itself price work or validate a policy. Hosted API dollars do not price co-resident EPYC workers.

Trigger on retained lead/worker traces with attributed worker spans and independent task groups; freeze judge and rubric, measure task quality, cache-adjusted tokens, end-to-end time, queueing and CPU/GPU occupancy. Count rejected/failed work in every arm.

### M9 · harness-program

HIL-16b is eval instrumentation. Neither replay nor a confidence gate alone trains a student, and the paper’s environment and teacher budget are not an EPYC estimate.

Trigger on a local student/teacher run with verified downstream outcomes and a fixed replay budget. Compare random and position-matched selection to evidence selection on unseen tasks, preserve all rejected prefixes, and separately score confidence calibration.

### M10 · eval-tower-program

A low marginal lift can reflect a task that both arms fail. EV-10a measures efficacy; a per-model retirement policy needs evidence of unaided competence.

Freeze baseline unaided success, skill-on/skill-off trials, invalid calls and retirement rule; reserve new tasks/trials, check retained reward and false retirements before withdrawing any skill.

## Complete recommendation mapping

| Ledger row | Source or review | Retained recommendation | Terminal plan mapping |
|---|---|---|---|
| RI-2982 | intake-2982#record | On an experimental tree compare the current compiler and a clang-23 candidate on gfx90a, verify emitted BF16 MFMA and run a small BF16 correctness smoke only if planning toolchain adoption. | M1 |
| RI-2983 | intake-2983#record | First count reachable fused small-K rows in current MI210 roles; if hit, compare baseline, split only, and split plus inclusive threshold at neighboring K and odd M, with token throughput and output parity. | P3 |
| RI-2984 | intake-2984#record | Reuse op-level batch tests and route receipts on the existing MI210 census, then do one fixed-input Zen5 replay across single and multiple columns for the first divergent op. Preserve the existing full audit-arm gate. | P6 |
| RI-2985 | intake-2985#record | Review the target sampler RNG cursor lifecycle for stable per-request coordinates under permutations, batch resize and slot recycle; borrow a small backend-neutral metamorphic fixture if current tests lack it. Treat state slots as a related pattern for existing restore ownership. | M6 |
| RI-2986 | intake-2986#record | Check model graph and CPU traces for KDA reachability. If reachable, compare scalar versus vector at real prefill/TG shapes with exponent and recurrent-state error/greedy checks; stop once the op cannot explain meaningful end-to-end time. | P7 |
| RI-2987 | intake-2987#record | On an eligible DS41 or Q38FN low-bit lane, use real expert-tensor shapes to compare normalized format bytes, arithmetic correctness and decode/prefill latency to incumbent GGUF, then equal-bytes quality before funding a model port. Keep precision switching a distinct experiment. | M3 |
| RI-2988 | intake-2988#record | Inventory exact artifacts and indexed-KV ABI first; compare replayed index coverage and KV bytes in the DS41 lane without reopening held tests. Promote to served throughput only when paired weights and index custody are available. | P5 |
| RI-2989 | intake-2989#record | Prioritize released boosted checkpoint with compatible format and same serving graph; run early-position and tail acceptance plus latency per chosen K on both devices. If training is required, perform dry-fit accounting and one-step peak reserve check against an explicit margin. | M4 |
| RI-2990 | intake-2990#record | Add one benchmark-only immutable draft-prefix arm to a separate-checkpoint path, with zero-exemplar same-token-budget control, target-only reference, held-out nonleaking exemplars, exact sampled-distribution check and session TTFT/time by cache state. Keep verifier prompt and sampler identical. | M5 |
| RI-2991 | intake-2991#record | Replay small set of saved DS41 route traces as placement + bytes feasibility, independent of held DS41 inference. Measure resident-route fraction, rows per cold expert, dedup ratio and timing estimates for same-placement CPU-only cold, GPU weight upload and mixed execution. If favorable, compare matched upload threshold/loading and parity before porting HIP graph. | P4 |
| RI-2992 | intake-2992#record | Locate scheduler sharing primitive and audit ordering, lifetime, realloc and separate fallback. If concrete MI210 fit is blocked by scratch, prototype under experimental ROCm eligibility and compare achieved peak VRAM, greedy exactness and throughput with overlap controls. | M2 |
| RI-2993 | intake-2993#record | Compare #27530 cleanup prerequisites against an experimental branch and port the minimal defensive guard with the isolation test. Verify valid restore, recoverable invalid restore and unchanged neighboring sequence on Zen5 and actual gfx90a resident state. | P1 |
| RI-2994 | intake-2994#record | Read existing P3 bounded worker traces to freeze task-family groups, failure categories and request-cost attribution. On unseen groups compare same lead alone, plan-only, unguided and profile tiers with the same available lead/worker pair. Log invalid, skipped and failed runs; predeclare minimum quality and latency margin and sample cap, stop if existing traces cannot identify routed spans. No P3 activation decision follows an offline or mock result. | M8 |
| RI-2995 | intake-2995#record | Attach an observational sidecar to the remaining EV-10a paired-mutation A/B: verify normalized effective skill manifests per arm and audit scorer constraints against visible task text, retain paired item outcomes and full denominator. Report within-cell shuffled null, untouched later draws for decisions, and task-family holdout for generalization. Reuse the suite-level gate with diagnostic sidecar output. Stop at a preregistered valid-pair cap or declared precision and do not use aggregate efficacy as evidence of task-level stability. | P2 |
| RI-2996 | intake-2996#record | Use existing HIL-16a source-era clean trace manifests and HIL-12/13 first-visible-deviation labels if joinable. Freeze original trajectories and hold out whole tasks; compare equal-sized evidence-ranked, random and depth-ranked turn lists for externally judged hit rate, late-turn recall and abstentions. Keep confounded or missing cases in denominator. Stop if no independent decision-turn labels or if equal-budget selection offers no material held-out gain. Keep existing four-arm replay acceptance independent of this diagnostic; only a positive diagnostic warrants testing its turn priorities in replay. | M9 |
| RI-2997 | intake-2997#record | Use as companion evidence for the paper. Under INF-80 compare effective bytes and scalar decode on frozen EXL3 fixtures and held-out KLD/model inputs before a single AVX-512 or HIP microbench. Freeze baseline, raw row outputs, invalid denominators, and latency/quality stops. | M3 |
| RI-2998 | intake-2998#record | Apply precommitted held-out policy and within-cell shuffled calibration at any SkillBank promotion. Freeze model/task/harness and thresholds, use disjoint tasks or new trials, archive per-trial decision/reward/graded/invalid/abstention denominators, compare always-load versus gate with existing paired and rerun logic, and predeclare minimum benefit and shuffle separation. | P2 |
| RI-2999 | intake-2999#record | Use as companion to DFly2. For INF-77 pin target/drafter versions and prove read-only released weight/latent/layer/last-accepted-position mappings, estimate gather bytes versus matched-width MTP/DSpark, then gate experimental serving if economics justify it. INF-50 can reuse target context on full-attention layers separately from native sparse index sharing. | P5 |
| RI-3000 | intake-3000#record | For an experimental cache candidate apply discard-before-destruction to owned buffer-reader failure exits and scope hybrid rollback correctly. Gate defensive isolated-state correctness with unaffected calls, preserved-unmodified and removed-modified outcomes across host/device. Q8-SERVED-CKPT-COPY-1 consumes the result and retains its timing gate. | P1 |
| RI-3001 | intake-3001#record | Fold into FlashInfer v0.7.6 action. If current per-op traces isolate GDN cross-phase mismatch, first establish same-bit rows and boundary state on fixed held-out shapes spanning prefill/chunk/decode/span and slot changes with witnessed valid domains. Gate any opt-in candidate against raw A/A, latency and VRAM. Existing RS-REPLAY tests rollback correctness/speed, a separate axis. | M7 |
| RI-3002 | intake-3002#record | Retain the SPEC-RNG.1 DO-NOT-CARRY result. If a named consumer requires same-seed cross-batch replay, first attribute failures by reusing a frozen-logit, same-key fixture with moved slot, batch width and request order. Keep within-stream repeatability and backend logit equality in distinct checks, and preserve the existing serving RNG until a consumer benefit is demonstrated. | M6 |
| RI-3003 | intake-3003#record | Extend the existing SPEC-PIT post-sampling fixture with exact ties just above/below the top-p boundary, filter order, -inf and no-op cases, and compare named support, sampled token and normalized probability against the current served sampler on identical rows/keys. Persist native versus whole-tie results and full-row versus post-filter logprob labels distinctly. Promote a new policy only if a consumer requests it and the same-denominator gate passes. | P8 |
| RI-3004 | intake-3004#record | Census the EPYC DFlash2/recurrent state path for residual state-sized copies versus direct writes and bound bytes/ms on both hardware paths. Reuse existing state controls, keeping a CPU fixture for permuted/noncontiguous slots, null initialization, alias rejection and slot reset/reuse. Only carry a direct-write arm when the current capture identifies a remaining copy boundary and its slot owner can enforce uniqueness and read-before-write lifecycle. | P9 |
| RI-3005 | intake-3005#record | Retain as a design for reversible retirement only when a SkillBank owner proposes a specific existing model/skill pair for suppression. Then freeze behavior-specific task families, verifier and model identity, include untouched-on-policy evaluation and challenge probes with an external witness, preserve abstentions and invalid counts, compare full library versus reversible removal with per-task receipts, and predeclare tolerated regression and restoration conditions. EV-10a still validates mutation efficacy by paired per-suite delta; do not reuse retirement labels as loader efficacy or automatically suppress rules/artifacts. | M10 |

## Stage-3 filing payload

```json
{
  "format_version": 2,
  "entry_updates": [
    {
      "id": "intake-2993",
      "integration_disposition": "integrated",
      "handoffs_updated": [
        "handoffs/active/kv-cache-program.md"
      ],
      "handoffs_created": [],
      "disposition_evidence": [
        "Restore destination-only error recovery for device checkpoints on the experimental kernel and add valid, absent-storage, truncated-header and partial-read regression cases. A source-pinned regression on two populated slots must return zero on failure, clear any partially modified destination as required, preserve the neighbor, and round-trip valid state. Repeat on a new sequence ID and in reverse slot order. Log each case and return value. Require a CPU build proof before model-backed evaluation and HIP residency proof before claiming device coverage."
      ]
    },
    {
      "id": "intake-3000",
      "integration_disposition": "integrated",
      "handoffs_updated": [
        "handoffs/active/kv-cache-program.md"
      ],
      "handoffs_created": [],
      "disposition_evidence": [
        "Restore destination-only error recovery for device checkpoints on the experimental kernel and add valid, absent-storage, truncated-header and partial-read regression cases. A source-pinned regression on two populated slots must return zero on failure, clear any partially modified destination as required, preserve the neighbor, and round-trip valid state. Repeat on a new sequence ID and in reverse slot order. Log each case and return value. Require a CPU build proof before model-backed evaluation and HIP residency proof before claiming device coverage."
      ]
    },
    {
      "id": "intake-2995",
      "integration_disposition": "integrated",
      "handoffs_updated": [
        "handoffs/active/eval-tower-program.md"
      ],
      "handoffs_created": [],
      "disposition_evidence": [
        "Add a task-level replay report for skill gating that records effective skills, scorer requirements, within-cell shuffled labels and held-out decisions. Freeze archive hashes, paired seeds, grader revision, effective inventories and folds. Compare the current suite gate, no gate and selected gate on the same cells. Refit the policy on each permuted training fold. Score untouched later trials and unseen task families separately with paired intervals. Publish cell-level outcomes including missing and timed-out arms. Stop if effective-arm identity or split independence cannot be established; a gain inside the null band cannot authorize gating."
      ]
    },
    {
      "id": "intake-2998",
      "integration_disposition": "integrated",
      "handoffs_updated": [
        "handoffs/active/eval-tower-program.md"
      ],
      "handoffs_created": [],
      "disposition_evidence": [
        "Add a task-level replay report for skill gating that records effective skills, scorer requirements, within-cell shuffled labels and held-out decisions. Freeze archive hashes, paired seeds, grader revision, effective inventories and folds. Compare the current suite gate, no gate and selected gate on the same cells. Refit the policy on each permuted training fold. Score untouched later trials and unseen task families separately with paired intervals. Publish cell-level outcomes including missing and timed-out arms. Stop if effective-arm identity or split independence cannot be established; a gain inside the null band cannot authorize gating."
      ]
    },
    {
      "id": "intake-2983",
      "integration_disposition": "integrated",
      "handoffs_updated": [
        "handoffs/active/autokernel-loop.md"
      ],
      "handoffs_created": [],
      "disposition_evidence": [
        "Count eligible fused small-K MMVQ calls in retained 27B and A3B traces at widths one through four. Pin trace digests, graph and candidate SHA. Emit op, quant type, K, rows, fused flag, width and frequency or unknown for every cell. Check later traces from each role. A verified zero closes that role. For hits compare split only, threshold only and both against current dispatch around exact-fit K. Include odd expert tails on wave64 before measuring time."
      ]
    },
    {
      "id": "intake-2991",
      "integration_disposition": "integrated",
      "handoffs_updated": [
        "handoffs/active/cpu-decode-roofline-program.md"
      ],
      "handoffs_created": [],
      "disposition_evidence": [
        "Replay existing per-layer expert routes against a capacity-bounded static GPU pool and price NUMA-local cold routes and deduplicated long-prefill uploads. Freeze trace manifest, expert sizes, host bandwidth evidence and HBM reservations for weights, KV, scratch and allocator margin. Fill the remaining bytes by utility across layers. Fit on early turns, score later whole sessions. Return per-turn hits, cold rows, unique bytes, join bound and invalid/unattributed counts. Compare same capacity, loading and phase threshold to current placement and host-only. Stop if the saved bytes cannot exceed the join cost within timing uncertainty, or if route identities are missing."
      ]
    },
    {
      "id": "intake-2988",
      "integration_disposition": "integrated",
      "handoffs_updated": [
        "handoffs/active/speculative-decoding.md"
      ],
      "handoffs_created": [],
      "disposition_evidence": [
        "Compare the released DFly2 target and drafter mappings with the local full-attention KV layout, sparse-index epoch and rollback semantics. Record exact weight/config revisions, source layer pairs, strides, dtype, ownership and one-step index timestamp. Walk representative released mappings against DS41 and the dense 27B control. Require a defined KV read and epoch across accept, reject and slot reuse before any execution probe. Mark unsupported layers and absent weights explicitly."
      ]
    },
    {
      "id": "intake-2999",
      "integration_disposition": "integrated",
      "handoffs_updated": [
        "handoffs/active/speculative-decoding.md"
      ],
      "handoffs_created": [],
      "disposition_evidence": [
        "Compare the released DFly2 target and drafter mappings with the local full-attention KV layout, sparse-index epoch and rollback semantics. Record exact weight/config revisions, source layer pairs, strides, dtype, ownership and one-step index timestamp. Walk representative released mappings against DS41 and the dense 27B control. Require a defined KV read and epoch across accept, reject and slot reuse before any execution probe. Mark unsupported layers and absent weights explicitly."
      ]
    },
    {
      "id": "intake-2984",
      "integration_disposition": "integrated",
      "handoffs_updated": [
        "handoffs/active/kv-cache-program.md"
      ],
      "handoffs_created": [],
      "disposition_evidence": [
        "Add fixed-width repeat and cross-width first-divergence comparisons to the long-context determinism diagnosis using retained inputs and dispatch receipts. Freeze model, store digest, prompt bytes, state, seeds and launch choices. Replay OFF/OFF and width-1/verify on identical logits inputs where captured. Preserve first mismatched op, tensor bits, route, reduction geometry and missing captures. Hold out later long prompts. Stop on a located first mismatch or insufficient captures; measure HIP cost for that isolated path only after a matched input reproduces."
      ]
    },
    {
      "id": "intake-2986",
      "integration_disposition": "integrated",
      "handoffs_updated": [
        "handoffs/active/cpu-decode-roofline-program.md"
      ],
      "handoffs_created": [],
      "disposition_evidence": [
        "Identify whether either KDA exponential loop executes in Q38FN CPU traces and bound its contribution to decode and prefill. Pin graph, model, ISA, row lengths and trace windows; emit per-loop counts, time share and missing fields. Repeat on a later prompt. Stop on proven zero or an Amdahl bound smaller than the paired timing error. Otherwise compare scalar and AVX-512 at actual sizes, scalar tails, exceptional inputs and recurrent-state error before throughput."
      ]
    },
    {
      "id": "intake-3003",
      "integration_disposition": "integrated",
      "handoffs_updated": [
        "handoffs/active/speculative-decoding.md"
      ],
      "handoffs_created": [],
      "disposition_evidence": [
        "Extend the frozen-logit sampler fixture to record retained support, drawn token and full versus post-filter probabilities at boundary ties. Hash rows, seeds and sampler chain; test top-k, top-p, min-p, both orders, no-op, infinities and exact ties. Compare native support to a whole-tie reference with identical inputs, then repeat on held-out row permutations. Emit every support and denominator; reject ambiguous probability labels. File a compatibility result. Serving policy requires a separate gate."
      ]
    },
    {
      "id": "intake-3004",
      "integration_disposition": "integrated",
      "handoffs_updated": [
        "handoffs/active/kv-cache-program.md"
      ],
      "handoffs_created": [],
      "disposition_evidence": [
        "Trace recurrent-state ownership and residual state-sized copies across rollback, slot reuse and phase transitions on CPU and HIP. Pin trace and source revisions plus the initial state; follow each pointer, dtype and byte count across gather, transition and scatter. Compare direct-write candidates to current device replay counts. Include a later trace and poisoned non-target slots. Report unresolved copies separately; stop at no remaining transfer. Require unique destination slots and read-before-write fences before any aliasing experiment."
      ]
    },
    {
      "id": "intake-2982",
      "integration_disposition": "monitor",
      "handoffs_updated": [
        "handoffs/active/rocm-kernel-authoring.md"
      ],
      "handoffs_created": [],
      "disposition_evidence": [
        "Check BF16 MFMA compiler compatibility when a clang-23 toolchain candidate enters qualification. Trigger on an actual LLVM 23 qualification build for gfx90a. Compare old/new fragments and emitted ISA at both compilers; run BF16 op parity and DF2 target-route smoke using the candidate binary."
      ]
    },
    {
      "id": "intake-2992",
      "integration_disposition": "monitor",
      "handoffs_updated": [
        "handoffs/active/speculative-decoding.md"
      ],
      "handoffs_created": [],
      "disposition_evidence": [
        "Consider sharing scratch when a single-sequence 27B configuration misses its fit bound by shareable scheduler bytes. Trigger on a measured fit failure with target/draft scratch live ranges that do not overlap. Record separate buffers, buffer types, async completion, realloc and actual peak. Test eligibility by capabilities and preserve independent fallback."
      ]
    },
    {
      "id": "intake-2987",
      "integration_disposition": "monitor",
      "handoffs_updated": [
        "handoffs/active/quantization-and-low-bit.md"
      ],
      "handoffs_created": [],
      "disposition_evidence": [
        "Compare nested-plane decoding at equal realized bytes and quality for a capacity-constrained target. Trigger when a proposed multi-rate deployment identifies the exact layers/rates and an incumbent that misses its fit or quality target. Run integer bit unpack against reference bytes, compare shared row tables in LDS and AVX-512 byte-permute/split tables with scalar tails, then paired KLD and held-out throughput against incumbent EXL3/GGUF."
      ]
    },
    {
      "id": "intake-2997",
      "integration_disposition": "monitor",
      "handoffs_updated": [
        "handoffs/active/quantization-and-low-bit.md"
      ],
      "handoffs_created": [],
      "disposition_evidence": [
        "Compare nested-plane decoding at equal realized bytes and quality for a capacity-constrained target. Trigger when a proposed multi-rate deployment identifies the exact layers/rates and an incumbent that misses its fit or quality target. Run integer bit unpack against reference bytes, compare shared row tables in LDS and AVX-512 byte-permute/split tables with scalar tails, then paired KLD and held-out throughput against incumbent EXL3/GGUF."
      ]
    },
    {
      "id": "intake-2989",
      "integration_disposition": "monitor",
      "handoffs_updated": [
        "handoffs/active/speculative-decoding.md"
      ],
      "handoffs_created": [],
      "disposition_evidence": [
        "Test a matched boosted head or budget a one-card training step once local traces put the limitation in draft acceptance. Trigger on a per-position acceptance deficit with a compatible frozen backbone/head pair and priced training baseline. Log optimizer/gradient/activation/weights and allocator peak in a single-device microbatch dry fit; retain HSM mix and HSGD detach probability separately."
      ]
    },
    {
      "id": "intake-2990",
      "integration_disposition": "monitor",
      "handoffs_updated": [
        "handoffs/active/speculative-decoding.md"
      ],
      "handoffs_created": [],
      "disposition_evidence": [
        "Test draft-only exemplars when a served repeated-task family uses a compatible separate draft model. Require stable shared tokenizer, true proposal probabilities and a family with disjoint exemplar and evaluation prompts. Compare target alone, symmetric draft, length-matched irrelevant and task-matched exemplars at equal cache state; measure TTFT and full session time."
      ]
    },
    {
      "id": "intake-2985",
      "integration_disposition": "monitor",
      "handoffs_updated": [
        "handoffs/active/speculative-decoding.md"
      ],
      "handoffs_created": [],
      "disposition_evidence": [
        "Retain request-local RNG and filtered-score semantics for a consumer that requires reproducible stochastic sampling across slots. Trigger on a recorded fixed-logit replay difference at equal seed and offset under reorder, recycle or filter-boundary ties, or a consumer requiring full versus retained log probabilities. Compare frozen logits/filters first."
      ]
    },
    {
      "id": "intake-3002",
      "integration_disposition": "monitor",
      "handoffs_updated": [
        "handoffs/active/speculative-decoding.md"
      ],
      "handoffs_created": [],
      "disposition_evidence": [
        "Retain request-local RNG and filtered-score semantics for a consumer that requires reproducible stochastic sampling across slots. Trigger on a recorded fixed-logit replay difference at equal seed and offset under reorder, recycle or filter-boundary ties, or a consumer requiring full versus retained log probabilities. Compare frozen logits/filters first."
      ]
    },
    {
      "id": "intake-3001",
      "integration_disposition": "monitor",
      "handoffs_updated": [
        "handoffs/active/kv-cache-program.md"
      ],
      "handoffs_created": [],
      "disposition_evidence": [
        "Use phase-invariant recurrent updates and indexed pool writes where a first difference or copy profile identifies recurrent state. Trigger on equal initial state/input and first mismatch in the GDN transition across phase or a measured recurrent-state copy. Compare fixed chunking, zero padding and tail at a fixed logical token. Verify poison slots, repeated indices, dtype and fences separately for the pool branch."
      ]
    },
    {
      "id": "intake-2994",
      "integration_disposition": "monitor",
      "handoffs_updated": [
        "handoffs/active/routing-program.md"
      ],
      "handoffs_created": [],
      "disposition_evidence": [
        "Compare task-specific delegation guidance against both plan-only and unguided routing before enabling heterogeneous delegation. Trigger on retained lead/worker traces with attributed worker spans and independent task groups; freeze judge and rubric, measure task quality, cache-adjusted tokens, end-to-end time, queueing and CPU/GPU occupancy. Count rejected/failed work in every arm."
      ]
    },
    {
      "id": "intake-2996",
      "integration_disposition": "monitor",
      "handoffs_updated": [
        "handoffs/active/harness-program.md"
      ],
      "handoffs_created": [],
      "disposition_evidence": [
        "Test hindsight allocation for a specific local distillation budget once eligible evidence-labeled trajectories exist. Trigger on a local student/teacher run with verified downstream outcomes and a fixed replay budget. Compare random and position-matched selection to evidence selection on unseen tasks, preserve all rejected prefixes, and separately score confidence calibration."
      ]
    },
    {
      "id": "intake-3005",
      "integration_disposition": "monitor",
      "handoffs_updated": [
        "handoffs/active/eval-tower-program.md"
      ],
      "handoffs_created": [],
      "disposition_evidence": [
        "Assess retirement separately from observed skill uplift when a named skill/model pair is scheduled for removal. Freeze baseline unaided success, skill-on/skill-off trials, invalid calls and retirement rule; reserve new tasks/trials, check retained reward and false retirements before withdrawing any skill."
      ]
    }
  ],
  "opportunity_reviews": {
    "P1": {
      "project_objective": "Restore destination-only error recovery for device checkpoints on the experimental kernel and add valid, absent-storage, truncated-header and partial-read regression cases.",
      "implementation_ref": "handoffs/active/kv-cache-program.md:797 scopes existing CPU PARTIAL_ONLY coverage; active gfx90a restore work is under KPF-17.4.; Upstream src/llama-context.cpp and src/llama-memory-hybrid.cpp, src/llama-io.h and tests/test-save-load-state.cpp @ 47ad34a. C21 src/llama-context.cpp:L3265-L3288,L3530-L3567,L3683-L3703, src/llama-memory-hybrid.cpp:L208-L213 @ 98ff8a4. handoffs/active/rocm-kernel-authoring.md:L1174-L1176 @ a660ead.",
      "gap": "C21 state_seq_set_data constructs its device reader and checks mem_storage before the catch. Its catch only logs. KPF-17 exercises partial restore; Q8-SERVED-CKPT-COPY-1 uses the host writer and times transfers. Neither checks this failure boundary.",
      "operational_change": "Restore destination-only error recovery for device checkpoints on the experimental kernel and add valid, absent-storage, truncated-header and partial-read regression cases.",
      "benefit_direction": "A source-pinned regression on two populated slots must return zero on failure, clear any partially modified destination as required, preserve the neighbor, and round-trip valid state. Repeat on a new sequence ID and in reverse slot order. Log each case and return value. Require a CPU build proof before model-backed evaluation and HIP residency proof before claiming device coverage.",
      "owner": "handoffs/active/kv-cache-program.md",
      "execution_conditions": "A source-pinned regression on two populated slots must return zero on failure, clear any partially modified destination as required, preserve the neighbor, and round-trip valid state. Repeat on a new sequence ID and in reverse slot order. Log each case and return value. Require a CPU build proof before model-backed evaluation and HIP residency proof before claiming device coverage.",
      "closure_basis": "C21 state_seq_set_data constructs its device reader and checks mem_storage before the catch. Its catch only logs. KPF-17 exercises partial restore; Q8-SERVED-CKPT-COPY-1 uses the host writer and times transfers. Neither checks this failure boundary."
    },
    "P2": {
      "project_objective": "Add a task-level replay report for skill gating that records effective skills, scorer requirements, within-cell shuffled labels and held-out decisions.",
      "implementation_ref": "Pinned EV-10a and EV-10f describe evaluate_skill_efficacy and evaluate_skill_efficacy_split in epyc-orchestrator/scripts/autopilot/skill_efficacy.py; default-off accept wiring is pinned in the handoff to 924ca50 and the suite aggregates cannot identify task regressions. Whether manifests already exist elsewhere requires current orchestrator inspection; checkout absent in the pinned lane.; reanalysis/skillgate_checks.py:L620-L647,L657-L712; reanalysis/results/{base,null,split,tasks}.json and paper/main.tex:L246-L288,L322-L328 @ eef0fae. handoffs/active/eval-tower-program.md:L3206-L3214 @ a660ead and epyc-orchestrator scripts/autopilot/paired_stats.py:L310-L370 implement rerun control; SkillBank is downstream.",
      "gap": "At orchestrator faa783c7, scripts/autopilot/skill_efficacy.py:313 and :352 aggregate suite-keyed efficacy. EV-10a and AEI-RERUN-FLIP can consume a diagnostic replay while the skill-bank activation policy stays with its current owner.",
      "operational_change": "Add a task-level replay report for skill gating that records effective skills, scorer requirements, within-cell shuffled labels and held-out decisions.",
      "benefit_direction": "Freeze archive hashes, paired seeds, grader revision, effective inventories and folds. Compare the current suite gate, no gate and selected gate on the same cells. Refit the policy on each permuted training fold. Score untouched later trials and unseen task families separately with paired intervals. Publish cell-level outcomes including missing and timed-out arms. Stop if effective-arm identity or split independence cannot be established; a gain inside the null band cannot authorize gating.",
      "owner": "handoffs/active/eval-tower-program.md",
      "execution_conditions": "Freeze archive hashes, paired seeds, grader revision, effective inventories and folds. Compare the current suite gate, no gate and selected gate on the same cells. Refit the policy on each permuted training fold. Score untouched later trials and unseen task families separately with paired intervals. Publish cell-level outcomes including missing and timed-out arms. Stop if effective-arm identity or split independence cannot be established; a gain inside the null band cannot authorize gating.",
      "closure_basis": "At orchestrator faa783c7, scripts/autopilot/skill_efficacy.py:313 and :352 aggregate suite-keyed efficacy. EV-10a and AEI-RERUN-FLIP can consume a diagnostic replay while the skill-bank activation policy stays with its current owner."
    },
    "P3": {
      "project_objective": "Count eligible fused small-K MMVQ calls in retained 27B and A3B traces at widths one through four.",
      "implementation_ref": "handoffs/active/kernel-champion-and-promotion.md MMID-Q8-N1-ODDM is the boundary regression to retain; upstream ggml/src/ggml-cuda/mmvq.cu and tests/test-backend-ops.cpp.",
      "gap": "The split changes reads in fused short rows, the inclusive cutoff changes eligibility, and C17 already carries fa221af5d for odd expert stores. The measured RTX Q8 case was flat.",
      "operational_change": "Count eligible fused small-K MMVQ calls in retained 27B and A3B traces at widths one through four.",
      "benefit_direction": "Pin trace digests, graph and candidate SHA. Emit op, quant type, K, rows, fused flag, width and frequency or unknown for every cell. Check later traces from each role. A verified zero closes that role. For hits compare split only, threshold only and both against current dispatch around exact-fit K. Include odd expert tails on wave64 before measuring time.",
      "owner": "handoffs/active/autokernel-loop.md",
      "execution_conditions": "Pin trace digests, graph and candidate SHA. Emit op, quant type, K, rows, fused flag, width and frequency or unknown for every cell. Check later traces from each role. A verified zero closes that role. For hits compare split only, threshold only and both against current dispatch around exact-fit K. Include odd expert tails on wave64 before measuring time.",
      "closure_basis": "The split changes reads in fused short rows, the inclusive cutoff changes eligibility, and C17 already carries fa221af5d for odd expert stores. The measured RTX Q8 case was flat."
    },
    "P4": {
      "project_objective": "Replay existing per-layer expert routes against a capacity-bounded static GPU pool and price NUMA-local cold routes and deduplicated long-prefill uploads.",
      "implementation_ref": "handoffs/active/deepseek-v41-flash-evaluation.md:1441 (existing pp512 MUL_MAT_ID premise); handoffs/completed/deepseek-v4-flash-cpu-port.md",
      "gap": "INF-45 already owns the route tap. Reuse it for DS41 and A3B; 64 GB is total device capacity. The paper’s 512-token crossover and dual-Xeon bandwidth cannot fix the NPS4 crossover.",
      "operational_change": "Replay existing per-layer expert routes against a capacity-bounded static GPU pool and price NUMA-local cold routes and deduplicated long-prefill uploads.",
      "benefit_direction": "Freeze trace manifest, expert sizes, host bandwidth evidence and HBM reservations for weights, KV, scratch and allocator margin. Fill the remaining bytes by utility across layers. Fit on early turns, score later whole sessions. Return per-turn hits, cold rows, unique bytes, join bound and invalid/unattributed counts. Compare same capacity, loading and phase threshold to current placement and host-only. Stop if the saved bytes cannot exceed the join cost within timing uncertainty, or if route identities are missing.",
      "owner": "handoffs/active/cpu-decode-roofline-program.md",
      "execution_conditions": "Freeze trace manifest, expert sizes, host bandwidth evidence and HBM reservations for weights, KV, scratch and allocator margin. Fill the remaining bytes by utility across layers. Fit on early turns, score later whole sessions. Return per-turn hits, cold rows, unique bytes, join bound and invalid/unattributed counts. Compare same capacity, loading and phase threshold to current placement and host-only. Stop if the saved bytes cannot exceed the join cost within timing uncertainty, or if route identities are missing.",
      "closure_basis": "INF-45 already owns the route tap. Reuse it for DS41 and A3B; 64 GB is total device capacity. The paper’s 512-token crossover and dual-Xeon bandwidth cannot fix the NPS4 crossover."
    },
    "P5": {
      "project_objective": "Compare the released DFly2 target and drafter mappings with the local full-attention KV layout, sparse-index epoch and rollback semantics.",
      "implementation_ref": "handoffs/active/speculative-decoding.md:1024 (current block-drafter control); handoffs/completed/deepseek-v4-flash-0731-dspark.md; docs/concepts/dfly2.md:L9-L45, configs/vllm_dsv41_flash_dfly2.yaml and angelspec/config/dfly2_dsv41_flash_draft_config.json @ e02ea36. handoffs/active/deepseek-v41-flash-evaluation.md:L1663-L1669,L1786-L1806 @ a660ead.",
      "gap": "INF-77 consumes the sparse selection. INF-50 can separately reuse target KV on full-attention layers, but a dense model supplies no target sparsity. A contract inventory can decide whether a converter or cache export is the next real dependency.",
      "operational_change": "Compare the released DFly2 target and drafter mappings with the local full-attention KV layout, sparse-index epoch and rollback semantics.",
      "benefit_direction": "Record exact weight/config revisions, source layer pairs, strides, dtype, ownership and one-step index timestamp. Walk representative released mappings against DS41 and the dense 27B control. Require a defined KV read and epoch across accept, reject and slot reuse before any execution probe. Mark unsupported layers and absent weights explicitly.",
      "owner": "handoffs/active/speculative-decoding.md",
      "execution_conditions": "Record exact weight/config revisions, source layer pairs, strides, dtype, ownership and one-step index timestamp. Walk representative released mappings against DS41 and the dense 27B control. Require a defined KV read and epoch across accept, reject and slot reuse before any execution probe. Mark unsupported layers and absent weights explicitly.",
      "closure_basis": "INF-77 consumes the sparse selection. INF-50 can separately reuse target KV on full-attention layers, but a dense model supplies no target sparsity. A contract inventory can decide whether a converter or cache export is the next real dependency."
    },
    "P6": {
      "project_objective": "Add fixed-width repeat and cross-width first-divergence comparisons to the long-context determinism diagnosis using retained inputs and dispatch receipts.",
      "implementation_ref": "handoffs/active/rocm-kernel-authoring.md:1225 and handoffs/active/workspace-58-champion-calibration.md:44.",
      "gap": "RKA-BATCH-INV-CENSUS-1 closed with five of six ops requiring changes. Q8IP-DET2 and devhandoff/Pando require a same-width baseline; fixed geometry cannot repair racy summation. This supplements GPU-27B-LONGCTX-SECOND-NONDET without reopening the full audit arm.",
      "operational_change": "Add fixed-width repeat and cross-width first-divergence comparisons to the long-context determinism diagnosis using retained inputs and dispatch receipts.",
      "benefit_direction": "Freeze model, store digest, prompt bytes, state, seeds and launch choices. Replay OFF/OFF and width-1/verify on identical logits inputs where captured. Preserve first mismatched op, tensor bits, route, reduction geometry and missing captures. Hold out later long prompts. Stop on a located first mismatch or insufficient captures; measure HIP cost for that isolated path only after a matched input reproduces.",
      "owner": "handoffs/active/kv-cache-program.md",
      "execution_conditions": "Freeze model, store digest, prompt bytes, state, seeds and launch choices. Replay OFF/OFF and width-1/verify on identical logits inputs where captured. Preserve first mismatched op, tensor bits, route, reduction geometry and missing captures. Hold out later long prompts. Stop on a located first mismatch or insufficient captures; measure HIP cost for that isolated path only after a matched input reproduces.",
      "closure_basis": "RKA-BATCH-INV-CENSUS-1 closed with five of six ops requiring changes. Q8IP-DET2 and devhandoff/Pando require a same-width baseline; fixed geometry cannot repair racy summation. This supplements GPU-27B-LONGCTX-SECOND-NONDET without reopening the full audit arm."
    },
    "P7": {
      "project_objective": "Identify whether either KDA exponential loop executes in Q38FN CPU traces and bound its contribution to decode and prefill.",
      "implementation_ref": "handoffs/active/long-context-program.md:1234 is the GDN context; upstream ggml/src/ggml-cpu/{vec.cpp,ops.cpp}. Validate KDA separately from generic GDN.",
      "gap": "CAFE-5 treats GDN rows. A generic GDN count leaves backend-specific KDA call reachability unresolved; Intel AVX2 results do not measure Zen 5.",
      "operational_change": "Identify whether either KDA exponential loop executes in Q38FN CPU traces and bound its contribution to decode and prefill.",
      "benefit_direction": "Pin graph, model, ISA, row lengths and trace windows; emit per-loop counts, time share and missing fields. Repeat on a later prompt. Stop on proven zero or an Amdahl bound smaller than the paired timing error. Otherwise compare scalar and AVX-512 at actual sizes, scalar tails, exceptional inputs and recurrent-state error before throughput.",
      "owner": "handoffs/active/cpu-decode-roofline-program.md",
      "execution_conditions": "Pin graph, model, ISA, row lengths and trace windows; emit per-loop counts, time share and missing fields. Repeat on a later prompt. Stop on proven zero or an Amdahl bound smaller than the paired timing error. Otherwise compare scalar and AVX-512 at actual sizes, scalar tails, exceptional inputs and recurrent-state error before throughput.",
      "closure_basis": "CAFE-5 treats GDN rows. A generic GDN count leaves backend-specific KDA call reachability unresolved; Intel AVX2 results do not measure Zen 5."
    },
    "P8": {
      "project_objective": "Extend the frozen-logit sampler fixture to record retained support, drawn token and full versus post-filter probabilities at boundary ties.",
      "implementation_ref": "Upstream flashinfer/batch_invariant/sampling/{support_spec.py,support_reference.py,draw_support_api.py,api.py} and tests/utils/test_batch_invariant_sampling_draw_support.py. EPYC handoffs/active/speculative-decoding.md:669–678 pins scripts/kernel_rnd/dist_gate/spec_dist_gate.py at 608c7050a and its randomized PIT/selection-matched rank chi-square, plus experimental pit_less/pit_tie capture and the 8-decimal tail artifact.",
      "gap": "SPEC-PIT.1 addresses distribution equivalence. A passing PIT result cannot establish that a reported log probability refers to the deployed filtered support.",
      "operational_change": "Extend the frozen-logit sampler fixture to record retained support, drawn token and full versus post-filter probabilities at boundary ties.",
      "benefit_direction": "Hash rows, seeds and sampler chain; test top-k, top-p, min-p, both orders, no-op, infinities and exact ties. Compare native support to a whole-tie reference with identical inputs, then repeat on held-out row permutations. Emit every support and denominator; reject ambiguous probability labels. File a compatibility result. Serving policy requires a separate gate.",
      "owner": "handoffs/active/speculative-decoding.md",
      "execution_conditions": "Hash rows, seeds and sampler chain; test top-k, top-p, min-p, both orders, no-op, infinities and exact ties. Compare native support to a whole-tie reference with identical inputs, then repeat on held-out row permutations. Emit every support and denominator; reject ambiguous probability labels. File a compatibility result. Serving policy requires a separate gate.",
      "closure_basis": "SPEC-PIT.1 addresses distribution equivalence. A passing PIT result cannot establish that a reported log probability refers to the deployed filtered support."
    },
    "P9": {
      "project_objective": "Trace recurrent-state ownership and residual state-sized copies across rollback, slot reuse and phase transitions on CPU and HIP.",
      "implementation_ref": "Upstream flashinfer/mamba/{ssd_combined.py,cake_ssd_combined.py}, tests/mamba/test_cake_ssd_combined_state_slots.py and benchmarks/bench_cake_mamba_ssd_combined.py. EPYC handoffs/active/autokernel-loop.md:4906 already passes device replay counts instead of gathering token-state snapshots; :4907 records seq-local state/control mirroring and :4914 the reviewed identity row. handoffs/active/kv-cache-program.md:590 and :1935 retain the separate hybrid transition design/HYPIC reference.",
      "gap": "Earlier replay optimization moved control counts on device. State-pool ownership, strided writes and slot safety remain separate from seed determinism and from chunk arithmetic.",
      "operational_change": "Trace recurrent-state ownership and residual state-sized copies across rollback, slot reuse and phase transitions on CPU and HIP.",
      "benefit_direction": "Pin trace and source revisions plus the initial state; follow each pointer, dtype and byte count across gather, transition and scatter. Compare direct-write candidates to current device replay counts. Include a later trace and poisoned non-target slots. Report unresolved copies separately; stop at no remaining transfer. Require unique destination slots and read-before-write fences before any aliasing experiment.",
      "owner": "handoffs/active/kv-cache-program.md",
      "execution_conditions": "Pin trace and source revisions plus the initial state; follow each pointer, dtype and byte count across gather, transition and scatter. Compare direct-write candidates to current device replay counts. Include a later trace and poisoned non-target slots. Report unresolved copies separately; stop at no remaining transfer. Require unique destination slots and read-before-write fences before any aliasing experiment.",
      "closure_basis": "Earlier replay optimization moved control counts on device. State-pool ownership, strided writes and slot safety remain separate from seed determinism and from chunk arithmetic."
    },
    "M1": {
      "project_objective": "Check BF16 MFMA compiler compatibility when a clang-23 toolchain candidate enters qualification.",
      "implementation_ref": "ggml/src/ggml-cuda/mma.cuh CDNA1 and CDNA2–4 BF16 MFMA fragment aliases in upstream patch; root production freeze pins ROCm 6.2.",
      "gap": "DF2-11-BF16 concerns the executed BF16 route. The upstream patch addresses compiler operand types and supplies no CDNA runtime measurement.",
      "operational_change": "Check BF16 MFMA compiler compatibility when a clang-23 toolchain candidate enters qualification.",
      "benefit_direction": "Trigger on an actual LLVM 23 qualification build for gfx90a. Compare old/new fragments and emitted ISA at both compilers; run BF16 op parity and DF2 target-route smoke using the candidate binary.",
      "owner": "handoffs/active/rocm-kernel-authoring.md",
      "execution_conditions": "Trigger on an actual LLVM 23 qualification build for gfx90a. Compare old/new fragments and emitted ISA at both compilers; run BF16 op parity and DF2 target-route smoke using the candidate binary.",
      "closure_basis": "DF2-11-BF16 concerns the executed BF16 route. The upstream patch addresses compiler operand types and supplies no CDNA runtime measurement."
    },
    "M2": {
      "project_objective": "Consider sharing scratch when a single-sequence 27B configuration misses its fit bound by shareable scheduler bytes.",
      "implementation_ref": "handoffs/active/kv-cache-program.md:41 KPF-13.1 establishes the relevant plain-MTP and DFlash2 context; upstream src/llama-context.cpp sched_new is the capability gate.",
      "gap": "The upstream guard literally requires CUDA; the fork names HIP ROCm. The C21 scheduler lacks the sharing primitive. DEV-INJECT removes a transfer and does not establish safe aliasing.",
      "operational_change": "Consider sharing scratch when a single-sequence 27B configuration misses its fit bound by shareable scheduler bytes.",
      "benefit_direction": "Trigger on a measured fit failure with target/draft scratch live ranges that do not overlap. Record separate buffers, buffer types, async completion, realloc and actual peak. Test eligibility by capabilities and preserve independent fallback.",
      "owner": "handoffs/active/speculative-decoding.md",
      "execution_conditions": "Trigger on a measured fit failure with target/draft scratch live ranges that do not overlap. Record separate buffers, buffer types, async completion, realloc and actual peak. Test eligibility by capabilities and preserve independent fallback.",
      "closure_basis": "The upstream guard literally requires CUDA; the fork names HIP ROCm. The C21 scheduler lacks the sharing primitive. DEV-INJECT removes a transfer and does not establish safe aliasing."
    },
    "M3": {
      "project_objective": "Compare nested-plane decoding at equal realized bytes and quality for a capacity-constrained target.",
      "implementation_ref": "handoffs/active/quantization-and-low-bit.md:93 (serving bytes-elasticity pre-gate) and :101 (verify-kernel route caveat); any_rate/README.md:L64-L81, kernels/ar_gemv.py:L1-L21,L34-L49,L80-L91 and kernels/csrc/ar_gemv_v14_dense.cu:L124-L161 @ 9e75eb7. EXL3 lane handoffs/active/quantization-and-low-bit.md:L74-L90 @ a660ead.",
      "gap": "Single-rate comparisons need all LUT and alignment overhead. No MI210 or Zen5 performance evidence; on-device LPDDR energy estimate cannot rank either platform.",
      "operational_change": "Compare nested-plane decoding at equal realized bytes and quality for a capacity-constrained target.",
      "benefit_direction": "Trigger when a proposed multi-rate deployment identifies the exact layers/rates and an incumbent that misses its fit or quality target. Run integer bit unpack against reference bytes, compare shared row tables in LDS and AVX-512 byte-permute/split tables with scalar tails, then paired KLD and held-out throughput against incumbent EXL3/GGUF.",
      "owner": "handoffs/active/quantization-and-low-bit.md",
      "execution_conditions": "Trigger when a proposed multi-rate deployment identifies the exact layers/rates and an incumbent that misses its fit or quality target. Run integer bit unpack against reference bytes, compare shared row tables in LDS and AVX-512 byte-permute/split tables with scalar tails, then paired KLD and held-out throughput against incumbent EXL3/GGUF.",
      "closure_basis": "Single-rate comparisons need all LUT and alignment overhead. No MI210 or Zen5 performance evidence; on-device LPDDR energy estimate cannot rank either platform."
    },
    "M4": {
      "project_objective": "Test a matched boosted head or budget a one-card training step once local traces put the limitation in draft acceptance.",
      "implementation_ref": "handoffs/active/speculative-decoding.md:117–118 (launch-fixed policy), use existing MTP evaluation as baseline",
      "gap": "Published memory is per GPU in a four-GB300 configuration. CPU and MI210 serving need acceptance-by-position and wall time at the same K before a head switch.",
      "operational_change": "Test a matched boosted head or budget a one-card training step once local traces put the limitation in draft acceptance.",
      "benefit_direction": "Trigger on a per-position acceptance deficit with a compatible frozen backbone/head pair and priced training baseline. Log optimizer/gradient/activation/weights and allocator peak in a single-device microbatch dry fit; retain HSM mix and HSGD detach probability separately.",
      "owner": "handoffs/active/speculative-decoding.md",
      "execution_conditions": "Trigger on a per-position acceptance deficit with a compatible frozen backbone/head pair and priced training baseline. Log optimizer/gradient/activation/weights and allocator peak in a single-device microbatch dry fit; retain HSM mix and HSGD detach probability separately.",
      "closure_basis": "Published memory is per GPU in a four-GB300 configuration. CPU and MI210 serving need acceptance-by-position and wall time at the same K before a head switch."
    },
    "M5": {
      "project_objective": "Test draft-only exemplars when a served repeated-task family uses a compatible separate draft model.",
      "implementation_ref": "handoffs/active/speculative-decoding.md:117–118 (launch-fixed drafter); avoid broad serving-control changes",
      "gap": "The existing DFlash2 path shares model features; a classical separate-proposal verifier is the consumer. Additional KV and prefill may overwhelm acceptance gains.",
      "operational_change": "Test draft-only exemplars when a served repeated-task family uses a compatible separate draft model.",
      "benefit_direction": "Require stable shared tokenizer, true proposal probabilities and a family with disjoint exemplar and evaluation prompts. Compare target alone, symmetric draft, length-matched irrelevant and task-matched exemplars at equal cache state; measure TTFT and full session time.",
      "owner": "handoffs/active/speculative-decoding.md",
      "execution_conditions": "Require stable shared tokenizer, true proposal probabilities and a family with disjoint exemplar and evaluation prompts. Compare target alone, symmetric draft, length-matched irrelevant and task-matched exemplars at equal cache state; measure TTFT and full session time.",
      "closure_basis": "The existing DFlash2 path shares model features; a classical separate-proposal verifier is the consumer. Additional KV and prefill may overwhelm acceptance gains."
    },
    "M6": {
      "project_objective": "Retain request-local RNG and filtered-score semantics for a consumer that requires reproducible stochastic sampling across slots.",
      "implementation_ref": "handoffs/active/kv-cache-program.md:797 demonstrates the local state isolation concern; no package upgrade is needed for these patterns.; Upstream flashinfer/batch_invariant/sampling/{draw_spec.py,draw_api.py,stream.py,stream_kernel.py} and tests/utils/test_batch_invariant_sampling_draw.py. EPYC handoffs/active/speculative-decoding.md:679–688 pins SPEC-RNG.1 at 9154bb28f, server replay at 261db6c7e and the MI210 DFlash2 runner at 2f8af0e2d. handoffs/active/autokernel-loop.md:4912 documents 2d0016466 for CPU/HIP logf divergence and bitwise Gumbel fix.",
      "gap": "SPEC-RNG.1 at lines 679–688 already tested keyed RNG. Position-keyed draws do not resolve earlier logit drift; no reason to repeat a served sweep merely from this release.",
      "operational_change": "Retain request-local RNG and filtered-score semantics for a consumer that requires reproducible stochastic sampling across slots.",
      "benefit_direction": "Trigger on a recorded fixed-logit replay difference at equal seed and offset under reorder, recycle or filter-boundary ties, or a consumer requiring full versus retained log probabilities. Compare frozen logits/filters first.",
      "owner": "handoffs/active/speculative-decoding.md",
      "execution_conditions": "Trigger on a recorded fixed-logit replay difference at equal seed and offset under reorder, recycle or filter-boundary ties, or a consumer requiring full versus retained log probabilities. Compare frozen logits/filters first.",
      "closure_basis": "SPEC-RNG.1 at lines 679–688 already tested keyed RNG. Position-keyed draws do not resolve earlier logit drift; no reason to repeat a served sweep merely from this release."
    },
    "M7": {
      "project_objective": "Use phase-invariant recurrent updates and indexed pool writes where a first difference or copy profile identifies recurrent state.",
      "implementation_ref": "flashinfer/batch_invariant/gdn/{api,pool,spec}.py and include/flashinfer/gdn/batch_invariant_decode.cuh @ 77a3cc5. handoffs/active/kv-cache-program.md:L1906,L1941 and handoffs/active/speculative-decoding.md:L1376-L1385 @ a660ead.",
      "gap": "No native CUTE/SM100 kernel on MI210; fixed chunking can sacrifice occupancy and state pooling needs an ownership and alias contract. CPU state rows are already under CAFE-5.",
      "operational_change": "Use phase-invariant recurrent updates and indexed pool writes where a first difference or copy profile identifies recurrent state.",
      "benefit_direction": "Trigger on equal initial state/input and first mismatch in the GDN transition across phase or a measured recurrent-state copy. Compare fixed chunking, zero padding and tail at a fixed logical token. Verify poison slots, repeated indices, dtype and fences separately for the pool branch.",
      "owner": "handoffs/active/kv-cache-program.md",
      "execution_conditions": "Trigger on equal initial state/input and first mismatch in the GDN transition across phase or a measured recurrent-state copy. Compare fixed chunking, zero padding and tail at a fixed logical token. Verify poison slots, repeated indices, dtype and fences separately for the pool branch.",
      "closure_basis": "No native CUTE/SM100 kernel on MI210; fixed chunking can sacrifice occupancy and state pooling needs an ownership and alias contract. CPU state rows are already under CAFE-5."
    },
    "M8": {
      "project_objective": "Compare task-specific delegation guidance against both plan-only and unguided routing before enabling heterogeneous delegation.",
      "implementation_ref": "Pinned P3 audit at lines 1043–1067 names _delegate_single, _delegate_parallel and PromptForge resolver.py brief-based fanout. Heterogeneous access-list chaining remains P2-gated. Existing isolation and homogeneous fanout can exercise a profiled advisory without adding delegate_chain. Orchestrator checkout absent inside lane.",
      "gap": "P3 chaining is gated. Delegation report persistence records handles; it cannot by itself price work or validate a policy. Hosted API dollars do not price co-resident EPYC workers.",
      "operational_change": "Compare task-specific delegation guidance against both plan-only and unguided routing before enabling heterogeneous delegation.",
      "benefit_direction": "Trigger on retained lead/worker traces with attributed worker spans and independent task groups; freeze judge and rubric, measure task quality, cache-adjusted tokens, end-to-end time, queueing and CPU/GPU occupancy. Count rejected/failed work in every arm.",
      "owner": "handoffs/active/routing-program.md",
      "execution_conditions": "Trigger on retained lead/worker traces with attributed worker spans and independent task groups; freeze judge and rubric, measure task quality, cache-adjusted tokens, end-to-end time, queueing and CPU/GPU occupancy. Count rejected/failed work in every arm.",
      "closure_basis": "P3 chaining is gated. Delegation report persistence records handles; it cannot by itself price work or validate a policy. Hosted API dollars do not price co-resident EPYC workers."
    },
    "M9": {
      "project_objective": "Test hindsight allocation for a specific local distillation budget once eligible evidence-labeled trajectories exist.",
      "implementation_ref": "Pinned HIL-16b references HIL-16a verified 80 recordings / 11 failed, and src/trace/replay/graph_harness.py:make_production_harness (orchestrator a16750a8). It documents later-pilot no-effect mock/diagnostic limits and unresolved source-era replay acceptance. This is an execution replay instrument; the paper trains student weights on new response samples. Orchestrator checkout absent inside lane.",
      "gap": "HIL-16b is eval instrumentation. Neither replay nor a confidence gate alone trains a student, and the paper’s environment and teacher budget are not an EPYC estimate.",
      "operational_change": "Test hindsight allocation for a specific local distillation budget once eligible evidence-labeled trajectories exist.",
      "benefit_direction": "Trigger on a local student/teacher run with verified downstream outcomes and a fixed replay budget. Compare random and position-matched selection to evidence selection on unseen tasks, preserve all rejected prefixes, and separately score confidence calibration.",
      "owner": "handoffs/active/harness-program.md",
      "execution_conditions": "Trigger on a local student/teacher run with verified downstream outcomes and a fixed replay budget. Compare random and position-matched selection to evidence selection on unseen tasks, preserve all rejected prefixes, and separately score confidence calibration.",
      "closure_basis": "HIL-16b is eval instrumentation. Neither replay nor a confidence gate alone trains a student, and the paper’s environment and teacher budget are not an EPYC estimate."
    },
    "M10": {
      "project_objective": "Assess retirement separately from observed skill uplift when a named skill/model pair is scheduled for removal.",
      "implementation_ref": "handoffs/active/eval-tower-program.md:L474-L489,L1723 @ a660ead. epyc-orchestrator scripts/autopilot/skill_efficacy.py:L221-L270 @ faa783c7 distinguishes comparable suite aggregates and negative-delta decision; retirement requires a per-model skill/probe and library-ablation contract absent in this path.",
      "gap": "A low marginal lift can reflect a task that both arms fail. EV-10a measures efficacy; a per-model retirement policy needs evidence of unaided competence.",
      "operational_change": "Assess retirement separately from observed skill uplift when a named skill/model pair is scheduled for removal.",
      "benefit_direction": "Freeze baseline unaided success, skill-on/skill-off trials, invalid calls and retirement rule; reserve new tasks/trials, check retained reward and false retirements before withdrawing any skill.",
      "owner": "handoffs/active/eval-tower-program.md",
      "execution_conditions": "Freeze baseline unaided success, skill-on/skill-off trials, invalid calls and retirement rule; reserve new tasks/trials, check retained reward and false retirements before withdrawing any skill.",
      "closure_basis": "A low marginal lift can reflect a task that both arms fail. EV-10a measures efficacy; a per-model retirement policy needs evidence of unaided competence."
    }
  },
  "actionable_additions": [],
  "steering_reconciliation": [
    {
      "seq": 1,
      "stage": 1,
      "verbatim": "Operator steering (context for Stage 1 ranking and Stage 3 grounding, not authorization to write handoffs):\n\nKERNELS / LOW-LEVEL",
      "disposition": "context-only",
      "plan_ref": null,
      "reason": "Defines ranking, evidence scope, maximum sweep count, approval boundary and handoff authoring format."
    },
    {
      "seq": 2,
      "stage": 1,
      "verbatim": "1. llama.cpp PR #33086 (open): CDNA MFMA bf16 builtins take short vectors; LLVM 23 rejects __bf16 fragments for gfx908/gfx90a/gfx942/gfx950. Builds with clang 23.1.6; identical codegen on clang 22; not run on CDNA hardware. Targets gfx90a directly. Value: rocm-kernel-authoring toolchain readiness before any TheRock 10.x / LLVM 23 move; BF16 drafter path (DF2-11-BF16).",
      "disposition": "planned",
      "plan_ref": "M1",
      "reason": "DF2-11-BF16 concerns the executed BF16 route. The upstream patch addresses compiler operand types and supplies no CDNA runtime measurement."
    },
    {
      "seq": 3,
      "stage": 1,
      "verbatim": "2. llama.cpp PR #33019 (open): split gate/up weight reads in small_k MMVQ; RTX 3060 decode +4.65% to +21.87% on small models, Q8_0 0.00%, Qwen3 8B Q4_K_M +0.03%; reviewer flagged a small_k row-bounds bug in single-token MoE. CUDA-tested; shared MMVQ code compiles for HIP. Value: AutoKernel MMVQ n<=4 route on the 27B and A3B MUL_MAT_ID cells.\n   Extract: the performance principles themselves — data layout, tiling, wavefront mapping, LDS use, fusion, quant packing and dispatch rules.\n   Check: whether each principle works on the MI210 (gfx90a, CDNA2, wave64, 64 KB LDS, no FP8) or the Zen 5 EPYC CPU (AVX-512, NPS4).\n   (Specifically: separate gate/up loops for short rows, the small_k threshold rule, row guarding for partial MoE blocks under wave64.)",
      "disposition": "planned",
      "plan_ref": "P3",
      "reason": "The split changes reads in fused short rows, the inclusive cutoff changes eligibility, and C17 already carries fa221af5d for odd expert stores. The measured RTX Q8 case was flat."
    },
    {
      "seq": 4,
      "stage": 1,
      "verbatim": "3. llama.cpp PR #32081 (draft): opt-in --batch-invariant via a per-backend proc address that pins one kernel configuration for every batch size, so greedy verify equals single-token decode; tested on Metal and CUDA; performance cost acknowledged, no numbers. Value: GPU-27B-LONGCTX-SECOND-NONDET, Q8IP-DET2-GATE-1, DTREE Pando / devhandoff FUTILITY_HARNESS_NONDET rows.\n   Extract: the performance principles themselves — data layout, tiling, wavefront mapping, LDS use, fusion, quant packing and dispatch rules.\n   Check: whether each principle works on the MI210 (gfx90a, CDNA2, wave64, 64 KB LDS, no FP8) or the Zen 5 EPYC CPU (AVX-512, NPS4).\n   (Specifically: fixed MMQ/MMVQ/FA dispatch across batch sizes, accumulation order, the cost on HIP.)",
      "disposition": "planned",
      "plan_ref": "P6",
      "reason": "RKA-BATCH-INV-CENSUS-1 closed with five of six ops requiring changes. Q8IP-DET2 and devhandoff/Pando require a same-width baseline; fixed geometry cannot repair racy summation. This supplements GPU-27B-LONGCTX-SECOND-NONDET without reopening the full audit arm."
    },
    {
      "seq": 5,
      "stage": 1,
      "verbatim": "4. FlashInfer v0.7.6 release: batch_invariant=True for chunk_gated_delta_rule (class gdn.bf16.c64) and recurrent_kda, same bits across prefill/chunked prefill/decode; seeded per-row top-k/top-p/min-p sampling; GDN/Mamba2 kernels on a caller-owned state pool. SM100/SM103/SM107 only; does not run on gfx90a. Value: determinism lane (kv-cache-program), GDN state handling for DFlash2 replay.\n   Extract: the performance principles themselves — data layout, tiling, wavefront mapping, LDS use, fusion, quant packing and dispatch rules.\n   Check: whether each principle works on the MI210 (gfx90a, CDNA2, wave64, 64 KB LDS, no FP8) or the Zen 5 EPYC CPU (AVX-512, NPS4).\n   (Specifically: fixed GDN chunk size across phases, per-row seed+offset sampling, slot-indexed state pool layout.)",
      "disposition": "planned",
      "plan_ref": "M6",
      "reason": "SPEC-RNG.1 at lines 679–688 already tested keyed RNG. Position-keyed draws do not resolve earlier logit drift; no reason to repeat a served sweep merely from this release."
    },
    {
      "seq": 6,
      "stage": 1,
      "verbatim": "5. llama.cpp PR #33077 (open): ggml_vec_exp_f32 wired to the per-platform ggml_v_expf; KDA loops of the GDN op faster than master by 1.5–2.7% (single token) to 3.1–6.5% (multi-token). Runs on the EPYC CPU (KDA path only). Value: Q38FN CPU non-GEMV diagnoses, cpu-decode-roofline-program.",
      "disposition": "planned",
      "plan_ref": "P7",
      "reason": "CAFE-5 treats GDN rows. A generic GDN count leaves backend-specific KDA call reachability unresolved; Intel AVX2 results do not measure Zen 5."
    },
    {
      "seq": 7,
      "stage": 1,
      "verbatim": "6. Any-Rate (arXiv 2611.34402): 2–8 bit nested multi-precision from one checkpoint, half-bit steps over 2–4 bits, extended-Hamming bit-planes, one LUT per row; 69% of FP16 accuracy at 2 bits; decode about as fast as existing kernels; up to 27% less energy (LPDDR model); code public. Targets on-device hardware. Value: INF-80 low-bit lane (EXL3 comparisons), KLD gates.\n   Extract: the performance principles themselves — data layout, tiling, wavefront mapping, LDS use, fusion, quant packing and dispatch rules.\n   Check: whether each principle works on the MI210 (gfx90a, CDNA2, wave64, 64 KB LDS, no FP8) or the Zen 5 EPYC CPU (AVX-512, NPS4).\n   (Specifically: bit-plane packing, per-row LUT decode via AVX-512 byte permutes or LDS tables on gfx90a.)\n\nINFERENCE SYSTEMS / HARNESS / POST-TRAINING",
      "disposition": "planned",
      "plan_ref": "M3",
      "reason": "Single-rate comparisons need all LUT and alignment overhead. No MI210 or Zen5 performance evidence; on-device LPDDR energy estimate cannot rank either platform."
    },
    {
      "seq": 8,
      "stage": 1,
      "verbatim": "7. DFly2 (arXiv 2611.34776): block-parallel drafter sharing the target's KV cache and sparse-indexer selections; accepts more tokens than DFlash/DSpark (+3.9–10.5% general, +10.0–31.5% long-context/agentic); +62% and +81% throughput at matched per-user speed on two 64K sets (DS-V4.1-Flash). Targets natively sparse models on GPU. Value: INF-50 DFlash2 (KV sharing on full-attention layers), INF-77 DS-V4.1-Flash.\n   Extract: the performance principles themselves — data layout, tiling, wavefront mapping, LDS use, fusion, quant packing and dispatch rules.\n   Check: whether each principle works on the MI210 (gfx90a, CDNA2, wave64, 64 KB LDS, no FP8) or the Zen 5 EPYC CPU (AVX-512, NPS4).\n   (Specifically: drafter-reads-target-KV layout, reuse of a selection made one step early, no drafter cache.)",
      "disposition": "planned",
      "plan_ref": "P5",
      "reason": "INF-77 consumes the sparse selection. INF-50 can separately reuse target KV on full-attention layers, but a dense model supplies no target sparsity. A contract inventory can decide whether a converter or cache export is the next real dependency."
    },
    {
      "seq": 9,
      "stage": 1,
      "verbatim": "8. HSM / HSGD (arXiv 2611.34092): training-only drafter fixes; up to 52.2% higher mean acceptance length than co-trained MTP with a frozen backbone; 48% lower peak training memory than TTT (Qwen3-8B, EAGLE-3); Megatron-LM / ModelOpt code. NVIDIA training stack. Value: INF-50 MTP/DFlash2 head retraining.\n   Extract: the performance principles themselves — data layout, tiling, wavefront mapping, LDS use, fusion, quant packing and dispatch rules.\n   Check: whether each principle works on the MI210 (gfx90a, CDNA2, wave64, 64 KB LDS, no FP8) or the Zen 5 EPYC CPU (AVX-512, NPS4).\n   (Specifically: hidden-state mixing schedule and memory footprint for a single 64 GB MI210 training run.)",
      "disposition": "planned",
      "plan_ref": "M4",
      "reason": "Published memory is per GPU in a four-GB300 configuration. CPU and MI210 serving need acceptance-by-position and wall time at the same K before a head switch."
    },
    {
      "seq": 10,
      "stage": 1,
      "verbatim": "9. AsymSpec (arXiv 2611.34010): training-free decoupled draft prompts with example solutions; 2.29–4.95x over autoregressive; exact sampling. Hardware-agnostic; needs a separate draft model. Value: INF-50 draft-model mode, orchestrator repeated-task families.",
      "disposition": "planned",
      "plan_ref": "M5",
      "reason": "The existing DFlash2 path shares model features; a classical separate-proposal verifier is the consumer. Additional KV and prefill may overwhelm acceptance gains."
    },
    {
      "seq": 11,
      "stage": 1,
      "verbatim": "10. Ostinato (arXiv 2611.11533 v2): static cross-layer GPU expert pool, resident routes on GPU, cold routes on CPU; tool-turn waits 2.5–6.6x lower, sessions 1.36–3.83x faster, 1.81–2.19x over llama.cpp expert cache on 335 GB DS-V4.1-Flash. CUDA consumer GPUs. Value: A3B GPU candidate lane, INF-77, INF-45 NUMA placement.\n   Extract: the performance principles themselves — data layout, tiling, wavefront mapping, LDS use, fusion, quant packing and dispatch rules.\n   Check: whether each principle works on the MI210 (gfx90a, CDNA2, wave64, 64 KB LDS, no FP8) or the Zen 5 EPYC CPU (AVX-512, NPS4).\n   (Specifically: expert residency pool sizing over 64 GB, CPU cold-route GEMV on NPS4, upload dedup on long prefills.)",
      "disposition": "planned",
      "plan_ref": "P4",
      "reason": "INF-45 already owns the route tap. Reuse it for DS41 and A3B; 64 GB is total device capacity. The paper’s 512-token crossover and dual-Xeon bandwidth cannot fix the NPS4 crossover."
    },
    {
      "seq": 12,
      "stage": 1,
      "verbatim": "11. llama.cpp PR #33068 (open): MTP/DFlash/draft context shares its partner's compute buffers via ggml_backend_sched_share_buffers; about -130 MiB (MTP) and -190 MiB (DFlash2) on RTX 5090 / RTX PRO 6000; single device, one sequence, no pipeline parallelism. Value: served 27B fit bound (62 GiB), Q8-SERVED-DEV-INJECT-1.\n   Extract: the performance principles themselves — data layout, tiling, wavefront mapping, LDS use, fusion, quant packing and dispatch rules.\n   Check: whether each principle works on the MI210 (gfx90a, CDNA2, wave64, 64 KB LDS, no FP8) or the Zen 5 EPYC CPU (AVX-512, NPS4).\n   (Specifically: whether HIP builds hit the same single-device condition.)",
      "disposition": "planned",
      "plan_ref": "M2",
      "reason": "The upstream guard literally requires CUDA; the fork names HIP ROCm. The C21 scheduler lacks the sharing primitive. DEV-INJECT removes a transfer and does not establish safe aliasing."
    },
    {
      "seq": 13,
      "stage": 1,
      "verbatim": "12. llama.cpp PR #30318 (merged 2026-11-25): ON_DEVICE per-sequence state restore now validates headers inside the try block and returns a recoverable error instead of GGML_ASSERT; without it 146/150 models failed the new rf test; tested CPU and CUDA (RTX 4070). Value: Q8-SERVED-CKPT-COPY-1 checkpoint save/restore path.\n   Extract: the performance principles themselves — data layout, tiling, wavefront mapping, LDS use, fusion, quant packing and dispatch rules.\n   Check: whether each principle works on the MI210 (gfx90a, CDNA2, wave64, 64 KB LDS, no FP8) or the Zen 5 EPYC CPU (AVX-512, NPS4).\n   (Specifically: ON_DEVICE reader semantics against the fork's C21 checkpoint path.)",
      "disposition": "planned",
      "plan_ref": "P1",
      "reason": "C21 state_seq_set_data constructs its device reader and checks mem_storage before the catch. Its catch only logs. KPF-17 exercises partial restore; Q8-SERVED-CKPT-COPY-1 uses the host writer and times transfers. Neither checks this failure boundary."
    },
    {
      "seq": 14,
      "stage": 1,
      "verbatim": "13. Partial Routing (arXiv 2611.33402): lead model delegates subtasks to a cheaper worker using trace-derived guidance; ViBench 70.2 -> 78.5 at 19% lower cost (delta 0.75); Terminal-Bench 54% -> 61% at similar cost. Hardware-agnostic. Value: routing-program escalation, review-plane delegation knobs, MemRL trace reuse.",
      "disposition": "planned",
      "plan_ref": "M8",
      "reason": "P3 chaining is gated. Delegation report persistence records handles; it cannot by itself price work or validate a policy. Hosted API dollars do not price co-resident EPYC workers."
    },
    {
      "seq": 15,
      "stage": 1,
      "verbatim": "14. SkillsBench audit (arXiv 2611.33943): 7,554 trials / 1,421 paired cells; no task-level reduction significant after correction; skill gating +2–3 pp, but shuffled labels give +4–7 pp; no held-out gain. Hardware-agnostic. Value: eval-tower paired_stats / AEI-RERUN-FLIP noise bands, skill-bank gating rigor.",
      "disposition": "planned",
      "plan_ref": "P2",
      "reason": "At orchestrator faa783c7, scripts/autopilot/skill_efficacy.py:313 and :352 aggregate suite-keyed efficacy. EV-10a and AEI-RERUN-FLIP can consume a diagnostic replay while the skill-bank activation policy stays with its current owner."
    },
    {
      "seq": 16,
      "stage": 1,
      "verbatim": "15. CARE-OPD (arXiv 2611.34756): on-policy distillation with prefix replay, confidence gating and hindsight turn allocation; SWE-bench Verified 59.5%, -45% training time, -44% environment actions vs async online OPD. Training-cluster scale. Value: post-training lane for local Qwen agents.\n",
      "disposition": "planned",
      "plan_ref": "M9",
      "reason": "HIL-16b is eval instrumentation. Neither replay nor a confidence gate alone trains a student, and the paper’s environment and teacher budget are not an EPYC estimate."
    },
    {
      "seq": 17,
      "stage": 1,
      "verbatim": "Automatically accept every recommended deep dive and literature expansion for up to four Stage 2 sweeps.",
      "disposition": "context-only",
      "plan_ref": null,
      "reason": "Defines ranking, evidence scope, maximum sweep count, approval boundary and handoff authoring format."
    },
    {
      "seq": 18,
      "stage": 1,
      "verbatim": "be mindful that the handoff formats have been stadardized recently so make sure you stick to project policies. review logs and progress reports for reference as needed",
      "disposition": "context-only",
      "plan_ref": null,
      "reason": "Defines ranking, evidence scope, maximum sweep count, approval boundary and handoff authoring format."
    }
  ],
  "opportunity_scan": [
    {
      "scan_id": "scan-30318",
      "source_ref": "intake-2993#01 · PR overview, recovery path",
      "implementation_ref": "handoffs/active/kv-cache-program.md:797 scopes existing CPU PARTIAL_ONLY coverage; active gfx90a restore work is under KPF-17.4.",
      "mechanism": "The patch moves ON_DEVICE validation into the recoverable exception path.",
      "consumer": "handoffs/active/kv-cache-program.md KPF-17",
      "application": "Compare #27530 cleanup prerequisites against an experimental branch and port the minimal defensive guard with the isolation test. Verify valid restore, recoverable invalid restore and unchanged neighboring sequence on Zen5 and actual gfx90a resident state.",
      "disposition": "actionable",
      "ledger_ids": [
        "RI-2993"
      ],
      "basis": "C21 state_seq_set_data constructs its device reader and checks mem_storage before the catch. Its catch only logs. KPF-17 exercises partial restore; Q8-SERVED-CKPT-COPY-1 uses the host writer and times transfers. Neither checks this failure boundary."
    },
    {
      "scan_id": "scan-27530",
      "source_ref": "intake-3000#01 · PR overview, second paragraph",
      "implementation_ref": "Upstream src/llama-context.cpp and src/llama-memory-hybrid.cpp, src/llama-io.h and tests/test-save-load-state.cpp @ 47ad34a. C21 src/llama-context.cpp:L3265-L3288,L3530-L3567,L3683-L3703, src/llama-memory-hybrid.cpp:L208-L213 @ 98ff8a4. handoffs/active/rocm-kernel-authoring.md:L1174-L1176 @ a660ead.",
      "mechanism": "Deferred writes can survive attempted cleanup.",
      "consumer": "handoffs/active/kv-cache-program.md",
      "application": "For an experimental cache candidate apply discard-before-destruction to owned buffer-reader failure exits and scope hybrid rollback correctly. Gate defensive isolated-state correctness with unaffected calls, preserved-unmodified and removed-modified outcomes across host/device. Q8-SERVED-CKPT-COPY-1 consumes the result and retains its timing gate.",
      "disposition": "actionable",
      "ledger_ids": [
        "RI-3000"
      ],
      "basis": "C21 state_seq_set_data constructs its device reader and checks mem_storage before the catch. Its catch only logs. KPF-17 exercises partial restore; Q8-SERVED-CKPT-COPY-1 uses the host writer and times transfers. Neither checks this failure boundary."
    },
    {
      "scan_id": "scan-2611.33943",
      "source_ref": "intake-2995#01 · Abstract, details in §§III-C–III-D",
      "implementation_ref": "Pinned EV-10a and EV-10f describe evaluate_skill_efficacy and evaluate_skill_efficacy_split in epyc-orchestrator/scripts/autopilot/skill_efficacy.py; default-off accept wiring is pinned in the handoff to 924ca50 and the suite aggregates cannot identify task regressions. Whether manifests already exist elsewhere requires current orchestrator inspection; checkout absent in the pinned lane.",
      "mechanism": "The audited frozen archive contained four placeholder skill directories, and one harness injected 48 built-in skills in most runs.",
      "consumer": "handoffs/active/eval-tower-program.md:478 EV-10a — Paired skill-vs-no-skill efficacy check",
      "application": "Attach an observational sidecar to the remaining EV-10a paired-mutation A/B: verify normalized effective skill manifests per arm and audit scorer constraints against visible task text, retain paired item outcomes and full denominator. Report within-cell shuffled null, untouched later draws for decisions, and task-family holdout for generalization. Reuse the suite-level gate with diagnostic sidecar output. Stop at a preregistered valid-pair cap or declared precision and do not use aggregate efficacy as evidence of task-level stability.",
      "disposition": "actionable",
      "ledger_ids": [
        "RI-2995"
      ],
      "basis": "At orchestrator faa783c7, scripts/autopilot/skill_efficacy.py:313 and :352 aggregate suite-keyed efficacy. EV-10a and AEI-RERUN-FLIP can consume a diagnostic replay while the skill-bank activation policy stays with its current owner."
    },
    {
      "scan_id": "scan-audit",
      "source_ref": "intake-2998#01 · reanalysis/skillgate_checks.py:L635-L643 @ eef0fae",
      "implementation_ref": "reanalysis/skillgate_checks.py:L620-L647,L657-L712; reanalysis/results/{base,null,split,tasks}.json and paper/main.tex:L246-L288,L322-L328 @ eef0fae. handoffs/active/eval-tower-program.md:L3206-L3214 @ a660ead and epyc-orchestrator scripts/autopilot/paired_stats.py:L310-L370 implement rerun control; SkillBank is downstream.",
      "mechanism": "The archived runner holds one trial per condition out in every eligible cell.",
      "consumer": "handoffs/active/eval-tower-program.md",
      "application": "Apply precommitted held-out policy and within-cell shuffled calibration at any SkillBank promotion. Freeze model/task/harness and thresholds, use disjoint tasks or new trials, archive per-trial decision/reward/graded/invalid/abstention denominators, compare always-load versus gate with existing paired and rerun logic, and predeclare minimum benefit and shuffle separation.",
      "disposition": "actionable",
      "ledger_ids": [
        "RI-2998"
      ],
      "basis": "At orchestrator faa783c7, scripts/autopilot/skill_efficacy.py:313 and :352 aggregate suite-keyed efficacy. EV-10a and AEI-RERUN-FLIP can consume a diagnostic replay while the skill-bank activation policy stays with its current owner."
    },
    {
      "scan_id": "scan-33019",
      "source_ref": "intake-2983#01 · PR overview, first paragraph",
      "implementation_ref": "handoffs/active/kernel-champion-and-promotion.md MMID-Q8-N1-ODDM is the boundary regression to retain; upstream ggml/src/ggml-cuda/mmvq.cu and tests/test-backend-ops.cpp.",
      "mechanism": "The patch separates gate and up weight reads only in the small-K MMVQ case.",
      "consumer": "handoffs/active/rocm-kernel-authoring.md",
      "application": "First count reachable fused small-K rows in current MI210 roles; if hit, compare baseline, split only, and split plus inclusive threshold at neighboring K and odd M, with token throughput and output parity.",
      "disposition": "actionable",
      "ledger_ids": [
        "RI-2983"
      ],
      "basis": "The split changes reads in fused short rows, the inclusive cutoff changes eligibility, and C17 already carries fa221af5d for odd expert stores. The measured RTX Q8 case was flat."
    },
    {
      "scan_id": "scan-2611.11533",
      "source_ref": "intake-2991#01 · Abstract and §3",
      "implementation_ref": "handoffs/active/deepseek-v41-flash-evaluation.md:1441 (existing pp512 MUL_MAT_ID premise); handoffs/completed/deepseek-v4-flash-cpu-port.md",
      "mechanism": "Short turns use GPU resident routes and CPU cold routes without expert weight copies.",
      "consumer": "handoffs/active/deepseek-v41-flash-evaluation.md:8",
      "application": "Replay small set of saved DS41 route traces as placement + bytes feasibility, independent of held DS41 inference. Measure resident-route fraction, rows per cold expert, dedup ratio and timing estimates for same-placement CPU-only cold, GPU weight upload and mixed execution. If favorable, compare matched upload threshold/loading and parity before porting HIP graph.",
      "disposition": "actionable",
      "ledger_ids": [
        "RI-2991"
      ],
      "basis": "INF-45 already owns the route tap. Reuse it for DS41 and A3B; 64 GB is total device capacity. The paper’s 512-token crossover and dual-Xeon bandwidth cannot fix the NPS4 crossover."
    },
    {
      "scan_id": "scan-2611.34776",
      "source_ref": "intake-2988#01 · Abstract",
      "implementation_ref": "handoffs/active/speculative-decoding.md:1024 (current block-drafter control); handoffs/completed/deepseek-v4-flash-0731-dspark.md",
      "mechanism": "DFly2 reuses target sparsity and carries no separate KV or scoring pass.",
      "consumer": "handoffs/active/deepseek-v41-flash-evaluation.md:8",
      "application": "Inventory exact artifacts and indexed-KV ABI first; compare replayed index coverage and KV bytes in the DS41 lane without reopening held tests. Promote to served throughput only when paired weights and index custody are available.",
      "disposition": "actionable",
      "ledger_ids": [
        "RI-2988"
      ],
      "basis": "INF-77 consumes the sparse selection. INF-50 can separately reuse target KV on full-attention layers, but a dense model supplies no target sparsity. A contract inventory can decide whether a converter or cache export is the next real dependency."
    },
    {
      "scan_id": "scan-angel",
      "source_ref": "intake-2999#01 · docs/concepts/dfly2.md:L12-L15 @ e02ea36",
      "implementation_ref": "docs/concepts/dfly2.md:L9-L45, configs/vllm_dsv41_flash_dfly2.yaml and angelspec/config/dfly2_dsv41_flash_draft_config.json @ e02ea36. handoffs/active/deepseek-v41-flash-evaluation.md:L1663-L1669,L1786-L1806 @ a660ead.",
      "mechanism": "DFly2 selects sparse target positions using the last accepted token.",
      "consumer": "handoffs/active/deepseek-v41-flash-evaluation.md",
      "application": "Use as companion to DFly2. For INF-77 pin target/drafter versions and prove read-only released weight/latent/layer/last-accepted-position mappings, estimate gather bytes versus matched-width MTP/DSpark, then gate experimental serving if economics justify it. INF-50 can reuse target context on full-attention layers separately from native sparse index sharing.",
      "disposition": "actionable",
      "ledger_ids": [
        "RI-2999"
      ],
      "basis": "INF-77 consumes the sparse selection. INF-50 can separately reuse target KV on full-attention layers, but a dense model supplies no target sparsity. A contract inventory can decide whether a converter or cache export is the next real dependency."
    },
    {
      "scan_id": "scan-32081",
      "source_ref": "intake-2984#01 · PR additional information, mechanism",
      "implementation_ref": "handoffs/active/rocm-kernel-authoring.md:1225 and handoffs/active/workspace-58-champion-calibration.md:44.",
      "mechanism": "Different accumulation order can change the selected token at near ties.",
      "consumer": "handoffs/active/rocm-kernel-authoring.md RKA-BATCH-INV-CENSUS-1; handoffs/active/workspace-58-champion-calibration.md CH-31-DEF1 for cross-slot cases",
      "application": "Reuse op-level batch tests and route receipts on the existing MI210 census, then do one fixed-input Zen5 replay across single and multiple columns for the first divergent op. Preserve the existing full audit-arm gate.",
      "disposition": "actionable",
      "ledger_ids": [
        "RI-2984"
      ],
      "basis": "RKA-BATCH-INV-CENSUS-1 closed with five of six ops requiring changes. Q8IP-DET2 and devhandoff/Pando require a same-width baseline; fixed geometry cannot repair racy summation. This supplements GPU-27B-LONGCTX-SECOND-NONDET without reopening the full audit arm."
    },
    {
      "scan_id": "scan-33077",
      "source_ref": "intake-2986#01 · PR overview, call sites",
      "implementation_ref": "handoffs/active/long-context-program.md:1234 is the GDN context; upstream ggml/src/ggml-cpu/{vec.cpp,ops.cpp}. Validate KDA separately from generic GDN.",
      "mechanism": "The new vector helper is reached from two GDN KDA loops.",
      "consumer": "handoffs/active/cpu-decode-roofline-program.md",
      "application": "Check model graph and CPU traces for KDA reachability. If reachable, compare scalar versus vector at real prefill/TG shapes with exponent and recurrent-state error/greedy checks; stop once the op cannot explain meaningful end-to-end time.",
      "disposition": "actionable",
      "ledger_ids": [
        "RI-2986"
      ],
      "basis": "CAFE-5 treats GDN rows. A generic GDN count leaves backend-specific KDA call reachability unresolved; Intel AVX2 results do not measure Zen 5."
    },
    {
      "scan_id": "scan-9619",
      "source_ref": "intake-3003#01 · PR Description, filtered draw contract",
      "implementation_ref": "Upstream flashinfer/batch_invariant/sampling/{support_spec.py,support_reference.py,draw_support_api.py,api.py} and tests/utils/test_batch_invariant_sampling_draw_support.py. EPYC handoffs/active/speculative-decoding.md:669–678 pins scripts/kernel_rnd/dist_gate/spec_dist_gate.py at 608c7050a and its randomized PIT/selection-matched rank chi-square, plus experimental pit_less/pit_tie capture and the 8-decimal tail artifact.",
      "mechanism": "With the new path a row's chosen token is intended to be independent of its slot, batch size and launch configuration.",
      "consumer": "handoffs/active/speculative-decoding.md SPEC-PIT.1; workspace-58 champion sampler diagnostics are a consumer",
      "application": "Extend the existing SPEC-PIT post-sampling fixture with exact ties just above/below the top-p boundary, filter order, -inf and no-op cases, and compare named support, sampled token and normalized probability against the current served sampler on identical rows/keys. Persist native versus whole-tie results and full-row versus post-filter logprob labels distinctly. Promote a new policy only if a consumer requests it and the same-denominator gate passes.",
      "disposition": "actionable",
      "ledger_ids": [
        "RI-3003"
      ],
      "basis": "SPEC-PIT.1 addresses distribution equivalence. A passing PIT result cannot establish that a reported log probability refers to the deployed filtered support."
    },
    {
      "scan_id": "scan-9644",
      "source_ref": "intake-3004#01 · PR Description, first paragraph",
      "implementation_ref": "Upstream flashinfer/mamba/{ssd_combined.py,cake_ssd_combined.py}, tests/mamba/test_cake_ssd_combined_state_slots.py and benchmarks/bench_cake_mamba_ssd_combined.py. EPYC handoffs/active/autokernel-loop.md:4906 already passes device replay counts instead of gathering token-state snapshots; :4907 records seq-local state/control mirroring and :4914 the reviewed identity row. handoffs/active/kv-cache-program.md:590 and :1935 retain the separate hybrid transition design/HYPIC reference.",
      "mechanism": "The Mamba2 state-slot path reads its initial states directly from a caller-owned pool.",
      "consumer": "handoffs/active/autokernel-loop.md GPU-RESIDENT-ROUND-2f for device state routing, with handoffs/active/kv-cache-program.md KPF-62-P3-SKELETON as a prospective hybrid state consumer",
      "application": "Census the EPYC DFlash2/recurrent state path for residual state-sized copies versus direct writes and bound bytes/ms on both hardware paths. Reuse existing state controls, keeping a CPU fixture for permuted/noncontiguous slots, null initialization, alias rejection and slot reset/reuse. Only carry a direct-write arm when the current capture identifies a remaining copy boundary and its slot owner can enforce uniqueness and read-before-write lifecycle.",
      "disposition": "actionable",
      "ledger_ids": [
        "RI-3004"
      ],
      "basis": "Earlier replay optimization moved control counts on device. State-pool ownership, strided writes and slot safety remain separate from seed determinism and from chunk arithmetic."
    },
    {
      "scan_id": "scan-33086",
      "source_ref": "intake-2982#01 · PR overview, CDNA builtin argument mismatch",
      "implementation_ref": "ggml/src/ggml-cuda/mma.cuh CDNA1 and CDNA2–4 BF16 MFMA fragment aliases in upstream patch; root production freeze pins ROCm 6.2.",
      "mechanism": "The operand ABI fix addresses a compiler rejection that includes gfx90a.",
      "consumer": "handoffs/active/rocm-kernel-authoring.md",
      "application": "On an experimental tree compare the current compiler and a clang-23 candidate on gfx90a, verify emitted BF16 MFMA and run a small BF16 correctness smoke only if planning toolchain adoption.",
      "disposition": "context-only",
      "ledger_ids": [
        "RI-2982"
      ],
      "basis": "DF2-11-BF16 concerns the executed BF16 route. The upstream patch addresses compiler operand types and supplies no CDNA runtime measurement."
    },
    {
      "scan_id": "scan-33068",
      "source_ref": "intake-2992#01 · PR overview, partner scheduler wiring",
      "implementation_ref": "handoffs/active/kv-cache-program.md:41 KPF-13.1 establishes the relevant plain-MTP and DFlash2 context; upstream src/llama-context.cpp sched_new is the capability gate.",
      "mechanism": "The draft shares partner-context scratch via the ggml scheduler.",
      "consumer": "handoffs/active/speculative-decoding.md",
      "application": "Locate scheduler sharing primitive and audit ordering, lifetime, realloc and separate fallback. If concrete MI210 fit is blocked by scratch, prototype under experimental ROCm eligibility and compare achieved peak VRAM, greedy exactness and throughput with overlap controls.",
      "disposition": "context-only",
      "ledger_ids": [
        "RI-2992"
      ],
      "basis": "The upstream guard literally requires CUDA; the fork names HIP ROCm. The C21 scheduler lacks the sharing primitive. DEV-INJECT removes a transfer and does not establish safe aliasing."
    },
    {
      "scan_id": "scan-2611.34402",
      "source_ref": "intake-2987#01 · Abstract",
      "implementation_ref": "handoffs/active/quantization-and-low-bit.md:93 (serving bytes-elasticity pre-gate) and :101 (verify-kernel route caveat)",
      "mechanism": "Selected planes encode half a bit per weight in groups of eight.",
      "consumer": "handoffs/active/quantization-and-low-bit.md:53",
      "application": "On an eligible DS41 or Q38FN low-bit lane, use real expert-tensor shapes to compare normalized format bytes, arithmetic correctness and decode/prefill latency to incumbent GGUF, then equal-bytes quality before funding a model port. Keep precision switching a distinct experiment.",
      "disposition": "context-only",
      "ledger_ids": [
        "RI-2987"
      ],
      "basis": "Single-rate comparisons need all LUT and alignment overhead. No MI210 or Zen5 performance evidence; on-device LPDDR energy estimate cannot rank either platform."
    },
    {
      "scan_id": "scan-Any-Rate",
      "source_ref": "intake-2997#01 · any_rate/README.md:L69 @ 9e75eb7",
      "implementation_ref": "any_rate/README.md:L64-L81, kernels/ar_gemv.py:L1-L21,L34-L49,L80-L91 and kernels/csrc/ar_gemv_v14_dense.cu:L124-L161 @ 9e75eb7. EXL3 lane handoffs/active/quantization-and-low-bit.md:L74-L90 @ a660ead.",
      "mechanism": "The H-plane format packs two 8-column codewords per byte.",
      "consumer": "handoffs/active/quantization-and-low-bit.md",
      "application": "Use as companion evidence for the paper. Under INF-80 compare effective bytes and scalar decode on frozen EXL3 fixtures and held-out KLD/model inputs before a single AVX-512 or HIP microbench. Freeze baseline, raw row outputs, invalid denominators, and latency/quality stops.",
      "disposition": "context-only",
      "ledger_ids": [
        "RI-2997"
      ],
      "basis": "Single-rate comparisons need all LUT and alignment overhead. No MI210 or Zen5 performance evidence; on-device LPDDR energy estimate cannot rank either platform."
    },
    {
      "scan_id": "scan-2611.34092",
      "source_ref": "intake-2989#01 · Abstract and §5",
      "implementation_ref": "handoffs/active/speculative-decoding.md:117–118 (launch-fixed policy), use existing MTP evaluation as baseline",
      "mechanism": "HSGD blocks gradients for hidden and embedding pathways while preserving forward values.",
      "consumer": "handoffs/active/speculative-decoding.md:15",
      "application": "Prioritize released boosted checkpoint with compatible format and same serving graph; run early-position and tail acceptance plus latency per chosen K on both devices. If training is required, perform dry-fit accounting and one-step peak reserve check against an explicit margin.",
      "disposition": "context-only",
      "ledger_ids": [
        "RI-2989"
      ],
      "basis": "Published memory is per GPU in a four-GB300 configuration. CPU and MI210 serving need acceptance-by-position and wall time at the same K before a head switch."
    },
    {
      "scan_id": "scan-2611.34010",
      "source_ref": "intake-2990#01 · §1, contributions; Theorem 1",
      "implementation_ref": "handoffs/active/speculative-decoding.md:117–118 (launch-fixed drafter); avoid broad serving-control changes",
      "mechanism": "The paper’s exactness claim targets its rejection-sampling algorithm.",
      "consumer": "handoffs/active/speculative-decoding.md:15",
      "application": "Add one benchmark-only immutable draft-prefix arm to a separate-checkpoint path, with zero-exemplar same-token-budget control, target-only reference, held-out nonleaking exemplars, exact sampled-distribution check and session TTFT/time by cache state. Keep verifier prompt and sampler identical.",
      "disposition": "context-only",
      "ledger_ids": [
        "RI-2990"
      ],
      "basis": "The existing DFlash2 path shares model features; a classical separate-proposal verifier is the consumer. Additional KV and prefill may overwhelm acceptance gains."
    },
    {
      "scan_id": "scan-flash",
      "source_ref": "intake-2985#01 · Release highlights, batch-invariant mode",
      "implementation_ref": "handoffs/active/kv-cache-program.md:797 demonstrates the local state isolation concern; no package upgrade is needed for these patterns.",
      "mechanism": "Deterministic sampling keys logical rows independently of position.",
      "consumer": "handoffs/active/speculative-decoding.md and handoffs/active/kv-cache-program.md",
      "application": "Review the target sampler RNG cursor lifecycle for stable per-request coordinates under permutations, batch resize and slot recycle; borrow a small backend-neutral metamorphic fixture if current tests lack it. Treat state slots as a related pattern for existing restore ownership.",
      "disposition": "context-only",
      "ledger_ids": [
        "RI-2985"
      ],
      "basis": "SPEC-RNG.1 at lines 679–688 already tested keyed RNG. Position-keyed draws do not resolve earlier logit drift; no reason to repeat a served sweep merely from this release."
    },
    {
      "scan_id": "scan-9365",
      "source_ref": "intake-3002#01 · PR Description, opening paragraph",
      "implementation_ref": "Upstream flashinfer/batch_invariant/sampling/{draw_spec.py,draw_api.py,stream.py,stream_kernel.py} and tests/utils/test_batch_invariant_sampling_draw.py. EPYC handoffs/active/speculative-decoding.md:679–688 pins SPEC-RNG.1 at 9154bb28f, server replay at 261db6c7e and the MI210 DFlash2 runner at 2f8af0e2d. handoffs/active/autokernel-loop.md:4912 documents 2d0016466 for CPU/HIP logf divergence and bitwise Gumbel fix.",
      "mechanism": "The unfiltered draw is identified by its source row and explicitly supplied request key.",
      "consumer": "handoffs/active/speculative-decoding.md SPEC-RNG.1, with handoffs/active/workspace-58-champion-calibration.md CH-31-DEF1 as the upstream-graph diagnostic consumer",
      "application": "Retain the SPEC-RNG.1 DO-NOT-CARRY result. If a named consumer requires same-seed cross-batch replay, first attribute failures by reusing a frozen-logit, same-key fixture with moved slot, batch width and request order. Keep within-stream repeatability and backend logit equality in distinct checks, and preserve the existing serving RNG until a consumer benefit is demonstrated.",
      "disposition": "context-only",
      "ledger_ids": [
        "RI-3002"
      ],
      "basis": "SPEC-RNG.1 at lines 679–688 already tested keyed RNG. Position-keyed draws do not resolve earlier logit drift; no reason to repeat a served sweep merely from this release."
    },
    {
      "scan_id": "scan-9405",
      "source_ref": "intake-3001#01 · PR description, guarantee R4",
      "implementation_ref": "flashinfer/batch_invariant/gdn/{api,pool,spec}.py and include/flashinfer/gdn/batch_invariant_decode.cuh @ 77a3cc5. handoffs/active/kv-cache-program.md:L1906,L1941 and handoffs/active/speculative-decoding.md:L1376-L1385 @ a660ead.",
      "mechanism": "The class requires per-token agreement across four processing paths.",
      "consumer": "handoffs/active/kv-cache-program.md",
      "application": "Fold into FlashInfer v0.7.6 action. If current per-op traces isolate GDN cross-phase mismatch, first establish same-bit rows and boundary state on fixed held-out shapes spanning prefill/chunk/decode/span and slot changes with witnessed valid domains. Gate any opt-in candidate against raw A/A, latency and VRAM. Existing RS-REPLAY tests rollback correctness/speed, a separate axis.",
      "disposition": "context-only",
      "ledger_ids": [
        "RI-3001"
      ],
      "basis": "No native CUTE/SM100 kernel on MI210; fixed chunking can sacrifice occupancy and state pooling needs an ownership and alias contract. CPU state rows are already under CAFE-5."
    },
    {
      "scan_id": "scan-2611.33402",
      "source_ref": "intake-2994#01 · §3.3 Compiling the delegation policy",
      "implementation_ref": "Pinned P3 audit at lines 1043–1067 names _delegate_single, _delegate_parallel and PromptForge resolver.py brief-based fanout. Heterogeneous access-list chaining remains P2-gated. Existing isolation and homogeneous fanout can exercise a profiled advisory without adding delegate_chain. Orchestrator checkout absent inside lane.",
      "mechanism": "Partial Routing uses both mean and worst observed lead–worker quality gaps to estimate delegation risk.",
      "consumer": "handoffs/active/routing-program.md:1043 P3 — Heterogeneous structured delegation chain",
      "application": "Read existing P3 bounded worker traces to freeze task-family groups, failure categories and request-cost attribution. On unseen groups compare same lead alone, plan-only, unguided and profile tiers with the same available lead/worker pair. Log invalid, skipped and failed runs; predeclare minimum quality and latency margin and sample cap, stop if existing traces cannot identify routed spans. No P3 activation decision follows an offline or mock result.",
      "disposition": "context-only",
      "ledger_ids": [
        "RI-2994"
      ],
      "basis": "P3 chaining is gated. Delegation report persistence records handles; it cannot by itself price work or validate a policy. Hosted API dollars do not price co-resident EPYC workers."
    },
    {
      "scan_id": "scan-2611.34756",
      "source_ref": "intake-2996#01 · Abstract, method in §§3.3–3.4",
      "implementation_ref": "Pinned HIL-16b references HIL-16a verified 80 recordings / 11 failed, and src/trace/replay/graph_harness.py:make_production_harness (orchestrator a16750a8). It documents later-pilot no-effect mock/diagnostic limits and unresolved source-era replay acceptance. This is an execution replay instrument; the paper trains student weights on new response samples. Orchestrator checkout absent inside lane.",
      "mechanism": "CARE-OPD broadens history coverage with student-seeded teacher completions, gates response confidence, and selects replay turns from downstream execution evidence.",
      "consumer": "handoffs/active/harness-program.md:1800 HIL-16b — Graph harness binding and real prefix replay, then the four-arm run",
      "application": "Use existing HIL-16a source-era clean trace manifests and HIL-12/13 first-visible-deviation labels if joinable. Freeze original trajectories and hold out whole tasks; compare equal-sized evidence-ranked, random and depth-ranked turn lists for externally judged hit rate, late-turn recall and abstentions. Keep confounded or missing cases in denominator. Stop if no independent decision-turn labels or if equal-budget selection offers no material held-out gain. Keep existing four-arm replay acceptance independent of this diagnostic; only a positive diagnostic warrants testing its turn priorities in replay.",
      "disposition": "context-only",
      "ledger_ids": [
        "RI-2996"
      ],
      "basis": "HIL-16b is eval instrumentation. Neither replay nor a confidence gate alone trains a student, and the paper’s environment and teacher budget are not an EPYC estimate."
    },
    {
      "scan_id": "scan-2610.32322",
      "source_ref": "intake-3005#01 · §2.4 Validity gate and Eq. 2",
      "implementation_ref": "handoffs/active/eval-tower-program.md:L474-L489,L1723 @ a660ead. epyc-orchestrator scripts/autopilot/skill_efficacy.py:L221-L270 @ faa783c7 distinguishes comparable suite aggregates and negative-delta decision; retirement requires a per-model skill/probe and library-ablation contract absent in this path.",
      "mechanism": "The validity gate requires evidence of aided gain from another model on the same scored items.",
      "consumer": "handoffs/active/eval-tower-program.md",
      "application": "Retain as a design for reversible retirement only when a SkillBank owner proposes a specific existing model/skill pair for suppression. Then freeze behavior-specific task families, verifier and model identity, include untouched-on-policy evaluation and challenge probes with an external witness, preserve abstentions and invalid counts, compare full library versus reversible removal with per-task receipts, and predeclare tolerated regression and restoration conditions. EV-10a still validates mutation efficacy by paired per-suite delta; do not reuse retirement labels as loader efficacy or automatically suppress rules/artifacts.",
      "disposition": "context-only",
      "ledger_ids": [
        "RI-3005"
      ],
      "basis": "A low marginal lift can reflect a task that both arms fail. EV-10a measures efficacy; a per-model retirement policy needs evidence of unaided competence."
    }
  ],
  "outcome_reviews": {
    "RI-2993": {
      "required_outcome": "Compare #27530 cleanup prerequisites against an experimental branch and port the minimal defensive guard with the isolation test. Verify valid restore, recoverable invalid restore and unchanged neighboring sequence on Zen5 and actual gfx90a resident state.",
      "review_status": "preserved",
      "review_basis": "C21 state_seq_set_data constructs its device reader and checks mem_storage before the catch. Its catch only logs. KPF-17 exercises partial restore; Q8-SERVED-CKPT-COPY-1 uses the host writer and times transfers. Neither checks this failure boundary. A source-pinned regression on two populated slots must return zero on failure, clear any partially modified destination as required, preserve the neighbor, and round-trip valid state. Repeat on a new sequence ID and in reverse slot order. Log each case and return value. Require a CPU build proof before model-backed evaluation and HIP residency proof before claiming device coverage.",
      "task_refs": [
        {
          "owner": "handoffs/active/kv-cache-program.md",
          "task_id": "KPF-RESTORE-RECOVERY",
          "task_text": "- [ ] **KPF-RESTORE-RECOVERY** [non-inference] Restore destination-only error recovery for device checkpoints on the experimental kernel and add valid, absent-storage, truncated-header and partial-read regression cases.",
          "acceptance": "A source-pinned regression on two populated slots must return zero on failure, clear any partially modified destination as required, preserve the neighbor, and round-trip valid state. Repeat on a new sequence ID and in reverse slot order. Log each case and return value. Require a CPU build proof before model-backed evaluation and HIP residency proof before claiming device coverage."
        }
      ]
    },
    "RI-3000": {
      "required_outcome": "For an experimental cache candidate apply discard-before-destruction to owned buffer-reader failure exits and scope hybrid rollback correctly. Gate defensive isolated-state correctness with unaffected calls, preserved-unmodified and removed-modified outcomes across host/device. Q8-SERVED-CKPT-COPY-1 consumes the result and retains its timing gate.",
      "review_status": "preserved",
      "review_basis": "C21 state_seq_set_data constructs its device reader and checks mem_storage before the catch. Its catch only logs. KPF-17 exercises partial restore; Q8-SERVED-CKPT-COPY-1 uses the host writer and times transfers. Neither checks this failure boundary. A source-pinned regression on two populated slots must return zero on failure, clear any partially modified destination as required, preserve the neighbor, and round-trip valid state. Repeat on a new sequence ID and in reverse slot order. Log each case and return value. Require a CPU build proof before model-backed evaluation and HIP residency proof before claiming device coverage.",
      "task_refs": [
        {
          "owner": "handoffs/active/kv-cache-program.md",
          "task_id": "KPF-RESTORE-RECOVERY",
          "task_text": "- [ ] **KPF-RESTORE-RECOVERY** [non-inference] Restore destination-only error recovery for device checkpoints on the experimental kernel and add valid, absent-storage, truncated-header and partial-read regression cases.",
          "acceptance": "A source-pinned regression on two populated slots must return zero on failure, clear any partially modified destination as required, preserve the neighbor, and round-trip valid state. Repeat on a new sequence ID and in reverse slot order. Log each case and return value. Require a CPU build proof before model-backed evaluation and HIP residency proof before claiming device coverage."
        }
      ]
    },
    "RI-2995": {
      "required_outcome": "Attach an observational sidecar to the remaining EV-10a paired-mutation A/B: verify normalized effective skill manifests per arm and audit scorer constraints against visible task text, retain paired item outcomes and full denominator. Report within-cell shuffled null, untouched later draws for decisions, and task-family holdout for generalization. Reuse the suite-level gate with diagnostic sidecar output. Stop at a preregistered valid-pair cap or declared precision and do not use aggregate efficacy as evidence of task-level stability.",
      "review_status": "preserved",
      "review_basis": "At orchestrator faa783c7, scripts/autopilot/skill_efficacy.py:313 and :352 aggregate suite-keyed efficacy. EV-10a and AEI-RERUN-FLIP can consume a diagnostic replay while the skill-bank activation policy stays with its current owner. Freeze archive hashes, paired seeds, grader revision, effective inventories and folds. Compare the current suite gate, no gate and selected gate on the same cells. Refit the policy on each permuted training fold. Score untouched later trials and unseen task families separately with paired intervals. Publish cell-level outcomes including missing and timed-out arms. Stop if effective-arm identity or split independence cannot be established; a gain inside the null band cannot authorize gating.",
      "task_refs": [
        {
          "owner": "handoffs/active/eval-tower-program.md",
          "task_id": "EV-SKILL-NULL-REPLAY",
          "task_text": "- [ ] **EV-SKILL-NULL-REPLAY** [non-inference] Add a task-level replay report for skill gating that records effective skills, scorer requirements, within-cell shuffled labels and held-out decisions.",
          "acceptance": "Freeze archive hashes, paired seeds, grader revision, effective inventories and folds. Compare the current suite gate, no gate and selected gate on the same cells. Refit the policy on each permuted training fold. Score untouched later trials and unseen task families separately with paired intervals. Publish cell-level outcomes including missing and timed-out arms. Stop if effective-arm identity or split independence cannot be established; a gain inside the null band cannot authorize gating."
        }
      ]
    },
    "RI-2998": {
      "required_outcome": "Apply precommitted held-out policy and within-cell shuffled calibration at any SkillBank promotion. Freeze model/task/harness and thresholds, use disjoint tasks or new trials, archive per-trial decision/reward/graded/invalid/abstention denominators, compare always-load versus gate with existing paired and rerun logic, and predeclare minimum benefit and shuffle separation.",
      "review_status": "preserved",
      "review_basis": "At orchestrator faa783c7, scripts/autopilot/skill_efficacy.py:313 and :352 aggregate suite-keyed efficacy. EV-10a and AEI-RERUN-FLIP can consume a diagnostic replay while the skill-bank activation policy stays with its current owner. Freeze archive hashes, paired seeds, grader revision, effective inventories and folds. Compare the current suite gate, no gate and selected gate on the same cells. Refit the policy on each permuted training fold. Score untouched later trials and unseen task families separately with paired intervals. Publish cell-level outcomes including missing and timed-out arms. Stop if effective-arm identity or split independence cannot be established; a gain inside the null band cannot authorize gating.",
      "task_refs": [
        {
          "owner": "handoffs/active/eval-tower-program.md",
          "task_id": "EV-SKILL-NULL-REPLAY",
          "task_text": "- [ ] **EV-SKILL-NULL-REPLAY** [non-inference] Add a task-level replay report for skill gating that records effective skills, scorer requirements, within-cell shuffled labels and held-out decisions.",
          "acceptance": "Freeze archive hashes, paired seeds, grader revision, effective inventories and folds. Compare the current suite gate, no gate and selected gate on the same cells. Refit the policy on each permuted training fold. Score untouched later trials and unseen task families separately with paired intervals. Publish cell-level outcomes including missing and timed-out arms. Stop if effective-arm identity or split independence cannot be established; a gain inside the null band cannot authorize gating."
        }
      ]
    },
    "RI-2983": {
      "required_outcome": "First count reachable fused small-K rows in current MI210 roles; if hit, compare baseline, split only, and split plus inclusive threshold at neighboring K and odd M, with token throughput and output parity.",
      "review_status": "preserved",
      "review_basis": "The split changes reads in fused short rows, the inclusive cutoff changes eligibility, and C17 already carries fa221af5d for odd expert stores. The measured RTX Q8 case was flat. Pin trace digests, graph and candidate SHA. Emit op, quant type, K, rows, fused flag, width and frequency or unknown for every cell. Check later traces from each role. A verified zero closes that role. For hits compare split only, threshold only and both against current dispatch around exact-fit K. Include odd expert tails on wave64 before measuring time.",
      "task_refs": [
        {
          "owner": "handoffs/active/autokernel-loop.md",
          "task_id": "AK-SHORT-ROW-CENSUS",
          "task_text": "- [ ] **AK-SHORT-ROW-CENSUS** [non-inference] Count eligible fused small-K MMVQ calls in retained 27B and A3B traces at widths one through four.",
          "acceptance": "Pin trace digests, graph and candidate SHA. Emit op, quant type, K, rows, fused flag, width and frequency or unknown for every cell. Check later traces from each role. A verified zero closes that role. For hits compare split only, threshold only and both against current dispatch around exact-fit K. Include odd expert tails on wave64 before measuring time."
        }
      ]
    },
    "RI-2991": {
      "required_outcome": "Replay small set of saved DS41 route traces as placement + bytes feasibility, independent of held DS41 inference. Measure resident-route fraction, rows per cold expert, dedup ratio and timing estimates for same-placement CPU-only cold, GPU weight upload and mixed execution. If favorable, compare matched upload threshold/loading and parity before porting HIP graph.",
      "review_status": "preserved",
      "review_basis": "INF-45 already owns the route tap. Reuse it for DS41 and A3B; 64 GB is total device capacity. The paper’s 512-token crossover and dual-Xeon bandwidth cannot fix the NPS4 crossover. Freeze trace manifest, expert sizes, host bandwidth evidence and HBM reservations for weights, KV, scratch and allocator margin. Fill the remaining bytes by utility across layers. Fit on early turns, score later whole sessions. Return per-turn hits, cold rows, unique bytes, join bound and invalid/unattributed counts. Compare same capacity, loading and phase threshold to current placement and host-only. Stop if the saved bytes cannot exceed the join cost within timing uncertainty, or if route identities are missing.",
      "task_refs": [
        {
          "owner": "handoffs/active/cpu-decode-roofline-program.md",
          "task_id": "MOE-STATIC-POOL-REPLAY",
          "task_text": "- [ ] **MOE-STATIC-POOL-REPLAY** [non-inference] Replay existing per-layer expert routes against a capacity-bounded static GPU pool and price NUMA-local cold routes and deduplicated long-prefill uploads.",
          "acceptance": "Freeze trace manifest, expert sizes, host bandwidth evidence and HBM reservations for weights, KV, scratch and allocator margin. Fill the remaining bytes by utility across layers. Fit on early turns, score later whole sessions. Return per-turn hits, cold rows, unique bytes, join bound and invalid/unattributed counts. Compare same capacity, loading and phase threshold to current placement and host-only. Stop if the saved bytes cannot exceed the join cost within timing uncertainty, or if route identities are missing."
        }
      ]
    },
    "RI-2988": {
      "required_outcome": "Inventory exact artifacts and indexed-KV ABI first; compare replayed index coverage and KV bytes in the DS41 lane without reopening held tests. Promote to served throughput only when paired weights and index custody are available.",
      "review_status": "preserved",
      "review_basis": "INF-77 consumes the sparse selection. INF-50 can separately reuse target KV on full-attention layers, but a dense model supplies no target sparsity. A contract inventory can decide whether a converter or cache export is the next real dependency. Record exact weight/config revisions, source layer pairs, strides, dtype, ownership and one-step index timestamp. Walk representative released mappings against DS41 and the dense 27B control. Require a defined KV read and epoch across accept, reject and slot reuse before any execution probe. Mark unsupported layers and absent weights explicitly.",
      "task_refs": [
        {
          "owner": "handoffs/active/speculative-decoding.md",
          "task_id": "DF2-TARGET-KV-CONTRACT",
          "task_text": "- [ ] **DF2-TARGET-KV-CONTRACT** [non-inference] Compare the released DFly2 target and drafter mappings with the local full-attention KV layout, sparse-index epoch and rollback semantics.",
          "acceptance": "Record exact weight/config revisions, source layer pairs, strides, dtype, ownership and one-step index timestamp. Walk representative released mappings against DS41 and the dense 27B control. Require a defined KV read and epoch across accept, reject and slot reuse before any execution probe. Mark unsupported layers and absent weights explicitly."
        }
      ]
    },
    "RI-2999": {
      "required_outcome": "Use as companion to DFly2. For INF-77 pin target/drafter versions and prove read-only released weight/latent/layer/last-accepted-position mappings, estimate gather bytes versus matched-width MTP/DSpark, then gate experimental serving if economics justify it. INF-50 can reuse target context on full-attention layers separately from native sparse index sharing.",
      "review_status": "preserved",
      "review_basis": "INF-77 consumes the sparse selection. INF-50 can separately reuse target KV on full-attention layers, but a dense model supplies no target sparsity. A contract inventory can decide whether a converter or cache export is the next real dependency. Record exact weight/config revisions, source layer pairs, strides, dtype, ownership and one-step index timestamp. Walk representative released mappings against DS41 and the dense 27B control. Require a defined KV read and epoch across accept, reject and slot reuse before any execution probe. Mark unsupported layers and absent weights explicitly.",
      "task_refs": [
        {
          "owner": "handoffs/active/speculative-decoding.md",
          "task_id": "DF2-TARGET-KV-CONTRACT",
          "task_text": "- [ ] **DF2-TARGET-KV-CONTRACT** [non-inference] Compare the released DFly2 target and drafter mappings with the local full-attention KV layout, sparse-index epoch and rollback semantics.",
          "acceptance": "Record exact weight/config revisions, source layer pairs, strides, dtype, ownership and one-step index timestamp. Walk representative released mappings against DS41 and the dense 27B control. Require a defined KV read and epoch across accept, reject and slot reuse before any execution probe. Mark unsupported layers and absent weights explicitly."
        }
      ]
    },
    "RI-2984": {
      "required_outcome": "Reuse op-level batch tests and route receipts on the existing MI210 census, then do one fixed-input Zen5 replay across single and multiple columns for the first divergent op. Preserve the existing full audit-arm gate.",
      "review_status": "preserved",
      "review_basis": "RKA-BATCH-INV-CENSUS-1 closed with five of six ops requiring changes. Q8IP-DET2 and devhandoff/Pando require a same-width baseline; fixed geometry cannot repair racy summation. This supplements GPU-27B-LONGCTX-SECOND-NONDET without reopening the full audit arm. Freeze model, store digest, prompt bytes, state, seeds and launch choices. Replay OFF/OFF and width-1/verify on identical logits inputs where captured. Preserve first mismatched op, tensor bits, route, reduction geometry and missing captures. Hold out later long prompts. Stop on a located first mismatch or insufficient captures; measure HIP cost for that isolated path only after a matched input reproduces.",
      "task_refs": [
        {
          "owner": "handoffs/active/kv-cache-program.md",
          "task_id": "KV-NONDET-FIRST-DIFF",
          "task_text": "- [ ] **KV-NONDET-FIRST-DIFF** [non-inference] Add fixed-width repeat and cross-width first-divergence comparisons to the long-context determinism diagnosis using retained inputs and dispatch receipts.",
          "acceptance": "Freeze model, store digest, prompt bytes, state, seeds and launch choices. Replay OFF/OFF and width-1/verify on identical logits inputs where captured. Preserve first mismatched op, tensor bits, route, reduction geometry and missing captures. Hold out later long prompts. Stop on a located first mismatch or insufficient captures; measure HIP cost for that isolated path only after a matched input reproduces."
        }
      ]
    },
    "RI-2986": {
      "required_outcome": "Check model graph and CPU traces for KDA reachability. If reachable, compare scalar versus vector at real prefill/TG shapes with exponent and recurrent-state error/greedy checks; stop once the op cannot explain meaningful end-to-end time.",
      "review_status": "preserved",
      "review_basis": "CAFE-5 treats GDN rows. A generic GDN count leaves backend-specific KDA call reachability unresolved; Intel AVX2 results do not measure Zen 5. Pin graph, model, ISA, row lengths and trace windows; emit per-loop counts, time share and missing fields. Repeat on a later prompt. Stop on proven zero or an Amdahl bound smaller than the paired timing error. Otherwise compare scalar and AVX-512 at actual sizes, scalar tails, exceptional inputs and recurrent-state error before throughput.",
      "task_refs": [
        {
          "owner": "handoffs/active/cpu-decode-roofline-program.md",
          "task_id": "CPU-KDA-EXP-CENSUS",
          "task_text": "- [ ] **CPU-KDA-EXP-CENSUS** [non-inference] Identify whether either KDA exponential loop executes in Q38FN CPU traces and bound its contribution to decode and prefill.",
          "acceptance": "Pin graph, model, ISA, row lengths and trace windows; emit per-loop counts, time share and missing fields. Repeat on a later prompt. Stop on proven zero or an Amdahl bound smaller than the paired timing error. Otherwise compare scalar and AVX-512 at actual sizes, scalar tails, exceptional inputs and recurrent-state error before throughput."
        }
      ]
    },
    "RI-3003": {
      "required_outcome": "Extend the existing SPEC-PIT post-sampling fixture with exact ties just above/below the top-p boundary, filter order, -inf and no-op cases, and compare named support, sampled token and normalized probability against the current served sampler on identical rows/keys. Persist native versus whole-tie results and full-row versus post-filter logprob labels distinctly. Promote a new policy only if a consumer requests it and the same-denominator gate passes.",
      "review_status": "preserved",
      "review_basis": "SPEC-PIT.1 addresses distribution equivalence. A passing PIT result cannot establish that a reported log probability refers to the deployed filtered support. Hash rows, seeds and sampler chain; test top-k, top-p, min-p, both orders, no-op, infinities and exact ties. Compare native support to a whole-tie reference with identical inputs, then repeat on held-out row permutations. Emit every support and denominator; reject ambiguous probability labels. File a compatibility result. Serving policy requires a separate gate.",
      "task_refs": [
        {
          "owner": "handoffs/active/speculative-decoding.md",
          "task_id": "SPEC-FILTER-TIES",
          "task_text": "- [ ] **SPEC-FILTER-TIES** [non-inference] Extend the frozen-logit sampler fixture to record retained support, drawn token and full versus post-filter probabilities at boundary ties.",
          "acceptance": "Hash rows, seeds and sampler chain; test top-k, top-p, min-p, both orders, no-op, infinities and exact ties. Compare native support to a whole-tie reference with identical inputs, then repeat on held-out row permutations. Emit every support and denominator; reject ambiguous probability labels. File a compatibility result. Serving policy requires a separate gate."
        }
      ]
    },
    "RI-3004": {
      "required_outcome": "Census the EPYC DFlash2/recurrent state path for residual state-sized copies versus direct writes and bound bytes/ms on both hardware paths. Reuse existing state controls, keeping a CPU fixture for permuted/noncontiguous slots, null initialization, alias rejection and slot reset/reuse. Only carry a direct-write arm when the current capture identifies a remaining copy boundary and its slot owner can enforce uniqueness and read-before-write lifecycle.",
      "review_status": "preserved",
      "review_basis": "Earlier replay optimization moved control counts on device. State-pool ownership, strided writes and slot safety remain separate from seed determinism and from chunk arithmetic. Pin trace and source revisions plus the initial state; follow each pointer, dtype and byte count across gather, transition and scatter. Compare direct-write candidates to current device replay counts. Include a later trace and poisoned non-target slots. Report unresolved copies separately; stop at no remaining transfer. Require unique destination slots and read-before-write fences before any aliasing experiment.",
      "task_refs": [
        {
          "owner": "handoffs/active/kv-cache-program.md",
          "task_id": "KPF-STATE-COPY-CENSUS",
          "task_text": "- [ ] **KPF-STATE-COPY-CENSUS** [non-inference] Trace recurrent-state ownership and residual state-sized copies across rollback, slot reuse and phase transitions on CPU and HIP.",
          "acceptance": "Pin trace and source revisions plus the initial state; follow each pointer, dtype and byte count across gather, transition and scatter. Compare direct-write candidates to current device replay counts. Include a later trace and poisoned non-target slots. Report unresolved copies separately; stop at no remaining transfer. Require unique destination slots and read-before-write fences before any aliasing experiment."
        }
      ]
    },
    "RI-2982": {
      "required_outcome": "On an experimental tree compare the current compiler and a clang-23 candidate on gfx90a, verify emitted BF16 MFMA and run a small BF16 correctness smoke only if planning toolchain adoption.",
      "review_status": "closed-with-basis",
      "review_basis": "DF2-11-BF16 concerns the executed BF16 route. The upstream patch addresses compiler operand types and supplies no CDNA runtime measurement. Trigger on an actual LLVM 23 qualification build for gfx90a. Compare old/new fragments and emitted ISA at both compilers; run BF16 op parity and DF2 target-route smoke using the candidate binary.",
      "task_refs": []
    },
    "RI-2992": {
      "required_outcome": "Locate scheduler sharing primitive and audit ordering, lifetime, realloc and separate fallback. If concrete MI210 fit is blocked by scratch, prototype under experimental ROCm eligibility and compare achieved peak VRAM, greedy exactness and throughput with overlap controls.",
      "review_status": "closed-with-basis",
      "review_basis": "The upstream guard literally requires CUDA; the fork names HIP ROCm. The C21 scheduler lacks the sharing primitive. DEV-INJECT removes a transfer and does not establish safe aliasing. Trigger on a measured fit failure with target/draft scratch live ranges that do not overlap. Record separate buffers, buffer types, async completion, realloc and actual peak. Test eligibility by capabilities and preserve independent fallback.",
      "task_refs": []
    },
    "RI-2987": {
      "required_outcome": "On an eligible DS41 or Q38FN low-bit lane, use real expert-tensor shapes to compare normalized format bytes, arithmetic correctness and decode/prefill latency to incumbent GGUF, then equal-bytes quality before funding a model port. Keep precision switching a distinct experiment.",
      "review_status": "closed-with-basis",
      "review_basis": "Single-rate comparisons need all LUT and alignment overhead. No MI210 or Zen5 performance evidence; on-device LPDDR energy estimate cannot rank either platform. Trigger when a proposed multi-rate deployment identifies the exact layers/rates and an incumbent that misses its fit or quality target. Run integer bit unpack against reference bytes, compare shared row tables in LDS and AVX-512 byte-permute/split tables with scalar tails, then paired KLD and held-out throughput against incumbent EXL3/GGUF.",
      "task_refs": []
    },
    "RI-2997": {
      "required_outcome": "Use as companion evidence for the paper. Under INF-80 compare effective bytes and scalar decode on frozen EXL3 fixtures and held-out KLD/model inputs before a single AVX-512 or HIP microbench. Freeze baseline, raw row outputs, invalid denominators, and latency/quality stops.",
      "review_status": "closed-with-basis",
      "review_basis": "Single-rate comparisons need all LUT and alignment overhead. No MI210 or Zen5 performance evidence; on-device LPDDR energy estimate cannot rank either platform. Trigger when a proposed multi-rate deployment identifies the exact layers/rates and an incumbent that misses its fit or quality target. Run integer bit unpack against reference bytes, compare shared row tables in LDS and AVX-512 byte-permute/split tables with scalar tails, then paired KLD and held-out throughput against incumbent EXL3/GGUF.",
      "task_refs": []
    },
    "RI-2989": {
      "required_outcome": "Prioritize released boosted checkpoint with compatible format and same serving graph; run early-position and tail acceptance plus latency per chosen K on both devices. If training is required, perform dry-fit accounting and one-step peak reserve check against an explicit margin.",
      "review_status": "closed-with-basis",
      "review_basis": "Published memory is per GPU in a four-GB300 configuration. CPU and MI210 serving need acceptance-by-position and wall time at the same K before a head switch. Trigger on a per-position acceptance deficit with a compatible frozen backbone/head pair and priced training baseline. Log optimizer/gradient/activation/weights and allocator peak in a single-device microbatch dry fit; retain HSM mix and HSGD detach probability separately.",
      "task_refs": []
    },
    "RI-2990": {
      "required_outcome": "Add one benchmark-only immutable draft-prefix arm to a separate-checkpoint path, with zero-exemplar same-token-budget control, target-only reference, held-out nonleaking exemplars, exact sampled-distribution check and session TTFT/time by cache state. Keep verifier prompt and sampler identical.",
      "review_status": "closed-with-basis",
      "review_basis": "The existing DFlash2 path shares model features; a classical separate-proposal verifier is the consumer. Additional KV and prefill may overwhelm acceptance gains. Require stable shared tokenizer, true proposal probabilities and a family with disjoint exemplar and evaluation prompts. Compare target alone, symmetric draft, length-matched irrelevant and task-matched exemplars at equal cache state; measure TTFT and full session time.",
      "task_refs": []
    },
    "RI-2985": {
      "required_outcome": "Review the target sampler RNG cursor lifecycle for stable per-request coordinates under permutations, batch resize and slot recycle; borrow a small backend-neutral metamorphic fixture if current tests lack it. Treat state slots as a related pattern for existing restore ownership.",
      "review_status": "closed-with-basis",
      "review_basis": "SPEC-RNG.1 at lines 679–688 already tested keyed RNG. Position-keyed draws do not resolve earlier logit drift; no reason to repeat a served sweep merely from this release. Trigger on a recorded fixed-logit replay difference at equal seed and offset under reorder, recycle or filter-boundary ties, or a consumer requiring full versus retained log probabilities. Compare frozen logits/filters first.",
      "task_refs": []
    },
    "RI-3002": {
      "required_outcome": "Retain the SPEC-RNG.1 DO-NOT-CARRY result. If a named consumer requires same-seed cross-batch replay, first attribute failures by reusing a frozen-logit, same-key fixture with moved slot, batch width and request order. Keep within-stream repeatability and backend logit equality in distinct checks, and preserve the existing serving RNG until a consumer benefit is demonstrated.",
      "review_status": "closed-with-basis",
      "review_basis": "SPEC-RNG.1 at lines 679–688 already tested keyed RNG. Position-keyed draws do not resolve earlier logit drift; no reason to repeat a served sweep merely from this release. Trigger on a recorded fixed-logit replay difference at equal seed and offset under reorder, recycle or filter-boundary ties, or a consumer requiring full versus retained log probabilities. Compare frozen logits/filters first.",
      "task_refs": []
    },
    "RI-3001": {
      "required_outcome": "Fold into FlashInfer v0.7.6 action. If current per-op traces isolate GDN cross-phase mismatch, first establish same-bit rows and boundary state on fixed held-out shapes spanning prefill/chunk/decode/span and slot changes with witnessed valid domains. Gate any opt-in candidate against raw A/A, latency and VRAM. Existing RS-REPLAY tests rollback correctness/speed, a separate axis.",
      "review_status": "closed-with-basis",
      "review_basis": "No native CUTE/SM100 kernel on MI210; fixed chunking can sacrifice occupancy and state pooling needs an ownership and alias contract. CPU state rows are already under CAFE-5. Trigger on equal initial state/input and first mismatch in the GDN transition across phase or a measured recurrent-state copy. Compare fixed chunking, zero padding and tail at a fixed logical token. Verify poison slots, repeated indices, dtype and fences separately for the pool branch.",
      "task_refs": []
    },
    "RI-2994": {
      "required_outcome": "Read existing P3 bounded worker traces to freeze task-family groups, failure categories and request-cost attribution. On unseen groups compare same lead alone, plan-only, unguided and profile tiers with the same available lead/worker pair. Log invalid, skipped and failed runs; predeclare minimum quality and latency margin and sample cap, stop if existing traces cannot identify routed spans. No P3 activation decision follows an offline or mock result.",
      "review_status": "closed-with-basis",
      "review_basis": "P3 chaining is gated. Delegation report persistence records handles; it cannot by itself price work or validate a policy. Hosted API dollars do not price co-resident EPYC workers. Trigger on retained lead/worker traces with attributed worker spans and independent task groups; freeze judge and rubric, measure task quality, cache-adjusted tokens, end-to-end time, queueing and CPU/GPU occupancy. Count rejected/failed work in every arm.",
      "task_refs": []
    },
    "RI-2996": {
      "required_outcome": "Use existing HIL-16a source-era clean trace manifests and HIL-12/13 first-visible-deviation labels if joinable. Freeze original trajectories and hold out whole tasks; compare equal-sized evidence-ranked, random and depth-ranked turn lists for externally judged hit rate, late-turn recall and abstentions. Keep confounded or missing cases in denominator. Stop if no independent decision-turn labels or if equal-budget selection offers no material held-out gain. Keep existing four-arm replay acceptance independent of this diagnostic; only a positive diagnostic warrants testing its turn priorities in replay.",
      "review_status": "closed-with-basis",
      "review_basis": "HIL-16b is eval instrumentation. Neither replay nor a confidence gate alone trains a student, and the paper’s environment and teacher budget are not an EPYC estimate. Trigger on a local student/teacher run with verified downstream outcomes and a fixed replay budget. Compare random and position-matched selection to evidence selection on unseen tasks, preserve all rejected prefixes, and separately score confidence calibration.",
      "task_refs": []
    },
    "RI-3005": {
      "required_outcome": "Retain as a design for reversible retirement only when a SkillBank owner proposes a specific existing model/skill pair for suppression. Then freeze behavior-specific task families, verifier and model identity, include untouched-on-policy evaluation and challenge probes with an external witness, preserve abstentions and invalid counts, compare full library versus reversible removal with per-task receipts, and predeclare tolerated regression and restoration conditions. EV-10a still validates mutation efficacy by paired per-suite delta; do not reuse retirement labels as loader efficacy or automatically suppress rules/artifacts.",
      "review_status": "closed-with-basis",
      "review_basis": "A low marginal lift can reflect a task that both arms fail. EV-10a measures efficacy; a per-model retirement policy needs evidence of unaided competence. Freeze baseline unaided success, skill-on/skill-off trials, invalid calls and retirement rule; reserve new tasks/trials, check retained reward and false retirements before withdrawing any skill.",
      "task_refs": []
    }
  },
  "proposed_tasks": [
    {
      "owner": "handoffs/active/kv-cache-program.md",
      "task_text": "- [ ] **KPF-RESTORE-RECOVERY** [non-inference] Restore destination-only error recovery for device checkpoints on the experimental kernel and add valid, absent-storage, truncated-header and partial-read regression cases."
    },
    {
      "owner": "handoffs/active/eval-tower-program.md",
      "task_text": "- [ ] **EV-SKILL-NULL-REPLAY** [non-inference] Add a task-level replay report for skill gating that records effective skills, scorer requirements, within-cell shuffled labels and held-out decisions."
    },
    {
      "owner": "handoffs/active/autokernel-loop.md",
      "task_text": "- [ ] **AK-SHORT-ROW-CENSUS** [non-inference] Count eligible fused small-K MMVQ calls in retained 27B and A3B traces at widths one through four."
    },
    {
      "owner": "handoffs/active/cpu-decode-roofline-program.md",
      "task_text": "- [ ] **MOE-STATIC-POOL-REPLAY** [non-inference] Replay existing per-layer expert routes against a capacity-bounded static GPU pool and price NUMA-local cold routes and deduplicated long-prefill uploads."
    },
    {
      "owner": "handoffs/active/speculative-decoding.md",
      "task_text": "- [ ] **DF2-TARGET-KV-CONTRACT** [non-inference] Compare the released DFly2 target and drafter mappings with the local full-attention KV layout, sparse-index epoch and rollback semantics."
    },
    {
      "owner": "handoffs/active/kv-cache-program.md",
      "task_text": "- [ ] **KV-NONDET-FIRST-DIFF** [non-inference] Add fixed-width repeat and cross-width first-divergence comparisons to the long-context determinism diagnosis using retained inputs and dispatch receipts."
    },
    {
      "owner": "handoffs/active/cpu-decode-roofline-program.md",
      "task_text": "- [ ] **CPU-KDA-EXP-CENSUS** [non-inference] Identify whether either KDA exponential loop executes in Q38FN CPU traces and bound its contribution to decode and prefill."
    },
    {
      "owner": "handoffs/active/speculative-decoding.md",
      "task_text": "- [ ] **SPEC-FILTER-TIES** [non-inference] Extend the frozen-logit sampler fixture to record retained support, drawn token and full versus post-filter probabilities at boundary ties."
    },
    {
      "owner": "handoffs/active/kv-cache-program.md",
      "task_text": "- [ ] **KPF-STATE-COPY-CENSUS** [non-inference] Trace recurrent-state ownership and residual state-sized copies across rollback, slot reuse and phase transitions on CPU and HIP."
    }
  ]
}
```
