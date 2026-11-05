# KPF-RS-1 r6 source-impact scan

The full row passed its source-scan rule at detached candidate `8952a0f693fb923918157eb25117641b74766230`. The seven native upstream results were LOW: `build_conv_state` (3 indexed impacts), `build_recurrent_attn` (4), `seq_rm` (2), and `seq_cp`, `state_write`, `state_read`, `s_copy` (0 each). `scan_complete` reports seven impacts and `partial=false`; the preceding source-reference record was partial progress only. Raw per-symbol output, analyzer logs, graph status and coverage are retained alongside this note.

The scan used the native 512 KiB cap; its skipped-file inventory is not evidence of zero impact in omitted files. The pass does not complete recurrent-state serialization, mutation testing, or CPU/GPU conformance.

The analyzer stderr is retained with epoch-millisecond timestamps redacted as `analyze.stderr` (original SHA-256 `1a823b4f8a8eacd5c14411f03bde74256f83f97e877f39e3a4a3296a8a5d0314`); the coverage manifest names its original `analyze.stderr` filename.
