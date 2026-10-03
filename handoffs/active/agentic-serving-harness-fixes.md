# Agentic serving harness fixes — demonstrate on the 27B, generalize, then audit

**Status**: active. Phase A is in flight: the F12 run on DFlash2 started 2026-10-03.
**Created**: 2026-10-03, by operator directive in session ak-ds41-main:

> "yes, i want all the harness bugs we identified to be fixed. The fixes shoudl be as general as possible (not limited solely to the 27B model) as I'm sure they would affect the usage of any of the models in the orchestrator stack. A full review/audit of how fixes should holistically be folded into the orchestrator's mgmt shoudl be performed after they are demonstrated on the 27B model."

**Categories**: agent_architecture, inference_serving, context_management, tool_implementation
**Parent index**: [`user-facing-harness-index.md`](user-facing-harness-index.md), row UFH-14.
**Owners**:
- Phase A and the client-side harness pieces: ak-ds41-main.
- Phase B orchestrator and stack pieces: workspace-ec, the stack owner (formerly workspace-8d).
- Phase C: the operator's choice of auditor (Fable, per the auditor convention).

**Related**:
- [`harness-selection-and-integration.md`](harness-selection-and-integration.md) (UFH-01, HS-4: harness features live inside the orchestrator).
- [`harness-improvement-loop.md`](harness-improvement-loop.md) (UFH-08).
- [`deepseek-v41-flash-evaluation.md`](deepseek-v41-flash-evaluation.md) (INF-77, where the defects were found: DS41-C95).

## Evidence (the defects this handoff fixes)

1. **The 27B harness experiment (DS41-C95)** was graded blind by claude-opus-5-5. P(keep): DeepSeek as-ran 0.75, 27B×codex 0.50, 27B×Hermes 0.33, 27B×opencode 0.25, 27B as-ran 0. Orchestrator arms orv and orsv went 0/4.
   - **Diagnosis:** `/mnt/raid0/llm/tmp/ds41-c95/diagnosis-27b-report.md`. Most 27B failures were harness and serving defects, not model capability. In 6 of 8 no-reply calls, a keep-class candidate already sat in the transcript.
2. **The prefill/decode share analysis** covers 09-24→10-01 and was parsed from llama-server logs: [`docs/reviews/prefill-share-20261003.md`](../../docs/reviews/prefill-share-20261003.md).
   - On :8083, 74% of prefill time was cold ≥8k prefills where no slot held the prefix.
   - 21k s was duplicate concurrent prefill of the same context.
   - There were 929 prompt-cache evictions and 456 "failed to find a memory slot" warnings.
   - Neighbour prefill dropped decode from 28.6 to 7.8 tok/s, costing about 60k s.
3. **Decode-vs-context probe** (solo, production shape): `/mnt/raid0/llm/tmp/ds41-c95/probe-decode-vs-context.md`. On MTP, prefill fell from 850 to 487 tok/s between 2k and 80k, and time to first token at 80k is 165 s.

| # | Defect | Layer | Generic? |
|---|---|---|---|
| D1 | Client stream idle timeout (codex ~300 s) shorter than a long silent prefill. The abandoned request keeps prefilling, which doubles the load. | client harness | yes: any model with long prompts |
| D2 | Compaction requests change the prompt prefix (codex sends `tools=[]`), forcing a full cold re-prefill of 79–94k tokens. | client harness | yes |
| D3 | Compaction drops the task prompt (opencode). | client harness | yes |
| D4 | No answer protocol: the model explores past its budget with a candidate in hand, and the final answer is never emitted. | harness prompt and loop | yes |
| D5 | Parallel arms start at the same moment on the same context, so each prefills cold. No prefix warming. | harness scheduling | yes |
| D6 | The `--kv-unified` pool (`-c 196608` shared by 4 slots) overflows under concurrent long contexts, causing evictions and context-exceeded errors. | server config | yes: per-model sizing |
| D7 | Concurrent long prefills stall decode in the other slots. | server admission | yes |
| D8 | Serving telemetry gaps: no wall-clock time, no record of which role or client sent each request, `prompt_eval_ms`=0, cancels untimed, queue wait unlogged. | orchestrator and stack logging | yes |

## Phase A — demonstrate on the 27B (production Qwen3.8-27B Q8_0, DFlash2, :8083)

- [ ] **UFH14-A1.** F12 run: the cxf1 arm (F1: solo, 1 h idle timeout, compaction at 150k) and the cxf12 arm (F1 plus F2: JSON-first answer, forced answer at 65% of budget, refine turn, 8k thinking cap). 8 solo calls on C2 and C4, graded blind against all C95 arms. Covers D1 and D4, partly D2.
  - Launcher: `/mnt/raid0/llm/tmp/ds41-c95/f12_launch2.sh`. Log: `logs/f12_launch2.log`.
- [ ] **UFH14-A2.** DFlash2 decode-vs-context probe on the production shape, to compare against the MTP probe and to separate drafter speed from harness effects.
- [ ] **UFH14-A3.** Prefix warming plus staggered starts for parallel arms. Issue one warm request for the shared context, then start the arms so they hit the prompt cache. Measure the cold-prefill share and decode stall against an unstaggered A/B. Covers D5.
- [ ] **UFH14-A4.** Compaction that keeps the prefix. Make compaction requests carry the same tools and system prefix, or compact through a separate summarization call that leaves the live prefix intact. Measure re-prefill tokens per compaction. Covers D2. Also cover opencode's task-prompt drop (D3).
- [ ] **UFH14-A5.** Phase A verdict: which fixes measurably change P(keep), wall time and prefill seconds on the 27B. Wire the results to the belief kernel; VB-DS41-C95 already exists, so extend it rather than adding a new ladder.

## Phase B — generalize, model-agnostic

Client and harness side (ak-ds41-main):

- [ ] **UFH14-B1.** Move the demonstrated client fixes (D1–D5) out of the C95 experiment drivers (`/mnt/raid0/llm/tmp/ds41-c95/run2.py`, `proxy2.py`) into shared, model-independent harness settings. Targets:
  - the AutoKernel actor launch (`epyc-inference-research` actors.py);
  - the opencode and codex provider configs used with local models;
  - the orchestrator's own agent-loop compaction (HS-4).

  Each parameter is derived from the serving server's measured prefill rate and slot context, never hardcoded for one model.

Orchestrator and stack side (workspace-ec; items are linked here as they land):

- [ ] **UFH14-B2.** Token-aware pool gate, keyed per server: one long prefill at a time, with all orchestrator traffic, scouts included, going through it. Covers D7. Operator-approved 2026-10-03; deployed as an API-only change.
- [ ] **UFH14-B3.** KV-pool sizing as a per-model stack rule: slots × expected context, plus a per-request cap. The :8083 instance is a relaunch with `-c 393216` unified and a 262144 per-request cap (stack change, operator signature). Covers D6.
- [ ] **UFH14-B4.** Prefix-cache and `--cache-ram` policy per server. Covers D5 and D6 on the server side.
- [ ] **UFH14-B5.** Serving telemetry: a launch banner with ISO-UTC, pid, role and argv; per-call role, request_id and llama `timings`; `prompt_eval_ms` filled in; cancel summaries; queue wait. Plus the belief-kernel write-side adapter, owned by workspace-ec. Covers D8.
- [ ] **UFH14-B6.** An OpenAI-compatible passthrough on :8000 for a named role (chat/completions and responses, streaming, tools, timings echoed), so harness experiments can go through the gate instead of hitting servers directly. The gap list is pending from workspace-ec.

## Phase C — holistic audit (starts only after A5)

- [ ] **UFH14-C1.** A full review of how the A and B fixes fold into orchestrator management across every model in the stack: CPU and GPU roles, frontdoor, architect, workers and embedders. Covers routing, admission, compaction, caching, telemetry and per-model parameters.
  - Output: a decision package for the operator (options, tradeoffs, recommendation), plus follow-up tasks filed in their owning handoffs.
  - Delete-lens included: name the fixes that should NOT become generic.

## Notes

- The C95 harness calls :8083 directly through its own proxy, because it needs raw streams with per-request timings on the wire. It runs at concurrency 1, so it cannot exhaust the pool. Once B6 exists, later harness experiments should go through the gate.
- Since 2026-09-30 DS41's planner and critic are external models (gpt-6.1-sol, claude-opus-5-5). Whether the 27B returns to the planner seat is an operator decision after A5. It competes for :8083 with the INF-80 X0 window (`/mnt/raid0/llm/tmp/x0-27b-quants/PLAN.md`).
