# ReMe — HoMe plugin, evaluation and optimization harness

[Primary source](https://github.com/agentscope-ai/ReMe) · intake-3022 · 2026-11-27

The official artifact includes the HoMe plugin, dataset and benchmark preparation, revision-pinned candidate promotion, runtime docs, and multiple CLI entry points for scoped smoke/formal evaluation and optional agent optimization. The implementation intersects before/after maps at (case ID, query ID) and carries coverage separately, while classification/inspection tools join retriever traces, source-session IDs, memory construction and Git diffs. The reuse path qualifies completed, infrastructure-error-free scored training ancestors by dataset and construction-config fingerprints (runtime, config, plugins, image and model identity), then checks individual archive hashes and prior successes, retaining the exact reviewed snapshots; previously reviewed case source maps cannot silently substitute any other archive. The LME default split excludes training IDs; BEAM default runner independently executes but evaluates 100K cases that may overlap training. The paper’s BEAM-1M result needs an explicit independent variant and candidate revision. Baselines printed in README refer to the authors’ paper and are not replication. The plugin requires ReMe 0.4.3+, benchmark Docker image, model/embedding endpoint configuration, and the default Linux optimizer/diagnoser uses Bubblewrap and delegated cgroup v2. Code was inspected only. No exact companion URL was found in the lane index.

Read the HoMe plugin README setup and artifact conventions, evaluation-artifact guide, benchmark evaluation configs/docs, and targeted evaluation/reuse.py, comparison.py and sampling.py implementation. Other repository modules, full tests, container build and runtime evaluation were not read or executed.

## Evidence

- HoMe retains content-verified archives for final replay and records the specific reviewed SHA-256. [plugins/home/README.md:12–15](https://raw.githubusercontent.com/agentscope-ai/ReMe/e3d602cc9d24e69348d4f243bafa7159c79bfc0e/plugins/home/README.md)
- The implementation intersects case/query IDs before comparing scores and reports coverage separately. [plugins/home/src/reme_home/evaluation/comparison.py:150](https://raw.githubusercontent.com/agentscope-ai/ReMe/e3d602cc9d24e69348d4f243bafa7159c79bfc0e/plugins/home/src/reme_home/evaluation/comparison.py)
- The default BEAM evaluation splits can overlap. The independent set must be selected explicitly. [benchmark/beam/README.md:150–153](https://raw.githubusercontent.com/agentscope-ai/ReMe/e3d602cc9d24e69348d4f243bafa7159c79bfc0e/benchmark/beam/README.md)

## Scope and local transfer



Use comparison and reuse code as inspectable reference patterns for CPU-side case/session identity, frozen input/manifest hashes and warm-construction artifact reuse. Only if evaluating retrieval changes on MI210, measure warm/cold token-cache categories and wall time separately. Keep eval variants explicit and validate disjoint benchmark case IDs before measuring. Extract reusable patterns into current harness surfaces rather than adopting the full framework by default.

M-12 receipt admission binds existing runs; candidate selection also needs versioned memory and isolation between search and final cases. Add content-addressed session-memory and harness identities to candidate replay. Smoke-test construction and retrieval, score candidates on a search split, and use locked, unseen conversations for final quality and query-token comparisons.

## Sources surfaced

No additional decision-changing source identified.
