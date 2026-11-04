# KPF-50 private-cgroup escape control

One model-free own-child test passed. It created one private cgroup-v2 subtree
with two private sibling groups. The test's child entered one sibling and then
moved itself into the other; the parent observed its captured PID leave the
first membership list and enter the second. The child exited normally and the
test removed both groups and the private parent. It did not write to any shared
parent cgroup's membership or use `cgroup.kill`.

This demonstrates same-UID escape from a writable private sibling boundary in
the tested environment. It does not exercise KPF-50, a profiler, GPU, process
death or a privileged admission boundary, and does not prove how all possible
cgroup configurations behave. A membership snapshot alone cannot establish
containment when the process can write an alternate cgroup's membership file.
