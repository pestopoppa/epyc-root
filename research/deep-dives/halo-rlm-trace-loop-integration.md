# Deep Dive: HALO RLM-Trace-Loop Integration on EPYC

**Sources**: intake-516 (HuggingFace `inference-net/HALO-Gemini-3-Flash-AppWorld`), intake-517 (`github.com/context-labs/halo`), intake-518 (`pypi.org/project/halo-engine`)
**Date**: 2026-04-30
**Scope**: Refine the recommended `halo-engine` 1-day spike against actual EPYC trace infrastructure; replace verdict (`adopt_patterns` / `worth_investigating`) with concrete go/no-go criteria.

## TL;DR

The trio's claims are credible (≈9-day-old repo, 179 stars, MIT, 5 contributors, `2.5 MB` sdist, Python ≥3.10, AppWorld SGC +10.7 pts on Sonnet 4.6 / Gemini 3 Flash). But against EPYC's existing infrastructure the unique value is **narrow**: we already implement an OTLP-compatible per-step span format (`scripts/autopilot/telemetry.py:to_otlp_span`), already feed traces back into a mutator (PromptForge Tier-1 `capture_recent_traces`), already have a unified-trace handoff scoped (`unified-trace-memory-service.md`), and already cover ≈80% of the foundational RLM patterns (intake-153, `rlm-orchestrator-roadmap.md` archived 2026-03-29 with R1–R6 done).

What HALO adds that we don't have:
1. **Two-file trace store** (canonical JSONL + sidecar byte-offset index) for random-access span retrieval at scale.
2. **Six-tool trace-querying analyzer agent** (`get_dataset_overview`, `query_traces`, `count_traces`, `view_trace`, `search_trace`, `view_spans`) with size-aware truncation (4 KB discovery / 16 KB surgical).
3. **Compaction + synthesis prompt templates** specialized for trace traversal (vs our generic context compaction).
4. **dev/test_normal anti-overfitting split discipline** (AppWorld convention).
5. **Concrete failure-mode taxonomy as analyzer output**: hallucinated tool calls, redundant args, refusal loops, semantic correctness errors.

Refined verdict: **REFINE the original spike plan but keep the 1-day gate.** Run halo-engine on a single converted autopilot trace; if the report adds signal beyond what `capture_recent_traces` already provides, lift patterns 1–5 manually into our stack (do **not** vendor halo-engine — its OTel-flavoured schema and OpenAI-Agents-SDK runner do not match our REPL graph cleanly). The OTel converter cost is `~80–120 LoC` and is anyway useful for the unified-trace-memory-service work.

AppWorld pairing: **defer**. Setup is feasible (no Docker/GPU required, FastAPI TestClient in-process) but the ~457-API simulator + 100-person world is multi-GB and tangential to current CPU-optimization pole.

---

## 1) Project Anatomy (intake-517 / 518)

### Repo layout (`context-labs/halo`)

```
halo/
  engine/
    __init__.py                 # __version__ = "0.1.0"
    main.py                     # stream_engine_async / run_engine — orchestrator
    engine_config.py            # EngineConfig (root_agent, subagent, synthesis_model, compaction_model)
    model_config.py             # ModelConfig (per-agent model + decode params)
    model_provider_config.py    # OpenAI base_url; supports vLLM/Together/Groq/Ollama/LM Studio
    errors.py
    agents/                     # 12 files — agent_config, agent_context, agent_execution,
                                #   compactor, engine_output_bus, engine_run_state,
                                #   openai_agent_runner, openai_event_mapper,
                                #   prompt_templates, runner_protocol
    models/                     # (under engine/, separate from traces/models)
    sandbox/runner.js           # Deno-bundled WASM sandbox for run_code_tool
    tools/                      # agent_context_tools, run_code_tool, subagent_result,
                                #   subagent_tool_factory, synthesis_tool, tool_protocol,
                                #   trace_tools  ← the six-tool surface
    traces/
      trace_store.py            # JSONL load + byte-offset seeking, SpanRecord(extra="allow")
      trace_index_builder.py    # Parallel ProcessPoolExecutor index build (≤8 workers)
      models/
        canonical_span.py
        trace_index_config.py
        trace_index_models.py   # TraceIndexRow with byte_offsets/byte_lengths
        trace_query_models.py
  halo_cli/
    main.py                     # Typer/Rich CLI; entry point `halo`
  demo/                         # incl. OpenAI Agents SDK example
  docs/integrations/
  tests/fixtures/
    tiny_traces.jsonl           # 3 traces, OpenInference-flavoured OTel JSONL
    medium_traces.jsonl
    realistic_traces.jsonl
    _generate_medium_traces.py
```

### Engine defaults

From `EngineConfig` (Pydantic, `extra="forbid"`):

| Field | Default | Notes |
|---|---|---|
| `text_message_compaction_keep_last_messages` | `12` | Recent-message cap |
| `tool_call_compaction_keep_last_turns` | `3` | Recent tool-turn cap |
| `maximum_depth` | `2` | Subagent recursion (CLI default `1`) |
| `maximum_parallel_subagents` | `4` | Concurrent subagents |
| `model` (CLI) | `gpt-5.4-mini` | Per `halo_cli/main.py` |
| `max_turns` (CLI) | `8` | Per CLI |

### Tool surface exposed to the RLM analyzer

```text
get_dataset_overview()                  # counts/services/models/sample_trace_ids
query_traces(limit, offset, filter)     # paginated trace list
count_traces(filter)                    # cardinality without materialization
view_trace(trace_id)                    # all spans, attrs capped ~4 KB
search_trace(trace_id, pattern)         # substring match e.g. STATUS_CODE_ERROR / tool name
view_spans(trace_id, span_ids)          # surgical fetch, attrs capped ~16 KB
```

These tools are the substantive contribution. They turn an over-long span tree into a navigable corpus the analyzer can REPL over (the original `intake-153` RLM idea, but specialized for OTel JSONL).

### Default analyzer system prompt (paraphrased from `engine/agents/prompt_templates.py`)

Seven mandatory rules: (1) always call `get_dataset_overview` first to obtain real trace IDs (no hallucination), (2) `query_traces` for pagination, (3) `count_traces` for cardinality, (4) inspection method depends on size with ≈50-spans threshold, (5) `search_trace` for `STATUS_CODE_ERROR` or tool name on large traces, (6) recognize `oversized` responses and follow recovery, (7) emit `<final/>` sentinel only at depth 0.

Two specialized prompts: `COMPACTION_SYSTEM_PROMPT` (preserves tool names + arg structures) and `SYNTHESIS_SYSTEM_PROMPT` (cross-trace findings).

### OTel schema details (per `engine/traces/trace_store.py`)

`SpanRecord` is Pydantic with `extra="allow"`. Fields explicitly used: `span_id`, `parent_span_id`, `name`, `kind`, `status.code` (e.g. `STATUS_CODE_ERROR`), `start_time`, `end_time`, `attributes`. Standard attribute keys observed in fixtures: `inference.llm.model_name`, `inference.llm.input_tokens`, `inference.llm.output_tokens`, `service.name`, `cost.total_usd`. This is **OpenInference**-flavoured OTLP — a superset of strict OTLP that adds LLM-specific keys. Schema is permissive; extra keys are accepted.

### CLI ergonomics

```bash
halo path/to/traces.jsonl -p "Diagnose errors and suggest fixes"
# --model gpt-5.4-mini --max-depth 1 --max-turns 8 --max-parallel 2 --instructions ...
```

`OPENAI_API_KEY` is the only hard requirement; `OPENAI_BASE_URL` swap to a local llama-server is supported (`model_provider_config.py` documents vLLM/Together/Groq/Ollama/LM Studio).

### Report format

The README does not specify (JSON vs Markdown). `<final/>` sentinel suggests the analyzer emits a free-text final assistant message — i.e., **markdown, not structured JSON**. Downstream coding-agent ingestion is therefore a free-text hand-off, not a typed artifact. (Implication for our pipeline: parse-and-extract step needed if we want structured failure tags.)

### Engine runner

`OpenAiAgentRunner.run()` uses `MAX_CONSECUTIVE_LLM_FAILURES = 10` with retry only when `events_seen == 0` (state-mutation-free retry). Built on the `openai-agents` SDK (v0.14.7) and `openai` (v2.32.0).

### Dataset (intake-516)

168 traces / 3,438 spans, Gemini 3 Flash on AppWorld test_normal. MIT, ≤10K rows, single `traces.jsonl`. Useful as a **schema reference**; insufficient as a training or fine-tuning corpus by itself.

---

## 2) AppWorld Benchmark Itself

| Property | Value |
|---|---|
| Apps | 9 (Amazon, Spotify, Venmo, Gmail, Slack, Uber, OpenTable, LinkedIn, Airbnb) + 2 helpers (ApiDocs, Supervisor) |
| APIs | 457 |
| DB tables | 100+ populated with simulated user activity |
| Population | ~100 simulated people |
| Docker | **Optional** (FastAPI TestClient in-process is the default) |
| GPU | **Not required** (CPU-only) |
| Per-task load | 4–5 s first task, <0.5 s subsequent (after init) |
| SGC eval runtime | Not stated explicitly; per-task latency dominated by agent calls, not env |
| License | Open (BSD/MIT-style; verify in repo) |

EPYC feasibility: **green light on hardware** (no GPU, no Docker, CPU OK). The cost is operational — wiring our orchestrator (Hermes + Qwen3.6 + 30B-A3B coder) into AppWorld's task-loop, building an SGC scorer, and producing dev/test_normal split runs. Roughly 3–5 days of integration work per `eval-tower-verification.md` patterns. **Defer** until a current eval gap clearly demands it.

---

## 3) RLM Foundational Coverage Audit (intake-153)

intake-153 (Zhang/Kraska/Khattab arxiv:2512.24601) is in our index as `already_integrated` with ≈80% pattern coverage per `rlm-orchestrator-roadmap.md` (R1–R6 closed 2026-02 to 2026-03).

| RLM concept | Our coverage | Source |
|---|---|---|
| Symbolic prompt handle (large input as variable) | Session compaction + virtual-memory index | `src/graph/helpers.py:_maybe_compact_context()` |
| REPL environment offloading | First-class — REPL is the orchestrator's primary worker mode | `src/repl_environment/` |
| Programmatic recursion via `llm_query()` | Architect → worker / specialist delegation | `src/api/routes/chat_delegation.py` |
| Context folding (4-phase) | Active handoff `context-folding-progressive.md` | (in-progress) |
| Budget propagation through sub-LM calls | R1 closed | `LLMPrimitives` request budget (2026-02-19) |
| Depth-based model override | R3 closed; production default-on | features `worker_depth_override` |
| Versioned persistence protocol | R4 closed (v1 boundary) | graph state restore |

What HALO adds **on top of** the RLM substrate:
- Specialized **trace-querying** RLM instead of generic-task RLM (the 6-tool surface).
- Two-file random-access store with byte-offset index (the foundational paper does not address this).
- dev/test_normal split as a meta-loop guard against overfitting.

These three are **net-new patterns** for us, not duplicates.

---

## 4) EPYC Trace Infrastructure Audit

### What we already log

| Surface | Format | Path | Scope |
|---|---|---|---|
| Inference tap | Per-call prompt/response, line-buffered | `/mnt/raid0/llm/tmp/inference_tap.log` (env `INFERENCE_TAP_FILE`) | Roles, timestamps, role-keyed blocks |
| Autopilot telemetry | OTLP-compatible JSONL | `orchestration/autopilot_telemetry.jsonl` | Per-trial transitions w/ `to_otlp_span()` |
| Autopilot journal | TSV + JSONL + state.json | `orchestration/autopilot_journal.{tsv,jsonl}`, `autopilot_state.json` | Per-trial decisions, Pareto archive |
| Agent audit | Tab-separated text | `logs/agent_audit.log` | `agent_task_start/end`, sessions |
| Progress narrative | Markdown + optional JSONL | `progress/YYYY-MM/*.md` | Per-day human-readable |
| Eval tower | Recent-trace tail | reads inference_tap.log via `capture_recent_traces(n=50)` | Tier-1 PromptForge feedback |
| Hermes sessions | JSON | `~/.hermes/sessions/*.json` (when used) | Conversation transcripts |

### Gap vs HALO's expected input

HALO requires **OpenInference-flavoured OTLP spans** with at minimum:

```json
{
  "trace_id": "...", "span_id": "...", "parent_span_id": "...",
  "name": "...", "kind": "INTERNAL",
  "status": {"code": "STATUS_CODE_OK"},
  "start_time_unix_nano": 0, "end_time_unix_nano": 0,
  "attributes": {
    "service.name": "...", "inference.llm.model_name": "...",
    "inference.llm.input_tokens": 0, "inference.llm.output_tokens": 0
  }
}
```

We already emit `to_otlp_span()` from `scripts/autopilot/telemetry.py` (Lines 57–80). The fields produced cover `traceId/spanId/parentSpanId/name/kind/startTimeUnixNano/endTimeUnixNano/attributes/status`. **The hard part is done.** Gaps:

1. `kind` must be set per span (we set `SPAN_KIND_INTERNAL` constant — fine).
2. `attributes` keys must match OpenInference conventions if HALO's analyzer prompt references them (`inference.llm.*`, `service.name`). We currently emit `trial_id/species/role/action_type/reward` — these are OK as extra attrs (HALO's `extra="allow"` accepts them) but the analyzer's stock prompt won't know what to do with them.
3. Span hierarchy: HALO expects nested per-trace span trees. Our autopilot telemetry is mostly flat (controller_reasoning → action_execution → safety_gate as siblings under one trial). For an inference-tap conversion, we'd need to assemble a tree from per-call records (root = chat request, children = orchestrator graph nodes).

### Concrete converter plan: inference_tap.log → OTel JSONL

Inference tap blocks look approximately like:

```
[2026-04-30 12:34:56] role=architect [PROMPT]
<prompt body>
[2026-04-30 12:34:58] role=architect [RESPONSE]
<response body>
```

A converter needs:
1. Block parser (regex on `[ts] role=X [PROMPT|RESPONSE]` headers) — `~30 LoC`.
2. Pair PROMPT/RESPONSE into one span per call — `~20 LoC`.
3. Group by request (heuristic: gap >5s starts a new trace; or use `session_id` if available in tap headers — `~20 LoC`).
4. Emit OpenInference attrs (`service.name="orchestrator"`, `inference.llm.model_name=<role>`, token counts if available else 0) — `~15 LoC`.
5. Build hierarchy (front_door → architect → worker_* → tool_call) using role transitions — `~25 LoC`.
6. JSONL writer with `to_otlp_span`-compatible shape — `~10 LoC`.

**Total: ~120 LoC** for a `scripts/halo/convert_tap_to_otel.py` standalone module. Test fixture: 3 hand-crafted tap blocks producing 1 trace with 3 nested spans. The autopilot telemetry path is faster (the JSON is already OTLP-shaped) — **`~30 LoC` to read `autopilot_telemetry.jsonl` and re-emit as a HALO-ingestible JSONL file** (needs `traceId` grouping per trial and `name` normalization).

---

## 5) Concrete Spike Plan (refines the original 1-day proposal)

### Pre-flight (30 min, before Day 1)

- Create venv: `python -m venv ~/.venvs/halo && source activate && pip install halo-engine==0.1.2`
- Verify CLI: `halo --help`
- Verify it works on the bundled fixture: `halo $(python -c "import halo_cli, pathlib; print(pathlib.Path(halo_cli.__file__).parent.parent / 'tests/fixtures/tiny_traces.jsonl')") -p "summarize"` — expect any output indicating successful run.
- Decide endpoint: either set `OPENAI_API_KEY` (real) or set `OPENAI_BASE_URL=http://127.0.0.1:8081/v1` + dummy key, pointing at our local `gpt-oss` server (or the QC30B-A3B server). Per `engine/model_provider_config.py` this is supported.

### Day 1 morning (4 h): converter + first run

Success criterion: HALO runs to completion on **one** real EPYC trace and produces non-trivial output.

| Step | Effort | Deliverable |
|---|---|---|
| Write `scripts/halo/convert_tap_to_otel.py` (autopilot_telemetry.jsonl variant first — simpler) | 30 min | ~30 LoC + 2 unit tests |
| Convert one autopilot trial's telemetry slab | 5 min | `tmp/halo_input.jsonl`, ≥3 spans |
| Run `halo tmp/halo_input.jsonl -p "Diagnose harness-level failure modes"` | 15 min | stdout report |
| Inspect report: tool calls used? trace ids correctly identified? error patterns flagged? | 30 min | written assessment |
| If trivial / vacuous → write `convert_tap_to_otel.py` for `inference_tap.log` (full ~120 LoC) | 2 h | second converter + test |
| Re-run on a richer inference-tap-derived trace | 30 min | second report for comparison |

### Day 1 afternoon (4 h): non-AppWorld signal assessment

Success criteria for **GO** at end of Day 1:
1. The report cites real `trace_id` / `span_id` values from the input (HALO actually inspected the trace, did not hallucinate).
2. The report flags **at least one** failure mode that matches a known orchestrator pathology (e.g., refusal loop, redundant tool args, excessive depth, repeated re-asks).
3. The report's failure-mode taxonomy is more granular than what `capture_recent_traces(n=50)` already feeds PromptForge.
4. The cost (tokens consumed for analysis) is bounded — set an OPENAI quota or local-model wallclock budget pre-run; abort if HALO exceeds 5× the analyzed trace's token count.

If 2/4 met: **partial-go**, recommend lifting patterns 1–3 from §0 manually but not vendoring halo-engine.
If 0–1/4 met: **no-go**, document and close. The intake-517 patterns still live in the meta-harness handoff for manual adoption.
If 3–4/4 met: **full-go**, schedule Day 2.

### Day 2 (only if GO) — manual pattern lift

Do **not** vendor halo-engine. Instead:

| Pattern | Where it lands | Effort |
|---|---|---|
| Two-file trace store (JSONL + byte-offset sidecar) | `epyc-orchestrator/src/trace/store.py` (already scoped in `unified-trace-memory-service.md` T1) | extends T1 by ~80 LoC |
| 6-tool trace-querying surface | `epyc-orchestrator/src/trace/query.py` extension (T5 of unified-trace handoff) — wrap as MCP tools or local Python API | ~150 LoC |
| dev/test_normal split discipline | `scripts/autopilot/eval_tower.py` — split sentinel set 50/50, require improvement on both before Pareto-promote | ~40 LoC + safety_gate hook |
| Failure-mode taxonomy for trace clustering | `scripts/autopilot/eval_tower.capture_contrastive_traces` (Tier 2b MH-7 already scoped) — adopt HALO's 4 categories as cluster labels | folds into MH-7 |
| Specialized analyzer system prompt | `orchestration/prompts/trace_analyzer.md` — new prompt file invoked by autopilot when a trace cluster needs harness-mutation reasoning | ~100 LoC prompt + 30 LoC dispatcher |

Total: ~3 days of implementation if all patterns adopted; one full week with tests + AR-3 validation. None of this requires halo-engine as a runtime dependency.

---

## 6) Risk Register

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| OTel schema is OpenInference-flavoured (non-strict OTLP) | High | Medium | Our converter emits permissive shape; HALO's `extra="allow"` accepts ours. Verify by running on `tiny_traces.jsonl` first. |
| Analyzer requires GPT-5-class reasoning | Medium | Medium | Default is `gpt-5.4-mini`; CLI lets us override. First test: try with `gpt-5.4-mini`. Fallback test: point `OPENAI_BASE_URL` at a local `qwen3-coder-30b` server. If small-model output is incoherent → vendor cost concern |
| Pre-1.0 churn: `0.1.2` released 2026-04-29, ≤2 days before this audit | High | Low | We pin `halo-engine==0.1.2` in the venv. Treat any breakage as a no-go signal (signal of fragility). |
| max_depth=1 default in CLI (intake-518 Tier 2b note re: OSS RLM) | Certain | Medium | Bumping max_depth raises cost super-linearly. Stay at 1 for spike. If signal weak, do not blindly raise — root cause is likely prompt or schema, not depth. |
| Free-text markdown report (no structured JSON) | High | Low | Parse-and-extract step adds ~40 LoC of regex/heuristic tagging. Manageable. |
| Single-bench scope (only AppWorld) | Certain | Medium | This is exactly why our spike runs on **non-AppWorld** traces. Day 1 PM gate is the falsification step. |
| Production fragility: latency spikes / format collapse / cost variance (intake-518 Tier 2b) | Medium | Medium | Spike is offline post-hoc analysis, not in the request path. Production fragility doesn't apply for our intended use. |
| Cost variance with frontier model | Medium | Low | Set `OPENAI_API_KEY` budget cap or use local endpoint. Worst case: one experiment costs ~$1–5. |
| Vendor lock-in via `openai-agents` SDK | Low | Low | We are not vendoring; spike is exploratory. |
| AppWorld dataset (168 traces) too small for fine-tuning | Certain | Low | We never proposed using it for training. Schema-reference role only. |

---

## 7) Decision Tree

```
                     Day 1 morning: converter + run
                                |
                  HALO runs to completion?
                          /        \
                       NO            YES
                       |              |
                  Document             Day 1 PM:
                  failure              non-AppWorld signal assessment
                  Close intake             /     |     \
                                       NO    PARTIAL    YES
                                        |       |        |
                                        |   Lift patterns 1-3   Lift all 5 patterns
                                        |   manually (Day 2)    (~3 days, MH-6/7/9 path)
                                        |   Skip halo-engine
                                        |
                                  Document; revisit only if
                                  intake-153 RLM coverage gaps
                                  emerge from autopilot data
```

```
            AppWorld pairing decision (independent track)
                                |
                  Current eval gap demands SGC benchmark?
                          /        \
                       NO            YES
                       |              |
                    DEFER          Plan 3-5d integration:
                    (current        - clone appworld.dev
                     stack: NO)     - wire Hermes/Qwen3.6/Coder
                                    - SGC scorer
                                    - dev/test_normal splits
                                    - baseline run
                                    Compare to Gemini 3 Flash 37.5%
```

---

## 8) Concrete Next Steps

### If user approves the refined spike (~1 day):

1. Create `scripts/halo/convert_tap_to_otel.py` with two entry points: `convert_autopilot_telemetry()` (~30 LoC) and `convert_inference_tap()` (~120 LoC).
2. Add 4 unit tests in `tests/halo/test_convert_tap_to_otel.py` (≥1 fixture per converter, ≥1 round-trip parse via HALO's `SpanRecord.model_validate_json`).
3. Pin `halo-engine==0.1.2` in a fresh venv at `~/.venvs/halo`.
4. Run pre-flight against bundled `tiny_traces.jsonl` to validate environment.
5. Execute Day 1 plan; document results in a new dated section of this deep-dive.
6. Issue Day 1 PM go/no-go decision against §5 success criteria.
7. If GO: open a sub-handoff `halo-pattern-lift.md` (NOT a vendor handoff) referencing intake-517 and the meta-harness MH-6/7/9 work items (already scoped).

### If user defers:

1. Keep this deep-dive as the standing reference.
2. Cross-reference from `meta-harness-optimization.md` MH-7 and MH-9 (already done in 2026-04-30 update).
3. Re-evaluate quarterly or whenever AR-3 autopilot signal indicates `capture_recent_traces` saturation.

---

## 9) Genuinely New vs Duplicate

| Pattern | Origin | Net-new for us? |
|---|---|---|
| OTel-compatible per-step span emission | intake-338 Agent Lightning | NO (telemetry.py:to_otlp_span already lives, since 2026-04-12) |
| Trace-driven prompt mutator | intake-244 Meta-Harness | NO (Tier-1 closed 2026-04-01) |
| Code-mutation search space | intake-244 Meta-Harness | NO (Tier-2 closed 2026-04-01) |
| GEPA reflective evolution | intake-240/345 | NO (PromptForge `gepa` mutation, 2026-04-12) |
| RLM symbolic recursion + REPL | intake-153 | NO (~80% coverage, R1-R6 closed 2026-03) |
| **Two-file trace store with byte-offset index** | intake-517 HALO | **YES** |
| **6-tool trace-query surface for analyzer agent** | intake-517 HALO | **YES** |
| **dev/test_normal anti-overfit split** | intake-517 HALO (AppWorld convention) | **YES** (we have one validation set, not split) |
| **Concrete failure-mode taxonomy** (4 labels) | intake-517 HALO | PARTIAL (Pocock taxonomy from intake-509 covers 4 different categories — these are complementary, not duplicate) |
| Free-text final-sentinel `<final/>` | intake-517 | NO value-add for us — we have structured eval scores |
| dev SGC + test_normal SGC reporting on AppWorld | intake-516/517/518 | Bench-only, defer |

Three concrete net-new patterns. All three lift cleanly into existing scoped work (`unified-trace-memory-service.md` T1/T5, `meta-harness-optimization.md` MH-6/7/9, `eval-tower-verification.md`). None require vendoring halo-engine.

---

## 10) Cross-References

- **Intake records**: `research/intake_index.yaml` intake-516, intake-517, intake-518, intake-153.
- **Active handoffs**:
  - `meta-harness-optimization.md` § Research Intake Update 2026-04-30 (HALO trio entry).
  - `autopilot-continuous-optimization.md` § Tier-1 traces (Phase-5 done).
  - `unified-trace-memory-service.md` (proposed, not started — direct integration target if patterns are lifted).
  - `eval-tower-verification.md` (dev/test_normal split lands here).
- **Completed handoffs**: `rlm-orchestrator-roadmap.md` (R1–R6 closed; baseline RLM coverage).
- **Codebase touchpoints**:
  - `epyc-orchestrator/scripts/autopilot/telemetry.py` (existing OTLP emitter).
  - `epyc-orchestrator/src/runtime/inference_tap.py` (canonical text trace).
  - `epyc-orchestrator/scripts/autopilot/eval_tower.py:capture_recent_traces` (current trace-feedback path).
  - Proposed: `epyc-orchestrator/scripts/halo/convert_tap_to_otel.py` (new, ~120 LoC).
  - Proposed: `epyc-orchestrator/src/trace/{store,query}.py` (already scoped in unified-trace handoff).
- **Memory file feedback to honour**:
  - `feedback_research_exhaustion_first.md` — production push is dead last; this is a research-priority intake.
  - `feedback_dont_dismiss_creative_uses.md` — confirmed three creative uses (schema, anti-overfit split, taxonomy).
  - `feedback_minimum_imports.md` — refined plan does **not** vendor halo-engine, only lifts patterns.
  - `feedback_credibility_from_source_not_readme.md` — credibility audit done from actual `engine/` source, not README.
