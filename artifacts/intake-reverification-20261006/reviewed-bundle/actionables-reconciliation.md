# IRV actionables reconciliation — bounded mechanical packet, draft only

This supersedes the earlier `/mnt/raid0/llm/tmp/intake-reverify/derived-actionables-ledger.draft.md`, which is not accepted coverage. The new packet preserves the source wording separately from proposed terminal dispositions and task-text bindings. Source-gate closure is required before ordinary Stage 3; it does not block preserving currently open work. No consumer, code, index, ledger, handoff, or wiki write is included.

The source collector examined only the known 22 dive directories and matching consumer-native proposals (one directory level; no recursive clone walk). It captured 79 action/recommendation records with packet path, field path, and packet SHA-256. It also retained the source-authored terminal/disposition fields as a separate collection. Machine files:

- `actionables-source-records.draft.json` — complete verbatim source recommendation/action records and packet provenance.
- `actionables-reconciliation.draft.json` — those source records, verbatim terminal-disposition fields, and provisional statuses; 39 original disposition fields.
- `actionables-task-bindings.draft.json` — exact current-origin checkbox/task text bindings, source path, line, checkbox state, and containing file hash.

Exact open owner task bindings found by task-text search, preserved as open and not rewritten:

- intake-1239: `KB-GS-1` through `KB-GS-4` in `handoffs/active/internal-kb-rag.md`; the current handoff itself says its details came from a summariser-rendered fetch and require re-verification before decision-grade use. Do not collapse these four probes into a generic “no task until source gate” decline.
- intake-1240: `C5-17` in `handoffs/active/agentic-rocm-kernel-authoring.md`. It is the existing surrogate-related task: ordinal bins plus calibration gate for any future predictor, decline the trained artifact, and defer building while C2-8/C2-9 remain open. Preserve the baseline-search comparison and equal-budget control in its text.
- intake-1087: `AK-PM-13` in `handoffs/active/autokernel-research-loop.md`, still open. The task binds the attenuation datum and calls for reading the merged source PRs; retain it for owning-session source/current-code review. The source result does not authorize deleting or closing that work.
- intake-1248: `AK-PM-9`, `AK-PM-11`, and `AK-PM-12` in the same handoff, all open; retain threshold-conditional negative, local ablation gate, and write-side receipt steering as separate tasks.
- intake-974: “Add the Slow/CRR conditional diagnostic” in `handoffs/active/architect-model-selection-bench.md`, open; preserve that objective.
- intake-989: two distinct open checkboxes in `handoffs/active/engram-conditional-memory.md`: RRR retroactive log diagnostic, and programmatic feedback extraction from tool output. The source supports considering both mechanisms, but its rates do not transfer; do not merge the two outcomes or claim existing code implements them.
- intake-983: the RA-9 gate-before-judge procedure is already checked/completed in both the active owner (`reviewer-typed-artifacts.md`, RA-9) and the completed security skill (`security-review-skill.md`). Preserve the existing single implementation and completion status; no duplicate schema or new implementation task.
- intake-1028: `AK-C6-1` syscall-confinement acceptance task is checked/completed in `autokernel-research-loop.md`; preserve the result and remaining owner context, without reopening or treating it as deployment authorization.
- intake-979: six C6 controls (whole tree, named threat, aggregation, monitor awareness, CoT visibility, FPR budget) are individually checked/completed in `rocm-verify-profile-backend.md`; retain them as carried outcomes, not fresh implementation tasks.

Other raw records remain individually identifiable in the source JSON. Where an exact current checkbox/task-text match or direct source-authored terminal mapping is absent, the record is `UNRECONCILED`; no semantic decline or “not applicable” conclusion is inferred. In particular, intake-978 candidate patterns, intake-1239’s KB probes, intake-1240 C5-17, and intake-1087 AK-PM-13 are not dropped. Current-code/source review is still required to terminalize all recommendations.

Read-only implementation-path locator results (candidate paths only; no fit or completion claim):

- Retrieval/KB surfaces: `epyc-orchestrator/src/retrieval/kb_rag.py`, `src/retrieval/colbert_encoder.py`, `src/tools/web/colbert_reranker.py`, `src/repl_environment/code_search.py`; corresponding tests include `tests/unit/test_colbert_reranker.py` and `tests/unit/test_code_search.py`.
- Memory/failure surfaces: `epyc-orchestrator/orchestration/repl_memory/episodic_store.py`, `failure_graph.py`, `distillation/failure_bridge.py`; matching tests `tests/unit/test_episodic_store.py`, `test_failure_graph.py`, and `test_failure_bridge.py`. A bounded `rg` over these runtime paths did not find an existing RRR `SequenceMatcher` reflection diagnostic; this is a locator result, not proof of full absence.
- RA-9 single implementation: `epyc-orchestrator/src/proactive_delegation/gold_annotations.py`, `gold_sanity.py` and `tests/test_gold_annotations.py`.
- intake-1087 / intake-1240: current owner tasks are handoff/documentation and source-PR/experiment gates; the bounded code search did not establish a direct producer implementation path to modify.

## Corrected source-wiring proposal

The generic research-intake row is already wired: `scripts/vidya/adapters/README.md:32` names the literature ladder and `research_intake.py`; line 233 says `research/intake_index.yaml` is live. The actual gap is the correction/refresh event path for current native warrants. See `consumer-patch/source-wiring.draft.md`, which proposes the explicit task ID `VB-RI-CORRECTION-REFRESH-1`: digest-pinned retirement of only the named current native support/opposition warrants; optional reviewed replacement claims through the existing literature ladder; and scoped read-depth withdrawals that emit no substitute source claim. This is a draft task, not a new grading rule or generic adapter-ingest task.
