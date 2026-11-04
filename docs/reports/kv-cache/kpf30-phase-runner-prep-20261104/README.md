# KPF-30 owner-runner phase bracketing preparation

Source inspected read-only: `/mnt/raid0/llm/tmp/kvfork/kpf17-oracle-build-20261104/source`, HEAD `8952a0f693fb923918157eb25117641b74766230`. No kernel source, build, inference, graph registry or shared metadata was modified. This preparation is **not a runnable producer patch**: candidate-bound impact admission is required before drafting one.

## Impact admission result

`gitnexus status` run inside the exact source returned `Repository not indexed`. `gitnexus impact handle_last_sampled_token --direction upstream --repo /mnt/raid0/llm/tmp/kvfork/kpf17-oracle-build-20261104/source` returned repository not found. An unqualified impact query also refused because multiple repositories are registered. The production and older experimental llama.cpp graphs are not substitutes. No impact risk classification exists; it must not be described as LOW. No index build was started under the owner's publisher-only rule.

## Authoritative mapping at this commit

All references below are in `tools/server/server-context.cpp` unless stated otherwise. Token count, ubatch size and `rowexact_verify` must never determine phase.

| Source control flow | Exact row membership | Phase |
| --- | --- | --- |
| `server_slot::handle_last_sampled_token`, lines 590–625, `spec_draft.empty()` branch | The sampled row appended at `i_batch` | `decode` |
| Same function, nonempty `spec_draft` branch | Every index explicitly inserted into `spec_i_batch`, including the sampled seed; serial mode records only the seed | `verify` |
| Prompt-token append loop, lines 5078–5096 | Rows appended by the prompt loop | `prefill` |
| `sample_and_accept_dspark_serial`, lines 5381–5425 | Each accepted draft token decoded in `serial_batch` | `verify` even though each call has exactly one token |
| `spec_exact_bonus` replay lambda, lines 5472–5485 | Prefix replay and bonus replay are separate target work | Must carry an explicit replay provenance policy; fail closed as `unknown` until replay is represented distinctly or owner approves inclusion in verification |

For the main decode at line 5279, preserve phase metadata alongside row insertion before `pre_decode` changes slot state. Slice the metadata using the same `off` and `batch_view.n_tokens` as the submitted batch; retain exact sequence/position, not slot-state classification at observation time. A mixed prefill/generation batch requires per-row labels. One global phase label is invalid.

`src/llama-kv-cache.cpp:1902–1908` emits no `pos` today. The consumer `_FIELDS` requires `row seq pos n_tokens ...`; therefore current native rows cannot produce a valid capture. Future patch must print `ubatch->pos[i]` immediately after `seq`, retaining the existing field order.

## Producer patch acceptance contract

1. Scope observer activation to `LLAMA_KPF30_MIXED_BLOCKS=1`; no behavioral change when disabled.
2. At every owner target `llama_decode` call, emit BEGIN with a unique monotonic call and exact submitted token count, then one PHASE per submitted index with explicit insertion provenance and actual `seq_id`/`pos`.
3. Emit END after return with the actual return code. Errors, exceptions, unknown provenance and any target work outside the scope must prevent successful capture; emit `KPF30_UNSCOPED_TARGET` for unsupported target paths. Audit target decoding through helpers, multimodal paths and speculative internals as well as the three direct calls found here.
4. Join mask rows by sequence and position; row indexes may restart across ubatches and layers. Never join a mask's local row number to a full-batch index.
5. Startup masks before the first bracket are excluded by the consumer. Any mask after observation starts outside a bracket fails closed. Run capture only after fan completion and process reap, using the actual binary digest and prompt-set digest.
6. Repeated sequence/position within one call and multi-sequence token inputs require explicit handling; current consumer intentionally rejects duplicate input joins and only the first sequence is emitted by the native observer. Do not claim these workloads covered without extending and testing the native schema.

## Validation

`python3 docs/reports/kv-cache/kpf30-phase-runner-prep-20261104/test_phase_contract.py`: six model-free tests pass. They prove single-token verify and multi-token decode retain explicit labels, mixed batches filter prefill correctly, current missing-position records are rejected, and unknown/failed/unscoped/partial data fail closed. These are consumer contract tests, not a claim that the future C++ producer builds or runs.

## Concrete publisher preparation

The earlier generic compute placeholder has been replaced with a canonical `publish_row.py` input specification at `/mnt/raid0/llm/tmp/kvfork/kpf30-impact-8952-20261104/spec.json` (the tracked JSON mirrors it). `publish_row.py` derives the actual `epyc.row.v3` row; this preparation deliberately does not fabricate a published row or grant.

The sealed launcher uses `filler_run15.sh`, CPU build placement, a real partial committed-source reference scan as first progress, and an isolated **detached git worktree** at `/mnt/raid0/llm/worktrees/kpf30-impact-8952-20261104`. Sealed SHA-256 inputs include the runner, launcher, specification, observer source, server source, native analysis wrapper and project admission guard. Every native index/query runs behind the launcher grant and project guard. Each HIGH/CRITICAL result is persisted before writing `OWNER_WARNING` and exiting immediately; no later symbol is queried. Full verbose analyzer logs, >512 KiB tracked-file coverage, status binding, all impacts and terminal result remain in `out/**`.

Preparation validation: canonical launcher parser and sealed `--check` pass; Python compile and Bash syntax pass. A direct **model-free smoke branch only** scanned the six committed symbol-reference sets, emitted a partial record and returned the expected 75. Receipt: `/mnt/raid0/llm/tmp/kvfork/kpf30-impact-8952-20261104/out/model-free-smoke-validation.json`. No graph indexing, native impact query, publication, inference, or full job execution was performed. The publisher must still qualify and publish this specification; this validation is not a PASS/ARMED receipt.

## Candidate impact packet custody correction

The reviewed scratch packet is bound to KPF-30.PHASE-IMPACT in `impact-index-compute-row.json`. Its job now checks the pinned detached HEAD, tracked cleanliness, matching `source_worktree` identity, and absence of untracked non-ignored files both before work and after all graph queries. The check uses `git ls-files --others --exclude-standard -z`, so GitNexus private metadata ignored by Git remains permitted. The packet includes `source_integrity.py` and `test_source_integrity.py`; `python3 test_source_integrity.py` verifies that untracked inputs are rejected while ignored `.gitnexus` metadata is allowed. This is a model-free custody test, not graph or risk clearance. The refreshed seal is `/mnt/raid0/llm/tmp/kvfork/kpf30-impact-8952-20261104/identity.json`; the candidate HEAD remains `8952a0f693fb923918157eb25117641b74766230`.
