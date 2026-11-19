# Stateful planning depth loop

`episode.py` provides the bounded episode loop for the model-evaluation queue's
Phase 2 depth probe. It has no server launcher. Its software
controls reuse the existing CF-3c `OrderService` and tool schemas: inspection
must precede release, and a final success assertion cannot replace the state
change. They establish software behavior, not model capability.

Call `run_episode` with a fresh isolated environment per episode, initial
messages, a model ID and seed, and these callbacks:

- `complete(request, timeout_s)` performs one native OpenAI-compatible request,
  honors the supplied remaining wall timeout, and returns the unmodified reply.
  Convert transport exceptions to `OSError` or `TimeoutError`; programming
  errors propagate rather than becoming model failures.
- `capture(record)` synchronously persists each request, raw response and tool
  result before returning. Use a unique per-episode append-only record and
  include the run's prospective protocol, case, model, source, build and serving
  custody identities in its envelope. Capture failure propagates.
- The environment supplies `tools`, `execute(calls)` and `score(text)` using the
  existing order-service interface. The supported schema is deliberately narrow:
  required string arguments with no additional properties. `score` checks actual
  environment state; it must not trust the model's textual success claim.

The loop forwards tool observations into the next request, rejects speculative
parallel calls and duplicate argument keys, and requires unique tool-call IDs.
`schema_rejections` counts rejected turns; `repairs` counts the first successful
action after each schema rejection. State-machine denials are retained as tool
events and do not count as schema failures. Neither metric is a quality verdict.

Terminal text receives the environment's deterministic score. Transport errors,
malformed native messages, empty responses, wall deadlines, token caps and turn
caps retain `UNKNOWN` and the partial transcript. Available native usage is
summed; missing or invalid usage makes total completion tokens null. This is
completion-token usage, not a separate measurement of hidden reasoning tokens.
Elapsed time includes the callbacks and capture; it is not TTFT or model-only
latency. No model comparison, uncertainty interval or adoption rule is defined.

Before measurement, pin prospective cases and success criteria, model/build and
dataset identities, endpoint custody, and paired arm order in a row packet.
Supply the owned endpoint transport and durable capture envelope, publish via
rowflow and require its native smoke. The pending belief-source task is
`VB-PLANNING-DEPTH-WIRE`; no loop-wiring claim exists yet.

`native.py` supplies the callback plumbing for a row that has already established
ownership of its endpoint. `NativeCompletion` accepts an explicit literal
loopback HTTP `/v1` URL, posts native requests without proxies or redirects, and
returns parsed replies without normalizing fields. Its absolute HTTP deadline
interrupts stalled headers and bodies by shutting down its own captured socket.
The default response bound is 8 MiB. Native response bytes (base64), status,
headers and errors are captured before parsing; malformed JSON and incomplete
HTTP remain transport failures. The episode loop recomputes its remaining
deadline after durable request capture.

Use one exclusive `DurableJournal(path, envelope)` context per episode. Supply
the prospective protocol, case, arm and source/build/serving identities in the
envelope; the helper requires a nonempty dictionary but does not verify those
identities. Pass the journal both to `NativeCompletion` and `run_episode`.
Each JSONL record carries the immutable envelope and a sequence number, and is
flushed and fsynced before returning. Capture errors propagate as fatal
`CaptureError`, preventing their conversion into model UNKNOWN results. The
caller must journal the episode's final result before leaving the context.
Existing journal paths are refused, preserving previous attempts. These helpers
do not establish endpoint ownership or replace the row's launcher/custody checks.

Software controls:

```bash
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python3 -m pytest -q -p no:cacheprovider tests/experiments/test_planning_depth.py
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python3 -m pytest -q -p no:cacheprovider tests/experiments/test_planning_depth_native.py
```
