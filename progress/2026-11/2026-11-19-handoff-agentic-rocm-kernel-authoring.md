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
