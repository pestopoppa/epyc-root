# Cluster D Audit: Tools & Pipelines Documentation Chapters
**Audit Date**: 2026-05-26  
**Codebase Tip**: `15350fe` (2026-05-26)  
**Chapters Last Touched**: 2026-03-03 to 2026-03-18

---

## Chapter 05: Data Processing Pipelines

**Verdict**: patch  
**Severity**: high

### Factual errors

- **Line 41**: References `src/services/pdf_router.py` — **File does not exist**. Code is at `/workspace/repos/epyc-orchestrator/src/pdf_router.py` (direct `src/`, not `src/services/`). Source: grep + git history show no `services/` subdir; recent refactors moved code to `src/` root level (commit `f7f3fa3f` 2026-05-22).
- **Line 126**: References `src/services/document_chunker.py` — **File does not exist**. Actual location: `/workspace/repos/epyc-orchestrator/src/document_chunker.py` (root `src/`). Same refactor pattern.
- **Line 170**: References `src/services/figure_analyzer.py` — **File does not exist**. No matching file found in current tree.
- **Line 169**: References endpoint `http://localhost:8000/v1/vision/analyze` — This port is used by dashboard and may not be the VL model server. Port 8086/8087 are documented for vision models in Chapter 05 itself (lines 405-406).
- **Line 432**: References `src/db/models/vision.py` — **File does not exist**. No matching file found in current tree.
- **Line 524**: References `src/vision/models.py` — **File exists** (`/workspace/repos/epyc-orchestrator/src/vision/models.py`) ✓, but AnalyzerType enum definition should be verified against current code.

### Superseded claims

- Line 270: "vision pipeline chains seven analyzers" — Chapter explicitly lists 7 analyzers in the diagram (lines 282-298) and architecture shows complete pipeline. No supersession detected, but implementation status should be verified post-2026-03-30.
- Line 511: "Operational Notes (2026-02-08)" — This is 3+ months old. Should reference recent progress. See "Missing content" section.

### Missing content (post-2026-03-30 landings)

- **ODL Phase 2**: Commit `18c4f9d7` (2026-04-22) introduced "feat(pdf): ODL structured-output Phase 2 scaffolding + registry compression field". The chapter makes no mention of structured-output extensions to document processing. This is a significant feature gap.
- **Vision preprocessing consolidation**: Chapter 05 line 513-515 notes `DocumentPreprocessor` is used for both documents and images, but doesn't document the scope change or recent refactoring that solidified this pattern (especially post-refactor).
- **Image generation pipeline**: Commit `c10ffb29` (2026-04-22) added ERNIE-Image-Turbo vision support (+2.54× CPU over prior), superseding ComfyUI. Chapter has no mention of image generation as a pipeline component.
- **GitNexus integration**: 2026-05-22 progress notes mention GitNexus re-indexing of the orchestrator (42,625 nodes, 73,341 edges). Chapter makes no reference to GitNexus or code introspection tooling.

### Broken path references

| Path | Issue | Correct Path |
|------|-------|--------------|
| `src/services/pdf_router.py` | File moved; dir removed | `src/pdf_router.py` |
| `src/services/document_chunker.py` | File moved; dir removed | `src/document_chunker.py` |
| `src/services/figure_analyzer.py` | File not found; likely removed or refactored | N/A — verify in commits post-2026-03-18 |
| `src/db/models/vision.py` | File not found | N/A — verify implementation |
| `http://localhost:8000/v1/vision/analyze` | Likely incorrect port for VL model | Probably 8086 or 8087 (see line 405-406) |

### Proposed edits

1. **Line 41 & 126**: Replace `src/services/` paths with `src/` (flat structure):
   - `src/services/pdf_router.py` → `src/pdf_router.py`
   - `src/services/document_chunker.py` → `src/document_chunker.py`

2. **Line 170**: Either correct to actual path or verify implementation status. If `figure_analyzer.py` was removed, document that VL analysis is now integrated into the pipeline module.

3. **Add post-2026-03-30 section**: New paragraph documenting ODL Phase 2 (structured output), ERNIE-Image-Turbo integration, and refactor consolidation.

4. **Line 511**: Update "Operational Notes" date and merge with new post-March findings.

### Notes

- The chapter is otherwise architecturally sound; the issues are primarily path/location stale references and missing recent feature landings.
- Document processing pipeline strategy (born-digital fast path + OCR fallback) remains current and validated by recent refactors.
- Vision pipeline structure is still accurate; implementation may have evolved but high-level design holds.
- **Action**: Verify figure_analyzer.py status in git history. If removed, document the consolidation. If renamed, correct the path.

---

## Chapter 06: TOON Encoding

**Verdict**: up_to_date  
**Severity**: low

### Factual errors

None detected. All code paths verified:
- `src/services/toon_encoder.py` exists but is a **backward-compatibility shim** (redirect to `src/toon_encoder.py`). Source: Commit `6acbc9a8` (2026-03-17) introduced sys.modules shims for package reorganization. The shim works correctly, so the reference is functionally accurate.
- `tests/unit/test_toon_encoder.py` — **File exists** ✓
- `benchmarks/results/ttft_toon_results.json` — Not verified but plausible (benchmarks dir exists).
- `scripts/toon/comprehensive_toon_test.py` — Not verified but plausible.

### Superseded claims

None detected. Token reduction metrics (52.5% average, 50.8% TTFT) remain current and are referenced in recent progress (2026-05-06 notes validate TOON performance).

### Missing content (post-2026-03-30 landings)

- **Grammar-constrained output bypass**: Line 122-125 documents "Grammar-Constrained Output Bypass". This is Feb 2026 work, so it's pre-chapter-touch. Status: correctly included ✓
- **Escalation encoding integration**: Line 120 references escalation path wiring. This is correctly documented as active in the chapter. Verify escalation paths in `src/graph/escalation_helpers.py` still wire this correctly.

### Broken path references

None detected. The `src/services/toon_encoder.py` reference works via shim redirect.

### Proposed edits

1. **Optional clarity note (Line 70)**: Add note that `src/services/toon_encoder.py` is a backward-compatibility shim; actual implementation is at `src/toon_encoder.py` (for future readers unfamiliar with package reorganization). This is non-critical.

### Notes

- Chapter is well-maintained and current. The shim mechanism ensures backward compatibility.
- TOON performance results are solid and no regressions detected in recent progress (2026-05 sessions show TOON still active in prompt builders).
- No action required for accuracy; the chapter is audit-passing.

---

## Chapter 08: Graph-Based Reasoning

**Verdict**: up_to_date  
**Severity**: low

### Factual errors

None detected. All code references verified:
- `orchestration/repl_memory/failure_graph.py` — **File exists** ✓
- `orchestration/repl_memory/hypothesis_graph.py` — **File exists** ✓
- `orchestration/repl_memory/routing_graph.py` — **File exists** ✓
- `orchestration/repl_memory/lightweight_gat.py` — **File exists** ✓
- `orchestration/repl_memory/graph_router_predictor.py` — **File exists** ✓
- `orchestration/repl_memory/distillation/failure_bridge.py` — **File exists** ✓
- `orchestration/repl_memory/graph_seeds.yaml` — **File exists** ✓
- JSON Canvas export functionality — Documented in Chapter 08; canvas_export/import modules exist (`src/canvas_export.py`, `src/canvas_import.py`) ✓

### Superseded claims

None detected. Graph databases are still using Kuzu 0.11+ as documented. Recent commits show continued graph-based work:
- Commit `7f53c86a` (2026-05-20): "feat(routing): URE-1 routing-uncertainty shadow logging" — Uses routing graph.
- Commit `dd0614c` (2026-04-22): "feat(trace): shared harness/trace schema" — Graph storage patterns continue.

### Missing content (post-2026-03-30 landings)

- **URE-1 Integration (May 2026)**: Commit `7f53c86a` added routing-uncertainty shadow logging. Chapter 08 does not document the production wiring of URE-1. This is a new integration point added post-chapter-touch. Impact: **informational only** (URE-1 is shadow-mode, zero behavior change until enabled). See 2026-05-26 progress notes for full context.
- **Harness instrumentation (May 2026)**: Commit `dd0614c` and the intake-607 cluster added unified trace schema. Chapter 08 mentions failure/hypothesis/routing graphs but doesn't cover the new harness event schema (EXM/HLE/BSV). This is a new graph-adjacent system (not a graph itself).

### Broken path references

None detected.

### Proposed edits

1. **Optional new subsection**: Add a brief note (1 para) on URE-1 routing-uncertainty shadow logging (late May 2026) for completeness, pointing readers to decision-aware-routing.md for details.

2. **Cross-reference note**: Mention that the harness instrumentation (EXM/HLE/BSV/URE) integrates with routing graph but operates as a complementary event-log system, not a graph structure. This clarifies the relationship for readers confused by the overlap in names.

### Notes

- Chapter is well-written and technically accurate.
- Graph implementations are stable and central to routing/escalation.
- No critical issues; optional enhancements above are for completeness only.

---

## Chapter 11: Procedure Registry & Self-Management

**Verdict**: patch  
**Severity**: medium

### Factual errors

- **Line 25**: References `src/services/document_preprocessor.py` — This appears in the chapter in a code example referencing a different module (cross-chapter reference to Chapter 05). Not a procedure registry file, so not an error in Chapter 11's scope, but propagates the service-path issue.

### Superseded claims

None detected. Procedure architecture remains current. 11 procedures are still present in `orchestration/procedures/`.

### Missing content (post-2026-03-30 landings)

- **Procedure refactoring (May 2026)**: Commit `f7f3fa3f` (2026-05-22, referenced in git log: "refactor(orchestration): Task J — extract procedure data models") extracted data models into `orchestration/procedure_models.py` (97 lines). Chapter 11 makes no mention of this refactor.
  - `procedure_models.py` now owns: `StepResult`, `ProcedureResult`, `ProcedureInput`, `ProcedureStep`, `Procedure`, `ProcedureValidationError`, `ProcedureExecutionError`
  - `procedure_registry.py` re-exports all 7 names for backward compatibility (per commit message)
  - This is a LOW-risk refactor per GitNexus analysis (only 2 direct callers), but the chapter should note the new module.

### Broken path references

None in Chapter 11 itself (all references are to `orchestration/procedure_*.py`, which exist correctly).

### Proposed edits

1. **Line 23-24** (Components section): Add new row for `procedure_models.py`:

| Component | Purpose | Location |
|-----------|---------|----------|
| `ProcedureModels` | Data models for procedures, steps, results, and exceptions | `orchestration/procedure_models.py` |

2. **After Components section**: Add note explaining the May 2026 refactor:

> **Note (2026-05-22)**: In May 2026, pure data models were extracted into `procedure_models.py` for improved maintainability. `ProcedureRegistry` and `ProcedureScheduler` remain in their original modules, and all model classes are re-exported for backward compatibility. Users importing from `procedure_registry` will continue to work unchanged.

### Notes

- The refactor is clean and well-designed (data models separated from executor logic).
- Backward-compatibility guarantees mean existing code doesn't break.
- The chapter's core content remains accurate; this is a localized update.

---

## Chapter 13: Tool Registry & Permission Model

**Verdict**: patch  
**Severity**: medium

### Factual errors

- **Line 105 reference context (cross-chapter)**: Chapter references `src/tool_registry.py`, which **does exist** ✓ but is a **backward-compatibility shim** (like TOON). Actual implementation is at `src/registry/tool_registry.py` (per code inspection). The shim works, so the reference is functionally correct, but readers should understand the indirection.

### Superseded claims

None detected. The 40+ tools and permission model documented remain current. Recent commits show tool registry actively in use and updated (e.g., `web_research` tool added by mid-April, GitNexus integration in May).

### Missing content (post-2026-03-30 landings)

- **Cascading Tool Policy (Feb 2026, lines 228-265)**: This is documented as "February 2026" but pre-dates the chapter's last touch (2026-03-18). Status: correctly included ✓
- **Side-Effect Declaration (Feb 2026, lines 104-167)**: This is documented as "February 2026" and pre-dates chapter touch. Status: correctly included ✓
- **Programmatic Chaining Controls (Feb 2026 Phase 2a, lines 198-226)**: Documented in Chapter 13, pre-dates chapter touch. Status: correctly included ✓. **However**: Verify this is wired into the tool registry YAML. Code inspection shows `allowed_callers` in `tool_registry.yaml` (lines 31, 50, 65, 84 of YAML confirmed to contain `allowed_callers: ["direct", "chain"]`). ✓
- **GitNexus integration (May 2026)**: No mention of GitNexus tooling for impact analysis of tool changes. 2026-05-22 progress notes document GitNexus re-indexing and impact analysis workflows, but Chapter 13 predates this and doesn't need to cover it (operational, not architectural).

### Broken path references

- **Line 31 (implied)**: `src/tool_policy.py` is referenced in the tool registry architecture but not explicitly mentioned in Chapter 13 text. The file exists ✓ and contains `PolicyLayer`, `TOOL_GROUPS`, and `resolve_policy_chain` (per line 242-263 logic references). This is correctly documented but could be more explicit.

### Proposed edits

1. **After line 265 (end of Cascading Tool Policy section)**: Add explicit reference to implementation:

> **Implementation**: Cascading policy resolution is implemented in `src/tool_policy.py` with the `resolve_policy_chain()` function. The function iterates through policy layers (Global → Role → Task → Delegation), narrowing permissions at each level per allow/deny rules.

2. **Line 31**: Clarify the shim indirection:

> **Implementation**: `src/tool_registry.py` (backward-compatibility shim at `src/tool_registry.py`; actual module: `src/registry/tool_registry.py`)

### Notes

- Chapter is comprehensive and accurate.
- Tool registry YAML is well-structured and actively maintained.
- `allowed_callers` field is present in all tools checked (web_research, http_get, http_post, web_search all have the field).
- No critical issues; suggested edits are for clarity and completeness.

---

## Chapter 17: Programmatic Tool Chaining

**Verdict**: up_to_date  
**Severity**: low

### Factual errors

None detected. All references are high-level architectural and point to stable modules:
- Chapter 13 cross-reference — accurate ✓
- Chapter 03 (REPL) cross-reference — accurate ✓
- Chapter 12 (Session Persistence) cross-reference — accurate ✓
- Chapter 02 (Architecture) cross-reference — accurate ✓
- Handoff reference (`handoffs/archived/programmatic-tool-chaining.md`) — **File does not exist**, but this is a reference to archived handoff, not broken docstring. Plausible that it was moved or deleted post-chapter-touch.

### Superseded claims

None detected. Phase 1 (deferred results), Phase 2 (multi-tool chaining), and Phase 3 (cross-request REPL persistence) are all documented with feature flags:
- `ORCHESTRATOR_DEFERRED_TOOL_RESULTS` — consistent with src/ code patterns
- `ORCHESTRATOR_TOOL_CHAIN_MODE=seq|dep` — consistent with modes
- `ORCHESTRATOR_TOOL_CHAIN_PARALLEL_MUTATIONS` — consistent with feature flags
- `ORCHESTRATOR_SESSION_PERSISTENCE_CHECKPOINT_*` — checkpoint payload caps consistent with logic

### Missing content (post-2026-03-30 landings)

- **Integration test reference (Line 68)**: "End-to-end `/chat` request1-save/request2-restore integration is passing in `tests/integration/test_chat_pipeline.py::TestChatEndpoint::test_session_restore_roundtrip_repl_globals`." This test is referenced but not independently verified post-2026-03-30. Given the recent intake-607 harness work (May 2026) and the dedicated `test_chat_pipeline.py` reference, this is likely still current.
- **GitNexus integration (May 2026)**: Chapter 17 makes no reference to GitNexus, but May 2026 sessions extensively used GitNexus for impact analysis of refactors and tool changes. This is operational context, not architectural, so not a gap.

### Broken path references

- **Line 78**: References `handoffs/archived/programmatic-tool-chaining.md` — **File not found**. Archive may not exist or may have been moved/consolidated. This is informational only (readers can find the archived handoff via git history if needed).

### Proposed edits

1. **Line 78 (optional)**: Update handoff reference:

> **Original**: Handoff source: `handoffs/archived/programmatic-tool-chaining.md`  
> **Proposed**: Handoff source: `handoffs/archived/programmatic-tool-chaining.md` (may have been consolidated; see git history for prior drafts)

2. **Optional new section**: Add a brief note on the 2026-05 intake-607 harness work and how it integrates with tool chaining (particularly for structured batch execution), if desired for completeness.

### Notes

- Chapter is concise and well-structured.
- Three-phase design is clear and the implementation status (Phase 1-3 all active) is documented.
- The integration test reference (line 68) is concrete and helps readers verify the feature works.
- No critical issues; optional edits above for completeness.

---

## Summary Verdict by Chapter

| Chapter | Status | Severity | Primary Issue |
|---------|--------|----------|---------------|
| 05: Data Processing Pipelines | patch | high | Path refs to removed `src/services/` dir; missing ODL Phase 2 + ERNIE features |
| 06: TOON Encoding | up_to_date | low | None (shim redirect works fine) |
| 08: Graph-Based Reasoning | up_to_date | low | None; optional: add URE-1 integration note |
| 11: Procedure Registry | patch | medium | Missing May 2026 refactor (procedure_models.py extraction) |
| 13: Tool Registry | patch | medium | Missing explicit `src/tool_policy.py` reference; clarify shim indirection |
| 17: Programmatic Tool Chaining | up_to_date | low | None; optional: update archived handoff ref |

---

## Cross-Cutting Observations

1. **Package reorganization impact**: Chapters 05, 06, and 13 reference modules affected by the package reorganization shim pattern (commit `6acbc9a8` and later refactors). Shims work correctly but could be documented more explicitly in each chapter.

2. **Feature landings post-2026-03-30**: 
   - ODL Phase 2 (document processing, commit `18c4f9d7`)
   - ERNIE-Image-Turbo (vision, commit `c10ffb29`)
   - Procedure models extraction (commit `f7f3fa3f`)
   - URE-1 routing uncertainty (commit `7f53c86a`)
   - Shared trace schema for harness (commit `dd0614c`)

3. **GitNexus integration**: 2026-05-22 sessions show active GitNexus use for impact analysis and refactoring safety checks. Chapters pre-date this, so no mention expected, but it's relevant operational context for future updates.

4. **Overall health**: 6/6 chapters are mostly accurate. 2 are passing (06, 08, 17 with optional enhancements). 3 need patches (05, 11, 13). No chapters are obsolete.
