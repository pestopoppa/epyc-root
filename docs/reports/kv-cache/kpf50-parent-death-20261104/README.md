# KPF-50 parent-death containment candidate

This isolated successor arms and verifies `PR_SET_PDEATHSIG=SIGKILL` before
exec of the inner supervisor and its direct window command, and refuses a
changed parent between fork and setup. Both launching processes are intended
to be single-threaded. Five model-free tests passed, including an isolated
subreaper fixture that SIGKILLed its own outer process and then observed both
captured direct descendants terminated and reaped.

This is not an integrated or native-safe runner. The fixture's *test parent*
was a subreaper and performed the reaping; the killed outer process cannot do
so. Parent-death signals are not inherited across an arbitrary program's
forked descendants and can be cleared by a child, so this does not establish
containment of nested survivors. Abrupt death before the first signal is armed,
privileged exec semantics, same-UID mutation, full runner integration and
native profiler/clock/device custody remain unqualified. No model, profiling
or GPU run was performed.
