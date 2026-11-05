# KPF-18 G3 slots deadline qualification, r2

The original qualification produced 11 passing native controls but ended outer rc75 partial-native-incomplete. Its completion command contains unescaped nested double quotes, which shell parsing removes; the completion checker suppresses stderr, so this is a likely cause rather than a proven runtime diagnosis. R2 uses a separate sealed Python completion validator and new result path. Original data are unchanged.

The qualification is model-free and applies only to the three copied slot-query call sites; it does not establish native cancellation, other slot calls, GPU admission, or the full lifecycle. The publisher smoke passed on four CPUs on 2026-11-05; the full qualification remains pending.
