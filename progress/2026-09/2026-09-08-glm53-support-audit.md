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

Builds and inference have not run. A task-scoped operator question is pending:
authorize the existing physical CPU/GPU locks directly because this interactive
session has no roster identity and the live coordinator has no compute-request
handler; allow observation-only timings without rebooting the approximately
26-day-old host. The request is recorded at
`/mnt/raid0/llm/tmp/glm53-validation-20260908/compute-request.md`.
Offline integration and test preparation continue while that answer is pending.
Native draft dispatch, actual acceptance/rejection, rollback/replay, and speed
remain unvalidated; T0-SPEC is not complete.
