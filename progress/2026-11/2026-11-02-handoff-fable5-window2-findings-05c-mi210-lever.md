# 2026-11-02 — handoff fable5-window2-findings-05c-mi210-lever

## 00:04Z — Prepare GPU VL prefill and CPU candidate inference rows

GPU VL vision-encoder prefill is the priority because the GPU ready inventory is empty. Dispatched bounded independent assessments of runnable VL inputs and launcher, measurement protocol, and CPU candidate rows. Awaiting their report files registered under this session’s awaiting directory; no row has been published and no compute was launched. Next: integrate the assessments, prepare any required inputs, and publish the GPU row if its specification is supported.

## 00:05Z — Prepare inference rows for the MI210 category matrix

The prior preparation commit reached origin/main. The earlier assessment outputs were absent on resume, so three independent bounded jobs now prepare the VL GPU baseline, Q4_K lever, and auxiliary baseline candidates, with output events registered. The handoff identifies L21 as a GPU GDN-hybrid lever (§3.4), despite the generated backlog tagging it CPU; the auxiliary parent includes the already-run BGE half and the open VL half, so avoid publishing a duplicate BGE row. No row is claimed published until its preparation outcome is received. Next: integrate and review the results, publish any complete rows, and record their IDs.

## 01:28Z — Reconcile MI210 inference tasks against existing evidence

Read-certification: BGE encode is already measured (13 GPU points, commit 182f30b6); the auxiliary parent and VL child require one remaining VL baseline, not duplicate BGE rows. The local Qwen3-VL 30B Q4_K_M and F16 projector exist; no reusable encoder-only timing harness was found, and an F16-only projector cannot establish a quant crossover. Dispatched a bounded harness and row-spec preparation task, with a completion event registered. Q4_K is a GPU kernel candidate, not a CPU flag-flip: the matched diagnostic rejects the old +43% projection, and the correctness-passing branchless candidate needs the clean replay owned by mi210-q8-dequant-gemv-roofline.md. Updated the handoff to preserve these corrections. No row published or compute launched. Next: integrate the VL harness result, validate its measurement scope and publish through rowflow; coordinate Q4 clean candidate with its owner.

## 01:31Z — Prepare VL baseline and repair stale index rollup

Previous wrap-up stopped at index freshness; regenerated index state, graph and master rollup. Confirmed production libmtmd contains the native image-slice encoder timing string, separate from decoder processing. VL harness preparation is delegated and its outcome event registered; no compute or row was published. INF-37 owns the Q4_K branchless work; its v9 patch is preserved under autokernel/preserved-uncommitted-20260823 and the clean replay is gated by OP-15 and a governed runner. The auxiliary baseline parent overlaps the VL child, with BGE already measured. Next: integrate and publish a verified VL row when the harness outcome arrives.
