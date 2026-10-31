CODE SHA: def3e2c08dbe5939ecbbc3e4c862f6110f29fda3 (origin/main remotely verified; normal hooks, serialized nonforce push; rebase over unrelated PromptForge formatting only).

M-17e — targeted content-corrupt episodic vector repair

Original owning row: handoffs/active/episodic-memory-integrity.md (text identity: “M-17e — No tool repairs a content-corrupt vector.”). ROOT owner applies the original box; do not split it. First checkbox line must contain exact final CODE SHA plus tests/unit/test_repair_episodic_vector.py and [no-belief: tooling-repair].

Deliverable: scripts/maintenance/repair_episodic_vector.py, a single-memory repair CLI. Default is an offline dry run. Apply requires explicit --readers-stopped because existing readers cache their index. Uses the existing .episodic_faiss.lock plus SQLite BEGIN IMMEDIATE; validates bidirectional DB/id_map/FAISS identity and IndexFlatIP semantics; obtains canonical embedding text; disables parallel hash fallback, fallback vectors and model subprocesses; normalizes in float64 and verifies finite float32 unit norm; reconstructs preserving every position and non-target vector; saves the original index and atomically replaces only embeddings.faiss. No live store mutation or inference was performed.

Evidence: lane-validation.log and lane-validation-receipt.json in this scratch root. 17 native FAISS/numpy/SQLite tests pass, including bad bidirectional bindings, float32 extrema, unchanged non-target vectors and DB/id_map bytes, dry run, offline embedding failure, actual fallback-path refusal, and injected publication failure preserving the original index. Ruff formatting and lint pass. make gates passed before the two review-requested localized refinements (only these new files changed afterward); MAIN explicitly said no repeat of unchanged gate paths needed.

Resource receipt: R6 model-free batch on SMT132-133 with physical36-37 mutex, all current CPU-quarter grants accounted for; q1 correctness and disjoint q0 timing; no whole-host timing grant. 2.51s elapsed;119021568-byte sampled peak process-tree RSS; spawned PID confirmed absent after wait. Tests use preexisting canonical APP Python3.11 environment, --confcutdir=tests/unit to exclude unrelated API initialization.

GitNexus: private lane unindexed; canonical APP stale83commits, explicitly reported. Existing maintenance lock LOW; canonical-memory helper CRITICAL33callers, dependency reused without editing. MAIN accepted controlled additive standalone scope; no existing runtime helper modified.

Deferred independent original /slots0/19 row: not claimed, not ticked, no quota credit. It explicitly asks for RTG-03 manifest/realized confirmation, which this standalone maintenance task does not establish.

CI enrollment: Makefile:205 runs pytest tests/ recursively; new tests/unit/test_repair_episodic_vector.py matches normal collection without explicit list enrollment.
