# autokernel-loop.md — open-box progress history (moved 2026-11-22)

Dated progress notes moved VERBATIM out of open boxes in `handoffs/active/autokernel-loop.md` so each box passes the dispatch lint (size rule e / gate-field prose). The box keeps its identity text, fields and a pointer here. Grep the box ID.

## AK-RSM-1

- 2026-11-10 PARTIAL (research `2962c4c6c`, branch `ak/rsm1-20261110`, merged into epyc-inference-research origin/main at `9c1a3a421`; box stays OPEN). `stage_receipts.py`: content-addressed stage receipts over the nine-stage graph, a file-backed graceful stop latch checked at stage boundaries, same-graph restart replay (completed stages never repeat); 9 tests pass. Remaining: (a) route the live executors through `StageRunner`, (b) wire the latch into `UnifiedCampaignDriver.tick`, (c) the versioned carry-forward receipt for graph upgrades. [no-belief: code change, no measurement]
- 2026-11-22 PARTIAL (WP4, epyc-inference-research `a902b44f0`; box stays OPEN): (b) done: `UnifiedCampaignDriver(stop_latch=StopLatch)` honors the file-backed latch at every tick stop boundary (test_unified_driver +2, 31 passed with test_stage_receipts). (c) already exists: `stage_receipts.carry_forward` (versioned, deployment-identity-preserving) since `2962c4c6c`. Remaining: (a) route the live executors through `StageRunner`. [no-belief: code change, no measurement]

## AK-PM-17-S1

- 2026-11-22 (WP4, epyc-inference-research `a2a247f15`; box stays OPEN): the planner prompt now asks for `expected_outcome` {direction, min_effect_fraction} and says it is scored as diagnosis accuracy and never changes gating; pinned prompt digests in test_actor_context updated deliberately (prompt change for review). Remaining: coverage above 0% on new rows (needs a campaign). [no-belief: code change]
- operator 2026-11-22: keep in the planner for the next loop launch (prompt digest change accepted) [no-belief: operator decision]

## AK-lineage-S3

- 2026-11-22 (WP4, epyc-inference-research `bf2875a3a`): run.py's run-end `publish_lineage` now also calls `publish_lineage_taxonomy` -> `lineage_taxonomy_wire.publish` over `<store>/experiments.db` (observation only, never raises); test_lineage_taxonomy_run_end 3. [no-belief: wiring]

## AK-integrity

- *(2026-11-22, p4)* CHECKPOINT (box stays open): epyc-inference-research 7db3ae76a `loop/integrity_pack.py` adds the fail-closed fresh-input-per-timed-run recheck, unified static blocklist (RVP-C6-9 + SOLX) and the scoped sealed-anchor divergence search with the V-D gain-loss recorded as PRE_REGISTERED_COST; 22 tests. NOT yet in the C6 verify path (needs a gates/bench/run import owned by others). [no-belief: checkpoint]
- 2026-11-22 (WP4, epyc-inference-research `1741e983e`; box stays OPEN): the static blocklist is in the C6 verify path: `integrity.validate_candidate` refuses on the RVP-C6-9 classes plus all 11 SOLX detectors (same set as `integrity_pack.static_blocklist`). Waiting: the fresh-input-per-timed-run recheck needs per-timed-run `input_seed`/`input_digest`/`output_digest` receipts that `bench.py` (WP2) does not emit yet. [no-belief: code change]

## C10-GPU-GREEDY-AA-QUALITY

- 2026-11-22 (autokernel, P2): ROW PUBLISHED `ak-c10-greedy-aa-quality-20261122` (A/A-rate protocol of docs/design/spec-decode-run-nondeterminism-20261122.md sec 3; the divergence half is explained there by float atomics, so this row asks only the quality question). Q38FN UD-IQ4_XS on C12 `457d5fc52` (hardlink of the r5 BASE HIP build, sealed digests, no build), `-ngl 99 --n-cpu-moe 48 -t 8`; arms BASE and NOATOM (r5 F 0.33 / 0.78) x 3 identical greedy runs x 40 gsm8k items; metric: per-run accuracy and per-pair |dacc|, answer-flip rate and F. Rule: QUALITY_NEUTRAL iff max pair |dacc| <= 1.96*sqrt(2p(1-p)/40) in both arms and no degenerate reply; QUALITY_AFFECTED_<arm>; NO_A_A_SIGNAL if no text divergence. Shape gpu-q3, rank 30, 8 threads, est 3000 s (need ~2400 s + 25%); GPU smoke queued. [no-belief: row published, no run yet]
- 2026-11-22 (autokernel) row `ak-c10-greedy-aa-quality-20261122-r2`: **QUALITY_AFFECTED_BASE**, filed **fail** (RESULT.json sha256 `de2ba43e1c6c949c3beaa6e89b99686bd70459c7af05d71a3e6f0b90e47daff3`). Box stays OPEN: its premise (quality-neutral near-tie noise) is falsified. BASE accuracy 0.05 in all three runs (the same 2 short items right), with 30-33 of 40 replies per run falling into phrase loops, e.g. "$2 per egg sold × ...". There are no empty replies and no NaN/Inf. Loop onset clusters just past absolute position 256 (prompt plus generated tokens, mostly 255-300), which is where n_kv steps from 256 to 512. NOATOM accuracy 0.70, 0 loops. F: BASE 0.31-0.34, NOATOM 0.49-0.57. Four of the five NOATOM knobs never run in this config: Q8_SKINNY needs ne11 5..16 (`mmq-q8-skinny.cu:75`), so the unordered atomic at :242 is not reached; Q8_WVSK needs 5..11, while ne11 here is 1, 4 or 69-110; TOPK_ASM has no (512, k=10) code object; TOPK_RADIX needs ncols > 1024 (`top-k.cu:203`). That leaves the `GGML_CUDA_DISABLE_FUSION` set (`ggml-cuda.cu:3414`). H14 is default off since C7, so the fusions live in BASE are AK-H15, the GDN cache fusion, the C12 rms_norm+mul and the upstream fusions. Production v10 is not exposed: its GPU store has none of the four atomic knobs and no H14/H15 strings, and Q38FN serves on the v10 CPU build (:8074). Child C10-GPU-FUSION-LOOP-BISECT names the fusion. [belief: cc]

## C10-GPU-FUSION-LOOP-BISECT

- (moved from the `rule:` field, 2026-11-22) r2 first-20 reference: (r2 first-20: BASE loops 15-16, acc 0.05; NOATOM loops 0, acc 0.55-0.60)
- 2026-11-22 (autokernel): row dir PREPARED, NOT PUBLISHED (the operator decides): `/mnt/raid0/llm/tmp/ak-c10-fusion-bisect-20261122` (job.py pre-registered rule, sealed BIN/SOURCE sha256, spec.json shape gpu-q3 rank 20, port 18955). [no-belief: row prepared, not published]
- 2026-11-22 (autokernel wrap-up): published per the handback ledger (22:5xZ, after the operator's exposure review). C18 must not promote before this verdict files. [no-belief: not-a-result]

## AK-ASM-T1-SPILL-R3

- 2026-11-22 (autokernel, P2): r3-20261121 (`ak-asm-t1-harness-r3-20261121`) judged NOTHING (NOT_JUDGEABLE_JIT_TIMEOUT), and the diagnosis was wrong: fmoe-16bit did not compile for 3600 s, it WAITED on a stale root-owned lock FILE `aiter/jit/build/module_moe_asm/build/lock` (dated 2026-11-06, inherited by cp -a; log line "waiting for baton release at .../module_moe_asm/build/lock"), which the harness `clear_stale_locks` never saw (it globs `build/lock_*` as the host user). ROW PUBLISHED `ak-asm-t1-harness-r3-20261122` (supersedes it): each unit container now moves every `*/build/lock` older than 30 min aside as root before the test. No JIT pre-warm and no build claim were needed. Shape: plain `gpu` (regions mi210_0,184-191), because `publish_row.py` REFUSED gpu-q3 for it: "REFUSED: non-timing GPU row books q3 cores: q3 CPU use runs in parallel with non-timing GPU work; use the plain gpu shape (regions mi210_0,184-191, --class gpu --no-fold-siblings). A timing row declares it: --role bench, admission_class block-timing-pairable|block-timing-quiet, or timing: bench|profile|ak-keep-gate; else shape_override". rank 30, 8 threads, est 4600 s (r3-20261121 booking, +25% already included); GPU smoke queued. [no-belief: row published, no run yet]
- 2026-11-22 (autokernel): row `ak-asm-t1-harness-r3-20261122` ended rc=0, FILED `fail` (RESULT.json sha256 1bba5706db7c74dd2f8975e3d1a3c93be549b020c5decd636f49eed4da62f7db; no top-level verdict, derived per this box). Spill unit fmoe-g1u0-int8smoothquant-id1024 = CORRECTNESS-FAIL: `fmoe_bf16_pertokenInt8_g1u0_vs_smf_silu_1tg_32x512.co` loads on gfx90a then HSA_STATUS_ERROR_MEMORY_FAULT, 0 family checks (harness label 'vacuous' is a mislabel of a real crash, never a pass; no r4 needed). fmoe-16bit PASS (max_abs 48); fmoe id384/g1u1-smoothquant/g1u1-int8quant PASS. Regression: topksoftmax, pa, mhc_seam, i8gemm PASS; bf16gemm-bf16out FAIL (2/2, max_abs 4.0); fmha_v3_fwd not exercised (invalid argument for fmha_fwd). Box stays OPEN: only 2 spill units have harness cases, not all 53 spill .co. [belief: cc]

## AK-EFF-KEEP-PATH-TIMING

- 2026-11-09 audit: code landed (research 2fd17033f, `epyc-inference-research/scripts/kernel_rnd/autokernel/loop/keep_timing.py`), but no store holds a `keep_path_timing` row, so the stop rule (recorded on the next keep) is unmet. [no-belief: audit]
- Owner: AutoKernel (operator ruling 2026-11-07, relayed by Pipeline Management: "AK tooling should be owned by the autokernel session"; Pipeline Management keeps keeper/rowflow/status-surface plumbing on request). [no-belief: ownership routing]
- 2026-11-22 (WP4) duplicate-build evaluation, code reading (`loop/run.py` promote_anchor -> `pool.promote_anchor` clean build, then `anchor.verify` incremental build of the same commit): the second build is the anchor guard's independent rebuild whose object digest is compared to the promoted clean build, so it is the guard's proof and cannot be removed without removing the guard; it is already the cheap side (incremental, minutes, since 2026-09-06; clean rebuild only on digest mismatch). Verdict: keep both. Remaining: per-stage times recorded in the store on the next keep (needs a granted campaign; loop launch held). [no-belief: code reading]

## AK-HR-3-S1

- · 2026-11-22 REVIEW PACKET PREPARED (autokernel P5; box stays OPEN, NOT ticked by the requester): review is the INF-73 loop owner's (session `autokernel-unified-20260908`). Packet with source SHAs, field list, evidence and checklist: `/mnt/raid0/llm/tmp/ak-hr3-review-packet-20261122.md`. Owed: that owner records APPROVED or findings here.

## AK-MMQ-H10a-S1

- (moved from the `stop rule:` field tail, 2026-11-22; stale after r2 publish) [no-belief: row prepared, no run yet]
- 2026-11-22 (autokernel, P2): r1 smoke FAILED (rc 3, 0 rows): its perf regex asked for m=4096 n=48..128, but the dense perf cases are n in {1,2,3,4,5,8,512} at k=14336. ROW PUBLISHED `ak-mmq-h10a-timing-csv-20261122-r2` with the regex fixed (dense `m=4096,n=(4|8|512),k=14336` + MUL_MAT_ID `n_mats=(32|128)`); shape gpu-q3, rank 30, 8 threads, est 3000 s; GPU smoke queued. Note: MUL_MAT_ID perf cases carry only f32/f16/q4_0/q8_0/q4_K/q6_K/iq2_xs, so the 7 required types are judged on the dense MUL_MAT cases. [no-belief: row published, no run yet]

## DTREE-V5I-PHASE-BUDGET-RERUN

- · result (2026-11-22): row `ak-dtree-phase-gpu-20261122-r2` filed inconclusive; phase deltas measured (T12 decode +6.02 ms [5.67,6.36], iter +6.06; T16 iter +9.97), budget doc updated; tree track PARKED confirmed (T12 +5.1 ms/round for +0.21 mean length). RESULT.json SHA-256 8b3d5f9a01b4cc3694af49ae3fdd8a346285f0b48aaecd094e4fd61b63bdfbf3 [belief: cc]
- · note (2026-11-22, P1 dedupe): served by NEW row `ak-dtree-phase-gpu-20261122-r2` (rank 30, same build 284a03e2d, A/A band widened to +-0.03 pre-registered before the run; smoke queued)

## AKU-RED-LOOP

- 2026-11-01 narrow recovery-fixture checkpoint: Research `99b9622f2780eb2b5d0ea5906e274ced7f7d07ea` gives the real interrupted-owner fixture a declared 300 s stage/1,000 s campaign bound before scheduler selection. Its retained actual held receipt was 13.493 s, exceeding the generic 10 s test budget; the scheduler correctly fenced the old fixture. Authentic non-scratch before/after controls now pass all five recovery tests without weakening ownership, receipt accounting or no-old-sample-mix checks. [Raw logs and original/new receipts](https://github.com/pestopoppa/epyc-inference-research/tree/99b9622f2780eb2b5d0ea5906e274ced7f7d07ea/artifacts/engineering/akx-runtime-recovery-20261101). The scratch-location refusal remains a valid historical-evidence gate. This parent remains open for measurement-granularity pause/yield; no production, model or deployment change and no new parent completion credit. [no-belief: fixture repair and native controls]
- 2026-10-07: **re-measured, much larger now** — `python3 -m pytest autokernel/loop -q` on research
- origin/main (`de02a21d`) shows **376 failed, 75 errors, 4556 passed** in 998s (one foreground pass).
- Triage: `/mnt/raid0/llm/tmp/ak-test-triage-20261007/TRIAGE.md` (worktree
- `research-ak-triage-20261007`). **357 of 451 (79%) collapse to ONE root cause**: commit `440b5b5c`
- ("fix disk-leak sources") changed `test_unified_planner.py`'s `runtime_anchor(target, recipe,
- tmp_path)` signature and fixed the 9 call sites inside its own file, but 7 other test modules
- (`test_cpu_profile_runtime.py`, `test_native_retention_catalog.py`,
- `test_profile_preparation_runtime.py`, `test_standalone_inputs.py`, `test_unified_driver.py`,
- `test_unified_driver_plan_versions.py`, `test_unified_worker.py`) still call the 2-arg form.
- Mechanical fix, ~30 min, test-helper only, zero production impact. Remaining ~94 split into: a
- 12-error producer-source schema-drift cluster (fixture vs `native_producer_source.py`'s closed-set
- schema, v1/v2 split from `f6e0cfe1`); two **UNCLEAR, possibly-real** clusters flagged for priority
- follow-up — `test_existing_cpu_run.py`'s per-iteration decision-sequence assertions
- (`measured_null`/`kept`/`regression`, touches `run.py` core) and
- `pool.prune_anchor_generations` call-count during legacy-keep pruning (touches `pool.py`/`run.py`
- kernel-lineage retention); two confirmed stale-mock clusters (`gpu_quiet_path` kwarg added by
- `0cb215c3`, and `test_heartbeat.py`'s brittle string-slice source guards); and an unexamined
- ~62-count long tail, largest single file `test_campaign_service.py` (13). No evidence found of an
- actual production bug in `serving.py`, `gates.py`, `longctx.py`, `model_identity.py`, or
- `serial_run.py`.
- 2026-10-07 (later): cluster 1 + cluster 4 (gpu `hold()` stub) **fixed** — research `58c86506`
- ("thread tmp_path through runtime_anchor() call sites; fix stale hold() stub"), epyc-root
- `fedc411f3`. Per-file rerun: 172 pass, 5 fail — 4x
- `test_existing_gpu_pool_uses_selected_requests_and_original_keep_owners` now fail on
- `"keep_candidate"` vs `"kept"` after the R23-44 keep-gate change (`run.py:5876`, needs an owner
- call, not a mechanical fix), plus 1 ordering flake in `test_unified_worker.py`. The full-suite
- rerun (`pytest autokernel/loop -q`, ~5000+ tests) was not completed this session.
- 2026-10-07 Codex follow-up: cluster 2 is a real producer/consumer mismatch, rather than a
- fixture-only repair. Research `62f1ac58` gives expanded raw source identity a separate v2 grammar
- while preserving exact historical v1 and unchanged response payload v1. Independent Astra
- source review PASS; old-parent live FF compatibility FAIL. Keep this writer out of the pinned
- lane worktree until a coordinated fresh parent/worker epoch; OP80's separately authorized
- next-batch FF must target its exact validated commit before v2 lands. Focused tests are queued.
- Heartbeat source guards are repaired in `52d871f9` and queued. Campaign-service long-tail
- tracing found another stale helper caller and a possible deployment package-path defect;
- those are being fixed and checked without changing grading or historical evidence.

## OAB-12

- 2026-10-31 source partial: Research 6a3981e4bd23379d57f791379f64ad07f7d334a2 publishes the prospective metrics writer extension; Git proof artifacts/autokernel_oab12_20261031/ records 34 passing controls. The exact published tree has an integrity-true private-Git native PII receipt; host-native PII capture was unavailable. Original acceptance remains open because the four OAB-9 exports are absent from recorded paths/current DB; no historical bytes are reconstructed.
- 2026-11-19 OAB-12 (2026-11-19): the exporter extension is on research main (6a3981e4). Acceptance still cannot be met: the four OAB-9 exports are not on disk (`artifacts/autokernel_ctx_ab_20260925/result-*.json` carry driver metrics, no tool parts), and no historical bytes are reconstructed. Resume on the next orchestrator-arm run, whose export will carry per-section pull bytes.

## OAB-18

- 2026-11-19 OAB-18: needs the run: enable `prefix_stable_order` for scoped REPL calls, run one scoped OAB-4 call to read per-turn uncached prefill, and compare the REPL-suite replies flag-on vs off. No code is missing; the flag exists in `src/features.py`.

## OAB-34

- 2026-09-28 (DS41-C70): DS41 hit `output_capped_empty` again at 11:23Z (batch 8, a 45.8k-char pure-reasoning
- step, `finish=length`, 0-char report). Fix applied for DS41 only: `DEFAULT_PLANNER_OUTPUT_LIMIT` raised
- 16,384 → 32,000 (research `9a64aec8`, opencode's own ceiling). This changes OAB-34's premise for the
- planner role — its default output cap is no longer 16,384 — but the cap-hit-rate measurement and the
- cross-role disposition called for above are still open.
- 2026-11-19 OAB-34 (2026-11-19): `actor_metrics` summaries now carry `output_capped_empty_rate` and `output_capped_steps_total` per role (research `a8171c0ea`). Measured on the four actor-calls logs still on disk: 0 capped of 14 calls (planner 7, author 4, critic 3). Too sparse to pick a fix; the DS41 logs behind the original report are not retained. Planner cap is already 32,000 (DS41-C70). Resume after the next batches, using `python3 -m autokernel.loop.actor_metrics <state_dir>`.

## OAB-6

- 2026-11-19 OAB-6: the utility is on orchestrator main (`10556542`: `src/prompt_builders/json_diet.py`, dedupe >=200-char repeated subtrees to `<same as $.path>`, clip prose at 500 chars, drop id fields; identity when under 4 KB or nothing repeats; 5 tests). Open: apply it where the orchestrator renders JSON context blocks (inline sections in the root prompt) and measure before/after on the DS41 planner prompt (fixture `loop/fixtures/ds41-run8-planner-prompt.txt` in research). The renderer call site is a behaviour change, so it was not flipped here.

## R18-D

- 2026-11-22 REFIT CHECK (autokernel WP2; box stays OPEN, table NOT changed): no stored pairs can refit the floor. The built-in row is keyed to DeepSeek-R1-Distill-Qwen-1.5B-Q4_K_M, whose only fresh A/A (`autokernel-r18d-pp512-v10-private-20261102`) is unpinned (sclk 800-1700 MHz), has a POST_BUILD arm-drift p 0.0095 and n=20, below the n>=24 the floor reader demands. The 27B captures (r3, r4) are a different workload, and both were refused under the operator's rules: r3 has no clock trace; r4 failed the predeclared band rule on 1 of 120 scored invocations (SETTLED pair 5, candidate, 1575 MHz against the 1580 floor; re-graded today with the job's pinned `clock_policy.band_verdict`: 119/120 scored plus 16/16 warmup in band). The brief's fallback (a CPU quarter row) was NOT published: this floor belongs to the GPU lane (`bench.CPU_LIST` 184-191, HIP llama-bench), so a CPU A/A would measure a different instrument and could not back a pp512 verdict. What remains: either the operator re-rules on r4's single 5 MHz dip (decision package), or one GPU A/A row on the 1.5B with the r4 pin, trace and band at n>=24. Meanwhile `calibrated=False` keeps prefill verdicts undecided. [no-belief: data audit, no new measurement]

## R21-5

- 2026-11-19 R21-5: STANDING by design. All pilot sub-items are done and the upstream-rebase cadence was decided 2026-11-18 (port-as-hypothesis is the standing answer); the row stays open only as the standing pipeline, with nothing left to build.

## R22-2

- 2026-11-02: the original docstring case is fixed on root main `b7e4a225c`; with both custody patches applied, the exact gate reported 66 passed / 1 failed on two newer byte-pinned, actively consumed source snapshots containing boundary references and caller-directed writes. Archiving their executable bytes to evade the scanner would weaken its invariant. The protected exemption list was not changed; resolve those findings under the existing human-only boundary, then rerun the gate. Log: `/mnt/raid0/llm/tmp/inf66-ci-ratification-check.log`. [no-belief: test result only]
- 2026-11-19 R22-2: still needs the `--calibrate-surface` floor calibration of `llama-batched-bench` (a GPU window) before any verdict may cite it; the CUSTODY-QUAL and CI-RATIFICATION children are merged here and sit behind the human-only boundary exemption list. No code left to write.
- 2026-11-19 R22-2 row (autokernel): `r22-2-batched-floor-gpu-20261119`. model: DeepSeek-R1-Distill-Qwen-1.5B-Q4_K_M (the loop's keyed calibration workload); build identity: production v10 `ffc1bac82` GPU store `llama-batched-bench` (sha 3a13b19f, HIP lib f26a166b). Same-binary A/A floor per parallel shape npl 1/2/4/8 (pp128/tg128, -fa off, -t/-tb 8): SETTLED (300 s settle, 1 warm-up) and PREHEATED (6 warm-ups), 20 measured pairs each, bootstrap p95 at k 1/3/5/9/20, residency sampler in-window at the loop's 0.25 s. The D8 post-build condition is NOT run (recorded adaptation). Raw floors land in the row's out/ only; promotion into `bench.py` stays a reviewed step. Stop-on-answer: RESULT CALIBRATED after the 4th shape. Stop-on-futility: first residency/digest/parse failure (FUTILITY_*) stops with nothing claimed; rc 75 only on STOP or deadline. Gate-class futility-only.
- 2026-11-20 (autokernel box audit) row `r22-2-batched-floor-gpu-20261119` filed **pass, CALIBRATED** (2026-11-19T02:09Z): all four npl shapes settled + preheated, 20 A/A pairs each, pinned binary/HIP digests; k=1 p95 floors settled/preheated npl1 15.61/16.41%, npl2 10.79/10.42%, npl4 7.67/8.17%, npl8 4.50/4.80%. NOT ticked: the box evaluates llama-batched-bench as the parallel-sequence surface; remaining = the reviewed promotion of these floors into `bench.py` (no post-build floor claimed). [no-belief: row verdict filed by agent]

## R22-5

- 2026-11-04 PARTIAL: `autokernel-r225-hip-build-only-20261104` PASS rc0 at `8f26e4f3`: test-backend-ops.cpp object (sha 6d6b1ee3) and gfx90a acc.cu HIP object (sha 52af2f65) built, binary sha 5e6928f0, HIP lib sha 541f4fda, build-only boundary marker present. Closes the 'complete claimed clean build' step; no execution, no numerical validation. Box stays open. Next: run the selected boundary corpus (M in 33..2048) on CPU and gfx90a against the ggml reference. [no-belief: build-only]
- M4-prefill intake relay, H5).** Validate kernels at M ∈ {33, 127, 128, 129, 512, 1023,
- 1024, 2047, 2048} — off-by-one probes around tile boundaries — in `gates.op_correctness`.
- Rationale from our own record: nearly every INF-67 fused-decoder defect (span overflow,
- conv-window layout, copy-back overrun, scratch overflows) was a boundary condition; the
- dominant defect class that kernel-isolated perf tests miss. Cheap; loop-budget cost is
- near zero if the case list lives in controller/. Source: intake-1295#record.
- 2026-11-02 proposed source only: experimental kernel `8f26e4f3a46cb79a09ed796b82f16daed3ecda63` ([proposal branch](https://github.com/pestopoppa/llama.cpp/tree/codex/r22-5-boundary-proposal-20261102)) and research `fa620eaa32677745fafdb062ed133d3838941241` ([proposal branch](https://github.com/pestopoppa/epyc-inference-research/tree/codex/r22-5-boundary-proposal-20261102)). Six op families have proposed case generators and an explicitly selected gate; unmapped CPU graph operations refuse explicit matrix requests and legacy gates remain unchanged. No complete build or test ran: two CPU builds were stopped after their region owners reported live workloads behind lost lock wrappers. No binary freshness proof, CPU/GPU numerical validation or universal coverage exists. R22-5 remains OPEN; review source, complete claimed clean build and validate the selected corpus before adoption. [no-belief: unvalidated source proposal]
- 2026-11-19 R22-5: the gate source (`boundary_matrix_correctness`, explicit requests only, unmapped ops refuse `oracle_unavailable`) was rebased onto research main as `d2f84e997` (conflict was one `strip_ansi` line; `test_r22_5_boundary.py` 6 passed, `test_gates*.py` 169 passed). Still open: run the M in {33..2048} corpus on CPU and gfx90a against the ggml reference on the experimental build `8f26e4f3` (needs a CPU region claim and a GPU window).
- 2026-11-19 R22-5 row (autokernel): `r22-5-boundary-gpu-20261119`. model: none (op-level corpus, no weights); build identity: experimental `8f26e4f3a46cb79a09ed796b82f16daed3ecda63` (v10 `ffc1bac82` + the `r22-5-v1` case set), in-row HIP gfx90a build. 18 units = {CPU backend, ROCm0, ROCm0 reference-mode (`--suite-seed 71 --autokernel-properties`)} x {MUL_MAT 36, MUL_MAT_ID 36, GATED_DELTA_NET 9, RMS_NORM 9, RMS_NORM_MUL_ADD 9, FLASH_ATTN_EXT 9} cases of M/length 33..2048. The CPU leg compares the CPU backend to tbo's sibling CPU reference, so it proves execution and agreement, not an independent CPU cross-check. Stop-on-answer: verdict after the 18th unit (PASS / FAIL(correctness) / DROP(incomplete)). Stop-on-futility: build, proof or residency failure (FUTILITY_*) stops with nothing claimed; rc 75 only on STOP or deadline. Gate-class futility-only.
- 2026-11-19 R22-5 filed FAIL_CORRECTNESS (`r22-5-boundary-gpu-20261119`): one build only (8f26e4f3a = v10 source + corpus), so `rocm` and `rocmref` are the same v10-source binary. CPU 6/6 units pass; GPU all pass except q8_0 MUL_MAT_ID n=1 k=256 at m%4!=0 (rocm: 33,127,2047; rocmref: 33,127,129,1023,2047; ERR 0.0006..1.0, set differs run to run = race). Real kernel defect, root-caused and tracked as **MMID-Q8-N1-ODDM** in kernel-champion-and-promotion.md. `rocmref` 'incomplete' is a harness defect: `tbo_parse.py` counts OK with `:\s*OK$`, but `--autokernel-properties` lines end `oracle=ggml_cpu_reference/v1 OK`, so n_ok=0 while the logs print 36/36, 9/9 x4 and 31/36. Open here: fix the n_ok regex (also accept AK_REF_V1 ... OK) in the gate/row parser, then rerun the corpus after the MMID fix lands. [belief: cc]

## R23-25

- 2026-11-19 R23-25: the classification is on research main (`531cea64a`: `controller/rung_routing.py`, size-dependent families launch geometry / occupancy / tiling go to the confirm rung, size-independent screen first, UNCLASSIFIED keeps today's screen-first; 8 tests). Not yet wired: the screen-rung selector in `loop/run.py` does not call `rung_routing.skips_screen`; wiring it spends loop-code budget (guard already reports a baseline violation) and needs the confirm-rung-only path exercised on a GPU window.

## R23-47

- 2026-11-02 operator decision: Ratify [approved, pending ratify script] (decisions-batch2-4-20261102.json)

## R23-48

- 2026-11-19 R23-48: the pure half is on research main (`a4eec04cb`: `controller/loo_arms.py` plans one arm per accumulated keep per promotion, a floor-gated judge where no floor or no effect is INCONCLUSIVE never a drop, and the `retracted_by_loo` row carrying both sample vectors; 10 tests). Open: the driver that does `git revert --no-commit <keep>` in a detached worktree, builds, and runs the paired A/B (needs builds and a GPU window), then runs it at the next champion-of-record advance.

## R24-10

- 2026-11-19 R24-10: the arithmetic and per-case runner are on research main (`27e2d6221`: `controller/multi_draw.py`, seed schedule, miss probability (3 draws miss p=0.015 95.6% of the time), draws-needed, mismatch rate with an upper bound, refusal-safe; 7 tests). Open: the physical run through `test-backend-ops --suite-seed/--repeat-suite` on ARGMAX/TOP_K at N>=100 draws per boundary case (needs the R22-5 corpus run first).
- 2026-11-19 R24-10 row (autokernel): `r24-10-multidraw-gpu-20261119`. model: none (op-level); instrument: production v10 store `test-backend-ops` (carries `--suite-seed`/`--repeat-suite`, no build) on ROCm0. 100 fresh `--suite-seed` draws (research `controller/multi_draw.seed_schedule(20261119, 100)`), one process per draw, over the default-corpus ARGMAX (7) and TOP_K (incl. 1023..2049 boundary lengths) cases; `--repeat-suite 2` once as a same-seed control, since it repeats the SAME seed and cannot draw fresh inputs. The R22-5 `r22-5-v1` set has no ARGMAX/TOP_K cases, so no claim about it is made. Stop-on-answer: verdict after draw 100 (PASS with per-case upper 95% bound, 0/100 -> 2.95%), or early FAIL at 3 mismatches in one case. Stop-on-futility: residency failure, no parsed cases, or >= 10 refused draws (FUTILITY_*); rc 75 only on STOP or deadline. Gate-class futility-only.

## R24-7

- 2026-11-19 R24-7: the detector is on research main (`4322ddb85`: `controller/keep_drought.py` K=10 pre-registered, consecutive non-keeps or window-best inside the floor, read-only experiments.db loader, plan-artifact validator, mechanical half of the 20-non-keep retrodiction bound; 10 tests). The exit criterion is NOT met: no run-18 or run-24 store is on disk (only synthetic fixtures), so the real retrodiction and the defect-naming half stay open, and no actor call is built. Resume: point `retrodict` at those stores' experiments.db.

## RKA-A3B48-D-REMEASURE

- 2026-11-19: r4 ended rc=75 before verdict; five VALID cells (rounds 1–2 complete, round 3 D4 only). No depth recommendation; resume remaining cells under the preregistered rule. results.jsonl SHA-256 71ccc863d8462f18a361f286ccfbe444ab19ddf7e870cc545a3b2a6978cb5cc3; row keep list retains results and launcher in the scratch vault on reclaim. [no-belief: interrupted run]
- 2026-11-18 (autokernel) the a3b48 e2e result above (NO_RECOMMENDATION, keep D=4) is later judged contaminated (bimodal cells, foreign CPU load unsampled), so it is not evidence for or against D=2. Contention-controlled row `rka-a3b48-d-remeasure-20261118-r2` is PUBLISHED at rank 110 (below GPU work). Box stays OPEN. [no-belief: row published]

## S3-AKU-13

- 2026-11-17 PARTIAL (autokernel, code-only; box stays OPEN): `epyc-inference-research` `f6e09036a` `goodhart_count.count_goodharted` takes the R23-48 LOO arms (keep-time effect + per-surface leave-one-out throughput) against full-bundle throughput per surface, counts keeps whose LOO arm is >= the full bundle on any surface (tie counts), records the keep-time effect beside each arm, and refuses malformed input or a surface with no full-bundle value. Tests in `test_promotion_goodhart.py` (5 cases). Remaining: feed it the real LOO arms and put `goodharted_count` on the promotion record (needs a promotion run). [no-belief: tooling landing]
- 2026-11-18 (autokernel, AKU bulk pass) PARTIAL (code-only; box stays OPEN): research `64fc1cfc1` `promotion_evidence.compound_from_heldout(goodhart=...)` validates a `goodhart_count.v1` result and records `goodharted_count`/`goodhart` on the promotion record beside the unchanged gain (None = not measured, never 0); `test_promotion_goodhart.py` 12 passed. Needs a RUN: the real R23-48 leave-one-out arms measured on the serving and re-baselined surfaces, then fed through `count_goodharted`. [no-belief: tooling landing]
- 2026-11-19 (autokernel) real LOO row `s3-aku-13-loo-cpu-c14-20261118` published: C14 `eee3da838` full bundle F vs five CPU LOO arms (L1-L4 `git apply -R` own builds, L5 `GGML_CPY_BALANCE=0`), paired ABBA x2 per arm on P4K and P32K. model: Qwen3.8-Flash-Next UD-IQ4_XS (Q38FN) + shared MTP Q8_0. Stop-on-answer: all 40 visits -> RESULT.json arms/full_bundle in the `count_goodharted` input shape (verdict computed by the owning session, tie counts). Stop-on-futility: missing input/proof failure, or L/F < 0.90 on both surfaces in block 1 skips that arm's block 2. Gate-class futility-only; other re-baselined surfaces (GPU) not in this row. [no-belief: tooling landing]
- 2026-11-19 (autokernel) FILED `s3-aku-13-loo-cpu-c14-20261118` **inconclusive** (box stays OPEN). `count_goodharted` = 4/5 (0d270f99b, 7a5db485e, a331665d4, 4348de400 goodharted; 8b9bf3031 not). loo/full P4K/P32K: L1 1.059/1.046, L2 1.029/0.984, L3 1.077/1.004, L4 1.014/1.014, L5 0.809/0.873 (block-1 futility). Only 2 blocks/arm, no arm clears the 3.84% floor on every block and surface, and host foreign busy_p50 was 35-52% on every visit (spikes on F visits inflate L1/L3). Greedy outputs byte-identical F vs every arm. L5 (GGML_CPY_BALANCE) clearly positive. Confirmation: AK-LOO-CONFIRM-C14. [no-belief: inconclusive row verdict]
- 2026-11-22 (WP4, epyc-inference-research `55fea1913`; box stays OPEN): `promotion_evidence.compound_from_heldout(loo_record=)` now refuses a promotion record whose TOUCHED-scoped LOO block lacks the count, LOO receipts or plan, or whose count differs from the goodhart block. Remaining: a conclusive real LOO count (the C14 row was inconclusive), which needs granted rows, not loop free-running. [no-belief: code change]

## U3-DEFAULTS-b

- 2026-11-19 U3-DEFAULTS-b: partial. `controller/surface_recipes.py` on research main (`0b12baae7`): `SurfaceRecipes` keys the recipe hash by surface (CPU shim ON vs GPU not set), canonical digest, and refuses a mismatched (surface, recipe_hash) pair, an unknown surface or a missing pin; 9 tests. Not yet done: carrying it on the champion record / Bundle schema (journal `LOOP_BUNDLE_SNAPSHOT_SCHEMA`) and calling `require_match` at the measurement gate.

## U3-SEED

- 2026-11-18 operator decision (decision tool): OP-AKU-U3 approved as packaged (option A: additive versioned records, legacy preserved). Estimand/test/N/multiplicity/mean-guard are now fixed as above; p95 deviation stays reporting-only. [no-belief: operator decision]
- 2026-11-19 (autokernel) PARTIAL (code-only; box stays OPEN): research `epyc-inference-research` `4676c07b6` implements the approved rule (seeded B=10000 paired session-unit bootstrap, n>=14 else `insufficient_n`, floor and unit as inputs, one test per candidate, typed KEEP_VARIANCE/REFUSE, never overrides an effect decision). Remaining: a producer that emits `variance_input` from real paired-launch RUNTIME_CONFIG session units, and real-launch false-keep calibration (CPU A/A row `ak-cpu-aa-calibration-20261118`, unpublished). Synthetic size/power row `u3-variance-keep-size-power-20261118` published for this box. model: none (pure-Python harness row). Stop-on-answer: all 60 units (6 cells x 100 sets) give per-cell false-keep/keep rates. Stop-on-futility: missing input, or a null cell above 25% false keeps at >= 30 sets (rule too liberal). Gate-class futility-only. [no-belief: tooling landing]
- 2026-11-19 U3-SEED: no code possible until OP-AKU-U3 is decided (variance estimand/test, alpha/N/multiplicity, mean-throughput guard); `_spread()` stays reporting-only. The recommended narrow rule above stands as the proposal.
- 2026-11-19 (autokernel) PARTIAL (code-only; box stays OPEN): research `epyc-inference-research` `ee4149f75` `loop/variance_input_producer.py` `produce(record, candidate_id=, floor=, unit=)` emits the closed `variance_input.v1` from the `serving_runtime_ab.v1` record of paired RUNTIME_CONFIG launches (pairing from `launch_membership`), refusing typed (unpaired, recipe-hash/unit mismatch, missing floor, bad value, unsupported schema), n<14 through `variance_keep`'s own `insufficient_n`; end-to-end test on SYNTHETIC launches (19 tests with variance_keep). Remaining: >=14 real paired RUNTIME_CONFIG launches with a session-unit floor record for a real verdict (CPU A/A calibration row `ak-cpu-aa-calibration-20261118`). [no-belief: code]
- 2026-11-20 (autokernel) RESULT `u3-variance-keep-size-power-20261118` rc=0 complete, MEASURED **SIZE_OK_POWER_LOW** (synthetic, 100 sets x 14 units/cell): null false-keep Wilson UB95 sd1 0.070 (2/100), sd2 0.085 (3/100), sd5 0.054 (1/100), heavy-tail 0.098 (4/100), all <= 10%; power keep rate sd0.5x 0.26, sd0.2x 0.59, both < 0.8. The rule is conservative at n=14; box stays OPEN (real-launch calibration = CPU A/A row). [belief: cc]

## RKA-A3B-ROUTER-WIDE

- · 2026-11-22 (autokernel) FILED **inconclusive** (row `rka-a3b-router-wide-gpu-20261121-r2`, rc 0, build 94d5bb376): FUTILITY_INPUT why=invalid-requests at cell r1-np8-D2-UNSET (baseline arm; one reasoning request returned 70/256 tokens), a harness fault, not an answer. Op data before the fault: WIDE f32 op_gain n12 +181%, n16 +139%, n24 -55%; bf16 n12 +144%, n32 -12%. `rowflow resume` refused (row ended complete), so a rerun needs a republish with the invalid-request check fixed. [no-belief: harness fault, no verdict]

## AKU-17

- 2026-11-18 (autokernel, box note, NOT ticked): Research `d3b512b74` adds `loop/cpu_keep_bundle.py` + `test_cpu_keep_bundle.py` (13 tests): schema `epyc.autokernel.cpu_accumulator_bundle.v1`, file `accumulator-bundle.cpu.<recipe>.json` (`filename`/`write`, atomic), each keep carries `magnitude` (provisional|settled), `contention_label` (`pre-hook` can never be settled) and the producing `statistic` (only `arm_level_permutation` can settle; an effect at or below its floor cannot), strict reader re-derives the compounded figure, `cpu_keeps_in_fold` filters a fold by explicit surface. **Remaining for the tick:** write the actual per-recipe bundles for the CPU keeps currently in the fold (needs each keep's effect, label and statistic read from the journal; none invented). [no-belief: code]
