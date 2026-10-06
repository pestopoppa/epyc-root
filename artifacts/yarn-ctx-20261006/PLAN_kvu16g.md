# KVU-16g: remove the solo-prefill TTFT cost of -b 512 -ub 512 on :8083 (plan; no kernel code)

Cost (PACKAGE.md A-4 / 8.3 item 12): solo req 0 prefills 383.8 vs 518.0 tok/s (-26%), TTFT 208.3 vs 154.2 s (+35%) at ~80k. Cause: each 512-token ubatch pays the fixed per-iteration/per-graph cost (n_kv-wide FA setup, mask, drafter pass) ~4x as often.

## Already built (this is NOT a new design)
KVU-16g = Sarathi-style decode-aware prefill budget, already implemented and CPU-validated:
- branch experimental/prefill-budget-on-fold-20261004, commit 65d48a7a0 (build 10312, store builds kernels/builds/{gpu,cpu}-20261004-65d48a7a0), worktree /mnt/raid0/llm/llama.cpp-experimental-prefill-budget-on-fold-20261004; doc /mnt/raid0/llm/tmp/prefill-budget-20261004/FOLD.md.
- Mechanism: --prefill-budget-decoding N: only while some slot is SLOT_STATE_GENERATING, cap prompt tokens per server iteration at N; with no decoder, full n_batch chunks. --prefill-budget-target-ms MS: adaptive (EMA ms/token, floor 64). Default off = no behaviour change.

## Where it lives
Kernel side (champion/experimental llama.cpp branch, becomes part of the next v11 candidate; production v10 is FROZEN): common/arg.cpp + common.h (flags), tools/server/server-context.cpp (prefill_budget_get(), prefill_budget_on_iter(), n_prompt_limit in the batch-fill at ~L3281, per-iteration log line), tests/unit/test_prefill_budget.py.
Orchestrator side (only after a v11 with the flag is in the kernel store): serving_shape fields + argv compiler in orchestration/model_registry.yaml and the launch renderer (orchestrator_stack.py) to emit --prefill-budget-decoding 512; vram_non_kv_gib/vram_non_kv_ubatch re-derived (below).

## The real design constraint (do not skip)
The budget only restores solo speed if solo chunks are LARGE, i.e. -b/-ub 2048 again. -ub fixes the compute-buffer reserve (target+drafter), which is the 2.96 GiB the :8083 package saved. So:
- Option A (fold as built): -b 2048 -ub 2048 --prefill-budget-decoding 512. Solo TTFT = baseline, neighbour-beside-decoders keeps 512-row iterations. Costs back +2.96 GiB (projected runtime peak ~59.8 vs 56.8 GiB; headroom to 62.00 gate drops to ~2.2). Probably unacceptable unless KVU-16h shrinks the runtime growth first.
- Option B: -b 512 -ub 512 stays; the budget is moot (chunk already 512). Remove the solo cost differently: intermediate -ub 1024 (mask/compute halfway, ~-1.5 GiB) with --prefill-budget-decoding 512 (a budget below n_ubatch still splits). Measure the ub 1024 point.
- Option C (code, needs approval): allow the solo path to submit n_batch > n_ubatch worth of tokens without extra per-ubatch overhead (fuse per-graph fixed costs) or reserve-at-max with dynamic n_ubatch: no VRAM gain, so only worthwhile if A's headroom is the blocker.
Recommendation: run the A/B with arms off / b512 / pb512 / ub1024+pb512; decide on the measured ratio of (solo TTFT cost) vs (VRAM peak). Decision belongs to the operator only if headroom vs TTFT trade is close; otherwise pick the arm that keeps runtime peak <= 58 GiB.

## GPU test plan (park/lock pattern, same as E1-MEM)
Existing harness: /mnt/raid0/llm/tmp/prefill-budget-20261004/gpu_slot.sh (own server :18093, :8083 shape, refuses if >2 GiB VRAM used, 45 min cap). Backlog item 5c in backlog-schedule-20261004.md. Wrapper to run:
  OUTER: region-lock run --gpu-quiet exclusive --tag ec-kvu16g --timeout-s 3600 -- /bin/bash <inner>; AFTER it returns: gpu_window restore.
  INNER: gpu_window park --ports 8083 --expected-end +60m; wait KFD empty; ARMS="off b512 pb512" NEW=/mnt/raid0/llm/kernels/builds/gpu-20261004-65d48a7a0/bin DEPTH=20000 NEIGHBOUR=80000 MAX_MIN=45 bash gpu_slot.sh; VRAM sampler per arm (PACKAGE 8.2(a)).
Add the ub1024+pb512 arm to arm_args() in a COPY of gpu_slot.sh (do not edit the original while others may run it).
Pass criteria: solo req-0 TTFT/prefill within 5% of off (518 tok/s); neighbour-beside-decoders decode tok/s >= b512's; per-arm KFD peak recorded; greedy text identical across arms on the coherence prompt; no ps -p survivors.
Caveat: the build is 65d48a7a0 on the champion fold (10312), not v10 (10303); the result is a v11-candidate measurement, not a v10 one.
