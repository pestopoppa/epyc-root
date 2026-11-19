# KPF-50 parent-death nested-process counterexample

One model-free, own-child test passed. An isolated parent subreaper captured
the PID and birth of an outer process, its direct child and a forked
grandchild. The direct child armed `PR_SET_PDEATHSIG=SIGKILL`; after the
captured outer process was killed, the direct child terminated by signal but
the same captured grandchild remained alive. The test then killed and reaped
that grandchild, and verified every captured PID absent using both `ps` and
`/proc`.

This is a synthetic demonstration of a nested-descendant escape under the
parent-death design, not an execution of the KPF-50 profiling runner or an
exhaustive proof about all possible containment designs. The test's parent
subreaper performed the cleanup. A real runner needs separately qualified
containment and cleanup for descendants beyond the direct parent-death chain;
no model, GPU or profiling result follows.
