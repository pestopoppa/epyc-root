# KPF-64-SNAPSLOT-READ — design note (code read, C17 @ ed5d94969)

Question: with speculation on (n_rs_seq >= 4), do the last prompt ubatch's GDN K-snapshot slots and conv history already hold the state at n-4, so the server's n-4 checkpoint batch cut can be replaced by a snapshot-slot copy with no kernel change?

## Verdict: possible, and exact up to one rounding-path caveat; open an implementation box.

Evidence (all file:line @ ed5d94969 unless noted):

1. **Slot layout.** `ggml_gated_delta_net(..., K = n_rs_seq + 1)` (src/models/delta-net-base.cpp, build_recurrent_attn, `int64_t K = cparams.n_rs_seq + 1`). The op writes the last min(n_tokens, K) per-token states: "slot 0 = most recent state, slot s = s tokens back" (ggml-cuda gated_delta_net.cu L718-731, the dive extract `c17_gdn.cu`). The chunked prefill kernel processes those K tokens as single-token chunks "so every per-token snapshot the cache keeps is materialised exactly" (c17_gdn.cu L37-38). So after any ubatch of >= K tokens, slot 4 = state after (N-4) tokens (needs n_rs_seq >= 4; the served 27B MTP log shows n_rs_seq = 8).
2. **Conv history.** delta-net-base.cpp (the `else` branch of the conv-state update, [TAG_RECURRENT_ROLLBACK_SPLITS]) writes K conv windows, `s_slot = K - t`, one per rollback slot, with the same slot index as the GDN state. So conv and S agree at slot 4.
3. **The last ubatch always contains the tail.** src/llama-memory-recurrent.cpp:494 `split_equal(n_ubatch, true, n_rs_seq + 1)` keeps the trailing (1 + n_rs_seq) tokens of each seq in one ubatch, so without the n-4 cut the final ubatch has >= K tokens (unless the whole remaining prompt is shorter than K: then slots older than n_tokens are caller-owned/stale; treat as "not available", keep the cut).
4. **A checkpoint is exactly a recurrent-only blob and the serializer already reads a chosen slot.** server-context.cpp:3360-3372 `create_checkpoint` uses `update_tgt(ctx_tgt, slot.id, LLAMA_STATE_SEQ_FLAGS_PARTIAL_ONLY)` (pos_min == pos_max, no attention KV). `llama_memory_recurrent::state_write_data` (memory-recurrent.cpp ~L852-870) serialises the row group `rs_idx_cur = rs_idx[seq_id]`; i.e. setting `set_rs_idx(seq, 4)` and calling the existing PARTIAL_ONLY writer emits the n-4 state; `set_rs_idx(seq, 0)` restores. This is the same mechanism `seq_rm` rollback uses (memory-recurrent.cpp:209-212). No kernel change.
5. **Existing server n-4 rule it replaces.** server-context.cpp:5314-5330 `checkpoint_offsets = {4 + n_ubatch, 4}` breaks the batch so `create_checkpoint` (before llama_decode, :5406-5409) sees the state at N-4.

Required (small) code, none of it in a kernel:
- A "peek checkpoint at slot s" path: `set_rs_idx(seq, s)` -> write -> `set_rs_idx(seq, 0)`, guarded.
- **Guard must be new.** `cell.rs_max` (memory-recurrent.cpp:726) is `n_seq_tokens - 1` only when the ubatch has <= n_rs_seq+1 tokens, else 0, so the seq_rm guard cannot be reused: add `snap_valid = min(n_seq_tokens, K) - 1` per cell, set in the same place, refuse when s > snap_valid, when the cell is shared (>1 seq), or when a reorder swapped the cell (see c7435cc77).
- **Draft/speculative side.** `create_checkpoint` also stashes `update_dft(ctx_dft, ...)` and `common_speculative_get_state` (:3368-3372). The MTP draft context has n_rs_seq = 0 (:1629), so its state at n-4 is not snapshotted. Open item for the implementation box: confirm the draft part (2.27 MiB; attention-like KV, rolled back by position) can be taken at N instead of N-4 or reconstructed by seq_rm; if not, the cut stays for draft-bearing recipes.
- Numerics: slot 4 is the per-token recurrent path state for tokens N-K..N-4 started from the chunked-scan state at N-K; the cut path's state at N-4 is a fully chunked scan. F32 both; not byte-identical, so the gate is KLD/top-1 equivalence of the restored continuation (the KPF-RS-1 A/A floor), not bytes.

## What removing the n-4 cut saves on the served recipes

Measured on the only timestamped served-recipe log (Qwen3.6-27B-MTP-Q8_0, np 2, n_batch = n_ubatch = 2048, n_rs_seq 8; `kpf64_cuts.py`, 1708 requests): n-4 cuts on 99.7% of requests; with n_batch == n_ubatch the n-4 break adds a **ubatch** as well as a server iteration (with n_batch >= n_ubatch + 4 it would add an iteration only). Upper-ish estimate of the extra wall attributable to the n-4 cut: **5.3% of prefill wall** (see KPF-64-CUTS table; interval also holds co-scheduled slot work), plus one checkpoint creation (~53 ms median, 0.64% of prefill wall) that the copy would still pay. Short requests (<= 200 processed tokens, 28% of requests) carry most of the relative cost.

## Precedent

The FlashStates fork resolves an exact state from a per-position speculative verify column instead of cutting the prefill (intake-2787#record, flashstates-designdoc.md claim 5 "SUPPORTED BY PRECEDENT": "the column of the last accepted draft", `MambaStateGather`). Our K-snapshot slots are that per-position layout restricted to the tail of a call.
