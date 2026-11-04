# KPF-50 outer supervisor containment candidate

This model-free outer process is a verified subreaper, captures the inner
supervisor's PID and birth, and drains adopted direct descendants after its
death. It refuses a normal outcome unless it observed an inner normal-finished
event and all adopted children were reaped. Three subprocess tests passed:
normal completion, SIGKILL of the captured inner supervisor while its child
was live, and SIGTERM to the outer process. The SIGKILL case verified that the
adopted child was reaped and no cleanup receipt was emitted.

This is a prototype, not integrated or safe for native use. Abrupt death of
the outer process itself, nested survivors, initial pidfd failures, stdout/IPC
failure before its protected region, remaining races, and full runner
integration are unqualified. No GPU, model, or profiling run was performed.
