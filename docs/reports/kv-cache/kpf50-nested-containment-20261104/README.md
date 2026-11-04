# KPF-50 nested descendant stop control

The model-free fixture launches the prior parent-death supervisor with a
command that forks a nested child. A Unix socket binds the child's PID and
birth before a requested stop. The isolated supervisor's actual cleanup
receipt records the adopted child's captured identity and reaping; the outer
supervisor returns a non-success outcome. The test parent is itself a
subreaper and signals only its own captured, birth-matched children if a
failure leaves any adopted survivors.

One fixture test passed. This tests a requested stop while the outer
supervisor remains alive; it does not establish containment after outer
SIGKILL, parent-death coverage of arbitrary descendants, the pre-capture
startup interval, GPU residency or a production profiler result. It is not
integrated into a native workload.
