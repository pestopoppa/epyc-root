# KPF18-R4-FORK-CODEREAD-1 — source audit

2026-10-31. This closes the code-read scope only. **Shared-prefix physical KV layout, padded global attention extent and extent-dependent flash-attention partitioning** provide a named mechanism consistent with the child/coldE difference, exact child/child2 control, and KPF-17.4c. R4 did not capture physical cell IDs, per-evaluation `n_kv` or the selected FA kernel, so this is not causal attribution of its measured gap. No demonstrated target-state corruption was found in this read. Native `FORK_PATH_SPECIFIC` and all scientific parent acceptance remain unchanged. [belief: cc]

## Retained instrument and evidence

The original R4 `RUN_RECORD.json` pins research runner `6e8ae35a274f9a356fefe8b118db543a079277c6` and kernel image `gpu-20261020-a1f0c8cf9`. The build provenance, CMake home and compile commands identify kernel commit `a1f0c8cf9bd7102415a72577474f307b8ba94db9` at `/mnt/raid0/llm/tmp/kpf-p1-20261004/src-store-p1r-20261020`. Both existing source checkouts were tracked-clean, and the audited files matched their pinned Git blobs.

R4 used the retained 27B Q8 + DFlash2 Q8 instrument, unified KV, FA and graphs on, K/V q8_0, four slots, context 393216 and batch/ubatch 512. The native record is `/mnt/raid0/llm/tmp/f8-launchers-20261024/kpf18-s1-r4/out/records/kpf18-20261024T154558Z-1.json`. Its common teacher-forced comparison covers 256 positions after a 60000-token trunk plus 512-token suffix. Rounded display: child/coldE mean absolute logprob delta is **0.032246**, largest cold/cold delta **0.031508**, and child/child2 is exactly zero at every position. Exact values and the original rule remain in the hash-pinned native records; publication does not change their precision or verdict.

[EVIDENCE.json](EVIDENCE.json) lists exact retained paths and SHA-256 hashes for 31 verified inputs: source files, runner, original argv/prompt/forced readsets, native records/verdicts, build metadata, frontend and five relevant DSOs. Current retained DSO bytes matched the store checksums; retained startup/linkage/residency records describe the original run. CMake and compile commands include HIP, ROCWMMA FA, and the audited cache/graph/server/FA sources. This audit did not run a binary or infer historical kernel dispatch from source. The private full audit, numbered source excerpts, verifier and original resource receipt are separately hash-pinned there; raw prompts, logprob arrays, process identities and source excerpts are not copied into this public packet.

## Exact source mechanism

Line references below are in the pinned R4 source root above.

| Source | Relevant behavior |
|---|---|
| `tools/server/server-context.cpp:1843` (`do_slot_fork`, through 1892) | Erases destination membership; checkpoint mode shares source attention prefix and restores target partial checkpoint state. Draft attention/state and speculative state have their own analogous restoration. |
| `common/common.cpp:1602`; `src/llama-memory-hybrid.cpp:157` | Attention-only copy is forwarded to KV membership sharing; recurrent state remains the checkpoint's responsibility. |
| `src/llama-kv-cache.cpp:453`, `:533` | Same-stream prefix copy adds destination sequence membership to existing physical cells; it does not recompute prefix K/V values. |
| `src/llama-kv-cache.cpp:400`, `:1070` | Removal can return the allocator head to freed cells; cold allocation scans physical empty-cell state. Source-owned prefix cells remain occupied. |
| `src/llama-kv-cells.h:93`; `src/llama-kv-cache.cpp:1341` | `used_max_p1` is the highest occupied physical index plus one. Padded `n_kv` derives from this global extent, rather than logical visible sequence length. |
| `src/llama-kv-cache.cpp:1357`, `:1721` | K/V views retain physical extent. The mask excludes other sequences and future positions without compacting the K/V columns into a per-sequence tensor. |
| `src/llama-graph.cpp:2699`, `:2951` | FA receives these K/V views and the mask. |
| `ggml/src/ggml-cuda/fattn.cu:20`; `fattn-vec.cuh:260`; `fattn-wmma-f16.cu:207` | Shared CUDA/HIP launch partition depends on K extent; compiled paths traverse physical chunks/live-row masks with floating-point reductions. The vector example is not a claim that R4 selected that kernel. |

Consequently, matching resident-slot counts leaves a concrete source-level difference: a child aliases the source prefix; coldE retains that source while independently allocating and recomputing the prefix. Visible column positions, global padded extent and FA reduction partition can therefore differ. The mask still enforces sequence isolation. This is a mechanism for deterministic numerical differences, not evidence of foreign sequence values leaking into attention.

## Control reconciliation and limits

The pinned runner `scripts/benchmark/kpf18/kpf18_r4.py:341` (through 386) erases the child slot before coldE and child2, retaining the source. Child and child2 each share its prefix and process only the suffix; coldE recomputes the full prompt. Native counters confirm those paths. Occupancy snapshots contain per-slot token counts, not physical cell layout. Repeated prefix sharing and freed-head reuse are consistent with exact child/child2 equality without requiring coldE equality. Both cold and fork arms request the checkpoint at T; absence of that checkpoint in coldE is not an explanation.

KPF-17.4c's retained verdict on `82c16126f2c2599e7a156c00f3ab15045ea1b8d1` reports `none_reproduced` / `control_layout_numerics`: layout-matched Xc/Cmask, Xe/C0 and Ks/C0 are identical in all four valid cells; Cmask/C0 and Cf/Cmask differ in all four. Its smaller-context, drafter-off experiment is not R4 causal proof. The audited hybrid-memory, cache, KV-cell, graph, FA-dispatch, vector and WMMA files are byte-identical between its image and R4's image; server/common wrappers differ. Exact blob pairs are retained in the manifest.

The code-read rule is met by naming this mechanism and reconciling both controls. This does not establish that all R4 deviation is layout numerics, invalidate its cold-floor exceedance, fix a fork defect, or complete KPF-18 item 3, KPF-17.4d or any other measurement parent.

## Existing verification

The completed model-free R6 verification checked 31 input hashes, nine pinned source files, cross-image blob equality and the retained child comparisons. It returned rc0 in about 0.213 seconds with about 20 MiB sampled peak tree RSS and an empty kernel childset. No inference, build or GPU execution occurred. Publication reuses that passing evidence without rerunning it or creating a new evidentiary tier.
