# Tool Implementation

**Category**: `tool_implementation`
**Confidence**: verified
**Last compiled**: 2026-08-13 (a research-intake round on agent-fleet failure grading found an Apache-2.0 trace-annotation tool (AdaMAST) that runs against our own Claude Code / Codex transcripts with no success/failure oracle required, superseding an unlicensed predecessor (MAST) — see below; earlier 2026-08-12 note (the plane rule gets its first enforcement pass and a matching failure mode: a **two-valued health check cannot say "I cannot tell"**, and three separate supervisors were found resolving that ambiguity into a confident restart, a confident kill, or a confident green. Plus a registry probe moved from transport to semantics, and a stale-source check wired only into the mode nobody runs — see below; earlier 2026-08-10 note: the dashboard plane rule — data contracts with their subsystem, pages/nav/registry with the hub — **supersedes** the 2026-07-05 transport-rule boundary recorded below; plus the shared nav registry, the absence-is-loud rendering discipline, and the one-assembly-path rule)
**Sources**: 40 documents (2026-07-06 focused pass: AutoPilot dashboard regions-lock coherence and local planner provider hardening; 2026-07-05 full pass: project dashboard hub :8100 + recency/Blocked-routing fixes, AutoPilot dashboard live-tps repair, loops-and-dashboards audit, repo-readiness portfolio-L5 milestone + passive pickup launcher wiring, and 2026-07-04 tool-sentinel activation telemetry; prior 2026-07-03 corpus-augmented prompt lookup revalidation and AutoPilot planner-turn tool-use hint rendering, 2026-06-22 DCP context-assembler and stack-change guard cross-refs, 2026-06-20 OpenRouter subagent/Fusion server-tool contract patterns)

## Summary

Tool implementation in the EPYC orchestrator spans two dimensions: the REPL tools that coding agents use during task execution (file operations, grep, tests, shell commands), and meta-tooling that provides codebase intelligence to improve those agents' effectiveness. The most significant finding from the research is that **precomputed dependency graph intelligence can replace 5-8 exploratory REPL turns with a single context injection**, reducing both token cost and wall-clock time per coding task. This is not a theoretical claim -- GitNexus is installed, all 4 EPYC repos are indexed (epyc-orchestrator: 12,187 symbols, 33,049 edges, 686 clusters, 300 execution flows), and the integration path is specified down to line numbers in the orchestrator source.

GitNexus implements an 8-phase indexing pipeline: file/folder tree extraction, tree-sitter AST parsing across 13 languages, cross-file import resolution with path normalization, function call tracking with confidence scores (0.3-0.9), inheritance/interface mapping, Leiden community detection for functional clustering, entry point detection with execution flow tracing, and hybrid search indexing (BM25 + snowflake-arctic-embed-xs semantic embeddings + HNSW). The resulting KuzuDB property graph stores symbols, files, folders, clusters, and processes connected by typed edges (CONTAINS, IMPORTS, CALLS, EXTENDS, IMPLEMENTS, DEFINES, MEMBER_OF, STEP_IN). Seven MCP tools expose this graph: `query` (process-grouped hybrid search), `context` (360-degree symbol view), `impact` (blast radius analysis at 3 depth tiers), `detect_changes` (pre-commit impact mapping), `rename` (coordinated multi-file refactoring with dual-confidence), `cypher` (raw graph queries), and `list_repos`.

The key architectural insight from the integration assessment is that **context injection beats tool calling**. The model currently discovers dependencies through trial-and-error grep cycles, each costing a full REPL turn (~5-10s + tokens). A single GitNexus context query returns the same information in <100ms and zero tokens. For a function like `_execute_turn` (7 callers, 30+ callees, 3 process flows), this replaces 5-8 grep turns with one injected context block. The recommended integration path (Option 3) auto-injects codebase intelligence into the prompt at `helpers.py:1276-1327`, after `_auto_gather_context()` but before prompt build, behind a `gitnexus_context_injection` feature flag.

The broader tool ecosystem includes the LLM-Wiki pattern (intake-269, intake-277) for maintaining compiled knowledge bases accessible to coding agents -- now integrated as the project's own wiki system. AST-based code review (intake-330) achieves 8.2x token reduction over full-file review by analyzing semantic diffs rather than raw text. Production agent skill engineering patterns (intake-337) document workflows for building and testing agent skills in production environments.

A recurring 2026-07-05 finding cuts across the project's monitoring tool surfaces: **dashboards built as liveness instruments do not answer "is this loop producing value?"** The loops-and-dashboards audit found both the AutoPilot dashboard (:8000) and the new project hub (:8100) well-engineered on freshness/liveness but blind on outcome KPIs (promotions, keepable rate, wasted-eval rate) and offering zero steering affordances (28 GET endpoints, 0 POST). The remediation pattern — outcome KPI + escalation rule per telemetry addition — is now the design bar for any new monitoring surface. Separately, the project gained a second first-class dashboard tool: a dependency-free stdlib hub on :8100 (handoff kanban, git-seeded progress timeline, kernel-R&D results page) run as an `orchestrator_stack.py` managed service, with the boundary rule *live orchestrator in-process state → :8000; artifact/file-backed and project-wide → :8100*. **That transport-based boundary was superseded on 2026-08-10 by the plane rule** — data contracts live with their subsystem, pages/nav/registry live with the hub — see the 2026-08-10 compiled update at the end of this page.

A 2026-04-17 deep dive (intake-398) investigated Magika, Google's AI-powered content-type detector (ICSE 2025, Apache 2.0, PyPI magika 1.0.2). The model is a 1 MB shallow byte-embedding MLP — not a CNN as commonly described — using three 512-byte windows (beginning, middle, end), 128-dim byte embeddings, two dense GELU layers, and global max-pooling over 200+ content types. Per-class confidence thresholds are calibrated to fix precision at 99% and maximize recall; below-threshold predictions fall back to `txt` or `unknown`, which explains the 99% F1 headline while synthetic OOD classes score 84–94%. Live measurements on the EPYC host showed 225 ms cold-start (onnxruntime init) and 2.8 ms/file amortized, with a confirmed JSON→JSONL misclassification. The deep dive concluded Magika is **not_applicable** to EPYC: the document-ingestion pipeline operates on a five-format, already-labeled corpus (arXiv PDF, GitHub MD, HTML, HuggingFace MD, user-uploaded PDF) where format is declared by URL pattern, HTTP Content-Type, or extension. No existing pipeline stage requires generic filetype detection, and adding ~80 MB of onnxruntime dependencies for zero measurable accuracy gain is pure negative value. Magika is worth reconsidering only if the pipeline begins ingesting truly arbitrary binary corpora.

### New Findings (2026-07-16 — harness cooperation is now part of the tool-surface contract)

- **Tool-output compression still lives at the orchestrator boundary, but its end-to-end value now depends on the harness not competing with its own compaction layer.** The new harness-selection index makes the boundary explicit: candidate user-facing harnesses can run their own prompt-cache, compaction, and subagent-spawn logic, which can partially negate Orch-side tool-output compression unless they defer. That is an implementation concern because it changes how much of the compression win survives to the model. Sources: [tool-output-compression.md](../handoffs/active/tool-output-compression.md), [harness-selection-and-integration.md](../handoffs/active/harness-selection-and-integration.md), [hermes-outer-shell.md](../handoffs/active/hermes-outer-shell.md), [progress 2026-07-16](../progress/2026-07/2026-07-16.md).

- **The MCP wrapper makes compression a reusable tool surface, not just a hook-side experiment.** Phase 4 now has a direct MCP-tool wrapper path for compression, which means the implementation can be consumed by tool-aware harnesses as a first-class tool rather than only as a shell hook. That keeps the compression path compatible with an open harness that defers to the Orch's policy layer. Sources: [tool-output-compression.md](../handoffs/active/tool-output-compression.md), [harness-selection-and-integration.md](../handoffs/active/harness-selection-and-integration.md).

## Key Findings

### New (2026-07-03, corpus-augmented prompt lookup revalidation)

- **Tool-use exploration now has a planner-visible control surface instead of relying on downstream handlers.** The existing tool-use sentinel lane, native-tool schema work, and REPL/delegate contracts were not enough by themselves because the AutoPilot planner prompt was not refreshed from StrategyStore each turn. Orchestrator `4b9e1fd0` adds a bounded `StrategyStore Planner Hints` block to the controller prompt when `AUTOPILOT_PLANNER_HINTS=1`; live smoke over the current store puts `v6 tool activation` and `tool-use sentinel lane` first, with identifiers such as `tools`, `repl`, `react_mode`, and `tool_use_sentinel_lane`. This makes tool-use exploration schedulable by the planner in the live daemon after the 2026-07-03 current-code restart, while keeping archival/completion writes operator-governed. Sources: [tool-use eval contract](../handoffs/active/tool-use-eval-contract.md), [autopilot continuous optimization](../handoffs/active/autopilot-continuous-optimization.md), [progress 2026-07-03](../progress/2026-07/2026-07-03.md).
- **The 651G local code corpus is not dead weight yet, but online benefit is unproven.** A10 repaired the high-blast-radius `build_corpus_context()` path by loading corpus retrieval settings through the live registry loader, requiring both global corpus enablement and per-role `acceleration.corpus_retrieval=true`, and emitting structured `corpus_retrieval` log evidence for disabled, injected, slow-query, and error outcomes. Current live parsing enables prompt-stuffing for `frontdoor` and `coder_escalation`; `worker_general`/architect/long-context roles remain disabled, and native llama prompt lookup/static-cache flags are still off. A forced offline probe against `/mnt/raid0/llm/cache/corpus/v3_sharded` returned `6/6` successful queries, `17` snippets, average `2.83` snippets/query, p50 `0.331 ms`, p95 `298.016 ms`, and `usable_for_online_prompt_injection=true` under the 5s health threshold; the later preflight `corpus_quality_preflight_20260704T164539Z.json` injected `6/6` prompts with `3` snippets each. This proves the index is alive and searchable, not that it improves code writing. The next clean-window A/B must test `coder_escalation` and `worker_general` if the worker still handles code/refactor tasks. `scripts/corpus/build_static_ngram_cache.py` can now plan bounded static-cache builds around llama.cpp's `llama-lookup-create`/`llama-lookup-merge`, but large corpus-derived cache builds should wait for code-writing value evidence or explicit operator approval for a throughput-only experiment. Sources: [corpus lookup handoff](../handoffs/active/corpus-augmented-prompt-lookup-revalidation.md), [progress 2026-07-03](../progress/2026-07/2026-07-03.md), `/mnt/raid0/llm/epyc-orchestrator/orchestration/reports/corpus_health_probe_20260703T112521Z.json`.

### New (2026-07-05, Fable week-run harness repairs)

- **The current Fable run resumed on a repaired harness, with failure surfaces narrowed to replayable candidate generation rather than tool plumbing.** Orchestrator `4400df02` constrains broad legacy `numeric_trial` blacklists so stale unscoped rows no longer exhaust W8 candidate-generation surfaces; `8be68732` fixes the forced-REPL tool-sentinel prompt contract so sentinel tasks ask for executable `TOOL("get_eval_secret", ...)` code instead of contradictory plain-text / no-code output; `6a0d60af` normalizes planner-friendly numeric params like `{"keep_ratio": 0.5}` to the applicator's `{"kv.keep_ratio": 0.5}`; and `854eff06` converts unreplayable W8 deferrals into numeric-trial fallback actions unless a sequential due-action owns the turn. Live state after `854eff06`: PID `2935890` is still on forced baseline-reference trial `1185` and correctly reports `code_stale=true` until a boundary restart activates the guard. Sources: [progress 2026-07-05](../progress/2026-07/2026-07-05.md), [autopilot-continuous-optimization.md](../handoffs/active/autopilot-continuous-optimization.md), [tool-use-eval-contract.md](../handoffs/active/tool-use-eval-contract.md).
- **Tool use is now a real prompt-shape contract, not a text-only aspiration.** The live tool-sentinel lane still depends on the REPL path, but the prompt now requires executable tool calls, and the structured tool-output envelope is already in place. That keeps the remaining work focused on driving a nonzero `total_tool_calls` signal in a real trial rather than debugging schema plumbing. Sources: [tool-use-eval-contract.md](../handoffs/active/tool-use-eval-contract.md), [progress 2026-07-05](../progress/2026-07/2026-07-05.md).

### New (2026-07-14, gate-3 tool telemetry and fail-closed web research)

- **The tool sentinel lane is now validated against a hard pass/fail boundary rather than optimistic logging.** Gate-3 hard-passed against the orchestrator PID under test: `get_eval_secret` returned `7/7` success rows, no-tool isolation passed, and the API reload plus authority-daemon recycle kept the live lane on `AUTOPILOT_TOOL_SENTINELS=1`. That confirms the implementation contract is active in the running loop, not just in the prompt template. Sources: [orchestration robustness audit](../handoffs/active/orchestration-robustness-audit-2026-07-11.md), [Progress 2026-07-14](../progress/2026-07/2026-07-14.md).

- **`web_research` now fails closed on bad evidence instead of surfacing a soft success.** The sentinel path reports `web_research result failed (search_failed)` for the degraded search lane, while a forced probe after reload still recovered a relevant Python.org result through DDG fallback and preserved `success:true`. That is a better tool contract: search quality is explicit, fallback is explicit, and a poisoned search no longer counts as a successful completion. Sources: [orchestration robustness audit](../handoffs/active/orchestration-robustness-audit-2026-07-11.md), [HALO Spike Results](../research/deep-dives/halo-spike-results-2026-07-14.md).
- **The tool-sentinel lane went from env-gated code to verified-live activation over 2026-07-04/05, with a dedicated telemetry gate proving the contract end-to-end.** Activation required syncing the env across BOTH the AutoPilot daemon and the API workers — a strict Fable report caught the split state (`api_env_missing_AUTOPILOT_TOOL_SENTINELS`) and an API-only reload under the `gate3-tool-telemetry` profile closed it; all sampled parent/worker processes now carry `AUTOPILOT_TOOL_SENTINELS=1` + `ORCHESTRATOR_STRUCTURED_TOOL_OUTPUT=1`. The hard verdict from `scripts/autopilot/gate3_tool_telemetry.py` was PASS: `get_eval_secret` counted 7-8 tool calls across runs, all secret-timing rows succeeded, and the no-tool isolation request inherited zero tools (`tools_called=[]`). Tool-use regressions are now visible to the safety gate as a suite signal — trials `1151`/`1154` were reverted partly on `suite_tool_use` regressions of `-3.000`. A soft `web_research` probe passed telemetry but exposed a separate post-tool architect formatting error (`AttributeError: 'str' object has no attribute 'output'`), tracked apart from the hard tool contract. Orchestrator `c7590be6` also folds journaled tool total/rate/name buckets into default-off BSV observe signatures with `process_signal_sources` provenance. Sources: [progress 2026-07-04](../progress/2026-07/2026-07-04.md), [progress 2026-07-05](../progress/2026-07/2026-07-05.md), [tool-use-eval-contract.md](../handoffs/active/tool-use-eval-contract.md).

### New (2026-07-05, project dashboard hub :8100 + AutoPilot dashboard live-tps repair + loops-and-dashboards audit)

> **Review flag (project-wiki writer-evidence policy):** model-compiled, not adopted until human or measured review. Test counts and endpoint behavior are verified (unit tests, live endpoint checks); throughput/backlog/spend figures are journal/log-derived OBSERVATIONS with no protocol id.

- **epyc-root now owns a project dashboard hub — a dependency-free stdlib web server on :8100, managed via `orchestrator_stack.py`.** Boundary decision: anything needing live orchestrator in-process state/SSE stays on the orchestrator dashboard (:8000); artifact/file-backed, project-wide views go to the hub. Pages shipped: a handoff kanban (Active/Blocked/Completed/Archived from `handoffs/` directory state, live 30s-TTL scan, card modal with rendered checklist), a git-history progress timeline (`scripts/handoffs/build_handoff_timeline.py` reconstructs from `git log -M -p`, preferring in-file self-reported dates over commit dates so charts reach true origin 2026-01-05 instead of bunching at the 2026-02-25 monorepo-split import), an outstanding-backlog snapshot (132 handoffs / 488 open tasks at build time), and a kernel-R&D Phase-3 page (`/kernel`) that renders the MI210 loop's export contract with OBSERVATION discipline front and center — the hub only *reads* `kernel_store.py export` JSON owned by `epyc-inference-research`. Two adversarial-review workflows (18+9 agents) confirmed 15 defects, all fixed with regression tests (32 initial + 18 follow-on = 50 stdlib-unittest tests passing). Sources: [progress 2026-07-05-dashboard-hub](../progress/2026-07/2026-07-05-dashboard-hub.md), [loops-and-dashboards-audit-2026-07-05.md](../handoffs/active/loops-and-dashboards-audit-2026-07-05.md).
- **"The board feels stale" was a sort-key artifact, not a broken hook — and the fix defines a reusable card-recency pattern.** The post-commit hook and 45s polling were healthy; cards *looked* frozen because Active/Blocked columns sorted by frontmatter `Updated`, which 85 of 134 active handoffs lack. The fix computes per-card `activity = max(frontmatter updated, git last-touch from a timeline-emitted file_activity map, mtime-if-git-dirty) → created`, labelled by `activity_source ∈ {updated,git,wip,created}`; 133/134 active cards now date and sort by real git activity. Blocked-column routing was similarly too literal (only `Status:` *starting with* "BLOCKED" matched); the widened `_is_blocked_status()` with negative guards ("does not block", "blocker … resolved") moved 5 genuinely blocked/parked/pending-operator handoffs out of Active while trap cases stayed put. Hook installation now wires `post-commit` + `post-merge` + `post-checkout` idempotently — but `.git/hooks` is not version-controlled, so fresh clones must run `install_timeline_hook.sh` (open item: wire into `clone-repos.sh`/session init). 50/50 tests pass including against the merged-into-main worktree. Sources: [progress 2026-07-05-dashboard-recency](../progress/2026-07/2026-07-05-dashboard-recency-and-blocked-routing.md), [progress 2026-07-05-dashboard-hub](../progress/2026-07/2026-07-05-dashboard-hub.md).
- **Three AutoPilot-dashboard regressions (frozen live stream, missing completed-task tok/s, no live per-role tok/s) all traced to ONE origin: the incomplete migration off v6's gutted `/slots`.** After the 2026-06-26 v6 cutover dropped `prompt`/`content` from `/slots`, the dashboard's live features half-moved to the structured tap: live tap rows never opened the per-token SSE and re-rendered from a 1 MB tail parse of a ~400 MB tap file (a single request's chunks slide out of the window — 20 requests observed at `response_len=0` despite 1507 chunks); `scan_orchestrator_tasks` dropped `tokens_generated`/`generation_ms` present in every `task_completed` event; and `topology_activity` derived rate only from terminal `timings` events, so no mid-generation rate existed. Fixes: chunk-span rate `tps_live = (chunk_count-1)/(last_ts-first_ts)` for running requests (self-correcting under tail truncation), carrying token/timing fields through terminal events, per-role `live_tps` aggregation, and prefix-dispatching `tap_` ids in `task_stream` to a reverse-grep resolver that recovers the full growing body (verified: 2438-char body recovered where the SSE previously idle-timed-out). Deployed via `orchestrator_stack.py reload orchestrator`. Root causes were confirmed by primitive data observation + a 4-agent adversarial verification workflow before any edit. Sources: [progress 2026-07-05-orchestrator-dashboard-live-tps](../progress/2026-07/2026-07-05-orchestrator-dashboard-live-tps.md), memory `project_v6_slots_no_prompt_content`.
- **A progress metric is only as live as the discipline feeding it: the hub's backlog % counts checkbox state only, and a full day of agent work (90+ handoff commits across 5+ sessions) moved it zero because every session recorded progress as prose, not `[ ]`→`[x]` flips.** Diagnosed 2026-07-05 evening (second consecutive false "board is stale" report — the board was live both times; the *input signal* was missing). Two-sided fix (epyc-root `ea561387`): instrument side — the board payload now carries `activity_today` (handoff commits / files touched / boxes checked / boxes added since local midnight, from `git log --since=midnight -p`) and the banner names the failure mode explicitly ("prose-only updates; no checkboxes flipped, so the % above cannot move"); discipline side — a required checklist-sync gate in `/wrap-up` (both Claude and Codex skill copies) plus an always-loaded CLAUDE.md rule that binds autonomous checkpoint commits, with a pre-commit verification count (`git diff HEAD -- handoffs/ | grep -cE '^\+\s*[-*] \[[xX]\]'`). Design lesson for any artifact-derived KPI: when the metric can silently starve, surface the *input-signal rate* next to the metric and name the starved state in the UI, rather than letting "frozen" and "no input" render identically. Sources: [progress 2026-07-05-dashboard-hub](../progress/2026-07/2026-07-05-dashboard-hub.md), [loops-and-dashboards-audit-2026-07-05.md](../handoffs/active/loops-and-dashboards-audit-2026-07-05.md).
- **Static dashboard explainers should not be toggled from cross-cadence live counters.** The topology panel explainer flicker was not a DOM rebuild bug: a static `#inflight-explainer` sibling was being shown/hidden every poll from `slotsActive` and `inflight.length`, two fields sourced from different producers at different cadences. The fix was deliberately simple: after the first snapshot, leave the small explanatory legend visible rather than debouncing an incoherent same-instant comparison. General rule: when UI text explains panel semantics rather than live state, render it as stable chrome; reserve live counter comparisons for explicitly stale-badged data rows. Source: [2026-07-05-dashboard-topology-explainer-flicker.md](../progress/2026-07/2026-07-05-dashboard-topology-explainer-flicker.md).
- **The loops-and-dashboards audit's central tooling lesson: both dashboards are liveness instruments, not value instruments — "any fix that adds telemetry without adding an outcome KPI + escalation rule deepens the pathology."** Audit-observed dashboard defects: :8000 computed `baseline_promotions` server-side but never rendered them; exposed 28 GET / 0 POST endpoints (no pause/rewind/promote from the UI — steering lives in shell tribal knowledge); read only the frozen base journal shard for trial-duration panels; still executed dead v6 `/slots` prompt/content reads at 2 Hz; left 5 rendered panels outside the freshness registry; and wrapped GEPA/Pareto updates in bare `catch{}` so frozen panels masqueraded as data. :8100's kernel freshness badge classified on export-file mtime (a cron re-export reads "fresh" forever — should classify on `max(runs[].ts)`), and the backlog banner is "a count, not a steering instrument." Phase-1 fixes already landed include outcome KPIs on the dashboard API/frontend (`45c118b8`: keepable rate, wasted-eval rate, learning-excluded rate, current-code health) and journal-derived outcome blockers in `phase_health_report.py` (`18c71bcc`, advisory by default, `--require-outcome-progress` strict). Remaining tail: hub outcome card, steering affordances (guarded POST or copy-exact command chips), freshness-registry completion. Sources: [loops-and-dashboards-audit-2026-07-05.md](../handoffs/active/loops-and-dashboards-audit-2026-07-05.md), [progress 2026-07-05](../progress/2026-07/2026-07-05.md).
- **Planner provider tooling gained a local tier and an enforced spend breaker** — `7036630c` adds an OpenAI-compatible `LocalPlannerProvider` (calls the orchestrator `/v1/chat/completions` with `x_orchestrator_role` + `x_disable_repl=true`; launcher default `AUTOPILOT_PLANNER_PRIMARY=local_ingest`), and `03dfac45` turns the previously status-string-only planner budget into a circuit breaker that forces local-local planning when projected spend exceeds threshold. This closes the open-source-only-policy gap where routine trial drafts went to metered cloud models. Full gate/statistics remediation detail belongs to the AutoPilot page; noted here as a tool-provider surface change. Sources: [loops-and-dashboards-audit-2026-07-05.md](../handoffs/active/loops-and-dashboards-audit-2026-07-05.md).

### New (2026-07-06, dashboard coherence and local planner provider contract)

- **The regions-lock panel must distinguish ownership from inference activity.** The dashboard coherence regression was not only a stale-render problem: the frontend collapsed real `/proc` CPU-region holders, live structured tap requests, tap-inferred activity, and slot-inferred activity into one `activeLockCount`, then labelled the summary as `/proc holder instance(s)`. Orchestrator `ea47f672` separates the counts and wording: the lock panel now reports real `/proc` holders separately from live tap requests, tap-inferred active streams, and slot-inferred active instances. This reconciles the panel with Live Inference without pretending every active request holds a process lock. Sources: [loops-and-dashboards audit](../handoffs/active/loops-and-dashboards-audit-2026-07-05.md), [progress 2026-07-06](../progress/2026-07/2026-07-06.md).
- **Local planner provider contracts now apply to critique calls, not just drafts.** The first frontdoor-draft canary produced clean action JSON, but local ingest critique ignored the existing critique prompt's JSON-only instruction and emitted long prose. Orchestrator `8464986e` adds a local critique wrapper that requires exactly one `json:autopilot_critique` fenced block and changes the default local critic to `local_worker`, while leaving Claude as fallback. This keeps the fully-local path testable without removing the independent critic escape hatch. Sources: [loops-and-dashboards audit](../handoffs/active/loops-and-dashboards-audit-2026-07-05.md), [progress 2026-07-06](../progress/2026-07/2026-07-06.md).

### New (2026-07-06, tool-use smoke follow-up)

- **Tool-use activation is env-ready, but the current local REPL behavior still fails on executable tool turns.** A five-way parallel Gate-3 smoke on PID `981677` confirmed the orchestrator API still carries `AUTOPILOT_TOOL_SENTINELS=1` and `ORCHESTRATOR_STRUCTURED_TOOL_OUTPUT=1`, and the batch fan-out itself worked, but all five sentinel requests still returned repeated no-progress nudges / comment-only REPL output with zero `get_eval_secret` calls. The no-tool isolation request remained clean, while the soft `web_research` probe bucketed as `INFRA_FAIL` for the same model-behavior reason. The remaining blocker is therefore prompt/runtime execution quality on the REPL path, not flag wiring. Sources: [tool-use-eval-contract.md](../handoffs/active/tool-use-eval-contract.md), [progress 2026-07-06](../progress/2026-07/2026-07-06.md).

### New (2026-07-05, repo-readiness scorer: portfolio Autonomous/L5, passive pickup wired into launcher)

- **The deterministic repo-readiness scorer drove the portfolio from Documented (L2, 2026-06-13) to Autonomous (L5, 2026-07-03/05) in three weeks, with the remediation queue shrinking 49 → 24 → 13 open items.** Current 2026-07-05 artifacts: `epyc-root`, `epyc-orchestrator`, and `epyc-inference-research` are Autonomous/L5; `epyc-llama` remains Standardized/L3 with six blocking L4 workflow-surface gaps (`incremental_validation`, `generated_docs`, `health_automation`, `analysis_reports`, `security_audit`, `replay_analysis`) — all P0 in the queue. The closeouts were real maintained surfaces, not placeholders: per-repo `make security-check` tracked-file audits, generated-docs/analysis-report index lanes with `--check` staleness failure, no-inference health checks, exploit-path-gated security-review skills, and the root `scripts/validate/candidate_eval_gate.sh` bundling validators + PII fixture eval + scorer tests as `L5.auto_eval_gates`. Sources: [repo-readiness-scorer.md](../handoffs/active/repo-readiness-scorer.md), [repo-readiness-2026-07-05](../progress/2026-07/repo-readiness-2026-07-05.md), [repo-readiness-remediation-2026-07-05](../progress/2026-07/repo-readiness-remediation-2026-07-05.md).
- **The authority boundary held under pressure — twice.** A parallel audit *rejected* crediting the passive repo-readiness pickup artifact as `L5.self_optimizing_loop` (a scorer test now pins that guardrail), keeping the honest gap open for root and llama. And the live-consumption path stays explicitly non-authoritative: `start_fable_authority_daemon.py` now injects the newest passive pickup JSON into future AutoPilot launches unless `AUTOPILOT_REPO_READINESS_PICKUP` overrides, but the artifact carries `mode=advisory_only` / `authority_gate=false` and the default-off planner bridge renders it as planning context that cannot override owning handoffs, GitNexus impact checks, or measurement gates. The design lesson generalizes: a deterministic scorer can *seed* an agent improvement queue, but promotion to authority requires a separate protocol and operator gate. Sources: [repo-readiness-scorer.md](../handoffs/active/repo-readiness-scorer.md), [progress 2026-07-05](../progress/2026-07/2026-07-05.md).
- **Operational blocker recorded: the `epyc-llama` GitNexus index is broken** — rebuild attempts repeatedly timed out on large backend translation units then crashed in the Node/NAPI parser. Per the handoff, do not edit the llama fork until the index is repaired (likely by narrowing `.gitnexusignore` for parser-hostile generated/backend files); this directly blocks the six P0 llama remediation items. Source: [repo-readiness-scorer.md](../handoffs/active/repo-readiness-scorer.md).


### New (2026-06-22, context-assembler + stack-change guard tooling cross-refs)

- **Two governance/assembly tools advanced.** The DCP context-assembler (`src/context_assembly.py`: budget-bounded iterative file discovery → AST codemap → token verify → slicing, with injectable ColGREP + file-reader backends) reached its first live A/B and recorded `hold` on a latency regression; see [context-management.md](context-management.md). The stack-change guard validator now enforces 27 rules across 13 consumer surfaces via the canonical `stack_change_pipeline.py check --run-promotion-gate` (174 tests pass, no waivers); see [knowledge-management.md](knowledge-management.md). Both are inference-free. Sources: [delegation-context-preassembly.md](../handoffs/active/delegation-context-preassembly.md), [model-stack-single-source-update-pipeline.md](../handoffs/active/model-stack-single-source-update-pipeline.md), [standardized-stack-update-pipeline-finalization.md](../handoffs/active/standardized-stack-update-pipeline-finalization.md).

- **Session closeout is now codified as a local Codex skill.** The `/workspace/.claude/commands/wrap-up.md` routine has a Codex skill mirror at `/home/node/.codex/skills/wrap-up`: update progress reports, handoffs, handoff indices, relevant docs, README freshness warnings, wiki compilation, agent log, and per-repo local commits, then report hashes for manual push. The project command remains the source of truth when present; the skill makes "wrap up", "checkpoint", and `/wrap-up` phrasing durable across Codex sessions. [progress 2026-05-27](../progress/2026-05/2026-05-27.md)
- **GitNexus remains the required pre-edit blast-radius tool, but markdown/log/progress targets are usually not indexed symbols.** During the 2026-05-27 wrap-up, `gitnexus impact` on documentation targets returned `UNKNOWN` / `0 impacted`; that is expected for unindexed prose surfaces. For code changes, high/critical impact still requires explicit warning and scoping before edits. [progress 2026-05-27](../progress/2026-05/2026-05-27.md)
- **GitNexus provides single-query answers to dependency questions that currently cost 5-8 REPL turns.** When the coder modifies `_execute_turn()` in helpers.py, it has no awareness that 7 node classes call it, that it depends on 15+ helper functions, or that changing its return signature would break the entire graph. The `impact` tool answers this in one call with confidence-scored edges. Import-resolved calls score 0.90, same-file calls 0.85, fuzzy single-match 0.50, fuzzy multi-match 0.30. Tools default to `minConfidence=0.7` to exclude guesses, letting the agent distinguish "definitely calls X" from "might call X." [gitnexus-codebase-intelligence.md](../research/deep-dives/gitnexus-codebase-intelligence.md)

- **Context injection is strictly superior to tool calling for dependency awareness.** Five integration options were assessed, ranked by ROI: (1) MCP tool server -- zero Python code, 20 lines of config; (2) REPL tool wrappers -- 120 lines, follows existing registry pattern; (3) auto-inject context into prompts -- 150 lines, highest impact on code quality, feature-flagged; (4) pre-commit validation -- 50 lines, safety net for blast radius; (5) KuzuDB direct Python queries -- 200 lines, sub-millisecond queries, no Node.js runtime dependency. The recommended order is 2, then 3, then 4, then 5. Option 3 (auto-injection) represents the highest value because the model gets dependency context before it writes code, matching the "front-load intelligence" pattern analogous to prefix caching. [gitnexus-orchestrator-integration.md](../research/deep-dives/gitnexus-orchestrator-integration.md)

- **Confidence-scored edges enable graduated trust in refactoring.** The `rename` tool distinguishes graph-resolved edits (high confidence, apply automatically) from AST-search edits (lower confidence, flag for review). This graduated trust model maps directly to the orchestrator's cascading tool policy, where different trust levels govern different tool categories. [gitnexus-codebase-intelligence.md](../research/deep-dives/gitnexus-codebase-intelligence.md)

- **Leiden clustering on the call graph produces functional areas that can auto-generate skill files.** Each cluster gets cohesion and separability scores plus member symbols ranked by call density. The `--skills` flag generates SKILL.md files per cluster -- targeted context per functional area. This could replace manual agent role descriptions with data-driven ones that update automatically as code evolves. [gitnexus-codebase-intelligence.md](../research/deep-dives/gitnexus-codebase-intelligence.md)

- **Hybrid search (BM25 + semantic + RRF) with process grouping organizes results by execution flow.** The agent sees "MainREPLLoop: route -> validate -> fetchUser -> createSession" instead of 4 disconnected functions. Reciprocal Rank Fusion (k=60) merges BM25 keyword and semantic embedding results, then 1-hop graph expansion adds CALLS/IMPORTS neighbors. This pattern is directly applicable to the episodic memory retrieval, which currently uses FAISS alone -- adding BM25 lexical matching would improve retrieval for exact function/class name queries. [gitnexus-codebase-intelligence.md](../research/deep-dives/gitnexus-codebase-intelligence.md)

- **AST-based code review achieves 8.2x token reduction** over full-file review (intake-330). By analyzing AST diffs rather than raw text diffs, only semantically meaningful changes are reviewed. This is applicable to the autopilot's code mutation validation, where PromptForge proposes changes that need efficient review.

- **The LLM-Wiki pattern is now integrated.** The Karpathy-inspired pattern of structured knowledge compilation (intake-269, intake-277) has been adopted as the project's own wiki system, demonstrating the loop from research intake to implementation. [intake-269, intake-277, intake-321]

- **Tool output compression provides 60-90% token reduction per tool invocation.** Seven command handlers (pytest, cargo test, git status, git diff, git log, ls, build compilers) compress outputs before they enter the context window, layering before the existing `_spill_if_truncated()` mechanism. Feature-flagged as `tool_output_compression`. [tool-output-compression.md handoff]

- **Production agent skills require structured engineering workflows.** Intake-337 documents patterns for building agent skills in production: hypothesis-driven development, incremental deployment, structured testing, and version-controlled skill definitions. This aligns with the project's existing `.claude/skills/` and `agents/` architecture.

- **Integration test infrastructure for graph execution uses "real REPL, mock LLM" pattern.** 61 integration tests (2026-04-13) cover graph execution loop, node-level paths, observability, and API endpoints using a `GraphRunContext` factory fixture that assembles real `REPLEnvironment` (executing actual Python) with `MockLLMPrimitives` returning canned responses. `StubFailureGraph` and `StubHypothesisGraph` are real in-memory implementations (not `MagicMock`) to exercise the full protocol surface. Key design lesson: mock LLM responses must be wrapped in markdown code blocks to prevent `auto_wrap_final` or prose rescue from converting them to FINAL answers. This pattern enables testing the full orchestration loop independently of inference servers. [integration-test-coverage.md]

- **Risk-weighted coverage classification drives test prioritization.** The 100%-feasibility audit (2026-04-14) classified uncovered branches as must-test (recovery paths, parsing fallbacks, context-size selection) vs acceptable-gap (import fallbacks, portability branches). Staged floor raises follow test tranches rather than forcing blanket 100%. This methodology achieved 100% on all 10 seeding benchmark modules and all 7 enforced orchestrator slice files through 12 targeted tranches (A-L) with zero runtime behavior modifications. [integration-test-coverage.md, progress/2026-04-14]

- **Crawl4AI provides self-hosted deep page scraping for LLM consumption.** Async Playwright-based crawler (51K+ stars, Apache-2.0) with BM25 content filtering, local LLM extraction via Ollama, browser pool management, and Docker deployment. Selected over Firecrawl (108K+ stars) due to open-source-only infrastructure policy -- Firecrawl's cloud-first SaaS model and credit-based pricing conflict with self-hosted philosophy. Complements SearXNG (search aggregation) by handling JS-heavy pages and complex PDFs that WebFetch cannot process. Evaluation gated on post-AR-3 WebFetch failure rate data. [searxng-search-backend.md]

- **A server-side delegate primitive already exists in the orchestrator — provider-hosted "subagent" tools (OpenRouter intake-705) are a packaging of a pattern we have shipped, not a missing capability.** OpenRouter's `subagent` server tool lets a model delegate a self-contained task to a cheaper/faster worker mid-generation, with the nested call run server-side: the worker is pinned at configure time (model, instructions, nested server tools, `max_tool_calls` 1-25, `max_completion_tokens`, temperature, reasoning effort), isolated from the parent conversation (sees only `task_description`, keeps no memory between tasks), and bounded by a per-request task-execution cap. Our `src/api/routes/chat_delegation.py` (47 KB) already implements the same shape for the architect→specialist path: configure-time role pinning (`_valid_delegate_roles`, `_normalize_delegate_role`), per-request loop caps (`max_delegate_turns`, specialist time budget), and a re-entrance guard (`_get_delegation_depth`, `reentrant_depth`, max-loop reduction when a specialist escalates back to the architect). The genuine remaining delta to feature-mine is a **cost-aware capable→cheaper-worker delegation mode** — our delegation is capability-driven (architect→specialist by role), not cost-driven (expensive parent offloading to a cheaper worker to save tokens/latency). [confidence: verified — code-read of chat_delegation.py; OpenRouter SaaS = external] [intake-705, chat_delegation.py]

- **The child-LLM structured-return contract is SHIPPED for both batched fan-out and single-delegate REPL paths.** OpenRouter's subagent tool returns **free text with no JSON-Schema return contract** — exactly the gap intake-693 (RLM structured-output) flagged. The orchestrator first closed this for the fan-out path in epyc-orchestrator commit `18b5ceb` ("Validate batched child LLM schemas"): `combined_ops.py::_batch_llm_query` now accepts `schema=`, renders a per-child JSON-Schema contract preamble (`_render_child_schema_preamble`), validates each child response, and retries-with-errors (`_render_child_schema_retry_prompt`, `max_retries` capped to 2). Commit `6426dd4` then closed the single-delegate REPL path: `delegate(..., schema=...)` is opt-in, preserves raw string behavior without a schema, validates with the same `FINAL` answer helper, retries with explicit validation errors, and returns a JSON envelope carrying `valid`/`response`/`raw_response`/`attempts`. Parallel delegation still rejects `schema=` for now. Remaining work is native-tools sentinel/parity and cost-aware capable-to-cheaper delegation, not another child-schema patch. [confidence: verified — commits 18b5ceb/6426dd4, combined_ops.py + REPL tests] [intake-705 deep-dive, tool-use-eval-contract.md]

- **OpenRouter Fusion (intake-712/714) contributes three backend-agnostic tool-contract patterns worth porting even though the SaaS panel itself is unrunnable on EPYC.** Fusion packages Mixture-of-Agents (parallel panel → judge → outer-model synthesis) as a model-invoked server tool. The MoA mechanism is already covered (intake-601 OptiLLM, documented as degraded on llama.cpp for lack of `n` multi-sample), and the frontier-panel cost model is the opposite of EPYC's RAM/BW constraints — so the panel does not port. What ports cleanly: (1) a **typed judge schema** that does comparative analysis rather than concatenation (`consensus` / `contradictions` / `partial_coverage` / `unique_insights` / `blind_spots` as structured JSON); (2) **model-discretionary invocation** with a `tool_choice: "required"` override to force it; (3) **recursion-depth bounding** (one fusion call per turn, panel/judge cannot recursively re-invoke fusion, tracked via an `x-openrouter-fusion-depth` header). These are the right shape for an escalation/ensemble-aggregation tier feeding the gated P21.B method-selection axis. [confidence: external — OpenRouter SaaS docs, no published quality/latency/cost numbers] [intake-712, intake-714]

- **The model-stack single-source update pipeline is itself a tool surface: structured truth is compiled into generated contracts that every consumer reads, and launch/AutoPilot-resume/benchmark interpretation fail-closed on drift.** Stack-specific facts (shared models, HOT/WARM status, memory footprints, context windows, launch ports, q_scorer costs, role labels) are edited once in structured truth, compiled into generated model descriptors + `orchestration/derived/stack_priors.yaml`, then projected to ~13 consumer surfaces (27 scanner rules). The canonical entry point is `scripts/registry/stack_change_pipeline.py check [--run-promotion-gate]`; consumers keep generated priors primary with explicit, manifest-owned degraded fallbacks. Notable hardening: AutoPilot system-card rendering now **fails closed** (it refuses to fall back to a checked-in stale `system_card.md`, instead marking live role/port/tier/throughput facts unavailable and forbidding historical docs/memories/logs as stack truth) — the tooling enforces the measurement-trust-boundary rule that stale numbers must not gate decisions. [confidence: verified — stack_change_pipeline.py, validator commits 471a4d2/523cb02] [model-stack-single-source-update-pipeline.md, standardized-stack-update-pipeline-finalization.md]

- **Magika (intake-398, ICSE 2025, Apache 2.0) is a 1 MB byte-embedding MLP that outperforms libmagic on text-format discrimination, but is not_applicable to EPYC's pipeline.** Contrary to reviews describing it as a CNN, the model is a shallow MLP: three fixed 512-byte windows (beginning, middle, end) are embedded at the byte level into 128-dim vectors, reshaped, passed through two 256-d Dense+GELU layers, global max-pooled for size invariance, and classified over 200+ content types with per-class thresholds calibrated for 99% precision. Training set grew from 24 M to ~100 M samples (GitHub + VirusTotal). The threshold mechanism causes abstention (falls back to `txt`/`unknown`) when confidence is below per-class calibration point — this is how the paper reports 99% F1 without claiming that accuracy on all inputs. Cold-start on the EPYC host measured 225 ms (onnxruntime init dominates); amortized per-file latency is 2.8 ms (better than the paper's 5.77 ms, consistent with the hardware). libmagic is 5-8x faster per file and has <1 ms cold-start, but struggles with text-format discrimination (Python vs Ruby vs JS). **Not applicable to EPYC**: the orchestrator's document-ingestion corpus is a five-format, already-labeled set (arXiv PDF, GitHub MD, HTML, HuggingFace MD, user-uploaded PDF) where format is declared by URL pattern, HTTP Content-Type header, or file extension. No pipeline stage (`pdf_router.py`, `document_preprocessor.py`, `fetch.py`, `research.py`) requires generic filetype detection. A trivial extension-plus-4-byte-magic check has essentially zero false-positive rate on this corpus. Live measurement confirmed the JSON/JSONL confusion documented in external reviews: Magika classified a `.json` file as `jsonl` (JSONL is line-delimited JSON, a distinct format). Integration cost would be ~80 MB of transitive dependencies (onnxruntime) and 225 ms cold-start with no accuracy gain. Reconsider only if the pipeline begins ingesting truly arbitrary binary corpora (malware, forensic dumps, archives with unknown extensions). [confidence: verified — magika-filetype-detection.md deep dive, 2026-04-17]

## 2026-06-13 Update — Review And Governance Tools

- **Security-review is now a first-class skill scaffold.** The v1 skill uses STRIDE, OWASP Web/API Top 10, OWASP LLM Top 10 2025, and supply-chain checks, but only emits findings after exploit-path validation. This is the same anti-false-positive discipline as the eval tower: attacker capability, reachability, trust boundary, vulnerable sink, mitigation analysis, concrete impact, fix, and file/line evidence all have to pass. CI and slash-command wrappers remain deferred. Source: [security-review-skill.md](../handoffs/active/security-review-skill.md).
- **External-source quarantine is now tooled, not only policy.** Root policy, safety-reviewer guardrail, research-intake rendering convention, warn-mode validator, and a synthetic canary landed. The orchestrator `web_research` path also wraps source-derived synthesis in `SOURCE-QUARANTINE` blocks with URL/retrieved/SHA metadata. Source: [frontier-f5-intake-injection-hardening.md](../handoffs/completed/frontier-f5-intake-injection-hardening.md).
- **Repo-readiness scoring gives agents a deterministic improvement queue.** The v1 scorer checks 45 criteria across 5 levels and 9 pillars using concrete artifacts. It should feed remediation planning only after humans decide which criteria matter; deterministic presence checks do not prove quality. Source: [repo-readiness-scorer.md](../handoffs/active/repo-readiness-scorer.md).

## Actionable for EPYC

### High Priority (immediate value)
1. **REPL tool wrappers for GitNexus** (Option 2) -- add 3 tools (`codebase_impact`, `codebase_context`, `codebase_changes`) to `orchestration/tool_registry.yaml` that shell out to `gitnexus` CLI. ~120 lines, integrates with existing registry pattern. Saves 3-5 REPL turns per coding task by front-loading dependency context.
2. **Auto-inject codebase context into prompts** (Option 3) -- when `_execute_turn()` builds the coder prompt, query GitNexus for target symbol context and inject alongside `gathered_context`. ~150 lines, feature-flagged behind `gitnexus_context_injection`. Highest single impact on coding agent quality.

### Medium Priority
3. **Pre-commit validation** -- wire `detect_changes` into the generation monitor. After the coder produces code, check blast radius against the graph before accepting. ~50 lines. Catches unintended side effects.
4. **BM25 + semantic hybrid search for episodic memory** -- the RRF fusion pattern from GitNexus is applicable to the FAISS-only episodic retrieval. Adding BM25 lexical matching via `rank_bm25` would improve retrieval for exact function/class name queries.
5. **Skill generation from clusters** -- run `gitnexus analyze --skills` on the orchestrator to generate data-driven skill files per functional cluster. Evaluate whether these can replace or supplement manual agent role descriptions.
6. **AST-based code review** (intake-330) -- integrate AST diff analysis into autopilot code mutation validation for more efficient review of PromptForge proposals.

### Lower Priority
7. **KuzuDB direct Python queries** (Option 5) -- eliminate Node.js subprocess overhead with native Python bindings to the GitNexus-built graph. ~200 lines, sub-millisecond queries. Pursue if subprocess latency (~50-500ms) becomes a bottleneck.
8. **Cross-repo graph** -- index all 4 EPYC repos into one graph to capture cross-repo dependencies (orchestrator -> llama.cpp binary paths, research -> orchestrator registry references).
9. **Re-indexing automation** -- add GitNexus re-indexing to `session_init.sh` with a HEAD sha staleness check. Current indexes go stale as code changes. Incremental re-indexing takes 2-5s.
10. **Crawl4AI deployment (post-AR-3, gated on WebFetch failure data)** -- if web_research sentinel data shows significant JS-heavy page fetch failures, deploy Crawl4AI Docker container alongside SearXNG. Apache-2.0, no API keys, local LLM extraction via Ollama. Evaluate as fetch backend for ColBERT reranker S5 pipeline.

### Known Issues
- `gitnexus impact` has a known segfault (exit 139) on some queries due to a KuzuDB native binding issue. `gitnexus context` is reliable. All calls must be wrapped in try/except with timeout.
- GitNexus license is PolyForm Noncommercial 1.0.0 -- fine for personal/research use, not for commercial distribution. If licensing becomes a constraint, the core patterns (tree-sitter + leidenalg + kuzu, all with Python bindings) can be reimplemented in ~500-800 lines.
- Disk usage: ~50MB per indexed repo (KuzuDB + HNSW index). All 4 repos total ~200MB.

## Crawl4AI — Self-Hosted Web Crawler for LLMs

Crawl4AI (intake-372, 51K+ GitHub stars, Apache-2.0) is a self-hosted async web crawler designed for LLM consumption. It fills the deep page scraping role that WebFetch cannot handle for JS-heavy pages and complex PDFs, complementing SearXNG which handles search aggregation.

Key capabilities: async Playwright-based crawling with browser pool management, BM25 content filtering for relevance, LLM extraction with local models (Llama 3, Mistral via Ollama integration), HTML-to-markdown conversion for LLM-ready output, and Docker deployment with no API keys required.

**Integration path**: Deploy as a Docker container alongside SearXNG. In the web_research pipeline, SearXNG finds URLs via search aggregation, Crawl4AI extracts page content for JS-heavy or dynamic pages where the current `WebFetch` tool fails. Also a candidate for the ColBERT reranker fetch step (colbert-reranker-web-research.md S5) where fetched pages need reliable content extraction.

**MCP integration**: Crawl4AI can be exposed as an MCP tool for Claude Code sessions, following the same pattern as the mcp-searxng bridge (intake-361). This provides an alternative to direct Python integration for agent workflows that need deep page scraping.

**Policy context**: Selected over Firecrawl (intake-364/365, 108K+ stars) due to the open-source-only infrastructure preference. Firecrawl's cloud-first SaaS model, credit-based pricing, and reduced self-hosted feature parity conflict with the project's self-hosted philosophy. Crawl4AI evaluation is gated on post-AR-3 web_research sentinel data: if WebFetch succeeds on >90% of pages, neither tool is needed short-term.

> Source: [SearXNG Search Backend](/workspace/handoffs/active/searxng-search-backend.md) -- intake-364/365/372, Crawl4AI Docker deployment, MCP integration, open-source-only policy

## 2026-06-15 Update — Tool Surfaces Became More Explicit

- **Security review is now a dedicated tool surface, not just an implied code-review habit.** The new skill scaffold runs STRIDE, OWASP, and supply-chain checks, but only records findings after exploit-path validation succeeds. Sources: [security-review-skill.md](../handoffs/active/security-review-skill.md).
- **External-source quarantine is now enforced in tooling, not just policy prose.** The intake/rendering path now wraps source-derived synthesis in `SOURCE-QUARANTINE` blocks with provenance metadata and a warn-mode validator. Source: [frontier-f5-intake-injection-hardening.md](../handoffs/completed/frontier-f5-intake-injection-hardening.md).
- **Token-compression middleware now extends the existing tool-output pipeline.** The downstream MCP wrapper/compressor path landed as a token-reduction layer on top of the current tool registry rather than a behavior change, so the implementation principle remains "compress outputs before they enter context." Source: [tool-output-compression.md](../handoffs/active/tool-output-compression.md).

## Open Questions

- Is the Node.js runtime dependency acceptable long-term, or should core patterns be reimplemented in Python? tree-sitter, leidenalg, and kuzu all have Python bindings. Estimated effort: ~500-800 lines.
- What is the right re-indexing cadence? Options: manual after major changes, session_init.sh at session start (recommended), post-commit hook (2-5s incremental).
- How should GitNexus context interact with the existing `gathered_context` in `_execute_turn()`? Additive injection (simplest) vs competitive replacement of grep-based gathering (more efficient but riskier).
- Can the Leiden cluster skill files replace manual agent role descriptions, or are they too granular for routing decisions?
- How does tool output compression interact with the Omega problem? If compressed tool outputs are more information-dense, they may improve REPL-mode accuracy on suites where tools currently hurt.
- What is the JS-heavy page failure rate with WebFetch in production web_research sessions? This determines whether Crawl4AI deployment priority should be elevated.
- Should the existing capability-driven `chat_delegation.py` gain a cost-aware mode where a capable parent offloads to a cheaper worker on token/latency grounds (the OpenRouter subagent delta)? What signal would gate the decision to delegate — predicted token cost, observed parent latency, or a routing-classifier confidence threshold?
- Should parallel delegation eventually accept `schema=` too, or is the current batched-query plus single-delegate coverage sufficient until a fan-out-heavy eval shows a remaining typed-return gap?
- Can a self-hosted, n-free escalation tier reuse Fusion's typed judge schema (consensus/contradictions/blind-spots) without the parallel-panel MoA cost model — e.g. a sequential judge over a small set of local-model candidates feeding P21.B?
- Should generated-contract fail-closed behavior (stack-summary unavailability rather than stale fallback) be generalized to other agent-facing context surfaces beyond the AutoPilot system card?
- How should dashboard steering affordances close the 28-GET/0-POST gap safely — guarded operator POST endpoints, or minimally copy-exact command chips (SIGTERM/pause/rewind) that keep execution in the operator's shell? Which actions, if any, are safe to expose behind a UI at all given the trust-boundary rules?
- Now that three of four repos score Autonomous/L5 on deterministic presence checks, what is the follow-on instrument that measures *quality* of those surfaces (the scorer explicitly certifies existence, not quality) — and should `L5.self_optimizing_loop` for epyc-root stay open until a loop with real promotion evidence exists?

## Related Categories

- [Agent Architecture](agent-architecture.md) -- tool implementation is a subsystem of the orchestrator's coding agents
- [Routing Intelligence](routing-intelligence.md) -- tool availability (e.g., web_search) can attenuate factual-risk scores in routing decisions
- [Memory Augmented](memory-augmented.md) -- hybrid search pattern (BM25 + semantic + RRF) applicable to episodic memory retrieval
- [Context Management](context-management.md) -- tool output compression is an upstream compression layer complementary to session-level context folding
- [Search & Retrieval](search-retrieval.md) -- Crawl4AI complements SearXNG search aggregation with deep page content extraction

## Source References

- [GitNexus codebase intelligence](../research/deep-dives/gitnexus-codebase-intelligence.md) -- 8-phase indexing pipeline, 7 MCP tools, hybrid search (BM25+semantic+RRF), Leiden clustering, confidence-scored edges, process-grouped results
- [GitNexus orchestrator integration](../research/deep-dives/gitnexus-orchestrator-integration.md) -- 5 integration options ranked by ROI, context injection > tool calling insight, re-indexing strategy, KuzuDB direct query path
- [corpus-augmented-prompt-lookup-revalidation.md](../handoffs/active/corpus-augmented-prompt-lookup-revalidation.md) -- 2026-07-03 A10 registry-loading repair, role-level corpus gate, structured evidence logging, and offline health-probe result for the local code corpus
- [tool-output-compression.md](../handoffs/active/tool-output-compression.md) -- 7-handler output compression (60-90% savings), feature-flagged, layered before spill mechanism
- [repl-turn-efficiency.md](../handoffs/active/repl-turn-efficiency.md) -- frecency file discovery, combined operations, contextual suggestions for REPL efficiency
- [intake-269](https://github.com/nvk/llm-wiki) nvk/llm-wiki -- Claude Code plugin for LLM-compiled knowledge bases (adopt_patterns, high relevance)
- [intake-277](https://github.com/NousResearch/hermes-agent/pull/5100) Hermes Agent PR#5100 LLM Wiki Skill -- Karpathy pattern for structured knowledge compilation (already_integrated)
- [intake-321](https://github.com/forrestchang/andrej-karpathy-skills) Karpathy-Inspired Claude Code Guidelines -- CLAUDE.md plugin pattern (already_integrated)
- [intake-330](https://github.com/tirth8205/code-review-graph) code-review-graph -- AST-based code review with 8.2x token reduction over full-file review (worth_investigating)
- [intake-337](https://github.com/addyosmani/agent-skills) Agent Skills -- production engineering workflows for AI coding agents (worth_investigating)
- [intake-340](https://github.com/Kohei-Wada/taskdog) Taskdog -- task management with schedule optimization (not_applicable)
- [Integration Test Coverage](/workspace/handoffs/active/integration-test-coverage.md) -- 61 integration tests with real REPL + mock LLM pattern, GraphRunContext factory, risk-weighted coverage classification
- [Progress 2026-04-14](/workspace/progress/2026-04/2026-04-14.md) -- Coverage tranches A-L (sessions 2-20), 100%-feasibility audit methodology, seeding control-plane characterization
- [SearXNG Search Backend](/workspace/handoffs/active/searxng-search-backend.md) -- intake-372 Crawl4AI (self-hosted web crawler, Apache-2.0, Docker deployment, MCP integration path), intake-364/365 Firecrawl (deferred: cloud-first SaaS)
- [pi-agent-core deep-dive](../research/deep-dives/pi-agent-core-stateful-ts-runtime.md) -- 2026-04-26 (intake-473). `beforeToolCall` / `afterToolCall` hook surface with field-replace semantics and throw-isolation: composable middleware for tool-output post-processing without each layer knowing about the others. Maps to `tool-output-compression.md` Phase 3d (compression as middleware) and `meta-harness-optimization.md` (code-mutation safety gates). Per-tool `executionMode` override + batch-falls-back-to-sequential rule for mixing exclusive-access tools with concurrent ones. Terminate-unanimous-batch rule for clean early-exit semantics. Verdict: adopt_patterns.
- [Magika deep dive](/workspace/research/deep-dives/magika-filetype-detection.md) -- intake-398; Google AI content-type detector (ICSE 2025, Apache 2.0); byte-embedding MLP architecture; 225 ms cold-start, 2.8 ms/file on EPYC; not_applicable — no pipeline stage requires generic filetype detection on EPYC's five-format corpus
- [intake-705](https://openrouter.ai/docs/guides/features/server-tools/subagent) OpenRouter Subagent server tool -- provider-hosted nested-model delegation: configure-time worker pinning, stateless scoped task isolation, per-request execution cap, free-text returns (no schema). adopt_patterns; SaaS = external. Maps to the orchestrator's existing `chat_delegation.py` server-side delegate; remaining delta = cost-aware capable→cheaper-worker mode
- `src/api/routes/chat_delegation.py` (epyc-orchestrator) -- existing server-side delegate primitive: configure-time role pinning (`_valid_delegate_roles`/`_normalize_delegate_role`), per-request loop caps (`max_delegate_turns`, specialist time budget), re-entrance guard (`_get_delegation_depth`, `reentrant_depth`). [confidence: verified — code-read]
- epyc-orchestrator commits `18b5ceb` "Validate batched child LLM schemas" and `6426dd4` "Add schema validation for single delegates" -- `combined_ops.py::_batch_llm_query` and `delegate(..., schema=...)` now cover the batched and single-delegate REPL child-return contracts; parallel delegation still rejects `schema=`. [confidence: verified — code + tests/unit/test_combined_ops.py / REPL tests]
- [intake-712](https://openrouter.ai/fusion) / [intake-714](https://openrouter.ai/docs/guides/features/server-tools/fusion) OpenRouter Fusion server tool -- model-invoked Mixture-of-Agents (panel→judge→outer); portable backend-agnostic patterns = typed judge schema (consensus/contradictions/partial_coverage/unique_insights/blind_spots), model-discretionary invocation with `tool_choice:required` override, recursion-depth bounding (`x-openrouter-fusion-depth`). adopt_patterns; SaaS frontier panel = external; MoA itself already covered by intake-601 OptiLLM
- [tool-use-eval-contract.md](../handoffs/active/tool-use-eval-contract.md) -- 2026-07-05 week-run repair: REPL-pinned tool-sentinel prompt contract now asks for executable tool calls; numeric-param normalization and structured skip outcomes keep the harness from silently no-oping
- [autopilot-continuous-optimization.md](../handoffs/active/autopilot-continuous-optimization.md) -- 2026-07-05 live state: planner-turn StrategyStore hints remain active, W8 is still the remaining blocker, and the repaired harness is running current code at PID `2370903`
- [model-stack-single-source-update-pipeline.md](../handoffs/active/model-stack-single-source-update-pipeline.md), [standardized-stack-update-pipeline-finalization.md](../handoffs/active/standardized-stack-update-pipeline-finalization.md) -- structured-truth → generated-contract → consumer-validation → fail-closed-on-drift tooling; `scripts/registry/stack_change_pipeline.py check [--run-promotion-gate]`; AutoPilot system-card fail-closed (523cb02); ~13 consumer surfaces / 27 scanner rules
- [loops-and-dashboards-audit-2026-07-05.md](../handoffs/active/loops-and-dashboards-audit-2026-07-05.md) -- 2026-07-05 audit of both control loops + both dashboards: liveness-vs-outcome verdict, 28-GET/0-POST steering gap, dead v6 `/slots` reads, freshness-registry gaps, phased remediation roadmap with Phase-1 fixes landed (outcome KPIs `45c118b8`, phase-health outcome blockers `18c71bcc`, `LocalPlannerProvider` `7036630c`, enforced spend breaker `03dfac45`)
- [2026-07-05-dashboard-hub.md](../progress/2026-07/2026-07-05-dashboard-hub.md) -- project dashboard hub build: stdlib server :8100 as managed service, handoff kanban, git-seeded timeline, backlog snapshot, kernel-R&D Phase-3 page reading the `kernel_store.py export` contract; 15 adversarial-review defects fixed, 32 tests
- [2026-07-05-dashboard-recency-and-blocked-routing.md](../progress/2026-07/2026-07-05-dashboard-recency-and-blocked-routing.md) -- card-recency `activity = max(updated, git, wip) → created` pattern, widened `_is_blocked_status()` routing (Blocked 0→5), post-commit/merge/checkout hook installer; 50/50 tests
- [2026-07-05-orchestrator-dashboard-live-tps.md](../progress/2026-07/2026-07-05-orchestrator-dashboard-live-tps.md) -- v6 `/slots`-cutover migration completion on :8000: chunk-span `tps_live`, completed-task tok/s carried from `task_completed` telemetry, per-role `live_tps`, `tap_` SSE prefix dispatch with reverse-grep body recovery
- [repo-readiness-scorer.md](../handoffs/active/repo-readiness-scorer.md) -- full scorer lifecycle 2026-06-13 → 2026-07-05: L2→L5 portfolio trajectory, remediation queue 49→13, passive pickup non-authority contract, launcher injection, llama GitNexus-index blocker
- [repo-readiness-2026-07-05.md](../progress/2026-07/repo-readiness-2026-07-05.md) / [repo-readiness-remediation-2026-07-05.md](../progress/2026-07/repo-readiness-remediation-2026-07-05.md) -- current generated artifacts: portfolio Autonomous/L5, epyc-llama L3 with six P0 L4 gaps, 13-item advisory queue
- [progress 2026-07-04](../progress/2026-07/2026-07-04.md) -- tool-sentinel activation telemetry: `gate3_tool_telemetry.py` hard PASS (`get_eval_secret=7`, no-tool isolation clean), API/daemon env-sync gap and reload fix, StrategyStore planner-tool boundary verification, BSV observe tool-evidence fold-in (`c7590be6`)

## markdownfs (mdfs) — agent-shaped MCP workspace as ETD candidate environment (2026-04-30)

**TL;DR**: intake-520 (subramanya1997/markdownfs, MIT) ships an in-memory concurrent markdown VFS in Rust with MCP server, Git-style versioning, and multi-user permissions. **NOT a substrate change for the EPYC stack** (we already have Git + KB-RAG + GitNexus over the same markdown corpus), but it is **exactly the shape of MCP-tool ecosystem the agent-world ETD species (AW-1) is meant to discover**.

### Tool surface

Ten MCP tools span four categories:

| Category | Tools |
|----------|-------|
| FS ops | `read`, `write`, `delete`, `move` |
| Directory ops | `list`, `create` |
| Search | `grep`, `glob` |
| Version control | `commit`, `log`, `revert`, `status` |

Complete tool surface with a clear verifiable-reward axis: versioned state + permission checks. Commit hashes + permission errors are deterministic ground truth — well suited to `agent-world-env-synthesis.md` AW-3 difficulty-band tagging.

### Key technique

Agent-shaped MCP workspace with content-addressable Git semantics and explicit `addagent` user class for user-to-agent permission delegation. `tokio Arc<RwLock<DbInner>>` single concurrent core fronted by CLI / REST / MCP. Atomic bincode persistence.

### Caveats (revised post-deep-dive 2026-04-30)

- **MCP server runs as `uid=0` root with NO per-user authentication** (documented in the project's own `docs/mcp-guide.md`: *"All MCP operations run as root (uid=0, gid=0). There is no per-user authentication within the MCP protocol — the agent has full access"*). The wheel/agent-token/chmod permission model is HTTP-only. The "user-to-agent permission delegation" framing in the project README is aspirational at the MCP boundary; the project's own `docs/demo-readiness.md` lists "agent-scoped MCP auth" as a known follow-up, not a feature.
- **Single-writer per `state.bin`**: CLI + HTTP + MCP cannot share a workspace concurrently — multi-process must funnel through the HTTP server. The "shared durable memory across agents" framing is not implemented as advertised.
- **The "~102.8× speedup over native FS" headline IS reproducible** (real 1,035-line `tests/perf_comparison.rs`) but methodologically biased: native FS in the bench uses `std::env::temp_dir()` which is `/tmp` = tmpfs (RAM) on Linux, so both sides are RAM. The number measures kernel VFS + syscall overhead saved (per-call dentry/inode/syscall round-trip vs in-process `BTreeMap` mutation), NOT in-memory-vs-disk. Per-op character: hot-cat 100–1000×, touch/stat 50–500×, large writes 2–5×, grep/find 3–20×. **Irrelevant for any LLM-inference-bound workload** — FS syscalls are nowhere near saturated at agentic cadence.
- **Pivot history visible in commit log**: 2026-04-29 commits removed the "remote workspace stack" and "Cloudflare deployment path" 24h after they landed. 8 commits total, 17 days old, single author, no published releases, MIT in README but absent from `Cargo.toml`. Active scope-finding from cloud product to local agent workspace.
- Hard ceilings: 10 MB max file, 1 M max inodes, 256 max depth, 5 s / 100-write auto-save crash window.
- Engineering quality is unusually HIGH for a 17-day single-author project — 239 tests, 4.76 s release-mode perf suite, 17.5 KB self-audit doc (`docs/verification-report.md`) caught 1 bug + 6 doc/reality mismatches and fixed each in-tree. Above the typical solo Rust toy quality bar; not enough on its own to flip adoption-risk.

### Patterns worth borrowing — independent of mdfs adoption

The deep-dive surfaced three patterns from `mdfs/docs/` that have value for EPYC even though we will not adopt mdfs as a dependency.

- **Pattern A — `/runs/<run-id>/` markdown artifact bundle** (from `docs/execution-roadmap.md`): per-run reserved directory of `prompt.md` / `command.md` / `stdout.md` / `stderr.md` / `result.md` / `metadata.md` / `artifacts/`. Clean human-reviewable companion to our JSONL journals for autopilot AR-3 trial bundles, env-synth-coordinator outputs, or HALO trace artifacts. Schema-only borrow.
- **Pattern B — "filesystem truth + derived vector index" with on-write/on-commit/on-revert reindex** (from `docs/semantic-index.md`): independently corroborates `internal-kb-rag.md` K1–K7 architecture. Heading-aware chunking, FS-canonical with derived vector DB, breadcrumb-shaped retrieval results. De-risks our retrieval design — we are not on a private architectural branch.
- **Pattern D — typed Agent identity with `addagent` + token-once-shown-then-SHA256-hashed**: cleaner identity model than our current implicit-trust pattern. Note that mdfs's own implementation of this is incomplete (does not extend to MCP); the pattern is portable, the implementation is not.

### Do NOT do

- **Do NOT adopt as substrate** for `wiki/` or `handoffs/` corpus — that role is already filled by Git + the planned ColBERT KB-RAG (`internal-kb-rag.md`). Single-writer constraint + single-author project + just-pivoted scope make adoption strictly net-negative.
- **Do NOT cite the 102.8× number as a perf prop** for EPYC use cases — the framing is misleading for any LLM-inference-bound workload.

### Concrete (non-blocking) actions

- When `agent-world-env-synthesis.md` AW-6 bootstrap runs the 48-hour discovery sweep, include `mdfs-mcp` as a candidate MCP endpoint. Tasks against a versioned markdown VFS with permissions are inherently verifiable (commit hashes are deterministic ground truth) — well suited to AW-3 difficulty-band tagging. Note the MCP-as-root caveat in AW-4 SafetyGate scoring.
- Treat `docs/semantic-index.md` as Pattern B corroboration in `internal-kb-rag.md` design notes.

### Watch signals (would lift relevance)

- Per-user MCP auth landing in mdfs (the project's own demo-readiness doc lists it as imminent) → relevance to medium.
- AWS S3 Files / mdfs / similar tools consolidating into a recognizable "agent workspace" product category → implications for `hermes-outer-shell.md` positioning.
- First published release / second contributor / run-records phase landing → adoption-risk improves.

### Sources

- [intake-520](https://github.com/subramanya1997/markdownfs) markdownfs (mdfs) — Rust, MIT, v0.2.0, 17 days old
- [Deep dive](../research/deep-dives/markdownfs-rust-mcp-vfs.md) — full source-and-docs read with corrections
- [`handoffs/active/agent-world-env-synthesis.md`](../handoffs/active/agent-world-env-synthesis.md) — Research Intake Update 2026-04-30 (markdownfs) and deep-dive integration

## DeepSeek-TUI snapshot store — subprocess-only git port recipe (2026-04-30)

**TL;DR**: intake-508 (Hmbown/DeepSeek-TUI, Rust, closed-API-only) ships a snapshot/rollback mechanism worth lifting as a Python port (~30 LoC, subprocess-only). See [agent-architecture.md § DeepSeek-TUI vocabulary + snapshot-store port recipe](agent-architecture.md) for the full pattern. Highlights for tool-implementation:

- **Storage layout**: `~/.deepseek/snapshots/<project_hash>/<worktree_hash>/.git`. Two-tier FNV-1a path hash strips `.worktrees/<name>` so sibling worktrees share a snapshot project while branches stay isolated.
- **Init**: `git init --quiet <parent_dir>`. Not a clone, not a hardlink, not a worktree-add.
- **Per-call invariant**: every `git` invocation passes both `--git-dir` and `--work-tree` → immune to cwd surprises, forecloses accidental `.git` mutation. Cleaner than a shadow clone.
- **Workspace-only**: snapshots are workspace-files-only. Conversation/session state persists separately. If we promise users "session rollback", we MUST also serialize and restore conversation state.
- **Port recipe**: `subprocess.run(["git", "--git-dir", g, "--work-tree", w, "add", "-A"])` then `write-tree`/`commit-tree`/`update-ref`/`checkout`. Language-agnostic.

### Sources

- [intake-508](https://github.com/Hmbown/DeepSeek-TUI) DeepSeek TUI (Rust)
- [`handoffs/active/hermes-outer-shell.md`](../handoffs/active/hermes-outer-shell.md) Research Intake Update 2026-04-30 — full pattern audit

## Cross-runtime SKILL.md installer pattern is the going default (2026-04-30)

**TL;DR**: intake-509 (mattpocock/skills, MIT) is the second cross-runtime SKILL.md installer collection in our index after intake-450 (veniceai/skills). Both distribute via `npx skills@latest add ...` targeting multiple coding-agent runtimes from one source repo. **Confirms the pattern is the going ecosystem default, not a one-off.**

### Pocock-specific patterns worth lifting

- **`/setup-matt-pocock-skills`** — per-repo bootstrap config skill that records issue-tracker, label vocabulary, and docs paths the other skills consume. Concrete reference for the `scripts/hermes/skills/` per-repo configuration story.
- **`/write-a-skill`** — meta-skill codifying progressive disclosure and bundled-resource conventions for new skills. Pairs with veniceai's authoring rubric for a unified `SKILL TEMPLATE.md` we've been planning.

### Action

Adopt the `/setup-X-skills` per-repo config-bootstrap shape when we wire `scripts/hermes/skills/`. Calibrated for TypeScript app development, not CPU inference — runtime guidance does not transfer; pattern shape does.

### Sources

- [intake-509](https://github.com/mattpocock/skills) Skills For Real Engineers
- intake-450 — veniceai/skills (sibling cross-runtime SKILL.md authoring rubric)
- [`handoffs/active/hermes-outer-shell.md`](../handoffs/active/hermes-outer-shell.md) Research Intake Update 2026-04-30 — installer pattern adoption note

## GitNexus CLI-only operational posture (2026-05-22)

**TL;DR**: Fresh agent sessions chronically struggled to use GitNexus because the CLI was not on PATH, `CLAUDE.md` referenced MCP tool names (`gitnexus_impact({...})`) with no MCP server registered, and the skill SKILL.md files were nested one level too deep for the Skill-tool discovery scanner. Settled on **CLI-only posture with `<!-- gitnexus:keep -->` bloat protection + a `--skip-skills` analyze wrapper** across all 5 repos (epyc-root, epyc-orchestrator, epyc-inference-research, llama.cpp, llama.cpp-experimental). MCP integration deliberately declined — the team's `Bash(gitnexus:*)` permission shows the CLI was always the intended path.

### Diagnosis (3 compounding causes)

- **No CLI on PATH.** `which gitnexus` exited 127. Only ephemeral `npx` caches existed under `~/.npm/_npx/` and one (`5e786f48223a616c`) was corrupted with an `ENOTEMPTY` rename error on `brace-expansion`. Fix: `npm install -g gitnexus@1.6.5` → `/usr/local/share/npm-global/bin/gitnexus` (already on PATH).
- **MCP-syntax in agent files with no MCP server registered.** The auto-generated `CLAUDE.md` and `AGENTS.md` gitnexus blocks instructed agents to call `gitnexus_impact({target, direction: "upstream"})`, `gitnexus_detect_changes()`, `gitnexus_query({query})`, `gitnexus_context({name})`, and `gitnexus_rename(...)` — none of which exist as Claude Code tools unless `.mcp.json` includes a `gitnexus` MCP server. None of the repos had one.
- **Skill SKILL.md nested one level too deep.** Upstream's `installSkills()` writes to `.claude/skills/gitnexus/<name>/SKILL.md`. The Skill-tool discovery scanner reads `.claude/skills/<name>/SKILL.md` (one level deep), so the 6 `gitnexus-*` skills never surfaced in the available-skills list.

### Bloat protection via upstream's `<!-- gitnexus:keep -->` marker

`gitnexus analyze` rewrites the `<!-- gitnexus:start --> ... <!-- gitnexus:end -->` block in both `CLAUDE.md` and `AGENTS.md` to a 43-line MCP-style template on every run (epyc-inference-research's pre-fix block had grown to 77 lines from prior hand-customization). Source-code inspection of the installed package (`/usr/local/share/npm-global/lib/node_modules/gitnexus/dist/cli/ai-context.js`) revealed an upstream-supported escape hatch: if `<!-- gitnexus:keep -->` is present on its own line inside the block, upstream preserves the user-authored content and only refreshes the stats line (regex `^Indexed as \*\*name\*\* \(...\)`). Adopted across the 3 active code repos; CLAUDE.md blocks now ~22 lines, AGENTS.md blocks now ~18 lines.

### Skill layout: flat + `--skip-skills` wrapper

Flattened `.claude/skills/gitnexus/gitnexus-*/SKILL.md` → `.claude/skills/gitnexus-*/SKILL.md` so all 6 skills (`gitnexus-cli`, `gitnexus-debugging`, `gitnexus-exploring`, `gitnexus-guide`, `gitnexus-impact-analysis`, `gitnexus-refactoring`) auto-surface in the Skill tool list. Upstream `gitnexus analyze` would re-nest them on next run, so each repo now ships `scripts/gitnexus-analyze.sh` wrapping `gitnexus analyze --skip-skills "$@"` — this is the canonical re-index entry point. The lean CLAUDE.md/AGENTS.md text explicitly warns: *"`scripts/gitnexus-analyze.sh` — NOT bare `gitnexus analyze`."*

### Verification

Ran the wrapper twice on epyc-root (stale at `17e43ca`, head at `00d2c80`). Block remained lean, stats line refreshed (`19925 → 19967 → 19966` symbols), nested `.claude/skills/gitnexus/` did not re-appear. Skill list confirmed all 6 `gitnexus-*` skills surfaced. Behavior identical for CLAUDE.md and AGENTS.md.

### Patterns worth re-using

- **`<!-- gitnexus:keep -->` as a template invariant.** Any upstream-managed block that supports a keep-style escape hatch is the right place to land project-specific lean text without forking the tool. Worth checking other auto-managed blocks (linters, formatters, generated docs) for similar mechanisms before fighting their default output.
- **Wrapper scripts as the canonical CLI entry point.** When the upstream binary has multiple subtly-wrong defaults (re-nesting skills, re-bloating templates, fetching when offline), the cheapest fix is a `scripts/<tool>.sh` wrapper that hardcodes the safe flags + a doc line in CLAUDE.md that warns against the bare command. Easier than vendoring the tool, easier than hooking the post-tool-use phase.
- **Skill auto-discovery's one-level rule is load-bearing.** When the harness's Skill tool list determines whether a skill is even reachable, the on-disk layout MUST match the scanner — vendor bundles that nest a level deeper (`.claude/skills/<vendor>/<name>/`) silently disappear from the agent's available actions. Flatten on install or symlink.
- **Bloat protection requires a 3-layer fix, not just one.** (a) Mark the block as user-owned (`keep` marker). (b) Make the canonical re-run wrapper carry the safe flags. (c) Document in agent files that the wrapper is the canonical command. Skipping any layer = re-bloat on the next session.

### Sources

- [`progress/2026-05/2026-05-22.md`](../progress/2026-05/2026-05-22.md) Session 4 — full diagnosis, verification, and per-repo commit table
- `memory/feedback_gitnexus_bloat_protection.md` — operational rule: never bypass the wrapper, never strip the keep-marker
- `memory/project_gitnexus_cli_only_setup.md` — full setup notes (global install, flat skills, wrapper, posture rationale)
- Upstream source: `/usr/local/share/npm-global/lib/node_modules/gitnexus/dist/cli/ai-context.js` — `upsertGitNexusSection` keep-marker logic (lines ~174–200)

## Understand-Anything — code-intelligence cohort entry (2026-05-27)

**TL;DR**: intake-625 ([Lum1104/Understand-Anything](https://github.com/Lum1104/Understand-Anything), MIT) is a multi-IDE plugin (Claude Code / Cursor / Copilot / Codex) that converts codebases + markdown corpora into interactive knowledge graphs via a hybrid Tree-sitter + LLM pipeline. It directly overlaps with **GitNexus (intake-151, in production)**, **code-review-graph (intake-330)**, and **Repo Prompt CodeMaps (intake-573)**. After a full-clone audit at commit `26edf61`, the verdict is `worth_investigating` — **adopt three deterministic patterns as design references, do NOT install the plugin, do NOT swap GitNexus.**

### What the plugin is, mechanically

- 9 specialized agents (README says 5) orchestrated by an 844-line `SKILL.md` running 7 phases: SCAN → BATCH → ANALYZE → ASSEMBLE-REVIEW → ARCHITECTURE → TOUR → REVIEW → SAVE.
- 10 first-class Tree-sitter languages (TypeScript, JavaScript, Python, Go, Rust, Java, Ruby, PHP, C/C++, C#); regex-fallback for PowerShell / Bash / Batch / Swift / Kotlin.
- Louvain community detection on the import graph batches files (`MAX_COMMUNITY_SIZE=35`, `MIN_BATCH_SIZE=3`); 5 concurrent `file-analyzer` subagents dispatch per batch.
- Incremental update via `git diff <lastCommitHash>..HEAD --name-only` + fingerprint-based change detection (cheap steady-state).
- TypeScript implementation: 16 340 LOC prod / 13 034 LOC tests (0.80 ratio, 44 test files).

### Patterns worth lifting (as design references, not as code dependency)

- **A. LLM-annotation layered on Tree-sitter structural truth.** `agents/file-analyzer.md:15` enforces a strict two-phase split: deterministic `extract-structure.mjs` (334 LOC) produces functions/classes/imports/exports/size/complexity *first*; the LLM then annotates the **skeleton + source** with summary, tags, semantic edges. A `merge-batch-graphs.py` canonicalizer normalizes IDs and drops orphans after the LLM. Application target: KB-RAG chunking — feed skeleton to the annotator, not raw source. Cheaper, less drift.
- **B. Dependency-ordered guided-tour generation.** `agents/tour-builder.md` Phase 1 is a deterministic graph-topology script: fan-in / fan-out rankings, explicit entry-point scoring rubric (`README.md` at root = +5, `main.{ts,py,go,rs,...}` = +3, root/one-deep = +1, high-fan-out top-10% = +1, low-fan-in bottom-25% = +1), BFS-with-depth-bands from the top entry point, bidirectional-cluster detection. The LLM only writes narrative around the computed topology. Application targets: handoff-index reading order; query-time context expansion over the `[[wiki-link]]` graph.
- **C. Code → business-domain mapping schema.** `agents/domain-analyzer.md` ships a `domain → flow → step` 3-level hierarchy with `flow_step.weight` as monotonic ordering in [0,1] and `step.filePath + lineRange` as round-trip anchor. Schema is well-specified; caveat — UA leaves the anchor as a soft prompt rule. If lifted, enforce at write time.

### Why not adopt UA itself (4 gates, 0 currently met)

- **Sustainability gate fails.** 547 commits / 30 contributors in 10 weeks, but Lum1104 = 83% (377+58+18 across two email aliases); second-largest contributor = 9 commits (1.6%). No CHANGELOG. Commit-rate tapering 60→8/wk over the last six weeks reads as one person's enthusiasm curve, not a maintained team.
- **Stability gate fails.** No API/schema-stability commitment for `knowledge-graph.json` / `domain-graph.json`.
- **Empirical gate fails.** Zero third-party-published full-rebuild + incremental benchmarks on >1k-file repos. 39 127 ★ in 10 weeks = novelty hype, not measured value (memory: `feedback_credibility_from_source_not_readme`).
- **Cost characterization.** Full rebuild on ~500-file repo ≈ 33 file-analyzer dispatches × 5 concurrent → low-hundreds to low-thousands of cents per full index. GitNexus is zero-LLM on both full and incremental, seconds-to-minutes regardless of size.

### Patterns NOT worth lifting

- **The 9-agent decomposition itself.** No published ablation comparing 1-agent vs 9-agent quality; reads as natural-LLM-style framing of orthogonal concerns. The repo's own count is unstable (README says 5, repo ships 9).

### Revisit-trigger (earliest 2026-08)

Requires **all four** of: (1) internal pull from `internal-kb-rag.md` for guided-onboarding or code→domain mapping that current K1–K10+K11 doesn't cover; (2) sustained second-committer ≥30 commits / ≥60 days; (3) CHANGELOG.md + written schema-stability commitment; (4) third-party-published full-rebuild + incremental benchmark on >1k-file repo.

### Sources

- [`research/deep-dives/2026-05-27-understand-anything-vs-gitnexus.md`](../research/deep-dives/2026-05-27-understand-anything-vs-gitnexus.md) — full audit + adoption thesis vs four user statements
- [`research/intake_index.yaml`](../research/intake_index.yaml) intake-625 — entry with deep_dive cross-link, refined verdict_justification, contradicting_evidence
- [`handoffs/active/internal-kb-rag.md`](../handoffs/active/internal-kb-rag.md) Research Intake Deep-Dive — 2026-05-27 section — gated lift-not-fork shopping list for Patterns A+B
- [`handoffs/active/meta-harness-optimization.md`](../handoffs/active/meta-harness-optimization.md) Research Intake Update — 2026-05-27 — explicit do-not-lift record for the 9-agent decomposition

## Wrap-up and index-hygiene guardrails (2026-05-27)

The manual `$wrap-up` routine is the controlled cadence for broad index pruning. Active indices track outstanding TODOs only, but pruning should happen during wrap-up rather than mid-campaign so status changes are reviewable and logged. The 2026-05-27 hygiene audit also tightened the archive rule: a handoff cannot be archived unless it is not a live reference target and its acceptance criteria are met as written.

Practical patterns:

- Prefer dereference/trim over archive when open work remains; move completed chronology into progress logs.
- If a direct domain index would otherwise hide a pending trim, add a short hygiene note in the affected index or handoff until the trim lands.
- Never mark flag-implemented work complete if the behavioral default in the acceptance criteria is still pending operator decision.
- Separate owner-refresh queues from direct edits: stale handoffs needing owner judgment should be logged, not silently rewritten.

Sources: [`handoffs/completed/handoff-backlog-hygiene-audit.md`](../handoffs/completed/handoff-backlog-hygiene-audit.md), [`handoffs/active/launcher-numa-mode-gating.md`](../handoffs/active/launcher-numa-mode-gating.md), [`progress/2026-05/2026-05-27.md`](../progress/2026-05/2026-05-27.md).

## Split-repo validator and wrap-up tool updates (2026-05-28)

The root governance validators now reflect the split-repo layout instead of assuming all code lives under epyc-root. `validate_doc_drift.py` resolves `epyc-orchestrator` through `repos/epyc-orchestrator`, `/workspace/repos/epyc-orchestrator`, or `EPYC_ORCHESTRATOR_REPO`, reads `PORT_MAP` from `scripts/server/stack_manifest.py`, and only requires a Makefile when root `CLAUDE.md` actually documents `make` targets. `validate_agents_references.py` no longer scans the archived `agent-files-refactor-complete` handoff as if it were active, and the CLAUDE accounting helper now requires only the root `CLAUDE.md` governed baseline.

The wrap-up command and Codex wrap-up skill were updated together so handoff compaction behavior is consistent across Claude and Codex surfaces. The important tooling semantics: compaction is manual-wrap-up-only; the trigger is first-screen readability, not line count; partial splits create or extend a sibling while editing the active handoff in place; repeat compactions update the newest sibling's date stamp; and wrap-up output must include a `## Index pruning / handoff compaction` table when any split/prune/archive happened.

Sources: [`scripts/validate/validate_doc_drift.py`](../scripts/validate/validate_doc_drift.py), [`scripts/validate/validate_agents_references.py`](../scripts/validate/validate_agents_references.py), [`wrap-up.md`](../.claude/commands/wrap-up.md), [`progress/2026-05/2026-05-28.md`](../progress/2026-05/2026-05-28.md).

## Compiled Update — 2026-08-12: a health check with two values is a tool that cannot report its own blindness

**Confidence: verified** — each item carries a commit and a test-count delta; one item is verified *from a ref* rather than from the working tree, deliberately.

### The defect class, stated once

Every item below is the same shape: **a check whose output has two states (`ok` / `not ok`) when its input has three (`ok` / `not ok` / `could not observe`)**. The third state gets folded into one of the first two, and which one it folds into decides whether the tool fails loud or fails silent. Three independent instances landed in one week:

- A hub supervisor's `health_ok()` collapses a curl timeout, a missing binary and a wrong port into the same value as a genuinely dead service — so "cannot observe" becomes "restart it", and the restart loop is indistinguishable from remediation. Filed, **open**.
- A bus supervisor's daemon-liveness predicate matched only self-launched daemons, so a healthy 75-minute-old daemon read as absent and was killed; its replacement predicate is **vacuous in a five-writer tree** and was observed killing healthy daemons in **11 cycles over 35 minutes**. (Full detail on [Agent Architecture](agent-architecture.md).)
- A production-kernel dashboard panel was **absence-tolerant quietly**: a missing attestation rendered as a muted line rather than an alarm. Fixed to render a loud `ATTESTATION UNAVAILABLE`; a cosmetic residual remains, in that the underlying function still returns `error: None` for a merely-absent file — the panel is loud now, the function still cannot say why.

The rule this yields for any probe: **enumerate the states of the observation, not the states of the subject.** A check that cannot emit "I cannot tell" will emit something else instead, and that something else will be actionable.

### The probe-semantics fix the plane rule implies

The plane rule recorded below says every dashboard needs a health probe; this week supplies the sharper version of *which* probe. A Kernel-R&D registry entry was pointing its `health_path` at the **transport** probe (`/health`) — which stays green over a dead producer, because the process is serving fine — and was moved to a **semantic** data-health probe (`/api/kernel/health`) that returns 503 when the champion, headroom or release package is unreported. Roughly 74 lines of server and 110 lines of tests. The generalisable statement: `/health` answers *is this process alive*, `/api/health` answers *is what this page shows still true*, and a registry that stores the first while the page promises the second is a correctly-configured lie.

A related wiring defect is worth carrying because it is cheap to reproduce: a staleness check was hooked into the one-shot command path and **never into the loop**, which is the default long-running mode — so the check existed, passed its tests, and never ran in production. The identical shape had already been fixed once in a sibling supervisor.

### Verify from a ref, not from the shared working tree

One verification in this pass was deliberately performed against a committed ref rather than the working tree, and the reason generalises to every multi-writer repo: **the working tree is the one surface that can show you a repair with no evidence that it is a repair.** The precedent is a same-week adjudication where a reviewer refuted a peer's finding 20 seconds *before* the fixing commit existed — they had read the peer's uncommitted edit and concluded the defect never existed. The rule adopted: adjudicate a peer's finding from `git show <ref>:<path>`.

### Counting instruments must anchor their own patterns

A checkbox counter using an unanchored `- [ ]` regex matched mid-line and was **wrong in both directions** — re-derived with an anchored pattern the real movement was 1273 → 1242 open (−31) and 2306 → 2368 done (+62), against circulated figures that had both endpoints wrong. A canonical anchored counter already existed in the repo and was not used. When a project has one, a hand-rolled grep is not a second opinion; it is an unvalidated instrument.

### Source References (2026-08-12)

- [`dashboard-architecture-restructure.md`](../handoffs/active/dashboard-architecture-restructure.md) — the D-1 absence-tolerant panel, the D-2 transport→semantic probe move, and the open D-3 two-valued supervisor check.
- [`non-inference-backlog.md`](../handoffs/active/non-inference-backlog.md) — the OBS-series "fails to say I cannot tell" sweep, including a fail-open guard and a duplicated liveness oracle across four files.
- [`session-bus-thin-dispatcher.md`](../handoffs/active/session-bus-thin-dispatcher.md) — the supervisor liveness and watchdog defects that share the class.
- [`progress/2026-08/2026-08-12.md`](../progress/2026-08/2026-08-12.md) — the verify-from-a-ref rule and the anchored-counter correction.

## Compiled Update — 2026-08-10: dashboards split by plane, not by transport

> The settled architecture from the dashboard restructure. The fix list is still moving; the
> decisions below are ratified and are what the next monitoring surface must be built against.

- **The ownership rule compiled above is a *transport* rule, and its premise has eroded.** The recorded
  boundary — *live orchestrator in-process state / SSE → the API's own page; artifact- or file-backed
  and project-wide → the hub* — governs **which process serves bytes, not what shares a page**, which
  is exactly how one page accreted into a 7,855-line route file plus a 7,649-line single HTML document
  mixing three concerns (a global machine/live-inference monitor, the autopilot loop's planning and
  governance surface, and orchestrator serving telemetry). The premise is now largely false as well:
  the topology and region-lock builders are `/proc`/`ps` scans verified network-free, the taps tail
  rotating event files, and the autopilot panels read journal and state files. What genuinely *is*
  in-process is per-worker fragmented — i.e. the part a fidelity audit already says should not be
  trusted as served. **Superseded by the plane rule below.**

- **The plane rule (ratified 2026-08-10)**: *data contracts live with the subsystem they observe;
  pages, navigation and the surface registry live with the governance hub; every new dashboard is a
  registry entry plus a health probe plus a freshness envelope; no unregistered pages.* Repos own
  **data endpoints and export contracts, not pages** — the exporter versions with the code it measures,
  so schema authority stays where the numbers are made. The proof it works here is the kernel-R&D
  split (a producer in the research repo exports schema'd JSON after fsync, the hub renders it, the
  seam is tested, and the hub never imports producer code); the counter-proof is that the one repo
  which owned a whole page grew the monolith. Cross-origin is the enabling detail: a hub page fetches
  the API's JSON/SSE **directly from the browser** under a path-scoped CORS allowlist, so there is no
  proxy, the hub stays stdlib, the processes stay independent, and when the API is down its panels go
  honestly dead instead of the page vanishing.

- **A global monitor whose data plane lives inside the most-restarted process on the host is an
  architecture smell, not merely an information-architecture one.** Under the optimization loop the API
  restarts every ~20–25 minutes per trial, so the machine monitor's delivery path blinks precisely when
  the machine is busiest — and a transport watchdog existed to paper over it. Naming that is what
  turned a layout question into an ownership decision. The matching discipline is that the standalone
  exporter was **deferred** pending observed blink-out evidence: state the coupling, do not build ahead
  of the evidence.

- **A constraint, not a preference, chose the larger option.** The recommendation was the minimal split
  (hub owns the global page; the process-specific page stays with its process). Full view-plane
  consolidation won because the operator depends on the old page *right now*: the minimal option's
  "slim the monolith in place" step surgically edits the live surface, while consolidation never
  touches it — both replacement pages are built fresh alongside it and the old page is deleted wholesale
  at operator-declared deprecation, with its data routes retained. **When the incumbent surface must
  stay live, the option that never edits it can be cheaper than the option that does less work.**

- **Navigation drift had one root cause and therefore one fix.** There was no shared nav component and
  no machine-readable directory of dashboards, so every page hand-copied its own `<nav>` and cross-server
  URLs were re-derived ad hoc in at least three places — one of them shipping a same-origin `href="/"`
  rewritten by JS, which silently pointed at the wrong server whenever the script did not run. The fix
  is a `registry.json` SSOT of surfaces (`id`, `title`, `port`, `path`, `owner_repo`, `health_path`,
  `blurb`) served as an API with per-`(port, health_path)` loopback probes behind a short TTL cache,
  plus **one generated nav asset with the registry inlined**, adopted by every page including the
  cross-origin one — where a `<script>` bootstrap works precisely because script tags are CORS-exempt,
  with an `onerror` fallback so the page never loses its one exit if the hub is down. Once the registry
  exists, drift becomes a **testable property**: a bidirectional routes↔registry check, an assertion
  that every page carries the nav, and a ban on the retired link patterns.
  One deliberate exclusion: the probes stay **out of** the health fold, because a down neighbour must
  not restart-loop the hub that reports on it.

- **Absence must be loud, and the honest states are the deliverable.** Render "slots `?` = unknown, not
  zero"; distinguish a lease held from decoding actually happening; keep stale panels **readable** with
  a bold "no data — last seen …" pill instead of greying them out (greying makes an operator squint at
  data that may still be true); surface a fan-out that answered 0/19 loudly as a machine-truth question
  rather than rendering zeros; and when all-time and windowed KPIs disagree sharply, render **both**,
  because choosing one would mislead. Staleness thresholds are set from the *observed* frame cadence
  rather than a flat constant, or the honest state flaps against a slower producer.

- **Two assembly paths for one payload is a defect class, not an incident.** A 32,851-token prefill
  rendered no progress counter because the SSE stream ran its own parse-and-enrich while only the
  unwatched polling endpoint attached the enrichment. Collapsing both onto one assembly function fixed
  it and incidentally recovered off-window holder handling the stream had silently lacked. From the same
  buildout, two honesty rules worth generalizing: attach live counters **only from fresh samples and
  never to completed requests** (a completed request on a shared port was caught wearing a running
  request's counters), and mark shared-port aggregates `ambiguous` rather than guessing.

- **Derive substrate from process evidence, never from names.** GPU/CPU labelling comes from the server
  binary path, `/proc` argv0, mapped HIP runtime libraries and a model-label hint — because a role named
  `architect_general` is a GPU role and nothing in its name says so, and the image-generation server
  turned out to be genuinely CPU-built on this host (no HIP libraries mapped, no `/dev/kfd`), contra the
  obvious assumption. A service is never allowed to claim "CPU" from the mere absence of a marker, since
  a Python wrapper's child process holds the evidence.

- **Two divergent freshness grammars is a live cost, and merging the code is not the fix.** Both servers
  independently grew panel→producer registries with freshness envelopes in different vocabularies
  (`fresh/aging/stale/missing` with reporting/content axes versus `fresh/aging/stale/dead` with
  gating/informational). Both are tested, so the proposal is to harmonize the **wire vocabulary only**
  and leave the implementations separate — the actual cost today is that every new dashboard must pick
  one of two grammars and the two health folds cannot be read uniformly.

### Source References

- [`handoffs/active/dashboard-architecture-restructure.md`](../handoffs/active/dashboard-architecture-restructure.md) — the audit, the ownership answer, and the ratified D1–D3 decision package
- [`progress/2026-08/2026-08-10.md`](../progress/2026-08/2026-08-10.md) — the buildout record, the deploy checks and the eyeball-pass findings
- [`handoffs/active/autopilot-dashboard-fidelity-audit-2026-07-22.md`](../handoffs/active/autopilot-dashboard-fidelity-audit-2026-07-22.md) — the data-truth defects that remain owned separately from this information-architecture work
- [`handoffs/active/loops-and-dashboards-audit-2026-07-05.md`](../handoffs/active/loops-and-dashboards-audit-2026-07-05.md) — the liveness-vs-value instrument finding this plan builds on
- [`handoffs/active/benchmark-results-dashboard.md`](../handoffs/active/benchmark-results-dashboard.md) — the producer/renderer contract used as the working precedent for the data-plane split

## Compiled Update — 2026-08-13: a licence blocker on failure-trace grading resolved by finding the maintained successor, not by waiting

**Confidence: external** for the tool's own reported metrics (vendor/author-reported, not measured on
our stack); **verified** for the licence and repository-state facts, which were read directly.

A research-intake dive on MAST (intake-1110, arXiv:2503.13657, the multi-agent failure taxonomy paper)
found its reference implementation unusable under EPYC's open-source-only sourcing policy: the
`multi-agent-systems-failure-taxonomy/MAST` repository carries no LICENSE file at all — all rights
reserved by default. A follow-up dive on the same authors' successor project, AdaMAST (intake-1127,
arXiv:2607.16387), found it Apache-2.0, actively maintained, and — the detail that matters for us — able
to detect Codex session transcripts natively, since its loader keys on the exact record-type set our own
Codex rollouts already use. Claude Code transcripts need a small normalizer (roughly 60–120 LOC) to the
tool's four-field canonical schema (`problem_id, task, raw_trajectory, metadata`); Codex needs none.

**The more important reversal happened inside the same dive.** An earlier pass on this material had
concluded that neither of our transcript corpora carries a machine-readable success/failure verdict, and
that building one was "the real blocker" before any grading tool could run. Re-reading AdaMAST's own
induction code overturned that: its taxonomy-induction step is deliberately **outcome-blind** — it
strips any outcome or gate-status field from a trace before an LLM judge ever sees it, precisely so the
induced categories describe failure *modes*, not success labels. A fixed-catalog grading pass (running
MAST's 14 published codes through AdaMAST's judge rather than inducing a new taxonomy) needs no oracle
and costs roughly one LLM call per trace. The oracle question is real but smaller than first framed: it
gates a *second-stage*, fleet-specific taxonomy induction, not the first useful grading pass.

Both tools are cited on the strength of author-reported metrics only; neither has been run against our
own corpus yet. The work is filed, not adopted — see the [Fleet Fan-Out
Measurement](../handoffs/active/fleet-fanout-measurement.md) stub's FM-2 task for the planned pilot.

### Source References

- `research/intake_index.yaml` intake-1110 (MAST) and intake-1127 (AdaMAST) — full dive records, including the mid-dive retraction of the "success/failure oracle required" finding
- [Fleet Fan-Out Measurement](../handoffs/active/fleet-fanout-measurement.md) — FM-2, the planned pilot run
- [Coordinator role — failure modes and refactor](../handoffs/active/coordinator-role-failure-modes-and-refactor.md) — R-24, the cross-walk of MAST's 14 modes against our own hand-built failure ledger
- [`progress/2026-08/2026-08-13-research-intake.md`](../progress/2026-08/2026-08-13-research-intake.md) — session record
