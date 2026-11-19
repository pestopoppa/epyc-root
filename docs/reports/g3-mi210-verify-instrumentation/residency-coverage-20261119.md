# G3 dispatch-residency coverage repair (2026-11-19)

The diagnostic analyzer previously returned `SCOPED_DISPATCH_OBSERVED` when
any dispatch had bounded residency, including captures with UNKNOWN joins.
That label did not distinguish partial from complete dispatch coverage. The
R4/R5 endpoint review identified this ambiguity; both historical endpoints
remain UNKNOWN and their retained inputs and outputs are unchanged.

The analyzer now records expected, bounded and UNKNOWN dispatch counts.
`SCOPED_DISPATCH_OBSERVED` requires every native candidate dispatch to have a
bounded join. A nonempty proper subset returns
`PARTIAL_SCOPED_DISPATCH_OBSERVED`, with an explicit coverage reason. Zero
bounded joins remains UNKNOWN. A missing join record also returns UNKNOWN.
Bounded observations and their VEC evidence are retained under the partial
status; unmatched dispatches do not acquire observations. Coverage is over
all parsed candidate invocations and expected attention layers, not just the
first successful invocation.

This change is diagnostic source code, not a new native result or an endpoint
grade. Complete residency coverage alone still cannot establish G3: independent
predeclared negative controls, GPU ownership and the full four-cell endpoint
remain required. Existing sealed row packets retain their original analyzer.
Any successor must bind the revised analyzer before execution. No benchmark
or performance claim is made; no native compute ran.

Validation: **24 focused model-free tests PASS**: 11 timed-analysis, six V5
trace, five sysfs residency and two diagnostic-runner tests. New tests execute
the real V5 parser and residency join on two-layer traces: partial versus full
coverage, all-invocation coverage, missing/foreign/zero/duplicate samples and
missing correlation records. A mocked dispatch-attribution regression retains
its specific non-VEC observation while exposing partial coverage.

Commands:

```sh
python3 -m unittest discover -s docs/reports/g3-mi210-verify-instrumentation -p test_analyze_timed_run.py
python3 -m unittest discover -s docs/reports/g3-mi210-verify-instrumentation -p test_invocation_trace_v5.py
python3 -m unittest discover -s docs/reports/g3-mi210-verify-instrumentation -p test_sysfs_residency.py
python3 -m unittest discover -s docs/reports/g3-mi210-verify-instrumentation -p test_diagnostic_runner.py
```

Analyzer SHA-256 `fd5b19062acdad4f9db02d8c6997b90b7e2534ba764bc141552b5aa135dadf85`.
Test SHA-256 `80138a606f2a03a37004d42c3db3e93aba5ce10ba32194c1f69f49a819fc6b60`.

[no-belief: diagnostic source repair and model-free tests only]
