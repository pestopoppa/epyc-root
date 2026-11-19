# G3 sampled environment gates (2026-11-19)

The prospective six-process native protocol now requires independent scheduler,
KFD allocation and operating-clock observations for both MTP-off controls and
all four MTP-on cells. Missing evidence yields UNKNOWN and no `vec_observed`
value. Historical R4/R5 records remain UNKNOWN and unchanged. No native model
inference ran and no successor was published in this change.

The runner reads the scheduler's fixed production grants directory, checks the
configured row against FILLER_ID, the live MI210 grant window, STOP/deadline and
captured PID registry, and refuses competing MI210 or gpu-quiet leases. KFD
allocations must include positive own allocation and no foreign MI210 allocation
entry. Active sclk and mclk values come from the discovered device's amdgpu
pp_dpm files; missing or ambiguous active markers fail closed. These are
independent observations, not values inferred from the dispatch trace or from
realtime/monotonic agreement.

The future base configuration must predeclare `row_id`, `environment_policy`
(sclk_mhz and mclk_mhz inclusive [min,max] bounds, plus positive max_gap_s), and
`protocol_sources` (the exact twelve-file SHA-256 map returned by
native_protocol.source_bindings()). Bind that map at preparation time. Both
protocol entry and each child runner verify it before native execution; the
retained per-cell configurations carry the map. These are source identities,
not a replacement for the runner's existing content-bound binary receipt.

Every request needs at least two distinct in-window observations. Each sample
and each uncovered gap must fit the declared maximum gap; observations must be
ordered, match row/PID/GPU identity, stay within one unchanged lease, and satisfy
the declared operating-clock bounds. The fold re-evaluates raw environment
samples instead of accepting only a stored PASS flag. All six processes must
share the grant digest. Only a complete dispatch protocol with all environment
gates passing yields SCOPED_DISPATCH_OBSERVED. This establishes a bounded sampled
environment only: it does not prove isolation or stable clocks between samples,
identify continuous clock behavior, or establish throughput/bandwidth. Clock
policy values for the future native row still need to be declared in its spec.

The wider regression run exposed a real cancellation defect: InterruptedError
from SIGTERM could be swallowed by the health-retry OSError handler. The runner
now propagates InterruptedError so its captured process group is drained. The
two private mock servers left by the failing tests were identified by their
exact test fixture paths, terminated by captured PID, and confirmed absent.

Validation: **50 model-free tests PASS** across environment gates (6), native
protocol (13), timed analyzer (11), V5 trace (6), diagnostic runner (2), binary
binding (6), active SIGTERM drain (1), and sysfs residency (5). After extending
the lease refusal cases, the 19 environment/protocol tests passed again.
The suite covers source drift, malformed policy, missing/sparse/duplicate
samples, raw evidence inconsistent with claimed PASS, device/row/PID mismatch,
changed/expired/missing grants, CPU-only grants, competing GPU/quiet grants,
foreign KFD allocations, missing PID registration, STOP, and operating clocks
outside declared bounds. `git diff --check` passed. GitNexus status/impact could
not provide a graph because this sparse lane has no index; direct source imports
and focused caller tests bound the change to the G3 diagnostic path.

Source identities (SHA-256):

- `environment_gates.py`: `19e587e4cd96b6a2314d8999d7bc1de83067a804b09a9c3ffc9246ccbfef57e8`
- `diagnostic_runner.py`: `bea72274779911ae89d237433c7b74940f51da8b9417254d8765d448db359445`
- `native_protocol.py`: `44bbefc7217ed3c4ab220701263c60ff8959d7924abf6aeb1e1ee93b0d2eedc3`
- `test_environment_gates.py`: `6c1556a9e4a76bea53c25e88c9f590c57af0829cebc6391a73abe22c56baa124`
- `test_native_protocol.py`: `3b8b751b628f4d817bdfebe78b5b3c2899958ed4bb4e1f6f6a48c0d0a1805604`

[no-belief: diagnostic code and model-free regression tests only]
