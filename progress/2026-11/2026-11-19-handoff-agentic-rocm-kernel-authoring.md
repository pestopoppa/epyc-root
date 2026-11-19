# 2026-11-19 — handoff agentic-rocm-kernel-authoring

## 02:01Z — File A3B GPU draft length and multi-slot knob sweep

Row rka-a3b-gpu-d-np-sweep-20261118-r3 completed rc=0: RECOMMEND_D2 at np4/8/16, with default-arm per-round aggregate gains over D4 of 10.15–13.58%, 11.65–13.55%, and 11.30–13.91%, respectively. DROP_MULTI: D2 knob gains +0.91%, -0.72%, -0.18%, none reaching +3%. RESULT.json SHA-256 90a803d8f0422f6f26bcf6069a4fb36e0262199d9904b71fa27e01f28e73fcd2. The mixed-prompt D4 measurements cannot be assigned to the separately indexed 2048/8192 prompt cells without inventing measurements; preserve those cells pending appropriately matched data. No recipe change made. Duplicate race-eqv-gpu-r9 event acknowledged; its verdict and follow-up were already filed.

## 02:03Z — File router-wide GPU instrument failure

Filed rka-a3b-router-wide-gpu-20261118 INCONCLUSIVE: native FUTILITY_CORRECTNESS is a parser failure; raw test log says 16/16 baseline tests passed and rc=0, with graph warmup messages separating four case lines from OK. WIDE correctness and all performance cells were not run, so no keep/drop conclusion. RESULT.json SHA-256 c457fa71b45950a43423e9b29c6ba9c5d3fa887e2fc4a6edf88e323649d1196b. Repair parser and republish on a later turn. Acknowledged duplicate c9-gemm-tile-select event; its verdict and follow-up were already recorded.

## 02:05Z — File C16 top-k staging GPU result

C16-TOPK-STAGE: DROP(FUTILITY_OP), rc=0: no engagement witness in either enabled visit, even though n=4 A/B was 1.0440; TOPK_MOE passed 320/320 in each arm, 27B did not engage. End-to-end was not run. RESULT.json SHA-256 7fa8dc2a242242a42cba61659f1caf0617f9f5438b56ec3d7a569a3792d10eff. The notified ak-gpu-signals-ctr-20261116-r2 was already filed and ticked (PASS 10/10).

## 02:07Z — File interrupted CPU draft-depth row

rka-a3b48-d-remeasure-20261118-r4 ended rc=75, no final verdict: five valid cells, two rounds complete and round 3 D4 only. Continue the preregistered measurement; no depth recommendation. results.jsonl SHA-256 71ccc863d8462f18a361f286ccfbe444ab19ddf7e870cc545a3b2a6978cb5cc3; manifest keep retains the partial data and launcher. The notified tsanfix-numeric-cpu-r2-20261110 was already filed and ticked.

## 02:14Z — Queue r5 continuation of the interrupted A3B draft-depth measurement with the five recorded r4 cells preserved.

RKA-A3B48-D-REMEASURE: queued continuation row `rka-a3b48-d-remeasure-20261119-r5` for smoke; it resumes the preregistered r4 sequence with the existing five cells (seed results SHA-256 `71ccc863d8462f18a361f286ccfbe444ab19ddf7e870cc545a3b2a6978cb5cc3`). Publisher reports queued for smoke, not yet PASS. The J64 run-end event was already filed on 2026-11-09, including its receipt and verdict; no duplicate filing.

## 02:16Z — Recognize the previously filed mutant-build event; no new result is available.

INF48-LIVE-6: dispatcher supplied the already filed `race-eqv-mutants-build-r3-20261109` event. Existing 2026-11-10 verdict is BUILD_OK, 19/19, source `36f024341`; the FILED receipt exists and the box is complete. A3B continuation r5 remains smoke-queued, not yet PASS.

## 02:17Z — Resolve duplicate run-end for rock-aiter-timing-c9-r2-20261109; existing filed verdict and receipt already complete

Duplicate run-end for rock-aiter-timing-c9-r2-20261109: previously filed PORT_CANDIDATES, 51 port cells and 7 FA recheck cells; rc=0. Existing FILED receipt dated 2026-11-09 and handoff result already recorded; AITER-PORT-1 completed. RESULT.json SHA-256 c20a7638967aa2b41edd897f4c769980b242f7a3c9e1a941e6c004fe480059f6. No duplicate tick or port task. [belief: cc]

## 02:19Z — Resolve duplicate run-end for inf48-race2-fixtures-20261116-r2, already filed

Duplicate run-end inf48-race2-fixtures-20261116-r2: previously filed and ticked FIXTURES_READY 7/7, rc=0; existing FILED receipt dated 2026-11-16. RESULT.json SHA-256 2a14f98c5d97c95d70eaffd554e451b1253489e8b09cc2100ebe22ce578ac1f5. Fixture capture is ungraded and is not a race measurement. [no-belief: duplicate event, existing verdict]

## 02:32Z — File c15-epi-q8-gpu-20261118 test-count failure

C15-EPI-Q8 row c15-epi-q8-gpu-20261118 rc=0; pre-registered verdict FAIL(tbo): 16/16 passed in both arms, expected exactly 14, zero test failures, residency proven. Decode timing and identity were not run; box remains open. RESULT.json SHA-256 edef3786d5abad18f456474fd28f61c395bae789bcf90136311bdf46f2ac41a8. [no-belief: row verdict filed]

## 02:36Z — File c6-26-corpus-repin-20261109-r3 verdict

Filed the previously recorded C6-26 re-pin result: rc=0, 26/26 runtime behaviours manifested on both ranked units; sensitivity 1.0 (11 planted), specificity 1.0 (15 clean). Receipt /mnt/raid0/llm/tmp/c6-26-corpus-repin-20261109-r3/out/receipt.json SHA-256 3dda28f7351d0e276fef0fb0f4f231f6cb0277314a211f8d002bf213ebc56bc3. The existing INF48-LIVE-1 finding already records this result; the parent remains open for other C6 work. [belief: cc]

## 02:37Z — File rock-aiter-prebuild-r4-20261105 verdict

Filed ROCK-AITER prebuild r4: rc=0, RESULT complete; 41 final modules built or cached, five build failures and one 7200 s timeout. Its ops_ready gate lists fused_moe_ck2stage, mha_varlen_ck and moe_sorting; build readiness alone does not establish runtime correctness. RESULT.json SHA-256 8373d0ad17643b98b2ba4c4ab620bf2d8c39eae7f9d765b093bc1e5baef66721; results.jsonl SHA-256 7a361491c365a628578198440d6668c6b9ebd655c6521cc1304e8fbd39261e36, under /mnt/raid0/llm/tmp/rock-aiter-gfx90a-20261105/rock-aiter-prebuild-20261105/out/. The existing ROCK-AITER-GFX90A box already records later runtime and timing verdicts and is closed. [belief: cc]

## 02:38Z — Inspect the dispatched AITER run-end and the C6 controller fix checkpoint

The dispatched vllm-aiter-gfx90a-gpu-20261111-r3 event was already filed on 2026-11-12 with its receipt and ROCK-AITER-GFX90A-VLLM tick. The existing verdict records attention KEEP (prefill 1.109x/1.103x), GEMM and RMS NO_GAIN; result SHA-256 cb663f174e9e7c98c538c088ebed0b1d6cfb8763b3ce4f82bbf11b051baeb52c. The operator parked the vLLM track. INF48-LIVE-1's typed EvidenceProducerError fix resides in epyc-inference-research; this dispatch limits edits and commits to the epyc-root lane, so that fix cannot be implemented under the current lane restriction.

## 02:39Z — Resolve the dispatched C6 native residency run-end against its existing filing

The dispatched c6-native-residency-20261109-r3 event was already filed and receipted on 2026-11-10, with INF48-C6-LIVE-PROOF already ticked. RESULT.json reports backend-matched ratio 1.0, CPU NMSE 0.000119933249, three bitwise-equal legs and KFD/VRAM residency for each; the pre-registered rule is PASS. The controller-level proof remains open after r8's untyped EvidenceProducerError.

## 02:40Z — Acknowledge the replayed C4-7 run-end after confirming the already-filed verdict

C4-7 replayed run-end acknowledged: full run rc=0, COLLECTED_ALL, nine counters present with 28,084 numeric rows each; SQ_LDS_BANK_CONFLICT total was zero. GPU residency was recorded. Existing handoff verdict is unchanged. Results SHA-256 c749f790c51306dd49ec3e43ec5ac3a3eadbcb7970f45186c048ce5623530840; CSV SHA-256 5347eb2f7c6429975c2f22e322abc19bd91a32c3667646f0c1cace6710f25f75. FILED receipt restored. [no-belief: previously filed row verdict]

## 02:41Z — Acknowledge replayed TSAN r2 run-end with previously filed race findings

TSAN r2 replayed run-end acknowledged: rc=78 gpu-fence-vacuous; results show nine reports in MUL_MAT and MUL_MAT_ID, timeouts in MUL_MAT and FLASH_ATTN_EXT, and zero reports with rc=0 for SOFT_MAX, ADD and MUL. The existing handoff records the race findings and later fix verification; this partial run does not establish a clean pass. Results SHA-256 d564f18db37bf8c9013487223264c969dfc8989839619974dd01fc8b85234604. FILED receipt restored. [no-belief: previously filed row findings]

## 02:42Z — Acknowledge replayed C10 GEMM-down build result

C10 GEMM-down build replayed end acknowledged: previously filed BUILD_OK, configure rc=0, build rc=0, source 7bcf6218bc4849dd47276078d1dd052e77e17fe1. results.jsonl SHA-256 10e6312aff244b520231a03694679cf28832a69772af2d2f8b9b69688cc9a95e. AITER-PORT-1 was subsequently completed by prefill and quality results; FILED receipt restored. [no-belief: previously filed build result]

## 02:43Z — Acknowledge replayed C10 correctness result and previously accepted addendum

C10 correctness replayed end acknowledged: native rc=75 and FAIL(witness); MUL_MAT 1202/1202, KLD -0.0 and top-1 99.997%. Previously filed witness-addendum re-score CORRECT was operator accepted, as recorded in AITER-PORT-1. Native results SHA-256 57f57112c99ed2ae784e07a49736c6286f2577145b6061076e7ee27ff1e14ca1. FILED receipt restored. [no-belief: previously filed and accepted result]

## 02:45Z — File c15-gv-bw-gpu-20261118 as an invalid automatic futility verdict and identify the required continuation

C15-GV-BW: row c15-gv-bw-gpu-20261118 ended rc=0, but its DROP(FUTILITY_OP) verdict is invalid: ratio128k is null for every arm despite complete 128k timings. All five arms passed 76/76 correctness, with variant witnesses and GPU residency. LDS alias base/variant ratios at 128k are 1.6453 (nb=1) and 1.5722 (nb=8), geometric mean 1.6083, exceeding the preregistered 1.10 futility threshold; al2 also exceeds it. End-to-end and DFlash2 were incorrectly skipped, so no KEEP/DROP conclusion and the box remains open. RESULT.json SHA-256 9ca85f68f8b5813b20373ac1f3c987fbf05e5632f6db28259a0abe07296a2fbb; results.jsonl SHA-256 980f8cf4bb27b85e8d443cc8c56f205967541d372d2af036ff9df135d184b5f6. Next: repair aggregate key selection and publish a continuation covering the missing preregistered end-to-end tests; preserve original units before any scratch reclamation. [belief: cc]

## 03:18Z — Repair C15 GV bandwidth aggregate parser and publish continuation for smoke

C15-GV-BW continuation: original parser matched kv=4 inside nh_kv=4, making every aggregate null and wrongly stopping. In scratch row c15-gv-bw-gpu-20261119-r2, anchor kv to the comma-delimited key and make missing aggregates FUTILITY_INSTRUMENT, never DROP; replay of original result units yields 128k geometric means pd2 1.02765, pd3 1.02050, al 1.60832, al2 1.59587. The row repeats the registered protocol, with the wiki prompt tokenized once before publication using C14 llama-tokenize. Published via publish_row.py; GPU busy, smoke queued, no PASS yet. The box remains open. Original row RESULT SHA-256 9ca85f68f8b5813b20373ac1f3c987fbf05e5632f6db28259a0abe07296a2fbb; continuation scripts and inputs sealed in /mnt/raid0/llm/tmp/c15-gv-bw-gpu-20261119-r2/SOURCE.sha256. [belief: cc]

## 03:32Z — Reconcile duplicate run-end event for previously filed INF48-EQV-FA-RESCALE

Duplicate run-end event for inf48-eqv-fa-rescale-gpu-20261116-r2: rc=0; existing FILED receipt and verdict dated 2026-11-16 already acknowledge it. The handoff already records the subsequent offline rescore, KEEP(CAUGHT), with six mutant-only MMA failures; RESCORE-r2.json SHA-256 232dd23a4d22290a4aa7dd5e72fe67956562089a416613954c6f11f77aaf1ef3. Original filed verdict remains inconclusive on instrumentation, including missed per-case residency; preserve that limitation when interpreting the rescore. No new measurement.

## 03:42Z — File rock-aiter-tests-r3-20261105 GPU op-test verdict

Filed historical row rock-aiter-tests-r3-20261105 (rc=0), under already-closed ROCK-AITER-GFX90A. Full-run results: passed rmsnorm, fused_add_rmsnorm, rope, gemm_a8w8_ck, gemm_bf16_tuned, paged_attn and mha_ck; fused_moe_ck2stage failed 2/2 checks each in p1 and p0, and mha_varlen_ck had 48/448 max-diff lines above 0.03; activation errored due to vacuous checks; moe_sorting was unsupported. The sorted-ids probe reports failure but its raw real-token counts are nonzero, so do not treat its label as proof of empty output or definitive localization. MHA CK passed on 12 max-diff lines <= 0.03. The timing follow-up and parent box were already completed. Evidence: /mnt/raid0/llm/tmp/rock-aiter-gfx90a-20261105/rock-aiter-tests-20261105/out/results.jsonl SHA-256 dc1deb4e8370d07b466d2814fa600f33d12f3db5e3e3aa483bb2a2cd787188e1; RESULT.json in same directory; grant rc=0. [belief: cc]

## 04:05Z — File c10-fold-build-20261109 verdict

Filed c10-fold-build-20261109: BUILD_OK (grant rc=0), source 7f1bd044b1e49a88b33460977bd96feae3db8e5c. CPU and GPU builds and configure succeeded; all recorded content markers passed, including GGML_HIP_GEMM_DOWN_TILE (2 occurrences), all four linkage checks per store returned 0, and test-hc-fuse-plan and test-fused-decode-prev-logits returned 0 on CPU. CPU and GPU build durations 130.5 s and 206.5 s. This build-only result does not establish GPU execution or performance; AITER-PORT-1 was already closed with subsequent evidence. Evidence: /mnt/raid0/llm/tmp/c10-fold-build-20261109/out/RESULT.json SHA-256 6976d2a16d755db1add3636bfc832c9ef0cb1d34b9f40c19a101fbb6dbfbf345, results.jsonl SHA-256 5bb03d522ebf1bd56817bb8e8c2c6dcf984c16f8aba19e38da87b545c42ecead. [belief: cc]

## 04:13Z — Resolve duplicate C10/C6 dispatch reprofile run-end event

Duplicate run-end event c10-c6-dispatch-reprofile-20261110-r2: verdict and FILED receipt already recorded 2026-11-10; C6-C10-REPIN is already ticked. Results SHA-256 72f949e598efe40269d9e82bd5c0d2c483633ce1f9c98cfd95a48d192436d25c: zero new C10 failures vs v10, supported/passed MUL_MAT 1202/1201, FLASH_ATTN_EXT 3094/3094, ROPE 428/428, RMS_NORM 21/21, SET_ROWS 159/159. No new result claimed.

## 04:20Z — Resolve duplicate CPU verify-tile run-end event

Duplicate event rka-verify-tile-cpu-20261117: verdict and FILED receipt already exist from 2026-11-17 and RKA-VERIFY-TILE is ticked. Five-round result SHA-256 d8cccc8eec7f9b885d8e34444b3f6ea2a61a3bb0680220d809cf42b1812bcbf2; A3B 48t 32k n3 to n4 rose about 63%; the contention-controlled follow-up is already armed. No new result claimed.

## 04:21Z — RKA-VERIFY-TILE-A3B48-E2E dispatch event was already filed and its handoff box completed on 2026-11-18; INF48-LIVE-1 requires changes in the separate research repository, outside the explicitly permitted root lane.

Dispatched RKA-VERIFY-TILE-A3B48-E2E event was already filed on 2026-11-18 with NO_RECOMMENDATION and a filing receipt; verdict SHA-256 16d8083521592a1edb97b8664b29d246a6e4d7d4177c8317bc98377651f7a56a. No duplicate filing. INF48-LIVE-1 content-hash corpus implementation requires editing epyc-inference-research, outside the permitted lane.

## 04:25Z — INF48-FAVEC-TAIL run-end was already filed and its box completed on 2026-11-18; no duplicate filing.

INF48-FAVEC-TAIL run-end was already filed with receipt on 2026-11-18. The completed handoff records clean 3103/3103 correctness and no consistent useful op-level gain; identity was inconclusive because the control also diverged. Native result SHA-256 f825d7772bdd7dab040dc7879715b2571042a817d05917dbfa25608a9cb07b19.

## 04:26Z — Resolve duplicate run-end event for already filed RKA-VERIFY-TILE GPU result

RKA-VERIFY-TILE GPU run-end was already filed and its box ticked on 2026-11-18; the existing FILED receipt and verdict are present. Native results SHA-256 e5f01894564654543c37bcf43e77fa2709f6b6be01d5d0866f97e9fc94c50d79; preregistered boundary verdict MIXED, 27B D=7 aligned, A3B has an unpredicted n=3 to 4 step at 32k. Subsequent A3B end-to-end work is already recorded in the handoff. No duplicate tick.

## 04:27Z — Resolve duplicate run-end event for already filed A3B GPU D-length result

RKA-VERIFY-TILE-A3B-GPU-E2E was already ticked and filed on 2026-11-18, including its FILED receipt. The preregistered verdict RECOMMEND_D2 found median 32k ms/token D2 9.89 versus D4 11.87, and 4k D2 9.36 versus D4 11.86. Native result SHA-256 4e5ebd79dd218d0367dcaaf27135e655658e30dc807f2c26cbd44ec92a996734. No duplicate tick.

## 04:29Z — Resolve duplicate run-end event for already filed gate/up CPU profile

INF48-GATEUP-PROBE was already ticked and filed on 2026-11-18 with receipt present. NO_CANDIDATE: CPU paired-launch upper bound 1.52% at depth 0 and 1.25% at 8192, below 2%; proxy profiler and perf caveats are recorded in the verdict. Native result SHA-256 6e12809eb65ad3af378a720975f8e8935f8457471ea936da86f897283ceb1dfe. No duplicate tick.

## 04:31Z — File completed RKA-A3B-N4-STEP GPU result

Filed rka-a3b-n4-step-gpu-20261118 (rc=0): FUTILITY under the preregistered rule. At 32k n=4, B4R2/UNSET ratios by round were 0.9604, 1.0076, 0.9880; median 0.9880 (1.2% reduction, below 5% threshold). All four correctness processes passed; all timing processes proved HIP residency. Result SHA-256 0e923c1c55ebac4976c07fa6fefe7f3613df72613e84124669507b4b8c6cd42d. The handoff already records this result, its subsequent attribution and the completed box; filed the missing receipt. [belief: cc]

## 04:32Z — File c6-admission-live-proof-r8 result

Filed c6-admission-live-proof-r8 (launcher rc=0): FUTILITY_CARRIER; validate and GPU trace passed, but the supervised controller reached the native C6 oracle and exited with untyped EvidenceProducerError, with zero admission records. The existing handoff records the inconclusive verdict; box remains open. Result SHA-256 5b7f21ddf0498445e2d2a9e6a2c3cd72c97113fd5a34b7a8b1c6c5daf414f177. Filed missing receipt. [belief: cc]

## 04:33Z — File A3B n4 trace GPU row result

Filed rka-a3b-n4-trace-gpu-20261118 (rc=0): INCONCLUSIVE by preregistered coverage rule, with trace coverage 0.670 and 0.667 below 0.70 in both repetitions. Test-backend-ops passed 27 cases; trace and timing records show GPU residency. Existing handoff records the result and subsequent completed follow-up. Result SHA-256 d9494b3e2d778e240169c1514daee32d9b8a58958bbd3c11bfe2f4bb9873fb38; filed missing receipt. [belief: cc]

## 04:34Z — File completed rka-a3b-mmvf8-e2e-gpu-20261118-r2 verdict and acknowledge its run end

Filed rka-a3b-mmvf8-e2e-gpu-20261118-r2 (rc=0): KEEP under its preregistered rule, 16/16 valid pairs in each cell and AA-calibrated identity passed. At 32k D4 K8 reduced median latency from 12.452 to 10.761 ms/token (13.58%); D2 remained faster at 9.921 ms/token. The finding and completed box were already recorded in handoffs/active/rocm-kernel-authoring.md. Results SHA-256 aaa26d5268d57ebef9353013dcc1ecd0eb00dff070a584f79a471d72f81dfb9f. Filed receipt created. [belief: cc]

## 04:35Z — File router-wide GPU run-end verdict

Filed rka-a3b-router-wide-gpu-20261118 (rc=0): job reports FUTILITY_CORRECTNESS but baseline test rc=0 and its parser missed four cases when CUDA graph diagnostics interrupted output; handoff already records INCONCLUSIVE / FUTILITY_INSTRUMENT. WIDE and timings did not run; repair parser and republish. results.jsonl SHA-256 509caa396ba7eade01f4dbad46f769f718b22cc767563dccdf855828353c0ac5. [no-belief: instrument failure]

## 04:36Z — File A3B GPU D and concurrency sweep result

Filed rka-a3b-gpu-d-np-sweep-20261118-r3 (rc=0): RECOMMEND_D2 at np4/8/16, with D2 aggregate throughput 10.15–13.91% above D4 in each unset-arm round; DROP_MULTI because D2 knob gains were +0.91%, -0.72%, -0.18%. All 36 cells present. Completed handoff box already records the result. results.jsonl SHA-256 4a6ecaa9e1c8e47707af75b19549d2fa19c55410122e0b79fcb3ae170fbab8b0. [belief: cc]

## 04:37Z — File C16 topk staging result under the registered futility rule

C16-TOPK-STAGE: confirmed the already-filed DROP(FUTILITY_OP) verdict and existing filing receipt for c16-topk-stage-gpu-20261118 (rc=0). Both knob-on op visits lacked the required engagement witness; n=4 A/B was 1.0440, and 320/320 TOPK_MOE cases passed in each arm. No end-to-end verdict was reached. RESULT.json SHA-256 7fa8dc2a242242a42cba61659f1caf0617f9f5438b56ec3d7a569a3792d10eff; handoff already records the result.

## 04:39Z — File interrupted r4 depth remeasurement result

RKA-A3B48-D-REMEASURE: r4 ended rc=75 with five valid cells: rounds 1–2 complete and round 3 D4 only. The preregistered decision cannot yet be made; the handoff already records this partial result and its filing receipt exists. results.jsonl SHA-256 71ccc863d8462f18a361f286ccfbe444ab19ddf7e870cc545a3b2a6978cb5cc3. Continuation r5 is qualified and armed.

## 04:41Z — Diagnose C15 epilogue test count mismatch

C15-EPI-Q8: diagnosed the 14 versus 16 test count from experimental source commit e0b5d2637858411bfb8b27609a2e7e199dc6f38c, tests/test-backend-ops.cpp:14194: two weight types each instantiate four normalization and four gated cases, including a 1536-wide epilogue-off normalization control per type. The row logs show all 16 for each arm. The preregistered 14-count rule still makes the completed run FAIL(tbo); prepare a new row with the correct 16-case expectation registered before execution. RESULT.json SHA-256 edef3786d5abad18f456474fd28f61c395bae789bcf90136311bdf46f2ac41a8.

## 07:28Z — File C15 GV bandwidth result against registered rule

C15-GV-BW row c15-gv-bw-gpu-20261119-r2 filed rc=0, registered DROP(clauses): alias op 128k geomean 1.5537x, all correctness arms 76/76, but all no-draft B visits lacked witnesses and DFlash2 had one B hash mismatch versus exact A/A. End-to-end performance inconclusive; DFlash2 prompt_n=4 versus registered 32768-token prime. results.jsonl SHA-256 973da60992643c6d487de839fa469b3fb2347d1a6dafea544bf680a9db2129f7; RESULT.json SHA-256 f28dbe5dfb123ec5869e15e8d5c344097908dae89cf8e87fa9fe6f6d0c09643d. [belief: cc]

## 07:31Z — Correct source-defined C15 epilogue test count and initiate fresh row publication

C15-EPI-Q8: source e0b5d2637858411bfb8b27609a2e7e199dc6f38c tests/test-backend-ops.cpp:14194 defines 2 weight types x (4 norm + 4 gate) = 16 cases, explaining prior 16/16 against erroneously registered 14; both prior arms passed and no decode was measured. Fresh row c15-epi-q8-gpu-20261119-r2 corrects count to 16 while retaining pre-registered performance and identity criteria. Publication and smoke initiated; qualification remains to be confirmed. [no-belief: source inspection]

## 07:34Z — Repair router-wide correctness parser and initiate fresh GPU smoke

RKA-A3B-ROUTER-WIDE: repaired split-line correctness parser in scratch job.py SHA-256 29d1456447605dc81589c9e8680e4c5fddee79efb5e4f8598553195d04d3db87; on the original tbo-test-UNSET.log it counts 16/16 and rejects absent or inconsistent summaries. Fresh row rka-a3b-router-wide-gpu-20261119-r2 submitted with unchanged decision thresholds; GPU smoke queued, qualification not yet established. C15-EPI-Q8 r2 smoke is also queued. [no-belief: instrument repair; no benchmark verdict]

## 07:36Z — Triage resolved row alerts and inspect router-wide smoke

RKA-A3B-ROUTER-WIDE r2 GPU smoke was running on inspection; qualification remains pending. Triaged historical alerts using filed receipts and the recorded ATT and AITER successor verdicts; ParEval r2 smoke remains unresolved and capture is partial, so its alert was not acknowledged as fixed. [no-belief: operational triage]

## 07:39Z — Repair router-wide smoke source checkout after deletion interrupted its build

RKA-A3B-ROUTER-WIDE: The r2 smoke build failed when the requested deletion of out/src overlapped its build (missing rwkv7.cpp / llama-memory-recurrent.h). Replaced the archive checkout with a detached worktree at bb3294c71b9d02fb8040a4d71dfec75f5522b4dc; updated job.py to verify commit and tree and use git worktree add --detach if absent, refreshed SOURCE.sha256, and invoked publish_row.py again. Qualification remains pending. C15-EPI-Q8 r2 smoke passed. [no-belief: operational repair]

## 07:41Z — Check router-wide smoke availability and clear resolved C6 alerts

RKA-A3B-ROUTER-WIDE r2 remains in smoke; out/src is a detached worktree at bb3294c71b9d02fb8040a4d71dfec75f5522b4dc. Acknowledged five C6 smoke alerts superseded by the documented r3 hardware results (residency backend match 1.0, NMSE 1.2e-4; corpus 26/26, sensitivity and specificity 1.0). Other mailbox alerts remain. [no-belief: operational status]

## 08:54Z — Submit router-wide current launcher for qualification

RKA-A3B-ROUTER-WIDE: rowflow reported needs-dryrun for current launcher despite earlier SMOKE_OK; submitted spec to publish_row.py for fresh qualification. Outcome pending. Historical alerts not acknowledged without resolution. [no-belief: qualification pending]

## 12:59Z — File router-wide r2 inconclusive result

RKA-A3B-ROUTER-WIDE: filed rka-a3b-router-wide-gpu-20261119-r2 inconclusive (rc=0). Both UNSET and WIDE correctness arms passed 16/16; performance rc=0 but parser recorded 1/16 baseline cells because graph warmup diagnostics split lines. No op gain or end-to-end decision can be made. RESULT.json SHA-256 f36b2a993115a9b46a2da8abab4d020eeed0753a4d4eb86ad4360c13d11b8d9d; perf log SHA-256 bb4ed960b54658412b25ee7802ae2c5ea8c9522f4f1d5b54b117ab1792bb057d. Repair performance parser and republish; box remains open. [no-belief: instrument failure]

## 13:04Z — Repair router-wide timing parser; publisher refused moved handoff box

RKA-A3B-ROUTER-WIDE moved to handoffs/active/autokernel-loop.md (rocm-kernel-authoring.md records the move). Publisher refused successor r3 because its box is no longer in this handoff; no row was published. Prepared scratch parser /mnt/raid0/llm/tmp/agentic-rocm-kernel-authoring/router-wide-r3/job.py SHA-256 06084c07cfbd1acc95619beba4d909ce73ae02168f95bf42df95d7751c7c9062: captured timing log SHA-256 bb4ed960b54658412b25ee7802ae2c5ea8c9522f4f1d5b54b117ab1792bb057d parses 16/16 unique cells, rejecting missing, duplicate and zero timings. Accidental import started an ungranted build; stopped its captured process group, verified exit, removed its worktree and build output. [no-belief: instrument repair; no measurement verdict]

## 13:06Z — File owned r6 result as inconclusive

Filed rka-a3b48-d-remeasure-20261119-r6 INCONCLUSIVE (rc 75, no RESULT.json). Five cells recorded foreign-busy p95 28.976%, 30.904%, 95.654%, 37.880%, 28.927%, all above the registered 25% threshold despite VALID labels; investigate grant/sampler accounting and validity before continuation. results.jsonl SHA-256 9f734f39169d7a5e41cfab32465f0f1619b2e37c259d2ba1b15660707d800f5d; filing receipt exists; scratch retained. Box resides in autokernel-loop.md. [no-belief: incomplete run and instrument discrepancy]

## 13:08Z — Assess C6-26 content-hash-memo implementation under lane-only worktree restriction

INF48-LIVE-1: C6-26 executable corpus change is in the separate epyc-inference-research repository, outside the only authorized lane worktree; implementation and corpus re-pin were not performed. C6 controller proof r9 is grantable after smoke PASS. The r6 A3B result was already filed inconclusive (receipt at filing-done/rka-a3b48-d-remeasure-20261119-r6.FILED); its five cells exceeded the pre-registered contention threshold despite VALID labels.

## 13:10Z — Determine whether C6-26 can be completed in the authorized worktree

INF48-LIVE-1 remains blocked by the instruction limiting edits to the root lane: the executable C6-26 corpus belongs to epyc-inference-research. INF48-C6-CONTROLLER-PROOF awaits qualified r9; INF48-FOLD-PLAN depends on C6 completion. Acknowledged r9 smoke failure after its later smoke passed, and r6 idle/ended alerts after its run ended and verdict was filed. Other mailbox alerts remain unhandled.

## 13:47Z — File C14 dispatch reprofile result

Filed `ak-c14-c6-dispatch-reprofile-20261119` **inconclusive** (rc=0): C14 store identity check stopped the run before any C14 cases or trace; seven checksum mismatches cover llama-bench, test-backend-ops, libggml-hip, libggml, libggml-base, libggml-cpu and libllama-bench-impl. No C14 baseline or dispatch re-pin is warranted. Production v10 had MUL_MAT 1073/1139 passed, 66 failed, 326 unsupported; FLASH_ATTN_EXT 2868/2868, ROPE 428/428, RMS_NORM 21/21 and SET_ROWS 159/159 passed. v10 dispatch trace SHA-256 `66954db9ee3a44b447081b96b0b6c0b7bbb6362d7c676e69aba49065ef5a2e`; native results SHA-256 `ea53416e500a3799ccea210eb35581b77c2750cb2e26bb68981be2efd0f6944f`. Filing receipt and detailed verdict under compute-flags/filing-done. Controller proof remains open; r9 is armed. [belief: cc]

## 15:12Z — File C14 dispatch reprofile r2 verdict

Filed `ak-c14-c6-dispatch-reprofile-20261119-r2` (rc=0). PASS: verified C14 source eee3da838e3c8306a856f2c72c4b04048fded698, MI210 KFD and VRAM evidence; MUL_MAT 1202/1202 passed, 326 unsupported, 0 new fails; FLASH_ATTN_EXT 3339/3339 passed, 2229 unsupported, 0 new fails; ROPE 428/428 passed, 20 unsupported, 0 new fails; RMS_NORM 21/21 passed, 0 unsupported, 0 new fails; SET_ROWS 159/159 passed, 496 unsupported, 0 new fails; C14 MUL_MAT fail multiset {}; 66 v10 MUL_MAT failures absent in C14. C14 dispatch trace SHA256 a93823a001595526f4d4bc130ea0d6f44d2afc09751d0a64424d4be9e866d32e; result SHA256 fbad484d53a252bc7596bdd6689af2df31079c1c1407984468deef112bc75cea. Dispatch tuples (kernel, calls, grid, workgroup, LDS bytes): [["void flash_attn_combine_results<64>(float const*, HIP_vector_type<float, 2u> const*, float*, int)",3096,896,64,512],["void k_set_rows<float, long, __half>(float const*, long const*, __half*, long, long, long, long, long, long, long, long, long, long, long, long, long, long, HIP_vector_type<unsigned int, 3u>, HIP_vector_type<unsigned int, 3u>, HIP_vector_type<unsigned int, 3u>, HIP_vector_type<unsigned int, 3u>, HIP_vector_type<unsigned int, 3u>)",3096,256,256,0],["void mul_mat_vec_q<(ggml_type)12, 1, true, false, 0, false, true, false>(void const*, void const*, int const*, ggml_cuda_mm_fusion_args_device, float*, unsigned int, HIP_vector_type<unsigned int, 3u>, unsigned int, unsigned int, unsigned int, HIP_vector_type<unsigned int, 3u>, unsigned int, unsigned int, unsigned int, HIP_vector_type<unsigned int, 3u>, unsigned int, unsigned int, unsigned int, unsigned int)",1548,114688,128,512],["void mul_mat_vec_q<(ggml_type)14, 1, true, false, 0, false, false, false>(void const*, void const*, int const*, ggml_cuda_mm_fusion_args_device, float*, unsigned int, HIP_vector_type<unsigned int, 3u>, unsigned int, unsigned int, unsigned int, HIP_vector_type<unsigned int, 3u>, unsigned int, unsigned int, unsigned int, HIP_vector_type<unsigned int, 3u>, unsigned int, unsigned int, unsigned int, unsigned int)",1548,114688,128,512],["void mul_mat_vec_q<(ggml_type)6, 1, false, true, 0, false, false, false>(void const*, void const*, int const*, ggml_cuda_mm_fusion_args_device, float*, unsigned int, HIP_vector_type<unsigned int, 3u>, unsigned int, unsigned int, unsigned int, HIP_vector_type<unsigned int, 3u>, unsigned int, unsigned int, unsigned int, HIP_vector_type<unsigned int, 3u>, unsigned int, unsigned int, unsigned int, unsigned int)",129,57344,128,512],["void mul_mat_vec_q<(ggml_type)6, 1, true, true, 0, false, false, false>(void const*, void const*, int const*, ggml_cuda_mm_fusion_args_device, float*, unsigned int, HIP_vector_type<unsigned int, 3u>, unsigned int, unsigned int, unsigned int, HIP_vector_type<unsigned int, 3u>, unsigned int, unsigned int, unsigned int, HIP_vector_type<unsigned int, 3u>, unsigned int, unsigned int, unsigned int, unsigned int)",6063,57344,128,1024],["void mul_mat_vec_q<(ggml_type)6, 1, true, true, 0, false, false, false>(void const*, void const*, int const*, ggml_cuda_mm_fusion_args_device, float*, unsigned int, HIP_vector_type<unsigned int, 3u>, unsigned int, unsigned int, unsigned int, HIP_vector_type<unsigned int, 3u>, unsigned int, unsigned int, unsigned int, HIP_vector_type<unsigned int, 3u>, unsigned int, unsigned int, unsigned int, unsigned int)",4644,8192,128,1024],["void mul_mat_vec_q<(ggml_type)6, 1, true, true, 0, false, false, false>(void const*, void const*, int const*, ggml_cuda_mm_fusion_args_device, float*, unsigned int, HIP_vector_type<unsigned int, 3u>, unsigned int, unsigned int, unsigned int, HIP_vector_type<unsigned int, 3u>, unsigned int, unsigned int, unsigned int, HIP_vector_type<unsigned int, 3u>, unsigned int, unsigned int, unsigned int, unsigned int)",3096,311296,128,1024],["void mul_mat_vec_q<(ggml_type)8, 1, false, true, 0, false, false, true>(void const*, void const*, int const*, ggml_cuda_mm_fusion_args_device, float*, unsigned int, HIP_vector_type<unsigned int, 3u>, unsigned int, unsigned int, unsigned int, HIP_vector_type<unsigned int, 3u>, unsigned int, unsigned int, unsigned int, HIP_vector_type<unsigned int, 3u>, unsigned int, unsigned int, unsigned int, unsigned int)",129,19447808,512,7168],["void mul_mat_vec_q<(ggml_type)8, 1, true, true, 0, false, false, true>(void const*, void const*, int const*, ggml_cuda_mm_fusion_args_device, float*, unsigned int, HIP_vector_type<unsigned int, 3u>, unsigned int, unsigned int, unsigned int, HIP_vector_type<unsigned int, 3u>, unsigned int, unsigned int, unsigned int, HIP_vector_type<unsigned int, 3u>, unsigned int, unsigned int, unsigned int, unsigned int)",1548,16384,512,14336],["void quantize_q8_1_1d<false>(float const*, void*, long, long)",15609,1024,64,0],["void quantize_q8_1_1d<false>(float const*, void*, long, long)",1548,5120,64,0],["void quantize_q8_1_1d<true>(float const*, void*, long, long)",1548,5120,64,0],["void rms_norm_f32<256, true, false, false>(float const*, float*, int, long, long, long, float, float const*, long, long, long, HIP_vector_type<unsigned int, 3u>, HIP_vector_type<unsigned int, 3u>, HIP_vector_type<unsigned int, 3u>, HIP_vector_type<unsigned int, 3u>, float const*, long, long, long, HIP_vector_type<unsigned int, 3u>, HIP_vector_type<unsigned int, 3u>, HIP_vector_type<unsigned int, 3u>, HIP_vector_type<unsigned int, 3u>)",6321,256,256,512],["void rope_neox<true, false, float, __half>(float const*, __half*, int, int, int, int, int, int, int, int, int, int, int const*, float, float, float, rope_corr_dims, float, float const*, long const*, int)",3096,256,256,0],["void rope_neox<true, false, float, float>(float const*, float*, int, int, int, int, int, int, int, int, int, int, int const*, float, float, float, rope_corr_dims, float, float const*, long const*, int)",3096,1024,256,0]]. This row is a reprofile, not the controller iteration; controller proof remains open. [belief: cc]

## 16:00Z — Assess remaining independent C6 work and controller proof availability

INF48-LIVE-1: the remaining C6-26 executable corpus change belongs to epyc-inference-research, outside this turn's lane-only edit restriction. INF48-C6-CONTROLLER-PROOF row c6-admission-live-proof-r11 passed smoke and is running; no terminal verdict is available. INF48-FOLD-PLAN depends on C6 completion. Historical mailbox alerts without established resolutions remain unacknowledged. No result-bearing task was completed. [no-belief: operational state]

## 16:01Z — Assess availability of the controller proof verdict

INF48-C6-CONTROLLER-PROOF: r11 remains running per dispatcher state; no terminal verdict is available. INF48-LIVE-1's independent C6-26 corpus change is in the research repository outside the authorized lane; INF48-FOLD-PLAN depends on C6 completion. Acknowledged the superseded ATT canary, AITER vLLM and C6 r2 smoke alerts based on completed successor results recorded in the handoff. Other unresolved alerts remain. No result-bearing task was completed. [no-belief: operational state]

## 17:22Z — Filed c6-admission-live-proof-r11 as inconclusive under its futility rule

Filed `c6-admission-live-proof-r11` **inconclusive (FUTILITY_CARRIER)**: job rc=0, trace and validation passed, but the controller completed after portfolio exhaustion with zero admission records and no typed C6 refusal; the two receipt reopenings are unproved. The controller proof remains open; stop on futility, no retry. Result SHA-256 `3027bb233b5d587752b6e90000c74279f0a8a6f7b6bd1a84ac8a91534a2aa992`. [belief: cc]

## 17:52Z — File c6-admission-live-proof-r12 diagnostic typed refusal

`c6-admission-live-proof-r12`: **PASS as diagnostic DROP**, `C6_ITERATION_C6SplitPolicyRefusal`; failed leg `precision_equivalence`, zero admission records. Trace and validation passed, with KFD present and 1,403,559,936 B peak VRAM. The refusal precedes sealing a successful new C6 correctness receipt; do not infer candidate admission or successful receipt reopening. The controller proof box remains open pending evidence for its receipt-reopening condition. Result SHA-256 `ae42d37b71fc6eba0d6343b945170abd7dc1f6ca5972e47bf4a1713c2ba626c0`. [belief: cc]

## 18:04Z — Assess r12 C6 receipt reopening boundary

The r12 typed `C6SplitPolicyRefusal` was raised while evaluating candidate outputs, before `_validate_c6_correctness_receipt` runs in the split execution path. This establishes that a newly produced successful C6 correctness receipt was not reopened in that iteration; it does not establish whether both historical native PASS receipts were reopened elsewhere. The controller proof box remains open. Execution closure `gpu_source_evidence.py` SHA-256 `57d846611a4fe9148164775449d668b20adeddc28bec74a9c0e723793d307f21` binds the source; result SHA-256 `ae42d37b71fc6eba0d6343b945170abd7dc1f6ca5972e47bf4a1713c2ba626c0`. [belief: cc]
