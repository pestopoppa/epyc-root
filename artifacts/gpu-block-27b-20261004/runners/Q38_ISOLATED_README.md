# Q38-T7 isolated-arm coordinator

`q38_t7_isolated.py` and `q38_t7_runtime.py` are the prospective successor's
coordinator and runtime contract. They retain the original source in `q38_t7.py`
unchanged. The coordinator runs the drafted and no-draft arms sequentially,
requires verified cleanup between them, seals identical pair bodies, rejects
request-level speculative overrides, and sends each arm its own warm request.
For a cached measurement it requires a native cache count at least as large as
the predeclared threshold. The warm and measured messages must share the declared
prefix. Every response and request-body hash is returned, including on partial
failure; no Q38 quality or speed verdict is inferred here.

`test_q38_t7_isolated_http.py` starts two **fake** HTTP server subprocesses in
sequence, routes real local HTTP calls, and verifies independent warmups,
matching body hashes, correct arm modes, refusal on mismatched mode or cache
evidence, and cleanup of its captured children. This exercises coordination,
not production serving or inference.

`q38_t7_supervisor.py` owns a captured subprocess using its PID, birth time and
pidfd. It builds separate recipes, checks pinned binary/model/draft digests,
rejects draft options and inherited llama/draft variables in the common recipe,
signals only its captured child, and requires a caller-supplied descendant-drain
verifier before reporting cleanup. The fake-HTTP test exercises this owner;
unverified cleanup remains sticky.

There is deliberately no production CLI, native-verifier implementation,
production transport or durable journal. Before target use, implement and qualify those
against the host's child/descendant ownership, process and socket identity,
recipe/binary/model/library binding, STOP and drain, durable no-redraw exposure,
native cache receipts and rowflow contracts. `Runtime`'s injected verifiers
and journal must prove these facts; a URL, mode string, fake-process test or
boolean supplied without such a proof is not qualification. Phase C, native
scoring and the remaining runners are outside this slice. KVU-16h-runner stays
open, and the guarded entry point remains the only supported historical-Q38
entry until the full successor is qualified.
