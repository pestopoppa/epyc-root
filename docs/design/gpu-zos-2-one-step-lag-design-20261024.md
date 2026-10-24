# GPU-ZOS-2: one-step-lag async scheduling on the np4 DFlash2 :8083 shape (experimental-branch design)

- **Status:** DESIGN. Gates predeclared 2026-10-24, before any code or build. Nothing here has been built or run.
- **Item:** GPU-ZOS-2 in `handoffs/active/gpu-serving-tie-in-program.md`, opened by the GPU-ZOS-1 rule (intake-2116#record, intake-2126#record). Author: workspace-f8 subagent.
- **Input grade:** INDICATIVE. GPU-ZOS-1a measured a share under a DEBUG_TIMINGS build on a host that was not quiet. No t/s or ms figure below is a champion or :8083 baseline. Each one is used only to size a ceiling.
- **Code references** are to `tools/server/server-context.cpp`, `common/sampling.cpp` and `common/speculative.cpp` at champion `dcc853b55` (`ak/champion/llama-cpp-ffc1bac82eec`), read with `git -C /mnt/raid0/llm/llama.cpp show dcc853b55:<path>`. Between `49550eda5` (the base of the 1a DEBUG_TIMINGS branch `b5a524605`) and `dcc853b55`, `tools/server/` and `common/` are byte-identical (`git diff --quiet 49550eda5 dcc853b55 -- tools/server common` exits 0). The 1a numbers therefore describe the server code this design changes.

## 0. Summary

- **Finding.**
  - True one-step lag cannot work on this shape (option B). No row of step k+1's batch can be built before step k's verification sampling finishes. The next batch begins with the token sampled at the first mismatch, or the bonus token, and the DFlash2 draft is conditioned on that token.
  - Deferring the non-critical post_decode work (option A) is worth about 0.01% of a step. On the spec-OFF arm, everything in post_decode other than sampling measured 0.0045 ms/step.
  - The measured 5.17 ms/step splits into two halves:
    - about 2.57 ms/step of verification sampling. This is dependency-critical, and the figure is an estimate.
    - about 2.60 ms/step of spec-only bookkeeping. This half is unattributed. The leading suspect is a per-round sampler clone that copies a roughly 3 MB candidate buffer for each slot and, on this shape, is never used.
- **Recommendation: option C, one knob, three tokens.**
  - **C1 `lazy-save`.** Skip the unused sampler clone. Byte-identical by construction.
  - **C2a `greedy-fast`.** An exact greedy fast path for verify rows. It scans the raw logits for argmax and falls back to the full chain on a tie or a NaN, so it is exact by construction.
  - **C3 `overlap-process`.** The only genuinely asynchronous piece. It runs the DFlash2 feature injection (`common_speculative_process`) on a worker thread while the main thread samples the verify rows. These two depend only on step k's target outputs and never on each other.
- **Ceiling.** The ceiling is the measured host share: post_decode 5.17 ms of a 139.6 ms step, which is **3.71% of step time, or at most +3.85% decode tok/s**. Even that would need every host millisecond to vanish. Author estimate for C1 + C2a + C3 at temperature 0: 1.5-3%, unverified. This design claims nothing above 3.71%.
- **Gates (§9).**
  - Knob off is byte-identical to the champion.
  - Knob on gives byte-identical greedy completions with equal acceptance counts at np4 DFlash2, subject to the champion's own two-pass determinism control.
  - Speed is tested A/B/A/B against the champion image. A change ships only if the effect is at least max(1.0%, 2 × noise floor) and the sign agrees across every adjacent pair.

## 1. Problem and measured numbers

Source: `/mnt/raid0/llm/tmp/f8-launchers-20261023/gpu-zos-1a/`.

| File | sha256 (prefix) |
|---|---|
| `VERDICT.json` | `ac752fadc06bc915` |
| `PREDECLARATION.md` | `d38ce7dd9149ec28` |
| `out/share.json` | `82c727034f335434` |
| `out/server.log` | `d4c8e1a4bbc9de4f` |
| `RUN_RECORD.json` | `04046189fa5b9d27` |
| `AMENDMENT-residency-check.md` | `d703e617a75ad537` |
| `drive.py` | `3ec90db83d47b3e1` |

**Shape.** Qwen3.8-27B-Q8_0 (GGUF `general.architecture = qwen35`, a hybrid of Gated-DeltaNet and attention layers) with the Qwen3.8-27B-DFlash2-Q8_0 drafter.
- Drafter: `--spec-type draft-dflash --spec-draft-n-max 7`, block_size 8.
- Server: `-np 4 -c 393216 -b/-ub 512 -ctk/-ctv q8_0 --kv-unified --cache-ram 65536`, on ROCm0 with host threads 184-191.
- argv: the production launch record, as listed in `RUN_RECORD.json`.

| Arm | N steps (4-slot windows) | pre ms/step | decode ms/step | post ms/step | sampl ms/call | share post/(dec+post) | share incl. pre |
|---|---|---|---|---|---|---|---|
| spec ON (prod shape) | 802 | 14.944 | 119.498 | **5.175** | (not timed on this path) | **4.15%** (waves 4.08-4.28%) | 14.4% |
| spec OFF (`speculative.n_max: 0`) | 2808 | 0.001 | 58.204 | 0.873 | 0.2171 (11232 calls) | 1.48% (waves 1.36-1.57%) | 1.48% |

Derived figures. The arithmetic is in §6, using `share.json` and the 12 `draft acceptance` lines of `server.log`.

- ON full step = 14.944 + 119.498 + 5.175 = **139.62 ms**. The post share of the full step is **3.706%**.
- ON per-wave step time: 138.83 / 139.18 / 140.98 ms. The range is 1.55% of the mean, an INDICATIVE prior for the noise floor (§9).
- OFF post_decode is 99.5% sampling: 0.8684 of 0.8729 ms/step. **Non-sampling post work on OFF is 0.0045 ms/step**, about 1.1 µs per emitted token.
- ON mean tokens emitted per verify round ("mean len") is **2.961**, the average of the 12 measured requests (2.53-3.49). Acceptance is 0.22-0.36 at n_max 7.
- `common_sampler_sample_and_accept_n` samples the accepted drafts plus one row (the mismatch or the bonus), so it samples exactly mean len rows per slot-round.

### What the timers wrap

All refs are to `server-context.cpp` at `dcc853b55`.
- `update_slots()` is at :3234.
- `t_pre_decode` is at :3273. It wraps `pre_decode()` (:3374) and `batch.render()`. pre_decode covers the context-shift check, the drafting setup, `common_speculative_draft` (:3534, the DFlash2 drafter decode plus the host lattice selection), draft-checkpoint bookkeeping, and `handle_last_sampled_token` (:3586).
- `t_decode` is at :3309. It wraps `decode()` (:4160), which is `llama_decode(ctx_tgt)` (:4203) **plus `common_speculative_process` (:4264)**, and then the DEBUG-only `llama_synchronize(ctx_tgt)` (:3315).
- For DFlash, `process()` (`speculative.cpp:1522`) does three things:
  - reads the five extracted target hidden-state layers through `llama_get_embeddings_layer_inp`, which synchronizes ctx_tgt (`llama-context.cpp:4153-4154`);
  - gathers and sanitizes features on the host;
  - per sequence, runs `llama_encode(ctx_dft)` (:1623), then `llama_decode(ctx_dft, batch_inject)` (:1643), then `llama_synchronize(ctx_dft)` (:1651). That is 4 serialized drafter rounds per step at np4.
- Consequences:
  1. **t_decode is not pure target device time.** It includes the drafter's KV injection for every row, rejected rows included (`TAG_SPEC_AVOID_DRAFT_REEVAL`). This holds on the OFF arm too, where each sequence injects one row. The rule's share is what the predeclaration said to compute, so the verdict stands.
  2. **The DEBUG_TIMINGS synchronize is close to a no-op on this shape**, because `process()` has already synchronized ctx_tgt. The predeclared limit that the instrument "separates device and host time by construction" therefore perturbs this shape less than feared.
- `t_post_decode` is at :3335 and wraps `post_decode()` (:4451).
- `t_sampl` wraps only the non-speculative `common_sampler_sample` calls (:4523, :4324). The batched verify path (`common_sampler_sample_and_accept_n`, :4627/:4630) is not timed, so `n_sampl = 0` on the ON arm.

## 2. What post_decode does on this shape (dependency-annotated)

Engagement facts, from code plus the 1a log:
- **Target rollback type is RS, not FULL.** `qwen35` passes `llm_arch_supports_rs_rollback` (`llama-arch.cpp:1180-1189`). `need_n_rs_seq()` returns `draft.n_max` = 7 for DFLASH (`common.h:390-396`), so `n_rs_seq` = 7 and `common_context_can_seq_rm` returns `RS` (`common.cpp:1570-1573`).
- **No checkpoints.** n_rollback ≤ n_draft = 7 ≤ n_rs_seq, so `use_ckpt_tgt` is false in pre_decode (:3557) and in post_decode (:4657). RS rollback only moves a snapshot index (`llama-memory-recurrent.cpp:192-196`, `set_rs_idx`); it is host bookkeeping.
- **Batched verify, not serial.** `LLAMA_SPEC_EXACT` is unset and the drafter is DFLASH, not DSPARK, so `use_serial_speculative_verify()` returns false (:3347-3372).
- **Host sampling.** Backend sampling is disabled for speculating slots (:1917), and `llama_context::decode` refuses more than one output per sequence under a backend sampler (`llama-context.cpp:2079-2100`).
- **Full logits copy.** All 4 × (1 + 7) = 32 verify rows request logits, so every step copies about 32 × 248k × 4 B ≈ 31.8 MB of logits to the host. That copy sits inside t_decode. `mask_token_id` = 248070 in the log; .1 reads the exact `n_vocab`.

Per generating slot, in the speculative block of `post_decode` (:4567-4789):

| # | Work (ref) | Host cost on this shape | Needed by step k+1? |
|---|---|---|---|
| 1 | `smpl_save.reset(common_sampler_clone(...))` (:4613). This copies the chain, the `prev` ring, **and `cur`, the n_vocab-sized `llama_token_data` scratch buffer of about 3 MB** (`sampling.cpp:486-498`). | Unmeasured. A 3 MB alloc + copy + free per slot-round, ×4 per step. | **No.** `smpl_save` is read only on the checkpoint-restore path (:4690) and in `spec_exact_bonus` (:4367). Neither can run on RS with n_draft ≤ n_rs_seq and `LLAMA_SPEC_EXACT` unset. The clone is pure waste here. |
| 2 | `common_sampler_sample_and_accept_n` (:4627/:4630, `sampling.cpp:637-708`). Per row: `set_logits` fills about 248k entries, then the chain runs (penalties, dry, top-n-sigma are no-ops; top-k 40 partial sort; typical no-op; top-p; min-p; xtc no-op; temp 0 greedy; dist). Accepts each token. | ≈ 2.96 rows × 0.217 ms per slot ≈ **2.57 ms/step** (estimate: OFF per-call cost × ON mean len × 4) | **Yes, critical.** It decides the accepted count, `slot.sampled` (the next batch's row 0 and the drafter's `id_last`) and n_past. |
| 3 | `common_speculative_accept` (:4700). This is stats only for DFlash (`speculative.cpp:3340`; no impl override). | µs | Mutates spec impl state, so it must not race with `process()` (C3 join point). |
| 4 | Prompt-token bookkeeping, `slot.sampled` (:4723-4727). `common_context_seq_rm` on ctx_tgt and ctx_dft (:4730-4733): an RS index move on tgt and a KV trim on dft. | µs | **Yes.** It must precede the next `pre_decode` drafting and the next target decode, and the ctx_dft trim must follow `process()`'s injection (C3 join point). |
| 5 | Emit loop (:4735-4783): `common_token_to_piece`, `process_token` (UTF-8 check, stop strings, `send_partial_response` if streaming), `send_final_response` on stop. | ≈ 1.1 µs per token (OFF-measured), about 12 tokens/step → **≈ 0.013 ms/step** | Partly. `process_token` decides release (stop conditions) and so whether the slot is in batch k+1, and `n_decoded` feeds `get_n_draft_max`. The text work and the queue sends are not needed. |

Unattributed remainder: 5.175 - 2.571 - 0.013 ≈ **2.59 ms/step** (≈ 0.65 ms per slot-round). Candidates, ranked by author judgement:
- (i) row 1's clone. A 3 MB allocation above the glibc mmap threshold on a non-main arena can page-fault on every touch, and its free can munmap.
- (ii) the per-row `llama_synchronize` / `llama_get_logits_ith` call overhead.
- (iii) the chain clones' own allocations.

The DEBUG sub-timers in .1 (§10) attribute it. Until then the split is a hypothesis.

## 3. The dependency chain (why one-step lag is not free here)

Step k's critical path on the single MI210 stream:

```
pre_decode(k):  draft(k) needs sampled(k-1), n_past(k-1) and drafter KV injected through k-1
                -> build batch [sampled(k-1), d1..d7] per slot
decode(k):      llama_decode(ctx_tgt) -> process(k): sync ctx_tgt, then per seq encode+inject on ctx_dft, sync
post_decode(k): sample verify rows (logits of k) -> accepted(k), sampled(k) -> rollback tgt/dft to pos_next(k)
                -> emit
pre_decode(k+1) ...
```

- Every row of batch k+1 depends on `sampled(k)`.
- The drafter's input for k+1 depends on `sampled(k)` and on its KV having been injected through step k and trimmed to `pos_next(k)`.
- So nothing in step k+1's target decode or drafting can start before row 2 of §2 finishes.

The only device work in the step that does not depend on post_decode(k) is `process(k)`. It depends only on step k's target hidden states, which are fixed once `llama_decode(ctx_tgt)` completes, so it is the only overlap partner for post_decode(k)'s host sampling.

## 4. Design options

### A. Defer the non-critical post_decode work (emit, streaming, metrics, print_timings) past the launch of decode k+1, or onto a worker

- Mechanism: keep an inline guard for anything that changes batch membership (an EOG id check, the `n_decoded`/`n_predict` counters, and a slot release). Move `token_to_piece`, stop-string search, `send_*_response`, `metrics.on_prediction` and `print_timings_tg` to a host worker, or run them after `llama_decode(k+1)` has been queued.
- Ceiling: the emit work only. Measured on OFF at 0.0045 ms/step and scaled to about 12 tokens/step on ON gives about 0.013 ms/step, **≈ 0.01% of a step**.
- Cost:
  - A stop string found lagged leaves a slot running one extra step: wasted rows, plus extra tokens in the cached prompt (`--cache-ram 65536`). That changes `n_tokens_cached` in responses and the next request's LCP reuse.
  - Response ordering needs a per-task queue.
- **Verdict: rejected.** Its ceiling is two orders of magnitude below the minimum effect worth shipping (1.0%, §9), and it adds a correctness surface.

### B. True one-step lag: build and launch batch k+1 speculatively before step k's acceptance is known, and roll back on a miss

- Mechanism (vLLM-style async scheduling): guess `accepted(k)` and `sampled(k)`, build batch k+1, launch it, and on a miss discard it and roll back the KV/RS.
- Obstacle: row 0 of batch k+1 is `sampled(k)`, the target's own choice at the first mismatch or the bonus position. The host cannot know it without step 2 of §2. Guessing "full acceptance, bonus = drafter's next token" would also need a drafter pass that is itself conditioned on the guess.
- Hit-rate arithmetic: full 7/7 acceptance is rare. The mean of 2.96 emitted tokens per round means about 1.96 of 7 drafts accepted. A miss wastes a full verify step, about 120 ms of device time.
- The async form that does work, as in vLLM, feeds sampled ids back to the next step on the device, with no host round-trip. In llama.cpp that needs (a) multi-row backend sampling (C2b below) and (b) a device-resident input-token path in `llama_batch`/the graph, which is a new libllama API.
- For spec OFF the dependency is the same, and the OFF share of 1.48% is below 3%, so the GPU-ZOS-1 rule already closed it.
- **Verdict: rejected for this shape.** Recorded: B becomes possible only after C2b plus a device-input API, and is worth re-costing only if a later read shows host time in the inter-step gap above 3% after C1-C3.

### C. Remove host cost from the critical path, and overlap only what is truly independent (RECOMMENDED)

**C1 `lazy-save`: skip the unused sampler clone.**
- Mechanism: before row 2, compute whether a restore is possible for any acceptance count:

  ```
  need_save = serial_verify ? false
            : spec_exact in {drop, redecode}
              || ctx_tgt_seq_rm_type == FULL
              || (ctx_tgt_seq_rm_type == RS && n_draft > llama_n_rs_seq(ctx_tgt))
  ```

  This is the same predicate as `use_ckpt_tgt` (:4657) with worst-case n_rollback = n_draft. Clone only when `need_save` holds; otherwise leave `smpl_save` null.
- On this shape `need_save` is always false.
- Exactness: byte-identical by construction. The object is never read when `need_save` is false, and a null `smpl_save` on the `spec_exact_bonus` path already makes it return false (:4375).
- Saving: row 1's cost, between 0 and about 2.59 ms/step (≤ 1.86% of a step), to be attributed by the sub-timer. Applies at every temperature.
- Diff: about 10 lines in `server-context.cpp`.

**C2a `greedy-fast`: an exact greedy fast path for verify rows, host side.**
- Mechanism: a new function, `common_sampler_sample_and_accept_n_greedy_fast(gsmpl, ctx, idxs, draft, bias)` in `common/sampling.{h,cpp}`. Existing functions are untouched.
  - Per row it scans the raw logits row (`llama_get_logits_ith`), applying the request's sparse `logit_bias` with the same `logit + bias` float add as `llama_sampler_logit_bias` (`ignore_eos` puts EOG ids here at -inf).
  - It tracks the max, whether the max is tied, and NaNs.
  - Unique max with no NaN: take that id and call `common_sampler_accept` exactly as the chain path does.
  - Otherwise: call `common_sampler_sample` for that row, which is the champion path.
- Engagement, decided once per slot in `launch_slot_with_task` (:1827). All of the following must hold, which makes the chain provably select the unique max of logit + bias:
  - temp ≤ 0 (`llama_sampler_temp_impl` greedy branch, `llama-sampler.cpp:265-282`);
  - no grammar and no reasoning budget;
  - mirostat 0 and adaptive_p disabled;
  - penalties neutral (repeat 1, freq 0, present 0);
  - dry_multiplier 0, xtc_probability 0, typ_p ≥ 1 (typical-p can drop the max), top_n_sigma < 0;
  - n_probs 0, so no candidate read-back. `cur_p` goes stale on the fast path, and nothing reads it when n_probs is 0.
  - Top-k, top-p and min-p always keep the maximum, so they do not need to be disabled.
- Exactness: exact by construction when the max is unique. Ties and NaNs fall back, so a tie-break difference cannot arise. Gated empirically anyway (§9).
- Saving: roughly 11.8 rows/step × (0.217 - c_fast) ms. c_fast is about 0.03-0.06 ms (author estimate: one 1 MB streaming read against the chain's roughly 1 MB read, 3 MB write and partial sort). That is about **1.9-2.2 ms/step, ≈ 1.3-1.6% of a step**. Greedy requests only.
- Production :8083 traffic may run at temperature > 0, so C2a may not apply there. The registry default seen is `temperature: 0.2`; the :8083 role's request parameters are to be confirmed in .1.

**C2b `device-verify`: multi-row backend argmax for verify rows (NOT in this branch; follow-up).**
- Mechanism: lift the one-output-per-sequence restriction (`llama-context.cpp:2079-2100`) for a greedy-only backend chain, so the graph emits per-row argmax ids and `needs_raw_logits` (:2035) skips the logits copy of about 31.8 MB per step.
- Saves C2a's host work plus the device-to-host copy. The copy sits inside t_decode, so 1a did not measure it and it is not claimed.
- Touches `src/llama-context.cpp`, `llama-graph.cpp` (`build_sampling`) and `llama-sampler.cpp`, which means a libllama ABI and behaviour change and a bigger blast radius.
- Re-cost only if C1 + C2a + C3 ship and a sub-timer read puts the logits copy above 1% of a step.

**C3 `overlap-process`: overlap `process(k)` with the verify sampling (the async piece).**
- Mechanism:
  - In `decode()`, when the knob is on and the batch is **pure verify**, do this instead of calling `common_speculative_process` inline: call `llama_synchronize(ctx_tgt)` (so logits and extracted hidden states are on the host), then hand a copy of `batch_view`'s token/pos/seq arrays to a persistent worker thread, which runs `common_speculative_process(spec, view)`.
  - "Pure verify" means all of: one sub-batch covering the whole batch; every row belongs to a `SLOT_STATE_GENERATING` slot with a non-empty `spec_draft`; no prompt rows; the spec impl list is exactly {DFLASH}; and `need_save` is false for every slot.
  - `post_decode` then runs in two phases when overlap is engaged. Phase 1, for all slots in order, is row 2 only: verify sampling into a per-slot `accepted`. Then a **join on the worker**, rethrowing its failure as `runtime_error("failed to process speculative batch")`. Phase 2, for all slots in order, runs rows 3-5 unchanged.
- Data-race argument:
  - The worker touches only `ctx_dft`, the DFlash impl's `features_buf` and `batch_inject`, and read-only host output buffers of ctx_tgt, already synchronized.
  - Phase 1 touches only `slot.smpl` and read-only ctx_tgt logits.
  - Every write to spec state or ctx_dft (`common_speculative_accept`, `seq_rm(ctx_dft)`, `common_speculative_begin`, `load_dft`) happens after the join.
  - Prompt-processing slots never engage, so `begin()` cannot race.
  - HTTP threads never touch contexts. They go through `queue_tasks`, and slot save and restore run on the main loop between `update_slots` calls, after the join.
- Exactness: the same operations run on the same data in the same per-context order, so it is byte-identical by construction.
  - Moving phase 1 for all slots ahead of phase 2 changes only interleaving across independent slots: phase 2 of slot s does not write ctx_tgt logits.
  - Per-task response order is unchanged.
- Saving: min(phase-1 host time, the device-bound part of `process(k)`). Without C2a that is up to about 2.57 ms/step (≤ 1.84%), at every temperature. With C2a it is the residual, about 0.35-0.7 ms/step (0.25-0.5%).
- Its value is mainly for temperature > 0 traffic, where C2a does not engage. The worker inherits the `taskset 184-191` affinity.
- Diff: about 120 lines (worker, condvar and job slot, two-phase split, destructor join).

**C4 (considered, rejected): batch the 4 per-sequence `process()` rounds into one encode and one inject.**
- It would cut 8 sync points to 2 inside t_decode.
- But it changes the drafter's batch shape, so its kernels' numerics change, so drafts change, so the verification batches change.
- On this target, batched verify is not row-exact against single-token decode: the GDN layers run the chunked kernel for n_seq_tokens > 1 (header comment :32-37). Different drafts can therefore change greedy output and acceptance counts. That violates this item's gates. It is a separate item with a different gate if ever wanted.

## 5. Recommendation

- Build C1 + C2a + C3 on one experimental branch behind one OFF-by-default knob (§8), each as its own token so each can be gated and excluded independently. Ship the subset that passes §9.
- Order of value on this shape at temperature 0, by author estimate: C2a, then C1, then C3. Order of safety: C1, then C2a, then C3.
- C2b and B are recorded follow-ups with named triggers (§4). A is rejected on its measured ceiling.
- Do not chase pre_decode in this item. Its 14.9 ms/step (10.7% of the step) is DFlash2 drafter work on the device plus lattice selection, and it depends on `sampled(k)`, so no async reordering removes it. It is the larger lever and sits outside this rule. Overlapping drafter and target on two streams for different slot groups breaks the np4 batching that amortizes the weight reads: OFF 4 rows = 58 ms against ON 32 rows = 120 ms, so splitting into 2 × 16 rows would cost about 1.4× the device time.

## 6. Expected saving (honest bounds)

| Quantity | Value | Basis |
|---|---|---|
| Measured host post_decode | 5.175 ms/step | share.json ON `ms_per_step.post`, N 802 |
| Measured full step (pre + dec + post) | 139.62 ms | share.json ON |
| **Ceiling (post → 0)** | **3.71% step time = +3.85% decode tok/s** | 5.175 / 139.62; 1/(1 - 0.03706) - 1 |
| Verify sampling (estimate) | 2.571 ms/step | 4 × 2.961 × 0.21709 ms (OFF per-call cost × ON mean len) |
| Unattributed remainder | ≈ 2.59 ms/step | 5.175 - 2.571 - 0.013 |
| C1 | 0-2.59 ms/step (0-1.86%) | ≤ remainder; sub-timer decides |
| C2a | ≈ 1.9-2.2 ms/step (1.3-1.6%) | author estimate of c_fast; greedy only |
| C3 after C2a | ≈ 0.35-0.7 ms/step (0.25-0.5%) | residual verify host time; bounded by process(k) |
| **C1 + C2a + C3, temp 0** | **author estimate 1.5-3%; never above 3.71%** | sum, capped by the ceiling |
| Not claimed | logits device-to-host copy (≈ 31.8 MB/step) and process() host work, both inside t_decode | 1a does not separate them |

## 7. Branch and base

- **Cut** fork branch `experimental/gpu-zos-2-one-step-lag-20261024` from champion `dcc853b55` (`ak/champion/llama-cpp-ffc1bac82eec`, also `fork/ak/champion/...`). Work in a separate worktree, as GPU-ZOS-1a did:

  ```
  git -C /mnt/raid0/llm/llama.cpp worktree add -b experimental/gpu-zos-2-one-step-lag-20261024 \
      /mnt/raid0/llm/worktrees/llama-gpu-zos-2-20261024 dcc853b55
  ```

  Never check out in the frozen tree. Push only to `fork`: `git push fork HEAD:refs/heads/experimental/gpu-zos-2-one-step-lag-20261024`. If `ak/champion/...` has advanced before .1 starts, cut from the new tip and re-run `git diff --quiet dcc853b55 <tip> -- tools/server common`. An in-flight C4 consolidation, `cdb4d8c77` on `experimental/champion-c4-20261024`, descends from `dcc853b55`.
- **Production v10 stays frozen.** `production-consolidated-v10` at `ffc1bac82` (`/mnt/raid0/llm/llama.cpp`, kernel store `kernels/production/{cpu,gpu}`) is never modified, rebased, built or committed to by this item (root CLAUDE.md, *Production kernels are FROZEN*). This change reaches production only as part of a new version (v11) through the kernel-promotion path.
- **Why the champion tip is the right base.**
  - Root CLAUDE.md, *Experimental Kernel Workflow*, step 1, reads: "Pull fresh production → `llama.cpp-experimental` — start from the *current* production tip so all its optimizations are present; never accumulate on a long-lived branch forked from an old tip". Step 4 says the promotion candidate must be "the FULL build (fresh production + all new features) validated as a whole — never reconciled via cherry-picks at promotion time".
  - The champion is production plus everything already folded for v11. `ffc1bac82` is an ancestor of `dcc853b55` (`git merge-base --is-ancestor ffc1bac82 dcc853b55` exits 0, 110 commits ahead).
  - `docs/reference/kernel-manifests/README.md` names `ak/champion/llama-cpp-ffc1bac82eec` as the branch v11 is built from ("Fold only into champions").
  - Cutting from the champion therefore keeps every production optimization (step 1's purpose) and develops the feature on the exact base the full v11 candidate will be (step 4). A cut from bare `ffc1bac82` would have to be reconciled against 110 champion commits at fold time, which is what step 4 forbids.
  - Stated precisely: the rule's literal text names the production tip, and the champion tip is a strict superset of it. The A side of every gate below is therefore **the champion image, not v10**.

## 8. The knob

- **Variable.** `LLAMA_ZOS2`, an environment variable read once at load, next to `spec_exact_mode_from_env` (:80, used at :1011). An environment variable lets one candidate binary serve the knob-off, single-token and all-on arms.
- **Grammar.** Comma-separated tokens from `lazy-save`, `greedy-fast`, `overlap-process`, or `all`. Unset or empty means everything off.
- **Fail-safe off.** An unknown token is ignored with one `SRV_WRN`, the same pattern as `LLAMA_SPEC_EXACT`.
- **Startup line.** One `SRV_INF` line: `GPU-ZOS-2: LLAMA_ZOS2 lazy-save=%d greedy-fast=%d overlap-process=%d`. The gate reads it.
- **Code structure.** Every change sits under `if (zos2.<token>) { new } else { champion statement unchanged }`. Knob off executes the champion statements. The new common function is only called when its token is on.
- **Diff scope.** Only `tools/server/server-context.cpp`, `common/sampling.h`, `common/sampling.cpp` and one new test file. Nothing in `ggml/` or `src/`.

## 9. PREDECLARED gates (fixed before any build)

### 9.1 Images, environment and validity (each failure → INCONCLUSIVE, rc 6, no model load)

- **A (champion):** `kernels/builds/gpu-20261023-dcc853b55-c3`, the champion image since 2026-10-24T07:50Z per its `PROVENANCE.md` (version 10413, dcc853b55).
- **Candidate:** a release build of the .1 head with the same recipe. Its `GGML_*`/`LLAMA_*` CMakeCache entries must show 0 differing lines against the champion image, with the CH-28d prefix-map flags.
- **Structural gates on the candidate:**
  - (a) `git diff --stat dcc853b55..HEAD` lists only the §8 files.
  - (b) `strings libllama-server-impl.so | grep LLAMA_ZOS2` gives ≥ 1 match on the candidate and 0 on the champion image (negative control).
  - (c) sha256 of `libggml*.so` and `libllama.so` equal the champion image's. The kernels are unchanged by construction, and the CH-28d deterministic builds make this checkable. A mismatch fails the build, not the science.
  - (d) `verify_ggml_linkage.sh` exits 0, with `LD_LIBRARY_PATH=<image>/bin:/opt/rocm/lib`.
  - (e) binary hashes are re-verified before each load.
- **argv:** `/mnt/raid0/llm/epyc-orchestrator/logs/server_launches/8083.json` verbatim, except the binary, `--port` and `--slot-save-path`. These are the 1a rules. One server at a time.
- **Proved from `/proc/<pid>/environ` of the own server pid:**
  - `HSA_OVERRIDE_CPU_AFFINITY_DEBUG=0` is present. 1a did not set it; this run must.
  - `GGML_CUDA_DISABLE_GRAPHS` is absent (HIP graphs ON). Positive proof as well: every request's `print_timing` shows `graphs reused` > 0.
  - `LLAMA_SPEC_EXACT` is absent.
  - `LLAMA_ZOS2` is absent on the A and O arms and equals the arm's value on B and F. The startup line in §8 must agree.
- **VRAM drain wait before each launch:**
  - the previous own pid is gone from `/proc` and from the KFD process table;
  - MI210 free VRAM is ≥ 50 GiB on 2 consecutive samples 5 s apart;
  - timeout 180 s, else rc 6.
- **Own-pid residency:** own-pid KFD VRAM ≥ 40 GiB within 30 s of `/health` (1a amendment), and ≥ 2 own-pid samples ≥ 20 GiB inside every wave (two-sample persistence).
- **Own-pid VRAM guard:** if own-pid VRAM exceeds 61440 MiB (60 GiB), send TERM and then KILL to the captured pid only, verify it is dead, and mark the pass invalid.
- **Waves:** every wave has 4/4 streams OK and every stream drafted (`draft_n` > 0).

### 9.2 Workload

- **Prompts:** 24 fixed prompts, the first 24 `TOPICS` of `gpu-zos-1a/drive.py` (sha256 prefix `3ec90db83d47b3e1`) with its prompt template. They run as 6 waves × 4 concurrent `/v1/chat/completions` requests at np4, after one excluded 64-token warmup wave.
- **Request fields:** `temperature 0`, `seed 1234`, `max_tokens 1024`, `ignore_eos true`, `chat_template_kwargs.enable_thinking false`, `stream false`, `return_tokens true`, `cache_prompt false`, `n_probs 0`. Spec stays ON at the server's n_max 7.
- **Arms, one server launch each, in this order:**
  - `A1` (champion), `B1` (candidate, `LLAMA_ZOS2=all`), `A2`, `B2`: 6 waves each.
  - `O` (candidate, knob unset): 6 waves.
  - `F1` = `lazy-save`, `F2` = `greedy-fast`, `F3` = `overlap-process` (candidate): 2 waves each (the first 8 prompts), correctness only.
- **Window:** ≥ 75 min on an exclusive MI210, including loads and drains.

### 9.3 Correctness gates

- **G-DET (determinism control):** A1 and A2 return identical `tokens` arrays for all 24 prompts.
  - **If G-DET holds:** the np4 gates below require exact identity.
  - **If G-DET fails:** record the A1/A2 mismatch count m_AA and the first-divergence index per prompt. The np4 gates become: mismatch count against A1 ≤ m_AA, with A2 as the reference set. A **serial tier** is then also required: 8 prompts sent one at a time, so 1 slot is generating, at `max_tokens 256`. It runs on A twice (serial A/A control), then on B, then on O.
    - Serial A/A identical: B and O must be byte-identical, with equal acceptance counts.
    - Serial A/A differs: correctness is INCONCLUSIVE and nothing ships.
    - The serial tier runs in the same window if time remains, else in a follow-up window; the verdict stays INCONCLUSIVE until it runs.
- **G-OFF (knob off == champion):** for every prompt, O equals A1 on `tokens` and `content`, and `timings.draft_n` and `timings.draft_n_accepted` are equal.
- **G-ON (knob on, greedy, np4 DFlash2):** for every prompt, B1, B2 and each F_i equal A1 on `tokens` and `content`, with equal `draft_n` and `draft_n_accepted`.
  - A token whose arm fails G-ON is excluded from the shipping set.
  - If any token fails, B is re-run, in a new window, with only the passing tokens.
- **G-FB (fast-path accounting):** in the DEBUG image (§9.6), C2a's fallback counter is reported (rows where a tie or NaN routed to the chain). This is informative only; correctness is G-ON.

### 9.4 Speed gate (release images only; DEBUG figures never gate)

- **Metric:**
  - Per request: `timings.predicted_per_second` (server-reported decode tok/s).
  - Pairing: by prompt, using only prompts whose `tokens` are identical between the two passes compared. Identical tokens mean identical acceptance and tokens per step, so the ratio is a step-time ratio.
  - Excluded prompts are counted. If more than 25% of prompts are excluded from any comparison, speed is INCONCLUSIVE.
  - g(·) is the geometric mean over the paired prompts.
- **Effect:** S = g( √(B1ᵢ·B2ᵢ) / √(A1ᵢ·A2ᵢ) ) - 1.
- **Noise floor:** NF = max( |g(A2ᵢ/A1ᵢ) - 1|, |g(B2ᵢ/B1ᵢ) - 1| ).
  - **Unit:** percent of per-request decode tok/s (paired, geometric mean over 24 or fewer prompts, np4 spec-ON, this shape).
  - Also reported: the p10/p90 of A2ᵢ/A1ᵢ, and the 1a INDICATIVE prior (per-wave step-time range 1.55%, DEBUG build).
- **Alternation check (A/B/A/B):** g(B1/A1) - 1, g(B1/A2) - 1 and g(B2/A2) - 1 all have the same sign as S.
- **Thresholds:**
  - Minimum effect worth shipping: E_min = 1.0%.
  - Upper plausibility bound: U = 3.71% + 2·NF, the measured host share plus noise. The B arm can only remove host time from post_decode, plus C3's overlap of the same.
- **Verdict:**
  - **SHIP:** all correctness gates pass, S ≥ max(E_min, 2·NF), the alternation check holds, and S ≤ U.
  - **SUSPECT:** S > U. The effect is larger than the measured share can explain, so do not ship until the DEBUG attribution (§9.6) explains it.
  - **NULL:** |S| < max(E_min, 2·NF), with NF ≤ 1.85%. Close GPU-ZOS-2 with the numbers.
  - **UNDERPOWERED:** NF > 1.85% (half the ceiling), so even a perfect implementation could not clear 2·NF. One extension is allowed: append A3 and B3 and recompute S and NF over all 6 passes with the same rule. If it is still underpowered, the result is INCONCLUSIVE.
  - **REGRESS:** S ≤ -2·NF. FAIL.
- **Supplementary, outside the rule:** if the window allows, run 2 waves per side of A and B at `temperature 0.2`, the registry default seen; the :8083 role's value is to be confirmed in .1. This is the production-temperature case, where only C1 and C3 engage. Speed only, reported, never gating.

### 9.5 Constants and their provenance

| Constant | Value | Provenance |
|---|---|---|
| Open threshold; measured shares | 3%; ON 4.15% (N 802), OFF 1.48% (N 2808); pre 14.9 ms/step, 14.4% incl. pre | **task** (GPU-ZOS-1 rule; 1a VERDICT / share.json) |
| Shape | np4 DFlash2 :8083 argv | **task** (1a launch record) |
| Branch, base | `experimental/gpu-zos-2-one-step-lag-20261024` from `dcc853b55` | **task** |
| Knob default | off | **task** |
| Gate list: knob-off byte-identity; greedy temp-0 byte-identity at np4 + champion two-pass control; equal acceptance; tok/s at np4 spec-ON; NF with unit; E_min from the share; A/B/A/B; own-pid KFD residency; graphs ON from environ; `HSA_OVERRIDE_CPU_AFFINITY_DEBUG=0`; 60 GiB own-pid guard; VRAM drain wait | as listed | **task** |
| Guard 61440 MiB; free VRAM ≥ 50 GiB; residency ≥ 40 GiB in 30 s; ≥ 2 samples ≥ 20 GiB per wave; prompts and template | as listed | **prior artifact** (1a PREDECLARATION / AMENDMENT / drive.py) |
| Ceiling 3.71% / +3.85% | derived | **derived** from task numbers (§6) |
| E_min = 1.0% | about 27% of the ceiling; above half the 1a per-wave range (0.78%) | **author** |
| 2·NF multiplier; UNDERPOWERED at NF > 1.85%; one A3/B3 extension; U bound | as listed | **author** |
| 24 prompts, 6 waves × 4, max_tokens 1024, seed 1234, cache_prompt false, return_tokens | as listed | **author** |
| 25% exclusion limit; serial tier 8 × 256 | as listed | **author** |
| Drain-wait 2 samples 5 s apart, 180 s timeout; F arms 2 waves | as listed | **author** |
| Window ≥ 75 min | about 39 min of waves + 8 loads/drains | **author** estimate |
| Engagement predicates, knob grammar, sub-timer set | §4, §8, §10 | **author** |

### 9.6 Attribution read (INDICATIVE, never gating)

- **Image:** the candidate rebuilt with `-DLLAMA_SERVER_DEBUG_TIMINGS=ON`, carrying 1a's raw `debug-timings:` line plus the .1 sub-timers.
- **Runs:** arms knob-off, each token alone, and `all`, 2 waves each, at the 1a shape.
- **Reports:** per-component ms/step and how much each token removed.
- **Purpose:** this is the attribution that SUSPECT requires, and the evidence for whether C2b is worth re-costing.
- **Window:** ≥ 30 min; it may share the gate window if time remains.

## 10. Implementation breakdown (proposed handoff sub-boxes; the main thread applies them)

- [ ] **GPU-ZOS-2.1 — code: the `LLAMA_ZOS2` knob (lazy-save, greedy-fast, overlap-process) on `experimental/gpu-zos-2-one-step-lag-20261024`.**
  - Base: cut from champion `dcc853b55`; re-cut if `ak/champion` has advanced.
  - Scope: only `tools/server/server-context.cpp`, `common/sampling.{h,cpp}` (one new function) and one new CPU unit test. No ggml/ or src/ change.
  - Knob: default off, with the knob-off path equal to the champion statements (design `docs/design/gpu-zos-2-one-step-lag-design-20261024.md` §4/§8).
  - Sub-timers, added under DEBUG_TIMINGS to 1a's raw line: verify, clone, rollback, emit, process, join_wait, and the C2a fallback count.
  - Unit test: the greedy fast path equals the chain on synthetic logits, including ties, NaN, -inf bias and the full default chain.
  - Also confirm the :8083 role's request temperature.
  - Done when the branch is pushed to `fork`, the test passes, and `git diff --stat dcc853b55..HEAD` shows only those files.
- [ ] **GPU-ZOS-2.2 — HIP gfx90a store builds of the .1 head (release + DEBUG_TIMINGS), c3 recipe.**
  - Gates: 0 CMakeCache diff against `gpu-20261023-dcc853b55-c3`; `strings` shows `LLAMA_ZOS2` in the candidate's libllama-server-impl and 0 in the champion's; `libggml*`/`libllama.so` sha256 equal the champion image's; linkage PASS.
  - Cost: CPU build role, about 2 min at -j24 each.
- [ ] **GPU-ZOS-2.3 — gate run (≥ 75 min exclusive MI210 window).**
  - Arms: A1 B1 A2 B2 + O + F1-F3 per design §9.
  - Verdict: SHIP / NULL / SUSPECT / UNDERPOWERED / REGRESS / INCONCLUSIVE.
  - Also: the INDICATIVE attribution read on the DEBUG image (§9.6).
  - SHIP leads to a pending-fold row in `docs/reference/kernel-manifests/llama-v11-manifest.md` (fold into the champion, never into v10). NULL closes GPU-ZOS-2 with the numbers.
  - The measurements wire into the belief kernel (a `scripts/vidya/adapters/README.md` row plus a VB task) at launcher-prep time.

## 11. Risks and known limits

- **np4 determinism is unproven.** Batch composition depends on request arrival, and the target is not row-exact across batch shapes. G-DET and the serial tier exist for this. If both fail, nothing can be certified at np4 and the item stops at INCONCLUSIVE rather than loosening the gate.
- **C2a covers only greedy requests.** If production :8083 runs at temperature > 0, only C1 and C3 help production. The temperature-0 gate then over-states production benefit, and the supplementary temperature-0.2 arm is the honest read.
- **C3 threading.** The race argument in §4 C3 rests on "nothing touches ctx_dft or spec between fork and join". The engagement predicate excludes every path that would: prompt rows, `begin()`, checkpoint restores, and non-DFlash impls. Any future server change to post_decode ordering must re-check it. The worker is joined in the destructor.
- **The DEBUG build does not separate the logits copy or the `process()` device time** from t_decode in 1a. The .1 sub-timers do, and those figures stay INDICATIVE.
- **The remainder attribution (2.59 ms/step) is a hypothesis.** If the clone is not the cause, C1's saving is about 0, and the ship decision rests on C2a and C3.

## 12. References

- Handoff: `handoffs/active/gpu-serving-tie-in-program.md` (GPU-ZOS-1, 1a, 2). Evidence: `/mnt/raid0/llm/tmp/f8-launchers-20261023/gpu-zos-1a/` (VERDICT.json, PREDECLARATION.md, AMENDMENT-residency-check.md, out/share.json, out/server.log, analyze.py, drive.py, job.sh, RUN_RECORD.json).
- 1a DEBUG_TIMINGS branch: fork `experimental/gpu-zos-debug-timings-20261023` @ `b5a524605` (CMake `LLAMA_SERVER_DEBUG_TIMINGS`, raw `debug-timings:` line).
- Champion image: `/mnt/raid0/llm/kernels/builds/gpu-20261023-dcc853b55-c3/PROVENANCE.md`. Build-script template: `/mnt/raid0/llm/tmp/gpu-leak1c/build_store.sh` and `/mnt/raid0/llm/tmp/c3-fold-prep/build_store.sh`.
- Workflow: root `CLAUDE.md` (*Experimental Kernel Workflow & Production-Kernel Immutability*); `docs/reference/kernel-manifests/README.md`.
