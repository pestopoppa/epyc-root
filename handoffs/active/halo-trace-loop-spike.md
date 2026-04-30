# HALO Trace-Loop Spike

**Status**: ready-to-claim (1-day spike + conditional Day 2)
**Created**: 2026-04-30 (post-intake-517/518 deep-dive)
**Categories**: agent_architecture, autonomous_research, tool_implementation
**Priority**: MEDIUM (validates whether to lift HALO patterns into existing meta-harness/autopilot scope)
**Depends on**: `meta-harness-optimization.md`, `autopilot-continuous-optimization.md`, `unified-trace-memory-service.md`
**Source deep-dive**: [`/workspace/research/deep-dives/halo-rlm-trace-loop-integration.md`](../../research/deep-dives/halo-rlm-trace-loop-integration.md)

## Objective

Validate whether `halo-engine` (intake-518, MIT, 2.5 MB pip install) produces actionable diagnostic reports against EPYC orchestrator traces — not just AppWorld traces. If yes, **lift the patterns manually** into existing scoped work (do NOT vendor halo-engine). If no, close out and rely on autopilot's existing trace summarization.

## Research Context

| Intake ID | Title | Relevance | Verdict |
|-----------|-------|-----------|---------|
| intake-517 | context-labs/HALO — Hierarchical Agent Loop Optimizer | high | adopt_patterns |
| intake-518 | halo-engine PyPI 0.1.2 (deployable artifact) | medium | worth_investigating |
| intake-516 | HALO-Gemini-3-Flash-AppWorld dataset (168 traces) | medium | worth_investigating (DEFERRED — see §AppWorld below) |
| intake-153 | RLM foundational paper (Zhang/Kraska/Khattab arxiv:2512.24601) | high | already_integrated (~80% pattern coverage) |

## Key Findings From Deep-Dive (informs spike scope)

- **Autopilot already emits OTLP-shaped spans** via `scripts/autopilot/telemetry.py:to_otlp_span` (since 2026-04-12). The OTel converter is **~30 LoC** for autopilot telemetry, ~120 LoC for inference-tap. Total spike code including tests: **~200 LoC**.
- **HALO is `0.1.2` released 2 days before this audit** — pre-1.0 churn likely; CLI default `max_depth=1` matches Tier-2b warning; report is free-text markdown (parse step needed).
- **Backend is `OPENAI_BASE_URL`-swappable** (`engine/model_provider_config.py`) → run halo's analyzer against our local llama-server, no cloud dependency.
- **Net-new patterns worth lifting** (3): six-tool trace-query analyzer surface, two-file JSONL+byte-offset trace store, dev/test_normal split discipline.
- **Duplicate of existing coverage** (5): OTel span emission (intake-338 done), trace-driven mutator (intake-244 Tier-1 done), code-mutation search (Tier-2 done), GEPA evolution (intake-345 done), RLM REPL recursion (intake-153 R1-R6 done).
- **Failure-mode taxonomy**: 4 labels (hallucinated tool calls, redundant args, refusal loops, semantic correctness). Complementary to intake-509 Pocock 4-mode taxonomy already in meta-harness scope.

## Tasks

### HALO-1: Pre-flight verification [30 min]

```bash
python -m venv /tmp/halo-spike-venv && source /tmp/halo-spike-venv/bin/activate
pip install halo-engine==0.1.2
# Run on bundled tiny_traces.jsonl from the repo
halo --help
# Verify OPENAI_BASE_URL swap to local llama-server
export OPENAI_BASE_URL=http://localhost:8090/v1   # or whatever model is up
export OPENAI_API_KEY=local
halo path/to/tiny_traces.jsonl -p "diagnose"
```

**Gate**: halo-engine installs cleanly, runs against bundled traces, accepts local-llama backend.

### HALO-2: Build OTel converter [Day 1 AM, 4 h]

Write `/workspace/scripts/halo/convert_tap_to_otel.py` with two converters:

- `convert_autopilot_telemetry()` — **~30 LoC**. Autopilot's `telemetry.py:to_otlp_span()` already produces OTLP-shaped JSON. Group spans into traces by trial_id and emit JSONL.
- `convert_inference_tap()` — **~120 LoC**. Block parser (~30) + PROMPT/RESPONSE pair extraction (~20) + trace grouping (~20) + OpenInference attribute mapping (~15) + hierarchy assembly (~25) + writer (~10).
- 4 unit tests (~80 LoC).

Convert ONE existing autopilot trial's telemetry to OTel JSONL. Run halo against it.

### HALO-3: Day 1 PM falsification gate [4 h]

Inspect the halo report against 4 criteria. **Need ≥3/4 to proceed to Day 2.**

| # | Criterion | Pass condition |
|---|-----------|----------------|
| 1 | Report cites real `trace_id` / `span_id` from converted trace | YES = literal IDs appear, not generic phrases |
| 2 | Flags ≥1 known orchestrator pathology | YES = at least one true positive against known autopilot failure modes (e.g., specific drafter-target token mismatch class, q-scorer misroute, session_compaction info loss) |
| 3 | More granular than current `capture_recent_traces(n=50)` PromptForge feedback | YES = surfaces pattern-level finding rather than per-trace anecdote |
| 4 | Bounded cost (≤ $0.50 OR ≤ 10 min wall-clock against local llama-server) | YES = within budget |

If ≥3/4 pass → proceed to HALO-4. If ≤2/4 → close handoff with `outcome: not_actionable` and write findings to `/workspace/research/deep-dives/halo-spike-results-2026-MM-DD.md`.

### HALO-4: Day 2 — Manual pattern lift (only on full-go)

**DO NOT VENDOR halo-engine.** Lift the 3 net-new patterns into existing scoped work:

- **Six-tool trace-query analyzer surface** + **two-file JSONL+byte-offset store**: extends `unified-trace-memory-service.md` T1 (trace ingestion) + T5 (analyzer agent). Estimate ~230 LoC new code into existing scope.
- **dev/test_normal split discipline**: extends `meta-harness-optimization.md` Tier 3 (anti-overfitting guard) and `eval-tower-verification.md` (split convention). Mostly methodology change + script glue, ~50 LoC.
- **Failure-mode taxonomy** (4 labels): seed labels for autopilot trace-clustering pass. Cross-ref intake-509 Pocock taxonomy (already in meta-harness scope).

Track each lift as a sub-task with its own line-count estimate; check off as merged.

### HALO-5: Spike close-out

Write outcome doc at `/workspace/research/deep-dives/halo-spike-results-2026-MM-DD.md`:

- Pre-flight gate result (HALO-1)
- Converter LoC actual vs estimate (HALO-2)
- 4-criterion gate scorecard (HALO-3)
- Lifted patterns and merge SHAs (HALO-4) OR `not_actionable` reasoning
- Whether to revisit halo-engine for a future use case (e.g., new model release in 6 months)

## AppWorld decision (intake-516 dataset)

**DEFER and skip the dataset** for this spike. Rationale:

- Hardware-feasible (no GPU/Docker; FastAPI in-process; ~5s first task / <0.5s subsequent).
- But integration cost is **3-5 days** (orchestrator wiring, SGC scorer, dev/test_normal split runs, baseline runs).
- **No current eval gap demanding it.** 168 traces is reference-scale, not training-scale.
- Revisit when an autopilot signal explicitly demands a long-horizon multi-tool benchmark, or when meta-harness Tier 3 needs an external reference benchmark for the dev/test_normal split discipline.

If the AppWorld decision flips later, scope it as a separate handoff (`appworld-eval-integration.md`), not as a sub-task of this spike.

## Risks (carried from deep-dive)

- HALO `0.1.2` is pre-1.0 — API surface may break in 0.2.x; pin version.
- Default `max_depth=1` in OSS RLM impls suggests the recursive-depth claim is harder to operationalize than the paper implies.
- Default analyzer model is `gpt-5.4-mini`; first test should validate whether a local 30B-A3B coder produces coherent reports BEFORE committing to the spike.
- Report is free-text markdown not structured JSON — adds a parse step if we want machine-actionable output.

## Reporting Instructions

After spike completion, update:

- This file with HALO-5 outcome reference and final status (`completed-success` or `completed-not-actionable`)
- `meta-harness-optimization.md` 2026-04-30 section with concrete merge results or `closed: not actionable`
- `autopilot-continuous-optimization.md` 2026-04-30 section similarly
- `progress/2026-04/2026-MM-DD.md` with one-paragraph summary

## Cross-references

- Deep-dive: `/workspace/research/deep-dives/halo-rlm-trace-loop-integration.md`
- Intake entries: intake-516, intake-517, intake-518, intake-153 (RLM foundational, already_integrated)
- Active handoffs: meta-harness-optimization, autopilot-continuous-optimization, unified-trace-memory-service, eval-tower-verification
