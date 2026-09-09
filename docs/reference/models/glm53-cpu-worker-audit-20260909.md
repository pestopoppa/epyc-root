# GLM5Next CPU graph scheduling audit (c463f601b)

> **Correction (2026-09-09):** route verification disproved the initial state-copy scheduling diagnosis. The 34 large state copies already use the contiguous, 48-worker block path. The experimental noncontiguous path affected other copies; its padded microbenchmark does not represent the GLM state copies. Private commit `f8e2668b6` removes the experiment. The measurements below remain valid; the single-worker interpretation and proposed CPY optimization are retracted.

## Scope and evidence

This is a read-only audit of the experimental GLM5Next CPU graph. It does not make a production or retained-performance claim. The source base is `c463f601bd39d0e313b744c214b8c22f9455bcd3`. The primary capture is:

- `/mnt/raid0/llm/tmp/glm53-validation-20260908/lever3-prof-c463/evidence/canonical-on-plain-n7628-p18500/pernode.tsv`
- per-node SHA-256 `bfd74dd001ab1de00c97de5a42b58715336dba6ca546bce8b834d90f51b48dee`; server log SHA-256 `5c476e5bf597bd516c20231df6e8402c5f0ff3192251ad8a4f4a83bb1a60e093`
- 215 accepted graph evaluations with `n_nodes=7628`; 78 `n_nodes=7804` evaluations excluded
- 125.422 ms observed thread-0 node interval per accepted evaluation, of which 98.641 ms was thread-0 compute

The profiler records a thread-0 timestamp before compute, after compute, and after the graph barrier. `wall_us - compute_us` combines thread-0 idle time, other-worker lag, and barrier cost. It is not a direct barrier measurement. Metadata is snapshotted from the first accepted graph, so its two-row tensor shapes do not prove every accepted evaluation had two rows. `GGML_CPU_PROF_THREADS` is excluded because its cumulative-thread maximum, graph-boundary race, and fused-node indexing do not provide an event critical path.

## Ranked result

| Family | Nodes | Compute us/eval | Thread-0 wall us/eval | Wall-compute us/eval | Finding |
|---|---:|---:|---:|---:|---|
| `MUL_MAT` | 684 | 58,251 | 69,675 | 11,424 | Dominant dense work and worker lag; Q8 exact-row batching owns its bounded optimization path. |
| `MUL_MAT_ID` | 126 | 30,472 | 38,826 | 8,355 | Dominant expert work and worker lag; exact expert multirow owns its bounded optimization path. |
| `CPY` | 179 nodes after the named outlier exclusions | 603 | 1,645 | 1,042 | Mostly 4 MiB recurrent-state writes, so this is bandwidth-bearing work rather than a tiny barrier-only chain. |
| `GET_ROWS` | 155 nodes after the named outlier exclusions | 1,624 | 2,629 | 1,005 | Mostly 4 MiB recurrent-state gathers, also bandwidth-bearing. |
| mHC PRE+COMB+POST | 270 | 385 | 1,216 | 831 | PRE/POST already distribute over embedding elements; only COMB is tiny and token-parallel. |
| `SCALE` | 436 nodes after the named outlier exclusions | 57 | 486 | 429 | One additional node was excluded because a single 72.6 ms event accounted for essentially its entire 340 us mean delta. |
| `RMS_NORM` | 305 | 1,965 | 2,382 | 417 | Real compute, already parallel for these shapes. |
| `CONCAT` | 135 | 270 | 589 | 319 | Small aggregate opportunity. |
| `UNARY` | 426 | 438 | 738 | 300 | Small aggregate opportunity. |
| Gated delta net | 34 | 2,437 | 2,706 | 269 | Calls an internal parallel kernel and cannot enter a solo run. |
| SSM convolution | 102 | 118 | 368 | 250 | Small aggregate opportunity. |
| `CONT` | 90 | 18 | 249 | 232 | Small, but isolated around compute-bearing recurrent nodes. |

The complete per-node TSV sums to 98.112 ms compute, 124.431 ms wall, and 26.319 ms wall-minus-compute per accepted evaluation. The full profiler summary is 98.641/125.422/26.781 ms; fused and solo accounting explains the small coverage difference, so these denominators are kept separate. The two matmul families contribute 19.78 ms, or 75.2% of the per-node TSV wall-minus-compute sum. The largest apparent individual nodes (`ffn_moe_down-39`, `ffn_moe_down-7`, and `kda_g1-33`) are driven by one to three 57–73 ms maxima across 215 evaluations. They are contention/outlier evidence, not repeat-stable node-local scheduling opportunities.

## Source reachability

The existing solo-run optimization is intentionally narrow in `ggml/src/ggml-cpu/ggml-cpu.c:2748-2859`: both source and destination must be F32, have at most one row by default, contain at most 4096 destination elements, and use a whitelisted row-partitioned operation. Internal-barrier operations, `MUL_MAT*`, GDN, and the DSV4 mHC operations are excluded. Widening `GGML_TINY_SOLO_ROWS` globally was already measured negative in INF-70 and remains unjustified.

The recurrent-state costs are structural. `src/llama-graph.cpp:3328-3366` gathers each selected recurrent state through `GET_ROWS`; `src/models/delta-net-base.cpp:527-609` writes each 128x128x64 state snapshot back with `CPY`. The measured 4 MiB source/destination per layer means serializing these nodes to remove a barrier would add substantial memory work to thread 0. Eliminating the gather or write requires changing recurrent-cache addressing or making GDN write the selected cache slot directly, which has broad rollback/state-layout risk and is not a bounded scheduling patch.

The mHC kernels are already fused at the operation level. `ggml_compute_forward_dsv4_hc_pre_f32` and `_post_f32` partition `4096*tokens` and `4096*4*tokens` elements across workers (`ggml/src/ggml-cpu/ops.cpp:11447-11570`). COMB partitions only by token (`:11341-11425`), but it is immediately followed by parallel POST. Making COMB solo cannot create a long solo chain and exposes at most its measured 0.169 ms aggregate wall-minus-compute interval.

The 64-head MLA Q8 nodes previously considered for special scheduling sum to 2.071 ms wall and 1.867 ms thread-0 compute, leaving only 0.203 ms combined idle/lag/barrier. That is 0.16% of this graph's thread-0 wall and does not justify a dedicated head scheduler.

## Native-MTP target-topology capture

The bounded native-MTP capture is `/mnt/raid0/llm/tmp/glm53-validation-20260908/lever3-prof-c463/evidence/canonical-on-mtp-n8720-p18501/`. It accepted 102 graphs with `n_nodes=8720`: three 22/26-token prompt graphs and 99 target verification graphs. The node metadata comes from the first accepted 22-token prompt graph, so this is a mixed target-topology aggregate rather than a fixed-row verification profile. The exact evidence digests are:

- `pernode.tsv`: `79fa5431fed85e095572a1eaa955acd70b7036496b3df4226aff6abae32706cd`
- `node-inventory.tsv`: `bfea45ca6b6746548a74e094a4db2f4e45026c6c0d082f07ce6cb5c6e60cd508`
- `server.log`: `ffa3db1436eb6dc5557fa8cde7273d23096ffd68480a7b55bf11cbbb5c9c704d`
- `run-observation.json`: `6e7263fd375e8ba763d1f17c12da816bbe9d2f631ccca839af4a4d10da70db1b`

The per-node table sums to 218.411 ms compute, 255.442 ms wall, and 37.031 ms wall-minus-compute per accepted target-topology graph. MMID remains largest at 126.623/110.854/15.770 ms wall/compute/delta; dense matmul contributes 84.684/79.874/4.810 ms. Together they account for 20.580 ms, or 55.6% of the per-node delta.

`CPY` contributes 12.762 ms wall and 5.513 ms delta in the mixed target-topology capture. Of that, 34 `cache_s_l*` nodes with logical F32 shape `[1048576,1,4]` contribute 11.132 ms wall and 4.459 ms delta. These measurements are valid, but the initial scheduling interpretation was wrong. The recorded source and destination contiguity flags are both true for all 34 nodes. `ggml_compute_forward_dup_bytes` therefore returns through `ggml_compute_forward_dup_same_cont` before the same-shape noncontiguous branch; that existing path partitions the tensor's blocks across all 48 graph workers. `ne01=1` does not serialize these copies.

The inventory contains 408 qualifying F32 `[3,8192,1,1]` copies whose source is noncontiguous and destination is contiguous. Those nodes already partition their 8192 rows across 48 workers and total 0.564 ms compute and 1.512 ms wall, or 11.85% of measured CPY wall. The first full-model ACTIVE witness reported 8192 rows, verifying that route class. A synthetic padded, noncontiguous `[1048576,1,4]` microbenchmark showed exact 0.464135/0.183828 ms off/on means (2.524827x; median ratio 2.430912x), but that layout is absent from the profiled state-copy nodes and cannot support retention for this model. The experiment was rejected and removed in private commit `f8e2668b6`.

## Decision

The late-plain capture supports no independently high-value tiny-op or MLA scheduling change. The MTP capture measures 11.132 ms of recurrent-state copy wall time, but route verification shows those copies already use the 48-worker contiguous block path. The bounded outer-row experiment optimized an unobserved synthetic layout and touched already row-parallel small copies in the model, so it is rejected. The expert and Q8 projection-kernel experiments separately target weight reuse inside `MUL_MAT_ID` and dense Q8. Profiling shares and the drifted five-arm selector do not establish gains from those experiments.

These conclusions are bounded to the filtered late-plain and mixed MTP target-topology captures. They do not rule out further opportunities in draft, catch-up, or long-prefill graphs. Any later scheduler patch must first prove that its guarded branch reaches the measured costly nodes, then show repeat-stable per-event critical-path cost and clear same-build guard-off, exact-token, rejection/replay, short, and long controls.
