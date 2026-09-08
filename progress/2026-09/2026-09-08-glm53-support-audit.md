# GLM-5.3-Flash support audit — 2026-09-08

Completed the requested champion/source/GGUF and official upstream PR audit.
Found three open architecture PRs and one native-MTP companion. Recommended a pinned
#27773/#27917 adaptation on the consolidated champion, with native speculative decoding
a mandatory gate. Identified metadata-prefix/index-sharing differences, quantization concerns,
hybrid KDA/kpool/mHC integration, and rejection rollback requirements. No kernel edits,
builds or inference runs; no throughput or parity claim.

Evidence and implementation/validation plan:
[support audit](../../docs/reference/models/glm53-flash-support-audit-20260908.md).

## Authorized text/MTP implementation follow-up

The operator approved the pinned port, made vision optional, and requested
gpt-5.6-sol medium subagents. Three subagents prepared the kernel adaptation,
independent GGUF contract/fixtures, and executable validation harness while the
owning session reviewed and integrated their submissions.

The experimental candidate is
`/mnt/raid0/llm/llama.cpp-experimental-glm53-20260908`, branch
`experimental/glm53-text-mtp-20260908`, based on champion
`ef81196d5bdd4190b46dff4ae7eecc333a46c8ce`. Production remains untouched.
Source checkpoint: `7d1e80a31` (`WIP: port GLM5Next text and native MTP`),
31 files, 2,782 insertions and 49 deletions. The candidate worktree is clean.
The text/runtime port excludes conversion and vision. Review preserved the
champion's Qwen cache filters and aligned hybrid-cache restore, and added missing
pooled-index/MTP-selection invalidation on restore and sequence edits.

Seven independent Python artifact/schema tests passed, including checks of all
six local shards against 1,412 required loader tensor names/shapes and four tiny
deterministic fixtures covering both architecture spellings and absent/explicit
optional metadata. These checks establish the tensor/schema contract only; they
do not establish numerical correctness or working inference. The artifact
manifest uses header and sampled-data hashes, not full model-file hashes.
The portable subset is committed in `tests/glm53/`: four tests pass by default
with one opt-in skip, and all five pass with the real model and identity
manifest enabled. `test-glm5next-mtp-rollback.cpp` is registered as a CMake target
but has not been compiled; its source exercises forced target suffix removal and
full-checkpoint restore into a used target context via continuation logits and
greedy tokens. Native MTP dispatch/acceptance and used-MTP-context restoration
remain separate runtime gates. Static review also scoped tokenizer changes so
legacy GLM4 behavior remains as in the champion.

Follow-up candidate commit `ab08a12bf` preserves eight source-only serve/runtime
helpers under `tests/glm53/`. Six launch-plan tests pass; generated schema
self-checks exercise 12 rollback records and six full/chunked pool pairs.
Negative checks reject vacuous evidence, mismatched requests, truncated outputs
and misaligned pool members. These generated records test the validators, not
the model. Matched MTP/plain plans record a verified champion recipe source
digest and require explicit candidate paths and physical locks; neither plan
was executed. The native-MTP evidence contract requires completed verification
log events with accepted and rejected drafts, since aggregate unaccepted draft
counts can include unused terminal drafts. The used-MTP-context restore and
executable pool/chunked-prefill producers remain runtime-validation work.

At the initial source-only checkpoint, builds and inference had not run. A task-scoped operator question was raised:
authorize the existing physical CPU/GPU locks directly because this interactive
session has no roster identity and the live coordinator has no compute-request
handler; allow observation-only timings without rebooting the approximately
26-day-old host. The request is recorded at
`/mnt/raid0/llm/tmp/glm53-validation-20260908/compute-request.md`.
That extra approval gate was withdrawn when the operator challenged the stop;
the requested experimental build/test/run was already authorized. Physical
region locks still serialize all compilation and inference. No roster or compute
policy was changed, and no canonical/promotion claim is made on the unrebooted host.

## Resumed build and runtime validation

Candidate `2346de90942e29534053df434db89c4a2b110616` builds with GCC 15.2.0,
Release/native/OpenMP CPU settings, HIP off. `llama-server` reports
`10308 (2346de909)`; SHA-256
`03c5859a1044698faa0c2812624ce2d08968c1f3e896a6d1e843046d53779fc6`.
Candidate-local linked libraries and compiled champion environment controls were
verified. Stock server dependencies still compile/link `libmtmd`; no GLM vision
implementation was imported.

Runtime exposed and fixed a real loader compatibility gap: GLM's per-layer
metadata includes its NextN block, unlike the champion's trunk-only reads for
other MTP architectures. Test construction was also corrected to retain the
already-selected target token when rejecting all drafts, use the last requested
logits row, and disable rollback-tail reservation in the prefill-only tiny pool
test. These test errors were not patched into kernel behavior or hidden by a
looser tolerance.

All four alias/default-explicit fixture variants passed under physical locks:
48 forced draft-prefix rejection/replay cases (maximum absolute continuation
logit difference `7.45058e-8`), four actual used-MTP-context restores (exact
logits and selections), and 24 full/chunked pool-boundary cases (maximum
difference `2.9802322387695312e-8`). The fixed tolerance was `1e-5` throughout.
Existing Qwen35 architecture and recurrent-rollback checks also passed.
Evidence: `/mnt/raid0/llm/tmp/glm53-validation-20260908/initial-tests/run-20260908T203012`.

The full six-shard native-MTP smoke completed: 32 output tokens at 10.5371
output tokens/s; 21/28 draft tokens accepted. A trace-enabled smoke produced
10 completed verification events, including 1/3 and 3/3 acceptance, so actual
rejection is witnessed rather than inferred from aggregate unused drafts.
Both owned server PIDs exited cleanly. These short raw-completion runs are
preliminary observations, not the sustained comparison.

After a second premature response left the longer comparison pending, the
operator pointed out the idle CPU. The paired full benchmark started at
2026-09-08T20:55:44Z under a physical CPU-region lock: five 512-token completions
per arm, matched greedy requests, model-provided chat formatting, and native
verification tracing. Results remain pending while the run executes.
Evidence root: `/mnt/raid0/llm/tmp/glm53-validation-20260908/artifact/run/`.
The wrapper preserves source/binary/library/instrument identity, bounded model
identity, exact recipe, in-window CPU samples, and owned-PID shutdown.


The first full MTP arm completed at t48: five 512-token output rates
7.57763, 7.58766, 7.59592, 7.63553, 7.59901 tokens/s; median 7.59592,
MAD 0.008261. All five output token arrays match exactly. Completed native
verification events include accepted and rejected drafts. MTP-off is running
next; t64 and t96 MTP scaling measurements are authorized by the operator's
follow-up about CPU utilization. The baseline uses 48 of 192 logical CPUs
(96 physical cores), so roughly 25% logical utilization is expected.

The saved `/apply-template` prompt actually enables `Reasoning Effort: Max`
and ends with `<think>` despite the server `--reasoning off` flag. Treat the
saved prompt as authoritative; both arms include reasoning tokens. Requests
force 512 tokens with `ignore_eos=true`, so they test a fixed-length trajectory,
not natural stop behavior. A briefly started GitNexus refresh was interrupted
with its own exec session during warmup; contention records are retained.


Matched t48 plain completed: 6.35585, 6.37764, 6.35307, 6.38704,
6.36609 output tokens/s; median 6.36609, MAD 0.011553. All owned PIDs
exited. The paired semantic gate FAILED: fast MTP differs from plain at
zero-based generated token 6 despite identical requests and internally
repeatable MTP output. Thus 7.59592 versus 6.36609 is a throughput observation
of different trajectories, not a validated lossless speedup. The auditor
reopened raw responses/log references rather than trusting sidecar flags.

Existing champion control `LLAMA_SPEC_EXACT=serial` was then tested, without
kernel edits: all first 64 tokens match plain exactly; 43/59 drafts accepted,
with actual completed acceptance and rejection events; 5.80489 output tokens/s.
This narrows the issue to the combined batched-verification/rejected-state path,
not independently to batching or rollback. Full t48 serial and t64/t96 scaling
are proceeding. Fast mode stays correctness-failed until the source-directed
batch/rollback discriminator resolves it.


Serial t48 full reps 1–4 each match the corresponding plain response exactly
for all 512 token IDs. Rates: 5.78376, 5.79336, 5.78594, 5.77524 output
tokens/s. The fifth is running. Additional thread scaling will use t64/t96
one-by-512 screening after stable warmups; only a materially faster winner
needs confirmation to five repetitions. This avoids treating logical CPU
utilization as the optimization objective; accepted output tokens/s remains
higher-is-better.


Full serial t48 finished: median 5.783764, MAD 0.008529 output tokens/s.
Independent raw-evidence audit verifies exact parity for all five 512-token
outputs, measured native draft acceptance 1615/2809, and 609 completed
verification events with a rejection. Result:
`runtime/reports/serial-plain-full-audit.json` under the evidence root.

The real target-only discriminator reproduced the fast-mode wrong argmax
from a clean sequential prefix followed by a four-token target batch, with no
prior rollback: 13931 versus plain 1246, max logit difference 0.1989278793.
Batch non-invariance suffices to explain the mismatch; this experiment does
not isolate an extra rollback defect. Executed source SHA256
`4ebb20360fefaf1ee3bb2ab1ba936735dbfa97c357362fc1245c8fffceecc500`.

Physical-thread screens (stable 64-token warmups then one 512-token request)
completed with exact token parity: t64 6.09226 output tokens/s; t96 5.67190.
The initial t48 setting feeds target and draft generation and batch threads;
96 threads uses all physical cores within taskset 0-95. More logical CPU
utilization did not imply higher throughput. Four additional t64 repetitions
and a matched-thread plain screen are running to complete the comparison.


Operator stopped the t64 confirmation and redirected effort to profiling and
high-value prefill/decode levers. Main sent SIGTERM to owned server PID2757765;
server and wrapper2757737 were confirmed absent with `ps`. Queued plain t64
screen is canceled. Partial confirmation evidence remains interrupted, not a
completed five-repetition result. The completed t64/t96 screens remain n=1.
Profiling and source audit are the active objective; no new performance-kernel
implementation is requested.


## High-value CPU profiling completed

Installed distro linux-perf6.17.13 after no-sudo user-space counter/sampling
preflight passed. Profiled plain t64 on candidate2346 with2029-token prefill
and128-token decode after2025-token cache reuse (four-token refresh adds316ms).
Both profiles have zero lost samples,64 sampled compute threads, and100%
counter running ratios. No model-load samples are included. Raw evidence:
`artifact/run/evidence-profile-plain-t64-20260908T214608Z` under the evidence root.
Dense Q8 math accounts for26.70% prefill/35.93% decode self cycles; OpenMP
22.33%/29.21%; MoE math/conversions27.82%/21.83%. OpenMP hot offsets are PAUSE
polling loops. CPU-cycle proportions are not wall-time improvement ceilings.

The targeted existing-switch experiment `GGML_IQK_Q8_0=1` improved profiled
prefill113.324→153.692 tokens/s (+35.6%) while decode6.574→6.627 was nearly
unchanged. Decode outputs differ at index56, so this is not a drop-in lossless
speedup. Q8 remains approximately36% of decode self cycles under the alternate
kernel. Evidence: `artifact/run/evidence-profile-plain-t64-iqkq8-20260908T215418Z`.

A separate bounded `GGML_ROWEXACT_N=16` experiment matches plain and parallel
MTP for64 tokens within the new configuration (6.733 vs8.870 tokens/s, n=1),
but both diverge from the original plain reference at index6. This is a promising
configuration hypothesis requiring reference-quality and longer parity tests,
not closure of normal parallel MTP correctness. No further benchmark is queued.

Ranked findings, evidence, source anchors and limits:
[GLM CPU profile](../../docs/reference/models/glm53-cpu-profile-20260908.md).
High-value work: validate IQK-Q8 prefill; improve dominant Q8 projection decode
and synchronization; establish reference-correct parallelMTP. Attention/indexer
micro-optimization has low measured share at this context length. Production
and performance-kernel sources were not modified by the profiling work.


Durable experimental helper/test commit:
`f25c89d52783e927958e879548c27d802f322e6f`. Candidate tree is clean.
This is source-only instrument preservation; the compiled measured server
remains `2346de909` with SHA256
`03c5859a1044698faa0c2812624ce2d08968c1f3e896a6d1e843046d53779fc6`.
Runner4/4, serve-plan6/6, portable artifact4+one opt-in skip, Python compile
and diff checks pass. Root index freshness/coverage check passes; GitNexus
refresh completed after profiling. Profiling server PIDs2787676 and2799034
exited cleanly. No profile/benchmark process remains scheduled by this session.
