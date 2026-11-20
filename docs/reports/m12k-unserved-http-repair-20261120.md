# M-12k non-200 routing detector repair

M-12k-UNSERVED-DETECT is source-complete. Canonical row driver
`scripts/benchmark/m12k_frontdoor_memory_ab.py` succeeds the owner’s scratch
`/mnt/raid0/llm/tmp/m12k-gpu-20261119T1500Z/job.py`, baseline SHA-256
`94491eec07c6eaf845c17cd979390f34361d1c18cf3df39d3585ea74a233560f`.
The historical failed row and its frozen inputs remain untouched. A future
publication must use this canonical driver with explicit `M12K_RUN_DIR` and
`M12K_ROW_ID`, fresh outputs and a source manifest binding these bytes.
This is the row client source, not an evidence copy or application deployment.

The defect was in error decoding: `post_chat` retained only the first 300 error
characters and discarded structured ChatResponse routing fields. The API's
`chat.py` returns `response.model_dump()` with error HTTP codes. The repaired
client parses the full JSON body before truncating receipt text, and retains
HTTP code, routed_to, role_history, routing_strategy, answer and error_detail.

UNSERVED now accepts non-200 responses only with both response-local evidence
of a role outside the four declared served roles and a backend failure reason
(connection, timeout, unavailability, admission/queue, rate limit or parked-role).
A bare 429 or pre-routing 503, malformed body, served-role failure or status
alone remains a non-ok infrastructure response. Successful answers from another
role remain scoreable. The original HTTP-200 in-band predicate is unchanged.
Historical log context cannot be substituted for absent per-response evidence.

An UNSERVED request has `correct=null` and bypasses answer scoring. Existing
paired reducers exclude its entire ON/OFF pair from accuracy, McNemar, bootstrap,
latency, routing divergence and A/A floor, and count it toward the existing
strict >10% FUTILITY_UNSERVED_ROUTING boundary at the original looks. The smoke
retains error metadata and reports UNSERVED without failing for that condition,
as original section 10 requires; unknown HTTP failures, switch violations and
store movement continue to fail smoke. No thresholds, sample sizes, retry rules
or success gates changed. These semantics supersede section 10's HTTP-200-only
restriction for the next publication; preserve the original frozen declaration
and include this dated amendment in that publication's protocol binding.

Validation: **43 tests pass** across `tests/benchmark/test_m12k_unserved.py` and the
existing `tests/benchmark/test_frontdoor_memory_pairs.py`; **selftest ok** from
`python3 scripts/benchmark/m12k_frontdoor_memory_ab.py --selftest`.
The 19 new fixture cases run the real urllib HTTP-error decoding, request
recorder, interim/final reducers and smoke recorder without network/model/store
access. They cover 502/504/429 in either arm; 11% versus exactly 10% pair voids;
complete pair exclusion from both arm statistics and A/A; full-payload parsing
beyond 300 bytes; history/error_detail evidence; malformed and bare errors;
served roles; HTTP-200 scoring; smoke acceptance versus infrastructure refusal.
The first fixture run exposed a fixture OFF strategy marked learned; the fixture
now preserves the independent switch guard rather than weakening that guard.

Source SHA-256: `e571903d5ac8380372739b31b7112c9c94990c6d7a71d323a59a890cdb8ecfb5`; Git blob `d48f5e8dbee9262a55752fb2839e6bc59362011f`.
Test SHA-256: `ef489eaf49508bfb1d13df94317d008353f587d92ff32810e68690b9118df636`; Git blob `6d06cf133a39b0871e48382579fca4efd5b7ace6`.
The existing VB-M12K-PAIRS-WIRE task/source row now includes the native driver
and error/void receipts. No adapter canary or measurement warrant is claimed.
GitNexus status/impact found no index; static scope is benchmark client/error
handling, recording and smoke, with offline reducer regression coverage.

Parent M-12k remains open: repair the external plan-review write boundary for
probe/smoke/health, integrate at the API owner's reload boundary, serve architect
and coder routes, then publish a fresh row with unchanged-store qualification.
No inference, live API reload, store change or answer-quality result occurred.
