# KPF-50 outer supervisor startup hardening

This isolated successor moves the protected cleanup boundary immediately after
spawning the inner supervisor. It requires an initial birth and pidfd, and
cleans up an owned unreaped child and adopted descendants on startup failures.
The three existing normal, inner-SIGKILL, and outer-SIGTERM controls passed.
A separate subprocess test injected missing initial birth, pidfd exhaustion,
closed stdout, and selector setup failure; all four cases refused and verified
the owned supervisor PID absent.

This is a model-free review candidate, not integrated into the runner. It does
not prove containment after outer SIGKILL/crash, arbitrary nested process races,
real profiler/clock/device custody, same-UID mutation safety, or a native run.
