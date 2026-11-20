# long-context-program — compacted ticked boxes (2026-11-20, handoff_compact.py)

- [x] **YARN-E0 — the zero-compute preparation (operator-approved 2026-10-04).** ✅ 2026-10-04 (the runner and
  runbook carried E1 end to end; see below) Subagents are preparing it
  in `/mnt/raid0/llm/tmp/yarn-e1-20261004/`. It has three parts:
  - **The runner.** Fork Q38-T7's cached-prefix needle logic into a long-context runner, and write truth rows in
    `coherence_gate` form (`{"grader":"needle","expected":[…]}`).
    - **Neutral haystack only:** RULER noise, or essays with sentence ids. Q38-T7's 80k needle failed because the
      model refused an "injected" fact planted in an AutoKernel context.
    - **One prefill per (arm, length):** 5 needles at depths of 10/30/50/70/90%, each asked as a short continuation on
      the cached prefix.
  - **The launch lines** on a scratch port (e.g. 18083), with the production env and `LD_LIBRARY_PATH`:
    - **A0 (native):** `-np 1 -c 262144 -ctk q8_0 -ctv q8_0 -ub 2048 --flash-attn on --no-mmap -ngl all --cache-ram 0`,
      with no `-md`.
    - **A1 (YaRN f2):** A0 plus `-c 524288 --rope-scaling yarn --rope-scale 2 --yarn-orig-ctx 262144 --override-kv
      qwen35.context_length=int:524288`.
    - **A2 (negative control):** A1 without the rope flags.
  - **The required bring-up proof lines:** `n_ctx_orig_yarn = 262144`, `freq_scale = 0.5`, `rope scaling = yarn`,
    and `n_ctx_slot = 524288` with no capping warning. KFD at load must be ≤ ~50 GiB.
  - **Stale-geometry caches** (intake-1347#record): the instance uses its own empty cache and a scratch slot path,
    and never restores production slots.
  - **Belief-kernel write side:** VB-YARN-E1 in `vidya-belief-substrate-program.md`.
- [x] **YARN-E1 — the GPU experiment, ~2.5–3 h of a parked-:8083 window (operator-approved 2026-10-04).** ✅ 2026-10-04
  RUN — **FAIL by C4 (memory) only**; results below. The
  pre-registered cells (ASSESSMENT §6), all greedy with thinking off and real token ids:
  1. **Short context:** ~60 `question_pool` items under 4K, A0 vs A1. A `coherence_gate` PASS means 0 REGRESSION.
  2. **Native range:** 128K and 240K haystacks with 5 needles each, A0 vs A1. A1 must score ≥ A0 − 1 correct out of
     10, with a clean `degeneracy.v2`. A0 at 240K is also the first ground truth near 262K for this model.
  3. **Beyond native:** 400K (A1, plus A2) and 500K (A1) haystacks. A1 needs ≥ 4/5 at each length, and A2 must
     score clearly worse, or the test is not discriminating.
  4. **Memory:** the KFD peak stays ≤ 55 GiB.
- [x] **YARN-FA-INT64 — fix the int32 mask/K offsets in GPU FlashAttention (probable llama.cpp #27090).** ✅ 2026-10-04
  (workspace-ec; coordinator add-on to the DCA work)
  - Branch `experimental/fa-int64-offset-20261004`, on the champion, three commits:
    - `6152cdf7a` fixes the WMMA kernel;
    - `0c4801127` fixes tile, MMA and vec, and adds `launch_fattn` truncation asserts;
    - `4f21c3477` adds the `test-backend-ops` `mask_ne0` cases.
  - CPU proof: the first wrapped mask offset is at n_kv 526,592 (ub 2048), 262,912 (ub 4096) and 1,057,024 (ub 1024);
    nothing wraps at ub 512.
  - GPU slot `gpu-slot-20261004T145625Z`: **PASS** (durable copy `artifacts/dca-yarn-kernel-20261004/fa-int64/`).
    - `mask_ne0` cases: the fixed build passes 4/4; the champion passes 1/4 (3 FAIL, ERR 0.03-0.59).
    - Full `FLASH_ATTN_EXT` suite on the fixed build: 2872/2872.
    - Existing cases: 119/119 bit-identical to the champion (worst nmse 0).
  - The v11 carry is `fork/experimental/fa-int64-offset-master-20261004`: the revert of #26046 plus the picks. It is
    not compile-verified on master.
- [x] **YARN-FN-FIX — Flash-Next fused decode must honour the rope parameters (in flight).** ✅ 2026-10-04 `qwen4exp-fused.cpp:1709-1717`
  hardcodes `freq_scale=1, ext_factor=0, n_ctx_orig=0`. Pass the model's real `freq_scale`, `ext_factor`,
  `n_ctx_orig_yarn`, `attn_factor` and `beta_*` through to the fused path. This is latent at native length as well,
  where `n_ctx_orig=0` is harmless only while `ext_factor` is 0. It is being built on `llama.cpp-experimental` in the
  same subagent dir. Done when the fused decode matches the graph path bit-for-bit (or within the fused path's
  existing tolerance) under a YaRN configuration in a CPU test, with no regression at native length.
  - *(2026-10-04, workspace-ec.)* **Fixed** in `5bfdcd18c` on `experimental/fused-yarn-20261004`.
    - The fused decode now takes the context's rope/YaRN parameters. `freq_base` was hardcoded as well, so
      `--rope-freq-base` had also been ignored.
    - `6c126e975` gates two per-token debug leftovers behind `GGML_FUSED_DECODE_TRACE`: a stderr line, and `/tmp`
      file writes on every token.
    - Test `tests/test-qwen4exp-fused-rope.cpp`: K nmse 6e-9 (YaRN) and 8e-9 (freq-base), against 0.53 and 1.09
      before; logits 1.7e-11; native OK; 56/56 steps fused.
    - Notes: `artifacts/dca-yarn-kernel-20261004/NOTES.md`.
    - A separate fidelity gap at non-production weight scales is FD-DIV-1 in `cpu-fused-decoder-blocks.md`.
  - [x] **YARN-FN-FIX-fold — fold `5bfdcd18c` + `6c126e975` into the champion.** (filed 2026-10-04, workspace-ec) ✅ 2026-10-23 (triage by 3c4ca599's fold-prep subagent; ec's box, ticked on the coordinator's instruction): already folded, nothing to do. `git cherry 141e4bcf5 fork/experimental/fused-yarn-20261004` marks `5bfdcd18c`, `6c126e975` and `45d8f2937` patch-equivalent to champion commits `b86c725e2`, `39c7209e4`, `b0ba1d427` (manifest V11-019 IN; `test-qwen4exp-fused-rope` 3/3, OK again on candidate C's final build). Evidence: `/mnt/raid0/llm/tmp/c3-fold-prep/PLAN.md` section 1.
    Production keeps `GGML_FUSED_DECODE_OFF=1`, but the champion's fused path still writes `/tmp` files on every
    token and ignores rope parameters. Done when the champion tip carries both commits, with the fused-rope test
    green.
- [x] **YARN-INERT-PRIORART — prior-art audit of how production stacks (vLLM/SGLang/TGI/TRT-LLM/llama.cpp upstream/HF dynamic+longrope) and Qwen guidance avoid native-window regression, and whether YaRN is still SOTA.** Write-up: `/mnt/raid0/llm/tmp/yarn-inert-design-20261006/OPTIONS.md` (in progress). Coordinate with YARN-OPTION-D-DECISION after the audit is complete. ✅ 2026-10-06
  - *(2026-10-06 correction, intake-1911 REDO)* "Nobody re-ropes at the crossing" is false for llama.cpp itself: `llama-memory_seq_div` plus the K-shift graph (`build_rope_shift`) re-rope cached K for Self-Extend (completion/passkey only; llama-server does not use it). Jet-Long keeps base-roped K and rotates distant K on the fly, so it avoids a cache rewrite.
  - *(2026-10-06, workspace-ec)* Prior-art audit complete; write-up `artifacts/yarn-ctx-20261006/OPTIONS.md` (durable copy). Root cause: mscale 1.0693 sharpens logits at all positions; feeds YARN-OPTION-D-DECISION.
- [x] **YARN-MSCALE-AB — mscale-neutral YaRN 3-arm greedy A/B (no-YaRN / static / attn-factor-cancelled) on experimental branch `llama.cpp-experimental/yarn-mscale-20261006`.** Includes the fix for `--yarn-attn-factor` being discarded when `ext_factor != 0` (`llama-context.cpp:220-228`). Done when the three arms are measured on a production-shaped Qwen3.8-27B prompt set (same as E1 short context) and the attn-factor test shows whether cancelling it recovers the native-window performance. ✅ 2026-10-06
  - *(2026-10-06, workspace-ec)* **VERDICT: the CTX-1 gate FAILS.** Fix `--yarn-attn-factor` is `720a98e2a` on `llama.cpp-experimental-yarn-mscale-20261006` (cancel factor 0.935190). Greedy identity vs no-YaRN: N 20/20, Y 13/20, YM 13/20; MTP@34k acceptance 0.514 / 0.490 / 0.468. Drift comes from frequency interpolation, not mscale, so cancelling mscale does not make YaRN inert. Evidence: `artifacts/yarn-ctx-20261006/yarn-mscale-ab-summary.md`.
- [x] **YARN-OPTION-D-DECISION ✅ 2026-10-06 — decide between the length-routed second server (D) and in-process per-request YaRN (A) after the prior-art audit and the mscale A/B.** Operator concerns to address: RAM cost of a second weights copy (production :8083 uses `--no-mmap --mlock`, so weights are private per process) and the re-prefill cost on crossing. Write the decision and its rationale into the stack-change plan template.
  - *(2026-10-06)* The package must state D's added RAM as a number (a second private weights copy under the canonical `--no-mmap --mlock` recipe, plus extended-server KV and compute buffers) and the F and Jet-Long-cached alternatives against the gates G1-G3 in the intake plan; the operator's rule (no regression inside the native window) and the CPU-first 1M order apply.
  Owner: workspace-ec
  - *(2026-10-06 inputs)* CTX-1 FAILED (inertness is not cheap via mscale), CTX-KSHIFT gate G2 fails (K-shift is not a re-rope primitive at v10), Jet-Long cost PASS on paper. Decision can now be written; see CTX-JETLONG-PROTO limits.
  - *(2026-10-06 evening, workspace-ec)* Decided by the operator 2026-10-06: cached Jet-Long (J) is the long-context target, no interim D, conditional on above-native recall >= static YaRN (D RAM would add ~49-52 GiB; host 778 GiB free). Evidence: `artifacts/ec-wrapup-20261006/DECISION_CTX4.md`.
- [x] **CTX-KSHIFT — three source-then-unit probes on the llama.cpp K-shift path (H1 mscale re-applied per shift under YaRN; H2 `pos_div` records shift += old-new vs `pos_add` += d; H3 quantized-K Hadamard `nrot` from the full head dim vs partial-rotary n_rot).** (filed 2026-10-06, from intake-1911 REDO) Experimental branch only, CPU, synthetic fixtures, f16 control. Done when each hypothesis is CONFIRMED or REFUTED with the max-abs error recorded and thresholds as predeclared (H1 norm ratio 1.000 +/- 1e-3; H2 error <= 1e-6; H3 <= 2x plain q8_0 round-trip error). A confirmed one becomes a defect ticket on the experimental branch; K-shift is not reused by F/A/Jet-Long until all three are closed. ✅ 2026-10-06
  - Owner: workspace-ec
  - *(2026-10-06, workspace-ec)* H1/H2/H3 all CONFIRMED at `ffc1bac82`. H1 K-shift re-applies YaRN mscale, ratio 1.0693^n (`llama-kv-cache.cpp:1992`). H2 `pos_div` sign error (`llama-kv-cells.h:478`; err 4.711 vs 1.7e-6). H3 q8_0 Hadamard nrot taken from the full head dim (`llama-kv-cache.cpp:1454-1461`; 84.7x/120.8x round-trip error); the CPU quantized shift also aborts (`ggml-cpu/ops.cpp:323`). Fixes on `llama.cpp-experimental-kshift-probe-20261006` (tip `f9cb7cd32`), unit-verified only; the H3 fix is marginal at 2.08x. Production NOT exposed (v10 defaults ctx_shift=false, n_cache_reuse=0; no production argv sets them). Gate G2 FAILS. Evidence: `artifacts/yarn-ctx-20261006/CTX2_KSHIFT.md`.
- [x] **CTX-JETLONG-COST — arithmetic plus CPU microbenchmark of the Jet-Long correction rotation (uncached vs per-G-epoch cached), n_rot=64, at 32K/128K/262K/1M.** (filed 2026-10-06, from intake-1900/1919 REDO) Done when bytes/step and measured ms/step on 96 threads under `region-lock` are filed; passes if the cached variant adds <= 10% decode at 262K and <= 25% at 1M, else the Jet-Long port is parked. ✅ 2026-10-06
  - Owner: workspace-ec
  - *(2026-10-06, workspace-ec)* PASS, measured. Uncached +13.5 ms/step at 262K and +46 ms at 1M (10 layers); cached +2.4 and +9.4 ms. About 9% uncached and 2% cached against EXTRAPOLATED baselines (143 ms, 500 ms), so the percentages are estimates. Evidence: `artifacts/yarn-ctx-20261006/ctx3a/COST.md`, `artifacts/yarn-ctx-20261006/ctx3a/results_20261006T054613Z.csv`.
- [x] **YARN-ATTN-FACTOR-CARRY ✅ 2026-10-06 — carry the `--yarn-attn-factor` fix `720a98e2a` (llama.cpp-experimental-yarn-mscale-20261006) onto the champion branch via the champion fold.** Owner: workspace-ec. (filed 2026-10-06) Done when the champion carries the fix, `strings` confirms it, and a re-run of the YM arm reproduces cancel factor 0.935190. Never on production.
  - *(2026-10-06 evening, workspace-ec)* Carried to the champion candidate llama.cpp-experimental-champion-specwidth-20261006 @ `8e597b701` (version 10342; CPU+HIP builds and linkage PASS). The fold itself is pending workspace-89 regression gates (`artifacts/ec-wrapup-20261006/FOLD.md`). Upstream draft: `artifacts/ec-wrapup-20261006/ISSUE_ATTNFACTOR.md`.
- [x] **JETLONG-SMALL-UB-BUG — fix the Jet-Long get_rows OOB assert (`ggml-cpu/ops.cpp:5350`) for ubatch < window at positions beyond native (IMRoPE).** Owner: workspace-ec. (filed 2026-10-06) Hits 4-token tails and likely decode on Qwen3.8-27B (qwen35); no repro on Qwen3-0.6B (NeoX). Evidence `artifacts/ec-wrapup-20261006/SAVE_RESTORE_TEST.md`. Done when ubatch 1/4/32 above native run without the assert on qwen35 and T1-T3 stay exact. Blocks the two items below. ✅ 2026-10-07 Fixed at `e6ea79421` (llama.cpp-experimental-jetlong-hip-20261006): root cause was `llm_graph_input_mem_hybrid::set_input` never filling Jet-Long inputs and `can_reuse` never blocking reuse; every pre-fix above-native hybrid result is INVALID. T4 tests ub 1/4/16/64, tail, decode, IMRoPE+NeoX, q8_0+f16 pass; evidence `artifacts/ec-wrapup-20261007/SAVE_RESTORE_TEST.md`.
- [x] **JETLONG-SAVERESTORE-PRETEST — order-(ii) slot save at the ack plus the within-window context-checkpoint hit (after JETLONG-SMALL-UB-BUG).** Owner: workspace-ec. (filed 2026-10-06) Checkpoint creation at the expected positions already observed; reuse on hybrid models was never observed historically (`progress/2026-09/2026-09-16-sub-op42-readiness.md:131-143`). Done when a restored slot resumes with a checkpoint hit and identical continuation. ✅ 2026-10-07 Prefill-only boundary trick passed on CPU 27B: save 280.8 MB/70 ms, restore 36 ms, extension prompt_n 2203 == delta, byte-identical, acceptance 33/41 both; first observed hybrid prefix reuse (follow-on HYBRID-PREFIX-REUSE, kv-unified-stack-rollout.md).
- [x] **KV-0a — Every KV slot save was failing; fixed.** ✅ 2026-08-20 `prefix_cache.py` built the filename with `os.path.join(...)`,
  producing a `/`-containing string; llama-server rejects those via
  `fs_validate_filename(allow_subdirs=false)` before it concatenates `--slot-save-path`. Proof it
  never worked: the 75 retained slot artifacts on disk are **all** `kv_migrate_*` from the sibling
  `concurrency_aware.py` path, and there are **zero** `slot_<id>_<hash>.bin` files anywhere. Fixed by
  emitting a bare filename (`_slot_state_filename`, mirroring `concurrency_aware._slot_filename`).
  Two compounding defects fixed alongside: the restore path did a **client-side** `os.path.exists()`
  on a **server-side** filename, and both backend methods caught `httpx.RequestError`, which does
  **not** cover `HTTPStatusError` — so a 4xx propagated instead of returning `False` as documented.
- [x] **KV-0b — Roles sharing one llama-server were evicting each other; fixed.** ✅ 2026-08-20 Under `shared_with`, several roles
  resolve to one physical server, but the legacy loop built a **separate `PrefixRouter` per role**,
  each allocating `id_slot` in `[0, num_slots)` from its own private LRU — so two roles both emitted
  `id_slot=0` and silently clobbered each other, unobservably. Now one router per physical URL
  (`_router_for`), matching the shape the fleet layer already had. 3 regression tests added.
- [x] **KV-5 — Correct `wiki/kv-cache.md`** ✅ 2026-08-20 (done in the wrap-up wiki sweep) so KVFlow is named as the ORIGIN of workflow-aware KV
  residency, with its own venue (NeurIPS 2025), its own 1.11× ablation and its Apache-2.0
  implementation — not solely as the denominator of PBKV's self-reported 1.26×. Note also that 1.26×
  **on static workflows** means KVFlow retains most of the gain on declared topologies, which is
  exactly what our delegation path is; filing it as "beaten" inverts the reading for our own use case.
- [x] Current-v7 source/build surface reconciled at `111bff89d` + `cf051d3e1` on `fork/experimental-v7-refresh-20260716` ✅ 2026-07-18
- [x] CPU mechanical smoke completed for baseline and StreamingLLM lanes; both passed mechanics but failed prompt-quality, so no admission/performance claim ✅ 2026-07-18
- [x] Pre-v7 floor/admission sweep completed on Qwen3-1.7B Q8 CPU-only: all arms exited cleanly, no sink/window cluster passed quality+speed floor, and no KV cluster is admitted before v7 promotion ✅ 2026-07-20
- [x] Resolve user questions: K_sink/K_win sweep values, F16 KV scope, PBKV order-of-operations ✅ 2026-08-25 — **operator decisions**: (1) full K_win sweep {1024, 2048, 4096} — 54 streaming cells; (2) F16 KV control on gemma4 only (smallest model); (3) PBKV runs in parallel — no sequential gate (lease/region serialization prevents concurrency poisoning; no PBKV spike currently in flight, so the floor still lands first de facto)

