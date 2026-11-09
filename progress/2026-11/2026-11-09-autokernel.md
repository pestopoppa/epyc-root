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


## Wrap-up 3 (operator-invoked, WRAPUP_AGENT_ID=autokernel, branch ak/wrap-20261109c)

- Ratifications signed today: RATIFY-AK-Q38FN-FLOOR-ACCEPT-20261109 (root `53172736b`; research `a7b94d516` serving floor 4.146%, `b63ce0107` 64k floor 1.448%; both accepted as suspect) and RATIFY-AK-C9-2-20261109 (root `1702d7bb0`, research `eb9be38dc`: 120 MHz GPU clock band, R18 manifest, code budget, retired and planner-cpu merges). All five commits are on origin/main.
- Proof row `ak-q38fn-relianceproof-c9-20261109-r4`: smoke PASS 20:40Z, manifest in `ready/`, not started. OP-AK-HOLD exception recorded in `9d1fa3d40`. It uses the suspect 4.146% floor, so a keep is possible but private and untrusted. r3 died of HostDegradedDuringCalibration, likely the disk-janitor reap (guard fix `9d597d559`, not proven). VB-REFOCUS-NONEMPTY-READ-PROOF stays open.
- `ak-kernel-h5-verify-c9-20261109` (AK-H5-VERIFY): verdict **UNDERFILL**, diagnostic, not a keep claim. h5 correct on 31/31 cells; h5 heads32/heads16 at nb512 kv16384 = 1.0547 (< 1.5), heads64/32 = 1.9113, nb2048 heads32/16 = 1.5733. Filed `inconclusive` through `file_result.py` (the box text names only SCALES or a clamp bug as the answer; UNDERFILL was added by the PREREG before the run). Box NOT ticked.
- `ak-lb49-sinks-gate-c9-20261109` (AKX-ALL-10.1 / LB4.9): **BITWISE_WITHIN_ROUTE_MISMATCH**, 8 failures (ds41-stock-mask and ds41-sinks-zero-stock at nth 16/32/64 on route 0; gathered-768 and gathered-768-sinks-zero at nth 96 on route 1), NMSE about 1.7e-9 vs oracle about 1e-13 to 2e-14; mutant check not reached. Local llama commit `72b58246c`. Neither box ticked. The operator later refined the bar (bitwise at one route and one nth; different nth are partitions judged by NMSE and the oracle) and superseded the row with `ak-lb49-sinks-gate-c9-20261109-r2` (test commit `5d752bff0`), so these failures are against the stricter reading the harness tested. This row was not filed through `file_result.py`.
- Not queued: `ak-iq3s-prof-c9-20261109` (smoke rc=3, 20:45Z) and `inf75-w2-gpu-census-c9-20261109` (smoke rc=1 at 21:10Z; the prefill capture records RemoteDisconnected). Both sit in `dryrun/`, not `ready/`. `ak-kernel-mmq-h3-c9-20261109` is published (in `ready/`), not run. Boxes AK-SEED-IQ3S-PROFILE, AKX-P0d-W2, AK-MMQ-H3 stay open.
- Evidence copies: `artifacts/analysis/ak-c9-h5-lb49-20261109/`.
- Lessons filed in project docs: `docs/guides/agent-workflows/compute-fillers.md` (Publishing discipline: queued means in `ready/` or grants; smoke_predicate) and `docs/guides/agent-workflows/ratify-script-authoring.md` (new: ratify scripts fetch and rebase immediately before push; the `!` no-TTY rule is already in OPERATING_CONSTRAINTS).
- Result ticks this wrap-up: 0 (no box met its own acceptance). Result sub-bullets carry `[belief: cc]` (H5, LB4.9) or `[no-belief: ...]`.
