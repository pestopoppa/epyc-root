# Codemode intake (2026-11-17): Ronacher "What is Codemode" and its evidence base

Run: intake-2675 .. intake-2693, all `dive-verified` with script-marked claim anchors (2026-11-17; 76 anchors; second reader found most PARTIAL because claims are composite; 3 mis-assigned anchors were corrected). `read_depth` FULL except Gondolin PARTIAL. Lane head 2d8b942e (root), orchestrator read at 12afe28. Raw sources: `/mnt/raid0/llm/tmp/dive-codemode/`.

## Entries

| ID | Source | One-line finding |
|---|---|---|
| 2675 | lucumr.pocoo.org 2026/10/6 codemode | Pattern description; contains no measured result. Concurrency sentence overturned by source (below). |
| 2676 | lucumr 2025/7/3 tools | Predecessor; assertions only. |
| 2677 | lucumr 2025/8/18 code-mcps | One n=1 anecdote; author says Playwrightess does not beat Playwright MCP. |
| 2678 | Cloudflare Code Mode | Mechanism only; no results text. |
| 2679 | Anthropic code execution with MCP | 98.7% figure is a worked example, not a measurement. |
| 2680 | Pi codemode source @ cead615b | Verified implementation; see locators. |
| 2681 | Gondolin | Execution-side microVM + egress/secret control. PARTIAL read. |
| 2682 | arXiv 2603.06713 ATLAS | Code orchestration gain on a 4B does not replicate on own second test set; RFT is what helps. |
| 2683 | arXiv 2607.10569 | Frontier-only; pass rates tied, cost depends on agent and regime. |
| 2684 | arXiv 2602.15945 | 16 attack classes; exception injection succeeds without sandbox escape; no numbers in paper. |
| 2685 | arXiv 2402.01030 CodeAct | +20.7 points is one strong model; open 2023 models at floor; JSON is the weak format. |
| 2686 | Pydantic code-mode benchmark | Best-designed measurement; long tasks -58% cost, small tasks pay a tax; no local small model. |
| 2687 | AIMultiple benchmark | Saving is tool-schema tokens; saturated success; superseded by 2686. |

## Pi source verification (`earendil-works/pi` @ cead615b48b80d1c61eecab2f0b576d16eeaf4c5, packages/ prefix)

- Sandbox: quickjs-wasi (`codemode/src/runtime/vm.ts:38,172,176`); 256 MiB cap `coding-agent/src/extensions/codemode/execute.ts:56,593`; no host globals asserted in `codemode/test/sandbox.test.ts:697-712`.
- Blog sentence "limits concurrent tool executions to four": NOT-FOUND-IN-SOURCE. The 4 is `MAX_CONCURRENT_MODEL_CALLS` (`execute.ts:50,750`) for classify/generateImages; separate 2-worker cap (`execute.ts:58`) with 60 s admission wait (`execute.ts:69`).
- `store()`: bounded JSON KV (`codemode/src/runtime/prelude-source.ts:15,34-35,276-290`), persisted as `codemode-store` session entries only on success (`execute.ts:617-621`), replayed branch-aware (`execute.ts:292-302`). Not injected into model context.
- Discovery: BM25 `searchTools`, `describeTool`, `describeNamespace`; inline declaration budget 3000 tokens (`docs/codemode.md:31-34`, `execute.ts:683`).
- Result contract: output to the model capped at 10000 tokens head+tail, spill to temp file (`execute.ts:306`); bash returns structured `{output, truncated, full_output_path, exit_code}` capped 1 MiB (`bash.ts:23`).
- The sandbox jails the script only; tools run with full host power.

## Cross-source reading for the orchestrator

1. Value is concentrated where item count is large (Pydantic crossover 20-50 items; savings are output and input tokens, not round trips).
2. No source measures a 7B-35B quantized worker. ATLAS and CodeAct suggest cold weak models gain nothing from the code format; Pydantic shows weak API models gain on long tasks but lose on short ones. A local paired probe is the deciding evidence.
3. Security: sandboxing is insufficient (2684); tool exceptions and outputs are injection channels; regeneration loops are an availability attack.
4. Progressive discovery likely explains most of the measured input-token savings (2687) and is separable from code execution.

## Wave 2 and 3 additions (intake-2688 .. 2693)

| ID | Source | One-line finding |
|---|---|---|
| 2688 | Ronacher 2026/7/4 Better Models: Worse Tools | About nested JSON tool schemas on Anthropic models, not about local or code-writing models; strict mode fixed it in his runs. |
| 2689 | Pydantic Code mode is not a sandbox (slug code-mode-vs-sandboxes) | Code mode and isolation are orthogonal; tools keep full agent authority; Monty limits are 30 s / 256 MiB / 100 tool calls and are opt-in. |
| 2690 | Colvin The code is the graph | Opinion and design; idempotency caveat for replay. |
| 2691 | maverick-jackson/code-puppy-speculation-ab | Independent frozen-plan A/B: code mode +33% wall time and +44% cost on 10-90 s tasks, same success; models do not batch (61% single-call snippets). Contradicts the vendor headline on short tasks. |
| 2692 | arXiv 2605.13360 SIA | Speculation on partial user speech; not a decode-loop result; no 7B-35B model. |
| 2693 | arXiv 2406.00059 Conveyor | Tool partial execution during decode: 26.3% on a code-generation case with Mistral-7B; nothing when tools are fast. |

Re-encounters recorded here instead of new entries (existing entries, not edited in this run): Prime Agent intake-1010 (dive-verified), AsyncFC intake-1119 (dive-overturned, monitor), spec-ptc blog intake-1312 (stage1-unverified, awaiting dive; the wave-2 read of the Zhang post found its own speedup is about 1-1.2x on Qwen3-30B-A3B and needs no engine support), Monty intake-1864 and the Monty sandbox-escape write-up intake-1870 (language-level escape in v0.0.16; the wave-3 read found no published escape suite in the repo docs, which intake-1870 qualifies), Pi harness intake-1360.

Prior in-house work found at the pinned lane head: `handoffs/active/memory-program.md` `## Track: repl-session-memory-maturity` already owns D-RI-CONTAIN (killable resource-limited CPython lane) and D-RI-MONTY-SLICE (restricted Monty adapter on twelve REPL cases).

## Dive-surfaced sources declined (recorded, wave cap not reached)

Fetched and ingested in waves 2-3: the Pydantic sandbox post, Colvin, Maverick, Ronacher 2026/7/4, SIA, Conveyor; Prime Agent, AsyncFC, spec-ptc and Monty were already indexed. Declined (surfaced by name only, no bearing on a decision): MCPBench, MAESTRO, CodeMem, MINT, TaskWeaver, InferCept, ToolLLM-style serving papers, Cursor agent-sandboxing post, Pydantic AI Code Mode docs, Monty docs pages not cloned (the Monty repo docs were read). Wave 4 not run: wave 3 surfaced nothing new that bears on a decision.

## Artifact audit

clean (dive scratch lives under /mnt/raid0/llm/tmp/dive-codemode/, outside the repo).
