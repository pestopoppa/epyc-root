# STACKCHANGE item: per-role request timeouts cannot cover a full-context prefill (UFH14-B1 F1 / D1)

> Durable copy (2026-10-04, workspace-ec wrap-up) of `/mnt/raid0/llm/tmp/ufh14-b1-20261003/orch/STACKCHANGE-ITEM.md`. Tracked as UFH14-B1d in [`handoffs/active/agentic-serving-harness-fixes.md`](../../handoffs/active/agentic-serving-harness-fixes.md). Review correction: with any deadline the dispatch clamp returns the remaining budget, so F1 can only record `doomed` under a deadline; `doomed` is judged against one prefill of the uncached tokens since orch 1d03d9b4.

Kept separate from `f1f2-proposal.diff`, which changes no registry field and no launch flag.
Base: orchestrator origin/main `0f0bfa19`; research master `orchestration/model_registry.yaml` @ origin/main `4a815f00`.

## The fields

The fields are `runtime_defaults.timeouts.roles.*` and `timeouts.server.request`.
- Defined in: the research master `orchestration/model_registry.yaml:565-605`.
- Compiled into: the orchestrator lean `orchestration/model_registry.yaml:74-90`.
- Read by: `TimeoutsConfig` (`src/config/models.py:1181-1215`, `src/config/__init__.py:460-572`).

They are used twice:
1. As the per-call `request.timeout` (`src/llm_primitives/inference.py:979-982`). This is the httpx read timeout, so it fires
   while the server is still in its silent prefill.
2. As the interactive request deadline: `resolve_timeout` returns min(role SLA, timeout_s)
   (`src/api/routes/chat_pipeline/routing_decision.py:678-711`). Every call is clamped to that deadline at dispatch
   (`inference.py:1283`, `primitives.py:609-645`). Only `eval_batch` / `task_root` requests can extend it.

The diff adds a derived prefill allowance to (1). Under (2) it can only RECORD `serving_params.doomed`, because the deadline
still wins.

## Why each value fails D1

The rough worst case is `per-request ctx / prefill rate`. The per-request context comes from `ContextLimitResolver`. Rates:

| Role (server) | Current | Per-request ctx | Prefill rate | One full-window prefill | Largest prompt the value covers |
|---|---|---|---|---|---|
| coder_escalation (:8083 27B) | 120 s | 262,144 | 257–325 tok/s ¹ | ~800–1,020 s | ~31k tokens |
| ingest_long_context (:8083) | 300 s | 262,144 | 257–325 | ~800–1,020 s | ~77k tokens |
| architect_critic (:8083) | 600 s | 262,144 | 257–325 | ~800–1,020 s | ~154k tokens |
| architect_general (:8074 Flash-Next CPU) | 600 s | 262,144 | unmeasured ² | 262,144 / rate | 600 x rate |
| frontdoor (:8070/:8080/:8180) | 180 s | 65,536 (role minimum: :8070 runs -np 4 split) | unmeasured ² | 65,536 / rate | 180 x rate |
| worker_* (same fleet) | 60 / 120 s | 65,536 | unmeasured ² | 65,536 / rate | 60 x rate |
| worker_vision / vision_escalation (:8086) | 60 s | 65,536 | 1,356.95 tok/s ³ | ~48 s | ~81k (with 2x queue: ~97 s, more than 60) |
| server.request (fallback) | 600 s | n/a | n/a | n/a | n/a |

Notes:
1. Measured :8083 long-prefill rates cited at `src/scheduling/kv_pool_admission.py:165-166` (all-traffic 32–64k: 257; ≥64k:
   325). F12 measured ~340 at 157k cold and solo, which still gives ~771 s at 262k.
2. The serving-call log (`logs/serving_calls/serving_calls.jsonl`, 20 KB at 15:41Z) holds no record with ≥8192 uncached
   tokens yet. `serving_params.for_url(<url>).to_dict()` gives the measured number once 3 exist.
3. The registry median image+text prefill (research registry, the worker_vision comment).

Two of these are contradictions on their own terms:
- **ingest_long_context** is the overflow-reroute target for long documents (`context_limits.py:723-735`), yet its 300 s
  deadline is doomed for any prompt above ~77k tokens on its own server.
- The registry comment on **coder_escalation** already says "262144-ctx prefill is now the timeout driver… 120 s may be too
  tight".

## Proposed rule (derived, no hand-picked values)

**Option A (recommended): the role value becomes the DECODE/interaction SLA (same numbers), and the deadline = SLA + derived
prefill allowance for THIS prompt.**
- The allowance is `serving_params.prefill_allowance(urls, prompt_tokens)`: 2 x prompt / measured rate x 1.25, ≥8192 tokens
  only, 0 when unmeasured.
- Code: `resolve_timeout` gains the prompt estimate and the role's URLs. The diff's per-call addition then survives the
  dispatch clamp.
- Registry: the comment on every `roles.*` entry and on `architect_general: 600 # Kept at 600 to cover full-context prefill`
  changes to "decode SLA; prefill is added from serving records". Values stay unchanged.
- Effect: short prompts are byte-identical. A long interactive call can finish its prefill instead of being abandoned while
  the server keeps prefilling (which doubles the load on the retry).
- Tradeoffs:
  - The latency upper bound grows with prompt size. A 150k-token :8083 call can take tens of minutes.
  - The callers' own HTTP timeouts toward :8000 must also exceed it. Hosted callers keep theirs.

**Option B: keep the SLA, and refuse a doomed call before dispatch.**
- The refusal is a typed `prefill_exceeds_budget`, recorded with `refusal.gate`.
- Effect: no abandoned prefill, and the caller learns immediately.
- Tradeoff: long-document ingestion through interactive traffic fails by design, unless the caller declares `timeout_s` on a
  `task_root` / `eval_batch` request.

**Option C: raise the constants** (for example ingest_long_context 300 → 1200).
- Rejected: hand-picked for one server, and wrong again after the next relaunch or `-c` change. F1 forbids it.

**Recommendation.** Apply the code diff first; it is API-only and log-only for interactive traffic. Then take one window of
`serving_params.doomed` counts per role from the serving records, and sign Option A with those counts as its evidence. Use
Option B only for roles whose purpose excludes long context, if the operator wants a hard latency bound.

## Not stack-owned (handled in the diff)

- The passthrough read timeout (`ORCHESTRATOR_PASSTHROUGH_READ_TIMEOUT_S`, default 1800). The code raises it per call; the
  env var still pins it.
- `ChatRequest.timeout_s` `le=3600` (`src/api/models/requests.py:212-224`). This is a shape ceiling. Revisit it only if a
  measured `task_root` prefill plus work exceeds it.
