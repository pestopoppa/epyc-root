# KPF-17 r3 signal control

A model-free actual-GDB control sent SIGTERM to its own captured debugger after
the inferior signaled readiness. It reproduced debugger rc0, an inferior exit
event with a null exit code, and no continue-return record. This establishes a
possible mechanism for the retained r3 event pattern, not who or what signaled
that debugger or the cause of the original INVALID attempt.

The original [launcher log](poller.out) records that region-lock forwarded
SIGTERM to its child before the launcher reported rc0/complete. It does not
identify what initiated the signal. The engine can accept a sealed INVALID
result as complete, so the reported outer rc is not proof that the inferior
completed normally; the native result remains INVALID.
