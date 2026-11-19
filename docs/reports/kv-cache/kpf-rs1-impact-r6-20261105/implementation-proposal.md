# KPF-RS-1 next implementation slice

The r6 scan answered its seven-query question: all seven native upstream impacts are exact and LOW, and scan_complete is nonpartial at 8952a0f693fb923918157eb25117641b74766230. Retain coverage.json: the native 512 KiB cap omits files and zero callers is not exhaustive zero impact. Do not requeue the same seven queries merely because the source-reference preamble says partial.

The detached scan source directory is absent. The four pinned implementation objects remain available in llama.cpp-experimental and prepare.py verified all four digests against r6 identity.json. The smoke does not grant source edit clearance on a different candidate.

Next row: **KPF-RS-1 model-free capture/provenance implementation**, on an owned champion-derived experimental branch, with candidate identity and source-bound context/impact for additional observer/test/synchronization symbols. No inference is part of this row. Source branch creation and graph work must obey current disk/claim limits; no weakening of the 150 GiB full scan floor.

Implementation order and exact files are in implementation-packet.json. The observer should read public r_l/s_l/p_l and cells/rs_idx after synchronization; it must not substitute state_write output, which stores selected current rows only. The test currently hardcodes n_seq_max=1 and all batch entries to sequence 0: both must become schedule-driven for np=4. Fork coverage must invoke actual seq_cp and independently advance parent/child.

At baseline, build_recurrent_attn computes n_written=min(n_seq_tokens,K) and enqueues a single multi-plane ggml_cpy; trailing S planes are unwritten. build_conv_state instead enqueues all K convolution-plane writes. A generic written flag set at graph construction would falsely prove completed writes, especially under a skipped-write mutation. Bind provenance to actual completed execution, and test short n_seq_tokens<K to expose the asymmetry. Capture optional P tensors explicitly or report unsupported; do not infer their update sites from R alone.

No implementation files were edited: deleted indexed worktree and unscanned additional symbols make a source patch inappropriate in this bounded follow-up. The ready source-object preparation spec and passing receipt are retained, not published. The owning session must add prospective belief-source wiring before measured output; this preparatory packet is not a measured result.
