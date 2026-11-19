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
