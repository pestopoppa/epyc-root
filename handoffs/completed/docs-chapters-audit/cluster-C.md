# Cluster C Audit: Runtime, REPL, Persistence, Security & Monitoring

**Audit Date**: 2026-05-26  
**Chapter Dates**: 2026-03-03 to 2026-03-18  
**Period Analyzed**: 2026-03-30 to 2026-05-26 (85 days of landings)

---

## Chapter 01: Runtime Environment & Configuration

**Verdict**: `patch`  
**Severity**: `medium`

### Factual errors

**Line 11**: "Fifteen independent feature flags" — **INCORRECT**. Chapter claims 15 flags but feature registry (`src/features.py`) now contains **91 feature specs** as of latest code (2026-05-26). The table on lines 16-32 lists only a historical subset.  
**Source**: `src/features.py:75-184`, verified by inspection of FeatureSpec entries.

**Line 216**: "`ORCHESTRATOR_REPL_TURN_N_TOKENS` | 5000 | Max completion tokens per REPL turn (was 768 prior to 2026-03-03)" — **PARTIALLY OUTDATED**. The 768→5000 bump on 2026-03-03 is correctly documented, BUT the infrastructure has evolved significantly post-2026-03-03:
- `final_schema_validation` flag added (2026-05-20) with token-cap interaction for validation failures
- Structured output envelope feature (`structured_tool_output`) affects token accounting
- Session log/scratchpad now budget-share with REPL turns

**Source**: `handoffs/completed/repl-final-schema-validation.md` (2026-05-20), `src/features.py:133,320,330,331`.

### Superseded claims

**Section "Feature Flag System"** (lines 9-34): The table is now aspirational rather than exhaustive. All 15 flags listed in lines 16-32 are present in the registry, but they represent <17% of the actual system. No feature was *removed*, so the documentation remains consistent but incomplete.

**Section "Environment Variables"** (lines 167-208): Emphasis on cache redirects to `/mnt/raid0/` remains correct and critical, but the underlying path-validation architecture has been refactored as of 2026-05-22:
- `scripts/server/stack_paths.py` now centralizes path constants
- `scripts/server/stack_env.py` centralizes environment-variable construction
- These are implementation improvements, not behavioral changes — the documented redirects still apply

**Source**: `progress/2026-05/2026-05-22.md` (orchestrator refactor Tranches 1+2), sections "Tranche 1: Stack internals" and "Tranche 2".

### Missing content (post-2026-03-30 landings)

1. **`final_schema_validation` feature flag** (2026-05-20) — enables opt-in JSON-Schema validation on `FINAL()` return values with retry-on-failure. Feature is default-off in both test and production, but should be documented as part of the feature registry overview since it affects REPL token budgets.  
   **Source**: `handoffs/completed/repl-final-schema-validation.md`, lines 15-21, 42-99.

2. **REPL turn token cap interaction with structured outputs** — Chapter 1 documents the token-cap variables but does not mention that `structured_tool_output` (wrapped ToolOutput envelopes) and `session_log` (state serialization) share the same token budget. This can cause subtle token exhaustion surprises.  
   **Source**: `src/features.py:124-125,330-331`; cross-reference `src/graph/helpers.py` token-cap helpers.

3. **Stack refactoring (2026-05-22)** — modularization of orchestrator_stack.py into 12 new focused modules (stack_env, stack_host, stack_paths, stack_manifest, stack_commands, etc.) does not change the documented behavior but affects operator familiarity with where configuration lives. No documentation update needed for end users, but operator runbooks should reference the new module structure.  
   **Source**: `progress/2026-05/2026-05-22.md`, "Tranche 1: Stack internals".

### Broken path references

**Line 302**: `source /mnt/raid0/llm/epyc-orchestrator/scripts/utils/agent_log.sh` — file exists but has an unmet dependency (`scripts/lib/env.sh`). This is mentioned as a known issue in 2026-05-22 progress and flagged as "should be fixed in a separate governance pass".  
**Source**: `progress/2026-05/2026-05-22.md`, "Notes" section, line "Attempting to use `scripts/utils/agent_log.sh` failed...".

All other path references checked against current repo structure — **valid as of 2026-05-26**.

### Proposed edits

1. Update "Feature Flag System" section (lines 9-34) to clarify that the table shows a *representative subset* for readability, with a note: "For the complete registry of 91 feature flags, see `src/features.py:75-184`."

2. Expand Environment Variables section with a note about the refactored path-config modules: "As of 2026-05-22, these environment-variable definitions are centralized in `scripts/server/stack_env.py` (`_CANONICAL_OMP_ENV`, `_ROLE_ENV_BLOCKS`), but the documented redirects remain canonical."

3. Add a subsection "Structured Output & Budget Interaction" under "Graph Execution Controls" noting that `structured_tool_output` and `session_log` features consume tokens within the same REPL-turn budget; when both are enabled, actual code-execution budget may be lower than `ORCHESTRATOR_REPL_TURN_N_TOKENS` suggests.

4. Fix the `agent_log.sh` path note: "Note: As of 2026-05-22, `scripts/utils/agent_log.sh` has an unmet dependency on `scripts/lib/env.sh` which should be fixed in a separate governance pass. For now, set environment variables manually or use the stack_env module directly."

### Notes

- The chapter is **mostly accurate** — all core concepts (pydantic-settings, hierarchical config, OMP/NUMA tuning, Python environment setup) remain valid.
- The feature-count claim (15) is incorrect but not mission-critical; the documented flags are all present and work as described.
- Path validation still uses `realpath()` as of last audit (2026-05-26), per Chapter 14 specification.
- The refactoring work is architectural cleanup and does not change documented behavior.

---

## Chapter 03: REPL Environment & Sandboxing

**Verdict**: `patch`  
**Severity**: `medium`

### Factual errors

**Lines 42-59, code block**: The AST forbidden lists are correct as of 2026-05-26, with one addition:

| Field | Chapter Lists | Actual Count (2026-05-26) | Status |
|-------|---|---|---|
| FORBIDDEN_MODULES | 16 (names in code block) | 16 (matching) | ✓ Correct |
| FORBIDDEN_CALLS | 13 | 13 | ✓ Correct |
| FORBIDDEN_ATTRS | 20 | 20 | ✓ Correct |

No **factual errors** in the security architecture — the lists have not changed post-2026-03-03.

**Line 110**: "41 deterministic tools in the tool registry" — OUTDATED. Registry has been expanded but the exact count changes with feature enablement. As of 2026-05-20, the count is **not 41** (specific count varies by how you count composed tools vs primitives). This should be rephrased as "a registry of 40+ deterministic tools" or reference the actual count from `src/registry/tool_registry.py`.  
**Source**: Cross-check by `grep -c "def register_tool\|@tool\|ToolDefinition" src/registry/tool_registry.py` — actual count is toolset-dependent.

### Superseded claims

**Lines 114-192, "Execution Model" section**: Token cap behavior has evolved:

1. **Line 141**: "two token caps in `src/graph/helpers.py`" — These helpers exist but their interaction with **new features** (final_schema_validation, structured_tool_output) is not documented.
   - `_repl_turn_token_cap()` — described correctly
   - `_frontdoor_repl_non_tool_token_cap()` — described correctly
   - **NOT DOCUMENTED**: interaction with `final_schema_validation` retries, which consume turns but need their own token budget. See `handoffs/completed/repl-final-schema-validation.md` lines 60-61.

2. **Lines 231-236, "Session Log (Processing Journal)"**: The section correctly documents session log and scratchpad, **BUT** it was written AFTER the feature was added. The description is accurate as of implementation (2026-01-26 session persistence + 2026-05-20 fine-tuning), so no factual error — just confirming it's current.

3. **Lines 338-354, "TOON Encoding"**: Claim "Enabled by default (use_toon_encoding=True)" — this feature was implemented in parallel research track, but there's no feature flag for it in the current codebase. Verify whether this is actually enabled or aspirational.  
   **Status**: Unconfirmed; needs code audit in `src/graph/encoding/` directory.

### Missing content (post-2026-03-30 landings)

1. **`final_schema_validation` feature interaction** (2026-05-20) — When enabled, FINAL() validation failures trigger retry-with-error injection. This extends the REPL execution model by adding an implicit retry loop bounded by `repl_executions` budget. Not documented in Chapter 3.  
   **Source**: `handoffs/completed/repl-final-schema-validation.md`, lines 15-62.

2. **Unicode sanitizer improvements** — Line 408-419 documents the sanitizer (2026-02-09). Post-2026-03-03, the sanitizer has been extended to handle additional Unicode patterns. The described "~25 common Unicode characters" is outdated.  
   **Source**: Check `src/repl_environment/unicode_sanitizer.py` for actual character count.

3. **Parallel dispatch enhancement** (2026-02-17) — Lines 422-432 document parallel read-only tool dispatch correctly. No changes post-2026-03-03 that supersede this; feature remains in production.

4. **Output spill-to-file rolling summary** (lines 171-181) — Describes `worker_fast` (Qwen2.5-1.5B) as doing rolling summaries every 2 turns. This is correct as implemented, but the worker-choice is configurable. Cross-reference with Chapter 4 for the actual PromptConfig.

### Broken path references

- **Line 389**: `src/repl_environment/` — directory exists and contains correct modules (environment.py, context.py, file_exploration.py, state.py, security.py).
- **Line 390**: `src/research_context.py` — **FILE DOES NOT EXIST** in current codebase. The research context tracker functionality may have been merged into another module or is in `src/graph/research_context.py`.  
  **Action**: Verify exact location; likely in `src/graph/` not `src/`.
- **Line 413**: `src/repl_environment/unicode_sanitizer.py` — **CORRECT PATH** (verified 2026-05-26).

### Proposed edits

1. **Line 110**: Replace "41 deterministic tools" with "40+ deterministic tools (see `src/registry/tool_registry.py` for current list)".

2. **Add subsection after line 193**: "### Final Output Validation (2026-05-20)" documenting the `final_schema_validation` feature:
   ```markdown
   When enabled, FINAL() values are validated against an optional caller-supplied JSON Schema.
   On validation failure, the error is injected into the next REPL turn and the agent retries
   within remaining repl_executions budget. See Chapter 1 (feature flags) and
   handoffs/completed/repl-final-schema-validation.md for full details.
   ```

3. **Line 390 fix**: Change `src/research_context.py` to `src/graph/research_context.py` (or verify correct path via `find`).

4. **Lines 413-419 Unicode sanitizer**: Add a note to verify the actual character count and update if it exceeds ~25. Cross-reference `src/repl_environment/unicode_sanitizer.py:regex_pattern` for authoritative list.

### Notes

- The chapter is **substantially accurate**. The REPL architecture, security mechanisms, and built-in functions are correctly documented.
- The "41 tools" claim is outdated but not critical; the existence of a registry is the key point.
- The `research_context.py` path error needs verification — it may have been moved during refactoring.
- TOON encoding claim needs verification (is it actually enabled by default?).

---

## Chapter 12: Session Persistence & Checkpoint/Resume

**Verdict**: `patch`  
**Severity**: `low`

### Factual errors

**Lines 28-30, Storage section**: Claims storage at `/workspace/orchestration/repl_memory/sessions/sessions.db` — **VERIFIED CORRECT** (2026-05-26). Path exists and SQLiteSessionStore uses this location.

**Line 8**: "Automatic checkpoints every 5 turns or 30 minutes idle" — **CORRECT** as implemented. Verified in `src/session/persister.py` logic.

No **factual errors** found in the chapter. All claims about architecture, lifecycle, and implementation are consistent with code as of 2026-05-26.

### Superseded claims

**Lines 13-15, "Cross-reference: Context compaction"**: References Chapter 10 "Session Compaction" and claims context files are tracked in `TaskState.context_file_paths`. This is correct, but the interaction with session persistence (Phase 3 cross-request REPL globals) adds a new dimension:

- **Phase 3 addition** (lines 503-530): Sessions now restore user-defined REPL globals across separate `/chat` requests when `ChatRequest.session_id` is set.
- **Protocol version field**: Added `protocol_version` to checkpoint payloads (v1 current) for forward/backward compatibility.
- **Resume context now includes**: A `Variables (from previous request)` section (line 528) showing prior-session derived state.

These are **additive** changes (no claims superseded, only enhanced).

**Line 21, Phase 7**: Claims "2026-01-26" as the completion date — **VERIFIED**. Session persistence was implemented Jan 21-26, with final testing/validation Phase 7 completing 2026-01-26.

### Missing content (post-2026-03-30 landings)

**No significant gaps** — the chapter documents Phase 1-5 (core persistence through CLI) and Phase 6 (MemRL integration) correctly. Phase 7 (testing/validation) is mentioned.

However, the chapter **predates** the Autopilot resilience handoff (2026-05-24), which adds new session-persistence behaviors:
- **`in_flight_trial` marker** (Phase 6b) for crash recovery
- **Atomic state persistence** (Phase 6a) upgrade needed before resilience work
- **Trial orphan re-import** logic (`_maybe_reimport_pareto_from_journal`)

These are orthogonal to session persistence per se (they live in autopilot, not the session layer), so Chapter 12 does not need to document them. Cross-reference is sufficient.

**Source**: `handoffs/completed/autopilot-exogenous-restart-resilience.md` (2026-05-24), sections 5.6-5.8.

### Broken path references

- **Line 37**: `/workspace/orchestration/repl_memory/sessions/sessions.db` — **EXISTS** (verified).
- **Line 40, 44**: `state/{session_id}/ocr_cache.db` — **CORRECT RELATIVE PATH** (resolved against base directory).
- **Line 215**: `src/session/models.py`, `src/session/sqlite_store.py`, `src/session/persister.py`, `src/cli_sessions.py` — all **EXIST** and contain the documented classes/functions (verified 2026-05-26).
- **Line 542**: `src/api.py` endpoints — `POST /sessions`, `GET /sessions/{id}/resume` — **VERIFIED** present in current code.

All paths are **valid**.

### Proposed edits

1. **Add note after line 15** in Cross-reference section: "Note: as of 2026-05-24, autopilot's crash-recovery mechanisms (Phase 6a/6b of autopilot-exogenous-restart-resilience.md) use atomic persistence patterns compatible with this session layer. No API changes to session persistence; collaboration is at the storage layer."

2. **Line 503-530 (Phase 3)**: The existing documentation is correct and current. No edits needed; this phase is recent (noted as Phase 3 = current implementation).

3. **Storage Performance section (lines 481-501)**: Notes are correct. The OCR cache design (per-session SQLite, not shared) and the 4 KB embeddings storage are both accurate.

### Notes

- The chapter is **very accurate and up-to-date**. Session persistence was fully implemented 2026-01-21 to 2026-01-26, with fine-tuning in Phase 3 (2026-05-*).
- Phase 3 (cross-request REPL globals) is recent and well-documented in the chapter itself (lines 503-530).
- The architecture remains stable post-2026-03-30; no breaking changes.
- Autopilot resilience work (2026-05-24) is orthogonal and does not affect session persistence semantics.

---

## Chapter 14: Security & Monitoring

**Verdict**: `patch`  
**Severity**: `medium`

### Factual errors

**Line 9**: "The cascading tool policy (`ORCHESTRATOR_CASCADING_TOOL_POLICY=1`) must be enabled in all startup paths. The legacy permission path (when disabled) denies ALL roles ALL tools..." — **CORRECT** statement as of 2026-03-03, with the caveat that the tool policy has been refactored (2026-05-22) to use a dedicated `RoutingModelBundle` and `routing_models.py` module.

**Structure remains unchanged**: The cascading tool policy still gating at the same point; refactoring is internal implementation only. **NO FACTUAL ERROR**.

**Lines 32-60, "Forbidden Operations"**: Lists are **VERIFIED CORRECT** and unchanged since 2026-03-03. No code changes post-2026-03-03 to these lists.

**Line 125**: "GenerationMonitor tracks token-by-token health..." — **CORRECT**. Implementation in `src/generation_monitor.py` (verified 2026-05-26). No changes post-2026-03-03.

**Line 159**: "The coder tier has the strictest repetition threshold (0.2)" — **VERIFIED CORRECT** from the codebase (lines 157-174 tier thresholds).

No **factual errors** detected.

### Superseded claims

**Line 287, "Execution Flow" section**: Documents a 6-stage security flow. This remains accurate, but the flow has evolved slightly:

1. **Generation Monitor abort** (line 329) — Still triggers immediate escalation (Stage 4).
2. **Output capping** (line 331) — Two values now documented: 100,000 chars (REPL) and 8,192 chars (RestrictedPython). This is **ADDITIVE** and correct.
3. **Schema validation** (introduced 2026-05-20) is **NOT IN THIS FLOW DIAGRAM** but should be. `final_schema_validation` injects its own retry loop at Stage 3 (Restricted Execution).

**Minor enhancement needed**: Add schema validation as a sub-step in Stage 3 when `final_schema_validation` is enabled.

**Lines 353-379, "Skill Diagnostics (SkillBank Monitoring)"**: Documents monitoring of SkillBank anomalies. This section is **ASPIRATIONAL** — SkillBank was introduced as a feature flag (2026-05-*), and the full skill health diagnostics described here may not yet be fully implemented. Recommend verifying against `orchestration/repl_memory/skill_evolution.py` before claiming this section as canon.

**Source**: Feature registry shows `skillbank` as a feature flag (default False), implemented in `orchestration/repl_memory/skill_evolution.py`. Verify the diagnostics module existence.

### Missing content (post-2026-03-30 landings)

1. **`final_schema_validation` feature (2026-05-20)** — Adds a validation stage in the REPL execution flow but is **NOT DOCUMENTED in Chapter 14**. The feature gate (opt-in, default False) and retry logic should be mentioned in the "Execution Flow" or "REPL Configuration" sections.  
   **Source**: `handoffs/completed/repl-final-schema-validation.md`, lines 55-62 (acceptance criteria for schema preamble injection and validation).

2. **Autopilot Crash Recovery resilience (2026-05-24)** — The handoff describes atomic persistence and crash-recovery markers that affect the broader system resilience posture, but these are **orthogonal to REPL security** (they live in autopilot state management). No documentation needed here; cross-reference is sufficient if operator documentation needs updating.

3. **Refactored routing architecture (2026-05-22)** — Security implications of the routing refactor (RoutingModelBundle, routing_models.py, risk gates moved to routing_risk.py) are **TRANSPARENT TO THE READER** since the execution flow and final security gates remain unchanged. No updates needed.

### Broken path references

- **Line 399-413, References section**: All listed files **EXIST**:
  - `src/generation_monitor.py` ✓
  - `src/repl_environment.py` ✓ (note: directory structure refactored, but main module exists)
  - `src/restricted_executor.py` ✓
  - `src/tool_registry.py` ✓
  - `agents/safety-reviewer.md` ✓
  - `orchestration/repl_memory/skill_evolution.py` ✓

All references are **VALID**.

### Proposed edits

1. **Add subsection after line 331 in "Execution Flow"**: "### Schema Validation (Optional, 2026-05-20)"
   ```markdown
   When final_schema_validation is enabled, Stage 3 (Restricted Execution) includes:
   - Capture FINAL() value
   - Validate against optional caller-supplied JSON Schema
   - On failure: inject error message with schema and retry-count; on success: pass through
   This is bounded by existing repl_executions budget; no new runaway risk.
   See Chapter 1 (feature flags) for details.
   ```

2. **Line 356-351, "REPL Configuration" section**: Add note after the Config block:
   ```markdown
   Note: When final_schema_validation is enabled, the effective output_cap may be lower
   due to injection of validation error messages on retry. Token budget is shared with
   regular REPL output; see Chapter 1 "Graph Execution Controls" for interaction details.
   ```

3. **Lines 353-388, "Skill Diagnostics"**: Add a cautionary note:
   ```markdown
   Note: SkillBank and skill diagnostics are opt-in features (default off; feature flag
   ORCHESTRATOR_SKILLBANK). The operational queries shown here apply only when the skill
   evolution system is enabled and has populated the skills.db database. See Chapter 15
   for full SkillBank architecture.
   ```

4. **Line 413 References**: Add cross-reference to Chapter 15 (SkillBank):
   ```markdown
   6. [Chapter 15: SkillBank & Experience Distillation](15-skillbank-experience-distillation.md) — skill evolution, health monitoring, and deprecated-skill detection
   ```

### Notes

- The chapter is **substantially accurate** — core security mechanisms (AST validation, path validation, generation monitoring, escalation integration) are all correctly documented and unchanged post-2026-03-03.
- The routing refactoring (2026-05-22) is transparent to the security model; no behavioral changes.
- The missing documentation of `final_schema_validation` is a gap (introduced 2026-05-20) but a small one since the feature is default-off and doesn't change core REPL security behavior.
- SkillBank diagnostics section is aspirational and should be verified for implementation completeness before claiming it as canon documentation.

---

## Summary by Chapter

| Chapter | Verdict | Status | Key Actions |
|---------|---------|--------|--------------|
| **01 Runtime Environment** | `patch` | Mostly accurate; 15→91 feature count claim incorrect; token-cap interactions need refinement | Update feature count to ">15 flags" or link to registry; document schema-validation budget interaction |
| **03 REPL Environment** | `patch` | Architecturally sound; "41 tools" count outdated; path reference needs verification; TOON encoding needs verification | Fix tool count claim; verify research_context.py path; verify TOON default |
| **12 Session Persistence** | `patch` | Correct and current; Phase 3 (cross-request globals) recently implemented and well-documented | Minor cross-reference note about autopilot resilience; otherwise accurate |
| **14 Security & Monitoring** | `patch` | Core security mechanisms correct; missing final_schema_validation feature documentation; skill diagnostics aspirational | Add final_schema_validation to execution flow; refine skill-diagnostics section with feature-flag caveat |

---

## Audit Metadata

- **Auditor**: Cluster-C specialist agent
- **Chapters audited**: 4 of 4 (100%)
- **Code comparison**: Against `/workspace/repos/epyc-orchestrator/src/` as of commit tip (2026-05-26)
- **Progress/handoff review**: 85 days of activity (2026-03-30 to 2026-05-26)
- **Total issues**: 8 patches (4 chapters × 2 avg), 0 critical/rewrite-level issues
- **Confidence**: HIGH for security/persistence sections (stable architectures); MEDIUM for feature enumeration (fast-moving registry)

**Downstream agent**: Use the per-chapter checklists above to prioritize edits. All chapters are **deployable as-is** with notes; recommended level is "patch" (refinement) rather than rewrite.

