# Hardware Optimization

**Category**: `hardware_optimization`
**Confidence**: verified (established CPU/NUMA findings) · observation (all 2026-07 GPU throughput numbers — single-run, contended host, no protocol-id per MEASUREMENT.md)
**Last compiled**: 2026-08-12 (adds the AutoKernel diagnostic-provenance boundary; prior Arena, real-MMQ WGM, C6, governed authoring, ROCm-upgrade, INF-37, Q4_K MMQ, expert-ceiling, oracle, sensitivity, C4, correctness, clock, roofline, topology, and quant-path findings retained)
**Sources**: 102+ documents

## Compiled Update — 2026-08-12 (AutoKernel diagnostic provenance)

**Confidence: verified receipt/source audit; no inference or campaign claim.**

RVP-T0-1, AK-BH-1/2/3, and AK-LN-2/AK-X-5a have durable diagnostic receipts and retain bounded
hardware, provider, factorial, flash-attention, and lane-proxy findings. They do not collectively
establish current AutoKernel campaign authority: several bind an experimental binary without a clean
committed source/build manifest, while the shared experimental tree is dirty. A receipt field naming
frozen v9 is not a substitute for the exact source, tree, build, library, and binary identities.

The operational dependency order is consequently provenance first: reproduce the hardened instrument
from clean committed source, run fresh frozen-v9 controls, run the full-host CPU IQK proposal, then
construct the real matched completed-proposal archive and evaluate it observe-only. Existing diagnostics
remain valid in their declared scope; synthetic archives remain regression tests.

### Source References (2026-08-12 provenance audit)

- [AutoKernel research loop](../handoffs/active/autokernel-research-loop.md) — campaign dependency order and matched-archive gates
- [ROCm verify/profile backend](../handoffs/active/rocm-verify-profile-backend.md) — diagnostic receipt authority boundary
- [2026-08-12 progress](../progress/2026-08/2026-08-12.md) — receipt hashes and source-provenance audit

## Compiled Update — 2026-08-11 (AutoKernel Arena audit and real-controller smoke)

**Confidence: verified audit and diagnostic-smoke behavior; no matched-campaign or promotion claim.**

The fixed AgentKernelArena authoring panel now distinguishes two authorities mechanically. The full
comparison remains eight arms and refuses at **6/8** because licensed, commit-pinned EvoEngineer and
ARGUS implementations are unavailable. A separately named available-source panel is ready at
**6/6**, but its receipt forbids implying an eight-arm result, ranking partial full-panel evidence,
or authorizing promotion. Both no-execution audits bind the same task, source identities, evaluator,
and 2h/8h/32h budget schedule.

A real one-iteration/two-branch KernelFoundry smoke found two defects that static coverage missed:
copied workspaces lacked the repository import root, then concurrent model branches raced in the
shared Arena evaluator. The repaired v3 run completed two GPT-5.6 Sol/high calls under a cleanly
released MI210 claim, passed centralized compilation and correctness, and admitted all four baseline
and four optimized timing cases. Its average speedup was **0.998668**, but the receipt is diagnostic,
non-rankable, and explicitly does not imply the matched campaign. The dashboard now projects this
empirical state separately from generic probe inventory and preserves those authority limits.

The K-Search, Xe-Forge, and GEAK-v1 one-iteration smokes subsequently completed the same centralized
compile, correctness, and 4/4 baseline plus 4/4 optimized timing boundary and released their MI210
claims. Their observed average speedups were respectively **1.003368**, **0.999612**, and
**0.995595**. Those values remain non-rankable smoke telemetry: the smokes establish executable
integration, not comparative controller quality or a matched-campaign result.

The Claude/Codex actor-critic path also reached a terminal integration smoke after repairs for
response parsing, contained candidate paths, nested-sandbox launch, and container stdin. Its actor
runs inside a digest-pinned, read-only-root container with only the task workspace writable. The
v5 completed planner, actor, and critic and reached centralized evaluation, but the evaluator worker
used `/usr/bin/python3` without pytest. Its apparent correctness failure and zero timing cases are
therefore infrastructure evidence, not evidence against the candidate. The authoring path was real,
but candidate correctness remained unknown until replay with the pinned ROCm evaluator Python and
package identity. That replay passed centralized compilation and correctness plus all
4/4 baseline and 4/4 optimized timing cases under the pinned ROCm evaluator. Its average speedup was
**0.993603**—non-rankable diagnostic telemetry that closes executable integration, not a controller
quality or promotion claim.

### Source References (2026-08-11 Arena audit/smoke)

- [Agentic ROCm kernel authoring](../handoffs/active/agentic-rocm-kernel-authoring.md) — fixed-panel coverage, source gates, receipt hashes, and live next actions
- [AutoKernel progress, 2026-08-11](../progress/2026-08/2026-08-11.md) — failed-smoke chronology, repairs, v3 measurements, and non-rankable scope
- [Dashboard contract](../dashboard/README.md) — current-state snapshot and separation of audit, available-source, and empirical-smoke authority

## Compiled Update — 2026-08-11 (AutoKernel C6 live-host sandbox)

**Confidence: verified live-host containment behavior; no inference or performance claim.**

AutoKernel's real kernel-authoring path now has a host-native, fail-closed C6 boundary rather than the
older devcontainer-only bwrap/unshare prototype. The evaluator provisions only a narrow
`/sys/fs/cgroup/autokernel` parent, creates a fresh per-invocation leaf, and keeps candidate execution
non-root under Landlock write confinement, seccomp signal/network/namespace denial, finite resource
limits, and descendant-draining teardown. Missing or unwritable delegation refuses before candidate
spawn; there is no `allow_unsandboxed` or environment escape on the live campaign path.

The live red-team probe on this host exercised Landlock ABI 6 as uid 1000. A write inside the
candidate tree succeeded, while an outside write and evaluator-receipt forgery failed; host signalling
and socket creation returned `EPERM`; and teardown killed an escaped descendant, proved empty cgroup
membership, and removed the invocation leaf. This closes the C6 host-readiness gate without weakening
the standing rule that a sandbox claim must name and exercise its actual syscall and filesystem
controls. No inference or production-stack change was needed.

### Source References (2026-08-11 C6 host sandbox)

- [ROCm verify/profile backend](../handoffs/active/rocm-verify-profile-backend.md) — dated C6 closure and live red-team outcomes
- [AutoKernel research loop](../handoffs/active/autokernel-research-loop.md) — syscall-confinement acceptance contract and live campaign ownership
- [2026-08-11 progress](../progress/2026-08/2026-08-11.md) — host provisioning, path wiring, verification scope, and no-inference boundary

## Compiled Update — 2026-08-11 (gfx90a WGM and authoring-loop boundary)

**Confidence: verified diagnostic microbenchmark and real-MMQ negative; no five-control performance
claim.**

A gfx90a work-group-mapping proxy found a real, bounded locality signal: WGM16 improved the synthetic
L2-sensitive kernel by **9.823%** versus no mapping across 240 balanced samples per cell, with a paired
bootstrap 95% CI of **9.754–9.977%** and bit-exact correctness. WGM8 and WGM32 were close; WGM2
regressed. The result selects none/8/16/32 for the real MMQ launch-order sweep. It does not establish
that the gain transfers to MMQ, because the proxy deliberately isolates locality rather than the full
quantized kernel.

The admitted real-MMQ transfer test then falsified that transfer. Its first pilot was a no-op because
CDNA stream-k bypassed the initial remap; r2 moved pure tile-order decoding into stream-k. All six
none/2/4/8/16/32 cells passed **43/43** Q4_K correctness cases, but WGM0 remained fastest and every
nonzero mapping regressed wall time by **1.286–4.050%**. WGM8 reduced all-MMQ TCC hit rate from
**67.304% to 59.849%** while read requests stayed nearly flat (**+0.201%**), and Q4_K alone lost
**7.903 percentage points**. G17 is therefore `CLOSED_NO_GO`; the uncommitted negative source is not a
promotion candidate, and the budget returns to the already-filed G15 elementwise/norm fusion lever.
The aborted trace-period counter pilot is excluded; successful counter-only captures are admitted.

The surrounding authoring loop now has three missing control-plane pieces: a versioned C5 seed corpus
with matched-budget RE-Bench log-time scoring, a prospective GEAK/Arena belief writer, and a gfx90a
FP8 target whose contract explicitly distinguishes authoring/emulation from unavailable MI210 native
FP8 matrix execution. A taxonomy audit also corrected an old citation conflation: KernelBench is a
kernel-generation benchmark, while the 9/9 bug-detection result belongs to a separate seeded-fuzzing
paper. RE-Bench contributes its scoring protocol, not its H100 task environment.

ROCm 7+ upgrades now have a fail-closed compile gate for the known LLVM unroll regression: pass
`-mllvm --amdgpu-unroll-threshold-local=600` through `CMAKE_HIP_FLAGS`, retain the compile command that
proves it reached HIP compilation, and compare only from an experimental branch. The current ROCm 6.2
stack is unchanged.

The authorized frozen-v9 five-control run did not reach inference. Its preflight passed source and
copied-binary identity but failed because the selected binary omitted six hardened runtime receipts;
package power was also unreadable. That is instrument evidence, not a performance result. The next
attempt must use a receipt-emitting hardened build and pass package-power preflight before taking a
claim.

### Source References (2026-08-11 WGM/authoring closeout)

- [AutoKernel research loop](../handoffs/active/autokernel-research-loop.md) — G17 negative disposition, G18 seed, and the failed-closed v9 control preflight
- [MI210 MFMA compute-bound paths](../handoffs/active/mi210-mfma-compute-bound-paths.md) — admitted proxy and real-MMQ receipts, hashes, and next lever
- [Agentic ROCm kernel authoring](../handoffs/active/agentic-rocm-kernel-authoring.md) — C5, RE-Bench, FP8, taxonomy and upgrade gates
- [ROCm upgrade checklist](../docs/runbooks/rocm-upgrade-checklist.md) — experimental-branch build and validation contract
- [2026-08-11 progress](../progress/2026-08/2026-08-11.md) — commit identities, receipt hash and no-inference boundary

## Compiled Update — 2026-08-11 (Q4_K MMQ correction and expert ceiling)

**Confidence: verified local correctness and matched historical measurement; experimental source is
not a durable candidate until operator-approved commit/push.**

The gfx90a Q4_K failure was not MFMA-specific: both the old force-MMQ MFMA and DP4A arms passed only
18/43 cases. The shared mechanism was Q8 activation staging. Q4_K's affine reconstruction multiplied
the quantized/dequantized Q8 values in its dot term but used the original float activation sum for the
min correction. Computing both from the same dequantized Q8 population fixed the ordinary and scatter
DS4 paths. Four final arms—default, force-rocBLAS, force-MMQ MFMA, and force-MMQ DP4A—then passed
172/172 cases at unchanged κ=1.5, maximum error ratio 1.228272. The receipt is retained; the source
change remains approval-gated in the experimental tree.

AutoKernel also gained a non-synthetic held-out task from local history. The new descriptor is honest
about the missing original July 4 command (`historical_command_recovered=false`), pins a replacement
surface, and seals the human patch until terminal candidate state. Across five matched blocks, the
human GDN bf16 patch raised mean `speed_tg` from 155.4233734 to 188.4099002, a 21.223659% expert
ceiling; same-binary expert-off stayed at parity with the parent (-0.105875%). With no terminal
AutoKernel candidate, candidate-to-expert scoring remains `COULD_NOT_CHECK` rather than inventing a
comparison.

Hostile same-shape distributions and checker isolation are now durable research gates, but their
two-case ROCm smoke is non-evidence: the producer is uncommitted and no receipt was retained. The
smoke showed both modes passing 2/2 selected `SOFT_MAX` rows with claim release and four samples;
campaign evidence waits for an operator-approved producer identity and fresh replay.

INF-37's alternative IQ2 profiler path is now instrumented but not yet evidence-bearing. A manual
Omniperf 2.0.1 / `rocprof` v1 smoke reached gfx90a and produced 260 dispatch rows, while the governed
runner retained a clean failure receipt: frozen-v9 `test-backend-ops` lacks the required
`--suite-seed` and `--repeat-suite` flags, so it refused before profiling. This separates tool
reachability from a reproducible counter claim. The seeded IQ2 capture remains open until the
experimental producer obtains an operator-approved durable identity and the same runner passes.

## Compiled Update — 2026-08-11 (AutoKernel input-sensitivity boundary)

**Confidence: verified implementation; live smoke is non-evidence until the producer has a durable
commit identity.**

AutoKernel now screens task populations on two independent axes before treating correctness cases as
meaningful: materialized inputs and reference outputs must vary across at least three seeds, and they
must also respond to identity, ×3, ×0.01, and negate transforms. Missing coverage, mixed suite
versions, a non-reference population, or an untrusted producer fails closed. The research reducer and
claim-aware runner are durable in research commit `000a2686` / `main` merge `f3c6b24a`.

A `SOFT_MAX` smoke returned PASS over 2,544 observations and 1,484 units with no unscoreable units,
while holding and releasing the CPU claim. It does **not** support a correctness or corpus-quality
claim: its `0db32c06e` suite identity names the committed parent while the materialized `AK_SENS_V1`
producer remains uncommitted. Producer-dependent rows stay open until an operator-approved producer
commit and fresh matched replay. This is the practical rule: an internally consistent receipt cannot
be durable evidence when the code that produced it is absent from the identity it cites.

The same audit invalidated promotion of the old RVP-C5-R observation: exact 2026-07-04 argv and raw
matched parent/human-patch evidence are gone, so a fresh retained replay is required.

## Compiled Update — 2026-08-11 (AutoKernel live correctness controls)

**Confidence: mixed — verified correctness-instrument acceptance on CPU; single-run GPU microbench
observations with retained receipts, not production or cross-surface performance claims.**

AutoKernel's stateful correctness pass now treats carried state as part of the result rather than
checking only ordinary outputs. For every selected recurrent/cache-backed case, the candidate and
reference must begin with byte-identical explicit state inputs, neither execution may mutate those
input buffers, and at least one final-state tensor must be included in the compared output set. A
missing receipt or any missing leg fails closed.

The first live pass used suite seed `4711` and accepted **5,184/5,184** cases across `SSM_SCAN`,
`SSM_CONV`, `FLASH_ATTN_EXT`, and `GATED_DELTA_NET`. Every `AK_STATE_V1` receipt carried
`initial_equal=1`, `input_immutable=1`, and one or more final outputs. The result validates the
instrument path; it does not make the experimental producer durable. Those producer changes remain
uncommitted pending explicit operator approval, and the v9/hardened performance calibration is a
separate next step.

The other live C2 axes now agree with that stateful result: the layout pass accepted **1,048/1,048**
offset, stride-gap, and transpose cases, while the seed-`4711` value pass accepted **779/779** cases
across `SOFT_MAX`, `ARGSORT`, `TOP_K`, and `SOLVE_TRI`, with identity, ×3, ×0.01, and negate all
completed. The `SOFT_MAX` checker required one important correction before acceptance: its invariant
must include implicit attention sink mass, not demand that only explicit output cells sum to one.

The predeclared clock-pinning discriminator also resolved negatively. During a 60-second 8192³ gfx90a
GEMM, 242 samples held 1700 MHz for 99.5868% of the window while throughput reached 41.904 TFLOP/s;
power peaked at only 200 W against the 300 W cap. The card did not approach the cap, so clock excursion
is not a live variance source under this saturation workload and a privileged
`--setperfdeterminism` control would add operational authority without solving an observed problem.

The next correctness layer is now live as an independent host-double oracle. It decodes Q4_0, Q8_0,
Q4_K, and Q6_K directly from GGUF wire bytes and emits
`fp64_error_ratio/host-double-gguf-wire/v1`, avoiding project quantization helpers on the reference
side. Five representative CPU cases, the dedicated broadcast regression, 31 real parser tests, and
the property self-test's 5/5 planted plus 5/5 clean cases passed.

The broad matrix first uncovered a real non-contiguous coverage bug in the oracle itself: quantized
rows must be read through the tensor's `nb[1..3]` strides, not as one packed span. After that repair,
the fixed forced-dispatch matrix preserved a much sharper negative result. Force-rocBLAS passed
**43/43** Q4_K cases with maximum error ratio **1.2283**; force-MMQ passed **18/43**, failed 25, and
reached **3.0361**. The remaining failures are therefore MMQ-specific stock correctness failures.
Keep κ fixed at 1.5, retain rocBLAS as the control, and do not rank the MMQ surface until corrected.

The baseline-honesty probes also reject global defaults. In AK-BH-1, best-heuristic hipBLASLt beat
rocBLAS at only three of nine prefill shapes, while its throughput ratio ranged from **0.734× to
1.322×**; future vendor baselines must choose the strongest library per exact shape. AK-BH-2 then
completed all eight explicitly pinned flash-attention × ROCWMMA × MMQ-MFMA arms on one 0.5B Q4_K_M
prefill surface. Flash attention on won each build pair, MMQ-MFMA was slower, and `r1m0-fa-on` won at
24,647.316788 t/s. That is a surface-local observation, not authority to change global build defaults.

Ranking now also has a device-local absolute-duration admission. RVP-C3-5 derives a
**250,090,903 ns** minimum complete repetition window from the first nominal-SCLK observation in the
RVP-T0-1 gfx90a receipt. Missing, foreign-device, malformed, or shorter live GPU windows receive no
speed rank even if their relative noise looks small. The focused implementation tests pass 11/11.
The experimental producer is still uncommitted under its explicit per-commit approval boundary.

C4 now crosses from deterministic profile evidence into the authoring loop without granting the
profile authority over a decision. The hash-bound `profile_context.py` bridge emits a priced discovery
block plus a framework-neutral `c4_evaluator_observation.v1`; both are `diagnostic_only`, retain the
report/manifest/formal-profile hashes, and cannot write a verdict or rank. Prompt hygiene also excludes
sealed evaluator paths. The generalized capture runner holds mapping and formal invocations to one
backend process, validates exact argv and quant selection, retains every artifact on failure, and uses
the existing deterministic report rather than exposing raw profiler text to the agent.

The first live op-level captures bound what that signal can presently say. At fixed
`m=16,n=1,k=256`, Q4_K and Q8_0 both produced complete fill → requantize → `mul_mat_vec_q` sequences.
Matvec occupied **41.95% versus 40.92%** of wall time and averaged about **5.72 versus 5.50 µs** per
dispatch. This small surface neither explains the 35→50 Q4_K roofline rung nor attributes unpack work
inside the fused kernel, so the representative-shape counter/source-timer question remains open.
IQ2_XXS is a durable tool boundary: ten unprofiled repetitions pass, but active `rocprofv2` capture
exits 139 even in one process. That failed receipt is evidence about profiler scope, not an
architectural bandwidth floor; the next IQ2 probe must use a non-`rocprofv2` device timer/counter path.

CPU baseline honesty now has the same exact-surface rule. On Qwen2.5-Coder-0.5B Q4_K_M prefill,
implicit AUTO measured **5,569.96 t/s**, explicit flash-attention ON **5,451.90 t/s**, and explicit
OFF **2,741.09 t/s** across randomized 30-repetition hardened arms. AUTO behaves like ON here, but
that observation does not authorize an implicit or portable default. The evaluator now requires both
provider arms on one identical model/quant/op/shape/dtype/build/factor surface, selects by declared
metric direction, and rejects any transfer to a different candidate surface.

The historical CPU fan-out shapes are execution capacity, not ranking capacity. Against the
full-machine anchor/IQK-off/flash-attention-off order, depth 4 retained Spearman 1.0, but depths 8,
16, 32, and 48 fell to 0.5. More decisively, every split failed the predeclared combined
package-power/frequency acceptance: maximum anchor lane-position deviations ranged from **16.28% to
77.43%** against a 10% limit, while loaded-frequency ratios ranged from **0.743 to 0.829**. The first
real CPU candidate must therefore rank on the full host unless a narrower change-class calibration
later clears the same gates.

Two Q4_K MMQ diagnostics narrowed the still-open correctness repair without fixing it. Disabling the
gfx90a MFMA route and forcing DP4A still failed **25/43** cases (maximum ratio 3.0178), excluding an
MFMA-only defect. A Q4_K-only least-squares refinement of the per-32 Q8 activation scale also failed
**25/43** (maximum ratio 2.8834) and was reverted. The clean 43/43 rocBLAS control and fixed κ=1.5
remain; the search must move below both the implementation choice and a one-parameter scale repair.

### Source References (2026-08-11 AutoKernel correctness)

- [AutoKernel research loop](../handoffs/active/autokernel-research-loop.md) — live checkpoint,
  baseline-honesty receipts, independent fp64 oracle, and next calibration step.
- [ROCm verify/profile backend](../handoffs/active/rocm-verify-profile-backend.md) — RVP-C2-5 triad
  contract, MMQ-isolated Q4_K finding, duration-window admission, and producer boundary.
- [Progress 2026-08-11](../progress/2026-08/2026-08-11.md) — exact live counts, seed, receipt flags,
  C4 receipt hashes and bounded results, runner paths, fixed-gate dispatch finding, and verification
  results.

## Compiled Update — 2026-08-03 (the AMD deficit is a QUANT deficit, not a device deficit; and the compute roofline, finally computed)

**Confidence: mixed and stated per claim — the attainment ladder is `observation` (our own measured
throughput, recomputed on one consistent basis, against a *spec* denominator); the compute-roofline
constants are `[D] derived` from vendor spec, not measured.**

### The finding that reframes the whole GPU program

We had been reading a large llama.cpp-on-AMD-vs-NVIDIA gap as an AMD problem. Recomputing our own
numbers on one consistent basis says otherwise:

| Rung on our MI210 | Bandwidth attainment |
|---|---|
| fp16 | **62.6%** |
| fp16, vLLM-ROCm, same device | **69.2%** |
| Q8_0 | 50.2% |
| Q4_K | 35.1% |
| MoE-Q8 (frontdoor) | 21.3% |
| **MoE-IQ2 (architect)** | **10.3%** |

**62–69% is already reached on this silicon, so the memory system is not the limiter.** The collapse is
entirely down the quant ladder, inside `mul_mat_vec_q`, which is **77.8% of decode time**. For
calibration, DGX Spark GB10 reaches **77–80% at Q4_K_M dense across five models on the same engine** —
NVIDIA's quant sag is 5–10 pp; ours is 27 pp. The gap is in the low-bit path, and it is ours to close.

**The denominator was measured the same day (2026-08-03): achievable = 1433.3 GB/s, 87.5% of the
1638 GB/s datasheet peak** — high for HBM2e. Correction factor **1.143×**, so fp16's 62.6%-of-spec is
**71.5%-of-achievable** and Q4_K's 35.1% is 40.1%. The prior estimate (~1.3–1.4 TB/s, a 17–26% rise) was
**low**, and it is worth recording that the guess erred in a knowable direction: HBM2e on a well-tuned
part attains more of its datasheet than the folklore figure suggests.

**⚠ And the thing that is easy to get wrong: this does NOT narrow the AMD-vs-NVIDIA gap.** Converting our
numbers to an achievable basis while a competitor's stay on a spec basis makes the gap *look* smaller
without it *being* smaller. The cross-vendor comparison must stay **spec-to-spec** — our 62.6% against
DGX Spark's 77–80%, both against datasheet — until somebody measures GB10's achievable bandwidth. Use the
achievable basis for headroom and campaign sizing; use the spec basis for comparison; **always say which
one you used.** This is the same failure mode as the vendor-KB defect two paragraphs down, where a
per-OAM TFLOPS figure was divided by a per-GCD bandwidth to give a ridge point off by 2×.

### The compute roofline, which nobody had computed

`[D]` derived from AMD spec; all four rates reproduce published figures exactly:

**181.0 TFLOPS fp16/bf16 = 181.0 TOPS int8** — **CDNA2 does not double int8**, and there is **no FP8, no
FP4, no TF32**. fp32 matrix 45.3 / vector 22.6. **Ridge point 110.5 FLOP/byte** (vs 281 for an RTX PRO
6000, so **the MI210 is the more bandwidth-balanced part** — a bandwidth-directed program is the
arithmetically correct one here).

Two consequences that convert standing puzzles into closed questions:

1. **`MfmaUtil ≈ 0%` at batch-1 is correct behaviour, not a defect.** Batch-1 arithmetic intensity is
   1.0–5.2 FLOP/byte, **31–113× below the knee**; the matrix units cannot exceed ~1.7–3.2% busy *at any
   bandwidth*. Authoring MFMA decode kernels returns **zero, with certainty**.
2. **The batch knee is predictable**: `B* = 110.5 × bytes_per_weight / 2` → Q4_K 31, Q8_0 59, bf16 110 —
   which **retro-predicts the bf16 knee we had already measured at B≈96–128**. Above `B*`, bandwidth
   attainment stops being the right ceiling.

**Do not import AMD's own ridge figure.** Their GEAK `cdna2_mi200/memory.md` computes 226 FLOP/byte
per-GCD from a TFLOPS number its own `arch.md` labels per-OAM — **off by 2×**. Use ~110–113. A vendor
knowledge base is useful and is not authoritative.

### Closing the vLLM gap is not a kernel goal

At batch-1, llama.cpp is **0.1–5.8% faster** on an RTX 4090 and comparable on an H200; vLLM leads by
**+11% on our MI210**, and *that 11% is the kernel delta*. The headline 24–44× arrives only at **16–64
concurrent users** and is continuous batching, PagedAttention and the scheduler — a serving-runtime
property, not a kernel one. Caveat worth carrying: every public batch-1 head-to-head is at **16-bit**,
i.e. exactly where our gap is not; **the quantized-vs-quantized comparison has never been run anywhere.**

### Every roofline denominator is now measured, and one of them was wrong by 2.2×

**H2D 28.89 GB/s · D2H 28.20 GB/s** on the MI210's PCIe Gen4 x16 link — **91.7% / 89.5% of the 31.5 GB/s
theoretical**, with a clean saturation curve (25.40 at 1 MB → 28.89 at 128 MB). This **retires a ~64 GB/s
figure** that had been circulating in our own docs and underpinning CPU-side-KV and offload arguments. It
was wrong twice over: a **Gen5 number on a Gen4 link**, and a **bidirectional-aggregate number applied to
one direction**.

**Bulk host↔device transfer is NUMA-node-independent** — all four nodes agree to within 0.1%. So
cross-node host-thread placement costs nothing *on the transfer path*, which is a narrower claim than it
sounds: it says nothing about host-side memory access during serving.

The general lesson, and it generalises past this card: **a bandwidth figure carries three attributes that
are all easy to drop — its link generation, its direction, and its basis.** Every one of those was wrong
somewhere in our own documentation, and each error survived because the number looked plausible. When a
transfer figure is quoted, it should be impossible to tell which of unidirectional / bidirectional /
theoretical / measured is meant only from context.

**A related trap, from the same sweep:** the same "~64 GB/s" string also appears in this project attached
to **xGMI inter-socket** bandwidth — a completely different link. Correcting those alongside the PCIe ones
would have been a category error. *Grep-and-fix on a number is not a correction; grep-and-fix on a
number's referent is.*

### gfx90a is commercially abandoned, not technically incapable — and the distinction is the whole plan

Corrected, with mechanism: gfx90a **does** have direct global→LDS (LLVM `FeatureVMemToLDSLoad` sits
inside `FeatureGFX9`; AMD's own CDNA2 doc says so; and our tree already calls the intrinsic). What it
genuinely lacks is the **async DMA engine** and the **SMEM-operand matrix instruction** — different
limitations with different consequences. Meanwhile AITER's supported-hardware table lists **no
MI210/MI250/gfx90a, not even experimental** (consumer RDNA parts rank ahead of our datacenter card),
TileLang is CDNA3-limited, and the quantization×kernel co-design school is ROCm-excluded across the
board. **Nobody will port anything to this card for us**, which is the premise the autokernel program
exists to answer — not a reason to stop.

Free transferable science, arch-independent, applicable today: **do not wave-specialize** (AMD statically
partitions registers across waves — 4 producers 893 TFLOPs vs 0 producers **1610**); prefer **8-wave
ping-pong** over 4-wave interleave (~90% of the performance at ¼ the code); **swizzle HBM-side, not
LDS-side**; HIPCC **will not feed AGPRs to MFMA** even though the hardware allows it; and grid-swizzle
WGM must be **swept, not set** (+9.6% at 8, **−13.9% at 32**).

## Compiled Update — 2026-07-31 (gfx90a ARGSORT defect: a green test suite hid an invalid kernel launch)

**Confidence: verified — measured on this host, third-party repo, production kernel untouched.**

Fixing TTS on the MI210 (see [Multimodal](multimodal.md) for the end-to-end speech-stack story)
required a real kernel fix, but not to *our* kernel: the third-party `qwentts.cpp` / vendored `ggml`
fork carried a gfx90a `ARGSORT` defect that also explained an unrelated, previously-unresolved HIP
graph-capture abort on the same fork.

### The defect: a thread-count launch bug that a "passing" test suite could not see

At `ne0=2048`, the fork's `ARGSORT` kernel launched **2048 threads per block against gfx90a's
1024-thread-per-block hardware cap** — an invalid launch, repeated **705× per synthesized
utterance**. `test-backend-ops` reported ARGSORT **46/46** and TOP_K **170/170** passing throughout,
because the failing shapes were **silently skipped**, not exercised. A green suite is not evidence
the covered shapes are the shapes that matter in production — this is the same class of trap as a
filtered log masking a working codepath, mirrored onto a test harness that filters the *inputs*
instead. The fix was a **thread-strided bitonic sort**, gated to the shapes that exceed the
1024-thread cap. Post-fix, `test-backend-ops` passes ARGSORT **74/74** and TOP_K **292/292** — the
count increase itself is the evidence that previously-skipped shapes are now exercised, not just that
existing cases still pass.

### HIP graphs were never a separate bug

The MI210 HIP-graph-capture abort on this fork — previously an open, unexplained failure — was
**downstream of the invalid ARGSORT launch**, not an independent graph-capture defect. With ARGSORT
fixed, graph capture on this fork works, is **13.2% faster**, and produces **bit-identical output**.
This generalizes the production-kernel finding immediately below (2026-07-11): HIP graphs are a clean
win once the underlying kernels are launch-valid; when they are not, the graph-capture layer is where
the failure surfaces, which can misdirect debugging toward "graphs are broken" when the actual defect
is upstream of graph capture entirely.

### Scope: a third-party fork, not the production kernel

This defect and fix live entirely inside `/mnt/raid0/llm/qwentts.cpp`'s vendored `ggml` (fork pin
`c044c6f0`), never in the frozen `production-consolidated-v8` tree (`67a433bf4`, untouched
throughout). Per the experimental-kernel workflow in `CLAUDE.md`, that four-step workflow (pull
fresh production → build → validate → deploy as a new production version) governs **our** kernel
tree; a patch inside a third-party repo's vendored copy is not in that tree and required no
experimental-kernel handoff. The operator's decision is to carry `qwentts.cpp` as a **pinned
versioned dependency** (pins: qwentts.cpp `abab6b3b`, ggml fork `c044c6f0`, binary md5
`5b858d75614dfd2f696071212ae8f2e4`) rather than merge it into the production llama.cpp fork; see
[Multimodal](multimodal.md) for the full TTS measurement story this defect unblocked (xRT 0.86×→5.47×,
`CodecDecode` share 64%→10.4%).

### Source References

- [`progress/2026-07/2026-07-31.md`](../progress/2026-07/2026-07-31.md) — §15c, the ARGSORT mechanism, the 74/74 / 292/292 counts, and the 13.2% HIP-graphs figure
- [`multimodal-pipeline.md`](../handoffs/active/multimodal-pipeline.md) — task S-6a (the ARGSORT fix closure) and S-3 (the one-line FP8-guard patch, a related but distinct third-party build fix on the same fork)
- [`master-handoff-index.md`](../handoffs/active/master-handoff-index.md) — row **N27** (speech)

## Compiled Update — 2026-07-30 (NUMA placement defect; the E5 quarters-vs-full verdict is RETRACTED)

Two of the 2026-07-24 findings below are **withdrawn, not revised**. The E5 W0 grid measured
every "full/half" placement through `stack_numa.py`'s `NUMA_NODE0 = "0-47,96-143"` — an
**NPS2-era name that spans two NPS4 nodes** — launched with no `numactl` policy, so the
big-instance arms were priced at roughly half their true speed while the quarter arms
(which *are* node-aligned) were priced correctly. Every "quarters win" conclusion drawn
from that grid is an artefact of the handicap, not a result.

Live NPS4 topology, re-read 2026-07-30: `node0 = 0-23,96-119`, `node1 = 24-47,120-143`,
`node2 = 48-71,144-167`, `node3 = 72-95,168-191`. Only the `NUMA_Q*` quarter constants are
node-aligned. Canonical single-instance placement is full machine `taskset -c 0-95` +
`numactl --interleave=all`.

Confidence: **`observation` for every corrected number below.** The protocol that would make
them decision-grade — `P-BENCH-PLACEMENT-1`
(`epyc-inference-research/docs/protocols/numa-placement-measurement-protocol.md`) — has a
MEASUREMENT.md registry entry that is **STAGED, not applied**. Nothing in this section may
gate a keep / revert / deploy / promote decision.

### Key Findings (2026-07-30)

- **RETRACTED: "C3 (4×quarters) is aggregate-throughput-optimal for every model."** At
  *matched total concurrency* `T`, one full-machine instance beats four quarters at every
  rung measured: `T=4` **79.7 vs 52.9**, `T=8` **105.1 vs 81.0**, `T=16` **131.0 vs 108.4**,
  `T=32` **145.9 vs 143.8** aggregate tok/s. The 2026-07-24 comparison was not `T`-matched
  and its full/half arms carried the straddling-cpuset handicap. Observation-grade.
  [numa-placement-defect-20260730](../handoffs/active/numa-placement-defect-20260730.md)

- **RETRACTED: "the dense-27B 1×big shape question is resolved — NODE0-local half beats
  full-machine+interleave, and the April 2026 cache-locality finding reproduces."** The
  "NODE0-local half" was never node-local: `0-47,96-143` straddles `node0`+`node1`. The
  April 2026-04-17 head-to-head it claimed to reproduce is **not valid evidence** — it
  predates the 2026-04-24 NPS4 reboot (when that cpuset genuinely *was* one node) and its
  source CSV records `spec == "baseline"`, i.e. speculative decoding OFF. The dense-27B
  shape question is **re-opened, not resolved**.

- **Both directions of this claim have been asserted from the same defective grid.** This
  wiki previously said quarters/half win; the published operator artifact previously said
  the opposite. Neither disagreement was informative — both were readings of a grid whose
  big-instance arms were handicapped, so the sign of the comparison was set by which arm a
  given pass happened to emphasise, not by the machine.

- **Two production roles are genuinely mis-wired; the fleet is not.** `frontdoor`
  (Qwen3.6-35B-A3B-Q8_0) measures `10.83 ± 0.04` tok/s as wired vs `23.36 ± 0.11` at
  canonical placement (**2.16×**, `llama-bench` tg128, spec-dec off, `r=10`, `drop_caches`
  before every arm, kernel `production-consolidated-v8` / binary `10107`);
  `ingest_long_context` (Qwen3-Next-80B-Q4_K_M) measures `12.42 → 22.92` (**1.85×**).
  `worker_general` and `architect_general` already run `0-95` + `interleave=all` and are
  **correct** — this is a two-role defect and must never be stated fleet-wide.

- **Shared mmap makes fleet placement depend on instance START ORDER.** GGUF pages are
  placed once, by whichever instance faults them in first; later instances inherit that
  placement regardless of their own `--membind`. Four quarters measured
  **25.6 / 25.6 / 24.2 / 26.9 %** node-local under shared mmap vs **100 % each** under
  `--no-mmap`, with fleet decode `40.91 → 52.13` tok/s. A quarter fleet therefore does
  *not* reliably get interleaved pages — it gets whatever the first loader chose.

- **The `stack_numa.py` wiring change is NOT authorised.** The file carries corrected
  comments only and is deliberately behaviourally unchanged, pending the inference owner
  and the stack gates.

## Compiled Update — 2026-07-29 (GPU topology ground truth; E5 still scout-only)

This pass records two corrections and one **status clarification that supersedes any
reading of the 2026-07-24 entry below as a settled result**. The corrections are to the
machine's own topology description; the clarification is that **E5 has produced no
decision-grade cell at all** — the 2026-07-24 W0 numbers were and remain scout-grade,
and the Stage-B waves that would confirm or overturn them have not run.

Confidence: `verified` for the sysfs/`numactl` topology facts and the landed doc-debt
findings; `observation` for every throughput figure carried forward from W0; the
device-local placement question is **unmeasured** and is labelled as such below.

### Key Findings (2026-07-29)

- **The MI210 is attached to NUMA node 1, not node 3 — a premise that had been inherited
  and propagated unchecked.** Ground truth read from sysfs: `/sys/class/drm/card2/device`,
  device id `0x740f`, `numa_node=1`. Consequence: the lane's measured 184-191 host-thread
  placement (which folds to physical cores 88-95 = region `q3`) **is already cross-node
  today**. Its authority is therefore **measured lineage** — every np×context ceiling was
  derived with the threads exactly there — **not device locality**. The distinction is
  load-bearing: lineage is a reason not to move the threads without re-deriving the
  ceilings, whereas locality would have been a reason they *belong* there. Only the first
  is true. [gpu-serving-tie-in-program](../handoffs/active/gpu-serving-tie-in-program.md),
  [progress 2026-07-29](../progress/2026-07/2026-07-29.md)

- **Device-local host-thread placement has never been tried, so scattered placement is not
  disqualified by physics — the current configuration is itself the existence proof.** The
  only comparison ever made was 184-191 vs 88-95, *both* inside `q3` and *both* cross-node.
  Node-1-local candidates (SMT ids within 120-143) are untested. The unmeasured costs are
  pinned-buffer DMA locality (`hipHostMalloc` first-touch scatters staging buffers) and,
  more plausibly, cache-line ping-pong on the submission state the 8 host threads share
  when spread across nodes. The upside is symmetric — the lane might get *faster* — which
  is why the P2-5j placement sweep is sequenced **before** any `q3` carve is minted.
  [gpu-serving-tie-in-program](../handoffs/active/gpu-serving-tie-in-program.md)

- **Documented topology invariant is wrong in code comments: `stack_numa.py:26` claims 2
  NUMA nodes while `numactl -H` reports 4 (NPS4).** Filed as P2-5l (behaviour-neutral, plus
  a stale 12.19 t/s comment) rather than edited in place, on the reasoning that a
  misdocumented topology invariant is how the next placement defect gets built.
  [progress 2026-07-29](../progress/2026-07/2026-07-29.md)

- **E5 status, stated plainly: W0 scout is still the only E5 data that exists. W1-W4 are
  `BLOCKED_ON_OPERATOR_SCHEDULED_REBOOT`.** The P-BENCH-1/3 one-week uptime boundary is a
  hard gate and reboots are operator-only. No Stage-B cell has been measured, so **none of
  the pre-registered R1-R4 questions (crossover K\*, lane verdict, provisioning rows) has
  an answer**, and the 2026-07-24 directions below remain hypotheses. Post-W0 work was
  preparation only: all four W0 runs now carry **observation-grade** `offline_scores.jsonl`
  with provenance (2,967 saved responses) and a Stage-B prune plan
  (`stage_b_prune_plan.json`, SHA-256 `9b4d4f03…96b8`). W2's Gemma group is **invalid for
  any quality interpretation** — 430/430 parse failures with no raw SSE ledger,
  unrecoverable — and W4's high-K `raw_fallback` rows are demoted from decision-grade use.
  **Re-attributed 2026-07-29** (research `5d6a17f2`): the capture parser bug was real and
  is fixed, but the token budget was consumed because the harness emitted no `--reasoning`
  flag, so gemma4 ran at llama-server's `auto` default (ON for `arch=gemma4`) while both
  model registries record `reasoning: 'off'` — the runs were not on the production recipe.
  The capture fail-close **detects** that, it does not **prevent** it; without
  `--reasoning off` a W2 run fails closed again at ~41/43.
  [batched-decode-measurement](../handoffs/active/batched-decode-measurement.md)

- **A decision-grade CPU anchor did land for the A4 optimized-serving shape, and it is
  proposal-only.** FG-4b run `fg4b-a4-cpu-optimized-server-20260729T110152Z`:
  `13.1599 tok/s` median, MAD `0.01633`, over five exact 512-token server decodes, all
  terminating on `length`, with a ratified affinity receipt and verified teardown. The
  generated registry patch was **not applied** — the evidence exists, the deployment does
  not. [gpu-serving-tie-in-program](../handoffs/active/gpu-serving-tie-in-program.md),
  [progress 2026-07-29](../progress/2026-07/2026-07-29.md)

- **Two quantities the program explicitly refuses to quote as results.** (1) Shed-batch net
  benefit is `(GPU gained − q3 CPU lost)` and is **never measured** — recorded so that "do
  not build the shed-batch class" can be a measurement outcome rather than the reversal of
  a shipped feature. (2) The 122B-at-72-threads/3-quadrant figure **does not exist**; a
  −10% to −40% band was bounded by a reviewer who declined to narrow it without data. A
  bound is not a result. [gpu-serving-tie-in-program](../handoffs/active/gpu-serving-tie-in-program.md)

### Open Questions (2026-07-29)

- Does device-local (node-1) host-thread placement beat the incumbent 184-191? Untested;
  P2-5j is the sweep that would answer it, and it gates the carve decision.
- Where is the E5 crossover K\*? Still unanswered — and will stay unanswered until Stage-B
  runs post-reboot, with W2 additionally gated on a focused SSE capture smoke.
- Does the historical placement-sensitivity prior (+184% from wiring alone, Probe B
  2026-05-04) still hold on v8? It is cited for **shape direction only** and is pre-era.

### Source References (2026-07-29)

- [gpu-serving-tie-in-program.md](../handoffs/active/gpu-serving-tie-in-program.md) — MI210
  node-1 ground truth, lineage-not-locality placement authority, P2-5j sweep sequencing,
  FG-4b decision-grade re-anchor, the never-measured shed trade and the non-existent 122B
  quadrant number.
- [batched-decode-measurement.md](../handoffs/active/batched-decode-measurement.md) — E5
  wave status (W0 only; W1-W4 blocked), offline-score provenance, W2 Gemma quality
  invalidity, W4 raw-fallback demotion, Stage-B prune plan hash.
- [progress 2026-07-29](../progress/2026-07/2026-07-29.md) — the topology-correction arc
  and the P2-5j/k/l/m filings, plus the FG-4b terminal entry.

## Compiled Update — 2026-07-24

The E5 NUMA×batch sweep (design frozen 2026-07-23) executed its W0 non-decision-grade scout across all four production model groups — the first empirical read of the full (N-instances × K-batch) grid since the v7/iqk kernel and the fleet-layer/lineup-restoration changes. In parallel, the GPU-only np×context throughput study was extended from the 122B-IQ2 architect candidate to all three GPU-fitting architect arms, producing the first cross-architecture comparison of how batching interacts with reasoning-budget/context length. Confidence: `observation` throughout — W0 is scout-grade by design (host uptime 20 days exceeded the one-week decision-grade policy, hence `--allow-host-health-warning`), and the np×context numbers are pre-`P-GPU-1` GPU throughput.

### Key Findings (2026-07-24)

- **⚠ RETRACTED 2026-07-30 — do not cite this bullet.** The grid it summarises measured its
  full/half arms through the straddling `NUMA_NODE0 = "0-47,96-143"` cpuset with no `numactl`
  policy, handicapping them by up to 2.16×; the quarter arms were node-aligned and unhandicapped.
  At matched total concurrency one full-machine instance **wins at every rung** (T=4 79.7 vs 52.9;
  T=8 105.1 vs 81.0; T=16 131.0 vs 108.4; T=32 145.9 vs 143.8 tok/s — observation-grade,
  `P-BENCH-PLACEMENT-1` registry entry STAGED not applied). See
  [Compiled Update — 2026-07-30](#compiled-update--2026-07-30-numa-placement-defect-the-e5-quarters-vs-full-verdict-is-retracted)
  and [numa-placement-defect-20260730](../handoffs/active/numa-placement-defect-20260730.md).
  Original text retained below for the record:

- ~~**E5 W0 scout: 69/69 cells clean, and "one big batched server vs quarter-batched servers" resolves to quarters-win, universally, at scout scale.**~~ All four model groups (`qwen36_q8_0` 35B-A3B frontdoor, `gemma4-26B-A4B` worker, `qwen36_27b_q8` dense-27B control, `qwen3_next_80b` ingest) completed. ~~**C3 (4×quarters) is aggregate-throughput-optimal for every model**~~ (RETRACTED 2026-07-30): qwen36 2028 tasks/hr @np4, gemma 5076 @np8 (1.78× the interleaved full at iso-total=32), dense-27B 1415 @np2, 80B 2520 @np4. This directly answers E5's pre-registered R1 "crossover" question at scout resolution: no model shows a big-instance win at any measured K. [batched-decode-measurement](../handoffs/active/batched-decode-measurement.md), [progress 2026-07-24](../progress/2026-07/2026-07-24.md)

- **⚠ SUSPENDED 2026-07-30 (same defective grid).** Both "half" arms in this bullet are the
  straddling `0-47,96-143` / `48-95,144-191` cpusets with no `numactl` policy, so the C1b-vs-C1
  comparison is between two handicapped shapes and its direction is not trustworthy. Treat as
  hypothesis pending re-measurement under `P-BENCH-PLACEMENT-1`.

- **The 2×half whole-machine provisioning candidate (C1b) is confirmed MODEL-DEPENDENT, not universally negative.** For the 35B-A3B MoE frontdoor model, C1b loses to the single-half C1 (1198 vs 1610 tasks/hr) — reproducing the 2026-05-26 dual-half negative result (co-run ≈0.5×, memory-channel contention) on the current v7 kernel. But **C1b wins for the dense 27B control (1009 vs 849) and the 80B SSM-hybrid ingest arm (2013 vs 1700)** — the opposite direction. This falsifies the assumption that the dual-half penalty generalizes: it is specific to the small-active-MoE shape, and dense/large models profit from the second NUMA-local half. This is new information the single 2026-05-26 measurement (frontdoor-shaped model only) could not have shown. [batched-decode-measurement](../handoffs/active/batched-decode-measurement.md)

- **⚠ RETRACTED 2026-07-30 — the dense-27B shape question is RE-OPENED, not resolved.** The
  arm labelled "NODE0-local half" was never node-local: `0-47,96-143` straddles `node0`+`node1`
  on this NPS4 host and ran with no `numactl` policy, so its full-machine comparator was the
  only correctly-placed arm in the pair. The "April 2026 cache-locality finding" it claimed to
  reproduce is **invalid twice over**: the 2026-04-17 head-to-head predates the 2026-04-24 NPS4
  reboot (the cpuset genuinely *was* one node then), and its source CSV records
  `spec == "baseline"` (speculative decoding OFF). Directly-measured, T-matched replacement
  data has the full-machine instance ahead at every concurrency rung (observation-grade,
  `P-BENCH-PLACEMENT-1` STAGED not applied). Do **not** adopt half0 as a Stage-B C1 anchor.
  Original text retained for the record:
  ~~"The dense-27B '1×big' shape question is resolved: NODE0-local half beats the
  full-machine+interleave instance, at both low and high concurrency. Scout pair-answer: half0
  751/814 tasks/hr (K=1/K=8) vs full-machine+interleave 574/611 — the April 2026 cache-locality
  finding reproduces for the dense-27B control on v7. Stage-B for the dense arm now adopts half0
  as its C1 anchor."~~ [batched-decode-measurement](../handoffs/active/batched-decode-measurement.md), [numa-placement-defect-20260730](../handoffs/active/numa-placement-defect-20260730.md)

- **Cross-architecture np×context throughput surface (GPU-only, all three architect candidates): batching is fundamentally architecture-dependent, and the earlier "don't batch long-context" rule was over-generalized from a single outlier arm.** Extending the initial 122B-IQ2-only np×context sweep to the 27B-dense (A3) and 35B-A3B (A4) candidates, each at its own max-opt MTP depth (see [Speculative Decoding](speculative-decoding.md)): peak aggregate decode t/s ranks **A4 (small-active MoE) ≫ A3 (dense) > A1 (large-active IQ2 MoE)** at every batched operating point (e.g. at a 2k-token budget: 243@np32 / 153@np16 / 103@np32). **A1 is the sole outlier**, with both a universal np=2 dip AND a long-context batching collapse (net-negative at a 32k-token budget: np4=45.7 < np1=52.0 t/s); A3 and A4 both batch robustly (2.2–3.4×) at every measured budget up to 32k. The np=2 dip and the long-context collapse are therefore **A1-specific** (confounded across IQ2 quant / MTP-depth-2 / large-active-param count), not generic properties of MoE or of long context as first reported. Mechanism: dense models batch well via weight-reuse amortization (read weights once, apply across np tokens); MoE's fewer-active-params advantage only pays off at high np where expert reuse kicks in — exactly where A4 climbs to np=32 and A3 plateaus around np=8. Router rule, now per-architecture rather than universal: A1 never batch past np=8 (never np=2; np=1 at ≥32k budget); A3 batch all budgets, sweet spot np=8; A4 batch aggressively at all budgets up to np=32+. Binding constraint throughout is memory **bandwidth**, not VRAM capacity — KV read per decode step scales with context×active-slots and MoE requests scatter across experts, so aggregate throughput can drop as concurrency rises at large context even with plenty of VRAM headroom. [reasoning-effort-levels](../handoffs/active/reasoning-effort-levels.md) §TB-6-exec, [progress 2026-07-23](../progress/2026-07/2026-07-23.md)

### Open Questions (2026-07-24)

- E5 Stage-B (decision-grade, ≥8 reps, ~13 cells/model) is gated on an operator host reboot (20-day uptime exceeds the P-BENCH-1/3 one-week policy) — the W0 directions above are not yet decision-grade.
- Does the C1b dense/80B win generalize to other large dense or hybrid models, or is it specific to these two arms' memory footprints?
- The np×context router rule (TB-6-ROUTER) is gated on the GPU joining the orchestration stack as a serving backend — currently a bench instrument only.

### Source References (2026-07-24)

- [batched-decode-measurement.md](../handoffs/active/batched-decode-measurement.md) — E5 sweep design, harness (`server_numa_np_sweep.py`, 121-cell pre-registered grid), W0 scout execution + results across all four model groups.
- [reasoning-effort-levels.md](../handoffs/active/reasoning-effort-levels.md) §TB-6-exec — the cross-candidate np×context throughput surface (A1/A3/A4), architecture-dependence findings, per-arm router rules.
- [progress 2026-07-23](../progress/2026-07/2026-07-23.md), [progress 2026-07-24](../progress/2026-07/2026-07-24.md) — W0 execution log, instrument-chain fixes (think-truncation → production chat template, GPU-coexistence mode), overnight A2/RP-5 run.

## Compiled Update — 2026-07-20

New CPU-prefill and GPU-kernel evidence sharpens the roofline picture: **CPU decode is bandwidth-exhausted, but CPU *prefill* is a distinct, still-open compute-bound regime**, and the GPU *raw-speed* frontier is now considered structurally exhausted (the live GPU frontier is residency/teleport, not more kernel speed). All 2026-07 GPU throughput numbers remain **observation-grade** pending production-named `P-GPU-1` certification on `production-consolidated-v8`.

### Key Findings (2026-07-20)

- **v7 is promoted as `production-consolidated-v7`** — frozen at `experimental-v7-refresh-20260716 @ 6ad45fa3ff` (binary `10098`) and cut over on 2026-07-20. Banked, correctness-verified, runtime-gated-off wins: HIP per-decode graph capture **+25%** worker spec-dec (A4B MoE) / +4–14% base decode; MMVQ→MMQ small-batch verify-dispatch **+17.4%** MTP-verify / **+31.7%** gemma-31B; nwarps 2→4 +4.6%; async prefetch +3.3%; bf16 GDN recurrent-state **+21.5% @B32**; single-stream dense-Q8 **+37%** (29→40.4 t/s). K5 quality neutral (+0.0% MMLU-Pro/GPQA). ([v7-promotion](../handoffs/active/v7-promotion.md), [gemma-challenge-kernel-techniques-v7](../handoffs/active/gemma-challenge-kernel-techniques-v7.md))
- **v8 is the current frozen production kernel, `production-consolidated-v8`** — `67a433bf45a8a091d83b4ea0b32ff0735fd51800` / binary `10107`, ratified by [`ratify_v8_final_freeze_20260725.json`](../artifacts/operator/ratify_v8_final_freeze_20260725.json) (SHA-256 `e7fce2c5cd720940fc84b669f57b78a61589fd8baef9b4e03030ed0dc4a3175b`). `GGML_IQK=1` now covers IQ2/IQ3 and IQ4_XS; IQ1 remains non-accelerated. v7 (`6ad45fa3ff6718c07c000061dbc6e29c1771f6e3` / `10098`) remains the rollback/history anchor.
- **CPU prefill ≠ CPU decode roofline (verified).** Decode is DRAM-BW-bound (Qwen3.6-27B Q8 @96t = 0.17 IPC, 96.6% cycles memory-stalled); prefill is `M>1` GEMM, compute-bound. PC-0 confirmed positive: 122B architect Q4 `p8192` ≈ 108–122 t/s at 0.92–1.47 IPC, and prompt/prefill dominates wall-clock in the targeted large/long-context regimes (GLM-5.2 patch review 81% prompt-wall, ingest 31K 75.1%). ([cpu-prefill-compute-large-models](../handoffs/active/cpu-prefill-compute-large-models.md))
- **The CPU-prefill hot path is OpenMP barriers, not math.** Symbolized profiling (PC-3/PC-4j) attributes 38–44% of prefill to `GOMP_barrier`/`__kmpc_barrier` (libomp spin/pause), ~22% to MoE `mul_mat_id`, and only ~1–2% each to GDN/SSM/RMS. The first landed lever is a **default-off CPU `CONCAT` dim0 row-partition** (`GGML_CPU_CONCAT_DIM0_ROWS=1`, experimental commit `93d945885`) targeting the `conv_input` CONCAT barrier in shared `build_conv_state()`: measured `pp8192` **+3.2% to +9.1%** single-seq and batched `pl=2` prompt **+22% to +54%**, cutting the target CONCAT barrier sum ~99%. It was **not part of frozen v7**; it is now carried default-off in frozen v8, with no default-on claim (one decode-only row regressed −5.8%). ([cpu-prefill-compute-large-models](../handoffs/active/cpu-prefill-compute-large-models.md), [progress 2026-07-20](../progress/2026-07/2026-07-20.md))
- **GPU raw-speed frontier is structurally exhausted** (single-stream dense-Q8 at the +37% ceiling; occupancy rewrites + compact-LDS falsified; stream-K already the live Q8 MMQ path). K28 GDN long-prefill is now a measured no-go: direct attribution found 15.40% / 14.65% / 12.18% GDN share at 2K/8K/32K and only 11.55% / 10.99% / 9.14% optimistic 4×-op full-model ceilings. The declining ceiling fails its higher-EV admission bar, so no fused prototype is warranted. ([mi210-big-model-and-acceleration-roadmap](../handoffs/active/mi210-big-model-and-acceleration-roadmap.md), [K28 closeout](../handoffs/completed/k28-fused-chunked-gdn-kernel-research.md))
- **E5 NUMA×batch is the never-measured 2D cross** (specced, post-promotion, runs last): batching amortizes per-token weight reads and may shift CPU decode from BW-bound to compute-bound, flipping the NUMA-locality advantage at high `-np` K — the crossover sets the slot-fabric grid shape. ([batched-decode-measurement](../handoffs/active/batched-decode-measurement.md))

### Open Questions (2026-07-20)

- Should the `CONCAT` dim0 row-partition ever go default-on / fold into a future production kernel, given the one decode-only regression?
- Does a real fused chunked GDN recurrence kernel raise the K28 Phase-0 ceiling enough to justify weeks of work? (Blocked on direct ROCm profiler attribution — `rocprofv2`/`rocprof`/`omniperf` currently unavailable on the host.)
- Where is the E5 NUMA×batch crossover K (one big high-`-np` server vs quarter-batched servers)?

### Source References (2026-07-20)

- [cpu-prefill-compute-large-models.md](../handoffs/active/cpu-prefill-compute-large-models.md) — PC-0..PC-4 profiling: prefill is compute-bound, hot path is OpenMP barriers, CONCAT dim0 row-partition lever.
- [v7-stack-throughput-full-optimization.md](../docs/reference/v7-stack-throughput-full-optimization.md) — deployed-lane vs candidate-bench throughput table with provenance guards.
- [v7-promotion.md](../handoffs/active/v7-promotion.md) / [gemma-challenge-kernel-techniques-v7.md](../handoffs/active/gemma-challenge-kernel-techniques-v7.md) — banked runtime-gated-off wins + readiness gate audit.
- [mi210-big-model-and-acceleration-roadmap.md](../handoffs/active/mi210-big-model-and-acceleration-roadmap.md) — GPU raw-speed frontier exhausted; residency/teleport is the live frontier.
- [k28-fused-chunked-gdn-kernel-research.md](../handoffs/completed/k28-fused-chunked-gdn-kernel-research.md) + [progress 2026-07-20-k28](../progress/2026-07/2026-07-20-k28-fused-gdn-kernel-research.md) — GDN serial-dependency finding + measured no-go closeout.
- [batched-decode-measurement.md](../handoffs/active/batched-decode-measurement.md) — E5 NUMA×batch 2D sweep spec.

## Summary

The entire project is built around the AMD EPYC 9655 "Turin" processor: 96 physical cores (192 threads), 1.13 TB DDR5-5600 ECC across 12 memory channels (~460 GB/s theoretical bandwidth), and true 512-bit AVX-512 (not Intel's double-pumped variant). The storage layer is a 2x Solidigm P44 Pro 2TB NVMe RAID0 array delivering 12.5 GB/s sequential reads, enabling a 280 GB model to be mmap'd in about 22 seconds.

The single most impactful optimization discovered in this project is NUMA-aware CPU pinning. The EPYC 9655 runs **NPS4 — 4 NUMA nodes** since the 2026-04-24 reboot (`node0 = 0-23,96-119`, `node1 = 24-47,120-143`, `node2 = 48-71,144-167`, `node3 = 72-95,168-191`; ~290 GB each). *(Corrected 2026-07-30: this paragraph previously read "2 NUMA nodes (cores 0-47 and 48-95, with hyperthreads 96-191), each with ~566 GB of RAM" — an NPS2-era description that survived the reboot. The `stack_numa.py` constants `NUMA_NODE0 = "0-47,96-143"` and `NUMA_NODE1 = "48-95,144-191"` inherit the same stale naming and each span **two** NPS4 nodes; only the `NUMA_Q*` quarter constants are node-aligned.)* Running a model naively across all 192 threads yields dramatically worse performance than NUMA-pinned instances. For the 35B-A3B frontdoor model, 4 independent instances on NUMA quarters (48 threads each) achieved 49.66 t/s aggregate -- a 6.9x improvement over the 7.25 t/s baseline. **That 6.9× is a comparison against the 192-thread naive baseline, not against a correctly-placed full-machine instance**; at matched total concurrency a single `taskset -c 0-95` + `numactl --interleave=all` instance beats four quarters at every measured rung (see [Compiled Update — 2026-07-30](#compiled-update--2026-07-30-numa-placement-defect-the-e5-quarters-vs-full-verdict-is-retracted); observation-grade, `P-BENCH-PLACEMENT-1` STAGED not applied). Canonical single-instance placement is therefore full machine `0-95` + `interleave=all`, **not** "single-node pinning".

Three runtime settings are non-negotiable: OMP_NUM_THREADS=1 (llama.cpp handles its own parallelism; nested OpenMP can halve throughput), numactl --interleave=all for single-instance models (distributes data across all 12 channels), and using only physical cores (hyperthreading hurts inference due to cache contention). The production stack uses taskset -c for NUMA pinning since numactl --membind is blocked in the container environment, relying on first-touch memory policy instead.

The system's 1.13 TB RAM enables a HOT/WARM/COLD three-tier memory architecture. HOT models (~701 GB with multi-instance copies) are always resident with --mlock, eliminating 15-90 second cold-start penalties. WARM models load on demand via mmap from NVMe (~12 GB/s, so a 140 GB model loads in ~12 seconds). COLD models remain on disk. The 120 GB OS SSD is strictly protected -- a December 2025 incident where Claude Code filled /tmp/claude with 20 GB crashed the machine, prompting a three-layer defense (bind mount, real-time monitoring, emergency cleanup). Another incident in January 2026 demonstrated that pytest -n auto on a 192-thread machine spawns 192 workers, each loading ~3 GB of embedding models, exhausting the full 1.13 TB of RAM.

## 2026-07-19 Update — certification boundary after v7 readiness

- `P-GPU-1` is now ratified, but only production-named kernels can produce decision-grade MI210 throughput claims. Existing experimental-v7 Gate-R/K35/AXA rows remain observations and, at this 2026-07-19 boundary, required reruns on `production-consolidated-v7` with hardware, binary identity, host-interference, repetition, prompt/decode, draft-counter, and cleanup fields present. Current reruns must use the current production kernel named above. Sources: [P-GPU-1 ratification package](../docs/reference/p-gpu-1-ratification-package-2026-07-18.md), [P-GPU-1 amendment draft](../docs/reference/p-gpu-1-amendment-draft-2026-07-19.md), [v7 promotion](../handoffs/active/v7-promotion.md).
- OP-2 closed the CPU-regression check under the canonical measurement boundary: canonical CPU rows require the codified recipe, clean preflight, exact binary/repo identity, and attestation; ungrammatical numbers remain observations even when repeatable. This preserves the distinction between validating the candidate and certifying a production claim. Sources: [OP-2 canonical bench package](../docs/reference/op-2-canonical-bench-window-package-2026-07-18.md), [P-GPU-1 ratification package](../docs/reference/p-gpu-1-ratification-package-2026-07-18.md), [model-probe scoreboard](../docs/reference/model-probe-scoreboard.md).
- The practical implication is a two-stage GPU record: use experimental-v7 measurements to choose and debug levers, then rerun the promoted production-named kernel before using throughput to gate deployment, rollback, or promotion. Sources: [v7 promotion](../handoffs/active/v7-promotion.md), [P-GPU-1 ratification package](../docs/reference/p-gpu-1-ratification-package-2026-07-18.md), [Gemma v7 kernel techniques](../handoffs/active/gemma-challenge-kernel-techniques-v7.md).

## Key Findings

### 2026-07-16 — v7 refreshed candidate clears K5/readiness; MI210 validation must use candidate shared libraries

- **The refreshed v7 candidate is quality-neutral against production on the K5 gate, so the remaining promotion question is operational readiness/promotion policy rather than an observed suite regression.** The corrected chat-endpoint harness ran matched v6 and v7 candidate `8e5c555ab` windows on CPU-only temp servers. MMLU-Pro was `73/200=36.5%` on both arms, GPQA was `50/195=25.6%` on both arms, errors were `0`, and the comparator passed at the `-5pp` suite threshold. The old raw `/v1/completions` run is explicitly non-evidence because it used the wrong endpoint contract. Sources: [gemma-challenge-kernel-techniques-v7.md](../handoffs/active/gemma-challenge-kernel-techniques-v7.md), [progress 2026-07-16.md](../progress/2026-07/2026-07-16.md), `/mnt/raid0/llm/tmp/v7-quality-20260716-chat/v7_quality_gate_report.md`.
- **The v7 ROCm binary is valid on MI210, but only when its own shared libraries are first in `LD_LIBRARY_PATH`.** A sidecar initially reported no GPU devices because `llama-bench` resolved shared libraries from the production CPU tree. Re-running with `LD_LIBRARY_PATH=/mnt/raid0/llm/llama.cpp-experimental/build-hip/bin` made `llama-bench --list-devices` see `ROCm0: AMD Instinct MI210`; a bounded Gemma3 1B Q8 bench recorded `build_commit=8e5c555ab`, `backends="ROCm"`, `gpu_info="AMD Instinct MI210"`, prompt `15765.579 tok/s`, generation `197.773 tok/s`, and sampled GPU use `99%`. This is a deployment hygiene lesson as much as a GPU smoke. Sources: [gemma-challenge-kernel-techniques-v7.md](../handoffs/active/gemma-challenge-kernel-techniques-v7.md), [progress 2026-07-16.md](../progress/2026-07/2026-07-16.md), `/mnt/raid0/llm/tmp/v7-gpu-sidecar-20260716-corrected/bench-gemma3-1b-q8-ldpath.log`.
- **Stack-launched CPU roles must explicitly hide ROCm devices when using a HIP-capable binary.** The v7 server A/B showed HIP-visible defaults on a CPU role could touch ROCm and regress the worker path, while `--device none` plus `--device-draft none` restored production-shaped behavior. The orchestrator launcher now appends those flags for stack-launched text roles, including speculative launches. Sources: [gemma-challenge-kernel-techniques-v7.md](../handoffs/active/gemma-challenge-kernel-techniques-v7.md), [progress 2026-07-16.md](../progress/2026-07/2026-07-16.md).
- **The N5 acceptance gate finally closed on the patched v7 candidate, so the authoritative GPU-drafter checkpoint is the execute artifact, not the earlier preflight.** Commit `da1bf5e2f` fixed the `draft-tree` output-capacity abort, the rebuilt `build-hip/bin/llama-server` reports `10077 (da1bf5e2f)`, and `/mnt/raid0/llm/epyc-inference-research/data/specdec_frontdoor_alpha/n5_retest_v7_execute_20260716T190836Z/summary.json` is `decision_grade=true` with `n5_spec_on` `376/376`, `positive_mtp` `355/401`, and `spec_off` `0/0`. Sources: [gpu-drafter-mi200-investigation.md](../handoffs/active/gpu-drafter-mi200-investigation.md), [Progress 2026-07-16](../progress/2026-07/2026-07-16.md).

### 2026-07-06 — production-consolidated-**v7 candidate** built + validated (CPU-iqk + GPU-opts lines reconciled, zero conflict) + experimental-kernel-immutability workflow + verified aggregate spec sheet — ⚠️ COMPILE-FLAGGED FOR HUMAN REVIEW

> **Review flag (project-wiki writer-evidence policy):** model-compiled from the v7-candidate reconciliation session; **not adopted until human or measured review**. The reconciliation audit is a git-fact audit (read-only, `git -C … ` only — no builds/inference); every throughput number is an **OBSERVATION** (single MI210, serial, seed 42, no P-GPU-1 per MEASUREMENT.md). Sources: [kernel reconciliation audit](../handoffs/completed/kernel-reconciliation-audit.md), [tree-draft forward-port plan (Phase-1a result)](../handoffs/active/tree-draft-forward-port-plan.md), [findings-05c lever × category matrix (v7-candidate aggregate table)](../handoffs/active/fable5-window2-findings-05c-mi210-lever-category-matrix.md), [progress 2026-07-06 v7-candidate + GPU levers](../progress/2026-07/2026-07-06-v7-candidate-and-gpu-levers.md).

- **The two divergent optimization lines reconcile into a v7 candidate with ZERO merge conflict — because the GPU (`ggml-cuda`) and CPU/server (`ggml-cpu/iqk` + `tools/server/*` + `src/llama-kv-*`) subsystems are DISJOINT.** A read-only audit fixed the exact fork point (`f8cc15f16`, 2026-06-22 — *before* iqk landed on prod 2026-06-25) and enumerated both directions: the experimental GPU-opts branch was silently missing **~4 CPU-only/server-side items** from prod (dominated by the **iqk AVX-512 CPU GEMM subsystem** — 7 commits, 40,541 insertions in `ggml-cpu/iqk/*` — plus Expected-Attention KV compaction `3f9df4bd3`, an IMROPE guard relax, a slot force-release fix; **zero GPU-relevant**), while prod was missing the **4 gfx90a GPU opts**. The *only* file touched by both lines is `ggml-cuda/vendors/hip.h` (the fp8 ROCm≥6.3 guard), and its diff is **byte-identical on both sides** → a no-op conflict. So the real v7 integration risk is not merge conflict but the combined flag-set build/runtime interaction (`GGML_IQK` + `GGML_CUDA_Q8_PREFETCH` + `GGML_CUDA_GDN_STATE_BF16` coexisting). **Nothing valid is stranded** — every landed optimization is committed on a real branch (the one uncommitted tracked diff on disk is DFlash, HELD/out of scope; the reverted CPU work — CPU2 AVX-512BW repack, CPU1/CPU4 CCD threadpool, CPU paged-attn — is net-absent from prod too and re-port-from-history, not drop-in). The lone non-resolving cited token `a8afd338` is a session/thread marker, not a git ref; its underlying optimizations all resolve to real commits.
- **The v7-candidate was actually built + validated on HIP — the reconciliation is not just a paper audit.** Branch `experimental-v7-candidate` in `llama.cpp-experimental` (commit `46f876c12`) = fresh `production-consolidated-v6` (upstream + native MTP/NEXTN + our CPU kernels + iqk) **+ the 4 gfx90a GPU opts + the tree-draft engine**, applied with zero conflicts, and **iqk + all 4 GPU opts + tree-draft compile/link clean** together. This closed a stale-fork bug: the GPU-opts branch had forked before iqk, so it had silently been missing the entire iqk CPU GEMM subsystem.
- **The refreshed v7 branch is current again, not a stale fork.** `experimental-v7-refresh-20260716` was committed at `8e5c555ab` and merged `origin/master` `a8dc0e326`, restoring upstream freshness including `Q2_0` support while keeping the K14 backend-ops fix (`99f3fffd6`) intact. Candidate validation passed on MI210: `ggml-hip`, `llama-server`, focused EXPM1 backend-ops (`2/2`), and full `test-backend-ops` (`100%`, `734.97 sec`). The practical effect is that the onegraph/HIP graph findings now sit on a fresh upstream base rather than a pre-Q2_0 snapshot.
- **All 4 gfx90a GPU opts survived the fresh-pull onto v6+iqk (regression-validated), and the deployed roles inherit them.** The opts (already documented in the 2026-07-04 subsection below — MMVQ→MMQ verify-dispatch `de447119f` +17.4%, nwarps 2→4 `5dc116130` +4.6%, `raw.buffer.load.lds` async-prefetch `7c28056b7` +3.3% byte-identical, bf16 GDN recurrent-state `496e2f098` +21.5%@B32) were re-A/B'd on the reconciled kernel: **bf16-state ON/OFF @B32 gives 27B 165.5→198.8 (+20.1%) and frontdoor 35B-A3B 346.9→408.3 (+17.7%)** — matching the original campaign, confirming iqk and the 4 GPU opts coexist and both deliver. All remain runtime-gated + operator-gated (`GGML_CUDA_Q8_PREFETCH` / `GGML_CUDA_GDN_STATE_BF16` default-off, byte-identical when off).
- **Verified v7-candidate aggregate spec sheet (batched-bench S_TG, optimal per-model config, temp+seed42):** gemma-4-31B Q8 (−fa0) 27.1 / 104.0 / 174.3 / **245.9** (B=1/8/16/32) · Qwen3.6-27B Q8 (−fa0, bf16-state) 31.4 / 103.6 / 157.8 / **198.8** · Qwen3.6-35B-A3B Q8 **FRONTDOOR** (−fa1, bf16-state) 94.0 / 228.1 / 286.2 / **408.3** · Qwen3.6-27B F16-proxy (−fa0, bf16-state) 19.2 / 72.6 / 109.3 / **141.2**. (B=1-of-aggregate ≠ single-stream top — it's plain at the aggregate FA config; use the single-stream MTP spec sheet for latency.)
- **Governance: the experimental-kernel workflow + production-kernel immutability rule was codified, and the v7 reconciliation is its first validated instance.** `production-consolidated-v6` is **immutable** — all kernel R&D happens only in `llama.cpp-experimental`, and a full build must pass before any promotion. The 4-step workflow the reconciliation followed: **pull-fresh-production → build → validate-no-regressions → version-past to a new production tag** (production kernels are never edited in place; a new optimization set is layered onto a fresh pull and promoted as the next immutable production kernel). The same workflow produced `production-consolidated-v7` on 2026-07-20 at frozen candidate `6ad45fa3ff`.

### 2026-07-05 — MI210 big-model residency ladder (2-for-2) + CoT-scaffold REOPENED/VALIDATED on reasoning tasks (GPQA reversal, +12) → verifier/selector now COMPLEMENTARY + KV-quant SCOPED→DEFER + MTP-on-GPU-MoE CONVERGED (~neutral at prod) + stream-K already-shipped — ⚠️ COMPILE-FLAGGED FOR HUMAN REVIEW

> **Review flag (project-wiki writer-evidence policy):** model-compiled from the MI210 residency phase; **not adopted until human or measured review**. Every throughput/PPL number is an **OBSERVATION** — single MI210, serial, contended host, no P-GPU-1 per MEASUREMENT.md — the *residency-viability verdict + ladder pattern* is the load-bearing part, not the absolute t/s. Sources: [MI210 speed-campaign summary](../handoffs/completed/mi210-speed-campaign-summary.md), [big-model residency + acceleration roadmap](../handoffs/active/mi210-big-model-and-acceleration-roadmap.md), [findings-05c lever × category matrix §3.3](../handoffs/active/fable5-window2-findings-05c-mi210-lever-category-matrix.md), [GPU CoT-scaffold sidecar](../handoffs/active/gpu-cot-scaffold-sidecar.md), [progress 2026-07-05 residency + CoT reframe](../progress/2026-07/2026-07-05-mi210-residency-and-cot-reframe.md), [progress 2026-07-05 CoT falsification + MTP re-check](../progress/2026-07/2026-07-05-cot-falsification-and-mtp.md), [progress 2026-07-05 GPQA reversal + KV-quant DEFER](../progress/2026-07/2026-07-05-mi210-gpqa-reversal-and-kvquant-defer.md).

- **The IQ2 GPU-residency bet is now MEASURED VIABLE on TWO large models — a 2-for-2 ladder, and the pattern generalizes across GDN families.** The prior campaign projected 122B-IQ2 residency; this phase *confirmed* it and added a second data point on a different arch. **(1) Qwen3.5-122B-A10B UD-IQ2_M** runs fully GPU-resident (47/64 GB, ~17 GB headroom): 43.7 t/s single / 148.7 agg @B=32, IQ2 PPL 5.02 healthy. **(2) Qwen3-Next-80B-A3B i1-IQ2_M** (26.1 GB, qwen3next GDN-hybrid — a *different* GDN family from qwen3.5): coherent under CDNA2 IQ2 MMQ with `-fa on`, 55.8 t/s single (~2.7–3.9× CPU-Q4) / 265 t/s agg @B=32 (~13–18× CPU-Q4), PPL 5.77; VRAM 27.7 GB @`-c 32768` → ~38 GB free, **32K KV fits trivially** because GDN linear-attn keeps KV ~O(1) (the long-context ingest role is *better* GPU-served than a dense model would be). The **bf16-GDN-state kernel win generalizes to qwen3next too** (+13.3% aggregate, coherent — first confirmation outside qwen3.5). Together this establishes that CDNA2 IQ2 residency is a repeatable capability lever for ≤122B GDN-hybrid MoEs, not a one-model fluke. (GLM-5.2 ~238 GB even at UD-IQ2 still does not fit GPU-only — the cap is ~122B; larger needs expert-offload/REAP.)

- **80B IQ2 aggregate throughput is compute-bound with VRAM non-binding — the card is a genuine high-concurrency host, not just a capacity trick.** Batch sweep B32→B128: 263 / 301 / 323 / 382 / **405 t/s** aggregate decode; knee at B≈96–128, asymptote ~498; per-step model = 0.059 s BW floor + 0.00201·B compute. VRAM is **not** the binding constraint (30 GiB @B128 = 46% of 64 GB) → the deployable optimum is B=96 (381 t/s, latency-balanced) / B=128 (405 t/s, max aggregate). This matches the campaign's earlier bf16-for-aggregate finding: at high batch the regime is compute-bound, so residency + concurrency compound rather than trade off.

- **122B IQ2 passed a judge-free eval-parity gate: IQ2 ≈ Q4 at Δ0.0pp — the residency prize is quality-confirmed, not just fast.** A 212-question deterministic *paired* eval (same questions, same eval-tower scorer, only the quant differs) gave **IQ2 163/212 = Q4 163/212, Δ0.0pp, McNemar p=1.000** (11/11 disagreements symmetric = quantization noise), + PPL 5.02. On judge-free evidence, UD-IQ2 is a **drop-in GPU-resident architect**. Correction recorded: the earlier "93%" architect-quality figure was the **35B coder**, not the 122B (Q4-122B = 2.57/3 = 85.67%). The LLM-judge weighted-rubric architect gate (70 Qs) remains deferred — it needs a cross-family judge, not runnable GPU-only. **Load-bearing measurement lesson: a paired same-question McNemar test isolates the quant effect judge-free**, sidestepping the cross-family-judge dependency that blocks the rubric gate.

- **bf16 GDN recurrent-state is the campaign's ONE clean deployed-role kernel win — BUILT + GO, and it beat its own projection.** The 2026-07-04 campaign had scoped bf16 recurrent-state as a modest, drift-gated "~+11% @B32" lever after the L20 GDN-occupancy path was ruled NO-GO (100% theoretical occupancy — the ~42% achieved is pure memory-latency, nothing to free). Measured, it is bigger and generalizes across **all three GDN-hybrid sizes** (runtime-gated `GGML_CUDA_GDN_STATE_BF16`, default-off, byte-identical when off; fork `496e2f098`, branch `upstream-mtp-verify`): **Qwen3.5-27B +21.5%** (162.8→197.8 t/s agg @B32, drift PPL +0.0035%, gemma isolation byte-identical, test-backend-ops 1103/1103) · **frontdoor 35B-A3B (deployed) +17.7%** (byte-identical) · **architect 122B IQ2 (deployed) +16.4%** (inherits the gate) · **Qwen3-Next-80B-A3B +13.3%** (first confirmation *outside* the qwen3.5 family). Mechanism: bf16 halves the recurrent-state **gather+scatter** (not just kernel compute) — rocprofv2 shows L2 hit 47.8→59.9%, VALUBusy 15.7→56%. High-batch-only (aggregate lever, not single-stream). This is the precision lever paying off where the occupancy lever couldn't, and it stacks under the IQ2 residency roles above. Sources: [progress 2026-07-05 capability + kernel-R&D](../progress/2026-07/2026-07-05-mi210-capability-kernel-rnd.md), [progress 2026-07-04 kernel-R&D loop](../progress/2026-07/2026-07-04-mi210-kernel-rnd-loop.md).

- **The MI210 acceleration ROADMAP is now a two-axis strategic thread — "one 64 GB card, two ways to use it" — with a corrected baseline that reframes every GPU win.** *Baseline correction (load-bearing):* the production architect (122B UD-Q4_K_M on CPU, v6 native MTP) is **~18–21 t/s single-stream** (best 20.75 MTP; live median ~16; 2-slot ~8.5/slot), **NOT** the stale lean-registry 4.3 — so every GPU speedup above is measured against ~20, not 4.3 (the residency win is ~2.2× single / ~8–9× aggregate, not ~10×). **Axis A — big-model RESIDENCY** (host a large model *on* the card): the quant-ladder is **IQ2 near-term** (122B + 80B both MEASURED VIABLE, 2-for-2, capped at ~122B) → **expert-offload / REAP medium-term** (quality-preserving: hot experts GPU-resident at Q8/bf16, cold experts streamed from the 1.1 TB RAM via `--n-cpu-moe`/`-ot exps=CPU`; REAP = *permanently* drop cold experts vs offload = *stream* them — one **expert-routing-skew profile** measurement gates both: Zipfian → offload flies, near-uniform → PCIe-latency-bound) → **GLM-5.2 754B GLM-MoE-DSA endgame** (~238 GB even at UD-IQ2 never fits GPU-only → offload mandatory, maybe REAP + IQ2-resident-experts + offload-cold-tail). **Axis B — GPU DRAFTER-FARM** (keep targets CPU-resident, host fast drafters on GPU for spec-dec): the key operator insight is **quant-asymmetric self-spec** — host the *same* model at an aggressive IQ on the GPU as the DRAFTER + the high-quality quant (Q8/Q4) on CPU as the VERIFIER. Identical vocab/M-RoPE/GDN → **N5 sidestepped by construction**, and the CPU verify launders quality (accepted tokens are full-quant); it is also the graceful fallback if IQ2 eval-parity ever fails (an IQ2 too weak to *serve* can still *draft*). The extreme case (Qwen3.5-397B-A17B ~400 GB Q8 CPU-resident + a REAP+IQ1 ~56 GB same-model drafter on GPU) is the path to running a 397B/GLM-class model at *full CPU quality + GPU-drafted speed* — arguably stronger than IQ2-direct-serving since quality is never traded. Measure **α (drafter→target acceptance) FIRST** per `feedback_measure_alpha_before_specdec_investment`. The two axes **compete for the single card** → Gate-R is a scheduling decision, not foregone. Cheap decisive gating experiments (do before building): expert-routing-skew profile (Axis A), GPU-draft N5 feasibility + quant-asymmetric α (Axis B), 122B IQ2 eval-parity (Axis A — now PASSED). Source: [big-model residency + acceleration roadmap](../handoffs/active/mi210-big-model-and-acceleration-roadmap.md).

- **CoT-scaffold sidecar: an accuracy-vs-token feature is gated by RESCUE RATE on tasks the cheap path fails, NOT token-efficiency vs its average.** The MI210 CoT-scaffold screen (small GPU-resident reasoner injects a scaffold into a CPU code worker's prompt) first read as "marginal / config-fragile" once baseline cleanups (suite saturation → `-c 8192` truncation → Qwen context-length rope-scaling, which flipped nothink 77.8%→88.9% just from `-c 8192`→`10240`) let plain nothink catch up token-normalized. **Operator reframe corrected the verdict on three counts:** (1) *metric* — when nothink FAILS a task, token cost is irrelevant; the data already showed the value: the scaffold **rescued 3 (format-native cross-family) / 4 (distilled) tasks nothink failed outright, 0 regressions**; (2) *distribution* — code puzzles are where reasoning helps least (short/verifiable → nothink saturates); rescue value lives in the hard tail + realistic agentic workflows; (3) *deployment* — a **conditional** episodic-memory-gated lever, not always-on. Two clean survivors: a **CoT-distilled generator beats a vanilla reasoner** as a scaffold source (+11.1pp @0.58× tok), and **cross-family transfer requires format-native reasoning-slot injection** (a literal foreign `<think>` tag does NOT transfer: 63% vs gemma-nothink 81.5%; the target's own reasoning slot lifts +11.1pp/0-regressions). Both are orchestration components (a family of accuracy-for-tokens levers — think-mode, MTP, escalation — the learned-routing-controller should select among per task-class). **UPDATE — single-shot lane CLOSED (2026-07-05):** the rescue-rate experiment ran to completion and, with a favorable-regime follow-up, **falsified single-shot injection in both strength regimes.** On the strong 35B beneficiary (`mode_advantage_hard`, nothink 41/60): scaffold-Qwable 39/60 = **net −2 (2 rescues, 4 regressions)**, scaffold-4B 32/60 = net −9 — even a distilled same-class generator is net-negative because the 35B is already as strong a reasoner as the distilled-35B generator (nothing to rescue, only derail). The favorable regime **generator > beneficiary** (Qwable → gemma-26B, format-native) also failed: 36/60 vs gemma-nothink 39/60 = **net −3, 1 rescue of 21 available nothink-failures (5%), no CPU savings**. **Mechanism: transplanted reasoning does not transplant capability** — handing a model a pre-made trace neither unlocks tasks it fails nor is cost-free, independent of strength ordering. The single-shot injection lane is therefore CLOSED; the only untouched mechanism is a **recursive reason↔execute loop** (the reasoner proposes one step, the strong model executes, the reasoner is re-grounded by the concrete output before the next step → execution feedback bounds/corrects a weak generator per-round instead of compounding a wrong conclusion) — a bigger, operator-gated build, prior lowered by these negatives. The objective it optimizes is autopilot's EXISTING 4D Pareto (`quality, speed, −cost, reliability` + a `q_reward` cost penalty on correct answers), so the scaffold is a `capability_registry` lever, not a new optimizer to build. This is a measurement-discipline finding as much as a hardware one — an accuracy-vs-token feature is gated by **rescue rate on tasks the cheap path fails**, not token-efficiency vs its average, and here that rescue rate was too low to pay: see memory `feedback_accuracy_token_tradeoff_rescue_metric`. **UPDATE — scaffold-injection CLOSED, VERIFIER/SELECTOR is the forward path (cont. 2026-07-05):** the last untouched mechanism, the recursive **reason↔execute loop**, was tested (a self-debug loop: 35B, bigcodebench, write→execute→feed-error→revise, MAX_ITERS=3) and is **also weak — 4% rescue (2/47), effort-curve flat** — matching **RL-ceiling (arXiv:2504.13837)**: self-refinement is bounded by the base's pass@k, so loops don't cross the ceiling. A public-literature survey then confirmed that **scaffold/reasoning-injection is a *published* dead-end and our negatives ARE the field consensus**: "Reasoning that Travels" (2605.28913, transplanted reasoning is a capability **amplifier not substitute**), small-planner-degrades-executor (2506.11578), RL-ceiling (2504.13837), reasoning is elicited-not-installed (LIMO/s1), and a learnability gap below ~3–7B (2502.12143 — our 4B-Fable5 sits at the boundary). **The ONE working "help another model" mode we never tested = VERIFIER / SELECTOR (best-of-N):** the reasoner does *its own* task — grade/rank/verify the beneficiary's candidate answers — and never transplants capability, so it sidesteps the whole transplant problem (**GenRM 2408.15240**: BoN 5%→45%, 73%→93%; **GenPRM 2504.00891**: a **1.5B generative PRM beats GPT-4o as a judge**, a 7B beats a 72B). It fits the GPU-reasoner + CPU-beneficiary topology and **plugs into the existing EV-9 DRACO/MindDR scorer**. Reframed GPU-reasoner role: (1) route reasoning-heavy tasks to it standalone; (2) verifier/selector best-of-N over CPU-model outputs — **NOT** scaffold-injection. Verifier/selector is the **recommended next GPU-reasoner experiment**, testable *entirely on GPU* by hosting the beneficiary on GPU and artificially rescaling its t/s to sweep the CPU-cost tradeoff. The reasoning loop-depth also frames as a local **"reasoning-effort" knob** (the analog of cloud `reasoning_effort`/thinking-budget) — an operator flag + an autopilot per-task-class tunable on the same 4D-Pareto. (A GPQA reasoning-diagnostic — nothink vs ownthink vs scaffold-Qwable — is in flight to decide whether the bench distribution, not reasoning, was the issue.) **UPDATE — GPQA REVERSAL (2026-07-05): the scaffold WORKS on reasoning-bottlenecked tasks; the "dead-end" was DISTRIBUTION-SPECIFIC, not fundamental.** On GPQA grad-science (N=48, wide caps, 35B beneficiary, deterministic MC, seed 42): nothink **48%** (23/48) / ownthink **67%** (32/48 — a LOWER BOUND, 20/48 still truncated @16384 because the 35B over-thinks and doesn't converge) / **scaffold-Qwable 73%** (35/48) = **+12 vs nothink (+25%), with 15 of 25 nothink-failures rescued, only 3 regressions, and 0 truncation.** This **reverses** the code-distribution single-shot falsification: two operator methodology catches were decisive — (1) we had tested the **wrong distribution** (bigcodebench = library-API knowledge, not reasoning), and (2) the **caps were too tight** (8192 truncated ownthink and understated it). The result **reconciles cleanly with "amplifier not substitute" (arXiv:2605.28913)**: the **receiver's latent capability is the gate** — GPQA (grad-science) the 35B HAS it so the scaffold amplifies (+12); library-code has knowledge gaps with nothing to amplify (self-debug loop 4%). The literature was never "scaffold is dead" — it was "scaffold amplifies a *capable* receiver," and we had been testing on the one distribution where the receiver had nothing to amplify. **Scaffold ≈ ownthink on quality but far more token-efficient** (Qwable reasons concisely + completely in 8192; the 35B overthinks past 16k) — the GPU reasoner delivers the benefit at a fraction of the beneficiary token cost and dodges the overthinking-truncation trap. **Caveat (needs a control):** on multiple-choice the +12 could be "35B latent capability elicited" or "Qwable solves it + the 35B relays the choice" — a **Qwable-standalone GPQA control** disambiguates; deployment value (the beneficiary server answers better) holds either way, and both readings are literature-endorsed (amplify vs standalone-reasoner). **The scaffold-injection lane is therefore REOPENED + VALIDATED on reasoning-bottlenecked tasks**, with a conditional deploy rule (reasoning-bound tasks where the beneficiary has latent capability, gated via `difficulty_band` + task-class), and **the verifier/selector best-of-N becomes a COMPLEMENTARY mode rather than the replacement** — its harness is built (`driver_verifier.py`, GenRM on cruxeval), ready to run. Load-bearing lesson: **an accuracy-vs-token verdict is distribution-conditional — test on the distribution where the receiver has latent capability to amplify before declaring a scaffold dead.**

- **Native MTP on a GPU-resident MoE stays net-negative — and the re-check exposes a spec-dec measurement trap: never A/B at temp 0.** The GPU-MoE self-spec verdict (`de447119f` MMQ-verify fix narrowed the earlier −12% penalty) was briefly re-read as **+6.5%** (91.2 vs 85.6 t/s) — but that was a **temp-0 (greedy) A/B, which spuriously inflates MTP draft-acceptance**. Re-measured at **production sampling (temp 0.6, seed 42): MTP-on-GPU-MoE is −6.8%** (87.9 vs 94.3 t/s, draft acceptance 0.57, mean-accept-len 3.3) — `de447119f` narrowed the penalty (−12% → −6.8%) but did **not** flip it. On already-fast plain MoE decode (reads only ~active-expert bytes off 1.6 TB/s) the draft+verify overhead still isn't repaid; MTP remains a no-go lever for GPU-resident qwen35moe (122B/35B). **Load-bearing measurement lesson:** greedy decoding is a best-case for speculative-decoding acceptance, so a temp-0 speed A/B systematically over-states any spec-dec win — always measure at production sampling (temp + seed). See memory `feedback_production_sampling_seed_not_temp0`. **UPDATE — CONVERGED to ~neutral at production temperature (cont. 2026-07-05):** the "−6.8%" above was the **temp-0.6 point of a temperature curve**, not "production sampling." Production actually runs low-temp (registry intent 0.1–0.3 + greedy fallback). Full curve (35B-A3B, seed 42): **temp 0 (greedy) +6.5%** (accept 0.79) · **temp 0.2 (production) −1.6%** (accept 0.63) · **temp 0.6 −6.8%** (accept 0.57). At the deployed temperature the operative number is **−1.6% = ~neutral (within single-sample noise)**; `de447119f` **neutralized the old −12% penalty**, so MTP-on-GPU-MoE is a **WASH at production temp — not worth enabling as a speed lever, but no longer a reason to avoid it** (this supersedes the "no-go" verdict). The three-way flip-flop (−12% → +6.5% → −6.8%) was caused entirely by measuring arbitrary temperatures instead of the deployed config. **This is textbook spec-dec behaviour:** speculative decoding is output-distribution-preserving (lossless) at *every* temperature — only the speedup varies, and **acceptance falls monotonically as temperature rises** (our 0.79→0.63→0.57 curve is exactly that shape), so low-temp production is the *favorable* spec-dec regime and the ~neutral reading is the expected outcome, not an anomaly.
- **stream-K is ALREADY the live CDNA2 MMQ path — a factual correction, not an un-tried bet (cont. 2026-07-05).** A read-only `mmq.cu` assessment (zero build) shows **`use_stream_k = true` for CDNA2**: the 104-WG grid the aggregate campaign already benchmarked **is** stream-K working as designed (`nsm` persistent blocks, one balanced block/CU) and produced the very aggregate baseline that was measured. The campaign's earlier framing of "stream-K as a bigger separate bet" was an error — it is the live path. The only untested residual is raising the persistent grid `nsm → k·nsm` (2 WG/CU) plus the saved compact-LDS patch (~2-line change, expected +0–10%, IQ2/HBM-capacity slot only), gated on a zero-build read of the captured pmc CSVs. **Lesson: audit the shipped kernel path before treating a named optimization as an unexplored lever.**

### 2026-07-04 — MI210 Qwen3.6-27B GPU speed campaign (kernel / quant / regime frontier) — ⚠️ COMPILE-FLAGGED FOR HUMAN REVIEW

> **Review flag (project-wiki writer-evidence policy):** this subsection was model-compiled from the MI210 campaign docs and is **not adopted until human or measured review**. Every throughput number is an **OBSERVATION** — single-run, contended MI210 host (production CPU stack live on :8070–:8095), no P-GPU-1 per MEASUREMENT.md; the *ordering/mechanism* is the load-bearing part, absolute t/s must be re-anchored under a ratified protocol before gating anything. Sources: [findings-05b MI210 inference architecture](../handoffs/active/fable5-window2-findings-05b-mi210-inference-architecture.md), [progress 2026-07-03 MI210 campaign](../progress/2026-07/2026-07-03-mi210-qwen36-27b-speed-campaign.md).

- **MMVQ→MMQ small-batch verify-dispatch fix is a real but DENSE-Q8-specific GPU win.** Routing small Q8_0 spec-dec verify batches to the batched `mul_mat_q` instead of per-column `mul_mat_vec_q` (one-line `ggml_cuda_should_use_mmvq` CDNA2 branch `case GGML_TYPE_Q8_0: return ne11 <= 1;`, experimental commit `de447119f`) measured **+17.4% single-stream MTP on Qwen3.6-27B dense-Q8** (34.4→40.4 t/s) and **+31.7% on gemma-4-31B dense-Q8** (34.7→45.7) — same sign, larger magnitude on a second model. NOT the projected ~2×: `mul_mat_vec_q` already amortizes tile loads across the 4 verify columns in-register, so MMQ removes only ~15% redundant HBM traffic. **Regime limit:** the fix touches only the DENSE path; **MoE experts route through a separate `get_mmvq_mmid_max_batch` mmid dispatch it never touches**, so the frontdoor qwen35moe is kernel-FLAT (+0.7%, ~−5% end-to-end). There is no dense-Q8 production role (the 27B is a test vehicle) → limited production value; the production-relevant `mmid` threshold is identified, untested, deferred behind residency. Numerically valid, not bit-exact. Operator-gated for prod promotion.
- **bf16 vs Q8 is a CROSSOVER, not a clean Q8 win (gemma-4-26B-A4B MoE).** Q8 wins single-stream (96.6 vs bf16 73.1 t/s, 1.32×) and B=8; **bf16 wins B=32 aggregate (744 vs 561 t/s)** — at high batch the regime is compute-bound and fp16 runs native on CDNA2 matrix cores with nothing to amortize while Q8's per-tile dequant caps compute-bound throughput (batch-scaling bf16 10.19× vs Q8 5.81×), directly confirming the dequant-amortization thesis. The bf16-batched win is **HBM-capacity-gated** (bf16 50.5 GB vs Q8 27 GB; fits ~55 GB @B32 on the 64 GB card). **Q8 for latency, bf16 for high-concurrency throughput where it fits HBM.**
- **GDN recurrence is the aggregate/batch-scaling bottleneck and is qwen35-specific — but the GDN-MFMA kernel is KILLED by profile for decode.** GDN grows 2%→19.5% of decode across B1→B32 (absolute ×39); the qwen35 frontdoor batch-scales only 3.4× (B1→B32) vs gemma-MoE 5.9× / gemma-dense 8.6×. rocprofv2 on `gated_delta_net_cuda` @B=32 decode: **MemUnitBusy 65% vs VALUBusy 16%, MfmaUtil 0%, ~42% occupancy, ~130 GB/s of 1638** — memory-unit + occupancy/latency-bound (recurrent-state ~106 MB/disp, 48% L2 hit), NOT compute-bound. An MFMA kernel targets compute headroom that isn't the bottleneck → **do not build it for decode**; the real GDN lever is occupancy + recurrent-state traffic/layout. (Prefill is more ALU-active, VALUBusy ~50% — separate open question.) Tooling: rocprof v1 reads SQ/TA counters as zero on this box; **rocprofv2 required**.
- **KV-quant does NOT help the weight-dominated MoE frontdoor.** q8_0-KV vs f16-KV on Qwen3.6-35B-A3B Q8 @98k context saves only ~0.94 GB VRAM and changes decode t/s by nothing (±1.5% noise); the ~36 GB Q8 weights dominate and ~15 GB is free even @128-way → VRAM is not the binding constraint and the **~430 t/s aggregate @128-way @80k plateau is compute/BW-bound**. Stay on f16-KV. (Alive in a KV-heavy regime — a dense model, or single-stream long-context where KV rivals the weights.) **UPDATE — SCOPED → DEFER (2026-07-05, findings-05c L14): no dedicated GPU run.** Resolving the "alive regime" against the deployed roster: only the **qwen35 ~1/4 full-global attention layers @ single-stream 32–64k** qualify — **GDN keeps KV O(1)**, **gemma SWA bounds it**, and **aggregate is weight-dominated**, so **3 of 4 resident model classes see ~0 payoff**. CPU precedent shows the **dequant cast COSTS throughput** (+9% wall / −30% gen). No deployed role needs it. Decision: run only as a cheap **~2–4h rider** on a *future* dense-full-global long-context role, to close the `[U]` with data — **it is a max-context / VRAM characterization, not a speed lever.**
- **Throughput-vs-context: the "hybrid stays flat" hypothesis is FALSIFIED (SWA confound).** 1k→64k single-stream decode degrades qwen35 hybrid **−22.3%** vs gemma-4 **−7.9%** — the OPPOSITE of expected. Root cause (GGUF metadata): gemma-4 uses sliding-window attention (bounded per-layer KV → context-capped decode) while qwen35's ~1/4 attention layers are full-global (unbounded KV growth). GDN context-independence is real, but the full-global attention layers dominate degradation; a clean GDN-flatness test needs a non-SWA dense baseline (gemma-4 is not one). qwen35's full-global attention is a recall advantage, not a pure loss.
- **The batch-1 dequant wall — the lever is dispatch, not a rewrite.** Single-stream Q8 decode is BW-bound `mul_mat_vec_q` (77.8% @B=1, whole GEMM/dequant bucket 84%; GDN only 2.0%), so raw batch-1 kernel headroom is small (Q8 47–52% roofline; fp16 ceiling 62% → ~+19% recoverable is the hard ceiling). The single-stream lever is the verify-dispatch fix above, not a dequant rewrite. Still OPEN as separate handoffs: a Q8 dequant-GEMV kernel ([mi210-q8-dequant-gemv-roofline](../handoffs/active/mi210-q8-dequant-gemv-roofline.md)) and MFMA for compute-bound paths ([mi210-mfma-compute-bound-paths](../handoffs/active/mi210-mfma-compute-bound-paths.md)).
- **CAMPAIGN OUTCOME (updated 2026-07-04 EOD — speed exhausted; frontier moved to capability).** Every kernel/occupancy bet has now been driven to a verdict, and the honest conclusion is convergence. Single-stream dense-Q8 banked **+37% (40.4 t/s)** — MMVQ +17.4%, nwarps 2→4 +4.6% (`5dc116130`), async-prefetch +3.3% (`7c28056b7`) — then **fused-prefetch, megakernel (Pass-2: MLP/memory floor — HIP graphs already capture the only +5.9% launch headroom), n-gram-GPU-spec, MFMA, and the L3-MoE MMQ-occupancy rewrite were all ruled out WITH DATA** (the last: *built* then falsified — Q8-MMQ at B=32 is **grid-limited** (104 WGs = 1/CU), not LDS-limited, and bf16 wins on native-MFMA not occupancy). Aggregate is solved by **config, not kernels**: **`-fa 1` is a WIN for MoE aggregate** (B≥8, +16–43%, peak **bf16+`-fa1` @B128 = 1548 t/s** — the *opposite* of dense-27B where FA hurt) and **bf16-for-aggregate / Q8-for-single-stream** (crossover B≈16–24). L20 GDN-occupancy scoped **NO-GO** (theoretical occupancy already 100% — nothing to free; the one modest lever is bf16 recurrent-state, ~+11%@B32, drift-gated). **Load-bearing meta-finding: a lever's sign is set by {arch × substrate × batch} — never carry a spec-dec / quant / FA verdict across dense↔MoE or GPU↔CPU.** With speed at bedrock, the frontier moved to **capability**: the CDNA2 sub-4-bit MMQ path is already numerically correct (`MUL_MAT_ID 789/789` across IQ2/IQ3/IQ1), so IQ2 unlocks **Qwen3.5-122B-A10B @ ~38 GB fully GPU-resident** — the residency bet's real prize (GLM-5.2 ~238 GB still won't fit). Top-line: [MI210 speed-campaign summary](../handoffs/completed/mi210-speed-campaign-summary.md) · [lever × model-category matrix (findings-05c)](../handoffs/active/fable5-window2-findings-05c-mi210-lever-category-matrix.md).
- **Kernel-R&D loop — the verify→profile→refine automation this campaign motivated** (a concrete instance of the 2026-06-03 GEAK/Apex agentic-kernel-authoring program below). The manual per-bet rigor is codified into a reusable, nightshift-runnable loop in `epyc-inference-research/scripts/kernel_rnd/`: **`kernel_eval.sh`** (GPU-idle gate → correctness-gate-FIRST/lexicographic → alternated-A/B → rocprofv2 mechanism → one OBSERVATION record), **`kernel_store.py`** (SQLite + a Pareto frontier over *correctness-passing* runs only — a fast-but-wrong variant can never reach the frontier), **`kernel_sweep.sh`** (the inner tuning loop). The *outer* hypothesis/design loop stays planner/critic-interactive (single-GPU serial ⇒ brute search too costly); authorize (P-GPU-1 / prod push) stays operator-only. **Build status (2026-08-11): the historical four-phase scaffold is reconciled into the system-wide AutoKernel loop.** Design history: [mi210-kernel-rnd-loop-proposal](../handoffs/completed/mi210-kernel-rnd-loop-proposal.md); current owner: [autokernel-research-loop](../handoffs/active/autokernel-research-loop.md).

### 2026-07-03 — Roofline-gap synthesis (CPU v6+iqk & MI210) and the GPU-program un-gating

- **The MI210 "~60% roofline ceiling" is largely a *batch-1 measurement artifact*, not a loss under production serving.** Weights are read once per forward step and reused across the batch, so at batch-32 the weight-BW utilization *falls* to ~28% while token throughput *rises 14.6×* (62.45 → 909.8 t/s) — the operating point leaves the BW-bound edge and climbs the compute/occupancy roof, where "% of weight-BW roofline" is the wrong axis. Under concurrent production serving the card already delivers ~910 tok/s @32-way. Sources: [findings-05 roofline](../handoffs/active/fable5-window2-findings-05-intake-sweep-and-roofline.md), [progress 2026-07-02 MI210](../progress/2026-07/2026-07-02-mi210.md).
- **The dequant slowdown IS compensable — and the cheapest, highest-recovery method is a config change, not a kernel.** Two gaps decompose the gfx90a decode roofline (consistent GiB basis): a **dequant gap** (Q4_K 34% → Q8 50% → fp16 62.5%; ~28pp lost on Q4, ~12pp on Q8) and a **batch-1 latency gap** (fp16 62% is already near the practical batch-1 ceiling — above vLLM-on-H100's ~50%, near Hazy's ~78% single-dispatch; no ROCm megakernel exists). Serving quantized models **batched (`-np 8–32`)** amortizes MMQ dequant across batch columns and engages MFMA, so for throughput roles the penalty self-compensates. A custom gfx90a Q4_K dequant-GEMV kernel (via the GEAK/agentic-rocm loop) is worth authoring **only for a batch-1 *latency* role** (e.g. a GPU drafter), recovering ~half the 28pp Q4 gap. NOT via AITER (gfx90a-unsupported), NOT via fp8 (needs ROCm 6.3), NOT via MFMA at batch-1 (GEMV idles the matrix cores). **Caveat making measurement mandatory:** the ~910 figure is fp16 Qwen3-8B — the *quantized* batched sweep was never run on the MI210, and MoE batches worse than dense (distinct tokens hit distinct experts), so a quantized `-np` sweep is the decisive first experiment. Source: [findings-05 roofline](../handoffs/active/fable5-window2-findings-05-intake-sweep-and-roofline.md).
- **CPU decode sits on a *barrier/op-count plateau*, not the BW wall — and iqk is decode-neutral on Q8_0.** Frontdoor Qwen3.6-35B-A3B Q8 ≈ 13.8% and worker gemma4-26B-A4B Q4 ≈ 21% of 460 GB/s STREAM; but STREAM ≠ achievable GEMV (realistic MoE-GEMV ceiling ~25–30%), so the worker is ~74–78% of *its* ceiling (little single-stream headroom) while the frontdoor is ~49% (a real gap). The bottleneck is libomp barrier / op count (≈45% of Q4_K decode cycles are barrier at 96t), so the top CPU decode lever is **frontdoor Q8_0 operator/graph fusion to cut barrier count** (est +10–15%), NOT more SIMD; iqk's wins are prefill + Q4 decode, so it does not move frontdoor Q8 decode. No *canonical* post-iqk decode number exists yet (v6-iqk-promotion Phase J bench pending). Sources: [findings-05 roofline](../handoffs/active/fable5-window2-findings-05-intake-sweep-and-roofline.md), [cpu-shape-specialized-gemv-decode.md](../handoffs/active/cpu-shape-specialized-gemv-decode.md), [iqk-port.md](../handoffs/active/iqk-port.md).
- **The MI210 GPU program is UN-GATED (operator-directed 2026-07-03): the DGX-Spark gating everywhere was stale.** The project *considered* a DGX Spark and bought the MI210 instead, so "DGX-gated / expected ~July 2026 / nothing runs until the card racks" lines across ~14 handoffs were reprioritized: `agentic-rocm-kernel-authoring` + `rocm-verify-profile-backend` flipped to ACTIVE (MEDIUM — an optimization to close the roofline gap, not a production blocker; first step = reproduce GEAK-eval on gfx90a, the only gfx90a-proven substrate — AgentKernelArena/robust-kbench are gfx942-listed), `gpu-acceleration-path` retargeted off the never-bought DGX Spark onto the MI210. The ordered queue is now G0 α-from-live-MTP-logs (free) → G1 P-GPU-1 protocol → G2 HIP op-smoke → G3 Gate-R frontdoor-residency bench. Sources: [findings-02 heterogeneous GPU](../handoffs/active/fable5-window2-findings-02-heterogeneous-gpu.md), [master-handoff-index §F](../handoffs/active/master-handoff-index.md), [gpu-acceleration-path.md](../handoffs/active/gpu-acceleration-path.md).

### 2026-07-02 — MI210 GPU installed: HIP path verified, first GPU benchmarks, vLLM head-to-head

- **The MI210 (gfx90a, CDNA2, 64 GB HBM2e) is physically installed and the hardware gate for the entire GPU-drafter program is now OPEN.** It is passed into the devcontainer (`--device=/dev/kfd --device=/dev/dri`) with **ROCm 6.2 bind-mounted at `/opt/rocm`**; `rocminfo`/`rocm-smi`/`hipcc` all work. Our fork's HIP build leg works on gfx90a: isolated worktree `mi210-hip-enable` off `production-consolidated-v6`, `-DGGML_HIP=ON -DAMDGPU_TARGETS=gfx90a`, with **one** build fix — `ggml-cuda/vendors/hip.h` guards OCP fp8 typedefs on `HIP_VERSION>=60200000` but ROCm 6.2 ships only the `_fnuz` fp8 types (OCP landed in ROCm 6.3), so the guard was bumped to `>=60300000` (commit `0ebf1b4d7`). Runtime gotcha: `BUILD_SHARED_LIBS=ON` + the container's inherited `LD_LIBRARY_PATH` (production CPU build first, no `libggml-hip.so`) → SIGSEGV; must prepend the HIP build's `bin:/opt/rocm/lib`. All GPU numbers below are **first-pass OBSERVATIONS** (contended host, ~106 load, operator-approved GPU-only), not decision-gating per MEASUREMENT.md. Sources: [progress 2026-07-02 MI210](../progress/2026-07/2026-07-02-mi210.md), [gpu-drafter-mi200-investigation.md](../handoffs/active/gpu-drafter-mi200-investigation.md).
- **First GPU-resident decode benchmarks (`-ngl 99`):** gemma4-31B dense Q4_K_M **30.01 t/s** (524 GB/s, 32% roofline); Qwen3.6-27B (qwen35 hybrid-SSM) Q4_K_M **32.88 t/s** (33%); Qwen3.6-27B **Q8_0 28.69 t/s** (766 GB/s, **47% roofline** — the best-case quantized point). Decode variance was ±0.01 t/s *under ~106 host load* → GPU-resident decode is fully insulated from the CPU stack (weights served from HBM, separate compute units), so the GPU can run concurrently with the 28-process CPU stack without contention. Source: [progress 2026-07-02 MI210](../progress/2026-07/2026-07-02-mi210.md).
- **gemma4-31B + NEXTN MTP speculative decoding works GPU-only.** Target + the 514 MB NEXTN head both on ROCm0 via `--spec-type draft-mtp -ngl 99 --spec-draft-ngl 99` (wired in `llama-server` only; the CLI/speculative example is not MTP-wired): decode **43.25 t/s = 1.44× over plain (30.01)**, draft acceptance **59.7%** (163/273), mean accept length **2.79** of n_max=3. The per-step hidden-state hop is a ~µs PCIe memcpy, not CPU compute — direct evidence that head-on-GPU MTP is structurally sound (the CPU-only gemma4 MTP baseline was 76.9% accept / Stage-0). Source: [gpu-drafter-mi200-investigation.md](../handoffs/active/gpu-drafter-mi200-investigation.md), [progress 2026-07-02 MI210](../progress/2026-07/2026-07-02-mi210.md).
- **qwen35 (gated-delta-net / hybrid-SSM) decodes CLEAN on the GPU HIP path** — Qwen3.6-27B at 28.69 t/s, no M-RoPE/GDN decode failures. The v6 fork's `ggml-cuda` has full delta-net/ssm-conv kernels (a strict superset of the `dflash` tree, incl. `gated_delta_net.cu`). This **localizes the long-standing CPU N5 external-draft / tree-spec qwen35 failures to the CPU speculative codepath, not the qwen35 forward pass** — it removes "qwen35 can't decode on our stack" as a GPU concern (it does not by itself supply the N5 frontdoor-drafter α). Source: [gpu-drafter-mi200-investigation.md](../handoffs/active/gpu-drafter-mi200-investigation.md).
- **The ~47% roofline ceiling is a QUANTIZED MMQ-dequant artifact, NOT general CDNA2 kernel immaturity.** Matched-precision **Qwen3-8B fp16** head-to-head (Goedel weights, both engines ~15.3 GB): llama.cpp-HIP per-stream **62.45 t/s (62% roofline)** vs vLLM 0.10.1 **~69 t/s (69%, +11%)**; batched 32-way (npp128/ntg128) llama.cpp **909.8 gen tok/s** vs vLLM **1129 (+24%)**. At fp16 (no dequant) llama.cpp reaches 62% roofline; same-model Q8 gets 766 GB/s vs Q4_K's 537 GB/s (~14 pts of roofline lost to Q4_K MMQ dequant). vLLM's decisive edge is **batched serving** (continuous batching), not per-stream. Flash-attn does not help decode on gfx90a (`-fa 0` beats `-fa 1`; FA helps prefill only); default MMQ beats forced rocBLAS. The residual tuning headroom is specifically the quantized dequant kernels. Sources: [progress 2026-07-02 MI210](../progress/2026-07/2026-07-02-mi210.md), [rocm-mi210-vllm deep-dive](../research/deep-dives/2026-07-02-rocm-mi210-vllm-gfx90a.md).
- **Vulkan is architecturally IMPOSSIBLE on the MI210 — do not re-attempt.** RADV loads but enumerates ZERO devices for gfx90a; no Vulkan ICD (RADV / AMDVLK / amdgpu-pro) targets the compute-only Instinct MI200 family. The kernel side is healthy; the gap is userspace drivers that do not exist for CDNA2. This complements the GT 1030 falsification — the GPU path on this box is **HIP/ROCm only**. Source: [progress 2026-07-02 MI210](../progress/2026-07/2026-07-02-mi210.md).
- **vLLM on gfx90a is a real, buildable, *reference-kernel* engine — an evaluation instrument, not a second production binary.** Support-matrix intake (intake-759..763): gfx90a is a first-class tuned ROCm/Triton target and vLLM's `PYTORCH_ROCM_ARCH` still includes gfx90a (not dropped; v0.6.5 default ROCm = 6.2, matching our bind-mount), FlashAttention-2 covers gfx90a via CK+Triton at ROCm 6.0+ — **BUT `AITER_ROCM_ARCH`/`MORI_GPU_ARCHS`/`DEEPEP_ROCM_ARCH` are `gfx942;gfx950` only**, so an MI210 vLLM loses AITER/MORI/DeepEP acceleration and falls back to Triton/CK reference kernels. The MI300-locked image (`rocm/vllm:rocm6.2_mi300…`, `config.py` raises "built for MI300 only", gfx942-only rocBLAS/hipBLASLt) was a hard dead-end; the verified path is the prebuilt `rocm/vllm:rocm6.4.1_vllm_0.10.1_20250909` image with `VLLM_ROCM_USE_AITER=0`/`VLLM_USE_TRITON_FLASH_ATTN=1`/`TORCH_BLAS_PREFER_HIPBLASLT=0`/`--dtype float16`. vLLM 0.10.1 (and v0.22.0) lack our `gemma4`/`qwen35` archs, so it can never be the frontdoor/worker engine — the head-to-head necessarily used a shared Qwen3-8B. Sources: [rocm-mi210-vllm deep-dive](../research/deep-dives/2026-07-02-rocm-mi210-vllm-gfx90a.md), [intake-759 AITER], [gpu-drafter-mi200-investigation.md](../handoffs/active/gpu-drafter-mi200-investigation.md).
- **MI210 BW envelope re-confirms the drafter thesis, and AITER is the vendor ceiling to beat.** MI210's single 1.6 TB/s HBM2e pool is ≈3.5× the CPU aggregate (~8–16× what a single CPU role sustains) — the regime where GPU-side drafting is unambiguously cheap (Qwen3-0.6B Q4 drafter ~0.25 ms/token on MI200 vs ~3–4 ms on CPU). rocWMMA (intake-303) is the gfx90a-capable ROCm lib our llama.cpp-HIP path actually uses; AITER's MLA-decode-17× / fused-MoE-3× numbers are MI300X/MI350 (CDNA3/4) only and define the ceiling any hand-authored gfx90a kernel must beat, motivating the ROCm kernel-authoring track. Sources: [gpu-drafter-mi200-investigation.md](../handoffs/active/gpu-drafter-mi200-investigation.md), [gpu-acceleration-path.md](../handoffs/active/gpu-acceleration-path.md).

### 2026-07-02 — CPU-side: v6+iqk cutover complete, dense-MTP validated, new-arch CPU ports triaged

- **The v6+iqk production cutover is COMPLETE (autonomous bar met 2026-06-26; era fence 2026-06-27) and now carries N≥200 matched eval-parity evidence.** Every hot role is healthy on the single canonical v6 binary, `runtime_attestation` clean, `GGML_IQK=1` everywhere, ik_llama deprecated. P-QUAL-PROMO parity on `worker_general` (AA Omniscience deterministic F1, 206 common questions): IQK-on vs IQK-off accuracy **unchanged** (0.111650 vs 0.111650), avg F1 +0.008365, and throughput **38.46 vs 27.78 t/s = 1.3848×** (throttle-caveated). **Still pending:** a clean post-reboot bench and any operator production-policy decision — do not treat 1.38× as a certified production number. Source: [v6-iqk-promotion.md](../handoffs/active/v6-iqk-promotion.md).
- **The N12 private-copy `--no-mmap` flip is closed NEGATIVE for `frontdoor`/`ingest`/`vision`.** Role-equivalent N12 A/Bs refuted the private-weight flip for those quarter roles; keep the shared-mmap production launch unless a materially different protocol is measured. Launcher argv plumbing is fixed and `affinity_preflight.py --require-memory-locality` now exposes `/proc/numa_maps` placement for any future private-copy gate (a live worker-quarter strict check showed CPU-correct but memory-interleaved placement, so numa_maps proof is mandatory before reopening). This narrows — does not overturn — the 2026-06-25 `--no-mmap` NUMA-suite finding (which was a *benchmark-topology* result, not a production-launch policy). Sources: [v6-iqk-promotion.md](../handoffs/active/v6-iqk-promotion.md), [gpu-drafter-mi200-investigation.md](../handoffs/active/gpu-drafter-mi200-investigation.md).
- **N12 observability re-check on the live stack (2026-07-06) found no new locality fault.** A fresh broad `affinity_preflight.py` run over the live roles (`frontdoor`, `ingest_long_context`, `vision_escalation`, `worker_general`, `worker_vision`, `architect_general`) reported `live_memory_placement_verified=True` with `required=4` and `mismatches=0`. `worker_general` quarters remained fully local (`signal=anon_pages`, `local=1.0`), while the shared-mmap quarter roles continued to report the expected interleaved mmap placement. The run wrote `/mnt/raid0/llm/tmp/affinity_preflight_live_20260706T184407Z.json` and confirms the current slowdown investigation should not treat NUMA placement as the immediate root cause. Sources: [progress 2026-07-06](../progress/2026-07/2026-07-06.md), [numa-private-weights-quarter-roles.md](../handoffs/active/numa-private-weights-quarter-roles.md).
- **Dense-CPU MTP is validated on two independent models; MoE-CPU MTP remains walled.** gemma-4-31B dense CPU MTP (clean host) gives **~1.84× on prose** (draft-max=3 optimal) and **2.5–3.2× on structured/code output** (predictable tokens draft at high acceptance) — correcting the earlier single-run 2.98× claim, and MTP output is **distribution-lossless, not byte-exact greedy**. Qwen3.5-9B dense MTP: **1.97×, 87% accept** (via a fresh upstream build). MoE-A3B stays ~1.06× (expert-union verification wall). The draft LM-head is a small BW slice — FR-Spec vocab-trim (intake-740) cuts the draft-head kernel −85% but yields only **+1–3% end-to-end** on BW-bound decode, reinforcing that expert-verification overhead, not draft quality, is the CPU MTP wall. Sources: [speculative-decoding-mtp-refresh.md](../handoffs/active/speculative-decoding-mtp-refresh.md), [qwen-mtp-llamacpp-port.md](../handoffs/active/qwen-mtp-llamacpp-port.md).
- **Landing native Qwen MTP in *our* fork by cherry-pick is INFEASIBLE — a model-framework generation gap, not glue.** PR #22673's Qwen MTP graph is written against upstream's `llama_model_<arch> : public llama_model_base` refactor (landed somewhere in the ~901 commits our fork is behind), while our fork still uses the older `llm_build_<arch> : public llm_graph_context` pattern; the MTP graph code cannot be lifted in. A fresh `origin/master` build runs Qwen dense MTP end-to-end (the verified path), but loses our NUMA/CPU kernels — so the deploy choice is fresh-upstream (loses kernels) vs a focused multi-session reimplementation in our idiom. Source: [qwen-mtp-llamacpp-port.md](../handoffs/active/qwen-mtp-llamacpp-port.md).
- **DeepSeek-V4-Flash (284B / 13B-active, new CSA+HCA+indexer+compressor+manifold-HC arch) CPU throughput gate provisional FAIL: 9.13 t/s vs an 18 t/s floor.** Three independent measurements cluster 8–11 t/s via the antirez mainstream-lineage fork (Strategy B, which lacks our AVX-512BW/CCD kernels). V4's effective per-active-param compute is ~2.5× gemma4's, and its F16 HC/compressor/indexer components (2× the BW of Q4_K) dominate the bandwidth budget — the 18 t/s floor (set as gemma4 76.5 × 4/13 with a discount) ignored that overhead and needs a V4-arch-aware recalibration (honest range ~8–12 t/s). ik_llama-API translation (Strategy A) could reach ~12–15 t/s but still likely under the gemma4-calibrated floor. Source: [deepseek-v4-flash-cpu-port.md](../handoffs/active/deepseek-v4-flash-cpu-port.md).
- **Engram-family n-gram-lookup MoE is technically viable on CPU at production rates, but LongCat-Flash-Lite is dominated by our deployed worker.** Track A (LongCat-Flash-Lite Q4_K_M, 68.5B/4.5B-active, ~31.4B in n-gram tables) closed **negative**: 37.08 t/s decode (above the 15 t/s abandon floor) but **−51% vs gemma4-MTP worker** and **21/39 vs 26/39 sentinel quality** (math 0/6 structural). The *family* verdict is positive — n-gram-keyed-memory MoE inference runs at production-relevant CPU rates — and the EPYC 1.13 TB / ~460 GB/s node is in principle the best-provisioned single node for it (n-gram lookup wants only ~0.7 GB/s, **<0.2% of aggregate BW**); we simply have a better-tuned alternative deployed. intake-758 confirms n-gram-embedding scaling is a sparsity axis orthogonal to MoE (but a pretraining choice, not retrofittable onto GGUF production models). Source: [engram-conditional-memory.md](../handoffs/active/engram-conditional-memory.md).
- **NVFP4 (intake-756, official NVIDIA Qwen3.6-27B) is not_applicable on our hardware — GPU-native, not GGUF-loadable, and MI210 (gfx90a) has no FP4/FP8 tensor path** (matches the intake-339 precedent). It stays useful as an *external bar*: its FP8-parity accuracy table (MMLU-Pro 86.3 vs FP8 86.1; two-level block-FP8 + tensor-FP32 scaling) is a target for our CPU 4-bit path (Q4_K_M / TQ3), and the Apache-2.0 BF16 source is freely re-quantizable to GGUF. The sub-2-bit weight track (Sherry STQ1_0, PR #22836) remains monitor-only pending merge + QAT'd stack-relevant checkpoints. Sources: [tq3-quantization-evaluation.md](../handoffs/active/tq3-quantization-evaluation.md).
- **MoE-Spec (budgeted-expert verification) is a proven CPU mechanism with NO live consumer.** REAP-246B B=40 delivered +13–16% pp32 / +3% end-to-end (robust across builds); Coder-30B B=64 was not robust. But the REAP role is removed from production, and the frontdoor runs **zero spec-dec** today — there is nowhere to deploy `moe_spec_budget`. Reopen is chained to first enabling frontdoor spec-dec and measuring α(drafter→frontdoor) on CPU; do not schedule registry integration on the strength of the released gate alone. The transferable mechanism (aggregate routing softmax across the K verification tokens → top-B expert shortlist → mask before argsort) reduces distinct-expert DRAM reads, the same memory-tier lever as GPU HBM-union reduction. Source: [moe-spec-cpu-spec-dec-integration.md](../handoffs/active/moe-spec-cpu-spec-dec-integration.md).

### 2026-06-26 v6 cutover — historical one-kernel consolidation (production-consolidated-v6 + iqk), ik_llama deprecated

- **The EPYC production stack was cut over 2026-06-26 from a TWO-kernel setup (v5 llama.cpp + a separate ik_llama.cpp binary used only by the gemma worker) onto a SINGLE kernel: `production-consolidated-v6`** (canonical tree `/mnt/raid0/llm/llama.cpp`). v6 = upstream llama.cpp framework + native MTP/NEXTN speculative decoding + our forward-ported CPU kernels + **ik_llama's `iqk_mul_mat` AVX-512 GEMM kernels integrated into the fork, runtime-gated by `GGML_IQK=1`**. There is no longer a second binary; **ik_llama.cpp is fully deprecated.** The iqk kernels give ~+11% vs ik_llama on the gemma worker (and prefill +22–49%/decode +8–9% across the stack's quant patterns per the iqk-port findings below). This is now a historical one-kernel consolidation record; current production is `production-consolidated-v8`.
- **Status (do NOT read as verified production throughput):** v6+iqk cutover executed 2026-06-26 — registry/launcher/governance config converged (all no-inference gates green, 174 promotion-gate tests pass), canonical binary built; **live throughput + garbage verification PENDING** (operator deploy gate). Tracking: [v6-iqk-promotion.md](../handoffs/active/v6-iqk-promotion.md).
- **v6 CLI grammar change (operational note):** spec decode is now `--spec-type draft-mtp` + `--spec-draft-n-max N` (NOT the old ik `--draft-max` / `--spec-type mtp`); `--kv-hadamard` was removed (rotation is auto per the quantization page). ngram/prompt-lookup decoding is OFF across the production stack today but FULLY SUPPORTED in v6 (incl. server-side `--spec-type ngram-simple|ngram-cache|ngram-map-k|ngram-mod`, draft-model-free) — the documented zero-RAM fallback for the architect.

### New (2026-06-25, iqk-port complete + v6 consolidation + draft-head precision)

- **NUMA-concurrent MTP suite CORRECTED (`--no-mmap`, all 7 models) — 4×quarter wins aggregate throughput for ~all models; 1×full only for single-stream latency. The earlier "large-dense → 1×full" rule was a mmap-sharing artifact and is RETRACTED.** The first suite used **mmap** under `numactl --cpunodebind=N --membind=N`, so the N concurrent quarter instances shared ONE page-cache copy on a single node (bandwidth-starved), and the full cells inherited the quarter loads' node-local placement when run after them — contamination, not topology. Fix = **`--no-mmap`** (private node-local weight copy per instance) **+ `drop_caches` between models**. Corrected aggregate t/s, MTP-on (4×quarter / 1×full / 2×half): gemma-26B small MoE **109.6** / 49.1 / 83.3; gemma-31B dense **30.1** / 23.9 / 17.5; Qwen3.6-27B dense 20.0 / 15.8 / **20.2** (quarter≈half); Qwen3.5-27B hybrid-SSM **18.7** / 14.4 / 16.8; Qwen3.6-35B Q8 frontdoor MoE **71.9** / 42.3 / 65.3; Qwen3-Next-80B SSM-MoE (no MTP) **49.2** / 23.8 / 39.8; Qwen3.5-122B architect MoE **28.3** / 18.0 / 26.2. **4×quarter wins for every model** (6/7 outright; Qwen3.6-27B quarter≈half) — including the large/dense ones (gemma-31B 30.1 > full 23.9; 122B-A10B 28.3 > full 18.0). 1×full wins only single-stream **latency** (per-instance t/s = aggregate / n_inst). **2×half is never the best** (confirms the dual-half negative finding). **Production update 2026-06-27:** role-equivalent N12 A/Bs later refuted the private `--no-mmap` flip for `vision_escalation`, `frontdoor`, and `ingest_long_context`; keep the current shared-mmap production launch for those roles unless a materially different protocol is measured. Sources: [iqk-port.md](../handoffs/active/iqk-port.md) (NUMA Phase-3B), [progress 2026-06-25](../progress/2026-06/2026-06-25.md), [progress 2026-06-27](../progress/2026-06/2026-06-27.md), [numa-private-weights-quarter-roles.md](../handoffs/active/numa-private-weights-quarter-roles.md).
- **ARCHITECT MTP CONFIRMED LIVE — the prior "no-MTP / GDN-wall" dismissal is refuted end-to-end.** Qwen3.5-122B-A10B (architect) loads and drafts with NO spec-assertion crash, validated download → load → draft → measure. The earlier "0.56× dead-end / GDN wall" verdict was measured on an old fork without `draft-mtp` (stale); qwen35moe uses the same size-independent NEXTN loader as the +103% frontdoor and its MTP blocks are dense attention, not recurrent. Under the corrected `--no-mmap` suite its best aggregate operating point is **4×quarter+MTP 28.3 t/s** (> full 18.0, > half 26.2) — the same "quarter wins aggregate throughput" bucket as the rest of the stack (the earlier "large-active → 1×full" placement was the mmap contamination artifact). Sources: [iqk-port.md](../handoffs/active/iqk-port.md), [progress 2026-06-25](../progress/2026-06/2026-06-25.md).
- **Root cause of the prior NUMA contamination: mmap page-cache sharing, NOT membind and NOT host noise alone.** A/B proof: gemma-26B 4×quarter **43.5 t/s (shared mmap) → 119.5 t/s (`--no-mmap` private node-local) = ~2.7×**; a dedicated-config A/B (both arms clean) read 64–73 t/s, so the launch params were fine — the bug was mmap-sharing + cross-cell cache contamination. The `numactl --membind` hypothesis (from an even earlier note) was already refuted (membind vs interleave 9.92 vs 10.05; settings A/B 11.73 vs 11.88) and is NOT reintroduced — membind is neither cause nor fix. The fix is `--no-mmap` (one private copy per instance) + `drop_caches` between models. Absolutes remain throttle-suspect at the host's ~4-week uptime (+ ~12 h sustained bench → cross-model drift); only per-model topology/MTP deltas in the fixed window are load-bearing. Sources: [iqk-port.md](../handoffs/active/iqk-port.md), [progress 2026-06-25](../progress/2026-06/2026-06-25.md), [orchestrator_numa_finding](../handoffs/active/numa-private-weights-quarter-roles.md).
- **iqk-port Stage 1+2 complete: prefill +22–49%, decode +8–9% across all stack quantization patterns, byte-identical.** The `iqk_mul_mat` AVX-512 kernels from ik_llama were ported into `production-consolidated-v6` (branch `iqk-port`, worktree `llama.cpp-v6-iqk`). Flag-gated `GGML_IQK=1`, single binary. Results (same-build A/B, llama-bench): gemma-4-31B Q4_K_M prefill +49%/decode +7.9% (byte-identical); gemma-4-26B-A4B MoE Q4_K_M prefill +22.5%/decode +8.8% (byte-identical); Qwen3.6-35B-A3B Q8_0 prefill +24.9%/decode ~0 (BW-bound as expected; correct output). Two root-cause fixes: (1) `iqk_row_size()` shim to stop `type_traits[]` OOB on ik-only repacked types; (2) `ggml_repack_get_optimal_repack_type` guard to prevent `CPU_REPACK` intercepting iqk-supported matmuls before the iqk hook. Deploy gate: operator-run eval-suite parity (Q8_0 non-bit-exact by design). Sources: [iqk-port.md](../handoffs/active/iqk-port.md), [progress 2026-06-25](../progress/2026-06/2026-06-25.md).
- **Draft head precision is a major MTP performance lever, specific to models with a separate vocab-embedding head.** gemma-4-26B-A4B same-window A/B: f16 head (855 MB) at 33.48 t/s → Q8_0 head (461 MB) at 42.78 t/s (+28%) at the same acceptance rate (0.796). v6-iqk + Q8 head (42.78 t/s) beats ik_llama (38.63 t/s, 0.655 acceptance) by +11% — the consolidation gap is closed and reversed. The bandwidth estimate (~1% impact) was wrong; the f16 token_embd tensor (262144×1024) dominates the draft forward pass. **Only models with a separate f16 vocab-embedding draft head are affected.** Qwen NEXTN heads share token_embd at the main model's quant (Q4/Q8); no equivalent lever exists there. Sources: [iqk-port.md](../handoffs/active/iqk-port.md), [progress 2026-06-25](../progress/2026-06/2026-06-25.md).
- **v6 consolidation F1 (paged-attn) resolved: "never activates" was a filtered INFO log, not a broken code path.** Verified end-to-end via ERROR-level probes: plain attention (Qwen3.6-35B Q8) byte-identical to paged-off; SWA/iswa (gemma-4-31B) activation WARN fired ×2. Two fixes landed on branch `f1-paged-attn`: iswa graph block-table wiring (genuine missing piece for SWA models); activation log INFO→WARN (makes activation observable). Opt-in/off-by-default/bit-exact. Pattern: "never activates / no log fires" ≠ dead code — check the log level filter before declaring a code path broken. Sources: [llamacpp-v6-consolidation.md](../handoffs/active/llamacpp-v6-consolidation.md), [progress 2026-06-25](../progress/2026-06/2026-06-25.md).
- **v6 F5 122B architect: validated with f16 K; quantized-K shift crashes (not a production blocker).** The IMROPE K-shift fires and generates 600 tokens coherently at 13.65 t/s with f16 K. With Q4_0 K (the architect's prod cache), the shift crashes in `ggml_compute_forward_dup` — the well-known quantized-K + rope-shift CPU-backend gap. Not a blocker: neither `--context-shift` nor `--cache-reuse` is enabled in production config (zero matches in orchestrator config). Workaround if ever needed: f16 K. Sources: [llamacpp-v6-consolidation.md](../handoffs/active/llamacpp-v6-consolidation.md), [progress 2026-06-25](../progress/2026-06/2026-06-25.md).
- **gemma MTP confirmed on v6: ik_llama worker retirement viable.** gemma-4-26B-A4B MTP on v6 required (1) correct-lineage base model (self-convert from `google/gemma-4-26B-A4B-it`, not the unsloth QAT base — wrong-lineage weights produced 0% acceptance); (2) chat path via `--jinja`/`/v1/chat/completions` (instruct model, raw `/completion` degenerates). v6-iqk + Q8 head at 42.78 t/s beats ik_llama at 38.63 t/s. Sources: [llamacpp-v6-consolidation.md](../handoffs/active/llamacpp-v6-consolidation.md), [progress 2026-06-25](../progress/2026-06/2026-06-25.md).

- **MI210 GPU work should start with verify/profile harness discipline, not kernel generation alone (2026-06-05).** The active ROCm kernel-authoring cluster frames the first useful deliverable as a local MI210 verify/profile/benchmark backend with reproducible artifacts, not an agent that writes kernels directly into production. This keeps generated GPU kernels behind correctness tests, profiler evidence, and an explicit backend contract before any routing or inference path consumes them. Sources: [agentic-rocm-kernel-authoring.md](../handoffs/active/agentic-rocm-kernel-authoring.md), [rocm-verify-profile-backend.md](../handoffs/active/rocm-verify-profile-backend.md), [agentic ROCm deep dive](../research/deep-dives/agentic-rocm-kernel-authoring-geak-synthesis.md).
- **GPU drafter work is a frontdoor-acceleration path, not a replacement for CPU topology optimization.** The GPU acceleration sources keep MI210 drafter experiments separate from CPU serving claims: CPU NUMA/matrix gates still govern production placement, while GPU experiments need their own verify/profile evidence and quality-preserving acceptance criteria before they can alter frontdoor or spec-dec routes. Sources: [gpu-acceleration-path.md](../handoffs/active/gpu-acceleration-path.md), [gpu-drafter-mi200-investigation.md](../handoffs/active/gpu-drafter-mi200-investigation.md), [single-instance-system-tuning.md](../handoffs/completed/single-instance-system-tuning.md).

- **NUMA is the dominant optimization**: 4-way NUMA quarter pinning delivers 6-7x aggregate throughput on models up to 65 GB. Single-node (96 threads on one NUMA node) is 1.85x faster than all-cores (192 threads) for MoE models because cross-NUMA memory access penalty is devastating. [progress/2026-03-18, numa-orchestrator-deployment.md]
- **MoE models are NUMA-sensitive, dense models are compute-sensitive**: Models with few active parameters (MoE) see 6-7x gains from NUMA pinning because cross-node memory access dominates cheap compute. Dense models see only ~2x because all parameters are active and 48 threads is not enough compute. Large hybrids (122B+) are recurrent-bottlenecked at ~12 t/s regardless of NUMA config. [numa-orchestrator-deployment.md]
- **Node 1 is ~85% of Node 0 performance**: Consistent across all configs, likely due to first-touch page cache bias (Node 0 loads first, OS caches pages there). Production should account for this asymmetry. [progress/2026-03-18]
- **Concurrent vs sequential cross-node**: When both NUMA nodes generate simultaneously, per-instance throughput drops ~25% (13.3 to 9.4 t/s) due to inter-node traffic. Sequential queries to alternating nodes avoid this penalty. [progress/2026-03-18]
- **Q4_K_M is optimal for hybrid models**: Recurrent state update (constant cost) fills most compute in hybrid architectures. Q8 costs 17-39% speed for marginal quality gain. Q4_K_M is also optimal for the coder: f16 offers zero quality improvement despite halving speed and using 3.5x RAM. [ssm-hybrid-acceleration.md, numa-orchestrator-deployment.md]
- **SpecExec thesis partially refuted on this hardware**: Verification cost scales 4-5x from N=1 to N=64 for Q4_K_M models due to dequantization compute overhead. Only f16 models (no dequant) show near-flat verification (1.69x at N=64). The pure bandwidth-bound regime SpecExec assumes does not hold for quantized CPU inference. [specexec-verification-profile.md]
- **NUMA distribute is dramatically better for single-token processing**: 75-94% faster for large models vs isolate mode. The gap narrows at larger batch sizes. Production should always use --numa distribute for single-instance models. [specexec-verification-profile.md]
- **Model load times scale linearly**: 0.5-1.5B models: 2-5s (acceptable for WARM tier). 7-32B: 10-20s. 80-235B: 30-60s. 480B: 60-90s. Parallel tensor repack on production branch reduces load time by 2.2x. Sequential model loading is mandatory -- concurrent mlock crashes the system. [04-production-server-stack.md]
- **--mlock eliminates 30x cold-start penalty**: Measured in S2 benchmarks. All HOT-tier models now use --mlock (~701 GB locked, 429 GB remaining for KV caches and OS). The host requires unlimited memlock ulimit. [numa-orchestrator-deployment.md]
- **Hyperthreading provides no benefit**: 96 physical cores at -t 96 outperforms 192 threads for compute-bound LLM inference. Hyperthreads add cache contention without meaningful throughput gain. [01-hardware-system.md]
- **Draft model speed varies 4x within same parameter class**: Qwen2.5-Coder-0.5B generates at 185 t/s vs Qwen3.5-0.8B at 44 t/s. Architecture matters more than parameter count for draft models. [specexec-verification-profile.md]
- **192-thread pytest is catastrophic**: Each worker loads its own embedding models (~3 GB), and 192 workers exhaust 1.13 TB RAM. Fixed with lazy model loading in test mode, memory guard at 100 GB minimum free, and blocking pytest -n auto. [02-storage-safety.md]
- **Comprehensive spec param sweep (1,290 measurements) overturned multiple prior assumptions**: Tree speculation helps Q4KM coders (was assumed harmful), hurts 480B MoE (-19%, was assumed beneficial), and registry throughput values were 2.3-3.6x inflated from warm-cache measurements. Never trust single-run benchmarks. [progress/2026-03-21]
- **Prompt lookup (--lookup) segfaults on Qwen3.5 hybrid SSM models** after 1-3 prompts due to prompt cache + recurrent state corruption. moe6-only is stable. Do not use until fixed upstream. [numa-orchestrator-deployment.md]
- **NUMA_MIRROR per-node weight replication does NOT deliver on single-socket NPS4 — DECISIVE NEGATIVE finding (MoE proxies tested)**. The Phase 1c implementation (commit `29a69599a` in llama.cpp-experimental) is bit-exact and correct: per-CPU_REPACK-buffer side-table tracks N anon-mmap+mbind replicas, `init_tensor` fans out `data_per_node[]`, `set_tensor` mirrors writes, and the `forward_mul_mat`/`forward_mul_mat_id` hot path was migrated to `tensor_data()` so threads on nodes 1..3 read THEIR replica. But the Phase 2 throughput gate FAILED: −1.0% on Coder-30B Q4_K_M tg128 (48.16 → 47.66), +0.6% on Qwen3.6-35B Q8 tg64 (23.30 → 23.45) — both within run-to-run noise. **Root cause**: single-socket NPS4 is DRAM-channel-bound, not fabric-bound. Per-thread BW share is 460 / 96 = 4.79 GB/s regardless of NUMA placement; with mirror, each node's 24 threads share 115 GB/s = identical 4.79 GB/s/thread. CPU24's perf-record memory-stall finding was correct but could not distinguish fabric-stall from DRAM-channel-stall — Phase 1c cleanly rules out the fabric-stall hypothesis. The vproxy-tools fork's reported +62%/+34% gains were on **two-socket** configurations where cross-SOCKET fabric IS the binding constraint. **Implication (NARROWED 2026-04-27 evening per peer review)**: the per-NUMA-node-weight-replication lever and per-CCD-mbind lever are falsified for single-socket NPS4; multiple software levers remain open and tracked (libomp completion, CPU22 work-stealing mechanism, CPU23 interference + 5-model coverage, MoE-Spec, ZenDNN, PGO/LTO, BOLT/FDO, prefill, parallel-slot). The earlier "software-level CPU optimization runway exhausted" framing was an over-generalization from one falsified hypothesis. Dense/hybrid architecture coverage (Qwen3.5/3.6-27B) for the negative finding is a small remaining gap, deferred to remediation Phase 2.6. [numa-mirror-integration.md, progress/2026-04-27]
- **Closure inflation is a recurring failure mode in this project's optimization tracks**. The pattern: agent falsifies one concrete hypothesis (e.g., NUMA_MIRROR's +25% gate) → generalizes to a broader exhaustion conclusion (e.g., "software runway exhausted") → leaves multiple track gates unmet, multiple required matrix pieces un-run, and stale/contradictory text fragments in the handoffs. Peer review on 2026-04-27 evening identified 10 such inflation events across CPU21/22/23/24/25 and the master index. Remediation policy adopted: any closure claim must point to ALL track-stated gates being met OR explicitly state "narrower scope; broader claim NOT made". CPU20 rigor protocol updated with retroactive artifact-bundle backfill policy. Closure-inflation feedback memory `feedback_closure_inflation.md` created as a persistent reminder. [progress/2026-04-27, ~/.claude/plans/nifty-discovering-allen.md, feedback_closure_inflation.md]
- **NUMA_MIRROR Phase 0/1a/1b framework is landed and bit-exact** on `feature/cpu-ep-inter-process` of llama.cpp-experimental. The migration involved 164 `tensor->data` references across 11 files moved to the `tensor_data()`/`tensor_set_data()` accessor (commits `9b1dbf4dd`, `b9920cc44`); `struct ggml_tensor` gained `data_per_node[GGML_NUMA_MAX_NODES]` (commit `ca39cb80a`); a TLS setter (`getcpu(2)` → `ggml_current_numa_node`) lands at graph-compute entry (commit `90a17af62`). PPL chunks 1-12 on Coder-30B Q4_K_M are byte-identical to a `-march=znver5` baseline build (chunk1=7.4537, final=11.1215). [numa-mirror-integration.md, progress/2026-04-27]
- **A mmap-only mirror is insufficient for our build** — for Coder-30B Q4_K_M, ~17 GB total but **13.4 GB lives in CPU_REPACK** (CPU2's AVX-512BW 8x8 interleaved layout) and only ~4.3 GB stays in the original mmap. Phase 1c must mirror at the **buffer** level — both the file mmap AND the CPU_REPACK output — or 79% of weight reads stay cross-NUMA and the +25% gate fails. [numa-mirror-integration.md]
- **Hugepages are NOT required for NUMA_MIRROR** on this host. `HugePages_Total = 0` for both 2 MB and 1 GB sizes across all 4 nodes. The Phase 1c path uses `mmap(MAP_ANONYMOUS) + mbind(MPOL_BIND)` on regular 4 KB pages with THP opportunistic 2 MB promotion — no kernel reboot needed. A later Phase 1d can switch to 1 GB hugepages if a reboot becomes acceptable. [numa-mirror-integration.md]
- **Always compare apples-to-apples build flags when validating bit-exactness**. A 0.116-PPL chunk-1 discrepancy that initially looked like a NUMA_MIRROR Phase 1a bug turned out to be pure `-march=znver5` codegen drift in fp ops vs an unflagged `-O3` build. Building a third `build_znver5/` (znver5 only, no MIRROR) restored bit-exactness. Lesson: any baseline comparison for a feature flag must hold all OTHER compile flags constant. [progress/2026-04-27]
- **CPU2 Q6_K AVX-512BW 8x8 kernel + T1 prefetch landed** (CPU2 Sessions 16-18). Q6_K SIMD kernel body (~95 lines of intrinsics) using `block_q6_Kx8` interleaved layout, validated bit-exact PPL = 9.8567. Q6_K with `_MM_HINT_T1` prefetch on ql/qh/q8.qs/scales = +0.7%. Q4_K T1 prefetch tested and **reverted** (−4%) — Q4_K block layout has tighter cache footprint that doesn't benefit from prefetch. Lesson: prefetch effectiveness is per-quant; never assume a pattern that works for Q6_K transfers to Q4_K. [cpu-shape-specialized-gemv-decode.md]
- **libomp delivers +6.4% on Coder-30B-A3B-Instruct Q4_K_M** apples-to-apples vs gcc+libgomp+znver5 (53.28 ± 0.11 vs 50.06 ± 0.05, 5-rep tg32 at proper canonical). Mostly model-specific: Qwen3.6-35B Q8 frontdoor +0.8% (within noise), REAP-246B -0.8% (within noise). Mechanism hypothesis: Coder-30B-A3B has thinner per-thread row-shard tiles (3.3B activated params) that benefit from libomp's lower-overhead barrier and task scheduling; larger MoE and BW-bound classes saturate on memory bandwidth before runtime overhead matters. PPL bit-exact within compiler determinism (clang+libomp PPL 11.1146 vs gcc+libgomp 11.1215, Δ 0.0069 from clang-vs-gcc fp-codegen drift, NOT quality regression). **v5 cherry-pick recommendation**: ship libomp-built llama-server (clang-20 + -march=znver5) as universal binary — single audit story, +6.4% on Coder-30B specifically, neutral elsewhere. Build dependency: `clang-20` package (~150 MB). [cpu-openmp-runtime-scheduling-matrix.md, data/cpu_optimization/2026-04-28-cpu21-libomp-chunks/]
- **`OMP_SCHEDULE=guided,16` is a model-specific +3.6% under libgomp on Coder-30B Q4_K_M** (3.5σ verified) but NOT a universal win — neutral on Qwen3.6-35B Q8 and REAP-246B. Under libomp it shrinks to +1.2% because libomp's default scheduling is closer to optimal than libgomp's. Per-role opt-in candidate for Coder-30B-A3B-Instruct workloads only; do NOT default system-wide. [cpu-openmp-runtime-scheduling-matrix.md]
- **First-decode TTFT amplification under concurrent prefill is severe on sync-bound MoE class**. 9.6× on Coder-30B Q4_K_M (rep-1 = 4.77 t/s vs baseline 47.99), 1.15× on Qwen3.6-35B Q8_0 BW-bound, 1.08× on Qwen3.6-27B Q8 dense/hybrid. Mechanism: llama-server's continuous batching makes the first new decode-after-prefill-arrival wait for the current prefill ubatch (Coder-30B's 137 t/s × 2048 batch = 14.9s/batch; rep-1 wait ~ half-batch ~ 7s). Steady-state continuous batching is essentially baseline within ±2% on all 3 classes — rep-2-onward decodes interleave efficiently with ongoing prefill. Single-user regime: rep-1 spike happens once per session and is not actionable. Multi-tenant regime: chunked-prefill could in principle reduce ubatch wall time. [cpu-context-regime-coverage.md, data/cpu_optimization/2026-04-28-cpu23-interference-metrics/]
- **Dense/hybrid is dramatically more cache-efficient than MoE classes** despite lower IPC. CPU24 perf-stat at 96-thread proper canonical: dense Qwen3.6-27B Q8 has 2.6% cache miss + 8.9% cross-NUMA fill fraction vs MoE classes' 7-11% miss + 25% cross-NUMA. Mechanism: dense streams weights uniformly across threads with no MoE expert-routing thrash. Despite cleaner memory pattern, dense IPC is the LOWEST of all 4 classes tested (0.175) because pure DRAM streaming has no compute-bound segments to overlap. MoE classes have expert-routing/gating compute that lifts IPC slightly even though it thrashes caches. **Bottleneck CLASS is universal across architectures (memory-stalled compute kernels), but MECHANISM differs**: MoE thrashes caches + pays per-token cross-NUMA latency; dense pays pure DRAM-streaming bandwidth without thrashing. Refines CPU24 attribution. [cpu-uncore-fabric-attribution.md, data/cpu_optimization/2026-04-28-cpu24-minimax-and-dense/]
- **CPU22 dynamic MoE work-stealing gate FAILED** on all 3 sync-bound MoE models (5-rep): -2.3% Coder-30B, -0.3% Next-80B (noise), -0.8% REAP-246B (noise). Prototype implemented as env-gated `GGML_EP_WORK_STEALING=1` with single global tile-array + atomic counter. PPL bit-exact verified at 12 chunks. The single-atomic contention overhead at 96 threads (~30 ns × ~12K tiles = ~360 µs/op × ~100 ops/token = ~36 ms wall) dominates over the limited 15% sync-share gain ceiling per CPU24. Existing per-expert chunked path already has chunk-level work-stealing (atomic_fetch_add per expert; threads iterate independently with no per-expert barrier), so the marginal improvement from inter-expert global queue is small. Track CLOSED via test (replaces prior closure-by-inference). Code preserved compile-flag-gated default-OFF. [cpu-dynamic-moe-load-balancing.md, data/cpu_optimization/2026-04-28-cpu22-work-stealing/]
- **Q6_K AVX-512BW 8x8 SIMD kernel passes full 32-chunk WikiText-2 PPL bit-exact** on both Coder-30B Q4_K_M (PPL 8.2622 ± 0.27495) and REAP-246B Q4_K_M (PPL 8.1396 ± 0.24168). All 32 chunks byte-identical between env=0 (generic Q6_K vec-dot) and env=1 (AVX-512BW SIMD path). `GGML_Q6_K_8X8_AVX` flipped from default-OFF-pending-PPL-gate to **production-ready opt-in**. v5 cherry-pick candidate at default-OFF with +0.4-0.7% throughput on Q4_K_M MoE class. [cpu-shape-specialized-gemv-decode.md, data/cpu_optimization/2026-04-28-cpu2-q6k-full-ppl/]
- **Statistical-significance threshold for sub-5% deltas requires ≥5 reps on this hardware**. Discovered via CPU22 Phase 3: initial 3-rep Next-80B Q4_K_M showed env=1 = 22.65 t/s vs env=0 = 21.31 t/s (+6.3%, would have been a positive signal). Re-running at 5 reps converged both paths to ~23.3 t/s (Δ -0.3%, neutral). The 3-rep result was a measurement artifact from cache-warmup state divergence between runs. **Lesson**: 3 reps is insufficient for tight gates on this hardware; ≥5 reps required for sub-5% deltas; consider ≥10 reps for tighter ones. [data/cpu_optimization/2026-04-28-cpu22-work-stealing/]
- **LLVM PGO is universally positive across all 4 production model classes** (CPU11, 2026-04-28). Apples-to-apples vs the libomp build at fixed -march=znver5: +3.2% Coder-30B Q4_K_M (56.84 → 58.65), **+6.6% Qwen3.6-35B Q8_0 (25.40 → 27.08, biggest absolute win — frontdoor BW-bound class loves PGO)**, +1.3% REAP-246B Q4_K_M (DRAM-saturated, smallest delta), +2.4% Qwen3.5-27B Q8_0 dense/hybrid. PPL bit-exact (Coder PPL 11.1146 byte-identical to pre-PGO build — PGO does not introduce reassociation, only branch layout / inlining / register allocation). Mechanism: PGO is orthogonal to libomp (codegen change vs runtime change) and applies to the whole CPU backend hot path (`mul_mat_id` dispatcher, Q4_K/Q8_0 dot loops, ggml function preludes, libomp's own barrier code). Compounding stack reaches +21.5% on Coder-30B vs gcc+libgomp+no-march baseline. **v5 cherry-pick recommendation: ship clang + libomp + -march=znver5 + PGO as the universal production binary**. Build adds: `apt install clang-20 libclang-rt-20-dev llvm-20`; ~30-min profile-and-rebuild cycle. [cpu-inference-optimization-index.md, data/cpu_optimization/2026-04-28-cpu11-pgo/]
- **LLVM BOLT post-link optimization is workload-sensitive — per-role opt-in only, NOT a universal v5 cherry-pick**. Apples-to-apples on top of PGO with merged 4-model fdata profile (CPU12, 2026-04-28): **+2.1% Coder-30B (58.65 → 60.54 t/s, the new compounded ceiling)**, −1.2% Q8 frontdoor, −0.1% REAP-246B (neutral), −0.9% dense 27B. PPL bit-exact (BOLT only changes block layout / function reordering / hot-cold split, not instruction encoding). Mechanism: BOLT's wins (i-cache density, function-pair locality, cold split) only fire when the LBR profile matches runtime workload — Q8 uses different inner kernels (Q8_0 vs Q4_K dot loops) and dense doesn't even hit `mul_mat_id`, so reordering for Coder paths actively hurts. Total compounded gain on Coder-30B vs gcc+libgomp baseline reaches **+25.4% / 60.54 t/s** with the full PGO+BOLT stack. **Deployment**: ship PGO-only as the universal production binary; optionally ship a per-role BOLT binary for the dedicated Coder-30B-A3B-Instruct role. Do NOT ship a single BOLT binary universally — cross-model regressions on Q8/dense erase the Coder gain. [cpu-inference-optimization-index.md, data/cpu_optimization/2026-04-28-cpu12-bolt/]
- **LLVM LTO is NEUTRAL on top of PGO** — confirmed empirically, not just exploratory. PGO+LTO measured 28.09 ± 0.04 t/s vs PGO alone 28.38 ± 0.08 t/s on Coder-30B Q4_K_M tg32 at warm position 2-3 of a 4-way sweep with `-pp 64` prefill warmup. Δ −1.0% within tight std (≤0.08 on both). Position-confound test (forward + reverse order) confirms order-independence. Mechanism: PGO with `-fprofile-instr-use` already enables clang to inline across translation units when the profile shows it's hot. LTO adds *additional* cross-TU inlining for cold paths, but those don't matter for the hot ggml decode kernels. Decision: **do NOT add LTO to v5 build flags** — keep `clang+libomp+znver5+PGO`. [cpu-inference-optimization-index.md, data/cpu_optimization/2026-04-28-cpu12-bolt-libomp/]
- **BOLT-rewriting libomp.so itself is FUNCTIONAL but does not deliver a measurable win under tested conditions**. Pipeline (CPU12 extension, 2026-04-28): downloaded `openmp-20.1.8.src.tar.xz` from the LLVM 20.1.8 release, built libomp from source with `clang-20 + -march=znver5 -O3 -Wl,--emit-relocs` (1.68 MB output, vs 1.21 MB system libomp — extra size from `.rela.text` for BOLT to consume), captured per-class perf data with `LD_PRELOAD=$CUSTOM_LIBOMP perf record -e cycles:u -j any,u`, generated 4 fdata files via `perf2bolt-20`, BOLT-rewrote with `llvm-bolt-20 -reorder-blocks=ext-tsp -reorder-functions=cdsort -split-functions -split-all-cold` using single-model coder fdata (the merged.fdata fell into legacy format and llvm-bolt rejected it). PPL bit-exact (Coder-30B chunks 1-12 = 11.1146, byte-identical to all prior PGO/BOLT runs). But under measurement: BOLTed libomp at warm position 2 (29.58 ± 0.04) is at parity OR slightly worse than system libomp at warm position 4 (31.95 ± 0.09); position effect ≥ BOLT delta. System noise was high (megasync at 95% CPU all afternoon, plus cumulative cache pressure from 4 build trees and LLVM source extraction caused 2× absolute throughput degradation vs morning). Decision: **do NOT add libomp-BOLT to v5**; reopen ONLY if a quieter measurement window confirms a clean signal. [cpu-inference-optimization-index.md, data/cpu_optimization/2026-04-28-cpu12-bolt-libomp/]
- **Kolinko Effort/bucketMul (Apple Metal, 2024) audited and DECLINED for EPYC port** (intake-528, deep-dive 2026-05-08). The Apple-Silicon-only structured-sparse GEMV achieves 50-70% of M2 BW at 50% effort and ~2× at 25% effort, but author concedes via own KL-distance test that it does not beat plain quantization on quality-per-speed. Last code commit 2024-04-25 = 24+ months frozen; issue #5 still open on Mac-only compilation; no third-party port in 25 months. Three portable algorithmic ideas survive the audit but none individually justifies the ~1-staff-month direct-port cost (new ggml repack format + AVX-512 kernel): (1) **load-time trailing-bucket skip** as ad-hoc distillation in any sorted-bucket repack format, (2) **per-token effort-dial** as a quality-budget primitive that could compose with routing-intelligence / per-request-reasoning-budget / decision-aware-routing, (3) **probe-as-diagonal-sample** (`probes[i] = w[i + i·cols]`) as O(1)/row magnitude estimator vs. Deja Vu's learned predictor. Realistic best-case EPYC upside 1.2-1.5× at 30-50% quality cost vs Q4_K_M — below already-shipped MTP 2.98× (intake-527) and CPU2 31.8% @ 1t. The deep dive itself is the closure record. Re-surface triggers documented in intake-528 verdict_justification: (a) sorted-bucket repack lands in ggml for unrelated reason, (b) routing/budgeting handoff activates with a kernel that supports proportional effort, (c) dynamic-activation-sparsity (Deja Vu / PowerInfer / TEAL family) re-enters scope, (d) Apple-Silicon backend re-enters scope. [research/deep-dives/kolinko-effort-engine-deep-dive.md, intake-528]
- **System noise can degrade absolute CPU throughput by 2× while leaving relative comparisons within a single sweep intact**. Same `clang+libomp+znver5+PGO` build measured 58.65 ± 0.24 t/s on Coder-30B Q4_K_M tg32 in the morning and 27.77-31.95 t/s in the afternoon of the same day. Causes identified: a single-thread heavy process (megasync at 95% CPU on 1 of 96 cores), 5-6 parallel claude/firefox/python processes holding 5-10% CPU each, and cumulative page-cache + NUMA pressure from 4 build trees + LLVM source extraction + 3 sequential bench sweeps. Critically, RELATIVE comparisons within a single sequential sweep (positions 2-4 of a 4-build sweep, all measured back-to-back inside <2 min) remain reliable: tight std (≤0.09) on warm positions, position effect ≤2 t/s. So sub-percent A/B testing within a single sweep is still possible even at degraded absolute throughput. Implication for measurement protocol: never compare absolute t/s across sessions hours apart; always measure A and B sequentially with a discarded warmup bench, and accept that the absolute scale may be 2× lower than another session. [data/cpu_optimization/2026-04-28-cpu12-bolt-libomp/]
- **DSA (Dynamic Sparse Attention) cache/runtime is now wired for GLM on current source; the open question is sparse compute, not basic model wiring.** Experimental-v7 `3dee86a5a` routes `LLM_ARCH_GLM_DSA` through `llama_kv_cache_dsa` and the DeepSeek32 DSA graph, and the current-source exact smoke returned `READY` with `Lightning Indexer enabled`. The remaining work is D2 profiling/implementation to determine whether final attention is dense-mask or real sparse, plus the long-context quality gates. [llama-cpp-dsa-contribution.md, glm51-reap-cpu-evaluation.md]
- **One DSA forward-pass implementation is a multi-model-for-1 hardware unlock**. DeepSeek-V3.2 (671B-class MoE), GLM-5.1-555B-A14B, and now GLM-5.2 (754B GLM-MoE-DSA, MIT, 1M context — intake-699) all share the identical DSA indexer + KV-cache infrastructure. The instant PR #21149 stabilizes — with or without our contribution — the entire GLM-5.x family unblocks on the 1.13 TB EPYC the same week. For GLM-5.2 the gating constraint is the DSA forward pass, *not* storage: the unsloth UD-IQ2 dynamic quant (~238 GB) already fits the raid0 free space. This converts the earlier "2-models-for-1" framing into "multi-model-for-1" and makes the unblocked-RAM-budget the binding question, not the missing weights. [llama-cpp-dsa-contribution.md, glm51-reap-cpu-evaluation.md]
- **A CPU image-generation role is deployed (`sd_server` / ERNIE-Image-Turbo via stable-diffusion.cpp) — the EPYC stack is no longer LLM-only**. This corrects the standing "no GPU, no image role" assumption: image generation runs on CPU today via stable-diffusion.cpp, independent of any GPU acquisition. The practical hardware implication is that the HOT/WARM/COLD RAM budget and NUMA-pinning discipline now also govern a diffusion workload, and a future on-prem diffusion-RL fine-tune (e.g. UniRL Flow-DPPO) would be gated only by "no training GPU", not by the absence of an image model to tune. [gpu-acceleration-path.md, intake-709]
- **Single-instance batched decode (CPU14) has still never been measured to claim grade; the first scout points to `-np 8` as the candidate operating point but with severe tail-latency cost**. A non-decision-grade scout (host uptime >1 week, `numa_balancing=0`, so `decision_grade=false`) showed Qwen3.6-35B-A3B Q8_0 peaking at `-np 8` (≈1816 tasks/h, +41% aggregate vs `-np 1`) while p95 latency rose ~3.8×; the dense Qwen3.6-27B Q8 control scaled *more strongly* through `-np 8`. `-np 16` regressed on both. The durable P-BENCH-3 harness (`server_np_sweep.py`) and E2 eval-driver A/B coordinator (`e2_eval_driver_ab.py`) are staged in the clean-window manifest, fail closed under host-health warnings, and verify server PIDs are dead post-run — but a reboot/quiesce window is still required before any keep/kill claim. Pitfall recorded: MoE batching is weaker than dense (distinct tokens hit distinct experts → expert-weight traffic grows with batch), so a dense control is mandatory and the 9.6× rep-1 TTFT amplification under concurrent prefill must be reported separately from steady-state per-stream decode. [batched-decode-measurement.md, fable5-findings-06-kernel-and-concurrency.md]
- **The eval-batch activation window now has claim-grade smoke/rollback evidence, but the default path is still unchanged.** Root `f755dbc4` added the stdlib handoff dashboard hub/timeline builder/tests, orchestrator `132c595d` finalized `handoff_dashboard` service/link and env propagation, and the `status=smoke_passed_rolled_back` activation window launched `eval_batch_frontdoor` on port `18070`, attested `eval_batch_serving=true` on API workers, passed smoke (`ok`), hit the expected tap port, then rolled back and stopped the frontdoor. Representative quality/reliability/throughput telemetry remains the next gate before any default EvalTower path change. [progress 2026-07-05](../progress/2026-07/2026-07-05.md), [batched-decode-measurement.md](../handoffs/active/batched-decode-measurement.md)
- **UniRL (Tencent Hunyuan) is a DGX-gated watch-item, not_applicable on CPU-only EPYC (2026-06-20)**. UniRL is a multi-GPU RL post-training framework (Ray DevicePool + FSDP + Transfer-Queue weight sync) for diffusion/AR/multimodal generators — training code only, no inference/serving path, and no benchmark numbers in its README (all observations, never decision-gating). It cannot run on the CPU-only stack: the blocker is the absence of a *training* GPU. Two forward-looking transfer hooks were flagged-not-dismissed: (a) its diffusion-RL algorithm Flow-DPPO could one day fine-tune the deployed `sd_server` image role, and (b) its LLM-targeted token-level trust-region variants (CPPO/DRPO; arXiv 2606.10968 / 2606.09821) could seed a future on-prem LLM RL track — neither exists today (current "learned" tracks are supervised routing classifiers, not policy-gradient RL). Confidence: external/DGX-gated. [gpu-acceleration-path.md, intake-709]

## 2026-06-13 Update — What Is Actually Exhausted

The Fable 5 kernel review draws a sharper boundary than earlier shorthand. Batch=1 decode micro-optimization is genuinely exhausted under the current evidence: the CPU is compute-idle but per-thread bandwidth saturated, so kernels that stream the same bytes faster do not change the bottleneck. That closure does not exhaust the hardware program.

Five live angles remain:

- **One-pass draft+verify**: spend idle FLOPS to reduce weight passes, if a quality-viable TiDAR-class checkpoint exists.
- **Low-bpw formats**: watch STQ1/Sherry-style releases and upstream support; build only after weights and llama.cpp support exist.
- **Sparsity / DSA**: first CPU smoke datapoint for PR #21149 remains unrun.
- **Frontdoor spec-dec**: measure alpha before treating GPU/CPU drafter ideas as viable.
- **Batched decode and eval serving**: CPU14 and a T1 eval-driver A/B are the highest-value missing serving measurements.

The MI210 hypothesis also changes emphasis. Dense frontdoor residency remains plausible, but GPU-as-eval-engine may compound more quickly: faster promotion evals increase statistical power per day, which directly addresses the evidence-plane bottleneck.

Sources: [Fable 5 kernel and concurrency](../handoffs/completed/fable5-findings-06-kernel-and-concurrency.md), [Fable 5 serving and GPU](../handoffs/completed/fable5-findings-03-serving-and-gpu.md), [gpu-drafter-mi200-investigation.md](../handoffs/active/gpu-drafter-mi200-investigation.md).

## Actionable for EPYC

- **Deployed NUMA configuration**: Frontdoor (4x48t quarters, ~50.8 t/s), coder_escalation (4x48t quarters, ~43.3 t/s), architect_general (1x96t node0, 4.3 t/s), architect_coding (1x96t node0, 7.0 t/s), ingest (1x96t node0, ~12 t/s). Total model footprint ~515 GB.
- **Every inference command must use**: `OMP_NUM_THREADS=1`, `taskset -c <cpulist>` for NUMA pinning, `-t 48` or `-t 96` (physical cores only). Missing any of these can halve throughput.
- **Storage safety is non-negotiable**: All LLM files must reside on /mnt/raid0/. Path verification (`[[ "$TARGET_PATH" == /mnt/raid0/* ]]`) before every write. Never enable core dumps (120 GB root SSD). Never use pytest -n auto.
- **Model servers must load sequentially** with 5-second cooldown between large models. Concurrent mlock crashes the system. Vision servers need 90-120s timeout for mmproj + main model.
- **Architect 2-instance opportunity**: Qwen3.5-122B-A10B at 69 GB could run 2x96t for ~2x aggregate if architect throughput bottlenecks. Currently single-instance.
- **Qwen3.5 hybrids are 2-3.6x faster than pure MoE at 122B+ scale** due to recurrent layers avoiding KV cache bandwidth costs. Consider replacing remaining MoE architect roles with hybrids if quality permits.
- **Always sweep before deploying**: The bench_all_spec_sweeps.sh script produces comprehensive verification. Single-run extrapolations have been wrong by up to 3.6x.

## 2026-06-15 Update — Benchmark Boundaries Stayed Narrow

- **Canonical measurement now treats historical speed claims as observations unless the protocol is explicit.** The publication draft and public-results draft both separate protocol-tagged rows from claim-grade rows, so throughput claims can no longer float free of reps, date, and attestation. The public-results generator also emits a public-scrub surface so complete protocol metadata cannot accidentally promote rows that still expose local paths, loopback endpoints, internal role aliases, or operator/internal workflow terms. Sources: [canonical-cpu-benchmarking-methodology-draft.md](../docs/publication/canonical-cpu-benchmarking-methodology-draft.md), [public-results-draft.md](../docs/publication/public-results-draft.md).
- **Serving truth is generated, not hand-curated.** The live stack contract now flows through generated stack priors and exact holder accounting, which means hardware conclusions need to align with the actual launched topology instead of static model tables or stale role maps. Sources: [model-stack-update-pipeline-audit.md](../handoffs/active/model-stack-update-pipeline-audit.md), [model-stack-single-source-update-pipeline.md](../handoffs/active/model-stack-single-source-update-pipeline.md).
- **Batch=1 closure does not imply batch/eval closure.** Fable 5’s serving work keeps continuous batching and `-np` sweeps as separate measurements, so the remaining performance question is still the effect of concurrent prefill and eval fanout, not more extrapolation from the kernel-level decode result. Sources: [canonical-cpu-benchmarking-methodology-draft.md](../docs/publication/canonical-cpu-benchmarking-methodology-draft.md), [public-results-draft.md](../docs/publication/public-results-draft.md).

## Open Questions

- **Does a gfx90a vLLM beat llama.cpp-HIP's quantized ceiling?** The matched-precision fp16 head-to-head is settled (vLLM +11% per-stream / +24% batched, and the ~47% ceiling is proven a Q4_K MMQ-dequant artifact), but **quantized-vs-quantized** (vLLM AWQ/fp8 vs llama.cpp Q4/Q8) — where llama.cpp's gap actually lives — is unmeasured because it needs vLLM quant weights. A deployment-scale Gemma-3-27B comparison (~100–190 GB downloads, now feasible post-reclaim) is gated on the 8B result being surprising.
- **Is the gfx90a MMQ dequant path worth hand-tuning?** llama.cpp gfx90a quantized decode tops out at ~33% (Q4_K) / 47% (Q8_0) of the 1.64 TB/s roofline; the fp16 62% result localizes the headroom to the dequant kernels specifically. This is the concrete target for the agentic ROCm kernel-authoring track (AITER's CDNA3/4 numbers are the ceiling to beat, but AITER does not support gfx90a).
- **Can any validated qwen35-compatible drafter path produce frontdoor α on CPU?** The GPU HIP path proves qwen35 *forward decode* is clean, isolating the failure to the CPU speculative codepath — but the N5 gating measurement (production-traffic acceptance of a validated frontdoor drafter → Qwen3.6-35B at γ=3) still has no decision-grade evidence; it gates cascade / custom-drafter-training / adaptive-K.
- **Does DeepSeek-V4-Flash clear a *recalibrated* (V4-arch-aware) throughput floor, and does the ik_llama-API translation (Strategy A) close enough of the F16-component BW gap to matter?** The provisional 9.13 t/s fails the gemma4-derived 18 t/s floor; whether V4 has any production niche (architect_general has a different throughput tolerance) is operator-gated and quality-gate-blocked on Mac/ds4 reference logprobs.
- Does the DSA Lightning Indexer (FP8 head-weighted scoring over a block-64 quantized key cache) profile as compute-bound or BW-bound on Zen 5? This gates whether an AVX-512BW indexer kernel (`vpmaddubsw`+`vpmaddwd`, NOT VPDPBUSD per the Zen 5 finding) is worth writing — if BW-bound, the SIMD work is a no-op and effort should redirect to extending the sparse path into prompt processing. Profile step is D3.1 in the DSA handoff; gated on operator inference approval.
- Does the DSA sparse path preserve CPU MoE throughput, or does FP8 indexer emulation erase the CPU advantage at long context? The first CPU smoke datapoint for PR #21149 (V3.2-Exp Q4_K_M, ~380 GB) remains unrun; all published numbers are CUDA WMMA.
- Decision-grade single-instance batched decode (CPU14 E1/E2) is blocked on a host-health/reboot window: the scout's `-np 8` candidate and the eval-driver A/B keep/kill recommendation cannot be promoted to claims until uptime, `numa_balancing`, and concurrent-inference preconditions are satisfied per P-BENCH-3.
- NUMA node asymmetry (Node 1 at ~85% of Node 0) may be addressable with explicit memory binding or model-loading order changes, but numactl --membind is blocked in the container.
- Transparent Huge Pages (THP) are enabled (`echo always | sudo tee /sys/kernel/mm/transparent_hugepage/enabled`) but their impact has not been isolated in benchmarks.
- CPU paged attention (production-consolidated-v3, patch #7-10) is deployed but RSS impact under NUMA 4-way has not been validated.
- The OMP_NUM_THREADS=1 devcontainer bug (all DFlash server benchmarks invalid due to single-thread OpenMP) suggests environment variable validation should be added to benchmark scripts.
- GPU acceleration path researched (2026-04-14, updated 2026-04-15): NVIDIA DGX Spark ($4,699, 128GB unified memory, 273 GB/s, Blackwell GPU) is the primary path. Unified memory eliminates PCIe bottleneck -- expert weights are directly accessible by both CPU and GPU, making `-ot "exps=CPU"` offloading unnecessary. ~70 t/s decode on MoE models from a single chip. Two units linkable via NVLink for 256GB. **vLLM speculation opportunity**: community benchmark shows 91 tok/s on Qwen3.5-27B AWQ with DDTree+Dflash (block diffusion) on GB10 -- GPU parallel scan removes the Delta Net sequential verification bottleneck that killed all CPU speculation approaches. Reproduction plan in gpu-acceleration-path.md.
- Consumer AMD GPU: RX 7900 XTX ($750-900, 24GB, ROCm stable, ~130 t/s decode 7B Q4) is the best budget option for hybrid MoE offloading. ROCm HIP compatibility with `-ot` tensor overrides is **unconfirmed**.
- CPU+GPU hybrid MoE expert offloading (`-ot "exps=CPU"`, `--n-cpu-moe N`) is production-ready in llama.cpp. PCIe latency is the bottleneck, not CPU compute speed. Two-tier expert cache proposal (#20757) shows 12-14 t/s vs 0.5-1 t/s pure CPU offload -- most impactful pending feature for discrete GPU setups.
- For short-context single-token decode, NUMA 4-way CPU may remain competitive with GPU since decode is memory-bandwidth-bound. GPU most beneficial for prefill (always compute-bound) and long-context decode (attention becomes compute-bound at >50% of per-token time).

## Related Categories

- [Benchmark Methodology](benchmark-methodology.md) -- all benchmark results depend on hardware configuration
- [Speculative Decoding](speculative-decoding.md) -- speculation effectiveness varies dramatically by NUMA config and quantization
- [Inference Serving](inference-serving.md) -- production stack topology built around NUMA optimization
- [MoE Optimization](moe-optimization.md) -- MoE models are the primary beneficiaries of NUMA pinning
- [Local Inference](local-inference.md) -- llama-server launch parameters are hardware-optimized
- [Quantization](quantization.md) -- Q4_K MMQ dequant cost on gfx90a, NVFP4/STQ1_0/TQ3 CPU vs GPU quant paths
- [KV Cache Optimization](kv-cache.md) -- KV cache quant (Hadamard rotation auto in v6; TurboQuant TBQ3/TBQ4 watch)

## Source References

- [Chapter 01: Hardware System](/workspace/docs/infrastructure/01-hardware-system.md) -- EPYC 9655 specifications, runtime optimizations, baseline performance
- [Chapter 02: Storage Architecture & Safety](/workspace/docs/infrastructure/02-storage-safety.md) -- 192-thread pytest danger, HOT/WARM/COLD tiers, root FS crisis
- [Chapter 04: Production Server Stack](/mnt/raid0/llm/epyc-orchestrator/docs/chapters/04-production-server-stack.md) -- Server topology, memory architecture, worker pool, concurrent inference sweep
- [NUMA Orchestrator Deployment](/workspace/handoffs/completed/numa-orchestrator-deployment.md) -- 6-7x NUMA throughput, deployment config, coder quant decision matrix, comprehensive sweep
- [Tree Speculation + NUMA Drafting](/workspace/handoffs/completed/tree-speculation-numa-drafting.md) -- NUMA 4-way results, tree vs linear at 48t, 480B tree+NUMA
- [SSM Hybrid Acceleration](/workspace/handoffs/completed/ssm-hybrid-acceleration.md) -- MoE self-draft results, architecture analysis, Q4_K_M optimality
- [SpecExec Verification Profile](/mnt/raid0/llm/epyc-inference-research/docs/experiments/specexec-verification-profile.md) -- Verification latency curves, NUMA impact on verification, draft model costs
- [Progress 2026-03-18](/workspace/progress/2026-03/2026-03-18.md) -- NUMA parallel decode S2 benchmark, production model sweep, T5/T6 tree+NUMA
- [Progress 2026-03-21](/workspace/progress/2026-03/2026-03-21.md) -- Comprehensive spec param sweep (1,290 measurements), corrected registry values
- [GPU Acceleration Path](/workspace/handoffs/active/gpu-acceleration-path.md) -- DGX Spark analysis, consumer GPU benchmarks, hybrid MoE offloading survey, KV cache split strategies; 2026-04-23 adds Lucebox + Hazy megakernel research; 2026-06-20 records the deployed CPU image-gen role (sd_server / ERNIE-Image-Turbo via stable-diffusion.cpp) and the UniRL DGX-gated watch-item (intake-709)
- [llama.cpp DSA Contribution](/workspace/handoffs/active/llama-cpp-dsa-contribution.md) -- PR #21149 tracking, DSA forward-pass-unimplemented (dense-MLA fallback) finding, three contribution sub-tracks (smoke test / PP sparse path / AVX-512BW Lightning Indexer), multi-model-for-1 unlock (V3.2 + GLM-5.1 + GLM-5.2)
- [Batched-Decode Measurement (E1/E2/E3)](/workspace/handoffs/active/batched-decode-measurement.md) -- CPU14 single-instance `-np` sweep harness, eval-driver A/B coordinator, non-decision-grade scout (`-np 8` candidate, p95 tail cost, MoE-vs-dense batching pitfall), clean-window manifest wiring
- [CPU Shape-Specialized GEMV Decode](/workspace/handoffs/active/cpu-shape-specialized-gemv-decode.md) -- new 2026-04-23 handoff stub for Zen 5 AVX-512 M=1 GEMV microkernel investigation; 4-phase plan with falsification gates
- [Deep Dive: Lucebox Hub](/workspace/research/deep-dives/lucebox-hub-consumer-gpu-dflash.md) -- consumer-RTX-3090 DFlash GGUF port + DeltaNet-hybrid megakernel; resolves intake-158's "no llama.cpp / no GGUF" blocker on GPU side
- [Deep Dive: Hazy Research Megakernel](/workspace/research/deep-dives/hazy-megakernel-llm-inference.md) -- single-dispatch kernel methodology; 78% H100 memory bandwidth vs ~50% for vLLM/SGLang; foundational for any future GPU engine we build
- [Progress 2026-07-02 — MI210 first-touch GPU inference](../progress/2026-07/2026-07-02-mi210.md) -- MI210/gfx90a install, HIP build (fp8 guard fix `0ebf1b4d7`, LD_LIBRARY_PATH SIGSEGV gotcha), first GPU benchmarks (gemma4-31B 30 t/s, Qwen3.6-27B Q8 47% roofline), gemma4-31B+NEXTN MTP 43.25 t/s/1.44×, Vulkan-impossible-on-CDNA2, and the Qwen3-8B fp16 vLLM-vs-llama.cpp head-to-head result (62% vs 69% roofline, +24% batched)
- [Deep Dive 2026-07-02 — ROCm on MI210 (gfx90a): vLLM-from-source build path](../research/deep-dives/2026-07-02-rocm-mi210-vllm-gfx90a.md) -- the gfx90a support matrix (Triton/FA-2/vLLM-core cover gfx90a; AITER/MORI/DeepEP `gfx942;gfx950` only → reference-kernel build), prebuilt-vs-source route ordering, ROCm-6.2 fp8/ABI risks; [intake-759 AITER], [intake-760 ROCm/Triton], [intake-761 ROCm/FlashAttention], [intake-762 vLLM Dockerfile.rocm], [intake-763 vLLM v0.6.5 ROCm docs]
- [GPU-Drafter on MI200 Investigation](../handoffs/active/gpu-drafter-mi200-investigation.md) -- MI200 BW envelope + GT 1030 falsification, MTP-head-split design, cross-tokenizer spec-dec (Timor SLEM/TLI), the N5 frontdoor-α gating measurement (still no evidence), and the 2026-07-02 hardware-gate-OPEN advancement (HIP build verified, gemma4 MTP + qwen35 GPU decode)
- [v6+iqk → production cutover](../handoffs/active/v6-iqk-promotion.md) -- one-kernel cutover complete (ik_llama deprecated), N≥200 IQK-on/off eval-parity (1.3848× throttle-caveated), era fence, N12 private-copy negative for frontdoor/ingest/vision; post-reboot bench pending
- [Speculative-Decoding / MTP Refresh](../handoffs/active/speculative-decoding-mtp-refresh.md) -- per-model MTP verdict table; dense-CPU-MTP validated (gemma4-31B ~1.84×/2.5-3.2× code) vs MoE ~1.06× wall; gemma4-31B Pareto-dominated by the A4B worker; eval-saturation caveat behind the A4B-ties-dense finding
- [Qwen MTP llama.cpp Port](../handoffs/active/qwen-mtp-llamacpp-port.md) -- #22673 cherry-pick INFEASIBLE (llama_model_base framework gap, ~901 commits behind); fresh-upstream build runs Qwen3.5-9B dense MTP 1.97×/87%; FR-Spec vocab-trim (intake-740) +1-3% e2e
- [DeepSeek-V4-Flash CPU Port](../handoffs/active/deepseek-v4-flash-cpu-port.md) -- 284B/13B-active new arch (CSA+HCA+indexer+compressor+manifold-HC); Strategy-B throughput gate provisional FAIL 9.13 t/s vs 18 t/s floor; F16 components dominate BW budget; floor recalibration needed
- [Engram — Conditional Memory via Scalable Lookup](../handoffs/active/engram-conditional-memory.md) -- LongCat-Flash-Lite CPU probe closed negative (37 t/s but dominated by gemma4-MTP); n-gram-lookup MoE viable on CPU (~0.7 GB/s, <0.2% aggregate BW); intake-758 embedding-scaling law
- [MoE-Spec — CPU Spec-Dec with Budgeted Expert Selection](../handoffs/active/moe-spec-cpu-spec-dec-integration.md) -- proven mechanism (REAP-246B B=40 +15% pp / +3% e2e) but NO live consumer; reopen chained to frontdoor spec-dec + N5 α
- [TQ3 / TurboQuant Quantization Monitor](../handoffs/active/tq3-quantization-evaluation.md) -- KV-cache quant watch (Hadamard PR #21038 landed/auto in v6; TBQ3/TBQ4 #21089 open); [intake-756 NVIDIA Qwen3.6-27B-NVFP4] not_applicable (GPU-native, MI210 no FP4 path) but an FP8-parity external bar; Sherry STQ1_0 sub-2-bit watch
- [MI210 big-model residency + acceleration roadmap](../handoffs/active/mi210-big-model-and-acceleration-roadmap.md) -- the two-axis strategic thread (Axis A residency quant-ladder IQ2→offload/REAP→GLM-5.2 754B endgame; Axis B GPU drafter-farm with quant-asymmetric self-spec N5-free-by-construction); corrected architect baseline ~18–21 t/s (not 4.3); expert-routing-skew profile as the shared offload/REAP gating experiment
- [MI210 speed-campaign summary](../handoffs/completed/mi210-speed-campaign-summary.md) -- completed top-line campaign verdict: single-stream dense-Q8 +37% banked, aggregate solved by config (bf16-for-aggregate / Q8-for-single-stream, `-fa 1` win for MoE), all occupancy rewrites (L3-MoE, L20) structurally dead, frontier moved speed→capability
- [MI210 batch-1 latency-wall greenfield (prefetch→megakernel)](../handoffs/active/mi210-batch1-latency-wall-greenfield.md) -- the 62→100% batch-1 MLP floor; async-prefetch `raw.buffer.load.lds` +3.3% (MemUnitStalled −62%, CDNA2 ceiling); megakernel RULED OUT (HIP graphs already capture the only +5.9% launch headroom; AMD Fleet arXiv 2604.15379 is the CDNA3/4 precedent, no CDNA2 megakernel exists); rocBLAS GEMV is dense-only (dequant-to-fp16 = fatal bytes-moved for BW-bound decode)
- [MI210 Q8 dequant-GEMV roofline](../handoffs/active/mi210-q8-dequant-gemv-roofline.md) -- the batch-1 dequant gap decomposition (Q4_K 34%→Q8 50%→fp16 62.5% roofline); custom dequant-GEMV worth authoring only for a batch-1 *latency* role (GPU drafter), self-compensates when served batched
- [MI210 MFMA compute-bound paths](../handoffs/active/mi210-mfma-compute-bound-paths.md) -- GDN-MFMA killed by profile for decode (MemUnitBusy 65% vs VALUBusy 16%, MfmaUtil 0% — memory/occupancy-bound, not compute); MFMA targets headroom that isn't the bottleneck
- [MI210 kernel-R&D loop proposal](../handoffs/completed/mi210-kernel-rnd-loop-proposal.md) -- completed historical scaffold; the current system-wide owner is AutoKernel
- [Progress 2026-07-03 — MI210 Qwen3.6-27B speed campaign](../progress/2026-07/2026-07-03-mi210-qwen36-27b-speed-campaign.md) -- the running kernel/quant/regime campaign log (MMVQ→MMQ verify-dispatch, nwarps, async-prefetch, fused-prefetch/megakernel/L3-MoE-occupancy falsifications, bf16-for-aggregate crossover)
- [Progress 2026-07-04 — MI210 kernel-R&D loop + occupancy falsification](../progress/2026-07/2026-07-04-mi210-kernel-rnd-loop.md) -- Phase-0 harness built/validated, L3-MoE MMQ-occupancy BUILT+FALSIFIED (grid-limited at B=32 not LDS-limited), L20 GDN-occupancy NO-GO, capability pivot to L15 residency
- [Progress 2026-07-05 — MI210 capability + kernel-R&D loop + strategy](../progress/2026-07/2026-07-05-mi210-capability-kernel-rnd.md) -- kernel-R&D Phases 1–2, bf16 GDN recurrent-state BUILT+GO (+21.5/+17.7/+16.4/+13.3% table), 122B IQ2 residency VIABLE, strategic roadmap wired, corrected architect baseline
- [Progress 2026-07-05 — MI210 residency ladder (2-for-2) + CoT-scaffold reframe](../progress/2026-07/2026-07-05-mi210-residency-and-cot-reframe.md) -- 122B IQ2 eval-parity PASSED judge-free (Δ0.0pp, McNemar p=1.000), 80B-ingest IQ2 VIABLE (residency generalizes to qwen3next), 80B aggregate ceiling 405 t/s @B128 compute-bound, CoT-scaffold rescue-metric operator reframe
- [Kernel reconciliation audit (pre-v7)](../handoffs/completed/kernel-reconciliation-audit.md) -- READ-ONLY git audit: fork point `f8cc15f16`; GPU (`ggml-cuda`) and CPU/server (`ggml-cpu/iqk` + `tools/server/*` + `src/llama-kv-*`) subsystems are DISJOINT (only shared file `hip.h` is byte-identical → no-op conflict); experimental was missing the iqk CPU GEMM subsystem (7 commits/40,541 ins) + 3 server/CPU items, prod was missing the 4 gfx90a GPU opts; nothing valid stranded; `a8afd338` is a thread marker not a git ref
- [Tree-draft forward-port plan — Phase-1a result](../handoffs/active/tree-draft-forward-port-plan.md) -- v7-candidate build `46f876c12` (v6+iqk + 4 GPU opts + tree-draft, clean HIP compile/link); DySpec engine bit-identical to linear draft but net-negative vs plain and dominated by embedded MTP → SHELVED
- [Progress 2026-07-06 — v7-candidate + GPU speed levers](../progress/2026-07/2026-07-06-v7-candidate-and-gpu-levers.md) -- v7-candidate reconciliation (zero-conflict, stale-fork bug closed); experimental-kernel-workflow + production-kernel-immutability governance (`a37fc7f5`); verified aggregate spec sheet (frontdoor 408 @B32) with bf16-state ON/OFF regression-validation on the reconciled kernel (27B +20.1%, 35B-A3B +17.7%); MTP-F16 +60.2%; verified temp→α curves + reproducibility root-cause

## 2026-04-23 Additions

### CPU throughput levers — post-TIDE deprecation landscape

The TIDE calibration-router early-exit track was deprecated 2026-04-23 (projection quality could not be solved with linear or bottleneck-adapter approaches, after 1.76× speed was confirmed at 50% layers). Remaining CPU throughput levers:

- **Weight-reduction strategies (mature/in-production)**: NUMA 4-way, MoE expert pruning (REAP), AM KV compaction, KV quantization, ngram-simple spec. These are the workhorses.
- **Operator fusion (ruled out empirically)**: Hadamard + unfused `q4_0` beat TurboQuant + fused dequant by 2.2× on our hardware. Upstream llama.cpp has stopped investing in CPU fusion (recent fusion commits all target CUDA/SYCL/WebGPU). Fusion hides compute latency, not memory latency; our workloads are bandwidth-bound (or recurrence-bound for hybrid).
- **Shape-specialized GEMV microkernels (uncharted)**: the one remaining lever. Prior art: llamafile 2.8× on Zen 4, KleidiAI 2.0× decode on Graviton 3. Zen 5's 512-bit AVX-512 datapath (doubled from Zen 4) favors this path. Full investigation handoff at `cpu-shape-specialized-gemv-decode.md`; Phase 0 profiling gate before committing code. Projected 1.5–2.5× end-to-end decode speedup if lever proves out.

### 2026-04-26 critique-integration addendum

- CPU4 hierarchical barrier work is now recorded as a **falsified single implementation variant**, not a full sync-class closure.
- Cross-track sequencing is explicit: CPU20 (rigor) → CPU21+CPU24 (attribution) → CPU22 (mechanism) → CPU23 (regime coverage).
- >150B EP regressions remain open for hardware-attribution closure; aggregate-DDR saturation is not accepted as proven root cause without CPU24 counter evidence.

### Perf-gap decomposition: Qwen3.6-27B at 4.8 t/s on EPYC 9655

Important clarification to prior benchmarks: **the 25.6 t/s figure in `qwen36-production-upgrade.md` is for Qwen3.6-35B-A3B (MoE, 3B active), not Qwen3.6-27B (dense hybrid)**. The 27B dense baseline is **4.8 t/s** (`progress/2026-04/2026-04-22-kernel-push.md:63`). Dense vs A3B is a ~9× bandwidth-per-token difference because the dense variant touches all 27B params per token while A3B touches only 3B.

Roofline check: Qwen3.6-27B Q8 is 26.6 GB; effective DDR5 BW ~460 GB/s → **17 t/s ceiling** if bandwidth-bound. We're at 4.8 t/s → **28% of roofline**. Compute-bound on DeltaNet sequential recurrence (75% of layers), not bandwidth-limited. Getting to 50% of roofline via ukernel work → 8.5 t/s (1.77×); 80% → 13.6 t/s (2.83×). Anything past 80% requires parallel-scan SSM state, which is GPU-only.

### Megakernel / GPU roofline context

For any future GPU engine: Hazy Research megakernels hit 78% memory bandwidth utilization on H100 (vs ~50% for vLLM/SGLang) via an on-GPU instruction interpreter per SM, shared-memory pagination, counter-based dependency tracking. Lucebox ports this to RTX 3090 + Qwen3.5-0.8B (1.55× vs llama.cpp BF16) and separately ships a DFlash GGUF port for Qwen3.5-27B at 207 tok/s peak / 129.5 t/s mean on HumanEval via llama.cpp fork with tree-mode support. These establish the GPU roofline target (78% MB utilization) for any future engine we build or evaluate.

### Single-instance vs aggregate throughput gap — and the uncharted CPU TP lever

On our EPYC 9655, 4×48t NUMA-pinned instances give **6.7× aggregate throughput** on 30B-A3B (95.8 t/s) vs 1×192t interleaved (14.2 t/s). A single interactive session only sees per-instance speed — **single-session decode is at ~20–50% of what the hardware can physically deliver**. The other 50–80% shows up only as aggregate across independent processes. Cause on a single socket: thread scaling plateaus around 48–64 threads per instance (GGML barrier cost dominates past that); the 12 memory channels are shared as one contention target; per-CCD L3 locality is wasted. Current single-instance 192t measured: 14.2 t/s × 16 GB = ~227 GB/s effective, i.e. ~50% of the 460 GB/s socket ceiling — confirms barrier-bound, not BW-bound.

Two paths to close the gap (both new 2026-04-23 handoffs):

- **Intra-process tensor-parallel decode across CCDs + comm-hiding** (`intra-process-tensor-parallel-decode.md`): shard each matmul column-wise across 12 CCDs, each CCD's threads read their local weight slice from local memory channels, reduction via shared-L3 buffer (240 KB per reduce, effectively free), comm-hiding via next-layer prefetch in the barrier window, per-CCD hierarchical thread pools. Unlike GPU TP, the "communication" is the same shared memory system the compute uses — bandwidth savings come from weight locality (each CCD reading its slice from its local channels), not from avoiding a fabric. **No known CPU prior art with CCD-fabric awareness** — GPU-native design pattern ported to CPU. Projected 2–3.5× single-instance under NPS2, 3.5–5× under NPS4/L3-as-NUMA. Combined with GEMV ukernels (1.5–2.5×), total 5.5× conservative / 12.5× stretch, capped by 460 GB/s BW ceiling.

- **System-level tuning audit** (`single-instance-system-tuning.md`): NPS mode (currently NPS2 — 2 NUMA nodes / 6 channels each; candidates NPS4 or L3-as-NUMA exposing 4 or 12 nodes), THP (currently `madvise`; candidate `always`), explicit 1 GB hugepages (currently 0 allocated), IRQ affinity, per-CCD sync primitive (replaces GGML global barrier), SMT on/off for AVX-512-heavy decode, per-NUMA weight replication for small models under NPS4/L3aaN. Projected 15–40% alone; gating multiplier for TP-sharding's full gain.

### Physical state at 2026-04-23 (baseline for future optimization work)

| Knob | Current |
|------|---------|
| NUMA mode | NPS2 (2 nodes, 6 channels each, distances 10/12) |
| THP | `madvise` |
| Explicit hugepages | 0 allocated |
| Governor | `performance` ✅ |
| SMT | enabled (192 logical threads from 96 cores) |
| NUMA balancing | default (kernel-controlled; AMD recommends explicit off) |
| IRQ affinity | default (not pinned) |
| Free memory | ~318 GB (out of 1.13 TB) |

These become the baseline for CPU3 Phase 0 measurements under the new `cpu-inference-optimization-index.md` backlog.

- [Intra-Process Tensor-Parallel Decode](/workspace/handoffs/active/intra-process-tensor-parallel-decode.md) -- new 2026-04-23, CCD sharding + comm-hiding, projected 2–5× single-instance
- [Single-Instance System Tuning](/workspace/handoffs/completed/single-instance-system-tuning.md) -- new 2026-04-23, NPS/THP/hugepages/barrier/IRQ audit, projected 15–40% alone
- [CPU Inference Optimization Index](/workspace/handoffs/active/cpu-inference-optimization-index.md) -- new 2026-04-23, backlog umbrella for all unimplemented CPU throughput techniques (CPU1–CPU14)
- [HSD + Hierarchical Self-Speculation](/workspace/handoffs/completed/hsd-hierarchical-self-speculation.md) -- SSM checkpoint overhead analysis, self-speculation failure modes

## 2026-04-23 late-session measurement update (supersedes projections above)

Phase 0 of the CPU optimization coordinated pickup executed 2026-04-23 with `perf record --call-graph dwarf` (installed via user sudo), on `llama.cpp-experimental` at `cpu-optimization/backlog-2026-04-23` (HEAD `9e048fbc1`). Findings materially revise the earlier-in-this-document projections:

### CPU2 GEMV ukernels — FALSIFIED by measurement

Phase 1 Target #1 implemented: ported `ggml_vec_dot_q8_0_q8_0` from AVX2 (256-bit) to AVX-512VNNI (512-bit) using the existing `mul_sum_i8_pairs_acc_int32x16` helper in `avx512-helpers.h`. Disassembly verified — new binary emits `vpdpbusd %zmm1,%zmm0,%zmm2` + `vpabsb %zmm,%zmm` + `vpmovb2m`; baseline emits `{vex} vpdpbusd %ymm`. Measured on Qwen3.6-27B Q8_0 decode:

- 96t pinned: AVX2 = 4.241 t/s, AVX-512VNNI = 4.313 t/s → **+1.7%** (within noise)
- 1t pinned: AVX2 = 1.020 t/s, AVX-512VNNI = 0.983 t/s → **−3.6%** (port overhead regressed)

Projection was 1.46× end-to-end; measured 1.017× at 96t. **Falsified by factor 30×.** Root cause: the 63.43% perf-sample count in `ggml_vec_dot_q8_0_q8_0` was cycles waiting for DRAM loads inside the inner loop, not ALU-bound compute. Doubling ALU width can't help when the CPU is stalled on memory. Change reverted; `quants.c` is clean. Same pattern observed for tinyBLAS (`GGML_USE_LLAMAFILE` on/off = 0% delta on both Q4_K_M and Q8_0 decode) and BLIS 5.2 (AOCL LD_PRELOAD on/off = 0% delta).

Implication: **compute-focused CPU ukernel work for quantized decode is not the right lever on EPYC 9655.** The earlier projection of 1.5–2.5× end-to-end was based on mis-reading perf samples. Memory-side levers (CPU1 TP-sharding, CPU4 sync primitive, KV compression) are the real opportunities. CPU2 may still help for prefill (M > 1) or batched decode where compute/BW ratio shifts.

### CPU1 TP-sharding Phase 0 — GATE PASSED

Phase 0 feasibility gate criteria from `intra-process-tensor-parallel-decode.md`:

- Gate (a): 192t single-instance <60% of 460 GB/s roofline → measured 18.7 t/s × ~2 GB/token = **8% of roofline**, PASS by huge margin.
- Gate (b): barrier cost >15% of per-token time → measured **32–45%** of cycles in libomp spin/barrier at 96t (`0x0000000000026580` family unresolved in perf), PASS.

Phase 1 prototype is gated GO. 96t / 192t throughput ratio = **2.63×** (49.11 / 18.7) is the concrete closing target for CCD-local weight sharding.

> **Naming correction 2026-07-30**: the 49.11 t/s arm was `taskset -c 0-95`, i.e. **all 96 physical cores of the whole machine** — not "one NUMA node". Under the NPS2 BIOS live on 2026-04-23 a node was `0-47,96-143`; under today's NPS4 a node is a quarter (`0-23,96-119` etc.). The "96t single-node" label used throughout this and neighbouring 2026-04 sections is a misnomer for the full-machine physical-core placement. The measurement is unaffected; the ratio is 96 physical cores vs 192 SMT threads, both whole-machine.

### CPU4 per-CCD sync primitive — PROMOTED to HIGH standalone

32–45% of decode cycles in OpenMP barrier/spin is a concrete measurement (not speculation). Originally MED / bundled into CPU3 Phase 3; now a standalone HIGH lever. ROI: halving barrier cost → +16% end-to-end on Q8_0, +22% on Q4_K_M.

### CPU3 zero-reboot knobs — within noise on canonical workload

User-applied 2026-04-23 via sudo:
- `kernel.perf_event_paranoid=1` (enables userspace perf profiling in container)
- `kernel.numa_balancing=0` (disable)
- `/sys/kernel/mm/transparent_hugepage/enabled=always`
- `/sys/kernel/mm/transparent_hugepage/defrag=always`
- 1× 1GB hugepage allocated on node 1 (kernel did not honor 40-page request — needs boot param for bulk 1GB allocation)

Re-benched 96t Qwen3-Coder-30B-A3B Q4_K_M across 3 runs after knobs: 46.4 / 46.4 / 48.2 t/s. Pre-knob baseline was 49.1 t/s. Net delta within measurement variance (cold-cache effects dominate). Knobs kept but not materially impactful on this workload. Further CPU3 work (NPS BIOS window, IRQ affinity, per-NUMA weight replication) still pending.

### New single-instance operating point — 96t-ALL-PHYSICAL-CORES (corrected 2026-04-24)

**Correction to 2026-04-23 labeling**: `taskset -c 0-95` is **all 96 physical cores across BOTH nodes (no SMT)**, NOT "full node 0". NUMA map:
- node 0 cpus: `0-47, 96-143` (physical + hyperthreads)
- node 1 cpus: `48-95, 144-191`

The real driver is avoiding hyperthreads — verified 2026-04-24: 96t all-physical (0-95) = 49.3 t/s vs 96t node 0 with HT (0-47,96-143) = 44.6 t/s → **−9.5% penalty from enabling HT**.

**Correction to +26% universal claim**: the 2026-04-23 "+26%" conflated (a) different models, (b) different session page-cache states. Apples-to-apples same-session measurement on Qwen3-Coder-30B-A3B Q4_K_M: 24t (cores 0-23) = 44.32 t/s, 96t all-physical = 49.34 t/s → **+11%**, not +26%. See `research/deep-dives/cpu-96t-production-sweep-2026-04-24.md` for the corrected multi-model matrix.

### Original thread sweep (numbers unchanged, labels corrected)

Systematic thread sweep on Qwen3-Coder-30B-A3B Q4_K_M (canonical baseline model, `-n 64 -r 3`, quiet host):

| Threads | CPU set | t/s (avg) | stddev | Note |
|---|---|---|---|---|
| 24 | taskset 0–23 (node 0 Q0A physical) | 40.76 (2026-04-23) / 44.32 (2026-04-24) | 0.11 / 0.03 | Production worker_general registry value = 39.1; measured higher today |
| 48 | taskset 0–47 (node 0 physical) | 39.59 / 45.80 | 0.21 / 0.10 | Barrier cost offsets BW gain over 24t |
| **96** | **taskset 0–95 (ALL PHYSICAL, BOTH NODES)** | **49.11 / 49.34** | **0.08 / 0.09** | **Peak** — uses all 12 DDR5 channels, no SMT |
| 96 (HT) | taskset 0-47,96-143 (node 0 phys+HT) | 44.63 (2026-04-24) | 0.04 | **-9.5% vs 96 all-physical** — HT hurts |
| 144 | taskset 0–143 (crosses NUMA unevenly) | 25.74 | 18.50 (bimodal 12.66/38.83) | Cross-NUMA disaster |
| 192 | full machine, `--numa distribute --mlock` | 18.69 | 7.23 (bimodal) | Production registry value = 14.2 |

**Corrected finding (2026-04-24 multi-model sweep)**: 96t-all-physical vs 48t-half-node is **model-dependent**:

| Model | Class | 48t | 96t all-phys | Δ |
|---|---|---|---|---|
| Qwen3-Coder-30B-A3B Q4_K_M | MoE Q4 (3B active) | 45.80 | 49.34 | **+7.7%** |
| Qwen3.6-27B Q4_K_M | Dense hybrid Q4 | 6.67 | **8.97** | **+34.5%** |
| Qwen2.5-Coder-32B Q4_K_M | Dense Q4 | 6.92 | **10.80** | **+56.1%** |
| Qwen3.6-27B Q8_0 | Dense hybrid Q8 | 4.26 | 4.19 | −1.6% |
| Qwen3.6-35B-A3B Q8_0 | MoE Q8 (frontdoor class) | 27.28 | 24.93 | **−8.6%** |

**Dense-Q4 models win big** (1.3-1.6×); MoE Q4 gets small gain; Q8 models flat-or-worse (closer to BW roofline at 48t).

**Concurrent-load sweep** (2026-04-24, SMT-paired splits, `-p 0 -n 32 -r 2`, **N INDEPENDENT llama-bench processes in parallel** — not single-instance TP-sharding): aggregate throughput **monotonically increases** as we split the socket into more concurrent instances.

| Model | 4×48t | 8×24t | 16×12t | 32×6t | **48×4t** | Peak | Δ 4→peak |
|---|---|---|---|---|---|---|---|
| Qwen3.6-27B Q8 (dense hybrid) | 6.62 | 7.91 | 8.55 | 10.47 | **15.39** | 48×4t | **+133%** |
| Qwen3.6-35B-A3B Q8 (frontdoor class) | 64.26 | 76.35 | 85.89 | 92.75 | **135.08** | 48×4t | **+110%** |
| Qwen2.5-Coder-32B Q4 (dense) | 13.64 | 15.08 | 16.01 | **20.03** | 17.34 ↓ | 32×6t | **+47%** |

**Biggest production finding of the session**: switching the orchestrator from **4×48t quarters** (current production) to per-model-optimal splits delivers **+47% to +133%** aggregate throughput with NO code changes. **35B-A3B Q8 at 48×4t hits 135 t/s, ≈100% of the 460 GB/s BW socket roofline** (up from 49% at 4×48t). Per-session throughput at 48-way split is tiny (2.8 t/s per session on 35B-A3B Q8) — this is strictly for concurrent/bulk workloads; single-session latency paths stay on 1×48t/1×96t. Coder-32B Q4 peaks at 32×6t and regresses at 48×4t (per-instance compute too small to saturate BW share).

Hypothesized mechanisms (Phase-0 perf data supports #1 and #2):
1. **Barrier cost is O(threads per instance)**: perf showed 32-45% of cycles in libomp barriers at 96t. Smaller instance barriers (6t vs 48t) are dramatically cheaper. 32 small barriers in parallel beat 4 large ones.
2. **CCD locality**: 6 physical cores ≈ <1 CCD on EPYC 9655 (8 cores/CCD). Smaller instances keep their working set within a single CCD → minimal cross-CCD L3/IOD coherence traffic.
3. **Page cache coherence**: all instances mmap the same GGUF, so weight reads share the page cache. No extra memory pressure from more instances.
4. **BW channel interleaving**: finer-grained instance → finer-grained memory channel contention resolution.

**Single-session crossover**: 1×48t isolated on 35B-A3B Q8 = 27.3 t/s. Split 32×6t aggregate 92.75 / 32 = 2.9 t/s per session. Single-session wins up to ~3 concurrent users; split wins at ≥4 concurrent.

Full corrected analysis: `research/deep-dives/cpu-96t-production-sweep-2026-04-24.md`.

### Memory note on decode-path perf interpretation

Going forward: when `perf report` shows a large overhead percentage inside a quantized-decode inner dot/matmul function on this hardware, treat those samples as **DRAM-wait cycles, not ALU-bound work**, unless separately verified. A cheap A/B test (wider-SIMD port) resolves the question in hours. See `feedback_cpu_decode_bw_bound.md` in auto-memory.

### Session artifacts landed

- `research/deep-dives/cpu-optimization-phase0-baseline.md` — full Phase 0 baseline + thread sweep + per-function perf profile + GGUF metadata for Qwen3.6-27B + revised CPU1/CPU2/CPU4 gate decisions.
- `research/deep-dives/cpu-optimization-cheap-checks-2026-04.md` — tinyBLAS/BLIS/compiler A/B all within noise.
- `progress/2026-04/2026-04-23-cpu-optimization-kickoff.md` — session narrative + step closures.
- `handoffs/active/cpu-inference-optimization-index.md` — pickup-sequence + revised priorities.
- `handoffs/active/cpu-shape-specialized-gemv-decode.md` — deprioritized status + negative-result writeup.
- `handoffs/active/intra-process-tensor-parallel-decode.md` — Phase 0 gate-passed annotation + data.

---

## 2026-04-24 late: Phase 1.4 shipped, fusion track closed, Zen 5 VNNI surprise

Outcome of the CPU optimization sprint's software-level phase on NPS4:

### Current operating point (reproducible)

```
GGML_CCD_POOLS=1 GGML_NUMA_WEIGHTS=1 GGML_CCD_WORK_DIST=1 GGML_BARRIER_LOCAL_BETWEEN_OPS=1 \
  taskset -c 0-47 llama-server -t 48 --flash-attn on --mlock
```

- Single-instance peak (llama-bench, `-n 64 -fa 1 -r 5`): **48.81 ± 0.08 t/s** on Qwen3-Coder-30B-A3B Q4_K_M.
- Layered with production stack (server + spec decode dm=8 + ngram-simple lookup) on code prompts: **58 t/s** (+27% on top of Phase 1.4).
- 4×48t concurrent aggregate: 77.5 t/s (new baseline after CCD-cpuset hang fix).

### Phase 1.4 (shipped)

`acb1bbdd7` — axis-0-aligned partitioning in element-wise ops (ADD, MUL, SCALE, UNARY) + safe CCD-local between-op barrier downgrade. Together with Phase 1.0/1.1/1.2/1.3 (CCD pools, pinning, work-dist, NUMA_WEIGHTS mempolicy interleave), this represents the full exploitation of CCD-locality in a single-instance decode path. Gains: 40 t/s session-start → 48.81 t/s (+22%). Phase 1.4 profile: barrier 43% → 28%, GEMV steady at ~33.5%, other 28% → 38%.

### Op-fusion infrastructure — reverted (no signal)

`b2154f3f3` (infra) + `9ea5b40e8` (Phase 2 graph-construction) briefly shipped with PPL-bit-exact correctness and a repack-path fusion kernel to handle the Q4_K_M repacked-weight path. Throughput gain on MUL_MAT+ADD fusion: **within ±0.4% noise in both fa=0 and fa=1 modes**. Why it didn't matter: the fused ADD is a tiny 2048-float tensor; the barrier it saves is ~0.5% of per-layer cost; and attention-internal fusion (the other potential target) is already fully handled by `ggml_flash_attn_ext` (single graph op covers Q@K + softmax + V@KQ). With no remaining leverage target, keeping fusion infra meant pure technical debt. Reverted as `c34aac61b` + `138b26cd4`.

**Takeaway**: on models where flash attention is enabled (which is all our production MoE workloads), there is no CPU-general op-fusion lever left to pull. Future fusion work only makes sense if (a) attention is NOT using flash attn for some reason, or (b) we discover a specific multi-op sequence with disproportionately large barrier cost that the Phase 1.4 local-barrier downgrade can't already catch.

### Q4_K GEMV VNNI probe — net-negative on Zen 5 (NOT committed)

Profile showed 33.5% of decode cycles in `ggml_gemv_q4_K_8x8_q8_K` (AVX2 kernel using `_mm256_maddubs_epi16` + `_mm256_madd_epi16`). Straightforward AVX-512VNNI port: replace the 8× `maddubs_epi16` + 7× `add_epi16` + 1× `madd_epi16` chain with 8× `_mm256_dpbusd_epi32` + 1× `_mm256_mullo_epi32`. PPL bit-exact with baseline (10.9882), so correctness holds. Throughput: **tg64 48.81 → 48.18 t/s** (slight regression outside of baseline's tight stddev).

**Root cause — Zen 5 instruction throughput asymmetry**:
- `VPMADDUBSW` 256-bit: **2 ops/cycle**
- `VPDPBUSD` 256-bit or 512-bit: **1 op/cycle**
- `VPMULLD` 256-bit: 1 op/cycle, 3-cycle latency

Total cycle count:
- AVX2 path: 16 ops / 2 per cycle = **8 cycles/sub-block**
- VNNI path: 9 ops / 1 per cycle = **9 cycles/sub-block**

The existing AVX2 kernel is actually **better-matched to Zen 5's pipeline** than a VNNI replacement, even though it's nominally more instructions. This contradicts the common assumption that VPDPBUSD always beats maddubs+add+madd — on Zen 5 specifically, maddubs has 2× the throughput of VNNI for this kernel shape. The same negative conclusion now holds for both Q4_K_M (compute-bound candidate, this probe) and Q8_0 (BW-bound, 2026-04-23 probe). Not committed; stash dropped.

**Actionable**: do not port other quantized GEMV kernels (Q5_K, Q6_K, Q2_K, etc.) to VNNI on Zen 5 without a measured A/B. The speed assumption flips on different CPUs (Zen 4, Intel Sapphire Rapids have VNNI-favorable throughput ratios). Revisit if/when we acquire Zen 6 or a different server class.

### llama-bench `-fa` default gotcha

`llama-bench` defaults to `-fa 0` (flash attention OFF) while `llama-perplexity` uses `-fa auto` (which enables it). This is a ~8–10% swing on CPU decode throughput and caused a false "regression" scare this sprint. **Always pass `-fa 1` explicitly when benchmarking decode**. Production `llama-server` uses `--flash-attn on` in the standard stack — that corresponds to `-fa 1` in llama-bench.

### Production-stack composability verified

Before committing to the L3-as-NUMA reboot, layered the production-stack accelerations on top of the Phase 1.4 experimental kernel via `llama-server` + curl (prompt: Python linked-list scaffold, 170 prompt tokens / 256 generated):

| Model | Config | tg (t/s) |
|---|---|---|
| Qwen3-Coder-30B-A3B Q4_K_M | base | 45.63 |
| Qwen3-Coder-30B-A3B Q4_K_M | + spec (dm=8) | **55.47** (+22%) |
| Qwen3-Coder-30B-A3B Q4_K_M | + spec + ngram-simple | **58.01** (+27%) |
| Qwen3.5-35B-A3B Q4_K_M (hybrid) | base | 31.25 |
| Qwen3.5-35B-A3B Q4_K_M (hybrid) | + moe6 + q4_0 KV | 32.61 |
| Qwen3.5-27B Q4_K_M (dense hybrid) | base | 7.56 |
| Qwen3.6-27B Q4_K_M (dense hybrid) | base | 7.14 |

All production accelerations compose cleanly with the experimental kernel — no regressions.

### Decision gate: L3-as-NUMA BIOS reboot is next

Every software-level lever on NPS4 has been exercised or ruled out. The 48.81 t/s single-instance peak (Qwen3-Coder-30B-A3B Q4_K_M) represents the ceiling of non-BIOS optimizations. L3aaN would expose **12 NUMA domains (one per CCD)** rather than NPS4's 4, enabling genuine per-CCD weight locality via per-CCD replicas. Expected gain from L3aaN: +10–20% on decode, contingent on whether the 12-domain layout delivers CCD-local reads where the 4-domain NPS4 currently forces cross-channel traffic for most accesses.

### Q4 vs Q8 throughput on the experimental kernel (2026-04-24)

Same stack, code-completion prompt, via llama-server + curl:

| Model | Quant | Config | tg (t/s) |
|---|---|---|---|
| Qwen3-Coder-30B-A3B | Q4_K_M | base | 45.63 |
| Qwen3-Coder-30B-A3B | Q4_K_M | + spec (dm=8) + ngram | 58.01 |
| Qwen3.5-35B-A3B | Q4_K_M | base | 31.25 |
| Qwen3.5-35B-A3B | Q4_K_M | + moe6 + q4_0 KV | 32.61 |
| Qwen3.5-35B-A3B (abliterated proxy) | Q8_0 | base | 22.20 |
| Qwen3.5-35B-A3B (abliterated proxy) | Q8_0 | + moe6 + q4_0 KV | 24.83 |
| Qwen3.6-35B-A3B | Q8_0 | base | 22.29 |
| Qwen3.6-27B (dense hybrid) | Q4_K_M | base | 7.14 |
| Qwen3.6-27B (dense hybrid) | Q8_0 | base | 4.36 |

Q4→Q8 ratios: **0.71 on 35B-A3B hybrid** (SSM compute partially amortizes the BW doubling), **0.61 on 27B dense hybrid** (closer to the pure BW ratio since dense weights dominate). MoE expert reduction (moe6 + q4_0 KV) scales with Q4 and Q8: +4% on Q4, +12% on Q8 — the expert-reduction gain grows when BW cost per expert is larger. No Q8-specific kernel bugs observed.

### x86 K-quant + Q8_0 repack dispatcher gaps (2026-04-24)

`ggml/src/ggml-cpu/repack.cpp:ggml_repack_get_optimal_repack_type` has NEON-only dispatch branches for `GGML_TYPE_Q5_K`, `GGML_TYPE_Q6_K`, and `GGML_TYPE_Q8_0`. On x86 these types fall through to `nullptr` → tensors remain in the non-repacked layout and run the single-row `ggml_vec_dot_*` kernels from `arch/x86/quants.c`.

Profile consequences on Qwen3.6-27B (dense hybrid) decode:
- Q4_K_M quant: 49.3% cycles in `ggml_gemv_q4_K_8x8_q8_K` (repacked AVX2, fast), **18.2% in `ggml_vec_dot_q6_K_q8_K` (non-repacked)**, 4.6% in `ggml_vec_dot_q5_K_q8_K` (non-repacked). Unsloth's imatrix Q4_K_M aggressively uses Q6_K for `attn_qkv.weight` and `ffn_down.weight` — the biggest non-expert tensors per layer.
- Q8_0 quant: **77.4% cycles in `ggml_vec_dot_q8_0_q8_0` (non-repacked single-row)**. All Q8 workloads are throttled by this single-row kernel.

Gradient test on 2026-04-24 — flipping the dispatcher to use the existing `*_generic` C implementations for Q5_K/Q6_K produced **−66% to −71% regression** (generic kernels are scalar C with triple-nested loops; they don't auto-vectorize well enough to match the hand-tuned AVX2 `vec_dot_*`). For Q8_0 the generic 4x8 kernel is **neutral** (no sub-block scales → simpler, auto-vectorizes to AVX2-equivalent).

Conclusion: the plumbing is sound but the kernel side is missing. Writing hand-optimized AVX-512BW 8x8 repacked GEMV kernels for Q8_0 (biggest win: 77% cycle share, simplest kernel) and Q6_K (18% on Q4_K_M dense, more complex due to 4+2 bit unpack) is the next real software-level lever after L3aaN. Use AVX-512BW width (`_mm512_maddubs_epi16` + `_mm512_madd_epi16`) — NOT VPDPBUSD — because Zen 5's maddubs has 2/cycle throughput vs VNNI's 1/cycle. Expected gain: +40-70% on Q8 decode, +7-10% on Q4_K_M dense.

Effort: 4-6 hours per kernel. Deferred pending L3aaN reboot (higher ROI, zero code risk).

## 2026-04-24 Session 15 update — Q8_0 8x8 AVX-512BW kernel landed; ceiling is NOT BW-bound

The 2026-04-24 morning entry above predicted "+40-70% on Q8 decode" from a hand-written AVX-512BW 8x8 Q8_0 kernel. Session 15 in the afternoon implemented that kernel and found the prediction was **partly right and partly wrong**, with two important corrections:

### Kernel implementation — landed and correct

Branch `cpu-optimization/q8-8x8-avx512bw` off `cpu-optimization/backlog-2026-04-23` (HEAD `138b26cd4`), 3 commits totaling +445 / -17 LOC:

- `1d18efce3` — AVX-512BW 8x8 Q8_0 GEMV kernel + scaffolding. Hot loop: `vpabsb` + `vpmovb2m` + masked `vpsubb` + `vpmaddubsw` + `vpmaddwd` + `vpaddd`. Disassembly verified the kernel emits these (NOT `vpdpbusd`); the existing `mul_sum_i8_pairs_acc_int32x16` helper auto-selects VNNI under `__AVX512VNNI__` so the kernel inlines the BW path manually. PPL on Wikitext-2 (3 chunks, ctx=512) = 6.6985 ± 0.708, sensible for Qwen3.6-27B-Q8_0.
- `e84a5c82f` — auto-`mbind(MPOL_INTERLEAVE)` on the CPU_REPACK buffer when `ggml_is_numa()` is true, plus K-parallel activation quantization for ne11 < 4 in tensor_traits `forward_mul_mat`. Without the mbind, first-touch placed all 26 GB of repacked weights on NUMA node 0 and 96 threads × 4 NPS4 nodes saturated that single node's memory controllers — observed initial regression 2.8× at 96t. Mbind fix is general-purpose; affects every repacked quant on multi-NUMA hosts.
- `ba1c23900` — env-gated `gated_delta_net` S_v sub-chunking refactor (default OFF). Hypothesis was that `nr = H * n_seqs = 16` chunking caps DeltaNet to 16 effective threads on Qwen3.6-27B at decode. Refactor expanded `nr = H * n_seqs * k_per_head` and partitioned each head's S_v=256 axis into k_per_head sub-chunks. Net-neutral throughput at 96t for k_per_head ∈ {1, 6, 16} → DeltaNet is **not** the dominant bottleneck. Refactor kept env-gated for future probing.

### Throughput numbers — reality check

| Threads | Baseline (non-repacked) | Repack 8x8 + AVX-512BW | Δ |
|---------|-------------------------|-------------------------|---|
| 1 | 0.85 t/s | **1.12 t/s** | **+31.8%** |
| 12 | 4.41 | 4.54 | +2.9% |
| 24 | 4.50 | 4.54 | +0.9% |
| 48 | 4.51 | 4.56 | +1.1% |
| 96 | 4.32 | 4.39 | +1.6% |

The +31.8% at 1 thread is real (the 8-row amortization win when DRAM isn't saturated). The +1-3% at 12-96t is the kernel's edge over the single-row baseline at the throughput ceiling.

### Correction to "BW-bound" framing

Initial Session 15 writeup called 4.4 t/s "BW-saturated at the memory ceiling." This was wrong. The math:

- Qwen3.6-27B Q8_0 at 96t = 4.4 t/s × 26.6 GB/token = **118 GB/s = 26% of theoretical 460 GB/s ceiling**.
- Qwen2.5-Coder-32B (pure dense) Q4_K_M = 10.8 t/s × 18.5 GB = **200 GB/s = 41% of ceiling** on same hardware.

The 1.7× BW-utilization gap means Qwen3.6-27B has substantial untapped headroom — it's **not** memory-bandwidth-bound. The ceiling at 4.4 t/s comes from somewhere else.

The DeltaNet refactor probe disproved one obvious candidate (`gated_delta_net` parallelism). Remaining hypotheses (unprobed, ranked by likelihood):

1. **Barrier overhead × hybrid op count.** 64 layers × ~10 ggml ops per DeltaNet layer = ~592 ops per token, each followed by `ggml_barrier`. At 96t × NPS4, barriers eat ~28% of decode cycles per CPU1 Phase 1.3 measurements on simpler graphs; the hybrid graph likely has 2-3× more barriers than comparable Qwen2.5 dense.
2. **Op kernels around the fused DeltaNet** (RMS norm, conv1d short-conv, gate projection, residual) — not yet probed individually.
3. **Activation quant per-matmul at ne11=1** — even with the standard path's K-parallel `from_float`, may still be suboptimal.

### Action

The next session should be a **`GGML_PERF=1` profile of Qwen3.6-27B Q8_0 decode at 96t**, paired with the same profile on a pure-dense reference (e.g. Qwen2.5-Coder-32B Q4KM if a current GGUF is built) to localize the 26%→41% BW utilization gap to specific ops. Profile-then-fix beats fix-then-measure.

The Q6_K and Q5_K 8x8 AVX-512BW kernels from the morning's recommendation remain valid follow-ups (Session 14 dispatcher gap is unchanged), expected +2-5% each on Q4_K_M dense. The auto-mbind fix is a general multi-NUMA bug worth upstreaming to `ggml-org/llama.cpp` independent of the CPU2 lineage.

### General lesson — backend-buffer NUMA placement

`ggml_aligned_malloc` returns unfaulted anonymous pages that get pinned to whichever NUMA node first-touches them. For the CPU_REPACK buffer, that meant all 26 GB on node 0 → 96-thread reads through one node's memory controllers → 2.8× regression. The fix (`mbind(buffer, size, MPOL_INTERLEAVE, all_nodes)` inside the buffer-type allocator, gated on `ggml_is_numa()`) is general and worth applying to every backend buffer type that holds large multi-thread-read working sets. Reference impl: commit `e84a5c82f` on `cpu-optimization/q8-8x8-avx512bw`.

## 2026-04-24 Session 15 part 4-5 — perf profile + graph-rewrite probe

After the kernel + NUMA fix (parts 1-3 above) the throughput ceiling on Qwen3.6-27B Q8_0 sat at 4.4 t/s and the user pushed back on the "BW-saturated" framing. Sessions 15 parts 4 and 5 ran a `perf record --call-graph dwarf` profile and tried two graph-level rewrites; both disproved the simple-fix hypothesis and clarified the actual ceiling.

### Profile (part 4)

`perf record -F 999 -g --call-graph dwarf,8192` on noomp + full CPU1 stack (`GGML_CCD_POOLS=1 GGML_NUMA_WEIGHTS=1 GGML_CCD_WORK_DIST=1 GGML_BARRIER_LOCAL_BETWEEN_OPS=1`):

- **72.15%** in `ggml_vec_dot_q8_0_q8_0` (single-row Q8 dot — DRAM-stall-dominated)
- **21.63%** in `ggml_barrier` (already 2-level CCD-hierarchical, CPU1 Phase 1.0+1.1)
- **2.94%** in `ggml_barrier_local` (CPU1 Phase 1.4, selectively used)
- **<4%** everything else; DeltaNet ops are <1% combined

`perf stat` confirmed: **0.17 IPC** (3.4% of Zen 5 peak), `frontend_stalls=0.81%`. ~96% of cycles are backend-stalled on memory. Doubling ALU width is decisively useless on this kernel — third independent confirmation (Sessions 13, 14, 15 part 4) that quantized-decode kernels are DRAM-bound, not ALU-bound.

### Cross-architecture / cross-quant BW utilization

Same hardware (EPYC 9655 NPS4, 96 threads):

| Model | Architecture | Quant | t/s @ 96t | BW achieved | % of 460 GB/s |
|-------|--------------|-------|-----------|-------------|---------------|
| Qwen3.6-27B | 75% DeltaNet hybrid | Q8_0 | 4.42 | 117 GB/s | 25% |
| Qwen3.6-27B | 75% DeltaNet hybrid | Q4_K_M | 6.75 | 106 GB/s | 23% |
| Qwen2.5-Coder-32B | pure dense | Q4_K_M | 10.8 (registry) | 200 GB/s | 44% |

Both quants of the **same hybrid model** land at the same ~24% BW utilization. The Q4↔Q8 throughput difference is purely the bytes-per-token ratio. Pure-dense models on the same hardware hit ~44% — **the 1.7× gap is hybrid-architecture overhead, not quant-bound or kernel-bound.** Theoretical ceiling for Qwen3.6-27B Q8_0 if it matched dense BW utilization: 460 × 0.44 / 26.6 = **7.6 t/s** (+72% over current).

### Graph-rewrite angles tried (part 5)

**Angle A: extend Phase 1.4 barrier-local coverage to RMS_NORM.** NOT SAFE: RMS_NORM at decode shape `[d, 1, 1, 1]` runs single-threaded (only thread 0 with ne01=1 in the upstream `for (i01 = ith; i01 < ne01; i01 += nth)` loop). Cross-CCD threads need a global barrier to see thread 0's writes; Phase 1.4's "axis-0 partition" precondition is exactly what RMS_NORM at decode violates. Expanding the coverage would silently corrupt outputs.

**Angle B: parallelize RMS_NORM across ne00 with an intra-op reduction barrier.** Implementation in commit `0467a5c17` on `cpu-optimization/q8-8x8-avx512bw`. Each thread computes a partial sum over its k-slice → `ggml_barrier` → reduce + parallel scale. PPL preserved (6.6767 vs 6.6985 baseline, within noise).

NET-NEGATIVE at 96t: **4.02 vs 4.41 t/s = −8.8% regression.** The intra-op barrier (~5 μs at 96t) costs more than the saved single-thread compute (~10 μs). Default OFF, kept env-gated (`GGML_RMS_NORM_PARALLEL=1`) for documentation + future probing on workloads where the math could flip.

### Why both probes confirm the ceiling

The 22% in `ggml_barrier` is **barrier-count-bound, not per-barrier-cost-bound**. Adding intra-op barriers (parallelizing within ops) makes things worse. Lighter-weight barrier impls (CPU1 Phase 1.0+1.1's 2-level CCD-hierarchical is already there) don't help if the count stays constant. **The only lever that actually reduces barrier count is operator fusion** — collapsing N consecutive ops into one super-op so the executor only barriers once.

### Concretely fusable cluster (not pursued — ROI doesn't justify)

In qwen35.cpp DeltaNet builder: `wqkv` + `wqkv_gate` + `ssm_beta` + `ssm_alpha` are 4 matmuls all reading the same `attn_norm` output and producing independent results combined later in `gated_delta_net`. Fusing into one super-matmul (concatenated weight tensor at model-load + sliced output at graph-construction) saves 3 barriers per DeltaNet layer × 48 layers = 144 barriers/token = ~6 ms = **+2.6% throughput**. Effort: ~1 day.

Not pursued because the ROI doesn't beat the production-side alternative: **Q4_K_M on this exact model already runs at 6.75 t/s — +52% over Q8 with zero code changes.** Plus Q6_K/Q5_K 8x8 AVX-512BW kernels (Session 14 dispatcher gap, unchanged) would lift Q4_K_M decode by another +2-5% each.

### Final verdict on Qwen3.6-27B Q8_0 single-instance throughput

**The 4.4 t/s ceiling is genuinely architecture-bound for this hardware × this hybrid model.** Not BW-bound (only 25% of 460 GB/s); not kernel-bound (Session 15 AVX-512BW + NUMA fix already at the optimum); not parallelism-bound within ops (Session 15 parts 3 + 5 disproved). It is bound by barrier count × small per-op compute on a hybrid graph with ~590 ops/token.

The CPU2 lineage closes here for Q8 specifically. Production-side moves (Q4_K_M switch, Q6_K/Q5_K kernels, eventual op fusion of the QKV+gate+beta+alpha matmuls) remain the only paths to higher throughput, none of which are CPU2 territory.

### Reference data + commits

- Profile data: `/mnt/raid0/llm/epyc-inference-research/data/cpu_optimization/2026-04-24-q8-profile/` (raw `.data` files git-ignored at 36+18 GB; `findings.md` + symbol reports tracked).
- Branch: `cpu-optimization/q8-8x8-avx512bw` on `llama.cpp-experimental`, 4 commits ahead of `138b26cd4`:
  - `1d18efce3` AVX-512BW 8x8 Q8_0 GEMV kernel
  - `e84a5c82f` auto-mbind CPU_REPACK + K-parallel activation quant
  - `ba1c23900` env-gated DeltaNet S_v sub-chunking (default off)
  - `0467a5c17` env-gated parallel RMS_NORM (default off, net-negative)

All correct, env-gated for safety, PPL-preserved.

## 2026-04-26 additions

### Bottleneck class follows the QUANT, not the model size

`perf stat` profile across 5 production models on EPYC 9655 NPS4 canonical baseline (`taskset -c 0-95 -t 96 -fa 1`, no env vars) — Phase D + P2 of the 2026-04-26 session:

| Model | Quant | Size | t/s | IPC | CPU util | Cache miss | Class |
|-------|-------|------|-----|-----|----------|------------|-------|
| Qwen3-Coder-30B-A3B | Q4_K_M | 17.3 GiB | 44.0 | 0.38 | 46.6/96 | 22.5% | sync + cache stall |
| **Qwen3.6-35B-A3B** | **Q8_0** | 34.4 GiB | **14.6** | **0.12** | **75.2/96** | 9.7% | **bandwidth-bound** |
| Qwen3-Next-80B-A3B | Q4_K_M | 45.1 GiB | 23.3 | 0.41 | 41.7/96 | 16.6% | sync-bound |
| REAP-246B-A35B | Q4_K_M | 138.3 GiB | 6.9 | 0.50 | 49.3/96 | 7.1% | sync-bound |
| gemma-4-26B-A4B-it | Q4_K_M | 15.6 GiB | 25.0 | 0.23 | 59.0/96 | 13.9% | mixed |

**Q8_0 → bandwidth-bound** (cores running, stalled on DRAM). Aggregate utilization ≈25-30% but per-NUMA-node BW likely saturated. The +17% EP win on Qwen3.6-35B-A3B is consistent with this (EP gives 2× DRAM channels).

**Q4_K_M → sync-bound** (half the threads idle waiting at barriers). Aggregate BW only ~14% utilized; not bandwidth-limited. The 49/96 idle threads is **structural MoE top-K imbalance** — top-8 of 80 experts active per token creates uneven work distribution across CCDs, not a barrier-implementation defect.

**Implication for software levers**:
- Q8_0 frontdoor → EP (shipped, +17%) and L3aaN BIOS reboot (untested, BW-locality lever)
- Q4_K_M lineup → no remaining software lever (CPU4 hierarchical sync was implemented and measured **net-negative**, see CPU4 entry below)

### CPU4 hierarchical barrier on EPYC 9655 OpenMP — NEGATIVE RESULT

Implemented per `handoffs/active/cpu-hierarchical-barrier.md`: extracted CPU1's existing 2-level sense-flip CCD-hierarchical barrier from `#ifndef GGML_USE_OPENMP` so it activates in production OpenMP builds. Per-thread state lookup via `tp->workers[omp_get_thread_num()]`.

Build green, init logs confirm `[GGML_CCD_POOLS] enabled: 12 CCDs x 8 threads/CCD`. Measurements consistently net-negative:

| Model | Config | Δ vs canonical |
|-------|--------|----------------|
| Coder-30B Q4_K_M | + GGML_CCD_POOLS=1 | -4.3% |
| Coder-30B Q4_K_M | + GGML_CCD_POOLS=1 + OMP_PROC_BIND=close | -5.8% |
| REAP-246B Q4_K_M | + GGML_CCD_POOLS=1 | -0.9% |
| REAP-246B Q4_K_M | + GGML_CCD_POOLS=1 + OMP_PROC_BIND=close | -25% (catastrophic) |

Reverted; design preserved for future reference. **libgomp's omp barrier is competitive with a custom 2-level CCD-aware barrier on this hardware**. The 22-30% cycles in libgomp.so are NOT pure waste — much is productive scheduling work that the OMP runtime does correctly. `OMP_PROC_BIND=close` itself regresses -7% on canonical (interferes with libgomp's NUMA-aware scheduling).

### CPU1 NUMA_WEIGHTS instability isolated

`GGML_NUMA_WEIGHTS=1` (set_mempolicy(MPOL_INTERLEAVE) before mmap) is the entire cause of the previously-observed CPU1-stack instability (±13-22 t/s std on Coder-30B; -15% on Qwen3.6-35B Q8_0). Per-flag isolation on Coder-30B Q4_K_M -r 5:

| Config | t/s ± std | Verdict |
|--------|-----------|---------|
| canonical | 43.37 ± 0.10 | reference |
| +CCD_POOLS only | 43.44 ± 0.06 | safe |
| +NUMA_WEIGHTS only | 32.91 ± 22.18 | **UNSTABLE** |
| +CCD_WORK_DIST only | 43.66 ± 0.18 | safe |
| +BARRIER only | 43.88 ± 0.15 | safe |
| 3-flag (no NW) | 44.15 ± 0.13 | **+1.8% stable** |

Fix attempt at `llama.cpp-experimental:8cb04da9d`: replace process-wide `set_mempolicy` with per-region `mbind()` on the mmap region. **Correct scope fix but doesn't resolve the underlying instability** — `MPOL_INTERLEAVE` itself behaves unstably on shared file-cache multi-NUMA hosts under fragmented memory. `GGML_NUMA_WEIGHTS=1` is now deprecated for production. The 3-flag stack (no NW) is safe and delivers a small +1.8% on Coder-30B as opt-in.

### "Regression" was a transient

The historical 49.34 t/s on Qwen3-Coder-30B-A3B Q4_K_M (logged 2026-04-24 at HEAD `9e048fbc1`) is NOT reproducible today on the same source/binary. Same Apr-23-built binary measures 44.37 t/s today; a fresh-built binary at the same commit gives 44.29. **No source-level regression exists.** The 49.34 was a system-state spike (likely fresh post-reboot memory layout, favorable thermals, or page cache state) that doesn't generalize. 43-44 t/s is the stable canonical baseline at every commit from `9e048fbc1` through `8cb04da9d`.

This finding extends to several other "wins" claimed during the CPU1 era: many were captured during fresh-NPS-state windows. Going forward, single-run t/s spikes should be cross-validated across multiple system-states (fresh-reboot vs warm vs fragmented) before being treated as repeatable optimizations.

### CPU2 mbind kill-switch shipped

`GGML_NUMA_REPACK_INTERLEAVE` env var (default ON, `=0` to disable) added at `llama.cpp-experimental:af2e45de4`. Gates the unconditional `mbind(MPOL_INTERLEAVE)` on CPU_REPACK buffers ≥1 MiB introduced by `e84a5c82f`. Default-on rationale: **+6% AND stabilizing on Q8_0 (CPU2 target)**, -0.9% wash on Q4_K_M.

### `--numa distribute` paradox is mild today

Historical 2026-04-25 claim: `--numa distribute` regresses Qwen3.6-35B Q8_0 from 14.69 → 9.93 (-32%). Today's measurement: -6% only (14.79 → 13.90). Like the Coder-30B "regression" above, the historical magnitude was a transient. Production guidance is unchanged: avoid `--numa distribute` on multi-NUMA MoE workloads. `--numa isolate` is genuinely pathological (12+ min on a 32-token decode); never use.

### Sources (2026-04-26)

- `progress/2026-04/2026-04-26.md` — full Phase A-G + P1-P4 narrative
- `handoffs/completed/cpu-kernel-env-flags-inventory.md` — 20 env knobs classified, including trace-interpretation effects
- `handoffs/active/cpu-hierarchical-barrier.md` — CPU4 design + negative-result data
- `handoffs/active/cpu-shape-specialized-gemv-decode.md` (updated) — kill-switch addendum
- `handoffs/active/nps-reboot-runbook.md` (updated) — L3aaN evaluation plan post-2026-04-26
- `handoffs/active/cpu-optimization-thesis-pause-2026-04-26.md` — companion doc
- `llama.cpp-experimental:af2e45de4` — kill-switch
- `llama.cpp-experimental:8cb04da9d` — NUMA_WEIGHTS per-region mbind fix

## 2026-04-26 evening: L3-as-NUMA evaluated and rejected

The user's pre-recorded "next gate after NPS4 software levers exhausted" — switching the BIOS NUMA Nodes Per Socket setting from NPS4 (4 nodes × 3 CCDs) to L3-as-NUMA (12 nodes × 1 CCD) — was tested in this session. **Outcome: catastrophic regression on every measured config; reverted.**

### Result table — L3aaN single-engine (96 cores)

| Model | NPS4 | L3aaN canonical | L3aaN best (`numactl --interleave=all`) | Δ best vs NPS4 |
|-------|------|-----------------|------------------------------------------|----------------|
| Qwen3-Coder-30B-A3B Q4_K_M | 43.57 ± 0.10 | 23.07 ± 0.10 | 27.90 (96t) / 29.42 (24t) | **−32.5%** |
| Qwen3.6-35B-A3B Q8_0 | 14.63 ± 0.01 | 8.12 ± 0.01 | 8.32 ± 0.01 | **−43.1%** |
| Qwen3-Next-80B-A3B Q4_K_M | 23.25 ± 0.08 | 14.12 ± 0.05 | 15.93 ± 0.02 | **−31.5%** |
| REAP-246B-A35B Q4_K_M | 6.85 ± 0.01 | 3.30 ± 0.00 | 3.91 ± 0.02 | **−42.9%** |
| gemma-4-26B-A4B Q4_K_M | 25.01 ± 0.08 | 17.51 ± 0.04 | 18.62 ± 0.05 | **−25.6%** |
| Qwen3.6-35B Q8_0 + full EP | 17.18 (ref) | 8.39 ± 0.01 | (12-way EP at 8.49) | (canon −51%) |

### Result table — L3aaN 12-rank concurrent-split (the "designed-for" pattern)

12 parallel `llama-bench` instances pinned per-CCD (`numactl --cpunodebind=N --membind=N -t 8`) on Coder-30B Q4_K_M:

| Configuration | Aggregate t/s | vs NPS4 |
|---------------|---------------|---------|
| NPS4 4×48t | ~104 | ref |
| NPS4 32×6t (concurrent-split) | ~104 | parity |
| **L3aaN 12×8t** | **67.38** (high variance) | **−35%** |

### Tweaks tested (audit-driven, all measured)

- `GGML_NUMA_WEIGHTS=1` alone (deprecated, kept for record): +2.3% on Coder-30B
- 3-flag stable stack (`CCD_POOLS + CCD_WORK_DIST + BARRIER_LOCAL_BETWEEN_OPS`): +1.9% Coder, +3.4% Q8_0
- `GGML_NUMA_REPACK_INTERLEAVE=0` (CPU2 mbind kill-switch): neutral
- `GGML_EP_N_INSTANCES=12` (12-way EP, the documented L3aaN payoff path): neutral (8.49 t/s)
- `numactl --interleave=all -t 96`: **+20.9%** on Coder-30B Q4_K_M (largest single lever); only +2.5% on Q8_0 because CPU2 auto-mbind already handles its CPU_REPACK buffer
- Thread sweep at `--interleave=all`: 24t is the sweet spot (29.42 t/s — 3 NUMA nodes × 8 cores = local L3 + 3 channels)
- Literature `--no-mmap + --numa distribute` recipe (issue #11744): matched `--interleave=all`, did not exceed
- Best stacked single-engine config (24t + `--interleave=all` + 3-flag): 29.19 — no compounding above topology lever

### Why L3aaN structurally fails for this workload (literature-confirmed)

A background literature review (subagent, 70 tool calls) returned 6 highest-quality sources:

1. **L3aaN does NOT change IOD/UMC interleave or aggregate channel BW — only the SRAT table.** Source: [Broadcom TechDocs — L3 LLC as NUMA](https://techdocs.broadcom.com/us/en/storage-and-ethernet-connectivity/ethernet-nic-controllers/bcm957xxx/adapters/Tuning/bios-tuning/l3-llc-last-level-cache-as-numa.html), [HPC Advisory Council — AMD EPYC Tuning Guide](https://hpcadvisorycouncil.atlassian.net/wiki/spaces/HPCWORKS/pages/1280442391/AMD+2nd+Gen+EPYC+CPU+Tuning+Guide+for+InfiniBand+HPC). The original BW-bound Q8_0 hypothesis was wrong: hardware BW is unchanged, only the OS scheduler hints differ.
2. **L3aaN is classified as a benchmarking/diagnostic feature, not production.** Broadcom: *"meant for isolating L3 caches and is not recommended for production deployments."*
3. **AMD's own AI/ML recommendation for Turin is NPS4**, not L3aaN. Source: [Phoronix EPYC 9005 HPC tuning](https://www.phoronix.com/review/amd-epyc-9005-hpc-tuning).
4. **L3aaN is for HPC/MPI rank-per-CCX patterns** (each rank loads private memory into its CCD-local node), not OpenMP-style 96-thread shared-memory inference. SUSE/AMD/Lenovo guides consensus.
5. **`numactl --interleave=all` is the documented standard mitigation** for the multi-node first-touch pathology. [llama.cpp issue #1437](https://github.com/ggml-org/llama.cpp/issues/1437) shows +125% on 4 nodes; we measured +13-21% on 12 nodes for Q4_K_M.
6. **The dual-socket `--no-mmap + --numa distribute` recipe (+80% in [issue #11744](https://github.com/ggml-org/llama.cpp/issues/11744))** is recovering an 8× cross-socket xGMI bottleneck that doesn't exist on single-socket EPYC. Different category of fix.

### Why concurrent-split also regresses

HPC MPI workloads have **per-rank private memory** — each rank loads its data into the CCD's local DDR. llama.cpp inference has **shared file-backed memory** (one GGUF mmap, pages placed by first-touch and shared across all instances). Even with `--cpunodebind=N --membind=N`, GGUF pages aren't replicated, so 11/12 instances always read remote pages. Per-CCD BW budget is also too small: 1 CCD ≈ 38 GB/s vs NPS4 quarter ≈ 115 GB/s.

### Untested literature-suggested path

`GGML_NUMA_MIRROR` (vproxy-tools/llama.cpp fork — full per-node weight replication; +60% on dense FP16 dual 9275F per [discussion #12289](https://github.com/ggml-org/llama.cpp/discussions/12289)). Memory cost at 12 nodes:

| Model | 12× rep | fits 1.1 TB? | × 1.6 (optimistic) | vs NPS4 ref |
|-------|---------|--------------|--------------------|-------------|
| Coder-30B Q4 | 207 GB | ✓ | 47.1 | +8% / −3% vs peak |
| Q3.6-35B Q8 | 412 GB | ✓ | 13.3 | −9% |
| Next-80B Q4 | 541 GB | ✓ | 25.5 | +10% |
| REAP-246B Q4 | **1660 GB** | ✗ DOES NOT FIT | n/a | n/a |
| Gemma-26B Q4 | 188 GB | ✓ | 29.8 | +19% |

Modest projected gains on 3 of 5 models, breaks REAP-246B at 12-way. Not worth the multi-day fork merge plus per-model orchestrator routing complexity.

### Decision and forward path

L3aaN is **rejected** for this stack. Production NUMA topology is **NPS4 going forward**. The single confirmed production gain from CPU1+CPU2+CPU15 work remains EP frontdoor (+17% on Qwen3.6-35B Q8_0); everything else is opt-in research.

### Sources (2026-04-26 evening)

- `progress/2026-04/2026-04-26.md` — L3aaN evaluation + supplemental tweak sweep + literature review + 12-rank concurrent split
- `handoffs/active/cpu-inference-optimization-index.md` — POST-REVERT PICKUP block + result tables
- `handoffs/active/nps-reboot-runbook.md` — runbook header marked complete
- `data/cpu_optimization/2026-04-26-l3aan/` — 16 raw bench logs, plus `concurrent12/SUMMARY.md`
- `memory/project_l3aan_reverted.md` — auto-memory entry (per-NUMA replication caveat noted)
- Literature: Broadcom L3 LLC as NUMA, HPC Advisory Council EPYC Tuning Guide, llama.cpp #1437, #11744, #12289, Phoronix EPYC 9005 HPC tuning

## 2026-04-26 late evening — Post-revert findings (CRITICAL)

After the user's manual BIOS revert from L3aaN back to NPS4, the post-revert verification surfaced three findings that revise the framing of all earlier 2026-04 CPU optimization work:

### Finding 1 — The "canonical NPS4 baseline" is a steady-state-after-warming figure, not a cold-cache value

| Configuration | Cold-cache result (post-reboot) | Historical (warmed) reference |
|---|---|---|
| Coder-30B Q4_K_M, `taskset -c 0-95 -t 96 -fa 1` | **22.92 ± 0.13** | 43.57 ± 0.10 |
| Same after 1 warm-up pass | 32.40 ± 0.08 | — |
| Coder-30B Q4_K_M, `--mmap 0 + numactl --interleave=all -t 96` | **42.41 ± 0.23** | 43.57 ± 0.10 |

The 43.57 number that was used as the L3aaN comparison baseline was a steady-state value reached after 1.5+ days of repeated benchmarking. From a fresh boot with caches dropped, plain canonical produces 22-23 t/s due to first-touch page-cache placement on `mmap 1` (default). `numactl --interleave=all` does NOT override file-cache placement — only anon-mmap. So `--mmap 0 + --interleave=all` is the only config that produces a reliable cold-cache baseline near the warmed reference.

**Implication for the L3aaN evaluation**: Earlier in 2026-04-26 we declared "L3aaN regresses 47% on Coder-30B (23.07 vs 43.57)". The fair apples-to-apples comparison is L3aaN best (29.42 with `--interleave=all`) vs NPS4 best (42.41 with `--mmap 0 + --interleave=all`) = **L3aaN −30.6%**. The revert decision is unchanged (every other model still regresses 26-43% on best-known L3aaN config), but the framing was inflated by ~17 percentage points. Future cross-session comparisons must use the same cache-state and same NUMA-hint config.

### Finding 2 — NVMe RAID0 is split across NUMA nodes 2 and 3 under NPS4

Under L3aaN both NVMes lived in the same CCX quadrant. Under NPS4 they're split across nodes 2 and 3. RAID0 stripe IO will pull cross-node no matter where you pin the worker — single-node `numactl --cpunodebind=N --membind=N` can't keep IO local for `/mnt/raid0`.

Recommended pattern for RAID-heavy work: `numactl --interleave=2,3 …`. For inference where weight loading goes through RAID, `numactl --interleave=all` covers both weight pages and IO buffers.

This also explains the post-reboot anomaly that node 3 had 270 GB free vs 288 GB on others (~20 GB pinned to nodes 2-3 for RAID driver / DMA / buffer cache), and why `numactl --cpunodebind=0 --membind=0 -t 24` measured only 16 t/s rather than the expected ~26 t/s NPS4-quarter share.

### Finding 3 — `kernel.numa_balancing` self-resets to 0 despite sysctl.d apply

Confirmed by user 2026-04-26: the sysctl.d file is intact, `systemd-sysctl` reports successful apply, but the runtime value reads 0. Manual `echo 1 > /proc/sys/kernel/numa_balancing` works briefly but flips back. Earlier hypothesis that 12-node L3aaN was the cause is **invalidated** — same self-reset happens on plain NPS4. Real fix would be a oneshot service running after `systemd-sysctl`. Open item; not blocking.

**Implication**: any benchmark that depends on `numa_balancing` state must check it explicitly per session, not trust the sysctl.d file.

### Memory entries created

- `memory/project_raid_numa_split_nps4.md` — RAID/NUMA split + recommended interleave config
- `memory/feedback_numa_balancing_self_reset.md` — sysctl drift caveat
- `memory/feedback_canonical_baseline_protocol.md` (extended) — cold-vs-warmed protocol distinction

## 2026-04-26 late evening — Compounding matrix downgrades all prior CPU wins

User-requested methodology check ("verify lever compounding"). Most prior optimization wins were sub-baseline artifacts. Full data: `data/cpu_optimization/2026-04-26-compounding/SUMMARY.md`.

### Re-measured optimization deltas against proper cold canonical (`--mmap 0 + --interleave=all -t 96 -fa 1`)

| Track | Historic (warmed mmap=1) | Proper canonical | Status |
|---|---|---|---|
| **CPU15 EP frontdoor (Qwen3.6-35B Q8_0)** | **+17%** (14.63→17.18) | **+1.6%** (20.81→21.15) | **DOWNGRADE — noise** |
| **CPU15 EP regression on REAP-246B** | **−47%** (6.85→3.65) | **0%** (5.94→5.92) | **DOWNGRADE — was sub-baseline artifact** |
| CPU2 auto-mbind on Q8_0 | +6% claimed | 0% (redundant with --interleave=all) | DOWNGRADE — redundant |
| CPU1 3-flag stack (Coder-30B Q4) | +1.8% (warmed) | +0.6% | DOWNGRADE — noise |
| CPU2 AVX-512BW Q8_0 SIMD kernel | +31.8% @ 1t | unchanged (kernel does compute) | unchanged |

### The biggest practical win is the canonical config itself (no code)

| Model | Quant | Proper canonical | Warmed mmap=1 ref | Δ |
|---|---|---|---|---|
| **Qwen3.6-35B-A3B** | **Q8_0** | **20.81** | 14.63 | **+44%** |
| **gemma-4-26B-A4B** | **Q4_K_M** | **34.69** | 25.01 | **+39%** |
| Qwen3-Coder-30B-A3B | Q4_K_M | 42.27 | 43.57 | −3% (~equivalent) |
| Qwen3-Next-80B-A3B | Q4_K_M | 20.51 | 23.25 | −12% (warmed wins) |
| REAP-246B-A35B | Q4_K_M | 5.94 | 6.85 | −13% (warmed wins) |

Production deployment should be **model-aware**: `--mmap 0 + --interleave=all` is dramatically better for Q8_0 + gemma-26B; warmed mmap=1 path settles into better state for Next-80B + REAP-246B over time.

### Strategic implications

1. **Most "production-shippable" optimization gains were sub-baseline artifacts.** EP code is bit-correct (32-chunk WikiText-2 PPL bit-identical) but throughput-neutral on proper baseline. CPU2 auto-mbind is redundant with `--interleave=all`. CPU1 3-flag is noise.
2. **CPU24 attribution scope simplifies**: there's no measurable EP regression on >150B to attribute. Open question becomes "what's the proper-canonical ceiling for REAP-246B (5.94 t/s)" rather than "why does EP regress".
3. **CPU19 Tutel 2DH motivation evaporates**: was specifically to fix the >150B EP regression, which doesn't exist on proper canonical.
4. **Production push roadmap simplifies**: the "+17% production gain" was largely illusory; the actual gain is the canonical config change (+44% on Q8_0, +39% on gemma) which requires no code, just per-model deployment config.

## 2026-04-26 late-evening — CPU21 OpenMP affinity universal lever + CPU24 perf-record correction

### CPU21 OpenMP runtime/scheduling matrix sweep — universal +3-8% lever found

Sweep on Coder-30B Q4_K_M (sync-bound class proxy) testing:
- Affinity (PROC_BIND × PLACES): close/cores, close/threads, spread/cores, spread/threads, master/cores, false
- Schedule (static/dynamic/guided × chunk 1/4)
- Wait policy (active vs passive)

**Best stack**: `OMP_PROC_BIND=spread OMP_PLACES=cores OMP_WAIT_POLICY=active`. Schedule policy is within noise (libgomp's defaults are near-optimal). `OMP_WAIT_POLICY=passive` is a deployment trap (−81.6% on Coder due to wake-up latency at 96 threads).

**Cross-model verification (full 5-model picture)**:

| Model | Class | Baseline (no OMP env) | + Combined stack | Δ |
|-------|-------|----------------------:|-----------------:|---|
| Qwen3-Coder-30B-A3B Q4_K_M | sync-small | 43.82 | **47.08** | **+7.4%** |
| Qwen3.6-35B-A3B Q8_0 | BW-bound | 21.36 | **23.04** | **+7.9%** |
| Qwen3-Next-80B-A3B Q4_K_M | sync-small/hybrid | 21.37 | **22.15** | **+3.7%** |
| Qwen3-Coder-REAP-246B-A35B Q4_K_M | sync-large | 6.14 | **6.33** | **+3.1%** |
| gemma-4-26B-A4B Q4_K_M | sync-small/mixed | 36.45 | **38.59** | **+5.9%** |

**First universal-positive lever** identified in 2026-04 CPU work — every prior optimization had asymmetric/regressive cases on at least one model. CPU21 affinity tuning is positive on every class. Modest on REAP (+3.1%, capped by structural sync) and largest on BW-bound Q8_0 + gemma (+7.9%/+5.9%).

**Updated production canonical**:

```
OMP_PROC_BIND=spread OMP_PLACES=cores OMP_WAIT_POLICY=active \
  numactl --interleave=all --physcpubind=0-95 \
  llama-bench -t 96 -fa 1 -p 0 -n 32 -r 3
```

### CPU24-narrow attribution corrected by perf-record

Initial CPU24 perf-stat counter analysis suggested sync overhead = 96% of parallelism loss based on REAP-246B's 4.27× thread scaling (1t→96t). This was WRONG.

`perf record -F 99 -g` on REAP-246B at 96t (160k samples, 25-second decode capture) shows actual cycle distribution:

| Symbol | % of samples |
|--------|-------------|
| `ggml_gemv_q4_K_8x8_q8_K` (compute kernel) | **64.37%** |
| `ggml_vec_dot_q6_K_q8_K` (compute kernel) | **15.64%** |
| libgomp internal sync at offset 0x26580 | **15.50%** |
| `ggml_compute_forward_flash_attn_ext` | 0.73% |

**80% of cycles are in compute kernels; only 15% in OpenMP sync.**

The 4.27× scaling deficit is **per-thread bandwidth contention INSIDE compute kernels**: 96 threads sharing 460 GB/s = 4.79 GB/s per thread vs single-thread effectively-unlimited (~30-40 GB/s on its local channel). Cores spend cycles in the gemv loop but stalled on memory loads — perf-record sees them at compute-kernel IPs, but IPC 0.39 reveals they're not retiring instructions.

**Corrected attribution**: `dominant_bottleneck = compute_kernel (memory-stalled INSIDE)`. Sync is secondary at 15%.

**Implications**:
- **CPU2 SIMD kernel work is REVALIDATED priority** — 80% of cycles in compute kernels, faster SIMD = real wall-time reduction
- CPU19 Tutel 2DH motivation FURTHER weakened — 15% sync ceiling means even halving sync gains at most 7-8%
- CPU22 dynamic load balancing — gain ceiling bounded by 15% sync share (not 96% as previously framed)

### CPU17 Sarathi-Serve closed for single-user regime

Phase 0 quick probe sweep `-ub` (microbatch / chunk-prefill granularity) on Coder-30B Q4_K_M:

| `-ub` | pp4096 (prefill t/s) | tg32 (decode t/s) |
|-------|---------------------:|------------------:|
| 128 | 243.91 | 46.50 |
| 256 | 358.10 | 46.95 |
| 512 (default) | 443.83 | 46.26 |
| 1024 | 480.54 | 46.83 |
| 2048 | 511.22 | 46.61 |

**Decode speed essentially constant** (46-47 t/s) across all `-ub` values. Smaller `-ub` only damages prefill (−52% at ub=128 vs ub=2048). For single-user CPU regime: no decode-stall-during-prefill problem to solve since requests don't compete within a single iteration. CPU17 + CPU16 (NUMA disagg) both **closed**. Re-open trigger: shift to multi-tenant API.

### CPU2 Session 16 — Q6_K AVX-512BW dispatcher scaffolding

Given CPU24 perf-record shows `ggml_vec_dot_q6_K_q8_K` is the second-largest cycle consumer (15.64% on REAP-246B), Q6_K AVX-512BW SIMD is the highest-ROI remaining optimization. Session 16 landed dispatcher scaffolding (env-gated `GGML_Q6_K_8X8_AVX=1`, stub falls through to generic). Full SIMD algorithm design documented in handoff for follow-up session. Estimated +2-5% on Q4_K_M decode once body lands.

## 2026-04-28 — GPU-day kernel-DSL primer (intake-497, TileLang puzzles + parent project)

Forward-looking entry, not actionable on current CPU stack. Compiled so the GPU-acquisition wave starts with a kernel-DSL evaluation matrix already in place.

**Context**: `tile-ai/tilelang-puzzles` (215★ tutorial repo) is the recommended on-ramp to **`tile-ai/tilelang`** (5.8k★), the Peking U + Microsoft Research kernel DSL underlying **BitBLAS** (low-bit GEMM library, FP16/FP8 × INT4/INT8/INT2/INT1) and **AttentionEngine**. TileLang is built on TVM, exposes layout annotations / L2-cache swizzling / pipelining / rasterization / 2:4 sparse tensor cores as primitives, and supports NVIDIA / AMD (CDNA3 + RDNA3) / Apple Metal / Huawei Ascend / WebGPU + a December 2025 CuTeDSL backend that lowers to NVIDIA CUTLASS.

**Why it matters for the GPU-gated EPYC backlog**:
- **BitBLAS as natural GPU successor to ggml CPU quant path** — BitBLAS is the production GPU equivalent of our hand-tuned Q4_K_M / Q6_K / Q8_0 ggml CPU kernels (see `project_q8_8x8_avx512bw_outcome` and `project_x86_kquant_repack_gaps` memories). BitBLAS is TileLang-native, which makes TileLang the right authoring DSL for any GGUF→GPU quant adapters we'd need.
- **AMD MI300X parity claim** — parent README claims FlashMLA-MI300X parity vs hand-tuned assembly. If our GPU-day path is RX 7900 XTX or MI300X (`gpu-acceleration-path.md` AMD branch), TileLang is the differentiated kernel DSL; on NVIDIA Spark, FlashInfer + CUTLASS + TRT-LLM (intake-458/465/463) dominate.
- **Curriculum lineage** — inspired by srush/Triton-Puzzles, SiriusNEO/Triton-Puzzles-Lite, LeetGPU. ~4-hour walkthrough Copy → reductions → softmax → GEMM → FlashAttention.

**Kernel DSL evaluation matrix** (excerpt; full matrix in deep-dive):

| Kernel family | Triton | TileLang | CUTLASS / CuTe | Production picks |
|--------------|--------|----------|----------------|------------------|
| Vanilla GEMM | yes | yes | yes (peak) | cuBLAS / hipBLASLt — no DSL |
| FlashAttention | reference impls | yes | yes (FA3) | flash-attn library; DSL only for custom variants |
| Low-bit GEMM (Q4/Q6) | possible | **native (BitBLAS = TileLang)** | yes | BitBLAS — and BitBLAS *is* TileLang |
| FlashMLA on AMD | lagging triton-amd | parity claim vs hand-tuned (MI300X) | no | TileLang iff AMD path |
| MoE expert grouping | yes | possible | yes (grouped GEMM) | TRT-LLM iff NVIDIA Spark; otherwise Triton/TileLang |

**GPU-day action queue** (gated on hardware acquisition):
1. Day-0: tilelang-puzzles 1-10 in 4 hours as engineer onboarding.
2. Day-1 NVIDIA: TileLang FA puzzle output vs Triton FA reference vs FlashInfer vs FA3 on actual GPU → DSL decision matrix.
3. Day-1 AMD: reproduce FlashMLA-MI300X parity claim on RX 7900 XTX (RDNA3) or MI300X (CDNA3).
4. **Day-2 (critical path)**: BitBLAS GGUF compatibility — does it load Q4_K_M / Q6_K directly, or do we need a thin K-grouped quant adapter?

**Non-actions**: do NOT author CPU kernels in TileLang (Zen 5 / AVX-512BW / NUMA-4-way path remains hand-tuned ggml — TileLang's "generic CPU targets" claim is unsubstantiated for our use case). Do NOT pre-commit to TileLang before GPU lands. Triton literacy remains mandatory regardless of authoring choice (most modern inference papers ship Triton reference impls).

**Risks**: educational fork has weak signals (7 commits, idle 5 weeks at 2026-04-28); no peer-reviewed paper for the parent DSL itself; CuTeDSL backend lowering implicitly concedes that for NVIDIA peak performance, CUTLASS is the substrate; multi-backend portability claims always degrade in production.

**Sources**:
- [intake-497](https://github.com/tile-ai/tilelang-puzzles) — tile-ai/tilelang-puzzles (medium relevance, worth_investigating)
- [tilelang-puzzles-kernel-dsl.md](../research/deep-dives/tilelang-puzzles-kernel-dsl.md) — full deep-dive with kernel-family matrix, AMD path, BitBLAS connection, risk register
- [gpu-acceleration-path.md](../handoffs/active/gpu-acceleration-path.md) — parent GPU-gated handoff (2026-04-28 deep-dive integration section)
- intake-458 (FlashInfer), intake-465 (CUTLASS), intake-466 (Triton), intake-464 (FA3) — adjacent GPU-day kernel-DSL entries from 2026-04-26 curriculum batch

## Updates — 2026-04-28

Consolidation pass over the CPU20→CPU25 rigor-and-attribution wave plus toolchain (CPU11/CPU12) and runtime (CPU21) finalization. Closure scope is narrowed throughout: low-level levers are exhausted **for the single-user single-socket NPS4 decode regime**, not globally.

### Canonical CPU baseline (post-CPU20)

The replication-grade baseline as of 2026-04-26 post-CPU21:

```
OMP_PROC_BIND=spread OMP_PLACES=cores OMP_WAIT_POLICY=active \
  numactl --interleave=all --physcpubind=0-95 \
  llama-bench -t 96 -fa 1 -p 0 -n 32 -r 3
```

Cold-cache reference numbers under this protocol: Coder-30B Q4_K_M = 47.08 ± 0.15 t/s; Qwen3.6-35B Q8_0 = 23.04 ± 0.01 t/s; REAP-246B Q4_K_M = 6.33 ± 0.00 t/s. The 48-thread NPS4 single-instance peak on Coder-30B Q4 stays 46.6 t/s (per `project_cpu1_48t_new_best`). 4×48t → 32×6t / 48×4t concurrent-split aggregate gains (+44–58%, up to +110% on Qwen3.6-35B-A3B Q8 = 135.1 t/s vs 64.3 baseline) reproduce under this baseline.

CPU20 rigor gates are now binding for any compounding claim:
- Rep counts scale with delta size: ≥10% = 3 reps; 5–10% = 5 reps; 2–5% = 5 reps; ≤2% = 10 reps.
- Pre/post pgrep zombie-check on every run.
- System-state capture: `numactl --hardware`, `kernel.numa_balancing`, THP state, scaling governor.
- LD path identity smoke run via `LD_DEBUG=libs` to confirm libomp vs libgomp resolution.

### CPU decode mechanism — DRAM-wait dominated

CPU decode on EPYC 9655 NPS4 is DRAM-wait dominated, not ALU-bound (`feedback_cpu_decode_bw_bound`). Perf cycles inside dot loops are stalled on memory. Implication: do not write compute-focused ukernels for quantized decode without a bandwidth roofline check first. Two empirical confirmations:

- **CPU2 Q8_0 8x8 AVX-512BW kernel**: single-thread +31.8% (1.12 vs 0.84 t/s, Qwen3.6-27B Q8_0); multi-thread plateau +1–3% at 12–96t. Both baseline and tuned kernel hit ~26% of the 460 GB/s socket roofline at 96t — same wall, different paths to it. PPL bit-exact (6.6985 ± 0.708). Production-viable, env-gated default-OFF (`GGML_Q8_0_8X8_AVX=1`).
- **NUMA auto-mbind fix (commit `e84a5c82f`) was load-bearing**: without it the kernel regressed −2.8× at 96t because first-touch placement pinned all CPU_REPACK pages on NUMA node 0. `GGML_NUMA_REPACK_INTERLEAVE` (default ON) auto-mbinds CPU_REPACK ≥ 1 MiB; for Q8_0, mbind ON = +6% AND stabilizes variance. Default ON is correct.

Zen 5 microarchitecture nuance preserved (`project_zen5_vnni_vs_maddubs`): VPMADDUBSW runs 2/cycle, VPDPBUSD runs 1/cycle, so the 8x8 kernel deliberately avoids VNNI.

### NUMA / topology — closures

- **L3aaN (BIOS L3-as-NUMA) — DECISIVE NEGATIVE, do not reactivate**. All 5 production models regressed −30 to −52% under `GGML_NUMA_MIRROR` (Coder-30B, Next-80B, REAP-246B, gemma-26B, Qwen3.6-35B). Reverted 2026-04-26. Per `project_l3aan_reverted`.
- **GGML_NUMA_WEIGHTS=1 — DEPRECATED**. Process-wide `set_mempolicy(MPOL_INTERLEAVE)` is unstable on shared file-cache multi-NUMA hosts; per-region `mbind()` improved but the underlying mechanism remains unstable. CPU1 P3 isolation: `NW=1` alone = 20–33 ± 19–22 t/s (unstable; baseline 43.37); 3-flag stack without NW = 44.15 ± 0.13 (+1.8%, stable); full 4-flag stack with NW = broken. **Recommended CPU1 stack post-P3** (default-OFF until v5 audit confirms PPL bit-identical): `GGML_CCD_POOLS=1 GGML_CCD_WORK_DIST=1 GGML_BARRIER_LOCAL_BETWEEN_OPS=1` — no NUMA_WEIGHTS.
- **NUMA_MIRROR investigation closed DECISIVE NEGATIVE on single-socket NPS4** (CPU25, 2026-04-27). Hardware is DRAM-channel-bound, not fabric-bound. Compile flag `GGML_NUMA_MIRROR` stays default-OFF; production stack must NOT enable it. Reopen ONLY for 2-socket configs.

### CPU runtime stack — libomp (CPU21)

Apples-to-apples vs libgomp at fixed `-march=znver5`: Coder-30B Q4_K_M = +6.4% real (53.28 vs 50.06); Qwen3.6-35B Q8_0 = +0.8% (noise); REAP-246B Q4_K_M = −0.8% (noise). Model-specific win, not universal. Mechanism hypothesis: thinner per-thread row-shard tiles on Coder-30B (3.3B active params) benefit from libomp's scheduling and barrier heuristics; larger MoE and BW-bound classes saturate before runtime overhead matters.

Universal affinity stack (adds +3–8% across model classes): `OMP_PROC_BIND=spread OMP_PLACES=cores OMP_WAIT_POLICY=active`. Trap to avoid: `OMP_WAIT_POLICY=passive` = −81.6% regression. `OMP_SCHEDULE=guided,16` is per-role opt-in only (+3.6% libgomp / +1.2% libomp on Coder-30B; neutral elsewhere).

v5 deployment: clang-20 + libomp + `-march=znver5` as the universal binary — single audit story, +6.4% on Coder-30B, neutral elsewhere.

### Build-time toolchain (PGO, BOLT, LTO) — compounding

| Lever | v5 cherry-pick | Coder-30B Q4_K_M | Frontdoor Q8_0 | Compounds with stack |
|-------|---|---|---|---|
| clang-20 + libomp + `-march=znver5` | Universal | +6.4% baseline | +0.8% | YES |
| + PGO (mixed-B profile) | Universal | +3.2% | +6.6% | YES |
| + BOLT-libggml | Per-role (Coder only) | +2.1% (60.54 t/s) | −1.2% | NO (cross-model regressions) |
| + LTO on top of PGO | Reject | −1.0% | — | NO (neutral; do not add) |

Total compounded on Coder-30B: clang+libomp+znver5+PGO = +25.4% / 60.54 t/s vs original gcc+libgomp+no-march. PPL bit-exact at every step. v5 default = clang+libomp+znver5+PGO universal; per-role binary = + BOLT for Coder-30B-A3B-Instruct only.

### Multi-tenant / context-regime (CPU23 Phase 2.2)

Long-context TTFT on canonical 96-thread:

| Model | TTFT @ 2K | TTFT @ 8K | TTFT @ 32K |
|-------|---|---|---|
| Coder-30B Q4_K_M | 4.2s | 24.6s | 262.4s |
| Qwen3.6-35B Q8_0 | 5.2s | 22.0s | 146.8s |
| Qwen3.6-27B dense Q8 | 18.8s | 78.0s | **403.6s** |

Concurrent long-prompt-mid-stream interference (30K prefill + 10 sequential decode-32): Coder-30B (sync-bound MoE) shows **9.6× rep-1 TTFT amplification** (4.77 vs baseline 47.99 t/s); Qwen3.6-35B Q8_0 (BW-bound) 1.15× mild; Qwen3.6-27B dense 1.08× mild. Steady-state continuous batching (rep 2+) is within ±2% of baseline on all 3 classes — the spike is rep-1 only.

### Closure-inflation accounting — exhaustion map

Low-level CPU kernel/runtime/NUMA paths for **single-user single-socket NPS4 decode** are now mostly closed. Explicit scoping per `feedback_closure_inflation`:

- **Exhausted in this regime**: CPU1 NUMA interleave (deprecated, unstable); CPU4 hierarchical barrier (one variant net-negative); CPU22 dynamic MoE work-stealing (−2.3% Coder; single-atomic contention dominates 15% sync-share ceiling); L3aaN (−30 to −52%); LTO-on-PGO (neutral).
- **Narrow v5-ready wins**: CPU21 libomp+clang (+6.4% Coder-only); CPU21 affinity stack (+3–8% MoE Q4_K_M); CPU2 Q8_0 8x8 AVX-512BW (+31.8% at 1t, +1–3% at 96t); CPU11 PGO universal (+3.2 to +6.6%); CPU12 BOLT per-role Coder (+2.1%).
- **Re-openable on workload shift**: Sarathi-Serve chunked prefill (deprioritized single-user; the 9.6× TTFT amplification under concurrent prefill invites re-promotion on multi-tenant API). CPU18 MegaBlocks (if batched-MoE / prefill workload shifts). CPU24 root-cause work (sync+compute bottleneck at 80–15% split).

Broader claims ("software runway exhausted") are not made.

### GPU path (parked behind hardware acquisition)

vLLM DDTree+Dflash plan activates on GPU acquisition; community benchmark shows 91 tok/s accepted on Qwen3.5-27B AWQ + GB10 (DGX Spark). TileLang puzzles (intake-497) → BitBLAS path is the natural GPU successor to ggml's Q4_K_M / Q6_K / Q8_0 CPU kernels (low-bit GEMM in INT4/INT8/INT2). AMD MI300X parity reproduction (FlashMLA-MI300X) is potentially the cheapest GPU path; DGX Spark Blackwell at $4,699 (~70 t/s MoE decode) remains the most cost-effective NVIDIA option.

### PPL bit-exactness gate (consolidated)

v5 cherry-pick candidates have all passed PPL bit-exactness:

| Lever | PPL (Coder-30B Q4_K_M unless noted) | Status |
|------|---|---|
| CPU1 3-flag stack (no NUMA_WEIGHTS) | 11.1146 ± 0.62405 | bit-exact vs baseline |
| CPU15 EP (N=2 drone+shard, Qwen3.6-35B Q8_0) | bit-identical | shipped |
| CPU21 libomp build | 11.1146 vs libgomp 11.1215 (Δ 0.0069 = clang-vs-gcc fp-codegen drift) | acceptable |
| CPU22 work-stealing | byte-identical env=0 vs env=1 | failed throughput, code preserved |
| CPU2 Q8_0 8x8 AVX-512BW | 6.6985 ± 0.708 | shipped, env-gated |
| CPU11 PGO | 11.1146 byte-identical to pre-PGO | shipped universal |
| CPU12 BOLT | bit-exact (block layout / function reordering only) | per-role only |

### Sources

- [`handoffs/completed/cpu-kernel-env-flags-inventory.md`](../handoffs/completed/cpu-kernel-env-flags-inventory.md) — completed env-flag catalogue, P3 stability verdict, NUMA_WEIGHTS deprecation, and trace-interpretation effects
- [`handoffs/completed/cpu-benchmark-rigor-and-revalidation.md`](../handoffs/completed/cpu-benchmark-rigor-and-revalidation.md) — CPU20 protocol, canonical baseline config, replication rules
- [`handoffs/completed/cpu-openmp-runtime-scheduling-matrix.md`](../handoffs/completed/cpu-openmp-runtime-scheduling-matrix.md) — CPU21 libomp +6.4% Coder, affinity stack +3–8%, schedule per-role opt-in
- [`handoffs/completed/cpu-context-regime-coverage.md`](../handoffs/completed/cpu-context-regime-coverage.md) — CPU23 Phase 2.2 TTFT / interference findings
- [`handoffs/active/cpu-shape-specialized-gemv-decode.md`](../handoffs/active/cpu-shape-specialized-gemv-decode.md) — CPU2 Q8_0 8x8 AVX-512BW kernel +31.8% at 1t
- [`handoffs/completed/cpu-dynamic-moe-load-balancing.md`](../handoffs/completed/cpu-dynamic-moe-load-balancing.md) — CPU22 work-stealing falsified (5-rep)
- [`handoffs/active/sarathi-serve-cpu-evaluation.md`](../handoffs/active/sarathi-serve-cpu-evaluation.md) — CPU17 chunked-prefill deprioritized single-user; re-promote on multi-tenant
- [`handoffs/active/gpu-acceleration-path.md`](../handoffs/active/gpu-acceleration-path.md) — GPU parked, vLLM+Dflash, DGX Spark cost-effective, TileLang/BitBLAS GPU-day
- [`research/deep-dives/tilelang-puzzles-kernel-dsl.md`](../research/deep-dives/tilelang-puzzles-kernel-dsl.md) — kernel-DSL evaluation matrix, BitBLAS path, AMD MI300X relevance
- intake-497 — TileLang puzzles (medium relevance, worth_investigating)

## 2026-04-29 Update — CPU4 Phase 1 op-coalesced barriers + Phase 0 design pause

### CPU4 op-coalesced barriers (Phase 1) — TESTED, NO-GO (framing revised 2026-04-29 evening — Remediation Phase A)

The CPU4 sync-primitive track was reopened on 2026-04-29 after the user direction "CPU4 sync primitive" — but the original 2-level CCD-aware barrier variant (CLOSED 2026-04-26 negative) and the lock-free expert dispatch variant (= CPU22 #1, CLOSED 2026-04-28 at -2.3% Coder) were already falsified.

A new design — **op-coalesced barriers** — was advanced through Phase 0 manual op-chain analysis (estimated 24-29% per-token barrier-count reduction on Qwen3 MoE) and Phase 1 prototype (~80 LOC env-gated `GGML_BARRIER_COALESCE=1` default off, committed `9f6191581` in llama.cpp-experimental).

**Critical Phase 1 discovery**: smoke test at COALESCE=1 with MUL_MAT/MUL_MAT_ID in the coalescable allowlist produced GARBLED output. Root cause: `ggml_compute_forward_mul_mat` writes src1 quantization to the shared `params->wdata` buffer BEFORE its internal barrier (`ggml-cpu.c:1467-1487`). Coalescing two MUL_MATs lets op N+1 clobber wdata while op N's chunk-loop still reads it. **Phase 0 manual analysis missed this constraint** — only checked dependency-graph independence, not buffer-sharing.

After tightening the allowlist to exclude MUL_MAT/MUL_MAT_ID, smoke passes bit-exact and PPL chunk-3 is identical between COALESCE=0/1 on Coder-30B + REAP-246B. But the achievable per-token barrier-count reduction drops from 24-29% to ~5% (only ROPE-Q → RMS_NORM-K is coalescable per layer).

**Throughput measurement (REVISED 2026-04-29 evening — Remediation Phase A)**: original Phase 1 measurement showed -19.7% Coder regression, but was POISONED by missing OMP env stack (`OMP_PROC_BIND=spread OMP_PLACES=cores OMP_WAIT_POLICY=active`). Re-measured under FULL CANONICAL recipe (bundle [`2026-04-29-remediation-phase-A-cpu4/`](../../epyc-inference-research/data/cpu_optimization/2026-04-29-remediation-phase-A-cpu4/)):

| Model | Original (broken OMP) | Phase A re-test (canonical) |
|---|---|---|
| Coder-30B Q4_K_M | -19.7% (POISONED) | **+0.19% NEUTRAL** (5-rep canonical, c0=46.96, c1=47.05, c0_recheck=47.00) |

Original "definitive negative" framing was a measurement artifact: under broken OMP, sleeping barriers were unusually expensive, and the coalesce code's barrier-skipping interacted asymmetrically. Under proper canonical, both arms behave well and coalescing is essentially a no-op for throughput on this conservative allowlist.

Gate (≥+5%): NOT MET (was actually NEUTRAL, not regression). Patch stays in tree disabled-by-default. The MUL_MAT wdata race finding stands (correctness, independent of perf). Future work: expanding the coalesce allowlist (e.g., adding RMS_NORM+ATTENTION pairs) is now a cleaner exploration since the conservative path is verified neutral, not destructive.

### Lesson preserved for future Phase 0 analyses

**Manual op-chain analyses MUST check buffer-sharing constraints** (`params->wdata`, `params->wsize`, threadpool atomics), not just dependency-graph (src/dst) independence. The wdata-shared-buffer hazard caused the 5× overestimate of coalescing potential. Future Phase 0 analyses should add this as a binding gate.

### Phase 0 design notes for remaining design-space candidates (paper-only)

Two new design notes landed on 2026-04-29 enumerating the still-open CPU4 + CPU22 deferred avenues:

- [`cpu22-hybrid-spillover-design.md`](../handoffs/completed/cpu22-hybrid-spillover-design.md) — 3 variants of hybrid static+dynamic work distribution. Gain ceilings 1-7% (capped by CPU24's 15% sync share, mostly already captured by existing per-expert dynamic chunk-stealing). LOC 100-300. Single-atomic contention risk class same as failed CPU22 #1.

- [`wdata-aware-mul-mat-coalescing-design.md`](../handoffs/completed/wdata-aware-mul-mat-coalescing-design.md) — architectural change to `ggml_cplan` (per-op wdata segments instead of shared `work_data`). Allows MUL_MAT pairs to coalesce safely. LOC 260-410. ABI implications. Gain ceiling 9.5-14% barrier reduction → 2-7% t/s estimate (universal across architectures).

Both have similar gain-per-LOC (~0.01-0.03% per LOC). Neither strongly compelling for Phase 1.

### Pattern: structural ceilings dominate the remaining CPU-optimization design space

After 5 closed-via-test mechanisms in this design space (CPU4 original 2026-04-26, CPU22 #1 2026-04-28, slot-promotion + MAB selector 2026-04-29, CPU4 Phase 1 2026-04-29 — note: Remediation Phases A/C 2026-04-29 evening revised some "decisive negative" framing to "neutral / within-noise" but did NOT flip any closure to GO), the pattern is clear: **the remaining CPU-optimization design space has structural gain ceilings (15% sync, ~10% barrier reduction) that implementation overhead consumes.**

Recommended pivot to higher-leverage activities:
1. **Multi-arch coverage** — test existing v5 PGO + CPU2 mbind + CPU1 stack on dense / hybrid SSM / attention-only models
2. **Workload-shape coverage** — prefill, multi-tenant batching, long-context (32K+)
3. **Different toolchain frontier** — newer compiler versions, AMX
4. **Higher-level mechanism research** — model-level fusions, quant layouts

This represents an honest acknowledgment that the within-ggml CPU-optimization design space is largely exhausted at the current hardware, and pivoting research direction is more productive than further squeezing existing levers.

## 2026-04-30 Update — v5 Cleanup Audit COMPLETE

### `production-consolidated-v5` branch ready

Single-session cleanup audit (~90 min wall-clock) producing a clean, minimal v5 branch from the experimental kernel. Branch state: 59 commits ahead of v4 = 50 cherry-picks (clean, zero conflicts) + 9 strip/refactor commits, ~−940 LOC of dead-by-default deprecated code stripped.

Audit handoff: [`v5-push-cleanup-audit.md`](../handoffs/completed/v5-push-cleanup-audit.md). Bundle: [`2026-04-30-v5-cleanup-audit/`](../../epyc-inference-research/data/cpu_optimization/2026-04-30-v5-cleanup-audit/).

### Decisions resolved

| Q | Decision | Note |
|---|---|---|
| CPU22 work-stealing | **STRIP** | Closure-via-test failed (-0.89% Coder, +0.18% Next, -0.32% REAP under canonical). No reopen workload identified. |
| Legacy `GGML_Q8_0_8X8` vs `_AVX` | **REFACTOR-AND-KEEP both** | Different layers (gateway flag at repack.cpp:5031 vs SIMD path selector at arch/x86/repack.cpp:1550) — complementary, not redundant. |
| `GGML_NUMA_WEIGHTS` family | **STRIP code + research deep-dive** | See [`numa-weights-deep-dive.md`](../../epyc-inference-research/research/numa-weights-deep-dive.md). |
| v4 baseline location | In-place workflow in experimental repo (both repos at SHA `e734a6828`) | |
| Toolchain ordering | AFTER cherry-picks, no CMake source change | Operator-applied at build via `-DCMAKE_C_COMPILER=clang-20 ...`. |

### Stripped (LOC removed)

- CPU22 work-stealing (`GGML_EP_WORK_STEALING`): −114
- `GGML_RMS_NORM_PARALLEL`: −80 (net-negative −9% per inline measurement)
- `GGML_GDN_K_PER_HEAD`: −55 (no current effect)
- CPU15 Phase 1+2 in `mul_mat_id`: −84 (superseded by Phase 3.2 inter-process EP)
- CPU15 Phase 2 anon-copies producer (loader): −211
- `GGML_NUMA_WEIGHTS` family soft strip: −90
- `GGML_NUMA_WEIGHTS` family hard-strip follow-up: −337 (deletes `if (false)` blocks + Lever A' consumer in ggml-cpu.c)

**Total stripped: ~940 LOC of dead-by-default code.**

### Refactors (KEEP commits cleaned up)

- `GGML_EP_VERBOSE` env flag introduced — gates 5 unconditional INFO `fprintf` lines in `ggml-ep-bootstrap.cpp` + 2 in `ggml-ep-shard.cpp`. Error-path fprintf untouched.
- `GGML_MUL_MAT_BLOCK` macro — replaces 6 bare `16` constants in mul_mat / mul_mat_id block-tile dimensions. Documented as Zen 4/5 AVX-512 register pressure × cache-line tuning.

### Validation gates (ALL PASS)

| Gate | Result | Threshold |
|---|---|---|
| Build (clang-20 + libomp 5.1 + `-march=znver5`) | 0 errors / 1 pre-existing test-code warning | 0 errors |
| Tripwire — Coder-30B Q4_K_M tg32 r=5 canonical | 47.13 ± 0.74 t/s | ≥47 cold-boot |
| **PPL bit-exact** — Coder-30B Q4_K_M chunks 1-12 | **11.1146 ± 0.62405** (exact match v4) | byte-identical |
| Bench Coder-30B Q4_K_M tg32 r=5 | 47.49 ± 0.17 t/s | ≥46.0 |
| Bench Qwen3.6-35B Q8_0 tg32 r=5 | 22.79 ± 0.04 t/s | ≥22.5 |
| Bench REAP-246B Q4_K_M tg32 r=5 | 6.25 ± 0.01 t/s | ≥6.15 |
| Bench gemma-31B Q4_K_M tg64 r=5 | 7.11 ± 0.01 t/s | ≥6.25 |

All bench σ ≤ 1%. Phase 4 wall-clock: ~5 min (PPL on default n_ctx=512 + bench r=5).

### Lesson preserved for future audits

**Inventory SHAs go stale after rebase.** The handoff inventory had cherry-pick hashes from a pre-rebase history snapshot. Only 2 of 22 hashes were findable in the current branch. Phase 0 reconciliation is mandatory for any "cherry-pick from another branch" workflow. Procedure: enumerate `v4..feature/X` actual commits, match by commit message + scope keyword, persist the verified-current SHA list in the inventory before any cherry-pick runs.

**C++11 static-lambda init = static-cached pattern.** The inventory flagged `repack.cpp` `static const bool x = []() { ... }();` as "uncached getenv". This is a wrong-classification; the lambda runs once at static initialization, semantically equivalent to the `static int s = -1; if (s < 0)` C-idiom. Future audits should not flag this idiom as a refactor target.

**Instruction-tuned model PPL on raw text is anomalous, not a regression.** PPL on `gemma-4-31B-it Q4_K_M` chunks 1-12 with default `--chunks 12` returned ~13357 — three orders of magnitude above expected. Root cause: instruction-tuned models expect chat-template wrapping; raw wiki.test plain-text is OOD. Same behavior occurs on v4 binary. Don't gate v5 on this number — use chat-template-wrapped eval or skip raw-text PPL for `-it` models.

### Pivot — v5 audit confirms structural ceiling pattern

The v5 audit produced no new throughput findings (validation was bit-exact + no-regression by design). It validates the prior conclusion (2026-04-29 entry above) that the within-ggml CPU-optimization design space is largely exhausted at this hardware. The audit's main value is **branch hygiene** — eliminating ~940 LOC of falsified-mechanism dead code from the production-bound branch — not new perf wins.

### Out of scope (deferred to follow-up)

- **Orchestrator-stack rollout**: per-role `binary_path` + `env` wiring per [`model-registry-v5-deployment-draft.yaml`](../handoffs/active/model-registry-v5-deployment-draft.yaml). User explicitly out of scope ("nowhere close to altering the orchestrator stack"). Deployment-draft stays in `handoffs/active/` as future-work staging.
- **Per-role smoke gate (Batch 5)**: requires orchestrator integration first.

### 2026-04-30 PM — v5 push + PGO/BOLT production binaries COMPLETE

`production-consolidated-v5` branch (tip `23bcd6aaf`, 59 commits) was pushed to GitHub. PGO and BOLT production binaries were built in `/mnt/raid0/llm/llama.cpp` (main fork, NOT the experimental dev tree).

**Build artifacts**:

| Directory | Purpose | Key output |
|---|---|---|
| `build_libomp_pgo_use/` | Universal PGO — all roles | `bin/llama-server` (11 MB), `bin/libggml-cpu.so.0.9.11` (1.4 MB) |
| `build_libomp_pgo_bolt/` | BOLT-ready build (relocs preserved) | `bin/llama-server` (13 MB), `bin/libggml-cpu.so.0.9.11` (1.8 MB) |
| `build_libomp_pgo_bolt/bin_bolted/` | Per-role BOLT lib (Coder-30B only) | `libggml-cpu.so.0.bolt` (6.3 MB) |

PGO profile: `/mnt/raid0/llm/llama.cpp-experimental/build_v5_pgo_gen/merged.profdata` (2 MB, collected April 28).
BOLT profile: collected from a DeepSeek-R1-1.5B instrumented run (~1 min; covers same ggml kernel code paths as production models; instrumentation overhead scales with model size, not kernel coverage).

**Key build engineering findings** (validated for future reference):

- `clang-20` cmake configure requires `-L/usr/lib/gcc/x86_64-linux-gnu/13` in linker flags to find `libstdc++`. Omit this path for the actual build (bake it only during configure).
- `-fprofile-instr-use` cannot be set at cmake configure time — cmake's compiler test rebuilds with those flags and the linker fails. Fix: configure without PGO flags, patch `CMakeCache.txt` directly after configure, then `touch CMakeFiles/cmake.check_cache` to freeze the check timestamp.
- BOLT fdata is binary-specific (counter IDs tied to specific binary layout). Cannot reuse fdata from a previous build — must re-collect from the new binary.
- For BOLT profiling, small models (~1.5B) cover identical kernel code paths as production models. Do NOT use large models (24 GB+) for BOLT profiling — instrumentation overhead is ~25× and wall time is ~90 min.
- `libstdc++-14-dev` required on this host for clang-20's GCC 14 toolchain detection (`apt install libstdc++-14-dev`).
- `bolt-20` package provides `llvm-bolt-20` binary (`apt install bolt-20`).

**Next gate**: orchestrator wiring (binary_path + env per role in model_registry.yaml). Blocked on user authorization; deployment-draft at `handoffs/active/model-registry-v5-deployment-draft.yaml` is the staging document.

Source: [progress/2026-04/2026-04-30.md section "v5 kernel push + PGO/BOLT production binaries"](../progress/2026-04/2026-04-30.md)

## 2026-05-04 Update — host_prereqs persistence + per-NUMA-node concurrent scaling

### Canonical OMP env stack persistence

The 2026-04-29 finding that post-reboot Coder-30B drops 17 → 48.8 t/s without `OMP_PROC_BIND=spread / OMP_PLACES=cores / OMP_WAIT_POLICY=active` (per `feedback_omp_env_stack_required`) was previously enforced only by per-bench discipline. 2026-05-04 wired persistent enforcement on three layers:

1. **Boot-time defaults** via `/etc/sysctl.d/99-epyc-inference.conf` for `kernel.numa_balancing=0` + `kernel.perf_event_paranoid=1`.
2. **Per-session drift catch** via `scripts/session/health_check.sh` (extended with NUMA balancing / THP / perf_paranoid checks; each emits a fix command on failure).
3. **Per-launch enforcement** via `apply_host_prerequisites()` and `build_launch_env()` in `epyc-orchestrator/scripts/server/orchestrator_stack.py` — every llama-server launch now applies the canonical OMP env stack + per-role GGML_* env block from `_ROLE_ENV_BLOCKS` (sourced from `model-registry-v5-deployment-draft.yaml`). Refuses to launch on prereq failure unless `--skip-host-prereqs` opt-out flag is set.

The "self-resets to 0" claim from `feedback_numa_balancing_self_reset` (2026-04-26) could not be verified in the 2026-05-04 session — sysctl.d apply succeeded and held throughout the session. The memory entry is 7+ days old and may be stale; re-validate after next reboot.

Source: [progress/2026-05/2026-05-04.md](../progress/2026-05/2026-05-04.md), [model-registry-v5-deployment-draft.yaml](../handoffs/active/model-registry-v5-deployment-draft.yaml) host_prerequisites section.

### Per-NUMA-node concurrent scaling — linear 4-way confirmed on 122B-A10B

Probe B Phase 2 (2026-05-04) measured Qwen3.5-122B-A10B Q4_K_M under 4 wiring configurations with the same env block (canonical OMP + `GGML_NUMA_REPACK_INTERLEAVE=0`):

| Wiring | per-instance t/s | Aggregate |
|---|---|---|
| 1× canonical 96t (`numactl --interleave=all -- taskset -c 0-95`) | 12.19 ± 0.05 | 12.19 |
| 1× single-NUMA-node 24t (`--cpunodebind=0 --membind=0`) | 4.21 ± 0.01 | 4.21 |
| 2× concurrent per-NUMA-node 24t | 4.19 / 4.27 | 8.47 |
| **4× concurrent per-NUMA-node 24t** | 4.15-4.25 (avg 4.22) | **16.86** |

Linear 4× scaling: each per-NUMA-node 24t instance saturates its node's 3 DRAM channels independently with no cross-node contention. **4× per-NUMA-node aggregate (16.86) beats 1× canonical (12.19) by +38%** when the workload can actually issue 4 concurrent requests. For single-request latency, 1× canonical wins; for throughput-bound workloads, 4× per-node wins. Production was previously running 2× cross-NUMA at 8.6 t/s aggregate — suboptimal in both dimensions (latency-wise vs 1×, throughput-wise vs 4×).

This is the same per-NUMA-node-saturation pattern as the 2026-04-24 concurrent-split finding (32×6t on 35B-A3B = 135.1 t/s aggregate, +110% vs 4×48t baseline). The linear-scaling regime applies when each instance's BW demand fits one NUMA node's 3 channels (~115 GB/s).

Wiring change LANDED in `epyc-orchestrator` commit `64101fd`: architect_general switched from 2× cross-NUMA to 1× canonical full-machine. `_numa_prefix()` extended with optional `numactl_policy` field to wrap launches with `numactl --interleave=all --` for canonical-recipe roles. NUMA_FULL = ("0-95", 96) constant added.

### Q6_K AVX-512BW kernel — bit-exact, BW-saturated at 96t (no production benefit)

Phase A.1 PPL gate: 5/5 production models bit-exact under `GGML_Q6_K_8X8_AVX=1` vs scalar generic (Coder-30B 8.2622, gemma-31B 4359.7, SuperGemma-31B 19.6921, Qwen3-Next-80B 4.1565, REAP-246B 8.1396 — all Δ=0).

Phase A.2 perf gate at 96t under canonical recipe: aggregate geomean **-0.28%**, REAP-246B regresses **-1.01%** (z>0). Gate FAILS — kernel is correct but BW-saturated at 96t (consistent with `project_q8_8x8_avx512bw_outcome` "+1-3% at 12-96t (BW-saturated)" pattern). Q6_K kernel kept env-gated default-OFF in `production-consolidated-v5`. Phase B (Q5_K body) and Phase C (blanket Q{5,6,8}_K default-on flip) **de-prioritized** — the compounding rationale for blanket flip is falsified.

The +31.8% single-thread benefit (per `project_q8_8x8_avx512bw_outcome`) remains opt-in via `GGML_Q6_K_8X8_AVX=1` for low-thread workloads. Source: [data/cpu_optimization/2026-05-04-q6k-default-on-validation/findings.md](../../epyc-inference-research/data/cpu_optimization/2026-05-04-q6k-default-on-validation/findings.md).

## 2026-05-08 Update — Sakana TwELL / SparseLM (intake-529/530/531) — design-reference-only

Sakana AI released [arxiv:2603.23198 "Sparser, Faster, Lighter Transformer Language Models"](../research/intake_index.yaml) (2026-03-24) along with a [publication blog](https://pub.sakana.ai/sparser-faster-llms/) and [github.com/SakanaAI/sparser-faster-llms](https://github.com/SakanaAI/sparser-faster-llms). The technique: L1 regularization on FFN hidden activations during from-scratch pretraining induces >99% average activation sparsity at iso-quality; a custom Hopper-only (SM 90A) fused CUDA kernel with the **TwELL (Tile-wise ELLPACK)** packing format avoids materializing the dense post-ReLU hidden vector. Reported gains: +17–20% inference, +7–22% training, 19–28% peak memory reductions on 0.5B / 1B / 1.5B (the **2B configuration shows a +22.3% memory regression** in Table 1, anomalous and unexplained), all vs dense BF16. Hardware: NVIDIA H100 PCIe.

**TL;DR**: `worth_investigating` (narrowed to "design-reference-only"). **Not adoptable on the production EPYC stack today.** Three structural blockers compound:

1. **MoE vs dense FFN architecture mismatch**. SparseLM checkpoints are dense gated-MLP (`SparseLlamaForCausalLM`, `model_type: "llama_sparse_relu"`); production stack is MoE (Qwen3 30B-A3B, Coder-30B, Next-80B, REAP-246B). TwELL skips post-ReLU zeros within a single FFN; MoE skips entire experts. The two compute-saving regimes do not orthogonal-stack on the same model — paper does not demonstrate it. No MoE-TwELL variant exists.
2. **SwiGLU vs ReGLU activation mismatch**. SparseLM uses `nn.ReLU` in actual model code (`hidden_act: "silu"` in `config.json` is a leftover overridden by `sparse_models.py`). Production drafters/targets use SiLU/SwiGLU. Adopting forces retraining FFN as ReGLU (cost: full pretrain) or using SparseLM 2 048-context toy checkpoints directly (cost: cannot replace any production role). Draft-target compatibility is broken — SparseLM cannot be a drafter for any Qwen target (guaranteed logit drift).
3. **No quantized baseline anywhere in the paper**. All speedups are vs dense BF16 — never against Q4_K_M / Q8_0 / FP8. Q4_K_M loads ~0.5 bytes/weight; sparse-BF16 at 99% sparsity is ~0.32 effective bytes/weight (with 32-bit packed `(idx, val)` overhead), but Q4_K_M's 256-element super-block layout is broken by indirect-addressed sparse loads. Either duplicate the super-block scale per non-zero index (memory blow-up) or read full super-blocks anyway (no BW saving). The headline +20% gain may not survive an apples-to-apples comparison.

**TwELL bit layout (worth recording as a design reference)**: 32-bit unit per non-zero, `(col_idx[15:0], BF16_value[31:16])`; per-row NNZ header (atomic-incremented during D2T fill); `T_n=256` tile width with compression factor 2/4/8x (default 8). The lightweight T2D path (`matmul_t2d.cu`, 153 lines, plain CUDA cores with `__shfl_sync` + `__ldcs/__stcs`) is bandwidth-bound and **maps cleanly to AVX-512BW masked-GEMV** in principle — estimated CPU port cost ~1–2 dev-weeks (gated on Zen 5 AVX512_BF16 verification per `project_zen5_vnni_vs_maddubs` precedent). The D2T (training) side is impractical to port (uses cluster / TMA / WGMMA — no CPU analog), but D2T isn't needed for inference.

**Repo reality**: 4 commits, all by single author Cetin (`Aladoro`); 1 stalled PR by Castillo (`emcastillo`); no tests, no CI, no `setup.py`; default branch `master` not `main`. Empty HF model cards. Repo MIT / HF weights Apache-2.0 license mix. `OUT_DIM=2048` hardcoded in the T2D kernel — kernel specialized to SparseLM's hidden dim.

**Counter-evidence to NimbleEdge**: Sakana's "scaling helps sparsity" claim (38% fewer non-zero activations going 0.5B → 2B at matched perplexity) is direct counter-evidence to the NimbleEdge thesis recorded in [intake-528 contradicting_evidence](../research/deep-dives/kolinko-effort-engine-deep-dive.md) that *modern dense / small-MoE LLMs lose the activation-magnitude sparsity OPT-class models had*. **But Sakana's evidence is single-lab, single-recipe, 0.5B–2B from-scratch — not yet replicated at production scale or another architecture family — and the 2B memory regression internally contradicts the scaling claim.** Both theses remain unsettled.

**Refined re-surface triggers**: (1) finetune-from-existing-weights variant (paper's own future work); (2) **combined sparse + INT4/Q4_K kernel result vs Q4_K_M dense baseline** — the apples-to-apples we need; (3) MoE variant of TwELL — could compound on Qwen3 30B-A3B; (4) Qwen-family or DeepSeek-family checkpoint released using this recipe; (5) CPU port by anyone demonstrating BW savings under indirect-addressed gather on EPYC-class chip; (6) internal pretraining-from-scratch campaign in our project; (7) sorted-bucket repack format lands in ggml for unrelated reason — trailing-skip / TwELL packing become reusable design references (shared with intake-528 trigger #1).

**Source**: [research/deep-dives/sakana-sparser-faster-llms-deep-dive.md](../research/deep-dives/sakana-sparser-faster-llms-deep-dive.md) — full source-level audit (paper Section 1–6 + actual TwELL CUDA source + HF checkpoint configs + repo metadata via GitHub API). Cross-references: intake-528 (Kolinko Effort Engine, same dynamic-activation-sparsity neighborhood); intake-474 / intake-493 / intake-511 (Sakana lab cluster: Trinity, Conductor, KAME); intake-467 (MegaBlocks, block-sparse MoE GEMM at structured-block granularity vs unstructured-weight here). Handoff anchor: [`cpu-shape-specialized-gemv-decode.md`](../handoffs/active/cpu-shape-specialized-gemv-decode.md) Research Intake Update + Deep-Dive Addendum sections.

## 2026-05-08 Update — NUMA full XOR quarters (worker_general gemma4 swap)

The 2026-05-08 worker_general → gemma4-26B-A4B MTP swap (see [Speculative Decoding § Production deployment](speculative-decoding.md#production-deployment-landed-2026-05-08)) surfaced a long-standing latent issue in the orchestrator's NUMA design: **`--only worker_general` brings up 1 full-NUMA-node instance + 4 quarter instances, and the 5 share overlapping CPU sets**. The full instance pins to CPUs 0-95 (all physical cores); the 4 quarters split into Q0A (0-23+SMT) / Q0B (24-47+SMT) / Q1A (48-71+SMT) / Q1B (72-95+SMT) — together also covering 0-95.

Pre-2026-05-08 (Qwen3-Coder-30B-A3B with `-t 24` per the 1.5B-era leftover), this overlap was tolerable: 5 instances × 24 threads = 120 threads on 192 logical CPUs, 0.6× subscription. With gemma4-MTP's required `-t 96` (full) / `-t 48` (quarters) per the canonical recipe, the math shifts to 1×96 + 4×48 = 288 threads on 192 logical CPUs = **1.5× CPU oversubscription**.

**Verified 2026-05-08**: load average jumped to 420; the full-speed instance throughput collapsed from **76.5 t/s solo → 9 t/s** with the quarters running. The kernel scheduler thrashes 288 threads across 192 CPUs and decode performance degrades catastrophically.

**Two-mode design**: production deployment must currently pick **either** the full-speed instance (max single-request throughput, single instance) **or** the 4 concurrent quarters (max aggregate throughput under multi-request load, no single instance) — **not both**. Workaround: run `start --only worker_general`, then manually `stop server_<port>` for the unwanted instances. Filed as [`launcher-numa-mode-gating.md`](../handoffs/active/launcher-numa-mode-gating.md): proposed `--numa-mode {full,quarter,both}` flag with `quarter` as the back-compatible default.

**Generalizes to any role with `-t` matching the canonical recipe**: any future role launched with full-canonical thread counts will hit the same overlap if its `NUMA_CONFIG` declares both a full-NUMA-node entry and quarter entries. The pattern is to restructure the role's instance list to one or the other, never both, gated by operator intent.

**Cross-references**: [progress/2026-05/2026-05-08.md § session 2 § Phase 3](../progress/2026-05/2026-05-08.md), commit `e205309` (epyc-orchestrator).

## CPU decode roofline measurement — BW math + AMD-correct counters (2026-05-28)

Two reference numbers that anchor any CPU decode performance claim on this host:

- **614 GB/s socket theoretical**: EPYC 9655 has 12 DDR5 channels at DDR5-6400 MT/s. `12 × 6400 × 8 = 614.4 GB/s`. Earlier text in some handoffs (now corrected) wrote 307 GB/s — that was wrong. Under NPS4 the 12 channels are split 3 per NUMA node → ~153.6 GB/s per-node theoretical.
- **~460 GB/s aggregate practical ceiling** under `--interleave=all` (per `feedback_canonical_baseline_protocol`) — ~75% of theoretical. Report achieved BW against **both** numbers: one answers "am I close to physics?", the other answers "am I close to what this configuration actually achieves?".

**AMD Zen 5 perf counters** (NOT Intel). Initial draft of [`cpu-decode-flops-roofline-audit.md`](../handoffs/completed/cpu-decode-flops-roofline-audit.md) prescribed `fp_arith_inst_retired.*` + `uncore_imc/cas_count_*` which `perf list` on this AMD host rejects. The Zen-5-correct families are:
- FP retire (sum sub-events; `mac_flops` counts FMAs as 2 ops): `fp_ret_sse_avx_ops.{all,mac_flops,add_sub_flops,mult_flops,div_flops}`
- DRAM via Data Fabric PMU (if kernel-exposed): `amd_df/cs_dispatched_*/` — event codes are Zen-revision-specific, confirm with `perf list amd_df/*`
- DRAM alternatives in priority order: PCM `pcm-memory` (recent builds support AMD) → AMD μProf `AMDuProfPcm` → `numastat` `numa_hit` pre/post-delta fallback (coarse but always available)

The roofline audit handoff is **blocked at Status: DRAFT** until Phase 0 counter calibration on this host produces all four artifacts (tested `-e` string, `perf stat -- sleep 1` transcript with every event resolving to numeric, DRAM-path resolution evidence, host identity stamp from `/proc/cpuinfo` + `numactl --hardware` + `uname -r`) and persists them in the handoff body. Reboot or kernel/microcode change invalidates the calibration.

**Decision rule (consistent across all referencing docs)**: achieved FLOPS < 10% of ~9.2 TFLOPS FP32 socket theoretical AND achieved DRAM BW > 70% of 614 GB/s socket theoretical → BW-bound; diffusion-LM port variants (Nemotron-LD Variant B TiDAR-pattern, C1/C2 hybrids) have FLOPS margin worth converting.

Sources: [`handoffs/completed/cpu-decode-flops-roofline-audit.md`](../handoffs/completed/cpu-decode-flops-roofline-audit.md) · [`research/deep-dives/nemotron-labs-diffusion-tri-mode.md` §10](../research/deep-dives/nemotron-labs-diffusion-tri-mode.md) · `feedback_canonical_baseline_protocol` · `feedback_no_concurrent_inference` · `progress/2026-05/2026-05-28.md` §research-intake-batch §Phase-6/7.

## CPU15 / CPU20 active-surface correction (2026-05-28)

The handoff compaction pass corrected a recurring CPU-optimization ambiguity: completed CPU15 expert-parallelism infrastructure is not a production default. The active CPU15 handoff now treats EP as default-off infrastructure that requires CPU20-compliant canonical revalidation before any deployment claim is revived. Old frontdoor EP win/regression claims were softened across the CPU index, environment-flag inventory, NPS reboot runbook, MoE-Spec notes, and master-index history so future agents do not treat superseded measurements as current rollout instructions.

The practical rule for hardware work is unchanged but now easier to find: CPU20 protocol compliance and current bottleneck proof are prerequisites for reopening TP/EP/kernel levers. The completed ledgers remain useful evidence, but the active handoffs hold the current gates and revalidation checklist. Sources: [`large-moe-expert-parallelism.md`](../handoffs/active/large-moe-expert-parallelism.md), [`large-moe-expert-parallelism-completed-through-2026-05-28.md`](../handoffs/completed/large-moe-expert-parallelism-completed-through-2026-05-28.md), [`cpu-benchmark-rigor-and-revalidation.md`](../handoffs/completed/cpu-benchmark-rigor-and-revalidation.md), [`progress/2026-05/2026-05-28.md`](../progress/2026-05/2026-05-28.md).

## 2026-06-03 — Agentic ROCm kernel authoring on MI210 (GEAK family, intake-660–679)

The GPU path (previously "parked behind hardware acquisition") gained a concrete near-term program when an **AMD MI210 Instinct (CDNA2 / gfx90a, 64 GB, ~July 2026)** entered scope and the operator set a goal of **authoring custom HIP/Triton kernels** for the EPYC stack via a **train-free agentic verify→profile→refine loop** (we cannot retrain a kernel model on one MI210). A 20-entry research-intake sweep (intake-660–679) of the LLM-GPU-kernel-generation literature produced the synthesis below.

**The pivotal finding — AMD already built the substrate, on our ISA.** The NVIDIA/Intel cluster (CUDA Agent, CUDA-L1, Kevin, KernelBench, EvoEngineer, KernelFoundry, K-Search, …) is methodology-transfer only. But AMD's own tools are AMD-native and largely reusable: **GEAK** (intake-674, MIT — train-free Triton agent + two open benchmarks) is **demonstrated on MI250X = gfx90a, the MI210's exact ISA family**; **Apex** (intake-675, MIT — profile→optimize→hot-patch→re-bench harness + Magpie scorer) is gfx90a-listed; **AgentKernelArena** (intake-679, Apache-2.0, arXiv 2605.16819 — a controller-A/B arena with Claude Code/Codex/Cursor/GEAK adapters over HIP/Triton/Torch2HIP) is the agent-comparison harness we'd otherwise build. This collapses the planned from-scratch ROCm backend into **adopt + reproduce**, leaving two net-new pieces we own: **C6 anti-reward-hacking** (robust-kbench intake-668 exploit classes + AgentKernelArena's unseen-shape generalization protocol) and **C4 gfx90a profiler-metric** (GEAK-v2 intake-677 raw-`rocprof-compute`→LLM, the cheapest path; Xe-Forge intake-672 static constraint-KB; CudaForge intake-662 formal selection).

**Hardware-eval lessons (reusable beyond this program):**
- **Same `gfx90a` predicts compile compatibility, not performance equivalence.** GEAK-v1's MI250X kernels/harness should build+run on the MI210 (identical wavefront=64/MFMA/LDS), but single-GCD bandwidth (~half MI250X aggregate), ROCm version, autotune space, and harness details require reproduction. GEAK-v2 / GEAK-HIP / AgentKernelArena are **gfx942/CDNA3-only** — a coverage regression vs GEAK-v1, the only gfx90a-proven reference.
- **Speedup-reward kernel agents are acutely game-able.** Documented across the literature: CUDA-L1's 32.8% stream-timing exploit; the AI CUDA Engineer 150×→~3×-*slowdown* scandal that birthed robust-kbench (which re-scored prior work 3.13×→1.49× after removing 40 gameable tasks); AgentKernelArena's own Torch2HIP correctness collapse to 59.7% on unseen shapes (shape-hardcoding). Any speedup-reward harness needs an anti-hacking layer (exploit-class defenses + unseen-shape checks + red-team) designed in from day one.
- **Isolated-op scores overstate real gains ~25pp** (FastKernels intake-671) — gate rewards on an honest vendor baseline (rocBLAS/hipBLASLt/AITER) and a whole-model exit gate, not torch-eager.
- **Build-tool LLM policy:** `opensource_only` governs deployed services, not build-time tooling — the authored kernel is the artifact, so a Claude+Codex actor-critic (reusing the autopilot planner infra) is the favored agent backend, empirically corroborated by AgentKernelArena's best results (Claude Code / Cursor / Codex) and CudaForge's cross-model coder/judge win.

**Standing caveat:** all AMD numbers (intake-674–679) are vendor-reported (AMD authors agent + benchmark + hardware) with no third-party reproduction; treat as provisional until reproduced on our own gfx90a. The first action when the card racks is reproducing GEAK-eval's MI250X numbers on the MI210.

Sources: [`research/deep-dives/agentic-rocm-kernel-authoring-geak-synthesis.md`](../research/deep-dives/agentic-rocm-kernel-authoring-geak-synthesis.md) (full reasoning + freshness appendix with GEAK repo pins) · [`handoffs/active/agentic-rocm-kernel-authoring.md`](../handoffs/active/agentic-rocm-kernel-authoring.md) · [`handoffs/active/rocm-verify-profile-backend.md`](../handoffs/active/rocm-verify-profile-backend.md) · `research/intake_index.yaml` intake-660–679 · master-handoff-index queue #62 · `progress/2026-06/2026-06-03.md`.

## 2026-07-11 — MI210 HIP graph capture for inference decode (first empirical benefits)

First end-to-end measurement of **HIP graph capture** (`GGML_HIP_GRAPHS=ON` → `USE_CUDA_GRAPH`) on the MI210 for *inference decode* (distinct from the GEAK kernel-authoring program above). Runtime toggle: `GGML_CUDA_DISABLE_GRAPHS=1` = direct dispatch. Arch gate `cc < GGML_CUDA_CC_AMPERE(800)` cannot trip on AMD (`cc` is offset by `0x1000000`, so MI210 CDNA2 = `0x100090a`); `MUL_MAT_ID` (MoE) does **not** disable graphs for quantized single-token decode (`mmvq_mmid_max=8`, `ne[2]=1`). All numbers observation-grade (MEASUREMENT.md), `build-hip` @ `46f876c12`, ROCm 6.2, Q8.

**Graph capture works and is net-positive — magnitude splits by what is accelerated:**
- **Base decode: helps every model** — gemma-4-26B-A4B MoE +4.3%, dense gemma-4-31B +6.1%, Qwen3.6-27B dense-hybrid +7.2%, Qwen3.6-35B-A3B MoE +13.9%. Benefit ≈ launch-overhead ÷ per-token time (fast/MoE > slow/dense).
- **Spec-dec: the big win is drafter-architecture-specific, NOT universal.** gemma4's **external assistant-head** MTP drafter → **+25%** (a separate tiny-model decode per draft step → launch overhead dominates → graphs amortize hugely). Qwen **native NEXTN-MTP** heads → only **+1.8–2.5%** (draft folded into the main forward → little separable launch overhead). So "graphs give +25% on spec-dec" is a gemma4-external-head property.

**Levers beyond default-ON (all evaluated, none landed):** `GGML_CUDA_GRAPH_OPT=1` (fan-out/stream-reorder pass) is **net-negative** (Q8 base −16%, spec −11%) → rejected. A **shape-aware graph cache key** (Lever A; the pointer-only `nodes[0]` key is shape-blind so draft/verify batch shapes may collide → warmup thrash) was implemented env-gated but measured **NEUTRAL** on Q8 (−2%, byte-identical output → correctness-safe, no speedup); reverted, preserved as `llama.cpp-experimental/lever-a-shape-key.patch`. The **onegraph single-graph fold** (fuse the N draft decodes into one replayable graph) is **DEFERRED** — the K2 Q4 regression is verify-side, not the draft loop (already shape-stable), so onegraph attacks a non-bottleneck; a draft-depth sweep confirmed no headroom (n_max 2≈4). The fork's **`GGML_CUDA_Q8_PREFETCH`** (CDNA2 dense-Q8_0-GEMV async weight-prefetch, `mmvq.cu:502`, byte-identical) is also **net-negative** across all 4 Q8 models (dense hurt most: Qwen-27B −12/−18%, gemma4-31B −6/−7.5%; MoE marginal/noisy) → keep off. Net: **default graphs-ON is the win; no additional decode lever (GRAPH_OPT, shape-key, Q8_PREFETCH) produced a clear validated gain.**

**Two reusable methodology lessons:**
- **gemma4 external-head MTP spec-dec is intermittently non-deterministic under host CPU load** (temp0/seed42 run-to-run output drift — a load-sensitive async-D2H-copy race); Qwen native-MTP is unaffected. So spec-dec A/B on the MI210 must run **quiesced + strictly sequential + fresh-server-per-run** (multi-request-per-server also drifts). Determinism held at load ~77, broke at ~100+.
- The MI210 GPU can be idle while the **host CPU** is the confound — the MTP draft loop's per-step token/h_row round-trip runs on the CPU, so production CPU load depresses/scatters spec-dec throughput even with the model fully on the GPU.

Sources: [`handoffs/active/gemma-challenge-kernel-techniques-v7.md`](../handoffs/active/gemma-challenge-kernel-techniques-v7.md) (K2 empirical tables + Kernel-Optimization Levers + Non-gemma4 generalization) · [`handoffs/active/speculative-decoding-mtp-refresh.md`](../handoffs/active/speculative-decoding-mtp-refresh.md) · [`progress/2026-07/2026-07-11.md`](../progress/2026-07/2026-07-11.md) · `project_mi210_hip_graph_capture` (memory) · `feedback_pair_speed_with_correctness_check` · `feedback_verify_test_method_before_calling_it_a_bug`.

## 2026-07-17 — Large cross-run CPU-decode "regressions" were transient host state, not source (K34/K24)

A v7-promotion guardrail chased apparent v7 CPU non-spec base-decode regressions (architect `-9.24%`, frontdoor `-6.55%`) and root-caused them to **host/runtime state, not a kernel-source regression** — a recurring trap when A/B benches straddle different host conditions.

- **The big deltas were repeatability noise, and current production itself had drifted far below its own prior guard cells.** A quiet, *paired* production-vs-current-v7 CPU rerun measured frontdoor `8.58 → 8.35 t/s` (−2.6%), architect `3.65 → 3.54` (−3.0%), ingest `9.80 → 9.90` (+1.0%) — but the same run showed *production* far below the 2026-07-16 production guard cells (architect old `5.85` vs now `3.65`; ingest old `13.89` vs `9.80`), so the headline "regression" was host-state drift affecting **both** arms, not a v7 source change. A HIP-enabled v7 build compared against a CPU-only production binary was itself a confound (a fresh CPU-only experimental artifact `build-k24-cpu` was needed to separate it). Under clean default placement the same cells recovered **+100–159%**, and v7 landed within ±4% of production. The source bisect against the two suspect commits (`3c2696b88` bf16 GDN recurrent-state, `90e0f5cfc` fused-op) was retired once the paired run falsified the premise. Sources: [gemma-challenge-kernel-techniques-v7.md](../handoffs/active/gemma-challenge-kernel-techniques-v7.md) (K24/K34), [progress 2026-07-17](../progress/2026-07/2026-07-17.md).
- **`--numa distribute` is not a universal remedy, and clean-run preflight is now the discipline.** The recovery came from default placement, not `--numa distribute`, which was mixed/noisy and actively hurt ingest (prod −8.05%, v7 −4.68%). Governor/EPP were already `performance` with boost on and auto-NUMA-balancing off, so the drift is page-cache/NUMA-imbalance/background-agent state, not config. A `cpu_bench_clean_preflight.py` records blockers, `numactl --hardware`, governor/EPP/boost/THP/NUMA-balancing, pinned `LD_LIBRARY_PATH`, and a sentinel decode (recovered reference `20.57 t/s`, retry threshold `18.0`) with an explicit "retry before source blame" rule. The generalizable lesson: **a CPU A/B must pair both arms in one quiet window against a live sentinel; cross-day/cross-host t/s deltas are host-state observations, never kernel evidence** (and they poison AutoPilot speed telemetry if trusted). Sources: [gemma-challenge-kernel-techniques-v7.md](../handoffs/active/gemma-challenge-kernel-techniques-v7.md) (K34.1/K34.2), [progress 2026-07-17](../progress/2026-07/2026-07-17.md).

### New (2026-07-21, iqk acceleration silently skipped every IQ-quant model)

> **Review flag (project-wiki writer-evidence policy):** model-compiled, not adopted until human or measured review. The change is committed but **unbuilt and unvalidated**.

- **A runtime acceleration flag can be enabled and still be inert, because kernel dispatch is per data type.** `GGML_IQK=1` swaps in ik_llama's AVX-512 GEMM kernels (measured +7.9-8.8% decode on Q4_K, +22-49% prefill on other families), but dispatch runs through a per-quant-type whitelist, `iqk_typeA_supported` in `ggml/src/ggml-cpu/iqk/iqk_dispatch.cpp`. That whitelist contained only K-quants and legacy quants, and `iqk_set_kernels_iquants` / `iqk_convert_iquants_q80_r8` were linker stubs returning `false`. On an IQ-quant model the flag therefore accelerated the attention and shared-expert tensors and fell back to the stock kernel for the parameter bulk — with no error, no warning and no log line. Sources: [iqk-iquant-enablement.md](../handoffs/active/iqk-iquant-enablement.md), [tq3-quantization-evaluation.md](../handoffs/active/tq3-quantization-evaluation.md), [iqk-port.md](../handoffs/completed/iqk-port.md).

- **The blast radius was four deployed models, and the largest beneficiary was not the obvious one.** Tensor counts parsed from GGUF headers: GLM-5.2 UD-IQ2_M **221** (148 IQ2_XXS + 71 IQ3_XXS + 2 IQ2_S), Qwen3.5-122B UD-IQ2_M **143**, **Qwen3-Next-80B i1-IQ2_M 433 — 54% of all 807 tensors**, Hy3-IQ1_M-mtp **157**. In every case these are the MoE routed experts (`ffn_gate_exps`/`ffn_up_exps`/`ffn_down_exps`), i.e. the parameter bulk and the dominant term in both decode bandwidth and prefill FLOPs. Reading the kernel's actual `switch` also showed it implements **five** native types (IQ2_XXS, IQ2_XS, IQ2_S, IQ3_XXS, IQ3_S), not the three initially assumed — whitelisting three would have silently missed Qwen3-Next's 19 IQ3_S tensors. Sources: [iqk-iquant-enablement.md](../handoffs/active/iqk-iquant-enablement.md), [cpu-inference-optimization-index.md](../handoffs/active/cpu-inference-optimization-index.md), [progress 2026-07-21](../progress/2026-07/2026-07-21.md).

- **The stale-assumption pattern is the durable lesson: a conditional stub with a written expiry that nobody re-checked.** `iqk_stubs.cpp:8-12` states plainly — *"The registry shows ZERO use of IQ-quants … If/when we adopt IQ-quants (e.g. future GLM IQ2), these MUST be replaced with the real ik kernels — do not leave them stubbed for a quant we deploy."* That was accurate when written; four IQ-quant models were subsequently added and the condition was never revisited. The generalizable guard is that a type/capability whitelist gated on "what the registry currently contains" needs an automated check against the live registry, not a comment. Sources: [iqk-iquant-enablement.md](../handoffs/active/iqk-iquant-enablement.md), [iqk-port.md](../handoffs/completed/iqk-port.md), [tq3-quantization-evaluation.md](../handoffs/active/tq3-quantization-evaluation.md).

- **What was folded from ik_llama at v6/v7 was the GEMM kernel subsystem, not the format plumbing — and the distinction decides where trellis can be evaluated.** Verified at `production-consolidated-v7 @ 6ad45fa3f`: zero references to `IQ2_KT`/`IQ4_KT` in our `ggml.h` enum, zero rows in the `ggml.c` `type_traits` table, and no KT option in `llama-quantize`. Our binary can therefore neither **produce** nor **load** a KT GGUF (the types are synthetic casts at 153-158 against `GGML_TYPE_COUNT = 43`), while `ik_llama.cpp` can do both. That is why a KT evaluation must currently run in that tree as a measurement instrument — which does not reopen its deprecation as a *serving* path. Sources: [iqk-iquant-enablement.md](../handoffs/active/iqk-iquant-enablement.md), [tq3-quantization-evaluation.md](../handoffs/active/tq3-quantization-evaluation.md), [v7-promotion.md](../handoffs/active/v7-promotion.md).

## Compiled Update — 2026-08-09 (what a production engine's chunked-GDN recurrence actually looks like; and the profiler-capture mode our tooling survives is the one that yields attribution)

> **Review flag (project-wiki writer-evidence policy):** model-compiled from dive-verified intake entries read against upstream source on 2026-08-09. Nothing here has been compiled or run on gfx90a; treat every portability statement as a hypothesis with a named test.

### The SOTA target is four autotuned stages, not one fused megakernel

- **A production serving engine expresses the chunked Gated-DeltaNet recurrence as four *separately-autotuned Triton stages* behind one autograd wrapper, not as a single hand-fused kernel.** Verified in `sgl-project/sglang` at `main`: `chunk_local_cumsum` (`fla/cumsum.py`) → `recompute_w_u_fwd` (`fla/wy_fast.py`, the WY/UT transform) → `chunk_gated_delta_rule_fwd_h` (`fla/chunk_delta_h.py`) → `chunk_fwd_o` (`fla/chunk_o.py`), orchestrated by `chunk_gated_delta_rule_fwd` / `ChunkGatedDeltaRuleFunction` in `fla/chunk.py`. This design is retained as reference material; K28 itself later closed no-go on the measured whole-model ceiling. Sources: [k28-fused-chunked-gdn-kernel-research.md](../handoffs/completed/k28-fused-chunked-gdn-kernel-research.md), [mi210-big-model-and-acceleration-roadmap.md](../handoffs/active/mi210-big-model-and-acceleration-roadmap.md), intake-1030/intake-1025 in [research/intake_index.yaml](../research/intake_index.yaml).

- **All four stage files are pure Triton with autotune and carry no `is_cuda` guard or device-capability check** — a necessary portability condition, not performance evidence. AutoKernel's GEAK/Arena round-trip has since proven Triton 3.1.0 compile/correctness/timing on physical gfx90a, but the K28-specific FLA probe was retired when direct whole-model attribution failed the parent gate. Sources: [k28-fused-chunked-gdn-kernel-research.md](../handoffs/completed/k28-fused-chunked-gdn-kernel-research.md), [rocm-verify-profile-backend.md](../handoffs/active/rocm-verify-profile-backend.md), intake-1030.

### Two-phase capture: the mode our profiler survives is the mode that gives attribution

- **CUDA graphs and kernel fusion destroy `kernel → cpu_op → source` attribution, so a single optimized trace tells you what is slow but not what produced it.** The upstream discipline is a *two-trace* protocol: a mapping trace captured with graphs disabled or lower fusion, then a formal trace with the real optimizations on. **The convergence worth recording is accidental and useful**: our own tooling audit independently found that `rocprof` v1 *aborts at init on graph-enabled builds*. The capture mode our profiler can survive is therefore the same one that yields source attribution — which turns a recorded tooling limitation into a two-phase protocol rather than a blocker. Sources: [rocm-verify-profile-backend.md](../handoffs/active/rocm-verify-profile-backend.md), intake-1026, intake-1025.

- **A profiler-triage report layer can be separated from its trace parser, which is what makes a ROCm port cheap.** In the reference implementation the renderers take `rows: Sequence[dict]` with parsing delegated to sibling modules, so adopting the report contract (kernel / overlap-opportunity / fuse-pattern tables, rows at or above a 1.0% cumulative GPU-time share, source-backed matching explicitly *not* fuzzy, and a bounded `high`/`medium`/`low` confidence vocabulary) requires building only a `rocprofv2` row adapter. This also **de-risks by subtraction**: confining the model to a similarity note and a catalog comparison, rather than reading raw counters, shrinks the trusted surface of the highest-risk item in the profiler-backend plan. Sources: [rocm-verify-profile-backend.md](../handoffs/active/rocm-verify-profile-backend.md), [autokernel-research-loop.md](../handoffs/active/autokernel-research-loop.md), intake-1026.

- **A kernel-time-share table is structurally blind to an entire class of bottleneck.** The reference catalog excludes "host-only scheduler, event-loop, executor, offload, and load-path patterns" *by written policy*, so a host/device transfer cost has no row and cannot surface. Any analogue we build must widen that scope deliberately or pair it with a host-side catalog. Sources: [rocm-verify-profile-backend.md](../handoffs/active/rocm-verify-profile-backend.md), intake-1029, intake-1027 (`stage1-unverified` — no figure from it may be cited).

## Compiled Update — 2026-08-10: the gfx90a kernel-agent program re-aimed, and a claim compiled here retired

> Freshness sweep of the agentic-kernel-authoring program (the sweep this handoff mandates at every
> audit). Amends the 2026-06-03 section above; band figures are sizing estimates with stated
> confidence, not measurements.

- **RETRACTION of a claim compiled above.** The 2026-06-03 section records *"GEAK-v2 / GEAK-HIP /
  AgentKernelArena are gfx942/CDNA3-only — a coverage regression vs GEAK-v1."* For GEAK proper that is
  **unpublished coverage, not removed coverage**, and the difference decides whether the vendor's tree
  is usable on our card. Verified in the v4 tree: `perf_knowledge/hardware/cdna2_mi200/` ships four
  files (`arch`, `matrix_core`, `memory`, `occupancy`), all `gens: [gfx90a]`, all updated 2026-06-08,
  titled for MI250X/MI210 — our exact card, named; the capability index carries **40 gfx90a entries**
  (against 214 gfx942 / 225 gfx950 / 20 gfx908); and there is no arch gating or allowlist, the card is
  auto-detected. The correct formulation to carry forward is: **GEAK v4 carries first-class gfx90a
  hardware knowledge and publishes zero gfx90a numbers.** Two caveats travel with it — pin `v1.0.0 @
  4ffba15a` for the paper's MI250X evidence (the v1 *release notes* name only MI300X; the gfx90a claim
  traces to the paper), and the vendor KB is not error-free: its ridge-point figure is off by 2× from
  confusing per-GCD with per-OAM. AMD's own consumption contract says the same thing we do — the KB is
  reference material, and consumers must "decide by on-box measurement."

- **The program was aimed at the wrong rung, and re-aiming doubled the prize.** Closing the measured
  quantized-dequant gap (~33% Q4_K / ~47% Q8 attainment) is half of what is available: the **fp16 rung
  at 62.6% attainment is demonstrated on our own device**, vLLM-ROCm reaches 69.2% on the same
  silicon, and a GB10 reaches 77–80% at Q4_K_M dense across five models on the same engine. The
  re-target is expressed as **bands with confidence, not point estimates**, so a campaign can be sized
  before it is run: K1 Q4_K→Q8 rung **+38–43% (HIGH)**; K5 batched elementwise/norm fusion **+20–27%
  (HIGH — 43% of B=128 time is non-GEMM while GEMM is only 37%)**; K2 Q4_K→fp16 +60–80% (MED); K3 MoE
  expert-gather ~2.0× (MED); K6 fp16 batch-1 +11% (HIGH); K7 HIP graphs +5.9% (banked); K8 LDS
  prefetch ~0 (CDNA2 ceiling); **K9 MFMA decode kernels 0 — DO NOT BUILD (certain, from arithmetic
  rather than counters)**; K10 prefill +20–30% (MED); K11 closing the vLLM gap is not a kernel program
  at all; K12 matching Blackwell prefill is unreachable behind a 5.6× int8 silicon deficit. A ceiling
  table that names two levers as *zero* is doing more work than one that ranks everything positive.

- **Prefill kernel quality is not the gap; prefill silicon is.** The MI210 converts 19–29% of matrix
  peak, against A100 22.8%, RTX PRO 6000 22–44%, H100 15.3% and MI300X 12.3% — mid-pack, not an AMD
  software problem. Attainment-vs-peers is the measurement that tells a kernel program where it cannot
  win.

- **A free compositional result: our frozen tile layout is already the state-of-the-art one.**
  HipKittens' `rt_base` fragment is **bit-identical** to `ggml/src/ggml-cuda/mma.cuh`'s `tile<16,16>`
  in production v8 (`get_i = tid%16`, `get_j = 4*(tid/16)+l`, `ne=4`), so every technique from that
  library composes onto our existing fragments with **zero layout re-derivation** — which is exactly
  why the right move is to harvest the lessons and *not* vendor the framework. A live gfx90a build arm
  already exists on its `cdna3` branch (`GPU_TARGET=CDNA2` → `--offload-arch=gfx90a`), and across 67
  headers exactly **one of six** `__builtin_amdgcn_*` intrinsics is unavailable on gfx90a (an fp8 MFMA
  builtin needing an `#if` guard), with a ~3000-test correctness harness that would run on our
  silicon. That makes declining the port an **economic** decision rather than a capability one — which
  is the only kind of decline worth recording.

- **Do not assume a CDNA3 microarchitectural constant transfers to CDNA2.** Whether gfx90a has 32 or
  64 LDS banks decides whether the reference swizzle constants transfer *at all*; a runnable bank/phase
  solver (a ~45-line kernel over rocprofv3 PMC counters, ~40 min of GPU) settles it on our own card
  instead of inheriting the answer.

- **The profiler blocker is closed, and how it was closed is the reusable part.** `rocprofv2`,
  `rocprof` and `rocm-bandwidth-test` are now available version-matched to ROCm 6.2.0-66, **side-loaded
  by extraction so nothing in the shared `/opt/rocm` bind mount changed** — the pattern for adding
  tooling to a shared host without mutating state other sessions depend on. The gfx90a counter taxonomy
  is proven on our own card: **465 counters across 12 blocks**, including every counter the program
  cites. `omniperf` is deliberately deferred as an off-critical-path fallback.

- **Two free operational levers, and one upgrade landmine to record before it bites.** From AMD's own
  ROCm llama.cpp work: hipBLASLt grouped-GEMM plus tuning (**+29%**) and ~10× fewer `hipMemcpyAsync`
  calls. Against that, llama.cpp issue #19984 reports an **LLVM loop-unroll regression in ROCm 7+
  costing 3.7–5× on prefill**, workaround `-mllvm --amdgpu-unroll-threshold-local=600`. It does not
  affect ROCm 6.2, which is precisely why it belongs on the build-flag checklist **now**, as a
  precondition of any ROCm upgrade rather than a discovery made during one.

- **New controller candidate worth an A/B slot**: ARGUS (arXiv 2604.18616) reports **99–104% of
  hand-optimised assembly on MI300X** for GEMM / FlashAttention / MoE, 2–1543× over prior agentic
  systems, 100% KernelBench L1 and 90% L2. CDNA3 evidence, so the numbers do not transfer — but the
  claim that *does* transfer is what an agentic loop achieves against a vendor's own hand-tuned
  assembly, which is the ceiling question the whole program is asking.

- **A three-way citation conflation, corrected.** The "seeded fuzzing catches 9/9 buggy kernels,
  passes 15/15 controls" finding attributed here to KernelBench belongs to a **separate seeded-fuzzing
  paper** (arXiv 2606.20128). The real KernelBench is Stanford's arXiv:2502.10517 (kernel *generation*,
  metric `fast_p`), and the third id in the tangle was never either paper. The correction had already
  been verified in a sibling handoff on 2026-07-22 and never propagated — a corrected claim only counts
  where the claim is read.

- **Adopt a benchmark's scoring protocol without adopting the benchmark.** RE-Bench is worth taking for
  its **protocol** — log-time scoring of behaviour-preserving optimization, 0 = starting state and
  1 = a strong reference solution, and time-budget curves (2h/8h/32h) rather than pass/fail — and is
  not worth standing up as-is: only 1 of 7 environments is a kernel task, it is Triton on H100, and
  porting it to gfx90a invalidates the published human and model anchors that are the entire reason to
  use it. The transferable asset of a benchmark is often its scoring rule, not its tasks.

### Source References

- [`handoffs/active/agentic-rocm-kernel-authoring.md`](../handoffs/active/agentic-rocm-kernel-authoring.md) — the amended GEAK scoping, the K1–K12 banded ceiling, and the 2026-08-03 index-backed leads
- [`handoffs/active/rocm-verify-profile-backend.md`](../handoffs/active/rocm-verify-profile-backend.md) — the side-loaded profiler toolchain, per-block collection limits and the counter taxonomy
- [`handoffs/active/mi210-mfma-compute-bound-paths.md`](../handoffs/active/mi210-mfma-compute-bound-paths.md) — the fragment-layout identity, the arch-independent HipKittens lessons and the vendor ridge-point error
- [`handoffs/active/mi210-q8-dequant-gemv-roofline.md`](../handoffs/active/mi210-q8-dequant-gemv-roofline.md) — the attainment ladder behind the fp16 re-target and its calibration caveat
- [`research/deep-dives/agentic-rocm-kernel-authoring-geak-synthesis.md`](../research/deep-dives/agentic-rocm-kernel-authoring-geak-synthesis.md) §9 — the freshness appendix this sweep executes
