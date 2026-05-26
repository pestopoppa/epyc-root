# How a request flows through the stack

A user types a question into a chat box. Twelve seconds later they get back a short, correct answer. What happened in between?

This is the cross-repo tour. Every paragraph here links to the chapter or topic article that explains the underlying machinery — read it as the connective tissue, not the reference.

## The system, in one breath

The orchestrator runs nine `llama-server` instances on a single AMD EPYC 9655 (96 cores, 1.13 TB DDR5). Each instance hosts one model, sized somewhere between 1.5 B and 480 B parameters. A FastAPI front-end accepts requests, decides *which* model to send each one to, runs it, decides whether the result is good enough, and — if not — escalates to a bigger model.

That's the whole shape. The interesting parts are *how* each of those decisions gets made.

## A request lands

Requests arrive at `localhost:8000`. The FastAPI handler in `src/api/` turns them into a `Task` object — a typed pydantic record with the prompt, the conversation history, any uploaded files, and a `task_type` hint that the client is allowed to suggest but the router is free to ignore.

The system's default assumption is that the client doesn't know the right model for its question. So routing is the orchestrator's job, not the caller's.

## The router decides

The router is the heart of the system, and it has gotten progressively smarter over the last six months:

1. **Hard rules first.** Some task types route deterministically. Vision tasks go to a multimodal model. Code-completion goes to a coder. Long-context ingestion (>32 K tokens) goes to the SSM-hybrid `Qwen3-Next-80B` regardless of what the rules would have picked, because that's the only model in the stack that can handle the length without re-tokenizing.

2. **Then the learned classifier.** A small MLP, trained on 2,700+ episodic memories of past task→outcome pairs, scores the task against every available model. It outputs a posterior P(success | route) per candidate. **98.7 % validation accuracy** on a held-out set as of 2026-05-21, wired into the routing pipeline a few days later. See [Routing Intelligence](../topics/routing-intelligence.md) and [MemRL System](../subsystems/orchestrator/07-memrl-system.md) for how the classifier is trained and how its confidence is calibrated.

3. **Then the cost-aware overlay.** Each model's expected throughput is multiplied through the success probability to get a cost-adjusted score. A 480 B architect that scores P=0.95 at 3.8 t/s is usually worse than a 26 B worker at P=0.82 and 60 t/s. The router picks the highest cost-adjusted score, not the highest accuracy. See [Cost-Aware Routing](../topics/cost-aware-routing.md).

4. **Confidence threshold.** If no candidate clears a confidence floor, the router *abstains* and routes to a configured fallback. This is a recent addition — it stops the router from confidently making bad calls on out-of-distribution tasks.

The full state machine is documented in [Escalation & Routing](../subsystems/orchestrator/10-escalation-and-routing.md).

## A model serves it

The request hits a `llama-server` instance — let's say it's `worker_general` on port 8072, running `gemma-4-26B-A4B` Q4_K_M.

The model was chosen for this role on 2026-05-08 after we benchmarked it against the previous incumbent (a Qwen2.5-7B). The new model is 4× larger but runs *faster* — 60.7 t/s vs 39 t/s — because it ships with **multi-token prediction** (MTP) heads and we're running it via [ik_llama.cpp](https://github.com/ikawrakow/ik_llama.cpp) which implements MTP-aware decode. The full investigation is in [MoE Optimization](../topics/moe-optimization.md); the deploy gotcha (`KMP_BLOCKTIME=10` because AOCC libomp ignores the standard idle API) is in [Inference Serving](../topics/inference-serving.md).

The server is pinned to a single NUMA quarter (24 cores, ~115 GB/s of the 460 GB/s aggregate bandwidth). Why a quarter and not the whole chip? Because **CPU LLM decode is bandwidth-bound, not compute-bound** on this hardware. Pinning to a quarter and running four instances in parallel gets ~3× aggregate throughput vs running one instance on all 96 cores. See [Hardware Optimization](../topics/hardware-optimization.md) for the NUMA story — including the L3-as-NUMA experiment we tried and reverted because it crashed throughput by 30–50 % on every production model.

## The answer comes back

Tokens stream out of the model and back to the user through the API. Latency to first token is usually under 200 ms; the throughput thereafter depends on the model.

But the orchestrator isn't done. While the user is reading the first words, the system is doing two more things in the background:

1. **Recording the episode.** The task, the chosen route, the latency, the token count, and (if available) a quality signal are appended to the episodic memory store. This feeds back into the next round of classifier training. The store is a FAISS index — a 35× speedup over the linear scan we started with. See [MemRL System](../subsystems/orchestrator/07-memrl-system.md).

2. **Watching for the failure signal.** If the answer trips a heuristic — empty output, a `<think>` loop that never closes, a tool call that the verifier rejects — the orchestrator marks the episode `failed` and triggers **escalation**.

## When the small model gives up

Escalation is the system's safety net. It used to be a four-level chain (worker → coder → coder-escalation → architect → architect-coding), but we consolidated it on 2026-05-06 after measurement showed that:

- The Qwen3.6-35B-A3B Q8 model (now serving as both frontdoor and coder-escalation) was beating the old 480 B architect-coding on every coding benchmark we ran.
- Keeping two architects in HOT memory cost 139 GB of RAM we could use for KV cache instead.

So the chain is now three roles: `worker_general` → `coder_escalation` → `architect_general` (terminal). The third level is where it stops; if the architect can't solve it, the system returns the failure to the user rather than burning more compute.

There's a subtle wrinkle worth noting. Qwen3.6 has a `enable_thinking` flag in its chat template that defaults to *on*. We had to explicitly disable it via `chat_template_kwargs.enable_thinking=false` because the model was getting stuck in degenerate `<think>...</think>` loops on mixed-domain prompts. Disabling thinking improved routing accuracy from 47 % to 80 %. The full incident is in [Chat Templates](../topics/chat-templates.md) — it's a good example of "production model, default off looks wrong, but the default actually breaks the model in our deployment."

## What's worth pausing on

Three things in this flow are worth reading the linked chapters for:

- **The router's confidence-abstain mechanism**. Most routing systems try to make the most-likely-correct call; this one explicitly refuses when it's not sure, and falls back to a known-safe model. The cost is occasional under-routing; the benefit is no high-confidence wrong answers on out-of-distribution input. [Routing Intelligence](../topics/routing-intelligence.md).

- **The MTP + NUMA-pinning combination on `worker_general`**. The 4× speedup on a single model swap came from two independent levers — model architecture (MTP-capable) and runtime (NUMA-aware quartering). Either one alone would have been incremental. Together they doubled the worker's headroom. [MoE Optimization](../topics/moe-optimization.md), [Inference Serving](../topics/inference-serving.md).

- **The decision to consolidate two architects into one**. We deleted a chunk of working code because measurement said it wasn't pulling its weight. That's the project's most-repeated pattern: build the obvious thing, measure, throw it away if smaller wins. [Stack Architecture](../subsystems/orchestrator/02-orchestration-architecture.md).

## What's next on this thread

If you want to follow the routing-decision side, the next read is [MemRL System](../subsystems/orchestrator/07-memrl-system.md). If you want the model-engineering side, [MoE Optimization](../topics/moe-optimization.md) is the deeper version of the worker_general story. If you want the hardware side, [Hardware Optimization](../topics/hardware-optimization.md) is where the NUMA work lives.
