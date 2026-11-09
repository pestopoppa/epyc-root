# 2026-11-09 AutoKernel

## LB3.2 re-pinned to C8; pair invalid

- r4 refused rc=6 before any arm: champion had moved 17 commits past C7r 62cb6a6af. Operator chose to rebase.
- New package `/mnt/raid0/llm/tmp/akx-lb32e-20261109`: G = store image `cpu-20261108-1bda248e3-c8rbseq`, M = clean 1bda248e3 with GGML_CPU_PROF=ON, champion guard relaxed to descends-from.
- Result PAIR_INVALID: GM SPLIT_UNRESOLVED (max F 9.54%, max S 51.9%, seed `node:norm`); MG INVALID on the 5% overhead gate (N=3 +8.77%, N=5 +5.21% at 64k). No retry under the one-fixed-pair rule.
- Filed under AKX-ALL-LB3.2, not ticked.

## LB3.2 median-overhead pair: order-sensitive

- Fresh pair lb32-c8m-20261109 under `AMENDMENT-median-overhead-r6.md` (median 64k overhead gate, seed-stability rule).
- PAIR_ORDER_SENSITIVE: GM LANE_LARGE (max F 10.14%), MG SPLIT_UNRESOLVED (max F 9.35%); max S about 52% and seed `node:norm` in both. Stop-on-futility, no retry.
- Filed under AKX-ALL-LB3.2, not ticked. Corrected the earlier arm-order remark to the single-repetition spike finding.

## Operator wrap-up

- Wiki sweep: tracked delta (6 sources) compiled into `wiki/hardware-optimization.md`; prune candidates none; README and belief ledger fresh.
- Derived actionables, explicit declines: (1) no box for a new LB3.2 predeclaration handling F near the 10% line, because the operator gates any further attempt; (2) median-gate branch `ak/lb32-median-overhead-20261109` not merged, because the pair did not decide and no consumer exists.
- Kept: `ak-lb32e-msrc` (named by the r5 package, gate refused), `ak-lb32f-rsrc` (branch unmerged). Result ticks this wrap-up: 0.
- Session bus drain refused: `autokernel` is not a roster id in config.yaml.

## Wrap-up 2 (operator-invoked, WRAPUP_AGENT_ID=autokernel)

- Loop test `ak-fulltest-c9-20261109`: r1-r4 failed startup gates; r5 ran one iteration live and the planner abstained (filed ABSTAIN; handoff box AK-FULLTEST-C9). Proof rows `ak-q38fn-relianceproof-c9` r1 (old COR), r2 (root repo env), r3 (HostDegradedDuringCalibration, pairs 10-14 and 18-20). No planner turn ran; VB-REFOCUS-NONEMPTY-READ-PROOF is still open.
- Q38FN floor on C9: r3 FAIL_WINDOW (degraded host); r4 FUTILITY_NOISY_NOT_REGISTERED at 12:57Z (64k 1.448%, serving 4.07%, both suspect). Cause undetermined, reaper is the lead. Diagnostic row `ak-q38fn-reaper-diag-c9-20261109` is queued by the operator's account (earliest about 19:30Z); I did not find it in any handoff or queue file, only its scratch dir `/mnt/raid0/llm/tmp/ak-reaper-diag-20261109`. Its reaper guard must require a future stamp after its smoke. Filed AK-Q38FN-REAPER-DIAG.
- Candidate `akm-cpu-iq3s-iq1-zmm-dot-gather`: BIT_EXACT_PASS, row `ak-iq3s-zmm-oracle-20261109-r4`, commit `fc71ff076` on the local experimental branch (already ticked in the handoff).
- Planner-only live 27B turn authored `akm-gemm-m10240-halve-tensile-cell` citing zero claims; report `/mnt/raid0/llm/tmp/ak-planner-only-27b-20261109/planner-only-report.json`. Branch `ak/planner-only-20261109` (`0358db7a3`) is 1 commit ahead of origin/main, unmerged pending code-budget approval.
- Belief audit: 16 is the TIER_CAPS target cap; 0 of 37 receipts declared reliance. Fixes: root `ce1eda82b`, research `952c4d859`, both on origin/main. Partial-floor fix `dffb3db37` also on origin/main.
- Unmerged: `ak/next-code-20261109` (6 commits, tip `08aa0938b`), tests pending. Cgroup row failed its smoke on a fixture without `cgroup.kill`; fix pending.
- Operator decisions today: critic default Fable medium; DS41 floor goes with its launch; AKX-P1b closed; LB4.9 per-route bitwise; H7/H8/WM-2a closed; non-inference work stays on the q3 partial cores during quiet-host runs. Not re-ticked here: no new evidence was produced in this wrap-up.
- Pending operator ratification command (not written): AK-FUSE-GRAPH-KLD-1 threshold, 35 code-budget exceptions, planner-only budget entries.
- Handoff edits: boxes added AK-Q38FN-REAPER-DIAG, AK-NEXT-CODE-MERGE, AK-CGROUP-FIXTURE-FIX, AK-PLANNER-ONLY-MERGE; floor box got r3/r4 sub-bullet. Checkbox flips: 0 ticks (no evidence). Belief-capture check clear (0 violations).
- Session bus drain refused again: `autokernel` is not a roster id.
- 2026-11-09 operator exception for row `ak-q38fn-relianceproof-c9-20261109-r4`: "OP-AK-HOLD exception: I authorize one AutoKernel loop turn on Q38FN UD-IQ4_XS CPU at C9 d210f85c2, row ak-q38fn-relianceproof-c9-20261109 (next revision after r3), regions 0-95, one iteration, critic claude-fable-5-1 medium, for VB-REFOCUS-NONEMPTY-READ-PROOF only. The hold otherwise stays in force."
