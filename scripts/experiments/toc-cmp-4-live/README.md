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

The `20261118-r3` smoke first sends the rendered prompt for the first frozen
LongBench point to the private server's tokenizer. It requires the graph to
report context exhaustion on turn 1 before any generation or boundary event.
The smoke then runs the short REPL instruction to qualify generation transport.
Both attempts are instrument checks outside the pilot ledger.

Start the row through the project's standard publisher with the scratch `spec.json`. The launcher fails closed on a busy private port, wrong source, changed model or build, slot shape mismatch, or backend or graph failure. The elapsed-time allocation is an estimate, pending observed costs. The runner resumes from its persisted ledger under an identical receipt and honors STOP and allocator deadlines between attempts. Process teardown reaps the captured server PID on exit.

## Read the results

The registered first eight points are all early. The pilot uses three arms and four repeats at those eight points, for 96 nominal runs. The frozen reserve sequence replaces whole points when a trajectory ends before the assigned boundary. The scheduler retries transport and pin failures once with the same seed. More than 9 dropped active runs voids the cell. A run requiring an unavailable image input is invalid. An unavailable external grade stays unknown and does not change a valid BAPS measurement.

The graph can exhaust the 16,384-token experiment budget before generation.
When the tokenizer and native trajectory confirm this outcome on turn 1, the
runner applies the same whole-point replacement rule. Accuracy and BAPS are
UNKNOWN for the voided attempt. Zero-generation exits without this evidence
still fail validation.

A verified graph termination on the assigned boundary turn leaves BAPS UNKNOWN
with reason `terminated_on_boundary_turn` because no action entered the endpoint's
denominator. The run remains in the ledger with its accuracy grade when available,
and contributes no eligible completion. By default, the frozen reserve rule applies
only to trajectories that never reach the boundary. Incomplete generation transport
follows the registered retry and drop rules.

### Proposed terminal-on-boundary replacement

The default-off candidate requires prospective human approval under the
[policy proposal](../../../docs/design/toc-cmp-4-boundary-terminal-proposal-20261118.md).
Any one verified terminal-on-boundary result with zero BAPS actions voids its
whole point. The scheduler draws the next point in the frozen same-stratum
reserve order and schedules all its arms and repeats. The void record preserves
the observed boundary, null BAPS, grade, native artifact references and reserve
decision. In `RUNS.jsonl`, earlier arms and the triggering arm at that point
retain their grades as `observed_correct` and `grade_reason` with analytical
eligibility set to false. Failed transport continues through the retry/drop
path. Terminal behavior can depend on the assigned arm, so this post-treatment
selection restricts the estimand to retained points and cannot establish an
unbiased arm effect for the frozen pool.

After approval, use a fresh successor row, scratch directory and ledger. Apply
`terminal-boundary-scheduler.patch` to the pinned orchestrator base in a
dedicated detached scratch worktree using `git apply`. Leave the scheduler
change unstaged. The runner checks the base commit, expects a single tracked
file change and verifies the scheduler digest. Prepare that successor packet with
`python3 -B runner.py prepare --replace-boundary-terminal` and add
`--replace-boundary-terminal` to its launcher’s `runner.py run` invocation.
The flag must match the prepared input manifest, and the receipt binds the
opted-in policy, base commit and candidate scheduler digest across windows.

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
