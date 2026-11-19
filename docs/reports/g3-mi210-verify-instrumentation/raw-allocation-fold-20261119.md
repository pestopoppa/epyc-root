# G3 raw allocation fold repair (2026-11-19)

The final environment assessment previously trusted the sampler's stored
`ownership=PASS` without checking its retained `allocations`. A two-sample
fixture with own PID 42 and foreign PID 43 returned PASS. Twelve malformed or
missing allocation cases reproduced the same defect before the repair.

The fold now requires exactly the observed server PID as the allocation-map
key and a strictly positive integer byte count. Missing maps, foreign entries
(including zero-byte entries), missing/zero/negative own allocation, booleans,
floats and strings yield UNKNOWN. This matches the existing sampler's strict
no-foreign-entry policy. The six-process endpoint regression separately proves
that corrupting any one process's allocations suppresses `vec_observed` even
when both stored PASS flags remain present.

Validation: `python3 -m unittest discover -s
 docs/reports/g3-mi210-verify-instrumentation -p 'test_*.py'` passes **111 tests**.
The new allocation regression failed in twelve cases before the source change.
`git diff --check` passes. GitNexus status/impact reported no index in this lane;
direct imports confine this repair to the G3 diagnostic and its tests.

SHA-256 source bindings:

- `environment_gates.py`: `900653dd4be62d2e8d0091a867faca47ef2920049572a7b731485f61602a3717`
- `test_environment_gates.py`: `01d2f1391ea3e5c9e8708461d243ed7f914d1f3813c4cb3d27a64a43d8e6ac60`
- `test_native_protocol.py`: `f179c17d2e61a094a81f257595a38ae91d679e8641343a482ff3e7ed87c58086`

No native inference ran or successor row was published. Historical UNKNOWN
records remain unchanged; new configurations must bind the current protocol
sources. G3's measured endpoint remains open.

[no-belief: diagnostic correctness repair and model-free regressions only]
