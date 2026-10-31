# 2026-10-31 — AKX-ALL-8 C5 build packet r4

Repaired the rejected r3 launcher without editing C5 source or production. The keeper's r3 launch failed before work because `state/` was root-owned and UID 1000 could not open its lock. R4 uses node-owned state. Actual entry then exposed an empty container `/mnt/micron` mountpoint and Git ownership check; r4 gates on the worktree `.git`, uses the approved host chroot as UID 1000, and scopes `safe.directory` to that clean C5 worktree.

Final R11 model-free normal compiled and linked `ggml-base` rc0 in 21.5 s with 555 MB sampled peak and full drain. A separate full-target run had live advancing compiler ticks before an own-pidfd interruption; it returned rc75/partial in 127.0 s, 849 MB sampled peak, full drain. Earlier failed controls and the r3 keeper refusal remain preserved. Private keeper scan and row validator passed. Published READY `refactor-akxall8-c5-cpu-build-r4-20261031` at 04:09:41Z; source manifest SHA-256 `da17bd761b8c44b60713f7205b11bae179c86fe353f54aec4bbac0fc32b6fc57`.

The full C5 server image and AKX-ALL-8 long-surface measurement are pending calendar execution. The original t48/ub512 target was retained; the new t96/effective ub2048 declaration is not a live :8074 identity or a timing result. [no-belief: source/build preparation and bounded native controls only]
