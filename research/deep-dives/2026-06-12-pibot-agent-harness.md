# pibot / "How to build a shitty robot" — Agent-Harness Deep-Dive (intake-688)

**Date**: 2026-06-12
**Intake**: intake-688 (blog: https://mariozechner.at/posts/2026-05-30-shitty-robot/ · repo: https://github.com/badlogic/pibot)
**Author of source**: Mario Zechner (badlogic)
**Lineage**: application of `pi-agent-core` (intake-473) — repo depends on `@earendil-works/pi-agent-core` + `@earendil-works/pi-ai` v0.78.1 (the pi-mono runtime, rescoped from `@mariozechner/*` to `@earendil-works/*`).
**Refined verdict**: `adopt_patterns` (unchanged) · **relevance: low (confirmed, not inflated)**

---

## TL;DR / Refined recommendation

**Honest answer: read-once reference. Nothing to integrate as code; one config data-point worth recording; one harness idea already covered by intake-473.**

- **LIFT (data-point only, no code):** pibot runs our *exact two production MoE models* — Gemma-4-26B-A4B Q4_K_M (default) and Qwen3.6-35B-A3B Q5_K_M — under stock llama.cpp and confirms `--chat-template-kwargs '{"enable_thinking":false}'` is needed (matches our `feedback_qwen3x_enable_thinking_false`). It also independently lands on a **128K context (`-c 131072`)** with **no `--parallel`/`-np`, no `-b/-ub`, no `-fa`, no slot tuning**, serving "up to four children" off default continuous batching on a 64 GB M1 Max (Metal, unified memory). This is a *qualitative* cross-check, not a number we can port: it's Metal not x86, and the blog publishes **zero token/sec or TTFT figures** for the LLM.
- **IGNORE (everything structural):** the agent loop is just pi-agent-core (already deep-dived at intake-473 — `research/deep-dives/pi-agent-core-stateful-ts-runtime.md`). pibot adds nothing to the primitive set we haven't already catalogued; its `harness.ts` is a thin event-subscription wrapper.
- **IGNORE (voice-specific):** the custom barge-in detector (mic-vs-playback cross-correlation, 20–420 ms delay search, 5-frame trigger) and turn-taking are voice-UX, implemented in a **compiled C++ worker** (not in the TS source), and have no analogue in our text/tool autopilot. Multi-child "concurrency" is humans self-organizing turns, not a server scheduler.
- **IGNORE (multimodal):** the on-demand photo-capture tool is a thin "client-side tool returns an image" pattern; the only mildly interesting bit is a context hook (`pruneImagesForContext(messages, maxContextImages)`) that drops old images from history. Our `multimodal-pipeline.md` already has a far more developed vision path (InsightFace/CLIP/VL, ChromaDB, 11 endpoints, 1234 tests). pibot is strictly behind us here.
- **Net:** do **not** open a handoff task. Record the model/config cross-check in intake notes and move on. The one thing genuinely worth a glance is pibot's `scripts/benchmark-llm-concurrency.mjs` *methodology* (aggregate `out_tok/s` at concurrency 1→4) as a sanity-template — but we already bench concurrency more rigorously.

---

## What it is

A hobbyist fully-local voice agent driving a EUR10 Silverlit Octobot toy. A phone web client streams mic audio to a Node/TypeScript server (port 8010); the server runs VAD → STT → an LLM tool-use agent → TTS back to the phone. Tools: web search + memory (server-side), photo capture / motor control / Spotify (client-side). Stack:

- **LLM**: Gemma-4-26B-A4B MoE Q4_K_M (default) · Qwen3.6-35B-A3B Q5_K_M (alt) · Gemma-4-12B-IT Q4 (`gemma12b`) — all via stock **llama.cpp** (`llama-server`, pinned release auto-downloaded to `~/.cache/pibot/llama.cpp`).
- **STT**: Parakeet TDT 0.6B int8 (parakeet.cpp worker) + Silero VAD — "~50× real-time on M1 Max".
- **TTS**: Qwen3-TTS 1.7B 6-bit — "~2× RT on M1 Max, ~4× on M5 Max", x-vector voice cloning.
- **Hardware**: M1 Max 64 GB (Metal, unified memory); M5 Max 128 GB also tested.

Repo structure (verified): `src/server/{index.ts, llama.ts, harness.ts, stt.ts, tts.ts, websocket-server.ts, memory-store.ts, robot-client.ts, sentence-chunker.ts, ...}`, `src/client/`, `scripts/benchmark-{llm-concurrency,stt,tts-concurrency}.mjs`, `native/` (C++/Rust workers). Depends on `@earendil-works/pi-agent-core`@0.78.1 — i.e. it **vendors the intake-473 runtime via npm**, it does not fork pi-mono in-tree.

**llama.cpp launch (verbatim from `src/server/llama.ts`):** `-m <model> --mmproj <mmproj> -ngl 999 -c 131072 --jinja` and, conditionally, `--chat-template-kwargs '{"enable_thinking":false}'`, plus `--host`/`--port`. **Absent**: `--parallel`/`-np`, `-b`/`-ub`, `--flash-attn`, threads, slot config. So "4 concurrent kids" rides default `llama-server` continuous batching with an unpartitioned 128K context.

**Agent loop (`harness.ts`):** wraps pi-agent-core's `AgentHarness` with `InMemorySessionRepo`, a dynamic `systemPrompt` callback, a `tool_call` hook (`beforeTool(toolName,input)`), a `context` hook (`pruneImagesForContext`), an event `subscribe()` stream (`message_start/update`, `tool_execution_start/end`, `message_end`), and `rebuildSession(reason)` for state reset. Barge-in cancels current speech + running tools and re-enters listening — but the cancellation/barge-in algorithm is **not in the TS source**; it lives in the compiled `parakeet.cpp` worker.

---

## Fit to EPYC (per-pattern verdict)

| Pattern | Transferable? | Why / why not |
|---|---|---|
| (a) Tool-use / agent loop structure | **No (already have it)** | It's pi-agent-core verbatim (intake-473). `harness.ts` adds only event wiring + `rebuildSession`. Nothing sharper than our REPL/`CALL(...)` tool-use contract or pi-agent-core's already-catalogued primitives (steer/followUp, terminate, before/afterToolCall, transformContext). No new primitive. |
| (b) On-demand photo-capture multimodal tool | **No (we're ahead)** | Pattern = "client tool returns an image, appended to history." Only novel detail is `pruneImagesForContext(messages, maxContextImages)` (drop stale images to cap context). Our `multimodal-pipeline.md` vision path is far richer (VL describe, faces, CLIP, ChromaDB, 11 endpoints). The image-pruning idea is a 5-line context-hook we'd already reach for. |
| (c) Custom barge-in / turn-taking under concurrency | **No (voice-specific + opaque)** | Mic-vs-playback cross-correlation (delays 20–420 ms, RMS+residual thresholds, 5-frame trigger, 800 ms silence end-of-utterance) is acoustic echo handling for a duplex voice UI. Implemented in compiled C++, not TS. "Multi-child concurrency" = kids learning to take turns, not a server scheduler. Zero overlap with our concurrent text/tool serving or QuarterScheduler/placement-SM work. |
| (d) Single-host multi-client serving as gemma4/Qwen3.6 cross-check | **Weak yes — qualitative only** | Confirms both prod models run fine under stock llama.cpp at 128K ctx serving ~4 streams on a 64 GB unified-mem box, and that `enable_thinking:false` is required (matches our memory). BUT: Metal ≠ EPYC x86 CPU/NUMA; no `-np/-b/-ub/-fa` tuning (opposite of our canonical configs); **no published t/s, TTFT, or memory breakdown** for the LLM (only STT 50×RT / TTS 2–4×RT, which are not LLM decode). Not a number we can port — just directional reassurance the models behave under concurrency. |
| Benchmark methodology (`benchmark-llm-concurrency.mjs`) | **No (we're more rigorous)** | Measures aggregate `out_tok/s` over concurrency 1→4 vs `/v1/chat/completions` (`max_tokens=768, temp=0, stream=false`), prints `conc run wall_s in_tok out_tok out_tok_s`. Ships **no baseline results**. Reasonable template, but cruder than our llama-bench + affinity-preflight + per-quarter concurrency protocol. |

---

## Decision gates & next steps

- **Gate — integrate anything?** → **No.** No code lift (TS / Metal / hardware-specific), no new technique (loop == intake-473), no number we can use (no LLM t/s; Metal not x86). Keep verdict `adopt_patterns`, relevance `low`. Do **not** create a handoff task; do **not** update `meta-harness-optimization.md` or `multimodal-pipeline.md` (nothing concrete transfers).
- **Next step** = intake-notes addendum only (below). No follow-up compute, no eval, no handoff.
- **Reopen criteria (narrow):** if pibot ever publishes actual gemma4/Qwen3.6 **decode t/s + TTFT at concurrency** on Metal, capture it as an external cross-check row for the inference compendium. The repo *has* the harness (`benchmark-llm-concurrency.mjs`) to produce those numbers but has not.

---

## Risks / why most of it does not transfer

- **Platform mismatch is fundamental.** Metal + unified memory hides exactly the bottleneck we fight (NUMA-channel BW, thread affinity, `--numa`/`taskset`). pibot's "out of the box, no flags" is the *opposite* of our canonical tuned configs — its config is a counter-example, not a recipe.
- **No LLM performance numbers.** The only quantified claims (STT 50×RT, TTS 2–4×RT) are non-LLM. "Serves four children" is a UX statement with no t/s/TTFT/memory attribution. Cannot enter the compendium as a measured data-point.
- **The interesting bit (barge-in) is compiled-out and voice-only.** Even if we wanted it, the algorithm isn't in the published TS; and we don't run a duplex audio UI.
- **Loop novelty is zero beyond intake-473** — and inflating it would double-count the same runtime we already deep-dived.
- **Honest-framing note:** per project policy we did not dismiss as `not_applicable`; but the transferable surface is genuinely a single config cross-check, not "harness patterns" plural. Earlier intake framing ("transferable harness patterns") slightly over-sells it.

---

## Cross-refs

- **intake-473** — `@earendil-works/pi-agent-core` (was `@mariozechner/*`) runtime; full primitive catalogue in `research/deep-dives/pi-agent-core-stateful-ts-runtime.md`. pibot is its deployed application, not a new source of primitives.
- `handoffs/active/multimodal-pipeline.md` — our vision/TTS/ASR pipeline; strictly ahead of pibot's image/photo path. (No update warranted.)
- `handoffs/active/meta-harness-optimization.md` — our harness-optimization loop; pibot offers nothing for the proposer/trace/mutation work. (No update warranted.)
- `handoffs/active/tool-use-eval-contract.md` — our REPL `CALL(...)` tool-use contract; more rigorous than pibot's loop for eval purposes.
- Memory: `feedback_qwen3x_enable_thinking_false` — independently corroborated by pibot's `--chat-template-kwargs '{"enable_thinking":false}'`.
- Memory: `project_worker_general_swap_2026_05_08` (gemma4-26B-A4B is our worker), routing notes for Qwen3.6-35B-A3B — pibot runs the same two GGUFs.
