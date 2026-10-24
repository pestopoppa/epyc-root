# KV prefix fork and paged attention: completed history through 2026-10-24

Historical ledger only; current work lives in [`../active/kv-prefix-fork-and-paged-attention.md`](../active/kv-prefix-fork-and-paged-attention.md).
Moved verbatim from the active handoff by the 2026-10-24 operator-invoked /wrap-up (workspace-f8). Line links inside point at the active file's pre-move numbering.

## GitNexus pass, 2026-10-04 (read-only; drafting session)

`gitnexus status` (epyc-root): up to date at db398a7. **llama.cpp index state:**
- `/mnt/raid0/llm/llama.cpp` is indexed at **v7 `6ad45fa` (2026-07-22): STALE**, and it is the frozen tree.
  Do not re-index it.
- `/mnt/raid0/llm/llama.cpp-experimental-fastload-ds41-20260925` is indexed at `00d118d`, which descends from v10
  `ffc1bac82` (+13 commits). It was used for the numbers below, for orientation only.
- Orchestrator: `/workspace/repos/epyc-orchestrator` is indexed at `f72d1d5` (2026-07-22): STALE. It predates
  `kv_pool_admission.py` and `prefix_history.py`.
- **Step for every phase: index the phase's own experimental worktree via
  `scripts/gitnexus-analyze.sh /mnt/raid0/llm/worktrees/kv-prefix-fork-<phase>`** and re-run the queries there.

| Symbol | Direction | Impacted | Risk | Direct dependants |
|---|---|---|---|---|
| `server_context_impl::update_slots` | upstream | 3 | LOW | `init` (one caller) |
| `update_slots` | downstream | 31 (25 processes) | **CRITICAL** | batch build, `pre_decode`, LoRA, embeddings, slot abort |
| `server_context_impl::pre_decode` | upstream | 0 | (LOW) | none resolved, although `update_slots` calls it |
| `get_available_slot` | upstream | 3 | LOW | `process_single_task` |
| `server_slot::copy_state_to` | upstream | 3 | LOW | `decode` ← `spec_exact_bonus` ← `post_decode` |
| `llama_state_seq_set_data_ext` | upstream | 9 | **HIGH** | server `load`, `common` `load_tgt`/`load_dft`, `llama_state_seq_set_data`, save-load-state tests |
| `llama_kv_cache::find_slot` | upstream | 5 | LOW | `prepare`, `state_read_meta` → `init_batch`, `state_read_sinfo`, `state_read` |
| `llama_memory_seq_cp` (public) | upstream | 7 | MEDIUM | `common_context_seq_cp`, speculative `build_tree_seq`, batched-bench, examples |
| `llama_memory_seq_rm` (public) | upstream | 26 | **HIGH** | common, speculative, `llama-kv-compress` `evict`, completion, tests |
| `llama_kv_cache::seq_cp` / `llama_memory_hybrid::seq_cp` / `llama_memory_recurrent::seq_cp` | upstream | 0 | (LOW) | none resolved |
| `PrefixRouter.get_slot_for_prompt` (orch, 2026-09-27 worktree index) | upstream | 3 | LOW | only `bench_cache_performance.py` |

**Reading it:**
- **The C++ callgraph under-resolves virtual dispatch.** The three `seq_cp` methods are reached through
  `llama_memory_i` and show 0 callers, while the public wrapper has 7. Python member calls are missed the same way
  (`CachingBackend` → `self._router` is absent). **A LOW from GitNexus on an interface method or a member-call
  path is not evidence of a small blast radius.** Supplement every query with `grep -rn` over the worktree.
- **P1 risk is HIGH.** The fork goes through `llama_state_seq_set_data_ext` (HIGH) and edits inside
  `update_slots`/`pre_decode`, whose single caller hides a CRITICAL downstream fan (every request's batch build).
  The upstream LOW measures callers, not the risk of editing `pre_decode`, a ~750-line function (L2984-3737). The owner acknowledges this before
  KPF-12/13 edit code.
- **P3**: `find_slot` also sits on the slot-restore path (`state_read_meta` → `state_read`). An allocator change
  must keep slot save/restore green (`tests/test-state-restore-fragmented.cpp`, `tools/server/tests/unit/test_slot_save.py`).


## P1 progress, 2026-10-04 (workspace-ec lane)

**Branch** `experimental/kv-prefix-fork-p1-20261004` (worktree `/mnt/raid0/llm/worktrees/kv-prefix-fork-p1`), base
`90c12df42` = `ak/champion/llama-cpp-ffc1bac82eec` tip resolved live (KVU-19a is **not** folded in it). Scratch:
`/mnt/raid0/llm/tmp/kpf-p1-20261004/` (PROGRESS.md, INTERFACE.md for P2, KPF02/03 records, smoke records).

### KPF-02 impact pass (index: sibling `fastload-ds41` @ `00d118d`; own-worktree index pending: two attempts did not complete (a parse-worker timeout, then an external stop during a peer CPU window); the coordinator will schedule the re-run; KPF-01 stays open until `gitnexus list` shows it)

| Symbol | Direction | Impacted | Risk | Direct dependants |
|---|---|---|---|---|
| `update_slots` | upstream | 3 | LOW | 1 |
| `pre_decode` | upstream | 0 | LOW | 0 |
| `get_available_slot` | upstream | 3 | LOW | 1 |
| `launch_slot_with_task` | upstream | 4 | LOW | 2 |
| `create_checkpoint` | upstream | 1 | LOW | 1 |
| `copy_state_to` | upstream | 3 | LOW | 1 |
| `llama_kv_cache::seq_cp` / `llama_memory_hybrid::seq_cp` / `llama_memory_recurrent::seq_cp` / `llama_memory_recurrent::state_read` | upstream | 0 | (LOW, virtual dispatch unresolved) | 0 |
| `llama_state_seq_set_data_ext` | upstream | 9 | **HIGH** | 5 |
| `common_speculative_set_state` | upstream | 1 | LOW | 1 |
| `prompt_clear` | upstream | 14 | **HIGH** | 5 |
| `llama_memory_seq_cp` (public) | upstream | 7 | MEDIUM | 6 |
| `common_context_seq_cp` | upstream | 3 | LOW | 1 |
| `llama_memory_i` (interface we add two defaulted virtuals to) | upstream | 12 | MEDIUM | 8 |

Flags: **HIGH** on `llama_state_seq_set_data_ext` (the fork restores dst's recurrent/drafter state through it) and
`prompt_clear` (a purge of a fork source). Acknowledged by the owner: experimental branch; mitigated by
calling both only through their existing, unchanged signatures, and by KPF-17's purge/restore tests. Grep
supplement (`kpf02/KPF02.md`): 8 classes derive from `llama_memory_i` plus `tests/test-batch-alloc.cpp` `mock_memory`
— the new virtuals are defaulted (not pure), so none of them changes.

### What was built (KPF-11..17)
Commits on `fork` (`experimental/kv-prefix-fork-p1-20261004`):

- `eb59174a1`: KPF-12/16 API. `llama_memory_seq_cp_ext(..., LLAMA_MEMORY_SEQ_CP_FLAGS_ATTN_ONLY)`:
  - a zero-copy share of the attention cells only;
  - never aliases the recurrent tail;
  - same-stream only, with a capability probe.

  Also `llama_memory_get_cell_stats` (pool size/used/shared plus per-seq private/shared), `common_context_seq_cp_attn`,
  `common_prompt_checkpoint::pinned`, and `--slot-fork-min-tokens N` (0 = off). The `llama_memory_i` virtuals are
  defaulted.
- `993b73765`: KPF-11/13/14/15/16, server.
  - The fork is taken in `launch_slot_with_task`, before `[TAG_IDLE_SLOT_CLEAR]`.
  - Modes are probed at load: `kv` for pure attention, `checkpoint` for hybrid/recurrent/SWA.
  - The source is any slot, busy or idle. Never a WAIT_OTHER child, a different LoRA set, mtmd, or a
    context-shifted/compressed/restored slot.
  - dst becomes "dst processed task[0,p) itself", so `pre_decode` takes `n_past = p` unchanged.
  - `get_available_slot` skips a `--cache-ram` load that the fork beats.
  - `checkpoint_at` creates pinned junction checkpoints; the end-of-prompt one is created in `post_decode`.
  - The `slot_fork` request opt-out.
  - Telemetry in `timings`, `/slots` and `/metrics`.
- `8279261a5`: P2 interface for workspace-89 (answers in `INTERFACE.md` §6): `content_epoch`, the `prefix_hash` ladder,
  `id_slot`/`id_task` in OAI timings, `/props.slot_fork`, and `checkpoint_at` `{"message": k}` (chat endpoints: rendered
  prefix, verified byte- then token-prefix).
- `a17ebe094` and `857d7ec1f`: KPF-17 tests (`tests/test-kv-seq-share.cpp`, `tools/server/tests/unit/test_slot_fork.py`).
- 19a/19b shared-trunk FlashAttention cases are prepared, not applied (KVU-19a is not in the champion):
  `/mnt/raid0/llm/tmp/kpf-p1-20261004/kpf17-19a/kpf17-shared-trunk-fa-unified.patch`. It applies to
  `fork/experimental/fa-maskskip-batched-20261004` (`git apply --check` OK).
- KPF-18 runner, not run: `/mnt/raid0/llm/tmp/kpf-p1-20261004/kpf18/` (`kpf18_gate.py`, `run_kpf18.sh`, `RUNBOOK.md`).
  It needs about 12 h 45 min of GPU time in 4 windows; the argv comes from `logs/server_launches/8083.json`.

### Results
CPU only, under `region-lock` (q1 after the coordinator's 2026-10-04 single-quadrant rule). Records are in
`/mnt/raid0/llm/tmp/kpf-p1-20261004/smoke-*/`.

- **test-kv-seq-share passes on 4 memory types:**
  - generated qwen35 GDN hybrid;
  - Qwen3.5-0.8B Q8_0 hybrid, rollback ring 0 and 8;
  - Qwen2.5-0.5B attention;
  - gemma-3-1b SWA.

  On those models (gemma-3 gets top-1 checks only, since one token ≠ one cell under SWA), fork vs fresh suffix,
  fork vs full-state copy, and source continuation with/without the fork are all **bit-identical** (max|d| = 0).
  Cell counts are exact: `used` does not grow at the fork, `find_slot` never reuses a shared cell, and a purge
  frees exactly the source's private cells. The fork's serialized state is byte-identical across the source purge.
- **Regressions green:** `test-recurrent-state-rollback` (qwen35), `test-save-load-state`,
  `test-state-restore-fragmented`.
- **Off = champion:** at `--slot-fork-min-tokens 0` vs the champion CPU store build `cpu-20260925-90c12df42`,
  7/7 generations (tokens + top-5 probs) are byte-identical on both models, with identical `timings` and `/slots`
  key sets.
- **Fork on, trunk-first 1575-token prompts, 3 children:**
  - every child forks 1560 tokens (hybrid kinds: `end` from the trunk slot, then `checkpoint` from the previous
    child's inherited junction) and prefills 9-15 tokens instead of 1575;
  - with `--no-cache-idle-slots` the pool holds 1772 unique cells vs 6452 logical (the trunk is held once);
  - pool invariant `used = Σ private + shared` holds;
  - zero "failed to find a memory slot".
- **Equivalence, matched instrument (same binary, fork-off arm at `--slot-fork-min-tokens 0`, same sequence):**
  - `cache-idle`: fork-on children = fork-off children = fresh, 3/3 on both models.
  - `no-cache-idle`: one child in three diverges from fresh at token 57 (hybrid) or 45 (attention). The
    **fork-off** arm diverges at the same token, and fresh-vs-fresh across arms diverges too.
  - So this is the unified-pool layout noise floor (resident neighbours change the FA partition), not the fork.
    KPF-18 item 1 measures it at production scale.
- **Server pytest:** Qwen2.5-0.5B 8 passed, 2 skipped (kv mode). Qwen3.5-0.8B 10 passed, including the P2 cases (epoch, hash ladder, ids in timings, `/props`, and message-index
  `checkpoint_at` on the Qwen3.5 template). Final run `smoke-20261004T073455Z`, all rc 0, q1 bench lock, `-t 8`.
- **Open finding for KPF-18 item 1 (not dismissed).** In the `-t 8` run, one hybrid child in cache-idle mode (child 2,
  forked from child 1's junction checkpoint) matched fresh for 55 of 64 greedy tokens and then diverged, while
  fresh-vs-fresh across arms was identical in that run. So it is fork-attributable at that thread count.
  - Likely mechanism, isolated in `test-kv-seq-share`: after the source purge, the fork's new tokens land in freed
    cells **before** its suffix cells, so the attention sum runs in a different order than a contiguous fresh
    prefill. On this hybrid that moved logits by up to 0.29 with top-1 unchanged.
  - The serialized state is byte-identical and every suffix/continuation check before the purge is bit-exact, so this
    is cell order, not wrong data.
  - KPF-18 item 1 must report fork-vs-fresh against the fresh-vs-fresh **and** fragmented-layout control. If it exceeds
    that control at production length, the fix is order-preserving placement for fork children (a P3 /
    `--kv-affine-chunk` concern), not the share itself.

