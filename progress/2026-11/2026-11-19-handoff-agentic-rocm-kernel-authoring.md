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
