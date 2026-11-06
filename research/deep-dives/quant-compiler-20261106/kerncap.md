---
entry: intake-2648 (proposed; intake-2647 is the current max in research/intake_index.yaml)
title: "Kerncap: Automated Kernel Extraction and Isolation for AMD GPUs"
arxiv_id: "2605.03208"
doi: "10.48550/arXiv.2605.03208"
source_url: "https://arxiv.org/abs/2605.03208"
source_revision: "arXiv:2605.03208v2 [cs.SE], submitted 2026-05-04, revised 2026-05-06 (HTML build 382,260 bytes; v1 == v2 byte-identical on fetch)"
local_copy: "/mnt/raid0/llm/tmp/dive-quant-compiler-20261106/raw/kerncap.html"
local_text: "/mnt/raid0/llm/tmp/dive-quant-compiler-20261106/raw/kerncap_paras.tsv"
sha256_html: "ec53fddaf064710abf5fc35e2457e010e4439f4914e23c43afbcc013f2b996fa"
sha256_paragraph_extraction: "f5b6ab85d163106e1c117e5da6feae5d72d76ff8435e956c4b6479c42608ca6a"
read_depth: "full-primary — abstract, §1–§8 and the full reference list read end to end in the arXiv HTML; all six result tables read cell by cell. No PDF fallback needed."
venue: "none stated at v2 (no journal-ref, no venue line, no artifact-evaluation statement; ACM-style ACM Reference block only)"
code_artifact: "yes — https://github.com/AMDResearch/intellikit, `kerncap/` subdirectory present (repo root listing verified 2026-11-06); repository-level licence file present, kerncap-scoped licence not read"
lane_worktree: "/mnt/raid0/llm/worktrees/intake-quant-compiler-20261106"
host_probe_date: "2026-11-06"
dive_author: "stage-2b analyst subagent"
---

# Kerncap — Stage-1 + Stage-2 dive

**One-line verdict.** Kerncap automates *exactly* the labour our autokernel loop pays for — turning one
kernel inside a large HIP/C++ application into an editable, recompileable, replayable single-file
project — and it is the only paper in this batch that evaluated **our kernel (`mul_mat_vec_q`), our
application (llama.cpp) and our GPU (MI210 / gfx90a)**. It is not a gate and must never become one
(no confinement, no anti-tamper, no reference oracle). Its capture path also **cannot run on this host
today**: it is built on `rocprofiler-sdk`, which is absent from ROCm 6.2.0-66 and which the paper only
validates on ROCm ≥ 7.0. Adopt the *pattern* immediately (it is free), gate the *tool* behind a ROCm 7
migration, and decline the headline 13.6×.

---

## 1. Stage-1 metadata

| Field | Value |
|---|---|
| Exact title | *Kerncap: Automated Kernel Extraction and Isolation for AMD GPUs* (`kerncap.html:302`) |
| Authors | Cole Ramos, Keith Lowery — both AMD, Austin, Texas (`kerncap.html:307`) |
| Date | Submitted 2026-05-04; v2 2026-05-06 |
| Categories | cs.SE only (no cs.DC / cs.PF / cs.MS cross-list) |
| Novelty | **medium-high** — the *components* all exist on NVIDIA (Nsight Compute kernel replay, CUPTI Checkpoint API, `rr`/CRIU), and Triton reproducers exist de facto via `TORCH_COMPILE_DEBUG` (the paper says so itself, `kerncap.html:2432`). Novel is the *combination on AMD*: HSA-level interception unified across HIP and Triton, and **address-space closure** — snapshotting the whole device address space at original VAs so `T**` pointer graphs survive with no DWARF and no pointer chasing (`kerncap.html:981`). The authors claim the combinatorial position is unoccupied by any open tool (`kerncap.html:2518`), and I found no counter-example. |
| Relevance | **high** — 1 of 6 eval workloads is llama.cpp; 1 of 3 GPUs is MI210 (gfx90a, CDNA2); the case-study kernel is `mul_mat_vec_q`, our decode hot kernel (`autokernel-loop.md:6495`). |
| Verdict | **adopt_patterns** (pattern + one numeric probe), with the tool itself **trigger-gated on ROCm ≥ 7.0** and the 13.6× claim **declined**. |
| Credibility score | **7 / 10** |

**Credibility rubric (my scoring, stated so it can be argued with).** Starting 10, deductions:
−1 no peer-reviewed venue, no journal-ref, no artefact-evaluation statement at v2; −1 headline
result is a **single** workload (llama.cpp) on a **single** GPU (gfx942) — §5.4 says so explicitly
(`kerncap.html:2184`); −1 the 13.6× is inflated by comparison choice (§2 claim 5 below); −0.5 Triton
reproducers validated on 2 of 3 architectures and RDNA scoped to HIP only, which the authors disclose
(`kerncap.html:2615`); +0.5 open artifact verified to exist; +0.5 numbers are internally consistent and
overhead is decomposed rather than asserted (§5.3); +0.5 every limitation I looked for is stated in §7.
Result: 7.

### key_claims (5)

1. **Unified HSA-level capture for HIP and Triton.** One `LD_PRELOAD` library (`libkerncap.so`)
   registers with `rocprofiler-sdk`, receives the live `HsaApiTable`, and hooks queue creation, the
   three memory-allocation families (pool, `hsa_memory_allocate`, VMEM) plus their frees, symbol
   lookup, and code-object load. Triton is bridged by a `sitecustomize.py` compile hook that writes
   `name_map.json` keyed by HSACO SHA-256 (`kerncap.html:783-905`).
2. **Address-space closure.** Every tracked device allocation is captured at its original virtual
   address and restored at that exact address via `hsa_amd_vmem_address_reserve`; replay **aborts** if
   the reserve returns a different VA (`kerncap.html:1420`). Embedded pointers therefore survive
   without DWARF or pointer chasing — demonstrated on vLLM's MoE pool reached through indirection:
   186 regions, 29,301 MB on gfx90a (`kerncap.html:1745`).
3. **Six workloads × three architectures, 152 MB → 30 GB snapshots**, HIP + Triton + torch.compile
   (`kerncap.html:343`, Table 1 `:1574`).
4. **llama.cpp case study: 13.6× end-to-end**, 162 s vs ~2,208 s; inner-loop (edit-recompile-replay)
   5.4×, 136 s → 25 s, with the single-TU recompile at 18.3 s vs 128 s for a full CMake rebuild
   (`kerncap.html:2206-2262`, `:2357`). The kernel edit itself was worth **1.22×** on the kernel
   (34.5 µs → 28.3 µs).
5. **Interception is nearly free; capture is bandwidth-bound.** Interception-only overhead 1.06× on
   llama.cpp/gfx942 and 1.15× on gfx90a; llama-bench `tg32` 251 vs 254 baseline (inside noise) with
   interception only, vs 195 under full capture and 158 under `rocprofv3 --kernel-trace`
   (`kerncap.html:2002-2015`, `:2113-2128`). Capture throughput ≈ 1.7 GB/s.

### techniques

HSA API-table interposition via `rocprofiler-sdk` registration · AQL packet callback with **completion-
signal substitution** (swap the packet's signal, block, snapshot after the kernel retires, then decrement
the original) · address-space-closure memory capture in 64 MiB chunks (`KERNCAP_SNAPSHOT_CHUNK_BYTES`) ·
module-variable (`__constant__`) capture and per-executable SHA-256 disambiguation · source discovery by
`compile_commands.json` + DWARF line tables + `nm` symbol disambiguation with a two-pass grep fallback ·
Clang **VFS overlay** (`-ivfsoverlay vfs.yaml --cuda-device-only --no-gpu-bundle-output`) to recompile one
file with the exact original flags · Triton **tuning-pinned** reproducers (autotuner config bound into the
artifact) · three-mode validation (smoke, byte-exact region diff, `numpy.allclose` with NaN detection).

### reported_results

| Workload | Arch | Regions | Snapshot | `extract` wall |
|---|---|---|---|---|
| llama.cpp (`mul_mat_vec_q`) | gfx942 | 21 | 12,233 MB | 15.6 s |
| llama.cpp | **gfx90a** | 21 | 12,126 MB | **20.9 s** |
| llama.cpp | gfx1100 | 20 | 11,520 MB | 18.8 s |
| vLLM (`fused_moe_kernel`) | gfx90a | 186 | 29,301 MB | 85.2 s |
| LAMMPS (Kokkos) | gfx90a | 84 | 8,421 MB | 28.2 s |
| rocBLAS GEMM (Tensile) | gfx90a | 10 | 152 MB | 11.2 s |
| FlashAttention-2 (Triton) | gfx90a | 13 | 178 MB | 13.2 s |
| torch.compile (Inductor) | gfx90a | 12 | 227 MB | 13.5 s |

(`kerncap.html:1669-1759`; Triton rows exist on gfx942 and gfx90a only, `:1762`.)
Payload: llama.cpp recompile-with-no-edit produces **byte-identical output across all 21 regions on all
three architectures** (`:1785`); Triton workloads validate at `max_error = 0.0` (`:1827`); `mul_mat_vec_q`
optimised 34.5 → 28.3 µs (1.22×) in 5 edit-recompile-validate iterations (`:2293-2370`).

### limitations (all author-stated, §7)

One dispatch at a time, no inter-kernel dependency or stream tracking (`:2536`) · single GPU (`:2549`) ·
a buffer freed between kernel completion and snapshot is lost (`:2558`) · **no host-side state** — CPU
memory, file handles, host-mapped buffers (`:2569`) · HIP source discovery degrades without
`compile_commands.json`; computed/macro include paths unsupported (`:2579`) · portability-layer kernels
give you the *framework template expansion*, not your functor (`:2590`) · Triton autotuner configs are
hardware-specific (`:2604`) · RDNA scoped to the three HIP workloads (`:2615`).

Two limitations the authors do **not** state, which matter to us: **(a)** the replay pipeline is
"validated … on ROCm ≥ 7.0, where the rocprofiler-sdk interception framework is stable"
(`:1455`) — that is the whole capture substrate; **(b)** nothing in the tool is adversarial. There is no
confinement, no process isolation, no tamper detection, and the correctness oracle is *identity to the
captured run*, not correctness against a reference. A candidate that is identically wrong passes.

---

## 2. Per-claim adjudication

Locators are `raw/kerncap.html:LINE` (the paragraph-extraction line map in `kerncap_paras.tsv` maps 1:1).
`quote_sha256` is SHA-256 over the quoted string, UTF-8, whitespace-collapsed, no trailing newline.
**Normalisation note:** the LaTeXML build duplicates math tokens (`13.6 × 13.6\times`, `1.22 ×
1.22\times`). Quotes below are normalised to the single, mathematically correct occurrence, matching the
PDF reading; the hash is over the normalised string as printed. `sha256_html` is over the raw fetched
bytes and is the authoritative identity.

| # | Claim | Verdict | Locator | Verbatim quote | quote_sha256 |
|---|---|---|---|---|---|
| 1 | A single HSA-level interposer captures both HIP and Triton dispatches, with a Python compile-hook shim supplying Triton's JIT-only metadata | **CONFIRMED** | `:67-68`, mechanism `:872-905` | "We present Kerncap, an automated kernel extraction tool that intercepts dispatches at the HSA runtime for both HIP and Triton, bridging Triton's JIT-only metadata into HSA-level capture via a lightweight Python compile-hook shim." | `22e8dac3e4c5bc101c39f5d79dc9e712b546f1b4dd3ceda92337564a1aa2b061` |
| 2 | Six real HIP+Triton workloads, three AMD architectures, 152 MB–30 GB, including a VA-faithful vLLM MoE capture reached through pointer indirection | **CONFIRMED** | `:69`, tables `:1669-1759` | "Across six real-world HIP and Triton workloads spanning traditional HPC and ML domains on three AMD GPU architectures (CDNA2, CDNA3, RDNA3), Kerncap extracts and validates kernels from snapshots ranging from 152 MB to 30 GB—including a VA-faithful capture of vLLM's Mixture-of-Experts weight pool reached through pointer indirection." | `f3fa28c7b5d9a164325092f753852b0744f06a837bf7db9f4b5a8ea866149ffe` |
| 3 | llama.cpp case study: 13.6× edit-recompile-validate vs the traditional workflow, multi-hour → one command | **PARTIAL** — the 13.6× is arithmetically correct (2,208/162) but is **dominated by replacing a 2,072 s `rocprof-compute` counter run with a 129.4 s byte-exact replay**; the developer-productivity number is the 5.4× inner loop | `:69`, decomposition `:2269`, `:2357`, `:2361` | "On our llama.cpp case study, Kerncap's edit-recompile-validate loop achieves a 13.6× speedup over the traditional workflow, reducing kernel isolation from a multi-hour process to a single command." | `76020aa8771179f6b1d32b60a812bdb807697770705032c8be5708eb4a28f660` |
| 4 | MI210 / gfx90a / CDNA2 is in scope | **CONFIRMED** | `:1564`, Table 2 `:1686-1689` | "We evaluate Kerncap across three AMD GPU architectures spanning AMD's data-center (CDNA) and consumer (RDNA) GPU families: AMD Instinct™ MI300X (gfx942, CDNA3), AMD Instinct™ MI210 (gfx90a, CDNA2), and AMD Radeon™ PRO W7900 (gfx1100, RDNA3)." | `1417751dcc8be573930551dc5e605b2e100e7d6289a04cb04d6e6bb63e8fbbef` |
| 5 | Interception does not perturb steady-state compute | **CONFIRMED for their host, not ours** — `tg32` 251 vs 254 is inside their own ±29/±7 sd; measured on gfx942 only | `:2128`, table `:2113-2123` | "Interception-only preserves tg32 within noise (251 vs. baseline 254), confirming that the per-dispatch callback mechanism does not degrade steady-state compute." | `cf061ac424e1361e9c6100485cc5a3fbad1885a7142638417ac6af0c6f3af361` |
| 6 | Single-translation-unit recompile is 7× cheaper than a full CMake rebuild | **CONFIRMED** | `:2325` | "make recompile rebuilds the single HSACO in 18.3 seconds (vs. 128 seconds for a full llama.cpp CMake rebuild)." | `a03d61d2194d413cce370347c5e615bc7dc6c3c8fd6174e4fdc533a69f0fd163` |
| 7 | One kernel dispatch at a time; no inter-kernel dependencies or stream synchronisation | **CONFIRMED** | `:2536` | "Kerncap captures one kernel dispatch at a time. It does not track inter-kernel data dependencies or stream synchronization, so kernels that depend on the output of preceding kernels require those predecessors to have already executed before the capture point." | `653b1721d36a79100a21dab1acd6a9a54ff26d7f543d1bb03d475d86fe5b2c84` |
| 8 | Address-space closure removes the need for DWARF/pointer chasing on indirect arguments | **CONFIRMED**, with three stated failure modes (host-resident pointers, ASLR'd host pointers, kernel-time pointer arithmetic that escapes the tracked set, `:998`) | `:981` | "An address space is a closure over its pointer graph: by capturing every tracked GPU allocation at its original virtual address, the embedded pointer relationships (e.g., T** arguments) are preserved for free, without DWARF metadata or pointer chasing." | `988c18a9437a147641700497af698f316ef8dfc7d6670c5931f1126ecff4e628` |

**Why claim 3 is PARTIAL and not CONFIRMED.** 2,208 s = 2,072 s of `rocprof-compute` counter collection
plus a 136 s inner loop (`:453`, `:461`). Kerncap's 162 s = 25 s inner loop + 129.4 s byte-exact replay.
The 13.6× therefore prices *"validate by collecting hardware counters on the full app"* against
*"validate by replaying one kernel"*. Those are not the same task, and **our gate does not run
`rocprof-compute` for validation** — it runs `test-backend-ops` plus paired `llama-bench`/`ab_probe`
timing against a floor (`kernel-champion-and-promotion.md:666`, `:601`). If I substitute our validation
step into their arithmetic, the comparison collapses toward their own 5.4× (and the 5.4× is the number
their Table 6 actually supports, `:2262`).

---

## 3. MECHANISM — what it extracts, how it isolates, what it measures, what it costs

**What is extracted.** One *kernel dispatch*. Not a kernel family, not a sequence, not a module
(`:2536`). The artifact is a directory:

```
isolated/mul_mat_vec_q/
  capture/  dispatch.json  kernarg.bin  kernel.hsaco  memory_regions.json
            memory/region_<va>.bin ...            (all tracked device allocations, VA-faithful)
  kernel_variant.cpp                              (the editable TU)
  deps/     <flattened headers, collision-safe>
  vfs.yaml                                        (Clang VFS overlay: local copy -> original path)
  Makefile                                        (run | recompile | run-variant | validate-variant)
```
(`kerncap.html:1207-1318`)

**How it isolates.** Four independent recoveries, each solving one of the paper's "three components of a
reproducer" (`:385`):

1. *Definition* — the exact HSACO blob is intercepted as it loads (`hsa_code_object_reader_create_from_memory`,
   `hsa_executable_load_agent_code_object`), and the source TU is found by `compile_commands.json` +
   `nm` on the object files + DWARF line tables, with `nm` disambiguating template-instance files —
   **the paper names `llama.cpp`'s `mmq-instance-*.cu` as the canonical case** (`:1131`).
2. *Runtime state* — the address-space closure above, plus the kernarg buffer captured at its exact
   `HSA_EXECUTABLE_SYMBOL_INFO_KERNEL_KERNARG_SEGMENT_SIZE` (`:971`), plus `__constant__` module
   variables (`:1018`).
3. *Environment* — the VFS overlay re-runs the **exact** original compiler command with three extra
   flags, so no build system is touched and no flag is reconstructed by hand (`:1303`).
4. *Replay* — a standalone HSA binary that pre-`mmap`s each VA range with `MAP_FIXED_NOREPLACE` before
   `hsa_init()` so the SVM aperture cannot claim it, then `munmap`s and re-reserves with
   `hsa_amd_vmem_address_reserve` at the captured base (`:1399-1430`).

**No source access required for capture.** Capture needs only the binary + runtime. Source discovery is a
*separate*, degradable stage: when no source is recoverable (Tensile codegen, Inductor JIT) the tool emits
HSACO-only reproducers that still replay and validate bit-exactly — the edit loop is simply unavailable
(`:1806`). **No binary rewriting** anywhere. **Runtime tracing is mandatory** (`LD_PRELOAD` interposer).
Source access is optional but determines whether the *edit* half of the loop exists.

**What it measures.** Not throughput in the first instance: its primary measurement is **fidelity** —
byte-exact comparison of every output region between the captured baseline HSACO and a variant HSACO
(`:1485`), or `numpy.allclose` with NaN detection for Triton (`:1497`). Timing exists but is secondary:
`kerncap replay --iterations N` with optional `--no-recopy` between iterations for stateful measurement
(`:1447`), and the case study reports mean kernel time over 10 iterations (`:2309`). **It is not a
benchmarking harness** — no floor, no pairing, no counterbalancing, no dispersion reporting.

**Cost per extraction.** Wall-clock, end-to-end (`extract` includes reproducer assembly): **9–21 s for the
five sub-200 MB-few-GB workloads, 15.6–20.9 s for llama.cpp's 12 GB, 60.9–85.2 s for vLLM's 30 GB**
(Table 2). Decomposed: interception ≈ 1.04–1.18× the base app, capture ≈ snapshot ÷ ~1.7 GB/s
(7.0 s for 12 GB on gfx942; 13.0 s on gfx90a), remainder = source discovery + assembly (Table 3/4). The
cost is **one-time and fixed**, independent of kernel count or app duration (`:2079`).

**Failure/abort behaviour worth noting for us.** `capture_complete` sentinel + watchdog that
`SIGTERM`/`SIGKILL`s the *child process group* the moment serialisation finishes (`:937`) — which is why
vLLM's "full capture" (60.8 s) is *shorter* than its 163.8 s baseline. Metadata is written before the
D2H copies so a failed region copy loses only that region (`:1045`). Replay aborts loudly on VA mismatch
rather than corrupting (`:1455`).

---

## 4. AMD SCOPE — the question that decides everything for us

| Axis | Answer | Evidence |
|---|---|---|
| GPUs | MI300X (gfx942, CDNA3), **MI210 (gfx90a, CDNA2)**, Radeon PRO W7900 (gfx1100, RDNA3) | `:1564` |
| **gfx90a / MI210** | **In scope and fully measured** — **6 of 6** workloads have gfx90a cells (Triton rows exist on gfx942+gfx90a, i.e. gfx1100 covers HIP only); llama.cpp: 21 regions / 12,126 MB / 20.9 s | Table 2 `:1686-1759`, `:1762` |
| Stack | ROCm 7.2.0 on RHEL 9.6; XNACK state not stated | `:1564` |
| Min ROCm | **7.0** — "validated the replay pipeline on ROCm ≥ 7.0, where the rocprofiler-sdk interception framework is stable" | `:1455` |
| Frameworks | llama.cpp (HIP), LAMMPS/Kokkos (HIP), rocBLAS/Tensile (HIP), FlashAttention-2 (Triton), vLLM (Triton), torch.compile/Inductor (Triton) | Table 1 `:1574` |
| PyTorch | Yes, as a *host*: Triton metadata (dtype/strides) comes from PyTorch tensors, and the shim is proven to propagate into vLLM's `EngineCore` workers via `multiprocessing.spawn` | `:890` |
| SGLang | **Not tested.** No mention anywhere in the paper. The mechanism (Triton → HSA) should generalise; untested is untested. | full text |
| **HIP C++ (our case)** | **Yes — this is the primary path.** llama.cpp's `mul_mat_vec_q` is hand-written HIP C++ in `mmvq.cu`, built by CMake, and it is the paper's case study | `:1579-1594` |
| Triton/compiler-generated only? | **No.** HIP is the *better-supported* path: source-level recompile via VFS; Triton gets the weaker tuning-pinned Python replay (no source recompile in the C++ sense) | `:1275` vs `:1360` |
| Wavefront width | Explicitly arch-agnostic: gfx1100 replays correctly at wave32 (`Block: 32×1×1`) vs wave64 32×2 on CDNA | `:1785` |
| Multi-GPU | Not supported | `:2549` |

**The host fact that gates us (probe, 2026-11-06).** This box reports `6.2.0-66` and
`/opt/rocm/lib` contains `librocprofiler-register.so*` but **no `librocprofiler-sdk`**. Kerncap's
interception is built on `rocprofiler-sdk`'s `rocprofiler_at_intercept_table_registration` (`:783`).
So the tool is **not runnable here as shipped**, and the blocker is not a build flag — it is a ROCm
major-version migration on a host whose frozen kernels carry load-bearing ROCm 6.2 / gfx90a patches
(`CLAUDE.md:41,49`). That is a stack decision, not a kernel experiment.

Secondary capacity check: our 27B Q8_0 model is ~29 GB of weights; a full address-space closure of a
`-ngl 99` llama-bench run on a 64 GB MI210 would snapshot on the order of 30 GB, i.e. ≈18 s of capture
at the paper's 1.7 GB/s and a 30 GB host-side artifact — inside the card, but only just, and
`KERNCAP_SNAPSHOT_CHUNK_BYTES` chunking is what keeps host RAM bounded (`:959`).

---

## 5. WHAT IT WOULD CHANGE FOR US

### What we actually do today

| Fact about our loop | Locator |
|---|---|
| Candidate = a source edit to `llama.cpp-experimental`; C2/C6 work lands in that tree "and in the harness that drives it" | `rocm-kernel-authoring.md:13` |
| Tiering: T0 correctness/build (fresh clean build from a content-addressed snapshot, **never the actor's incremental tree**) → T1 search (microbench, paired blocks) → T2 lineage → T3 freeze | `autokernel-loop.md:2166-2167`, `:2298-2306` |
| Per-iteration cost, **median 2,675 s = build 2,025 (75.7%) · planner 412 · critic 100 · measured 105 (3.9%)** | `autokernel-loop.md:6667` |
| Lifetime compiling **29.0 h**, and **`-j 1` in 77/77 build logs on a 192-thread host** | `autokernel-loop.md:6666` |
| Our decode target kernel is `mul_mat_vec_q`, "entirely our source" | `autokernel-loop.md:6495` |
| We already have a native oracle/candidate harness (`c6_mul_mat_harness.cpp`, oracle + 3 candidate legs as confined processes under one held claim) | `autokernel-loop.md:56-58` |
| We already have a HIP launch-capture shim planned for the race verifier, "launch grid, workgroup size and kernarg from a small HIP launch-capture shim" | `rocm-kernel-authoring.md:1729` |
| We already plan to hand-build "a standalone harness (1-2 weeks)" for the GCN-Gym ISA rung, with `hipModuleLoad` replay of served-shape launches | `rocm-kernel-authoring.md:2996` |
| Gate currency: paired relative difference, floor = max(2.00 %, P-vs-P spread); no claim survives inside the floor | `kernel-champion-and-promotion.md:666`, `:601` |

### The verdict, in four parts

**(a) It is solving our problem, not a different one.** The framing — "a kernel is not a
self-contained artifact; you must recover definition, runtime state and environment"
(`kerncap.html:379-385`) — is a precise description of why our T1 lane is expensive, and llama.cpp is
its proof case. This is not "extraction from a serving framework" in the abstract; it is extraction
from *our* codebase class.

**(b) It would **not** replace the C6/native harness, and must not.** C6 is a *trust boundary*: sealed
oracle and candidate legs as distinct confined processes, one held claim, digest-bound witness handover,
anti-tamper, no actor-writable path (`autokernel-loop.md:56-65`). Kerncap has none of that, and its
correctness oracle is identity-to-capture, not correctness-to-reference. Inserting it as a gate would
*weaken* T0 while looking like it strengthened it. It is a **fixture generator and an inner-loop
accelerator that runs inside the sandbox**, nothing more.

**(c) It would reduce per-iteration setup cost — but less than the headline implies, and not first.**
Their honest number is 5.4× on the inner loop (136 → 25 s) and 7× on the rebuild step (128 → 18.3 s).
Our 75.7 % build share is **not** the same 128 s: our logs show `-j 1` in 77/77 builds on a 192-thread
host (`autokernel-loop.md:6666`), so an unknown but large fraction of our 2,025 s is a harness defect
that Kerncap would faithfully accelerate instead of fixing. **Order of operations: fix parallel build
and instrument build seconds first (AK-HR-3b, filed 2026-10-20), then measure what Kerncap's
single-TU path adds on top.** Otherwise we would be buying a 7× on a number that is 10× too big for
reasons of our own making.

**(d) Two places where it is a genuine substitute for work we have already scheduled.** Both are
one-to-two-week hand-builds in the lane:
- the **RVP-RACE-2 launch-capture shim** (`rocm-kernel-authoring.md:1729`) — Kerncap produces exactly
  `dispatch.json` + kernarg + captured inputs for a served-shape launch;
- the **C5-ISA-2 standalone harness** (`rocm-kernel-authoring.md:2996`) — Kerncap's HSACO-only path plus
  `--hsaco` variant replay is a ready-made harness for hand-written `.co` kernels loaded via
  `hipModuleLoad`, which is precisely the AK-GFX90A-ASM-SURFACE tier (`autokernel-loop.md:5617`).

That is the real prize: not the 13.6×, but **deleting two bespoke harnesses** and getting VA-faithful
real-input fixtures for the asm tier for free.

**Does it help with the frozen-build identity constraint?** Neutrally-to-positively. Capture is
`LD_PRELOAD` on a process we already run, so the frozen tree is untouched (`CLAUDE.md:49`); and because
the reproducer binds the HSACO by content, it composes with our "a build path does not identify the
binary" rule (`CLAUDE.md:132`) better than a mtime-based harness would. But the reproducer's own
recompiled HSACO is **not** a sealed build, so it can never carry a promotion claim.

---

## 6. Comparison with KREX (already dived — `research/deep-dives/quant-compiler-20261106/krex.md`)

| Axis | KREX (intake-2647) | Kerncap (this) |
|---|---|---|
| Problem named | GPU *capacity* wasted by command-granular exclusivity; contention corrupts measurement | *Setup* cost of isolating one kernel from a large app; rebuild + full-app rerun |
| Unit of work | A timing-sensitive **region** inside a command | A **single kernel dispatch** |
| Mechanism | Submit-block + drain + sibling freeze + CPU-slice; region lock | HSA interposer + VA-faithful snapshot + VFS single-TU recompile |
| Host blocker on gfx90a | Freezing process trees we do not own (forbidden) | `rocprofiler-sdk` absent on ROCm 6.2 |
| gfx90a evidence | **None** (MI308X = gfx942 only) | **Full** (all 6 workloads measured on gfx90a) |
| Transferable value to us | Region-scoped grants (KX-1) + floor discipline (KX-2) | Fixture generation + single-TU rebuild; two harnesses deleted |
| Headline number's honesty | 3.4× is real but 78 % is off-region concurrency; AMD arm disables pooling | 13.6× is inflated by comparing to a 2,072 s counter run; 5.4× is the honest number |

**Overlap.** Both are "the cost of getting a trustworthy measurement" papers, and both propose
infrastructure rather than a kernel. Both were evaluated with llama.cpp in the loop (KREX replays agent
commands, Kerncap extracts `mul_mat_vec_q`).

**Complement — and this is the important structural point.** The two papers disagree about *where* the
cost is, and our lane's own numbers settle the disagreement **in Kerncap's favour**: our iteration is
75.7 % build / 3.9 % measured (`autokernel-loop.md:6667`), and the GPU is already exclusive by grant
(`krex.md` §E: "Within a grant there is no co-tenant to drain, so mechanism (1) buys exactly nothing
today"). KREX's premise is unproven here and its own dive says so; Kerncap's premise is directly
measured in our journal. If we spend effort on measurement infrastructure this quarter, it belongs to
setup cost, not contention.

**Conflict — one, and it is manageable.** KREX's KX-1 wants timing rows to *release* `mi210_0` between
regions. A Kerncap replay is a tight, latency-sensitive single-kernel loop (34.5 µs kernel, 10
iterations) that wants the device for its whole duration, and its capture wants the full device
address space at one instant. Both are satisfiable — capture is one-shot and replay declares its own
region — but it means **Kerncap's replay is a region-holder under KX-1's model**, not an exception to
it. Recording that now prevents a future collision.

**No conflict on region-granular exclusivity itself.** Kerncap does not touch scheduling, co-tenancy,
or fidelity statistics; its validation is byte-exact, which is orthogonal to KREX's p95 inflation
question and immune to it (a 3.9 % timing tail cannot corrupt a byte comparison).

---

## 7. Derived-actionables ledger

| ID | Action | Owning lane handoff | Disposition |
|---|---|---|---|
| **KC-1** | **ROCm 7.0 availability gate.** Kerncap's capture substrate is `rocprofiler-sdk`; this host is `6.2.0-66` with no `librocprofiler-sdk`. Record that no Kerncap trial is possible until a ROCm ≥ 7.0 migration is authorised, and that the migration is a stack decision (frozen kernels carry ROCm 6.2/gfx90a patches), not a kernel experiment. | `rocm-kernel-authoring.md` (probe) + the stack/freeze lane for the decision | **TRIGGER** — on ROCm ≥ 7.0 landing on the host. Not an open item; it is a precondition with a named owner. |
| **KC-2** | **Fix the build-cost defect before buying a build accelerator.** `-j 1` in 77/77 build logs on a 192-thread host (`autokernel-loop.md:6666`); build is 75.7 % of a 2,675 s iteration. Instrument build seconds (AK-HR-3b already filed, `:5741`) and parallelise; only then is Kerncap's 7× single-TU number meaningful. | `autokernel-loop.md` (AK-HR-3b / rebuild program) | **IMMEDIATE** — zero GPU, highest expected value in this dive. |
| **KC-3** | **Probe the one transferable kernel win: hoist the runtime `use_gate` branch out of `mul_mat_vec_q`'s inner accumulation loop + force dot-product inlining.** Their measured effect: 34.5 → 28.3 µs, **1.22×** on our decode hot kernel (`autokernel-loop.md:6495`). Audit whether our `mmvq.cu` carries an equivalent inner-loop branch (our gated-MoE / GPT-OSS paths differ). Gate: op-level ≥5 interleaved reps vs the C6 store, keep ≥1.10, drop below. | `autokernel-loop.md` (MMVQ / AK-ASM family) | **PROBE** — one op-level GPU row; falsifier is a branch audit showing no hoistable branch. |
| **KC-4** | **Replace two scheduled hand-built harnesses with Kerncap's reproducer**, once KC-1 clears: (i) the RVP-RACE-2 launch-capture shim (`rocm-kernel-authoring.md:1729`); (ii) the C5-ISA-2 "standalone harness (1–2 weeks)" (`rocm-kernel-authoring.md:2996`), where the HSACO-only path + `--hsaco` variant replay is exactly the `.co`/`hipModuleLoad` asm-tier harness. Scope: fixture generation only, inside the sandbox. | `rocm-kernel-authoring.md` | **TRIGGER** — behind KC-1; compare against the hand-built option on effort, not on principle. |
| **KC-5** | **Do not let Kerncap near the trust boundary.** No confinement, no anti-tamper, no oracle separation; its correctness oracle is identity-to-captured-run, so an identically-wrong candidate passes. Record as an architectural anti-claim so a future reader does not "simplify" C6 into it. | `autokernel-loop.md` (§C6 / §12) | **DECLINE** — architectural, not effort. Does not block KC-2/3/4. |
| **KC-6** | **Do not carry the 13.6×.** It prices a 2,072 s `rocprof-compute` counter run against a 129.4 s byte-exact replay; our validation step is `test-backend-ops` + paired timing against a 2 % floor. Carry **5.4× inner loop / 7× single-TU rebuild**. | `kernel-champion-and-promotion.md` | **DECLINE-CLAIM** (anti-claim, recorded). |
| **KC-7** | **Adopt "tuning-pinned" for any Triton arm we ever gate.** Different autotune configs are numerically different: switching from the fastest to the second-fastest config, 7.7 % slower, changed 11.3 % of output elements (max abs err 1.22e-4) on FP16 `attn_fwd` (`kerncap.html:574`). Any Triton candidate comparison must bind `num_warps`/`num_stages`/tile sizes or it is not a comparison. | `autokernel-loop.md` (§1.5.1 Triton tier) | **ADOPT-PATTERN** — cheap, no GPU. |
| **KC-8** | **Snapshot-capacity check before any trial on 27B-class models.** 27B Q8_0 ≈ 29 GB weights + workspace against a 64 GB MI210 and a 1.7 GB/s capture path: budget ~18 s and ~30 GB of host artifact per capture. Confirms feasibility; record the number so nobody is surprised. | `rocm-kernel-authoring.md` | **NOTE** — folded into KC-1's preconditions. |

---

## 8. Dive-surfaced sources (grep-checked against `research/intake_index.yaml`)

| Source | In index? | Why it matters here |
|---|---|---|
| **CRIUgpu** — Stoyanov et al. 2025, arXiv:2502.16631 | **absent** (grep `2502.16631` = 0) | Transparent checkpoint/restore of GPU workloads, cited as the process-level alternative Kerncap rejects (`kerncap.html:2475`). The closest thing to "restore a captured device state" outside the kernel-replay literature. |
| **rr** — O'Callahan et al. 2017, arXiv:1705.05937 | **absent** (grep = 0) | The CPU record-replay reference; the paper's argument for *why* GPU state is different lives in this contrast. |
| **Kokkos Kernels** — Rajamanickam et al. 2021, arXiv:2103.11991 | **absent** (grep = 0) | Framework-generated kernel discovery (DWARF is the only path that works when `__global__` lives in framework headers). Relevant if we ever extract from a portability layer. |
| **AMDResearch/intellikit** (repo, `kerncap/` subdir) | **absent** (grep = 0) | The artifact itself; a `kerncap/` directory is present at repo root (verified 2026-11-06). Not a paper — needs a repo entry, not an intake row. |
| ROCm Compute Profiler / `rocprof-compute` | present as a tool (19 mentions), no own entry | Used as the paper's validation baseline; already ours. |
| GEAK (2507.23194) | present (18 mentions) | Already the AK substrate selection (`rocm-kernel-authoring.md:1770`); Kerncap cites it as a consumer of exactly this kind of fixture (`kerncap.html:2499`). |
| KernelBench (2502.10517) | present (45 mentions) | Same consumer argument. |
| Nsight Compute / CUPTI Checkpoint API | discussed in-index (205 / 24 mentions), no own entry | The prior art Kerncap must beat; nothing to ingest. |
| LAMMPS — Thompson et al. 2022 | 2 mentions, no entry | Eval workload only. |

---

## 9. Artifact audit

- **Artifact exists and is open.** `https://github.com/AMDResearch/intellikit` returns 200 and its root
  listing contains `kerncap/` alongside `accordo`, `linex`, `metrix`, `nexus`, `rocm_mcp`, `uprof_mcp`
  (probe 2026-11-06). The paper's `\footnote` link is to the *monorepo*, not to a Kerncap-scoped
  release; no tag, version or DOI is named. I did not read the `kerncap/` licence — do not assume MIT.
- **Not independently reproducible from this dive.** I did not run the tool: ROCm 6.2.0-66 lacks
  `librocprofiler-sdk`, and the paper requires ROCm ≥ 7.0. Every number above is the authors'.
- **Numbers checked for internal consistency.** 13.6× = 2,208/162 ✓; 5.4× = 136/25 ✓; 1.22× =
  34.5/28.3 ✓; 7× = 128/18.3 ✓; capture-cost arithmetic on vLLM: 30 GB ÷ 1.7 GB/s ≈ 18 s ✓, and
  `Full cap. < Base` is explained by the sentinel short-circuit rather than being an error (`:1952`).
  Table 3's §5.3 text says "~7–14 s on llama.cpp across archs" while Table 4 gives 7.0 / 13.0 / 13.8 s
  — consistent. One soft spot: §5.3 prose says a 10-second baseline "yields a 1.9–2.6× wall-clock
  ratio" (`:1850`) while Table 3 reports 1.90× for llama.cpp and 1.54× for LAMMPS on gfx942 — the
  range spans architectures, not the single gfx942 column; not an error, but easy to misread.
- **Extraction caveat in this dive's own copy.** LaTeXML duplicates math tokens; `kerncap_paras.tsv`
  inherits the duplication for tabular cells (`1.06 × 1.06\times`). Prose quotes are normalised to one
  occurrence and hashed as printed; table values above are read as the single occurrence, which
  matches the PDF rendering. `sha256_html` over raw bytes is authoritative.
- **Host facts** (ROCm `6.2.0-66`, no `librocprofiler-sdk`, MI210/gfx90a) are live probes on
  2026-11-06, not literature.
