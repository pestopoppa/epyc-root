# PREDECLARATION — locals-ufh14-lb7-stall (UFH14-LB7)

Written 2026-10-23 by workspace-f8 (subagent), BEFORE any compute for this item. Nothing below may be changed after the
first session starts except by a dated `## Amendment N` section appended at the end, written before the session it governs.

Task: `handoffs/active/agentic-serving-harness-fixes.md` UFH14-LB7 (root). FILLERS row `locals-ufh14-lb7-stall`.

## 1. Question and the decision it informs

In the UFH14-B4i A/B (2026-10-04, one rep per arm), the `--cache-idle-slots` ON arm paid a stall **before** prompt
evaluation: per turn ≥ 2, `TTFT − prompt_ms` had a median of **43.49 s ON vs 1.01 s OFF** (15 turns each, recomputed
from `artifacts/gpu-block-27b-20261004/results/b4i/{ON-r1-20261004T040819Z,OFF-r1-20261004T042211Z}/turns.jsonl`). Turn-1
gaps were about 0 in both arms, and the re-prefill share was the same (hit_tok 0.81 in both).

**Question:** which server-loop component owns that stall? The candidates are:

- neighbour idle-slot saves (VRAM→RAM);
- the turn's own prompt-cache load (RAM→VRAM, including the draft context);
- other conversations' prompt loads that block the loop;
- queue and loop-busy residual.

**Decision informed:** which component owns the restore stall, before any TTL or retention-policy work. It also
decides whether the idle-slots package (B4j) needs a code change or only the flag.

**Minimum effect:** a component is material only if its ON−OFF mean contribution is **≥ 10 s** of the 43.5 s median.

## 2. Code read (champion 49550eda5, read-only via `git show`; line numbers are that commit's)

All of these run on the **single server-loop thread**, so they block every slot.

- `process_single_task` (server-context.cpp:2753-2768). After **every** completion-task launch, each idle slot runs
  `prompt_save` (VRAM→host copy of target **and** draft KV) and then, with `--kv-unified`, `prompt_clear`.
- `get_available_slot` (:1672-1780). A conversation whose slot was cleared is skipped by LCP selection (empty tokens) and
  picked by LRU, which sets `update_cache = true` (:1752). That path runs `prompt_save(victim)` and then `prompt_load`,
  which calls `server_prompt_cache::load`. The load scans the entries (LCP) and runs `llama_state_seq_set_data_ext` for the
  target and then the draft context. After that comes `update()`.
- `llama_kv_cache::state_read_meta` (llama-kv-cache.cpp:2510) calls `find_slot(ubatch, false)`, which allows
  non-contiguous cells. `state_read_data` then takes the **per-cell scatter path** (:2646/:2689/:2744): one
  `tensor_set` per cell per layer, for K and for V. Saves copy one `write_tensor` per contiguous cell range. So on a
  fragmented unified pool, one copy can become thousands of small host↔device transfers. This is a hypothesis for *why* a
  copy is slow; it is not part of the gating rule.
- `t_start_process_prompt` is set at :3639. The `new prompt` TRACE line follows it immediately. At the end of the same
  STARTED block, `send_partial_response(..., is_begin=true)` (:3933) makes the HTTP layer send the response headers. Hence
  **client header time ≈ server `new prompt` time**, and `prompt_ms` starts there. Therefore `TTFT − prompt_ms` =
  (t_start_process_prompt − t_send) + first-token delivery.
- Lock wait: there is no lock in this path except the `server_queue` mutex, which is held for microseconds. A task
  "waiting" is a task sitting in `queue_tasks` while the loop runs something else. That time is measured as the residual
  components below.

## 3. Instrument and replay design

**Binary.** The champion GPU store image is `kernels/builds/gpu-20261021-49550eda5-c-nemotron` (10411 / 49550eda5). It is
the same binary in both arms, and there is **no code branch**. Every delimiting line below already exists, and `job.sh`
checks each string in `libllama-server-impl.so` before load.

The server runs with `-lv 4 --log-prefix --log-timestamps`. TRACE is level 4. The timestamp is `M.SS.mmm.uuu` since log
init, taken on the calling thread at log time.

| event | line (level) | marks |
|---|---|---|
| SEL | `selected slot by LRU / LCP similarity / id` (INFO) | the loop picked the task up |
| CU_B / CU_E | `updating prompt cache` / `prompt cache update took X ms` (TRACE) | own prompt-cache update (victim save + load + update) |
| SAVE | ` - saving prompt with length N, total state size = X MiB (draft: Y MiB)` (TRACE) | start of a VRAM→RAM copy, with bytes and the draft share |
| LOOK / FOUND | ` - looking for better prompt` / ` - found better prompt` (TRACE) | cache lookup scan; FOUND = start of the RAM→VRAM restore |
| CSTATE (+ entries) | ` - cache state: …` + `   - prompt P: N tokens, …, X MiB` (TRACE) | end of a copy; the entry list gives restored bytes |
| LAUNCH | `processing task, is_child = 0` (INFO) | task launched; idle saves follow |
| IDLE / CLEAR | `saving idle slot to prompt cache` / `clearing prompt with N tokens` (TRACE) | one neighbour idle save+clear interval |
| NEWP | `new prompt, n_ctx_slot = …, task.n_tokens = N` (TRACE) | t_start_process_prompt |

**Clock alignment.** The client records `t_send` and `t_hdr` (headers received) per turn. Each turn is matched to its
NEWP line by `task.n_tokens == prompt_n + cache_n`. The offset is the minimum over turns of (t_hdr − t_NEWP). Lag is
(t_hdr − t_NEWP) − offset, which is ≥ 0. The server window of a turn is W = [t_send − offset, t_NEWP].

What `-lv 4` cannot split is **report-only** and never gates the verdict:

- **Target vs draft inside one copy.** It is estimated in proportion to bytes (`draft: Y MiB` of the SAVE line, and of
  the restored entry's original SAVE).
- **Scatter vs bandwidth.** It is tagged from copy throughput: < 1 GiB/s means transfer-count bound; > 5 GiB/s means
  bandwidth bound.
- **Draft resync after the load.** `common_speculative_begin` runs at DONE_PROMPT, which is inside `prompt_ms`. So by
  construction it is not part of the pre-evaluation gap. The ON−OFF `prompt_ms` delta is reported separately.

**Shape.** The B4i scratch argv (`results/b4i/launch_ON.sh`):

- np 4, `-c 393216`, `-t 8`, `-ub 2048` (b default 2048), `--flash-attn on`, q8_0 KV, `--kv-unified`, `--no-mmap`,
  `-ngl all`, `--cache-ram 65536`;
- terse template, DFlash2 drafter n-max 7 on ROCm0;
- numactl `--membind=3`, taskset 184-191;
- own port 18307 and a scratch `--slot-save-path`. Arm OFF adds `--no-cache-idle-slots`.

This is the shape that produced the 43.5 s. Production :8083 now runs `-b/-ub 512` and OFF; that shape is out of scope here.

**Turns.** These are the B4i turns, built with the B4i runner's own helpers (`lib_gpublock.fit_prompt`, `rotated_text`,
the DS41 C1..C7 corpus, the B4i `SYSTEM` text):

- 3 conversations × 6 turns;
- a ~20k-token base, then +~1.5k tokens of "tool output" per turn;
- 200 generated tokens, temperature 0, `enable_thinking=false`, stream;
- `/slots` sampled every 2 s, as in B4i;
- `id_slot` NOT sent. An explicit id_slot takes a different path; see section 7.

**Predeclared deviations from B4i:**

- (a) Deterministic prompt heads `[b4i conv<c> lb7]`, so all 6 sessions send the same turns.
- (b) A round barrier. Turn 1 sends conv c at +12c s, as in B4i. Turn k ≥ 2 starts 30 s after every conversation has
  finished turn k−1, with conv 0, 1, 2 at +0/+2/+4 s. This gives the same arrival order and spacing in every arm and rep.
  B4i's per-conversation pauses let the order drift (B4i rounds arrived within ~4 s in mixed order). Slot assignment is
  left to the server (LCP/LRU), as in B4i. The parser records the slot sequence per session.
- (c) The client records `t_hdr`.

**Sessions.** There are 6 sessions in ABBAAB order: s1-ON, s2-OFF, s3-OFF, s4-ON, s5-ON, s6-OFF. That gives **n = 3 reps
per arm**.

- Every session runs on a **fresh server**: empty KV pool, empty RAM cache, same binary.
- The pairs are (s1,s2), (s4,s3) and (s5,s6). A pair starts only if both its sessions fit the window.

**Proofs per session:**

- the own pid owns the port and `/health` answers;
- KFD VRAM > 0 for that pid;
- `libggml-hip.so` is mapped from the store image;
- production :8083 is not listening.

## 4. Attribution (per turn, turns ≥ 2)

W is partitioned exactly into the components below. Loop intervals never overlap because there is one thread. Each
component is the overlap of W with that interval class:

| component | interval | group |
|---|---|---|
| neighbour_save_own_trigger | IDLE→CLEAR with bytes copied, triggered by this turn's own launch | NEIGHBOUR_IDLE_SAVE |
| neighbour_save_other_trigger | the same, triggered by another conversation's launch | NEIGHBOUR_IDLE_SAVE |
| own_load_victim_save | own CU_B→LOOK (prompt_save of the LRU victim) | OWN_PROMPT_LOAD |
| own_load_lookup | own LOOK→FOUND (or →CSTATE when nothing matched) | OWN_PROMPT_LOAD |
| own_load_copy | own FOUND→CSTATE (set_data of target + draft) | OWN_PROMPT_LOAD |
| own_load_bookkeeping | own CSTATE→CU_E | OWN_PROMPT_LOAD |
| other_load | another task's CU_B→CU_E inside W | OTHER_PROMPT_LOAD |
| idle_noop | IDLE→CLEAR with nothing copied (empty slot, or already cached) | QUEUE_AND_LOOP_BUSY |
| residual_pre_pickup | unlabelled time before the own SEL (HTTP template + tokenize + queue wait on decode/prefill) | QUEUE_AND_LOOP_BUSY |
| dispatch_overhead | unlabelled time between the own SEL and LAUNCH | QUEUE_AND_LOOP_BUSY |
| residual_post_launch | unlabelled time between the own LAUNCH and NEWP (batch admission, update_slots of other slots) | QUEUE_AND_LOOP_BUSY |

Per session, every component's **mean** over the 15 turns ≥ 2 is computed. Means are additive, so the group means sum to
mean W.

## 5. Rule (gates in order; `lb7_parse.py aggregate`)

**Per pair** (ON vs OFF):

- ΔW = mean W(ON) − mean W(OFF), and Δgroup likewise for each group;
- fraction f_group = Δgroup / ΔW;
- ΔG uses the client gap G = TTFT − prompt_ms.

1. **INCOMPLETE** if fewer than 2 valid pairs.
2. **NOT_REPRODUCED** unless the median over pairs of ΔG is ≥ 20 s **and** every valid pair has an ON median G ≥ 20 s.
3. **INSTRUMENT_FAIL** unless every valid pair meets all of these:
   - lag p95 ≤ 0.5 s, with ≥ 3 turns at lag < 0.2 s, in both sessions;
   - ≥ 90 % of turns matched;
   - ON coverage |1 − mean W / mean G| ≤ 0.10, i.e. the partition explains the client gap.
4. **OWNER=<group>** if one group has f ≥ 0.5 in **every** valid pair **and** a median Δ ≥ 10 s.
5. Otherwise **SHARED=<g1>+<g2>** if the two largest groups each have a median Δ ≥ 10 s and together a median f ≥ 0.8.
6. Otherwise **UNATTRIBUTED**.

**Report-only (never gates):**

- the pre-header share of G in ON (≥ 0.8 confirms "before prompt evaluation");
- OWN+OTHER load as one mechanism;
- the draft-copy byte-share estimate;
- the copy throughput and its mechanism tag;
- per-component medians;
- the slot sequence;
- the ON−OFF `prompt_ms` delta;
- the `/slots` idle-drop count (B4i's purge evidence).

The verdict is written to `VERDICT.json`. `PASSED` means 6/6 sessions are OK and the verdict is not INCOMPLETE.

## 6. What each verdict leads to (stated now, so the reading cannot drift)

- **OWNER=NEIGHBOUR_IDLE_SAVE.** The cost is the synchronous save of every idle neighbour on every launch. B4j
  (`--no-cache-idle-slots` on :8083) is the right lever. Any upstream or experimental fix targets the save, for example
  deferring the save, saving only on pool pressure, or skipping slots already cached.
- **OWNER=OWN_PROMPT_LOAD or OTHER_PROMPT_LOAD.** The cost is the RAM→VRAM restore. If the mechanism tag says
  transfer-count bound, the next experimental-branch probe is contiguous `find_slot` or batched scatter in
  `state_read_data`.
- **SHARED.** Both. Report both Δs.
- **UNATTRIBUTED, or QUEUE_AND_LOOP_BUSY largest.** The stall is loop time that no `-lv 4` line delimits. The next
  stage adds timing probes on an `experimental/` branch from 49550eda5, around `process_single_task`,
  `get_available_slot`, `prompt_save`/`load` (target vs draft) and `update_slots` admission. That is a new
  predeclaration amendment.

## 7. Package amendment facts (code read at 49550eda5; text for the idle-slots package, no compute needed)

- **An explicit `id_slot` on a slot that cache-idle-slots cleared skips the RAM restore.**
  - `f_keep = (sim_best * n) / ret->prompt.tokens.size()` (:1718) is 0/0 = NaN.
  - `f_keep < 0.5f` (:1726) is false, so `update_cache` stays false and `prompt_load` never runs.
  - The turn re-prefills from zero although its state is in cache-ram.
  - Only `id_slot = -1` (LRU, :1752) reaches the restore.
- **An explicit `id_slot` onto a slot holding another context.** With the default `slot_prompt_similarity = 0.1`,
  f_keep is below 0.5, so the victim **is** saved before it is overwritten. The victim is overwritten without a save only
  when `--slot-prompt-similarity 0` skips that block. The task text's "explicit id_slot reuse overwrites the victim
  without saving it" holds only in that configuration. The owning session should verify it before quoting it.
- **Pool-full with idle contexts resident (OFF).** When a decode finds no KV space (`ret == 1`), `try_clear_idle_slots`
  (:1787, called at :4252) purges idle slots one at a time with `prompt_clear` only: WARN `purging slot N with M tokens`,
  and **no RAM save**. If nothing can be purged, it halves `n_batch`. So with four idle contexts filling the pool, the
  next large prompt silently drops an idle conversation, whose next turn is a cold prefill.

## Amendments

(none)
