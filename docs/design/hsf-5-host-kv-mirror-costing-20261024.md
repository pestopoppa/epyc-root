# HSF-5 host KV mirror costing, MI210 np4 slots (2026-10-24, workspace-f8)

Task: `handoffs/active/heterogeneous-slot-fabric-residency.md` HSF-5 (intake-2126#record, intake-2140#record): cost a
write-through host KV mirror for the MI210 np4 slots. Cover bytes/token/layer, D2H time against the PCIe plateau and
against a 3% decode budget, the HIP-graph-capture interaction, and the handover cost the mirror would remove versus a
slot-file save. Include the mapped-host gather pattern (ROCm/mori UMBP, MIT) as the read side. The task is analytic
only, and it decides whether the host-tier prototype trigger fires. No inference was run. The analytic half (2026-10-20,
`/mnt/raid0/llm/tmp/analytics-20261020/HSF-5/REPORT.md`) left D2H, disk and gather rates unmeasured. This document
finishes the costing with the measured numbers that now exist and with labelled analytic bounds for the rest.

## Headline

- **Trigger: FIRES.** The rule is DI-140 (`kv-unified-stack-rollout.md`, dormant triggers): "the analytic write-through
  mirror costing finds the mirror fits the decode budget and removes measurable handover cost". Both conditions hold.
  - **(1) Fits the 3% decode budget.** The KV tail write-through costs 0.44% of a spec-ON step and 1.01% of a spec-OFF step
    in the worst case (128 separate copies, serialized). With one staged copy per step it costs 0.014% / 0.016%. The
    hybrid recurrent state (149.6 MiB per slot) fits only as a periodic checkpoint: each slot at least every 6 steps
    (about 18 tokens) spec-ON, or every 13 steps (13 tokens) spec-OFF. A per-step D2D snapshot plus an async D2H also
    fits, at about 0.7-0.9% ON and 1.6-2.1% OFF (analytic HBM rate).
  - **(2) Removes measurable handover cost.** Per handover the mirror removes 130 / 218 / 395 ms of tmpfs slot save,
    250 / 417 / 753 ms of disk save, or 105 / 155 / 184 ms of `--cache-ram` save stall at L = 8k / 16k / 32k. These are
    graphs-ON measured medians minus a 5.6 ms residual recurrent copy, and each exceeds its own 3-rep range.
- **What the trigger does NOT say.** The benefit per handover is sub-second. Handover frequency is still unknown: HSF-3.1
  is not judgeable, with 0 keyed session pairs. The 43.5 s ON-arm pre-eval stall is 57x the largest single transfer, so
  a mirror does not fix that stall (UFH14-LB7 owns it). Firing the trigger materializes the prototype task. It does not
  promise a serving win.
- **Box: can close.** No unmeasured rate is decision-relevant to the trigger. Three rates are unmeasured: small-copy D2H
  latency, D2H overlap with decode, and the gfx90a gather rate. They become the prototype's first measurements, and none
  can flip either condition (see "Unmeasured").

## Inputs (all measured unless labelled)

| Quantity | Value | Source |
|---|---|---|
| D2H plateau (pinned, unidirectional) | **28.20 GB/s** (28.199-28.201 on all four NUMA nodes, 128 MiB) | rocm-bandwidth-test 2.6.0, 2026-08-03, receipt `epyc-inference-research/data/mi210-h2d-d2h/20260803T131500Z/` (commit `2aa14264`), OBSERVATION |
| H2D plateau (the "28.9 GB/s" in the task text) | **28.89 GB/s** (28.866-28.895) | same receipt. The task text's "28.9" is this H2D number, and HSF-5 uses the D2H 28.20 for the write side |
| D2H small-size curve | 25.11 GB/s at 1 MiB (41.76 us), 26.59 at 2 MiB (78.88 us) | same receipt. A two-point fit gives a **4.64 us fixed cost per copy** (ANALYTIC extrapolation: the curve starts at 1 MiB, so nothing below 1 MiB is measured) |
| Slot save / restore / `--cache-ram` stalls at L = 8k / 16k / 32k | the graphs-ON table | KPF-18-S1.7g `VERDICT.json` -> `step7_graphs_on_result` (rule sha256 `79350337f034…`), quoted in `docs/design/hsf-4-results-20261023.md` |
| KV bytes | 2,176 B/token/layer (4 KV heads x 512 K+V dims x 34/32 B, q8_0) x 16 attention layers = 34,816 B/token. Server fit 34,840, step-7 fit 34,844 B/token | HSF-5 analytic half; step 7 |
| Recurrent state per slot | 149.6 MiB = 156.9 MB (48 gated-delta layers, rewritten every token) | step-7 fixed term. The server's own context checkpoint for slot 0 is 189.6 MiB (`checkpoints_slot0`) |
| Decode step, production :8083 shape (np 4, DFlash2 n-max 7) | spec ON 139.62 ms/step (pre 14.94 + dec 119.50 + post 5.17), 2.925 tokens/slot/step (pooled 12,288 tokens, 8,087 accepted); spec OFF 59.08 ms/step, 1 token/slot/step | GPU-ZOS-1a `/mnt/raid0/llm/tmp/f8-launchers-20261023/gpu-zos-1a/RUN_RECORD.json` (N = 802 / 2,808 steps). INDICATIVE: a DEBUG_TIMINGS build with an explicit sync after decode, not a champion baseline |
| Idle re-prefill | 1.3659 ms/token at L = 8000 | PB-QCOST-1 n = 0 control (as in HSF-4) |

Budget: 3% of the step = **4.19 ms** spec ON, **1.77 ms** spec OFF. Every "serialized" figure below charges the copy
fully to the step, which is the worst case. The production step is shorter than the DEBUG_TIMINGS step, because about
106 tok/s aggregate is logged against 84 here. The required checkpoint interval scales as 1/T_step: k >= 4 x 5.56 ms /
(0.03 x T_step).

## (1) Write side: bytes per step and D2H time against the budget

KV tail per step: 4 slots x tokens committed per slot x 34,840 B.

| Arm | tokens/step | bytes/step | link time at 28.20 GB/s | 128 copies (4 slots x 16 layers x K,V) at 4.64 us + link | share of step | one staged copy (gather into a contiguous device buffer, 1 D2H) | share |
|---|---|---|---|---|---|---|---|
| spec ON | 11.70 | 407,630 | 14.5 us | 0.608 ms | **0.44 %** | ~19 us | 0.014 % |
| spec OFF | 4.00 | 139,360 | 4.9 us | 0.599 ms | **1.01 %** | ~10 us | 0.016 % |

Even the per-copy layout fits with 3x headroom spec-OFF and 7x spec-ON. The staged layout makes the per-copy launch latency
irrelevant. With `--kv-unified`, the four slots' cells interleave in one buffer per layer, so the staged layout is
also the natural one.

Recurrent state (hybrid 27B): one slot checkpoint = 156.9 MB / 28.20 GB/s = **5.56 ms**.

| Design | spec ON | spec OFF |
|---|---|---|
| A. Every slot, every step, serialized D2H | 15.9 % (fails) | 37.7 % (fails) |
| A'. Each slot every k steps, serialized | fits at k >= 5.31, so **k = 6 steps = 17.6 tokens/slot** | fits at k >= 12.56, so **k = 13 steps = 13 tokens/slot** |
| B. Per-step D2D snapshot into 4 x 149.6 MiB device staging, then async D2H on a copy stream | critical path 0.69-0.90 % (ANALYTIC: 2 x 156.9 MB per slot at 1.0-1.3 TB/s effective HBM). Link occupancy 15.9 % | 1.63-2.12 %. Link occupancy 37.7 % |

The 2026-10-20 figure ("every >= 19.2 tokens per slot") used about 106 tok/s aggregate. On the GPU-ZOS-1a step it becomes 15.5
tokens (ON) or 12.6 (OFF). Restore then replays at most k steps of tokens (at most 17.6 tokens, about 24 ms at 1.37 ms/token)
from the mirrored KV tail. Design B needs about 598 MiB of extra VRAM (peak own-pid VRAM 49,726 MiB of 64 GiB in step 7,
so it fits). Design B's HBM traffic (0.63 GB/step) competes with the decode's weight streaming. This is the
reason it is charged to the critical path, and the reason it is an analytic figure. The host mirror for the full pool
(393,216 tokens + 4 states) needs 14.3 GB (q8_0), pinned and on the membind=3 node. That fits beside the 64 GiB `--cache-ram`
budget (unchanged from the analytic half).

The earlier note's "fails 3%" applied to per-token write-through of the recurrent state. That remains ruled out. The
mirror is **KV write-through plus periodic recurrent checkpoint**, not write-through of everything.

## (2) Handover cost removed versus slot-file save (graphs-ON source rates)

The residual with a live mirror at handover is one fresh recurrent checkpoint (5.56 ms) plus at most k steps of KV tail
(< 0.7 MB, about 25 us). It is zero if the handover waits for the next periodic checkpoint and accepts the replay at restore.

| L | slot bytes | pure D2H at 28.20 GB/s | tmpfs save ms (removed) | disk save ms (removed) | `--cache-ram` save stall ms (removed) | own 3-rep range: tmpfs / disk / cache_save ms |
|---|---|---|---|---|---|---|
| 8000 | 435,646,768 | 15.4 ms | 135.9 (**130.3**) | 255.7 (**250.2**) | 111.0 (**105.4**) | 19.5 / 99.6 / 20.7 |
| 16000 | 714,398,768 | 25.3 ms | 223.9 (**218.4**) | 422.2 (**416.6**) | 160.5 (**155.0**) | 36.0 / 171.5 / 52.6 |
| 32000 | 1,271,902,768 | 45.1 ms | 400.7 (**395.1**) | 758.5 (**753.0**) | 189.2 (**183.6**) | 59.9 / 308.8 / 13.5 |

The slot-file save runs at 3.2 GB/s, which is **11.3-11.4% of the D2H link**. So about 89% of the save time is host-side
serialization (pageable staging plus file write), not PCIe. A mirror removes exactly that part from the handover path. The
durable copy to disk, if one is wanted, becomes a background write of host memory, off the GPU and off the slot's critical
path.

Restore side with a mirror: an H2D from pinned host memory at 28.89 GB/s takes 15.1 / 24.7 / 44.0 ms. That compares with
graphs-ON tmpfs restore at 50.8 / 84.1 / 174.6 ms, cold-disk restore at 111.0 / 181.3 / 335.6 ms, and `--cache-ram` load
stall at 77.9 / 55.1 / 83.2 ms. The draft model's state is not in either path and must be rebuilt in both, so it cancels
out of the comparison.

## (3) Read side: mapped-host gather (ROCm/mori UMBP pattern, MIT)

The pattern comes from intake-2140#record. UMBP's DRAMTier registers host memory with `hipHostRegister(Mapped|Portable)` and
takes a device alias with `hipHostGetDevicePointer`. A flat-grid HIP kernel (`GatherFragmentsKernel`, uint4 loads, up to 8
blocks per fragment) then pulls KV fragments into device buffers. Pageable regions fall back to hipMemcpy. Only portable
HIP calls are used, so it ports to gfx90a without a hardware change. On ROCm 6.2 it must be source-copied, because MORI
itself requires gfx942+ and ROCm >= 6.4.

- **Upper bound (ANALYTIC):** zero-copy reads from mapped host memory cross the same PCIe Gen4 x16 link, so the bound is the
  H2D plateau of **28.89 GB/s**. Scattered fragment reads land below it by an unmeasured factor (gather rate NOT COVERED
  in step 7, because no code exists).
- **As a restore path:** fine even at a pessimistic efficiency. At one third of the plateau (9.6 GB/s) it still matches the
  graphs-ON tmpfs restore (8.5-8.6 GB/s at 8k-16k). A bulk hipMemcpy from the pinned mirror at the plateau is always
  available as the fallback. The gather kernel is therefore an optimization for fragmented, `--kv-unified` cell layouts,
  not a precondition of the mirror.
- **As an in-place decode read (attention over host-resident KV every step): ruled out.** At L = 32k each slot needs
  1.115 GB per step, which is 38.6 ms per slot and 154 ms for four slots at the plateau. That is more than the whole
  139.6 ms spec-ON step, and 8k already costs 38.6 ms per step for four slots. The read side is restore-only.

## (4) HIP-graph-capture interaction (from the frozen v10 tree, read-only)

Facts, from `ggml/src/ggml-cuda/ggml-cuda.cu` @ production v10 `ffc1bac82`:
- One graph per `cgraph` key (`cgraph->nodes[0]`). `ggml_cuda_graph_update_required` compares node properties (data
  pointers, shapes, op params). A change resets warmup, and the step runs un-captured until two consecutive calls are
  identical (`ggml_cuda_graph_update_required` :2603, which records each node's src data pointers, ne and nb; `ggml_backend_cuda_graph_compute` :4171).
- Capture uses `cudaStreamBeginCapture(stream, cudaStreamCaptureModeRelaxed)` on the backend's single stream.

Consequences for a mirror:
1. **A D2H copy inside the captured graph** (a ggml copy op into a host buffer, or `hipMemcpyAsync` on the capture
   stream) **breaks graph reuse**. The destination address advances every step (it is the tail position), so node
   properties change every step and the graph never leaves warmup. Decode would run permanently un-captured. That is
   exactly the condition KPF-18-S1.7g says moves the numbers. A copy into pageable memory inside capture is not
   capturable at all.
2. **Graph-safe in-graph variant:** a `SET_ROWS`-style scatter whose destination is the mapped host alias (a stable
   pointer) and whose row indices sit in an index tensor. Data, not pointers, changes per step. This is how the KV append
   itself stays graph-compatible today. It needs a custom buffer type, so that the scheduler does not split the graph at a
   "host" buffer. It is the write-side mirror image of the UMBP gather. It is the preferred prototype design for the KV
   tail.
3. **Out-of-graph variant (design A'/B):** record an event after `cudaGraphLaunch` and issue the staged D2H or the D2D
   snapshot on a second stream that waits on that event. It must be issued from the host thread after the launch, never
   between `BeginCapture` and `EndCapture`. The host must poll the copy's completion (an event query), not synchronize on it
   in `post_decode`. GPU-ZOS-1a already measured `post_decode` at 4.15% of the spec-ON step (verdict OPEN, a one-step-lag
   async design). A blocking wait there would add to the host share that design is trying to remove. The two designs
   share the same "after the step event, on a side stream" slot and should be designed together.
4. The existing slot save/restore (`ggml_backend_tensor_get/set`, synchronous) runs between graph launches and does not
   change node properties, so a pinned mirror's bulk restore H2D does not force a re-capture either.

## Unmeasured, and why none blocks the trigger

| Rate | Status | Could it flip a trigger condition? |
|---|---|---|
| Small-copy D2H latency (< 1 MiB) | ANALYTIC 4.64 us (extrapolated) | No. At 3x the estimate (14 us), 128 copies are 1.8 ms: 1.3% ON, 3.0% OFF (OFF at the edge). The staged single copy is < 0.1% at any plausible latency (<= 50 us) |
| D2H concurrent with decode (overlap, HBM/PCIe contention) | not measured | No for design A' (charged fully serialized, already fits). Matters only for design B |
| gfx90a mapped-host gather rate | NOT COVERED (no code) | No. Restore-only, and the bulk pinned H2D fallback is measured (28.89 GB/s) |
| Handover frequency (the benefit side) | not judgeable (HSF-3.1: 0 keyed pairs) | Not a DI-140 condition. It sizes the value, not the trigger |

These are the prototype's first measurement, not prerequisites. Draft acceptance microbench for the prototype task
(scratch server, MI210, about 15 min, no model needed for steps 1-2):
1. `hipMemcpyAsync` D2H from a device buffer into a `hipHostRegister(Mapped)` buffer at 4 KiB, 64 KiB, 400 KiB, 1 MiB and
   157 MB, with 3 reps each (latency curve below 1 MiB).
2. The gather kernel source-copied from UMBP, compiled for gfx90a: fragment sizes 2,176 B x {1, 16, 512} contiguous
   tokens, reading from the mapped tier into device memory (GB/s versus the 28.89 plateau).
3. On the :8083 shape with graphs ON: an ABA comparison of decode ms/step with the mirror writer off / on / off (staged
   KV tail every step, recurrent checkpoint every k = 6 steps). The gate is a delta of at most 3% against the off arms'
   own spread. Report `graphs reused` counts in both arms, to prove the capture is not broken.

## Decision rule used

DI-140, verbatim: "trigger = the analytic write-through mirror costing finds the mirror fits the decode budget and
removes measurable handover cost". Two operational readings are **AUTHOR** choices:
- "fits the decode budget" = the serialized worst case is at most 3% of the measured GPU-ZOS-1a step, on both arms, for at
  least one implementable layout.
- "measurable" = the removed handover cost exceeds the measured 3-rep range of the save it replaces, at every L.

intake-2140#record's recommended action says "gated on a full-attention resident". **AUTHOR ruling:** the handoff's DI-140
text is the operative trigger (the intake shorthand predates the disposition). The concern that gate encodes is that
per-token recurrent write-through is too costly. The k-step checkpoint costing above answers that concern for the hybrid
27B. It remains a design constraint (KV write-through plus periodic recurrent checkpoint plus replay of at most k steps at
restore), not a block.

## Proposed prototype task text (for the owning session to file; DI-140 materializes)

**HSF-5.P — Host-pinned KV mirror prototype for the MI210 np4 slots (DI-140 fired 2026-10-24, intake-2140#record).** On a
fork `experimental/*` branch from current production: (a) a `hipHostRegister(Mapped)` host tier on the membind=3 node, about
14.3 GB, q8_0; (b) the KV tail write as a graph-safe scatter into the mapped alias, or a staged single D2H on a side stream
after the step event, with no copy inside the capture and no blocking wait in `post_decode`; (c) a recurrent checkpoint every
k = 6 steps per slot (design A'), with replay of at most k steps at restore; (d) restore by bulk pinned H2D, with the UMBP
`GatherFragmentsKernel` source-copied (MIT) for fragmented cells. Accept with the 3-step microbench in
`docs/design/hsf-5-host-kv-mirror-costing-20261024.md` (graphs ON, ABA, decode delta at most 3%, `graphs reused` unchanged,
restore greedy-equivalent to a slot-file restore). Value is bounded per handover (0.1-0.75 s). Design it together with the
GPU-ZOS-1a one-step-lag async slot.

## Data provenance

- KPF-18-S1.7g `/mnt/raid0/llm/tmp/f8-launchers-20261023/kpf18-s1-step7-graphs-on/VERDICT.json`
  9868e8bc4219e61f3045687bebd857b8ee65b1fda60772a02ff77927c515956d; `PREDECLARATION.md`
  79350337f0342562830a728bf8ca0448c9ae292d75cd7b12a612aa20221684d2.
- GPU-ZOS-1a `/mnt/raid0/llm/tmp/f8-launchers-20261023/gpu-zos-1a/VERDICT.json`
  ac752fadc06bc915143eef1148150edbed0c99a20de9478f613cf424de8b4298; `RUN_RECORD.json`
  04046189fa5b9d27df0d6afacfb63e8ec572c167c05d0106f6927c15d766eb63; `out/waves.jsonl` (tokens per step from
  `predicted_n` and `draft_n_accepted`).
- MI210 H2D/D2H receipt `epyc-inference-research/data/mi210-h2d-d2h/20260803T131500Z/{receipt.json,raw_unidirectional.txt}`.
- HSF-5 analytic half `/mnt/raid0/llm/tmp/analytics-20261020/HSF-5/REPORT.md`.
- Graph logic: `/mnt/raid0/llm/llama.cpp` (production v10, read-only) `ggml/src/ggml-cuda/ggml-cuda.cu`
  `ggml_cuda_graph_check_compability`, `ggml_backend_cuda_graph_compute`.
- Calculation script (not committed): `/mnt/raid0/llm/tmp/analytics-20261020/HSF-5/calc_20261024.py`
  sha256 89b26c5f0bd58c403b4f0e8dc992ef4ff6c42b9f6c97e812aaeaf0bc24881ea8.
