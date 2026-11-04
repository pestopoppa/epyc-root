# KPF-50 cgroup admission context

The read-only diagnostic collects the matching cgroup-v2 mount, effective
capabilities and target membership writability. It rejects ambiguous or
malformed mount information, symlinked paths and missing capability data.
It always refuses admission: a snapshot cannot rule out writable alternate
groups, ACLs, namespaces, privilege changes or later races. Five model-free
tests passed. No cgroup or process was modified; no containment, native runner
or permission claim follows. The candidate is not integrated into a runner.
