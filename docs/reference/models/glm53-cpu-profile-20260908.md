# GLM-5.3-Flash CPU profile and high-value levers — 2026-09-08

The operator stopped throughput confirmation and requested profiling to identify
high-value prefill/decode improvements. These findings concern the local UD-Q4_K_XL
artifact on champion-descended experimental candidate `2346de909`; production
is unchanged. No new performance kernel was developed during this audit.

## Measured baseline

Plain target, 64 threads, champion environment, model-local libraries. `perf`
6.17.13 sampled user cycles at 99 Hz with DWARF call stacks; separate hardware
counter captures accompanied each phase. Model loading was outside both windows.

| Phase | Work | Profiled throughput | Cycle samples |
|---|---|---:|---:|
| Prefill | 2,029 prompt tokens, one sampled output | 113.324 prompt tokens/s | 111,300 |
| Decode | 128 output tokens after cached prompt | 6.574 output tokens/s | 122,626 |

Decode reused 2,025 cached tokens and refreshed four prompt tokens (316 ms),
then generated for 19.472 s. Thus the decode capture has approximately 1.6%
request-time prefill contamination; it is not a perfectly isolated decode graph.
The single prefill output token has a meaningless near-zero generation timer,
which is excluded from all decode claims.

Both captures report zero lost samples. Exactly 64 active threads were sampled;
workers account for 98.4% of samples. Counter enabled/running ratios are 100%,
with 63.930 and 63.966 average active CPUs. Unknown-DSO shares are 0.14% and
0.27%. These are sampled CPU-cycle shares, not critical-path wall-time shares.

| Self-cycle group | Prefill | Decode |
|---|---:|---:|
| Dense Q8 matrix math | 26.70% | 35.93% |
| MoE quantized math and associated conversions | 27.82% | 21.83% |
| OpenMP runtime | 22.33% | 29.21% |
| Activation conversion | 3.15% | 3.19% |
| Flash attention | 2.72% | 0.27% |
| Recurrent scan plus convolution | 2.06% | 0.20% |
| Indexer/top-k | 0.17% | 0.01% |

The dominant OpenMP offsets disassemble to PAUSE polling loops with futex
fallback. Stacks place them under graph execution, matmul and MoE dispatch.
This supports synchronization/spin attribution, but eliminating spin does not
necessarily shorten the critical path. DRAM traffic was not captured; cache
miss rates and IPC alone do not establish a memory-bandwidth bottleneck.

## Ranked candidate levers

### 1. Route dense Q8 work through the existing IQK implementation

`GGML_IQK=1` does not enable Q8: `iqk_dispatch.cpp` separately gates Q8 through
`GGML_IQK_Q8_0`, default off. The profiled fallback is `ggml_vec_dot_q8_0_q8_0`
for decode and tinyBLAS Q8 GEMM for prefill. This directly targets the largest
individual measured compute family in both phases. The full artifact has 645
Q8 tensors totaling 8.955 GiB, including 1.926 GiB attention-output projections,
3 × 1.129 GiB KDA Q/K/V projections, 0.628 GiB output head, and
3 × 0.357 GiB shared-expert up/gate/down projections. These are tensor-inventory
sizes, not per-family sampled attribution; the token-embedding lookup is not
streamed matrix math. The native single-row x86 Q8 dot implementation uses
YMM/AVX2; the tinyBLAS symbol name alone does not establish instruction width. The matched single profile with only `GGML_IQK_Q8_0=1` completed:
prefill rose from 113.324 to 153.692 prompt tokens/s (+35.6%); decode changed
from 6.574 to 6.627 output tokens/s (+0.8%). The prefill request/input and single
output token match, but the 128-token decode trajectories differ. This is a
high-value prefill candidate requiring repetition and quality validation, not
a demonstrated lossless decode improvement. It also shows that merely routing
decode through IQK does not solve its dominant Q8 cost.

For decode, optimize the identified single-token projection work and its
threading/packing cost, then validate numerics. An ISA rewrite cannot be
justified from the AVX2 label alone; measure whether arithmetic, data movement,
or synchronization limits that kernel.

### 2. Reduce graph synchronization and matmul/expert load imbalance

OpenMP accounts for roughly one quarter to one third of sampled cycles. Prefer
per-operation worker sizing, balanced expert/row partitions and reducing small
operation barriers over adding threads indiscriminately. The existing serial
MTP screens give 6.092 tokens/s at 64 threads versus 5.672 at 96 threads (n=1
each), despite the latter occupying every physical core. These are supporting
observations, not a complete thread optimum or a realized synchronization gain.
Instrument operation dimensions and per-thread completion skew to locate which
barriers are on the critical path before attempting fusion or scheduler changes.

### 3. Recover exact parallel MTP rather than paying serial verification cost

Fast MTP reaches 7.596 tokens/s at t48 but fails exact greedy parity. Existing
serial verification matches all five 512-token plain trajectories at 5.784
versus plain 6.366 tokens/s. A clean four-token target batch reproduces the
wrong argmax without prior rollback, so batch non-invariance is sufficient to
explain the failure. The compiled `GGML_ROWEXACT_N` control applies row-consistent
matmul/MMID arithmetic and is a bounded configuration experiment before new
kernel development. Both plain and MTP arms must use the same value: the control
can also affect small per-expert prefill groups. The N=16 paired 64-token experiment completed: parallel MTP and plain match
all 64 tokens, with observed rates 8.870 and 6.733 output tokens/s respectively
(n=1). Both differ from the original plain/serial baseline at generated index 6.
Thus the control changes target arithmetic; internal parity under a new
configuration is promising, but is not proof of original-reference fidelity or
general lossless MTP correctness. The next gate is longer/multiple-prompt exact
parity under identical configuration plus reference quality checks.

## Measured configuration experiments

| Experiment | Observed result | What it establishes |
|---|---|---|
| IQK Q8 enabled, same profiled 2K prefill | 113.324 → 153.692 prompt tokens/s | Promising prefill configuration lever; n=1 |
| IQK Q8 enabled, profiled decode128 | 6.574 → 6.627 output tokens/s | No material demonstrated decode gain; outputs differ |
| Rowexact16, plain vs parallel MTP,64 tokens | 6.733 vs 8.870 output tokens/s | Internal token parity under changed arithmetic only; n=1 |
| Serial MTP t64 vs t96,512 tokens | 6.092 vs 5.672 output tokens/s | More physical workers did not help this screen; n=1 |

Do not multiply these ratios or add sampled-cycle shares to forecast a combined
gain. They use different workloads, modes, and arithmetic configurations.

## Scope and evidence

The low attention/indexer shares apply to this approximately 2K-token context.
They do not dismiss long-context sparse-attention work. Snapshot elimination
in serial MTP is a secondary source hypothesis: the serial verifier never
decodes rejected tokens, yet reserves rollback planes. It is lower priority
than the measured dominant matrix/synchronization costs, pending a draft/target
profile proving its wall-time significance.

Raw baseline evidence:
`/mnt/raid0/llm/tmp/glm53-validation-20260908/artifact/run/evidence-profile-plain-t64-20260908T214608Z/`.
Source/compiled library identities, request windows, raw perf data, counter
records and server exit proof are retained there. Host uptime exceeds one week;
all performance values are observations, not canonical promotion evidence.

Q8-enabled evidence:
`/mnt/raid0/llm/tmp/glm53-validation-20260908/artifact/run/evidence-profile-plain-t64-iqkq8-20260908T215418Z/`.
Source anchors (experimental candidate): `ggml/src/ggml-cpu/iqk/iqk_dispatch.cpp`
(Q8 opt-in at lines58–64, dense gate239, MMID gate394),
`ggml/src/ggml-cpu/arch/x86/quants.c` (`ggml_vec_dot_q8_0_q8_0`),
`ggml/src/ggml-cpu/ggml-cpu.c` (`ggml_cpu_rowexact_n` and matrix dispatch),
and `src/models/glm5-next.cpp` (KDA, pooled attention, MoE and mHC graph).

Independent raw-evidence audit:
`/mnt/raid0/llm/tmp/glm53-validation-20260908/runtime/profile-analysis-20260908T214608Z/audit-summary.json`,
SHA256 `2da409d9d63df64af39262f5a5f9aecaec4c2ebcfedadfaab8e6498e5d2aaf18`.
It confirms identical profile requests/source/model/binary and the sole Q8-switch
environment delta. Q8 decode first diverges at token56 (1096→358); sampled Q8
cycle-period totals are effectively unchanged (1.8864e12→1.8866e12), consistent
with the negligible decode timing change. Prefill Q8 sampled period falls from
1.204e12 to0.543e12. These are sampled periods, not measured DRAM traffic.
