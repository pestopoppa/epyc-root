# System-Wide Inference Kernel Optimization Program

**Status:** Draft handoff — research program, not a deployment plan  
**Primary goal:** Build the fastest correct inference stack that this machine can sustain across CPU, GPU, short-context, long-context, single-stream, batched, dense, MoE, and recurrent-hybrid workloads  
**Hardware scope:** AMD EPYC 9655-class host, four NUMA domains, approximately 1.1 TiB DDR5 memory, one AMD Instinct MI210  
**Software scope:** `llama.cpp` fork, HIP backend, CPU backend, model loading/quantization, speculative decoding, serving scheduler, and the measurement/autoresearch harness  
**Production rule:** All kernel and scheduler work remains isolated, default-off, and outside the frozen production branch until correctness, quality, repeatability, and promotion gates pass

**ROCm provider rule:** AutoKernel may search exact-shape library selection, compiler flags, launch
topology, standalone Triton/HIP kernels, and source-available ROCm modules in isolated,
content-addressed builds. Those artifacts are candidate providers, not independent champions. A win
must integrate through an experimental `llama_gpu` build and pass operator plus whole-model gates
before it can join the `llama.cpp` champion. Shared `/opt/rocm` mutation is forbidden; opaque vendor
binaries may serve only as hash-bound baselines or dependencies, never authored champion source.

> The Qwen3.5-122B-A10B IQ2 comparison is only the observation that exposed the broader issue. This program is explicitly **not** a 122B-IQ2 optimization plan. It is a system-wide effort to close software-addressable efficiency gaps on both the MI210 and the EPYC host.

---

## 1. Core question

The MI210 has roughly 1.6–1.7 TB/s of HBM bandwidth. The host exposes roughly 450 GB/s of aggregate DDR5 bandwidth under an ideal streaming workload. Yet measured token throughput often scales much less than these nominal bandwidth ratios suggest.

The correct question is not:

> Why is one particular model slower than a friend's DGX Spark result?

The correct question is:

> For every important inference regime on this machine, what fraction of the relevant hardware roofline is being realized, what prevents higher utilization, and which missing algorithms, layouts, kernels, fusions, and scheduler features can close the gap?

The program therefore separates:

- raw kernel efficiency from scheduler efficiency;
- model payload traffic from KV/state/metadata traffic;
- bandwidth saturation from memory-latency and insufficient-parallelism limits;
- single-token GEMV from batched GEMM/MMQ;
- dense, small-active-MoE, large-active-MoE, and recurrent-hybrid architectures;
- CPU decode, CPU prefill, GPU decode, GPU prefill, and serving-level throughput.

---

## 2. Why token throughput does not automatically scale with nominal bandwidth

For a pure, perfectly streamed, batch-one decode step:

\[
T_{\text{decode}} \approx
\frac{B_{\text{effective}}}
     {W_{\text{active}} + K_{\text{read}} + S_{\text{state}} + M_{\text{metadata}}}
\]

where:

- \(B_{\text{effective}}\) is achieved bandwidth, not the datasheet number;
- \(W_{\text{active}}\) is the actual weight payload touched per token;
- \(K_{\text{read}}\) is KV-cache traffic;
- \(S_{\text{state}}\) is recurrent or other persistent-state traffic;
- \(M_{\text{metadata}}\) includes scales, codebooks, routing indices, quant metadata, and intermediate writes.

This approximation only works when compute, synchronization, launch overhead, routing, and sampling are secondary.

A nominal bandwidth ratio predicts throughput only if the two systems have approximately equal:

- active parameter count;
- effective bits per active weight;
- metadata overhead;
- dequantization/unpack work;
- achieved-bandwidth fraction;
- memory-level parallelism;
- launch overhead;
- routing pattern;
- recurrent-state cost;
- KV format and context;
- scheduler behavior;
- speculative-decoding acceptance and verification cost.

Those conditions rarely hold between:

- Blackwell + vLLM + AutoRound INT4/FP8;
- CDNA2 + llama.cpp + GGUF IQ/K-quants;
- Zen 5 + AVX-512 + NUMA-distributed DDR5.

### 2.1 The important conclusion

The fact that token throughput rises much less than nominal bandwidth does **not** prove the gap is fundamental.

It proves that nominal bandwidth is not currently the only active term.

The objective of this handoff is to measure the missing terms directly and determine which are software-addressable.

---

## 3. Program-wide workload taxonomy

No optimization is “good for the system” until its valid regime is known.

### 3.1 Architecture classes

Use at least one representative model from each class:

| Class | Representative role in the program | Main kernel risks |
|---|---|---|
| Dense transformer | Dense Q8/Q4 control | GEMV/GEMM utilization, attention, LM head |
| Small-active MoE | Few active parameters, many experts | routing, grouped expert execution, batch reuse |
| Large-active MoE | Larger expert payload per token | HBM/DDR traffic, expert-union growth, underfilled grids |
| Recurrent-hybrid / GDN / SSM | Attention mixed with recurrent layers | state traffic, serial dependencies, rollback, launch count |
| Long-context attention/DSA | KV-heavy or indexed attention | KV bandwidth, sparse attention, indexer overhead |
| Very-large CPU-only MoE | Models exceeding MI210 capacity | NUMA locality, expert placement, offload economics |

### 3.2 Serving regimes

Every relevant model class should be evaluated in:

1. batch-one short-context decode;
2. batch-one long-context decode;
3. high-concurrency short-context decode;
4. high-concurrency long-context decode;
5. short prefill;
6. long prefill;
7. mixed prefill/decode serving;
8. speculative decode;
9. continuous variable-length serving;
10. CPU-only, GPU-only, and hybrid execution where applicable.

---

## 4. Measurement constitution

A faster number without a mechanism receipt is not a result.

### 4.1 Required identity for every run

Record:

- source repository, branch, commit, and dirty state;
- exact binary and linked libraries;
- compiler, ROCm, kernel, and firmware versions;
- model path, file sizes, hashes, tensor inventory, and quant metadata;
- context, batch, slots, MTP depth, KV formats, flash-attention path;
- exact CPU affinity and NUMA policy;
- GPU PCIe path and device NUMA node;
- prompt set, generated-token count, sampling parameters, and cache state;
- competing processes, clock/power state, and thermal state;
- whether the result is observation-grade or decision-grade.

### 4.2 Correctness gates

Before performance comparison:

1. backend-op tests cover the exact new shapes;
2. no silent CPU fallback;
3. no invalid launch;
4. no NaN or unstable accumulation;
5. deterministic-output comparison where bit identity is expected;
6. bounded numerical and perplexity checks where accumulation order changes;
7. recurrent-state and MTP rollback tests;
8. a real-model coherence smoke;
9. a fixed quality mini-suite before broad benchmarking.

### 4.3 Required mechanism counters

#### GPU

- kernel wall share;
- HBM bytes and achieved bandwidth;
- L2 hit rate and cache-line utilization;
- active waves and occupancy;
- memory-unit busy/stalled;
- VALU and MFMA utilization;
- LDS allocation and bank conflicts;
- kernel launch count and inter-kernel gaps;
- tokens per expert and unique experts touched;
- graph-capture hit rate;
- MTP accepted tokens and verify-shape distribution;
- KV/state bytes per decode step.

#### CPU

- per-NUMA read/write bandwidth;
- local versus remote traffic;
- IPC and stall classes;
- vector instruction counts;
- OpenMP barrier count and wall share;
- LLC and TLB misses;
- thread scaling by physical core and SMT;
- first-touch and mmap placement;
- expert-locality statistics;
- per-op and per-graph-node wall time.

### 4.4 Derived metrics

\[
\text{bytes/token}
=
\frac{\text{measured model-related bytes}}
     {\text{generated tokens}}
\]

\[
B_{\text{effective}}
=
\frac{\text{measured model-related bytes}}
     {\text{decode wall time}}
\]

\[
\eta_{\text{memory}}
=
\frac{B_{\text{effective}}}
     {B_{\text{nominal}}}
\]

\[
U_{\text{experts}}
=
\left|\bigcup_{\text{tokens in batch}}
\text{selected experts}\right|
\]

\[
R_{\text{expert reuse}}
=
\frac{\text{total expert selections}}
     {\text{unique expert weights touched}}
\]

\[
C_{\text{launch/token}}
=
\frac{\text{launch-gap time}}
     {\text{generated tokens}}
\]

---

# Part I — Baseline and diagnosis

## P0.1 Exact per-operator roofline map

**Purpose:** Replace broad “bandwidth-bound” or “compute-bound” labels with a measured roofline for every important operator and model class.

### Matrix

For each representative architecture:

- short and long context;
- batch one;
- medium batch;
- saturation batch;
- speculation off;
- production speculation recipe.

### Output

For each major operator:

```text
operator
shape
dtype/quant
bytes read
bytes written
FLOPs or integer ops
achieved bandwidth
achieved compute
launch cost
occupancy
wall share
classification
```

### Classifications

- bandwidth-saturated;
- memory-latency/MLP limited;
- grid-underfilled;
- compute/dequant limited;
- launch limited;
- barrier/synchronization limited;
- cache/TLB limited;
- NUMA remote limited;
- scheduler fragmented.

### Completion criterion

At least 90% of end-to-end wall time must be assigned to measured mechanisms before a new large kernel project begins.

---

## P0.2 Kernel benchmark versus serving benchmark

Create two distinct benchmark families.

### Fixed-shape synchronized benchmark

- equal prompt lengths;
- equal generated-token lengths;
- synchronized decode;
- no request churn;
- no prefix-cache hits.

This isolates the backend kernels.

### Continuous variable-length benchmark

- staggered arrivals;
- variable prompts and outputs;
- realistic completion churn;
- bounded latency objective.

This isolates scheduler, KV allocation, and batching policy.

A serving-stack win must not be reported as a kernel win, and a kernel win must not be hidden by a weak scheduler.

---

## P0.3 Cross-substrate normalized scoreboard

Maintain a scoreboard indexed by:

```text
(model, quant, device, context, batch, speculation, KV format, kernel build)
```

Include:

- tok/s;
- effective GB/s;
- bytes/token;
- prefill tok/s;
- per-user throughput;
- p50/p95 latency;
- quality receipt;
- profiler bottleneck;
- valid dispatcher region.

---

# Part II — MI210 GPU program

## G1. Host-thread, PCIe, and pinned-memory NUMA locality

**Status:** Important remaining measurement.

The MI210 is attached to a specific NUMA node. Submission threads, pinned allocations, and first-touch placement should be tested explicitly rather than inherited from historical CPU-region conventions.

### Arms

1. historical placement control;
2. device-local physical cores;
3. device-local SMT siblings;
4. compact versus spread local placement;
5. local CPU + local host-memory binding;
6. local CPU + interleaved host memory;
7. remote-node control;
8. allocator first-touch performed by the eventual submission team.

### Workloads

- empty/small HIP launch latency;
- H2D/D2H transfers at relevant sizes;
- dense batch-one decode;
- dense high-batch decode;
- MoE batch-one decode;
- MoE high-batch decode.

### Required evidence

- launch gaps;
- host cache-line migration;
- DMA latency;
- GPU idle intervals;
- throughput and p99 latency.

---

## G2. Batch-one low-bit GEMV efficiency

**Goal:** Raise achieved HBM utilization for dense and expert GEMV-like shapes.

### Candidate work

- wave64-native data layout;
- load-time SoA repack;
- more independent weight loads in flight;
- async prefetch and deeper double buffering;
- batch-one-specific workgroup sizing;
- register/LDS balance autotuning;
- activation quantization reuse;
- persistent GEMV;
- separate layouts for batch one and batched execution;
- weight swizzle aligned to gfx90a cache and wave behavior.

### Required controls

- FP16/BF16 path as a hardware-utilization control;
- Q8 path;
- Q4/K-quant path;
- IQ path;
- dense and expert-row shapes.

### Key question

Is low-bit inference saving bytes while losing more in unpack, metadata, occupancy, or memory-level parallelism than it gains?

---

## G3. GPU-native low-bit layout program

Do not assume GGUF's storage layout is the optimal execution layout.

### Candidate layouts

- scale/codebook/sign arrays separated for coalesced access;
- pre-expanded small metadata;
- expert rows aligned and padded to native tile boundaries;
- dual layout: GEMV for batch one, grouped MMQ for batch;
- per-tensor-class layout rather than one model-wide format;
- optional load-time repack with a measured startup/VRAM budget.

### Decision rule

A repack is justified when:

- startup cost is acceptable for the serving duty;
- VRAM overhead preserves required context;
- a real graph, not only a microbenchmark, gains materially;
- profiler counters show reduced metadata traffic or higher HBM utilization.

---

## G4. Persistent grouped MoE execution

**Goal:** Replace fragmented per-expert execution with a globally load-balanced GPU work queue.

### Proposed pipeline

1. route tokens;
2. sort or bucket by expert;
3. emit compact expert/token/tile descriptors;
4. persistent workgroups pull tiles;
5. execute gate/up;
6. fuse activation where profitable;
7. execute down projection;
8. apply routing weights;
9. scatter/reduce output;
10. optionally append shared experts to the same schedule.

### Variants

- batch-one/small-M path;
- medium batch;
- high batch;
- Q8;
- Q4/K;
- IQ2/IQ3;
- fused shared experts;
- full versus partial expert pipeline.

### Success metrics

- more workgroups than the baseline expert grid;
- higher CU occupancy;
- higher memory-unit busy;
- lower launch count;
- higher expert-weight reuse;
- meaningful end-to-end gain.

---

## G5. Stream-K and split-K for underfilled expert shapes

The existing compact-LDS work established that freeing LDS alone does not help when the grid itself is too small.

### Search space

- split factor 2/4/8;
- static split-K;
- dynamic stream-K queue;
- atomic accumulation;
- separate reduction kernel;
- fused reduction;
- Q8 and IQ paths;
- expert-token count from one token to saturation.

### Dispatcher rule

Use this path only when baseline workgroup count cannot fill the GPU. Already-saturated shapes must retain the existing kernel.

### Stop rule

Retire any split where reduction/fixup consumes most of the added parallelism benefit.

---

## G6. Shared-expert fusion

### Candidate levels

1. append shared experts to routed-expert scheduling;
2. share activation packing only;
3. share gate/up execution;
4. fuse activation and down projection;
5. fuse weighted output accumulation.

### Expected benefits

- fewer launches;
- one activation conversion;
- larger grouped operation;
- better workgroup count;
- improved L2 reuse.

---

## G7. LM-head, logits, top-k, and sampling tail

The DGX comparison suggests that the output head can be a large software lever. The MI210 path should have its own hardware-native implementation.

### Candidate path

- INT8/Q8 vocabulary projection;
- BF16/FP16 activation;
- persistent vocabulary tiling;
- partial top-k per workgroup;
- fused final reduction;
- fused temperature/top-p/top-k;
- repetition-penalty integration;
- direct sampled-token output without materializing full FP32 logits where possible.

### Controls

- short output;
- long output;
- small and large vocabulary;
- batch one and batch;
- exact top-k agreement;
- distributional sampling check.

---

## G8. Shape-bucketed HIP graphs

Generic graph capture is not enough when verification and batching produce many shapes.

### Program

1. trace shape frequency;
2. identify buckets covering at least 95% of steps;
3. pre-capture graphs;
4. compare:
   - exact multi-graph cache;
   - padded masked buckets;
   - onegraph/supergraph;
5. account for padding work versus saved launch time.

### Required result

Graph hit rate, launch-gap reduction, and end-to-end improvement must all be reported.

---

## G9. Recurrent/GDN/SSM decode fusion

This is one architecture class, not the whole program, but it needs a dedicated path because ordinary GEMM assumptions do not cover it.

### Candidate fusion boundary

- state load;
- convolution-state update;
- recurrent-state update;
- normalization;
- gating;
- output preparation;
- speculative snapshot/rollback bookkeeping.

### Non-negotiable requirements

- correct committed and speculative states;
- no full-state copy per draft token;
- exact rollback after rejection;
- separate batch-one and batched-verify shapes;
- BF16-state option retained.

---

## G10. Chunked recurrent long-prefill

### Program

- fused FP32 reference;
- BF16 state;
- on-chip chunk-local intermediates;
- chunk-size autotuning;
- MFMA projection fusion;
- prefill-to-decode transition validation;
- multi-request prefill controls.

### Goal

Reduce recurrent graph dispatch and state round trips on long prompts.

---

## G11. Mixed-KV shape-specialized attention

A general all-quant attention build should not replace optimized homogeneous paths.

### Work

- retain dedicated f16/f16 and q4/q4 kernels;
- add a dedicated mixed q4/f16 kernel;
- specialize exact model dimensions;
- remove runtime format branching inside hot loops;
- test short and long contexts;
- prove no silent CPU fallback.

---

## G12. Joint speculation-depth × batch × context policy

Per-model MTP depth is only one axis. The production policy should be a measured surface:

```text
(model, quant, context band, active slots, scheduler pressure) -> draft depth
```

### Required telemetry

- acceptance;
- accepted length;
- target forward passes;
- verify-shape distribution;
- graph-cache hits;
- rollback cost;
- aggregate and per-user throughput.

A depth optimal at batch one must not be assumed optimal at batch 32.

---

## G13. vLLM as design oracle and possible alternate engine

The objective is not a blind vLLM port. It is a capability audit.

### Audit

1. build current vLLM ROCm for gfx90a;
2. benchmark a supported dense control;
3. identify model-loader, quant, GDN, attention, and fused-MoE blockers;
4. separate:
   - scheduler advantage;
   - graph advantage;
   - fused-MoE advantage;
   - output-head advantage;
   - unsupported hardware paths;
5. decide whether to:
   - complete gfx90a support;
   - port selected kernels;
   - reproduce the execution structure in llama.cpp.

### Important hardware caveat

ROCm features written for CDNA3+ must not be treated as directly usable on the MI210. Port the algorithm, not the unsupported instruction path.

### ROCm module mutation and promotion boundary

Treat rocBLAS, hipBLASLt, CK/CK-Tile, rocWMMA, compiler/runtime choices, and source-available vendor
modules as separate mechanisms during diagnosis. AutoKernel may benchmark provider/algorithm
selection, author a standalone replacement, or fork a source-available module when a current profile
identifies that mechanism as the limiter. Every such action occurs in a pinned isolated environment;
the resident ROCm installation and live stack remain immutable.

The deployable unit is still the experimental llama GPU candidate. Module-local speed is diagnostic
until the exact integration is bound to captured workload tensors, correct output, and a whole-model
result. This avoids two opposite errors: blaming every custom low-bit path on “ROCm,” and allowing a
fast standalone module to become a champion without proving that llama.cpp can safely use it.

---

# Part III — EPYC CPU program

## C1. Exact DDR and NUMA roofline

For every representative model class, measure:

- bytes/token;
- per-NUMA bandwidth;
- remote/local traffic;
- thread scaling;
- barrier time;
- vector utilization;
- active-weight traffic;
- metadata traffic;
- KV/state traffic.

Classify each model/shape as:

```text
bandwidth-saturated
latency/MLP-limited
barrier-limited
compute/dequant-limited
NUMA-remote-limited
cache/TLB-limited
```

Do not carry a “CPU decode is bandwidth-bound” conclusion from one dense or one hybrid model to every workload.

---

## C2. Operator-cluster fusion for decode

### Candidate clusters

- Q/K/V projections;
- MoE gate/up;
- activation + expert weighting;
- norm + projection preparation;
- residual + norm;
- shared/routed expert accumulation;
- recurrent state/norm/gate micro-ops.

### Goals

- one activation pack per cluster;
- fewer graph nodes;
- fewer OpenMP barriers;
- longer work intervals per thread;
- better cache reuse;
- reduced synchronization-to-compute ratio.

### Measurement

Every fusion must show:

- fewer barriers;
- lower barrier wall time;
- lower graph-node count;
- lower end-to-end wall time;
- no adverse NUMA traffic shift.

---

## C3. Persistent CPU thread team

### Candidate designs

- persistent worker team across operator clusters;
- per-NUMA worker teams;
- epoch counters instead of full barriers;
- node-local task queues;
- restricted work stealing;
- barrier elision for disjoint output regions;
- one backend task spanning several graph nodes.

### Required validation

- no races;
- no oversubscription;
- stable concurrent serving;
- deterministic completion;
- thread-safety tests;
- clean teardown.

---

## C4. Expert-local NUMA placement

Global interleaving maximizes theoretical controller participation, but it may not be best for routed experts.

### Designs

- whole experts owned by one NUMA node;
- expert work executed by the owning node;
- shared experts replicated;
- small hot-expert set replicated;
- routed experts local, dense/shared tensors interleaved;
- routing-frequency-aware placement;
- static round-robin control.

### Measurements

- remote traffic;
- node imbalance;
- per-node bandwidth;
- reduction overhead;
- single-stream and batched throughput;
- routing-skew sensitivity.

---

## C5. Grouped CPU MoE for batched workloads

This is workload-gated and should not be judged on single-token decode.

### Target regimes

- EvalTower/bulk evaluation;
- multi-request serving;
- long prefill;
- batched agent workloads.

### Candidate implementation

- blocked sparse expert-token index;
- packed activation matrices by expert;
- grouped gate/up and down GEMMs;
- reusable transpose/scatter indices;
- integration with expert-local NUMA placement.

---

## C6. CPU prefill continuation

The existing default-off CONCAT row-partition work establishes that prefill graph scheduling remains fertile.

### Next profile-selected candidates

- same-input gate/up fusion;
- GDN projection cluster fusion;
- activation-pack reuse;
- norm-tail fusion;
- conversion hoisting;
- shared/routed accumulation fusion;
- chunked prefill;
- prefill-specific thread-team policy.

---

## C7. Automatic policy for the existing CONCAT fast path

Replace a manual environment switch with a safe shape dispatcher based on:

- tensor dimensions;
- transposition;
- tensor type;
- prompt/batch width;
- prefill versus decode;
- thread count.

The dispatcher must preserve known positive prefill cells and avoid known decode regressions.

---

## C8. CPU LM-head and fused sampling

### Work

- AVX-512BW INT8/Q8 vocabulary projection;
- NUMA-partitioned vocabulary;
- per-thread partial top-k;
- one final merge;
- fused scaling, repetition penalty, top-p, and sampling;
- avoid full FP32 logits when not required.

---

## C9. Tensor-class hybrid quantization

The fastest artifact may not be “Q4” or “IQ2” globally.

Potential policy:

- routed experts: aggressive low bit;
- shared experts: Q8/BF16;
- recurrent state: BF16;
- attention projections: Q4/Q8;
- LM head: INT8/Q8;
- norms and small tensors: F16/F32.

Measure one tensor class at a time and retain only changes that improve quality-adjusted wall time.

---

# Part IV — Serving and scheduler program

## S1. Token-budget continuous batching

Transplant the serving concept, not necessarily the vLLM implementation.

### Features

- maximum tokens scheduled per step;
- independent prefill/decode budgets;
- immediate compaction of finished requests;
- dynamic batch composition;
- bounded admission;
- optional multiple in-flight batches;
- scheduler-pressure-aware MTP depth;
- context-aware avoidance of pathological batching.

---

## S2. Block/paged KV management

### Objectives

- avoid reserving full slot context;
- raise useful concurrency;
- reduce KV copying;
- allow safe prefix sharing;
- support prefill/decode disaggregation experiments;
- preserve explicit cache-state labels in benchmarks.

---

## S3. Capability registry

Every optimized path must be indexed by:

```text
model
quant
device
context band
active slots
prefill/decode phase
MTP depth
KV format
kernel build
```

Each row contains:

- valid shapes;
- expected throughput;
- variance;
- quality/correctness receipt;
- fallback;
- mechanism;
- source commit.

Role names are not sufficient.

---

# Part V — Autoresearch loop

## A1. Objective

Automate proposal, implementation, build, correctness testing, profiling, and measurement while keeping promotion human-controlled.

The loop optimizes separate objectives:

1. GPU batch-one short context;
2. GPU batch-one long context;
3. GPU batched short context;
4. GPU batched long context;
5. CPU batch-one decode;
6. CPU batched decode;
7. CPU long prefill;
8. mixed serving;
9. quality-adjusted throughput;
10. energy efficiency.

---

## A2. Proposal schema

Every generated candidate must state:

```yaml
hypothesis:
target_regime:
expected_counter_change:
files_and_functions:
correctness_risks:
target_shapes:
non_target_shapes:
fallback:
stop_condition:
```

A proposal without a falsifiable counter prediction should not consume a benchmark window.

---

## A3. Candidate pipeline

1. create isolated worktree;
2. apply one conceptual change;
3. build targeted binaries;
4. run static checks;
5. run exact backend-op shapes;
6. run state/rollback tests;
7. run tiny real-model smoke;
8. run short paired A/B;
9. profile mechanism;
10. run repeated matrix;
11. run quality mini-suite;
12. emit machine-readable verdict;
13. bank default-off or revert;
14. never auto-merge or auto-deploy.

---

## A4. Lexicographic reward

Priority order:

1. correctness;
2. quality;
3. stability;
4. target throughput;
5. target latency;
6. non-target regression;
7. energy;
8. complexity.

Example:

\[
R =
\begin{cases}
-\infty, & \text{correctness or quality fails}\\
\Delta T
-\lambda_1 R_{\text{non-target}}
-\lambda_2 \sigma
-\lambda_3 C_{\text{complexity}},
& \text{otherwise}
\end{cases}
\]

Add a mechanism bonus only if the intended profiler counter moves.

---

## A5. Cache and prompt hygiene

- distinct prompts across repetitions;
- fixed prompt-token and output-token budgets;
- record prefix/prompt cache hits;
- disable caches for direct-kernel claims;
- retain full responses;
- report finish reasons;
- never benchmark repeated identical prompts against a stateful cache unless cache behavior is the subject.

---

## A6. Search hierarchy

Search in this order:

1. placement and launch configuration;
2. dispatcher;
3. autotuning;
4. layout/repack;
5. operator fusion;
6. work scheduling;
7. new kernel;
8. scheduler architecture;
9. alternate engine.

Do not write a new kernel while an unmeasured placement or dispatch defect remains plausible.

---

# Part VI — Initial execution queue

| Order | Work item | Why first |
|---:|---|---|
| 1 | Exact CPU/GPU bytes-token and operator roofline map | Establishes where nominal bandwidth is being lost |
| 2 | MI210 host-thread and pinned-memory NUMA sweep | Cheap, unmeasured, system-wide |
| 3 | Fixed-shape versus continuous-serving benchmark split | Prevents scheduler and kernel effects from being conflated |
| 4 | Joint MTP-depth/batch/context surface | May recover throughput without kernel work |
| 5 | GPU LM-head/logits/top-k profile and prototype | Clear transplantable concept from the DGX stack |
| 6 | First CPU operator-cluster fusion | Main remaining CPU decode research direction |
| 7 | GPU-native low-bit layout microbenchmarks | Tests whether packed formats waste HBM potential |
| 8 | Persistent grouped MoE prototype | Main batched-MoE redesign |
| 9 | Shape-gated stream-K prototype | Direct response to underfilled expert grids |
| 10 | CPU expert-local NUMA prototype | Exploits four memory domains rather than only interleaving them |
| 11 | Shape-bucketed HIP graphs | Removes remaining launch fragmentation |
| 12 | Recurrent decode/prefill fusion | Architecture-specific, after common kernels are mapped |
| 13 | Current-vLLM gfx90a capability audit | Determines whether to port engine, kernels, or scheduler ideas |
| 14 | Token-budget continuous batching | Serving-layer gain after kernel baselines are trustworthy |

---

# Part VII — Do-not-repeat ledger

The executor must consult existing project handoffs before reopening any of the following:

- generic fused-dequant proposal where the current Q8 path is already integer-native;
- n-gram speculation claims based on repeated prompts or warm context;
- compact-LDS MoE work without proving the grid can occupy a second workgroup;
- blanket all-quant flash attention;
- global MTP depth inherited across models and regimes;
- global NUMA claims based on stale NPS2 constants;
- shared-mmap fleet measurements without first-touch control;
- SIMD-only CPU rewrites when the profile is barrier- or bandwidth-dominated;
- router/top-k optimization without profile evidence that routing is material;
- scheduler-split rewrites when the graph is already one backend split;
- single-token evaluation of a technique intended for batched MoE;
- synthetic-shape kernel wins that do not occur in a real graph.

---

# Part VIII — Decision outcomes

The program should distinguish among several possible system-level conclusions.

## Outcome A — Achieved bandwidth is the dominant gap

Prioritize:

- native layouts;
- prefetch;
- persistent kernels;
- stream-K;
- coalescing;
- MLP;
- NUMA locality.

## Outcome B — Low-bit unpack/dequant dominates

Prioritize:

- hardware-native quant formats;
- hybrid tensor precision;
- metadata pre-expansion;
- fused unpack/compute;
- tensor-class quant policy.

## Outcome C — Routing and expert fragmentation dominate

Prioritize:

- grouped persistent MoE;
- token sorting;
- shared-expert fusion;
- expert-local NUMA placement;
- better batch scheduler.

## Outcome D — Recurrent state dominates

Prioritize:

- recurrent fusion;
- state-format specialization;
- snapshot/rollback redesign;
- chunked recurrence.

## Outcome E — Launch, barrier, and scheduler fragmentation dominate

Prioritize:

- graph buckets;
- persistent thread teams;
- operator fusion;
- token-budget continuous batching;
- paged KV.

The likely result is a different dominant mechanism in each regime. The final system should therefore be a portfolio of shape- and model-class-specific kernels selected by a capability registry, not one universal path.

---

## Local context integration

The two presentation artifacts mentioned during drafting already exist locally. The hosted copies
are mirrors and must not be used as AutoKernel inputs:

- E5 CPU/NUMA results: `artifacts/operator/e5_w0_preliminary_results.md` and
  `artifacts/operator/e5_w0_preliminary_results.html`;
- GPU model-selection surface: `/mnt/raid0/llm/tmp/claude-artifacts/np_context_v8_decision.html`,
  backed by `epyc-inference-research/artifacts/np_context_study_v8_20260727/` and
  `epyc-inference-research/artifacts/np_context_study_20260723/`.

Reconcile this draft against those local records to:

1. remove duplicate experiments;
2. preserve any already-closed negative results;
3. import their prioritization and execution constraints;
4. add missing cross-links to existing project handoffs;
5. align terminology with the project's current measurement constitution.

AutoKernel's bootstrap manifest should name content-hashed local paths only. The temporary GPU
presentation surface should be copied to a durable local artifact path before implementation; its
underlying research bundles remain the evidence authority.
