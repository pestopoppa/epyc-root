# Handoff note draft — SPEC-GRAM.3 r2 CPU repair

Target active task: `handoffs/active/speculative-decoding-mtp-refresh.md`, existing SPEC-GRAM.3 task text (leave its checkbox and ownership unchanged; main applies any handoff edit).

Prepared a fresh r2 packet with canonical v14 source pins, a dynamic CPU claim, the unchanged science job, and fail-closed production qualification. Test evidence is limited to canonical dynamic-CPU parsing and explicitly nonproduction fixture behavior. `job_entry.sh` rejects production qualification until the real same-job native first-compute/result-writer/STOP path is implemented; the direct fixture rejects `production=true`, missing `production`, and string `"false"`. No science result, READY, official grant, or HARD receipt is claimed. The actual model is 37.8 GB with prior peak RSS near 37 GiB, outside R11 <=8 GiB; do not run it under that cap.

Next action for the row owner: at an eligible keeper/resource boundary, install/verify the published v14 bundle, implement/qualify the actual same-job native qualification within the approved resource envelope, then obtain real 24-thread same-job throughput evidence before considering a fresh row arm. Keep r1 FAILED/FILED history and the 24.86 ms proxy characterization unchanged.
