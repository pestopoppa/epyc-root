# KPF-50 child evidence guard proposal

This is an unapplied review proposal for `KPF-50.CHILD-EVIDENCE-OUTPUT`. The proposed guard refuses an output path that is the input file, a symlink to it, or an existing hard link to it. Nine isolated tests passed on a scratch copy, including those aliases and a separate output. Exact-source GitNexus upstream impact remains unavailable: the lane is unindexed and older indexed trees do not contain this file. Do not apply the patch before the required impact result.

The proposed path checks and subsequent write are separate operations. A concurrent path replacement can redirect the write after the checks; the proposal protects static paths only and is not a concurrent filesystem safety guarantee. The eventual implementation should account for that limitation before claiming stronger protection.
