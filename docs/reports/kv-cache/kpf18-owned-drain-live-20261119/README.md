# KPF-18 real captured-child cleanup controls

Three Linux process tests PASS against the unchanged source-bound helper
`docs/reports/kv-cache/kpf18-g3-owned-drain-20261104/owned_drain.py`, SHA-256
`6cf1d4159ee768b762ba76f911cab16b675a4b115b1fff34cf6c3e35aa461ec4`.
They exercise actual TERM/reap, TERM-ignore followed by KILL/reap, and a real
orphaned grandchild adopted by PR_SET_CHILD_SUBREAPER and reaped. Each isolated
supervisor starts with no children, checks direct ownership before draining,
and refuses success if its child list or target /proc entry remains. The KILL
case also requires the helper's escalation message. Harness cleanup signals
only captured pidfds and its own Popen supervisor. No name-pattern signals.

Reproduce:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -B -m unittest discover \
  -s docs/reports/kv-cache/kpf18-owned-drain-live-20261119 -p test_live.py -v
```

Test SHA-256: `63511c5743b578d49bc4f043e42ae0706e8697c1593851ad8adedf8621b6e578`.

This closes the fake-only coverage gap for these three helper paths. It does
not establish full-driver integration, native request cancellation/release,
owned server cleanup, rowflow admission, model or GPU execution. No existing
entry barrier or runtime file is changed. KPF-18.0d remains open. Next: integrate
this helper into the disabled full-driver supervisor with preexisting-child
refusal and qualify its cleanup ordering before publishing native lifecycle.

GitNexus status and upstream impact could not run: this sparse lane is not
indexed. Changes are confined to this test package and the owning handoff.
No new measurement source or measurement warrant is asserted; this is software
qualification, recorded with no-belief.
