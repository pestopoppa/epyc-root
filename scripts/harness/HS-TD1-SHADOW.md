# HS-TD-1 observed-policy shadow consumer

`hs_td1_shadow.py` consumes finite, prepared JSONL observations and emits one
logging-only classification and native `decision_receipt.v1` per turn. It imports
the existing orchestrator prepared-action API; it implements no receipt or
grading ladder. Model output has exactly risk (`low`, `medium`, `high`), intent
(`read`, `edit`, `execute`, `external`) and confidence (finite number 0..1).
The receipt offers the twelve risk/intent combinations and validates the frozen
observation, catalog and expiry. No action is executed or authorized.

Input contract, shown as a **synthetic structural example**, not native evidence:

```json
{"schema_version":"hs_td1.dispatch_observation.v1","phase":"pre_dispatch","session_id":"session-1","turn_id":"request-1","captured_at":"2026-11-19T10:00:00Z","request":"Read README","context":"Local repository","harness_decision":{"kind":"observed","decision":"permissive","session_id":"session-1","turn_id":"request-1","native_event_id":"policy-event-1"}}
```

A future native producer must capture request/context before dispatch and join
the **actual** harness decision by session and turn identity. Its original event
record and code identity must be retained with the prepared input manifest.
This consumer validates schema and join identities; metadata alone cannot prove
that an event was observed. Authored references, missing/unknown decisions,
missing native event IDs and mismatched turns do not enter inference. There is
no native producer installed by this change and no live-session acceptance claim.
Do not adapt the authored feasibility corpus by relabeling it `observed`.

Only request/context enter model input. The policy answer and event IDs are
retained in the frozen observation beside the judgment, never in the prompt.
The diagnostic comparison maps high risk or external intent to restrictive,
all other combinations to permissive. Agreement is with this declared mapping,
not proof of correct permissions. Confidence is uncalibrated self-report.
Raw worker responses survive schema failures; failures, expiry and changed
inputs remain unknown. The CLI rejects duplicate turns, flushes/fsyncs each
record, creates outputs exclusively with mode 0600, and bounds input lines and
worker response bytes. Reuse requires a fresh output path. Inputs and outputs
contain private user text and must live in private scratch storage.

Execution requires a qualified keeper row (`FILLER_ID`); no live endpoint or
inference is started by the plugin or these tests:

```bash
python3 scripts/harness/hs_td1_shadow.py --help
python3 -m pytest -q tests/harness/test_hs_td1_shadow.py tests/test_hs_td1_probe.py
```

Before publishing, freeze/validate the complete input once, retain its digest,
planned turn count, native producer/event provenance and worker model/build/
library identity. The CLI honors STOP/deadline between calls and bounds each
request to 90 seconds; a keeper must enforce its grant deadline. Preserve partial
attempts. `summarize(records, expected)` uses the predeclared count; missing and
invalid turns stay unknown, confidence is reported by turn including disagreements,
and all-attempt elapsed time includes failures. Higher agreement is descriptive;
lower added call time is cheaper. Summary generation is explicit and offline;
the CLI writes per-turn records only. No input window coverage is inferred from
the records that happen to arrive. This is replay of pre-dispatch inputs: it
does not measure live dispatch latency or satisfy the real-session window gate.

## Opt-in native event capture (HS-TD-1-CAPTURE)

Set `EPYC_DISPATCH_CAPTURE_LOG` to an absolute JSONL path in a private existing
scratch directory before starting OpenCode with the EPYC plugin. Default off.
`harness/opencode-plugin/src/dispatch-capture.ts` records raw
`hs_td1.native_event.v1` events; these are **not** prepared replay observations.
The `chat.message` hook snapshots the native user message/parts before returning,
using `output.message.id` (the optional input message ID may be absent).
Native permission asked/updated/replied events retain their entire original
payload, including request/tool/message/call IDs when supplied by the shell.
Each record has a locally generated `capture_id`; it is never a native event ID.

Permission events deliberately have `turn_id: null`, `status: unjoined`.
A later offline join must resolve the native assistant message's `parentID` to
the captured user request, and pair a reply with its exact permission request ID.
Never assign the most recent user request or turn a tool permission into a
turn-wide verdict. Preserve unresolved joins, missing events and absent policy
coverage as unknown. No new replay input is manufactured by this producer.

At the audited shell commit `350c726aa8b6b11eb9242040bc5eb7ae837fbf8a`,
`packages/opencode/src/session/prompt.ts` invokes `chat.message` before persisting
and processing the user message. `packages/opencode/src/permission/index.ts`
emits asked/replied events for interactive permissions but returns/throws for
automatic allow/deny without those events. The older generated SDK also names
`permission.updated`; the collector retains both spellings without translating
payloads. Event absence **cannot** mean permissive. Full turn-policy comparison
still requires explicit native decision instrumentation and a declared real
session window. This change installs code only, enables no live capture, makes
no model call, and closes no real-session acceptance gate.

Writes are awaited by the observation hooks to preserve pre-dispatch snapshot
ordering; they add filesystem overhead, not measured live inference latency.
Failures are swallowed after warning, never changing policy or output. Four
writes may be pending; excess work warns and drops, without a queue. A native
snapshot is serialized before the first await. Payloads above 128 KiB become
explicit oversize metadata. Append sinks must be owned regular files with exact
0600 mode; symlinks and relative paths are refused. Each successful record is
flushed with fsync. Use one capture process per sink: cross-process atomicity,
short-write recovery, exhaustive coverage and restart deduplication are not
guaranteed. Retain raw files privately with the source git object, predeclared
window/count and capture configuration; raw records alone supply no measurement
warrant. A later qualified replay row must preserve this original provenance.

Offline verification: `node --test harness/opencode-plugin/test/*.test.ts`.
