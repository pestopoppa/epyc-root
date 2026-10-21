# KV prefix fork: the radix lesson, vLLM copy-vs-share by path, and the junction-checkpoint lesson

**Task**: KPF-04 in [`handoffs/active/kv-prefix-fork-and-paged-attention.md`](../../handoffs/active/kv-prefix-fork-and-paged-attention.md).
**Status**: staging text for `wiki/kv-cache.md`. KPF-04 says the wiki compile happens at the first wiki sweep after KPF-18 closes, and wiki compilation waits for an operator-invoked `/wrap-up`, so this page holds the compiled content under `docs/reference/` until then. The sweep lifts it into the wiki and adds the KPF-18 result in the last section.
**Confidence**: every vLLM statement is **external** (read from vLLM source on disk at the commits named, one reader plus an independent second reader per wave, nothing run on our hardware). The radix history is verified from our own tree and the wiki.

## 1. The radix lesson (ours)

The orchestrator built a client-side radix router once and it never served a request.

- January 2026: `handoffs/archived/radix-attention.md` built `radix_cache.py` (about 480 lines) beside `PrefixRouter`, marked "VERIFIED 2026-01-09". Its Next Steps stopped at "Integration testing with live llama-server"; that never happened.
- 2026-08-20: the file was deleted as dead code (KV-0c, `wiki/kv-cache.md`). Its only importers were itself, and 20 green tests covered an unwired module.
- What survived is `PrefixRouter` in `epyc-orchestrator/src/inference/prefix_cache.py`. Slot pinning became opt-in on 2026-10-03 (UFH14-B4) because against v10 a pin can only lose: a busy pinned slot defers the task while other slots are free, and under `--kv-unified` idle slots are cleared anyway.

**The lesson.** A client-side prefix structure cannot share KV the server does not share. Reuse has to live where the cells live, in llama-server's slot/KV layer. The orchestrator makes reuse possible (byte-stable trunks, trunk-first ordering) and counts it (unique cells); it never models the cache. Every phase's done-when is a measurement on the live server, never green unit tests over an unwired path.

**The 2026-10-04 revival (KPF-27)** is the same lesson applied, not a reversal. The tree returned as an index of where prefixes are, never a cache model or slot allocator, under three rules: the server is the source of truth (each slot entry is bound to `/slots` `id_task` and dropped when the server disagrees); a client key is the WIRE text, not a canonicalized or client-tokenized one; and it is wired into paths every request already crosses, with a flag-off test proving nothing else changed. The January module failed on the third rule.

## 2. vLLM: is recurrent state copied or shared? By path

Source: `intake-2061#record` (vLLM PR #46384, partial prefix-cache hit for hybrid models; merge commit `481e481`; Stage-2 dive read from disk). Short answer from the dive: **PARTIAL, it depends on the path.** The question matters to us because our recurrent half cannot be shared by reference the way attention KV can (`llama_memory_recurrent::seq_cp` shares only the source's current tail cell), so the copy rows below are the vLLM analogue of our checkpoint restore (KPF-13), not of `seq_cp`.

| Path | Attention KV | Recurrent (Mamba) state | Mechanism and anchor |
|---|---|---|---|
| New request, block-aligned hit, no partial hit | shared by reference (refcount) | **shared by reference**, the hit block is the saved state | not copied by #46384; the model kernel reads the block (kernel side not in these PRs, NOT-FOUND-IN-SOURCE). `single_type_kv_cache_manager.py` L1527-L1530 |
| New request, **partial** hit (prefix ends inside a block) | whole-block page **copied** source to a private block | whole-block page **copied** (attention and mamba tensors alike) | `allocate_new_blocks` pops `_partial_hit_reqs`, takes a fresh block, `_apply_cow` replaces the request's block entry (L338-L348, L376-L396); the worker copies it before the forward pass (`gpu/model_runner.py` L841-L848, `worker/utils.py` L573-L577, `blocks[dst] = blocks[src]` on block-major pages) |
| Running request that owns an aligned Mamba block | owner keeps its block | the **cache entry moves to a copy**: owner stays on its block (the worker block table is append-only), `move_block_hashes` re-points the hash to a queued copy | same file, CoW-on-owner path; comment "Move the cache entry to cow_block" |
| Lifetime of source and destination blocks | n/a | both endpoints retained by refcount until the end of the `schedule()` call; deferred past the copy step only when `defer_block_free` | `scheduler.py` L1123-L1131 and L2198-L2207; `defer_block_free` is true only for a KV-consumer connector with more than one in-flight batch (L150-L152). `intake-2061#record` narrows the Stage-1 claim that every copy is fenced |
| EAGLE/MTP drafter | the drafter's attention KV is rebuilt by dropping one hash unit | the drafter has no mamba layers, so no drafter recurrent state exists to copy | coordinator L737-L743; `single_type` L527. #46384 has no MTP-specific recurrent or draft-state handling |

Three reading rules from the same dive, each of which corrects a casual summary:

1. `prefix_match_unit` is a **rename** of the existing `hash_block_size`, not a new concept (#46384 adds the `--prefix-match-unit` flag; the survey credited the flag to #45939, see `intake-2062#record`). The default is the GCD of the cacheable groups' block sizes, so a hybrid model whose attention and mamba blocks are equal gets **no** sub-block hit unless the flag is set explicitly.
2. "EAGLE drops one match unit instead of one block" is true only for non-Mamba groups. Mamba gets no margin, and the reconciled joint hit still falls to the Mamba grid (a third-party report in vLLM PR #52371, secondary: attention 48 becomes 44, Mamba holds 16/32/48, the joint hit is 32).
3. The merged rule registers **one** extra Mamba state per request, at the prompt tail. That serves only "shared prefix equals the producer's whole prompt"; for "shared system prompt plus private suffix" the tail state is over tokens nobody shares and the joint hit is zero. The fix is section 3.

The single benchmark in the PR body (second-request latency 0.0955 s versus 0.1337 s) is one run, self-reported, FP8 35B-A3B, no variance, and the first request got slower (0.305 versus 0.287 s). It is **not** a number we may cite as a performance claim.

## 3. The junction-checkpoint lesson (vLLM PR #53945)

Source: `intake-2072#record` (merged 2026-09-08, merge commit `263c4ff`, read in full from the diff and body). Related: `intake-2066#record` (the vLLM docs page, which documents the later flag name).

- **Defect.** With EAGLE/MTP, the attention group hits at a position it holds a key for, EAGLE drops one hash unit off that candidate, and the Mamba group holds state only on its own block grid, so nothing exists at the resulting position and the hit floors to the previous block boundary.
- **Mechanism.** The scheduler ends a prompt chunk exactly at `request.shared_prefix_boundary` (the junction a sibling was seen to stop at) instead of flooring it to the block grid, and `MambaManager._cache_partial_tail_block` additionally accepts a state publish at that junction. Under EAGLE the replay boundary and the tail checkpoint both move one unit down, so the stored state sits where the post-drop hit lands.
- **Gating.** One predicate, computed in `KVCacheManager` and read by both scheduler and manager: flag on, an EAGLE-annotated group, fine-grained partial hash hits, no multi-module MTP. The stated reason is that a stop the manager then refuses costs a forward pass and displaces the block-boundary stop. This is the same "one derivation of one position" rule our KPF-17.1 (n_tokens binding) enforces.
- **Limits.** The junction is **reactive**: a sibling must already have stopped there, so the first occurrence of a prefix still pays full prefill. The publish is bounded to the prompt (`num_computed_tokens < position <= num_prompt_tokens`) because during decode the target block is mutated in place; no decode-time checkpoint exists. It is opt-in and default off; the flag was named `--enable-mamba-fine-grained-prefix-cache` in the PR and is `--enable-mamba-shared-prefix-checkpoint` at vLLM `b272cff` (rename in #57382), so do not cite the PR's name as current.
- **Author-reported benefit** (a simulation that drives the real scheduler and cache manager, not wall-clock serving): 0 of 84 configurations reduce reuse; the saving is a constant block-size-minus-hash-unit tokens per request (for example 8,704 to 6,720 uncached prefill tokens at 57,600 shared plus 6,400 suffix, hash unit 64, block 2,048). Self-reported, AI assistance disclosed, not reproduced.
- **Do not cite it for** drafter state: the PR contains no drafter hidden-state restore or recompute (it says only that EAGLE drops one hash unit).

**What it means for the fork.** KPF-15's explicit junction (`checkpoint_at`) converges on the same shape, end the chunk at the junction and publish state there, and removes two vLLM limits: junction discovery is not reactive (the client names the junction) and there is no hash-unit drop. That makes it the later-upstream design in intent, not the merged #46384 design, and it is the comparison baseline for the KPF-18.1 trunk-then-suffix arms. Dense per-boundary snapshots are the wrong response because our per-slot checkpoints are large (about 150 MiB for a 27B); snapshots belong at branch points (see KPF-17.3 for the per-slot bound).

## 4. KPF-18 result (to be filled by the wiki sweep)

KPF-04 asks the compiled wiki text to include the KPF-18 result. KPF-18 was open when this page was written; the sweep adds one paragraph here from the closed KPF-18 record (equivalence versus fresh, the MTP parity arm, and the trunk-then-suffix arms) before lifting the page into `wiki/kv-cache.md`.
