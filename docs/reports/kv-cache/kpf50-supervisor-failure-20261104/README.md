# KPF-50 supervisor failure-path candidate

This isolated successor handles SIGTERM, SIGINT and SIGHUP as stop requests,
drains captured children after IPC failure, and bounds the startup failure
path. If pidfd creation fails, signaling falls back only after checking that
the target is the same unreaped direct child. The initial missing-birth path
kills and reaps the owned child before refusing; it never publishes a receipt.

Eight model-free subprocess tests passed: normal exit, explicit stop, nested
adoption, SIGTERM to the supervisor, IPC EOF and malformed input, injected
pidfd failure, and injected initial child-birth failure. These do not establish
containment if the supervisor itself receives SIGKILL or crashes abruptly, nor
do they qualify identity races, native clock or device evidence, scientific
validity, production integration or same-UID mutation safety. The candidate
must not be used for a real workload until those remaining boundaries are
qualified. No model or profiling run was performed.
