# KPF-50 prospective HIP build result

`kvfork50-hip-build-20261104` completed rc0 on CPUs 24–47. The build-only rule is met: source `1e8a6d5da9836a27e8f1d2010a02e6cebd95abdc`, linked HIP server and ggml libraries, own-library linkage and runtime/file custody are recorded in `RESULT.json` and `linkage.log`. The server implementation contains all six requested KPF50 step/iteration/draft/input markers, and libllama contains both trunk-mask markers. The retained server SHA-256 is `f2ff854e01ce8ceecf43a1afeafb07632ce05c95df6884ad4156e76c2b625701`.

This is a build-only PASS. No model, GPU execution, profiling, historical-result adjudication, performance, or promotion conclusion follows. KPF-50 remains open for its profiling and conditional serving gates.
