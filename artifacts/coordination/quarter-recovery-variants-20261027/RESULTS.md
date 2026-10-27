# Artifact-only recovery results — 2026-10-27

WS58's q0 META run started 20:41:17Z and ended 20:41:20Z rc0, normal resource guard PASS, peak 25,940 KiB, drained true. Its original `RECOVERY-ACCEPTED` matches the q0 `RECOVERY-WORK-DONE`; marker SHA-256 is 42d29cdae3c0ffebc51c9de8fcd48235cb528bf1cf60866e7298f5e80b52b8fe. Marker records original build rc70 and outer drain unproven. The prior original run is not reclassified.

WS58's q0 DF2 run started 20:42:02Z and ended 20:42:05Z rc0, normal resource guard PASS, peak 26,000 KiB, drained true. The original `RECOVERY-COMPLETE` and `BUILD-COMPLETE` are identical hardlinks, inode 193120741, SHA-256 8e94fd7f8cb579438c8a7cbe20866e692e8d2378985fc58c702c4ee888df6322. Original evidence hashes are retained in that marker.

Exact source, ELF and marker paths and hashes are in ACTUAL-BINDINGS.sha256. Runtime logs are in `/mnt/raid0/llm/tmp/codex-ni-20261027-quarter-recovery-variants/{meta,df2}/ws58-launcher.out`; end records are `/mnt/raid0/llm/tmp/compute-flags/grants/codex-ni-{meta-recovery-q0,df2-build-recovery-q0}-20261027.ended`. MAIN accepted these artifact recoveries only. They do not establish GPU correctness, speed, parity or promotion. Original CPU/HIP compiles were not rerun. [no-belief: operational completion evidence, not a performance or correctness measurement]

The originally launched watcher did not persist (PID absent, empty log); its one-shot script was rerun after completion and produced both result flags from the original markers. This is notification repair, not another recovery.
