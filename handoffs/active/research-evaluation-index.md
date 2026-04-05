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
| [reasoning-compression.md](reasoning-compression.md) | Reasoning token optimization | in-progress (Tier 1 deployed) | HIGH | 2026-04-04 |
| [tool-output-compression.md](tool-output-compression.md) | Tool output token reduction | stub (Phase 0 next) | MEDIUM | 2026-04-04 |
| [multiscreen-attention-evaluation.md](multiscreen-attention-evaluation.md) | Novel attention mechanism | stub (WATCH) | LOW | 2026-04-04 |
| [yarn-context-extension-research.md](yarn-context-extension-research.md) | Context extension via YaRN | stub | LOW | 2026-03-25 |
| [long-context-eval-datasets.md](long-context-eval-datasets.md) | Eval dataset collection | stub | MEDIUM | 2026-03-26 |
| [tq3-quantization-evaluation.md](tq3-quantization-evaluation.md) | TQ3/TurboQuant monitoring | monitoring (do NOT merge) | LOW | 2026-04-01 |
| [11-conceptlm-monitoring.md](11-conceptlm-monitoring.md) | Concept-level LM monitoring | monitoring (watch-only) | LOW | 2026-03-03 |

---

## Outstanding Tasks (Priority Order)

### P0 — Reasoning Compression (actionable now)

- [ ] Run TrimR evaluation on math/gpqa suites (requires model server) — `eval_trimr.py`
- [ ] Collect shadow telemetry from `difficulty_signal.py` in production
- [ ] Validate difficulty signal predictive power against benchmark accuracy
- [ ] If validated: implement enforce mode (route easy→worker, hard→architect)
- [ ] Compute Omega metric per-suite to identify where reasoning is wasted (Action 6)

### P1 — Tool Output Compression (evaluate RTK)

- [ ] Install RTK binary with `RTK_TELEMETRY_DISABLED=1`
- [ ] Run one autopilot session with RTK enabled, collect `rtk gain` metrics
- [ ] Compare net savings (input reduction minus output compensation) against baseline
- [ ] Go/no-go decision: net ≥40% savings, no EAGAIN errors, no quality regression
- [ ] If no-go: begin Phase 2 native hook implementation (P0 commands: test runners, git status, git diff)

### P2 — Reasoning Compression (deferred)

- [ ] Generate SEAL control vectors for Qwen3-32B (Action 8 — 2-day experiment)
- [ ] Summarizer quality assessment — shared with `context-folding-progressive.md` Phase 2a
- [ ] Free-zone compression threshold sweep — `context-folding-progressive.md` Phase 2b (intake-261/262)
- [ ] Helpfulness scoring calibration — `context-folding-progressive.md` Phase 2c (intake-261)

### P3 — Long-Context Evaluation Datasets

- [ ] Download LongBench to `/mnt/raid0/llm/data/eval/`
- [ ] Download RULER
- [ ] Complete Needle-in-a-Haystack integration
- [ ] Create adapter scripts in `epyc-inference-research/scripts/benchmark/`

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
