# 2026-09-16 — sub-gpu-runner (sole MI210 runner, subagent of the main session)

Research worktree: `/mnt/raid0/llm/worktrees/sub-gpu-runner-epyc-inference-research`, branch
`sub/gpu-runner-20260916`, based on `142fd1e3` (= `lane/autokernel-unified-20260908` head, the base the
prep agent also uses). Scratch results: `/mnt/raid0/llm/tmp/sub-gpu-runner-20260916/`.
GPU claim: `autokernel.loop.claim.hold()` (flock `/mnt/raid0/llm/tmp/gpu_device.mi210_0.lock`), held by
each runner for its whole window. No KFD process was present at start; no CPU inference was started.

## 1. INF-66 R23-61a — already done 2026-09-15; not re-run

- The code half was already landed: research `a25aaf1f` (`serving.write_floor` stamps `n` and
  `floor_ci`; test `loop/test_floor_ci.py`), merged into the lane at `e65ed477`.
- The run was also already done on 2026-09-15 (option (b), PRE-BIOS floor), and the box is ticked in the
  `autokernel-hardening-20260915` lane copy of `autokernel-rebuild-program.md` (not yet in `/workspace`).
- The live floor file `autokernel/loop-memory/serving-floor.qwen3.8-27b-q8-gpu-dflash2-np4.json`
  reads **7.897% p95_dev, unit `process`, n=24, 95% bootstrap CI [5.520, 11.322]%** (descriptive), with
  median 160.18 tok/s, cv 4.473%, and range 147.53–174.63. Residency is proven 24/24 and
  `recipe_hash` is `29fbffc56cd7`. It was built on `build-fold-ef81196d5`.
- **Compared with the stored n=10 value:** 4.581% stored (4.494% recomputed). That value lies
  **below** the new CI. The new floor is 1.76× the old one. Window, harness and build all differ, so
  this is not a measured degradation.
- **Verified today:** `instruments.read_floor(..., effect_unit='process')` returns
  `FloorReading(floor_pct=7.897, provenance='verified')`.
- **Why not re-run:** the host has not rebooted since 2026-08-13 (`uptime -s`), so the floor is still
  valid on its own terms. The post-BIOS repeat is R23-61b, gated on the operator's reboot. Everything
  below uses 7.897%.
- **Handoff:** no box ticked by me. The `/workspace` copy is stale against the lane, which carries the
  tick.

## 2. INF-62 SL-1: DONE (box ticked)

- **Run.** `scripts/benchmark/sl1_dflash2_nmax_pmin_sweep.py`, 09:27–10:53Z. **160/160 launches ok**, with
  residency proven on every launch and the GPU claim held.
- **Evidence.** Research `6b585b58` `data/inf62-sl1-20260916/`; scratch `/mnt/raid0/llm/tmp/sub-gpu-runner-20260916/sl1/`.
- **Source findings (champion `ef81196d5`).**
  - The DFlash2 drafter's block_size is 8, so n-max 8 is clamped to 7.
  - The `is_dflash2` branch ignores `p_min`.
  - Measurement confirms both: tok/step is identical across these arms at np1 and np2.
- **Pooled medians, in tok/s** (n7≡n8, n=20):

  | in-flight | n4 | n6 | n7≡n8 |
  |---|---|---|---|
  | np1 | 59.3 | 70.4 | 77.0 |
  | np2 | 93.5 | 103.1 | 113.4 |
  | np4 | 138.8 | 153.2 | 160.7 |
  | np8 | 168.2 | 171.1 | 177.2 |

- **Estimated verify steps/s.** Flat at np1 (≈13.2–13.6). At np8 it falls with block length: 44.9 at n4
  → 36.2 at n7/n8.
- **Decision.** Keep n-max 8 (≡7). p-min is irrelevant for DFlash2.
- **Anomalies.** One launch outlier (n8-p50-np1 at 62.8 tok/s), which gives that arm a p95_dev of 18.6%.
- **Belief kernel.** Pre-hook: zero rows. Filed as the README row "sub-gpu-runner recipe sweeps" and
  task VB-GPU-RUNNER.

## Side work done while the GPU ran

- **TALE write/read adapter (VB-PRB-T4).** Added root `scripts/vidya/adapters/tale_budget_capture.py` and
  `tale_budget.py`, with 6 tests in `tests/vidya/test_tale_budget_adapter.py`. The README TALE row is
  updated. Uncommitted in root.
- **Review-F1 adapter (VB-REVIEW-F1).** Added root `review_f1_capture.py` and `review_f1.py`, with tests in
  `tests/vidya/test_review_f1_adapter.py` (13 pass together with the TALE tests). Uncommitted in root.
- **EV-13b semantic judge implemented.** Research branch `sub/gpu-runner-ev13b-20260916`, commit `0627a5d9`:
  - `semantic_judge.py` and `ev13b_run.py`;
  - a harness fix that sends `chat_template_kwargs.enable_thinking=false`, since the top-level key is
    inert on llama-server;
  - 34 review_f1 tests pass.
  - The Augment-v1 set was fetched and verified in git-ignored `data/external`: 50 PRs, 137 goldens,
    97 scored; checksum `fa0aba78…` matches the manifest.
- **§5 MoE runner.** Moved to Option A (18d1d7c8). The thresholds are frozen verbatim in the
  fable5-window2-05 §5 #1 box as operator-approved, at 09:57Z. An approval file gates the runner.
- **Serialized chains.**
  - chain1: SL-1 → SL-5 → INF-61.
  - chain2: DF2-6 serial → PRB-T4 → CJ-1e → §5 → ERNIE.
  - chain3: EV-13b.
  - chain4: OCC-1, using research worktree `0d3ca467` and root worktree origin/main `760bf433`.

## 3. INF-62 SL-5 (DF2-6 A/A): DONE (box ticked)

- **Run.** 10:53–11:08Z, `sl5_df26_aa_control.py`. `df2_greedy_parity` ran twice on `ef81196d5`.
- **A/A is 12/12 identical for every arm** (baseline, dflash2, draft_simple) across fresh processes.
  Draft volumes are identical too.
- **Verdicts on this build.** dflash2 6/12, draft_simple 5/12. Both fail at the same index on 4 prompts.
- **Conclusion.** DF2-6 pass counts are deterministic at temp 0, so run-to-run noise is zero. The earlier
  7/12 came from `5c278648a`, a different build.
- **Evidence.** Research `416cd853` `data/inf62-sl5-20260916/`.
- **Belief kernel.** Pre-hook, zero rows.

## 4. INF-61 first attempt: FAILED; re-queued

- **Run.** 11:08–11:13Z. Every launchable cell failed my host-thread affinity gate. Pinning happened
  only via `taskset` at exec; the codified v8 `fence_threads` also re-applies `taskset -apc` after launch,
  and my driver did not.
- **Capacity skips (genuine).** np32 at L2048 and L8192: `failed to allocate ROCm0 buffer`.
- **Fix.** Research `0608f2f2`. Re-queued as chain5, after OCC-1.
- **Order deviation, stated.** INF-61 now runs after items 5–10.

## 5. DF2-6 serial-exact confirmation: DONE, hypothesis SUPPORTED (no box ticked)

- **Run.** 11:13–11:28Z on `build-champion-c463f601b-hip-20260909`.
- **Results.**
  - none A/A: 12/12.
  - serial draft-simple: 12/12. serial dflash: 12/12. Both have draft_n > 0 on every prompt, and serial
    mode is confirmed in the server log.
  - unset draft-simple: 5/12. unset dflash: 6/12.
  - At all 6 dflash first-diff tokens, the baseline token is the verify row's top-2, with margins of
    0.005–0.079.
- **Instrument gap.** `GGML_CUDA_LOG_MMVQ_ROUTE=2` still gives zero lines; the log channel is likely
  filtered.
- **Evidence.** Research `7a876f23`. The note is under DF2-8 in the DFlash2 handoff, unticked, for the
  main session to judge.

## 6. PRB-T4 first attempt: FAILED at start; re-queued

- **Failure.** `eval_tale_budget.py` needs `httpx`, and system python lacks it. All 4 suites exited rc=1
  within 2 s. The server was stopped cleanly, and no results were written.
- **Fix.** Research `91d66725` runs the harness under the research repo `.venv`, which has httpx and imports
  cleanly. Failed-attempt logs are in `prbt4/attempt1-httpx-missing/`.
- **Re-queued.** chain6, after INF-61.

## Root handoff patch (per main session)

- **Patch.** `/mnt/raid0/llm/tmp/sub-gpu-runner-20260916/root-handoff-edits.patch`, made in worktree
  `/mnt/raid0/llm/worktrees/sub-gpu-runner-root-edits` at origin/main `6e85d3b5`.
- **Contents.**
  - SL-1, SL-5 and DF2-8 are ticked with evidence, plus a pointer under DF2-6.
  - The §5 #1 Option A pre-registration block.
- **Superseded.** The `/workspace` copies of these edits.

## 7. CJ-1e GPQA-Diamond-CoT pair: DONE (ordering not resolved)

- **Run.** 11:28–14:01Z. Both arms ran at np=4 / c=49152 with no fallback, residency proven.
  - Arm A: 41.3 GiB peak VRAM. Its peak KFD count was 2, likely from my own rocm-smi sample at 12:01.
  - Arm B: 38.5 GiB peak VRAM.
- **Results.**
  - Qwen3.8-27B + DFlash2: **152/198 (76.8%)**, 28 truncated, 127.7 agg tok/s.
  - Qwen3.6-35B-A3B-MTP: **158/198 (79.8%)**, 8 truncated, 155.2 agg tok/s.
- **Paired.** 15 vs 21 discordant, both-correct 69.2%, **sign test p = 0.405**. The local ordering is
  the reverse of the vendor ordering, but it is not resolvable.
- **Thinking off.** reasoning_chars = 0 and no `<think>` on all 396 rows.
- **Belief kernel.** The SC32 rows were written by the runner.
- **Evidence.** Research `c72e5ad2`, summaries only (canary-safe). The note is in the root patch under
  canonical-judge-suite-revamp CJ-1e; the box is left for the owner.

---

# Collection phase (sub-gpu-collect, took over 2026-09-16 ~14:15Z)

## Research landing (done at the handoff)

- **Evidence commits.** Research main `8146880b` carries the evidence from `6b585b58`, `416cd853`,
  `7a876f23` and `c72e5ad2`, landed as data only:
  - `occ1_gpu_driver.py` was dropped, because it hard-codes tmp paths.
  - Each SL-5 and DF2-6 `records.json` became `records.digest.json`: the completion text and token ids
    were removed, with sha256 kept.
  - CJ-1e carries per-item ids and scores only.
- **EV-13b merge.** Research merge `59d0bc73` brings in EV-13b `0627a5d9`, which also carries prep commits
  `a454b7fd`, `e70b6974` and `b1c7dedb`.
  - Tests: review_f1 34/34, plus tale and cj_gpqa 33/33.
  - The Augment manifest is metadata only (checksums, PR titles); no golden text.
- **Runner scripts not merged.** `c2204c21`, `18d1d7c8`, `0608f2f2` and `91d66725` hard-code tmp paths.

## 8. §5 #1 MoE batched -np sweep: Q-A GO, Q-B INCONCLUSIVE ×2 (box NOT ticked)

- **Run.** 14:01–14:21Z. 25/25 launches ok. Exit marker: `S5 exit 0`.
- **Residency.** Proven on every launch: ≥102 VRAM samples each, peak 25.2–38.7 GiB, peak KFD count 1.
- **Binary and linkage.**
  - The binary sha matches the prereg (`5801cd74…`).
  - The runner took no linkage receipt, so I took one after the run with ldd and the same env: PASS.
- **sclk.** 19/25 launches dipped, with a minimum of 1440 MHz.
- **Q-A: GO.** E median 1.021, n=5 pairs, range 0.993–1.063, p95_dev 4.06%. F(1) = 1.028, F(32) = 1.064,
  E(16) = 0.991.
- **Q-B: INCONCLUSIVE on both pairs.**
  - G4:Dg4: M2(32) = 0.602, M2(16) = 0.527.
  - Q8m:Dq8: M2(32) = 0.648, M2(16) = 0.577.
  - Both values are mid-band.
- **Open.** The pre-committed top-up (+5 at B∈{1,32}) was not run; the main session decides.
- **Commits.** Evidence: research `6cbdd856`. Handoff note: root `a5c9d5aa`.
- **Belief kernel.** No hook; covered by VB-GPU-RUNNER.

## 9. ERNIE MI210 ROCm rebench: f32 fix REFUTED at 1024² (box NOT ticked)

- **Run.** 14:21–14:30Z. Exit marker: `ERNIE exit 0`.
- **Admissibility.**
  - 23/23 requests returned HTTP 200.
  - The server pid was in KFD in every sample.
  - Log checks pass: MI210 device found, params at RAM 0.00MB.
- **Results.** Every cell was bit-identical across its 3 reps.
  - Patch ON: 768/896/960² are good, at 16.3/23.0/26.9 s. **1024² and 832×1248 are uniform white**
    (mean 255, sd 0).
  - Patch OFF: 896² is good at 20.3 s; 1024² is white at 26.5 s.
  - The patch costs about 13%. The 960² image was visually checked: a correct cat.
- **Next.** Recipe §5 widening. Also add a patch-OFF 960² cell, needed to attribute the 960² change.
- **Commits.** Evidence: research `cf05eefc`. Handoff note: root `befdfcdc`.
- **Belief kernel.** No hook; covered by VB-GPU-RUNNER.

---

# Collection phase 2 (sub-gpu-collect2, took over 2026-09-16 ~14:58Z)

- **Takeover state.** EV-13b reader leg running (29/50 PRs at 14:58Z; reader pid 1870037, driver 1858122).
  Chains 4–6 (OCC-1 → INF-61 → PRB-T4) are waiting on their markers. Observe-only.
- **Process note.** pid 554421 (the aku-glm53 llama-server named in the brief) is no longer running.
  Another CPU GLM-5.3 llama-server is up: pid 3096727, started 14:55Z, port 18497, from the aku12a store.
  It is not runner-owned, so I left it alone.

## 10. EV-13b run leg: the EV-6 judge-swap gate FAILS (2.94pp > 2.0pp; box NOT ticked)

- **Run.** 14:30–15:38Z. Exit marker: `EV13B exit 0`. All steps returned rc=0.
- **Residency.** Proven for all 3 servers: KFD count 1, VRAM peaks of 35.6/26.0/38.3 GiB.
- **Calibration.** Both judges are valid.
  - gemma-4-26B-A4B Q4_K_M: positive/negative controls 99.0%/100%.
  - Qwen3.6-35B-A3B Q8_0: 100%/96%.
- **Results.** Reader Qwen3.8-27B-Q8_0, 50 PRs × 3 runs, 370 findings. CANDIDATE observations; no codified
  protocol.
  - Semantic Mean-F1 with the gemma judge: 0.338 (sd 0.014).
  - With the Qwen3.6 judge: 0.367 (sd 0.021).
  - Swap delta 2.94pp, so the gate FAILS. The Qwen judge scored higher in all 3 runs.
- **Open.** Leg B (the Qwen3.6 reader) was not run.
- **Commits.** Evidence: research `aac025a4`, summaries and calibration digests only, with judge raw text
  dropped. Handoff note: root `03153379`.
- **Belief kernel.** `ingest review-f1` wrote 6 rows (18 frames) to `/workspace/.vidya/ledger.jsonl`.

## 11. OCC-1 optical context compression: NEGATIVE (box ticked; OCC-3 not triggered)

- **Run.** 15:38–16:16Z. Exit marker: `OCC1 exit 0`. The pilot came back NEGATIVE (not VOID), so the full
  run went ahead. The reader was torn down and verified gone.
- **Instrument.** Qwen3-VL-30B-A3B Q4_K_M on the champion build `b10301-ef81196d5`, MI210. Suite
  261d8ac1eaed, 1165 paired questions per arm.
- **Validity.** No VOID reasons. Residency proven: 1283/1283 samples high and in KFD, peak +20.5 GiB.
- **Text arm.** F1 0.888.
- **Image arms.** F1 0.455/0.456 (6x10 bw/color, ratio 0.326), 0.536 (8x13, ratio 0.516, NEGATIVE_COST) and
  0.364/0.363 (8x8u/12x12u, ratio 0.437). Every ΔF1 CI lies below −0.3, so none is POSITIVE.
- **Commits.** Evidence: research `84dc568d`, with records and plan digests (no SQuAD text). Handoff: root
  `844a0502`.
- **Belief kernel.** `ingest occ1` wrote 22 rows (66 frames).
- **Note.** With OCC-1 and OCC-2 done and OCC-3 not triggered, the handoff is ready for completion.
  Moving it and deleting its index row is for the owning session.

## 12. INF-61 Qwen3.8 np×depth grid at MTP n-max 8: re-collected (box ticked); below the n-max 4 grid at np≥2

- **Run.** 16:16–19:10Z. Exit marker: `INF61B exit 0`. 36/36 launches ok. Residency proven and threads
  fenced on every launch.
- **Capacity skips.** np16 @16k/32k and np32 @all L (ROCm0 buffer allocation at startup).
- **Results.** Mean t/s: np1 44.0–46.4, np2 58.0–63.0, np4 78.6–92.2, np8 95.2–112.3, np16 116.8 (2k) and
  97.2 (8k). Between-launch spread is ≤13.6%.
- **Comparison.** Versus the withdrawn n-max 4 grid, np8/2k is 112.3 vs 157.3, np16/2k 116.8 vs 153.5 and
  np2/8k 59.8 vs 66.6. That grid is cross-session, so this is an observation. An ABA is needed before any
  cells ship.
- **Commits.** Evidence: research `0a711890`, aggregates only. Handoff and vidya: root `413e88a9`.
  - VB-REVIEW-F1 ticked.
  - VB-GPU-RUNNER box filed, with §5, ERNIE and INF-61 as pre-hook sources.
  - Source row added to `adapters/README.md`.
- **Belief kernel.** No hook; covered by VB-GPU-RUNNER.

## 13. PRB-T4 TALE-EP: INCONCLUSIVE on 3 of 4 suites (box NOT ticked)

- **Run.** 2026-09-16 19:10Z to 09-17 02:22Z. Exit marker: `PRBT4B exit 0`. Served GGUF verified via
  `/props`, v9. Residency proven: 25,869 samples.
- **TALE net token change / accuracy delta by suite:**
  - math: −58.4% / +0.7pp
  - olympiadbench: −26.6% / −1.0pp
  - livecodebench: −18.6% / 0.0pp, but its accuracy is vacuous (`substring 'def '`)
- **Static arm.** On olympiadbench, static costs −12.0pp. On livecodebench, static wins.
- **Defects.** mmlu_pro failed at q1 with `ScoringUnavailableError`: the gold is 'I' and no choices are
  configured. Every sampled math item has a `gsm8k_*` id. The CPU replicate was not run.
- **Rule outcome.** INCONCLUSIVE, so the next step is a re-run at n=400 per suite once the mmlu_pro join and
  the livecodebench scorer are fixed.
- **Commits.** Evidence: research `b4d38ebc`, digests only. Handoff and vidya note: root `47816fe1`.
- **Belief kernel.** `ingest tale-budget` wrote 24 rows (math, olympiadbench). The livecodebench sidecar was
  withheld.

## Collector-2 close (2026-09-17 ~02:35Z)

- **Queue.** My four items (EV-13b, OCC-1, INF-61, PRB-T4) are collected. The GPU is not idle:
  - chain7 (§5 Q-B pre-registered top-up, `s5_topup.py` pid 2409552) started at 02:22Z.
  - chain8 (ERNIE ROCm precision-variant A/B) waits on it.
  - Both were queued after my brief and are not collected by me.
- **Leftover servers.** No runner-owned llama-server or sd-server is running. pid 910274 (prod sd-server)
  was untouched. pid 554421 was already gone at takeover.
- **Worktrees removed** (clean, HEAD on origin/main): tale-a454b7fd, cj1e-b1c7dedb, ev13b, occ1-0d3ca467,
  root-occ1, sub-gpu-collect-research.
- **Worktrees kept:**
  - `sub-gpu-runner-epyc-inference-research`: HEAD `c72e5ad2` is not on any remote (runner scripts
    unmerged), and chain7 is using it as cwd.
  - `sub-gpu-runner-root-edits`: dirty. It holds a +39-line CJ-1e note in `canonical-judge-suite-revamp.md`
    whose content is already on origin/main, so it is a superseded duplicate. Discard it, then remove.
