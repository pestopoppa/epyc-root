# NEMO request identity producers — independent source preparation

Status: **OFFLINE-PREPARED / NOT BUILD-QUALIFIED**. This packet is a narrow
request identity producer handoff, prepared independently of the frozen r14
build packet. Producer and validator tests pass, and the frozen r14 patch passes
an apply check against pinned C3 source files. No source checkout was modified,
no server or client request was run, no build was performed, no historical trace
was reassigned, and no row was published.

## Contents and data flow

- `capture_client.py` creates a random request ID, sends one non-streaming
  completion, retains the exact request and response bodies as base64, verifies
  the response echo, and publishes a completed JSON record atomically without
  replacing an existing destination.
- `request_join-producer.fragment.txt` gives the native server insertion
  contract: accept the ID only for one string prompt / one non-stream completion,
  emit one `request_join` mapping the request ID to the actual server task ID,
  then echo the ID in the final response.
- `validate_request_join.py` checks transport echoes and raw body identities
  against exactly one native join per request. `validate_events.py` enforces the
  envelope signature and basic native event structure.
- `test_capture_publication.py` checks complete atomic publication, cleanup after
  producer failure, and refusal of an occupied destination before a request is sent.

All artifacts here are intended for future source/build qualification. The
native fragment matches the request identity addition in r14's proposed handler
patch, and the complete patch applies cleanly (check only) to the two pinned C3
server files. This verifies source context, not compilation or API correctness.
Producer provenance still requires build/capture qualification. The validator
result explicitly leaves native event authenticity, emitted-token reconciliation
and profiler attribution unassessed.

## Why no compute row was published

This packet's work is file preparation, source-context verification and offline
tests. It has no independent compute action with a defensible estimate of at
least five minutes. The r14 server+fixture build is already pending; relabeling
that same build as a separate prerequisite would duplicate it. Historical trace
resegmentation remains analysis-only and cannot be made compute by this packet.

## Required next qualification

For build qualification, the owner must use a fresh source worktree tied to the
approved experimental commit and finalized instrumentation patch. Then qualify
the exact client and server producer bytes before any prospective capture. A
request join proves identity mapping only; it does not prove timestamp boundaries,
profiler alignment, token counts, workload attribution, or any historical boundary.

Offline checks run 2026-11-05: `python3 -m unittest -v test_capture_publication.py`
(3 PASS) in this packet and `python3 -m unittest -v test_capture_client
test_validate_events test_validate_request_join test_fixture_result_layout`
(26 PASS) in the frozen r14 packet. `py_compile` and the packet SHA manifest
also passed. No row was published because no distinct compute prerequisite met
the >=5 minute threshold.

The reference packet also includes two mocked-transport checks: exact request
and response bytes retain the same request ID, while bad echoes and unsupported
request shapes fail closed without issuing an invalid request. These tests do
not run a server or establish marker-to-token correlation.

## Pinned C3 integration

`c3-instrument.patch` is the existing r14 marker patch, including the native
request-to-task join and single-result echo. `INTEGRATION.json` records its
source review and successful apply check against C3
`dcc853b5559bef4e50acf251f4910f7f4e0ba538`. The source review found that the
join uses the assigned task ID before queue submission and applies only to one
non-streaming completion. The checked source worktree was removed. The patch
has not been compiled or validated against a live request or profiler capture.
