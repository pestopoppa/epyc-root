# Corpus-Augmented Prompt Lookup Revalidation

**Status**: ACTIVE-HIGH, created 2026-07-03 from live-stack audit
**Parent index**: [inference-acceleration-index.md](inference-acceleration-index.md)
**Priority**: high disk/capability ROI, below current G0/GPU and evidence-plane authority rows
**Related**: [speculative-decoding-mtp-refresh.md](speculative-decoding-mtp-refresh.md), [model-stack-single-source-update-pipeline.md](model-stack-single-source-update-pipeline.md), archived [hybrid-lookup-spec-decode.md](../archived/hybrid-lookup-spec-decode.md), archived [llama-server-prompt-lookup.md](../archived/llama-server-prompt-lookup.md)

## Objective

Decide whether the local code corpus at `/mnt/raid0/llm/cache/corpus` is a live
performance feature or reclaimable dead weight. The current artifact occupies
about `651G`, so it must either provide measured coding-task acceleration or be
quarantined/deleted by explicit operator decision.

## Current Findings

- Live `llama-server` commands do not pass n-gram/prompt-lookup corpus flags;
  active servers use draft-MTP where supported.
- No live process currently holds files under `/mnt/raid0/llm/cache/corpus`.
- Recent inference tap logs contain no `<reference_code>` or `## Reference Code`
  prompt-injection evidence.
- Production code still has corpus-injection call sites:
  `src/prompt_builders/builder.py:build_corpus_context()`,
  `src/api/routes/chat.py`, `src/api/routes/chat_pipeline/stream_adapter.py`,
  `src/graph/helpers.py`, and `src/api/routes/chat_delegation.py`.
- Direct `build_corpus_context()` testing returned an empty string.
- Likely wiring bug: `build_corpus_context()` imports `ModelRegistry`, but the
  current registry module exposes `RegistryLoader`; the failure path silently
  leaves the retriever disabled.
- Current `RegistryLoader(validate_paths=False)` reports
  `corpus_retrieval=False` for `frontdoor`, `coder_escalation`,
  `worker_general`, `architect_general`, and `ingest_long_context`, despite
  stale older YAML sections mentioning corpus retrieval.
- Forced retrieval against `/mnt/raid0/llm/cache/corpus/v3_sharded` can return
  snippets, but one realistic query took about `29s` for 3 snippets; short
  low-overlap queries returned no snippets in about `0.36s`.

## Prioritized Task List

- [ ] **CPL-1: Fix or explicitly retire the wiring path, no inference.**
  Repair `build_corpus_context()` registry loading, make per-role
  `corpus_retrieval` resolution explicit, and add fail-visible diagnostics when
  corpus retrieval is disabled by config, missing index, import failure, or slow
  query timeout.
- [ ] **CPL-2: Add live observability.** Emit structured tap/log metadata when
  corpus snippets are injected: role, request/task id, index path, query n-grams,
  snippet count, context chars, retrieval latency, and timeout/failure reason.
  This must make "header only, no corpus" impossible to confuse with real use.
- [ ] **CPL-3: Add a cheap offline health probe.** Provide a CLI probe over the
  v3 sharded corpus that runs representative coding queries and reports
  p50/p95 latency, snippets returned, candidate counts, and whether the current
  index is usable for online prompt injection.
- [ ] **CPL-4: Run a focused corpus-on/off A/B for coding tasks.** Compare
  corpus injection off vs on for `coder_escalation` and any intended cheap
  coding role. Capture latency, generated t/s, draft acceptance if available,
  quality, and injected-snippet telemetry. This is not a production enablement
  gate unless it follows `/workspace/MEASUREMENT.md`.
- [ ] **CPL-5: Decide keep/quarantine/delete.** Keep only if the A/B shows a
  measured coding-task benefit and retrieval overhead is bounded. Otherwise
  mark `/mnt/raid0/llm/cache/corpus` reclaimable and preserve only the small
  build metadata/scripts needed to recreate it.

## Dependency Graph

```mermaid
flowchart TD
    C1[CPL-1 wiring/config] --> C2[CPL-2 observability]
    C1 --> C3[CPL-3 offline probe]
    C2 --> C4[CPL-4 corpus-on/off A/B]
    C3 --> C4
    C4 --> C5[CPL-5 keep/quarantine/delete decision]
```

## Cross-Cutting Concerns

- This is not the same as native draft-MTP. MTP may stay enabled while corpus
  injection is off; corpus work must not disturb current v6 draft-MTP serving.
- If role-level corpus enablement becomes a stack fact, it belongs in the
  generated stack-prior/descriptor pipeline rather than a stale local constant.
- Retrieval latency is part of the metric. A 29s snippet lookup is a regression
  even if the generated answer improves.
- Do not delete the `651G` corpus without an explicit operator decision after
  CPL-4/CPL-5 evidence.

## Key File Locations

- Corpus artifact: `/mnt/raid0/llm/cache/corpus/v3_sharded`
- Corpus service: `/mnt/raid0/llm/epyc-orchestrator/src/services/corpus_retrieval.py`
- Prompt wiring: `/mnt/raid0/llm/epyc-orchestrator/src/prompt_builders/builder.py`
- Chat call sites: `/mnt/raid0/llm/epyc-orchestrator/src/api/routes/chat.py`,
  `/mnt/raid0/llm/epyc-orchestrator/src/api/routes/chat_pipeline/stream_adapter.py`,
  `/mnt/raid0/llm/epyc-orchestrator/src/api/routes/chat_delegation.py`,
  `/mnt/raid0/llm/epyc-orchestrator/src/graph/helpers.py`
- Registry/config: `/mnt/raid0/llm/epyc-orchestrator/orchestration/model_registry.yaml`,
  `/mnt/raid0/llm/epyc-orchestrator/src/registry/registry_loader.py`
- Existing benchmark scaffold:
  `/mnt/raid0/llm/epyc-orchestrator/scripts/benchmark/corpus_quality_gate.py`

## Reporting Instructions

After any CPL step, update this handoff first, then
[inference-acceleration-index.md](inference-acceleration-index.md) if priority
or keep/delete status changes, and finally
[master-handoff-index.md](master-handoff-index.md) if it changes the active
queue. Record any numeric claims with protocol and era labels per
`/workspace/MEASUREMENT.md`.
