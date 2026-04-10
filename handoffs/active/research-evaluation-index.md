# Research & Evaluation — Coordination Index

**Status**: active
**Created**: 2026-04-04
**Purpose**: Entry point for agents working on pre-production research, evaluation, and monitoring tasks. These handoffs track techniques and tools not yet targeting production deployment.

---

## Agent Operating Instructions

1. Read the **Outstanding Tasks** section to find actionable work
2. Most handoffs here are stubs or monitoring — check status before investing time
3. After completing work: update the task checkbox here, update the handoff document, update `progress/YYYY-MM/YYYY-MM-DD.md`
4. Do NOT modify production orchestrator code from this index — production changes go through `routing-and-optimization-index.md`

---

## Subsystem Status

| Handoff | Domain | Status | Priority | Last Updated |
|---------|--------|--------|----------|-------------|
| [reasoning-compression.md](reasoning-compression.md) | Reasoning token optimization | in-progress (Tier 1 deployed, Actions 12-14 done, 15 eval ready) | HIGH | 2026-04-09 |
| [tool-output-compression.md](tool-output-compression.md) | Tool token optimization (output + definition) | Phase 2 done, Phase 3a-b done (55% compression) | MEDIUM | 2026-04-09 |
| [multiscreen-attention-evaluation.md](multiscreen-attention-evaluation.md) | Novel attention mechanism | stub (WATCH) | LOW | 2026-04-04 |
| [yarn-context-extension-research.md](yarn-context-extension-research.md) | Context extension via YaRN | stub | LOW | 2026-03-25 |
| [long-context-eval-datasets.md](long-context-eval-datasets.md) | Eval dataset collection | READY (5 datasets, adapters integrated) | MEDIUM | 2026-04-05 |
| [tq3-quantization-evaluation.md](tq3-quantization-evaluation.md) | TQ3/TurboQuant monitoring | monitoring (do NOT merge) | LOW | 2026-04-01 |
| [11-conceptlm-monitoring.md](11-conceptlm-monitoring.md) | Concept-level LM monitoring | monitoring (watch-only) | LOW | 2026-03-03 |
| [knowledge-base-governance-improvements.md](knowledge-base-governance-improvements.md) | KB linter, credibility scoring, anti-bias, project-wiki skill | ALL PHASES COMPLETE | MEDIUM | 2026-04-07 |
| [memento-block-reasoning-compression.md](memento-block-reasoning-compression.md) | Block-level reasoning compression (KV masking) | active (S1 llama.cpp feasibility) | HIGH | 2026-04-09 |
| [repl-turn-efficiency.md](repl-turn-efficiency.md) | REPL turn reduction (frecency + combined ops) | in-progress (S1-S2 done, S4 pending) | MEDIUM | 2026-04-09 |
| [root-archetype-linter-templates-upstream.md](root-archetype-linter-templates-upstream.md) | Linter + brevity templates upstream | in-progress | MEDIUM | 2026-04-09 |

---

## Outstanding Tasks (Priority Order)

### P0 — Reasoning Compression (actionable now)

- [x] Run TrimR evaluation on math/gpqa suites — ✅ 2026-04-09 (Package B). DeepSeek-R1-7B 4×48t. GPQA: thinking helps ~6pp. Math: thinking irrelevant (151 tok avg). TrimR valuable on hard tasks only.
- [x] Collect shadow telemetry from `difficulty_signal.py` in production — ✅ 2026-04-06. 635 requests, Package A run.
- [x] Validate difficulty signal predictive power against benchmark accuracy — ✅ 2026-04-09 (Package B Phase 4). At 0.15/0.35: NO predictive spread — escalation rate flat across easy/medium/hard (62/61/62%). Signal does not differentiate routing needs at current thresholds.
- [ ] If validated: implement enforce mode — **BLOCKED**: difficulty signal has no predictive power at current thresholds. Need semantic features or different approach before enforce.
- [x] Compute Omega metric per-suite — ✅ 2026-04-09 (Package B Phase 4). **7/10 suites: tools HURT accuracy** (direct > REPL). Worst: agentic -54pp, coder -44pp, general -26pp. Only hotpotqa +12pp and gpqa +6pp benefit.

### P1 — Tool Output Compression

- [x] ~~Install RTK binary~~ — SKIPPED: PostToolUse hooks cannot replace built-in tool output. Phase 0 RTK trial deferred.
- [x] Phase 2 native compression module — ✅ 2026-04-05. `compress_tool_output.py` with 7 handlers (pytest, cargo test, git status/diff/log, ls, build). 27 tests.
- [x] Orchestrator integration — ✅ 2026-04-05. Feature flag `tool_output_compression` (env `TOOL_OUTPUT_COMPRESSION`). Wired at `helpers.py:1497` before `_spill_if_truncated()`.
- [ ] Enable flag in production and measure net savings on real autopilot sessions
- [x] A/B comparison: tool_output_compression on vs off — ✅ 2026-04-10 (Package B). Controlled A'/B' rerun (5 suites × 20q, WS-3 fix active). **Compression +4pp REPL overall.** Suite-dependent: math +25pp (noise reduction), hotpotqa -25pp (retrieval context lost). No change to default (ON).
- [x] P3a: Token audit of tool definitions — ✅ 2026-04-09. `token_audit.py` + report. 841 tokens, 4 duplicates, 29.8% instruction ratio.
- [x] P3b: Manual compression of `DEFAULT_ROOT_LM_TOOLS` — ✅ 2026-04-09. 55% reduction (647→290 words). Old preserved as `VERBOSE_ROOT_LM_TOOLS`. Ratio → 16.0%.
- [ ] P3d: A/B test compressed vs original on seeding harness

### P2 — Reasoning Compression (deferred)

- [ ] Generate SEAL control vectors for Qwen3-32B (Action 8 — 2-day experiment). Prep scripts READY: `epyc-inference-research/scripts/seal/generate_pairs.py` (80 problems), `eval_cvectors.py` (scaling sweep). Experiment doc: `docs/experiments/seal-concise-reasoning.md`.
- [ ] Summarizer quality assessment — `eval_summarizer.py` READY (created 2026-04-07), needs model servers to run (→ Package C)
- [ ] Free-zone compression threshold sweep — `eval_compaction_sweep.py` READY (implemented 2026-04-07), needs model servers to run (→ Package C)
- [x] Helpfulness scoring calibration — ✅ 2026-04-07. `run_calibration()` implemented (pure heuristic). Tested on 250 traces: Spearman ρ=0.63-0.65, overlap-heavy config best (separation=0.37, NDCG=0.998). Package C LLM-based Δ_k eval still pending.

### P2.5 — Memento Block Reasoning Compression (Tier 3+ research)

See [memento-block-reasoning-compression.md](memento-block-reasoning-compression.md). Deep-dive: `research/deep-dives/memento-iterative-reasoning-cluster.md`.

- [ ] S1: llama.cpp block masking feasibility — evaluate `llama_kv_self_seq_rm()` as block eviction primitive. Depends on v3 upstream KV API maturity.
- [ ] S2: LoRA SFT on Qwen3-32B using OpenMementos-228K. Two-stage (format + compression learning). Blocked on S1.
- [ ] S3: Deployment integration — block masking + Fold/Unfold toggle + m@k voting + Hadamard q4_0 stacking. Blocked on S1+S2.

### P3 — Long-Context Evaluation Datasets

- [x] Download LongBench — ✅ 2026-04-05. Using v2 (parquet-native, 503 MCQ). v1 uses deprecated HF scripts.
- [x] Download RULER — ✅ 2026-04-05. Cloned, adapter generates NIAH tasks at configurable lengths.
- [x] Download ZeroSCROLLS — ✅ 2026-04-05. 538 examples (10 tasks), raw zip download.
- [x] Download L-Eval — ✅ 2026-04-05. 514 examples (20 tasks), raw JSONL download.
- [x] Complete Needle-in-a-Haystack integration — ✅ 2026-04-05. Parameterized: 5 lengths × 5 depths = 25 tests. Paul Graham essays haystack.
- [x] Create adapter scripts — ✅ 2026-04-05. `long_context_adapters.py` (5 classes), registered in `dataset_adapters.py` + `suites.py`.
- [x] Validation — ✅ 2026-04-05. All 5 suites: OK (1,630 total questions).

### P4 — YaRN Context Extension (when datasets ready)

- [ ] Benchmark quality degradation curve from 256K → 512K → 1M with YaRN
- [ ] Measure KV cache memory impact at 1M context
- [ ] Measure speed impact of YaRN extension

### P5 — Harness Engineering Experiments (from intake-271/272/273/274 deep-dive)

- [ ] Bullet-vs-narrative consolidation A/B test: run CF Phase 2a eval suite with two compaction summary formats (structured narrative vs flat bullet-point). Tests whether context rot shuffled finding (intake-273) has signal for reasoning tasks. Low cost, high signal. (→ Package C)
- [ ] Documentation-stripped ablation: replicate intake-272 methodology on our repos. Strip all `.md`, run evals with vs without thin-map agent files. Isolates whether our agent files provide value beyond existing documentation. (→ Package B or standalone)
- [ ] `task_relevance` as candidate 5th signal in `segment_helpfulness()`: prototype semantic similarity (all-MiniLM-L6-v2, CPU) between segment text and current task description. Depends on bullet-vs-narrative results before shipping. (Design only until Package C data)

### P6 — REPL Turn Efficiency (from intake-295/301)

See [repl-turn-efficiency.md](repl-turn-efficiency.md). Addresses the Omega finding: 7/10 suites where REPL tools hurt accuracy. Complementary to WS-1/WS-3 prompt-level fixes.

- [x] S1a: Implement `file_recency.py` frecency module — ✅ 2026-04-09. `FrecencyStore` class, SQLite, 10 tests.
- [x] S1b-c: Wire into `_list_dir()` + `code_search()` (feature-flagged `REPL_FRECENCY`) — ✅ 2026-04-09. 7 wiring tests.
- [x] S2a-b: Mine autopilot logs + implement combined ops — ✅ 2026-04-09. Finding: only web_search/search_wikipedia used (file tools never called). `_CombinedOpsMixin` with `batch_web_search`, `search_and_verify`, `peek_grep`. Flag: `REPL_COMBINED_OPS`. 18 tests.
- [ ] S4: A/B benchmark turn count reduction on seeding harness

### P2.5 — Knowledge Base Governance (from intake-268/269/270/277)

- [x] **Phase 5a**: Create `wiki.yaml` config, fix hardcoded paths, create `wiki/SCHEMA.md` living taxonomy — ✅ 2026-04-07
- [x] **Phase 5b**: Build lint operation into project-wiki skill (5 passes, config-driven) — ✅ 2026-04-07
- [x] **Phase 5c**: Build query operation ("what do we know about X?") — ✅ 2026-04-07
- [x] Add credibility scoring to research-intake skill Phase 2 — ✅ 2026-04-07
- [x] Add anti-confirmation-bias directive to research-intake Phase 3 — ✅ 2026-04-07
- [x] Update intake-268/269/270 verdicts and cross-references — ✅ 2026-04-06
- [x] **Phase 5d**: Upstream project-wiki skill to root-archetype — ✅ 2026-04-07
- [x] Session persistence documentation for research workflows — ✅ 2026-04-07
- [x] qmd semantic search addon documentation — ✅ 2026-04-07

### P0.5 — Brevity Prompt Upgrade (from intake-276 deep-dive)

- [x] **Action 12**: Replace "be concise" with explicit word limits in worker prompts — ✅ 2026-04-09. Format-specific templates in worker_general.md + worker_math.md.
- [x] **Action 13**: Model-tier-differentiated conciseness — ✅ 2026-04-09. Audit + thinking_reasoning suffix update.
- [x] **Action 14**: Add OAA metric + per-token intelligence measurement to eval framework — ✅ 2026-04-07.
- [ ] **Action 15**: Evaluate TALE dynamic budget estimation — eval script ready (eval_tale_budget.py), awaiting model servers.
- [x] Upstream linter + templates to root-archetype — ✅ 2026-04-09. Generalized `lint_wiki.py` (dynamic root, configurable paths). 4 brevity templates in `_templates/prompts/`. Companion handoff: [root-archetype-linter-templates-upstream.md](root-archetype-linter-templates-upstream.md).

### Monitoring (no action unless triggered)

- [ ] **TQ3**: Watch PR #21038 for merge, evaluate PR #21089 when merged, read ChunkKV paper
- [ ] **ConceptLM**: Quarterly check for open-weight concept-level models or framework support
- [ ] **Multiscreen**: Monitor for community reproduction, model releases, or llama.cpp PRs

---

## Dependency Graph

```
P0 (reasoning-compression TrimR)  ──independent──
P1 (tool-output-compression RTK)  ──independent──
P2 (reasoning SEAL vectors)       ──depends on model server availability──
P2.5 (KB governance improvements) ──independent (companion: root-archetype linter)──
P3 (long-context datasets)        ──independent──
P4 (YaRN extension)               ──depends on P3 (datasets)──
P5 (harness engineering experiments)  ──depends on P3 (datasets) + Package B/C results──
P6 (REPL turn efficiency)            ──S1 independent; S2 depends on autopilot log data; S4 depends on seeding harness──
TQ3 monitoring                    ──depends on upstream PR merges──
ConceptLM monitoring              ──depends on external model releases──
Multiscreen monitoring            ──depends on external adoption──
```

---

## Cross-Cutting Concerns

1. **Reasoning compression ↔ routing-intelligence**: TrimR evaluation uses `debug_scorer.py`, same scorer infrastructure as factual-risk routing. `difficulty_signal.py` (shadow mode) is shared between reasoning token budgets and routing decisions. Changes to scorer must be coordinated.

2. **Tool output compression ↔ context-folding**: Complementary layers — tool-output-compression reduces inputs, context-folding compresses conversation history. Together they multiplicatively reduce context pressure. Phase 0 RTK trial results should inform context-folding Phase 1 design (if RTK handles tool outputs, Phase 1 can focus purely on conversation history).

3. **Long-context datasets ↔ KV cache quantization**: Datasets collected here serve both YaRN evaluation and TurboQuant KV cache quality validation (kv-cache-quantization.md Phase 3d). Coordinate dataset format with benchmark scripts.

4. **Summarizer quality ↔ context-folding Phase 2a/2b/2c**: Phase 2b (free-zone sweep) and Phase 2c (helpfulness calibration) both require eval infrastructure. Helpfulness calibration (LLM-based Δ_k ground truth) is the most expensive eval — schedule with other benchmark runs. Literature basis: Skill0 (intake-261) helpfulness-driven curriculum, AgentOCR (intake-262) compression quality thresholds.: reasoning-compression's summarizer quality assessment and context-folding Phase 2 share the same eval methodology (Claude-as-Judge scoring). Implement once, use in both.

5. **Bulk Inference Campaign**: Tasks P0 (TrimR, Omega, difficulty validation), P1 (tool compression A/B), and P2 (summarizer quality, free-zone, helpfulness) are consolidated into Packages B and C of [`bulk-inference-campaign.md`](bulk-inference-campaign.md). Package B (seeding eval v2) resolves P0+P1 tasks in a single full-stack run. Package C (CF eval batch) resolves P2 tasks using individual model servers. See that handoff for execution schedule, feature flags, and success criteria.

7. **Knowledge base governance ↔ root-archetype**: The KB linter and skill template patterns from P2.5 are being upstreamed to root-archetype via a companion handoff (`/mnt/raid0/llm/root-archetype/handoffs/active/knowledge-base-linter.md`). Epyc-root deploys the linter first as an instance-specific validator, then the generalized version goes to root-archetype. The credibility scoring and anti-confirmation-bias changes are research-intake skill edits that may also be templated in root-archetype's skill scaffold.

8. **Tool output compression ↔ Complexity Trap validation**: intake-274 ("The Complexity Trap") validates our two-layer architecture — pattern-based tool compression upstream, LLM conversation summarization downstream. The hybrid finding (7-11% further cost reduction) confirms this design is near-optimal. Package B tool compression A/B will be the first empirical confirmation on our stack. This also informs context-folding: observation masking (stripping old tool outputs) is equivalent to high recency weight in `segment_helpfulness()`.

9. **REPL turn efficiency ↔ Omega problem**: Turn reduction (P6) and WS-1/WS-3 prompt fixes address the same root cause — tools hurt accuracy on 7/10 suites — from different angles. P6 reduces wasted tool calls structurally (frecency, combined ops); WS-1/WS-3 tighten tool-use policy in prompts. Both should be measured together in WS-2 Omega re-run. Risk: contextual suggestions (S3) may worsen the problem if they encourage more tool use.

6. **Research intake deep-dive caveats (2026-04-06)**: intake-264 (SSD) downgraded to monitor-only — requires 8×B200 SFT, not actionable for inference-only stack. intake-266 (OPD Survey) downgraded to reference-only — training-only methods, agent distillation already solved by SkillBank. No new tasks generated from either. Caveats appended to reasoning-compression.md.

---

## Reporting Instructions

After completing any task:
1. Check the task checkbox in this index
2. Update the relevant handoff document with findings
3. Add entry to `progress/YYYY-MM/YYYY-MM-DD.md`
4. If findings affect production systems, flag in `routing-and-optimization-index.md`

---

## Key File Locations

| Resource | Path |
|----------|------|
| TrimR evaluation script | `epyc-inference-research/scripts/benchmark/eval_trimr.py` |
| Difficulty signal classifier | `epyc-orchestrator/src/classifiers/difficulty_signal.py` |
| Classifier config | `epyc-orchestrator/orchestration/classifier_config.yaml` |
| Reasoning length alarm | `epyc-orchestrator/src/graph/helpers.py` |
| Output spill utility | `epyc-orchestrator/src/graph/helpers.py` (`_spill_if_truncated()`) |
| Eval datasets target | `/mnt/raid0/llm/data/eval/` |
| Benchmark scripts | `epyc-inference-research/scripts/benchmark/` |
| Research intake index | `epyc-root/research/intake_index.yaml` |
| Cross-reference map | `epyc-root/.claude/skills/research-intake/references/cross-reference-map.md` |
| File exploration (REPL) | `epyc-orchestrator/src/repl_environment/file_exploration.py` |
| Tool definitions | `epyc-orchestrator/src/prompt_builders/constants.py` |
| TOON encoder | `epyc-orchestrator/src/services/toon_encoder.py` |
