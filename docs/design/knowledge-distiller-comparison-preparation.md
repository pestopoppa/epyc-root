# ID-4 comparison preparation — 2026-11-02

Status: native paired primitive exists; no quality comparison row is publishable yet. This is a concrete implementation handoff, not an inference booking or adoption authorization.

## Grounded execution path

`orchestration.repl_memory.episodic_control.run_paired_arms` accepts raw StrategyStore records, explicit deletion IDs, an embedder/dimension, one query, retrieval options, and a callback. It creates fresh temporary control/candidate stores and closes/removes both. Candidate callback: `lambda store: KnowledgeDistiller(store).distill(trial_id=<comparison-cycle>)`. Identical survivor inputs and retrieval options reach both arms; only candidate receives abstraction. The callback and native distiller require no LLM: current abstraction deterministically selects the longest cluster member as seed and adds a summary prefix. Model pinning is required for downstream task quality and embedder, not for a nonexistent distillation model.

Defaults currently include cluster similarity 0.75, convention similarity 0.70, minimum validity 0.10, minimum raw cluster size 3; native retrieval defaults k=5, quarantine excluded, stale penalty=0.5. Freeze these explicitly in a comparison manifest, rather than relying on future defaults.

IMPORTANT: native distiller groups by `species`, not task family. Partition original records into separate task-family invocations of the paired primitive before distilling; preserve their original species. Merely passing species as the family would alter provenance and is not equivalent. Each primitive call handles one query; a multiquery harness must rebuild equivalent stores per query or introduce an explicitly scoped evaluation wrapper.

The native fixture uses generated alpha strings and a deterministic clusterable embedder. It proves arm isolation/retrieval behavior, not usefulness on held-out tasks. Do not republish its 17 passing tests as a quality comparison.

## Corpus checkpoint — 2026-11-02

A read-only local snapshot was prepared at `/mnt/raid0/llm/tmp/compute-flags/handoff-sessions/intake-derived-work-2026-07-25/id4-corpus/`: 1,428 strategy records, 1,372 folded trials, and 450 conservatively eligible episodes, split 346 source / 104 held-out with disjoint recorded episode and trial evidence IDs. Its manifest and `READINESS.md` record hashes, filters and limitations. This scratch location is a preparation artifact, not a durable publication or a quality result. The recorded `action_type` is an optimization-action family, not a downstream benchmark task family; historical aggregate scores do not supply question-level prompts or correctness oracles, and question-level independence has not been established. Recover and bind those before making a quality claim. A retrieval-only manipulation pilot could use the snapshot without deciding adoption.

## Implementable next work

1. Export an immutable, read-only snapshot of actual raw StrategyStore episodes with original IDs, trial/evidence IDs, descriptions/insights, species, metadata and validity context; snapshot corresponding folded trial journal so invalid/excluded evidence cannot be silently resurrected. No live-store path is passed into the primitive. Bind export hashes and code hashes (id4-readset.json).
2. Build task-family map from recorded task identities. Freeze train/source episode IDs, held-out query/task IDs and a disjointness check over underlying evidence/trial IDs. If no task identity is recorded, produce the missing mapping from source trial records before starting compute. The local snapshot above is available for preparation; preserve its provenance and do not substitute a synthetic fixture for a quality corpus.
3. Implement batch family partition -> paired primitive -> serialized retrievals/stats. Pin actual embedder artifact, dimensions, CPU placement, tokenizer and downstream answer model/build. Reject a run with zero patterns/conventions or no changed retrieved context as a manipulation-check failure rather than evidence of equivalence.
4. Use the same held-out prompts, decoding settings, retrieved-context budget and scoring library for both arms. Retain raw retrieval text, source IDs, answers, scorer outputs, prefill/decode tokens, wall time, memory and distillation counters. Score task correctness higher-is-better; total pipeline tokens/cost lower-is-better. Preserve per-family outcomes so an aggregate gain cannot hide family harm.
5. Predeclare the actual adoption criterion before execution: bind a numeric task-quality benefit/nonregression rule and token-cost tradeoff to the selected corpus. No acceptance threshold was found in the current owner handoff; this document deliberately does not manufacture authorization to ship. A pilot can characterize outcomes but cannot name a winner without that rule.
6. Register the measurement writer with the existing Vidya source ladder and carry a claim tuple at write time before treating outputs as decision evidence. No new grading rule. Preserve the no-production-caller tripwire.

## Ready-to-run smoke check (model-free; not executed here)

From the pinned orchestrator checkout, with its dependency environment and the owning session's granted CPU affinity:

```bash
.venv/bin/python -m pytest -q tests/unit/test_episodic_control.py tests/unit/test_knowledge_distiller.py -k 'ap29 or invalid_pairs'
```

This command is a structural verification only, not the held-out comparison. No inference, row publication, production wiring, gate/index/handoff edit or commit was performed during this preparation.
