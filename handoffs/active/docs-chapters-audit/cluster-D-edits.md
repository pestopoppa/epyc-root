# Cluster D — Edit Pass Report

## Files modified

1. `/workspace/repos/epyc-orchestrator/docs/chapters/05-data-processing-pipelines.md`
   - Added a new top-level **Recent Additions (2026-04 / 2026-05)** section documenting:
     - ODL Phase 2 structured output (commit `18c4f9d7`, 2026-05-06) — `src/models/odl_structured.py`, `_extract_with_opendataloader_structured()` in `pdf_router.py`, `build_figure_prompt_with_context()` in `figure_analyzer.py`, `chunk_by_odl_headings()` in `document_chunker.py`, `ORCHESTRATOR_ODL_STRUCTURED` feature flag.
     - ERNIE-Image-Turbo image generation (commit `c10ffb29`, 2026-04) — `src/services/sd_server_client.py`, `src/services/image_generator.py`, `src/models/image.py`. Noted that this is image *generation* (distinct from the existing vision-analysis pipeline) and replaces ComfyUI.
   - Expanded the References section with `document_chunker.py`, `sd_server_client.py`, `image_generator.py`, `odl_structured.py`, `image.py`, and `db/models/vision.py`.

2. `/workspace/repos/epyc-orchestrator/docs/chapters/11-procedure-registry.md`
   - Added a `procedure_models.py` row to the Core Components table listing the seven re-exported names (`StepResult`, `ProcedureResult`, `ProcedureInput`, `ProcedureStep`, `Procedure`, `ProcedureValidationError`, `ProcedureExecutionError`).
   - Added a "Note (2026-05 refactor, Task J)" paragraph explaining the extraction and the backward-compatible re-export from `procedure_registry`.
   - Added `procedure_models.py` to the References section.

3. `/workspace/repos/epyc-orchestrator/docs/chapters/13-tool-registry.md`
   - Introduction now states explicitly that `src/tool_registry.py` is a backward-compat shim re-exporting `src/registry/tool_registry.py`, and that cascading policy lives in `src/tool_policy.py`.
   - Added an "Implementation" paragraph at the end of the Cascading Tool Policy section enumerating the exports of `src/tool_policy.py` (`PolicyLayer`, `TOOL_GROUPS`, `resolve_policy_chain`, `permissions_to_policy`) and the feature-flag fall-back behavior.
   - Updated References to point at `src/registry/tool_registry.py`, `src/tool_policy.py`, and the shim relationship.

## Edits deferred or skipped

- **Ch05 path rewrites (`src/services/X.py` → `src/X.py`)**: Deferred — **the audit was incorrect**. See "Audit items I disagreed with" below. No path changes were applied to Ch05.
- **Ch05 line 169 endpoint port (`http://localhost:8000/v1/vision/analyze`)**: Skipped pending verification — the audit speculates this is wrong but does not confirm. Chapter 05 itself documents 8086/8087 in a later table; the inline example may be a stale or stand-in URL. Did not change without confirmation.
- **GitNexus integration callout in Ch13 / Ch17**: Skipped — the audit itself classifies this as "operational, not architectural" and notes the chapters predate the workflow. Adding it would be gold-plating outside the chapters' scope.
- **Ch06 / Ch08 / Ch17 optional enhancements (verdict = up_to_date)**: Skipped per task instructions (skip unless clearly worthwhile). The optional items (TOON shim note, URE-1 routing mention, archived-handoff cross-ref) are minor and the up_to_date verdict already covers them.

## Audit items I disagreed with

- **Ch05, all claims that `src/services/` was deleted / files moved to `src/` root** (audit lines 15–19, 38–40, 46–47): **Verified false**. `/workspace/repos/epyc-orchestrator/src/services/` still exists and contains `pdf_router.py`, `document_chunker.py`, `figure_analyzer.py`, `archive_extractor.py`, `document_preprocessor.py`, `image_generator.py`, `sd_server_client.py`, `toon_encoder.py`, `worker_pool.py`, etc. The commit the audit cites (`f7f3fa3f`) is actually the Task-J **procedure-models** refactor in `orchestration/`, not a `src/services/` flattening. The chapter's existing paths are correct; rewriting them would introduce real bugs.
- **Ch05, `src/db/models/vision.py` "file not found"** (audit line 19): **Verified false**. File exists at `/workspace/repos/epyc-orchestrator/src/db/models/vision.py`. Kept the chapter's existing reference and added it to References explicitly.
- **Ch05, `src/services/figure_analyzer.py` "file not found"** (audit line 17): **Verified false**. File exists; in fact the ODL Phase 2 commit added `build_figure_prompt_with_context()` to it.
- **Ch11, "Line 25 references `src/services/document_preprocessor.py`"** (audit line 156): The chapter text does not contain that reference — the audit appears to have crossed wires with Ch05. No edit needed.

## Recommended new chapters or follow-ups

- **Image generation pipeline**: ERNIE-Image-Turbo + `sd-server` are now first-class enough (per the user's "managed services" guidance in MEMORY) that a short dedicated chapter or a sub-chapter under Ch05 may be warranted. For now it lives as a sub-section inside Ch05.
- **Re-audit Cluster D's path-claim methodology**: The Ch05 audit conflated the procedure-models extraction commit with a `src/services/` flattening that never happened. Future audits should `ls` the cited directory before flagging "file moved" — this prevents follow-on agents from applying destructive edits.
- **Package-reorganization shim map**: Ch13 hints at the `src/` → `src/registry/` shim. A short reference page enumerating every backward-compat shim (`src/tool_registry.py`, `src/toon_encoder.py`, others) and the canonical module each points at would be useful for new readers.

## Verification notes

- Confirmed `/workspace/repos/epyc-orchestrator/src/services/` exists with all files the audit claimed were moved (`ls` output recorded above).
- Confirmed `/workspace/repos/epyc-orchestrator/orchestration/procedure_models.py` exists (96 lines), docstring explicitly references the "2026-05-22 Task-J refactor" and the re-export pattern. `procedure_registry.py` imports the names from it (line 65).
- Confirmed `/workspace/repos/epyc-orchestrator/src/tool_registry.py` is indeed a one-line shim (`importlib` redirect to `src.registry.tool_registry`), and `src/registry/tool_registry.py` is the real implementation.
- Confirmed `/workspace/repos/epyc-orchestrator/src/tool_policy.py` exists and exports the cascading-policy primitives described in the chapter.
- Confirmed commits `18c4f9d7` (ODL Phase 2, dated 2026-05-06 in `git log`) and `c10ffb29` (ERNIE-Image-Turbo) exist with the file changes referenced in the new Ch05 section.
- All three modified files left uncommitted in the working tree (no `git add`/`git commit` performed per task instructions).
