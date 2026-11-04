# KPF-50 cgroup admission refusal

This read-only diagnostic refuses native admission when parent cgroup
membership is writable, and also refuses when that particular check is
negative: it cannot establish the absence of writable alternate groups,
capabilities, ACLs, namespaces, or later changes. It does not modify cgroups.
Four model-free unit tests passed for writable, apparently nonwritable,
missing, and symlinked paths.

On this host the diagnostic refused `/sys/fs/cgroup` because the effective
identity can write its `cgroup.procs`. This is an observed access check, not
proof of containment or a native run. The candidate is not wired into the
KPF-50 runner, and no admission path is offered until a separately qualified
containment boundary is available.
