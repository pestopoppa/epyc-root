# KPF-50 private cgroup membership control

The model-free test created and removed its own cgroup-v2 child under
`/sys/fs/cgroup`. A child entered it and forked a second process; the control
captured both member PIDs, pidfds and birth identities, then released and
reaped the processes normally. The cgroup membership file was empty after exit.
One test passed. The current environment allowed creation and writes to the
private child's `cgroup.procs` and `cgroup.freeze`; neither a shared cgroup nor
`cgroup.kill` was used.

This proves only membership capture for a cooperative, quiescent fork family.
It does not test parent death, cgroup freezing, signals or adversarial escape.
The parent cgroup's `cgroup.procs` is writable by this UID, so same-UID members
can potentially move out and membership cannot by itself prove containment.
No KPF-50 runner, model, profiler or GPU was exercised. Reliable cleanup after
supervisor death needs an independent owner, exact PID/birth capture and a
separately qualified admission/containment boundary before native use.
