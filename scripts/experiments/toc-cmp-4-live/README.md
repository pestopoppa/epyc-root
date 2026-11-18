# TOC-CMP-4 isolated frontdoor pilot

This packet drives the frozen option-(a) schedule through the orchestrator's real REPL graph. It starts a private loopback frontdoor on `:19359` with the registered Qwen3.6-35B-A3B MTP Q8 weights, terse template, production v10 CPU kernel, Q8 KV, and four split 65,536-token slots. The server stays private to the row through an ephemeral API key and uses its four allocated CPUs. This is an early-stratum diagnostic pilot. Live production-tenant validation remains a separate experiment on `:8070`.

Each trial runs a new graph process, REPL, and artifact directory. The adapter passes the assigned seed to the real inference primitive, checks its value on the HTTP request, and records the actual sampling fields and prompt hashes. It uses temperature 0.3 for graph calls and the graph's temperature-zero OpenClaw summary call. Cross-trial prompt caching is disabled. The receipt records the serving argv, source, frozen draw, model/build/template, region, and per-trial native artifact links. The trial directories preserve exact native events, including the paths rendered to the model.

Each generation request also writes `wire/NNNN/request.original.body`,
`request.sent.body`, `response.body` and `record.json` in its trial directory.
The record binds exact-byte digests and HTTP status. Streaming capture writes each
chunk as the backend consumes it and records whether it saw the SSE terminal
marker, transport EOF, or a partial response. A connection failure before
headers preserves the original and transmitted request bodies. Authorization
headers are excluded. Belief projection and the planning-context canary remain
the separate `VB-TOC-CMP4-LIVE-WIRE` task.

## Prepare and publish

Copy `runner.py`, `graph_trial.py`, `analysis.py`, `launcher.sh`, and `spec.json` into the scratch packet directory declared in `launcher.sh`. Prepare the detached orchestrator worktree at the scratch `source` path using the commit pinned in `runner.py`. Run `python3 -B runner.py prepare` from the scratch packet before publishing. Preparation checks the pinned orchestrator tracked tree, verifies the frozen draw and reserve order, hashes the GGUF once, and binds the v10 server, libraries, and template. The grant checks file custody and the small executable/library hashes. It never hashes the model. The smoke and grants use the allocated CPU engine. The smoke uses a one-turn REPL instruction to qualify real model delivery, graph and trajectory capture, seed forwarding, and server exit. Its early finish leaves BAPS unknown, separate from the pilot ledger.

Start the row through the project's standard publisher with the scratch `spec.json`. The launcher fails closed on a busy private port, wrong source, changed model or build, slot shape mismatch, or backend or graph failure. The elapsed-time allocation is an estimate, pending observed costs. The runner resumes from its persisted ledger under an identical receipt and honors STOP and allocator deadlines between attempts. Process teardown reaps the captured server PID on exit.

## Read the results

The registered first eight points are all early. The pilot uses three arms and four repeats at those eight points, for 96 nominal runs. The frozen reserve sequence replaces whole points when a trajectory ends before the assigned boundary. The scheduler retries transport and pin failures once with the same seed. More than 9 dropped active runs voids the cell. A run requiring an unavailable image input is invalid. An unavailable external grade stays unknown and does not change a valid BAPS measurement.

- `RECEIPT.json` identifies the frozen inputs, scope and run configuration.
- `ledger.jsonl` records raw scheduling decisions. Each window has its native server evidence and per-attempt graph, verdict and trajectory capture.
- `RUNS.jsonl` contains normalized observations for `analysis.py pilot RUNS.jsonl`. Rows for voided points remain visible and are ineligible for analysis.
- `RESULT.json` requires all 96 eligible runs and eight complete paired points. `PARTIAL.json` preserves incomplete, stopped or voided cells.
- BAPS counts blocked or error actions on numeric turns `b+1` through `b+5` for boundary turn `b`. A pure successful log re-read stays in the denominator. Mixed tool or error turns retain their observed blocked or error classification.

The pilot reports base BAPS, paired-difference dispersion, and per-run wall time. It cannot assess variance in unsampled strata or support an arm-effect claim.

CPU-grant repair (2026-11-18): the successor row id ends in `20261118-r2`,
and its scratch root has the suffix `-r2`. The job restricts itself and its
children to four distinct physical cores within the inherited grant; it
accepts either four threads or their eight-thread SMT expansion and keeps
four inference threads. Insufficient physical cores are refused. The
failed predecessors supply no behavioral evidence. See TOC-CMP-2r in the
[owning handoff](../../../handoffs/active/context-and-token-economy.md) for
preserved evidence, successor rows and qualification status.
