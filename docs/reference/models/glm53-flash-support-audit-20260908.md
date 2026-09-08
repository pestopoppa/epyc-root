# GLM-5.3-Flash support audit — 2026-09-08

## Verdict and scope

The existing champion cannot load the local model, but upstream contributors have implemented
support. Recommend adapting a pinned version of **PR #27773 plus its native-MTP companion
#27917** into an experimental candidate descended from the current consolidated champion.
This is a provisional integration recommendation based on source inspection, not a validated
build or a performance prediction. **Native speculative decoding is a required completion gate**
(operator, this audit); trunk-only generation is an intermediate test.

No kernel, model artifact, production configuration, or running inference process was modified.
No inference, compilation, numerical parity test, or speed measurement was performed.

## Identities and upstream search

Local champion: `ef81196d5bdd4190b46dff4ae7eecc333a46c8ce`, build 10301,
`/mnt/raid0/llm/tmp/build-fold-ef81196d5/bin`; actual build source
`/mnt/raid0/llm/tmp/fold-ef81196d5-src`. The `champ2` checkout has the same tip.
Compiled libllama postdates that commit; both source registry and binary lack `glm5next`.

Official `ggml-org/llama.cpp` master inspected at
`f3f1a8f2760f28325a5ec20c05b171e5b7c83a29` has no GLM5Next registration.
GitHub API metadata, complete model sources, and relevant diffs were inspected, not just search results.

| Upstream PR | State on inspection | Pinned head | Assessment |
|---|---|---|---|
| [#27752, eauchs](https://github.com/ggml-org/llama.cpp/pull/27752) | Open, unmerged | `1d0c76f3c6d030fdfc269aa27db6334ea2834cec` | Text + native MTP; matches `glm5next`. Reports missing reference numerical validation, no MTP index sharing, and batch-dependent greedy output. |
| [#27754, Unsloth](https://github.com/ggml-org/llama.cpp/pull/27754) | Open, unmerged | `b9b8207fcfc2962093b9466df7af4ff29c2a81ef` | Text/vision + native MTP; matches disk naming. Documents `-fa off` correctness requirement; therefore cannot inherit the champion's FA-on recipe unchanged. |
| [#27773, timkhronos](https://github.com/ggml-org/llama.cpp/pull/27773) | Open, unmerged | `8134115f88ed8018474e7db69afcfe97fb097fc4` | Text/vision; uses `glm5-next`. Base graph explicitly rejects NextN. Author reports small-model reference-logit comparisons, not our validation. |
| [#27917, timkhronos](https://github.com/ggml-org/llama.cpp/pull/27917) | Open **draft**, unmerged | `5b8593b5451ec45fd4a81fb844efb6be9b45fd36` | Native NextN, draft-chain index reuse and rollback support; builds on #27773. Required alongside that trunk implementation. |

These PRs are alternatives/related stacks, not four patches to combine indiscriminately.
The MTP head contains overlapping base changes: reconcile the two pinned heads before porting.
Do not assume the latest trunk and draft snapshots apply cleanly to each other or to the champion.

## Local model and architecture gap

Six UD-Q4_K_XL shards at
`/mnt/raid0/llm/models/unsloth/GLM-5.3-Flash-GGUF/UD-Q4_K_XL/`,
199,707,321,347 bytes total. Actual headers describe 45 trunk blocks plus one NextN block:

* 34 KDA recurrent blocks; 11 MLA/DSA blocks at 3,7,11,15,19,23,27,31,35,39,43.
* KDA: 64 heads, dimension128, convolution width4, gate lower bound−5.
* MLA: hidden4096, query rank1536, KV rank512, **zero RoPE dimensions**.
* Four mHC streams, 20 Sinkhorn iterations; three initial dense FFNs, then 288 routed
  experts/top8 plus one shared expert. NextN is block45, an MLA/DSA block.

The [official model configuration](https://huggingface.co/zai-org/GLM-5.3-Flash/blob/main/config.json)
agrees on this hybrid layout and enables `index_share_for_mtp_iteration=true`,
`index_kpool=4`, `index_topk=2048`, and incomplete-tail selection.

Existing GLM-DSA is not an alias candidate: its trunk uses DeepSeek32's per-layer MLA/indexer
graph (`src/models/models.h:1243`, `src/models/deepseek32.cpp`). Block0 of this model instead
requires KDA and mHC. Renaming its architecture to `glm-dsa` cannot implement those operations.

## Reuse and necessary changes

The champion already has Kimi-linear, delta-net, DeepSeek4 mHC operations and hybrid indexed
memory. CPU GDN supports vector gates and multiple snapshot slots
(`ggml/src/ggml-cpu/ops.cpp:11119`). Existing CPU operations therefore appear sufficient for
a correctness-first port; new optimized assembly or a kernel search is not a prerequisite.

Required integration touches architecture/schema registration, model construction, hparams,
tensor loading, model graph, hybrid index-cache lifecycle, and speculative context plumbing.
Relevant local files: `src/llama-arch.{h,cpp}`, `src/llama-model.{h,cpp}`,
`src/llama-hparams.h`, `src/models/models.h`, `src/llama-memory-hybrid-idx.{h,cpp}`,
`src/llama-context.cpp`, and `common/speculative.cpp`.

Upstream helper organization differs: the champion lacks the PR's templated DeepSeek4 graph
base and stream-mean helper. Adapt helper access without replacing the champion wholesale.
Kpool also changes memory lifecycle: the current PR stores raw keys, learned gates and pooled
keys, with membership/masks and cache invalidation. It selects 512 complete four-token pools
and adds the incomplete tail, potentially 2051 tokens. A legacy token-level top-k adjustment
does not implement this. See the [pinned graph](https://github.com/timkhronos/llama.cpp/blob/8134115f88ed8018474e7db69afcfe97fb097fc4/src/models/glm5-next.cpp).

## Disk-format and quantization audit

The local architecture and metadata prefixes are `glm5next`; the recommended PR stack uses
`glm5-next`. Provide explicit, tested compatibility for both the architecture value and key
prefixes, or create a separately named converted artifact. Do not overwrite the six source shards.
Compressor tensor names already match the inspected PR head. Required architecture-specific keys
and representative tensor dimensions match after prefix normalization.

Local optional metadata lacks the index-sharing flag: the inspected loader defaults it to false,
whereas official configuration says true. An alias alone leaves this semantic mismatch.

The on-disk model stores several mHC mixers, indexer projections/gates, KDA gate projections and
MLA low-rank projections in Q8_0, while the PR's
[quantizer protections](https://github.com/timkhronos/llama.cpp/blob/8134115f88ed8018474e7db69afcfe97fb097fc4/src/llama-quant.cpp)
keep these unquantized. This is a validation concern, **not proof of broken weights**.
A header rewrite cannot restore precision. Preserve the artifact and first evaluate it; only
request replacement tensors or another conversion if controlled evidence identifies a problem.

## Speculative decoding acceptance contract

Use the native one-block NextN head through `--spec-type draft-mtp`; there is no need to find a
separate small draft model. The upstream MTP implementation exports post-normalized trunk hidden
states after mHC collapse, projects token embedding plus hidden state into the draft block, and
reuses its sparse index selection across draft iterations.

Verification must restore both convolution and KDA recurrent states after rejection, as well as
MLA/indexer/pool state. The champion has rollback-aware helpers in
`src/models/delta-net-base.cpp:454` and `:522`; the MTP PR uses snapshots and registers GLM5Next
for recurrent rollback. A terminal-state-only trunk graph is insufficient.
The [pinned MTP graph](https://github.com/timkhronos/llama.cpp/blob/5b8593b5451ec45fd4a81fb844efb6be9b45fd36/src/models/glm5-next.cpp)
and `common/speculative.cpp` must be reviewed as one stateful path.

Source presence is not correctness evidence: the MTP PR currently skips the GLM architecture
fixture. #27752 has a further CPU concern: its inspected rollback allowlist omits GLM5Next,
so rejected speculation can require prefix replay. Neither alternative establishes byte-identical
greedy output across batch shapes. Do not describe speculative decoding as validated or lossless
until controlled tests establish the relevant contract.

## Recommended execution plan and stop conditions

1. Pin the full current champion as the experimental candidate base. Reconcile and adapt the
   #27773/#27917 support stack, preserving accumulated CPU/GPU keeps. No production edits.
2. Add explicit old-Unsloth metadata compatibility and reference-correct MTP index-sharing
   metadata. Validate all tensor dimensions and quant types before loading weights.
3. Run CPU trunk and native-MTP smoke tests. Check real draft tokens, acceptance counters and
   draft-head graph dispatch; a silently disabled speculative path fails this gate.
4. Test reference logits on a manageable fixture; pool boundaries/tails and prompts crossing
   the sparse-selection threshold; full vs chunked prefill; state save/restore; forced rejection
   at every draft position; all accepted, none accepted, and repeated accept/reject cycles.
   Compare rollback continuation against replay of the same accepted prefix. Separate ordinary
   batch-shape numerical differences from stale-state defects. Reset sessions between prompts.
5. Validate existing champion CPU and GPU workloads on the full candidate. Shared cache and
   speculative changes have cross-model scope even though the new architecture is isolated.
6. Measure native MTP with draft lengths 1,3,5 against identical-artifact plain decode, reporting
   prefill, accepted output tokens/s, acceptance and verification cost. MTP is the required
   candidate configuration; plain decode is its diagnostic baseline. No speedup is presumed.

Finish only when native MTP works correctly and its measured CPU performance is reported.
If drafting works but is slower, report that result explicitly; do not replace it silently with
plain generation. Speed observations remain subject to the canonical recipe, claims, residency
and host-health rules. The current host's >1-week uptime prevents a trusted canonical claim
without the required host-health resolution.

## Audit evidence limits

Read-only inspection, not a runtime certification. GitNexus's indexed loader query returned LOW
with zero upstream callers, but that index is not proof of whole-port scope; shared memory and
speculative code require the regression matrix above. No kernel edits were made.
Raw API/source snapshots from this session are in
`/mnt/raid0/llm/tmp/glm53-support-audit-20260908/` and `/tmp/glm53-mtp-audit/`;
commit-pinned links and the identities above are the durable external references.


## Executed CPU validation — 2026-09-08

The source-only audit above is superseded for CPU execution by candidate
`2346de90942e29534053df434db89c4a2b110616` on
`experimental/glm53-text-mtp-20260908`. Production is unchanged. The candidate
adapts the upstream text/MTP implementation and local metadata compatibility;
no GLM vision path or new performance kernel was developed.

The full six-shard local model runs. With the champion's t48 CPU recipe,
matched five-by-512-token measurements produced these observation-only results:

| Mode | Median output tokens/s | MAD | Exact token parity against plain |
|---|---:|---:|---|
| Plain | 6.366087 | 0.011553 | reference |
| Native MTP, parallel verification | 7.595921 | 0.008261 | FAIL, index 6 in every repetition |
| Native MTP, `LLAMA_SPEC_EXACT=serial` | 5.783764 | 0.008529 | PASS, all five 512-token arrays |

Serial MTP's measured requests contain 939 completed verification events:
2809 drafted tokens, 1615 accepted, 609 events rejecting at least one draft.
These are real native-MTP executions, not merely load or flag checks. The exact
serial mode is about 9.1% slower than plain on this trajectory. Parallel mode's
higher rate is not a validated lossless speedup.

The real-artifact target-only discriminator reproduces token 13931 instead of
plain token 1246 from a clean sequential prefix followed by a four-token batch,
without any prior rollback (maximum logit difference 0.1989278793). Therefore
batch non-invariance alone suffices to explain the first mismatch. Existing
champion serial verification avoids that path. This result does not prove that
every other rollback history is correct; separate tests cover 48 forced
rejection/replay cases, four used-MTP-context restores, and 24 pool boundary
cases across tiny fixtures, plus the Qwen35 regression checks.

Evidence: `/mnt/raid0/llm/tmp/glm53-validation-20260908/`;
`runtime/reports/serial-plain-full-audit.json` reopens raw response and native
verification-log records, checks source/model/binary identities, and validates
exact requests and all token arrays. The earlier parallel failure is retained
in `runtime/reports/paired-full-audit.json`. The target-only discriminator is
in `runtime/real-divergence-20260908T212632Z/`.

Limits: the shared host has about 26 days uptime, so timings are observations,
not canonical promotion evidence. One prompt was measured, using the saved
model template with reasoning enabled and `ignore_eos=true` to force 512 output
tokens. No natural-stop parity, broad model quality, GPU regression, long-context
sparse-selection performance, or independent unquantized reference parity is
claimed. Thread-count screens are recorded in the session progress report.
