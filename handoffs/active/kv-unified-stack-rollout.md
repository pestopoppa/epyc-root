# Unified KV (`--kv-unified`) stack rollout and shared-pool serving

**Status**: ACTIVE. The GPU-residency package (OP-54) is **applied and serving-proven** (2026-09-24 ~18:45–18:55Z,
orch `0a564a1f`, research `75ee1b8e`): :8083 runs `-np 4 -c 196608 --kv-unified --spec-draft-n-max 4 -ub 2048
--cache-ram 65536`, STT/TTS run on CPU cores 0-23 / 24-39. The overflow branch and the gate fix are merged. What is
left: the depth-4 production confirmation (KVU-1b / M-3b),
the opencode limit (KVU-1a, operator), and the follow-ups below.
**Scratch**: `/mnt/raid0/llm/tmp/codex-ni-20261027-fa4-sixkey-diagnostic/`, `/mnt/raid0/llm/tmp/codex-ni-20261027-fa4-attempt2-fix/`, `/mnt/raid0/llm/tmp/codex-ni-20261027-fa4-original-nan-audit/` · worktrees: none
**Created**: 2026-09-24 (main-ak-seat, stack-configuration window)
**Priority**: HIGH. :8083 caps every request at 98,304 tokens today, and that ceiling emptied DS41 run 8's planner reply.
**Categories**: inference_serving, kv_cache, orchestration, stack_lifecycle
**Parent index**: [routing-and-optimization-index.md](routing-and-optimization-index.md) (row RTG-57)
**Depends on**: RTG-19 (single-source stack pipeline; its SSU-F3 capacity accounting is done, 2026-09-23), RTG-36 (stack-change governance),
INF-41 (speech VRAM in the capacity gate, OP-48). Downstream, not a dependency: INF-77 DS41-C25 (run 9) waits
on KVU-1.
**Related**: [`deepseek-v41-flash-evaluation.md`](deepseek-v41-flash-evaluation.md) DS41-C25,
[`attention-matching-kv-compaction.md`](attention-matching-kv-compaction.md) KV-3 (native LCP slot pick),
[`speculative-decoding-mtp-refresh.md`](speculative-decoding-mtp-refresh.md) SW-9,
[`autokernel-orchestrator-actor-backend.md`](autokernel-orchestrator-actor-backend.md) OAB-4a,
[`multimodal-pipeline.md`](multimodal-pipeline.md) S-11a

## Start here

Live front as of 2026-10-24 (sections A and B are largely done; their history stays in place under Tasks):

1. **C — kernel candidate (v11, guarded)**: KVU-LB1.d always-F32 VKQ, V11-FA-4/-6, fold-c1-p3, CPU-FA-VKQ-2 (see section C).
2. **D — measurement follow-ups**: HPR-b 64k holdout (`hpr-b-64k-holdout`, armed, resumable); KVU-16g-1 row-5c A/B;
   KVU-19b-rework-c2-cal; **KVU-12.3b** (busy-subset re-check, trigger: stack back + >= 100 resumed turns at >= 3 busy slots).
3. **E — speech residency** items as listed.
4. The 2026-09-24 rationale, evidence and first-session record moved to the completed sibling (see Completed Scope).


## Completed Scope

Completed history through 2026-10-24 (moved verbatim, no open tasks): [kv-unified-stack-rollout-completed-through-2026-10-24.md](../completed/kv-unified-stack-rollout-completed-through-2026-10-24.md). Sections moved: Why this exists: production was never unified; Evidence (all 2026-09-24); Done this session.

## Tasks
<!-- 2026-10-21 (noninf-ak, KVU-RESTORE-1): everything else that 465954bc0 (2026-10-07, a stale-base overwrite, +12/-892 lines) deleted between 'Depends on' and 'Not filed here' was restored byte-exact from 465954bc0^ by a three-way merge onto origin/main, with original tick states. NOT restored here, because they already exist: the C2 section's items (V11-FA-1..6, KVU-16g-1/2, KVU-19b-fold-c1-p3, KVU-19b-rework-c2-cal, CPU-FA-VKQ-2; they stay in C2, so their parents below list them only by reference) and the later KVU-12 through 12.6 and 2026-10-20 KVU-21 text. The old KVU-21 (#29510 flash_attn_ext_rows A/B arm) collides with the current KVU-21 id; it was restored later under the new id KVU-22 (see 'restored 2026-10-21 from 465954bc0^, re-IDed from KVU-21'). The interim restore block from ef9e1ab6f was removed (C2 carries those items). Three in-place updates the overwrite had reverted came back: the 'Depends on' SSU-F3 wording, KVU-1d's 2026-10-03 note, and the 'Not filed here' SSU-F3 bullet. -->

### A — :8083 bring-up
- [x] **KVU-1 — apply the signed `-kvu` package and prove it serves** (OP-54). ✅ 2026-09-24 — applied as the
  revised revision-3 package (not the np2 funding below): `-np 4 -c 196608 --kv-unified --spec-draft-n-max 4 -ub
  2048 --cache-ram 65536`, O-2 **dropped** (a q8_0 draft cache adds a 768 MiB FA conversion buffer), STT → CPU
  0-23, TTS → CPU 24-39 via the `nprocs` shim. Orch `0a564a1f` (plus the contention-matrix re-bench, topology
  `4893e37e`), research `75ee1b8e`. Serving proof: :8083 pid 2009477 logs `n_slots = 4, n_ctx_slot = 196608,
  kv_unified = 'true'`; a 124k-token request served; jfk.wav RTF 0.20; TTS first packet 97 ms; both speech
  services 0 VRAM; `orchestrator_stack.py status` shows no attestation warnings; promotion gate green. The text
  below is the pre-revision plan, kept for the record.
  - Defaults: patches 1–3. Recommended funding: `-np 2 + -kvu + O-2`.
  - O-2 measured neutral: per-request 39.4 vs 37.1 tok/s at 2k and 41.0 vs 41.3 at 8k, acceptance 0.428/0.420 vs
    0.403/0.448. The package's buffer model says it frees 0.35 GiB, which raises card headroom from 0.18 to
    0.53 GiB.
  - Optional: MTP depth 8 → 4, measured neutral. Acceptance is 0.63–0.66 vs 0.40–0.46; per-request 40.0 vs 37.1
    (np2 2k), 40.3 vs 41.3 (np2 8k), 29.7 vs 29.0 (np4 8k), i.e. within ±2.5% except the +7.8% cell. It uses
    1014 MiB less whole-device VRAM at `-np 2 -c 196608 -kvu` (load-only).
    That workload was olympiad-style, so **confirm on production traffic** (KVU-1b) before the recipe changes.
  - Run package §5 phases 7–8 and all seven §6 serving proofs. Report what each proof returned; `healthy` is not
    proof.
- [ ] **KVU-1a — opencode `limit` (N-3).** Apply `patches/opencode-OPERATOR-ACK-limit.patch` (operator, outside
  containment) together with the reload, then restart opencode. Retire this manual step once the overflow branch's
  `/v1/models` `context_length` (T7) is live and opencode reads it.
- [ ] **KVU-1b — production-traffic confirmation of MTP depth 4** before changing `--spec-draft-n-max`. Compare
  `mean len` and t/s on real planner traffic at equal prompt length, with the §6 rollback thresholds.
  - **2026-09-24 M-3 (log-only): NOT confirmed.** Depth 4 went live with OP-54 before this check. Depth-8
    production arm n=240 (median context 63.5k, mean accepted 4.86, acceptance 0.483, 38.2 tok/s); depth-4 arm
    0 organic requests (its 22 are probes or M-4). A truncation projection from the depth-8 log — a model, not a
    measurement — puts depth 4 at 0.93× depth 8 for the median request and 1.01× aggregate; positions 5–8 carry
    27.5% of accepted tokens on production traffic. Research
    `artifacts/np_context_kvu_study_20260924/m3_depth_production.md` (`07060eaa`).
  - [ ] **M-3b — resolve depth 4 vs 8 at production context.** Let organic depth-4 traffic accrue to ~175
    requests (resolves an effect of ~8%), re-run the M-3 log read, and if the difference is inside 8% run a
    same-window A/B (depth 8 vs 4 alternating on :8083) for the ~2.5% effect. If depth 4 loses by more than the
    §6 rollback threshold, revert `draft_max` to 8 through a stack-change reload.
  - **SUPERSEDED 2026-10-03 (KVU-1b and M-3b):** :8083 no longer runs MTP. Since `RATIFY-STACKCHG-DFLASH2-20261003`
    it serves DFlash2 (`--spec-type draft-dflash --spec-draft-n-max 8`, clamped to 7; PID 3793153), so MTP depth 4
    vs 8 has no production arm left. The DFlash2 depth question (n-max 7 vs 8) is KVU-16; the production-shape
    speed/correctness check is `qwen38-27b-replace-qwen36.md` Q38-T7. Boxes left for their owner to close.
- [x] **KVU-1c — add the context-checkpoint read to the serving proof.** ✅ 2026-09-24 — :8083 was reloaded
  with `LLAMA_ARG_LOG_VERBOSITY=4`; its log since the np4/kvu launch holds 26 `created context checkpoint` lines
  (first: slot 3, task 1, `checkpoint 1 of 32`, 150.2 MiB), read-only from
  `epyc-orchestrator/logs/llama-server-8083.log` at 19:54Z. Original task: With `-lv 4`, confirm `created context
  checkpoint` fires on :8083 (audit #8 / T14). This is the only partial-prefix reuse the hybrids get.
- [ ] **KVU-1d — replace the `vram_non_kv_gib` UNVALIDATED line** (still open after bring-up: research
  `75ee1b8e` declares 32.80 as UNVALIDATED, and the package's proof step 2 reading was not written back) with KFD − 6.375 from the M-1 reading. Record the
  reading through SSU-F3's prepared claim tuple (RTG-19; SSU-F3 itself is done).
  - 2026-10-03: the master figure is now `vram_non_kv_gib: 37.92` MEASURED for DFlash2 (research `be2cc414`, KFD on
    PID 3737649 minus 6.38 GiB KV, `vram_non_kv_drafter: dflash2`); the load-time peak was sampled at bring-up
    (43.49 GiB card-total, `qwen38-27b-replace-qwen36.md` Q38-T8). The 32.80 UNVALIDATED line is gone. Still open
    here: recording the reading through SSU-F3's claim tuple.
- [x] **KVU-1e — M-4: np4 aggregate under concurrent load, live.** ✅ 2026-09-24 — live :8083 (np4, kvu, depth
  4), fixed-length 1024-token generations (`ignore_eos`), 2 waves per level: aggregate 40.2 / 39.9 tok/s at
  concurrency 1, 71.4 / 67.8 at 2, 95.3 / 93.1 at 4; per-request median 40.5 / 40.2, 36.4 / 34.9, 27.6 / 26.1.
  Research `m4_np4_concurrent_live.json` (`07060eaa`). Feeds KVU-8.
- [x] **KVU-2 — size `serving_shape.cache_ram` per server** ✅ 2026-09-24 — applied with OP-54: live argv
  `--cache-ram 65536` on :8083, `32768` on :8070 and :8074 (and the frontdoor halves), `0` on :8086 (read from
  `/proc/<pid>/cmdline`). (audit #4 / T8; OP-55). Today every server runs the
  8192 MiB default, and one full-pool 27B prompt (~9.2 GiB, inferred) does not fit.
  - Recommendations: 65536 MiB on :8083 (floor 24576), 32768 on :8070, 16384–32768 on :8074, 0 on :8086.
  - The value compiles to `-cram` already. Land it at the same :8083 reload if the operator agrees; a second
    reload costs a planner transient.
- [x] **KVU-15a — close step 1's two known gate limits** ✅ 2026-10-04 (filed 2026-10-03, workspace-ec, from the KVU-15 landing,
  orch 2586a7bb). **BUILT 2026-10-03, NOT DEPLOYED:** orch cdf0f9b4 (host-wide `fcntl.flock` lease per server,
  `ORCHESTRATOR_KV_POOL_CROSS_PROCESS_LEASE=0` reverts; new-token sizing from the longest prefix an IDLE slot holds,
  margin `ORCHESTRATOR_KV_POOL_CACHE_CREDIT_MARGIN_TOKENS`), integrated on orch `integ/api-reload-2-ec` 10bc5681; not
  ticked until deployed and the done-when replay below has run (deploy = UFH14-DEPLOY-EC in
  `agentic-serving-harness-fixes.md`). (1) The long-prefill lease is per uvicorn worker; across the 6 workers it relies on `/slots`, which sees a
  long prefill only after ~4096 processed tokens plus a 1.5 s cache, so two workers can start long prefills seconds apart:
  move the lease to a cross-process primitive (flock or the region-lock layer). (2) Size is judged on the whole prompt, so a
  mostly-cached long prompt still waits: subtract the matching slot's cached prefix (`cache_n` from the serving records)
  when estimating new tokens. Done when a 2-worker replay shows peak 1 long prefill and a cached-prefix request is not held.
  - **DEPLOYED 2026-10-03 ~14:50Z, pending live verification** (UFH14-DEPLOY-EC: merged to orch main 10bc5681, now
    aa1d6894; API-only reload → PID 1628390; full `tests/unit` 15979 passed / 0 failed). The flock lease half is live.
    The 2-worker replay waits for the :8083 restore (KVU-16e). The cached-prefix half **cannot pass in production as
    built**: the credit is inert, see the finding and KVU-15c below. Not ticked.
  - **Post-restore, 2026-10-03 ~15:40Z (workspace-ec): nothing new proven for the lease.** The only dispatched
    calls since the :8083 restore are three short passthrough calls (15:39Z, `serving_calls.jsonl`), far below the
    16384-token long-prefill threshold, so neither the flock lease nor the credit was exercised. The 2-worker replay
    is still the proof. Since 15:43:08Z :8083 runs a `LLAMA_SERVER_SLOTS_DEBUG` window (UFH14-DIAG-EC-a, experiment
    id `UFH14-A7`), where the credit goes live only because debug exposes slot text: the replay's lease half may run
    there, but its cached-prefix half must not be read from that window.
  - **PASSED LIVE 2026-10-04 02:48–02:52Z (workspace-ec), production flags** (SLOTS_DEBUG off, `slots_debug_env:
    null`), evidence `/mnt/raid0/llm/tmp/gpu-block-27b-20261003/results/ec2_lease/`:
    - Lease half (run `20261004T025039Z`): two concurrent ~24k-token passthrough prompts; the flock lease was held by
      2 different API worker PIDs (3858210, 3858214), never at once (max holders 1, 1042 samples); :8083 max 1 slot
      prefilling; B waited 48.9 s for A's prefill. Peak 1 long prefill across workers.
    - Cached-prefix half (run `20261004T024825Z`): call 2 extended call 1, was credited 18,829 tokens (KVU-15c
      `fp_history`), sized as a 7,197-token prefill (`long_prefill: false`) and admitted after 5.3 ms, i.e. not held.
    - Both halves of the done-when hold, so ticked. The credit run was sequential rather than inside the 2-worker
      replay; the lease run had no cached prefix (both `cache_n` 0). UFH14-DEPLOY-EC-2a/2b record the same proofs.
  - **Finding, 2026-10-03 (workspace-ec): the cached-prefix credit is inert in production.** It reads the prompt
    text an idle slot holds from `/slots`. v10 returns slot prompt text only under `LLAMA_SERVER_SLOTS_DEBUG`
    (`tools/server/server-context.cpp` `to_json` :699-730; `slot.to_json(slots_debug == 0)` at :2541, prompt only under `!only_metrics` at :726). With debug off, a
    busy slot reports `n_prompt_tokens` / `_processed` / `_cache` but no `prompt`. Live check on :8074: an idle slot
    reports only `id`, `is_processing`, `n_ctx` and `speculative`. So the credit always falls back to whole-prompt
    sizing. That is safe, but the credit is never applied. Step 1's `/slots` prefill observation is unaffected,
    because it reads token counts, not text.
  - [x] **KVU-15c — re-base the cached-prefix credit on orchestrator-side prefix history, not `/slots` text.** ✅ 2026-10-04 (filed
    2026-10-03, workspace-ec, from the finding above)
    - Keep a per-port history of recent `prefix_fp` fingerprints and the server-reported `cache_n` from the UFH14-B4
      serving records. Credit a request with the longest prefix that history says a slot or `--cache-ram` holds,
      less the margin.
    - Until it lands, make the fallback visible: count and record `cache_credit_unavailable` (reason
      `slots_no_prompt`) on every serving record where the credit could not be computed, so an inert credit no
      longer looks like zero hits.
    - Do not read the KVU-15a credit from a `LLAMA_SERVER_SLOTS_DEBUG` window (UFH14-DIAG-EC-a): the credit goes
      live there only because debug exposes the text.
    - Done when the 2-worker replay shows a cached-prefix request admitted with a non-zero credit on a
      production-flag server, and the KVU-15a done-when passes.
    - **BUILT and DEPLOYED 2026-10-03 (workspace-ec); live proof pending, so not ticked.** orch 0f0bfa19 on main,
      API-only reload.
      - `src/scheduling/prefix_history.py` is a per-server LRU of served prompts, keyed by the UFH14-B4 `prefix_fp`
        ladder, with server-measured tokens (`timings.prompt_n + cache_n`). It is kept in-process plus a host-wide
        JSON file under flock, so a follow-up turn on another uvicorn worker is credited too. An entry survives only
        within the `--cache-ram` volume, an 1800 s window and the same server launch.
      - `kv_pool_admission` credits the longest matched prefix; `/slots` text stays a second source.
      - Serving records carry a `kv_admission` block: `cache_credit_source` (`fp_history` | `slots_text` | none),
        `cache_credited_tokens`, and `cache_credit_unavailable` per source. That also covers the "make the fallback
        visible" bullet above.
      - Tests: `tests/unit/test_kv_prefix_history.py`, plus passthrough wiring in `test_passthrough_route.py`.
      - Live proof: the GPU-block runner's `deploy_ec2_lease.py` (step 1 of
        `/mnt/raid0/llm/tmp/gpu-block-27b-20261003/RUNBOOK.md`, :8083 serving and not parked, SLOTS_DEBUG off). PASS
        means call 2's record has `cache_credit_source == "fp_history"`, `cache_credited_tokens > 0` and
        credited / `timings.cache_n` within 0.5-1.5. It runs in the coordinated GPU block after ~18:15Z.
    - **PASSED LIVE 2026-10-04 ~02:49-02:50Z (workspace-ec)**, :8083 at production flags (`slots_debug_env: null`):
      call 2 `kv_admission.cache_credit_source == "fp_history"`, `cache_credited_tokens` 18,829 vs server
      `timings.cache_n` 22,178 (ratio 0.849); call 1 recorded `cache_credit_unavailable` `{fp_history: no_match,
      slots_text: slots_no_prompt}`, so the fallback is visible. The KVU-15a done-when also passes (above). Evidence
      `/mnt/raid0/llm/tmp/gpu-block-27b-20261003/results/ec2_lease/20261004T024825Z/report.json`. This opens the
      KVU-15b count (≥ 200 credited calls).
  - [ ] **KVU-15d — primitives-lane serving records must say whether the call held the long-prefill lease.** (filed
    2026-10-03, workspace-ec, found while preparing the GPU-block runner) Passthrough records carry
    `passthrough.long_prefill`, but primitives-lane `serving_call.v1` records have no `long_prefill` field, only
    `queue.pre_dispatch_wait_ms`, which mixes lock, placement and lease wait. So the KVU-15a lease cannot be read
    from organic primitives traffic. Add `long_prefill` (and the lease wait in ms) to the primitives record through
    the same staging path that sets `kv_admission`, with a test. Done when a primitives record for a long prompt
    carries `long_prefill: true` and its lease wait.
    - *(2026-10-21 triage)* open (no evidence found); only later mentions are agentic-serving-harness-fixes.md:479,499 still citing it as missing.
  - [ ] **KVU-15b — measure cache-credit misses on the serving records.** (filed 2026-10-03, workspace-ec; owner's
    decision was keep the credit and measure) On unified-KV servers the credit assumes the matched prefix survives in
    `--cache-ram`; a miss costs one extra concurrent long prefill. After KVU-15a is live, count calls admitted with
    `cache_credited` whose server-reported `cached_prompt_tokens` (`timings.cache_n`) fell short of the credited
    prefix, over ≥ 200 calls on :8083 (two windows, two-sample persistence). Today `cache_credited` is an admission
    counter and a passthrough-record field; put it on every `serving_call.v1` record first if it is missing there.
    Remove or narrow the credit if misses persist above ~5% of credited calls.
    - **Moot until KVU-15c (2026-10-03).** In production the credit never fires (finding above), so there is nothing
      to miss. Re-scope against KVU-15c's history-based credit once it lands. Records from a SLOTS_DEBUG window do
      not count.
    - 2026-10-03 (workspace-ec): the field half is done. Since orch 0f0bfa19, every serving record carries
      `kv_admission.cache_credited_tokens` and `cache_credit_source`, on the primitives and passthrough lanes. The
      count still waits for KVU-15c's live proof and then ≥ 200 credited calls.
    - *(2026-10-21 triage)* open (no evidence found); agentic-serving-harness-fixes.md:522 says window records are not a baseline.
- [x] **KVU-16 — :8083 KV-pool step 2: one stack change for `-c 393216`, a 262144 per-request cap, n-max 7** ✅ 2026-10-03 (workspace-ec) — LIVE. SIGNED 2026-10-03T11:50:52Z, RATIFY-STACKCHG-KVPOOL-20261003; research 412e8fc1, orch 09e91e1e + 841935ea, archive root 64d70d17 (`artifacts/operator/stack-change-kvpool-20261003/`; live evidence in `/mnt/raid0/llm/tmp/stack-change-kvpool-20261003/{apply,evidence}/`). Bring-up after workspace-89's "F12 done": `reload architect_critic` → PID 4052768 at 13:14:35Z, argv `-c 393216 … --spec-draft-n-max 7` (`evidence/argv_8083_live_post_relaunch.txt`); server log "slot context (393216) exceeds the training context (262144) - capping", `n_slots = 4, n_ctx_slot = 262144, kv_unified = 'true'`, no clamp-to-7 warning. Load-peak VRAM 50.78 GiB (`evidence/vram_during_reload.log`). API reload → PID 4054223; `context_limits` per_request 262144, kv_unified True, shared_pool True, pool_tokens 393216. Alias completion via :8000 `coder_escalation` correct with draft acceptance logged (`apply/completion.json`). `stack_change_pipeline check --run-promotion-gate` all ok incl. runtime_attestation (`apply/check-final.out`). The 4 × 90k concurrency probe is NOT a pass — see KVU-16b/16c; full-pool concurrent residency is UNPROVEN, not disproven. :8083 has been stopped for the INF-80 X0 window since 13:55Z (KVU-16e restores it).
  - Original scope:
  (operator-approved 2026-10-03, IN PACKAGING; decision package
  `/mnt/raid0/llm/tmp/kv-sizing-8083-20261003/DECISION.md` §4 step 2). One :8083 relaunch carrying: `-c` 196608 →
  393216 unified at np 4 (+4.86 GiB → ~51.4 GiB, 12.5 GiB free; four concurrent p90 prompts fit); an orchestrator
  per-request cap of 262144 (= `n_ctx_train`; `context_limits.py` `per_request_n_ctx` must take
  `min(n_ctx, n_ctx_train)` once `-c` exceeds it); `--spec-draft-n-max` 8 → 7 (the kernel already clamps to 7; the
  GDN ring is sized from the unclamped value, so 7 should save ~0.58 GiB); re-derive `vram_non_kv_gib` for the new
  depth (DRAFT-SEL-1's `check_lean` refuses a selection whose VRAM was not re-derived). Bring-up with `-lv 4`:
  read the `llama_kv_cache` / `memory_recurrent` / `sched_reserve` lines and KFD at load (expect ~51.4 GiB), then
  one synthetic 4 × 90k concurrent replay: zero "failed to find a memory slot", KFD peak ≤ 62 GiB. Before
  packaging, run DECISION §4 measurement 1 (zero compute: regress per-slot decode vs pool high-water on the
  existing log); if decode with neighbours is >15% slower at 300k+ fill than at 100k, take option (c) split
  4 × 163840 instead. Fix the "3 GiB" comment at `stack_manifest.py:1690` (code uses 2.0) in the same package.
  - [ ] **KVU-16a — replace the derived `vram_non_kv_gib` with the measured one.** (filed 2026-10-03, workspace-ec,
    from the KVU-16 bring-up) The package carries a derived 39.15 GiB; the bring-up measured 50.78 GiB load peak −
    12.75 GiB KV pool ≈ 38.03 GiB (`evidence/vram_during_reload.log`). Land the measured value in the research master
    with its evidence pointer through the stack-change pipeline (registry value, DRAFT-SEL-1 `check_lean` reads it),
    and recompile. Done when `check` passes and the lean carries 38.03 with an evidence path.
    - *(Annotation, workspace-ec, 2026-10-04.)* **PACKAGED, VALID, awaiting the operator's signature** in
      STACKCHG-HYGIENE-20261003 (`/mnt/raid0/llm/tmp/stack-change-hygiene-20261003/PACKAGE.md`; `--validate-only`
      VALID, 68 pins; `validate-main.out`): 39.15 derived → 38.03 measured (50.7822 GiB load peak − 12.75 GiB KV pool;
      evidence copied to `evidence/vram_during_reload_8083_20261003.log`). Argv identity 11/11 live servers, so no
      relaunch. Not ticked until signed, applied and `check` passes.
    - *(Annotation, workspace-ec, 2026-10-04.)* 38.03 GiB is right as a LOAD-time figure, and OP-72 can be signed
      as packaged. However, :8083 grows +7.2 GiB while serving (KVU-16h), so the load-time figure understates the
      runtime peak. The runtime term is KVU-16i; it does not change this item.
    - *(2026-10-21 triage)* open (no evidence found).
  - [x] **KVU-16b — a corrected concurrent-residency proof for the 393216 pool.** NOTE (2026-10-03, workspace-89 P3 code read): production runs `cache_idle_slots` ON, so idle slots are flushed to RAM at each task launch and the pool can only fill with ACTIVELY GENERATING sequences. The proof must hold 4 long contexts DECODING at once (long `n_predict`), not parked. P3 part A1 uses `--no-cache-idle-slots`: cite it only as a mechanism result, NOT as a production residency proof. (filed 2026-10-03, workspace-ec) ✅ 2026-10-26 (workspace-58) PASS, predicate `request-task-prompt-end-v1`: 4 requests decoding past prompt-end at once, 324673 resident cells with all 4 decoding (pool 393216), KFD peak 48.567 GiB <= 62, 0 failed requests / slot errors / faults; one load of the current champion c72/10419, `-np 4 -c 393216`. Evidence `/mnt/raid0/llm/tmp/cal-1026/kvu-16b/out/native/kvu16b/20261026T214759Z/report.json` + `out/RUN_RECORD.json`. NO rate/performance claim, no promotion; the earlier INVALID prompt_end data stays invalid; child result, not KVU program closure. [belief: cc]
    - **Correction (2026-10-03, workspace-ec, from the P3 report):** the idle-purge claim above is a CODE READ, not a
      measurement. P3 arm A0 ran at the exact production flags and did NOT reproduce the purge: its neighbour slot held
      0 tokens before the probe task, so the purge path was never exercised (inconclusive). "Production always purges
      idle slots" is therefore NOT proven. The design rule stands anyway: holding 4 contexts DECODING at once is valid
      whether or not idle slots are purged. Measuring whether the purge happens is folded into UFH14-B4i's A/B.
    - **Second correction (2026-10-03, workspace-ec, read-only log read while preparing the GPU-block runner): the
      purge IS real on organic traffic.** `logs/llama-server-8083.log` holds **211 idle-slot purges of non-empty
      slots** between log lines 35430 and 130878. Each is a `saving idle slot to prompt cache` line followed by
      `clearing prompt with N tokens` with N > 0, 11.5 M tokens in all. The latest is line 130621, `id 2 | clearing
      prompt with 84951 tokens`. All are at the previous kv-unified shape (np 4, `n_ctx_slot` 196608), before the
      393216 relaunch. So "not reproduced" described P3 A0 only, not production. At the current shape it is still to
      be shown; `kvu16b_residency.py` records it with an optional 1-token purge probe.
    - Runner prepared, dry-run OK: `/mnt/raid0/llm/tmp/gpu-block-27b-20261003/kvu16b_residency.py` (RUNBOOK step 4,
      :8083 serving with its roles parked). It holds 4 long contexts decoding at once and samples `/slots` and KFD
      during the run. Exit 0 = PASS against the done-when above. It runs in the coordinated GPU block after ~18:15Z.
    The probe (`evidence/concurrency-probe-20261003T135133Z.json`) failed its own criterion: max cells in flight 92,343
    vs ≥ 300k. What held: 4 × 89,921-token requests all 200, zero "failed to find a memory slot", zero "Context size
    has been exceeded", 4 slots processing at once, KFD peak 51.73 GiB (≤ 62). Why it failed: the server prefilled
    largely serially (done at 263 / 682 / 1328 / 2166 s) and `n_predict 64` freed each request's cells right after its
    prefill. Re-run with long generations (`ignore_eos`, n_predict large enough to outlast the slowest neighbour's
    prefill) so all four contexts are resident at once; sample `/slots` cells and KFD during, not after. Done when
    peak resident cells ≥ 300k with zero memory-slot lines and KFD ≤ 62 GiB. Closed instead by KVU-16c if that
    evidence exists. Needs a :8083 window, so it runs after the X0 hand-back (KVU-16e).
    - **2026-10-04 (workspace-ec): RAN; the runner said PASS, but the PASS is INVALID, so this box stays open.**
      The run is `results/kvu16b/20261004T032520Z/`, with a durable copy in
      [`artifacts/gpu-block-27b-20261004/results/kvu16b/`](../../artifacts/gpu-block-27b-20261004/results/kvu16b/).
      workspace-89's read-only root cause is `artifacts/gpu-block-27b-20261004/analysis/kvu16b-rootcause-REPORT.md`
      (original at `/mnt/raid0/llm/tmp/kvu16b-rootcause-20261004/REPORT.md`).
      - **Why the PASS is invalid:** the predicate `proc and n_dec > 0` reads a stale `n_decoded`, which resets only
        at prompt end. Request i=3 (server slot 0) was still prefilling (60.7k of 79.8k) at the PASS sample, so the
        true peak was 3 decoding + 1 prefilling.
      - **What held:** ~310k cells resident, zero "failed to find a memory slot" lines, KFD 58.88 GiB (≤ 62).
      - **Decode collapsed to 0.52 tok/s summed** (≥ 90% confidence). Prefill shares every server batch with decode:
        each iteration is the 8-row verify for every decoding slot plus ~2024 prompt tokens (`n_batch` 2048). So each
        decoding slot advances one verify step per prefill chunk. Without the masked-block skip, a chunk's attention
        reads every occupied cell, at T ≈ 2.6 s + 0.052 s per 1k cells: **17–19 s per chunk at 240–310k**. Drafting
        stayed healthy at 2.8–4.2 tokens per step; only the step rate collapsed. TTFT climbs for the same reason
        (prefill 440 → 232 → 146 → 115 tok/s for i=0..3). Context checkpoints, the drafter, `--cache-ram` and an FA
        fallback are ruled out.
      - **VRAM grew while serving:** 51.69 GiB at load, then 58.88, then 59.77 GiB during Q38-T7 #2 and still
        rising. That is +7.2 GiB, and only ~2.2 GiB of margin to the 62 GiB gate. See KVU-16h.
      - Fixes, cheapest first: KVU-16f (`-b 512`), KVU-16g (a prefill budget while slots decode), KVU-19a in
        production (workspace-89's fold, KVU-19; ~3.5× alone, ~10× with KVU-16f), KVU-19b, and KVU-20.
    - [x] **KVU-16b-1 — fix the residency runner's decoding predicate, then re-run KVU-16b.** (filed 2026-10-04, ✅ 2026-10-27 [belief: cc]
      - *(2026-10-27, workspace-58 results harvest)* Re-run on champion c72ec82f5/10419 (:8083 argv on scratch :18436, request-task-prompt-end predicate) PASS: 324,673 cells resident with 4/4 requests decoding (gate >=300,000), KFD peak 48.57 GiB (gate <=62), 0 failed/memory-slot/fault lines, 898 residency samples; decode sum 32.08 tok/s; n=1 replay. Capability proof. Artifact `/mnt/raid0/llm/tmp/cal-1026/kvu-16b/out/native/kvu16b/20261026T214759Z/report.json`.
      workspace-ec) In `kvu16b_residency.py:203,260` (durable copy
      `artifacts/gpu-block-27b-20261004/runners/`), count a slot as decoding only when `n_proc >= prompt_tokens` or a
      first token has been observed for its request. Key the report by request index, not by server slot (request
      i=3 ran on server slot 0). Treat `/slots` poll timeouts as samples missed during an iteration, not as slot
      errors. Re-run after KVU-16f or KVU-16g lands; otherwise the run measures the interleave again. Done when the
      runner's PASS requires 4 slots past prompt end at once, and a re-run meets the done-when above.
      - *(Evidence pointer, ak-ds41-main, 2026-10-04; not a tick.)* The 05:08-06:20Z GPU slot re-ran the KVU-16b
        replay with a fixed predicate (decoding = past prompt end; report keyed by request index) in its own copy,
        `artifacts/gpu-slot-ak-20261004/runners/kvu16b_residency_slot.py`. The durable runner is unchanged. Results under
        KVU-16f below.
      - *(2026-10-21 triage)* open (no evidence found).
    - *(2026-10-21 triage)* open (no evidence found); corrected probe still referenced as pending in agentic-serving-harness-fixes.md:200.
  - [x] **KVU-16f — A/B `-b 512 -ub 512` on :8083, then one stack change.** ✅ 2026-10-25 (A/B 2026-10-04, signed STACKCHG-8083BATCH, serving since 10-07; `cal-1025/kvu16f-b512/REDUNDANT.md`) [no-belief: duplicate-of: 10-04 A/B (artifacts/gpu-slot-ak-20261004); cc-register pending (VB-CC-PILOT)] (filed 2026-10-04, workspace-ec, from the
    KVU-16b root cause, fix 1) `-ub` alone does nothing: the server packs `n_batch` prompt tokens per iteration. At 512,
    the root cause predicts an iteration of ~4.7 s at 300k (~4× faster decode while a prefill runs) and a KQ mask
    1536 → 384 MiB (−1.1 GiB). The registry's mask term must then be re-derived. The cost is a possible 10–20% lower
    solo prefill at shallow depth. Measure in a coordinated :8083 window: the KVU-16b runner (s per chunk and decode
    while prefilling, after KVU-16b-1), plus Q38-T7 phase B at 80k (prefill rate, paired correctness). Then ship it as
    ONE stack change together with UFH14-B4j (`--no-cache-idle-slots`). Done when the A/B is recorded here and the
    combined package is signed and serving.
    - *(Evidence pointer, ak-ds41-main, 2026-10-04; not a tick — the owner decides what it closes.)* GPU slot
      `gpu-slot-ak-20261004`, 05:08-06:20Z, :8083's argv on scratch :18183, build `gpu-20261004-c7f5ac9ad`, KVU-16b replay
      (4 × ~80k staggered) with the fixed predicate. Durable copy:
      [`artifacts/gpu-slot-ak-20261004/`](../../artifacts/gpu-slot-ak-20261004/).
      - **skip OFF (the v10-equivalent path), `-b 512` vs `-b 2048`:** 3.5–4.2× decode while a neighbour prefills; KFD
        peak 48.57 vs 51.69 GiB (−3.1 GiB); solo shallow prefill TTFT 208.3 vs 154.2 s (−26%, outside the 10–20% the
        root cause predicted). Both arms hit the 20-min cap with at most 3 decoding.
      - **skip ON + `-b 512`:** 7.91 vs 0.56 tok/s summed decode while the last request prefills (14×); all 4 requests
        decode at once at 7.7–10.7 tok/s each; PASS in 926 s. skip ON + `-b 2048`: 2.30 tok/s summed, PASS in 781 s.
      - **Attribution:** every skip-ON arm is the combined 19a+19b build INCLUDING commit 2 (WMMA seq tiles), which is not
        in the KVU-19 fold. Do not attribute skip-ON numbers to the fold (cf. KVU-19b-fold-c1 / rework-c2).
      - Not covered: Q38-T7 phase B at 80k (paired correctness) and P3 v2 (skipped for budget). Greedy spot-check text
        was identical across all four arms (no classifier).
    - *(2026-10-04 ~08:00Z, workspace-ec; not ticked until signed and serving.)* **The combined package is VALID and
      greenlit by workspace-ec; it awaits the operator's terminal signature.** `STACKCHG-8083BATCH-20261004`
      (`/mnt/raid0/llm/tmp/stack-change-8083-batch-20261004/PACKAGE.md`): part B `-b 512 -ub 512`, part A
      `--no-cache-idle-slots` (UFH14-B4j); `--validate-only` VALID (`evidence/validate-only.txt`). Signing token
      `RATIFY-STACKCHG-8083BATCH-20261004`; the operator runs `ratify_stackchg_8083batch_20261004.sh` from an interactive
      terminal (TTY-gated). It applies at the :8083 restore after YaRN E1 (one relaunch, package §8.2). Stated cost: solo
      shallow prefill −26% (383.8 vs 518.0 tok/s), TTFT +35%; KVU-16g is the follow-up that removes it. With KVU-16h
      attributed, `-b 512` also lowers the replay's growth (+0.79 vs +1.42 GiB) but does not bound the `n_max: 0`
      mechanism; that is KVU-16h-fold.
    - *(2026-10-21 triage)* open (no evidence found); no stack change with -b 512 -ub 512 in git after 10-07; KVU-16g (decode-aware budget) is the preferred form.
    - *(2026-10-25, workspace-58 wrap-up; ticked.)* Both halves of the done-when hold; the 10-21 triage looked in git, not at the live launch record. Citations (`/mnt/raid0/llm/tmp/cal-1025/kvu16f-b512/REDUNDANT.md`): (1) the A/B is recorded above (10-04, `artifacts/gpu-slot-ak-20261004/`); (2) the package is signed: `/mnt/raid0/llm/tmp/stack-change-8083-batch-20261004/receipts/RATIFY-STACKCHG-8083BATCH-20261004.json` (part B `-b 512 -ub 512`, part A `--no-cache-idle-slots`) with `evidence/apply-proof.txt`; (3) it is serving: `epyc-orchestrator/logs/server_launches/8083.json` (launched 2026-10-07T02:52Z) carries `-b 512 -ub 512 … --no-cache-idle-slots`, and GPU-LEAK-1b/1d (10-23) probed that exact argv. No launcher was written for a re-A/B: the incumbent IS the 512 arm. A re-A/B on the current champion would be a new question, owned by KVU-16g-1 (off/b512 arms).
    - [ ] **KVU-16f-1 — re-derive the registry's KQ-mask term for `-b 512` (filed 2026-10-25, from the KVU-16f residue).** The box predicted the mask falls 1536 → 384 MiB at `-b 512`; the 10-04 A/B measured KFD peak −3.1 GiB. Update the :8083 memory term in the master registry (research `orchestration/model_registry.yaml`) from the measured value, citing the A/B. Docs/registry only, no compute, no reload. Done when the term matches `-b 512` and cites the A/B.
  - [ ] **KVU-16g — decode-aware prefill budget on llama-server (Sarathi-style), experimental tree.** (filed 2026-10-04,
    workspace-ec; KVU-16b root cause fix 1e, KV-serving survey Rec 1) In `update_slots()`, cap the prompt tokens added
    per iteration while any slot generates (`--prefill-budget-decoding N`, or sized from a per-step time target), and
    keep `-ub 2048` for solo prefill. This shields decode without shrinking solo prefill batches, so it is the better
    form of KVU-16f. **In flight 2026-10-04:** a subagent is building it on `llama.cpp-experimental`
    (`/mnt/raid0/llm/tmp/prefill-budget-20261004/`). Risks to check: more checkpoint-creation points, and DFlash2
    verify-row indexing in `post_decode` (cf. KVU-7). Done when the KVU-16b re-run shows decode under a neighbour's
    prefill ≥ 4× better at ≤ 30% TTFT cost on the prefilling request, with `test-backend-ops` and a paired correctness
    check green. Ships with the next kernel version (four-step workflow), not as a flag on v10.
    - *(2026-10-04 07:15Z, workspace-ec; built, GPU-unvalidated, so not ticked.)* **Rebased onto the folded champion.**
      Branch `experimental/prefill-budget-on-fold-20261004` @ `65d48a7a0` (byte-identical cherry-pick of `338c5f84f`
      onto `1bceceb05`), pushed to `fork`. Store builds `kernels/builds/{gpu,cpu}-20261004-65d48a7a0` (build 10312,
      recipes identical, linkage PASS); CPU identity and dry-run checks in
      `/mnt/raid0/llm/tmp/prefill-budget-20261004/` (`FOLD.md`, `cpu_identity_summary.txt`, `dryrun2/`). The 27B A/B
      runner `gpu_slot.sh` is ready for schedule row 5c: arms off / b512 / pb512 / t1000, DEPTH 20000, NEIGHBOUR 80000,
      default build `gpu-20261004-65d48a7a0`.
    - *(2026-10-04 PM, workspace-ec; GPU A/B queued, so not ticked.)* **Rebased onto champion Y** as `98c0ce12a`. The
      slot's earlier refusal was a `pipefail` false alarm in the runner, now fixed. The row-5c GPU A/B (KVU-16g-1) is
      next in the GPU queue, on the Y-based build.
    - *(2026-10-21 triage)* open (partial: built and folded as V11-016 in docs/reference/kernel-manifests/llama-v11-manifest.md, but serving A/B and enablement are KVU-16g-1/-2).
  - [x] **KVU-16h — URGENT: attribute :8083's +7.2 GiB VRAM growth while serving.** ✅ 2026-10-04 (filed 2026-10-04, workspace-ec)
    KFD for pid 1703677 was 51.69 GiB right after load, 58.88 after Q38-T7 #1's concurrent prefill+decode traffic, and
    59.77 after Q38-T7 #2, still rising. That leaves ~2.2 GiB to the 62 GiB gate. The growth follows request shape,
    not KV occupancy: KVU-16b at 310k cells added nothing. Candidates: the ggml-cuda legacy pool (`NO_VMM=1` →
    `ggml_cuda_pool_leg`, which never frees), compute-buffer reallocation beyond the `n_seqs = n_seq_max` reserve,
    and rocBLAS/hipBLASLt workspaces. In a GPU window, relaunch :8083's argv on a scratch port at `-lv 4`, replay the
    Q38-T7 phases one at a time with phase markers, and sample KFD at 1 Hz. Done when the growth is attributed to a
    named allocator with a per-phase table, and either bounded by a flag or carried as a runtime term in KVU-16i.
    - **2026-10-04 PM (workspace-ec): ATTRIBUTED, CONFIRMED and FIXED** (KVU-16h-confirm, KVU-16h-fold below); the
      runtime term on v10 production stays in KVU-16i.
    - **2026-10-04 (workspace-ec): ATTRIBUTED; a fix is built, and GPU confirmation is pending, so the parent stays open.**
      Durable copy: [`artifacts/kvu16h-vram-20261004/`](../../artifacts/kvu16h-vram-20261004/) (replay summary, runner,
      shim analysis, follow-up scripts; originals `/mnt/raid0/llm/tmp/kvu16h-vram-20261004/`).
      - **Replay** (`results/20261004T063830Z/summary.md`, :8083's argv on a scratch port, `-lv 4`, allocator shim):
        +1.42 GiB over load, then a PLATEAU (mix1 −0.02, mix2 −0.00 GiB). The largest share is the ggml-cuda legacy pool
        (`GGML_HIP_NO_VMM`): 0.58 GiB target + 0.50 GiB draft, through `ggml_cuda_mul_mat_cublas` F16 dequant buffers.
        Arm B (`-ub 512`) grew +0.79 GiB.
      - **Why production grew +7.2 GiB when the replay plateaued.** The HIP-graph `mmvq_q8_1_graph_cache`, a LOCAL
        AutoKernel keep (`dd161d519`, `c0d42d81c`, `8a3049beb`), holds legacy-pool buffers from one capture until the
        next. A batch-1 capture's ~250 small holds take every free pool buffer, including the large cuBLAS dequant
        buffers, so each following >128-token prefill allocates a fresh set. Past 256 held buffers the overflow
        free-and-redrain grows VRAM linearly per decode/prefill alternation. The trigger is per-request
        `speculative.n_max: 0` traffic (no-draft requests alternate graph shapes). 0.29 GiB per event fits all four
        datasets.
      - **Latent use-after-free hazard:** the legacy pool can `cudaFree` a released buffer (slot overflow, the OOM-retry
        `clear_pool`) that a captured graph still references.
      - **Fix:** branch `experimental/mmvq-graph-cache-pool-20261004` @ `656c9a66b` (on the folded champion
        `1bceceb05`, pushed to `fork`). It gives the cache a private per-context device arena (4 MiB chunks, rewound at
        each capture, freed with the context), so it never touches `ctx.pool()`; kernels and q8_1 contents are
        unchanged. Store build `kernels/builds/gpu-20261004-656c9a66b`. Commit text:
        `artifacts/kvu16h-vram-20261004/mmvq-fix/COMMIT_656c9a66b.txt`.
    - [x] **KVU-16h-a — attribute the growth to a named allocator with a per-phase table.** ✅ 2026-10-04 (workspace-ec)
      Replay table plus the follow-up mechanism above: legacy pool, held by the local HIP-graph MMVQ q8_1 cache, triggered
      by `n_max: 0` requests.
    - [x] **KVU-16h-confirm — confirm the fix on the GPU (schedule row 4c, `gpu_slot_kvu16h_followup_c.sh`).** ✅ 2026-10-04 (filed
      2026-10-04, workspace-ec) Run `/mnt/raid0/llm/tmp/kvu16h-vram-20261004/gpu_slot_kvu16h_followup_c.sh` (durable
      copy in `artifacts/kvu16h-vram-20261004/scripts/`) in a coordinated GPU slot: the `n_max: 0` alternation that grows
      the champion must stay flat on `gpu-20261004-656c9a66b`, with output byte-identical and decode within noise.
      Done when the row-4c summary shows growth bounded (no per-event step) on the fix and present on the control.
      - *(2026-10-04 PM, workspace-ec.)* **CONFIRMED, and the fix HOLDS.** Run `fuc-20261004T110509Z` (own-pid KFD;
        durable copy `artifacts/kvu16h-vram-20261004/results/fuc-20261004T110509Z/summary.md`):
        - arm A (v10): +5.83 GiB over 21 `n_max: 0` → prefill events, 0.28 GiB per event (model 0.29); control +0.06.
        - arm B (`GGML_CUDA_DISABLE_GRAPHS=1`): +0.05 GiB, but no-draft decode −5.6% (31.38 → 29.63 tok/s).
        - arm C (fix `656c9a66b`, graphs on): +0.057 GiB over the same 21 events, no MMVQ pool pins, arena 1 × 4 MiB;
          decode +1.0% no-draft and +4.9% drafted vs A.
    - [x] **KVU-16h-fold — fold `656c9a66b` into the champion after KVU-16h-confirm passes.** ✅ 2026-10-04 (filed 2026-10-04,
      workspace-ec) Guarded fast-forward of `ak/champion/llama-cpp-ffc1bac82eec` from `1bceceb05` (its parent), the same
      CAS route as `artifacts/champion-fold-kvu19-20261004/scripts/advance_ref.sh`; G0 plus `test-backend-ops` ROCm0 on
      the folded build; the fold-table ledger entry goes through workspace-89. Done when the champion tip carries
      `656c9a66b` and the standing receipt is refreshed.
      - *(2026-10-04 PM.)* Folded in champion Y `61bdb185c` (the all-keeps fold, executed by ak-ds41-main with
        workspace-89; ledger in `autokernel-champion-aggregate.md`). Y gates: FA 2949/2949, MUL_MAT 1139/1139, 27B greedy
        Y ≡ X 3/3. Standing receipt refreshed: Y champion-only tg +0.35% (pp +18.2% is flagged as unpaired host drift).
    - [ ] **KVU-16h-runner — bench runners give `n_max: 0` (no-draft) arms their own server launch.** (filed
      2026-10-04, workspace-ec, from workspace-89's suggestion) Mixing per-request `speculative.n_max: 0` into a drafted
      server's traffic is exactly the KVU-16h trigger: it grows VRAM on every pre-fix build and alternates HIP-graph
      shapes, so a no-draft arm measured on a shared server contaminates both arms. In the shared bench runners
      (`p3_kvu_probe.sh`/`x0_common.py`, the KVU-16b replay, Q38-T7, `gpu_slot*.sh`), launch a dedicated server
      without `-md` for each no-draft arm. Done when no runner sends `n_max: 0` to a drafted server, with a check that
      refuses it.
      - *(2026-10-21 triage)* open (no evidence found).
      - *(2026-10-30, scoped current K35 no-draft arm protocol correction.)* Research source commit `b205f566a9271b7f8108e69bd0ec2349c6a320fd` changes the three currently tracked K35 no-spec scenarios to launch with `--spec-type none`, no draft model/switches, and no request-level `speculative.n_max: 0`; plan construction rejects a request-zero/drafted-server combination. Plans and results carry `kvu16h-dedicated-no-draft-v2`. Historical result files and interpretations are unchanged; prior request-local-zero runs are not measurements of this corrected launch recipe. The broader parent item remains open until coverage of all named legacy/shared runners is established; intentional trigger-attribution probes are separate experiments. No inference or new performance measurement was run. Validation log: `/mnt/raid0/llm/tmp/codex-ni-kvu16h-runner-20261030/scripts/benchmark/VALIDATION-KVU16H-20261030.log` (35 tests, SHA-256 `4ce3fedbad4ed02f682226e2b11fc3760996170bda8c214b5249053b2e7e6fcc`). [no-belief: implementation/tooling; no new measurement]
      - [x] **P3 private dedicated-lifecycle native diagnostic replay** ✅ 2026-10-28 — 20 decode-only rows (10 drafted / 10 no-draft), full native rc 0 at 2026-10-28 17:26:00 UTC, wall 4776.752 s, writer and captured-server cleanup verified. Evidence `/mnt/raid0/llm/tmp/codex-kvu16h-runner-20261028/run-20261028T160623Z-105416/{result.json,native/a1.json,native/p3_result.json,native/report.md}`; details `progress/2026-10/2026-10-28-rtg57-native-diagnostic.md`. Native report meets its two trigger thresholds, but this is indicative diagnostic evidence with disclosed CPU sibling co-tenancy and parked-neighbor flags, no deployment or decision-grade warrant. No retrospective measurement tuple. The parent task remains open for all named shared runners. [belief: cc]
  - [ ] **KVU-16i — the capacity gate must carry the RUNTIME peak, not only the load-time `vram_non_kv_gib`.** (filed
    2026-10-04, workspace-ec) The registry's non-KV figure is load-derived: 39.15 GiB derived, and 38.03 GiB measured in
    KVU-16a / OP-72, from the load peak. The runtime peak runs +7.2 GiB above that (KVU-16h). The capacity gate in
    `stack_manifest.py:1604-1626` therefore passes lineups whose serving peak is within ~2 GiB of the card limit. Add
    a measured `vram_runtime_growth_gib` term (or a runtime-peak field with an evidence path) per GPU server, and have
    `check_lean` / the capacity gate sum it. Done when the master carries the term for :8083 with KVU-16h's evidence,
    and the gate's arithmetic for :8083 reproduces the measured ~59.8 GiB peak.

    - *(2026-10-04, workspace-ec.)* KVU-16h is attributed to an unbounded mechanism on v10 and the current champion
      (legacy-pool growth per `n_max: 0` event), so the term does not shrink to the replay's +1.42 GiB plateau. Keep the
      +8.08 GiB runtime term until KVU-16h-confirm (row 4c) shows the fix bounds the growth; re-derive it from the
      confirm run's measured peak only then, and only for a build that carries `656c9a66b`.
    - *(2026-10-04 PM, workspace-ec.)* KVU-16h-confirm passed and `656c9a66b` is in the champion (Y). The term drops to
      the bounded ~1.42 GiB replay plateau only when a production kernel that carries `656c9a66b` serves (v11). Until
      then v10 production keeps the +8.08 GiB term, under the operating rule **no per-request `speculative.n_max: 0`
      against :8083** (KVU-16h-runner enforces it for bench runners).
    - [ ] **KVU-16i-v11 — at the v11 promotion, re-measure :8083's runtime term on the v11 build and lower it in the
      master.** (filed 2026-10-04, workspace-ec) Replay the row-4c traffic (with `n_max: 0` alternation) on the v11
      candidate; expect the ~1.42 GiB plateau. Done when the master carries the v11-measured term with its evidence path
      and the +8.08 GiB term retires with the v10 kernel.
      - *(2026-10-21 triage)* open (no evidence found); v11 not yet promoted.
    - *(2026-10-21 triage)* open (no evidence found).
  - [x] **KVU-16c — or cite workspace-89's P3 parked-neighbour run as the residency proof.** (filed 2026-10-03)
    ✅ 2026-10-03 — resolved: **NOT citable**, so KVU-16b runs. P3 A1 (`/mnt/raid0/llm/tmp/x0-27b-quants/results/p3/report.md`)
    had zero slot-failure lines, but it ran with `--no-cache-idle-slots` (not the production flag), and its ≈355k fill
    rests on the slot-restore replies: `/slots` showed only 156,971 resident tokens, because restored slots do not
    report `n_tokens` there. VRAM peak was 51.96 GiB (within ≤ 62 GiB). It is a mechanism result only.
    Workspace-89's X0 window carries the P3 probe (llama.cpp #28495, intake-1849#record: unified-KV flash-attention
    decode cost as the pool fills). If its parked-neighbour arm reports peak resident cells ≥ 300k with zero
    memory-slot lines, cite it here and close KVU-16b; otherwise run KVU-16b.
  - [x] **KVU-16d — act on the P3 decode-cost verdict: unified vs split per-slot.** (filed 2026-10-03, workspace-ec)
    ✅ 2026-10-03 — **DECIDED: keep the shared 393216 pool** (operator, 2026-10-03, this session's AskUserQuestion
    answer: "Keep shared 393k for now"). No split-per-slot stack change. Mitigation: rely on the one-long-prefill gate
    (KVU-15 / KVU-15a) and fix the kernel. The masked-block skip is KVU-19, implemented directly as KVU-19a.
    - 2026-10-03: P3 trigger MET (KVU-18 A1: −59.5% no-draft at ≈355k nominal fill, three parked neighbours; batched-bench
      kvu vs no-kvu −15.2% TG). workspace-ec is preparing the option (c) package. *(Superseded by the decision above;
      no package was prepared.)*
    - **Decision record, the options considered (VRAM at load, approximate):**

      | Option | Shape | VRAM at load | Effect |
      |---|---|---|---|
      | split 2 × 262144 | np 2, per-slot | ~52-55 GiB | full per-request context, but only 2 concurrent requests |
      | split 3 × 196608 | np 3, per-slot | ~57 GiB | per-request cap 196608, 3 concurrent requests |
      | split 4 × 163840 | np 4, per-slot (DECISION.md §4 option c) | ~59 GiB | per-request cap falls below 262144 |
      | **keep shared 393216** | np 4, unified | 50.78 GiB (measured) | **CHOSEN**: decode tax with resident neighbours remains until KVU-19 lands |

    - Reopen trigger: KVU-19a fails its validation, or the fold into the champion stalls, while organic traffic shows
      the neighbour decode tax (serving records, KVU-17).
    If P3 shows ≥ 15% decode loss at 300k+ pool fill vs ~100k, prepare the option (c) split stack change (4 × 163840,
    DECISION.md §4) for operator signature; if < 15%, record the verdict here and keep unified. Trigger: workspace-89's
    P3 result.
  - [x] **KVU-16e — restore :8083 after workspace-89's "X0 done" (ETA ~16:30Z 2026-10-03; extended, see below).** ✅ 2026-10-03 (filed 2026-10-03,
    workspace-ec) `orchestrator_stack.py reload architect_critic`; verify the live argv equals
    `evidence/argv_8083_live_post_relaunch.txt`, `context_limits` (262144 / unified / pool 393216) and one alias
    completion via :8000. :8083 is down from 13:55Z (stop verified: PID dead, VRAM 0.01 GiB; X0 argv record
    `/mnt/raid0/llm/tmp/ds41-c95/X0_ARGV_8083.txt`).
    - 2026-10-03, ~15:00Z: the X0 window was extended (granted) to a ~17:15Z hand-back. Order: X0 serving + KLD,
      then P3 (KVU-18, llama.cpp #28495), then LB1 (rocprof low-bit kernel roofline, operator-approved), then a
      speech stop plus EXL3 correctness. Whisper/TTS will be stopped for ~30 min near the end. The restore also
      unblocks the UFH14-DEPLOY-EC-2 live proofs (B6, RI-18c, KVU-15a, B4).
    - **DONE 2026-10-03 ~15:35Z (workspace-ec).** workspace-89 sent "speech back + X0 done" at 15:31Z: all its scratch
      PIDs dead, KFD list empty, VRAM 13 MB. `reload architect_critic` → PID 1064570 at 15:35:49Z, `/health` ok. The
      launch banner argv (`logs/server_launches/launches.jsonl`) equals `evidence/argv_8083_live_post_relaunch.txt`
      token for token, `argv_sha256` b865820d… (same as the 13:14Z launch). Completions via :8000 to :8083 correct at
      15:39Z (UFH14-B6 proof). `context_limits` was not re-read here. `reload whisper tts` → PIDs 1064878 / 1065102,
      health ok, TTS smoke 57,644 bytes. Production outage: :8083 13:55Z → ~15:35Z; speech ~15:00Z → ~15:35Z.
    - Later the same day, 15:43:08Z: :8083 relaunched (PID 1083497) with the UFH14-DIAG-EC-a SLOTS_DEBUG override
      (experiment id `UFH14-A7`, TTL 14400 s). Same argv; a plain `reload architect_critic` restores it.
  - Finding, not filed as a task: 4 concurrent ~90k prompts take ~36 min for the last one (2166 s). That is the
    neighbour-prefill serialisation the one-long-prefill gate (KVU-15) makes explicit by design; it is a capacity
    fact, not a defect. Declined as a separate task: the actionable part, unified vs split, is KVU-16d.

### B — orchestrator
- [x] **KVU-15 — :8083 KV-pool step 1: close the admission bypasses** ✅ 2026-10-03 (workspace-ec) — orch 2586a7bb on main, API reload: scouts reserve prompt+max_tokens on the token gate; one long prefill (≥16384 est. tokens, env ORCHESTRATOR_KV_POOL_LONG_PREFILL_TOKENS, 0=off) per server, lease ends at first chunk or prompt/250 tok/s; /slots observation holds long requests behind any slot prefilling ≥4096 (covers other uvicorn workers + direct clients like C95); per-request cap = min(slot ctx, model ctx_max). 32 new tests; 4126 related pass. Live alias call via gate ok. Remaining limits: per-worker gate (cross-worker via /slots only), whole-prompt size even when mostly cached; ungated paths documented in /mnt/raid0/llm/tmp/kv-gate-8083-ec/BYPASS.md (action_repair_completer if pointed at :8083; prewarmer only :8074). Was: (operator-approved 2026-10-03, IN PROGRESS;
  `/mnt/raid0/llm/tmp/kv-sizing-8083-20261003/DECISION.md` §3(d), §4 step 1). All 17 pool-exhaustion episodes in
  the 8083 log were four ~45-55k contexts filling the 196k pool, and `logs/orchestrator.log` holds zero
  `SharedKVPoolAdmission` queue lines: the load never passed through the gate. No relaunch, API reload only:
  - route :8083 traffic through the token gate — scouts reserve TOKENS, not slots (`scout_stage.py:39-50`,
    `:250-266`, `:726-753`);
  - one long prefill (≥ 8k tokens) at a time per URL, which targets the 28.6 → 7.8 tok/s neighbour-prefill decode
    collapse (`kv_pool_admission.py`);
  - re-point remaining direct :8083 clients (AutoKernel/DS41 harnesses, opencode, codex, Hermes, C95) at :8000.
  Done when a replay of concurrent long prompts through :8000 queues FIFO with zero "failed to find a memory slot".
- [x] **KVU-17 — serving telemetry: record per-call server timings, including streamed chat** ✅ 2026-10-03 —
  LANDED orch c6225e8b/f7fad574/9a0d38e0 on main, API reload 04:59Z; a live :8083 call logged prompt_eval_ms 2368 ms,
  queue wait 113 ms, role/request_id/orch_commit (logs/serving_calls/serving_calls.jsonl). Was (IN PROGRESS
  2026-10-03; scratch `/mnt/raid0/llm/tmp/serving-timing-ec/`, new `src/backends/serving_calls` module, 44 tests
  pass on the candidate `llama_server.py`). The chat-stream path ignored the `timings` object llama-server
  attaches to the last chunk and hard-coded `prompt_eval_ms = 0.0`, so every streamed completion logged zero
  prefill time and no draft acceptance. The change records `prompt_ms`, `predicted_ms`, `cache_n`, `draft_n` and
  `draft_n_accepted` per call (`infer`, `infer_stream_text`, `/completion`, `/v1/chat/completions`). It is the
  instrument for KVU-15/16 (decode vs pool fill) and Q38-T7 (DFlash2 acceptance on organic traffic). Land on orch
  main, `reload orchestrator`, prove one streamed completion logs non-zero `prompt_eval_ms`, and wire the records
  as a belief-kernel source (VB-SERVING-DF2).
- [x] **KVU-3 — land `feat/context-overflow-handling-20260924` @ `8bbe2a3c`** once OP-55 decides: ✅ 2026-09-24 —
  OP-55 decided "all recommended"; `5ca21957` added route-by-live-limit; merged as orch `8a0c0944` (351 targeted
  tests pass on the merge), shared clone fast-forwarded, API reloaded (orchestrator only); `/v1/models` shows the
  live per-request context. Original decision list:
  - reroute roles (add `architect_critic` at 262144?);
  - the long-context threshold (tokens, ~5k now);
  - `cache_ram` sizes (KVU-2);
  - an unbounded-generation cap;
  - an opencode bypass.

  Then merge, and the owner runs the API reload (`orchestrator_stack.py reload orchestrator`, API only).
- [x] **KVU-3a — detect truncation of streamed chat.** Stream usage now drives the same context-limit classification as nonstream responses, preserving native counts and effective request limits. Orchestrator main `61bf851858bbdd5d911d51051cb87b45a3699ef4` includes reviewed `445cb6be`;209 tests across seven modules pass, including actual SSE content/finish/usage-only/DONE public-path regression. No API reload performed. ✅ 2026-10-30 [no-belief: source repair and deterministic regression controls]
- [x] **KVU-4 — promotion gate: clear the 4 strict known-gap errors.** ✅ 2026-09-24 The operator chose option A:
  `option/critic-general-suite-evidence-20260924` @ `9692c7f9` was merged into the fix branch as `d7ab368e`.
  Strict now counts `general_suite_quality` as per-axis evidence, never as `overall`. The role-purpose critic-suite
  gap remains open as RTG-19 SSU-F16.
- [x] **KVU-4a — clear the gate's only remaining failure: runtime attestation.** ✅ 2026-09-24 — :8180, :8080,
  :8074, :8070 reloaded on `-ub 2048` (18:16–18:18Z, healthy, frontdoor completion ok); the branch merged as orch
  `ff67bbec`; the promotion gate is green. :8083 followed with KVU-1. :8070, :8074, :8080 and :8180 run
  with `-ub 8192` live, but K4 declares 2048. The change is inert, because effective ubatch was already 2048 by
  clamp. :8083 rides KVU-1.
  - The owning session reloads those four after the running speech test, then merges
    `fix/promotion-gate-red-20260924` @ `d7ab368e` and re-runs the gate in the shared clone.
  - Do not merge while the shared orchestrator clone holds another session's uncommitted edits.
  - Acceptance: `stack_change_pipeline.py check --numa-mode both --run-promotion-gate` is green.
- [ ] **KVU-5 — preemption on the orchestrator side** (audit #6 / T4a). When the pool is short, cancel the youngest
  or lowest-priority in-flight request, optionally after `POST /slots/{id}?action=save`, and requeue it idempotently
  with the same request id.
  - Needs a cancellable in-flight registry per URL and a request priority field, and it must preserve the FCFS
    no-starvation invariant.
  - This is the only way to turn the server's abort-all into one recompute without touching the kernel.
- [ ] **KVU-6 — cache-aware ordering on kvu servers** (audit #7 / T9).
  - Stop pinning `id_slot` on unified servers: the server clears idle slots anyway, and the RAM tier is what
    keeps the prefix.
  - Add a bounded longest-prefix-match bypass to the admission queue (at most one skip per waiter).
  - Coordinate with INF-05 KV-3, which is the same lever (native LCP slot pick). Move this task there if INF-05
    takes it.
- [x] **KVU-13a — ambient `LLAMA_ARG_*` env is invisible to the cmdline attestation.** `-kvu` on argv wins, but an
  ambient `LLAMA_ARG_N_PARALLEL` would not be seen. Extend `_live_kv_unified()` (patch 3) to read
  `/proc/<pid>/environ`, or scrub `LLAMA_ARG_*` from the launch env. Same class (package revision 3 §9): an
  ambient `LD_PRELOAD` / `SHIM_NPROCS` in the launcher's parent env would reach every aux service, because
  `build_service_env` starts from `os.environ`; scrub both unless the service entry declares them. ✅ 2026-10-29 — orchestrator main `61c4763b3655` scrubs inherited `LLAMA_ARG_*` in llama and aux environment builders and drops undeclared aux `LD_PRELOAD` / `SHIM_NPROCS`; declared service shims remain explicit. Ninety-nine focused/regression tests pass, including seven hostile-parent controls; Ruff and diff checks pass. `make gates` reached shellcheck and stopped because shellcheck is absent. This closes the source repair; no running service was reloaded. [no-belief: source implementation and regression tests]
- [ ] **KVU-13b — the stack-change skill's DERIVATION source list omits the files a new launch flag needs**
  (`src/registry/stack_priors.py`, `scripts/server/stack_commands.py`, `scripts/server/orchestrator_stack.py`, and
  per package revision 3 §9 also `scripts/server/stack_manifest.py` and `scripts/voice/`).
  Also, `preflight.sh`, `capacity.sh` and `topology_check.py` hardcode the real ORCH path, so they cannot run
  against a scratch clone. Fix both in `.claude/skills/stack-change/`.
- [x] **KVU-13c — the capacity gate runs at import of `stack_manifest`.** A lineup that fails capacity makes the
  launcher and the pipeline un-importable, so the tool you would use to fix the lineup cannot load (hit in the
  package scratch, revision 3 §9). Move the gate to an explicit call (pipeline `check` / launcher pre-start) and
  keep import side-effect-free; test: a failing lineup still imports and `check` reports the failure.
  ✅ 2026-10-30 — orchestrator main `5f72ca3f2687d26ad7d59ff828f08b696db2e7b1`: capacity-only import side effect removed; unchanged capacity validation runs explicitly in the fresh-process pipeline check, start/reload handlers before service mutation, and direct model/API/aux start entries. Declaration classification/parity validation remains. Native over-capacity controls prove import/status work while pipeline/start/reload refuse; valid capacity reaches the next stage. All152 related controls pass; Ruff passes. `make gates` stops at unavailable shellcheck. No live service/config, capacity arithmetic, grading or production-kernel change. [no-belief: source implementation and regression controls]
- [ ] **KVU-14 — session-keyed admission hold on shared-pool servers (DESIGN; opens only if dynamic-stack-concurrency.md G5 finds cross-session eviction).** ThunderAgent's contract (intake-1816#1, intake-1816#4, intake-1816#6): a session is REASONING while a request is in flight and ACTING from response completion; capacity = the unified KV pool plus `--cache-ram`; under pressure, hold the NEXT turn of the smallest idle (ACTING) sessions at admission — never mid-decode — and resume shortest-first with hysteresis and a forced-resume timeout (HSF-3 p99). Optionally back the hold with `POST /slots/{id}?action=save` to RAM (the verb KVU-5 uses). Reads the ONE session table (heterogeneous-slot-fabric-residency.md tracked-session index; identity from harness-selection-and-integration.md HS-16); shares the admission queue with KVU-5/KVU-6; no second occupancy notion. Upstream ThunderAgent and Dynamo's plugin are not deployable here (vLLM/SGLang backends only; Dynamo frontend only).

### C — kernel candidate (v11, guarded)
- [ ] **KVU-19 (intake P5) — masked-block skip for unified-KV flash attention on `llama.cpp-experimental`.
  Trigger: KVU-18 measures a decode loss of 5% or more.** Upstream trims only the fully masked *tail* of the KV
  range, and the launch gate never fires for unified-KV decode (`n_stream` == 1). So a decode or verify step
  attends over every block that other slots' sequences occupy (`intake-1849#00`). Skip masked blocks anywhere in
  the range, not just at the tail, for the decode and verify shapes, HIP/gfx90a first. No upstream fix exists:
  the WMMA-only PR #28943 closed unmerged (`intake-1849#03`). Four-step workflow; validate on the KVU-18 cells
  and on the DF2 verify shape (n_max 7). Not triggered means no kernel work.
  - **TRIGGERED 2026-10-03** by KVU-18 (no-draft decode −32.6% with one ~99k parked neighbour, −59.5% with three).
    Validate on the KVU-18 A1 cells (same P, 0/1/2/3 neighbours) plus the DF2 verify shape. Whether the split stack
    change (KVU-16d) lands first changes the production stake, not the kernel case: any unified-KV deployment
    with parked neighbours pays this tax.
  - *(Annotation, workspace-ec, 2026-10-03; this item stays workspace-89's.)* KVU-16d is decided **keep shared
    393k**, so production keeps paying the tax until this lands. The operator asked for the skip to be implemented
    DIRECTLY, without waiting on AutoKernel, and folded into the champion. The implementation is KVU-19a (workspace-ec);
    the champion fold and the full-scale P3 re-measurement stay here with workspace-89.
  - *(Annotation, workspace-ec, 2026-10-03 ~17:15Z; this item stays workspace-89's.)* KVU-19a is built: fold record
    [`docs/design/fa-masked-block-skip-20261003-fold.md`](../../docs/design/fa-masked-block-skip-20261003-fold.md)
    (cherry-pick ac97e305a + a0d0ae238; both clean onto b3e0b0902). The P3 re-run needs a `BIN` override in
    `p3_kvu_probe.sh` and `x0_common.py`, and arms new build vs the same binary with `GGML_CUDA_FA_MASK_SKIP=0`.
    workspace-89 was asked to run it on its harness in the coordinated GPU block after ~18:15Z. Falsifiable
    expectations: at L3, drafted ≥ ~33 tok/s (was 15.4) and no-draft ≥ ~19 (was 8.3); batched-bench `-kvu` S_TG within
    ~5% of `-no-kvu` (was −15.2%); L0 unchanged within noise. Its records project under VB-KVU-P3.
  - *(Annotation, workspace-ec, 2026-10-04; this item stays workspace-89's.)* KVU-19a-1 passed on the store build
    (02:25-02:47Z), but the batched-bench expectation above already FAILS at small scale: 4×16k `-kvu` S_TG 444 vs
    `-no-kvu` 542/551 t/s (base 437). The skip is per tile, and a batched decode tile spans all sequences. Single-
    sequence decode/verify behind idle neighbours is fixed (P3-mini 82 → 169 steps/s). Per-row skipping is KVU-19b.
  - *(Annotation, workspace-ec, 2026-10-04 later; this item stays workspace-89's.)* The KVU-16b root cause raises
    the production stake. On :8083's mixed prefill+decode iterations, the skip is estimated at ~3.5× decode on its
    own and ~10× with KVU-16f's `-b 512`: the i=3 prefill attends ~40k own cells against ~275k occupied. The fold's
    P3 v2 can use the KVU-16b replay (after KVU-16b-1) as its full-scale cell. KVU-19b's store build
    `gpu-20261004-c7f5ac9ad` carries the KVU-19a arm too (`GGML_CUDA_FA_SEQ_ROWS=0`).
  - *(Annotation, workspace-ec, 2026-10-04 05:05Z; this item stays workspace-89's.)* KVU-19b-1 scored the KVU-19b store
    build: fold **commit 1 only** (`1bceceb05`, batched-decode vec routing: 5.5 vs 9.2 ms at 4×80k; batched-bench
    `-kvu` 522 vs `-no-kvu` 529 t/s). Commit 2 (`c7f5ac9ad`) is out until KVU-19b-rework-c2 lands. Filed as
    KVU-19b-fold-c1.
  - *(Annotation, workspace-ec, 2026-10-04 ~07:55Z; this item stays workspace-89's.)* **KVU-19a and KVU-19b commit 1
    are IN THE CHAMPION.** `ak/champion/llama-cpp-ffc1bac82eec` advanced `90c12df42` → `1bceceb05` (fast-forward:
    `ac97e305a`, `a0d0ae238`, `1bceceb05`, original shas kept), locally and on `fork`, by the guarded CAS in
    `artifacts/champion-fold-kvu19-20261004/scripts/advance_ref.sh`. Builds `kernels/builds/{gpu,cpu}-20261004-1bceceb05`
    (build 10311). Record: [`artifacts/champion-fold-kvu19-20261004/`](../../artifacts/champion-fold-kvu19-20261004/)
    (`FOLD-CANDIDATE.md`, GPU slot summary). The fold is ledgered in `autokernel-champion-aggregate.md` (root
    `3cef9579`, ak-ds41-main). What remains here for workspace-89: the full-scale P3 27B re-measurement on the folded
    champion (KVU-19b-fold-c1-p3).
  - [x] **KVU-19a — implement masked-block skip directly; fold via workspace-89.** ✅ 2026-10-04 (filed 2026-10-03, workspace-ec;
    operator instruction 2026-10-03, implements KVU-19) IN PROGRESS: an Opus subagent on a new `llama.cpp-experimental`
    branch from the global champion 90c12df42 (`ak/champion/llama-cpp-ffc1bac82eec`).
    - Scope: the HIP (gfx90a) and CPU flash-attention kernels skip fully masked KV blocks anywhere in the range, not
      just the tail, for the decode and verify (n_max 7) shapes.
    - Correctness: `test-backend-ops` cases with multi-sequence masks.
    - Speed: a small-model micro-bench, with 0/1/3 resident neighbours.
    - Build into a new `kernels/builds/` dir; a feature commit plus `FOLD.md`, with a trial merge onto the DS41
      accumulator b3e0b0902.
    - Hand-off: workspace-89 folds it into the champion with DS41's promoted keeps and runs the full-scale P3
      re-measurement window (KVU-19). Never touches the frozen production tree.
    - Done when `test-backend-ops` passes with the new masks, the micro-bench shows the neighbour tax reduced, and
      `FOLD.md` plus the trial-merge result are handed to workspace-89.
    - **BUILT 2026-10-03 (workspace-ec); GPU validation on the store build pending, so not ticked.** Fold record:
      [`docs/design/fa-masked-block-skip-20261003-fold.md`](../../docs/design/fa-masked-block-skip-20261003-fold.md)
      (durable copy of `/mnt/raid0/llm/tmp/fa-maskskip-20261003/FOLD.md`).
      - Branch `experimental/fa-maskskip-20261003` from champion 90c12df42, pushed to `fork`: ac97e305a (GPU plus
        `test_flash_attn_ext_unified`, 52 cases) and a0d0ae238 (CPU). Store builds
        `kernels/builds/gpu-20261003-a0d0ae238` and `cpu-20261003-a0d0ae238` (build 10310); linkage PASS.
      - Kernels: all 4 HIP FA kernels, the CDNA2 fused-combine vec path and the CPU path. A new scan kernel marks
        live/dead 256-cell blocks per query tile. On gfx90a, plain decode uses vec, and verify/batched/prefill use
        WMMA after a q8_0→f16 conversion that now skips dead blocks too. Knobs: `GGML_CUDA_FA_MASK_SKIP=0` (one
        binary is its own control) and `GGML_CUDA_FA_MASK_SKIP_MIN_KV` (default 4096).
      - Correctness, on the dev build before the final q8_0 converter change: `test-backend-ops -o FLASH_ATTN_EXT -b
        ROCm0` 2920/2920 including the 52 new cases. The 64-case harness is bit-identical with the skip on vs off.
        Against the unpatched champion, 58/64 are bit-identical and 6 differ at nmse ≤ 3e-7 from codegen. CPU 86/86
        bit-identical.
      - Kernel micro-bench (dev build, contended GPU, indicative only), 27B attention shape: decode (vec) 2446 →
        401 µs at +112k foreign cells; drafted verify (WMMA) 4443 → 788 µs, a +18% residual against +590% unpatched;
        0 foreign +4-5%, within noise, to be re-measured.
      - Upstream: #28495 still open. The maintainer-requested approach builds on `flash_attn_mask_to_KV_max`; PR
        #28943 closed, #29510 is a draft. Drop ac97e305a for the upstream design when it lands.
      - Fold: trial merge and cherry-pick onto DS41 accumulator b3e0b0902 are both clean. workspace-89 does the
        champion fold (KVU-19).
    - [x] **KVU-19a-1 — validate the STORE build on the GPU (`gpu_slot.sh`).** ✅ 2026-10-04 (filed 2026-10-03, workspace-ec) The
      correctness and micro-bench numbers above come from the dev build. Run
      `/mnt/raid0/llm/tmp/fa-maskskip-20261003/gpu_slot.sh` (~20-25 min, < 2 GiB) in a coordinated GPU slot, never
      during another session's GPU measurement window (INC-20261003-subagent-gpu-tests-in-peer-window). It covers
      store-build exactness, the micro-bench with 3 alternating rounds, P3-mini on gemma-3-1b, batched-bench `-kvu`
      vs `-no-kvu`, and `test-backend-ops` with `GGML_CUDA_FA_MASK_SKIP_MIN_KV` default and 0. Done when
      `test-backend-ops` passes on the store build, skip on/off is bit-identical, and the 0-foreign micro-bench row is
      within noise of the champion. Then tick KVU-19a. Scheduled for the coordinated GPU block after ~18:15Z.
      - **PASSED 2026-10-04 02:25-02:47Z (workspace-ec)** on the store build, results
        `/mnt/raid0/llm/tmp/fa-maskskip-20261003/slot-20261004T022552Z/` (VRAM before/after equal).
        - Exactness (`exact.txt`): skip off vs on 64/64 bit-identical; base (champion) vs on 58/64, worst nmse 3.05e-7.
          `test-backend-ops -o FLASH_ATTN_EXT` 2920/2920 twice (`MIN_KV` default and 0).
        - Kernel micro-bench, 3 alternating rounds (`perf_results.txt`): nb=1 at +114,688 foreign cells base ~2003 µs
          vs on ~282 µs (7.1x); nb=8 at +114,688 3808 vs 584 µs; 0 foreign 271 vs 275 µs (noise).
        - P3-mini, gemma-3-1b, 8k own, 3×32k idle neighbours (`p3mini_results.txt`): draft 1 base 82 → on 169 steps/s
          (no-neighbour ~182-197); draft 8 41.8 → 89.5 (no-neighbour ~99.5).
        - Batched-bench, 4 concurrent 16k sequences (`bb_*.jsonl`): S_PP kvu base 13,205 → new 21,017 t/s (no-kvu
          ~20,000); S_TG kvu base 437 → new 444 vs no-kvu 542/551.
        - **FINDING: the skip does NOT help concurrent decodes.** A batched decode's query tile spans every sequence,
          so its live-block set is their union and nothing is dead. Production flushes idle slots (211 organic
          purges, KVU-16b), so concurrent decode is the production-relevant case. Filed as KVU-19b.
        - KVU-19a's done-when holds (tests pass, neighbour tax reduced for single-sequence decode/verify, fold record
          handed to workspace-89, whose P3 v2 on this build is queued), so KVU-19a is ticked.
    - [ ] **KVU-19a-2 — report or investigate the latent D=512/576 tile-kernel nondeterminism upstream.** (filed
      2026-10-03, workspace-ec, from the KVU-19a build) A no-op branch inside the KV loop of the D=512/576 GQA tile
      FA kernel made its output run-to-run nondeterministic on gfx90a (~1e-4 nmse), even with the skip disabled.
      That is pre-existing upstream code, codegen-sensitive, and it affects Gemma-4 D=512 layers on HIP. KVU-19a
      avoids triggering it by advancing the loop index instead. Reduce it to a standalone `test-backend-ops` repro
      on an experimental branch, then file an upstream llama.cpp issue with the repro. Detail: the fold record's
      *Not done / follow-ups*. Done when an upstream issue link is recorded here, or the repro shows it is not
      reproducible on the unpatched kernel.
      - *(2026-10-21 triage)* open (no evidence found).
    - [ ] **KVU-19b — per-sequence (per-query-row) block skipping inside a multi-sequence FA tile.** (filed
      2026-10-04, workspace-ec, owner workspace-ec, from KVU-19a-1's batched-bench finding) KVU-19a marks a KV block
      dead only if it is dead for EVERY query row in the tile, so a batched decode over 4 sequences sees the union
      and skips nothing: S_TG kvu 444 vs no-kvu 542/551 t/s. Skip per query row (or regroup query rows by sequence)
      inside the tile, on `llama.cpp-experimental` from the current champion, HIP/gfx90a first, keeping the 64-case
      exactness harness and `test-backend-ops` green. Done when batched-bench `-kvu` S_TG at 4×16k is within ~5% of
      `-no-kvu` and single-sequence results do not regress.
      - **2026-10-04 (workspace-ec): BUILT CPU-side; GPU validation in progress, so not ticked.** Fold record:
        `/mnt/raid0/llm/tmp/fa-maskskip-batched-20261004/FOLD.md` (design in `DESIGN.md` beside it).
        - Branch `experimental/fa-maskskip-batched-20261004` on base a0d0ae238 (KVU-19a), pushed to `fork`:
          - `1bceceb05` routes "every row a different sequence" batches to the vec kernel, one row per block, using a
            new `ggml_flash_attn_ext_{set,get}_n_seq` hint that `llama-graph.cpp` sets from `ubatch.n_seqs_unq`;
          - `c7f5ac9ad` cuts WMMA query tiles at sequence boundaries with a device planner.
        - Knob: `GGML_CUDA_FA_SEQ_ROWS=0` turns both off, which is the same as KVU-19a. So one binary carries the
          three arms 19b, 19a, and 19a with the skip off.
        - Store builds `kernels/builds/{gpu,cpu}-20261004-c7f5ac9ad` (build 10312); linkage PASS.
        - CPU FA harness v2: 141/141 bit-identical to the KVU-19a CPU store build. The llama-side hint checks out on
          gemma-3-1b (4 in every multi-sequence kvu step graph, 0 for single-sequence and for `kv_unified=false`).
        - `gpu_slot2.sh` ran 04:44-05:05Z (`slot2-20261004T044448Z/`); scored in KVU-19b-1 below.
      - **2026-10-04 05:05Z (workspace-ec): GPU validation SCORED; parent stays open.** Durable evidence:
        [`artifacts/kvu19b-20261004/`](../../artifacts/kvu19b-20261004/) (`slot2-20261004T044448Z/summary.txt`,
        `FOLD.md`, `DESIGN.md`, runner `gpu_slot2.sh`). The batched-bench done-when holds for commit 1 (`-kvu` S_TG
        522.4 vs 529.3 base `-no-kvu`, -1.3%; -5.5% vs the same binary `-no-kvu`, 552.7; 19a was 434.6) and single-
        sequence rows are unchanged vs 19a. KVU-19b is NOT ticked because commit 2 broke the design's bit-identity
        claim and is being reworked (KVU-19b-rework-c2), and p3batch draft=1 still trails no-kvu (KVU-19b-gap). Tick
        it when the rework is folded or dropped.
      - [x] **KVU-19b-1 — validate the KVU-19b STORE build on the GPU (`gpu_slot2.sh`).** ✅ 2026-10-04 (workspace-ec;
        store build `gpu-20261004-c7f5ac9ad`, linkage PASS, VRAM before/after equal)
        - Correctness: `test-backend-ops -o FLASH_ATTN_EXT -b ROCm0` 2978/2978, plus the unified cases 110/110 with
          `MIN_KV=0` and 110/110 with `SEQ_ROWS=0`. Every arm (on / seqoff / k19a) is within the CPU reference on all
          119 harness cases (worst nmse 8.97e-05 at a 5e-4 tolerance). seqoff == alloff == k19a bit-identical (119/119).
        - **Commit 1 (`1bceceb05`, vec routing, one row per sequence) WINS.** Kernel at 4 seqs × 81920 own, n_kv 327680:
          5.53 ms vs 9.23 ms (19a) vs 8.77 ms (base); per-sequence streams reference 5.26 ms. At 4 × 16384: 1.08 vs
          1.78 ms. p3batch gemma-3-1b 4×16k draft=1: 440 / 430 / 449 tok/s (on) vs 377 / 373 / 396 (19a) vs 491 / 523 /
          518 (no-kvu), three rounds.
        - **Commit 2 (`c7f5ac9ad`, WMMA sequence tiles) is MIXED and breaks exactness.** Aligned 4×8 verify: 11.86 vs
          10.36 ms (seqoff), 14% slower. Uneven [1,8,8,8]: 11.90 vs 13.64 ms, 13% faster. Skip on vs off is NOT
          bit-identical on 6 cases (110/111/118/119/126/127, all hint=4 nb≥25 multi-row tiles, f16/q8_0/bf16):
          ndiff 384, nmse ≤ 8.3e-10. DESIGN.md claimed bit-identity for the tile layout under skip on/off. p3batch
          draft=8 rows are within run-to-run noise (±10%), so the end-to-end effect is unresolved.
        - Recommendation sent to workspace-89 (fold owner): fold commit 1 only.
        - **Contention caveat.** The slot ran its host side unlocked on `taskset -c 160-183` (the SMT siblings of
          64-87) while workspace-89 held `cpu-window2-20261004` and two dev servers and a build were also running
          (INC-20261004-subagent-unlocked-cpu-in-held-window). Arms alternate within each round, so the comparisons
          stand, but host-bound absolute numbers (p3batch on a 1B model, ~100 steps/s) are noisier than a quiet
          host would give. `gpu_slot3.sh` takes `region-lock` for its host side.
      - [x] **KVU-19b-fold-c1 — fold KVU-19b commit 1 (`1bceceb05`) into the champion; leave commit 2 out.** ✅ 2026-10-04 (filed
        2026-10-04, workspace-ec, owner **workspace-ec** (reassigned 2026-10-04 by workspace-89; operator "proceed in coordination"), from KVU-19b-1) Cherry-pick order: `ac97e305a a0d0ae238`
        (KVU-19a, if not folded yet), then `1bceceb05` only. Commit 1 also touches `ggml.h/ggml.c` (the
        `ggml_flash_attn_ext_{set,get}_n_seq` hint) and `src/llama-graph.cpp`. Gates on the folded candidate, from
        `artifacts/kvu19b-20261004/FOLD.md`: house recipes; `test-backend-ops -o FLASH_ATTN_EXT -b ROCm0` (also with
        `GGML_CUDA_FA_MASK_SKIP_MIN_KV=0`); harness exactness; P3 B on the 27B. Done when the champion carries commit 1
        and its P3 B shows `-kvu` batched decode within ~5% of `-no-kvu`.
        - **FOLDED 2026-10-04 (workspace-ec).** The champion ref is `1bceceb05` locally and on `fork` (advanced from
          `90c12df42` by the guarded CAS `advance_ref.sh`; `ak-loop-tree` refreshed clean; frozen tree untouched on
          `production-consolidated-v10`). `c7f5ac9ad` is not in it (`plan_seq_tiles` 0 in strings/`nm`). Durable record:
          [`artifacts/champion-fold-kvu19-20261004/`](../../artifacts/champion-fold-kvu19-20261004/).
          - G0 feature preservation: source, GPU and CPU pairs PASS, 0 losses. G0 is vacuous for HIP kernels (it
            classifies CPU families only), so the GPU gate is the slot below.
          - CPU: harness v1 86/86 and v2 141/141 bit-identical to the 19a/19b CPU stores and the unpatched champion;
            `test-backend-ops -b CPU` 5178/5178.
          - **GPU slot `slot-20261004T073429Z`: VERDICT PASS.** Exactness E1-E8 (skip on == off with seq rows on and
            off, `SEQ_ROWS=0` == the KVU-19a build, only vec-routed cases differ, worst nmse 8.97e-05 vs the CPU
            reference); 27B DFlash2 smoke byte-identical champion vs candidate skip off vs skip on (`MIN_KV=0`), 74
            tokens, accept 36.054% in all three; `test-backend-ops -o FLASH_ATTN_EXT -b ROCm0` 2949/2949, plus
            81/81 × 3 (`MIN_KV=0`, hint with `SEQ_ROWS=0`, `MASK_SKIP=0`); perf2 4×1 kvu 1084 vs 1733 µs (16k own) and
            5514 vs 9168 µs (80k own), single-sequence +114,688 foreign 284 vs 2335 µs, 0-foreign rows within noise.
          - **Ticked on the fold; the P3 B half of the done-when is split out** as KVU-19b-fold-c1-p3, because the slot
            budget did not include it and it needs a :8083-sized window.
          - The standing receipt (single arm, operator ruling 2026-10-04) is KVU-19b-fold-c1-receipt.
        - [x] **KVU-19b-fold-c1-receipt — record the ONE-champion standing receipt for `1bceceb05`.** ✅ 2026-10-04 (filed
          2026-10-04, workspace-ec) `standing_receipt.sh` (single arm per operator ruling: champion only, 1 warm-up +
          20 launches tg128 on the 27B; baseline = the FOLD-2 G5 `ef81196d5` samples of 2026-09-08, median 31.301
          tok/s, unpaired, 26 days apart, BIOS change in between) was started ~07:59Z under `region-lock run
          --cpu-list 0-95 --role bench` and was waiting on the region lock at wrap-up time; nothing published yet.
          Done when `loop-memory/champion-vs-production.json` names `1bceceb05` (exit 0) and the ratio plus its
          caveats are recorded here, or exit 4 is recorded with the reason. tg128 runs at n_kv ≈ 128, so the number is
          the lineage's decode aggregate, not a KVU-19 effect.
          - *(2026-10-04 PM, workspace-ec.)* **Recorded as a PAIRED receipt** (operator decision 2026-10-04: measure v10
            once on DFlash2). 14 paired launches, v10 `ffc1bac82` vs champion `1bceceb05`, on the :8083 DFlash2 argv:
            tg +0.61% [95% CI −0.20, +1.41] (40.125 vs 40.369 tok/s), pp −0.21%, output identity C ≡ P on every launch.
            Ingested as the v10 `serving_probe` baseline (`production-baseline.ffc1bac82eec.serving_probe-{tg,pp}.json`)
            and `champion-vs-production.1bceceb0514d.serving_probe.json`. The raw run dir was lost to a glob `rm`
            (INC-20261004-glob-rm-deleted-receipt-evidence); surviving evidence is in
            `artifacts/champion-fold-kvu19-20261004/paired-receipt-20261004T094057Z/`.
          - Later the same day: candidate X `cf23279ae`, paired vs v10, tg −0.23% [−0.57, +0.23], FA `test-backend-ops`
            2949/2949 (`artifacts/champion-fold-kvu19-20261004/receipt-ab/paired-cf23279ae-20261004T115822Z/`). The
            operator chose Y `61bdb185c` (DS41 serving-gated keeps + `656c9a66b`, no IQ4_NL allowlist); Y champion-only
            tg +0.35%, pp +18.2% flagged as unpaired drift
            (`artifacts/champion-fold-kvu19-20261004/receipt-ab/champion-only-61bdb185c-20261004T144303Z/`).
            workspace-89 advanced the champion `1bceceb05` → `61bdb185c`. The next fold is Yfa `9a3f1392a` (+ CPU FA
            hybrid v2), with its gates passed.
      - [x] **KVU-19b-rework-c2 — make WMMA sequence tiles exact, straddle-only, and separately switchable; then
        `gpu_slot3.sh`.** (filed 2026-10-04, workspace-ec, owner workspace-ec, from KVU-19b-1; rework dispatched)
        (1) Root-cause the skip on/off difference on cases 110/111/118/119/126/127 (384 elements differ in each). The
        design says the planner and tiles never depend on `GGML_CUDA_FA_MASK_SKIP`, so something does. (2) Plan
        sequence tiles only when a default tile straddles sequences, so the aligned 4×8 verify keeps the 19a layout
        (it is 14% slower today). (3) Split the knob: `GGML_CUDA_FA_SEQ_TILES` for the tiles, `GGML_CUDA_FA_SEQ_ROWS`
        for the vec routing only. (4) Write and run `gpu_slot3.sh` with more p3batch rounds for draft 8 and [1,8,8,8].
        Done when skip on/off is bit-identical on all cases, aligned 4×8 is within noise of seqoff, uneven keeps its
        gain, and the result is handed to workspace-89 as a separate fold item (or commit 2 is dropped with the
        reason recorded here).
        - *(2026-10-04, workspace-ec; steps 1-3 built, step 4 GPU pending, so not ticked.)* **Rework v2:** branch
          `experimental/fa-maskskip-batched-v2-20261004` @ `54df2c030`, pushed to `fork`, on `c7f5ac9ad` (so on the
          folded champion lineage). Store builds `kernels/builds/{gpu,cpu}-20261004-54df2c030`. Scratch:
          `/mnt/raid0/llm/tmp/fa-maskskip-batched-20261004/rework/`.
          - (1) **Exactness root cause found and fixed** (`61d98bf6f`). `c7f5ac9ad` started each sequence tile at its
            first row, so row r ran in tile column r − tile.x instead of r % ncols. The column picks the unrolled code
            copy, and those copies round Q·scale → FP16 differently: gfx90a assembly shows columns 0-11 use
            `v_mul_f32` + `v_cvt_f16_f32` (two roundings) and columns 12-15 `v_fma_mixlo_f16` (one). A compiler
            rounding difference between WMMA columns, not a planner dependency on the skip knob. Rows now keep their
            plain tile column.
          - (2) **Aligned-verify gate** (`54df2c030`): no planning, scan or extra grid slots when every row is its own
            sequence or the rows are equal groups that the plain tiling does not cut, so the aligned 4×8 verify takes
            exactly the KVU-19a path; a device cost check uses planned tiles only when they save live (tile, KV
            block) pairs.
          - (3) **Knob split** (`0c33b64fc`): `GGML_CUDA_FA_SEQ_VEC=0` turns off the commit-1 vec routing,
            `GGML_CUDA_FA_SEQ_TILES=0` the WMMA sequence tiles; `GGML_CUDA_FA_SEQ_ROWS=0` still turns both off
            (== KVU-19a).
          - CPU harness v2 on the v2 build: 141/141 bit-identical to the v2 reference (`rework/cpu_v3_vs_v2ref.txt`).
          - (4) `gpu_slot3.sh` is ready (default `NEW=gpu-20261004-54df2c030`, controls `gpu-20261003-a0d0ae238` and
            `gpu-20261004-c7f5ac9ad`, host side under `region-lock`); it runs in the next coordinated GPU slot.
        - *(2026-10-04 PM, workspace-ec; step 4 ran, but calibration triage is open, so not ticked.)* **`gpu_slot3.sh`
          ran** (`slot3-20261004T115000Z`, durable copy `artifacts/fa-maskskip-batched-20261004/slot3-20261004T115000Z/`).
          - Exactness: all five bit-identity criteria PASS, 132/132 each (on ≡ skipoff, on ≡ tilesoff, force ≡ seqoff,
            tilesonly ≡ seqoff, seqoff ≡ alloff).
          - Kernel µs/op vs KVU-19a at 4 seqs × 80k cells: 4×9 ×0.708; uneven ×0.88-0.90; aligned 4×8 ×0.98; streams
            ×0.99-1.01.
          - `test-backend-ops`: 118/118 ×2.
          - Two calibration FAILs remain:
            - seqoff vs k19a: 22 hs=128 cases at nmse 7.79e-08 against the pinned Q-rounding bound;
            - case 152 vs the CPU reference: nmse 0.00176 > 5e-4 on every arm, the KVU-19a build included.
          - p3batch draft 1: on 8.14 vs no-kvu 7.40 ms/step (KVU-19b-gap).
        - *(2026-10-21 triage)* open (no evidence found); successor KVU-19b-rework-c2-cal exists, kv-prefix-fork-and-paged-attention.md:309.
      - [ ] **KVU-19b-gap — commit 1 still trails no-kvu at draft=1 in p3batch; find out why.** (filed 2026-10-04,
        workspace-ec, from KVU-19b-1) p3batch gemma-3-1b 4×16k draft=1: 449 vs 518 tok/s (round 3; medians 440 vs
        518, about 15% short), while the kernel micro-bench is at the streams reference (5.53 vs 5.26 ms) and
        batched-bench is within 1.3%. So the remainder is likely outside the FA op: mask construction over
        n_kv = 4 × own, the KVU-19a scan, KV copy/view ops on a single stream, or graph shape. Profile one
        p3batch step `-kvu` vs `-no-kvu` (rocprof per-kernel, GPU slot) and attribute the gap per op. Done when the gap
        is attributed with a fix filed, or shown to be inherent to a single KV stream. Re-measure the gap
        under `region-lock` first: slot2 ran on a contended host (KVU-19b-1 caveat), and host overhead hits the
        1B model hardest.
        - *(2026-10-21 triage)* open (no evidence found).
      - *(2026-10-21 triage)* open (no evidence found).
  - *(2026-10-21 triage)* open (no evidence found); fold evidence is in autokernel-champion-aggregate.md but the masked-block-skip task carries open children.
- [ ] **KVU-20 — cross-slot prefix fork anchored on recurrent checkpoints, plus trunk-first dispatch.** (filed
  2026-10-04, workspace-ec, from the KV-serving survey Rec 2,
  `artifacts/gpu-block-27b-20261004/analysis/kv-serving-survey-REPORT.md` §4.)
  - **The gap.** Four subagents sharing a 60k trunk prefill it four times and hold four copies (~6 GB of the pool).
    Slot selection never looks at busy slots (`get_available_slot`), and `seq_cp` is used only for `n>1` children.
  - **Server side (experimental tree).** For a new task, compute the LCP against all slots and their checkpoint
    lists. Fork attention KV zero-copy with `mem_attn->seq_cp(S, dst, 0, p)` at the largest checkpoint ≤ LCP.
    Restore the recurrent state (and the drafter's) from that checkpoint with `llama_state_seq_set_data_ext(...,
    PARTIAL_ONLY)`; `llama_memory_hybrid::seq_cp` shares S's *current* tail, so do not rely on it. Add a request field
    that marks the end of the shared prefix so a checkpoint lands exactly at the parent→subagent junction.
  - **Orchestrator side.** Issue the trunk first, then the children; order and pin slots by the KVU-15c prefix
    history; have the KV-pool gate count unique cells.
  - **Gate.** A logits-equivalence test, fork vs fresh prefill (top-1 on ≥ 24 prompts), with the drafter state
    included.
  - **Done when** a 4-child fan-out over a ≥ 30k trunk prefills the trunk once, the child TTFT is the suffix time,
    and the gate passes.
  - *(2026-10-21 triage)* open (no evidence found).
- [ ] **KVU-19c — measure the live-block fraction per row on organic traffic before building sequence-affine cell
  allocation.** (filed 2026-10-04, workspace-ec, survey Rec 3) `find_slot` allocates first-fit, so concurrent decode
  interleaves the sequences' new tokens in shared 256-cell blocks. A block holding generated tokens is then live for
  every decoding sequence, and even KVU-19b cannot skip it. Have KVU-19a's scan kernel, or a debug counter, report
  the per-row live-block fraction on an organic :8083 replay. Build the allocator (~100–200 LOC in
  `llama-kv-cache.cpp`, per-sequence 256-cell chunks) only if mixed blocks are a material share. Done when the
  fraction is recorded here, with a build/no-build verdict.
  - *(2026-10-21 triage)* open (no evidence found).
- **CPU FlashAttention FP16 VKQ overflow (2026-10-04, workspace-ec).** `ggml-cpu/ops.cpp`
  `ggml_compute_forward_flash_attn_ext_f16_one_chunk` accumulates the un-normalised VKQ in FP16 whenever V is F16. For
  diffuse attention that is about the per-channel sum of V over the visible cells, so 2048 cells × a same-sign channel
  of 32 passes FP16_MAX (65504) → inf → NaN; below overflow, FP16 rounding (ulp 32 at 32k) degrades peaked attention
  too. The path is every untiled F16-V call: verify/spec batches and prompt tails with < 64 rows, and the split-KV
  decode. Upstream is unfixed. Evidence: `/mnt/raid0/llm/tmp/cpu-fa-f16-20261004/`, durable copy
  [`artifacts/cpu-fa-fp32-vkq-20261004/`](../../artifacts/cpu-fa-fp32-vkq-20261004/).
  - **Production is not at risk today.** The architect (:8074) probe measured `acc_peak` ≤ 238 over 37-18,940-token
    prompts (`probe/run_base.log`), because its 2048-cell indexer bounds the visible window. The MTP draft head is
    dense with an F16 KV, so acceptance loss is possible at very long context; that is CPU-FA-VKQ-3.
  - [x] **CPU-FA-VKQ-0 — reproduce and fix on an experimental branch.** ✅ 2026-10-04 (workspace-ec) Branch
    `experimental/cpu-fa-fp32-vkq-20261004` @ `2ad8bff36` (on `90c12df42`; pushed to `fork` at wrap-up; a trial merge
    onto `1bceceb05` is clean). F16 V now accumulates into the FP32 VKQ with a fused `ggml_vec_mad_f32_f16` (AVX512F and
    AVX2+F16C+FMA paths, portable fallback), the same per-element arithmetic as the tiled path; `GGML_FA_VKQ_F16=1`
    restores the legacy accumulator for A/B. Harness: fix 84/84 finite and within reference (nmse ≤ 1e-12) vs base
    71/84 (10 non-finite, 3 mismatch); determinism 84/84 on every arm; FA-op cost at parity (e.g. 4×1 at 128k cells
    23.2 vs 22.4-23.6 ms). The fusion matters: a two-pass convert costs ~3× FA op time on Zen 5.
  - [ ] **CPU-FA-VKQ-3 (optional) — MTP acceptance at > 64k on the architect, fix vs legacy.** (filed 2026-10-04,
    workspace-ec) The dense F16 MTP head is the one consumer whose visible window is not bounded by the indexer. Replay
    a > 64k architect conversation with MTP on a scratch port in a CPU window, `GGML_FA_VKQ_F16=1` vs default, and
    compare acceptance and the first-divergence token. Done when the acceptance delta is recorded, or the probe shows
    `acc_peak` stays far below FP16 range at that length.
    - *(2026-10-21 triage)* open (no evidence found).
    - *(2026-10-22, KVU-LB1.c, intake-2455)* moved to the top of this open list: production v10 has no fix and the architect declares 262144 context.
  - [x] **CPU-FA-VKQ-1 — fold `2ad8bff36` into the champion (and so into v11).** (filed 2026-10-04, workspace-ec) ✅ 2026-10-23 CLOSED AS SUPERSEDED, NOT FOLDED BY DESIGN (ec's box, closed on the coordinator's instruction; the done-when was never met and will not be): the champion carries the hybrid port (FP16 + end-of-row overflow check, FP32 recompute of overflowed rows), manifest V11-086 states `2ad8bff36` is not carried, and the live successor is the register-resident arm (V11-086, `fa-vkq-reg-on-c-20261022` @ `8110933ba`, gate HOLD, timing `v11-086-cpu` BACKLOG). Triage: `/mnt/raid0/llm/tmp/c3-fold-prep/PLAN.md` section 1.
    Cherry-pick onto the current champion tip (`1bceceb05`, or the tip after KVU-16h-fold), CPU store build on the
    champion recipe, G0 plus `test-backend-ops -o FLASH_ATTN_EXT -b CPU` and the CPU FA harnesses v1/v2 (expect the
    F16-V cases to change, every other case bit-identical), then the guarded CAS advance and the standing receipt.
    Done when the champion tip carries the commit with those gates recorded here.
    - *(2026-10-04 PM, workspace-ec; not ticked until the champion tip carries it.)*
      - The fix was ported as hybrid v2 `a99e5330a`.
      - It is folded into the next fold candidate, Yfa `9a3f1392a` (Y + the fix, without the opt-in arms).
      - Yfa's gates passed: bit-identical on the KVU-19 FA harness, 86 + 141 cases.
      - The advance to Yfa is workspace-89's next fold.
    - *(2026-10-21 triage)* superseded by autokernel-champion-aggregate.md fold ledger "Yfa" (057270556 + a99e5330a folded without 2ad8bff36) and manifest V11-086 EXCL (opt-in arm excluded by design; CPU-FA-VKQ-2 decides define-or-drop).
  - [x] **CPU-FA-VKQ-4 — report the CPU FP16-VKQ overflow upstream with the fix.** (filed 2026-10-04, workspace-ec; premise corrected and closed 2026-10-22 by the kernel follow-up intake, intake-2499, intake-2455) ✅ 2026-10-22
    Premise corrected (intake-2499): upstream has NOT fixed the GPU (MFMA) analog. #28576 removes only the per-MFMA fp16 round
    trip; the unnormalized VKQ partial is still staged as half before the row-sum division (`fattn-mma-f16.cuh` L1670-L1678,
    divide L1734 @ `ca29eaf`), and the opnan arms with and without it fail the same 6/228 cases. The GPU check is V11-FA-8.
    CPU side (intake-2455): the defect is upstream issue 29774 / PR 29810; KVU-LB1.a posted our reduced repro, accumulator
    peaks and fix data on PR #29810 (link in the KVU-LB1 section of this file, operator-approved 2026-10-22). That meets this
    task's done-when, so no separate report is opened.
    - *(2026-10-21 triage)* open (no evidence found).
- [ ] **KVU-22 — at the v11 rebase, carry upstream #29510 (`flash_attn_ext_rows`) as an A/B arm against KVU-19b.**
  (filed 2026-10-04, workspace-ec, survey Rec 4; trigger: the v11 rebase starts) #29510 is NVIDIA-MMA-only. It cannot
  slice DFlash2 verify batches or mixed ubatches (unified KV uses `split_simple`), and it falls back to dense when
  sequences share cells (`n_sum > n_kv`). So it complements KVU-19b rather than replacing it. If it has merged by
  then, port the `kv_rows` path to the HIP vec kernel and the CDNA MMA path. A/B it on the KVU-18 cells and the 4×80k
  shape, and drop whichever loses. Done when the A/B verdict is recorded.
  - *(restored 2026-10-21 from 465954bc0^, re-IDed from KVU-21.)*
- [ ] **KVU-7 — the MTP pool-full exception is a v11 experimental-kernel candidate.** v10 `ffc1bac82` with
  `-np 2 -c 4096 --kv-unified` and two 2048-token generations fails exactly one request with
  `speculative batch index 8 is not inside the current sub-batch [0, 8)`, instead of the clean
  `Context size has been exceeded.`
  - Reproduced 4/4. Evidence: research `artifacts/np_context_kvu_study_20260924/q38_27b_q8/unified/np2_L2048/server.stderr`
    and `q38_27b_q8_h/unified_poolfull_r{1,2,3}/np2_L2048/server.stderr`. The split controls
    `split_poolfull_r{1,2,3}` never error.
  - Locate it in the frozen source (read-only). File it on a `llama.cpp-experimental` branch together with the
    upstream "evict one slot" TODO (`server-context.cpp:3760`, audit T4b).
  - **Guarded:** the standing rule is no kernel research until the champion is consolidated, and the operator
    reopens it. The orchestrator already classifies the error (KVU-0e).

#### C2 — Restored task texts (v11 FA path, KVU-16g, KVU-19b, CPU-FA-VKQ)

Restored 2026-10-20. Commit `465954bc0` (2026-10-07) deleted 892 lines of this file in one commit, including every
task below; the ids stayed alive in `routing-and-optimization-index.md` RTG-57, in `dflash2-block-drafter-experimental-build.md`
DF2-9 and in `docs/reference/kernel-manifests/llama-v11-manifest.md` (rows V11-016/049/050/051/085/086), so they dangled.
The texts below are copied verbatim from `git show 465954bc0~1:handoffs/active/kv-unified-stack-rollout.md` (which also
holds the other deleted bodies, KVU-15..KVU-20, if any is wanted back); 2026-10-20 notes are marked. Ids not restored
here: none of the RTG-57 ids remain undefined. The owner named in these texts (workspace-ec) has had no bus heartbeat since
2026-10-08 (manifest at-risk item 2): the next session to claim any of them takes ownership.

- **v11 FA-path audit (2026-10-04, workspace-89; durable copy
  [`artifacts/v11-fa-path-audit-20261004/REPORT.md`](../../artifacts/v11-fa-path-audit-20261004/REPORT.md)).** Upstream
  #26046 deletes rocWMMA FA. On gfx90a, for our D=256 GQA-6 q8_0 shape, v11 then routes 3-32 query rows (4×1 batched
  decode, 1-3-slot DFlash2 verify) to the generic TILE kernel (no matrix cores; the RDNA4 analog #26220 lost ~2×) and
  >32 rows (4-slot verify, prefill) to MMA `<256,256,32,2>`, which spills 314 VGPRs under ROCm 6.2. The DF2-9 all-NaN
  path is the ROCWMMA=OFF route. These tasks gate the v11 rebase and RTG-58's P4 `kv_rows` phase
  ([`kv-prefix-fork-and-paged-attention.md`](kv-prefix-fork-and-paged-attention.md) KPF-40..42), and inform KVU-22 (the #29510 A/B arm, re-IDed from the old KVU-21).
  Owner of V11-FA-1..4: **workspace-ec** (filed 2026-10-04 at the coordinator's direction). Every build and run below
  takes `region-lock` for its host side.
- [x] **V11-FA-1 — A/B the champion with ROCWMMA=OFF (exact v11 FA routing) against ROCWMMA=ON, plus a third arm with
  #27870 and #28576 cherry-picked.** ✅ 2026-10-04 (filed 2026-10-04, workspace-ec, from the v11 FA-path audit §5) ROCWMMA=OFF
  reproduces upstream's D=256 routing: TILE at ≤32 rows, MMA above. The third arm approximates v11's MMA kernel
  (`b74f590ea` divergent-barrier fix, `bfdc32183` fp32 VKQ). Build in an experimental worktree, never the frozen tree.
  Bands: 4×1 decode, 1-3-slot DFlash2 verify (9-27 rows), 4-slot verify (36 rows), prefill (512 and mixed 512+3×9),
  own cells {4k, 16k, 57k} × foreign {0, 3×~100k}. Instruments: the 19b `perf2` micro-bench, `test-backend-ops` perf
  mode (TFLOPS, comparable to #28576/#28907), batched-bench `-kvu` vs `-no-kvu`, and the P3 harness L0 (v10: drafted
  36.3, no-draft 20.4 tok/s). Gate every arm on the DF2-9 reproducer (V11-FA-2) and on TILE D=256 `ncols2=2`
  run-to-run bit-exactness (those kernels have never been compiled into any of our builds). Done when the per-band
  delta is recorded here and decides one of: carry WMMA (V11-FA-4), retune the TILE/MMA crossover for gfx90a, cap
  ncols (V11-FA-3), or nothing.
  - *(2026-10-04, workspace-ec; prep done, slot not yet run, so not ticked.)* **Arms built, slot ready.** Scratch
    `/mnt/raid0/llm/tmp/v11-fa-ab-20261004/`; durable copy of the docs and runner:
    [`artifacts/v11-fa-ab-20261004/`](../../artifacts/v11-fa-ab-20261004/). Runner `gpu_slot_v11fa.sh` (one MI210 slot,
    budget 80 min, DF2-9 probes on every arm first). Arms: A `gpu-20261004-90c12df42-A` (ROCWMMA ON, champion recipe);
    B `gpu-20261004-90c12df42-B` (ROCWMMA OFF = v11 D=256 routing); C `gpu-20261004-5026470c6-C` (B + #27870 + #28576);
    D `gpu-20261004-fa5ebc0c8-D` (C + the CDNA D=256 MMA tuning of V11-FA-3); M upstream master `11fe02151`.
  - **The picks are neutral on the ROCWMMA-ON route** (`PICKS_ON_ROUTE.md`). Both #27870 and #28576 touch only
    `fattn-mma-f16.cuh`, and the ON champion launches no MMA kernel for any production shape: every cache-backed FA op
    has `K->ne[1] % 256 == 0`, so WMMA takes all > 2-row shapes. So arm A+ (ON + picks) was not built. The picks matter
    only on the OFF / v11 route.
  - **In v11 the drafter's 9-row block moves to MMA.** The DFlash2 drafter (D=128, GQA 4) block of 9 rows runs WMMA on
    the champion and D=128 MMA on v11 (≥ 5 rows), TILE at 3-4 rows. The audit did not list this shape; it belongs in
    the V11-FA-1 bands and the DF2-9 probes.
  - *(2026-10-04 PM, workspace-ec.)* **Ran; decision: carry WMMA (V11-FA-4).**
    - Slots: `slot-20261004T113710Z` (arms A/B/C/D/M/D32/D9; merged summary) and `slot-20261004T150551Z` (A/B/E/C).
      Durable copies: `artifacts/v11-fa-ab-20261004/slot-*/` (`summary.txt`, `perf_table.tsv`).
    - FA µs/op vs A (rocWMMA ON), on the v11 route:
      - 4×1 decode: ×0.60 (faster).
      - 1-3-slot verify, 9-27 rows: ×1.14-1.24 (TILE slower).
      - 36 rows: ×0.5-0.9 (B/C/M faster).
      - prefill-512: master M ×0.84-0.90; C ×1.09-1.16; B ×1.28-1.35.
      - drafter D=128, 9 rows: ×1.64-1.86 slower; 64 rows ×0.55-0.74.
    - Patches D and D9 do not help: D ≡ C at 512 rows, and D9 is ×1.35-1.42 at 9-27 rows.
    - The server DF2-9 arm errored on a busy port (18093) in both slots, so the model probe carries the DF2-9
      verdict (V11-FA-2).
- [x] **V11-FA-2 — root-cause DF2-9: all-NaN target features at ~2k-token prompts with ROCWMMA OFF.** ✅ 2026-10-04 (filed
  2026-10-04, workspace-ec, from the audit §0.4 and §4b) Build a standalone reproducer first: `test-backend-ops` cannot
  catch it, because its random [-1,1] inputs never overflow. Add a new FA case with large magnitudes and long KV
  (|V|~30, kv ≥ 4k) checked against the CPU reference. The length discriminator fits the >32-row MMA route: a short
  prompt's prefill goes to TILE, while ~2k prompts split into 512-row ubatches that go to MMA. Candidates in the
  audit's order: the D=256 MFMA-MMA route (consistent with the `99f3fffd6` unpadded-KV guard); the fp16 VKQ downcast
  (fp32 after #28576); the #27870 barrier. Record: `dflash2-block-drafter-experimental-build.md` DF2-9 and wiki CH-8.
  Done when the reproducer is 12/12 finite on the fixed path, or the faulting kernel and cause are recorded with an
  upstream issue.
  - *(2026-10-04, workspace-ec; reproducers built, GPU run pending.)* **DF2-9 sits on the MMA `<256,256,8,8>` route at
    60-340 tokens**, not `<256,256,32,2>` (see V11-FA-3's correction). Reproducers: `df29/` (op-level nan probe, the
    27B model probe `fa_nan_probe` and the server reproducer `df29_server.sh`, `df29/RECIPE.md`) run on every arm in
    `gpu_slot_v11fa.sh` step (a). **ggml CPU reproduces the fp16-overflow mechanism**: the CPU FA path accumulates VKQ
    in FP16 for F16 V and goes non-finite on diffuse attention over 2048 cells (CPU-FA-VKQ below), the same mechanism
    #28576 fixes for MFMA. Upstream issue text is drafted, never posted:
    `artifacts/v11-fa-ab-20261004/UPSTREAM-ISSUE-DRAFT.md`.
  - *(2026-10-04 PM, workspace-ec.)* **ROOT-CAUSED: the pre-#27870 MMA divergent-barrier race.**
    - Model-level probe (27B, 10 runs per arm):
      - B (ROCWMMA OFF): FAIL, 6/10 runs non-finite; first bad node `FLASH_ATTN_EXT` at layer 3.
      - E (B + #27870 only, `gpu-20261004-e9b3b04df-E`): PASS.
      - C (B + #27870 + #28576): PASS.
      - A (rocWMMA ON): PASS.
    - `test-backend-ops -o FLASH_ATTN_EXT -b ROCm0`: B 598/640; E and C 640/640.
    - Op-level determinism: B 84/228 identical; C, D and E 228/228.
    - So **#27870 is a mandatory v11 carry** (V11-FA-6), and #28576 is not needed for DF2-9.
    - The NaN is not an upstream issue, because #27870 already fixes it. The NaN framing in
      `UPSTREAM-ISSUE-DRAFT.md` is superseded; only a perf-only issue remains (V11-FA-5).
    - The opnan non-finites left on A/C/D/E/M are the synthetic `v=bias1024` diffuse cases (fp16-range stress), and
      they occur on every arm.
  - [ ] **V11-FA-2b — give `df29_server.sh` a free port.** (filed 2026-10-04, workspace-ec) The fixed port 18093 was
    busy in both slots, so the server-level DF2-9 arm produced no verdict. Pick a free port at launch and refuse
    loudly if none is free. Done when a slot records a server verdict for every arm.
- [ ] **V11-FA-3 — MMA `<256,256,32,2>` spills 314 VGPRs on gfx90a under ROCm 6.2; evaluate an ncols cap for D=256
  prefill.** (filed 2026-10-04, workspace-ec, from the audit §0.3 and §3.1) `<256,256,16,2>` has 0 spills (499
  registers including 243 AGPR). The spill is structural: 512 threads means 2 waves per SIMD on gfx90a's unified
  register file. Candidates: cap D=256 at `ncols1=16` on CDNA2, or give `(256,256,64)` 256 threads. Leave the choice to
  AutoKernel. Re-check v11's own code object (these numbers predate #28576) with the register-audit scripts in
  `artifacts/v11-fa-path-audit-20261004/register-audit/`. Done when the prefill A/B (ON vs capped) is recorded, and
  the cap is either carried into the v11 candidate or declined with the numbers.
  - *(2026-10-04, workspace-ec; patch built as arm D, GPU A/B pending.)* **Correction to the audit:** for the 27B (GQA 6)
    CDNA picks `ncols2 = 8` by its generic ladder, so every >32-row shape (4-slot verify, mixed ubatch, 512 prefill)
    runs **`<256,256,8,8>`** (64 columns, 512 threads), not `<256,256,32,2>`; the latter is what a GQA-2 model or RDNA
    would run (`NCOLS_CAP.md`, register numbers from `fa_codeobj_audit.py`). Arm D implements the tuning: ncols2 by
    divisibility plus a 16-column cap (GQA 6 → `<256,256,8,2>`, the only spill-free D=256 MMA config with fp32 VKQ),
    with runtime knobs `GGML_CUDA_FA_CDNA_D256_MAX_COLS` and `GGML_CUDA_FA_CDNA_D256_MMA_MIN_ROWS` (arms D32, D9).
  - *(2026-10-04 PM, workspace-ec; A/B recorded, not ticked.)* **The ncols cap brings no gain.**
    - Arm D (16-column cap) ≡ C on 512-row prefill: ×1.16 / ×1.12 vs A.
    - D9 (MMA from 9 rows) is ×1.35-1.42 at 9-27 rows.
    - For reference, D32 measured ×0.97 / ×0.92 and master M ×0.90 / ×0.84 at 512 rows.
    - Recommendation: decline the cap. Still missing before the tick: the register re-check on v11's own code object
      (master `11fe02151`), which the slots' register tables do not include.
  - *(2026-10-20 restore; manifest V11-051.)* The default-on 16-column cap (`GGML_CUDA_FA_CDNA_D256_MAX_COLS`,
    `..._D256_TUNE=0` to disable) is carried in `experimental/v11-fa-ab-20261004` @ `2e0f9dd06`/`fa5ebc0c8` and is
    GPU-unvalidated; it is NOT in candidate C. Remaining work is unchanged: the register re-check on v11's own code
    object, then carry (`MAX_COLS=16|32` bench at the 27B shapes) or decline with the numbers. This task is the
    owner of manifest row V11-051.
- [ ] **V11-FA-4 — in v11, carry rocWMMA FA as an in-binary arm until TILE/MMA is at least as fast on every band.**
  - *(2026-10-27, workspace-58 results harvest)* fa4-c5-matched-bands attempts 1-2 INVALID (residency proofs); attempt 3 INCOMPLETE: op-level exact-set control failed (synthetic nan stage ON 4/228 non-finite, OFF 6/228, intersection 2, all bias1024/diffuse). FA4-SIXKEY-DIAG-1 (5 processes/arm): 6 keys SYSTEMATIC path difference, 2 INCONCLUSIVE, mechanism unknown. Model level before the refusal: df29 PASS both arms (0/10 non-finite); greedy prod server 14/15 text_head identical (<=160 chars, 32 tokens; 1 divergence at char 93), sampled orig 11/13; 0 garbage; DFlash2 acceptance 0.681 vs 0.689. No band/perf verdict and no task-accuracy comparison. Artifacts `/mnt/raid0/llm/tmp/codex-ni-20261027-fa4-attempt2-fix/out/`, `/mnt/raid0/llm/tmp/codex-ni-20261027-fa4-sixkey-diagnostic/out/VERDICT.json`. [no-belief: correctness-only, perf incomplete]
  - 2026-10-29 `fa4-c5-exact-set-r2-20261029` first normal grant ended 19:21:50Z rc75 at `WAIT-INTERRUPTED: disk free below 150 GiB floor plus 8 GiB output reserve`. ADMIT_PASS at 151.05 GiB was followed by the stricter wait check; no new native process/result or NORMAL-COMPLETE is evidenced for this attempt. Later repeated waits remain separate. Restore adequate headroom and reconcile advertised output with the actual guard before normal execution; preserve the floor and require all exact-input/native outcomes under the existing task. No equivalence, mechanism, performance or promotion verdict. Evidence `/mnt/raid0/llm/tmp/codex-ni-fa4-exact-set-successor-20261029/ws58-launcher.out`. [belief: cc]
  - [ ] **V11-FA-4a — decide the exact-set control for synthetic bias1024 stress cases (membership difference proven systematic), then re-run the band comparison.**
  - *(2026-10-30 checkpoint; full task remains open.)* R8's same-launcher arm-A smoke is accepted only for the one real `control_25c` request, native writers/cleanup and 20 in-window proofs; its full job repeatedly yielded at the disk/output gate before native work. The owned R8 poller was STOPped via captured pidfd; original logs and STOP are retained, its armed JSON is archived at `/mnt/raid0/llm/tmp/compute-flags/ready/withdrawn/fa4-c5-exact-set-r8-20261030.retired-resource-gate-20261030.json` (SHA-256 `666daede8c8319996869a488dcfc432f90a8c02b4c7a095079d6faaf4fceb7ab`). The stop-file re-arm exited rc=1 before native start. R9 adds only exact `/proc` read-path eligibility to the pidfd-bound race retry; six-path terminal controls and live/mismatch/required-native refusal controls pass. R9 has not smoked or completed the comparison. The fresh split-storage R10 packet preserves the original full protocol and 1-GiB output budget; Micron admission plan is 151.125 GiB, RAID metadata/source/launcher/state/log cap 128 MiB above the unchanged 150-GiB floor. [no-belief: smoke/source diagnostics only]
    - 2026-10-29 (ws58 filer A): `fa4-bias-sensitivity-20261028` rc0 00:09:38Z (GPU mi210_0 + 72-95,184-191, 45 s, 30/30 stages: V-bias offsets 128/256/512/768/1024 x ON/OFF x 3 fresh-process repeats over the 8 original bias1024/diffuse geometry keys, original Q/K/mask seeds, only V changed). Predeclared rule: ungraded value-bias sensitivity, no timing/quality/causal/promotion verdict -> diagnostic observation. Each arm's output FNV64 is identical across its 3 repeats at every bias and key (0 of 80 cells unstable); ON and OFF outputs differ at every cell. Nonfinite onset: bias 128 and 256 give 0 nonfinite in both arms; at 512 only OFF goes nonfinite (r512/kv4096, F16 and Q8_0, 47,616 each); at 768 and 1024 both arms go nonfinite on partly different keys (ON: r512/kv4096 49,152 and r64/kv2048 6,144 per type at both biases; OFF: r512 at both KV sizes, plus r64/kv4096 at 1024). Meaning: the bias1024 exact-set membership difference is a deterministic, bias-dependent finite-range property of each path, not run-to-run noise; mechanism not established. Evidence `/mnt/raid0/llm/tmp/codex-fa4-bias-probe-20261028/RUN_COMPLETE.json` (raw logs under `attempts/`). [belief: cc]
      - [ ] **V11-FA-4a-fu1 (filed 2026-10-29):** use this map to choose the exact-set control and write it into the band predeclaration before re-running the V11-FA-1 bands: either a synthetic stress set at bias <= 256 (both arms 0 nonfinite) or bias1024 with nonfinite membership compared as a predeclared per-key set.
    - *(2026-10-29, Codex refactor diagnostic.)* The scheduler-granted FA4 bias-sensitivity run completed rc0 with all 30 native stages and drained children. For each arm and bias, the denominator is eight geometries repeated three times, not 24 independent geometries. ON/OFF nonfinite cases were 0/24 and 0/24 at biases 128 and 256; 0/24 and 6/24 at 512; 12/24 and 12/24 at 768; and 12/24 and 18/24 at 1024. A separate reopening verified all 240 raw case keys and nonfinite counts, 30 raw-log SHA-256 bindings, 40 matched bias/geometry groups, matching FNV input identities within groups, stable Q/K/mask FNVs across bias levels, and own positive GPU-residency witnesses in every stage. FNV is not a cryptographic input identity. Native result `/mnt/raid0/llm/tmp/codex-fa4-bias-probe-20261028/RUN_COMPLETE.json` SHA-256 `cc96161018b085019fa4e8550170c619e11200f1ad929bbba0fc24d50f5bd921`. These synthetic diagnostics do not establish the mechanism, model quality, timing, or a promotion outcome; the parent exact-set decision and band run remain open. [belief: cc]
    - *(2026-10-29, Codex refactor prep.)* A prospective ungraded value-bias probe is READY for scheduler admission as `fa4-bias-sensitivity-20261028`, source `/mnt/raid0/llm/tmp/codex-fa4-bias-probe-20261028/`. It retains the eight original geometry keys and compares C5 ON/OFF at five value biases in three alternating fresh-process pairs, preserving Q/K/V/mask identities and raw finiteness results. The exact actual launcher passed real small-model lifecycle normal (rc0, 66.09 s) and forced cutoff (outer rc75, partial, 64.93 s), with own KFD/HIP/VRAM witnesses and children drained; these are launcher smokes, not FA4 sensitivity results. READY submission is not scheduler acceptance. V11-FA-4a remains open and no mechanism, quality, timing or promotion conclusion is established. Prospective capture enrollment: `VB-FA4-BIAS-WIRE`. [no-belief: diagnostic preparation only]
  - [ ] **V11-FA-4b — model-level rocWMMA ON/OFF quality A/B**: same two images, >=100 greedy prompts (-np 1, --cache-ram 0, n_predict 512, prod q8_0 KV + f16 variant, drafter OFF and ON) reporting token identity and first-divergence index, plus >=200 scored items (olympiad/math + coding) paired McNemar; agree = paired accuracy diff 95% CI within +/-2 pp and 0 non-finite/garbage.
    - [x] **V11-FA-4b source and admission preparation — freeze the two-image, four-config quality matrix and receive MAIN acceptance.** ✅ 2026-10-27 — research commit `1a71ba5b660c59f53119822468d7164b51cbd6de`; frozen matrix manifest SHA-256 `7cec33127e4162b89610d4e8b66eb362fb289e3fde1dadbc20e2834d36f13a51`; source manifest SHA-256 `eadfbb2c5b9fa06887b43470ff96fe9ba8ca6d9827a3b5198232ee36995b4832`. Eight source tests, five wrapper tests, row validation, same-entry model-free T1 and private normal admission passed. Temporary PF poller reaped. This closes preparation only; later quality slice 1 failed on `no_reference`, with no quality verdict. [no-belief: source and admission preparation only]
    - *(2026-10-27 12:30Z, ws58 results harvest.)* **Slice 1 (ON, q8_0, drafter off) FAILED 12:02:34Z, rc1, no quality verdict.** GPU quarter job `v11-fa4b-quality` started 11:33:09Z (cpus 184-191), served about 29 min on the C5 gpu image `gpu-20261024-c72ec82f5-c5` (5,962 positive during-run residency proofs, sampler error none), then `v11_fa4b_quality.py:269` raised `ValueError: scoring undecidable: no_reference` from `parse_response`. Meaning: a scoring-harness defect (a scored item reached the parser with no reference answer), not evidence about rocWMMA; the number of completed observations is not recorded (only one exec record and the proofs file exist; `slice-result.json` carries no count). Residency was proven, so the 29 min of GPU time is wasted but the harness failed closed. Evidence: `/mnt/raid0/llm/tmp/codex-ni-20261027-fa4-sixkey-diagnostic/model-quality-row-prep/OWNER-POLLER.log`, `out/slices/1793100720-ON-q8_0-off/slice-result.json`. Next: find which item lacks a reference (corpus manifest vs `quality_gpu_job.py` item list), fix and add a pre-flight that every item has a reference before the server is launched, then re-run slice 1 (new row). Box stays open. [no-belief: harness failure, no quality measurement]
    - **Supersedes the prior `Next: find which item lacks a reference` instruction:** item 100, `leetcode_find-the-index-of-the-first-occurrence-in-a-string`, has a native gold oracle (`expected=strStr` and two `entry_point_cases`). The false `no_reference` came from applying the research scorer's `test_cases` profile to the LiveCodeBench `entry_point_cases` profile; this is a scorer-profile mismatch, not a missing corpus reference.
    - [ ] **V11-FA-4b-fix1 (filed 2026-10-27, ws58):** locate the `no_reference` item(s), make `v11_fa4b_quality.py` validate the whole item set (every item has a reference) BEFORE launching the server, then re-run slice 1.
    - [x] **V11-FA-4b-fix1a — scorer-repair audit and regression controls.** ✅ 2026-10-27 — Published research branch `codex/v11-fa4b-quality-20261027` at `b607e190` adds M2 whole-manifest validation against the pinned LiveCodeBench oracle and routes coding items through the native scorer; M1 remains immutable. Pinned M2 source SHA-256 `ad0e3f5a6182ab918782bd4fc300d84ef5f23fc6fda4554d496fddff22dd6d36`; source tests SHA-256 `a8b5f7f973311aa98fd5f6c9fd730404554be9c00048b940ad0ff2999e613e09`. Existing controls: 5/5 source tests, including item 100 native-correct/mutated-wrong, missing-case preflight refusal, and normal corpus acceptance; wrapper PF2 failed its cursor-fixture expectation, corrected PF3 passed 1/1. Item 100's ON/OFF captures are individually `correct=true`, not a paired quality verdict. Full paired quality matrix remains open. [no-belief: scorer repair/regression controls; no quality measurement]
    - *(2026-10-27 14:00Z, ws58 results harvest.)* M2 quality slice (`model-quality-row-prep/out-repair/`) ended rc0 at 13:45:44Z (grant 12:38-13:53Z); `slice-result.json`: error null, 13528 positive during-run proofs, sampler error null. PROGRESS ONLY, no quality verdict until all cells complete. Present on disk: one cell, `OFF/q8_0-off`, 200 scored-item files plus 20 score chunk markers (all 20 chunks complete), and 96 files in `greedy/` of which 8 are chunk markers (chunks 000-080 complete; 88 item files, 0 beyond chunk 080). That is 1 of 8 cells started; 288 of 2,400 observations counted as item files (not scored). Remaining: 7 cells and the rest of the greedy set. [no-belief: partial progress, no verdict]
    - *(2026-10-28 ~03:45Z, ws58, NI recorded-scorer diagnostic; checkpoint `09dacf490`.)* MAIN accepted the bounded diagnostic after `v11-fa4b-quality` ended rc0 at 03:01:18Z. The producer REPORT is DECIDABLE but `agreement_all_configs=false`: agreement across configs is FALSE and completion is not a quality-equivalence pass. 200 matched scored and 100 greedy pairs per config. C5 ON minus OFF, 95% paired interval: q8/off -0.5 pp [-2.5,+1.0], McNemar 1 vs 2, 37/100 token-identical; q8/on +1.0 pp [0,+2.5], 2 vs 0, 39/100; f16/off +1.5 pp [0,+3.5], 3 vs 0, 38/100; f16/on 0 pp [-2,+2], 2 vs 2, 29/100. Only f16/on met the predeclared +/-2 pp rule; intervals crossing the margin do not prove a difference beyond it. Length-capping was heavy: 102-105/200 scored and 98-99/100 greedy outputs per arm/config were truncated, scored unchanged. No timing, promotion or universal quality claim. Independent model-free replay (`/mnt/raid0/llm/tmp/codex-ni-20261028-fa4b-completion-audit/audit-venv.log`) validated retained response/identity links, the 100 M1 math records under their original seal, and exact analyzer report reproduction; the analyzer trusts sealed capture-time scorer booleans and does not re-execute generated code. Same-PID/birth HIP+KFD+positive-VRAM proofs for M1 and 12 M2 slices; per-task affinity masks and a unique HIP-to-PCI map were not independently reconstructable. A prior slice hit the 150 GiB disk guard and resumed; no failed request was omitted. The V11-FA-4b parent box stays open (owner decides exact task scope). Source: `/mnt/raid0/llm/tmp/codex-ni-20261027-fa4-sixkey-diagnostic/model-quality-row-prep/out-repair/REPORT.json`. [belief: cc]
    - 2026-10-28: paired ON-minus-OFF accuracy delta 95% CI within +/-2 pp AND 0 non-finite/garbage (predeclared, `PREDECLARATION-M2.md`) -> met in 1 of 4 cells (f16/draft-on 0.0 pp [-2.0,+2.0]); q8_0/off -0.5 pp [-2.5,+1.0], q8_0/on +1.0 pp [0.0,+2.5], f16/off +1.5 pp [0.0,+3.5] fail the margin; every McNemar p >= 0.25 (discordants 1-3 of 200), so no significant difference, but equivalence within 2 pp is NOT established -> correctness-only (rule unmet, parent stays open; the REPORT carries no explicit non-finite/garbage counter, only per-item undecidable=none). Caveat: 98-99/100 greedy and 102-105/200 scored outputs per arm/config hit the 512-token cap. Evidence: /mnt/raid0/llm/tmp/codex-ni-20261027-fa4-sixkey-diagnostic/model-quality-row-prep/out-repair/REPORT.json. [belief: cc]
      - [ ] **V11-FA-4b-fix2 (filed 2026-10-28):** the 200-pair n cannot resolve a +/-2 pp margin when length-capping hits half the items; decide with the owner between a larger paired n and an uncapped n_predict re-run of the 3 failing cells, and add an explicit non-finite/garbage counter to the analyzer REPORT so the second half of the rule is machine-checked.
  (filed 2026-10-04, workspace-ec, from the audit §4 "Can rocWMMA FA be carried in v11? Yes" and §5.3)
  - Restore `fattn-wmma-f16.{cu,cuh}`, the dispatch branch and the CMake/`hip.h` flags.
  - Keep the tile skip-list out, so the same binary carries TILE for the A/B.
  - Adapt to v11's `fattn_kernel_t`/`launch_fattn` signatures.
  - Re-apply `db18f3937` and KVU-19a's WMMA hunk.
  - Keep the `99f3fffd6` D=256 unpadded-KV → TILE guard until v11 `test-backend-ops` on ROCm0 proves MMA D=256
    unpadded is correct.
  - Expose it as a runtime knob (e.g. `GGML_CUDA_FA_PREFER_WMMA`), so the ONE candidate carries its own control.
  - Cost: ~1-2 days plus a recurring conflict tax. It pins rocWMMA 1.x; ROCm 7 brings back #16221/#19461.
  - Drop-when: TILE/MMA ≥ WMMA on every V11-FA-1 band, and DF2-9 is clean without WMMA.
  - Done when the v11 candidate carries the arm, or V11-FA-1 shows it is not needed.
  - *(2026-10-04, workspace-ec.)* The bands that decide it now include the drafter's 9-row D=128 block, which v11 moves
    from WMMA to MMA (V11-FA-1 note); arm A vs B/C/D in `gpu_slot_v11fa.sh` is the deciding run.
  - *(2026-10-04 PM, workspace-ec.)* **Justified by V11-FA-1.** On the v11 route:
    - TILE is ×1.14-1.24 slower for 9-27 rows.
    - The drafter's 9-row D=128 block is ×1.7-1.9 slower.

    WMMA therefore stays the arm for 9-32 rows. 4×1 decode (×0.60) and 36 rows are faster on the v11 route, so the
    knob should send only the 9-32-row band to WMMA.
  - *(2026-10-20 restore.)* No manifest row carries this arm yet; the v11 candidate list must either carry it or
    record the decline (kernel-manifests README rule 4). Caution: the A/B behind the 'justified' note above ran on
    the 2026-10-04 builds, not on candidate C.
- [ ] **V11-FA-5 — draft (never post) the upstream perf-only issue: on gfx90a, v11's TILE/MMA is slower than the removed
  rocWMMA FA for 9-32 rows.** (filed 2026-10-04, workspace-ec; WARRANTED under the upstream-report rule.)
  - Scope is perf only: the DF2-9 NaN is already fixed upstream by #27870.
  - Content: the V11-FA-1 numbers (`perf_table.tsv`), the arms and builds, and the drafter's D=128 9-row shape.
  - Done when the draft is in `artifacts/v11-fa-ab-20261004/` and handed to the operator. Posting it is the operator's
    call.
- [ ] **V11-FA-6 — the v11 candidate must carry #27870 (mandatory for DF2-9).** (filed 2026-10-04, workspace-ec) *(2026-10-23 triage, left open: the code part is DONE, `f88127a86` is an ancestor of champion 141e4bcf5 (V11-049 IN); the OWED part is the gate, scheduled in CH-29 as an extra `-c3-rwoff` GPU image (`FOLD_ROCWMMA=OFF`), `test-backend-ops -o FLASH_ATTN_EXT -b ROCm0` 640/640 and the df29 10-run probe. Plan: `/mnt/raid0/llm/tmp/c3-fold-prep/PLAN.md` sections 3-5.)*
  - *(2026-10-27, workspace-58 results harvest)* OFF-route df29 probe on c72ec82f5 ROCWMMA OFF (`cal-1026/fa4-c5-rwoff-r2/build`) PASS 0/10 non-finite (f16 + q8_0, R 9/36/512/2048, VRAM 29.36 GiB); ON control PASS. Half the gate met; test-backend-ops FLASH_ATTN_EXT 640/640 on OFF still owed. Artifact `/mnt/raid0/llm/tmp/codex-ni-20261027-fa4-attempt2-fix/out/model_B/verdict.txt`. [no-belief: correctness-only]
  - [x] **V11-FA-6a — run test-backend-ops -o FLASH_ATTN_EXT -b ROCm0 on the rwoff-r2 OFF build (640/640) as a standalone correctness row.** ✅ 2026-10-28 — the documented equivalent current full suite passed 2978/2978 on the sealed OFF build; the old 640 count is a stale plan count, not a replacement partial threshold. See the native completion below. [belief: cc]
    - [x] **FA6a bounded same-launcher diagnostic smoke and READY** ✅ 2026-10-28 — native smoke started at 17:31:09 UTC, ran 75.114 s, rc 75 / partial=true; 643 printed successful operations, 732 during-run own HIP/KFD/positive-VRAM samples, result writer and captured-PID cleanup verified. No terminal summary or gate verdict (gate_pass=null). Owner accepted diagnostic READY; `progress/2026-10/2026-10-28-fa6a-diagnostic-ready.md` records exact evidence and pins. The packet's source/version equivalence establishes the current 2978-case terminal gate; at smoke time the full gate remained open; the subsequent full gate is recorded below. [no-belief: bounded diagnostic smoke, no full correctness or measurement warrant]
    - *(2026-10-28, native full gate.)* Normal row `v11-fa6a-off-native-20261028` ran 17:42:07-17:47:20 UTC, rc 0 / nonpartial. Native ROCm0 log terminates with `2978/2978 tests passed`, `Backend ROCm0: OK` and `2/2 backends passed`; result writer reports gate_pass=true, 312.229 s and cleanup_verified=true. There are 3,076 during-run same-recorded-PID HIP/KFD/positive-VRAM samples; captured PIDs are now absent. `suite-equivalence.json` binds unchanged C3/control and C5 OFF test/dispatch source bytes and explains the current 2978-case gate. This closes only FA6a's OFF native operator test; the V11-FA-6 parent, broader FA4 controls and promotion remain open. Exact evidence, hashes and limits: [native gate](../../progress/2026-10/2026-10-28-fa6a-native-gate.md). [belief: cc]

  - The v11 rebase must contain `b74f590ea` (#27870).
  - Gate the candidate on the DF2-9 model probe (`df29/`, 10 runs, 0 non-finite).
  - Also gate it on `test-backend-ops -o FLASH_ATTN_EXT -b ROCm0` at 640/640 on the ROCWMMA-OFF route.
  - Done when the v11 candidate's gate record shows both.
  - *(2026-10-20 restore; manifest V11-049.)* Candidate C `f0c96dc1f` already carries #27870 as `f88127a86`. The
    ROCWMMA-OFF route probe (10/10 on an OFF build) and `test-backend-ops` 640/640 on that route are still owed
    (CH-20 item 3 in `autokernel-champion-aggregate.md`). CH-18 also lists #27870: reconcile at the v11 pull so it is
    not applied twice.
- [x] **V11-FA-7 — decide upstream #28576 (fp32 VKQ accumulation on MFMA; manifest V11-050): fold into the v11 candidate, exclude with reason, or defer explicitly.** Decided 2026-10-22: carried by the pull. ✅ 2026-10-22
  (filed 2026-10-20 from the derived-actionables gate; the 2026-10-04
  shard declined a separate #28576 carry task because DF2-9 does not need it and a master-based v11 contains it, but
  manifest row V11-050 is still PEND/'decision open' and README rule 4 requires fold/exclude/defer before the freeze.)
  Branch `experimental/v11-fa-ab-20261004` @ `5026470c6` (pick `bfdc32183`). Bench cell: GPU FA exactness (`test-backend-ops
  -o FLASH_ATTN_EXT -b ROCm0`) plus occupancy (CDNA config 4 to 3) at the 27B shapes, using the V11-FA-1 harness
  (`artifacts/v11-fa-ab-20261004/`). If the v11 pull is taken from master and master already contains #28576, the
  outcome is 'carried by the pull' and the row is closed with that sentence.
  - *(2026-10-22, research intake intake-2499.)* Outcome: **carried by the pull.** `bfdc32183` (#28576) is an ancestor of upstream
    master `11fe02151`, so a v11 pull from master at or after 2026-09-14 carries it (candidate C does not); presence gate on the pulled
    base: G-ANC on `bfdc32183`. It is perf-only on MMA-routed MFMA shapes and overflow-neutral: the raw VKQ partial is still staged as
    half before normalisation, and the opnan arms with and without it fail the same 6/228 cases. It does not touch the ROCWMMA-ON
    champion route. The occupancy 4 to 3 change is the CDNA-only (64,64,64) config, not a 27B shape; register cost at D=256 stays
    with V11-FA-3. Candidate FA gates compare the non-finite case set against the incumbent instead of demanding 0/228 on the
    bias1024 diffuse stress. Cite only the PR's on-path perf rows (nb >= 512, MMA-routed).
- [ ] **V11-FA-8 — GPU sibling of the CPU-FA-VKQ probe: does the MMA kernel's half-staged VKQ partial overflow on the 27B?** (filed 2026-10-22, intake-2499) Dump per-channel max abs(V) and the per-row unnormalized row sums over one warp's KV share from the 27B FA layers on an ~8k repetitive prompt and a 57k context, and evaluate them for arm A and candidate C of the V11-FA-1 harness. File the upstream report on the MMA shared-memory half staging only if a value is non-finite or exceeds FP16 range. Correctness class (no quiet host); launcher and PREDECLARATION.md written before compute, main arms the queue row. Done when the per-layer peaks are recorded here with the verdict (safe / at risk / overflow).
- **Other restored tasks cited by RTG-57 / the v11 manifest (parent task bodies remain in git history).**
  - [ ] **KVU-16g-1 — run the row-5c prefill-budget A/B (`gpu_slot.sh`) and score it against the done-when above.**
    (filed 2026-10-04, workspace-ec) Then fold `65d48a7a0` into the champion through the KVU-19 fold route if it
    passes, or record why not.
    - *(2026-10-20 restore; manifest V11-016.)* The A/B ran: GPU run dirs `gpuab-20261004T145622Z` and
      `gpuab-20261004T172118Z` under `/mnt/raid0/llm/tmp/prefill-budget-20261004/` (scratch; durability unverified). The
      fold ledger (candidate W, `autokernel-champion-aggregate.md`) quotes pb512 decode-under-prefill x2.92 with solo
      prefill -4% vs `-b 512` x3.22 / -14%, and the feature is folded in the champion (`7052e26df`, default OFF).
      The original done-when (decode under a neighbour's prefill >= 4x at <= 30% TTFT cost, KVU-16b re-run) is NOT met
      by x2.92 as quoted (unverified: score sheet not read). Closing this task = copy the per-arm table from the run
      dir here and record the score against the done-when; the enable decision is KVU-16g-2.
    - *(2026-10-26, workspace-58 wrap-up; parent KVU-16g and this box stay open.)* Read-out of the existing 2026-10-04 A/B (`/mnt/raid0/llm/tmp/prefill-budget-20261004/gpuab-20261004T172118Z/`; `gpuab-20261004T145622Z/` is empty). One sample per arm, fixed order, OFF = b/ub2048 (not the served optimum). Decode-during-neighbour x vs OFF / TTFT cost / solo prefill: b512 x3.22 / +21.5% / -13.7%; pb512 x2.92 / +26.7% / -3.6%; t1000 x3.87 / +44.8% / -3.8%. No arm meets the done-when (>=4x at <=30% TTFT cost): pb512 passes cost but misses gain, t1000 misses both. No paired correctness / test-backend-ops green artifact found. Historical descriptive read-out, not decision-grade; no flag is enabled. Source: `/mnt/raid0/llm/tmp/cal-1026/kvu16g1-fa4-audit/OWNER-READOUT.md` (sha `93faf270…`).
      - [x] **KVU-16g-1 read-out of the existing 10-04 A/B scored against the done-when (read-out only; done-when NOT met).** Per-arm table above. ✅ 2026-10-26 [belief: cc]
      - [ ] **KVU-16g-1 done-when unmet (checkpoint wrap-ws58-20261026-2320).** Needs prospective g-2 measurements on the current candidate: OFF byte identity, decode-only np4 TPOT target, package gates. Do not enable flags or tick KVU-16g.
  - [ ] **KVU-16g-2 — enable `--prefill-budget-decoding` (+ `--prefill-budget-target-ms`) on :8083 in the v11 stack-change package.**
    (filed 2026-10-20 from the derived-actionables gate; manifest V11-016 and the champion aggregate say 'the :8083
    switch lands with v11' but no task enabled it.) Choose the target-ms from the PB-QCOST-1 fit
    (`gpu-serving-tie-in-program.md`); gate: decode-under-prefill >= the KVU-16g x2.92 reading, solo prefill within -4%
    to -14%, off == byte-identical; part of the one v11 stack-change signature (no piecemeal reload).
    - *(2026-10-24, batch-a.)* Package component drafted (not a deploy): `docs/design/prefill-budget-8083-stack-change-package.md` adds `--prefill-budget-decoding N` + `--prefill-budget-target-ms MS` to the :8083 argv inside the one v11 signature, with the flag semantics read from `7052e26df`, the SW-A2/A3 target-ms rule (`target_ms = TPOT_target_ms - margin`, margin = PB-QCOST-1 held-out one-sided P99 residual, currently 211.2 ms/iter at n = 4, INDICATIVE until confirm-R), the DI-126/PB-HOL-1 scope caveat, gates, and rollback (remove flags). N and TPOT_target_ms are NOT set (no source for either): they need the KVU-16g-1 score sheet / decode-only step time. Box stays open: the gate (decode-under-prefill >= x2.92, solo prefill within -4..-14%, off == byte-identical) needs numbers not yet produced. Job specs owed (not run): (a) KVU-16g-1 read-out of `/mnt/raid0/llm/tmp/prefill-budget-20261004/gpuab-*/` score sheets; (b) decode-only step time at np4 for TPOT_target_ms; (c) OFF byte-identity greedy run on the v11 candidate.
  - *(2026-10-21 research intake, intake-2221#07, intake-2218#02, intake-2219#06.)* The budget is decode-gated: `prefill_budget_get()` returns 0 when `pb_iter.n_generating == 0` (98c0ce12a), so enabling it covers decode-vs-prefill interference only, never prefill-vs-prefill head-of-line (DI-126); PB-HOL-1 (gpu-serving-tie-in-program.md) measures that residual, and this enable must not be counted as covering DI-126.
  - *(2026-10-22, PB-HOL-1 budget-on arms.)* The budget is not a HOL fix: with pb512 armed (and `-b`/`-ub` 2048) the short prompt above the long slot waited 83,352 ms vs 70,932 ms budget-off; below the long slot 3,593 vs 3,217.5 ms. Enabling it still covers decode-vs-prefill interference only. Also: take target-ms from the PB-QCOST-1 REFIT (the frozen model failed, MAPE 12.84% / 26.32%), and only after its uncontended confirmation run. Dormant fragmentation guard: if the KVU-16g A/B log shows the budget split across >= 4 prefilling slots with < 64 tokens each per iteration, file a minimum-effective-chunk rule on the experimental tree (the literature's APC gain is against a degenerate 0.78-token-chunk baseline, so no task before the trigger).
  - [x] **KVU-19b-fold-c1-p3 — P3 B on the 27B against the folded champion: `-kvu` batched decode within ~5% of
    `-no-kvu`.** ✅ 2026-10-25 (WITHIN_5PCT: −0.94% vs the v1 reference −15.23%, INDICATIVE) [no-belief: cc-register pending (VB-CC-PILOT)] (filed 2026-10-04, workspace-ec, split from fold-c1's done-when) workspace-89's P3 harness
    (`p3_kvu_probe.sh` with a `BIN` override) on `gpu-20261004-1bceceb05`, arms skip on vs the same binary with
    `GGML_CUDA_FA_SEQ_ROWS=0` and `-no-kvu`; no-draft arms on their own server launch (KVU-16h-runner). Run it
    in the coordinated GPU block that also serves KVU-19 (workspace-89). Done when the per-arm table is recorded
    here.
    - *(2026-10-20 restore.)* Define-or-delete: the folded champion has since advanced (`dd3d9721c`); either re-aim this
      P3 B run at the current champion in the next coordinated GPU block, or record 'superseded by the v11 gate' and
      delete the id (the RTG-57 row cites it as `fold-c1-p3`).
    - *(2026-10-25 read-out, workspace-58 wrap-up; ticked by the predeclared rule.)* Re-aimed at the current champion, as the 10-20 note asked: calendar item `kvu19b-p3` (`/mnt/raid0/llm/tmp/cal-1025/kvu19b-p3/`), champion store image `gpu-20261023-dcc853b55-c3` resolved from `ak/champion`, Qwen3.8-27B-Q8_0, `llama-batched-bench` npl 4, npp 16384, ntg 64, HIP graphs ON, a fresh process per arm, ABAB. Predeclaration sha256 `6b72d2e3…c4476`. Rule: kvu vs no-kvu S_TG delta, edge −5.0% of the no-kvu mean; both pairs and the mean on the same side; within-arm spread ≤ 3.0%.

      | arm | S_TG (t/s) | S_PP (t/s) |
      |---|---|---|
      | K1 `-kvu` | 56.67 | 833.8 |
      | N1 `-no-kvu` | 56.45 | 831.5 |
      | K2 `-kvu` | 55.20 | 823.1 |
      | N2 `-no-kvu` | 56.48 | 824.3 |
      | S1 `-kvu`, `GGML_CUDA_FA_SEQ_ROWS=0` (diagnostic, one run) | 47.02 | — |

      Mean S_TG kvu 55.93 vs no-kvu 56.47 = **−0.94%** (pairs +0.39%, −2.27%; within-arm spread K 2.62%, N 0.07%; S_PP +0.07%). Box result **WITHIN_5PCT**. The v1 P3 on production v10 was −15.23% at the same npp. The SEQ_ROWS=0 control is −15.9% vs kvu, so the per-row skip carries the gain. Timing class: indicative (block-timing-pairable, host co-tenants allowed). Evidence: research `data/kvu19b-p3/` (VERDICT, RUN_RECORD, per-arm JSON, SHA256SUMS; committed `84ae00217`, on main via `237a7a789`). This unblocks the kvu part of the v11 stack-change signature.
  - [x] **KVU-19b-rework-c2-cal — triage the two slot-3 calibration FAILs, then hand commit 2 v2 to workspace-89.**
    (filed 2026-10-04, workspace-ec)
    - (a) The hs=128 bound: decide whether the bound is mis-set, or the layouts-off path still differs from KVU-19a.
    - (b) Case 152: it fails against the CPU reference on every arm, k19a included, so fix the reference or the
      threshold.
    - Done when both are explained with numbers, and the fold hand-off (or the drop of commit 2) is recorded here.
    - ✅ 2026-10-23 (operator decision ~16:20Z): **commit 2 dropped.** Excluded from v11: ~14% slower on aligned verify, skip-on/off exactness breaks 6/119; no GPU triage. KVU-19b-rework-c2 closed with it.
    - *(2026-10-20 restore; manifest V11-085.)* Commit 2 is currently EXCLUDED from v11: about 14% slower on the aligned
      4x8 verify and breaks skip-on == skip-off exactness (6/119 cases); the rework result was not found. Branches
      `experimental/fa-maskskip-batched-20261004` @ `c7f5ac9ad`, `...-v2-20261004` @ `439b52cc2`. Parent task text
      (`KVU-19b-rework-c2`) is recoverable with `git show 465954bc0~1:handoffs/active/kv-unified-stack-rollout.md`.
      Define-or-delete outcome: if nobody triages the two calibration FAILs, record 'commit 2 dropped' here and in
      manifest V11-085 and delete this id from the RTG-57 row at the next index pass.
  - [ ] **CPU-FA-VKQ-2 — decode A/B of the fix on a CPU role at production threads.** (filed 2026-10-04, workspace-ec)
    The harness shows FA-op parity; serving decode is not yet measured. `llama-bench` tg at depth (e.g. 16k and 64k,
    F16 KV) fix vs `GGML_FA_VKQ_F16=1` in one binary, alternating, under `region-lock run --role bench`, n ≥ 5 per arm.
    Done when the decode delta is recorded with its noise floor; it gates CPU-FA-VKQ-1's promotion, not its fold.
    - *(2026-10-04 PM, workspace-ec.)* PENDING: the end-to-end bench of hybrid v2 is running; no result yet.
    - *(2026-10-20 restore; manifest V11-086.)* The register-resident arm `GGML_FA_VKQ_REG=1` (`5bde1b83d`) was
      local-only at the time (whether `13bdbdc4d`, the branch tip now on `fork`, contains it is unverified). The
      champion port carries the fix without the opt-in arms. Define-or-delete: run the A/B (including the `VKQ_REG`
      arm, if it is to be considered for v11) or record 'excluded, not benched' in V11-086 and delete this id from the
      RTG-57 row.

- [x] **KVU-RESTORE-1 - audit and restore the task bodies deleted from this handoff by commit `465954bc0` (2026-10-07).** That commit is titled as adding the HYBRID-PREFIX-REUSE task but changed this file 12 insertions / 892 deletions (1234 -> 407 lines), about 50 task bodies (KVU-15..KVU-20 incl. KVU-16a..i and KVU-19a/b, CPU-FA-VKQ-0..4, V11-FA-*), which looks like an overwrite from a stale copy, not a deliberate compaction. The RTG-57 ids were restored under 'C2' on 2026-10-21; recover the rest from `git show 465954bc0~1:handoffs/active/kv-unified-stack-rollout.md` (sibling lineage: `06ce3ce14`, `a3f9206d9`), sort each into restore-as-open, already-done (tick with the original date) or superseded (archive to `handoffs/archived/`), and record the outcome. Done when no task id cited by an index row, manifest row or another handoff is undefined. (filed 2026-10-21 by the 3c4ca599 wrap-up, derived from the restoration of the RTG-57 ids)
  - 2026-10-21 (handoff-guard): warn-only guard installed against this failure class, `scripts/hooks/handoff_mass_deletion_warn.py` at `df88e40bc` on main (warns on a commit deleting >30% and >=40 lines of a `handoffs/active/*.md`; always exits 0).
  - *(2026-10-21, noninf-ak; box left open for the owner's sort pass.)* Restored as written (all from `465954bc0^`, original tick states): KVU-15, 15a-d, KVU-16 with 16a-i (16g-1/2 stay in C2), KVU-17, KVU-18, KVU-19 with 19a/19a-1/19a-2/19b/19b-1/19b-gap/19b-fold-c1/19b-fold-c1-receipt/19b-rework-c2 (fold-c1-p3 and rework-c2-cal stay in C2), KVU-19c, KVU-20, CPU-FA-VKQ-0/1/3/4, KVU-1b's 2026-10-03 SUPERSEDED note, KVU-1d's 2026-10-03 note, and the lost sections (D, E, Not filed here). Not restored: the old KVU-21 (#29510 A/B arm; id now taken by the agent-resume probe) which still needs a new id if wanted, from `git show 465954bc0^:handoffs/active/kv-unified-stack-rollout.md` lines 885-890. Sorting each restored item into open / already-done / superseded is still owed (the loss was a stale-base overwrite, not a deliberate drop; no restored item has a known deliberate removal).
  - *(2026-10-24, batch-a audit.)* Audit complete: all 87 ids from `465954bc0~1` are defined in this file (0 undefined; a wider scan of every KVU-/CPU-FA-VKQ-/V11-FA-/HYBRID-PREFIX-REUSE id cited in handoffs/active, blocked, completed, docs/design and kernel-manifests found 0 cited-but-undefined ids); the old KVU-21 is KVU-22 (already restored 2026-10-21), and the two stale "not restored" statements (the line-86 comment; line ~966 cross-reference) are corrected. The 2026-10-21 triage notes already sorted every still-open item (open / superseded); ticked ids kept their original dates. Outstanding relative to the done-when: none. (The sub-bullet at the old line ~1168 saying "Not restored ... still needs a new id" is superseded by this one.)

### D — measurement follow-ups
- [x] **KVU-18 (intake P3) — unified-KV decode cost on :8083's shape. Running in the 2026-10-03 INF-80 X0
  window** (`/mnt/raid0/llm/tmp/x0-27b-quants/PLAN.md`). Measure one slot's decode and verify tok/s at a fixed
  context while 0, 1 and 3 other slots hold parked long contexts, unified vs split, same binary. Include a cell
  near the F12 range: 50–150k own context, 15–60k neighbours. The source reports -6.6% S_TG on gfx1201 and
  "a 15.6k conversation with three others parked generates at the speed of a 62k one" on V100
  (`intake-1849#02`). Those are other GPUs and are not MI210 expectations. The loss, if any, is independent of
  drafter acceptance, so it must be measured before 25–30 tok/s agentic decode is blamed on DFlash2 (UFH14-A2
  in [`agentic-serving-harness-fixes.md`](agentic-serving-harness-fixes.md)). A loss of 5% or more triggers
  KVU-19. Carry the belief-kernel write-side hook from the first cell.
  - ✅ 2026-10-03 — **both triggers MET.** Report `/mnt/raid0/llm/tmp/x0-27b-quants/results/p3/report.md`; native records `a1.json`, `a0.json`, `b.json`,
    `p3_result.json`. MI210, v10 `ffc1bac82` kernel store, Qwen3.8-27B Q8_0 + DFlash2, :8083 production argv (pool 393216).
    - *A1, mechanism* (`--no-cache-idle-slots`, so parked neighbours stay resident): slot 0 holds P = 57,082 tokens and
      decodes 512 tokens; neighbours are one ~99.4k prefill plus two slot restores of it. No-draft decode (isolates
      attention): base 20.39 tok/s → **−32.6% / −49.5% / −59.5%** with 1 / 2 / 3 neighbours; drafted 36.28 tok/s →
      −29.6% / −47.2% / −57.6%. Acceptance unchanged (0.393–0.397). ABA drift −0.61% (L0 before vs after). Zero
      slot-failure, purge or restore-failure log lines. Nominal fill at L3 ≈ 57k + 3 × 99.4k ≈ 355k (0.90 of the pool).
    - *Caveat on the fill figure:* `/slots` reported only 156,971 resident tokens (0.399) at L1–L3, because the two
      restored slots never show `n_tokens` there; the restore replies report 99,378 tokens each, and the monotone L1→L3
      loss says the restored cells are attended. The ≥300k condition rests on the restore records, not on `/slots`.
    - *A0, production flags* (`cache_idle_slots` default on): **inconclusive** — the neighbour slot held 0 tokens before
      the probe task, so the "new task purges an idle neighbour" path was never exercised. Not re-filed as a task: the
      production default parks neighbours in RAM, and A1 already answers the decode-cost question the triggers ask.
    - *B, `llama-batched-bench`* (no drafter, pl 4, 4 × 16k, n_kv 65,792): kvu vs no-kvu S_TG 47.17 vs 55.64 t/s
      (**−15.2%**), S_PP 587.4 vs 823.3 t/s (**−28.6%**).
    - Consequences: KVU-19 is triggered (≥5%). KVU-16d's ≥15%-at-≥300k condition is met — workspace-ec is preparing the
      split-per-slot stack-change package there (their item). Belief-kernel wiring: VB-KVU-P3 in
      [`vidya-belief-substrate-program.md`](vidya-belief-substrate-program.md).
    - *(Annotation, workspace-ec, 2026-10-03.)* The operator decided KVU-16d as keep shared 393k, so no split package
      is being prepared. The skip is implemented directly as KVU-19a. A0 being inconclusive leaves the production
      idle-purge claim a code read (see the KVU-16b correction).
- [x] **KVU-8 — confirm the throughput verdict with fixed-length or multi-wave generation.** ✅ 2026-09-24 —
  confirmed, with one named substitution. (1) 35B-A3B, both arms, fixed-length L 2048 cells: unified within 2% of
  split in all 4 (per-request −0.6..−1.7%, aggregate −0.7..−1.1%); at 8k/32k the per-request spread is −5.3..+5.6%
  with no consistent sign because the arms' completions differ even at np 1. (2) 27B L 2048 cells, where every
  request in both arms ran to the cap: unified aggregate +5.1% at np 4. (3) M-4 (KVU-1e): the live np4 kvu shape
  at fixed length, 2 waves, gives 95.3 / 93.1 tok/s aggregate at concurrency 4, in line with the study's split
  np4 cells (92.9–102.0). So the single-wave −8% / −16% "aggregate loss" was the answer-length artifact. The
  substitution: no fixed-length **split** arm was re-run on the 27B; the claim rests on (1)–(3), n ≤ 2 per cell.
  Original task: Every cell is n=1, and
  the np4 aggregate gap tracks divergent completions. Rerun the np 2/4 cells with fixed-length generation
  (`ignore_eos` + `n_predict`) or at least 3 waves, both arms on the same binary. Carry the write-side hook
  (VB-KVU-1) from the first run.
- [x] **KVU-9 — finish, commit and read the Qwen3.6-35B-A3B-MTP Q8_0 GPU matrix.** ✅ 2026-09-24 — 24 cells,
  0 errors, np 8 fits at every L (44–45 GiB at 32k); committed research `07060eaa` (README §7, SHA256SUMS). Read
  in KVU-8. :8083 and :8086 were restored (18:30Z) and :8083 then came up on the OP-54 shape. The 35B ran at
  depth 4. Original task: Research
  `artifacts/np_context_kvu_study_20260924/q36_35b_a3b_q8_h/` was running from ~17:12Z with driver pid 1224153.
  - After the driver exits: verify it, add the run to the study README and SHA256SUMS, and commit it to research
    main.
  - Then restore :8083 and :8086 (`orchestrator_stack.py start --only …`; the owning session does this).
- [ ] **KVU-10 — roll `-kvu` to other roles, in the inventory's order.**
  - Embedders first (:8090–8095). Per-slot context is 256, below bge-large's 512 window, and every launch WARNs.
    The alternative is `-c 2048 -np 4`.
  - :8070 only if long jobs are routed there.
  - :8086 only if its `-np` rises.
  - Never :8080, :8180 or :8074 (`-np 1`, nothing to gain).
- [ ] **KVU-12 — np × ctx on CPU (TB-6 successor, Flash-Next) only if needed.** The operator skipped C2 at 17:25Z
  because the GPU matrix showed no unified-KV throughput cost. Reopen only if a CPU role shows qualitatively
  different relative behaviour.
  - **Reopened 2026-10-20 (operator):** measure the CPU concurrency x context tradeoffs before any frontdoor
    `--kv-unified` stack change, and reuse the matrix for the other models in the stack. Prompted by a vLLM
    deployment of the same 35B-A3B (NVFP4) that serves 8 x 64K from one shared pool, while :8070 caps each request at
    65,536 (`-np 4 -c 262144`, split KV). Matrix: KV {split, unified 512K/1M} x np {1,2,4,8} x L {8k..128k} x prompts
    {independent, shared-prefix}, fixed-length generation, >=3 waves, one deliberate pool-full cell. Spec and driver:
    `epyc-inference-research/artifacts/np_context_kvu_cpu_study_20261020/`. The timing half needs an exclusive
    full-host window.
  - *(2026-10-21.)* Tier-0 window W2 (00:30–04:45Z; epyc-inference-research `artifacts/np_context_kvu_cpu_study_20261020/w2_20261021/` (READOUT.md, capture rows, SHA256SUMS); v10 sha 4483bcfc, Qwen3.6-35B-A3B MTP on, one launch per cell): split np4 L64k decode sum 18.67 / 18.50 tok/s (ABA spread 0.9%, n=2 launches, higher=better), unified np4 L64k 18.22 (−2.0%), prefill −3.0%, TTFT +1.0% (lower=better). NOT like-for-like: the split arm lost its 4th stream to HTTP 400 context-exceeded (65.5k-token turn > 65,536 slot) in every decode wave (3 vs 4 streams), and cache-idle-slots was on for split, off for unified. Unified np8: L32k 26.71, L64k 10.18 tok/s sum (L64k at ~99% pool occupancy; unexplained 2.6× drop). Decision rule undecidable. s4 (np8 P=1M L128k) and the bank block SKIPPED for time (cells ran 1.8× estimate).
  - [ ] **KVU-12.4 — Tier-0 np4 L64k ABA redo with equal streams.** Size the depth-mode document so wave-1 suffix turns fit the 65,536 slot, run --no-cache-idle-slots on both arms, run the 32k anchor at start, middle and end for a floor with its unit (n ≥ 24 where it gates), and predeclare the unified-vs-split threshold in the PLAN before the window. Exclusive window, est ~7,800 s.
    - *(2026-10-21, workspace-f8.)* Prep done and pushed (research `2629df4ca`): slot-fit budget with fail-loud refusal (`REFUSED_OVERSIZE`, exit 3/5), equal-argv ABA guard (`--no-cache-idle-slots` on both arms, ledger-checked, exit 4), anchors at start/mid/end (`t8short`, floor with its unit), verdict script, and the PLAN §10 rule RATIFIED by the KVU-12 owner (operator may override before the window). Launcher `/mnt/raid0/llm/tmp/kvu12-redo-20261021/window.sh`: quiet part (ABA block + np8 pair) under nested gpu-quiet exclusive, then GPU_ALLOWED_FROM, then the GPU-allowed part (s4, bank) with per-step GPU-state sampling. Scheduled D4 19:10Z via d3-launch.sh (driver pinned to a detached checkout of `2629df4ca`).
    - *(2026-10-22, workspace-f8; ABA block in the quiet part, 19:10Z start, all steps rc 0, GPU idle (`gpu_busy_frac` 0.0); verdict `/mnt/raid0/llm/tmp/kvu12-redo-20261021/out/k4_verdict.json`.)* **np4 L64k verdict: NO_DIFFERENCE (PROPOSED-until-ratified; `proposed_by` workspace-f8, not ratified).** Unified vs the mean of the two split arms: decode_tps_sum -22.78%, decode_tps per stream -24.33%, TTFT +0.79%. Anchor floor (percent of the anchor-cell median; unit = anchor launch, n = 3 launches at start/mid/end): 12.48% / 11.93% / 0.51%; predeclared threshold 2x floor = 24.96% / 23.86% / 3.78%; split ABA spread 2.6% (sum), 1.89% (stream, TTFT). The gaps sit inside the thresholds, so by the predeclared rule: no difference. **Weak**: the anchor floor is large (12%), so unified looks about 23% slower on decode but within noise; this is not evidence that they are equal. Disturbance: workspace-58's numpy burst (~20:25-20:55Z, no region claim) overlapped `k4_B_unified_np4_L64k` (19:59-~20:43Z), `k4_anchor_mid` and the start of `k4_A2_split_np4_L64k`, per `QUIET_PART_DISTURBANCES.md`; expected below the step noise but the unified step is the one affected.
  - [ ] **KVU-12.4 re-run decision — one more ABA with a tighter anchor floor, or accept NO_DIFFERENCE.** Right-sized: accept NO_DIFFERENCE and record the ~23% unified-decode gap as inside a 12% floor, unless the unified decode gap matters to a decision. If it does, run ONE ABA (split, unified, split) at np4 L64k with the anchor floor brought under about 5% (find why the 32k anchor varies 12% across launches first; more anchor launches, n >= 6) and the disturbance file empty for the unified step. Exclusive window about 2.2 h. The owner ratifies or rejects the PROPOSED verdict file first.
  - [x] **KVU-12.5 — Tier-0 s4 re-run: unified np8 pool 1,048,576 L128k depth live** — DECLINED 2026-10-22 (f8; see the decline note below; the np8 relative claim moves to the `KVU-12.5 re-run` item, part (a)). (skipped 2026-10-21 for time; est 10,639 s at the calibrated 1.795 factor), then the S2/S3 bank block (MTP-off np8 L64k control, occupancy, pool-full) and a split np8 L64k partner so np8 gets a relative claim. Next exclusive full-host window.
    - *(2026-10-22, workspace-f8; redo ran 19:10Z-05:19Z, ended rc 125 = the s4 cap; `/mnt/raid0/llm/tmp/kvu12-redo-20261021/`.)* **s4 (unified np8 pool 1,048,576, L128k, depth live): rc 125, hit its 12,000 s cap (12,004 s), no result.** Bank block: `k6_bank_build_unified` done (4,944 s) and `k6_bank_mtpoff_np8_L64k` done (679 s); `k6_bank_np8_pool524288_and_poolfull` SKIPPED for time (needed 10,844 s, 4,227 s left). **np8 L64k unified-vs-split pair: CONFOUNDED, no verdict.** The unified cell (5,526 s) ran with `gpu_busy_frac` 0.4654 and a foreign KFD process (early GPU release, foreign GPU jobs); the split cell (5,090 s) ran at 0.0. Unequal GPU state across the pair, so the gap cannot be attributed to unified vs split. Box stays open.
  - [ ] **KVU-12.5 re-run — np8 L64k pair on a GPU-idle host (parts (b) s4 and (c) pool-full DECLINED 2026-10-22, see note).** (a) np8 L64k unified and split back to back under gpu-quiet, `gpu_busy_frac` 0.0 and zero foreign KFD pids on both (sampler as in the redo); (b) s4 with a cap of at least 14,000 s (the redo ran 12,004 s without finishing, so the 1.795 factor underestimated it) or drop s4 if the np8 pair is enough for the decision; (c) pool524288/poolfull bank cell (~10,844 s). Needed only if the np8 claim is still wanted; KVU-12.6 (the L32k -> L64k collapse) is the more useful np8 question.
    - [x] **KVU-12.5 np8 A/B pair** (operator decision 2026-10-25 via decision tool): file a clean np8 L64k unified vs split pair on one CPU quarter (~1-2 h), GPU idle on both arms; parts (b) and (c) stay declined. Launcher prepared (not armed): `/mnt/raid0/llm/tmp/cal-1025/kvu12-5-np8/`. ✅ 2026-10-27 [belief: cc]
      - *(2026-10-27, workspace-58 results harvest)* Verdict SPLIT_BETTER (PROPOSED until KVU-12 owner ratifies). Medians unified vs split: decode sum 10.49 vs 20.63 tok/s (-49.2%, threshold 25.0%), per stream 1.41 vs 2.54 (-44.5%, threshold 23.9%), TTFT +2.2% (threshold 3%); GPU idle both arms (busy 0.0, 0 foreign KFD); q3, -t 24, not comparable to the 10-21 redo. Artifact `/mnt/raid0/llm/tmp/cal-1025/kvu12-5-np8/VERDICT.json`.
      - [ ] **KVU-12.5 ratify — KVU-12 owner ratifies or rejects the PROPOSED SPLIT_BETTER verdict; then close the KVU-12.5 re-run parent.**
    - *(2026-10-21, workspace-f8.)* Queued in the same window after the quiet/GPU boundary (s4 cap 12,000 s, then the bank block); the np8 L64k unified+split pair sits in the quiet part under the shared `np8L64k` argv ledger key. Bank block likely skipped on the time budget (31,418 s needed before it vs a ~34,000 s window).
  - *(2026-10-22, workspace-f8; EXPLICIT DECLINE + D4 overrun root cause.)* **Declined: the s4 re-run (unified np8 pool 1,048,576 L128k) and the 128k bank + poolfull cells (parts (b) and (c) above, and the original KVU-12.5 box).** Not filed because: these are CPU timing of the 35B frontdoor, which is moving to GPU, so no live decision needs them (the np8 L64k pair (a) stays open only if the np8 claim is still wanted). Root cause of the D4 overrun (workspace-58, `/mnt/raid0/llm/tmp/d4-why-20261022/REPORT.md`): the driver's estimate model was wrong (128k prefill ~65 tok/s measured vs 195 modelled; shared-batch decode 0.08-0.12 tok/s per stream), so k5_s4's 12,000 s cap was unreachable; GPU contention was REFUTED as the cause. The estimate model is fixed on research `f8/kvu12-arms` `8e532d23f` and re-costed: KVU-12.1 8k ~2.1 h on one quarter / 0.6 h full host; the 32k pair +3.5 h / 0.9 h.
  - [ ] **KVU-12.6 — explain the np8 L64k decode collapse** (26.71 → 10.18 tok/s sum, L32k → L64k, pool ~99% occupied): separate pool occupancy from np/L with an np8 L48k cell and an np4 equal-token cell, and account for per-stream resume-depth differences, before any np8 decode figure is quoted.
- [ ] **KVU-12.1 — checkpoint-policy arms in the CPU np x ctx matrix.** On the frontdoor Qwen3.6-35B-A3B and the 27B add four hybrid-checkpoint arms to the KVU-12 matrix: dense (today: --checkpoint-min-step spacing plus n-4 / n-4-n_ubatch; record the positions actually materialized, since a chunk spanning several cadence boundaries materializes only its end), tail plus junction only (<=2 recurrent states per request via checkpoint_at on the fork build), fixed-interval with a cap on checkpoints per request, and a coarser grid whose resume is at most I tokens earlier than dense. Record per arm and per context length L: retained checkpoint count per sequence, bytes per checkpoint, resume prompt_n and cache_n, TTFT, and hit length against checkpoint spacing; baseline is the dense count at the current granularity; cite no external figure. Output sizes --ctx-checkpoints and --checkpoint-min-step and answers HYBRID-PREFIX-REUSE (b). Counts and prompt_n are correctness-class (build-role claim, no quiet host); TTFT and throughput wait for the scheduled exclusive window. Controls: frozen manifest = corpus manifest + bank_manifest sha256 + binary sha256; baseline = the dense arm on the same binary; raw per-request rows through the VB-KVU-CPU emitter; holdout = stride and cap chosen at L=32k and evaluated at 64k and 128k; denominator = every request including pool-full and errors; predeclared rule = an alternate arm replaces dense only if its resume prompt_n is within the dense arm's wave-to-wave spread at every L and its checkpoint bytes per sequence are lower at every L, else dense stays.
  - *(2026-10-21, backlog audit.)* RIGHT-SIZED PLAN (audit REPORT §0.6, §1 KVU-12.1, §2 S2; research branch `f8/kvu12-arms`, `artifacts/np_context_kvu_cpu_study_20261020/PLAN.md` §11): 6 arms x 2 waves at 8k on the Qwen3.6-35B-A3B only, substrate "either" (counts are substrate-independent; place on whichever of the idle night MI210 or a CPU quarter frees first), to validate the simulator (prompt_n, cache_n, bytes and retained-checkpoint counts are deterministic functions of checkpoint placement; PLAN §11.1 records the simulator-vs-log agreement); the arm decision at 32k / 64k / 128k is made by the simulator; ONE 32k holdout pair (selected arm + dense, 2 waves, ~2.5 h). No 128k cells (2.3 h/cell, adds only bytes scaling = arithmetic) and no 27B (same server code). ~1.7 h + ~2.5 h instead of ~20 Q-h. The holdout wording above ("stride and cap chosen at L=32k, evaluated at 64k and 128k") is superseded by this plan.
  - *(2026-10-22, workspace-f8; run 09:10-12:24Z on one quarter (48-71,144-167, `-t 24`), fork binary sha256 `1442c95d…`, outputs `/mnt/raid0/llm/tmp/kvu121-arms/out/{cells,requests}.jsonl` + `launch.log`; `decide` output, read-only, `/mnt/raid0/llm/tmp/f8-kvu121-kpf18-verdicts/kvu121_decide.json`, selection `{"q36_35b": null}`.)* **Rule verdict: DENSE_STAYS for every alternate arm (not ticked, see the gaps).** Phase 1: 12/12 8k cells OK. Phase 2: 32k dense and tail_junction, w0 OK, **both w1 cells ERRORS**.
    - **8k does not discriminate.** The 8k conversation (~8.2k tokens) is shorter than every min-step of 8k or more, so dense, coarse, fixed_s8k_c8 and fixed_s16k_c8 place the same checkpoints and use the same bytes (296 / 231 MiB for w0 / w1). They FAIL rule (b), bytes lower, by tying. fixed_s4k_c8 adds one checkpoint: +27.8% bytes (fail), and halves edit_back_4096 prompt_n (5,176 vs 10,331). tail_junction is byte-identical to dense at 8k.
    - **tail_junction fails on substance at 32k, not only by the error clause.** On the clean w0 pair it uses 40% fewer bytes (460 vs 763 MiB, 4 vs 7 states; `meets_le2_states=false` as expected without P-B). But edit_back_8192 and edit_back_16384 fully re-prefill: prompt_n 37,976 / 37,989 vs dense 9,200 / 18,766, TTFT 620 / 651 s vs 291 / 520 s, indicative. The dense wave spread on those probes is 276 / 968 tokens. Junction-only placement loses every resume deeper than the last user message.
    - **Simulator NOT validated: `sim_matches_log=false` in 16/16 cells (12/12 at 8k), and the count agrees in only 8/16.** So the phase-2 gate was not met. The launcher started phase 2 on phase-1 rc 0 alone and never checked agreement. The causes are in the driver (`kvu_ckpt_arms.py` `run_ckpt_cell`/`simulate_prefill`):
      - (a) User starts are estimated from per-message content tokens plus an evenly spread template overhead, never from rendered offsets. They drift with depth: sim 31,064 vs log 28,930 at 32k.
      - (b) `0 < x` drops the first user start. The server's empty-set checkpoint sits at 154 (template header), so the simulator substitutes a later start (2,851).
      - (c) The n_ubatch checkpoint is 4 tokens off: log `n - n_ubatch`, sim `n - 4 - n_ubatch`.
      - (d) **Wave-1 artifact:** w1 runs on the server w0 warmed. The w0 checkpoint at 154 persists (w1 cold_build restores it, `cache_n` 154), so the server does not create the empty-set checkpoint. The per-cell `CkptSet` never sees the inherited checkpoint, so every w1 row under-reports count by 1 and bytes by ~63 MiB. The "dense wave-to-wave spread" also mixes cold and warm servers: 8,137 tokens on 8k edit_back_2048, which makes rule (a) nearly vacuous at 8k.
      - The tails (n-4, last user) match within 1-4 tokens.
    - **ERRORS root cause (both 32k w1 cells): a driver bug that overflows the context, not a server or simulator defect.** `fit_conversation` scales only the final user message, with turn texts cut at a fixed 4.0 chars/token. It silently returns the closest probe when it cannot reach the 32,688-token target: w0 got 35,863 tokens (+9.7%), w1 got 38,868 (+18.9%, denser corpus slice). `extend_1` then adds ~2,100 tokens, giving 40,965 > `-c 40960` (`HEADROOM_TOK` 8192), so the server returns HTTP 400 "exceeds the available context size" (`requests.jsonl`, probe extend_1, both w1 cells).
      - Knock-on: `cur` does not advance, so the edits are cut against the un-extended conversation. On tail_junction w1 every edit lands before the junction at 36,820 and fully re-prefills ~38.7k tokens (TTFT 807-834 s × 3). That explains the 3,233 s wall (actual/model 1.066).
      - dense w1 otherwise resumed normally (29,418 / 21,110).
  - [x] **KVU-12.1a — driver fixes before any further KVU-12.1 cell** (research `f8/kvu12-arms`, `kvu_ckpt_arms.py` + launcher; no compute to write, tests with no server): ✅ 2026-10-22
    - (1) `fit_conversation` fails loud (a REFUSED_FIT row, counted) when the best probe is outside tol. Calibrate chars/token from the first render and scale `n_pairs`/turn sizes, not only the last message.
    - (2) Size `-c` from the fitted `n_total` + extend pair + slack, or refuse the cell.
    - (3) Feed `simulate_prefill` the rendered token offset of every message (prefix renders through `/apply-template` + `/tokenize`) and include the first user start. Model the n_ubatch checkpoint at `n - n_ubatch`.
    - (4) Give each wave a fresh server (or `/slots` erase plus a checkpoint read-back), so w1 is not a warm-server artifact and the count/bytes include every retained checkpoint.
    - (5) The launcher starts phase 2 only if `sim_matches_log` holds on every phase-1 cell.
    - Re-judge the stored 8k rows offline with the fixed simulator: positions after fix (3) vs the logged positions.
    - Done when the tests cover (1)-(5) and the offline re-check shows exact position, count and byte agreement on the w0 8k cells.
    - *(2026-10-22, workspace-f8.)* ✅ 2026-10-22 Done on research `f8/kvu121a-driver-20261022` @ `f7b647705` (not pushed): (1) `fit_conversation` scales every turn and raises `REFUSED_FIT` (counted, parked) instead of returning an overshoot; (2) `-c` = the cell's own L + `HEADROOM_TOK`, and a cell raises `REFUSED_CTX` before any request when fitted + extend + edit tag + n_predict exceed it; (3) exact `ServerSim` (server restore/invalidate/chunking/eviction rules) on the rendered token ids, user starts = the server's delimiter positions (first user start 154 included), tail checkpoint at `n - min(n_batch, 4 + n_ubatch)`; every request records prompt_n/cache_n/count/bytes/positions agreement; (4) one fresh server per ckpt cell, retained set replayed from the whole server log; (5) `run` refuses (rc 8, `REFUSED_SIM_GATE`, reasons printed) while any earlier ckpt cell in `--out` lacks exact agreement; no launcher change needed. Offline re-check: `kvu121_offline_offsets.py` rebuilt the recorded conversations without a server (corpus sha256 = the run's, every offline prompt length = the logged one) -> `driver/fixtures/kvu121_recorded_20261022/`. **Wave 0: 0/8 cells agreed before; 8/8 cells, 34/34 requests exact after** (prompt_n, cache_n, positions, count, bytes). Wave 1 still disagrees, only by the checkpoint at 154 inherited from w0 (fix 4's cause); 32k w1 also has the failed extend_1. Tests: `test_kvu_ckpt_arms.py` 86 passed (22 new).
  - [x] **KVU-12.1b — 32k holdout: dense vs coarse, 2 waves each, fresh server per wave, after KVU-12.1a.** coarse (`--checkpoint-min-step 16384`) is the only remaining arm that places checkpoints differently from dense at 32k:
    - *(2026-10-22, workspace-f8.)* launcher armed 2026-10-22, FILLERS row kvu121b-32k-dense-vs-coarse; rule in /mnt/raid0/llm/tmp/f8-launchers-20261022/kvu121b-32k-dense-vs-coarse/job.sh header. Not run yet, nothing ticked.
    - fixed_s8k_c8 = dense with a cap that 7 states never reach;
    - fixed_s16k_c8 = coarse;
    - fixed_s4k_c8 and tail_junction already fail.
    - Spec: Qwen3.6-35B-A3B-MTP Q8_0 on the same fork binary, one CPU quarter (`-t 24`, build-role claim, correctness class, no quiet host). RAM ~45 GiB (37.8 GB mlocked weights, 40,960-ctx q8 KV, ≤32 checkpoints × ~110 MiB). Wall ≈ 4 cells × ~1,900 s + launches ≈ 2.2 h.
    - Rule unchanged (PLAN §11.4).
    - Prediction, stated before the run: coarse keeps ~4 states but restores near ~17k on edit_back_8192, so prompt_n ≈ 21k vs dense 9.2k. It fails (a), and DENSE_STAYS holds.
    - If the owner accepts the prediction, close this box as declined with that reason. Then KVU-12.1 closes on DENSE_STAYS, and HYBRID-PREFIX-REUSE (b) keeps `--ctx-checkpoints 32 --checkpoint-min-step 8192`.
    - *(2026-10-23, workspace-f8; RAN, the prediction was WRONG.)* ✅ 2026-10-23 **Verdict REPLACES_DENSE at 32k, against the stated prediction DENSE_STAYS.** Evidence: `/mnt/raid0/llm/tmp/f8-launchers-20261022/kvu121b-32k-dense-vs-coarse/VERDICT.json` (+ `RUN_RECORD.json`, `PASSED`). Rule = `decide_121` (PLAN section 11.4) over the 4 32k rows per arm; validity = exact sim-vs-log agreement on every ckpt cell (met, `sim_problems: []`).
      - Bytes: coarse retains 534.05 MiB vs dense 735.05 MiB per sequence = **-27.34%**, junction materialised.
      - prompt_n (arm median vs dense median, dense wave spread): edit_back_2048 1866.5 vs 1866.5 (0, spread 21); extend_1 2420.5 vs 2420.5 (0, spread 107); edit_back_8192 17300.5 vs 11392.0 (**gap +5908.5**, spread 6644); edit_back_16384 17314.5 vs 21284.5 (gap -3970, spread 6675). All four pass rule (a).
      - **Caveat, do not oversell:** the edit_back_8192 gap is positive and large (+5.9k tokens of extra re-prefill, about 52% more than dense's median there). It passes only because the dense wave-to-wave spread on that probe (6,644) is itself huge. The prediction (coarse restores near ~17k) was right about the mechanism, wrong about the verdict, because the rule is spread-relative. A tighter spread (more waves) could flip it; the rule as predeclared is what decides. Coarse also GAINS 3,970 tokens on edit_back_16384.
      - **Scope of the verdict:** the 32k holdout only. At 8k coarse ties dense on checkpoints and bytes (the 8k conversation is shorter than the 16k step), so rule (b) "bytes lower at EVERY L" is not met at 8k by the strict reading; 64k/128k are unmeasured for coarse-vs-dense (128k holdout was declined above). So KVU-12.1 does NOT close on DENSE_STAYS anymore (the earlier 2026-10-22 note "DENSE_STAYS for every alternate arm" is superseded for `coarse`): the 32k result re-opens HYBRID-PREFIX-REUSE (b) below, which carries the remaining confirmation steps.
- [x] **KVU-12.2 — MTP-on context bank: port #30574, gate it, fold it into the champion if it passes.** v10 slot save/restore writes ctx_tgt only (the study measured restored acceptance below 0.9x live, PLAN section 9 gate (b)), so MTP-on bank cells stay labelled "restored-draft" and no MTP-on decode tok/s from the bank is quoted as production-representative. Operator 2026-10-20: port upstream #30574 now onto `experimental/slotdraft-30574-20261020` from the champion tip (porting in progress), run gate (a) and gate (b) on that build against the unported champion as control with the study's predeclared rule (restored acceptance >= 0.9x live and restored decode >= 0.95x live, both layouts, both suffixes); if it passes, fold #30574 into the champion through the fold-ledger route (FOLD.md + trial merge onto the champion tip, recorded in autokernel-champion-aggregate.md) and run the MTP-on bank cells on the champion+#30574 binary, labelled with that binary; v10-binary MTP-on cells stay labelled restored-draft; a bank written by a build carrying #26640 is not restorable on v10, so rebuild banks per binary. Correctness class under region-lock; no external figure.
  - *(2026-10-20.)* Port + gate + fold done: `experimental/slotdraft-30574-20261020` (#26004 + #30574 ports) restored/live MTP acceptance 0.98–1.02 and decode 0.99–1.02 on both layouts vs the unported champion's 0.53–0.71 / 0.71–0.85 (`/mnt/raid0/llm/tmp/slotdraft-30574/REPORT.md`); folded as champion `dd3d9721c` (ledger in `autokernel-champion-aggregate.md`). Still open: the MTP-on bank cells on the `dd3d9721c` CPU image. Tonight's Tier-0 window (00:30–06:30Z, `/mnt/raid0/llm/tmp/overnight-20261020/`) runs the v10 production binary with MTP-on cells live.
  - *(2026-10-22, workspace-f8.)* ✅ 2026-10-22 MTP-on bank cells COMPLETE, PASSED (`/mnt/raid0/llm/tmp/f8-fillers-20261022/kvu122/VERDICT.json`, `RUN_RECORD.json`). Candidate = `cpu-20261020-dd3d9721c` (champion + #26004 + #30574, MTP drafter state banked with the slot): all 4 cells (split/unified x suffix A/B) pass, restored/live acceptance 0.98-1.02, decode 0.98-1.01, tokens identical. Control = unported champion image `cpu-20261006-4348de400` (no draft bank): all 4 fail, acceptance 0.53-0.71, decode 0.77-0.82, so the gate discriminates. MTP-on bank cells on that binary are production-representative for it; v10-binary MTP-on cells stay labelled restored-draft.
  - *Dormant (research intake 2026-10-20):* Marconi-style FLOP-aware checkpoint eviction (recency plus alpha times covered tokens; our snapshots are equal-size, junctions are pinned). Trigger: the KVU-12.1 arms show unpinned-checkpoint churn with misses on long prefixes.
- [ ] **HYBRID-PREFIX-REUSE — make multi-turn prefix caching actually hit on hybrid (GDN/recurrent) production models via a prefill-only boundary checkpoint.** (filed 2026-10-07) — Owner: workspace-ec.
  - Finding: on hybrid models llama-server reuses a prefix ONLY via context checkpoints, and v10 creates them only at n-4/n-16 of each request's prompt. So a follow-up request that diverges inside the previous prompt's tail forces a full re-prefill (observed: prompt_n = full, "forcing full prompt re-processing (hybrid/recurrent)").
  - Workaround PROVED on CPU, Qwen3.8-27B: a prefill-only request (n_predict 0) of the shared prefix ending at a turn boundary puts checkpoints at prefix-4/-16. Later questions re-decode only their tail (prompt_n 58 and 74 vs 3556), and slot save/restore plus extension gives prompt_n == the delta with byte-identical output. Evidence: `/mnt/raid0/llm/tmp/jetlong-gpu27b-20261006/SAVE_RESTORE_TEST.md` and `saverestore5/` (copy `SAVE_RESTORE_TEST.md` to `artifacts/hybrid-prefix-reuse-20261007/` and cite the copy).
  - Also note: champion commit `ef81196d5` adds user-message-start checkpoints, which may make this automatic.
  - Plan, as sub-bullets:
    (a) correctness on the production frontdoor :8070 recipe (Qwen3.6-35B-A3B): a multi-turn replay with and without a prefill-only boundary request, and also on the champion (`ef81196d5` user-message checkpoints), measuring prompt_n and cache hit rate per turn, plus greedy identity. This is CORRECTNESS work, under build-role quarter claims.
    (b) if (a) passes, choose the mechanism (orchestrator-side prefill-only boundary request vs the champion's server-side user-message checkpoints) and the `--ctx-checkpoints` / `--cache-ram` settings.
      - *(2026-10-22, workspace-f8; KVU-12.1 input to (b); SUPERSEDED 2026-10-23 by the KVU-12.1b result below for the coarse grid.)* The checkpoint-policy arms gave DENSE_STAYS: keep `--ctx-checkpoints 32 --checkpoint-min-step 8192`. Tail+junction-only fully re-prefills every resume deeper than the last user message (32k: 37,976 vs 9,200 tokens). Evidence is in the KVU-12.1 note above.
      - [ ] **HYBRID-PREFIX-REUSE (b) RE-OPENED (2026-10-23, workspace-f8): coarse (`--checkpoint-min-step 16384`) REPLACES_DENSE at 32k (KVU-12.1b: -27.3% checkpoint bytes, 534 vs 735 MiB/seq; prompt_n within the dense spread on every probe).** Next step, per PLAN section 11.4: run the unchanged holdout of dense vs `coarse` at 64k (and 128k only if the earlier decline of the 128k cells is lifted) on the same fork binary and quarter, with the same rule, fresh server per wave, using the KVU-12.1a driver (`kvu_ckpt_arms.py run --stages holdout`, which refuses without the sim gate); add waves so the dense spread is measured on the edit_back_8192-class probe rather than assumed, because the 32k pass rests on a 6,644-token dense spread against a +5,908-token coarse gap. Then set `--checkpoint-min-step` (16384 vs 8192) and `--ctx-checkpoints` for the :8070 recipe from the survivors, still subject to (a) (greedy identity and the champion's user-message checkpoints) and (c)/(d). Until then production keeps `--ctx-checkpoints 32 --checkpoint-min-step 8192`.
        - *(2026-10-24, workspace-f8 subagent; PREPARED, not run.)* Launcher `/mnt/raid0/llm/tmp/f8-launchers-20261024/hpr-b-64k-holdout/` (FILLERS row draft `FILLERS_ROW.md`, BACKLOG, block-correctness, one CPU quarter; DRY rc 0).
          - It uses the same driver pin `95550d294` and the KVU-12.1b fork binary as a byte-identical store copy `kernels/builds/cpu-20261021-80a09c6ad-p1r2-fork` (sha `1442c95d…`).
          - Phases: an 8k dense+coarse smoke, then the 64k holdout, dense vs coarse, 3 waves each, one fresh server per cell. The selection is `{q36_35b: null}` from the KVU-12.1b cells. 128k is not run.
          - Expected ~7.3 h, resumable per cell. Rule: decide_121 unchanged, over the 64k rows. `PREDECLARATION.md` sha256 `56649c03…`.
        - *(2026-10-24, workspace-f8.)* ARMED 09:06Z under the operator's pre-approval of the batch-E one-quarter CPU correctness launchers (pid 373947). Queued on q1/q2 from about 10:10Z, capped at 16:30Z. The box stays open.
        - *(2026-10-24 10:21Z, workspace-f8 subagent.)* The 09:26Z q1 grant ended with rc 6, "store staging failed: built with GNU 15.2.0…", before any load. The binary is fine. The cause is a bug in `stage_store_copy.sh`: it required `--version` to name the worktree HEAD `80a09c6ad`, but the binary stamps `dd5bb0d3b`, the commit it was built at, and the one commit after that touches only tests. The "GNU" text was the second line of a two-line message, cut off by job.sh's `tail -1`. Fixed in the launcher dir: the build-info commit must be HEAD, or an ancestor of HEAD with no source change in between. The check now also runs on the source binary, so DRY catches it, and every message is one line. Backup `.pre-verfix-20261024`, tests `test_stage_store_copy.sh` 14/14, note `AMENDMENT-stage-verfix-20261024.md`. The store copy is now staged (SHA256SUMS and linkage OK) and DRY is rc 0. PREDECLARATION and the binary sha are unchanged. The `--repeat` engine is still up and runs on the next grant. Box stays open.
        - *(2026-10-24, ws58 wrap-up.)* Run `/mnt/raid0/llm/tmp/f8-launchers-20261024/hpr-b-64k-holdout/` ended VERDICT.json `INVALID_SIM_DISAGREES` (PREDECLARATION sha256 `56649c03…`): one cell, q36_35b|dense|ckpt|64k|w0 extend_1, has prompt_n sim 2818 vs log 2799 and cache_n sim 65314 vs log 65333 (the server reused 19 more tokens than the simulator predicted). Predeclared outcome: no decision, never re-graded. The holdout box stays open. Codex diagnosis `/mnt/raid0/llm/tmp/codex-ni-20261024-scheduling/tasks-from-ws58/HPR-B-SIM-DISAGREE-1-REPORT.md`: strong but not proven explanation is that the simulator omits the retained generated suffix (19 = 4 checkpoint gap + 15 retained generation); token IDs were not captured.
        - *(2026-10-28, codex-ni-01a16d6b; fixture setup recovery.)* The previously reviewed test-only environment fix was recovered after the October 26 publication refused rc79 on unrelated KPF adapter drift. Absent `EPYC_HPR_RESEARCH_WT` skips the HPR fixture class; configured invalid/empty paths fail explicitly; valid pinned producer helpers still run all five tests. Fresh controls passed (5/5 configured helper tests, expected absent/invalid/empty outcomes, 8 adjacent pure units). Source SHA-256 `cc0878a68dd979baf9793e995f16cbbe91edade6e2cc09da5fe1c193321d4bfb`; details in `progress/2026-10/2026-10-28-hpr-env-recovery.md`. Source branch is the candidate for owner integration; native contract, holdout and parent gates remain open. [no-belief: test setup repair; no native parity finding]
        - [ ] **HPR-B-SIM-FIX-2 (filed 2026-10-24, ws58 wrap-up):** simulator models retained generation + driver captures prompt token IDs + unit test reproducing 2799/65333; then a NEW predeclared 64k holdout re-run (Codex task, deadline 10-25 08:00Z).
          - [x] **HPR prospective 64k diagnostic READY** ✅ 2026-10-28 — `hpr-fix2-prospective64k-20261028` passed the actual launcher smoke under q2/48–49: 75.610 s, 40 real requests over 60.531 s, result writer and captured cleanup verified. Smoke is non-admitted two-CPU/512-context; the full 24-CPU/64k six-cell work remains open, with no historical regrade or timing/adoption warrant. [Evidence and limitations](../../progress/2026-10/2026-10-28-hpr-meta-ready.md). [belief: cc]
          - [x] **HPR-RAW-R2-AUDIT — harvest completed raw capture, without a policy verdict.** ✅ 2026-10-28. The fresh six-cell 64k dense/coarse successor is complete: existing sealed `holdout_full.cell_problems` replayed cleanly on all six cells; 36/36 requests report HTTP 200, no errors and complete prefix captures; all 42 cell/request self-hashes match the producer's `row_hash`. Existing `witness_problems` replayed cleanly across 36 request windows / 127,870 in-window samples for recorded 24-47 affinity and pinned store-bin library parent. Native `RAW-OBSERVATION.json` remains `RAW_OBSERVATION_UNVERIFIED`, `native_contract=UNVERIFIED`, `policy_verdict=null`. Original INVALID_SIM_DISAGREES evidence and both contamination disclosures remain applicable; no timing grading or native parity verdict was produced. Evidence and remaining scope: [bounded audit](../../progress/2026-10/2026-10-28-hpr-raw-capture-audit.md). The native holdout and parent gates stay open. [belief: cc]
        - *(2026-10-27 12:30Z, ws58 results harvest; contamination note, run still in progress.)* The HPR-B 64k r2 run (grant `hpr-b-64k-raw-r2-20261027`, q1 = CPUs 24-47, window 10:10Z to 20:00Z) was not alone on its region. Refactor's bounded preflight checks (attempts 59-64, `launch-checker`/std-library/row-validator and bash parse only, no model/app/fulltests) ran on CPUs 24-25 between 10:14:18Z and 10:24:40Z; each admission helper REFUSED the q1 overlap but the outer shell continued (no `set -e`). One 0.2 s `gitnexus status` also ran around 10:4xZ (exact time not recorded). Source: `/mnt/raid0/llm/tmp/refactor-01a16fc3/compute-coordination-20261026/ADMISSION-DEVIATION-20261027-HPR.md`. Meaning: timing impact is NOT excluded and not measured; the analysis of r2 MUST flag every sample inside 10:14:18Z-10:24:40Z (and the gitnexus instant) as contended, and report the verdict with and without them. Next: analysis step reads the deviation file before grading. [no-belief: contamination disclosure, no measurement]
          - *(2026-10-26, ws58; note, not a tick.)* golden v3 (2026-10-26 03:30–05:41Z, q1): 24 fresh captures / 12 exact comparisons, 4 families × 3 probes × 2 endpoints, all control predicates PASS, 7626 DURING samples in 24-47; accepted ONLY as prospective instrument equivalence on the pinned experimental CPU model/settings; native contract UNVERIFIED; no regrade/perf claim; evidence research data/hpr/golden-v3-20261026/. HPR parent, the new predeclared 64k holdout and the native contract stay OPEN. [no-belief: instrument-equivalence control; reader projection per VB-KVU-HPR-PREFIX pending]
    (c) TIMING: TTFT and throughput A/B in a scheduled window.
    (d) stack-change package for :8070 (and :8083 if applicable).

### E — speech residency
- [x] **KVU-11a — commit the speech study's follow-up run.** ✅ 2026-09-24 — option C (`smtC`) committed in
  research `07060eaa` (README addendum, SHA256SUMS regenerated); the shared clone's untracked copies were moved
  aside and the clone fast-forwarded (it is at `6afc7eed`, ≥ `34373dd8`). Option C failed: TTS 20–37× slower than
  real time with the frontdoor generating. Original task: After 17:14Z the study kept writing to the shared
  research clone: an `smtC` SMT-sibling run, an edited `speech_cpu_bench.py`, and a grown
  `raw/whisper_bench_encoder_matrix.txt`. Once it finishes:
  - commit the delta onto research main (`artifacts/speech_cpu_realtime_20260924/`, SHA256SUMS regenerated);
  - update the README's option C;
  - after a checksum match, remove the shared clone's untracked copies, so DS41-C10a's fast-forward is not blocked.
- [x] **KVU-11 — decide where STT/TTS live** (OP-56). ✅ 2026-09-24 — operator: STT **and** TTS to CPU (STT
  24@0-23, TTS 16@24-39); applied with OP-54 (KVU-1). Voice turns route their reasoning step to
  architect_general (:8083), a requirement for the voice-pipeline handoff the operator is drafting. The
  follow-up measurement showed this layout collides with the CPU LLM roles (KVU-11b). Original options: Research `artifacts/speech_cpu_realtime_20260924/README.md`.
  - (A) Stay on GPU. Recommended: whisper costs ~2.2 GB VRAM, plus TTS when it runs.
  - (B) Give speech its own cores. Shrink the `-t 96` frontdoor and :8074 to free 24–40 physical cores. The
    frontdoor cost is unmeasured and needs a frontdoor relaunch.
  - (C) Run speech on SMT siblings 96–175. This was untested in the committed snapshot; an `smtC` run was in
    progress at 17:53Z (KVU-11a).
  - Either CPU option must use a measured core layout: whisper hangs on some layouts (e.g. 32@0-31). TTS also
    needs the `get_nprocs` shim to control its thread count.
  - Couples with OP-48 (capacity gate sees speech VRAM) and package N-5 (TTS does not fit next to kvu today).
  - The operator is drafting a separate conversation-stack handoff (STT → frontdoor → TTS). Do not file the
    omni/Moshi intake here.
- [x] **KVU-11b — CPU speech is not real time while a CPU LLM role generates: decided.** ✅ 2026-09-24
  **Operator decision 2026-09-24 ~20:00Z (first-hand to main-ak-seat): option D, no change to the layout.** The
  operator is drafting a larger STT/TTS integration plan that supersedes options A-C; the measurements below are its
  input, collected in [`docs/reference/speech/cpu-speech-contention-20260924.md`](../../docs/reference/speech/cpu-speech-contention-20260924.md).
  Do not re-propose partitioning or a throttle as standalone work.
  Measured 2026-09-24 19:19–19:43Z against the live layout (research
  `artifacts/speech_cpu_realtime_20260924/README.md` addendum 3, `6afc7eed`; harness `live_llm_contention.py`):
  - With :8074 or :8070 generating (`-t 96` on 0-95): STT RTF ≥ 58 (one 11 s clip took ~10.7 min), TTS first
    packet 13.4–13.6 s and then stalls. The collision is two-sided: :8074 falls 31.2 → 0.59 tok/s and :8070
    36.8 → 1.05 tok/s, because speech threads sit inside the LLMs' core masks and their barriers wait on them.
  - Partition test (a TEST Flash-Next instance, `-t 56` on 40-95): STT back to quiet levels (RTF 0.22–0.44), TTS
    marginal (first packet 0.24–1.0 s, RTF 0.93–1.40 vs 0.55–0.63 quiet), LLM decode −22..26% (23.0 / 24.5 vs
    31.1 / 31.3 tok/s). The frontdoor under the same partition was not measured (inferred similar).
  - No priority-pause mechanism exists today.
  - Options presented: **(A, was recommended)** partition the CPU LLM roles to 40-95 **and** move TTS back to the GPU
    (0.92 GB of weights; re-check VRAM headroom against the np4 :8083 + VL resident set first); (B) partition
    only (TTS stays marginal); (C) keep the layout and build a decode throttle that pauses LLM decode while TTS
    streams; (D) do nothing (any speech request during a `-t 96` generation wrecks both).
  - Acceptance that would have applied to A/B (keep for the operator's plan): the live-contention harness re-run against the new layout gives STT RTF < 0.5 and TTS
    first packet < 1 s with a CPU LLM generating, and the LLM decode loss is recorded.
  - The voice-pipeline handoff the operator's parallel agent is drafting must carry this contention as a
    requirement; that handoff did not exist at 2026-09-24 ~19:50Z, so no cross-reference was written.
  - Cross-reference (added 2026-09-24, later): the operator's plan landed as
    [`conversation-stack.md`](conversation-stack.md) (INF-79). This contention and the acceptance above are carried
    there as CS-12 (CS-11 declined 2026-10-21) (cascade onto the second MI210). KVU-11c stays here.
  - Layout hygiene seen in the same run: `megasync` (unpinned) ran at 60–100% on core 16, inside whisper's 0-23
    mask — a possible straggler source (quiet STT RTF spread 0.22–0.39). Pin it outside 0-39 as part of whichever
    option lands.
- [ ] **KVU-11c — replace the TTS `nprocs` shim with a real thread flag.** The shim (`LD_PRELOAD` interposer on
  `get_nprocs()`, orch `scripts/voice/`) is the accepted stopgap (package revision 3 §4.2). Add a thread-count
  flag to qwentts.cpp on an `experimental` branch and promote it as the next speech kernel version; then drop the
  shim and `SHIM_NPROCS` from the launch manifest.

## Not filed here (explicit)
- SSU-F3 structural capacity model (RS, draft KV, compute terms): RTG-19's SSU-F3 is done (2026-09-23,
  `artifacts/operator/vram-gap-27b-20260923.md`); the open follow-on is SSU-F10 (per-buffer VRAM logging on every GPU
  role). INF-41 aux VRAM in the gate:
  owned by OP-48 / INF-41.
- Package §10 items that the overflow branch already fixes: the 20,000-char routing threshold (now tokens and
  capacity-fenced), the 32768 compaction fallback, and 400 / "Context size has been exceeded." handling.
- The speech addendum's "priority pause instead of partitioning" alternative: not filed as its own task, because a
  pause cannot act mid-token and no mechanism exists; it survived as option C (KVU-11b; operator chose D).
- Frontdoor-under-partition measurement: not filed; the operator chose D (KVU-11b), and any re-run belongs to
  the operator's STT/TTS plan.
- A Stage-1 intake sweep of the audit's new primary sources (vLLM / SGLang / TGI / TRT-LLM / LMDeploy / LMCache
  docs): no claim here relies on them. Intake runs only when the operator invokes it.
- Declined 2026-10-04 (workspace-ec), from the KVU-16b root cause and the KV-serving survey:
  - `--no-kv-unified` (root cause fix 1c). It caps a slot at 98k and defeats KVU-16. KVU-16d already decided to keep
    the shared 393k pool, and its reopen trigger stands.
  - The admission rule "no ≥ 32k prefill while ≥ 2 slots decode" (fix 1d). KVU-16f/16g bound the same interference
    inside the server without starving long ingest, and KVU-15's one-long-prefill lease is the coarse version.
    Reopen it if KVU-16g fails its done-when.
  - `--ctx-checkpoints`, `--cache-ram` and `-cd` as fixes (fix 1b). Ruled out by source and log evidence.
  - Cascade/Hydragen shared-trunk attention (survey Rec 5). It pays only after KVU-20 forks trunks, and only if a
    rocprof profile shows shared-prefix attention dominating after KVU-16g, KVU-19b and KVU-20. Not filed until then.
  - Cherry-picking upstream #28532 `--slot-linger-ms`. The orchestrator's opt-in `id_slot` pinning gives the same
    binding (UFH14-B4).
  - A time-boxed vLLM/SGLang reference probe on the MI210 (survey §5). gfx90a is a degraded tier (ROCm ≥ 6.3 needed,
    no AITER, an open MI210 crash for this family), and it is not a production path. The survey offers it to the
    operator as an optional reference number; not filed unless the operator asks for it.
  - More checkpoints per slot for trunk-heavy roles (survey host-tier note). It is only meaningful once KVU-20 makes
    checkpoints into fork anchors, so it rides KVU-20.
  - A per-buffer VRAM logging task for KVU-16h. SSU-F10 already owns per-buffer VRAM logging on every GPU role, and
    KVU-16h uses `-lv 4` for its one-off attribution.

## Key files
- Orchestrator: `src/scheduling/kv_pool_admission.py`, `src/backends/context_limits.py`,
  `src/backends/context_overflow.py`, `src/llm_primitives/context_recovery.py`, `src/llm_primitives/inference.py`,
  `src/api/routes/openai_compat.py`, `scripts/server/orchestrator_stack.py`, `scripts/server/stack_commands.py`,
  `src/registry/stack_priors.py`
- Research: `orchestration/model_registry.yaml` (`serving_shape.kv_unified`, `vram_non_kv_gib`, `draft_kv_quant`,
  `cache_ram`)
- Frozen tree (read-only): `tools/server/server.cpp:145-150`, `tools/server/server-context.cpp:3303-3310, 3759-3801,
  1716-1735, 2468-2482`, `src/llama-context.cpp:289-302`

## Reporting
Flip the box here, update RTG-57's `Next action`, and append to `progress/YYYY-MM/`. Operator decisions go through
the master index: OP-54, OP-55 and OP-56 are decided and applied; the CPU speech contention (KVU-11b) was decided D (no change) by
the operator directly, with no queue row. The gate's known-gap choice was decided before filing: option A.

## Research intake 2026-10-20 — DeepInfer (research intake entries 2116–2142, see research/intake_index.yaml)

Operator-approved 2026-10-20 via research intake (plan sha256 recorded in the session's stage3_filing).

- [x] **KVU-21 — Agent-resume recompute probe on :8083 (intake-2131#record).** From existing request logs/timings compute, per resumed agent turn, recompute fraction = prompt tokens processed / prompt tokens, and pool usage from /slots, vs concurrent agents 1..4 plus queued; one bounded 4-agent fan-out replay in a GPU window only if logs lack it. Rule: median recompute fraction >= 0.25 at >= 3 agents while usage >= 0.5 opens the CONCUR-style AIMD admission trigger; below closes it. ✅ 2026-10-24 — CONCUR AIMD trigger CLOSED
  - *(2026-10-20, workspace-f8.)* usage arm NOT JUDGEABLE (/slots pool usage is in no :8083 log); fraction arm on agent-length resumes (prompt>=2000): median recompute 0.065 at >=3 busy slots (n=43), 0.014-0.015 at 1-2, all below 0.25; leans toward closing the CONCUR trigger, not conclusive; evidence /mnt/raid0/llm/tmp/analytics-20261020/KVU-21/REPORT.md.
  - [x] **KVU-21 replay arm (one bounded 4-agent fan-out replay in a GPU window) — NOT NEEDED** ✅ 2026-10-21 (backlog audit `/mnt/raid0/llm/tmp/inference-backlog-audit-20261021/REPORT.md` §0.4). The rule is a conjunction (median recompute >= 0.25 at >= 3 agents AND usage >= 0.5); the measured fraction is 0.065 at >= 3 busy slots on agent-length resumes (n=43, two eras; `/mnt/raid0/llm/tmp/analytics-20261020/KVU-21/REPORT.md`), below 0.25, so the CONCUR AIMD trigger closes whatever the unjudgeable usage arm reads and the 0.5 GPU-h replay cannot change the verdict. Caveat: n=43 is small and queued depth is unknown; the other open parts of KVU-21 stay open.
  - *(2026-10-24, f8 sweep.)* Refresh: no new :8083 data (log unchanged since 10-20 14:53Z; :8083 not run since), so the numbers reproduce exactly: median recompute on agent-length resumes 0.015 (1 busy, n=2062), 0.014 (2, n=916), 0.065 at >= 3 busy (n=43; only 1 of 43 >= 0.25, P(true median >= 0.25) ~ 5e-12). The usage arm is still unlogged (cheapest source: a zero-token /slots JSONL poller during the next :8083 agent window) and is irrelevant under the conjunction, so the trigger closes. Evidence `/mnt/raid0/llm/tmp/analytics-20261024/KVU-21/` (kvu21_refresh.py, results.json).
- [x] **KVU-12.3 — Decode-boundary checkpoint arm for the KVU-12.1 matrix (intake-2116#record).** Add a fifth hybrid-checkpoint arm that snapshots recurrent (and drafter) state every 128 generated tokens (capped per sequence), run on the frontdoor Qwen3.6-35B-A3B and the 27B with the KVU-12.1 controls; measure turn-2 resume prompt_n after 1k-4k generated tokens vs the dense arm, checkpoint bytes and TTFT. Counts are correctness class; TTFT in a window. — **CLOSED NOT NEEDED 2026-10-24** by the KVU-12.3a predeclared rule (generated-span re-prefill 4.52 % < 5 %); the P-A patch is not built.
  - *(2026-10-21, backlog audit.)* P-A SERVER PATCH DEFERRED (audit REPORT §0.6, §1 KVU-12.3): PLAN §11.5 unbuilt; do not build the decode-boundary snapshot patch until the zero-compute log pass below shows mid-generation divergences are material (A7 found 179/230 turns already extend exactly, i.e. little left for decode-boundary snapshots to recover). One confirming cell later only if the pass says so.
  - [x] **KVU-12.3a — zero-compute log pass: are mid-generation divergences material?** From existing request logs/slot timings (the KVU-21 :8083 log analysis `/mnt/raid0/llm/tmp/analytics-20261020/KVU-21/` and HSF-4 data; A7 = 179/230 turns extend exactly) count, per resumed agent turn, how many have a prefix divergence inside the previously GENERATED span (not the prompt) and the prompt tokens recomputed because of it; report the count and fraction with n, vs the exact-extend share. Decision: P-A patch build (KVU-12.3) opens only if the recomputed-token share from generated-span divergence is material (state the threshold in the result before reading it; predeclare >= 5% of processed prompt tokens at >= 3 busy slots unless the owner sets another); else close KVU-12.3 as NOT NEEDED. No server, nice -n 19, `prior=` the two inputs above. ✅ 2026-10-24
    - *(2026-10-24, f8 sweep, zero compute.)* Predeclared before reading (`/mnt/raid0/llm/tmp/analytics-20261024/KVU-12.3a/PREDECLARED.md`, 08:50:15Z): R = tokens re-prefilled because a resumed turn diverged inside the previous generated span (LCP - cache_n) >= 5% of processed prompt tokens at >= 3 busy slots opens P-A; with < 10 such turns at >= 3 busy the same test applies at all concurrencies. Input: the KVU-21 :8083 log (unchanged since 10-20). Exact divergence point from the v10 'checking checkpoint ... against X' trace (era 8 only, 1,456 tasks; cross-checks 1456/1456 and 152/152): 1083/1235 resumed turns extend exactly (87.7 %), 152 (12.3 %) diverge in the generated span; >= 3 busy n = 5, so the fallback applies: R = 422,853 / 9.35M processed = 4.52 % < 5 %. Derived point (f_keep x previous n_tokens, all 15 eras, robustness only): >= 3 busy n = 23, R = 0.055 %. Verdict: KVU-12.3 closes NOT NEEDED. Caveat: the cost sits at 1 busy slot (4.9-6.9 %); counting every re-prefilled previous-turn token gives 5.9-6.1 %, where A7 step 1 (render-side root cause via `LLAMA_SERVER_SLOTS_DEBUG`) is the cheaper lever. Evidence `/mnt/raid0/llm/tmp/analytics-20261024/KVU-12.3a/` (parse2.py, analyze2.py, derived.py, results.json, results_derived.json).
    - *(2026-10-24, f8 main, scope of the close.)* The close holds under its rule as written, but it is weak evidence for the case the question is about. Only 5 resumed turns fell at >= 3 busy slots, so the predeclared fallback pooled all concurrencies (1,235 resumed turns, mostly quiet). 4.52% sits close to the 5% bar. KVU-12.3 is NOT-NEEDED on quiet-dominated traffic; it is unmeasured under load.
    - [ ] **KVU-12.3b — re-check KVU-12.3a under load once busy traffic exists.** Trigger: the serving stack is back and >= 100 resumed turns have accrued at >= 3 busy slots on :8083 (down since 10-23; the 10-24 sweep found only `/health` traffic). Re-run `/mnt/raid0/llm/tmp/analytics-20261024/KVU-12.3a/analyze2.py` on the busy subset only, with the same R definition and 5% bar from its PREDECLARED.md and no pooled fallback. If R >= 5%, reopen KVU-12.3, the decode-boundary checkpoint arm. Zero compute.

**Dormant triggers (no checkbox, no index next action; materialize a task only when the trigger is observed). 'An' in a row means that intake entry's own dive-ledger row n:**

- DI-016 (intake-2119): monitor: revisit when (a) a second MI210 is attached (CS-12 cascade, kv-unified-stack-rollout.md:331) or (b) an NVMe-resident KV tier becomes the reload source and its read bandwidth, not PCIe, is the measured bottleneck
- DI-018 (intake-2119): monitor: admission-queue wait or TTFT p95 on :8083 rises while pool occupancy stays below its fit limit (that is the signature a pool-fit-only cap misses)
- DI-023 (intake-2120): monitor: llama_perf sampling time (t_sample_ms) exceeds 1% of eval time on a production frontdoor/architect log; otherwise knowledge-only (DeepSelect fp32 sampler claim is CUDA-only and our sampler already single-pass)
- DI-047 (intake-2125): monitor: the dive found Gemma-3n/4 KV-shared tail layers get no prompt-row pruning in prefill (exact skip available), but Gemma-4 was retired and deleted from the lineup on 2026-09-23 (orchestration/model_registry.yaml deprecated_models @ 62ee3ba6), so no consumer exists today. Trigger: any model with n_layer_kv_from_start sharing (Gemma-3n/4 class) re-enters the lineup; then file the exact row-prune with last-row logit parity.
- DI-053 (intake-2126): monitor: the AutoKernel GPU profiler reports MI210 prefill (-ub 2048) as compute-bound on GEMMs with a material attention share of layer time (otherwise nothing to overlap), or a hardware change adds idle matrix capacity (second MI210 / matrix-capable part). Until then knowledge-only.
- DI-060 (intake-2116#record): monitor: revisit only if a llama-server async-scheduling task is filed from the scheduler dive; trigger = any task that overlaps host scheduling of step N+1 with device forward of step N.
- DI-106 (intake-2131): monitor: CONCUR-A1 probe result (KVU-21) shows recompute fraction >= 0.25 at >= 3 agents with usage >= 0.5; then draft task in kv-unified-stack-rollout.md
- DI-126 (intake-2136; rewritten 2026-10-21 from intake-2215#04, intake-2216#01, intake-2217#01, intake-2218#02, intake-2219#03, intake-2221#00): monitor: short-request TTFT on a shared server rises while a request longer than 16K tokens is prefilling (join request_keys with the inference tap and record id_slot of BOTH requests). Mechanism in the frozen v10 tree: the pending-prompt loop walks slots in fixed index order (iterate(), server-context.cpp:2793) and returns for every later slot once batch.size() >= n_batch (:3205-3230, :3614), so a short request in a higher-index slot than a prefilling long slot gets zero prompt tokens until that prompt completes, while one in a lower-index slot waits one iteration; the KVU-16g budget never applies when no slot is generating. Split any rise into (i) queue-wait = task post to slot launch, which exists only when all np slots are busy (deferred deque, FIFO with slot affinity) or when the orchestrator long-prefill lease holds longs back, (ii) slot-order head-of-line inside update_slots (the mechanism above), (iii) prefill-share = decode/prefill interference, the KVU-16g domain, and (iv) co-batch inflation = iteration ms with the long chunk present minus the solo short iteration from the PB-QCOST-1 fit (324 + 0.987 q ms), the only part LAPS-style batch homogeneity could remove. Deciding probe for (ii) and (iv): PB-HOL-1 (gpu-serving-tie-in-program.md), which records the iteration ms at collision and a solo-short reference. Remedy per component: (i) a lane-aware pop_deferred_task() (short-first by task size with an enqueue timestamp and a long_max_wait_ms aging gate, or the static cost-normalised aging score wait_ms / estimated_prefill_ms plus a log-length boost with weights fitted from our own records, composed with LCP slot affinity; experimental branch) or an aging gate on the orchestrator's existing bounded short-pass rule, worth building only if the per-iteration prefill budget is fine (KVU-16g N in the 256-512 class) because reordering moves queue wait only, never execution time; (ii) shortest-remaining-prompt-first ordering of the pending-prompt loop plus a prefill-vs-prefill cap (M4 trigger, fires on PB-HOL-1); (iii) KVU-16g / 16g-2. Thresholds: (i) fires only if requests_deferred > 0 coincides with the rise; (ii)/(iii) fire when a colliding short request's TTFT rises by more than one prefill iteration (1.3-1.8 s per the PB-QCOST-1 fit); when KVU-15d lands, carry the admission verdict (head / wait / pass with the long flag) beside its lease-wait field so (i) is measurable; watch TTFT-under-long-prefill and preemption, not utilization. Until measured there is nothing to fix. UPDATE 2026-10-21: PB-HOL-1 off arms CONFIRMED component (ii): short TTFT 3217.5 ms with the short slot below the long slot vs 70932 ms above it (B/A 22.05, 3 repeats each), so the M4 ordering-fix trigger is open; budget-on arms ran 2026-10-21 evening and the budget does NOT relieve it: above/on 83352 ms vs above/off 70932 ms (23.2x vs 22.05x the below-slot arm; confounded by `-b`/`-ub` 512 -> 2048, no-decoder arm 63980 ms). The M4 ordering fix is now a filed task under PB-HOL-1 (`gpu-serving-tie-in-program.md`).
- DI-140 (intake-2140): monitor: a host-pinned KV tier prototype (hipHostRegister mapped region plus a small gather kernel, source-copied MIT from ROCm/mori UMBP and compiled for gfx90a) is the read side of a write-through mirror; trigger = the analytic write-through mirror costing finds the mirror fits the decode budget and removes measurable handover cost. MORI itself does not support gfx90a or ROCm 6.2, so this is a port, priced there.
- DI-142 (intake-2140): monitor: second MI210 installed AND a serving-engine EP consumer exists; then rerun this port map (first step: add gfx90a to _supported_arch_list / MORI_SUPPORTED_ARCHS with MORI_GPU_ARCHS=gfx90a and run only the intranode ep2 test)

**Retained knowledge (no task):**

- DI-008 (intake-2117): knowledge-only: lessons (1) and (3) feed kv-prefix-fork-and-paged-attention.md and v9-kernel-per-request-speculative-params.md as design context; no task.
- DI-011 (intake-2118): knowledge-only: design reference for A2 option (2); no separate task until A2 probe shows the class is open on a live server.
- DI-017 (intake-2119): knowledge-only: design rule for any future mirrored/offloaded KV traffic (see intake-2126-A3): price it against decode-in-flight on the same link and cores before enabling
- DI-019 (intake-2119): knowledge-only: have an equivalent feedback budget; revisit only with the sarathi-serve-cpu-evaluation re-promotion trigger (multi-tenant / prefill-heavy)
- DI-048 (intake-2125): knowledge-only: only Gemma-3n/4 in the lineup share KV across layers; nothing else benefits from YOCO-style prefill skipping.
- DI-049 (intake-2125): knowledge-only: cite YOCO for the exact early-exit argument and the O(N+CL) memory formula; do NOT cite its 71.8x/9.6x/80x figures as achievable on our stack (H100, gRet, 3B).
- DI-051 (intake-2126): knowledge-only: sets the precondition for A1 follow-up: only the non-spec arms (and CPU draft-free roles) could use a lagged batch; revisit if A1 shows a material gap in the no-spec arm
- DI-054 (intake-2126): knowledge-only: one-line regime test for the roofline program and np/batch sweeps; no new task
- DI-064 (intake-2116#record): knowledge-only: retained use is the boundary condition for any future "replay instead of checkpoint" proposal on Qwen3.6/3.8 hybrids (reject for GDN layers; only drafter SWA windows qualify, covered by KPF-13.1).
- DI-065 (intake-2116#record): monitor: next pull of fresh production into llama.cpp-experimental carries PR #30580 (llama.cpp upstream); trigger = KPF-17.4 SWA checkpoint range case runs on the new tip.
- DI-067 (intake-2116#record): knowledge-only: retained use is the comparison point for KPF-18.1 hit-length rows and a candidate hit policy for DS41 only after DS41-CED.1 shows the approximation is acceptable.
- DI-070 (intake-2116#record): knowledge-only: retained use is the Sarathi reopen comparison (sarathi-serve-cpu-evaluation.md:L14) - cite as vendor-reported engine behaviour code-verified @774ce24
- DI-092 (intake-2116#record): knowledge-only: cite the coverage_complete / rule-vs-judge agreement pattern when touching quality-gate summaries; do not import vendor Pass@1 as an EPYC target
- DI-098 (intake-2128): knowledge-only: Gemma-3n/4 are natively trained with KV sharing (not YOCO-style early exit; their upper layers still run for every token); the YOCO++ evidence neither supports nor refutes them, and no layer-skipping prefill on them is implied.
- DI-107 (intake-2131): knowledge-only: retained use = if A2 opens, fold a usage gauge into the same champion patch series rather than polling /slots; HSF-2 (heterogeneous-slot-fabric-residency.md:L276) already owns --metrics launch argv
- DI-108 (intake-2131): knowledge-only: intake-2119 reader_should_conclude should drop CONCUR as the support for the hit-rate figure; the 98.7% stays DualPath own-trace, vendor-reported
- DI-127 (intake-2136): knowledge-only: design input for the HSF demote threshold (0.8 hysteresis and a drain grace as starting hypotheses to be replaced by HSF-1 swap cost data); no separate task.
- DI-143 (intake-2140): knowledge-only: retained as the prior for MORI-A1 tier placement (no placement experiment needed unless A1 proceeds)
- SRF-A3 (intake-2215#01, #02): tuning doctrine for any length lane or lease threshold: put the threshold at the valley of the prompt-length histogram (P70-P85 as a start), size an aging bound from the long-request waiting tail measured under strict short-first, never from mean short TTFT, and read a promotion streak as "threshold too small"; re-check DEFAULT_LONG_PREFILL_TOKENS=16384 against HSF-4's per-role histogram when it exists.
- SRF-A6 (intake-2215#03): SharedKVPoolAdmission already has a bounded short-pass rule (short passes only when every ticket ahead is a lease-held long and it fits with their reservations counted; kv_pool_admission.py:59-62, 907-916 @ 65fbdce), i.e. the ShortRequestFirst idea at the admission layer without aging; the declined "no >= 32K prefill while >= 2 slots decode" rule stays declined.
- TB-A6 (intake-2216#04): the dual-pool paper's savings lever is vLLM reserving max_model_len KV per sequence (concurrency scales about 1/C_max); our frontdoor KV is per-instance host DRAM and the GPU champion has one instance, so the lever does not transfer as-is; verify the slot/KV reservation behaviour of our llama-server config before assuming either direction.
- TB-A8 (intake-2216#05): a chunked-prefill budget (KVU-16g / PB-QCOST-1) fixes head-of-line compute scheduling but not memory provisioning; on one MI210 the binding resource in the KVU-16g scenario is iteration time, so no new task.
- EW-A4 (intake-2217#02): EWSJF stays above the engine (waiting-queue / batch construction) and calls Sarathi-style iteration scheduling orthogonal; KVU-16g and KVU-15a are unaffected by it.
- FA-A2 (intake-2219#04): no paper in the lane supplies a measured aging-vs-SLO curve (vLLM-Ascend SRF has a bound and no numbers; 2606.09061 has numbers and no bound); if DI-126 component (i) ever fires, long_max_wait_ms = our own measured p99 queue wait of long requests under strict short-first, capped at the long-request TTFT SLO.
- GL-A3 (intake-2220#02): the magnitude class of a shared-queue HOL symptom at saturation is about 6.5 pp of TTFT pass rate (GreenLLM 8 QPS row, A100/Dynamo); context for DI-126, not a trigger value.
- LP-A5 (intake-2222#01): the KVU-15a 16384-token long-prefill lease with bounded short-pass is already orchestrator-level temporal disaggregation (at most one long prefill in flight, shorts pass); any engine-side long/short split is the residual after the lease, which PB-HOL-1 measures, not a new mechanism.
- SW-A2 (intake-2223#03), rider for KVU-16g-2: choose target-ms as the decode TPOT target minus a ONE-SIDED margin equal to the held-out P99 absolute residual of the PB-QCOST-1 fit (PB-QCOST-1 now reports it), never from the mean fit; SW-A3: in llama-server every generating slot advances in one batch per iteration, so per-slot deadlines merged by min collapse to one global target minus the host gap GPU-ZOS-1 measures.

### Research intake 2026-10-22 — Locals + Beacon (intake-2386..2460)

- [ ] **KVU-LB1 — CPU FP16 V-accumulator follow-through from the upstream reading: attach our reduced repro, accumulator-peak probe data and hybrid-fix results to the existing upstream issue and PR instead of a new report (posting is the operator's call; record the link); use upstream's fused-F32 cost data in the decode A/B and run it on the architect's real decode path at N=1 and N=5; move the dense-MTP-head acceptance check above 64k up, since production v10 has no fix and the architect declares a 262144 context (intake-2455).**
  - [x] KVU-LB1.a upstream evidence posted on PR #29810 (operator-reviewed and approved 2026-10-22): https://github.com/ggml-org/llama.cpp/pull/29810#issuecomment-6340235109 — model-free repro (non-finite only for n_q<64 once n_kv*bias > 65504), F16-accumulator sub-overflow error 0.297 vs 4.1e-5 F32, fused-F32 op-time parity on Zen 5 (24 thr, 131072 cells), real-model peak 237.6 with a 2048-cell window; we back always-F32. The unsourced "two-pass ~3x" figure was dropped (raw log not retained). ✅ 2026-10-22
  - [x] KVU-LB1.b decode A/B of fused-F32 on the architect's real decode path at N=1 and N=5 (compute; FILLERS row locals-kvu-lb1-arch-decode-ab, launcher armed 2026-10-22; rule in /mnt/raid0/llm/tmp/f8-launchers-20261022/locals-kvu-lb1-arch-decode-ab/PREDECLARATION.md) ✅ 2026-10-23
    - *(2026-10-23, run 1 post-mortem + redesign; workspace-f8)* Run 1 (07:06→08:16Z grant, champion dd3d9721c) ended rc=124 with s1-F16 OK and s2-F32 two cells into four.
      **The cause was not F32.** llama-bench `parse_cmd_params()` never initialises `cmd_params::autokernel_harden` (UB, present since `0492c2319` 2026-08-11, so in v10 `ffc1bac82`, dd3d9721c and 49550eda5).
      s2's process read it as true and silently ran the `--autokernel-harden` protocol: its jsonl rows carry `"autokernel_hardened": true`, and its stderr has no per-rep progress lines, because that branch prints none.
      That protocol does a separate depth fill for each of 20 contexts plus each measured/replicate rep, so 40 x 8192-token fills per benchmark.
      Timings: pp5@8k 07:12:43→07:39:52 (1629 s, ~40.7 s/fill) and tg64@8k →08:10:36 (1844 s, ~43.3 s/fill; the GPU job on SMT siblings 184-191 overlapped from 07:47).
      The two 32k benchmarks would have taken another ~4-5 h.
      For comparison, the non-hardened s1-F16 did ONE cached 8k fill (~37.5 s) and one 32k fill (~193 s), 306 s for the whole session.
    - F32 code path (ops.cpp at dd3d9721c and 49550eda5): `GGML_FA_VKQ_*` is a once-per-process `static const` that acts only in `flash_attn_ext_f16_one_chunk`, which serves N<64 query rows (decode, pp5) and split-KV.
      The tiled path (N>=64, i.e. every 512-token ubatch of a fill or prefill) always accumulates in FP32, whatever the knob says.
      So F32 has **no prefill catastrophe**, and there is no case for keeping F16 for prefill.
      The residual F32-hardened vs F16-plain per-fill gap (40.7 vs ~37.5 s, about 8%) is an upper bound, confounded by the hardened protocol: 20 contexts, different tokens, one F16 sample.
      Confidence: high on where the time went (arithmetic closes within a few %); low on any F32 prefill cost (code says ~0; the run-2 probe tests it).
      Bearing on KVU-LB1: "always F32" stays viable, and its cost question is decode-only (N=1, N=5), which run 2 measures.
      The s2 tg64@8k figure (22.73 vs 23.65 t/s) is unpaired, from a different protocol and from another binary, so it is not evidence.
    - Run 2 (PREDECLARATION.md **Amendment 2**, written before compute; thresholds, cells and ABBAAB unchanged):
      - re-anchored to 49550eda5 / build 10411 (`kernels/builds/cpu-20261021-49550eda5-c-nemotron`, via `arch_common.sh`); run-1 data archived to `out/run1-dd3d9721c-20261023/` and excluded;
      - hardened-protocol guard: a missing warmup line 30 s after the weights are resident triggers kill-own-pid and a relaunch, up to 5 attempts; any `autokernel_hardened: true` row makes the session INVALID;
      - report-only `FILL_TIMES.json` and a prefill probe: pp512/pp2048 at d0, ABBA, -r 3, written to `PREFILL_PROBE.json`;
      - window ~45-50 min expected, ~60 worst case. DRY_RUN=1 is clean.
    - Fleet-wide follow-up (the owner must file it): about half of llama-bench processes on these builds run hardened unasked. 18 of 32 jsonl files under `tmp/cpu-backlog-20261004/c4` and `tmp/f8-launchers-20261022` carry `"autokernel_hardened": true` without the flag.
      Fix: initialise the field (`params.autokernel_harden = cmd_params_defaults.autokernel_harden;` and the seed/timeout) in the experimental tree.
      Until that lands, any llama-bench consumer must reject rows whose `autokernel_hardened` is true unless it asked for them.
    - *(2026-10-23 run 2, workspace-f8.)* Verdict **NO_COST** (PREDECLARATION + Amendment 2, thresholds unchanged): champion store image 49550eda5/10411, Q38FN architect recipe, 96 threads, ABBAAB, 3/3 valid pairs. Median effect (F32-F16)/F16 decode tok/s: N1@8k +1.38%, N5@8k +0.86%, N1@32k +1.05%, N5@32k +14.1% (one pair +55%, noisy); no cell at or below -1%. Report-only prefill probe (pp512/pp2048 at d0, 2 pairs): +1.8% / -0.1%, matching the code reading (n_q>=64 takes the tiled FA path, always FP32). The hardened-row guard relaunched 9 sessions (up to 4 attempts; `out/hardened_relaunches.txt`); every row used is `autokernel_hardened: false`. So always-F32 FA accumulation costs nothing on the architect CPU decode path, and it removes the FP16 VKQ overflow risk (KVU-LB1.a).
    - [ ] KVU-LB1.d — adopt always-F32 VKQ accumulation on the CPU FA path (`GGML_FA_VKQ_F32=1`, or make F32 the compiled default in the next champion): decide the carrier (recipe env per CPU role vs a champion default change via the fold ledger), then roll it through the stack-change package with the 3-gate check. Run-2 evidence: NO_COST on the architect; check the frontdoor/worker CPU shapes with the same guarded harness before flipping a global default.
      - [x] **T96 failed-row repair and diagnostic READY** ✅ 2026-10-28 — the old failed attempt had three complete arms and two of four cells in its fourth, not a completed six-arm comparison. Repaired captured-descendant cleanup and fresh atomic ABBAAB launch path; actual same-launcher smoke on free, ungranted q2 CPUs 48-49 ran 74.491 s, rc 0, two real HYBRID tiny-geometry benchmark iterations, result writer and cleanup verified. Published `rtg57-c5-vkq-t96-repair-20261028` READY (0-95, min 5100 s / window 5700 s, 110 GiB); keeper reports resource wait. This is preparation only: full T96, F32 treatment, correctness and carrier/adoption remain open. [Evidence and limits](../../progress/2026-10/2026-10-28-t96-repair-ready.md). [belief: cc]
      - *(2026-10-28, retained native completion/postprocessor failure.)* Whole-host T96 job ended 20:52:03 UTC outer rc1 after 2494.415 s, cleanup verified. All 6 native arms/24 rows completed; postprocessor then failed on an output-depth-derived PROTOCOL path, before tuples/COMPLETE. Independent read-only replay with explicit producer binding reproduces native indicative COSTS; all 19 source pins and 7 producer-bound timing-disclosure files verify. Unbounded peer/NI co-activity means no clean-window or decision warrant. Original projected-claims output is empty; no post-run measurement backfill/ingest. Preserve only the committed descriptive conclusion; launcher path repair continues without automatically repeating native work. [Details](../../progress/2026-10/2026-10-28-codex-ni-periodic-wrap.md). [belief: cc]
      - [x] **KVU-LB1D-FRONTDOOR-PREP-01a16fc3:** reviewed CPU frontdoor diagnostic packet changes V cache q8 to F16 to exercise F32 treatment; unarmed; actual run requires owner scheduling and grant. No live q8 claim. ✅ 2026-10-27 [no-belief: preparation only, no measurement]
      - *(2026-10-27 21:35Z, ws58 results filing, KVU-LB1.d frontdoor F16-V quarter diagnostic.)* `refactor-01a16fc3-kvu-lb1d-frontdoor-f16v-q1-20261027` rc0; verdict **NO_COST** (`/mnt/raid0/llm/tmp/refactor-01a16fc3/m4-cpu-frontdoor-worker-ready/frontdoor-q1/runs/<attempt-dir>/verdict.json (single attempt)`). Per-cell median effects in the verdict file (F16-V vs F32 diagnostic; sign convention is the verdict file's own): n1,8192 +0.5954%; n1,32768 +5.92%; n5,8192 -0.398%; n5,32768 +8.879%. A quarter (CPUs 24-47) F16-V diagnostic of the frontdoor model only: NOT the live q8-V recipe, no live-q8 claim, no fold or default change. [belief: cc]
      - *(2026-10-27 12:30Z, ws58 results harvest; build evidence for gate (a), not a decision.)* C5 CPU build `refactor-01a16fc3-c5-cpu-build-20261027` rc0 (BUILD_COMPLETE 10:18:48Z, source `c72ec82f5417bb2937310326120f149b665e8400`, 117 ELF hashes, linkage OK against its own `buildcpu/bin`); C5 HIP build `q0-v2` rc0 (BUILD_COMPLETE 11:32:37Z, 118 ELF hashes, linkage OK, `GGML_HIP_ROCWMMA_FATTN` in the compile commands, `ggml_cuda_flash_attn_ext_wmma_f16` symbol present). The 2-minute HIP time is a genuine fresh build, not a cache: `buildhip` was absent beforehand, ccache was NOT found (`GGML_CCACHE_FOUND-NOTFOUND`), configure ran 11:30:43Z, the first `.o` was written 11:30:50Z, 604 build steps, binary mtimes span 11:30:44Z-11:32:36Z on 24 CPUs. M4 recut (`bc441f1a261766d11bfeff21668a1031c4dbf8cd`, M4 7-file recut on C5) CPU build rc0 10:28:26Z (118 ELFs) and HIP build rc0 11:35:36Z (119 ELFs). The string `GGML_FA_VKQ_F32` is present in all four binaries, so a null from that knob in a later A/B is evidence about the knob, not about a missing knob. No model ran in any build. Evidence: `/mnt/raid0/llm/tmp/refactor-01a16fc3/{c5-candidate,inf22-m4-prep}/jobs/{cpu,hip-q0-v2}/` (BUILD_COMPLETE, ELF.sha256, LINKAGE.txt, BINARY-MTIMES.txt, strings-*.txt). Meaning: the C5 candidate binaries exist and are structurally verified; no speed, quality or F32-VKQ cost number follows from a build. Next: gate (a) measurement on these binaries via the guarded harness on the frontdoor/worker CPU shapes. [belief: cc]
  - [x] KVU-LB1.c move the dense-MTP-head acceptance check above 64k up in its owning queue (production v10 has no fix; architect declares 262144 ctx) ✅ 2026-10-22: the task is `CPU-FA-VKQ-3` in the CPU-FA-VKQ group of this file (was 4th of the open items); moved to the top of that open list.

### KVU-LB1.d candidate-only preparation — 2026-10-27

- [x] **KVU-LB1.d-prep — prepare conditional C5 architect HYBRID/F32 comparisons and a narrow numerical probe.** T48 and T96 entries passed scoped same-entry preflight and private live-poller row/admission checks, remain STOP/main-seal/owner-enrollment guarded, and have not run the model. The independently predeclared C5 F32 model-free f16/D256/KV8192/causal one-thread case passed an FP64 oracle (max N1 NMSE `3.78851027e-9`, N5 `3.682e-9` vs existing `5e-4`); a finite +1 N1 output mutation was detected (`3.47959096`). CPU library/knob/env/live mapping verified; 24 Q heads, 2 KV heads and D256 match architect GGUF metadata. No iqk fastpath, role quality, timing or adoption claim. Original receipt lacks producer-script hashes; future v2 records them prospectively. Details, receipts, source, and owner wiring drafts: `artifacts/operator/rtg57-f32-prep/`. ✅ 2026-10-27 [no-belief: native receipt captured; adapter enrollment and planning-context canary remain pending]

- [x] **KVU-LB1.d-VKQ-WIRE-PREP — prepare native belief capture and private planning canaries.** MAIN accepted `codex/rtg57-vkq-wire-20261027` code at `3b25745b0c49e32d67fd9ac3937b1b83c0bc62f9`; shared measurement grading, no new ladder. Both synthetic T48/T96 receipt-writer → private ingest → planner checks produced four Judged/Located target claims, n=3 and empty protocol; tampered raw arms were refused; 99 scoped tests passed. The original n=1 model-free oracle remains without model/device scope and missing original producer hashes. MAIN sealed both packet entries; owner source/table/task enrollment, post-merge installed-source/producer canary and actual timing remain pending. T96's 5700s is a bounded attempt, not a completion estimate; partial output has no verdict and cannot resume. ✅ 2026-10-27 [no-belief: synthetic capture and wiring preparation, no new measurement]

The parent KVU-LB1.d remains open. Its carrier, owner belief enrollment, actual role comparisons and stack-change gates are not complete.


2026-10-30 01:07:21–01:09:24Z, original `fa4-c5-exact-set-r5-20261030` window ended rc1/INCOMPLETE. Its A/ON native op control covered the exact 228 unique predeclared six-field inputs (`arm_check=OK`), 224 OK and 4 NONFINITE: tail/diffuse/bias1024 at `(rows, n_kv, KV) = (64,2048,f16), (512,4096,f16), (64,2048,q8_0), (512,4096,q8_0)`. The A model probe completed 10 runs with 0 nonfinite. Server-A wrote 13 request rows, all HTTP 200, but its native stage remained partial: the driver raised `ProcessLookupError` reading a disappeared `/proc/.../status` during process sampling. Owned cleanup was verified. B/OFF did not run in this window, and `NORMAL-COMPLETE.json` is absent; exact ON/OFF outcome comparison, mechanism, performance and promotion remain unestablished. Earlier same-ID windows and any later rearm are separate originals. [belief: cc] [Committed native audit](../../artifacts/compute/results-filing-20261030-0138.json).


Insert under V11-FA-4a in /workspace/handoffs/active/kv-unified-stack-rollout.md; leave the checkbox open:

  - *(2026-10-30, original fa4-c5-exact-set-r6; incomplete)* Under the predeclared source-derived 228-case universe, ON/A covered 228 distinct keys with `arm_check=OK`: 224 OK and four nonfinite bias1024/diffuse tail cases (f16 and q8_0, rows64/KV2048 and rows512/KV4096). ON/A model probe passed 10/10 with 0 nonfinite. The server-A stage then failed during process-executable sampling with `FileNotFoundError` for `/proc/3424357/exe`; the native HTTP request record is empty, so no HTTP result is established. Cleanup was verified. OFF/B and the matched-input comparison, remaining native controls, and all three-pair/22-band timing were not completed. The disappearance's underlying process state is not established. Source/predeclaration SHA `d42489124f7c7b1e2b81ce54db34b57ff6a789588f0f9620e66f194a28f4a532`; original `FAILED.json` SHA `d43670caf40378911e4a96fe5001dbd6defcd00d90eee6b2b4555ff24c0fcc7a`; ON/A native SHA `f72813b0c0c1d9b29914fd606f62399116f3f61c0d463f6a4b58f0b09638dd63`. Original run: `/mnt/raid0/llm/tmp/codex-ni-fa4-exact-set-successor-r6-20261030/runs/20261030T022226Z-3404347/`. [no-belief: incomplete diagnostic; no paired comparison]

Owner action: investigate how the process executable can disappear while the retained pidfd appears live, preserving birth identity and refusing to count missing process/residency evidence; keep the original run immutable and use a new successor identity for any later execution. No new checkbox is needed.

[Committed original audit](../../artifacts/compute/results-filing-20261030-0252.json).
