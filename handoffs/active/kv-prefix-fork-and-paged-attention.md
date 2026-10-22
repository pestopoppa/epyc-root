# KV prefix fork and paged attention: cross-slot prefix sharing, cache-aware dispatch, per-sequence KV views

**Status**: ACTIVE. Operator-approved program (2026-10-04: *"all sound like crucial features to fold into our
champion. We shouldn't be afraid of large efforts."*). P0 and P1 are dispatchable now. P2's prefix index (KPF-27
branch A, flag OFF) landed on orchestrator main 2026-10-04; its gate half (branch B) waits for workspace-ec's ack.
**Created**: 2026-10-04 (drafted for ak-ds41-main from the KV-serving survey)
**Priority**: HIGH. Four subagents with one 60k-token trunk prefill it four times today and hold four copies
(~180k cells, ~6 GB of the :8083 pool). Fan-out child TTFT is minutes when it could be seconds.
**Categories**: inference_serving, kv_cache, llama_cpp_experimental, orchestration
**Parent index**: [routing-and-optimization-index.md](routing-and-optimization-index.md) (row RTG-58, applied by the
owning session)
**Scratch**: `/mnt/raid0/llm/tmp/kv-prefix-fork/` · worktrees: `/mnt/raid0/llm/worktrees/kv-prefix-fork-*`
**Owners**: **workspace-ec** executes every phase: P1 server/KV side, P2 orchestrator side (as stack owner), P3, P4
and P5. **ak-ds41-main** keeps this handoff and its index row.
**Owner change, 2026-10-20 (operator):** P1 is reassigned to the 2026-10-20 operator session. workspace-ec has had no
bus heartbeat since at least 2026-10-08, and the P1 code (KPF-11..16, `experimental/kv-prefix-fork-p1-20261004` @
`857d7ec1f`) had sat ungated for 16 days. Re-cut onto the live champion tip in progress:
`experimental/kv-prefix-fork-p1r-20261020`, worktree `/mnt/raid0/llm/worktrees/kv-prefix-fork-p1r-20261020`, notes in
`/mnt/raid0/llm/tmp/kv-prefix-fork/p1r-20261020/`. The CPU correctness half of KPF-18 runs first, on the frontdoor
35B-A3B on one quarter; the GPU and timing halves wait for windows. P2-P5 stay with workspace-ec unless reassigned.

**Canonical P1 branch, 2026-10-20:** `experimental/kv-prefix-fork-p1r2-20261020` @ `14d603f3a` (on the new champion `dd3d9721c`; the six fork commits applied with no conflicts, plus `test_pinned_junction_slot_file_roundtrip`; pushed to fork). Verified: test-kv-seq-share and save-load/state-restore tests pass, test_slot_fork.py 12/12 (Qwen3.5-0.8B), test_slot_save.py 15/15, fork-off ≡ champion 7/7 on two models (`/mnt/raid0/llm/tmp/kv-prefix-fork/p1r2-20261020/RECUT2.md`, `smoke-latest/`). Known limitation: a pinned junction saved to an upstream-format slot file restores unpinned (no pin flag in the SCKP block); a format extension is an operator decision. `experimental/kv-prefix-fork-p1r-20261020` @ `a1f0c8cf9` stays as the binary of tonight's GPU window (`kernels/builds/gpu-20261020-a1f0c8cf9`).
**Ownership addendum, 2026-10-20 (research intake `intake-hybrid-prefix-cache-20261020`):** the 2026-10-20 operator session owns P1 (KPF-11..19, KPF-17a) and KPF-21/KPF-25, reassigned from workspace-ec; P2 (KPF-22..24, KPF-26, KPF-27) and P3-P5 otherwise stay with workspace-ec unless reassigned. New rows KPF-13.1, KPF-17.1-17.4, KPF-18.1-18.3, KPF-19.1, KPF-26.1 and KPF-DOC-1 come from that intake (hybrid prefix caching in vLLM/SGLang/llama.cpp; the entries and findings are in `research/intake_index.yaml`, not restated here).
**Depends on**: RTG-57 [`kv-unified-stack-rollout.md`](kv-unified-stack-rollout.md) (KVU-19a/19b and the
prefill budget), RTG-27 [`prompt-construction-determinism.md`](prompt-construction-determinism.md) (byte-stable
prompts, load-bearing for P2), INF-65 [`autokernel-champion-aggregate.md`](autokernel-champion-aggregate.md) (the
ONE champion and the v11 candidate gate)
**Related**: INF-05 [`attention-matching-kv-compaction.md`](attention-matching-kv-compaction.md) KV-1/2/3/6 (the
orchestrator prefix-cache rows), [`agentic-serving-harness-fixes.md`](agentic-serving-harness-fixes.md) UFH14-B4
(`id_slot` pinning made opt-in), [`vidya-belief-substrate-program.md`](vidya-belief-substrate-program.md) (VB-KVU-*)

## Why this exists

Survey [`artifacts/gpu-block-27b-20261004/analysis/kv-serving-survey-REPORT.md`](../../artifacts/gpu-block-27b-20261004/analysis/kv-serving-survey-REPORT.md) (durable copy of
`/mnt/raid0/llm/tmp/kv-serving-survey-20261004/REPORT.md`)
(§0, §4) ranks five levers for concurrent long-context serving on :8083 (Qwen3.8-27B Q8_0 hybrid GDN + full
attention, DFlash2 n-max 7, `-np 4 -c 393216 --kv-unified`). This program carries **Recs 2-5**:

| Phase | Survey rec | Fixes (survey §3 legend) |
|---|---|---|
| P1 cross-slot prefix fork, server side | Rec 2 (server) | (c) duplicate prefix KV, (d) hybrid prefix reuse, (e) VRAM |
| P2 cache-aware dispatch, orchestrator side | Rec 2 (orchestrator) | (c), (e); relieves (a)/(b) |
| P3 sequence-affine KV cell allocation | Rec 3 (allocator half) | (a) for generated tokens |
| P4 upstream #29510 `kv_rows` port, A/B vs KVU-19b | Rec 4 | (a) |
| P5 cascade / shared-trunk attention | Rec 5 | (a) with sharing |

**Not in scope here, owned by RTG-57 and cross-referenced only:**
- **Rec 1, the decode-aware prefill budget**: workspace-ec is building it now (worktree
  `/mnt/raid0/llm/llama.cpp-experimental-prefill-budget-20261004`, branch `experimental/prefill-budget-20261004`).
  It gets a KVU row in RTG-57; this handoff only tests against it (KPF-18).
- **KVU-19a** (masked-block skip, done) and **KVU-19b** (per-row skip, open). P3 depends on 19b, P4 is an A/B arm
  against 19b, P5 reuses their block-liveness scan.
- **Context only, not a task here:** workspace-ec is preparing a :8083 stack-change package with
  `-b 512 -ub 512` + `--no-cache-idle-slots` (root cause:
  [`artifacts/gpu-block-27b-20261004/analysis/kvu16b-rootcause-REPORT.md`](../../artifacts/gpu-block-27b-20261004/analysis/kvu16b-rootcause-REPORT.md)
  §4 fix 1). Once live, it is the production shape every gate here runs at. `--no-cache-idle-slots` keeps idle
  trunks resident, which gives P1 more fork sources and makes P2's unique-cell gate matter more.
  Measured 2026-10-04 (ak-ds41-main GPU slot, [`artifacts/gpu-slot-ak-20261004/`](../../artifacts/gpu-slot-ak-20261004/),
  fixed decoding predicate): skip OFF `-b 512` vs `-b 2048` gives 3.5–4.2× decode while a neighbour prefills, −3.1 GiB
  KFD peak, and −26% solo shallow prefill; skip ON (19a+19b incl. commit 2) with `-b 512` gives 14× summed decode
  during the last prefill, with all 4 requests decoding at 8–11 tok/s.

## Start here

1. **KPF-01**: index a P1 experimental worktree with GitNexus (wrapper only), then run the KPF-02 impact pass.
2. **KPF-03**: file the belief-kernel wiring (VB-KVU-PF) before the first measurement record exists.
3. **KPF-11 → KPF-18**: build P1 on a fresh worktree from the current champion tip and run its gate.
4. In parallel with P1: **KPF-25** (byte-stable trunks) and **KPF-21** (trunk-first ordering). Both pay off with
   the existing `--cache-ram` copy restore even before the fork lands.
5. **KPF-30** (live-block fraction) can run as soon as KVU-19b's build exists. It needs no P1.
6. P4 waits on the v11 FA-path audit ([`artifacts/v11-fa-path-audit-20261004/REPORT.md`](../../artifacts/v11-fa-path-audit-20261004/REPORT.md), complete
   2026-10-04; actionables V11-FA-1..4 in RTG-57) and the v11 rebase. P5 waits on P1 and a rocprof profile.

## Standing rules for every phase

- **Kernel workflow** (CLAUDE.md *Experimental Kernel Workflow*): `/mnt/raid0/llm/llama.cpp` @ `ffc1bac82`
  (production-consolidated-v10) is READ-ONLY reference. Never build, modify, re-index or commit to it. All work
  happens on `experimental/kv-prefix-fork-*` branches in worktrees under
  `/mnt/raid0/llm/worktrees/kv-prefix-fork-<phase>`. Branch from the **current champion tip, resolved live**
  (`ak/champion/llama-cpp-ffc1bac82eec`, at drafting 90c12df42, which sits on v10 `ffc1bac82`), never from a
  pinned sha or bare production mid-cycle. Fold back through the champion owner (KVU-19a's route: `FOLD.md` plus a
  trial merge onto the champion tip). Production arrives only via the kernel-promotion skill.
- **ONE champion, one binary.** Every feature dispatches inside the one champion binary, keyed on argv, request
  fields, GGUF metadata or batch shape. **No env-only gates.** An env var may exist only as a diagnostic kill
  switch. The A/B control is an argv value in the same binary (e.g. `--slot-fork-min-tokens 0`).
- **Measurement** (MEASUREMENT.md, `agents/shared/MEASUREMENT_POLICY.md`): pair every speed number with a
  correctness check at production prompt length. Use the matched instrument: same binary, argv-off vs argv-on
  arms, alternating ABA windows, coordinated GPU windows only (never during another session's GPU window,
  INC-20261003-subagent-gpu-tests-in-peer-window). Prove HIP residency (`verify_ggml_linkage.sh`, VRAM sampled
  DURING the run). Two-sample persistence before acting on a delta.
- **Belief kernel**: every gate's native records project under **VB-KVU-PF** (KPF-03). Wire the write side before
  the first record.
- **GitNexus before editing** (CLAUDE.md): `gitnexus context` and `gitnexus impact <sym> --direction upstream` on
  each phase's key symbols; report blast radius and risk; **stop and warn on HIGH or CRITICAL**. Re-index only via
  `scripts/gitnexus-analyze.sh <worktree>`, never bare `gitnexus analyze`, and never on the frozen tree.
- **Scratch**: everything under the declared roots above. A store build in `kernels/builds/` is load-bearing and
  not scratch.

## Lessons: the orchestrator already had a radix router once

- **January 2026**: [`handoffs/archived/radix-attention.md`](../archived/radix-attention.md) built a Python radix
  router (`radix_cache.py`, 482 lines) next to `PrefixRouter`, marked "VERIFIED 2026-01-09" on
  Qwen2.5-Coder-0.5B. Its Next Steps stopped at *"Integration testing with live llama-server"*. That integration
  never happened.
- **2026-08-20**: `radix_cache.py` was deleted as dead code (KV-0c, `wiki/kv-cache.md`, compiled update
  2026-08-23, ~L498-504). Its only importers were itself; 20 green tests covered an unwired module.
- **What survived**: `PrefixRouter` (`epyc-orchestrator/src/inference/prefix_cache.py`). It keys on a 256-char
  SHA-256 of the canonicalized prompt and pins `id_slot`. UFH14-B4 (2026-10-03) made pinning **opt-in**
  (`ORCHESTRATOR_PREFIX_ROUTER_PIN_SLOTS=1`; `_pin_slots_enabled`, prefix_cache.py ~L381-402). Against v10, a pin
  can only lose: every root-LM prompt of a role maps to one slot, a busy pinned slot DEFERS the task while other
  slots are free, and under `--kv-unified` idle slots are cleared anyway.
- **The lesson, binding on this program**: a client-side prefix structure cannot share KV the server does not
  share. Prefix reuse has to live where the cells live, in llama-server's slot/KV layer (P1). The orchestrator's
  job is to make reuse *possible* (byte-stable trunks, trunk-first ordering) and to *count* it (unique cells),
  never to model the cache itself (P2). Every phase's done-when is a measurement on the live server, never green
  unit tests over an unwired path.
- The wiki sweep should compile this lesson into `wiki/kv-cache.md` when P1's gate closes (KPF-04).
- **2026-10-04 revival (KPF-27).** The radix tree came back in a different role: an index that records where
  prefixes are and lets the gate act on it (credit, LPM, trunk hold, fork plan), never a cache model and
  never a slot allocator. Three rules made it safe to revive: (1) the server is the source of truth — every
  slot entry is bound to `/slots` `id_task` and dropped the moment the server disagrees; (2) a client key is
  the WIRE text, not a canonicalized or client-tokenized one; (3) it is wired into paths every request
  already crosses (the KV pool gate and the serving record), with a flag-off test that proves nothing else
  changed — the January module failed on exactly that last point.

## What already exists in our tree (read-only line refs, each tagged by tree)

Tree tags used below, every number verified with `git show <rev>:<path>` on 2026-10-20 (script `/mnt/raid0/llm/tmp/zero-inference-20261020/KPF-DOC-1/map.py`):
**v10** = `ffc1bac82` (frozen production); **champ** = `dd3d9721c` (champion tip; `e33229348` was the tip before the #26004/#30574 ports, so a ref quoted against it is ~+229 lines off from `server-context.cpp` L2450 onward); **p1r** = `a1f0c8cf9` (KPF-11..17 on `e33229348`); **p1r2** = `14d603f3a` (the same KPF work rebased on `dd3d9721c`, plus the slot-file pin test). A bare `L123` below is v10; cite a line only with its tree tag. Format: `[v10 · champ · p1r · p1r2]`.

- `llama_kv_cache::seq_cp` (`src/llama-kv-cache.cpp` [450-491 · 451-492 · 526-567 · 526-567]): in unified mode (`s0 == s1`) it adds the dst
  seq bit to every src cell in `[p0, p1)`. Zero copy. One O(n_cells) metadata pass, ~393k cells.
- `llama_memory_recurrent::seq_cp` (`src/llama-memory-recurrent.cpp` 246-281 in all four trees) **ignores p0/p1**. It makes dst share
  src's *current* tail cell. `llama_memory_hybrid::seq_cp` (`src/llama-memory-hybrid.cpp` 152-155 in all four trees; p1r/p1r2 add the attention-only share, KPF-12, as a separate entry point and leave this one unchanged) calls both
  halves, so a hybrid `seq_cp(src, dst, 0, p)` gives dst the correct attention prefix but src's state at its
  current end, not at p. **Never use hybrid `seq_cp` for a fork.**
- Context checkpoints (`create_checkpoint`, `tools/server/server-context.cpp` [2365-2412 · 2396-2443 · 2802 · 2802]; p1r/p1r2 add the `bool pinned = false` parameter) save the
  non-rollbackable state with `LLAMA_STATE_SEQ_FLAGS_PARTIAL_ONLY`: the target's recurrent half
  (`llama-memory-hybrid.cpp` [191-203 · 191-203 · 203-215 · 203-215]), the drafter's SWA cache (`llama-kv-cache-iswa.cpp` [259-273 · 259-273 · 273-287 · 273-287]), and the
  DFlash2 speculative state (`common_speculative_get_state` → `cur.data_spec`). The placement policy is in
  `pre_decode` ([2984-3733 · 3334-4117 · 3666-4466 · 3895-4705], called from `update_slots` starting [2856 · 3194 · 3526 · 3755]) placement ~[3562-3726 · 3933-4110 · 4263-4459 · 4502-4698]: user-message starts (#24176), and
  `4 + n_ubatch` and 4 tokens before prompt end. The spacing exemption `is_last_user_message || near_prompt_end` is in v10 (L3718), in the champion before the KPF work (`e33229348` L3863, `dd3d9721c` L4102) and in all KPF trees: it is NOT a KPF change. The KPF departures in this block are the `ckpt_pinned ||` term added to that same condition and `create_checkpoint(..., ckpt_pinned)` (`ckpt_pinned` defined at p1r L4433 / p1r2 L4672, spacing term p1r L4449 / p1r2 L4688, call p1r L4458 / p1r2 L4697), see "KPF-branch departures" below.
  Restore is at ~[3451-3480 · 3812-3841 · 4146-4175 · 4375-4404], on the slot's own checkpoints only (champ: the block grew by ~10 lines with the #26004 port).
- `server_slot::copy_state_to` ([735-757 · 756-778 · 798 · 798]; p1r/p1r2 body changed for forks) does `seq_rm` + full `seq_cp` on `ctx_tgt` and `ctx_dft`. It is used only
  for `n>1` child tasks, and only from `SLOT_STATE_DONE_PROMPT`.
- `get_available_slot` ([1601-1705 · 1632-1736 · 2013 · 2013]; the p1r/p1r2 body is KPF-14's fork-source path): it computes LCP similarity only over slots that are **not processing**, then
  falls back to LRU, then does a `--cache-ram` save/load **by copy**.
- Idle-slot purge ([2469-2484 · 2713-2728 · 2968-2983 · 3181-3196], `[TAG_IDLE_SLOT_CLEAR]`): with `cache_idle_slots` on and unified KV, each new task
  launch saves every idle slot to `--cache-ram` and `prompt_clear()`s it. **This runs after
  `launch_slot_with_task`**, so a fork whose source is an idle slot must be taken at launch, before this loop
  (KPF-14).
- `--cache-reuse` is force-disabled for recurrent memory ([1286-1301 · 1307-1322 · 1361-1376 · 1361-1376]). **Corrected 2026-10-21 (KPF-63):** this premise is wrong for the champion. `llama_memory_hybrid::get_can_shift()` returns true (`llama-memory-hybrid.cpp:133`), so the server does not disable `--cache-reuse` on hybrids; no production role sets the flag; the engine defect is CH-21 (`handoffs/active/autokernel-champion-aggregate.md`; design `/mnt/raid0/llm/tmp/cacheclip-port-20261021/DESIGN.md`). Non-prefix reuse on hybrids is under test in KPF-60, not ruled out.
- `find_slot` (`src/llama-kv-cache.cpp` [901-1075 · 902-1076 · 977-1151 · 977-1151]) is first-fit from `head` per ubatch (P3).
- Hybrid ubatch split (`src/llama-memory-hybrid.cpp:80-89` in all four trees): `split_equal(n_ubatch, !unified, n_rs_seq + 1)`. The
  pure-KV path at `llama-kv-cache.cpp` [716 · 717 · 792 · 792] uses `split_simple`. **Survey correction to verify in KPF-40:** survey §2.4
  finding 3 says #29510 cannot slice DFlash2 verify ubatches because unified KV uses `split_simple`. Our hybrid
  model goes through `split_equal`, and #29510's `get_n_kv_slices()` accepts `equal_seqs() && n_seqs == n_seqs_unq`
  (`pr29510.diff` L1080-1091). So verify ubatches (4 seqs × 8 rows) may slice after all. If so, P4 is worth more
  than the survey estimated.
- CPU paged-attention scaffolding from v5 (`src/llama-kv-block.h`, `GGML_OP_FLASH_ATTN_EXT_PAGED`,
  `tests/test-kv-block.cpp`): forward-ported in `0e485a91b`, reverted in `a4e2b4f86`; none of the three files exists in v10, champ, p1r or p1r2 (checked), so this is history, not tree content. It is reusable block
  accounting for P3/P4, with no GPU kernel.

### KPF-branch departures from the champion (p1r on `e33229348`, p1r2 on `dd3d9721c`)

These exist only on the KPF branches. A promotion carries them inside the FULL candidate build (fresh production + every feature, validated as a whole) and never as a cherry-pick:

- `common_prompt_checkpoint::pinned` (`common/common.h:1130` in p1r and p1r2; absent in v10 and champ) and the `checkpoint_at` request parameter (`tools/server/server-task.h:72`, KPF-15), with the eviction loops in `create_checkpoint` never dropping a pinned checkpoint.
- The `ckpt_pinned` override of the checkpoint spacing rule in `pre_decode`: a requested junction is checkpointed regardless of spacing or placement policy (`ckpt_pinned ||` heads the `do_checkpoint` spacing condition: p1r L4433-4458, p1r2 L4672-4697).
- Correction to the earlier wording: the last-user exemption `is_last_user_message || near_prompt_end` is NOT a departure. It is in v10 and in the champion, and the KPF branches only prepend `ckpt_pinned ||` to it.
- Everything else (cross-slot fork in `get_available_slot`/`copy_state_to`, attention-only zero-copy seq share in `llama-kv-cache.cpp`/`llama-memory-hybrid.cpp`, fork telemetry, `/props` fork capability, prefix-hash ladder, content epoch) is also KPF-only: commits `528b76f99`..`a1f0c8cf9` on p1r and `efd92d46a`..`14d603f3a` on p1r2.

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

## Tasks

### P0: setup (workspace-ec; KPF-03 prepared by any session, applied by the owning session)

- [ ] **KPF-01: create the P1 worktree and index it.** `git -C /mnt/raid0/llm/llama.cpp worktree add
  /mnt/raid0/llm/worktrees/kv-prefix-fork-p1 -b experimental/kv-prefix-fork-p1-<date> <champion tip>`, with the
  champion tip resolved live. Then `scripts/gitnexus-analyze.sh /mnt/raid0/llm/worktrees/kv-prefix-fork-p1`. Done
  when `gitnexus list` shows the worktree at its HEAD.
  - *(2026-10-20, operator session.)* Re-cut worktrees exist (`kv-prefix-fork-p1r-20261020` @ `a1f0c8cf9` on `e33229348`; `kv-prefix-fork-p1r2-20261020` @ `14d603f3a` on `dd3d9721c`). The own-worktree GitNexus index is refused by gitnexus-guard unless all four CPU quarters are held with role build, so this box stays open until an index run inside a full-host build window.
- [x] **KPF-02: GitNexus impact pass on the P1 worktree.** ✅ 2026-10-04 Run `context` + `impact --direction upstream` on
  `update_slots`, `pre_decode`, `get_available_slot`, `launch_slot_with_task`, `create_checkpoint`, `copy_state_to`,
  `llama_kv_cache::seq_cp`, `llama_memory_hybrid::seq_cp`, `llama_memory_recurrent::seq_cp`,
  `llama_memory_recurrent::state_read`, `llama_state_seq_set_data_ext`, `common_speculative_set_state`, and
  `prompt_clear`. Add grep for the interface paths. Append the table to this handoff and flag every HIGH/CRITICAL
  before KPF-12.
- [ ] **KPF-03: belief-kernel wiring, VB-KVU-PF.** Prepare (a) a source row in `scripts/vidya/adapters/README.md`:
  *KV prefix-fork / cache-aware dispatch / affine-allocation / kv_rows / cascade measurements (KPF-18, -26, -33,
  -42, -53 native records: per-run JSON with binary sha, argv, arm, prompt-set hash, equivalence verdicts, TTFT,
  prefill tokens, unique cells, decode tok/s)*, status "not yet produced; wire before KPF-18"; and (b) a task
  **VB-KVU-PF** in `vidya-belief-substrate-program.md` (write side plus projection; one ladder; no new grading
  rule). The owning session applies both. Done when both are on main and KPF-18's runner emits the record shape.
- [ ] **KPF-04: compile the radix lesson (above), the vLLM copy-vs-share table by path (PR #46384) and the junction-checkpoint lesson (PR #53945) into `wiki/kv-cache.md`** at the first wiki sweep after KPF-18
  closes, including the KPF-18 result.
  - *(2026-10-21, workspace-f8)* Staging page written: [`docs/reference/kv-prefix-fork-radix-lesson-and-vllm-copy-vs-share.md`](../../docs/reference/kv-prefix-fork-radix-lesson-and-vllm-copy-vs-share.md) (radix lesson, vLLM copy-vs-share by path from `intake-2061#record`, junction-checkpoint lesson from `intake-2072#record`; cite-check clean). Still open: lift into `wiki/kv-cache.md` and add the KPF-18 result (page section 4) at the first sweep after KPF-18 closes.
- [x] **KPF-DOC-1 — tag line references by tree and record the KPF-branch departures from the champion.** In "What already exists in our tree" and "Key files" tag each line reference with its tree (v10 `ffc1bac82`, champion `e33229348`, or p1r `a1f0c8cf9`) so a reader cannot cite one against another (create_checkpoint is L2365 in v10 but L2396 in the champion, pre_decode L2984 vs L3105). Record that the last-user spacing exemption (is_last_user_message || near_prompt_end) and the pinned checkpoint field are KPF-branch departures from the champion, so any promotion carries them inside the FULL candidate build and never as a cherry-pick. Zero compute. ✅ 2026-10-20

### P1: cross-slot prefix fork, server side (workspace-ec) — effort M-L, ~2-3 weeks including the gate

Target: a new task whose prompt shares a long prefix with **any** slot, busy or idle, starts from a zero-copy fork
of that slot's attention cells plus a checkpoint-restored recurrent and drafter state at the fork position. It
prefills only the suffix.

- [x] **KPF-11: cross-slot fork-source selection.** ✅ 2026-10-04 Add `find_fork_source(task)` to `server_context_impl`, called
  from `get_available_slot` (L1601) / `launch_slot_with_task`:
  - For every slot ≠ dst, **busy ones included**, compute `lcp = slot.prompt.tokens.get_common_prefix(task.tokens)`.
  - Fork position `p` = the largest checkpoint in that slot's `prompt.checkpoints` with `n_tokens ≤ lcp`, or the
    slot's exact end if the slot is idle with `n_tokens == lcp`.
  - Require `p < task.tokens.size()`, so at least one token is processed (`[TAG_PROMPT_LOGITS]`).
  - Pick the largest `p` across slots. Ties: idle source first, then most recent. Compare against the dst slot's
    own LCP/checkpoint and the `--cache-ram` best hit, and take the largest reuse.
  - Threshold: new argv `--slot-fork-min-tokens N` (0 = off, the A/B control). Default chosen in KPF-18.
- [x] **KPF-12: attention-only zero-copy share.** ✅ 2026-10-04 Add an explicit attention-only copy so the recurrent half is never
  aliased: `llama_memory_seq_cp_ext(mem, src, dst, p0, p1, flags)` with an `ATTN_ONLY` flag. Touches
  `include/llama.h`, `src/llama-memory.h` (`llama_memory_i`), `src/llama-memory-hybrid.cpp:152`, `src/llama-context.cpp`
  (API) and `common/common.cpp` (`common_context_seq_cp`). Sequence: `seq_rm(dst, -1, -1)`, then
  `seq_cp_ext(src, dst, 0, p, ATTN_ONLY)`.
  - Rejected alternative: hybrid `seq_cp` followed by a checkpoint load into dst. Recurrent `seq_cp` makes dst
    share src's tail cell, so the following `state_read` could write src's live state unless it copies on write.
    That is an aliasing window with no test that would catch it.
- [x] **KPF-13: recurrent and drafter state from the checkpoint.** ✅ 2026-10-04 Into dst: `ckpt.load_tgt(ctx_tgt, dst.id,
  PARTIAL_ONLY)`, `ckpt.load_dft(ctx_dft, dst.id, PARTIAL_ONLY)` (the drafter's SWA window travels in the
  checkpoint, `llama-kv-cache-iswa.cpp:259-273`) and `common_speculative_set_state(spec, dst.id, ckpt.data_spec)`.
  Then set `dst.prompt.tokens = task.tokens[0:p]`, clone the source checkpoints with `n_tokens ≤ p` into
  `dst.prompt.checkpoints`, set `n_past = p`, and prefill from p. Positions are unchanged, so no shift.
  - Verify in code and in a test that `llama_memory_recurrent::state_read` for dst allocates or uses **dst's own**
    rows: 4 slots × 8 rows with the rollback ring, `n_rs_seq`. It must never write a cell src still references.
- [ ] **KPF-13.1 — drafter restore vs re-prefill A/B at the fork point.** On the P1 build with a plain-KV MTP drafter and with DFlash2, fork a slot twice from the same junction: (restore) drafter state restored from the checkpoint as KPF-13 does, (recompute) drafter re-prefilled over the last N tokens before the fork position. Assert identical first-draft tokens under greedy and equal draft acceptance over the first 64 generated tokens. Record what the restore does not carry: MTP pending_h (common_speculative_impl_draft_mtp has no get_state/set_state, so common_speculative_set_state is a no-op for it) and the DFlash2 per-seq selector RNG (re-seeded or continued after a restore, so draft sampling is non-reproducible across a fork; pin the seed in tests; the target verifies, so output is unaffected). The A/B is an independent control and rests on no other engine's behaviour. Trigger-gated follow-up (prose, no checkbox): port the shape of upstream #30141 only if the A/B shows an acceptance drop after fork restore. Controls: manifest = prompt set + binary sha256; baseline = a no-fork prompt-cache hit with the same batch partition as the arm (corrected 2026-10-22: never a cold unforked twin, which takes a different batch shape); raw draft tokens and acceptance retained; held-out prompts for N; all attempts counted; rule = token identity and acceptance within the same-shape control's run-to-run spread. CPU, correctness class.
  - *(2026-10-22, workspace-f8.)* **Fork cleared.** The v1 reduced run failed A and B at suffix 1 against cold twins. Repro `/mnt/raid0/llm/tmp/kpf13-repro/run/verdict.json` (predeclared rules sha `189686b5…`, no request forks): a no-fork cache hit with a 1-token remainder == arm A1 and a prefill with no 1-token ubatch == arm B1, bit-for-bit (tokens and gap0); the cold control R0 == twin W1. Cause: a 1-token ubatch takes a different CPU reduction path (llamafile_sgemm refuses n<2, iqk tiles differ at nrc_y==1, MoE top-k amplifies it), not fork state. v1's #30141 trigger is withdrawn (measured against the wrong control). v11 property to carry: **fork ≡ prompt-cache hit with the same remainder**.
  - *(2026-10-22, v2 result, rules v2 sha `e0e6e528…`.)* `/mnt/raid0/llm/tmp/kpf13-reduced-v2/run/verdict.json`: tokens clean, every attempt `tokens_ok` against the same-shape control (A 23/24 runs pass, B 18/24); all 7 failures are acceptance-only and off by 1-4 draft tokens, because v2 took the acceptance interval from a single control run (zero width, e.g. draft_n in [83,83]). Not a restore defect; verdict not yet decision-grade.
  - [ ] **KPF-13.1 rules v3** — derive the acceptance interval from the drafter's run-to-run spread on the same-shape control (>= 3 control repeats per cell), predeclare it with its sha, re-judge the stored v2 cells offline, then decide KPF-13.1a. (filed 2026-10-22, f8)
  - [ ] **KPF-13.1a — decision input: skip `load_dft` for plain drafters at the fork.** On a plain (non-SWA) drafter `do_slot_fork` shares [0, p) via `seq_cp_attn(ctx_dft)` and then `load_dft` replaces that share with a private copy of identical content (one drafter-KV copy per fork, no output effect; job 27 2026-10-21). Option: when `slot_fork_dft_plain(src, p)`, keep the share and skip `load_dft` (what `--slot-fork-dft-full` already does); SWA drafters (DFlash2, KPF-19.1a) keep the load. Decide with KPF-13.1's restore-vs-recompute result.
- [x] **KPF-14: launch ordering and seq-bit safety.** ✅ 2026-10-04
  - Take the fork at launch, before the `[TAG_IDLE_SLOT_CLEAR]` loop (L2469-2484), so an idle source is not
    cleared first.
  - Confirm `prompt_clear()` / `seq_rm(src, -1, -1)` on a source removes only its own seq bit: a cell is freed only
    when its last bit goes, and `used` stays right.
  - Cover `cache_idle_slots` on AND off, because production flips to `--no-cache-idle-slots` with the in-progress
    package.
- [x] **KPF-15: explicit junction checkpoint, request field `checkpoint_at`.** ✅ 2026-10-04
  - Format: an array of token positions; `-1` means end of prompt. Parse it in `tools/server/server-task.cpp`.
  - In `pre_decode` (~L3640-3720), end a prompt chunk exactly at each requested position and create a checkpoint
    there, regardless of `checkpoint_min_step`.
  - Mark such checkpoints `pinned`, so the erase loops in `create_checkpoint` (L2370-2394) never evict them, and
    carry them through `prompt_save`/`prompt_load` (`server_prompt_cache`, `server-task.h`).
  - This is vLLM's `--enable-mamba-shared-prefix-checkpoint` and SGLang's branch-point caching, on demand.
  - Snapshots stay sparse: one costs ~150 MiB, about 4.4k tokens of KV (survey §1.3).
- [x] **KPF-16: fork telemetry.** ✅ 2026-10-04
  - Response `timings`: `n_fork_tokens`, `fork_src_slot`, `fork_src_kind` (`checkpoint` | `end`).
  - One INFO log line per fork.
  - `/slots`: per-slot private vs shared cell counts. `/props` or `/metrics`: pool **unique** cells used. P2's gate
    reads this.
  - Serving records already pass `timings` through (KVU-17), so these fields reach `serving_calls.jsonl` with no
    orchestrator change.
- [ ] **KPF-17: tests.**
  - New `tests/test-kv-seq-share.cpp`: cell seq bits under `seq_cp`/`seq_rm`/`seq_keep` with shared cells; the
    `used` count; `find_slot` never hands out a shared cell.
  - Extend `tests/test-save-load-state.cpp` (`test_seq_cp_device` exists): a PARTIAL_ONLY restore into a different
    seq id while src keeps decoding.
  - Server pytest `tools/server/tests/unit/test_slot_fork.py`. If no tiny hybrid GDN GGUF exists for CI, run that
    case in the GPU window on the 27B.
  - Extend KVU-19a's `test_flash_attn_ext_unified` cases and the 64-case exactness harness with **multi-seq
    (shared) cells**, so 19a/19b stay exact over shared trunks.
- [ ] **KPF-17a: shared-trunk cases for KVU-19a/19b's `test_flash_attn_ext_unified`, applied at the 19a/19b fold.**
  KPF-17's fourth bullet cannot land on the P1 branch, because the test lives on the unfolded 19a/19b line. The
  patch is prepared: `/mnt/raid0/llm/tmp/kpf-p1-20261004/kpf17-19a/kpf17-shared-trunk-fa-unified.patch`, which adds
  an `n_shared` trunk owned by every sequence plus 25 cases, and passes `git apply --check` on
  `fork/experimental/fa-maskskip-batched-20261004`. Apply it with the fold, then run `-o FLASH_ATTN_EXT` on ROCm0 and
  CPU and the 64-case harness. KPF-17 stays open until it is applied (P1 branch: `test-kv-seq-share` + `test_slot_fork.py`
  are done).
  - *(2026-10-04 ~08:00Z, workspace-ec wrap-up.)* **The 19a/19b fold landed WITHOUT this patch**: the champion is now
    `1bceceb05` (KVU-19a + KVU-19b commit 1; `kv-unified-stack-rollout.md` KVU-19b-fold-c1). The patch does **not**
    apply there: `git apply --check` in the clean `1bceceb05` worktree fails at `tests/test-backend-ops.cpp:8584`,
    because it was cut against the commit-2 branch. Re-cut it on `1bceceb05` (or on the KVU-19b-rework-c2 v2 branch
    `54df2c030` if commit 2 folds next), apply it as a test-only commit on the next champion fold (KVU-16h-fold or
    CPU-FA-VKQ-1), and run `-o FLASH_ATTN_EXT` on ROCm0 and CPU plus the harness there.
  - *(2026-10-20, operator session.)* CPU half re-cut and run on the champion tip `e33229348`: branch `experimental/kpf17a-shared-trunk-fa-20261020` @ `ada3fa92e` (worktree `/mnt/raid0/llm/worktrees/kpf17a-20261020`), `-o FLASH_ATTN_EXT` on CPU passes 5207/5207 including the 25 shared-trunk cases (`/mnt/raid0/llm/tmp/kpf17a-20261020/test.log`). The ROCm0 half waits for the GPU window; this box stays open until it is recorded.
  - *(2026-10-20 GPU window.)* ROCm0 `-o FLASH_ATTN_EXT` on `ada3fa92e`: 2978/2978 pass (`/mnt/raid0/llm/tmp/overnight-20261020/log/w1_kpf17a_rocm0.log`). Still open: the KVU-19a 64-case exactness harness on ROCm0 and CPU.
- [x] **KPF-17.1 — checkpoint-integrity cases for the fork (deterministic conformance, CPU first).** On the P1 build (`experimental/kv-prefix-fork-p1r-20261020`) add cases that each FAIL when their guard is removed: (1) every pinned checkpoint satisfies ckpt.n_tokens == its requested checkpoint_at position with DFlash2 and MTP on and off, including a chunk end that coincides with a draft-verification batch (no draft scratch or rollback row is ever captured); a fork restored from it, a prompt_save/prompt_load round trip and a clone-to-fork all keep n_tokens, and first-token logits equal a cold prefill at that position within the fresh-vs-fresh floor; read first that create_checkpoint runs after the forward of the chunk's last position and that chunk end and publish position come from one checkpoint_at entry; (2) offset oracle under concurrency: np>=2 with n_batch set so slot chunks end at arbitrary offsets; for EVERY checkpoint created, including the "end" kind taken from an idle source, restore into a fresh seq, decode one token and require logits equal to a cold prefill to n_tokens within the floor, and assert the ckpt.pos_max + 1 != p guard in find_fork_source silently skipped none; (3) abort-then-retry: abort a trunk-first request at several offsets mid-prefill, send a sibling at once, require its output equal to a fresh run within the floor and find_fork_source never selecting the aborted slot's cells beyond its decoded n_past (read first how a slot cancelled mid-prefill is treated); (4) key check with negative control: P1=S+a, P2=S+b with a[0]!=b[0], run P1,P2,P1: P2 must not restore P1's junction beyond S, and a forced stale restore must diverge from a cold prefill by a large margin. Deterministic infrastructure, so no holdout: the conformance fixtures are the four cases, the mutation case is the guard removed, provenance = binary sha256 + branch sha in the record. Acceptance: all four pass on CPU (frontdoor Qwen3.6-35B-A3B hybrid and one tiny hybrid), each fails with its guard removed, records under VB-KVU-PF.
  - *(2026-10-20.)* Cases for 17.1–17.4 and 19.1 implemented on `experimental/kv-prefix-fork-p1r2-20261020` (435ee2d8b, e3fe30e59, 1f453d022: `--slot-pinned-checkpoints`, `--slot-fork-dft-full`, LLAMA_KPF_MUTATE mutation hooks), queued as CPU jobs 10–40 in /mnt/raid0/llm/tmp/cpu-queue-f8 (results under /mnt/raid0/llm/tmp/kv-prefix-fork/p1r2-20261020/queue-results/).
  - [x] *(2026-10-20, fix pass, workspace-f8 subagent)* ✅ 2026-10-21 — `f3a3bb4b1`, `1f9b2a8bf`, `1fd7e2e12` on p1r2 (rebuilt `build-cpu`, llama-server sha256 defc5a094fcd…, newer than HEAD). Queue jobs 22/23 failures were oracle/setup bugs, not fork defects: batch-boundary and KV-cell-placement float floor (CPU logits move 0.32–0.47 under any evaluation-order change, top-1 unchanged), idle-slot purge on launch with a unified KV pool, an abort-then-retry case whose non-streaming request never aborted, SWA checkpoint sizes. SWA restore re-serializes byte-exact. The kv-mode pos_max guard is unreachable at launch; now proven with test-only fault injection `LLAMA_KPF_MUTATE=abort_keeps_tail` (with `no_posmax_guard` added it fails as intended).
  - [x] **KPF-17.1a — re-check gate for the relaxed oracles**: ✅ 2026-10-21 (closed by the KPF-17.1c pass; see the note under 17.1c) — queue job 24 (re-runs 23 + a non-SWA floor + the new abort matrix) and jobs 20/21/30/40 on the tiny hybrid and the 35B. Pass requires job 21's mutants still FAIL under the new near-tie rule (`same_as_fresh` accepts one flip to the fresh runner-up within 0.5 nats, then stops comparing); if any mutant now passes, tighten the rule to the measured floor instead of a fixed 0.5 nats.
    - *(2026-10-21)* Gate FAILED in job 21: mutant `fork_clobber_src` not detected by 17.2(3). Root cause: the case never forked — its wait loop read a stale `/slots` `next_token.n_decoded` (48, from the previous task), returned while the source was still prefilling below the junction, and the child prefilled from scratch (`n_fork_tokens 0`); job 20's honest 17.2(3) pass was vacuous for the same reason. Not the near-tie rule. Fix `11dbef15e` (wait on generated-token count, require a real fork from slot 0, check source cells/length directly, A/A control instead of a fixed 0.5 nats). With the fork really running, the clobber aborts the server on a hybrid cache (`common_context_seq_rm` GGML_ABORT) and drops source cells on SWA/attention.
    - [x] **KPF-17.1b — no vacuous fork cases**: ✅ 2026-10-21 (verified by `28-kpf17-oracle-recheck-nproc`, which supersedes parked job 25: honest PASS on both models, `fork_clobber_src` and `fork_skip_ckpt_load` FAIL on both) — audit every fork test for stale `/slots` waits (e.g. `test_fork_from_busy_source` uses `n_decoded > 0`), and make every case whose purpose is the fork fail when `n_fork_tokens == 0`; then run parked job 25 (honest PASS ×2 models, `fork_clobber_src` FAIL ×2, `fork_skip_ckpt_load` FAIL) after 06:30Z.
      - *(2026-10-21)* Audit done in `a7af56dff` (Python only; build.ok still valid): new `assert_forked` guard (fails on n_fork_tokens 0, below the case minimum, or wrong source slot) in every fork-purpose case. Vacuous before: `test_fork_from_busy_source` (stale n_decoded wait), 172 current-step (all siblings forked from an idle slot; n_f 0 accepted), 172 same-iteration-as-erase (`assert any(...) or True`), 171 abort-then-retry, 171 key-check negative control, 174 SWA pinned-junction (no fork asserted), P2 epoch ladder. Verification = parked jobs 25 + 26 (honest PASS on tiny hybrid, gemma SWA, Qwen2.5 kv-mode; 9 mutant arms FAIL), released after W2. Not yet run.
      - *(2026-10-21, morning re-check, workspace-f8)* Re-check jobs 25/26/40 (evidence `epyc-inference-research` `artifacts/f8-evidence-20261021/kpf17/queue-results/`): `fork_clobber_src` is now DETECTED on hyb and swa (the 17.1b guard works). Still failing: 17.2(3) decoding-source honest on swa (job 25) and mtp (job 40); honest same-iteration on hyb and swa and honest p2 on swa (job 26); mutants `fork_skip_ckpt_load` on hyb (job 25) and `dft_partial_noop` flag-off (job 40) NOT detected.
    - [x] **KPF-17.1c — diagnose the morning re-check failures** (workspace-f8): ✅ 2026-10-21 — for each failing honest case decide oracle/setup defect vs fork defect (check for a vacuous wait or an oracle that cannot see the mutation, as in 17.1b), fix, and rerun jobs 25/26/40; gate 17.1a only closes when every honest case passes and every mutant is detected.
      - *(2026-10-21, workspace-f8 subagent)* All six failures were test defects, none a fork defect (two of them were the subagent's own earlier mistakes). (1) 17.2(3) swa `base_tok == base_cells`: iSWA counts base+SWA cells, now compared with the unforked run. (2) `fork_skip_ckpt_load` on the hybrid undetected: the one-sided 0.5-nat near-tie rule accepted an index-0 flip (fresh margin 0.43). `same_as_fresh` is now two-sided on top-2 logprobs (greedy-token drift < `DRIFT_FLOOR` 0.45, flip distance < `TIE_MARGIN` 0.6). Floors were measured with the gates off: honest drift ≤ 0.082 hyb / 0.215 swa, honest flip distance ≤ 0.125, mutants 1.85–2.03 or inf. (3) same-iteration clone check ran after `fresh()`, whose launch purges idle slot 1. (4) p2-swa epoch bump is correct behaviour: upstream SWA `pre_decode` restores a checkpoint and truncates whenever pos_next ≤ n_swa; the rule now follows `cache_n`. (5) 35B+MTP "source finished": the source hit EOS at 35 tokens while the fork was taken busy; new server telemetry `fork_src_busy` (`dd5bb0d3b`) replaces the thread-alive proxy. (6) `dft_partial_noop` is output-neutral on the fork path (see KPF-19.1). Commits `dd5bb0d3b` (server) + `80a09c6ad` (tests) on p1r2, binary sha256 `1442c95d…` in `build.ok`. Verified locally on q2 at 24 threads: honest 13/13 on Qwen3.5-0.8B and gemma-3-1b, 3/3 on Qwen2.5-0.5B; 8 mutant arms FAIL. Queue: job 27 (35B+MTP rerun of job 40) PASS 7/7; `28-kpf17-oracle-recheck-nproc` (jobs 25+26 matrix at the queue thread count; not the same job as `28-kpf-19-1-17-3`) PASS 18/18 (honest 13/13 hyb, 13/13 swa, 3/3 kv; 15 mutant arms detected; honest drift ≤ 0.157, flip distance ≤ 0.050 at 192 threads, evidence `queue-results/28-kpf17-oracle-recheck-nproc/oracle-drift.txt`).
      - *(2026-10-21, 17.1a gate result)* Every honest case passes and every job-21 mutant is detected under the tightened (measured-floor) oracle. Tiny hybrid + gemma + Qwen2.5 at 192 threads: `28-kpf17-oracle-recheck-nproc` 18/18. 35B frontdoor suite: job 29 (rerun of job 30 on `80a09c6ad`) 10/10. 35B+MTP: job 27 (rerun of job 40) 7/7. The two job-21 `ckpt_ntokens_skew` arms not in job 28 (171 ntokens, 171 offset-oracle) were run locally on q2 and FAIL as required.
  - *(2026-10-21, backlog audit tick.)* ✅ Verified against results before ticking: acceptance (all four cases pass on CPU on the frontdoor Qwen3.6-35B-A3B hybrid and a tiny hybrid; each fails with its guard removed) is met by `queue-results/29-kpf17-35b-suite-recheck` (rc 0; 17.1 cases 171-ntokens/offset-oracle/abort-then-retry/key-check PASS, `fork_no_lcp` and `pin_cap_off` mutants DETECTED) and `28-kpf17-oracle-recheck-nproc` (18/18 on tiny hybrid + gemma + Qwen2.5, 15 mutant arms detected), results under `/mnt/raid0/llm/tmp/kv-prefix-fork/p1r2-20261020/queue-results/`; all of 17.1a/b/c are ticked above.
- [x] **KPF-17.2 — checkpoint-lifecycle cases for the fork (deterministic conformance, CPU first).** (1) Source diverges below a junction: when a source slot rewinds below its own pinned junction its checkpoint is correctly erased (the slot no longer holds attention KV up to the junction), so test the real invariant instead: a NEW request with the same trunk still forks correctly from a child slot that holds the pinned clone, bit-exact against a fresh run within the floor, with cache_idle_slots on and off; (2) fork launched in the same update_slots iteration in which the source's create_checkpoint erase loop or prompt_clear runs: dst holds its own cloned checkpoint and the restore succeeds bit-exactly; (3) checkpoint_at inside an unverified draft window of a decoding source is clamped or rejected to the last accepted position, and a fork taken while the source has k pending draft tokens leaks no recurrent state (the source's continuation is byte-identical with and without the fork); (4) a fork from a checkpoint created in the current batch step is refused or deferred one step. Each case fails with its guard removed; provenance = binary sha256 + branch sha. Acceptance: all four pass on CPU and are listed in the P1 branch test inventory. ✅ 2026-10-22
  - *(2026-10-22, workspace-f8, closed on prior.)* The planned re-run (`/mnt/raid0/llm/tmp/f8-fillers-20261022/kpf172/`) was not needed: the four cases already pass on CPU in `/mnt/raid0/llm/tmp/kv-prefix-fork/p1r2-20261020/queue-results/`: job 20 (tiny hybrid) 172-diverge-below-junction, same-iteration, decoding-source, current-step all OK; jobs 29/30 (35B frontdoor) f-172 diverge/same-iteration/current-step OK; job 27 (35B+MTP) m-172-decoding-source-mtp OK with `fork_clobber_src` and `fork_skip_ckpt_load` mutants DETECTED. The SWA failures (job 25 `172-decoding-source-swa`, job 23) belong to KPF-17.4, not this task.
- [x] **KPF-17.3 — bound pinned-checkpoint lifetime per slot.** Pinned checkpoints are exempt from the erase loops and the cap of 8 is per request (server-context.cpp:2848 on `experimental/kv-prefix-fork-p1r-20261020`), so pinned checkpoints accumulate across requests on a slot. Add a per-slot cap on TOTAL pinned checkpoints (argv, default derived from ~150 MiB per 27B checkpoint and --ctx-checkpoints) that drops the OLDEST pinned checkpoint when exceeded, and release a slot's pinned checkpoints only when its prompt is cleared (prompt_clear) or evicted to the prompt cache, never on ordinary slot release (an idle slot's pinned junction is a fork source). Test: more sequential checkpoint_at requests than the cap never exceed it, the newest junction survives and the oldest is dropped first, a forked child's inherited clones count toward its own cap, and checkpoint memory stays bounded over a long request series. Deterministic conformance on CPU; mutation case = cap disabled must fail the bound; cap=0 behaviour must equal today's per-request bound.
  - *(2026-10-21, workspace-f8)* Already implemented (`435ee2d8b` cap, `e3fe30e59` tests); queue jobs 20 and 30 passed on the tiny hybrid and the 35B and `pin_cap_off` was detected. Job 28 re-runs it on `experimental/kpf-19-1-17-3-20261021`; tick when its 173-* steps pass.
  - *(2026-10-21, backlog audit tick.)* ✅ Condition in the note above met: job 28 (`experimental/kpf-19-1-17-3-20261021` @ `82c16126f`, `/mnt/raid0/llm/tmp/kv-prefix-fork/kpf-19-1-17-3/queue-results/28-kpf-19-1-17-3/steps.txt`) STEP 173-pinned-cap OK, 173-cap-zero OK, 173-mut-pin_cap_off DETECTED; also job 29 f-173-pinned-cap OK and `pin_cap_off` DETECTED on the 35B. (Job 28's overall rc=1 is from its six `strings-*` static greps, which looked for the symbols in `libllama-server-impl.so` where they are not compiled in; the mutation hooks demonstrably engage because the mutants are detected. Harness check defect, not a 17.3 failure.)
- [ ] **KPF-17.4 — SWA checkpoint range correctness ([TAG_CHECKPOINTS_FIX_POS_MIN]).** RE-TARGETED 2026-10-21 (backlog audit §1): the Gemma-class target is retired from production; run on the Qwen3.8-27B target + the `Qwen3.8-27B-DFlash2-Q8_0.gguf` SWA drafter (`sliding_window` 2048 on all 5 layers), TOGETHER with KPF-19.1a in ONE server load (same build, same argv; sweep S2). On the SWA drafter cache, save a checkpoint, restore it and compare next-token and logits against a no-checkpoint run; record each checkpoint's recorded pos_min against the actual cache pos_min (v10, the champion and the fork all carry the open TODO that the saved data covers [pos_min, pos_max], which is not true for SWA). Gate any pinned-junction use on SWA caches on the result. Deterministic conformance on CPU with a mutation case (use the recorded range instead of the real window must fail); take any upstream follow-up only through CH-18, never as a patch.
  - *(2026-10-20)* Correctness result: SWA checkpoint data always covers its own resume window and the recorded pos_min is never above the real one (iSWA `seq_pos_min` counts masked-but-unpruned cells, llama-kv-cache-iswa.cpp:156; `state_write` skips them, llama-kv-cache.cpp:2209), so a pinned-junction fork on an SWA cache cannot produce wrong output. Conservative choice kept: range not re-recorded (recording the real range would make upstream's `pos_min < pos_next - n_swa` gate reject every junction checkpoint).
  - *(2026-10-21 sync from `progress/2026-10/2026-10-20-workspace-f8.md`.)* The 23:00-23:35Z queue re-run reported real KPF-17.4 failures: SWA checkpoint recorded range != restored range, continuation max|d| 0.33, fork-vs-fresh divergence, and the `no_posmax_guard` mutation undetected (a diagnosis subagent was dispatched). The fix pass recorded under KPF-17.1 classed the jobs 22/23 failures as oracle/setup bugs (batch-boundary float floor with top-1 unchanged, idle-slot purge, an abort case that never aborted, SWA checkpoint sizes), not fork defects, and proved the pos_max guard with `LLAMA_KPF_MUTATE=abort_keeps_tail`. So the code-reading result above stands, but no clean re-run of the SWA range comparison is recorded yet; KPF-17.1a (job 24) is the re-check.
  - [ ] **KPF-17.4a — measure the long-context SWA fork loss** (found by code reading): once context exceeds the SWA cache (~n_swa × n_seq + n_ubatch) recorded and real pos_min coincide, the gate rejects junction checkpoints and the fork falls back to full reprocessing (correct output, lost speed). RE-TARGETED 2026-10-21: measure on the Qwen3.8-27B + DFlash2 SWA drafter (n_swa 2048) at a context above that bound, in the same load as KPF-19.1a (the "Gemma-class" target is retired); the fix is upstream TAG_CHECKPOINTS_FIX_POS_MIN via CH-18.
- [ ] **KPF-18: P1 gate (GPU window, :8083 production argv on the fork build; workspace-ec).** The matched
  instrument is the same binary with `--slot-fork-min-tokens 0` vs on, in alternating windows. Done when ALL hold:
  1. **Equivalence vs fresh.** Prompt set ≥ 32 trunk/suffix pairs (trunk 8k-80k, suffix 0.5-8k), greedy, DFlash2
     on and off. First measure the **control noise floor**: fresh vs fresh at the same batch composition, because
     unified-KV outputs already differ at np2/np4 at a fixed seed (RTG-57 evidence). Fork vs fresh must be no worse
     than that control on first-token top-1 agreement, first-token logits max-abs/KLD, and identical-greedy-prefix
     length over 256 tokens. Report the counts, not a pass word.
  2. **Bit-exactness where it is owed.** Fork from a checkpoint vs the source's own continuation from that
     checkpoint is bit-identical (same state, same suffix).
  3. **Source invariance.** The source slot's own continuation is byte-identical with and without a fork taken
     from it mid-decode.
  4. **Mid-prefill checkpoints (the SGLang #39342 class).** Fork from checkpoints created while the source was
     mid-prefill inside **mixed prefill+decode ubatches**, on a build that carries workspace-ec's prefill budget, at
     `-b 512 -ub 512`. Equivalence holds as in (1).
  5. **Seq-bit safety.** With `cache_idle_slots` on and off, purging or reusing the source never changes dst's
     continuation, and pool `used` returns to the expected unique count after all tasks finish. Zero "failed to
     find a memory slot".
  6. **Off = champion.** With `--slot-fork-min-tokens 0`, outputs are bit-identical to the champion tip on the
     same prompts.
  7. **Speed.** For a 4-child fan-out over a 60k trunk: total server prefill tokens ≈ T + Σ suffix (from `timings`),
     child TTFT, peak unique cells (expect −(N−1)·T ≈ −180k), and decode tok/s of all slots during the fan-out.
     Two windows. The expected gain is the survey's §4 Rec 2 estimate, not a promise.

  Records project under VB-KVU-PF. Then write `FOLD.md`, trial-merge onto the champion tip, and hand to the
  champion owner (KVU-19a's route). Production default-on rides the next promotion ratification (kernel-promotion).
  - *(2026-10-20 GPU window f8-w1, workspace-f8.)* MI210, :8083 gate shape, fork build `kernels/builds/gpu-20261020-a1f0c8cf9`, fixed runner (KPF-18.0a); records `/mnt/raid0/llm/tmp/overnight-20261020/kpf18-run/records/`. Item 6 off ≡ champion 8/8 bit-identical. Item 5 seq-bit safety: every invariant 44/44 (cis on and off), forks 8/8. Item 1 (groups 0,2,4,7; DFlash2 on and off): fork taken at n_fork_tokens == T 16/16; vs fresh first-token top-1 16/16 vs control 15/16; greedy-prefix median 174 vs control 53 (DFlash2 on), 46 vs 32 (off); logit max-abs 0.17 within the fresh-vs-fresh spread 0.09–0.17 — within the control floor. Item 2: bit-identical 0/32, token-identical 10/32 — INCONCLUSIVE: on the MI210 two fresh runs match all 256 tokens only 2/16 (non-batch-invariant GPU kernels; same item on CPU gave 16/16 tokens), and the runner has no same-slot A/A control for this item. Not run: items 3, 4 (needs the prefill-budget trial build), 7.
- [x] **KPF-18.0a — fix the inherited KPF-18 runner bugs.** ✅ 2026-10-20 (A) items 2-5 bound the trunk length late, so every group used the last group's T; (B) item 1 sent the fork child after the fresh controls, so it forked their full-prompt checkpoint instead of the trunk; (C) the runner wrote `<out>/logs/*.linkage.txt` before creating `<out>/logs`. Fixed runner: `/mnt/raid0/llm/tmp/kpf-p1-20261004/kpf18/kpf18_gate.py` (sha256 `d46336488013d120…`, original kept as `kpf18_gate.py.orig-20261004`); GPU-mode behaviour otherwise unchanged (CPU adaptations sit behind `--cpu`).
- [x] **KPF-18.0c — the 10-04 open divergence finding is benign.** ✅ 2026-10-20 Hybrid child 2's departure from fresh (token 55-57) reproduces, but the fork child is bit-identical (incl. top-5 probs) to the same slot continuing a trunk it prefilled itself without a fork, and a fresh run on a deliberately fragmented pool diverges at the same token: prefill chunk boundaries and KV cell layout, not fork state. Evidence: `/mnt/raid0/llm/tmp/kv-prefix-fork/p1r-20261020/CPU-GATE-REPORT.md`.
- [ ] **KPF-18.0b — finish the KPF-18 CPU subset with the fixed runner.** CPU subset so far on the frontdoor Qwen3.6-35B-A3B (MTP n-max 4, one quarter): item 6 off ≡ champion 8/8, item 3 source invariance 2/2, item 4 mid-prefill junction with the prefill budget 2/2 — exact; items 1, 2 and 5 ran on the buggy runner and must be re-run; item 7 (16k fan-out prefill) not measured. Re-run 1/2/5 and run 7 (~2.5 h of one quarter), and read the 2026-10-20 GPU window records (`/mnt/raid0/llm/tmp/overnight-20261020/kpf18-run/`, window id `f8-w1-20261020`; items 6, 1, 2, 5 ran with the fixed runner) in the same pass.
  - [x] **KPF-18.0b(item 7, CPU)** ✅ 2026-10-21: fan-out of a 16k trunk + 4 children, 2 windows per arm, Qwen3.6-35B-A3B-MTP Q8_0 on one quarter. Fork off: 51,712 fan-out prefill tokens, child TTFT 183–512 s, aggregate decode 1.5 tok/s. Fork on (min-tokens 1024): 2,560 prefill tokens, 3 checkpoint forks × 16,384 tokens per window, child TTFT 38–47 s, aggregate decode 23–24 tok/s; logical KV cells 68,604 vs unique 19,452. n=1 per cell, OBSERVATION grade, host shared with concurrent correctness jobs; equivalence not measured in item 7. Records `/mnt/raid0/llm/tmp/kv-prefix-fork/p1r-20261020/kpf18cpu/rerun-20261021/item7/`.
  - [x] **KPF-18.0b.1 — fix the item-7 record**: the CPU runner stamps `dflash2: true` although the shape is draft-mtp, and the unique-cells metric differs between arms (`/slots` sum vs `kv_cells_used`). ✅ 2026-10-21: `dflash2` is now derived from the launched argv (`--spec-type draft-dflash` and a DFlash2 `-md`; new fields `spec_type_from_argv`, `draft_model_from_argv`, `speculative_requested`), and item-7 unique cells use `llamacpp:kv_cells_used` for both arms (`None` with an explicit method if the series is absent, never a substitute). CPU runner `/mnt/raid0/llm/tmp/kv-prefix-fork/p1r-20261020/kpf18cpu/kpf18_gate.py` (backup `kpf18_gate.py.pre-kpf180b1-20261021`); the same patch is in the GPU runner `/mnt/raid0/llm/tmp/kpf-p1-20261004/kpf18/kpf18_gate.py` (backup `kpf18_gate.py.pre-kpf180b1-20261021`). py_compile and item-7 `--cpu --dry-run` pass; no live run yet.
  - [ ] **KPF-18.0b.2** — confirm fork_off exposes kv_cells_used on the CPU fork build at the next item-7 run
- [ ] **KPF-18.0d — finish the KPF-18 GPU half.** Add an item-2 A/A control arm to the runner (the source slot's own continuation from the same checkpoint, run twice in the same batch composition) and judge item 2 against it; run items 3 and 7 and item 4 (build the prefill-budget trial merge first, per the runbook) in a scheduled MI210 window with q3 (host threads 184-191) free. (derived 2026-10-20 from the f8-w1 records)
  - [x] **KPF-18.0d(item 3, groups 0–4) — source invariance on the MI210** ✅ 2026-10-20 (window f8-w1c, 23:15–23:41Z, paired by agreement under the peer's gpu-quiet; fork build `gpu-20261020-a1f0c8cf9`; T = 8k–48k, S = 4k, n = 5). First-token distributions fork vs no-fork identical in 5/5 (max |Δp| 0, KL 0); full 256-token greedy match 3/5 (min prefix 43). The A/A control (no-fork vs no-fork repeat, same server) matches 4/5 tokens, 3/5 bit-identical, min prefix also 43. Within that floor: no sign the fork perturbs its source, but n = 5 cannot separate fork effect from GPU batch non-invariance. Groups 5–7 (60k–80k) not run (window). Record `/mnt/raid0/llm/tmp/overnight-20261020/kpf18-run-w1c/records/kpf18-20261020T231530Z-1.json`; grade: OBSERVATION (n = 1 per cell).
  - [x] **KPF-18.0d(item 7, GPU) — four-way fan-out speed on the MI210** ✅ 2026-10-21 (T4, done 14:55Z, rc 0, CANDIDATE grade, A/B/A/B; fork build `gpu-20261020-a1f0c8cf9`; argv `/mnt/raid0/llm/tmp/overnight-20261020/argv.8083-gate.txt`). Total fan-out TTFT: fork_off A1 1312.9 s, A2 1404.0 s; fork_on B1 169.3 s, B2 140.0 s (about 8.5x). Prefill tokens 254,512 -> 74,512, exactly the shared expectation; unique cells 75,532; aggregate decode 3.40/3.32 -> 26.5/32.1 tok/s. All checks OK. Records `/mnt/raid0/llm/tmp/overnight-20261020/kpf18-run-c/records/` and `item7_summary.json`. Equivalence is not measured in item 7 (items 1/3 carry it).
  - [ ] **KPF-18.0d(item 3, rest)** — groups 5–7 plus more repeats per group, so fork-vs-no-fork divergence can be compared with the A/A control rate (the A/A control already diverges at token 43 in 1/5).
    - *(2026-10-22, workspace-f8.)* launcher armed 2026-10-22, FILLERS row kpf18-item3-v2-sameshape; rule in /mnt/raid0/llm/tmp/f8-launchers-20261022/kpf18-item3-v2-sameshape/PREDECLARATION.md. Not run yet, nothing ticked.
  - [ ] **KPF-18.0d(item 3, D2 repeats)**
    - 2026-10-21 (observation grade): item-3 repeats read from the records (fork-vs-no-fork `source_fork_vs_nofork`, A/A control `source_nofork_vs_repeat`; tokens-identical / n; min greedy prefix of 256):

      | record | fork tok-identical | fork min prefix | A/A tok-identical | A/A min prefix |
      |---|---|---|---|---|
      | w1c `20261020T231530Z-1` (groups 0-4) | 3/5 | 43 | 4/5 | 43 |
      | g1 `20261021T094738Z-1` | 2/2 | 256 | 2/2 | 256 |
      | g1 `20261021T101637Z-1` | 1/1 | 256 | 1/1 | 256 |
      | g1 `20261021T104608Z-1` | 4/5 | 161 | 5/5 | 256 |
      | g1 `20261021T165524Z-1` (groups 5-7; 2026-10-21 16:55-18:08Z) | 3/3 | 256 | 3/3 | 256 |
      | g1 `20261021T174300Z-1` (groups 0-4, repeat) | 4/5 | 161 | 5/5 | 256 |
      | **cumulative, all 6 item-3 records (2026-10-22 recount)** | **17/21** | 43 | **20/21** | 43 |
      | *(2026-10-21 tally, first 4 records)* | *10/13* | 43 | *12/13* | 43 |

      First-token top-1 agreement and KL are 0 in every record (all 13 pairs). Fork divergences (3) exceed A/A control divergences (1), but n = 13 is small (observation grade) and the w1c record's A/A also diverged at token 43; this cannot separate a fork effect from GPU batch non-invariance. g1 totals (8 pairs) are fork 7/8 vs A/A 8/8, not the 6/8 vs 7/8 in the 2026-10-21 workspace-f8 progress line; the records are authoritative. Records: `/mnt/raid0/llm/tmp/overnight-20261020/kpf18-run-g1/records/`, `.../kpf18-run-w1c/records/`.
    - *(2026-10-22, workspace-f8; G1 ended `rc1=0 rc2=0`, last two records 16:55-18:08Z.)* Recount over EVERY item-3 pass (w1c + five g1 records; the earlier `kpf18-run/records` hold no item-3 record: they are items 6, 1, 2, 5), re-derived from the row files and matching the 10/13 vs 12/13 table above for the first four: **fork vs no-fork token-identical 17/21, A/A (no-fork vs repeat) 20/21; min greedy prefix 43 for both.** Fork divergences are 4: group 0 at token 43 (w1c) and group 3 at token 161 in all three records that ran group 3 (w1c, `104608Z`, `174300Z`); the single A/A divergence is group 0 at token 43 (w1c). Group 3 never diverged in an A/A pair. First-token top-k identical for the fork pair in every group of the g1 records. What the numbers show: the group-3 fork divergence reproduces (3 of 3 passes, same token 161) while group 3's A/A pairs were identical 3 of 3; the numbers do not show whether that is a fork effect or a prompt-specific near-tie sensitive position, because no arm has yet varied batch composition for group 3. Unchanged grade: OBSERVATION, no clean/unclean call. Open: `KPF-18.0d(item 3, rest)` and `(D2 repeats)` stay open; a group-3-targeted check is filed below.
  - [ ] **KPF-18.0d(item 3, group 3)** — localise the reproducible fork-vs-no-fork divergence at token 161 in group 3 (3 of 3 passes; A/A 0 of 3 diverge): run group 3 alone with fork, no-fork and no-fork-repeat, each with the fork child's batch composition matched (fresh batch order), and read the logit gap at token 161 (top-2 margin) in each arm. Either substrate-GPU (27B fork build), ~20 min, a filler inside KPF-18-S1 step (5). Rule: if the no-fork arms also flip at 161 under the changed batch order, it is a near-tie sensitive position (not a fork effect); if only fork flips with a margin above the A/A noise, it is a fork effect and KPF-18 item 3 does not close.
    - *(2026-10-22, workspace-f8; KPF-18-S1 records `/mnt/raid0/llm/tmp/kpf18-s1/out/records/kpf18-20261022T120943Z-14.json` (localisation, on the shared S1 load) and `...T121719Z-15.json` (item 3 g3 on its own fresh load); binary sha256 `2be7a16e…`, DFlash2 on.)* **Predeclared rule NOT satisfied: classification `aa_diverges_earlier` (undetermined), box stays open.**
      - Record 14: fork vs nofork first diverge at 161 again (tokens 1358 vs 279). The nofork top-2 margin at 161 is 0.167 nats, which is 0.010 nats above the A/A noise of 0.157 (max |Δ chosen logprob| over the 114 pre-divergence positions). But the A/A pair itself (nofork vs nofork_repeat, no fork anywhere) diverges EARLIER, at token 114, with margins 1.10 / 0.87. The rule cannot separate the arms.
      - Record 15 (fresh load): the source's own stream with a concurrent fork child diverges from the no-fork source at 161 (4th of 4 passes), while nofork vs repeat stays bit-identical over 256 tokens. `source_invariance` [1,0], `source_fork_vs_nofork` prefix 161, first-token top-1 1/1, first-token KL 0.0.
      - **Reading: batch-shape/placement numerics, not a fork defect (OBSERVATION grade, not a verdict).**
        - (i) The no-fork arm alone flips at token 114 when the server state differs (record 14). The GPU path is order-sensitive on this prompt without any fork.
        - (ii) The flip at 161 sits at a near-tie (0.167 nats), inside a repetitive loop of the generated text, after 160 bit-identical tokens.
        - (iii) The defect classes the fork mutants model (`fork_clobber_src`, wrong state) give aborts or gross early divergence (KPF-17.1a/b), not a late near-tie flip.
        - (iv) On CPU, which is deterministic, KPF-17.2(3) already shows the source's continuation byte-identical with and without a fork. Today's KPF-13 repro showed fork ≡ prompt-cache hit there, and that the remaining differences are ubatch-shape numerics.
        - (v) The fork arm differs from nofork in exactly the dimension the A/A does not vary: shared vs private trunk cells in the unified KV, and the source's decode/verify batches interleaved with a child that resumes at a different time (child TTFT 12.0 s fork vs 14.6 s nofork; source draft_n 500 vs 440). That is the same-shape-control lesson: the nofork arms are not a same-shape control for the fork arm.
    - [ ] **KPF-18.0d(item 3, group 3) v2 — same-shape control on GPU** (27B fork build, ~25 min, filler in the next GPU window). Three arms, each n ≥ 3 on fresh loads:
      - (A) fork vs nofork with the child released only after the source finishes (no concurrency, so cell sharing is the only difference);
      - (B) as today but with the DFlash2 drafter request-off on both (1-token decode, no verify-batch-shape variation);
      - (C) the A/A floor taken over ≥ 3 repeats with the same timing.
      - Predeclared: if (A) and (B) are token-identical fork vs nofork, the 161 flip is concurrency/batch-shape numerics and item 3 closes on that ground. If the fork alone still flips in (A) with a margin above the (C) floor, it is a fork effect.
  - [ ] **KPF-18.0d(item 4, prefill budget) — measured, judgement pending KPF-18.0e**
    - 2026-10-21 (run 13:02-13:10Z, groups 0-1, record `/mnt/raid0/llm/tmp/overnight-20261020/kpf18-run-item4/records/kpf18-20261021T130205Z-1.json`): control_floor 2/2 bit-identical (256 tokens); vs_fresh 0/2 tokens-identical, min greedy prefix 35, max first-token KL 0.0017 (max |Δlogit| 0.0051), top-1 agree 2/2; structural checks all OK (child_sent_mid_prefill_after_junction 6/6, fork_from_busy_ckpt 2/2, fresh_cache_n_zero 4/4). Consistent with KVU/KPF-18.0e cell-placement non-invariance (fork places KV cells differently than fresh; the A/A control holds placement fixed), but n = 2 cannot separate that from a state defect: judge item 4 against a measured placement floor (KPF-18.0e).
  - [ ] **KPF-18.0e — item 2 oracle on CPU**: bit-identity vs the source's own continuation is not owed when KV cell placement differs (Gemma: fork vs own continuation differs 0.04 nats at token 1). Gate item 2 at the measured A/A floor instead of bit-identity, in both the CPU and GPU runners.
- [ ] **KPF-18-S1 — ONE 27B GPU sweep window for the whole KPF-18 GPU half** (backlog audit §2 S1; ~2 GPU-h instead of ~4.25 GPU-h booked as four windows; 1 load, one shared anchor bank). Prereq: KPF-18.0e. One Qwen3.8-27B load on the fork build `kernels/builds/gpu-20261020-a1f0c8cf9`, :8083 argv `/mnt/raid0/llm/tmp/overnight-20261020/argv.8083-gate.txt`, host threads 184-191 (= q3, KPF-18 claim), harness on research branch `f8/kpf18-arms`; pairs with CPU correctness on other quarters. Order: (1) A/A control (3 launches; the 18.0d item-2 control) -> (2) KPF-18.1 arms A, B, D and row C CUT from 16 lengths x drafter on/off to 6 lengths (0, 1, ub/2-1, ub/2, ub-1, ub) x DFlash2-on (row D covers the no-drafter/MTP prediction; ~12 cells, ~15 min instead of ~38) -> (3) KPF-18.2 clauses 1, 3, 4, 5 (clause 2 BLOCKED_ON_PATCH: `drafter_kv_hit` is not exposed) -> (4) KPF-18.3 parts 1 and 4 (parts 2-3 are CPU fillers) -> (5) KPF-18.0d item 3 (groups 5-7 plus repeats) and item 4 judged at the A/A floor (KPF-18.0e) -> (6) KPF-19.1a flag off/on on the GPU fork build (~10 min; with KPF-17.4/17.4a) -> (7) HSF-4/HSF-5 microbench tail (~10 min each). Acceptance: every arm's record carries manifest sha256 + binary sha256 + argv; the A/A control rate is the floor every item is judged against; per-item counts not pass words.
  - *(2026-10-22, workspace-f8; ran 10:57-12:24Z, rc 0, MI210 + 184-191, 3 loads, every load's linkage/residency/argv read-back OK. Outputs: `/mnt/raid0/llm/tmp/kpf18-s1/out/records/` (15 records), `rows/`, `belief_measurements.jsonl`; `run.log`.)* **Steps 1-5 ran; steps 6 (KPF-19.1a) and 7 (HSF-4/5) did NOT run.** They are not in the plan the runner executed. Box stays open. Per-item counts:
    - **Item 2 (A/A-floor oracle, KPF-18.0e): rule NOT satisfied, 0/12 OK.** The A/A floor is 12/12 bit-identical (zero), so bit-identity is owed. Fork vs own continuation: first-token top-1 12/12, 0/12 bit-identical, max first-token KL 0.035, max |Δp| 0.053, greedy prefixes from 1 to 256. The A/A holds slot and cell placement fixed, so its zero floor measures run-to-run determinism, not the placement floor KPF-18.0e says is not owed. Same class as item 3 (below).
    - **18.1:** A 3/3 n_fork == T (rule met). A tail-only recorded 3/3 at 8000, not "near 0", probably a pinned junction inherited from arm A on the same load (arm-order confound, record `T113323Z-3`). B 4/4 within floor. C cut 6/6 forked at L, 6/6 top-1, 6/6 within floor. D 9/9 + held-out (drop 0). No fork-off baseline launch was run, by S1 design.
    - **18.2:** cold control met. Parity 6/6, 0 defects. Attribution clause abstains (`drafter_kv_hit` not exposed). Policy control met (junction-only = dense = 8508).
    - **18.3:** part 1 chunk-split cost -0.25% / -0.08%, inside the noise floor (no follow-up triggered). Part 4 (60.5k prompt) ABSTAINED: common greedy prefix 0 < 16, so the three runs disagree at token 1, and the rule's greedy-prefix basis cannot judge it.
    - **Item 3 / group 3:** see KPF-18.0d(item 3, group 3) above: `aa_diverges_earlier`, read as numerics.
  - [ ] **KPF-18-S1 remainder + oracle repair** (next GPU window, ~45 min):
    - (1) Run steps 6 and 7.
    - (2) Re-judge item 2 against a placement-varied same-shape control: the source's own continuation restored onto ANOTHER slot through the no-fork prompt-cache path, i.e. fork ≡ prompt-cache hit, as in today's KPF-13 repro. Fold the item-3 v2 arms in.
    - (3) Re-run 18.3 part 4 with d() computed over the per-position chosen-token logprob of a teacher-forced common sequence instead of the greedy common prefix. Predeclare it before the window.
    - (4) Run A_tailonly on a fresh load, or after an explicit `/slots` erase.
- [ ] **KPF-18.1 — hit-length rows added to the KPF-18 gate (KPF-18 does not close without them).** Arms on the matched instrument (same binary, --slot-fork-min-tokens 0 vs on): (A) trunk-then-private-suffix with checkpoint_at=[len(trunk)] vs tail-only (no checkpoint_at): pass = every sibling n_fork_tokens == len(trunk) in arm A, arm B recorded (expected near 0); (B) identical-prompt resend and child==trunk (suffix 0), with and without checkpoint_at [-1]: n_fork_tokens>0 through the n-4 / n-4-n_ubatch checkpoints and logits equal cold, fail = 0 while pre-end checkpoints exist in /slots; (C) trunk-length sweep, >=16 lengths at fixed stride across one -ub period, DFlash2 on and off, checkpoint_at=[len(trunk)]: fork matches fresh within the control floor at every length; (D) hit-count prediction at lengths c-1, c, c+1 for each checkpoint position c in force (junction, n-4, n-4-n_ubatch) with no drafter, MTP and DFlash2: n_fork_tokens equals the KPF-11 rule's prediction (largest checkpoint n_tokens <= lcp with p < task size), where any drafter-dependent drop is measured once from a cold-vs-fork position probe at a held-out length, not assumed; an unidentified drafter configuration must not disable fork reuse for the whole model. Controls: manifest = prompt-set sha256 + binary sha256 + argv from the launch log; baseline = the fork-off arm (--slot-fork-min-tokens 0) on the same binary and the champion tip e33229348; per-sibling raw n_fork_tokens, logits and errors retained; held-out lengths or prompts not used to set the rule; every sibling counted including failures, aborts and abstentions; decision rule predeclared in this line; report counts, not a pass word. CPU subset first on the frontdoor quarter; the :8083 shape needs the GPU window.
- [ ] **KPF-18.2 — drafter parity, per-component attribution and anti-vacuity records for KPF-18.** (1) MTP-on and MTP-off arms must report identical n_fork_tokens for identical prompts (the drafter state travels in the checkpoint); any difference is a defect; add a DFlash2 arm. (2) For every sibling log tgt_kv_hit, recurrent_ckpt_pos, drafter_kv_hit and the minimum used; pass = n_fork_tokens equals the minimum and no sibling with a drafter on has drafter_kv_hit below it (a zero component zeroes the whole fork). (3) Per arm record the checkpoint set that exists (/slots), hit tokens, tokens lost to a missing checkpoint and the prefix-hit counter, so an arm that never armed cannot pass; read n_fork_tokens from the slot, never a server-reported cached-token count alone. (4) Cold control in the same process through cache_prompt=false (check first that llama-server expresses it) instead of a second engine. (5) Policy control: identical resend under DFlash2 with checkpoint_at=[len(trunk)] only vs dense checkpoints every U tokens, n_fork_tokens per arm and per component. Records under VB-KVU-PF after VB-KVU-PF.1. Controls: manifest = prompt-set sha256 + binary sha256 + argv from the launch log; baseline = the fork-off arm (--slot-fork-min-tokens 0) on the same binary and the champion tip e33229348; per-sibling raw n_fork_tokens, logits and errors retained; held-out lengths or prompts not used to set the rule; every sibling counted including failures, aborts and abstentions; decision rule predeclared in this line; report counts, not a pass word.
- [ ] **KPF-18.3 — chunk-split cost, end-checkpoint position, request lane and warm-vs-cold logprob rows for KPF-18.** (1) Log prefill tokens/s and wall for the trunk request with checkpoint_at=[len(trunk)] vs without, same trunk length; if the forced chunk-end split costs more than the noise floor, that is the trigger for an intra-batch state-capture follow-up (measurement only here). (2) Read post_decode and maybe_create_end_checkpoint and record whether the pinned end checkpoint sits at prompt end or generation end; if prompt end, add a multi-turn case where turn 2 resends turn 1's reply and require n_fork_tokens to cover turn 1's prompt and reply, or record the gap. (3) Record per trunk request which lane produced it: chat (message_delimiters present, user-start checkpoints) or raw /completion (near-end checkpoints only). (4) On a >=50k-token prompt with a shared prefix, mean |dlogprob| cold-vs-fork at T=0 must be within the cold-vs-cold floor at the same batch composition; a needle-retrieval pass alone never closes the case. Items 1 and 4 run in the KPF-18 GPU window, items 2 and 3 on CPU. Controls: manifest = prompt-set sha256 + binary sha256 + argv from the launch log; baseline = the fork-off arm (--slot-fork-min-tokens 0) on the same binary and the champion tip e33229348; per-sibling raw n_fork_tokens, logits and errors retained; held-out lengths or prompts not used to set the rule; every sibling counted including failures, aborts and abstentions; decision rule predeclared in this line; report counts, not a pass word.
- [ ] **KPF-19: rebase watch.** `server-context.cpp` is upstream's most-churned file. At the v11 rebase,
  re-verify KPF-11..16 against the new `update_slots`/`pre_decode`, re-run KPF-17 and a reduced KPF-18 (items 1, 3, 6).
- [x] **KPF-19.2 — operator decision: carry the fork's `pinned` flag in slot files?** ✅ 2026-10-20 Decided (operator, OP-KPF19-2): accept upstream's layout — restored junctions come back unpinned (never wrong output; at worst extra prefill if eviction drops the junction before the next fork); no slot-format divergence. Dormant trigger (prose, no checkbox): if KPF-18 or KPF-26 shows migrated fan-outs losing fork hits after a `concurrency_aware.py` full→half KV migration, re-pin after restore by re-sending the trunk's prefill-only `checkpoint_at` request (KPF-21 path). Upstream's slot-file checkpoint block (SCKP, #26004) has no pin flag, so a pinned junction restored from a slot file comes back unpinned and loses its protection from min-step and capacity eviction (data and restore are correct; `test_pinned_junction_slot_file_roundtrip`, `/mnt/raid0/llm/tmp/kv-prefix-fork/p1r2-20261020/RECUT2.md`). Options: (a) accept the limitation; (b) a v2 appendix with a per-checkpoint flag that v1 readers ignore (diverges from upstream's layout).
- [ ] **KPF-19.1 — explicit drafter restore before any rebase that takes #30514.** Today ckpt.load_dft(ctx_dft, dst.id, PARTIAL_ONLY) (server-context.cpp:1886 on `experimental/kv-prefix-fork-p1r-20261020`) restores the WHOLE drafter KV of a plain-KV drafter only because plain llama_kv_cache::state_write ignores the flag; upstream #30514 makes it honour PARTIAL_ONLY, after which the same call restores nothing. Make the fork destination independent of that semantics: full drafter KV (save/load_dft with flags NONE) or a drafter re-prefill, chosen by KPF-13.1's result; check whether DFlash2's ctx_dft is a plain non-SWA cache (subject to this) or SWA. Before the rebase confirm do_slot_fork still carries the drafter through seq_cp_attn(ctx_dft), ordinary checkpoint restore still relies on seq_rm(ckpt.pos_max+1,-1) leaving drafter KV in place, and the prompt-cache load path is unchanged. Done when a CPU test forks an MTP-drafter slot and its draft tokens equal the unforked slot's, first on the current build and again on the CH-18 build that carries #30514 (deterministic conformance; mutation = revert to PARTIAL_ONLY must fail on the second build).
  - *(2026-10-21, workspace-f8)* Implemented `435ee2d8b`. Finding from code reading: on a plain (non-SWA) drafter `seq_cp_attn(ctx_dft)` already shares the whole drafter KV, so the `PARTIAL_ONLY` load is redundant and `dft_partial_noop` (the #30514 emulation) is EXPECTED to pass (job 40's 'not detected' is correct). Added the `dft_no_transfer` mutation as the non-vacuity guard (`82c16126f`, branch `experimental/kpf-19-1-17-3-20261021`, on `fork`); job 28 queued. The Qwen3.8-27B DFlash2 GGUF has `sliding_window` 2048 on all 5 layers, so its drafter is an SWA cache where `PARTIAL_ONLY` IS load-bearing (iswa `state_write` already honours the flag).
  - *(2026-10-21, KPF-17.1c pass)* Confirmed by job 27 (35B+MTP, `dd5bb0d3b`): `dft_partial_noop` PASSES with the flag off and on, and child draft stats equal the fresh run. One mechanism detail matters for KPF-13.1: today's `load_dft` after `seq_cp_attn` is not merely redundant. `llama_kv_cache::state_read_meta` seq_rm's the destination and writes a PRIVATE copy of the same drafter cells, so every fork of a plain-drafter slot pays one drafter-KV copy that sharing would avoid.
  - *(2026-10-21, backlog audit verification; box LEFT OPEN.)* Verified on the current build: job 28 STEPs 191-flag-off / 191-flag-on OK, 191-partial-noop-off/on-passes OK (expected on a plain drafter), 191-mut-dft_no_transfer-off/on DETECTED (`/mnt/raid0/llm/tmp/kv-prefix-fork/kpf-19-1-17-3/queue-results/28-kpf-19-1-17-3/steps.txt`). NOT verified: the "done when" clause's second leg, the same case on the CH-18 build that carries #30514 with the PARTIAL_ONLY-revert mutation failing there (no such run exists; it is carried by KPF-19.1a) and the DFlash2 SWA drafter run (KPF-19.1a). Tick when the CH-18-build leg lands.
  - [ ] **KPF-19.1a — DFlash2 SWA-drafter fork run (correctness, CPU, no exclusive window; also part of KPF-18 S1 on the GPU fork build, and run together with KPF-17.4/17.4a in one load).** On the job-28 build run `test_kpf191` with `KPF_SPEC_TYPE` set to the DFlash2 draft type on the Qwen3.8-27B target + `Qwen3.8-27B-DFlash2-Q8_0.gguf`, flag off and on: child tokens and draft_n / draft_n_accepted equal the fresh run; `dft_no_transfer` must FAIL. Budget ~40 min under a build-role claim on a non-q3 quarter. Also needed before a rebase taking #30514: the same case on the CH-18 build (copy job 28, point B/WT there).

### P2: cache-aware dispatch, orchestrator side (workspace-ec as stack owner) — effort M, ~1-2 weeks

KPF-21 and KPF-25 can start now: they already pay through LCP slot selection and the `--cache-ram` copy restore.
KPF-22..24 and KPF-26 need P1 live.

- [ ] **KPF-20: GitNexus on a fresh orchestrator worktree.**
  `scripts/gitnexus-analyze.sh /mnt/raid0/llm/worktrees/kv-prefix-fork-p2` (the main index is stale, `f72d1d5`).
  Run `context`/`impact` on `SharedKVPoolAdmission.acquire`, `_fits`, `reservation_tokens`, `history_prefill_estimate`
  (`src/scheduling/kv_pool_admission.py`), the `prefix_history.py` LRU, `PrefixRouter.get_slot_for_prompt`,
  `CachingBackend.infer`/`_pin_slots_enabled` (`src/inference/prefix_cache.py`), `scout_stage.py` dispatch,
  `parallel_step_executor.compute_waves`, `typed_decisions/fanout_policy.py` and `routes/delegate.py`. Add grep for
  member-call paths. Report the risks.
- [ ] **KPF-21: trunk-first fan-out.** Wherever N children share a trunk (scouting `scout_stage.py`, HS-19
  scheduled dispatch, `parallel_step_executor` waves, `routes/delegate.py`), issue the trunk once: either the parent
  turn itself, or a prefill-only request with `max_tokens: 0` and `checkpoint_at: [len(trunk)]` once KPF-15 exists.
  Release the children after its prefill completes. This fixes the cold start #26204 measured, where built-in reuse
  found 0 cached tokens.
  - *(2026-10-20, operator session.)* Scout path done on `feat/rtg58-kpf21-25-20261020` (`6d631212`, `a572338d`, pushed, NOT merged to epyc-orchestrator main): `src/inference/trunk_prefill.py` sends one `max_tokens: 0` trunk request with `checkpoint_at` before the gate releases held siblings, behind `ORCHESTRATOR_PREFIX_INDEX` + `ORCHESTRATOR_PREFIX_INDEX_FORK` and `/props.slot_fork`; `tests/unit/test_kpf21_25_trunk.py` asserts `checkpoint_at` is sent before release. Not wired: `llm_call` delegate waves (no per-site payload hook). This box stays open until the branch is merged and the delegate-wave path is wired or recorded as not wired.
    - *(Correction 2026-10-21.)* The 'NOT merged' above is stale: `a572338d` is an ancestor of epyc-orchestrator `origin/main` (merge `73cabf8c`, 2026-10-20 19:42Z; verified with `git merge-base --is-ancestor a572338d origin/main`). The scout path is merged and stays flag-gated OFF (INDEX and FORK flags). What keeps this box open is only the `llm_call` delegate-wave wiring (or recording it as not wired); the enable path is KPF-26 / KPF-26.1 / KPF-27d.
- [ ] **KPF-22: LPM ordering in the admission queue.** Add a bounded longest-prefix-match bypass (at most one skip
  per waiter, FCFS no-starvation kept) using KVU-15c's `fp_history` match length.
  - **This is KVU-6's second bullet and INF-05 KV-3's lever.** Implement it here once. KVU-6's and KV-3's owners
    record the overlap and close their items; this session never ticks their boxes.
- [ ] **KPF-23: reconcile with `PrefixRouter`.**
  - Prefix affinity no longer needs `id_slot`: the server picks the fork source by LCP across all slots. Keep
    pinning only for **session continuity** (same session → its own slot), only when that slot is idle, and never
    as a hard pin that defers (the UFH14-B4 failure mode).
  - Retire the 256-char hash routing on kvu servers. Keep `canonicalize_prompt` only if INF-05 KV-6's measurement
    says it is cheap.
  - Record the decision in `prefix_cache.py`'s docstring and in INF-05's rows.
- [ ] **KPF-24: the KV-pool gate counts unique cells.** In `kv_pool_admission._fits` / `reservation_tokens`, reserve
  `prompt − fork credit + max_new` per request. Read the server's unique-cell figure (KPF-16) rather than summing
  per-request reservations. Add `cache_credit_source: "fork"` next to `fp_history` / `slots_text`. Tests in
  `tests/unit/test_kv_prefix_history.py` and a new `test_kv_pool_unique_cells.py`.
- [x] **KPF-25: byte-stable trunks.** ✅ 2026-10-20 Audit the fan-out prompt builders for anything that varies across siblings
  inside the trunk: ordering, timestamps, ids, per-child text placed before the junction. Use the RTG-27
  prompt-construction-determinism findings. Add a test that N children's prompts share a byte-identical trunk of the
  expected length (the UFH14-B4 `prefix_fp` ladder).
  - *(evidence)* audit `docs/design/kpf25-byte-stable-trunks-audit.md` and `tests/unit/test_kpf21_25_trunk.py` on epyc-orchestrator `feat/rtg58-kpf21-25-20261020` (`6d631212`, `a572338d`), pushed, not merged; the wave reorder and persona relocation are flag-gated on INDEX AND FORK (INDEX alone leaves prompts byte-identical). The task-outcome check is KPF-26.1.
    - *(Correction 2026-10-21.)* 'pushed, not merged' above is stale: the branch is merged to epyc-orchestrator `origin/main` (merge `73cabf8c`; `a572338d` is an ancestor, verified). The flag gating described is unchanged (OFF by default).
- [ ] **KPF-26: P2 gate.** Replay a real fan-out (an HS-19 scouting round or a delegate wave) through :8000 on the
  P1 build: trunk prefilled once (server `timings`), child TTFT, peak unique cells, admission waits, and **task
  outcome unchanged** on the replay set vs the pre-P2 path. Two windows; records under VB-KVU-PF.
- [ ] **KPF-26.1 — task-outcome check on persona-bearing waves.** KPF-25's wave-prompt reorder and persona relocation are gated on ORCHESTRATOR_PREFIX_INDEX plus ORCHESTRATOR_PREFIX_INDEX_FORK (a572338d on `feat/rtg58-kpf21-25-20261020`; INDEX alone leaves prompts byte-identical). The KPF-26 replay set must include delegate waves whose steps carry different personas and compare TASK OUTCOME flag-on vs flag-off, not only prefill tokens and TTFT. Controls: frozen replay manifest (task ids + prompt digests); flag-off path as baseline; per-task raw outputs retained; held-out waves not used to choose the ordering; every task counted including failures and timeouts; predeclared rule = outcome rate within the flag-off rerun-to-rerun spread, any regression keeps the reorder off. Two windows, records under VB-KVU-PF.
  - [x] KPF-26.1a: runner. `scripts/trace/kpf261_outcome_run.py` (epyc-orchestrator branch `feat/kpf261-outcome-runner-20261022`, `c6f58498`, pushed, not merged). Renders every delegate-wave step with the REAL `StepExecutor._build_step_prompt`, flags off (arm A, persona prepended as `llm_call` does) and on (arm B, shared-first, persona after the trunk), plus a flag-off rerun (arm A2) as the rerun-to-rerun spread; ABA order per rep; frozen `manifest.json` (task ids + prompt SHA-256 per arm, resume aborts on mismatch); raw outputs kept; every case counted, errors are fails; predeclared verdict UNCHANGED / WITHIN_SPREAD (drop <= |rate(A)-rate(A2)|) / CHANGED (reorder KEEP_OFF) / INVALID. ✅ 2026-10-22
  - [x] KPF-26.1b: 18 unit tests with a fake HTTP endpoint (no model): treatment really reorders, persona-after-trunk regression is detected as CHANGED, decision table, B errors are regressions, manifest freeze, resume, stop/deadline, port-ownership and window guards. ✅ 2026-10-22
  - [x] KPF-26.1c: filler job + queue row `s5-kpf261-outcome` (CPU, private store-build frontdoor 35B-A3B on :18966, ram_admit 41 derived, one replicate per grant: win1 seed 261, win2 seed 262). The blocker "runner not located" was wrong: the task text and its audit (`docs/design/kpf25-byte-stable-trunks-audit.md`) specify the design and nothing existed, so the runner was written. ✅ 2026-10-22
  - [ ] KPF-26.1d: window 1 (seed 261) run; verdict in `/mnt/raid0/llm/tmp/kpf261-outcome-out/summary.win1.json`.
  - [ ] KPF-26.1e: window 2 (seed 262) run, different waves; `summary.win2.json`. KEEP_ON_ELIGIBLE needs both windows UNCHANGED or WITHIN_SPREAD.
  - [ ] KPF-26.1f: VB-KVU-PF write side for the outcome records (per window: manifest digest, seed, per-arm pass counts, spread, drop, verdict). Extend the `kv_prefix_fork` adapter sidecar; one tuple per record through `claim_tuple.grade()`, no new ladder. Write side before the first window completes if the owner can; otherwise the runner's `cases.jsonl` + `manifest.json` (re-hashable) are the attestation and nothing is lost.
  - Scope note: KPF-26.1 covers the outcome clause only. Trunk-prefilled-once timings, child TTFT, unique cells and admission waits stay in KPF-26 (need the P1 build and the stack on :8000).
- [ ] **KPF-27: revived prefix index (radix tree) — orchestrator side, behind `ORCHESTRATOR_PREFIX_INDEX`
  (default OFF).** Branches `feat/rtg58-p2-prefix-index` (branch A: index, record observation, `idle` pin) and
  stacked `feat/rtg58-p2-prefix-index-gate` (branch B, `d63f7aa9`: KV pool gate wiring — GitNexus HIGH on
  `SharedKVPoolAdmission.acquire/_admissible/release`, lands only after workspace-ec acknowledges). **Branch A landed
  on epyc-orchestrator main 2026-10-04 as `2833e3a2` + audit fix `99348f54`** (flag OFF; API not reloaded). Branch B
  is stacked on `2833e3a2`, so it rebases onto `99348f54` before landing. Module `src/inference/prefix_index.py`: one
  index per physical server, path-compressed trie over chained 512-char block hashes, entries `slot` (bound to
  `/slots` `id_task`), `pending`, `served`, `inflight`; reconciled with `/slots` at every gate poll; verified slots
  shared host-wide via `{tmp_dir}/kv_prefix_index.{host}_{port}.json`. Design, blast radius, the eight server questions
  for P1's INTERFACE.md and the test record:
  [`artifacts/rtg58-p2-prefix-index-20261004/DESIGN.md`](../../artifacts/rtg58-p2-prefix-index-20261004/DESIGN.md).
  - [x] KPF-27a: audit of the January `radix_cache.py` (keep LPM semantics; fix stale-slot bug and missing
    path compression; drop client slot allocation and client tokenizer). Regression test for the stale-slot bug.
    ✅ 2026-10-04 — landed with branch A (`2833e3a2`, `test_stale_slot_regression_from_the_january_radix_cache`).
  - [x] KPF-27b: wiring — serving-record observation (`recorded_call`, `passthrough.write_serving_record`),
    `CachingBackend` pin policy `idle` (branch A); KV pool gate (`prefix_key` on primitives, passthrough,
    scouts; credit, LPM, trunk hold, fork credit, fork plan) on branch B. 2026-10-04: the branch A half is on main
    (`2833e3a2` + `99348f54`); the branch B half waits on KPF-27b-ack.
    ✅ 2026-10-04 — branch B landed on epyc-orchestrator main: `f9b1553b` (KV pool gate driven by the prefix index,
    flag OFF), `084921bb` (review D1–D6 + KPF-26 queue cap), `d39491e3` (the stack owner's six P2-B defect tests as
    regressions), `46c2d833` (Fable re-review notes: `ORCHESTRATOR_PREFIX_INDEX_FORK=auto` turns fork features on only
    when the server reports `/props.slot_fork`; busy-source credit re-inflation; per-owner prefill; prompt_progress).
    Flag-off path byte-identical (`test_prefix_index_flag_off.py`). API not reloaded; the shadow window is KPF-27d.
  - [x] KPF-27b-ack: workspace-ec acknowledges the HIGH blast radius of branch B (acquire/_admissible/release)
    before it lands, as for KPF-12/13.
    - *(2026-10-04 ~08:00Z, workspace-ec.)* P1's handoff edit is on main (`b22ff171`). Branch B's Fable review returned
      **ACK-with-fixes (D1-D6)**; the fixes were made and the **v2 re-review is in progress**. The ack is given, and this
      box ticked, when the v2 review clears D1-D6.
    - ✅ 2026-10-04 — the v2 re-review's notes were fixed in `46c2d833` and its six defect tests landed as regressions
      (`d39491e3`); branch B then landed on main (KPF-27b).
  - [x] KPF-27c: flag-off proof (`tests/unit/test_prefix_index_flag_off.py`) and wiring tests through the
    passthrough route and `llm_call` → `/completion`. ✅ 2026-10-04 — branch A 237 passed, branch B 350 passed; the
    one wider failure (`test_canonicalization_throughput`) fails identically on untouched main (DESIGN.md §6).
  - [ ] KPF-27d: land on main (owning session), then a **shadow window** on :8083 with the flag on and
    `_FORK` off: record `prediction_abs_err_tokens/predictions`, `slot_prediction_hits/slot_predictions` and
    the `stale_drops` mix from `get_status()`; done when two windows are recorded (VB-KVU-PF). 2026-10-04: branch A
    is landed; branch B and both shadow windows are open.
  - [ ] KPF-27e: when P1's INTERFACE.md lands, map its fields (content epoch, `id_slot`/`id_task` on OAI
    timings, checkpoint positions, `/props` fork capability, unique cells) into `reconcile`/`lookup`, and send
    `checkpoint_at` from the trunk-first path (KPF-21).
    - 2026-10-04: the mapping half is on main (`084921bb`: `/slots` `content_epoch` binding, `prefix_hash` with a
      server-identical `fnv1a64_tokens`, checkpoint-mode fork from a busy slot; `46c2d833`: `/props.slot_fork` gates
      FORK=auto). Each field is used when present and falls back to v10 inference when absent. Still open: sending
      `checkpoint_at` from the trunk-first path, which needs the prefill-only trunk request (KPF-21 → KPF-15). P1's
      server fork is built (workspace-ec); its live INTERFACE fields are proven in the KPF-27d shadow window.
- KPF-21 note: trunk-first is implemented centrally in the gate (`ORCHESTRATOR_PREFIX_INDEX_FORK=1`, branch B), not
  per fan-out site; KPF-21 stays open for the prefill-only trunk request with `checkpoint_at` (needs KPF-15).
- KPF-22 note: the bounded LPM bypass is implemented in KPF-27 branch B (`_prefix_index_admissible`, at most
  `ORCHESTRATOR_PREFIX_INDEX_LPM_MAX_SKIPS` passes per waiter). KVU-6's and INF-05 KV-3's owners record the
  overlap; KPF-22 closes after KPF-26 measures it.
- KPF-23 note: decision recorded in `prefix_cache.py`'s docstring (landed with branch A) — `PrefixRouter` kept as the
  legacy opt-in; index pin policy `idle` pins only verified idle slots; hash routing retires after the KPF-27d shadow
  metric.
- KPF-24 note: `cache_credit_source: "prefix_index"` added on branch B; fork credit on the reservation behind
  `_FORK`; switch from the client estimate to the server's unique-cell figure once KPF-16 publishes it.

### P3: sequence-affine KV cell allocation (workspace-ec) — effort: measure S (~2-3 days), build S-M (~1 week)

Measure first. The build is gated on the measurement.

- [ ] **KPF-30: measure the mixed-block fraction.** Add a debug counter to KVU-19a's block-liveness scan kernel, or
  a host-side pass over cell seq bits per ubatch, reporting for each decode/verify row: live 256-cell blocks, and
  live blocks that also hold another sequence's **private** cells (shared trunk cells excluded). Run on an organic
  replay at the production shape (4 slots decoding, DFlash2) on the KVU-19b build.
  - **Gate (proposed, confirm when the counter exists):** build KPF-32 only if mixed blocks are ≥ 10% of live blocks
    for decode/verify rows in two windows. Otherwise close P3 with the measurement recorded.
- [ ] **KPF-31: GitNexus on `find_slot`**, plus `apply_ubatch` and `llama_kv_cells` (`src/llama-kv-cells.h`), in
  the P3 worktree. `find_slot` feeds slot restore (see the GitNexus table).
- [ ] **KPF-32: affine allocator.** In `find_slot` (`llama-kv-cache.cpp:901-1075`), give each sequence a cursor into
  its own 256-cell chunk, matching the FA block size of KVU-19a/19b. Place its new tokens there, and open a new chunk
  when it is full. Fall back to first-fit when fragmented. Dispatch keys on unified KV and n_seq > 1 (shape), with
  argv `--kv-affine-chunk N` (0 = off) as the A/B control. ~100-200 LOC, no kernel change.
- [ ] **KPF-33: P3 gate.**
  - Correctness: `test-backend-ops -o FLASH_ATTN_EXT`, the state and restore tests, and output equivalence off vs on.
  - Speed: batched-bench `-kvu` at 4×16k and 4×80k with the DFlash2 verify shape, and P3-style decode with
    neighbours. Pair with KVU-19b's numbers.
  - Pool-full behaviour: no new "failed to find a memory slot", and no new sub-batch error (the KVU-7 class).

### P4: upstream #29510 `kv_rows` port as an A/B arm vs KVU-19b (workspace-ec) — effort M-L (HIP MMA + vec), ~2-4 weeks, at the v11 rebase

**Gated on the #26046 v11 FA-path audit** ([`artifacts/v11-fa-path-audit-20261004/REPORT.md`](../../artifacts/v11-fa-path-audit-20261004/REPORT.md), complete
2026-10-04). v11 moves verify and prefill from rocWMMA onto MMA/MFMA (upstream removed the rocWMMA FA in #26046,
2026-07-24), which changes where 19a/19b and `kv_rows` live. Diff on hand:
`/mnt/raid0/llm/tmp/kv-serving-survey-20261004/pr29510.diff` (scratch snapshot of the open PR as of 2026-10-04; it is
upstream code, so it is not copied into this repo — re-fetch with `gh pr diff 29510 -R ggml-org/llama.cpp`).

- [ ] **KPF-40: pre-check (read-only, zero compute).** Read the v11 audit. Re-derive which of our ubatch shapes
  `get_n_kv_slices()` accepts on the **hybrid** split (`llama-memory-hybrid.cpp:89`, `split_equal`), which may
  overturn the survey's "verify falls back" finding (see the survey correction above). Re-check #29510's state:
  merged, reshaped by the Metal objection, or still a draft. Write the port plan into this handoff.
  - *(Annotation, workspace-ec, 2026-10-04.)* The v11 FA-path audit is COMPLETE. Durable copy:
    [`artifacts/v11-fa-path-audit-20261004/REPORT.md`](../../artifacts/v11-fa-path-audit-20261004/REPORT.md) (the
    `/mnt/raid0/llm/tmp` path is not durable). Its actionables are filed as V11-FA-1..4 in
    [`kv-unified-stack-rollout.md`](kv-unified-stack-rollout.md) section C (owner workspace-ec). P4 relevance: on
    gfx90a, v11 MMA serves only >32-row shapes; the 3-32-row band goes to TILE, which `kv_rows` does not touch.
- [ ] **KPF-41: port.** If #29510 has merged upstream by v11, it arrives with the rebase. Otherwise port it onto the
  v11 experimental line:
  - Enable the MMA `kv_rows` path on CDNA. Upstream gates it `GGML_CUDA_CC_IS_NVIDIA && turing_mma_available`; add
    AMD MFMA.
  - Add `kv_rows` reads to the vec kernel for plain decode.
  - Make the q8_0 → f16 conversion gather only the referenced rows, extending KVU-19a's dead-block conversion skip.
  - Dispatch keys on shape: `kv_rows` where slicing applies and cells are not shared (`n_sum ≤ n_kv`). Shared
    trunks go to P5 or fall back to 19b. Upstream's `cparams.fused_kv_rows` must not become an env-only gate.
- [ ] **KPF-42: P4 gate, A/B vs KVU-19b.** Run on the KVU-18 cells (0/1/2/3 neighbours), 4×16k and 4×80k
  batched-bench, and the DFlash2 verify shape. Pair `test-backend-ops` exactness, the 64-case harness and output
  equivalence with the speed numbers. Keep the winner per regime inside one binary, or drop the loser. Records under
  VB-KVU-PF.

### P5: cascade / shared-trunk attention, LSE merge (workspace-ec) — effort L, ~4-8 weeks; after P1, profile first

- [ ] **KPF-50: rocprof profile first (GPU window).** On the P1 build, at 4 × 80k with a 60k forked trunk and
  DFlash2, measure attention's share of the decode/verify step and the share spent on trunk cells.
  - **Gate (proposed):** build only if trunk attention is ≥ 20% of step time after P1 + KVU-19b (+ P4 if landed).
  - Survey §1.2's inference that gfx90a attention here is compute/latency-bound (~15 ns per foreign cell per layer,
    ~10× the byte cost) is the reason to expect more than the bandwidth argument. Confirm it in this profile.
- [ ] **KPF-51: design.**
  - Trunk identification: blocks whose seq set covers every decoding sequence in the ubatch (vLLM
    `get_num_common_prefix_blocks`). The P1 fork makes these exact, and the 19a/19b scan already computes block
    liveness.
  - Graph (`src/llama-graph.cpp` `build_attn_mha` L2533, `build_attn` overloads): pass 1 runs all N × (≤8) query
    rows against the trunk cells as one matmul-shaped FA call; pass 2 does per-row private suffixes via 19b or
    `kv_rows`; then an LSE merge.
  - Reuse the split-K partial/LSE machinery (`flash_attn_combine_results`, `ggml/src/ggml-cuda/fattn-common.cuh:916`;
    the CDNA2 fused-combine vec path) rather than a new merge kernel.
  - Write a CPU reference path for `test-backend-ops`.
- [ ] **KPF-52: kernels on the v11 FA paths** (MMA/MFMA for verify and batched; vec for decode), not on v10 rocWMMA.
  Add `test-backend-ops` cases: cascade vs non-cascade within tolerance, and bit-identical with cascade off.
- [ ] **KPF-53: P5 gate.** Decode tok/s at 4 × 80k with a 60k trunk, paired with greedy equivalence vs non-cascade
  over the KPF-18 prompt set. No regression when nothing is shared (shape dispatch turns cascade off). Records
  under VB-KVU-PF.

## Research intake 2026-10-20: dormant triggers (owner: this handoff unless noted)

Each item is dormant, not blocked. A reviewed session confirms the trigger and only then materializes a task.
- **MTP state hook port** (upstream #30141 shape: validate width, row count and payload size, clear transient rows). Trigger: KPF-13.1 shows a draft-acceptance drop after fork restore, or the change merges and enters a pull-fresh list (CH-18).
- **iSWA `seq_pos_max` assertion** (upstream #29480). Trigger: it merges, or a Gemma-class gate run shows a partial `seq_rm` below the window before a checkpoint restore.
- **Intra-batch state capture** (internal checkpoint inside one forward, the vLLM #52789 shape). Trigger: KPF-18.3 item 1 shows the forced chunk-end split costs more than the noise floor.
- **Refresh of vLLM #53479 / lookahead-hash #50897 / chunk-stop #54076**. Trigger: the refreshed #53479 head is re-opened on current vLLM main, or #50897 merges; then re-dive.
- **Write-side trailing-block-drop change (#52244) and the third-party bisect method.** Trigger: a DFlash2 identical-resend test or the warm-vs-cold logprob row (KPF-18.3 item 4) needs the exact change or method detail.
- **Stage1-unverified survey entries intake-2064#record and intake-2069#record.** Trigger: an owner needs the reporters' data that our own spacing and divergence measurements cannot supply; then dive.

## Dependencies and sequencing

| Phase | Hard dependencies | Interacts with |
|---|---|---|
| P0 | none | — |
| P1 | KPF-01/02; current champion tip | Prefill budget (RTG-57; KPF-18 item 4 tests against it); KVU-19a/19b exactness over shared cells (KPF-17); the `-b 512 -ub 512` + `--no-cache-idle-slots` package (production shape for the gate) |
| P2 | KPF-21/25 none; KPF-22..24/26 need P1 deployed | KVU-6, KVU-15c (`fp_history`), INF-05 KV-2/3/6, RTG-27, UFH14-B4 |
| P3 | KVU-19b build (the skip that makes affinity pay); KPF-30 gate | P1 (shared trunk cells are excluded from "mixed") |
| P4 | v11 FA-path audit; v11 rebase | KVU-19b (A/B partner); P5 (shared rows) |
| P5 | P1 deployed; KPF-50 gate; v11 FA paths | KVU-19a/19b scan; P4 |

## Effort summary

| Phase | Effort | Estimate | Expected impact (survey estimates, not measurements) |
|---|---|---|---|
| P1 | M-L | 2-3 weeks incl. gate (~400-700 LOC server + KV API + tests) | Fan-out child TTFT minutes → seconds; −(N−1)·T cells (~6 GB at 4×60k) |
| P2 | M | 1-2 weeks (KPF-21/25 parallel to P1) | Makes P1 fire: hit rate, unique-cell admission |
| P3 | S + S-M | 2-3 days measure; ~1 week build if gated in | Lets 19b skip generated-token blocks |
| P4 | M-L | 2-4 weeks at v11 | Overlaps 19b for plain decode; possibly verify too (KPF-40) |
| P5 | L | 4-8 weeks | Trunk attention ÷N; maybe 1.3-2× decode at 4×80k / 60k trunk |

## Key files

- **llama.cpp** (reference lines tagged `[v10 `ffc1bac82` · champ `dd3d9721c` · p1r `a1f0c8cf9` · p1r2 `14d603f3a`]`; edit only in the phase worktree):
  - `tools/server/server-context.cpp`: `copy_state_to` [735 · 756 · 798 · 798], `get_available_slot` [1601 · 1632 · 2013 · 2013],
    `create_checkpoint` [2365 · 2396 · 2802 · 2802], the idle-slot purge [2469 · 2713 · 2968 · 3181],
    `update_slots` [2856 · 3194 · 3526 · 3755], `pre_decode` [2984 · 3334 · 3666 · 3895]
    (checkpoint restore ~[3451 · 3812 · 4146 · 4375], placement ~[3562 · 3933 · 4263 · 4502]).
  - `tools/server/server-task.{h,cpp}` (request params, `server_prompt_cache`, checkpoints).
  - `src/llama-kv-cache.cpp` (`seq_cp` [450 · 451 · 526 · 526], `find_slot` [901 · 902 · 977 · 977], `apply_ubatch` [1100 · 1101 · 1176 · 1176], `set_input_kq_mask` [1757 · 1758 · 1833 · 1833]);
    `src/llama-kv-cells.h`.
  - `src/llama-memory-hybrid.cpp` (split L89 and `seq_cp` L152 in all four; state [191 · 191 · 203 · 203]); `src/llama-memory-recurrent.cpp`
    (`seq_cp` L246 in all four); `src/llama-kv-cache-iswa.cpp` (state [259 · 259 · 273 · 273]).
  - `src/llama-context.cpp`, `include/llama.h`, `common/common.cpp`, `common/speculative.{h,cpp}`
    (`common_speculative_{get,set}_state`).
  - `src/llama-graph.cpp` (`build_attn_mha` [2533 · 2699 · 2699 · 2699]).
  - `ggml/src/ggml-cuda/fattn-{common.cuh,vec.cuh,wmma-f16.cu,mma-f16.cuh}`.
  - Tests: `tests/test-save-load-state.cpp`, `tests/test-state-restore-fragmented.cpp`,
    `tests/test-recurrent-state-rollback.cpp`, `tools/server/tests/unit/test_slot_save.py`,
    `tools/server/tests/unit/test_speculative.py`.
- **Orchestrator**: `src/scheduling/kv_pool_admission.py`, `src/scheduling/prefix_history.py`,
  `src/inference/prefix_cache.py`, `src/api/routes/chat_pipeline/scout_stage.py`, `src/parallel_step_executor.py`,
  `src/typed_decisions/fanout_policy.py`, `src/api/routes/delegate.py`, `src/backends/serving_calls`.
- **Evidence and inputs**: the survey (`artifacts/gpu-block-27b-20261004/analysis/kv-serving-survey-REPORT.md`; the
  `pr29510.diff` snapshot stays in `/mnt/raid0/llm/tmp/kv-serving-survey-20261004/`); the v11 FA-path audit
  (`artifacts/v11-fa-path-audit-20261004/`); the KVU-16b root cause
  (`artifacts/gpu-block-27b-20261004/analysis/kvu16b-rootcause-REPORT.md`); the 2026-10-04 skip OFF/ON × `-b` replay
  (`artifacts/gpu-slot-ak-20261004/`); the P2 prefix-index design (`artifacts/rtg58-p2-prefix-index-20261004/DESIGN.md`); the KVU-19a fold record
  (`docs/design/fa-masked-block-skip-20261003-fold.md`).

## Not filed here (explicit)

- **vLLM/SGLang on the MI210 for this role.** Not a production path (survey §5: gfx90a degraded tier, #25030, no
  FP8, no GGUF path for this hybrid). A ≤1-day reference probe is the operator's call. It is not filed.
- **CacheBlend / `--cache-reuse` / non-prefix reuse.** ~~Impossible with recurrent state.~~ **Corrected 2026-10-21 (KPF-63):** not impossible. At the champion `llama_memory_hybrid::get_can_shift()` returns true (`llama-memory-hybrid.cpp:133`), so the server does not disable `--cache-reuse` on hybrids; no production role sets the flag; the engine defect is CH-21 (`handoffs/active/autokernel-champion-aggregate.md`; design `/mnt/raid0/llm/tmp/cacheclip-port-20261021/DESIGN.md`); non-prefix reuse on hybrids is under test in KPF-60.
- **Per-slot split KV (KVU-16d option c).** Decided "keep shared 393k" in RTG-57. Its reopen trigger lives there.
- **#28532 `--slot-linger-ms`.** KPF-23's session-continuity pinning covers the same effect from the orchestrator.
  Cherry-pick it only if KPF-26 shows session turns losing their slot.

## Reporting

Flip boxes here. The owning session (ak-ds41-main) updates RTG-58's `Next action`; workspace-ec reports phase
boundaries to it on the bus. Append to `progress/YYYY-MM/`. Production default-on of any feature goes through the
kernel-promotion ratification, not this handoff.

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

## Research intake 2026-10-20 — DeepInfer (research intake entries 2116–2142, see research/intake_index.yaml)

Operator-approved 2026-10-20 via research intake (plan sha256 recorded in the session's stage3_filing).

- [ ] **KPF-28 — DS41 (dsv4 memory) checkpoint and fork characterisation (intake-2116#record, intake-2136#record).** On the prefix-fork build with the DS41 GGUF record bytes per context checkpoint per component (raw SWA window, compressed planes and compressor state, indexer, engram), window-ring bytes and plane bytes separately, whether create_checkpoint/restore and the KPF-11 fork rule work on llama_kv_cache_dsv4 (hit length vs the checkpoint grid, 128-aligned vs dense), and resume prompt_n. Correctness class, CPU. Decides whether a 128-grid policy or a window-state-free checkpoint (needs DS41-CED.1) is worth building.
- [ ] **KPF-60 — Chunk-KV phase 0: setup, frozen gate thresholds, measurements (in progress since 2026-10-21 on operator agreement).** Per `/mnt/raid0/llm/tmp/cacheclip-port-20261021/DESIGN.md` section 6: worktree on `experimental/chunk-kv-reuse-p0` cut from the champion tip resolved live, GitNexus index of the worktree (`llama_state_seq_set_data_ext` and the `update_slots` area are HIGH impact, proceed methodically); commit the predeclared gate thresholds and the corpus manifest before any phase produces a number; static check of production argv for `--cache-reuse` on hybrids (none set it per the cache-reuse-hazard source check); measure prefill rate per role, inject latency, GDN decay statistics and (A,B) norms from a real run, and the layer-input drift study (isolated versus in-context) on the 27B and the 35B-A3B. Non-timing parts need only build-role claims; timing parts need a window. Premise: intake-2297#record, intake-2326#record. Production is untouched and nothing here merges to production; the work folds into the champion only. Acceptance: thresholds and manifest committed to git; a drift curve and a crossover table per role in this handoff; the argv check result recorded. Estimate: 4-6 days plus one timing window.
- [ ] **KPF-61 — Chunk-KV phase 1a: reorder planner, exact and hybrid-safe (in progress since 2026-10-21).** Port the reorder planner idea (rebuild the longest exact prefix of a cached prompt from pieces of the incoming prompt, minimum run 16, last tokens pinned) into llama-server as an opt-in `kv_chunks_reorder`, relying on the KPF fork and `checkpoint_at` junctions, with telemetry for matched-prefix share. It is the one non-prefix mechanism in the vLLM, SGLang and LMCache survey that is compatible with recurrent state (`/mnt/raid0/llm/tmp/kv-reuse-survey-20261021/REPORT.md`). This is infrastructure for the planned paths, not a bet on current traffic: REPL embedding retrieval re-retrieves the same 256-token chunks across turns and requests after different text each time, episodic memory and SkillBank put a small heavily reused library into many requests, and document QA and RAG are planned. Coding-agent transcripts (Claude Code, Codex, opencode) are the wrong proxy because those agents append reads in order; they show reorder-case repeats at 0.003-0.004 percent of prompt tokens (trace-chunk-reuse report 2026-10-21). Real reuse on the planned paths is measured by RTE-LOG-1 once they are live (DP-I). Acceptance: a reordered request is bit-identical to a full recompute of the reordered prompt on the 27B and the 35B-A3B; a permutation task A/B; the prefix-reconstructible share is reported by RTE-LOG-1 data when it exists. Estimate: 1-2 weeks.
  - *(2026-10-21 note, wrap-up 3c4ca599-c.)* P1a is at `a62f64d5` in the chunk-KV experimental tree (experimental branch, not production); its kernel-manifest row (V11-099) is pending push and not yet in `docs/reference/kernel-manifests/llama-v11-manifest.md`. Design of record: `/mnt/raid0/llm/tmp/cacheclip-port-20261021/DESIGN.md`. Real-trace finding that sets the framing: a never-evicted prefix cache captures about 99 percent of prompt tokens in append-ordered agent traffic, so chunk reuse is NOT justified by coding-agent traces; operator framing (2026-10-21): chunk reuse is infrastructure for the REPL, memory and RAG paths, whose real reuse RTE-LOG-1 measures. KPF-64 is the parallel prefix-hit-reliability lever.
  - [x] **KPF-61.1 — add the V11-099 row (chunk-KV P1a, `a62f64d5`) to `docs/reference/kernel-manifests/llama-v11-manifest.md` once the branch is pushed to `fork`.** Row fields as V11-098: branch and sha, status PEND, launch impact, gate, owner; a manifest row for an unpushed commit would cite an object nobody can fetch. (filed 2026-10-21)
    - 2026-10-21 TICKED (audit-ticks): V11-099 row landed in `docs/reference/kernel-manifests/llama-v11-manifest.md` by `773c9f8fb` (on origin/main) and cites `experimental/chunk-kv-reuse-p1a-20261021` @ `a62f64d5e`. `git ls-remote fork` shows that branch at `a62f64d5eae92b80d9fbf846701f023fad18cdca`, so the object is fetchable; no push was needed.
- [ ] **KPF-62 — Chunk-KV phase 1: attention-only core (store, range export and inject, RoPE shift, selector).** Per DESIGN.md section 6: `server_chunk_store` keyed by content hash with no predecessor, libllama range export and inject, RoPE shift on inject with the startup self-check, selector v1 (head window plus auxiliary-model scoring plus check-layer K deviation, group-contiguous runs), sparse recompute by explicit-position batches; test model Qwen3-VL-30B-A3B text path plus a small attention-only CI model. Gates G0, G1, G3 of DESIGN.md section 5 are frozen by KPF-60 before this phase produces a number. Whether phase 2 onward starts is DP-I. Acceptance: G0, G1 and G3 pass on the attention-only models, and speed is reported against the tuned prefill including load. Estimate: 2-3 weeks.
  - *(2026-10-21 note, dpf-kpf62: SLICE 1 DONE, KPF-62 stays open.)* Branch `experimental/chunk-kv-reuse-p1-20261021` on the fork @ `2b7e1c98d` (over `afc9efc35`, on P1a `a62f64d5`). Landed: libllama range export/inject (`llama_chunk_kv_*` in `src/llama-ext.h`; hybrid/recurrent/SWA refuse with a log line, off = byte-identical), K re-rotation through the existing K-shift graph, startup rope round-trip self-check, content-keyed `server-chunk-store.h` (not wired into the server yet). CPU results on the tiny attention models (qwen3, qwen3vl, qwen3vlmoe; f32 K/V): round-trip NMSE ~3e-15, G1 K NMSE <= 2e-11 and logits NMSE <= 7e-18 at delta 1/17/300, V bit-exact; `qwen35` refuses cleanly. `llama-dense` K NMSE is 1.2e-5 at delta 300 because the generated model carries random `rope_freqs` (informational there; logits still gate). Tests: `tests/test-chunk-kv.cpp`, `tests/test-server-chunk-store.cpp`; `scripts/chunk-kv/build_and_test_cpu.sh`. **Ready for an inference window:** `scripts/chunk-kv/run_g1_real_role.sh` (G1 on the real Qwen3-VL-30B-A3B Q4_K_M with f32 K/V; refuses unless `WINDOW_CONFIRMED=1`). **Remaining slices (fresh agents):** (1) selector: head window W=64 + check-layer K deviation + group-contiguous runs, then auxiliary-model scoring (needs a K tap at a check layer); (2) sparse recompute by explicit-position batches beside the cache-reuse block, G0 at r=100% bit-identical; (3) server wiring: `--chunk-store-mib` (0 = off), `kv_chunks` request field, isolated-encode on miss, startup self-check logged, `prompt.approx=true`, ctx_dft/MTP/DFlash2 coverage; (4) G3 harness on the frozen corpus (needs the corpus manifest hash in P0_THRESHOLDS section 8); (5) speed vs tuned prefill including load (timing window).
  - *(2026-10-21 ruling, main.)* G3 continuation positions = the prompt-suffix tokens after the last reused chunk plus the first 64 generated tokens of the full-recompute reference, teacher-forced; KL, top-1 and NMSE are computed over all of those positions. Recorded as a dated amendment in `P0_THRESHOLDS.md` (uncommitted until the corpus manifest exists).
  - *(2026-10-21 belief-kernel wiring, VB-KVCHUNK-WRITE.)* KPF-62 G1 and G3 records feed `scripts/vidya/adapters/chunk_kv.py` (carrier on lane `lane/dpf-specs-20261021`). Mapping: speed vs tuned prefill and inject cost use the existing kinds `prefill_rate` (tok/s) and `inject_latency` (ms, samples) with `source_program: KPF-62`, `served_pin {role, model, kernel_ref}` and the `window` claim. G1 (K/V/logits/round-trip NMSE, lower better) and G3 (mean KL, p95 KL, top-1, logits NMSE median/p95, retention, naive-baseline ratio) fit no existing kind, so the adapter needs `KPF-62` added to `PROGRAMS` plus two kinds (`shift_exactness`, `approx_gate`), each re-deriving its value from recorded per-position payloads; that extension is KPF-62.2.
  - [ ] **KPF-62.1 — Fix the K-shift for YaRN models (re-applied `attn_factor` on every rotation).** `llama_kv_cache::build_rope_shift` passes the model's `yarn_attn_factor` and `yarn_ext_factor` to `ggml_rope_ext`, which multiplies cos and sin by `mscale`, so every `seq_add` multiplies K by an extra `mscale` (details in `/mnt/raid0/llm/tmp/cacheclip-port-20261021/YARN_SHIFT_NOTE.md`). Chunk-KV side: the startup self-check must fail on such a model and the feature must refuse (or use the corrected shift) until the champion-side fix lands; then run the self-check on a YaRN-configured tiny model as a regression. The champion-side fix of the existing context-shift and `--cache-reuse` paths is routed separately by main. Acceptance: self-check NMSE <= 1e-6 on a YaRN-configured model, or a clean refusal.
    - 2026-10-21 note (yarn-kshift-fix): champion-side fix written and tested, `experimental/yarn-kshift-fix-20261021` @ `b67a5b9bc` (manifest V11-100, pending fold into the NEXT consolidation after C2). Confirmed by failing test: YaRN round-trip K NMSE 8.8e-2, non-YaRN `attn_factor` 1.1 also 4.4e-2. The chunk-KV self-check regression on a YaRN tiny model remains to run once the fix is in a build.
  - [ ] **KPF-62.2 — Extend `chunk_kv.py` for KPF-62 G1/G3 records.** Add `KPF-62` to `PROGRAMS` and the `shift_exactness` and `approx_gate` kinds (value re-derived from recorded per-position payloads, direction per metric), with a fixture that grades; coordinate with the owner of VB-KVCHUNK-WRITE. Acceptance: a G1 fixture row from the tiny-model run grades through the shared ladder.
  - [ ] **KPF-62.3 - selector** (head window W=64 + check-layer K deviation + group-contiguous runs; then auxiliary-model scoring, needs a K tap at a check layer). Fresh agent. Filed 2026-10-21.
  - [ ] **KPF-62.4 - sparse recompute** by explicit-position batches beside the cache-reuse block; G0 at r=100% bit-identical. Fresh agent. Filed 2026-10-21.
  - [ ] **KPF-62.5 - server wiring**: `--chunk-store-mib` (0 = off), `kv_chunks` request field, isolated-encode on miss, startup self-check logged, `prompt.approx=true`, ctx_dft/MTP/DFlash2 coverage. Fresh agent. Filed 2026-10-21.
  - [ ] **KPF-62.6 - G3 harness on the frozen corpus** (needs the corpus manifest hash in P0_THRESHOLDS section 8). Fresh agent. Filed 2026-10-21.
  - [ ] **KPF-62.7 - speed report vs tuned prefill including load** (timing window). Filed 2026-10-21.
  - [x] **KPF-62.8 - real-role G1** (Qwen3-VL-30B-A3B Q4_K_M f32 K/V, CPU bench quarter): `WINDOW_CONFIRMED=1 scripts/chunk-kv/run_g1_real_role.sh`. In the INFERENCE QUEUE (CURRENT-CAMPAIGN). Filed 2026-10-21.
    - 2026-10-22 (rulings-20261022) ticked: real-model re-run in `/mnt/raid0/llm/worktrees/qb2-chunkkv-g1-20261021/results/chunk-kv-g1-filler/run-20261022T110704Z/g1.log` gave `VERDICT G1a (inject == in-tree seq_add, bit-for-bit): PASS`; G1a at deltas 1, 17, 300 all `K bit-identical  V bit-identical  logits bit-identical`. `VERDICT G1-ref (pre-registered, ref = encode in place at delta; K/V <= 1e-6, logits <= 1e-5): FAIL (informational: CKV_G1_REF_INFORMATIONAL=1)`; see KPF-62.9.
    - 2026-10-21 (fillers-3c4ca599): registered as queue item `kpf-62-8-g1` (NOT armed): `test-chunk-kv` is not built; script lives in the chunk-kv experimental tree, not /workspace/scripts.
    - 2026-10-21 (queue-builders-2): build side made runnable. Worktree `/mnt/raid0/llm/worktrees/qb2-chunkkv-g1-20261021` (llama.cpp-experimental, branch experimental/chunk-kv-reuse-p1-20261021, tip `2e98e283e`: `run_g1_real_role.sh` now resolves `test-chunk-kv` from the BUILD_OK marker and has `--dry-run`; the scripts live in that tree's `scripts/chunk-kv/`, not `/workspace`). Build filler `kpf-62-8-build` is ARMED (grant-polling, runs `build_and_test_cpu.sh` under the filler's build claim, marker `/mnt/raid0/llm/tmp/qb2-kpf62-8/BUILD_OK`). The G1 run itself stays a bundle sub-row (needs an inference window); production trees untouched.
    - 2026-10-22 (kpf62-fix): **first run FAILED the pre-registered G1; root cause is the REFERENCE, not the inject.** Run `2026-10-22T10:54Z` on q0 (binary @ `2e98e283e`; log `/mnt/raid0/llm/worktrees/qb2-chunkkv-g1-20261021/results/chunk-kv-g1-filler/run-20261022T105437Z/g1.log`) gave G1 K NMSE 1.4e-3 / 1.5e-3 / 1.8e-3, V 6.4e-3 / 6.9e-3 / 7.8e-3 and logits 6.4e-3 / 5.4e-3 / 8.7e-3 at delta 1 / 17 / 300. All 9 failed checks were those three NMSE checks at each of the three deltas. The `unexpectedly reached end of buffer` line is the deliberate truncated-blob negative test of `test_off_identical`. It also prints on the passing tiny run, so it is not an overrun. Hypotheses 1 and 2 (serialised layout or row stride) are refuted by the same log, because the bit-exact check `v_inj == v_src` PASSED. V carries no position, so V NMSE 6e-3 against the reference can only be drift in the reference's own re-encode at delta. Hypothesis 3 (RoPE / YaRN) is refuted by layer-0 K NMSE 7e-15: the shift is exact, and this role has no YaRN. Mechanism: RoPE attention is translation-invariant only in exact arithmetic. In f32 the q.k of a chunk encoded at delta differs from the one encoded at 0 in the last ulp, and that propagates through the layers. A 48-layer Q4_K_M MoE amplifies it, because every matmul re-quantizes its activations to q8 blocks (an ulp on a rounding boundary flips a whole q8 step) and router top-k flips compound. That is why the drift is independent of delta (1.4e-3 at 1, 1.8e-3 at 300) and grows with depth (layer 1 2e-5, deep layers 2-7e-3). The tiny fixtures lack exactly this: they are 2 layers with f32 weights and 2 experts. Long-chunk tiny runs (n=512) show the same drift at 1e-20..1e-19 V NMSE, with the injected V still bit-identical. **Fix** (`experimental/chunk-kv-reuse-p1-20261021` @ `357f3117f`, pushed to `fork`, manifest V11-101): `test-chunk-kv` adds **G1a**, which compares inject at +delta with the same encode moved by the in-tree `llama_memory_seq_add` K-shift (the `--cache-reuse` path) and requires K, V and suffix logits to be **bit-identical**. G1a is always gated and isolates the plumbing on any weight type. It also prints the pre-registered G1-ref with a VERDICT line, the in-tree seq_add vs ref numbers (equal to inject vs ref), per-layer K and V NMSE and an ubatch-split floor. G1-ref gates unless `CKV_G1_REF_INFORMATIONAL=1`, which `run_g1_real_role.sh` sets by default. `build_and_test_cpu.sh` adds Q4_K_M tiny fixtures (qwen3, qwen3vlmoe) at a 512-token chunk as the regression. It also fixes a `nm -D | grep -q` SIGPIPE false "stale build" under pipefail, which is latent in both scripts. Tests (q1, build role, 11:06Z): all tiny models pass G1a bit-exact at delta 1/17/300 (llama, qwen3, qwen3vl, qwen3vlmoe, plus Q4_K_M qwen3 and qwen3vlmoe at n=512); qwen35 refuses cleanly; `test-server-chunk-store` passes. BUILD_OK `/mnt/raid0/llm/tmp/qb2-kpf62-8/BUILD_OK` records head `357f3117f`. Re-queued: the STOP file was set at 10:56Z and removed after the build, poller PID 1648273 is still polling, and workspace-58 was told the job is ready for a grant (19 GiB).
    - [x] **KPF-62.8a — read the re-run.** Acceptance: VERDICT G1a PASS (bit-identical K, V and logits) on the real role. Record the G1-ref numbers, the in-tree seq_add vs ref numbers, the per-layer V curve and the floor. If G1a differs on the real role, that IS an inject defect: reopen this item with the log. Filed 2026-10-22.
      - 2026-10-22 (rulings-20261022) ticked: VERDICT G1a PASS on the real role (inject bit-identical to in-tree `seq_add` in K, V and logits at offsets 1, 17, 300; NMSE 0). G1-ref still fails at about 1e-3..8e-3 (e.g. layer 47 K NMSE=2.224e-03, V NMSE=9.581e-03) and the in-tree `seq_add` shows IDENTICAL drift against that same reference, so the drift is the reference, not the inject. Run: `/mnt/raid0/llm/worktrees/qb2-chunkkv-g1-20261021/results/chunk-kv-g1-filler/run-20261022T110704Z/g1.log`.
    - [x] **KPF-62.9 — ruling: P0_THRESHOLDS amendment (c), the G1 reference definition (main).** The pre-registered G1 reference ("encoded in place at delta") cannot pass on a deep k-quant role with any implementation, the in-tree K-shift included. Options: (A, recommended) G1 = inject vs the in-tree seq_add K-shift of the same encode, bit-identical. The in-place-at-delta drift is reported as an ungated "translation drift" figure and belongs to the G3 approximation budget (the naive r=0 baseline already measures it). (B) Keep G1-ref with a tolerance set from that drift (needs a frozen number; arbitrary). (C) Run G1-ref only on f32/f16-weight models, with real roles G1a-only. Tradeoff: A is exact and model-independent but changes the reference after data exists, so it must be recorded as an amendment with that fact stated. Proposed text is in `/mnt/raid0/llm/tmp/cacheclip-port-20261021/P0_THRESHOLDS.md` section 9 as "(c) PROPOSED". Until a ruling lands, the test reports G1-ref and gates only G1a on the real role. Filed 2026-10-22.
      - 2026-10-22 RULED by main: option A. G1 becomes bit-identity with llama.cpp's in-tree shift (G1a). The offset drift against in-place re-encode is reported ungated as "translation drift" under the G3 approximation budget. Rationale (verbatim): "the pre-registered G1-ref criterion is unsatisfiable by ANY implementation on a deep quantized model — llama.cpp's own seq_add path drifts identically — so it was a criterion defect, not a result; G1a is the strongest attainable correctness gate." Transparency: this criterion changed AFTER data existed (the first real-role run failed G1-ref); it is recorded as an amendment for that reason, and P0_THRESHOLDS section 9 is updated accordingly.
- [x] **KPF-63 — Correct the premise that `--cache-reuse` is force-disabled on recurrent memory.** Edit the two statements in this handoff (the line saying `--cache-reuse` is force-disabled for recurrent memory, and the line saying CacheBlend, `--cache-reuse` and non-prefix reuse are impossible with recurrent state) to record the corrected facts: at the champion `llama_memory_hybrid::get_can_shift()` returns true (`llama-memory-hybrid.cpp:133`), so the server does not disable `--cache-reuse` on hybrids; no production role sets the flag; the engine defect is CH-21; and non-prefix reuse on hybrids is under test in KPF-60, not impossible. Acceptance: both lines carry the correction with a pointer to CH-21 and the design document. Estimate: 0.1 day. ✅ 2026-10-21
- [ ] **KPF-64 — Replay real agent-trace sessions through the hybrid slot cache to measure prefix-hit reliability (the higher-payoff lever).** The measured traces (1,519 Claude Code transcripts plus sampled Codex and opencode sessions) say an ideal never-evicted prefix cache would capture about 98.7-99.2 percent of prompt tokens and chunk reordering adds well under 1 percent, so for append-ordered agent traffic one lever, running in parallel with the chunk-reuse infrastructure and not instead of it, is making the prefix cache hit reliably on our hybrid models: recurrent-state checkpoints at block boundaries (KPF), the `--cache-ram` tier and the eviction policy. Replay 20 sessions from the transcript stores (outputs regenerated live, concurrency equal to the slot count, the named trigger of the earlier replay monitor is now met by this load) against one hybrid role with checkpointing on and off and `--cache-ram` sizes, and report uncached prefill tokens per request against the ideal-cache bound. Build cost: a transcript-to-request adapter for llama-server (0.5-1 day). Needs a timing window and proof of the served binary (`verify_ggml_linkage.sh`, VRAM sampled during the run for GPU roles). Acceptance: a table of realised versus ideal prefix-hit share per configuration with the eviction events counted; the gap and its causes named. Estimate: adapter 1 day plus first run 1 day.
  - 2026-10-21 (fillers-3c4ca599): registered as queue item `s5-kpf64-replay` (NOT armed): replay harness not landed (adapter, driver, arm launcher, analysis all missing).
  - 2026-10-21 (queue-builders-2): harness BUILT (research repo `scripts/benchmark/kpf64_replay/`, commit `dcd6d5be7` on lane/qb2-kpf64-20261021): transcript adapter for the Claude/Codex/opencode stores, window-gated resumable replay driver, arm launcher (kernel-store binary, linkage proof, own PID), bootstrap analysis, `PREDECLARED.md` (arms A-D = ctx-checkpoints x `--cache-ram`, N=20, rule = paired CI excludes 0 and >0.5 pp), 14 tests, no-inference dry-run (ideal bound of the 20 sampled sessions 94.2%, below the study's 98.7-99.2% because short sessions are included). Class decision: filler (own server, token-count metric, needs no stack). Ready, arm command in the FILLERS.md row; NOT armed because the arm call was refused by the auto-mode classifier. Remaining: first live arm (calibrates the inferred-eviction tolerance).
  - [ ] KPF-64.1 repoint the replay adapter (`scripts/benchmark/kpf64_replay/adapter.py`, research branch `lane/qb2-kpf64-20261021`) at the operator-ruled read-only sources: opencode from `/mnt/raid0/llm/opencode-db/{epyc,host-daniele}.db` via `?mode=ro` + `query_only` (it currently opens the LIVE `~/.local/share/opencode/opencode.db`, which the 2026-10-22 ruling forbids), and add the vault `{host,twyne,epyc}/{claude,codex}` as extra Claude/Codex sources tagged by `source`. Reuse `open_ro` and `OPENCODE_RO_DBS` from root `dh_sources.py`. Explicit decline for the live `~/.claude` and `~/.codex` JSONL: append-only read-only reads are harmless and the replay wants the current container's sessions, so keep them as an additional source. Zero compute; the stratified N=20 sample must be redrawn per-source after the change (seed 64 unchanged). (f8 wrap-up 2026-10-22)
    - *(2026-10-22, correction by workspace-f8.)* The opencode half is already DONE on research main: the lane (9df45f4db) was merged earlier and main's adapter was repointed in the opencode-ro change (`OPENCODE_RO_DBS` + `refuse_live_opencode_path`, research 6616dcb9d-era). Remaining: add the vault Claude/Codex sources as an optional input (live `~/.claude`/`~/.codex` JSONL stays as the default source, read-only).

## Research intake 2026-10-21 — DeepSeek V4.1-Flash deployment commentary (intake-2214..2223, see research/intake_index.yaml)

Operator-approved 2026-10-21 via research intake (plan sha256 recorded in the session's stage3_filing).

**Dormant trigger (no checkbox, no index next action):**

- XP-A9/XP-A10 (intake-2214#10, #11): monitor: a fleet-wide prefix-to-instance index (KPF-27's per-server radix index keyed by instance; router-owned, since llama-server emits no KV events) as the affinity input for frontdoor instance selection, or alternatively a shared host-RAM prefix store (the single-host analogue of a Mooncake pool, intake-472). Trigger = WP-15 arm (d) shows the re-prefill fraction on returning sessions >= 0.25 under the current sticky rule AND KVU-12 keeps the multi-instance frontdoor (a unified-KV single server makes both moot). Price both at that time, not before.

## KPF-60 P0 GPU stages armed for the 2026-10-22 D4g window — overnight-gpu-arm, 2026-10-21
- Chunk-KV P0 GPU stages (MI210 prefill rate pp512/2048/8192 per role on the 27B Q8, RAM->GPU PCIe copy, NVMe chunk-load) are armed as a self-starting launcher: `/mnt/raid0/llm/tmp/overnight-gpu-arm-20261022/launch_job.sh job1` (body `job1_p0_gpu.sh`, script `/mnt/raid0/llm/tmp/cacheclip-port-20261021/p0_timing.sh`).
- Start: when `/mnt/raid0/llm/tmp/kvu12-redo-20261021/GPU_ALLOWED_FROM` and f8's `/mnt/raid0/llm/tmp/pb-qcost-1/PB_QCOST_1_ENDED` both exist (planned ~02:45Z). Hard stop 04:15Z. Flags and record: `$D/runs/job1/{DONE,FAILED,run_record.json}`; results `$D/runs/job1/out/`.
- Claim: `flock` on `gpu_device.mi210_0.lock` plus `region-lock run --gpu-quiet shared --role build`, no CPU region lock (agreed by f8 via 5c); host threads 184-191, membind 3. Every rep is labelled "GPU job beside f8 s4": indicative, not decision-grade.
- Build measured: champion `gpu-20261020-dd3d9721c` (version 10345), ggml linkage verified. The CPU-timing stages (`cpu_pp`, `memcpy`) are NOT in this run and still need the 06:30Z-onward quiet slot.
- Dies on host reboot; nothing re-arms it.
- 2026-10-22 (overnight-fix): the launcher above FAILED at 22:01Z with rc=64 (`region-lock run needs --regions, --cpu-list and/or --gpu-quiet`): with `D4_GPU_FREED` present `launch_job_v2.sh` ran `region-lock run --role build` with no claim flags, a branch its dry run never exercised. Superseded by grant-polling filler `kpf60-p0-gpu` (class block-timing-quiet; `filler_run2.sh --gpu-quiet exclusive --role timing --claim-cpus 184-191`, the p0_timing.sh gpu_pp claim; ~20 min, min window 30 min; resumable per stage; PID 435445; registry row in FILLERS.md; arm script `/mnt/raid0/llm/tmp/overnight-gpu-arm-20261022/arm_fillers.sh`). Claim argv proven against the real region-lock (reaches acquisition, times out only on the DS41 exclusive holder) and a fake-RL filler dry run. `launch_job_v3.sh` (fixed fallback) kept, not armed. Needs a grant from workspace-58 (asked for 14:30-18:00 or after 21:45).
## Research Intake Update — 2026-10-21 (harness cluster, DP-F amendment)

Operator-approved Stage-3 amendment (plan sha256 2edfb0662f61e1254e7dc5e2b21888ef4f19df800a283e82b25caebeb6644746). Durable records only: no checkbox, no index next action. Each monitor row carries its trigger and first step; each knowledge row states what to rely on. Ledger ids (DPF-...) key to the Stage-3 recommendation mapping preserved in `.research-session.json` (`stage3_filing`).

### K13 — KV, prefix-cache, prompt-layout and chunk-reuse evidence

- DPF-W1-CACHE-C1 (intake-2230): Up-to-80% saving is GPT-5.2/Claude, 10k-token system prompt, vs a UUID-forced-miss baseline, at list prices (cached input 0.1x). Abstract TTFT range (13-31%) disagrees with Table 1 (6.1-30.9%).
- DPF-W1-CACHE-C2 (intake-2230): Layout rules: no timestamps/session ids in the system prompt; unavoidable dynamic content at the END of the system prompt; exact-prefix match is all-or-nothing.
- DPF-W1-CACHE-C6 (intake-2230): Provider minimum token thresholds (1,024-4,096) and TTLs gate benefit; below threshold no benefit.
- DPF-W1-CACHE-C7 (intake-2230): Benefit scales with cacheable prefix length (linear in prompt size), flat in tool count.
- DPF-W1-CACHE-C9 (intake-2230): Credibility discipline: PwC-authored preprint, forced-miss baseline, n=40, TTFT from one-shot API latency with acknowledged server noise, no accuracy measure.
- DPF-W1-OOAGENTS-N1 (intake-2245): The paper has no L0-L3 state-cache hierarchy and no 'agentic garbage collection' (grep: zero hits). That vocabulary is intake-1313's. NOOA's own state tiers: method-scoped REPL locals, fields on self…
- DPF-W1-OOAGENTS-N2 (intake-2245): Persistence contrast: NOOA REPL locals vanish at method return; durable state is in-process self fields plus a memory store. Full-text search finds no checkpoint, restore, lease, crash or idempotency…
- DPF-W1-OOAGENTS-N6 (intake-2245): SWE-bench token claim: 82.2% at ~28 calls / 1.1M tokens vs OpenCode 78.6% at ~1.3M vs PI 78.2% at 66 calls / 2.2M. Attribution to pass-by-reference is asserted; harnesses differ in tools, prompts, co…
- DPF-W1-OOAGENTS-N7 (intake-2245): Validated termination: typed TaskResult (root cause, evidence, verification command) must validate or the loop continues; 77% of OpenCode's failed GPT-5.5 Terminal-Bench trials stop within ten steps.…
- DPF-W1-OOAGENTS-N8 (intake-2245): Memory design points: injection runs retrieval with touch=False so surfaced memories do not inflate usage activation; typed kind:key references resolved against live state at recall, returning a live…
- DPF-W1-OOAGENTS-N10 (intake-2245): Convergent spill-to-reference designs in other harnesses (Hermes: oversized output spilled to a file and replaced by preview plus dereferenceable path; Deep Agents: evicted to /large_tool_results/ pa…
- DPF-W1-OOAGENTS-N11 (intake-2245): Running model code in-process needed a per-cell Landlock/seccomp sandbox, uid drop, alias anonymisation and hard cell timeouts; the AST cell guard has a documented evasion gap (dynamic attribute look…
- DPF-W1-OOAGENTS-N12 (intake-2245): Fan-out in plain Python: the model defines an ellipsis-body @strategy function inside a cell and asyncio.gather()s it over a batch; sub-task must be strictly simpler than the current call to bound re…
- DPF-W2-MANUS-1 (intake-2276): KV hit rate top metric; 100:1
- DPF-W2-MANUS-3 (intake-2276): append-only context
- DPF-W2-MANUS-5 (intake-2276): file system as restorable context
- DPF-W2-MANUS-7 (intake-2276): keep errors in context
- DPF-W2-MANUS-8 (intake-2276): serialization variation vs few-shot rut
- DPF-W2-MANUS-9 (intake-2276): cache breakpoints/session routing
- DPF-W2-OOAGENTS-REPO-OR1 (intake-2280): Pinned paper revision 59ae56bf47af7582990355ad5312da098713c8f4 (2026-07-01) is absent from the public history, which starts 2026-07-20 as one squashed commit; run results are gitignored. Paper number…
- DPF-W2-OOAGENTS-REPO-OR2 (intake-2280): memory touch flag: retrieval(touch=True) default; spontaneous recall passes touch=False so passively injected memories are not reinforced (usage signal not distorted by the harness).
- DPF-W2-OOAGENTS-REPO-OR3 (intake-2280): ARC example runs the agent process inside a user+mount+network namespace (bwrap, else unshare), LLM access via an out-of-namespace Unix-socket broker, game data never mounted.
- DPF-W2-OOAGENTS-REPO-OR4 (intake-2280): AST checks plus module deny-lists are labelled by the authors as guardrails, not containment.
- DPF-W2-PROMPTCACHE-P1 (intake-2283): Position half is done by --cache-reuse in v10 (server-context.cpp:3323-3386, draft ctx too), default 0, off on all live roles because all are hybrid/recurrent; K-shift path had 3 confirmed defects (Y…
- DPF-W2-PROMPTCACHE-P2 (intake-2283): Prompt Cache and --cache-reuse use DIFFERENT approximations: module KV encoded with no preceding context (block-diagonal) vs chunk KV computed under the old context with positions corrected. Neither…
- DPF-W2-PROMPTCACHE-P3 (intake-2283): Table 1 "comparable" hides Passage Retrieval -43%/-28% relative (7B/13B) and TriviaQA down in 4/4 models; single greedy run, no variance.
- DPF-W2-PROMPTCACHE-P5 (intake-2283): TTFT-only benefit; decode per-token unchanged; memcpy 3.8-5.3 ms per 5K tokens is negligible vs prefill.
- DPF-W2-PROMPTCACHE-P8 (intake-2283): Stored-KV memory cost is GB per 1K tokens at 70B scale.
- DPF-W3-BLOCK-ATTENTION-B1 (intake-2295): Mechanism = block-diagonal prefill (positions reset to 0 per block, RoPE-rotated to real offset, last block attends all). Needs a block-FINE-TUNED model; training-free drops RAG avg 66.1 to 49.9.
- DPF-W3-BLOCK-ATTENTION-B2 (intake-2295): Own-paper inconsistency: text says gap to full-attention <=1%; Table 1 HQA gap is 2.5 pts (72.3 vs 74.8), avg 70.0 vs 71.3. Also '16.2% drop' is vs Tulu3-SFT not Tulu3-RAG (21.4).
- DPF-W3-BLOCK-ATTENTION-B3 (intake-2295): Wave-2 DIVE said it benchmarks CacheBlend; it does NOT (only PromptCache and Superposition, both collapsing 30-60 pts). Prompt Cache baseline setup unspecified.
- DPF-W3-BLOCK-ATTENTION-B4 (intake-2295): TTFT 3638 to 45 ms at 32K excludes KV load cost (footnote 4). On CPU-resident serving load is a RAM memcpy, so the exclusion is smaller here than on GPU, but the headline is still not a measured end-…
- DPF-W3-BLOCK-ATTENTION-B5 (intake-2295): Port to llama-server: server-context.cpp:3323-3386 --cache-reuse only shifts chunks from the SAME slot own previous prompt; it cannot import independently encoded chunk KV. Block prefill is expressib…
- DPF-W3-CACHECLIP-C1 (intake-2297): Quality is lossy even best case: 85.2% NIAH / 91.1% LongBench of full attention at 20% recompute; at 16K baselines 58 vs CacheClip 72.9-75.4 (full not stated in text read). Independent (Intel) confir…
- DPF-W3-CACHECLIP-C2 (intake-2297): CacheBlend (their reimplementation) gets WORSE as recompute rises 5 to 80% on single2/single3 because partial entity-token recompute corrupts values; grouping fixes it (RULER 40.47 to 81.28).
- DPF-W3-CACHECLIP-C4 (intake-2297): Port to llama-server with hybrid models: no. Needs sparse-query recompute (authors needed a Triton sparse-query FlashAttention kernel; llama.cpp prefill takes explicit per-token positions so a recomp…
- DPF-W4-INFERENCE-PERF-I4 (intake-2330): Comparability checklist (ignore_eos, fixed output, sampling, warmup, token counting).
- DPF-W4-CONCAT-FT-RECOMPUTE-D1 (intake-2326): Fine-tune and recompute stack (+9.7 at 124k) but neither closes the gap; combined still -24 pts
- DPF-W4-CONCAT-FT-RECOMPUTE-D4 (intake-2326): TTFT claims must be re-baselined against FA2/native kernel and include load cost before being cited

### M22 — KV, cache and serving-measurement follow-ons

- DPF-W1-OOAGENTS-N4 (intake-2245): Previews induce blind generalisation in small models: GPT-5.4 Mini fitted keyword rules to the 25 visible of 50 texts and applied them to all 50 (wrong); GPT-5.5 deliberately defeated the preview by… — Trigger: D-h preview rendering is implemented. Then run a 50-item batch task with a preview showing only half the items on the served worker role and count (a) blind rule-fitting, (b) retyping loss; both are inference, so they take their o…
- DPF-W2-MANUS-4 (intake-2276): mask not remove tools — If C3 shows tool-block divergence at a served role, test llama-server grammar/logit_bias gating.
- DPF-W2-MANUS-6 (intake-2276): todo.md recitation
- DPF-W2-PROMPTCACHE-P7 (intake-2283): PML tags (module, union, param) are in-band markup; if module markup were built from untrusted text, tag spellings need neutralising. control_tokens.py only neutralises chat special-token spellings. — Trigger: any schema or module markup assembled from retrieved or user text.
- DPF-W3-CACHECLIP-C3 (intake-2297): Auxiliary-model-guided selection: 135M-0.5B model last-layer attention picks the primary important positions better than primary layer 1 (Jaccard 0.28-0.41 vs 0.11-0.23 in rows read). Cross-family on… — Trigger: if any compaction arm needs a query-aware span scorer, evaluate a small CPU model last-layer query-to-span attention as the scorer.
- DPF-W4-INFERENCE-PERF-I6 (intake-2330): Prometheus-based server metrics are vLLM-specific. — Build: map llama-server /metrics names into the report (~1 day) when a run needs server-side queue/KV series.

### Research intake 2026-10-22 — Locals + Beacon (intake-2386..2460)

- [ ] **KPF-LB1 — Tabulate cache_n/prompt_n by role x endpoint (/completion vs chat) x turn index for hybrid roles; if rebuilt /completion turns re-prefill from near zero (v10 fills message_delimiters only on the chat path), add message_delimiters to orchestrator /completion payloads behind a flag so v10 checkpoints at a harness-chosen junction (intake-2386).**
  - *(2026-10-22, workspace-f8 / locals-a.)* Tabulated (branch `f8/locals-a-orch-20261022` (unmerged, not pushed), commit `80bdae83`, `scripts/analysis/kpf_lb1_cache_by_turn.py`, read-only). Chat path, hybrid roles, from opencode.db step records (cache_n = `tokens.cache.read`, prompt_n = `tokens.input`), by turn ordinal within session: **qwen-gpu (Qwen3.8-27B, :8083)** turn 1 token-weighted hit 0.032 (n=162, 85% cold), turn 2 median prompt_n 5,945 / cache_n 39,713 hit 0.696 with 19.8% of turn-2 steps below 10% cache, turn 3 hit 0.784 (24.7% cold), turns 4-5 0.878, 6-10 0.934, 11-20 0.948, 21+ 0.922; **qwen-local (Flash-Next)** turn 2 hit 0.976 and 0% cold from turn 2 on. So on the 27B chat path one turn in five to four still re-prefills from near zero at turns 2-3 while the Flash-Next path does not. The /completion x turn cell is NOT measurable from retained logs: `serving_calls` has no session or turn key, holds 8 `/completion` rows (coder_escalation, scratch port 18973, median prompt_n 518 / cache_n 2,086, 2 of 8 below 10% cache) and the llama-server logs carry neither role nor endpoint. The conditional (rebuilt /completion turns re-prefill from near zero) is therefore undecided, and the `message_delimiters` /completion flag is not added.
  - [ ] KPF-LB1.1 — controlled /completion vs chat comparison on a hybrid role: replay one captured 12-turn REPL transcript through the orchestrator's rebuilt-prompt /completion path and through /v1/chat/completions with `message_delimiters`, same slot, per-turn `timings.cache_n/prompt_n`; if /completion turns 2+ re-prefill below 10% cache while chat does not, add `message_delimiters` to the /completion payload behind a flag. NEEDS-COMPUTE spec: GPU :8083 (MI210, Qwen3.8-27B-Q8_0, ~33 GB VRAM, exclusive via the GPU window), host RAM ~12 GB, ~25 min, 1 server, no CPU quarter beyond the 2 GPU host threads. Rides with the next granted 8083 window.
    - [ ] prerequisite: capture one live 12-turn REPL transcript with full prompts (enable `replay_recording` or `INFERENCE_TAP_FILE` for one live orchestrator run; fits the operator's pending API reload). Launcher `locals-kpf-lb1-1-27b-completion-turns` armed in `/mnt/raid0/llm/tmp/f8-launchers-20261022/` is blocked on it.
- [x] **KPF-LB2 — Amend the transcript-replay harness before its first live arm: link sub-agent transcripts to their parents and replay bursts (parent paused, children concurrent) with a sessions>slots arm; emit think-time gaps with a scale knob; detect the opencode V1/V2 layout from sqlite_master (never read both for one session) and fail loudly on zero sessions; report the within-session and the cross-session-head ideal bounds plus the provider-realised cache share; compute our fan-out stats (child share of requests, peak concurrency) (intake-2417, intake-2418, intake-2435#record, intake-2437).** ✅ 2026-10-22
  - *(2026-10-22, workspace-f8 / locals-c.)* Amended before any live arm: research `c38ef247b` (+ `8b545b228` for the DS-LB1 ordering log) on the research branch `f8/locals-c-research-20261022` (worktree `/mnt/raid0/llm/worktrees/f8-locals-c-research`, unmerged, unpushed); `PREDECLARED.md` carries Amendment 1. Measured while amending: all 7 "claude" sessions of the original 20-session sample are SUB-AGENT transcripts (0 of 79 live top-level Claude transcripts pass the 200k-char replay cap), so flat mode keeps sub-agents as sessions (the sample is byte-identical to the pre-amendment adapter's on fixed disk state) and records each one's parent link; `--mode families` + `--children bursts` replay parent-paused bursts (non-replayable parents are virtual anchors). Store-wide fan-out of our traffic (`adapter.py --fanout-store`): 3,072 sessions, 1,963 sub-agents, child share of requests 73.6 %, peak 28 children under one parent, peak 44 concurrent lineages (span upper bounds). Sample reference: within-session ideal 93.4 %, cross-session-head 93.5 %, provider-realised cache share 93.8 %. Zero sessions now fail loudly (exit 4); opencode V1/V2 detected from `sqlite_master`, one layout per session. New follow-up arms E (sessions>slots) and F (bursts). 15 new tests, the original 14 unchanged. Environmental note: ports 18964 and 18971 had listeners on this host while testing, so `test_launcher_*` need `KPF64_PORT=31111`.
  - [ ] **KPF-LB2.1 — exercise the opencode V2 (`session_message`) reader on real rows: the live DB's V2 table is empty (V1 only), so the V2 path is fixture-tested against the projector's message shapes read from the installed opencode binary; the first migrated session must be checked by eye. No compute.**
  - [ ] **KPF-LB2.2 — recalibrate the E/F knobs (`--think-scale 0.1 --think-cap-s 60`, `--max-children 8`) at the first live arm and record any change in `PREDECLARED.md` before the result is read. Needs the KPF-64 timing window (CPU, 4-slot frontdoor 35B, ~40 GiB RAM, hours).**

Trigger-gated (no checkbox until the trigger fires):
- Prefix-stable template variant (if the render test fails), exact token-id replay (if the re-tokenization mismatch is material), shortest-remaining-first prefill among slots (if short-prompt TTFT under overlap shows a gap), post-reload trunk warm restore, cache-capacity-derived concurrency caps (intake-2386#record).
- Per-tool TTL from the Continuum argmax rule, session-keyed admission priority (arrival vs accumulated service time vs smallest-idle), a per-request retain hint on the experimental line, value-aware cache-ram eviction, the idle-gap timeout sweep and Preble-style cross-instance cost terms — open on the existing triggers: keyed-gap data at least 50 sessions per class, cross-session eviction at least 10%, or the prefix-cache-policy two-window rule (intake-2398#record, intake-2411#record, intake-2413#record, intake-2430#record).
- Public-trace scale arms for the replay harness (Weka v7, AIPerf cross-check, synthetic-content adapter) and the cch billing-header prefix note — open when our fan-out stats differ materially from the public set or a plan points Claude Code at llama-server (intake-2404#record, intake-2418#record, intake-2435#record).
