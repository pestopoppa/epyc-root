# KPF-18 GPU item-1 observation, 2026-11-02

Integrated C5 candidate 8952a0f69, 27B + DFlash2, 32 pairs at 8k–80k trunks, one 256-token comparison per cell. Native records, raw rows, linkage, compressed original server log and VRAM/KFD samples are retained; `SHA256SUMS` covers copied data. Decompress the `.gz` files to reproduce their original byte streams.

The draft-on record has 32/32 fork witnesses and 64/64 fresh cache-zero checks. Draft-off reuses each slot’s L-1 checkpoint with speculative n_max 0 (96/96 restore checks), not a separate draft-free server. Fork-vs-fresh-A matched all 256 tokens in 6/32 draft-on and 5/32 no-draft cases; fresh-A-vs-fresh-B matched 6/32 and 8/32 respectively. None of those comparisons was fully bit-identical. Matching first-token/top-k aggregates and differing fresh controls do not establish a fork-specific cause. No gate or performance pass is claimed.

The original outer chain was stopped at operator request while this already-running item completed; its outer exit receipt is absent. Both native records finalized and record the owned server reaped, with linkage and GPU residency; there was no rowflow grant. CPU/model/build co-tenancy occurred during the run, so there is no clean timing claim. The direct-claim original is retained under `/mnt/raid0/llm/tmp/kv-prefix-fork/kpf18-item1-integrated-20261102/` with KEEP.
