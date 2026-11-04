# KPF-50 per-window supervisor and IPC candidate

This isolated, single-threaded process launches one owned command, captures its
PID/birth under a subreaper, accepts a newline-JSON stop command over stdin,
and captures and reaps adopted direct children before publishing a cleanup
receipt. It returns normal only for an unrequested zero exit with no surviving
adopted child. Three model-free subprocess tests passed: normal exit, requested
stop, and a surviving nested child that is adopted, stopped and reaped.

This is a review candidate, not an integrated or publishable KPF-50 runner.
It does not provide native profiler, GPU, clock, model, admission or outcome
custody. Initial child identity/pidfd failure and process termination of the
supervisor itself are not qualified; these cases may leave descendants, so the
candidate must not be used for a real workload until its containment and IPC
failure paths are hardened and tested. A cleanup receipt records cleanup only,
not successful science or a completed window. Same-UID mutation protection and
end-to-end producer/consumer integration remain open. No model or GPU was run.
