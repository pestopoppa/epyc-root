# DIVE-I — DELTA RECEIVED (base report NOT received; consolidation requested)
This is ONLY the agent's final-sweep delta. The underlying findings are pending re-emission.

## THE AGENT'S OWN CORRECTION TO A NUMBER IT QUOTED
It had cited the MMQ-dequant roofline gap as "~33% Q4_K, ~47% Q8" from handoff PROSE.
On a CONSISTENT GiB/GiB basis the corrected rungs are:
  **Q4_K 34% -> Q8_0 50% -> fp16 62.5%**
  (fable5-window2-findings-05-intake-sweep-and-roofline.md:58-59 — "the log's GiB-over-decimal-TB
   mixing slightly deflates the quantized rungs")
AND THE CEILING IS SOFT: the 62.5% fp16 figure was measured on **stock Qwen3-8B fp16, NOT our 27B**,
and is held at [H]. The gap is real but SMALLER than first stated, and its ceiling is NOT firmly established.

## q1 CORROBORATED FROM INSIDE OUR OWN REPO
The load-bearing claim — that gfx90a HAS direct-to-LDS and HipKittens' "async" is SOFTWARE PIPELINING —
is confirmed from our side. Our greenfield handoff already prescribes
`llvm.amdgcn.raw.buffer.load.lds` on gfx90a at **4 B/lane (1 dword/lane)**: a NARROW direct-to-LDS DMA,
not a CDNA3-class async BULK copy.
=> This RECONCILES the apparent contradiction with K28's categorical "NO async-copy/TMA/cp.async":
   **both are true at different granularities.** Anyone authoring must read BOTH.
Supporting precedent: `rocblas_gemvn_double_buffered_kernel` is explicitly `is_gfx90a`-gated in rocBLAS
=> proof that double-buffered GEMV is a real gfx90a win.

## TAXONOMY ADDITIONS — TWO SCHOOLS WERE UNDER-COVERED
School 4 (compiler DSL) was THINNER than reported. The index also holds:
- **intake-500 MLC LLM** (TVM Unity / Relax / TensorIR) — **the ONLY true multi-vendor compile target in
  the index**: CUDA, **ROCm**, Vulkan, Metal, WebGPU. The entry already names it "the natural authoring
  path for any custom AMD/Vulkan kernels we'd need on a non-NVIDIA GPU acquisition path."
  **A second option open to gfx90a that the agent had wrongly implied did not exist.**
- intake-458 FlashInfer — JIT template compiler, one operator family, CUDA-only, non-applicable.

**A SEVENTH SCHOOL MISSED ENTIRELY: quantization x kernel CO-DESIGN** — "design the format for the
datapath", distinct from all six. intake-818 ZipServ, intake-872 EXL3, intake-946/956 Escha W2,
intake-194 turboquant, intake-529/530/531 Sakana (TRAIN THE MODEL TO FIT THE KERNEL).
**Nearly all are explicitly ROCm-EXCLUDED**: ZipServ "not portable to MI210/gfx90a without full kernel
re-engineering"; EXL3 lists ROCm under "What's missing."
**This matters because our actual measured gap IS dequant — so this is the school CLOSEST to our
problem, and it has abandoned us as thoroughly as the vendor school.**

One scheduling entry sits on our exact ISA: **intake-309 Stream-K++ was tested on MI250X = gfx90a**,
built on Composable Kernel. Consistent with the finding that stream-K is already the live CDNA2 MMQ path.

## EXTERNAL CORROBORATION FOR THE MEASUREMENT-CONTRACT SECTION
**intake-939** (Meta/FAIR) independently states timing on the machines doing the work is unusable as a
ranking signal (41.2pp) and that correctness must be an OUTER GATE, never additive — precisely
P-AK-SEARCH-1's "no speed rank at all - not a penalised one" and its resource-claim preconditions.
**Stronger convergent evidence than QuixiCore's AGENTS.md, and from a source we already hold.**

## NEW gfx90a FACTS THAT SHARPEN THE CEILING
- **NO FP8 hardware** (confirmed from our own wiki, matching the LLVM `fp8-insts` finding). Also NO TF32/xf32.
- **1024 threads/block hardware cap — AND WE SHIPPED A VIOLATION**: the fork's ARGSORT launched
  2048 threads/block, an INVALID LAUNCH repeated **705x per synthesized utterance**. Fixed via
  thread-strided bitonic sort.
- Occupancy ceilings pinned: 32 waves/CU, 256 VGPR/thread. Q8-MMQ occupancy 2.61 vs bf16 3.22,
  register-pressure-limited.
- **NO MEASURED MI210 PEAK MATRIX TFLOPs EXISTS ANYWHERE IN THE REPO** — no achieved-vs-peak-FLOPs figure
  for any kernel, and nobody has done the spec arithmetic. The ridge point is explicitly OPEN.
  A real blank spot for any compute-bound claim.
- **Vulkan is ARCHITECTURALLY IMPOSSIBLE on CDNA2** (no ICD; RADV enumerates zero devices).
- rocBLAS GEMV is DENSE-ONLY => forces dequant-to-fp16 in HBM, 2-4x bytes moved. MMQ beat forced-rocBLAS
  at batch-1 as a **BYTES-MOVED gap, not a kernel-quality gap.**

## TWO DEPENDENCIES AFFECTING PROPOSED ACTIONABLES
- Actionable #4 (rerun HK's LDS bank/phase solver on gfx90a) is feasible, BUT `rocprofv2`/`rocprof`/
  `omniperf` were **ABSENT** as of 2026-07-20, rocprof v1 SQ/TA counters read ZERO on this box, and
  `rocm-bandwidth-test` is not installed. The LDS solver is TIMING-based so it should still run, but
  **C4 is blocked on TOOL AVAILABILITY as well as metric selection — a harder blocker than the handoff
  currently reflects.** (Independently corroborates DIVE-C's rocprof-not-installed finding.)
- **HIGHER-VALUE ITEM THAN SEVERAL LISTED**: /workspace/wiki/hardware-optimization.md:135-137 records
  that **the MI210 is attached to NUMA node 1, NOT node 3** — ground truth from sysfs, a premise that had
  been inherited and propagated UNCHECKED. The GPU lane's host threads at 184-191 are therefore
  **ALREADY CROSS-NODE, and device-local placement has NEVER been tried.**
  AutoKernel Sec 19.6 seed G1, flagged READY_EXISTING_PROTOCOL — except "that protocol was deleted from
  git and must be restored before the seed is executable."
  **Zero kernel work, potentially real throughput, and exactly the class of premise error this dive
  class exists to catch.**

## THE ONE GENUINELY OPEN KERNEL FRONTIER, WITH ITS CEILING
A fused chunked GDN recurrence kernel — "No CDNA2/ROCm-tuned GDN kernel exists ... genuinely open
territory (and a candidate upstream contribution)" — BUT BOUNDED: GDN is ~15% of GPU prefill wall-clock,
so a **4x op speedup buys ~11% full-model.**

## NET EFFECT (agent's own assessment)
Conclusions unchanged and slightly strengthened. The CDNA2-exclusion overturn is corroborated from two
independent directions. The "agentic generation is the only school left" conclusion GAINS one
alternative (MLC/TVM, ROCm-capable) and loses none. The honest ceiling is somewhat LOWER than stated,
and the compute-side roofline turns out to be UNMEASURED rather than merely unclosed.

## PROCESS
Nothing written or modified. All ledger items remain proposals. Item #9 (an Annex K stub) is another
session's IN-FLIGHT APPLY that the agent deliberately did not touch.
