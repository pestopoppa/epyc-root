# CMP-4 r3 incomplete pilot, 2026-11-18

The official `toc-cmp-4-pilot96-20261118-r3` run ended rc=75 at 04:32:39Z with reason `partial-native-incomplete`. Its coverage rule was `completed >= 96`; the native partial records completed=0, planned=96, processed=9 and dropped=9. No complete RESULT.json exists. This does not establish a BAPS, accuracy, Pass^3, arm contrast, per-valid-run duration or deployment result.

The instrument correctly voided the first LongBench point before its boundary and selected the registered same-stratum reserve `real_suite_v1_0026@3`. Nine active MBPP runs across arms and repetitions were dropped after two attempts each, reporting `ValueError: missing post-boundary action or measurement fields`. The allocator deadline stopped the run before the dropped-run threshold was exceeded. Server exit was clean. Missing outcomes remain UNKNOWN; they are not zero BAPS or successful compliance.

Native custody is preserved at `/mnt/raid0/llm/tmp/delegation-context-preassembly/cmp4-r3-disposition/native/`, with its sealed packet in sibling `packet/`. The 382-file inventory is `NATIVE-PACKET-SHA256SUMS`, SHA-256 `e7c2dbbb34a0e9b7fba0717e25d1d8f44761c5a435a842fe3454f2e15d438065`. Owner interpretation is in sibling `verdict.json`. The existing FILED receipt consumed the run-end event; the critical alert `de2cdf82e42e25e50ee80dc2` was acknowledged.

The registered endpoint counts actions on numeric turns b+1 through b+5 after boundary turn b. The preregistration explicitly prohibits scoring missing post-boundary actions as zero. Section 7a authorizes whole-point replacement only for trajectories with no boundary event. A clean terminal on the boundary turn is a distinct zero-denominator outcome. Broadening replacement to it requires a prospective operator amendment; it cannot be silently inferred from the existing reserve rule or retroactively turn this partial run into completed coverage.

This records an incomplete instrument outcome. The original paired pilot and later 720-run/live-stack validation remain open under [TOC-CMP-4](../../handoffs/active/context-and-token-economy.md).
