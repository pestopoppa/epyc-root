# Delegation Context Pre-Assembly (Budget-Bounded)

**Status**: implementation-scoped draft — audit-refined 2026-05-25; still feature-flag/default-off until DCP-6 validates
**Created**: 2026-05-25 (via `/research-intake` deep dive of intake-605 Repo Prompt)
**Categories**: context_management, agent_architecture, routing_intelligence, tool_implementation
**Source**: intake-605 (Repo Prompt — Context Builder + CodeMaps); cross-ref intake-330 (code-review-graph), intake-151 (GitNexus), intake-295 (fff.nvim)
**Owning index**: [`routing-and-optimization-index.md`](routing-and-optimization-index.md) P22
**DCP-6 falsification-harness construction**: [`bep-dcp-falsification-harness.md`](bep-dcp-falsification-harness.md) (2026-05-26 — reviewed / ready to build; Phase 5 shares the BEP-2 task-root harness, adds delegation workload + top-up-rate metric; DCP-4 advisory wiring already landed `31ea6d4`)

## Objective

Give the orchestrator a **proactive, token-budget-bounded context _assembly_ layer** that packages a curated, sliced, codemap-augmented context bundle for a sub-task *before* the receiving role runs — instead of having each delegated role re-discover context reactively from scratch via REPL. This is the *assemble* side of context engineering; [`context-folding-progressive.md`](context-folding-progressive.md) owns the *evict* side (compaction of an already-large context).

## Strategic frame — why this is a real gap

Two opposite context philosophies:
- **Ours (reactive discovery)**: the Root LM runs REPL code (grep / read / ColGREP / GitNexus queries) mid-reasoning, pulling context in as it goes. Flexible, but each delegated sub-agent pays the discovery cost again, and unbounded reads can flood the window.
- **Repo Prompt (proactive pre-assembly)**: a Context Builder loop curates a bundle that *provably fits* a token budget before the model runs: task analysis → file discovery → codemap generation → token verification → iterative add/drop/slice → emit a non-prescriptive handoff prompt.

RP built this for cloud GPT-5 Pro (its 60k default is literally the ChatGPT-Pro paste ceiling). On our **BW-bound CPU regime the principle is sharper, not weaker**: every unearned context token is DRAM bandwidth paid at decode, and the prefill of a bloated bundle is pure latency. A budget-bounded packager is plausibly a double win on delegation — less prefill latency *and* less context contamination (better quality).

## What we already have (building blocks)

- **GitNexus** — Tree-sitter symbol graph (42.6K symbols / 73.3K relationships on epyc-orchestrator), impact analysis, `context`/`impact` MCP commands. Can produce signature-level structure → the **CodeMaps analog**, but nothing currently emits an "architecture snapshot" sized to a budget for prompt injection.
- **ColGREP / NextPLAID** — AST-chunked code search (ColGREP ~71% top-1), `epyc-orchestrator/src/repl_environment/code_search.py`. Candidate *file/chunk discovery* engine.
- **context-folding-progressive** — eviction/compaction (two-level condensation, segment scoring). The complement, not a substitute.
- **dispatcher.py / escalation.py** — where a packaged bundle would attach to a delegated sub-task.
- **TOON encoder** — structured-payload compaction; relevant for encoding the assembled bundle.

## The RP mechanism (reverse-engineered) — what to mine

From the official blog + the open-source `w-winter/dot314` MCP wrapper source (repoprompt.com is JS-opaque).
1. **Iterative selection loop**: task analysis → auto file discovery → codemap gen → token verification against budget → iterative refinement (drop/add) → file slicing to fit → non-prescriptive handoff prompt.
2. **Per-file inclusion modes**: each file tracked as `full | slices | codemap_only`; reads auto-promote to slices; overlapping/adjacent line-ranges auto-merged. So a 10k-line file contributes only its relevant ~200 lines, or just its signatures.
3. **CodeMaps as a separate budget class**: signature-only API skeletons injected distinctly from full bodies — architecture awareness while reserving budget for the files actually under edit.
4. **Non-prescriptive discovery prompt** (its own task below): discovery deliberately withholds proposed solutions, emitting open questions + file-relationship explanations only, to avoid biasing / under-scoping the downstream plan.

## Proposed tasks (implementation-grade after audit)

- [ ] **DCP-1 — Context bundle data model + per-file inclusion modes.** Define a `ContextBundle` with per-entry `mode ∈ {full, slices, codemap_only}`, merged line-range slices (auto-merge overlapping/adjacent ranges), and a live token-count accumulator. Each entry MUST carry: `path`, `mode`, `line_ranges`, `symbol_ids` where available, `content_sha256`, `source` (`gitnexus|colgrep|direct_read|manual_seed`), `reason_included`, `reason_downgraded_or_excluded`, and `estimated_tokens`. Reuse GitNexus for `codemap_only`, ColGREP/read for `slices`/`full`. Store the bundle manifest separately from rendered prompt text so downstream roles can request top-ups against stable IDs instead of asking for "that file again." *(Substrate for everything else; net-new.)*
- [ ] **DCP-2 — Budget-bounded assembly loop.** Given a sub-task description + token budget, run discover → codemap → token-verify → add/drop/slice until the bundle fits; emit the bundle + a manifest of what was included/excluded and why. **Budget is a per-role parameter, NOT a fixed 60k** — ours is set by the receiving role's context window and the CPU latency target, not a cloud paste ceiling. Implement as a two-pass loop for efficiency: first pass uses only cheap metadata (GitNexus graph, file sizes, symbol names, ColGREP candidate IDs); second pass reads bodies only for files that survive ranking. Reserve explicit budget bands before packing: task/instructions, codemap, editable slices/full files, tests/examples, and an output reserve. Fail closed if the estimate cannot fit after slicing: emit `codemap_only` + "missing evidence" manifest rather than silently overflowing.
- [ ] **DCP-3 — CodeMaps-as-budget-class via GitNexus.** Add a GitNexus-backed "architecture snapshot" producer: signature-only skeletons for a symbol/file set, sized to a sub-budget, injected as a distinct section. *(Closes the "analyzed-not-wired" gap — GitNexus can already do this, nothing exposes it for prompt injection.)* Cache codemaps by `(path, content_sha256, gitnexus_index_commit)` and expose staleness in the manifest. If `gitnexus status` is stale, either run the wrapper re-index before assembly or mark codemap confidence low and prefer direct slices for changed files.
- [x] **DCP-4 — Wire pre-assembly into delegation as a seed bundle, not a hard context firewall.** WIRED 2026-05-26 (`31ea6d4`), behind `features().dcp_pre_assembly` (default-off). Attach point is `chat_delegation._run_specialist_loop` (the LIVE specialist delegation path — NOT `dispatcher.py`, which only generates the plan/commands): after `corpus_ctx` is built, `_maybe_dcp_seed_context()` augments it with `render_bundle(assemble_delegation_bundle(query, code_search_fn=deleg_repl._code_search, file_reader_fn=...))`. Added `context_discovery.render_bundle()` (the missing body-materialization step — the bundle only planned modes). **Advisory**: reactive discovery stays fully enabled; any failure falls back to plain `corpus_ctx` (never blocks delegation). 7 tests. *(Top-up-rate eval signal + manifest-in-prompt are DCP-6-era refinements; the seed currently renders bodies only.)* Remaining: offline replay + DCP-6 inference A/B (deferred to post-J6).
- [ ] **DCP-5 — Non-prescriptive discovery prompt.** Generate the handoff prompt so it states open questions + file relationships WITHOUT proposing a solution. Land as a **PromptForge mutation** so autopilot can A/B it (see meta-harness-optimization / autopilot). Guardrail: keep solution-free does not mean evidence-free; include why each file/slice matters, known uncertainty, and explicit "do not assume omitted files are irrelevant" text.
- [ ] **DCP-6 — Eval.** Measure on a delegation-heavy workload: prefill tokens, end-to-end latency, top-up count, bundle-build latency, downstream answer quality, hallucinated-file references, and context-contamination failures vs the reactive-discovery baseline. Hypothesis: budget-bounded pre-assembly cuts prefill + latency at equal-or-better quality. Start with a non-inference offline replay over historical tasks to validate bundle size/coverage, then run the inference gate. *(Inference-gated — per `feedback_no_concurrent_inference`, prepare commands; user runs benches.)*

## Audit refinements / missed gaps

1. **Token counting must be model-calibrated, not a rough character heuristic.** The packer should use the same tokenizer or conservative estimator as the target role. Log estimate-vs-rendered-token error and keep p95 over-estimation positive; under-estimation is the failure mode that causes prompt overflow.
2. **Slice boundaries need semantic padding.** A line-range slice should automatically include imports, enclosing class/function headers, decorators, type definitions referenced by the slice, and adjacent tests where cheap. A 20-line hunk without its type/import context is high-risk even if it fits.
3. **Bundle freshness is a correctness property.** Every bundle should include `repo_sha`, `gitnexus_index_commit`, and per-file `content_sha256`. If a delegated role applies edits after files change, the manifest should be considered stale and regenerated.
4. **Do not run broad search on every delegation.** Candidate discovery should prefer caller/callee neighborhoods from GitNexus plus ColGREP top-k, capped by role and task class. Full-repo ColGREP every handoff would erase the latency win.
5. **Security/noise filters belong in DCP-1, not as an afterthought.** Exclude binaries, generated artifacts, huge lockfiles, secrets-like files, and vendored dirs by policy unless explicitly requested. Record exclusions so the worker can ask for an override.
6. **Context-folding integration should share scoring features.** Importance signals from folding (recent use, role relevance, failure history, symbol centrality) should be exposed as rank features for DCP instead of implementing a parallel heuristic.
7. **The first production mode should be advisory.** Attach the bundle while leaving existing reactive discovery enabled, then compare whether the role uses fewer reads/tool calls. Only consider stricter modes after DCP-6 shows quality does not drop.

## Open questions (for brainstorming)

- Does pre-assembly *replace* reactive discovery for delegated roles, or layer under it (assemble a seed bundle, still allow REPL top-ups)? Likely hybrid.
- Right budget per role? Tie to the role's context window and a CPU latency target, not a fixed number.
- Can DCP-2's discovery reuse the learned router / difficulty signal to size the budget by task difficulty?
- Slicing granularity: function-level (GitNexus symbols) vs line-range (ColGREP chunks) vs both?
- Interaction with context-folding: if the assembled bundle still overflows mid-task, folding takes over — do the two share the segment-importance scorer?

## Dependencies / cross-cutting

- **context-folding-progressive** — assemble vs evict; should share segment-importance heuristics (extends routing-index CCC #7).
- **meta-harness-optimization / autopilot-continuous-optimization** — DCP-5 non-prescriptive prompt = PromptForge mutation; DCP-2 budget = candidate autopilot search-space knob.
- **GitNexus** (DCP-3) and **ColGREP** (DCP-1/2 discovery).
- **batched-edit-parallel-apply** (sibling RP-derived handoff) — a pre-assembled bundle feeds a clean think-then-act batch edit.

## Key file locations (targets)

- `epyc-orchestrator/src/orchestration/dispatcher.py`, `escalation.py` — delegation attach point (DCP-4).
- `epyc-orchestrator/src/repl_environment/code_search.py` — ColGREP discovery (DCP-1/2).
- GitNexus MCP `context`/`impact` — codemap source (DCP-3).
- `epyc-orchestrator/src/prompt_builders/` — non-prescriptive handoff prompt (DCP-5).
- `epyc-orchestrator/src/context/bundle.py` *(proposed, new)* — ContextBundle model + assembly loop. **Layout note (gap-fix 2026-05-25):** implemented as top-level `epyc-orchestrator/src/context_assembly.py` (DCP-1/DCP-2 pack core, on main (merged 2026-05-26)) to match the existing `context_manager.py` / `context_compression.py` convention rather than a new `src/context/` package.

## Reporting

Update this handoff + routing-and-optimization-index P22 after each DCP task; record bench results (DCP-6) per `feedback_incremental_persistence`.

## Post-result conditional workflow + mitigation (DCP-6 / bulk-inference J7)

Pre-run wiring: **DCP-1 + DCP-2 discovery + DCP-3 ast-codemap DONE + tested** on main (merged 2026-05-26) (`src/context_discovery.py`: `discover_candidates` / `build_python_codemap` / `cost_candidates` / `assemble_delegation_bundle`, injectable ColGREP + file-reader backends, 11 tests; codemap is a dependency-free `ast` signature skeleton — GitNexus is not a runtime dep). **Remaining: only DCP-4** — the reviewed dispatcher/escalation **advisory** seed-bundle attach (flag default-off; reactive discovery stays on), wiring the orchestrator's ColGREP (`parse_colgrep_json(self._code_search(q, limit=k))`) + workspace file reader into `assemble_delegation_bundle`.

Run **advisory-first** (bundle attached, reactive discovery still enabled — DCP-1 audit #7). Decision tree:
- ✅ prefill+latency down AND quality ≥ baseline AND top-up rate ≤20% → keep advisory; consider seed-bundle-primary mode after a second confirm.
- ⚠️ quality flat but top-up rate >20% (packer under-selecting) → tune discovery depth / ColGREP top-k / per-role budget; re-run.
- ❌ quality drop OR no latency improvement → keep reactive discovery; shelve pre-assembly; flag off.

Mitigation: flag default-off; advisory mode never removes reactive discovery; top-ups always allowed (no hard firewall); bundle freshness (`repo_sha`/`content_sha256`) re-checked per delegation; security/noise exclusion policy applied at DCP-1. Operator decision tree mirrored in [`bulk-inference-campaign.md`](bulk-inference-campaign.md) Package J.
