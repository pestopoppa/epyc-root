# EXP-09 R6 disk-floor stop

R6 ended rc=75 at the disk floor one second after grant. The native result path does not exist and the event stream contains only a dry-run preflight, so there are no new native treatment cells and no paired comparison. The 24 original R3 controls remain byte-exact in the archived seed (SHA-256 `59b4358cfdb709bf3b14a0781803d6595080b3045c8c0133b830b3e836ba7266`). The smoke cell is qualification evidence, not a native result.

The filing schema uses the empty-content hash as a placeholder when `result_exists=false`; it does not establish an empty result file. The 150 GiB long-run floor remains in force. R3 remains open; future comparisons must disclose split execution and scratch-pointer roots.

A subsequent free-space sample during preparation showed 225 GiB available. The allocator has no disk-aware hold, so this sample does not guarantee capacity at a later grant. The successor preserves the 150 GiB runtime guard and the original seed.
