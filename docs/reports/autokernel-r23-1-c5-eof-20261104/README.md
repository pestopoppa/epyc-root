# R23-1 C5 Linux EOF behavior, 2026-11-04

The granted model-free run completed rc 0. The C5 candidate CLI exited rc 1 on model-selection EOF after local mock health and model-list requests with no POST. Eight linked console reader cases passed: EOF, blank, slash, and text in both simple and PTY modes. [Result and pinned closure](result.json) retain per-case original log hashes, source, binary, and tool identities. Archived log copies redact process memory ranges and therefore differ from the original log hashes. No model or inference was used.

This does not test chat, mtmd, Windows, numerical correctness, performance, or manual champion admission. The patch changes shared console code as well as CLI and mtmd. The existing upstream fix was merged in PR 29722.
