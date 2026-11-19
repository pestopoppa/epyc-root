# KPF-50 cleanup guard integration boundary

This isolated runner copy requires a real same-process `Guard` to have captured
and reaped the server PID and birth identity before the typed window receipt
can be published. A server-only stop record, missing guard, unreaped child or
birth mismatch is refused. The guard publishes the typed cleanup record only
after it proves the child-free subreaper and ECHILD checks. Two model-free
subprocess tests passed, including an actual child and end-to-end receipt.

This is a fail-closed integration boundary, not a runnable profiling packet.
The existing runner is multithreaded, starts the server itself and uses
`Popen.poll`/`wait`; it does not create or drive a compatible single-threaded
subreaper guard and its stop record lacks the required birth identity. Its
normal item-7 path therefore refuses completion with this candidate. A new
isolated per-window process supervisor and IPC, native clock and trace evidence,
device residency, input sealing and publisher qualification remain necessary.
No profiling, model run or scientific, same-UID race or full-production
cleanup claim follows.
