# Non-Inference Backlog — Tasks Actionable Without Compute

**Status**: active
**Created**: 2026-04-11 (consolidated from audit of near-complete and active handoffs)
**Updated**: 2026-04-12 (tasks 7-18 completed; AP-14/AP-16 confirmed already done per routing index 2026-04-07; tasks 1-2/4-6 completed 2026-04-11)
**Priority**: MEDIUM
**Purpose**: Index of all remaining tasks across active handoffs that do NOT require model servers / inference compute. Can be tackled while compute is unavailable or occupied by bulk-inference-campaign Package D.

> **Notes**:
> - Claude Code integration Phase 1 removed (2026-04-11) — superseded by Hermes outer shell. See [claude-code-local-constellation-routing.md](claude-code-local-constellation-routing.md).
> - Root-archetype upstream tasks (linter testing, init-project.sh, README) removed — those are root-archetype repo work, not epyc-root. Tracked in [root-archetype-linter-templates-upstream.md](root-archetype-linter-templates-upstream.md).

---

## Task List (ordered by estimated impact)

### P0 — High impact, low effort

| # | Task | Source Handoff | Target Repo | Description | Effort |
|---|------|---------------|-------------|-------------|--------|
| ~~1~~ | ~~Brevity prompt upgrade (Action 12)~~ | ~~[reasoning-compression.md](reasoning-compression.md)~~ | ~~epyc-orchestrator~~ | ✅ DONE (Actions 12-15 complete, TALE eval done 2026-04-11). Static limits kept, TALE deferred. | — |

### P1 — Medium impact

| # | Task | Source Handoff | Target Repo | Description | Effort |
|---|------|---------------|-------------|-------------|--------|
| ~~2~~ | ~~REPL turn efficiency S3a~~ | ~~[repl-turn-efficiency.md](repl-turn-efficiency.md)~~ | ~~epyc-orchestrator~~ | ✅ DONE (2026-04-11). S3a contextual suggestions prototype implemented (`suggestions.py`, `_SuggestionsMixin`, 17 tests). Feature flag: `REPL_SUGGESTIONS` (default OFF). S4 A/B benchmark still needs inference. | — |
| 3 | Hermes outer shell Phase 2 completion | [hermes-outer-shell.md](hermes-outer-shell.md) | epyc-root | Phase 2 near-complete: skills done, streaming validated (Package E). Auth deferred. Remaining: E2E test of `x_disable_repl` + `x_max_escalation` with full graph (needs inference). LG Phase 3 now complete — escalation cap enforcement unblocked. | ~2h |
| ~~4~~ | ~~Dynamic stack Phase E design~~ | ~~[dynamic-stack-concurrency.md](dynamic-stack-concurrency.md)~~ | ~~epyc-orchestrator~~ | ✅ DONE (2026-04-11). DS-6 QuarterScheduler (health monitor, burst drain, idle tracking) + DS-7 stack templates (schema, loader, validator, default.yaml, --stack-profile CLI). 26 tests. Phase E autoresearch integration awaiting AR-3 results. | — |
| ~~5~~ | ~~Tool output compression monitoring~~ | ~~[tool-output-compression.md](tool-output-compression.md)~~ | ~~epyc-orchestrator~~ | ✅ DONE (2026-04-11). Compression metrics wired into TaskState, helpers.py, diagnostic JSONL, API response, seeding harness. Analysis script: `scripts/analysis/compression_stats.py`. | — |
| ~~6~~ | ~~LangGraph Phase 3 flag flips~~ | ~~[bulk-inference-campaign.md](bulk-inference-campaign.md)~~ | ~~epyc-orchestrator~~ | ✅ DONE (2026-04-11). All 7 per-node flags enabled in `orchestrator_stack.py`. Fixed append-field bug in `_run_via_langgraph` (role_history delta handling). 72 LG tests + 4495 unit tests pass. | — |

### P2 — Lower priority / future

| # | Task | Source Handoff | Target Repo | Description | Effort |
|---|------|---------------|-------------|-------------|--------|
| ~~7~~ | ~~Meta-harness documentation~~ | ~~[meta-harness-optimization.md](meta-harness-optimization.md)~~ | ~~epyc-orchestrator~~ | ✅ DONE (2026-04-12). Operator guide: `docs/guides/meta-harness-operator-guide.md` (6 sections: quick ref, Tier 1/2, safety, integration, checklist). | — |
| ~~8~~ | ~~Skill governance audit~~ | ~~[hermes-agent-index.md](hermes-agent-index.md) H-9~~ | ~~epyc-root~~ | ✅ DONE (2026-04-12). Verification gates (per-phase evidence) + anti-rationalization tables (10+6 rows) added to research-intake and agent-file-architecture SKILL.md. | — |
| ~~9~~ | ~~Autopilot short-term memory~~ | ~~[autopilot-continuous-optimization.md](autopilot-continuous-optimization.md) AP-22/23/24~~ | ~~epyc-orchestrator~~ | ✅ DONE (2026-04-12). `short_term_memory.py` + `self_criticism.py`. ShortTermMemory class (4-section markdown, token-budgeted). SelfCriticism (rule-based, no inference). 3 new JournalEntry fields. Wired into controller loop + prompt template. CLI: `reset-memory`. | — |
| ~~10~~ | ~~DSPy + GEPA installation~~ | ~~[autopilot-continuous-optimization.md](autopilot-continuous-optimization.md) AP-18~~ | ~~epyc-orchestrator~~ | ✅ DONE (2026-04-12). `dspy>=2.5.0` in pyproject.toml. `src/dspy_signatures/` package: FrontdoorClassifier, EscalationDecider, ModeSelector + config.py. 8 smoke tests. | — |
| ~~11~~ | ~~dspy.RLM infrastructure setup~~ | ~~[autopilot-continuous-optimization.md](autopilot-continuous-optimization.md) AP-25~~ | ~~epyc-orchestrator~~ | ✅ DONE (2026-04-12). `configure_rlm(main_lm_url, sub_lm_url)` in config.py. Coder as main LM, frontdoor as sub_lm. `test_connection()` health check. | — |
| ~~12~~ | ~~CF-P1: Validity timestamps~~ | ~~[context-folding-progressive.md](context-folding-progressive.md) CF-P1~~ | ~~epyc-orchestrator~~ | ✅ DONE (2026-04-12). `validity_timestamp` + `source_turn_ids` on ConsolidatedSegment. Populated at all 3 creation sites. Serialized in to_dict/from_dict. | — |
| ~~13~~ | ~~CF-P2: Supersession detection~~ | ~~[context-folding-progressive.md](context-folding-progressive.md) CF-P2~~ | ~~epyc-orchestrator~~ | ✅ DONE (2026-04-12). `check_supersession()` with 8 regex patterns. `superseded` + `superseded_by_turn` fields. | — |
| ~~14~~ | ~~CF-P3: Metadata filtering eval~~ | ~~[context-folding-progressive.md](context-folding-progressive.md) CF-P3~~ | ~~epyc-orchestrator~~ | ✅ DONE (2026-04-12). `topic_tags` field + `_extract_topic_tags()` (7 categories). Populated at all creation sites. | — |
| ~~15~~ | ~~CF-P4: Hybrid raw+derived design~~ | ~~[context-folding-progressive.md](context-folding-progressive.md) CF-P4~~ | ~~epyc-orchestrator~~ | ✅ DONE (2026-04-12). `is_raw` field on ConsolidatedSegment. Serialization ready. Raw window logic pending production wiring. | — |
| ~~16~~ | ~~MH-5: Agent Lightning traces~~ | ~~[meta-harness-optimization.md](meta-harness-optimization.md) MH-5~~ | ~~epyc-orchestrator~~ | ✅ DONE (2026-04-12). `telemetry.py`: TelemetryCollector with TransitionRecord, OTLP spans, JSONL export. Per-step: reasoning→execution→safety_gate. | — |
| ~~17~~ | ~~H-8: MemPalace MCP prototype~~ | ~~[hermes-agent-index.md](hermes-agent-index.md) H-8~~ | ~~epyc-root~~ | ✅ DONE (2026-04-12). `scripts/hermes/mempalace_setup.sh` setup script. MCP server config documented. | — |
| ~~18~~ | ~~S5: dspy.RLM REPL cross-reference~~ | ~~[repl-turn-efficiency.md](repl-turn-efficiency.md) S5~~ | ~~epyc-root~~ | ✅ DONE (2026-04-12). Pattern mapping (3 RLM patterns → REPL), 3 improvement proposals with effort estimates, priority ranking. | — |

---

## Completion Protocol

After completing any task:
1. Update the source handoff (checkbox + status)
2. Update this backlog (strikethrough completed items)
3. If the source handoff becomes fully complete, move it to `handoffs/completed/`
