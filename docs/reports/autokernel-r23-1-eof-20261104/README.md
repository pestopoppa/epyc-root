# R23-1 Linux EOF behavior, 2026-11-04

The granted model-free run completed rc 0. The actual custody CLI exited rc 1 on model-selection EOF after the local mock health and model-list requests, with no POST. Eight linked console reader cases passed: EOF, blank, slash, and text in both simple and PTY modes. [Result and pinned closure](result.json) retain per-case original log hashes and source, binary, and tool identities. Archived log copies redact process memory ranges; their bytes therefore differ from the original hashes. No model or inference was used.

This checks the v10-derived candidate on Linux, not the full C5 champion candidate. It does not test chat, mtmd, Windows, numerical correctness, performance, or manual champion admission. The patch changes shared console code as well as CLI and mtmd. The existing upstream fix was merged in PR 29722; a duplicate upstream filing is unnecessary.
