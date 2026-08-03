# DIVE-I CONSOLIDATED — intake-944 QuixiCore + intake-947 HipKittens

## HEADLINE: the operator was right to overturn the decline — and for a SHARPER reason than expected.
**The Stage-1 finding that foreclosed HipKittens is WRONG ON ITS STATED MECHANISM.**
Stage 1 said gfx90a "lacks the CDNA3 asynchronous buffer-load machinery the primitives are built
around." Verified against source: **THERE IS NO SUCH MACHINERY.** `global_load_lds` has **ZERO
occurrences** in the entire HipKittens repo. Their "asynchronous loads" are ordinary
`global_load_dwordx4` into VGPRs with `s_waitcnt` DEFERRED, then `ds_write_b64` into LDS —
**software pipelining, available on gfx90a forever.** The paper's D.5 claim that direct global->LDS is
a CDNA3/4 feature is contradicted by LLVM (`FeatureVMemToLDSLoad` sits INSIDE `FeatureGFX9`) and by
our own repo (we already prescribe `llvm.amdgcn.raw.buffer.load.lds` on gfx90a at 4 B/lane). Their own
E.1 admits they don't use it on CDNA3 anyway.

**gfx90a is not technically incapable of the modern tile abstraction. IT IS COMMERCIALLY ABANDONED.**
That distinction is the whole planning consequence: nobody will port anything for us, so anything we
want on this card, we author — which is exactly what AutoKernel is for. The dive found NO alternative
school still standing on our silicon, which is a stronger result than finding one.

## THE DECOMPOSITION
NOT fundamental: tile types, LDS layout, coalesced loads, wave64 shuffles, buffer-resource addressing,
64 KB LDS budget, and the **bf16/fp16 MFMA core**. The two builtins HK's CDNA3 path uses are
`mfma_f32_16x16x16f16` (LLVM feature `mai-insts`) and `mfma_f32_16x16x16bf16_1k`
(**feature `gfx90a-insts` — literally named for our chip**).
**AND WE ALREADY HAVE THAT LAYER**: frozen v8 ships `ggml/src/ggml-cuda/mma.cuh` calling THOSE EXACT
TWO BUILTINS (:1051, :1250, :1286) plus int8 MFMA, with explicit CDNA1/2/3/4 branches.
**The gap to HK on bf16 is TUNING QUALITY, not capability.**
GENUINELY fundamental: fp8/fp6/fp4 and MX-scaled MFMA (`fp8-insts`/`gfx950-insts`) + gfx950 wide-K
shapes. **gfx90a has NO FP8 matrix core** (confirmed in our own wiki), no TF32/xf32. **100% of the
project's current momentum lives there.**
MOOT: chiplet swizzling (~7-19% on MI355X) — single-GCD MI210 has one fewer knob, not a loss.

## STAGE-1 STRUCTURAL CLAIMS: TWO OVERTURNED
- "There is no CDNA2 macro" — **FALSE.** `KITTENS_CDNA2` exists at `include/cdna3/common/util.cuh:518`
  and on the cdna3 branch at `common/util.cuh:126`, plus **13 build files** carrying
  `-DKITTENS_CDNA2 --offload-arch=gfx90a`.
- "gfx90a appears nowhere" — **FALSE.** gfx90a in **20 files**; CDNA2 in **14**.
- OPERATIVE FACT SURVIVES: `kittens.cuh` has no CDNA2 dispatch arm, so the flag includes NO headers;
  `kernels/common.mk` hard-errors on anything but CDNA3/CDNA4/UDNA1.
  **Restate as "a DANGLING BUILD ARM, not support."** MI210: 0 hits — confirmed.
- The tell: `MAX_SHARED_MEMORY` is IDENTICAL for CDNA2 and CDNA3 (65536) — gfx90a sits in the same
  64 KB LDS regime the design already has a working variant for.

## THE DECISIVE COUNTER-EVIDENCE AGAINST PORTING
Their Fig. 14, on **MI325X (CDNA3, ONE GENERATION BACK)**, is the only chart with just two arms — and
**HK LOSES AT 3 OF 5 GEMM SIZES**: N=4096 PyTorch 755 vs HK 752; N=8192 791 vs 755; N=16384 749 vs 716.
Paired with E.1 ("the hardware only has 65 KB of shared memory so we cannot double buffer in shared
memory... We do not use the direct HBM to LDS buffer loads"), **the design is ALREADY DEGRADING at
CDNA3.** MI210 is a further generation back and entirely untested.
**A port is buildable and would probably not be worth building.**

## SEVEN-SCHOOL TAXONOMY (the deliverable the operator asked for)
1 VENDOR KERNEL LIBRARY (AITER 307, hipBLASLt/Tensile 308, CK, rocWMMA 306) — **CLOSED**
2 HAND-WRITTEN ASSEMBLY (AITER ASM, FlashAttention-3 464, Flash-MoE 166) — **CLOSED** (no expertise/budget;
  FA-3 is Hopper-only BY CONSTRUCTION — the cleanest illustration of why this school never descends)
3 TILE DSL, C++-EMBEDDED (HipKittens 947, ThunderKittens) — **FORECLOSED BY CHOICE, NOT SILICON** (bf16 only)
4 COMPILER/AUTO-SCHEDULER DSL (Triton; TileLang 497 "currently limited to CDNA3"; **MLC LLM/TVM Unity 500**;
  FlashInfer 458 CUDA-only) — **OPEN: Triton YES, and MLC/TVM YES** — the ONLY true multi-vendor compile
  target in the index (CUDA/**ROCm**/Vulkan/Metal/WebGPU), already named in-index as "the natural
  authoring path for any custom AMD kernels". **A second option the first pass wrongly implied didn't exist.**
5 AGENTIC LLM KERNEL GENERATION (GEAK 674/677/678, Apex 675, AgentKernelArena 679, EvoEngineer 666,
  ShinkaEvolve 779, K-Search 673, KernelFoundry 669, Xe-Forge 672) — **OPEN. GEAK-v1 is the ONLY
  gfx90a-proven substrate** (paper evaluates on MI300X **and MI250 = gfx90a, our exact ISA target**).
  677/678/679 are gfx942-only — a coverage REGRESSION vs v1.
6 CONFORMANCE CONTRACT / EXECUTABLE SPEC (QuixiCore 944, intake-939, Afterburner 949, MultiKernelBench 667,
  robust-kbench 668, KernelBench 664/797) — **OPEN as method; kernels are not**
7 **QUANTIZATION x KERNEL CO-DESIGN** (ZipServ 818, EXL3 872, Escha 946/956, turboquant 194,
  Sakana 529/530/531, Effort Engine 528) — **A SEVENTH SCHOOL MISSED ENTIRELY.** "Design the format for
  the datapath", or train the model to fit the kernel. **ALMOST ENTIRELY CLOSED**: ZipServ "not portable
  to MI210/gfx90a without full kernel re-engineering"; EXL3 lists ROCm under "What's missing"; Escha
  closed CUDA sm_80-120; Sakana Hopper-only WGMMA/TMA.
  **THE PAINFUL ONE: our actual measured gap IS dequant, so the school CLOSEST to our problem has
  abandoned us as thoroughly as the vendor school.**
=> Schools 1,2,3,7 have all converged on CDNA3+ and abandoned CDNA2. **Only 4, 5, 6 are reachable — and
   AutoKernel already sits at the 4+5 intersection with 6 as its evaluator. The dive did not discover a
   new option; it CONFIRMED THE CHARTERED ONE IS THE ONLY ONE.**
HK's own best sentence, partitioning the port: "core tile and bulk compute interfaces carry over from
TK to HK, but decisions around memory access patterns, scheduling compute and memory, and ordering
thread blocks within the chiplet architecture differ."
On our exact ISA family: **intake-309 Stream-K++ (MI250X = gfx90a, on Composable Kernel)** and GEAK-v1.
CORPUS GAPS: Mojo, CuTe/CuTeDSL, ThunderKittens, Hidet, Ansor, DeepGEMM, AlphaEvolve, OpenEvolve have
NO standalone index entries.

## AITER MERGE: CONFIRMED — AND IT DOES NOT REACH gfx90a
PR **#2039** "Introduce HipKittens based nhead=128 MLA Kernel" **MERGED 2026-03-09T07:12:14Z** into main
by `ruanjm`, 23 files, **+3483/-480**. `csrc/include/mla_h k.h` carries AMD copyright 2025-2026 MIT.
11 files live on main today. `csrc/opus_gemm/include/gfx950/` cites "HipKittens XCD swizzle parameters"
and "the HipKittens split-barrier swizzle". PR body: **HK beats AMD's hand-written ASM by 5-20%** across
MI308/MI300 at nearly every batch x ctx cell.
=> the credibility_score 5 "+1 corroboration ... reportedly merging" is now **EARNED, not provisional**.
**BUT AITER's own Supported Hardware table**: MI300X/MI325X gfx942 fully supported; MI350/MI355X gfx950
supported; W7900/AI Max/R9700 RDNA3-4 **experimental**. **NO MI210, NO MI250, NO gfx90a — NOT EVEN
EXPERIMENTAL. Consumer RDNA parts are supported AHEAD of our datacenter card.**
The HK-derived kernels are mi35x/mi3xx and FP8 — doubly foreclosed.
**PROCUREMENT DATAPOINT, PLAINLY: AMD's centralized kernel library has DROPPED CDNA2. Single most
consequential fact in the dive.**

## THE TWO GGUF CLAIMS — BOTH **PARTIAL**, verified read-only against our tree
### A. E8M0 code 255 -> +Inf: mechanism CONFIRMED, "no special cases" FALSE TWICE, and it describes a
### function that is NEVER CALLED.
`ggml/src/ggml-impl.h:439-473`: code 0 IS special-cased (`bits = 0x00400000`); the 255->NaN branch is
PRESENT BUT COMMENTED OUT with the stated rationale "disabled as we don't need to handle NaNs".
**`GGML_E8M0_TO_FP32` has ZERO call sites in the entire tree.** Every CPU MXFP4 path uses
`ggml_e8m0_to_fp32_half` (:477) where (255-1)<<23 = 0x7F000000 = **2^127 ~ 1.70e38, FINITE** — not
+Inf, not NaN. ggml DOES special-case 255 — **at LOAD VALIDATION**: `validate_e_e8m0()`
(ggml-quants.c:5366-5372) rejects e==0xff as invalid row data, wired for MXFP4 at :5560, called from
llama-model-loader.cpp:1410,1555,1581,1643. A GGUF carrying 255 is REFUSED — treating 0xFF as reserved
exactly as OCP MX intends.
**THREE-WAY BACKEND DIVERGENCE, undisclosed by the claim**: CPU -> finite 2^127; Metal/SYCL/Vulkan/
OpenCL/**HIP** -> +Inf; CUDA >= 12.8 -> NaN. **On our MI210 HIP build CUDART_VERSION is undefined, so
we take the +Inf fallback** (ggml-cuda/common.cuh:816-822).
Agent self-corrected one intermediate step: QuixiCore's "code 0 decodes to 2^-127" does NOT contradict
its own vector — 0x00400000 = 5.8774717541114375e-39 = exactly 2^-127 (subnormal). **The irony: their
vector is right ONLY BECAUSE ggml has the special case their prose denies.**
### B. IQ2_XXS "four DEPENDENT random reads ... plus A sign-table read": "four" OK, "256-entry" OK,
### **"dependent" OVERTURNED**, "a sign-table read" **UNDERCOUNTS 4x**.
ggml-quants.c:2499-2510 — all four indices arrive in a **SINGLE 8-BYTE memcpy** (:2500). No address
depends on another lookup's result. **Four INDEPENDENT data-dependent gathers, ILP ~ 4 — not a pointer
chase.** `ksigns_iq2xs[...]` is INSIDE the l loop => **four** sign reads.
Ratio holds across every SIMD path incl. **our production iqk** (iqk_gemm_iquants.cpp:176-181 make4,
signs :86-90) 4+4, AVX2 4+4, CUDA 4+4 per 32.
CORRECT STATEMENT: *per 32 quantized weights, four INDEPENDENT data-dependent gathers into a
256-entry / 2 KiB grid, plus FOUR sign-table gathers, each grid entry expanding to 8 values.*
### PROVENANCE: the number attached to the claim BREAKS QUIXICORE'S OWN GATE
The spec's "measured on CDNA3 that is 1.07x ... against 3.4x for decode-at-load" traces to a ROCm
kernel README that actually says "**Measured in vLLM** at DeepSeek-V4 expert shapes (4096->2048,
32 experts, top-6) ... at **512 routed tokens**." One hop later the umbrella spec DROPS vLLM, DROPS the
shapes, DROPS the token count, re-attributes it to "CDNA3", and generalizes it to "a property of the
format, not of any one backend." Worse: commit `73e40a641b10` (2026-08-02) touched five files and
**NOT `perf/optimization_status.md`** — which their own AGENTS.md MANDATES for any performance claim.
**Their contract is well-designed and their most recent kernel commit bypassed it.**

## FREE INCIDENTAL FINDING IN OUR OWN TREE
`iqk_gemm_iquants.cpp` contains an AVX512-VPOPCNTDQ routine deriving IQ2 signs arithmetically with
**ZERO table reads** — but its dispatch at :184 is guarded by `#if defined z_HAVE_FANCY_SIMD && ...`.
**The `z_` prefix makes the macro undefinable, so the branch is PERMANENTLY DEAD** (same at :109, :571)
and the table lookup always runs — **including on our Zen 5 host, which HAS VPOPCNTDQ.**
Inherited verbatim from ik_llama.cpp via fec061dea; not introduced by us.

## MEASUREMENT-CONTRACT COMPARISON
THEY HAVE, WE DON'T:
1 "Do not claim a backend supports a kernel/dtype/quant/perf-tier unless the backend repo has
  correctness AND performance evidence" — a **CAPABILITY-CLAIM gate**, not a measurement gate.
  **Genuine gap; the one thing most worth importing.**
2 "'It got faster and I don't know why' is a reason to keep measuring, not to land" — a
  **MECHANISM-PLAUSIBILITY requirement** backed by bytes/FLOPs/counters. **Absent from P-AK-SEARCH-1**,
  which is purely statistical: pass the e-process, clear phi, publish MDE — and you may bank a candidate
  nobody can explain. Cheap to add; directly anti-reward-hacking (our C6).
3 "Rejected — with the reason, so they are not retried" as a first-class section + "Established Findings
  — Do Not Re-Derive". We have this INFORMALLY; not constitutional, not machine-checked.
4 **TEST-VECTOR-AS-CONTRACT** — committed edge-case vectors that "caught four backends decoding the same
  E8M0 byte three different ways at the edges. Nothing had compared them because nothing ran."
  **We have NO cross-backend numerical conformance vectors — and this dive found exactly that defect
  class LIVE in our tree (three answers for code 255 across seven backend sites). Strongest single import.**
WE HAVE, THEY DON'T: P-AK-SEARCH-1's calibration block (no literals), anytime-valid e-processes (LCB
FORBIDDEN as the ranking test), MDE published with the estimate, order-randomized interleaved paired
blocks (blocked designs FORBIDDEN — thermal/page-cache drift aliases onto the arm effect), anchor gate,
five controls incl. a degraded-negative that must get NO speed rank, immutable anchor by source commit +
binary SHA-256 + linkage SHA-256, evaluator bundle hash, codified recipe constructors, resource-claim and
host-health receipts, correctness lexicographically prior, human-only amendment boundary.
**QuixiCore has NO STATISTICAL TEST AT ALL** — median and p20/p80 against a fixed 3%/8-10% threshold.
**STRONGER CONVERGENT EVIDENCE ALREADY IN OUR INDEX: intake-939** (41.2pp, correctness as outer gate,
discretized > continuous) is precisely P-AK-SEARCH-1's design, arrived at independently, and is ALREADY
cross-referenced to autokernel-research-loop.md. intake-949 adds four-bucket B/M/W/F scoring.
**THE FINDING THAT MATTERS MOST IS ABOUT US: an unenforced measurement contract is decoration.**
`MEASUREMENT.md` Sec 2 lists P-AK-SEARCH-1 ratified 2026-08-03, but
`measurement/protocols/kernel-research.md` is **GIT-UNTRACKED** and holds ONLY a self-failing TODO token
("verification step G.4 fails while it is here"). Apply ran 08:30:05 UTC today => almost certainly
ANOTHER SESSION MID-APPLY and the guard working as designed. NOT TOUCHED. Flagged because untracked
looks identical to committed.

## HIPKITTENS MEASURED RESULTS (paper obtained, 41pp; all MI355X gfx950 unless noted)
Authors include **FOUR AMD EMPLOYEES**. **Zero mentions of gfx90a/MI210/MI250/CDNA2 anywhere.**
WHERE THE 1.2-2.4x COMES FROM — GQA BACKWARD d=128 (the flagship): seq 8192 causal SDPA 224 / CK 489 /
AITER 272 / **HK 933** (3.4x AITER); 8192 non-causal 309/463/384/**1155** (3.0x); 16384 causal
259/541/334/**995** (3.0x). d=64 attention: 4096 AITER 392 vs **HK 821**; 16384 633 vs **941**.
**WHERE AITER STILL WINS — the shapes AMD actually hand-tuned**: MHA backward d=128 causal AITER takes
**4 of 5** (8192: AITER 1034 vs HK 941); MHA forward d=128 causal AITER **4 of 5**; BF16 GEMM
hipBLASLt wins at 4096 and 16384, HK wins only at 8192 (1610 vs 1575).
ABLATIONS (the transferable science): **Tab.2 wave specialization is COUNTERPRODUCTIVE on AMD** —
4 producers/8 consumers = 893 TFLOPs vs **0 producers/8 consumers = 1610**, because "AMD hardware
STATICALLY DIVIDES REGISTERS across all waves, meaning producers consume registers without contributing
to output computation" (architectural, not gfx950-specific). **Tab.3 8-wave ping-pong is 4x cheaper in
code for ~90% of performance** (FP8 GEMM 48 LoC/3222 vs 183 LoC/3327). **Tab.5 LDS bank/phase behaviour
is UNDOCUMENTED in the CDNA ISA; they built a solver** (ds_read_b128 -> 64 banks/4 phases;
ds_read_b96 -> 32 banks/8 phases). Swizzle on the **HBM side, not the LDS side** — no single swizzle
serves both ds_write_b64 and ds_read_b128. **HIPCC WILL NOT FEED AGPRs to matrix-core instructions**
even though the hardware supports it, forcing redundant v_accvgpr_read.
FAIRNESS: better than typical — 500 warmup/100 timed uniformly; `hipblaslt-bench --rotating 512`
DEFEATS cache reuse (the HARDER setting); best-of-N baseline selection IN THE BASELINES' FAVOUR; pinned
upstream commits; AITER GEMM uses its TUNED entry point.
CAVEATS TO CARRY: **hipBLASLt is run WITHOUT any tuning/algo-search flag** while the NVIDIA baseline is
EXPLICITLY autotuned — an asymmetry that mildly flatters HK against AMD baselines. CDNA3 numbers come
from a DIFFERENT CONTAINER than CDNA4 numbers (MI325X panel not stack-comparable). **Correctness is ONE
SENTENCE, no table.** FP6 self-flagged preliminary. **No Limitations or Future Work section exists.**
NET: the abstract's range is REAL but carried by shapes where AMD's assembly coverage is ABSENT, not by
beating AMD where AMD tried. The paper is candid; a citation that isn't would be misleading.

## IMPLICATIONS FOR AUTOKERNEL
FORECLOSED: vendor library (permanently); HK as a component (right decision, WRONG original reason);
TileLang (CDNA3-limited); school 7 (nearly all ROCm-excluded); vLLM-ROCm (already in our
do-not-re-propose ledger as gfx90a arch-blocked); Vulkan (architecturally impossible, RADV enumerates
zero devices).
OPEN: agentic generation (GEAK-v1 = the only gfx90a-proven substrate; **its CURRENT README has narrowed
to "CDNA, e.g. gfx942/gfx950", so the gfx90a evidence is v1-era and AGEING**); MLC LLM/TVM Unity.
**THE FIRST SANITY GATE HAS BEEN OPEN SINCE 2026-06-03 AND IS STILL UNCHECKED**: "Reproduce GEAK-eval
on gfx90a MI210 — compile+correctness+timing round-trip". Everything downstream (controller A/B, C4, C6)
is blocked behind it.
CEILING, HONESTLY: our own campaign already concluded **GPU speed is structurally exhausted** on MI210
(both occupancy rewrites falsified, single-stream dense-Q8 done at +37%, aggregate solved by config).
**CORRECTED ROOFLINE RUNGS** (supersede the "~33%/~47%" prose): on a consistent GiB/GiB basis
**Q4_K 34% -> Q8_0 50% -> fp16 62.5%**, and **the ceiling is SOFT** — 62.5% was measured on **stock
Qwen3-8B fp16, NOT our 27B**, held at [H]. GDN L20 scoping 266 GB/s (~16%); bf16 recurrent-state raises
GDN VALUBusy 15.7%->56%, L2 hit 47.8->59.9%.
**THE COMPUTE ROOFLINE IS A BLANK SPOT: there is NO measured or quoted MI210 peak FP16/BF16 matrix
TFLOPs figure ANYWHERE in the repo, and no achieved-vs-peak-FLOPs percentage for any kernel.** Nobody
has done the spec arithmetic (1024 FLOP/cyc/CU fp16-MFMA x 104 CU x clock). Ridge point explicitly open;
in-repo guidance is "**Optimize wall-clock, not FLOP utilization.**"
ONE GENUINELY OPEN FRONTIER, BOUNDED: fused chunked GDN recurrence kernel — "No CDNA2/ROCm-tuned GDN
kernel exists ... genuinely open territory (and a candidate upstream contribution)" — but **GDN is ~15%
of GPU prefill wall-clock, so a 4x op speedup buys ~11% full-model.**
rocBLAS mechanistically ruled out for decode: GEMV is dense-only, forcing dequant-to-fp16 in HBM,
2-4x bytes moved. **MMQ beat forced-rocBLAS at batch-1 as a BYTES-MOVED gap, not a kernel-quality gap.**
HARD CONSTRAINTS an authoring loop must respect: **1024 threads/block — AND WE SHIPPED A VIOLATION**
(the fork's ARGSORT launched 2048/block, an INVALID LAUNCH repeated **705x per synthesized utterance**;
fixed via thread-strided bitonic sort, ARGSORT 46/46->74/74, TOP_K 170/170->292/292). 32 waves/CU;
256 VGPR/thread (Q8-MMQ occupancy 2.61 vs bf16 3.22, register-pressure-limited). Mixed q4_0/f16 KV is
UNSUPPORTED on the default HIP build; GGML_CUDA_FA_ALL_QUANTS=ON fixes mixed (415.31 t/s) but REGRESSES
homogeneous (489 -> 415/416) => "should not be treated as a blanket default."
TRANSFERABLE SCIENCE, FREE, APPLIES TODAY: (1) DO NOT WAVE-SPECIALIZE; (2) 8-wave ping-pong before
4-wave interleave; (3) LDS bank/phase must be SOLVED EMPIRICALLY — their answer doesn't transfer, THE
METHOD DOES; (4) swizzle HBM-side not LDS-side; (5) HIPCC won't feed AGPRs to MFMA — a live compiler tax
on gfx90a and exactly what C4 should learn to recognize; (6) chiplet swizzling is a non-issue for us.

## ENTRY DISPOSITIONS
- intake-947 -> **dive-verified**, TWO MATERIAL OVERTURNS (the CDNA2-macro/gfx90a-absence claims, and
  the stated foreclosure mechanism). verdict adopt_patterns STANDS — **on economics, not capability**.
  credibility 5 STANDS, now EARNED. Also CORRECT "CI unconfirmed" -> **CI CONFIRMED ABSENT** (.github 404s).
- intake-944 -> **dive-verified**; verdict worth_investigating STANDS; both GGUF claims downgraded to
  PARTIAL; ADD that `cdna2` is declared in FOUR MANIFESTS and implemented in ZERO FILES (0 hits for
  gfx90a/cdna2/mi210 across 1251 blobs, vs 469 cdna3 / 272 cdna4); ADD the gate violation; CONFIRM
  QuixiCore-ROCm is a HARD FORK of HipKittens (API parent/source), MIT; CPU backend unlicensed
  confirmed THREE ways.

## LEDGER: 13 drafts/flags, 3 declines
1 raise priority on the standing GEAK-eval gfx90a reproduction -> EXISTING task, attach rationale, argue MED->HIGH
2 **MI210 IS ON NUMA NODE 1, NOT NODE 3** (sysfs ground truth: /sys/class/drm/card2/device, 0x740f,
  numa_node=1). GPU host threads at 184-191 are ALREADY CROSS-NODE; device-local placement NEVER TRIED.
  **HIGHEST VALUE-PER-EFFORT IN THE LEDGER.** gpu-serving-tie-in-program.md P2-5j / AutoKernel 19.6 G1.
  BLOCKER: G1's protocol "was deleted from git and must be restored before the seed is executable."
3 record the corrected CDNA2 verdict so nobody re-derives "gfx90a lacks async buffer loads"
4 import the arch-independent HK scheduling lessons -> mi210-mfma-compute-bound-paths.md
5 rerun HK's LDS bank/phase SOLVER METHOD on gfx90a -> rocm-verify-profile-backend.md C4 (see row 12)
6 feed the corrected IQ2_XXS characterization into mi210-q8-dequant-gemv-roofline.md
7 investigate the DEAD z_HAVE_FANCY_SIMD AVX512-VPOPCNTDQ sign path -> EXPERIMENTAL BRANCH ONLY
8 cross-backend numerical conformance vectors -> **OPERATOR DECISION ITEM, not a task line** (a new
  instrument; instruments touch the measurement trust boundary)
9 two P-AK-SEARCH-1 amendments (mechanism-plausibility field; capability-claim rule) -> **HUMAN-ONLY
  amendment path; present as a decision package, do NOT draft into the annex**
10 confirm Annex K transcription before anything cites P-AK-SEARCH-1 -> **NOT MINE TO TOUCH**, in-flight
   from another session; flag to operator/coordinator only
11 add MLC LLM/TVM Unity (intake-500) to the AutoKernel backend-option set
12 **PROFILER TOOLING IS A BLOCKER**: rocprofv2/rocprof/omniperf ABSENT as of 2026-07-20; rocprof v1
   SQ/TA counters read ZERO and it aborts on graph builds; rocm-bandwidth-test not installed. Combined
   with "CDNA2 counter taxonomy unproven", **C4 is blocked on TOOL AVAILABILITY as well as metric
   selection.** Host action, not a sub-agent action.
13 correct the PCIe generation in our docs: gpu-acceleration-path.md:306 says PCIe 5.0; **the link is
   measured Gen4 x16**, and three mutually inconsistent figures circulate (~64 vs ~26 GB/s). H2D/D2H
   bandwidth remains unmeasured.
DECLINE 14 port HipKittens to gfx90a (buildable for bf16; negative EV)
DECLINE 15 adopt QuixiCore any backend (reaffirmed/strengthened) — adopt the METHOD not the code
DECLINE 16 pursue school-7 sources for gfx90a (closure documented so it is not re-derived)

## DIVE-SURFACED SOURCES
- ROCm/aiter PR #2039 + csrc/kernels/mla/hk/ — whether HK kernels ever reach gfx942 in opus_gemm
- **AITER Supported Hardware table — SETTLED: AMD dropped CDNA2 entirely. Strongest procurement signal.**
- hazyresearch.stanford.edu/blog/2025-11-09-amd-brr (2nd blog, UNREAD) — may carry TileLang/Mojo
  comparison detail the paper omits; a DISTINCT artifact per the companion rule
- GPU Mode lecture youtube.com/watch?v=jsYyF03Fs3o (Feb 2026) — author Q&A likely covers "why not older
  hardware" directly; cheapest way to settle intent vs capability
- AMD-AIG-AIMA/GEAK-agent current README — PARTLY SETTLED: now scoped "CDNA, e.g. gfx942/gfx950", no
  gfx90a. **This IS the freshness sweep agentic-rocm-kernel-authoring.md mandates at every audit.**
- intake-500 MLC LLM/TVM Unity — whether the ROCm backend compiles competitive gfx90a kernels
- intake-939 — already settled as convergent evidence for P-AK-SEARCH-1's design
- intake-309 Stream-K++ — MI250X = gfx90a, Composable Kernel
- QuixiCore/matrices/format-conformance.md + test-vectors/quant/*.json — the concrete artifact for
  actionable #8; ~4 JSON files, MIT
- QuixiCore-ROCm/perf/perf.md Sec 5,7,12,13 — rejection ledger + "Do Not Re-Derive" patterns
- llvm-project BuiltinsAMDGPU.td + AMDGPU.td — the authoritative arch-capability oracle; worth PINNING
  as the standing reference for any future "does gfx90a have X" question
- **NOT FETCHED, FLAGGED NOT DISMISSED: the QuixiAI org also holds a llama.cpp FORK and QuixiFlow
  (a vLLM fork). Given that our production kernel IS llama.cpp, that fork warrants a Stage-2b look.**
