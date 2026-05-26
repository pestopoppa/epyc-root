# How a request flows through the stack

A user types a question into a chat box. Twelve seconds later they get back a short, correct answer. What happened in between?

This is the cross-repo tour. Every paragraph links to the chapter or topic article that explains the underlying machinery — read it as connective tissue, not the reference.

## The system, in one breath

The orchestrator runs nine `llama-server` instances on a single AMD EPYC 9655 (96 cores, 1.13 TB DDR5). Each instance hosts one model, sized somewhere between 1.5 B and 480 B parameters. A FastAPI front-end accepts requests, decides which model to send each one to, runs it, decides whether the result is good enough, and — if not — escalates to a bigger model.

That's the whole shape. The interesting parts are *how* each of those decisions gets made.

## A request lands

Requests arrive at `localhost:8000`. The FastAPI handler in `src/api/` turns them into a `Task` object — a typed pydantic record with the prompt, the conversation history, any uploaded files, and a `task_type` hint that the client is allowed to suggest but the router is free to ignore. The system's default assumption is that the client doesn't know the right model for its question, so routing is the orchestrator's job, not the caller's.

## The router decides

The router is the heart of the system and it has gotten progressively smarter over the past six months.

Hard rules run first. Some task types route deterministically: vision tasks go to a multimodal model, code-completion goes to a coder, and any long-context ingestion above ~32 K tokens goes to the SSM-hybrid `Qwen3-Next-80B` regardless of what the rules would have picked, because that's the only model in the stack that can handle the length without re-tokenizing.

When no hard rule applies, the learned classifier takes over. A small MLP, trained on 2,700+ episodic memories of past task-to-outcome pairs, scores the task against every available model and outputs a posterior P(success | route) per candidate. The classifier hit 98.7 % validation accuracy on a held-out set as of 2026-05-21 and was wired into the routing pipeline a few days later. [Routing Intelligence](../topics/routing-intelligence.md) and the [MemRL System](../subsystems/orchestrator/07-memrl-system.md) chapter cover how it's trained and calibrated.

The classifier's posterior gets multiplied through each model's expected throughput to produce a cost-adjusted score. A 480 B architect at P=0.95 and 3.8 t/s is usually worse than a 26 B worker at P=0.82 and 60 t/s; the router picks the highest cost-adjusted score, not the highest accuracy. See [Cost-Aware Routing](../topics/cost-aware-routing.md) for the underlying philosophy.

The final stage is a confidence threshold. If no candidate clears a confidence floor, the router explicitly *abstains* and routes to a configured fallback rather than committing to a low-confidence guess. This is a recent addition; it stops the system from confidently making bad calls on out-of-distribution inputs. The full state machine — including escalation triggers — is in [Escalation & Routing](../subsystems/orchestrator/10-escalation-and-routing.md).

## A model serves it

The request hits a `llama-server` instance — let's say `worker_general` on port 8072, running `gemma-4-26B-A4B` Q4_K_M.

The model was chosen for this role on 2026-05-08 after benchmarking against the previous incumbent (a Qwen2.5-7B). The new model is four times larger but runs faster — 60.7 t/s versus 39 t/s — because it ships with multi-token prediction (MTP) heads and we're running it via [ik_llama.cpp](https://github.com/ikawrakow/ik_llama.cpp), which implements MTP-aware decode. The full story of that swap, including the production deployment bug that briefly cut throughput by an order of magnitude, is in [Worker_general: 17 → 76 t/s](worker-general-story.md).

The server is pinned to a single NUMA quarter — 24 cores with about 115 GB/s of the chip's 460 GB/s aggregate bandwidth. The question of why a quarter and not the whole chip has one answer: CPU LLM decode is bandwidth-bound, not compute-bound, so pinning to a quarter and running four instances in parallel gets roughly 3× the aggregate throughput of one instance on all 96 cores. [Hardware Optimization](../topics/hardware-optimization.md) covers the NUMA story, including the L3-as-NUMA experiment we tried and reverted because it crashed throughput by 30-50 % on every production model.

## The answer comes back

Tokens stream out of the model and back to the user through the API. Latency to first token is usually under 200 ms; throughput thereafter depends on the model.

But the orchestrator isn't done. While the user is reading the first words, the system records the episode — the task, the chosen route, the latency, the token count, and (if available) a quality signal are appended to the FAISS-indexed episodic memory store that feeds the next round of classifier training. It also watches for a failure signal: an empty output, a `<think>` loop that never closes, a tool call the verifier rejects. If any of those fires, the orchestrator marks the episode failed and triggers escalation.

## When the small model gives up

Escalation is the safety net. It used to be a four-level chain (worker → coder → coder-escalation → architect → architect-coding), but we consolidated it on 2026-05-06 after measurement showed two things: the Qwen3.6-35B-A3B Q8 model (now serving as both frontdoor and coder-escalation) was beating the old 480 B architect-coding on every coding benchmark we ran, and keeping two architects in HOT memory was costing 139 GB of RAM we could give to KV cache instead.

The chain is now three roles: `worker_general` → `coder_escalation` → `architect_general`. The third level is terminal — if the architect can't solve it, the system returns the failure to the user rather than burning more compute.

One subtle wrinkle worth noting. Qwen3.6 has an `enable_thinking` flag in its chat template that defaults to *on*. We had to explicitly disable it via `chat_template_kwargs.enable_thinking=false` because the model was getting stuck in degenerate `<think>...</think>` loops on mixed-domain prompts. Disabling thinking improved routing accuracy from 47 % to 80 %. It's a good example of "production model, default looks right, but the default actively breaks the model in our deployment." [Chat Templates](../topics/chat-templates.md) has the full incident.

## Where to go next

For the routing-decision side of the system, [MemRL System](../subsystems/orchestrator/07-memrl-system.md) is the next read. For the model-engineering side, [MoE Optimization](../topics/moe-optimization.md) is the deeper version of the worker_general story. For the hardware side, [Hardware Optimization](../topics/hardware-optimization.md) is where the NUMA work lives.
