# CMP-3 isolated live REPL probe

The [screen protocol](../../../docs/design/toc-cmp-3-live-protocol-20261118.md) defines the question and scope.
Run `python3 -B scripts/experiments/toc-cmp-3-live/prepare.py` from the root to prepare
a detached candidate and a verified packet under `/mnt/raid0/llm/tmp/delegation-context-preassembly/cmp3-live-r3`.
Preparation reuses the CMP-4 GGUF digest and checks its file identity, runtime hashes and the original CMP-3
candidate patch. The printed packet spec is the input to the normal row publisher.

Each synthetic task requests two REPL actions before giving the answer. The first exposes a padded, exact
source record and the second leaves a small tail. The forced boundary at the start of turn 3 uses an 8,192-token
graph budget and a 20% tail. If the model takes a shortcut or the first output fits the tail, the missing
observation stays unknown. Each task shares one seed across its arms and the second reverses the first arm order.
The graph caps each trial at seven turns and the launcher caps each attempt at 1,200 seconds
within its allocator deadline and 7,380-second row cap.
The private CPU server uses the CMP-4 model, template and runtime on port 19368. The publisher smoke qualifies
one contract-on summary trajectory with a real generated summary and continuation.

The first generated action after compaction is turn 3. Its request bytes, response bytes, wire metadata and
native turn must agree. The exact framed contract is evaluated in that HTTP request. For manifest rows, the
probe validates each declared UTF-8 digest against the exact character span in the native log. Native prompt
token counts include the brief where present. The row reports literal custody, exact-match answer grades,
and the elapsed time of each arm. The two tasks give each arm two observations. The source record stays
available in REPL context throughout the task, so answer grades also reflect direct re-reads of the source.

The successor row id ends in `20261118-r3`. The job restricts itself and its
children to four distinct physical cores within the inherited grant; it
accepts either four threads or their eight-thread SMT expansion and keeps
four inference threads. On r2 the summary's 120-second HTTP timeout expired
after 94 seconds of prefill while the server was still decoding near 4.9
tokens per second. R3 allows 360 seconds per generation or summary request
and 390 seconds for the lock watchdog in the isolated graph process. The
smoke still requires a complete summary, observed continuation, and listener
exit within 1,260 seconds. See TOC-CMP-2r in the
[owning handoff](../../../handoffs/active/context-and-token-economy.md) for
preserved evidence, successor rows and qualification status.
