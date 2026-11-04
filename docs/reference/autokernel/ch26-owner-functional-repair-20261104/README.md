# CH-26b owner/observer functional harness repair

The isolated prototype at `/mnt/raid0/llm/tmp/autokernel-cross-workload-keep-gate/ch26b-serving-observer-join` changed the owner API without updating its model-free native functional harness. The original harness imports `owner_hook` from the wrong directory and omits the required `request_context`. This copy adds the native directory to the import path and supplies a synthetic diagnostic context to `RequestCapture`. The all-zero digest is a synthetic marker, not a real request digest.

`python3 -m unittest -v test_repair` checks the repaired import and context passed to the owner. The copied native modules are the isolated prototype dependencies; they have not been shown to provide authenticated request boundaries or continuous coverage. No inference or native perf capture was run by these unit tests. The original requested C5 floor, actual observation overhead, source authentication, and full native functional qualification remain open.

A proposed six-checkpoint row was withdrawn because its five-minute duration was not supported by a distinct measurement question. Its publication attempt failed at smoke before executing the job: the launcher used relative paths in its source-seal check. No row was published.
