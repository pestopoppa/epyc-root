# KV prefix fork and paged attention: cross-slot prefix sharing, cache-aware dispatch, per-sequence KV views

**Status**: ACTIVE. Operator-approved program (2026-10-04: *"all sound like crucial features to fold into our
champion. We shouldn't be afraid of large efforts."*). Nothing is built yet; P0 and P1 are dispatchable now.
**Created**: 2026-10-04 (drafted for ak-ds41-main from the KV-serving survey)
**Priority**: HIGH. Four subagents with one 60k-token trunk prefill it four times today and hold four copies
(~180k cells, ~6 GB of the :8083 pool). Fan-out child TTFT is minutes when it could be seconds.
**Categories**: inference_serving, kv_cache, llama_cpp_experimental, orchestration
**Parent index**: [routing-and-optimization-index.md](routing-and-optimization-index.md) (row RTG-58, applied by the
owning session)
**Scratch**: `/mnt/raid0/llm/tmp/kv-prefix-fork/` · worktrees: `/mnt/raid0/llm/worktrees/kv-prefix-fork-*`
**Owners**: **workspace-ec** executes every phase: P1 server/KV side, P2 orchestrator side (as stack owner), P3, P4
and P5. **ak-ds41-main** keeps this handoff and its index row.
**Depends on**: RTG-57 [`kv-unified-stack-rollout.md`](kv-unified-stack-rollout.md) (KVU-19a/19b and the
prefill budget), RTG-27 [`prompt-construction-determinism.md`](prompt-construction-determinism.md) (byte-stable
prompts, load-bearing for P2), INF-65 [`autokernel-champion-aggregate.md`](autokernel-champion-aggregate.md) (the
ONE champion and the v11 candidate gate)
**Related**: INF-05 [`attention-matching-kv-compaction.md`](attention-matching-kv-compaction.md) KV-1/2/3/6 (the
orchestrator prefix-cache rows), [`agentic-serving-harness-fixes.md`](agentic-serving-harness-fixes.md) UFH14-B4
(`id_slot` pinning made opt-in), [`vidya-belief-substrate-program.md`](vidya-belief-substrate-program.md) (VB-KVU-*)

## Why this exists

Survey [`/mnt/raid0/llm/tmp/kv-serving-survey-20261004/REPORT.md`](/mnt/raid0/llm/tmp/kv-serving-survey-20261004/REPORT.md)
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
  [`/mnt/raid0/llm/tmp/kvu16b-rootcause-20261004/REPORT.md`](/mnt/raid0/llm/tmp/kvu16b-rootcause-20261004/REPORT.md)
  §4 fix 1). Once live, it is the production shape every gate here runs at. `--no-cache-idle-slots` keeps idle
  trunks resident, which gives P1 more fork sources and makes P2's unique-cell gate matter more.

## Start here

1. **KPF-01**: index a P1 experimental worktree with GitNexus (wrapper only), then run the KPF-02 impact pass.
2. **KPF-03**: file the belief-kernel wiring (VB-KVU-PF) before the first measurement record exists.
3. **KPF-11 → KPF-18**: build P1 on a fresh worktree from the current champion tip and run its gate.
4. In parallel with P1: **KPF-25** (byte-stable trunks) and **KPF-21** (trunk-first ordering). Both pay off with
   the existing `--cache-ram` copy restore even before the fork lands.
5. **KPF-30** (live-block fraction) can run as soon as KVU-19b's build exists. It needs no P1.
6. P4 waits on the v11 FA-path audit (`/mnt/raid0/llm/tmp/v11-fa-path-audit-20261004/REPORT.md`, in progress at
   drafting) and the v11 rebase. P5 waits on P1 and a rocprof profile.

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

## What already exists in our tree (v10 `ffc1bac82`, read-only line refs)

- `llama_kv_cache::seq_cp` (`src/llama-kv-cache.cpp:450-491`): in unified mode (`s0 == s1`) it adds the dst
  seq bit to every src cell in `[p0, p1)`. Zero copy. One O(n_cells) metadata pass, ~393k cells.
- `llama_memory_recurrent::seq_cp` (`src/llama-memory-recurrent.cpp:246-281`) **ignores p0/p1**. It makes dst share
  src's *current* tail cell. `llama_memory_hybrid::seq_cp` (`src/llama-memory-hybrid.cpp:152-155`) calls both
  halves, so a hybrid `seq_cp(src, dst, 0, p)` gives dst the correct attention prefix but src's state at its
  current end, not at p. **Never use hybrid `seq_cp` for a fork.**
- Context checkpoints (`create_checkpoint`, `tools/server/server-context.cpp:2365-2412`) save the
  non-rollbackable state with `LLAMA_STATE_SEQ_FLAGS_PARTIAL_ONLY`: the target's recurrent half
  (`llama-memory-hybrid.cpp:191-203`), the drafter's SWA cache (`llama-kv-cache-iswa.cpp:259-273`), and the
  DFlash2 speculative state (`common_speculative_get_state` → `cur.data_spec`). The placement policy is in
  `pre_decode` (L2984-3737, called from `update_slots` L2856-2965) ~L3562-3720: user-message starts (#24176), and
  `4 + n_ubatch` and 4 tokens before prompt end.
  Restore is at ~L3451-3480, on the slot's own checkpoints only.
- `server_slot::copy_state_to` (L735-757) does `seq_rm` + full `seq_cp` on `ctx_tgt` and `ctx_dft`. It is used only
  for `n>1` child tasks, and only from `SLOT_STATE_DONE_PROMPT`.
- `get_available_slot` (L1601-1705): it computes LCP similarity only over slots that are **not processing**, then
  falls back to LRU, then does a `--cache-ram` save/load **by copy**.
- Idle-slot purge (L2469-2484, `[TAG_IDLE_SLOT_CLEAR]`): with `cache_idle_slots` on and unified KV, each new task
  launch saves every idle slot to `--cache-ram` and `prompt_clear()`s it. **This runs after
  `launch_slot_with_task`**, so a fork whose source is an idle slot must be taken at launch, before this loop
  (KPF-14).
- `--cache-reuse` is force-disabled for recurrent memory (L1286-1301). Correct, and not a lever here.
- `find_slot` (`src/llama-kv-cache.cpp:901-1075`) is first-fit from `head` per ubatch (P3).
- Hybrid ubatch split (`src/llama-memory-hybrid.cpp:80-89`): `split_equal(n_ubatch, !unified, n_rs_seq + 1)`. The
  pure-KV path at `llama-kv-cache.cpp:716` uses `split_simple`. **Survey correction to verify in KPF-40:** survey §2.4
  finding 3 says #29510 cannot slice DFlash2 verify ubatches because unified KV uses `split_simple`. Our hybrid
  model goes through `split_equal`, and #29510's `get_n_kv_slices()` accepts `equal_seqs() && n_seqs == n_seqs_unq`
  (`pr29510.diff` L1080-1091). So verify ubatches (4 seqs × 8 rows) may slice after all. If so, P4 is worth more
  than the survey estimated.
- CPU paged-attention scaffolding from v5 (`src/llama-kv-block.h`, `GGML_OP_FLASH_ATTN_EXT_PAGED`,
  `tests/test-kv-block.cpp`): forward-ported in `0e485a91b`, reverted in `a4e2b4f86`. It is reusable block
  accounting for P3/P4, with no GPU kernel.

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
- [ ] **KPF-02: GitNexus impact pass on the P1 worktree.** Run `context` + `impact --direction upstream` on
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
- [ ] **KPF-04: compile the radix lesson (above) into `wiki/kv-cache.md`** at the first wiki sweep after KPF-18
  closes, including the KPF-18 result.

### P1: cross-slot prefix fork, server side (workspace-ec) — effort M-L, ~2-3 weeks including the gate

Target: a new task whose prompt shares a long prefix with **any** slot, busy or idle, starts from a zero-copy fork
of that slot's attention cells plus a checkpoint-restored recurrent and drafter state at the fork position. It
prefills only the suffix.

- [ ] **KPF-11: cross-slot fork-source selection.** Add `find_fork_source(task)` to `server_context_impl`, called
  from `get_available_slot` (L1601) / `launch_slot_with_task`:
  - For every slot ≠ dst, **busy ones included**, compute `lcp = slot.prompt.tokens.get_common_prefix(task.tokens)`.
  - Fork position `p` = the largest checkpoint in that slot's `prompt.checkpoints` with `n_tokens ≤ lcp`, or the
    slot's exact end if the slot is idle with `n_tokens == lcp`.
  - Require `p < task.tokens.size()`, so at least one token is processed (`[TAG_PROMPT_LOGITS]`).
  - Pick the largest `p` across slots. Ties: idle source first, then most recent. Compare against the dst slot's
    own LCP/checkpoint and the `--cache-ram` best hit, and take the largest reuse.
  - Threshold: new argv `--slot-fork-min-tokens N` (0 = off, the A/B control). Default chosen in KPF-18.
- [ ] **KPF-12: attention-only zero-copy share.** Add an explicit attention-only copy so the recurrent half is never
  aliased: `llama_memory_seq_cp_ext(mem, src, dst, p0, p1, flags)` with an `ATTN_ONLY` flag. Touches
  `include/llama.h`, `src/llama-memory.h` (`llama_memory_i`), `src/llama-memory-hybrid.cpp:152`, `src/llama-context.cpp`
  (API) and `common/common.cpp` (`common_context_seq_cp`). Sequence: `seq_rm(dst, -1, -1)`, then
  `seq_cp_ext(src, dst, 0, p, ATTN_ONLY)`.
  - Rejected alternative: hybrid `seq_cp` followed by a checkpoint load into dst. Recurrent `seq_cp` makes dst
    share src's tail cell, so the following `state_read` could write src's live state unless it copies on write.
    That is an aliasing window with no test that would catch it.
- [ ] **KPF-13: recurrent and drafter state from the checkpoint.** Into dst: `ckpt.load_tgt(ctx_tgt, dst.id,
  PARTIAL_ONLY)`, `ckpt.load_dft(ctx_dft, dst.id, PARTIAL_ONLY)` (the drafter's SWA window travels in the
  checkpoint, `llama-kv-cache-iswa.cpp:259-273`) and `common_speculative_set_state(spec, dst.id, ckpt.data_spec)`.
  Then set `dst.prompt.tokens = task.tokens[0:p]`, clone the source checkpoints with `n_tokens ≤ p` into
  `dst.prompt.checkpoints`, set `n_past = p`, and prefill from p. Positions are unchanged, so no shift.
  - Verify in code and in a test that `llama_memory_recurrent::state_read` for dst allocates or uses **dst's own**
    rows: 4 slots × 8 rows with the rollback ring, `n_rs_seq`. It must never write a cell src still references.
- [ ] **KPF-14: launch ordering and seq-bit safety.**
  - Take the fork at launch, before the `[TAG_IDLE_SLOT_CLEAR]` loop (L2469-2484), so an idle source is not
    cleared first.
  - Confirm `prompt_clear()` / `seq_rm(src, -1, -1)` on a source removes only its own seq bit: a cell is freed only
    when its last bit goes, and `used` stays right.
  - Cover `cache_idle_slots` on AND off, because production flips to `--no-cache-idle-slots` with the in-progress
    package.
- [ ] **KPF-15: explicit junction checkpoint, request field `checkpoint_at`.**
  - Format: an array of token positions; `-1` means end of prompt. Parse it in `tools/server/server-task.cpp`.
  - In `pre_decode` (~L3640-3720), end a prompt chunk exactly at each requested position and create a checkpoint
    there, regardless of `checkpoint_min_step`.
  - Mark such checkpoints `pinned`, so the erase loops in `create_checkpoint` (L2370-2394) never evict them, and
    carry them through `prompt_save`/`prompt_load` (`server_prompt_cache`, `server-task.h`).
  - This is vLLM's `--enable-mamba-shared-prefix-checkpoint` and SGLang's branch-point caching, on demand.
  - Snapshots stay sparse: one costs ~150 MiB, about 4.4k tokens of KV (survey §1.3).
- [ ] **KPF-16: fork telemetry.**
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
- [ ] **KPF-19: rebase watch.** `server-context.cpp` is upstream's most-churned file. At the v11 rebase,
  re-verify KPF-11..16 against the new `update_slots`/`pre_decode`, re-run KPF-17 and a reduced KPF-18 (items 1, 3, 6).

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
- [ ] **KPF-25: byte-stable trunks.** Audit the fan-out prompt builders for anything that varies across siblings
  inside the trunk: ordering, timestamps, ids, per-child text placed before the junction. Use the RTG-27
  prompt-construction-determinism findings. Add a test that N children's prompts share a byte-identical trunk of the
  expected length (the UFH14-B4 `prefix_fp` ladder).
- [ ] **KPF-26: P2 gate.** Replay a real fan-out (an HS-19 scouting round or a delegate wave) through :8000 on the
  P1 build: trunk prefilled once (server `timings`), child TTFT, peak unique cells, admission waits, and **task
  outcome unchanged** on the replay set vs the pre-P2 path. Two windows; records under VB-KVU-PF.

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

**Gated on the #26046 v11 FA-path audit** (`/mnt/raid0/llm/tmp/v11-fa-path-audit-20261004/REPORT.md`, in progress
at drafting). v11 moves verify and prefill from rocWMMA onto MMA/MFMA (upstream removed the rocWMMA FA in #26046,
2026-07-24), which changes where 19a/19b and `kv_rows` live. Diff on hand:
`/mnt/raid0/llm/tmp/kv-serving-survey-20261004/pr29510.diff`.

- [ ] **KPF-40: pre-check (read-only, zero compute).** Read the v11 audit. Re-derive which of our ubatch shapes
  `get_n_kv_slices()` accepts on the **hybrid** split (`llama-memory-hybrid.cpp:89`, `split_equal`), which may
  overturn the survey's "verify falls back" finding (see the survey correction above). Re-check #29510's state:
  merged, reshaped by the Metal objection, or still a draft. Write the port plan into this handoff.
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

- **llama.cpp** (reference lines at v10 `ffc1bac82`; edit only in the phase worktree):
  - `tools/server/server-context.cpp`: `copy_state_to` L735, `get_available_slot` L1601, `create_checkpoint`
    L2365, the idle-slot purge L2469, `update_slots` L2856, `pre_decode` L2984
    (checkpoint restore ~L3451, placement ~L3562-3720).
  - `tools/server/server-task.{h,cpp}` (request params, `server_prompt_cache`, checkpoints).
  - `src/llama-kv-cache.cpp` (`seq_cp` L450, `find_slot` L901, `apply_ubatch` L1100, `set_input_kq_mask` L1757);
    `src/llama-kv-cells.h`.
  - `src/llama-memory-hybrid.cpp` (split L89, `seq_cp` L152, state L191); `src/llama-memory-recurrent.cpp`
    (`seq_cp` L246); `src/llama-kv-cache-iswa.cpp` (state L259).
  - `src/llama-context.cpp`, `include/llama.h`, `common/common.cpp`, `common/speculative.{h,cpp}`
    (`common_speculative_{get,set}_state`).
  - `src/llama-graph.cpp` (`build_attn_mha` L2533).
  - `ggml/src/ggml-cuda/fattn-{common.cuh,vec.cuh,wmma-f16.cu,mma-f16.cuh}`.
  - Tests: `tests/test-save-load-state.cpp`, `tests/test-state-restore-fragmented.cpp`,
    `tests/test-recurrent-state-rollback.cpp`, `tools/server/tests/unit/test_slot_save.py`,
    `tools/server/tests/unit/test_speculative.py`.
- **Orchestrator**: `src/scheduling/kv_pool_admission.py`, `src/scheduling/prefix_history.py`,
  `src/inference/prefix_cache.py`, `src/api/routes/chat_pipeline/scout_stage.py`, `src/parallel_step_executor.py`,
  `src/typed_decisions/fanout_policy.py`, `src/api/routes/delegate.py`, `src/backends/serving_calls`.
- **Evidence and inputs**: the survey (`/mnt/raid0/llm/tmp/kv-serving-survey-20261004/REPORT.md`, `pr29510.diff`);
  the KVU-16b root cause (`/mnt/raid0/llm/tmp/kvu16b-rootcause-20261004/REPORT.md`); the KVU-19a fold record
  (`docs/design/fa-masked-block-skip-20261003-fold.md`).

## Not filed here (explicit)

- **vLLM/SGLang on the MI210 for this role.** Not a production path (survey §5: gfx90a degraded tier, #25030, no
  FP8, no GGUF path for this hybrid). A ≤1-day reference probe is the operator's call. It is not filed.
- **CacheBlend / `--cache-reuse` / non-prefix reuse.** Impossible with recurrent state.
- **Per-slot split KV (KVU-16d option c).** Decided "keep shared 393k" in RTG-57. Its reopen trigger lives there.
- **#28532 `--slot-linger-ms`.** KPF-23's session-continuity pinning covers the same effect from the orchestrator.
  Cherry-pick it only if KPF-26 shows session turns losing their slot.

## Reporting

Flip boxes here. The owning session (ak-ds41-main) updates RTG-58's `Next action`; workspace-ec reports phase
boundaries to it on the bus. Append to `progress/YYYY-MM/`. Production default-on of any feature goes through the
kernel-promotion ratification, not this handoff.
