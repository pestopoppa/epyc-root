# KPF-50 host clock bracket validator

`bracket.py` is a separate structural validator for the before/after records produced by the existing `kpf50-clock-witness-20261104/clock_witness.py`. It checks schema, phase, window/run lineage, producer PID and birth/lifetime fields, producer pin, native SHA-256 binding, native producer PID/frequency, ordered in-lifetime samples, and that the selected sample is the narrowest native bracket. It then checks that the caller-supplied step interval, expressed in `CLOCK_MONOTONIC` nanoseconds, satisfies:

```
before.mono_after_ns <= step_begin_ns < step_end_ns <= after.mono_before_ns
```

The supplied step timestamps are not authenticated or source-bound by this validator; a separate bound native trace is required to establish that they describe the actual profiling step. The validator intentionally does not translate rocprof `BeginNs`/`EndNs` into host time, estimate an HSA/host offset, or establish that profiler nanoseconds share either clock's epoch. HSA tick ordering and a host-monotonic bracket do not calibrate the profiler, bound drift through the interval, prove device use, or qualify a measurement. Those remain separate evidence requirements. This is model-free prospective code; no GPU, inference, or profiling run was performed.

Run the model-free checks with:

```
python3 -m unittest discover -s docs/reports/kv-cache/kpf50-clock-bracket-20261104 -p 'test_*.py'
```
