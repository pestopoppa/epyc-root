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
| [reasoning-compression.md](reasoning-compression.md) | Reasoning token optimization | in-progress (Tier 1 deployed) | HIGH | 2026-04-06 |
| [tool-output-compression.md](tool-output-compression.md) | Tool output token reduction | Phase 2 native implemented (feature-flagged) | MEDIUM | 2026-04-05 |
| [multiscreen-attention-evaluation.md](multiscreen-attention-evaluation.md) | Novel attention mechanism | stub (WATCH) | LOW | 2026-04-04 |
| [yarn-context-extension-research.md](yarn-context-extension-research.md) | Context extension via YaRN | stub | LOW | 2026-03-25 |
| [long-context-eval-datasets.md](long-context-eval-datasets.md) | Eval dataset collection | READY (5 datasets, adapters integrated) | MEDIUM | 2026-04-05 |
| [tq3-quantization-evaluation.md](tq3-quantization-evaluation.md) | TQ3/TurboQuant monitoring | monitoring (do NOT merge) | LOW | 2026-04-01 |
| [11-conceptlm-monitoring.md](11-conceptlm-monitoring.md) | Concept-level LM monitoring | monitoring (watch-only) | LOW | 2026-03-03 |

---

## Outstanding Tasks (Priority Order)

### P0 — Reasoning Compression (actionable now)

- [ ] Run TrimR evaluation on math/gpqa suites (requires model server) — `eval_trimr.py` (→ Package B, see [`bulk-inference-campaign.md`](bulk-inference-campaign.md))
- [x] Collect shadow telemetry from `difficulty_signal.py` in production — ✅ 2026-04-06. 635 requests, Package A run.
- [x] Validate difficulty signal predictive power against benchmark accuracy — ✅ 2026-04-06. Thresholds recalibrated (0.3/0.6 → 0.15/0.35). Re-validate at new thresholds needed.
- [ ] If validated: implement enforce mode (route easy→worker, hard→architect) (depends on Package B results)
- [ ] Compute Omega metric per-suite to identify where reasoning is wasted (Action 6) (→ Package B)

### P1 — Tool Output Compression

- [x] ~~Install RTK binary~~ — SKIPPED: PostToolUse hooks cannot replace built-in tool output. Phase 0 RTK trial deferred.
- [x] Phase 2 native compression module — ✅ 2026-04-05. `compress_tool_output.py` with 7 handlers (pytest, cargo test, git status/diff/log, ls, build). 27 tests.
- [x] Orchestrator integration — ✅ 2026-04-05. Feature flag `tool_output_compression` (env `TOOL_OUTPUT_COMPRESSION`). Wired at `helpers.py:1497` before `_spill_if_truncated()`.
- [ ] Enable flag in production and measure net savings on real autopilot sessions
- [ ] A/B comparison: tool_output_compression on vs off (→ Package B)

### P2 — Reasoning Compression (deferred)

- [ ] Generate SEAL control vectors for Qwen3-32B (Action 8 — 2-day experiment)
- [ ] Summarizer quality assessment — shared with `context-folding-progressive.md` Phase 2a (→ Package C)
- [ ] Free-zone compression threshold sweep — `context-folding-progressive.md` Phase 2b (intake-261/262). Eval skeleton: `eval_compaction_sweep.py --dry-run` ready. (→ Package C)
- [x] Helpfulness scoring heuristic — ✅ 2026-04-05. `segment_helpfulness()` + `prioritized_compaction()` in `session_log.py`. LLM-based calibration deferred: `eval_helpfulness_calibration.py --dry-run` ready.

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
P3 (long-context datasets)        ──independent──
P4 (YaRN extension)               ──depends on P3 (datasets)──
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
