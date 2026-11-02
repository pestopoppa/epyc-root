# HS-19d.P0: task-delegation probe exports, 2026-11-02

Read-only descriptive inspection; no new inference. The probe named in `docs/design/hs19-stage2-dispatch-20260927.md` §3 is `/mnt/raid0/llm/tmp/task-probe-20260927/`. Its 15 run directories with parent exports contain 30 assistant messages. For each parent message, count parts with `type=tool` and `tool=task`:

- Nine HS-19a-prompt runs (01–09): each has `[1, 0]`, with one task part and one child export.
- Six DS41-prompt runs (10–15): each has `[0, 0]`, with no task part or child export.
- The conditional 16–18 directories have no parent export; they are not counted as zero-task runs.

For each of the nine task parts, `state.input.prompt` is a string. Comparing that string in memory to the only text part of the first user message in that run's one child export gave **9/9 exact matches**. This demonstrates the correspondence in these archived OpenCode exports. It does not prove that the orchestrator tap retained emitted response arguments, establish a server-side join, cover parallel or duplicated prompts, prove uniqueness in a larger population, or establish capture integrity at the time of the runs. Source content and session identifiers are not reproduced here.

The 15 parent plus nine child file bytes were read once for this inspection. A reproducible aggregate SHA-256 is `1c96810c7c6fc618c46ee5e79bc816487dcd26a632d13f5962a959f44f4f3f9a`: sorted run order, then parent followed by sorted child files; append each relative POSIX path encoded UTF-8, NUL, and the raw 32-byte SHA-256 digest of that file to the outer digest. This later identity is not a sealed run-time snapshot.

Current orchestrator source `src/api/routes/openai_compat.py:834-839` records only function names in `tool_calls_emitted` metadata; that source read is not itself proof of the historical running binary or of all tap events. The prior HS-19a tap inventory likewise found string list elements, not captured argument objects. The required actual emitted-call argument capture, child join validation and separate probe tap inspection remain open.
